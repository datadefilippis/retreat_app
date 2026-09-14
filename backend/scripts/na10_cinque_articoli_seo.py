"""NA10 (14/9/2026 notte) — i primi cinque articoli del piano SEO-editoriale
(docs/PIANO_SEO_EDITORIALE_2026-09.md, calendario §6), uno per porta:

  C  Meditazione guidata per dormire: 10 minuti           → il Cerchio
  O  Corso di yoga 200 ore: come valutarlo, cosa serve dopo → entra-nella-rete
  D  Riflessologia plantare: mappa, seduta, prezzi        → /operatori/riflessologia
  A  Welfare aziendale 2026: esempi, deducibilità, benessere → /aziende
  R  Yoga e ritiri in Toscana: la guida                   → il Cerchio

Regola del founder: nessun doppione dei 47 articoli esistenti (elenco in
docs/seo/articoli_esistenti_2026-09-14.json): questi cinque coprono intenti
che non avevano una pagina. Nessuna firma di operatori. Ogni pezzo ha
«In breve», FAQ (domande in grassetto, per il FAQPage della shell),
link interni verso articoli che esistono davvero e la chiamata della sua
porta. Le affermazioni sul corpo hanno la fonte o la formula «chi lo
pratica dice».

    venv/bin/python scripts/na10_cinque_articoli_seo.py [--dry-run] [--ping]
"""
import asyncio
import os
import re
import sys
import uuid
from datetime import datetime, timezone

# articoli esistenti che si linkano (verificati nell'elenco del 14/9)
MEDIT = "meditazione-per-chi-inizia-guida-semplice"
NIDRA = "yoga-nidra-cose-come-funziona-una-sessione"
PRANA = "pranayama-tecniche-respirazione-yoga"
KIT = "kit-pratiche-quotidiane-15-minuti"
STRESS = "pratiche-olistiche-contro-stress-cosa-funziona"
MBSR = "mindfulness-cose-mbsr-come-funziona"
RESPIRO = "respiro-sistema-nervoso-cosa-succede"
PIVA = "partita-iva-operatore-olistico-fiscalita-guida"
ATECO = "codice-ateco-operatore-olistico"
RC = "assicurazione-rc-operatore-olistico"
BIO = "bio-professionale-operatore-olistico"
LEGGE = "legge-4-2013-professioni-olistiche"
SCEGLI_INS = "come-scegliere-un-insegnante-di-yoga"
TIPI_YOGA = "differenze-tipi-di-yoga-hatha-vinyasa-ashtanga-yin-kundalini"
YOGA = "yoga-cose-da-dove-viene-come-cominciare"
MASSAGGIO = "massaggio-olistico-tipi-cosa-aspettarsi"
SHIATSU = "shiatsu-cose-come-funziona-una-seduta"
COSTI = "quanto-costano-pratiche-olistiche"
SERIO = "come-capire-se-un-operatore-olistico-e-serio"
COLLOQUIO = "primo-colloquio-operatore-olistico"
SCEGLI_RIT = "come-scegliere-un-ritiro"
PORTARE = "cosa-portare-a-un-ritiro"
DOMANDE = "domande-da-fare-prima-di-prenotare-un-ritiro"
CAMMINI = "cammini-italiani-quale-scegliere-la-prima-volta"
PREZZO_RIT = "prezzo-giusto-ritiro-come-calcolarlo"
PROMUOVI = "come-promuovere-un-ritiro-e-riempire-i-posti"

# ── 1. Meditazione guidata per dormire ──────────────────────────────

SLUG_1 = "meditazione-guidata-per-dormire-10-minuti"
TITOLO_1 = "Meditazione guidata per dormire: la pratica di 10 minuti"
DESCR_1 = ("Una pratica di dieci minuti da fare a letto, passo per passo: cosa dice la "
           "ricerca sul sonno, gli errori che tengono svegli, e le tracce da ascoltare.")
IN_BREVE_1 = ("Una meditazione per dormire non «spegne» la mente: sposta l'attenzione dal pensare "
              "al sentire, e il corpo fa il resto. Dieci minuti bastano se si fanno ogni sera nello "
              "stesso modo. Qui trovi la pratica scritta passo per passo, le tracce sonore di Aurya "
              "e i casi in cui serve un medico, non una traccia.")
