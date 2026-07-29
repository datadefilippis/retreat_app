# Piano Account Unico Aurya — 29 lug 2026

Ciclo AP. Obiettivo founder: UN account utente a livello piattaforma
per tutti gli acquisti (listino e ritiri, da profilo e marketplace),
con dentro acquisti cross-operatore, tracking, guide e materiale
gratuito se loggato e iscritto alla newsletter. RIUSANDO l'esistente.

## Parte 1 — Diagnosi del bug visto dal founder (riprodotta)

1. La creazione account al checkout fallisce con 400: il signup
   customer (CG-4, customer_auth_service.py:331) RIFIUTA la
   registrazione se lo store non ha pubblicato Privacy+Termini.
   Gli store demo sono not_configured → 400. Il checkout ingoia
   l'errore (best-effort, useCheckoutForm.js:797) e mostra solo un
   toast generico: ordine ok, account no. Fallirebbe identico anche
   sullo storefront: NON e' un bug del checkout inline, e' il limite
   del doppio sistema account.
2. Il consenso newsletter FUNZIONA: marketing timbrato su customer e
   consent_audit (RS5), indipendente dal signup. Preoccupazione
   infondata.
3. Il Passaporto FUNZIONA: platform_account pending creato, ordine
   timbrato, claim email alla conferma.

## Parte 2 — Scelta architetturale (dai numeri del codice)

DUE sistemi oggi: platform_accounts (Passaporto: email unica globale,
passwordless magic link + OTP, /account con ordini cross-operatore,
export/delete GDPR, 9 endpoint, 4 lingue) e customer_accounts
(per-store: password, verifica email, consensi CG-4 per-store, corsi
col player Bunny, 23 endpoint). Gia' collegati: l'ordine porta
entrambi gli id, claim retroattivo P4 aggancia lo storico.

DECISIONE: architettura a due livelli.
1. Il Passaporto (platform_account) E' l'account Aurya: identita'
   unica, login passwordless (magic link + codice 6 cifre, email gia'
   pronte x4 lingue), hub /account.
2. customer_accounts resta come RECORD INTERNO org-scoped (corsi,
   asset emessi, consensi per-store che sono legalmente del
   merchant), linkato via platform_account_id. MAI globalizzato: la
   sua email e' unica solo per org, fondere account con password e
   consensi diversi e' esattamente il rischio da evitare.
3. Newsletter: aurya_subscribers ha gia' email unica globale e token
   JWT sullo stesso secret → il join con l'account e' l'email.

## Parte 3 — Onde AP

### AP0 — Fix del bug (subito)
1. Coerenza con RS3 (i documenti autogenerati valgono): il signup
   customer accetta anche legal autogenerato, snapshot versione
   autogen:v0 come gia' fanno gli ordini. Il gate 400 resta solo se
   lo store non esiste.
2. Il catch del checkout diventa onesto: se il signup fallisce, il
   messaggio dice il motivo vero; per i corsi (dove l'account e'
   obbligatorio) resta bloccante.
3. Guardie: signup con store autogen va a buon fine; ordine+account
   dal checkout inline e storefront.

### AP1 — Il checkout parla Aurya, non store
1. La checkbox "crea account" del checkout viene sostituita dal
   messaggio Passaporto unico: "I tuoi acquisti in un posto solo:
   ricevi il link di accesso via email" (il claim gia' parte a
   pagamento/conferma). Niente password al checkout.
2. Opzione "Hai gia' un account Aurya? Accedi" prima del checkout:
   magic link/OTP (riuso AccountLoginPage inline o link), che
   prefilla nome/email e aggancia l'ordine all'account verificato.
3. Il signup customer resta SOLO dove serve strutturalmente (corsi),
   creato come record interno nel flusso, non come scelta utente.

### AP2 — /account hub completo
1. Tracking: la proiezione /platform/me/orders espone fulfillment
   (tracking_number/url, shipped_at); il rendering riusa quello del
   portale customer (OrderDetailPage). Stato ordine visibile.
2. Guide e newsletter: al login platform, lookup aurya_subscribers
   per email; se confermato → flag iscritto + emissione
   subscriber_token (riuso generate_subscriber_token, stesso secret)
   → le guide riservate si sbloccano da loggato senza ri-iscriversi.
   Sezione "Guide e materiale" in /account con gli articoli gated.
   Se non iscritto: invito a iscriversi (double opt-in esistente).
3. CTA coerenti: successo checkout, email, footer → /account.

### REVISIONE FOUNDER (29 lug, dopo AP2) — pivot password + legal Aurya

