"""ES3 — i cerchi di donne, e le ultime tre voci in prima persona.

DUE COSE INSIEME perche' sono lo stesso problema.

L'ESPANSIONE. "Cerchi di donne" aveva 732 parole ed era il solo pezzo
della categoria femminile. Restava sulla superficie: cos'e', come si
svolge, quanto costa. Mancava tutto quello che una donna vuole sapere
prima di entrare in una stanza con dieci sconosciute, e cioe' la
riservatezza come funziona davvero, cosa succede se ci si commuove,
chi facilita e con quale formazione (in un campo dove la formazione
non e' regolata da nessuno), e quali sono i cerchi da evitare.

LA VOCE. Tre articoli parlavano ancora in prima persona da praticante:
una donna che racconta il proprio primo cerchio, un'astrologa che dice
"io racconto cio' che la carta suggerisce", un lettore di tarocchi con
"i tarocchi che pratico io". Con la firma collettiva quelle righe
diventano rivendicazioni di Aurya, e nel caso dei cerchi la cosa
finiva perfino nella meta descrizione: "Il racconto di una
facilitatrice", stampato nei risultati di ricerca.

E' lo stesso difetto gia' corretto su reiki, breathwork, campane e
gong. Questi erano gli ultimi tre.

    venv/bin/python scripts/es3_cerchi_e_voce.py [--dry-run]
"""
import asyncio
import os
import re
import sys
from datetime import datetime, timezone

CERCHI = "cerchi-di-donne-cosa-sono-come-funzionano"
SERIO = "/blog/come-capire-se-un-operatore-olistico-e-serio"
MEDIT = "/blog/meditazione-per-chi-inizia-guida-semplice"
TAROCCHI = "/blog/tarocchi-oracoli-strumento-evolutivo"
DOMANDE = "/blog/domande-da-fare-prima-di-prenotare-un-ritiro"

TITOLO = "Cerchi di donne: cosa sono, come funzionano, come trovarne uno"
DESCRIZIONE = (
    "Cosa succede in un cerchio, come funziona la riservatezza, chi lo "
    "facilita, quanto costa e come si riconosce un cerchio condotto bene."
)

