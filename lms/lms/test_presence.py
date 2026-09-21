import json
import unittest

from lms.lms.presence import (
	MAX_FIELD_LENGTH,
	PRESENCE_TTL_SECONDS,
	day_series,
	describe_user,
	flush_pending,
	parse_pending,
	pending_seconds,
	read_present,
	record_ping,
	summarize,
)


class FakeCache:
	"""The few Redis calls presence uses, with expiry evaluated against a settable clock."""

	def __init__(self):
		self.now = 0.0
		self.zsets: dict[str, dict[str, float]] = {}
		self.values: dict[str, tuple[str, float]] = {}
		self.hashes: dict[str, dict[str, int]] = {}

	def make_key(self, key):
		return f"site|{key}"

	def zadd(self, name, mapping):
		self.zsets.setdefault(name, {}).update(mapping)

	def zremrangebyscore(self, name, low, high):
		zset = self.zsets.get(name, {})
		for member in [m for m, s in zset.items() if s <= high]:
			del zset[member]

	def zrange(self, name, start, end):
		members = sorted(self.zsets.get(name, {}).items(), key=lambda kv: kv[1])
		return [m.encode() for m, _s in members][start : end + 1]

	def setex(self, name, time, value):
		self.values[name] = (value, self.now + time)

	def get(self, name):
		value = self.values.get(name)
		return value[0].encode() if value and value[1] > self.now else None

	def hincrby(self, name, field, amount):
		h = self.hashes.setdefault(name, {})
		h[field] = h.get(field, 0) + amount
		return h[field]

	def hmget(self, name, fields):
		h = self.hashes.get(name, {})
		return [str(h[f]).encode() if f in h else None for f in fields]

	def rename(self, src, dst):
		if src not in self.hashes:
			raise KeyError("no such key")
		self.hashes[dst] = self.hashes.pop(src)

	def execute_command(self, command, name):
		assert command == "HGETALL"
		return {f.encode(): str(v).encode() for f, v in self.hashes.get(name, {}).items()}

	def delete(self, name):
		self.hashes.pop(name, None)

	def mget(self, names):
		out = []
		for name in names:
			value = self.values.get(name)
			out.append(value[0].encode() if value and value[1] > self.now else None)
		return out


