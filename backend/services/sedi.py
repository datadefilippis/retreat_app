"""SD (14/9/2026) — le SEDI dell'operatore: da una localita' a tre.

Founder: «piu' di un operatore vorrebbe inserire piu' localita' in cui
opera (massimo 3); tutte nel profilo; chi opera in Puglia e in Lombardia
compare in entrambe nei filtri della directory. Integrazione, non reset:
chi ha gia' una localita' non perde niente».

Come e' fatto (docs/ANALISI_PIU_SEDI_2026-09-14.md):
- `public_profile.sedi` = lista di 1..MAX_SEDI voci
  {citta, provincia, regione, paese, lat, lng, etichetta}; la prima e'
  la sede PRINCIPALE.
- i quattro campi storici `city`, `region`, `latitude`, `longitude`
  restano e sono SPECCHI della sede principale (ricalcolati qui, mai
  editati a parte): i quindici lettori esistenti non si toccano.
- `geo` = MultiPoint di tutte le sedi con coordinate: l'indice 2dsphere
  e la $geoNear della directory restano identici e la distanza e' quella
  dalla sede piu' vicina (provato: un documento, nessun doppione).
- `sedi_da_profilo(pp)` ricava le sedi ANCHE da un profilo non ancora
  migrato: la localita' di ieri E' la sede principale, per costruzione.
- la regione e' canonica (le 20 regioni dei ritiri) o vuota (estero).
"""
import math
import re
from typing import Any, Dict, List, Optional, Tuple

from models.event_occurrence import ITALIAN_REGIONS

MAX_SEDI = 3
_REGIONI_LOWER = {r.lower(): r for r in ITALIAN_REGIONS}
# Nominatim scrive le regioni bilingui con la barra: si tiene la parte italiana
_ALIAS = {"trentino-alto adige/sudtirol": "Trentino-Alto Adige",
          "trentino-alto adige/südtirol": "Trentino-Alto Adige",
          "trentino alto adige": "Trentino-Alto Adige",
          "valle d'aosta/vallée d'aoste": "Valle d'Aosta",
          "valle d'aosta/vallee d'aoste": "Valle d'Aosta",
          "vallée d'aoste": "Valle d'Aosta",
          "emilia romagna": "Emilia-Romagna",
          "friuli venezia giulia": "Friuli-Venezia Giulia",
          "friuli-venezia giulia": "Friuli-Venezia Giulia"}


def regione_canonica(v: Optional[str]) -> Optional[str]:
    """«puglia», «Trentino-Alto Adige/Südtirol» → la regione come la
    scrivono i ritiri; None se non e' una regione italiana."""
    s = (v or "").strip()
    if not s:
        return None
    low = s.lower()
    if low in _REGIONI_LOWER:
        return _REGIONI_LOWER[low]
    if low in _ALIAS:
        return _ALIAS[low]
    testa = low.split("/")[0].strip()
    return _REGIONI_LOWER.get(testa) or _ALIAS.get(testa)


def _coord(v: Any, lo: float, hi: float) -> Optional[float]:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if lo <= f <= hi else None


def _testo(v: Any, n: int) -> Optional[str]:
    if not isinstance(v, str):
        return None
    s = re.sub(r"\s+", " ", v).strip()[:n]
    return s or None


def normalizza_sede(raw: Any) -> Optional[Dict[str, Any]]:
    """Una sede pulita da cio' che arriva dal client (o dai campi
    storici). None se non c'e' ne' citta' ne' regione."""
    if not isinstance(raw, dict):
        return None
    citta = _testo(raw.get("citta"), 80)
    regione = regione_canonica(raw.get("regione"))
    # citta' che in realta' e' una regione («Umbria», «Puglia» scelte
    # dalla lista): e' la sede «tutta la regione»
    if citta and not regione and regione_canonica(citta):
        regione, citta = regione_canonica(citta), None
    if citta and regione and citta.lower() == regione.lower():
        citta = None
    if not citta and not regione:
        return None
    lat = _coord(raw.get("lat"), -90, 90)
    lng = _coord(raw.get("lng"), -180, 180)
    if lat is None or lng is None:
        lat = lng = None
    provincia = _testo(raw.get("provincia"), 40)
    if provincia and citta and provincia.lower() == citta.lower():
        provincia = None
    paese = _testo(raw.get("paese"), 60) or "Italia"
    sede = {"citta": citta, "provincia": provincia, "regione": regione,
            "paese": paese, "lat": lat, "lng": lng}
    sede["etichetta"] = _testo(raw.get("etichetta"), 160) or etichetta_sede(sede)
    return sede


