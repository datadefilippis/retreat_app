"""SEO-B (14/9/2026 sera) — le PAGINE LOCALI della directory.

Analisi SEO (docs/ANALISI_SEO_PIATTAFORMA_2026-09-14.md, gap G1): le
ricerche che portano clienti sono locali («yoga Lecce», «operatore
olistico Puglia»), e nessuna pagina del sito le intercettava:
/operatori/{categoria} canonicalizzava a /operatori, le destinazioni
nascevano dai ritiri. Da oggi:

  /operatori/{disciplina}                Yoga: operatori in Italia
  /operatori/{regione}                   Operatori olistici in Puglia
  /operatori/{disciplina}/{regione}      Yoga in Puglia

Regola anti-thin: una pagina e' INDICIZZABILE (canonical di se stessa,
in sitemap) solo con almeno SOGLIA operatori; sotto esiste, si naviga,
ma e' noindex. I titoli/description/intro vivono QUI e li usano sia la
shell per i crawler sia la pagina viva (via l'API): una verita' sola.
Un solo posto anche per l'ordine dei segmenti: prima si prova la
disciplina, poi la regione, poi la categoria di prodotto (legacy).
"""
from typing import Any, Dict, List, Optional, Tuple

from models.disciplines import DISCIPLINES, DISCIPLINE_FAMILIES
from models.event_occurrence import ITALIAN_REGIONS
from services.sedi import luogo_seo, sedi_da_profilo, slug_destinazione

SOGLIA = 3   # operatori minimi perche' la pagina locale si indicizzi

REGIONE_DA_SLUG: Dict[str, str] = {slug_destinazione({"regione": r}): r for r in ITALIAN_REGIONS}
FAMIGLIA_DI: Dict[str, Tuple[str, str]] = {}
for _fam_slug, _fam_label, _voci in DISCIPLINE_FAMILIES:
    for _slug, _ in _voci:
        FAMIGLIA_DI[_slug] = (_fam_slug, _fam_label)

# una frase per famiglia: e' l'intro della pagina (mai promesse, mai numeri)
INTRO_FAMIGLIA = {
    "corpo": "Pratiche che passano dal corpo e dal movimento: lezioni individuali, piccoli gruppi, percorsi nel tempo.",
    "mente": "Pratiche per la mente e il respiro: sessioni guidate, percorsi di consapevolezza, incontri regolari.",
    "massaggio": "Trattamenti e lavoro sul corpo, in studio o a domicilio, con la mano di chi li pratica da anni.",
    "energia": "Pratiche energetiche e vibrazionali, in presenza e in alcuni casi a distanza.",
    "natura": "Rimedi naturali, consulenze e percorsi che partono dalla natura e dall'alimentazione.",
    "anima": "Percorsi interiori e di crescita personale, in sessioni individuali o in cerchio.",
}

# disciplina → categoria del Magazine con articoli (per il link «Leggi»)
CATEGORIA_ARTICOLI = {
    "yoga": "yoga", "pilates": "yoga",
    "meditazione": "meditazione", "mindfulness": "meditazione", "training-autogeno": "meditazione",
    "breathwork": "breathwork",
    "sound-healing": "suono",
    "reiki": "reiki", "pranoterapia": "reiki", "cristalloterapia": "reiki", "theta-healing": "reiki",
    "access-bars": "reiki", "kinesiologia": "reiki",
    "allineamento-chakra": "reiki", "lavoro-energetico-chakra": "reiki",
    "costellazioni-familiari": "costellazioni",
    "astrologia": "astrologia", "tarocchi-evolutivi": "astrologia", "numerologia": "astrologia",
    "massaggio-olistico": "massaggio", "shiatsu": "massaggio", "massaggio-thai": "massaggio",
    "riflessologia": "massaggio", "craniosacrale": "massaggio", "linfodrenaggio": "massaggio", "hot-stone": "massaggio",
    "massaggio-ayurvedico": "ayurveda", "consulenza-ayurvedica": "ayurveda",
    "cerchi-di-donne": "femminile", "sacro-femminile": "femminile",
    "naturopatia": "naturopatia", "aromaterapia": "naturopatia", "floriterapia": "naturopatia",
    "erboristeria": "naturopatia", "alimentazione-olistica": "naturopatia",
    "counseling-olistico": "crescita", "coaching-olistico": "crescita",
}