class TestPresence(unittest.TestCase):
	def setUp(self):
		self.cache = FakeCache()

	def ping(self, user, page="CourseDetail", course=None, staff=False):
		record_ping(self.cache, user, page, course, staff, self.cache.now)

	def users(self):
		return sorted(p["user"] for p in read_present(self.cache, self.cache.now))

	def test_ping_makes_user_present(self):
		self.ping("a@x.id")
		self.assertEqual(self.users(), ["a@x.id"])

	def test_user_drops_out_after_the_ttl(self):
		self.ping("a@x.id")
		self.cache.now += PRESENCE_TTL_SECONDS - 1
		self.assertEqual(self.users(), ["a@x.id"])
		self.cache.now += 2
		self.assertEqual(self.users(), [])

	def test_a_fresh_ping_keeps_the_user_present(self):
		self.ping("a@x.id")
		self.cache.now += 60
		self.ping("a@x.id")
		self.cache.now += 60
		self.assertEqual(self.users(), ["a@x.id"])

	def test_same_user_in_two_tabs_counts_once_at_the_latest_location(self):
		self.ping("a@x.id", course="ekonomi")
		self.ping("a@x.id", course="bahasa-inggris")
		present = read_present(self.cache, self.cache.now)
		self.assertEqual(len(present), 1)
		self.assertEqual(present[0]["course"], "bahasa-inggris")

	def test_expired_index_entries_are_pruned(self):
		self.ping("a@x.id")
		self.cache.now += PRESENCE_TTL_SECONDS + 5
		read_present(self.cache, self.cache.now)
		self.assertEqual(self.cache.zsets["site|lms_presence"], {})

	def test_entry_without_detail_is_not_counted(self):
		self.ping("a@x.id")
		self.cache.values.clear()
		self.assertEqual(self.users(), [])

	def test_corrupt_detail_is_skipped(self):
		self.ping("a@x.id")
		self.ping("b@x.id")
		self.cache.values["site|lms_presence:b@x.id"] = ("not json", self.cache.now + 50)
		self.assertEqual(self.users(), ["a@x.id"])

	def test_page_and_course_are_trimmed_and_type_checked(self):
		record_ping(self.cache, "a@x.id", "x" * 500, ["not", "a", "string"], False, 0)
		(entry,) = read_present(self.cache, 0)
		self.assertEqual(len(entry["page"]), MAX_FIELD_LENGTH)
		self.assertIsNone(entry["course"])

	def test_blank_strings_become_none(self):
		record_ping(self.cache, "a@x.id", "   ", "", False, 0)
		(entry,) = read_present(self.cache, 0)
		self.assertIsNone(entry["page"])
		self.assertIsNone(entry["course"])

	def test_detail_is_stored_as_json(self):
		self.ping("a@x.id", course="ekonomi")
		raw, _expires = self.cache.values["site|lms_presence:a@x.id"]
		self.assertEqual(
			json.loads(raw),
			{"page": "CourseDetail", "course": "ekonomi", "staff": False, "since": 0.0, "last": 0.0},
		)

	def since(self, user):
		return next(p["since"] for p in read_present(self.cache, self.cache.now) if p["user"] == user)

	def test_since_is_the_first_ping_of_the_stay(self):
		self.cache.now = 1000
		self.ping("a@x.id")
		self.assertEqual(self.since("a@x.id"), 1000)

	def test_since_survives_later_pings_while_the_stay_continues(self):
		self.cache.now = 1000
		self.ping("a@x.id")
		for _ in range(6):
			self.cache.now += 30
			self.ping("a@x.id")
		self.assertEqual(self.since("a@x.id"), 1000)

	def test_since_survives_a_change_of_page(self):
		self.cache.now = 1000
		self.ping("a@x.id", course="a")
		self.cache.now += 30
		self.ping("a@x.id", course="b")
		self.assertEqual(self.since("a@x.id"), 1000)

	def test_since_restarts_after_a_gap_longer_than_the_ttl(self):
		self.cache.now = 1000
		self.ping("a@x.id")
		self.cache.now += PRESENCE_TTL_SECONDS + 10
		self.ping("a@x.id")
		self.assertEqual(self.since("a@x.id"), 1000 + PRESENCE_TTL_SECONDS + 10)

	def test_a_missed_ping_inside_the_ttl_does_not_restart_the_stay(self):
		self.cache.now = 1000
		self.ping("a@x.id")
		self.cache.now += PRESENCE_TTL_SECONDS - 5
		self.ping("a@x.id")
		self.assertEqual(self.since("a@x.id"), 1000)

	def test_each_user_has_their_own_since(self):
		self.cache.now = 1000
		self.ping("a@x.id")
		self.cache.now = 1050
		self.ping("b@x.id")
		self.assertEqual((self.since("a@x.id"), self.since("b@x.id")), (1000, 1050))

	def test_old_records_without_since_are_treated_as_a_new_stay(self):
		self.cache.now = 1000
		self.cache.values["site|lms_presence:a@x.id"] = (json.dumps({"page": "x", "staff": False}), 1050)
		self.ping("a@x.id")
		self.assertEqual(self.since("a@x.id"), 1000)


class TestSummarize(unittest.TestCase):
	def test_staff_are_counted_apart_from_learners(self):
		out = summarize(
			[
				{"user": "s1", "course": "a", "staff": False},
				{"user": "s2", "course": None, "staff": False},
				{"user": "t1", "course": "a", "staff": True},
			]
		)
		self.assertEqual((out["learners"], out["staff"]), (2, 1))

	def test_courses_are_ranked_by_learner_count_then_name(self):
		present = [{"user": f"u{i}", "course": c, "staff": False} for i, c in enumerate("bbaacb")]
		self.assertEqual(summarize(present)["by_course"], [("b", 3), ("a", 2), ("c", 1)])

	def test_staff_do_not_inflate_course_counts(self):
		out = summarize([{"user": "t", "course": "a", "staff": True}])
		self.assertEqual(out["by_course"], [])
		self.assertEqual(out["on_course_pages"], 0)

	def test_learners_outside_course_pages_are_the_remainder(self):
		out = summarize(
			[
				{"user": "s1", "course": "a", "staff": False},
				{"user": "s2", "course": None, "staff": False},
			]
		)
		self.assertEqual(out["learners"] - out["on_course_pages"], 1)

	def test_nobody_present(self):
		self.assertEqual(
			summarize([]), {"learners": 0, "staff": 0, "on_course_pages": 0, "by_course": []}
		)


class Person:
	def __init__(self, full_name, user_image=None):
		self.full_name = full_name
		self.user_image = user_image


