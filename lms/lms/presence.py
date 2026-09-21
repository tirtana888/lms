"""Live presence and daily study time: who has the LMS open in a visible browser tab.

`User.last_active` and the login log only move when a browser makes a request, so a
student watching a video or reading an already-loaded page looks offline after a few
minutes. Instead the frontend sends a small heartbeat (`ping`) every ~30 seconds from
each visible tab, and a user counts as present until PRESENCE_TTL_SECONDS pass without one.

Live state (who is here, since when, where) lives only in Redis: a sorted set of
user -> last ping time, plus one short-lived key per user holding the details.

Study time is the sum of the gaps between consecutive pings inside one stay. It is
accumulated in a Redis hash on every ping (no database write), and `flush_pending`, run by
the scheduler every few minutes, adds the totals to one `LMS Study Day` row per user per day.
Reading "today" adds whatever has not been flushed yet, so the number is live.
"""

import json
import time
from datetime import datetime, timedelta

import frappe
from frappe import _

from lms.lms.utils import (
	PRIVILEGED_ROLES,
	has_course_instructor_role,
	has_evaluator_role,
	has_moderator_role,
)

# Three missed 30-second pings.
PRESENCE_TTL_SECONDS = 90
MAX_TRACKED_USERS = 5000
MAX_LISTED_USERS = 50
MAX_FIELD_LENGTH = 140
MAX_HISTORY_DAYS = 90
IGNORED_USERS = ("Administrator", "Guest")

_INDEX_KEY = "lms_presence"
_PENDING_KEY = "lms_presence_pending"


def _text(value) -> str | None:
	if not isinstance(value, str):
		return None
	value = value.strip()[:MAX_FIELD_LENGTH]
	return value or None


def _index_key(cache) -> str:
	return cache.make_key(_INDEX_KEY)


def _detail_key(cache, user: str) -> str:
	return cache.make_key(f"{_INDEX_KEY}:{user}")


def _pending_key(cache) -> str:
	return cache.make_key(_PENDING_KEY)


def _number(value):
	return value if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def _previous(cache, user: str) -> dict | None:
	"""The user's record if their last ping is still inside the TTL, else None."""
	raw = cache.get(_detail_key(cache, user))
	if raw is None:
		return None
	try:
		detail = json.loads(raw)
	except (TypeError, ValueError):
		return None
	return detail if isinstance(detail, dict) else None


def _day_of(now_ts: float) -> str:
	return datetime.fromtimestamp(now_ts).date().isoformat()


def record_ping(
	cache,
	user: str,
	page: str | None,
	course: str | None,
	is_staff: bool,
	now_ts: float,
	day: str | None = None,
):
	"""Mark `user` as present at `now_ts` and credit the time since their previous ping.

	`since` is when the current stay began: it carries over while pings keep arriving inside
	the TTL and restarts after a longer gap (tab closed, hidden or offline). The time between
	two pings of one stay is study time; the first ping of a stay credits nothing, and two
	tabs never double count because the gaps between consecutive pings simply add up.
	"""
	day = day or _day_of(now_ts)
	previous = _previous(cache, user)
	last = _number(previous.get("last")) if previous else None
	since = _number(previous.get("since")) if previous else None
	continuing = last is not None and since is not None and 0 <= now_ts - last <= PRESENCE_TTL_SECONDS

	if continuing:
		credited = int(now_ts - last)
		if credited:
			cache.hincrby(_pending_key(cache), f"{day}|{user}|s", credited)
	else:
		since = now_ts
		cache.hincrby(_pending_key(cache), f"{day}|{user}|n", 1)

	detail = {
		"page": _text(page),
		"course": _text(course),
		"staff": bool(is_staff),
		"since": since,
		"last": now_ts,
	}
	cache.zadd(_index_key(cache), {user: now_ts})
	cache.setex(name=_detail_key(cache, user), time=PRESENCE_TTL_SECONDS, value=json.dumps(detail))


def read_present(cache, now_ts: float) -> list[dict]:
	"""Everyone whose last ping is within the TTL, with where they are."""
	index = _index_key(cache)
	cache.zremrangebyscore(index, "-inf", now_ts - PRESENCE_TTL_SECONDS)
	users = [u.decode() if isinstance(u, bytes) else u for u in cache.zrange(index, 0, MAX_TRACKED_USERS - 1)]
	if not users:
		return []

	present = []
	for user, raw in zip(users, cache.mget([_detail_key(cache, u) for u in users])):
		if raw is None:
			# The per-user key already expired: the ping is too old to count.
			continue
		try:
			detail = json.loads(raw)
		except (TypeError, ValueError):
			continue
		present.append({"user": user, **detail})
	return present


