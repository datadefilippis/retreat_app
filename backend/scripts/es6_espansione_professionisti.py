"""ES6 — i due pezzi per i professionisti, e un dato inventato da togliere.

LA COSA GRAVE, trovata leggendo per espandere. In "Come promuovere un
ritiro" c'era scritto:

    "Un dato dalla nostra esperienza: gli organizzatori che chiedono
    una caparra online hanno tassi di presenza vicini al 100%. Quelli
    che raccolgono «interessati» via messaggio perdono per strada dal
    30 al 50% dei posti."

Non e' un'esagerazione di marketing, e' un NUMERO INVENTATO attribuito
a dati nostri. Aurya non ha mai gestito una prenotazione di ritiro:
quell'esperienza non esiste. E' il difetto peggiore trovato finora,
perche' tutti gli altri erano questioni di voce o di fase, mentre
questo e' un dato falso presentato come proprio.

Sostituito con il MECCANISMO, che e' vero e non ha bisogno di cifre:
chi ha versato dei soldi si comporta diversamente da chi ha scritto
"mi interessa". Vale anche l'altra riga, "osservando gli operatori che
riempiono i loro ritiri edizione dopo edizione", che rivendica
un'osservazione sistematica che non abbiamo fatto.

E in "Come calcolare il prezzo" la chiusura diceva ancora "e'
letteralmente il motivo per cui stiamo costruendo Aurya", cioe' una
promessa di visibilita' della fase precedente.

LE ESPANSIONI. Al pezzo sul prezzo mancava la cosa piu' utile in
assoluto per chi legge: UN ESEMPIO NUMERICO COMPLETO. E mancava come
si tratta con una struttura, che e' dove si decide meta' del margine.
Al pezzo sulla promozione mancava il calendario di lancio e la parte
sul GDPR della lista contatti, che gli operatori sbagliano
regolarmente e che costa cara.

    venv/bin/python scripts/es6_espansione_professionisti.py [--dry-run]
"""
import asyncio
import os
import re
import sys
from datetime import datetime, timezone

PREZZO = "prezzo-giusto-ritiro-come-calcolarlo"
PROMO = "come-promuovere-un-ritiro-e-riempire-i-posti"
IVA = "/blog/partita-iva-operatore-olistico-fiscalita-guida"
SERIO = "/blog/come-capire-se-un-operatore-olistico-e-serio"
DOMANDE = "/blog/domande-da-fare-prima-di-prenotare-un-ritiro"

TITOLO_P = "Come calcolare il prezzo di un ritiro, passo per passo"
DESCRIZIONE_P = (
    "Costi vivi, il valore del tuo lavoro, il punto di pareggio, un esempio "
    "numerico completo e come si tratta con la struttura."
)

