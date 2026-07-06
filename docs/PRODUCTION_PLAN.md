# Piano di produzione — analisi olistica della piattaforma (10 luglio 2026)

Quattro audit paralleli sull'intera codebase (residui brand, email
transazionali, codice obsoleto, scalabilità/production readiness) +
verifiche dirette. Questo documento è LA lista per andare in produzione:
niente qui dentro è opinione, ogni voce ha file:riga negli audit.

## Fotografia onesta della piattaforma

**Cosa è già solido** (non va rifatto):
- Motore soldi provato con pagamenti veri: caparre, dunning, rimborsi,
  webhook con firma+idempotenza, direct charges per-org con fee da piano.
- Suite a 4146 test verdi; kill-list dei moduli via piano (zero if nel
  codice); scheduler con lock distribuito; backup cifrati (age, 30gg);
  Sentry con scrubbing PII; health endpoints; rate limit su 20+ endpoint.
- Marketplace completo: directory geografica, landing vetrina, doppio
  guscio store/marketplace, Passaporto con OTP, multilingua manuale 4
  lingue, onboarding operatore.
- Codebase pulita: 94,5% del codice è attivo; il fork da AFianco è
  gestito con fallback ordinati, non con rovine.

**I numeri degli audit**: 39 email transazionali (15 col brand vecchio,
12 con lacune i18n); ~15 file con residui AFianco user-visible; ~2.150
LOC + 2,5MB di dipendenze rimovibili subito (fascia A); 3 bloccanti di
scalabilità; voto production-readiness 6.4/10 → target 9.

---

## R1 · Rebranding totale (1 gg) — SBLOCCATO DAL NOME (decisione founder)

Il nome va scelto PRIMA: tutto il resto di R1 lo indossa. Nel frattempo
il lavoro è preparabile con le costanti.
- [ ] **Backend brand config** (`core/brand.py`): BRAND_NAME,
      BRAND_FROM_EMAIL, BRAND_SUPPORT_EMAIL, BRAND_TAGLINE — speculare a
      frontend/src/config/brand.js. Tutti i punti sotto leggono da qui.
- [ ] email_service.py: SMTP_FROM_NAME/EMAIL (oggi "AFianco"
      <davide@afianco.ch>), subject e body in 4 lingue (~15 email),
      footer "Gestione finanziaria per PMI" → tagline ritiri, header
      fallback <h1>AFianco</h1>.
- [ ] **Pagine legali** (4 lingue, legal.json): citano "afianco" —
      user-visible E legalmente sbagliate. Vanno riscritte col nome
      nuovo e riviste nel merito (siamo un marketplace, non un
      gestionale: la privacy deve descrivere Passaporto, ordini
      cross-operatore, geolocalizzazione on-click).
- [ ] Frontend residui: AuthShell "by AFianco", UpgradeDialog/PlansPage
      (copy + mailto support@afian.co), StoreSettings "via AFianco",
      products.json "afianco.app".
- [ ] File scaricabili: afianco_report.pdf, afianco_export_*.zip,
      prenotazione-*-afianco.ics → nome nuovo.
- [ ] server.py: title OpenAPI "AFianco", service tag nei log.
- [ ] Cookie/storage: afianco_cart_id (cookie+localStorage),
      afianco_cookie_disclosure — rinomina CON migrazione (leggere la
      chiave vecchia una volta, scrivere la nuova; mai perdere carrelli).
- [ ] seed dev: "Demo Restaurant" → nome coerente.
- **DoD**: grep -ri "afianco" su frontend/src + backend (esclusi
  docs/test) = zero righe user-visible.

## R2 · Redesign email transazionali (1,5 gg)

