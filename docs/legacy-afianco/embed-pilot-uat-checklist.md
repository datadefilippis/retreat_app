# Embed Widget — UAT Test Plan & Regression Checklist

> **Audience**: merchant pilot QA + dev team. Da eseguire prima del go-live e dopo ogni deploy.
> **Tempo stimato**: ~90 minuti per il full pass, ~20 minuti per smoke test rapido.

## Setup pre-test

### Environment

- [ ] Backend dev/staging running: `http://localhost:8000` o `https://api.afianco.app`
- [ ] Frontend dev running: `http://localhost:3000`
- [ ] Widget bundle aggiornato: `pnpm embed:rebuild` (build + sync)
- [ ] Bundle verificato: `frontend/public/embed/v1/afianco-embed.es.js` esiste
- [ ] Browser: Chrome + Safari + Firefox per cross-browser testing
- [ ] DevTools Console aperta in tutti i browser per catch errori

### Store di test setup

- [ ] Store pilot creato con slug `acme-pilot` (o equivalente)
- [ ] Admin merchant: ha accettato DPA (`/settings/legal/dpa`)
- [ ] Origin del widget aggiunta a `allowed_origins` (es. `http://localhost:8080`)
- [ ] `storefront_languages` configurato con `['it', 'en', 'de', 'fr']`
- [ ] Brand color, logo, custom_nav_links configurati
- [ ] Almeno 1 prodotto per ogni `item_type`:
  - [ ] 1 `physical` (es. "Coffee Bag 250g" €25)
  - [ ] 1 `digital` (es. "PDF Recipe Book" €15)
  - [ ] 1 `service` con `service_options` + availability slots (es. "Consulenza 1h" €100)
  - [ ] 1 `event_ticket` con `occurrence` + 2 tier (es. "Webinar 15/07")
  - [ ] 1 `rental` con date range flavor (es. "Sala Riunioni" €50/day)
  - [ ] 1 `course` con Bunny Stream video (es. "Course Excel Base" €97)
- [ ] Almeno 1 coupon attivo (es. `PILOT10` -10%)
- [ ] Almeno 2 shipping options configurate (Standard €5, Express €10)
- [ ] Free shipping threshold configurato (es. €100)

### Embed HTML test page

Crea `test-embed.html`:

```html
<!DOCTYPE html>
<html lang="it">
<head>
  <meta charset="UTF-8">
  <title>Pilot Test</title>
</head>
<body>
  <h1>AFianco Pilot Test</h1>
  <script type="module" src="http://localhost:3000/embed/v1/afianco-embed.es.js?v=20260606"></script>
  <afianco-storefront-init slug="acme-pilot" base-url="http://localhost:8000">
    <afianco-header></afianco-header>
    <afianco-account hide-trigger></afianco-account>
    <afianco-product-grid show-search></afianco-product-grid>
    <afianco-product-detail></afianco-product-detail>
    <afianco-cart-drawer hide-trigger></afianco-cart-drawer>
    <afianco-checkout-button></afianco-checkout-button>
  </afianco-storefront-init>
</body>
</html>
```

Servi via: `python3 -m http.server 8080` → apri `http://localhost:8080/test-embed.html`.

---

## TEST SUITE 1 — Smoke Test (20 min)

### S1. Bootstrap + Init

- [ ] Apri `test-embed.html` su Chrome → widget si carica entro 2s
- [ ] DevTools Console: zero errori rossi (warnings OK)
- [ ] DevTools Network: `GET /init/acme-pilot` ritorna 200 con `storefront_languages: ['it','en','de','fr']`
- [ ] Header mostra logo merchant + nome store + custom nav links + language switcher + account icon + cart icon
- [ ] Product grid mostra tutti i 6 prodotti di test
- [ ] Categorie pills visibili (se merchant ha categorie)
- [ ] Search bar visibile (clicca → input attivo)

### S2. Test rapido catalogo

- [ ] Click sulla card "Coffee Bag" → drawer detail si apre da destra
- [ ] Drawer mostra: image, name, price €25, description, qty stepper
- [ ] CTA mostra "Aggiungi al carrello"
- [ ] Click "Aggiungi al carrello" → drawer si chiude, badge cart aggiornato (1)
- [ ] Click icon cart → drawer cart si apre
- [ ] Cart mostra: 1 item, qty 1, totale €25, button "Procedi al checkout"
- [ ] Click "Procedi al checkout" → modal checkout si apre

### S3. Test rapido checkout

