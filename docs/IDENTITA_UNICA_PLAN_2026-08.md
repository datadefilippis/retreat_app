# Identità unica — piano ID (20 agosto 2026)

**Il caso che ha aperto il ciclo**: un'operatrice registrata il 19/8 non
riusciva «più a entrare». In produzione: account operatore sano, zero
tentativi falliti sul suo mondo, otto 401 su `/api/platform/auth/login` —
la porta dei CLIENTI, dove lei non esiste. Non è il primo caso, e il
messaggio «credenziali non valide» non le ha mai detto che la porta era
sbagliata.

**Il principio del ciclo**: su Aurya una persona è UNA persona. A volte
vende (gestionale), a volte compra (biglietti, meditazioni), a volte si
iscrive solo alla Lettera. Quale archivio la contiene è un dettaglio
NOSTRO: scaricarlo sull'utente sotto forma di «due login» è il bug.

---

## 1. Stato attuale (mappa verificata sul codice, 20/8)

Quattro rappresentazioni della stessa persona:

| collezione | scopo | credenziali | porta | token |
|---|---|---|---|---|
| `users` | operatore, org-scoped (+ system_admin) | password (12+ char) | `/login` | `token` (JWT type user, 7gg) |
| `platform_accounts` | identità utente finale marketplace (AP, lug 2026) | magic-link-first, password opzionale | `/account/accedi` | `platform_token` |
| `customer_accounts` | login cliente org-scoped (era storefront) | password | `/account/login` (DORMIENTE: nessun link pubblico) | JWT type customer |
| `newsletter_subscriptions` | iscrizione Lettera | nessuna | — | — |

Fatti che vincolano il progetto:

- **Numeri di oggi (prod)**: 7 operatori, 2 platform account, e le 2
  email dei platform account sono ANCHE operatori. Zero clienti veri.
  → il momento più economico per sistemare le fondamenta è ADESSO.
- `customer_accounts` non è più una porta: resta il gancio CRM/ordini
  (`customer_account_id` sugli ordini, link a `platform_account_id`).
- Il menu dell'omino (MarketplaceShell) chiama «Il tuo account Aurya»
  la sezione clienti: un operatore, che UN account Aurya ce l'ha, si
  riconosce lì e sbaglia porta. L'etichetta mente.
- Entrambe le porte rispondono «credenziali non valide» anche quando la
  vera causa è «esisti, ma nell'altro mondo» (anti-enumeration corretto,
  UX cieca).
- Lockout e rate-limit sono PER MONDO: 5 tentativi + 20/h per email su
  `users`, contatori separati su `platform_accounts`. Un attaccante può
  martellare una porta mentre l'altra non conta.
- Flussi che DEVONO restare intatti: signup operatore 4 campi (guardia),
  `?next=` su login e account/accedi (open-redirect guard), checkout con
  pass/Passaporto (TA), GDPR due livelli (AP/LI).

## 2. Architettura bersaglio

**Una persona → una email → un accesso → due cappelli.**

Non si fondono le collezioni (rischio alto, guadagno zero oggi): si
fondono la PORTA e il LEGAME. `users` e `platform_accounts` restano gli
archivi dei due cappelli; nasce il collegamento esplicito fra loro e una
sola esperienza di accesso davanti.

```
                    /accedi  (unica porta visibile)
                       │ POST /api/auth/entra {email, password}
                       ▼
          ┌─ verifica su users ──────── match → token operatore (+ cliente se linkato)
          └─ verifica su platform ───── match → platform_token
                       │ nessun match → errore UNICO generico
                       ▼
     users.platform_account_id  ⇄  platform_accounts.operator_user_id
              (il «legame dei cappelli», nuovo, opzionale)
```

Regole di disambiguazione (nessun conflitto possibile):

1. La **password è il selettore**: si entra nel mondo la cui credenziale
   combacia. Email uguale nei due mondi con password diverse → nessuna
   ambiguità.
2. Password che combacia in ENTRAMBI → si entra da operatore (il
   gestionale è il contesto di lavoro), e l'interruttore del cappello è
   nel menu. Nessuna schermata di scelta: la scelta vive DOPO, non prima.
3. Identità **collegate e email verificata da entrambe le parti** → la
   porta rilascia entrambi i token in una risposta sola (effetto SSO:
   un login, due cappelli). Se non collegate, rilascia solo il mondo
   combaciato.
