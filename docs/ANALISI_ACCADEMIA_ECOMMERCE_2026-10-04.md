# Aurya come negozio e accademia — analisi di fattibilità

*4 ottobre 2026. Un operatore ha chiesto di vendere corsi su Aurya. Il founder vuole rianalizzare la riattivazione di ciò che è nascosto (prodotti fisici e digitali, guide, libri) e aggiungere i videocorsi fruibili dentro la piattaforma, come un'accademia. Modello economico: commissione sulle vendite online, azzerata per chi ha l'abbonamento. I moduli nascono negli Strumenti, poi si collegano al profilo e a directory dedicate. Analisi profonda prima di costruire: solido, isolato, scalabile, sicuro.*

## 0. La risposta in dieci righe

1. **Il negozio e l'accademia esistono già nel codice.** Sette tipi di prodotto (servizio, biglietto evento, fisico, digitale, corso, noleggio, prenotazione), wizard per fisici e digitali, editor dei corsi con moduli e lezioni, video su Bunny Stream con link firmati, download protetti da token, spedizione con indirizzo strutturato e magazzino, player dei corsi lato cliente. Tutto congelato dal 28 luglio dietro un interruttore per organizzazione (`legacy_commerce`), con dati e codice intatti e una guardia nei test che ne garantisce la riattivabilità.
2. **Non è «riaccendere l'interruttore».** Il mondo legacy ha tre fratture con l'Aurya di oggi: il cliente dei corsi usa un login per negozio diverso dall'account Aurya unico; i video richiedono che ogni operatore porti un proprio account Bunny; la vetrina `/s/{slug}` è stata sostituita dal profilo `/o/{slug}`. Vanno saldate prima di esporre qualcosa.
3. **Il primo collo di bottiglia non è il codice: è Stripe.** In prod zero operatori hanno Stripe collegato, quattro ordini in tutto. Prodotti e corsi si vendono solo online: senza Stripe collegato il modulo è vuoto. L'onboarding Stripe va reso il primo passo del modulo, non un prerequisito nascosto.
4. **Le commissioni sono già nel motore.** Ogni sessione di pagamento applica `application_fee_percent` dell'organizzazione, derivata dal piano; il registro delle commissioni esiste. Oggi tutti i piani hanno 0% per decisione del 10/9. Il modello «commissione su prodotti e corsi, zero col Pro» è un numero per piano, non un'architettura: ma va deciso in coerenza con la promessa «senza commissioni, mai» stampata su landing, /costi e informativa.
5. Consiglio: **tre lotti progressivi, il primo senza video**. Lotto A: digitali (guide, libri in PDF, audio) sul profilo, con l'account Aurya come chiave di accesso. Lotto B: videocorsi con Bunny gestito da Aurya, player dentro l'account Aurya. Lotto C: fisici con spedizione e, solo dopo, le directory pubbliche `/guide`, `/corsi`, `/prodotti`. Ogni lotto è un modulo negli Strumenti, acceso per organizzazione.

## 1. Cosa c'è davvero (inventario)

### 1.1 Catalogo e tipi

| Tipo (`item_type`) | Contenuto collegato | Stato | Note |
|---|---|---|---|
| `service` | opzioni, disponibilità | **vivo** (listino del profilo) | 98 prodotti in prod |
| `event_ticket` | occorrenze, fasce | **vivo** (ritiri ed eventi) | 7 in prod |
| `physical` | magazzino, spedizione | congelato | wizard completo, opzioni di spedizione, indirizzo strutturato nel checkout |
| `digital` | `DigitalAsset` + `IssuedDownload` | congelato | file su disco privato, download a token, max 100 MB, contatore scaricamenti |
| `course` | `Course → CourseModule → Lesson` + `IssuedCourseAccess` | congelato | editor, politiche di accesso (durata), progresso per lezione, Bunny Stream per il video |
| `rental`, `booking` | configurazione inline | congelato | fuori perimetro |

