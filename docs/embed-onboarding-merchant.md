# Merchant Onboarding — Embed Widget AFianco

> Onboarding **5 minuti** per integrare il widget AFianco nel tuo sito.

## TL;DR — Copy-paste e via

1. **Login admin** → `app.afianco.ch` con il tuo account
2. **Store → Condividi** → click "Mostra snippet embed"
3. **Aggiungi origin del tuo sito** alla allowlist (es. `https://miosito.com`)
4. **Copia lo snippet** e incollalo nel tuo HTML

```html
<script type="module" src="https://app.afianco.ch/embed/v1/afianco-embed.es.js"></script>
<afianco-storefront-init slug="tuo-store-slug">
  <afianco-header></afianco-header>
  <afianco-account hide-trigger></afianco-account>
  <afianco-product-grid show-search></afianco-product-grid>
  <afianco-product-detail></afianco-product-detail>
  <afianco-cart-drawer hide-trigger></afianco-cart-drawer>
  <afianco-checkout-button></afianco-checkout-button>
</afianco-storefront-init>
```

**Fatto.** Il widget si auto-bootstrap, fetcha il tuo catalogo, e renderizza
prodotti + cart + checkout + portale customer.

---

## Personalizzazione brand

Il widget eredita automaticamente:
- **Logo** + **nome store** (configurato nell'admin)
- **Colori** (`brand_color`, `brand_color_text`)
- **Design tokens Phase 9** (`accent_color`, `font_family`, `border_radius`,
  `density`, `header_style`, `card_style`)

Configura una sola volta nell'admin → si propaga sia al `afianco.ch/s/{slug}`
sia al widget embed.

### Override CSS variables custom

Per override puntuale di colori/spaziature, applica inline style sull'host:

```html
<afianco-storefront-init
  slug="tuo-store"
  style="
    --afianco-color-primary: #FF5500;
    --afianco-font-family: 'Inter', sans-serif;
    --afianco-radius-md: 14px;
  ">
  <!-- componenti -->
</afianco-storefront-init>
```

---

## Configurazione multi-lingua

Il widget supporta **IT + EN** out-of-the-box. Per attivare:

1. Admin store → Lingue → seleziona `it`, `en` (anche `de`, `fr` per
   storefront classico)
2. Widget rileva automaticamente la lingua del browser
3. Customer puo' cambiare manualmente via icona 🌐 nell'header

URL deep-link:
```
https://miosito.com/shop?lang=en   # forza inglese
```

---

## Feature gates configurazione

### Coupon

Configura codici sconto nell'admin → automaticamente disponibili al widget
checkout. Customer inserisce il codice nel campo "🎟️ Codice promo".

### Shipping

Per prodotti `physical` con fulfillment shipping:

1. Admin → Spedizioni → crea le opzioni (es. "Standard €5", "Express €10")
2. Imposta optional `free_shipping_threshold` (es. €100 free)
3. Widget mostra automaticamente il radio picker al checkout

### Eventi + biglietti

1. Crea prodotto `event_ticket` nell'admin
2. Aggiungi `occurrence` (date evento) + `tier` (categorie biglietto)
3. Se `requires_attendee_details=true`, il widget raccoglie nome+email
   per ogni biglietto al checkout
4. Post-acquisto: customer riceve email con link QR + PDF + .ics

### Videocorsi (course)

1. Crea prodotto `item_type=course` nell'admin
2. Configura modules + lessons con Bunny Stream video URL
3. Customer dopo acquisto vede "I miei corsi" nel portale widget
4. Click su corso → iframe player Bunny + progress heartbeat automatico

---

## Customer authentication

Il widget gestisce tutto:
- **Signup** inline al checkout (checkbox "Crea account")
- **Login** standalone (drawer account)
- **Password reset** via email (link → storefront classico per reset)
- **GDPR Art.17 erasure** dal portale customer

Token JWT salvato in `localStorage[afianco_token_{slug}]` — scoped per
slug per supportare multi-merchant sulla stessa origin.

---

## Analytics (opzionale)

Aggiungi `<afianco-analytics-bridge>` al snippet per dispatchare automaticamente
eventi al tuo Google Tag Manager o GA4:

```html
<afianco-analytics-bridge gtm gtag></afianco-analytics-bridge>
```

Eventi inviati: `view_item`, `add_to_cart`, `begin_checkout`, `purchase`,
`login`, `sign_up`. Zero PII per privacy compliance.

---

## Common errors

### "Origin non autorizzato"

Il browser invia un Origin header che NON è nella tua allowlist:

```
Browser → https://miosito.com  ↔  CORS allowlist: ['https://altro.com']
                                    ❌ blocked
```

**Fix**: admin → Store → Condividi → aggiungi `https://miosito.com`
(senza trailing slash).

### Widget non si vede

1. Apri DevTools (F12) → Console
2. Cerca errore `[afianco-embed]`
3. Verifica che lo `slug` nel `<afianco-storefront-init slug="X">`
   corrisponda al tuo store slug nell'admin

### Bundle cache stale

Bumpa il cache buster:
```html
<script src=".../afianco-embed.es.js?v=$(date +%Y%m%d)"></script>
```

---

## Bundle size

- ES module: ~426 KB / **gzip ~85 KB**
- 35+ web components Lit registrati
- Zero dipendenze esterne runtime (Lit included)
- Lazy loading per locale dictionaries (IT + EN bundled)

---

## Supporto

- Email: `davide@afianco.ch`
- Docs complete: `docs/embed-integration-guide.md`
- Audit UX: `docs/embed-ux-symmetry-audit.md`
- Troubleshooting: `docs/embed-troubleshooting.md`
