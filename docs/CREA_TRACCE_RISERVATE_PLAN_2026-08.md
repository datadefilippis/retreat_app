# Crea Studio col piano Pro — il piano, spiegato (ciclo TR, v3)

*v3 del 27/8/2026, riscritta perché si capisca. Due correzioni del
founder rispetto alla v2: (1) se l'operatore smette di pagare, i link
dei suoi clienti SI SPENGONO — non c'è periodo di grazia; (2) serviva
chiarezza sul pannello system admin: nessun conflitto, qui è spiegato
come convivono. Il principio resta: preciso, isolato, scalabile, e
il flusso di chi oggi usa Crea in produzione (founder e Valentina)
non cambia di un byte.*

---

## 1 · In una frase

**Chi paga l'abbonamento Aurya Pro (19€) ha Crea Studio: compone le
sue meditazioni e le condivide in privato coi suoi clienti. Chi ha la
concessione manuale del system admin (oggi: tu e Valentina) ha Crea
COMPLETO, come oggi: compone E pubblica nelle Meditazioni di Aurya.**

## 2 · Le due chiavi (e perché il pannello admin non va in conflitto)

Immagina due chiavi diverse per la stessa stanza (Crea):

**CHIAVE 1 — la concessione manuale.** È quella che esiste OGGI: la
dai tu dal pannello `/admin/sound`, org per org. **Non cambia niente**:
stesso pannello, stesso interruttore, stesso audit. Chi ce l'ha può
fare TUTTO — comporre, pubblicare nelle Meditazioni pubbliche di
Aurya, e (novità) anche condividere tracce in privato. Questa chiave
non scade mai: non c'entra col billing.

**CHIAVE 2 — l'abbonamento (nuova, automatica).** Chi ha il piano Pro
attivo ha Crea Studio senza che nessuno debba fare niente: il sistema
lo capisce da solo guardando l'abbonamento, a ogni richiesta. Questa
chiave apre comporre + condividere in privato. **NON apre mai le
Meditazioni pubbliche**: il server rifiuta la pubblicazione pubblica
a chi ha solo questa chiave, anche se qualcuno provasse per vie
traverse.

**Come convivono — le tre regole:**
1. Il pannello admin **continua a esistere identico** per la chiave 1.
2. Nel pannello aggiungiamo una colonna in sola lettura che ti mostra
   chi ha la chiave 2 («Studio: attivo via abbonamento»), così hai la
   regia completa in un posto solo — ma non devi gestirla: si accende
   e spegne da sola col billing.
3. Un'org può avere entrambe le chiavi (es. un giorno Valentina con
   un suo abbonamento): vince sempre la più ampia, cioè la manuale.
   E per le emergenze c'è un interruttore per-org («spegni Studio»)
   che chiude la chiave 2 a una specifica org anche se paga — il
   kill switch per gli abusi.

**In pratica per te non cambia nulla**: continui a dare e togliere la
chiave 1 come oggi. La chiave 2 lavora da sola.

## 3 · Cosa succede quando un operatore si abbona (il film)

1. L'operatore sottoscrive il Pro (o parte la prova gratuita — è
   quella già esistente del piano, col blocco anti-seconda-prova già
   in produzione).
2. Alla prima visita in area Sound trova Crea aperto, con una
   schermata di benvenuto («Benvenuto nello Studio») che spiega le
   tre mosse: registra, componi, condividi.
3. Compone. Quando pubblica, la traccia è **automaticamente
   riservata**: non gli viene nemmeno mostrata l'opzione «Meditazioni
   di Aurya» (e se la chiedesse al server a mano, riceverebbe un no).
4. Dalla lista delle sue tracce sceglie un contatto dal suo CRM (o ne
   crea uno al volo) e genera **il link personale di quel contatto**.
   Lo invia con WhatsApp o email dai pulsanti che già esistono.
5. Il cliente apre il link e ascolta. Senza registrarsi, senza
   scaricare niente: il player è quello di Aurya.

## 4 · Il link del cliente: come funziona, e le tue tre domande

- **«Il link è accessibile solo a quell'utente?»** Ogni contatto ha
  il SUO link, diverso da quello di chiunque altro (un codice casuale
  impossibile da indovinare, registrato da noi). Tecnicamente chi
  possiede il link può aprirlo — come un invito personale: se Marco
  lo gira, sta girando il SUO invito, e l'operatore lo vede (ogni
  link conta i suoi ascolti e l'ultima apertura). Il lucchetto duro
  per-persona (verifica dell'email del cliente prima dell'ascolto) è
  la fase 2: il disegno la prevede già, si accende con un flag.
- **«Deve creare un account?»** No, per scelta: obbligare il cliente
  di uno yoga teacher a registrarsi su Aurya ammazza l'uso al primo
  invio. L'account cliente è la fase 3, se e quando servirà.
- **«E se l'operatore vuole revocare?»** Un click sul singolo link:
  quel contatto smette di ascoltare SUBITO, gli altri continuano.
  Niente da rigenerare, niente link degli altri da rimandare.

## 5 · Se l'operatore smette di pagare (deciso dal founder)

