/**
 * @afianco/embed-sdk — Public entry point.
 *
 * Phase 0 Step 11 (scaffold) + Phase 1 Track C (real components).
 *
 * Importa o registra automaticamente i Web Components esportati. Il merchant
 * include questa entry come <script type="module" src=".../afianco-embed.es.js">
 * e poi può usare i custom elements come tag HTML normali.
 *
 * Esempio:
 *   <script type="module" src="https://cdn.afianco.app/embed/v0/afianco-embed.es.js"></script>
 *   <afianco-storefront-init slug="acme">
 *     <afianco-product-grid></afianco-product-grid>
 *   </afianco-storefront-init>
 *
 * Versioning:
 *   - Major versions in URL path (/embed/v0/, /embed/v1/) — breaking changes
 *   - Minor/patch in CDN cache invalidation policy — backward compatible
 */

// Public API surface — registra i custom elements all'import del bundle.
export { AfiancoTestCard } from './components/afianco-test-card.js';
// Phase 1 Step 22 — Track C root provider
export { AfiancoStorefrontInit } from './components/afianco-storefront-init.js';
// Phase 1 Step 23 — Track C product card
export { AfiancoProductCard } from './components/afianco-product-card.js';
// Phase 1 Step 24 — Track C product grid
export { AfiancoProductGrid } from './components/afianco-product-grid.js';
// Track E Step 2.4.5 — Product detail drawer (landing page).
// Listener su 'afianco:product-view-requested' dispatched dalle card al
// click → apre drawer con description full + qty + CTA "Aggiungi al
// carrello" che dispatcha 'afianco:add-to-cart' al cart-drawer.
export { AfiancoProductDetail } from './components/afianco-product-detail.js';

// Track E Step 2.4.7 — Type-aware picker components (sub-components del
// product-detail drawer). Esposti come building block riusabili per
// merchant che vogliono compositions custom (es. embeddare solo lo slot
// picker senza il drawer detail completo). Tipicamente usati internamente
// da <afianco-product-detail> via dispatch per item_type.
export { AfiancoServiceOptionsPicker } from './components/afianco-service-options-picker.js';
export { AfiancoAvailabilityPicker } from './components/afianco-availability-picker.js';
export { AfiancoOccurrencePicker } from './components/afianco-occurrence-picker.js';
export { AfiancoTierPicker } from './components/afianco-tier-picker.js';
export { AfiancoDateRangePicker } from './components/afianco-date-range-picker.js';
// F2 — modulo Newsletter: form embeddabile autonomo
export { AfiancoNewsletterForm } from './components/afianco-newsletter-form.js';
export { AfiancoCoursePreview } from './components/afianco-course-preview.js';

// Track E Step 2.4.8 — Customer portal sub-components per le nuove tab.
// my-courses + course-player → tab "I miei corsi" (video Bunny iframe +
// progress heartbeat). my-downloads → tab "Download" (signed URL list).
// my-bookings → tab "Prenotazioni" (bookings + reservations unified).
// Usati internamente da <afianco-customer-portal>, esportati anche
// standalone per merchant compositions custom.
export { AfiancoMyCourses } from './components/afianco-my-courses.js';
export { AfiancoCoursePlayer } from './components/afianco-course-player.js';
export { AfiancoMyDownloads } from './components/afianco-my-downloads.js';
export { AfiancoMyBookings } from './components/afianco-my-bookings.js';

// Track E Step 2.4.9 — Extras picker (mandatory/optional/radio_variant).
// Renderizzato dentro <afianco-product-detail> per type physical/digital/
// service/rental (i type con extras configurabili dal merchant nell'admin).
export { AfiancoExtrasPicker } from './components/afianco-extras-picker.js';

// Track E Step 2.4.10 — Live price preview (debounced server-side compute).
// Esposto come building block riusabile per merchant che vogliono mostrare
// il totale in posizioni custom (es. sticky bar dedicata o sidebar).
export { AfiancoPricePreview } from './components/afianco-price-preview.js';

// Track E Step 4.2 — Shipping flow components (fulfillment + options).
// Used internamente da <afianco-checkout-button> ma esposti standalone
// per merchant che vogliono custom checkout layout.
export { AfiancoFulfillmentPicker } from './components/afianco-fulfillment-picker.js';
export { AfiancoShippingOptionsPicker } from './components/afianco-shipping-options-picker.js';

