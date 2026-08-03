"""PC8 — secondo pezzo del cluster "scegliere": le domande da fare prima.

PERCHE' QUESTO. Il cluster aveva un solo articolo, ed e' quello piu'
vicino alla tesi della casa: la fiducia si costruisce chiedendo, non
sperando. "Come capire se un operatore e' serio" risponde a chi sta
valutando una persona; questo risponde a chi sta per pagare, che e' il
momento in cui la domanda diventa urgente e in cui quasi nessuno la
fa, per non sembrare diffidente.

LA MOSSA UTILE, e vale la pena dirla qui perche' e' il punto dell'
articolo: le domande non servono a incastrare nessuno. Un organizzatore
che lavora bene le aspetta, e la velocita' con cui risponde dice piu'
del contenuto della risposta.

LEGA I DUE MONDI. E' il primo pezzo per clienti che manda a un articolo
della sezione professionisti (il calcolo del prezzo): chi capisce come
si costruisce un preventivo smette di leggere il prezzo come un numero
arbitrario. Il link e' contestuale, non promozionale.

    venv/bin/python scripts/pc8_articolo_domande_prima_di_prenotare.py [--dry-run]
"""
import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone

SLUG = "domande-da-fare-prima-di-prenotare-un-ritiro"
TITOLO = "Le domande da fare prima di prenotare un ritiro"
DESCRIZIONE = (
    "Ventidue domande su soldi, gruppo, giornata e salute, con le risposte "
    "che dovresti sentire e i tre casi in cui conviene lasciar perdere."
)
CATEGORIA = "scegliere"

