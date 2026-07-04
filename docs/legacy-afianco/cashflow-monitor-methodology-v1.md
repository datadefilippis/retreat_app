# AFianco — Cashflow Monitor: Product Methodology & Specification

**Document Version:** v1.0
**Status:** Draft for Review
**Date:** March 2026
**Author:** AFianco Product & Engineering
**Classification:** Internal / Investor-Ready

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Intended Audience](#2-intended-audience)
3. [Use Cases](#3-use-cases)
4. [Purpose of the Cashflow Report](#4-purpose-of-the-cashflow-report)
5. [Scope of the Module](#5-scope-of-the-module)
6. [Data Inputs and Source Variables](#6-data-inputs-and-source-variables)
7. [Derived KPI Definitions](#7-derived-kpi-definitions)
8. [KPI Cards Overview](#8-kpi-cards-overview)
9. [Financial Health Score Methodology](#9-financial-health-score-methodology)
10. [Scored Dimensions — Detail](#10-scored-dimensions--detail)
11. [Diagnostic Metrics](#11-diagnostic-metrics)
12. [Rules for Missing Data / Not-Computable Logic](#12-rules-for-missing-data--not-computable-logic)
13. [Proxy Metrics and Interpretation Caveats](#13-proxy-metrics-and-interpretation-caveats)
14. [AI Layer on Top of the Financial Engine](#14-ai-layer-on-top-of-the-financial-engine)
15. [Example Interpretation Logic](#15-example-interpretation-logic)
16. [Limitations](#16-limitations)
17. [Glossary](#17-glossary)
18. [Governance / Revision Notes](#18-governance--revision-notes)

---

## 1. Executive Summary

AFianco's **Cashflow Monitor** is a real-time financial reporting module designed for Italian small and medium enterprises (SMEs). It transforms raw transactional data — sales, operating expenses, supplier purchases, and fixed costs — into a structured set of KPIs, a composite Financial Health Score, diagnostic indicators, and AI-generated explanations.

The module serves three core purposes:

1. **Operational visibility.** Business owners see their daily inflows and outflows, net result, cost structure, and burn rate at a glance.
2. **Financial health assessment.** A composite score (0–100) across five distinct financial dimensions summarizes the business's health with clear thresholds and labels.
3. **Actionable guidance.** AI-powered explanations translate numeric scores into plain-language assessments, identify priorities, and surface data quality warnings.

**Key design principles:**

- **No false-good scores.** When data is missing, the corresponding dimension is excluded from the score rather than defaulted to a misleadingly favorable value.
- **Clear separation of scored vs. diagnostic metrics.** Only five dimensions drive the score; all other metrics are displayed for context but do not influence the composite number.
- **Proxy metrics are always labeled.** Any metric that approximates a concept (e.g., operational coverage as a proxy for real liquidity) is explicitly marked and caveated.
- **AI is bounded by data.** The AI layer reads structured outputs and does not invent financial facts. It qualifies proxy metrics and recommends verification by a professional.

---

## 2. Intended Audience

| Audience | What they should get from this document |
|---|---|
| **Product managers** | Complete specification for feature governance, roadmap planning, and QA validation |
| **Engineers** | Exact formulas, thresholds, and edge cases for implementation parity |
| **Investors / Board** | Methodology credibility, intellectual property clarity, and product maturity signal |
| **Compliance / Legal** | Disclaimer boundaries, proxy metric labeling, and AI limitation disclosures |
| **Customer Success** | Understanding of what each metric means so they can support end users |

---

## 3. Use Cases

| # | Use Case | Actor | Module Feature |
|---|---|---|---|
| UC-1 | Monitor daily revenue vs. expenses | Business owner | KPI cards, daily series chart |
| UC-2 | Understand profitability after all costs | Business owner | Net Result, Net Margin %, Health Score |
| UC-3 | Check if revenue covers the break-even threshold | Business owner | Break-Even card, Structural Strength dimension |
| UC-4 | Identify cash cycle inefficiencies | Finance manager | DSO, DPO, Cash Conversion Gap, Cash Cycle dimension |
| UC-5 | Get a quick health summary for a board meeting | CEO / Owner | Health Score gauge, AI explanation |
| UC-6 | Detect anomalies and negative trends early | Business owner | Alert rules, Revenue Dynamics dimension |
| UC-7 | Understand how long current margins can sustain operations | Business owner | Operational Coverage (proxy), Burn Rate |
| UC-8 | Assess data completeness and reliability of the score | Any user | Confidence indicator, data caveats, NOT_COMPUTABLE labels |

---

## 4. Purpose of the Cashflow Report

The Cashflow Report provides a structured, automated financial overview that translates raw transaction data into business-relevant metrics. It is not a replacement for professional accounting or CFO-level analysis. It is a **directional tool** that helps business owners:

- Understand where money is going
- Identify early warning signs
- Track trends over time
- Communicate financial posture to stakeholders

The module distinguishes between **facts** (recorded transactions), **derived metrics** (calculated from facts), and **proxies** (approximations where direct data is unavailable).

---

## 5. Scope of the Module

### Included

- Revenue and expense tracking (daily granularity)
- Four-bucket cost model: operating expenses, supplier purchases, fixed costs, and their combination as total outflows
- Profitability KPIs: net result, margins, break-even
- Cash cycle KPIs: DSO, DPO, cash conversion gap
- Operational KPIs: burn rate, operational coverage
- Composite health score (0–100) with five dimensions
- Period-over-period and year-over-year comparisons
- AI-generated explanations and insights
- Alert rules for anomaly detection
- Payment aging and 60-day forecast (when payment data is available)

### Not Included

- Bank account balance integration (no direct bank feed)
- Tax calculations or VAT filing
- Inventory management or COGS tracking
- Multi-currency consolidation
- Intercompany reconciliation
- Payroll processing

---

## 6. Data Inputs and Source Variables

All financial computations begin with four categories of raw input data uploaded by the user.

### 6.1 Raw Financial Inputs

| Input Category | Key Fields | Source |
|---|---|---|
| **Sales (Revenue)** | `date`, `amount`, `category`, `due_date`, `payment_status` | CSV/XLSX upload or manual entry |
| **Operating Expenses** | `date`, `amount`, `category` | CSV/XLSX upload or manual entry |
| **Supplier Purchases** | `date`, `quantity`, `unit_price`, `total_price`, `iva`, `total_with_iva`, `supplier_name`, `due_date`, `payment_status` | CSV/XLSX upload or manual entry |
| **Fixed Costs** | `name`, `category`, `amount`, `frequency`, `start_date`, `end_date` | Manual entry |

### 6.2 Derived Aggregates

From the raw inputs, the system computes period-level aggregates:

| Variable | Definition |
|---|---|
| `total_sales` | Sum of all sales amounts in the selected period |
| `total_expenses` | Sum of all operating expense amounts in the selected period |
| `supplier_purchases` | Sum of all purchase totals (using `effective_total`: coalesces `total_with_iva`, `amount`, `total_price`) |
| `fixed_costs_total` | Sum of all active fixed costs, prorated to the selected period based on frequency |
| `variable_outflows` | `total_expenses + supplier_purchases` |
| `total_outflows` | `variable_outflows + fixed_costs_total` |
| `net_before_fixed` | `total_sales − variable_outflows` |
| `net_after_fixed` | `total_sales − total_outflows` |
| `open_receivables` | Sum of sales amounts where `payment_status ≠ "paid"` and `due_date` is set |
| `open_payables` | Sum of purchase amounts where `payment_status ≠ "paid"` and `due_date` is set |

### 6.3 Period Definition

| Variable | Formula |
|---|---|
| `period_days` | `(end_date − start_date).days + 1` (calendar days, inclusive) |
| Previous period | Same duration, immediately preceding the selected period |
| Year-over-year | Same calendar dates, previous year |

---

## 7. Derived KPI Definitions

Each KPI below is computed from the aggregates defined in Section 6. All computations use a **canonical formula layer** (`kpi_formulas.py`) that ensures identical results across the overview, insights, and alert systems.

### 7.1 Profitability KPIs

#### Net Margin %

| Attribute | Value |
|---|---|
| **Purpose** | Measures what percentage of revenue remains as profit after all costs |
| **Formula** | `(net_after_fixed ÷ total_sales) × 100` |
| **Unit** | Percentage (1 decimal) |
| **Returns None when** | `total_sales ≤ 0` |
| **Interpretation** | > 15% excellent · 5–15% adequate · < 0% loss |
| **Caveat** | If fixed costs are not uploaded, the margin is artificially inflated |

#### Cost-to-Revenue Ratio

| Attribute | Value |
|---|---|
| **Purpose** | Shows how much of every euro of revenue is consumed by costs |
| **Formula** | `(total_outflows ÷ total_sales) × 100` |
| **Unit** | Percentage (1 decimal) |
| **Returns None when** | `total_sales ≤ 0` |
| **Interpretation** | < 80% healthy · > 100% spending more than earning |
| **Caveat** | Diagnostic only — not scored |

#### Variable Cost Ratio (VCR)

| Attribute | Value |
|---|---|
| **Purpose** | Ratio of variable costs to revenue; input for break-even calculation |
| **Formula** | `variable_outflows ÷ total_sales` |
| **Unit** | Ratio, 4 decimals (0.0–1.0+) |
| **Returns None when** | `total_sales ≤ 0` |
| **Interpretation** | Used internally — not displayed directly |

### 7.2 Break-Even KPIs

#### Break-Even Point

| Attribute | Value |
|---|---|
| **Purpose** | The minimum revenue needed to cover all costs |
| **Formula** | `fixed_costs_total ÷ (1 − variable_cost_ratio)` |
| **Unit** | EUR (2 decimals) |
| **Returns None when** | VCR is None (no sales), OR `fixed_costs ≤ 0`, OR `VCR ≥ 1.0` (variable costs exceed revenue) |
| **Interpretation** | Revenue above this = profit; below = loss |
| **Caveat** | When VCR ≥ 1.0, break-even is structurally unreachable — costs must be reduced first |

#### Break-Even Headroom %

| Attribute | Value |
|---|---|
| **Purpose** | How far above (or below) break-even the current revenue sits |
| **Formula** | `((total_sales − break_even) ÷ break_even) × 100` |
| **Unit** | Percentage (1 decimal) |
| **Returns None when** | `break_even` is None, OR `total_sales ≤ 0`, OR `break_even ≤ 0` |
| **Interpretation** | Positive = safe margin above break-even; Negative = deficit |

#### Fixed Cost Ratio

| Attribute | Value |
|---|---|
| **Purpose** | Weight of fixed costs relative to revenue |
| **Formula** | `(fixed_costs_total ÷ total_sales) × 100` |
| **Unit** | Percentage (1 decimal) |
| **Returns None when** | `total_sales ≤ 0` OR `fixed_costs ≤ 0` |
| **Interpretation** | < 15% lean · 15–30% moderate · > 30% heavy structure |

### 7.3 Cash Flow Timing KPIs

#### DSO (Days Sales Outstanding)

| Attribute | Value |
|---|---|
| **Purpose** | Average number of days to collect payment from customers |
| **Formula** | `(open_receivables ÷ total_sales) × period_days` |
| **Unit** | Days (1 decimal) |
| **Returns None when** | `total_sales ≤ 0` OR `period_days ≤ 0` |
| **Returns 0.0 when** | `open_receivables = 0` (all collected — legitimate zero) |
| **Caveat** | Estimated metric. Accuracy improves as users add due dates and payment status to sales records |

#### DPO (Days Payable Outstanding)

| Attribute | Value |
|---|---|
| **Purpose** | Average number of days to pay suppliers |
| **Formula** | `(open_payables ÷ supplier_purchases) × period_days` |
| **Unit** | Days (1 decimal) |
| **Returns None when** | `supplier_purchases ≤ 0` OR `period_days ≤ 0` |
| **Returns 0.0 when** | `open_payables = 0` (all paid — legitimate zero) |
| **Caveat** | Estimated metric. Accuracy improves as users add due dates and payment status to purchase records |

#### Cash Conversion Gap

| Attribute | Value |
|---|---|
| **Purpose** | Net timing difference between collecting receivables and paying suppliers |
| **Formula** | `DSO − DPO` |
| **Unit** | Days (1 decimal) |
| **Returns None when** | Both DSO and DPO are None |
| **Fallback** | When only one is computable, the missing value is treated as 0 |
| **Interpretation** | Negative = cash comes in before it goes out (favorable); Positive = need to finance the gap |

### 7.4 Operational KPIs

#### Burn Rate (Daily)

| Attribute | Value |
|---|---|
| **Purpose** | Average daily total outflows across all cost categories |
| **Formula** | `total_outflows ÷ period_days` |
| **Unit** | EUR/day (2 decimals) |
| **Returns None when** | `period_days ≤ 0` |
| **Returns 0.0 when** | `total_outflows = 0` |
| **Interpretation** | Higher burn rate = faster cash consumption |

#### Operational Coverage (Proxy)

| Attribute | Value |
|---|---|
| **Purpose** | Estimates how many days the current net margin would cover daily outflows |
| **Formula** | `net_after_fixed ÷ (total_outflows ÷ period_days)` |
| **Unit** | Days (1 decimal) |
| **Returns None when** | `period_days ≤ 0` OR `total_outflows ≤ 0` |
| **Returns 0.0 when** | `net_after_fixed ≤ 0` (in loss — zero coverage) |
| **⚠️ PROXY METRIC** | This is NOT real liquidity. No bank balance data is used. It is a directional signal based on the relationship between margin and burn rate. Always labeled with `~ estimated` in the UI |

### 7.5 Trend KPIs

#### Sales Trend %

| Attribute | Value |
|---|---|
| **Formula** | `((current_sales − prev_sales) ÷ prev_sales) × 100` |
| **Returns None when** | Previous period has zero sales |
| **Interpretation** | Positive = growth; Negative = contraction |

#### Margin Trend (Percentage Points)

| Attribute | Value |
|---|---|
| **Formula** | `current_net_margin_pct − previous_net_margin_pct` |
| **Returns None when** | Either period has zero sales |
| **Interpretation** | Positive = improving profitability; Negative = margin compression |

---

## 8. KPI Cards Overview

The Cashflow Monitor presents KPIs in a structured card layout with two rows in the Detail tab and five compact cards in the Summary tab.

### Detail Tab — Row 1 (Core Operational)

| Position | Card | Value Source | Trend | Color Logic |
|---|---|---|---|---|
| 1 | Total Revenue | `total_sales` | PoP % | Always green |
| 2 | Operating Expenses | `total_expenses` | PoP % (inverse) | Always red |
| 3 | Supplier Purchases | `supplier_purchases` | — | Red |
| 4 | Fixed Costs | `fixed_costs_total` | — | Default |
| 5 | Net Result | `net_after_fixed` | — | Green if ≥ 0, red if < 0 |
| 6 | Burn Rate | `burn_rate_total` | — | Default |

### Detail Tab — Row 2 (Structural + Diagnostic)

| Position | Card | Value Source | Color Logic | Styling |
|---|---|---|---|---|
| 1 | Break-Even | `break_even` or "N/A" | Green if sales > BE; Red if sales < BE | Standard |
| 2 | Operational Coverage ~ est. | `giorni_autonomia` + "gg" | Red < 30d, Green ≥ 60d | Standard + proxy badge |
| 3 | Fixed Cost Ratio | `fixed_costs_pct` + "%" | Red > 30%, Green ≤ 30% | Standard |
| 4 | Operating Margin % | `operating_margin_pct` + "%" | — | **Diagnostic** (muted) |
| 5 | Outflow Ratio | `total_outflow_ratio` + "%" | — | **Diagnostic** (muted) |

> Cards 4 and 5 use **diagnostic styling**: reduced opacity (75%), muted border, no success/danger coloring. This visually communicates that they are supplementary context, not primary decision metrics.

### Summary Tab (5 Compact Cards)

| Position | Card | Comparison | Note |
|---|---|---|---|
| 1 | Total Revenue | YoY preferred, PoP fallback | — |
| 2 | Net Result | YoY | — |
| 3 | Outflow Ratio | YoY (inverse) | Swapped before Op. Margin — more actionable for SMEs |
| 4 | Operating Margin % | YoY | — |
| 5 | Operational Coverage ~ est. | None | Proxy — not reliable for trend comparison |

---

## 9. Financial Health Score Methodology

### 9.1 Overview

The Financial Health Score is a composite indicator from **0 to 100** that summarizes business health across five financially distinct dimensions. It is designed as a **directional signal**, not a precise diagnosis.

### 9.2 Design Principles

1. **No redundancy.** Each dimension measures a distinct financial concept. Previous versions had 8 dimensions with ~90% correlation between three of them; the v3.0 redesign eliminated this.
2. **Not-computable > false-good.** When data is insufficient to calculate a dimension, it is excluded and its weight is redistributed — the score never defaults to a deceptively favorable value.
3. **Scored vs. diagnostic.** Only five dimensions drive the score. All other metrics (cost-to-revenue ratio, operating margin, burn rate, DSO/DPO individually, operational coverage) are displayed for context but never influence the composite number.
4. **Confidence transparency.** A confidence value (0.0–1.0) indicates what fraction of the total weight was actually computable. Users should interpret a score with confidence < 0.5 with caution.

### 9.3 Dimension Weights

| # | Dimension | Key | Weight | What It Measures |
|---|---|---|---|---|
| 1 | **Net Margin** | `net_margin` | 25 pt | Net profitability after all costs |
| 2 | **Revenue Dynamics** | `revenue_dynamics` | 20 pt | Revenue and margin trajectory |
| 3 | **Structural Strength** | `structural_strength` | 20 pt | Break-even distance and fixed cost leverage |
| 4 | **Cash Cycle** | `cash_cycle` | 25 pt | Cash conversion timing (DSO − DPO) |
| 5 | **Operational Risk** | `operational_risk` | 10 pt | Alert signals and data completeness |
| | | | **100 pt** | **Total** |

### 9.4 Score Bands

| Score Range | Label | Color | Meaning |
|---|---|---|---|
| 80–100 | Excellent | Green (#22C55E) | Strong financial position across most dimensions |
| 60–79 | Good | Yellow (#EAB308) | Generally healthy with areas to monitor |
| 40–59 | Attention | Orange (#F97316) | One or more dimensions require action |
| 0–39 | Critical | Red (#EF4444) | Significant financial stress detected |

### 9.5 Weight Rescaling

When one or more dimensions are disabled or not computable, the remaining dimensions' weights are **proportionally rescaled** to maintain a 0–100 scale.

**Algorithm:**

```
computable_weight_sum = sum of weights for all active + computable dimensions
For each computable dimension:
    rescaled_max = (original_weight ÷ computable_weight_sum) × 100
    rescaled_points = (original_points ÷ original_max) × rescaled_max
Final score = sum of all rescaled_points (capped 0–100)
```

**Example:** If Cash Cycle (25 pt) is not computable:
- Remaining computable weight = 75
- Net Margin rescaled max = (25 ÷ 75) × 100 = 33.3 pt
- Confidence = 75 ÷ 100 = 0.75

### 9.6 Confidence

```
confidence = computable_weight ÷ 100
```

| Confidence | Meaning |
|---|---|
| 1.0 | All five dimensions computed — full reliability |
| 0.55–0.99 | One or two dimensions missing — score is directional but partial |
| < 0.55 | Significant data gaps — score should be treated with caution |

---

## 10. Scored Dimensions — Detail

### 10.1 Net Margin (25 pt)

| Attribute | Value |
|---|---|
| **Measures** | Net profitability as a percentage of revenue |
| **Input** | `total_sales`, `net_after_fixed` |
| **Formula** | `margin_pct = (net_after_fixed ÷ total_sales) × 100` |
| **Not computable when** | `total_sales ≤ 0` |

**Scoring thresholds:**

| Net Margin % | Points (of 25) | Assessment |
|---|---|---|
| > 15% | 25 | Excellent profitability |
| > 10% | 21 | Strong |
| > 5% | 16 | Adequate |
| > 0% | 10 | Marginal |
| = 0% | 5 | Break-even |
| < 0% | 0 | Loss |

### 10.2 Revenue Dynamics (20 pt)

| Attribute | Value |
|---|---|
| **Measures** | Revenue and margin trajectory compared to the previous period |
| **Input** | `sales_trend_pct`, `margin_trend_pp` |
| **Structure** | Composite: Sub-A (Sales Trend, 10 pt) + Sub-B (Margin Trend, 10 pt) |
| **Not computable when** | Both `sales_trend_pct` and `margin_trend_pp` are None |

**Sub-A: Sales Trend (10 pt)**

| Sales Trend | Points |
|---|---|
| > +10% | 10 |
| > 0% | 7 |
| > −10% | 4 |
| > −20% | 2 |
| ≤ −20% | 0 |

**Sub-B: Margin Trend (10 pt)**

| Margin Trend (pp) | Points |
|---|---|
| > +2 pp | 10 |
| > −2 pp | 7 |
| > −5 pp | 4 |
| ≤ −5 pp | 0 |

**Rescaling:** If only one sub-score is computable, it is rescaled to the full 20 pt range (e.g., 7/10 → 14/20).

### 10.3 Structural Strength (20 pt)

| Attribute | Value |
|---|---|
| **Measures** | Distance from break-even and weight of fixed costs |
| **Input** | `total_sales`, `break_even`, `fixed_costs_total` |
| **Structure** | Composite: Sub-A (Break-Even Headroom, 10 pt) + Sub-B (Fixed Cost Ratio, 10 pt) |
| **Not computable when** | Both sub-scores cannot be computed |

**Sub-A: Break-Even Headroom (10 pt)**

| Headroom % | Points |
|---|---|
| > 30% | 10 |
| > 15% | 7 |
| > 0% | 4 |
| ≤ 0% | 0 |

Special case: If `break_even = None` but `fixed_costs > 0`, the sub-score is 0 (structural deficit — variable costs exceed revenue) but remains marked as computable.

**Sub-B: Fixed Cost Ratio (10 pt)**

| Fixed Cost Ratio | Points |
|---|---|
| < 15% | 10 |
| < 25% | 7 |
| < 35% | 4 |
| < 50% | 2 |
| ≥ 50% | 0 |

### 10.4 Cash Cycle (25 pt)

| Attribute | Value |
|---|---|
| **Measures** | Net timing gap between collecting receivables and paying suppliers |
| **Input** | `cash_conversion_gap` (DSO − DPO), `has_payment_status_data` |
| **Not computable when** | `has_payment_status_data = false` OR `cash_conversion_gap = None` |
| **Payment data threshold** | At least 3 records with a `payment_status` field across sales or purchases |

**Scoring thresholds:**

| Cash Conversion Gap (days) | Points (of 25) | Assessment |
|---|---|---|
| ≤ 0 | 25 | Cash arrives before costs are due |
| < 15 | 19 | Short gap — manageable |
| < 30 | 13 | Moderate gap |
| < 60 | 6 | Significant gap — working capital pressure |
| ≥ 60 | 0 | Severe gap — financing likely needed |

### 10.5 Operational Risk (10 pt)

| Attribute | Value |
|---|---|
| **Measures** | Severity of active alerts and completeness of uploaded data |
| **Input** | `alerts_high_count`, `data_sources_present` |
| **Always computable** | Both sub-scores always return a value |

**Sub-A: High-Severity Alerts (5 pt)**

| High Alerts | Points |
|---|---|
| 0 | 5 |
| 1–2 | 2 |
| > 2 | 0 |

**Sub-B: Data Completeness (5 pt)**

| Data Sources Present | Points | Sources |
|---|---|---|
| ≥ 4 | 5 | Sales + Expenses + Purchases + Fixed Costs |
| ≥ 3 | 3 | — |
| ≥ 2 | 1 | — |
| < 2 | 0 | — |

---

## 11. Diagnostic Metrics

The following metrics are computed and displayed to provide additional context but are **not scored** — they do not affect the composite health score.

| Metric | Formula | Unit | Purpose |
|---|---|---|---|
| **Cost-to-Revenue Ratio** | `(total_outflows ÷ total_sales) × 100` | % | Overall cost pressure indicator |
| **Operating Margin %** | `((total_sales − variable_outflows) ÷ total_sales) × 100` | % | Profitability before fixed costs |
| **Burn Rate (Daily)** | `total_outflows ÷ period_days` | EUR/day | Cash consumption speed |
| **Operational Coverage** | `net_after_fixed ÷ (total_outflows ÷ period_days)` | Days | Proxy: margin-to-burn-rate coverage |
| **DSO** | `(open_receivables ÷ total_sales) × period_days` | Days | Individual collection timing |
| **DPO** | `(open_payables ÷ supplier_purchases) × period_days` | Days | Individual payment timing |

> **Why diagnostic, not scored?** These metrics either overlap with scored dimensions (e.g., operating margin is ~90% correlated with net margin for most SMEs) or represent individual components of a scored composite (e.g., DSO and DPO individually feed into the Cash Cycle dimension as a gap). Scoring them independently would create redundancy and double-counting.

---

## 12. Rules for Missing Data / Not-Computable Logic

### 12.1 General Principle

When a dimension lacks sufficient data to produce a meaningful score, it is marked as **not_computable** rather than defaulted to zero or a neutral value. This prevents the system from producing artificially favorable (or artificially unfavorable) scores.

### 12.2 Not-Computable Triggers by Dimension

| Dimension | Trigger | Reason Displayed |
|---|---|---|
| Net Margin | `total_sales ≤ 0` | "No revenue data" |
| Revenue Dynamics | Both `sales_trend_pct` and `margin_trend_pp` are None | "No previous period data" |
| Structural Strength | Both break-even and fixed cost sub-scores fail | "Insufficient data (no fixed costs or revenue)" |
| Cash Cycle | `has_payment_status_data = false` or `gap = None` | "No payment status data available" |
| Operational Risk | Never — always computable | — |

### 12.3 Sparse-Data False-Good Safeguard

A special guard triggers when:
- Only **1 data source** has been uploaded (typically just sales)
- AND net margin exceeds **50%** (artificially inflated because no costs are recorded)

In this case, the system appends a prominent caveat: *"Net margin may be overestimated: only one data source has been uploaded. Add operating expenses, supplier purchases, or fixed costs for a more accurate score."*

This warning appears in both the structured data caveats and the rule-based explanation text.

### 12.4 UI Representation

- **Not-computable dimensions** appear in the Health Score breakdown with grayed-out progress bars and "—" instead of points
- **Data caveats** are listed below the score explanation
- **The confidence badge** reflects the fraction of total weight that was actually scored

---

## 13. Proxy Metrics and Interpretation Caveats

### 13.1 What Is a Proxy Metric?

A proxy metric approximates a concept for which direct data is not available. In the Cashflow Monitor, the primary proxy is **Operational Coverage**.

### 13.2 Operational Coverage — Detailed Caveat

| Aspect | Detail |
|---|---|
| **What it approximates** | How long the business can sustain operations |
| **What it actually measures** | Ratio of net margin to daily burn rate |
| **What it does NOT include** | Bank balance, credit lines, receivable collection timing, payable schedules |
| **Why it can be misleading** | A business with €50k profit and €5k/day burn rate shows 10 days — but may have €200k in the bank |
| **UI label** | Always displayed as `"Operational Coverage ~ estimated"` |
| **In the health score** | Diagnostic only — does NOT drive any scored dimension |
| **AI handling** | AI must qualify this metric with "approximately" or "estimated from burn rate" |

### 13.3 DSO and DPO Caveats

Both DSO and DPO are **estimated values** that improve as users add payment status and due date fields to their records. The system displays an `~ estimated` badge and provides tooltips explaining the limitation.

### 13.4 Cumulative Cashflow Chart Caveat

The cumulative cashflow chart shows the **accumulation of daily net results** over the period. It does NOT represent the actual bank account balance. Rising lines indicate positive accumulation; falling lines indicate cash erosion. A prominent note is displayed alongside the chart.

---

## 14. AI Layer on Top of the Financial Engine

### 14.1 Architecture

The AI layer consists of two modes:

1. **Rule-based explanation** (default, zero API cost) — generated on every page load
2. **AI-powered explanation** (on-demand, via Claude API) — triggered by user action

Both modes read the **same structured outputs**: the health score, breakdown, KPI values, diagnostics, and data caveats. Neither mode invents financial facts.

### 14.2 How AI Works on Top of the Financial Data

The AI receives a structured prompt containing:

- The composite score and its label (e.g., "72/100 — Good")
- Per-dimension breakdown (e.g., "Net Margin: 21/25")
- Key KPI values (net result in EUR, operating margin %, operational coverage, DSO, outflow ratio)
- Data caveats and proxy warnings

The AI is instructed to:

- Write exactly 2–3 sentences of flowing text (no bullets, no emoji)
- Be concrete: cite strengths and critical areas with numbers
- Qualify proxy metrics with "approximately" or "indicates"
- Never present the score as an exact diagnosis
- Respect a 250-character maximum
- Respond in the user's locale (IT, EN, DE, FR)

### 14.3 What the AI Can Answer

| Question Domain | What the AI Can Do |
|---|---|
| **Profitability** | Explain whether the business is profitable, by how much, and the trend direction |
| **Cost pressure** | Identify which cost bucket (expenses, purchases, fixed costs) is heaviest relative to revenue |
| **Break-even** | Explain how far above or below the break-even threshold the business operates |
| **Trends** | Describe whether revenue and margin are improving or declining period-over-period |
| **Cash cycle** | Explain the gap between collection and payment timing and its business impact |
| **Data completeness** | Warn when the score is based on limited data and suggest what to upload |
| **Operational warnings** | Flag high-severity alerts and their potential impact |
| **Priority actions** | Suggest the most impactful improvement areas based on the weakest dimensions |
| **Proxy qualification** | Clarify when a metric (especially operational coverage) is an estimate, not a measured fact |

### 14.4 What the AI Cannot Reliably Infer

| Limitation | Reason |
|---|---|
| **Actual bank balance** | No bank account data is ingested |
| **Tax obligations** | Tax computation is out of scope |
| **Future projections beyond recorded due dates** | Forecasting requires assumptions the system does not make |
| **Industry benchmarks** | The system does not compare against sector-specific norms |
| **Root cause analysis** | The AI can identify WHAT is weak but not WHY (that requires domain knowledge) |
| **Accounting accuracy** | The system reflects uploaded data — if uploads are incomplete or incorrect, so is the analysis |
| **Investment advice** | The system is not a financial advisor and should not be used for investment decisions |

### 14.5 AI Guardrails

- Temperature is set to **0.2** (conservative, deterministic output)
- Maximum output tokens: **200**
- If the Claude API is unavailable, the system **always falls back** to rule-based explanation — no silent failure
- The AI system prompt includes explicit instructions to never overstate proxy metrics

---

## 15. Example Interpretation Logic

### Scenario: Growing E-commerce with Cash Cycle Pressure

**Input:** Revenue €200k, Margin 20%, Sales Trend +25%, Margin Trend +3pp, Fixed Costs €20k, DSO 55 days, DPO 10 days, 0 high alerts, 4 data sources.

**Expected Health Score:**

| Dimension | Points | Assessment |
|---|---|---|
| Net Margin (25) | 25/25 | 20% margin — excellent |
| Revenue Dynamics (20) | 20/20 | Strong growth in both sales and margin |
| Structural Strength (20) | 20/20 | High headroom above break-even, moderate fixed costs |
| Cash Cycle (25) | 6/25 | 45-day gap — significant working capital pressure |
| Operational Risk (10) | 10/10 | No alerts, complete data |

**Score: ~81 (Excellent)**
**Confidence: 1.0**
**Strongest: Net Margin, Revenue Dynamics, Structural Strength**
**Weakest: Cash Cycle (6/25 = 24% → high-priority issue)**

**Expected Priority Action:** "Accelerate collections or negotiate longer payment terms with suppliers."

**Expected AI Explanation (IT):** *"Salute finanziaria eccellente (81/100) con margine solido al 20% e forte crescita. Attenzione al ciclo di cassa: i 45 giorni di gap tra incassi e pagamenti indicano pressione sul capitale circolante."*

This example demonstrates how a business can score "Excellent" overall while still having a clearly flagged problem area with a specific, actionable recommendation.

---

## 16. Limitations

1. **Not a bank statement.** The Cashflow Monitor operates on uploaded transaction data, not real-time bank feeds. There is no visibility into actual cash balances, credit lines, or overdraft facilities.

2. **Garbage in, garbage out.** If uploaded data is incomplete, duplicated, or incorrectly categorized, the KPIs and health score will reflect those inaccuracies. The system provides import validation and duplicate detection but cannot verify business-level correctness.

3. **No inventory or COGS.** The system does not track inventory or cost of goods sold. Manufacturing or retail businesses with significant inventory should interpret the break-even and margin metrics in that context.

4. **Fixed-period comparisons.** Period-over-period comparisons use equal-length calendar windows. Businesses with seasonal patterns may see misleading trends during transition periods.

5. **Sector-agnostic thresholds.** The scoring thresholds (e.g., 15% net margin = excellent) are set for general SME applicability. Capital-intensive industries, early-stage startups, or high-margin service businesses may find certain thresholds too generous or too strict for their context.

6. **Not a substitute for professional advice.** The Cashflow Monitor is a monitoring and signaling tool. It does not replace the judgment of an accountant, CFO, or financial advisor. Users should consult qualified professionals for material financial decisions.

---

## 17. Glossary

| Term | Definition |
|---|---|
| **Break-Even Point** | The revenue level at which total costs equal total revenue — no profit, no loss |
| **Burn Rate** | Average daily total outflows; indicates how fast the business consumes cash |
| **Cash Conversion Gap** | DSO minus DPO; the number of days between paying suppliers and collecting from customers |
| **Confidence** | Fraction of total health score weight that was computable (0.0–1.0) |
| **Diagnostic Metric** | A metric displayed for context but not included in the health score calculation |
| **DPO** | Days Payable Outstanding — average days to pay suppliers |
| **DSO** | Days Sales Outstanding — average days to collect from customers |
| **Fixed Costs** | Costs incurred regardless of revenue (rent, salaries, leasing, subscriptions) |
| **Net Margin** | Net profit after all costs, expressed as a percentage of revenue |
| **Not Computable** | A dimension that cannot be scored due to insufficient data; excluded from the score |
| **Operational Coverage** | Proxy metric estimating margin-to-burn-rate coverage in days; not real liquidity |
| **Period Days** | Calendar days in the selected period, inclusive of start and end dates |
| **Proxy Metric** | A metric that approximates a concept for which direct data is unavailable |
| **Rescaling** | Redistribution of weight from not-computable dimensions to computable ones |
| **VCR** | Variable Cost Ratio — ratio of variable outflows to revenue |
| **Variable Outflows** | Operating expenses + supplier purchases (costs that vary with activity) |

---

## 18. Governance / Revision Notes

| Field | Value |
|---|---|
| **Document Version** | v1.0 |
| **Status** | Draft for Review |
| **Model Version** | Health Score v3.0 (5 dimensions) |
| **Previous Model** | v2.x (8 dimensions — deprecated due to 90% correlation between 3 pairs) |
| **KPI Formula Layer** | Canonical (`kpi_formulas.py`) — single source of truth across overview, insights, and alerts |
| **Last Code Audit** | March 2026 |
| **Test Coverage** | 722 backend tests passing |
| **Locales Supported** | Italian, English, German, French |
| **AI Model** | Claude (Anthropic), temperature 0.2, max 200 tokens |

### Planned for v1.1

- Confidence badge more prominent in the Health Score gauge UI
- Sector-specific threshold profiles (e.g., restaurant vs. manufacturing)
- Bank feed integration (when available) to replace proxy operational coverage with real liquidity

### Change Log

| Date | Change | Author |
|---|---|---|
| March 2026 | Initial draft — v1.0 | AFianco Product & Engineering |

---

*This document is proprietary to AFianco S.r.l. Distribution is limited to authorized internal stakeholders and designated investors.*
