# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

"""Server-side proxy between the lesson page's AI Study Coach and getlearn.ai.

The browser never sees the getlearn.ai API key: a student's question reaches this module
through the normal logged-in Frappe session, and only the server talks to getlearn.ai.
The student is identified there by the same one-way id getlearn.ai derives while pulling
this site's roster (see FrappeSyncService.anonymizeLearnerId), so no email leaves the site.
"""

from __future__ import annotations

import hashlib
from urllib.parse import quote

import frappe
import frappe.utils.password
from frappe import _

DEFAULT_BASE_URL = "https://getlearn-core-production.up.railway.app"
REQUEST_TIMEOUT = 60
MAX_MESSAGE_LENGTH = 1000
# Per student: at most this many questions per window. getlearn.ai meters tokens per school,
# so one runaway client must not be able to drain everyone's balance.
RATE_LIMIT_MESSAGES = 20
RATE_LIMIT_WINDOW_SECONDS = 600


def _learner_ref(user: str) -> str:
	# Must stay identical to the derivation in getlearn.ai's frappeSync.service.ts.
	return "frappe_" + hashlib.sha256(user.encode("utf-8")).hexdigest()[:32]


def _require_student() -> str:
	user = frappe.session.user
	if not user or user == "Guest":
		frappe.throw(_("Please log in to use the AI Study Coach."), frappe.PermissionError)
	return user


def _config() -> tuple[str, str] | None:
	"""(base_url, api_key), or None when the integration is switched off / not set up."""
	settings = frappe.get_cached_doc("LMS Settings")
	if not settings.get("getlearn_enabled"):
		return None
	api_key = frappe.utils.password.get_decrypted_password(
		"LMS Settings", "LMS Settings", "getlearn_api_key", raise_exception=False
	)
	# Doctype defaults are not backfilled into an already-saved single, so fall back here.
	base_url = (settings.get("getlearn_base_url") or DEFAULT_BASE_URL).rstrip("/")
	if not api_key or not base_url:
		return None
	return base_url, api_key


def _check_rate_limit(user: str) -> None:
	# Best effort: if the cache is unavailable we skip limiting rather than block students.
	try:
		cache = frappe.cache()
		key = f"getlearn_chat_count:{user}"
		count = int(cache.get_value(key) or 0)
		if count >= RATE_LIMIT_MESSAGES:
			frappe.throw(
				_("You are asking questions very quickly. Please wait a few minutes and try again."),
				frappe.ValidationError,
			)
		cache.set_value(key, count + 1, expires_in_sec=RATE_LIMIT_WINDOW_SECONDS)
	except frappe.ValidationError:
		raise
	except Exception:
		frappe.log_error(title="getlearn chat rate limit unavailable")


def _request(method: str, path: str, body: dict | None = None) -> dict:
	import requests

	config = _config()
	if not config:
		frappe.throw(_("The AI Study Coach is not enabled on this site."))
	base_url, api_key = config

	try:
		response = requests.request(
			method,
			f"{base_url}{path}",
			json=body,
			headers={"Authorization": f"Bearer {api_key}"},
			timeout=REQUEST_TIMEOUT,
		)
	except requests.RequestException:
		frappe.log_error(title="getlearn chat request failed")
		frappe.throw(_("The AI Study Coach is unreachable right now. Please try again shortly."))

	if response.status_code == 402:
		frappe.throw(_("The AI Study Coach is temporarily unavailable. Please contact your administrator."))
	if response.status_code == 404:
		frappe.throw(
			_(
				"Your learning profile is not ready yet. It is updated every few minutes, "
				"please try again shortly."
			)
		)
	if not response.ok:
		frappe.log_error(
			title="getlearn chat error", message=f"{response.status_code}: {response.text[:2000]}"
		)
		frappe.throw(_("The AI Study Coach could not answer right now. Please try again."))

	return response.json()


def _lesson_titles(ids: list[str]) -> list[dict]:
	if not ids:
		return []
	rows = frappe.get_all("Course Lesson", filters={"name": ["in", ids]}, fields=["name", "title"])
	titles = {r.name: r.title for r in rows}
	# Keep getlearn's ordering; an id that is not a lesson (e.g. other content) is dropped.
	return [{"id": i, "title": titles[i]} for i in ids if i in titles]


