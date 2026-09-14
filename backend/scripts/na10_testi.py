"""NA10 — i testi dei cinque articoli, in forma narrativa (riscritti la notte
del 14/9 dopo il feedback del founder: «voglio storytelling, stile umano,
non linguaggio tecnico o frasi troppo corte a punti; devi raccontare bene»).
Lo script na10_cinque_articoli_seo.py li importa e li pubblica."""

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


def _b(slug: str) -> str:
    return "/blog/" + slug


# ── 1. Meditazione guidata per dormire ──────────────────────────────

SLUG_1 = "meditazione-guidata-per-dormire-10-minuti"
TITOLO_1 = "Meditazione guidata per dormire: la pratica di 10 minuti"
DESCR_1 = ("Una pratica di dieci minuti da fare a letto, raccontata passo per passo: perché "
           "funziona, cosa tiene svegli, e le tracce di Aurya da ascoltare.")
IN_BREVE_1 = ("Se la sera la testa riparte appena spegni la luce, non è un difetto tuo: è il sistema "
              "nervoso che non ha ancora ricevuto il segnale. Una pratica di dieci minuti, fatta ogni "
              "sera nello stesso modo, glielo dà: sposta l'attenzione dal pensare al sentire, e il "
              "corpo fa il resto. Qui la trovi scritta passo per passo, con le tracce di Aurya da "
              "ascoltare e i casi in cui, invece di una traccia, serve un medico.")
CONTENUTO_1 = f"""\
C'è un momento preciso, la sera, in cui tutto quello che di giorno non ha trovato spazio si presenta insieme. Hai spento la luce, il telefono è a faccia in giù sul comodino come ti hanno detto di fare, la stanza è buia. E la testa riparte: la cosa detta male in riunione, il messaggio a cui non hai risposto, l'appuntamento di domani. Più cerchi di fermarla, più corre. Se ti riconosci, sappi che una meditazione per dormire funziona proprio perché non ti chiede di fermare i pensieri, cosa che nessuno sa fare a comando. Ti chiede una cosa più piccola e molto più facile: spostare l'attenzione dalla testa al corpo, dove non c'è niente da risolvere.

In questa guida trovi la pratica scritta passo per passo, così la prima sera puoi seguirla da sola o da solo, e dalla seconda lasciare che ti guidi una voce. In fondo ci sono le tracce sonore di Aurya e le risposte alle domande che ci fanno più spesso.

## Perché funziona

Il sonno non si comanda. Arriva quando il sistema nervoso passa dalla modalità in cui sta di giorno, quella dell'allerta e del fare, alla modalità del riposo, e il passaggio non lo decide la volontà ma il corpo. Le pratiche che portano l'attenzione sul respiro e sulle sensazioni fisiche abbassano l'attivazione, e non è una suggestione: nel 2015 uno studio randomizzato pubblicato su *JAMA Internal Medicine* ha seguito adulti con disturbi del sonno moderati e ha visto che un programma di consapevolezza migliorava la qualità del sonno più di un corso classico di igiene del sonno, quello delle regole su caffè e schermi. Il respiro lento fa la sua parte: sotto i sei atti al minuto aumenta l'attività del nervo vago, che è il freno del sistema nervoso. Ne abbiamo scritto in [respiro e sistema nervoso]({_b(RESPIRO)}), se vuoi capire cosa succede dentro.

Detto questo, una meditazione non è una medicina e non sostituisce le cure. Se il sonno è un problema da mesi, più avanti ti diciamo quando è il momento di parlarne con qualcuno.

## La pratica, dieci minuti

Si fa a letto, a luci spente, nella posizione in cui dormi. Non serve altro.

Nel primo minuto ti limiti ad arrivare. Ti sdrai come per dormire e senti il peso del corpo sul materasso: la testa che affonda nel cuscino, le spalle, la schiena, le gambe. Non cambi niente, noti soltanto dove il corpo appoggia, ed è già un modo di dire alla testa che per stasera il lavoro è finito.

Nei due minuti seguenti porti l'attenzione al respiro, ma senza guidarlo. Lo cerchi dove lo senti meglio, che per qualcuno sono le narici, per altri il petto, per molti la pancia. Non lo allunghi, non lo controlli. Conti tre respiri e ricominci da uno. Perderai il conto, perché la mente tornerà ai suoi pensieri, e va bene così: accorgersi di aver perso il conto e tornare al respiro è tutta la pratica.

Poi, dal quarto minuto, cominci un viaggio lento dai piedi alla testa. Le dita dei piedi, le piante, le caviglie; i polpacci, le ginocchia, le cosce. Ogni zona la senti per un paio di respiri e poi la lasci andare, come se la stessi salutando. Sali al bacino, alla pancia, al petto; alle mani, alle braccia, alle spalle. Al collo, e alla mandibola, che quasi sempre scopri stretta e puoi lasciar cadere. Gli occhi, la fronte. Questo giro del corpo si chiama *body scan* ed è la tecnica su cui è costruito lo [yoga nidra]({_b(NIDRA)}), il rilassamento profondo dello yoga: se ti piace, lì trovi la versione lunga.

Verso il settimo minuto, e non prima, rendi l'espirazione un po' più lunga dell'inspirazione. C'è un ritmo che quasi tutti trovano naturale, inspirare contando fino a quattro ed espirare contando fino a sei, ma se contare ti tiene sveglio smetti di contare e senti soltanto che l'aria esce più a lungo di quanto entra.

Gli ultimi due minuti sono i più semplici e i più difficili: smetti di fare qualsiasi cosa. Non c'è più niente da seguire. Se arriva un pensiero lo guardi passare, come una macchina che passa sotto la finestra e si allontana. Se ti addormenti prima della fine, hai fatto tutto giusto.

## Quello che tiene svegli

Quasi tutti, le prime sere, fanno lo stesso errore: cercano di addormentarsi. È l'unico sforzo che produce il risultato contrario, perché cercare è un'attività e il sonno è il suo opposto. L'obiettivo della pratica è sentire il corpo; il sonno arriva di conseguenza, e quando non arriva non è un fallimento.

Il secondo errore è cambiare pratica ogni sera, perché il sonno ama la ripetizione e la testa impara in fretta che a quel giro del corpo segue il riposo. Dalle la stessa pratica alla stessa ora per almeno due settimane, prima di giudicare. Il terzo è lo schermo: se ascolti una traccia, il telefono resta a faccia in giù e l'audio parte con lo schermo che si spegne da solo.

E poi c'è la notte in cui non funziona. Gli specialisti del sonno hanno una regola che sembra dura e invece libera: se dopo venti minuti sei ancora sveglio, ti alzi, fai qualcosa di noioso a luce bassa e torni a letto quando torna la sonnolenza. Restare a lottare insegna al cervello che il letto è il posto in cui si lotta, ed è l'ultima cosa che vuoi insegnargli.

## Le tracce da ascoltare

Seguire una voce o un suono toglie l'ultimo compito che ti resta, quello di ricordarti i passaggi. Le [meditazioni di Aurya](/meditazioni) sono sessioni sonore composte dai professionisti della rete, alcune pensate proprio per dormire; l'ascolto è riservato a chi fa parte del Cerchio, ci si iscrive in un minuto ed è gratis, e quando esce una traccia nuova la ricevi. Fra quelle pubbliche c'è [Mondo Nuovo, onde delta](/frequenze/meditazione-mondo-nuovo-onde-delta), ventisette minuti composti da Aurya per accompagnare tutto il passaggio verso il sonno. Se invece vuoi solo l'esercizio del respiro lungo fatto da un suono, [Respiro](/sound/respiro) sono dieci minuti gratuiti, senza registrarsi, a sei atti al minuto; e [Calm](/sound/calm) sono sei minuti costruiti per creare uno spazio di quiete, che come tutto quello che pubblichiamo su Aurya Sound non promette effetti e non è una terapia.

Per le pratiche brevi di giorno, quelle che preparano la sera, nel [kit delle sette pratiche da quindici minuti]({_b(KIT)}) ce ne sono due pensate per la fine della giornata.

## Quando una traccia non basta

Una meditazione aiuta il sonno disturbato dallo stress, dai pensieri, dalle giornate troppo piene: quello che ha portato quasi tutti noi a leggere una pagina come questa. Non cura l'insonnia cronica, che gli specialisti definiscono come la difficoltà a dormire per almeno tre notti a settimana da almeno tre mesi, con conseguenze di giorno. In quel caso esiste un trattamento di prima scelta, la terapia cognitivo-comportamentale per l'insonnia, e il primo passo è il medico di base. Vale anche se russi forte con pause del respiro, se ti addormenti di giorno senza volerlo, o se il sonno è cambiato insieme all'umore: sono segnali che una traccia non deve coprire.

Se la meditazione ti incuriosisce oltre la sera, la [guida semplice per chi inizia]({_b(MEDIT)}) racconta postura, durata e cosa aspettarsi; e per il respiro ci sono le [tecniche del pranayama]({_b(PRANA)}).

## Domande frequenti

**Quanto deve durare una meditazione per dormire?**
Dieci minuti bastano, se diventano un'abitudine. Le tracce più lunghe, come i ventisette minuti di Mondo Nuovo, servono a chi vuole essere accompagnato per tutto il passaggio al sonno: non sono più efficaci, sono più lunghe.

**Va bene addormentarsi prima della fine?**
È esattamente quello che cerchi. Se ascolti una traccia, imposta il telefono perché si spenga da solo, così non ti sveglia il silenzio.

**Meglio una voce o solo suoni?**
Le prime sere la voce aiuta a non perdere i passaggi. Con l'abitudine molte persone passano ai suoni senza parole, perché la voce comincia a risvegliare l'attenzione. Provale entrambe per una settimana e scegli.

**Funziona anche quando mi sveglio alle tre?**
Lo stesso giro del corpo, dal quarto minuto in poi, si fa anche al risveglio notturno. E vale la regola dei venti minuti: se il sonno non torna, ci si alza a luce bassa.

**È adatta ai bambini?**
Il giro del corpo si fa anche con i bambini dai sei anni, con parole semplici e più corto; con i più piccoli funziona meglio una storia letta a voce bassa.

**Quando devo parlarne con un medico?**
Quando la difficoltà dura da più di tre mesi, per tre notti a settimana o più; quando russi con pause del respiro; quando il sonno è peggiorato insieme all'umore. La meditazione può accompagnare una cura, non sostituirla.
"""