39 email, layout tecnico comune ma design vecchio (header blu #4f5dca).
- [ ] **Nuovo template base** (_wrap_template + _BASE_STYLE): palette
      Salvia&Terracotta, wordmark, footer marketplace, bottoni coerenti
      con la UI. UNA modifica veste tutte le 39.
- [ ] Revisione copy per gruppo: auth operatore (7), auth cliente store
      (5), ordini (5), pagamenti/dunning (4), biglietti/broadcast (7),
      alert operativi (4), quote (2), inviti (3), prenotazioni (1),
      Passaporto (1+OTP).
- [ ] **Fix i18n**: sollecito at-risk operatore (hardcoded it), conferma
      prenotazione (hardcoded it), magic link/OTP Passaporto (da
      localizzare in 4 lingue — è l'email più vista dai viaggiatori).
- [ ] Email mancanti da valutare: conferma rimborso esplicita al
      cliente; benvenuto Passaporto post-claim.
- [ ] Test di resa: invio reale via Brevo di 5 email campione (Gmail,
      Apple Mail, Outlook) prima del lancio.
- **DoD**: ogni email col brand nuovo, 4 lingue, stessa faccia della
  piattaforma; matrice email in un doc (EMAILS.md) come fonte unica.

## R3 · Bloccanti di scalabilità (1 gg)

- [ ] **Upload su object storage**: oggi filesystem locale
      (/uploads/...) — zero multi-istanza, zero replica. Adapter S3
      compatibile (Hetzner/Scaleway Object Storage, gratis-quasi) con
      fallback locale in dev; migrazione one-off degli asset esistenti.
- [ ] **to_list(None) → cap**: 10 endpoint (orders.py:382,
      products.py:516/531, public.py:2363/2407/3035, service_options,
      shipping_options, product_extras, embed_public) → limit espliciti.
- [ ] **Indici mancanti**: availability_rules(org+product),
      blocked_slots (hot path del checkout servizi) + guard-test.
- **DoD**: nessuna query unbounded; upload funzionanti con 2 istanze.

## R4 · Alleggerimento (0,5 gg — fascia A dell'audit, rischio zero)

- [ ] Rimozione AI legacy: routers chat/digests/insights + services/llm
      (~2.150 LOC) + dipendenza `anthropic` (2,5MB) + AnalisiAIPage.
      (La kill-list dei piani già li spegne: si toglie il cadavere.)
- [ ] PosPage (POS in-person: zero use case ritiri).
- [ ] TTL Mongo su ai_usage_events (90g) e chat_sessions (30g).
- [ ] Fascia B (alerts/datasets/insights) NON si tocca: disattivata dal
      piano, riattivabile senza codice. Fascia C (public_slug fallback,
      booking→rental) resta finché migrazione completa.
- **DoD**: suite verde dopo la potatura; requirements più snello.

## R5 · Hardening produzione (1 gg + operativo)

- [ ] Rate limit espliciti su webhook Stripe/Brevo (oggi default 60/min).
- [ ] /api/metrics Prometheus-style (latency/throughput) — Sentry copre
      solo gli errori.
- [ ] **Route /termini mancante** (il footer marketplace ci punta → 404)
      + contenuti legali definitivi (vedi R1).
- [ ] Config produzione: PUBLIC_APP_URL/FRONTEND_URL/CORS su dominio
      vero, cookie Secure/SameSite in prod, JWT/secret rotation
      documentata.
- [ ] Operativo (fuori dal codice, decisioni founder): dominio + DNS +
      SSL, VPS/host, chiave Brevo LIVE (le 39 email oggi sono dry-run!),
      Stripe LIVE + onboarding Connect reale operatori, backfill_geo in
      prod, pip-audit/CI.
- **DoD**: checklist deploy scritta ed eseguita su staging.

## R6 · QA pre-lancio (1 gg)

- [ ] E2E su staging con Stripe LIVE-test: il giro completo directory →
      caparra su pagina Stripe hosted VERA (il harness dev non può) →
      webhook reale → biglietti → email reali → Passaporto.
- [ ] Resa email nei client reali (R2), giro mobile completo, 404/edge
      (link condivisi, slug inesistenti, token scaduti).
- [ ] Mini security pass: headers (CSP/HSTS), enumeration sui nuovi
      endpoint, permessi upload.
- **DoD**: una prenotazione vera fatta dal telefono del founder, email
  ricevute belle, biglietto in mano.

---

## Cosa manca al PRODOTTO (non al codice) — decisioni founder
1. **Il nome** (blocca R1/R2 e il dominio).
2. Testi legali definitivi (privacy/termini da marketplace).
3. Contenuti veri: foto reali dei ritiri (le demo sono placeholder),
   bio operatori curate — il design nuovo rende quanto le foto.
4. Prezzo/fee finali confermati e pagina piani pubblica.
5. Recensioni: dopo il lancio (slot già predisposto).
6. Interviste organizzatori (gate business mai partito — resta il
   rischio più grande: il lato OFFERTA).

## Ordine consigliato e stima
R3 (scalabilità, non dipende dal nome) → R4 (potatura) → R5 (hardening)
in parallelo alla decisione nome → R1 (rebrand) → R2 (email) → R6 (QA).
**Totale: ~6 giorni di lavoro** + le decisioni/operazioni founder.
Al termine: production-ready senza asterischi.
