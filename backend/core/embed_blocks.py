"""
Embed Block Catalog — Embed à-la-carte, Fase 0 (2026-06-19).

Single source of truth (lato backend) per i "blocchi embeddabili" che il
merchant puo' comporre dalla pagina "Condividi store". UI builder e snippet
generato derivano TUTTI da questo catalogo: aggiungere un blocco = una voce
qui, nessun refactor altrove.

Vedi `docs/EMBED_ALACARTE_PLAN.md`.

Due stili di snippet
====================
1. **full** (legacy, retrocompatibile): lo store intero wrappato in
   `<afianco-storefront-init>` — identico byte-per-byte a
   ``embed_distribution.generate_embed_snippet`` (sentinel-pinned dal test
   ``test_embed_blocks``). Questo modulo NON ridefinisce quel formato: lo
   importa e lo espone come preset, cosi' resta una sola fonte di verita'.

2. **à-la-carte**: elementi singoli (carrello, account, categorie, singolo
   prodotto) montabili ovunque. Si appoggiano al futuro "Store Kernel"
   per-slug (Fase 1): un'unica config di pagina via
   ``<script ... data-afianco-slug="...">`` evita di ripetere lo slug su
   ogni elemento.

   NOTA: i custom element à-la-carte (``afianco-cart-button``,
   ``afianco-account-button``, ``afianco-product``) e l'attributo
   ``categories`` sulla grid vengono implementati nelle Fasi 1-2. In Fase 0
   questo modulo CONGELA il vocabolario e il formato dello snippet; gli
   snippet generati diventano funzionanti quando l'SDK li supporta.

Sicurezza
=========
- ``slug`` validato upstream (Pydantic ``Store.slug``: 3-50 char,
  alphanumeric+hyphen). Qui si ri-valida difensivamente lo slug e si
  sanifica ogni valore di config (category slug, product id) prima di
  interpolarlo in un attributo HTML.
- Nessun input utente libero finisce nel markup senza whitelist/escape.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass, field
from typing import Callable, Optional

from core.embed_distribution import (
    generate_embed_snippet,
    get_embed_bundle_url,
)


# ── Validazione difensiva degli identificatori interpolati ───────────────
#
# Mirror del contract Store.slug + product/category id. Qualsiasi valore che
# non matcha viene scartato (mai interpolato grezzo nel markup).

_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{2,49}$")
_CATEGORY_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
# Product id: UUID-like o mongo ObjectId-like. Conservativo: alfanumerico +
# hyphen, 1-64 char. (Gli id reali sono validati per esistenza a monte dal
# router; questa e' solo difesa anti-injection sul markup.)
_PRODUCT_ID_RE = re.compile(r"^[A-Za-z0-9-]{1,64}$")


def _sanitize_slug(slug: str) -> str:
    if not slug or not _SLUG_RE.match(slug):
        raise ValueError(f"Invalid store slug: {slug!r}")
    return slug


def _sanitize_category_slugs(values: list[str]) -> list[str]:
    out: list[str] = []
    for v in values or []:
        v = (v or "").strip().lower()
        if v and _CATEGORY_SLUG_RE.match(v) and v not in out:
            out.append(v)
    return out


def _sanitize_product_id(value: str) -> str:
    value = (value or "").strip()
    if not value or not _PRODUCT_ID_RE.match(value):
        raise ValueError(f"Invalid product id: {value!r}")
    return value


# ── Config field spec (descrive cosa il builder deve chiedere) ───────────


@dataclass(frozen=True)
class ConfigField:
    """Un input di configurazione richiesto da un blocco (per il builder UI)."""

    key: str
    type: str  # "category_multi" | "product"
    label: str
    required: bool = True


# ── Block spec ───────────────────────────────────────────────────────────


@dataclass(frozen=True)
class BlockSpec:
    """Voce dichiarativa del catalogo.

    Attributi
    ---------
    id        identificatore stabile del blocco (contract con frontend).
    label     etichetta umana (IT) per il builder.
    description breve spiegazione mostrata nel builder.
    group     "menu" | "content" | "singleton" | "preset".
              menu/content = selezionabili; singleton = montati una volta
              (auto-aggiunti via ``requires``); preset = "tutto lo store".
    needs     config richiesta (ConfigField[]).
    requires  id di blocchi singleton da montare una volta (dedup).
    render    funzione (slug, config) -> HTML degli elementi del blocco.
              Per i singleton, ``config`` e' tipicamente vuota.
    """

    id: str
    label: str
    description: str
    group: str
    render: Callable[[str, dict], str]
    needs: tuple[ConfigField, ...] = ()
    requires: tuple[str, ...] = ()
    selectable: bool = True  # appare nella checklist del builder


# ── Render helpers per i singoli elementi ────────────────────────────────


def _r_cart_button(slug: str, config: dict) -> str:
    return "<afianco-cart-button></afianco-cart-button>"


def _r_account_button(slug: str, config: dict) -> str:
    return "<afianco-account-button></afianco-account-button>"


def _r_categories(slug: str, config: dict) -> str:
    cats = _sanitize_category_slugs(config.get("categories") or [])
    if not cats:
        # Nessuna categoria scelta = griglia completa con nav filtri.
        return "<afianco-product-grid show-filter-nav></afianco-product-grid>"
    # Una griglia per categoria selezionata, usando l'attributo `category`
    # (gia' supportato dalla grid). Cosi' "un gruppo di categorie" funziona
    # SUBITO, senza dipendere da un nuovo parametro backend.
    return "\n".join(
        f'<afianco-product-grid category="{html.escape(c, quote=True)}"></afianco-product-grid>'
        for c in cats
    )


def _r_product(slug: str, config: dict) -> str:
    pid = _sanitize_product_id(config.get("product_id") or "")
    attr = html.escape(pid, quote=True)
    return f'<afianco-product product-id="{attr}"></afianco-product>'


def _r_newsletter(slug: str, config: dict) -> str:
    # F2 — form newsletter (autonomo, identità = form_id). Lo slug store NON
    # è usato dal component: il form è org-scoped e può vivere standalone.
    fid = (config.get("form_id") or "").strip()
    if not fid or not _PRODUCT_ID_RE.match(fid):
        raise ValueError(f"Invalid newsletter form id: {fid!r}")
    attr = html.escape(fid, quote=True)
    return f'<afianco-newsletter-form form-id="{attr}"></afianco-newsletter-form>'


def _r_singleton_cart(slug: str, config: dict) -> str:
    # Drawer carrello + bottone checkout (orchestrano insieme via event bus).
    return (
        "<afianco-cart-drawer hide-trigger></afianco-cart-drawer>\n"
        "<afianco-checkout-button></afianco-checkout-button>"
    )


def _r_singleton_account(slug: str, config: dict) -> str:
    return "<afianco-account hide-trigger></afianco-account>"


def _r_singleton_product_detail(slug: str, config: dict) -> str:
    return "<afianco-product-detail></afianco-product-detail>"


def _r_full(slug: str, config: dict) -> str:
    # Preset legacy: delega all'unica fonte di verita' esistente.
    return generate_embed_snippet(slug)


# ── Catalogo ──────────────────────────────────────────────────────────────

_BLOCK_LIST: tuple[BlockSpec, ...] = (
    # Preset "tutto lo store" (stile legacy, wrapper-based).
    BlockSpec(
        id="full",
        label="Tutto lo store",
        description="Lo store completo: header, prodotti, carrello, account, checkout.",
        group="preset",
        render=_r_full,
    ),
    # ── Elementi per il menu ──
    BlockSpec(
        id="cart-button",
        label="Carrello (menu)",
        description="Icona carrello con badge, da mettere nel menu del sito.",
        group="menu",
        render=_r_cart_button,
        requires=("cart",),
    ),
    BlockSpec(
        id="account-button",
        label="Account utente (menu)",
        description="Pulsante login/area personale, da mettere nel menu.",
        group="menu",
        render=_r_account_button,
        requires=("account",),
    ),
    # ── Elementi di contenuto ──
    BlockSpec(
        id="categories",
        label="Categorie / prodotti",
        description="Griglia prodotti, opzionalmente filtrata su una o piu' categorie.",
        group="content",
        render=_r_categories,
        needs=(
            ConfigField(
                key="categories",
                type="category_multi",
                label="Categorie (vuoto = tutte)",
                required=False,
            ),
        ),
        requires=("product-detail", "cart"),
    ),
    BlockSpec(
        id="product",
        label="Singolo prodotto",
        description="Un singolo prodotto renderizzato inline in una pagina.",
        group="content",
        render=_r_product,
        needs=(
            ConfigField(
                key="product_id",
                type="product",
                label="Prodotto",
                required=True,
            ),
        ),
        requires=("product-detail", "cart"),
    ),
    BlockSpec(
        id="newsletter",
        label="Form newsletter",
        description="Modulo di iscrizione newsletter (autonomo, nessun carrello richiesto).",
        group="content",
        render=_r_newsletter,
        needs=(
            ConfigField(
                key="form_id",
                type="newsletter_form",
                label="Form newsletter",
                required=True,
            ),
        ),
        # Nessun singleton richiesto: il form è self-contained.
    ),
    # ── Singleton (montati una volta, auto-aggiunti via requires) ──
    BlockSpec(
        id="cart",
        label="Sistema carrello",
        description="Drawer carrello + checkout. Va incluso una sola volta.",
        group="singleton",
        render=_r_singleton_cart,
        selectable=False,
    ),
    BlockSpec(
        id="account",
        label="Drawer account",
        description="Pannello login/registrazione/area personale. Una sola volta.",
        group="singleton",
        render=_r_singleton_account,
        selectable=False,
    ),
    BlockSpec(
        id="product-detail",
        label="Dettaglio prodotto",
        description="Drawer di dettaglio aperto al click su una card. Una sola volta.",
        group="singleton",
        render=_r_singleton_product_detail,
        selectable=False,
    ),
)

BLOCKS: dict[str, BlockSpec] = {b.id: b for b in _BLOCK_LIST}


# ── API pubblica ───────────────────────────────────────────────────────────


def get_blocks_catalog() -> list[dict]:
    """Catalogo serializzabile per il frontend builder.

    Espone solo i blocchi *selezionabili* (menu/content/preset); i singleton
    sono dettaglio implementativo risolto dal generatore.
    """
    out: list[dict] = []
    for b in _BLOCK_LIST:
        if not b.selectable:
            continue
        out.append(
            {
                "id": b.id,
                "label": b.label,
                "description": b.description,
                "group": b.group,
                "needs": [
                    {
                        "key": f.key,
                        "type": f.type,
                        "label": f.label,
                        "required": f.required,
                    }
                    for f in b.needs
                ],
            }
        )
    return out


@dataclass(frozen=True)
class ComposedSnippet:
    """Risultato della composizione à-la-carte, in 3 sezioni guidate."""

    head: str  # <script ... data-afianco-slug> — una volta, nel <head>
    elements: tuple[dict, ...]  # {id, label, html} — incolla dove vuoi
    singletons: tuple[dict, ...]  # {id, label, html} — una volta, a fine pagina
    snippet: str  # tutto insieme, pronto da copiare


def _resolve_singletons(selected_ids: list[str]) -> list[str]:
    """Espande i ``requires`` dei blocchi scelti in lista singleton dedup,
    nell'ordine canonico del catalogo (output stabile)."""
    needed: set[str] = set()
    for sid in selected_ids:
        spec = BLOCKS.get(sid)
        if spec:
            needed.update(spec.requires)
    # ordine canonico = ordine nel catalogo
    return [b.id for b in _BLOCK_LIST if b.id in needed]