# ── 2. Corso di yoga 200 ore ─────────────────────────────────────────

SLUG_2 = "corso-yoga-200-ore-come-valutarlo-cosa-serve-dopo"
TITOLO_2 = "Corso di yoga 200 ore: come valutarlo e cosa serve dopo"
DESCR_2 = ("Cosa vale davvero un corso da 200 ore in Italia, come riconoscerne uno serio, "
           "quanto costa, e cosa serve per insegnare dopo: fisco, assicurazione, spazio, allievi.")
IN_BREVE_2 = ("In Italia nessun corso di yoga è riconosciuto dallo Stato: le duecento ore sono uno "
              "standard che il settore si è dato, non un titolo. Un corso serio lo riconosci dalle "
              "ore passate in sala, da chi insegna anatomia, dalle volte in cui insegni tu con qualcuno "
              "che ti corregge. E il diploma è l'inizio: la partita IVA, l'assicurazione, uno spazio "
              "e i primi allievi vengono dopo, ed è la parte di cui le scuole non parlano.")
CONTENUTO_2 = f"""\
Quasi tutte le persone che cercano «come diventare insegnante di yoga» arrivano alla domanda nello stesso modo. Praticano da qualche anno, hanno un'insegnante che ammirano, e a un certo punto in sala succede qualcosa: si accorgono di guardare gli altri più che sé, di capire prima dell'insegnante che il vicino sta forzando la schiena. La domanda nasce lì. E le risposte che trovano online arrivano quasi tutte da chi vende un corso, il che rende difficile capire cosa vale davvero. Questa guida non vende corsi. Racconta cosa sono le duecento ore, come si riconosce un corso fatto bene, quanto costa, e soprattutto cosa succede il giorno dopo il diploma, che è la parte che nessuna brochure racconta.

## Cosa sono, davvero, le duecento ore

Duecento ore è lo standard minimo fissato da *Yoga Alliance*, un registro privato nato negli Stati Uniti negli anni Novanta. Chi completa un corso presso una scuola registrata può iscriversi come RYT-200, che sta per *Registered Yoga Teacher*, e la sigla compare poi sulle biografie di mezzo mondo. Vale la pena sapere cosa c'è dietro: è un registro, non un albo. Si paga una quota annuale, nessuno verifica le competenze, e in Italia non ha alcun valore legale.

Da noi l'insegnamento dello yoga rientra fra le professioni che la [legge 4/2013]({_b(LEGGE)}) definisce «non organizzate in ordini o collegi». Significa che chiunque può insegnare, dichiarando la propria formazione e senza usare titoli che facciano pensare a una professione sanitaria. Gli attestati degli enti di promozione sportiva, come CSEN, ASI o UISP, riconosciuti dal CONI, servono a lavorare dentro le associazioni sportive dilettantistiche con il regime fiscale di quel mondo, e sono utili per quello; nemmeno loro sono un riconoscimento dello Stato della professione, per quanto qualche sito lo lasci intendere.

La conseguenza è semplice e liberatoria: nessun corso ti rende insegnante per legge. Ti rende insegnante la preparazione, e il corso è il posto dove la costruisci. Per questo conviene giudicarlo per quello che contiene, e non per il bollino che stampa sul diploma.

## Come si riconosce un corso serio

Immagina di avere davanti due programmi, uno da 1.300 euro tutto online e uno da 3.800 in un centro sulle colline, con vitto e alloggio. Il prezzo non ti dice quale sia migliore, e nemmeno la sigla in fondo alla pagina. Te lo dicono altre cose.

La prima è quante ore si passano in sala. Una parte teorica si può fare benissimo a distanza, la storia, la filosofia, le basi di anatomia; ma nessuno impara a correggere un corpo attraverso uno schermo, e un corso da duecento ore interamente online forma al massimo un buon praticante. La seconda è chi insegna anatomia e fisiologia, e per quante ore: servono almeno una ventina, con qualcuno che le sappia insegnare, che sia un fisioterapista, un osteopata, un medico o un'insegnante con una formazione specifica. Se nel programma trovi solo «anatomia sottile», manca la metà che serve a non fare male alle persone.

La terza cosa, e forse la più importante, è la pratica di insegnamento: le ore in cui insegni tu, ai compagni di corso, con qualcuno che ti corregge la voce, il ritmo, le mani. Un corso in cui si pratica soltanto forma praticanti, non insegnanti. Poi vengono i nomi: chi insegna, da quanti anni, con quale storia. Se il sito mostra solo la scuola e non le persone, chiedi, e se puoi fai una lezione con l'insegnante principale prima di iscriverti. Guarda anche quanti sarete in sala, perché sopra i venticinque o trenta la correzione individuale sparisce, e leggi il contratto: cosa succede se ti ritiri, se salti un weekend, se la scuola cancella.

E poi ci sono le parole che dovrebbero farti chiudere la pagina. «Riconosciuto dallo Stato», «abilitante», «lavoro garantito» sono formule che in questo campo non possono essere vere. Su come si riconosce chi lavora bene abbiamo scritto anche dal lato di chi cerca un insegnante, in [come scegliere un insegnante di yoga]({_b(SCEGLI_INS)}): leggerla da futura insegnante aiuta a capire cosa cercheranno un giorno i tuoi allievi. E prima ancora conviene sapere che stile imparerai, perché hatha, vinyasa, ashtanga, yin e kundalini sono [mondi diversi]({_b(TIPI_YOGA)}), e un corso serio dichiara il suo.

## Quanto costa, quanto dura

In Italia, nel 2026, un corso da duecento ore costa fra i 1.500 e i 4.500 euro. Nella parte alta ci sono gli intensivi residenziali, tre o quattro settimane in un centro con vitto e alloggio; in quella media i corsi nei weekend, distribuiti su otto o dieci mesi, che permettono di continuare a lavorare e di praticare l'insegnamento nel tempo, cosa che un intensivo non consente. Il prezzo racconta il formato, il luogo e il cibo, non la qualità didattica: il corso da 1.300 euro e quello da 3.800 possono valere lo stesso, o non valere niente.

A quella cifra vanno aggiunti quasi sempre i libri, l'assicurazione per la pratica, la quota dell'ente sportivo se il corso la richiede, e il tempo, che è la spesa più grande e la meno calcolata.

## Il giorno dopo

Ed eccoci alla parte che le brochure saltano. Il diploma è in cornice, la chat del corso è ancora viva, e tu hai davanti la domanda vera: come si insegna, adesso, per davvero?

Prima di tutto c'è il fisco, e non è la parte più noiosa, è la parte che decide se puoi continuare. Se insegni saltuariamente, una lezione ogni tanto, esistono la prestazione occasionale e, dentro le associazioni sportive, i compensi sportivi con la loro soglia esente. Quando insegni con continuità serve la partita IVA, quasi sempre in regime forfettario, con il codice ATECO giusto: ne abbiamo scritto con calma in [partita IVA per operatori olistici]({_b(PIVA)}) e nel pezzo sul [codice ATECO]({_b(ATECO)}), e un commercialista che conosce il settore vale ogni euro della sua parcella. Subito dopo, prima ancora della prima lezione, una polizza di responsabilità civile professionale: [qui la guida]({_b(RC)}).

Poi serve un posto dove insegnare, e qui le ricerche online raccontano una storia interessante: «affitto sala yoga Milano», «affitto sala yoga Torino», «coworking olistico» sono fra le cose più cercate da chi ha appena finito il corso. Le strade sono sempre le stesse. Si affitta una sala a ore in un centro già avviato, pagando una quota per lezione o una percentuale; si divide uno spazio con altri operatori; si insegna all'aperto nei mesi buoni e a domicilio in quelli cattivi; e si apre uno spazio proprio solo quando i numeri lo reggono. La regola che vale per tutti è partire senza affitto fisso, perché sono i costi fissi a decidere se un'attività sopravvive al primo inverno.

Il prezzo delle lezioni non parte da quello che vorresti guadagnare. Parte da quanto costa la sala, da quante persone servono per coprirla, e da lì si risale. In Italia una lezione di gruppo va dai 10 ai 20 euro a persona e una privata dai 40 agli 80, con differenze forti fra una città e la sua provincia; nei primi anni quasi tutti affiancano un altro lavoro, e chi vive di yoga di solito lo fa combinando gruppi, privati, qualche ritiro e un pubblico costruito con pazienza.

I primi allievi arrivano da tre posti, e nessuno dei tre è la pubblicità. Arrivano dalle persone che già conosci, che sono sempre più di quante pensi; dal centro in cui affitti la sala; e da una pagina online che dica chi sei, cosa insegni, dove e quando, con un modo per prenotare. All'inizio non serve altro. Su Aurya il profilo pubblico fa esattamente questo, è gratis, e la parte che conta di più, la bio, [l'abbiamo raccontata a parte]({_b(BIO)}).

L'ultima cosa la dicono le scuole serie il giorno del diploma: le duecento ore sono l'inizio della formazione, non la fine. Dopo un anno di insegnamento capirai da sola cosa ti manca, e a quel punto sceglierai il modulo successivo sapendo perché.

## Domande frequenti

**Un corso di yoga da 200 ore è riconosciuto in Italia?**
No. Nessun corso di yoga è riconosciuto dallo Stato: l'insegnamento è una professione non organizzata, secondo la legge 4/2013, e si esercita dichiarando la propria formazione. Yoga Alliance è un registro privato, gli attestati degli enti sportivi valgono nel mondo delle associazioni.

**Si può fare un corso da 200 ore online?**
La parte teorica sì. Un corso interamente online non insegna a correggere un corpo né a condurre una sala, e per insegnare servono ore in presenza e pratica di insegnamento con qualcuno che ti corregge.

**Quanto costa diventare insegnante di yoga?**
Fra 1.500 e 4.500 euro per il corso, più assicurazione, libri e la quota dell'ente sportivo se serve. Poi i costi per lavorare: la partita IVA quando arriva, lo spazio, una pagina online.

**Serve subito la partita IVA?**
Non subito. Per le attività saltuarie esistono la prestazione occasionale e i compensi sportivi nelle associazioni; con continuità e volumi serve la partita IVA, quasi sempre in regime forfettario.

**Quanto guadagna un insegnante di yoga?**
Dipende da quante lezioni tiene e da dove. Con gruppi a 10-20 euro a persona e privati a 40-80, nei primi anni quasi tutti affiancano un altro lavoro; chi vive di yoga combina gruppi, privati, ritiri e un pubblico costruito nel tempo.

**Che differenza c'è fra 200 e 500 ore?**
Le 500 ore aggiungono trecento ore di approfondimento, in genere dopo almeno un anno di insegnamento. Non sono più riconosciute delle 200: sono più formazione.
"""

