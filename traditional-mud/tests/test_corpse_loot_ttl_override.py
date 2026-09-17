from __future__ import annotations

import unittest

from mud.combat import EnemyState, SEWER_RAT
from mud.corpse_loot import CORPSE_TTL_OVERRIDES, corpse_ttl_seconds_for, register_corpse_ttl


class CorpseLootTtlOverrideTests(unittest.TestCase):
    def test_content_can_override_corpse_lifetime_by_enemy_key(self):
        old = CORPSE_TTL_OVERRIDES.get("sewer_rat")
        try:
            register_corpse_ttl("sewer_rat", 42)
            self.assertEqual(corpse_ttl_seconds_for(EnemyState(SEWER_RAT)), 42.0)
        finally:
            if old is None:
                CORPSE_TTL_OVERRIDES.pop("sewer_rat", None)
            else:
                CORPSE_TTL_OVERRIDES["sewer_rat"] = old


if __name__ == "__main__":
    unittest.main()