CONTENUTO_1 = """\
Chi cerca una meditazione per dormire di solito ha già provato tutto il resto: niente schermi, camomilla, la stanza al buio. E poi, a letto, la testa riparte. Una pratica guidata funziona perché non chiede di *smettere di pensare*, cosa che nessuno sa fare a comando, ma di spostare l'attenzione dal pensiero al corpo, dove non c'è niente da risolvere.

Questa guida contiene una pratica di dieci minuti scritta passo per passo, che puoi seguire da sola o da solo la prima sera e poi lasciare che ti guidi una voce. In fondo trovi le tracce sonore di Aurya e le domande più frequenti.

## Perché funziona, in tre righe

Il sonno non si comanda: arriva quando il sistema nervoso passa dalla modalità di allerta a quella di riposo. Le pratiche che portano l'attenzione sul respiro e sul corpo abbassano l'attivazione, e questo è misurabile: uno studio randomizzato pubblicato su *JAMA Internal Medicine* nel 2015 (Black e colleghi) ha trovato che un programma di consapevolezza migliorava la qualità del sonno in adulti con disturbi moderati più di un corso di igiene del sonno. Il respiro lento, sotto i sei atti al minuto, aumenta l'attività del nervo vago; ne abbiamo scritto in [respiro e sistema nervoso](/blog/""" + RESPIRO + """).

Non è magia e non sostituisce le cure: se il problema dura da mesi, in fondo diciamo quando fermarsi e parlare con un medico.

## La pratica di dieci minuti

Fatta a letto, al buio, a luci spente. Non serve una posizione particolare: la posizione in cui dormi.

**Minuto 1 — arrivare.** Sdraiati come per dormire. Senti il peso del corpo sul materasso: la testa, le spalle, la schiena, le gambe. Non cambiare nulla, solo nota dove il corpo appoggia.

**Minuti 2-3 — il respiro, senza guidarlo.** Porta l'attenzione al punto dove senti meglio il respiro: le narici, il petto o la pancia. Non allungarlo, non controllarlo. Conta tre respiri, poi ricomincia da uno. Se perdi il conto, va bene: perdere il conto è la pratica.

**Minuti 4-6 — il corpo, dai piedi alla testa.** Sposta l'attenzione lentamente: le dita dei piedi, le piante, le caviglie, i polpacci, le ginocchia, le cosce. Ogni zona la senti per due respiri e lasci andare. Poi il bacino, la pancia, il petto, le mani, le braccia, le spalle. Il collo, la mandibola (di solito è stretta: lasciala cadere), gli occhi, la fronte. Questo è il *body scan*, la tecnica su cui si fonda lo [yoga nidra](/blog/""" + NIDRA + """).

**Minuti 7-8 — allungare l'espiro.** Ora, e solo ora, rendi l'espirazione un po' più lunga dell'inspirazione. Un ritmo che molti trovano naturale: inspira contando quattro, espira contando sei. Se conti troppo, smetti di contare e senti solo che l'espiro è lungo.

**Minuti 9-10 — lasciare.** Smetti di fare qualsiasi cosa. Non c'è più niente da seguire. Se arriva un pensiero, lo guardi passare come una macchina fuori dalla finestra. Se ti addormenti prima della fine, è il risultato giusto.

## Gli errori che tengono svegli

- **Cercare di addormentarsi.** È l'unico sforzo che produce l'effetto contrario. L'obiettivo della pratica è sentire il corpo, non dormire: il sonno è un effetto collaterale.
- **Cambiare pratica ogni sera.** Il sonno ama la ripetizione. Stessa pratica, stessa ora, per almeno due settimane prima di giudicare.
- **Farla con lo schermo acceso.** Se ascolti una traccia, il telefono va a faccia in giù, luminosità al minimo, o meglio ancora l'audio parte e lo schermo si spegne.
- **Guardare l'ora.** Se non ti addormenti in venti minuti, la regola degli specialisti del sonno è alzarsi, fare qualcosa di noioso a luce bassa e tornare a letto quando torna la sonnolenza. Restare a lottare insegna al cervello che il letto è un posto dove si lotta.

## Le tracce da ascoltare

Seguire una voce o un suono toglie l'ultimo compito, quello di ricordarsi i passaggi.

- [Le meditazioni di Aurya](/meditazioni): sessioni sonore composte dai professionisti della rete, per dormire, meditare, rilassarsi. L'ascolto è riservato a chi fa parte del Cerchio: ci si iscrive in un minuto, gratis, e si ricevono anche le nuove tracce quando escono.
- [Meditazione «Mondo Nuovo», onde delta](/frequenze/meditazione-mondo-nuovo-onde-delta): ventisette minuti composti da Aurya, pensati per il passaggio verso il sonno.
- [Respiro](/sound/respiro): dieci minuti gratuiti, senza registrarsi, di guida sonora alla respirazione lenta a sei atti al minuto. È l'esercizio dei minuti 7-8 fatto da un suono.
- [Calm](/sound/calm): sei minuti di ascolto costruiti per creare uno spazio di calma. Non è una terapia e non promette effetti, come tutto quello che pubblichiamo su Aurya Sound.

Se preferisci pratiche brevi da fare di giorno, nel [kit delle sette pratiche da quindici minuti](/blog/""" + KIT + """) ce ne sono due per la sera.

## Quando la traccia non basta

Una meditazione aiuta il sonno disturbato dallo stress, dai pensieri, dalle giornate troppo piene. Non cura l'insonnia cronica, che gli specialisti definiscono come difficoltà a dormire almeno tre notti a settimana per almeno tre mesi con conseguenze di giorno. In quel caso il trattamento di prima scelta è la terapia cognitivo-comportamentale per l'insonnia, e il primo passo è il medico di base. Lo stesso vale se russi forte con pause del respiro, se ti addormenti di giorno senza volerlo, o se il sonno è cambiato insieme all'umore.

Se vuoi partire da zero con la meditazione, la [guida semplice per chi inizia](/blog/""" + MEDIT + """) spiega postura, durata e cosa aspettarsi. Per il respiro, le [tecniche del pranayama](/blog/""" + PRANA + """).

## Domande frequenti

**Quanto deve durare una meditazione per dormire?**
Dieci minuti bastano, se si fanno ogni sera. Le tracce più lunghe, come i ventisette minuti di «Mondo Nuovo», servono a chi vuole accompagnare tutto il passaggio al sonno; non sono «più efficaci», sono più lunghe.

**Va bene addormentarsi prima della fine?**
Sì. È il risultato che cerchi. Se ascolti una traccia, imposta il telefono perché si spenga da solo.

**Meglio una voce o solo suoni?**
Le prime sere una voce aiuta a non perdere i passaggi. Con l'abitudine molte persone passano a suoni senza parole, perché la voce inizia a «svegliare» l'attenzione. Provale entrambe per una settimana.

**Funziona anche per chi si sveglia alle tre di notte?**
Lo stesso schema, dal minuto 4, si può fare al risveglio notturno. La regola dei venti minuti vale anche lì: se non torna il sonno, ci si alza a luce bassa.

**È adatta ai bambini?**
Il body scan si fa anche con i bambini dai sei anni, con parole semplici e più corto. Con i più piccoli funziona meglio una storia letta a voce bassa.

**Quando devo vedere un medico?**
Se la difficoltà a dormire dura da più di tre mesi, tre notti a settimana o più, se russi con pause del respiro, o se il sonno è peggiorato insieme all'umore. La meditazione può accompagnare una cura, non sostituirla.
"""

# ── 2. Corso di yoga 200 ore ─────────────────────────────────────────

SLUG_2 = "corso-yoga-200-ore-come-valutarlo-cosa-serve-dopo"
TITOLO_2 = "Corso di yoga 200 ore: come valutarlo e cosa serve dopo"
DESCR_2 = ("Cosa vale davvero un corso da 200 ore in Italia, come riconoscerne uno serio, "
           "quanto costa, e cosa serve per insegnare dopo: fisco, assicurazione, spazio, allievi.")
IN_BREVE_2 = ("In Italia nessun corso di yoga è «riconosciuto dallo Stato»: le 200 ore sono uno "
              "standard di settore, non un titolo. Un corso serio si vede dalle ore in presenza, "
              "dall'anatomia, dalla pratica di insegnamento e dai nomi di chi insegna. Il corso è "
              "l'inizio: partita IVA, assicurazione, uno spazio e i primi allievi vengono dopo, e "
              "nessuna scuola te ne parla.")