def compose_alacarte(
    slug: str,
    selected_ids: list[str],
    config: Optional[dict] = None,
    *,
    base_url: Optional[str] = None,
) -> ComposedSnippet:
    """Compone lo snippet à-la-carte da una selezione di blocchi.

    Args:
        slug: store slug (validato difensivamente).
        selected_ids: id di blocchi selectable (menu/content). "full" non si
            mescola con l'à-la-carte: se presente, vince e ritorna il preset.
        config: dict {block_id: {field_key: value}} con la config dei blocchi.
        base_url: override backend URL (dev: http://localhost:8000). In prod
            si omette (default produzione lato SDK).

    Returns:
        ComposedSnippet con sezioni head/elements/singletons + snippet unito.

    Raises:
        ValueError: slug invalido, blocco sconosciuto, o config invalida.
    """
    slug = _sanitize_slug(slug)
    config = config or {}

    # Preset "full": ritorna il legacy, niente sezioni à-la-carte.
    if "full" in selected_ids:
        full = generate_embed_snippet(slug)
        return ComposedSnippet(head="", elements=(), singletons=(), snippet=full)

    # Valida e mantiene l'ordine canonico del catalogo per output stabile.
    unknown = [s for s in selected_ids if s not in BLOCKS]
    if unknown:
        raise ValueError(f"Unknown block id(s): {unknown}")
    ordered = [
        b.id
        for b in _BLOCK_LIST
        if b.id in selected_ids and b.selectable and b.group != "preset"
    ]

    # Head: script una-tantum con config di pagina.
    bundle = get_embed_bundle_url()
    base_attr = (
        f' data-afianco-base-url="{html.escape(base_url, quote=True)}"'
        if base_url
        else ""
    )
    head = (
        f'<script type="module" src="{bundle}" '
        f'data-afianco-slug="{html.escape(slug, quote=True)}"{base_attr}></script>'
    )

    # Elementi selezionati.
    elements: list[dict] = []
    for sid in ordered:
        spec = BLOCKS[sid]
        elements.append(
            {
                "id": sid,
                "label": spec.label,
                "html": spec.render(slug, config.get(sid, {})),
            }
        )

    # Singleton richiesti (dedup, ordine canonico).
    singletons: list[dict] = []
    for sid in _resolve_singletons(ordered):
        spec = BLOCKS[sid]
        singletons.append(
            {"id": sid, "label": spec.label, "html": spec.render(slug, {})}
        )

    # Snippet unito, con commenti-guida.
    parts: list[str] = [
        "<!-- 1) Una sola volta, nel <head> o prima di </body> -->",
        head,
    ]
    if elements:
        parts.append("")
        parts.append("<!-- 2) Incolla dove vuoi (menu, pagine diverse, ...) -->")
        parts.extend(e["html"] for e in elements)
    if singletons:
        parts.append("")
        parts.append("<!-- 3) Una sola volta, a fine pagina -->")
        parts.extend(s["html"] for s in singletons)
    snippet = "\n".join(parts)

    return ComposedSnippet(
        head=head,
        elements=tuple(elements),
        singletons=tuple(singletons),
        snippet=snippet,
    )
