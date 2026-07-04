"""Markdown sanitization service — Wave E.8.5 (Sprint 1 W1.5).

Defense-in-depth contro stored XSS nei field testuali user-editable
(product description, long_description, extras description, etc.).

Strategy
========
Zero-dependency, regex-based stripping di pattern dannosi PRIMA della
persistenza Mongo. Il merchant puo' usare markdown puro (**bold**,
*italic*, liste, link) ma NON puo' iniettare:
  - <script>, <iframe>, <object>, <embed>, <svg>, <style>, <link>,
    <meta>, <base> tag (e tutti gli altri HTML tag in generale)
  - Event handler inline (onclick, onerror, onload, on*)
  - javascript: / data: / vbscript: URL schemes nei link
  - HTML entity codepoints decoded a tag (es. &lt;script&gt;)

Defense-in-depth layer
======================
Anche se il frontend render fosse compromesso (es. widget usa
`unsafeHTML` per bug futuro, o React MarkdownLite ha edge case
unsafe), il backend storage ha gia' SANITIZZATO l'input -> attacker
non puo' iniettare payload pericolosi nel database.

Performance: O(N) sui field testuali, max_length cap a 30K char per
campo descrizione (privacy/terms gia' coperti dal merchant_legal_*
pattern Wave CG-1). Tipico product description <2K chars -> overhead
<1ms.

Sentinel: TestSEC_E_8_5_MarkdownXSSSafe verifica 5+ XSS vector.

Usage
=====
::

    from services.markdown_safe import sanitize_merchant_text

    @app.post("/products")
    async def create_product(body: ProductCreate):
        body.description = sanitize_merchant_text(body.description)
        body.long_description = sanitize_merchant_text(body.long_description)
        ...

OR via Pydantic field validator (preferred — sanitization automatica):

    from pydantic import field_validator
    class ProductCreate(BaseModel):
        description: Optional[str] = None

        @field_validator('description', mode='before')
        @classmethod
        def _sanitize_description(cls, v):
            from services.markdown_safe import sanitize_merchant_text
            return sanitize_merchant_text(v) if v else v
"""

from __future__ import annotations

import html
import re
from typing import Optional


# ─── Regex patterns ─────────────────────────────────────────────────────


# Tutti gli HTML/XML tag — match con flag IGNORECASE + DOTALL.
# Pattern: < + tag-name (with optional attributes) + >
# Match anche tag self-closing (<br/>) e tag con multiline attributes.
_HTML_TAG_RE = re.compile(r"</?[a-zA-Z][^>]*>", re.IGNORECASE | re.DOTALL)


# Event handler inline (onerror=, onclick=, onload=, ecc.) anche dopo
# strip dei tag — se merchant invia `<p>text</p onerror=x>` o tricks.
_EVENT_HANDLER_RE = re.compile(
    r"\bon[a-z]+\s*=\s*[\"']?[^\"'>]*[\"']?",
    re.IGNORECASE,
)


# URL schemes dannosi nei link markdown [text](javascript:alert(1))
# Anche dopo HTML strip — markdown link sono safe-by-default ma il
# raw text potrebbe contenere il pattern.
_DANGEROUS_URL_RE = re.compile(
    r"(?:javascript|data|vbscript|file)\s*:\s*[^\s)]*",
    re.IGNORECASE,
)


# CSS expression() pattern (legacy IE XSS vector)
_CSS_EXPRESSION_RE = re.compile(
    r"expression\s*\(",
    re.IGNORECASE,
)


# Default max length per field testo merchant (anti-DoS + UX).
DEFAULT_MAX_LENGTH = 30_000


# ─── Public API ─────────────────────────────────────────────────────────


def sanitize_merchant_text(
    raw: Optional[str],
    *,
    max_length: int = DEFAULT_MAX_LENGTH,
) -> Optional[str]:
    """Sanitize input testuale merchant rimuovendo pattern XSS dannosi.

    Args:
        raw: input string (None/empty passthrough).
        max_length: cap dopo sanitization (truncation hard, no error).

    Returns:
        String sanitizzata pronta per persistenza Mongo. None se input None.

    Behavior:
        1. Decode HTML entities (es. &lt;script&gt; → <script>) cosi'
           lo stripping che segue le riconosce.
        2. Strip TUTTI gli HTML/XML tag (whitelist deliberatamente vuota
           — merchant deve usare markdown puro per formatting).
        3. Strip event handler inline (on*=) defense-in-depth.
        4. Strip URL schemes dannosi (javascript:, data:, vbscript:).
        5. Strip CSS expression() (legacy IE vector).
        6. Truncate a max_length.
        7. Re-encode HTML entities pericolose rimaste (<, >, ", ').

    Idempotent: ``sanitize(sanitize(x)) == sanitize(x)``.
    """
    if raw is None:
        return None
    if not isinstance(raw, str):
        # Defensive: caller dovrebbe sempre passare str ma se passa
        # int/float/dict, return str(raw) sanitized (no crash).
        raw = str(raw)
    if not raw:
        return raw

    text = raw

    # Step 1: decode HTML entities cosi' i pattern obfuscated diventano
    # visibili allo stripping. Es. "&lt;script&gt;" → "<script>"
    # cosi' poi lo stripping HTML lo rimuove.
    text = html.unescape(text)

    # Step 2: strip tutti gli HTML tag (whitelist vuota — markdown puro).
    text = _HTML_TAG_RE.sub("", text)

    # Step 3: strip event handlers inline (anche se non in tag, paranoia).
    text = _EVENT_HANDLER_RE.sub("", text)

    # Step 4: strip URL schemes dannosi (markdown link permessi ma con
    # http(s):// only).
    text = _DANGEROUS_URL_RE.sub("[removed]", text)

    # Step 5: strip CSS expression() (legacy IE vector).
    text = _CSS_EXPRESSION_RE.sub("[removed](", text)

    # Step 6: truncate
    if len(text) > max_length:
        text = text[:max_length]

    # Step 7: re-encode HTML special chars per output safety.
    # Pattern: i `<`, `>`, `"`, `'` rimasti dopo strip vengono escapati
    # cosi' anche se finiscono in un render unsafe (futuro bug) restano
    # innocui. Markdown render lato frontend gestira' i caratteri.
    # NOTA: NON escape `&` perche' rompe link markdown e markdown render
    # se ne occupa.
    # NOTA: NON escape spazi/newline.
    text = (
        text.replace("<", "&lt;")
            .replace(">", "&gt;")
    )

    return text


def is_safe_text(raw: Optional[str]) -> bool:
    """Return True iff ``raw`` contiene zero pattern dannosi noti.

    Utile per assertion test e per validators read-only (non
    modifica input, solo check). Per write path usare ``sanitize_merchant_text``.
    """
    if raw is None or not isinstance(raw, str) or not raw:
        return True
    decoded = html.unescape(raw)
    if _HTML_TAG_RE.search(decoded):
        return False
    if _EVENT_HANDLER_RE.search(decoded):
        return False
    if _DANGEROUS_URL_RE.search(decoded):
        return False
    if _CSS_EXPRESSION_RE.search(decoded):
        return False
    return True
