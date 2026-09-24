"""Lotto E3 (24/9/2026) — la riga del Cerchio nelle email transazionali.

Il cliente che compra e' cliente dell'OPERATORE, non di Aurya (legal a
due livelli): il Cerchio e' marketing di un altro titolare e non puo'
essere un effetto dell'ordine. Quello che si puo' fare (ANALISI §6.3) e'
UNA riga, non un volantino, in due email che gia' partono (conferma
ordine, codice per la recensione), con un link firmato: il clic e'
insieme il consenso e la prova dell'indirizzo (rotta
/public/newsletter/entra/{token} in routers/subscribers.py).

La riga NON si mostra a chi e' gia' iscritto confermato (best effort:
se il controllo fallisce, la riga non parte: meglio una porta in meno
che un invito a chi e' gia' dentro).
"""
from __future__ import annotations

import logging
from html import escape
from typing import Optional
from urllib.parse import quote

logger = logging.getLogger(__name__)

# le superfici del canale «commercio» che vivono in un'email
SUPERFICI_EMAIL = ("email-ordine", "email-recensione")

TESTO_RIGA = "Vuoi la Lettera del Cerchio di Aurya (meditazioni, guide, ritiri)? Un clic:"
TESTO_LINK = "entro nel Cerchio"


def link_entra(email: str, da: str = "email-ordine", to: Optional[str] = None) -> str:
    """URL assoluto del link «entra con un clic»: token firmato
    dell'email, fonte (`da`) e, se serve, dove andare dopo (solo
    percorsi interni: la rotta scarta il resto)."""
    from core.subscriber_token import generate_subscriber_token
    from services.url_builder import build_public_url
    token = generate_subscriber_token(email)
    fonte = da if da in SUPERFICI_EMAIL else "email-ordine"
    url = build_public_url(f"/api/public/newsletter/entra/{token}") + f"?da={fonte}"
    if to:
        url += f"&to={quote(to, safe='/')}"
    return url


async def gia_nel_cerchio(email: str) -> bool:
    """True se l'indirizzo e' un iscritto CONFERMATO: a lui la riga non
    serve. Un errore di lettura vale come «gia' dentro» (niente riga)."""
    try:
        from database import db
        doc = await db.aurya_subscribers.find_one(
            {"email": (email or "").strip().lower()}, {"_id": 0, "status": 1})
        return bool(doc and doc.get("status") == "confirmed")
    except Exception as exc:                # noqa: BLE001
        logger.warning("porte_cerchio: controllo iscritto fallito: %s", exc)
        return True


async def riga_cerchio_html(email: str, da: str = "email-ordine",
                            locale: str = "it") -> str:
    """La riga pronta per il template dell'email, o "" quando non va
    mostrata (gia' iscritto, lingua non italiana: la Lettera e' in
    italiano, email vuota). Mai un'eccezione: l'email transazionale non
    si rompe per una porta in piu'."""
    try:
        email = (email or "").strip().lower()
        if not email or not (locale or "it").lower().startswith("it"):
            return ""
        if await gia_nel_cerchio(email):
            return ""
        url = link_entra(email, da)
        return (f'<p style="color:#666;font-size:13px;" data-porta="cerchio">'
                f'{escape(TESTO_RIGA)} <a href="{url}">{escape(TESTO_LINK)}</a></p>')
    except Exception as exc:                # noqa: BLE001
        logger.warning("porte_cerchio: riga non costruita: %s", exc)
        return ""
