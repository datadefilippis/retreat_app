"""NA8 — shiatsu e mindfulness: due termini molto cercati e senza casa.

SHIATSU. Nella guida al massaggio e' una voce fra nove, e merita di
piu': e' la porta d'ingresso al lavoro sul corpo per chi non vuole
spogliarsi, ed e' l'unica disciplina di questa famiglia che in
Giappone ha un riconoscimento statale — il ministero della salute lo
ha inquadrato come terapia negli anni Cinquanta. In Italia no, ed e'
un'asimmetria che genera equivoci esattamente come per l'ayurveda.

MINDFULNESS. Finora era una sezione dentro la guida alla meditazione,
ma e' un termine che le persone cercano da solo e che significa una
cosa precisa: un protocollo laico e strutturato, nato nel 1979 in un
ospedale universitario americano per pazienti con dolore cronico. Chi
cerca "mindfulness" non sta cercando "meditazione".

LA PARTE CHE VALE, e che in italiano non si legge quasi mai: la
critica della MCMINDFULNESS. La pratica e' stata estratta da una
cornice etica e rivenduta come strumento di produttivita' aziendale,
al punto che a volte serve a far tollerare condizioni di lavoro che
andrebbero cambiate. E' una critica interna e seria, portata avanti da
studiosi come Ronald Purser, e un articolo che presenta la mindfulness
senza nominarla e' un depliant.

    venv/bin/python scripts/na8_shiatsu_e_mindfulness.py [--dry-run]
"""
import asyncio
import os
import re
import sys
import uuid
from datetime import datetime, timezone

MASSAGGIO = "/blog/massaggio-olistico-tipi-cosa-aspettarsi"
MEDIT = "/blog/meditazione-per-chi-inizia-guida-semplice"
SERIO = "/blog/come-capire-se-un-operatore-olistico-e-serio"
KIT = "/blog/kit-pratiche-quotidiane-15-minuti"
STRESS = "/blog/pratiche-olistiche-contro-stress-cosa-funziona"
CAMMINI = "/blog/camminare-bagni-di-foresta-cammini"
CHAKRA = "/blog/chakra-cosa-sono-i-sette-come-si-usano"
PRANA = "/blog/pranayama-tecniche-respirazione-yoga"

SLUG_S = "shiatsu-cose-come-funziona-una-seduta"
TITOLO_S = "Shiatsu: cos'è, come funziona una seduta, a cosa serve"
DESCR_S = (
    "Il lavoro sul corpo che si riceve vestiti: origini, le due scuole, "
    "come si svolge una seduta, cosa dice la ricerca e come scegliere."
)

