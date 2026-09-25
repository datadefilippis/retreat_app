# Registrazione per vedere i contatti e per prenotare — analisi e piano

*25 settembre 2026, sera. Richiesta del founder: «per ottenere più iscritti alla newsletter, chi vuole vedere social, sito, email o numero di un operatore deve essere iscritto ad Aurya come utente; anche per prenotare; i dati poi precompilati nell'ordine; un meccanismo dove obblighiamo a registrarsi ed essere iscritti alla newsletter. Snello, senza sfasciare ciò che funziona.»*

## 0. Risposta breve

**Fattibile, con una correzione di rotta su una parola: «obbligare» vale per l'account, non per la newsletter.**

- **Account obbligatorio per prenotare e per vedere i contatti: sì.** È lecito, è normale nei marketplace, e i mattoni ci sono già (accesso senza password con codice a 6 cifre, prefill del checkout, sessione cliente).
- **Newsletter obbligatoria: no.** Un consenso dato perché altrimenti non puoi prenotare non è un consenso (GDPR art. 7.4). La nostra stessa informativa (§7-bis) promette che il Cerchio è «specifico, non preselezionato e revocabile». Se lo rendiamo una condizione, ogni iscritto raccolto così è contestabile e l'informativa va riscritta.
- **La via che porta più iscritti davvero:** la casella del Cerchio compare nel passaggio in cui la persona ha appena verificato l'email col codice. Non serve più il doppio opt-in: l'email è già provata, l'iscrizione è confermata all'istante (la strada `gia_verificato` esiste già). Casella separata, spenta, ma con il valore scritto accanto. È il punto di massima resa: la persona è dentro, ha fiducia, un clic e ha finito.

Stima onesta dell'effetto: oggi il collo di bottiglia non è la newsletter, è il volume (4 ordini in totale, 7 account, 41 iscritti). Il cancello sui contatti produrrà registrazioni subito, perché i contatti li cerca chi ha già deciso di scrivere. Il cancello sul checkout va fatto dopo, misurando: ogni passo in più prima di pagare costa conversione, e con 2 ordini al mese non possiamo permetterci di scoprirlo tardi.

## 1. Dove siamo (misurato in prod il 25/9)

| Cosa | Numero |
|---|---|
| Account cliente (platform_accounts) | 7, di cui 6 con email verificata |
| Iscritti al Cerchio | 41 (22 confermati, 19 in attesa del clic) |
| Ordini totali / ultimi 30 giorni | 4 / 2, tutti già legati a un account |
| Operatori che mostrano i contatti | 7 su 23 pubblicati |
| Operatori con almeno un social o sito | 27 (su 35 utenti operatore) |

**Cosa esiste già e si riusa senza toccarlo:**

1. **Accesso senza password** (`/platform/auth/magic-link` + `/platform/auth/code/verify`): email → codice a 6 cifre → sessione. Se l'email è nuova, l'account nasce da solo alla richiesta del codice e viene segnato verificato al primo uso. Zero password, venti secondi.
2. **AuryaQuickLogin** nel checkout: pannello inline «Hai un account? Entra col codice», al successo prefilla nome ed email. Oggi è facoltativo: chi non entra compra come ospite.
3. **Consensi sull'account**: chi ha l'account ha già accettato privacy e termini una volta; nel checkout le caselle legali spariscono (regola CG-4). Il consenso marketing resta una casella a parte.
4. **Il Cerchio con prova**: token firmato (5 anni) che il server verifica per i contenuti riservati; `iscrivi(..., gia_verificato=True)` conferma senza doppio opt-in quando l'email è già provata (E6, 24/9). Alla creazione dell'account c'è già `wants_newsletter` che chiama la stessa iscrizione.
5. **Profilo cliente** (`/platform/me`, PATCH): nome, telefono, lingua. Storico ordini e export GDPR già pronti.
6. **Claim degli ordini**: gli ordini ospite vengono agganciati all'account via email. Con l'account obbligatorio non serve più.

## 2. Le tre regole che non si negoziano

