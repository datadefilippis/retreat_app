# Audit olistico round 2 — parità commerce A/B/C + refinement

> Data 2026-06-19. Fronti: **A** = storefront su URL afianco · **B** = embed intero
> (`<afianco-storefront-init>`) · **C** = embed à-la-carte (componenti singoli).
> Verdetto: **sicurezza alta, parità del cuore transazionale RAGGIUNTA**
> (A/B/C condividono `submit_order_from_storefront`→`create_order`→Stripe; C=B per
> costruzione). Trovati **bug condivisi pre-esistenti** (non causati dall'embed) e
> debito strutturale. Nessun CRITICO/ALTO di **sicurezza**.

## 🔴 CRITICI (correttezza incasso — condivisi A=B=C)
- **R1 — Stripe non addebita shipping/coupon/extra.** `payment_checkout_service.py:183-190`
  costruisce i line_items SOLO da `unit_price×qty`. `order.total` include shipping
  (folded `order_service.py:381`) e sottrae `discount_total`, ma Stripe non li vede.
  → con coupon il cliente paga **più** del totale scontato; lo shipping **non** è
  incassato. **Verificato.** Fix nel service condiviso (line item shipping + extras +
  mappare coupon su Stripe discount/negative item, currency-safe).
- **R2 — Extra optional/radio persi dal checkout.** `OrderRequestItem` non dichiara
  `extra_selections` (`public.py:270`, Pydantic `ignore`) e non viene propagato a
  `OrderLineCreate` (`order_creation_service.py:397`, `public.py:2963`). Nell'embed la
  catena si rompe già a monte (`afianco-product-detail.ts:440` → `afianco-cart-drawer.ts`
  newItem non mappa extras → `CartItemInput` privo del campo → `embed_public.py:1893`).
  Solo gli extra **mandatory** entrano nell'ordine. Il price-preview li mostra →
  **prezzo mostrato ≠ pagato**. Fix: aggiungere `extra_selections` a `OrderRequestItem`
  + a `CartItem/CartItemInput` + propagarlo in entrambe le mappature → `OrderLineCreate`.

## 🟠 Parità: feature presenti su storefront, mancanti/parziali su embed
- **R3 — Rental nell'embed senza `blocked-dates` né `availability-windows`** (durata
  variabile Onda 17). Storefront: `public.py:2494/2006`. Embed: endpoint assenti,
  `afianco-date-range-picker.ts` MVP → il cliente può scegliere date già occupate
  (rifiuto solo a confirm).
- **R4 — `service_custom_request`** (data/ora preferita fuori calendario): assente
  nell'embed; nello storefront è validato ma **non persistito** su `OrderLineCreate`.

## 🟡 Sicurezza — hardening (nessuno sfruttabile oggi)
- **R5** Coupon: nessun limite **per-cliente** + `current_uses` incrementato pre-pagamento
  (ordine Stripe abbandonato consuma uno slot, no rollback) → abuso coupon promozionali.
- **R6** iframe live-preview `allow-scripts allow-same-origin` su origin admin
  (`EmbedComposer.jsx`): difesa in profondità → servire da sotto-dominio sandbox
  (era B7 deferred).
- **R7** Rate-limit slowapi **in-memory**: con multi-replica il limite è per-istanza
  (Nx). → Redis store quando si scala. (Mitigato da nginx oggi.)
- **R8** `store_embed.py` admin usa `require_admin` ma non `get_verified_user`
  (asimmetria con la policy verified-gate).
