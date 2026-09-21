"""Live presence: who has the LMS open in a visible browser tab right now.

`User.last_active` and the login log only move when a browser makes a request, so a
student watching a video or reading an already-loaded page looks offline after a few
minutes. Instead the frontend sends a small heartbeat (`ping`) every ~30 seconds from
each visible tab, and a user counts as present until PRESENCE_TTL_SECONDS pass without one.

State lives only in Redis (a sorted set of user -> last ping time, plus one short-lived key
per user holding where they are). Nothing is written to the database, and a closed tab
drops out by itself within the TTL.
"""

import json
import time

import frappe
from frappe import _

from lms.lms.utils import (
	PRIVILEGED_ROLES,
	has_course_instructor_role,
	has_evaluator_role,
	has_moderator_role,
)

# Three missed 30-second pings.
PRESENCE_TTL_SECONDS = 90
MAX_TRACKED_USERS = 5000
MAX_FIELD_LENGTH = 140
IGNORED_USERS = ("Administrator", "Guest")

_INDEX_KEY = "lms_presence"


def _text(value) -> str | None:
	if not isinstance(value, str):
		return None
	value = value.strip()[:MAX_FIELD_LENGTH]
	return value or None


def _index_key(cache) -> str:
	return cache.make_key(_INDEX_KEY)


def _detail_key(cache, user: str) -> str:
	return cache.make_key(f"{_INDEX_KEY}:{user}")


def record_ping(cache, user: str, page: str | None, course: str | None, is_staff: bool, now_ts: float):
	"""Mark `user` as present at `now_ts`. Repeated pings overwrite, so the state cannot grow."""
	cache.zadd(_index_key(cache), {user: now_ts})
	detail = {"page": _text(page), "course": _text(course), "staff": bool(is_staff)}
	cache.setex(name=_detail_key(cache, user), time=PRESENCE_TTL_SECONDS, value=json.dumps(detail))


def read_present(cache, now_ts: float) -> list[dict]:
	"""Everyone whose last ping is within the TTL, with where they are."""
	index = _index_key(cache)
	cache.zremrangebyscore(index, "-inf", now_ts - PRESENCE_TTL_SECONDS)
	users = [u.decode() if isinstance(u, bytes) else u for u in cache.zrange(index, 0, MAX_TRACKED_USERS - 1)]
	if not users:
		return []

	present = []
	for user, raw in zip(users, cache.mget([_detail_key(cache, u) for u in users])):
		if raw is None:
			# The per-user key already expired: the ping is too old to count.
			continue
		try:
			detail = json.loads(raw)
		except (TypeError, ValueError):
			continue
		present.append({"user": user, **detail})
	return present


def summarize(present: list[dict]) -> dict:
	"""Counts for the dashboard: learners vs. staff, and where the learners are."""
	learners = [p for p in present if not p.get("staff")]
	by_course: dict[str, int] = {}
	for p in learners:
		if p.get("course"):
			by_course[p["course"]] = by_course.get(p["course"], 0) + 1
	return {
		"learners": len(learners),
		"staff": len(present) - len(learners),
		"on_course_pages": sum(by_course.values()),
		"by_course": sorted(by_course.items(), key=lambda kv: (-kv[1], kv[0])),
	}


@frappe.whitelist(methods=["POST"])
def ping(page: str = None, course: str = None):
	"""Heartbeat from an open, visible LMS tab. Cheap by design: Redis only, no DB writes."""
	user = frappe.session.user
	if user in IGNORED_USERS:
		return {"tracked": False}
	is_staff = bool(PRIVILEGED_ROLES.intersection(frappe.get_roles(user)))
	record_ping(frappe.cache(), user, page, course, is_staff, time.time())
	return {"tracked": True}


@frappe.whitelist()
def get_active_now():
	"""Learners with the LMS open right now, for the admin dashboard (same audience as the rest of it)."""
	if not (
		has_moderator_role()
		or has_course_instructor_role()
		or has_evaluator_role()
		or "System Manager" in frappe.get_roles()
	):
		frappe.throw(_("You are not permitted to view this dashboard."), frappe.PermissionError)

	now_ts = time.time()
	summary = summarize(read_present(frappe.cache(), now_ts))

	titles = {}
	if summary["by_course"]:
		titles = {
			row.name: row.title
			for row in frappe.get_all(
				"LMS Course", {"name": ["in", [c for c, _n in summary["by_course"]]]}, ["name", "title"]
			)
		}
	return {
		"learners": summary["learners"],
		"staff": summary["staff"],
		"elsewhere": summary["learners"] - summary["on_course_pages"],
		"courses": [
			{"course": name, "title": titles.get(name) or name, "count": count}
			for name, count in summary["by_course"]
		],
		"window_seconds": PRESENCE_TTL_SECONDS,
		"as_of": frappe.utils.now_datetime().isoformat(),
	}
