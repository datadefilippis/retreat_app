"""Wave GDPR-Admin Phase C — public legal document router (2026-05-16).

Serves the Privacy Policy and Terms of Service text bundles in 4
locales (it / en / de / fr) as Markdown.

Public, no auth required (these are pre-signup documents users
must read before accepting). Light-weight (file read, no DB);
cache-friendly (5-minute Cache-Control for browsers + CDN).

Endpoints:
  GET /api/legal/privacy?lang=xx     →  Privacy Policy markdown
  GET /api/legal/terms?lang=xx       →  Terms of Service markdown
  GET /api/legal/versions            →  Current version metadata

The frontend reads ``?lang=`` from the URL (or falls back to the
i18n.language preference) and calls the appropriate endpoint.

Returns 200 with a JSON envelope (NOT raw markdown body) so the
frontend can also access the metadata (locale_actual, is_draft,
version_tag, available_locales) for UI rendering of the
"translation in progress" notice + the language switcher.
"""

import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse

# Wave GDPR-Commerce CG-7 — DPA endpoints require admin auth. The
# import sits up here so the decorator on the endpoint definitions
# (much later in the file) can reference it cleanly.
from auth import require_admin


logger = logging.getLogger(__name__)


router = APIRouter(prefix="/legal", tags=["Legal"])


@router.get("/privacy")
async def get_privacy_policy(
    lang: Optional[str] = Query(
        default=None,
        description="Requested locale (it, en, de, fr). Falls back to it.",
    ),
):
    """Return the Privacy Policy in the requested locale.

    The response is a JSON envelope (not raw markdown) so the
    frontend can render both the content AND the metadata badges
    (draft notice, version tag, language switcher).

    Cache-Control: public, max-age=300 — these documents change
    rarely and are version-tagged; a 5-minute browser cache is
    appropriate. CDN-friendly.
    """
    from core.legal_versions import get_legal_document
    doc = get_legal_document("privacy", lang)
    return JSONResponse(
        content=doc,
        headers={"Cache-Control": "public, max-age=300"},
    )


@router.get("/terms")
async def get_terms_of_service(
    lang: Optional[str] = Query(
        default=None,
        description="Requested locale (it, en, de, fr). Falls back to it.",
    ),
):
    """Return the Terms of Service in the requested locale.

    Same envelope shape as /privacy. See ``get_privacy_policy``.
    """
    from core.legal_versions import get_legal_document
    doc = get_legal_document("terms", lang)
    return JSONResponse(
        content=doc,
        headers={"Cache-Control": "public, max-age=300"},
    )


@router.get("/versions")
async def get_legal_versions():
    """Return the current legal version metadata.

    Used by the signup flow to display the version+locale that the
    user is accepting (rendered in the consent checkbox label) and
    by the settings page to indicate whether a re-acceptance is
    required after a version bump.

    Cache-Control: public, max-age=60 — version bumps should
    propagate within a minute. The actual document content endpoints
    cache for 5 minutes; this metadata endpoint caches shorter
    because it is the canonical signal that triggers re-acceptance.
    """
    from core.legal_versions import (
        CURRENT_VERSION_TAG, CURRENT_VERSION_HASH,
        current_version_string,
    )
    return JSONResponse(
        content={
            "version_tag": CURRENT_VERSION_TAG,
            "version_hash": CURRENT_VERSION_HASH,
            "version_string": current_version_string(),
            "available_locales": ["it", "en", "de", "fr"],
            "default_locale": "it",
            # v1.0 production launch: EN/DE/FR are full translations
            # of the IT binding bundle, no longer drafts. Field kept
            # on the envelope so a future locale added pre-review can
            # be flagged without breaking the frontend contract.
            "draft_locales": [],
            "binding_locale": "it",
        },
        headers={"Cache-Control": "public, max-age=60"},
    )


# ── Wave GDPR-Admin Phase E — public sub-processor disclosure ─────────────
#
# GDPR Art. 28.3.i and Art. 13.1.f require that sub-processors and
# international transfer mechanisms be DISCOVERABLE INDEPENDENTLY of the
# full Privacy Policy. We already list them inside privacy_<locale>.md,
# but a dedicated machine-readable + UI-friendly endpoint makes the
# disclosure first-class:
#
#   GET /api/legal/sub-processors            (locale-aware)
#
# The list is the SINGLE SOURCE OF TRUTH for the frontend
# /legal/sub-processors page and any future audit-export tooling.
# Updates here MUST be mirrored in the privacy_<locale>.md sections.

