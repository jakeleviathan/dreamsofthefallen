from __future__ import annotations

import unittest

from mud.corpse_loot import CORPSE_PROTECTION_SECONDS


class CorpseProtectionDurationTests(unittest.TestCase):
    def test_default_protection_window_is_sixty_seconds(self):
        self.assertEqual(CORPSE_PROTECTION_SECONDS, 60)


if __name__ == "__main__":
    unittest.main()
