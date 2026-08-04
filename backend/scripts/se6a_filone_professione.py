# -*- coding: utf-8 -*-
"""SE6a — il filone professione: tre articoli per chi lavora nel benessere.

PERCHE' QUESTI TRE. L'analisi SEO (docs/SEO_AUDIT_PIANO_2026-08.md) ha
trovato il cluster "professione olistica" quasi scoperto nelle SERP
italiane: le query esistono (codice ATECO, assicurazione, legge 4/2013),
la concorrenza e' fatta di blog commerciali di scuole e software, e ogni
lettore e' UN LEAD del funnel professionisti — il funnel che conta in
fase rete. I tre pezzi completano la guida partita IVA gia' pubblicata
(hub) come approfondimenti (spoke), con link incrociati.

REGOLE RISPETTATE. Niente numeri inventati: dove le fonti divergono
(i codici ATECO dopo la riforma 2025) si dice che divergono; niente
premi assicurativi sparati; l'unico link esterno e' Normattiva (testo
della legge), gia' in whitelist. Voce di casa: scena in apertura,
seconda persona, zero promesse, FAQ nel formato del rich snippet.

Idempotente; da rieseguire in produzione al lancio.

    venv/bin/python scripts/se6a_filone_professione.py [--dry-run]
"""
import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone

NORMATTIVA = ("https://www.normattiva.it/uri-res/N2Ls?"
              "urn:nir:stato:legge:2013-01-14;4")

