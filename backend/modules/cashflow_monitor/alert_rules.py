"""
Cashflow Monitor — alert rules.

Extracted verbatim from alert_service.py (v2.1).  Contains all
cashflow-specific anomaly detection logic:
  1. Daily sales deviation vs 30-day average (last 7 days)
  2. Daily expense deviation vs 30-day average (last 7 days)
  3. Per-category expense spike >50% above category average (last 7 days)
  4. Consecutive days with negative cashflow (last 14 days)

Plus deduplication: existing open alerts are checked before inserting.

Public interface:
    run_alert_checks(org_id) -> List[Alert]
        Self-contained: loads its own data, runs all checks, returns the
        Alert list.  alert_service calls create_many() on the result.
        Never raises — returns [] on any error that escapes a sub-check.
"""
import asyncio
from typing import List
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from models import Alert, AlertSeverity
from repositories import analytics_repository, alert_repository
from database import expense_records_collection
from modules.cashflow_monitor import kpi_formulas

_SCHEMA_VERSION = "2.0"

# Deviation thresholds for sales / overall expense anomalies (unchanged)
_LOW_THRESHOLD = 10      # %
_MEDIUM_THRESHOLD = 20   # %
_HIGH_THRESHOLD = 30     # %

# Extra threshold for per-category anomalies (more lenient: noise is higher)
_CATEGORY_HIGH_THRESHOLD = 50  # %


def _get_deviation_severity(deviation: float):
    """Map a deviation percentage to AlertSeverity. Returns None if below threshold."""
    if deviation > _HIGH_THRESHOLD:
        return AlertSeverity.HIGH
    elif deviation > _MEDIUM_THRESHOLD:
        return AlertSeverity.MEDIUM
    elif deviation > _LOW_THRESHOLD:
        return AlertSeverity.LOW
    return None


