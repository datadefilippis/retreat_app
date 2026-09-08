"""LA STRUTTURA RICETTIVA — il modello (ciclo SR, fase 0, 8/9/2026).

Un solo modello, due porte: in fase 0 la scheda la scrive il system
admin dal pannello (services + repository + routers/admin_strutture);
in fase 1 la struttura si registra e apre la SECONDA porta sullo
stesso modello (routers/struttura, `require_struttura`). I campi
della fase 1 esistono da oggi, vuoti: `organization_id`, `origine`,
`slug`, `visibilita`. Nessuna migrazione dopo.

Regola: tutto cio' che si deve CERCARE e' una lista chiusa (tuple qui
sotto, servite al frontend da /admin/strutture/schema), mai testo
libero. Il testo libero e' per le persone (descrizione, note).
Isolamento: questo file non importa niente dai professionisti e
nessun file dei professionisti importa da qui (guardia SR).
"""
import re
import unicodedata
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

# ── le liste chiuse (valore, etichetta) ─────────────────────────────────────

TIPI_STRUTTURA: Tuple[Tuple[str, str], ...] = (
    ("masseria", "Masseria"), ("agriturismo", "Agriturismo"), ("casale", "Casale"),
    ("eremo", "Eremo o monastero"), ("centro_ritiri", "Centro ritiri"),
    ("bed_and_breakfast", "Bed & breakfast"), ("villa", "Villa"), ("hotel", "Hotel"),
    ("rifugio", "Rifugio"), ("glamping", "Glamping"), ("altro", "Altro"),
)
CONTESTI = (("mare", "Mare"), ("collina", "Collina"), ("montagna", "Montagna"),
            ("campagna", "Campagna"), ("lago", "Lago"), ("bosco", "Bosco"), ("citta", "Città"))
TIPOLOGIE_CAMERA = (("singola", "Singola"), ("doppia", "Doppia"), ("matrimoniale", "Matrimoniale"),
                    ("tripla", "Tripla"), ("quadrupla", "Quadrupla"), ("camerata", "Camerata"),
                    ("glamping", "Tenda o glamping"), ("appartamento", "Appartamento"))
TIPI_LETTO = (("singoli", "Letti singoli"), ("matrimoniale", "Matrimoniale"),
              ("castello", "A castello"), ("misti", "Misti"))
BAGNO = (("privato", "Privato"), ("condiviso", "Condiviso"))
PAVIMENTI = (("legno", "Legno"), ("cotto", "Cotto"), ("pietra", "Pietra"),
             ("moquette", "Moquette"), ("resina", "Resina"), ("altro", "Altro"))
ATTREZZATURE_SALA = (("tappetini", "Tappetini"), ("cuscini", "Cuscini da meditazione"),
                     ("coperte", "Coperte"), ("blocchi", "Blocchi e cinghie"),
                     ("audio", "Impianto audio"), ("proiettore", "Proiettore o schermo"),
                     ("sedie", "Sedie"), ("camino", "Camino o stufa"))
TIPI_SPAZIO_ESTERNO = (("prato", "Prato"), ("terrazza", "Terrazza"), ("giardino", "Giardino"),
                       ("uliveto", "Uliveto"), ("bosco", "Bosco"), ("spiaggia", "Spiaggia"),
                       ("piazzale", "Piazzale"), ("orto", "Orto"), ("altro", "Altro"))
ARIA_CONDIZIONATA = (("nessuna", "Nessuna"), ("camere", "Solo nelle camere"),
                     ("sale", "Solo nelle sale"), ("tutto", "Camere e sale"))
WIFI = (("assente", "Assente"), ("debole", "Debole"), ("buono", "Buono"))
PISCINA = (("nessuna", "Nessuna"), ("esterna", "Esterna"), ("interna", "Interna"),
           ("riscaldata", "Riscaldata"))
