"""ES1 — espansione della guida alla meditazione (812 → ~1950 parole).

PERCHE' QUESTA PER PRIMA. E' il pezzo magro con piu' link in entrata
del Magazine, e il protocollo minimo che conteneva era buono ma
rispondeva a una domanda sola: come si comincia. Chi comincia poi
inciampa in altre tre, e le trovava altrove.

COSA SI AGGIUNGE.

1. LE FAMIGLIE. La guida diceva in una FAQ che la mindfulness e' un
   tipo di meditazione, e non lo spiegava. Chi cerca "meditazione" si
   trova davanti nomi — vipassana, samatha, metta, trascendentale —
   senza sapere che fanno cose diverse.

2. COME SI STA SEDUTI. Banale finche' non sono i venti minuti in cui
   la schiena decide di parlare. Sedia, cuscino, sdraiato: tre
   soluzioni e i loro difetti.

3. LA PARTE CHE QUASI NESSUNO SCRIVE, ed e' il motivo per cui questa
   espansione vale: la meditazione ha effetti avversi documentati.
   Britton e colleghi li studiano da anni, e un lavoro pubblicato su
   JAMA Psychiatry nel 2022 su un campione di popolazione ha trovato
   che una parte non trascurabile di chi pratica riporta episodi di
   ansia aumentata, depersonalizzazione o riemersione di materiale
   doloroso. Quasi sempre transitori, e vale la pena saperli prima,
   perche' chi li incontra senza saperlo pensa di essere rotto.

4. MEDITARE SENZA SEDERSI. La pratica informale, che e' quella che
   sopravvive nelle settimane in cui la formale salta.

    venv/bin/python scripts/es1_espansione_meditazione.py [--dry-run]
"""
import asyncio
import os
import sys
from datetime import datetime, timezone

SLUG = "meditazione-per-chi-inizia-guida-semplice"
TITOLO = "Meditazione per chi inizia: come cominciare e cosa aspettarsi"
DESCRIZIONE = (
    "Il protocollo dei cinque minuti, le famiglie di meditazione, come si "
    "sta seduti, cosa dice la ricerca e cosa fare se la pratica smuove."
)

SERIO = "/blog/come-capire-se-un-operatore-olistico-e-serio"
DOMANDE = "/blog/domande-da-fare-prima-di-prenotare-un-ritiro"
NIDRA = "/blog/yoga-nidra-cose-come-funziona-una-sessione"
STILI = "/blog/differenze-tipi-di-yoga-hatha-vinyasa-ashtanga-yin-kundalini"
PRANA = "/blog/pranayama-tecniche-respirazione-yoga"
KIT = "/blog/kit-pratiche-quotidiane-15-minuti"
CHAKRA = "/blog/chakra-cosa-sono-i-sette-come-si-usano"

