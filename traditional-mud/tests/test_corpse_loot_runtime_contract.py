from __future__ import annotations

import unittest


class CorpseLootRuntimeContractTests(unittest.TestCase):
    def test_production_entrypoint_installs_corpse_runtime(self):
        import server

        self.assertTrue(getattr(server.PlayerSession, "_corpse_loot_runtime_installed", False))


if __name__ == "__main__":
    unittest.main()
