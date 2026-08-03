"""NA1 — i chakra, il termine piu' cercato del cluster energia.

PERCHE'. "Energia" ha quattro pezzi (reiki, tarocchi, tema natale,
costellazioni) e nessuno sui chakra, che e' la parola che tutti hanno
sentito e nessuno sa spiegare. Chi la cerca in italiano trova o pagine
che diagnosticano malattie dai chakra, o pagine che liquidano tutto
come sciocchezza. Manca quella che racconta cosa dice la tradizione,
cosa e' stato aggiunto dopo, e come si usa la mappa senza crederla
un'anatomia.

IL PUNTO DELICATO, ed e' il motivo per cui questo pezzo vale.
I sette chakra con i colori dell'arcobaleno NON sono la tradizione
indiana: sono una sistematizzazione occidentale del Novecento, che
passa dalla traduzione di Arthur Avalon del 1919 e poi dalla New Age.
I testi tantrici hanno numeri diversi a seconda della scuola e non
assegnano quei colori. Dirlo non demolisce la pratica — la mappa
resta uno strumento di attenzione che funziona — toglie solo la
pretesa di antichita' a una parte che antica non e'.

E LA COSA CHE PROTEGGE IL LETTORE: "hai il quarto chakra bloccato"
non e' una diagnosi, e chi la usa per spiegare una malattia sta
facendo una cosa che nessuna tradizione seria autorizza.

    venv/bin/python scripts/na1_articolo_chakra.py [--dry-run]
"""
import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone

SLUG = "chakra-cosa-sono-i-sette-come-si-usano"
TITOLO = "I chakra: cosa sono, quali sono i sette e come si usano"
DESCRIZIONE = (
    "Cosa dice la tradizione, cosa è stato aggiunto in Occidente, i sette "
    "uno per uno e come si usa la mappa senza scambiarla per anatomia."
)
CATEGORIA = "energia"

YOGA = "/blog/yoga-cose-da-dove-viene-come-cominciare"
PRANA = "/blog/pranayama-tecniche-respirazione-yoga"
MEDIT = "/blog/meditazione-per-chi-inizia-guida-semplice"
REIKI = "/blog/reiki-cose-come-funziona-una-sessione"
SERIO = "/blog/come-capire-se-un-operatore-olistico-e-serio"

