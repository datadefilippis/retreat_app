# AFianco — Stripe Add-on Setup Guide (v5.8 / Onda 3)

**Audience**: AFianco platform owner. You.
**When to do this**: AFTER backend deploy of Onda 3 (commit will be tagged in repo). Before Onda 4.
**Time required**: ~20 minutes test mode + ~20 minutes live mode.
**Reversibility**: Fully reversible — just deactivate the Stripe Prices and unset the IDs in MongoDB.

---

## What you're doing

You'll create **4 new Stripe Products** (one per add-on) with a recurring monthly Price each,
then paste those IDs into MongoDB so the backend can append them to existing Stripe Subscriptions.

The 4 add-ons:

| Slug (in DB)            | Public name      | Price/mo | Function |
|-------------------------|------------------|----------|----------|
| `addon_ai_chat_pack`    | +50 AI chat      | €9       | Stackable up to 5× |
| `addon_ai_chat_pro`     | +200 AI chat     | €29      | Stackable up to 3× |
| `addon_orders_pack`     | +200 ordini      | €15      | Stackable up to 5× |
| `addon_extra_store`     | +1 store         | €19      | Stackable up to 7× (Pro plan only) |

You do **NOT** touch the existing Stripe Products for free / starter / core / pro / enterprise.
Those stay exactly as today — Onda 5 will rename them, but Onda 3 leaves them alone.

---

## Phase 1 — Test mode (do this first, validate, then go live)

### Step 1 — Open Stripe Dashboard in test mode

1. Go to https://dashboard.stripe.com
2. Top-right toggle: **"View test data" must be ON** (orange "TEST" badge visible)
3. Verify the URL bar shows `dashboard.stripe.com/test/...`

⚠️ **Critical**: every step below assumes you're in TEST mode. Don't proceed if the orange badge isn't showing.

### Step 2 — Create 4 Stripe Products

For each of the 4 add-ons, click **Products → + Add product** and fill in:

#### Product 1 — `+50 AI chat`

| Field | Value |
|---|---|
| Name | `+50 AI chat` |
| Description | `50 chat AI extra al mese, cumulabile fino a 5×.` |
| Image | (optional — skip for now) |
| Pricing model | `Recurring` |
| Price (one-off) | `9.00 EUR / month` |
| Tax behavior | `Inclusive` (or whatever matches your existing plans — check core or pro for reference) |
| Metadata → Add row | key=`afianco_addon`, value=`addon_ai_chat_pack` |

Click **Save product**. You'll land on the product page. Note the two IDs near the top:
- **Product ID**: starts with `prod_` (e.g. `prod_abc123XYZ`)
- **Price ID**: starts with `price_` (e.g. `price_1xyz...`)

→ Copy both somewhere (text editor, sticky note). You'll paste them into MongoDB in Step 3.

#### Product 2 — `+200 AI chat`

Same as above but:
- Name: `+200 AI chat`
- Description: `200 chat AI extra al mese, cumulabile fino a 3×.`
- Price: `29.00 EUR / month`
- Metadata: key=`afianco_addon`, value=`addon_ai_chat_pro`

#### Product 3 — `+200 ordini`

- Name: `+200 ordini`
- Description: `200 ordini ecommerce extra al mese, cumulabile fino a 5×.`
- Price: `15.00 EUR / month`
- Metadata: key=`afianco_addon`, value=`addon_orders_pack`

#### Product 4 — `+1 store`

- Name: `+1 store`
- Description: `Aggiungi 1 storefront in più al tuo piano, cumulabile fino a 7×.`
- Price: `19.00 EUR / month`
- Metadata: key=`afianco_addon`, value=`addon_extra_store`

After all 4 are created, you should have **8 IDs** total: 4 product IDs and 4 price IDs.

### Step 3 — Paste the IDs into MongoDB

Two ways. Pick one.

#### Option A — via mongosh (fastest)

Connect to your **test mode** database (the same one your local backend uses). Replace
`<DB_NAME>` with what's in your `backend/.env`'s `DB_NAME`.

```javascript
mongosh "mongodb://localhost:27017/<DB_NAME>"
```

Then run, replacing the `prod_xxx` / `price_xxx` placeholders with the IDs from Stripe:

```javascript
db.commercial_plans.updateOne(
  { slug: "addon_ai_chat_pack" },
  { $set: {
      stripe_product_id: "prod_REPLACE_WITH_REAL_ID",
      stripe_price_id_monthly: "price_REPLACE_WITH_REAL_ID"
  }}
);

db.commercial_plans.updateOne(
  { slug: "addon_ai_chat_pro" },
  { $set: {
      stripe_product_id: "prod_REPLACE_WITH_REAL_ID",
      stripe_price_id_monthly: "price_REPLACE_WITH_REAL_ID"
  }}
);

db.commercial_plans.updateOne(
  { slug: "addon_orders_pack" },
  { $set: {
      stripe_product_id: "prod_REPLACE_WITH_REAL_ID",
      stripe_price_id_monthly: "price_REPLACE_WITH_REAL_ID"
  }}
);

db.commercial_plans.updateOne(
  { slug: "addon_extra_store" },
  { $set: {
      stripe_product_id: "prod_REPLACE_WITH_REAL_ID",
      stripe_price_id_monthly: "price_REPLACE_WITH_REAL_ID"
  }}
);
```