@frappe.whitelist()
def get_chat_config() -> dict:
	"""Lets the lesson page decide whether to show the coach at all."""
	_require_student()
	return {"enabled": _config() is not None}


def _lesson_titles_map(ids: list[str]) -> dict[str, str]:
	ids = [i for i in dict.fromkeys(ids) if i]
	if not ids:
		return {}
	rows = frappe.get_all("Course Lesson", filters={"name": ["in", ids]}, fields=["name", "title"])
	return {r.name: r.title for r in rows}


def _history_items(messages: list[dict]) -> list[dict]:
	"""getlearn's stored messages in the shape the widget renders, with lesson titles resolved."""
	wanted: list[str] = []
	for m in messages:
		wanted.append(m.get("lesson_id") or "")
		wanted.extend(m.get("source_content_ids") or [])
	titles = _lesson_titles_map(wanted)

	items = []
	for m in messages:
		lesson_id = m.get("lesson_id")
		items.append(
			{
				"id": m.get("id"),
				"role": "user" if m.get("sender") == "user" else "assistant",
				"text": m.get("content") or "",
				"sources": [
					{"id": i, "title": titles[i]} for i in (m.get("source_content_ids") or []) if i in titles
				],
				"lesson": lesson_id if lesson_id in titles else None,
				"lesson_title": titles.get(lesson_id) if lesson_id else None,
			}
		)
	return items


@frappe.whitelist()
def resume_session(fresh: int | str = 0) -> dict:
	"""The student's one continuous conversation with the coach, with its recent messages.

	It follows the student from lesson to lesson (the open lesson travels with each message), and
	survives reloads and other devices because getlearn.ai keeps it. ``fresh`` starts a new one.
	"""
	user = _require_student()
	data = _request(
		"POST",
		"/v1/chat/sessions/resume",
		{"learner_id": _learner_ref(user), "fresh": frappe.utils.cint(fresh) == 1},
	)
	return {
		"session_id": data["session_id"],
		"resumed": bool(data.get("resumed")),
		"messages": _history_items(data.get("messages") or []),
	}


@frappe.whitelist()
def start_session(lesson: str | None = None) -> dict:
	user = _require_student()

	body = {"learner_id": _learner_ref(user), "scope": "learner", "objective_ids": []}
	# From a lesson page the coach searches that lesson's material first.
	if lesson and isinstance(lesson, str) and frappe.db.exists("Course Lesson", lesson):
		body.update(scope="objective", objective_ids=[lesson])

	data = _request("POST", "/v1/chat/sessions", body)
	return {"session_id": data["session_id"], "opening_message": data["opening_message"]}


@frappe.whitelist()
def send_message(session_id: str, message: str, lesson: str | None = None) -> dict:
	user = _require_student()

	if not isinstance(session_id, str) or not session_id:
		frappe.throw(_("Missing chat session."))
	if not isinstance(message, str) or not message.strip():
		frappe.throw(_("Please type a question."))
	message = message.strip()
	if len(message) > MAX_MESSAGE_LENGTH:
		frappe.throw(_("Your question is too long. Please keep it under {0} characters.").format(MAX_MESSAGE_LENGTH))

	# A session belongs to one student: never let one student write into another's session,
	# even if a session id leaks.
	session = _request("GET", f"/v1/chat/sessions/{quote(session_id, safe='')}")
	if session.get("learner_id") != _learner_ref(user):
		frappe.throw(_("This chat session does not belong to you."), frappe.PermissionError)

	_check_rate_limit(user)

	body = {"message": message}
	# The lesson the student has open right now; retrieval and their scores follow it.
	if lesson and isinstance(lesson, str) and frappe.db.exists("Course Lesson", lesson):
		body["lesson_id"] = lesson

	data = _request("POST", f"/v1/chat/sessions/{quote(session_id, safe='')}/messages", body)
	# Follow-up questions the coach suggests; defensive about shape and length, they go to the UI.
	suggestions = [
		s.strip()[:60] for s in (data.get("suggestions") or []) if isinstance(s, str) and s.strip()
	][:3]
	return {
		"id": data.get("message_id"),
		"message": data["content"],
		"sources": _lesson_titles(data.get("source_content_ids") or []),
		"suggestions": suggestions,
	}
