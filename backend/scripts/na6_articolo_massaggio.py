"""NA6 — il massaggio olistico: si riempie una stanza che era vuota.

"Massaggio & Bodywork" esisteva nella tassonomia dei ritiri con zero
articoli. Una categoria vuota nel Magazine e' peggio di una categoria
assente: c'e' e non porta da nessuna parte.

LA PARTE CHE VALE, e che in italiano si trova quasi solo sui forum: IL
CONFINE. "Massaggio" e' una parola sola che copre due mondi separati
per legge. Il massaggio a scopo di benessere e rilassamento lo puo'
fare un operatore non sanitario; il massaggio come trattamento di una
patologia e' un atto sanitario e richiede un titolo. Chi propone un
massaggio "per curare" la cervicale o l'ernia sta oltrepassando quel
confine, e chi lo riceve di solito non sa che esiste.

Il quadro italiano e' anche piu' intricato del solito: i requisiti per
esercitare cambiano da regione a regione, e non esiste un titolo unico
nazionale per chi fa massaggio benessere. Lo dico senza fingere che ci
sia un ordine che non c'e'.

L'ALTRA COSA CHE MANCA OVUNQUE: il consenso al tocco e la gestione del
telo. E' il massaggio, cioe' la pratica in cui ci si spoglia davanti a
uno sconosciuto, e quasi nessuna guida italiana spiega cosa e'
normale aspettarsi e cosa non lo e'.

    venv/bin/python scripts/na6_articolo_massaggio.py [--dry-run]
"""
import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone

SLUG = "massaggio-olistico-tipi-cosa-aspettarsi"
TITOLO = "Massaggio olistico: i tipi principali e cosa aspettarsi"
DESCRIZIONE = (
    "Le tecniche più diffuse, il confine fra benessere e atto sanitario, "
    "come si svolge una seduta, il consenso al tocco e le controindicazioni."
)
CATEGORIA = "massaggio"

SERIO = "/blog/come-capire-se-un-operatore-olistico-e-serio"
AYU = "/blog/ayurveda-cose-i-tre-dosha-cosa-aspettarsi"
CAMPANE = "/blog/campane-tibetane-benefici-come-funzionano"
STRESS = "/blog/pratiche-olistiche-contro-stress-cosa-funziona"
REIKI = "/blog/reiki-cose-come-funziona-una-sessione"
YOGA = "/blog/yoga-cose-da-dove-viene-come-cominciare"

