"""PE4 — primo articolo del pilastro "Le discipline": i tipi di yoga.

PERCHE' QUESTO PER PRIMO (piano editoriale, Parte 3, famiglia B).
E' la domanda che si fa chiunque si avvicini allo yoga, e in italiano
la risposta e' sparsa su decine di pagine che elencano nomi senza
spiegare cosa cambia in una lezione vera. E' anche il nodo a cui si
agganciano i pezzi successivi della famiglia: kriya yoga, yoga nidra,
pranayama.

VOCE. Regole della Parte 1b applicate dalla prima riga: nessun
qualificatore che si auto-elogia, "davvero" bandito, le negazioni solo
dove correggono un malinteso che una persona ha davvero.

SALUTE. Dove si parla di corpo il testo rimanda a un medico invece di
rassicurare: e' il capitolo "Cosa non faremo mai" applicato.

Idempotente: rilanciarlo aggiorna il testo senza duplicare l'articolo
e senza toccare la data di pubblicazione.

    venv/bin/python scripts/pe4_articolo_tipi_di_yoga.py [--dry-run]
"""
import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone

SLUG = "differenze-tipi-di-yoga-hatha-vinyasa-ashtanga-yin-kundalini"
TITOLO = "Hatha, vinyasa, ashtanga, yin, kundalini: le differenze fra i tipi di yoga"
DESCRIZIONE = (
    "Cosa cambia fra hatha, vinyasa, ashtanga, yin e kundalini: ritmo, "
    "intensità, a chi si adattano e come scegliere la lezione giusta per te."
)
CATEGORIA = "yoga"