def risolvi(a: Optional[str], b: Optional[str] = None) -> Dict[str, Optional[str]]:
    """Da /operatori/{a}[/{b}] a {disciplina, regione, categoria}.
    `a` puo' essere disciplina, regione o categoria di prodotto (legacy);
    `b` solo regione. Ignoto → tutto None (la pagina resta /operatori)."""
    out: Dict[str, Optional[str]] = {"disciplina": None, "regione": None, "categoria": None, "valida": True}
    a = (a or "").strip().lower() or None
    b = (b or "").strip().lower() or None
    if a in DISCIPLINES:
        out["disciplina"] = a
        if b:
            if b in REGIONE_DA_SLUG:
                out["regione"] = REGIONE_DA_SLUG[b]
            else:
                out["valida"] = False
    elif a in REGIONE_DA_SLUG:
        out["regione"] = REGIONE_DA_SLUG[a]
        if b:
            out["valida"] = False
    elif a:
        out["categoria"] = a          # legacy: categoria di prodotto
        if b:
            out["valida"] = False
    return out


def percorso(disciplina: Optional[str], regione: Optional[str]) -> str:
    seg = [s for s in (disciplina, slug_destinazione({"regione": regione}) if regione else None) if s]
    return "/operatori" + ("/" + "/".join(seg) if seg else "")


def regione_di(pp: Dict[str, Any]) -> List[str]:
    """Le regioni (canoniche) di tutte le sedi dell'operatore."""
    return sorted({s["regione"] for s in sedi_da_profilo(pp) if s.get("regione")})


def appartiene(pp: Dict[str, Any], disciplina: Optional[str], regione: Optional[str]) -> bool:
    if disciplina and disciplina not in (pp.get("disciplines") or []):
        return False
    if regione and regione not in regione_di(pp):
        return False
    return True


def conteggi(profili: List[Dict[str, Any]]) -> Dict[Tuple[Optional[str], Optional[str]], int]:
    """{(disciplina|None, regione|None): n} per ogni pagina locale
    possibile, dai profili pubblici (public_profile di ciascuno)."""
    out: Dict[Tuple[Optional[str], Optional[str]], int] = {}
    for pp in profili:
        disc = [d for d in (pp.get("disciplines") or []) if d in DISCIPLINES]
        regs = regione_di(pp)
        chiavi = {(d, None) for d in disc} | {(None, r) for r in regs} | {(d, r) for d in disc for r in regs}
        for k in chiavi:
            out[k] = out.get(k, 0) + 1
    return out


def indicizzabili(profili: List[Dict[str, Any]]) -> List[Tuple[Optional[str], Optional[str], int]]:
    """Le pagine locali che superano la soglia (per la sitemap)."""
    return sorted(((d, r, n) for (d, r), n in conteggi(profili).items() if n >= SOGLIA),
                  key=lambda x: (x[0] or "", x[1] or ""))


def _in_regione(regione: str) -> str:
    return luogo_seo({"sedi": [{"regione": regione}]})   # «in Puglia», «nel Lazio»