CONTENUTO_P = f"""\
C'è un errore che accomuna quasi tutti alla prima esperienza: fissare il prezzo del ritiro guardando quello degli altri. Il risultato, molto spesso, è lavorare settimane per un margine che, diviso per le ore investite, fa impallidire qualsiasi paga oraria.

E chi non si sostiene smette, prima o poi, di fare questo mestiere.

Questa guida costruisce il prezzo dal basso: dai costi veri, non dal listino dei concorrenti. Alla fine trovi un esempio con i numeri fatti per intero.

## Passo 1: i costi vivi

Elenca tutto, non solo la struttura.

1. **Struttura e vitto**: il costo per partecipante concordato con la location, incluse **le tue notti e i tuoi pasti**. Ci sei anche tu, e non sei gratis.
2. **Co-conduttori e collaboratori**: compensi pattuiti, viaggio incluso.
3. **Materiali**: tappetini extra, oli, candele, stampe, quaderni.
4. **Trasporti organizzati**: navette, transfer.
5. **Assicurazione**: la responsabilità civile per l'attività.
6. **Commissioni di incasso**: qualunque canale usi per farti pagare online ha un costo di transazione. Mettilo nel conto dall'inizio.
7. **Promozione**: anche solo il tempo, spesso anche sponsorizzate, foto, grafiche.
8. **Il tuo viaggio**, che quasi tutti dimenticano.

## Passo 2: il tuo lavoro

Un weekend di ritiro non dura due giorni: dura le settimane di progettazione, i sopralluoghi, le decine di messaggi con i partecipanti, la promozione, e i due giorni in cui sei operativo dall'alba a notte.

Contale, quelle ore, e dai loro un valore orario dignitoso. È l'unico modo per scoprire se il tuo ritiro è un lavoro o un hobby costoso.

La domanda test: se lo stesso monte ore lo dedicassi a sessioni individuali alla tua tariffa abituale, quanto incasseresti? Quel numero è il tuo costo-opportunità, e il ritiro dovrebbe quantomeno avvicinarlo.

## Passo 3: separa i costi fissi da quelli a persona

È il passaggio che quasi tutti saltano, e saltarlo produce conti sbagliati.

**I costi fissi** ci sono comunque, con sei iscritti o con dodici: le tue notti, il tuo viaggio, i materiali, l'assicurazione, la promozione, e il tuo lavoro.

**I costi a persona** crescono con il gruppo: vitto e alloggio di ogni partecipante, i transfer, i materiali individuali.

Il pareggio si calcola così: **(costi fissi + il tuo compenso) diviso il numero di iscritti, più il costo per persona**. Dividere il totale come se fosse tutto fisso gonfia il prezzo; trattarlo tutto come variabile ti fa lavorare gratis se il gruppo resta piccolo.

La regola prudente è calcolarlo sul **sessanta o settanta per cento dei posti**. Otto posti? Il prezzo deve reggerti con cinque o sei iscritti.

Da qui nasce anche la decisione più importante: **il gruppo minimo** sotto il quale il ritiro non parte, scritto nelle condizioni fin dall'inizio. Annullare con dignità — rimborso o data alternativa — è meglio che condurre in perdita col sorriso tirato.

## Un esempio con i numeri

Weekend di due notti in agriturismo, otto posti, conduzione singola, pensione completa a 85 € a persona a notte.

**Costi fissi — 520 €**
- Le tue due notti: 170 €
- Materiali e stampe: 90 €
- Assicurazione, quota sull'evento: 60 €
- Il tuo viaggio: 80 €
- Promozione: 120 €

**Costo per ogni partecipante — 170 €**
- Due notti in pensione completa.

**Il tuo lavoro — 1.625 €**
- Progettazione 20 ore, promozione e iscrizioni 15, sopralluogo 6, giorni di ritiro 24. Sessantacinque ore a 25 € l'ora.

**Il pareggio con sei iscritti**
- (520 + 1.625) diviso 6 = 357,50 €
- più 170 € di costo a persona = **527,50 €**
- più il costo di transazione dell'incasso online, circa il 2% = **~538 €**

**Il prezzo, fissato a 580 €**
- **Con sei iscritti:** incassi 3.480 €, spendi 520 + (6 × 170) = 1.540 €. Restano 1.940 €, cioè il tuo compenso di 1.625 € più 315 €.
- **Con otto iscritti:** incassi 4.640 €, spendi 520 + (8 × 170) = 1.880 €. Restano 2.760 €, cioè il tuo compenso più **1.135 €**.

E qui si vede la cosa che i numeri rendono ovvia: passare da sei a otto iscritti non aggiunge il 33% di guadagno, lo **triplica**. Ogni posto oltre il pareggio porta la differenza piena fra prezzo e costo a persona — qui 410 € su 580. È il motivo per cui la promozione non è un accessorio.

Un avvertimento sull'esempio: i costi delle strutture variano moltissimo e il valore orario che ti attribuisci è una tua decisione. Il metodo resta, le cifre cambiano.

## Come si tratta con la struttura

È il passaggio dove si decide metà del margine, e quasi nessuno lo racconta.

**Chiedi un prezzo a persona in pensione completa**, non le voci separate: è più semplice da girare al partecipante e ti protegge dalle sorprese.

**Chiedi la gratuità per chi conduce.** Molte strutture la concedono a partire da un certo numero di partecipanti — spesso da otto o dieci in su. Se non la offrono, chiedila: nel peggiore dei casi ti dicono di no.

**Negozia il minimo garantito**, cioè il numero di persone che paghi comunque. È la voce che può affondarti se il gruppo resta piccolo, e va discussa prima di firmare.

**Metti per iscritto le date di cancellazione** della struttura, e allineale a quelle che offri tu ai partecipanti. Se tu rimborsi fino a trenta giorni prima e la struttura ti trattiene tutto a quarantacinque, quella differenza la paghi tu.

**Chiedi cosa succede se piove**, se la sala è condivisa con altri gruppi, e a che ora si può accedere il primo giorno.

## Passo 4: il posizionamento

Col pareggio in mano, guarda ora il mercato: non per copiare, ma per collocarti.

**Il prezzo comunica.** Un ritiro troppo economico non attira più persone: attira dubbi — cosa manca? — e partecipanti meno impegnati, con più cancellazioni.

**Non competere sul prezzo, competi sulla chiarezza.** Chi mostra programma dettagliato, volto, recensioni vere e condizioni trasparenti vince su chi costa il venti per cento in meno e resta vago. È esattamente quello che chi prenota va a cercare: le [domande che si fa]({DOMANDE}) sono note e conviene rispondere prima che le faccia.

**Le opzioni aiutano più dei ribassi.** Camera condivisa o singola, caparra bassa con saldo comodo, prezzo early per chi prenota presto.

Le fasce reali in Italia, per orientarsi: un weekend va in genere dai 250 ai 500 euro, una settimana dai 700 ai 1.500 e oltre, con variazioni forti secondo struttura e zona.

## Passo 5: caparra e condizioni

Un prezzo giusto sulla carta muore senza un sistema di incasso serio. La caparra del venti o trenta per cento alla prenotazione trasforma gli interessati in iscritti, e le condizioni di cancellazione scritte proteggono te e loro. Ne parliamo a fondo nella [guida alla promozione](/blog/{PROMO}).

## L'IVA e il regime, prima di stampare il prezzo

Il prezzo che esponi è quello che il partecipante paga, e cosa ci finisce dentro dipende dal tuo regime fiscale. In forfettario non applichi IVA; in regime ordinario sì, e va calcolata prima di fissare la cifra, non dopo. È una delle voci che manda in perdita i primi ritiri: [la guida fiscale]({IVA}) entra nel dettaglio.

## L'errore finale: lo sconto in privato

Arriva sempre: «per me si può fare qualcosa?».

Lo sconto concesso in privato al singolo è veleno lento: sleale verso chi ha pagato pieno, corrosivo per il tuo posizionamento, e si sparge sempre. Se vuoi essere accessibile, crea **una** via ufficiale — una borsa di partecipazione, un prezzo early, una tariffa per chi porta un'amica — e tienila uguale per tutti.

## Se non si riempie: le leve, in ordine

**Non abbassare il prezzo.** È la prima tentazione ed è quella che fa più danni, perché svaluta anche chi ha già pagato.

**Allunga la finestra**, se puoi: due settimane in più raccolgono spesso i due posti mancanti.

**Riattiva chi ha chiesto informazioni e non ha prenotato.** Un messaggio personale a chi ti aveva scritto converte più di qualsiasi sponsorizzata.

**Proponi la rateizzazione** o una caparra più bassa: sposta l'ostacolo senza toccare il valore.

**Apri alla co-conduzione** con un collega che porta il suo pubblico.

**Riduci il gruppo minimo** solo se i conti reggono davvero.

**Annulla in tempo**, se serve. Farlo con quattro settimane di anticipo e rimborsare è una scelta professionale; farlo tre giorni prima è un danno che resta.

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

TITOLO_R = "Come promuovere un ritiro e riempire i posti"
DESCRIZIONE_R = (
    "Il calendario di lancio, il pubblico che hai già, la lista contatti a "
    "norma, la pagina che converte, la caparra e cosa fare dopo."
)

CONTENUTO_R = f"""\
Hai creato un ritiro bellissimo. Il luogo è giusto, il programma è curato, tu sei pronto. Manca una cosa sola: le persone.

