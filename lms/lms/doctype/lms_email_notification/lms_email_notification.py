# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class LMSEmailNotification(Document):
	def on_update(self):
		# Every send-site reads through email_notifications.get_notification_settings(),
		# which caches by event_key - without this an admin's toggle/template change
		# would not take effect until something else happened to clear the cache.
		frappe.cache.hdel("lms_email_notification", self.event_key)
