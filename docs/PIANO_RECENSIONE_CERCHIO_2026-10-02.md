# Il Cerchio dalla recensione — piano RC

*2 ottobre 2026, sera. Richiesta del founder: chi lascia una recensione deve poter scegliere di entrare nel Cerchio, con una casella. Vincolo assoluto: il flusso delle recensioni funziona bene e non deve avere regressioni, inciampi o messaggi fuorvianti.*

## 0. Com'è oggi il flusso (e cosa non si tocca)

Modal «Scrivi una recensione» sulla pagina dell'operatore, quattro passi in un solo componente (`OperatorProfilePage.js`, `WriteReviewModal`):

| Passo | Cosa succede | Chiamata |
|---|---|---|
| email | spiega la verifica, chiede l'email | `POST /public/reviews/request-otp` → 202 sempre, codice a 6 cifre via email |
| code | inserisci il codice | nessuna chiamata (il codice si verifica al submit) |
| form | stelle, nome visibile, testo (min 20) | — |
| submit | una sola chiamata con email + codice + recensione | `POST /public/reviews/submit` → `{status, verified, id}` |
| done | «Grazie della tua recensione!» + Chiudi | — |

Lato server: si guarda il codice, si decide `verified` (ha ordini con l'operatore), si valida, si **brucia il codice solo a recensione accettata**, si salva con l'email **solo in hash**, parte la ricevuta al recensore e l'avviso all'operatore.

**Non si tocca niente di questo.** Né l'OTP, né la validazione, né la ricevuta, né l'hash, né i messaggi d'errore, né i limiti.

## 1. Il gancio: una casella nel passo «form», un solo invio

### 1.1 Interfaccia

Nel passo `form`, sotto il testo della recensione e sopra «Pubblica la recensione», **una casella facoltativa e non preselezionata**, in carattere piccolo, con lo stesso testo versionato del Cerchio che c'è su tutte le altre porte (`lib/testiConsenso.js`):

> ☐ Sì, mandami la Lettera del Cerchio di Aurya (meditazioni, guide, ritiri). Ti cancelli con un clic.

Dice «di Aurya» per non confondersi con la newsletter dell'operatore. Nessun testo in più, nessun campo in più. Il pulsante resta «Pubblica la recensione»: il gesto principale è e rimane la recensione.

### 1.2 Una sola chiamata, come oggi

Il submit manda lo stesso payload di oggi più `cerchio: true/false` (facoltativo, default false, quindi un bundle vecchio in cache manda esattamente quello di oggi) e `consenso_versione`. **Nessuna seconda chiamata dal browser**: niente doppio stato, niente «la recensione è andata e l'iscrizione no» da gestire lato utente.

### 1.3 Ordine delle cose sul server

1. `submit_review` come oggi, fino in fondo: recensione salvata, codice bruciato, ricevuta inviata. Se qui c'è un errore, l'errore è quello di oggi e **del Cerchio non si fa nulla**.
2. Solo dopo, se `cerchio` è vero: iscrizione con la funzione interna già usata dalle altre porte (`iscrivi(..., gia_verificato=True)`), fonte `recensione`, consenso registrato con testo e versione, poi `segna_verificato(email, "otp", "recensione:<slug>")`. Il codice OTP è già la prova che l'indirizzo è suo, quindi **l'iscritto entra confermato** senza seconda email di conferma. Il tipo `otp` esiste già nel registro delle prove.
3. Qualunque errore del Cerchio viene inghiottito e loggato: la recensione è già a posto, la risposta resta 200.
4. La risposta aggiunge una chiave: `cerchio: "iscritto" | "gia_dentro" | null`. Le tre chiavi di oggi restano identiche.

Casi: honeypot pieno → 202 finto come oggi, nessuna iscrizione. Recensione in attesa di approvazione (operatore con recensioni aperte, non cliente) → l'iscrizione vale lo stesso: consenso e prova dell'email non dipendono dalla moderazione. Email già nel Cerchio → nessun doppione, risposta `gia_dentro`.

### 1.4 Il messaggio finale: prima la recensione, sempre

Il passo `done` resta com'è: **«Grazie della tua recensione!»** in evidenza, poi Chiudi. Sotto, in piccolo e solo se serve:

| Risposta | Riga in più |
|---|---|
| casella non spuntata | nessuna (identico a oggi) |
| `iscritto` | «E benvenuta nel Cerchio: la prima Lettera arriva nella tua casella.» |
| `gia_dentro` | «Sei già nel Cerchio di Aurya.» |
| `null` (errore silenzioso lato Cerchio) | nessuna |

Niente toast, niente secondo schermo, niente «ti sei iscritto» come titolo. Chi ha spuntato la casella trova la conferma in una riga; chi non l'ha spuntata non vede differenze.

### 1.5 Le email che arrivano

- Ricevuta della recensione: come oggi.
- Se iscritto: la prima email del Cerchio (il benvenuto che parte a ogni conferma). Due email nello stesso minuto, da Aurya, coerenti: una dice «la tua recensione è pubblica», l'altra «benvenuta nel Cerchio». Nessuna email di «conferma l'iscrizione»: la prova c'è già.

### 1.6 Dati e regia

- `source = recensione`, provenienza canale `sito` › superficie `recensione` (una riga nella tabella di `services/provenienza.py`), così nella regia Iscritti e in Brevo (`AURYA_SUPERFICIE`) si vede subito quanti arrivano da qui.
- `verificato_da = {tipo: otp, dettaglio: recensione:<slug>}`, consenso con `modalita: doppio` (prova presente), testo e versione della casella.
- Legale: niente da cambiare, la riga 7-bis copre già il Cerchio con consenso e testo versionato. Nessun bump, nessun modal.

## 2. Lotti

| Lotto | Cosa | Guardia |
|---|---|---|
| **RC1 backend** | `cerchio` e `consenso_versione` in `ReviewSubmit`; dopo `submit_review`, l'iscrizione best-effort; `cerchio` nella risposta; riga `recensione` in provenienza | `test_recensione_cerchio.py`: payload senza `cerchio` → risposta identica a oggi; con `cerchio` e OTP valido → iscritto confermato, `verificato_da.tipo == "otp"`, source e superficie giuste; errore simulato nel Cerchio → recensione salvata e 200; honeypot → nessuna iscrizione; i test recensioni esistenti intatti |
| **RC2 modal** | casella nel passo form (testid `review-cerchio`), stato `cerchio`, payload, riga condizionale nel passo done (testid `review-cerchio-esito`); chiavi i18n ×4 (parità) | guardia sul sorgente: casella non preselezionata, titolo del done invariato, nessuna seconda chiamata |
| **RC3 prova e deploy** | prova in locale: recensione senza casella (identica a oggi), con casella (riga di esito, iscritto in regia con superficie `recensione` e prova `otp`), email già nel Cerchio, codice sbagliato; suite; giro backend + frontend | verifica in prod senza creare recensioni vere: solo la casella visibile e la risposta del submit con codice sbagliato (400 identico a oggi) |

Due o tre ore. Deploy in un giro solo.

## 3. Perché non può rompere le recensioni

- Il campo nuovo è facoltativo e falso di default: il payload di oggi è un sottoinsieme valido di quello nuovo.
- L'iscrizione parte **dopo** che la recensione è salvata e il codice bruciato, dentro un `try` che non lascia uscire nulla. La recensione non sa nemmeno che il Cerchio esiste.
- Nessuna nuova chiamata dal browser, nessun nuovo passo, nessun nuovo pulsante: il passo `done` cambia solo per una riga in piccolo, e solo per chi ha spuntato.
- Le tre chiavi della risposta restano uguali: i test live esistenti (`status == "published"`, `invalid_code`) non vedono differenze.
- Niente seconda email di conferma: meno posta, meno inciampi, e la prova è più forte di un clic (codice a 6 cifre, una volta sola, 15 minuti).

## 4. Cosa misurare

Nella regia Iscritti, ripartizione per canale › superficie `recensione`: quanti al mese e quanti sono già confermati (tutti, per costruzione). In Brevo il segmento «Dalla recensione» = `AURYA_SUPERFICIE = recensione`. Con 9 recensioni in tre mesi saranno pochi, ma sono clienti paganti che tornano a scrivere: i migliori.
