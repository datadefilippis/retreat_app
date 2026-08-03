"""PL1 — il pilastro dello yoga: la porta d'ingresso che mancava.

PERCHE' ORA. Il cluster ha quattro pezzi e cinquemila parole, e nessuno
di loro e' una porta: chi cerca "yoga" e basta — il termine piu' cercato
fra tutti quelli che tocchiamo — non trova dove entrare, trova quattro
approfondimenti che presuppongono di sapere gia' cosa sia.

COSA DEVE FARE UN PILASTRO. Due cose insieme, e la seconda si dimentica
sempre: dire la cosa per intero a chi non sa nulla, e smistare verso i
figli chi vuole andare a fondo. Se fa solo la prima e' un articolo
lungo; se fa solo la seconda e' un indice.

LE SCELTE DI CONTENUTO che rendono questo pezzo diverso dagli altri
mille "cos'e' lo yoga" in italiano.

1. GLI OTTO RAMI, spiegati. E' la filosofia, ed e' la parte che quasi
   nessuno racconta perche' non porta clic. Ma e' anche il fatto che
   riordina tutto: le posizioni sono uno degli otto rami, e sono il
   terzo. Chi lo scopre guarda la propria lezione con altri occhi.

2. LA STORIA DETTA COM'E', compreso il punto scomodo: la lezione che
   facciamo oggi e' stata codificata in gran parte nel Novecento. Non
   toglie profondita' alla pratica, toglie solo il fumo a chi vende
   "cinquemila anni di tradizione" per una sequenza di vent'anni fa.

3. IL GLOSSARIO delle parole che sentirai in sala. Serve a chi entra la
   prima volta e non osa chiedere cosa significa drishti. E' la parte
   piu' utile e la meno scritta.

    venv/bin/python scripts/pl1_pilastro_yoga.py [--dry-run]
"""
import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone

SLUG = "yoga-cose-da-dove-viene-come-cominciare"
TITOLO = "Yoga: cos'è, da dove viene e come cominciare"
DESCRIZIONE = (
    "La guida completa: le origini, gli otto rami, cosa succede in una "
    "lezione, cosa dice la ricerca e come scegliere da dove partire."
)
CATEGORIA = "yoga"

STILI = "/blog/differenze-tipi-di-yoga-hatha-vinyasa-ashtanga-yin-kundalini"
PRANA = "/blog/pranayama-tecniche-respirazione-yoga"
NIDRA = "/blog/yoga-nidra-cose-come-funziona-una-sessione"
KRIYA = "/blog/kriya-yoga-cose-come-funziona"
SERIO = "/blog/come-capire-se-un-operatore-olistico-e-serio"
MEDIT = "/blog/meditazione-per-chi-inizia-guida-semplice"