- **R9** Price-preview storefront (`public.py:3635`) non scopa per `organization_id`
  (info-leak minore prezzo cross-tenant; l'embed lo scopa già).

## 🟢 Struttura / scalabilità
- **R10** Rimuovere il **legacy path** in `public.py:2642-3385` (~700 righe, gated da
  `USE_ORDER_CREATION_SERVICE`, "remove after 14 days" → sono 3 settimane). È il punto
  #1 di drift (B3 applicato in 2 posti).
- **R11** Catalogo/lettura prodotti **duplicato**: `public.py:664-1080` reimplementa
  proiezione/categorie/sort/N+1 già in `embed_init_service`. → estrarre `catalog_service`
  condiviso.
- **R12** Nessun **contract-test** backend↔`shared-types` (i tipi TS proteggono solo
  l'embed; lo storefront può divergere). → snapshot/OpenAPI-gen.
- **R13** `_resolve_org` (`public.py:408`) non cachato: 2 query × ogni endpoint, ~10
  round-trip per cold-load widget. → TTL-cache / per-request memo.
- **R14** `X-API-Version` solo su embed; `PublicShippingOption`/`EmbedShippingOption`
  mirror manuale; cache `/meta` (60s no-ETag) vs `/init` (300s+ETag). Allineare o
  documentare.

## ✅ Confermato SOLIDO (preservare)
- **Account/ordini/biglietti/corsi/download**: stessi endpoint `/customer/*` per
  storefront ed embed → sicurezza+logica uniformi per costruzione. Nessun IDOR.
- **Video corsi**: enrollment ri-verificato al play (6 controlli), URL firmati TTL 2h,
  `bunny_video_guid` mai esposto, niente accesso a corsi non acquistati.
- **Pipeline ordini** condivisa (prezzi server-authoritative, order_fields/attendee/
  tier/occurrence/rental/booking, GDPR/T&C). **Coupon (B3)** allineato A=B/C.
- **CORS/preview-token (B1/B2)**, multi-tenant, auth admin/customer, anti-phishing
  return-url, Stripe keys/webhook: tutti corretti.

## Ordine di refinement consigliato
R1 (incasso) → R2 (extra) → R3/R4 (parità rental/service) → R10 (legacy) → R5 (coupon)
→ R11/R13 (catalog/cache) → R6 (iframe) → R8/R9 → R7/R12/R14.
Ogni fix nei **service condivisi** per mantenere A=B=C; ogni step con test sentinella.

---

# Piano di refinement strutturato

## Principi (i 5 requisiti, come si esegue ogni step)
- **Strutturato** — 5 ondate per tema; ogni R è un commit atomico con un solo scopo.
- **Isolato** — modifica piccola e additiva; il fix vive nel **service condiviso** così
  copre A/B/C in un punto solo (niente patch duplicate); flussi esistenti intatti finché
  il test sentinella non prova il nuovo invariante.
- **Scalabile** — single-source (estrazione `catalog_service`, cache `_resolve_org`),
  niente logica per-fronte.
- **Sicuro** — sempre fail-closed; le fix "money" (R1/R2) sono coperte da test che
  pinnano `incassato == order.total`; nessun controllo indebolito.
- **Mantenibile** — rimozione duplicazioni (R10 legacy, R11 catalog), contract-test
  (R12); i test fanno da documentazione vivente.

Regola trasversale: **un solo punto di verità**. Se un fix richiede 2 edit (es. legacy +
service), o si unifica prima (R10) o si pinna con un test che confronta i due output.

## Ondata 1 — Correttezza incasso (money) 🔴
### R1 — Stripe addebita shipping + extra + sconto coupon — ✅ FATTO
> `_build_checkout_lines` (payment_checkout_service): line item per riga = `line_total`
> (incl. extra) + riga Spedizione; sconto via Stripe coupon one-off (provider) + fee sul
> netto. Invariante `Σ(line_items)−discount==order.total` (test_r1_checkout_lines.py, 3).
> 244 backend verdi. TODO pre-prod: smoke Stripe test-mode (coupon su connected account).

- **Fix**: in `payment_checkout_service` costruire i line_items così che
  `Σ(line_items) − discounts == order.total`: (a) line item prodotto per riga; (b) line
  item "Spedizione" se `shipping_cost>0`; (c) extras per-riga (fold nell'unit_amount di
  riga o line item dedicato); (d) coupon → Stripe `discounts:[{coupon}]` (coupon one-off
  `amount_off=discount_total`) **oppure** sconto proporzionale sulle righe. Currency in
  centesimi, rounding controllato.
- **File**: `services/payment_checkout_service.py:183`, `payment_providers/stripe/*`,
  input da `order` (subtotal/discount_total/shipping/extras_total).
- **Test**: sentinella che, dato un order con shipping+coupon+extra, verifica
  `Σ line_items − discounts == order.total` (mock provider). Edge: solo prodotti, solo
  shipping, solo coupon, coupon che azzera.
- **Isolamento/rischio**: ALTO (Stripe/incasso) → test rigorosi + verifica in test mode.
  Unico punto (service) → A=B=C automatico.

### R2 — Propagazione `extra_selections` fino all'ordine — ✅ FATTO
> Campo aggiunto a OrderRequestItem/OrderLineCreate (mapping service+legacy) +
> CartItem/CartItemInput + cart_service + embed cart→OrderRequestItem + shared-types
> (CartItem/Input) + cart-drawer (snapshot/newItem/update). Test
> test_r2_extras_propagation.py (3) + cart-drawer INV-CD-5d. 101 backend verdi.
> NB: l'addebito effettivo su Stripe dipende da R1.

- **Fix**: aggiungere `extra_selections` a `OrderRequestItem` (`public.py`) e propagarlo a
  `OrderLineCreate` in **entrambe** le mappature (`order_creation_service.py:397` +
  legacy `public.py:2963`, o solo service dopo R10); embed: aggiungere il campo a
  `CartItem/CartItemInput` (`models/cart.py`) e mapparlo in `afianco-cart-drawer.ts`
  (newItem) + `embed_public.py:1893` (cart→OrderRequestItem). `create_order` già calcola
  `extras_total`.
- **Test**: backend — order con extra optional/radio → `extras_total` e `order.total`
  includono gli extra. SDK — cart-drawer addItem con extras → presenti nel PATCH body.
- **Isolamento/rischio**: MEDIO. Dipende da R1 per il pieno effetto sull'incasso.

## Ondata 2 — Parità feature embed 🟠
### R3 — Rental embed: blocked-dates + availability-windows — ✅ FATTO
- **Fix attuato**:
  - Backend: estratto `get_rental_blocked_dates(org, product_id, from, to)` in
    `services/slot_generator.py` (single source of truth); `public.py` (storefront)
    refactorato per usarlo → A=B garantito by construction. Due endpoint embed
    `GET /public/embed/products/{slug}/{id}/blocked-dates` e `/availability-windows`
    (rate-limit 30/min, scoped via `_resolve_org`, `_embed_rental_product_match`),
    che **riusano** gli stessi service dello storefront.
  - api-client: metodi `embed.getRentalBlockedDates({from,to})` →
    `{ blocked_dates: string[] }` e `getRentalAvailabilityWindows({days})`.
  - SDK: `afianco-product-detail.ts` precarica best-effort le blocked-dates per
    rental flavor=range (orizzonte 365gg) e le passa via `.blockedDates` al picker;
    `afianco-date-range-picker.ts` rifiuta inline un range che le include
    (`rental.error_dates_unavailable`, i18n it/en/de/fr). Validazione **advisory**:
    il guard atomico server-side a confirm-time resta la verità.
- **Test**: `tests/test_r1/r2` backend verdi (6); SDK `afianco-date-range-picker.test.ts`
  5 sentinel (contratto eventi: overlap → no `selected`, adiacente/clear → `selected`).
  Typecheck shared-types/api-client/embed-sdk OK; bundle ribuildato+sincato.
- **Note**: gli input nativi `type=date` non possono greyare le singole date → la UX
  V2 (calendario custom con celle disabilitate) resta un enhancement; l'overlap-guard
  inline copre il caso funzionale. Parità A=B=C mantenuta.

### R4 — `service_custom_request`: persistere + embed — ✅ FATTO
- **Problema**: il flag (slot proposto fuori dalle regole) era letto solo dal
  validator e poi SCARTATO — non finiva sull'ordine, su NESSUNA superficie (anche
  storefront A). L'embed inoltre non lo esponeva affatto (solo un hint statico).
- **Fix attuato**:
  - Backend (persistenza, vale per A=B=C): aggiunto `service_custom_request` a
    `OrderLineCreate` **e** `OrderLineBase` (snapshot persistito, default False
    back-compat); mappato in `create_order` (order_service), nel path condiviso
    `order_creation_service`, nel legacy `public.py`, e nel cart embed
    (`CartItem`/`CartItemInput` + `cart_service` + mapping cart→OrderRequestItem
    in `embed_public`). `OrderRequestItem` (public.py) lo aveva già.
  - SDK (esposizione embed): nuovo componente isolato `<afianco-custom-request>`
    (data+inizio+fine+note, validazione end>start, form opzionale) renderizzato
    in `product-detail` per service con `service_allow_custom_request` e senza
    slot; on add-to-cart marca `service_custom_request=true` + `booking_date/
    start/end` + `rental_notes`. cart-drawer propaga il campo nello snapshot,
    nel newItem e nella **signature** (richiesta custom = riga distinta dallo
    slot standard). shared-types `embed-cart.ts` aggiornato. i18n it/en/de/fr.
- **Test**: backend `test_r4_custom_request.py` 4 sentinel (boundary + persistenza
  OrderLineBase + back-compat + cart). SDK `afianco-custom-request.test.ts` 5
  (contratto eventi) + cart-drawer INV-CD-5e/5f (propagazione PATCH + riga
  distinta). Typecheck OK; bundle ribuildato. 10/10 backend, 152 SDK pass
  (15 fail pre-esistenti invariati).

## Ondata 3 — Riduzione drift / struttura 🟢
### R10 — Rimuovere il legacy path in `public.py` — ✅ FATTO
- **Fix attuato**: rimosse ~747 righe del legacy inline order-creation in
  `public.py` (`submit_order_request` ora è un thin adapter sul service) +
  eliminato il flag `USE_ORDER_CREATION_SERVICE` e la funzione
  `use_order_creation_service()` in `order_creation_service`. `order_creation_service`
  è ora l'UNICO path storefront+embed → eliminato il punto #1 di drift.
- **Test**: aggiornati i sentinel che pinnavano il legacy:
  `test_invariants_order_creation_service` (flag rimosso, router senza flag,
  legacy assente da public.py); `test_invariants_business_flow` INV-3/INV-4
  ri-puntati a `order_creation_service` (GDPR triple-write + snapshot vivono lì);
  `test_invariants_security` SEC-E.2.2 allineato ai 4 endpoint reali di
  `store_embed` (sentinel stale dal builder embed). Suite backend: **3747 passed,
  0 failed** (escluso solo il pre-esistente `test_new_features.py`, env-dipendente).
- **Rischio gestito**: MEDIO eseguito dopo R1/R2/R4 (service completo).

### R11 — Parità catalogo storefront↔embed (contract-test) — ✅ FATTO
- **Decisione (2026-06-19)**: NON unificare in un service unico. Le due superfici
  divergono *per design*: contratti diversi (`PublicProduct`/lista piatta vs card
  dict embed) e capacità diverse (embed: ricerca/filtro/paginazione/5 sort-mode;
  storefront: lista piatta max 200). Analisi: i segnali critici
  (`has_availability_slots` incl. regola globale+use_default_schedule,
  `service_allow_custom_request`) sono già calcolati in modo equivalente —
  **nessun bug attivo** (a differenza di R1/R2/R4). Un'estrazione completa sarebbe
  alto rischio su 2 superfici di produzione con payoff = sola purezza strutturale.
- **Fix attuato (fonde R11+R12)**: contract-test `test_r11_catalog_parity.py` che,
  su uno store seedato reale, chiama ENTRAMBE le superfici e pinna: stesso SET di
  product_id (parità di visibilità, incl. filtro event-senza-occorrenze) + parità
  dei campi-identità/commercio condivisi (id/slug/name/description/image_url/
  unit_price/category/unit/item_type/unit_label/price_mode/transaction_mode/
  stock_quantity). Blocca i drift futuri senza toccare il codice di produzione.
- **Test**: 2 sentinel verdi (confermano che le superfici sono GIÀ in parità).

### R13 — Cache `_resolve_org` — ✅ FATTO
- **Fix attuato**: `_resolve_org` ora è un wrapper di caching (TTL 45s,
  positive-only) sul core rinominato `_resolve_org_uncached` (logica invariata).
  Ritorna deep-copy isolate (no pollution cross-request); i miss/404 NON sono
  cacheati (nuovi store pubblicati immediati). Helper `_invalidate_resolve_org_cache(slug)`
  + invalidazione esplicita su `update_store_allowed_origins` (dato CORS-rilevante
  effettivo subito).
- **Test**: `test_r13_resolve_org_cache.py` 5 sentinel (risoluzione singola entro
  TTL, copia isolata, miss non cacheato, invalidazione esplicita, scadenza TTL via
  monotonic monkeypatch). Suite backend 3752 passed, 0 failed.

### R14 — Allineare versioning / shape / cache — ✅ FATTO
- **Shipping option model condiviso**: `EmbedShippingOption` era un duplicato
  byte-per-byte di `PublicShippingOption` → ora è un **alias**
  (`from models.shipping_option import PublicShippingOption as EmbedShippingOption`):
  un solo contratto, niente drift di shape sullo shipping.
- **Cache /meta vs /init allineate/documentate**: corrette 2 docstring stale in
  `embed_public.py` (dicevano `max-age=60`, il codice setta `max-age=300` dal Track
  S Step 3.4). Stato documentato: `/embed/init` e `/embed/categories` (meta) =
  300s; `/embed/products` e detail = 60s. Coerente con i commenti inline.
- **Versioning**: l'embed è versionato via `apply_api_version` (header
  `X-API-Version`); lo storefront pubblico resta **unversioned** by design
  (consumato solo dal proprio frontend React, deploy accoppiato). Documentato qui.

