# AFianco Billing v5.7/v5.7.1 — Manual Integrated Testing Runbook

**Scope**: Checkout recovery verification, webhook path, verify fallback, UI state, DB persistence.
**Version**: v5.7.1 (2026-03-20)
**Audience**: Developer or QA executing manual end-to-end tests before controlled production rollout.

---

## A. Preconditions & Setup

### A1. Environment Variables

Your `backend/.env` must contain:

| Variable | Required | Example / Notes |
|---|---|---|
| `STRIPE_SECRET_KEY` | Yes | `sk_test_51TCxk...` — Stripe test mode key |
| `STRIPE_PUBLISHABLE_KEY` | Yes | `pk_test_51TCxk...` — Stripe test mode key |
| `STRIPE_WEBHOOK_SECRET` | Conditional | `whsec_...` — set or unset depending on scenario |
| `FRONTEND_URL` | Yes | `http://localhost:3000` |
| `MONGO_URL` | Yes | `mongodb://localhost:27017` |
| `DB_NAME` | Yes | e.g. `test_database` |

**Toggle for scenarios**: You will comment/uncomment `STRIPE_WEBHOOK_SECRET` between scenarios. Keep the rest constant.

### A2. Stripe Test Mode Setup

1. **Stripe Dashboard** — Log into [dashboard.stripe.com](https://dashboard.stripe.com) in **test mode** (toggle in top-right).
2. **Products & Prices** — Verify that Stripe products exist for `core` and `pro` plans. Each must have a monthly price ID stored in the `commercial_plans` MongoDB collection under `stripe_price_id_monthly`. If not configured yet, run `scripts/setup_stripe.py` or create them manually.
3. **Stripe CLI** — Install and authenticate `stripe` CLI:
   ```
   stripe login
   stripe listen --forward-to localhost:8000/api/billing/webhooks
   ```
   Copy the `whsec_...` value printed by `stripe listen` into your `.env` as `STRIPE_WEBHOOK_SECRET`.
4. **Test card numbers**:
   - Success: `4242 4242 4242 4242` (any future expiry, any CVC)
   - Decline: `4000 0000 0000 0002`

### A3. Test Accounts & Organizations

You need **two** test accounts in the local DB:

| Label | Role | Org | Purpose |
|---|---|---|---|
| **Admin A** | `admin` | `org_alpha` | Primary test account — performs all checkout flows |
| **Admin B** | `admin` | `org_beta` | Cross-org security check (Scenario F) |

Both must start on the `free` plan with `billing_status: "none"` and no `stripe_customer_id`. Reset before each full run:

```js
// MongoDB shell — reset org to clean free state
db.organizations.updateOne(
  { id: "org_alpha" },
  { $set: {
      commercial_plan_slug: "free",
      billing_status: "none",
      stripe_customer_id: null,
      stripe_subscription_id: null,
      billing_interval: null,
      trial_ends_at: null,
      current_period_end: null,
      cancel_at_period_end: false,
      plan_assigned_by: "system"
  }}
)
```

Repeat for `org_beta`.

### A4. Catalog / Seed Assumptions

The following commercial plans must exist (seeded automatically on startup):

| Slug | Self-serve | Trial days | Price |
|---|---|---|---|
| `free` | No (baseline) | 0 | 0 EUR |
| `core` | Yes | 14 | 39 EUR/mo |
| `pro` | Yes | 14 | 79 EUR/mo |
| `enterprise` | No (contact sales) | 0 | 199 EUR/mo |

Verify: `db.commercial_plans.find({}, {slug:1, is_self_serve:1, trial_days:1, stripe_price_id_monthly:1})`.
The `core` and `pro` plans **must** have non-null `stripe_price_id_monthly` values.

### A5. What to Monitor

Open these in separate terminals/tabs throughout all scenarios:

| Monitor | How | What to watch |
|---|---|---|
| **Backend logs** | Terminal running `uvicorn` or `python server.py` | `[webhook]`, `[verify]`, `Provisioned plan`, warnings |
| **Stripe CLI** | Terminal running `stripe listen --forward-to ...` | Event delivery status, `200` vs `400` vs `500` responses |
| **Browser DevTools → Network** | Chrome/Firefox F12 → Network tab | `/billing/status`, `/billing/verify-checkout` calls |
| **Browser DevTools → Console** | Chrome/Firefox F12 → Console tab | JS errors, fetch failures |
| **Stripe Dashboard → Events** | dashboard.stripe.com → Developers → Events | `checkout.session.completed` event status |
| **MongoDB** | `mongosh` or Compass connected to test DB | `organizations` and `billing_events` collections |

### A6. Startup Verification

1. Start the backend with `STRIPE_SECRET_KEY` set but `STRIPE_WEBHOOK_SECRET` **commented out**.
2. **EXPECT in logs**: `WARNING — STRIPE_SECRET_KEY is set but STRIPE_WEBHOOK_SECRET is missing. Stripe webhook events will be rejected — billing state will not propagate after checkout. For local dev, run 'stripe listen' and copy the whsec_... value into .env.`
3. **EXPECT**: `Free plan integrity check passed (4 module mappings)`
4. Stop the backend, uncomment `STRIPE_WEBHOOK_SECRET`, restart. Confirm the warning **does not appear**.

---

## B. Test Scenarios

### Scenario A — Happy Path: Webhook Configured

**Goal**: Verify the normal checkout flow where the webhook lands before polling exhausts.

**Setup**:
- `STRIPE_WEBHOOK_SECRET` is set and `stripe listen` is running
- `org_alpha` is on `free` plan, `billing_status: "none"`
- Log in as **Admin A**

**Steps**:

| # | Action | Where |
|---|---|---|
| 1 | Navigate to Settings page | Browser |
| 2 | Verify BillingSection shows plan badge = "Free", status badge = "none" | Browser UI |
| 3 | Click "Passa a un piano a pagamento" (upgrade button) | Browser UI |
| 4 | In UpgradeDialog, select **Core** plan, click confirm | Browser UI |
| 5 | You are redirected to Stripe Checkout hosted page | Browser |
| 6 | Enter test card `4242 4242 4242 4242`, any future expiry, any CVC, complete checkout | Stripe Checkout |
| 7 | Stripe redirects you back to `/settings?billing_success=1&session_id=cs_test_...` | Browser |
| 8 | Observe: loading toast "Aggiornamento del piano in corso..." appears | Browser UI |
| 9 | Wait ≤5 seconds | — |
| 10 | Observe: success toast "Piano aggiornato con successo!" appears | Browser UI |
| 11 | Verify BillingSection now shows: plan = "AFianco Core", status = "trialing" | Browser UI |

**Expected backend logs** (in order):
```
[webhook] checkout.session.completed event_id=evt_... session_id=cs_test_... org_id=org_alpha plan=core interval=month
Provisioned plan 'core' for org 'org_alpha': cancelled N subs, created 4 subs (by: stripe)
```

**Expected Stripe CLI output**:
```
checkout.session.completed [200] POST ...
```

**Expected Stripe Dashboard**: Event `checkout.session.completed` shows status "Succeeded".

**Expected DB state** (`db.organizations.findOne({id:"org_alpha"})`):
```
commercial_plan_slug: "core"
billing_status: "trialing"
billing_interval: "month"
stripe_subscription_id: "sub_test_..."  (non-null)
stripe_customer_id: "cus_test_..."      (non-null)
trial_ends_at: <14 days from now ISO>
plan_assigned_by: "stripe"
```

**Expected `/billing/status` response** (check in Network tab):
```json
{
  "commercial_plan_slug": "core",
  "billing_status": "trialing",
  "billing_interval": "month",
  "trial_ends_at": "2026-04-03T...",
  "current_period_end": "2026-04-03T...",
  "cancel_at_period_end": false,
  "plan_assigned_by": "stripe",
  "has_stripe_customer": true,
  "has_had_trial": true
}
```

**Expected Network tab observation**: Multiple `GET /billing/status` poll calls visible. The verify endpoint `/billing/verify-checkout` should **NOT** be called (webhook landed during Phase 1 polling).

**Pass/Fail criteria**:
- [ ] Success toast within ~5s
- [ ] Plan badge shows "AFianco Core"
- [ ] Status badge shows "trialing"
- [ ] Trial end date ~14 days out
- [ ] `stripe_subscription_id` set in DB
- [ ] No `/billing/verify-checkout` call in Network tab
- [ ] No errors in backend logs

---

### Scenario B — Recovery Path: Webhook Secret Missing

**Goal**: Verify the v5.7 verify fallback provisions the plan when webhooks cannot land.

**Setup**:
- **Stop `stripe listen`**
- **Comment out `STRIPE_WEBHOOK_SECRET`** in `.env`
- Restart backend (confirm the startup warning appears in logs)
- Reset `org_alpha` to `free` / `billing_status: "none"` (also clear `stripe_customer_id` and `stripe_subscription_id`)
- Log in as **Admin A**

**Steps**:

| # | Action | Where |
|---|---|---|
| 1 | Navigate to Settings, verify plan = "Free", status = "none" | Browser UI |
| 2 | Click upgrade → select **Core** → complete Stripe Checkout with test card | Browser → Stripe |
| 3 | Return to app: `/settings?billing_success=1&session_id=cs_test_...` | Browser |
| 4 | Observe: loading toast "Aggiornamento del piano in corso..." | Browser UI |
| 5 | Wait ~16-18 seconds (Phase 1 polling: 8 attempts × 2s + 1.5s initial delay) | — |
| 6 | Observe in Network tab: 8× `GET /billing/status` calls, all returning `"free"` | DevTools |
| 7 | Observe in Network tab: `POST /billing/verify-checkout` call fires | DevTools |
| 8 | Observe: success toast "Piano aggiornato con successo!" appears | Browser UI |
| 9 | Verify BillingSection shows: plan = "AFianco Core", status = "trialing" | Browser UI |

**Expected backend logs**:
```
WARNING — STRIPE_SECRET_KEY is set but STRIPE_WEBHOOK_SECRET is missing...
  (at startup)

[verify] Provisioned org 'org_alpha' with plan='core' status='trialing' via checkout recovery
verify-checkout session_id=cs_test_... org_id=org_alpha result=provisioned
```

Note: **No `[webhook]` log lines** should appear because the webhook is rejected at signature verification.

If `stripe listen` was still running (forwarding events), you would also see:
```
Webhook signature verification failed: STRIPE_WEBHOOK_SECRET not configured
```

**Expected Stripe Dashboard**: The `checkout.session.completed` event exists but shows as "Failed" (endpoint returned 400) because the webhook was rejected.

**Expected DB state** (same as Scenario A):
```
commercial_plan_slug: "core"
billing_status: "trialing"
stripe_subscription_id: "sub_test_..."
plan_assigned_by: "stripe"
```

**Expected `/billing/status` response**: Same shape as Scenario A.

**Expected Network tab — critical observation**: The `/billing/verify-checkout` POST must appear AFTER the 8th `/billing/status` GET. The verify response should contain `"status": "provisioned"`.

**Pass/Fail criteria**:
- [ ] Loading toast visible for ~17s (Phase 1 polling period)
- [ ] `/billing/verify-checkout` appears in Network tab
- [ ] Verify response body contains `"status": "provisioned"`
- [ ] Success toast appears after verify completes
- [ ] Plan badge shows "AFianco Core", status = "trialing"
- [ ] DB state matches expected
- [ ] No `[webhook] checkout.session.completed` log line (webhook rejected)
- [ ] `[verify] Provisioned org ...` log line present

---

### Scenario C — Idempotent Refresh After Recovery

**Goal**: Verify that reloading the page after recovery does not regress state, and calling verify again returns `already_provisioned`.

**Setup**:
- Continue directly from Scenario B (org_alpha is now on Core/trialing via verify recovery)
- `STRIPE_WEBHOOK_SECRET` still commented out

**Steps**:

| # | Action | Where |
|---|---|---|
| 1 | Hard-refresh the Settings page (Ctrl+Shift+R) | Browser |
| 2 | Verify BillingSection loads with plan = "AFianco Core", status = "trialing" | Browser UI |
| 3 | Verify no polling or verify calls fire (no `billing_success=1` in URL) | DevTools Network |
| 4 | Manually call verify via curl: | Terminal |

```bash
curl -X POST http://localhost:8000/api/billing/verify-checkout \
  -H "Authorization: Bearer <admin_a_token>" \
  -H "Content-Type: application/json" \
  -d '{"session_id": "<cs_test_... from Scenario B>"}'
```

| # | Action | Where |
|---|---|---|
| 5 | Verify curl response | Terminal |

**Expected curl response**:
```json
{
  "status": "already_provisioned",
  "commercial_plan_slug": "core",
  "billing_status": "trialing",
  "billing_interval": "month",
  "trial_ends_at": "2026-04-03T...",
  "current_period_end": "2026-04-03T..."
}
```

**Expected backend log**:
```
[verify] Org 'org_alpha' already provisioned with plan='core' sub='sub_test_...' status='trialing' -- no-op
verify-checkout session_id=cs_test_... org_id=org_alpha result=already_provisioned
```

**Expected DB state**: Unchanged from end of Scenario B. No `plan_assigned_at` timestamp update.

**Pass/Fail criteria**:
- [ ] Page reload shows correct plan without any flash of "Free"
- [ ] Curl returns `"status": "already_provisioned"` (not `"provisioned"`)
- [ ] Backend log shows `already provisioned ... -- no-op`
- [ ] No `provision_commercial_plan` call in logs (no re-provisioning)
- [ ] DB `plan_assigned_at` timestamp did NOT change

---

### Scenario D — Cancel Checkout Before Completion

**Goal**: Verify that cancelling on the Stripe Checkout page does not trigger polling, verify, or state changes.

**Setup**:
- Reset `org_alpha` to `free` / `billing_status: "none"`
- Log in as **Admin A**

**Steps**:

| # | Action | Where |
|---|---|---|
| 1 | Navigate to Settings → verify plan = "Free" | Browser UI |
| 2 | Click upgrade → select Core → redirected to Stripe Checkout | Browser |
| 3 | Click the **back arrow** or "← Back" link on Stripe Checkout page | Stripe Checkout |
| 4 | Stripe redirects to `/settings?billing_cancelled=1` | Browser |
| 5 | Verify: URL gets cleaned to `/settings` (no query params) | Browser |
| 6 | Verify: **no** loading toast appears | Browser UI |
| 7 | Verify: **no** polling calls to `/billing/status` in Network tab | DevTools |
| 8 | Verify: plan still shows "Free", status = "none" | Browser UI |

**Expected backend logs**: No checkout-related logs. Possibly a standard `/billing/status` GET from the billing context initial load.

**Expected Stripe Dashboard**: The Checkout Session exists with status `expired` or `open` (not `complete`).

**Expected DB state**: Unchanged — still `commercial_plan_slug: "free"`, `billing_status: "none"`.

**Pass/Fail criteria**:
- [ ] No toast of any kind related to checkout
- [ ] No polling or verify calls in Network tab
- [ ] Plan remains "Free"
- [ ] No state change in DB

---

### Scenario E — Missing session_id on Return URL

**Goal**: Verify graceful degradation when `session_id` is absent from the return URL (backward compatibility with old bookmarks or manual URL edits).

**Setup**:
- `STRIPE_WEBHOOK_SECRET` commented out (so webhook won't land)
- Reset `org_alpha` to `free`

**Steps**:

| # | Action | Where |
|---|---|---|
| 1 | Complete a checkout flow normally through Stripe | Browser → Stripe |
| 2 | **Before Stripe redirects**, intercept by manually navigating to: `http://localhost:3000/settings?billing_success=1` (no `session_id` param) | Browser address bar |
| 3 | Observe: loading toast appears, polling begins | Browser UI |
| 4 | Wait ~17s for polling to exhaust | — |
| 5 | Observe in Network tab: **no** `/billing/verify-checkout` call (no session_id to use) | DevTools |
| 6 | Observe: pending toast appears: "Pagamento ricevuto. L'attivazione del piano è in corso, ricarica tra qualche istante." | Browser UI |

**Expected backend logs**: Only `/billing/status` GET calls, no verify-related logs.

**Expected behavior**: The v5.6 honest-fallback path. The pending toast with 8-second duration appears. No crash, no error toast.

**Pass/Fail criteria**:
- [ ] No JavaScript errors in console
- [ ] Pending (info) toast appears, NOT an error toast
- [ ] No `/billing/verify-checkout` call
- [ ] App remains functional

---

### Scenario F — Wrong-Org Verify Protection

**Goal**: Verify that Admin B cannot use a session_id belonging to Admin A's org.

**Setup**:
- Complete Scenario A or B so you have a valid `session_id` (e.g. `cs_test_ABC`) that belongs to `org_alpha`
- Note the session_id from the Stripe Dashboard or from browser Network tab

**Steps**:

| # | Action | Where |
|---|---|---|
| 1 | Obtain a valid Bearer token for **Admin B** (org_beta) | Auth flow |
| 2 | Call verify with Admin A's session_id using Admin B's token: | Terminal |

```bash
curl -X POST http://localhost:8000/api/billing/verify-checkout \
  -H "Authorization: Bearer <admin_b_token>" \
  -H "Content-Type: application/json" \
  -d '{"session_id": "cs_test_ABC"}'
```

**Expected response**: HTTP 403 Forbidden
```json
{
  "detail": "Session does not belong to this organization (session org_id=org_alpha, caller org_id=org_beta)"
}
```

**Expected backend log**:
No `[verify] Provisioned ...` log. The `PermissionError` is caught by the router and mapped to 403.

**Expected DB state**: `org_beta` is completely unchanged. `org_alpha` is unchanged.

**Pass/Fail criteria**:
- [ ] HTTP 403 returned (not 400, not 200)
- [ ] Error detail mentions org mismatch
- [ ] Neither org's billing state changed

---

### Scenario G — Invalid session_id

**Goal**: Verify that a garbage or expired session_id returns 400, not 500.

**Steps**:

```bash
# Garbage session_id
curl -X POST http://localhost:8000/api/billing/verify-checkout \
  -H "Authorization: Bearer <admin_a_token>" \
  -H "Content-Type: application/json" \
  -d '{"session_id": "cs_test_NONEXISTENT_garbage_id"}'
```

**Expected response**: HTTP 400 Bad Request
```json
{
  "detail": "Invalid or expired checkout session: ..."
}
```

**Expected backend log**:
No error-level log (this is a handled ValueError, not an unhandled exception).

**Pass/Fail criteria**:
- [ ] HTTP 400 (not 500)
- [ ] Error detail mentions "Invalid or expired"
- [ ] No 500-level error in backend logs

---

### Scenario H — Free Plan Baseline & Cannot Buy Free

**Goal**: Verify that a fresh free-plan user sees the correct UI and that attempting to checkout "free" is blocked.

**Setup**:
- Reset `org_alpha` to `free` / `billing_status: "none"`
- Log in as **Admin A**

**Steps**:

| # | Action | Where |
|---|---|---|
| 1 | Navigate to Settings → BillingSection | Browser UI |
| 2 | Verify: plan badge = "Free", status badge = "none" | Browser UI |
| 3 | Verify: "Passa a un piano a pagamento" button is visible (not "Cambia piano") | Browser UI |
| 4 | Verify: "Gestisci fatturazione" button is NOT visible (no `stripe_customer_id`) | Browser UI |
| 5 | Attempt to create checkout for "free" via curl: | Terminal |

```bash
curl -X POST http://localhost:8000/api/billing/checkout-session \
  -H "Authorization: Bearer <admin_a_token>" \
  -H "Content-Type: application/json" \
  -d '{"plan_slug": "free", "interval": "month"}'
```

**Expected response**: HTTP 400 Bad Request
```json
{
  "detail": "The Free plan is the system baseline and cannot be purchased through checkout. ..."
}
```

| # | Action | Where |
|---|---|---|
| 6 | Verify `/billing/status` returns the free baseline: | Terminal |

```bash
curl http://localhost:8000/api/billing/status \
  -H "Authorization: Bearer <admin_a_token>"
```

**Expected `/billing/status` response**:
```json
{
  "commercial_plan_slug": "free",
  "billing_status": "none",
  "billing_interval": null,
  "trial_ends_at": null,
  "current_period_end": null,
  "cancel_at_period_end": false,
  "plan_assigned_by": "system",
  "has_stripe_customer": false,
  "has_had_trial": false
}
```

**Pass/Fail criteria**:
- [ ] UI shows "Free" plan correctly
- [ ] No "Gestisci fatturazione" button visible
- [ ] Checkout for "free" returns 400
- [ ] `/billing/status` shape matches expected

---

### Scenario I — Already-Provisioned Account Does Not Regress on Reload

**Goal**: Verify that a Core-plan org persists correctly across page reloads, browser restarts, and backend restarts.

**Setup**:
- `org_alpha` is on Core/trialing (from Scenario A or B)
- `STRIPE_WEBHOOK_SECRET` is set (re-enable it)

**Steps**:

| # | Action | Where |
|---|---|---|
| 1 | Navigate to Settings → verify plan = "AFianco Core", status = "trialing" | Browser UI |
| 2 | Hard-refresh (Ctrl+Shift+R) | Browser |
| 3 | Verify plan still shows "AFianco Core", status = "trialing" | Browser UI |
| 4 | Restart the backend server (stop + start) | Terminal |
| 5 | Refresh the Settings page again | Browser |
| 6 | Verify plan still shows "AFianco Core", status = "trialing" | Browser UI |
| 7 | Open a new incognito window, log in as Admin A | Browser |
| 8 | Navigate to Settings → verify plan = "AFianco Core" | Browser UI |
| 9 | Verify in DB: all billing fields intact | mongosh |

**Expected behavior**: The plan is stored in MongoDB. It survives any application-layer restart. The billing context hook reads from `/billing/status` which reads from DB.

**Pass/Fail criteria**:
- [ ] Plan persists across hard refresh
- [ ] Plan persists across backend restart
- [ ] Plan persists in incognito session (proves it's server-side, not cached)
- [ ] DB fields unchanged across all reloads

---

## C. Observability Guide

### C1. Log Lines That Prove Webhook Path Succeeded

| Log pattern | Meaning |
|---|---|
| `[webhook] checkout.session.completed event_id=evt_... session_id=cs_... org_id=... plan=core` | Webhook handler entered |
| `Provisioned plan 'core' for org '...': cancelled N subs, created 4 subs (by: stripe)` | `provision_commercial_plan()` completed |
| Stripe CLI: `checkout.session.completed [200]` | Webhook endpoint returned 200 |

If all three appear in order: **webhook path succeeded**.

### C2. Log Lines That Prove Verify Fallback Was Used

| Log pattern | Meaning |
|---|---|
| `[verify] Provisioned org '...' with plan='core' status='trialing' via checkout recovery` | `verify_checkout_session` provisioned the plan |
| `verify-checkout session_id=cs_... org_id=... result=provisioned` | Router-level audit log of successful verify |
| Stripe CLI: `checkout.session.completed [400]` (or no CLI running) | Webhook was rejected or never forwarded |

If the `[verify]` lines appear **without** any `[webhook] checkout.session.completed` line: **verify fallback was the provisioning path**.

### C3. Log Lines That Prove Idempotency Worked

| Log pattern | Meaning |
|---|---|
| `[verify] Org '...' already provisioned with plan='core' sub='sub_...' status='trialing' -- no-op` | Idempotency check short-circuited |
| `verify-checkout ... result=already_provisioned` | Router confirmed no-op |

If these appear **without** a `Provisioned plan ...` line: **idempotency prevented re-provisioning**.

### C4. Warning / Error Signals

| Log pattern | Meaning | Severity |
|---|---|---|
| `STRIPE_SECRET_KEY is set but STRIPE_WEBHOOK_SECRET is missing` | Webhooks will be silently rejected | WARNING — config issue |
| `Webhook signature verification failed: STRIPE_WEBHOOK_SECRET not configured` | Incoming webhook rejected | WARNING — expected when secret missing |
| `Webhook handler failed for event '...' (...): ...` | Handler raised exception; webhook returns 500 so Stripe retries | ERROR — investigate handler |
| `Checkout session creation failed: ...` | Unhandled error in checkout flow | ERROR — investigate |
| `verify-checkout failed session_id=... org_id=...: ...` | Unhandled error in verify flow | ERROR — investigate |
| `BILLING INVARIANT VIOLATED: 'free' commercial plan not found` | Free plan missing — all downgrades will break | CRITICAL — fix seed immediately |

### C5. Signals of Stale or Split-Brain State

These indicate the DB and Stripe are out of sync:

| Observation | What it means |
|---|---|
| DB has `stripe_subscription_id` but Stripe shows that sub as `canceled` | Webhook `customer.subscription.deleted` was missed. Org is accessing a plan it shouldn't have. |
| DB has `billing_status: "none"` but Stripe has an `active` subscription | Webhook `checkout.session.completed` was missed. This is the exact scenario v5.7 recovery addresses. |
| DB has `commercial_plan_slug: "core"` but `stripe_subscription_id` is null | Likely an admin manual override (`plan_assigned_by: "admin:..."`). Check `plan_assigned_by` field. |
| Two different orgs share the same `stripe_subscription_id` | Data corruption — should never happen. Investigate immediately. |
| `billing_events` has a failed `checkout.session.completed` event but org is on Free | Webhook fired but handler failed. Check the `error` field on the billing event. |

---

## D. Bug Triage Guide

### D1. UI Still Shows "Free" After Checkout

**Inspection order**:

1. **Check URL on return**: Did `?billing_success=1&session_id=cs_...` appear in the URL? If not, the redirect URL may be misconfigured (check `FRONTEND_URL` env var).

2. **Check Network tab**: Did polling calls to `/billing/status` happen? Did they return `"free"`?

3. **Check if verify fired**: Look for `POST /billing/verify-checkout` in Network tab.
   - If it fired and returned 200 with `"provisioned"` — the plan was set, but the billing context may not have refreshed. Hard-refresh.
   - If it fired and returned 400/403/500 — see D2/D3 below.
   - If it did NOT fire — check if `session_id` was in the return URL. If not, the verify path cannot be used (Scenario E behavior).

4. **Check backend logs**: Search for `[webhook]` and `[verify]` lines.
   - No webhook lines + no verify lines = both paths failed.
   - Check for `Webhook signature verification failed` — means `STRIPE_WEBHOOK_SECRET` is wrong or missing.

5. **Check DB directly**: `db.organizations.findOne({id:"org_alpha"}, {commercial_plan_slug:1, billing_status:1, stripe_subscription_id:1})`.
   - If DB shows `core`/`trialing` but UI shows Free — the frontend billing context is stale. Hard-refresh.
   - If DB shows `free`/`none` — neither webhook nor verify provisioned. Check Stripe dashboard for the subscription status.

6. **Check Stripe Dashboard**: Navigate to the customer → subscriptions. Is there an active/trialing subscription?
   - If yes: provisioning failed. Check backend error logs.
   - If no: the checkout may not have completed. Check the Checkout Session status.

### D2. Verify Endpoint Returns 400

| Error detail | Cause | Fix |
|---|---|---|
| `"Invalid or expired checkout session: ..."` | session_id doesn't exist in Stripe or is very old | Use the correct session_id from the checkout flow |
| `"Checkout session mode is '...', expected 'subscription'"` | Wrong type of checkout session | Should not happen in normal flow — investigate |
| `"Checkout session has no subscription ID"` | Session exists but has no subscription | The checkout may have been for a one-time payment — not supported |
| `"Checkout session metadata missing plan_slug"` | Metadata wasn't set on the session | Bug in `create_checkout_session` — investigate |
| `"Failed to retrieve subscription: ..."` | Stripe subscription ID on session is invalid | Stripe-side issue — check dashboard |
| `"STRIPE_WEBHOOK_SECRET not configured"` | This is actually a webhook error, not verify | Verify doesn't use webhook secret — this indicates wrong endpoint was called |

### D3. Verify Endpoint Returns 403

| Error detail | Cause | Fix |
|---|---|---|
| `"Session does not belong to this organization (session org_id=X, caller org_id=Y)"` | The authenticated user's org doesn't match the session's `metadata.org_id` | This is working as designed. The user is calling verify on someone else's session. Ensure the correct user is authenticated. |

### D4. Webhook Endpoint Returns 400

| Error detail | Cause | Fix |
|---|---|---|
| `"Missing stripe-signature header"` | Request came without the Stripe signature header | Not a real Stripe webhook — could be a curl test. Real Stripe always sends this header. |
| `"Invalid webhook signature"` | `STRIPE_WEBHOOK_SECRET` doesn't match the signing secret Stripe used | Get the correct `whsec_...` from `stripe listen` output (for local) or from the Stripe Dashboard webhook endpoint settings (for staging/prod). |

Check for: `Webhook signature verification failed: STRIPE_WEBHOOK_SECRET not configured` — this means the env var is completely absent, not just wrong.

### D5. Plan is Correct in DB But Not in UI

1. **Hard-refresh** the browser (Ctrl+Shift+R). The billing context hook calls `/billing/status` on mount.
2. **Check `/billing/status` response** directly (curl or Network tab). If it returns the correct plan, the issue is in the React rendering layer.
3. **Check `useBilling` hook**: The hook reads from a context. If the context was initialized before the plan changed, it may be stale. The `billing.refresh()` call should update it.
4. **Check for JS errors** in the browser console. A rendering error could prevent the updated state from displaying.
5. **Check if the billing context uses caching**: If there's a stale localStorage/sessionStorage cache, clear it.

---

## E. Go/No-Go Checklist

Complete all items before moving from manual staging to controlled pilot/live.

### Functional Completeness

| # | Check | Status |
|---|---|---|
| 1 | Scenario A (happy path with webhook) passed all criteria | [ ] |
| 2 | Scenario B (verify fallback without webhook) passed all criteria | [ ] |
| 3 | Scenario C (idempotent re-verify) returned `already_provisioned` | [ ] |
| 4 | Scenario D (cancel checkout) caused no state change | [ ] |
| 5 | Scenario E (missing session_id) showed honest pending toast, no crash | [ ] |
| 6 | Scenario F (wrong-org verify) returned 403 | [ ] |
| 7 | Scenario G (invalid session_id) returned 400 | [ ] |
| 8 | Scenario H (free baseline, cannot buy free) returned 400 on checkout | [ ] |
| 9 | Scenario I (persistence across reload/restart) plan survived | [ ] |

### Automated Tests

| # | Check | Status |
|---|---|---|
| 10 | `pytest tests/test_billing.py -v` — 206 passed, 0 failed | [ ] |
| 11 | `pytest tests/ --ignore=tests/test_new_features.py -v` — 378 passed, 0 failed | [ ] |
| 12 | 8 functional tests (v5.7.1) pass: happy path, idempotent, wrong-org, incomplete, canceled sub, webhook regression, stripe_sub skip/retrieve | [ ] |

### Configuration

| # | Check | Status |
|---|---|---|
| 13 | `STRIPE_WEBHOOK_SECRET` is set in staging/production environment | [ ] |
| 14 | Stripe webhook endpoint URL is registered in Stripe Dashboard for staging/prod | [ ] |
| 15 | Webhook endpoint is listening for: `checkout.session.completed`, `customer.subscription.updated`, `customer.subscription.deleted`, `invoice.paid`, `invoice.payment_failed` | [ ] |
| 16 | Startup log does NOT show the "STRIPE_WEBHOOK_SECRET is missing" warning | [ ] |
| 17 | Commercial plans (`core`, `pro`) have valid `stripe_price_id_monthly` values in DB | [ ] |
| 18 | `FRONTEND_URL` is set to the correct staging/production origin | [ ] |

### Observability

| # | Check | Status |
|---|---|---|
| 19 | Backend log level is INFO or lower (so `[webhook]`, `[verify]`, and `Provisioned` lines are visible) | [ ] |
| 20 | Stripe Dashboard Events page is accessible and shows recent test events | [ ] |
| 21 | Team knows which log patterns indicate webhook success vs. verify fallback (Section C) | [ ] |

### Rollback Plan

| # | Check | Status |
|---|---|---|
| 22 | Reverting the v5.7 frontend code (removing verify fallback) degrades gracefully to v5.6 polling-only behavior — no crash | [ ] |
| 23 | The verify endpoint can be disabled independently (remove route or feature flag) without breaking checkout or webhooks | [ ] |
| 24 | DB schema changes are backward-compatible (no new required fields) | [ ] |

### Decision

| Criteria | Threshold | Result |
|---|---|---|
| All 9 scenarios pass | 9/9 required | [ ] |
| All automated tests pass | 206/206 billing + 378/378 full suite | [ ] |
| All configuration items confirmed | 6/6 required | [ ] |
| At least one team member reviewed the triage guide | 1 required | [ ] |

**GO** = All thresholds met.
**NO-GO** = Any scenario failed, any automated test failed, or any required configuration item missing. Fix the issue and re-run the failing scenario before re-evaluating.