Il registro dei tipi (`models/product_types.py`) è la fonte unica, i validatori per tipo esistono, il backend accetta ancora tutti i tipi: è la UI del «mondo snello» a non offrirli. Landing per tipo già instradate e registrate nel registro delle rotte: `/p/`, `/dg/`, `/ph/`, `/co/`, `/e/`, `/r/`.

### 1.2 Pagamenti e commissioni

- Stripe Connect Express: la sessione nasce **sul conto connesso dell'operatore** (`stripe_account=`), Aurya trattiene `application_fee_percent` scritto sull'organizzazione dal piano (`plan_provisioning`). Rimborsi restituiscono anche la commissione. Registro `platform_fee_ledger`.
- Piani correnti: Gratis, Pro (19/200 dal 1/1/2027), Founding, Partner, tutti con `transaction_fee_percent = 0.0` («zero commissioni, sempre», 10/9).
- Prod oggi: 44 organizzazioni, **0 con Stripe pronto**, 4 ordini (2 pagati). Il checkout su richiesta senza pagamento esiste per i ritiri; per prodotti e corsi non ha senso.

### 1.3 Lato cliente

- **Account Aurya** (`platform_accounts`): unico, con password, cross-operatore; hub `/account` con ordini e biglietti; porta per contatti e, in futuro, checkout.
- **Cliente legacy** (`customer_accounts`): uno per negozio, JWT `customer_token_{slug}`, usato dal **player dei corsi** (`/account/courses/...`) e dal portale ordini legacy, oggi rediretto all'account Aurya. Il player è l'unica superficie legacy rimasta viva, per le email «Vai al corso» già spedite.
- Gli ordini portano `customer_account_id`; non esiste ancora un ponte stabile account Aurya → iscrizione al corso.

### 1.4 Video e file

- **Bunny Stream** è l'unico host video previsto: l'operatore collega la *sua* libreria (API key, library id, chiave di sicurezza dei token) in `integrations.bunny_libraries`; il resolver sceglie la libreria per lezione; il backend firma l'URL di riproduzione a ogni play; il client Bunny sa solo leggere libreria e video (niente creazione librerie, niente upload dal nostro backend). In prod non c'è nessuna variabile Bunny: nessuno l'ha mai usato.
- **File digitali**: filesystem privato del backend (`private_uploads/digital`), mai servito come statico, download via token. Il volume Docker in prod copre solo `uploads`: `private_uploads` **non è su volume**, quindi oggi un rebuild del container perderebbe i file. Da sistemare prima di qualunque vendita digitale.
- **Object storage S3** (`services/object_storage.py`): adapter pronto per Hetzner/R2, non configurato in prod; copre solo gli asset pubblici.

### 1.5 Strumenti e moduli