def meta(disciplina: Optional[str], regione: Optional[str], n: int) -> Dict[str, Any]:
    """title/description/h1/intro/canonical/noindex della pagina locale.
    Stesse stringhe per shell e client."""
    label = DISCIPLINES.get(disciplina) if disciplina else None
    dove = _in_regione(regione) if regione else "in Italia"
    fam = FAMIGLIA_DI.get(disciplina, (None, None))[0] if disciplina else None
    if disciplina and regione:
        title = f"{label} {dove}: operatori e professionisti | Aurya"
        h1 = f"{label} {dove}"
        descr = (f"Operatori di {label.lower()} {dove}: pratiche, prezzi, "
                 f"recensioni verificate e contatto diretto su Aurya.")
    elif disciplina:
        title = f"{label}: operatori e professionisti in Italia | Aurya"
        h1 = f"{label} in Italia"
        descr = (f"Chi pratica {label.lower()} in Italia, con listino, sedi e recensioni verificate. "
                 f"Trova il professionista giusto vicino a te su Aurya.")
    elif regione:
        title = f"Operatori olistici {dove} | Aurya"
        h1 = f"Operatori olistici {dove}"
        descr = (f"Professionisti del benessere {dove}: yoga, meditazione, massaggi, pratiche energetiche, "
                 f"con listino, recensioni e contatto diretto su Aurya.")
    else:
        title = "Operatori olistici e professionisti del benessere in Italia | Aurya"
        h1 = "I professionisti della rete Aurya"
        descr = "Scopri i professionisti del benessere su Aurya: pratiche, discipline e percorsi, raccontati uno a uno."
    intro = INTRO_FAMIGLIA.get(fam) if fam else None
    # Google taglia a ~65 caratteri: le combinazioni lunghe («Costellazioni
    # familiari in Friuli-Venezia Giulia») perdono la coda, mai il luogo
    if len(title) > 65 and (disciplina or regione):
        title = f"{h1} | Aurya"
    return {"title": title, "h1": h1, "description": descr, "intro": intro,
            "path": percorso(disciplina, regione),
            "disciplina": disciplina, "disciplina_label": label, "regione": regione,
            "n": n, "indicizzabile": (n >= SOGLIA) if (disciplina or regione) else (n > 0),
            "categoria_articoli": CATEGORIA_ARTICOLI.get(disciplina) if disciplina else None}


def briciole(disciplina: Optional[str], regione: Optional[str]) -> List[Tuple[str, str]]:
    out = [("Aurya", "/"), ("Professionisti", "/operatori")]
    if disciplina:
        out.append((DISCIPLINES[disciplina], percorso(disciplina, None)))
    if regione:
        out.append((regione, percorso(disciplina, regione)))
    return out


def pagine_per_profilo(pp: Dict[str, Any], contatori: Dict[Tuple[Optional[str], Optional[str]], int]
                       ) -> List[Dict[str, str]]:
    """SEO-C — i link «Altri operatori di Yoga in Puglia» dal profilo:
    solo verso pagine che superano la soglia (mai verso una noindex)."""
    out: List[Dict[str, str]] = []
    visti = set()
    disc = [d for d in (pp.get("disciplines") or []) if d in DISCIPLINES]
    regs = regione_di(pp)
    candidati = [(d, r) for d in disc for r in regs] + [(d, None) for d in disc] + [(None, r) for r in regs]
    for d, r in candidati:
        if contatori.get((d, r), 0) < SOGLIA or (d, r) in visti:
            continue
        visti.add((d, r))
        m = meta(d, r, contatori[(d, r)])
        out.append({"label": m["h1"], "path": m["path"]})
        if len(out) >= 4:
            break
    return out


async def profili_pubblici() -> List[Dict[str, Any]]:
    """I public_profile degli operatori pubblici (stesso perimetro della
    directory e della sitemap)."""
    from database import organizations_collection
    return [o.get("public_profile") or {} async for o in organizations_collection.find(
        {"is_sample": {"$ne": True}, "is_active": {"$ne": False},
         "exclude_from_listings": {"$ne": True}, "public_slug": {"$nin": [None, ""]}},
        {"_id": 0, "public_profile.disciplines": 1, "public_profile.sedi": 1,
         "public_profile.city": 1, "public_profile.region": 1})]


async def contatori_locali() -> Dict[Tuple[Optional[str], Optional[str]], int]:
    """{(disciplina, regione): n}: quali pagine locali esistono e quali link
    mettere nei profili."""
    return conteggi(await profili_pubblici())
