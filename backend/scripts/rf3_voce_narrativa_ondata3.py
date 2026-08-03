"""RF3 — voce narrativa, terza ondata: cinque pezzi.

Prezzo (70%, 15 frammenti), mindfulness (77%, 13), tarocchi (79%, 12),
costellazioni (72%, 11), bagno di gong (70%, 7).

UNA DISTINZIONE CHE VALE LA PENA FISSARE, emersa riscrivendo il pezzo
sul prezzo. Non tutti gli elenchi vanno sciolti in prosa: dove la
STRUTTURA E' L'INFORMAZIONE — un conto economico, un calendario, una
lista di controindicazioni che si consulta e non si legge — l'elenco e'
la forma giusta e scioglierlo peggiorerebbe la lettura. Quello che va
sciolto sono i frammenti in grassetto usati al posto della
punteggiatura, cioe' un ragionamento spezzato in dodici pezzi che
sembrano paralleli e non lo sono.

Nel pezzo sul prezzo, quindi: l'esempio numerico resta un conto, e
attorno torna il ragionamento che spiega perche' quei numeri fanno
quella differenza.

LE PRATICHE, che restano il criterio principale.

MINDFULNESS. I tre esercizi erano un elenco puntato: ora lo spazio di
respiro dei tre minuti e' guidato minuto per minuto, la scansione del
corpo dice dove ci si perde, e il primo boccone e' raccontato come si
fa davvero.

TAROCCHI. La stesa a tre carte diventa una pratica accompagnata, con
la parte che quasi nessuno scrive: guardare l'immagine prima di aprire
il manuale, e rileggere quello che hai scritto una settimana dopo.

    venv/bin/python scripts/rf3_voce_narrativa_ondata3.py [--dry-run]
"""
import asyncio
import os
import re
import sys
from datetime import datetime, timezone

PREZZO = "prezzo-giusto-ritiro-come-calcolarlo"
MINDFUL = "mindfulness-cose-mbsr-come-funziona"
TAROCCHI = "tarocchi-oracoli-strumento-evolutivo"
COST = "costellazioni-familiari-cosa-sono-come-funzionano"
GONG = "bagno-di-gong-sound-healing-benefici"

PROMO = "/blog/come-promuovere-un-ritiro-e-riempire-i-posti"
IVA = "/blog/partita-iva-operatore-olistico-fiscalita-guida"
DOMANDE = "/blog/domande-da-fare-prima-di-prenotare-un-ritiro"
SERIO = "/blog/come-capire-se-un-operatore-olistico-e-serio"
MEDIT = "/blog/meditazione-per-chi-inizia-guida-semplice"
KIT = "/blog/kit-pratiche-quotidiane-15-minuti"
STRESS = "/blog/pratiche-olistiche-contro-stress-cosa-funziona"
TEMA = "/blog/lettura-tema-natale-cosa-aspettarsi"
CERCHI = "/blog/cerchi-di-donne-cosa-sono-come-funzionano"
CAMPANE = "/blog/campane-tibetane-benefici-come-funzionano"
NIDRA = "/blog/yoga-nidra-cose-come-funziona-una-sessione"

# ──────────────────────────────────────────────────────────── prezzo
TITOLO_P = "Come calcolare il prezzo di un ritiro, passo per passo"
DESCR_P = (
    "Costi fissi e costi a persona, il valore del tuo lavoro, un esempio "
    "con i numeri fatti per intero e come si tratta con la struttura."
)

