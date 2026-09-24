"""SA4 (24/9/2026) — il pulitore del profilo pubblico, estratto.

Fino a oggi tutta la logica di `PATCH /organizations/current/public-profile`
viveva inline nella rotta dell'operatore (routers/organizations.py). Ora
la rotta dell'operatore e quella del system admin
(`PATCH /admin/organizations/{id}/public-profile`) passano dalle STESSE
due funzioni: zero cambi di comportamento per l'operatore, un solo posto
da mantenere.

  pulisci(body, org)            → updates pronti per `$set` (whitelist
                                   _PUBLIC_PROFILE_FIELDS, nome_persona,
                                   social canonici, show_contacts,
                                   link_page, name, photos, languages,
                                   disciplines, translations, lat/lng,
                                   sedi/specchi)
  dopo_salvataggio(org_id, upd) → i cinque effetti: geocoding, allinea
                                   sedi, superficie pubblica, cache
                                   slug→org, IndexNow

Le costanti (whitelist, tetti, temi della pagina link) restano definite
in routers/organizations.py: i test le leggono li' e altri moduli le
importano da li'. Qui si importano in modo pigro per evitare il ciclo.
"""
import logging

from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def pulisci(body: dict, org: Optional[dict] = None) -> Dict[str, Any]:
    """Whitelist rigida + limiti lunghezza: nessun campo arbitrario
    puo' entrare nel documento org. `org` (il documento attuale) e'
    accettato per chi vorra' regole dipendenti dallo stato; oggi la
    pulizia non ne ha bisogno."""
    from routers.organizations import (_PUBLIC_PROFILE_FIELDS, _PP_LANGS,
                                       _PP_PHOTOS_MAX, _clean_link_page)
    body = body if isinstance(body, dict) else {}
    updates: Dict[str, Any] = {}
    for field, max_len in _PUBLIC_PROFILE_FIELDS.items():
        if field in body:
            val = body[field]
            if val is None or val == "":
                updates[f"public_profile.{field}"] = None
            elif isinstance(val, str):
                updates[f"public_profile.{field}"] = val.strip()[:max_len]
    # P1 — il nome della persona si salva pulito (spazi doppi via): e' la
    # stringa che compone il titolo pubblico
    if isinstance(updates.get("public_profile.nome_persona"), str):
        updates["public_profile.nome_persona"] = " ".join(updates["public_profile.nome_persona"].split())[:80] or None
    # LS (14/9/2026) — i social si salvano in forma canonica: «nome_utente»,
    # «@nome» o l'URL incollato dall'app diventano https://instagram.com/nome;
    # sito con https davanti; via il tracciamento (services.social_links)
    from services.social_links import NORMALIZZATORI
    for campo, fn in NORMALIZZATORI.items():
        chiave = f"public_profile.{campo}"
        if updates.get(chiave):
            updates[chiave] = (fn(updates[chiave]) or "")[:_PUBLIC_PROFILE_FIELDS[campo]] or None
    if "show_contacts" in body:
        updates["public_profile.show_contacts"] = bool(body["show_contacts"])
    # LK1 — pagina link: il client manda sempre lo stato COMPLETO
    # dell'editor, mai merge parziali; la validazione e' tutta in
    # _clean_link_page (https-only, tetti, tema dalla rosa)
    if "link_page" in body:
        updates["public_profile.link_page"] = _clean_link_page(body["link_page"])
    # OP4 — nome pubblico = organizations.name (la stessa riga che si
    # modifica dalle Impostazioni). Il vuoto NON cancella: un titolo
    # sparito romperebbe email, fatture e SEO.
    if isinstance(body.get("name"), str) and body["name"].strip():
        updates["name"] = body["name"].strip()[:120]
    # PR1 — liste con validazione dedicata
    if "photos" in body:
        photos = body["photos"] if isinstance(body["photos"], list) else []
        updates["public_profile.photos"] = [
            str(u).strip()[:500] for u in photos
            if isinstance(u, str) and u.strip()
        ][:_PP_PHOTOS_MAX]
    if "languages" in body:
        langs = body["languages"] if isinstance(body["languages"], list) else []
        updates["public_profile.languages"] = [
            l for l in langs if l in _PP_LANGS][:6]
    # DI (founder 14/8) — le discipline DICHIARATE dall'operatore:
    # slug dalla tassonomia unica, dedup, max 10 (clean_disciplines)
    if "disciplines" in body:
        from models.disciplines import clean_disciplines
        updates["public_profile.disciplines"] = clean_disciplines(
            body["disciplines"])
    # PV2 — l'intervista NON è più self-service: la scrive e pubblica il
    # system admin (PUT /admin/organizations/{id}/interview). Un client
    # vecchio che manda ancora "interview" viene ignorato in silenzio
    # (retrocompat: niente 4xx, il resto del salvataggio passa).
    # OP2 — profilo multilingua MANUALE, stessa logica dei prodotti:
    # translations = {en|de|fr: {bio, tagline}}, testi clip alle stesse
    # lunghezze dell'italiano, lingue sconosciute scartate in silenzio.
    if "translations" in body:
        raw = body["translations"] if isinstance(body["translations"], dict) else {}
        clean = {}
        for lang, fields in raw.items():
            if lang not in ("en", "de", "fr") or not isinstance(fields, dict):
                continue
            entry = {}
            for f, max_len in (("bio", 600), ("tagline", 80)):
                val = fields.get(f)
                if isinstance(val, str) and val.strip():
                    entry[f] = val.strip()[:max_len]
            if entry:
                clean[lang] = entry
        updates["public_profile.translations"] = clean or None
    # AN3 — posizione dell'operatore: lat/lng espliciti (autocomplete
    # località nel form) vincono; validati e trasformati in GeoJSON per
    # l'indice 2dsphere. La scoperta geografica non dipende più dai
    # ritiri futuri: è il PROFILO a dire dove sei.
    lat_raw, lng_raw = body.get("latitude"), body.get("longitude")
    if lat_raw is not None and lng_raw is not None:
        try:
            lat_f, lng_f = float(lat_raw), float(lng_raw)
            if -90 <= lat_f <= 90 and -180 <= lng_f <= 180:
                updates["public_profile.latitude"] = lat_f
                updates["public_profile.longitude"] = lng_f
                updates["public_profile.geo"] = {
                    "type": "Point", "coordinates": [lng_f, lat_f]}
        except (TypeError, ValueError):
            pass
    # SD1 (14/9/2026) — le SEDI (1..3): quando il client le manda sono la
    # verita'; city/region/latitude/longitude diventano SPECCHI della
    # sede principale e `geo` un MultiPoint di tutte (services.sedi).
    # Chi manda solo `city` (benvenuto, client vecchi) passa dal ramo
    # storico e _allinea_sedi_dagli_specchi conserva le altre sedi.
    if "sedi" in body:
        from services.sedi import normalizza_sedi, specchi
        _sedi = normalizza_sedi(body.get("sedi"))
        updates["public_profile.sedi"] = _sedi
        for _k, _v in specchi(_sedi).items():
            updates[f"public_profile.{_k}"] = _v
    return updates


