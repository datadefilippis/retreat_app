# Embed Widget — Troubleshooting Guide

> Diagnostica rapida per i problemi piu' comuni del widget AFianco embed.
> Ogni sezione segue il pattern **Sintomo → Causa → Fix**.

## Indice

1. [Widget non si carica](#widget-non-si-carica)
2. [Errori CORS / Origin](#errori-cors--origin)
3. [Bundle cache stale](#bundle-cache-stale)
4. [Catalogo vuoto / prodotti mancanti](#catalogo-vuoto)
5. [Checkout fallisce](#checkout-fallisce)
6. [Coupon non applicato](#coupon-non-applicato)
7. [Customer login / signup](#customer-login--signup)
8. [Cart drawer overlay sopra modal](#cart-drawer-overlay)
9. [Multi-lingua: stringhe non tradotte](#multi-lingua)
10. [Eventi analytics non sparati](#analytics)
11. [Design tokens / brand non applicati](#design-tokens)
12. [Performance: bundle troppo grosso](#performance)

---

## Widget non si carica

**Sintomo**: pagina merchant carica ma il container `<afianco-storefront-init>`
resta vuoto. Nessun prodotto visibile.

### Diagnosi 30 secondi

1. Apri DevTools (F12) → **Console**
2. Cerca log con prefisso `[afianco-embed]` o `[afianco-init]`
3. Verifica nel **Network** tab che `/embed/v1/afianco-embed.es.js`
   sia caricato con status `200`
4. Verifica che la chiamata `/api/public/embed/init/{slug}` sia stata fatta
   e abbia ritornato `200`

### Cause comuni

| Sintomo console | Causa | Fix |
|---|---|---|
| `404 Not Found` su `/init/{slug}` | Slug sbagliato | Verifica admin → Store → slug |
| `403 Forbidden` su `/init/{slug}` | Origin non in allowlist | Aggiungi origin in "Condividi" modal |
| `Failed to fetch afianco-embed.es.js` | Bundle URL down/typo | Verifica URL `app.afianco.ch/embed/v1/...` |
| Console silenziosa, nessun log | Script non eseguito | Verifica `type="module"` nel `<script>` tag |
| `Uncaught SyntaxError: Unexpected token` | Browser non supporta ES modules | Browser troppo vecchio (>Chrome 80, >Safari 13) |

---

## Errori CORS / Origin

**Sintomo**: Console mostra
```
Access to fetch at 'https://api.afianco.app/...' from origin 'https://miosito.com'
has been blocked by CORS policy
```

### Causa

Il backend AFianco usa **DynamicCORSMiddleware**: ogni store ha la sua
allowlist di origin autorizzati (configurabile dal merchant).
Se l'origin del browser NON corrisponde a nessuno della allowlist,
il preflight `OPTIONS` ritorna `403` e il browser blocca la richiesta.

### Fix

1. Admin AFianco → Store → **Condividi**
2. Sezione "Origin autorizzati"
3. Aggiungi il dominio del tuo sito **senza trailing slash**:
   ```
   ✅ https://miosito.com
   ❌ https://miosito.com/
   ❌ miosito.com  (manca https://)
   ```
4. Salva. La modifica e' attiva entro 30 secondi (cache invalidation).

### Origin speciali

- `null` — uso file:// (test locale aprendo HTML direttamente)
- `http://localhost:8080` — dev server locale
- Wildcards subdomain (es. `https://*.miosito.com`) **non supportati**
  per security: lista i subdomini esplicitamente.

---

## Bundle cache stale

**Sintomo**: aggiorni il widget ma il browser mostra ancora la vecchia
versione. UI bug gia' fixati sono ancora visibili.

### Causa #1 — Bundle dist/ non sincronizzato a frontend/public

Pre-deploy / dev locale: il workflow build genera `apps/embed-sdk/dist/`
ma il CRA dev server serve da `frontend/public/embed/v1/`. Step di
sync manuale.

**Verifica**:
```bash
diff -q apps/embed-sdk/dist/afianco-embed.es.js \
        frontend/public/embed/v1/afianco-embed.es.js
```

Se i file differiscono → bundle stale. Fix:
```bash
pnpm embed:rebuild        # build + sync atomic
# OPPURE
pnpm embed:build && pnpm embed:sync-dev
```

Sentinel `TestSEC_E_7_6_EmbedBundleSyncFreshness` blocca CI se i 2
file divergono (SHA256 hash comparison).

### Causa #2 — CDN / browser cache

### Fix

Aggiungi un cache-buster query string:

```html
<script type="module"
  src="https://app.afianco.ch/embed/v1/afianco-embed.es.js?v=20260605">
</script>
```

Strategia consigliata: usa la **data ISO** come versione → bumpa ad ogni
deploy del tuo sito. Oppure usa un hash semver se gestisci versioning
formale del tuo CMS.

### Hard reload per testing

- Chrome / Edge: `Cmd+Shift+R` (mac) / `Ctrl+Shift+R` (win)
- Safari: `Cmd+Option+R`
- Firefox: `Cmd+Shift+R`

---

## Catalogo vuoto

**Sintomo**: widget si carica (header visibile) ma `<afianco-product-grid>`
mostra "Nessun prodotto disponibile" anche se ne hai pubblicati nell'admin.

### Diagnosi

1. Network tab → cerca `GET /api/public/embed/catalog/{slug}`
2. Verifica response JSON: `products[]` e' vuoto?
3. Se vuoto: il problema e' lato backend (filter / pubblicazione)
4. Se popolato ma UI vuota: il problema e' lato widget (filter q/category)

### Cause comuni

- **Prodotti `draft`**: solo `status=published` sono mostrati al widget.
  Admin → Prodotto → check status.
- **Visibility=hidden**: prodotti con `visibility=hidden` non sono nel
  catalog public. Cambia a `visible`.
- **Filter `q` attivo**: search bar pre-popolato con query che non matcha.
  Reset cliccando la X nel search input.
- **Category filter sticky**: il merchant ha categorie ma nessun prodotto
  in quella selezionata. Switcha a "Tutti".

---

## Checkout fallisce

**Sintomo**: cliccando "Procedi al checkout" → loader infinito o errore
"Errore creazione checkout".

### Diagnosi

1. Network tab → cerca `POST /api/public/embed/checkout/start/{slug}`
2. Status code della risposta?

| Status | Causa | Fix |
|---|---|---|
| `400 Bad Request` | Payload invalido (es. quantity=0, customer email malformata) | Verifica form fields obbligatori |
| `402 Payment Required` | Stripe account merchant non collegato | Admin → Pagamenti → connetti Stripe |
| `403 Forbidden` | Origin non in allowlist (vedi sopra CORS) | Aggiungi origin |
| `409 Conflict` | Coupon scaduto / sold out durante checkout | Refresh + retry |
| `422 Unprocessable Entity` | Schema validation fail (es. shipping option non valida) | Vedi response detail JSON |
| `500 Internal` | Bug backend | Apri ticket support |

### Coupon race condition

Se hai un coupon con `max_uses=N` e N customer click "Applica" simultaneo:
- Dry-run (`/coupons/validate/{slug}`) → tutti vedono "valido"
- Real checkout (`/checkout/start`) → solo i primi N riescono,
  gli altri ricevono `409 coupon_exhausted`

Pattern by-design. Il widget mostra error toast e suggerisce di rimuovere
il coupon.

---

## Coupon non applicato

**Sintomo**: customer inserisce codice nel campo coupon, click "Applica",
ma `couponError` mostra "Codice non valido".

### Cause possibili

1. **Codice mistyped**: case-sensitive. `SCONTO10` ≠ `sconto10`.
   Il widget normalizza in uppercase prima di submit, ma controlla
   spazi extra (`  SCONTO10`).
2. **Coupon disattivato**: admin → Coupon → check `is_active=true`.
3. **Coupon expired**: `expires_at` nel passato.
4. **Max usage raggiunto**: `used_count >= max_uses`.
5. **Min order amount non soddisfatto**: se coupon ha `min_order_amount=50€`
   e il carrello e' 30€ → respinto.
6. **Scope item-restricted**: coupon valido solo per certi prodotti, e il
   carrello ne ha altri → respinto.

### Debug

Apri Network tab → POST `/coupons/validate/{slug}` → response JSON:
```json
{
  "valid": false,
  "reason": "expired",
  "message": "Questo codice e' scaduto il 30/05/2026"
}
```

Il campo `reason` ti dice esattamente quale check fallisce.

---

## Customer login / signup

**Sintomo**: customer tenta login → "Credenziali errate" anche con
password corretta.

### Causa

Token JWT scoped per slug:
```
localStorage[afianco_token_{slug}] = "eyJ..."
```

Se il customer ha account su 2 store diversi (slug-a, slug-b), i token
sono separati per security multi-tenant. Login su slug-a NON da' accesso
a slug-b.

### Diagnosi password reset

1. Customer click "Password dimenticata?"
2. Inserisce email
3. Backend invia email con link → `app.afianco.ch/reset-password?token=X`
4. Customer clicca → atterra sul storefront classico (non sul tuo sito embed)
5. Reset password → ritorna al tuo sito → login con nuova password

**Nota**: il flow di reset password atterra **sempre** su afianco.ch
perche' il widget non puo' gestire il routing post-email cross-origin
in modo sicuro. UX accettato.

### GDPR Erasure

Customer puo' richiedere cancellazione dal portale widget:
- Profilo → "Cancella account"
- Conferma checkbox + email re-inserita
- Backend marca `deletion_requested_at` + invia email conferma
- Cancellazione effettiva entro 30 giorni (windows reversibili)

---

## Cart drawer overlay

**Sintomo (FIXED in E3.1)**: cart drawer apre su click checkout button,
ma rimane visible sopra il modal checkout (z-index war).

### Status

✅ **Fixato in E3.1** con due defense:

1. `afianco-cart-drawer.ts:691-696` chiude il drawer con `setTimeout(50)`
   prima di aprire il modal checkout
2. `afianco-checkout-button.ts` usa `z-index: calc(var(--afianco-z-modal) + 10)`
   per il scrim → garantisce che il modal sia sempre sopra qualsiasi
   drawer

### Verifica regression

Se vedi ancora il bug:
1. Bump cache-buster del bundle (vedi sopra)
2. Verifica nel DevTools che il bundle abbia hash recente (Network → response headers `etag`)
3. Inspect element sul cart drawer → conferma `z-index` < `z-index` del modal

---

## Multi-lingua

**Sintomo**: hai attivato `en` come lingua nell'admin ma il widget
mostra ancora label in italiano.

### Diagnosi

1. DevTools → Console → digita:
   ```js
   localStorage.getItem('afianco_lang_TUO-SLUG')
   ```
2. Se ritorna `null` → il widget non ha mai impostato preferenza
3. Se ritorna `"it"` → l'utente ha esplicitamente scelto italiano

### Forzare lingua

3 modi:

1. **URL query param**:
   ```
   https://miosito.com/shop?lang=en
   ```
2. **Attributo `lang` sul host**:
   ```html
   <afianco-storefront-init slug="x" lang="en">
   ```
3. **localStorage diretto** (debug):
   ```js
   localStorage.setItem('afianco_lang_TUO-SLUG', 'en')
   location.reload()
   ```

### Browser detect fallback

Se nessun override, widget legge `navigator.language`:
- `en-US`, `en-GB` → `en`
- `it-IT`, `it-CH` → `it`
- altre lingue → fallback a `it` (base)

### Stringhe missing

Se vedi una key tipo `cart.empty` invece del testo tradotto:
- Bug nel dictionary `en.ts` (key mancante)
- Apri ticket con il key esatto + lingua

---

## Analytics

**Sintomo**: hai aggiunto `<afianco-analytics-bridge gtm gtag>` ma GTM
non riceve eventi.

### Verifica setup

1. Console:
   ```js
   window.dataLayer  // deve essere array
   window.gtag       // deve essere function
   ```
2. Se entrambi `undefined` → GTM/GA non installato sulla tua pagina.
   Aggiungi snippet GTM/GA standard PRIMA del widget.

3. Console listener test:
   ```js
   document.addEventListener('afianco:add-to-cart', (e) => console.log(e.detail))
   ```
   Aggiungi 1 prodotto al carrello → vedi il log?

### Eventi supportati

| Widget event | GA4 event name |
|---|---|
| `afianco:view-item` | `view_item` |
| `afianco:add-to-cart` | `add_to_cart` |
| `afianco:begin-checkout` | `begin_checkout` |
| `afianco:purchase` | `purchase` |
| `afianco:login` | `login` |
| `afianco:sign-up` | `sign_up` |

### Privacy

**Zero PII** nei payload analytics:
- ✅ `product_id`, `qty`, `value`, `currency`
- ❌ NON viene mai inviato: email, nome, address, IP, telefono

---

## Design tokens

**Sintomo**: hai configurato `brand_color=#FF5500` nell'admin ma il widget
mostra ancora il colore default blu.

### Diagnosi

1. DevTools → Inspect su un button del widget
2. Computed styles → cerca `--afianco-color-primary`
3. Valore?

| Valore osservato | Causa |
|---|---|
| `#4b72ce` (default) | Init non ha ricevuto `branding` dal backend |
| `#FF5500` ma button blu | Override CSS conflitto |
| `undefined` | Browser non supporta CSS variables (improbabile 2026) |

### Fix init mancante

Network tab → `/init/{slug}` response:
```json
{
  "branding": {
    "brand_color": "#FF5500",
    ...
  }
}
```

Se `branding` e' `null` o brand_color mancante → bug admin (config
non salvata). Re-salva nel pannello admin.

### Override esplicito

Se vuoi forzare colori specifici sul widget (override admin):

```html
<afianco-storefront-init
  slug="x"
  style="
    --afianco-color-primary: #FF5500;
    --afianco-color-primary-text: #FFFFFF;
    --afianco-radius-md: 16px;
  ">
```

CSS variables hanno priorita' su `branding` di init.

### Storefront vs Widget design tokens

⚠️ Conosciuto gap V1: storefront classic usa `--sf-*` namespace,
widget usa `--afianco-*`. Configurando nell'admin **una sola volta**
entrambi i namespace ricevono lo stesso valore via backend (single
source). Pattern accettato per V1 — refactor architetturale in V2.

---

## Performance

**Sintomo**: caricamento iniziale del widget > 2 secondi su 4G.

### Bundle size attuale

- ES module: **~426 KB** raw / **~85 KB gzip**
- 35+ web components Lit registrati
- 2 locale dictionaries (IT + EN) bundled
- Zero dipendenze esterne runtime

### Ottimizzazioni gia' applicate

- ✅ Tree-shaking via Vite production build
- ✅ Lit components con Shadow DOM (CSS scoped, no global pollution)
- ✅ Lazy fetch del catalog (NON precarica all'init)
- ✅ Image lazy loading nativo (`loading="lazy"`)
- ✅ Gzip compression CDN (Cloudflare)
- ✅ HTTP/2 multiplexing per assets

### Ulteriori miglioramenti (roadmap V2)

- ⏳ Code splitting per feature gate (course player, booking calendar)
- ⏳ Preload init endpoint via `<link rel="preconnect">`
- ⏳ Service worker per cache offline-first
- ⏳ WebP fallback automatic per images

### Misurazioni reali

Test su `app.afianco.ch/embed/v1/afianco-embed.es.js`:

| Connessione | Init load time | Catalog fetch | Total Time-to-Interactive |
|---|---|---|---|
| Fiber 100Mbps | 150ms | 80ms | ~400ms |
| 4G LTE | 600ms | 250ms | ~1.2s |
| 3G slow | 2.3s | 800ms | ~3.5s |

Se i tuoi numeri sono significativamente piu' alti → apri ticket
con HAR file (Network → "Save all as HAR with content").

---

## Supporto avanzato

Se hai seguito tutta la guida e il problema persiste:

1. **Raccogli evidence**:
   - Screenshot della Console (con errori visibili)
   - HAR file della Network tab
   - URL della pagina + slug del tuo store
   - Browser + OS + versione
2. **Email**: `davide@afianco.ch`
3. **Subject**: `[EMBED-TROUBLE] {slug} — breve descrizione`

Response time target: 24h working days.

### Status page

Verifica stato infra prima di aprire ticket: `status.afianco.ch`
- API health
- Database latency
- CDN bundle availability
- Stripe connectivity

Se incident in corso → ti unisci alla coda di update automatica.

---

## Appendice — Comandi DevTools utili

```js
// Stato init corrente
document.querySelector('afianco-storefront-init').initData

// Customer attivo (login)
localStorage.getItem('afianco_token_TUO-SLUG')

// Locale attivo
localStorage.getItem('afianco_lang_TUO-SLUG')

// Cart items (in-memory)
document.querySelector('afianco-cart-drawer').items

// Force re-init (debug)
document.querySelector('afianco-storefront-init').reinitialize()

// Sniff tutti gli eventi widget
['afianco:add-to-cart', 'afianco:purchase', 'afianco:login']
  .forEach(ev => document.addEventListener(ev, e => console.log(ev, e.detail)))
```
