# Meta Pixel e Conversions API — piano MP

*5 ottobre 2026. Il founder fa sponsorizzate Facebook/Instagram verso la landing del Cerchio e vuole: dati veri sulle inserzioni per ottimizzare la spesa, far sapere a Meta i contatti effettivi, misurare sia gli iscritti al Cerchio sia le registrazioni degli operatori. Vincolo: zero regressioni sulle porte che oggi funzionano e sono sponsorizzate.*

## 0. Principi

1. **Il nostro registro è la verità, Meta è lo strumento di ottimizzazione.** Ogni iscritto e ogni operatore portano già (o porteranno) provenienza, campagna e inserzione nel nostro database: lì si legge il costo per contatto vero, confermato o no. A Meta mandiamo gli eventi perché le sue inserzioni imparino su chi si iscrive davvero.
2. **Niente parte senza consenso.** Il pixel si carica solo se la persona accetta la categoria «marketing» nel banner; gli eventi dal server partono solo per chi l'ha accettata. Oggi informativa e banner promettono «nessun cookie pubblicitario, mai» e «niente Facebook Pixel»: si cambia la promessa prima del codice, non dopo.
3. **Un evento, un identificativo, due strade.** Browser e server mandano lo stesso evento con lo stesso `event_id`: Meta lo conta una volta, e quando il browser è bloccato (iOS, adblock) il server lo porta comunque.
4. **Tutto spegnibile da una variabile.** Senza `META_PIXEL_ID` il sito è identico a oggi, byte per byte.
5. **Il server non aspetta Meta.** Gli invii sono in coda, con timeout e tentativi, mai dentro una risposta all'utente.

## 1. Da dove partiamo (fatti verificati)

| Punto | Stato |
|---|---|
| Pixel / dataset | «Aurya website», ID 1093685309713150, creato; corrispondenza avanzata automatica spenta |
| Token Conversions API | generato, provato sull'endpoint eventi, salvato in `.env.production` (root, 600), mai nel codice |
| Dominio | `aurya.life` verificato via TXT su Cloudflare |
| Analytics oggi | GA4 con Consent Mode v2, ID da `/public/site-config` (runtime), page_view sui cambi rotta, eventi `generate_lead`, `porta`, `first_service_online`, `lead_magnet_download` |
| Banner cookie | una sola scelta (statistiche sì/no), chiavi `afianco_cookie_disclosure_v1` e `aurya_analytics_consent_v1`; testo: «Nessun cookie pubblicitario, mai» |
| Informativa §15 | nomina GA4 e dice esplicitamente «non Facebook Pixel» |
| Provenienza iscritti | url, referrer, utm source/medium/campaign, dispositivo: ottimo, ma le inserzioni finora non avevano UTM (15 iscritti da Facebook con utm vuoti) |
| Provenienza operatori | nessuna: la registrazione non salva né referrer né UTM |
| Account cliente | nessuna provenienza |

## 2. Architettura

```
 Browser                                   Server
 ───────                                   ──────
 banner v3 ──consenso {stat, mkt}──►  salvato con l'iscrizione / registrazione
      │                                      │
 lib/meta.js (solo se mkt)                   services/meta_capi.py (solo se mkt)
   PageView, Lead, CompleteRegistration,       stesso event_id, email in hash,
   Contact, Purchase  + eventID ──────┐        fbp/fbc, ip, user-agent,
                                      │        event_source_url, test_event_code
                                      ▼                   │
                              Meta deduplica ◄────────────┘
                                                          │
                                           registro tracciamento_eventi (90 gg)
                                                          │
                                           regia: campagne, stato Meta, lunedì
```

### 2.1 Browser: `lib/meta.js`
- `initMeta(pixelId)` chiamato da App insieme a `initAnalytics`, con l'ID da `site-config` (`META_PIXEL_ID`, come `GA_MEASUREMENT_ID`). Non carica nulla finché il consenso marketing non è vero: lo script `fbevents.js` si inietta **solo** al consenso, e prima non parte nessuna richiesta verso Meta.
- `fbq('consent', 'revoke')` di default, `grant` al consenso; PageView a ogni cambio rotta (come GA).
- Funzioni no-op senza consenso: `metaLead({eventID, porta, superficie})`, `metaCompleteRegistration({eventID, tipo: 'operatore'|'account'})`, `metaContact({eventID})`, `metaPurchase({eventID, value, currency})`.
- `idEvento()` genera un uuid che il form manda anche al server.
- `datiTracciamento()` legge i cookie `_fbp` e `_fbc` e il parametro `fbclid` dall'URL: viaggiano nel payload solo con consenso marketing.

