#!/usr/bin/env python3
"""Generate investor-ready PDF from the Cashflow Monitor methodology markdown."""

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, cm
from reportlab.lib.colors import HexColor, black, white, Color
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, KeepTogether, HRFlowable,
)
from reportlab.platypus.doctemplate import PageTemplate, BaseDocTemplate, Frame
from reportlab.lib.units import inch
import re
import os

# ── Colors ──────────────────────────────────────────────────────────────────
PRIMARY = HexColor("#1a1a2e")
ACCENT = HexColor("#0f3460")
LIGHT_BG = HexColor("#f8f9fa")
TABLE_HEADER_BG = HexColor("#1a1a2e")
TABLE_HEADER_FG = white
TABLE_ALT_ROW = HexColor("#f0f2f5")
BORDER_COLOR = HexColor("#dee2e6")
GREEN = HexColor("#22C55E")
YELLOW = HexColor("#EAB308")
ORANGE = HexColor("#F97316")
RED = HexColor("#EF4444")
MUTED = HexColor("#6c757d")

# ── Styles ──────────────────────────────────────────────────────────────────
styles = getSampleStyleSheet()

styles.add(ParagraphStyle(
    "DocTitle", parent=styles["Title"],
    fontSize=22, leading=28, textColor=PRIMARY,
    spaceAfter=6, alignment=TA_LEFT, fontName="Helvetica-Bold",
))
styles.add(ParagraphStyle(
    "DocSubtitle", parent=styles["Normal"],
    fontSize=10, leading=14, textColor=MUTED,
    spaceAfter=4, fontName="Helvetica",
))
styles.add(ParagraphStyle(
    "H1", parent=styles["Heading1"],
    fontSize=16, leading=22, textColor=PRIMARY,
    spaceBefore=24, spaceAfter=10, fontName="Helvetica-Bold",
))
styles.add(ParagraphStyle(
    "H2", parent=styles["Heading2"],
    fontSize=13, leading=18, textColor=ACCENT,
    spaceBefore=18, spaceAfter=8, fontName="Helvetica-Bold",
))
styles.add(ParagraphStyle(
    "H3", parent=styles["Heading3"],
    fontSize=11, leading=15, textColor=PRIMARY,
    spaceBefore=12, spaceAfter=6, fontName="Helvetica-Bold",
))
styles.add(ParagraphStyle(
    "Body", parent=styles["Normal"],
    fontSize=9.5, leading=14, textColor=black,
    spaceAfter=6, alignment=TA_JUSTIFY, fontName="Helvetica",
))
styles.add(ParagraphStyle(
    "BodyBold", parent=styles["Normal"],
    fontSize=9.5, leading=14, textColor=black,
    spaceAfter=6, fontName="Helvetica-Bold",
))
styles.add(ParagraphStyle(
    "BulletItem", parent=styles["Normal"],
    fontSize=9.5, leading=14, textColor=black,
    leftIndent=18, bulletIndent=6, spaceAfter=3,
    fontName="Helvetica",
))
styles.add(ParagraphStyle(
    "Note", parent=styles["Normal"],
    fontSize=8.5, leading=12, textColor=MUTED,
    leftIndent=12, spaceAfter=6, fontName="Helvetica-Oblique",
))
styles.add(ParagraphStyle(
    "TableCell", parent=styles["Normal"],
    fontSize=8, leading=11, fontName="Helvetica",
))
styles.add(ParagraphStyle(
    "TableCellBold", parent=styles["Normal"],
    fontSize=8, leading=11, fontName="Helvetica-Bold",
))
styles.add(ParagraphStyle(
    "TableHeader", parent=styles["Normal"],
    fontSize=8, leading=11, fontName="Helvetica-Bold", textColor=white,
))
styles.add(ParagraphStyle(
    "Footer", parent=styles["Normal"],
    fontSize=7, leading=10, textColor=MUTED, alignment=TA_CENTER,
    fontName="Helvetica",
))
styles.add(ParagraphStyle(
    "CodeBlock", parent=styles["Normal"],
    fontSize=8, leading=11, fontName="Courier",
    leftIndent=12, spaceAfter=8, backColor=LIGHT_BG,
))


def make_table(headers, rows, col_widths=None):
    """Create a styled table."""
    header_row = [Paragraph(h, styles["TableHeader"]) for h in headers]
    data = [header_row]
    for row in rows:
        data.append([Paragraph(str(c), styles["TableCell"]) for c in row])

    if col_widths is None:
        col_widths = [None] * len(headers)

    t = Table(data, colWidths=col_widths, repeatRows=1)
    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), TABLE_HEADER_BG),
        ("TEXTCOLOR", (0, 0), (-1, 0), TABLE_HEADER_FG),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]
    # Alternate row colors
    for i in range(1, len(data)):
        if i % 2 == 0:
            style_cmds.append(("BACKGROUND", (0, i), (-1, i), TABLE_ALT_ROW))

    t.setStyle(TableStyle(style_cmds))
    return t


def make_kv_table(rows, key_width=120, val_width=360):
    """Key-value attribute table."""
    data = []
    for k, v in rows:
        data.append([
            Paragraph(f"<b>{k}</b>", styles["TableCell"]),
            Paragraph(str(v), styles["TableCell"]),
        ])
    t = Table(data, colWidths=[key_width, val_width])
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("BACKGROUND", (0, 0), (0, -1), LIGHT_BG),
    ]))
    return t


