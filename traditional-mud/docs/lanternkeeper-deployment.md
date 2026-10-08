# Lanternkeeper deployment (not enabled by merging)

## Prerequisites

Stripe product `prod_VOympoGet3eLK1`, monthly price
`price_1UOAp3LnIVgW4g5mj4rNdD7P`, billing portal
`bpc_1UOAs3LnIVgW4g5mND3kqWi3` were created in the authorized live account.

Install `stripe` Python package into the same environment as the MUD.
Keep credentials in a root-readable systemd EnvironmentFile, never in Git:

```ini
DOTF_BILLING_ENABLED=1
DOTF_BILLING_ORIGIN=https://fallendreams.cloud
STRIPE_SECRET_KEY=sk_live_REPLACE_WITH_PRIVATE_KEY
DOTF_STRIPE_WEBHOOK_SECRET=whsec_REPLACE_WITH_WEBHOOK_SIGNING_SECRET
```

Add to the existing Caddy site for `fallendreams.cloud`:

```caddyfile
handle /lanternkeeper/* {
    reverse_proxy 127.0.0.1:8766
}
```

The main website should present HTTPS forms that POST `account` and `password`
to `/lanternkeeper/checkout` and `/lanternkeeper/portal`. These are the
player's existing MUD account credentials, not their character name.
The form must be served from the exact `DOTF_BILLING_ORIGIN` origin.
Never log form bodies, disable caching, and rate-limit login attempts at the proxy.
Do not embed Stripe secret keys in browser code.

Register a Stripe **snapshot** webhook event destination for
`https://fallendreams.cloud/lanternkeeper/webhook` with events:
`customer.subscription.created`, `customer.subscription.updated`,
`customer.subscription.deleted`. Save its signing secret as
`DOTF_STRIPE_WEBHOOK_SECRET`. Do not use thin events with this handler.

Restart the MUD service after validating Caddy. Verify HTTPS externally and
Stripe webhook delivery in the Stripe Dashboard.

## Acceptance checks

From `traditional-mud` run:

```bash
python3 -m unittest tests.test_lanternkeeper_wisp tests.test_lanternkeeper_persistence -v
```

Then, in Stripe sandbox first, verify:
1. Wrong MUD password cannot open checkout or portal.
2. A paid checkout creates a subscription containing `dotf_account_id`.
3. A signed subscription event activates `LANTERNKEEPER` and `WISP SUMMON`.
4. Another logged-in character sees the Wisp in LOOK, but not as a target.
5. Disconnecting the owner removes the Wisp from others' LOOK.
6. Subscription cancellation or expiry makes the Wisp dormant without deleting cosmetics.
7. Duplicate and out-of-order events do not reactivate expired membership.
8. Billing portal allows payment method changes and cancellation.

**Do not enable production checkout until the complete acceptance checklist passes.**
