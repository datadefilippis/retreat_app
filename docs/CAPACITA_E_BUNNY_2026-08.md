# Quanto regge Aurya Sound, e il capitolo Bunny (21 agosto 2026, notte)

Domande del founder: quanto traffico regge il sito oggi (ascolti +
produzione operatori)? Servono altre ottimizzazioni? Ha senso il tetto
dei 30 minuti? Cosa sono gli avvisi agli operatori? E il sistema è
predisposto a passare a bunny.net per l'hosting — conviene, e la
migrazione romperebbe qualcosa?

Tutto misurato sullo stato DOPO il ciclo ES (nginx serve gli audio,
spezzone, vetrina indicizzata).

---

## 1. Quanto regge, oggi — la stima onesta

### Cosa costa un ascolto, dopo le ottimizzazioni

| voce | peso | chi lo serve |
|---|---|---|
| pagina (prima visita) | ~1–2 MB, poi cache | nginx statico |
| API (catalogo, traccia, sblocco) | pochi KB | il worker Python |
| sintesi delle frequenze | **zero** | il telefono dell'utente |
| basi-tappeto | **~4,5 MB l'una** (spezzone) | nginx sendfile |
| voce dell'operatore | ~1 MB/min usato | nginx sendfile |

**Un ascolto tipico: ~5–15 MB.** Prendiamo 10 come media prudente.

### I tre tetti, in ordine di arrivo

1. **Banda inclusa (20 TB/mese)** → **~2 milioni di ascolti/mese**
   (~65.000/giorno). È il primo muro, ed è lontanissimo.
2. **Scheda di rete (1 Gbit)** → ~12 ascolti *avviati al secondo* a
   pieno regime, cioè ~43.000/ora nei picchi. Con gli ascolti
   distribuiti nella giornata, non è un vincolo prima del punto 1.
3. **Il worker Python (unico)** → dopo ES1 fa solo API leggere: regge
   realisticamente 100+ richieste/secondo, e un ascolto ne fa ~5.
   Anche questo arriva dopo il punto 1.

La **produzione degli operatori** è irrilevante per il carico: salvare
una bozza scrive kilobyte, pubblicare scrive un documento, la voce è
sotto quota (100 MB/org) e passa dal worker solo all'upload — evento
raro. **Mille operatori attivi non spostano l'ago.**

### Verdetto

> Con l'infrastruttura attuale (~15 €/mese) Aurya Sound regge
> **~50–60.000 ascolti al giorno** senza toccare nulla. Siamo in fase
> rete con zero tracce pubblicate: il margine è di **quattro ordini di
> grandezza**. Il sistema oggi NON ha un problema di capacità; ha (già
> scritte in ES6) le soglie per riconoscere quando lo avrà.

### Cosa resta di fragile — perché la solidità non è solo capacità

