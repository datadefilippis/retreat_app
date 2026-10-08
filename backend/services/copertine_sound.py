"""MR1 (8/10/2026, piano refinement meditazioni) — LE COPERTINE, UN FORMATO SOLO.

Decisione del founder: 1:1. Ogni copertina di meditazione o playlist che
entra (foto del founder) si RITAGLIA AL CENTRO in quadrato e si
ridimensiona a 1200×1200 WebP: una sola versione, uguale in ogni vista
(card, vetrina, pagina playlist, email, card social).

Chi non ha una foto riceve la COPERTINA GENERATA (rete di sicurezza,
decisione 4 del piano Sound): un gradiente nel tono della meditazione con
il titolo, fatta una volta sola alla pubblicazione e salvata come vera
`cover_url`, così email e card social la vedono uguale. Stesso mestiere di
services/article_cover.py (Magazine), stessi font.
"""
from __future__ import annotations

import io
import logging
import math
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger("aurya.copertine_sound")

LATO = 1200
QUALITA_WEBP = 84
_FONTS_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"

# i toni della casa (gli stessi di casa/MeditazioniCasa.jsx: TONI per intento)
TONI = {
    "salvia": ((28, 52, 48), (127, 201, 176)),
    "viola": ((34, 30, 56), (181, 166, 222)),
    "acqua": ((22, 48, 56), (126, 193, 199)),
    "oro": ((48, 40, 26), (201, 179, 126)),
}
TONO_PER_INTENT = {"dormire": "viola", "elaborare": "viola", "meditare": "salvia",
                   "concentrare": "acqua", "rilassare": "oro", "energizzare": "oro"}


def tono_di(intent: Optional[str], tono: Optional[str] = None) -> str:
    if tono in TONI:
        return tono
    return TONO_PER_INTENT.get(intent or "", "oro")


def _apri(data: bytes):
    from PIL import Image, ImageOps
    try:  # iPhone: HEIC/HEIF, se il plugin c'e' (PV1)
        import pillow_heif
        pillow_heif.register_heif_opener()
    except Exception:  # noqa: BLE001
        pass
    img = Image.open(io.BytesIO(data))
    img = ImageOps.exif_transpose(img)
    return img.convert("RGB")


def quadra(data: bytes, lato: int = LATO) -> Tuple[bytes, str]:
    """Ritaglio al centro in quadrato + lato fisso + WebP. Ritorna (bytes, 'webp')."""
    from PIL import Image, ImageOps
    img = _apri(data)
    img = ImageOps.fit(img, (lato, lato), method=Image.LANCZOS, centering=(0.5, 0.5))
    out = io.BytesIO()
    img.save(out, format="WEBP", quality=QUALITA_WEBP, method=4)
    return out.getvalue(), "webp"


def _font(nome: str, size: int):
    from PIL import ImageFont
    try:
        return ImageFont.truetype(str(_FONTS_DIR / nome), size)
    except Exception:  # noqa: BLE001
        return ImageFont.load_default()


def _sfondo(base, bagliore, lato: int):
    """Gradiente radiale: luce in alto a sinistra, buio in basso a destra."""
    from PIL import Image
    piccolo = lato // 6
    im = Image.new("RGB", (piccolo, piccolo), base)
    px = im.load()
    cx, cy = piccolo * 0.3, piccolo * 0.2
    max_d = math.hypot(piccolo, piccolo) * 0.8
    for y in range(piccolo):
        for x in range(piccolo):
            d = math.hypot(x - cx, y - cy) / max_d
            t = max(0.0, 1.0 - d) ** 2 * 0.6
            px[x, y] = tuple(round(base[i] + (bagliore[i] - base[i]) * t) for i in range(3))
    return im.resize((lato, lato), Image.LANCZOS)


def _a_capo(draw, testo: str, font, larghezza: int, max_righe: int = 3):
    parole = testo.split()
    righe, riga = [], ""
    for p in parole:
        prova = (riga + " " + p).strip()
        if draw.textlength(prova, font=font) <= larghezza or not riga:
            riga = prova
        else:
            righe.append(riga)
            riga = p
    if riga:
        righe.append(riga)
    if len(righe) > max_righe:
        righe = righe[:max_righe]
        righe[-1] = righe[-1].rstrip(".,;:") + "…"
    return righe