CONTENUTO_2 = """\
«Come diventare insegnante di yoga» è una delle domande più cercate in Italia, e quasi tutte le risposte arrivano da chi vende un corso. Questa guida non ne vende: spiega cosa vale un corso da 200 ore, come si riconosce uno fatto bene, quanto costa, e soprattutto cosa succede il giorno dopo il diploma, che è la parte di cui nessuno parla.

## Cosa sono «le 200 ore»

Duecento ore è lo standard minimo fissato da *Yoga Alliance*, un registro privato statunitense nato negli anni Novanta. Chi completa un corso presso una scuola registrata può iscriversi come RYT-200 (*Registered Yoga Teacher*). È un registro, non un albo: paga una quota annuale, non verifica le competenze, e in Italia non ha alcun valore legale.

In Italia l'insegnamento dello yoga rientra nelle professioni **non organizzate in ordini o collegi**, regolate dalla [legge 4/2013](/blog/""" + LEGGE + """): chiunque può esercitare, dichiarando la propria formazione e senza usare titoli che confondano con professioni sanitarie. Gli attestati degli enti di promozione sportiva (CSEN, ASI, UISP e altri, riconosciuti dal CONI) permettono di lavorare nelle associazioni sportive dilettantistiche con il regime fiscale agevolato di quel mondo; anche questi non sono «riconoscimenti statali» della professione.

Tradotto: **nessun corso ti rende insegnante per legge**. Ti rende insegnante la preparazione, e il corso è il posto dove si costruisce. Per questo conviene giudicarlo per quello che contiene, non per il bollino.

## Come si riconosce un corso serio

Otto cose da controllare prima di versare l'acconto.

1. **Ore in presenza.** Un corso da 200 ore interamente online non può insegnare a correggere un corpo. Va bene una parte teorica a distanza; la pratica e la didattica si fanno in sala.
2. **Anatomia e fisiologia vere.** Almeno venti ore, con qualcuno che le sa insegnare: fisioterapisti, osteopati, medici, o insegnanti con una formazione specifica. Se il programma dice «anatomia sottile» e basta, manca la metà che serve a non far male.
3. **Pratica di insegnamento.** Ore in cui insegni tu, ai compagni di corso, con correzione. Un corso in cui si pratica soltanto forma praticanti, non insegnanti.
4. **Chi insegna.** Nomi, biografie, anni di insegnamento. Se il sito mostra solo la scuola e non le persone, chiedi. Un buon segno è poter fare una lezione con l'insegnante principale prima di iscriversi.
5. **Il lignaggio dichiarato.** Non serve una tradizione antica; serve sapere che stile imparerai (hatha, vinyasa, ashtanga, yin, kundalini: le [differenze](/blog/""" + TIPI_YOGA + """) sono sostanziali) e da chi lo ha imparato chi te lo insegna.
6. **Numero di allievi.** Sopra i 25-30 per un insegnante la correzione individuale sparisce.
7. **Contratto e rimborso.** Programma scritto, calendario, cosa succede se ti ritiri, se salti un weekend, se la scuola cancella.
8. **Cosa promettono.** «Riconosciuto dallo Stato», «abilitante», «garantito lavoro» sono formule che dovrebbero far chiudere la pagina.

Su come si riconosce chi lavora bene, dal lato di chi cerca un insegnante, abbiamo scritto [una guida a parte](/blog/""" + SCEGLI_INS + """): leggerla da futuro insegnante aiuta a capire cosa cercheranno i tuoi allievi.

## Quanto costa e quanto dura

Le fasce che si vedono in Italia nel 2026: **da 1.500 a 4.500 euro** per 200 ore, con i corsi intensivi residenziali (tre-quattro settimane) nella parte alta e i corsi nei weekend, distribuiti su otto-dieci mesi, nella parte media. Il prezzo non dice la qualità: dice il formato, il luogo e il vitto. Un corso da 1.200 euro tutto online e uno da 4.000 in un centro con vitto e alloggio possono avere lo stesso valore didattico, o nessuno.

A questo si aggiungono, quasi sempre fuori prezzo: i libri, l'assicurazione per la pratica, la quota dell'ente di promozione sportiva se il corso la richiede, e il tempo. Il formato nei weekend permette di continuare a lavorare; quello intensivo permette di finire in un mese ma non di praticare l'insegnamento nel tempo.

## Il giorno dopo il diploma

Qui finiscono le brochure e comincia la parte utile.

**Il fisco.** Se insegni saltuariamente, esistono la prestazione occasionale e, dentro le associazioni sportive, i compensi sportivi con la loro soglia esente. Se insegni con continuità serve la partita IVA, quasi sempre in regime forfettario, con il codice ATECO giusto. Ne abbiamo scritto in dettaglio: [partita IVA per operatori olistici](/blog/""" + PIVA + """) e [codice ATECO](/blog/""" + ATECO + """). Il commercialista che conosce il settore vale la sua parcella.

**L'assicurazione.** Una polizza di responsabilità civile professionale è la prima cosa da fare, prima della prima lezione: [la guida](/blog/""" + RC + """).

**Lo spazio.** Le domande «affitto sala yoga Milano», «coworking olistico» sono fra le più cercate da chi ha appena finito il corso. Le strade: l'affitto a ore in un centro già avviato (si paga una quota per lezione o una percentuale), la sala in condivisione con altri operatori, le lezioni all'aperto nei mesi buoni, il domicilio degli allievi, e il proprio spazio quando i numeri lo reggono. Partire senza affitto fisso è la regola: i costi fissi decidono se un'attività sopravvive al primo inverno.

**Il prezzo.** In Italia una lezione di gruppo va dai 10 ai 20 euro a persona, una lezione privata dai 40 agli 80, con differenze forti fra città e provincia. Non parti dal prezzo che vorresti: parti da quanto costa la sala, quante persone servono per coprirla, e da lì.

**I primi allievi.** Vengono da tre posti: le persone che già conosci (che sono più di quante pensi), il centro in cui affitti la sala, e la tua presenza online. Per quest'ultima serve una cosa sola all'inizio: una pagina che dica chi sei, cosa insegni, dove e quando, con un modo per prenotare. Su Aurya il profilo pubblico fa esattamente questo ed è gratis; la [bio professionale](/blog/""" + BIO + """) è la parte che conta di più, e ne abbiamo fatto una guida.

**Continuare a imparare.** Le 200 ore sono l'inizio della formazione, non la fine. Le scuole serie lo dicono: dopo un anno di insegnamento si capisce cosa manca, e si sceglie il modulo successivo con cognizione.

## Domande frequenti

**Un corso di yoga 200 ore è riconosciuto in Italia?**
No, nessun corso di yoga è riconosciuto dallo Stato. L'insegnamento dello yoga è una professione non organizzata (legge 4/2013): si può esercitare dichiarando la propria formazione. Yoga Alliance è un registro privato; gli attestati degli enti di promozione sportiva valgono nel mondo delle associazioni.

**Si può fare un corso 200 ore online?**
Una parte teorica sì. Un corso interamente online non insegna a correggere un corpo né a condurre una sala: per insegnare servono ore in presenza e pratica di insegnamento con correzione.

**Quanto costa diventare insegnante di yoga?**
Fra 1.500 e 4.500 euro per il corso da 200 ore, più assicurazione, libri e, se serve, la quota dell'ente sportivo. Poi i costi per lavorare: partita IVA, spazio, sito o profilo.

**Serve la partita IVA per insegnare yoga?**
Non subito: per attività saltuarie esistono la prestazione occasionale e i compensi sportivi nelle associazioni. Con continuità e volumi serve la partita IVA, di solito in regime forfettario.

**Quanto guadagna un insegnante di yoga?**
Dipende da quante lezioni tiene e da dove. Con lezioni di gruppo a 10-20 euro a persona e private a 40-80, molti insegnanti nei primi anni affiancano un altro lavoro. Chi vive di yoga di solito combina lezioni, privati, ritiri e un pubblico costruito nel tempo.

**Che differenza c'è fra 200 e 500 ore?**
Le 500 ore (RYT-500) aggiungono 300 ore di approfondimento, in genere dopo almeno un anno di insegnamento. Non sono «più riconosciute»: sono più formazione.
"""