CONTENUTO_P = f"""\
Il primo ritiro quasi tutti lo prezzano allo stesso modo: aprono tre siti di colleghi, guardano quanto chiedono, e si mettono lì in mezzo.

Poi il ritiro finisce, si fanno due conti a mente, e viene fuori che dopo settimane di preparazione, decine di messaggi e due giorni in piedi dall'alba a notte è rimasto qualche centinaio di euro. Diviso per le ore, è una paga che nessuno accetterebbe da un datore di lavoro.

Il problema non è che quel numero fosse sbagliato: è che era stato preso dal posto sbagliato. Un prezzo si costruisce dal basso, dai costi veri, e solo alla fine si guarda cosa fanno gli altri — per collocarsi, non per copiare.

Questa guida fa quel percorso in cinque passi, con un esempio in cui i numeri sono fatti per intero.

## Passo 1: i costi vivi

Il primo esercizio è elencarli tutti, e la parte difficile è ricordarsi quelli che non sembrano costi.

1. **Struttura e vitto**: il costo per partecipante concordato con la location, incluse le tue notti e i tuoi pasti. Ci sei anche tu, e non sei gratis.
2. **Co-conduttori e collaboratori**: compensi pattuiti, viaggio incluso.
3. **Materiali**: tappetini extra, oli, candele, stampe, quaderni.
4. **Trasporti organizzati**: navette, transfer.
5. **Assicurazione**: la responsabilità civile per l'attività.
6. **Commissioni di incasso**: qualunque canale usi per farti pagare online ha un costo di transazione.
7. **Promozione**: anche solo il tempo, spesso anche sponsorizzate, foto, grafiche.
8. **Il tuo viaggio**, che quasi tutti dimenticano.

## Passo 2: il tuo lavoro

Questo è il costo che non compare in nessuna fattura e che decide se il ritiro è un mestiere o un hobby costoso.

Un weekend di ritiro non dura due giorni. Dura le settimane di progettazione, i sopralluoghi, le decine di messaggi con i partecipanti, la promozione, e poi i due giorni in cui sei operativo dall'alba a notte senza una vera pausa. Conta quelle ore — tutte — e dai loro un valore orario dignitoso.

C'è una domanda che rende il conto immediato: se lo stesso monte ore lo dedicassi a sessioni individuali alla tua tariffa abituale, quanto incasseresti? Quel numero è il tuo costo-opportunità, ed è la soglia sotto la quale il ritiro ti sta costando invece di rendere.

## Passo 3: separa i costi fissi da quelli a persona

È il passaggio che quasi tutti saltano, e saltarlo produce conti sbagliati in entrambe le direzioni.

I **costi fissi** ci sono comunque, che il gruppo sia di sei persone o di dodici: le tue notti, il tuo viaggio, i materiali, l'assicurazione, la promozione, e il tuo lavoro. I **costi a persona** invece crescono con il gruppo: vitto e alloggio di ogni partecipante, i transfer, i materiali individuali.

Il pareggio si calcola così: costi fissi più il tuo compenso, diviso il numero di iscritti, più il costo per persona. Se dividi tutto come se fosse fisso gonfi il prezzo e ti tagli fuori dal mercato; se tratti tutto come variabile ti ritrovi a lavorare gratis appena il gruppo resta piccolo.

E il numero su cui dividere non è il tutto esaurito. La regola prudente è calcolare sul sessanta o settanta per cento dei posti: se ne hai otto, il prezzo deve reggerti con cinque o sei iscritti.

Da qui nasce anche la decisione più importante di tutte, che è il **gruppo minimo** sotto il quale il ritiro non parte, scritto nelle condizioni fin dall'inizio. Annullare con dignità — rimborso o data alternativa — è sempre meglio che condurre in perdita col sorriso tirato.

## Un esempio con i numeri

Weekend di due notti in agriturismo, otto posti, conduzione singola, pensione completa a 85 € a persona a notte.

**Costi fissi — 520 €**
- Le tue due notti: 170 €
- Materiali e stampe: 90 €
- Assicurazione, quota sull'evento: 60 €
- Il tuo viaggio: 80 €
- Promozione: 120 €

**Costo per ogni partecipante — 170 €**, cioè le sue due notti in pensione completa.

**Il tuo lavoro — 1.625 €**: progettazione 20 ore, promozione e gestione iscrizioni 15, sopralluogo 6, giorni di ritiro 24. Sessantacinque ore a 25 € l'ora.

**Il pareggio con sei iscritti** viene da un conto solo: (520 + 1.625) diviso 6 fa 357,50 €, più i 170 € di costo a persona fanno 527,50 €, più circa il 2% di costo di transazione dell'incasso online, cioè poco meno di 540 €.

Metti il prezzo a **580 €** e guarda cosa succede ai due estremi.

Con sei iscritti incassi 3.480 € e spendi 520 + (6 × 170) = 1.540 €. Restano 1.940 €: il tuo compenso di 1.625 € più 315 €.

Con otto iscritti incassi 4.640 € e spendi 520 + (8 × 170) = 1.880 €. Restano 2.760 €: il tuo compenso più **1.135 €**.

Ed è qui che i numeri dicono una cosa che a mente non si vede. Passare da sei a otto iscritti non aumenta il guadagno di un terzo: lo triplica. Il motivo è che ogni posto oltre il pareggio porta la differenza piena fra prezzo e costo a persona — in questo caso 410 € su 580 — mentre i costi fissi e il tuo compenso sono già coperti.

È la ragione per cui la [promozione]({PROMO}) non è un accessorio del ritiro: è la parte che decide se ci guadagni.

Un avvertimento sull'esempio: i costi delle strutture variano moltissimo e il valore orario che ti attribuisci è una tua decisione. Il metodo resta, le cifre cambiano.

## Come si tratta con la struttura

È il passaggio dove si decide metà del margine, e quasi nessuno lo racconta perché non è la parte spirituale del mestiere.

Chiedi sempre **un prezzo a persona in pensione completa**, non le voci separate: è più semplice da girare al partecipante e ti protegge dalle sorprese dell'ultimo minuto. Chiedi **la gratuità per chi conduce**, che molte strutture concedono a partire da un certo numero di partecipanti — spesso da otto o dieci in su — e che se non viene offerta si può domandare, perché nel peggiore dei casi ti dicono di no.

Poi c'è la voce che può affondarti, ed è il **minimo garantito**: il numero di persone che paghi comunque, anche se non le porti. Va discussa prima di firmare, perché è quella che trasforma un ritiro semivuoto in una perdita secca.

Metti per iscritto le **date di cancellazione** della struttura e allineale a quelle che offri tu ai partecipanti. Se tu rimborsi fino a trenta giorni prima e la struttura ti trattiene tutto a quarantacinque, quella differenza esce dalle tue tasche e nessuno te l'ha detto.

E chiedi le cose banali che diventano problemi: cosa succede se piove e le attività erano all'aperto, se la sala è condivisa con altri gruppi, a che ora si può accedere il primo giorno.

## Passo 4: il posizionamento

Adesso, e non prima, si guarda il mercato.

Il prezzo comunica, e un ritiro troppo economico non attira più persone: attira dubbi — cosa manca? — e partecipanti meno impegnati, con più cancellazioni dell'ultimo minuto.

E non conviene competere sul prezzo, conviene competere sulla chiarezza. Chi mostra programma dettagliato, volto, recensioni vere e condizioni trasparenti vince su chi costa il venti per cento in meno e resta vago, perché è esattamente quello che chi prenota sta cercando: le [domande che si fa]({DOMANDE}) sono note, e rispondere prima che le faccia vale più di uno sconto.

Quando serve rendere accessibile, funzionano meglio le opzioni dei ribassi: camera condivisa o singola, caparra bassa con saldo comodo, prezzo early per chi prenota presto.

Le fasce reali in Italia, per orientarsi: un weekend va in genere dai 250 ai 500 euro, una settimana dai 700 ai 1.500 e oltre, con variazioni forti secondo struttura e zona.

## Passo 5: caparra, condizioni e IVA

Un prezzo giusto sulla carta muore senza un sistema di incasso serio. La caparra fra il venti e il trenta per cento alla prenotazione trasforma gli interessati in iscritti, e le condizioni di cancellazione scritte proteggono te quanto loro.

E c'è un'ultima voce che manda in perdita più primi ritiri di quante ne manderebbe un errore di calcolo: **l'IVA**. Il prezzo che esponi è quello che il partecipante paga, e cosa ci finisce dentro dipende dal tuo regime fiscale — in forfettario non applichi IVA, in regime ordinario sì, e va calcolata prima di fissare la cifra, non dopo. [La guida fiscale]({IVA}) entra nel dettaglio.

## L'errore finale: lo sconto in privato

Arriva sempre, di solito via messaggio e di solito da qualcuno che conosci: «per me si può fare qualcosa?».

Lo sconto concesso in privato al singolo è veleno lento. È sleale verso chi ha pagato pieno, corrode il tuo posizionamento, e soprattutto si sparge sempre — le persone parlano fra loro, e il tuo prezzo diventa il prezzo che si contratta.

Se vuoi essere accessibile, e ci sono ottime ragioni per volerlo, crea **una** via ufficiale: una borsa di partecipazione, un prezzo early, una tariffa per chi porta un'amica. Una sola, dichiarata, uguale per tutti.

## Se non si riempie

Le leve esistono e vanno usate in ordine, perché la prima tentazione è anche quella che fa più danni.

**Non abbassare il prezzo.** Svaluta il ritiro e insulta chi ha già pagato, e chi lo scopre dopo non torna.

Allunga la finestra, se il calendario te lo permette: due settimane in più raccolgono spesso i due posti che mancano. Riattiva personalmente chi ti aveva scritto per informazioni e non ha prenotato, che è la mossa che converte di più e costa solo il tempo di scrivere. Proponi la rateizzazione o una caparra più bassa, che sposta l'ostacolo senza toccare il valore. Apri alla co-conduzione con un collega che porta il suo pubblico. Riduci il gruppo minimo solo se i conti reggono per davvero.

E se niente di tutto questo basta, annulla in tempo. Farlo con quattro settimane di anticipo e rimborsare è una scelta professionale che le persone ricordano bene; farlo tre giorni prima è un danno che resta attaccato al tuo nome.

## Domande frequenti

**Il mio primo ritiro può essere in pari invece che in guadagno?**
Può essere una scelta consapevole — stai comprando esperienza e recensioni — purché sia una decisione presa con i numeri davanti, non una sorpresa a consuntivo.

**Meglio prezzo tutto incluso o base più extra?**
Tutto incluso quasi sempre: semplifica la scelta e riduce le micro frizioni. Gli extra hanno senso solo per servizi davvero individuali.

**Quanto anticipo serve per l'early bird?**
Apri le iscrizioni tre o quattro mesi prima con un early di quattro o sei settimane: abbastanza per premiare i decisi, non così lungo da svuotare di senso il prezzo pieno.

**Che valore orario mi attribuisco?**
Parti dalla tua tariffa individuale e scendi un po', perché in un ritiro lavori su più persone insieme. Sotto i venti euro l'ora stai finanziando tu il ritiro.

**Devo pagare io le notti dei co-conduttori?**
Sì, e vanno nei costi vivi insieme al loro compenso e al loro viaggio. È una delle dimenticanze più frequenti.

**Quanto margine è ragionevole?**
Non c'è una regola. Il criterio utile è che il margine oltre il tuo compenso copra almeno un annullamento: se un ritiro saltato ti manda in crisi, il prezzo era troppo basso.
"""

# ─────────────────────────────────────────────────────── mindfulness
TITOLO_MI = "Mindfulness: cos'è, come funziona un protocollo MBSR"
DESCR_MI = (
    "Il protocollo delle otto settimane, tre esercizi guidati da provare "
    "stasera, cosa dice la ricerca e la critica alla versione aziendale."
)