# ── 3. Riflessologia plantare ────────────────────────────────────────

SLUG_3 = "riflessologia-plantare-mappa-seduta-prezzi"
TITOLO_3 = "Riflessologia plantare: la mappa, la seduta, i prezzi"
DESCR_3 = ("Cos'è la riflessologia plantare, come si legge la mappa del piede, come si svolge "
           "una seduta, cosa dice la ricerca, controindicazioni e prezzi in Italia.")
IN_BREVE_3 = ("La riflessologia plantare lavora con pressioni sul piede seguendo una mappa che associa "
              "zone del piede a parti del corpo. Quella mappa non è mai stata dimostrata; quello che "
              "la ricerca sostiene è l'effetto sul rilassamento e sullo stress, che è già molto. Una "
              "seduta dura tre quarti d'ora o un'ora, costa fra i 40 e i 70 euro, e non si fa con "
              "trombosi, ferite o infezioni al piede; in gravidanza si sceglie chi ha esperienza.")
CONTENUTO_3 = f"""\
La prima volta che qualcuno ti tocca i piedi con quell'intenzione, c'è un momento di imbarazzo che dura pochi secondi. Poi il pollice trova un punto sotto l'arco, preme, e senti qualcosa che non ti aspettavi: non dolore, una specie di eco da un'altra parte del corpo, o forse solo la sorpresa di scoprire quanta tensione tieni in un posto a cui non pensi mai. È da lì che nasce la curiosità per la mappa del piede, ed è per questo che «riflessologia plantare mappa» è una delle ricerche più frequenti fra le pratiche sul corpo. In questa guida raccontiamo cos'è la riflessologia, come si legge quella mappa, cosa succede in una seduta, cosa ne dice davvero la ricerca, quando è meglio non farla e quanto costa. Se invece cerchi una panoramica di tutto il lavoro sul corpo, la [guida al massaggio olistico]({_b(MASSAGGIO)}) mette a confronto nove tecniche.

## Da dove viene

La riflessologia come la conosciamo ha una data e due nomi. Negli anni Trenta una fisioterapista americana, Eunice Ingham, partì dalla «terapia zonale» del medico William Fitzgerald, che divideva il corpo in dieci fasce verticali, e la concentrò sul piede, disegnando la prima mappa: ogni zona della pianta avrebbe corrisposto a un organo o a una parte del corpo, e premere lì avrebbe avuto un effetto a distanza. La mappa è diventata il simbolo della pratica, stampata sui poster di ogni studio.

Va detto con chiarezza, perché chi lavora bene lo dice per primo: quella corrispondenza non è mai stata dimostrata. Non esiste un collegamento anatomico o nervoso conosciuto fra l'arco del piede e l'intestino. Quello che invece esiste, ed è documentato, è l'effetto che una pressione attenta sul piede ha sul sistema nervoso: rilassamento profondo, una percezione dello stress che cala, in alcuni studi meno ansia e meno dolore percepito. Chi la pratica seriamente lavora su questo, e usa la mappa come una lingua, non come uno strumento diagnostico.

## Come si legge la mappa

Se guardi la pianta del piede come una figura, la mappa tradizionale la racconta così. Le dita sono la testa e il collo, con l'alluce che rappresenta la testa e il cervello e le altre dita occhi, orecchie e seni paranasali. Subito sotto, i cuscinetti, corrispondono al torace: i polmoni, il cuore sul piede sinistro, le spalle verso il bordo esterno. L'arco è l'addome, con lo stomaco, il fegato a destra e la milza a sinistra, il pancreas, e l'intestino che scende verso il tallone; il tallone è il bacino, la zona lombare e gli organi pelvici. Il bordo interno del piede, dall'alluce al tallone, segue la colonna vertebrale dalle cervicali al sacro, e il bordo esterno raccoglie anca, ginocchio, gomito e spalla. Il piede destro parla della metà destra del corpo, il sinistro della sinistra, con differenze fra una scuola e l'altra.

Chi conduce la seduta usa questa mappa per orientare il lavoro e per parlare con te, dicendoti per esempio che sente una zona più tesa. Se qualcuno pretende invece di leggere nel piede una malattia, sta oltrepassando un confine che la [legge 4/2013]({_b(LEGGE)}) traccia con precisione: la riflessologia non è una pratica sanitaria e non può diagnosticare nulla.

## Come si svolge una seduta

Si resta vestiti, si tolgono scarpe e calze, e ci si sdraia su un lettino o si affonda in una poltrona reclinata. Le prime parole servono a capire perché sei lì, che sia stanchezza, una tensione che non passa, notti difficili o semplice curiosità; poi chi conduce riscalda il piede con movimenti ampi, e comincia il lavoro punto per punto, con una pressione decisa ma mai dolorosa, alternando i due piedi. Alcune zone risultano più sensibili di altre, e una buona operatrice chiede sempre se la pressione va bene. Una seduta dura fra i quarantacinque minuti e l'ora, e molti si addormentano: è normale, ed è quasi il segno che sta funzionando. Alla fine si beve un bicchiere d'acqua e ci si alza con calma.

Quello che le persone raccontano più spesso, uscendo, è di avere i piedi leggeri, di dormire meglio quella notte, di sentire una calma che dura qualche ora. Chi ha un obiettivo, un periodo di stress per esempio, fa di solito un ciclo di quattro o sei sedute, una a settimana, e poi una al mese quando ne sente il bisogno.

## Cosa dice la ricerca

Le revisioni sistematiche degli ultimi quindici anni raccontano una storia coerente, ed è una storia in tre parti. La prima è che la riflessologia produce rilassamento e riduce l'ansia e lo stress percepito, con risultati che tornano in contesti seri come le cure oncologiche di supporto e le cure palliative, dove viene usata per il benessere delle persone e non per la malattia. La seconda è che non esistono prove che agisca su organi specifici o che possa diagnosticare qualcosa. La terza è che gli studi sono spesso piccoli e di qualità diversa, per cui gli effetti sul dolore e sul sonno restano promettenti ma non solidi.

È una pratica di benessere, e va scelta come tale: se qualcosa non va nel corpo, la prima tappa è il medico, e la riflessologia può accompagnare la cura, non sostituirla.

## Quando è meglio aspettare

Ci sono situazioni in cui una pressione sul piede non è indicata, e una brava operatrice te le chiede prima di cominciare. Con una trombosi alle gambe, o il sospetto di averla, non si fa. Con ferite, infezioni, micosi o verruche al piede si aspetta la guarigione, e lo stesso vale per fratture recenti e interventi al piede o alla caviglia. In gravidanza non è vietata, ma nel primo trimestre molte operatrici preferiscono evitare e in ogni caso serve chi ha una formazione specifica: si dice sempre di essere incinta. Con il diabete accompagnato da neuropatia, con disturbi della circolazione o con malattie in fase acuta, si chiede prima al proprio medico.

## Quanto costa, come scegliere

In Italia una seduta di riflessologia plantare costa fra i 40 e i 70 euro, con le grandi città nella parte alta e la provincia in quella bassa, e i cicli di cinque o sei sedute hanno quasi sempre uno sconto. I prezzi di chi la pratica nella rete Aurya sono nel listino del profilo, e per un confronto con tutte le altre pratiche c'è [quanto costano le pratiche olistiche, una per una]({_b(COSTI)}).

Per scegliere chi la pratica valgono i segni di serietà che valgono ovunque: chiedi dove si è formata e da quanto la pratica, diffida di chi promette di curare qualcosa, preferisci chi al primo incontro fa domande sulla tua salute e ti dice quando la riflessologia non è indicata. Li abbiamo raccolti in [come capire se un operatore olistico è serio]({_b(SERIO)}) e nel racconto del [primo colloquio]({_b(COLLOQUIO)}). Chi la pratica nella rete lo trovi nella pagina della disciplina, [riflessologia](/operatori/riflessologia), con le sedi, il listino e le recensioni verificate; e se ti piace il lavoro sul corpo che si riceve vestiti, lo [shiatsu]({_b(SHIATSU)}) è la pratica cugina.

## Domande frequenti

**La riflessologia plantare fa male?**
No. La pressione è decisa e alcune zone possono risultare sensibili, ma non deve mai essere dolorosa: se lo è, lo dici e chi conduce alleggerisce.

**Quante sedute servono?**
Per il rilassamento ne basta una. Chi ha un obiettivo, come un periodo di stress o notti difficili, fa di solito un ciclo di quattro o sei sedute settimanali e poi una al mese.

**Dal piede si può capire se ho una malattia?**
No. Non esistono prove che dal piede si leggano malattie, e chi lo sostiene va oltre quello che la legge consente a una pratica non sanitaria.

**Si può fare in gravidanza?**
Con cautela e con chi ha una formazione specifica; nel primo trimestre molte operatrici preferiscono evitare. Si dice sempre di essere incinta.

**Quanto costa una seduta?**
Fra 40 e 70 euro, per tre quarti d'ora o un'ora. I cicli hanno spesso uno sconto.

**Che differenza c'è con un massaggio ai piedi?**
Il massaggio lavora sui muscoli e sulla circolazione con movimenti ampi; la riflessologia lavora per punti, seguendo la mappa, con pressioni ferme. Spesso una seduta li combina.
"""

