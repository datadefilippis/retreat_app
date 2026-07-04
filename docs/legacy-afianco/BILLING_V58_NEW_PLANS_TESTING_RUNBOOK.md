# AFianco Billing v5.8 — New Plans + Add-ons Testing Runbook

**Scope**: Verify the new commercial plan structure (Free/Solo/Commerce Starter/Commerce Pro/Custom),
add-on packs, multi-language quota warnings, grandfather pricing, and system admin custom plans.

**Companion document**: `BILLING_V57_TESTING_RUNBOOK.md` — covers the underlying checkout flow,
recovery path, webhook idempotency, and cross-org guards. Scenarios there (A–I) are still
applicable and **not duplicated** here.

**Version**: v5.8 (Onda 0+ — pre-implementation reference)
**Audience**: Developer or QA executing manual end-to-end tests during the rollout of Ondes 1–9.

---

## Table of contents

| Section | Covers |
|---|---|
| **A.** Preconditions extending v5.7 | New env vars, new test orgs, new seed assumptions |
| **B.** Add-on pack scenarios (J–N) | Buy / cancel / stack / upgrade / cross-org |
| **C.** Plan rebrand + grandfather scenarios (O–Q) | New customers vs legacy lock |
| **D.** Quota warning scenarios (R–T) | 80% email, exceeded paywall, multi-language |
| **E.** Commerce-flow scenarios (U–W) | Orders quota, stores quota, contact_request fallback |
| **F.** Subscription lifecycle scenarios (X–Z) | Cancel→Free→Resubscribe (no double charge) |
| **G.** System admin scenarios (AA–CC) | Custom plan, trial extension, impersonate |
| **J.** Onda 9.A — Cancel/Reactivate + admin add-ons (DD–JJ) | Native cancel button, reactivate, trial-once enforcement, admin manual addons |
| **H.** Cleanup matrix | What state to reset between scenarios |
| **I.** Go/No-Go checklist for v5.8 | Production readiness |

---

## A. Preconditions extending v5.7

### A1. New env vars (none required for v5.8)

v5.8 introduces no new env vars. Reuse the v5.7 setup:
- `STRIPE_SECRET_KEY`, `STRIPE_PUBLISHABLE_KEY`, `STRIPE_WEBHOOK_SECRET`, `MONGO_URL`, `DB_NAME`, `FRONTEND_URL`.

### A2. Updated catalog after Ondes 1–5

After Ondes 1–5 are applied, the `commercial_plans` collection must contain:

| Slug | Name (new) | Trial | Price (EUR/mo) | is_self_serve | is_addon |
|---|---|---|---|---|---|
| `free` | Free | 0 | 0 | false | false |
| `starter` | Solo | 14 | 15 | true | false |
| `core` | Commerce Starter | 14 | 39 | true | false |
| `pro` | Commerce Pro | 14 | 89 | true | false |
| `enterprise` | Custom | 0 | 199 (placeholder) | false | false |
| `addon_ai_chat_pack` | +50 AI chat | 0 | 9 | true | true |
| `addon_ai_chat_pro` | +200 AI chat | 0 | 29 | true | true |
| `addon_orders_pack` | +200 orders | 0 | 15 | true | true |
| `addon_extra_store` | +1 store | 0 | 19 | true | true |

Verify with:
```js
db.commercial_plans.find({}, {slug:1, name:1, is_addon:1, price_monthly:1, stripe_price_id_monthly:1}).sort({sort_order:1})
```

The 4 add-on plans **must** have non-null `stripe_price_id_monthly` after Stripe ops (manual step in Onda 3 / Onda 5).

### A3. Test orgs — extended set

In addition to `org_alpha` / `org_beta` from v5.7, you need **4 new test orgs** seeded by
`backend/scripts/seed_test_orgs.py`:

| Test org slug | billing_status | commercial_plan_slug | Purpose |
|---|---|---|---|
| `org_test_active` | active | core | Has paid Stripe sub, used for upgrade/downgrade/add-on tests |
| `org_test_trialing` | trialing | core | In trial (14gg from creation), used for trial-expiry tests |
| `org_test_past_due` | past_due | pro | Failed payment, used for past_due gate tests |
| `org_test_canceled` | canceled | free | Came from a canceled paid sub, fell back to Free |

