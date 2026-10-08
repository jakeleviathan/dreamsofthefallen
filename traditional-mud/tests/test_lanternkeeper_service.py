"""Smoke-test the standalone billing process without touching live services."""
import os
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path


class LanternkeeperServiceTests(unittest.TestCase):
    def test_staging_worker_starts_responds_and_stops(self):
        with tempfile.TemporaryDirectory() as directory:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.bind(("127.0.0.1", 0))
                port = sock.getsockname()[1]
            environment = os.environ.copy()
            environment.update({
                "DOTF_BILLING_ORIGIN": "https://mud.lvthn.io",
                "DOTF_BILLING_PORT": str(port),
                "MUD_DB_PATH": str(Path(directory) / "staging.sqlite3"),
            })
            environment.pop("DOTF_BILLING_ENABLED", None)
            environment.pop("STRIPE_SECRET_KEY", None)
            environment.pop("DOTF_STRIPE_WEBHOOK_SECRET", None)
            process = subprocess.Popen(
                [sys.executable, "-m", "mud.lanternkeeper_service"],
                cwd=Path(__file__).resolve().parents[1],
                env=environment,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            try:
                for _ in range(100):
                    if process.poll() is not None:
                        self.fail("Standalone billing worker exited before HTTP became ready")
                    try:
                        with urllib.request.urlopen(
                            f"http://127.0.0.1:{port}/lanternkeeper/", timeout=0.5
                        ) as response:
                            page = response.read().decode("utf-8")
                            self.assertEqual(response.status, 200)
                            self.assertIn("Lanternkeeper", page)
                            break
                    except (urllib.error.URLError, TimeoutError, ConnectionError):
                        time.sleep(0.05)
                else:
                    self.fail("Standalone billing worker did not become ready")
            finally:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
            self.assertEqual(process.returncode, 0)
            self.assertTrue((Path(directory) / "staging.sqlite3").exists())


if __name__ == "__main__":
    unittest.main()