def summarize(present: list[dict]) -> dict:
	"""Counts for the dashboard: learners vs. staff, and where the learners are."""
	learners = [p for p in present if not p.get("staff")]
	by_course: dict[str, int] = {}
	for p in learners:
		if p.get("course"):
			by_course[p["course"]] = by_course.get(p["course"], 0) + 1
	return {
		"learners": len(learners),
		"staff": len(present) - len(learners),
		"on_course_pages": sum(by_course.values()),
		"by_course": sorted(by_course.items(), key=lambda kv: (-kv[1], kv[0])),
	}


# ---------------------------------------------------------------------------------------------
# Daily study time
# ---------------------------------------------------------------------------------------------


def parse_pending(raw: dict) -> dict[tuple[str, str], dict[str, int]]:
	"""{b"2026-09-21|a@x.id|s": b"120", ...} -> {("2026-09-21", "a@x.id"): {"seconds": 120, "sessions": 1}}."""
	totals: dict[tuple[str, str], dict[str, int]] = {}
	for field, value in raw.items():
		field = field.decode() if isinstance(field, bytes) else field
		day, sep, rest = field.partition("|")
		user, sep2, kind = rest.rpartition("|")
		if not sep or not sep2 or kind not in ("s", "n"):
			continue
		try:
			amount = int(value)
		except (TypeError, ValueError):
			continue
		if amount <= 0:
			continue
		row = totals.setdefault((day, user), {"seconds": 0, "sessions": 0})
		row["seconds" if kind == "s" else "sessions"] += amount
	return totals


def _apply_day_total(day: str, user: str, seconds: int, sessions: int):
	name = frappe.db.get_value("LMS Study Day", {"member": user, "date": day})
	if name:
		frappe.db.sql(
			"UPDATE `tabLMS Study Day` SET seconds = seconds + %s, sessions = sessions + %s WHERE name = %s",
			(seconds, sessions, name),
		)
	else:
		frappe.get_doc(
			{
				"doctype": "LMS Study Day",
				"member": user,
				"date": day,
				"seconds": seconds,
				"sessions": sessions,
			}
		).insert(ignore_permissions=True, ignore_links=True)


def flush_pending(cache=None, apply=None) -> int:
	"""Scheduler job: move the counters accumulated in Redis into `LMS Study Day`.

	The hash is renamed first (atomic), so pings that arrive meanwhile start a fresh one and
	nothing is counted twice. A row that fails to save is added back to be retried next time.
	Returns the number of user-days written.
	"""
	cache = cache or frappe.cache()
	apply = apply or _apply_day_total
	pending = _pending_key(cache)
	taking = cache.make_key(f"{_PENDING_KEY}:flushing:{int(time.time() * 1000)}")
	try:
		cache.rename(pending, taking)
	except Exception:
		return 0  # nothing pending

	raw = cache.execute_command("HGETALL", taking)
	cache.delete(taking)

	written = 0
	for (day, user), row in parse_pending(raw).items():
		try:
			apply(day, user, row["seconds"], row["sessions"])
			written += 1
		except Exception:
			frappe.log_error(title="LMS study time flush failed")
			if row["seconds"]:
				cache.hincrby(pending, f"{day}|{user}|s", row["seconds"])
			if row["sessions"]:
				cache.hincrby(pending, f"{day}|{user}|n", row["sessions"])
	return written


def pending_seconds(cache, day: str, users: list[str]) -> dict[str, int]:
	"""Study seconds recorded today that the scheduler has not yet flushed to the database."""
	if not users:
		return {}
	values = cache.hmget(_pending_key(cache), [f"{day}|{u}|s" for u in users])
	out = {}
	for user, value in zip(users, values):
		try:
			out[user] = int(value) if value is not None else 0
		except (TypeError, ValueError):
			out[user] = 0
	return out


def day_series(rows: dict[str, int], today: str, days: int) -> list[dict]:
	"""One entry per day for the last `days` days ending today, zero for days with no record."""
	end = datetime.strptime(today, "%Y-%m-%d").date()
	series = []
	for offset in range(days - 1, -1, -1):
		day = (end - timedelta(days=offset)).isoformat()
		series.append({"date": day, "seconds": rows.get(day, 0)})
	return series


def _is_dashboard_audience() -> bool:
	return bool(
		has_moderator_role()
		or has_course_instructor_role()
		or has_evaluator_role()
		or "System Manager" in frappe.get_roles()
	)


