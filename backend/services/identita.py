"""L'IDENTITÀ DI AURYA, in un posto solo (ciclo LX, 5/9/2026).

Domanda del founder: «i vari LLM hanno tutto il contesto per leggere e
proporre Aurya in tutte le sue forme?». Verificato sul vivo: i crawler
delle AI vedono lo stesso HTML di Google, ma l'Organization nel
JSON-LD diceva ancora «la casa dei ritiri: trova e prenota» (il
marketplace spento a luglio), /llms.txt conosceva solo Magazine e
rete, e Chi siamo / Manifesto / Per i professionisti / il Cerchio
erano gusci da 200 caratteri per i bot.

Qui vive UNA descrizione del brand (riusata da JSON-LD, llms.txt e
renderer), i PILASTRI con una riga onesta ciascuno, e i corpi delle
pagine cardine costruiti dalla copia italiana vera
(backend/assets/copia_it/*.json = frontend/src/locales/it/*.json,
tenuti uguali da scripts/copia_locales.py e dalla guardia LX). Il
testo che legge una persona e quello che legge un modello sono lo
stesso: niente da mantenere due volte, niente cloaking.
"""
import html as _html
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

_ASSETS = Path(__file__).resolve().parents[1] / "assets" / "copia_it"

IDENTITA = {
    "name": "Aurya",
    "tagline": "Ci si fida di qualcuno, non di qualcosa.",
    "description": (
        "Aurya è la rete italiana dei professionisti del benessere, "
        "raccontati uno a uno con interviste verificate, e uno spazio per "
        "orientarsi prima di scegliere: un Magazine di guide oneste sulle "
        "pratiche olistiche, Aurya Sound (una biblioteca educativa sul "
        "suono con esperienze d'ascolto gratuite, un laboratorio del suono "
        "nel browser e Crea Studio per comporre meditazioni), le "
        "meditazioni riservate al Cerchio di Aurya, e i ritiri e le "
        "esperienze dei professionisti della rete. In italiano, senza "
        "promesse di guarigione, con le fonti citate."),
    "email": "info@aurya.life",
    "sameAs": ["https://www.instagram.com/aurya.life"],
    "foundingDate": "2026",
    "founders": ["Davide De Filippis", "Valentina"],
    "inLanguage": "it",
    "areaServed": "IT",
    "knowsAbout": [
        "benessere olistico", "professionisti del benessere in Italia",
        "ritiri olistici", "yoga", "meditazione e mindfulness", "breathwork",
        "ayurveda", "naturopatia", "massaggio e bodywork", "reiki e pratiche "
        "energetiche", "sound healing", "frequenze e onde cerebrali",
        "battiti binaurali e toni isocronici", "meditazioni guidate",
    ],
}

# I PILASTRI: (slug, nome, riga onesta). È l'elenco che un modello deve
# poter recitare per dire «cos'è Aurya» per intero.
PILASTRI: List[Tuple[str, str, str]] = [
    ("/operatori", "La rete dei professionisti",
     "Professionisti del benessere raccontati uno a uno, con profilo pubblico, "
     "listino, richieste di appuntamento, eventi e ritiri prenotabili dal profilo."),
    ("/blog", "Il Magazine",
     "Guide oneste sulle pratiche olistiche, per argomento: cosa sono, cosa dice "
     "la ricerca, costi reali, come scegliere chi le conduce."),
    ("/sound", "Aurya Sound",
     "Tre esperienze d'ascolto gratuite (CALM, GROUND, RESPIRO), una biblioteca "
     "educativa di schede su bande cerebrali, frequenze e metodi con il livello di "
     "evidenza dichiarato, Le fondamenta e il glossario."),
    ("/sound/lab", "Il Laboratorio del suono",
     "Un banco vero nel browser: generatore, oscilloscopio, spettro, microfono, il "
     "Ritratto di un suono registrato, le Meraviglie, le Risonanze."),
    ("/sound/studio", "Crea Studio",
     "L'atelier con cui nascono le meditazioni di Aurya: voce registrata dal browser, "
     "basi sonore, frequenze, scena visiva."),
    ("/meditazioni", "Le meditazioni",
     "Sessioni sonore composte dai professionisti della rete; l'ascolto completo è "
     "per chi è nel Cerchio di Aurya, gratis."),
    ("/newsletter", "Il Cerchio di Aurya",
     "Meditazioni riservate, ritiri ed esperienze in anteprima e una lettera quando "
     "vale la pena. Gratis, una conferma via email."),
    ("/entra-nella-rete", "Per i professionisti",
     "Come entrare nella rete: profilo raccontato con cura, gestionale per listino, "
     "appuntamenti, eventi e ritiri, vendita online dal profilo."),
    ("/manifesto", "Il Manifesto",
     "Perché esistiamo, in cosa crediamo, i cinque principi."),
    ("/chi-siamo", "Chi siamo",
     "Davide e Valentina, le due persone dietro Aurya, e come lavorano."),
]