- [ ] Form mostra sezioni: Customer info, Fulfillment, Shipping option, Coupon, GDPR, Submit
- [ ] **Privacy Policy** e **Termini di Servizio** sono **cliccabili** (link blu sottolineato) → click apre nuova tab
- [ ] Inserisci dati: Nome "Test User", Email "test@example.com"
- [ ] Seleziona shipping option "Standard €5"
- [ ] Coupon: inserisci `PILOT10` → entro 500ms badge verde "Codice valido — sconto -€2.50"
- [ ] OrderSummary aggiorna: Subtotale €25, Sconto coupon -€2.50, Shipping €5, **Totale €27.50**
- [ ] Spunta Privacy + Termini checkbox
- [ ] Click "Procedi al pagamento" → popup Stripe checkout si apre (NON simulare pagamento — chiudi popup)
- [ ] Customer torna allo store → cart drawer riapre, modal checkout chiusa

---

## TEST SUITE 2 — Per Product Type (60 min)

### T1. Physical product order (Track 1)

#### Customer Journey

1. [ ] Apri widget → vedi "Coffee Bag" nella grid
2. [ ] Click card → drawer detail
3. [ ] Imposta qty=3, stock_hint mostra "Solo X disponibili" se stock<3
4. [ ] Click "Aggiungi al carrello" → cart badge mostra "3"
5. [ ] Apri cart → 1 item con qty 3, totale €75
6. [ ] Click "Procedi al checkout"
7. [ ] Compila form:
   - Nome: "Mario Rossi"
   - Email: "mario@test.com"
   - Telefono: "+39 333 1234567"
   - Fulfillment mode: **Spedizione**
   - Shipping address: tutti campi compilati (Via Roma 1, Milano, 20100, MI)
   - Shipping option: Standard
   - Note: "Consegna mattina"
   - GDPR Privacy + Terms checked
   - Marketing optional unchecked
   - **Crea account** checked + password "test1234"
8. [ ] Click submit → Stripe popup → simula pagamento ok (Stripe test card 4242 4242 4242 4242)
9. [ ] Post-payment: messaggio "Ordine completato. Grazie!"
10. [ ] Email confirma ricevuta da merchant
11. [ ] Customer login (account auto-creato) → vede order nel portale

#### Backend Verifications

- [ ] Admin merchant → Ordini → vede nuovo ordine con dati Mario Rossi
- [ ] Stripe dashboard → pagamento `succeeded`
- [ ] Customer accounts → "mario@test.com" creato con `gdpr_privacy_accepted=true`

---

### T2. Event ticket order (Track 2)

#### Customer Journey

1. [ ] Click "Webinar 15/07" card → drawer apre
2. [ ] **Occurrence picker** mostra le date disponibili con location + remaining capacity
3. [ ] Seleziona occurrence del 15/07
4. [ ] **Tier picker** appare: "Standard €25" + "VIP €50"
5. [ ] Seleziona "Standard" qty=2 + "VIP" qty=1
6. [ ] Drawer total mostra €100 (25*2 + 50*1)
7. [ ] Click "Acquista biglietto"
8. [ ] Cart mostra 3 line items (1 per tier slot)
9. [ ] Click "Procedi al checkout"
10. [ ] Form aggiuntivo: sezione **Dati partecipanti** (3 partecipanti)
11. [ ] Compila per ogni partecipante: nome + email + (optional phone)
12. [ ] Stripe pay → completa
13. [ ] Email ricevuta con QR code biglietti + .ics calendar attachment

#### Backend Verifications

- [ ] Admin → Ordini → 1 ordine con 3 ticket records (uno per attendee)
- [ ] occurrence.booked_count incrementato di 3
- [ ] Tier.remaining decrementato correttamente

---

### T3. Service slot booking (Track 3)

#### Customer Journey

1. [ ] Click "Consulenza 1h" card → drawer
2. [ ] **Service options picker** mostra: "Online €100" / "In-person €150"
3. [ ] Seleziona "Online"
4. [ ] **Availability picker** carica calendar (settimana prossima)
5. [ ] Clicca data → slot della giornata appaiono
6. [ ] Seleziona slot "10:00-11:00"
7. [ ] CTA abilitato → click "Aggiungi al carrello"
8. [ ] Checkout → conferma slot nel review summary
9. [ ] Stripe pay → completa
10. [ ] Email confirma con appointment details + .ics

#### Backend Verifications

- [ ] booking record creato con `booking_date`, `booking_start_time`, `service_option_id`
- [ ] Slot rimosso dalla disponibilità (anti-double-booking)

---

