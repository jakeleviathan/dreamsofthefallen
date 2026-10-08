"""Lanternkeeper HTTPS-reverse-proxied billing routes.

Bind to loopback only. Publish /lanternkeeper/* through a TLS reverse proxy.
POST /lanternkeeper/checkout or /lanternkeeper/portal with form fields
account and password; POST /lanternkeeper/webhook with Stripe's raw payload.
"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit
import os
import threading

from mud.database import Database
from mud.security import verify_password
from mud.lanternkeeper_checkout import create_checkout, create_billing_portal
from mud.lanternkeeper_stripe import process_stripe_webhook

def start_lanternkeeper_http(host="127.0.0.1", port=8766):
    public_origin = os.environ.get("DOTF_BILLING_ORIGIN", "").rstrip("/")
    if not public_origin.startswith("https://") or urlsplit(public_origin).path not in ("", "/"):
        raise RuntimeError("DOTF_BILLING_ORIGIN must be an HTTPS origin")
    database = Database()

    class Handler(BaseHTTPRequestHandler):
        def reply(self, code, body):
            data = body.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_POST(self):
            path = urlsplit(self.path).path
            if path not in ("/lanternkeeper/webhook", "/lanternkeeper/checkout", "/lanternkeeper/portal"):
                return self.reply(404, "Not found")
            length = self.headers.get("Content-Length", "")
            if not length.isdigit() or int(length) > 65536:
                return self.reply(413, "Invalid request size")
            raw = self.rfile.read(int(length))
            if path == "/lanternkeeper/webhook":
                try:
                    processed = process_stripe_webhook(database, raw, self.headers.get("Stripe-Signature", ""))
                except ValueError:
                    return self.reply(400, "Invalid event")
                except Exception:
                    return self.reply(503, "Webhook processing unavailable")
                return self.reply(200, "Processed" if processed else "Ignored")
            # Require a same-origin browser POST. No account identity from cookies or query params.
            if self.headers.get("Origin") != public_origin:
                return self.reply(403, "Invalid origin")
            try:
                params = parse_qs(raw.decode("utf-8"), strict_parsing=True)
                name, password = params["account"][0], params["password"][0]
                if len(name) > 80 or len(password) > 256:
                    return self.reply(400, "Invalid credentials")
                with database.connect() as db:
                    row = db.execute("SELECT id,password_hash FROM accounts WHERE name=? COLLATE NOCASE", (name,)).fetchone()
                if row is None or not verify_password(password, row["password_hash"]):
                    return self.reply(401, "Invalid account or password")
                account_id = int(row["id"])
                if path.endswith("/checkout"):
                    url = create_checkout(database, account_id, public_origin + "/lanternkeeper/success",
                                          public_origin + "/lanternkeeper/cancel")
                else:
                    url = create_billing_portal(database, account_id, public_origin + "/lanternkeeper")
                self.send_response(303)
                self.send_header("Location", url)
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", "0")
                self.end_headers()
            except (KeyError, IndexError, ValueError, UnicodeError):
                self.reply(400, "Invalid request")
            except Exception:
                self.reply(503, "Billing service unavailable")

    server = ThreadingHTTPServer((host, port), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True, name="lanternkeeper-http")
    thread.start()
    return server