def _copia(ns: str) -> Dict:
    try:
        return json.loads((_ASSETS / f"{ns}.json").read_text(encoding="utf-8"))
    except Exception:   # noqa: BLE001 — senza copia il renderer resta in piedi
        return {}


def _t(sez: Dict, chiave: str) -> str:
    v = sez.get(chiave)
    return _html.escape(v) if isinstance(v, str) else ""


def _p(sez: Dict, *chiavi: str) -> str:
    """Un paragrafo dalle chiavi date (le vuote si saltano)."""
    frasi = [t for t in (_t(sez, k) for k in chiavi) if t]
    return f"<p>{' '.join(frasi)}</p>" if frasi else ""


def _h2(sez: Dict, chiave: str) -> str:
    t = _t(sez, chiave)
    return f"<h2>{t}</h2>" if t else ""


def _ul(sez: Dict, *chiavi: str) -> str:
    voci = [t for t in (_t(sez, k) for k in chiavi) if t]
    return "<ul>" + "".join(f"<li>{v}</li>" for v in voci) + "</ul>" if voci else ""


def _coppie(sez: Dict, base: str, n: int, tit: str = "Title", body: str = "Body") -> str:
    out = []
    for i in range(1, n + 1):
        t, b = _t(sez, f"{base}{i}{tit}"), _t(sez, f"{base}{i}{body}")
        if t or b:
            out.append(f"<li><b>{t}</b> {b}</li>")
    return "<ul>" + "".join(out) + "</ul>" if out else ""


def corpo_chi_siamo() -> str:
    s = _copia("landings").get("aboutPage") or {}
    if not s:
        return ""
    return "".join([
        f"<h1>{_t(s, 'heroTitle')}</h1>",
        _p(s, "heroQuestion"), _p(s, "heroP1", "heroP2"),
        _p(s, "bridge1", "bridge2", "bridge3"),
        _h2(s, "pathsTitle"), _p(s, "pathsLead"),
        _p(s, "pathsValentina1", "pathsValentina2"), _p(s, "pathsDavide1", "pathsDavide2"),
        _p(s, "pathsClose1", "pathsClose2", "pathsClose3"),
        _h2(s, "longTitle"), _p(s, "longP1", "longP2", "longP3"),
        _ul(s, "step1", "step2", "step3", "step4"), _p(s, "stepsClose"),
        _h2(s, "howTitle"), _p(s, "howLead"), _coppie(s, "p", 4),
        _h2(s, "togetherTitle"), _p(s, "togetherLead"),
        _ul(s, "who1", "who2", "who3", "who4"), _p(s, "togetherClose"),
    ])


def corpo_manifesto() -> str:
    s = _copia("landings").get("manifesto") or {}
    if not s:
        return ""
    return "".join([
        f"<h1>{_t(s, 'heroTitle')}</h1>",
        _ul(s, "q1", "q2", "q3"),
        _h2(s, "whyTitle"), _p(s, "whyP1", "whyP2"), _p(s, "whyPivot1", "whyPivot2"),
        _p(s, "whyClose1", "whyClose2"),
        _h2(s, "believeTitle"), _p(s, "believeLead1", "believeLead2"),
        _p(s, "believeP1", "believeP2"), _p(s, "bandLine1", "bandLine2"),
        _h2(s, "howTitle"), _p(s, "howP1", "howP2", "howP3", "howP4"),
        _p(s, "howClose1", "howClose2"),
        _h2(s, "principlesTitle"), _p(s, "principlesIntro"), _coppie(s, "p", 5),
        _h2(s, "buildingTitle"), _p(s, "buildingLead"),
        _ul(s, "buildingStep1", "buildingStep2", "buildingStep3"),
        _p(s, "buildingClose1", "buildingClose2"),
        _h2(s, "followTitle"), _p(s, "followP1", "followP2", "followP3"),
        _p(s, "signature"),
    ])