async def dopo_salvataggio(org_id: str, updates: Optional[dict] = None) -> None:
    """I cinque effetti post-salvataggio, nell'ordine di sempre. Tutti
    best-effort: il salvataggio del profilo e' gia' avvenuto."""
    from routers.organizations import (_allinea_sedi_dagli_specchi,
                                       _ensure_public_surface,
                                       _geocode_profile_if_needed,
                                       _ping_operator_indexnow)
    # AN3 — geocoding best-effort: city presente ma niente coordinate
    # (form senza autocomplete, profili vecchi) → stessa cache
    # Nominatim delle occurrence. Mai bloccante.
    await _geocode_profile_if_needed(org_id)
    # SD1 — dopo un salvataggio storico (solo city/lat/lng) o un geocoding,
    # la sede principale segue gli specchi e le altre sedi restano
    await _allinea_sedi_dagli_specchi(org_id)
    # GT6 — gradino 0 profilo-first: il primo profilo con bio accende
    # la vetrina pubblica anche senza store ne' prodotti
    await _ensure_public_surface(org_id)
    # LK1 — chi salva il profilo e apre subito la propria pagina
    # pubblica deve vederla AGGIORNATA, non la copia di 45s fa: si
    # svuota la cache slug→org del mondo pubblico per questo slug.
    # Best-effort, mai bloccante (vale per tutto il profilo, non solo
    # per la pagina link).
    try:
        from routers.public import (_invalidate_resolve_org_cache,
                                    _resolve_public_slug_for_org)
        _slug = await _resolve_public_slug_for_org(org_id)
        if _slug:
            _invalidate_resolve_org_cache(_slug)
    except Exception:
        pass
    # SEO2 — IndexNow: profilo aggiornato → reindicizza /o/ e /s/ (prima
    # solo publish di ritiri/prodotti pingava; l'operatore che cura la
    # scheda LocalBusiness merita reindex rapido). Best-effort, mai blocca.
    await _ping_operator_indexnow(org_id)
    # 24/9 sera — UNA variabile nome: il profilo ha un nome persona nuovo
    # → l'account di chi si e' registrato lo segue (operatore o admin,
    # stessa strada). Best-effort, mai blocca.
    if updates and updates.get("public_profile.nome_persona"):
        try:
            from services.nome_persona import allinea_account
            await allinea_account(org_id, updates["public_profile.nome_persona"])
        except Exception as exc:  # noqa: BLE001
            logger.warning("nome persona non allineato sull'account per %s: %s", org_id, exc)