1. **Newsletter mai condizione.** Casella separata, spenta, testo cerchio-v3, un clic per uscire. Chi non la spunta prenota lo stesso. (GDPR 7.4, considerando 43; informativa Aurya §7-bis e §4.1.)
2. **SEO intatta.** Google deve vedere ciò che vede una persona. Se i contatti si vedono solo da loggati, il telefono esce anche dal JSON-LD LocalBusiness (oggi c'è): tenerlo nascosto agli umani e visibile a Google è cloaking di dati strutturati. Costo SEO: modesto (il posizionamento locale viene da nome, luogo, geo, recensioni, contenuti; il telefono nello schema serve ai rich result, non alla classifica). Tutto il resto resta com'è: pagine, sitemap, robots con `Allow: /api/public/`, fetcher AI.
3. **La pagina link (/@slug) non si tocca.** È la bio Instagram dell'operatore: chi arriva da lì è già suo pubblico. Metterle un cancello sarebbe un torto all'operatore. Vale anche per i suoi social dentro quella pagina.

## 3. Il disegno: «una porta, tre usi»

Un solo componente, **PortaAurya**: email → codice a 6 cifre → sessione cliente. Nasce da AuryaQuickLogin, oggi chiuso nel checkout, e si monta in tre posti.

### 3.1 Contatti e canali dell'operatore (profilo /o/ e scheda «Chi siamo» dello store)

- Il JSON del profilo dice solo cosa c'è: `contacts = {has_phone, has_email, has_socials, has_website}`. Niente valori.
- Il riquadro «Contatti» mostra: «Telefono, email, Instagram e sito: entra con la tua email per vederli. Venti secondi, nessuna password.» Sotto, PortaAurya inline. Chi ha già la sessione vede tutto subito.
- La rotta `GET /public/operator/{slug}/contatti` (già in prod dal giro anti-scrape, oggi aperta con limite) richiede il bearer cliente e risponde con telefono, email, social, sito. Limite 30 al minuto per account.
- **Il dato in più che vale per l'operatore:** ogni apertura scrive un evento `richiesta_contatto {account, org, quando, da dove}`. L'operatore vede nel gestionale «12 persone hanno chiesto i tuoi contatti» con nome ed email (è un lead, il motivo per cui è su Aurya). La persona lo sa prima di aprire: una riga «l'operatore vedrà che hai chiesto i suoi contatti» (trasparenza, informativa §2.2).
- JSON-LD: via `telephone` (vedi regola 2). Resta tutto il resto del LocalBusiness.

### 3.2 Prenotazione con account (checkout)

- Il passo «I tuoi dati» del checkout diventa PortaAurya se non c'è sessione: email → codice → dentro. Nome, email e telefono si prefillano dall'account; ciò che manca (telefono, nome) si chiede una volta e si salva sull'account (PATCH /platform/me).
- Le caselle legali seguono la regola di oggi: sparite per chi ha l'account (accettate alla creazione), quindi il checkout si accorcia, non si allunga.
- La strada ospite si spegne dietro un interruttore (`CHECKOUT_RICHIEDE_ACCOUNT`), acceso in prod solo dopo una settimana di misura del 3.1. Se l'interruttore è spento nulla cambia rispetto a oggi.
- Ordini sempre con `customer_id`: la claim email diventa inutile.

### 3.3 La casella del Cerchio, nel momento giusto

Subito dopo il codice verificato (in 3.1 e 3.2), una riga sola:

> ☐ Sì, mandami la Lettera del Cerchio di Aurya (meditazioni, guide, ritiri). Ti cancelli con un clic.
> *Con la Lettera ascolti le meditazioni complete e ricevi i ritiri in anteprima.*

- Spenta di default, testo cerchio-v3 (lo stesso di tutte le porte, versionato).
- Se spuntata: `iscrivi(gia_verificato=True)` → stato `confirmed` all'istante, prova del Cerchio salvata nel browser (le meditazioni si sbloccano nello stesso momento), provenienza `canale=account, superficie=contatti|checkout`, consenso registrato con versione, IP e pagina come oggi.
- Se già nel Cerchio: la riga non compare («Sei nel Cerchio ✓»).
- Chi non spunta: nessuna email marketing. Riceve solo le email transazionali dell'ordine.

### 3.4 Dati che si raccolgono (tutti dichiarati)

Account: email (verificata), nome, telefono, lingua. Facoltativi, chiesti una volta e mai bloccanti: città e, se spunta il Cerchio, il blocco «Avvisami sui ritiri» (vie, dove, budget) che già esiste. Eventi: richieste di contatto, ordini. Tutto visibile in regia (Cerchio → iscritti con provenienza `account`; Operatori → «lead dai contatti»).

## 4. Piano a lotti (piccoli, isolati, ognuno con interruttore e guardia)

| Lotto | Cosa | Tocca | Rischio | Stima |
|---|---|---|---|---|
| **R1 Porta unica** | `PortaAurya` estratto da AuryaQuickLogin (email → codice → sessione, casella Cerchio con `gia_verificato`, prefill), profilo account con città | frontend storefront, `platform_accounts` (patch profilo), `subscribers.iscrivi` | basso: componente nuovo, nulla cambia finché non lo si monta | 1 giorno |
| **R2 Contatti dietro la porta** | flag nel JSON, `/contatti` con bearer + evento `richiesta_contatto`, riquadro nuovo su /o/ e StoreAbout, via `telephone` dal JSON-LD, lead nel gestionale operatore | `public.py`, `seo_shell.py`, OperatorProfilePage, StoreAbout, una tab/card in dashboard | medio-basso: interruttore `CONTATTI_DIETRO_PORTA` (spento = oggi) | 1 giorno |
| **R3 Checkout con account** | PortaAurya obbligatoria al passo dati, prefill telefono, salvataggio sull'account, ospite dietro `CHECKOUT_RICHIEDE_ACCOUNT` | CheckoutForm, useCheckoutForm, `/order-request` (customer_id obbligatorio se flag) | medio: è il checkout; si accende dopo la misura di R2 | 1 giorno |
| **R4 Misura e regia** | contatori in system admin (account creati, richieste contatto, ordini con account, iscritti da account), provenienza `account` nella tab Cerchio | admin | basso | mezza giornata |
| **R5 Legale** | informativa v2.8: account necessario per prenotare, richiesta di contatto condivisa con l'operatore, Cerchio sempre facoltativo; termini allineati | `backend/legal/*`, versione legale | basso, ma va fatto PRIMA di accendere R2 in prod | mezza giornata |

Ordine: **R1 → R5 → R2 (acceso) → R4 → una settimana di numeri → R3.**

Verifiche per ogni lotto: guardie sui letterali (come sempre), prova dal vivo sull'org demo, prova nel browser da visitatore, suite completa sulla baseline, deploy con interruttore spento e accensione da `.env.production`.

## 5. Cosa può rompersi, e come si evita

- **Il checkout inline dal profilo e dalle landing ritiro** (PN/PP): stesso `CheckoutForm`, quindi R3 li copre tutti con un solo interruttore; le guardie del checkout (`test_ap*`, `test_checkout_*`) vanno aggiornate al passo nuovo.
- **AuryaQuickLogin oggi non tocca i consensi** (CG-4): in R3 la persona con account non vede le caselle legali, come già oggi; chi crea l'account dal checkout le accetta lì, una volta.
- **Codici a raffica**: `/platform/auth/magic-link` ha già rate limit e honeypot; il cancello contatti lo esporrà di più → limite per IP a 5 richieste/10 minuti (nginx zone signup già esiste).
- **Google e i fetcher AI**: nessun cambio a robots, sitemap, shell; solo `telephone` sparisce dal LocalBusiness. Da verificare in Search Console la settimana dopo.
- **Operatori**: comunicare la novità come «da oggi vedi chi chiede i tuoi contatti». Chi ha `show_contacts` acceso continua a mostrarli, solo a persone identificate.
- **Utenti già nel Cerchio senza account**: alla porta, se l'email è già confermata nel Cerchio, il codice la lega all'account e la casella non compare.

## 6. Cosa non fare

- Casella del Cerchio preselezionata, o «iscrivendoti accetti la newsletter»: consenso non valido, e l'informativa dice il contrario.
- Cancello sulla pagina link /@slug o sull'anteprima dei ritiri: taglia il traffico che gli operatori portano da soli.
- Nascondere i contatti agli umani lasciandoli nello schema per Google.
- Password obbligatoria: il codice a 6 cifre basta; la password resta un'opzione per chi la vuole (già così).
- Accendere R3 prima di aver visto una settimana di R2.

## 7. Decisioni che servono dal founder

1. Contatti dietro la porta: **tutti** (telefono, email, social, sito) o solo telefono ed email? Consiglio tutti: è ciò che genera il lead per l'operatore.
2. Via il telefono dal JSON-LD (coerenza con quanto vede la persona): sì/no. Consiglio sì.
3. Ordine dei lotti come sopra (contatti prima, checkout dopo una settimana di numeri): ok?
4. Il lead all'operatore (nome ed email di chi apre i contatti): sì/no. Consiglio sì, dichiarato all'utente.
