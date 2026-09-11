import frappe


def execute():
	"""Surface LMS Enrollment/Quiz Submission/Certificate/Program Member as
	Connections on the User doctype in Desk, without touching core's own
	user.json (which a framework upgrade would overwrite).
	"""
	links = [
		("LMS Enrollment", "member"),
		("LMS Quiz Submission", "member"),
		("LMS Certificate", "member"),
		("LMS Program Member", "member"),
	]

	custom_doc = frappe.get_doc("Customize Form")
	custom_doc.doc_type = "User"
	custom_doc.fetch_to_customize()

	existing = {link.link_doctype for link in custom_doc.links}
	changed = False
	for link_doctype, link_fieldname in links:
		if link_doctype in existing:
			continue
		custom_doc.append(
			"links",
			{
				"link_doctype": link_doctype,
				"link_fieldname": link_fieldname,
				"group": "Learning",
			},
		)
		changed = True

	if changed:
		custom_doc.save()