CONTENUTO = """\
Un ritiro di quattro giorni costa fra i quattrocento e i millecinquecento euro, chiede ferie e mette il tuo corpo in mano a qualcuno per un tempo lungo. È una delle spese meno reversibili che si fanno per il proprio benessere.

Eppure la maggior parte delle persone prenota dopo aver letto una pagina e guardato dieci foto, senza scrivere una riga. Il motivo è quasi sempre lo stesso: chiedere sembra diffidenza, e la diffidenza sembra fuori posto in un contesto che parla di apertura e di fiducia.

È il contrario. Chi organizza ritiri da anni si aspetta le domande, e la maggior parte ha già le risposte pronte in un documento. Chi si irrigidisce di fronte a una domanda semplice ti sta dando l'informazione più utile della conversazione.

Queste sono le domande che contano, divise per quello che proteggono.

## Sui soldi

**Quanto costa in tutto, comprese le tasse?**
La cifra che ti interessa è quella finale. Chiedi se il prezzo esposto include IVA, tassa di soggiorno, eventuali quote associative.

**Cosa è incluso e cosa no?**
Le voci che più spesso restano fuori: i transfer dall'aeroporto o dalla stazione, i pasti del primo e dell'ultimo giorno, i trattamenti individuali, le bevande, la biancheria. Un programma serio ha un elenco scritto di cosa comprende.

**Quanto è la caparra e quando si paga il saldo?**
La forma diffusa è un acconto fra il venti e il trenta per cento alla prenotazione e il saldo qualche settimana prima. Diffida di chi chiede l'intero importo mesi prima senza spiegare perché.

**Cosa succede se disdico?**
È la domanda che salva più soldi di tutte, e la risposta deve essere una politica scritta, con date e percentuali: entro trenta giorni rimborso pieno meno la caparra, entro quindici il cinquanta per cento, e così via. «Vediamo caso per caso» non è una politica, è una speranza.

**E se annullate voi?**
Succede: numeri insufficienti, un imprevisto di chi conduce. Chiedi se in quel caso il rimborso è integrale e in quanti giorni arriva. Chiedi anche entro quando decidete, perché quella data è il momento in cui puoi ancora annullare un volo senza perderlo tutto.

**Come si paga?**
Bonifico e carta vanno bene. Un pagamento che deve passare solo per canali senza tracciabilità, con la richiesta di non specificare la causale, è un segnale da prendere sul serio.

Se il prezzo ti sembra alto o basso senza capire perché, aiuta sapere [come si calcola il prezzo di un ritiro](/blog/prezzo-giusto-ritiro-come-calcolarlo): vitto e alloggio, spesso, pesano più di quanto sembri, e un prezzo molto sotto la media di solito significa che qualcosa è stato tagliato.

## Su chi conduce

**Chi conduce, esattamente?**
Nome e cognome, non «il nostro team». Se le sessioni sono tenute da persone diverse, chiedi chi fa cosa.

**Che formazione ha, e con chi?**
Non serve un diploma: serve una risposta specifica. «Formazione di cinquecento ore con questa scuola, nel 2019» è una risposta. «Studio da tutta la vita» non lo è.

**Da quanti anni conduce ritiri, e quante edizioni ha fatto questo?**
Un primo ritiro può essere ottimo, ma è utile saperlo, perché la prima edizione ha sempre qualcosa che non funziona.

**C'è qualcuno che parla la mia lingua?**
Sembra ovvio finché non ti trovi in una sessione di lavoro emotivo con una traduzione approssimativa.

Su come si legge una formazione e cosa vale un attestato, il quadro completo sta in [come capire se un operatore è serio](/blog/come-capire-se-un-operatore-olistico-e-serio).

## Sul gruppo

**Quante persone siete?**
È la domanda che cambia di più l'esperienza. Sotto le dodici persone c'è spazio per parlare; sopra le venticinque, in una pratica intensa, un solo facilitatore non riesce a vedere tutti.

**Quanti facilitatori ci sono per quante persone?**
Vale soprattutto per le pratiche che possono smuovere: respiro intenso, lavoro sul trauma, cerchi.

**Che tipo di persone partecipa di solito?**
Chiedi l'età media e se vengono più da sole o in coppia. Non è curiosità: se hai quarantacinque anni e il gruppo ne ha in media venticinque, la settimana sarà diversa da come te la immagini.

**Dormo in camera singola o condivisa, e con chi?**
La condivisa abbassa il prezzo e alza l'intensità. Se la singola esiste, chiedi quanto costa in più prima di prenotare, non dopo.

## Sulla giornata

**Com'è una giornata tipo, ora per ora?**
Un programma vero ha degli orari. «Pratiche, natura, condivisione» descrive un'atmosfera, non una giornata.

**A che ora si comincia?**
Alcuni ritiri partono alle sei del mattino. È una scelta legittima e conviene saperla prima di prenotare, non alla prima sveglia.

**Quanto del programma è obbligatorio?**
La risposta giusta è che nulla lo è. Chiedi esplicitamente se puoi saltare una sessione e restare in camera senza che sia un problema.

**Quanto tempo libero c'è?**
Un ritiro pieno dalle sei alle ventidue non è riposo, è un altro tipo di intensità. Entrambi vanno bene, purché tu sappia quale hai comprato.

**Ci sono momenti di silenzio, e per quanto?**
Alcuni ritiri prevedono ore o giornate in silenzio. Per qualcuno è la parte migliore, per altri è la ragione per scegliere un altro ritiro.

**C'è campo, e posso usare il telefono?**
Molti ritiri chiedono di consegnarlo. Se hai figli piccoli o un genitore anziano, chiedi come si fa a essere raggiungibili in caso di urgenza.

## Sul corpo e sulla salute

**Mi chiedete qualcosa sulla mia salute prima?**
Questa è la domanda che rovescia il tavolo, ed è la più informativa dell'elenco. Un ritiro che prevede pratiche intense e non fa nessuna anamnesi — questionario, colloquio, anche solo una mail di domande — sta saltando un passaggio che riguarda la tua sicurezza. Vale in particolare per le [tecniche di respiro intenso](/blog/breathwork-cose-tecniche-benefici), che hanno controindicazioni precise, e per il digiuno.

**Ci sono controindicazioni per quello che farete?**
Chi conosce la propria pratica sa elencarle senza esitare.

**Come funziona il cibo, e gestite intolleranze e allergie?**
Chiedi il tipo di alimentazione (spesso vegetariana), quanti pasti, e se una celiachia o un'allergia seria sono gestibili in quella cucina.

**Cosa succede se sto male, fisicamente o emotivamente?**
La risposta migliore è concreta: dov'è l'ospedale più vicino, chi resta con te, cosa è successo le altre volte. Chi ha esperienza ha già affrontato la cosa e la racconta senza drammi.

**Assumo farmaci o sono in terapia: cambia qualcosa?**
Devi poterlo dire senza sentirti giudicato. E nessuno, in nessun contesto, può suggerirti di sospendere una terapia: se succede, quello è il momento di andarsene, [prima ancora del ritiro](/blog/pratiche-olistiche-contro-stress-cosa-funziona).

## Sul luogo

**Dove si svolge, con l'indirizzo?**
Un luogo che resta vago fino al pagamento è un'anomalia. Cerca la struttura, guarda le recensioni di chi ci ha soggiornato per altri motivi.

**Come ci si arriva, e c'è un transfer?**
Chiedi il costo e l'orario. Un ritiro in mezzo alla natura può significare quaranta minuti di auto dalla stazione più vicina.

**Le camere e i bagni come sono?**
Bagno in camera o condiviso, riscaldamento, wifi. Nessuna di queste cose è superflua a febbraio.

## Le domande da fare a te stesso

Sono quattro, e vengono prima di tutte le altre, perché un ritiro può essere organizzato benissimo e restare quello sbagliato per te in questo momento.

**Cosa sto cercando?** Riposo, o movimento, o una risposta a qualcosa. Sono tre ritiri diversi, e il primo si riconosce dal programma leggero mentre il secondo si riconosce dagli orari.

**Sto attraversando un momento difficile?** Un lutto recente, una separazione, un periodo di terapia in corso non escludono un ritiro, ma cambiano quale. Le pratiche intense in un momento fragile chiedono un contesto che sappia reggerle, e vale la pena dirlo a chi organizza prima di partire.

**Voglio stare in gruppo o voglio stare da solo?** Un ritiro è quasi sempre una convivenza stretta con dieci sconosciuti. Se quello che cerchi è silenzio e nessuno intorno, esistono formule diverse.

**Sono disposto a stare scomodo?** Sveglie presto, cibo diverso, un letto in condivisione, ore senza telefono. La scomodità è spesso il punto, ma è utile sapere quanta ne accetti prima di pagare.

## Metti per iscritto quello che ti dicono

Quando le risposte arrivano al telefono, riassumile in una mail e mandale a chi le ha date: «Riepilogo quello che ci siamo detti, fammi sapere se ho capito bene». Nessuno si offende, e da quel momento gli accordi esistono in una forma consultabile da entrambi.

Vale soprattutto per le tre cose che generano i disaccordi veri: cosa comprende la quota, cosa succede in caso di disdetta, e cosa ti è stato detto sulla tua situazione di salute.

## Come si leggono le risposte

Il contenuto conta, ma tre cose contano di più.

**La velocità.** Una risposta entro due giorni lavorativi è normale. Chi impiega una settimana a rispondere prima che tu abbia pagato non diventerà più presente dopo.

**La precisione.** Le risposte utili contengono numeri, nomi e date. Quelle evasive contengono aggettivi.

**La reazione alla domanda.** Un organizzatore esperto risponde volentieri, perché sa che chi chiede è anche chi poi partecipa con attenzione. Chi si offende, chi ti fa sentire poco spirituale per aver chiesto di soldi, chi risponde che «devi fidarti del processo», ti ha appena detto come gestirà un tuo dubbio quando sarai lì.

## Tre risposte che valgono un no

**Promesse di guarigione.** Un ritiro che dichiara di curare una patologia, o che suggerisce di ridurre farmaci, sta oltrepassando un confine che è anche legale.

**Nessuna politica di cancellazione scritta.** Non è una formalità: è il segnale che quell'organizzazione non ha ancora affrontato la prima disdetta, oppure che preferisce non impegnarsi.

**Pressione a decidere subito.** «Restano due posti» ripetuto per tre settimane è una tecnica di vendita. Un ritiro che vale la pena resta valido anche fra due giorni.

## Come chiedere senza sentirti a disagio

Una mail sola, cinque o sei domande, in tono normale. Non serve giustificarsi né spiegare perché chiedi.

Una traccia che funziona:

> Buongiorno, sto valutando il ritiro di [date] e vorrei qualche informazione prima di prenotare: quante persone siete di solito, cosa comprende esattamente la quota, come funziona in caso di disdetta da parte mia, e se è previsto un questionario sulla salute prima dell'arrivo. Grazie.

Chi organizza ritiri riceve messaggi così ogni settimana. Se sei il primo a mandarne uno, quella è già un'informazione.

## Domande frequenti

**Non è scortese fare tutte queste domande?**
No, ed è il timore che ferma quasi tutti. Un organizzatore che lavora bene le riceve di continuo e spesso ha già un documento pronto.

**Quante ne faccio senza esagerare?**
Cinque o sei in una mail sola. Scegli quelle che pesano sul tuo caso: se hai un'allergia seria, la domanda sul cibo viene prima di quella sul silenzio.

**Se non rispondono a tutto, è un problema?**
Dipende da cosa saltano. Una risposta parziale sul programma capita; il silenzio sulle regole di disdetta o sulla salute è un'altra cosa.

**Posso chiedere di parlare al telefono?**
Sì, e dieci minuti di conversazione dicono più di dieci mail. La disponibilità stessa è una risposta.

**Come faccio a sapere se il prezzo è giusto?**
Confronta cosa include, non la cifra. Un ritiro che comprende alloggio in singola, tutti i pasti e i transfer non è paragonabile a uno che comprende solo le sessioni.

**E se ho già prenotato e le risposte non mi convincono?**
Rileggi le condizioni: se sei nella finestra di rimborso, la caparra persa costa meno di una settimana passata male. Se non lo sei, scrivi comunque le tue preoccupazioni prima di partire, così che chi conduce le sappia.
"""