class TestDescribeUser(unittest.TestCase):
	def entry(self, **kw):
		return {"user": "a@x.id", "course": "ekonomi", "staff": False, "since": 1000, **kw}

	def test_reports_how_long_the_stay_has_lasted(self):
		row = describe_user(self.entry(), Person("Ayu", "/img.png"), {"ekonomi": "Ekonomi Kreatif"}, 1000 + 25 * 60)
		self.assertEqual(row["online_seconds"], 25 * 60)
		self.assertEqual(row["since"], 1000)
		self.assertEqual((row["full_name"], row["user_image"]), ("Ayu", "/img.png"))
		self.assertEqual(row["course_title"], "Ekonomi Kreatif")

	def test_falls_back_to_the_user_id_without_a_profile(self):
		self.assertEqual(describe_user(self.entry(), None, {}, 1100)["full_name"], "a@x.id")

	def test_falls_back_to_the_course_id_without_a_title(self):
		self.assertEqual(describe_user(self.entry(), None, {}, 1100)["course_title"], "ekonomi")

	def test_no_course_means_no_course_title(self):
		row = describe_user(self.entry(course=None), None, {}, 1100)
		self.assertIsNone(row["course_title"])

	def test_duration_never_goes_negative(self):
		self.assertEqual(describe_user(self.entry(since=2000), None, {}, 1000)["online_seconds"], 0)

	def test_missing_since_counts_as_just_arrived(self):
		row = describe_user(self.entry(since=None), None, {}, 5000)
		self.assertEqual((row["since"], row["online_seconds"]), (5000, 0))

	def test_staff_flag_is_carried(self):
		self.assertTrue(describe_user(self.entry(staff=True), None, {}, 1100)["staff"])


PENDING = "site|lms_presence_pending"
DAY = "2026-09-21"


class TestStudyTime(unittest.TestCase):
	def setUp(self):
		self.cache = FakeCache()

	def ping(self, user="a@x.id", at=None):
		if at is not None:
			self.cache.now = at
		record_ping(self.cache, user, "Lesson", None, False, self.cache.now, DAY)

	def totals(self, user="a@x.id"):
		h = self.cache.hashes.get(PENDING, {})
		return h.get(f"{DAY}|{user}|s", 0), h.get(f"{DAY}|{user}|n", 0)

	def test_first_ping_of_a_stay_credits_no_time_but_counts_a_session(self):
		self.ping(at=1000)
		self.assertEqual(self.totals(), (0, 1))

	def test_time_between_pings_of_one_stay_is_credited(self):
		for i in range(11):  # pings at 1000, 1030, ... 1300
			self.ping(at=1000 + 30 * i)
		self.assertEqual(self.totals(), (300, 1))

	def test_a_gap_longer_than_the_ttl_credits_nothing_and_starts_a_new_session(self):
		self.ping(at=1000)
		self.ping(at=1030)
		self.ping(at=1030 + PRESENCE_TTL_SECONDS + 60)
		self.assertEqual(self.totals(), (30, 2))

	def test_a_missed_ping_inside_the_ttl_is_still_credited(self):
		self.ping(at=1000)
		self.ping(at=1000 + 80)
		self.assertEqual(self.totals(), (80, 1))

	def test_two_tabs_do_not_double_count(self):
		# Two tabs ping alternately every 15 seconds each: one minute of wall time.
		for i in range(5):
			self.ping(at=1000 + 15 * i)
		self.assertEqual(self.totals(), (60, 1))

	def test_users_are_counted_separately(self):
		self.ping("a@x.id", at=1000)
		self.ping("b@x.id", at=1010)
		self.ping("a@x.id", at=1030)
		self.assertEqual(self.totals("a@x.id"), (30, 1))
		self.assertEqual(self.totals("b@x.id"), (0, 1))

	def test_the_day_passed_in_is_the_one_credited(self):
		record_ping(self.cache, "a@x.id", None, None, False, 1000, "2026-09-20")
		record_ping(self.cache, "a@x.id", None, None, False, 1030, "2026-09-21")
		h = self.cache.hashes[PENDING]
		self.assertEqual(h["2026-09-20|a@x.id|n"], 1)
		self.assertEqual(h["2026-09-21|a@x.id|s"], 30)

	def test_a_clock_that_goes_backwards_starts_a_new_stay_instead_of_crediting(self):
		self.ping(at=1000)
		self.ping(at=900)
		self.assertEqual(self.totals(), (0, 2))