CONTENUTO_MI = f"""\
La parola è finita ovunque: sulle app, nei corsi aziendali, sulle copertine dei libri di gestione del tempo. E a forza di comparire ha smesso di significare qualcosa di preciso — oggi «mindfulness» può voler dire una meditazione guidata di tre minuti, un seminario di team building o un modo di dire «con calma».

Significa invece una cosa piuttosto precisa, e ha perfino una data di nascita: il 1979, in un ospedale universitario americano, dentro un programma pensato per pazienti con dolore cronico che la medicina non riusciva più ad aiutare.

Questa guida racconta cos'è, come è fatto il protocollo vero, cosa puoi provare stasera senza iscriverti a niente, cosa dice la ricerca — e una critica seria che di solito non compare da nessuna parte.

## Cos'è

La definizione classica, di Jon Kabat-Zinn, è: prestare attenzione in un modo particolare — intenzionalmente, al momento presente, senza giudicare.

Sono tre parole che fanno tutto il lavoro. **Intenzionalmente** significa che non è distrarsi bene: è scegliere dove mettere l'attenzione. **Al momento presente** significa non ai piani e non ai ricordi, ma a quello che c'è adesso, comprese le cose spiacevoli — ed è la parte che la versione commerciale tende a saltare. **Senza giudicare** significa notare «sto pensando ad altro» invece di «sto sbagliando», ed è la più difficile delle tre.

Come pratica la mindfulness discende dalla vipassana buddhista, da cui è stata estratta e resa laica deliberatamente, per poter entrare in un ospedale pubblico senza chiedere a nessuno di aderire a una tradizione. Quella scelta è la ragione del suo successo, ed è anche l'origine delle critiche di cui parliamo alla fine.

## Il protocollo delle otto settimane

Il programma di riferimento si chiama MBSR, *Mindfulness-Based Stress Reduction*, ed è nato al centro medico dell'Università del Massachusetts. Ha una forma precisa, e conoscerla serve a una cosa molto pratica: riconoscere quando ti stanno vendendo altro con lo stesso nome.

Dura **otto settimane**, con un incontro di gruppo settimanale di circa due ore e mezza, più **una giornata intera di pratica in silenzio** collocata di solito fra la sesta e la settima settimana. E chiede **pratica a casa tutti i giorni**, intorno ai quaranta minuti, con tracce audio guidate: è la parte che quasi tutti sottovalutano ed è dove il programma effettivamente avviene. Gli incontri servono a capire cosa fare e a confrontarsi; il lavoro è a casa.

Dentro si alternano quattro pratiche formali — la scansione del corpo, la meditazione seduta sul respiro e sulle sensazioni, il movimento consapevole con posizioni semplici derivate dallo yoga, e la camminata consapevole — e una serie di esercizi informali da portare nella giornata: mangiare un pasto in silenzio, notare un'attività di routine, registrare gli eventi piacevoli e spiacevoli della settimana.

Esiste poi l'**MBCT**, che adatta lo stesso impianto alla prevenzione delle ricadute depressive aggiungendo elementi di terapia cognitiva. È il protocollo con il riconoscimento clinico più solido di tutta la famiglia.

## Tre esercizi da provare stasera

Sono tratti dal programma e si fanno senza corso. Vale la pena provarli in quest'ordine.

### Lo spazio di respiro dei tre minuti

È il più portatile del protocollo, e si usa nei momenti in cui la giornata sta scivolando: in coda, prima di una riunione, dopo una telefonata difficile.

Siediti o resta in piedi, non importa, e chiudi gli occhi se puoi.

**Il primo minuto è largo.** Chiediti che cosa c'è adesso, e fai un giro: che pensieri stanno passando, che emozione c'è sotto, cosa senti nel corpo. Non devi cambiare niente e non devi risolvere niente: stai facendo un inventario, e ti bastano parole brevi — «fretta», «peso allo stomaco», «quella mail».

**Il secondo minuto è stretto.** Lascia cadere tutto quel materiale e porta l'attenzione sul respiro. Solo il respiro, nel punto in cui lo senti di più. Quando la mente torna alla mail, e ci tornerà, riportala qui.

**Il terzo minuto si riapre.** Allarga l'attenzione dal respiro a tutto il corpo, come se respirassi attraverso la pelle: la postura, il contatto con la sedia o con il pavimento, l'aria sulle mani. Poi riapri gli occhi.

La forma è una clessidra — larga, stretta, larga — e non è casuale: serve a uscire dal pensiero senza fuggirlo, e a rientrare nella giornata da un punto diverso.

### La scansione del corpo

È la pratica su cui il programma insiste di più nelle prime settimane, e la più facile da fare male.

Sdraiati sulla schiena, coperto, con le braccia lungo i fianchi. Porta l'attenzione al **piede sinistro** — non a immaginarlo, a sentirlo: il contatto con il pavimento, la temperatura, il calzino. Resta lì per qualche respiro, poi sposta lentamente: caviglia, polpaccio, ginocchio, coscia. Poi la gamba destra, allo stesso modo. Poi il bacino, l'addome, la schiena, il petto, le mani, le braccia, le spalle, il collo, il viso, la sommità della testa.

Ci sono due cose che succedono a tutti e che vale la pena aspettarsi. La prima è che **in alcune zone non sentirai niente**, e «niente» è una risposta legittima: annotala e passa oltre, senza andare a caccia di sensazioni. La seconda è che **ti perderai**, spesso — ti accorgerai di essere alla spalla senza ricordare di aver fatto il braccio. Quando succede, torna all'ultima zona che ricordi e riparti da lì.

Nella versione lunga dura quaranta minuti. Quella breve, da venti, si fa a gruppi: tutta la gamba, tutto il tronco, tutto il braccio.

### Il primo boccone

Sembra il più banale dei tre ed è quello che le persone ricordano a distanza di anni.

Al prossimo pasto, prima di cominciare davvero, prendi un solo boccone e dedicagli tutta l'attenzione. Guardalo per qualche secondo, come se non sapessi cos'è. Sentine l'odore. Portalo in bocca senza masticare subito e nota cosa succede — la salivazione, la temperatura, la consistenza. Poi mastica lentamente, contando i primi cinque colpi di mascella, e segui il sapore che cambia mentre si scioglie.

Poi deglutisci, e solo dopo prendi il secondo boccone come faresti normalmente.

La cosa che quasi tutti notano è quanto poco del cibo abbiano registrato in tutti gli altri pasti della loro vita.

Se stai costruendo un'abitudine quotidiana, queste tre si incastrano bene con le altre pratiche brevi del [kit dei quindici minuti]({KIT}).

## Cosa dice la ricerca

È la pratica di questo mondo con la letteratura più ampia, e proprio per questo distinguere conta più che altrove.

Le prove più solide riguardano la **prevenzione delle ricadute depressive** con MBCT in persone con episodi ricorrenti — l'area più forte, tanto da essere entrata in linee guida cliniche di alcuni paesi come intervento raccomandato. Poi la riduzione di **stress percepito e sintomi d'ansia**, con effetti replicati. E poi il **dolore cronico**, dove l'effetto documentato non riguarda tanto l'intensità del dolore quanto la relazione con esso e l'interferenza con la vita quotidiana, che è precisamente lo scopo per cui il programma è nato.

Più modesti, e non sempre replicati, sono gli effetti su attenzione, memoria di lavoro e prestazioni cognitive.

C'è poi un limite metodologico che attraversa il campo: molti studi confrontano un corso di mindfulness con il non fare nulla, invece che con un'altra attività di pari impegno e attenzione. Quando il confronto è con un programma attivo, le differenze si assottigliano. Non significa che non funzioni — significa che una parte dell'effetto è il gruppo, l'impegno e l'attenzione ricevuta, cosa che vale [per molte pratiche]({STRESS}).

E gli effetti indesiderati esistono, come per ogni pratica meditativa: ansia che aumenta, senso di distacco, riemersione di materiale doloroso. Ne parliamo nella [guida alla meditazione]({MEDIT}).

## La critica che di solito non si legge

Merita spazio perché non viene dai detrattori: viene da dentro.

La mindfulness è stata estratta da una tradizione in cui la pratica dell'attenzione era inseparabile da una cornice etica — come si vive, come si trattano gli altri, cosa si sceglie di fare. Nella versione laica quella cornice è stata lasciata fuori, per buone ragioni pratiche.

Il risultato, secondo questa critica — associata soprattutto al lavoro di Ronald Purser, che l'ha chiamata *McMindfulness* — è che la pratica può diventare uno strumento di adattamento. Un corso aziendale che insegna ai dipendenti a gestire meglio lo stress di condizioni di lavoro che nessuno intende cambiare sposta su di loro la responsabilità di un problema che non hanno creato, e lo fa con un linguaggio gentile.

Non è un argomento contro la pratica. È un argomento contro l'uso della pratica **come sostituto di un cambiamento necessario**, ed è un criterio utile anche su scala personale: se stai imparando a tollerare una situazione che andrebbe affrontata, la mindfulness sta lavorando per la parte sbagliata.

## Come si riconosce un corso serio

Segue il protocollo delle otto settimane, con la giornata di pratica e il lavoro quotidiano a casa: un corso di quattro incontri da un'ora non è MBSR, e chiamarlo così è scorretto.

Chi lo conduce ha una formazione dichiarata presso un centro riconosciuto e una propria pratica personale continuativa — è il campo in cui questa seconda cosa conta di più, perché non si accompagna dove non si è stati.

C'è un colloquio prima di iscriversi, in cui ti viene chiesto come stai e se stai attraversando un periodo particolare. Ti viene detto cosa il corso non è: non una terapia, non un sostituto di un percorso clinico, e con l'avvertenza che possono emergere cose difficili. E il gruppo ha dimensioni gestibili, con qualcuno che sa cosa fare se una persona sta male.

In Italia un percorso MBSR completo costa in genere fra i 300 e i 600 euro. Valgono anche i [criteri generali]({SERIO}).

## Domande frequenti

**Che differenza c'è fra mindfulness e meditazione?**
La mindfulness è un tipo di meditazione, resa laica e strutturata in protocolli. La [meditazione]({MEDIT}) è la famiglia grande, che comprende anche concentrazione, mantra, amorevolezza e pratiche devozionali.

**Serve fare un corso o basta un'app?**
Le app funzionano per cominciare e per mantenere l'abitudine. Il protocollo di otto settimane in gruppo è un'altra cosa: c'è il confronto, c'è qualcuno che risponde alle domande, e c'è l'impegno che deriva dall'esserci.

**Quanto tempo al giorno serve?**
Il protocollo chiede circa quaranta minuti. Fuori dal protocollo, dieci minuti al giorno costanti valgono più di un'ora ogni tanto.

**È una pratica religiosa?**
No. Discende da una tradizione buddhista ma è stata deliberatamente resa laica per poter entrare in contesti sanitari e scolastici.

**Funziona per l'ansia?**
Gli effetti su stress percepito e sintomi d'ansia sono fra i più replicati. Per un disturbo d'ansia diagnosticato affianca un percorso clinico, non lo sostituisce.

**Posso farla se sono in terapia?**
Spesso sì, e a volte è il terapeuta stesso a proporla. Parlane prima con chi ti segue.

**Cos'è la McMindfulness?**
La critica secondo cui la pratica, separata dalla sua cornice etica, può diventare uno strumento per far tollerare condizioni che andrebbero cambiate.

**Da dove comincio oggi?**
Dallo spazio di respiro dei tre minuti, due volte al giorno per una settimana. Se ti resta addosso, il passo successivo è un percorso di otto settimane.
"""