### 2.2 Server: `services/meta_capi.py`
- `invia(evento, email, event_id, url, ip, user_agent, fbp, fbc, custom)`: costruisce il payload della Conversions API (`action_source=website`, `event_time`, `user_data` con `em` in SHA-256 dell'email normalizzata, `client_ip_address`, `client_user_agent`, `fbp`, `fbc`; `custom_data` con porta, superficie, campagna). Firma una sola funzione, un solo posto.
- Esecuzione in **task di background** (lo stesso schema di `_dopo_iscrizione`): timeout 5 s, 3 tentativi con attesa crescente, mai un'eccezione verso l'alto, mai dentro la risposta HTTP.
- `META_TEST_EVENT_CODE` in env: se presente, gli eventi vanno nella scheda «Testa gli eventi» di Meta e non nei dati veri. È così che si prova in locale e in prod prima di accendere.
- Ogni invio scrive una riga in `tracciamento_eventi`: evento, event_id, canale (browser non lo sappiamo, server sì), esito, `events_received` di Meta, errore; indice TTL 90 giorni. Nessuna email in chiaro: solo l'hash.
- Guard-rail: niente token nel log, niente payload nel log in caso di errore oltre al codice e al messaggio di Meta.

### 2.3 Consenso: banner v3
- Tre scelte, come vuole il Garante: **Solo essenziali**, **Statistiche**, **Accetta tutto** (statistiche + marketing). Testo nuovo: «Usiamo cookie tecnici e, solo se accetti, Google Analytics per capire come viene usato il sito e Meta per misurare le nostre inserzioni. Puoi scegliere.»
- Stato salvato in `aurya_consent_v3 = {analytics, marketing, at, versione_testo}`; il banner ricompare **una volta** a chi aveva già scelto con la versione precedente, perché le categorie sono cambiate. Chi aveva accettato le statistiche le ritrova preselezionate nel senso del bottone, non si perde nulla.
- `lib/consenso.js` espone `consensoMarketing()` e `consensoStatistiche()` letti da GA e da Meta: un solo punto di verità.
- Il valore `marketing` viaggia con ogni iscrizione, registrazione e richiesta contatti e si salva nel documento (`provenienza.tracciamento.marketing`), così il server sa a chi può mandare eventi anche giorni dopo (conferma, acquisto).

### 2.4 Provenienza estesa, anche per gli operatori
- `pulisci_utm` accetta anche `content` e `term`; si salvano `fbclid` e `gclid` quando presenti. Così in regia si distingue l'inserzione, non solo la campagna.
- **Registrazione operatore** (`/accedi?vista=crea` professionista e `/entra-nella-rete`): il form manda `provenienzaCorrente()` come già fa il Cerchio; il backend la salva su `organizations.provenienza` con lo stesso `classifica()`. La regia Operatori mostra «Provenienza» e il lunedì conta gli operatori per canale.
- **Account cliente** (PortaAurya): idem su `platform_accounts.provenienza`.

## 3. Gli eventi, e perché proprio questi

| Evento Meta | Quando | Browser | Server | Dati utili |
|---|---|---|---|---|
| `PageView` | ogni rotta | sì | no | — |
| `Lead` | iscrizione al Cerchio riuscita (tutte le porte: cerca-ritiro, home, blog, cancelli, recensione, account) | sì | sì | porta, superficie, campagna |
| `LeadConfermato` (custom) | primo clic verificante o conferma | no | sì | segnale di qualità per Meta: un Lead che apre |
| `CompleteRegistration` | registrazione operatore riuscita; creazione account cliente | sì | sì | `content_name`: operatore / account |
| `Contact` | sblocco dei contatti di un operatore (porta) | sì | sì | slug operatore |
| `Purchase` | ordine pagato (webhook Stripe) e pagina di grazie | sì | sì | valore, valuta, tipo |

Regole: Lead e CompleteRegistration sono le conversioni delle due campagne (Cerchio, Professionisti); Contact e Purchase servono alle campagne future e al retargeting; `LeadConfermato` è l'evento che distingue Aurya: Meta impara sugli iscritti vivi. In «Misurazione eventi aggregata» l'ordine di priorità sarà Lead, CompleteRegistration, Purchase, Contact.

## 4. Regia: leggere i soldi spesi

- **Iscritti**: filtri `campagna` e `inserzione` (utm_campaign, utm_content), ripartizione «Per campagna» con tre numeri per riga: iscritti, confermati, percentuale. Scheda della persona: UTM completi e `fbclid` presente sì/no.
- **Operatori**: colonna «Provenienza» (canale › superficie, campagna) e filtro.
- **Numeri del lunedì**: blocco «Campagne, 30 giorni»: per campagna iscritti/confermati/operatori; blocco «Meta»: eventi inviati e accettati nelle ultime 24 ore, errori, ultimo invio. Se gli invii falliscono si vede lì, non tra sei mesi.
- Una pagina `/admin/tecnico` già esiste: ci va il semaforo «Pixel: acceso/spento, token valido (ultimo invio ok alle hh:mm)».

## 5. Legale e testi, prima del codice

- **Informativa §15**: GA4 **e** Meta Pixel + Conversions API (Meta Platforms Ireland Ltd), finalità «misurazione e ottimizzazione delle nostre inserzioni», base consenso dal banner (categoria marketing), dati: identificativi cookie `_fbp`/`_fbc`, pagina, e per gli eventi dal server l'email in forma pseudonimizzata (hash); revoca dal banner (link «Preferenze cookie» nel piè di pagina). §15.2 elenca i cookie di Meta. Via la frase «non Facebook Pixel». Tabella sub-responsabili: + Meta. Versione **v2.11**, hash, modal «Cosa è cambiato» con il testo giusto.
- **Banner**: testo nuovo ×4 lingue; «Nessun cookie pubblicitario, mai» sparisce perché non sarebbe più vero.
- **Piè di pagina**: link «Preferenze cookie» che riapre il banner (oggi la revoca è solo «cancella i dati del browser»: con il marketing serve un gesto visibile).
- Termini: nessun cambio.

## 6. Zero regressioni: come lo garantiamo

- Senza consenso marketing nessuna richiesta verso Meta parte dal browser: guardia che `fbevents.js` non è nel bundle iniziale e viene iniettato solo da `grantMarketing()`.
- Senza `META_PIXEL_ID` tutto spento: `initMeta` esce subito, le funzioni sono no-op; guardia con env vuota.
- Payload del subscribe: i campi nuovi (`event_id`, `tracciamento`) sono facoltativi; un bundle vecchio in cache manda il payload di oggi e il server risponde come oggi (guardia dal vivo, come per l'età).
- La risposta HTTP non aspetta Meta: l'invio è in task; se Meta è giù il form va a buon fine identico (guardia con endpoint finto che fallisce).
- GA non cambia: `trackEvent` resta, solo la categoria si sdoppia; guardia che `generate_lead` continua a partire.
- Dedup: guardia che browser e server usano lo stesso `event_id` per lo stesso Lead.
- Privacy: guardia che nel registro e nei log non c'è mai l'email in chiaro né il token.
- Banner: guardia sulle tre scelte, sulle chiavi v3 e sulla ricomparsa una volta sola.
- Prova con `META_TEST_EVENT_CODE` in locale e in prod prima di togliere il codice di test: gli eventi si vedono nella scheda «Testa gli eventi» con il nome, l'`event_id` e la dedup confermata.

## 7. Lotti e tempi

| Lotto | Cosa | Giorni |
|---|---|---|
| **MP0 Fondamenta** | `META_PIXEL_ID`/`META_CAPI_TOKEN`/`META_TEST_EVENT_CODE` in compose e site-config; `pulisci_utm` esteso (content, term, fbclid, gclid); provenienza alla registrazione operatore e all'account cliente; UTM nelle inserzioni (fatto dal founder) | 0,5 |
| **MP1 Consenso e testi** | banner v3 a tre scelte, `lib/consenso.js`, link «Preferenze cookie», informativa §15 + sub-responsabili v2.11 ×4, modal | 0,5 |
| **MP2 Pixel browser** | `lib/meta.js`, PageView, Lead su tutte le porte, CompleteRegistration (operatore, account), Contact, Purchase sulla pagina di grazie; `event_id` nei payload | 0,5 |
| **MP3 Conversions API** | `services/meta_capi.py` con coda/retry/test code, hook su subscribe, conferma (LeadConfermato), registrazione operatore, account, contatti, webhook Stripe (Purchase); registro `tracciamento_eventi` con TTL | 1 |
| **MP4 Regia** | filtri e ripartizione per campagna negli Iscritti, colonna Provenienza negli Operatori, blocchi «Campagne» e «Meta» nel lunedì, semaforo nel Tecnico | 0,5 |
| **MP5 Prova e accensione** | prova in locale con test code (dedup verificata), deploy, prova in prod con test code, poi via il test code; in Meta: configurazione eventi web (priorità), campagna su obiettivo Contatti → Lead | 0,5 |
| **Totale** | | **3,5** |

Ordine: MP0 → MP1 → MP2 → MP3 → MP4 → MP5, un giro di deploy solo alla fine (più un giro di solo frontend se il banner va rivisto). Ogni lotto con la sua guardia; suite al baseline prima del giro.

## 8. Cosa leggerai dopo, e dove

- In **Meta**: nella colonna «Risultati» della campagna i Lead (deduplicati browser+server), il costo per Lead, e in Gestione eventi la «qualità della corrispondenza» (quanti eventi Meta riesce ad abbinare a una persona: con email in hash e fbp sale sopra 6/10).
- In **regia**: quanti di quei Lead sono persone vere e confermate, per campagna e per inserzione; quanti operatori sono arrivati dalle inserzioni per professionisti; quanto costa un iscritto confermato (spesa Meta ÷ confermati). Questo numero è quello che decide dove mettere i soldi.

## 9. Decisioni del founder

1. Banner a tre scelte (Solo essenziali / Statistiche / Accetta tutto) e ricomparsa una volta a chi aveva già scelto: ok?
2. Eventi: Lead, LeadConfermato, CompleteRegistration (operatore e account), Contact, Purchase. Togliere o aggiungere qualcosa?
3. Informativa v2.11 con Meta tra i sub-responsabili: ok a un nuovo clic di ri-accettazione per gli operatori (oggi 44)?
4. Via ai lotti MP0-MP5 in sequenza, deploy unico alla fine con prova in test mode prima e dopo.
