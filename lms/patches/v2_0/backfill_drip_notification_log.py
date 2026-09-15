from lms.lms.drip_notifications import backfill_existing_unlocks


def execute():
	"""Run once, before send_drip_unlock_notifications ever fires for real
	(see backfill_existing_unlocks' own docstring) - marks every already-
	unlocked chapter/quiz/assignment as already notified for every currently
	enrolled student, so day one of this feature doesn't email the entire
	student body about content most of them unlocked (and likely already
	saw) long before this feature existed.
	"""
	backfill_existing_unlocks()