Reset all 4 between full test runs:
```bash
python backend/scripts/seed_test_orgs.py --reset
```

### A4. Test users (one admin per test org)

Each test org has 1 admin user with email pattern `admin@<orgslug>.test` and password `Test1234!`.
Created automatically by `seed_test_orgs.py`.

For multi-language tests (Section D), the admin's `User.locale` is set as follows:
- `org_test_active` → `it`
- `org_test_trialing` → `en`
- `org_test_past_due` → `de`
- `org_test_canceled` → `fr`

This lets us test all 4 locales without changing settings between scenarios.

### A5. State snapshot before each section

Before starting any new section (B, C, D, …), dump current pricing state:
```bash
python backend/scripts/dump_pricing_state.py --output /tmp/pricing_pre_<section>.json
```

If a scenario fails and you need to rollback, diff against this snapshot.

---

## B. Add-on pack scenarios (J–N)

### Scenario J — Buy first add-on on existing paid sub

**Goal**: Org with active sub buys an add-on. Stripe sub gets a 2nd line_item, AddonSubscription
record is created, effective limit increases.

**Setup**:
- `org_test_active` is on `core` (Commerce Starter, chat=80, orders_monthly=200)
- No add-ons yet (`db.addon_subscriptions.find({organization_id: "org_test_active"}).count() == 0`)

**Steps**:

| # | Action | Where | Expected |
|---|---|---|---|
| 1 | Login as admin@org-test-active.test | Browser | Lands on dashboard |
| 2 | Navigate to `/plans` → scroll to "Add-on packs" | Browser | Sees 3 visible add-ons (`addon_ai_chat_pack`, `addon_ai_chat_pro`, `addon_orders_pack`). NOT visible: `addon_extra_store` (Pro-only) |
| 3 | Click "+ Aggiungi" on `addon_ai_chat_pack` | Browser | Confirmation modal: "+50 AI chat for €9/mo" |
| 4 | Confirm | Browser → Backend | POST `/api/billing/add-addon` with `{addon_slug: "addon_ai_chat_pack", quantity: 1}` |
| 5 | Backend calls `stripe.Subscription.modify()` adding new line_item | Stripe API | Sub now has 2 items: main `core` + addon |
| 6 | Stripe fires `customer.subscription.updated` | Stripe webhook → Backend | Webhook adds `AddonSubscription` row |
| 7 | UI refreshes, shows "+50 AI chat × 1" in active add-ons section | Browser | Effective chat limit = 80 + 50 = 130 |
| 8 | Try `/api/ai/chat` 130 times | Browser/curl | All succeed (no 429) |
| 9 | 131st chat | Browser/curl | 429 QUOTA_EXCEEDED |

**Verify in DB**:
```js
db.addon_subscriptions.findOne({organization_id: "org_test_active", addon_slug: "addon_ai_chat_pack"})
// expected: {status: "active", quantity: 1, stripe_subscription_item_id: "si_xxx"}

db.billing_events.find({organization_id: "org_test_active"}).sort({created_at:-1}).limit(2)
// expected: 1× checkout/modify event + 1× addon-add event with stripe_event_id present
```

**Verify in Stripe Dashboard**:
- Subscription > sub_xxx > 2 items visible (core + ai_chat_pack)
- Next invoice preview shows €9 prorated charge

### Scenario K — Increase add-on quantity (stackable)

**Goal**: Org already has add-on with quantity=1, increases to 3.

**Setup**: Continue from Scenario J (org_test_active has 1× ai_chat_pack)

**Steps**:

| # | Action | Expected |
|---|---|---|
| 1 | UI: edit quantity in active add-on row to 3 | POST `/api/billing/add-addon` with `quantity: 3` |
| 2 | Backend: `stripe.Subscription.modify()` updates existing item with new quantity | Stripe sub item still has 1 ID, quantity=3 |
| 3 | Webhook subscription.updated | AddonSubscription.quantity updated to 3 |
| 4 | Effective chat = 80 + (50 × 3) = **230** | New 429 threshold |

**Verify**: NO new line_item created. Same `stripe_subscription_item_id` as before.