CONTENUTO = f"""\
Prima o poi qualcuno te lo dice: «hai il quarto chakra chiuso», oppure «lavoriamo sul primo, che è dove sei scarico». Annuisci, perché chiedere cosa significhi esattamente sembra ammettere di non capire una cosa che sembrano capire tutti.

Non la capiscono tutti. E la parte più interessante è che una porzione di quello che si racconta in Italia sui chakra ha meno di cent'anni.

Questa guida mette in fila tre cose: cosa dicono le tradizioni da cui il termine viene, cosa è stato aggiunto dopo e da chi, e come si usa questa mappa in modo sensato — perché come strumento funziona, a patto di sapere che strumento è.

## Cosa significa la parola

*Chakra* in sanscrito vuol dire ruota, o disco.

Nelle tradizioni che la usano indica un punto di raccolta in un corpo che non è quello fisico: un corpo *sottile*, percorso da canali chiamati *nadi* in cui scorre il *prana*, il soffio vitale. I chakra sono i nodi dove quei canali si incrociano.

Fin qui è importante notare una cosa che poi si perde: si sta descrivendo una mappa di esperienza interiore, non un organo. Nessun testo antico sostiene che si possano trovare aprendo un corpo.

## Da dove vengono

Il termine compare nei testi tantrici e hatha fra l'ottavo e il quindicesimo secolo, in una letteratura vasta e tutt'altro che uniforme.

**Il numero cambia da scuola a scuola.** Alcuni testi ne descrivono quattro, altri sei, altri nove, altri ancora arrivano a dodici. Il sistema a sette che conosciamo tutti è uno fra i tanti, non il canone.

**I colori dell'arcobaleno sono un'aggiunta occidentale.** È la scoperta che sorprende di più. Nei testi tradizionali i chakra sono associati a petali di loto, sillabe, divinità e colori che non seguono affatto la sequenza rosso-arancione-giallo-verde-azzurro-indaco-viola. Quella corrispondenza nasce nel Novecento, in Occidente, e si diffonde con la cultura New Age degli anni Settanta.

**Il passaggio chiave è del 1919**, quando John Woodroffe, che firmava Arthur Avalon, traduce e commenta i testi tantrici in *The Serpent Power*. È da lì che il sistema a sette entra nell'immaginario occidentale, e da lì che comincia a mescolarsi con la psicologia e con la teosofia.

Dire tutto questo non toglie valore alla mappa. Toglie la pretesa di antichità a una parte che antica non è, e chi insegna con serietà questa distinzione la conosce.

## I sette, uno per uno

Nella versione diffusa oggi, dal basso verso l'alto.

**1. Muladhara — la radice.** Base della colonna, perineo. Il tema è la sicurezza di base: avere un posto, un corpo, di che vivere. Elemento terra.

**2. Svadhisthana — il sacro.** Sotto l'ombelico. Il tema è il piacere, la creatività, il desiderio, la capacità di lasciarsi attraversare da quello che sente il corpo. Elemento acqua.

**3. Manipura — il plesso solare.** Sopra l'ombelico. Il tema è la volontà e l'affermazione: decidere, dire di no, prendere posizione. Elemento fuoco.

**4. Anahata — il cuore.** Centro del petto. Il tema è la relazione: affetto, compassione, la capacità di lasciare entrare qualcuno. È il punto in cui la mappa si divide fra i tre centri bassi e i tre alti. Elemento aria.

**5. Vishuddha — la gola.** Il tema è l'espressione: dire quello che si pensa, e anche saper ascoltare. Elemento etere.

**6. Ajna — il terzo occhio.** Fra le sopracciglia. Il tema è la percezione e la chiarezza interiore.

**7. Sahasrara — la corona.** Sommità del capo. Il tema è il rapporto con qualcosa che eccede l'individuo. Nella tradizione non è propriamente un chakra come gli altri, ma il punto in cui la mappa si conclude.

Guardata di fila, la sequenza racconta una progressione riconoscibile: dalla sopravvivenza al piacere, dal piacere alla volontà, dalla volontà alla relazione, e da lì verso l'espressione e la conoscenza. È il motivo per cui questa mappa ha attraversato un secolo di culture diverse restando utilizzabile.

## Cosa non sono

Qui conviene essere netti, perché è il punto in cui più persone vengono raggirate.

**Non hanno un corrispettivo anatomico.** Non sono ghiandole, non sono plessi nervosi, non sono organi. L'associazione con il sistema endocrino, che si legge spesso, è un'analogia costruita a posteriori in Occidente: suggestiva, e senza base nella fisiologia.

**Non sono misurabili.** Nessuno strumento rileva un chakra, e nessuno studio ne ha dimostrato l'esistenza fisica. Chi mostra una macchina che «legge i chakra» sta usando un dispositivo che misura altro — di solito la conduttanza della pelle — e lo presenta per quello che non è.

**«Chakra bloccato» non è una diagnosi.** È un modo di dire dentro un linguaggio simbolico. Usarlo per spiegare una malattia, o per suggerire che una terapia non serva, è la cosa che dovrebbe far chiudere la porta. Nessuna tradizione seria autorizza quel passaggio, e in Italia farlo senza titolo è anche un problema legale — è uno dei criteri con cui si riconosce [chi lavora con serietà]({SERIO}).

**Non c'è una versione ufficiale.** Il numero, i colori, i temi cambiano fra scuole. Chi presenta la propria come l'unica corretta sta dicendo qualcosa su di sé.

## Allora a cosa servono

A una cosa precisa, e piuttosto potente: **sono una mappa dell'attenzione**.

Il corpo ha zone dove le emozioni si sentono in modo riconoscibile. La paura stringe la pancia, l'ansia chiude la gola, il dolore affettivo pesa sul petto. Non serve credere a un'anatomia sottile per accorgersene: succede.

I chakra danno un ordine a quelle zone e ci attaccano dei temi. Portare l'attenzione al centro del petto pensando alla relazione, o alla gola pensando a quello che non si è detto, produce un effetto — sull'attenzione, sul respiro, a volte sulle emozioni. Chiamare quella zona *anahata* aggiunge una tradizione e un vocabolario, e per molte persone rende l'esperienza più leggibile.

È lo stesso motivo per cui la mappa attraversa lo yoga, la [meditazione]({MEDIT}), il lavoro sul respiro e le pratiche a mediazione corporea come il [reiki]({REIKI}): serve come indice, non come referto.

## Una pratica da fare stasera

Il modo più semplice per capire di cosa si parla è provarlo. Dieci minuti.

**Siediti** comodo, schiena appoggiata se serve. Chiudi gli occhi. Tre respiri lenti, con l'espirazione più lunga dell'inspirazione.

**Parti dal basso.** Porta l'attenzione alla base della colonna, dove il corpo tocca la sedia. Restaci un minuto. Non cercare niente: nota solo cosa c'è — peso, calore, niente. «Niente» è una risposta valida.

**Sali di una zona alla volta.** Basso ventre, sopra l'ombelico, centro del petto, gola, fra le sopracciglia, sommità del capo. Un minuto ciascuno.

**Nota dove ti fermi volentieri e dove hai fretta di passare oltre.** È l'unica informazione che conta, e di solito è la stessa per settimane.

**Chiudi** con tre respiri e riapri gli occhi lentamente.

Fatta due o tre volte a settimana per un mese, questa pratica dice più di qualsiasi lettura. E si combina bene con [una tecnica di respiro]({PRANA}) prima di cominciare.

## Come si riconosce chi ne parla con serietà

Quattro cose, e valgono in una sala di yoga come in uno studio.

**Distingue la tradizione dalla metafora.** Chi sa da dove viene questa mappa sa anche dirti quale parte è antica e quale no.

**Non diagnostica.** Non spiega un sintomo con un chakra, non tocca il tema dei farmaci, e se il tuo racconto entra in territorio medico ti dice di andare da un medico.

**Non vende sblocchi.** Il pacchetto in cinque sedute che «riallinea i chakra» è un prodotto, non una pratica.

**Ammette i limiti.** «Questa è una mappa che uso per lavorare sull'attenzione» è una frase che si può dire con rispetto per la tradizione e senza pretese. Chi la dice, di solito, sa quello che fa.

Se lo incontri dentro una pratica di yoga, il quadro d'insieme in cui questa mappa sta lo trovi nella [guida generale allo yoga]({YOGA}).

## Domande frequenti

**I chakra esistono?**
Come struttura fisica, no: non sono organi e nessuno strumento li rileva. Come mappa di zone del corpo a cui associare temi ed emozioni sono uno strumento reale e utilizzabile, e la differenza fra le due cose è tutto.

**Quanti sono davvero?**
Dipende dalla tradizione: i testi ne descrivono da quattro a dodici e oltre. Il sistema a sette è quello diffuso in Occidente, non l'unico.

**Perché ognuno ha un colore?**
L'associazione con i colori dell'arcobaleno nasce in Occidente nel Novecento e non appartiene ai testi originali, che assegnano colori diversi e non in sequenza.

**Cosa vuol dire avere un chakra bloccato?**
È un modo di dire dentro un linguaggio simbolico: indica un tema su cui si fa fatica. Non è una diagnosi, e chi lo usa per spiegare una malattia sta oltrepassando un confine.

**Si possono riequilibrare?**
Le pratiche che lavorano su respiro, attenzione e corpo hanno effetti reali su come ti senti. Chiamarli riequilibrio dei chakra è una scelta di vocabolario. Diffida di chi promette un risultato misurabile in un numero fisso di sedute.

**Servono cristalli o oggetti?**
No. La mappa funziona con l'attenzione. Gli oggetti sono un supporto rituale per chi li trova utili, e nessuno studio attribuisce loro un effetto proprio.

**Da dove comincio se il tema mi interessa?**
Dalla pratica di dieci minuti descritta qui sopra, e da una pratica di [meditazione]({MEDIT}) regolare. Le due cose insieme rendono la mappa leggibile molto più della lettura di un libro.
"""