@frappe.whitelist(methods=["POST"])
def ping(page: str = None, course: str = None):
	"""Heartbeat from an open, visible LMS tab. Cheap by design: Redis only, no DB writes."""
	user = frappe.session.user
	if user in IGNORED_USERS:
		return {"tracked": False}
	is_staff = bool(PRIVILEGED_ROLES.intersection(frappe.get_roles(user)))
	record_ping(frappe.cache(), user, page, course, is_staff, time.time(), frappe.utils.nowdate())
	return {"tracked": True}


@frappe.whitelist()
def get_active_now():
	"""Learners with the LMS open right now, for the admin dashboard (same audience as the rest of it)."""
	if not _is_dashboard_audience():
		frappe.throw(_("You are not permitted to view this dashboard."), frappe.PermissionError)

	cache = frappe.cache()
	now_ts = time.time()
	present = read_present(cache, now_ts)
	summary = summarize(present)

	course_names = {p["course"] for p in present if p.get("course")}
	titles = {}
	if course_names:
		titles = {
			row.name: row.title
			for row in frappe.get_all("LMS Course", {"name": ["in", list(course_names)]}, ["name", "title"])
		}

	people = {}
	today_seconds = {}
	shown = sorted(present, key=lambda p: p.get("since") or 0, reverse=True)[:MAX_LISTED_USERS]
	if shown:
		names = [p["user"] for p in shown]
		today = frappe.utils.nowdate()
		people = {
			row.name: row
			for row in frappe.get_all("User", {"name": ["in", names]}, ["name", "full_name", "user_image"])
		}
		saved = {
			row.member: row.seconds
			for row in frappe.get_all(
				"LMS Study Day", {"member": ["in", names], "date": today}, ["member", "seconds"]
			)
		}
		waiting = pending_seconds(cache, today, names)
		today_seconds = {u: int(saved.get(u) or 0) + waiting.get(u, 0) for u in names}

	return {
		"learners": summary["learners"],
		"staff": summary["staff"],
		"elsewhere": summary["learners"] - summary["on_course_pages"],
		"courses": [
			{"course": name, "title": titles.get(name) or name, "count": count}
			for name, count in summary["by_course"]
		],
		"users": [
			describe_user(p, people.get(p["user"]), titles, now_ts, today_seconds.get(p["user"], 0))
			for p in shown
		],
		"window_seconds": PRESENCE_TTL_SECONDS,
		"as_of": frappe.utils.now_datetime().isoformat(),
	}


def describe_user(entry: dict, person, titles: dict, now_ts: float, today_seconds: int = 0) -> dict:
	"""One row of the dashboard list: who, where, since when, for how long, and today's total."""
	since = entry.get("since") or now_ts
	course = entry.get("course")
	return {
		"user": entry["user"],
		"full_name": (person.full_name if person else None) or entry["user"],
		"user_image": person.user_image if person else None,
		"staff": bool(entry.get("staff")),
		"course": course,
		"course_title": (titles.get(course) or course) if course else None,
		"since": since,
		"online_seconds": max(0, int(now_ts - since)),
		"today_seconds": max(0, int(today_seconds)),
	}


@frappe.whitelist()
def get_study_time(member: str, days: int = 30):
	"""Daily study time of one member: for staff, or for the member themselves."""
	if member != frappe.session.user and not _is_dashboard_audience():
		frappe.throw(_("You are not permitted to view this."), frappe.PermissionError)

	days = max(1, min(int(days or 30), MAX_HISTORY_DAYS))
	today = frappe.utils.nowdate()
	start = frappe.utils.add_days(today, -(days - 1))

	saved = frappe.get_all(
		"LMS Study Day",
		{"member": member, "date": ["between", [start, today]]},
		["date", "seconds", "sessions"],
	)
	by_day = {str(row.date): int(row.seconds or 0) for row in saved}
	by_day[today] = by_day.get(today, 0) + pending_seconds(frappe.cache(), today, [member]).get(member, 0)
	series = day_series(by_day, today, days)

	lifetime = frappe.db.sql(
		"SELECT COALESCE(SUM(seconds), 0), COUNT(*) FROM `tabLMS Study Day` WHERE member = %s AND seconds > 0",
		(member,),
	)[0]
	return {
		"days": series,
		"today_seconds": by_day[today],
		"last_7_days_seconds": sum(d["seconds"] for d in series[-7:]),
		"period_seconds": sum(d["seconds"] for d in series),
		"active_days": sum(1 for d in series if d["seconds"] > 0),
		"total_seconds": int(lifetime[0]) + pending_seconds(frappe.cache(), today, [member]).get(member, 0),
		"total_days": int(lifetime[1]),
	}
