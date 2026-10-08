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
    reverse_proxy 127.0.0.1:8766 {
        # Replace any incoming value; the backend trusts only this Caddy-set header.
        header_up X-Lanternkeeper-Client-IP {client_ip}
    }
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

## Sandbox account verification (first live Stripe API read)

Sandbox Lanternkeeper Price ID:
`price_1UOBtYLsIp78ZNViq1uuSgZf` (distinct from the live Price ID).
It must represent an active USD $4.99 monthly recurring price.

The feature branch includes a read-only preflight command:

```bash
cd ~/dotf-lanternkeeper-test/traditional-mud
~/dotf-lanternkeeper-venv/bin/python -m mud.lanternkeeper_sandbox_check
```

In the **Dreams of the Fallen staging sandbox**, open Stripe Dashboard
**Developers → API keys** and find its sandbox secret key (begins `sk_test_`).
Enter it directly into the terminal's hidden prompt. Do **not** paste it
into ChatGPT, Git, a command, or a shared log. The script neither saves the
key nor creates customers, subscriptions, payments, or webhooks. It retrieves
this Price ID to verify that the key belongs to the correct sandbox and the
price is active, in USD, $4.99, and monthly.

Once the preflight succeeds, keep the isolated staging billing worker
configured with `DOTF_LANTERNKEEPER_PRICE_ID=price_1UOBtYLsIp78ZNViq1uuSgZf`
alongside a **sandbox** `STRIPE_SECRET_KEY`. Never put this Price ID or test
secret in the live service environment, and never use a live key in staging.
Later, set up sandbox webhooks separately with their own signing secret.

## Predeployment staging smoke test

Run the standalone billing subprocess test using the isolated worktree and
Stripe-enabled venv, **without any Stripe API key or live database**:

```bash
cd ~/dotf-lanternkeeper-test/traditional-mud
~/dotf-lanternkeeper-venv/bin/python -m unittest tests.test_lanternkeeper_service -v
```

This test creates a temporary SQLite database, binds a randomly selected
loopback-only port using `DOTF_BILLING_PORT`, confirms the billing HTML is
served, and shuts the subprocess down cleanly. Production uses the default
port 8766. The staging process does not activate billing or contact Stripe.

## Standalone billing worker

The feature branch includes `mud.lanternkeeper_service` and a sample
`deploy/lanternkeeper.service.example` unit. Unlike the existing game server,
this worker uses the Stripe-enabled venv, listens ONLY on
`127.0.0.1:8766`, and reads the live MUD SQLite database.

**Staging sequence (do not execute live until acceptance checks are complete):**

1. Back up the production SQLite database and verify there are no unresolved
   Git conflicts or local changes that a deployment would overwrite.
2. Merge/review the feature into the production source without resetting the
   production worktree.
3. Install the protected `/etc/dotf/lanternkeeper.env` file and limit access
   to root; confirm the billing worker's OS user can write the intended SQLite
   database and its journal/WAL files.
4. Copy the systemd sample to `/etc/systemd/system/dotf-lanternkeeper.service`
   and validate the working directory, interpreter, and database path.
5. Run `sudo systemctl daemon-reload`, then start the standalone service
   only after the above review. This **does not** require changing `dotf`
   or setting `DOTF_BILLING_ENABLED=1`.
6. Validate loopback-only listening, the public Caddy routes (including no
   trailing slash), the browser form's trusted IP header, and Stripe's
   webhook verification. Finally verify billing through sandbox/test-mode,
   then an explicitly approved controlled live transaction.

Use `sudo systemctl status dotf-lanternkeeper --no-pager` for state;
do NOT paste environment files or credentials. Keep the billing service
**stopped and disabled** until the security and end-to-end checks pass.

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
- Validate proxy-injected client-IP parsing and per-IP login throttling in staging;
  edge-level/CDN WAF controls are still recommended for brute-force and volumetric attacks.
- Confirm TLS, proxy forwarding, body logging exclusions, and secrets file permissions.
- Reconcile pending sessions and test repeated checkout, cancel/rejoin, and Stripe
  Billing Portal end to end.
- Test with a separate Stripe **sandbox/test-mode price**; the live Price ID
  cannot be used with test API keys. Set
  `DOTF_LANTERNKEEPER_PRICE_ID=price_<SANDBOX_PRICE_ID>` **only** in the
  isolated sandbox worker, along with a test-mode Stripe API key and
  matching test-mode webhook signing secret. Checkout creation and webhook
  entitlement verification both use this configured price. Omit the override
  for the production live price.
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
