from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path


class StyleLoginCopyTests(unittest.TestCase):
    def test_production_removes_style_announcement_without_disabling_style_runtime(self):
        root = Path(__file__).resolve().parents[1]
        code = r'''
import server

assert server.PlayerSession._style_collectibles_runtime_installed
assert getattr(server.PlayerSession, "_style_login_announcement_removed", False)
print("STYLE_LOGIN_COPY_OK")
'''
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=root,
            text=True,
            capture_output=True,
            env={**os.environ, "PYTHONPATH": str(root)},
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertIn("STYLE_LOGIN_COPY_OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
