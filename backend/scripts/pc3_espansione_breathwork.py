"""PC3 — espansione della guida al breathwork (831 → ~1800 parole).

PERCHE'. E' la testa della famiglia in cui ora vive il rebirthing, e
quel pezzo si appoggia a questo per la fisiologia: se la spiegazione
sta qui una volta per tutte, gli articoli figli possono citarla invece
di ripeterla. E' anche il cluster che cresce di piu' nei prossimi mesi.

GLI STESSI TRE DIFETTI DEL REIKI, corretti allo stesso modo.
1. Prima persona: "Racconto quello che vedo accompagnando le persone".
   Con la firma collettiva e' una rivendicazione di Aurya. Via.
2. "merita di essere raccontato con onesta'", "cosa fa davvero", "Con
   onesta', come sempre", "la parte che nessuno ti dice": qualificatori
   che si auto-elogiano, vietati dalla revisione di voce.
3. Chiudeva promuovendo un marketplace che non e' acceso, con link a
   /cerca-ritiro.

COSA SI AGGIUNGE. La fisiologia spiegata per bene (perche' formicolano
le mani, e perche' passa da solo), le tecniche una per una con
istruzioni utilizzabili, la differenza fra i due rami detta in modo che
resti, le controindicazioni divise fra i due rami invece che in blocco,
e come si sceglie chi conduce.

    venv/bin/python scripts/pc3_espansione_breathwork.py [--dry-run]
"""
import asyncio
import os
import sys
from datetime import datetime, timezone

SLUG = "breathwork-cose-tecniche-benefici"
TITOLO = "Breathwork: cos'è, le tecniche principali, benefici e controindicazioni"
DESCRIZIONE = (
    "Le tecniche lente e quelle intense, cosa succede nel corpo, cosa dice "
    "la ricerca, le controindicazioni e come scegliere chi conduce."
)