# ───────────────────────────────────────────────────────── tarocchi
TITOLO_TA = "Tarocchi evolutivi: cosa sono, come funziona un consulto"
DESCR_TA = (
    "Da dove vengono davvero le carte, come è fatto un mazzo, cosa succede "
    "in un consulto, perché funziona senza poteri e come provarli da soli."
)

CONTENUTO_TA = f"""\
Chi tira fuori un mazzo di tarocchi davanti a qualcuno che non li ha mai visti riconosce sempre lo stesso sguardo: metà curiosità, metà «adesso mi dice quando muoio».

Ed è da lì che chi usa le carte in senso evolutivo comincia sempre, dicendo la cosa che spiazza di più: queste carte non predicono niente. Sono più interessanti così.

Questa guida racconta da dove vengono davvero — che è una storia diversa da quella dei negozi — come è fatto un mazzo, cosa succede in un consulto, e la parte che di solito manca: perché un'ora con settantotto figurine produce un effetto reale anche se nessuna di quelle figurine sa nulla di te.

## Da dove vengono, per davvero

La versione che si legge quasi ovunque parla di antica sapienza egizia tramandata per millenni. La versione documentata è più recente e molto più interessante.

Nel **Quattrocento**, nell'Italia settentrionale, compaiono i primi mazzi di *trionfi*, poi detti tarocchi. Sono **carte da gioco**: un gioco di prese con briscola permanente, che si gioca ancora oggi in alcune zone d'Europa. I mazzi più antichi che ci sono arrivati sono commissioni di corte, dipinti a mano, e nessuno li usava per leggere il futuro.

L'uso divinatorio nasce molto dopo, e ha una data. Nel **1781**, in Francia, Antoine Court de Gébelin pubblica un saggio in cui sostiene che i tarocchi conservino la sapienza dell'antico Egitto. È un'invenzione — formulata peraltro prima che i geroglifici venissero decifrati, e smentita da tutto quello che è emerso dopo — ma è l'atto di nascita di tutto il resto. Da lì in avanti Etteilla e gli occultisti francesi dell'Ottocento costruiscono i sistemi di lettura che conosciamo, associando le carte a significati, corrispondenze astrologiche e cabalistiche.

L'ultimo passaggio è del **1909**, a Londra, quando esce il mazzo Rider-Waite-Smith disegnato da Pamela Colman Smith su indicazioni di Arthur Edward Waite. È il primo in cui anche le carte numerali hanno una scena illustrata, e quella scelta grafica è la ragione per cui oggi i tarocchi si leggono come si leggono: le immagini raccontano situazioni riconoscibili anche a chi non ha studiato niente.

Sapere questo non toglie nulla alla pratica. Toglie valore a chi vende millenni che non ci sono.

## Come è fatto un mazzo

Settantotto carte, divise in due gruppi che nella lettura fanno cose diverse.

I **ventidue arcani maggiori** vanno dal Matto al Mondo, e rappresentano situazioni umane grandi: la scelta, il rovesciamento, la perdita, il tempo, la rinascita. Sono le carte che tutti riconoscono, e in una lettura indicano i temi di fondo, quelli che attraversano un periodo intero.

I **cinquantasei arcani minori** si dividono in quattro semi — bastoni, coppe, spade, denari — dall'asso al dieci più quattro figure, e riguardano il quotidiano. Le coppe parlano di emozioni e relazioni, le spade di pensieri e conflitti, i bastoni di azione e desiderio, i denari del concreto e del materiale.

C'è una lettura che chi legge fa per prima, prima ancora dei significati: **guardare la proporzione**. Una stesa in cui escono soprattutto arcani maggiori racconta un momento di passaggio; una fatta quasi solo di minori racconta la vita di tutti i giorni.

## I mazzi principali

Il **Marsiglia** è il più antico fra quelli ancora in uso, e ha gli arcani minori non illustrati: la lettura è più severa e più simbolica, e in Italia e in Francia ha una tradizione forte.

Il **Rider-Waite-Smith** è il più diffuso al mondo ed è il più semplice per cominciare, proprio per via delle scene illustrate su ogni carta.

Il **Thoth**, disegnato su indicazioni di Aleister Crowley, è denso di riferimenti esoterici: bellissimo, e non adatto all'inizio.

Gli **oracoli** sono un'altra famiglia: mazzi liberi che non seguono la struttura dei settantotto, ognuno con un tema proprio — natura, animali, archetipi femminili — e un linguaggio in genere più dolce. Sono spesso la porta d'ingresso più facile: meno codice da imparare, stessa funzione di specchio.

## Evolutivo e cartomanzia

La cartomanzia tradizionale usa le carte per rispondere a domande sul futuro: tornerà, vincerò, quando. È il modello della televisione notturna, ed è quello che ha riempito il settore di dipendenza, paure indotte e tariffe al minuto.

L'approccio evolutivo usa lo stesso strumento in modo opposto: le carte come specchio del presente, non come finestra sul futuro.

E la differenza si vede tutta nella domanda. Non «tornerà?», ma «cosa mi sta chiedendo questa relazione?». Non «andrà bene?», ma «cosa non sto guardando di questa scelta?». La prima cerca una risposta da qualcun altro; la seconda apre un lavoro.

## Come funziona un consulto

Si parte dal tema che porti — una situazione, una decisione, un passaggio — e la prima cosa che si fa insieme è trasformarlo in una domanda aperta. È un passaggio breve e decisivo: le domande da sì o no sono le meno fertili, e chi legge bene ci lavora prima di toccare le carte.

Poi si mescola e si dispongono le carte secondo uno schema in cui ogni posizione ha un significato: la situazione, la radice, la risorsa, la direzione.

Nella lettura si vede chi lavora bene, perché non recita significati a memoria: intreccia i simboli con quello che **tu** riconosci. Le intuizioni migliori arrivano quasi sempre da chi riceve, davanti a un'immagine che sblocca qualcosa che era già lì.

E si chiude con una o due domande da portare a casa, non con delle sentenze. Un consulto dura in genere fra i quarantacinque e i sessanta minuti e in Italia costa fra i 40 e gli 80 euro.

## Perché funziona, senza bisogno di poteri

È la domanda che si fa chi è scettico, e ha tre risposte precise che valgono più della domanda.

La prima è l'**effetto Barnum**, descritto negli anni Quaranta dallo psicologo Bertram Forer: la tendenza a riconoscersi in affermazioni abbastanza generali da valere per chiunque. Viene citato quasi sempre per demolire, e in realtà spiega solo metà della cosa — un'affermazione generica funziona perché **ci mettiamo dentro il nostro materiale**, ed è esattamente quello che serve a un lavoro di riflessione.

La seconda è la **proiezione**. Davanti a un'immagine ambigua la mente ci proietta quello che ha già in testa: una figura che si allontana da tre coppe rovesciate diventa la tua storia, non una storia qualunque.

La terza è la più semplice e la più sottovalutata: **un'ora dedicata a una domanda sola**, con qualcuno che ascolta e nessuna distrazione, è una cosa che quasi nessuno si concede. Buona parte del valore sta lì, ed è la stessa ragione per cui funziona una [pratica di meditazione]({MEDIT}).

Nessuna evidenza sostiene che le carte sappiano alcunché, e chi le usa con serietà non lo sostiene. Il valore non è nella magia: è nella qualità della riflessione che attivano. Vale lo stesso discorso della [lettura del tema natale]({TEMA}).

## Provare da soli: la stesa a tre carte

Non serve un maestro per cominciare, e questa è la pratica più semplice che esista. Servono un mazzo, un foglio e venti minuti.

**Scrivi la domanda prima di toccare le carte.** Deve essere aperta: «cosa mi serve vedere di questa situazione?» funziona quasi sempre. Scriverla, invece di tenerla in testa, la costringe a diventare precisa.

**Mescola con calma**, senza fretta e senza rituali complicati, pensando alla domanda. Poi estrai tre carte e mettile in fila, coperte.

**Girale una alla volta**, e qui viene la parte che quasi nessuno fa: **guarda l'immagine per un minuto intero prima di aprire qualsiasi manuale**. Cosa vedi? Che espressione ha la figura, dove sta guardando, cosa c'è dietro, cosa manca. Scrivi due righe di quello che vedi, anche se ti sembrano banali.

Solo dopo, se vuoi, leggi il significato tradizionale. Se contraddice quello che avevi visto, non cancellare quello che avevi scritto: tienili tutti e due.

**Leggile in ordine.** La prima è la situazione com'è adesso. La seconda è quello che la alimenta o la ostacola. La terza è la direzione possibile.

**Rimetti il foglio in un cassetto e rileggilo fra una settimana.** È la parte che sorprende di più, ed è anche l'unica prova che la pratica ti serva a qualcosa: se rileggendo non riconosci niente, hai scoperto qualcosa di utile lo stesso.

## Come riconoscere chi legge con serietà

Non predice il futuro e te lo dice subito, usando il linguaggio dell'esplorazione e non quello della sentenza. Non alimenta paure: nessuna carta maledetta, nessun malocchio, nessun rituale da comprare per rimediare a una carta uscita male — chi usa la paura sta vendendo.

Il prezzo è a sessione, mai al minuto: la tariffa al minuto è il modello economico della dipendenza, perché chi guadagna sulla durata ha un interesse diretto a non chiudere.

E non tocca salute, denaro e decisioni legali. Nessuna carta dice se fare un intervento, se lasciare il lavoro o se firmare, e chi lo fa sta oltrepassando un confine che vale [per ogni pratica]({SERIO}).

Sopra tutti c'è un test che funziona sempre: dopo il consulto ti senti con più strumenti, o con più bisogno di tornare?

## Le carte nei percorsi

Nei ritiri e nei percorsi di crescita i tarocchi evolutivi compaiono come traccia per la scrittura riflessiva, nei [cerchi di condivisione]({CERCHI}) o nei consulti individuali a margine delle giornate.

## Domande frequenti

**I tarocchi sono antichi ed egizi?**
No. Nascono nell'Italia del Quattrocento come gioco di carte; l'origine egizia è un'invenzione francese del 1781, formulata prima che i geroglifici fossero decifrati.

**Devo credere nei tarocchi perché il consulto funzioni?**
No. Serve disponibilità a riflettere davanti a immagini simboliche, e lo scetticismo curioso è un ottimo punto di partenza.

**Le carte possono dire qualcosa di brutto?**
Nell'approccio evolutivo nessuna carta è negativa: anche le più dure — la Torre, la Morte — parlano di chiusure e ricominciamenti.

**Meglio tarocchi o oracoli per iniziare?**
Gli oracoli sono più immediati, i tarocchi più strutturati. Per un primo consulto va bene lasciar scegliere a chi legge.

**Quale mazzo compro?**
Il Rider-Waite-Smith, perché ogni carta ha una scena illustrata e si legge anche senza aver studiato.

**Posso imparare da solo?**
Sì, ed è un buon strumento di riflessione personale. Il consulto con un'altra persona resta un'esperienza diversa: lo sguardo esterno vede quello che il tuo punto cieco copre.

**Ogni quanto ha senso un consulto?**
Quando c'è una domanda vera. Chi propone appuntamenti fissi settimanali sta costruendo un'abitudine, non accompagnando un percorso.
"""