4. Errore sbagliato/inesistente → UN solo messaggio generico, identico
   per timing e byte (anti-enumeration invariata, anzi migliorata:
   una porta sola = una sola superficie da uniformare).
5. Platform account nato passwordless (magic link) e nessun match
   password → il form offre «Accedi senza password» (flusso OTP/magic
   esistente, invariato).

Il lockout diventa **per email, trasversale**: i tentativi falliti sulla
porta unica incrementano un contatore unico; soglie e backoff attuali
(5 tentativi, 15→30→60…min) invariati. Sparisce il bypass a due porte.

## 3. Le fasi

### ID1 — L'errore che ripara (cerotto, subito, ~½ giornata)
Sulle DUE pagine attuali: quando il login fallisce, sotto l'errore
generico compare SEMPRE (non condizionato all'esistenza dell'email:
niente enumeration) il rimando all'altra porta: «Sei un professionista?
L'accesso al gestionale è qui →» / «Cerchi i tuoi acquisti? L'account
cliente è qui →». Su `/account/accedi` il rimando smette di essere la
postilla grigia in fondo: entra nel corpo dell'errore.
*Vale anche se ID2-ID5 slittano: è indipendente e si butta via dopo.*

### ID2 — La porta unica `/accedi` (~1 giornata)
- BE: `POST /api/auth/entra` — orchestratore che chiama i DUE servizi di
  verifica esistenti (`auth_service`, `platform_account_service`), senza
  toccarli; risposta `{worlds: [{type, token}], hint?}`. Rate-limit IP
  10/min + lockout unificato per email. Log con esito e mondo.
- FE: pagina `/accedi` unica (form email+password, secondaria «senza
  password», «Password dimenticata?»), che salva i token ricevuti nelle
  chiavi ESISTENTI (`token`, `platform_token`) e redirige: operatore →
  `/dashboard` (o `?next=`), cliente → `/account` (o `?next=`).
- `/login` e `/account/accedi` restano VIVI come alias: stessi form
  sostituiti da redirect 302 (i segnalibri e i `?next=` non muoiono mai).
- Tutti i link interni (menu omino, shell, footer, `PRO_ENTRY`,
  soccorsi incrociati LR1) puntano a `/accedi`.
- Il menu omino si riscrive: UNA voce «Accedi» da sloggato; le due
  sezioni restano solo da loggato, coi cappelli disponibili.

### ID3 — Il legame dei cappelli (~1 giornata)

Stato verificato (20/8): i due signup sono CIECHI l'uno all'altro —
`auth_service.signup` controlla solo `users`, `platform_account_service`
non tocca mai `users_collection`. Oggi un operatore che vuole comprare
fa una seconda registrazione con seconda verifica e seconda password;
un cliente che diventa operatore, idem al contrario.

Campi `users.platform_account_id` ⇄ `platform_accounts.operator_user_id`
(indicizzati, opzionali). Backfill: stessa email verificata nei due
mondi → link automatico (oggi: 2 persone).

**Direzione A — operatore → cappello cliente (il caso «compro dal
collega»):** UN clic, zero credenziali nuove.
`POST /api/auth/hats/client` autenticato col JWT operatore:
- se esiste già un platform_account VERIFICATO con la sua email → link;
- se non esiste → lo crea DALL'identità operatore: email già verificata
  al signup operatore → nasce `email_verified: true`,
  `password_hash: None`, già linkato. Nessuna seconda verifica, nessuna
  seconda password: dal login successivo la porta unica gli rilascia
  entrambi i token.
Il bottone vive dove serve: in `/account`, nel checkout, sulla pagina
di una meditazione da salvare. Mai provisioning automatico senza gesto
esplicito: un cappello nasce solo se richiesto.

**Direzione B — cliente → diventa operatore:** il signup operatore
resta INTATTO (4 campi, guardia). Se arriva loggato da cliente, l'email
è precompilata. Alla verifica dell'email operatore, se esiste un
platform_account verificato con la stessa email → link automatico.
Dal login successivo: un solo accesso, due cappelli.

**Il punto concettuale**: il meccanismo non impone «una password sola
nel database» — rende IRRILEVANTE quante ce ne siano. Con porta unica +
legame, un login qualsiasi (con la credenziale che combacia, o col
magic link) apre entrambi i mondi. Se per storia esistono due password
diverse, sono due chiavi valide della stessa porta: nessun conflitto,
e l'utente ne deve ricordare una qualsiasi.