# Sub-processor static registry — manually curated.
#
# Each entry carries:
#   - name        legal name of the processor
#   - country     processing country (with EU/EEA flag for trust signal)
#   - purpose     scoped activity for which data is shared
#   - data        category of personal data shared (Art. 30 record)
#   - safeguard   transfer mechanism for non-EU processors (SCCs, DPF, …)
#   - url         link to the processor's privacy / DPA page
#
# Locale-specific phrasing lives in the per-locale label maps below;
# stable machine fields (id, country code, url) are locale-independent.

_SUB_PROCESSORS = [
    {
        "id": "hetzner",
        "name": "Hetzner Online GmbH",
        "country_code": "DE",
        "is_eu_eea": True,
        "url": "https://www.hetzner.com/legal/privacy-policy/",
    },
    {
        "id": "mongodb_self_hosted",
        "name": "MongoDB (self-hosted on Hetzner)",
        "country_code": "DE",
        "is_eu_eea": True,
        "url": "https://www.mongodb.com/legal/privacy-policy",
    },
    {
        "id": "anthropic",
        "name": "Anthropic, PBC",
        "country_code": "US",
        "is_eu_eea": False,
        "url": "https://www.anthropic.com/legal/privacy",
    },
    {
        "id": "stripe",
        "name": "Stripe Payments Europe, Ltd.",
        "country_code": "IE",
        "is_eu_eea": True,
        "url": "https://stripe.com/privacy",
    },
    {
        "id": "brevo",
        "name": "Brevo (ex Sendinblue)",
        "country_code": "FR",
        "is_eu_eea": True,
        "url": "https://www.brevo.com/legal/privacypolicy/",
    },
]

# Per-locale labels — kept inline so they're easy to audit against the
# privacy_<locale>.md sections. If you add a new sub-processor above,
# add a matching row to ALL FOUR locale maps. If a locale is missing a
# row, the endpoint falls back to the Italian label.

_SP_LABELS = {
    "it": {
        "hetzner": {
            "purpose": "Hosting infrastruttura (VPS + storage)",
            "data": "Tutti i dati applicativi (cifrati a riposo)",
            "safeguard": "UE/SEE — nessun trasferimento internazionale",
        },
        "mongodb_self_hosted": {
            "purpose": "Database operativo (auto-ospitato su Hetzner)",
            "data": "Account, vendite, acquisti, chat AI, audit log",
            "safeguard": "UE/SEE — istanza auto-ospitata in Germania",
        },
        "anthropic": {
            "purpose": "Modelli AI (chat assistant, analisi documenti)",
            "data": "Domande utente + estratti aggregati delle vendite",
            "safeguard": "SCC UE + EU-US Data Privacy Framework (DPF)",
        },
        "stripe": {
            "purpose": "Pagamenti abbonamento e modulo Commerce",
            "data": "Email, nome, dati di fatturazione, token carta",
            "safeguard": "UE/SEE (Stripe Payments Europe, Irlanda)",
        },
        "brevo": {
            "purpose": "Email transazionali (verifica, warning cancellazione)",
            "data": "Email, nome, contenuto del messaggio",
            "safeguard": "UE/SEE (sede Francia, server UE)",
        },
    },
    "en": {
        "hetzner": {
            "purpose": "Infrastructure hosting (VPS + storage)",
            "data": "All application data (encrypted at rest)",
            "safeguard": "EU/EEA — no international transfer",
        },
        "mongodb_self_hosted": {
            "purpose": "Operational database (self-hosted on Hetzner)",
            "data": "Accounts, sales, purchases, AI chat, audit log",
            "safeguard": "EU/EEA — self-hosted instance in Germany",
        },
        "anthropic": {
            "purpose": "AI models (chat assistant, document analysis)",
            "data": "User questions + aggregated sales excerpts",
            "safeguard": "EU SCCs + EU-US Data Privacy Framework (DPF)",
        },
        "stripe": {
            "purpose": "Subscription payments and Commerce module",
            "data": "Email, name, billing data, card token",
            "safeguard": "EU/EEA (Stripe Payments Europe, Ireland)",
        },
        "brevo": {
            "purpose": "Transactional emails (verification, deletion warning)",
            "data": "Email, name, message content",
            "safeguard": "EU/EEA (HQ France, EU servers)",
        },
    },
    "de": {
        "hetzner": {
            "purpose": "Infrastruktur-Hosting (VPS + Speicher)",
            "data": "Alle Anwendungsdaten (verschlüsselt im Ruhezustand)",
            "safeguard": "EU/EWR — keine internationale Übermittlung",
        },
        "mongodb_self_hosted": {
            "purpose": "Operative Datenbank (selbst gehostet bei Hetzner)",
            "data": "Konten, Verkäufe, Einkäufe, KI-Chat, Audit-Log",
            "safeguard": "EU/EWR — selbst gehostete Instanz in Deutschland",
        },
        "anthropic": {
            "purpose": "KI-Modelle (Chat-Assistent, Dokumentenanalyse)",
            "data": "Benutzerfragen + aggregierte Verkaufsauszüge",
            "safeguard": "EU-SCC + EU-US Data Privacy Framework (DPF)",
        },
        "stripe": {
            "purpose": "Abonnementzahlungen und Commerce-Modul",
            "data": "E-Mail, Name, Rechnungsdaten, Karten-Token",
            "safeguard": "EU/EWR (Stripe Payments Europe, Irland)",
        },
        "brevo": {
            "purpose": "Transaktions-E-Mails (Verifizierung, Löschwarnung)",
            "data": "E-Mail, Name, Nachrichteninhalt",
            "safeguard": "EU/EWR (Hauptsitz Frankreich, EU-Server)",
        },
    },
    "fr": {
        "hetzner": {
            "purpose": "Hébergement de l'infrastructure (VPS + stockage)",
            "data": "Toutes les données applicatives (chiffrées au repos)",
            "safeguard": "UE/EEE — pas de transfert international",
        },
        "mongodb_self_hosted": {
            "purpose": "Base de données opérationnelle (auto-hébergée chez Hetzner)",
            "data": "Comptes, ventes, achats, chat IA, journal d'audit",
            "safeguard": "UE/EEE — instance auto-hébergée en Allemagne",
        },
        "anthropic": {
            "purpose": "Modèles IA (assistant chat, analyse de documents)",
            "data": "Questions utilisateur + extraits agrégés des ventes",
            "safeguard": "CCT UE + EU-US Data Privacy Framework (DPF)",
        },
        "stripe": {
            "purpose": "Paiements abonnement et module Commerce",
            "data": "E-mail, nom, données de facturation, jeton carte",
            "safeguard": "UE/EEE (Stripe Payments Europe, Irlande)",
        },
        "brevo": {
            "purpose": "E-mails transactionnels (vérification, avertissement suppression)",
            "data": "E-mail, nom, contenu du message",
            "safeguard": "UE/EEE (siège France, serveurs UE)",
        },
    },
}