# ─────────────────────────────────────────────────── costellazioni
TITOLO_CO = "Costellazioni familiari: cosa sono e cosa succede in una sessione"
DESCR_CO = (
    "Il metodo, i tre ordini, come si svolge una sessione di gruppo, cosa "
    "provano i rappresentanti, la ricerca e le controversie su Hellinger."
)

CONTENUTO_CO = f"""\
In una sala, una persona sceglie fra gli sconosciuti presenti qualcuno che rappresenti sua madre, qualcuno che rappresenti suo padre, qualcuno che rappresenti sé stessa. Li dispone nello spazio, uno rispetto all'altro, e si siede a guardare.

Dopo qualche minuto la donna che rappresenta la madre dice che le viene da voltarsi verso la finestra, e non sa perché. Chi ha portato il tema comincia a piangere.

È la scena che divide più di ogni altra in questo mondo: chi l'ha vissuta ne parla come di un'esperienza che ha spostato qualcosa di profondo, chi la guarda da fuori la liquida come teatro suggestivo.

Questa guida racconta cosa sono le costellazioni familiari, su quale modello poggiano, cosa succede davvero in una sessione, cosa dice la ricerca, e cosa si sa del suo fondatore — che è la parte di solito assente.

## Cosa sono

Un metodo di esplorazione delle dinamiche familiari e relazionali, sviluppato dal tedesco Bert Hellinger a partire dagli anni Ottanta e Novanta.

L'idea di fondo è che portiamo dentro di noi, spesso senza saperlo, lealtà, esclusioni e pesi che appartengono al nostro sistema familiare — anche a generazioni che non abbiamo conosciuto. La costellazione è un modo per renderle visibili disponendole nello spazio, dove diventano una cosa che si guarda invece che una cosa di cui si parla.

## I tre ordini

Il metodo poggia su tre principi che Hellinger chiama *ordini dell'amore*, e conoscerli aiuta a capire cosa il facilitatore sta guardando mentre osserva la scena.

Il primo è l'**appartenenza**: ogni membro del sistema ha diritto di farne parte, compresi quelli che sono stati esclusi, dimenticati o taciuti — un figlio non nato, un parente allontanato, chi ha fatto qualcosa di grave. Secondo il modello, chi viene escluso «torna» attraverso qualcun altro, che ne ripete il destino senza saperlo.

Il secondo è l'**ordine**: chi è arrivato prima ha una precedenza rispetto a chi è arrivato dopo, i genitori prima dei figli, i primi legami prima dei successivi. Molte tensioni, in questa lettura, nascono da qualcuno che occupa un posto che non è il suo — tipicamente un figlio che si mette al posto di un genitore.

Il terzo è l'**equilibrio fra dare e ricevere**, che nelle relazioni fra pari deve compensarsi. Fra genitori e figli no: i figli ricevono e non possono restituire, e possono solo passare avanti.

Sono lenti di lettura, non leggi verificate, e la loro utilità sta in quello che fanno vedere.

## Come si svolge una sessione di gruppo

Si comincia dalla domanda. Chi costella porta un tema — una relazione bloccata, uno schema che si ripete, un senso di estraneità — e il facilitatore lo mette a fuoco con poche domande sui fatti essenziali del sistema familiare. Poche davvero: è una particolarità del metodo, che lavora con pochissime informazioni.

Poi arriva la messa in scena, cioè la cosa che spiazza chi arriva la prima volta. Altri partecipanti vengono scelti come **rappresentanti** dei membri della famiglia e disposti nello spazio, uno rispetto all'altro. Nessuno recita e nessuno sa niente: i rappresentanti riferiscono soltanto quello che sentono nella posizione in cui si trovano — un impulso a voltarsi, un peso alle spalle, la difficoltà a guardare qualcuno.

Da lì il facilitatore osserva, sposta, a volte dà voce a una frase. Le dinamiche — vicinanze, esclusioni, pesi — emergono nella disposizione con una nitidezza che sorprende, e il lavoro si chiude cercando un'immagine di maggiore equilibrio, a volte accompagnata da frasi rituali semplici.

Dopo, chi ha costellato porta a casa un'immagine più che una spiegazione, e l'indicazione classica è lasciarla lavorare senza analizzarla troppo nei giorni successivi.

Esistono anche formati individuali, con oggetti o sagome al posto dei rappresentanti, e sessioni online. L'intensità del gruppo dal vivo resta un'altra cosa.

## Cosa provano i rappresentanti

È il fenomeno che colpisce di più: persone che non sanno nulla di quella famiglia riferiscono sensazioni ed emozioni che chi ha portato il tema riconosce.

La spiegazione più prudente, e anche la più sostenuta, è la **lettura inconsapevole dei segnali**. Il gruppo riceve moltissima informazione non verbale — la postura di chi ha portato il tema, il tono con cui ha nominato una persona, come si dispone chi lo circonda, perfino la scelta di chi rappresenta chi — e la elabora senza accorgersene. È un fenomeno reale e ben studiato in psicologia sociale, e basta a rendere conto di quello che succede.

La lettura tradizionale parla invece di un campo informativo condiviso a cui i rappresentanti accedono, e non ha riscontro sperimentale.

Non serve scegliere un campo per vivere l'esperienza con beneficio. Serve sapere che la prima spiegazione è sufficiente, così che nessuno debba comprare la seconda per giustificare quello che ha provato.

## Cosa dice la ricerca

Va detto senza giri di parole: **le costellazioni familiari non hanno validazione scientifica come metodo terapeutico**. Gli studi esistenti sono pochi e su campioni piccoli; alcuni riportano miglioramenti del benessere percepito dopo i seminari, nulla che soddisfi gli standard delle evidenze cliniche. Diverse voci della psicologia invitano esplicitamente alla prudenza.

Il che si traduce in tre conseguenze pratiche. Non sono una psicoterapia e non la sostituiscono, mai. Sono un'esperienza simbolica ed evocativa: uno specchio, non una cura. E su temi delicati — lutti recenti, traumi, disturbi psichici — il contesto giusto è quello clinico, con la costellazione eventualmente dopo e a fianco.

Un facilitatore serio queste cose le dice da solo. Se qualcuno promette di guarire il transgenerazionale o spinge a interrompere una terapia, quello è il momento di andarsene.

## Bert Hellinger, e perché va nominato

Chi si avvicina al metodo prima o poi incontra le polemiche sul suo fondatore, e conviene arrivarci preparati invece di scoprirle per caso.

Hellinger, morto nel 2019, è stato una figura discussa ben oltre il merito della tecnica. Ha espresso pubblicamente posizioni che hanno suscitato critiche dure, anche da parte di associazioni professionali del settore psicologico, in particolare per il modo in cui ha trattato temi come la responsabilità fra vittime e autori di violenza, e per interventi su casi delicati condotti davanti a un pubblico.

Una parte consistente di chi pratica oggi in Europa ha preso distanza esplicita da quelle posizioni e lavora con impostazioni più prudenti, spesso con una formazione psicologica alle spalle. Chiedere quale linea segue chi conduce è una domanda del tutto legittima, e la risposta dice molto.

## Chi dovrebbe rimandare

Ci sono situazioni in cui la risposta giusta è «non adesso», e riconoscerle in anticipo evita di farsi male.

Chi ha subito un lutto recente e non lo ha ancora attraversato. Chi ha una storia di trauma non elaborato, dove il contesto clinico viene prima. Chi attraversa un disturbo psichico in fase acuta. Chi ci arriva spinto da qualcun altro invece che da una domanda propria. E chi cerca una risposta a una decisione pratica, perché non è quello che il metodo fa.

## Come scegliere un facilitatore

Formazione dichiarata e verificabile, meglio se accompagnata da un background in ambito relazionale o psicologico. Linguaggio onesto, che parla di esplorazione ed esperienza e non di guarigione garantita. Uno screening iniziale, in cui ti viene chiesto come stai e cosa porti e in cui chi conduce sa dire «questo tema non è da costellazione». Nessuna pressione a continuare, niente pacchetti obbligati. E una risposta pronta alla domanda su cosa fa se qualcuno sta male durante o dopo il lavoro.

Valgono anche i [criteri generali]({SERIO}). Una sessione di gruppo in Italia costa fra i 30 e gli 80 euro come rappresentante o partecipante, e fra gli 80 e i 150 per costellare il proprio tema.

## Costellazioni e ritiri

Compaiono spesso nei ritiri olistici come esperienza serale o come giornata dedicata, e il contesto del ritiro — un gruppo che si conosce, tempo disteso, nessuna fretta di tornare a casa — le rende più intense di una serata singola in città. È un motivo in più per informarsi prima: le domande da fare stanno [qui]({DOMANDE}).

## Domande frequenti

**Devo raccontare tutta la mia storia familiare?**
No. Una particolarità del metodo è che lavora con pochissime informazioni: il facilitatore chiede solo i fatti essenziali.

**Posso partecipare solo come rappresentante?**
Sì, ed è il modo più graduale di conoscere il metodo: si vive dall'interno senza esporre un tema proprio.

**È un percorso o un evento singolo?**
Tradizionalmente si costella un tema una volta e lo si lascia lavorare. Diffida di chi propone costellazioni a ripetizione sullo stesso tema.

**È compatibile con una psicoterapia?**
Spesso sì come esperienza complementare, ma parlane prima con il tuo terapeuta, che è la persona giusta per valutare tempi e opportunità.

**Come mai i rappresentanti sentono cose che non sanno?**
La spiegazione più sostenuta è la lettura inconsapevole dei segnali non verbali del gruppo, che è un fenomeno reale e studiato. La lettura tradizionale parla di un campo condiviso e non ha riscontro sperimentale.

**Che effetto fa nei giorni dopo?**
Molte persone riferiscono qualche giorno di sensibilità aumentata o di stanchezza. L'indicazione classica è non prendere decisioni importanti nell'immediato.

**Il metodo è riconosciuto?**
No, non è una professione regolata né un metodo validato, e chi lo pratica non è per questo un terapeuta.
"""

