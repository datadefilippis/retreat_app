# Modulo Newsletter / Form embeddabili — Audit + Piano

> Stato: **PIANIFICAZIONE** (nessun codice scritto). Data: 2026-06-19.
> Obiettivo: creare un modulo per costruire form (iscrizione newsletter) con
> campi configurabili, embeddabili su siti esterni. Chi si iscrive deve
> comparire in **Customer Insights** con lo stato "iscritto alla newsletter",
> anche se non ha mai acquistato. Coerenza piena con opt-in/opt-out esistenti.
> Vincoli: isolato, strutturato, scalabile, **no duplicazione / no monolite**.

---

## 1. Stato attuale (audit verificato)

### 1.1 Cos'è "iscritto alla newsletter" oggi
Non esiste una collection "newsletter". **"Iscritto" == marketing opt-in attivo.**
La verità è su due campi denormalizzati + un audit immutabile:

- `customers` (CRM org-scoped) — `accepted_marketing_at`, `marketing_revoked_at`
  ([models/customer.py:48](backend/models/customer.py)).
- `customer_accounts` (login) — stessi due campi
  ([models/customer_account.py:109](backend/models/customer_account.py)).
- `consent_audit` — prova legale immutabile, TTL 365gg
  ([repositories/consent_audit_repository.py](backend/repositories/consent_audit_repository.py)).

**Stato iscrizione (most-recent-wins):**
`opted_in = accepted_marketing_at != null AND (revoked_at == null OR accepted_at > revoked_at)`.

### 1.2 Dove l'opt-in viene scritto oggi (il "triple-write", INLINE)
Solo al **checkout** (`gdpr_marketing_accepted=True`), inline in
[order_creation_service.py:493-586](backend/services/order_creation_service.py):
1. `consent_audit.record_consent(source="customer_checkout"|..., document_type="merchant_marketing", ...)`
2. `customer_accounts.update($set accepted_marketing_at, marketing_revoked_at=null)` (se loggato)
3. `customers.update($set accepted_marketing_at, marketing_revoked_at=null)` (sempre)

E al **signup** customer ([customer_auth_service.py:421](backend/services/customer_auth_service.py),
`source="customer_marketing_optin"`).
➡️ **Questa logica NON è una funzione riusabile: è duplicata inline. È il primo
punto da estrarre per evitare drift** (lezione delle ondate R1-R14).

### 1.3 Opt-out (già esistente, riusabile as-is)
Router dedicato [routers/marketing_consent.py](backend/routers/marketing_consent.py):
- `GET /api/marketing-consent/unsubscribe/{token}` (preview) +
  `POST .../confirm` (esegue). Two-step anti-prefetch.
- Token JWT HS256 firmato con `SECRET_KEY`, scope `marketing_unsubscribe`,
  payload `{email, org_id, exp}`, TTL 5 anni
  ([core/marketing_unsubscribe_token.py](backend/core/marketing_unsubscribe_token.py)).
- Scrive `marketing_revoked_at=now` su `customers` + `customer_accounts` +
  audit `source="customer_marketing_revoke"`.
- Pagina pubblica `/u/:token` ([frontend/src/pages/MarketingUnsubscribePage.js]).
- ➡️ Il nuovo modulo **riusa** questo flusso tale e quale (un subscriber da form
  riceve lo stesso link unsubscribe). Nessun lavoro nuovo lato opt-out.

### 1.4 Customer Insights / segmentazione — **il nodo centrale**
Modulo: [backend/modules/customer_insights/](backend/modules/customer_insights/) +
[frontend/src/features/customer-insights/](frontend/src/features/customer-insights/).
- La lista parte da `customer_metrics` (materializzato) via
  `find_metrics_by_org` ([service.py:201](backend/modules/customer_insights/service.py)),
  poi idrata email/phone/account/marketing dai `customers`/`customer_accounts`.
