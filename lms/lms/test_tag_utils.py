import unittest

from lms.lms.tag_utils import (
	TAG_MAX_LENGTH,
	InvalidTag,
	dedupe_tags,
	format_tags,
	normalize_tag,
	parse_tags,
	same_tag,
	tag_counts,
	users_with_tag,
)


class TestNormalizeTag(unittest.TestCase):
	def test_trims_and_collapses_whitespace(self):
		self.assertEqual(normalize_tag("  Magang   Taiwan "), "Magang Taiwan")

	def test_rejects_empty(self):
		for raw in ("", "   ", None):
			with self.assertRaises(InvalidTag) as ctx:
				normalize_tag(raw)
			self.assertEqual(str(ctx.exception), "empty")

	def test_rejects_comma(self):
		with self.assertRaises(InvalidTag) as ctx:
			normalize_tag("A,B")
		self.assertEqual(str(ctx.exception), "comma")

	def test_rejects_too_long(self):
		self.assertEqual(normalize_tag("x" * TAG_MAX_LENGTH), "x" * TAG_MAX_LENGTH)
		with self.assertRaises(InvalidTag) as ctx:
			normalize_tag("x" * (TAG_MAX_LENGTH + 1))
		self.assertEqual(str(ctx.exception), "too_long")


class TestParsing(unittest.TestCase):
	def test_parse_and_format_round_trip(self):
		self.assertEqual(parse_tags(",Beasiswa,Tritunggal"), ["Beasiswa", "Tritunggal"])
		self.assertEqual(format_tags(["Beasiswa", "Tritunggal"]), ",Beasiswa,Tritunggal")

	def test_empty_values(self):
		self.assertEqual(parse_tags(None), [])
		self.assertEqual(parse_tags(""), [])
		self.assertEqual(format_tags([]), "")

	def test_dedupe_ignores_case_and_keeps_first(self):
		self.assertEqual(dedupe_tags(["Beasiswa", "beasiswa", "Alumni"]), ["Beasiswa", "Alumni"])

	def test_same_tag(self):
		self.assertTrue(same_tag("Beasiswa", " beasiswa "))
		self.assertFalse(same_tag("Beasiswa", "Beasiswa Plus"))


class TestCounts(unittest.TestCase):
	def test_counts_members_not_occurrences(self):
		rows = [",Beasiswa,beasiswa", ",Beasiswa,Alumni", "", None, ",Alumni"]
		self.assertEqual(tag_counts(rows), [("Alumni", 2), ("Beasiswa", 2)])

	def test_sorted_by_count_then_name(self):
		rows = [",b", ",a", ",c,a"]
		self.assertEqual(tag_counts(rows), [("a", 2), ("b", 1), ("c", 1)])

	def test_most_common_spelling_wins(self):
		rows = [",alumni", ",Alumni", ",Alumni"]
		self.assertEqual(tag_counts(rows), [("Alumni", 3)])


class TestUsersWithTag(unittest.TestCase):
	def test_exact_match_not_substring(self):
		rows = [
			("a@x.com", ",Beasiswa"),
			("b@x.com", ",Beasiswa Plus"),
			("c@x.com", ",alumni,beasiswa"),
			("d@x.com", None),
		]
		self.assertEqual(users_with_tag(rows, "Beasiswa"), ["a@x.com", "c@x.com"])


if __name__ == "__main__":
	unittest.main()
