"""RF6 — voce narrativa, gli ultimi due veri: i due al 47%.

Pratiche contro lo stress e partita IVA erano gli unici rimasti sotto
il 50% di parole in prosa. Zero frammenti in grassetto, e meta' del
testo in ELENCHI NUMERATI dove il numero non porta nessuna sequenza:
"1. Meditazione. 2. Respirazione. 3. Yoga. 4. Natura." non sono passi,
sono voci. Numerarle fa sembrare che ci sia un ordine e toglie lo
spazio per dire perche' una viene prima di un'altra.

DOVE INVECE I NUMERI RESTANO, e nella guida fiscale sono due punti:
il calcolo dell'esempio, che e' una sequenza vera (imponibile →
contributi → imposta → totale), e l'elenco delle regole del
forfettario, che si consulta invece di leggersi. Vale la distinzione
gia' fissata: dove la struttura E' l'informazione, l'elenco resta.

TRE ARTICOLI RESTANO SOTTO L'85% PER SCELTA, e vale la pena metterlo
per iscritto cosi' nessuno li "sistema" piu' avanti.

"Le domande da fare prima di prenotare" e' una lista di controllo che
si consulta prima di scrivere una mail: renderla scorrevole la
renderebbe inutilizzabile.

"Le differenze fra i tipi di yoga" ripete su ogni stile gli stessi tre
bullet — ritmo, cosa allena, a chi si adatta — e servono esattamente a
questo: permettere il confronto incrociato fra cinque famiglie. Sono
la parte piu' utile dell'articolo.

"Kriya yoga" e "campane" stanno sopra l'80% con pochi frammenti, e
quello che resta e' elenco legittimo.

La metrica ha un punto cieco sulle strutture comparative. Non riscrivo
un articolo per far salire un mio numero.

    venv/bin/python scripts/rf6_voce_narrativa_ultimi_due.py [--dry-run]
"""
import asyncio
import os
import re
import sys
from datetime import datetime, timezone

STRESS = "pratiche-olistiche-contro-stress-cosa-funziona"
IVA = "partita-iva-operatore-olistico-fiscalita-guida"

MEDIT = "/blog/meditazione-per-chi-inizia-guida-semplice"
MINDFUL = "/blog/mindfulness-cose-mbsr-come-funziona"
BREATH = "/blog/breathwork-cose-tecniche-benefici"
YOGA = "/blog/yoga-cose-da-dove-viene-come-cominciare"
CAMMINARE = "/blog/camminare-bagni-di-foresta-cammini"
CAMPANE = "/blog/campane-tibetane-benefici-come-funzionano"
REIKI = "/blog/reiki-cose-come-funziona-una-sessione"
MASSAGGIO = "/blog/massaggio-olistico-tipi-cosa-aspettarsi"
KIT = "/blog/kit-pratiche-quotidiane-15-minuti"
SERIO = "/blog/come-capire-se-un-operatore-olistico-e-serio"
DOMANDE = "/blog/domande-da-fare-prima-di-prenotare-un-ritiro"
PREZZO = "/blog/prezzo-giusto-ritiro-come-calcolarlo"
PROMO = "/blog/come-promuovere-un-ritiro-e-riempire-i-posti"

TITOLO_S = "Pratiche contro lo stress: cosa funziona secondo la ricerca"
DESCR_S = (
    "Cosa fa lo stress al corpo, le pratiche con le prove più solide, quelle "
    "promettenti, come scegliere la tua e quando serve un professionista."
)

