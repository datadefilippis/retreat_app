"""AN6/DS2/SW4 — cover autogenerate per gli articoli del blog.

Ogni categoria ha la sua tonalità sopra la palette Aurya (Salvia
#376254 / Terracotta #C97B5D / Crema #F6F3EC) e la sua GEOMETRIA
SACRA (fiore della vita, vesica piscis, spirale aurea…), disegnata
con ImageDraw: zero dipendenze dai font per il segno.
In basso la firma: logo loto+sole + wordmark AURYA in Cinzel oro,
come nell'header del sito. Output WebP 1200×630 (OG-perfetto).
Best-effort by design: se Pillow o gli asset mancano, l'articolo
esce senza cover, mai un publish bloccato.

SW4 (31/7/2026) — VIA IL TITOLO DALL'IMMAGINE. La versione
precedente stampava il titolo dentro la cover: nella scheda grande
del Magazine il titolo compariva due volte (immagine + h3) e nelle
miniature da 128 px diventava un intrico illeggibile. La cover
torna a essere quello che deve essere, un SEGNO: medaglione con la
geometria della categoria, il nome della categoria, la firma.
Il titolo lo dice la pagina, non l'immagine; anche per og:image va
meglio così, perché la card social il titolo lo stampa da sé.

Composizione centrata, e non per gusto: la miniatura del kit
editoriale è 4:3 con `object-cover`, quindi di un 1200×630 mostra
solo la fascia centrale (≈840 px di larghezza). Tutto ciò che conta
sta dentro quella fascia; cornice e texture, che ne escono, sono
decorazione che a 128 px non serve.
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

# SW4 — le categorie EDITORIALI del Magazine (models/article.py:
# ARTICLE_EXTRA_CATEGORIES) non stanno nella tassonomia dei ritiri, ma
# hanno articoli e quindi copertine: prima cadevano tutte e tre sul
# ripiego salvia, cioè tre cover identiche. Vivono in un dizionario a
# parte perché CATEGORY_PALETTES e CATEGORY_GEOMETRY sono il calco
# esatto di RETREAT_CATEGORIES e devono restarlo.
EDITORIAL_PALETTES = {
    "ritiri":    ((96, 78, 50),   (172, 142, 88)),    # oro/ocra caldo
    "energia":   ((78, 62, 108),  (152, 132, 190)),
    "operatori": ((44, 74, 66),   (110, 142, 126)),   # salvia profondo
}

CREAM = (246, 243, 236)
GOLD_LIGHT = (214, 196, 154)


# ─── Geometrie sacre (line art, una per categoria) ─────────────────────
# `w` (spessore) e' un parametro: da SW4 il segno non e' piu' una
# filigrana d'angolo ma il soggetto della cover, e a 128 px un tratto
# da 3 px sparisce nel ridimensionamento.

def _circle(draw, cx, cy, r, color, w=3):
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), outline=color, width=w)


def _geo_lotus(draw, cx, cy, R, color, w=3):
    """Yoga — fiore di loto: petali come cerchi intersecati a raggiera."""
    for k in range(8):
        a = math.radians(k * 45)
        _circle(draw, cx + math.cos(a) * R * 0.45,
                cy + math.sin(a) * R * 0.45, R * 0.55, color, w)


def _geo_flower_of_life(draw, cx, cy, R, color, w=3):
    """Meditazione — fiore della vita: reticolo esagonale di cerchi."""
    r = R * 0.38
    _circle(draw, cx, cy, r, color, w)
    for ring, dist in ((6, r), (6, r * math.sqrt(3)), (6, 2 * r)):
        for k in range(ring):
            a = math.radians(k * 60 + (30 if dist == r * math.sqrt(3) else 0))
            _circle(draw, cx + math.cos(a) * dist, cy + math.sin(a) * dist,
                    r, color, w)


def _geo_seed_of_life(draw, cx, cy, R, color, w=3):
    """Detox — seme della vita: 7 cerchi, il germoglio di tutto."""
    r = R * 0.5
    _circle(draw, cx, cy, r, color, w)
    for k in range(6):
        a = math.radians(k * 60)
        _circle(draw, cx + math.cos(a) * r, cy + math.sin(a) * r, r, color, w)


def _geo_waves(draw, cx, cy, R, color, w=3):
    """Suono — cimatica: onde concentriche."""
    for k in range(1, 7):
        _circle(draw, cx, cy, R * k / 6, color, w)


def _geo_vesica(draw, cx, cy, R, color, w=3):
    """Massaggio — vesica piscis: due cerchi che si compenetrano."""
    r = R * 0.62
    _circle(draw, cx - r / 2, cy, r, color, w)
    _circle(draw, cx + r / 2, cy, r, color, w)
    _circle(draw, cx, cy, r * 1.55, color, w)


def _geo_spiral(draw, cx, cy, R, color, w=3):
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
        draw.line(pts, fill=color, width=w, joint="curve")


def _geo_hexagram(draw, cx, cy, R, color, w=3):
    """Cammini — due triangoli intrecciati nel cerchio: terra e cielo."""
    _circle(draw, cx, cy, R * 0.9, color, w)
    for rot in (0, 180):
        pts = []
        for k in range(3):
            a = math.radians(rot + 90 + k * 120)
            pts.append((cx + math.cos(a) * R * 0.78,
                        cy - math.sin(a) * R * 0.78))
        draw.polygon(pts, outline=color, width=w)


def _geo_triple_moon(draw, cx, cy, R, color, w=3):
    """Femminile — triplice luna: crescente, piena, calante."""
    r = R * 0.36
    _circle(draw, cx, cy, r, color, w)                    # luna piena
    for side in (-1, 1):
        x = cx + side * r * 1.7
        _circle(draw, x, cy, r * 0.78, color, w)
        _circle(draw, x + side * r * 0.4, cy, r * 0.7, color, w)


def _geo_metatron(draw, cx, cy, R, color, w=3):
    """Aziendale — cubo di Metatron semplificato: l'ordine nel cerchio."""
    _circle(draw, cx, cy, R * 0.92, color, w)
    verts = []
    for k in range(6):
        a = math.radians(k * 60 + 30)
        verts.append((cx + math.cos(a) * R * 0.72,
                      cy + math.sin(a) * R * 0.72))
    for i in range(6):
        for j in range(i + 1, 6):
            draw.line([verts[i], verts[j]], fill=color,
                      width=max(2, w - 2))
    for v in verts:
        _circle(draw, v[0], v[1], R * 0.1, color, w)