## Ondata 4 — Sicurezza hardening 🟡
- **R5 — ✅ FATTO** Coupon per-cliente + rollback. Nuova collezione
  `coupon_redemptions` (unique `(organization_id, coupon_id, customer_key)`,
  customer_key = account id se loggato, altrimenti email lower). `validate_coupon`
  ora claima lo slot per-cliente PRIMA del global increment e rolla-back il claim
  se il global è esaurito (no slot fantasma); `order_creation_service` passa
  customer_key + order_id (vale per storefront+embed, unico path post-R10).
  `release_coupon_for_order` (via `order.coupon_code`, copre anche i guest)
  agganciato a `cancel_order` → la cancellazione decrementa `current_uses` e
  libera il cliente. Test `test_r5_coupon_per_customer.py` 4 (anti-riuso, cliente
  diverso ok, release→riuso, rollback su esaurimento). *Follow-up*: rollback
  automatico su scadenza/abbandono Stripe checkout (serve webhook
  `checkout.session.expired` o sweep ordini draft) — oggi coperto solo il cancel
  esplicito.
- **R8 — ✅ FATTO** Nuovo `require_verified_admin` (role admin + email verificata);
  i 4 endpoint admin di `store_embed.py` (embed-info, embed-snippet,
  preview-token, allowed-origins) lo usano al posto di `require_admin`. Sentinel
  SEC-E.2.2 rafforzato (pinna la dependency = require_verified_admin).
