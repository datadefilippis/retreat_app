"""PC4 — terzo pezzo del cluster yoga: il pranayama.

PERCHE' QUESTO PER PRIMO fra i quattro previsti. Ha due agganci gia'
pronti: la guida ai tipi di yoga lo nomina come uno degli otto rami, e
quella al breathwork dice che il pranayama e' "il ramo dove la
distinzione fra tecniche lente e intense serve di piu'". Scriverlo ora
chiude quella frase invece di lasciarla in sospeso, e lega due cluster
che oggi si toccano appena.

ATTENZIONE ALLA MATERIA. Qui si danno istruzioni che le persone
eseguono sul proprio corpo: alcune tecniche (kapalabhati, bhastrika,
ritenzioni lunghe) sono a tutti gli effetti pratiche intense, con le
stesse controindicazioni del ramo intenso del breathwork. Il testo le
separa dalle lente e mette i limiti accanto a ciascuna, non in fondo:
un elenco di controindicazioni in coda lo legge chi ha gia' finito.

    venv/bin/python scripts/pc4_articolo_pranayama.py [--dry-run]
"""
import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone

SLUG = "pranayama-tecniche-respirazione-yoga"
TITOLO = "Pranayama: le tecniche di respirazione dello yoga, una per una"
DESCRIZIONE = (
    "Cos'è il pranayama, le tecniche principali con istruzioni e limiti, "
    "cosa dice la ricerca e come si impara senza farsi male."
)
CATEGORIA = "yoga"