# ── 4. Welfare aziendale 2026 ────────────────────────────────────────

SLUG_4 = "welfare-aziendale-2026-esempi-deducibilita-benessere"
TITOLO_4 = "Welfare aziendale 2026: esempi, deducibilità e benessere"
DESCR_4 = ("Cos'è il welfare aziendale, le soglie 2026 dei fringe benefit, quando è deducibile "
           "al 100%, gli esempi che funzionano e dove entra il benessere.")
IN_BREVE_4 = ("Il welfare aziendale è tutto quello che un'azienda dà alle persone oltre lo stipendio, "
              "con un vantaggio fiscale se rispetta le regole dell'articolo 51 del TUIR. Nel 2026 i "
              "fringe benefit sono esenti fino a mille euro, duemila con figli a carico, e il "
              "benessere psicofisico rientra fra i servizi ammessi, deducibile per intero se lo "
              "scrivi in un regolamento. Ma il welfare che funziona non è un catalogo: è una cosa "
              "fatta bene, che le persone sentono. Qui raccontiamo quale, con le cifre da verificare "
              "con il consulente.")
CONTENUTO_4 = f"""\
C'è una scena che si ripete in molte aziende italiane verso ottobre. La responsabile delle risorse umane ha davanti il budget dell'anno dopo, una voce che dice «welfare», e il catalogo di una piattaforma con quattromila prodotti dentro: buoni carburante, abbonamenti in palestra, corsi di inglese, cene. L'anno scorso le persone hanno speso quasi tutto in buoni spesa. Nel sondaggio interno, alla domanda su cosa vorrebbero, hanno risposto «meno stress» e «più tempo». E lei si chiede come si faccia a mettere «meno stress» in un catalogo. Questa guida parte da quella domanda. Racconta cos'è il welfare aziendale, come funziona il fisco nel 2026, quali esempi funzionano davvero e dove entra il benessere delle persone, che è il pezzo su cui lavora Aurya. Le regole fiscali cambiano quasi ogni anno: le cifre che leggi sono quelle in vigore mentre scriviamo e vanno verificate con il consulente del lavoro o il commercialista prima di decidere qualsiasi cosa.

## Cos'è, detto semplice

Il welfare aziendale è l'insieme dei beni, dei servizi e delle somme che un'azienda riconosce alle persone oltre la retribuzione, e che lo Stato tratta con favore, senza imposte e senza contributi, a patto che rispettino le condizioni dell'articolo 51 del Testo unico delle imposte sui redditi. Dentro ci stanno cose molto diverse fra loro: i buoni pasto entro le soglie, i rimborsi per la scuola dei figli, l'assistenza per un genitore anziano, l'abbonamento al treno, le opere e i servizi con finalità di educazione, ricreazione, assistenza sociale e sanitaria, e i cosiddetti fringe benefit, cioè i beni e i servizi in natura fino a una soglia annua.

La cosa che conta capire subito è che il welfare può nascere in tre modi, e il modo cambia il fisco. Può essere previsto dal contratto collettivo o da un accordo aziendale, può essere introdotto con un regolamento che l'azienda scrive e si impegna a rispettare, oppure può essere deciso di volta in volta, per generosità o per premio. Torneremo su questa differenza, perché vale molto.

## Le cifre del 2026

Per anni la soglia sotto cui un fringe benefit non faceva reddito è stata di 258,23 euro, una cifra che tutti gli uffici del personale conoscono a memoria. La legge di bilancio del 2025 l'ha alzata, per gli anni 2025, 2026 e 2027, a mille euro, e a duemila per chi ha figli fiscalmente a carico. Sotto quella soglia il valore non si tassa; sopra, e questo sorprende sempre, diventa imponibile l'intero importo e non solo la parte eccedente. Nella soglia rientrano anche i rimborsi delle bollette di casa, dell'affitto e degli interessi del mutuo sulla prima casa, alle condizioni previste.

C'è poi il premio di risultato: quando il contratto lo prevede, la persona può scegliere di riceverlo sotto forma di servizi di welfare invece che in busta paga, e in quel caso non paga imposte sulla parte convertita, entro i limiti di legge. È il meccanismo con cui molte aziende finanziano il proprio welfare senza aggiungere costi.

E arriva la differenza promessa poco fa. Le spese per opere e servizi di educazione, ricreazione, assistenza sociale e sanitaria sono deducibili per intero se nascono da un contratto, da un accordo o da un regolamento aziendale; se invece l'azienda le decide volontariamente, di volta in volta, la deducibilità si ferma al cinque per mille del costo del lavoro, secondo l'articolo 100 del Testo unico. È il motivo per cui quasi tutte le aziende, prima di fare qualsiasi cosa, scrivono un regolamento di due pagine.

## Gli esempi che funzionano

Le piattaforme offrono cataloghi sterminati, e le aziende che ne ricavano qualcosa sono quasi sempre quelle che scelgono poche cose e le fanno bene. La salute è la voce più usata e la più apprezzata nei sondaggi interni: i check-up, le polizze sanitarie integrative, le campagne vaccinali. La conciliazione, cioè gli asili, i campus estivi, i rimborsi scolastici e l'assistenza ai familiari non autosufficienti, riduce le assenze più di qualunque premio, perché toglie alle persone il pensiero che le tiene sveglie. La mobilità, con gli abbonamenti al trasporto pubblico e le bici aziendali, costa poco e si vede tutti i giorni. E poi c'è il tempo, che non passa dal fisco ma è spesso la prima cosa che le persone chiedono: qualche giorno in più, un orario che si può muovere.

Il benessere psicofisico è la voce che cresce più in fretta ed è anche quella su cui si fa più confusione, perché è facile comprarlo male: un'app che nessuno apre, una giornata a tema con i palloncini, un corso di mindfulness usato per far sopportare carichi di lavoro che andrebbero cambiati. Chi lavora in questo campo con serietà lo dice prima: un programma di benessere non sostituisce un'organizzazione sana, la rende possibile.

## Dove entra il benessere delle persone

Dal 2008 ogni azienda ha l'obbligo di valutare il rischio da stress lavoro-correlato, lo dice il decreto legislativo 81. La valutazione è obbligatoria; cosa fare dopo, no. Ed è esattamente in quello spazio che il benessere smette di essere un regalo e diventa una risposta.

Torniamo alla responsabile delle risorse umane di ottobre. Se prende in mano la valutazione dello stress che l'azienda ha già fatto, scopre che dice dove sono i problemi: un reparto, un periodo dell'anno, un tipo di ruolo. Da lì la strada che vediamo funzionare parte piccola. Un gruppo pilota di quindici o venti persone, un percorso di otto settimane e non una giornata, con una misura semplice prima e una dopo: dieci domande sul carico percepito, ripetute dopo tre mesi. Il formato più studiato al mondo è il [protocollo MBSR]({_b(MBSR)}), otto incontri e pratica a casa; ma anche dieci minuti di [respiro guidato]({_b(RESPIRO)}) all'inizio di una riunione, una pausa attiva a metà pomeriggio, una lezione di yoga all'una fanno la differenza, perché stanno dentro l'orario di lavoro, e quello che si fa fuori orario non lo fa nessuno.

E poi c'è la cosa che nessuna app può fare: qualcuno che entra in azienda, conosce le persone, e torna. Su Aurya questo lavoro lo fanno i professionisti della rete, insegnanti di yoga, istruttori di mindfulness, operatori del respiro e del suono con esperienza di gruppo, e il modo più semplice per far provare a un gruppo qualcosa che poi chiede di continuare è una giornata fuori sede: yoga al mattino, respiro, un bagno di suono, un cammino in natura nel pomeriggio. Ne parliamo nella pagina [Aurya per le aziende](/aziende). Per una panoramica delle pratiche che hanno prove sullo stress, [cosa funziona davvero]({_b(STRESS)}).

## Cosa costa, come si comincia

Le cifre del mercato italiano, indicative perché ogni preventivo si fa sul gruppo, sul luogo e sulla durata: una lezione di gruppo in azienda costa fra gli 80 e i 150 euro; un percorso di otto settimane per un gruppo fra i 1.500 e i 4.000; una giornata di team building di benessere fuori sede fra gli 80 e i 200 euro a persona, struttura e vitto compresi. Non sono cifre da piattaforma: sono cifre da persone che vengono da te.

Il percorso, allora, è questo. Si legge la valutazione dello stress. Si sceglie un gruppo pilota e un percorso di otto settimane con la misura prima e dopo. Si scrive il benessere nel regolamento aziendale, con il consulente, per la deducibilità piena. Si raccontano i risultati prima alle persone e poi alla direzione. E solo dopo, se ha funzionato, si allarga: il catalogo, la piattaforma, le voci in più. Per un progetto con la rete Aurya il primo passo è il [modulo per le aziende](/aziende), e rispondiamo entro due giorni lavorativi.

## Domande frequenti

**Cos'è il welfare aziendale, in una frase?**
Beni, servizi e somme che l'azienda riconosce alle persone oltre lo stipendio, con un trattamento fiscale agevolato se rispettano l'articolo 51 del TUIR.

**Qual è la soglia dei fringe benefit nel 2026?**
Mille euro all'anno, duemila per chi ha figli a carico, per gli anni 2025-2027 secondo la legge di bilancio 2025. Sopra la soglia diventa imponibile tutto l'importo. Le regole cambiano spesso: da verificare con il consulente.

**Il welfare è deducibile per l'azienda?**
Per intero se previsto da contratto, accordo o regolamento aziendale; al cinque per mille del costo del lavoro se deciso volontariamente, secondo l'articolo 100 del TUIR.

**Lo yoga in azienda rientra nel welfare?**
Sì, fra le opere e i servizi con finalità di educazione, ricreazione e assistenza sociale, se offerto a tutti o a categorie di dipendenti. Anche i percorsi di gestione dello stress. Come strutturare l'offerta lo si decide con il consulente.

**Meglio una piattaforma o un percorso con le persone?**
Non si escludono. La piattaforma copre le voci a catalogo; il benessere psicofisico dà risultati quando qualcuno entra in azienda e torna. Chi parte da un pilota di otto settimane sa cosa comprare dopo.

**Un team building di benessere è welfare?**
Di norma è un costo di gestione, non welfare del dipendente. Può essere la porta per un percorso che poi entra nel regolamento. Anche qui, il consulente.
"""

