"""Lanternkeeper HTTPS-reverse-proxied billing routes.

Bind to loopback only. Publish /lanternkeeper/* through a TLS reverse proxy.
POST /lanternkeeper/checkout or /lanternkeeper/portal with form fields
account and password; POST /lanternkeeper/webhook with Stripe's raw payload.
"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit
import os
import html
import threading
import time
from collections import defaultdict, deque

from mud.database import Database
from mud.security import verify_password
from mud.lanternkeeper_checkout import create_checkout, create_billing_portal
from mud.lanternkeeper_stripe import process_stripe_webhook

def start_lanternkeeper_http(host="127.0.0.1", port=8766):
    public_origin = os.environ.get("DOTF_BILLING_ORIGIN", "").rstrip("/")
    if not public_origin.startswith("https://") or urlsplit(public_origin).path not in ("", "/"):
        raise RuntimeError("DOTF_BILLING_ORIGIN must be an HTTPS origin")
    database = Database()
    # In-process throttling; do not trust client-supplied forwarding headers.
    attempts = defaultdict(deque)
    attempts_lock = threading.Lock()
    window_seconds = 900
    max_attempts = 5

    def blocked(ip, account):
        now = time.monotonic()
        with attempts_lock:
            for key in (("ip", ip), ("account", account.casefold())):
                recent = attempts[key]
                while recent and recent[0] <= now - window_seconds:
                    recent.popleft()
                if len(recent) >= max_attempts:
                    return True
            return False

    def record_failure(ip, account):
        now = time.monotonic()
        with attempts_lock:
            for key in (("ip", ip), ("account", account.casefold())):
                recent = attempts[key]
                while recent and recent[0] <= now - window_seconds:
                    recent.popleft()
                recent.append(now)


    class Handler(BaseHTTPRequestHandler):
        def reply(self, code, body):
            data = body.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            path = urlsplit(self.path).path
            if path not in ("/lanternkeeper", "/lanternkeeper/", "/lanternkeeper/success", "/lanternkeeper/cancel"):
                return self.reply(404, "Not found")
            if path == "/lanternkeeper/success":
                heading = "Thank you for supporting Dreams of the Fallen"
                detail = "Stripe is processing your subscription. Your Lantern Wisp becomes available after payment confirmation. Reconnect to the MUD and use LANTERNKEEPER to check your status."
            elif path == "/lanternkeeper/cancel":
                heading = "Checkout canceled"
                detail = "No subscription was started by this checkout. You can return whenever you are ready."
            else:
                heading = "Lanternkeeper"
                detail = "Support Dreams of the Fallen for $4.99 per month and receive a cosmetic Lantern Wisp. Enter your existing MUD account credentials to continue securely to Stripe."
            forms = ""
            if path in ("/lanternkeeper", "/lanternkeeper/"):
                forms = (
                    '<form method="post" action="/lanternkeeper/checkout">'
                    '<label>Account name <input name="account" autocomplete="username" required maxlength="80"></label>'
                    '<label>Password <input type="password" name="password" autocomplete="current-password" required maxlength="256"></label>'
                    '<button type="submit">Subscribe for $4.99/month</button>'
                    '</form>'
                    '<p>Already subscribed? Manage your membership:</p>'
                    '<form method="post" action="/lanternkeeper/portal">'
                    '<label>Account name <input name="account" autocomplete="username" required maxlength="80"></label>'
                    '<label>Password <input type="password" name="password" autocomplete="current-password" required maxlength="256"></label>'
                    '<button type="submit">Manage billing</button>'
                    '</form>'
                )
            page = (
                '<!doctype html><html lang="en"><head><meta charset="utf-8">'
                '<meta name="viewport" content="width=device-width, initial-scale=1">'
                '<meta name="referrer" content="no-referrer">'
                '<title>Lanternkeeper | Dreams of the Fallen</title>'
                '<style>body{background:#10101c;color:#f1e8d8;font:17px system-ui,sans-serif;'
                'max-width:560px;margin:8vh auto;padding:24px;line-height:1.6}'
                'h1{color:#eac98b}form{padding:20px 0;border-top:1px solid #484052}'
                'label{display:block;margin:12px 0}input{display:block;width:100%;'
                'box-sizing:border-box;padding:10px;background:#211e30;color:white;border:1px solid #776b8c}'
                'button{padding:12px 18px;background:#eac98b;color:#191420;border:0;cursor:pointer}'
                'a{color:#eac98b}</style></head><body>'
                '<h1>' + html.escape(heading) + '</h1><p>' + html.escape(detail) + '</p>'
                + forms + '<p><a href="https://fallendreams.cloud">Return to Dreams of the Fallen</a></p>'
                '</body></html>'
            ).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Length", str(len(page)))
            self.end_headers()
            self.wfile.write(page)

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
                if not name or not password or len(name) > 80 or len(password) > 256:
                    return self.reply(400, "Invalid credentials")
                ip = self.client_address[0]
                if blocked(ip, name):
                    return self.reply(429, "Too many login attempts; try again later")
                with database.connect() as db:
                    row = db.execute("SELECT id,password_hash FROM accounts WHERE name=? COLLATE NOCASE", (name,)).fetchone()
                if row is None or not verify_password(password, row["password_hash"]):
                    record_failure(ip, name)
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