async def run_alert_checks(org_id: str) -> List[Alert]:
    """Run all cashflow anomaly checks for the organisation.

    Returns the list of new Alert objects to persist.  Returns [] when
    there is no data or all alerts already exist (deduplicated).

    Detection order:
    1. Sales deviation vs 30-day average (per day, last 7 days)
    2. Overall expense deviation vs 30-day average (per day, last 7 days)
    3. Per-category expense spike (>50% above category average, last 7 days)
    4. Consecutive negative cashflow (last 14 days)
    """
    end_date = datetime.now(timezone.utc).date()
    start_date = end_date - timedelta(days=30)
    start_str = start_date.isoformat()
    end_str = end_date.isoformat()

    sales_by_date = await analytics_repository.aggregate_sales_by_date(
        org_id, start_str, end_str
    )
    expenses_by_date = await analytics_repository.aggregate_expenses_by_date(
        org_id, start_str, end_str
    )

    if not sales_by_date and not expenses_by_date:
        return []

    avg_sales = sum(sales_by_date.values()) / len(sales_by_date) if sales_by_date else 0
    avg_expenses = (
        sum(expenses_by_date.values()) / len(expenses_by_date) if expenses_by_date else 0
    )

    # Load open alert keys for deduplication (date_reference, title_prefix)
    existing_keys = await alert_repository.find_active_keys(org_id, "cashflow_monitor")

    new_alerts: List[Alert] = []

    # ── 1 & 2: Sales and expense daily deviation ───────────────────────────────
    for i in range(7):
        check_date = (end_date - timedelta(days=i)).isoformat()

        # Sales anomaly: daily sales well below the 30-day average
        daily_sales = sales_by_date.get(check_date, 0)
        if daily_sales > 0 and avg_sales > 0:
            deviation = (avg_sales - daily_sales) / avg_sales * 100
            severity = _get_deviation_severity(deviation)
            if severity:
                # Key matches find_active_keys fingerprint: metric_payload.alert_type
                key = (check_date, "sales_below_avg")
                if key not in existing_keys:
                    new_alerts.append(Alert(
                        organization_id=org_id,
                        module_key="cashflow_monitor",
                        severity=severity,
                        title=f"Ricavi {deviation:.0f}% sotto la media",
                        summary=(
                            f"Il {check_date} i ricavi sono stati €{daily_sales:,.0f}, "
                            f"pari a {deviation:.0f}% sotto la media di 30 giorni "
                            f"(€{avg_sales:,.0f})."
                        ),
                        date_reference=check_date,
                        metric_payload={
                            "actual": daily_sales,
                            "average": avg_sales,
                            "deviation_pct": round(deviation, 1),
                            "alert_type": "sales_below_avg",
                        },
                        schema_version=_SCHEMA_VERSION,
                    ))

        # Expense anomaly: daily expenses well above the 30-day average
        daily_expenses = expenses_by_date.get(check_date, 0)
        if daily_expenses > 0 and avg_expenses > 0:
            deviation = (daily_expenses - avg_expenses) / avg_expenses * 100
            severity = _get_deviation_severity(deviation)
            if severity:
                # Key matches find_active_keys fingerprint: metric_payload.alert_type
                key = (check_date, "expenses_above_avg")
                if key not in existing_keys:
                    new_alerts.append(Alert(
                        organization_id=org_id,
                        module_key="cashflow_monitor",
                        severity=severity,
                        title=f"Spese {deviation:.0f}% sopra la media",
                        summary=(
                            f"Il {check_date} le spese sono state €{daily_expenses:,.0f}, "
                            f"pari a {deviation:.0f}% sopra la media di 30 giorni "
                            f"(€{avg_expenses:,.0f})."
                        ),
                        date_reference=check_date,
                        metric_payload={
                            "actual": daily_expenses,
                            "average": avg_expenses,
                            "deviation_pct": round(deviation, 1),
                            "alert_type": "expenses_above_avg",
                        },
                        schema_version=_SCHEMA_VERSION,
                    ))

    # ── 3: Per-category expense spike ─────────────────────────────────────────
    category_alerts = await _check_category_expense_anomalies(
        org_id, start_str, end_str, end_date, existing_keys
    )
    new_alerts.extend(category_alerts)

    # ── 4: Consecutive negative cashflow ──────────────────────────────────────
    consecutive_alert = _check_consecutive_negative_cashflow(
        org_id, sales_by_date, expenses_by_date, end_date, existing_keys
    )
    if consecutive_alert:
        new_alerts.append(consecutive_alert)

    # ── 5: Overdue receivables (>60 days) ────────────────────────────────────
    overdue_alerts = await _check_overdue_receivables(org_id, existing_keys)
    new_alerts.extend(overdue_alerts)

    # ── 6: Cash gap forecast (scadenzario netto 30gg < 0) ────────────────────
    cash_gap_alert = await _check_cash_gap_forecast(org_id, existing_keys)
    if cash_gap_alert:
        new_alerts.append(cash_gap_alert)

    # ── 7: Structural risks (DSO, CCC, supplier concentration, autonomia) ────
    structural_alerts = await _check_structural_risks(
        org_id, sales_by_date, expenses_by_date, existing_keys
    )
    new_alerts.extend(structural_alerts)

    return new_alerts


# ── Private check helpers ──────────────────────────────────────────────────────

async def _check_category_expense_anomalies(
    org_id: str,
    start_str: str,
    end_str: str,
    end_date,
    existing_keys: set,
) -> List[Alert]:
    """Detect per-category expense spikes over the last 7 days.

    For each expense category, computes the 30-day daily average and flags
    any day in the last 7 where that category exceeds the average by more than
    _CATEGORY_HIGH_THRESHOLD (50%).  One alert per (category, day) pair.

    Never raises — returns [] on any error.
    """
    try:
        # Aggregate expenses by (date, category) for the full 30-day window
        pipeline = [
            {
                "$match": {
                    "organization_id": org_id,
                    "date": {"$gte": start_str, "$lte": end_str},
                }
            },
            {
                "$group": {
                    "_id": {
                        "date": "$date",
                        "category": {"$ifNull": ["$category", "Uncategorized"]},
                    },
                    "total": {"$sum": "$amount"},
                }
            },
        ]
        cursor = expense_records_collection.aggregate(pipeline)
        docs = await cursor.to_list(5000)

        # Build category→{date: amount} and compute per-category averages
        by_cat: dict = defaultdict(dict)
        for doc in docs:
            cat = doc["_id"]["category"]
            date = doc["_id"]["date"]
            by_cat[cat][date] = doc["total"]

        alerts: List[Alert] = []
        for cat, date_totals in by_cat.items():
            if not date_totals:
                continue
            avg = sum(date_totals.values()) / len(date_totals)
            if avg <= 0:
                continue

            for i in range(7):
                check_date = (end_date - timedelta(days=i)).isoformat()
                daily = date_totals.get(check_date, 0)
                if daily <= 0:
                    continue
                deviation = (daily - avg) / avg * 100
                if deviation > _CATEGORY_HIGH_THRESHOLD:
                    # Key matches find_active_keys fingerprint for category_expense_spike:
                    # "cat_<category_name>" (per-category dedup prevents cross-category collisions)
                    cat_slug = cat.lower().replace(" ", "_")
                    key = (check_date, f"cat_{cat_slug}")
                    if key not in existing_keys:
                        alerts.append(Alert(
                            organization_id=org_id,
                            module_key="cashflow_monitor",
                            severity=(
                                AlertSeverity.HIGH
                                if deviation > 100
                                else AlertSeverity.MEDIUM
                            ),
                            title=f"Categoria '{cat}' {deviation:.0f}% sopra la media",
                            summary=(
                                f"Il {check_date} le spese in '{cat}' hanno raggiunto "
                                f"€{daily:,.0f}, pari a {deviation:.0f}% sopra la media "
                                f"giornaliera di €{avg:,.0f} per questa categoria."
                            ),
                            date_reference=check_date,
                            metric_payload={
                                "category": cat,
                                "actual": round(daily, 2),
                                "average": round(avg, 2),
                                "deviation_pct": round(deviation, 1),
                                "alert_type": "category_expense_spike",
                            },
                            schema_version=_SCHEMA_VERSION,
                        ))
        return alerts

    except Exception:
        return []


