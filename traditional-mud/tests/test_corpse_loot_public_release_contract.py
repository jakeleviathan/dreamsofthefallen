from __future__ import annotations

import unittest

from mud.corpse_loot import CORPSE_PROTECTION_SECONDS


class CorpsePublicReleaseContractTests(unittest.TestCase):
    def test_public_release_follows_protection_window(self):
        self.assertGreater(CORPSE_PROTECTION_SECONDS, 0)


if __name__ == "__main__":
    unittest.main()