- `customer_metrics` è popolato da [refresh.py:70](backend/modules/customer_insights/refresh.py):
  **aggrega `sales_records` raggruppando per `customer_id`**.
- ⚠️ **CONSEGUENZA**: un iscritto che non ha MAI acquistato non ha riga in
  `customer_metrics` → **NON compare nella lista**. I `customers` sono usati solo
  come `contact_map` per id già presenti nelle metrics.
- Filtri esistenti: `marketing_opted_in` (true/false), `has_account`, `search`,
  `segment` (RFM: top/active/occasional/inactive/new), `customer_status`.
- Export CSV già include `marketing_opted_in` + `unsubscribe_url`
  ([modules/customer_insights/router.py](backend/modules/customer_insights/router.py)).

### 1.5 Creazione clienti (guest→customer)
`customer_repository.upsert_by_email(org_id, *, name, email, phone, customer_account_id, source="storefront")`
([repositories/customer_repository.py:53](backend/repositories/customer_repository.py)),
race-safe (`find_one_and_update(upsert=True)`), salva `metadata.source`. I campi
marketing NON sono inizializzati all'insert (restano null).
➡️ Un subscriber-senza-acquisto = riga `customers` con `source="newsletter_form"`,
`customer_account_id=null`. **Già supportato**: un customer può esistere senza ordini.

### 1.6 Campi configurabili (riusabile, da estendere)
[models/field_config.py](backend/models/field_config.py): `FieldConfig{id,label,type,required,placeholder,help_text,sort_order}`.
Tipi MVP: **solo `text|textarea|number`**. Editor admin riusabile:
[FieldEditorList.js](frontend/src/features/events/components/FieldEditorList.js) +
`pruneFieldConfigs`. Rendering dinamico oggi inline nel checkout
([StorefrontPage.js:2195-2274](frontend/src/features/storefront/StorefrontPage.js)).
➡️ Per la newsletter servono almeno `email|checkbox|select`. Estendere il
`Literal` di `type` è **backward-compatible** (i dati vecchi restano validi).

### 1.7 Infrastruttura embed (riusabile al 100%)
- Web component Lit in [apps/embed-sdk/src/components/](apps/embed-sdk/src/components/),
  registrati in [index.ts](apps/embed-sdk/src/index.ts); context via
  `@consume(storefrontContext)`; kernel per à-la-carte (`window.__afiancoStores`).
- Endpoint pubblici [routers/embed_public.py](backend/routers/embed_public.py):
  pattern `slug` + `_resolve_org` + `@limiter.limit(key_func=get_real_ip_with_slug)` +
  `apply_api_version`.
- CORS dinamico [middleware/dynamic_cors.py](backend/middleware/dynamic_cors.py):
  valida Origin vs `store.allowed_origins`; **va aggiunto il pattern regex** del
  nuovo path a `_SLUG_PATH_PATTERNS`.
- Builder à-la-carte [core/embed_blocks.py](backend/core/embed_blocks.py)
  (`BlockSpec`/`ConfigField`/`compose_alacarte`) + [routers/store_embed.py] +
  [EmbedComposer.jsx]. Si aggiunge un `BlockSpec` "newsletter".
- api-client [packages/api-client/src/client.ts] + shared-types
  [packages/shared-types/] + i18n SDK [apps/embed-sdk/src/i18n/] (it/en/de/fr).
- Pattern form già presenti: `afianco-signup`, `afianco-custom-request`
  (validazione + custom event + stato inline).

### 1.8 Pattern CRUD admin (riusabile)
Router org-scoped: [routers/coupons.py], [routers/store_embed.py] (per-store,
`require_verified_admin`). Modelli `*Create`/`*Update`/`*Response`. Collection +
indici in [database.py](backend/database.py) `create_indexes()`. Feature frontend:
tab in StoresPage o feature dedicata; api in `frontend/src/api/`.

---

