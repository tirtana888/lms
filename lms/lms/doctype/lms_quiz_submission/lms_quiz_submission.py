# Copyright (c) 2021, FOSS United and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.desk.doctype.notification_log.notification_log import make_notification_logs
from frappe.model.document import Document
from frappe.utils import cint

EXTENSION_SCORE_CAP_PERCENTAGE = 80


class LMSQuizSubmission(Document):
	def validate(self):
		self.validate_if_max_attempts_exceeded()
		self.validate_marks()
		self.set_percentage()
		self.cap_score_if_via_extension()

	def on_update(self):
		self.notify_member()

	def validate_if_max_attempts_exceeded(self):
		max_attempts = frappe.db.get_value("LMS Quiz", self.quiz, ["max_attempts"])
		if max_attempts == 0:
			return

		from lms.lms.schedule_utils import get_active_extension

		extension = get_active_extension(self.member, "LMS Quiz", self.quiz)
		if extension:
			max_attempts += cint(extension.granted_extra_attempts)

		current_user_submission_count = frappe.db.count(
			self.doctype, filters={"quiz": self.quiz, "member": self.member}
		)
		if current_user_submission_count >= max_attempts:
			frappe.throw(
				_("You have exceeded the maximum number of attempts ({0}) for this quiz").format(
					max_attempts
				),
				MaximumAttemptsExceededError,
			)

	def validate_marks(self):
		self.score = 0
		for row in self.result:
			if cint(row.marks) > cint(row.marks_out_of):
				frappe.throw(
					_(
						"Marks for question number {0} cannot be greater than the marks allotted for that question."
					).format(row.idx)
				)
			else:
				self.score += cint(row.marks)

	def set_percentage(self):
		if self.score and self.score_out_of:
			# Floored at zero, or negative marking throws the whole submission away.
			self.percentage = max(0, (self.score / self.score_out_of) * 100)

	def cap_score_if_via_extension(self):
		"""A submission is only possible after the quiz's own original deadline
		has passed because an Approved extension let it through (assert_doc_within_schedule,
		called before create_submission ever reaches here, would otherwise have blocked
		it) - so it is capped at EXTENSION_SCORE_CAP_PERCENTAGE, a late-submission
		penalty. score and score_out_of are re-derived together so the two fields
		never disagree (see update_quiz_score's own int-consistency fix for why that
		matters).
		"""
		if not self.percentage or self.percentage <= EXTENSION_SCORE_CAP_PERCENTAGE:
			return
		if not self.score_out_of:
			return

		from frappe.utils import get_datetime, now_datetime

		quiz_details = frappe.db.get_value(
			"LMS Quiz",
			self.quiz,
			[
				"course",
				"schedule_end",
				"enable_scheduling",
				"deadline_type",
				"deadline_days",
				"drip_type",
				"drip_date",
				"drip_days",
			],
			as_dict=True,
		)
		if not quiz_details or not quiz_details.enable_scheduling:
			return

		from lms.lms.schedule_utils import resolve_effective_schedule_end

		original_end = quiz_details.schedule_end
		if quiz_details.deadline_type == "Days after release" and quiz_details.course:
			from lms.lms.permissions import get_drip_anchor_dates

			enrollment_creation, batch_start = get_drip_anchor_dates(quiz_details.course, self.member)
			if enrollment_creation:
				original_end = resolve_effective_schedule_end(
					quiz_details.schedule_end,
					quiz_details.deadline_type,
					quiz_details.deadline_days,
					quiz_details.drip_type,
					quiz_details.drip_date,
					quiz_details.drip_days,
					enrollment_creation,
					batch_start,
				)
		if not original_end or now_datetime() <= get_datetime(original_end):
			return

		self.score = round(self.score_out_of * EXTENSION_SCORE_CAP_PERCENTAGE / 100)
		self.percentage = max(0, (self.score / self.score_out_of) * 100)

	def notify_member(self):
		if self.score != 0 and self.has_value_changed("score"):
			notification = frappe._dict(
				{
					"subject": _("You have got a score of {0} for the quiz {1}").format(
						(frappe.bold(self.score)), frappe.bold(self.quiz_title)
					),
					"email_content": _(
						"There has been an update on your submission. You have got a score of {0} for the quiz {1}"
					).format(frappe.bold(self.score), frappe.bold(self.quiz_title)),
					"document_type": self.doctype,
					"document_name": self.name,
					"for_user": self.member,
					"from_user": frappe.session.user,
					"type": "Alert",
					"link": "",
				}
			)

			make_notification_logs(notification, [self.member])


class MaximumAttemptsExceededError(frappe.DuplicateEntryError):
	pass
