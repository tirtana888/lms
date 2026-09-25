"""Pure helpers for member tags.

Frappe keeps a document's tags in one comma-separated column (`_user_tags`,
stored as ",a,b"). Nothing here imports frappe, so the parsing and counting
rules can be unit-tested anywhere.
"""

from collections import Counter

TAG_MAX_LENGTH = 50
MAX_BULK_MEMBERS = 500


class InvalidTag(ValueError):
	"""`str(exc)` is one of: empty, comma, too_long."""


def normalize_tag(raw) -> str:
	"""Trim and collapse whitespace; reject what the `_user_tags` format cannot hold.

	A comma would silently split one tag into two, so it is refused outright.
	"""
	tag = " ".join(str(raw or "").split())
	if not tag:
		raise InvalidTag("empty")
	if "," in tag:
		raise InvalidTag("comma")
	if len(tag) > TAG_MAX_LENGTH:
		raise InvalidTag("too_long")
	return tag


def parse_tags(raw) -> list[str]:
	"""",a,b" -> ["a", "b"] (order kept, blanks dropped)."""
	return [tag.strip() for tag in (raw or "").split(",") if tag.strip()]


def same_tag(a: str, b: str) -> bool:
	return (a or "").strip().casefold() == (b or "").strip().casefold()


def dedupe_tags(tags) -> list[str]:
	"""Drop repeats that differ only by letter case; the first spelling wins."""
	unique: list[str] = []
	for tag in tags:
		if tag and not any(same_tag(tag, seen) for seen in unique):
			unique.append(tag)
	return unique


def tag_counts(raw_values) -> list[tuple[str, int]]:
	"""Members per tag, from every member's raw `_user_tags` value.

	Tags are grouped ignoring letter case; the spelling shown is the one most
	members use. Sorted by count (high first), then name.
	"""
	spellings: dict[str, Counter] = {}
	members: Counter = Counter()
	for raw in raw_values:
		# a member carrying "a" and "A" still counts once
		for tag in dedupe_tags(parse_tags(raw)):
			key = tag.casefold()
			members[key] += 1
			spellings.setdefault(key, Counter())[tag] += 1

	rows = [(spellings[key].most_common(1)[0][0], count) for key, count in members.items()]
	return sorted(rows, key=lambda row: (-row[1], row[0].casefold()))


def users_with_tag(rows, tag: str) -> list[str]:
	"""Names whose raw `_user_tags` holds `tag` exactly (ignoring letter case).

	`rows` is [(name, raw_user_tags)]. A SQL LIKE cannot do this on its own:
	"Beasiswa" would also match "Beasiswa Plus".
	"""
	return [name for name, raw in rows if any(same_tag(t, tag) for t in parse_tags(raw))]


def format_tags(tags) -> str:
	"""["a", "b"] -> ",a,b" (empty string for no tags), as Frappe stores it."""
	tags = dedupe_tags(tags)
	return "," + ",".join(tags) if tags else ""