class TestParsePending(unittest.TestCase):
	def test_groups_seconds_and_sessions_by_day_and_user(self):
		raw = {b"2026-09-21|a@x.id|s": b"300", b"2026-09-21|a@x.id|n": b"2", b"2026-09-20|b@x.id|s": b"45"}
		self.assertEqual(
			parse_pending(raw),
			{
				("2026-09-21", "a@x.id"): {"seconds": 300, "sessions": 2},
				("2026-09-20", "b@x.id"): {"seconds": 45, "sessions": 0},
			},
		)

	def test_ignores_malformed_fields_and_values(self):
		raw = {b"garbage": b"5", b"2026-09-21|a@x.id|x": b"5", b"2026-09-21|a@x.id|s": b"abc", b"2026-09-21|b@x.id|s": b"0"}
		self.assertEqual(parse_pending(raw), {})

	def test_a_pipe_inside_the_user_id_survives(self):
		self.assertEqual(
			parse_pending({b"2026-09-21|we|ird@x.id|s": b"9"}), {("2026-09-21", "we|ird@x.id"): {"seconds": 9, "sessions": 0}}
		)


class TestFlushPending(unittest.TestCase):
	def setUp(self):
		self.cache = FakeCache()
		self.saved = []

	def apply(self, day, user, seconds, sessions):
		self.saved.append((day, user, seconds, sessions))

	def fill(self):
		self.cache.hashes[PENDING] = {f"{DAY}|a@x.id|s": 120, f"{DAY}|a@x.id|n": 1, f"{DAY}|b@x.id|s": 30}

	def test_writes_each_user_day_once_and_empties_the_hash(self):
		self.fill()
		written = flush_pending(self.cache, self.apply)
		self.assertEqual(written, 2)
		self.assertCountEqual(self.saved, [(DAY, "a@x.id", 120, 1), (DAY, "b@x.id", 30, 0)])
		self.assertNotIn(PENDING, self.cache.hashes)
		self.assertFalse([k for k in self.cache.hashes if "flushing" in k])

	def test_nothing_pending_is_a_no_op(self):
		self.assertEqual(flush_pending(self.cache, self.apply), 0)
		self.assertEqual(self.saved, [])

	def test_a_second_flush_does_not_repeat_the_first(self):
		self.fill()
		flush_pending(self.cache, self.apply)
		flush_pending(self.cache, self.apply)
		self.assertEqual(len(self.saved), 2)

	def test_a_failed_row_is_kept_for_the_next_flush(self):
		self.fill()

		def flaky(day, user, seconds, sessions):
			if user == "a@x.id":
				raise RuntimeError("db down")
			self.saved.append((day, user, seconds, sessions))

		self.assertEqual(flush_pending(self.cache, flaky), 1)
		self.assertEqual(self.cache.hashes[PENDING], {f"{DAY}|a@x.id|s": 120, f"{DAY}|a@x.id|n": 1})
		self.assertEqual(flush_pending(self.cache, self.apply), 1)
		self.assertIn((DAY, "a@x.id", 120, 1), self.saved)

	def test_pings_arriving_during_a_flush_are_kept(self):
		self.fill()

		fired = []

		def apply_and_ping(day, user, seconds, sessions):
			if fired:
				return
			fired.append(True)
			record_ping(self.cache, "c@x.id", None, None, False, 5000, DAY)
			record_ping(self.cache, "c@x.id", None, None, False, 5030, DAY)

		flush_pending(self.cache, apply_and_ping)
		self.assertEqual(self.cache.hashes[PENDING][f"{DAY}|c@x.id|s"], 30)


class TestPendingSeconds(unittest.TestCase):
	def test_reads_unflushed_seconds_per_user(self):
		cache = FakeCache()
		cache.hashes[PENDING] = {f"{DAY}|a@x.id|s": 90}
		self.assertEqual(pending_seconds(cache, DAY, ["a@x.id", "b@x.id"]), {"a@x.id": 90, "b@x.id": 0})

	def test_no_users(self):
		self.assertEqual(pending_seconds(FakeCache(), DAY, []), {})


class TestDaySeries(unittest.TestCase):
	def test_has_one_entry_per_day_ending_today_with_zeros_for_gaps(self):
		out = day_series({"2026-09-21": 300, "2026-09-19": 60}, "2026-09-21", 4)
		self.assertEqual(
			out,
			[
				{"date": "2026-09-18", "seconds": 0},
				{"date": "2026-09-19", "seconds": 60},
				{"date": "2026-09-20", "seconds": 0},
				{"date": "2026-09-21", "seconds": 300},
			],
		)

	def test_crosses_a_month_boundary(self):
		out = day_series({}, "2026-10-02", 3)
		self.assertEqual([d["date"] for d in out], ["2026-09-30", "2026-10-01", "2026-10-02"])

	def test_describe_user_carries_todays_total(self):
		row = describe_user({"user": "a@x.id", "since": 1000}, None, {}, 1100, 7800)
		self.assertEqual(row["today_seconds"], 7800)
