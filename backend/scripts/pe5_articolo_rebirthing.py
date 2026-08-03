"""PE5 — secondo articolo del pilastro "Le discipline": il rebirthing.

PERCHE'. In italiano il rebirthing e' raccontato male o da chi lo
vende. Una guida che spiega cos'e', come si svolge una sessione e
soprattutto QUANDO E' SCONSIGLIATO e' utile proprio perche' noi non
stiamo vendendo la pratica.

VINCOLO DEL FOUNDER (2 ago 2026), scritto qui perche' non si perda.
Il founder e' in formazione e NON puo' proporsi come rebirther:
l'articolo si scrive come informazione, non porta firma personale e
non deve in nessun punto far intendere che Aurya offra la pratica.
E' il Manifesto applicato a noi stessi, e sarebbe la prima crepa se
lo violassimo.

COME SONO TRATTATE LE AFFERMAZIONI DELLA DISCIPLINA. La teoria del
trauma della nascita e' riportata come quello che e' — la cornice
teorica di chi ha fondato la pratica — e non come un fatto. Le
sensazioni fisiche invece hanno una spiegazione fisiologica nota
(alcalosi respiratoria) e viene data. Dove la ricerca non c'e', si
dice che non c'e'.

Categoria: breathwork. Il rebirthing e' una delle pratiche di quella
famiglia, e mettercelo rinforza il cluster invece di aprirne un altro
con un pezzo solo dentro.

    venv/bin/python scripts/pe5_articolo_rebirthing.py [--dry-run]
"""
import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone

SLUG = "rebirthing-cose-come-funziona-una-sessione"
TITOLO = "Rebirthing: cos'è, come funziona una sessione e quando è sconsigliato"
DESCRIZIONE = (
    "Respirazione circolare consapevole: come si svolge una sessione di "
    "rebirthing, cosa si sente nel corpo, cosa dice la ricerca e le "
    "controindicazioni."
)
CATEGORIA = "breathwork"