# i link in entrata: l'articolo sui criteri chiude con una FAQ che
# apre esattamente su questo, e la guida al prezzo (lato professionisti)
# guadagna un lettore che capisce cosa sta comprando.
AGGIUNTE = [
    ("come-capire-se-un-operatore-olistico-e-serio",
     "**Posso chiedere di parlare prima di prenotare?**\n"
     "Sì, ed è consigliabile. La disponibilità a una conversazione "
     "preliminare gratuita di dieci minuti è già una risposta.",
     "**Posso chiedere di parlare prima di prenotare?**\n"
     "Sì, ed è consigliabile. La disponibilità a una conversazione "
     "preliminare gratuita di dieci minuti è già una risposta. Se stai "
     "valutando un ritiro, abbiamo raccolto [le domande da fare prima di "
     f"prenotare](/blog/{SLUG})."),
]


async def main(dry_run: bool) -> None:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from database import db

    print(f"{TITOLO}\n  slug: {SLUG}\n  categoria: {CATEGORIA}\n"
          f"  parole: {len(CONTENUTO.split())}\n"
          f"  descrizione: {len(DESCRIZIONE)} caratteri")
    esistente = await db.articles.find_one({"slug": SLUG}, {"_id": 0, "id": 1})
    print("  stato:", "gia' presente, si aggiorna" if esistente else "nuovo")
    if dry_run:
        print("\n--dry-run: nessuna scrittura")
        return

    now = datetime.now(timezone.utc)
    campi = {
        "title": TITOLO, "description": DESCRIZIONE, "content": CONTENUTO,
        "category": CATEGORIA, "author_name": "Aurya", "published": True,
        "updated_at": now, "translations": {},
        "related_slugs": [
            "come-capire-se-un-operatore-olistico-e-serio",
            "pratiche-olistiche-contro-stress-cosa-funziona",
            "breathwork-cose-tecniche-benefici",
        ],
    }
    if not esistente:
        campi |= {"id": str(uuid.uuid4()), "slug": SLUG,
                  "created_at": now, "published_at": now}
    await db.articles.update_one({"slug": SLUG}, {"$set": campi}, upsert=True)

    doc = await db.articles.find_one({"slug": SLUG},
                                     {"_id": 0, "featured_image_url": 1})
    if not doc.get("featured_image_url"):
        from routers.articles import _autogen_cover
        url = await _autogen_cover(SLUG, CATEGORIA)
        if url:
            await db.articles.update_one({"slug": SLUG},
                                         {"$set": {"featured_image_url": url}})
            print(f"  copertina: {url}")

    for slug, vecchio, nuovo in AGGIUNTE:
        d = await db.articles.find_one({"slug": slug}, {"_id": 0, "content": 1})
        if not d:
            print(f"  ASSENTE {slug}")
        elif nuovo in d["content"]:
            print(f"  link gia' presente in {slug[:40]}")
        elif vecchio in d["content"]:
            await db.articles.update_one({"slug": slug}, {"$set": {
                "content": d["content"].replace(vecchio, nuovo, 1)}})
            print(f"  link aggiunto in {slug[:40]}")
        else:
            print(f"  NON TROVATO in {slug[:40]} — controllare a mano")

    print("\npubblicato")


if __name__ == "__main__":
    asyncio.run(main("--dry-run" in sys.argv))