def faq_professionisti() -> List[Tuple[str, str]]:
    """Le domande frequenti della landing, come coppie (domanda, risposta)."""
    s = _copia("prelaunch").get("opPro") or {}
    coppie = []
    q1 = s.get("faq1q")
    a1 = " ".join(x for x in (s.get("faq1b1"), s.get("faq1b2"), s.get("faq1b3")) if x)
    if q1 and a1:
        coppie.append((q1, a1))
    for i in (2, 3, 4, 5):
        q, a = s.get(f"faq{i}q"), s.get(f"faq{i}a")
        if q and a:
            coppie.append((q, a))
    return coppie


def corpo_professionisti() -> str:
    s = _copia("prelaunch").get("opPro") or {}
    if not s:
        return ""
    faq = "".join(f"<h3>{_html.escape(q)}</h3><p>{_html.escape(a)}</p>"
                  for q, a in faq_professionisti())
    return "".join([
        f"<p><i>{_t(s, 'heroEyebrow')}</i></p>",
        f"<h1>{_t(s, 'heroTitle')}</h1>",
        _p(s, "heroP1"), _p(s, "heroBeat1", "heroBeat2", "heroBeat3", "heroBeat4"),
        _p(s, "heroP2", "heroP3", "heroP4", "heroP5"),
        _h2(s, "nowTitle"), _p(s, "nowP1", "nowP2", "nowP3"), _p(s, "nowCloseA", "nowCloseB"),
        _h2(s, "joinTitle"), _coppie(s, "j", 3, "t", "b"),
        _h2(s, "goTitle"), _p(s, "goP1", "goP2", "goP3", "goP4"), _coppie(s, "v", 5, "t", "b"),
        _p(s, "goSoon"),
        _h2(s, "forTitle"), _p(s, "forP1", "forP2"), _p(s, "forNo"), _p(s, "forYes"),
        _h2(s, "faqTitle"), faq,
        _h2(s, "whoEyebrow"), _p(s, "whoLead"), _p(s, "whoV", "whoD", "whoP"),
        _h2(s, "formTitle"), _p(s, "formA", "formB", "formC"),
        _p(s, "formD", "formE", "formF", "formG"),
        _p(s, "endA", "endB", "endC", "endD"), _p(s, "endBody"),
    ])


def corpo_cerchio() -> str:
    s = _copia("prelaunch").get("nl") or {}
    if not s:
        return ""
    return "".join([
        f"<h1>{_t(s, 'title')}</h1>", _p(s, "lead"), _p(s, "trust"),
        _h2(s, "findTitle"), _coppie(s, "r", 3, "t", "b"),
        _h2(s, "whoTitle"), _coppie(s, "a", 2, "t", "b"),
        _h2(s, "endTitle"), _p(s, "end1"),
    ])


def corpo_meditazioni() -> str:
    """La pagina delle meditazioni non e' tradotta: la sua copia sta
    in MeditazioniPage.js (la guardia LX ne verifica le frasi)."""
    return (
        "<h1>Le meditazioni di Aurya</h1>"
        "<p><i>sessioni vibrazionali composte dagli operatori della rete</i></p>"
        "<p>Qui vivranno le sessioni composte dagli operatori di Aurya, per dormire, "
        "meditare, rilassarsi, concentrarsi. L'ascolto completo è per chi è nel "
        "Cerchio di Aurya: entrare è gratis, e ti apre anche i ritiri in anteprima "
        "e la Lettera.</p>"
        "<p>Vuoi prima un assaggio? Su Aurya Sound ascolti novanta secondi di una "
        "meditazione riservata, senza iscriverti.</p>"
        "<h2>Come funziona</h2>"
        "<ul><li>Le meditazioni sono composte con Crea Studio: voce registrata, basi "
        "sonore e frequenze.</li>"
        "<li>Chi è nel Cerchio le ascolta per intero, anche a schermo bloccato.</li>"
        "<li>Chi non è ancora iscritto ascolta l'assaggio su Aurya Sound.</li></ul>"
        '<p><a href="/sound">Aurya Sound</a> · <a href="/newsletter">Il Cerchio di Aurya</a> · '
        '<a href="/sound/studio">Crea Studio</a></p>')


