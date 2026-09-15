# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

"""Email a student the moment a drip-scheduled chapter/quiz/assignment opens
for them (item 12a). The two things that made this "the trickiest part" of
the whole email-notification plan (see the roadmap): drip's release date is
resolved per student (enrollment date, or their batch's start date - not one
shared date like a schedule_end deadline), and "is this unlocked" stays true
forever once the date passes, so re-running the check every day needs its own
dedup log (LMS Drip Notification Log) - unlike deadline_reminders.py, which
needed none because an exact day-offset match can only ever be true once.
"""

import frappe
from frappe import _
from frappe.utils import getdate, nowdate

from lms.lms.email_notifications import send_notification_email
from lms.lms.permissions import get_drip_anchor_dates
from lms.lms.utils import get_lms_route, resolve_drip_release_date

# (doctype, content_type label used on LMS Drip Notification Log)
_DRIP_KINDS = [
	("Course Chapter", "Chapter"),
	("LMS Quiz", "Quiz"),
	("LMS Assignment", "Assignment"),
]


def send_drip_unlock_notifications():
	for doctype, label in _DRIP_KINDS:
		_process_kind(doctype, label)


def backfill_existing_unlocks():
	"""One-time (run from a patch, not the scheduler): mark every already-
	unlocked (member, content) combination as already notified, without
	sending anything. Without this, the very first real run of
	send_drip_unlock_notifications() would see every chapter/quiz/assignment
	that unlocked for any student at any point in the past - weeks or months
	of backlog for a long-lived site - as brand new, and email all of it to
	everyone at once. Only unlocks that happen after this point should ever
	generate a real email.
	"""
	for doctype, label in _DRIP_KINDS:
		_process_kind(doctype, label, send_email=False)


def _process_kind(doctype: str, label: str, send_email: bool = True):
	items = frappe.get_all(
		doctype,
		# Same filter shape already proven for chapters in compute_drip_locked_chapters
		# (lms/lms/utils.py) - matched here rather than invented, since a bare
		# "!=" '' (not a "not in" list) is what's confirmed to also exclude a
		# NULL drip_type correctly on this schema.
		{"drip_type": ("!=", "")},
		["name", "title", "course", "drip_type", "drip_date", "drip_days"],
	)
	if not items:
		return

	by_course = {}
	for item in items:
		if item.course:
			by_course.setdefault(item.course, []).append(item)

	for course, course_items in by_course.items():
		members = frappe.get_all("LMS Enrollment", {"course": course}, ["member", "member_name"])
		if not members:
			continue
		course_title = frappe.db.get_value("LMS Course", course, "title")
		course_url = frappe.utils.get_url(get_lms_route(f"courses/{course}"))

		for member in members:
			enrollment_creation, batch_start = get_drip_anchor_dates(course, member.member)
			if not enrollment_creation:
				continue

			for item in course_items:
				_maybe_notify(
					label, item, member, course, course_title, course_url,
					enrollment_creation, batch_start, send_email,
				)


def _maybe_notify(
	label, item, member, course, course_title, course_url, enrollment_creation, batch_start, send_email=True
):
	release = resolve_drip_release_date(
		item.drip_type, item.drip_date, item.drip_days, enrollment_creation, batch_start
	)
	# Not just "== today": a missed scheduler run (a day the container was
	# down) must still catch up on anything that unlocked in the meantime,
	# not silently skip it forever. LMS Drip Notification Log below is what
	# turns this "still true tomorrow" comparison into a one-time email
	# instead of a repeat every day after release.
	if not release or getdate(release) > getdate():
		return

	already_sent = frappe.db.exists(
		"LMS Drip Notification Log",
		{"member": member.member, "content_type": label, "content_name": item.name},
	)
	if already_sent:
		return

	if send_email:
		args = {
			"student_name": member.member_name,
			"item_title": item.title,
			"item_type": label,
			"course_title": course_title,
			"course_url": course_url,
		}
		subject = _("New content unlocked: {0}").format(item.title)
		send_notification_email(
			"drip_unlock",
			member.member,
			"drip_unlock",
			args,
			default_subject=subject,
			header=[subject, "green"],
		)
	frappe.get_doc(
		{
			"doctype": "LMS Drip Notification Log",
			"member": member.member,
			"content_type": label,
			"content_name": item.name,
			"course": course,
			"notified_on": nowdate(),
		}
	).insert(ignore_permissions=True)