ARTICOLI = [
    # ── 1. Codice ATECO ──────────────────────────────────────────────
    {
        "slug": "codice-ateco-operatore-olistico",
        "title": "Codice ATECO per operatori olistici: quale scegliere",
        "description": ("I codici ATECO per chi lavora nel benessere "
                        "olistico dopo la riforma 2025: le famiglie fra "
                        "cui scegliere, cosa cambia davvero e gli errori "
                        "da evitare."),
        "category": "operatori",
        "related": ["partita-iva-operatore-olistico-fiscalita-guida",
                    "assicurazione-rc-operatore-olistico",
                    "legge-4-2013-professioni-olistiche"],
        "content": """Il modulo è quasi finito. Nome, indirizzo, regime fiscale. Poi arriva una casella piccola che chiede una cosa enorme: il codice dell'attività. Sei caratteri che dicono allo Stato che lavoro fai, e che nessuno ti ha mai spiegato dove trovare.

Questa guida serve a capire il panorama prima della conversazione con il commercialista. Non al posto di quella conversazione: il codice giusto dipende dal tuo mix di attività, e sceglierlo da un articolo, questo compreso, è l'errore più comune di chi apre da solo.

## Cos'è il codice ATECO

ATECO è la classificazione delle attività economiche usata da Agenzia delle Entrate, INPS e Camere di commercio. Quando apri la partita IVA dichiari uno o più codici, e da quei codici discendono cose molto concrete: la gestione previdenziale in cui versi, il coefficiente con cui il regime forfettario calcola il tuo reddito, perfino gli obblighi assicurativi o di sicurezza in certi casi.

Nel 2025 la classificazione è stata aggiornata: la nuova ATECO 2025 ha sostituito la versione del 2007, alcuni codici sono stati rinumerati e sono comparse voci nuove che riguardano da vicino il mondo olistico. Se leggi guide scritte prima della riforma, i numeri potrebbero non corrispondere più.

## Le famiglie fra cui si sceglie

Per le discipline olistiche non esiste un codice unico, e le fonti non sempre concordano sull'inquadramento migliore. Quello che si può dire con onestà è quali famiglie ricorrono.

**I servizi alla persona.** Il contenitore storico è il 96.09.09, "altre attività di servizi per la persona", il codice residuale in cui sono finiti per anni operatori olistici, counselor e figure affini. Resta la scelta più usata per chi offre percorsi di benessere non sanitari e non estetici.

**L'area della medicina complementare.** La classificazione 2025 ha introdotto voci dedicate alle attività di medicina complementare e alle tecniche di trattamento del corpo, in cui rientrano pratiche come naturopatia e discipline energetiche. È una novità rilevante: per la prima volta alcune attività olistiche hanno un nome proprio nella classificazione, con conseguenze su previdenza e coefficiente che vanno valutate caso per caso.

**L'insegnamento.** Chi insegna una pratica, per esempio yoga o meditazione in forma di corso, ragiona su codici diversi: quelli della formazione (l'area 85.52 dei corsi) o quelli delle attività sportive e del benessere, a seconda di come l'attività è strutturata. Un insegnante che tiene corsi regolari e un operatore che riceve su appuntamento fanno mestieri diversi anche per l'ATECO.

**Più attività, più codici.** Si può avere un codice principale e codici secondari. Chi tiene sedute individuali, insegna in un corso settimanale e organizza un ritiro l'anno non deve schiacciare tutto in una casella: deve raccontare il mix com'è.

## Perché la scelta pesa davvero

Nel regime forfettario le imposte non si calcolano sul reddito reale ma su una percentuale dei ricavi, il coefficiente di redditività, che dipende dal gruppo ATECO. Fra un gruppo e l'altro la differenza può essere di dieci punti e più: stesso incasso, imponibile diverso. È il motivo per cui la scelta va fatta guardando l'attività reale, non il coefficiente più basso: un codice che non corrisponde a quello che fai è un problema che si presenta al primo controllo, e costa più di quello che ha fatto risparmiare.

Il codice incide anche sulla gestione previdenziale: a seconda dell'inquadramento si versa alla Gestione separata INPS o alla gestione commercianti, con regole e importi molto diversi. Anche qui: è il mestiere del commercialista, non di un blog.

## Gli errori che vediamo più spesso

**Copiare il codice di un collega.** Il collega fa un mix diverso dal tuo, o l'ha scelto male a sua volta. Il codice si sceglie sulla propria attività.

**Scegliere per il coefficiente.** Vedi sopra: l'ottimizzazione che non corrisponde alla realtà non è un'ottimizzazione, è un rischio.

**Non aggiornarlo mai.** Le attività cambiano: chi ha aperto per i massaggi e oggi vive di corsi ha un'attività diversa da quella dichiarata. Il codice si può cambiare e aggiungere dopo l'apertura, con una variazione dati: farlo è ordinaria manutenzione, non un dramma.

**Confondere il codice con un'abilitazione.** L'ATECO classifica, non autorizza. Dichiarare un codice dell'area della medicina complementare non rende sanitaria un'attività che non lo è: i confini li mettono le leggi sulle professioni, non la classificazione statistica. Su questo la cornice giusta è la [legge 4 del 2013](/blog/legge-4-2013-professioni-olistiche).

## Da dove cominciare

Prima della conversazione con il commercialista, arriva con tre cose chiare: l'elenco onesto di quello che fai e di quanto pesa ciascuna attività sui tuoi incassi, l'idea di dove vuoi andare nei prossimi due anni, e le domande di questa guida. Mezz'ora ben preparata vale più di dieci articoli.

Il quadro completo su regimi, tasse e contributi è nella [guida alla partita IVA per operatori olistici](/blog/partita-iva-operatore-olistico-fiscalita-guida). E prima di ricevere il primo cliente, vale la pena sistemare anche [l'assicurazione](/blog/assicurazione-rc-operatore-olistico).

## Domande frequenti

**Qual è il codice ATECO per un operatore olistico?**
Non esiste un codice unico. Il più usato storicamente è il 96.09.09 (altre attività di servizi per la persona); la classificazione ATECO 2025 ha introdotto voci dedicate alla medicina complementare e alle tecniche di trattamento del corpo; chi insegna ragiona sui codici della formazione o del benessere. La scelta dipende dal mix di attività e va fatta con un commercialista.

**Serve un codice diverso per ogni disciplina?**
No. Serve un codice che descriva l'attività prevalente, più eventuali codici secondari se fai attività davvero diverse fra loro, per esempio trattamenti individuali e corsi regolari.

**Il codice ATECO decide quante tasse pago?**
In regime forfettario sì, in parte: dal gruppo ATECO dipende il coefficiente di redditività, cioè la quota dei ricavi su cui si calcolano imposte e contributi. Per questo un codice sbagliato può costare caro in entrambe le direzioni.

**Posso cambiare codice dopo l'apertura?**
Sì, con una variazione dati all'Agenzia delle Entrate. Se l'attività è cambiata rispetto a quando hai aperto, aggiornare il codice è la cosa corretta da fare.""",
    },

    # ── 2. Assicurazione RC ──────────────────────────────────────────
    {
        "slug": "assicurazione-rc-operatore-olistico",
        "title": "Assicurazione per operatori olistici: cosa serve davvero",
        "description": ("La responsabilità civile per chi lavora nel "
                        "benessere: cosa copre, cosa resta fuori, il "
                        "ruolo delle associazioni e le domande da fare "
                        "prima di firmare."),
        "category": "operatori",
        "related": ["partita-iva-operatore-olistico-fiscalita-guida",
                    "codice-ateco-operatore-olistico",
                    "legge-4-2013-professioni-olistiche"],
        "content": """Il messaggio arriva di sera: una cliente è scivolata uscendo dalla sala, niente di grave, ma il polso fa male e domani va al pronto soccorso. Tu riavvolgi la giornata: il tappeto vicino alla porta, la luce bassa, il pavimento appena lavato. E ti accorgi che non sai rispondere alla domanda più semplice: se chiede i danni, chi paga?

Per le professioni del benessere l'assicurazione non è, in generale, un obbligo di legge. È una delle cose che la [legge 4 del 2013](/blog/legge-4-2013-professioni-olistiche) lascia alla responsabilità del professionista. Ma la differenza fra averla e non averla si misura esattamente in serate come quella del messaggio.

## Le due coperture da distinguere

**La responsabilità civile professionale** copre i danni che puoi causare a terzi nell'esercizio dell'attività: la cliente che si fa male durante un trattamento, la reazione a un olio usato in seduta, l'infortunio durante una lezione che conduci. È la copertura che porta il tuo nome e ti segue dove lavori.

**La responsabilità civile della struttura** copre i danni legati al luogo: il pavimento scivoloso, lo scaffale che cade. Se ricevi in uno studio tuo, serve anche questa; se lavori in una struttura altrui, di solito è la struttura ad averla, ma conviene chiederlo per iscritto invece di presumerlo. La scivolata del nostro esempio sta proprio sul confine fra le due: è il motivo per cui vanno pensate insieme.

## Cosa copre, in concreto

Una RC professionale ben fatta risponde quando un terzo subisce un danno e te ne chiede conto: paga il risarcimento entro il massimale e, nelle polizze migliori, anche le spese legali per difenderti, comprese le richieste infondate. Il massimale è la cifra oltre la quale la copertura si ferma: è il primo numero da guardare, prima del prezzo.

Le polizze non sono tutte uguali, e per le discipline olistiche la differenza la fanno le attività dichiarate: una copertura pensata per il counseling non copre automaticamente i trattamenti con contatto fisico, e una polizza da studio non copre da sola il ritiro residenziale con trenta persone. La regola è dichiarare per iscritto tutte le attività che fai davvero, comprese quelle occasionali.

## Cosa non copre mai

Vale la pena dirlo senza giri: nessuna polizza copre l'esercizio abusivo di professioni sanitarie. Se un'attività è riservata a medici, fisioterapisti o psicologi, farla senza titolo non è un rischio assicurabile: è un illecito, e l'assicurazione non risponde. Lo stesso vale per i danni causati con dolo e, spesso, per le promesse terapeutiche: dire a una persona di sospendere una cura è fuori da ogni copertura, oltre che fuori da ogni serietà.

È il motivo per cui l'assicurazione non sostituisce i confini chiari della professione: li presuppone. Chi lavora dentro quei confini si assicura bene e a condizioni ragionevoli; chi li supera non è coperto da niente.

## Il canale delle associazioni

Molte associazioni professionali della legge 4/2013 offrono convenzioni assicurative riservate agli iscritti: polizze collettive pensate per le discipline che rappresentano, spesso a condizioni migliori di quelle che un singolo otterrebbe da solo. È uno dei benefici concreti dell'iscrizione, insieme all'attestato di qualità.

Il costo di una RC per operatori del benessere dipende da troppe variabili per dare cifre oneste in un articolo: massimale, discipline coperte, contatto fisico o no, canale associativo o polizza individuale. Il metodo giusto è chiedere due o tre preventivi con la stessa descrizione scritta della tua attività, e confrontare massimali ed esclusioni prima dei prezzi.

## Le domande da fare prima di firmare

Quali attività sono coperte, esattamente, e quali escluse. Qual è il massimale per sinistro e per anno. C'è la tutela legale, e fino a che importo. Sono coperti gli eventi fuori sede, i ritiri, le attività online. C'è una franchigia, e quanto pesa. Cosa succede se un sinistro viene denunciato dopo la fine della polizza, per un fatto avvenuto durante.

Sono sei domande. Un assicuratore serio risponde per iscritto a tutte; se qualcuna mette a disagio chi vende, hai imparato qualcosa di importante prima di pagare.

## Da leggere insieme

Il quadro fiscale e contributivo è nella [guida alla partita IVA](/blog/partita-iva-operatore-olistico-fiscalita-guida), e la scelta del [codice ATECO](/blog/codice-ateco-operatore-olistico) incide anche su come gli assicuratori inquadrano la tua attività.

## Domande frequenti

**L'assicurazione è obbligatoria per un operatore olistico?**
In generale no: per le professioni non organizzate della legge 4/2013 non esiste un obbligo assicurativo generalizzato. Ma molte associazioni professionali la richiedono ai propri iscritti, molte strutture la pretendono per contratto da chi collabora, e lavorare a contatto con le persone senza copertura è un rischio che ricade tutto su di te.

**Cosa copre la responsabilità civile professionale?**
I danni causati a terzi nell'esercizio dell'attività dichiarata in polizza, entro il massimale: infortuni durante trattamenti o lezioni, danni collegati alla tua prestazione, e nelle polizze migliori le spese legali di difesa.

**La polizza copre anche ritiri ed eventi?**
Solo se sono dichiarati. Le attività fuori sede, residenziali o con gruppi numerosi vanno indicate espressamente: una polizza da studio non le copre in automatico.

**Cosa non copre mai una polizza?**
L'esercizio di attività sanitarie riservate ad altre professioni, i danni causati intenzionalmente e, in genere, le conseguenze di promesse terapeutiche. L'assicurazione protegge chi lavora dentro i confini della propria professione, non chi li supera.""",
    },

    # ── 3. Legge 4/2013 ──────────────────────────────────────────────
    {
        "slug": "legge-4-2013-professioni-olistiche",
        "title": "Legge 4/2013: cosa dice per le professioni olistiche",
        "description": ("La legge sulle professioni non organizzate "
                        "spiegata: cosa permette, cosa impone, il ruolo "
                        "delle associazioni e l'attestato di qualità."),
        "category": "operatori",
        "related": ["come-capire-se-un-operatore-olistico-e-serio",
                    "partita-iva-operatore-olistico-fiscalita-guida",
                    "codice-ateco-operatore-olistico"],
        "content": """In fondo a una fattura, in piccolo, c'è una riga che quasi nessuno legge: «professione disciplinata ai sensi della legge n. 4 del 14 gennaio 2013». Sembra burocrazia. È invece la risposta dello Stato italiano a una domanda che riguarda tutto il mondo olistico: che cosa sono, giuridicamente, le professioni che non hanno un albo?

Questa guida spiega la legge com'è, senza gonfiarla e senza sminuirla. Perché intorno alla 4/2013 circolano due racconti sbagliati e opposti: chi la presenta come un riconoscimento che «abilita» le discipline olistiche, e chi la ignora del tutto. La verità è più utile di entrambi.

## Cosa regola

L'Italia divide le professioni in due mondi. Da una parte quelle organizzate in ordini e collegi: medici, avvocati, psicologi, fisioterapisti, con albi, esami di Stato ed esclusive di legge. Dall'altra tutte le altre: [il testo della legge](""" + NORMATTIVA + """) le chiama «professioni non organizzate», e comprendono counselor, naturopati, operatori del benessere, insegnanti di discipline orientali e moltissime figure oltre il mondo olistico.

Il principio della legge è liberale: queste professioni si possono esercitare liberamente, senza autorizzazioni preventive. In cambio, chiede una cosa sola ma la chiede sul serio: trasparenza verso il cliente.

## Cosa impone

**Il riferimento in ogni documento.** Chi esercita una professione non organizzata deve citare la legge in ogni documento e rapporto scritto con il cliente: preventivi, fatture, contratti, siti. È la riga in piccolo dell'apertura. Ometterla non è un dettaglio: la legge la tratta come pratica commerciale scorretta, con le sanzioni del Codice del consumo.

**Chiarezza su cosa si offre.** Il professionista risponde della correttezza delle informazioni che dà sul proprio servizio. Per il mondo olistico questo ha un significato preciso: presentare una disciplina di benessere come una cura è esattamente il tipo di scorrettezza che la cornice sanziona.

## Le associazioni professionali

La legge permette ai professionisti di riunirsi in associazioni di natura privata, che possono darsi standard di formazione, codici deontologici, obblighi di aggiornamento. Le associazioni con determinati requisiti possono essere inserite in un elenco tenuto dal ministero competente, consultabile online da chiunque.

Le associazioni possono inoltre rilasciare ai propri iscritti un **attestato di qualità e qualificazione professionale dei servizi**: un documento che dichiara che l'iscritto rispetta gli standard dell'associazione. Alcune discipline hanno anche norme tecniche UNI che descrivono conoscenze e competenze della figura professionale, e la certificazione a fronte di quelle norme è un gradino ulteriore.

Va detto con la stessa onestà: l'iscrizione è volontaria, l'attestato non è un'abilitazione di Stato, e un'associazione non vale l'altra. Sono strumenti di trasparenza, non timbri di infallibilità. Il loro valore sta in quello che permettono di verificare: chi forma, con che criteri, con quale deontologia.

## Cosa la legge non fa

Non crea albi né esclusive: chiunque può esercitare una professione non organizzata, iscritto o no a un'associazione. Non «riconosce» le discipline nel senso in cui spesso si legge: non certifica che funzionino, si limita a regolare chi le esercita. E soprattutto non sposta di un millimetro i confini con le professioni sanitarie: diagnosi, prescrizione e cura restano riservate a chi ha i titoli, e nessuna iscrizione associativa autorizza a superarli.

## Cosa significa in pratica

**Se lavori nel benessere:** metti la dicitura ovunque, valuta un'associazione seria del tuo settore per formazione continua, deontologia e [convenzioni assicurative](/blog/assicurazione-rc-operatore-olistico), e tieni i confini sanitari con una cura maniacale, perché la cornice che ti permette di lavorare è la stessa che sanziona chi la tradisce. Il quadro fiscale sta nella [guida alla partita IVA](/blog/partita-iva-operatore-olistico-fiscalita-guida).

**Se stai scegliendo un professionista:** la dicitura in fattura, l'associazione dichiarata e verificabile, la chiarezza sui limiti della disciplina sono segnali concreti, e la loro assenza è un'informazione anche quella. Il metodo completo per valutarli è nella guida su [come capire se un operatore è serio](/blog/come-capire-se-un-operatore-olistico-e-serio).

## Domande frequenti

**La legge 4/2013 riconosce le professioni olistiche?**
Le regola, che è diverso: stabilisce che possono essere esercitate liberamente e impone trasparenza verso il cliente. Non è un'abilitazione di Stato e non certifica l'efficacia di nessuna disciplina.

**Un operatore olistico deve citare la legge 4/2013?**
Sì: il riferimento va inserito in ogni documento e rapporto scritto con il cliente. L'omissione è considerata pratica commerciale scorretta ed è sanzionabile.

**Cos'è l'attestato di qualità dei servizi?**
Un documento che le associazioni professionali possono rilasciare ai propri iscritti, attestando il rispetto degli standard dell'associazione. È uno strumento di trasparenza volontario, non un'abilitazione.

**L'iscrizione a un'associazione è obbligatoria?**
No, è volontaria. Ma un'associazione seria offre formazione continua, deontologia e verificabilità: per chi lavora è un investimento sensato, per chi sceglie è un segnale da controllare, non da prendere sulla parola.""",
    },
]

