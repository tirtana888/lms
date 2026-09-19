"""Custom page renderers for LMS app.

Handles rendering of profile pages.
"""

import mimetypes
import os
from urllib.parse import unquote

import frappe
from frappe.website.page_renderers.base_renderer import BaseRenderer
from werkzeug.utils import send_file

# A SCORM package is not one request, it is 25-70 of them for a single page view
# (every JS chunk, font, image and content fragment is its own file) and more
# again as the learner scrolls. Every one of those was served with no validators
# at all, so nothing was ever reusable: reopening or reloading a lesson re-fetched
# the whole package - a 1.4 MB JS chunk included - through the same Python gate,
# behind a web pool shared with the rest of the app. The bytes are extracted files
# that only change when an instructor re-uploads the package, so they cache well.
# An hour, not longer: a re-upload should still reach learners the same session.
SCORM_ASSET_MAX_AGE = 60 * 60

# How long an "allowed" decision is reused across the follow-up asset requests of
# the same package. The gate below runs per file, and each run costs several
# queries (chapter/lesson lookup, course access, drip + deadline lock state) -
# paid again for every file in the package. Only an allow is cached, and only
# briefly: a denial is always evaluated fresh, and a lesson that locks mid-session
# closes within this window rather than whenever the learner next loads a page.
SCORM_PERMISSION_TTL = 60


def _serve_scorm_file(path):
	"""Serve an extracted SCORM file with the validators a static file server would send.

	`send_file` rather than a bare Response, for its conditional handling: a repeat
	view answers If-None-Match/If-Modified-Since with a 304 instead of the bytes,
	and a media file inside a package can be range-requested, which iOS Safari
	requires before it will play audio or video at all.
	"""
	response = send_file(
		path,
		frappe.local.request.environ,
		mimetype=mimetypes.guess_type(path)[0] or "application/octet-stream",
		conditional=True,
		max_age=SCORM_ASSET_MAX_AGE,
	)
	# send_file marks a cacheable response public; these bytes are gated per user,
	# so only the learner's own browser may hold them - never a shared proxy or CDN.
	response.cache_control.public = False
	response.cache_control.private = True
	return response


class SCORMRenderer(BaseRenderer):
	def can_render(self):
		return "scorm/" in self.path

	# Disk roots tried, in order, to resolve SCORM bytes. New packages are extracted
	# under private/scorm (gated: /private is always routed through Frappe, so this
	# permission gate runs in production too). Legacy packages already extracted under
	# public/scorm are still served as a fallback, but the standard bench nginx config
	# serves public/ directly (try_files .../public/$uri @webserver), so for those legacy
	# files this Python gate is BYPASSED in production, exactly as before. Such packages
	# stay ungated in prod until re-uploaded (re-extraction lands them in private). New
	# uploads are gated in dev and prod alike.
	_DISK_ROOTS = ("private", "public")

	def _check_permission(self):
		from lms.lms.permissions import can_access_lesson, get_locked_lessons

		parts = self.path.strip("/").split("/")
		# scorm/<course>/<title>/...
		if len(parts) < 3 or parts[0] != "scorm":
			raise frappe.PermissionError
		course, title = unquote(parts[1]), unquote(parts[2])

		# Keyed on the session user: an allow is that learner's alone, never shared.
		cache_key = f"lms-scorm-access:{frappe.session.user}:{course}:{title}"
		if frappe.cache().get_value(cache_key):
			return

		chapter = frappe.db.get_value(
			"Course Chapter",
			{"course": course, "title": title, "is_scorm_package": 1},
			"name",
		)
		if not chapter:
			raise frappe.PermissionError

		# SCORM chapters are created with exactly one lesson (upsert_chapter invariant
		# in api.py). order_by keeps the access check deterministic if that ever changes.
		lesson = frappe.db.get_value("Lesson Reference", {"parent": chapter}, "lesson", order_by="idx asc")
		# can_access_lesson answers "is this course yours or are you enrolled", which is
		# lock-unaware. Sequential courses gate the bytes too, otherwise the SCORM page
		# is a route around the gate that never touches get_lesson.
		if not lesson or not can_access_lesson(lesson) or lesson in get_locked_lessons(course):
			frappe.logger("lms.security").warning(
				"SCORM resource access denied: user=%s path=%s",
				frappe.session.user,
				self.path,
			)
			raise frappe.PermissionError

		frappe.cache().set_value(cache_key, 1, expires_in_sec=SCORM_PERMISSION_TTL)

	def _is_safe_path(self, path):
		resolved = os.path.realpath(path)
		for base in self._DISK_ROOTS:
			scorm_root = os.path.realpath(os.path.join(frappe.local.site_path, base, "scorm"))
			if resolved == scorm_root or resolved.startswith(scorm_root + os.sep):
				return True
		return False

	def _serve_file(self, path):
		return _serve_scorm_file(path)

	def render(self):
		self._check_permission()
		# Try private/scorm first (new, gated), then public/scorm (legacy).
		for base in self._DISK_ROOTS:
			response = self._render_from_root(base)
			if response is not None:
				return response

	def _render_from_root(self, base):
		path = os.path.join(frappe.local.site_path, base, self.path.lstrip("/"))

		if not self._is_safe_path(path):
			raise frappe.PermissionError

		extension = os.path.splitext(path)[1]
		if not extension:
			path = f"{path}.html"

		# check if path exists and is actually a file and not a folder
		if os.path.exists(path) and os.path.isfile(path):
			return self._serve_file(path)
		else:
			path = path.replace(".html", "")
			if os.path.exists(path) and os.path.isdir(path):
				index_path = os.path.join(path, "index.html")
				if os.path.exists(index_path):
					return self._serve_file(index_path)
			elif not os.path.exists(path):
				chapter_folder = "/".join(self.path.split("/")[:3])
				chapter_folder_path = os.path.realpath(frappe.get_site_path(base, chapter_folder))
				file = path.split("/")[-1]
				correct_file_path = None

				if not self._is_safe_path(chapter_folder_path):
					raise frappe.PermissionError

				for root, _dirs, files in os.walk(chapter_folder_path):
					if file in files:
						correct_file_path = os.path.join(root, file)
						break

				if correct_file_path and self._is_safe_path(correct_file_path):
					return self._serve_file(correct_file_path)
		return None