Verify all 4 are populated:

```javascript
db.commercial_plans.find(
  { is_addon: true },
  { slug: 1, stripe_product_id: 1, stripe_price_id_monthly: 1, _id: 0 }
).toArray();
```

You should see 4 documents, each with non-null `stripe_product_id` and `stripe_price_id_monthly`.

#### Option B — via admin API

If you prefer not to touch Mongo directly, there's an admin endpoint to update the Stripe IDs:

```bash
# 1. Get a system_admin JWT (login flow)
TOKEN="your_jwt_here"

# 2. For each add-on, PUT the new Stripe IDs:
curl -X PUT https://YOUR_API_HOST/api/admin/commercial-plans/addon_ai_chat_pack \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "stripe_product_id": "prod_REPLACE",
    "stripe_price_id_monthly": "price_REPLACE"
  }'

# Repeat for the 3 others.
```

> **Note**: this endpoint exists if your admin UI exposes it. If you get a 404, fall back to Option A.

### Step 4 — Validate end-to-end in test mode

You'll buy an add-on as a fake customer to confirm the flow works. Use the seeded test orgs
created by `python backend/scripts/seed_test_orgs.py --execute` (Onda 0).

#### 4a. Subscribe a test org to a paid plan (Stripe Checkout)

If `org_test_active` doesn't yet have a real Stripe Subscription, do a checkout first:

1. Login as `admin@org-test-active.test` / `Test1234!`
2. Navigate to `/plans`
3. Click "Abbonati" on Commerce Starter (slug `core`)
4. In Stripe Checkout: card `4242 4242 4242 4242`, any future expiry, any CVC
5. Wait for redirect → `/settings?billing_success=1` → BillingSection shows "active"

#### 4b. Buy the +50 AI chat add-on

```bash
TOKEN="logged_in_user_jwt"

curl -X POST https://YOUR_API_HOST/api/billing/add-addon \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"addon_slug": "addon_ai_chat_pack", "quantity": 1}'
```

Expected response:
```json
{
  "status": "ok",
  "addon_slug": "addon_ai_chat_pack",
  "quantity": 1,
  "subscription_id": "sub_xxx",
  "note": "AddonSubscription will be persisted by webhook delivery."
}
```

Within ~1 second the Stripe webhook fires `customer.subscription.updated` → backend persists
the AddonSubscription row.

#### 4c. Verify the AddonSubscription row

```javascript
db.addon_subscriptions.findOne({
  organization_id: "org_test_active",
  addon_slug: "addon_ai_chat_pack"
});
```

Expected:
- `status: "active"`
- `quantity: 1`
- `stripe_subscription_item_id: "si_xxx"` (some Stripe item ID)
- `stripe_price_id`: matches what you set in Step 3

#### 4d. Verify the effective limit went up

The org was on Commerce Starter → `chat: 80`. After buying +50 AI chat → `chat: 130`.

Test it via the AI chat endpoint:

```bash
# Try the 81st AI chat. Pre-Onda-3 it would 429. Now it should succeed.
curl -X POST https://YOUR_API_HOST/api/ai/chat \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"message": "test"}'
# → 200 OK
```

(Or just check `db.ai_usage_events.count({organization_id: "org_test_active"})` after
exceeding 80 calls — no 429 thrown.)

#### 4e. Cancel the add-on

```bash
curl -X DELETE https://YOUR_API_HOST/api/billing/addon/addon_ai_chat_pack \
  -H "Authorization: Bearer $TOKEN"
```

Within ~1 second the row should flip to `status: "cancelled"`. Effective chat limit returns to 80.

✅ If all 5 sub-steps pass, **test mode setup is complete**. Proceed to live mode.

---

## Phase 2 — Live mode (production)

**Prerequisites**:
- Phase 1 fully validated in test mode
- Backend Onda 3 deployed to production
- A backup of `commercial_plans` taken (`python backend/scripts/dump_pricing_state.py --output /tmp/pre_addon_live.json`)

### Step A — Create the same 4 Products in LIVE mode

Repeat Phase 1 Steps 2 + 3 but with the **TEST/LIVE toggle turned OFF** in Stripe Dashboard.
Same Product names, same prices, same metadata.

Stripe live IDs are different from test IDs. The MongoDB collection `commercial_plans` is the
SAME for both environments (your DB is single-tenant). So when you `db.commercial_plans.updateOne(...)`
in Step 3 of Phase 2, you're **overwriting** the test IDs with live IDs.