CONTENUTO = """\
Entri in una scuola di yoga e sul volantino ci sono sei nomi: hatha, vinyasa, ashtanga, yin, kundalini, forse iyengar. Nessuno spiega cosa cambia. Chiedi, e ti rispondono che «dipende da cosa cerchi» — che è vero e inutile insieme, perché per sapere cosa cerchi bisognerebbe già sapere cosa esiste.

Questa guida mette in fila le famiglie principali: cosa succede in una lezione, che ritmo ha, che cosa lascia addosso e a chi si adatta. Alla fine c'è la parte che conta più di tutte, e non riguarda lo stile.

## Una premessa che risolve metà della confusione

In Occidente «yoga» è diventato sinonimo di posizioni. Nella tradizione da cui viene, le posizioni sono un ramo su otto: ci sono anche il respiro, l'osservanza etica, il ritiro dei sensi, la concentrazione, la meditazione. Quando una scuola dice «facciamo yoga» quasi sempre intende **asana**, cioè il lavoro sul corpo, con dosi variabili di respiro e attenzione.

Questo spiega perché due lezioni chiamate allo stesso modo possono somigliarsi poco: gli stili non sono discipline separate come il nuoto e la corsa, sono modi diversi di dosare gli stessi ingredienti — posizione, respiro, ritmo, attenzione.

## Hatha: il contenitore, e la lezione lenta

**Hatha** è un termine con due vite. Nella tradizione indica l'intera famiglia dello yoga fisico: in quel senso vinyasa, ashtanga e iyengar sono tutti hatha yoga.

Nelle scuole di oggi, però, «lezione di hatha» ha finito per indicare una cosa più stretta: una pratica **lenta, con posizioni tenute per qualche respiro e pause fra l'una e l'altra**. Si costruisce una posizione, ci si sta dentro, si osserva, si esce.

- **Ritmo:** lento, con soste dichiarate.
- **Cosa allena:** consapevolezza della posizione, forza isometrica, respiro.
- **A chi si adatta:** a chi comincia, a chi vuole capire dove sono le proprie articolazioni prima di muoverle in fretta, a chi arriva stanco e cerca qualcosa che non lo prosciughi.

Se una scuola offre un'unica lezione «per tutti», di solito è questa.

## Vinyasa: il movimento legato al respiro

**Vinyasa** significa disporre in una sequenza. Nella pratica indica lo stile in cui **ogni movimento è legato a un'inspirazione o a un'espirazione**, e le posizioni si susseguono senza soste lunghe. Il nome che vedi più spesso è *vinyasa flow*.

Le sequenze cambiano da lezione a lezione: l'insegnante le compone, quindi due lezioni di vinyasa nella stessa scuola possono essere diverse.

- **Ritmo:** continuo, spesso sostenuto.
- **Cosa allena:** resistenza, coordinazione fra respiro e movimento, calore.
- **A chi si adatta:** a chi si annoia a stare fermo, a chi cerca anche un effetto cardiovascolare, a chi ha già un minimo di familiarità con le posizioni di base.

Chi comincia da qui a volte fatica: quando il ritmo corre, è difficile accorgersi di come si sta appoggiando la mano. Molte scuole risolvono con una lezione «slow flow», che è vinyasa a velocità ridotta.

## Ashtanga: la stessa sequenza, ogni volta

**Ashtanga vinyasa**, codificato da Sri K. Pattabhi Jois a Mysore, ha una caratteristica che lo distingue da tutto il resto: **la sequenza è fissa**. Esiste una prima serie, poi una seconda, poi altre; si pratica sempre lo stesso ordine, e si avanza quando le posizioni precedenti sono stabili.

Esiste anche il metodo **Mysore**: in sala ognuno pratica la propria serie al proprio ritmo, in silenzio, e l'insegnante gira fra le persone. Sembra una lezione senza insegnante, ed è il contrario: è la forma in cui l'insegnamento diventa individuale.

- **Ritmo:** sostenuto e regolare.
- **Cosa allena:** forza, disciplina, memoria del corpo.
- **A chi si adatta:** a chi ama la ripetizione e misura i progressi nel tempo; a chi vuole una pratica da fare anche da solo, perché la sequenza si impara.

È lo stile più esigente sul piano fisico fra quelli comuni. Se hai problemi a spalle, polsi o schiena, parlane con l'insegnante prima di iscriverti a un corso, e con un medico se il disturbo è in corso.

## Yin: pochi minuti in una posizione sola

**Yin yoga** lavora su un principio diverso dagli altri quattro. Le posizioni si fanno quasi tutte a terra e si tengono a lungo — **da tre a cinque minuti, a volte di più** — con i muscoli rilassati invece che attivi.

La ragione dichiarata è che i tessuti più profondi (fasce, legamenti, capsule articolari) rispondono a sollecitazioni lunghe e leggere, non a contrazioni brevi. La ricerca su questi meccanismi è ancora in corso e le spiegazioni che troverai variano; quello che si osserva in pratica è un aumento della mobilità e uno stato mentale che somiglia alla meditazione.

- **Ritmo:** immobile. La difficoltà non è fisica, è stare.
- **Cosa allena:** mobilità, tolleranza dell'immobilità, attenzione.
- **A chi si adatta:** a chi ha una vita veloce, a chi fa sport di forza e ha bisogno del complemento, a chi arriva alla sera con la testa piena.

Molte persone lo trovano il più difficile di tutti, ed è quasi sempre per motivi che con i muscoli non c'entrano.

## Kundalini: respiro, mantra, ripetizione

**Kundalini yoga** è l'unico dei cinque in cui le posizioni non sono il centro. Una lezione è fatta di **kriya**, cioè sequenze precise che combinano movimenti spesso ripetitivi, tecniche di respiro intense, mantra cantati e periodi di meditazione. Si sta seduti più che in piedi, e si canta.

È lo stile più lontano dall'idea comune di «lezione di yoga», e quello su cui le reazioni si dividono di più: chi lo ama lo trova il più potente, chi non lo ama esce a metà.

Due cose da sapere prima di entrare in una sala. La prima: alcune tecniche di respiro (il *respiro di fuoco* è la più nota) sono sconsigliate in gravidanza, in caso di ipertensione, epilessia o disturbi cardiaci — un insegnante preparato lo chiede all'inizio, e se non lo chiede puoi dirlo tu. La seconda: la diffusione occidentale di questo stile si deve in larga parte a Yogi Bhajan, la cui condotta personale è stata oggetto di un'inchiesta indipendente pubblicata nel 2020, con accuse di abusi. Molte scuole hanno preso posizione e continuano a insegnare le tecniche separandole dalla figura: è una cosa su cui puoi chiedere apertamente cosa ne pensa la scuola dove stai per iscriverti.

## Gli altri nomi che incontrerai

- **Iyengar** — nato dal lavoro di B.K.S. Iyengar: posizioni tenute a lungo, precisione millimetrica dell'allineamento e uso sistematico di supporti (mattoni, cinghie, coperte). È lo stile più usato quando c'è un problema fisico da aggirare.
- **Yoga nidra** — non è una lezione di posizioni: si sta sdraiati e si segue la voce dell'insegnante attraverso il corpo, in uno stato fra veglia e sonno. Serve a riposare, non ad allenarsi.
- **Kriya yoga** — attenzione all'omonimia: qui *kriya* non indica le sequenze del kundalini. Il kriya yoga diffuso da Paramahansa Yogananda è un percorso di **tecniche di meditazione e respiro** trasmesse per iniziazione, non un corso di asana in cui ci si iscrive.
- **Yoga in gravidanza, yoga per bambini, yoga sulla sedia** — non sono stili ma adattamenti, e possono partire da qualsiasi famiglia.

## Come scegliere, in tre domande

**Cosa vuoi che ti lasci addosso?** Se vuoi scaricare energia, vinyasa o ashtanga. Se vuoi rallentare, hatha o yin. Se vuoi qualcosa che tocchi anche il piano emotivo e non ti spaventa cantare, kundalini.

**Quanto tempo hai, e con che regolarità?** Ashtanga premia chi pratica spesso e a lungo: praticato una volta ogni tanto rende poco. Yin e hatha funzionano anche a frequenza bassa.

**Il tuo corpo ha qualcosa da dire?** Se hai ernie, protrusioni, problemi articolari, pressione alta o sei in gravidanza, la domanda non è quale stile ma **quale insegnante**: cerca chi ha una formazione specifica e parlane prima con il tuo medico. Nessuna guida, questa compresa, può sostituire quella conversazione.

## La cosa che conta più dello stile

Dopo aver messo in fila cinque famiglie, la parte più utile è anche la più semplice: **fra due lezioni dello stesso stile, la differenza la fa l'insegnante**, non il nome sul volantino.

Un buon insegnante ti chiede come stai prima di cominciare, propone alternative invece di correggere in silenzio, spiega perché una posizione serve, e ti lascia uscire da un movimento senza farti sentire in difetto. Quando lo trovi, lo stile diventa un dettaglio: quasi tutti funzionano, praticati bene.

Il consiglio pratico è quindi uno solo. Prova tre lezioni di famiglie diverse nella stessa settimana, con insegnanti diversi. Alla terza avrai capito più di quanto ti abbia detto questa pagina.

## Domande frequenti

**Qual è lo yoga più adatto per iniziare?**
Hatha, per il ritmo che lascia il tempo di capire cosa sta facendo il corpo. In alternativa uno *slow flow*, che è vinyasa rallentato.

**Qual è il più impegnativo fisicamente?**
Fra quelli comuni, ashtanga. Il vinyasa a ritmo alto gli si avvicina.

**Yin yoga e stretching sono la stessa cosa?**
No. Nello stretching si allunga un muscolo con una contrazione volontaria per pochi secondi; nello yin si rilascia e si aspetta per minuti, lavorando su tessuti diversi e con un obiettivo che è anche mentale.

**Posso praticare più stili insieme?**
Sì, ed è una delle combinazioni più equilibrate: una pratica dinamica durante la settimana e una lenta per compensare.

**Quante volte a settimana serve praticare?**
Due volte è la soglia sotto la quale i cambiamenti si notano poco. Tre è la frequenza in cui la maggior parte delle persone comincia a sentire una differenza stabile.

**Serve essere flessibili per cominciare?**
La flessibilità è un effetto della pratica, non un requisito. Il vero requisito è trovare un insegnante che sappia adattare le posizioni al corpo che hai adesso.
"""