# ── 3. Riflessologia plantare ────────────────────────────────────────

SLUG_3 = "riflessologia-plantare-mappa-seduta-prezzi"
TITOLO_3 = "Riflessologia plantare: la mappa, la seduta, i prezzi"
DESCR_3 = ("Cos'è la riflessologia plantare, come si legge la mappa del piede, come si svolge "
           "una seduta, cosa dice la ricerca, controindicazioni e prezzi in Italia.")
IN_BREVE_3 = ("La riflessologia plantare lavora con pressioni sul piede secondo una mappa che "
              "associa zone del piede a parti del corpo. La ricerca la sostiene come pratica di "
              "rilassamento e riduzione dello stress, non come diagnosi o cura. Una seduta dura "
              "45-60 minuti e costa fra 40 e 70 euro. Non si fa con trombosi, ferite o infezioni "
              "al piede, e in gravidanza si sceglie chi ha esperienza.")
CONTENUTO_3 = """\
«Riflessologia plantare mappa» è una delle ricerche più frequenti fra le pratiche sul corpo, e non a caso: la mappa del piede è la cosa che incuriosisce di più e che si capisce meno. Questa guida spiega cos'è la riflessologia, come si legge la mappa, cosa succede in una seduta, cosa ne dice la ricerca, quando non farla e quanto costa. Per chi invece cerca una panoramica del lavoro sul corpo, la [guida al massaggio olistico](/blog/""" + MASSAGGIO + """) confronta nove tecniche.

## Cos'è

La riflessologia plantare è una pratica manuale che applica pressioni con i pollici e le dita su punti e zone del piede. L'idea di fondo, formalizzata negli anni Trenta dalla fisioterapista americana Eunice Ingham a partire dalla «terapia zonale» del medico William Fitzgerald, è che il piede sia una mappa del corpo: ogni zona corrisponderebbe a un organo o a una parte, e la pressione su quella zona avrebbe un effetto a distanza.

È importante dirlo subito: questa corrispondenza non è mai stata dimostrata. Non esiste un collegamento anatomico o nervoso noto fra, per esempio, l'arco del piede e l'intestino. Quello che invece esiste, ed è documentato, è l'effetto della pressione sul piede sul sistema nervoso: rilassamento, riduzione della percezione dello stress, in alcuni studi riduzione dell'ansia e del dolore percepito. Chi la pratica seriamente lo sa e lo dice.

## La mappa del piede, in breve

La mappa tradizionale divide il piede così, con differenze fra scuole:

- **Le dita** corrispondono alla testa e al collo: l'alluce alla testa e al cervello, le altre dita a occhi, orecchie, seni paranasali.
- **La zona sotto le dita** (i cuscinetti) al torace: polmoni, cuore (sul piede sinistro), spalle verso il bordo esterno.
- **L'arco** agli organi dell'addome: stomaco, fegato (destra), milza (sinistra), pancreas, intestino verso il tallone.
- **Il tallone** al bacino, alla zona lombare e agli organi pelvici.
- **Il bordo interno del piede**, dall'alluce al tallone, alla colonna vertebrale, dalle cervicali al sacro.
- **Il bordo esterno** ad anca, ginocchio, gomito, spalla.

Il piede destro rappresenta la metà destra del corpo, il sinistro la metà sinistra. Chi conduce la seduta usa la mappa come guida per il lavoro e come linguaggio con la persona («qui sento tensione»), non come strumento diagnostico. Se qualcuno pretende di diagnosticare una malattia dal piede, sta oltrepassando un confine, e la [legge 4/2013](/blog/""" + LEGGE + """) lo vieta.

## Come si svolge una seduta

Si resta vestiti, si tolgono scarpe e calze, ci si sdraia su un lettino o ci si siede su una poltrona reclinata. Una prima parte, di solito breve, serve a capire perché sei lì: stanchezza, tensione, difficoltà a dormire, o semplice curiosità. Poi la persona che conduce riscalda il piede con movimenti ampi e comincia il lavoro punto per punto, con una pressione decisa ma non dolorosa, alternando i due piedi. Alcune zone possono risultare sensibili; un buon operatore chiede sempre se la pressione va bene.

La durata tipica è di **45-60 minuti**. Molti si addormentano; è normale. Alla fine si beve acqua e ci si alza con calma. Gli effetti raccontati più spesso: piedi leggeri, sonno migliore quella notte, una sensazione di calma che dura qualche ora. Le persone che hanno un obiettivo (per esempio, un periodo di stress) fanno di solito un ciclo di 4-6 sedute settimanali, poi una al mese.

## Cosa dice la ricerca

Le revisioni sistematiche degli ultimi quindici anni concordano su tre punti. Primo: la riflessologia produce **rilassamento e riduzione dell'ansia e dello stress percepito**, con risultati coerenti in contesti come l'oncologia di supporto e le cure palliative, dove viene usata per il benessere delle persone, non per la malattia. Secondo: **non ci sono prove** che agisca su organi specifici o che possa diagnosticare qualcosa. Terzo: gli studi sono spesso piccoli e di qualità variabile, per cui gli effetti sul dolore e sul sonno sono promettenti ma non solidi.

È una pratica di benessere, e va scelta come tale. Se qualcosa non va nel corpo, la prima tappa è il medico; la riflessologia può accompagnare, non sostituire.

## Quando non farla

- **Trombosi venosa o sospetto di trombosi** alle gambe: pressione controindicata.
- **Ferite, infezioni, micosi, verruche** al piede: si aspetta la guarigione.
- **Fratture recenti o interventi** al piede o alla caviglia.
- **Gravidanza**: non è vietata, ma nel primo trimestre molti operatori preferiscono evitare e in ogni caso serve chi ha formazione specifica; si dice sempre di essere incinta.
- **Diabete con neuropatia**, disturbi della circolazione, patologie in fase acuta: si chiede prima al medico.

## Quanto costa

In Italia una seduta di riflessologia plantare costa in genere **fra 40 e 70 euro**, con le grandi città nella parte alta e la provincia in quella bassa; i cicli di cinque o sei sedute hanno spesso uno sconto. I prezzi dei singoli operatori della rete sono nel loro listino, sul profilo. Per un confronto con le altre pratiche, [quanto costano le pratiche olistiche, una per una](/blog/""" + COSTI + """).

## Come scegliere chi la pratica

Chiedi dove si è formato e da quanto la pratica; diffida di chi promette di «curare» qualcosa; preferisci chi al primo incontro fa domande sulla tua salute e ti dice quando la riflessologia non è indicata. Sono i segni di serietà che valgono per ogni pratica, e li abbiamo raccolti in [come capire se un operatore olistico è serio](/blog/""" + SERIO + """) e nel [primo colloquio](/blog/""" + COLLOQUIO + """). Chi la pratica nella rete Aurya lo trovi nella pagina della disciplina: [riflessologia](/operatori/riflessologia), con sedi, listino e recensioni verificate; per il lavoro sul corpo a piede vestito, lo [shiatsu](/blog/""" + SHIATSU + """) è la pratica cugina.

## Domande frequenti

**La riflessologia plantare fa male?**
No. La pressione è decisa e alcune zone possono risultare sensibili, ma non deve essere dolorosa: se lo è, si dice, e chi conduce alleggerisce.

**Quante sedute servono?**
Per il rilassamento anche una sola. Chi ha un obiettivo, come un periodo di stress o difficoltà a dormire, fa di solito un ciclo di 4-6 sedute settimanali, poi una al mese.

**La riflessologia può diagnosticare una malattia?**
No. Non esistono prove che dal piede si possano leggere malattie, e chi lo sostiene oltrepassa quello che la legge consente a una pratica non sanitaria.

**Si può fare in gravidanza?**
Con cautela e con chi ha formazione specifica; nel primo trimestre molti operatori preferiscono evitare. Si dice sempre di essere incinta.

**Quanto costa una seduta?**
Fra 40 e 70 euro in Italia, 45-60 minuti. I cicli hanno spesso uno sconto.

**Che differenza c'è con il massaggio ai piedi?**
Il massaggio lavora sui muscoli e sulla circolazione con movimenti ampi; la riflessologia lavora per punti secondo la mappa, con pressioni statiche. Spesso una seduta li combina.
"""

