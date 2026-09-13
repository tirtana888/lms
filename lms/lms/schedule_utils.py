# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

"""Shared availability-window helpers for LMS Quiz and LMS Assignment."""

from __future__ import annotations

from zoneinfo import ZoneInfo

import frappe
from frappe import _
from frappe.utils import add_days, cint, get_datetime, get_system_timezone, getdate, now_datetime


def validate_schedule_fields(doc) -> None:
	"""DocType validate for enable_scheduling / schedule_start / schedule_end.

	When scheduling is off, clear start/end so stale values are not kept.
	When on, start is required and end (if set) must be after start.
	"""
	if not doc.enable_scheduling:
		doc.schedule_start = None
		doc.schedule_end = None
		return

	if not doc.schedule_start:
		frappe.throw(_("Schedule Start is required when scheduling is enabled."))

	if doc.schedule_end:
		start = get_datetime(doc.schedule_start)
		end = get_datetime(doc.schedule_end)
		if end <= start:
			frappe.throw(_("Schedule End must be after Schedule Start."))


def get_schedule_block_reason(
	enable_scheduling,
	schedule_start,
	schedule_end,
	*,
	now=None,
) -> str | None:
	"""Return 'not_started', 'ended', or None if the window is open."""
	if not enable_scheduling:
		return None

	now = now or now_datetime()
	if schedule_start and now < get_datetime(schedule_start):
		return "not_started"
	if schedule_end and now > get_datetime(schedule_end):
		return "ended"
	return None


def assert_within_schedule(
	enable_scheduling,
	schedule_start,
	schedule_end,
	*,
	label: str | None = None,
) -> None:
	"""Throw if the current time is outside the availability window."""
	reason = get_schedule_block_reason(enable_scheduling, schedule_start, schedule_end)
	if not reason:
		return

	item = label or _("This item")
	if reason == "not_started":
		frappe.throw(
			_("{0} opens on {1}.").format(item, frappe.format(schedule_start, {"fieldtype": "Datetime"})),
			frappe.ValidationError,
		)
	frappe.throw(
		_("The schedule for {0} has ended.").format(item),
		frappe.ValidationError,
	)


def resolve_effective_schedule_end(
	schedule_end,
	deadline_type,
	deadline_days,
	drip_type,
	drip_date,
	drip_days,
	enrollment_creation,
	batch_start_date,
):
	"""``schedule_end`` as stored, unless ``deadline_type`` is "Days after
	release" - then an end-of-day cutoff ``deadline_days`` after this item's
	own drip-resolved open date for THIS student, so the deadline is a
	rolling per-student window instead of one fixed cutoff that can fall
	before drip has even opened the item for some students.

	Falls back to the stored ``schedule_end`` when there is nothing to
	anchor a relative deadline to (``drip_type`` blank, or drip not yet
	resolvable) - a relative deadline needs a release date to be relative to.
	"""
	if deadline_type != "Days after release":
		return schedule_end

	from lms.lms.utils import resolve_drip_release_date

	release_date = resolve_drip_release_date(
		drip_type, drip_date, drip_days, enrollment_creation, batch_start_date
	)
	if not release_date:
		return schedule_end

	deadline_date = add_days(getdate(release_date), cint(deadline_days))
	return get_datetime(f"{deadline_date} 23:59:59")


def _resolve_doc_schedule_end(doc: dict, course: str | None, member: str | None):
	"""``schedule_end`` for ``doc``, resolved per-student when its
	``deadline_type`` is "Days after release" - the one place this
	resolution lives, shared by assert_doc_within_schedule (write side) and
	enrich_schedule_payload (read side) so the two can never drift apart.

	``course``/``member`` are optional so a caller that hasn't got them (or
	a doc whose deadline_type is blank, the overwhelming majority today)
	pays nothing extra: the stored schedule_end passes through untouched.
	"""
	schedule_end = doc.get("schedule_end")
	if doc.get("deadline_type") != "Days after release" or not course or not member:
		return schedule_end

	from lms.lms.permissions import get_drip_anchor_dates

	enrollment_creation, batch_start = get_drip_anchor_dates(course, member)
	if not enrollment_creation:
		return schedule_end

	return resolve_effective_schedule_end(
		schedule_end,
		doc.get("deadline_type"),
		doc.get("deadline_days"),
		doc.get("drip_type"),
		doc.get("drip_date"),
		doc.get("drip_days"),
		enrollment_creation,
		batch_start,
	)


def assert_doc_within_schedule(
	doc: dict, *, course: str | None = None, member: str | None = None, label: str | None = None
) -> None:
	"""Convenience wrapper for a quiz/assignment dict (e.g. from
	``frappe.db.get_value(..., as_dict=1)``).

	Pass ``course``/``member`` to also honour a "Days after release"
	deadline_type - without them this behaves exactly as before (raw
	schedule_end only), which is the correct fallback since resolving a
	relative deadline needs both.
	"""
	assert_within_schedule(
		doc.get("enable_scheduling"),
		doc.get("schedule_start"),
		_resolve_doc_schedule_end(doc, course, member),
		label=label,
	)


def datetime_to_iso(value) -> str | None:
	"""Convert a naive system-timezone Datetime to an offset-bearing ISO string.

	Learners' browsers must not treat schedule boundaries as local wall clocks;
	ISO with an explicit offset keeps client and server windows aligned.
	"""
	if not value:
		return None
	dt = get_datetime(value)
	if dt.tzinfo is None:
		dt = dt.replace(tzinfo=ZoneInfo(get_system_timezone()))
	return dt.isoformat()


def enrich_schedule_payload(doc: dict, *, member: str | None = None) -> dict:
	"""Attach schedule_block_reason and offset-aware ISO timestamps for the UI.

	``member`` defaults to the current session user - both existing callers
	(get_quiz_with_questions, get_assignment) are "can the viewer access
	this right now" reads for whoever is asking, so the default covers every
	real call site without forcing it to be passed explicitly. When the
	doc's deadline_type is "Days after release", the resolved schedule_end
	is this member's own per-student cutoff rather than the raw stored
	field - see resolve_effective_schedule_end.
	"""
	member = member or frappe.session.user
	schedule_end = _resolve_doc_schedule_end(doc, doc.get("course"), member)

	doc["schedule_block_reason"] = get_schedule_block_reason(
		doc.get("enable_scheduling"),
		doc.get("schedule_start"),
		schedule_end,
	)
	doc["schedule_start_iso"] = datetime_to_iso(doc.get("schedule_start"))
	doc["schedule_end_iso"] = datetime_to_iso(schedule_end)
	return doc