class LessonSCORMRenderer(BaseRenderer):
	"""Serves a SCORM package embedded as a lesson editor block (Scorm tool,
	alongside Quiz/Assignment/Programming Exercise), as opposed to the
	whole-chapter-is-a-SCORM-package flow SCORMRenderer above handles.

	A separate class rather than folding this into SCORMRenderer: this path's
	permission check maps straight onto a single Course Lesson (no "which
	lesson does this chapter's SCORM package belong to" indirection), and
	keeping it separate means the existing class above needed zero changes —
	its own tests and legacy public/scorm fallback are untouched.

	URL shape: scorm-lesson/<course>/<lesson>/... — "scorm-lesson/" is not a
	substring of "scorm/", so SCORMRenderer.can_render() never matches these
	paths and this class never matches chapter ones; the two coexist without
	either needing to know the other exists.
	"""

	def can_render(self):
		return "scorm-lesson/" in self.path

	def _check_permission(self):
		from lms.lms.permissions import can_access_lesson, get_locked_lessons, resolve_lesson_name

		parts = self.path.strip("/").split("/")
		# scorm-lesson/<course>/<lesson>/...
		if len(parts) < 3 or parts[0] != "scorm-lesson":
			raise frappe.PermissionError
		course, lesson = unquote(parts[1]), unquote(parts[2])

		# Keyed on the session user: an allow is that learner's alone, never shared.
		cache_key = f"lms-scorm-lesson-access:{frappe.session.user}:{course}:{lesson}"
		if frappe.cache().get_value(cache_key):
			return

		# The URL carries the lesson name the package was uploaded under, which may since
		# have been renamed ("<n> Untitled lesson" -> its real title); permissions are
		# checked against the lesson as it exists now.
		lesson = resolve_lesson_name(course, lesson)
		if not lesson:
			raise frappe.PermissionError

		# Same rule as the chapter path: can_access_lesson alone is lock-unaware,
		# so a sequential/drip-gated lesson still needs the explicit lock check
		# or this route reads the SCORM bytes before the lesson itself opens.
		if not can_access_lesson(lesson) or lesson in get_locked_lessons(course):
			frappe.logger("lms.security").warning(
				"Lesson SCORM resource access denied: user=%s path=%s",
				frappe.session.user,
				self.path,
			)
			raise frappe.PermissionError

		frappe.cache().set_value(cache_key, 1, expires_in_sec=SCORM_PERMISSION_TTL)

	def _is_safe_path(self, path):
		resolved = os.path.realpath(path)
		scorm_root = os.path.realpath(os.path.join(frappe.local.site_path, "private", "scorm-lesson"))
		return resolved == scorm_root or resolved.startswith(scorm_root + os.sep)

	def _serve_file(self, path):
		return _serve_scorm_file(path)

	def render(self):
		self._check_permission()
		path = os.path.join(frappe.local.site_path, "private", self.path.lstrip("/"))

		if not self._is_safe_path(path):
			raise frappe.PermissionError

		extension = os.path.splitext(path)[1]
		if not extension:
			path = f"{path}.html"

		if os.path.exists(path) and os.path.isfile(path):
			return self._serve_file(path)

		path = path.replace(".html", "")
		if os.path.exists(path) and os.path.isdir(path):
			index_path = os.path.join(path, "index.html")
			if os.path.exists(index_path):
				return self._serve_file(index_path)
			return None

		# Fall back to a search within the lesson's own extracted folder, same
		# as SCORMRenderer does for a SCORM package's internal asset paths.
		lesson_folder = "/".join(self.path.split("/")[:3])
		lesson_folder_path = os.path.realpath(frappe.get_site_path("private", lesson_folder))
		if not self._is_safe_path(lesson_folder_path):
			raise frappe.PermissionError

		file = path.split("/")[-1]
		for root, _dirs, files in os.walk(lesson_folder_path):
			if file in files:
				candidate = os.path.join(root, file)
				if self._is_safe_path(candidate):
					return self._serve_file(candidate)
				break
		return None
