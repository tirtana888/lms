# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from lms.lms.doctype.lms_content_author.lms_content_author import AuthoredDocument
from lms.lms.schedule_utils import validate_schedule_fields
from lms.lms.utils import has_course_instructor_role, has_moderator_role


class LMSAssignment(AuthoredDocument, Document):
	def validate(self):
		validate_schedule_fields(self)
