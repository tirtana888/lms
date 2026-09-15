# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

"""Single entry point every LMS notification email goes through.

Before this, each of ~12 send sites in the codebase independently decided its
own subject/template and always fired unconditionally - only 3 (certification,
batch_confirmation, payment_reminder) supported swapping in an admin-authored
Email Template, and none of them supported turning the email off at all. This
module generalizes that pattern (LMS Settings.certification_template etc.) to
every notification email in the app, backed by one doctype (LMS Email
Notification, one row per event) instead of one Settings field per email.

NOTIFICATION_REGISTRY is the single source of truth for what events exist -
both the seed patch and the Settings UI list read it, so a new event only
needs to be added here once.
"""

import frappe
from frappe import _

# (event_key, label, category, description, default_template)
# default_template names an existing .html file under lms/templates/emails/ -
# kept here only for display in Settings; the actual fallback still goes
# through frappe.sendmail(template=...), never through this string directly.
NOTIFICATION_REGISTRY = [
	(
		"published_course",
		"Course Published",
		"Course & Batch",
		"Sent to every user when a new course is published (only when System Configuration > Send Notification for Published Courses is set to Email).",
		"published_course_notification",
	),
	(
		"published_batch",
		"Batch Published",
		"Course & Batch",
		"Sent to every user when a new batch is published (only when System Configuration > Send Notification for Published Batches is set to Email).",
		"published_batch_notification",
	),
	(
		"course_interest",
		"Interested User Alert",
		"Course & Batch",
		"Sent to a user who asked to be notified once an upcoming course becomes available.",
		"lms_course_interest",
	),
	(
		"batch_confirmation",
		"Batch Enrollment Confirmation",
		"Course & Batch",
		"Sent to a student right after they enroll in a batch.",
		"batch_confirmation",
	),
	(
		"batch_start_reminder",
		"Batch Starting Tomorrow",
		"Course & Batch",
		"Sent the day before a batch starts, to every enrolled student.",
		"batch_start_reminder",
	),
	(
		"certification",
		"Certificate Issued",
		"Certificates & Evaluations",
		"Sent to a student the moment their certificate is issued.",
		"certification",
	),
	(
		"certificate_request_notification",
		"Evaluation Slot Booked",
		"Certificates & Evaluations",
		"Sent to the student and evaluator when a certificate evaluation slot is booked.",
		"certificate_request_notification",
	),
	(
		"payment_reminder",
		"Payment Reminder",
		"Course & Batch",
		"Sent to a student who started, but did not complete, a paid enrollment.",
		"payment_reminder",
	),
	(
		"live_class_reminder",
		"Live Class Today",
		"Live Classes",
		"Sent to every enrolled student on the day of a scheduled live class.",
		"live_class_reminder",
	),
	(
		"deadline_reminder_h3",
		"Deadline in 3 Days",
		"Deadlines",
		"Sent 3 days before a scheduled quiz/assignment deadline, to students who have not yet submitted.",
		"deadline_reminder",
	),
	(
		"deadline_reminder_h1",
		"Deadline Tomorrow",
		"Deadlines",
		"Sent 1 day before a scheduled quiz/assignment deadline, to students who have not yet submitted.",
		"deadline_reminder",
	),
	(
		"mention_notification",
		"Mentioned in a Comment",
		"Community",
		"Sent to a user when someone @mentions them in a lesson discussion or batch comment.",
		"mention_template",
	),
	(
		"job_application",
		"New Job Applicant",
		"Jobs",
		"Sent to the employer when a candidate applies to their job post.",
		"job_application",
	),
	(
		"job_report",
		"Job Post Reported",
		"Jobs",
		"Sent to System Managers when a user reports a job post.",
		"job_report",
	),
	(
		"drip_unlock",
		"New Content Unlocked",
		"Course & Batch",
		"Sent to a student the day a drip-scheduled chapter, quiz, or assignment becomes available to them.",
		"drip_unlock",
	),
]