CONTENUTO = """\
In una lezione di yoga arriva sempre il momento in cui l'insegnante dice di sedersi e respirare in un certo modo. Per molti è la parte più oscura dell'ora: le posizioni si vedono, il respiro no, e le istruzioni arrivano con nomi sanscriti che nessuno traduce.

Il pranayama è quel ramo della pratica, ed è più antico e più vasto di quanto la lezione lasci intuire. È anche l'unica parte dello yoga in cui si può fare del male facendo troppo, e vale la pena saperlo prima.

## Cosa significa la parola

*Prana* è l'energia vitale, il soffio. *Yama* significa controllo, ma anche *ayama* significa estensione: la parola si può leggere come "controllo del soffio" o come "estensione del soffio", e le due letture convivono nelle scuole.

Nella struttura degli otto rami dello yoga, il pranayama è il quarto: viene dopo le posizioni e prima del ritiro dei sensi. La sequenza non è casuale — il corpo si prepara, poi si lavora sul respiro, poi l'attenzione può rivolgersi all'interno.

Se ti sei avvicinato allo yoga dalle posizioni, questa guida racconta il gradino successivo. Se non sai ancora quale stile fa per te, quella sulle [differenze fra i tipi di yoga](/blog/differenze-tipi-di-yoga-hatha-vinyasa-ashtanga-yin-kundalini) viene prima.

## Le quattro parti di un respiro

Ogni tecnica lavora su quattro momenti, e conoscerli rende leggibili tutte le istruzioni che sentirai.

**Puraka** è l'inspirazione. **Rechaka** è l'espirazione. **Antara kumbhaka** è la sospensione a polmoni pieni. **Bahya kumbhaka** è la sospensione a polmoni vuoti.

Le *kumbhaka*, cioè le ritenzioni, sono la parte potente e quella delicata: nelle scuole tradizionali si introducono dopo mesi o anni di pratica sulle prime due, e non per prudenza formale.

## Le tecniche lente: si praticano da soli

**Respiro yogico completo.** Il fondamento: si riempie prima l'addome, poi la parte bassa del torace, poi l'alta, e si svuota in ordine inverso. Serve a recuperare un'ampiezza che la vita seduta toglie. Cinque minuti al giorno, seduti comodi.

**Ujjayi.** Si restringe leggermente la glottide e il respiro produce un suono simile a un'onda. Rallenta il respiro e dà all'attenzione qualcosa a cui appoggiarsi: è il respiro usato durante la pratica dinamica nell'ashtanga e in molte lezioni di vinyasa.

**Nadi shodhana**, la respirazione a narici alternate. Si chiude una narice, si inspira dall'altra, si cambia, si espira. È la tecnica più consigliata a chi comincia: è lenta, si controlla facilmente e ha una buona base di studi sugli effetti di calma. Cinque o dieci cicli bastano.

**Sitali e sitkari.** Si inspira attraverso la lingua arrotolata o fra i denti, producendo un raffreddamento. Tradizionalmente usate per abbassare il calore, fisico e non solo.

**Bhramari**, il respiro dell'ape. Si espira producendo un ronzio a bocca chiusa. È fra le più semplici e fra le più efficaci per calmare in fretta, e ha il vantaggio che l'effetto si sente subito.

Su queste tecniche il limite è quasi sempre il buon senso: se compare vertigine o affanno, si smette e si torna al respiro normale.

## Le tecniche intense: qui servono un insegnante e delle cautele

**Kapalabhati.** Espirazioni brevi e forzate con l'addome, inspirazioni passive, a ritmo sostenuto. Viene presentata come una pratica di pulizia ed è a tutti gli effetti una forma di iperventilazione controllata: produce gli stessi fenomeni descritti nella guida al [breathwork](/blog/breathwork-cose-tecniche-benefici), formicolii e testa leggera compresi.

**Bhastrika**, il respiro del mantice. Inspirazioni ed espirazioni entrambe forzate e rapide. Più intensa della precedente.

**Le ritenzioni prolungate.** Trattenere il respiro a lungo, in genere con rapporti precisi fra le quattro fasi, e spesso combinate con i *bandha*, le chiusure interne.

Per tutte e tre valgono le stesse controindicazioni: **gravidanza, ipertensione, patologie cardiovascolari, epilessia, glaucoma, distacco di retina, aneurismi, ernia addominale o inguinale, interventi recenti, disturbi psichiatrici in fase acuta**. Chi ha una di queste condizioni può praticare le tecniche lente, e per le altre la parola spetta al medico.

Vanno imparate accanto a un insegnante che ti guarda mentre le fai. Un video non vede che stai forzando le spalle, né che sei diventato pallido.

## Cosa dice la ricerca

Il pranayama è fra le pratiche yogiche più studiate, e i risultati sono migliori di quanto si potrebbe temere in un campo così antico.

Sulla **respirazione lenta**, comprese narici alternate e respiro allungato, gli studi riportano in modo consistente riduzione della frequenza cardiaca, aumento della variabilità cardiaca, riduzione della pressione e miglioramenti su ansia e qualità del sonno. Il meccanismo è compreso: il respiro lento stimola il nervo vago e sposta l'equilibrio verso il sistema parasimpatico.

Sulle **tecniche intense** la letteratura è più scarsa e più cauta, e gli effetti descritti riguardano soprattutto attivazione e attenzione. Gli studi sono piccoli e i protocolli difficili da confrontare.

Un'osservazione che vale per tutto il campo: molti studi confrontano il pranayama con "nessun intervento" invece che con un'attività di controllo, e questo rende difficile separare l'effetto della tecnica da quello di sedersi in silenzio dieci minuti al giorno. Che poi è comunque qualcosa.

## Come si impara, in pratica

**Comincia dal respiro completo e da nadi shodhana**, cinque minuti al giorno per due settimane. È la base su cui poggia tutto il resto e non richiede nessuna supervisione.

**Pratica a stomaco vuoto**, o almeno due ore dopo un pasto. È l'unica regola tradizionale che ha una ragione immediatamente evidente a chi ci prova.

**Seduto con la schiena lunga**, su una sedia va benissimo. La posizione a terra non è un requisito, e forzarla toglie attenzione al respiro.

**Se compare vertigine, fermati.** Non è un passaggio da attraversare: è il segnale che stai facendo troppo, e con le tecniche lente non dovrebbe comparire affatto.

**Per le tecniche intense, cerca un insegnante.** Sulla scelta valgono i criteri generali che abbiamo raccolto in [come capire se un operatore è serio](/blog/come-capire-se-un-operatore-olistico-e-serio): il più utile qui è chiedere in quali casi ti direbbe di non praticare una certa tecnica.

## Domande frequenti

**Il pranayama si può fare senza praticare le posizioni?**
Sì. Le tecniche lente si praticano da sedute e non richiedono nessuna preparazione fisica. Nella tradizione le posizioni vengono prima perché preparano il corpo a stare fermo a lungo, ma non è un vincolo per cominciare.

**Quanto tempo al giorno serve?**
Cinque minuti per un effetto immediato, e due o tre settimane di pratica quotidiana perché il cambiamento diventi stabile. Meglio cinque minuti tutti i giorni che mezz'ora una volta a settimana.

**Qual è la tecnica migliore per l'ansia?**
Fra le lente, nadi shodhana e bhramari sono le più indicate, insieme a qualsiasi respirazione in cui l'espirazione duri il doppio dell'inspirazione. Le tecniche intense in fase acuta di ansia sono sconsigliate.

**Kapalabhati fa dimagrire?**
No. È una tecnica di respiro e l'affermazione che bruci grasso addominale non ha basi. Attiva l'addome, che è un'altra cosa.

**Posso praticarlo in gravidanza?**
Le tecniche lente in genere sì, escluse le ritenzioni; quelle intense no. La decisione va presa con chi segue la gravidanza, e conviene rivolgersi a un insegnante con formazione specifica.

**Che differenza c'è fra pranayama e breathwork?**
Il pranayama è il ramo di tecniche che appartiene alla tradizione dello yoga, con una cornice filosofica e un ordine di apprendimento propri. Il breathwork è il termine contemporaneo che comprende anche pratiche nate in Occidente nel Novecento, e alcune sue tecniche intense assomigliano molto a kapalabhati e bhastrika.
"""