CORPI = {
    "chi-siamo": corpo_chi_siamo,
    "manifesto": corpo_manifesto,
    "entra-nella-rete": corpo_professionisti,
    "newsletter": corpo_cerchio,
    "meditazioni": corpo_meditazioni,
}


def testo(html: str) -> str:
    """Testo piano da un frammento HTML (per llms-full)."""
    b = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
    b = re.sub(r"</(p|h1|h2|h3|li|ul|ol|div)>", "\n", b, flags=re.I)
    b = re.sub(r"<[^>]+>", " ", b)
    b = _html.unescape(b)
    return re.sub(r"[ \t]+", " ", re.sub(r"\n\s*\n+", "\n\n", b)).strip()


# ── JSON-LD ─────────────────────────────────────────────────────────────────

def organization_jsonld(base: str) -> Dict:
    return {
        "@context": "https://schema.org",
        "@type": "Organization",
        "@id": f"{base}/#organization",
        "name": IDENTITA["name"],
        "url": f"{base}/",
        "logo": {"@type": "ImageObject", "url": f"{base}/logo-aurya-512.png"},
        "slogan": IDENTITA["tagline"],
        "description": IDENTITA["description"],
        "email": IDENTITA["email"],
        "foundingDate": IDENTITA["foundingDate"],
        "areaServed": IDENTITA["areaServed"],
        "knowsAbout": IDENTITA["knowsAbout"],
        "sameAs": IDENTITA["sameAs"],
        "founder": [{"@type": "Person", "name": n} for n in IDENTITA["founders"]],
    }


def website_jsonld(base: str) -> Dict:
    return {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": IDENTITA["name"],
        "url": f"{base}/",
        "inLanguage": IDENTITA["inLanguage"],
        "publisher": {"@id": f"{base}/#organization"},
        "potentialAction": {
            "@type": "SearchAction",
            "target": {"@type": "EntryPoint",
                       "urlTemplate": f"{base}/operatori?q={{search_term_string}}"},
            "query-input": "required name=search_term_string",
        },
    }


def faq_jsonld(coppie: List[Tuple[str, str]]) -> Optional[Dict]:
    if not coppie:
        return None
    return {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": q,
             "acceptedAnswer": {"@type": "Answer", "text": a}}
            for q, a in coppie],
    }


def pagina_jsonld(tipo: str, base: str, url: str, nome: str, descrizione: str) -> Dict:
    return {
        "@context": "https://schema.org",
        "@type": tipo,
        "name": nome,
        "url": url,
        "description": descrizione,
        "inLanguage": IDENTITA["inLanguage"],
        "isPartOf": {"@id": f"{base}/#website"} if False else {"@type": "WebSite", "url": f"{base}/"},
        "publisher": {"@id": f"{base}/#organization"},
    }


# ── llms.txt: le sezioni dei pilastri ────────────────────────────────────────

def intestazione_llms(base: str) -> List[str]:
    d = IDENTITA["description"]
    righe = ["# Aurya", ""]
    righe += [f"> {r}" for r in _spezza(d, 68)]
    righe += [f"> Il payoff del brand: \"{IDENTITA['tagline']}\"", ""]
    righe += ["## Cos'è Aurya, in dieci righe", ""]
    righe += [f"- [{nome}]({base}{slug}): {riga}" for slug, nome, riga in PILASTRI]
    return righe