CONTENUTO_S = f"""\
Nessuno arriva a un bagno di gong per curiosità intellettuale.

Ci si arriva perché da qualche mese si dorme male, perché la mascella al mattino è contratta, perché una discussione banale ha prodotto una reazione sproporzionata e te ne sei accorto. Lo stress è la porta da cui quasi tutti entrano in questo mondo, e la domanda che si portano dietro è ragionevole: fra tutte le pratiche che promettono di aiutare, quali funzionano?

Questa guida risponde guardando cosa dicono gli studi. Prima però conviene capire cosa stiamo cercando di spegnere, perché è la cosa che spiega perché pratiche diversissime producono effetti simili.

## Cosa fa lo stress al corpo

Lo stress non è un'emozione, è una risposta fisiologica.

Davanti a una minaccia il sistema nervoso simpatico accelera tutto insieme: battito, respiro, tensione muscolare, cortisolo. È un meccanismo perfetto per scappare da un pericolo e pessimo per rispondere alle email, perché la minaccia moderna non arriva e se ne va — resta, e il sistema resta acceso con lei.

La buona notizia è che esiste anche il pedale del freno. Si chiama sistema parasimpatico, ed è quello che governa il riposo e la digestione. Quasi tutte le pratiche che funzionano hanno una cosa in comune: **lo attivano deliberatamente**. È il motivo per cui un'ora di yoga, dieci minuti di respiro lento e una camminata nel bosco arrivano allo stesso posto da tre strade diverse — rallentano un sistema progettato per correre.

## Le pratiche con le prove più solide

**La meditazione e la mindfulness** sono l'area più studiata in assoluto. I programmi strutturati, come il protocollo MBSR di otto settimane, mostrano riduzioni misurabili di stress percepito e ansia in decine di studi controllati. Gli effetti sono moderati e non miracolosi, e crescono con la costanza più che con la durata delle sessioni. Se parti da zero, la [guida per chi comincia]({MEDIT}) spiega il minimo indispensabile; se ti interessa il protocollo, ne parliamo [nel dettaglio]({MINDFUL}).

**La respirazione lenta e controllata** è il collegamento più diretto con il parasimpatico che esista: bastano pochi minuti di respiro rallentato per abbassare in modo misurabile battito e pressione. È la pratica con il miglior rapporto fra sforzo e beneficio dell'intero elenco, e non chiede né tempo né soldi né una sala. È anche la porta d'ingresso al [mondo del breathwork]({BREATH}).

**Lo yoga** mette insieme movimento, respiro e attenzione, e mostra prove buone su stress, ansia lieve e qualità del sonno. Il suo vantaggio, però, è meno ovvio di quello che sembra e riguarda l'aderenza: una pratica che coinvolge il corpo si mantiene più facilmente di una puramente mentale, e una pratica mantenuta batte una pratica migliore abbandonata. Il quadro d'insieme sta [qui]({YOGA}).

**Il tempo passato nella natura** ha alle spalle più numeri di quanto la sua gratuità lasci pensare: le ricerche documentano riduzioni di cortisolo e pressione dopo anche solo venti o trenta minuti in un bosco o in un parco, e una soglia settimanale ricorrente intorno alle due ore. Ne abbiamo scritto in [camminare come pratica]({CAMMINARE}).

**Il massaggio** è fra le pratiche a mediazione corporea con la letteratura più consistente, soprattutto su dolore muscoloscheletrico, ansia e sonno. Le tecniche, e il confine fra benessere e atto sanitario, stanno nella [guida dedicata]({MASSAGGIO}).

E poi ci sono i due pilastri poco esotici che moltiplicano tutto il resto: **il sonno e il movimento regolare**. Nessuna pratica compensa un sonno cronicamente sacrificato, e l'attività fisica resta uno dei più potenti regolatori dell'umore documentati. Chi ha entrambi in ordine ottiene di più da qualsiasi altra cosa in questa pagina.

## Le pratiche promettenti, con ricerca più giovane

**Il suono e i bagni sonori** producono un rilassamento profondo e immediato per moltissime persone, e questo è reale. Gli studi specifici però sono ancora pochi e piccoli: [gong e campane]({CAMPANE}) vanno vissuti come un'ottima esperienza con aspettative oneste.

**Le pratiche energetiche**, dal [reiki]({REIKI}) in poi, hanno documentato il rilassamento riferito da chi le riceve; quello che non ha oggi conferme è l'efficacia specifica oltre l'effetto del contesto, dell'attenzione e del tocco. Sono esperienze di benessere, non terapie, e chi le pratica con serietà lo dice per primo.

## Come scegliere la tua

C'è una cosa che la ricerca dice e che suona controintuitiva: **la pratica migliore non è quella con più studi alle spalle, è quella che fai davvero**. L'aderenza batte l'eleganza, e una tecnica mediocre praticata ogni giorno vale più di una eccellente provata tre volte.

Da qui, tre domande che restringono il campo in fretta.

**Corpo o mente?** Se stare fermo ti agita, partire dalla meditazione seduta è il modo più veloce per concludere che «non fa per te»: comincia dal movimento, cioè yoga o camminata consapevole. Se invece il corpo è esausto e la testa non si spegne, parti da respiro e suono.

**Da solo o accompagnato?** L'autonomia quotidiana — respiro, meditazione con un timer — costa zero e chiede disciplina. Il gruppo e la guida, cioè un corso o un cerchio, danno la struttura che la volontà da sola spesso non regge. Non c'è una risposta giusta: c'è la tua, e la conosci già.

**Cinque minuti o un'immersione?** I due formati non si escludono. La pratica quotidiana breve costruisce il fondamento, e un'immersione — un fine settimana, un ritiro — crea una discontinuità che a casa non arriva mai. Chi ha fatto entrambe le cose racconta spesso che è stata l'immersione a far smettere la pratica di essere un compito.

Se vuoi cominciare da qualcosa di concreto stasera, il [kit delle pratiche quotidiane]({KIT}) mette in fila sette pratiche brevi spiegate passo per passo.

## Quando le pratiche non bastano

Questa è la sezione più importante dell'articolo, e vale più di tutte le precedenti.

Le pratiche olistiche lavorano bene sullo stress fisiologico e sul carico della vita quotidiana. Ma esistono soglie oltre le quali serve altro, e riconoscerle non è un fallimento del percorso: è il percorso.

Se l'ansia o il peso che senti interferiscono in modo significativo con lavoro, relazioni o sonno **da settimane**, il primo passo giusto è un professionista della salute mentale, non un ritiro. Se compaiono attacchi di panico ricorrenti, pensieri che ti spaventano o un abbassamento profondo del tono dell'umore, quella conversazione va fatta con un medico o uno psicoterapeuta, e va fatta adesso.

Le pratiche possono accompagnare benissimo un percorso clinico — molti terapeuti le raccomandano — ma a fianco, mai al posto.

Un operatore serio conosce questo confine e te lo indica lui stesso, prima che tu glielo chieda. È uno dei criteri con cui selezioniamo chi entra su Aurya, ed è anche uno dei modi più affidabili per [riconoscere chi lavora bene]({SERIO}).

## Il punto, in una frase

Lo stress non si combatte: si disinnesca, insegnando al sistema nervoso la strada di casa.

E le pratiche che funzionano sono quelle che percorri davvero, un respiro alla volta, sapendo cosa possono fare e cosa no.

## Domande frequenti

**Qual è la pratica più veloce per calmarsi in un momento acuto?**
La respirazione con espirazione allungata: inspira contando fino a quattro, espira contando fino a sei o otto, per due o tre minuti. L'espirazione lenta è il segnale di sicurezza più diretto che puoi mandare al tuo sistema nervoso.

**Quanto tempo serve per vedere risultati?**
Gli effetti acuti, cioè la calma dopo una sessione, sono immediati. Quelli strutturali — reattività più bassa, sonno migliore — richiedono in genere dalle quattro alle otto settimane di pratica regolare, anche breve.

**Meglio una pratica sola o combinarne diverse?**
Per iniziare una sola, piccola e quotidiana: la semplicità protegge la costanza. Le combinazioni arrivano da sole quando il fondamento c'è.

**I ritiri anti-stress funzionano?**
Un buon ritiro produce un effetto reale e misurabile su sonno, tono e prospettiva. La domanda giusta è cosa succede dopo: i ritiri migliori ti mandano a casa con una pratica sostenibile, non solo con un bel ricordo. Se ne stai valutando uno, le [domande da fare prima di prenotare]({DOMANDE}) aiutano a capirlo in anticipo.
"""

