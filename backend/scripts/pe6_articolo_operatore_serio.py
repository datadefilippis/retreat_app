"""PE6 — primo articolo del pilastro "Scegliere e fidarsi".

E' il territorio del brand: in Italia nessuno spiega a chi cerca come
si riconosce chi lavora bene, e questo e' l'unico cluster il cui
sbocco naturale e' la rete invece della lettera. Inaugura anche la
categoria "scegliere" (modello + palette + geometria del bivio).

VERIFICHE FATTE PRIMA DI SCRIVERE, perche' qui si parla di legge e di
salute e un errore costa la fiducia di tutto il sito:
- legge 4/2013: disciplina le professioni NON organizzate in ordini o
  collegi; obbliga a indicare il riferimento alla legge nei documenti;
  le associazioni possono essere iscritte in un elenco tenuto dal
  ministero e rilasciare un'attestazione di qualita' dei SERVIZI. Non
  crea un albo e non abilita ad atti sanitari.
- esercizio abusivo della professione: art. 348 del codice penale.
- psicologo e psicoterapeuta: professioni con albo (legge 56/1989).

Il testo non dice mai a chi legge cosa deve scegliere: gli da' gli
strumenti per chiedere. E' la differenza fra una guida e una vendita.

    venv/bin/python scripts/pe6_articolo_operatore_serio.py [--dry-run]
"""
import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone

SLUG = "come-capire-se-un-operatore-olistico-e-serio"
TITOLO = "Come capire se un operatore olistico è serio: cosa guardare"
DESCRIZIONE = (
    "Attestati e sigle: cosa valgono in Italia, i segnali che contano, "
    "le domande da fare al primo contatto e quando serve un medico."
)
CATEGORIA = "scegliere"

