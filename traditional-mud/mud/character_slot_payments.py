"""Account-bound $1 character slot checkout and verified Stripe webhook fulfillment.

The HTTP listener is intended to sit behind an HTTPS reverse proxy. It does not
grant anything from browser redirects or client input; only paid signed events.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import os
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen

from mud.database import Database

SLOT_PRICE_CENTS = 100
TOKEN_LIFETIME_SECONDS = 15 * 60
WEBHOOK_TOLERANCE_SECONDS = 5 * 60


def _settings() -> dict[str, str] | None:
    values = {
        "stripe_key": os.environ.get("DOTF_STRIPE_SECRET_KEY", "").strip(),
        "price_id": os.environ.get("DOTF_SLOT_STRIPE_PRICE_ID", "").strip(),
        "webhook_secret": os.environ.get("DOTF_SLOT_STRIPE_WEBHOOK_SECRET", "").strip(),
        "link_secret": os.environ.get("DOTF_SLOT_LINK_SECRET", "").strip(),
        "public_url": os.environ.get("DOTF_SLOT_PUBLIC_BASE_URL", "").strip().rstrip("/"),
    }
    if not all(values.values()) or not values["public_url"].startswith("https://"):
        return None
    if not values["price_id"].startswith("price_") or not values["stripe_key"].startswith("sk_"):
        return None
    return values


def configured() -> bool:
    return _settings() is not None


def sign_purchase_token(account_id: int, secret: str, *, now: int | None = None) -> str:
    if account_id < 1 or not secret:
        raise ValueError("A valid account and signing secret are required.")
    expires = int(time.time() if now is None else now) + TOKEN_LIFETIME_SECONDS
    payload = f"{account_id}:{expires}".encode("ascii")
    encoded = base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")
    signature = hmac.new(secret.encode("utf-8"), encoded.encode("ascii"), hashlib.sha256).hexdigest()
    return f"{encoded}.{signature}"


def account_from_purchase_token(token: str, secret: str, *, now: int | None = None) -> int:
    try:
        encoded, signature = token.split(".", 1)
        expected = hmac.new(secret.encode("utf-8"), encoded.encode("ascii"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise ValueError("Invalid purchase link.")
        decoded = base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)).decode("ascii")
        account_raw, expiry_raw = decoded.split(":", 1)
        account_id, expiry = int(account_raw), int(expiry_raw)
        if account_id < 1 or int(time.time() if now is None else now) > expiry:
            raise ValueError("Expired purchase link.")
        return account_id
    except (ValueError, UnicodeError, IndexError, binascii.Error) as exc:
        raise ValueError("Invalid or expired purchase link.") from exc


def purchase_link_for_account(account_id: int) -> str | None:
    settings = _settings()
    if settings is None:
        return None
    token = sign_purchase_token(account_id, settings["link_secret"])
    return f'{settings["public_url"]}/slots/checkout?{urlencode({"token": token})}'


def verify_stripe_event(
    payload: bytes, signature_header: str, webhook_secret: str, *, now: int | None = None
) -> dict:
    """Verify Stripe's timestamped HMAC signature before parsing or trusting payload."""
    fields = {}
    for field in signature_header.split(","):
        key, _, value = field.strip().partition("=")
        fields.setdefault(key, []).append(value)
    try:
        timestamp = int(fields["t"][0])
        signatures = fields["v1"]
    except (KeyError, IndexError, ValueError) as exc:
        raise ValueError("Missing Stripe webhook signature.") from exc
    if abs(int(time.time() if now is None else now) - timestamp) > WEBHOOK_TOLERANCE_SECONDS:
        raise ValueError("Expired Stripe webhook signature.")
    digest = hmac.new(
        webhook_secret.encode("utf-8"), str(timestamp).encode("ascii") + b"." + payload, hashlib.sha256
    ).hexdigest()
    if not any(hmac.compare_digest(digest, candidate) for candidate in signatures):
        raise ValueError("Invalid Stripe webhook signature.")
    event = json.loads(payload)
    if not isinstance(event, dict):
        raise ValueError("Invalid Stripe event.")
    return event