CONTENUTO = f"""\
Un cerchio di donne, visto da fuori, è difficile da collocare: non è un corso, non è una terapia di gruppo, non è un'uscita fra amiche. E chi lo sente nominare per la prima volta di solito lo immagina più esoterico di quanto sia.

Questa guida risponde alle domande che si fanno prima del primo cerchio: cosa succede dentro, come funziona la riservatezza, chi lo conduce, quanto costa e come si riconosce un cerchio condotto bene.

## Cos'è un cerchio di donne

È un incontro guidato da una facilitatrice in cui un gruppo di donne si riunisce per condividere, ascoltare e praticare insieme. La forma circolare non è un dettaglio: nel cerchio non c'è una cattedra, non c'è chi sta sopra e chi sta sotto. Ogni voce ha lo stesso spazio.

È una forma che attraversa quasi tutte le culture — dalle tende rosse delle tradizioni mediorientali ai cerchi delle donne native americane, fino ai gruppi di parola del femminismo del Novecento. La versione contemporanea intreccia questi fili con pratiche di consapevolezza recenti, e vale la pena saperlo: **non è una tradizione unica tramandata intatta**, è un incontro fra tradizioni diverse e un bisogno molto attuale.

Il bisogno è riconoscibile: uno spazio dove nessuno chiede di essere performanti, e dove parlare non comporta ricevere consigli.

## Come si svolge un incontro

Ogni facilitatrice ha il suo stile, ma la struttura ricorre.

**L'apertura.** Si crea lo spazio: una candela, un centro, un momento di silenzio o una breve [meditazione]({MEDIT}) per arrivare anche con l'attenzione, non solo col corpo.

**Il patto.** In un cerchio condotto bene, all'inizio si dicono le regole ad alta voce: quello che viene detto resta nel cerchio, non si interrompe, non si danno consigli, si può passare. Se questo momento manca, mancano le fondamenta.

**Il tema.** Un filo conduttore proposto dalla facilitatrice: la ciclicità, il lasciar andare, i confini, la rinascita. Le pratiche dell'incontro si sviluppano intorno a quello.

**Il giro di condivisione.** Il cuore. Chi vuole parla, senza essere interrotta e senza ricevere consigli non richiesti. Le altre ascoltano, e quell'ascolto pieno è già la cosa che le persone tornano a cercare. Spesso si usa un oggetto che passa di mano: chi lo tiene parla, le altre tacciono.

**La pratica.** A seconda del cerchio: scrittura, movimento, meditazione, rituali stagionali, lavoro con la luna o con il ciclo. Niente è obbligatorio.

**La chiusura.** Si chiude lo spazio, spesso con un gesto condiviso.

Un incontro dura in genere fra le due e le tre ore.

## La riservatezza, come funziona

È la regola che rende possibile tutto il resto, ed è utile sapere cosa significa in pratica.

**Quello che viene detto nel cerchio non esce dal cerchio.** Non si racconta fuori, nemmeno in forma anonima, nemmeno alla propria migliore amica.

**Non si nomina chi c'era.** Incontrare per strada una donna conosciuta in un cerchio e non nominare il cerchio davanti ad altri è parte del patto.

**Non si riprende e non si fotografa** durante la condivisione. Un cerchio che fa foto per i social durante il giro di parola ha un problema di priorità.

**Non si torna sull'argomento dopo**, a meno che non sia lei ad aprirlo. Chiedere «come è andata poi con tuo padre?» la settimana dopo, fuori dal cerchio, è un'invasione anche se nasce da affetto.

## Cosa non è

**Non è una terapia di gruppo.** La facilitatrice non è necessariamente una terapeuta e il cerchio non cura: accompagna. Se stai attraversando una sofferenza importante, il cerchio può affiancare un percorso professionale, mai sostituirlo.

**Non è un club esoterico.** Ci sono cerchi più spirituali e cerchi del tutto laici: la condivisione è il centro, il resto è linguaggio.

**Non è contro nessuno.** Lo spazio fra sole donne serve a creare un'intimità particolare, non a escludere. Esistono anche cerchi di uomini e cerchi misti, con dinamiche diverse.

**Non è un gruppo di amiche.** Ed è il fraintendimento più utile da sciogliere: la forza del cerchio sta proprio nel fatto che le altre non ti conoscono, non hanno una storia con te e non devono gestire le conseguenze di quello che dici.

## Chi facilita, e con quale formazione

Qui va detta una cosa: **facilitare un cerchio non è una professione regolata**. Non esiste un titolo, non esiste un albo, e chiunque può aprire un cerchio domani.

Esistono formazioni serie, di durata molto variabile, che lavorano su conduzione di gruppo, ascolto attivo e gestione delle emozioni intense. E ne esistono di brevissime.

La differenza si vede in una cosa sola: **cosa succede quando qualcuna si rompe**. In un cerchio capita che una condivisione tocchi qualcosa di grosso, e in quel momento chi conduce deve saper restare senza precipitarsi a consolare, tenere il tempo del gruppo, e riconoscere quando una persona ha bisogno di qualcosa che il cerchio non può dare.

Le domande utili prima di iscriversi: da quanto facilita, quante persone accoglie, che formazione ha fatto e con chi, e cosa fa se qualcuna sta male. Valgono [gli stessi criteri]({SERIO}) di chiunque ti accompagni.

## Cosa aspettarsi la prima volta

**Sentirsi osservatrici è normale.** Nessuna facilitatrice seria forza a condividere, e passare è previsto.

**Molte raccontano la stessa parabola:** primo cerchio in silenzio, secondo cerchio due parole, terzo cerchio qualcosa che non sapevano di trattenere.

**Commuoversi è frequente**, e non è un incidente: succede perché per una volta nessuno interrompe.

**Uscire stanche è normale.** Due ore di ascolto pieno costano più di quanto sembri, e conviene non incastrare un impegno subito dopo.

Cosa portare: vestiti comodi, una bottiglia d'acqua, un cuscino se richiesto. Nient'altro.

## Quanto costa

In Italia un cerchio costa in genere fra i 10 e i 30 euro a incontro, spesso con formule a offerta libera o a contributo consapevole. I cerchi dentro un ritiro sono compresi nell'esperienza.

Un percorso a cicli — quattro o otto incontri con lo stesso gruppo chiuso — costa di più e funziona diversamente: il gruppo si conosce, e la profondità cresce di incontro in incontro.

## I cerchi da evitare

Pochi segnali, e piuttosto netti.

**Nessun patto iniziale.** Se le regole non vengono dette, non ci sono.

**La facilitatrice parla per metà del tempo.** Il cerchio non è la sua lezione.

**Si danno consigli.** «Io al posto tuo farei» è esattamente la cosa che il cerchio esiste per non fare.

**Si insiste perché tu parli.** Anche con delicatezza, anche «solo una parola»: il passo deve essere davvero libero.

**Si vende qualcosa alla fine.** Un percorso, una consulenza individuale, un prodotto. Proporlo dopo una condivisione emotiva è approfittare del momento in cui le persone sono più aperte.

**Si promettono guarigioni.** Un cerchio che dichiara di curare traumi o disturbi sta oltrepassando un confine che non gli appartiene.

## Come trovarne uno

I canali sono sparsi: passaparola, gruppi social locali, studi di yoga che ospitano cerchi mensili. Conviene chiedere direttamente nello studio dove pratichi, perché molti cerchi non vengono annunciati da nessun'altra parte.

Se quello che stai valutando è un ritiro del femminile e non un incontro singolo, le domande da fare sono di più e riguardano anche soldi, gruppo e giornata: le abbiamo raccolte [qui]({DOMANDE}).

## Domande frequenti

**Devo parlare per forza?**
No. Il passo è sempre concesso e l'ascolto è partecipazione piena.

**Serve credere in qualcosa?**
No. Esistono cerchi con linguaggio spirituale e cerchi del tutto laici. Se il linguaggio di uno non ti risuona, cercane un altro: la varietà è grande.

**Posso andare se non conosco nessuna?**
È la norma, ed è parte del punto: la forza del cerchio sta nel fatto che le altre non hanno una storia con te.

**E se mi metto a piangere?**
Capita spesso e non è un problema. In un cerchio condotto bene nessuno si precipita a consolarti: ti lasciano il tempo, che è quello che serve.

**Che differenza c'è con la tenda rossa?**
La tenda rossa è una forma specifica legata alla ciclicità femminile, tradizionalmente uno spazio di riposo nei giorni del ciclo. Ogni tenda rossa è un cerchio, non ogni cerchio è una tenda rossa.

**Sono adatti in gravidanza o nel post parto?**
Sì, ed esistono cerchi dedicati a quelle fasi. Conviene dirlo prima alla facilitatrice, perché cambia cosa si propone.

**Cosa succede se incontro per strada una donna del cerchio?**
La si saluta come chiunque. Il patto dice di non nominare il cerchio davanti ad altri e di non tornare su quello che ha condiviso, a meno che non sia lei ad aprirlo.

**Ci sono cerchi con carte o oracoli?**
Alcuni li usano come traccia per la scrittura o la condivisione: sui [tarocchi come strumento riflessivo]({TAROCCHI}) abbiamo scritto a parte.
"""

