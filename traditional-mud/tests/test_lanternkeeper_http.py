"""Local-only HTTP security regression tests; no Stripe requests."""
import http.client
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mud.database import Database
from mud.lanternkeeper_http import start_lanternkeeper_http


class LanternkeeperHTTPTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = Database(Path(self.tmp.name) / "game.db")
        with self.db.connect() as conn:
            conn.execute("INSERT INTO accounts(name,password_hash) VALUES('alpha','test')")
            conn.execute("INSERT INTO accounts(name,password_hash) VALUES('beta','test')")
        self.env = patch.dict(os.environ, {"DOTF_BILLING_ORIGIN": "https://mud.lvthn.io"})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.db_patch = patch("mud.lanternkeeper_http.Database", return_value=self.db)
        self.db_patch.start()
        self.addCleanup(self.db_patch.stop)
        self.server = start_lanternkeeper_http(port=0)
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)

    def post(self, path, body, origin="https://mud.lvthn.io"):
        conn = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=3)
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        if origin is not None:
            headers["Origin"] = origin
        conn.request("POST", path, body, headers)
        response = conn.getresponse()
        status = response.status
        response.read()
        conn.close()
        return status

    def test_cross_origin_credentials_rejected(self):
        self.assertEqual(
            self.post("/lanternkeeper/checkout", "account=alpha&password=wrong", origin="https://attacker.test"),
            403,
        )

    def test_oversized_body_rejected(self):
        self.assertEqual(self.post("/lanternkeeper/checkout", "x" * 65537), 413)

    def test_failed_attempts_do_not_block_different_account(self):
        with patch("mud.lanternkeeper_http.verify_password", return_value=False):
            for _ in range(5):
                self.assertEqual(
                    self.post("/lanternkeeper/checkout", "account=alpha&password=wrong"), 401
                )
            self.assertEqual(self.post("/lanternkeeper/checkout", "account=alpha&password=wrong"), 429)
            self.assertEqual(self.post("/lanternkeeper/checkout", "account=beta&password=wrong"), 401)

    def test_unknown_path_rejected(self):
        self.assertEqual(self.post("/lanternkeeper/not-a-route", ""), 404)


if __name__ == "__main__":
    unittest.main()