def _check_consecutive_negative_cashflow(
    org_id: str,
    sales_by_date: dict,
    expenses_by_date: dict,
    end_date,
    existing_keys: set,
) -> "Alert | None":
    """Detect a run of consecutive days where cashflow < 0.

    Unchanged logic from Phase 2; deduplication check preserved.
    """
    all_dates = sorted(set(sales_by_date.keys()) | set(expenses_by_date.keys()))
    consecutive_negative = 0
    max_consecutive = 0
    negative_start = None

    for date in all_dates[-14:]:
        sales = sales_by_date.get(date, 0)
        expenses = expenses_by_date.get(date, 0)
        if sales - expenses < 0:
            consecutive_negative += 1
            if negative_start is None:
                negative_start = date
            max_consecutive = max(max_consecutive, consecutive_negative)
        else:
            consecutive_negative = 0
            negative_start = None

    if max_consecutive >= 3:
        ref_date = negative_start or end_date.isoformat()
        # Key matches find_active_keys fingerprint: "consecutive_negative_cashflow_{days}"
        # Using the count allows a new alert when severity escalates (3→5 consecutive days).
        key = (ref_date, f"consecutive_negative_cashflow_{max_consecutive}")
        if key in existing_keys:
            return None
        return Alert(
            organization_id=org_id,
            module_key="cashflow_monitor",
            severity=AlertSeverity.HIGH if max_consecutive >= 5 else AlertSeverity.MEDIUM,
            title=f"Cashflow negativo per {max_consecutive} giorni consecutivi",
            summary=(
                f"L'azienda ha registrato cashflow negativo per "
                f"{max_consecutive} giorni consecutivi a partire dal {ref_date}."
            ),
            date_reference=ref_date,
            metric_payload={
                "consecutive_days": max_consecutive,
                "alert_type": "consecutive_negative_cashflow",
            },
            schema_version=_SCHEMA_VERSION,
        )
    return None


async def _check_overdue_receivables(
    org_id: str,
    existing_keys: set,
) -> List[Alert]:
    """Detect overdue receivables grouped by aging bucket.

    Uses the aging aggregation from analytics_repository.
    Generates one alert per aging bucket (61-90gg, >90gg).
    Never raises — returns [] on any error.
    """
    try:
        aging = await analytics_repository.aggregate_receivables_by_aging(org_id)
        if not aging:
            return []

        alerts: List[Alert] = []
        today_str = datetime.now(timezone.utc).date().isoformat()

        for bucket in aging:
            bucket_label = bucket.get("bucket", "")
            total = bucket.get("total", 0)
            count = bucket.get("count", 0)

            if total <= 0:
                continue

            # Only alert on 61-90 and >90 day buckets
            if bucket_label == "61-90":
                severity = AlertSeverity.MEDIUM
            elif bucket_label == ">90":
                severity = AlertSeverity.HIGH
            else:
                continue

            key = (today_str, f"overdue_receivables_{bucket_label}")
            if key in existing_keys:
                continue

            alerts.append(Alert(
                organization_id=org_id,
                module_key="cashflow_monitor",
                severity=severity,
                title=f"Crediti scaduti {bucket_label} giorni: €{total:,.0f}",
                summary=(
                    f"Ci sono {count} fatture per un totale di €{total:,.0f} "
                    f"con scadenza nella fascia {bucket_label} giorni. "
                    f"Valutare azioni di sollecito o recupero crediti."
                ),
                date_reference=today_str,
                metric_payload={
                    "bucket": bucket_label,
                    "total": round(total, 2),
                    "count": count,
                    "alert_type": f"overdue_receivables_{bucket_label}",
                },
                schema_version=_SCHEMA_VERSION,
            ))
        return alerts
    except Exception:
        return []