# le ultime due voci in prima persona, fuori dai cerchi
VOCE = [
    ("lettura-tema-natale-cosa-aspettarsi",
     "Non è un monologo dell'astrologa: è un dialogo. Io racconto ciò che "
     "la carta suggerisce, tu riconosci (o non riconosci) quei temi nella "
     "tua vita. È in questo scambio che la lettura prende senso.",
     "Non è un monologo: è un dialogo. Chi conduce racconta quello che la "
     "carta suggerisce, tu riconosci o non riconosci quei temi nella tua "
     "vita. È in questo scambio che la lettura prende senso, ed è anche il "
     "motivo per cui una lettura registrata e spedita vale molto meno di "
     "un incontro."),

    ("tarocchi-oracoli-strumento-evolutivo",
     "Ogni volta che tiro fuori un mazzo di tarocchi davanti a qualcuno di "
     "nuovo, vedo lo stesso lampo negli occhi: metà curiosità, metà "
     "\"adesso mi dice quando muoio\". E ogni volta comincio dallo stesso "
     "punto: i tarocchi che pratico io non predicono niente. E sono molto "
     "più interessanti così.",
     "Chi tira fuori un mazzo di tarocchi davanti a qualcuno che non li ha "
     "mai visti riconosce sempre lo stesso sguardo: metà curiosità, metà "
     "«adesso mi dice quando muoio». E chi li usa in senso evolutivo "
     "comincia sempre dallo stesso punto: queste carte non predicono "
     "niente. Sono più interessanti così."),
]