CUCINA = (("struttura", "Cucina della struttura"), ("cuoco_esterno", "Cuoco esterno ammesso"),
          ("self_service", "Cucina a disposizione del gruppo"), ("nessuna", "Nessuna"))
REGIMI = (("vegetariano", "Vegetariano"), ("vegano", "Vegano"), ("senza_glutine", "Senza glutine"),
          ("senza_lattosio", "Senza lattosio"), ("ayurvedico", "Ayurvedico"),
          ("crudista", "Crudista"), ("macrobiotico", "Macrobiotico"))
PASTI = (("nessuno", "Nessuno"), ("colazione", "Colazione"), ("mezza_pensione", "Mezza pensione"),
         ("pensione_completa", "Pensione completa"), ("su_richiesta", "Su richiesta"))
BASI_TARIFFA = (("persona_notte", "A persona a notte"), ("camera_notte", "A camera a notte"),
                ("struttura_notte", "Intera struttura a notte"),
                ("persona_soggiorno", "A persona a soggiorno"))
TRATTAMENTI = (("solo_pernotto", "Solo pernotto"), ("colazione", "Con colazione"),
               ("mezza_pensione", "Mezza pensione"), ("pensione_completa", "Pensione completa"))
ADATTA_A = (("yoga", "Yoga"), ("meditazione", "Meditazione"), ("breathwork", "Breathwork"),
            ("digiuno_detox", "Digiuno e detox"), ("cerchi", "Cerchi"),
            ("sound_healing", "Sound healing"), ("cammini", "Cammini"), ("aziende", "Aziende"),
            ("famiglie", "Famiglie"), ("silenzio", "Silenzio"), ("ayurveda", "Ayurveda"),
            ("danza", "Danza e movimento"), ("arti", "Arti e scrittura"))
ESPERIENZA_RITIRI = (("mai", "Mai ospitato ritiri"), ("qualche", "Qualche ritiro"),
                     ("abituale", "Ospita ritiri abitualmente"))
STAGIONALITA = (("tutto_anno", "Aperta tutto l'anno"), ("stagionale", "Stagionale"))
MESI = (("1", "Gennaio"), ("2", "Febbraio"), ("3", "Marzo"), ("4", "Aprile"), ("5", "Maggio"),
        ("6", "Giugno"), ("7", "Luglio"), ("8", "Agosto"), ("9", "Settembre"),
        ("10", "Ottobre"), ("11", "Novembre"), ("12", "Dicembre"))
PREFERENZA_CONTATTO = (("telefono", "Telefono"), ("email", "Email"), ("whatsapp", "WhatsApp"))
STATI_PIPELINE = (("da_contattare", "Da contattare"), ("contattata", "Contattata"),
                  ("visitata", "Visitata"), ("in_lista", "In lista"), ("sospesa", "Sospesa"))
VISIBILITA = (("riservata", "Riservata"), ("pubblica", "Pubblica"))
ORIGINI = (("redazione", "Scritta da Aurya"), ("struttura", "Scritta dalla struttura"))

REGIONI = (
    "Abruzzo", "Basilicata", "Calabria", "Campania", "Emilia-Romagna",
    "Friuli-Venezia Giulia", "Lazio", "Liguria", "Lombardia", "Marche", "Molise",
    "Piemonte", "Puglia", "Sardegna", "Sicilia", "Toscana", "Trentino-Alto Adige",
    "Umbria", "Valle d'Aosta", "Veneto",
)


def _valori(lista) -> List[str]:
    return [v for v, _ in lista]


