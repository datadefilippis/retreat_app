"""BN3 — pubblica la prima guida riservata: "Il kit delle pratiche
quotidiane". Idempotente (upsert per slug).

BOZZA da approvazione founder (BN0): il testo qui sotto e' scritto
allo standard delle guide (esaustivo, onesto, fonti citate,
controindicazioni) ma la parola finale sui contenuti e' del founder.
In locale serve a verificare il gate end-to-end; in prod si esegue
SOLO dopo l'approvazione del testo.

Uso: python scripts/bn3_publish_kit_pratiche.py
"""

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

SLUG = "kit-pratiche-quotidiane-15-minuti"

TITLE = "Il kit delle pratiche quotidiane: 15 minuti al giorno, spiegati bene"

DESCRIPTION = ("Sette pratiche olistiche essenziali in un unico kit: "
               "protocolli passo passo, cosa dice la ricerca, errori "
               "comuni e come costruire la tua routine di 15 minuti.")

CONTENT = """C'e' un equivoco che blocca quasi tutti: credere che per stare meglio servano un'ora al giorno, un maestro e una disciplina di ferro. La verita' che vediamo ogni giorno negli operatori della nostra rete e' un'altra: contano i minuti fatti, non i minuti promessi. Quindici minuti al giorno, distribuiti bene, battono qualsiasi buon proposito da un'ora.

Questo kit raccoglie sette pratiche essenziali in versione minima ma completa: per ognuna trovi il protocollo passo passo, quanto tempo serve davvero, cosa dice la ricerca (onestamente, senza gonfiare) e gli errori che fanno mollare. In fondo, tre routine pronte da 15 minuti per combinare le pratiche senza pensarci.

## Come usare questo kit

Non fare tutto. Scegli UNA pratica dalla sezione che ti chiama di piu' e falla per due settimane, agganciata a un'abitudine che hai gia' (dopo il caffe', prima della doccia). Solo quando e' diventata automatica, aggiungi la seconda. La routine completa da 15 minuti e' un punto di arrivo, non di partenza.

Una nota di onesta' che vale per tutto il kit: queste pratiche sostengono il benessere, non sostituiscono un percorso medico o psicologico. Se stai attraversando un momento clinicamente difficile, usale COME AFFIANCAMENTO a un professionista, non al suo posto.

## 1. Il respiro fisiologico (2 minuti)

Il modo piu' rapido documentato per abbassare l'attivazione del sistema nervoso e' un pattern respiratorio preciso: doppia inspirazione dal naso, espirazione lunga dalla bocca.

Protocollo:
1. Inspira dal naso normalmente, e quando pensi di aver finito aggiungi un secondo piccolo sorso d'aria (riapre gli alveoli collassati).
2. Espira dalla bocca, lentamente, piu' a lungo dell'inspirazione.
3. Ripeti da 1 a 3 volte. Per un effetto piu' profondo: 2 minuti.

Cosa dice la ricerca: uno studio randomizzato di Stanford (Balban et al., 2023, Cell Reports Medicine) ha confrontato tre tecniche di respiro con la mindfulness: il "cyclic sighing" (questo pattern) e' risultato il piu' efficace nel migliorare l'umore e abbassare la frequenza respiratoria a riposo, con soli 5 minuti al giorno.

Errore comune: forzare inspirazioni enormi. Il secondo sorso e' piccolo; il lavoro vero lo fa l'espirazione lunga.

## 2. Meditazione dell'attenzione (5 minuti)

La base di tutto: ti siedi, segui il respiro, la mente scappa, te ne accorgi, torni. Quel ritorno e' l'esercizio, non il fallimento.

Protocollo:
1. Siediti comodo, schiena dritta ma non rigida. Timer a 5 minuti.
2. Porta l'attenzione al respiro, dove lo senti di piu' (narici, petto, pancia).
3. Quando ti accorgi che stai pensando ad altro (succedera' subito), nota "pensiero" e torna al respiro. Senza giudizio: il giudizio e' solo un altro pensiero.
4. Al timer, prima di alzarti, nota com'e' il corpo rispetto a 5 minuti fa.

Cosa dice la ricerca: la meditazione e' tra le pratiche piu' studiate; le meta-analisi (Goyal et al., 2014, JAMA Internal Medicine) mostrano effetti moderati ma consistenti su ansia, depressione e dolore. Moderati: non miracolosi. E costruiti sulla costanza, non sulle sessioni lunghe.

Errore comune: giudicare le sessioni ("oggi e' andata male"). Una sessione in cui torni cinquanta volte e' riuscita cinquanta volte.

## 3. Lo scan del corpo (3 minuti)

Il ponte tra mente e corpo: passare l'attenzione, zona per zona, senza dover cambiare nulla.

Protocollo:
1. Da seduto o sdraiato, occhi chiusi. Parti dai piedi.
2. Sali lentamente: piedi, gambe, bacino, schiena, pancia, petto, spalle, braccia, mani, collo, viso, testa. Qualche respiro per zona.
3. Dove trovi tensione, non "rilassarla" a forza: osservala un respiro in piu' e passa oltre. Spesso si scioglie da sola, e se non lo fa va bene lo stesso.

Quando usarlo: e' la pratica migliore prima di dormire (sdraiato, partendo dalla testa verso i piedi) e nei momenti in cui ti accorgi di essere "solo testa".

## 4. I cinque sensi (1 minuto, ovunque)

La pratica di emergenza: riporta nel presente in sessanta secondi, in fila alla posta come in una giornata storta.

Protocollo (5-4-3-2-1):
1. Nota 5 cose che VEDI, una alla volta.
2. Poi 4 cose che SENTI col tatto (i piedi a terra, il tessuto sulla pelle).
3. Poi 3 suoni.
4. Poi 2 odori.
5. Poi 1 sapore.

Perche' funziona: l'attenzione sensoriale interrompe la ruminazione (il rimuginio ripetitivo) occupandone il canale. E' una tecnica di grounding usata anche in ambito clinico per gli stati d'ansia acuta.

## 5. La camminata consapevole (10 minuti, sostituibile a tutto)

Se sedersi a meditare proprio non fa per te, questa e' la porta d'ingresso: la stessa attenzione, in movimento.

Protocollo:
1. Cammina a passo naturale, senza telefono e senza cuffie.
2. Per i primi 2 minuti, attenzione solo ai piedi: l'appoggio, la spinta, il peso che passa da un lato all'altro.
3. Poi allarga: l'aria sulla pelle, i suoni, quello che vedi. Quando la mente parte coi pensieri, torna ai piedi.

Cosa dice la ricerca: l'attivita' fisica leggera regolare e' uno dei fattori piu' solidi per l'umore e il sonno; camminare nella natura amplifica l'effetto sulla riduzione della ruminazione (Bratman et al., 2015, PNAS). Dieci minuti contano davvero.

## 6. Il diario di scarico (3 minuti, sera)

Scrivere non e' "tenere un diario": e' svuotare la testa perche' la notte non debba farlo lei.

Protocollo:
1. Prima di dormire, un foglio o un quaderno (non il telefono).
2. Tre minuti, due sole domande: "Cosa mi porto di oggi?" e "Cosa lascio qui?". Scrivi senza rileggere e senza curare la forma.
3. Chiudi il quaderno: il gesto conta quanto le parole.

Variante con la ricerca alle spalle: la "gratitudine specifica": tre cose precise per cui sei grato oggi (non "la famiglia", ma "la telefonata con mia sorella"). Gli studi di Emmons e McCullough mostrano effetti misurabili su benessere percepito e sonno con la pratica regolare.

## 7. Il digiuno digitale del mattino (0 minuti, cambia tutto)

L'unica pratica di questo kit che consiste nel NON fare qualcosa: niente telefono per i primi 30 minuti dopo il risveglio.

Come riuscirci davvero:
1. La sveglia NON e' il telefono (una sveglia da 10 euro cambia la mattina).
2. Il telefono si carica fuori dalla camera, o almeno fuori portata dal letto.
3. Nei 30 minuti ci stanno il respiro (pratica 1), il caffe' fatto con calma, la doccia. Non serve riempirli: serve non riempirli di feed.

Perche' e' nel kit: iniziare la giornata nel proprio filo, invece che in quello degli altri, e' il moltiplicatore silenzioso di tutte le altre pratiche.

## Le tre routine pronte

**Routine del mattino (15 minuti):** digiuno digitale + respiro fisiologico (2') + meditazione (5') + camminata anche breve o scan in piedi (8').

**Routine anti-stress per la giornata lavorativa:** respiro fisiologico prima delle riunioni difficili (1') + cinque sensi nelle transizioni (1') + camminata consapevole in pausa pranzo (10').

**Routine della sera (10 minuti):** camminata dopo cena (5') + diario di scarico (3') + scan del corpo a letto (2', spesso non arrivi in fondo: e' il punto).

## Quando la pratica quotidiana non basta

C'e' un limite onesto in tutto questo: 15 minuti al giorno mantengono e costruiscono, ma certe soglie si attraversano solo con l'immersione. Un fine settimana di pratica guidata, senza telefono, con un gruppo e una guida esperta, porta in profondita' in tre giorni quello che a casa richiede mesi. E' esattamente il lavoro degli operatori che intervistiamo nella rete Aurya: quando apriremo le prenotazioni, chi e' iscritto alla lettera sara' il primo a saperlo.

## Domande frequenti

**Quanto tempo prima di vedere risultati?** Le prime sensazioni (piu' calma dopo la sessione) arrivano subito; i cambiamenti stabili (sonno, reattivita' allo stress) chiedono 4-8 settimane di costanza. Diffida di chi promette di meno.

**Meglio la mattina o la sera?** Meglio quando la fai davvero. La mattina ha un vantaggio pratico: nessuna giornata storta puo' cancellarla.

**Ho saltato tre giorni: ricomincio da capo?** No. Riprendi da oggi, con la versione piu' corta della pratica (anche 2 minuti). La continuita' si misura sui mesi, non sui giorni.

**Le app di meditazione vanno bene?** Per iniziare si': la voce guidata e' una stampella utile. Dopo qualche settimana prova il silenzio con un timer semplice: e' un'altra pratica, piu' tua.
"""