### T4. Course order (Track 4)

#### Customer Journey

1. [ ] Click "Course Excel Base" card → drawer
2. [ ] **Course preview** mostra: badge "Accesso a vita", "12 Lezioni", "4h 30min", hint "Dopo acquisto…"
3. [ ] **NO add to cart se guest** — drawer mostra hint "Crea account o accedi prima"
4. [ ] Inline signup nel checkout form (checkbox "crea account")
5. [ ] Stripe pay → completa
6. [ ] Customer auto-loggato + portale apre con tab "I miei corsi"
7. [ ] Click corso → curriculum + click lezione 1 → Bunny Stream player carica video
8. [ ] Progress heartbeat ogni 30s (verifica DevTools Network)

#### Backend Verifications

- [ ] enrollment record creato con `access_policy='lifetime'`
- [ ] Bunny signed URL TTL 15min (verifica `expires_at` query param)
- [ ] progress record con `position_seconds` aggiornato

---

### T5. Rental order (Track 5)

#### Customer Journey

1. [ ] Click "Sala Riunioni" card → drawer
2. [ ] **Date range picker** appare con today come minimo
3. [ ] Seleziona "from: today+3" / "to: today+5" (3 giorni)
4. [ ] Price preview aggiorna: €50 × 3 giorni = €150
5. [ ] Extras opzionali per_day se configurati
6. [ ] Click "Noleggia" → cart
7. [ ] Checkout normale → Stripe pay
8. [ ] Email confirma rental con date + .ics

#### Backend Verifications

- [ ] reservation record con `date_from` + `date_to`
- [ ] Calendar bloccato per quelle date (verifica `/reservations/blocked-dates`)

---

### T6. Digital download order (Track 6)

#### Customer Journey

1. [ ] Click "PDF Recipe Book" card → drawer
2. [ ] CTA "Acquista" → cart
3. [ ] Checkout → Stripe pay
4. [ ] Email con link download signed URL
5. [ ] Customer login portale → "I miei download" → click "Scarica" → file scaricato
6. [ ] Re-click "Scarica" → conta download (max N se configurato)
7. [ ] Dopo TTL: badge "Scaduto", link disabilitato

---

## TEST SUITE 3 — i18n + Locale (10 min)

### I1. Language switcher

- [ ] Widget mostra language switcher in header (dropdown 🌐)
- [ ] Click switcher → menu apre con 4 opzioni: Italiano, English, Deutsch, Français
- [ ] Click **English** → entro 100ms TUTTO traduce:
  - Header: "Cart" / "Sign in"
  - Cart drawer: "Your cart", "Proceed to checkout"
  - Product cards CTA: "Discover more"
  - Drawer detail: "Quantity", "Add to cart"
  - Checkout: "Complete order", "Privacy Policy", "Terms"
  - Empty states e error messages
- [ ] Click **Deutsch** → tutto in tedesco (Warenkorb, In den Warenkorb, ecc.)
- [ ] Click **Français** → tutto in francese (Panier, Ajouter au panier, ecc.)
- [ ] Click **Italiano** → torna in italiano

### I2. Locale persistence

- [ ] Imposta lingua = Français
- [ ] Hard refresh browser (Cmd+Shift+R)
- [ ] Widget riapre → ancora in francese (localStorage persist)

### I3. Browser language auto-detect

- [ ] Imposta browser language = `de-DE` (Chrome Settings → Languages)
- [ ] Apri widget senza localStorage cleared
- [ ] Widget auto-seleziona Deutsch al primo caricamento

### I4. Locale propagation merchant change (W4.4-W4.6)

- [ ] Admin merchant → modifica `storefront_languages` rimuovendo `fr`
- [ ] Save nell'admin
- [ ] Tab widget aperto entro 90 secondi → polling re-fetcha init
- [ ] Se customer era su `fr`, locale forza fallback a default merchant
- [ ] Dropdown switcher aggiorna (mostra 3 lingue invece di 4)

---

## TEST SUITE 4 — Regression W1-W4 (15 min)

### R1. DPA enforcement (W1.1)

- [ ] Crea **nuovo** store admin (no DPA acknowledged)
- [ ] Click "Pubblica store" → ricevi 412 con message DPA required
- [ ] Vai a `/settings/legal/dpa` → leggi + accetta
- [ ] Torna allo store → ora pubblicazione succeeds

### R2. GDPR Erasure React (W1.2)