Decisioni del founder che aggiornano le onde successive:
1. NIENTE "Passaporto" come concetto o nome: UN solo account utente
   Aurya, classico, con email e password. Il passwordless resta solo
   come "accedi senza password" e recupero (gia' costruito, costo 0).
2. Legal a due livelli gestito da Aurya: Privacy e Termini di AURYA
   (titolare per account, newsletter, navigazione marketplace)
   accettati UNA volta alla creazione account, con snapshot versione
   sull'account. L'operatore NON gestisce piu' un impianto legale
   completo: configura solo le SUE condizioni (politica cancellazione,
   gia' RS3, + requisiti specifici del servizio, es. dichiarazione
   assenza patologie cardiache per rebirthing) che compaiono
   DINAMICAMENTE al checkout come checkbox propria solo se compilate.
3. L'operatore resta titolare autonomo dei dati dei suoi clienti
   (realta' GDPR dei marketplace): informativa autogenerata come link
   informativo. I testi legali Aurya definitivi vanno rivisti da un
   legale prima del lancio pubblico.

### AP1b — Password sull'account Aurya (NUOVA)
1. platform_account.password_hash (Optional, gia' nel modello) si
   attiva: signup email+password+verifica email, login password,
   reset password. Riuso della macchina customer_auth collaudata
   (bcrypt, lockout, token verifica) portata a livello piattaforma.
2. Magic link/OTP restano come alternativa e recovery; il claim
   post-acquisto guest invita a IMPOSTARE la password.
3. Guardie: signup/login/reset, lockout, email gia' registrata,
   account solo-passwordless che imposta password al primo accesso.

### AP-L — Legal a due livelli (NUOVA)
1. Consenso Aurya (terms+privacy backend/legal, versionato) timbrato
   sull'account alla creazione; audit immutabile come CG-4.
2. Checkout: per i loggati niente ri-accettazione Aurya; per i guest
   una riga con link ai documenti Aurya. Checkbox DINAMICA delle
   condizioni operatore (cancellation_policy + requisiti specifici
   per-servizio via terms_content promosso a "Requisiti e condizioni
   del servizio" in riga listino e wizard ritiro) solo se presenti.
3. Merchant legal per-store ridimensionato: autogen resta come
   informativa linkata, niente piu' obbligo di pubblicazione.
4. Estensione testi Aurya (bozza per revisione legale): titolarita'
   account/newsletter/marketplace, ruoli art. 28 con operatori.

Ordine aggiornato: AP2 (fatta) → AP1b → AP-L → AP4 (copy pass che
elimina anche "Passaporto") → AP5.

### AP3 — Ponte per-store dentro l'hub (corsi e asset)
1. Endpoint ponte POST /platform/me/store-session {org}: se esiste un
   customer_account linkato (claim P4) emette il customer JWT di
   quell'org (riuso create_customer_token); se non esiste e serve
   (corso comprato), lo crea come record interno senza password
   esposta, consensi snapshot autogen/pubblicati.
2. /account mostra corsi e download per-store come sotto-sezioni che
   usano il ponte dietro le quinte: l'utente vede UN account.
3. Il portale customer legacy resta vivo (retrocompatibilita' link
   email vecchi) ma non e' piu' proposto.

### AP4 — Pulizia UX e routing
1. /account = hub unico; /account/accedi = login unico. Le rotte
   customer (/account/login, /account/orders...) redirigono all'hub
   dove sensato; il player corsi resta sulla sua rotta col ponte.
2. Copy pass: mai "account del negozio"; sempre "il tuo account
   Aurya". Email claim/magic link riviste in questa chiave.

### AP5 — Piano test completo (richiesto dal founder)
Matrice E2E lato utente, ogni riga con guardia o test riproducibile:
1. Richiesta servizio dal profilo /o/ da guest: ordine + consensi +
   Passaporto pending + claim alla conferma + marketing nel CRM.
2. Acquisto diretto Stripe dalla landing /e/ (marketplace e profilo):
   ordine, redirect, claim al pagamento, ordine in /account.
3. Login magic link E login OTP: accesso, ordini cross-operatore
   visibili, tracking visibile su ordine spedito (fixture).
4. Iscritto newsletter confermato che fa login → guide sbloccate;
   non iscritto → invito; iscrizione da /account → double opt-in.
5. Corso acquistato → record interno creato → player accessibile
   dall'hub via ponte; niente password mai mostrata.
6. Errori onesti: signup impossibile (store inesistente), email gia'
   registrata, token scaduto, OTP sbagliato 5 volte (lockout).
7. GDPR: export e cancellazione da /account (due livelli), consensi
   per-store intatti, audit coerente.
8. Isolamento: due org, stesso cliente email → un solo Passaporto,
   due customer record, dati mai mescolati cross-org.
9. Regressione: storefront legacy, corsi via portale vecchio,
   re-consent CG-4, suite completa.

Ordine: AP0 → AP1 → AP2 → AP3 → AP4 → AP5 (i test si scrivono onda
per onda, AP5 e' il giro finale completo). Invarianti: motore ordini
e Stripe intoccati; customer_accounts mai fuso; email uniche globali
solo su platform e subscribers.

## Valore
Un solo account, zero password al checkout, tutti gli acquisti e le
guide in un posto, meccanismi email gia' collaudati riusati al 100%.
Il bug visto dal founder sparisce alla radice in AP0.