CONTENUTO = f"""\
In Italia lo yoga è arrivato soprattutto come una cosa che si fa in una sala, su un tappetino, in calzamaglia. Un'ora di posizioni, un po' di respiro, cinque minuti sdraiati alla fine.

Quella è una parte. Nel sistema originale è la terza di otto, e non è la più importante.

Questa guida racconta l'insieme: da dove viene, com'è fatto, cosa succede la prima volta che entri in una sala, cosa dicono gli studi e come si sceglie da dove partire. Alla fine trovi anche le parole che sentirai dire e che nessuno ti spiega.

## Cos'è, in una frase

Lo yoga è un sistema di pratiche nato in India per portare l'attenzione dove di solito non sta: sul corpo mentre si muove, sul respiro mentre passa, sulla mente mentre si agita.

La parola viene dalla radice sanscrita *yuj*, unire. Cosa si unisca esattamente dipende da chi lo racconta — corpo e mente, individuo e universo, attenzione e momento presente — e questa vaghezza attraversa duemila anni di testi senza essersi mai risolta.

Quello su cui tutte le scuole concordano è più concreto: è una pratica, e funziona facendola.

## Da dove viene

La storia raccontata nelle brochure dice «cinquemila anni di tradizione». La storia vera è più interessante e ha quattro momenti.

**I testi antichi.** Il termine compare nei Veda e poi nelle Upanishad, fra il 1500 e il 500 avanti Cristo, in un contesto che è filosofico e rituale: nessuna posizione, nessuna sala.

**Patanjali, intorno al secondo secolo.** Gli *Yoga Sutra* mettono in ordine quello che circolava, in centonovantacinque frasi brevissime. È il testo che definisce gli otto rami di cui parliamo qui sotto, ed è il riferimento che ancora oggi tiene insieme scuole molto diverse fra loro.

**L'hatha yoga, fra l'undicesimo e il quindicesimo secolo.** È qui che entrano il corpo, le posizioni e le tecniche di respiro, in testi come la *Hatha Yoga Pradipika*. Le posizioni descritte sono poche decine, quasi tutte sedute, e servono a poter meditare a lungo.

**Il Novecento.** La lezione che facciamo oggi — sequenze fluide, saluti al sole, un'ora scandita — è stata composta in gran parte nel secolo scorso, soprattutto nella scuola di Krishnamacharya a Mysore, incrociando l'hatha con la ginnastica occidentale che circolava in India in quegli anni. Da lì passano i tre maestri che hanno formato l'Occidente: Iyengar, Pattabhi Jois, Desikachar.

Vale la pena saperlo. Non toglie niente alla pratica, toglie il fumo a chi vende una sequenza di quarant'anni fa come se fosse millenaria.

## Gli otto rami

È la parte che quasi nessuno racconta, perché non è quella che si vende. Ed è quella che riordina tutto il resto.

Patanjali descrive otto rami, e le posizioni sono il terzo.

**1. Yama — come stai con gli altri.** Cinque principi: non fare del male, dire il vero, non prendere quello che non ti spetta, usare bene la propria energia, non accumulare oltre il necessario.

**2. Niyama — come stai con te.** Altri cinque: pulizia, accontentarsi, disciplina, studio di sé, dedizione a qualcosa di più grande.

**3. Asana — le posizioni.** Nel testo originale ce n'è una sola definizione, e non parla di flessibilità: una posizione stabile e comoda. Tutto quello che si fa in una lezione moderna sta dentro questa riga.

**4. Pranayama — il respiro.** Le tecniche che lavorano sul respiro e, secondo la tradizione, sull'energia che ci passa dentro. È un ramo vastissimo: [le tecniche principali le abbiamo raccontate una per una]({PRANA}).

**5. Pratyahara — staccare i sensi.** Smettere di rincorrere quello che arriva da fuori. È il passaggio che fa da cerniera fra la parte esteriore e quella interiore.

**6. Dharana — la concentrazione.** Tenere l'attenzione su una cosa sola.

**7. Dhyana — la meditazione.** Quando quella attenzione smette di aver bisogno di sforzo.

**8. Samadhi — l'assorbimento.** Lo stato in cui la separazione fra chi osserva e cosa è osservato si allenta. È il punto d'arrivo dichiarato, ed è anche quello di cui si parla meno, perché non si insegna in un corso.

La conseguenza pratica: una scuola che lavora solo sul terzo ramo sta facendo una cosa legittima e parziale, e le scuole serie lo dicono.

## Cosa succede in una lezione

Se non ci sei mai stato, ecco come va, al netto delle differenze fra stili.

**Prima.** Arrivi dieci minuti prima, ti togli le scarpe all'ingresso, il tappetino spesso te lo prestano. Non serve abbigliamento tecnico: qualcosa di comodo in cui puoi piegarti. Si pratica a piedi nudi e a stomaco vuoto, o almeno due ore dopo un pasto.

**L'inizio.** Quasi sempre seduti, qualche minuto per posare l'attenzione sul respiro. Alcune scuole aprono con un *om* cantato insieme o con una frase in sanscrito: puoi restare in silenzio, nessuno se ne accorge.

**Il corpo.** La parte centrale, dai trenta ai cinquanta minuti. L'insegnante nomina le posizioni, spesso in sanscrito e in italiano, e le mostra. Passa fra i tappetini e a volte corregge con le mani: in una sala che lavora bene, ti viene chiesto prima se va bene essere toccato.

**La chiusura.** Cinque o dieci minuti sdraiati sulla schiena, immobili, coperti. Si chiama *savasana*, e chi pratica da anni la considera la parte più difficile.

**Namasté.** Il saluto finale. Significa più o meno «ti saluto», ed è una formalità, non un impegno spirituale.

La cosa più utile da sapere per la prima volta: **puoi fermarti quando vuoi**. Sederti, saltare una posizione, sdraiarti a metà lezione. Un insegnante preparato lo dice all'inizio; se non lo dice, vale lo stesso.

## Gli stili, in breve

Sotto lo stesso nome ci sono lezioni che non si somigliano: una di ashtanga e una di yin hanno in comune il tappetino e poco altro.

In sintesi grossolana: **hatha** è lento e didattico, **vinyasa** è fluido e continuo, **ashtanga** è una sequenza fissa e atletica, **yin** tiene le posizioni per minuti a terra, **kundalini** lavora su respiro, mantra e sequenze ripetute.

La versione lunga, con cosa aspettarsi da ciascuno e per chi funziona, sta in [le differenze fra i tipi di yoga]({STILI}).

## Il respiro, il riposo, la via meditativa

Tre direzioni in cui la pratica si allarga oltre la lezione, e ognuna è un mondo suo.

**Il respiro.** Il pranayama è il secondo grande ramo tecnico dopo le posizioni. Alcune tecniche calmano in tre minuti, altre sono a tutti gli effetti intense e chiedono un insegnante. [Qui le trovi una per una]({PRANA}).

**Il riposo.** Lo [yoga nidra]({NIDRA}) si pratica sdraiati, senza fare niente, seguendo una voce. È la porta più larga per chi pensa di non poter praticare: non richiede mobilità, esperienza né sforzo.

**La via meditativa.** Il [kriya yoga]({KRIYA}) è un percorso di meditazione che si riceve per iniziazione e a cui non ci si iscrive come a un corso. È utile sapere che esiste, se non altro per sciogliere l'omonimia con le sequenze del kundalini.

## Cosa dice la ricerca

Lo yoga è fra le pratiche di questo mondo con la letteratura più solida, e conviene distinguere dove le prove sono buone da dove sono deboli.

**Dove le prove sono buone.** Il **mal di schiena cronico lombare** è l'area più studiata: linee guida internazionali includono lo yoga fra gli approcci non farmacologici raccomandati, con efficacia paragonabile alla fisioterapia. Poi **equilibrio e mobilità negli anziani**, con riduzione del rischio di caduta. Poi **ansia e sintomi depressivi**, dove funziona come pratica di accompagnamento e non come trattamento a sé. E **qualità del sonno**, soprattutto nelle forme lente.

**Dove sono promettenti ma parziali.** Pressione arteriosa, dolore cronico non lombare, sintomi della menopausa, benessere in corso di terapie oncologiche: risultati incoraggianti, campioni ancora piccoli.

**Dove non ci sono.** Tutto quello che riguarda la cura di patologie. Nessuno studio sostiene che lo yoga curi una malattia, e chi lo afferma sta facendo un'altra cosa.

Un limite attraversa tutto il campo: è difficile costruire un gruppo di controllo per un'ora di movimento consapevole in un gruppo con un insegnante attento. Parte dell'effetto misurato è quello, e resta un effetto.

## A chi fa bene, e le poche cautele

Praticamente chiunque può cominciare, a qualsiasi età e a qualsiasi livello di rigidità. La flessibilità è un risultato, non un requisito, ed è il fraintendimento che tiene fuori più persone di ogni altro.

Le situazioni che chiedono attenzione, e che vanno dette all'insegnante prima della lezione, non dopo:

- **Gravidanza**, dove servono classi dedicate o adattamenti precisi
- **Ipertensione non controllata, glaucoma, distacco di retina**, per cui le posizioni capovolte sono sconsigliate
- **Ernie discali e problemi cervicali**, dove alcune posizioni vanno sostituite
- **Interventi chirurgici recenti**, con il via libera di chi ti ha operato
- **Osteoporosi grave**, che esclude le torsioni profonde e le flessioni in avanti spinte

Un insegnante preparato chiede queste cose all'inizio del corso. Se nessuno chiede niente, quella è già un'informazione.

## Come cominciare

**Scegli in base a dove parti, non a cosa suona bene.**

Se sei fermo da anni o hai più di sessant'anni, parti da **hatha** o da una classe *dolce*. Se cerchi movimento e sudore, **vinyasa**. Se sei rigido e stressato, **yin**. Se hai la schiena delicata, cerca **Iyengar**, che usa supporti e lavora sull'allineamento. Se l'idea di stare in piedi ti sembra troppo, comincia dallo [yoga nidra]({NIDRA}), che si fa sdraiati.

**Ti serve pochissimo.** Un tappetino, e all'inizio nemmeno quello. Abbigliamento comodo, niente scarpe, una bottiglia d'acqua.

**Vai in presenza le prime volte.** I video sono utili dopo, quando sai riconoscere una posizione sbagliata nel tuo corpo. All'inizio serve qualcuno che ti guardi.

**Prova almeno tre lezioni prima di giudicare.** La prima si passa a capire dove mettere le mani. Ed è normale non farsi piacere il primo insegnante trovato: prova un'altra sala prima di concludere che lo yoga non fa per te.

**Due volte a settimana è la soglia** in cui la maggior parte delle persone comincia a sentire un cambiamento. Una volta a settimana mantiene, tre accelerano.

**Su come si sceglie chi ti insegna** valgono i criteri generali di [come capire se un operatore è serio]({SERIO}), con una specificità: nello yoga esistono formazioni riconoscibili — le più diffuse contano 200 o 500 ore — e un insegnante serio le dichiara senza che tu debba chiederle.

## Le parole che sentirai

Il piccolo glossario che nessuno ti dà, e che serve la prima volta.

**Asana** — la posizione. Ogni nome che finisce in *-asana* è una posizione.

**Vinyasa** — il collegamento fra una posizione e l'altra attraverso il respiro. Dà il nome a uno stile intero.

**Pranayama** — le tecniche di respiro.

**Drishti** — il punto in cui appoggi lo sguardo. Serve all'equilibrio e all'attenzione.

**Bandha** — una contrazione interna, tipicamente del pavimento pelvico o dell'addome. Se non capisci l'indicazione, ignorala: si impara col tempo.

**Savasana** — la posizione finale, sdraiati sulla schiena. Letteralmente «posizione del cadavere».

**Om** — il suono cantato all'inizio o alla fine. Puoi tacere.

**Namasté** — il saluto di chiusura.

**Sanscrito** — la lingua in cui sono nominate le posizioni. Nessuno si aspetta che tu la sappia.

## Il punto

Lo yoga è una delle poche pratiche di questo mondo che regge sia la prova della ricerca sia quella dei duemila anni. Ma il modo in cui funziona è banale e va detto: funziona se lo fai, con regolarità, in una sala dove ti senti a tuo agio.

Il resto — lo stile, il maestro, il tappetino giusto — viene dopo, e conta molto meno di quanto sembri all'inizio.

## Domande frequenti

**Devo essere flessibile per fare yoga?**
No, ed è il fraintendimento che tiene lontane più persone di ogni altro. La flessibilità è un effetto della pratica, non una condizione per cominciare.

**Quante volte a settimana serve praticare?**
Due volte è la soglia in cui la maggior parte delle persone nota un cambiamento. Una volta mantiene quello che c'è.

**Lo yoga è una religione?**
No. Nasce dentro un contesto culturale e filosofico indiano, e alcune scuole ne mantengono elementi rituali come i canti. Non richiede alcuna adesione religiosa, e la maggior parte delle sale in Italia lo pratica in forma laica.

**Quanto costa una lezione in Italia?**
La forbice reale va dai 10 ai 20 euro a lezione singola, con abbonamenti mensili spesso fra i 50 e gli 80 euro. Le prime lezioni di prova sono di solito gratuite o scontate.

**Meglio a casa con i video o in una sala?**
In sala all'inizio, perché serve qualcuno che veda cosa fa il tuo corpo. A casa dopo, quando la pratica è entrata e i video diventano un modo per mantenerla.

**Che differenza c'è fra yoga e pilates?**
Il pilates nasce nel Novecento come metodo di rieducazione posturale, lavora soprattutto sulla forza del centro e non ha una componente filosofica o meditativa. Lo yoga arriva da una tradizione più antica e più larga, di cui le posizioni sono una parte.

**Posso fare yoga in gravidanza?**
Sì, con classi dedicate o con adattamenti concordati con l'insegnante, e dopo aver sentito chi ti segue. Alcune posizioni sono da evitare, soprattutto nel primo trimestre e nelle torsioni.

**Lo yoga fa dimagrire?**
Gli stili dinamici hanno un consumo calorico paragonabile a una camminata veloce, quindi contribuiscono. L'effetto più documentato è però indiretto: migliora il sonno, abbassa lo stress e cambia il rapporto con la fame.

**Da quale stile conviene cominciare?**
Hatha se vuoi capire le posizioni con calma, vinyasa se cerchi movimento, yin se sei rigido e teso. La [guida agli stili]({STILI}) entra nel dettaglio.

**Serve meditare per fare yoga?**
No, e non è nemmeno l'ordine consueto: molte persone arrivano alla [meditazione]({MEDIT}) dopo mesi di pratica sul tappetino, quando lo stare fermi ha smesso di sembrare impossibile.
"""