def normalizza_sedi(lista: Any) -> List[Dict[str, Any]]:
    """Max MAX_SEDI, senza doppioni (stessa citta'+regione), ordine tenuto."""
    out: List[Dict[str, Any]] = []
    viste = set()
    for raw in (lista if isinstance(lista, list) else []):
        s = normalizza_sede(raw)
        if not s:
            continue
        chiave = ((s["citta"] or "").lower(), (s["regione"] or "").lower(), (s["paese"] or "").lower())
        if chiave in viste:
            continue
        viste.add(chiave)
        out.append(s)
        if len(out) >= MAX_SEDI:
            break
    return out


def sedi_da_profilo(pp: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Le sedi di un profilo, migrato o no: se `sedi` manca, la
    localita' storica (city/region/lat/lng) E' la sede principale."""
    pp = pp or {}
    if isinstance(pp.get("sedi"), list) and pp["sedi"]:
        return normalizza_sedi(pp["sedi"])
    if not pp.get("city") and not pp.get("region"):
        return []
    s = normalizza_sede({"citta": pp.get("city"), "regione": pp.get("region"),
                         "lat": pp.get("latitude"), "lng": pp.get("longitude")})
    return [s] if s else []


def etichetta_sede(s: Dict[str, Any]) -> str:
    """«Ostuni, Puglia» · «Bellinzona, Svizzera» · «tutta la Puglia»."""
    citta, regione, paese = s.get("citta"), s.get("regione"), s.get("paese") or "Italia"
    if citta and regione:
        return f"{citta}, {regione}"
    if citta:
        return citta if paese == "Italia" else f"{citta}, {paese}"
    return f"tutta la {regione}" if regione else ""


def dove_testo(pp: Optional[Dict[str, Any]], sep: str = " · ") -> str:
    """La riga «dove» per shell SEO, llms.txt, elenchi: tutte le sedi."""
    return sep.join(etichetta_sede(s) for s in sedi_da_profilo(pp) if etichetta_sede(s))


def geo_multipoint(sedi: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    punti = [[s["lng"], s["lat"]] for s in sedi if s.get("lat") is not None and s.get("lng") is not None]
    if not punti:
        return None
    return {"type": "MultiPoint", "coordinates": punti}


def specchi(sedi: List[Dict[str, Any]]) -> Dict[str, Any]:
    """I quattro campi storici + geo, dalla sede principale (e da tutte
    le sedi per geo). `city` non resta mai vuota se c'e' una sede: i
    lettori di ieri («a {city}») continuano a parlare."""
    if not sedi:
        return {"city": None, "region": None, "latitude": None, "longitude": None, "geo": None}
    p = sedi[0]
    return {"city": p.get("citta") or p.get("regione"),
            "region": p.get("regione"),
            "latitude": p.get("lat"), "longitude": p.get("lng"),
            "geo": geo_multipoint(sedi)}


def slug_destinazione(s: Dict[str, Any]) -> Optional[str]:
    """Lo slug di /destinazioni/{…}: regione se c'e', altrimenti citta'
    (stessa regola di placeSlugOf nel frontend)."""
    import unicodedata
    base = s.get("regione") or s.get("citta")
    if not base:
        return None
    t = unicodedata.normalize("NFKD", base).encode("ascii", "ignore").decode().lower()
    t = re.sub(r"[^a-z0-9]+", "-", t).strip("-")
    return t or None


def sede_pubblica(s: Dict[str, Any]) -> Dict[str, Any]:
    """La forma per le API pubbliche (directory, profilo)."""
    return {"citta": s.get("citta"), "provincia": s.get("provincia"),
            "regione": s.get("regione"), "paese": s.get("paese") or "Italia",
            "lat": s.get("lat"), "lng": s.get("lng"),
            "etichetta": etichetta_sede(s), "destinazione": slug_destinazione(s)}


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def sede_piu_vicina(sedi: List[Dict[str, Any]], lat: float, lng: float
                    ) -> Tuple[Optional[Dict[str, Any]], Optional[float]]:
    """(sede, km) piu' vicina a un punto; (None, None) senza coordinate."""
    migliore, km = None, None
    for s in sedi:
        if s.get("lat") is None or s.get("lng") is None:
            continue
        d = haversine_km(lat, lng, s["lat"], s["lng"])
        if km is None or d < km:
            migliore, km = s, d
    return migliore, (round(km, 1) if km is not None else None)


def nomi_luoghi(sedi: List[Dict[str, Any]]) -> set:
    """Citta' e regioni di tutte le sedi: alimenta `regions` della
    directory (e quindi /destinazioni) e il filtro testuale ?luogo."""
    out = set()
    for s in sedi:
        for k in ("citta", "regione", "provincia"):
            if s.get(k):
                out.add(s[k])
    return out
