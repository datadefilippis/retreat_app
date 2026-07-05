# Account unico piattaforma («Passaporto Ritiri») — piano (5 luglio 2026)

Richiesta founder: nell'aggregatore /ritiri un utente finale deve poter creare
UN solo account e comprare da più operatori, senza un account per ogni store.
A livello di singolo store il processo resta ESATTAMENTE com'è.
(È la Fase 5.4 del master plan, differita — il marketplace la rende necessaria.)

## 0 · Fotografia dell'esistente (verificata nel codice)

- `customer_accounts` è **org-scoped by design**: stessa email può registrarsi
  su org diverse in modo indipendente (`models/customer_account.py`). Questo È
  l'isolamento giusto per il CRM dell'operatore — non si tocca.
- Il checkout pubblico funziona **guest-first** (nome+email), account opzionale.
- Gli ordini linkano `customer_account_id` (org-scoped); i corsi lo richiedono.
- Portal cliente per-org: /me, /orders, sessioni con logout-all, flussi
  verify/reset enumeration-safe (202).

## 1 · Architettura: identità sopra, CRM sotto (isolata e scalabile)

**Principio: due livelli con responsabilità separate, linkati, mai fusi.**

```
platform_accounts (NUOVO)          ← identità dell'utente finale, 1 per email
   │  (platform_account_id)           titolare: la piattaforma
   ├── customer_accounts org A     ← CRM dell'operatore A (ESISTENTE, intatto)
   ├── customer_accounts org B     ← CRM dell'operatore B
   └── orders.platform_account_id  ← stamp denormalizzato per "i miei ritiri"
```

- **`platform_accounts`** (collection nuova): email unica a livello
  piattaforma, nome, telefono, lingua, consensi. Auth **magic-link-first**
  (password opzionale dopo): il flusso più snello possibile.
- **Al primo acquisto presso l'operatore X**: find-or-create del
  `customer_account` org X con `platform_account_id` valorizzato. L'operatore
  continua a vedere SOLO il suo record e i suoi ordini — l'isolamento
  organizzativo non cambia di un millimetro.
- **Ordini**: nuovo campo `platform_account_id` (stamp alla creazione) →
  l'area personale aggrega cross-operatore con una query, senza join.
- **Sessioni separate**: token piattaforma con audience dedicata — zero
  interferenza con le sessioni store org-scoped (possono coesistere).

**Perché è isolato**: modulo nuovo (`routers/platform_accounts.py` +
`services/platform_account_service.py` + collection nuova); i flussi store
esistenti non vengono toccati; feature flag per accensione graduale.
**Perché è scalabile**: identità piatta 1-per-email, stamp denormalizzato
sugli ordini, niente migrazione distruttiva dei customer esistenti.

## 2 · Il flusso utente (snello davvero)

**Acquisto dal marketplace (nuovo):**
1. /ritiri → landing → checkout: SEMPRE guest-friendly (nome+email — come ora).
   Se già loggato in piattaforma: campi precompilati, un click in meno.
2. Dopo il pagamento: email "Gestisci le tue prenotazioni" con **magic link**
   → l'account piattaforma nasce/aggancia QUI, a valle dell'acquisto.
   Nessuna registrazione obbligatoria prima di pagare: zero attrito, zero
   carrelli persi.
3. Acquisti successivi da QUALSIASI operatore: stessa identità, prefill,
   tutto in un posto.

**Area personale /account (piattaforma):**
- I miei ritiri (tutti gli operatori): prossimi e passati
- Pagamenti: caparre versate, saldi in scadenza con i link /pay/{token}
  (già eterni) — un solo posto per pagare tutto
- Pass QR / biglietti · Profilo e consensi

**Single store (/s/:org)**: invariato al 100% — guest checkout + account
org opzionale, come oggi.

## 3 · GDPR e titolarità (da decidere bene ORA, non dopo)