CONTENUTO = """\
Respiriamo circa ventimila volte al giorno senza accorgercene. Il breathwork parte da un'osservazione semplice: quel gesto automatico è anche l'unica funzione del sistema nervoso autonomo che possiamo governare a piacere. Il cuore non lo comandiamo, la digestione nemmeno. Il respiro sì.

Da lì in poi la famiglia si allarga, e la prima cosa da capire è che al suo interno ci sono pratiche che fanno cose opposte.

## Due rami che vale la pena non confondere

**Le tecniche di regolazione.** Respirazione diaframmatica, coerenza cardiaca, respiro quadrato, buona parte del pranayama. Rallentano il respiro e abbassano l'attivazione. Sono adatte a quasi tutti, si praticano da soli e gli effetti si misurano in minuti.

**Le tecniche esperienziali.** Respirazione circolare connessa, olotropica, [rebirthing](/blog/rebirthing-cose-come-funziona-una-sessione). Amplificano volontariamente il respiro per periodi lunghi e portano a stati di coscienza non ordinari. Vanno fatte con un facilitatore e hanno controindicazioni precise.

Chiamarle con lo stesso nome è comodo e fuorviante: una abbassa, l'altra alza prima di lasciar cadere. Sapere in quale delle due stai entrando è la cosa più utile di questa guida.

## Cosa succede nel corpo

Vale per entrambi i rami, e conoscerlo cambia l'esperienza.

Il respiro regola la quantità di **anidride carbonica** nel sangue, e l'anidride carbonica ne regola l'acidità. Quando respiri più del necessario ne elimini più di quanta ne produci: il sangue diventa temporaneamente più alcalino. Questo ha due effetti immediati e documentati. I nervi periferici diventano più eccitabili — da qui **formicolii a mani, piedi e labbra, e talvolta l'irrigidimento delle dita**. E i vasi cerebrali si restringono, il che contribuisce alla sensazione di testa leggera o distante.

Sono effetti meccanici e transitori: **si risolvono da soli rallentando il respiro**, e un facilitatore preparato lo dice all'inizio, non quando succede. Non sono un segno che qualcosa si sta sbloccando, e conoscerli toglie lo spavento senza togliere valore a quello che si prova.

All'estremo opposto, respirare lentamente e allungare l'espirazione stimola il nervo vago e sposta l'equilibrio verso il sistema parasimpatico, quello del riposo e della digestione. È il motivo per cui sei respiri al minuto calmano: non è suggestione, è fisiologia.

## Le tecniche di regolazione, una per una

**Respirazione diaframmatica.** Respirare nella pancia invece che nel petto. Una mano sull'addome, una sul torace: si muove la prima. Cinque minuti bastano per sentire la differenza, ed è la base di tutto il resto.

**Coerenza cardiaca.** Circa sei respiri al minuto — cinque secondi di inspirazione, cinque di espirazione — per cinque minuti, due o tre volte al giorno. È fra le tecniche più studiate per la gestione dello stress e agisce sulla variabilità della frequenza cardiaca.

**Respiro quadrato.** Inspiro, pausa, espiro, pausa, quattro tempi uguali di quattro secondi. Serve a ritrovare lucidità sotto pressione ed è usato anche in contesti operativi e sportivi.

**Espirazione allungata.** Il principio più semplice e più efficace: se l'espirazione dura il doppio dell'inspirazione, l'attivazione scende. Quattro dentro, otto fuori.

**Pranayama.** Le tecniche di respiro dello yoga: una tradizione vasta, dalla narice alternata ai respiri energizzanti, con effetti molto diversi fra loro. Alcune sono lente, altre sono a tutti gli effetti tecniche intense: è il ramo dove la distinzione di questa guida serve di più, e conviene impararle con un insegnante.

## Le tecniche esperienziali

**Respirazione circolare connessa.** Inspirazione ed espirazione collegate senza pause, per quarantacinque o novanta minuti, sdraiati, spesso con musica e sempre con qualcuno accanto. È la tecnica alla base delle sessioni di rebirthing e, con differenze di contesto, dell'olotropica.

Le persone descrivono formicolii, ondate di caldo o freddo, contrazioni involontarie, e un'emotività che arriva in fretta: pianto, riso, immagini, ricordi. Molti raccontano di aver mosso qualcosa che era fermo da tempo.

È un'esperienza, non un rilassamento, ed è il motivo per cui richiede un contesto protetto e qualcuno che sappia riconoscere quando fermarsi.

## Cosa dice la ricerca

I due rami hanno basi di evidenza diverse, e vale la pena tenerli separati anche qui.

**Sulle tecniche lente le prove sono solide.** La respirazione lenta e diaframmatica riduce in modo misurabile gli indicatori fisiologici dello stress, migliora la variabilità cardiaca e ha effetti documentati su ansia e qualità del sonno. È uno degli interventi non farmacologici più studiati degli ultimi vent'anni.

**Sulle tecniche intense la ricerca è più giovane.** Esistono studi che riportano miglioramenti sul benessere percepito, ma i campioni sono piccoli e i disegni sperimentali difficili da controllare, come accade per tutte le pratiche in cui contano ambiente, aspettativa e presenza di un facilitatore. Quello che è ben descritto è la fisiologia dell'iperventilazione, cioè il meccanismo, non l'effetto terapeutico.

In pratica: il respiro lento è uno strumento di regolazione quotidiana su cui si può contare; quello intenso è un'esperienza da prendere con rispetto e senza aspettative di guarigione.

## Controindicazioni

Le due famiglie hanno cautele diverse, e metterle nello stesso elenco confonde.

**Le tecniche lente** sono accessibili a quasi tutti. L'unica accortezza riguarda chi ha patologie respiratorie serie o attacchi di panico legati al respiro, dove conviene cominciare accompagnati.

**Le tecniche intense** sono sconsigliate, o richiedono il via libera di un medico, in caso di: gravidanza, patologie cardiovascolari, ipertensione non controllata, epilessia, aneurismi, distacco di retina, glaucoma, asma grave, disturbi psichiatrici come psicosi e disturbo bipolare, interventi chirurgici recenti, osteoporosi grave.

Un facilitatore preparato chiede tutto questo **prima** della sessione, con un colloquio o un questionario. Se nessuno chiede niente, quella è l'informazione più importante che riceverai su quel contesto.

E vale la regola generale: una pratica di respiro può accompagnare un percorso di cura, mai sostituirlo.

## Come scegliere chi conduce

I criteri sono gli stessi che valgono per il resto — li abbiamo raccolti in [come capire se un operatore è serio](/blog/come-capire-se-un-operatore-olistico-e-serio) — con tre domande specifiche per questo campo.

**Cosa fai se qualcuno va in crisi?** Chi ha esperienza ha una risposta pronta e concreta.

**Quante persone segui per sessione?** Nelle sessioni intense di gruppo il rapporto conta: un facilitatore per quindici persone non riesce a vedere tutti.

**Posso fermarmi quando voglio?** La risposta giusta è sì, sempre, ed è utile sentirsela dire prima.

## Come cominciare

Dal ramo lento, che si pratica da soli e non ha bisogno di nessuno: cinque minuti di respirazione diaframmatica al giorno, o la coerenza cardiaca due volte al giorno, magari agganciati a una [pratica di meditazione](/blog/meditazione-per-chi-inizia-guida-semplice) che hai già.

Quando arriva la curiosità per l'esperienziale, la strada è una sessione di gruppo guidata: in Italia costano in genere fra i venticinque e i sessanta euro, e permettono di capire se quella intensità fa per te prima di impegnarsi in un percorso individuale.

## Domande frequenti

**Il breathwork è pericoloso?**
Le tecniche lente no. Quelle intense hanno controindicazioni precise, elencate sopra, e vanno fatte con un facilitatore: i fenomeni che si presentano (formicolii, irrigidimento delle mani) sono transitori e si risolvono rallentando il respiro.

**Posso praticarlo da solo?**
Le tecniche di regolazione sì, ed è il modo consigliato di cominciare. La respirazione circolare prolungata no: serve qualcuno che osservi e sappia intervenire.

**Quanto tempo serve per sentire un effetto?**
Sulle tecniche lente, pochi minuti per l'effetto immediato e due o tre settimane di pratica quotidiana per un cambiamento stabile. Una sessione intensa si sente subito, ma è un'altra cosa.

**Che differenza c'è fra breathwork e pranayama?**
Il pranayama è il ramo di tecniche di respiro che appartiene alla tradizione dello yoga, con una cornice filosofica propria. Il breathwork è il termine ombrello contemporaneo, che comprende anche pratiche nate in Occidente nel Novecento.

**Perché durante una sessione mi si irrigidiscono le mani?**
È l'effetto dell'alcalosi respiratoria descritta sopra: temporaneo, meccanico, e reversibile rallentando il respiro. Non è un segnale che qualcosa si stia sbloccando.

**Il breathwork sostituisce la psicoterapia?**
No. Può accompagnare un percorso, ma chi conduce una sessione di respiro non è un terapeuta e la pratica non è un trattamento per un disturbo.
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
        "updated_at": datetime.now(timezone.utc),
    }})
    print("\naggiornato (slug e data di pubblicazione invariati)")


if __name__ == "__main__":
    asyncio.run(main("--dry-run" in sys.argv))
