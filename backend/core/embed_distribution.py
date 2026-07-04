"""
Track E Step 2.1 — Embed Distribution canonical helper.

Single source of truth per:
  1. Bundle JS URL (where afianco-embed.es.js is hosted)
  2. Snippet HTML generator (what merchant copies-pastes)
  3. Versioning del bundle (path /embed/v1/...)

Architettura Cloudflare-ready
=============================

Bundle URL e' configurabile via env var EMBED_CDN_BASE_URL. Default:
  https://app.afianco.ch/embed   (nginx self-host start)

Upgrade path a CDN esterno (Cloudflare R2 / Fastly / etc.):
  EMBED_CDN_BASE_URL=https://cdn.afianco.ch
  → zero code changes, solo env update + redeploy
  → SDK consumer (merchant): nessun impact (snippet rigenerato auto via
    backend endpoint /embed-info)
  → Versioning path /embed/v1/... resta lo stesso → cache invariate

Pattern industry standard:
  - Twilio embeddable widgets: env-configurable CDN
  - Stripe Elements: api-base + cdn-base separately env-driven
  - Intercom messenger: cdn.intercom.io via env switch

Versioning
==========

Path versionato esplicito (/embed/v1/) per evitare breaking changes:
  - v1: contratto stable corrente
  - v2 future: nuovo path /embed/v2/, v1 mantenuto 6+ mesi
  - SDK bundle servito a /embed/{version}/afianco-embed.es.js

Single point of update: EMBED_BUNDLE_VERSION constant qui. Bump version
solo per breaking changes contract embed-SDK (vedi embed-integration-guide.md
versioning policy).

Snippet generator
=================

Generato server-side per:
  - URL bundle controlled by ops (no hardcoded in frontend)
  - Snippet customizable per merchant (slug-specific)
  - Future: customization per merchant tier (es. premium = no afianco
    branding footer) senza touch frontend

Anti-XSS: store_slug e' validato (3-50 char, alphanumeric+hyphen) upstream
da Pydantic Store model. Non re-validate qui (caller responsibility) ma
escape HTML attributes nel template (` " ` quotes balanced).

Public API
==========

    EMBED_CDN_BASE_URL: str
        Resolved base URL (env or default).
    EMBED_BUNDLE_VERSION: str (= "v1")
        Current bundle version path component.
    DEFAULT_CDN_BASE: str (= "https://app.afianco.ch/embed")
        Default nginx self-host URL. Override via env.

    get_embed_bundle_url() -> str
        Canonical URL del bundle JS embed:
        e.g. https://app.afianco.ch/embed/v1/afianco-embed.es.js

    get_embed_module_url() -> str
        ES module variant (preferred su browser modern).

    generate_embed_snippet(store_slug) -> str
        Genera HTML snippet completo per il merchant.

    get_hosted_storefront_url(store_slug, base_app_url=None) -> str
        URL hosted storefront afianco-side per merchant senza dominio
        proprio. Pattern: https://app.afianco.ch/s/{slug}
"""

import os
from typing import Optional


# ── Configurazione ─────────────────────────────────────────────────────

# Default base URL: nginx self-host della app principale.
# Override via env var per migrazione futura a CDN esterno (Cloudflare R2).
DEFAULT_CDN_BASE = "https://app.afianco.ch/embed"

# Path version segment. Bump solo per breaking changes contract embed-SDK.
EMBED_BUNDLE_VERSION = "v1"

# Resolved CDN base URL (resolution at import time, no per-call os.environ
# overhead).
EMBED_CDN_BASE_URL = os.environ.get(
    "EMBED_CDN_BASE_URL", DEFAULT_CDN_BASE
).rstrip("/")

# Default base URL della admin app per hosted storefront. Pattern dello
# stesso env var family ma orthogonale: hosted storefront e' una pagina
# admin-domain-served, NON il CDN bundle.
DEFAULT_APP_BASE = "https://app.afianco.ch"
APP_BASE_URL = os.environ.get(
    "PUBLIC_APP_URL", DEFAULT_APP_BASE
).rstrip("/")


# ── Bundle URL builders ────────────────────────────────────────────────


def get_embed_bundle_url() -> str:
    """Canonical URL del bundle ES module (ESM).

    Pattern: {EMBED_CDN_BASE_URL}/{EMBED_BUNDLE_VERSION}/afianco-embed.es.js

    Es. default: https://app.afianco.ch/embed/v1/afianco-embed.es.js
    Es. con env=https://cdn.afianco.ch: https://cdn.afianco.ch/v1/...

    Returns:
        URL completo bundle ES module (preferred for browser modern).
    """
    return f"{EMBED_CDN_BASE_URL}/{EMBED_BUNDLE_VERSION}/afianco-embed.es.js"


def get_embed_module_url() -> str:
    """Alias semantico di get_embed_bundle_url() — ES module preferred."""
    return get_embed_bundle_url()


def get_embed_umd_url() -> str:
    """UMD bundle URL (fallback per browser senza ESM support).

    Tipicamente NON usato (ESM e' supported da tutti i browser target
    >=2018). Esposto per compat documentation completa.
    """
    return f"{EMBED_CDN_BASE_URL}/{EMBED_BUNDLE_VERSION}/afianco-embed.umd.js"


# ── Hosted storefront URL ──────────────────────────────────────────────


