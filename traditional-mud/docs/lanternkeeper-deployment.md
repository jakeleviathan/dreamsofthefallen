# Lanternkeeper launch runbook — NOT LIVE until verified

Lanternkeeper is a **$4.99/month** cosmetic subscription for Dreams of the Fallen.
The live Stripe account contains product `prod_VOympoGet3eLK1`, price
`price_1UOAp3LnIVgW4g5mj4rNdD7P`, and portal configuration
`bpc_1UOAs3LnIVgW4g5mND3kqWi3`.

## Current infrastructure

- MUD: `mud.lvthn.io:4000`, running via the existing `dotf` systemd service.
- Public billing origin: **`https://mud.lvthn.io`** (NOT `fallendreams.cloud`).
- Public entry point: **`https://mud.lvthn.io/lanternkeeper/`**.
- Stripe webhook URL: **`https://mud.lvthn.io/lanternkeeper/webhook`**.
- Public game website `https://fallendreams.cloud` should LINK to the entry point.
- Reverse proxy: existing Caddy on the MUD VPS, forwarding to loopback port 8766.
- Database: same production SQLite database as the MUD, configured with `MUD_DB_PATH`.
- Existing production `dotf` service uses `/usr/bin/python3` with **no stripe SDK**.
  Do not switch its interpreter or enable billing in its environment without verifying
  all game dependencies. A dedicated billing systemd service using the billing venv
  is preferable; keep the MUD service unchanged.

## Caddy route

**Important:** `handle /lanternkeeper/*` alone does not necessarily
match `/lanternkeeper` (no trailing slash). Route both paths explicitly.

Example inside the **existing `mud.lvthn.io` site block**, preserving its
patches endpoint and other handlers:

```caddyfile
@lanternkeeper path /lanternkeeper /lanternkeeper/*
handle @lanternkeeper {
    reverse_proxy 127.0.0.1:8766
}
```

Validate with `sudo caddy validate --config /etc/caddy/Caddyfile` BEFORE
reloading Caddy. Test both `/lanternkeeper` and `/lanternkeeper/`.

## Credentials and service configuration

Do not paste keys or webhook secrets into chat, terminal transcripts, Git,
screenshots, or the game website. Use a protected, root-owned systemd
`EnvironmentFile` outside the repository. Its settings are:

```ini
DOTF_BILLING_ORIGIN=https://mud.lvthn.io
MUD_DB_PATH=/home/ubuntu/dotf-data/mud.db
STRIPE_SECRET_KEY=<private Stripe secret key>
DOTF_STRIPE_WEBHOOK_SECRET=<private Stripe snapshot-webhook signing secret>
```

The billing worker must run with the stripe-enabled venv; the existing MUD
service does not require `DOTF_BILLING_ENABLED=1` when a separate worker runs.
**Do not add live credentials or activate the worker yet.**

## Stripe webhook

Create a **snapshot event** destination once the billing worker is ready,
at `https://mud.lvthn.io/lanternkeeper/webhook` subscribing to:

- `customer.subscription.created`
- `customer.subscription.updated`
- `customer.subscription.deleted`

Never use thin events for this handler. Configure the exact destination's
signing secret privately. Verify signature enforcement and delivery retries,
including out-of-order events, before enabling checkout for the public.

## Security gates

- Browser `Origin` validation, no-store responses, request-size limits, and
  account-based authentication throttling currently exist.
- Finish trusted-client-IP/edge-level rate limiting for login POST endpoints.
- Confirm TLS, proxy forwarding, body logging exclusions, and secrets file permissions.
- Reconcile pending sessions and test repeated checkout, cancel/rejoin, and Stripe
  Billing Portal end to end.
- Test with a separate Stripe **sandbox/test-mode price**; the live Price ID
  cannot be used with test API keys.
- Verify the real Wisp visibility and entitlement lifecycle across MUD logins.
- Ensure a rejected webhook never silently activates or strands a customer:
  inspect delivery failures and support manual reconciliation.
- Do not announce the subscription as available for sale until all gates pass.

## Offline regression tests

From the isolated testing worktree's `traditional-mud` directory:

```bash
~/dotf-lanternkeeper-venv/bin/python -m unittest \
  tests.test_lanternkeeper_wisp \
  tests.test_lanternkeeper_persistence \
  tests.test_lanternkeeper_stripe \
  tests.test_lanternkeeper_checkout \
  tests.test_lanternkeeper_http -v
```

The live `main` worktree has unrelated local changes; do not reset or pull over
them to deploy this feature. Do not merge merely because offline tests pass.