CONTENUTO_S = f"""\
Fra le pratiche che lavorano sul corpo, lo shiatsu è quella che spiazza di più chi arriva la prima volta: si resta **vestiti**, si sta **a terra** su un futon, e non c'è olio.

Ed è proprio per questo che per molte persone è la porta d'ingresso più semplice al lavoro sul corpo.

Questa guida racconta cos'è, da dove viene, come si svolge una seduta, cosa dice la ricerca e come si sceglie chi lo pratica.

## Cos'è

*Shiatsu* significa letteralmente «pressione con le dita». Chi conduce applica una pressione perpendicolare e sostenuta con pollici, palmi, gomiti e a volte ginocchia, lungo percorsi del corpo che nella tradizione orientale corrispondono ai meridiani, insieme a stiramenti e mobilizzazioni delle articolazioni.

Due cose lo distinguono dal massaggio a cui siamo abituati.

**Non c'è scorrimento.** La mano non scivola: si appoggia, affonda lentamente, resta, e si sposta. La sensazione è più simile a un peso che a una carezza.

**Chi riceve non è passivo.** Il respiro di chi riceve guida il ritmo della pressione, e in molte scuole viene chiesto esplicitamente di respirare in un certo modo.

## Da dove viene

Più recente di quanto sembri, e con un dettaglio che vale la pena conoscere.

Lo shiatsu nasce in **Giappone nella prima metà del Novecento**, dall'incontro fra le tecniche manuali tradizionali giapponesi, l'agopuntura e nozioni di anatomia occidentale. Le due figure di riferimento sono **Tokujiro Namikoshi**, che ne codifica una versione basata su punti e pressione, e **Shizuto Masunaga**, che negli anni Settanta sviluppa lo *zen shiatsu*, con una teoria dei meridiani estesa e una diagnosi addominale.

Il dettaglio: in **Giappone lo shiatsu è riconosciuto dallo Stato**, con un percorso formativo regolamentato e una licenza rilasciata dal ministero della salute a partire dagli anni Cinquanta.

**In Italia no.** Chi lo pratica qui non ha un titolo sanitario e rientra fra le professioni non organizzate della legge 4/2013. È la stessa asimmetria dell'ayurveda, e genera gli stessi equivoci: la serietà della formazione giapponese non si trasferisce automaticamente a chiunque usi quel nome.

## Le due scuole

Sapere quale hai davanti spiega perché due sedute possono somigliarsi poco.

**Namikoshi.** Lavora su punti anatomicamente definiti, con una sequenza abbastanza standard e una lettura vicina alla fisiologia occidentale. Più sistematico, più prevedibile.

**Masunaga, o zen shiatsu.** Lavora sui meridiani estesi, con una diagnosi che parte dalla palpazione dell'addome e una seduta che cambia in base a quello che chi conduce sente. Più interpretativo, meno standardizzato.

Molti operatori italiani mescolano le due impostazioni. La domanda «in che scuola ti sei formato» è legittima e la risposta è informativa.

## Come si svolge una seduta

Dura in genere fra i cinquanta e i settantacinque minuti, e in Italia costa fra i 50 e gli 80 euro.

**Il colloquio.** Qualche minuto su come stai, su eventuali dolori, su condizioni di salute e terapie in corso. In alcune scuole si aggiunge la palpazione dell'addome, che a chi non se l'aspetta va spiegata prima.

**La posizione.** Si sta vestiti, con abiti comodi e di cotone, distesi su un futon a terra. Si cambia posizione più volte: supino, prono, sul fianco, a volte seduti.

**Il lavoro.** Chi conduce si sposta intorno e usa il proprio peso più che la forza. La pressione è profonda ma non deve essere dolorosa: la soglia giusta è quella in cui puoi continuare a respirare normalmente.

**La chiusura.** Qualche minuto fermi, poi ci si rialza con calma.

## Cosa si prova

Le descrizioni ricorrenti sono tre.

**Una pesantezza piacevole**, diversa dal rilassamento di un massaggio con l'olio: più radicata, meno vellutata.

**Punti che «parlano».** Capita che una pressione in un punto produca una sensazione altrove. È un fenomeno di riferimento noto e non ha bisogno della teoria dei meridiani per essere reale.

**Stanchezza dopo**, soprattutto le prime volte. Molte persone dormono meglio la notte successiva.

## Cosa dice la ricerca

Va detto con precisione: **le prove specifiche sullo shiatsu sono poche e deboli**.

Esistono studi su campioni piccoli che riportano miglioramenti su dolore lombare, ansia e qualità del sonno, ma con disegni sperimentali fragili e difficoltà evidenti a costruire un confronto credibile. Le revisioni sistematiche concludono in genere che i dati non bastano a trarre conclusioni.

Quello che è documentato meglio riguarda la famiglia più larga a cui lo shiatsu appartiene: il **contatto manuale prolungato** ha effetti misurabili su dolore percepito, ansia e tensione muscolare, ed è la stessa base su cui poggia [il massaggio in generale]({MASSAGGIO}).

E i meridiani? Sono una mappa tradizionale senza corrispettivo anatomico, esattamente come i [chakra]({CHAKRA}). Serve come sistema di orientamento a chi lavora, non come descrizione del corpo.

In pratica: pratica di benessere, mai terapia sostitutiva.

## Controindicazioni

- **Febbre e infezioni in corso**
- **Trombosi o sospetta trombosi**, la controindicazione più seria
- **Fratture recenti, osteoporosi grave, protesi recenti**, dove la pressione va evitata o adattata
- **Gravidanza**, che richiede posizioni dedicate e l'esclusione di alcuni punti: serve un operatore formato su questo
- **Tumori in corso**, dove serve il via libera dell'oncologo
- **Terapia anticoagulante**, che sconsiglia le pressioni profonde
- **Lesioni cutanee** nelle zone da trattare

## Tre punti da premere da soli

Non sostituiscono una seduta, e sono un modo semplice di capire di cosa si parla. Pressione ferma per un minuto, respirando lentamente.

**Fra pollice e indice.** Nell'incavo carnoso del dorso della mano. È il punto più usato per la tensione a testa e collo. **Da evitare in gravidanza.**

**Sotto la nuca.** Nelle due fossette ai lati della colonna, dove il collo incontra il cranio. Pressione con i pollici, testa leggermente appoggiata all'indietro.

**Quattro dita sotto il ginocchio**, sul lato esterno della tibia, nel muscolo. È il punto della tradizione legato all'energia generale e alla digestione.

Se una pressione fa male in modo acuto, togli la mano: la regola è la stessa della seduta.

## Come si sceglie chi lo pratica

Oltre ai [criteri generali]({SERIO}), quattro domande.

**In quale scuola ti sei formato e per quante ore?** Le formazioni serie in Italia durano tre anni con pratica supervisionata, non un fine settimana.

**Namikoshi o Masunaga?** La risposta dice come lavorerà.

**Sei coperto da un'assicurazione professionale?**

**Cosa fai se ho un problema che non è di tua competenza?** La risposta giusta contiene il nome di una figura sanitaria.

E il criterio che vale più di tutti, identico a quello del massaggio: **una seduta non deve fare male**. Scomoda sì, respirabile sempre.

## Domande frequenti

**Devo spogliarmi?**
No, ed è la caratteristica dello shiatsu. Si sta vestiti, con abiti comodi e preferibilmente di cotone.

**Fa male?**
La pressione è profonda ma sostenibile. Se stringi i denti o trattieni il fiato è troppa, e dirlo è tuo diritto.

**Che differenza c'è con il massaggio tradizionale?**
Il massaggio scorre sulla pelle con olio; lo shiatsu appoggia e affonda, senza scorrimento e senza olio, e include stiramenti.

**È come l'agopuntura?**
Condivide la mappa tradizionale dei meridiani, ma usa la pressione delle mani invece degli aghi. L'agopuntura in Italia è atto medico, lo shiatsu no.

**Quante sedute servono?**
Per una tensione specifica, un ciclo di quattro o cinque ravvicinate. Per il benessere generale, una al mese è la frequenza più comune.

**Posso farlo in gravidanza?**
Sì, con un operatore formato specificamente: cambiano le posizioni e alcuni punti vanno evitati. Diffida di chi non fa questa distinzione.

**Serve credere nei meridiani?**
No. Sono una mappa di orientamento per chi lavora; l'effetto della pressione sui tessuti e sul sistema nervoso non dipende da cosa credi.
"""