async def main(dry_run: bool) -> None:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from database import db

    print(f"{TITOLO}\n  slug: {SLUG}\n  categoria: {CATEGORIA}\n"
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
        # PE7 — il pezzo entra nel grafo nello stesso momento in cui
        # nasce: un articolo pubblicato senza correlati e' un'isola.
        "related_slugs": [
            "differenze-tipi-di-yoga-hatha-vinyasa-ashtanga-yin-kundalini",
            "breathwork-cose-tecniche-benefici",
            "meditazione-per-chi-inizia-guida-semplice",
        ],
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

    # i due articoli che lo devono citare: link in mezzo al testo, e il
    # grafo aggiornato in entrambe le direzioni
    aggiunte = [
        ("differenze-tipi-di-yoga-hatha-vinyasa-ashtanga-yin-kundalini",
         "- **Yoga nidra** — non è una lezione di posizioni",
         f"- **Pranayama** — le tecniche di respiro dello yoga, un ramo "
         f"a sé che si pratica da seduti: le abbiamo messe in fila in "
         f"[questa guida](/blog/{SLUG}).\n"
         "- **Yoga nidra** — non è una lezione di posizioni"),
        ("breathwork-cose-tecniche-benefici",
         "è il ramo dove la distinzione di questa guida serve di più, e "
         "conviene impararle con un insegnante.",
         f"è il ramo dove la distinzione di questa guida serve di più, e "
         f"conviene impararle con un insegnante: le trovi una per una in "
         f"[questa guida al pranayama](/blog/{SLUG})."),
    ]
    for slug, vecchio, nuovo in aggiunte:
        d = await db.articles.find_one({"slug": slug}, {"_id": 0, "content": 1})
        if not d:
            print(f"  ASSENTE {slug}")
            continue
        if nuovo in d["content"]:
            print(f"  link gia' presente in {slug[:40]}")
        elif vecchio in d["content"]:
            await db.articles.update_one({"slug": slug}, {"$set": {
                "content": d["content"].replace(vecchio, nuovo, 1)}})
            print(f"  link aggiunto in {slug[:40]}")
        else:
            print(f"  NON TROVATO in {slug[:40]} — controllare a mano")

    print("\npubblicato")


if __name__ == "__main__":
    asyncio.run(main("--dry-run" in sys.argv))