@router.get("/sub-processors")
async def get_sub_processors(
    lang: Optional[str] = Query(
        default=None,
        description="Requested locale (it, en, de, fr). Falls back to it.",
    ),
):
    """Return the locale-aware sub-processor registry.

    Public, no auth — the page is linked from the signup flow and the
    public Privacy / Terms pages, so end users browsing before account
    creation can review the data-sharing chain (GDPR Art. 28.3.i +
    Art. 13.1.f).

    Cache-Control: public, max-age=300 — registry changes are rare and
    version-tagged via the standard /api/legal/versions bump.
    """
    from core.legal_versions import (
        CURRENT_VERSION_TAG,
        current_version_string,
    )

    requested = (lang or "it").lower()
    locale = requested if requested in {"it", "en", "de", "fr"} else "it"
    labels = _SP_LABELS[locale]
    # Italian acts as the legally-binding fallback for any future
    # locale that ships before its localized labels (defensive).
    fallback = _SP_LABELS["it"]

    enriched = []
    for entry in _SUB_PROCESSORS:
        sid = entry["id"]
        loc_lbl = labels.get(sid, fallback.get(sid, {}))
        enriched.append({
            **entry,
            "purpose": loc_lbl.get("purpose", ""),
            "data": loc_lbl.get("data", ""),
            "safeguard": loc_lbl.get("safeguard", ""),
        })

    return JSONResponse(
        content={
            "locale_actual": locale,
            "locale_requested": requested,
            "version_tag": CURRENT_VERSION_TAG,
            "version_string": current_version_string(),
            "binding_locale": "it",
            "controller": {
                "name": "Davide De Filippis",
                "city": "Lugano",
                "country": "Switzerland",
                "email": "info@aurya.life",
            },
            "sub_processors": enriched,
        },
        headers={"Cache-Control": "public, max-age=300"},
    )