TITOLO_I = "Partita IVA e fiscalità per operatori olistici: la guida 2026"
DESCR_I = (
    "Quando serve la partita IVA e quando no, il codice ATECO, il "
    "forfettario con un esempio numerico, INPS e la legge 4/2013."
)

CONTENUTO_I = f"""\
C'è un momento preciso in cui la domanda arriva, ed è quasi sempre lo stesso: quando smetti di fare qualche sessione per amiche e cominci a tenere un calendario.

A quel punto ti chiedi se devi aprire la partita IVA, cerchi online, e trovi quasi solo pagine scritte da chi vuole vendertela.

Questa guida prova a fare l'opposto: numeri veri, aggiornati al 2026, e la mappa completa delle opzioni **comprese quelle in cui la partita IVA non serve**. Una premessa doverosa prima di tutto: è un articolo informativo e non sostituisce un commercialista, che resta l'investimento più intelligente dei tuoi primi cinquecento euro di attività. Le norme cambiano, e le cifre vanno sempre verificate aggiornate.

## Ti serve davvero la partita IVA?

Non sempre, e vale la pena capirlo prima di aprirla. Le situazioni sono tre e si distinguono per una parola sola, che è **abitualità**.

**L'attività occasionale** è quella davvero saltuaria: nessuna organizzazione stabile, nessuna continuità. Si opera con la prestazione occasionale, emettendo una ricevuta con ritenuta d'acconto del 20% quando il cliente è un'azienda, e tenendo d'occhio la soglia dei 5.000 euro lordi annui, oltre la quale scattano i contributi INPS.

Il punto critico è proprio quella parola. Se pubblichi un calendario di sessioni, hai un listino e clienti che tornano, la tua attività è abituale — e l'occasionale non è più difendibile davanti a un controllo, indipendentemente da quanto incassi.

**L'attività sportiva dilettantistica** è una strada diversa. Se insegni una disciplina riconosciuta in ambito sportivo, e lo yoga in molti casi lo è, attraverso una ASD o SSD affiliata a un ente riconosciuto, i compensi sportivi dilettantistici godono di una franchigia esente fino a 15.000 euro annui secondo la riforma dello sport. È un mondo con regole proprie e funziona solo se il rapporto con l'ente è genuino: usarlo come schermo per un'attività che è altro è un problema, non una soluzione.

**L'attività abituale** — sessioni regolari, ritiri organizzati, promozione continua — è un'attività professionale e richiede la partita IVA. È il percorso di cui parla il resto di questa guida.

## Il codice ATECO

All'apertura serve indicare il codice attività, e questa è la prima decisione da prendere con qualcuno, non da soli.

Per gli operatori olistici il riferimento più usato è il **96.09.09**, «altre attività di servizi per la persona», che copre le discipline bio naturali e del benessere. Chi ha invece un'attività prevalente di insegnamento — corsi di yoga, formazione — valuta con il commercialista i codici dell'area istruzione, come l'85.51.00.

La scelta non è formale: determina il coefficiente di redditività, cioè quanta parte di quello che incassi viene considerata reddito, e l'inquadramento complessivo. Sbagliarla costa più di quanto costi la consulenza per farla bene.

## Il regime forfettario

Per la quasi totalità degli operatori olistici che partono, il forfettario è la scelta naturale. Le regole 2026, in sintesi:

1. **Limite di ricavi**: 85.000 euro l'anno. Sotto questa soglia resti nel regime.
2. **Coefficiente di redditività**: per il codice 96.09.09 è il 67%. Significa che lo Stato considera reddito imponibile il 67% di quello che incassi, e il restante 33% è forfettariamente considerato costi, senza bisogno di documentarli.
3. **Imposta sostitutiva**: 15%, che scende al **5% per i primi cinque anni** di una nuova attività, se i requisiti di novità sono rispettati.
4. **Contributi INPS**: gli operatori olistici senza cassa professionale si iscrivono alla **Gestione Separata**, con aliquota intorno al 26% calcolata sul reddito imponibile. Il lato buono è che non ci sono quote fisse: paghi in proporzione a quello che guadagni.
5. **Niente IVA in fattura, niente ritenute**: le fatture sono più semplici e i clienti pagano quello che vedono.

## I conti veri, su un primo anno

Un esempio con numeri concreti vale più di qualsiasi spiegazione. Immagina un primo anno da 20.000 euro incassati, codice 96.09.09, forfettario startup.

1. Reddito imponibile: 20.000 × 67% = **13.400 euro**
2. Contributi Gestione Separata: 13.400 × 26,07% = **circa 3.490 euro**
3. Imposta sostitutiva al 5%, calcolata sull'imponibile al netto dei contributi versati: indicativamente **circa 500 euro**
4. Totale fra tasse e contributi: **circa 4.000 euro**, cioè un carico complessivo intorno al 20% di quello che hai incassato

Non è poco, ed è comunque molto meno di quanto la paura fiscale fa immaginare. E i contributi non sono soldi persi: sono la tua pensione e le tue tutele, dalla maternità alla malattia nei limiti della gestione.

## La legge 4/2013

Le discipline olistiche in Italia sono professioni non organizzate in ordini o collegi, regolate dalla legge 4 del 2013, e questo ha quattro conseguenze pratiche.

Non serve un albo per esercitare, ma bisogna operare con correttezza e trasparenza verso il cliente. Nei documenti e nelle comunicazioni professionali va citato il riferimento alla norma, con una dicitura del tipo «professione disciplinata ai sensi della legge n. 4/2013». Le associazioni di categoria offrono attestazioni di qualità facoltative ma preziose, perché portano formazione verificata, un codice deontologico e credibilità verso il pubblico.

E poi c'è il confine da non superare mai: niente atti medici, niente diagnosi, niente promesse di cura. È la linea che protegge te quanto chi accompagni, e su cosa comporta esattamente abbiamo scritto [qui]({SERIO}).

## I quattro errori più costosi

**Restare occasionali per anni.** Con un calendario pubblico di eventi l'abitualità è evidente a chiunque guardi, e la regolarizzazione a posteriori costa molto più di quanto sarebbe costata la partita IVA.

**Incassare senza tracciabilità.** Contanti e bonifici su conti personali senza documentazione sono il modo più veloce per trasformare un controllo ordinario in un problema. Ogni incasso deve avere il suo documento, sempre.

**Non accantonare.** Tasse e contributi arrivano l'anno dopo, tutti insieme, con il meccanismo di saldo e acconto — ed è lì che le attività giovani vanno in crisi. La regola che salva è accantonare fra il 25 e il 30% di ogni incasso su un conto separato, dal primo giorno e senza eccezioni.

**Scegliere l'ATECO leggendo un blog**, questo compreso. Il codice giusto dipende dal tuo mix di attività, ed è una conversazione da mezz'ora con un commercialista.

## La tracciabilità è la vera semplificazione

C'è un filo che unisce tutto questo articolo: un'attività fiscalmente serena è quella in cui ogni prenotazione, ogni caparra e ogni incasso hanno una traccia ordinata.

Non è una questione di software. È l'abitudine di registrare le cose quando succedono invece di ricostruirle a memoria a marzo, quando il commercialista chiede e tu apri una cartella di screenshot.

In pratica significa tre cose: un conto separato da quello personale, le caparre incassate con un metodo tracciabile, e le condizioni di cancellazione scritte prima del pagamento. Quest'ultima sembra una questione commerciale e invece è anche contabile, perché un rimborso senza una regola concordata diventa una discussione, e la discussione lascia il segno anche nei conti.

Se stai costruendo i tuoi primi ritiri, leggi anche [come calcolare il prezzo]({PREZZO}) e [come riempire i posti]({PROMO}).

## Domande frequenti

**Quanto costa aprire e tenere la partita IVA?**
L'apertura è gratuita, online o tramite commercialista. Il costo reale è la gestione: un commercialista per un forfettario costa in genere fra i 300 e i 600 euro l'anno.

**Posso aprire la partita IVA mentre sono dipendente?**
Nella maggior parte dei casi sì, salvo clausole di esclusività nel contratto. Il forfettario resta possibile se il reddito da lavoro dipendente non supera i limiti previsti: la soglia aggiornata va verificata con il commercialista.

**Devo fare lo scontrino o la fattura?**
Il forfettario emette fattura, anche semplificata. L'obbligo di fatturazione elettronica riguarda anche i forfettari: serve un software di fatturazione, e molti costano pochi euro al mese.

**Le attestazioni delle associazioni sono obbligatorie?**
No, sono facoltative. Ma la formazione certificata e l'appartenenza a un'associazione seria sono un segnale di fiducia che il pubblico riconosce sempre di più.

**Quanto devo accantonare ogni mese?**
Fra il 25 e il 30% di ogni incasso, su un conto separato. È la singola abitudine che distingue chi supera il secondo anno da chi si trova con una cartella e nessuna liquidità.
"""

