"""AN6 — cover autogenerate per gli articoli del blog.

Ogni categoria olistica ha la sua tonalità sopra la palette Aurya
(Salvia #376254 / Terracotta #C97B5D / Crema #F6F3EC): fondo con
gradiente radiale come l'hero del marketplace, glifo di categoria
in filigrana, overline di categoria in Cinzel (il font del wordmark)
e IL TITOLO DENTRO l'immagine in Manrope. Output WebP 1200×630
(OG-perfetto). Best-effort by design: se Pillow o i font mancano,
l'articolo esce senza cover, mai un publish bloccato.
"""

import logging
import math
from io import BytesIO
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

WIDTH, HEIGHT = 1200, 630

_FONTS_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"

# Palette per categoria: (tono di fondo scuro, tono radiale chiaro).
# Il fondo resta nella famiglia Salvia con derive percettive per
# categoria; il testo è sempre crema (contrasto AA garantito).
CATEGORY_PALETTES = {
    "yoga":        ((55, 98, 84),  (138, 116, 64)),   # salvia + oro brand
    "meditazione": ((47, 79, 79),  (100, 130, 120)),
    "detox":       ((62, 92, 62),  (140, 160, 110)),
    "suono":       ((72, 62, 92),  (150, 130, 170)),
    "massaggio":   ((122, 82, 62), (201, 123, 77)),   # terracotta
    "breathwork":  ((52, 82, 102), (120, 150, 170)),
    "cammini":     ((72, 82, 52),  (150, 160, 110)),
    "femminile":   ((112, 62, 82), (190, 130, 150)),
    "aziendale":   ((62, 72, 82),  (130, 140, 150)),
}
_DEFAULT_PALETTE = ((55, 98, 84), (138, 116, 64))    # salvia + oro

CREAM = (246, 243, 236)
GOLD_LIGHT = (214, 196, 154)


def _load_font(name: str, size: int, weight: Optional[int] = None):
    from PIL import ImageFont
    font = ImageFont.truetype(str(_FONTS_DIR / name), size)
    if weight is not None:
        try:
            font.set_variation_by_axes([weight])
        except Exception:            # font non variabile: pazienza
            pass
    return font


def _radial_background(base: Tuple[int, int, int],
                       glow: Tuple[int, int, int]):
    """Gradiente radiale dal quadrante alto-destro, come la texture
    dell'hero directory (M4)."""
    from PIL import Image
    img = Image.new("RGB", (WIDTH, HEIGHT), base)
    px = img.load()
    cx, cy = WIDTH * 0.82, HEIGHT * 0.18
    max_d = math.hypot(WIDTH, HEIGHT) * 0.75
    # campiona a passi di 4 e lascia che il resize lisci: 75× più
    # veloce del per-pixel pieno, invisibile a occhio dopo LANCZOS
    small = Image.new("RGB", (WIDTH // 4, HEIGHT // 4), base)
    spx = small.load()
    for y in range(HEIGHT // 4):
        for x in range(WIDTH // 4):
            d = math.hypot(x * 4 - cx, y * 4 - cy) / max_d
            t = max(0.0, 1.0 - d) ** 2 * 0.55
            spx[x, y] = tuple(
                round(base[i] + (glow[i] - base[i]) * t) for i in range(3))
    return small.resize((WIDTH, HEIGHT), Image.LANCZOS)


def _wrap_title(draw, title: str, font, max_width: int) -> list:
    words = title.split()
    lines, line = [], ""
    for w in words:
        probe = f"{line} {w}".strip()
        if draw.textlength(probe, font=font) <= max_width or not line:
            line = probe
        else:
            lines.append(line)
            line = w
    if line:
        lines.append(line)
    return lines[:4]                  # mai più di 4 righe


def render_article_cover(title: str,
                         category: Optional[str] = None,
                         category_label: Optional[str] = None) -> Optional[bytes]:
    """Rende la cover come bytes WebP, o None se l'ambiente non può
    (Pillow/font assenti): il chiamante NON deve mai fallire per noi."""
    try:
        from PIL import ImageDraw

        base, glow = CATEGORY_PALETTES.get(category or "", _DEFAULT_PALETTE)
        img = _radial_background(base, glow)
        draw = ImageDraw.Draw(img)

        # aura in filigrana: cerchi concentrici come il sole del logo,
        # mezzi fuori dal bordo destro (nessuna dipendenza dai font)
        ring = tuple(min(255, c + 16) for c in base)
        cx, cy = WIDTH - 150, HEIGHT - 140
        for r in (270, 210, 150, 90):
            draw.ellipse((cx - r, cy - r, cx + r, cy + r),
                         outline=ring, width=3)

        margin = 84
        # overline: categoria (o il motto) in Cinzel oro, tracking largo
        overline = (category_label or "CONNECT · HEAL · GROW").upper()
        over_font = _load_font("Cinzel-SemiBold.ttf", 30, weight=600)
        draw.text((margin, 96), " ".join(overline), font=over_font,
                  fill=GOLD_LIGHT)

        # titolo in Manrope, crema, a capo automatico
        title_font = _load_font("Manrope-Regular.ttf", 68, weight=600)
        lines = _wrap_title(draw, title, title_font, WIDTH - margin * 2 - 60)
        y = 190
        for line in lines:
            draw.text((margin, y), line, font=title_font, fill=CREAM)
            y += 86

        # firma wordmark in basso
        brand_font = _load_font("Cinzel-SemiBold.ttf", 34, weight=600)
        draw.text((margin, HEIGHT - 110), "A U R Y A", font=brand_font,
                  fill=GOLD_LIGHT)

        buf = BytesIO()
        img.save(buf, format="WEBP", quality=82)
        return buf.getvalue()
    except Exception as exc:          # pragma: no cover - ambiente povero
        logger.warning("article_cover: generazione saltata (%s)", exc)
        return None
