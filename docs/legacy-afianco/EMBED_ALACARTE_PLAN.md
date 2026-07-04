# Embed à-la-carte — Piano architetturale e roadmap

> Stato: **APPROVATO, in implementazione**
> Data: 2026-06-19 · SDK embed v0.8.0 · Branch base: `main`
> Obiettivo: passare dall'embedding monolitico ("tutto lo store insieme") a un
> embedding **à-la-carte** — ogni elemento (carrello, account, categorie, singolo
> prodotto) embeddabile liberamente dove si vuole, anche su pagine diverse — con
> un **builder visuale** integrato nella pagina "Condividi store".

Principi guida: **strutturato, scalabile, isolato, sicuro, mantenibile** (file
piccoli, fonte di verità unica, additivo e retrocompatibile).

---

## 1. Deep analysis — perché oggi è "tutto o niente"

### Come funziona adesso
Ogni componente (`<afianco-product-grid>`, `<afianco-cart-drawer>`,
`<afianco-header>`, ecc.) ottiene il "cervello" — client API, dati store
(`init`), lingua — tramite un **Lit Context** (`apps/embed-sdk/src/context.ts:74`).
Il provider è `<afianco-storefront-init>`
(`apps/embed-sdk/src/components/afianco-storefront-init.ts:117`); i componenti lo
consumano con `@consume` (es. `afianco-product-grid.ts:123`).

**Blocco critico:** il Lit Context si risolve via **DOM ancestry** — il
componente cerca il provider risalendo l'albero DOM. Quindi *deve* essere annidato
dentro `<afianco-storefront-init>`. Fuori dal wrapper resta in stato "loading" con
`client: null`. Questo è l'**unico vero blocco** all'embedding libero.

### Cosa già funziona a favore
Esiste un **secondo canale**, già indipendente dalla posizione DOM: un **event
bus a livello `document`**. Header, cart e account si parlano già così:
`afianco:add-to-cart`, `afianco:open-cart`, `afianco:open-account`,
`afianco:cart-updated`, `afianco:customer-logged-in`, `afianco:locale-changed`,
`afianco:product-view-requested` + eventi `storage` (cross-tab).
Vedi `afianco-cart-drawer.ts:380` e `afianco-header.ts:121`. Manca solo che i
componenti condividano lo stesso "cervello" senza essere annidati.

### Perché "wrappare ogni isola" è una cattiva soluzione
Un `<afianco-storefront-init>` attorno a ogni elemento "funzionerebbe a metà":
- **N chiamate `/embed/init`** ridondanti → N skeleton di caricamento;
- **N stati separati in memoria**: due carrelli non si vedono live (si riallineano
  solo via evento/`storage`, fragile);
- **Overlay duplicati**: `cart-drawer` e `account` sono `position:fixed` singleton
  (`afianco-cart-drawer.ts:126`) → due istanze = due overlay sovrapposti.

### Gap specifici per i casi d'uso target
| Obiettivo | Stato oggi | Gap |
|---|---|---|
| Carrello fisso nel menu | Solo dentro `<afianco-header>` | Manca trigger carrello standalone |
| Account fisso nel menu | Solo dentro `<afianco-header>` | Manca trigger account standalone |
| Categorie diverse in pagine diverse | `category="x"` supportato (`afianco-product-grid.ts:75`) | OK 1 categoria; manca gruppo `categories="x,y"` |
| Singolo prodotto in una pagina | `product-detail` è solo event-driven (`afianco-product-detail.ts:23`) | Manca render inline via `product-id` |
| Elementi sparsi ovunque | Bloccato dal DOM-ancestry del context | Serve disaccoppiare binding dal DOM |

---

## 2. Architettura target — lo **Store Kernel** (cervello condiviso per-slug)

