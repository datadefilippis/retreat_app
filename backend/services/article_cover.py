"""AN6/DS2 — cover autogenerate per gli articoli del blog.

Ogni categoria olistica ha la sua tonalità sopra la palette Aurya
(Salvia #376254 / Terracotta #C97B5D / Crema #F6F3EC) e la sua
GEOMETRIA SACRA in filigrana (fiore della vita, vesica piscis,
spirale aurea…), disegnata con ImageDraw: zero dipendenze dai font.
In basso la firma: logo loto+sole + wordmark AURYA in Cinzel oro,
come nell'header del sito. Titolo DENTRO l'immagine in Manrope.
Output WebP 1200×630 (OG-perfetto). Best-effort by design: se
Pillow o gli asset mancano, l'articolo esce senza cover, mai un
publish bloccato.
"""

import logging
import math
from io import BytesIO
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

WIDTH, HEIGHT = 1200, 630

_ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
_FONTS_DIR = _ASSETS_DIR / "fonts"
_LOGO_PATH = _ASSETS_DIR / "brand" / "logo-aurya-128.png"

# Palette per categoria: (tono di fondo scuro, tono radiale chiaro).
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


# ─── Geometrie sacre (line art, una per categoria) ─────────────────────

def _circle(draw, cx, cy, r, color, w=3):
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), outline=color, width=w)


def _geo_lotus(draw, cx, cy, R, color):
    """Yoga — fiore di loto: petali come cerchi intersecati a raggiera."""
    for k in range(8):
        a = math.radians(k * 45)
        _circle(draw, cx + math.cos(a) * R * 0.45,
                cy + math.sin(a) * R * 0.45, R * 0.55, color)


def _geo_flower_of_life(draw, cx, cy, R, color):
    """Meditazione — fiore della vita: reticolo esagonale di cerchi."""
    r = R * 0.38
    _circle(draw, cx, cy, r, color)
    for ring, dist in ((6, r), (6, r * math.sqrt(3)), (6, 2 * r)):
        for k in range(ring):
            a = math.radians(k * 60 + (30 if dist == r * math.sqrt(3) else 0))
            _circle(draw, cx + math.cos(a) * dist, cy + math.sin(a) * dist,
                    r, color)


def _geo_seed_of_life(draw, cx, cy, R, color):
    """Detox — seme della vita: 7 cerchi, il germoglio di tutto."""
    r = R * 0.5
    _circle(draw, cx, cy, r, color)
    for k in range(6):
        a = math.radians(k * 60)
        _circle(draw, cx + math.cos(a) * r, cy + math.sin(a) * r, r, color)


def _geo_waves(draw, cx, cy, R, color):
    """Suono — cimatica: onde concentriche."""
    for k in range(1, 7):
        _circle(draw, cx, cy, R * k / 6, color)


def _geo_vesica(draw, cx, cy, R, color):
    """Massaggio — vesica piscis: due cerchi che si compenetrano."""
    r = R * 0.62
    _circle(draw, cx - r / 2, cy, r, color)
    _circle(draw, cx + r / 2, cy, r, color)
    _circle(draw, cx, cy, r * 1.55, color)


def _geo_spiral(draw, cx, cy, R, color):
    """Breathwork — spirale aurea: il ritmo del respiro."""
    a, b = R * 0.02, 0.16
    pts = []
    for i in range(0, 1700, 5):
        t = math.radians(i)
        r = a * math.exp(b * t)
        if r > R:
            break
        pts.append((cx + math.cos(t) * r, cy + math.sin(t) * r))
    if len(pts) > 1:
        draw.line(pts, fill=color, width=3, joint="curve")


def _geo_hexagram(draw, cx, cy, R, color):
    """Cammini — due triangoli intrecciati nel cerchio: terra e cielo."""
    _circle(draw, cx, cy, R * 0.9, color)
    for rot in (0, 180):
        pts = []
        for k in range(3):
            a = math.radians(rot + 90 + k * 120)
            pts.append((cx + math.cos(a) * R * 0.78,
                        cy - math.sin(a) * R * 0.78))
        draw.polygon(pts, outline=color, width=3)


def _geo_triple_moon(draw, cx, cy, R, color):
    """Femminile — triplice luna: crescente, piena, calante."""
    r = R * 0.36
    _circle(draw, cx, cy, r, color)                       # luna piena
    for side in (-1, 1):
        x = cx + side * r * 1.7
        _circle(draw, x, cy, r * 0.78, color)
        _circle(draw, x + side * r * 0.4, cy, r * 0.7, color)


def _geo_metatron(draw, cx, cy, R, color):
    """Aziendale — cubo di Metatron semplificato: l'ordine nel cerchio."""
    _circle(draw, cx, cy, R * 0.92, color)
    verts = []
    for k in range(6):
        a = math.radians(k * 60 + 30)
        verts.append((cx + math.cos(a) * R * 0.72,
                      cy + math.sin(a) * R * 0.72))
    for i in range(6):
        for j in range(i + 1, 6):
            draw.line([verts[i], verts[j]], fill=color, width=2)
    for v in verts:
        _circle(draw, v[0], v[1], R * 0.1, color)