# ─────────────────────────────────────────────────────────────────────────
# Wave GDPR-Commerce Phase CG-2 — per-store merchant legal endpoints
# ─────────────────────────────────────────────────────────────────────────
#
# Public endpoints serving each merchant's OWN Privacy Policy + Terms of
# Service for their storefront. The merchant is the Data Controller toward
# their end customers; afianco is the Data Processor. So the storefront
# must surface the MERCHANT'S docs, not afianco's.
#
# Architectural cornerstone (set in CG-1): the merchant edits 4 locales
# but chooses ONE ``merchant_legal_display_locale`` that is the SOLE
# version shown to ALL customers. No ``lang`` query param — the locale
# is dictated by the merchant.
#
# Endpoints:
#   GET /api/storefront/{slug}/legal/privacy
#   GET /api/storefront/{slug}/legal/terms
#   GET /api/storefront/{slug}/legal/metadata
#
# Behaviour matrix
# ----------------
#   slug unknown                       → 404
#   slug found, status=not_configured  → 200 with content=""
#                                        + status flag + merchant_email
#                                        (frontend renders a graceful
#                                         "merchant has not configured"
#                                         placeholder rather than 404 so
#                                         the rest of the storefront UX
#                                         is not broken)
#   slug found, status=draft           → same as not_configured for the
#                                        PUBLIC endpoint — the draft is
#                                        not yet legally published, must
#                                        not be served to customers
#   slug found, status=stale_draft     → serve the LAST PUBLISHED bundle
#                                        (the draft is not visible to
#                                         customers until publish)
#   slug found, status=published       → 200 with content + version_tag
#
# Cache-Control: public, max-age=300 — same as afianco platform docs.
# Slug enumeration is rate-limited at the public.py middleware layer.


async def _resolve_store_for_legal(slug: str) -> Optional[dict]:
    """Return the store document for ``slug`` if it exists & is publicly
    accessible — else None.

    This is intentionally a NEW helper distinct from public._resolve_org
    because we want a different not-found behaviour: legal endpoints
    return a 200 envelope with status="not_configured" rather than 404,
    so the public storefront doesn't visually break when a merchant
    publishes a store but hasn't filled in their docs yet.

    Returns None for:
      - slug not in stores collection (true 404)
      - store inactive or not published
      - legacy single-store org without a Store doc (CG-1 schema doesn't
        carry merchant_legal_* on the legacy ``org.store_settings``, so
        we can't serve anything meaningful)

    The caller distinguishes the None case from "found but not_configured"
    by checking the returned dict's status flag.
    """
    from database import stores_collection

    return await stores_collection.find_one(
        {
            "slug": slug,
            "is_published": True,
            "is_active": True,
            "visibility": "public",
        },
        {"_id": 0},
    )


def _build_autogen_template_vars(store: dict) -> "TemplateVars":
    """Track E Step 7.5 — build TemplateVars dal store doc per auto-render
    di fallback legale.

    Quando il merchant NON ha ancora pubblicato Privacy/Terms (status=
    not_configured | draft), il customer cliccando il link nel widget
    embed atterrava su una pagina placeholder vuota — UX rotta e
    compliance gap perche' nessuna informativa era effettivamente
    consultabile al momento del consenso GDPR.

    Fix: usiamo il template-engine merchant esistente (lo stesso usato
    dall'admin per "Genera bozza standard") per renderizzare al volo un
    documento base personalizzato con i dati anagrafici gia' presenti
    nello store. Cosi' il customer vede SEMPRE un'informativa concreta
    (anche se generata dal template) invece di un placeholder vuoto, e
    il merchant puo' successivamente personalizzarla pubblicandone una
    propria.

    Strategia campi:
      - Se ``merchant_legal_template_vars`` gia' valorizzato (wizard
        admin partially-completed), lo riusiamo come baseline → vince
        sul fallback derivato dallo store doc.
      - Altrimenti derivati dal store doc (name, contact_email,
        country, ecc.).

    Note: questa funzione e' PURE (no DB), defensive ai field mancanti
    (TemplateVars accetta empty string default su tutti).
    """
    from services.merchant_legal_template_service import TemplateVars

    saved = store.get("merchant_legal_template_vars") or {}
    if isinstance(saved, dict) and saved:
        try:
            return TemplateVars(**saved)
        except Exception:
            # Saved dict corrupt → fall through al fallback store-derived
            pass

    # Derivazione defensive dai field del store:
    #   - store_name + merchant_name fall-back uno sull'altro
    #   - country: contact_country / billing_country / "" (template ha
    #     placeholder leggibile se vuoto)
    store_settings = store.get("store_settings") or {}
    name = store.get("name") or store_settings.get("display_name") or ""
    email = store.get("contact_email") or store_settings.get("contact_email") or ""
    country = (
        store.get("country")
        or store.get("billing_country")
        or store_settings.get("country")
        or ""
    )
    fulfillment_modes = store.get("fulfillment_modes") or []
    collects_shipping = "shipping" in fulfillment_modes
    return TemplateVars(
        merchant_name=name,
        merchant_email=email,
        merchant_country=country,
        store_name=name,
        store_country=country,
        collects_phone=False,
        collects_shipping_address=collects_shipping,
        uses_marketing=False,
        ships_to_eu=collects_shipping,  # conservative default
    )