CONTENUTO = f"""\
«Massaggio olistico» è un'etichetta che copre pratiche molto diverse: un'ora di sfioramenti lenti con gli oli e una seduta di shiatsu in cui vieni premuto con i gomiti hanno in comune il lettino e poco altro.

E c'è una cosa che viene prima delle tecniche, che quasi nessuno spiega e che riguarda direttamente chi si spoglia in una stanza con uno sconosciuto: il confine fra un massaggio di benessere e un atto sanitario.

Questa guida mette in fila entrambe le cose: cosa distingue le tecniche principali, e cosa è normale aspettarsi da una seduta condotta bene.

## Il confine che conta

In Italia la parola «massaggio» copre due mondi che la legge tiene separati.

**Il massaggio a scopo di benessere.** Rilassare, sciogliere tensioni, dare sollievo, accompagnare una persona sana. Lo può praticare un operatore non sanitario, ed è quello di cui parla questa guida.

**Il massaggio come trattamento.** Intervenire su una patologia, riabilitare dopo un infortunio, curare una condizione diagnosticata. È un **atto sanitario** e richiede un titolo abilitante: fisioterapista, massofisioterapista, massaggiatore sanitario.

La conseguenza pratica è netta. Un operatore del benessere può farti stare meglio; **non può dirti che ti cura la cervicale, l'ernia o la sciatica**, e se lo fa sta oltrepassando un confine che è anche penale — vale qui come per [qualsiasi pratica olistica]({SERIO}).

Va detta anche la parte scomoda: **in Italia non esiste un titolo unico nazionale per chi fa massaggio benessere**. I requisiti per esercitare dipendono dalla regione e dalla forma con cui si lavora — qualifica di operatore del benessere, percorso estetico, associazione professionale della legge 4/2013. È un quadro frammentato, e chi lavora bene sa dirti esattamente in quale casella sta.

## Le tecniche principali

**Massaggio classico, o svedese.** Il più diffuso: sfioramenti, impastamenti, frizioni, percussioni. Lavora sulla muscolatura superficiale e sulla circolazione. Se non sai da dove cominciare, è da qui.

**Californiano.** Movimenti lunghi, lenti e avvolgenti su tutto il corpo, con oli. È il più orientato al rilassamento profondo e al contatto: nato negli anni Settanta in California nel contesto della psicologia umanistica, ha una vocazione emotiva dichiarata, e capita che smuova.

**Deep tissue.** Pressione profonda e mirata sui tessuti sotto la superficie, spesso con gomiti e avambracci. Efficace sulle tensioni croniche, e sgradevole se chi lo esegue non gradua. Non deve mai fare un male che non riesci a respirare.

**Shiatsu.** Di origine giapponese, si pratica **vestiti**, su un futon a terra. Pressioni con pollici, palmi e gomiti lungo linee energetiche della tradizione orientale, insieme a stiramenti e mobilizzazioni. Chi non ama spogliarsi trova qui la porta d'ingresso più semplice.

**Thai.** Anche questo vestiti e a terra: una sequenza di stiramenti passivi in cui chi conduce muove il corpo in posizioni che ricordano lo [yoga]({YOGA}). Attivo, a tratti intenso, e insolito per chi si aspetta di stare fermo.

**Lomi lomi.** Di tradizione hawaiana, movimenti fluidi e continui con gli avambracci, spesso su tutto il corpo insieme. Molto avvolgente.

**Riflessologia plantare.** Pressione su punti del piede che nella tradizione corrispondono a zone del corpo. Si sta vestiti, tolte le scarpe, e la mappa va presa come mappa: la corrispondenza fra punti del piede e organi non ha riscontro anatomico, mentre l'effetto di rilassamento è reale e ben descritto.

**Abhyanga.** Il massaggio con olio caldo della tradizione ayurvedica, su tutto il corpo, spesso con oli scelti in base alla costituzione. Fa parte di un sistema più ampio, di cui abbiamo scritto nella [guida all'ayurveda]({AYU}).

**Massaggio sonoro.** Le [campane appoggiate sul corpo]({CAMPANE}) e fatte suonare: la vibrazione si trasmette ai tessuti. È l'unico di questa lista che non prevede quasi contatto manuale.

Una nota su una tecnica che si sente nominare spesso: il **drenaggio linfatico** nella sua forma codificata è una tecnica di ambito sanitario, con indicazioni cliniche precise. Quello proposto in un centro benessere è un'altra cosa, e chiamarlo con lo stesso nome genera aspettative che non verranno soddisfatte.

## Come si svolge una seduta

**Il colloquio.** Cinque o dieci minuti in cui racconti come stai e in cui ti vengono chieste condizioni di salute, farmaci, interventi recenti, gravidanza, zone dolenti. Se questa parte manca, manca la parte che riguarda la tua sicurezza.

**La preparazione.** Ti viene detto cosa toglierti e ti viene lasciata la stanza per farlo. Ti sdrai sotto un telo.

**Il lavoro.** Dai cinquanta ai novanta minuti, a seconda della tecnica. Chi conduce lavora una zona alla volta.

**La chiusura.** Qualche minuto fermi prima di rialzarsi, e un bicchiere d'acqua. Alzarsi di scatto dopo un massaggio profondo è il modo più comune di sentirsi storditi.

Il prezzo in Italia va in genere dai 50 ai 90 euro per un'ora, con differenze fra città e fra tecniche.

## Il consenso al tocco, e il telo

Questa sezione esiste perché il massaggio è la pratica in cui ci si spoglia davanti a una persona che non si conosce, e perché quasi nessuna guida spiega cosa è normale.

**Ti viene detto prima cosa succederà.** Quali zone verranno trattate, con che pressione, per quanto. Non «rilassati e lascia fare».

**Ti spogli da solo, in privato.** Chi conduce esce dalla stanza o si volta, e rientra quando sei coperto.

**Il telo copre sempre quello che non si sta trattando.** Si scopre una zona alla volta e la si ricopre. È una tecnica precisa, si impara nelle scuole serie, e la sua assenza è un segnale.

**Le zone intime non si toccano.** Mai, in nessuna tecnica di questa lista. Il seno e la zona inguinale restano coperti, salvo tecniche specifiche di ambito sanitario per cui serve un titolo e un consenso esplicito.

**Puoi dire di no in qualsiasi momento.** A una zona, a una pressione, a tutta la seduta. Un professionista si ferma e basta.

**Se qualcosa ti mette a disagio, puoi interrompere e andartene.** Non devi giustificarti, e non devi finire la seduta per educazione. Se succede qualcosa di scorretto, esiste la strada ordinaria della denuncia.

## Cosa dice la ricerca

Il massaggio è fra le pratiche a mediazione corporea con la letteratura più consistente, ed è utile separare i piani.

**Dove le prove sono buone.** Riduzione del **dolore muscoloscheletrico**, in particolare lombare e cervicale, con effetti nel breve termine documentati e riconosciuti in alcune linee guida come opzione di accompagnamento. Poi **ansia e stress percepito**, dove il massaggio è uno degli interventi non farmacologici più studiati. Poi la **qualità del sonno**.

**Dove sono più deboli.** Gli effetti a lungo termine, che tendono a svanire senza continuità. E le corrispondenze delle mappe — punti del piede, meridiani — che restano cornici tradizionali senza riscontro anatomico.

**Quello che non fa.** Non elimina tossine, non scioglie il grasso, non cura patologie. La frase «espellere le tossine» ricorre ovunque e non descrive niente di verificabile.

Un dato interessante e poco citato: negli studi sul dolore, il massaggio regge il confronto con altri interventi anche quando si controlla per l'effetto dell'attenzione ricevuta. Il contatto fisico prolungato, di per sé, fa qualcosa — ed è la stessa ragione per cui funziona in [molte pratiche contro lo stress]({STRESS}).

## Controindicazioni

Vanno dette prima della seduta, e un professionista le chiede.

- **Febbre e infezioni in corso**, che escludono la seduta
- **Trombosi o sospetta trombosi venosa profonda**, che è la controindicazione più seria in assoluto
- **Patologie cardiache non compensate e ipertensione non controllata**
- **Tumori in corso o recenti**, dove serve il via libera dell'oncologo
- **Lesioni cutanee, ustioni, dermatiti** nelle zone da trattare
- **Fratture recenti, protesi, interventi chirurgici** degli ultimi mesi
- **Gravidanza**, che richiede tecniche e posizioni dedicate, soprattutto nel primo trimestre
- **Terapia anticoagulante**, che sconsiglia le pressioni profonde

## Come si sceglie chi ti tratta

Oltre ai [criteri generali]({SERIO}), quattro domande specifiche.

**Che formazione hai e di quante ore?** Le scuole serie di massaggio contano centinaia di ore con pratica supervisionata. Un corso di un fine settimana insegna una sequenza, non un mestiere.

**Sei coperto da un'assicurazione professionale?** Domanda normale e informativa: chi lavora con le mani sul corpo altrui e non ha una copertura ci ha pensato poco.

**Cosa fai se ho un problema che non è di tua competenza?** La risposta giusta contiene il nome di una figura sanitaria.

**Come gestisci il telo?** Sembra strana e non lo è: chi ha studiato risponde con precisione perché è una tecnica che ha imparato.

E un criterio che vale più di tutti: **un massaggio non deve fare male**. Una pressione intensa può essere scomoda e respirabile; se stringi i denti e trattieni il fiato, è troppa, e dirlo è tuo diritto.

## Domande frequenti

**Che differenza c'è fra massaggio olistico e fisioterapia?**
Il primo accompagna il benessere di una persona sana; la seconda è una professione sanitaria che tratta patologie e disfunzioni con un titolo abilitante. Sono due cose distinte, non due livelli della stessa.

**Un massaggiatore può curarmi la cervicale?**
Non può presentarlo come cura. Può dare sollievo alla tensione muscolare, che è un'altra affermazione. Se hai una diagnosi, la figura di riferimento è sanitaria.

**Devo spogliarmi del tutto?**
Dipende dalla tecnica: shiatsu e thai si fanno vestiti, le tecniche con olio in genere in intimo. Non è mai richiesto di togliere l'intimo, e il telo copre sempre quello che non si sta trattando.

**Quanto dovrebbe costare?**
In Italia fra i 50 e i 90 euro per un'ora, con differenze fra città e tecnica. Sotto una certa soglia conviene chiedere formazione e durata effettiva.

**Ogni quanto ha senso farlo?**
Per il benessere generale, una volta al mese è la frequenza più comune. Su una tensione specifica, un ciclo ravvicinato di tre o quattro sedute funziona meglio di una sola.

**Il massaggio elimina le tossine?**
No. È una frase che ricorre ovunque e non descrive un processo verificabile. Bere acqua dopo è comunque una buona idea, per la stessa ragione per cui lo è sempre.

**Quale tecnica scelgo se non ho mai fatto un massaggio?**
Classico o californiano se cerchi rilassamento, shiatsu se preferisci restare vestito, deep tissue solo se hai tensioni croniche e sai di tollerare la pressione.

**Posso farlo in gravidanza?**
Sì, con tecniche e posizioni dedicate e dopo aver sentito chi ti segue. Molti operatori evitano il primo trimestre per prudenza.

**È normale commuoversi durante un massaggio?**
Capita, soprattutto nelle tecniche lente e avvolgenti, ed è il rilassamento che scioglie quello che era trattenuto. Chi conduce bene non fa domande: lascia il tempo che serve. Vale lo stesso in altre pratiche a mediazione corporea come il [reiki]({REIKI}).
"""

AGGIUNTE = [
    ("pratiche-olistiche-contro-stress-cosa-funziona", "## Domande frequenti",
     f"Del massaggio, che in questo elenco e' fra le pratiche con le prove "
     f"piu' solide, abbiamo scritto [una guida a parte](/blog/{SLUG}): le "
     f"tecniche, il confine fra benessere e atto sanitario, e cosa e' "
     f"normale aspettarsi da una seduta.\n\n## Domande frequenti"),
    ("ayurveda-cose-i-tre-dosha-cosa-aspettarsi", "## Domande frequenti",
     f"L'abhyanga e' uno dei tanti modi in cui si lavora sul corpo con le "
     f"mani: le altre tecniche, e cosa le distingue, stanno nella [guida al "
     f"massaggio olistico](/blog/{SLUG}).\n\n## Domande frequenti"),
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
        "related_slugs": ["come-capire-se-un-operatore-olistico-e-serio",
                          "ayurveda-cose-i-tre-dosha-cosa-aspettarsi",
                          "campane-tibetane-benefici-come-funzionano"],
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
