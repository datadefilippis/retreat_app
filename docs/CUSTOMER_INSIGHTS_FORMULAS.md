# Customer Insights — Formula Reference

**Status**: Phase 0 deliverable.
**Source of truth**: [`backend/modules/customer_insights/formulas.py`](../backend/modules/customer_insights/formulas.py).
**Tests**: [`backend/tests/test_customer_insights_formulas.py`](../backend/tests/test_customer_insights_formulas.py) — 91 unit tests, < 1 s.

This document is the public face of every metric rendered on the new
"Clienti" insights page. Each metric below is shown to the merchant
through an info-box with three fields:

- **def** — what is this number, in plain language.
- **calc** — how it's computed (the actual formula).
- **read** — how to interpret it ("higher = better" vs. inverse).

Those three strings live in `frontend/src/locales/{it,en,de,fr}/customerInsights.json`
and the parity guard (`tests/test_i18n_locales_parity.py`) verifies
that every locale provides them.

---

## Table of contents

1. [Per-customer metrics](#1-per-customer-metrics)
2. [Segment & lifecycle classification](#2-segment--lifecycle-classification)
3. [Churn risk](#3-churn-risk)
4. [Trend & status](#4-trend--status)
5. [Org-level concentration](#5-org-level-concentration)
6. [Order metrics (v13.0)](#6-order-metrics)
7. [Period delta (Phase 1)](#7-period-delta)
8. [Before / After — the five Phase 0 corrections](#8-before--after-the-five-phase-0-corrections)
9. [Configuration knobs](#9-configuration-knobs)

---

## 1. Per-customer metrics

| # | Field | Formula | Edge cases |
|---|---|---|---|
| 1 | `total_revenue` | Sum of `sales_records.amount` per `customer_id` (mongo aggregate) | 0 if no sales |
| 2 | `transaction_count` | Count of sales rows per customer | 0 if no sales |
| 3 | `avg_transaction_value` | `total_revenue / transaction_count` | 0 when count = 0 |
| 4 | `first_purchase_date` | Min `date` from sales | None if no sales |
| 5 | `last_purchase_date` | Max `date` from sales | None if no sales |
| 6 | `days_since_last_purchase` | `(today - last_purchase_date).days` | 0 if no last date |
| 7 | `purchase_frequency_monthly` ⚠ | `count / months_active` only when `count ≥ 3`; else **None** | None when history too short |
| 8 | `revenue_share_pct` | `customer_revenue / org_total_revenue × 100` | 0 if org has no revenue |
| 9 | `revenue_rank` | 1-based ordinal (sorted desc by revenue) | 1 for sole customer |
| 10 | `revenue_rank_pct` | `(rank - 1) / total_customers` | 0.0 for sole customer |
| 11 | `projected_annual_revenue` ⚠ | `avg_transaction_value × frequency × 12` (was named `lifetime_value`); **None if frequency is None** | Cascades None |
| 12 | `payment_reliability_pct` | `paid_on_time / total_with_due_date × 100` | **None** when no due-date data (≠ 0) |

⚠ = revised in Phase 0. See [Before / After](#8-before--after-the-five-phase-0-corrections).

---

## 2. Segment & lifecycle classification

Each customer falls into exactly one of five segments. Priority
(first-match-wins): **new > top > active > occasional > inactive**.

| Segment | Rule (default thresholds) |
|---|---|
| `new` | `first_purchase_date` within last `new_days` days (default 90) |
| `top` | `revenue_rank_pct ≤ top_pct` (default 0.10 = top 10 %) |
| `active` | `days_since_last ≤ active_days` (default 60) |
| `occasional` | `days_since_last ≤ occasional_days` (default 180) |
| `inactive` | `days_since_last > occasional_days` |

**Configurable per-org** (`organization.settings.customer_lifecycle`):

```json
{
  "new_days": 14,
  "active_days": 7,
  "occasional_days": 30,
  "top_pct": 0.10
}
```

The defaults match the legacy `modules.customers_light` behaviour
exactly so existing orgs see no change. Industries with non-monthly
cadence (yoga = weekly, photographer = annual) override.

---

## 3. Churn risk

`churn_risk_score` is an integer in `[0, 100]` decomposed into four
transparent components. The info-box renders the breakdown so the
merchant sees **why** a customer is at risk, not just a black-box number.

```
score = min(100, recency + frequency + single_penalty + cancel_penalty)
```

| Component | Range | Logic |
|---|---|---|
| `recency` | 0–50 | 0 if `days_since_last ≤ 30`; linear to 50 over 30–180 d; capped at 50 |
| `frequency` | 0–30 | 0 if `freq ≥ 2/month`; linear; 30 if `< 0.5/month` or `freq is None` |
| `single_penalty` | 0–20 | +20 if `transaction_count == 1` |
| `cancel_penalty` | 0–20 | +20 if `cancellation_rate > 30 %`; +10 if `> 3` cancelled orders |

**Status overlay** (`customer_status`):

| Status | Trigger |
|---|---|
| `lost` | `segment == "inactive"` |
| `at_risk` | `churn_risk_score ≥ 60` |
| `watch` | `segment == "occasional"` OR `trend == "declining"` |
| `healthy` | everything else |

---

## 4. Trend & status

`trend_direction` compares revenue in the last 90 days to the prior
90 days.

```
new       — segment == "new" OR no previous revenue with recent > 0
growing   — recent ≥ previous × growth_factor   (default 1.20)
declining — recent ≤ previous × decline_factor  (default 0.80)
stable    — within ±20 % band
```

**Configurable per-org** (`organization.settings.trend_thresholds`):

```json
{
  "growth_factor": 1.10,
  "decline_factor": 0.90
}
```

Sensitive industries (e.g. coaches with 1-2 sessions/month) need
tighter bands than retail.

---

## 5. Org-level concentration

| KPI | Formula |
|---|---|
| `total_customers` | Distinct customers with linked sales |
| `total_revenue` | Sum of all customer revenue |
| `avg_customer_value` | `total_revenue / total_customers` (0 if no customers) |
| `top_5_share_pct` | `Σ top-5-revenue / total_revenue × 100` |
| `top_10_share_pct` | `Σ top-10-revenue / total_revenue × 100` |
| `inactive_rate_pct` | `inactive_count / total_customers × 100` |
| `growing_count` | Customers with `trend_direction == "growing"` |
| `declining_count` | Customers with `trend_direction == "declining"` |
| `high_churn_risk_count` | Customers with `churn_risk_score ≥ 60` |

---

## 6. Order metrics

Computed from `orders_collection` (separate from sales_records). Each
materialized per customer:

| Field | Formula |
|---|---|
| `order_count` | Distinct orders per customer |
| `order_total_value` | Sum of `orders.total` |
| `avg_order_value` | `order_total_value / order_count` |
| `last_order_date` | Max `created_at` |
| `orders_confirmed` | Count where `status in ("confirmed", "completed")` |
| `orders_cancelled` | Count where `status == "cancelled"` |
| `cancellation_rate_pct` | `orders_cancelled / order_count × 100` |
| `booking_count` | Σ `items.quantity` where `item_type == "booking"` (non-cancelled) |
| `event_attendance` | Σ `items.quantity` where `item_type == "event_ticket"` |
| `fulfillment_success_rate` | Fulfilled / total-with-fulfillment × 100; **None** if no fulfillment data |

These feed into the churn-risk `cancel_penalty` and per-vertical UI
modules (event/booking attendance only relevant for some merchants).

---

## 7. Period delta

For Phase 1's period selector ("vs 30 days prior"):

```
percentage_delta(current, previous) =
    None                                 if previous == 0
    (current - previous) / previous × 100  otherwise
```

Returning **None** rather than `+∞` prevents the UI from showing
"+9999 %" on an org's first month of operation.

---

## 8. Before / After — the five Phase 0 corrections

### Correction 1 — `lifetime_value` → `projected_annual_revenue`

**Before**: The metric was called `lifetime_value` and computed as
`avg_tx × monthly_freq × 12`. This is **not** a true LTV (no
retention curve, no discount rate, no cohort logic). For a customer
with 1 purchase yesterday, the formula yielded an inflated value
because `monthly_freq` was floored at 1.0 (see Correction 2).

**After**: Renamed to `projected_annual_revenue` to communicate
exactly what the number means. Returns **None** when frequency is
None (cascading from Correction 2). The UI uses both values:

- `revenue_actual` (the real `total_revenue`) — the source of truth.
- `projected_annual_revenue` — a forward-looking estimate, displayed
  with the caveat "stima a 12 mesi" alongside the actual.

### Correction 2 — `purchase_frequency_monthly` for short history

**Before**: A customer with 1 purchase 5 days ago returned
`1.0 / month` because `months_active` was floored at 1.0 yielding
`1 / 1 = 1`. Misleading: we had no signal at all, but the UI
showed a confident-looking number.

**After**: Returns **None** when `transaction_count <
MIN_PURCHASES_FOR_FREQUENCY = 3`. The UI renders "Storia troppo
breve" so the merchant knows we're being honest, not silent.

Downstream impact:
- `projected_annual_revenue` cascades None.
- `churn_risk_breakdown.frequency` treats None as worst-case (30) —
  better to flag for follow-up than miss a churning new customer.

### Correction 3 — `churn_risk_score` opacity

**Before**: Single integer `churn_risk_score`. The merchant saw "75"
and wondered "is that bad? why?".

**After**: `compute_churn_risk_breakdown` returns a `ChurnRiskBreakdown`
dataclass with the per-component split. The info-box on the customer
table renders:

> Recency 32 + Frequency 18 + Single-purchase 20 + Cancellations 0
> = 70 / 100

The legacy `churn_risk_score` wrapper still exists for backward
compatibility with the materialized `customer_metrics` collection.

### Correction 4 — Hardcoded lifecycle thresholds

**Before**: `_classify_segment` hardcoded 60 days for "active" and
180 days for "occasional". A yoga studio with weekly clients had its
power users mis-classified as "active" (when they were actually
"occasional" by the studio's own cadence). A wedding photographer
with annual customers had everyone mis-classified as "inactive".

**After**: `LifecycleThresholds` dataclass is passed in. Defaults
preserve legacy behaviour bit-for-bit. Per-org config overrides via
`organization.settings.customer_lifecycle` — Phase 1 will surface
this in the Settings UI as a "Customer cadence" preset selector.

### Correction 5 — Hardcoded trend threshold

**Before**: `_classify_trend` hardcoded ±20 % for growing/declining.
Some industries see seasonal swings of ±30 % naturally; others see
±5 % shifts that matter.

**After**: `TrendThresholds` dataclass with `growth_factor` and
`decline_factor` defaults of 1.20 / 0.80. Per-org configurable via
`organization.settings.trend_thresholds`.

---

## 9. Configuration knobs

All optional. Defaults are the legacy hardcoded values, so
existing orgs see no behavioural change until they explicitly
opt in.

```jsonc
// organization.settings (new fields, all optional)
{
  "customer_lifecycle": {
    "new_days": 90,
    "active_days": 60,
    "occasional_days": 180,
    "top_pct": 0.10
  },
  "trend_thresholds": {
    "growth_factor": 1.20,
    "decline_factor": 0.80
  }
}
```

Phase 1 will add API endpoints to read/write these blocks and render
them in Settings UI. Phase 2 will surface them in the info-box copy
("Active = last purchase within 60 days — change in Settings").

---

## Versioning

| Phase | Date | Change |
|---|---|---|
| 0 | 2026-05-10 | Initial doc + 5 corrections + 91 unit tests |
| 1 | TBD | Period filter / cohort additions |
| 2 | TBD | UI binding + info-box copy in 4 locales |
