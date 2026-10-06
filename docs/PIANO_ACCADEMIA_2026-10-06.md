# Aurya Accademia — piano v3 (corsi online con moduli, progressi, account)

*6 ottobre 2026, sera. Riprende `PIANO_ACCADEMIA_2026-10-04.md` (v2) e lo integra con quello che nel frattempo è andato in prod: il modulo Prodotti (P0-P2, consolidamento, design, galleria), il lotto S (Stripe col paese giusto), la fee per riga, l'account Aurya obbligatorio per comprare. Qui c'è solo il lotto B di allora, «Videocorsi», ripensato come **primo modulo dell'Accademia**: un contesto nuovo in Strumenti, sicuro, scalabile, isolato, che non tocca nient'altro.*

*Investigazione fatta su codice e documenti ufficiali Bunny (6/10): tutto quello che segue cita file e righe. Nessun codice scritto.*

## 0. Il giudizio in una pagina

**Cosa chiede il founder.** L'operatore crea un percorso online (corso → moduli → lezioni) in modo semplice e immediato; chi compra lo segue nella sua area privata, modulo per modulo, con i progressi e lo stato del percorso; monetizzazione a commissione sulle vendite oppure inclusa in abbonamento (dettaglio da definire). Prima versione di «Aurya Accademia».

**Cosa esiste già (e vale).** Il legacy «Release 4 Courses» è completo da capo a fondo: modelli `Course → CourseModule → Lesson` (`backend/models/course.py`), prodotto gemello di tipo `course` creato automaticamente (`routers/courses.py:78-156`), iscrizione per riga d'ordine con progresso per lezione (`models/issued_course_access.py`, `services/issued_course_access_service.py`: idempotente, revoca al rimborso), firma degli URL video Bunny a 2 ore con rinnovo (`services/bunny/signer.py`), resolver delle librerie (`services/bunny/resolver.py`), un player React con barra laterale, spunta automatica a fine video, «riprendi da dove eri» (`features/customer-portal/course-player/*`, 1.600 righe), email «Vai al corso». Le fondamenta sono buone: non si reinventano.

**Cosa manca (le sei assenze, verificate).**
1. **Nessun upload video**: il client Bunny sa solo leggere (`services/bunny/client.py`: due metodi); l'operatore deve caricare sul pannello Bunny e incollare un GUID in un campo di testo (`CourseEditor.js:379-390`). Inaccettabile per «semplice e immediato».
2. **Bunny per-operatore**: ogni operatore dovrebbe avere il suo account Bunny e incollare chiavi API (`models/organization.py:110-158`). Nessuna variabile Bunny in prod: nessuno l'ha mai usato.
3. **Due identità cliente**: l'iscrizione al corso pretende `customer_account_id` (cliente legacy per negozio), mentre i prodotti usano `platform_account_id` (account Aurya). Nella stessa funzione convivono i due guardiani (`order_creation_service.py:150-187`). L'area account Aurya (`/account`) non elenca corsi; il player vive su `/account/courses/*` col JWT legacy.
4. **La landing passa dallo store** (`public.py:2368-2380`, `/co/{store}/{slug}`), che 4 operatori su 7 in locale e quasi tutti in prod non hanno. Stessa frattura risolta ieri per i prodotti con `/prodotto/{public_slug}/{slug}`.
5. **Nessun modulo, nessun tier, nessun interruttore**: `routers/courses.py` non ha `require_module`; il menu lo nasconde solo `legacy_commerce` (`Layout.js:280-299`); zero quote (corsi, minuti, GB); zero test dedicati (su 264 file di test, nessuno copre corsi, Bunny, iscrizioni).
6. **Nessun «percorso»**: la durata la scrive a mano l'operatore, nessun completamento del corso (solo per lezione), nessuna anteprima gratuita riproducibile, nessun attestato, battito di progresso a orologio e non a posizione reale del video.