E i posti vuoti non sono solo un mancato guadagno: come mostrano i conti nella [guida al prezzo](/blog/{PREZZO}), gli ultimi due posti sono spesso quasi tutto il margine.

Questa guida raccoglie quello che funziona, in ordine di importanza, con un calendario di lancio in fondo.

## 1. Il pubblico più prezioso è quello che hai già

L'errore più comune: cercare sconosciuti prima di aver parlato con chi ti conosce. Chi ha già praticato con te, ha già ricevuto un tuo trattamento, ti segue da mesi: sono persone che valgono molte volte qualsiasi pubblico freddo.

**Annuncia il ritiro prima ai tuoi.** Una comunicazione dedicata — email o messaggio personale, non solo un post — con una condizione riservata a chi prenota entro una data.

**Cura la lista contatti come un giardino.** È l'asset più importante della tua attività, e nessun algoritmo può togliertelo.

**Chiedi il passaparola in modo esplicito.** «Se conosci qualcuno a cui questo ritiro farebbe bene, giragli questo messaggio» funziona meglio di quanto pensi.

## 2. La lista contatti, fatta come si deve

Questa parte gli operatori la sbagliano regolarmente, e può costare cara.

**Il consenso va raccolto, non presunto.** Avere l'email di qualcuno perché ha partecipato a una tua lezione non ti autorizza a inserirlo in una lista di comunicazioni promozionali. Serve un consenso specifico, dato liberamente e documentabile.