// Track E Step 4.4 — Customer portal editable.
// Edit profile + change password + GDPR erasure request in accordion.
// Used dentro <afianco-customer-portal> tab "Profilo".
export { AfiancoProfileEditor } from './components/afianco-profile-editor.js';

// Track E Step 4.5 — i18n multi-language support.
// Language switcher autohide se store ha solo 1 lingua, dropdown
// compatto con icona globo. Integrato in <afianco-header>.
export { AfiancoLanguageSwitcher } from './components/afianco-language-switcher.js';
// Re-export i18n helpers for merchant integrations custom
export { t, setLocale, getLocale, initLocale, getSupportedLocales } from './i18n/index.js';

// Track E Step 5.4 — Analytics bridge (opt-in component).
// Listen widget events + push to window.dataLayer (GTM) or window.gtag()
// (GA4) con event taxonomy GA4-standard (view_item, add_to_cart, etc.).
// Zero PII inviati per privacy compliance.
export { AfiancoAnalyticsBridge } from './components/afianco-analytics-bridge.js';
// Phase 1 Step 25 — Track C cart drawer
export { AfiancoCartDrawer } from './components/afianco-cart-drawer.js';
// Phase 1 Step 26 — Track C checkout button
export { AfiancoCheckoutButton } from './components/afianco-checkout-button.js';
// Phase 1 Step 27 — Track C customer auth standalone
export { AfiancoLogin } from './components/afianco-login.js';
export { AfiancoSignup } from './components/afianco-signup.js';
// Phase 1 Step 28 — Track C customer portal (chiude Track C)
export { AfiancoCustomerPortal } from './components/afianco-customer-portal.js';
// Track E Step 2.4.2 — full embedding 360 (unified account widget:
// floating button + drawer con login/signup/portal conditional).
// Composito dei components esistenti, no duplicazione logica auth.
export { AfiancoAccount } from './components/afianco-account.js';
// Track E Step 2.4.4 — Unified navbar header. Raccoglie i trigger
// account + cart in un layout ordinato sticky-top. Risolve UX "FAB
// sparsi sui prodotti". Loose coupling via document events
// (afianco:open-account, afianco:open-cart).
export { AfiancoHeader } from './components/afianco-header.js';

// Embed à-la-carte (Fase 2) — elementi "drop-anywhere" per il menu / pagine
// singole. Funzionano fuori da <afianco-storefront-init> via Store Kernel.
export { AfiancoCartButton } from './components/afianco-cart-button.js';
export { AfiancoAccountButton } from './components/afianco-account-button.js';
export { AfiancoProduct } from './components/afianco-product.js';

// Re-export the context for advanced integrations (custom components
// che vogliono partecipare al provider chain afianco).
export {
  storefrontContext,
  STOREFRONT_INITIAL,
  type StorefrontContext,
  type StorefrontStatus,
} from './context.js';

// Embed à-la-carte (Fase 1) — Store Kernel per-slug + config di pagina.
// Infrastruttura per i componenti drop-anywhere (Fase 2). Additivo: non
// cambia il comportamento dei componenti context-based esistenti.
export {
  AfiancoStoreKernel,
  getStoreKernel,
  type KernelState,
  type KernelStatus,
} from './store/kernel.js';
export { getPageConfig, type PageEmbedConfig } from './store/page-config.js';
export { StoreConsumerController } from './store/store-consumer.js';

// Library version (sostituito al build time da vite-define se utile in futuro)
export const VERSION = '0.8.0';

// Convenience banner per il merchant che apre devtools console
if (typeof window !== 'undefined') {
  // eslint-disable-next-line no-console
  console.info(
    `[afianco-embed] v${VERSION} loaded. ` +
    `Available tags: <afianco-test-card>, <afianco-storefront-init>, ` +
    `<afianco-product-card>, <afianco-product-grid>, <afianco-product-detail>, ` +
    `<afianco-cart-drawer>, <afianco-checkout-button>, <afianco-login>, ` +
    `<afianco-signup>, <afianco-customer-portal>, <afianco-account>, ` +
    `<afianco-header>, <afianco-cart-button>, <afianco-account-button>, ` +
    `<afianco-product>. ` +
    `Docs: https://afianco.app/docs/embed`
  );
}
