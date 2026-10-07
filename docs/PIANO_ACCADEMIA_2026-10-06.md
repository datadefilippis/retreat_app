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

**AC1 L'operatore IMPLEMENTATO in locale (7/10 sera).** Funziona senza chiave Bunny (si creano corsi, moduli, lezioni di testo; l'upload dice «non ancora attivo»); con la chiave in env si accende tutto.
- **Bunny gestito** (`services/bunny/gestito.py`): chiave di account solo in env (`BUNNY_ACCOUNT_API_KEY`), una libreria per org creata via API alla prima lezione video (`assicura_libreria`: nome `aurya-{slug}`, impostazioni di **costo** — risoluzioni 360p/720p/1080p, originali NON conservati, niente MP4 fallback né direct play, nessuna replica — e di **sicurezza** — token auth, referrer aurya.life, webhook), hostname del pull zone letto da Bunny, salvata in `bunny_libraries[]` con `managed/created_by/read_only_api_key/quota`; firma TUS = SHA256(library_id + api_key + expire + video_id) a 10 minuti; verifica webhook HMAC-SHA256 con la ReadOnlyApiKey a tempo costante. Client esteso (`create_video`, `get_video`, `delete_video`, `BunnyAccountClient.create_library/update_library/get_pullzone`).
- **Webhook** `POST /api/webhooks/bunny` (firmato, idempotente): stato della lezione (codifica → pronto → errore), durata/dimensione/miniatura da Bunny quando è pronto, quota corretta con la dimensione reale, campi del legacy (`bunny_video_guid`, `bunny_library_id`) allineati così firma e player esistenti funzionano.
- **API** `/api/accademia` dietro `require_module("accademia")`: lista (prerequisiti, limiti, quota video, commissione `course`, `public_slug`, `bunny_attivo`), crea (patto DPA, quota `corsi_max`, slug libero, prodotto gemello riusato, modulo «Lezioni» di default), scheda/modifica (prezzo e testi sul gemello), copertina, pubblica con lucchetti (Stripe, patto, pagina, prezzo, ≥1 lezione pronta, nessun video in lavorazione o in errore, nessuna lezione vuota), ritira, togli; moduli (crea, rinomina, togli → le lezioni passano al precedente); lezioni (video o testo, anteprima, sposta tra moduli, togli), `PUT /ordine`; video (`POST` → quota PRIMA, libreria, video su Bunny, credenziali TUS; `GET` stato con rilettura pigra; `DELETE`); studenti (nome, email, percentuale, stato attivo/completato/scaduto/revocato) e revoca con motivo.
- **Modelli additivi**: `Lesson.tipo/testo/video{guid, library_id, stato, duration_seconds, size_bytes, thumbnail_url}`; `BunnyLibrary.read_only_api_key/managed/created_by/quota`.
- **Frontend** (`features/accademia/*` sul kit dei Prodotti): `/accademia` (lista), `/accademia/nuovo` (tre gesti: il corso → le lezioni → pubblica), `/accademia/:id` (scheda, lezioni, studenti), `LezioniEditor` (titolo, dropzone video con `tus-js-client` riprendibile e barra, stato codifica con rilettura ogni 6 s, testo, anteprima gratuita, frecce per l'ordine, moduli facoltativi), cancello `AccademiaGate` (anteprima: aperto al pilota), scheda Strumenti «Attivo → I miei corsi» per i piloti, rotta `accademia` nel registro + nginx.
- guardie: `tests/test_accademia_ac1.py` (firma TUS con vettore, HMAC, stati, impostazioni di costo, client, modelli, webhook, router, ragioni di pubblicazione, slug).
- **Per accendere i video**: aprire l'account Bunny e mettere `BUNNY_ACCOUNT_API_KEY` (+ `BUNNY_WEBHOOK_BASE_URL=https://aurya.life`) nell'env di prod; la prima lezione video crea la libreria.

**Prossimo: AC2 Lo studente** — `/platform/me/corsi*`, «I miei corsi» in /account, player dentro /account/corsi/:id, email «Il tuo corso è pronto».

**Prova dal vivo con la chiave Bunny (7/10 sera).** Chiave di account in `.env.production` (messa dal founder) e nel `.env` locale. Risultati: la libreria gestita `aurya-masseria-demo` (id 773157) è nata via API con le impostazioni di costo verificate su Bunny (360p/720p/1080p, originali non conservati, niente MP4 fallback né direct play, codifica standard x264) e token auth acceso; l'upload TUS dal Mac è andato a buon fine (1,6 MB, H.264 720p, 16 s); due correzioni trovate e committate: (1) sulle org con `integrations: null` il `$push` fallisce → `$set` dell'oggetto intero, e una libreria già creata con lo stesso nome viene ADOTTATA invece di duplicata; (2) `AllowedReferrers` nell'update è ignorato da Bunny → endpoint dedicato `addAllowedReferrer`; (3) due vocabolari di stato: nell'oggetto video «finito» è 4 (3 = transcodifica), nel webhook è 3. **Aperto**: entrambi i video (TUS e PUT diretto) restano a `status 2 / encodeProgress 0` per oltre 25 minuti con `Balance 0` sul conto: da verificare sul pannello Bunny se l'account di prova è attivo per la codifica (email confermata, trial Stream attivo).

**Prova dal vivo, seconda parte (7/10 sera): FUNZIONA.** La codifica Bunny è arrivata dopo ~30 minuti di coda (video 16 s, 720p): la lezione è passata a «pronto · 15 s» con miniatura, la quota a 10,9 MB (tre rendition), il corso è pubblicabile. Tre scoperte, tutte committate:
1. **I codici di stato sono due vocabolari**: l'oggetto video (GET) ha 4 = finito e 3 = transcodifica; il webhook ha 3 = finito. La rilettura pigra usa il vocabolario giusto.
2. **La protezione vera è sul pull zone, non sulla libreria.** `PlayerTokenAuthenticationEnabled` da solo NON blocca playlist e miniature (rispondono 200 col referrer giusto). Con `ZoneSecurityEnabled` sul pull zone (acceso via API alla creazione) playlist e miniature rispondono 403 senza firma anche col referrer di aurya.life; la `ZoneSecurityKey` diventa la `token_security_key` della libreria: firma l'embed (sha256 esadecimale di chiave+guid+expires, il firmatario legacy) e i file CDN (base64url di sha256 grezzo di chiave+path+expires, `firma_url_cdn`). Verificato nel browser: embed firmato → player con il video (poster, 00:15, play funzionante); embed senza firma → bloccato. Il referrer resta come seconda cintura (aurya.life, www, localhost per il dev).
3. **Le miniature si firmano a ogni lettura** (24 ore), mai salvate firmate.
Pulizia: il video orfano della prova diretta è stato cancellato; la pagina HTML di prova non è nel repo.

**Ordine su Bunny (7/10, founder: «non vorrei fare un mappazzone»).** La struttura su Bunny rispecchia Aurya: **libreria = operatore** (`aurya-{slug}`), **collezione = corso** (cartella creata alla prima lezione video, salvata in `courses.bunny.collection_id`, rinominata se cambia il titolo del corso), **video = lezione** col titolo «NN · titolo» dove NN è la posizione nel corso; al riordino i numeri si riallineano, alla rinomina il titolo segue. Provato dal vivo sulla libreria del demo: collezione «Respiro consapevole in 5 giorni», video «01 · …», «03 · …». Niente dipende dai titoli Bunny: l'ordine vero vive in Aurya, i titoli servono a chi guarda il pannello.

**AC2 Lo studente IMPLEMENTATO in locale (7/10 notte).**
- **API** `/api/platform/me/corsi` (`routers/platform_corsi.py`, stampo di `/me/file`): lista con progresso, stato (attivo · completato · scaduto · revocato), operatore e «prossima lezione»; dettaglio con lo STESSO contratto del legacy (`enrollment, course, progress, progress_stats`) più `tipo`, `testo`, `video_pronto`, miniature firmate; `play-url` (60/min; 409 `video_not_ready` se il video non è pronto; URL firmato a 2 ore col watermark dell'email); `progresso` (120/min; `watched_seconds` monotono, `completed_at` fisso; al 100% `completed_at` del corso una volta sola, `completato_ora` nella risposta). `platform_account_id` sempre dentro la query Mongo. Trappola trovata: con `@limiter.limit` il `from __future__ import annotations` fa leggere il corpo come query (422) → tolto.
- **Account**: sezione «I miei corsi» in `/account` (card con copertina, operatore, barra, «Comincia / Continua / Rivedi», accesso scaduto o terminato visibile ma non apribile); player `/account/corsi/:enrollment_id` (`features/account/CorsoStudentePage.js`) che RIUSA i componenti legacy (LessonPlayer con la prop `api`, CourseSidebar, LessonActionBar, LessonDetails, HelpCheatsheet, useLessonNavigation) nel guscio del sito, con le lezioni di testo, «Il video sta arrivando» per i video non pronti, «Percorso completato», errori gentili (non tuo · revocato · scaduto · non più disponibile).
- **Email**: «Il pagamento è andato a buon fine e il tuo corso è pronto…» con CTA «Vai ai miei corsi» quando l'ordine è solo corsi; le card dei corsi puntano a `/account/corsi/{id}`.
- **Provato dal vivo**: ordine confermato con una riga corso per l'account `viaggiatore@example.com` → iscrizione emessa con `platform_account_id`; lista 33% → 67% con i progressi; play-url firmato; nel browser: card con barra e «Continua», player con lezione di testo, lezione video (iframe Bunny con poster e watermark), frecce da tastiera. Il legacy `/account/courses/*` resta finché AC3 non lo dismette con i pin.
- guardie: `tests/test_accademia_ac2.py`.

**Prossimo: AC3 Il pubblico** — `/corso/{org}/{slug}` (telaio della pagina prodotto, programma, anteprime riproducibili, compra in pagina), sezione «Corsi» sul profilo, meta per i bot, sitemap, dismissione del legacy.

**AC3 Il pubblico IMPLEMENTATO in locale (7/10 notte).** Il founder ha chiesto la pagina del corso «come eventi e prodotti», configurabile dall'operatore, e cosa proporre per le anteprime: la risposta è ENTRAMBE le cose, un **video di presentazione** caricato apposta e le **lezioni segnate come anteprima gratuita**, riproducibili dalla pagina senza comprare.
- **La pagina** `/corso/{org}/{slug}` (`features/storefront/CorsoLandingPage.js`, telaio di `/prodotto`): in alto il video di presentazione (o la copertina), scheda con chi insegna (ritratto, città, recensioni), due righe, lezioni · durata · accesso, prezzo, «Compra il corso» in pagina (`InlineProdottoCheckout` con riga `course`: account Aurya + Stripe, testo di esito «in «I miei corsi»»), «Condividi» (share nativo o link copiato), tre rassicurazioni; sotto **Il programma** (moduli e lezioni, «Guarda gratis» sulle anteprime), il racconto, chi insegna, altri corsi; su telefono barra fissa con prezzo e Compra. Dati da `GET /api/public/corso/{org}/{slug}` (dal `public_slug`, 404 su org campione o senza pagina; il programma NON porta mai GUID). Anteprime: `POST /api/public/corso/{org}/{slug}/anteprima/{lezione|trailer}/play-url` (30/min per IP, URL firmato a 1 ora senza watermark; solo il trailer pronto o una lezione video `is_preview` E pronta, le altre 404).
- **Il video di presentazione**: `Course.trailer` (stesso `VideoLezione`), endpoint `POST/GET/DELETE /api/accademia/{id}/trailer` (quota, libreria, collezione del corso, video «00 · Presentazione» su Bunny, credenziali TUS; uno per corso, il nuovo sostituisce; la cancellazione restituisce la quota), webhook che riconosce anche `trailer.guid`; nel gestionale la scheda «Il video di presentazione» (`TrailerEditor`, stesso ciclo delle lezioni) e la scheda «Condividi» col link della pagina (`LinkPagina` con prefisso `corso`); in lista «Copia link» sui corsi online.
- **Il profilo**: sezione «Corsi online» (`_operator_corsi`: solo pubblicati con almeno una lezione pronta; card della misura dei ritiri con lezioni · minuti · accesso, «Scopri di più» → la pagina, «Compra» in pagina).
- **Bot e registro**: `_meta_corso` nella shell (title, description, og:image, JSON-LD `Course` + `Offer` + breadcrumb) con `head == "corso"`; sitemap `course → corso`; registro: `corso` pubblica + solo_con_slug, `co` e `courses` sono rimandi (`servizio` per la SPA, 301 di prefisso in nginx: `/co/{org}/{slug}` → `/corso/{org}/{slug}` conservando la coda, `/courses*` → `/accademia`).
- **Legacy dismesso**: App.js non carica più `CourseLandingPage`, `CoursesPage`, `CourseEditor`, `CoursesIndexPage`, `CoursePlayerPage` (i file restano sul disco, codice morto da potare in un giro a parte); `/account/courses/:id` → `/account/corsi/:id` (le vecchie email atterrano sul player Aurya), `/courses*` → `/accademia`, la voce «Corsi» legacy sparisce dalla barra. Pin aggiornati (`test_listino_tw`, `test_seo_locali_sl`, `test_landing_pages_lp`, `test_indicizzazione_ix`).
- **Provato dal vivo** (demo, lezione «Giorno 1» segnata anteprima): landing 200 senza GUID, anteprima 200 / lezione non anteprima 404 / trailer assente 404; shell per Googlebot con title e `Course`; nel browser: pagina, «Guarda gratis» → player Bunny firmato nel riquadro in alto, «Corsi online» sul profilo, `/co/...` → `/corso/...`, `/courses` → `/accademia`, scheda trailer e Condividi nel gestionale; trailer via API: POST → credenziali TUS e stato «caricamento», GET, DELETE → quota tornata a 10,9 MB.
- guardie: `tests/test_accademia_ac3.py`.

**Prossimo: AC4 Regia e rifinitura** — colonna «Accademia» in regia Operatori, prova end-to-end con pagamento Stripe di test, mobile, `/costi` e Termini v2.13 pronti per lo sblocco; poi il giro di deploy di AC1–AC4 in anteprima (la chiave Bunny è già nell'env di prod: il backend va ricreato per leggerla).

**AC4 Regia e rifinitura IMPLEMENTATO in locale (7/10 notte).**
- **Regia Operatori**: colonna «Strumenti» in ogni riga (`_strumenti_batch`: tre aggregazioni sulla pagina, mai per riga): Prodotti `online/n`, Accademia `online/corsi · studenti · GB` (il pubblicato si legge dal prodotto gemello, i GB dalla quota delle librerie Bunny) e i due **interruttori per org** (`prodotti_spento`, `accademia_spento`): un clic scrive il flag con il router esistente `PUT /admin/feature-flags/{org}` (system admin, audit) e il modulo risponde 403 al gestionale; **da AC4 il flag spegne anche il pubblico** (niente card sul profilo, landing e anteprime 404, ordine rifiutato) perché un operatore tagliato fuori non deve continuare a vendere. Prima i kill switch non avevano UI.
- **Checkout del corso con l'account Aurya**: trovati e chiusi due intoppi veri nella prova end-to-end: (1) con l'account Aurya riconosciuto il form chiedeva ANCORA un «account (richiesto)» legacy con password → `requiresCustomerAccount` è falso quando `platformLoggedIn`; (2) in dev il preflight CORS dell'ordine rispondeva 400 perché `X-Aurya-Account` non era fra gli header ammessi (in prod è same-origin) → aggiunto.
- **Prova Stripe test end-to-end dal browser**: pagina del corso → Compra → ordine → Checkout Stripe (sandbox, carta di prova) → ritorno su `/s/checkout-success` → `verifica-pagamento` → ordine ORD-10005 `confirmed/collected`, iscrizione emessa con `platform_account_id`, email «ordine confermato» al cliente e «nuovo ordine pagato» all'operatore (dry run), sessione Stripe `paid 3900 eur` con la fee della mappa per riga (demo = Pro → 0; il 15% del Gratis passa dalla stessa mappa provata coi prodotti).
- **Rifiniture**: pagina di successo con il blocco «Il tuo corso è pronto → Vai ai miei corsi» (riga `course`); sulla pagina del corso, se lo segui già (iscrizione attiva o completata sull'account riconosciuto) niente «Compra»: «Vai al corso / Rivedi il corso» + nota «già tuo»; mobile verificato (landing, player, account a 375 px senza scorrimento orizzontale).
- **/costi**: i corsi online accanto ai prodotti (15% Gratis, 0 Pro): solo numeri, nessun bump dei Termini.
- **Termini v2.13 PRONTI, NON applicati**: `scripts/sblocco_accademia_v213.py` (a secco di default, `--applica` scrive) porta 6.4 e 7.2 IT/EN/DE/FR ai Corsi online, bump `v2.12 → v2.13` con changelog e hash ricalcolato, «Cosa è cambiato» nei 4 `legal.json`, `ACCADEMIA_UI_PRONTA = true`, e stampa i pin dei test da aggiornare. La guardia `test_accademia_ac4` verifica che le ancore esistano ancora e che a secco non cambi nulla.
- guardie: `tests/test_accademia_ac4.py`.

**RF Refinement olistico IMPLEMENTATO in locale (8/10/2026 notte, founder: «più visual e immediato»).**
- **Anteprima sempre nella copertina**: la pagina del corso parte già con il video (presentazione se c'è, altrimenti la prima lezione gratuita), con l'etichetta «Presentazione / Anteprima gratuita · titolo»; «Guarda gratis» cambia solo quale lezione gira («In riproduzione» su quella attiva). Niente più clic per vedere il video, niente «Chiudi».
- **Profilo a schede**: il catalogo (Servizi e prezzi · Esperienze · Prodotti · Corsi online) si sfoglia con una barra di pastiglie coi conteggi, sticky su telefono; le schede esistono solo per le categorie che l'operatore ha, con una sola categoria niente barra. L'hash sceglie la scheda (`#listino`, `#servizio-x`, `#prodotto-x`, `#corso-x`, `#ritiri`), così i deep link da landing ed email continuano a funzionare; le esperienze salgono nel catalogo prima della galleria (pin IG5 `hasUpcoming` intatto).
- **Account come hub**: l'orientamento è una **barra fissa in basso, su ogni schermo**, nel verde di marca con icone e testi nell'oro del marchio: sei voci (Esperienze · Corsi · File · Guide · Meditazioni · Account/Gestionale), lo stato sotto da tablet in su, la sezione in vista evidenziata, un tocco salta lì (founder 8/10 sera: le tessere in testa sono state tolte, «bianca non si nota» → verde + oro); la sezione Meditazioni esiste anche vuota, con l'invito; inizialmente sei tessere (Esperienze · Corsi · File · Guide · Meditazioni · Account/Gestionale) con lo stato in una riga («2 in programma», «Nessuno ancora», «Sbloccate»…) e il salto alla sezione; ogni sezione esiste anche vuota, con l'invito e la porta (`/esperienze`, `/corsi`, `/operatori`, `/newsletter`); larghezza 3xl, saluto col nome.
- **Categorie e directory `/corsi`**: `Course.categoria` = una famiglia del registro discipline (`famiglie_rosa`, validata: slug ignoto → 400), obbligatoria nel wizard, modificabile dalla scheda, etichetta in lista e sulla landing (link a `/corsi/{categoria}`); `GET /public/corsi` (org non campione con pagina online, Accademia non spenta, ≥1 lezione pronta) con filtri categoria · ricerca (titolo, descrizione, professionista) · ordine (recenti, prezzo, durata) · solo con anteprima, e i conteggi delle categorie prima del filtro; pagina `features/storefront/CorsiDirectoryPage.js` (testata, pastiglie, ricerca, griglia di card con copertina, professionista, lezioni · durata · accesso, prezzo, badge «Anteprima gratuita»; vuota: «I primi corsi stanno arrivando» → professionisti ed esperienze); rotte `/corsi`, `/corsi/:categoria` nel registro (pubblica) e in nginx; shell `_meta_corsi` (CollectionPage, noindex finché vuota, titolo con la categoria); sitemap `/corsi` quando c'è almeno un corso; voce «Corsi» nel menu pubblico SOLO allo sblocco (`ACCADEMIA_UI_PRONTA`).
- guardie: `tests/test_refinement_rf.py`; 467 test dei file toccati verdi.

**AU Lezioni audio e Aurya Sound IMPLEMENTATO in locale (8/10/2026 notte, founder: «combino video istruzioni sul respiro e tracce fatte con Aurya Sound»).** Tre tipi di lezione in più di video e testo, con le tre guardie chieste dal founder.
- **Lezione «Audio»** (mp3, m4a, wav, ogg, fino a 50 MB): storage PRIVATO su disco (`backend/private_uploads/lezioni/{org}/{corso}/{lezione}/`, mai sotto `uploads/`; `services/lezioni_file.py`), nomi su disco nostri, estensioni decise da noi, la durata la misura il browser prima di caricare, pronta subito (niente Bunny, niente coda). Conta nella quota video del piano. Lo studente la ascolta con un `<audio>` nativo: il play-url porta un **pass JWT a tempo (6 h) in query**, scoped a iscrizione e lezione, e la consegna ricontrolla l'iscrizione (una revoca chiude anche i pass già emessi); **Range (206) a mano** per il seek (lezione dei master del 26/8). Progresso ogni 15 s e fine come i video.
- **Lezione «Suono»** = una traccia Aurya Sound dell'operatore. Tre cerchi sul server: (1) solo col **privilegio del comporre** (`services/studio_access`: Pro o concessione; senza, il tipo non esiste e il server rifiuta), (2) **solo le proprie tracce** (`organization_id` dentro la query, bozze e pubblicate, mai la biblioteca né altre org: id altrui → 404), (3) **solo chi ha comprato ascolta** (play-url dell'iscrizione). Niente file: la lezione tiene `track_id` + snapshot del titolo; la ricetta viaggia al player (`payload_traccia`, stesso contratto di `/frequencies/public/{slug}`, mai l'org) e il motore la suona dal vivo (`SuonoPlayer` → `creaAscolto` delle esperienze integrate; **senza sipario né testi in più**, per scelta del founder dell'8/10: solo traccia, play, tempo e barra). Se l'operatore ritocca la traccia, la lezione segue; se la cancella, «traccia non più disponibile». Se perde Sound, le lezioni già vendute continuano a suonare.
- **Allegati per lezione** (pdf, office, testo, immagini, audio, zip; 20 MB, max 10): stesso storage privato, scaricabili dallo studente con un pass per allegato emesso dal dettaglio del corso; nel programma pubblico solo il conteggio.
- **Editor**: pulsanti Audio / Suono (Suono solo col privilegio) / Testo / Video; dropzone audio con barra; select delle proprie tracce (titolo · durata · bozza) con il rimando a Crea se non ce ne sono; «Aggiungi allegato» su ogni lezione. **Landing**: anteprima gratuita anche per audio e suono («Ascolta gratis»), icone per tipo, conteggio allegati. **Studente**: `AudioPlayer` / `SuonoPlayer` al posto dell'iframe, allegati in «Risorse».
- **Provato dal vivo** (API + browser, corso demo): wav caricato e pronto, riascolto 206, formato vietato 400, allegato, anteprima pubblica audio 206, play-url studente 206 e pass manomesso 401, traccia propria OK / id inventato 404, payload senza org; nel browser anteprima audio e suono in copertina, editor con Suono e allegati, player studente con audio che suona (currentTime avanza) e allegato in Risorse.
- guardie: `tests/test_accademia_au.py` (storage, pass, Range, guardie, player).

**Prossimo: il giro di deploy di AC1–AC4+RF+AU in ANTEPRIMA** (solo su go esplicito): backend + frontend + nginx rigenerato (`corso`, rimandi `co`/`courses`); il backend va ricreato per leggere `BUNNY_ACCOUNT_API_KEY`; in prod la UI resta chiusa (pilota admin@demo.com) finché il founder non dice di sbloccare → `scripts/sblocco_accademia_v213.py --applica` + pin + giro.