def get_notification_settings(event_key: str) -> frappe._dict:
	"""Cached (enabled, custom_template) for one event. Falls back to enabled=1/
	no override if the row is missing - e.g. between deploy and the seed patch
	running, or a typo'd event_key - so a lookup miss never silently kills mail.
	"""

	def _fetch():
		row = frappe.db.get_value(
			"LMS Email Notification", event_key, ["enabled", "custom_template"], as_dict=True
		)
		if row:
			return row
		return frappe._dict(enabled=1, custom_template=None)

	return frappe.cache.hget("lms_email_notification", event_key, _fetch)


def send_notification_email(
	event_key: str,
	recipients,
	default_template: str,
	args: dict,
	default_subject: str = None,
	override_template: str = None,
	**kwargs,
):
	"""Send one LMS notification email, honoring that event's on/off + template
	override. Every call site in the app should go through this rather than
	calling frappe.sendmail directly, so Settings has exactly one place that
	actually controls every email this app sends.

	override_template: for the rare case a single record carries its own template
	choice (e.g. LMS Batch.confirmation_email_template) - takes precedence over
	the event's Settings-level custom_template, which still applies to every
	other record of that same event. The event's `enabled` flag still gates
	both the same way.

	kwargs (header, cc, bcc, attachments, retry, now, ...) pass straight through
	to frappe.sendmail unchanged.
	"""
	settings = get_notification_settings(event_key)
	if not settings.enabled:
		return

	template_override = override_template or settings.custom_template
	if template_override:
		# Not the whitelisted get_email_template() wrapper: it calls
		# doc.check_permission("read") against frappe.session.user, and Email
		# Template only grants read to Desk User/System Manager (confirmed
		# against the vendored doctype JSON) - every LMS role here (LMS
		# Student included) has desk_access=0. Plenty of these send sites run
		# inside a hook triggered by the student's own action (enrolling in a
		# batch, applying for a job, ...), so that check would throw and the
		# email - sometimes the whole triggering action - would fail the
		# moment any admin sets a custom template. Sending a notification is
		# a privileged, system-level operation regardless of who happens to
		# be logged in when the trigger fires, so it reads the template
		# directly instead of through the permission-gated wrapper.
		email_template = frappe.get_doc("Email Template", template_override).get_formatted_email(args)
		frappe.sendmail(
			recipients=recipients,
			subject=email_template.get("subject") or default_subject,
			content=email_template.get("message"),
			**kwargs,
		)
	else:
		frappe.sendmail(
			recipients=recipients,
			subject=default_subject,
			template=default_template,
			args=args,
			**kwargs,
		)


@frappe.whitelist()
def get_email_notifications() -> list:
	frappe.only_for(["Moderator", "System Manager"])
	rows = frappe.get_all(
		"LMS Email Notification",
		fields=["event_key", "label", "category", "description", "enabled", "custom_template", "default_template"],
		order_by="category asc, label asc",
	)
	return rows


@frappe.whitelist()
def update_email_notification(event_key: str, enabled: int = None, custom_template: str = None):
	frappe.only_for(["Moderator", "System Manager"])
	if not frappe.db.exists("LMS Email Notification", event_key):
		frappe.throw(_("Unknown notification: {0}").format(event_key), frappe.DoesNotExistError)

	values = {}
	if enabled is not None:
		values["enabled"] = 1 if frappe.utils.cint(enabled) else 0
	# "" clears a previously-set override; None (the default) leaves it untouched.
	if custom_template is not None:
		values["custom_template"] = custom_template or None

	if not values:
		return

	doc = frappe.get_doc("LMS Email Notification", event_key)
	doc.update(values)
	doc.save(ignore_permissions=True)  # doc.on_update() clears this event's cached settings
	return {"enabled": doc.enabled, "custom_template": doc.custom_template}
