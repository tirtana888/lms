# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

"""AI-assisted quiz question drafting.

Generates candidate LMS Question rows from an instructor-described topic (plus
optional reference text, e.g. a lesson's own content) via Gemini or DeepSeek.
Nothing here writes to the database: every result is a draft dict shaped like
the question_doc QuestionCard.vue's draft mode already produces, left for the
instructor to review/edit and only then persist through the existing
frappe.client.insert path (QuizForm.vue's persistDraft) — the same contract
already used for a manually-added blank question, just several at once.

Constrained to this app's three real question types (LMS Question.type:
Choices / User Input / Open Ended) — nothing richer (dropdown, match,
ordering) exists in the schema, so the prompt is instructed accordingly.
"""

from __future__ import annotations

import json

import frappe
from frappe import _
from frappe.utils import cint

from lms.lms.utils import has_course_instructor_role, has_moderator_role

ALLOWED_TYPES = ("Choices", "User Input", "Open Ended")
MAX_COUNT = 20
MAX_OPTIONS = 10
MAX_POSSIBILITIES = 10


def _require_author() -> None:
	if not (has_moderator_role() or has_course_instructor_role()):
		frappe.throw(_("You are not permitted to generate questions."), frappe.PermissionError)


def _clean_types(question_types) -> list[str]:
	if isinstance(question_types, str):
		try:
			question_types = frappe.parse_json(question_types)
		except Exception:
			question_types = [question_types]
	if not isinstance(question_types, list) or not question_types:
		question_types = list(ALLOWED_TYPES)
	cleaned = [t for t in question_types if t in ALLOWED_TYPES]
	if not cleaned:
		frappe.throw(_("Select at least one question type."))
	return cleaned


def _response_schema(allowed_types: list[str]) -> dict:
	"""JSON Schema for the model's structured output, shared by both providers
	(Gemini's responseSchema and DeepSeek's json_schema use the same shape)."""
	return {
		"type": "object",
		"properties": {
			"questions": {
				"type": "array",
				"items": {
					"type": "object",
					"properties": {
						"type": {"type": "string", "enum": allowed_types},
						"question": {"type": "string"},
						"multiple": {"type": "boolean"},
						"options": {
							"type": "array",
							"items": {
								"type": "object",
								"properties": {
									"text": {"type": "string"},
									"is_correct": {"type": "boolean"},
									"explanation": {"type": "string"},
								},
								"required": ["text", "is_correct"],
							},
						},
						"possibilities": {"type": "array", "items": {"type": "string"}},
					},
					"required": ["type", "question"],
				},
			}
		},
		"required": ["questions"],
	}


def _build_prompt(topic: str, count: int, allowed_types: list[str], reference_text: str | None) -> str:
	type_notes = {
		"Choices": (
			"Choices: 2-6 short options. Exactly one option has is_correct true unless "
			"the question genuinely has more than one correct option, in which case set "
			"multiple true and mark every correct one. Never leave an option's "
			"correctness ambiguous."
		),
		"User Input": (
			"User Input: a short-answer/fill-in-the-blank question. Provide 1-5 "
			"acceptable phrasings of the correct answer in possibilities (these are "
			"matched by fuzzy similarity, not exact string match, so near-duplicate "
			"phrasings are fine but do not pad with unrelated wrong answers)."
		),
		"Open Ended": (
			"Open Ended: a free-response question a human will grade manually. No "
			"options or possibilities."
		),
	}
	notes = "\n".join(f"- {type_notes[t]}" for t in allowed_types)
	parts = [
		f"You are writing {count} quiz question(s) for a course on: {topic.strip()}",
		"Only use these question types, exactly as spelled: " + ", ".join(allowed_types) + ".",
		notes,
		"Write plain question text (no markdown headers, no numbering prefix).",
		"Match the difficulty and terminology to the topic description.",
	]
	if reference_text:
		# Truncated: this is student-facing lesson material handed to the model as
		# grounding context, not something worth spending the whole budget on if an
		# instructor pastes in an entire chapter.
		parts.append(
			"Base the questions on this reference material rather than general "
			"knowledge where the two would differ:\n---\n" + reference_text[:8000] + "\n---"
		)
	return "\n".join(parts)


def _call_gemini(prompt: str, schema: dict) -> dict:
	import requests

	api_key = frappe.utils.password.get_decrypted_password(
		"LMS Settings", "LMS Settings", "gemini_api_key", raise_exception=False
	)
	if not api_key:
		frappe.throw(_("Gemini API Key is not configured. Add it in LMS Settings."))

	url = (
		"https://generativelanguage.googleapis.com/v1beta/models/"
		"gemini-flash-latest:generateContent"
	)
	response = requests.post(
		url,
		params={"key": api_key},
		json={
			"contents": [{"parts": [{"text": prompt}]}],
			"generationConfig": {
				"responseMimeType": "application/json",
				"responseSchema": schema,
			},
		},
		timeout=60,
	)
	if not response.ok:
		frappe.log_error(title="Gemini quiz generation failed", message=response.text[:2000])
		frappe.throw(_("Gemini request failed: {0}").format(response.status_code))
	data = response.json()
	try:
		text = data["candidates"][0]["content"]["parts"][0]["text"]
	except (KeyError, IndexError):
		frappe.throw(_("Gemini returned an unexpected response."))
	return json.loads(text)


