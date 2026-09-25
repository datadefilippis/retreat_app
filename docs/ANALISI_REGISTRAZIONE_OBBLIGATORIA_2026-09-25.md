# Account per vedere i contatti e per ordinare — analisi e piano (v2)

*25 settembre 2026, sera. Richiesta del founder: chi vuole vedere social, sito, email o telefono di un operatore deve avere un account Aurya; per ordinare l'account diventa obbligatorio e i dati si precompilano; più iscritti al Cerchio. Vincoli: snello, senza regressioni su newsletter, creazione account e creazione ordini, solido e scalabile.*

*v2: riscritto dopo la lettura integrale dei tre flussi (ordine, account, Cerchio). Sostituisce la v1 dello stesso giorno.*

---

## 0. Le decisioni, in chiaro

| Domanda | Risposta del piano |
|---|---|
| Contatti (telefono, email, Instagram, Facebook, sito) sul profilo `/o/` e nella scheda dello store | **Visibili solo con account Aurya.** Chi non ce l'ha lo crea sul posto: nome, email, password, fatto (il codice a 6 cifre resta solo per entrare senza password). |
| Pagina link `/@slug` (bio Instagram dell'operatore) | **Invariata.** È traffico che porta l'operatore da solo. |
| Ordinare (profilo, store, landing ritiro) | **Account obbligatorio.** Stessa porta, stessa password. Chi ha già la sessione salta il passo. La strada ospite si spegne con un interruttore, solo quando i numeri del cancello contatti dicono che la porta funziona. |
| Newsletter (il Cerchio) | **Mai condizione.** Casella separata, spenta, nella creazione dell'account; l'iscrizione si conferma da sola nel momento in cui l'email viene provata (link di verifica o codice), senza un secondo clic. È il punto di massima resa, ed è l'unico modo lecito. |
| Widget embed sui siti degli operatori | **Invariati.** Sono clienti dell'operatore sul suo sito: nessun account Aurya lì. |
| SEO | **Invariata**, con una sola conseguenza: il telefono esce dal JSON-LD LocalBusiness, perché Google non deve vedere ciò che una persona non vede. Costo modesto e spiegato al §6. |

**Perché la newsletter non può essere obbligatoria.** GDPR art. 7.4 e considerando 43: un consenso dato perché altrimenti non ottieni il servizio non è libero. La nostra informativa (§7-bis) dichiara il Cerchio «specifico, non preselezionato e revocabile». Ogni iscritto raccolto per obbligo sarebbe contestabile e l'informativa andrebbe riscritta al contrario. L'account invece è una necessità del servizio (art. 6.1.b) e non ha bisogno di consenso.

---

## 1. Come funziona oggi (letto nel codice, misurato in prod il 25/9)

### 1.1 Numeri

| Cosa | Prod |
|---|---|
| Account Aurya (`platform_accounts`) | 7, 6 verificati, 4 col timbro legale, **0 col telefono** |
| Iscritti al Cerchio | 41 (22 confermati, 19 in attesa del clic) |
| Ordini | 4 in tutto, 2 negli ultimi 30 giorni, **tutti già con `platform_account_id`** (agganciati dopo, per email) |
| Account per-store (`customer_accounts`, sistema legacy) | **0** |
| Operatori con contatti mostrati / con social o sito | 7 / 27 |

### 1.2 Tre sistemi di identità, uno solo vivo

1. **Account Aurya** (`platform_accounts`, token `type=platform`, client `platformApi`): email + codice a 6 cifre (`/platform/auth/magic-link` → `/platform/auth/code/verify`), oppure password. Il codice **crea l'account da solo** se l'email è nuova, **ma solo se la richiesta porta `accepted_terms=True`** (AP-L: nessun account nasce senza timbro legale, fonte `signup_passwordless`). Il pannello inline del checkout (`AuryaQuickLogin`) oggi **non** manda quel flag: fa entrare chi ha già l'account, non crea.
2. **Account per-store** (`customer_accounts`, `customerApi`, registrazione con password dal checkout, `wantRegister`): eredità ecommerce, obbligatorio solo per i corsi. In prod non esiste nessuno. È l'unica identità che `/public/order-request` legge dal Bearer.
3. **Cliente CRM** (`customers`, per org): nasce a ogni ordine da nome+email, senza login.

**Conseguenza importante per il piano:** oggi l'ordine **non** viaggia con l'account Aurya. `/public/order-request` accetta solo il token per-store; l'account Aurya viene timbrato sull'ordine *dopo*, per email (`retroactive_claim` al login, o email di claim). Per rendere l'account obbligatorio all'ordine, l'ordine deve nascere già con `platform_account_id`, dal token, con l'email del token come email del cliente.

### 1.3 Checkout

- Un solo `CheckoutForm` + `useCheckoutForm` + `useCheckoutSubmit`, montati da StorefrontPage, OperatorProfilePage (checkout inline dal listino), InlineServiceCheckout, InlineEventCheckout, EventLandingPage. **Una modifica li copre tutti.**
- Legale a due livelli (AP-L/CG-4): con sessione Aurya la casella «Accetto Termini e Privacy di Aurya» non compare (accettata alla creazione dell'account); la casella dell'operatore compare solo se ha pubblicato le sue condizioni.
- Casella del Cerchio già presente (`cerchio_optin`, Lotto E del 24/9): dopo l'ordine `order_creation_service` iscrive l'email **in doppio opt-in**, perché l'email dell'ordine non è provata.
- Pagamento: `payment_checkout_url` (Stripe) o richiesta/approvazione, deciso dal backend. Non si tocca.

### 1.4 Contatti

- Profilo JSON: `contacts = {public_phone, has_email}` (dal giro anti-scrape di oggi); email al clic da `/public/operator/{slug}/contatti` (10/min, aperta). Social e sito in chiaro nel JSON (`socials`). JSON-LD con `telephone`.
- Pagine: `OperatorProfilePage` (riquadro «Contatti» + riga social), `StoreAbout` (store), `LinkPage` (`/@slug`, resta libera).

### 1.5 Difese già in piedi

Rate limit su codice (5/min) e verifica (10/min), honeypot, limiti per IP ora non aggirabili (AS1), consensi versionati e audit immutabile (`aurya_legal`, registro consensi), Cerchio con prova firmata e verifica «per uso».

---

## 2. Il disegno: una porta, tre usi

*Aggiornato dopo la decisione del founder (25/9 sera): l'account si crea con una password, mai senza.*

**`PortaAurya`** (componente unico, in `features/account`): due viste.

- **Entra**: email + password (`/platform/auth/login`). Sotto: «Non hai un account? Crealo», «Accedi senza password» (il codice a 6 cifre resta come ripiego: magic-link + code/verify) e «Password dimenticata?» (la vista `recupero` di `/accedi`).
- **Crea**: nome, email, password con le quattro regole di `/accedi` (12 caratteri, minuscola, maiuscola, numero), la casella legale obbligatoria «Accetto i Termini e la Privacy di Aurya» (`accepted_terms`, senza la quale il server risponde 400) e, separata e spenta, **la riga del Cerchio** col testo unico e versionato (cerchio-v3) e sotto «Con la Lettera ascolti le meditazioni complete e ricevi i ritiri in anteprima». → `/platform/auth/signup` con `wants_newsletter` e `consenso_versione`.

Il momento della verifica. Con password, l'email si prova al clic sul link di verifica (non al codice). Due comportamenti, decisi dall'interruttore `LOGIN_SENZA_VERIFICA` (E6, lo stesso già deciso per gli operatori):

- **acceso**: il signup risponde già con la sessione; la porta si chiude e si prosegue (contatti o ordine); l'email si prova «per uso» al primo clic su un nostro link (verifica, ordine, Lettera). L'export GDPR resta rigido.
- **spento** (oggi): «Ti abbiamo scritto: apri l'email e conferma. Poi entra con la tua password».

In entrambi i casi, quando l'email viene provata (link di verifica, codice, magic link) l'iscrizione al Cerchio chiesta nella riga passa da «in attesa» a **confermata** nello stesso istante (`segna_verificato`, tipo «account»): nessun secondo clic, nessuna email di conferma in più. Chi non spunta la riga non riceve nulla di marketing.

Con sessione già aperta la porta non si vede: nome, email e telefono si prefillano dall'account (`/platform/me`, che ora porta anche `city`).

Usi: **U1** riquadro contatti, **U2** passo «I tuoi dati» del checkout, **U3** (già oggi) accesso da `/accedi`.

---

## 3. Lotti

Ogni lotto: interruttore in `.env` (spento = comportamento di oggi, byte per byte), guardia con letterali, prova dal vivo sull'org demo, prova nel browser da visitatore, suite completa sulla baseline, deploy con interruttore spento, accensione a parte.

### R1 · La porta unica (FATTO il 25/9 sera, in locale)

**Backend**
- `services/platform_account_service`: `_conferma_cerchio_per_uso(email, dettaglio)` chiamata dove l'email viene provata (verify-email, codice, magic link) → il Cerchio in attesa si conferma (tipo «account»); `password_login` accetta gli account non verificati solo con `LOGIN_SENZA_VERIFICA` acceso.
- `auth.get_current_platform_account`: sessione valida prima della verifica solo col flag; `get_current_platform_account_strict` per `/me/export`.
- `POST /platform/auth/signup`: col flag acceso risponde con `access_token` + `verifica_morbida: true` nella stessa 202; spento, come prima.
- `PATCH /me` e `GET /me`: `city`.

**Frontend**
- `features/account/PortaAurya.jsx` (viste entra/codice/crea/inviata, mai un submit del form padre).
- `AuryaQuickLogin`: «Hai già un account Aurya? Accedi · Non ce l'hai? Crealo» — la creazione con password vive nel pannello del checkout, la sessione e il prefill sono gli stessi di prima.

**Guardia**: `test_porta_aurya_r1.py` (letterali, flag spento di default, signup dal vivo con Cerchio in attesa e login rigido, verifica che conferma il Cerchio sul db locale).

### R5 · Legale (prima di accendere R2)

Informativa v2.8 e Termini: account necessario per vedere i contatti e per ordinare; la richiesta di contatto è comunicata all'operatore (nome ed email, base: esecuzione del servizio richiesto dall'utente, art. 6.1.b); il Cerchio resta facoltativo e separato; conservazione delle richieste di contatto (12 mesi). Versione legale nuova → re-consent operatori come da meccanismo esistente; per i clienti Aurya il timbro `aurya_legal` porta la versione e la modale di ri-accettazione già gestisce i bump. **Stima**: mezza giornata. **Guardie**: `test_legal_*` sulla versione.

### R2 · Contatti dietro la porta (interruttore `CONTATTI_DIETRO_PORTA`)

**Backend**
- `GET /public/operator/{slug}`: con interruttore acceso, `contacts` e `socials` diventano **flag**: `{has_phone, has_email, has_instagram, has_facebook, has_website}`; niente valori. Spento: come oggi.
- `GET /public/operator/{slug}/contatti`: con interruttore acceso richiede Bearer `type=platform` (401 altrimenti), risponde con telefono, email, instagram, facebook, sito (solo quelli che l'operatore ha scelto di mostrare: `show_contacts` per telefono/email; i social sono pubblici per scelta sua). Limite 30/min per account, 10/min per IP resta.
- **Evento `richiesta_contatto`**: collezione `contact_requests {id, org_id, platform_account_id, email, nome, quando, da (o|store), ip}`; indice `(org_id, quando)` e unico su `(org_id, platform_account_id, giorno)` (una riga al giorno per persona, non una per clic). Scritta in background, mai bloccante.
- `GET /organizations/current/contact-requests` per l'operatore (ultimi 90 giorni, conteggio + lista).
- `seo_shell`: via `telephone` dal LocalBusiness quando l'interruttore è acceso.

**Frontend**
- Riquadro «Contatti e canali» (`ContattiOperatore.jsx`, usato da OperatorProfilePage e StoreAbout): con sessione → chiama `/contatti` e mostra tutto; senza → testo «Telefono, email e social: entra con la tua email per vederli. Venti secondi, senza password. L'operatore vedrà che hai chiesto i suoi contatti.» + `PortaAurya` inline → al successo carica e mostra. Interruttore spento → il riquadro di oggi.
- Gestionale operatore: card «Chi ha chiesto i tuoi contatti» nella pagina Clienti (`customers-mgmt`), con nome, email, data. È il motivo per cui l'operatore accetta il cancello.
- `LinkPage` (`/@slug`): non tocca nulla.

**Guardie**: `test_contatti_porta_r2.py` (flag nel JSON, 401 senza token, evento scritto una volta al giorno, LinkPage senza `/contatti`, JSON-LD senza telephone con flag acceso e CON telephone spento, `MostraEmail` sostituito). Suite: `test_anti_scrape_as`, `test_reviews_*`, `test_seo_shell`, `test_anima_an`, `test_sedi_sd`, `test_llm_lx`.

**Rischi e mitigazioni**: cache 45 s del profilo pubblico (il JSON dei flag è cacheabile: nessun dato personale); Googlebot vede i flag e non i valori, coerente con l'HTML; operatori: email «da oggi vedi chi chiede i tuoi contatti» (una riga nella Lettera degli operatori, non un giro nuovo). **Stima**: 1 giorno.

### R4 · Misura e regia

System admin → Cerchio: provenienza `account` nei conteggi e nelle vie. Operatori: colonna «richieste contatto (30 gg)». Dashboard: account creati per giorno, richieste di contatto, ordini con account, iscritti da account. Un solo endpoint `GET /admin/funnel` che legge le collezioni esistenti (nessuna scrittura). **Stima**: mezza giornata. **Guardie**: `test_regia_funnel_r4.py`.

### Una settimana di numeri, poi:

### R3 · Ordinare con l'account (interruttore `CHECKOUT_RICHIEDE_ACCOUNT`)

**Backend**
- `/public/order-request`: accetta anche il Bearer `type=platform` (oggi solo `customer`). Con token platform: `platform_account_id` sull'ordine **alla nascita**, `customer_email` = email dell'account (il corpo non può dirne un'altra), nome/telefono dal corpo se presenti, altrimenti dall'account; il cliente CRM nasce o si aggancia come oggi (`_find_or_create_customer` con l'account). Con interruttore acceso e senza token platform → 401 con codice `account_richiesto` (il frontend lo traduce nella porta). Il percorso embed (`embed_public`) **non passa da qui** e resta ospite.
- `cerchio_optin` al checkout con token platform → `iscrivi(gia_verificato=True)` (oggi doppio opt-in). Senza token, come oggi.
- Dopo l'ordine: telefono del corpo salvato sull'account se l'account non ce l'ha (una volta, mai sovrascritto).
- `retroactive_claim` e claim email restano per gli ordini vecchi; per i nuovi non scattano (già agganciati).

**Frontend**
- `useCheckoutForm`: con interruttore acceso, il passo «I tuoi dati» è `PortaAurya` finché non c'è sessione; poi nome/email/telefono prefillati (email non modificabile), casella Aurya assente (regola AP-L di oggi), casella operatore come oggi, casella Cerchio come oggi ma con la nota «confermata subito». `useCheckoutSubmit`: manda il token platform (header `Authorization` se non c'è quello per-store). `wantRegister` (account per-store con password) sparisce dalla UI quando l'interruttore è acceso; resta per i corsi finché esistono.
- Success page e email d'ordine invariate; `/account` mostra l'ordine subito (già legge `platform_account_id`).

**Guardie**: `test_checkout_account_r3.py` (401 `account_richiesto` con flag; ordine con `platform_account_id` alla nascita; email del token vince; embed ospite intatto; `gia_verificato` solo con token; flag spento = payload byte-identico a oggi). Suite: `test_checkout_*`, `test_invariants_embed_checkout`, `test_invariants_embed_auth_checkout`, `test_listino_tw` (AP1-AP5, PN, LM), `test_payment_*`, `test_r1_checkout_lines`, `test_wave_gdpr_commerce_CG*`, e2e in `tests/e2e_*.py`.

**Rischi e mitigazioni**: è il checkout → interruttore spento al deploy, prova generale sulla copia di prod (dump → restore → backend :8001 → ordine di prova con token), accensione in un momento di traffico basso, rollback = spegnere il flag (nessuna migrazione dati). Conversione: il passo in più è un codice via email; si misura con R4 prima e dopo (ordini iniziati / completati). **Stima**: 1 giorno + mezza di prova generale.

---

## 4. Ordine, tempi, punti di ritorno

`R1 (1 g) → R5 (½ g) → R2 acceso (1 g) → R4 (½ g) → 7 giorni di misura → R3 spento (1½ g) → acceso.` Totale lavoro: circa 4 giorni e mezzo, distribuiti su due settimane per via della misura.

Punti di ritorno: ogni interruttore si spegne da `.env.production` con un riavvio del backend (10 secondi) e riporta al comportamento di oggi. Nessuna migrazione irreversibile: la collezione nuova è additiva, i campi nuovi sull'account sono opzionali, gli ordini vecchi non si toccano.

---

## 5. Cosa NON cambia (elenco di controllo per le regressioni)

- `/public/newsletter/subscribe` e tutte le porte del Cerchio (home, landing, meditazioni, cancello traccia, Magazine, checkout): stesso testo, stessa versione, stesso doppio opt-in dove l'email non è provata.
- Signup con password, magic link da `/accedi`, `/account`, export GDPR, cancellazione account.
- Embed (widget sui siti degli operatori): identità per-store o ospite, come oggi.
- Ordini manuali, Stripe, webhook, numeri d'ordine, email transazionali, claim degli ordini vecchi.
- Pagina link `/@slug`, directory `/operatori`, pagine locali, sitemap, robots, shell SEO (tranne `telephone`), fetcher AI, llms.txt.
- Recensioni (OTP proprio, non tocca la porta).

---

## 6. SEO: cosa costa davvero

Il solo cambio è `telephone` fuori dal LocalBusiness. Google usa il numero nello schema per i rich result locali, non per la classifica; la scheda locale vera è Google Business Profile dell'operatore, che Aurya non gestisce. Nome, indirizzo, geo, recensioni (`aggregateRating`), discipline, bio, intervista, listino (`OfferCatalog`) restano tutti. Se tra 30 giorni Search Console mostrasse un calo sulle query locali col nome dell'operatore, la mossa di ritorno è una riga (il telefono torna nello schema e resta dietro la porta per gli umani: accettato da Google come «click to reveal» se il numero compare dopo un'azione dell'utente sulla pagina).

---

## 7. Cosa non fare

- Casella del Cerchio preselezionata o inglobata nell'accettazione legale.
- Cancello sulla pagina link, sulla directory o sull'anteprima dei ritiri.
- Password obbligatoria (il codice basta; la password resta opzionale).
- Accendere R3 prima dei numeri di R2.
- Toccare l'embed.