# ── 4. Welfare aziendale 2026 ────────────────────────────────────────

SLUG_4 = "welfare-aziendale-2026-esempi-deducibilita-benessere"
TITOLO_4 = "Welfare aziendale 2026: esempi, deducibilità e benessere"
DESCR_4 = ("Cos'è il welfare aziendale, le soglie 2026 dei fringe benefit, quando è deducibile "
           "al 100%, gli esempi che funzionano e dove entra il benessere.")
IN_BREVE_4 = ("Il welfare aziendale è l'insieme di beni e servizi che l'azienda dà ai dipendenti "
              "fuori dalla busta paga, con un trattamento fiscale favorevole se rispetta le regole "
              "dell'articolo 51 del TUIR. Nel 2026 le soglie dei fringe benefit sono 1.000 euro, "
              "2.000 con figli a carico. Il benessere psicofisico, dallo yoga in azienda ai percorsi "
              "contro lo stress, rientra fra i servizi ammessi e si deduce al 100% se previsto da "
              "un regolamento o un accordo. Le cifre vanno verificate con il consulente: qui c'è la "
              "mappa.")
CONTENUTO_4 = """\
«Welfare aziendale» è una delle ricerche più frequenti fra chi gestisce persone in azienda, e la maggior parte delle risposte arriva dai fornitori di piattaforme. Questa guida spiega cos'è, come funziona il fisco nel 2026, quali esempi funzionano davvero e come far entrare il benessere delle persone, che è la parte in cui Aurya lavora. Le regole fiscali cambiano spesso: le cifre qui sotto sono quelle in vigore mentre scriviamo e vanno verificate con il consulente del lavoro o il commercialista prima di decidere.

## Cos'è il welfare aziendale

È l'insieme di beni, servizi e somme che l'azienda riconosce ai dipendenti **oltre la retribuzione**, con un trattamento fiscale e contributivo favorevole se rispetta le condizioni dell'articolo 51 del Testo unico delle imposte sui redditi. Rientrano, per esempio, i buoni pasto entro le soglie, i rimborsi per l'istruzione dei figli, i servizi di assistenza per anziani, l'abbonamento al trasporto pubblico, le opere e i servizi con finalità di educazione, ricreazione, assistenza sociale e sanitaria, e i cosiddetti fringe benefit, cioè beni e servizi in natura fino a una soglia annua.

Il welfare può essere **contrattuale** (previsto dal contratto collettivo o da un accordo aziendale), **regolamentare** (introdotto con un regolamento aziendale che l'azienda si impegna a rispettare) o **volontario** (deciso di volta in volta). La distinzione conta per la deducibilità, più avanti.

## Le cifre 2026 da sapere

- **Fringe benefit**: la soglia di esenzione ordinaria era di 258,23 euro. La legge di bilancio 2025 ha fissato per gli anni **2025, 2026 e 2027** una soglia di **1.000 euro**, che sale a **2.000 euro** per chi ha figli fiscalmente a carico. Sotto la soglia il valore non fa reddito; sopra, l'intero importo diventa imponibile. Nella soglia rientrano anche i rimborsi delle utenze domestiche, dell'affitto e degli interessi sul mutuo della prima casa, alle condizioni di legge.
- **Premio di risultato convertito in welfare**: quando il contratto lo prevede, il dipendente può scegliere di ricevere il premio sotto forma di servizi di welfare, e in quel caso non paga imposte sull'importo convertito, entro i limiti di legge.
- **Deducibilità per l'azienda**: le spese per opere e servizi di educazione, ricreazione, assistenza sociale e sanitaria sono deducibili **al 100%** se derivano da contratto, accordo o regolamento aziendale; se sono decise volontariamente, la deducibilità è limitata al **5 per mille** del costo del lavoro (articolo 100 del TUIR). È la ragione per cui quasi tutte le aziende adottano un regolamento.

## Esempi che funzionano

Le piattaforme di welfare offrono cataloghi di migliaia di voci; le aziende che ne traggono qualcosa sono quelle che scelgono poche cose e le fanno bene.

- **Salute e prevenzione**: check-up, polizze sanitarie integrative, campagne vaccinali. Sono la voce più usata e la più apprezzata nei sondaggi interni.
- **Conciliazione**: asili, campus estivi, rimborsi scolastici, assistenza a familiari non autosufficienti. Riducono le assenze più di qualunque premio.
- **Mobilità**: abbonamenti al trasporto pubblico, bici aziendali.
- **Benessere psicofisico**: percorsi di gestione dello stress, mindfulness, yoga in azienda, sportelli di ascolto psicologico, giornate del benessere. È la voce in più rapida crescita, ed è quella su cui si fa più confusione.
- **Tempo**: giorni in più, orari flessibili. Non passano dal fisco e sono spesso ciò che le persone chiedono per primo.

## Dove entra il benessere delle persone

Dal 2008 le aziende hanno l'obbligo di valutare il **rischio da stress lavoro-correlato** (decreto legislativo 81/2008). La valutazione è obbligatoria; cosa fare dopo, no. Ed è qui che il welfare del benessere diventa una risposta concreta e non un regalo.

Cosa funziona, per esperienza diretta di chi lo conduce e per quello che dicono gli studi sui programmi di mindfulness e di respiro in azienda:

- **Percorsi, non eventi isolati.** Una giornata del benessere fa piacere; otto settimane di pratica cambiano qualcosa. Il [protocollo MBSR](/blog/""" + MBSR + """) è il formato più studiato: otto incontri, pratica a casa, misure prima e dopo.
- **Pratiche brevi nell'orario di lavoro.** Dieci minuti di [respiro guidato](/blog/""" + RESPIRO + """) a inizio riunione, una pausa attiva a metà pomeriggio, la lezione di yoga alle 13. Quello che si fa fuori orario non lo fa nessuno.
- **Condotto da persone vere.** Un'app è un buon complemento; il cambiamento passa da qualcuno che entra in azienda, conosce le persone e torna. Su Aurya questo lavoro lo fanno i professionisti della rete: insegnanti di yoga, istruttori di mindfulness, operatori del respiro e del suono, con esperienza in gruppo.
- **Una misura semplice prima e dopo.** Un questionario di dieci domande sul carico percepito, ripetuto dopo tre mesi. Non serve la ricerca scientifica: serve sapere se è servito.
- **Il team building come porta.** Una giornata fuori sede con yoga, respiro, un bagno di suono e un cammino in natura è il modo più semplice per far provare a un gruppo cose che poi chiede di continuare. Ne parliamo nella pagina [Aurya per le aziende](/aziende).

Quello che non funziona: il corso di mindfulness usato per far tollerare carichi di lavoro che andrebbero cambiati. Chi lo propone seriamente lo dice prima, e su questo la critica interna al mondo della mindfulness è chiara. Un programma di benessere non sostituisce un'organizzazione sana; la rende possibile. Per una panoramica delle pratiche con evidenza sullo stress, [cosa funziona](/blog/""" + STRESS + """).

## Come partire, in pratica

1. **Leggi la valutazione dello stress** che l'azienda ha già fatto: dice dove sono i problemi.
2. **Scegli un gruppo pilota** di 15-25 persone e un percorso di otto settimane, con una misura prima e dopo.
3. **Metti il benessere nel regolamento aziendale** per la deducibilità piena, con il consulente.
4. **Misura e racconta** i risultati alle persone prima che alla direzione.
5. **Solo dopo, allarga**: catalogo, piattaforma, voci in più.

I costi: una lezione di gruppo in azienda costa fra 80 e 150 euro, un percorso di otto settimane per un gruppo fra 1.500 e 4.000 euro, una giornata di team building di benessere fuori sede fra 80 e 200 euro a persona, vitto e struttura compresi. Sono fasce indicative del mercato italiano; i preventivi si fanno sul gruppo, sul luogo e sulla durata. Per un progetto con la rete Aurya il primo passo è il [modulo per le aziende](/aziende): rispondiamo entro due giorni lavorativi.

## Domande frequenti

**Cos'è il welfare aziendale, in una frase?**
Beni, servizi e somme che l'azienda riconosce ai dipendenti oltre lo stipendio, con un regime fiscale agevolato se rispettano l'articolo 51 del TUIR.

**Qual è la soglia dei fringe benefit nel 2026?**
1.000 euro all'anno, 2.000 per chi ha figli fiscalmente a carico, per gli anni 2025-2027 secondo la legge di bilancio 2025. Sopra la soglia tutto l'importo diventa imponibile. Da verificare con il consulente, perché le regole cambiano.

**Il welfare è deducibile per l'azienda?**
Al 100% se previsto da contratto, accordo o regolamento aziendale; al 5 per mille del costo del lavoro se volontario (articolo 100 del TUIR).

**Lo yoga in azienda rientra nel welfare?**
Sì, fra le opere e i servizi con finalità di educazione, ricreazione e assistenza sociale, se offerto alla generalità o a categorie di dipendenti. Anche i percorsi di gestione dello stress. Il modo in cui si struttura l'offerta va concordato con il consulente.

**Meglio una piattaforma o un percorso condotto da persone?**
Non si escludono. La piattaforma copre le voci a catalogo; il benessere psicofisico dà risultati quando qualcuno entra in azienda e torna. Le aziende che partono da un pilota di otto settimane sanno cosa comprare dopo.

**Un team building di benessere è welfare?**
Il team building è di norma un costo di gestione, non welfare per il dipendente. Può essere la porta per un percorso di benessere che poi rientra nel regolamento. Anche qui: consulente.
"""