SLUG_M = "mindfulness-cose-mbsr-come-funziona"
TITOLO_M = "Mindfulness: cos'è, come funziona un protocollo MBSR"
DESCR_M = (
    "Il protocollo delle otto settimane, gli esercizi che puoi fare oggi, "
    "cosa dice la ricerca e la critica alla mindfulness aziendale."
)

CONTENUTO_M = f"""\
«Mindfulness» è una di quelle parole che a forza di comparire ovunque — nelle app, nei corsi aziendali, sulle copertine — ha smesso di significare qualcosa di preciso.

Significa invece una cosa piuttosto precisa, e ha una data di nascita: **1979**, in un ospedale universitario americano, dentro un programma per pazienti con dolore cronico che la medicina non riusciva più ad aiutare.

Questa guida racconta cos'è, come è fatto il protocollo, cosa si può provare stasera, cosa dice la ricerca, e una critica seria che di solito non compare.

## Cos'è

La definizione classica, di Jon Kabat-Zinn, è: **prestare attenzione in un modo particolare — intenzionalmente, al momento presente, senza giudicare**.

Tre parole fanno il lavoro.

**Intenzionalmente.** Non è distrarsi bene: è scegliere dove mettere l'attenzione.

**Al momento presente.** Non ai piani, non ai ricordi. A quello che c'è adesso, comprese le cose spiacevoli.

**Senza giudicare.** Notare «sto pensando ad altro» invece di «sto sbagliando». È la parte più difficile e quella che fa la differenza.

Come pratica, la mindfulness discende dalla vipassana buddhista, da cui è stata **estratta e resa laica** deliberatamente, per poter entrare in un ospedale pubblico. Quella scelta è la ragione del suo successo, e anche l'origine delle critiche di cui parliamo più avanti.

## Il protocollo delle otto settimane

Il programma di riferimento si chiama **MBSR**, *Mindfulness-Based Stress Reduction*, ed è nato al centro medico dell'Università del Massachusetts. Ha una forma precisa, ed è utile conoscerla per riconoscere un corso vero.

**Otto settimane**, con un incontro di gruppo settimanale di due ore e mezza circa.

**Una giornata intera** di pratica in silenzio, di solito fra la sesta e la settima settimana.

**Pratica a casa tutti i giorni**, intorno ai quaranta minuti, con tracce audio guidate. È la parte che le persone sottovalutano ed è dove sta il programma.

**Quattro pratiche formali** che si alternano: la **scansione del corpo**, la **meditazione seduta** sul respiro e sulle sensazioni, il **movimento consapevole** con posizioni semplici derivate dallo yoga, e la **camminata consapevole**.

**Esercizi informali** da portare nella giornata: mangiare un pasto in silenzio, notare un'attività di routine, registrare gli eventi piacevoli e spiacevoli.

Esiste anche l'**MBCT**, *Mindfulness-Based Cognitive Therapy*, che adatta lo stesso impianto alla prevenzione delle ricadute depressive, con l'aggiunta di elementi di terapia cognitiva. È il protocollo con il riconoscimento clinico più solido della famiglia.

## Cosa puoi provare stasera

Tre esercizi del programma, praticabili senza corso.

**Lo spazio di respiro dei tre minuti.** È il più usato e il più portatile.
- *Primo minuto:* cosa c'è adesso? Che pensieri, che emozioni, che sensazioni nel corpo. Solo notare.
- *Secondo minuto:* porta tutta l'attenzione sul respiro. Solo il respiro.
- *Terzo minuto:* allarga l'attenzione a tutto il corpo, come se respirassi con la pelle.
Si fa in coda, prima di una riunione, dopo una telefonata difficile.

**La scansione del corpo.** Sdraiati, si porta l'attenzione una zona alla volta dai piedi alla testa, notando quello che c'è, comprese le zone in cui non si sente niente. Venti o quarantacinque minuti. È la pratica su cui il protocollo insiste di più le prime settimane.

**Il primo boccone.** Al prossimo pasto, mangia il primo boccone senza fare altro: guardalo, sentine l'odore, mastica lentamente, nota il sapore che cambia. È l'esercizio che le persone ricordano di più a distanza di anni.

Queste si incastrano bene con le altre pratiche brevi del [kit dei quindici minuti]({KIT}).

## Cosa dice la ricerca

È la pratica di questo mondo con la letteratura più ampia, e questo rende ancora più importante distinguere.

**Dove le prove sono buone.** La **prevenzione delle ricadute depressive** con MBCT in persone con episodi ricorrenti è l'area più solida, tanto da essere entrata in linee guida cliniche di alcuni paesi come intervento raccomandato. Poi la riduzione di **stress percepito e sintomi d'ansia**, con effetti replicati. Poi il **dolore cronico**, dove l'effetto documentato non è tanto sull'intensità quanto sulla relazione con il dolore e sull'interferenza con la vita quotidiana — che è precisamente lo scopo per cui il programma è nato.

**Dove sono modeste.** Attenzione, memoria di lavoro, prestazioni cognitive: effetti piccoli e non sempre replicati.

**Il limite metodologico.** Molti studi confrontano un corso di mindfulness con il non fare nulla, invece che con un'altra attività di pari impegno e attenzione. Quando il confronto è con un programma attivo, le differenze si assottigliano. Non significa che non funzioni: significa che una parte dell'effetto è il gruppo, l'impegno e l'attenzione ricevuta — cosa che vale [per molte pratiche]({STRESS}).

**E gli effetti indesiderati esistono**, come per ogni pratica meditativa: ansia che aumenta, senso di distacco, riemersione di materiale doloroso. Ne parliamo nella [guida alla meditazione]({MEDIT}).

## La critica che di solito non si legge

Merita spazio perché viene da dentro, non dai detrattori.

La mindfulness è stata estratta da una tradizione in cui la pratica dell'attenzione era **inseparabile da una cornice etica**: come si vive, come si tratta gli altri, cosa si sceglie di fare. Nella versione laica quella cornice è stata lasciata fuori, per buone ragioni pratiche.

Il risultato, secondo questa critica — associata soprattutto al lavoro di **Ronald Purser**, che l'ha chiamata *McMindfulness* — è che la pratica può diventare uno strumento di adattamento: un corso aziendale che insegna ai dipendenti a gestire lo stress di condizioni di lavoro che nessuno intende cambiare, spostando su di loro la responsabilità di un problema che non hanno creato.

Non è un argomento contro la pratica. È un argomento contro **l'uso della pratica come sostituto di un cambiamento necessario**, ed è un criterio utile anche a livello personale: se stai imparando a tollerare una situazione che andrebbe affrontata, la mindfulness sta lavorando per la parte sbagliata.

## Come si riconosce un corso serio

**Segue il protocollo delle otto settimane**, con la giornata di pratica e la pratica quotidiana a casa. Un corso di quattro incontri da un'ora non è MBSR, e chiamarlo così è scorretto.

**Chi lo conduce ha una formazione dichiarata** presso un centro riconosciuto, e una propria pratica personale continuativa. È il campo in cui questa seconda cosa conta di più.

**C'è un colloquio prima di iscriversi**, in cui ti viene chiesto come stai e se stai attraversando un periodo particolare.

**Ti viene detto cosa non è.** Un corso serio dice che non è una terapia, che non sostituisce un percorso clinico e che possono emergere cose difficili.

**Il gruppo è di dimensioni gestibili**, e chi conduce sa cosa fare se qualcuno sta male.

In Italia un percorso MBSR completo costa in genere fra i 300 e i 600 euro. Valgono anche i [criteri generali]({SERIO}).

## Domande frequenti

**Che differenza c'è fra mindfulness e meditazione?**
La mindfulness è un tipo di meditazione, reso laico e strutturato in protocolli. La [meditazione]({MEDIT}) è la famiglia grande, che comprende anche concentrazione, mantra, amorevolezza e pratiche devozionali.

**Serve fare un corso o basta un'app?**
Le app funzionano per cominciare e per mantenere l'abitudine. Il protocollo di otto settimane in gruppo è un'altra cosa: c'è il confronto, c'è qualcuno che risponde, e c'è l'impegno che deriva dall'esserci.

**Quanto tempo al giorno serve?**
Il protocollo chiede circa quaranta minuti. Fuori dal protocollo, dieci minuti al giorno costanti valgono più di un'ora ogni tanto.

**È una pratica religiosa?**
No. Discende da una tradizione buddhista ma è stata deliberatamente resa laica per poter entrare in contesti sanitari e scolastici.

**Funziona per l'ansia?**
Gli effetti su stress percepito e sintomi d'ansia sono fra i più replicati. Per un disturbo d'ansia diagnosticato affianca un percorso clinico, non lo sostituisce.

**Posso farla se sono in terapia?**
Spesso sì e a volte è il terapeuta stesso a proporla, ma parlane prima con chi ti segue.

**Cos'è la McMindfulness?**
La critica secondo cui la pratica, separata dalla sua cornice etica, può diventare uno strumento per far tollerare condizioni che andrebbero cambiate. È una critica interna e vale la pena conoscerla.

**Da dove comincio oggi?**
Dallo spazio di respiro dei tre minuti, due volte al giorno per una settimana. Se ti resta addosso, il passo successivo è un percorso di otto settimane.
"""