## 2. Decisioni di design — ✅ DECISE (2026-06-19)

### D1 — Visibilità subscriber in Customer Insights → **A. Union nella lista**
`build_customer_list` parte da `customers` ∪ `customer_metrics`. I non-acquirenti
compaiono con metrics a zero e un segmento dedicato (`lead`/`subscriber`). Il
filtro `marketing_opted_in` funziona già. Da fare con sentinel + attenzione RFM su
zero-purchase. *(Insights è org-scoped → vale anche per i form non legati a store.)*

### D2 — FieldConfig → **estendere** (`email|select|checkbox|tel`)
Estendere il `Literal` `type` (+ `options` per select). Backward-compatible. Un solo
concetto di campo, riuso di editor (`FieldEditorList`) e renderer.

### D3 — Opt-in → **singolo (MVP)**
Submit con checkbox privacy/consenso esplicito → iscritto subito (`confirmed`). Il
double opt-in (status `pending` + email di conferma) resta una fase successiva (F5).

### D4 — Scope del form → **per-organizzazione, store OPZIONALE** *(rivisto)*
⚠️ Decisione utente: **il form NON è per forza legato a uno store** — può essere
creato solo per embed esterno. Conseguenze:
- `NewsletterForm.organization_id` required; `store_id: Optional` (nullable).
- Il form ha **identità embed propria**: `slug` unico per org + **`allowed_origins`
  propri** (non eredita per forza da uno store).
- Path pubblico per **form-slug**, non store-slug:
  `POST /api/public/embed/newsletter/{form_slug}/submit`.
- CORS dinamico: serve una **nuova risoluzione** "form_slug → form.allowed_origins"
  in `dynamic_cors` (oggi risolve solo store-slug → store.allowed_origins). Se il
  form è collegato a uno store, può opzionalmente ereditarne gli origins.
- Admin UI: **feature top-level dedicata** `features/newsletter/` (non un tab di
  StoresPage), perché i form non sono store-bound. Filtro/associazione store
  opzionale nella UI.
- I `customers` restano **org-scoped** → un iscritto da form standalone crea
  comunque una riga customer in quell'org e appare in Insights (D1). ✓

### D5 — Anti-abuso (form pubblico) → **confermato**
Rate-limit per (IP, form_slug), honeypot anti-bot, validazione email, **dedup per
email** (re-submit stessa email = update, non duplicato), niente PII negli errori.

### D6 — Campi built-in: email (required) + **name/phone opzionali** + custom
Oltre ai `field_configs` custom, il form supporta i campi standard email (sempre),
name e **phone** come opzioni attivabili (toggle), così il caso "newsletter con
telefono" non richiede un custom field.

### D7 — Tracciamento sorgente iscrizione *(requisito utente)*
Lo stesso form può essere embeddato su più siti/link: per OGNI iscrizione si deve
sapere **esattamente da quale link** è arrivata. Catturiamo su due livelli:
- **Server (trust anchor, non spoofabile dal browser)**: header `Origin` + `Referer`
  della richiesta di submit (già disponibili al CORS dinamico) →
  `source_origin`, `source_referrer_server`.
- **Client (granularità "link/pagina")**: il web component invia
  `window.location.href` (pagina che ospita il form) + `document.referrer` →
  `source_url`, `source_referrer`.
- **Etichetta opzionale (campagne)**: attributo snippet `source="..."` (es.
  `<afianco-newsletter-form source="blog-footer">`) → `source_label`. Permette
  posizionamenti nominati (stile UTM) oltre all'URL automatico.

Persistenza: tutti i campi `source_*` sullo **`NewsletterSubscription`** (per-evento).
Attribuzione first-touch sul customer: `customers.metadata.acquisition_source` =
primo `source_label`||`source_origin` (solo se assente → non sovrascrive). La UI
admin submissions mostra/filtra/raggruppa per sorgente; opzionale badge sorgente
in Customer Insights.

