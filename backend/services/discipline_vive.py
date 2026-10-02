"""Il registro vivo delle discipline — DV1 (2/10/2026, founder: «il system
admin deve poter aggiungere discipline da solo e renderle disponibili a
tutti»). Piano: docs/ANALISI_DISCIPLINE_DINAMICHE_2026-10-02.md.

PRINCIPIO. Il codice resta la BASE (models/disciplines.py, con le sue
guardie); il database AGGIUNGE (collezione `discipline_extra`). Qui le due
cose si uniscono e si applicano IN PLACE alle strutture che tutto il
backend gia' legge — DISCIPLINES, DISCIPLINE_FAMILIES, DISCIPLINA_TO_CATEGORIA,
CATEGORIA_ARTICOLI, FAMIGLIA_DI — cosi' nessun consumatore cambia: la
directory, il profilo, la shell SEO, le pagine locali, la validazione del
PATCH vedono l'unione come se fosse sempre stata nel codice.

Regole (le stesse del documento):
  - lo slug e' IMMUTABILE e canonico (minuscolo, trattini);
  - una voce non si cancella: si SPEGNE (attiva=false) — resta valida per chi
    l'ha gia' (sta in DISCIPLINES) ma esce dal selettore (famiglie);
  - gli slug di codice non si sovrascrivono: dal db possono ricevere solo
    SINONIMI in piu' (documento con `arricchimento: true`);
  - famiglie e categorie restano di codice: dal db si sceglie dalla rosa;
  - interruttore DISCIPLINE_VIVE: spento = codice e basta (registro ignorato).

Quando si ricarica: all'avvio (lifespan), dopo ogni scrittura dalla regia,
e pigramente ogni 60 secondi quando qualcuno chiede l'elenco pubblico. In
prod gira un solo worker (gunicorn --workers 1): basta.
"""
from __future__ import annotations

import logging
import re
import time
import unicodedata
from typing import Any, Dict, List, Optional

from core.flags import discipline_vive
from models import disciplines as D
from models import retreat_taxonomy as RT

logger = logging.getLogger(__name__)

SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
SLUG_MAX = 40
LABEL_MIN, LABEL_MAX = 2, 60
SINONIMI_MAX = 12
_TTL = 60.0

# cosa abbiamo applicato l'ultima volta, per toglierlo prima di riapplicare
_stato: Dict[str, Any] = {"caricato_il": 0.0, "slug_applicati": [], "extra": []}


# ── slug ─────────────────────────────────────────────────────────────────

def slugify(label: str) -> str:
    """«Regressione & Vite passate» → «regressione-e-vite-passate»;
    accenti via, «&» diventa «e», tutto il resto non alfanumerico → trattino."""
    s = unicodedata.normalize("NFKD", str(label or "")).encode("ascii", "ignore").decode()
    s = s.lower().replace("&", " e ")
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    s = re.sub(r"-{2,}", "-", s)
    return s[:SLUG_MAX].strip("-")


def slug_valido(slug: str) -> bool:
    return bool(slug) and len(slug) <= SLUG_MAX and SLUG_RE.match(slug) is not None


# ── rosa delle scelte (di codice) ────────────────────────────────────────

def famiglie_rosa() -> List[Dict[str, str]]:
    return [{"slug": f, "label": l} for f, l, _ in D.DISCIPLINE_FAMILIES]


def categorie_ritiro_rosa() -> List[Dict[str, str]]:
    return [{"slug": k, "label": v} for k, v in RT.RETREAT_CATEGORIES.items()]


def categorie_articoli_rosa() -> List[str]:
    from services.pagine_locali import CATEGORIA_ARTICOLI
    return sorted(set(CATEGORIA_ARTICOLI.values()))


# ── applicazione in place ────────────────────────────────────────────────

def _famiglia(fslug: str):
    for f in D.DISCIPLINE_FAMILIES:
        if f[0] == fslug:
            return f
    return None


def _togli_precedenti() -> None:
    """Via tutto cio' che l'ultima applicazione aveva aggiunto (mai le voci di codice)."""
    from services.pagine_locali import CATEGORIA_ARTICOLI, FAMIGLIA_DI
    for slug in _stato["slug_applicati"]:
        if slug in D.DISCIPLINE_CODICE:
            continue
        D.DISCIPLINES.pop(slug, None)
        RT.DISCIPLINA_TO_CATEGORIA.pop(slug, None)
        CATEGORIA_ARTICOLI.pop(slug, None)
        FAMIGLIA_DI.pop(slug, None)
        for f in D.DISCIPLINE_FAMILIES:
            f[2][:] = [v for v in f[2] if v[0] != slug]
    _stato["slug_applicati"] = []


def _applica(extra: List[dict]) -> None:
    from services.pagine_locali import CATEGORIA_ARTICOLI, FAMIGLIA_DI
    _togli_precedenti()
    applicati: List[str] = []
    for doc in extra:
        slug = doc.get("slug")
        if not slug_valido(slug or ""):
            continue
        if slug in D.DISCIPLINE_CODICE:
            continue            # arricchimento di una voce di codice: solo sinonimi (vedi sinonimi_extra)
        fam = _famiglia(doc.get("famiglia") or "")
        if fam is None:
            logger.warning("discipline_vive: famiglia ignota per %s, voce saltata", slug)
            continue
        label = str(doc.get("label") or slug).strip()[:LABEL_MAX]
        # la voce vale SEMPRE per chi l'ha gia' scelta (etichetta, categorie)...
        D.DISCIPLINES[slug] = label
        RT.DISCIPLINA_TO_CATEGORIA[slug] = doc.get("categoria") or "crescita"
        CATEGORIA_ARTICOLI[slug] = doc.get("cat_articoli") or RT.DISCIPLINA_TO_CATEGORIA[slug]
        FAMIGLIA_DI[slug] = (fam[0], fam[1])
        # ...ma entra nel selettore (famiglie) solo se ATTIVA
        if doc.get("attiva", True):
            fam[2].append((slug, label))
        applicati.append(slug)
    _stato["slug_applicati"] = applicati
    _stato["extra"] = list(extra)