PEZZI = [
    (SLUG_S, TITOLO_S, DESCR_S, CONTENUTO_S, "massaggio",
     [MASSAGGIO.split("/blog/")[1], "chakra-cosa-sono-i-sette-come-si-usano",
      "come-capire-se-un-operatore-olistico-e-serio"]),
    (SLUG_M, TITOLO_M, DESCR_M, CONTENUTO_M, "meditazione",
     [MEDIT.split("/blog/")[1], KIT.split("/blog/")[1],
      STRESS.split("/blog/")[1]]),
]

AGGIUNTE = [
    ("massaggio-olistico-tipi-cosa-aspettarsi", "## Domande frequenti",
     f"Fra queste tecniche, quella che piu' spesso diventa una pratica a se'"
     f" e' lo [shiatsu](/blog/{SLUG_S}): si riceve vestiti, a terra, e in "
     f"Giappone ha un riconoscimento statale che in Italia non ha.\n\n"
     f"## Domande frequenti"),
    ("meditazione-per-chi-inizia-guida-semplice", "## Domande frequenti",
     f"Della mindfulness, che e' la forma laica e strutturata piu' diffusa e "
     f"la piu' studiata, abbiamo scritto [una guida a parte](/blog/{SLUG_M}):"
     f" il protocollo delle otto settimane, cosa provare stasera e la "
     f"critica alla versione aziendale.\n\n## Domande frequenti"),
    ("pratiche-olistiche-contro-stress-cosa-funziona", "## Domande frequenti",
     f"Sulla mindfulness, che in questo elenco e' la voce con la letteratura "
     f"piu' ampia, abbiamo scritto [nel dettaglio](/blog/{SLUG_M}).\n\n"
     f"## Domande frequenti"),
]


