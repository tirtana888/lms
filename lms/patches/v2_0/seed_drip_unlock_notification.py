import frappe

from lms.lms.email_notifications import NOTIFICATION_REGISTRY


def execute():
	"""Separate from seed_email_notifications: that patch already ran once (Patch
	Log tracks it by name) and won't re-run just because NOTIFICATION_REGISTRY
	gained this one new "drip_unlock" row - so it needs its own patch entry.
	Same idempotent insert-if-missing shape as the original.
	"""
	for event_key, label, category, description, default_template in NOTIFICATION_REGISTRY:
		if event_key != "drip_unlock":
			continue
		if frappe.db.exists("LMS Email Notification", event_key):
			return
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