**Un modulo con la casella non pre-spuntata** e una riga chiara su cosa riceverà e ogni quanto.

**Ogni email deve poter essere disiscritta** con un clic, e la disiscrizione va rispettata subito.

**Tieni traccia di quando e come hai raccolto ogni contatto.** Se ti viene chiesto, devi poterlo dimostrare.

**Non comprare liste** e non importare i contatti della rubrica del telefono. Oltre a essere fuori regola, funziona malissimo.

Una lista di duecento persone che ti hanno detto di sì vale più di duemila indirizzi presi da qualche parte, e ti fa dormire meglio.

## 3. La pagina del ritiro

Chi arriva decide in pochi minuti, e in quei minuti deve trovare risposte.

- **Chi conduce, con volto e storia.** Le persone non prenotano un programma: prenotano te.
- **Programma giorno per giorno**, anche indicativo ma concreto.
- **Cosa è incluso e cosa no**, senza zone grigie.
- **Prezzo chiaro e condizioni di cancellazione visibili.** Nasconderli non aumenta le prenotazioni: aumenta le domande via messaggio e gli abbandoni silenziosi.
- **Recensioni di chi c'è già stato**, verificate e con nome.
- **Foto vere** del luogo e dei tuoi ritiri passati. Le foto d'archivio si riconoscono, e raccontano che qualcosa non è ancora reale.
- **Le risposte alle domande che si fanno tutti** prima di prenotare: quante persone siete, come si dorme, quanto è obbligatorio il programma, cosa succede se sto male. [Sono note]({DOMANDE}), e rispondere prima ti risparmia venti messaggi.

## 4. La caparra

Un «mi interessa» non riempie un ritiro. Una caparra sì.

La prenotazione con caparra, fra il venti e il trenta per cento, e saldo successivo è lo standard che protegge entrambi. Il meccanismo per cui funziona è semplice e non ha bisogno di statistiche: **chi ha versato del denaro si comporta in modo diverso da chi ha scritto un messaggio**. Ha preso una decisione, l'ha segnata in calendario, e nel frattempo non sta valutando altre tre opzioni.

Per te il vantaggio è ancora più concreto: pianifichi su numeri reali invece che su intenzioni, e sai con settimane di anticipo se il gruppo minimo è raggiunto.

## 5. I social: semina, non raccolta

I social servono, ma non come pensi. Il post «ultimi posti disponibili» pubblicato tre volte a settimana non riempie ritiri: costruisce assuefazione.