SCHEMA_LISTE: Dict[str, Tuple[Tuple[str, str], ...]] = {
    "tipi_struttura": TIPI_STRUTTURA, "contesti": CONTESTI, "tipologie_camera": TIPOLOGIE_CAMERA,
    "tipi_letto": TIPI_LETTO, "bagno": BAGNO, "pavimenti": PAVIMENTI,
    "attrezzature_sala": ATTREZZATURE_SALA, "tipi_spazio_esterno": TIPI_SPAZIO_ESTERNO,
    "aria_condizionata": ARIA_CONDIZIONATA, "wifi": WIFI, "piscina": PISCINA, "cucina": CUCINA,
    "regimi": REGIMI, "pasti": PASTI, "basi_tariffa": BASI_TARIFFA, "trattamenti": TRATTAMENTI,
    "adatta_a": ADATTA_A, "esperienza_ritiri": ESPERIENZA_RITIRI, "stagionalita": STAGIONALITA,
    "mesi": MESI, "preferenza_contatto": PREFERENZA_CONTATTO, "stati_pipeline": STATI_PIPELINE,
    "visibilita": VISIBILITA, "origini": ORIGINI,
}


def schema_per_frontend() -> Dict:
    """Le liste chiuse con le etichette italiane: UNA fonte per form e filtri."""
    return {"liste": {k: [{"valore": v, "etichetta": e} for v, e in lista]
                      for k, lista in SCHEMA_LISTE.items()},
            "regioni": list(REGIONI),
            "sezioni": list(SEZIONI)}


# ── le sezioni della scheda ─────────────────────────────────────────────────

class Foto(BaseModel):
    url: str
    alt: Optional[str] = Field(default=None, max_length=160)


class Identita(BaseModel):
    nome: Optional[str] = Field(default=None, min_length=2, max_length=120)
    tipo: Optional[str] = None
    descrizione: Optional[str] = Field(default=None, max_length=4000)
    sito: Optional[str] = Field(default=None, max_length=300)


class Luogo(BaseModel):
    indirizzo: Optional[str] = Field(default=None, max_length=200)
    comune: Optional[str] = Field(default=None, max_length=80)
    provincia: Optional[str] = Field(default=None, max_length=4)
    regione: Optional[str] = None
    cap: Optional[str] = Field(default=None, max_length=10)
    latitudine: Optional[float] = Field(default=None, ge=-90, le=90)
    longitudine: Optional[float] = Field(default=None, ge=-180, le=180)
    come_si_arriva: Optional[str] = Field(default=None, max_length=1500)
    stazione_km: Optional[float] = Field(default=None, ge=0, le=1000)
    aeroporto_km: Optional[float] = Field(default=None, ge=0, le=1000)
    contesto: List[str] = Field(default_factory=list)
    silenzio: Optional[int] = Field(default=None, ge=1, le=5)
    raggiungibile_senza_auto: Optional[bool] = None


class Camera(BaseModel):
    tipologia: str
    quantita: int = Field(ge=1, le=200)
    letti: int = Field(ge=1, le=40)
    tipo_letti: Optional[str] = None
    bagno: Optional[str] = None
    note: Optional[str] = Field(default=None, max_length=300)


class Ricettivita(BaseModel):
    camere: List[Camera] = Field(default_factory=list)
    posti_letto_dichiarati: Optional[int] = Field(default=None, ge=0, le=2000)
    bagni_totali: Optional[int] = Field(default=None, ge=0, le=500)
    accetta_letti_condivisi: Optional[bool] = None
    uso_esclusivo_possibile: Optional[bool] = None
    persone_min: Optional[int] = Field(default=None, ge=1, le=2000)
    persone_max: Optional[int] = Field(default=None, ge=1, le=2000)


class Sala(BaseModel):
    nome: Optional[str] = Field(default=None, max_length=80)
    mq: Optional[float] = Field(default=None, ge=1, le=5000)
    altezza_m: Optional[float] = Field(default=None, ge=1, le=30)
    pavimento: Optional[str] = None
    capienza_persone: Optional[int] = Field(default=None, ge=1, le=2000)
    riscaldata: Optional[bool] = None
    climatizzata: Optional[bool] = None
    luce_naturale: Optional[bool] = None
    attrezzata: List[str] = Field(default_factory=list)
    note: Optional[str] = Field(default=None, max_length=300)


