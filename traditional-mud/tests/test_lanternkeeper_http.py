"""Local-only HTTP security regression tests; no Stripe requests."""
import http.client
import json
import time
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

    def post(self, path, body, origin="https://mud.lvthn.io", client_ip="192.0.2.10", forwarded_for=None, return_location=False):
        conn = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=3)
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        if client_ip is not None:
            headers["X-Lanternkeeper-Client-IP"] = client_ip
        if forwarded_for is not None:
            headers["X-Forwarded-For"] = forwarded_for
        if origin is not None:
            headers["Origin"] = origin
        conn.request("POST", path, body, headers)
        response = conn.getresponse()
        status = response.status
        location = response.getheader("Location")
        response.read()
        conn.close()
        return (status, location) if return_location else status

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

    def test_missing_trusted_proxy_header_fails_closed(self):
        self.assertEqual(
            self.post("/lanternkeeper/checkout", "account=alpha&password=wrong",
                      client_ip=None, forwarded_for="198.51.100.10"),
            503,
        )

    def test_spoofed_forwarding_header_does_not_bypass_ip_limit(self):
        with patch("mud.lanternkeeper_http.verify_password", return_value=False):
            for i in range(50):
                self.assertEqual(
                    self.post("/lanternkeeper/checkout",
                              "account=missing%d&password=wrong" % i,
                              forwarded_for="198.51.100.%d" % ((i % 100) + 1)),
                    401,
                )
            self.assertEqual(
                self.post("/lanternkeeper/checkout", "account=beta&password=wrong",
                          forwarded_for="198.51.100.250"),
                429,
            )
            self.assertEqual(
                self.post("/lanternkeeper/checkout", "account=beta&password=wrong",
                          client_ip="192.0.2.11", forwarded_for="192.0.2.10"),
                401,
            )

    def test_authenticated_checkout_redirect_uses_server_generated_url(self):
        with patch("mud.lanternkeeper_http.verify_password", return_value=True):
            with patch("mud.lanternkeeper_http.create_checkout",
                       return_value="https://checkout.stripe.com/c/pay/mock"):
                status, location = self.post(
                    "/lanternkeeper/checkout", "account=alpha&password=correct",
                    return_location=True,
                )
                self.assertEqual(status, 303)
                self.assertEqual(location, "https://checkout.stripe.com/c/pay/mock")

    def test_unsigned_stripe_webhook_returns_400(self):
        fake_event = {
            "id": "evt_unsigned", "created": int(time.time()),
            "type": "customer.subscription.created",
            "data": {"object": {"id": "sub_unsigned", "status": "active"}},
        }
        with patch.dict(os.environ, {"DOTF_STRIPE_WEBHOOK_SECRET": "whsec_offline_test"}):
            status = self.post(
                "/lanternkeeper/webhook", json.dumps(fake_event), origin=None
            )
            self.assertEqual(status, 400)

    def test_unknown_path_rejected(self):
        self.assertEqual(self.post("/lanternkeeper/not-a-route", ""), 404)


if __name__ == "__main__":
    unittest.main()