# ── 5. Yoga e ritiri in Toscana ──────────────────────────────────────

SLUG_5 = "yoga-e-ritiri-in-toscana-guida"
TITOLO_5 = "Yoga e ritiri in Toscana: dove, quando, quanto costa"
DESCR_5 = ("Ritiri di yoga e benessere in Toscana: le zone, le stagioni, i formati, i prezzi "
           "veri e come scegliere. E come farsi avvisare quando se ne apre uno.")
IN_BREVE_5 = ("La Toscana è la regione più cercata in Italia per i ritiri di yoga: colline, casali, "
              "silenzio e distanze brevi. Le stagioni migliori sono aprile-giugno e settembre-ottobre. "
              "Un weekend costa fra 250 e 500 euro, una settimana fra 900 e 1.800, quasi sempre con "
              "vitto e alloggio. Dove si va, cosa aspettarsi, e come farsi avvisare quando un ritiro "
              "in Toscana apre le iscrizioni.")
CONTENUTO_5 = """\
«Ritiro yoga Toscana» è, fra tutte le regioni, la ricerca più frequente in Italia, con «Toscana yoga retreat» subito dietro per chi cerca in inglese. Il motivo è semplice: colline, casali con vista, silenzio a mezz'ora dalle città, e la distanza giusta da Firenze, Roma, Bologna e Milano per un weekend. Questa guida spiega dove si va, quando, quanto si spende e come scegliere. In fondo, il modo per farsi avvisare quando un ritiro in Toscana apre le iscrizioni.

## Le zone

- **Chianti e Val d'Elsa**: fra Firenze e Siena, la Toscana dei casali fra le vigne. La più servita e la più cara; ideale per il primo ritiro e per chi arriva in treno (Firenze, Siena, Poggibonsi).
- **Val d'Orcia e Amiata**: le colline del sud, il paesaggio da cartolina, i borghi di Pienza e Montalcino, le terme di Bagno Vignoni e San Filippo. Il monte Amiata porta bosco e fresco d'estate: molti ritiri di silenzio stanno qui.
- **Maremma**: la costa selvaggia (Argentario, parco dell'Uccellina) e l'interno di Pitigliano e Sorano. Più lontana, più mare, spesso più economica.
- **Casentino e Mugello**: la Toscana dei boschi e degli eremi, a nord-est di Firenze. Le foreste del Casentino ospitano da secoli luoghi di ritiro spirituale, e oggi anche ritiri laici di meditazione e cammino; [i bagni di foresta](/blog/""" + CAMMINI + """) qui hanno casa.
- **Garfagnana e Lunigiana**: montagna vera, le Apuane, pochi turisti. Per chi vuole camminare.
- **Elba e la costa**: ritiri di yoga e mare, fra maggio e settembre.

## Le stagioni

La Toscana si riempie ad agosto e le ricerche lo confermano («ritiro yoga agosto 2026» è la più frequente), ma i mesi migliori sono altri: **aprile-giugno** e **settembre-ottobre**, con temperature da praticare all'aperto, luce lunga e prezzi più bassi. I ponti di primavera (25 aprile, 1 maggio) e l'inizio dell'autunno sono i momenti in cui aprono più ritiri brevi. In inverno restano i ritiri di silenzio e i weekend con le terme; a Capodanno alcuni ritiri residenziali vanno esauriti già a novembre.

## I formati

- **Il weekend** (venerdì sera-domenica pomeriggio): due o tre pratiche al giorno, pasti insieme, tempo libero il sabato pomeriggio. È il formato per chi comincia. Prezzo: **250-500 euro** con vitto e alloggio.
- **La settimana** (5-7 notti): il formato classico dei ritiri estivi, con più profondità e più stanchezza. **900-1.800 euro** tutto compreso; oltre, si paga il lusso della struttura, non lo yoga.
- **Il ritiro di silenzio o di meditazione** (3-10 giorni): meno yoga, più seduta e cammino, regole precise (niente telefono, spesso niente parola). Esistono formati a donazione, soprattutto nella tradizione vipassana; per il resto le fasce sono simili alla settimana.
- **La giornata**: una domenica di pratica e pranzo in un casale, **60-120 euro**. È il modo per provare un insegnante prima di seguirlo per una settimana.

Il prezzo dipende da tre cose: la struttura (agriturismo, casale privato, centro con sale attrezzate), il numero di partecipanti (sotto le dieci persone il prezzo sale) e chi conduce. Chi organizza i ritiri conosce bene questa matematica: ne abbiamo scritto dal loro lato in [come calcolare il prezzo di un ritiro](/blog/""" + PREZZO_RIT + """), e leggerla aiuta anche chi partecipa a capire cosa sta pagando.

## Cosa aspettarsi da un ritiro in Toscana

Una giornata tipo: sveglia presto, pratica all'alba o prima della colazione, colazione lenta, una seconda pratica o un laboratorio in tarda mattinata, pranzo, pomeriggio libero o cammino, pratica dolce o meditazione al tramonto, cena, a volte un cerchio o una serata di suono. I pasti sono quasi sempre vegetariani e cucinati sul posto; molti ritiri in Toscana fanno della cucina una parte dell'esperienza.

Il tipo di yoga cambia tutto: un ritiro di ashtanga alle sei del mattino e uno di yin al tramonto sono due vacanze diverse. Prima di prenotare, [le differenze fra gli stili](/blog/""" + TIPI_YOGA + """) e la nostra guida su [come scegliere un ritiro](/blog/""" + SCEGLI_RIT + """): tipo, durata e budget. Le [domande da fare prima di prenotare](/blog/""" + DOMANDE + """) evitano le brutte sorprese, e [cosa portare](/blog/""" + PORTARE + """) chiude la lista.

## Come arrivare

La Toscana dei ritiri è quella senza treno. Firenze, Siena, Arezzo, Grosseto e Pisa sono le stazioni di riferimento; da lì quasi tutti i ritiri organizzano un passaggio dalla stazione a un'ora fissa, o consigliano il noleggio. Chiedere come si arriva è la prima domanda utile, e la risposta dice molto sull'organizzazione.

## Chi conduce, e come farsi avvisare

I ritiri in Toscana li conducono insegnanti che spesso vivono altrove e affittano la struttura per la settimana: il modo migliore per sceglierne uno è conoscere l'insegnante prima. Nella rete Aurya trovi i profili degli [insegnanti di yoga](/operatori/yoga) con sedi, listino e recensioni verificate; quando uno di loro apre un ritiro, compare nel suo profilo e nel [calendario delle esperienze](/esperienze).

Ma un ritiro in Toscana si riempie in fretta, e chi lo cerca a luglio per agosto arriva tardi. Per questo esiste il Cerchio: dici che tipo di ritiro cerchi e dove, e **ti avvisiamo noi quando se ne apre uno** che corrisponde, prima che vada esaurito. Ci si iscrive in un minuto, gratis, da [qui](/cerca-ritiro); intanto ricevi le meditazioni riservate.

## Domande frequenti

**Quanto costa un ritiro di yoga in Toscana?**
Un weekend fra 250 e 500 euro, una settimana fra 900 e 1.800, di solito con vitto e alloggio. Una giornata singola 60-120 euro. Sopra queste cifre si paga la struttura, non la pratica.

**Qual è il periodo migliore?**
Aprile-giugno e settembre-ottobre: si pratica all'aperto, c'è meno gente e i prezzi sono più bassi. Agosto è il mese più richiesto e il più caro.

**Serve esperienza per partecipare?**
Per i ritiri di hatha, yin e la maggior parte dei weekend no. Per ashtanga, kundalini o i ritiri di silenzio lunghi conviene avere una pratica regolare. Il programma lo dice sempre; se non lo dice, si chiede.

**Si può andare da soli?**
Sì, ed è la norma: la maggior parte delle persone arriva sola e i ritiri sono pensati per questo. Le camere singole costano di più e finiscono prima.

**Come arrivo senza auto?**
Con il treno fino a Firenze, Siena, Arezzo, Grosseto o Pisa e il passaggio organizzato dal ritiro. Chiederlo prima di prenotare.

**Come faccio a sapere quando apre un ritiro in Toscana?**
Iscrivendoti al Cerchio di Aurya con le tue preferenze: ti scriviamo quando un ritiro che corrisponde apre le iscrizioni, prima che vada esaurito.
"""