class SpazioEsterno(BaseModel):
    tipo: str
    mq: Optional[float] = Field(default=None, ge=1, le=100000)
    ombra: Optional[bool] = None
    adatto_pratica: Optional[bool] = None
    note: Optional[str] = Field(default=None, max_length=300)


class Spazi(BaseModel):
    sale: List[Sala] = Field(default_factory=list)
    spazi_esterni: List[SpazioEsterno] = Field(default_factory=list)


class Comfort(BaseModel):
    aria_condizionata: Optional[str] = None
    riscaldamento: Optional[bool] = None
    wifi: Optional[str] = None
    piscina: Optional[str] = None
    sauna: Optional[bool] = None
    vasca_idromassaggio: Optional[bool] = None
    parcheggio_posti: Optional[int] = Field(default=None, ge=0, le=1000)
    accessibile_disabili: Optional[bool] = None
    animali: Optional[bool] = None
    lavanderia: Optional[bool] = None
    altri_servizi: List[str] = Field(default_factory=list)


class Cucina(BaseModel):
    cucina: Optional[str] = None
    regimi: List[str] = Field(default_factory=list)
    pasti_inclusi: Optional[str] = None
    prodotti_propri: Optional[bool] = None
    note: Optional[str] = Field(default=None, max_length=1000)


class Tariffa(BaseModel):
    base: str
    tipologia_camera: Optional[str] = None          # None = tutte
    trattamento: Optional[str] = None
    prezzo: Optional[float] = Field(default=None, ge=0, le=100000)   # None = da compilare


class Stagione(BaseModel):
    nome: str = Field(min_length=1, max_length=40)
    dal: Optional[str] = Field(default=None, pattern=r"^\d{2}-\d{2}$")   # MM-GG, ricorrente
    al: Optional[str] = Field(default=None, pattern=r"^\d{2}-\d{2}$")
    tariffe: List[Tariffa] = Field(default_factory=list)


class Prezzi(BaseModel):
    valuta: str = "EUR"
    stagioni: List[Stagione] = Field(default_factory=list)
    affitto_esclusivo_notte: Optional[float] = Field(default=None, ge=0, le=1000000)
    minimo_notti: Optional[int] = Field(default=None, ge=1, le=365)
    minimo_persone: Optional[int] = Field(default=None, ge=1, le=2000)
    acconto_percento: Optional[int] = Field(default=None, ge=0, le=100)
    cancellazione: Optional[str] = Field(default=None, max_length=1500)
    tassa_soggiorno: Optional[bool] = None
    tassa_soggiorno_importo: Optional[float] = Field(default=None, ge=0, le=100)
    note: Optional[str] = Field(default=None, max_length=1500)


class AdattaA(BaseModel):
    adatta_a: List[str] = Field(default_factory=list)
    esperienza_ritiri: Optional[str] = None
    ritiri_ospitati_note: Optional[str] = Field(default=None, max_length=1500)


class Disponibilita(BaseModel):
    stagionalita: Optional[str] = None
    chiusura_mesi: List[str] = Field(default_factory=list)
    note: Optional[str] = Field(default=None, max_length=1000)


class Contatti(BaseModel):
    referente: Optional[str] = Field(default=None, max_length=120)
    ruolo: Optional[str] = Field(default=None, max_length=80)
    telefono: Optional[str] = Field(default=None, max_length=40)
    email: Optional[str] = Field(default=None, max_length=160)
    preferisce: Optional[str] = None


class VoceStoria(BaseModel):
    quando: Optional[str] = None
    chi: Optional[str] = Field(default=None, max_length=80)
    nota: str = Field(min_length=1, max_length=2000)