async def _check_cash_gap_forecast(
    org_id: str,
    existing_keys: set,
) -> "Alert | None":
    """Alert when net scadenzario over next 30 days is negative (cash gap).

    Compares upcoming receivables vs upcoming payables in the next 30 days.
    Never raises — returns None on any error.
    """
    try:
        upcoming_recv = await analytics_repository.aggregate_upcoming_receivables(org_id, 30)
        upcoming_pay = await analytics_repository.aggregate_upcoming_payables(org_id, 30)

        recv_total = sum(r["total"] for r in upcoming_recv)
        pay_total = sum(p["total"] for p in upcoming_pay)
        net = round(recv_total - pay_total, 2)

        if net >= 0:
            return None

        today_str = datetime.now(timezone.utc).date().isoformat()
        key = (today_str, "cash_gap_forecast_30")
        if key in existing_keys:
            return None

        gap = abs(net)
        return Alert(
            organization_id=org_id,
            module_key="cashflow_monitor",
            severity=AlertSeverity.HIGH if gap > 10000 else AlertSeverity.MEDIUM,
            title=f"Gap di cassa previsto: -€{gap:,.0f} nei prossimi 30gg",
            summary=(
                f"Nei prossimi 30 giorni le uscite previste (€{pay_total:,.0f}) "
                f"superano gli incassi attesi (€{recv_total:,.0f}) di €{gap:,.0f}. "
                f"Verificare la copertura di liquidità."
            ),
            date_reference=today_str,
            metric_payload={
                "upcoming_receivables": round(recv_total, 2),
                "upcoming_payables": round(pay_total, 2),
                "net_gap": net,
                "alert_type": "cash_gap_forecast_30",
            },
            schema_version=_SCHEMA_VERSION,
        )
    except Exception:
        return None