Quello che funziona è la semina lunga: contenuti che mostrano la tua pratica, il luogo, le persone con il loro consenso, i momenti veri. Chi ti segue per mesi e vede coerenza, quando sente il bisogno di fermarsi penserà a te.

**Il ritiro si vende nei mesi in cui non lo stai vendendo.**

## 6. La collaborazione moltiplica

Un ritiro condotto da due professionisti complementari — yoga e suono, meditazione e lavoro sul corpo — raggiunge due comunità con lo stesso sforzo. Divide i costi, moltiplica il pubblico, arricchisce l'esperienza.

Come si propone, in concreto: scrivi a chi stimi con una proposta già abbozzata (date, luogo, ipotesi di programma, come dividereste ricavi e costi), non con un generico «facciamo qualcosa insieme». La differenza di risposte è netta.

## 7. Dopo il ritiro: il momento più sottovalutato

Il lavoro migliore comincia quando il ritiro finisce.

**Chiedi la recensione subito**, nei giorni successivi, quando l'esperienza è viva. Rendila facile: un link, due minuti.

**Annuncia la prossima edizione ai partecipanti prima che a chiunque altro.** Chi ha vissuto un buon ritiro con te è il pubblico più caldo che avrai mai.

**Resta in contatto** con delicatezza: una comunicazione stagionale vale più di dieci post.

**Scrivi cosa ha funzionato e cosa no** entro tre giorni, finché ricordi. È la cosa che rende la seconda edizione più facile della prima.

## Il calendario di lancio

Per un weekend. Per una settimana, sposta tutto indietro di un mese.

**Quattro mesi prima.** Date bloccate con la struttura, prezzo calcolato, pagina scritta. Non annunci ancora niente.

**Tre mesi prima.** Annuncio alla tua lista e ai tuoi allievi, con condizione riservata. Apri le iscrizioni con caparra.

**Dieci settimane prima.** Annuncio pubblico. Un post che racconta il perché di questo ritiro, non l'elenco delle attività.

**Otto settimane prima.** Scade la condizione riservata. È il momento in cui di solito arriva la prima ondata di iscrizioni.

**Sei settimane prima.** Verifica: a che punto sei rispetto al gruppo minimo? Se sei sotto la metà, è ora di attivare le leve, non due settimane prima.

**Quattro settimane prima.** Ultima chiamata, e riattivazione personale di chi aveva chiesto informazioni senza prenotare.

**Tre settimane prima.** Decisione sul gruppo minimo. Se si annulla, si annulla adesso.

**Una settimana prima.** Informazioni pratiche ai partecipanti: come si arriva, cosa portare, a che ora, chi chiamare.

## Cosa non fare

**La scarsità finta.** «Ultimi due posti» ripetuto per tre settimane si nota, e brucia la fiducia con chi ti segue da tempo.

**Il conto alla rovescia perpetuo.** Se ogni tuo annuncio è un'urgenza, nessuno lo è più.

**Promettere risultati.** «Tornerai trasformato» è una promessa che non puoi mantenere, ed è anche il tipo di frase che fa allontanare le persone più consapevoli — le stesse che leggono [come si riconosce chi lavora bene]({SERIO}).

**Sparire fra un'edizione e l'altra.** La visibilità non è una campagna, è una presenza.

## Il punto di tutto

Nessuna di queste strategie è un trucco. Sono la stessa cosa detta in modi diversi: rendere visibile e affidabile un lavoro che lo merita. La visibilità porta le persone alla porta; la trasparenza — prezzi, condizioni, recensioni — le fa entrare.

## Domande frequenti

**Quanto tempo prima devo iniziare a promuovere?**
Almeno tre mesi per un weekend, quattro o sei per una settimana. I primi posti si riempiono con la tua comunità, gli ultimi con la visibilità esterna: entrambi hanno bisogno di tempo.

**Devo fare pubblicità a pagamento?**
Non all'inizio. Prima esaurisci i canali gratuiti. La pubblicità amplifica quello che già funziona: se la pagina non converte, pagherai per portare persone a una porta chiusa.