async def main(dry_run: bool) -> None:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from database import db

    for slug, titolo, descr, contenuto, categoria, correlati in PEZZI:
        print(f"{titolo}\n  slug: {slug}  |  categoria: {categoria}\n"
              f"  parole: {len(contenuto.split())}  |  "
              f"descrizione: {len(descr)} caratteri")
        esistente = await db.articles.find_one({"slug": slug}, {"_id": 0, "id": 1})
        print("  stato:", "aggiornato" if esistente else "nuovo")
        if dry_run:
            continue
        now = datetime.now(timezone.utc)
        campi = {"title": titolo, "description": descr, "content": contenuto,
                 "category": categoria, "author_name": "Aurya",
                 "published": True, "updated_at": now, "translations": {},
                 "related_slugs": correlati}
        if not esistente:
            campi |= {"id": str(uuid.uuid4()), "slug": slug,
                      "created_at": now, "published_at": now}
        await db.articles.update_one({"slug": slug}, {"$set": campi},
                                     upsert=True)
        doc = await db.articles.find_one({"slug": slug},
                                         {"_id": 0, "featured_image_url": 1})
        if not doc.get("featured_image_url"):
            from routers.articles import _autogen_cover
            url = await _autogen_cover(slug, categoria)
            if url:
                await db.articles.update_one({"slug": slug}, {"$set": {
                    "featured_image_url": url}})
                print(f"  copertina: {url}")

    if not dry_run:
        for slug, vecchio, nuovo in AGGIUNTE:
            d = await db.articles.find_one({"slug": slug}, {"_id": 0,
                                                            "content": 1})
            if not d:
                print(f"  ASSENTE {slug}")
            elif nuovo.split("\n\n")[0] in d["content"]:
                print(f"  link gia' presente in {slug[:42]}")
            elif vecchio in d["content"]:
                await db.articles.update_one({"slug": slug}, {"$set": {
                    "content": d["content"].replace(vecchio, nuovo, 1)}})
                print(f"  link aggiunto in {slug[:42]}")
            else:
                print(f"  NON TROVATO in {slug[:42]}")

    print("\n── controlli")
    arts = [a async for a in db.articles.find({}, {"_id": 0, "slug": 1,
                                                   "content": 1,
                                                   "featured_image_url": 1})]
    slugs = {a["slug"] for a in arts}
    rotti = [(a["slug"], l) for a in arts
             for l in re.findall(r"\]\(/blog/([a-z0-9-]+)\)", a["content"])
             if l not in slugs]
    orfani = [a["slug"] for a in arts
              if not any(f"/blog/{a['slug']})" in b["content"]
                         for b in arts if b["slug"] != a["slug"])]
    tic = re.compile(r"(con onest|onestà:|la parte onesta|senza misteri|"
                     r"dalla nostra esperienza)", re.I)
    print(f"  link rotti: {rotti or 'nessuno'}")
    print(f"  vicoli: {orfani or 'nessuno'}")
    print(f"  tic: {sum(len(tic.findall(a['content'])) for a in arts)}")
    print(f"  copertine distinte: "
          f"{len({a.get('featured_image_url') for a in arts})} su {len(arts)}")
    print(f"  TOTALE: {len(arts)} articoli, "
          f"{sum(len(a['content'].split()) for a in arts)} parole")

    if dry_run:
        print("\n--dry-run: nessuna scrittura")


if __name__ == "__main__":
    asyncio.run(main("--dry-run" in sys.argv))