Regole anti-bug del legame:
1. link SOLO fra email verificate da ENTRAMBE le parti (anti-takeover);
2. link idempotente e riparabile: se un puntatore esiste e l'altro no
   (crash a metà), il login successivo completa la coppia (lazy repair);
3. cambio email su un lato = il link si SPEZZA e si ricrea solo dopo la
   verifica del nuovo indirizzo (mai un link che sopravvive a un'email
   che non combacia più);
4. GDPR: cancellare un cappello annulla il puntatore sull'altro lato e
   non tocca nient'altro (regole P4 invariate); l'export di ciascun
   mondo menziona il legame;
5. nessuna fusione di dati fra i mondi: il legame è due FK, non un merge.

### ID4 — Coerenza di superficie (~½ giornata)
- `/account` mostra il cappello professionista se linkato («Il tuo
  spazio di lavoro → Gestionale») e viceversa l'omino nel gestionale
  mostra «I tuoi acquisti» se linkato.
- Stato Lettera in `/account` (iscritto sì/no, per email) con
  disiscrizione — il terzo «cappello» è solo una riga, non un login.
- Porta dormiente `/account/login` (customer_accounts): redirect a
  `/accedi`. Il router `customer_auth` resta per i token già emessi ma
  il login smette di accettare nuove sessioni (flag), con log di
  quarantena per 30 giorni prima della rimozione.
- Forgot unificato: `/password-dimenticata` → il BE spedisce il reset
  per OGNI mondo in cui l'email esiste (una email sola, sempre 200).

### ID5 — Guardie (~½ giornata, insieme alle fasi)
- Parità anti-enumeration: stessa risposta byte-per-byte per «email
  inesistente» e «password sbagliata» sulla porta unica.
- Lockout trasversale: N tentativi su `/accedi` = N sul contatore email,
  mai due contatori.
- Alias vivi: `/login` e `/account/accedi` rispondono 30x verso
  `/accedi` conservando `?next=`.
- `?next=` open-redirect guard invariata (`/` sì, `//` no).
- Signup operatore: 4 campi, invariato (guardia esistente).
- Link legame: mai auto-link su email NON verificata da entrambe le
  parti (altrimenti: registro un platform account con la TUA email e
  aspetto che il link mi regali il tuo gestionale).
- Menu omino: da sloggato una sola voce di accesso; l'etichetta
  «Il tuo account Aurya» non può convivere con una seconda porta.

## 4. Cosa NON si fa (e perché)

- **Niente fusione di collezioni**: `users` resta org-scoped col suo
  modello di ruoli, `platform_accounts` resta l'identità marketplace.
  La fusione è un progetto di migrazione che oggi non paga: il legame
  dà lo stesso risultato percepito con 1/10 del rischio.
- **Niente scelta del mondo PRIMA del login** («sei cliente o
  operatore?»): è la domanda che l'utente non sa. La password decide.
- **Niente token unico nuovo**: le chiavi `token`/`platform_token` e i
  due assi JWT restano; cambiarli invaliderebbe ogni sessione viva e
  ogni guardia. Il «token unico» è l'eventuale ID6 futuro, quando
  servirà davvero (oggi no).
- **Niente migrazione dei customer_accounts**: sono CRM, non identità.

## 5. Rischi e contromisure

| rischio | contromisura |
|---|---|
| account takeover via auto-link | link SOLO con email verificata da entrambe le parti (guardia ID5) |
| enumeration dalla porta unica | risposta unica, timing uniforme, lockout per email trasversale |
| doppio conteggio/bypass lockout | contatore unico per email, guardia dedicata |
| segnalibri e `?next=` rotti | alias 30x permanenti, guardia dedicata |
| sessioni vive invalidate | zero cambi a formato/chiavi token |
| flussi checkout/pass (TA) | il checkout continua a parlare con platform_token; ID3 aggiunge solo il provisioning rapido |

## 6. Ordine e stima

ID1 subito (indipendente). Poi ID2 → ID3 → ID4 con ID5 intrecciato.
Totale: ~3,5 giornate di lavoro effettivo. Ogni fase lascia il sistema
funzionante e deployabile da sola; il deploy resta a go esplicito del
founder.

Aperto (decisioni founder):
1. **SSO sì/no**: quando le identità sono collegate, la porta unica
   rilascia entrambi i token (raccomandato: sì — un login, due cappelli)?
2. I 2 platform account esistenti in prod sono account di prova? (se
   sì, il backfill ID3 parte pulito)
3. Nome della porta: `/accedi` (raccomandato) o riuso di `/login`?