---

## 3. Architettura proposta (isolata + integrata)

Principio guida: **estrarre i servizi condivisi**, poi costruire il modulo sopra.

### 3.1 Estrazioni condivise (fanno sparire la duplicazione)
- **`services/marketing_consent_service.py`** *(nuovo, condiviso)*:
  `record_marketing_optin(org_id, *, email, customer_id, customer_account_id,
  store_id, ip, user_agent, locale, version_tag, version_hash, source)` → esegue il
  triple-write (audit + accounts + customers, con reset `marketing_revoked_at`).
  ➡️ **checkout, signup E newsletter** chiamano questo. Elimina il drift inline.
  (Eventuale `record_marketing_revoke(...)` simmetrico riusato da unsubscribe.)
- **Renderer campi dinamici frontend**: estrarre `DynamicFieldForm` dal checkout
  per riuso (admin preview + eventuale render storefront).

### 3.2 Nuovo modulo Newsletter (isolato, per-org)
**Backend**
- `models/newsletter.py`:
  `NewsletterForm{id, organization_id, store_id:Optional, name, slug (unico per org),
  allowed_origins:List[str], collect_name:bool, collect_phone:bool,
  field_configs:List[FieldConfig], consent_text, privacy_required:bool,
  success_message, redirect_url, is_active, created_at, updated_at}` +
  `*Create`/`*Update`/`*Response`.
  `NewsletterSubscription{id, organization_id, form_id, email, name, phone,
  fields_data, status(confirmed|unsubscribed), customer_id, ip, user_agent,
  created_at,` **sorgente (D7):** `source_url, source_origin, source_referrer,
  source_referrer_server, source_label}`.
- `routers/newsletter_forms.py` *(admin, org-scoped, `require_verified_admin`)*:
  CRUD form + `PATCH .../allowed-origins` (come store_embed) + `GET .../submissions`
  + `GET .../embed-snippet`.
- Estensione [embed_public.py]: `POST /api/public/embed/newsletter/{form_slug}/submit`
  *(pubblico)* → risolve il **form** per slug → org; valida consenso/email/honeypot;
  cattura sorgente (D7): `source_origin`/`source_referrer_server` dagli **header**
  request + `source_url`/`source_referrer`/`source_label` dal **body** (client);
  **upsert customer** org-scoped (`source="newsletter_form"`, first-touch
  `metadata.acquisition_source`); **chiama
  `marketing_consent_service.record_marketing_optin(...)`**; salva/aggiorna
  `newsletter_subscriptions` (dedup per email) con i campi `source_*`. Rate-limit
  per (IP, form_slug).
- `database.py`: `newsletter_forms_collection`, `newsletter_subscriptions_collection`
  + indici (`organization_id`, `(organization_id,slug)` **unique**, `slug` per
  lookup pubblico, `(organization_id,form_id)`, `(organization_id,email)`).
- **CORS** [dynamic_cors.py]: nuova risoluzione `form_slug → newsletter_form.allowed_origins`
  (oggi risolve solo store-slug → store.allowed_origins) + pattern path
  `/api/public/embed/newsletter/{slug}/submit`. Se `store_id` valorizzato, può
  ereditare gli origins dello store.
- `core/embed_blocks.py`: `BlockSpec(id="newsletter", group="content", needs=form_id)`
  — nel builder store si può inserire un form esistente dell'org.
- `server.py`: registra il router.

**SDK / packages**
- `apps/embed-sdk/src/components/afianco-newsletter-form.ts`: web component Lit
  (consuma context `client`+`locale`; rende i `field_configs`; validazione +
  consenso; legge attributo `source` + `window.location.href`/`document.referrer`
  e li passa nel submit (D7); `client.newsletter.submit(...)`; eventi
  `afianco:newsletter-subscribed`).