def genera_fallback(titolo: str, intent: Optional[str] = None, sottotitolo: str = "",
                    tono: Optional[str] = None, lato: int = LATO) -> Tuple[bytes, str]:
    """La copertina generata: tono della meditazione, titolo in Playfair,
    l'etichetta «AURYA SOUND» in Cinzel, un anello sottile (il cerchio)."""
    from PIL import ImageDraw
    base, bagliore = TONI[tono_di(intent, tono)]
    im = _sfondo(base, bagliore, lato)
    d = ImageDraw.Draw(im)
    bone = (242, 237, 228)
    oro = (214, 196, 154)
    # l'anello
    r = lato * 0.26
    cx, cy = lato * 0.5, lato * 0.36
    d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=(*oro, ), width=max(2, lato // 300))
    d.ellipse((cx - r * 0.82, cy - r * 0.82, cx + r * 0.82, cy + r * 0.82), outline=tuple(min(255, c + 20) for c in base), width=max(1, lato // 400))
    # l'etichetta
    f_et = _font("Cinzel-SemiBold.ttf", lato // 34)
    et = "A U R Y A   S O U N D"
    d.text((cx - d.textlength(et, font=f_et) / 2, lato * 0.10), et, font=f_et, fill=oro)
    # il titolo (si adatta: 3 righe massimo)
    titolo = (titolo or "Meditazione").strip()
    for size in (lato // 11, lato // 13, lato // 15, lato // 18):
        f = _font("PlayfairDisplay-Variable.ttf", size)
        righe = _a_capo(d, titolo, f, int(lato * 0.78))
        if len(righe) <= 3:
            break
    alt = int(size * 1.18)
    y0 = lato * 0.72 - alt * len(righe) / 2 + lato * 0.02
    for i, riga in enumerate(righe):
        w = d.textlength(riga, font=f)
        d.text((lato / 2 - w / 2, y0 + i * alt), riga, font=f, fill=bone)
    if sottotitolo:
        f_s = _font("Manrope-Regular.ttf", lato // 30)
        w = d.textlength(sottotitolo, font=f_s)
        d.text((lato / 2 - w / 2, y0 + len(righe) * alt + lato * 0.02), sottotitolo, font=f_s, fill=oro)
    out = io.BytesIO()
    im.save(out, format="WEBP", quality=QUALITA_WEBP, method=4)
    return out.getvalue(), "webp"


def salva_fallback_traccia(track: dict) -> Optional[str]:
    """Genera e salva la copertina di una traccia senza foto; ritorna l'URL
    (o None se qualcosa va storto: mai bloccare una pubblicazione)."""
    try:
        from services.object_storage import save_public_upload
        import uuid
        minuti = int(round(((track.get("score") or {}).get("duration_sec") or track.get("duration_sec") or 0) / 60))
        sotto = f"{minuti} minuti" if minuti else ""
        data, ext = genera_fallback(track.get("title") or "Meditazione", track.get("intent"), sotto)
        return save_public_upload("frequenze", f"{track['id']}.{uuid.uuid4().hex[:8]}.gen.{ext}", data, content_type="image/webp")
    except Exception as exc:  # noqa: BLE001
        logger.warning("copertina generata non salvata per %s: %s", track.get("id"), exc)
        return None


def salva_fallback_playlist(playlist: dict, n_tracce: int = 0) -> Optional[str]:
    try:
        from services.object_storage import save_public_upload
        import uuid
        sotto = f"{n_tracce} meditazion{'e' if n_tracce == 1 else 'i'}" if n_tracce else "Playlist"
        data, ext = genera_fallback(playlist.get("title") or "Playlist", None, sotto, tono="oro")
        return save_public_upload("playlists", f"{playlist['id']}.{uuid.uuid4().hex[:8]}.gen.{ext}", data, content_type="image/webp")
    except Exception as exc:  # noqa: BLE001
        logger.warning("copertina generata non salvata per playlist %s: %s", playlist.get("id"), exc)
        return None