CONTENUTO = f"""\
C'è una cosa che chi medita da anni sa bene e chi inizia scopre con sollievo: non si tratta di svuotare la mente. Se hai provato a meditare, hai pensato «non ci riesco, penso troppo» e hai mollato, questa guida è per te. Perché quel pensiero, esattamente quello, È la pratica.

## Cosa significa meditare

Meditare significa allenare l'attenzione. Ti siedi, porti l'attenzione su qualcosa di semplice (il respiro, di solito), la mente scappa dopo pochi secondi perché è il suo mestiere, tu te ne accorgi e la riporti indietro. Quel momento in cui te ne accorgi e torni: quello è l'esercizio. Una ripetizione, come in palestra.

Chi crede di «non riuscire a meditare» perché ha pensieri sta fraintendendo il gioco: i pensieri non sono il fallimento della pratica, sono la materia prima. Una sessione in cui la mente scappa cinquanta volte e tu torni cinquanta volte è una sessione riuscita.

## Come iniziare: il protocollo minimo

1. **Cinque minuti, non trenta.** L'errore numero uno è partire in grande. Cinque minuti al giorno battono un'ora alla settimana, sempre.
2. **Stesso momento, stesso posto.** Dopo il caffè, prima della doccia: aggancia la pratica a un'abitudine che hai già. La costanza nasce dall'aggancio, non dalla forza di volontà.
3. **Siediti comodo.** Sedia normalissima, schiena dritta ma non rigida, mani sulle gambe. Il loto non serve.
4. **Segui il respiro.** Non modificarlo: osservalo. L'aria che entra, l'aria che esce. Quando ti accorgi che stai pensando ad altro, e succederà subito, torna al respiro. Senza giudicarti: il giudizio è solo un altro pensiero.
5. **Fine.** È tutto qui. La profondità arriva dalla ripetizione, non dalla complicazione.

Un timer aiuta, così non controlli l'orologio. Le app vanno bene per iniziare, con un'avvertenza: la voce guidata è una stampella utile i primi tempi, ma prima o poi vale la pena provare il silenzio.

## Come si sta seduti

Sembra un dettaglio finché non sono i venti minuti in cui la schiena comincia a parlare. Tre soluzioni, con i loro difetti.

**La sedia.** La più sottovalutata e la più pratica. Piedi a terra, schiena staccata dallo schienale o appoggiata se serve, mani sulle cosce. Funziona per chiunque e non ha controindicazioni. Il difetto: è così ordinaria che sembra di barare, e non è così.

**Il cuscino.** Seduti a terra, bacino più alto delle ginocchia — è questo che conta, non le gambe incrociate. Un cuscino da meditazione, o due cuscini da divano, o una coperta piegata. Il difetto: senza abitudine, dopo dieci minuti le gambe si addormentano, e la scomodità diventa l'unica cosa che osservi.

**Sdraiato.** Legittimo, soprattutto per chi ha dolori. Il difetto è ovvio: ci si addormenta. Se ti succede sempre e ti va bene così, quello che stai cercando somiglia più allo [yoga nidra]({NIDRA}), che si pratica proprio da sdraiati e non considera il sonno un errore.

La regola sotto tutte e tre: **la posizione deve essere sostenibile per il tempo che hai deciso**. Se la stai correggendo di continuo, stai meditando sulla posizione.

## Le famiglie di meditazione

«Meditazione» è un nome di famiglia, non di pratica. Le principali fanno cose diverse, e sapere quale hai davanti evita di concludere che una cosa non fa per te quando ne hai provata un'altra.

**Concentrazione (samatha).** L'attenzione resta su un oggetto solo — il respiro, un suono, una fiamma — e si torna lì ogni volta. È la porta d'ingresso della maggior parte delle tradizioni, ed è il protocollo minimo descritto qui sopra.

**Visione profonda (vipassana).** Invece di restare su un oggetto, si osserva quello che passa: sensazioni, pensieri, impulsi, uno dopo l'altro, senza seguirli. È la base della mindfulness contemporanea. Nella forma tradizionale si pratica in ritiri di dieci giorni in silenzio.

**Mindfulness.** La versione laica e strutturata della vipassana, codificata alla fine degli anni Settanta da Jon Kabat-Zinn in ambito ospedaliero. Il programma di riferimento, MBSR, dura otto settimane con incontri di gruppo e pratica quotidiana. È la forma più studiata di tutte.

**Amorevolezza (metta).** Si ripetono mentalmente frasi di augurio rivolte prima a sé, poi a una persona cara, poi a una neutra, poi a una difficile. Suona sentimentale e non lo è: è la pratica con gli effetti più misurabili sull'umore e sulla reattività.

**Meditazione trascendentale.** Si ripete internamente un mantra ricevuto da un insegnante, venti minuti due volte al giorno. È un percorso a pagamento con una struttura organizzativa propria.

**Meditazioni guidate e visualizzazioni.** Una voce accompagna in un'immagine o in un percorso interiore. Utilissime per cominciare, ed è bene sapere che stanno facendo un'altra cosa rispetto alla pratica silenziosa.

**Le pratiche in movimento.** Camminata meditativa, e in senso lato tutto il lavoro sul respiro dello [yoga]({PRANA}). Chi non sopporta l'immobilità spesso trova qui la porta.

Nessuna è migliore. La domanda utile è: **cosa riesco a fare tutti i giorni?**

## Cosa dice la scienza

La meditazione è fra le pratiche di questo mondo con la letteratura più ampia, e conviene distinguere.

**Dove le prove sono buone.** Riduzione dello stress percepito e dei sintomi d'ansia, miglioramento della qualità del sonno, maggiore capacità di regolare le emozioni. I programmi strutturati di otto settimane, MBSR in testa, sono fra gli interventi non farmacologici più studiati degli ultimi decenni. Esiste anche una letteratura sull'uso della mindfulness nella prevenzione delle ricadute depressive, dove è entrata in alcune linee guida cliniche come intervento di accompagnamento.

**Dove sono più incerte.** Gli effetti sulla pressione arteriosa, sul dolore cronico e sulle prestazioni cognitive esistono ma sono modesti e variabili.

**Un limite generale.** Gli effetti misurati sono in genere moderati, non trasformativi, e molti studi confrontano la meditazione con il non fare nulla invece che con un'altra attività di pari impegno. Il che non toglie valore: significa che una parte dell'effetto è lo stare fermi mezz'ora con attenzione, e quella è comunque una cosa che quasi nessuno fa.

## Quando la pratica smuove qualcosa

Questa parte si legge di rado, e serve.

La meditazione ha **effetti indesiderati documentati**. Un gruppo di ricerca guidato da Willoughby Britton se ne occupa da anni, e uno studio pubblicato su *JAMA Psychiatry* nel 2022 su un campione di popolazione ha trovato che una quota non trascurabile di chi pratica riporta almeno un episodio di questo tipo: ansia che aumenta invece di calare, senso di distacco da sé o dalla realtà, riemersione di ricordi o emozioni dolorose, sonno peggiorato, in alcuni casi un senso di vuoto.

Tre cose da tenere insieme.

**Sono quasi sempre transitori.** Nella maggior parte delle persone passano da soli, e non sono un segno che qualcosa in te sia rotto.

**Sono più probabili in certe condizioni.** Pratiche lunghe e intensive, ritiri in silenzio, e una storia di trauma o di disturbi dissociativi. È il motivo per cui un ritiro di dieci giorni non è il posto da cui cominciare.

**Sapere che possono succedere cambia come li si attraversa.** Chi li incontra senza averne mai sentito parlare tende a concludere di aver sbagliato qualcosa, e spesso smette in silenzio.

Cosa fare, in pratica: accorcia la sessione, apri gli occhi, passa a una pratica in movimento o a una guidata, e parlane con qualcuno. Se attraversi un periodo difficile o hai una storia di trauma, comincia accompagnato da chi ha una formazione specifica su quel terreno — è uno dei casi in cui [scegliere bene chi ti guida]({SERIO}) conta più della tecnica.

E la regola generale: la meditazione affianca un percorso di cura, non lo sostituisce.

## I tre errori che fanno mollare

**Aspettarsi il rilassamento immediato.** A volte arriva, a volte no. Meditare non è rilassarsi: è osservare. Il rilassamento è un effetto collaterale frequente, non l'obiettivo.

**Giudicare le sessioni.** «Oggi è andata male» non esiste: esistono sessioni in cui la mente era agitata e le hai fatto compagnia comunque. Sono le più preziose.

**Mollare alla terza settimana.** È il momento in cui l'entusiasmo cala e l'abitudine non si è ancora formata. Sapere che arriva è metà della soluzione: riduci a tre minuti se serve, ma non saltare.

## Meditare senza sedersi

È la pratica che sopravvive nelle settimane in cui quella formale salta, e in molte tradizioni è considerata il vero obiettivo: portare la stessa attenzione dentro le cose che fai già.

**Lavare i piatti.** Acqua, temperatura, peso del piatto, rumore. Quando la mente parte, torna alle mani.

**Camminare.** Cento metri, senza telefono, sentendo il piede che appoggia. Anche dal parcheggio all'ufficio.

**I tre respiri.** Prima di aprire una porta, prima di rispondere a un messaggio che ti ha irritato, prima di mangiare. Tre respiri interi, contati.

**Aspettare.** Alla cassa, al semaforo, in coda. Il momento in cui l'istinto è tirare fuori il telefono è esattamente il momento di praticare.

Non sostituiscono la pratica seduta, che resta il posto dove si costruisce il muscolo. Ma sono quelle che tengono in vita l'abitudine, e si incastrano bene con le altre pratiche brevi del [kit dei quindici minuti]({KIT}).

## Come si va avanti

**Settimane 1-3: cinque minuti.** L'obiettivo è solo esserci tutti i giorni. Non conta com'è andata.

**Settimane 4-8: dieci minuti.** Qui la maggior parte delle persone comincia ad accorgersi di qualcosa fuori dalla sessione: una reazione che non è partita, un sonno più facile.

**Dopo il secondo mese: venti minuti, o due sessioni.** È la soglia in cui molte tradizioni collocano il punto in cui la pratica cambia qualità.

**Quando ha senso un insegnante.** Quando vuoi approfondire una famiglia specifica, quando la pratica smuove qualcosa, o quando sei fermo da mesi senza capire perché.

**Quando ha senso un ritiro.** Un weekend o qualche giorno dedicato porta la pratica a una profondità che a casa richiederebbe mesi. Non è il punto di partenza, è un acceleratore per chi ha già un'abitudine. Se lo stai valutando, la scelta di chi conduce pesa più del luogo: i criteri stanno in [come capire se un operatore è serio]({SERIO}) e le domande da fare prima di prenotare le abbiamo raccolte [qui]({DOMANDE}).

Se l'idea di stare seduti resta l'ostacolo vero, [lo yoga nidra]({NIDRA}) si pratica da sdraiati e ammette perfino di addormentarsi. Se invece stai valutando una pratica sul tappetino, [le differenze fra i tipi di yoga]({STILI}) spiegano cosa cambia da una lezione all'altra.

## Domande frequenti

**Quanto tempo serve per vedere i benefici?**
Con cinque o dieci minuti quotidiani, la maggior parte delle persone nota qualcosa su sonno, reattività e lucidità entro tre o quattro settimane. Il cambiamento è graduale: si vede meglio guardando indietro di due mesi che di due giorni.

**Meglio la mattina o la sera?**
Il momento in cui la fai davvero. La mattina ha un vantaggio pratico: la giornata non ha ancora avuto il tempo di travolgerti.

**Ho bisogno di un insegnante?**
Per iniziare no, il protocollo minimo basta. Diventa prezioso quando vuoi approfondire, quando la pratica smuove qualcosa, o quando sei fermo senza capire perché.

**Che differenza c'è fra meditazione e mindfulness?**
La mindfulness è un tipo di meditazione — attenzione al momento presente, senza giudizio — diventata anche protocollo laico e clinico. La meditazione è la famiglia grande: dentro ci sono anche concentrazione, amorevolezza, mantra e pratiche devozionali.

**Da quale famiglia conviene cominciare?**
Dalla concentrazione sul respiro, che è la più semplice da spiegare e la più difficile da sbagliare. Le altre hanno senso dopo, quando la pratica c'è.

**È normale addormentarsi?**
Sì, soprattutto la sera e da sdraiati. Se succede sempre, prova seduto e a un'altra ora. Se ti va bene addormentarti, quello che cerchi somiglia allo yoga nidra.

**Meditare può fare male?**
In una minoranza di casi la pratica intensiva porta ansia, distacco o riemersione di materiale doloroso, quasi sempre transitori. Con sessioni brevi il rischio è basso; con una storia di trauma conviene essere accompagnati.

**Serve credere in qualcosa?**
No. Le pratiche di concentrazione e mindfulness sono laiche e non richiedono adesione a nessuna tradizione, anche quando da una tradizione provengono.

**Devo lavorare sui chakra mentre medito?**
No, sono due cose distinte. La mappa dei [chakra]({CHAKRA}) può essere usata come guida dell'attenzione da chi la trova utile, e non è parte del protocollo di base.
"""


async def main(dry_run: bool) -> None:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from database import db

    doc = await db.articles.find_one({"slug": SLUG}, {"_id": 0, "content": 1})
    if not doc:
        print(f"ASSENTE: {SLUG}")
        return
    print(f"{TITOLO}\n  prima: {len(doc['content'].split())} parole"
          f"\n  dopo:  {len(CONTENUTO.split())} parole"
          f"\n  descrizione: {len(DESCRIZIONE)} caratteri")
    if CONTENUTO == doc["content"]:
        print("\ngia' aggiornato")
        return
    if dry_run:
        print("\n--dry-run: nessuna scrittura")
        return
    await db.articles.update_one({"slug": SLUG}, {"$set": {
        "title": TITOLO, "description": DESCRIZIONE, "content": CONTENUTO,
        "author_name": "Aurya",
        "related_slugs": [KIT.split("/blog/")[1], NIDRA.split("/blog/")[1],
                          CHAKRA.split("/blog/")[1]],
        "updated_at": datetime.now(timezone.utc),
    }})
    print("\naggiornato (slug e data di pubblicazione invariati)")


if __name__ == "__main__":
    asyncio.run(main("--dry-run" in sys.argv))