- `packages/shared-types/src/embed-newsletter.ts` + export.
- `packages/api-client`: namespace `newsletter.submit(...)` (+ `confirm` se double).
- i18n SDK: chiavi `newsletter.*` (it/en/de/fr).
- `embed:rebuild` per il bundle.

**Frontend admin**
- **Feature top-level dedicata** `features/newsletter/` (NON tab di StoresPage,
  perché i form non sono store-bound): lista/CRUD form (riusa `FieldEditorList` +
  toggle name/phone), gestione `allowed_origins`, modale embed (riusa pattern
  ShareStore/EmbedComposer), lista submissions **con colonna/filtro/raggruppamento
  per sorgente (D7)** + campo "etichetta sorgente" nello snippet generato,
  associazione store **opzionale**. `api/newsletter.js`. Nuova voce di navigazione.

### 3.3 Integrazione Customer Insights (per D1=A consigliata)
- `build_customer_list`: includere i `customers` privi di metrics (union), con
  metrics-zero + segmento `lead`/`subscriber`. Filtro `marketing_opted_in` già
  presente → "iscritti newsletter" filtrabile out-of-the-box.
- Eventuale nuovo segmento/badge "Solo newsletter" (zero acquisti + opted_in).
- Sentinel: subscriber-only opted-in compare in lista con `marketing_opted_in=true`,
  `has_account=false`, `transaction_count=0`.

---

## 4. Cosa si RIUSA vs cosa è NUOVO

| Area | Riuso | Nuovo |
|---|---|---|
| Opt-out / unsubscribe | ✅ marketing_consent router + token + pagina /u | — |
| Opt-in triple-write | ⚠️ da **estrarre** in service condiviso | service + 1 call |
| Stato "iscritto" | ✅ campi marketing su customers/accounts | — |
| Customer upsert | ✅ `upsert_by_email(source=...)` | — |
| Campi form | ✅ FieldConfig + editor + renderer | estendere `type` |
| Embed (component/CORS/builder/api-client/i18n) | ✅ tutto il pattern | 1 component + 1 endpoint + 1 block + tipi |
| CRUD admin | ✅ pattern coupons/store_embed | router + models + UI |
| Customer Insights | ✅ filtri/CSV/stato marketing | union non-acquirenti (D1) |

---

## 5. Piano a fasi (ognuna isolata, con sentinel)

- **F0 — Estrazione condivisa — ✅ FATTO**: creato `services/marketing_consent_service.py`
  con `record_marketing_optin(...)` (audit merchant_marketing + dual snapshot sync
  accounts/customers, most-recent-wins, sync best-effort). Checkout
  (`order_creation_service`) refactorato per delegare (parità esatta). Signup
  lasciato invariato (audit-only + campo a creazione account; unificazione opz.
  futura). Sentinel `test_f0_marketing_consent_service.py` (3) + re-pointing INV-3
  business_flow + order_creation_service ai nuovi marker nel service. Suite
  backend: 3764 passed, 0 failed.
- **F1 — Backend Newsletter core — ✅ FATTO**:
  - `models/field_config.py`: esteso `type` con `email/tel/select/checkbox` +
    `options` (validator: select richiede ≥1 opzione, altri tipi azzerati).
  - `models/newsletter.py`: `NewsletterForm`(+Create/Update) org-scoped, store
    opzionale, slug+allowed_origins propri, collect_name/phone, field_configs,
    privacy_required; `NewsletterSubscription` con campi sorgente D7; payload
    `NewsletterSubmitRequest/Response`.
  - `database.py`: collection `newsletter_forms`/`newsletter_subscriptions` +
    indici (slug unico per org, dedup unique (org,form,email)).
  - `routers/newsletter_forms.py` (admin, `require_verified_admin`): CRUD +
    allowed-origins + submissions (filtro per sorgente). Registrato in server.py.
  - `embed_public.py`: `POST /public/embed/newsletter/{form_id}/submit` (path per
    **form_id** uuid, coerente con product-id): honeypot → form attivo → consenso
    → upsert customer (source=newsletter_form, first-touch acquisition_source) →
    `record_marketing_optin` (F0) → upsert subscription (dedup email) + sorgente.
  - `core/rate_limiting.py`: `get_real_ip_with_slug` riconosce anche `form_id`
    (isolamento per-form, sentinel SEC-E.1.4 rispettato).
  - Test `test_f1_newsletter_backend.py` (8): modelli + submit (customer+optin+
    subscription, sorgente D7, dedup, honeypot, consenso, first-touch). Suite
    backend: 3770 passed, 0 failed. CORS cross-origin browser → F2.