def get_hosted_storefront_url(
    store_slug: str,
    base_app_url: Optional[str] = None,
) -> str:
    """URL hosted storefront afianco-side per merchant senza dominio proprio.

    Pattern: {APP_BASE_URL}/s/{slug}
    Es: https://app.afianco.ch/s/pasticceria-mario

    Args:
        store_slug: store.slug del merchant (3-50 char validati upstream)
        base_app_url: override del default (testing / multi-env)

    Returns:
        URL completo accessibile pubblicamente (no auth required, store
        deve essere pubblicato + visibility=public).
    """
    base = (base_app_url or APP_BASE_URL).rstrip("/")
    return f"{base}/s/{store_slug}"


# ── Snippet generator ──────────────────────────────────────────────────


def generate_embed_snippet(store_slug: str) -> str:
    """Genera HTML snippet completo per merchant da incollare sul sito.

    Output contract (sentinel pinned) — Track E Step 2.4.5 (product detail):
      - <script type="module" src="..."> caricamento bundle (ES module)
      - <afianco-storefront-init slug="..."> web component root provider
      - 6 web component children, IN ORDINE coordinato per UX coerente:
          * <afianco-header>            navbar sticky top (account + cart trigger)
          * <afianco-account hide-trigger> drawer login/signup/portal
              hide-trigger nasconde il FAB interno (sostituito dall'header)
          * <afianco-product-grid>      catalogo prodotti + filtri categoria
          * <afianco-product-detail>    landing drawer per ogni prodotto
              (E2.4.5): click sulla card → apre detail con description,
              qty selector, CTA "Aggiungi al carrello"
          * <afianco-cart-drawer hide-trigger> drawer carrello slide-in
              hide-trigger nasconde il FAB interno (sostituito dall'header)
          * <afianco-checkout-button>   checkout Stripe
      - Indented 2-space leggibile

    Embedding completo a 360 gradi con navbar unificato (E2.4.4):
      - Header sticky top con icone account + cart ordinate
      - Prodotti + filtri (via product-grid)
      - Categorie (via product-grid filter)
      - Cart management (cart-drawer) — apertura via header click o
        auto-open al primo add-to-cart
      - Checkout Stripe (checkout-button)
      - Account login/signup/portal (afianco-account) — apertura via
        header click

    Architettura: loose coupling via document events
        afianco:open-account, afianco:open-cart sono dispatched dal
        <afianco-header> al click → ascoltati dai drawer corrispondenti.
        Zero direct reference tra componenti.

    Anti-XSS:
      - store_slug validato upstream (Pydantic Store.slug: 3-50 char,
        regex alphanumeric+hyphen). Sentinel assume valid input.
      - " quotes balanced + non-user-controlled URL = no injection vector
      - Future: se permettiamo custom store_slug user input → escape
        via html.escape() qui

    Args:
        store_slug: slug del store da embeddare (validato upstream).

    Returns:
        HTML snippet string ready per copy-to-clipboard nel merchant
        dashboard.

    Example:
        >>> generate_embed_snippet("pasticceria-mario")
        '<script type="module" src="https://...es.js"></script>\\n
         <afianco-storefront-init slug="pasticceria-mario">\\n
           <afianco-header></afianco-header>\\n
           <afianco-account hide-trigger></afianco-account>\\n
           <afianco-product-grid></afianco-product-grid>\\n
           <afianco-cart-drawer hide-trigger></afianco-cart-drawer>\\n
           <afianco-checkout-button></afianco-checkout-button>\\n
         </afianco-storefront-init>'
    """
    bundle_url = get_embed_bundle_url()
    # Use single-line string concatenation for predictable output
    # (no leading/trailing whitespace surprises).
    return (
        f'<script type="module" src="{bundle_url}"></script>\n'
        f'<afianco-storefront-init slug="{store_slug}">\n'
        f'  <afianco-header></afianco-header>\n'
        f'  <afianco-account hide-trigger></afianco-account>\n'
        f'  <afianco-product-grid></afianco-product-grid>\n'
        f'  <afianco-product-detail></afianco-product-detail>\n'
        f'  <afianco-cart-drawer hide-trigger></afianco-cart-drawer>\n'
        f'  <afianco-checkout-button></afianco-checkout-button>\n'
        f'</afianco-storefront-init>'
    )


def get_distribution_info() -> dict:
    """Snapshot del distribution config corrente.

    Utile per:
      - Endpoint admin /embed-info (frontend modal)
      - Debug / monitoring (e.g. operator check di prod)
      - Future migration health check

    Returns:
        Dict con: cdn_base, version, bundle_url, app_base, default_cdn.
        default_cdn esposto per dashboard ops indicator "still on default
        nginx vs migrated to CDN".
    """
    return {
        "cdn_base": EMBED_CDN_BASE_URL,
        "version": EMBED_BUNDLE_VERSION,
        "bundle_url": get_embed_bundle_url(),
        "umd_bundle_url": get_embed_umd_url(),
        "app_base": APP_BASE_URL,
        "default_cdn": DEFAULT_CDN_BASE,
        "is_default_cdn": EMBED_CDN_BASE_URL == DEFAULT_CDN_BASE,
    }


__all__ = [
    "EMBED_CDN_BASE_URL",
    "EMBED_BUNDLE_VERSION",
    "DEFAULT_CDN_BASE",
    "APP_BASE_URL",
    "get_embed_bundle_url",
    "get_embed_module_url",
    "get_embed_umd_url",
    "get_hosted_storefront_url",
    "generate_embed_snippet",
    "get_distribution_info",
]
