# Piano SB — un diritto, una prova, una memoria (20 agosto 2026)

Richiesta del founder: consolidare iscrizione alla Lettera, verifica e
sblocco in modo che **si sblocchi una volta e si sblocchi tutto**, che
l'email resti in memoria fino alla creazione dell'account, e che per
gli iscritti senza account ci sia il gancio per finalizzare. «Tutto il
sistema deve essere intelligente ovunque l'utente si trovi.»

Riferimenti: `docs/MAPPA_PERCORSI_IDENTITA_2026-08.md`,
`docs/COERENZA_PERCORSI_PIANO_CP_2026-08.md`.

---

## 1. La diagnosi — un diritto solo, quattro prove diverse

Il diritto è UNO: «fa parte del cerchio» (Lettera confermata, oppure
account Aurya). Ma la prova di quel diritto oggi vive in **quattro
artefatti diversi**, ognuno con il suo formato, la sua chiave nel
browser e le sue superfici:

| # | prova | formato | chi la scrive | chi la legge |
|---|---|---|---|---|
| P1 | `aurya_nl_token` | JWT `newsletter_subscriber` | pagina di conferma, mini-form «già iscritto» del blog, login account (AP2), quick-login checkout | **solo le guide** del Magazine |
| P2 | `fqz_catalog_unlock` | `{email, token}` HMAC `fqz-catalog:` | form meditazioni, form traccia condivisa | **solo** catalogo meditazioni + traccia |
| P3 | `fqz_listener_ok` | flag `'1'` | traccia condivisa **al solo subscribe** | player della traccia |
| P4 | Bearer platform | sessione account | login | tutte le superfici |

Da qui discendono TUTTI i sintomi segnalati. Non sono cinque bug: è
una prova frammentata.

## 2. I fatti verificati sul codice

**F1 — Riiscriversi è sempre possibile e la risposta è sempre
«controlla l'email».** Il backend invece È intelligente: per un'email
già confermata NON riparte il double opt-in, manda un'email di accesso
(magic link) — `_send_access_email`, `routers/subscribers.py:271`. Ma i
form non lo dicono: il grazie del LeadForm promette sempre «il link di
conferma sblocca la guida». Solo il form delle meditazioni prova lo
sblocco immediato dopo il subscribe; il gate delle guide no, pur
avendo ora `/public/newsletter/unlock` a disposizione.

**F2 — Lo sblocco non si propaga.** Sbloccare le meditazioni scrive P2;
sbloccare una guida scrive P1. Nessuno dei due scrive l'altro: la
stessa persona, già dentro, trova chiuso il cancello accanto.