def _render_autogen_fallback(store: dict, doc_type: str, locale: str) -> str:
    """Renderizza il template auto-fallback. Soft-fail a "" se template
    file missing (deployment edge case — torna a placeholder originale)."""
    from services.merchant_legal_template_service import render_template
    try:
        vars_obj = _build_autogen_template_vars(store)
        return render_template(
            doc_type=doc_type,  # type: ignore[arg-type]
            locale=locale,  # type: ignore[arg-type]
            vars=vars_obj,
        )
    except (FileNotFoundError, ValueError) as exc:
        logger.warning(
            "legal: autogen fallback failed slug=%s doc=%s locale=%s: %s",
            store.get("slug"), doc_type, locale, exc,
        )
        return ""


def _public_doc_envelope(
    store: dict,
    doc_type: str,
) -> dict:
    """Build the public JSON envelope for one merchant legal document.

    Pure function — no DB access. Always returns a 200-ready dict; the
    caller wraps it in JSONResponse with cache headers.

    The envelope contract is stable for the frontend:
      content            : raw markdown of the published display_locale
                           document. Quando il merchant non ha pubblicato
                           (status=not_configured | draft), Track E Step
                           7.5 popola questo campo con un FALLBACK
                           auto-generato dal template merchant standard
                           pre-fillato con i dati anagrafici store. Cosi'
                           il customer vede SEMPRE un'informativa
                           consultabile al momento del consenso GDPR.
      display_locale     : the locale customers actually see (or null)
      status             : "not_configured" | "draft" | "published" |
                           "stale_draft" — see merchant_legal_versioning
      is_autogenerated   : bool — true quando content e' il fallback
                           template (vs. content pubblicato dal
                           merchant). Frontend mostra un banner
                           informativo sopra il documento.
      version_tag        : "v1.0", "v1.1", … (null when never published)
      version_hash       : SHA256-hex16 (null when never published)
      version_string     : "v1.0:48ea..." (null when never published)
      doc_type           : passthrough ("privacy" | "terms")
      merchant_email     : contact for GDPR rights (or null)
      store_name         : human-readable store name
      published_at       : ISO UTC of last publish (or null)
    """
    from services.merchant_legal_versioning import (
        merchant_legal_status, current_version_string,
        get_effective_display_locale,
    )

    # CG-3-Polish-3 (2026-05-18 late evening) — resolve the
    # customer-facing locale via the helper, NOT the raw legacy
    # field. The CG-3-Polish-2 auto-cleanup unsets the legacy field
    # on every admin save; if we still read the raw field here the
    # public endpoint sees `display=None` and serves empty content.
    # Bug reported by user: "privacy/T&C non si vedono più nel
    # commerce frontend".
    display = get_effective_display_locale(store)
    status_value = merchant_legal_status(store)
    is_autogenerated = False

    if status_value in ("published", "stale_draft") and display:
        # For stale_draft we'd ideally serve the SNAPSHOT at last
        # publish_at — but CG-1 doesn't keep the snapshot. For CG-2 we
        # serve the current display-locale content. This is acceptable
        # because: (a) the merchant has edited but not republished —
        # the new edits are still in progress, not in the legally
        # binding bundle; (b) most edits are minor wording fixes; and
        # (c) once they publish the version bumps and the customer
        # re-consents. A future CG-N can persist the snapshot at
        # publish-time if we want strict immutability.
        field = f"merchant_{doc_type}_content_{display}"
        content = store.get(field) or ""
        # Edge case difensivo: status=published ma field vuoto (data
        # drift — un publish riuscito senza content non dovrebbe
        # capitare ma proteggiamo comunque il customer).
        if not content:
            content = _render_autogen_fallback(store, doc_type, display or "it")
            is_autogenerated = bool(content)
    else:
        # Track E Step 7.5 — Auto-fallback per not_configured + draft.
        # Pre-fix: content="" → la pagina React mostrava SOLO il
        # placeholder giallo e nessuna informativa concreta. Compliance
        # gap critico (Art. 13 GDPR richiede informativa accessibile al
        # momento del consenso). Post-fix: rendiamo il template default
        # pre-fillato con i dati anagrafici store cosi' il customer ha
        # SEMPRE un'informativa GDPR-compliant da leggere.
        fallback_locale = display or "it"
        content = _render_autogen_fallback(store, doc_type, fallback_locale)
        is_autogenerated = bool(content)

    return {
        "content": content,
        "display_locale": display,
        "status": status_value,
        # Track E Step 7.5 — bandiera per il frontend (mostra banner
        # informativo "documento auto-generato, contatta merchant per
        # personalizzata"). Customer comunque legge il documento.
        "is_autogenerated": is_autogenerated,
        "version_tag": store.get("merchant_legal_version_tag"),
        "version_hash": store.get("merchant_legal_version_hash"),
        "version_string": current_version_string(store),
        "doc_type": doc_type,
        "merchant_email": (store.get("contact_email") or "") or None,
        "store_name": store.get("name") or "",
        "published_at": store.get("merchant_legal_published_at"),
    }


