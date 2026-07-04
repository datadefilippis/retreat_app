# Piano di remediation — audit olistico commerce/embed

> Data: 2026-06-19 · Origine: audit olistico (prodotti, account, carrello, checkout,
> pagamenti, sicurezza embed). Verdetto audit: **l'embedding non ha introdotto
> regressioni**; i punti medio/alti sono in gran parte **pre-esistenti**.
> Stato: **da eseguire step-by-step**.

## Principi (come si esegue ogni step)
- **Strutturato** — ondate per tema; ogni step è un commit atomico con un solo scopo.
- **Isolato** — modifiche piccole e additive; nessun big-bang refactor; il flusso
  esistente resta intatto finché il test sentinella non prova il nuovo invariante.
- **Solido** — ogni step porta un **test sentinella** che pinna l'invariante (la
  regressione futura fallisce subito).
- **Scalabile** — fix in helper/service condivisi (single source of truth) così
  coprono sia il path embed sia il legacy storefront in un colpo.
- **Sicuro** — prima la sicurezza/isolamento; sempre fail-closed; mai indebolire i
  controlli esistenti.
- **Mantenibile** — i test fanno da documentazione; niente logica duplicata.

Ordine consigliato: **Ondata A → B → C → D**. Ogni step è indipendente: si può
fermarsi/riprendere senza lasciare il sistema rotto.

Già fatti in sessione (non ripetere): `mint_preview_token` fail-closed; drawer
passivo non fa `loadPersistedCart` (gating singleton).

---

## Ondata A — Sicurezza & isolamento (priorità massima)

### B1 — Carrello scoped per STORE, non solo per org · ALTO · sicurezza · ✅ FATTO
> Helper `_assert_cart_in_store` in `embed_public.py` applicato a get/update/delete/
> merge/checkout. 404 se cart.store_id ≠ store risolto; fail-safe per cart legacy.
> Test `tests/test_embed_cart_store_scoping.py` (4 inv.) + 47 invariant embed verdi.

- **Problema**: `cart_repository.find_by_id` filtra `{id, organization_id}`
  (`backend/repositories/cart_repository.py:61`). In org multi-store un `cart_id`
  di store A è usabile con `?slug=B` (stessa org) su GET/PATCH/DELETE/merge/checkout
  (`backend/routers/embed_public.py` ~1456/1505/1586/1712/1822). Non cross-tenant,
  ma rompe l'isolamento per-store + attribution.
- **Fix**: validare `cart.store_id == store risolto da slug` negli handler embed
  (helper unico `_assert_cart_in_store`), almeno su **checkout/start** e mutazioni;
  404 uniforme se mismatch. (Opzione più forte: aggiungere `store_id` al filtro
  repository — ma rischia il legacy single-store: prima verificare.)
- **Test**: cart creato con slug A + `?slug=B` (stessa org) → 404.
- **Isolamento/rischio**: medio-basso; non tocca il calcolo prezzi. Attenzione al
  ramo legacy single-store (store_id pseudo).

### B2 — Preview-token: verificare anche `store_id` · MEDIO · sicurezza · ✅ FATTO
> `decode_preview_token` (puro) + `_preview_token_authorizes` (dynamic_cors): il
> bypass richiede store_id del token == store reale dello slug (lookup DB). Test:
> store match→ok, mismatch/slug-mismatch/store-not-found→reject. Live: token reale
> 200, falso 403.

- **Problema**: `verify_preview_token` controlla solo `slug`
  (`backend/core/embed_preview.py:55`). Sicuro oggi per indice slug globale unico,
  ma dipendenza implicita non difesa.