# ── caricamento ──────────────────────────────────────────────────────────

async def ricarica() -> int:
    """Rilegge il registro e lo applica. Col flag spento applica il vuoto
    (= codice e basta). Ritorna quante voci extra sono applicate."""
    extra: List[dict] = []
    if discipline_vive():
        try:
            from database import discipline_extra_collection
            extra = await discipline_extra_collection.find(
                {}, {"_id": 0}).sort("creata_il", 1).to_list(500)
        except Exception:  # noqa: BLE001 — il registro non deve mai rompere il sito
            logger.exception("discipline_vive: registro non leggibile, resta il codice")
            extra = []
    _applica(extra)
    _stato["caricato_il"] = time.monotonic()
    return len(_stato["slug_applicati"])


async def assicura_fresco() -> None:
    if time.monotonic() - _stato["caricato_il"] > _TTL:
        await ricarica()


def extra_applicate() -> List[dict]:
    return list(_stato["extra"])


# ── cosa vede il mondo ───────────────────────────────────────────────────

def sinonimi_extra() -> Dict[str, List[str]]:
    """I sinonimi che vivono nel registro: delle voci nuove e gli
    arricchimenti delle voci di codice (il frontend li somma ai suoi)."""
    out: Dict[str, List[str]] = {}
    for doc in _stato["extra"]:
        if not doc.get("attiva", True) and doc.get("slug") not in D.DISCIPLINE_CODICE:
            continue
        sin = [str(x).strip() for x in (doc.get("sinonimi") or []) if str(x).strip()]
        if sin:
            out[doc["slug"]] = sin[:SINONIMI_MAX]
    return out


def payload_pubblico() -> Dict[str, Any]:
    """GET /public/discipline — l'unione, nella forma di lib/disciplines.js."""
    return {
        "vive": discipline_vive(),
        "famiglie": [
            {"slug": f, "label": l, "items": [{"slug": s, "label": lab} for s, lab in items]}
            for f, l, items in D.DISCIPLINE_FAMILIES
        ],
        "sinonimi": sinonimi_extra(),
        "extra": [d["slug"] for d in _stato["extra"] if d.get("attiva", True)
                  and d.get("slug") not in D.DISCIPLINE_CODICE],
        "totale": len(D.DISCIPLINES),
    }


# ── validazione per la regia ─────────────────────────────────────────────

def valida_nuova(body: dict) -> dict:
    """Corpo del POST della regia → documento pronto, o ValueError col motivo."""
    label = " ".join(str(body.get("label") or "").split())
    if not (LABEL_MIN <= len(label) <= LABEL_MAX):
        raise ValueError(f"Etichetta: da {LABEL_MIN} a {LABEL_MAX} caratteri.")
    slug = str(body.get("slug") or "").strip().lower() or slugify(label)
    if not slug_valido(slug):
        raise ValueError("Identificativo non valido: solo minuscole, numeri e trattini.")
    if slug in D.DISCIPLINES:
        raise ValueError(f"«{slug}» esiste già: scegline un altro.")
    fam = _famiglia(body.get("famiglia") or "")
    if fam is None:
        raise ValueError("Scegli una famiglia dalla lista.")
    categoria = body.get("categoria") or ""
    if categoria not in RT.RETREAT_CATEGORIES:
        raise ValueError("Scegli una categoria di ritiro dalla lista.")
    cat_articoli = body.get("cat_articoli") or categoria
    if cat_articoli not in categorie_articoli_rosa() and cat_articoli not in RT.RETREAT_CATEGORIES:
        raise ValueError("Scegli una categoria del Magazine dalla lista.")
    sinonimi = pulisci_sinonimi(body.get("sinonimi"))
    # doppioni per etichetta (stessa parola gia' in tassonomia, al netto di maiuscole/accenti)
    simile = next((s for s, l in D.DISCIPLINES.items() if slugify(l) == slugify(label)), None)
    if simile:
        raise ValueError(f"Esiste già una voce con questo nome («{D.DISCIPLINES[simile]}», {simile}).")
    return {"slug": slug, "label": label, "famiglia": fam[0], "categoria": categoria,
            "cat_articoli": cat_articoli, "sinonimi": sinonimi, "attiva": True}


def pulisci_sinonimi(raw) -> List[str]:
    if isinstance(raw, str):
        raw = [p for p in re.split(r"[,\n;]", raw)]
    if not isinstance(raw, list):
        return []
    out: List[str] = []
    for p in raw:
        p = " ".join(str(p or "").split()).lower()
        if p and p not in out and len(p) <= 40:
            out.append(p)
        if len(out) >= SINONIMI_MAX:
            break
    return out


def simili(label: str) -> List[Dict[str, str]]:
    """Per l'avviso prima di salvare: voci la cui etichetta o slug contiene
    una parola della nuova (parole di almeno 4 lettere)."""
    parole = [p for p in re.split(r"[^a-z0-9]+", slugify(label).replace("-", " ")) if len(p) >= 4]
    out = []
    for s, l in D.DISCIPLINES.items():
        testo = f"{s} {slugify(l)}"
        if any(p in testo for p in parole):
            out.append({"slug": s, "label": l})
    return out[:6]