### Scenario L — Cancel add-on (no impact on base plan)

**Goal**: Remove add-on without canceling main subscription.

**Setup**: Continue from Scenario K (1 add-on with quantity=3)

**Steps**:

| # | Action | Expected |
|---|---|---|
| 1 | UI: click "Rimuovi" on active add-on | Confirmation modal |
| 2 | Confirm | DELETE `/api/billing/addon/addon_ai_chat_pack` |
| 3 | Backend: `stripe.Subscription.modify(items=[{id: si_xxx, deleted: true}])` | Stripe sub now has only main item |
| 4 | Webhook | AddonSubscription.status = `cancelled`, quantity unchanged (audit) |
| 5 | Main plan unchanged | `org.commercial_plan_slug = "core"`, `billing_status = "active"` |
| 6 | Effective chat = 80 (base only) | 81st chat → 429 |

**Critical**: `stripe.Subscription.cancel()` is **NEVER** called. Only `modify()`.

### Scenario M — Multiple add-ons coexist

**Goal**: Org buys 2 different add-ons simultaneously.

**Setup**: `org_test_active` clean (no add-ons)

**Steps**:

| # | Action | Expected |
|---|---|---|
| 1 | Buy `addon_ai_chat_pack` (qty 1) | 2 sub items |
| 2 | Buy `addon_orders_pack` (qty 2) | 3 sub items |
| 3 | Effective limits: chat = 80+50=130, orders = 200+(200×2)=600 | Both addons active |
| 4 | Cancel `addon_ai_chat_pack` | 2 sub items (orders pack remains) |
| 5 | Effective: chat = 80, orders = 600 | Mixed state correct |

### Scenario N — Add-on incompatibility check

**Goal**: Free user cannot buy add-ons (must upgrade first).

**Setup**: Login as `admin@org-test-canceled.test` (canceled → fell back to Free)

**Steps**:

| # | Action | Expected |
|---|---|---|
| 1 | Navigate to `/plans` | Add-on cards visible but with disabled state |
| 2 | Hover "+ Aggiungi" on `addon_ai_chat_pack` | Tooltip: "Disponibile dai piani a pagamento" (i18n in `fr` for this user) |
| 3 | Try direct API call POST `/api/billing/add-addon` | 400 ADDON_INCOMPATIBLE error |

---

## C. Plan rebrand + grandfather scenarios (O–Q)

### Scenario O — New customer sees new prices

**Goal**: Fresh signup after Onda 5 sees Solo €15, Commerce Starter €39, Commerce Pro €89.

**Setup**: Fresh org, no Stripe customer (pre-Onda 5 cleanup if needed)

**Steps**:

| # | Action | Expected |
|---|---|---|
| 1 | Navigate to `/plans` (anonymous or new account) | 4 cards: Free €0, Solo €15, Commerce Starter €39, Commerce Pro €89 |
| 2 | Click "Abbonati" on Commerce Starter | Stripe Checkout opens with €39/mo Price |
| 3 | Complete with test card 4242… | Webhook → org provisioned with NEW commercial_plan_slug=core, NEW stripe_price_id |
| 4 | DB check | `org.legacy_pricing_lock = false` (new customer, no lock) |

### Scenario P — Legacy customer keeps old price

**Goal**: Existing customer (active before Onda 5) keeps their old €19/€39/€79 price.

**Setup**: `org_test_active` was active BEFORE Onda 5 ran. After Onda 5:
- `org.legacy_pricing_lock = true`
- `org.legacy_price_ids = {si_xxx: price_legacy_yyy, ...}` (snapshot from Stripe)

**Steps**:

| # | Action | Expected |
|---|---|---|
| 1 | Login as legacy admin | UI shows badge "🔒 Legacy pricing" next to plan name |
| 2 | Navigate to `/settings/billing` | Price displayed = legacy price (e.g. €79 if was Pro) |
| 3 | Try upgrade Solo → Commerce Pro | `stripe.Subscription.modify()` uses **legacy price_id from `legacy_price_ids`**, not new €89 price |
| 4 | Stripe invoice preview shows OLD price | NO double-charge, NO price increase |

**This is the most important scenario** — verifies grandfather works end-to-end.