def add_header_footer(canvas, doc):
    """Page header and footer."""
    canvas.saveState()
    # Header line
    canvas.setStrokeColor(PRIMARY)
    canvas.setLineWidth(0.5)
    canvas.line(2*cm, A4[1] - 1.5*cm, A4[0] - 2*cm, A4[1] - 1.5*cm)
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(MUTED)
    canvas.drawString(2*cm, A4[1] - 1.3*cm, "AFianco - Cashflow Monitor Methodology v1.0")
    canvas.drawRightString(A4[0] - 2*cm, A4[1] - 1.3*cm, "CONFIDENTIAL - Draft for Review")

    # Footer
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(MUTED)
    canvas.line(2*cm, 1.5*cm, A4[0] - 2*cm, 1.5*cm)
    canvas.drawString(2*cm, 1*cm, "AFianco S.r.l. - Proprietary & Confidential")
    canvas.drawRightString(A4[0] - 2*cm, 1*cm, f"Page {doc.page}")
    canvas.restoreState()


def build_pdf(output_path):
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        topMargin=2*cm,
        bottomMargin=2*cm,
        leftMargin=2*cm,
        rightMargin=2*cm,
    )

    story = []
    W = A4[0] - 4*cm  # available width

    # ── COVER / TITLE ───────────────────────────────────────────────────────
    story.append(Spacer(1, 2*cm))
    story.append(Paragraph("Cashflow Monitor", styles["DocTitle"]))
    story.append(Paragraph("Product Methodology &amp; Specification", ParagraphStyle(
        "SubMain", parent=styles["DocTitle"], fontSize=16, leading=22,
        textColor=ACCENT, spaceAfter=16,
    )))
    story.append(HRFlowable(width="100%", thickness=1, color=PRIMARY, spaceAfter=12))

    meta_data = [
        ["Document Version", "v1.0"],
        ["Status", "Draft for Review"],
        ["Date", "March 2026"],
        ["Author", "AFianco Product &amp; Engineering"],
        ["Classification", "Internal / Investor-Ready"],
    ]
    meta_table = Table(meta_data, colWidths=[100, 200])
    meta_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (0, -1), MUTED),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 1.5*cm))

    # ── TABLE OF CONTENTS ───────────────────────────────────────────────────
    story.append(Paragraph("Table of Contents", styles["H1"]))
    toc_items = [
        "1. Executive Summary",
        "2. Intended Audience",
        "3. Use Cases",
        "4. Purpose of the Cashflow Report",
        "5. Scope of the Module",
        "6. Data Inputs and Source Variables",
        "7. Derived KPI Definitions",
        "8. KPI Cards Overview",
        "9. Financial Health Score Methodology",
        "10. Scored Dimensions - Detail",
        "11. Diagnostic Metrics",
        "12. Rules for Missing Data / Not-Computable Logic",
        "13. Proxy Metrics and Interpretation Caveats",
        "14. AI Layer on Top of the Financial Engine",
        "15. Example Interpretation Logic",
        "16. Limitations",
        "17. Glossary",
        "18. Governance / Revision Notes",
    ]
    for item in toc_items:
        story.append(Paragraph(item, styles["Body"]))
    story.append(PageBreak())

    # ── 1. EXECUTIVE SUMMARY ────────────────────────────────────────────────
    story.append(Paragraph("1. Executive Summary", styles["H1"]))
    story.append(Paragraph(
        "AFianco's <b>Cashflow Monitor</b> is a real-time financial reporting module designed for Italian small "
        "and medium enterprises (SMEs). It transforms raw transactional data - sales, operating expenses, "
        "supplier purchases, and fixed costs - into a structured set of KPIs, a composite Financial Health "
        "Score, diagnostic indicators, and AI-generated explanations.",
        styles["Body"]
    ))
    story.append(Paragraph("The module serves three core purposes:", styles["Body"]))
    story.append(Paragraph(
        "<b>1. Operational visibility.</b> Business owners see daily inflows/outflows, net result, cost structure, and burn rate at a glance.",
        styles["BulletItem"]
    ))
    story.append(Paragraph(
        "<b>2. Financial health assessment.</b> A composite score (0-100) across five distinct financial dimensions summarizes business health with clear thresholds.",
        styles["BulletItem"]
    ))
    story.append(Paragraph(
        "<b>3. Actionable guidance.</b> AI-powered explanations translate numeric scores into plain-language assessments, identify priorities, and surface data quality warnings.",
        styles["BulletItem"]
    ))
    story.append(Spacer(1, 8))
    story.append(Paragraph("<b>Key design principles:</b>", styles["Body"]))
    for principle in [
        "<b>No false-good scores.</b> Missing data dimensions are excluded rather than defaulted to misleadingly favorable values.",
        "<b>Scored vs. diagnostic separation.</b> Only five dimensions drive the score; all others are context-only.",
        "<b>Proxy metrics are labeled.</b> Any approximation (e.g., operational coverage) is explicitly marked and caveated.",
        "<b>AI is bounded by data.</b> The AI reads structured outputs and does not invent financial facts.",
    ]:
        story.append(Paragraph(principle, styles["BulletItem"]))

    # ── 2. INTENDED AUDIENCE ────────────────────────────────────────────────
    story.append(Paragraph("2. Intended Audience", styles["H1"]))
    story.append(make_table(
        ["Audience", "What they should get from this document"],
        [
            ["Product managers", "Complete specification for feature governance, roadmap planning, and QA validation"],
            ["Engineers", "Exact formulas, thresholds, and edge cases for implementation parity"],
            ["Investors / Board", "Methodology credibility, intellectual property clarity, and product maturity signal"],
            ["Compliance / Legal", "Disclaimer boundaries, proxy metric labeling, and AI limitation disclosures"],
            ["Customer Success", "Understanding of what each metric means for end-user support"],
        ],
        col_widths=[100, W - 100],
    ))

    # ── 3. USE CASES ────────────────────────────────────────────────────────
    story.append(Paragraph("3. Use Cases", styles["H1"]))
    story.append(make_table(
        ["#", "Use Case", "Actor", "Feature"],
        [
            ["UC-1", "Monitor daily revenue vs. expenses", "Business owner", "KPI cards, daily chart"],
            ["UC-2", "Understand profitability after all costs", "Business owner", "Net Result, Health Score"],
            ["UC-3", "Check break-even coverage", "Business owner", "Break-Even card, Structural Strength"],
            ["UC-4", "Identify cash cycle inefficiencies", "Finance mgr.", "DSO, DPO, Cash Cycle dimension"],
            ["UC-5", "Quick health summary for board", "CEO / Owner", "Health Score gauge, AI explanation"],
            ["UC-6", "Detect anomalies early", "Business owner", "Alert rules, Revenue Dynamics"],
            ["UC-7", "Estimate operational runway", "Business owner", "Operational Coverage (proxy)"],
            ["UC-8", "Assess data completeness", "Any user", "Confidence, data caveats"],
        ],
        col_widths=[30, 160, 80, W - 270],
    ))

    # ── 4. PURPOSE ──────────────────────────────────────────────────────────
    story.append(Paragraph("4. Purpose of the Cashflow Report", styles["H1"]))
    story.append(Paragraph(
        "The Cashflow Report provides a structured, automated financial overview that translates raw "
        "transaction data into business-relevant metrics. It is not a replacement for professional accounting "
        "or CFO-level analysis. It is a <b>directional tool</b> that helps business owners understand where "
        "money is going, identify early warning signs, track trends over time, and communicate financial "
        "posture to stakeholders.",
        styles["Body"]
    ))
    story.append(Paragraph(
        "The module distinguishes between <b>facts</b> (recorded transactions), <b>derived metrics</b> "
        "(calculated from facts), and <b>proxies</b> (approximations where direct data is unavailable).",
        styles["Body"]
    ))

    # ── 5. SCOPE ────────────────────────────────────────────────────────────
    story.append(Paragraph("5. Scope of the Module", styles["H1"]))
    story.append(Paragraph("<b>Included:</b> Revenue/expense tracking (daily), four-bucket cost model, profitability KPIs, "
        "cash cycle KPIs, operational KPIs, composite health score (0-100), PoP/YoY comparisons, "
        "AI explanations, alert rules, payment aging and 60-day forecast.", styles["Body"]))
    story.append(Paragraph("<b>Not included:</b> Bank account balance integration, tax/VAT filing, inventory/COGS, "
        "multi-currency consolidation, intercompany reconciliation, payroll processing.", styles["Body"]))

    # ── 6. DATA INPUTS ──────────────────────────────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph("6. Data Inputs and Source Variables", styles["H1"]))

    story.append(Paragraph("6.1 Raw Financial Inputs", styles["H2"]))
    story.append(make_table(
        ["Input Category", "Key Fields", "Source"],
        [
            ["Sales (Revenue)", "date, amount, category, due_date, payment_status", "CSV/XLSX or manual"],
            ["Operating Expenses", "date, amount, category", "CSV/XLSX or manual"],
            ["Supplier Purchases", "date, quantity, unit_price, total_price, iva, total_with_iva, supplier, due_date, payment_status", "CSV/XLSX or manual"],
            ["Fixed Costs", "name, category, amount, frequency, start_date, end_date", "Manual entry"],
        ],
        col_widths=[95, W - 190, 95],
    ))

    story.append(Paragraph("6.2 Derived Aggregates", styles["H2"]))
    story.append(make_table(
        ["Variable", "Definition"],
        [
            ["total_sales", "Sum of all sales amounts in the selected period"],
            ["total_expenses", "Sum of all operating expense amounts in the selected period"],
            ["supplier_purchases", "Sum of purchase totals (coalesces total_with_iva, amount, total_price)"],
            ["fixed_costs_total", "Sum of active fixed costs, prorated to period based on frequency"],
            ["variable_outflows", "total_expenses + supplier_purchases"],
            ["total_outflows", "variable_outflows + fixed_costs_total"],
            ["net_after_fixed", "total_sales - total_outflows"],
            ["open_receivables", "Sum of unpaid sales with due_date set"],
            ["open_payables", "Sum of unpaid purchases with due_date set"],
            ["period_days", "(end_date - start_date).days + 1 (calendar days, inclusive)"],
        ],
        col_widths=[110, W - 110],
    ))

    # ── 7. DERIVED KPI DEFINITIONS ──────────────────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph("7. Derived KPI Definitions", styles["H1"]))
    story.append(Paragraph(
        "All computations use a <b>canonical formula layer</b> (kpi_formulas.py) ensuring identical results "
        "across the overview, insights, and alert systems.", styles["Body"]
    ))

    # 7.1 Profitability
    story.append(Paragraph("7.1 Profitability KPIs", styles["H2"]))

    for kpi_name, rows in [
        ("Net Margin %", [
            ("Purpose", "Measures percentage of revenue remaining as profit after all costs"),
            ("Formula", "(net_after_fixed / total_sales) x 100"),
            ("Unit", "Percentage (1 decimal)"),
            ("Returns None", "total_sales <= 0"),
            ("Interpretation", "> 15% excellent; 5-15% adequate; < 0% loss"),
            ("Caveat", "If fixed costs not uploaded, margin is artificially inflated"),
        ]),
        ("Cost-to-Revenue Ratio", [
            ("Purpose", "Shows how much of every euro of revenue is consumed by costs"),
            ("Formula", "(total_outflows / total_sales) x 100"),
            ("Unit", "Percentage (1 decimal)"),
            ("Returns None", "total_sales <= 0"),
            ("Interpretation", "< 80% healthy; > 100% spending more than earning"),
            ("Note", "Diagnostic only - not scored"),
        ]),
    ]:
        story.append(Paragraph(f"<b>{kpi_name}</b>", styles["H3"]))
        story.append(make_kv_table(rows))
        story.append(Spacer(1, 6))

    # 7.2 Break-Even
    story.append(Paragraph("7.2 Break-Even KPIs", styles["H2"]))
    for kpi_name, rows in [
        ("Break-Even Point", [
            ("Purpose", "Minimum revenue needed to cover all costs"),
            ("Formula", "fixed_costs_total / (1 - variable_cost_ratio)"),
            ("Unit", "EUR (2 decimals)"),
            ("Returns None", "VCR is None, OR fixed_costs <= 0, OR VCR >= 1.0"),
            ("Caveat", "When VCR >= 1.0, break-even is structurally unreachable"),
        ]),
        ("Break-Even Headroom %", [
            ("Purpose", "How far above/below break-even the current revenue sits"),
            ("Formula", "((total_sales - break_even) / break_even) x 100"),
            ("Unit", "Percentage (1 decimal)"),
            ("Interpretation", "Positive = safe; Negative = deficit"),
        ]),
        ("Fixed Cost Ratio", [
            ("Purpose", "Weight of fixed costs relative to revenue"),
            ("Formula", "(fixed_costs_total / total_sales) x 100"),
            ("Interpretation", "< 15% lean; 15-30% moderate; > 30% heavy"),
        ]),
    ]:
        story.append(Paragraph(f"<b>{kpi_name}</b>", styles["H3"]))
        story.append(make_kv_table(rows))
        story.append(Spacer(1, 6))

    # 7.3 Cash Flow Timing
    story.append(Paragraph("7.3 Cash Flow Timing KPIs", styles["H2"]))
    for kpi_name, rows in [
        ("DSO (Days Sales Outstanding)", [
            ("Formula", "(open_receivables / total_sales) x period_days"),
            ("Unit", "Days (1 decimal)"),
            ("Returns None", "total_sales <= 0 OR period_days <= 0"),
            ("Caveat", "Estimated. Accuracy improves with due dates and payment status"),
        ]),
        ("DPO (Days Payable Outstanding)", [
            ("Formula", "(open_payables / supplier_purchases) x period_days"),
            ("Unit", "Days (1 decimal)"),
            ("Returns None", "supplier_purchases <= 0 OR period_days <= 0"),
            ("Caveat", "Estimated. Accuracy improves with due dates and payment status"),
        ]),
        ("Cash Conversion Gap", [
            ("Formula", "DSO - DPO"),
            ("Interpretation", "Negative = favorable (cash in before costs due); Positive = gap to finance"),
            ("Returns None", "Both DSO and DPO are None"),
            ("Fallback", "When only one computable, missing value treated as 0"),
        ]),
    ]:
        story.append(Paragraph(f"<b>{kpi_name}</b>", styles["H3"]))
        story.append(make_kv_table(rows))
        story.append(Spacer(1, 6))

    # 7.4 Operational
    story.append(Paragraph("7.4 Operational KPIs", styles["H2"]))
    for kpi_name, rows in [
        ("Burn Rate (Daily)", [
            ("Formula", "total_outflows / period_days"),
            ("Unit", "EUR/day (2 decimals)"),
            ("Interpretation", "Higher burn rate = faster cash consumption"),
        ]),
        ("Operational Coverage (PROXY)", [
            ("Formula", "net_after_fixed / (total_outflows / period_days)"),
            ("Unit", "Days (1 decimal)"),
            ("WARNING", "This is NOT real liquidity. No bank balance data is used."),
            ("UI Label", 'Always displayed as "Operational Coverage ~ estimated"'),
            ("In Health Score", "Diagnostic only - does NOT drive any scored dimension"),
        ]),
    ]:
        story.append(Paragraph(f"<b>{kpi_name}</b>", styles["H3"]))
        story.append(make_kv_table(rows))
        story.append(Spacer(1, 6))

    # ── 8. KPI CARDS OVERVIEW ───────────────────────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph("8. KPI Cards Overview", styles["H1"]))

    story.append(Paragraph("Detail Tab - Row 1 (Core Operational)", styles["H2"]))
    story.append(make_table(
        ["Pos", "Card", "Value Source", "Trend", "Color Logic"],
        [
            ["1", "Total Revenue", "total_sales", "PoP %", "Green"],
            ["2", "Operating Expenses", "total_expenses", "PoP % (inv.)", "Red"],
            ["3", "Supplier Purchases", "supplier_purchases", "-", "Red"],
            ["4", "Fixed Costs", "fixed_costs_total", "-", "Default"],
            ["5", "Net Result", "net_after_fixed", "-", "Green >= 0; Red < 0"],
            ["6", "Burn Rate", "burn_rate_total", "-", "Default"],
        ],
        col_widths=[25, 100, 105, 70, W - 300],
    ))

    story.append(Paragraph("Detail Tab - Row 2 (Structural + Diagnostic)", styles["H2"]))
    story.append(make_table(
        ["Pos", "Card", "Color Logic", "Styling"],
        [
            ["1", "Break-Even", "Green if sales > BE; Red if < BE", "Standard"],
            ["2", "Operational Coverage ~ est.", "Red < 30d; Green >= 60d", "Standard + proxy badge"],
            ["3", "Fixed Cost Ratio", "Red > 30%; Green <= 30%", "Standard"],
            ["4", "Operating Margin %", "-", "DIAGNOSTIC (muted, 75% opacity)"],
            ["5", "Outflow Ratio", "-", "DIAGNOSTIC (muted, 75% opacity)"],
        ],
        col_widths=[25, 130, 160, W - 315],
    ))
    story.append(Paragraph(
        "Cards 4 and 5 use diagnostic styling: reduced opacity, muted border, no success/danger coloring. "
        "This visually communicates they are supplementary context, not primary decision metrics.",
        styles["Note"]
    ))

    # ── 9. HEALTH SCORE METHODOLOGY ─────────────────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph("9. Financial Health Score Methodology", styles["H1"]))

    story.append(Paragraph(
        "The Financial Health Score is a composite indicator from <b>0 to 100</b> that summarizes business "
        "health across five financially distinct dimensions. It is designed as a <b>directional signal</b>, "
        "not a precise diagnosis.", styles["Body"]
    ))

    story.append(Paragraph("9.1 Design Principles", styles["H2"]))
    for p in [
        "<b>No redundancy.</b> Each dimension measures a distinct financial concept. Previous v2.x had 8 dimensions with ~90% correlation between 3 pairs.",
        "<b>Not-computable > false-good.</b> Insufficient data excludes the dimension; weight is redistributed.",
        "<b>Scored vs. diagnostic.</b> Only five dimensions drive the score; all others are context-only.",
        "<b>Confidence transparency.</b> A value (0.0-1.0) indicates what fraction of weight was computable.",
    ]:
        story.append(Paragraph(p, styles["BulletItem"]))

    story.append(Paragraph("9.2 Dimension Weights", styles["H2"]))
    story.append(make_table(
        ["#", "Dimension", "Key", "Weight", "What It Measures"],
        [
            ["1", "Net Margin", "net_margin", "25 pt", "Net profitability after all costs"],
            ["2", "Revenue Dynamics", "revenue_dynamics", "20 pt", "Revenue and margin trajectory"],
            ["3", "Structural Strength", "structural_strength", "20 pt", "Break-even distance + fixed cost leverage"],
            ["4", "Cash Cycle", "cash_cycle", "25 pt", "Cash conversion timing (DSO - DPO)"],
            ["5", "Operational Risk", "operational_risk", "10 pt", "Alert signals + data completeness"],
            ["", "", "", "100 pt", "Total"],
        ],
        col_widths=[20, 100, 110, 45, W - 275],
    ))

    story.append(Paragraph("9.3 Score Bands", styles["H2"]))
    story.append(make_table(
        ["Score Range", "Label", "Color", "Meaning"],
        [
            ["80-100", "Excellent", "Green (#22C55E)", "Strong financial position across most dimensions"],
            ["60-79", "Good", "Yellow (#EAB308)", "Generally healthy with areas to monitor"],
            ["40-59", "Attention", "Orange (#F97316)", "One or more dimensions require action"],
            ["0-39", "Critical", "Red (#EF4444)", "Significant financial stress detected"],
        ],
    ))

    story.append(Paragraph("9.4 Weight Rescaling", styles["H2"]))
    story.append(Paragraph(
        "When dimensions are disabled or not computable, remaining weights are <b>proportionally rescaled</b> "
        "to maintain a 0-100 scale.", styles["Body"]
    ))
    story.append(Paragraph(
        "rescaled_max = (original_weight / computable_weight_sum) x 100<br/>"
        "rescaled_points = (original_points / original_max) x rescaled_max<br/>"
        "confidence = computable_weight / 100",
        styles["CodeBlock"]
    ))

    # ── 10. SCORED DIMENSIONS ───────────────────────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph("10. Scored Dimensions - Detail", styles["H1"]))

    # 10.1 Net Margin
    story.append(Paragraph("10.1 Net Margin (25 pt)", styles["H2"]))
    story.append(Paragraph("Formula: margin_pct = (net_after_fixed / total_sales) x 100. Not computable when total_sales <= 0.", styles["Body"]))
    story.append(make_table(
        ["Net Margin %", "Points (of 25)", "Assessment"],
        [
            ["> 15%", "25", "Excellent profitability"],
            ["> 10%", "21", "Strong"],
            ["> 5%", "16", "Adequate"],
            ["> 0%", "10", "Marginal"],
            ["= 0%", "5", "Break-even"],
            ["< 0%", "0", "Loss"],
        ],
    ))

    # 10.2 Revenue Dynamics
    story.append(Paragraph("10.2 Revenue Dynamics (20 pt)", styles["H2"]))
    story.append(Paragraph("Composite: Sub-A (Sales Trend, 10 pt) + Sub-B (Margin Trend, 10 pt). If only one computable, it is rescaled to 20 pt.", styles["Body"]))
    story.append(make_table(
        ["Sales Trend", "Points", "", "Margin Trend (pp)", "Points"],
        [
            ["> +10%", "10", "", "> +2 pp", "10"],
            ["> 0%", "7", "", "> -2 pp", "7"],
            ["> -10%", "4", "", "> -5 pp", "4"],
            ["> -20%", "2", "", "<= -5 pp", "0"],
            ["<= -20%", "0", "", "", ""],
        ],
    ))

    # 10.3 Structural Strength
    story.append(Paragraph("10.3 Structural Strength (20 pt)", styles["H2"]))
    story.append(Paragraph("Composite: Sub-A (Break-Even Headroom, 10 pt) + Sub-B (Fixed Cost Ratio, 10 pt). Same rescaling logic.", styles["Body"]))
    story.append(make_table(
        ["Headroom %", "Points", "", "FC Ratio", "Points"],
        [
            ["> 30%", "10", "", "< 15%", "10"],
            ["> 15%", "7", "", "< 25%", "7"],
            ["> 0%", "4", "", "< 35%", "4"],
            ["<= 0%", "0", "", "< 50%", "2"],
            ["", "", "", ">= 50%", "0"],
        ],
    ))

    # 10.4 Cash Cycle
    story.append(Paragraph("10.4 Cash Cycle (25 pt)", styles["H2"]))
    story.append(Paragraph("Based on Cash Conversion Gap (DSO - DPO). Not computable when has_payment_status_data = false.", styles["Body"]))
    story.append(make_table(
        ["Cash Conversion Gap (days)", "Points (of 25)", "Assessment"],
        [
            ["<= 0", "25", "Cash arrives before costs are due"],
            ["< 15", "19", "Short gap - manageable"],
            ["< 30", "13", "Moderate gap"],
            ["< 60", "6", "Significant gap - working capital pressure"],
            [">= 60", "0", "Severe gap - financing likely needed"],
        ],
    ))

    # 10.5 Operational Risk
    story.append(Paragraph("10.5 Operational Risk (10 pt)", styles["H2"]))
    story.append(Paragraph("Always computable. Sub-A: High alerts (5 pt). Sub-B: Data sources (5 pt).", styles["Body"]))
    story.append(make_table(
        ["High Alerts", "Points", "", "Data Sources", "Points"],
        [
            ["0", "5", "", ">= 4", "5"],
            ["1-2", "2", "", ">= 3", "3"],
            ["> 2", "0", "", ">= 2", "1"],
            ["", "", "", "< 2", "0"],
        ],
    ))

    # ── 11. DIAGNOSTIC METRICS ──────────────────────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph("11. Diagnostic Metrics", styles["H1"]))
    story.append(Paragraph(
        "The following metrics are computed and displayed for context but are <b>not scored</b> - "
        "they do not affect the composite health score.", styles["Body"]
    ))
    story.append(make_table(
        ["Metric", "Formula", "Unit", "Purpose"],
        [
            ["Cost-to-Revenue Ratio", "(total_outflows / total_sales) x 100", "%", "Overall cost pressure"],
            ["Operating Margin %", "((sales - variable_outflows) / sales) x 100", "%", "Profitability before fixed costs"],
            ["Burn Rate (Daily)", "total_outflows / period_days", "EUR/day", "Cash consumption speed"],
            ["Operational Coverage", "net_after_fixed / (total_outflows / period_days)", "Days", "PROXY: margin-to-burn-rate coverage"],
            ["DSO", "(open_receivables / total_sales) x period_days", "Days", "Individual collection timing"],
            ["DPO", "(open_payables / supplier_purchases) x period_days", "Days", "Individual payment timing"],
        ],
        col_widths=[100, 170, 50, W - 320],
    ))
    story.append(Paragraph(
        "Why diagnostic, not scored? These metrics either overlap with scored dimensions (~90% correlated) "
        "or are individual components of a scored composite. Scoring them independently would create "
        "redundancy and double-counting.",
        styles["Note"]
    ))

    # ── 12. NOT-COMPUTABLE LOGIC ────────────────────────────────────────────
    story.append(Paragraph("12. Rules for Missing Data / Not-Computable Logic", styles["H1"]))
    story.append(Paragraph(
        "When a dimension lacks sufficient data, it is marked as <b>not_computable</b> rather than defaulted "
        "to zero. This prevents artificially favorable (or unfavorable) scores.", styles["Body"]
    ))
    story.append(make_table(
        ["Dimension", "Trigger", "Reason Displayed"],
        [
            ["Net Margin", "total_sales <= 0", "No revenue data"],
            ["Revenue Dynamics", "Both trends are None", "No previous period data"],
            ["Structural Strength", "Both sub-scores fail", "Insufficient data (no fixed costs or revenue)"],
            ["Cash Cycle", "No payment status data or gap = None", "No payment status data available"],
            ["Operational Risk", "Never - always computable", "-"],
        ],
    ))

    story.append(Paragraph("Sparse-Data False-Good Safeguard", styles["H2"]))
    story.append(Paragraph(
        "A special guard triggers when only <b>1 data source</b> is uploaded AND net margin exceeds <b>50%</b> "
        "(artificially inflated because no costs are recorded). The system appends a prominent warning in both "
        "the structured caveats and the explanation text.", styles["Body"]
    ))

    # ── 13. PROXY METRICS ───────────────────────────────────────────────────
    story.append(Paragraph("13. Proxy Metrics and Interpretation Caveats", styles["H1"]))
    story.append(Paragraph("Operational Coverage - Detailed Caveat", styles["H2"]))
    story.append(make_kv_table([
        ("Approximates", "How long the business can sustain operations"),
        ("Actually measures", "Ratio of net margin to daily burn rate"),
        ("Does NOT include", "Bank balance, credit lines, receivable collection, payable schedules"),
        ("Why misleading", "Business with EUR 50k profit and EUR 5k/day burn shows 10 days but may have EUR 200k in bank"),
        ("UI Label", '"Operational Coverage ~ estimated"'),
        ("In Health Score", "Diagnostic only - does NOT drive any scored dimension"),
        ("AI Handling", 'Must qualify with "approximately" or "estimated from burn rate"'),
    ]))

    # ── 14. AI LAYER ────────────────────────────────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph("14. AI Layer on Top of the Financial Engine", styles["H1"]))

    story.append(Paragraph("14.1 Architecture", styles["H2"]))
    story.append(Paragraph(
        "Two modes: (1) <b>Rule-based explanation</b> (default, zero API cost, every page load) and "
        "(2) <b>AI-powered explanation</b> (on-demand via Claude API). Both read the same structured outputs. "
        "Neither invents financial facts.", styles["Body"]
    ))

    story.append(Paragraph("14.2 What the AI Can Answer", styles["H2"]))
    story.append(make_table(
        ["Domain", "Capability"],
        [
            ["Profitability", "Explain whether the business is profitable, by how much, and trend direction"],
            ["Cost pressure", "Identify which cost bucket is heaviest relative to revenue"],
            ["Break-even", "Explain distance above or below break-even threshold"],
            ["Trends", "Describe revenue and margin trajectory period-over-period"],
            ["Cash cycle", "Explain gap between collection and payment timing"],
            ["Data completeness", "Warn when score is based on limited data; suggest uploads"],
            ["Priority actions", "Suggest most impactful improvement areas from weakest dimensions"],
            ["Proxy qualification", "Clarify when a metric is an estimate, not a measured fact"],
        ],
        col_widths=[100, W - 100],
    ))

    story.append(Paragraph("14.3 What the AI Cannot Reliably Infer", styles["H2"]))
    story.append(make_table(
        ["Limitation", "Reason"],
        [
            ["Actual bank balance", "No bank account data is ingested"],
            ["Tax obligations", "Tax computation is out of scope"],
            ["Future projections", "Forecasting requires assumptions the system does not make"],
            ["Industry benchmarks", "No sector-specific comparison norms"],
            ["Root cause analysis", "Can identify WHAT is weak but not WHY"],
            ["Accounting accuracy", "Reflects uploaded data quality"],
            ["Investment advice", "Not a financial advisor"],
        ],
        col_widths=[120, W - 120],
    ))

    story.append(Paragraph("14.4 AI Guardrails", styles["H2"]))
    for g in [
        "Temperature: <b>0.2</b> (conservative, deterministic output)",
        "Maximum output: <b>200 tokens</b>",
        "Fallback: if Claude API unavailable, <b>always falls back</b> to rule-based explanation",
        "System prompt explicitly instructs to never overstate proxy metrics",
    ]:
        story.append(Paragraph(g, styles["BulletItem"]))

    # ── 15. EXAMPLE ─────────────────────────────────────────────────────────
    story.append(Paragraph("15. Example Interpretation Logic", styles["H1"]))
    story.append(Paragraph("<b>Scenario: Growing E-commerce with Cash Cycle Pressure</b>", styles["Body"]))
    story.append(Paragraph(
        "Revenue EUR 200k, Margin 20%, Sales Trend +25%, Margin Trend +3pp, Fixed Costs EUR 20k, "
        "DSO 55 days, DPO 10 days, 0 high alerts, 4 data sources.", styles["Body"]
    ))
    story.append(make_table(
        ["Dimension", "Points", "Assessment"],
        [
            ["Net Margin (25)", "25/25", "20% margin - excellent"],
            ["Revenue Dynamics (20)", "20/20", "Strong growth in both sales and margin"],
            ["Structural Strength (20)", "20/20", "High headroom, moderate fixed costs"],
            ["Cash Cycle (25)", "6/25", "45-day gap - significant WC pressure"],
            ["Operational Risk (10)", "10/10", "No alerts, complete data"],
        ],
    ))
    story.append(Paragraph(
        "<b>Score: ~81 (Excellent), Confidence: 1.0.</b> Strongest: Net Margin, Dynamics, Structure. "
        "Weakest: Cash Cycle (24% - high-priority issue). Priority Action: Accelerate collections or "
        "negotiate longer payment terms.", styles["Body"]
    ))

    # ── 16. LIMITATIONS ─────────────────────────────────────────────────────
    story.append(Paragraph("16. Limitations", styles["H1"]))
    for lim in [
        "<b>Not a bank statement.</b> Operates on uploaded data, not real-time bank feeds.",
        "<b>Garbage in, garbage out.</b> Incomplete/incorrect uploads produce inaccurate KPIs.",
        "<b>No inventory or COGS.</b> Manufacturing/retail should interpret margins accordingly.",
        "<b>Fixed-period comparisons.</b> Seasonal businesses may see misleading trends.",
        "<b>Sector-agnostic thresholds.</b> May be too generous or strict for specific industries.",
        "<b>Not a substitute for professional advice.</b> Consult accountants/CFOs for material decisions.",
    ]:
        story.append(Paragraph(lim, styles["BulletItem"]))

    # ── 17. GLOSSARY ────────────────────────────────────────────────────────
    story.append(Paragraph("17. Glossary", styles["H1"]))
    story.append(make_table(
        ["Term", "Definition"],
        [
            ["Break-Even Point", "Revenue level where total costs equal total revenue"],
            ["Burn Rate", "Average daily total outflows"],
            ["Cash Conversion Gap", "DSO minus DPO; days between paying suppliers and collecting from customers"],
            ["Confidence", "Fraction of total health score weight that was computable (0.0-1.0)"],
            ["Diagnostic Metric", "Metric displayed for context, not included in health score"],
            ["DPO", "Days Payable Outstanding - average days to pay suppliers"],
            ["DSO", "Days Sales Outstanding - average days to collect from customers"],
            ["Net Margin", "Net profit after all costs, as percentage of revenue"],
            ["Not Computable", "Dimension excluded from score due to insufficient data"],
            ["Operational Coverage", "PROXY metric: margin-to-burn-rate coverage in days"],
            ["Period Days", "Calendar days in selected period, inclusive"],
            ["Proxy Metric", "Approximation for a concept without direct data"],
            ["Rescaling", "Redistribution of weight from not-computable dimensions"],
            ["VCR", "Variable Cost Ratio - variable outflows / revenue"],
        ],
        col_widths=[120, W - 120],
    ))

    # ── 18. GOVERNANCE ──────────────────────────────────────────────────────
    story.append(Paragraph("18. Governance / Revision Notes", styles["H1"]))
    story.append(make_table(
        ["Field", "Value"],
        [
            ["Document Version", "v1.0"],
            ["Status", "Draft for Review"],
            ["Model Version", "Health Score v3.0 (5 dimensions)"],
            ["Previous Model", "v2.x (8 dimensions - deprecated)"],
            ["KPI Formula Layer", "Canonical (kpi_formulas.py) - single source of truth"],
            ["Last Code Audit", "March 2026"],
            ["Test Coverage", "722 backend tests passing"],
            ["Locales Supported", "Italian, English, German, French"],
            ["AI Model", "Claude (Anthropic), temperature 0.2, max 200 tokens"],
        ],
        col_widths=[120, W - 120],
    ))

    story.append(Spacer(1, 12))
    story.append(Paragraph("<b>Planned for v1.1:</b>", styles["Body"]))
    for item in [
        "Confidence badge more prominent in Health Score gauge UI",
        "Sector-specific threshold profiles (e.g., restaurant vs. manufacturing)",
        "Bank feed integration to replace proxy operational coverage with real liquidity",
    ]:
        story.append(Paragraph(item, styles["BulletItem"]))

    story.append(Spacer(1, 24))
    story.append(HRFlowable(width="100%", thickness=0.5, color=MUTED, spaceAfter=8))
    story.append(Paragraph(
        "<i>This document is proprietary to AFianco S.r.l. Distribution is limited to "
        "authorized internal stakeholders and designated investors.</i>",
        styles["Note"]
    ))

    # ── BUILD ───────────────────────────────────────────────────────────────
    doc.build(story, onFirstPage=add_header_footer, onLaterPages=add_header_footer)
    print(f"PDF generated: {output_path}")


if __name__ == "__main__":
    output = os.path.join(os.path.dirname(__file__), "cashflow-monitor-methodology-v1.pdf")
    build_pdf(output)
