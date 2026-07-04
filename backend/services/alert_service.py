"""
Alert Service — arch-v1 dispatcher.

Transforms alert_service.py from a cashflow-specific service into a
module-agnostic dispatcher.  The actual detection logic for each module
lives in the module's alert_rules callable, registered via core.module_registry.

Changes vs v2.1:
  - All cashflow-specific check code removed from this file; it lives in
    modules/cashflow_monitor/alert_rules.py (extracted verbatim).
  - generate_and_save_alerts() now iterates all registered modules and calls
    their alert_rules capability.  alert_repository.create_many() stays here
    as shared infrastructure.
  - Public signature of generate_and_save_alerts(org_id) is unchanged.
  - Behavioural note: when there is no data the response is
    "Generated 0 new alerts" instead of "No data available for analysis".
    The alerts_generated count (0) is identical; the message field is not
    consumed by the frontend in a structured way.

Design:
  - Lazy import of core.module_registry inside the function body avoids
    circular-import risk at module load time.
  - Each module's alert_rules call is isolated in its own try/except so a
    failure in one module does not prevent others from running.
"""
import logging
from repositories import alert_repository

logger = logging.getLogger(__name__)


async def generate_and_save_alerts(org_id: str, locale: str = "it") -> dict:
    """Run anomaly detection for all registered modules and persist new alerts.

    For each module registered in core.module_registry that exposes an
    alert_rules capability, calls alert_rules(org_id) to obtain the list
    of new Alert objects, then persists them via alert_repository.create_many().

    Returns:
        {"message": "Generated N new alerts", "alerts_generated": N}

    Never raises — errors from individual modules are logged and skipped.
    """
    from core.module_registry import get_all as registry_get_all

    total_new = 0
    all_new_alerts = []

    for module in registry_get_all():
        if module.alert_rules is None:
            continue
        try:
            new_alerts = await module.alert_rules(org_id)
            if new_alerts:
                await alert_repository.create_many(new_alerts)
                total_new += len(new_alerts)
                all_new_alerts.extend(new_alerts)
                logger.info(
                    "alert_service: saved %d alerts for org=%s module=%s",
                    len(new_alerts), org_id, module.module_key,
                )
        except Exception as exc:
            logger.error(
                "alert_service: error running alert_rules for module=%s org=%s: %s",
                module.module_key, org_id, exc, exc_info=True,
            )

    # ── v3.0: Email notification for HIGH severity alerts ───────────────────
    if all_new_alerts:
        try:
            from services.alert_notification_service import notify_high_severity_batch
            await notify_high_severity_batch(all_new_alerts, org_id, locale)
        except Exception as exc:
            logger.warning(
                "alert_service: HIGH alert notification failed for org=%s: %s",
                org_id, exc,
            )

    # ── v2.5: AI root-cause analysis for new alerts (gated by entitlement) ──
    #     Dispatches through the module registry so each module can provide
    #     its own alert_analysis capability.
    if all_new_alerts:
        try:
            from collections import defaultdict
            from repositories import organization_repository
            from services.module_access import check_module_access
            from core.module_registry import get as registry_get

            org_doc = await organization_repository.find_by_id(org_id)

            # Group alerts by module_key so each module analyses its own
            alerts_by_module = defaultdict(list)
            for alert in all_new_alerts:
                mk = getattr(alert, "module_key", None) or "cashflow_monitor"
                alerts_by_module[mk].append(alert)

            for mk, module_alerts in alerts_by_module.items():
                module = registry_get(mk)
                if not module or module.alert_analysis is None:
                    continue

                # Entitlement check — alert_analysis is gated under ai_assistant
                try:
                    await check_module_access(
                        org_id, "ai_assistant", "alert_analysis", org_doc=org_doc,
                    )
                except Exception:
                    logger.debug(
                        "alert_service: AI analysis skipped for org=%s module=%s (no entitlement)",
                        org_id, mk,
                    )
                    continue

                # Wave 13.4 — group alerts by their analysis window so
                # each batch is analysed with KPIs from the SAME window
                # that produced the alert. Pre-13.4 we passed kpis={} →
                # Sonnet had to invent context, which produced generic
                # analyses that sometimes contradicted the alert's own
                # numbers. Now each batch is paired with the real KPIs
                # of its window.
                #
                # Grouping key is (start, end). Alerts whose window is
                # still None (rare — only legacy pre-Wave-13.4 alerts
                # bypassing the engine default) fall into a single
                # "unknown" bucket analysed with empty kpis (backward
                # compatible).
                from collections import defaultdict as _defaultdict
                alerts_by_window = _defaultdict(list)
                for alert in module_alerts:
                    start = getattr(alert, "period_start", None)
                    end = getattr(alert, "period_end", None)
                    alerts_by_window[(start, end)].append(alert)

                module_modified_total = 0
                for (win_start, win_end), batch in alerts_by_window.items():
                    # Compute KPIs for this batch's window. cashflow KPIs
                    # are the only ones alert_analysis prompts for today
                    # (Sonnet's batch message templates KPIs as
                    # ricavi/uscite/margine — see alert_analysis._build_batch_message).
                    batch_kpis = await _build_alert_window_kpis(
                        org_id, win_start, win_end, locale,
                    )

                    # Wave 9.B — organization_id propagated so usage event
                    # is correctly attributed.
                    analyses = await module.alert_analysis(
                        batch, kpis=batch_kpis, locale=locale,
                        organization_id=org_id,
                    )
                    if analyses:
                        modified = await alert_repository.bulk_update_ai_analysis(
                            analyses, org_id,
                        )
                        module_modified_total += modified

                if module_modified_total:
                    logger.info(
                        "alert_service: AI analysis added to %d/%d alerts for "
                        "org=%s module=%s (Wave 13.4: batched by window)",
                        module_modified_total, len(module_alerts), org_id, mk,
                    )
        except Exception as exc:
            logger.warning(
                "alert_service: AI analysis pass failed for org=%s: %s", org_id, exc,
            )

    return {
        "message": f"Generated {total_new} new alerts",
        "alerts_generated": total_new,
    }