PEZZI = [
    (SLUG_1, TITOLO_1, DESCR_1, IN_BREVE_1, CONTENUTO_1, "meditazione", [MEDIT, NIDRA, KIT]),
    (SLUG_2, TITOLO_2, DESCR_2, IN_BREVE_2, CONTENUTO_2, "operatori", [PIVA, ATECO, RC]),
    (SLUG_3, TITOLO_3, DESCR_3, IN_BREVE_3, CONTENUTO_3, "massaggio", [MASSAGGIO, SHIATSU, COSTI]),
    (SLUG_4, TITOLO_4, DESCR_4, IN_BREVE_4, CONTENUTO_4, "aziendale", [MBSR, STRESS, RESPIRO]),
    (SLUG_5, TITOLO_5, DESCR_5, IN_BREVE_5, CONTENUTO_5, "ritiri", [SCEGLI_RIT, DOMANDE, PORTARE]),
]

# i link di ritorno dagli articoli esistenti (niente vicoli ciechi)
AGGIUNTE = [
    (MEDIT, "## Domande frequenti",
     "Se il momento difficile è la sera, abbiamo scritto una [pratica di dieci minuti per "
     "dormire](/blog/" + SLUG_1 + "), con le tracce da ascoltare.\n\n## Domande frequenti"),
    (NIDRA, "## Domande frequenti",
     "Il body scan dello yoga nidra è anche il cuore della nostra [meditazione guidata per "
     "dormire in dieci minuti](/blog/" + SLUG_1 + ").\n\n## Domande frequenti"),
    (SCEGLI_INS, "## Domande frequenti",
     "Se invece l'insegnante vuoi diventarlo tu, [come valutare un corso da 200 ore e cosa "
     "serve dopo](/blog/" + SLUG_2 + ").\n\n## Domande frequenti"),
    (PIVA, "## Domande frequenti",
     "Chi sta scegliendo la formazione trova in [corso di yoga 200 ore: come valutarlo](/blog/"
     + SLUG_2 + ") la parte che le scuole non raccontano.\n\n## Domande frequenti"),
    (MASSAGGIO, "## Domande frequenti",
     "Della riflessologia plantare, la mappa del piede e la seduta, abbiamo scritto [una guida "
     "a parte](/blog/" + SLUG_3 + ").\n\n## Domande frequenti"),
    (COSTI, "## Domande frequenti",
     "Per la riflessologia plantare, i prezzi e cosa comprendono: [la guida](/blog/" + SLUG_3
     + ").\n\n## Domande frequenti"),
    (STRESS, "## Domande frequenti",
     "In azienda queste pratiche entrano dal welfare: [come funziona nel 2026, esempi e "
     "deducibilità](/blog/" + SLUG_4 + ").\n\n## Domande frequenti"),
    (MBSR, "## Domande frequenti",
     "Il protocollo in azienda: [welfare aziendale 2026 e benessere delle persone](/blog/"
     + SLUG_4 + ").\n\n## Domande frequenti"),
    (SCEGLI_RIT, "## Domande frequenti",
     "Per la regione più cercata d'Italia, [yoga e ritiri in Toscana: dove, quando, quanto "
     "costa](/blog/" + SLUG_5 + ").\n\n## Domande frequenti"),
    (DOMANDE, "## Domande frequenti",
     "Se il ritiro è in Toscana, [la guida alle zone, alle stagioni e ai prezzi](/blog/"
     + SLUG_5 + ").\n\n## Domande frequenti"),
]