| punto | stato | rischio reale |
|---|---|---|
| monitor esterno del sito | **manca** (nota dall'incidente cert del 12/8) | un down si scopre dagli utenti |
| `/uploads` pubblico senza auth | debito noto, ora con freno 30 req/min per IP | banda rubata: mitigato |
| rate-limit in memoria | si azzera al riavvio | accettato, documentato |
| backup uploads settimanale | ok fino a ~2 GB (soglia ES6) | perdita max 7 giorni di voce |

Il **monitor esterno** è l'unico vero buco di solidità rimasto: costa
zero (UptimeRobot/Hetzner) e non è codice — è una decisione tua.

---

## 2. Il tetto dei 30 minuti — sì, e c'è una ragione in più

Proposta del founder: via la traccia lunga, massimo 30 minuti in
libreria e in Crea.

**Correzione di fatto**: le basi oltre i 30 minuti sono **sei**, non
una — ma quattro sforano di *secondi* (30,1–30,3: sono tracce «da 30
minuti» con la coda). Quelle davvero lunghe sono due:

- «Too Brief A Time To Be Anything» — 45,0 min
- «Uccelli e pianoforte» — 37,3 min

**La ragione in più che rende il tetto coerente**, oltre alla RAM:
l'**ascolto a schermo bloccato funziona solo fino a 30 minuti**
(`CONTINUO_MAX_SEC`, il limite di memoria del telefono). Una sessione
da 45 minuti è quindi una sessione *senza* la funzione più preziosa su
mobile. Col tetto, ogni meditazione pubblicata è ascoltabile a schermo
bloccato: il sistema smette di avere una zona d'ombra.

Cosa comporterebbe (piano, non ancora eseguito):

1. **Crea**: campo durata max 30 (oggi 60), default resta 20;
2. **modello**: `DURATION_MAX` da 7200 → 1800 (oggi il server
   accetterebbe due ore!). Zero migrazioni: in prod le pubblicate sono
   0 e in locale nessuna supera i 20 min;
3. **libreria**: le 2 basi davvero lunghe si accorciano a ≤30 min con
   lo stesso attrezzo di ES2 (ricodifica → id... no: qui basta il
   taglio, stesso script esteso con `-t 1800`); le quattro «30 e
   spiccioli» si lasciano — lo spezzone le ha già rese innocue
   all'ascolto, e tagliare 15 secondi non compra niente.

*Nota di onestà: dopo lo spezzone, il tetto NON è più un'ottimizzazione
di peso (un tappeto da 45 min costa già 4,5 MB come uno da 10). È una
scelta di coerenza di prodotto — giusta — non di banda.*

---

## 3. Gli avvisi agli operatori, spiegati una volta per tutte

Oggi in Crea un operatore può incontrare **quattro** messaggi:

| avviso | quando compare | cosa gli sta dicendo |
|---|---|---|
| **«Anteprima senza dissolvenze — nella traccia pubblicata entra in Xs ed esce in Ys»** | sempre, se ha dissolvenze | il play in Crea parte a volume pieno per lavorare; chi ascolterà la traccia pubblicata avrà l'ingresso morbido che ha scelto |
| **🎧 avviso cuffie** | solo da telefono, solo mentre suona, solo se le frequenze stanno sotto i 500 Hz | «se non senti niente non è rotto: l'altoparlante del telefono non riproduce questi toni» |
| **stima di memoria** («questa sessione chiede ~N MB») | solo sopra i 350 MB stimati | può capitare **solo se spegne il loop** su una base lunga (brano intero): la sessione potrebbe non partire sui telefoni di chi ascolta |
| **quota voce** | al superamento (10 min/spezzone, 100 MB/org) | lo spazio registrazioni della sua organizzazione è pieno |

Dopo lo spezzone, la stima di memoria è diventata **rarissima** (i
tappeti pesano un decimo): non è rumore quotidiano, è una rete per il
caso limite. Se comunque i quattro messaggi ti sembrano tanti, l'unica
semplificazione onesta è di *copy*, non di sostanza: sono quattro fatti
diversi e nessuno è ridondante.

---

## 4. Bunny.net — la risposta in tre parti

### a) Chiarimento che cambia la domanda: le meditazioni NON si hostano

Una meditazione creata da un operatore è una **ricetta da ~581 byte**
in Mongo: non esiste un file da mettere su Bunny. Su un CDN
finirebbero solo: le **basi della libreria** (626 MB) e la **voce
registrata** (oggi 4 MB). «Tutte le tracce automaticamente su Bunny»
in pratica significa: *i file audio* su Bunny; le meditazioni restano
dove sono, gratis per definizione.

### b) Conviene? Oggi NO, e il conto è semplice

| | Hetzner (oggi) | Bunny |
|---|---|---|
| banda | **inclusa fino a 20 TB/mese** | ~0,005–0,01 €/GB → **~100–200 €/mese** a 20 TB |
| storage | incluso nel disco | ~0,01 €/GB/mese (spiccioli) |
| latenza extra-UE | mediocre (Falkenstein) | ottima (edge globale) |
| scala oltre i 20 TB | upgrade/traffico a pagamento Hetzner | lineare, senza toccare il server |

Finché la banda è inclusa, **Bunny costa di più per definizione** — si
pagherebbe ciò che oggi è gratis. Bunny **scala meglio** (nessun tetto,
edge nel mondo), ma quel «meglio» serve solo quando: superi ~5 TB/mese
reali, oppure arrivano ascoltatori fuori dall'Europa che sentono la
latenza. Sono esattamente le soglie già scritte in ES6.

### c) Il sistema è predisposto? Sì — e con mezz'ora di lavoro diventa un interruttore

I fatti architetturali che rendono la migrazione **banale**:

1. le sessioni salvano l'**`asset_id`**, mai l'URL: l'indirizzo del
   file si risolve al momento dell'ascolto, lato server;
2. l'URL si costruisce in **due soli punti** del backend
   (`routers/frequencies.py`, righe 545 e 651);
3. i nomi dei file sono **id immutabili** (content-addressed): su
   Bunny avrebbero lo stesso nome, e la cache `immutable` non può
   servire roba stantia perché un file nuovo ha sempre un URL nuovo;
4. il frontend non hardcoda mai l'host: prende `stream_url` dall'API.

**La predisposizione da fare ora** (mezz'ora): unificare i due punti in
un helper che legge una variabile (`ASSETS_PUBLIC_BASE`, default
vuoto = `/uploads` come oggi). Da quel momento la migrazione è:

- copiare i file su Bunny Storage (uno script rsync-like, i nomi non
  cambiano);
- per gli upload nuovi: il backend scrive in locale **e** fa PUT su
  Bunny (stesso helper) — l'«automatico» che chiedi;
- girare l'interruttore: `ASSETS_PUBLIC_BASE=https://aurya.b-cdn.net`;
- tenere `/uploads` com'è: è il fallback istantaneo se Bunny ha un
  problema (si svuota la variabile e tutto torna com'era).

**Cosa si rompe: niente.** Link pubblici, meditazioni salvate, bozze,
composizioni: tutto passa dall'`asset_id`. L'unico effetto visibile
sarebbe l'header della richiesta audio che cambia dominio.

---

## 5. Raccomandazioni, in ordine

| # | cosa | perché | costo |
|---|---|---|---|
| 1 | **monitor esterno** del sito | l'unico buco di solidità vero; già dovuto dall'incidente del 12/8 | 10 min, zero € |
| 2 | **tetto 30 min** (Crea max 30, modello 1800, taglio delle 2 basi lunghe) | coerenza: ogni traccia diventa ascoltabile a schermo bloccato | mezza giornata |
| 3 | **predisposizione Bunny** (helper + variabile) | trasforma una migrazione in un interruttore; zero effetto oggi | mezz'ora |
| 4 | Bunny vero e proprio | **NO oggi**: costa ciò che ora è gratis | quando scattano le soglie ES6 |

Il sistema, così com'è, regge la fase attuale con quattro ordini di
grandezza di margine. La cosa più preziosa da fare non è
un'ottimizzazione: è il monitor che ti avvisa se il sito cade.


---

## ESEGUITO + le risposte alle domande del founder (21/8, notte)

**Decisioni del founder recepite**: tolleranza di qualche minuto sopra
i 30 (niente tagli netti alle basi da «30 e spiccioli»); Bunny
**lasciato stare** (resta tutto in-house — non conviene finché la banda
è inclusa); predisposizione Bunny rimandata con lui.

### Fatto

1. **Tetto 30 minuti**: Crea accetta max 30 (default resta 20), il
   modello scende da 2 ore a 30 min (`DURATION_MAX 1800`). Zero
   migrazioni (nessuna traccia esistente lo supera).
2. **Le due basi davvero lunghe** (45 e 37 min) portate a 30:00 con
   `scripts/accorcia_basi_lunghe.py`: coda **sfumata in 12 s** (coseno
   rialzato, la stessa curva di tutte le dissolvenze di Aurya), mai
   taglio netto. Nome file nuovo (cache immutable salva), documento
   aggiornato prima della cancellazione. Le quattro da 30,1–30,3 **non
   toccate** (tolleranza). Guardia viva a 33 minuti.
3. **La finestra dei brani interi**: domanda esplicita del founder —
   *«se una traccia da 30 minuti è usata per 3, si scaricano 3
   minuti?»*. Prima NO (i brani non-loop scaricavano tutto); **ora
   sì**: si chiede al server solo la finestra usata dal mix (+10 s), e
   la coda la sfuma l'inviluppo del livello. Misurato: finestra da 3
   min di un brano da 30 → **4,2 MB scaricati** invece di 32.
4. **La nota delle dissolvenze riscritta** — il founder stesso non la
   capiva, prova che il copy era sbagliato: ora dice *«Qui l'anteprima
   parte subito a volume pieno, per lavorare. Chi ascolterà la traccia
   pubblicata la sentirà nascere dal silenzio in 10 secondi e spegnersi
   dolcemente negli ultimi 20.»* (coi numeri veri dell'operatore).

### Le risposte, nero su bianco

- **«Un mix con 10 tracce da 30 minuti scarica la somma?»** Sì: ogni
  base *distinta* si scarica una volta (la cache evita i doppioni
  dentro la stessa sessione). Ma con spezzone e finestra la somma è
  di **~4,5 MB a base**, non 55: dieci tappeti ≈ 45 MB, non 550. La
  stima di memoria in Crea somma esattamente questo e avvisa sopra i
  350 MB.
- **«La banda si consuma anche in Aurya Sound (non meditazioni)?»**
  Le **frequenze** (schede della biblioteca, compositore) sono sintesi
  nel browser: **zero banda**, sempre. I **suoni** (anteprime del
  mondo Suoni) sì — ma in streaming progressivo: si paga solo ciò che
  si ascolta davvero.
- **«Il sistema musica impatta il gestionale?»** Dopo ES1, no. Gli
  audio li serve **nginx** (processo separato, sendfile); il worker
  Python — quello del gestionale e del marketplace — riceve dal mondo
  Sound solo API da pochi KB. Le uniche risorse condivise restano la
  scheda di rete e Mongo, entrambe a ordini di grandezza dal limite.
  Il core non è in ostaggio del suono.
- **Bunny**: chiuso per ora, su decisione del founder. Le soglie di
  ES6 dicono quando riaprirlo; l'architettura (id, non URL; 2 punti di
  costruzione degli indirizzi) rende la predisposizione una mezz'ora
  di lavoro il giorno che servirà.


---

## REVISIONE SERALE (21/8) — le tre decisioni finali del founder

1. **Dissolvenze: default 5 e 10** (erano 10 e 20). E le etichette in
   Crea ora dicono cosa succede al suono: **«nasce in (s)»** e **«si
   spegne in (s)»**, coi tooltip che completano la frase —
   «apertura/chiusura» non lo capiva nemmeno il founder.
2. **UNIFORME: TS1b ritrattata.** In Crea si sente esattamente ciò che
   sentirà chi ascolta, dissolvenze comprese. L'opzione `fades` è stata
   RIMOSSA dal motore (non può tornare di nascosto: guardia). Coi
   default nuovi il play in Crea arriva a volume pieno in 5 s — il
   problema che TS1b curava (10 s × attacco 12 s = silenzio) non
   esiste più alla radice, perché l'attacco è 1,5 s da TS1a.
   La nota «anteprima senza dissolvenze» è stata tolta: non è più vera.
3. **Tolleranza ritrattata: standard a 30:00.** Anche le quattro basi
   da 30,1–30,3 sono state portate a 30 esatti con la coda sfumata in
   12 s. Bonus non richiesto ma benvenuto: la ricodifica le ha portate
   da 55,4 a ~35 MB l'una (−80 MB di libreria). Guardia viva a 1800,5 s.

Ora la regola è una e senza eccezioni: **nessuna base supera i 30:00**,
ogni traccia pubblicata è ascoltabile a schermo bloccato, e ciò che
l'operatore sente in Crea è ciò che il mondo sentirà.
