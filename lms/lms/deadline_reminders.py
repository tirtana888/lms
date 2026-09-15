# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

"""Deadline reminders for scheduled quizzes/assignments (LMS Settings' schedule
feature - item 7/16, upstream PR #2719). Deliberately simpler than a
drip-unlock notification would be: `schedule_end` is one fixed Datetime shared
by every student on that quiz/assignment, not resolved per-student like drip's
anchor date - so "does this fire today" needs no per-student dedup tracking at
all, just an exact day-offset match.
"""

import frappe
from frappe import _
from frappe.utils import add_days, nowdate

from lms.lms.email_notifications import send_notification_email
from lms.lms.utils import get_lms_route

# (doctype, submission doctype, submission's link fieldname back to it)
_ASSESSMENT_KINDS = [
	("LMS Quiz", "LMS Quiz Submission", "quiz"),
	("LMS Assignment", "LMS Assignment Submission", "assignment"),
]


def send_deadline_reminders_h3():
	_send_deadline_reminders(days_before=3, event_key="deadline_reminder_h3")


def send_deadline_reminders_h1():
	_send_deadline_reminders(days_before=1, event_key="deadline_reminder_h1")


def _send_deadline_reminders(days_before: int, event_key: str):
	target_date = add_days(nowdate(), days_before)
	for doctype, submission_doctype, link_field in _ASSESSMENT_KINDS:
		_remind_for_kind(doctype, submission_doctype, link_field, target_date, event_key, days_before)


def _remind_for_kind(doctype, submission_doctype, link_field, target_date, event_key, days_before):
	items = frappe.get_all(
		doctype,
		{
			"enable_scheduling": 1,
			"schedule_end": ["between", [f"{target_date} 00:00:00", f"{target_date} 23:59:59"]],
		},
		["name", "title", "course"],
	)

	for item in items:
		if not item.course:
			continue

		members = frappe.get_all(
			"LMS Enrollment", {"course": item.course}, ["member", "member_name"]
		)
		if not members:
			continue

		submitted = set(
			frappe.get_all(
				submission_doctype,
				{link_field: item.name, "member": ["in", [m.member for m in members]]},
				pluck="member",
			)
		)
		course_title = frappe.db.get_value("LMS Course", item.course, "title")
		course_url = frappe.utils.get_url(get_lms_route(f"courses/{item.course}"))

		for member in members:
			if member.member in submitted:
				continue

			args = {
				"student_name": member.member_name,
				"item_title": item.title,
				"course_title": course_title,
				"days_left": days_before,
				"course_url": course_url,
			}
			subject = (
				_("Deadline tomorrow: {0}").format(item.title)
				if days_before == 1
				else _("Deadline in {0} days: {1}").format(days_before, item.title)
			)
			send_notification_email(
				event_key,
				member.member,
				"deadline_reminder",
				args,
				default_subject=subject,
				header=[subject, "orange"],
			)
