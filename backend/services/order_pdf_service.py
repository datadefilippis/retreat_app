"""
Order PDF Service — generates order receipt/confirmation PDFs.

Uses ReportLab (same as digest_pdf). Lightweight, no external dependencies.
"""

import io
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def generate_order_receipt(order: dict, store_settings: dict, locale: str = "it") -> bytes:
    """Generate a PDF receipt for an order. Returns bytes.

    Graceful degradation: truncates long strings, handles missing fields.
    Raises RuntimeError with context if ReportLab fails.

    ``locale`` controls the numeric layout for monetary amounts (it/de/fr
    use European-style decimals, en uses US-style). The currency itself
    is derived from the order's snapshot via
    :func:`services.currency_service.get_currency_for_order`, with the
    legacy EUR fallback for orders that pre-date the multi-currency
    work — so callers that don't pass ``locale`` keep producing identical
    output to before this refactor.
    """
    try:
        return _build_receipt_pdf(order, store_settings, locale=locale)
    except Exception as e:
        logger.error("order_pdf: generation failed for order %s: %s", order.get("id", "?")[:12], e)
        raise RuntimeError(f"Errore nella generazione del PDF: {str(e)}")


def _build_receipt_pdf(order: dict, store_settings: dict, locale: str = "it") -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=20*mm, rightMargin=20*mm,
                            topMargin=20*mm, bottomMargin=20*mm)

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('Title2', parent=styles['Title'], fontSize=18, spaceAfter=6)
    subtitle_style = ParagraphStyle('Sub', parent=styles['Normal'], fontSize=10, textColor=colors.grey)
    normal = styles['Normal']
    bold_style = ParagraphStyle('Bold', parent=normal, fontName='Helvetica-Bold')

    store_name = store_settings.get("display_name") or "Store"
    store_email = store_settings.get("contact_email") or ""
    store_phone = store_settings.get("contact_phone") or ""

    order_number = order.get("order_number") or order.get("id", "")[:8]
    order_date = order.get("order_date") or ""
    customer_name = order.get("customer_name") or ""
    status = order.get("status", "draft")
    payment_status = order.get("payment_status", "pending")

    elements = []

    # Header
    elements.append(Paragraph(store_name, title_style))
    if store_email or store_phone:
        elements.append(Paragraph(f"{store_email}  {store_phone}", subtitle_style))
    elements.append(Spacer(1, 8*mm))

    # Order info
    status_label = {"draft": "Bozza", "confirmed": "Confermato", "completed": "Completato", "cancelled": "Annullato"}.get(status, status)
    payment_label = {"pending": "In attesa", "paid": "Pagato", "overdue": "Scaduto"}.get(payment_status, payment_status)

    elements.append(Paragraph(f"<b>Ricevuta Ordine {order_number}</b>", bold_style))
    elements.append(Paragraph(f"Data: {order_date} &nbsp;&nbsp; Stato: {status_label} &nbsp;&nbsp; Pagamento: {payment_label}", normal))
    elements.append(Paragraph(f"Cliente: <b>{customer_name}</b>", normal))

    # Fulfillment
    ff = order.get("fulfillment") or {}
    if ff.get("mode") == "shipping" and ff.get("shipping_address"):
        elements.append(Paragraph(f"Spedizione: {ff['shipping_address']}", normal))
    if order.get("notes"):
        elements.append(Paragraph(f"Note: {order['notes']}", normal))

    elements.append(Spacer(1, 6*mm))

    # CH compliance v1: resolve currency from the order snapshot once,
    # then format every amount through the shared formatter so the PDF
    # matches the email and the in-app frontend exactly. The locale comes
    # from the caller (defaults to it).
    from core.currency_format import format_amount
    from services.currency_service import get_currency_for_order
    receipt_currency = get_currency_for_order(order)

    # Items table
    items = order.get("items", [])
    table_data = [["Prodotto", "Tipo", "Qtà", "Prezzo", "Totale"]]
    for item in items:
        type_label = {"physical": "Fisico", "service": "Servizio", "rental": "Noleggio",
                      "event_ticket": "Evento", "booking": "Prenotazione"}.get(item.get("item_type", ""), "")
        qty = item.get("quantity", 1)
        price = item.get("unit_price", 0)
        total = item.get("line_total", 0)
        name = item.get("product_name", "")

        # Add date info for booking/rental/event
        if item.get("booking_date"):
            name += f" ({item['booking_date']} {item.get('booking_start_time', '')}-{item.get('booking_end_time', '')})"
        elif item.get("rental_date_from"):
            name += f" ({item['rental_date_from']}"
            if item.get("rental_date_to"):
                name += f" → {item['rental_date_to']}"
            name += ")"
        elif item.get("occurrence_start_at"):
            name += f" ({item['occurrence_start_at'][:10]})"

        table_data.append([
            name,
            type_label,
            str(int(qty)),
            format_amount(price, receipt_currency, locale=locale),
            format_amount(total, receipt_currency, locale=locale),
        ])

    # Total row
    subtotal = order.get("subtotal") or order.get("total") or 0
    table_data.append(["", "", "", "Totale:", format_amount(subtotal, receipt_currency, locale=locale)])

    table = Table(table_data, colWidths=[200, 60, 35, 60, 60])
    table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.95, 0.95, 0.95)),
        ('GRID', (0, 0), (-1, -2), 0.5, colors.Color(0.85, 0.85, 0.85)),
        ('FONTNAME', (-2, -1), (-1, -1), 'Helvetica-Bold'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
    ]))
    elements.append(table)

    elements.append(Spacer(1, 10*mm))
    elements.append(Paragraph(
        f"<i>Documento generato il {datetime.now().strftime('%d/%m/%Y %H:%M')} — {store_name}</i>",
        ParagraphStyle('Footer', parent=normal, fontSize=8, textColor=colors.grey),
    ))

    doc.build(elements)
    return buf.getvalue()