CONTENUTO = """\
Cerchi «reiki» o «costellazioni familiari» nella tua città e trovi trenta profili. Hanno tutti foto curate, tutti parlano di ascolto e di percorso, molti espongono una sigla che non hai mai sentito. Nessuno sta mentendo, e proprio per questo non sai come scegliere: mancano gli appigli, non la buona fede.

Questa guida mette in fila gli appigli che esistono. Alla fine non ci sarà un nome consigliato: ci saranno le domande da fare e il modo di leggere le risposte.

## Perché è difficile: in Italia non c'è un albo

Le professioni olistiche in Italia rientrano fra le **professioni non organizzate in ordini o collegi**, disciplinate dalla **legge 4 del 14 gennaio 2013**. È la stessa cornice di molte altre attività: significa che non esiste un albo da consultare, né un esame di Stato, né un ente pubblico che verifichi la competenza di chi la esercita.

La legge però qualcosa la stabilisce, ed è utile conoscerlo.

**Chi esercita deve dichiararlo.** In ogni documento e in ogni comunicazione verso il pubblico, un professionista che rientra in questa legge deve indicare gli estremi della norma. Se trovi scritto «professionista di cui alla legge n. 4 del 14 gennaio 2013», stai leggendo una persona che sa in quale cornice lavora: è un segnale piccolo ma reale.

**Le associazioni possono essere in un elenco pubblico.** Le associazioni professionali che rispettano certi requisiti vengono iscritte in un elenco tenuto dal ministero competente e consultabile online. Un'associazione presente in quell'elenco è verificabile; una sigla che non compare da nessuna parte è solo una sigla.

**L'attestato riguarda i servizi, non la persona.** Le associazioni iscritte possono rilasciare un'attestazione di qualità e qualificazione professionale dei servizi. È una cosa diversa da un'abilitazione: non certifica che quella persona sia brava, certifica che rispetta gli standard dichiarati da quell'associazione. Sapere questa differenza cambia il peso che dai a un logo su un sito.

## Il confine che nessuno può superare

C'è una linea che vale per tutti, e conoscerla protegge chi cerca più di qualsiasi attestato.

**Nessun operatore olistico può fare diagnosi, prescrivere terapie o dirti di sospendere una cura.** Sono atti riservati alle professioni sanitarie; esercitarli senza titolo è un reato (articolo 348 del codice penale). Allo stesso modo, «counseling» e «terapia» sono cose diverse: la psicoterapia è riservata a chi è iscritto all'albo degli psicologi o dei medici con specializzazione.

Se qualcuno ti dice che puoi ridurre un farmaco, che una pratica cura una malattia, o che il tuo disturbo ha una causa energetica precisa, **quella persona ha superato il confine**. Non è una questione di scuole di pensiero: è la sola cosa in questa guida che non ammette sfumature.

## I segnali che contano

**Dichiara dove si è formata, con chi e per quanto.** «Formata in reiki» dice poco. «Tre anni di formazione presso X, con Y come insegnante di riferimento» dice tutto: puoi verificare, e chi scrive così sa che lo puoi fare.

**Ha una supervisione o un aggiornamento in corso.** Chi lavora con le persone e continua a formarsi e a confrontarsi con qualcuno più esperto è in un altro campionato rispetto a chi ha finito un corso nel 2016 e da allora ripete.

**Parla dei limiti prima che glieli chieda tu.** «Questo non è indicato se…», «in questo caso ti mando da…». È il segnale più affidabile di tutti, perché va contro l'interesse immediato di chi lo dice.

**Ti chiede la tua storia prima di cominciare.** Salute, farmaci, percorsi in corso, gravidanza. Se questa conversazione manca, manca la cosa più importante.

**È chiara su prezzi, durata e disdetta.** Prima, per iscritto, senza che tu debba chiedere.

**Racconta il metodo, non i risultati degli altri.** «Lavoriamo così, ci vuole questo tempo» è un'informazione. Le testimonianze di trasformazioni straordinarie sono una vetrina.

## I segnali che sembrano dire qualcosa e non dicono niente

**Il numero di follower.** Misura la capacità di comunicare, che è un mestiere diverso.

**Un sito bello.** Costa poche centinaia di euro e non ha alcun rapporto con la qualità della pratica.

**«Certificato» senza dire da chi.** La parola da sola è vuota. Certificato da quale ente, in che anno, con quale percorso.

**I master di un fine settimana.** Alcune tecniche si trasmettono in tempi brevi, ed è legittimo. Ma un fine settimana non forma la capacità di stare con una persona che si commuove sul lettino: quella la dà la pratica accompagnata, negli anni.

**Le liste di benefici.** Più sono lunghe, meno sono utili: una pratica che promette di risolvere ansia, insonnia, digestione, autostima e relazioni sta descrivendo un desiderio, non un metodo.

## Le domande da fare al primo contatto

Sono cinque, si fanno in un messaggio, e la qualità delle risposte vale più di qualsiasi recensione.

1. **Dove ti sei formato e per quanto tempo?**
2. **Cosa succede in una sessione, passo per passo?**
3. **In quali casi mi diresti che questa pratica non fa per me?**
4. **Quanto costa, quanto dura, e come funziona se devo disdire?**
5. **Con che altre figure lavori, se serve?**

La terza è quella che separa. Chi risponde con precisione ha pensato ai propri limiti; chi risponde «è adatta a tutti» ti ha appena detto qualcosa di importante.

Sulla quinta: un professionista inserito in una rete di colleghi — medici, psicologi, fisioterapisti — è quasi sempre più affidabile di uno che lavora isolato, perché sa quando non tocca a lui.

## Quando la risposta non è un operatore olistico

Ci sono situazioni in cui la prima porta è un'altra, e dirlo fa parte del servizio.

Se stai attraversando un disturbo del sonno persistente, un dolore che non passa, un calo di peso che non hai cercato, pensieri di farti del male, un lutto che ti impedisce di funzionare, o se stai gestendo una malattia diagnosticata: **la prima conversazione è con il tuo medico, o con uno psicologo**.

Questo non esclude una pratica olistica: molte persone le portano avanti insieme, e i professionisti seri lo incoraggiano. Ma l'ordine conta, e nessuna pratica di benessere sostituisce una cura.

## Una cosa da tenere per ultima

Tutti i segnali di questa guida servono a ridurre il rischio, non ad azzerarlo. Alla fine resta una parte che nessun criterio copre: come ti senti quando parli con quella persona.

Se dopo il primo contatto ti senti messo fretta, valutato, o vagamente in colpa per le domande che hai fatto, quello è un dato. Vale quanto un attestato, e arriva prima.

## Domande frequenti

**Esiste un albo degli operatori olistici in Italia?**
No. Rientrano nella legge 4/2013 sulle professioni non organizzate: esistono associazioni professionali, alcune iscritte in un elenco ministeriale, ma nessun albo.

**Cosa vale un attestato rilasciato da un'associazione?**
Attesta che quella persona rispetta gli standard di quell'associazione per i servizi che offre. Non è un'abilitazione e non certifica la competenza individuale. Il valore dipende da quanto è verificabile l'associazione.

**Un operatore olistico può dirmi di sospendere un farmaco?**
Mai. È un atto medico, e chi lo fa senza titolo commette un reato. È il motivo più solido per interrompere un percorso.

**Quanto dovrebbe costare una sessione?**
Dipende da pratica, città e durata: la forbice reale è ampia. Il criterio utile è un altro, ed è che il prezzo sia dichiarato prima, insieme a durata e regole di disdetta.

**Le recensioni online sono affidabili?**
Sono un indizio, non una prova, e vanno lette per come sono scritte: quelle che raccontano cosa è successo valgono più di quelle che dicono «esperienza fantastica». Una recensione legata a una prenotazione verificata vale più di una anonima.

**Posso chiedere di parlare prima di prenotare?**
Sì, ed è consigliabile. La disponibilità a una conversazione preliminare gratuita di dieci minuti è già una risposta.
"""


async def main(dry_run: bool) -> None:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from database import db

    print(f"{TITOLO}\n  slug: {SLUG}\n  categoria: {CATEGORIA} (nuova)\n"
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
    print("\npubblicato")


if __name__ == "__main__":
    asyncio.run(main("--dry-run" in sys.argv))