**F3 — La pagina di conferma serve solo il blog.** `_safe_return_to`
accetta solo `/blog/*`: il `return_to: '/meditazioni'` aggiunto con
NL-septies viene **scartato in silenzio**, e la pagina di conferma
salva solo P1. Risultato: il testo «il link ti riporta qui, con le
meditazioni sbloccate» oggi è **falso due volte** — non riporta lì, e
non sblocca lì (bisogna ridigitare l'email nel mini-form).

**F4 — La traccia condivisa si apre ancora da pending.** In
`PublicFrequencyPage.js:130` il subscribe imposta `fqz_listener_ok='1'`
e `setUnlocked(true)` PRIMA di ogni conferma: la regola debole che
NL-septies ha tolto dal catalogo è sopravvissuta qui. Chiunque digiti
un indirizzo qualsiasi ascolta la traccia intera.

**F5 — Nessuna memoria dell'email verso l'account.** Il sistema
l'email la SA (è in chiaro in P2, ed è leggibile nel payload di P1),
ma `/accedi?vista=crea` precompila solo da `?email=` nell'URL: chi
arriva dal menu dell'omino trova il campo vuoto.

**F6 — Dopo lo sblocco, nessun gancio verso l'account.** Il ponte
«crea il tuo account» (NL2) esiste solo dopo l'ISCRIZIONE dal
LeadForm. Chi sblocca da «già iscritto» — cioè esattamente l'iscritto
fedele senza account — non riceve mai l'invito.

## 3. Il principio

> **Un diritto, una prova, una memoria.**
> La prova è il token della Lettera (o la sessione account); vive in
> UN posto nel browser; ogni cancello la legge da lì; e finché non
> c'è un account, quella prova È la memoria dell'email — ovunque.

## 4. Le fasi

### SB1 — Una prova sola: il token della Lettera apre tutto

Il JWT `newsletter_subscriber` (P1) diventa l'unica prova lato Lettera.

- **Backend**: catalogo meditazioni e traccia accettano il JWT
  (`decode_subscriber_token` + `_subscriber_ok` riverificato, come oggi
  con l'HMAC). L'HMAC resta accettato in lettura per i browser che ce
  l'hanno già (in prod i token vivono in localStorage): si toglie in un
  ciclo futuro. `/frequencies/catalog/unlock` ritorna il JWT — o
  meglio: il form usa direttamente `/public/newsletter/unlock`.
- **Frontend**: nasce `lib/cerchio.js` (stesso disegno di
  `utils/authLinks.js`: il posto unico): `salvaProva(token)`,
  `prova()`, `emailDellaProva()` (dal payload del JWT). UNA chiave:
  `aurya_nl_token`. Le chiavi P2/P3 si leggono come ripiego e si
  migrano al primo uso.
- Effetto: **sbloccare in un posto qualsiasi sblocca ovunque**, perché
  ogni cancello legge la stessa prova.

### SB2 — I form hanno lo stesso cervello

Dopo OGNI subscribe, un solo comportamento (oggi ne esistono tre):

1. prova lo sblocco immediato (`/public/newsletter/unlock`);
2. se riesce → «Sei già dei nostri: tutto sbloccato» + prova salvata
   (guide E meditazioni, per SB1);
3. se non riesce → «Ti abbiamo scritto: il click conferma e sblocca» —
   e stavolta è vero (SB3).

La logica vive in un hook condiviso (`useIscrizioneLettera`), usato da
LeadForm, meditazioni e traccia: i vestiti restano diversi, il
cervello è uno.

### SB3 — La conferma finisce il lavoro ovunque

- `_safe_return_to` diventa una whitelist di path interni:
  `/blog/*`, `/meditazioni`, `/frequenze/*` (sempre niente `//`).
- La pagina di conferma onora quei ritorni («Torna a…» generico, non
  più solo «alla guida») e salva la prova unica — che per SB1 apre da
  sé anche meditazioni e traccia.
- Il testo di attesa delle meditazioni smette di mentire: il link
  riporterà davvero lì, sbloccato.

### SB4 — La traccia condivisa smette di aprirsi da pending

Via il `fqz_listener_ok` incondizionato al subscribe: la traccia si
apre solo con la prova (sblocco riuscito) o resta in attesa di
conferma, con lo stesso messaggio delle meditazioni. Chiude il buco
gemello di NL-septies.

### SB5 — La memoria dell'email arriva fino alla porta

`/accedi?vista=crea` precompila in quest'ordine:
1. `?email=` nell'URL (com'è oggi — i cancelli lo passano già);
2. **`emailDellaProva()`** — l'email dell'iscritto sbloccato, anche se
   arriva dal menu dell'omino senza passare da un cancello;
3. vuoto.

Vale anche per la vista di accesso (email precompilata, mai la
password).

### SB6 — Il gancio per finalizzare: dallo sblocco all'account

Dopo OGNI sblocco riuscito (mini-form guide, meditazioni, traccia, e
al ritorno dalla conferma), compare il ponte già esistente di NL2 —
riusato, non duplicato: «Vuoi ritrovare tutto su ogni dispositivo?
Crea il tuo account» → `creaAccount(email, next)` con l'email della
prova. Discreto (una riga, congedabile), perché chi sblocca vuole
prima di tutto il contenuto. Con SB5, anche chi lo ignora ritrova
l'email pronta se cambia idea più tardi.

## 5. Cosa NON si tocca

- Il double opt-in: `confirmed` resta l'unica soglia (NL-septies).
- La risposta HTTP neutra del subscribe (nessun oracolo di enumerazione).
- Il legame account↔Lettera (AP2: il login porta già la prova).
- La strada operatore (LetterCard in Impostazioni, CP2).
- Niente email in chiaro in più nel browser: P2 la salvava già, il JWT
  la porta nel payload come oggi.

## 6. Ordine, rischi, verifica

| fase | tocca | rischio | verifica |
|---|---|---|---|
| SB1 | frequencies.py + lib/cerchio.js + 3 pagine | medio (dual-read HMAC) | E2E: sblocco dal blog → /meditazioni aperto senza ridigitare |
| SB2 | hook + 3 form | basso | E2E: riiscrizione con email confermata → sblocco immediato, messaggio onesto |
| SB3 | subscribers.py + ConfirmPage | basso | E2E: iscrizione da /meditazioni → click conferma → si torna lì, aperto |
| SB4 | PublicFrequencyPage | basso | guardia: subscribe da solo NON apre il player |
| SB5 | AccountLoginPage | basso | E2E: sblocco → omino → crea account → email già dentro |
| SB6 | gate ×3 + ConfirmPage | basso | guardia: il ponte compare dopo lo sblocco, con l'email |

Ordine: SB1 → SB4 (sicurezza) → SB2 → SB3 → SB5 → SB6.
Totale ~2 giornate. Nessuna migrazione dati: i vecchi artefatti nel
browser restano letti in ripiego e migrati al primo uso.