- **F2 — SDK component + embed — ✅ FATTO**:
  - Backend: `GET /public/embed/newsletter/{form_id}` (config public-safe,
    `NewsletterFormPublic`); `dynamic_cors` risolve `form_id → newsletter_forms.
    allowed_origins` via identità prefissata `nlform:{id}` (riusa flusso+cache),
    invalidazione cache su update allowed-origins; blocco builder `newsletter`
    in `embed_blocks` (`<afianco-newsletter-form form-id="...">`).
  - shared-types: `embed-newsletter.ts` (FieldConfig/FormPublic/Submit*).
  - SDK: `afianco-newsletter-form.ts` **autonomo** (no context/kernel): legge
    `form-id`/`base-url`/`source`, fetcha config, rende built-in+custom fields,
    valida+consenso, POST submit con sorgente D7 (location.href/referrer/source),
    honeypot, success/redirect. Registrato in index.ts. i18n `newsletter.*` 4 lingue.
    Bundle ricostruito.
  - Test: SDK `afianco-newsletter-form.test.ts` (4, contratto fetch+eventi) +
    backend `test_f2_newsletter_embed.py` (5: CORS form_id, config public-safe,
    blocco). Backend 3775 passed; SDK 156 passed (15 fail pre-esistenti invariati).
- **F3 — Admin UI — ✅ FATTO**: `api/newsletter.js` (CRUD + allowed-origins +
  submissions + `buildNewsletterSnippet`); feature dedicata
  `features/newsletter/NewsletterPage.js` (lista form + dialog create/edit con
  `FieldEditorList` riusato [tipi text/textarea/number/email/tel/checkbox] +
  toggle name/phone + consenso + `allowed_origins` textarea; modale "Incorpora"
  con snippet copia-incolla + warning domini; dialog "Iscritti" filtrabile per
  sorgente). Route `/newsletter` in App.js, voce nav (icona Mail) in Layout
  `dynamicOpsNav`, i18n `nav.newsletter` 4 lingue. Frontend compila pulito
  (0 errori); API admin raggiungibile + auth-gated (403). Verifica in-browser
  lato utente (preferenza "testo io").
- **F4 — Integrazione Customer Insights — ✅ FATTO** (D1): `build_customer_list`
  ora fa la **union** `customers ∪ customer_metrics` — i clienti CRM senza riga
  metriche (es. iscritti newsletter senza ordini) compaiono come **lead**
  (metriche zero, `segment='lead'`), con stato marketing risolto dal CRM. Filtri
  coerenti: lead inclusi solo se `segment` ∈ {none, 'lead'} e nessun filtro
  status/min_revenue; il filtro `marketing_opted_in=true` li include. Per
  `segment='lead'` si usa `find_metric_customer_ids` (set globale acquirenti) per
  non riaggiungere acquirenti come lead; per `segment=None` si riusano i metrics
  già in memoria (no query extra → nessuna regressione sui test esistenti).
  Frontend: chip filtro 'lead' in `SegmentFilters` + traduzione `segment.lead`
  (4 lingue); il badge segment già gestiva valori sconosciuti (fallback 'outline').
  Test `test_f4_customer_insights_leads.py` (3) + 27 test customer_insights
  esistenti verdi. Suite backend: 3778 passed, 0 failed.