async def main(dry_run: bool) -> None:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from database import db

    doc = await db.articles.find_one({"slug": CERCHI}, {"_id": 0, "content": 1})
    if doc:
        print(f"{TITOLO}\n  prima: {len(doc['content'].split())} parole"
              f"  →  dopo: {len(CONTENUTO.split())} parole"
              f"  (descrizione {len(DESCRIZIONE)} caratteri)")
        if CONTENUTO == doc["content"]:
            print("  gia' aggiornato")
        elif not dry_run:
            await db.articles.update_one({"slug": CERCHI}, {"$set": {
                "title": TITOLO, "description": DESCRIZIONE,
                "content": CONTENUTO, "author_name": "Aurya",
                "related_slugs": [
                    "come-capire-se-un-operatore-olistico-e-serio",
                    "meditazione-per-chi-inizia-guida-semplice",
                    "tarocchi-oracoli-strumento-evolutivo"],
                "updated_at": datetime.now(timezone.utc)}})
            print("  aggiornato")

    print("\n── la voce negli altri due")
    for slug, vecchio, nuovo in VOCE:
        d = await db.articles.find_one({"slug": slug}, {"_id": 0, "content": 1})
        if not d:
            print(f"  ASSENTE {slug}")
        elif nuovo in d["content"]:
            print(f"  gia' a posto {slug[:40]}")
        elif vecchio in d["content"]:
            if not dry_run:
                await db.articles.update_one({"slug": slug}, {"$set": {
                    "content": d["content"].replace(vecchio, nuovo, 1)}})
            print(f"  riscritto in terza persona {slug[:40]}")
        else:
            print(f"  NON TROVATO in {slug[:40]}")

    print("\n── prima persona rimasta nel Magazine")
    P = re.compile(r"(?<![\w'’])(io |mi sono|ho (?:visto|provato|ricevuto|"
                   r"imparato|conosciuto|accompagnat|condott)|sono (?:un'|un )?"
                   r"(?:operatric|insegnant|facilitatric)|la mia (?:pratica|"
                   r"esperienza|formazione)|quando (?:conduco|accompagno))",
                   re.I)
    n = 0
    async for a in db.articles.find({}, {"_id": 0, "slug": 1, "content": 1,
                                         "description": 1}):
        t = a["content"] + "\n" + (a.get("description") or "")
        for h in P.finditer(t):
            i = max(0, h.start() - 55)
            print(f"  {a['slug'][:32]:34} …{t[i:h.end() + 55]}…"
                  .replace("\n", " "))
            n += 1
    print(f"  occorrenze: {n or 'nessuna'}")

    if dry_run:
        print("\n--dry-run: nessuna scrittura")


if __name__ == "__main__":
    asyncio.run(main("--dry-run" in sys.argv))