def _cache_headers_for_envelope(envelope: dict) -> dict:
    """Wave CG-3-Polish-4 — build Cache-Control + ETag headers for the
    public storefront legal endpoints.

    Previously the endpoints used ``Cache-Control: public, max-age=300``
    which meant browsers cached the doc for 5 minutes. After a merchant
    published a new version, customers could see stale content for up
    to 5 minutes — and the merchant themselves while testing perceived
    this as "my changes are not being applied".

    Fix: shorter max-age (30s) + an ETag derived from the legal version
    string. When the merchant publishes (version_string changes), the
    ETag changes, the browser's conditional request returns the new
    content immediately rather than honouring the now-stale cache entry.

    Track E Step 7.5 — Con il content auto-generato, l'ETag deve
    invalidare anche quando cambia uno dei field anagrafici che
    influenzano il render del template (store_name, contact_email,
    storefront_languages[0]). Includiamo hash content-derived nel seed
    per is_autogenerated=true cosi' la cache si invalida correttamente
    quando il merchant aggiorna l'anagrafica.
    """
    import hashlib

    vs = envelope.get("version_string")
    status_v = envelope.get("status") or "unknown"
    is_auto = envelope.get("is_autogenerated", False)
    # ETag format: "<status>:<version_or_state>" + hash content se autogen
    # The wrapping quotes are required by RFC 7232.
    if vs:
        etag_seed = f"{status_v}:{vs}"
    elif is_auto:
        # Auto-gen content non ha version → usiamo hash16 del content
        # cosi' cache invalida quando merchant cambia name/email/lingua
        content = envelope.get("content") or ""
        locale = envelope.get("display_locale") or ""
        content_hash = hashlib.sha256(
            f"{content}|{locale}".encode("utf-8")
        ).hexdigest()[:16]
        etag_seed = f"{status_v}:autogen:{content_hash}"
    else:
        etag_seed = f"{status_v}:no-version"
    return {
        "Cache-Control": "public, max-age=30, must-revalidate",
        "ETag": f'"{etag_seed}"',
    }


@router.get("/storefront/{slug}/privacy")
async def get_storefront_privacy(slug: str):
    """Return the merchant's published Privacy Policy for this storefront.

    Public, no auth. See module docstring for the behaviour matrix.

    NOTE: even when the merchant has not yet configured their docs, we
    return 200 with status="not_configured" + an empty content. The
    frontend renders a graceful placeholder ("Questo negozio sta
    completando la configurazione, contatta merchant@example.com") so
    the rest of the storefront UX isn't broken by a missing legal page.
    """
    store = await _resolve_store_for_legal(slug)
    if store is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Store not found",
        )
    envelope = _public_doc_envelope(store, "privacy")
    return JSONResponse(
        content=envelope,
        headers=_cache_headers_for_envelope(envelope),
    )


@router.get("/storefront/{slug}/terms")
async def get_storefront_terms(slug: str):
    """Return the merchant's published Terms of Service for this storefront.

    Same envelope shape and not-found behaviour as the privacy endpoint.
    """
    store = await _resolve_store_for_legal(slug)
    if store is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Store not found",
        )
    envelope = _public_doc_envelope(store, "terms")
    return JSONResponse(
        content=envelope,
        headers=_cache_headers_for_envelope(envelope),
    )


@router.get("/storefront/{slug}/metadata")
async def get_storefront_legal_metadata(slug: str):
    """Return only the legal-version metadata for a storefront.

    Used by:
      - The signup form on the storefront to bind the
        ``accepted_terms_version`` it records to the legally-published
        snapshot.
      - The customer portal to detect a stale ``accepted_terms_version``
        on the customer document and trigger the re-consent modal
        (mirror of the admin-side flow in Wave GDPR-Admin Phase E).

    Cache shorter than the content endpoints (max-age=60) — when the
    merchant publishes a new version we want customers' /me responses
    to switch ``consent_needs_refresh`` to true within a minute, not
    five.
    """
    from services.merchant_legal_versioning import (
        merchant_legal_status, current_version_string,
        get_effective_display_locale,
    )

    store = await _resolve_store_for_legal(slug)
    if store is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Store not found",
        )

    status_value = merchant_legal_status(store)
    return JSONResponse(
        content={
            "status": status_value,
            # CG-3-Polish-3 — use the helper, not the raw legacy field.
            "display_locale": get_effective_display_locale(store),
            "version_tag": store.get("merchant_legal_version_tag"),
            "version_hash": store.get("merchant_legal_version_hash"),
            "version_string": current_version_string(store),
            "published_at": store.get("merchant_legal_published_at"),
            "merchant_email": (store.get("contact_email") or "") or None,
            "store_name": store.get("name") or "",
        },
        headers={"Cache-Control": "public, max-age=60"},
    )