- **Piattaforma** = titolare dell'account piattaforma (identità, credenziali).
- **Operatore** = titolare del SUO CRM (il customer record org-scoped) per le
  sue prenotazioni — modello già coerente con Stripe Connect (vende l'operatore).
- **Consenso marketing PER OPERATORE**, mai globale: comprare da A non
  autorizza B a scriverti. Newsletter/consensi restano org-scoped.
- Export/cancellazione a due livelli: cancellare l'account piattaforma
  scollega i link ma NON cancella i dati fiscali/ordini degli operatori
  (obblighi di legge loro); registro consensi con snapshot (pattern esistente).

## 4 · Fasi (isolate, ognuna mergiabile e testabile da sola)

### P1 · Fondamenta identità ✅ (fatto 5/7/2026 — merge su main)
- [ ] Modello `platform_accounts` + indici (email unica, case-insensitive)
- [ ] Auth magic-link: request → email con token one-shot TTL 15' →
      sessione; rate-limit + enumeration-safe (pattern 202 esistente);
      password opzionale (set dopo, mai richiesta al primo giro)
- [ ] Sessioni piattaforma (audience dedicata, logout-all)
- [ ] Test sicurezza: nessun endpoint piattaforma espone dati org; nessun
      endpoint org accetta token piattaforma
- **DoD**: signup/login magic link funzionante dietro feature flag, suite verde.

### P2 · Aggancio acquisto (~2-3 gg)
- [ ] Checkout: se sessione piattaforma → prefill nome/email/telefono
- [ ] Post-acquisto: email "gestisci le tue prenotazioni" con magic link
      (riuso template transazionali Brevo); claim = verifica email implicita
- [ ] `create_order`: stamp `platform_account_id` (se noto) + find-or-create
      `customer_account` org linkato
- [ ] Ordini corsi: account org auto-creato e linkato (oggi è il punto più
      attritivo — l'utente piattaforma non deve accorgersene)
- **DoD**: compro da 2 operatori con la stessa email → 1 account piattaforma,
  2 customer org linkati, entrambi gli ordini stampati.

### P3 · Area personale /account (~3 gg)
- [ ] Pagina /account: i miei ritiri cross-operatore (prossimi/passati),
      saldi in scadenza con /pay links, pass QR, profilo
- [ ] SEO-safe: noindex; mobile-first (si apre dal telefono, dall'email)
- **DoD**: utente con acquisti da 2 operatori vede tutto in una pagina e
  paga un saldo da lì.

### P4 · Linking retroattivo + hardening (~2 gg)
- [ ] Claim ordini passati: al primo login, link automatico dei
      customer_accounts esistenti con stessa email VERIFICATA
- [ ] Consensi/GDPR: registro, export, cancellazione a due livelli
- [ ] Test cross-org: l'operatore A non vede MAI acquisti presso B;
      l'area personale non espone dati interni operatore
- **DoD**: security review del modulo passata, docs GDPR aggiornati.

Totale: **~2 settimane**, parallelizzabile in parte con la Fase 6 (infra).

## 5 · Cosa NON facciamo
- NON fondiamo i customer_accounts esistenti (nessuna migrazione distruttiva)
- NON tocchiamo il flusso single-store (esplicitamente richiesto)
- NON obblighiamo la registrazione prima del pagamento (guest-first resta)
- NON introduciamo password obbligatorie (magic link first; password opt-in)

## 6 · Decisioni founder richieste prima di partire
1. **Magic-link-first** confermato? (raccomandato: sì — zero attrito)
2. L'area personale vive sul **dominio piattaforma** (es. app.dominio/account)
   — ok? (i link nelle email transazionali punteranno lì)
3. Priorità: P1-P4 **prima** della Fase 6 (produzione), **dopo**, o in
   parallelo? (raccomandato: in parallelo — P1/P2 subito, P3/P4 mentre
   si prepara l'infra; il marketplace al lancio DEVE già avere l'account
   unico, è la sua promessa di base)
