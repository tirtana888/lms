import frappe

from lms.lms.email_notifications import NOTIFICATION_REGISTRY


def execute():
	"""Idempotent: only inserts rows that don't exist yet, so re-running (or a
	registry entry added later) never overwrites an admin's enabled/custom_template
	choice on an existing row."""
	for event_key, label, category, description, default_template in NOTIFICATION_REGISTRY:
		if frappe.db.exists("LMS Email Notification", event_key):
			continue
		frappe.get_doc(
			{
				"doctype": "LMS Email Notification",
				"event_key": event_key,
				"label": label,
				"category": category,
				"description": description,
				"default_template": default_template,
				"enabled": 1,
			}
		).insert(ignore_permissions=True)