PEZZI = [
    (STRESS, TITOLO_S, DESCR_S, CONTENUTO_S),
    (IVA, TITOLO_I, DESCR_I, CONTENUTO_I),
]

# Restano sotto l'85% per scelta: la loro struttura E' l'informazione.
PER_SCELTA = {
    "domande-da-fare-prima-di-prenotare-un-ritiro":
        "lista di controllo che si consulta prima di scrivere una mail",
    "differenze-tipi-di-yoga-hatha-vinyasa-ashtanga-yin-kundalini":
        "tabella comparativa: stessi tre criteri ripetuti su cinque stili",
}


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
        print(f"{titolo[:50]:52} prosa {q1}% → {q2}%   frammenti {f1} → {f2}   "
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

    print("\n── il Magazine per intero")
    arts = [a async for a in db.articles.find({}, {"_id": 0, "slug": 1,
                                                   "content": 1})]
    righe = sorted(((analizza(a["content"]), a["slug"]) for a in arts))
    sotto = [(q, s, f) for (q, _, f), s in righe if q < 85]
    for q, s, f in sotto:
        nota = PER_SCELTA.get(s)
        print(f"  {s[:46]:48} {q:3}%  {'← per scelta: ' + nota if nota else ''}")
    slugs = {a["slug"] for a in arts}
    rotti = [(a["slug"], l) for a in arts
             for l in re.findall(r"\]\(/blog/([a-z0-9-]+)\)", a["content"])
             if l not in slugs]
    orfani = [a["slug"] for a in arts
              if not any(f"/blog/{a['slug']})" in b["content"]
                         for b in arts if b["slug"] != a["slug"])]
    sopra = sum(1 for (q, _, _), _ in righe if q >= 85)
    print(f"\n  sopra l'85%: {sopra} su {len(arts)}")
    print(f"  sotto per scelta: {sum(1 for _, s, _ in sotto if s in PER_SCELTA)}")
    print(f"  link rotti: {rotti or 'nessuno'}")
    print(f"  vicoli: {orfani or 'nessuno'}")
    print(f"  TOTALE: {len(arts)} articoli, "
          f"{sum(len(a['content'].split()) for a in arts)} parole")

    if dry_run:
        print("\n--dry-run: nessuna scrittura")


if __name__ == "__main__":
    asyncio.run(main("--dry-run" in sys.argv))