class Redazione(BaseModel):
    stato_pipeline: Optional[str] = None
    visitata_da: Optional[str] = Field(default=None, max_length=80)
    visitata_il: Optional[str] = Field(default=None, max_length=10)
    giudizio: Optional[int] = Field(default=None, ge=1, le=5)
    punti_forti: Optional[str] = Field(default=None, max_length=2000)
    punti_deboli: Optional[str] = Field(default=None, max_length=2000)
    prossimo_passo: Optional[str] = Field(default=None, max_length=500)


SEZIONI = ("identita", "luogo", "ricettivita", "spazi", "comfort", "cucina",
           "prezzi", "adatta", "disponibilita", "contatti", "redazione")

MODELLI_SEZIONE = {
    "identita": Identita, "luogo": Luogo, "ricettivita": Ricettivita, "spazi": Spazi,
    "comfort": Comfort, "cucina": Cucina, "prezzi": Prezzi, "adatta": AdattaA,
    "disponibilita": Disponibilita, "contatti": Contatti, "redazione": Redazione,
}


class StrutturaCrea(BaseModel):
    nome: str = Field(min_length=2, max_length=120)
    regione: str
    tipo: Optional[str] = None


class StrutturaPatch(BaseModel):
    """Il PATCH porta una o piu' sezioni: si salva una sezione alla volta."""
    identita: Optional[Identita] = None
    luogo: Optional[Luogo] = None
    ricettivita: Optional[Ricettivita] = None
    spazi: Optional[Spazi] = None
    comfort: Optional[Comfort] = None
    cucina: Optional[Cucina] = None
    prezzi: Optional[Prezzi] = None
    adatta: Optional[AdattaA] = None
    disponibilita: Optional[Disponibilita] = None
    contatti: Optional[Contatti] = None
    redazione: Optional[Redazione] = None
    visibilita: Optional[str] = None
    foto: Optional[List[Foto]] = None
    foto_copertina: Optional[str] = None


# ── validazione delle liste chiuse ──────────────────────────────────────────

_LISTE_PER_CAMPO = {
    ("identita", "tipo"): TIPI_STRUTTURA, ("luogo", "regione"): None,
    ("comfort", "aria_condizionata"): ARIA_CONDIZIONATA, ("comfort", "wifi"): WIFI,
    ("comfort", "piscina"): PISCINA, ("cucina", "cucina"): CUCINA,
    ("cucina", "pasti_inclusi"): PASTI, ("adatta", "esperienza_ritiri"): ESPERIENZA_RITIRI,
    ("disponibilita", "stagionalita"): STAGIONALITA,
    ("contatti", "preferisce"): PREFERENZA_CONTATTO,
    ("redazione", "stato_pipeline"): STATI_PIPELINE,
}
_MULTI_PER_CAMPO = {
    ("luogo", "contesto"): CONTESTI, ("cucina", "regimi"): REGIMI,
    ("adatta", "adatta_a"): ADATTA_A, ("disponibilita", "chiusura_mesi"): MESI,
}