# ────────────────────────────────────────────────────────────── gong
TITOLO_GO = "Bagno di gong: come funziona una sessione e cosa si prova"
DESCR_GO = (
    "Cosa succede in quell'ora, cos'è davvero un gong, cosa si prova, le "
    "controindicazioni e cosa regge alla prova della ricerca."
)

CONTENUTO_GO = f"""\
Sei sdraiato su un materassino, coperto da una coperta, in una sala con altre quindici persone che non conosci. Le luci sono basse. Per un minuto non succede niente.

Poi comincia un suono così debole che non sapresti dire quando è iniziato, cresce fino a riempire la stanza, e a un certo punto ti accorgi che non lo stai più sentendo con le orecchie: lo senti nello sterno.

È la descrizione che quasi tutti danno del primo bagno di gong, insieme a quella che arriva un'ora dopo, all'uscita: la sensazione di aver dormito una notte intera.

Questa guida racconta cos'è un bagno sonoro, come si svolge, cosa si prova, e cosa di tutto questo regge alla prova della ricerca — inclusa una spiegazione molto diffusa che non regge.

## Cos'è il sound healing

È una famiglia di pratiche che usa il suono e le vibrazioni per accompagnare corpo e mente in uno stato di rilassamento profondo. Gli strumenti più diffusi sono il gong, le [campane tibetane]({CAMPANE}), le campane di cristallo, i tamburi, la voce.

La differenza con l'ascoltare musica è quella che le persone faticano a spiegare e riconoscono subito: non è suono da ascoltare, è **vibrazione da attraversare**. Un gong suonato a tre metri di distanza arriva prima al torace che alle orecchie, ed è una cosa che non si può raccontare a chi non l'ha provata.

## Cos'è un gong

Vale la pena dirlo perché viene spesso presentato come uno strumento antico e sacro.

Il gong da sala — un grande disco di lega metallica sospeso a un telaio — è nella sua forma attuale uno **strumento orchestrale contemporaneo**, prodotto soprattutto in Europa e in Asia orientale a partire dal Novecento. I modelli più usati nei bagni sonori sono di due tipi: quelli sinfonici, dal suono ampio e indistinto, e quelli accordati su frequenze associate ai corpi celesti, che sono una convenzione commerciale recente e non una scoperta astronomica.

La famiglia dei gong ha certamente radici antiche in Asia, in contesti rituali e cerimoniali. Ma lo strumento che trovi in una sala italiana è figlio del Novecento, e la sua efficacia non dipende da quanto è antico.

## Come si svolge una sessione

Si arriva un po' prima e ci si sistema su un materassino con cuscino e coperta. Conviene vestirsi a strati, perché la temperatura corporea scende con il rilassamento e il freddo è la ragione più comune per cui una sessione non funziona. Chi conduce introduce brevemente la pratica e chiede di eventuali condizioni di salute.

Poi ci si sdraia e si chiudono gli occhi. Il suono comincia piano, quasi impercettibile, e cresce in onde che salgono e si ritirano. Il gong produce una gamma di frequenze così fitta che l'orecchio smette presto di provare ad analizzarla e si limita a seguirla — ed è quello il momento in cui, per la maggior parte delle persone, la mente si stacca. Una sessione dura fra i quarantacinque e i settantacinque minuti.

Alla fine il suono si dirada gradualmente e si resta qualche minuto in silenzio prima di rialzarsi. La fretta, in quel momento, è la cosa che rovina di più l'esperienza: chi si alza di scatto esce stordito.

## Cosa si prova

Le esperienze variano molto, e vale la pena sapere in anticipo quali sono le più comuni, perché nessuna di loro è un segno che stia funzionando meglio o peggio.

Quasi tutti riferiscono un **rilassamento profondo**, simile allo stato di confine fra veglia e sonno: il corpo pesante, la mente che rallenta. Molti vedono **immagini e colori** che affiorano spontanei, senza che stessero cercando di visualizzare niente. La **vibrazione si sente fisicamente**, soprattutto nel torace e nell'addome. Parecchi **si addormentano**, il che va benissimo. E capita che **emergano emozioni**, a volte commozione senza una ragione evidente: è il rilassamento che scioglie quello che era trattenuto.

E c'è anche chi non sente niente di particolare la prima volta, e vive semplicemente un'ora di riposo raro. In un mondo che non si ferma, è un buon risultato.

## Cosa dice la ricerca

Il quadro va diviso in due, perché il modo in cui viene raccontato mescola le due parti come se avessero lo stesso peso.

**Quello che è documentato** sono gli effetti dello stato di rilassamento profondo: riduzione degli indicatori di stress percepito, tensione muscolare più bassa, sonno migliore nelle ore successive. Esistono anche alcuni studi specifici su sessioni di bagno sonoro con risultati incoraggianti su umore e ansia, su campioni piccoli.

**Quello che viene raccontato come dimostrato e non lo è** è la spiegazione più diffusa in sala: il **trascinamento delle onde cerebrali**, cioè l'idea che una frequenza esterna sincronizzi l'attività elettrica del cervello portandola in stati theta o delta. Il fenomeno esiste in condizioni sperimentali molto controllate, ma applicarlo a un gong suonato dal vivo in una stanza è un salto che gli studi non autorizzano. È una metafora, non un meccanismo misurato.

Il che non toglie niente all'esperienza. Significa solo che l'effetto reale ha una spiegazione più semplice — un'ora di immobilità, buio, calore e un suono avvolgente che occupa tutta l'attenzione — e che quella spiegazione basta.

## Controindicazioni

Sono poche e vanno dette prima della sessione. La gravidanza, soprattutto nel primo trimestre, per cui molti operatori sconsigliano o adattano la distanza dagli strumenti. I pacemaker e i dispositivi impiantati, che richiedono un confronto preventivo. L'epilessia, per cui vale un parere del proprio medico. Gli acufeni severi e l'ipersensibilità uditiva, che in alcune persone peggiorano. E i disturbi psichiatrici in fase acuta, dove uno stato alterato prolungato non è indicato.

Chi conduce chiede queste cose prima. Se non le chiede nessuno, quella è l'informazione più importante che riceverai su quel contesto.

## Come prepararsi la prima volta

Vestiti comodi e a strati, con calze calde, perché il freddo arriva verso il quarantesimo minuto. Niente pasti pesanti nelle due ore precedenti. Bevi acqua prima e dopo. E arriva in anticipo: entrare di corsa in una sala già in silenzio è il modo peggiore di cominciare.

Soprattutto, arriva senza aspettative. L'esperienza migliore è quella che non si prova a controllare, e chi entra decidendo cosa dovrebbe succedere di solito passa l'ora a verificare se sta succedendo.

## Come si sceglie una sala

Quattro cose distinguono una sessione condotta bene, e si notano tutte prima o durante.

**Il volume**, perché un bagno sonoro non deve fare male alle orecchie: se il suono è aggressivo o la testa pulsa, quella sala sta suonando troppo forte.

**La distanza dagli strumenti**, che sotto il gong è tutta un'altra intensità rispetto a cinque metri: chi conduce con esperienza dispone le persone tenendone conto e lo dice.

**La possibilità di uscire**, che ti viene detta all'inizio: puoi alzarti e andartene in qualsiasi momento, senza spiegazioni.

E **cosa succede se qualcuno sta male**, che è una domanda da fare prima e a cui chi ha esperienza risponde senza esitare.

Sul resto valgono i [criteri generali]({SERIO}), e se quello che stai valutando è un ritiro di suono le domande da fare stanno [qui]({DOMANDE}).

## Dove provare

Una sessione di gruppo nella propria città è il modo più accessibile, e in Italia costa in genere fra i 15 e i 40 euro. Un trattamento individuale, di solito con le [campane appoggiate sul corpo]({CAMPANE}), permette un lavoro più mirato ed è il passo successivo naturale. E un ritiro di suono, dove i bagni sonori si intrecciano con meditazione, yoga e silenzio, porta la pratica a una profondità che la sessione singola accenna soltanto.

## Domande frequenti

**Il bagno di gong è adatto a tutti?**
Quasi. Le eccezioni sono gravidanza, pacemaker, epilessia, acufeni severi e disturbi psichiatrici in fase acuta: in tutti questi casi serve un confronto preventivo.

**Serve credere in qualcosa perché funzioni?**
No. Un'ora di immobilità, buio e suono avvolgente agisce sul sistema nervoso indipendentemente dalle convinzioni, e lo scetticismo iniziale non rovina niente.

**Meglio individuale o di gruppo?**
Per iniziare il gruppo va benissimo e costa meno. L'individuale permette un lavoro più mirato.

**Quanto spesso si può fare?**
Non ci sono controindicazioni alla frequenza, e molte persone lo vivono come un appuntamento mensile.

**È vero che il suono sincronizza le onde cerebrali?**
È la spiegazione più ripetuta e la meno sostenuta: il fenomeno esiste in laboratorio, non è dimostrato per un gong suonato dal vivo. L'effetto di rilassamento è reale, la spiegazione è più semplice.

**Che differenza c'è fra gong e campane?**
Il gong lavora sull'ampiezza e sull'indistinto, le campane sulla precisione e sul contatto col corpo. Nei bagni sonori si usano insieme.

**Posso addormentarmi?**
Sì, capita spesso e non è un problema. Se ti succede sempre e la cosa ti piace, quello che cerchi somiglia anche allo [yoga nidra]({NIDRA}).
"""