AGGIUNTE = [
    ("reiki-cose-come-funziona-una-sessione", "## Domande frequenti",
     f"Nel vocabolario di queste pratiche torna spesso la parola chakra: "
     f"cosa dice la tradizione e cosa e' stato aggiunto dopo lo abbiamo "
     f"raccontato [qui](/blog/{SLUG}).\n\n## Domande frequenti"),
    ("yoga-cose-da-dove-viene-come-cominciare", "## Domande frequenti",
     f"Nelle sale si sente nominare spesso anche un'altra mappa, quella dei "
     f"[chakra](/blog/{SLUG}): utile sapere quale parte viene dalla "
     f"tradizione e quale e' stata aggiunta in Occidente.\n\n"
     f"## Domande frequenti"),
]


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
        "related_slugs": ["reiki-cose-come-funziona-una-sessione",
                          "meditazione-per-chi-inizia-guida-semplice",
                          "yoga-cose-da-dove-viene-come-cominciare"],
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

    for slug, vecchio, nuovo in AGGIUNTE:
        d = await db.articles.find_one({"slug": slug}, {"_id": 0, "content": 1})
        if not d:
            print(f"  ASSENTE {slug}")
        elif f"/blog/{SLUG})" in d["content"]:
            print(f"  link gia' presente in {slug[:44]}")
        elif vecchio in d["content"]:
            await db.articles.update_one({"slug": slug}, {"$set": {
                "content": d["content"].replace(vecchio, nuovo, 1)}})
            print(f"  link aggiunto in {slug[:44]}")
        else:
            print(f"  NON TROVATO in {slug[:44]} — controllare a mano")

    print("\npubblicato")


if __name__ == "__main__":
    asyncio.run(main("--dry-run" in sys.argv))