### Scenario Q — System admin overrides legacy lock

**Goal**: System admin can bring a legacy customer to new pricing on request.

**Steps**:

| # | Action | Expected |
|---|---|---|
| 1 | System admin → admin UI → org detail → "Remove legacy lock" button | Confirmation modal explaining "User will be charged at new prices on next renewal" |
| 2 | Confirm | `org.legacy_pricing_lock = false`, `legacy_price_ids = null` |
| 3 | Next billing cycle: Stripe charges at new price | OK |

---

## D. Quota warning scenarios (R–T)

### Scenario R — 80% warning email (Italian)

**Goal**: Italian admin gets quota warning email at 80%.

**Setup**:
- Login as `admin@org-test-active.test` (locale=it, plan=core, chat limit=80)
- Use 64 chat messages (= 80% of 80)

**Steps**:

| # | Action | Expected |
|---|---|---|
| 1 | Send 64 AI chat messages | DB: 64 AIUsageEvent records this month |
| 2 | Trigger sweep manually: `POST /api/admin/system/quota-sweep` (system admin only) OR wait 6h | Backend evaluates quotas |
| 3 | Email sent to admin@org-test-active.test in **Italian** | "Stai per raggiungere il limite di chat AI" |
| 4 | Email body shows 64/80 + CTA "Acquista pack" linking to `/plans?from=quota_warning&metric=chat` | i18n correct |
| 5 | Run sweep again 1h later | NO duplicate email (idempotency via OrgQuotaNotice record) |

### Scenario S — Exceeded paywall (English)

**Goal**: English admin hits quota → paywall component shown in UI.

**Setup**:
- Login as `admin@org-test-trialing.test` (locale=en, plan=core, chat limit=80)
- Use 80 chat messages

**Steps**:

| # | Action | Expected |
|---|---|---|
| 1 | Send 81st AI chat | Backend returns 429 QUOTA_EXCEEDED |
| 2 | Frontend catches 429 → shows `<UpgradePaywall />` modal | Modal in **English**: "You've reached your AI chat limit" |
| 3 | CTA primary "Add chat pack" → `/plans?focus=addon_ai_chat_pack` | Click → goes to plans page with addon highlighted |
| 4 | CTA secondary "Upgrade plan" → `/plans` | OK |
| 5 | Email "limit exceeded" sent (idempotent — only once per cycle) | OK |

### Scenario T — Multi-language email coverage

**Goal**: All 4 locales render quota emails correctly.

**Setup**: 4 test orgs, one per locale (it, en, de, fr), all approaching quota.

**Steps**:

| # | Action | Expected |
|---|---|---|
| 1 | Set up each org at 80% of one metric | OK |
| 2 | Trigger sweep | 4 emails sent, one per locale |
| 3 | Verify subject + body for each | All 4 languages render correctly, no missing keys, all CTAs translated |

---

## E. Commerce-flow scenarios (U–W)

### Scenario U — Orders monthly quota enforced

**Goal**: Free user is limited to 30 orders/month + transformed to contact_request after.

**Setup**: `org_test_canceled` on `free` plan (commerce_free, orders_monthly=30, checkout_stripe=0)

**Steps**:

| # | Action | Expected |
|---|---|---|
| 1 | Public storefront: place 30 orders | All 30 created with `status=contact_request` (NOT Stripe checkout, since checkout_stripe=0) |
| 2 | 31st order attempt | Either: still goes to contact_request (soft warning to admin) OR returns 429 with "limite ordini raggiunto" |
| 3 | Org upgrades to Commerce Starter | orders_monthly = 200, checkout_stripe = -1 |
| 4 | New orders go through Stripe checkout | OK |

### Scenario V — Stores max enforced

**Goal**: Commerce Starter (1 store) tries to create 2nd → 429.

**Setup**: `org_test_active` on Commerce Starter (stores_max=1)

**Steps**:

| # | Action | Expected |
|---|---|---|
| 1 | Has 1 active store | OK |
| 2 | Try POST `/api/stores` to create 2nd | 429 STORES_MAX_REACHED with paywall message |
| 3 | Buy `addon_extra_store` (Pro only) → BLOCKED (incompatible_plans) | Test addon compatibility |
| 4 | Upgrade to Commerce Pro (stores_max=3) | Now can create up to 3 stores |
| 5 | Buy 2× `addon_extra_store` → effective stores_max = 3+2 = 5 | OK |