async def _check_structural_risks(
    org_id: str,
    sales_by_date: dict,
    expenses_by_date: dict,
    existing_keys: set,
) -> List[Alert]:
    """Detect structural financial risks: DSO>60, CCC>90, supplier concentration>40%, autonomia<30.

    Uses data already loaded + additional scadenzario/supplier queries.
    Never raises — returns [] on any error.
    """
    try:
        today_str = datetime.now(timezone.utc).date().isoformat()
        end_date = datetime.now(timezone.utc).date()
        start_date = end_date - timedelta(days=30)

        total_sales = sum(sales_by_date.values())
        total_expenses = sum(expenses_by_date.values())
        # v3.0: use calendar days (not active data days) for financial ratios
        period_days = (end_date - start_date).days + 1

        # Fetch additional data for structural checks
        (
            open_receivables,
            open_payables,
            purchases_by_date_30,
            purchases_by_supplier,
        ) = await asyncio.gather(
            analytics_repository.aggregate_open_receivables(org_id),
            analytics_repository.aggregate_open_payables(org_id),
            analytics_repository.aggregate_purchases_by_date(
                org_id, start_date.isoformat(), end_date.isoformat()
            ),
            analytics_repository.aggregate_purchases_by_supplier(
                org_id, start_date.isoformat(), end_date.isoformat()
            ),
        )

        supplier_purchases = sum(purchases_by_date_30.values())
        variable_outflows = total_expenses + supplier_purchases
        fixed_costs_total = await analytics_repository.aggregate_fixed_costs_total(
            org_id, start_date.isoformat(), end_date.isoformat()
        )
        total_outflows = variable_outflows + fixed_costs_total

        alerts: List[Alert] = []

        # DSO > 60 days
        _dso = kpi_formulas.dso(open_receivables, total_sales, period_days)
        if _dso is not None and _dso > 60:
            dso = _dso
            if True:
                key = (today_str, "structural_dso_high")
                if key not in existing_keys:
                    alerts.append(Alert(
                        organization_id=org_id,
                        module_key="cashflow_monitor",
                        severity=AlertSeverity.HIGH if dso > 90 else AlertSeverity.MEDIUM,
                        title=f"DSO elevato: {dso:.0f} giorni",
                        summary=(
                            f"Il tempo medio di incasso (DSO) è di {dso:.0f} giorni, "
                            f"significativamente sopra la soglia di 60. Rischio liquidità: "
                            f"i clienti pagano troppo tardi."
                        ),
                        date_reference=today_str,
                        metric_payload={"dso": dso, "alert_type": "structural_dso_high"},
                        schema_version=_SCHEMA_VERSION,
                    ))

        # CCC > 90 days
        _dso_ccc = kpi_formulas.dso(open_receivables, total_sales, period_days)
        _dpo_ccc = kpi_formulas.dpo(open_payables, supplier_purchases, period_days)
        _ccc = kpi_formulas.cash_conversion_gap(_dso_ccc, _dpo_ccc)
        if _ccc is not None and _ccc > 90:
            dso = _dso_ccc or 0.0
            dpo = _dpo_ccc or 0.0
            ccc = _ccc
            if True:
                key = (today_str, "structural_ccc_high")
                if key not in existing_keys:
                    alerts.append(Alert(
                        organization_id=org_id,
                        module_key="cashflow_monitor",
                        severity=AlertSeverity.HIGH,
                        title=f"Ciclo di cassa lungo: {ccc:.0f} giorni",
                        summary=(
                            f"Il Cash Conversion Cycle è di {ccc:.0f} giorni (DSO {dso:.0f} − DPO {dpo:.0f}). "
                            f"L'azienda finanzia il ciclo operativo troppo a lungo."
                        ),
                        date_reference=today_str,
                        metric_payload={"ccc": ccc, "dso": dso, "dpo": dpo, "alert_type": "structural_ccc_high"},
                        schema_version=_SCHEMA_VERSION,
                    ))

        # Supplier concentration > 40%
        if purchases_by_supplier and supplier_purchases > 0:
            top_supplier = purchases_by_supplier[0]
            top_total = top_supplier.get("total", 0)
            top_pct = round((top_total / supplier_purchases * 100), 1)
            if top_pct > 40:
                top_name = str(top_supplier.get("_id", "N/D"))[:50]
                key = (today_str, "structural_supplier_concentration")
                if key not in existing_keys:
                    alerts.append(Alert(
                        organization_id=org_id,
                        module_key="cashflow_monitor",
                        severity=AlertSeverity.MEDIUM,
                        title=f"Concentrazione fornitore: {top_name} al {top_pct}%",
                        summary=(
                            f"Il fornitore '{top_name}' rappresenta il {top_pct}% degli acquisti totali. "
                            f"Rischio: dipendenza da un singolo fornitore. Valutare diversificazione."
                        ),
                        date_reference=today_str,
                        metric_payload={
                            "supplier": top_name,
                            "percentage": top_pct,
                            "alert_type": "structural_supplier_concentration",
                        },
                        schema_version=_SCHEMA_VERSION,
                    ))

        # Giorni autonomia < 30
        net_after_fixed = total_sales - total_outflows
        _giorni = kpi_formulas.operational_coverage_days(
            net_after_fixed, total_outflows, period_days,
        )
        if _giorni is not None and _giorni < 30 and _giorni >= 0:
            giorni = _giorni
            if True:
                key = (today_str, "structural_low_autonomia")
                if key not in existing_keys:
                    alerts.append(Alert(
                        organization_id=org_id,
                        module_key="cashflow_monitor",
                        severity=AlertSeverity.HIGH if giorni < 15 else AlertSeverity.MEDIUM,
                        title=f"Autonomia finanziaria critica: {giorni:.0f} giorni",
                        summary=(
                            f"Al ritmo attuale di spesa, la cassa copre solo {giorni:.0f} giorni. "
                            f"Priorità: ridurre le uscite o aumentare gli incassi rapidamente."
                        ),
                        date_reference=today_str,
                        metric_payload={"giorni_autonomia": giorni, "alert_type": "structural_low_autonomia"},
                        schema_version=_SCHEMA_VERSION,
                    ))

        return alerts
    except Exception:
        return []