- `/strumenti` oggi ha una sola scheda, Aurya Sound Studio, con stati (incluso nel Pro, da attivare). La pagina è pensata per ospitare «i moduli che espandono la tua pratica».
- Due meccanismi di accensione convivono: i **feature flag per organizzazione** (`feature_flags.legacy_commerce`, scritti solo dall'admin) e i **moduli a piano** (`module_plans` → `ModuleSubscription`, `require_module(feature)` con `MODULE_OWNERSHIP`: reviews e newsletter sotto `commerce`, statistiche sotto `product_catalog`...). I nuovi moduli devono usare il secondo, con il primo come interruttore di emergenza.

### 1.6 Legale

- Aurya è intermediario: il venditore è l'operatore (titolare autonomo, condizioni per-negozio). I **template legali per-negozio** coprono già prodotti digitali, spedizioni e il diritto di recesso con l'eccezione per i contenuti digitali consumati con rinuncia esplicita. Per vendere, il negozio deve avere le sue condizioni pubblicate (`merchant_legal_status`): oggi nel mondo snello nessuno le ha mai compilate.
- I Termini di Aurya promettono «senza commissioni» in più punti (landing, /costi, piani). Una commissione su prodotti e corsi richiede un aggiornamento esplicito dei testi e dei piani.

## 2. Le tre fratture da saldare

### F1. Un solo cliente: l'account Aurya
Il player dei corsi e i download devono riconoscere l'**account Aurya**, non il cliente per negozio. Oggi un acquirente di un corso dovrebbe avere due identità. Soluzione: l'accesso al corso (`IssuedCourseAccess`) e al download (`IssuedDownload`) si emettono con `platform_account_id`; il player e la pagina dei download vivono dentro `/account` (sezioni «I miei corsi», «I miei file»); il JWT cliente legacy resta accettato solo per le iscrizioni storiche (oggi zero in prod: si può anche dismettere). Il checkout già idrata l'account Aurya (ciclo TA).

### F2. Video gestito da Aurya, non dall'operatore
Chiedere a ogni operatore un account Bunny con API key è un muro: nessuno lo farà. Soluzione: **un account Bunny di Aurya**, una libreria per operatore creata via API (il client va esteso: creazione libreria, upload con URL firmato o TUS diretto dal browser, stato di codifica), chiave dei token per libreria, quote per piano (minuti caricati, GB al mese). L'architettura del resolver resta identica: la libreria «gestita da Aurya» è solo una voce in `bunny_libraries` con `managed=true`. Costo Bunny Stream dell'ordine di 0,005 $/GB al mese di archivio e 0,01 $/GB di traffico, cioè centesimi per corso venduto: si copre con la commissione o con il Pro.

### F3. Dal negozio al profilo
La vetrina `/s/{slug}` è morta: il profilo `/o/{slug}` è il negozio. Prodotti digitali, corsi e fisici devono comparire come **sezioni del profilo** («Guide e libri», «Corsi», «Prodotti») con acquisto inline come già fanno i servizi (`InlineServiceCheckout` riusa il checkout condiviso, che gestisce già spedizione e indirizzo). Le landing `/dg/`, `/co/`, `/ph/` restano le pagine di dettaglio indicizzabili.

## 3. Il modello economico, con i numeri che contano

| Opzione | Pro | Contro |
|---|---|---|
| **A. Commissione su prodotti e corsi (es. 10%), zero col Pro** | coerente con la richiesta; incentiva il Pro; Stripe fa tutto (fee per sessione) | contraddice «senza commissioni, mai» stampato ovunque: va riscritta la promessa limitandola a ritiri e servizi, con una riga nei Termini e nei piani |
| B. Zero commissioni, moduli solo nel Pro | nessuna contraddizione; semplice | il Pro parte a gennaio: fino ad allora i moduli sarebbero chiusi, e chi vende poco non paga 19 € per una guida |
| C. Zero commissioni per tutti, costi video a carico | massima coerenza | Aurya paga Bunny e il supporto senza ritorno: insostenibile se funziona |

Consiglio: **A**, con la commissione solo sui tipi nuovi (digitale, corso, fisico) e dichiarata come «costo del servizio di consegna»: hosting video, download protetti, accesso nell'account del cliente. Numero proposto 10% + Stripe, azzerato nel Pro. Tecnicamente è `application_fee_percent` **per tipo di riga**, non più per organizzazione: la sessione calcola la fee sulle righe nuove e lascia a zero ritiri e servizi. È l'unico pezzo del motore pagamenti da toccare, e va coperto da guardie (ordine misto, rimborso parziale, Pro che scade).

## 4. Il piano a lotti

| Lotto | Cosa | Dipende da | Stima |
|---|---|---|---|
| **A0 Fondamenta** | `private_uploads` su volume Docker (o S3 privato con streaming); onboarding Stripe come primo passo dentro gli Strumenti («Collega gli incassi»); condizioni per-negozio precompilate dal template e pubblicabili in un passo; decisione e testi del modello economico (Termini, /costi, landing, piani) | — | 2 giorni |
| **A Guide e file digitali** | modulo «Guide e file» negli Strumenti: wizard digitale ripulito (titolo, descrizione, copertina, file, prezzo, anteprima facoltativa); sezione «Guide e libri» sul profilo con acquisto inline; `IssuedDownload` legato all'account Aurya; «I miei file» in `/account` con download a token; email di consegna; landing `/dg/` indicizzabile; fee per tipo | A0 | 3 giorni |
| **B Videocorsi** | Bunny gestito da Aurya (account unico, libreria per operatore via API, upload diretto dal browser, stato di codifica); editor corsi ripulito (moduli, lezioni, materiali allegati come digitali); sezione «Corsi» sul profilo; `IssuedCourseAccess` sull'account Aurya; player dentro `/account/corsi` con progresso; quote per piano; landing `/co/` | A | 5 giorni |
| **C Prodotti fisici** | modulo «Prodotti» (wizard fisico ripulito, magazzino, opzioni di spedizione già nel checkout); sezione sul profilo; stati di evasione nel gestionale ordini (già esistenti) | A0 | 2 giorni |
| **D Directory** | `/guide`, `/corsi`, `/prodotti` pubbliche con filtri per disciplina (registro vivo), soglia minima di voci per aprirle (come le pagine locali), sitemap, llms.txt, shell SEO | A, B, C con contenuti veri | 2 giorni |

Ogni lotto: modulo nel registro (`MODULE_OWNERSHIP` + `module_plans`), scheda negli Strumenti con tre stati (incluso, da attivare, in arrivo), interruttore di emergenza per organizzazione, guardie di parità, deploy separato. Il flag `legacy_commerce` non si riaccende mai: resta la via d'uscita storica, i moduli nuovi hanno i loro flag.

## 5. Cosa può rompersi e come si evita

- **Due identità cliente** → tutto il nuovo si lega a `platform_account_id`; il JWT cliente legacy non entra nelle superfici nuove.
- **File persi a un rebuild** → A0 prima di tutto; una guardia che pretende il volume nel compose.
- **Fee sbagliata su un ordine misto** → fee per riga con test su ogni combinazione; il registro delle commissioni confronta con quanto Stripe ha trattenuto.
- **Video non protetti** → URL firmati a scadenza breve (già così), dominio di riproduzione limitato, nessun link diretto al file.
- **Operatore senza condizioni legali che vende** → il modulo non pubblica nulla finché le condizioni per-negozio non sono pubblicate; il template le precompila.
- **Promessa «senza commissioni» tradita** → testi aggiornati **prima** di accendere la fee, con la distinzione chiara: ritiri e servizi sempre senza commissione.
- **SEO**: niente directory vuote; landing di dettaglio con JSON-LD `Product`/`Course`; `noindex` finché la soglia non è raggiunta.
- **Carico**: video e file non passano dal backend (Bunny e storage servono direttamente); il backend firma e registra. Il server attuale regge.

## 6. Cosa chiedere all'operatore che ha fatto la domanda

Che cosa vuole vendere davvero: un corso registrato a moduli, una guida in PDF, incontri dal vivo online. Se è un corso dal vivo via Zoom, oggi si vende già come **servizio** del listino con l'incontro in calendario; non serve nessun lotto. Se è registrato, è il lotto B e l'operatore può essere il pilota: cinque giorni di lavoro con un caso reale valgono più di un modulo generico.

## 7. Decisioni del founder

1. Modello economico: A (commissione sui tipi nuovi, zero col Pro) con quale percentuale, oppure B o C.
2. Ordine: parto da A0 + A (guide e file digitali, senza video) o direttamente da B con l'operatore pilota.
3. Bunny gestito da Aurya: ok ad aprire l'account Bunny di Aurya e ai costi variabili.
4. Directory pubbliche: subito con soglia, o dopo i primi contenuti veri.
