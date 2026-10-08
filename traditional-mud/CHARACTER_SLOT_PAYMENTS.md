# Extra Character Slots ($1 USD each)

Extra character slots are a **one-time account upgrade**, not a Lanternkeeper subscription entitlement. Everyone starts with **8 free character slots**; every successful $1 USD checkout adds exactly one permanent slot to the purchasing account. There is no combat, XP, currency, equipment or inventory benefit.

## Stripe product

- Payment account: Vesper Heart IP Holdings LLC (the same account as Lanternkeeper).
- Product: Dreams of the Fallen — Extra Character Slot
- Product ID: `prod_VP0vpYxSBSTgLi`
- Live **one-time** USD 100-cent price: `price_1UOCtFLnIVgW4g5mRXVriDJY`

The game deliberately does not use a generic reusable Payment Link. It generates a 15-minute **signed, account-bound** URL from the authenticated character roster so a verified Checkout Session knows which account to credit.

## Required server environment

Set these in the **`dotf` systemd service environment**, never in Git or client code:

```dotenv
DOTF_STRIPE_SECRET_KEY=sk_live_<live secret for the same Stripe account>
DOTF_SLOT_STRIPE_PRICE_ID=price_1UOCtFLnIVgW4g5mRXVriDJY
DOTF_SLOT_STRIPE_WEBHOOK_SECRET=whsec_<signing secret from the webhook endpoint>
DOTF_SLOT_LINK_SECRET=<generate a random 32+ byte secret, e.g. openssl rand -hex 32>
DOTF_SLOT_PUBLIC_BASE_URL=https://mud.lvthn.io
```

Do **not** use the live price ID with a test-mode API key. For staging, create a matching test-mode product/price and use all test-mode keys.

If any value is absent, the payment listener and public purchase links stay disabled. The MUD and all eight free slots continue working.

## HTTPS proxy and webhook

Once the game process starts with those variables, a **loopback-only** HTTP listener runs at `127.0.0.1:8768`. In Caddy, add a route for `/slots/*` on the host named by `DOTF_SLOT_PUBLIC_BASE_URL`, *ahead of the existing site fallback*:

```caddyfile
# Inside the existing mud.lvthn.io site block (do not replace its other routes):
handle /slots/* {
    reverse_proxy 127.0.0.1:8768
}
```

Configure a Stripe webhook endpoint at:

`https://mud.lvthn.io/slots/webhook`

Subscribe to both `checkout.session.completed` and `checkout.session.async_payment_succeeded`. Store **that endpoint's signing secret** in `DOTF_SLOT_STRIPE_WEBHOOK_SECRET`, then restart `dotf` and reload Caddy.

**Do not route port 8768 directly to the Internet.** Expose it only through the HTTPS proxy.

## Player experience

1. Log in normally and open the **Character Roster** (no Lanternkeeper subscription needed).
2. Type **`BUY SLOT`**.
3. Open the signed HTTPS link within 15 minutes; Stripe hosts the payment page.
4. After Stripe verifies the payment, its authenticated webhook records one slot entitlement, keyed by the unique Checkout Session ID.
5. The next roster refresh shows 9 slots, then 10 after another separate $1 purchase, and so on. Already-created characters and purchases are preserved.

Returning from Checkout without a verified payment **never** grants a slot. Duplicate webhook deliveries **never** grant a second slot. Character creation also enforces the current account limit inside a serialized database transaction, so concurrent sessions cannot exceed it.

## Release checks

- Do not deploy from this branch until CI passes and the VPS's previously reported unresolved Git merge conflicts are fixed without discarding local changes.
- Back up the live SQLite database before deployment.
- Verify a fresh account gets 8 free slots, and a Lanternkeeper-free account can request a purchase link.
- First perform a complete **test-mode** checkout and webhook delivery against a copied/staging DB; confirm 8 → 9 and identical replay remains 9.
- Confirm the real Caddy route reaches checkout and webhook through HTTPS; check that the incoming Stripe webhook logs a 2xx response.
- Check that a cancelled checkout, unpaid session, wrong price, invalid HMAC signature and expired checkout URL never change the slot count.
- Refunds/disputes are not automatically removed from a permanent entitlement; investigate these manually before implementing any revocation policy.

No gameplay perks or subscriptions are attached to this purchase.