def fulfill_stripe_event(database: Database, event: dict, *, expected_price_id: str) -> bool:
    """Credit exactly one slot after an authentic paid Checkout Session event.

    A false result means the event was irrelevant or its session was already credited.
    The caller must pass only events verified by verify_stripe_event.
    """
    if event.get("type") not in {"checkout.session.completed", "checkout.session.async_payment_succeeded"}:
        return False
    session = (event.get("data") or {}).get("object") or {}
    meta = session.get("metadata") or {}
    if (
        session.get("object") != "checkout.session"
        or session.get("mode") != "payment"
        or session.get("payment_status") != "paid"
        or session.get("currency") != "usd"
        or session.get("amount_subtotal") != SLOT_PRICE_CENTS
        or meta.get("dotf_item") != "extra_character_slot"
        or meta.get("dotf_price_id") != expected_price_id
    ):
        return False
    try:
        account_id = int(meta["dotf_account_id"])
        checkout_id = session["id"]
    except (KeyError, TypeError, ValueError):
        return False
    if account_id < 1 or not isinstance(checkout_id, str):
        return False
    return database.record_character_slot_purchase(account_id, checkout_id)


def _create_checkout(account_id: int, settings: dict[str, str]) -> str:
    data = urlencode({
        "mode": "payment",
        "line_items[0][price]": settings["price_id"],
        "line_items[0][quantity]": "1",
        "client_reference_id": str(account_id),
        "metadata[dotf_account_id]": str(account_id),
        "metadata[dotf_item]": "extra_character_slot",
        "metadata[dotf_price_id]": settings["price_id"],
        "success_url": settings["public_url"] + "/?character_slot=success",
        "cancel_url": settings["public_url"] + "/?character_slot=cancelled",
    }).encode("ascii")
    req = Request(
        "https://api.stripe.com/v1/checkout/sessions",
        data=data,
        headers={
            "Authorization": "Bearer " + settings["stripe_key"],
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )
    with urlopen(req, timeout=12) as response:
        checkout = json.load(response)
    url = checkout.get("url")
    if not isinstance(url, str) or not url.startswith("https://checkout.stripe.com/"):
        raise ValueError("Stripe did not return a hosted checkout link.")
    return url


def start_character_slot_payment_server(
    database: Database, *, host: str = "127.0.0.1", port: int = 8768
) -> ThreadingHTTPServer | None:
    """Start loopback-only payment endpoints when all secret env vars are set."""
    settings = _settings()
    if settings is None:
        return None

    class Handler(BaseHTTPRequestHandler):
        def _respond(self, status: int, message: str) -> None:
            data = message.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self) -> None:
            request = urlparse(self.path)
            if request.path != "/slots/checkout":
                self._respond(404, "Not found.")
                return
            token = parse_qs(request.query).get("token", [""])[0]
            try:
                account_id = account_from_purchase_token(token, settings["link_secret"])
                if database.get_account_by_id(account_id) is None:
                    self._respond(404, "Account no longer exists.")
                    return
                url = _create_checkout(account_id, settings)
            except ValueError:
                self._respond(400, "Purchase link is invalid or expired. Return to your character roster for a fresh link.")
                return
            except (HTTPError, URLError, TimeoutError, OSError):
                self._respond(502, "Checkout is temporarily unavailable.")
                return
            self.send_response(303)
            self.send_header("Location", url)
            self.send_header("Cache-Control", "no-store")
            self.end_headers()

        def do_POST(self) -> None:
            if urlparse(self.path).path != "/slots/webhook":
                self._respond(404, "Not found.")
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                length = 0
            if length < 1 or length > 65536:
                self._respond(400, "Invalid event.")
                return
            payload = self.rfile.read(length)
            try:
                event = verify_stripe_event(
                    payload, self.headers.get("Stripe-Signature", ""), settings["webhook_secret"]
                )
            except (ValueError, json.JSONDecodeError):
                self._respond(400, "Invalid webhook signature.")
                return
            try:
                fulfill_stripe_event(database, event, expected_price_id=settings["price_id"])
            except Exception:
                # Stripe retries 5xx deliveries. Never acknowledge failed persistence.
                self._respond(500, "Unable to record payment.")
                return
            self._respond(200, "OK")

    server = ThreadingHTTPServer((host, port), Handler)
    Thread(target=server.serve_forever, name="dotf-slot-payments", daemon=True).start()
    return server