# backlink dagli articoli esistenti (hub → spoke)
AGGIUNTE = [
    ("partita-iva-operatore-olistico-fiscalita-guida",
     "All'apertura serve indicare il codice attività, e questa è la prima "
     "decisione da prendere con qualcuno, non da soli.",
     "All'apertura serve indicare il codice attività, e questa è la prima "
     "decisione da prendere con qualcuno, non da soli. Il panorama dei "
     "codici, le famiglie fra cui si sceglie e gli errori più comuni sono "
     "nella [guida al codice ATECO per operatori olistici]"
     "(/blog/codice-ateco-operatore-olistico)."),
    ("come-capire-se-un-operatore-olistico-e-serio",
     "4 del 14 gennaio 2013», stai leggendo una persona che sa in quale "
     "cornice lavora: è un segnale piccolo ma reale.",
     "4 del 14 gennaio 2013», stai leggendo una persona che sa in quale "
     "cornice lavora: è un segnale piccolo ma reale. Cosa dice davvero "
     "quella legge, e cosa no, è spiegato nella [guida alla legge 4/2013]"
     "(/blog/legge-4-2013-professioni-olistiche)."),
]


async def main(dry_run: bool) -> None:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from database import db

    for art in ARTICOLI:
        assert len(art["title"]) <= 60, art["slug"]
        assert 0 < len(art["description"]) <= 158, art["slug"]
        print(f"{art['title']}\n  slug: {art['slug']}  "
              f"parole: {len(art['content'].split())}  "
              f"T:{len(art['title'])} D:{len(art['description'])}")

    if dry_run:
        print("\n--dry-run: nessuna scrittura")
        return

    now = datetime.now(timezone.utc)
    for art in ARTICOLI:
        esistente = await db.articles.find_one({"slug": art["slug"]},
                                               {"_id": 0, "id": 1})
        campi = {"title": art["title"], "description": art["description"],
                 "content": art["content"], "category": art["category"],
                 "author_name": "Aurya", "published": True,
                 "updated_at": now, "translations": {},
                 "related_slugs": art["related"]}
        if not esistente:
            campi |= {"id": str(uuid.uuid4()), "slug": art["slug"],
                      "created_at": now, "published_at": now}
        await db.articles.update_one({"slug": art["slug"]},
                                     {"$set": campi}, upsert=True)
        doc = await db.articles.find_one({"slug": art["slug"]},
                                         {"_id": 0, "featured_image_url": 1})
        if not doc.get("featured_image_url"):
            from routers.articles import _autogen_cover
            url = await _autogen_cover(art["slug"], art["category"])
            if url:
                await db.articles.update_one(
                    {"slug": art["slug"]},
                    {"$set": {"featured_image_url": url}})
                print(f"  copertina: {url}")

    for slug, vecchio, nuovo in AGGIUNTE:
        d = await db.articles.find_one({"slug": slug}, {"_id": 0, "content": 1})
        if not d:
            print(f"  ASSENTE {slug}")
        elif "/blog/codice-ateco" in d["content"] and "codice-ateco" in nuovo:
            print(f"  link gia' presente in {slug[:44]}")
        elif "/blog/legge-4-2013" in d["content"] and "legge-4-2013" in nuovo:
            print(f"  link gia' presente in {slug[:44]}")
        elif vecchio in d["content"]:
            await db.articles.update_one({"slug": slug}, {"$set": {
                "content": d["content"].replace(vecchio, nuovo, 1)}})
            print(f"  backlink aggiunto in {slug[:44]}")
        else:
            print(f"  NON TROVATO in {slug[:44]}")

    # ── audit: link interni integri, FAQ estraibili, niente orfani ───
    import re
    arts = await db.articles.find({"published": True},
                                  {"_id": 0, "slug": 1, "content": 1}).to_list(100)
    slugs = {a["slug"] for a in arts}
    rotti = [(a["slug"], l) for a in arts
             for l in re.findall(r"\]\(/blog/([a-z0-9-]+)\)", a["content"])
             if l not in slugs]
    print(f"\nlink rotti: {rotti or 'nessuno'}")
    from routers.seo_shell import _extract_faq
    for art in ARTICOLI:
        n = len(_extract_faq(art["content"]))
        print(f"  FAQ estratte da {art['slug'][:40]}: {n}")
        assert n >= 3, "FAQ non estraibili: controlla il formato"
    inbound = {a["slug"]: 0 for a in arts}
    for a in arts:
        for l in re.findall(r"\]\(/blog/([a-z0-9-]+)\)", a["content"]):
            if l in inbound and l != a["slug"]:
                inbound[l] += 1
    orfani = [s for s, n in inbound.items() if n == 0]
    print(f"orfani: {orfani or 'nessuno'}")
    print(f"articoli totali: {len(arts)}")


if __name__ == "__main__":
    asyncio.run(main("--dry-run" in sys.argv))