def _call_deepseek(prompt: str, schema: dict) -> dict:
	import requests

	api_key = frappe.utils.password.get_decrypted_password(
		"LMS Settings", "LMS Settings", "deepseek_api_key", raise_exception=False
	)
	if not api_key:
		frappe.throw(_("DeepSeek API Key is not configured. Add it in LMS Settings."))

	# DeepSeek's JSON mode only guarantees *valid JSON*, not schema conformance
	# (unlike Gemini's responseSchema) - the schema is restated in-prompt as the
	# best available steering, and _parse_ai_questions() is the real backstop.
	schema_prompt = (
		prompt
		+ "\n\nRespond with a single JSON object matching this shape (no prose, "
		"no markdown fences):\n" + json.dumps(schema)
	)
	response = requests.post(
		"https://api.deepseek.com/chat/completions",
		headers={"Authorization": f"Bearer {api_key}"},
		json={
			"model": "deepseek-chat",
			"messages": [{"role": "user", "content": schema_prompt}],
			"response_format": {"type": "json_object"},
		},
		timeout=60,
	)
	if not response.ok:
		frappe.log_error(title="DeepSeek quiz generation failed", message=response.text[:2000])
		frappe.throw(_("DeepSeek request failed: {0}").format(response.status_code))
	data = response.json()
	try:
		text = data["choices"][0]["message"]["content"]
	except (KeyError, IndexError):
		frappe.throw(_("DeepSeek returned an unexpected response."))
	return json.loads(text)


def _to_draft(raw_question: dict, allowed_types: list[str]) -> dict | None:
	"""Map one model-proposed question into the question_doc shape
	QuestionCard.vue's draft mode / persistDraft() already expects. Returns
	None (dropped, not thrown) for a malformed row so one bad item in a batch
	doesn't fail the whole generation - the instructor reviews the survivors
	either way before anything is saved.
	"""
	q_type = raw_question.get("type")
	text = (raw_question.get("question") or "").strip()
	if q_type not in allowed_types or not text:
		return None

	draft = {"type": q_type, "question": text, "marks": 1}

	if q_type == "Choices":
		options = [o for o in (raw_question.get("options") or []) if (o.get("text") or "").strip()]
		options = options[:MAX_OPTIONS]
		if len(options) < 2 or not any(o.get("is_correct") for o in options):
			return None
		draft["multiple"] = 1 if sum(1 for o in options if o.get("is_correct")) > 1 else 0
		for i, option in enumerate(options, start=1):
			draft[f"option_{i}"] = option.get("text", "").strip()
			draft[f"is_correct_{i}"] = 1 if option.get("is_correct") else 0
			if option.get("explanation"):
				draft[f"explanation_{i}"] = option["explanation"]

	elif q_type == "User Input":
		possibilities = [p for p in (raw_question.get("possibilities") or []) if isinstance(p, str) and p.strip()]
		possibilities = possibilities[:MAX_POSSIBILITIES]
		if not possibilities:
			return None
		for i, possibility in enumerate(possibilities, start=1):
			draft[f"possibility_{i}"] = possibility.strip()

	return draft


@frappe.whitelist()
def generate_quiz_questions(
	topic: str,
	count: int | str = 5,
	question_types: list | str | None = None,
	provider: str = "gemini",
	reference_text: str | None = None,
):
	"""Return a list of not-yet-saved question drafts. Writes nothing."""
	_require_author()

	if not isinstance(topic, str) or not topic.strip():
		frappe.throw(_("Please describe the topic."))

	count = min(max(cint(count) or 5, 1), MAX_COUNT)
	allowed_types = _clean_types(question_types)
	if reference_text is not None and not isinstance(reference_text, str):
		frappe.throw(_("reference_text must be a string."))

	prompt = _build_prompt(topic, count, allowed_types, reference_text)
	schema = _response_schema(allowed_types)

	if provider == "deepseek":
		raw = _call_deepseek(prompt, schema)
	elif provider == "gemini":
		raw = _call_gemini(prompt, schema)
	else:
		frappe.throw(_("Unknown provider: {0}").format(provider))

	raw_questions = raw.get("questions") if isinstance(raw, dict) else None
	if not isinstance(raw_questions, list):
		frappe.throw(_("The AI response was not in the expected format."))

	drafts = [d for d in (_to_draft(q, allowed_types) for q in raw_questions if isinstance(q, dict)) if d]
	if not drafts:
		frappe.throw(_("The AI did not return any usable questions. Try rephrasing the topic."))
	return drafts


@frappe.whitelist()
def get_lesson_reference_text(lesson: str) -> str:
	"""Plain text pulled from a lesson's own content, for use as generation
	grounding. Read-only, same authoring-role gate as generation itself.
	"""
	_require_author()
	if not isinstance(lesson, str) or not lesson:
		frappe.throw(_("lesson is required."))

	from lms.lms.utils import get_editorjs_blocks

	content = frappe.db.get_value("Course Lesson", lesson, "content")
	if not content:
		return ""

	# Only the block types that actually hold prose; upload/scorm/quiz/assignment
	# blocks carry no extractable study text.
	chunks = []
	for block in get_editorjs_blocks(content):
		data = block.get("data") or {}
		block_type = block.get("type")
		if block_type in ("header", "paragraph", "markdown", "quote") and data.get("text"):
			chunks.append(frappe.utils.strip_html_tags(data["text"]))
		elif block_type == "list" and isinstance(data.get("items"), list):
			for item in data["items"]:
				item_text = item.get("content") if isinstance(item, dict) else item
				if isinstance(item_text, str) and item_text.strip():
					chunks.append(frappe.utils.strip_html_tags(item_text))
	return "\n".join(c.strip() for c in chunks if c and c.strip())