Disaccoppiare il binding dei dati dalla posizione nel DOM con un **singleton per
slug** a livello pagina (un registry, non legato all'albero DOM). Qualunque
elemento `afianco-*`, ovunque, si connette al kernel **per slug**. È il pattern
micro-frontend / Shopify Buy Buttons / Stripe Elements.

```
        OGGI (DOM-ancestry)                    TARGET (Store Kernel per-slug)

  <afianco-storefront-init slug>          window.__afiancoStores[slug] = Kernel
    ├─ <product-grid>                        (client + init + cart + auth + locale)
    ├─ <cart-drawer>                                 ▲      ▲      ▲
    └─ <header>                                       │      │      │
  TUTTO deve stare qui dentro          [menu]────────┘  [body]─┘  [altra pagina]
                                       cart-button   product-grid   product(id)
                                       ovunque, niente wrapper, 1 solo init
```

### Componenti dell'architettura
1. **`AfiancoStoreKernel` — singleton reattivo per slug.** Registry
   `window.__afiancoStores: Map<slug, Kernel>` (namespaced, API congelata). Ogni
   kernel possiede: `AfiancoClient`, `init` (fetchato **una sola volta**, dedup
   delle chiamate concorrenti + refresh visibility/polling già esistente spostato
   qui), `locale`, **stato carrello** e **stato auth** come **unica fonte di
   verità** della pagina. Risultato: tutte le isole vedono lo stesso
   carrello/login **live in memoria**.
2. **`StoreConsumerMixin` — binding retrocompatibile.** ReactiveController che
   risolve il kernel a cascata: (1) provider `<afianco-storefront-init>` antenato
   → gli snippet attuali continuano a funzionare identici; (2) attributo
   `store="slug"`; (3) **slug di default della pagina** (§3); (4) errore amichevole.
3. **Config di pagina una-tantum (DRY).**
   ```html
   <script type="module" src=".../afianco-embed.es.js"
           data-afianco-slug="marco-conti" data-afianco-base-url="..."></script>
   ```
   imposta lo slug di default ⇒ gli elementi non ripetono attributi. `store="..."`
   per-elemento permette **più store nella stessa pagina**.

### Catalogo elementi "drop-anywhere"
- `<afianco-cart-button>` **(nuovo)** — icona+badge carrello per il menu.
- `<afianco-account-button>` **(nuovo)** — trigger account per il menu.
- `<afianco-cart-drawer hide-trigger>` / `<afianco-account hide-trigger>` — overlay
  singleton, montati **una volta** (il kernel garantisce unicità).
- `<afianco-product-grid categories="x,y,z">` **(esteso)** — gruppi di categorie.
- `<afianco-product product-id="...">` **(nuovo)** — singolo prodotto inline.
- Tutti gli altri (login, signup, customer-portal, language-switcher) drop-anywhere.

---

## 3. Builder visuale nella pagina "Condividi store"

Nel tab **"Embed"** di `frontend/src/features/stores/components/ShareStoreModal.jsx`
(oggi 2 tab Link/Embed) si aggiunge un toggle a due modalità:

```
┌─ Embed ──────────────────────────────────────────────┐
│  [ Tutto lo store ]  [ Componi (à-la-carte) ]   ◄ toggle │
│                                                          │
│  TUTTO LO STORE → snippet completo (come oggi)           │
│                                                          │
│  COMPONI → pannello dinamico:                            │
│   ☑ Carrello (per il menu)                               │
│   ☐ Account utente (per il menu)                         │
│   ☑ Categorie ▸ [Coaching] [Workshop] (multi-select)    │
│   ☐ Singolo prodotto ▸ [cerca/seleziona prodotto…]      │
│        ▼ genera in tempo reale (snippet validato backend) │
└──────────────────────────────────────────────────────────┘
```

### Principio: **Block Catalog** (data-driven, fonte di verità unica)
Un **catalogo dichiarativo dei blocchi embeddabili** guida sia la UI sia la
generazione dello snippet. Aggiungere un blocco = **una voce dati**, non refactor.

Voce di catalogo (concettuale):
```
{
  id: "cart",
  label: "Carrello", icon: "cart", group: "menu",
  needs: [],                        // config richiesta (es. category, product)
  emits: ["<afianco-cart-button>"], // snippet dell'elemento
  requires: ["cart-drawer"],        // singleton/dipendenze da montare 1 volta
}
```
Tipi di config (`needs`): nessuna (carrello/account) · `category[]` (multi-select)
· `product` (picker). La risoluzione di `requires` è l'intelligenza UX (§3.2).

### 3.1 Struttura file (piccoli, separati per responsabilità)
**Backend (fonte di verità dello snippet → no drift frontend):**
- `backend/core/embed_blocks.py` *(nuovo)* — catalogo + template per-blocco +
  resolver dipendenze; compone lo snippet à-la-carte da `{blocks, config}`.
- `backend/core/embed_distribution.py` *(esteso)* — `generate_embed_snippet` (full)
  diventa "il preset che seleziona tutti i blocchi".
- `backend/routers/store_embed.py` *(esteso)* — `embed-info` aggiunge
  `blocks_catalog`; nuovo `POST .../embed-snippet` riceve `{blocks, config}` e
  ritorna lo snippet composto e **validato** (slug/categoria/prodotto verificati).

**Frontend (builder modulare, pezzi piccoli):**
- `ShareStoreModal.jsx` *(modifica minima)* — toggle "Tutto / Componi" → monta
  `<EmbedComposer/>`.
- `features/stores/components/embed/EmbedComposer.jsx` *(nuovo)* — orchestratore.
- `embed/BlockChecklist.jsx` *(nuovo)* — render lista blocchi dal catalogo (map).
- `embed/pickers/CategoryPicker.jsx`, `embed/pickers/ProductPicker.jsx` *(nuovi)* —
  categorie da `/embed/init/{slug}`, prodotti da `/embed/products/{slug}`.
- `embed/SnippetOutput.jsx` *(nuovo)* — blocco copia (riusa stile `<pre>` esistente).
- `api/storeEmbed.js` *(esteso)* — `getCatalog`, `composeSnippet`.

### 3.2 Risoluzione dipendenze (user-friendly)
Il generatore, dato l'insieme di blocchi, produce **3 sezioni guidate**:
1. **Una-tantum (testa pagina):** lo `<script ... data-afianco-slug>`.
2. **Gli elementi scelti**, da incollare dove si vuole (menu, pagina X, pagina Y).
3. **Singleton richiesti** (es. `<afianco-cart-drawer hide-trigger>`) con nota
   *"incolla una sola volta, a fine pagina"* — aggiunti automaticamente,
   deduplicati. Il merchant non deve sapere che il pulsante-carrello richiede il
   drawer: lo dichiara il catalogo, lo risolve il generatore.

---

## 4. Mappa requisiti → soluzione
| Requisito | Come |
|---|---|
| **Strutturato** | Catalogo dichiarativo → UI e snippet derivati; 3 sezioni guidate |
| **Scalabile** | Nuovo blocco = 1 voce catalogo; bootstrap pagina O(1) (kernel: 1 init con N elementi) |
| **Isolato** | Web Component + Shadow DOM (CSS isolato bidirezionale); slug diversi = kernel/cart/token separati |
| **Sicuro** | Snippet generato e validato dal backend; `allowed_origins`/CORS invariati; nessun segreto; solo identificatori pubblici |
| **Mantenibile** | 1 catalogo + 1 generatore backend + 5-6 componenti React piccoli; snippet a fonte unica |

### Sicurezza — garanzie invariate
- **CORS/allowlist invariato**: ogni isola chiama `/api/public/embed/*` con
  l'`Origin` del browser, validato da `DynamicCORSMiddleware` contro
  `store.allowed_origins`. Più elementi = più richieste dalla stessa origine già
  autorizzata: **zero nuova superficie**.
- Nessun segreto nel bundle (slug pubblico; il kernel tiene solo dati pubblici + il
  JWT cliente già in localStorage per-slug).
- Idempotency mutazioni + anti-phishing return-url checkout: invariati.
- *(Pre-esistente: token cliente in localStorage → esposto a XSS del sito merchant.
  Non peggiora con l'à-la-carte; hardening futuro via cookie/iframe, fuori scope v1.)*

---

## 5. Roadmap a fasi (additiva, retrocompatibile)
- **Fase 0 — ✅ FATTA.** Catalogo come contratto: `backend/core/embed_blocks.py`
  + `backend/tests/test_embed_blocks.py` (18 verdi). Preset "full" byte-identico
  all'attuale `generate_embed_snippet`.
- **Fase 1 — ✅ FATTA.** Store Kernel per-slug + page-config:
  `apps/embed-sdk/src/store/kernel.ts` + `page-config.ts` + `store-kernel.test.ts`
  (8 verdi). Additivo, zero breaking change.
- **Fase 2 — ✅ FATTA (manca solo multi-categoria).** `StoreConsumerController`
  (`store/store-consumer.ts`) + nuovi `<afianco-cart-button>`,
  `<afianco-account-button>`, `<afianco-product product-id>` + retrofit 1-riga di 6
  componenti esistenti (grid, cart-drawer, account, product-detail, checkout-button,
  header) → funzionano standalone. `store-consumer.test.ts` (5 verdi). Demo:
  `embed-playground/alacarte.html`. **Residuo:** `categories="x,y"` multi-categoria
  sulla grid + parametro backend `categories=` (oggi solo `category` singola).
- **Fase 3 — ✅ FATTA.** Backend builder: `POST /api/stores/{id}/embed-snippet`
  (slug server-derived) + `blocks_catalog` e `categories` in `embed-info`
  (`backend/routers/store_embed.py`, riusa `_aggregate_categories` per slug
  coerenti). Test: `backend/tests/test_store_embed_snippet.py` (4 verdi).
  Multi-categoria risolta: il blocco "categories" emette UNA grid per categoria
  via `category=` (zero modifiche backend al products endpoint).
- **Fase 4 — ✅ FATTA.** UI Composer nel tab Embed: toggle "Tutto lo store /
  Componi" in `ShareStoreModal.jsx` + `features/stores/components/embed/
  EmbedComposer.jsx` (checklist data-driven dal catalogo + CategoryPicker +
  ProductPicker + output con copy). `api/storeEmbed.js` → `composeSnippet`.
  Frontend compila pulito.
- **Fase 5 — DA FARE.** Preview live nel modale + test sentinel frontend + docs
  merchant + bump 0.8.0 → 0.9.0. "Tutto lo store" resta intatta.

---

## 6. Decisioni prese (default; modificabili)
1. **Categorie multiple**: `categories="x,y"` su un'unica grid, con parametro
   backend dedicato (paginazione corretta). *(vs una grid per categoria)*
2. **Singolo prodotto**: nuovo `<afianco-product product-id>` inline.
   *(vs riuso del drawer `product-detail`)*
3. **Preview live**: in **Fase 5** (richiede caricare il bundle dentro la dashboard).

---

## 6bis. Deep Audit & Refinement (2026-06-19)

Audit verificato nel browser sulla pagina `embed-playground/alacarte.html`.

### Bug investigati
- **"Prodotto singolo bianco" — NON è un bug di rendering.** Ispezione DOM:
  kernel `ready`, `<afianco-product>` fetcha il prodotto e genera
  `<afianco-product-card>` che renderizza l'articolo (nome/colori corretti,
  card 416px); la grid genera 3 card. Il "bianco" era il viewport del preview a
  2px. **Causa reale del bianco lato utente:** lo snippet del builder punta al
  bundle CDN di **produzione** (`app.afianco.ch/embed/v1`, non deployato) e senza
  `base-url` → su pagina locale i tag non si registrano / l'API non risponde.
  → Gap di **testabilità**, non di codice.
- **"Errore alla chiusura" — non riproducibile come crash runtime.** Apri/chiudi
  carrello e account (ESC/scrim/setOpen) → console pulita. Probabile overlay di
  compile-error CRA transitorio durante le edit (ora build pulita), oppure
  eccezione nel Composer che senza protezione fa crashare la SPA admin.

### Fix applicati
- **Admin a prova di crash:** `EmbedComposer` avvolto in `ErrorBoundary` con
  fallback inline (un errore nel builder NON fa più white-screen dell'app);
  `ErrorBoundary` esteso con prop `fallback` opzionale. Cancel-guard sul fetch
  prodotti del Composer (no setState dopo unmount).
- **Chiarezza builder:** nota nell'output che spiega requisiti (dominio
  autorizzato + store pubblicato) e perché in locale può apparire vuoto.

### Navigazione multi-pagina (prodotti su pagine diverse)
- **MPA (reload completo):** ogni pagina ricarica il bundle → kernel ricreato →
  re-init (cache server 300s+ETag). Carrello/auth persistono via `localStorage`
  (per slug). Ogni pagina include i singleton + i propri elementi. ✅
- **SPA (routing client-side):** bundle caricato una volta; il kernel per-slug
  persiste su `window.__afiancoStores` → init/carrello/auth **condivisi in
  memoria** tra route, navigazione **fluida** senza re-fetch. ✅
- **Regola d'oro:** lo `<script data-afianco-slug>` e i **singleton**
  (`cart-drawer`, `account`, `product-detail`) vanno messi **una volta nello
  shell** del sito; gli elementi (grid/prodotto/bottoni) per-pagina. Evita di
  duplicare i singleton per-route (doppi overlay fixed).

### Refinement
1. **Live preview nel modale — ✅ FATTO (Fase 5).** Soluzione solida scelta:
   **preview-token firmato, read-only, slug-scoped** (`core/embed_preview.py`,
   TTL 15 min) generato da `GET /api/stores/{id}/embed-preview-token`
   (require_admin, org-scoped). Il `DynamicCORSMiddleware` accetta il token
   (header `X-Afianco-Preview-Token` o query `preview_token`) come bypass
   dell'allowlist **solo per GET** (init/products/categories) — mutazioni
   bloccate. SDK: `previewToken` propagato client→kernel→page-config
   (`data-afianco-preview-token`). Frontend: `EmbedComposer` rende i blocchi in
   un **iframe sandboxed** (`allow-scripts allow-same-origin`) con bundle
   same-origin + base-url + token. NON tocca gli `allowed_origins` pubblici.
   Verificato in browser: render reale da origin non-allowlisted; 403 senza
   token / per slug diverso / su POST. Fix incluso: `X-Afianco-Preview-Token`
   aggiunto agli `Access-Control-Allow-Headers` del preflight.
   Test: `backend/tests/test_embed_preview.py`.
2. **Guard singleton nell'SDK — ✅ FATTO.** `store/singleton-guard.ts`
   (`SingletonController`): un solo `cart-drawer`/`account`/`product-detail`
   attivo per (nome, slug); i duplicati restano passivi (render `nothing` +
   handler early-return su `!active`); alla disconnessione dell'attivo il
   successivo viene promosso (utile in SPA). Test:
   `apps/embed-sdk/tests/singleton-guard.test.ts` (6 verdi). Verificato in
   browser: istanza singola attiva, nessuna regressione.
3. **Snippet ambiente-aware — SCARTATO (di proposito).** Non ha un vero caso
   d'uso merchant: l'embed parla sempre con l'API di produzione afianco (non
   esiste un "backend locale del merchant"), e la **live preview** copre gia'
   il "vedere se funziona". Aggiungerlo creerebbe solo confusione.

## 6ter. Uniformare à-la-carte ↔ full-store (deep audit 2026-06-19)

**Problema riportato:** con l'embed intero (`<afianco-storefront-init>`) tutti i
processi funzionano (calendario/disponibilità servizi, tipi prodotto + metodi
d'acquisto, account con storico/biglietti/corsi, checkout). Con gli elementi
à-la-carte alcuni processi mancavano (es. servizi non aggiungibili al carrello).

**Causa (audit):** 22 componenti consumano il Lit context, ma solo i 9 top-level
avevano il retrofit à-la-carte. I **13 nidificati** non ricevevano il context
fuori dal provider: `availability-picker` (CALENDARIO servizi), `price-preview`,
`shipping-options-picker`, e tutto l'account (`login`, `signup`,
`customer-portal`, `my-bookings`, `my-courses`, `my-downloads`, `profile-editor`,
`course-player`), `product-card`. Il `StoreConsumerController` *impostava* il
context sul singolo host ma non lo *ri-forniva* ai figli.

**Fix (uniformante, 1 modifica):** `StoreConsumerController` ora, in modalità
standalone, crea un **`ContextProvider` Lit** sull'host (sourced dal kernel) →
ogni elemento à-la-carte top-level fa da provider per il proprio sottoalbero,
esattamente come `<afianco-storefront-init>`. Tutti i 13 nidificati ricevono il
context automaticamente. Nessun retrofit per-componente.

**Verificato in browser (à-la-carte, origin non-allowlisted via playground):**
- servizio 90-min: `availability-picker` ora `ctx ready` + client → calendario
  carica le date (prima: "nessuno slot") + CTA "Aggiungi al carrello";
- account: `afianco-login` annidato `ctx ready` + client → login/registrazione ok
  (→ storico ordini/biglietti/corsi dopo login).
- Suite SDK: 15 falliti PRE-ESISTENTI / 136 passati (zero regressioni).

**Nota acquisto per tipo/modalità (NON è un bug):** l'aggiunta al carrello
dipende dal prodotto: `transaction_mode=direct` → "Aggiungi al carrello";
`request` → "Richiedi info"; `approval` → richiesta approvazione. I servizi/eventi
`direct` richiedono uno slot/data disponibile (availability configurata).

## 7. Note operative ambiente di sviluppo
- Playground locale già pronto: `embed-playground/` servito su
  `http://localhost:8090` (vedi `.claude/launch.json`), bundle via symlink a
  `frontend/public/embed/v1/`.
- Store di test con `allowed_origins` che include `http://localhost:8090`:
  `marco-conti-coaching` (9 prodotti), `centro-benessere-lugano` (8), `bottega-demo` (4).
- Backend `:8000`, frontend `:3000`.