PEZZI = [
    (PREZZO, TITOLO_P, DESCR_P, CONTENUTO_P),
    (MINDFUL, TITOLO_MI, DESCR_MI, CONTENUTO_MI),
    (TAROCCHI, TITOLO_TA, DESCR_TA, CONTENUTO_TA),
    (COST, TITOLO_CO, DESCR_CO, CONTENUTO_CO),
    (GONG, TITOLO_GO, DESCR_GO, CONTENUTO_GO),
]


def analizza(testo):
    blocchi = [b.strip() for b in testo.split("\n\n") if b.strip()]
    prosa = frammenti = parole_prosa = 0
    for b in blocchi:
        if b.startswith("#"):
            continue
        if b.startswith(("-", ">", "1.", "2.", "3.", "4.", "5.", "6.", "7.", "8.")):
            continue
        if b.startswith("**") and b.count(".") <= 2 and len(b.split()) < 28:
            frammenti += 1
            continue
        prosa += 1
        parole_prosa += len(b.split())
    return (round(100 * parole_prosa / max(len(testo.split()), 1)),
            prosa, frammenti)


async def main(dry_run: bool) -> None:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from database import db

    for slug, titolo, descr, contenuto in PEZZI:
        doc = await db.articles.find_one({"slug": slug}, {"_id": 0, "content": 1})
        if not doc:
            print(f"ASSENTE: {slug}")
            continue
        q1, _, f1 = analizza(doc["content"])
        q2, _, f2 = analizza(contenuto)
        print(f"{titolo[:52]:54} prosa {q1}% → {q2}%   frammenti {f1} → {f2}   "
              f"parole {len(doc['content'].split())} → {len(contenuto.split())}")
        if doc["content"] == contenuto:
            print("  gia' aggiornato")
            continue
        if dry_run:
            continue
        await db.articles.update_one({"slug": slug}, {"$set": {
            "title": titolo, "description": descr, "content": contenuto,
            "author_name": "Aurya",
            "updated_at": datetime.now(timezone.utc)}})

    print("\n── quello che resta sotto l'85%")
    arts = [a async for a in db.articles.find({}, {"_id": 0, "slug": 1,
                                                   "content": 1})]
    righe = sorted(((analizza(a["content"]), a["slug"]) for a in arts))
    for (q, _, f), s in righe:
        if q < 85:
            print(f"  {s[:48]:50} {q:3}%  frammenti {f}")
    slugs = {a["slug"] for a in arts}
    rotti = [(a["slug"], l) for a in arts
             for l in re.findall(r"\]\(/blog/([a-z0-9-]+)\)", a["content"])
             if l not in slugs]
    sopra = sum(1 for (q, _, _), _ in righe if q >= 85)
    print(f"\n  link rotti: {rotti or 'nessuno'}")
    print(f"  sopra l'85%: {sopra} su {len(arts)}")
    print(f"  TOTALE: {len(arts)} articoli, "
          f"{sum(len(a['content'].split()) for a in arts)} parole")

    if dry_run:
        print("\n--dry-run: nessuna scrittura")


if __name__ == "__main__":
    asyncio.run(main("--dry-run" in sys.argv))