def errori_liste(sezione: str, dati: dict) -> List[str]:
    """Ritorna le violazioni delle liste chiuse (valori non ammessi)."""
    errori = []
    for (sez, campo), lista in _LISTE_PER_CAMPO.items():
        if sez != sezione or campo not in dati or dati[campo] is None:
            continue
        ammessi = REGIONI if lista is None else _valori(lista)
        if dati[campo] not in ammessi:
            errori.append(f"{sezione}.{campo}: «{dati[campo]}» non è un valore ammesso")
    for (sez, campo), lista in _MULTI_PER_CAMPO.items():
        if sez != sezione or not dati.get(campo):
            continue
        fuori = [v for v in dati[campo] if v not in _valori(lista)]
        if fuori:
            errori.append(f"{sezione}.{campo}: valori non ammessi {fuori}")
    if sezione == "ricettivita":
        for c in dati.get("camere") or []:
            if c.get("tipologia") not in _valori(TIPOLOGIE_CAMERA):
                errori.append(f"camere: tipologia «{c.get('tipologia')}» non ammessa")
            if c.get("tipo_letti") and c["tipo_letti"] not in _valori(TIPI_LETTO):
                errori.append(f"camere: tipo letti «{c['tipo_letti']}» non ammesso")
            if c.get("bagno") and c["bagno"] not in _valori(BAGNO):
                errori.append(f"camere: bagno «{c['bagno']}» non ammesso")
    if sezione == "spazi":
        for s in dati.get("sale") or []:
            if s.get("pavimento") and s["pavimento"] not in _valori(PAVIMENTI):
                errori.append(f"sale: pavimento «{s['pavimento']}» non ammesso")
            fuori = [a for a in (s.get("attrezzata") or []) if a not in _valori(ATTREZZATURE_SALA)]
            if fuori:
                errori.append(f"sale: attrezzature non ammesse {fuori}")
        for e in dati.get("spazi_esterni") or []:
            if e.get("tipo") not in _valori(TIPI_SPAZIO_ESTERNO):
                errori.append(f"spazi esterni: tipo «{e.get('tipo')}» non ammesso")
    if sezione == "prezzi":
        for st in dati.get("stagioni") or []:
            for t in st.get("tariffe") or []:
                if t.get("base") not in _valori(BASI_TARIFFA):
                    errori.append(f"tariffe: base «{t.get('base')}» non ammessa")
                if t.get("trattamento") and t["trattamento"] not in _valori(TRATTAMENTI):
                    errori.append(f"tariffe: trattamento «{t['trattamento']}» non ammesso")
                if t.get("tipologia_camera") and t["tipologia_camera"] not in _valori(TIPOLOGIE_CAMERA):
                    errori.append(f"tariffe: tipologia camera «{t['tipologia_camera']}» non ammessa")
    return errori


# ── i derivati: cio' che si filtra si calcola al salvataggio ────────────────

def calcola_derivati(doc: dict) -> dict:
    """I campi di ricerca, sempre coerenti con le sezioni: posti letto,
    prezzo da, ha una sala, sala piu' grande, piscina, aria, regione."""
    ric = doc.get("ricettivita") or {}
    camere = ric.get("camere") or []
    calcolati = sum(int(c.get("quantita") or 0) * int(c.get("letti") or 0) for c in camere)
    posti = ric.get("posti_letto_dichiarati") or calcolati or None
    spazi = doc.get("spazi") or {}
    sale = spazi.get("sale") or []
    prezzi = doc.get("prezzi") or {}
    persona_notte = [t["prezzo"] for st in (prezzi.get("stagioni") or [])
                     for t in (st.get("tariffe") or [])
                     if t.get("base") == "persona_notte" and (t.get("prezzo") or 0) > 0]   # 0 = non compilato
    comfort = doc.get("comfort") or {}
    return {
        "posti_letto_totali": posti,
        "prezzo_da": min(persona_notte) if persona_notte else None,
        "ha_sala": bool(sale),
        "sala_mq_max": max((s.get("mq") or 0) for s in sale) if sale else None,
        "ha_piscina": (comfort.get("piscina") or "nessuna") != "nessuna",
        "ha_aria": (comfort.get("aria_condizionata") or "nessuna") != "nessuna",
        "ha_spazi_esterni": bool(spazi.get("spazi_esterni")),
        "regione": (doc.get("luogo") or {}).get("regione"),
        "tipo": (doc.get("identita") or {}).get("tipo"),
        "adatta_a": (doc.get("adatta") or {}).get("adatta_a") or [],
        "stato_pipeline": (doc.get("redazione") or {}).get("stato_pipeline") or "da_contattare",
    }


def slugify(nome: str) -> str:
    base = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode()
    base = re.sub(r"[^a-z0-9]+", "-", base.lower()).strip("-")
    return base[:80] or "struttura"


def adesso() -> str:
    return datetime.now(timezone.utc).isoformat()
