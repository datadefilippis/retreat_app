"""SN2 (8/10/2026, piano Aurya Sound §4.5) — L'ANNUNCIO AL CERCHIO.

Quando il founder pubblica una meditazione o una playlist nuova, il
Cerchio la riceve per email con il link diretto: «Ascolta ora» apre la
pagina già sbloccata (link verificante + prova, come il pulsante della
Lettera). Un annuncio per contenuto, mai due: il documento si marca PRIMA
di spedire (stessa regola del promemoria del Cerchio).

A chi: gli iscritti a cui il Cerchio scrive (services.sequenze.filtro_sub,
che rispetta l'interruttore del singolo opt-in). La prova a secco conta i
destinatari e restituisce l'anteprima senza spedire nulla.
"""
from __future__ import annotations

import asyncio
import html as _html
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

logger = logging.getLogger("aurya.annunci_sound")

_MAX_DESTINATARI = 5000


def attivo() -> bool:
    """L'INTERRUTTORE (founder 8/10/2026 sera: «non voglio mandare email
    automatiche al Cerchio prima di aver creato le meditazioni»). Spento
    di default: l'annuncio non parte da nessuna porta, nemmeno a mano. Si
    accende con SOUND_ANNUNCI_ATTIVI=1 nell'ambiente, letto a ogni chiamata."""
    import os
    return (os.getenv("SOUND_ANNUNCI_ATTIVI") or "").strip().lower() in ("1", "true", "on", "si", "sì", "yes")


def _fmt_min(sec) -> str:
    m = int(round((sec or 0) / 60))
    return f"{m} minut{'o' if m == 1 else 'i'}" if m else ""


def _cover_assoluta(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    if url.startswith("http"):
        return url
    from services.url_builder import build_public_url
    return build_public_url(url)


def testo_annuncio(kind: str, doc: dict, guida: str = "") -> Dict[str, str]:
    """Oggetto e corpo (HTML interno, senza il telaio) per una traccia o
    una playlist. `doc` porta title, description, slug, cover_url, e per
    la traccia intent/duration_sec, per la playlist tracce_count/duration_sec."""
    titolo = _html.escape(doc.get("title") or ("Playlist" if kind == "playlist" else "Meditazione"))
    racconto = _html.escape((doc.get("description") or "").strip()[:400])
    if kind == "playlist":
        oggetto = f"Nuova playlist nel Cerchio: {doc.get('title') or 'Playlist'}"
        n = doc.get("tracce_count") or 0
        riga = f"{n} meditazion{'e' if n == 1 else 'i'}"
        durata = _fmt_min(doc.get("duration_sec"))
        if durata:
            riga += f" · {durata}"
        percorso = f"/meditazioni/playlist/{doc.get('slug')}?da=email"
        intro = "C'è una playlist nuova nella casa delle meditazioni: una raccolta da ascoltare in fila, una dopo l'altra."
    else:
        oggetto = f"Nuova meditazione nel Cerchio: {doc.get('title') or 'Meditazione'}"
        parti = []
        if doc.get("intent"):
            parti.append(_html.escape(str(doc["intent"]).capitalize()))
        durata = _fmt_min((doc.get("score") or {}).get("duration_sec") or doc.get("duration_sec"))
        if durata:
            parti.append(durata)
        if guida:
            parti.append(f"guidata da {_html.escape(guida)}")
        riga = " · ".join(parti)
        percorso = f"/frequenze/{doc.get('slug')}?da=email"
        intro = "C'è una meditazione nuova nella casa delle meditazioni, composta per il Cerchio di Aurya."
    cover = _cover_assoluta(doc.get("cover_url"))
    corpo = (
        (f'<p><img src="{_html.escape(cover)}" alt="" width="520" '
         f'style="max-width:100%;border-radius:14px;display:block"></p>' if cover else "")
        + f"<p>{intro}</p>"
        + f"<h2 style=\"margin:18px 0 4px\">{titolo}</h2>"
        + (f"<p style=\"color:#6b6b6b;margin:0 0 10px\">{_html.escape(riga)}</p>" if riga else "")
        + (f"<p>{racconto}</p>" if racconto else "")
    )
    return {"oggetto": oggetto, "corpo": corpo, "percorso": percorso}


async def destinatari() -> List[dict]:
    from database import db
    from services.sequenze import filtro_sub
    out = []
    async for s in db.aurya_subscribers.find(filtro_sub(), {"_id": 0, "email": 1, "name": 1}).limit(_MAX_DESTINATARI):
        if s.get("email"):
            out.append(s)
    return out


def _spedisci_uno(email: str, nome: Optional[str], oggetto: str, corpo: str, percorso: str) -> bool:
    try:
        from services.email_service import _link_block, _wrap_template, send_email
        from services.email_sequenze import _bottone, _link, _saluto, url_preferenze_nudo
        from core.subscriber_token import generate_subscriber_token
        url = _link(email, percorso)
        html = _wrap_template(
            f"<p>{_saluto(nome or '')}</p>" + corpo
            + _bottone(url, "Ascolta ora") + _link_block(url)
            + "<p style=\"color:#8a8a8a;font-size:13px\">Il link apre la meditazione già sbloccata per te. "
              "Se non ti va, non devi fare nulla.</p>")
        return bool(send_email(email, oggetto, html,
                               unsubscribe_url=url_preferenze_nudo(generate_subscriber_token(email))))
    except Exception as exc:  # noqa: BLE001 — un indirizzo rotto non ferma gli altri
        logger.warning("annuncio sound: email fallita per %s: %s", (email or "")[:2] + "***", exc)
        return False


async def spedisci(kind: str, coll, doc_id: str, oggetto: str, corpo: str, percorso: str, lista: List[dict]) -> Dict[str, int]:
    """Il giro vero, in background: un'email alla volta fuori dal loop,
    poi il conto sul documento (inviati, errori, stato fatto)."""
    inviati = errori = 0
    for s in lista:
        ok = await asyncio.to_thread(_spedisci_uno, s["email"], s.get("name"), oggetto, corpo, percorso)
        if ok:
            inviati += 1
        else:
            errori += 1
    try:
        await coll.update_one({"id": doc_id}, {"$set": {"annuncio.inviati": inviati, "annuncio.errori": errori,
                                                        "annuncio.stato": "fatto",
                                                        "annuncio.finito_at": datetime.now(timezone.utc)}})
    except Exception as exc:  # noqa: BLE001
        logger.warning("annuncio sound (%s %s): conto non salvato: %s", kind, doc_id, exc)
    logger.info("annuncio sound %s %s: %d inviati, %d errori", kind, doc_id, inviati, errori)
    return {"inviati": inviati, "errori": errori}


async def prenota(coll, doc_id: str, n: int) -> bool:
    """Marca il documento come annunciato PRIMA di spedire: True se la
    marca e' nostra (nessun annuncio prima), False se qualcuno ha gia'
    annunciato (niente doppioni)."""
    r = await coll.update_one(
        {"id": doc_id, "annuncio.at": {"$exists": False}},
        {"$set": {"annuncio": {"at": datetime.now(timezone.utc), "destinatari": n, "inviati": 0,
                               "errori": 0, "stato": "in_corso"}}})
    return r.modified_count == 1