async def main() -> None:
    from database import db
    from models.common import utc_now

    now = datetime.now(timezone.utc)
    existing = await db.articles.find_one({"slug": SLUG}, {"_id": 0, "id": 1})
    doc_set = {
        "title": TITLE,
        "description": DESCRIPTION,
        "content": CONTENT,
        "category": "meditazione",
        "access": "subscriber",          # BN3: guida riservata
        "published": True,
        "updated_at": utc_now(),
    }
    if existing:
        await db.articles.update_one({"slug": SLUG}, {"$set": doc_set})
        print(f"aggiornata: {SLUG}")
    # cover nel formato standard del Magazine (AN6): la guida non passa
    # dal flusso publish dell'admin, quindi la genera lo script
    doc = await db.articles.find_one({"slug": SLUG}, {"_id": 0,
                                                      "featured_image_url": 1})
    if not (doc or {}).get("featured_image_url"):
        from routers.articles import _autogen_cover
        cover = await _autogen_cover(SLUG, "meditazione")
        if cover:
            await db.articles.update_one(
                {"slug": SLUG}, {"$set": {"featured_image_url": cover}})
            print(f"cover generata: {cover}")
    else:
        import uuid
        await db.articles.insert_one({
            "id": str(uuid.uuid4()), "slug": SLUG, **doc_set,
            "translations": {}, "author_name": "Aurya",
            "published_at": now, "created_at": now,
        })
        print(f"creata: {SLUG}")
    words = len(CONTENT.split())
    print(f"parole: {words}, access: subscriber, category: meditazione")


if __name__ == "__main__":
    asyncio.run(main())