⚠️ **Critical decision**: do you have separate test/prod MongoDB instances?
- **If yes** (production has its own DB): paste live IDs into the prod DB. Test DB keeps test IDs.
- **If no** (single DB used by both your local and prod): you have to pick one. Recommended:
  paste **live** IDs into the prod DB, and re-run Phase 1 Step 3 on your local laptop with
  test IDs whenever you want to test locally.

You probably want to set up a small `.env.live-stripe-ids` file with the live IDs you can copy-paste.

### Step B — Smoke test in production

1. Pick one safe paying customer (or a friendly beta tester)
2. Have them go to `/plans` → buy the +50 AI chat add-on
3. Verify in Stripe Dashboard: their Subscription now has 2 items (main plan + addon)
4. Verify in DB: `addon_subscriptions` has the row
5. Verify their next invoice (preview) shows the proration charge

If anything is off, **revoke the live Stripe Prices** (set `active: false` in Stripe) and unset
the IDs in MongoDB:

```javascript
db.commercial_plans.updateMany(
  { is_addon: true },
  { $set: { stripe_product_id: null, stripe_price_id_monthly: null } }
);
```

This makes the add-on endpoints reject any new add-on purchase with `"Add-on '<slug>' has no
stripe_price_id_monthly"` error — clean rollback, no Stripe state corruption.

---

## Troubleshooting

### "POST /api/billing/add-addon → 400 invalid_addon"

Most likely cause: the add-on `CommercialPlan` row in MongoDB has `stripe_price_id_monthly: null`.
Check Step 3 above and verify the IDs were pasted in.

### "POST /api/billing/add-addon → 400 incompatible_plan"

The current org's plan is in the add-on's exclusion list. Compatibility:

| Add-on | Compatible with |
|---|---|
| `addon_ai_chat_pack` | `starter`, `core`, `pro` |
| `addon_ai_chat_pro` | `core`, `pro` |
| `addon_orders_pack` | `core`, `pro` |
| `addon_extra_store` | `pro` only |

Free plan can never buy add-ons (must upgrade first).

### "Webhook subscription.updated fired but AddonSubscription not created"

Check the backend logs around the webhook delivery:
```
[webhook] subscription.updated org=... sub=... addon sync: upserted=N cancelled=M
```

If `upserted=0` despite the customer buying an add-on, the metadata on the Stripe item is
missing or malformed. Stripe Dashboard → the Subscription → click on the addon line item →
verify metadata contains `is_addon: true` and `addon_slug: <slug>`.

If metadata is absent, the bug is in `stripe_service.modify_subscription` — open an issue
referencing `_handle_subscription_updated` log output.

### "Stripe Subscription has 2 items but AddonSubscription is missing"

Run the reconcile manually:

```bash
# Forces re-sync from Stripe to DB
curl -X POST https://YOUR_API_HOST/api/admin/organizations/<ORG_ID>/billing/reconcile \
  -H "Authorization: Bearer <SYSTEM_ADMIN_JWT>" \
  -d '{"dry_run": false}'
```

This pulls the live Stripe state and rebuilds the local AddonSubscription rows.

### "Want to fully wipe add-on data and start over"

```javascript
// In test mode only:
db.addon_subscriptions.deleteMany({});
```

The next webhook from Stripe will repopulate any active add-ons via reconcile.

---

## What happens behind the scenes

When the customer clicks "+ Aggiungi" on `+50 AI chat`:

1. Frontend POSTs `/api/billing/add-addon` with `{addon_slug, quantity: 1}`
2. Backend validates: org has paid sub, addon exists, plan is compatible, quantity within max
3. Backend calls `stripe.Subscription.modify(sub_id, items=[{price: addon_price_id, quantity: 1, metadata: {is_addon: "true", addon_slug: "addon_ai_chat_pack"}}], proration_behavior: "create_prorations")`
4. Stripe charges proration immediately (~€0.30 for the remaining days of the month) and adds the line item
5. Stripe fires `customer.subscription.updated` webhook
6. Backend handler iterates `sub.items.data[]`, finds the new add-on item, calls `reconcile_addons_with_stripe_items` which inserts the AddonSubscription row
7. Next time the user fires an AI chat, `module_access.check_module_access` calls `_get_addon_contribution` → returns 50 → effective_limit = 80 + 50 = 130 → user has 130 chat available

The add-on persists across renewal cycles — it stays attached until the user cancels it explicitly
or the parent subscription is deleted. The user is charged €9 every month alongside the main €39
plan, on a single combined invoice.

---

## Reference — what's stored where

| Stripe object | MongoDB mirror | Purpose |
|---|---|---|
| Stripe `Product` (prod_xxx) | `commercial_plans.stripe_product_id` | Catalog reference |
| Stripe `Price` (price_xxx, recurring) | `commercial_plans.stripe_price_id_monthly` | Pricing for new checkouts/modifies |
| Stripe `Subscription.items[]` (si_xxx) | `addon_subscriptions.stripe_subscription_item_id` | Per-org per-addon active row |
| Webhook `customer.subscription.updated` event | `billing_events` | Idempotency log (already existed pre-Onda-3) |