**Come gestisco le cancellazioni?**
Con regole scritte prima della prenotazione: entro quando si può annullare e cosa viene rimborsato. Le decidi tu, l'importante è che chi prenota le veda prima di pagare. La chiarezza previene quasi tutti i conflitti.

**Un ritiro piccolo può essere sostenibile?**
Sì, se i numeri sono onesti. Otto persone con caparra sono meglio di venti interessati. Calcola il pareggio prima di fissare il prezzo.

**Posso scrivere a chi ha partecipato a una mia lezione?**
Per comunicazioni promozionali serve un consenso specifico, raccolto e documentabile. Avere l'indirizzo per un altro motivo non basta.

**Quante email posso mandare senza infastidire?**
Nella fase di lancio, tre o quattro in tre mesi sono normali se ognuna dice qualcosa. Il problema non è la frequenza, è mandare quattro volte lo stesso messaggio.

**Meglio annunciare prima le date o prima il prezzo?**
Insieme. Un annuncio senza prezzo genera messaggi che devi gestire uno a uno, e perde le persone che non scrivono.
"""

# la fase precedente e il dato inventato
DA_VERIFICARE = [
    "dalla nostra esperienza",
    "vicini al 100%",
    "stiamo costruendo Aurya",
    "osservando gli operatori che riempiono",
]

PEZZI = [
    (PREZZO, TITOLO_P, DESCRIZIONE_P, CONTENUTO_P,
     [PROMO, IVA.split("/blog/")[1], DOMANDE.split("/blog/")[1]]),
    (PROMO, TITOLO_R, DESCRIZIONE_R, CONTENUTO_R,
     [PREZZO, IVA.split("/blog/")[1], DOMANDE.split("/blog/")[1]]),
]


async def main(dry_run: bool) -> None:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from database import db

    for slug, titolo, descr, contenuto, correlati in PEZZI:
        doc = await db.articles.find_one({"slug": slug}, {"_id": 0, "content": 1})
        if not doc:
            print(f"ASSENTE: {slug}")
            continue
        print(f"{titolo}\n  prima: {len(doc['content'].split())} parole"
              f"  →  dopo: {len(contenuto.split())} parole"
              f"  (descrizione {len(descr)} caratteri)")
        if contenuto == doc["content"]:
            print("  gia' aggiornato")
            continue
        if dry_run:
            continue
        await db.articles.update_one({"slug": slug}, {"$set": {
            "title": titolo, "description": descr, "content": contenuto,
            "author_name": "Aurya", "related_slugs": correlati,
            "updated_at": datetime.now(timezone.utc)}})
        print("  aggiornato")

    print("\n── dati nostri e promesse della fase precedente")
    n = 0
    async for a in db.articles.find({}, {"_id": 0, "slug": 1, "content": 1}):
        for frase in DA_VERIFICARE:
            for h in re.finditer(re.escape(frase), a["content"], re.I):
                i = max(0, h.start() - 60)
                print(f"  {a['slug'][:30]:32} …{a['content'][i:h.end() + 60]}…"
                      .replace("\n", " "))
                n += 1
    print(f"  occorrenze: {n or 'nessuna'}")

    arts = [a async for a in db.articles.find({}, {"_id": 0, "slug": 1,
                                                   "content": 1})]
    slugs = {a["slug"] for a in arts}
    rotti = [(a["slug"], l) for a in arts
             for l in re.findall(r"\]\(/blog/([a-z0-9-]+)\)", a["content"])
             if l not in slugs]
    magri = [(a["slug"], len(a["content"].split())) for a in arts
             if len(a["content"].split()) < 900]
    print(f"\n  link rotti: {rotti or 'nessuno'}")
    print(f"  sotto le 900 parole: {magri or 'nessuno'}")
    print(f"  TOTALE: {len(arts)} articoli, "
          f"{sum(len(a['content'].split()) for a in arts)} parole")

    if dry_run:
        print("\n--dry-run: nessuna scrittura")


if __name__ == "__main__":
    asyncio.run(main("--dry-run" in sys.argv))