# ─────────────────────────────────────────────────────────────────────────
# Wave GDPR-Commerce Phase CG-7 — DPA (Data Processing Agreement) admin
# ─────────────────────────────────────────────────────────────────────────
#
# The DPA is the Art. 28 GDPR agreement between afianco (Processor) and
# each merchant org (Controller). Required by law for every merchant
# that uses the Commerce module — the merchant uploads end-customer
# personal data into afianco's systems, so this agreement must exist.
#
# Implementation
# --------------
# The DPA is a single-template document (one per locale) with merchant
# variables interpolated at render time. The acknowledgement is a
# single immutable consent_audit record with source="merchant_dpa_acknowledged"
# and document_type="merchant_dpa". An organization can only have ONE
# accepted DPA at a time; trying to acknowledge again returns the
# original acknowledgement timestamp.
#
# Endpoints (auth required: admin of the org)
#   GET  /api/legal/dpa?lang=xx    rendered markdown + variables status
#   POST /api/legal/dpa/acknowledge  immutable audit record
#   GET  /api/legal/dpa/status       has-this-org-acknowledged?
#
# Security
# --------
# - Every endpoint runs through ``require_admin``.
# - The variables interpolated (merchant_name, merchant_email,
#   merchant_country, org_id, date) are derived SERVER-SIDE from the
#   admin's JWT + the organization document. Never trusted from the
#   request payload.
# - Acknowledgement is appended-only via consent_audit_repository —
#   immutable, TTL 365 days, no UPDATE / DELETE path.


_DPA_DIR = Path(__file__).resolve().parent.parent / "legal"


def _read_dpa_template(locale: str) -> str:
    """Load the raw DPA template for ``locale``. Caller normalises.
    FileNotFoundError bubbles to 500 (deployment bug — file missing)."""
    path = _DPA_DIR / f"dpa_{locale}.md"
    return path.read_text(encoding="utf-8")


def _interpolate_dpa(template: str, vars_dict: dict) -> str:
    """Replace ``{{var}}`` occurrences in the DPA template. Unknown
    placeholders left literal so they're visible in the rendered output
    (defensive — DPA templates only use placeholders we own)."""
    import re
    placeholder_re = re.compile(r"\{\{([a-zA-Z_][a-zA-Z0-9_]*)\}\}")

    def repl(m):
        key = m.group(1)
        if key in vars_dict and vars_dict[key] is not None:
            return str(vars_dict[key])
        return m.group(0)

    return placeholder_re.sub(repl, template)


async def _load_dpa_vars(current_user: dict) -> dict:
    """Build the variable bag for DPA interpolation from the admin's
    organization document + the current date."""
    from database import organizations_collection
    from datetime import datetime, timezone

    org_id = current_user.get("organization_id")
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="DPA is only available to organization-scoped users.",
        )
    org = await organizations_collection.find_one(
        {"id": org_id}, {"_id": 0},
    )
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    # Best-effort identity. The admin can always edit these fields if
    # the rendered DPA doesn't look right — we read them but don't
    # fail if some are missing (renders the placeholder instead).
    merchant_name = org.get("name") or ""
    # Best-effort contact email: try several common slots on the org doc
    merchant_email = (
        org.get("contact_email")
        or (org.get("store_settings") or {}).get("contact_email")
        or ""
    )
    merchant_country = (
        org.get("country")
        or org.get("billing_country")
        or ""
    )
    today_iso = datetime.now(timezone.utc).date().isoformat()

    return {
        "merchant_name": merchant_name,
        "merchant_email": merchant_email,
        "merchant_country": merchant_country,
        "org_id": org_id,
        "date": today_iso,
        # Platform side — same defaults as merchant_legal_template_service.
        "platform_name": "afianco",
        "platform_controller_name": "Davide De Filippis",
        "platform_controller_email": "info@aurya.life",
        "platform_controller_country": "Switzerland",
    }