async def main(dry_run: bool, ping: bool) -> None:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from database import db

    for slug, titolo, descr, in_breve, contenuto, categoria, correlati in PEZZI:
        faq = len(re.findall(r"^\*\*[^*]+\?\*\*$", contenuto, re.M))
        print(f"{titolo}\n  slug: {slug} | categoria: {categoria} | parole: {len(contenuto.split())}"
              f" | descrizione: {len(descr)} car. | FAQ: {faq} | in breve: {len(in_breve)} car.")
        assert len(descr) <= 165 and faq >= 4 and len(titolo) <= 62, "fuori misura"
        esistente = await db.articles.find_one({"slug": slug}, {"_id": 0, "id": 1})
        print("  stato:", "aggiornato" if esistente else "nuovo")
        if dry_run:
            continue
        now = datetime.now(timezone.utc)
        campi = {"title": titolo, "description": descr, "in_breve": in_breve,
                 "content": contenuto, "category": categoria, "author_name": "Aurya",
                 "access": "public", "published": True, "updated_at": now,
                 "translations": {}, "related_slugs": correlati}
        if not esistente:
            campi |= {"id": str(uuid.uuid4()), "slug": slug, "created_at": now, "published_at": now}
        await db.articles.update_one({"slug": slug}, {"$set": campi}, upsert=True)
        doc = await db.articles.find_one({"slug": slug}, {"_id": 0, "featured_image_url": 1})
        if not doc.get("featured_image_url"):
            from routers.articles import _autogen_cover
            url = await _autogen_cover(slug, categoria)
            if url:
                await db.articles.update_one({"slug": slug}, {"$set": {"featured_image_url": url}})
                print(f"  copertina: {url}")

    if not dry_run:
        for slug, vecchio, nuovo in AGGIUNTE:
            d = await db.articles.find_one({"slug": slug}, {"_id": 0, "content": 1})
            if not d:
                print(f"  ASSENTE {slug}")
            elif nuovo.split("\n\n")[0] in d["content"]:
                print(f"  link gia' presente in {slug[:42]}")
            elif vecchio in d["content"]:
                await db.articles.update_one({"slug": slug}, {"$set": {
                    "content": d["content"].replace(vecchio, nuovo, 1),
                    "updated_at": datetime.now(timezone.utc)}})
                print(f"  link aggiunto in {slug[:42]}")
            else:
                print(f"  NON TROVATO in {slug[:42]}")

    print("\n── controlli")
    arts = [a async for a in db.articles.find({"published": True}, {"_id": 0, "slug": 1, "content": 1,
                                                                    "featured_image_url": 1})]
    slugs = {a["slug"] for a in arts}
    rotti = [(a["slug"], l) for a in arts
             for l in re.findall(r"\]\(/blog/([a-z0-9-]+)\)", a["content"]) if l not in slugs]
    nuovi = {p[0] for p in PEZZI}
    orfani = [s for s in nuovi if s in slugs and not any(
        f"/blog/{s})" in b["content"] for b in arts if b["slug"] != s)]
    tic = re.compile(r"(con onest|onestà:|la parte onesta|senza misteri|dalla nostra esperienza)", re.I)
    print(f"  link rotti: {rotti or 'nessuno'}")
    print(f"  nuovi senza link in entrata: {orfani or 'nessuno'}")
    print(f"  tic: {sum(len(tic.findall(a['content'])) for a in arts)}")
    print(f"  TOTALE: {len(arts)} articoli, {sum(len(a['content'].split()) for a in arts)} parole")

    if ping and not dry_run:
        try:
            from services.indexnow import ping_urls_async
            await ping_urls_async([f"/blog/{p[0]}" for p in PEZZI] + ["/blog"])
            print("  IndexNow: ping inviato")
        except Exception as e:      # noqa: BLE001
            print("  IndexNow non inviato:", e)
    if dry_run:
        print("\n--dry-run: nessuna scrittura")


if __name__ == "__main__":
    asyncio.run(main("--dry-run" in sys.argv, "--ping" in sys.argv))