**I link si spengono.** Abbonamento scaduto o annullato → Crea si
chiude E tutti i link dei suoi clienti smettono di suonare, subito.
Il cliente che apre un link spento vede un messaggio neutro («Questo
ascolto non è al momento disponibile») — mai una colpa esposta al
cliente; l'operatore invece vede chiaro nel gestionale il perché e il
bottone per riattivare. Le tracce e i link **non si cancellano**:
alla riattivazione tutto riprende esattamente da dov'era, senza
rigenerare niente. (Tecnicamente è la scelta più semplice: il
controllo dell'abbonamento sta anche sulla rotta d'ascolto.)

Le org con la chiave 1 (tu e Valentina) non c'entrano col billing:
niente si spegne mai per loro.

## 6 · Il muro: le prove che l'attuale non si rompe

Prima di qualunque deploy, questi test devono essere verdi — sono il
contratto del «non bugghi l'attuale»:

1. **Il test di Valentina**: org con la chiave 1 e senza abbonamento →
   compone, pubblica nelle Meditazioni, la traccia appare in catalogo.
   Identico a oggi, byte per byte.
2. Org con solo chiave 2 → pubblica: la traccia è privata; il
   tentativo di pubblicazione pubblica riceve un no dal server; la
   traccia non appare MAI in catalogo, sitemap, SEO, profilo.
3. Org senza chiavi (free/starter) → Crea chiuso, come oggi.
4. Link revocato → non suona più; gli altri link della stessa traccia
   sì.
5. Abbonamento scaduto → Crea chiuso E i link non suonano; alla
   riattivazione tutto riprende.
6. Prova gratuita → Studio attivo; seconda prova → negata (già
   garantito dal billing esistente).
7. Interruttore d'emergenza «off» → Studio spento anche se paga.

## 7 · Le onde (ordine di costruzione)

- **TR1 — la chiave 2** (mezza giornata): la funzione unica che dice
  «Studio attivo?» leggendo l'abbonamento, il nuovo controllo sugli
  endpoint di Crea, l'interruttore d'emergenza, la colonna nel
  pannello admin. Test 1, 3, 6, 7.
- **TR2 — riservata vs pubblica** (mezza giornata): il campo di
  visibilità sulla traccia (assente = pubblica: zero migrazioni sui
  dati esistenti), il portiere sulla pubblicazione, il filtro
  strutturale che tiene le private fuori da ogni superficie pubblica.
  Test 2.
- **TR3 — i link per contatto** (una giornata): l'oggetto-condivisione
  (org, traccia, contatto, codice, stato, contatori), gli endpoint
  crea/lista/revoca, la pagina d'ascolto `/ascolta/{codice}` col
  controllo abbonamento, il collegamento al player e al file master
  già esistenti. Test 4 e 5.
- **TR4 — la UI** (una giornata): il benvenuto nello Studio, la
  scelta di visibilità al publish (solo per chi ha la chiave 1), il
  pannello condivisioni nelle «mie tracce» (scegli contatto → crea
  link → invia → revoca), il messaggio neutro del link spento.
- **TR5 — i doveri** (mezza giornata): cancellazione definitiva che
  porta via anche condivisioni e master privati; la riga nei ToS
  sulla titolarità («le meditazioni che componi restano tue»);
  niente dati nuovi sul cliente finale oltre al contatore.
- **TR6 — il collaudo**: il muro del §6 completo + il film del §3
  provato per intero, compresa la revoca e la scadenza.

TR1+TR2+TR3 stanno insieme in un branch (~2 giorni); TR4 sopra;
TR5-TR6 prima del deploy. Deploy SOLO col muro verde e col tuo go.

## 8 · Fuori scope, detto per non rifarlo

Verifica email per-share (fase 2), account cliente (fase 3),
analytics oltre i contatori, percorsi assegnati, email transazionali,
watermark audio. Il catalogo Professional resta com'è: spento in
vetrina, substrato della futura fase-vibrazioni.

---

## Appendice tecnica (per l'implementazione)

- **Chiave 2 derivata, mai sincronizzata** — una funzione sola:
  `studio_attivo(org) = override!="off" AND (sound_composer OR
  override=="on" OR (plan=="pro" AND billing_status in
  {active,trialing,manual}))`. Campi reali già in produzione:
  `organizations.plan`, `organizations.billing_status`,
  `has_used_trial_plan_slug` (anti-doppia-prova). Campo nuovo:
  `sound_studio_override` ∈ {assente, "on", "off"}.
- **Gate**: `require_sound_crea` = chiave 1 O chiave 2, sui 12
  endpoint del compositore; `require_sound_composer` resta INTATTO e
  guarda solo la chiave 1 (pubblicazione pubblica, pannello admin).
- **Visibilità**: `frequency_tracks.visibility` ∈ {assente=public,
  "private"}; filtro `visibility != "private"` nella query-base del
  catalogo (un solo punto, guardato — stile `_mio()`).
- **Share**: collezione `sound_shares{id, org_id, track_id,
  contact_id, token(128-bit random, opaco — non JWT: la revoca deve
  essere immediata), stato, creato_il, revocato_il, accessi,
  ultimo_accesso}`; indici su token (unico), (org_id, track_id),
  (org_id, contact_id). Rotta `/ascolta/{token}`: share attivo AND
  traccia privata pubblicata AND studio_attivo(org proprietaria) →
  master-pass effimero (scope `fqz_condivisa`) → nginx serve i byte
  (X-Accel, Range). Pagina noindex, fuori da sitemap/shell; rate
  limit sulla rotta.
- **Invio**: riuso di ContactActions (wa.me/mailto + gate GDPR).