# ── 5. Yoga e ritiri in Toscana ──────────────────────────────────────

SLUG_5 = "yoga-e-ritiri-in-toscana-guida"
TITOLO_5 = "Yoga e ritiri in Toscana: dove, quando, quanto costa"
DESCR_5 = ("Ritiri di yoga e benessere in Toscana: le zone, le stagioni, i formati, i prezzi "
           "veri e come scegliere. E come farsi avvisare quando se ne apre uno.")
IN_BREVE_5 = ("La Toscana è la regione più cercata in Italia per un ritiro di yoga, e il motivo non è "
              "solo la cartolina: è la distanza giusta da Firenze, Roma, Bologna e Milano, i casali "
              "che si affittano per una settimana, il silenzio a mezz'ora da tutto. I mesi buoni sono "
              "primavera e inizio autunno; un weekend costa fra 250 e 500 euro, una settimana fra 900 "
              "e 1.800. Qui le zone, le stagioni, i formati, e il modo per farsi avvisare quando un "
              "ritiro in Toscana apre le iscrizioni.")
CONTENUTO_5 = f"""\
Immagina di cercare, un martedì sera di luglio, un ritiro di yoga per agosto. Scrivi «ritiro yoga Toscana» e trovi due cose: tantissime pagine, e quasi tutte esaurite. È la ricerca più frequente in Italia fra tutte le regioni, con «Toscana yoga retreat» subito dietro per chi cerca in inglese, e il motivo è più concreto della cartolina. La Toscana ha i casali fra le colline che si affittano per una settimana intera, il silenzio a mezz'ora da qualsiasi città, e soprattutto sta alla distanza giusta da Firenze, da Roma, da Bologna e da Milano per un weekend, che è il formato con cui quasi tutti cominciano. Questa guida racconta dove si va, quando, quanto si spende e come si sceglie; e in fondo spiega come farsi avvisare quando un ritiro apre le iscrizioni, così il prossimo luglio non arrivi tardi.

## Le Toscane

Non esiste una Toscana sola, e i ritiri lo sanno. Quella che tutti hanno in mente è il Chianti e la Val d'Elsa, fra Firenze e Siena: i casali fra le vigne, i cipressi, la luce del pomeriggio. È la zona più servita e la più cara, la più facile da raggiungere in treno da Firenze, Siena o Poggibonsi, e per questo la migliore per un primo ritiro.

Più a sud si apre la Val d'Orcia, con Pienza e Montalcino, le terme di Bagno Vignoni e di San Filippo dove ci si immerge dopo la pratica, e il monte Amiata che porta bosco e fresco anche in agosto: molti ritiri di silenzio stanno lì, dove il paesaggio aiuta a non parlare. La Maremma è un'altra cosa ancora, più lontana, più selvatica, con la costa dell'Argentario e del parco dell'Uccellina e l'interno di Pitigliano e Sorano scavato nel tufo; è la Toscana dei ritiri con il mare, spesso più economica.

A nord-est di Firenze cominciano i boschi. Il Casentino e il Mugello sono la Toscana degli eremi, dove da secoli si va a stare in silenzio, e oggi accanto ai monasteri ci sono ritiri laici di meditazione e di cammino: i [bagni di foresta]({_b(CAMMINI)}) qui hanno una casa naturale. Ancora più a nord, la Garfagnana e la Lunigiana sono montagna vera, le Apuane, pochi turisti, per chi vuole camminare sul serio. E poi c'è l'Elba, con la costa, per i ritiri di yoga e mare fra maggio e settembre.

## Le stagioni, quelle vere

Le ricerche dicono che tutti vogliono agosto, e in agosto la Toscana è piena, calda e cara. I mesi migliori sono altri: da aprile a giugno e da settembre a ottobre si pratica all'aperto, la luce dura fino a tardi, i prezzi scendono e nei casali c'è posto. I ponti di primavera, il 25 aprile e il primo maggio, sono i momenti in cui aprono più ritiri brevi, e l'inizio dell'autunno è quando molti insegnanti organizzano il weekend che poi ripetono ogni anno. In inverno restano i ritiri di silenzio e i weekend che finiscono alle terme; a Capodanno i ritiri residenziali vanno esauriti già a novembre, e chi li cerca a dicembre trova le liste d'attesa.

## I formati e quanto costano

Il weekend, dal venerdì sera alla domenica pomeriggio, è il formato per chi comincia: due o tre pratiche al giorno, i pasti insieme, il sabato pomeriggio libero. Costa fra i 250 e i 500 euro con vitto e alloggio, e la differenza fra le due cifre la fa quasi sempre la struttura, non lo yoga. La settimana, cinque o sette notti, è il formato classico dell'estate, con più profondità e più stanchezza, e costa fra i 900 e i 1.800 euro tutto compreso; oltre, si paga il lusso del posto. Il ritiro di silenzio o di meditazione, da tre a dieci giorni, ha meno yoga e più seduta e cammino, regole precise sul telefono e spesso sulla parola, e nella tradizione vipassana esistono formati a donazione. E c'è la giornata, una domenica di pratica e pranzo in un casale, fra i 60 e i 120 euro, che è il modo migliore per provare un'insegnante prima di seguirla per una settimana.

Il prezzo dipende da tre cose: la struttura, il numero dei partecipanti, perché sotto le dieci persone il costo a testa sale, e chi conduce. Chi organizza i ritiri conosce questa matematica meglio di chiunque, e ne abbiamo scritto dal loro lato in [come calcolare il prezzo di un ritiro]({_b(PREZZO_RIT)}): leggerla da partecipante aiuta a capire cosa si sta pagando.

## Com'è una giornata

Ci si sveglia presto. La pratica è all'alba o comunque prima della colazione, che poi è lenta, lunga, e per molti è la parte migliore. In tarda mattinata c'è una seconda pratica o un laboratorio; il pranzo, quasi sempre vegetariano e cucinato lì, in molti ritiri toscani è una parte dell'esperienza e non un intervallo. Il pomeriggio è libero, o c'è un cammino; al tramonto una pratica dolce o una meditazione, poi la cena, e a volte un cerchio o una serata di suono. Il tipo di yoga cambia tutto: un ritiro di ashtanga alle sei del mattino e uno di yin al tramonto sono due vacanze diverse, e prima di prenotare conviene guardare [le differenze fra gli stili]({_b(TIPI_YOGA)}), leggere [come scegliere un ritiro]({_b(SCEGLI_RIT)}) per tipo, durata e budget, fare [le domande giuste]({_b(DOMANDE)}) e chiudere con [cosa portare]({_b(PORTARE)}).

Una domanda che sembra piccola e non lo è: come si arriva. La Toscana dei ritiri è quella senza treno. Firenze, Siena, Arezzo, Grosseto e Pisa sono le stazioni di riferimento, e quasi tutti i ritiri organizzano un passaggio dalla stazione a un'ora fissa o consigliano un noleggio. Chiederlo prima di prenotare è la prima domanda utile, e la risposta dice molto su come è organizzato il resto.

## Chi conduce, e come non arrivare tardi

I ritiri in Toscana li conducono insegnanti che spesso vivono altrove e affittano il casale per quella settimana, e il modo migliore per sceglierne uno è conoscere l'insegnante prima. Nella rete Aurya trovi i profili degli [insegnanti di yoga](/operatori/yoga) con le sedi, il listino e le recensioni verificate; quando uno di loro apre un ritiro, compare nel suo profilo e nel [calendario delle esperienze](/esperienze).

Ma torniamo al martedì sera di luglio. Un ritiro in Toscana si riempie in fretta, e chi lo cerca a luglio per agosto arriva tardi quasi sempre. Per questo esiste il Cerchio: dici che tipo di ritiro cerchi e dove, e ti avvisiamo noi quando se ne apre uno che corrisponde, prima che vada esaurito. Ci si iscrive in un minuto, gratis, da [qui](/cerca-ritiro), e intanto si ricevono le meditazioni riservate.

## Domande frequenti

**Quanto costa un ritiro di yoga in Toscana?**
Un weekend fra 250 e 500 euro, una settimana fra 900 e 1.800, quasi sempre con vitto e alloggio; una giornata fra 60 e 120. Sopra queste cifre si paga la struttura, non la pratica.

**Qual è il periodo migliore?**
Da aprile a giugno e da settembre a ottobre: si pratica all'aperto, c'è meno gente, i prezzi sono più bassi. Agosto è il mese più cercato e il più caro.

**Serve esperienza per partecipare?**
Per i weekend e per i ritiri di hatha o yin no. Per ashtanga, kundalini e i ritiri di silenzio lunghi conviene avere una pratica regolare; il programma lo dice, e se non lo dice si chiede.

**Si può andare da soli?**
Sì, ed è la norma: la maggior parte delle persone arriva sola, e i ritiri sono pensati per questo. Le camere singole costano di più e finiscono prima.

**Come arrivo senza auto?**
In treno fino a Firenze, Siena, Arezzo, Grosseto o Pisa, e con il passaggio organizzato dal ritiro. Da chiedere prima di prenotare.

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
