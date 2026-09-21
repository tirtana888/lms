import json
import unittest

from lms.lms.presence import (
	MAX_FIELD_LENGTH,
	PRESENCE_TTL_SECONDS,
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
		self.assertEqual(json.loads(raw), {"page": "CourseDetail", "course": "ekonomi", "staff": False})


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
