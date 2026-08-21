# Audit pre-deploy — 21 agosto 2026

Delta da **prod-2026-08-16c** (17/8, = `origin/main`): **80 commit,
100 file, +16.600 righe**. Dentro: porta unica /accedi + SSO (ID),
funnel Lettera e sblocco unico (NL/CP/SB), Aurya Sound intero
(FQ/LN/SP/SL/SF/ONDA/audit), marca unica (DN), striscia in home, voce
professionisti. In produzione: **7 operatori, 12 org, 2 account
cliente (di prova), 6 iscritti Lettera, 1 ordine** — e link di
registrazione già in mano a persone che potrebbero usarli in qualunque
momento.

## 1. Continuità verificata (cosa NON si rompe)

| cosa | verifica | esito |
|---|---|---|
| verifica email operatore (`/verify-email?token=`) | rotta viva, pagina invariata | ✔ |
| reset operatore (`/reset-password`) | rotta viva | ✔ |
| verifica/reset cliente (`/account/verify-email`, `/account/reset-password`) | rotte vive | ✔ |
| **magic link vecchi** (`/account/accedi?token=`) | redirect a `/accedi` che **conserva la query**; `/accedi` consuma `?token=` | ✔ |
| magic link nuovi | il backend genera `/accedi?token=` (2 punti, verificati) | ✔ |
| conferma Lettera (`/newsletter/conferma/:token`) | rotta viva; whitelist dei ritorni ALLARGATA (mai ristretta) | ✔ |
| link registrazione girati (`/signup`, `/entra-nella-rete`) | `/signup` → redirect al form vivo | ✔ |
| biglietti/prenotazioni (`/t/`, `/b/`, `/rsv/`, `/d/`) | intoccati nel delta | ✔ |
| sessioni esistenti (token operatore e cliente) | stessi segreti, stessi claim: restano valide | ✔ |
| bookmark `/login` | redirect con query conservata | ✔ |
| env | **nessuna variabile nuova obbligatoria** | ✔ |
| indici Mongo nuovi (frequenze, favorites, voice, legami identità) | creati dal backend all'avvio, `sparse` dove serve | ✔ |
| build frontend | `CI=true npm run build` → **exit 0** | ✔ |
| suite | 4.137-4.142 verdi; 4 rossi noti d'ordine (cascata rate-limit login: test_login_success 429, ordini_mo full_circle, P4Gdpr, sitemap pp2b) — verdi in isolamento | ✔ |

## 2. Le DUE azioni obbligatorie al deploy

### R1 — Timbro benvenuto per le org esistenti (senza: sorpresa a 7 operatori)
`welcome_pending` è vero per ogni org senza `welcome_seen_at`, e **in
prod sono 12 su 12**. Al primo login post-deploy ogni operatore
esistente verrebbe portato su `/benvenuto` — saltabile e una tantum, ma
è un onboarding mostrato a gente che lavora su Aurya da settimane:
l'opposto della continuità chiesta.

**Fix nel deploy** (prima di riaprire il traffico), org esistenti = tutte:

```js
db.organizations.updateMany(
  { welcome_seen_at: { $exists: false } },
  { $set: { welcome_seen_at: new Date().toISOString(),
            welcome_backfilled: true } })
```

Le org nate DOPO il deploy non hanno il timbro → il benvenuto resta
vivo per i nuovi, che è il suo scopo.

### R2 — La libreria dei suoni (62 file, 635 MB)
In prod `audio_assets` è **0**. Le frequenze funzionano senza (si
sintetizzano nel browser), ma il mondo «Suoni» di Esplora e le basi
del compositore sarebbero vetrine vuote.

**Fix nel deploy**: `mongodump` locale della sola `audio_assets` +
restore in prod, e `rsync` di `backend/uploads/audio/` (635 MB) sul
volume del server. Da fare PRIMA dello switch, così il primo visitatore
trova tutto. (In alternativa si rimanda il mondo Suoni: sconsigliato,
la UI lo mostra.)

### R3 (facoltativa, economica) — Backfill legami identità
`scripts/link_identity_hats.py` in prod: oggi collegherebbe poco o
nulla (2 account di prova), e il legame si auto-ripara comunque a ogni
login (`auto_link_by_email`). Lanciarlo è un minuto e azzera il dubbio.

## 3. Rischi accettati — da sapere, non da fixare

1. **`/public/newsletter/unlock` rivela lo stato d'iscrizione** di
   un'email (404 se non confermata). È il prezzo del «sei già
   iscritto? sblocca» voluto nel funnel; mitigato dal rate limit
   10/min/IP. Dato poco sensibile (appartenenza a una newsletter), ma
   è un'informazione che prima non usciva.
2. **`/uploads` e l'elenco suoni sono pubblici** (debito noto dal
   ciclo SL): per l'ascolto è necessario, ma 635 MB di audio diventano
   scaricabili da chiunque abbia gli URL — banda da tenere d'occhio.
3. **Primo avvio dell'«app» dopo il deploy**: chi era loggato resta
   loggato (token validi), ma chi aveva la pagina APERTA durante lo
   switch vedrà il solito refresh richiesto. Normale.
4. **I contatori anti-bruteforce sono in memoria**: il riavvio li
   azzera (nessun impatto per gli utenti; i lockout persistenti su DB
   restano).
5. **Il benvenuto post-R1**: un nuovo operatore invitato PRIMA del
   deploy che si registra DOPO vedrà /benvenuto — corretto, è nuovo.

## 4. Piano di deploy proposto (nell'ordine)

1. **Push di `main`** su GitHub (80 commit locali: oggi origin è fermo
   al tag di prod). I tag non passano (ruleset), come sempre.
2. **Backup Mongo** pre-deploy (`/root/backups/predeploy-2026-08-21.gz`).
3. Server: `git pull` + build (runner script server-side con nohup,
   come da prassi).
4. **R1** (timbro benvenuto) e **R2** (libreria suoni: restore
   `audio_assets` + rsync file) prima di riaprire il traffico.
5. R3 facoltativa (backfill legami).
6. **Smoke sul vivo**:
   - `/accedi`: login operatore vero (con consenso del titolare) o
     conto demo → dashboard, NIENTE /benvenuto (prova di R1);
   - un magic link fresco richiesto da `/accedi` (email arriva, entra);
   - `/newsletter/conferma/<token-test>` → conferma + «Torna…»;
   - `/sound/esplora` → schede che suonano, mondo Suoni popolato
     (prova di R2), `/meditazioni` col cancello;
   - home: striscia Sound visibile, contrasto ok sul server (la foto
     `hp-sound.jpg` viaggia nella build);
   - `/blog/<guida-riservata>`: gate + «sei già iscritto» funziona;
   - sitemap: `/sound*` presente; GSC ricaricata dal founder (prassi).
7. Tag `prod-2026-08-21` locale.

## 5. Cosa NON serve fare

- Migrazioni dati su utenti/ordini: **zero** (nessun campo esistente
  cambia significato; le versioni score sono additive e prod non ha
  tracce).
- Nuove env, nuovi servizi, nuovi container: no.
- Backfill Lettera: i 6 iscritti restano com'erano; il funnel nuovo
  legge gli stessi stati.

## 6. Giudizio

Il delta è grande ma **additivo**: i punti dove tocca l'esistente
(porta unica, redirect, funnel Lettera) sono coperti da redirect che
conservano la query e da guardie che testano proprio i percorsi
vecchi (172+ guardie nuove nel delta). Le due azioni R1/R2 sono
l'unico ponte fra «tutto verde in locale» e «nessuna sorpresa per chi
già usa Aurya». Con quelle nel piano, il deploy è controllato.
