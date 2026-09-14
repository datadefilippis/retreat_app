"""LS (14/9/2026) — i link social si NORMALIZZANO al salvataggio, in un punto solo.

Founder: «gli operatori sbagliano a inserire i link dei social: alla
maggior parte viene spontaneo inserire solo il nome utente e non l'URL».
Verificato in produzione: 4 profili Instagram su 10 erano il solo nome
utente e il sito costruiva `https://nome_utente` (link rotto); gli altri
sei erano URL incollati dall'app con parametri di tracciamento
(`?igsi=…`, `utm_source=qr`).

La regola: si accetta TUTTO cio' che una persona scrive spontaneamente
(nome utente, @nome, URL con o senza https, URL con tracciamento) e si
salva la forma canonica. Ogni pagina che mostra il link (profilo,
pagina link, dati per Google) legge il valore salvato e non deve
indovinare niente. Chi mostra un campo nel gestionale usa
`nome_utente_instagram` per far vedere il solo nome.

Instagram → https://instagram.com/<nome>   (nome: lettere, cifre, . _ ; max 30)
Facebook  → URL pulito dal tracciamento (i link «share/…» e
            «profile.php?id=…» restano cosi': funzionano); un nome nudo
            diventa https://facebook.com/<nome>
Sito      → https:// davanti se manca, tracciamento via, barra finale via
Un valore che non si riesce a leggere resta com'e' (mai perdere dati).
"""
import re
from typing import Dict, Optional
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

# parametri di tracciamento che le app appiccicano quando si copia un link
TRACCIANTI = {"igsi", "igshid", "igsh", "stkn", "fbclid", "mibextid", "si",
              "utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term", "utm_id"}
_RE_NOME_IG = re.compile(r"^[A-Za-z0-9._]{1,30}$")
_RE_NOME_FB = re.compile(r"^[A-Za-z0-9.\-]{2,60}$")


def _url_pulito(v: str, *, tieni_query: bool = True) -> Optional[str]:
    """https davanti se manca, via i parametri di tracciamento e la barra
    finale. None se non e' leggibile come indirizzo."""
    v = (v or "").strip()
    if not v:
        return None
    if not re.match(r"^https?://", v, re.I):
        v = "https://" + v
    try:
        parti = urlsplit(v)
    except ValueError:
        return None
    if not parti.netloc or "." not in parti.netloc:
        return None
    query = ""
    if tieni_query and parti.query:
        coppie = [(k, val) for k, val in parse_qsl(parti.query, keep_blank_values=True)
                  if k.lower() not in TRACCIANTI]
        query = urlencode(coppie)
    percorso = parti.path.rstrip("/") or ""
    return urlunsplit(("https", parti.netloc.lower(), percorso, query, ""))


def nome_utente_instagram(v: Optional[str]) -> Optional[str]:
    """Il solo nome utente, da un nome nudo, @nome o URL di Instagram."""
    v = (v or "").strip().lstrip("@")
    if not v:
        return None
    if "instagram.com" in v.lower():
        pulito = _url_pulito(v, tieni_query=False)
        segmenti = [s for s in urlsplit(pulito or "").path.split("/") if s] if pulito else []
        v = segmenti[0] if segmenti else ""
    v = v.strip().lstrip("@").rstrip("/")
    return v if _RE_NOME_IG.match(v) else None


def normalizza_instagram(v: Optional[str]) -> Optional[str]:
    v = (v or "").strip()
    if not v:
        return None
    nome = nome_utente_instagram(v)
    if nome:
        return f"https://instagram.com/{nome}"
    return _url_pulito(v) or v          # illeggibile: si conserva com'e'


def normalizza_facebook(v: Optional[str]) -> Optional[str]:
    v = (v or "").strip()
    if not v:
        return None
    if "/" not in v and "." not in v and _RE_NOME_FB.match(v.lstrip("@")):
        return f"https://facebook.com/{v.lstrip('@')}"
    if "facebook.com" not in v.lower() and "fb.com" not in v.lower() and not re.match(r"^https?://", v, re.I):
        if _RE_NOME_FB.match(v.lstrip("@")):
            return f"https://facebook.com/{v.lstrip('@')}"
    return _url_pulito(v) or v


def normalizza_sito(v: Optional[str]) -> Optional[str]:
    v = (v or "").strip()
    if not v:
        return None
    return _url_pulito(v) or v


NORMALIZZATORI = {
    "instagram": normalizza_instagram,
    "facebook": normalizza_facebook,
    "website": normalizza_sito,
}


def normalizza_social(pp: Dict) -> Dict:
    """Ritorna {campo: valore canonico} per i campi social presenti in pp
    (solo quelli che cambiano)."""
    out: Dict = {}
    for campo, fn in NORMALIZZATORI.items():
        if campo in pp and pp[campo]:
            nuovo = fn(pp[campo])
            if nuovo != pp[campo]:
                out[campo] = nuovo
    return out