def sezione_sound_llms(base: str, schede: Dict, stanze: Dict) -> List[str]:
    righe = ["", "## Aurya Sound", "",
             "Una biblioteca educativa sul suono: ogni scheda dichiara il suo livello di "
             "evidenza (documentato, ricerca in corso, tradizione). Nessuna promessa "
             "terapeutica.", "",
             "### Le esperienze d'ascolto, gratuite", "",
             f"- [CALM]({base}/sound/calm): sei minuti per creare uno spazio di calma.",
             f"- [GROUND]({base}/sound/ground): otto minuti per ritrovare il peso.",
             f"- [RESPIRO]({base}/sound/respiro): dieci minuti a sei respiri al minuto.",
             "", "### La biblioteca delle frequenze", ""]
    for slug, s in sorted(schede.items(), key=lambda kv: kv[1].get("t") or kv[0]):
        uso = (s.get("uso") or "").strip()
        righe.append(f"- [{s.get('t') or slug}]({base}/sound/esplora/{slug})"
                     + (f": {uso}" if uso else ""))
    righe += ["", "### Le fondamenta e il glossario", "",
              f"- [Le fondamenta]({base}/sound/impara): onde cerebrali, entrainment, "
              "binaurale, monaurale e isocronico, cuffie o altoparlanti, come si "
              "costruisce una sessione, quanto è accurato ciò che ascolti.",
              f"- [Il glossario del suono]({base}/sound/impara/glossario): le parole "
              "del suono spiegate in una riga.",
              "", "### Il Laboratorio del suono", "",
              f"- [La Sala del Lab]({base}/sound/lab): un banco vero nel browser."]
    for k, c in stanze.items():
        righe.append(f"- [{k.capitalize()}]({base}/sound/lab/{k}): {c.get('domanda', '')}")
    righe += ["", "### Comporre", "",
              f"- [Crea Studio]({base}/sound/studio): l'atelier con cui nascono le "
              "meditazioni di Aurya, aperto ai professionisti del benessere.",
              f"- [Aurya Sound Professional]({base}/sound/professional): protocolli "
              "d'ascolto strutturati per professionisti, su invito."]
    return righe


def sezione_meditazioni_llms(base: str) -> List[str]:
    return ["", "## Le meditazioni e il Cerchio di Aurya", "",
            f"- [Le meditazioni]({base}/meditazioni): sessioni sonore composte dai "
            "professionisti della rete; ascolto completo per chi è nel Cerchio, gratis; "
            "un assaggio di novanta secondi su Aurya Sound senza iscriversi.",
            f"- [Il Cerchio di Aurya]({base}/newsletter): meditazioni riservate, ritiri "
            "ed esperienze in anteprima e una lettera quando vale la pena. Una conferma "
            "via email, ci si cancella con un clic."]


def sezione_rete_llms(base: str, profili: List[Dict]) -> List[str]:
    righe = ["", "## La rete dei professionisti", "",
             "Professionisti del benessere raccontati uno a uno. Dal profilo si "
             "prenotano sessioni, eventi e ritiri quando il professionista li pubblica; "
             "le recensioni verificate arrivano solo da chi ha prenotato.", "",
             f"- [Tutti i professionisti]({base}/operatori)",
             f"- [Entrare nella rete]({base}/entra-nella-rete): gratuito, con profilo "
             "raccontato con cura e gestionale.", ""]
    for o in profili:
        pp = o.get("public_profile") or {}
        dove = ", ".join(x for x in (pp.get("city"), pp.get("region")) if x)
        disc = ", ".join(pp.get("disciplines_labels") or [])
        coda = " — ".join(x for x in (dove, disc) if x)
        righe.append(f"- [{o.get('name') or o['public_slug']}]({base}/o/{o['public_slug']})"
                     + (f": {coda}" if coda else ""))
    return righe


def sezione_ritiri_llms(base: str) -> List[str]:
    return ["", "## Ritiri ed esperienze", "",
            "I ritiri, i workshop e le esperienze sono proposti dai professionisti "
            "della rete e si prenotano dal loro profilo. Oggi Aurya li racconta (guide "
            "nel Magazine, categoria «Mondo ritiri») e li mette in anteprima a chi è "
            "nel Cerchio; la directory dei ritiri si accende man mano che i "
            f"professionisti li pubblicano: [{base}/operatori]({base}/operatori)."]


def _spezza(testo_: str, larghezza: int) -> List[str]:
    parole, righe, riga = testo_.split(), [], ""
    for p in parole:
        if len(riga) + len(p) + 1 > larghezza and riga:
            righe.append(riga)
            riga = p
        else:
            riga = f"{riga} {p}".strip()
    if riga:
        righe.append(riga)
    return righe
