"""PC2 — espansione della guida al Reiki (767 → ~1900 parole).

PERCHE' PROPRIO QUESTO. E' la pratica piu' cercata fra quelle che
trattiamo ed e' la testa del cluster "energia", che oggi ha quattro
pezzi e la media di parole piu' bassa del Magazine. Sotto le mille
parole non si compete: allungare questo vale piu' che aggiungerne un
quinto sottile.

TRE COSE CHE VANNO SISTEMATE, NON SOLO ALLUNGATE.

1. La versione precedente era in PRIMA PERSONA: "quando dico che sono
   un'operatrice Reiki", "quello che posso dirti dalla mia
   esperienza". Con la firma collettiva decisa il 2/8 quelle frasi
   diventano una rivendicazione di Aurya: e' lo stesso problema
   sollevato dal founder sul rebirthing. Il testo passa alla terza
   persona e le esperienze diventano quello che sono, cioe' quello che
   le persone riportano.
2. C'era una sezione "Reiki e ritiri" che promuoveva ritiri che oggi
   non esistono, e un link a /cerca-ritiro (che e' un rimando alla
   Lettera). Via entrambi.
3. La ricerca era liquidata in una riga dentro le domande frequenti.
   Diventa una sezione con la sua onesta': cosa si osserva, perche' e'
   difficile da studiare, e cosa NON si puo' dire.

I collegamenti interni gia' aggiunti da PE7 sono conservati.

    venv/bin/python scripts/pc2_espansione_reiki.py [--dry-run]
"""
import asyncio
import os
import sys
from datetime import datetime, timezone

SLUG = "reiki-cose-come-funziona-una-sessione"
TITOLO = "Reiki: cos'è, come funziona una sessione e cosa si sente"
DESCRIZIONE = (
    "Origini, livelli, come si svolge una seduta, cosa si sente, cosa "
    "dice la ricerca e come scegliere chi la conduce."
)