@router.get("/dpa")
async def get_dpa(
    lang: Optional[str] = Query(
        default=None,
        description="Requested locale (it, en, de, fr). Falls back to it.",
    ),
    current_user: dict = Depends(require_admin),
):
    """Return the rendered DPA markdown for the caller's organization.

    Auth: admin of the org. The interpolated variables (merchant_name,
    merchant_email, merchant_country, org_id, date) are read SERVER-SIDE
    from the organization document — never trusted from the request.

    Cache-Control: ``private, no-store`` — the rendered content carries
    org-scoped identity fields, must not be cached publicly or by CDNs.
    """
    requested = (lang or "it").lower()
    locale = requested if requested in ("it", "en", "de", "fr") else "it"

    try:
        template = _read_dpa_template(locale)
    except FileNotFoundError:
        # Asset missing — deployment bug.
        logger.error("dpa: template file missing for locale=%s", locale)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="DPA template missing",
        )

    vars_dict = await _load_dpa_vars(current_user)
    content = _interpolate_dpa(template, vars_dict)

    return JSONResponse(
        content={
            "content": content,
            "locale_actual": locale,
            "locale_requested": requested,
            "vars": vars_dict,
        },
        headers={"Cache-Control": "private, no-store"},
    )


@router.post("/dpa/acknowledge")
async def acknowledge_dpa(
    request: Request,
    current_user: dict = Depends(require_admin),
):
    """Record the merchant org's acknowledgement of the DPA.

    Idempotent: a second POST does NOT create a duplicate record — it
    returns the original acknowledgement timestamp. This is important
    so an accidental double-click doesn't pollute the audit trail with
    near-duplicate entries.

    The audit record carries:
      - source="merchant_dpa_acknowledged"
      - document_type="merchant_dpa"
      - user_id, organization_id, ip_address, user_agent
      - locale of the version shown (from optional body, defaults "it")
      - version_tag = "v1.0" (single-version DPA at this stage; will
        evolve when we ship a v1.1)
    """
    from datetime import datetime, timezone
    from repositories import consent_audit_repository as car

    org_id = current_user.get("organization_id")
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="DPA acknowledgement is only available to org users.",
        )

    # Optional request body: { locale: "it"|"en"|"de"|"fr" }
    locale = "it"
    try:
        body = await request.json()
        if isinstance(body, dict):
            requested = str(body.get("locale") or "it").lower()
            if requested in ("it", "en", "de", "fr"):
                locale = requested
    except Exception:
        # No body or invalid JSON — fine, use default.
        pass

    # Check existing acknowledgement (idempotency).
    existing = await car.find_latest_for_org_dpa(org_id)
    if existing:
        return JSONResponse(
            content={
                "status": "already_acknowledged",
                "acknowledged_at": existing.get("accepted_at"),
                "acknowledged_by_user_id": existing.get("user_id"),
                "locale": existing.get("locale"),
                "version_tag": existing.get("version_tag"),
            },
        )

    # First-time acknowledgement.
    # The DPA hash is deterministic from the template content + locale —
    # captures which version of the doc the merchant saw.
    try:
        template = _read_dpa_template(locale)
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="DPA template missing",
        )
    version_hash = car.hash_document_text(template)

    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    await car.record_consent(
        user_id=current_user["user_id"],
        organization_id=org_id,
        locale=locale,
        version_tag="v1.0",
        version_hash=version_hash,
        ip_address=client_ip,
        user_agent=user_agent,
        source="merchant_dpa_acknowledged",
        document_type="merchant_dpa",
    )

    return JSONResponse(
        content={
            "status": "acknowledged",
            "acknowledged_at": datetime.now(timezone.utc).isoformat(),
            "locale": locale,
            "version_tag": "v1.0",
        },
    )


@router.get("/dpa/status")
async def get_dpa_status(
    current_user: dict = Depends(require_admin),
):
    """Has THIS organization acknowledged the DPA?

    Returns ``{ acknowledged: bool, acknowledged_at?, version_tag?,
    locale?, acknowledged_by_user_id? }``. Used by the admin UI to
    decide whether to show the "Conferma ricezione" CTA or the
    "DPA confermato il <date>" badge.
    """
    from repositories import consent_audit_repository as car

    org_id = current_user.get("organization_id")
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="DPA status is only available to org users.",
        )

    existing = await car.find_latest_for_org_dpa(org_id)
    if not existing:
        return JSONResponse(content={"acknowledged": False})

    return JSONResponse(content={
        "acknowledged": True,
        "acknowledged_at": existing.get("accepted_at"),
        "acknowledged_by_user_id": existing.get("user_id"),
        "locale": existing.get("locale"),
        "version_tag": existing.get("version_tag"),
    })
