"""SE1 — markdown → HTML per il body della shell SEO.

PERCHE'. La shell serviva head perfetto e body VUOTO (108 byte,
`<div id="root">`): l'articolo esisteva solo nel bundle JS e
nell'articleBody del JSON-LD. Google lo indicizza via rendering
(seconda ondata, piu' lento e costoso su un dominio senza storia);
Bing e i crawler AI (GPTBot, ClaudeBot, PerplexityBot) spesso non
eseguono JS: per loro le pagine erano vuote. Questo modulo rende il
contenuto visibile nell'HTML iniziale; React monta sopra e sostituisce.

COSA RENDE. Il SOTTOINSIEME che gli articoli usano davvero (misurato
su tutti i 33: h2/h3, grassetto, corsivo, link, liste puntate e
numerate, un blockquote). Niente tabelle, immagini o codice: se un
giorno serviranno, si aggiungono qui e la guardia di parita' con il
renderer client (test_seo_shell) lo pretendera'.

SICUREZZA. Il testo viene escapato PRIMA di ogni conversione: il
contenuto e' nostro, ma la regola non fa eccezioni. I link ammessi
sono solo percorsi interni, https e mailto (stessa whitelist del
renderer client).
"""
import html as _html
import re

_LINK_RE = re.compile(r"\[([^\]]+)\]\(((?:/|https?://|mailto:)[^)\s]+)\)")
_BOLD_RE = re.compile(r"\*\*([^*]+)\*\*")
_ITALIC_RE = re.compile(r"(?<!\*)\*([^*\n]+)\*(?!\*)")
_ULIST_RE = re.compile(r"^[-*]\s+")
_OLIST_RE = re.compile(r"^\d+[.)]\s+")


def _inline(text: str) -> str:
    """Inline markdown su testo GIA' escapato."""
    def _link(m):
        label, href = m.group(1), m.group(2)
        # l'escape ha trasformato & in &amp; dentro l'href: va bene
        # anche nell'attributo. Solo interni/https/mailto (regex).
        return f'<a href="{href}">{label}</a>'
    text = _LINK_RE.sub(_link, text)
    text = _BOLD_RE.sub(r"<strong>\1</strong>", text)
    text = _ITALIC_RE.sub(r"<em>\1</em>", text)
    return text


def render_markdown(md: str) -> str:
    """Il documento, blocco per blocco. Stessa segmentazione del
    renderer client: righe vuote separano i blocchi, le liste
    raggruppano righe consecutive."""
    out: list[str] = []
    lines = _html.escape(md or "").split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        m = re.match(r"^(#{2,3})\s+(.+)$", line)
        if m:
            tag = f"h{len(m.group(1))}"
            out.append(f"<{tag}>{_inline(m.group(2))}</{tag}>")
            i += 1
            continue
        if line.startswith("&gt; "):
            quote = []
            while i < len(lines) and lines[i].startswith("&gt; "):
                quote.append(lines[i][5:])
                i += 1
            out.append(f"<blockquote><p>{_inline(' '.join(quote))}</p></blockquote>")
            continue
        if _ULIST_RE.match(line):
            items = []
            while i < len(lines) and _ULIST_RE.match(lines[i]):
                items.append(f"<li>{_inline(_ULIST_RE.sub('', lines[i]))}</li>")
                i += 1
            out.append("<ul>" + "".join(items) + "</ul>")
            continue
        if _OLIST_RE.match(line):
            items = []
            while i < len(lines) and _OLIST_RE.match(lines[i]):
                items.append(f"<li>{_inline(_OLIST_RE.sub('', lines[i]))}</li>")
                i += 1
            out.append("<ol>" + "".join(items) + "</ol>")
            continue
        # paragrafo: righe consecutive non speciali
        para = []
        while (i < len(lines) and lines[i].strip()
               and not re.match(r"^#{2,3}\s", lines[i])
               and not _ULIST_RE.match(lines[i])
               and not _OLIST_RE.match(lines[i])
               and not lines[i].startswith("&gt; ")):
            para.append(lines[i])
            i += 1
        if para:
            out.append(f"<p>{_inline(' '.join(para))}</p>")
    return "".join(out)
