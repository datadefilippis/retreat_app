"""Impagina un Markdown della casa (titoli, paragrafi, elenchi, tabelle,
blocchi di codice, citazioni, grassetto/corsivo) in un PDF leggibile.

Uso: venv/bin/python scripts/md_in_pdf.py docs/FILE.md out.pdf
Solo reportlab: niente pandoc, niente weasyprint sulla macchina.
"""
import re
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (KeepTogether, PageBreak, Paragraph, Preformatted,
                                SimpleDocTemplate, Spacer, Table, TableStyle)

FONT_DIR = Path("/Library/Fonts")
SUPP = Path("/System/Library/Fonts/Supplemental")


def _font(name, files):
    for d in (FONT_DIR, SUPP):
        for f in files:
            p = d / f
            if p.exists():
                pdfmetrics.registerFont(TTFont(name, str(p)))
                return True
    return False


_font("Corpo", ["Arial.ttf", "Arial Unicode.ttf"])
_font("CorpoB", ["Arial Bold.ttf", "Arial.ttf"])
_font("CorpoI", ["Arial Italic.ttf", "Arial.ttf"])
_font("CorpoBI", ["Arial Bold Italic.ttf", "Arial Bold.ttf"])
_font("Titoli", ["Georgia Bold.ttf", "Georgia.ttf", "Arial Bold.ttf"])
_font("TitoliR", ["Georgia.ttf", "Arial.ttf"])
from reportlab.pdfbase.pdfmetrics import registerFontFamily
registerFontFamily("Corpo", normal="Corpo", bold="CorpoB", italic="CorpoI", boldItalic="CorpoBI")

SALVIA = colors.HexColor("#4b6b5a")
TERRA = colors.HexColor("#8a6a3c")
GRIGIO = colors.HexColor("#555555")
RIGA = colors.HexColor("#d9d4c7")
FONDO = colors.HexColor("#f4f1ea")

S = {
    "h1": ParagraphStyle("h1", fontName="Titoli", fontSize=22, leading=27, spaceBefore=6, spaceAfter=10, textColor=SALVIA),
    "h2": ParagraphStyle("h2", fontName="Titoli", fontSize=15, leading=19, spaceBefore=16, spaceAfter=6, textColor=SALVIA),
    "h3": ParagraphStyle("h3", fontName="CorpoB", fontSize=11.5, leading=15, spaceBefore=11, spaceAfter=4, textColor=TERRA),
    "sub": ParagraphStyle("sub", fontName="TitoliR", fontSize=13, leading=17, spaceAfter=8, textColor=GRIGIO),
    "meta": ParagraphStyle("meta", fontName="CorpoI", fontSize=9.5, leading=13, spaceAfter=14, textColor=GRIGIO),
    "p": ParagraphStyle("p", fontName="Corpo", fontSize=10, leading=14.5, spaceAfter=6, alignment=TA_LEFT),
    "li": ParagraphStyle("li", fontName="Corpo", fontSize=10, leading=14.5, leftIndent=14, bulletIndent=3, spaceAfter=3),
    "quote": ParagraphStyle("quote", fontName="CorpoI", fontSize=10, leading=14.5, leftIndent=12, textColor=GRIGIO, backColor=FONDO, borderPadding=(5, 6, 5, 6), spaceAfter=8),
    "cell": ParagraphStyle("cell", fontName="Corpo", fontSize=8.6, leading=11.5),
    "cellh": ParagraphStyle("cellh", fontName="CorpoB", fontSize=8.6, leading=11.5, textColor=colors.white),
    "code": ParagraphStyle("code", fontName="Courier", fontSize=8.2, leading=10.5, backColor=FONDO, borderPadding=(6, 6, 6, 6), spaceAfter=8),
}


def inline(t):
    t = t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<i>\1</i>", t)
    t = re.sub(r"`([^`]+)`", r"<font face='Courier' size='8.6'>\1</font>", t)
    t = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1", t)
    return t