- [ ] Login customer su React storefront `/account`
- [ ] Tab Profilo → scroll down → vede "Cancellazione account (GDPR Art. 17)"
- [ ] Click "Procedi alla richiesta di cancellazione"
- [ ] Form appare: warning + reason + email re-type + confirm checkbox
- [ ] Email re-type mismatch → button disabled
- [ ] Email match + checkbox → button enabled
- [ ] Click submit → success banner verde + request_id

### R3. Idempotency-Key SDK (W1.3)

- [ ] DevTools Network → POST `/cart` o `/checkout/start`
- [ ] Headers tab → vede `Idempotency-Key: <uuid-v4>`
- [ ] Replay manualmente la stessa request → backend cached response (no duplicate)

### R4. Catalog projection no leak (W1.4)

- [ ] DevTools Network → `GET /products/{slug}` response JSON
- [ ] Verifica response NON contiene: `cost_price`, `cost_source`, `supplier_id`, `internal_tags`, `sku`, `barcode`

### R5. Markdown XSS sanitize (W1.5)

- [ ] Admin: crea product con description: `<script>alert(1)</script>OK testo`
- [ ] Save → riapri admin → description mostra solo "OK testo" (script stripped)
- [ ] Widget product card: description NON triggera alert

### R6. Privacy/Terms cliccabili + auto-fallback (E7.4 + E7.5)

- [ ] Admin: rimuovi published privacy policy (status → not_configured)
- [ ] Widget: customer apre checkout → click "Privacy Policy" link
- [ ] Atterra su `/s/{slug}/privacy` con **banner azzurro "Documento generato automaticamente"** + contenuto template auto-popolato
- [ ] Admin: pubblica privacy custom → click link → contenuto custom merchant

### R7. Cart merge guest → auth (W2.6)

- [ ] Guest: aggiungi 2 items al cart (3 e 4 quantity)
- [ ] Guest fa login (esistente customer con cart vuoto)
- [ ] Entro 1 secondo: cart drawer aggiorna → items persistono
- [ ] DevTools: vedi `POST /cart/{guest_id}/merge` chiamato

### R8. Coupon dry-run React (W2.1)

- [ ] React storefront `/s/{slug}` → aggiungi prodotto → vai a checkout
- [ ] Inserisci codice coupon → entro 500ms badge verde/rosso con feedback
- [ ] OrderSummary aggiorna con sconto

### R9. Search bar React (W2.4)

- [ ] React storefront → input search "coffee" → grid filtra
- [ ] Empty state se zero match
- [ ] Clear X reset

### R10. Bundle sync drift (E7.6)

- [ ] Esegui `diff -q apps/embed-sdk/dist/*.es.js frontend/public/embed/v1/*.es.js`
- [ ] Output vuoto (file identici)
- [ ] Bundle gzip <105 KB

---

## TEST SUITE 5 — Edge Cases & Errors (10 min)

### E1. Network errors

- [ ] Backend offline → widget mostra error banner "Storefront non pronto"
- [ ] Network throttle 3G → widget loads <5s

### E2. Validation errors

- [ ] Checkout submit con email invalida → error inline + form non si submitta
- [ ] Coupon inesistente → badge rosso "Codice non valido"
- [ ] Shipping address incompleto → error "Compila tutti i campi"

### E3. Edge UX

- [ ] ESC chiude drawer (cart, account, product detail)
- [ ] Click esterno scrim chiude drawer
- [ ] Drawer scroll funziona su contenuto lungo
- [ ] Cart vuoto → empty state + no checkout button

### E4. Rate limit

- [ ] Spam click "Applica coupon" 10x veloce → backend rate limit OK
- [ ] Login con password errate 5x → account locked + countdown timer

### E5. Multi-browser

- [ ] Chrome desktop ✓
- [ ] Safari desktop ✓
- [ ] Firefox desktop ✓
- [ ] iOS Safari mobile ✓
- [ ] Android Chrome mobile ✓

---

## Sign-off

- [ ] **Suite 1 (Smoke)** — PASS
- [ ] **Suite 2 (Product types)** — PASS (6/6 types)
- [ ] **Suite 3 (i18n)** — PASS (4 lingue verified)
- [ ] **Suite 4 (Regression W1-W4)** — PASS (10 items)
- [ ] **Suite 5 (Edge cases)** — PASS

**Tester**: ___________________
**Data**: ___________________
**Bundle version**: ___________________
**Commit SHA**: ___________________

**Note bugs encountered**:
```
[Compila qui]
```

**Decision**: 
- [ ] GO per pilot launch
- [ ] NO-GO, blocker bugs above
- [ ] GO con caveat (specifica nei note)
