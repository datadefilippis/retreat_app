"""
Digest Report Builder — orchestrates PDF report generation.

Reuses build_overview() for data (zero extra DB queries).
Generates charts via digest_charts, assembles PDF via digest_pdf.
Optionally includes AI insights/recommendations (Core+ plans).
"""

import logging
from typing import Optional
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)


async def build_digest_report(
    org_id: str,
    period_days: int = 7,
    digest_type: str = "weekly",
    locale: str = "it",
    include_ai: bool = True,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    *,
    user_id: Optional[str] = None,
) -> Optional[dict]:
    """Build a complete PDF digest report.

    Returns dict with:
        pdf_bytes: bytes — the PDF file
        sections: dict — structured data for frontend preview
        kpis_summary: dict — backward compat with Digest model
        alerts_count: int
        content: str — text summary (for DB storage)
        model_version: str
        format: "report"
        has_pdf: True
    """
    # Wave 12.A — use the full cross-module context (cashflow + customers
    # + products + commerce + enriched health) so the PDF can render the
    # new sections too. Single source of truth shared with the text path.
    from modules.cashflow_monitor.digest_context_builder import build_digest_context
    from modules.cashflow_monitor.digest_charts import (
        generate_daily_chart, generate_cumulative_chart,
        generate_category_chart, generate_health_gauge,
    )
    from modules.cashflow_monitor.digest_pdf import build_report_pdf

    # CH compliance v1: resolve the org's currency so the DB-stored
    # text content and the AI prompt both speak the merchant's units
    # instead of the previous "EUR" hardcode.
    from repositories import organization_repository
    from services.currency_service import get_currency_for_org
    org_doc = await organization_repository.find_by_id(org_id)
    org_currency = get_currency_for_org(org_doc or {})

    # ── 1. Compute date range ────────────────────────────────────────────
    if not end_date:
        end_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if not start_date:
        start_date = (
            datetime.now(timezone.utc) - timedelta(days=period_days)
        ).strftime("%Y-%m-%d")

    # ── 2. Fetch all data via the full digest context (Wave 12.A) ─────────
    try:
        overview = await build_digest_context(
            org_id=org_id,
            period=f"{period_days}d",
            start_date=start_date,
            end_date=end_date,
            period_days=period_days,
        )
    except Exception as exc:
        logger.error("digest_report: context failed for org=%s: %s", org_id, exc)
        return None

    if not overview:
        logger.info("digest_report: no data for org=%s", org_id)
        return None

    kpis = overview.get("kpis", {})
    health = overview.get("health_score", {})
    alerts_summary = overview.get("alerts_summary", {})
    charts_data = overview.get("charts", {})
    categories = overview.get("categories", {})

    # Daily series from overview
    daily_series = charts_data.get("daily_series", [])
    sales_by_date = {}
    expenses_by_date = {}
    purchases_by_date = {}
    for point in daily_series:
        d = point.get("date", "")
        if d:
            sales_by_date[d] = point.get("sales", 0)
            expenses_by_date[d] = point.get("expenses", 0)
            purchases_by_date[d] = point.get("purchases", 0)

    # ── 3. Generate charts ───────────────────────────────────────────────
    try:
        chart_daily = generate_daily_chart(
            sales_by_date, expenses_by_date, purchases_by_date, locale,
        )
        chart_cumulative = generate_cumulative_chart(
            sales_by_date, expenses_by_date, purchases_by_date, locale,
        )

        top_sales_cats = categories.get("top_sales", [])
        top_expense_cats = categories.get("top_expenses", [])

        _labels = {
            "it": ("Top Ricavi", "Top Uscite"),
            "en": ("Top Revenue", "Top Expenses"),
            "de": ("Top Einnahmen", "Top Ausgaben"),
            "fr": ("Top Revenus", "Top Depenses"),
        }
        rev_title, exp_title = _labels.get(locale, _labels["it"])

        chart_rev_cats = generate_category_chart(
            top_sales_cats, rev_title, locale, color="#2563EB",
        ) if top_sales_cats else None

        chart_exp_cats = generate_category_chart(
            top_expense_cats, exp_title, locale, color="#DC2626",
        ) if top_expense_cats else None

        chart_health = generate_health_gauge(
            health.get("score", 0),
            health.get("label", ""),
            locale,
        )
    except Exception as exc:
        logger.error("digest_report: chart generation failed: %s", exc)
        chart_daily = chart_cumulative = chart_health = None
        chart_rev_cats = chart_exp_cats = None

    charts = {
        "daily": chart_daily,
        "cumulative": chart_cumulative,
        "categories_revenue": chart_rev_cats,
        "categories_expense": chart_exp_cats,
        "health": chart_health,
    }

    # ── 4. AI digest (Wave 12.B — unified single call) ────────────────────
    # Pre-Wave-12 this section made a SECOND Sonnet call via
    # _generate_ai_insights to produce a JSON {insights, recommendations}
    # specifically for the PDF. That was a different prompt from the
    # text digest, which led to inconsistent narratives between the
    # frontend digest and the PDF body.
    #
    # Wave 12.B unifies on ONE call (generate_digest_markdown) that
    # produces the full 7-section markdown. We then PARSE the markdown
    # into structured sections via parse_digest_sections. This eliminates
    # the second Sonnet call (~$0.02 saved per PDF generation) and
    # guarantees the PDF body says exactly what the frontend says.
    insights = None
    recommendations = None
    ai_sections = None
    model_version = "rule-based"
    ai_markdown = None

    if include_ai:
        try:
            from modules.cashflow_monitor.digest_builder import (
                generate_digest_markdown, parse_digest_sections,
            )
            ai_result = await generate_digest_markdown(
                overview=overview, digest_type=digest_type,
                period_days=period_days, locale=locale,
                org_id=org_id, user_id=user_id,
                agent_id="digest_report_builder",
            )
            if ai_result.get("ok"):
                ai_markdown = ai_result.get("content")
                model_version = ai_result.get("model_version") or "rule-based"
                # Parse the markdown into 7 sections — the PDF body uses
                # the parsed parts for backward-compat rendering.
                ai_sections = parse_digest_sections(ai_markdown)
                # Map parsed sections to the legacy insights/recommendations
                # parameters that build_report_pdf already accepts.
                # - "insights" := short bullets pulled from TL;DR + Performance
                # - "recommendations" := numbered actions from "Azioni Prioritarie"
                _insights_lines = []
                for src in (ai_sections.get("tldr", ""),
                             ai_sections.get("performance", "")):
                    if not src:
                        continue
                    # Pull bullet lines or first sentence
                    for line in src.split("\n"):
                        ls = line.strip()
                        if ls.startswith(("-", "*", "•")):
                            _insights_lines.append(ls.lstrip("-*• ").strip())
                        elif ls and not ls.startswith(">") and len(ls) < 200:
                            _insights_lines.append(ls)
                        if len(_insights_lines) >= 3:
                            break
                    if len(_insights_lines) >= 3:
                        break
                insights = _insights_lines[:3] if _insights_lines else None
                recommendations = ai_sections.get("actions") or None
        except Exception as exc:
            logger.warning("digest_report: AI digest generation failed: %s", exc)

    # ── 5. Get org name ──────────────────────────────────────────────────
    try:
        from repositories import organization_repository
        org = await organization_repository.find_by_id(org_id)
        org_name = org.get("name", "Organization") if org else "Organization"
    except Exception:
        org_name = "Organization"

    # ── 6. Build PDF ─────────────────────────────────────────────────────
    period_label = f"{start_date} — {end_date}"

    # Add previous period totals to kpis for trend calculation
    kpis_for_pdf = {**kpis}
    kpis_for_pdf["prev_total_sales"] = kpis.get("prev_total_sales", 0)
    kpis_for_pdf["prev_total_outflows"] = kpis.get("prev_total_outflows", 0)

    # Alerts list for PDF
    recent_alerts = alerts_summary.get("recent", [])

    try:
        pdf_bytes = build_report_pdf(
            org_name=org_name,
            period_label=period_label,
            digest_type=digest_type,
            kpis=kpis_for_pdf,
            health=health,
            charts=charts,
            alerts=recent_alerts,
            insights=insights,
            recommendations=recommendations,
            locale=locale,
            is_starter=not include_ai,
            overview=overview,
        )
    except Exception as exc:
        logger.error("digest_report: PDF generation failed: %s", exc)
        pdf_bytes = None

    # ── 7. Build text content (Wave 12.B redesign) ────────────────────────
    # Pre-Wave-12 the report path stored only a 4-line summary in `content`
    # (Score / Revenue / Outflows / Margin + sparse insights bullets).
    # This is what DigestTab.js renders for digests generated as PDF
    # reports — and is the ROOT CAUSE of the "4 numeri senza intelligenza"
    # experience the user reported even after the Sonnet revert.
    #
    # Post-Wave-12: when an AI digest was generated, the full 7-section
    # markdown is stored as `content` so the frontend renders the rich
    # narrative. Falls back to the legacy 4-line block when AI is
    # disabled / failed.
    if ai_markdown:
        content_lines = [ai_markdown]
    else:
        content_lines = [
            f"Health Score: {health.get('score', 0)}/100 ({health.get('label', '')})",
            f"Ricavi: {org_currency} {kpis.get('total_sales', 0):,.0f}",
            f"Uscite: {org_currency} {kpis.get('total_outflows', 0):,.0f}",
            f"Margine: {kpis.get('operating_margin_pct', 0):.1f}%",
        ]

    # ── 8. Build sections for frontend preview ───────────────────────────
    sections = {
        "snapshot": {
            "health_score": health.get("score", 0),
            "health_label": health.get("label", ""),
            "total_sales": kpis.get("total_sales", 0),
            "total_outflows": kpis.get("total_outflows", 0),
            "net_after_fixed": kpis.get("net_after_fixed", 0),
            "operating_margin_pct": kpis.get("operating_margin_pct", 0),
            "sales_trend_pct": kpis.get("sales_trend_pct", 0),
        },
        "alerts": [
            {"title": a.get("title", ""), "severity": a.get("severity", "low"),
             "action": a.get("suggested_action", "")}
            for a in recent_alerts[:5]
        ],
        "alerts_count": alerts_summary.get("open_count", 0),
        "insights": insights,
        "recommendations": recommendations,
    }

    return {
        "organization_id": org_id,
        "digest_type": digest_type,
        "content": "\n".join(content_lines),
        "period_start": start_date,
        "period_end": end_date,
        "kpis_summary": {
            "total_sales": kpis.get("total_sales", 0),
            "total_expenses": kpis.get("total_expenses", 0),
            "net_after_fixed": kpis.get("net_after_fixed", 0),
            "operating_margin_pct": kpis.get("operating_margin_pct", 0),
            "health_score": health.get("score", 0),
        },
        "alerts_count": alerts_summary.get("open_count", 0),
        "model_version": model_version,
        "format": "report",
        "has_pdf": pdf_bytes is not None,
        "pdf_bytes": pdf_bytes,
        "sections": sections,
    }




# Wave 12.B (2026-05) — _generate_ai_insights() was REMOVED.
#
# Pre-Wave-12 this function made a SECOND Sonnet call (different prompt
# than the text digest) to produce a JSON {insights, recommendations}
# block specifically for the PDF. That meant every PDF digest cost ~2x
# Anthropic and the PDF body could disagree with the frontend digest.
#
# Post-Wave-12, build_digest_report uses ONE call via
# digest_builder.generate_digest_markdown() and parses the resulting
# 7-section markdown into structured pieces via
# digest_builder.parse_digest_sections() — single source of truth
# shared with the text-only path.