async def main(dry_run: bool) -> None:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from database import db

    parole = len(CONTENUTO.split())
    print(f"{TITOLO}\n  slug: {SLUG}\n  categoria: {CATEGORIA}\n"
          f"  parole: {parole}\n  descrizione: {len(DESCRIZIONE)} caratteri")

    esistente = await db.articles.find_one({"slug": SLUG}, {"_id": 0, "id": 1})
    print("  stato:", "gia' presente, si aggiorna" if esistente else "nuovo")

    if dry_run:
        print("\n--dry-run: nessuna scrittura")
        return

    now = datetime.now(timezone.utc)
    campi = {
        "title": TITOLO,
        "description": DESCRIZIONE,
        "content": CONTENUTO,
        "category": CATEGORIA,
        "author_name": "Aurya",      # PE1: la firma e' sempre collettiva
        "published": True,
        "updated_at": now,
        "translations": {},          # solo italiano (founder, 2/8)
    }
    if not esistente:
        campi |= {"id": str(uuid.uuid4()), "slug": SLUG,
                  "created_at": now, "published_at": now}

    await db.articles.update_one({"slug": SLUG}, {"$set": campi}, upsert=True)

    # la copertina autogenerata: stesso helper del pannello admin
    doc = await db.articles.find_one({"slug": SLUG},
                                     {"_id": 0, "featured_image_url": 1})
    if not doc.get("featured_image_url"):
        from routers.articles import _autogen_cover
        url = await _autogen_cover(SLUG, CATEGORIA)
        if url:
            await db.articles.update_one({"slug": SLUG},
                                         {"$set": {"featured_image_url": url}})
            print(f"  copertina: {url}")

    print("\npubblicato")


if __name__ == "__main__":
    asyncio.run(main("--dry-run" in sys.argv))