- **Fix**: il middleware passa anche lo `store` risolto (o si documenta come
  invariante l'unicità globale slug). Preferito: verificare `store_id` nel token.
- **Test**: token per (slug,store A) non valido se lo slug viene rimappato.
- **Rischio**: basso; additivo.

### B8 — Embed checkout per org legacy single-store · MEDIO · funzionale · ✅ FATTO
> Lo pseudo-store legacy (`public.py` _resolve_org) ora espone
> `allowed_origins` da `store_settings` (fail-safe []). L'embed checkout
> funziona per le org legacy che li configurano.

- **Problema**: lo pseudo-store legacy non ha `allowed_origins`
  (`backend/routers/public.py:444`) → `validate_embed_return_url(url, [])` → checkout
  embed rifiutato (fail-safe). Le org multi-store funzionano.
- **Fix**: o popolare `allowed_origins` nello pseudo-store da `store_settings`, o
  documentare che l'embed richiede multi-store. Decisione di prodotto.
- **Test**: org legacy con allowed_origins configurati → checkout passa.

### B9 — Cart merge: rifiutare se cart già di altro cliente · BASSO · sicurezza · ✅ FATTO
> `merge_embed_cart`: 403 se `existing.customer_account_id` ≠ richiedente.

- **Problema**: `update_customer_binding` filtra `{id, organization_id}` senza
  verificare `customer_account_id` esistente (`backend/repositories/cart_repository.py:156`).
  Mitigato da cart_id UUID non indovinabile.
- **Fix**: rifiutare merge se il cart ha già un `customer_account_id` diverso.
- **Test**: merge su cart di altro cliente → errore.

---

## Ondata B — Correttezza acquisto (billing)

### B3 — Coupon: doppio incremento usi + min su quantità · MEDIO · funzionale · ✅ FATTO
> Pre-creazione → `validate_coupon_dry_run(check_min_order=False)` (no increment).
> Post-creazione → unica `validate_coupon(subtotale reale, store_id)` (1 increment,
> min corretto). Fix in `order_creation_service.py` (path attivo) + `public.py`
> (fallback kill-switch). Test `tests/test_coupon_b3.py` (3) + 14 coupon verdi.

- **Problema**: `validate_coupon` incrementa `current_uses` ad ogni chiamata
  (`coupons.py:132`), ma è chiamato 2× per ordine
  (`order_creation_service.py:459` e `:612`); `increment_coupon_usage` è no-op.
  Inoltre la 1ª chiamata passa `items[0].quantity` come `subtotal` → gate
  `min_order_amount` falsato (`order_creation_service.py:461`). Stesso pattern nel
  legacy `public.py:3035/3244`.
- **Fix**: 1ª validazione **read-only** (`validate_coupon_dry_run`, niente
  increment) con **subtotale reale**; unico increment atomico alla validazione
  post-creazione. Applicare allo **stesso service condiviso** → copre embed + legacy.
- **Test**: un ordine con coupon → `current_uses` +1 (non +2); `min_order_amount`
  valutato sul subtotale.
- **Isolamento/rischio**: medio (tocca billing) → test accurati su edge (coupon
  quasi esaurito, min al limite).

---

## Ondata C — Carrello robusto

### B4 — Update/remove riga per signature, non per product_id · MEDIO · funzionale · ✅ FATTO
> `updateItemQuantity(signature)` matcha la singola riga; `buildItemSignature`
> include ora booking_end_time/date + rental_notes. Render passa la signature.
> Test `afianco-cart-drawer.test.ts` INV-CD-5b (multi-slot non collassano).

- **Problema**: `updateItemQuantity`/remove operano per solo `product_id`
  (`afianco-cart-drawer.ts:699-738`) → collassano righe dello stesso prodotto con
  slot/tier diversi. `buildItemSignature` (`:685`) omette `booking_end_*`/`rental_notes`.
- **Fix**: indicizzare le operazioni per **signature** (o indice di riga);
  completare la signature con i campi mancanti.
- **Test**: 2 righe stesso prodotto, slot diversi → +/− su una non tocca l'altra.

### B5 — Sync carrello multi-tab + lost-update · MEDIO · funzionale · ✅ (a) FATTO · (b) DEFERRED
> (a) Sync cross-tab: `_broadcastCartTouch` su mutazione + listener `storage`
> (`_onCartStorage`) → refetch. Anti ping-pong: broadcast solo su mutazioni, non
> sui refetch. Test INV-CD-5c. (b) Optimistic concurrency (version/ETag sul cart
> per il lost-update su PATCH concorrenti) = miglioria backend deferred (rischio
> raro; (a) mitiga la finestra).

- **Problema**: nessun listener `storage` sul cart → tab non sincronizzati; PATCH
  è replace-list senza versioning → last-write-wins (lost update).
- **Fix**: (a) listener `storage` sulla chiave `afianco_cart_id_<slug>` nel drawer →
  rifetch; (b) optimistic concurrency sul cart (version/ETag) o PATCH a delta.
  Step (a) prima (semplice), (b) come miglioria.
- **Test**: due drawer (simulati) + cart-updated → coerenza badge; PATCH concorrente
  non perde item (con versioning).

---

## Ondata D — Hardening embed (difesa in profondità)

### B6 — Singleton key allineata allo slug del provider · MEDIO · funzionale · ✅ FATTO
> `resolveKey`: store attr > slug del provider (`closest('afianco-storefront-init')`)
> > page-config. Test singleton-guard INV-SG-5.

- **Problema**: `SingletonController.resolveKey` usa `store`-attr/page-config slug
  (`singleton-guard.ts:43`), slegato dallo slug reale del provider → in pagine che
  mescolano full-store + à-la-carte stesso slug, un drawer può diventare passivo.
- **Fix**: risolvere la chiave dallo stesso slug del context attivo (es. `ctx.init.slug`).
- **Test**: full-store + à-la-carte stesso slug → entrambi i ruoli corretti.

### B7 — iframe live-preview: ridurre `allow-same-origin` · MEDIO · sicurezza (difesa in profondità) · da embed
- **Problema**: `sandbox="allow-scripts allow-same-origin"` nell'origin admin
  (`EmbedComposer.jsx`) → la sandbox non isola dal contesto admin.
- **Fix**: servire l'anteprima da un **origin/sottodominio sandbox** dedicato
  (es. `preview.afianco.ch`), oppure rimuovere `allow-same-origin` adattando il
  bundle a girare cross-origin (richiede preview-token già presente). Infra change.
- **Test**: l'anteprima funziona senza `allow-same-origin`.

### B10 — Auth-state UI + listener storage per-slug · BASSO · funzionale · ✅ (parziale)
> Listener `storage` ora filtra la key del PROPRIO slug (account, account-button,
> header) → multi-store safe. Validità/scadenza token UI = cosmetico (il backend
> rifiuta sempre l'expired) → non implementato.

### B11 — Kernel registry: non esporre `client` · BASSO · sicurezza · ⏸️ NON FATTO (accettato)
- Registry già `Object.defineProperty` non-enumerable/non-writable. `client`
  leggibile solo same-origin (token già in localStorage same-origin → nessuna
  nuova superficie). Nascondere `client` complicherebbe l'accesso kernel↔controller
  senza beneficio reale. Accettato come cosmetico.

### B12 — Token cliente in localStorage: guida hardening · BASSO · doc · pre-esistente
- Documentare per i merchant: opzione `MemoryTokenStorage` + CSP sul loro sito;
  valutarla default per flussi sensibili.

### B13 — Idempotency digest senza body: verifica client · BASSO · verifica · ✅ VERIFICATO
- `client.ts:217` → `Idempotency-Key = opts.idempotencyKey ?? uuidv4()` per ogni
  richiesta non-GET. Key fresca per richiesta → nessun rischio di collisione body.
  Nessuna modifica necessaria.

---

## Riepilogo sequenza
A: B1 → B2 → B8 → B9 · B: B3 · C: B4 → B5 · D: B6 → B7 → B10 → B11 → B12 → B13

Ogni step: implementa → test sentinella verde → suite non regredita → (commit).
