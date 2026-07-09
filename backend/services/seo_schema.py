"""SEO1 — costruttori schema.org, fonte unica per la SEO shell.

Funzioni PURE (nessun I/O): trasformano i dati già letti dal DB in
frammenti JSON-LD conformi a schema.org, così la logica di dati
strutturati vive in un posto solo (prima era inline in ogni resolver e
divergeva da ciò che emetteva il client).

Requisito founder: ritiri e operatori devono comparire sui motori con
la loro LOCATION. Qui costruiamo PostalAddress + GeoCoordinates + Offer
(rich result evento) e AggregateRating (stelle in SERP — solo su tipi
schema-eligibili: LocalBusiness/Organization, MAI su Event).
"""

from typing import Any, Dict, List, Optional

# Mesi per la data leggibile nei title/description (niente ISO grezzo in
# SERP). IT è la lingua sorgente della shell; le altre restano pronte.
_MONTHS = {
    "it": ["", "gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno",
           "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"],
    "en": ["", "January", "February", "March", "April", "May", "June",
           "July", "August", "September", "October", "November", "December"],
    "de": ["", "Januar", "Februar", "März", "April", "Mai", "Juni", "Juli",
           "August", "September", "Oktober", "November", "Dezember"],
    "fr": ["", "janvier", "février", "mars", "avril", "mai", "juin",
           "juillet", "août", "septembre", "octobre", "novembre", "décembre"],
}


def human_date(iso: Optional[str], lang: str = "it") -> str:
    """'2026-10-04T09:30:00' -> '4 ottobre 2026'. Fallback: prime 10 char."""
    if not iso or len(iso) < 10:
        return iso or ""
    try:
        y, mo, d = int(iso[:4]), int(iso[5:7]), int(iso[8:10])
        months = _MONTHS.get(lang, _MONTHS["it"])
        if lang == "en":
            return f"{months[mo]} {d}, {y}"
        return f"{d} {months[mo]} {y}"
    except (ValueError, IndexError):
        return iso[:10]


def postal_address(*, street: Optional[str] = None, city: Optional[str] = None,
                   region: Optional[str] = None, postal_code: Optional[str] = None,
                   country: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """PostalAddress schema.org. None se non c'è alcun campo utile."""
    fields: Dict[str, Any] = {}
    if street:
        fields["streetAddress"] = street
    if city:
        fields["addressLocality"] = city
    if region:
        fields["addressRegion"] = region
    if postal_code:
        fields["postalCode"] = postal_code
    if country:
        fields["addressCountry"] = country
    if not fields:
        return None
    return {"@type": "PostalAddress", **fields}


def geo_coordinates(lat: Any, lng: Any) -> Optional[Dict[str, Any]]:
    """GeoCoordinates. None se lat/lng mancano."""
    if lat is None or lng is None:
        return None
    return {"@type": "GeoCoordinates", "latitude": lat, "longitude": lng}


def place(*, name: Optional[str] = None,
          address: Optional[Dict[str, Any]] = None,
          geo: Optional[Dict[str, Any]] = None,
          fallback_name: str = "") -> Dict[str, Any]:
    """Place per Event.location: nome + PostalAddress + GeoCoordinates.
    address resta almeno una stringa (fallback) se non c'è un indirizzo
    strutturato, per non perdere il segnale locale."""
    p: Dict[str, Any] = {"@type": "Place", "name": name or fallback_name}
    p["address"] = address or (name or fallback_name)
    if geo:
        p["geo"] = geo
    return p


def offer(*, price: Any, currency: Optional[str] = "EUR",
          url: Optional[str] = None, availability: str = "InStock",
          valid_from: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Offer: prezzo nel rich result evento. None se price manca."""
    if price is None:
        return None
    try:
        price_val = round(float(price), 2)
    except (TypeError, ValueError):
        return None
    o: Dict[str, Any] = {
        "@type": "Offer",
        "price": price_val,
        "priceCurrency": currency or "EUR",
        "availability": f"https://schema.org/{availability}",
    }
    if url:
        o["url"] = url
    if valid_from:
        o["validFrom"] = valid_from
    return o


def aggregate_rating(stats: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """AggregateRating da reviews_stats {avg, count}. None se 0 recensioni.
    Va SOLO su LocalBusiness/Organization/Product, MAI su Event (Google
    non usa le stelle sugli eventi e segnala 'invalid')."""
    if not stats:
        return None
    count = stats.get("count") or 0
    avg = stats.get("avg")
    if not count or avg is None:
        return None
    return {
        "@type": "AggregateRating",
        "ratingValue": round(float(avg), 1),
        "reviewCount": count,
        "bestRating": 5,
        "worstRating": 1,
    }


def same_as(*urls: Optional[str]) -> List[str]:
    """sameAs: normalizza domini nudi (es. 'instagram.com/x') in URL
    assoluti https. Scarta i vuoti."""
    out: List[str] = []
    for u in urls:
        if not u:
            continue
        u = str(u).strip()
        if not u:
            continue
        if not u.startswith(("http://", "https://")):
            u = "https://" + u.lstrip("/")
        out.append(u)
    return out