def _geo_circle_of_people(draw, cx, cy, R, color, w=3):
    """Ritiri — il cerchio: dodici presenze attorno allo stesso fuoco."""
    _circle(draw, cx, cy, R * 0.92, color, w)
    for k in range(12):
        a = math.radians(k * 30)
        _circle(draw, cx + math.cos(a) * R * 0.92,
                cy + math.sin(a) * R * 0.92, R * 0.1, color, w)


def _geo_rays(draw, cx, cy, R, color, w=3):
    """Energia — la raggiera: un centro e dodici direzioni."""
    _circle(draw, cx, cy, R * 0.34, color, w)
    _circle(draw, cx, cy, R * 0.95, color, max(2, w - 2))
    for k in range(12):
        a = math.radians(k * 30 + 15)
        draw.line([(cx + math.cos(a) * R * 0.46, cy + math.sin(a) * R * 0.46),
                   (cx + math.cos(a) * R * 0.84, cy + math.sin(a) * R * 0.84)],
                  fill=color, width=w)


def _geo_square_in_circle(draw, cx, cy, R, color, w=3):
    """Operatori — il quadrato nel cerchio: il mestiere dentro la pratica."""
    _circle(draw, cx, cy, R * 0.92, color, w)
    _circle(draw, cx, cy, R * 0.3, color, w)
    pts = [(cx + math.cos(math.radians(k * 90 + 45)) * R * 0.92,
            cy + math.sin(math.radians(k * 90 + 45)) * R * 0.92)
           for k in range(4)]
    draw.polygon(pts, outline=color, width=w)


def _geo_aura(draw, cx, cy, R, color, w=3):
    """Default — l'aura del logo: cerchi concentrici."""
    for k in (1.0, 0.75, 0.5, 0.25):
        _circle(draw, cx, cy, R * k, color, w)


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

EDITORIAL_GEOMETRY = {
    "ritiri": _geo_circle_of_people,
    "energia": _geo_rays,
    "operatori": _geo_square_in_circle,
}


def palette_for(category: Optional[str]):
    """La tonalità della categoria, ritiri o editoriale che sia."""
    key = category or ""
    return (CATEGORY_PALETTES.get(key)
            or EDITORIAL_PALETTES.get(key)
            or _DEFAULT_PALETTE)


def geometry_for(category: Optional[str]):
    """Il segno della categoria; l'aura del logo per tutto il resto."""
    key = category or ""
    return (CATEGORY_GEOMETRY.get(key)
            or EDITORIAL_GEOMETRY.get(key)
            or _geo_aura)


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
    """Gradiente radiale dall'alto al centro: SW4 lo sposta dal
    quadrante alto-destro all'asse centrale, perché adesso la
    composizione è simmetrica e nella miniatura 4:3 si vede solo la
    fascia di mezzo (un bagliore laterale li' finiva tagliato via)."""
    from PIL import Image
    cx, cy = WIDTH * 0.5, HEIGHT * 0.16
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


# ── L'ETICHETTA DI CATEGORIA ─────────────────────────────────────────
# Cinzel spaziato, centrata. "Meditazione & Mindfulness" spaziata a 30
# px sarebbe larga quasi quanto la tela: il corpo scende finché la riga
# non sta nella misura, invece di andare a capo o sbordare.
_OVERLINE_SIZES = (30, 27, 24, 21, 18)
_OVERLINE_MAX_W = 860