def _geo_aura(draw, cx, cy, R, color):
    """Default — l'aura del logo: cerchi concentrici."""
    for k in (1.0, 0.75, 0.5, 0.25):
        _circle(draw, cx, cy, R * k, color)


CATEGORY_GEOMETRY = {
    "yoga": _geo_lotus,
    "meditazione": _geo_flower_of_life,
    "detox": _geo_seed_of_life,
    "suono": _geo_waves,
    "massaggio": _geo_vesica,
    "breathwork": _geo_spiral,
    "cammini": _geo_hexagram,
    "femminile": _geo_triple_moon,
    "aziendale": _geo_metatron,
}


# ─── Composizione ──────────────────────────────────────────────────────

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
    (Pillow/font assenti): il chiamante NON deve mai fallire per noi.

    Design v2 (11/7, armonizzato sulle card Masseria che il founder ama):
    cornice doppia incisa, texture a puntini, titolo SERIF (Playfair)
    ancorato in basso, geometria sacra discreta in alto a destra, firma
    con lineetta. Tutti gli elementi delicati passano da un layer RGBA
    così l'opacità è controllata davvero (niente linee grezze)."""
    try:
        from PIL import Image, ImageDraw

        base, glow = CATEGORY_PALETTES.get(category or "", _DEFAULT_PALETTE)
        img = _radial_background(base, glow).convert("RGBA")

        # ── layer delicato: texture, cornice, geometria (con alpha) ──
        fine = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
        fdraw = ImageDraw.Draw(fine)

        gold_soft = GOLD_LIGHT + (66,)     # oro al ~26%: inciso, non urlato
        gold_faint = GOLD_LIGHT + (34,)

        # texture: griglia di puntini appena percettibile
        for gy in range(46, HEIGHT - 30, 34):
            for gx in range(46, WIDTH - 30, 34):
                fdraw.ellipse((gx - 1, gy - 1, gx + 1, gy + 1),
                              fill=gold_faint)

        # cornice doppia incisa, come una card stampata
        fdraw.rectangle((26, 26, WIDTH - 26, HEIGHT - 26),
                        outline=gold_soft, width=1)
        fdraw.rectangle((36, 36, WIDTH - 36, HEIGHT - 36),
                        outline=gold_faint, width=1)

        # geometria sacra di categoria: piccola, in alto a destra,
        # tratto sottile oro (non più filigrana tono su tono)
        geometry = CATEGORY_GEOMETRY.get(category or "", _geo_aura)
        geometry(fdraw, WIDTH - 235, 205, 130, gold_soft)

        img = Image.alpha_composite(img, fine)
        draw = ImageDraw.Draw(img)

        margin = 84
        # overline: categoria (o il motto) in Cinzel oro, tracking largo
        overline = (category_label or "CONNECT · HEAL · GROW").upper()
        over_font = _load_font("Cinzel-SemiBold.ttf", 26, weight=600)
        draw.text((margin, 84), " ".join(overline), font=over_font,
                  fill=GOLD_LIGHT)

        # firma in basso: lineetta oro + logo + wordmark
        sign_y = HEIGHT - 118
        draw.line((margin, sign_y - 16, margin + 56, sign_y - 16),
                  fill=GOLD_LIGHT, width=2)
        logo_size = 44
        try:
            logo = Image.open(_LOGO_PATH).convert("RGBA")
            logo.thumbnail((logo_size, logo_size), Image.LANCZOS)
            img.paste(logo, (margin, sign_y), logo)
            text_x = margin + logo_size + 16
        except Exception:             # senza logo la firma resta il wordmark
            text_x = margin
        brand_font = _load_font("Cinzel-SemiBold.ttf", 26, weight=600)
        draw.text((text_x, sign_y + 10), "A U R Y A", font=brand_font,
                  fill=GOLD_LIGHT)

        # titolo SERIF (Playfair SemiBold), crema, ancorato in basso
        # sopra la firma: il respiro sta sopra, come nella card Masseria
        title_font = _load_font("PlayfairDisplay-Variable.ttf", 64,
                                weight=600)
        lines = _wrap_title(draw, title, title_font, WIDTH - margin * 2 - 60)
        line_h = 80
        y = sign_y - 52 - line_h * len(lines)
        y = max(y, 170)               # 4 righe lunghe: mai sopra l'overline
        for line in lines:
            draw.text((margin, y), line, font=title_font, fill=CREAM)
            y += line_h

        buf = BytesIO()
        img.convert("RGB").save(buf, format="WEBP", quality=82)
        return buf.getvalue()
    except Exception as exc:          # pragma: no cover - ambiente povero
        logger.warning("article_cover: generazione saltata (%s)", exc)
        return None