# i quattro figli puntavano l'uno all'altro senza mai risalire.
AGGIUNTE = [
    (STILI.split("/blog/")[1],
     "Entri in una scuola di yoga e sul volantino ci sono sei nomi",
     f"Se stai partendo da zero, la [guida generale allo yoga](/blog/{SLUG}) "
     f"racconta da dove viene la pratica e cosa succede in una lezione. Qui "
     f"entriamo nelle differenze fra stili.\n\n"
     f"Entri in una scuola di yoga e sul volantino ci sono sei nomi"),
    (PRANA.split("/blog/")[1],
     "## Domande frequenti",
     f"Il pranayama è il quarto degli otto rami dello yoga: come si "
     f"incastra con gli altri lo racconta la [guida generale]"
     f"(/blog/{SLUG}).\n\n## Domande frequenti"),
    (NIDRA.split("/blog/")[1],
     "## Domande frequenti",
     f"Se dello yoga conosci solo le posizioni, la [guida generale]"
     f"(/blog/{SLUG}) racconta l'insieme in cui questa pratica sta.\n\n"
     f"## Domande frequenti"),
    (KRIYA.split("/blog/")[1],
     "## Domande frequenti",
     f"Per il quadro d'insieme — le origini, gli otto rami, gli stili — "
     f"parti dalla [guida generale allo yoga](/blog/{SLUG}).\n\n"
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
        "related_slugs": [STILI.split("/blog/")[1], PRANA.split("/blog/")[1],
                          NIDRA.split("/blog/")[1]],
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
            print(f"  risale gia' in {slug[:44]}")
        elif vecchio in d["content"]:
            await db.articles.update_one({"slug": slug}, {"$set": {
                "content": d["content"].replace(vecchio, nuovo, 1)}})
            print(f"  risalita aggiunta in {slug[:44]}")
        else:
            print(f"  NON TROVATO in {slug[:44]} — controllare a mano")

    # il pilastro entra anche fra i correlati dei figli
    for figlio in [STILI, PRANA, NIDRA, KRIYA]:
        s = figlio.split("/blog/")[1]
        d = await db.articles.find_one({"slug": s}, {"_id": 0,
                                                    "related_slugs": 1})
        rel = d.get("related_slugs") or []
        if SLUG not in rel:
            await db.articles.update_one({"slug": s}, {"$set": {
                "related_slugs": [SLUG] + rel[:2]}})

    print("\npubblicato")


if __name__ == "__main__":
    asyncio.run(main("--dry-run" in sys.argv))
