import tempfile
import unittest
from pathlib import Path

from mud.database import Database
from mud.vote_rewards import (
    VOTE_ECHO_REWARD,
    VOTE_SPARK_REWARD,
    _account_status,
    _create_pending_claim,
    _grant_manual_echoes,
    _grant_manual_vote,
    _ingest_observation,
    _profile,
    _resolve_unlock,
    _set_profile_field,
    allocate_pending_claims,
    buy_echo_item,
    ensure_vote_schema,
)


class VoteRewardTests(unittest.TestCase):
    def _world(self):
        temp = tempfile.TemporaryDirectory()
        db = Database(Path(temp.name) / "vote.sqlite3")
        ensure_vote_schema(db)
        admin = db.create_account("vote_admin", "x")
        first = db.create_account("voter_one", "x")
        second = db.create_account("voter_two", "x")
        first_char = db.create_character(first.id, "Votera", "human", "wizard")
        first_alt = db.create_character(first.id, "VoteraAlt", "goblin", "priest")
        second_char = db.create_character(second.id, "Voterb", "dwarf", "brute")
        return temp, db, admin, first, second, first_char, first_alt, second_char

    def test_first_month_observation_is_baseline_not_free_votes(self):
        temp, db, *_ = self._world()
        self.addCleanup(temp.cleanup)

        created = _ingest_observation(db, "2026-09", 10, 100)
        self.assertEqual(created, 0)
        with db.connect() as conn:
            count = conn.execute("SELECT COUNT(*) AS n FROM mudverse_vote_events").fetchone()["n"]
        self.assertEqual(count, 0)

        self.assertEqual(_ingest_observation(db, "2026-09", 11, 110), 1)
        with db.connect() as conn:
            row = conn.execute(
                "SELECT month_key, ordinal FROM mudverse_vote_events"
            ).fetchone()
        self.assertEqual((row["month_key"], row["ordinal"]), ("2026-09", 11))

    def test_one_increment_can_only_reward_one_pending_claim(self):
        temp, db, _admin, first, second, first_char, _alt, second_char = self._world()
        self.addCleanup(temp.cleanup)

        _ingest_observation(db, "2026-09", 5, 100)
        self.assertEqual(_create_pending_claim(db, first.id, first_char.id, 5, now=101)[0], "created")
        self.assertEqual(_create_pending_claim(db, second.id, second_char.id, 5, now=102)[0], "created")
        _ingest_observation(db, "2026-09", 6, 103)

        awards = allocate_pending_claims(db, now=104)
        self.assertEqual(len(awards), 1)
        self.assertEqual(awards[0]["account_id"], first.id)
        self.assertEqual(_account_status(db, first.id)["lifetime"], 1)
        self.assertEqual(_account_status(db, second.id)["lifetime"], 0)

        awards_again = allocate_pending_claims(db, now=105)
        self.assertEqual(awards_again, [])

    def test_fifo_two_events_reward_two_accounts_in_order(self):
        temp, db, _admin, first, second, first_char, _alt, second_char = self._world()
        self.addCleanup(temp.cleanup)

        _ingest_observation(db, "2026-09", 20, 100)
        _create_pending_claim(db, first.id, first_char.id, 20, now=101)
        _create_pending_claim(db, second.id, second_char.id, 20, now=102)
        _ingest_observation(db, "2026-09", 22, 103)

        awards = allocate_pending_claims(db, now=104)
        self.assertEqual([row["account_id"] for row in awards], [first.id, second.id])

    def test_vote_reward_is_account_wide_but_sparks_and_xp_go_to_claim_character(self):
        temp, db, _admin, first, _second, first_char, first_alt, _second_char = self._world()
        self.addCleanup(temp.cleanup)

        _ingest_observation(db, "2026-09", 3, 100)
        _create_pending_claim(db, first.id, first_alt.id, 3, now=101)
        _ingest_observation(db, "2026-09", 4, 102)
        awards = allocate_pending_claims(db, now=103)
        self.assertEqual(len(awards), 1)

        status = _account_status(db, first.id)
        self.assertEqual(status["echoes"], VOTE_ECHO_REWARD)
        self.assertEqual(status["lifetime"], 1)
        self.assertEqual(db.get_sols(first_char.id), 0)
        self.assertEqual(db.get_sols(first_alt.id), VOTE_SPARK_REWARD)
        self.assertEqual(db.get_character_by_name(first_alt.name).experience, 5)

    def test_daily_cooldown_is_account_wide_across_alts(self):
        temp, db, _admin, first, _second, first_char, first_alt, _second_char = self._world()
        self.addCleanup(temp.cleanup)

        _ingest_observation(db, "2026-09", 8, 100)
        _create_pending_claim(db, first.id, first_char.id, 8, now=101)
        _ingest_observation(db, "2026-09", 9, 102)
        allocate_pending_claims(db, now=103)

        state, details = _create_pending_claim(db, first.id, first_alt.id, 9, now=104)
        self.assertEqual(state, "cooldown")
        self.assertGreater(details["remaining"], 0)

    def test_vote_count_correction_never_reissues_old_ordinals(self):
        temp, db, *_ = self._world()
        self.addCleanup(temp.cleanup)

        _ingest_observation(db, "2026-09", 10, 100)
        self.assertEqual(_ingest_observation(db, "2026-09", 11, 101), 1)
        self.assertEqual(_ingest_observation(db, "2026-09", 9, 102), 0)
        self.assertEqual(_ingest_observation(db, "2026-09", 11, 103), 0)
        self.assertEqual(_ingest_observation(db, "2026-09", 12, 104), 1)
        with db.connect() as conn:
            ordinals = [
                row["ordinal"]
                for row in conn.execute(
                    "SELECT ordinal FROM mudverse_vote_events ORDER BY ordinal"
                ).fetchall()
            ]
        self.assertEqual(ordinals, [11, 12])

    def test_five_lifetime_rewards_unlock_first_milestone_title(self):
        temp, db, admin, first, _second, first_char, _alt, _second_char = self._world()
        self.addCleanup(temp.cleanup)

        for index in range(5):
            _grant_manual_vote(
                db,
                first.id,
                first_char.id,
                admin.id,
                f"test correction {index}",
                now=100 + index,
            )

        status = _account_status(db, first.id)
        self.assertEqual(status["lifetime"], 5)
        key, error = _resolve_unlock(db, first.id, "The Heard", "title")
        self.assertIsNone(error)
        self.assertEqual(key, "title_the_heard")

    def test_echo_shop_unlocks_are_account_wide_and_profile_is_character_specific(self):
        temp, db, admin, first, _second, first_char, first_alt, _second_char = self._world()
        self.addCleanup(temp.cleanup)

        balance = _grant_manual_echoes(db, first.id, admin.id, 10, "test funds", now=100)
        self.assertEqual(balance, 10)
        state, balance = buy_echo_item(db, first.id, "cosmetic_silver_echo_sigil", now=101)
        self.assertEqual(state, "purchased")
        self.assertEqual(balance, 4)

        key, error = _resolve_unlock(db, first.id, "Silver Echo Sigil", "cosmetic")
        self.assertIsNone(error)
        self.assertEqual(key, "cosmetic_silver_echo_sigil")

        _set_profile_field(db, first_alt.id, "sigil_key", key, now=102)
        self.assertIsNone(_profile(db, first_char.id)["sigil_key"])
        self.assertEqual(_profile(db, first_alt.id)["sigil_key"], key)

    def test_manual_grants_require_auditable_rows(self):
        temp, db, admin, first, _second, first_char, _alt, _second_char = self._world()
        self.addCleanup(temp.cleanup)

        _grant_manual_vote(db, first.id, first_char.id, admin.id, "restore missed legitimate vote", now=100)
        _grant_manual_echoes(db, first.id, admin.id, 2, "customer service correction", now=101)
        with db.connect() as conn:
            actions = [
                row["action"]
                for row in conn.execute(
                    "SELECT action FROM vote_admin_audit ORDER BY id"
                ).fetchall()
            ]
        self.assertEqual(actions, ["manual_vote_grant", "manual_echo_grant"])


if __name__ == "__main__":
    unittest.main()