CONTENUTO = """\
Il nome è la prima cosa che confonde. «Rebirthing» promette una rinascita, e chi lo sente per la prima volta immagina qualcosa fra la seduta di psicoterapia e il rito iniziatico. Quello che succede in una sessione è più semplice da descrivere: una persona sdraiata respira in un modo particolare per circa un'ora, con qualcuno accanto.

Da lì in poi le cose si complicano, ed è la parte che vale la pena capire prima di prenotare.

## Cos'è, in una riga

Il rebirthing è una pratica di **respirazione circolare consapevole**: si respira senza pause fra inspirazione ed espirazione, in modo continuo, per un periodo prolungato. Nella famiglia del breathwork è una delle tecniche a respirazione intensa, quelle che modificano attivamente la chimica del sangue invece di calmarla.

La differenza con le tecniche di rilassamento è netta, e conviene tenerla a mente: una respirazione lenta e allungata abbassa l'attivazione, questa la alza prima di lasciarla cadere.

## Da dove viene

La pratica nasce negli Stati Uniti negli anni Settanta dal lavoro di **Leonard Orr**. Le prime sessioni si svolgevano in vasche d'acqua calda, con la persona immersa e un boccaglio: da lì il nome, e l'idea che quello stato somigliasse alla condizione prenatale.

L'acqua è quasi sparita: oggi le sessioni si fanno quasi sempre a secco, sdraiati su un tappetino. Chi la propone ancora in acqua lo dichiara, e richiede più esperienza da entrambe le parti.

## Come si svolge una sessione

Le sessioni durano fra i sessanta e i novanta minuti e seguono quasi ovunque la stessa struttura.

**Il colloquio.** Si parla di come stai, di cosa ti porta lì, della tua storia medica. Un facilitatore preparato chiede di patologie cardiache, pressione, epilessia, gravidanza, farmaci e percorsi psicologici in corso. Se questa parte manca, è già un'informazione sulla persona che hai davanti.

**L'avvio.** Sdraiato, si comincia a respirare collegando inspirazione ed espirazione senza fermarsi nel mezzo. L'inspirazione è attiva, l'espirazione lasciata andare. Il facilitatore accompagna con la voce e a volte con un contatto leggero.

**La fase centrale.** È qui che il corpo reagisce, e ci arriviamo fra due paragrafi.

**L'integrazione.** Il respiro torna spontaneo, si resta sdraiati in silenzio, spesso coperti. Molti descrivono questo momento come la parte più importante.

**La chiusura.** Si parla di quello che è successo. Un buon facilitatore ascolta senza interpretare al posto tuo.

## Cosa si sente, e perché

Durante la fase centrale le sensazioni riferite più spesso sono formicolio a mani, piedi e labbra, irrigidimento delle dita, sensazione di freddo o di caldo, a volte contrazioni involontarie, e uno stato di coscienza alterato che va dal sogno a occhi aperti a un'emotività improvvisa: pianto, riso, ricordi.

Queste sensazioni hanno una spiegazione fisiologica documentata e vale la pena conoscerla, perché toglie spavento senza togliere valore all'esperienza. Respirando più del necessario si elimina più anidride carbonica di quanta se ne produca: il sangue diventa temporaneamente più alcalino, e questo cambia l'eccitabilità dei nervi e il calibro dei vasi cerebrali. **Formicolio e irrigidimento sono l'effetto meccanico di questo, non un segno che qualcosa si sta sbloccando.** Si risolvono da soli rallentando il respiro, ed è la prima cosa che un facilitatore preparato ti dice di poter fare in qualsiasi momento.

Che questa condizione fisiologica apra anche una porta emotiva è quello che riportano molte persone. Sul perché, le spiegazioni disponibili sono ipotesi.

## La teoria della nascita: cos'è e come leggerla

La cornice teorica originale sostiene che il modo in cui siamo nati lascia un'impronta, e che la respirazione circolare permetterebbe di raggiungerla e scioglierla. È da qui che vengono il nome e molto del linguaggio che troverai.

Questa è la teoria di chi ha fondato la pratica, e va presa per quello che è: **una cornice interpretativa, non un fatto stabilito**. Non esistono prove che una sessione di respiro riporti alla memoria eventi della nascita, e la ricerca sulla memoria dei primi mesi di vita va nella direzione opposta.

Distinguere le due cose serve a chi legge, non a sminuire la pratica: si può trovare valore in un'esperienza senza doverne accettare la spiegazione. Un facilitatore che presenta la teoria come una certezza scientifica sta dicendo qualcosa di sé.

## Cosa dice la ricerca

Poco, ed è giusto dirlo. Il rebirthing come metodo ha pochissimi studi clinici; quelli disponibili hanno campioni piccoli e nessun gruppo di controllo serio.

Esiste invece letteratura più solida su cose vicine: gli effetti della respirazione controllata sul sistema nervoso autonomo, e la fisiologia dell'iperventilazione, che è ben descritta. Sono corpi di conoscenza diversi, e sovrapporli sarebbe scorretto.

C'è poi un capitolo che va nominato perché riguarda la sicurezza. Negli anni Duemila, negli Stati Uniti, una pratica chiamata «rebirthing» e usata su una bambina in un contesto di terapia dell'attaccamento — dove la persona veniva avvolta e trattenuta a simulare il canale del parto — causò la morte della minore e portò a leggi che vietano quelle tecniche di contenimento in alcuni Stati. **Non è la stessa cosa della respirazione circolare** di cui parla questa guida, ma condivide il nome, e sapere che la confusione esiste aiuta a fare le domande giuste.

## Quando è sconsigliato

Questa è la sezione da leggere anche se salti il resto. La respirazione intensa è sconsigliata, o richiede il via libera di un medico, in presenza di:

- **gravidanza**
- **malattie cardiovascolari**, aritmie, pressione alta non controllata
- **epilessia** o storia di crisi convulsive
- **aneurismi**, distacco di retina, glaucoma
- **asma grave** o patologie respiratorie serie
- **disturbi psichiatrici** come psicosi, disturbo bipolare, dissociazione
- **interventi chirurgici recenti** o fratture in via di guarigione
- **osteoporosi grave**
- uso di farmaci che agiscono sul sistema nervoso centrale

L'elenco non sostituisce il parere di chi ti ha in cura. Se hai una condizione in corso, la domanda va fatta al tuo medico prima che al facilitatore.

E una cosa che vale sempre: **una pratica di respiro non è una psicoterapia**. Se stai attraversando un lutto, un trauma o un periodo di sofferenza importante, il rebirthing può accompagnare un percorso ma non prenderne il posto.

## Come scegliere chi conduce la sessione

In Italia il rebirthing non è una professione regolamentata: chiunque può proporsi. Non esiste un albo da consultare, quindi le domande le devi fare tu.

- **Con chi si è formato, e per quanto tempo.** Una formazione seria dura anni e prevede sessioni ricevute, non solo studiate.
- **Cosa chiede prima.** Se non c'è un colloquio sulla salute, manca la cosa più importante.
- **Cosa promette.** «Ti libererai del trauma» è una promessa che nessuno può fare. «Vediamo cosa emerge» è un'altra cosa.
- **Cosa dice sui limiti.** Chi conosce la pratica sa a chi non è adatta e lo dice per primo.
- **Come si comporta se chiedi di fermarti.** La risposta giusta è che si può smettere quando si vuole, sempre.

## Domande frequenti

**Quante sessioni servono?**
Chi la pratica lavora per cicli, spesso di dieci sessioni. Una sola dà un assaggio dell'esperienza, non un percorso.

**È pericoloso?**
Per una persona in buona salute e con un facilitatore preparato, le reazioni descritte sopra sono transitorie e si risolvono rallentando il respiro. Il rischio sta nelle condizioni dell'elenco delle controindicazioni, ed è il motivo per cui quel colloquio iniziale conta.

**Si può fare da soli, a casa?**
Le tecniche di respiro leggere sì. La respirazione circolare prolungata no: serve qualcuno che osservi e sappia intervenire, e non è una cautela formale.

**Che differenza c'è con la respirazione olotropica?**
Sono cugine: entrambe usano una respirazione intensa e prolungata. L'olotropica, sviluppata da Stanislav Grof, si pratica in gruppo, con musica per tutta la durata e in coppie che si alternano. Il rebirthing è quasi sempre individuale e silenzioso.

**Che differenza c'è con il breathwork in generale?**
Il breathwork è la famiglia, il rebirthing è una delle tecniche. Nella stessa famiglia ci sono anche pratiche che rallentano il respiro invece di intensificarlo, con effetti opposti.

**Devo raccontare la mia storia personale?**
Solo quello che vuoi. Un facilitatore ha bisogno di sapere cosa riguarda la tua sicurezza; il resto lo decidi tu.
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
        "title": TITOLO,
        "description": DESCRIZIONE,
        "content": CONTENUTO,
        "category": CATEGORIA,
        "author_name": "Aurya",     # PE1 + vincolo: nessuna firma personale
        "published": True,
        "updated_at": now,
        "translations": {},
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