CONTENUTO = """\
Il Reiki è una delle pratiche olistiche più diffuse al mondo e una di quelle su cui circolano più idee vaghe. Chi non l'ha mai provato lo immagina come una forma di massaggio, o come qualcosa di religioso. Chi ci si avvicina si trova davanti a un vocabolario — energia, canalizzazione, livelli — che spiega poco di quello che succede in una stanza.

Questa guida racconta la pratica per come si svolge: com'è fatta una sessione, cosa riportano le persone, cosa dice la ricerca e cosa non può dire, e come si riconosce chi la conduce con serietà.

## Cos'è, e cosa significa il nome

Il Reiki è una pratica di imposizione delle mani: chi la conduce appoggia le mani sul corpo di chi la riceve, o le tiene a pochi centimetri, seguendo una sequenza di posizioni. Chi riceve resta vestito e non deve fare niente.

Il nome unisce due parole giapponesi: *rei*, che indica una dimensione universale, e *ki*, l'energia vitale individuale — lo stesso concetto del *qi* cinese o del *prana* della tradizione indiana. Nella cornice della disciplina, l'operatore non trasmette energia propria: fa da tramite.

Questa è la spiegazione che la pratica dà di sé, e vale la pena tenerla distinta da quello che si può osservare, che arriva più avanti.

## Le origini: Giappone, primi del Novecento

La pratica nasce in Giappone negli anni Venti del Novecento dal lavoro di **Mikao Usui**, che sviluppa un metodo di guarigione basato sull'imposizione delle mani e fonda una scuola a Tokyo.

Il passaggio in Occidente avviene attraverso **Hawayo Takata**, una donna hawaiana di origine giapponese che apprende il metodo negli anni Trenta e lo diffonde negli Stati Uniti nei decenni successivi. È da questa linea che discende la maggior parte delle scuole occidentali, quello che oggi viene chiamato Reiki Usui.

Nel frattempo in Giappone sono rimaste linee di trasmissione differenti, e questo spiega perché due operatori formati in tradizioni diverse possano descrivere la pratica in modi che non coincidono del tutto.

## I livelli, e cosa significano

Il Reiki si trasmette per gradi, attraverso quelle che le scuole chiamano armonizzazioni o iniziazioni. I livelli sono tre, con nomi che variano.

**Primo livello.** Abilita a praticare su di sé e su altre persone con il contatto diretto. Si impara la sequenza delle posizioni e si comincia la pratica quotidiana su di sé, che nella maggior parte delle scuole è considerata il fondamento di tutto il resto.

**Secondo livello.** Introduce i simboli e la pratica a distanza. È il livello a cui molti operatori cominciano a lavorare con altre persone in modo regolare.

**Terzo livello o maestria.** Abilita a trasmettere la pratica ad altri, cioè a formare nuovi operatori.

Qui c'è una cosa che conviene sapere prima di scegliere: **i livelli si possono ottenere in tempi molto brevi**. Esistono percorsi che portano alla maestria in pochi fine settimana. Nulla lo vieta, perché la materia non è regolamentata, ma un titolo preso in fretta dice poco sulla capacità di stare accanto a una persona che si commuove sul lettino. Quella si costruisce praticando, per anni.

## Come si svolge una sessione

Una seduta dura fra i quarantacinque e i sessanta minuti.

**L'accoglienza.** Si comincia parlando: come stai, cosa ti porta lì, se ci sono zone di tensione. Un operatore preparato chiede anche di condizioni di salute in corso, gravidanza e terapie. Non è necessario raccontare più di quello che si vuole condividere.

**La sessione.** Ci si sdraia vestiti su un lettino, in un ambiente tranquillo, spesso con una musica di sottofondo. L'operatore appoggia le mani in sequenza — testa, spalle, torace, addome, gambe — restando su ciascuna posizione qualche minuto. Il contatto è leggero e fermo: nessuna manipolazione, nessun massaggio. Chi preferisce non essere toccato può chiedere che le mani restino sollevate, e la pratica funziona allo stesso modo secondo le sue premesse.

**La chiusura.** Qualche minuto di riposo, poi un breve scambio su quello che si è percepito. Un operatore serio ascolta senza interpretare al posto tuo.

## Cosa riportano le persone

Le sensazioni descritte più spesso sono calore nelle zone di contatto, un rilassamento profondo simile allo stato fra veglia e sonno, formicolii leggeri, a volte emozioni che affiorano senza una ragione evidente. Molte persone si addormentano.

La variabilità è la norma: c'è chi descrive esperienze intense e chi soltanto un grande riposo. Nessuna delle due è più corretta dell'altra, e aspettarsi qualcosa di preciso è il modo più rapido per restare delusi.

## Il Reiki a distanza

Dal secondo livello, la pratica prevede sessioni a distanza: l'operatore lavora in un momento concordato mentre chi riceve si trova altrove.

È l'aspetto su cui la disciplina fa l'affermazione più forte e su cui non esistono prove. Vale la pena saperlo prima di prenotare, perché il prezzo di una sessione a distanza è spesso lo stesso di una in presenza, e la parte che le persone descrivono come più preziosa — un'ora in cui qualcuno si occupa di te, in silenzio — a distanza si perde.

## Cosa dice la ricerca

Qui serve precisione, perché è il punto in cui si dicono più cose non vere in entrambe le direzioni.

Gli studi clinici sul Reiki esistono, e alcuni riportano miglioramenti su ansia, percezione del dolore e qualità del sonno. Le revisioni sistematiche però concordano su un punto: **gli studi sono in gran parte piccoli, metodologicamente deboli e difficili da confrontare**, e non permettono di attribuire quei miglioramenti alla pratica in sé.

Il motivo è interessante e vale la pena capirlo. In una sessione di Reiki agiscono insieme almeno quattro cose: un'ora di immobilità, un ambiente silenzioso, il contatto fisico leggero, e l'attenzione esclusiva di una persona. Sono tutti fattori con effetti documentati sul sistema nervoso. Isolare da questi un effetto specifico dell'energia richiede disegni sperimentali difficili da realizzare, e quelli tentati finora non hanno prodotto risultati conclusivi.

La conseguenza pratica è duplice. Chi sostiene che il Reiki curi malattie sta dicendo qualcosa che le prove non sostengono. Chi sostiene che non serva a niente sta ignorando che il rilassamento profondo e il contatto umano fanno qualcosa di misurabile alle persone.

## Quando non è indicato, e il confine da non superare

Il Reiki non ha controindicazioni fisiche note: è una pratica non invasiva, senza manipolazione né sostanze. Le cautele riguardano il contesto, non la tecnica.

**Non sostituisce alcuna cura.** Nessun operatore può fare diagnosi, suggerire di sospendere un farmaco o dire che una pratica cura una malattia: sono atti riservati alle professioni sanitarie, e farli senza titolo è un reato. Se qualcuno lo fa, interrompi il percorso.

**In oncologia e nelle malattie gravi** alcune strutture ospedaliere propongono il Reiki come pratica di accompagnamento, sempre accanto alle terapie e mai al loro posto. Se stai affrontando una malattia, parlane con chi ti ha in cura prima di cominciare.

**Se stai attraversando un momento psicologico difficile**, il Reiki può accompagnare un percorso ma non prenderne il posto: non è una psicoterapia e chi lo conduce non è un terapeuta.

## Quanto costa, e come si sceglie

In Italia una sessione individuale costa in genere fra i quaranta e i settanta euro, con variazioni per città e per esperienza di chi la conduce. Molti operatori propongono cicli di quattro o cinque sedute, perché una sola dà un assaggio dell'esperienza più che un percorso.

Sulla scelta valgono i criteri generali, e abbiamo scritto una guida a parte su [come capire se un operatore è serio](/blog/come-capire-se-un-operatore-olistico-e-serio). I tre che contano di più qui: **da chi e da quanto tempo si è formato**, **cosa chiede prima di cominciare**, e **cosa dice sui limiti** della pratica. Chi risponde a quest'ultima con precisione ha capito il mestiere.

## Domande frequenti

**Il Reiki è riconosciuto scientificamente?**
No. Esistono studi che riportano benefici su ansia e percezione del dolore, ma sono in gran parte piccoli e metodologicamente deboli, e non permettono di attribuire l'effetto alla pratica in sé invece che al rilassamento e al contatto umano. Va inteso come pratica di accompagnamento, mai come cura.

**Quanto costa una sessione?**
In Italia in genere fra i quaranta e i settanta euro, secondo città ed esperienza. Chiedi sempre prima anche la durata e le regole di disdetta.

**Devo togliermi i vestiti?**
No. Il Reiki si riceve vestiti, sdraiati o seduti.

**Quante sessioni servono?**
Una dà un assaggio dell'esperienza. Chi cerca un percorso lavora per cicli, di solito di quattro o cinque sedute ravvicinate.

**Il Reiki è una religione?**
No, e non richiede alcuna fede. Nasce in un contesto culturale giapponese ma non prevede credenze né appartenenze, e viene praticato da persone di ogni orientamento.

**Posso praticarlo su me stesso?**
Sì, dal primo livello. Nella maggior parte delle scuole l'auto-trattamento quotidiano è considerato il fondamento della pratica, prima ancora del lavoro su altre persone.
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