### Scenario W — checkout_stripe flag UI

**Goal**: Storefront UI adapts CTA based on checkout_stripe flag.

**Steps**:

| Plan | checkout_stripe | Storefront button | Click action |
|---|---|---|---|
| Free | 0 | "Richiedi info" | Form contatto, no Stripe |
| Solo | 0 | (commerce disabled, store hidden) | N/A |
| Commerce Starter | -1 | "Acquista" | Stripe Checkout |
| Commerce Pro | -1 | "Acquista" | Stripe Checkout |

---

## F. Subscription lifecycle scenarios (X–Z) — **NO DUPLICATE BILLING**

These scenarios verify the most user-confusing flow: cancel → free → resubscribe.
**Critical**: at NO point does the user see double charges.

### Scenario X — Cancel paid → fall to Free → re-subscribe to same plan

**Goal**: Cancel a Commerce Starter sub at period end, become Free, then subscribe again to Commerce Starter.

**Setup**: `org_test_active` on Commerce Starter (paid, current_period_end = 30 days from now)

**Steps**:

| # | Action | Expected |
|---|---|---|
| 1 | UI: "Cancel subscription" → confirms cancel at period end | `org.cancel_at_period_end = true`, status still `active` until period end |
| 2 | Stripe still bills nothing extra (already paid for current period) | Invoice preview = €0 |
| 3 | At period end (advance Stripe clock for testing OR wait), Stripe fires `customer.subscription.deleted` | Webhook: org provisioned to Free, `stripe_subscription_id = null`, `commercial_plan_slug = free` |
| 4 | UI: shows Free plan + "Sottoscrivi un piano" CTA | OK |
| 5 | User clicks "Subscribe to Commerce Starter" | NEW Stripe Checkout session created (NOT a modify of canceled sub) |
| 6 | Same Stripe customer (`cus_xxx` reused), NEW Stripe subscription (`sub_yyy`) | OK |
| 7 | Charged once for new period (nothing for the gap between cancel and resubscribe) | NO double charge |

**Verify in Stripe Dashboard**:
- Old subscription: status `canceled`
- New subscription: status `active`
- Customer has 2 subscriptions in history (1 canceled, 1 active)
- Invoices: 1 paid for old period, 1 paid for new period — no overlapping charges

### Scenario Y — Cancel paid → re-subscribe to DIFFERENT plan

**Goal**: User cancels Commerce Starter, then subscribes to Commerce Pro.

**Setup**: `org_test_active`, was on Commerce Starter, just canceled (now on Free)

**Steps**:

| # | Action | Expected |
|---|---|---|
| 1 | From Free, click "Subscribe to Commerce Pro" | NEW Stripe Checkout, NEW sub |
| 2 | If user had a 14gg trial originally on Commerce Starter, the new Commerce Pro sub does NOT get a fresh trial | `org.trial_ends_at` stays `null` (already used trial historically) |
| 3 | Invoice for full first month €89, no trial discount | OK |

**Critical**: trial is org-lifetime, not plan-lifetime. The check is `org.trial_ends_at != null` once
the org has ever started a trial, regardless of plan.

### Scenario Z — Trial expired → upgrade vs do nothing

**Goal**: A trialing user has 2h grace after trial_ends_at, then becomes read-only.

**Setup**: `org_test_trialing` on Commerce Starter trial, simulate trial expiry by setting `trial_ends_at` 3h ago.

**Steps**:

| # | Action | Expected |
|---|---|---|
| 1 | Backend billing_sweep runs (cron or manual) | Detects trial expired > 2h, calls Stripe to sync status |
| 2 | If Stripe reports payment NOT collected (Stripe normally fails first invoice if user didn't add card during trial) | Stripe sub status = `incomplete_expired` or `canceled` → org becomes `free` |
| 3 | If Stripe collected payment automatically | Org becomes `active`, normal flow continues |
| 4 | UI: BillingStatusBanner BILLING_TRIAL_EXPIRED shown if status = past_due | "Sottoscrivi ora" CTA |
| 5 | User upgrades to Solo | Stripe Checkout in new mode (no trial since already used) |

---

## G. System admin scenarios (AA–CC)

### Scenario AA — Custom plan creation for strategic customer

**Goal**: System admin creates a custom plan with override for a specific org.

**Setup**: Login as system_admin

**Steps**:

| # | Action | Expected |
|---|---|---|
| 1 | Admin UI → Organizations → org_test_active → "Custom plan" tab | Form with template dropdown |
| 2 | Select template = Commerce Pro | Form pre-fills with Pro limits |
| 3 | Override: AI chat = 500, orders_monthly = 5000, price_monthly = €49 | Save |
| 4 | Backend: creates new CustomCommercialPlan record (slug `custom_<orgid>_<timestamp>`) + new Stripe Price (price_data inline at checkout next time) | DB: new commercial_plan with `is_custom=true, organization_id=org_test_active` |
| 5 | Admin clicks "Apply now" | Org's commercial_plan_slug = new custom slug, modify_subscription if active sub |
| 6 | UI now shows custom plan name with custom limits | Effective limits respected |

### Scenario BB — Trial extension

**Goal**: System admin extends trial for a customer by 7 days.

**Setup**: `org_test_trialing` with trial_ends_at = today

**Steps**:

| # | Action | Expected |
|---|---|---|
| 1 | Admin UI → org_test_trialing → "Trial Extension" tab | Input `extra_days` + reason text |
| 2 | Set `extra_days = 7`, reason = "Beta tester partner" | Save |
| 3 | Backend: `org.trial_ends_at += 7 days` | OK |
| 4 | Stripe sub trial NOT extended in Stripe (we don't modify Stripe trial directly) | Stripe will still fail to charge if no card on file at original date |
| 5 | Backend billing_sweep skips this org for past_due flag because we manually set trial date | OK |
| 6 | Audit log entry: action=trial_extended, system_admin_id, target_org, extra_days, reason | OK |

### Scenario CC — Impersonate for support

**Goal**: System admin impersonates an admin user for debugging.

**Steps**:

| # | Action | Expected |
|---|---|---|
| 1 | Admin UI → user list → admin@org-test-active.test → "Impersonate" button | Confirmation modal |
| 2 | Confirm | Backend: generates JWT with `impersonate_user_id`, TTL 30min, audit log entry |
| 3 | Browser redirects to impersonated session | Top banner: "🔴 Impersonating admin@…" |
| 4 | All actions logged with impersonate context | OK |
| 5 | Click "Stop impersonating" | Returns to system_admin session |

---

## J. Onda 9.A — Native cancel/reactivate + admin manual add-ons

**Pre-req for J**: Ondes 1–8 + 9.A all deployed. This section validates the
in-app cancel/reactivate flow (no Stripe Customer Portal needed) and the
new admin-manual add-on assignment.

### Scenario DD — Native cancel at period end (in-app)

1. Use **org_test_paid_active** (Commerce Pro, billing_status=active, has Stripe sub).
2. Login as admin → /settings → Billing.
3. Verify the new hero card shows "Commerce Pro · €89/mese · Prossimo rinnovo: <date>".
4. Click **Cancella abbonamento** (red ghost button in Section C).
5. Modal opens with two options pre-selected to "Cancella a fine periodo".
6. Type a reason ("Test scenario DD"), keep "Cancella a fine periodo".
7. Click **Conferma cancellazione a fine periodo**.

**Expected**:
- Toast "Abbonamento programmato per la cancellazione a fine periodo".
- `billing.cancel_at_period_end = true` in `/api/billing/status`.
- Cancel button DISAPPEARS from Section C.
- "Riprendi abbonamento" button appears (primary blue).
- Hero card subline now reads "Accesso fino al <date> (cancellazione programmata)".
- Orange `cancel-at-period-end warning` banner visible.
- Stripe Dashboard → Subscription → "Cancellation: Cancel at period end" set.
- AuditLog entry: `action="user_cancelled_subscription"`, `details.at_period_end=true`,
  `details.reason="Test scenario DD"`.

### Scenario EE — Reactivate after cancel-pending

1. Continue from DD (`cancel_at_period_end=true`).
2. Click **Riprendi abbonamento**.

**Expected**:
- Toast "Abbonamento riattivato. La cancellazione è stata annullata".
- `billing.cancel_at_period_end = false` in `/api/billing/status`.
- "Riprendi abbonamento" button DISAPPEARS.
- "Cancella abbonamento" button reappears.
- Hero card subline reverts to "Prossimo rinnovo: <date>".
- Orange warning banner disappears.
- Stripe Dashboard → Subscription → "Cancellation: None".
- AuditLog: `action="user_reactivated_subscription"`.

### Scenario FF — Native immediate cancel (in-app)

1. Use **org_test_paid_active** (reset state first, sub active, no cancel pending).
2. Click **Cancella abbonamento** → modal.
3. Switch radio to "Cancella subito" (red highlight).
4. Type reason "Test FF", click **Conferma cancellazione immediata**.

**Expected**:
- Toast "Abbonamento cancellato. Il piano è stato riportato a Free".
- Within 3-5s (webhook delivery), `billing.plan = "free"`, `billing_status = "canceled"` or `"none"`.
- Hero card now shows "Free · Gratis".
- Stripe Dashboard → Subscription "Status: Canceled".
- AuditLog: `action="user_cancelled_subscription"`, `details.at_period_end=false`.

### Scenario GG — Trial-once enforcement (CRITICAL — explicitly requested)

The user MUST NOT receive a second trial after the first has been used.

1. Pick a fresh test org **org_test_trial_eligible** (no `has_used_trial`, never subscribed).
2. Login → /plans → click **Inizia prova gratuita** on Commerce Starter.
3. Complete Stripe Checkout with a 4242… card.
4. Wait for webhook → confirm `billing_status="trialing"`, `trial_ends_at = <14 days>`.
5. Wait for trial expiry (or manually set `trial_ends_at` to 1h ago + run `quota_warning_sweep` to fire trial-ending notice).
6. Org status transitions to `past_due` or `canceled` (depends on payment method outcome).
7. Now: as the SAME admin, go to /plans → click **Inizia prova gratuita** on Commerce Pro.

**Expected**:
- Stripe Checkout opens but shows the FULL price (no trial banner).
- The Stripe-side `subscription.trial_end` field is null on creation.
- After checkout: `billing_status="active"` immediately (no trialing window).
- Backend fingerprint check (Stripe `customer.id` reused) prevents trial reissuance.
- `subscription.metadata.trial_used` flag is set to `true` on the org's customer in Stripe.

**Verification command**:
```js
// In MongoDB shell
db.organizations.findOne({id: "<orgid>"}, {has_used_trial: 1, trial_ends_at: 1, billing_status: 1})
// Expected: has_used_trial: true (or equivalent flag), billing_status="active" (not "trialing")
```

**Stripe verification**:
- Stripe Dashboard → Customer → Subscriptions: only the new sub shows `trial=No`.

### Scenario HH — Admin manually assigns add-on (custom override)

1. Login as **system_admin** → /admin → Organizations tab.
2. Pick **org_test_paid_active**, open detail dialog.
3. Scroll to AdminOrgBillingActions panel → click **Add-ons** tab.
4. Verify the "Active add-ons" list reflects current state.
5. In "Assign new add-on", pick `addon_orders_pack` (+200 orders), quantity 1.
6. Reason: "Comp for partner Q2 deal", Notes: "Granted for 90 days".
7. Click **Assign add-on**.

**Expected**:
- Active add-ons list refreshes; new row shows "+200 orders ×1" with **purple "custom override" badge**.
- Row subline shows "by system_admin:<id>".
- AuditLog: `action="admin_assign_addon"`, with `details.notes`, `details.reason`, `details.addon_subscription_id`.
- Org's `/api/billing/usage-summary` now reflects the +200 boost on `commerce.orders_monthly` effective_limit.
- Stripe is NOT touched — the org's Stripe subscription items unchanged.
- Org admin viewing /settings → Billing sees the new add-on in their "Active add-ons" list with the override badge.

### Scenario II — Admin manually removes add-on

1. Continue from HH (org has the custom-override addon).
2. In Add-ons tab, click the trash icon next to the "+200 orders" row.
3. Browser prompt asks for reason → enter "Test II — removal".
4. Confirm.

**Expected**:
- Active addons list refreshes; the +200 orders row is gone.
- AuditLog: `action="admin_remove_addon"`, `details.was_custom_override=true`, `details.reason="Test II — removal"`.
- Effective `orders_monthly` limit drops back to plan baseline.
- No "Stripe warning" alert (it was an override, no Stripe item).

### Scenario JJ — Admin removes Stripe-linked addon (warning displayed)

1. Have an org with a real Stripe-linked addon (e.g. user bought `addon_extra_store` via /plans).
2. Admin opens Add-ons tab → row shows NO "custom override" badge (it's Stripe-linked).
3. Admin clicks trash → enters reason "Test JJ".

**Expected**:
- DB row marked `status=cancelled`.
- `window.alert` displays the Stripe warning: "This add-on was linked to a Stripe subscription. The DB row is cancelled but the Stripe item is still active — use the Stripe Dashboard if you also need to stop billing."
- Admin must manually remove the Stripe `subscription_item` to actually stop charges.
- AuditLog records `was_custom_override=false` for forensic clarity.

---

## H. Cleanup matrix

Reset specific state between scenarios to avoid pollution:

| Section | Reset command |
|---|---|
| B (add-on) | `db.addon_subscriptions.deleteMany({organization_id: <orgid>})` + Stripe.Subscription.modify removing addon items |
| C (rebrand) | Restore `org.legacy_pricing_lock = false` + restore `legacy_price_ids = null` |
| D (quota) | `db.org_quota_notices.deleteMany({organization_id: <orgid>})` + reset usage events for current month |
| E (commerce) | `db.orders.deleteMany({organization_id: <orgid>, status: "contact_request"})` |
| F (lifecycle) | Full reset via `seed_test_orgs.py --reset` |
| G (admin) | `db.commercial_plans.deleteMany({is_custom: true, organization_id: <orgid>})` |

---

## I. Go/No-Go checklist for v5.8 production rollout

### Functional completeness

- [ ] All 4 add-on plans seeded in DB with valid `stripe_price_id_monthly`
- [ ] All 5 commercial plans renamed to new public names
- [ ] `commerce_disabled`, `commerce_starter`, `commerce_pro`, `commerce_unlimited` PricingPlan exist
- [ ] All existing orgs have `legacy_pricing_lock = true` set
- [ ] `quota_warning_sweep` cron job is running every 6h
- [ ] **Onda 9.A**: native cancel button appears in `BillingSection` Section C for paid orgs without cancel-pending
- [ ] **Onda 9.A**: native reactivate button appears when `cancel_at_period_end=true`
- [ ] **Onda 9.A**: Scenario GG (trial-once enforcement) verified — second trial NOT issued after first use
- [ ] **Onda 9.A.2**: admin Add-ons tab visible in OrganizationsTab detail dialog
- [ ] **Onda 9.A.2**: custom-override add-ons surface in user-facing /billing/my-addons

### Backward compatibility

- [ ] All v5.7 scenarios (A–I) still pass after v5.8 deploy
- [ ] No org with active Stripe sub experiences price change at next renewal (legacy lock works)
- [ ] Webhook idempotency unchanged (`BillingEvent.stripe_event_id` unique index intact)

### Multi-language

- [ ] All 4 locales (it/en/de/fr) render quota warning emails correctly
- [ ] All UI banners read `User.locale` correctly

### Stripe operational

- [ ] Stripe live mode has 4 add-on Products + Prices
- [ ] Stripe live mode has updated Product names
- [ ] Old Stripe Prices still exist with `active=false` (grandfather)

### Observability

- [ ] Logs of `quota_warning_sweep` show "sent N quota emails"
- [ ] Stripe Dashboard → Events shows no failed webhooks during initial 48h

### Rollback plan

- [ ] `pre-onda1to9-rollback` Docker images tagged on prod
- [ ] Mongo backup taken pre-deploy in `/opt/margin-sentinel/backups/pre-v58/`
- [ ] Rollback script tested in staging

### Decision

- [ ] Tech lead sign-off
- [ ] Product owner sign-off
- [ ] All scenarios B–G executed at least once in staging