def _fit_overline(draw, text: str):
    spaced = " ".join(text)
    for size in _OVERLINE_SIZES:
        font = _load_font("Cinzel-SemiBold.ttf", size, weight=600)
        if draw.textlength(spaced, font=font) <= _OVERLINE_MAX_W:
            return font, spaced
    return font, spaced                # l'ultimo corpo disponibile


# Il medaglione: dove sta e quanto è grande. Tutto dentro la fascia
# centrale 4:3 (x da 180 a 1020), quella che sopravvive alla miniatura.
_MEDAL_CY = 248
_MEDAL_R = 172
_GLYPH_R = 112
_GLYPH_W = 5


def render_article_cover(title: Optional[str] = None,
                         category: Optional[str] = None,
                         category_label: Optional[str] = None) -> Optional[bytes]:
    """Rende la cover come bytes WebP, o None se l'ambiente non può
    (Pillow/font assenti): il chiamante NON deve mai fallire per noi.

    `title` NON viene stampato: resta nella firma solo perché qualche
    chiamante lo passa ancora posizionalmente. Il titolo lo dice la
    pagina (h1, h3 della scheda, card social); dentro l'immagine era
    un doppione a 1200 px e un intrico a 128.

    Design v3 (SW4) — un SIGILLO, non un manifesto:
      fondo radiale della categoria, texture a puntini e cornice doppia
      incisa (continuità con la v2), poi al centro il MEDAGLIONE: disco
      crema appena acceso, anello, e dentro la geometria sacra della
      categoria a tratto pieno. Sotto, il nome della categoria in
      Cinzel oro spaziato; in fondo la firma logo + wordmark.
    Tutti gli elementi delicati passano da un layer RGBA così
    l'opacità è controllata davvero (niente linee grezze)."""
    try:
        from PIL import Image, ImageDraw

        base, glow = palette_for(category)
        img = _radial_background(base, glow).convert("RGBA")
        cx = WIDTH // 2

        # ── layer delicato: texture, cornice, medaglione (con alpha) ──
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

        # il disco: un alone crema al 12%. E' lui a far leggere la cover
        # da lontano, quando il tratto della geometria si assottiglia
        # sotto il pixel: a 128 px resta un cerchio chiaro su fondo
        # scuro, e quello si riconosce sempre.
        fdraw.ellipse((cx - _MEDAL_R, _MEDAL_CY - _MEDAL_R,
                       cx + _MEDAL_R, _MEDAL_CY + _MEDAL_R),
                      fill=CREAM + (30,))
        fdraw.ellipse((cx - _MEDAL_R, _MEDAL_CY - _MEDAL_R,
                       cx + _MEDAL_R, _MEDAL_CY + _MEDAL_R),
                      outline=CREAM + (120,), width=3)

        # la geometria sacra della categoria: al centro, tratto pieno
        geometry = geometry_for(category)
        geometry(fdraw, cx, _MEDAL_CY, _GLYPH_R, CREAM + (232,), _GLYPH_W)

        img = Image.alpha_composite(img, fine)
        draw = ImageDraw.Draw(img)

        # la categoria sotto il medaglione (o il marchio, se l'articolo
        # non ne ha una): e' l'unica parola della cover.
        from core.brand import BRAND_NAME
        over_font, spaced = _fit_overline(
            draw, (category_label or BRAND_NAME).upper())
        draw.text((cx, 468), spaced, font=over_font, fill=GOLD_LIGHT,
                  anchor="mm")

        # firma in fondo: lineetta oro, poi logo + wordmark centrati
        draw.line((cx - 46, 516, cx + 46, 516), fill=GOLD_LIGHT, width=2)
        brand_font = _load_font("Cinzel-SemiBold.ttf", 24, weight=600)
        wordmark = "A U R Y A"
        text_w = draw.textlength(wordmark, font=brand_font)
        logo_size, gap = 38, 14
        logo = None
        try:
            logo = Image.open(_LOGO_PATH).convert("RGBA")
            logo.thumbnail((logo_size, logo_size), Image.LANCZOS)
        except Exception:             # senza logo la firma resta il wordmark
            logo = None
        block_w = text_w + (logo.width + gap if logo else 0)
        x = cx - block_w / 2
        if logo:
            img.paste(logo, (round(x), 560 - logo.height // 2), logo)
            x += logo.width + gap
        draw.text((x, 560), wordmark, font=brand_font, fill=GOLD_LIGHT,
                  anchor="lm")

        buf = BytesIO()
        img.convert("RGB").save(buf, format="WEBP", quality=82)
        return buf.getvalue()
    except Exception as exc:          # pragma: no cover - ambiente povero
        logger.warning("article_cover: generazione saltata (%s)", exc)
        return None