def tabella(righe, larghezza):
    celle = [[c.strip() for c in r.strip().strip("|").split("|")] for r in righe if not re.match(r"^\s*\|?\s*:?-{2,}", r)]
    if not celle:
        return None
    n = max(len(r) for r in celle)
    celle = [r + [""] * (n - len(r)) for r in celle]
    pesi = [max(len(r[i]) for r in celle) for i in range(n)]
    pesi = [max(p, 6) ** 0.7 for p in pesi]
    tot = sum(pesi)
    cols = [larghezza * p / tot for p in pesi]
    dati = [[Paragraph(inline(c), S["cellh"] if i == 0 else S["cell"]) for c in r] for i, r in enumerate(celle)]
    t = Table(dati, colWidths=cols, repeatRows=1)
    st = [("BACKGROUND", (0, 0), (-1, 0), SALVIA), ("VALIGN", (0, 0), (-1, -1), "TOP"),
          ("LINEBELOW", (0, 0), (-1, -1), 0.4, RIGA), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
          ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5)]
    for i in range(1, len(dati)):
        if i % 2 == 0:
            st.append(("BACKGROUND", (0, i), (-1, i), FONDO))
    t.setStyle(TableStyle(st))
    return t


def converti(md, out):
    doc = SimpleDocTemplate(out, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm, topMargin=18 * mm, bottomMargin=18 * mm,
                            title=Path(md).stem, author="Aurya")
    larg = A4[0] - 40 * mm
    righe = Path(md).read_text(encoding="utf-8").splitlines()
    story, i, primo_h1 = [], 0, True
    par = []

    def flush():
        nonlocal par
        if par:
            story.append(Paragraph(inline(" ".join(par)), S["p"]))
            par = []

    while i < len(righe):
        r = righe[i]
        if r.startswith("```"):
            flush(); j = i + 1; blocco = []
            while j < len(righe) and not righe[j].startswith("```"):
                blocco.append(righe[j]); j += 1
            story.append(Preformatted("\n".join(blocco), S["code"])); i = j + 1; continue
        if r.strip().startswith("|"):
            flush(); j = i; blocco = []
            while j < len(righe) and righe[j].strip().startswith("|"):
                blocco.append(righe[j]); j += 1
            t = tabella(blocco, larg)
            if t is not None:
                story.append(t); story.append(Spacer(1, 8))
            i = j; continue
        if r.strip() == "---":
            flush(); story.append(Spacer(1, 6)); i += 1; continue
        m = re.match(r"^(#{1,3})\s+(.*)", r)
        if m:
            flush(); liv = len(m.group(1)); testo = inline(m.group(2))
            if liv == 1:
                if not primo_h1:
                    story.append(PageBreak())
                story.append(Paragraph(testo, S["h1"])); primo_h1 = False
            elif liv == 2:
                # il sottotitolo del documento, subito dopo il primo h1
                stile = S["sub"] if len(story) == 1 else S["h2"]
                story.append(Paragraph(testo, stile))
            else:
                story.append(Paragraph(testo, S["h3"]))
            i += 1; continue
        m = re.match(r"^\s*[-*]\s+(.*)", r)
        if m:
            flush(); story.append(Paragraph(inline(m.group(1)), S["li"], bulletText="•")); i += 1; continue
        m = re.match(r"^\s*(\d+)\.\s+(.*)", r)
        if m:
            flush(); story.append(Paragraph(inline(m.group(2)), S["li"], bulletText=f"{m.group(1)}.")); i += 1; continue
        if r.startswith(">"):
            flush(); j = i; blocco = []
            while j < len(righe) and righe[j].startswith(">"):
                blocco.append(righe[j].lstrip("> ").rstrip()); j += 1
            story.append(Paragraph("<br/>".join(inline(x) for x in blocco), S["quote"])); i = j; continue
        if r.strip() == "":
            flush()
            if len(story) == 2 and isinstance(story[-1], Paragraph) and story[-1].style is S["sub"]:
                pass
            i += 1; continue
        # riga di meta (autori/data) subito dopo il sottotitolo
        if len(story) == 2 and story[-1].style is S["sub"]:
            story.append(Paragraph(inline(r), S["meta"])); i += 1; continue
        par.append(r.strip()); i += 1
    flush()

    def piede(canvas, d):
        canvas.saveState(); canvas.setFont("Corpo", 8); canvas.setFillColor(GRIGIO)
        canvas.drawString(20 * mm, 11 * mm, "Aurya · settembre 2026")
        canvas.drawRightString(A4[0] - 20 * mm, 11 * mm, str(d.page)); canvas.restoreState()

    doc.build(story, onFirstPage=piede, onLaterPages=piede)


if __name__ == "__main__":
    converti(sys.argv[1], sys.argv[2])
    print("scritto", sys.argv[2])