**Il verdetto.** Si tiene il 60% (modelli, emissione, progresso, firma, resolver, componenti del player) e si costruisce intorno un modulo nuovo, `accademia`, con lo stesso stampo di Prodotti: registro + tier + interruttore d'emergenza + anteprima in Strumenti + account obbligatorio + fee per riga + landing dal profilo. Il 40% nuovo sta in tre punti: **video gestito da Aurya** (account Bunny unico, libreria per operatore creata via API, upload diretto dal browser con firma del server, webhook firmato), **studente sull'account Aurya** (iscrizioni su `platform_account_id`, «I miei corsi» e player dentro `/account`), **percorso vero** (stato per lezione e per corso, ordine delle lezioni, durata letta da Bunny, anteprime).

**Tempo**: circa 12 giorni in cinque lotti, in anteprima in prod come i Prodotti finché il founder non sblocca. Prima di scrivere codice servono le decisioni del §9.

## 1. Architettura: un modulo chiuso, un solo cliente, byte fuori dal server

```
 Strumenti → scheda «Accademia» (in arrivo · attiva · incluso nel piano)
      │
 /accademia/*  (gestionale, dietro require_module("accademia") + accademia_spento)
      │  corsi · moduli · lezioni · video (TUS firmato) · studenti
      ▼
 courses + products(item_type=course)  ──►  profilo /o/{slug} sezione «Corsi»
      │                                     landing /corso/{public_slug}/{slug}
      │                                     acquisto in pagina (account Aurya + Stripe)
      ▼
 confirm_order → issued_course_accesses(platform_account_id)
      │
 /account → «I miei corsi» → /account/corsi/{iscrizione} (player, progresso)
      │
 Bunny (account Aurya): libreria per org · upload TUS · webhook codifica · URL firmati
```