# ── Wave 13.4 — KPI builder for alert AI analysis ───────────────────────────


async def _build_alert_window_kpis(
    org_id: str,
    window_start: "str | None",
    window_end: "str | None",
    locale: str,
) -> dict:
    """Return cashflow KPIs computed on a specific window.

    Used by ``generate_and_save_alerts`` to pair each batch of new
    alerts with the KPIs of the window THEY were generated on, so the
    Sonnet root-cause analysis cites numbers that are actually
    consistent with the alert's premise.

    Returns an empty dict on any failure (preserves the pre-13.4
    behaviour where alert_analysis received kpis={} — never blocks the
    pipeline, just degrades gracefully to a generic analysis).
    """
    if not window_start or not window_end:
        # Legacy pre-13.4 alerts with no recorded window. Fall back to
        # pre-13.4 behaviour: empty kpis, generic analysis.
        return {}

    try:
        from modules.cashflow_monitor.cashflow_summary import build_ai_summary

        summary = await build_ai_summary(
            org_id,
            period="custom",
            start_date=window_start,
            end_date=window_end,
            locale=locale,
        )
        # alert_analysis._build_batch_message reads these specific keys
        # from the kpis dict — preserve exact names so the prompt
        # interpolation stays correct.
        kpis_block = (summary or {}).get("kpis", {}) or {}
        return {
            "total_sales":           kpis_block.get("total_sales", 0),
            "total_outflows":        kpis_block.get("total_outflows", 0),
            "operating_margin_pct":  kpis_block.get("operating_margin_pct", 0),
            "dso":                   kpis_block.get("dso", 0),
            "dpo":                   kpis_block.get("dpo", 0),
            "giorni_autonomia":      kpis_block.get("giorni_autonomia", 0),
            "total_outflow_ratio":   kpis_block.get("total_outflow_ratio", 0),
            # Window metadata for the audit trail — alert_analysis will
            # NOT inject these into the prompt (the template ignores
            # unknown keys), but they are useful in logs.
            "_window_start":         window_start,
            "_window_end":           window_end,
        }
    except Exception as exc:
        logger.warning(
            "alert_service: failed to build KPIs for window %s→%s org=%s: %s",
            window_start, window_end, org_id, exc,
        )
        return {}
