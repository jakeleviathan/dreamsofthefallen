from __future__ import annotations

import unittest

from mud.corpse_loot import NAMED_CORPSE_TTL_SECONDS, REGULAR_CORPSE_TTL_SECONDS


class CorpseDecayDurationTests(unittest.TestCase):
    def test_regular_and_named_default_durations(self):
        self.assertEqual(REGULAR_CORPSE_TTL_SECONDS, 300)
        self.assertEqual(NAMED_CORPSE_TTL_SECONDS, 900)


if __name__ == "__main__":
    unittest.main()