Le cinque regole, ereditate dal piano v2 e già provate coi Prodotti:
1. **Un solo cliente**: `platform_account_id` è la chiave dell'iscrizione. Il player legacy `/account/courses/*` si dismette (in prod zero iscrizioni, zero corsi): rimando a `/account`.
2. **Il profilo è il negozio**: sezione «Corsi» sotto «Prodotti», stesse card dei ritiri, «Scopri di più» → landing, «Compra» in pagina con `InlineProdottoCheckout` (che già impone l'account).
3. **Il server non trasporta byte**: upload diretto dal browser a Bunny con credenziali firmate a scadenza; riproduzione dall'iframe Bunny con URL firmati; il backend crea, firma, conta, registra.
4. **Modulo a piano, non flag sparsi**: `accademia` nel registro, tier `accademia_retreat_free/_pro`, `KILL_SWITCH_FLAGS["accademia"]="accademia_spento"`, `MODULE_OWNERSHIP`, patto DPA esteso al tipo `course`, migrazione d'avvio idempotente come `migrate_prodotti_p0_v1`.
5. **Commissione per riga**: `course` entra nella mappa per tipo (`fee_per_riga.TIPI_CON_FEE`), col valore del piano; ritiri e servizi restano a zero. L'abbonamento ai contenuti è un lotto a parte (§6).

## 2. Il video: Bunny gestito da Aurya (verificato sui documenti ufficiali il 6/10)

**Perché Bunny e non altro.** Tutto il legacy è Bunny (firma, resolver, iframe, CSP già aperta in nginx). I prezzi: Bunny Stream **0,01 $/GB al mese di archivio, 0,005 $/GB di traffico, nessun costo di codifica, minimo 1 $/mese**; Cloudflare Stream **5 $ ogni 1.000 minuti archiviati, 1 $ ogni 1.000 minuti erogati**. Un corso da 10 lezioni × 15 minuti (150 min, ≈ 4,5 GB in 1080p): su Bunny 0,05 $/mese di archivio e ≈ 0,01 $ per studente che lo guarda tutto (mille studenti ≈ 8 $); su Cloudflare 5 $/mese di archivio e 150 $ per mille studenti. Bunny costa 15-20 volte meno sul traffico, che è la voce che cresce.

**Come funziona, passo per passo (API documentate).**
- **Account unico di Aurya**: una chiave di account in env (`BUNNY_ACCOUNT_API_KEY`), mai nel browser, mai nel documento dell'org.
- **Una libreria per operatore**, creata dal backend alla prima lezione video: `POST https://api.bunny.net/videolibrary` con `Name` (= slug dell'org) → risposta con `Id`, `ApiKey`, `ReadOnlyApiKey`, `PullZoneId`. Si salva in `organizations.integrations.bunny_libraries[]` con `managed=true`, `created_by="aurya"`, come voce con priorità nel resolver esistente. Impostazioni della libreria: `PlayerTokenAuthenticationEnabled=true` (gli URL non firmati non partono), `AllowedReferrers` = aurya.life, `WebhookUrl` = il nostro webhook, download disabilitato nel player.
- **Upload diretto dal browser (TUS)**: il backend crea il video (`POST https://video.bunnycdn.com/library/{id}/videos`, titolo = titolo della lezione) e restituisce al browser le credenziali TUS: endpoint `https://video.bunnycdn.com/tusupload`, header `AuthorizationSignature = SHA256(library_id + api_key + expiration + video_id)`, `AuthorizationExpire`, `VideoId`, `LibraryId`. La chiave API resta sul server; la firma scade (10 minuti). Il browser carica con `tus-js-client` (riprendibile: se cade la rete riparte da dove era), barra di avanzamento vera.
- **Webhook firmato**: Bunny chiama `POST /api/webhooks/bunny` a ogni cambio di stato con `{VideoLibraryId, VideoGuid, Status}` e tre header; si verifica `X-BunnyStream-Signature` = HMAC-SHA256 del corpo con la `ReadOnlyApiKey` della libreria, in confronto a tempo costante. Stati utili: 3 = pronto (si legge la durata con `GET .../videos/{guid}` → `length`), 4 = già riproducibile, 5 = errore. La lezione passa da «in codifica» a «pronto» senza che l'operatore faccia nulla; se il webhook non arriva, un controllo pigro alla lettura della lezione lo rimpiazza.
- **Riproduzione**: firma e iframe esattamente come oggi (`signer.py`, TTL 2 ore, rinnovo 5 minuti prima); watermark con l'email dello studente già previsto.
- **Quote per piano**: minuti o GB caricati per org, contati alla creazione del video e corretti dal webhook; l'upload oltre quota è rifiutato prima di iniziare.

**Rischio e risposta.** Un account solo è un punto singolo: la chiave in env e nel vault del server, rotazione documentata, nessuna scrittura dal browser. Costi variabili coperti dalla commissione o dal Pro. Limite di 5 GB per video e formati video comuni (mp4, mov, m4v, webm) in v1; l'audio puro (meditazioni) si carica come video con copertina fissa oppure come allegato scaricabile: da decidere (§9).

## 3. Il modello: cosa si riusa, cosa si aggiunge

| Pezzo | Oggi | Domani |
|---|---|---|
| `Course`, `CourseModule`, `Lesson`, `CourseResource` (`models/course.py`) | solidi | **riusa**. `Lesson` + `tipo` (`video` \| `testo`), + `video` {`guid`, `library_id`, `stato` caricamento·codifica·pronto·errore, `duration_seconds` da Bunny, `thumbnail_url`}, + `testo` (markdown breve) per lezioni senza video. I moduli restano facoltativi (un corso corto è un modulo solo, invisibile). |
| Prodotto gemello `item_type=course` | solido | **riusa**: prezzo, pubblicazione, slug; via `create_product` come i prodotti. `is_published` resta sul prodotto (fonte unica). |
| `IssuedCourseAccess` + progresso | solido | **riusa** + `platform_account_id` (indice `(platform_account_id, revoked_at)`), + `source` (`order` oggi, `subscription` \| `gift` domani), + `completed_at` di corso (scritto una volta al 100%). `customer_account_id` diventa facoltativo (storico). |
| Emissione alla conferma (`issue_for_order`) | solido | **adatta**: legge `order.platform_account_id`; rifiuta senza. |
| Guardia all'ordine (`course_requires_account`) | sul cliente legacy | **adatta**: `platform_account_id`, stesso messaggio dei prodotti. |
| Firma URL (`signer.py`), resolver (`resolver.py`) | solidi | **riusa**; il resolver prende prima la libreria `managed`. |
| Client Bunny (`client.py`) | legge soltanto | **estendi**: `create_library`, `update_library_settings`, `create_video`, `tus_credentials`, `get_video`, `delete_video`. |
| Webhook Bunny | assente | **nuovo** (`routers/webhooks_bunny.py`), firmato. |
| `bunny_libraries[]` | per-operatore | **estendi**: `managed`, `created_by`, `quota` {`minuti`, `gb`}; le librerie personali restano possibili per chi le ha (nessuno). |
| Fee per riga | physical, digital | **estendi**: `course` in `TIPI_CON_FEE`, nel piano (`transaction_fee_by_type.course`) e nella mappa dell'org. Un solo punto, con guardie. |
| Patto DPA `SELLABLE_ITEM_TYPES` | service, event, physical, digital | + `course`. |
| Editor corsi (1.156 righe), `SalesCard`, griglie | funzionanti ma pesanti, in inglese | **rifai in tre gesti** sul kit `features/prodotti/ui.js` (campi, bottoni, passi, schede). |
| Player (`LessonPlayer`, `CourseSidebar`, `LessonActionBar`, `ProgressRing`, `useLessonNavigation`) | funzionante, client legacy | **riusa i componenti, cambia il client**: le chiamate passano da `customerPortalAPI` a `platformApi` (`/platform/me/corsi/...`); `CoursePlayerPage` si rimonta dentro `/account/corsi/:id` con l'identità grafica di oggi. |
| Landing `/co/` (store) | morta per quasi tutti | **sostituisci** con `/corso/{public_slug}/{slug}` sul telaio di `ProdottoLandingPage` (galleria, chi insegna, programma, anteprime, compra in pagina). |
| Legacy `/account/courses/*`, `/courses/*`, `/co/` | vivi per nessuno | **dismetti** con rimandi; pin dei test aggiornati (`test_listino_tw.py:3398`, `test_seo_locali_sl.py:157`). |

## 4. L'operatore: tre gesti, come i prodotti

**Dove.** Strumenti → scheda «Accademia» (stesso stampo di Prodotti: «In arrivo» oscurata finché il founder non sblocca, aperta al pilota demo; poi «Attivo → I miei corsi»). Prerequisiti dentro il modulo: incassi Stripe, patto, pagina pubblica (riga verde quando ci sono).

**Un corso in tre gesti** (`/accademia/nuovo`):
1. **Il corso**: titolo, due righe, prezzo, immagine (galleria come i prodotti), chi insegna (precompilato dal profilo), durata dell'accesso (per sempre · 12 mesi · 6 mesi), «Altro»: il racconto completo, a chi è pensato, cosa serve.
2. **Le lezioni**: un elenco. «Aggiungi lezione» → titolo, poi o si trascina un video (parte l'upload riprendibile, si vede «carico 42%», poi «in codifica», poi «pronto · 12 min» con l'anteprima) o si scrive un testo; allegati facoltativi (PDF, audio: file privati con download a token, come i digitali); «anteprima gratuita» per una o due lezioni. Riordino con frecce su/giù e trascinamento. «Aggiungi un modulo» = un separatore con un titolo, solo se serve.
3. **Pubblica**: anteprima della card e della pagina; i lucchetti sono gli stessi dei prodotti più due: almeno una lezione pronta, nessuna lezione in errore. 409 con le ragioni in chiaro.

**Dopo**: scheda del corso (`/accademia/:id`) con le stesse sezioni (La scheda · Le lezioni · Le foto · La pagina da condividere · Studenti); «Studenti» = nome, email, a che punto (x/y lezioni), ultima volta, accesso attivo/scaduto/revocato, pulsante «Revoca» con motivo (API esistente). Gli ordini sono in Ordini come tutto il resto.

## 5. Lo studente: compra, trova, riprende, finisce

1. **Profilo** → sezione «Corsi» (card come i ritiri) → **pagina del corso** `/corso/{op}/{slug}`: immagine, chi insegna, descrizione, prezzo, durata totale e numero di lezioni (dai dati Bunny, non a mano), programma con i moduli e le lezioni, **anteprime gratuite riproducibili senza acquisto** (endpoint pubblico `play-url` solo per lezioni `is_preview`, firma breve), «Compra» in pagina con l'account Aurya, «Condividi».
2. **Email** «Il tuo corso è pronto» → un bottone → `/account/corsi/{iscrizione}`.
3. **`/account` → «I miei corsi»**: card con copertina, operatore, barra di progresso, «Continua» (alla prima lezione non completata) o «Ricomincia», stato: in corso · completato · accesso terminato (resta visibile, non parte).
4. **Il player** `/account/corsi/{iscrizione}`: video grande, elenco lezioni a lato (sotto da telefono) con spunte e moduli come sezioni, «Segna come fatta» e spunta automatica a fine video, «Prossima lezione», allegati scaricabili, testo della lezione, «riprendi da dove eri». Progresso salvato a battiti (la posizione reale la manda il player Bunny via `postMessage`, non l'orologio). Al 100% il corso si segna **completato** con data.
5. **Sicurezza**: ogni chiamata verifica `platform_account_id` + stato dell'iscrizione dentro la query Mongo (come oggi, `customer_portal.py:567-590`); `play-url` e `progresso` con rate limit (60/min); URL firmati a 2 ore, rinnovati in silenzio.

## 6. Monetizzazione: oggi la commissione, domani l'abbonamento (senza rifare nulla)

**v1 (questo piano)**: il corso si compra una volta. La commissione è per riga, col tipo `course`, dal piano dell'org: proposta **15% Gratis / 0% Pro**, come i prodotti, così `/costi` resta a due numeri. Stripe sul conto dell'operatore, `application_fee` come oggi; rimborso → revoca dell'accesso (esiste).

**v2 (lotto a parte, quando il founder decide)**: «incluso in abbonamento» = l'operatore vende ai suoi clienti un abbonamento mensile ai suoi contenuti (Stripe Subscriptions sul conto connesso, prodotto di tipo `membership`); l'iscrizione nasce con `source=subscription` e `expires_at` = fine del periodo pagato, rinnovata dal webhook `invoice.paid`, chiusa da `customer.subscription.deleted`. Per questo il modello di oggi prevede già `source` ed `expires_at`: l'abbonamento è un **modo di emettere** l'iscrizione, non un'altra iscrizione. Nessuna decisione va presa adesso, ma i campi si mettono subito.

**Termini**: la v2.12 parla di «Prodotti (digitali e fisici)». Un corso online è un contenuto digitale, ma è più onesto nominarlo: una riga in §6.4 («Prodotti e Corsi online») → **v2.13**, un clic per gli operatori, da fare **insieme allo sblocco** dell'Accademia, non prima (così un solo re-consent). I numeri restano solo su `/costi` (principio già in vigore).

## 7. Dati e API, in breve

**Nuovo o modificato (tutto additivo, retrocompatibile)**
- `courses.modules[].lessons[]`: `+ tipo`, `+ video{guid, library_id, stato, duration_seconds, thumbnail_url, uploaded_at}`, `+ testo`; `bunny_video_guid`/`bunny_library_id` restano letti per il legacy.
- `issued_course_accesses`: `+ platform_account_id` (indice), `+ source`, `+ completed_at`; `customer_account_id` facoltativo.
- `organizations.integrations.bunny_libraries[]`: `+ managed`, `+ created_by`, `+ quota{minuti_caricati, gb_caricati}`.
- Piani: `module_plans.accademia` (`accademia_retreat_free`: 2 corsi, 30 lezioni, 2 GB video; `accademia_retreat_pro`: 30 corsi, 500 lezioni, 50 GB), `transaction_fee_by_type.course`; org: `application_fee_by_type.course`. Migrazione d'avvio `migrate_accademia_a0_v1` (modulo + tier + fee su tutte le org `retreat_*`).
- Env: `BUNNY_ACCOUNT_API_KEY`, `BUNNY_WEBHOOK_BASE_URL`. Nessun'altra variabile.
- Registro rotte: `accademia` (app), `corso` (pubblica, solo con slug); nginx rigenerato; sitemap `course → corso`.

**API** (prefissi del modulo, `require_module("accademia")`)
- Operatore `/accademia`: `GET ""` (corsi, prerequisiti, limiti, commissione), `POST ""`, `GET/PATCH /{id}`, `POST /{id}/pubblica` (lucchetti), `/{id}/ritira`, `/{id}/foto*` (galleria come i prodotti), `/{id}/moduli` e `/{id}/lezioni` (CRUD + `PUT /{id}/ordine` con la lista degli id), `POST /{id}/lezioni/{lid}/video` → `{tus_endpoint, headers, expires_at, video_guid}` (crea la libreria dell'org se manca, controlla la quota), `GET /{id}/lezioni/{lid}/video` (stato; se Bunny dice pronto e il webhook non è passato, aggiorna), `DELETE .../video`, `/{id}/lezioni/{lid}/allegati` (file privati), `GET /{id}/studenti`, `POST /{id}/studenti/{iscrizione}/revoca`.
- Webhook: `POST /webhooks/bunny` (HMAC della libreria, idempotente per `(VideoGuid, Status)`).
- Studente (`platform_accounts.py`, stesso stampo di `/me/file`): `GET /platform/me/corsi`, `GET /platform/me/corsi/{iscrizione}`, `POST .../lezioni/{lid}/play-url`, `POST .../progresso`, `GET .../allegati/{id}` (token).
- Pubblico: `GET /public/corso/{org_slug}/{slug}` (dal `public_slug`, come `/public/prodotto`), `POST /public/corso/{org}/{slug}/anteprima/{lid}` (play-url breve, solo `is_preview`), `corsi` nel payload del profilo; meta per i bot (`_meta_corso`, JSON-LD `Course` + `Offer`).

## 8. Isolamento, sicurezza, scalabilità: le garanzie (con le guardie)

**Isolamento**
- Modulo spento = invisibile: niente menu, niente scheda attiva, niente sezione sul profilo, niente rotte (cancello `AccademiaGate` come `ProdottiGate`), 403 `MODULE_NOT_AVAILABLE` dal backend. Interruttore d'emergenza per org dalla regia.
- Un solo punto toccato nel motore pagamenti (`course` nella mappa fee) con guardie: ordine solo ritiri → fee 0 byte per byte; ordine misto prodotto+corso → somma per riga; rimborso parziale → quota; Pro → 0.
- `confirm_order` cambia in una riga (chiave dell'account); tutto il resto del flusso ordini è quello dei prodotti, già provato in prod.
- Guardie di parità: registro moduli ↔ tier ↔ scheda Strumenti ↔ menu; registro rotte ↔ nginx ↔ sitemap; tipi vendibili ↔ patto DPA.

**Sicurezza**
- Chiave Bunny di account solo in env; chiavi di libreria nel documento org (come oggi) con un lotto successivo di cifratura a riposo; mai nel browser (il browser riceve solo firme a scadenza).
- Webhook verificato con HMAC in tempo costante; idempotente; non fa fede per i pagamenti (solo stato video).
- Video: token auth sulla libreria, referrer limitati, download disabilitato, URL firmati a 2 ore, watermark con l'email.
- Accessi: query con `platform_account_id` + stato; rate limit; revoca con motivo e audit.
- Upload: credenziali TUS a 10 minuti, quota per piano controllata prima, formati e dimensione massima, un video per lezione (il secondo sostituisce e cancella il primo).

**Scalabilità e costi**
- Byte fuori dal server (upload e riproduzione diretti). Indici su `platform_account_id`, `(organization_id, course_id)`, `(VideoGuid)`.
- Costo variabile piccolo (§2). Quando serve S3 per gli allegati: adapter già previsto.

**Test (oggi zero)**: `test_accademia_*.py` per modello, registro/tier/fee (parità), firma TUS e verifica HMAC (vettori fissi), emissione con `platform_account_id`, guardia all'ordine, `/me/corsi` e `play-url` (403/410 come oggi), lucchetti di pubblicazione, rotte/nginx/sitemap, pin dei testi.

## 9. I lotti, con i tempi

| Lotto | Contenuto | Giorni | Dipende |
|---|---|---|---|
| **AC0 Fondamenta** | account Bunny di Aurya + env; modulo `accademia` (registro, tier, kill switch, ownership, DPA), migrazione d'avvio; `course` nella fee per riga (+ piani, + org); `platform_account_id`/`source`/`completed_at` sulle iscrizioni (+ indici); guardia all'ordine sull'account Aurya; emissione sull'account; scheda Strumenti «Accademia · In arrivo» con l'anteprima; rotte nel registro; guardie | 2 | decisioni 1-3 |
| **AC1 L'operatore** | client Bunny esteso (libreria per org, crea video, firma TUS, stato, cancella); webhook firmato; `/accademia/*`; wizard in tre gesti sul kit dei prodotti (upload riprendibile con `tus-js-client`, stato codifica, riordino, moduli facoltativi, allegati, anteprime); scheda corso; studenti e revoca | 4 | AC0 |
| **AC2 Lo studente** | `/platform/me/corsi*`; «I miei corsi» in `/account`; player dentro `/account/corsi/:id` (componenti riusati, client nuovo, progresso a posizione reale, completamento del corso); email «Il tuo corso è pronto»; accesso scaduto/revocato visibile | 3 | AC1 |
| **AC3 Il pubblico** | `/corso/{org}/{slug}` (telaio della pagina prodotto, programma, anteprime riproducibili, compra in pagina), sezione «Corsi» sul profilo, meta per i bot, sitemap, dismissione delle rotte legacy con rimandi | 1,5 | AC2 |
| **AC4 Regia e rifinitura** | colonna «Accademia» in regia Operatori (corsi, studenti, GB), interruttore per org, prova end-to-end con pagamento Stripe di test, mobile su tre browser, `/costi` e Termini v2.13 pronti per lo sblocco | 1,5 | AC3 |
| **Totale** | | **12** | |
| *AC5 Abbonamento ai contenuti* | *membership dell'operatore (Stripe Subscriptions sul conto connesso), iscrizioni `source=subscription`, rinnovi dai webhook* | *4, dopo* | *decisione del founder* |

Ogni lotto: suite al baseline, prova in locale dal browser, deploy separato in **anteprima** (come Prodotti: scheda visibile, modulo chiuso, pilota demo), documento e memoria. Lo sblocco pubblico dell'Accademia è un interruttore + Termini v2.13, quando il founder lo dice.

## 10. Rischi veri e risposte

| Rischio | Risposta |
|---|---|
| Un operatore carica un video da 3 GB in 4G e cade la rete | TUS è riprendibile: riparte dal byte dove era; stato visibile; limite per video e quota per piano |
| Il webhook Bunny non arriva | controllo pigro alla lettura della lezione e dalla scheda («Aggiorna stato»); nessuno resta bloccato |
| Il player non parte su iPhone | iframe Bunny con HLS nativo, già usato dal legacy; prova sui tre browser nel lotto AC4 |
| Pirateria | token auth + referrer + no download + watermark: lo standard; il resto non vale il costo |
| Costi Bunny fuori controllo | quote per piano, contatore per org in regia, allarme sopra soglia |
| Rimborso dopo aver visto il corso | condizioni per-negozio (recesso escluso per contenuti digitali avviati), revoca automatica già esistente |
| Due identità cliente | tutto il nuovo su `platform_account_id`; legacy dismesso con rimandi (zero iscrizioni in prod) |
| «Senza commissioni» | i testi dicono già «ritiri e servizi senza commissioni»; i corsi entrano nella frase dei Prodotti su `/costi` |
| Account Bunny unico | chiave solo in env, rotazione documentata, nessuna scrittura dal browser |

## 11. Decisioni per partire

1. **Account Bunny di Aurya**: lo apri tu (prova 14 giorni senza carta, poi minimo 1 $/mese) e mi passi la chiave di account da mettere in env in prod. Senza, AC1 non parte.
2. **Commissione sui corsi**: 15% Gratis / 0% Pro come i prodotti (un numero solo su `/costi`), oppure una percentuale diversa?
3. **Termini**: aggiungo «e Corsi online» nella riga dei Prodotti (v2.13) **al momento dello sblocco**, non adesso: confermi?
4. **Lezioni v1**: video + testo + allegati. L'audio puro (una meditazione) lo tratto come allegato scaricabile oppure come video con copertina? Proposta: allegato in v1, «traccia audio» in un lotto dopo (riusando il player di Aurya Sound).
5. **Anteprime gratuite** riproducibili dalla pagina senza acquisto: sì?
6. **Legacy**: dismetto `/account/courses/*`, `/courses/*`, `/co/` con rimandi (zero dati in prod): confermi?
7. **Ordine**: parto con AC0 + AC1 in locale subito, in anteprima in prod come i Prodotti.

## 12. Stato

**Decisioni del founder (6/10 notte):** 1 account Bunny lo apre lui quando glielo chiedo; 2 commissione 15% Gratis / 0% Pro per ora (potrebbe rendere i corsi solo per abbonati: da valutare); 3 Termini v2.13 allo sblocco; 4 lezioni v1 video+testo+allegati, audio come allegato; 5 anteprime gratuite sì; 6 legacy dismesso; 7 si parte dalle fondamenta.

**AC0 Fondamenta IMPLEMENTATO in locale (6/10 notte).** Niente si vende: le rotte arrivano con AC1/AC2.
- modulo `accademia` registrato (`modules/accademia`), `MODULE_OWNERSHIP["accademia"]`, interruttore `accademia_spento` (`KNOWN_FLAGS`), patto DPA esteso al tipo `course`;
- tier `accademia_retreat_free` (2 corsi, 30 lezioni, 2 GB video) e `accademia_retreat_pro` (30, 500, 50 GB) nei piani `retreat_*`; fee `course` nella mappa per riga (`TIPI_CON_FEE`) e nei piani (Gratis 15, abbonati 0); migrazione d'avvio `migrate_accademia_a0_v1` (modulo + tier + SOLO la chiave `course` nella mappa dell'org, le altre intatte; in locale 11 org, 8 a 15);
- iscrizioni sull'account Aurya: `IssuedCourseAccess` + `platform_account_id` (indice con `revoked_at`), `source` (`order` oggi, `subscription`/`gift` domani), `completed_at` di corso; `customer_account_id` facoltativo (storico); l'emissione legge `order.platform_account_id` (legacy accettato); la guardia all'ordine chiede l'account Aurya con il messaggio dei prodotti;
- Strumenti: scheda «Accademia · In arrivo» oscurata, senza pulsanti, con l'anteprima in quattro righe; `features/accademia/stato.js` (`ACCADEMIA_UI_PRONTA=false`, pilota admin@demo.com) pronto per i cancelli di AC1;
- guardie: `tests/test_accademia_ac0.py` (registro, tier, fee con una riga corso in un ordine misto, modello e emissione, guardia, scheda); pin storici aggiornati (ownership, moduli del Gratis, mappa fee).

**Prossimo: AC1 L'operatore** — serve la chiave di account Bunny (il founder apre l'account quando glielo chiedo: lo chiedo all'inizio di AC1, serve per la libreria e l'upload).