---

## ✅ MVP COMPLETO (F0–F4)
Il modulo Newsletter è **funzionante end-to-end**: creazione form da UI admin →
embed standalone su sito esterno (CORS per-form) → iscrizione (opt-in marketing
condiviso + sorgente D7) → iscritto visibile e segmentabile in Customer Insights
anche senza acquisti. Unsubscribe già coperto dall'infra esistente.
Rimangono opzionali: **F5** (double opt-in) e **F6** (hardening/analytics).

---

## ✅ F7 — Preview, colori, privacy policy, email-default (2026-06-19)
Enhancement post-MVP richiesti dall'utente.
- **Email default + nome/telefono**: l'email è sempre raccolta (non un toggle, non
  un campo extra); UI admin mostra "Email (sempre richiesta)" + checkbox Nome/Telefono.
- **Colori (theming)**: `NewsletterForm.theme {primary_color, primary_text_color}`
  (hex-validati) → esposti nella config pubblica → il componente li mappa a
  `--afianco-color-primary/-contrast` sull'host (set-or-remove per il preview live).
  Admin: toggle "Personalizza colori" + 2 color picker.
- **Preview live**: componente esteso con `@property config` (bypassa fetch) +
  `preview` (no submit reale, mostra esito). React `NewsletterFormPreview` carica
  una volta il bundle SDK e inietta la config via ref → anteprima istantanea di
  campi/colori/privacy NON salvati, riusando lo STESSO web component (no duplicazione).
- **Privacy policy (riuso per-store, scelta utente)**: `privacy_mode`
  ('none'|'store'|'custom') + `privacy_store_id` + `privacy_custom_url`.
  Risoluzione server `_resolve_newsletter_privacy_url`: 'store' → riusa il route
  pubblico esistente `{APP_BASE_URL}/s/{slug}/privacy` (servito da routers/legal.py,
  zero duplicazione); 'custom' → URL utente; 'none' → nessun link. Il componente
  linka la privacy nel consenso. Admin: select modo + selettore store con stato
  privacy (`PrivacyStoreStatus` via storeLegalAPI) + **bottone "Crea privacy" che
  riapre lo STESSO `MerchantLegalDialog` dell'ecommerce** sullo store scelto →
  auto-link. NB: il sistema legale è solo per-store → niente nuovo modello org-level.
- **Test**: backend `test_f7_newsletter_privacy_theme.py` (4: risoluzione privacy
  custom/none/store, theme hex, config shape); SDK `afianco-newsletter-form` INV-NLF-6
  (preview: no fetch + theme CSS var + privacy link). Backend 3782 passed, 0 failed;
  SDK 157 passed (15 fail pre-esistenti invariati); frontend compila pulito.
- **F5 — (opz.) Double opt-in**: email di conferma + endpoint confirm + status.
- **F6 — Hardening**: anti-bot/honeypot, dedup, rate-limit fine, analytics submissions.

---

## 6. Decisioni — ✅ TUTTE PRESE (2026-06-19)
- D1 = **A. Union** nella lista Insights (non-acquirenti visibili, segmento `lead`).
- D2 = **estendere FieldConfig** (`email|select|checkbox|tel`).
- D3 = **opt-in singolo** (MVP); double opt-in → F5.
- D4 = **form per-org, store opzionale**, slug + allowed_origins propri.
- D5 = rate-limit + dedup email + honeypot.
- D6 = campi built-in email (required) + name/phone opzionali + custom fields.
- D7 = tracciamento sorgente per iscrizione (server Origin/Referer + client URL/referrer
  + etichetta opzionale `source`); first-touch su customer.metadata.acquisition_source.

➡️ Piano congelato. Avvio dalla **F0** (estrazione `marketing_consent_service`),
poi F1→F4 (MVP completo), F5 (double opt-in) e F6 (hardening) opzionali.