- **R9 — ✅ FATTO** `/api/public/price-preview` ora richiede `slug` e vincola il
  prodotto all'org risolta (parità col wrapper embed): niente enumerazione
  cross-tenant per product_id. Frontend `usePricePreview`/`ReservationLandingPage`
  passano lo slug. Test `test_r9_price_preview_scope.py` 3 (slug required,
  cross-tenant→404, own→200).
- **R6 — ⏸️ RINVIATO (infra)** iframe live-preview da **sotto-dominio sandbox**
  per rimuovere `allow-same-origin` in sicurezza. Richiede un origin separato per
  servire la preview (oggi `srcDoc` + `allow-scripts allow-same-origin` sull'origin
  admin). Rischio residuo mitigato dal fatto che l'SDK usa templating Lit
  (auto-escape) + token preview read-only. Da fare quando il sotto-dominio è
  disponibile; NON implementabile come solo codice senza l'infra.
- **R7 — ⏸️ RINVIATO (scale-out)** Rate-limit store su **Redis** per multi-replica.
  Non necessario in single-replica (rate-limit in-memory corretto); da abilitare
  al primo scale-out orizzontale.

## Ondata 5 — Contract & robustezza 🟢
- **R12** Contract-test backend↔`shared-types` (snapshot delle response reali o
  generazione tipi da OpenAPI) → blocca i drift di shape lato Python.

## Sequenza esecutiva
1→2 (money) · 2→3/4 (parità) · 3 (R10→R11→R13→R14, struttura) · 4 (security) · 5 (contract).
Ogni step: implementa → sentinella verde → suite non regredita → (commit).
