# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime

from lms.lms.utils import PRIVILEGED_ROLES

DEFAULT_MAX_EXTENSION_REQUESTS = 2


class LMSExtensionRequest(Document):
	def validate(self):
		self.enforce_member_ownership()
		self.validate_reference()
		self.set_reference_title()
		if self.is_new():
			self.status = "Pending"
			self.validate_enrollment()
			self.snapshot_current_deadline()
			self.validate_feature_enabled()
			self.validate_request_cap()
			self.validate_no_duplicate_pending()
			self.validate_not_already_extended()

	def enforce_member_ownership(self):
		"""A student may only ever request for themselves. Reviewers (who create
		nothing here today, but may in future) are exempt so an admin action on
		behalf of a member is never blocked by this.
		"""
		if PRIVILEGED_ROLES & set(frappe.get_roles()):
			return
		if self.member and self.member != frappe.session.user:
			frappe.throw(
				_("You can only request an extension for your own account."),
				frappe.PermissionError,
			)
		self.member = frappe.session.user

	def validate_reference(self):
		if self.reference_type not in ("LMS Quiz", "LMS Assignment"):
			frappe.throw(_("Extension requests are only supported for a Quiz or an Assignment."))
		ref_course = frappe.db.get_value(self.reference_type, self.reference_name, "course")
		if not ref_course:
			frappe.throw(_("The selected item could not be found."))
		if ref_course != self.course:
			frappe.throw(_("The selected item does not belong to this course."))

	def set_reference_title(self):
		self.reference_title = frappe.db.get_value(self.reference_type, self.reference_name, "title")

	def validate_enrollment(self):
		"""get_extendable_items already requires enrollment before it will even
		offer an item to pick, but that is the picker's own gate, not
		enforcement - without this, a direct client.insert call could create a
		request for a course the caller never enrolled in.
		"""
		if PRIVILEGED_ROLES & set(frappe.get_roles()):
			return
		from lms.lms.permissions import get_membership

		if not get_membership(self.course, self.member):
			frappe.throw(_("You are not enrolled in this course."), frappe.PermissionError)

	def snapshot_current_deadline(self):
		"""The deadline as it stood for this member at request time - shown to the
		reviewer for context. Resolved the same way access is actually enforced
		(schedule_utils), not just the raw stored schedule_end.
		"""
		from lms.lms.schedule_utils import _resolve_doc_schedule_end

		doc = frappe.db.get_value(
			self.reference_type,
			self.reference_name,
			[
				"name",
				"course",
				"schedule_end",
				"deadline_type",
				"deadline_days",
				"drip_type",
				"drip_date",
				"drip_days",
			],
			as_dict=True,
		)
		if doc:
			self.current_deadline = _resolve_doc_schedule_end(
				doc,
				doc.course,
				self.member,
				reference_type=self.reference_type,
				reference_name=self.reference_name,
			)

	def validate_feature_enabled(self):
		if PRIVILEGED_ROLES & set(frappe.get_roles()):
			return
		if not frappe.db.get_value("LMS Course", self.course, "allow_extension_requests"):
			frappe.throw(
				_("Extension requests are not enabled for this course."),
				frappe.PermissionError,
			)

	def validate_request_cap(self):
		if PRIVILEGED_ROLES & set(frappe.get_roles()):
			return
		limit = (
			frappe.db.get_value("LMS Course", self.course, "max_extension_requests")
			or DEFAULT_MAX_EXTENSION_REQUESTS
		)
		# Rejected requests don't consume the cap - only ones that are still
		# pending review or were actually granted count against it.
		existing = frappe.db.count(
			"LMS Extension Request",
			{"member": self.member, "course": self.course, "status": ["!=", "Rejected"]},
		)
		if existing >= limit:
			frappe.throw(
				_("You have reached the maximum of {0} extension requests for this course.").format(limit),
				frappe.ValidationError,
			)

	def validate_no_duplicate_pending(self):
		if frappe.db.exists(
			"LMS Extension Request",
			{
				"member": self.member,
				"reference_type": self.reference_type,
				"reference_name": self.reference_name,
				"status": "Pending",
			},
		):
			frappe.throw(_("You already have a pending extension request for this item."))

	def validate_not_already_extended(self):
		"""get_extendable_items already hides an item once it has a still-valid
		Approved extension, but that is a UI convenience, not the enforcement -
		block it here too so a direct client.insert call can't create a second,
		redundant Approved row (and burn another slot of the cap) for something
		already unlocked.
		"""
		active = frappe.db.exists(
			"LMS Extension Request",
			{
				"member": self.member,
				"reference_type": self.reference_type,
				"reference_name": self.reference_name,
				"status": "Approved",
				"granted_until": [">=", now_datetime()],
			},
		)
		if active:
			frappe.throw(_("This item already has an active extension."))
