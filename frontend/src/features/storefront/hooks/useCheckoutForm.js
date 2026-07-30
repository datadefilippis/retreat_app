/**
 * useCheckoutForm — stato + validazioni + submit del checkout storefront.
 *
 * PN2 (PROFILO_NEGOZIO_PIANO_2026-07) — blocchi spostati TALI E QUALI da
 * StorefrontPage.js (stati ~613-694, derivati/validazioni ~1004-1595,
 * handleSubmit ~1597-1851). Il hook riceve le dipendenze della pagina e
 * restituisce tutto cio' che CheckoutForm e la pagina usano. Nessuna
 * logica cambiata: payload di submit byte-identico.
 */
import { useState, useEffect, useMemo } from 'react';
import { toast } from 'sonner';
// Wave GDPR-Commerce CG-5 — fetch the merchant's legal status to know
// whether to render the GDPR consent block on checkout.
import { fetchStorefrontLegalMetadata } from '../../../services/legalService';
import { publicShippingOptions } from '../../../api/shippingOptions';
import { useCheckoutSubmit } from './useCheckoutSubmit';
// Sprint 2 W2.2 — live price preview hook for breakdown discount
import useCouponValidation from './useCouponValidation';
import { useStoreMeta } from '../../../hooks/useStoreMeta';
// 2026-05-20 — Symmetric marketing checkbox visibility (hides the
// box when the customer is already opted-in, regardless of guest or
// registered). See hooks/useIsMarketingOptedIn.js for the lookup
// strategy (logged-in synchronous derivation vs guest debounced
// public endpoint).
import useIsMarketingOptedIn from '../../../hooks/useIsMarketingOptedIn';
import { resolveDominantMode } from '../../../constants/itemTypes';
import { resolveTransactionModeCopy } from '../components/StorefrontCards';
// AP-L — legal a due livelli: il checkout deve sapere se il compratore
// e' loggato con l'account Aurya (consenso gia' timbrato sull'account).
import platformApi, { PLATFORM_TOKEN_KEY } from '../../../api/platformClient';

// Password strength check mirrors backend policy (customer_auth validate_password_strength):
// 12+ chars, at least one uppercase, one lowercase, one digit.
//
// Returns { ok: bool, score: 0..4, reasonCodes: [string] } — the reason
// codes are stable identifiers the caller renders via
// `t('storefront:password.<code>')`. Decoupling the validator from i18n
// keeps it pure (no React/hook dependency) so it can be called from
// useMemo/render paths without coupling, AND lets the strings travel
// through future locales without touching this function.
export function computePasswordStrength(pwd) {
  if (!pwd) return { ok: false, score: 0, reasonCodes: ['enter'] };
  const reasonCodes = [];
  if (pwd.length < 12) reasonCodes.push('minLength');
  if (!/[A-Z]/.test(pwd)) reasonCodes.push('upper');
  if (!/[a-z]/.test(pwd)) reasonCodes.push('lower');
  if (!/[0-9]/.test(pwd)) reasonCodes.push('digit');
  let score = 0;
  if (pwd.length >= 12) score++;
  if (pwd.length >= 16) score++;
  if (/[A-Z]/.test(pwd) && /[a-z]/.test(pwd)) score++;
  if (/[0-9]/.test(pwd) && /[^A-Za-z0-9]/.test(pwd)) score++;
  return { ok: reasonCodes.length === 0, score, reasonCodes };
}

export default function useCheckoutForm({
  slug,
  catalog,
  selectedItems,
  getOrderedTierEntries,
  customer,
  isCustomerAuthenticated,
  customerSignup,
  attendeeDetails,
  setAttendeeDetails,
  orderFieldsData,
  selectedServiceOptions,
  selectedServiceSlots,
  clearCartSnapshot,
  loadAvailability,
  t,
  // PS6.4 — canale ESPLICITO dalla superficie reale: 'store' (profilo
  // /o/, landing raggiunta dal profilo) o 'marketplace' (viaggio dalla
  // directory). Se assente (storefront legacy /s/), si conserva il
  // comportamento storico: il flag di sessione mktp_ctx decide.
  channel,
}) {
  // F4 Onda 11 — T&C acceptance state. PAGE-LOCAL (not part of the
  // sessionStorage snapshot) because the checkbox state should reset
  // on every page mount — a returning visitor must re-affirm.
  const [termsAccepted, setTermsAccepted] = useState(false);
  const [termsExpanded, setTermsExpanded] = useState(false);

  // ── Wave GDPR-Commerce CG-5 (2026-05-19) — per-order consent state ──
  //
  // ``legalMeta`` is the response of GET /api/legal/storefront/<slug>/metadata.
  // Used to decide whether to RENDER the GDPR consent block on the
  // checkout form. If the merchant has not published their per-store
  // legal docs (status="not_configured" / "draft"), this stays null and
  // the block does NOT render — checkout proceeds via the legacy T&C
  // flow only.
  //
  // Three local booleans for the new checkboxes. Reset on every page
  // mount (same intent as termsAccepted above).
  const [legalMeta, setLegalMeta] = useState(null);
  const [gdprTermsAccepted, setGdprTermsAccepted] = useState(false);
  const [gdprPrivacyAccepted, setGdprPrivacyAccepted] = useState(false);
  const [gdprMarketingAccepted, setGdprMarketingAccepted] = useState(false);

  // ── AP-L (2026-07-29) — legal a due livelli ────────────────────────
  // 1. Livello Aurya: per i GUEST una checkbox unica "Accetto i Termini
  //    e la Privacy di Aurya" (auryaAccepted); per chi e' loggato con
  //    l'account Aurya (platformAccount) la checkbox non compare, il
  //    consenso vive gia' sull'account (aurya_legal, timbrato alla
  //    creazione).
  // 2. Livello operatore: checkbox dinamica "Accetto le condizioni di
  //    {operatore}" (operatorTermsAccepted), SOLO se l'operatore ha
  //    compilato politica di cancellazione o requisiti del servizio.
  const [platformAccount, setPlatformAccount] = useState(null);
  const [auryaAccepted, setAuryaAccepted] = useState(false);
  const [operatorTermsAccepted, setOperatorTermsAccepted] = useState(false);

  // Sessione Aurya gia' aperta (token in localStorage): profilo da
  // /platform/me. Token scaduto/invalido → silenzio, resta guest.
  useEffect(() => {
    let token = null;
    try { token = localStorage.getItem(PLATFORM_TOKEN_KEY); } catch { /* private mode */ }
    if (!token) return undefined;
    let active = true;
    platformApi.get('/platform/me')
      .then(res => { if (active) setPlatformAccount(res.data); })
      .catch(() => { /* guest: la checkbox Aurya resta */ });
    return () => { active = false; };
  }, []);

  const platformLoggedIn = !!platformAccount;

  // AP-L — l'atto Aurya del guest assorbe l'accettazione primaria: i
  // flag CG-5 dell'operatore viaggiano insieme alla spunta unica (nel
  // blocco resta linkata anche l'informativa dell'operatore), cosi' la
  // macchina consensi merchant esistente continua a timbrare.
  const setAuryaConsent = (checked) => {
    setAuryaAccepted(checked);
    setGdprTermsAccepted(checked);
    setGdprPrivacyAccepted(checked);
  };

  // Wave GDPR-Commerce CG-5 — fetch the per-store legal metadata so
  // we know whether to render the GDPR consent block on checkout.
  // We only need ``status`` + ``version_string`` + ``display_locale``
  // here; the body content is fetched on demand from the linked pages.
  //
  // Fail-soft: any network/server error leaves ``legalMeta`` at null,
  // which makes the checkout flow fall back to legacy (no GDPR block).
  // Better to silently degrade than to block all checkouts because of
  // a metadata fetch hiccup.
  useEffect(() => {
    if (!slug) return;
    let active = true;
    fetchStorefrontLegalMetadata(slug).then(
      (meta) => { if (active) setLegalMeta(meta); },
      (err) => { console.warn('CG-5: legal metadata fetch failed:', err); }
    );
    return () => { active = false; };
  }, [slug]);

  // Cache slot search results per product
  const [serviceSlotsByProduct, setServiceSlotsByProduct] = useState({});
  const [formOpen, setFormOpen] = useState(false);
  // (Removed `cartExpanded` state — the mini-cart bar that used it
  // was deleted in the post-Phase-7 cleanup pass. Cart review now
  // happens inside the checkout modal's OrderSummary.)
  const [form, setForm] = useState({
    name: '', email: '', phone: '', notes: '',
    fulfillment_mode: '',
    // Structured shipping address. Replaces the legacy single textarea.
    // Submitted as `shipping_address_details` — the backend synthesizes
    // the flattened `shipping_address` string server-side.
    shipping_address_details: {
      recipient_name: '',
      line1: '',
      civic: '',
      postal_code: '',
      city: '',
      province: '',
      country: 'IT',
    },
    fulfillment_notes: '',
    coupon_code: '',
    shipping_option_id: '',
  });
  // Shipping options resolved by the backend for this store. Empty list is
  // a legitimate state (merchant hasn't configured any) — the checkout
  // surfaces a banner in that case so the customer knows to get in touch.
  const [shippingOptions, setShippingOptions] = useState([]);
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(null); // null | { transaction_mode, order_status, message, registered?: bool }
  // Shared checkout submitter (unifies the Stripe redirect path with
  // EventLandingPage). `submitting` above still drives the cart UI
  // loading state since it's woven into the pre-submit registration
  // step; the hook's own submitting flag is unused here on purpose.
  const { submit: submitCheckout } = useCheckoutSubmit();
  // 2026-05-20 — Marketing checkbox visibility resolver.
  // Logged-in path: synchronous from customer.accepted_marketing_at.
  // Guest path: debounced public lookup on form.email change.
  // The hook returns isOptedIn=false when "unknown" (network glitch,
  // email empty/invalid, lookup never ran) so the default behaviour
  // is to KEEP showing the checkbox — never hide it on uncertainty.
  const marketingStatus = useIsMarketingOptedIn({
    customer,
    isAuthenticated: isCustomerAuthenticated,
    email: form.email,
    slug,
  });

  // Optional ecommerce registration during checkout (Fase C1).
  // Strictly scoped to the storefront flow — NEVER touches admin auth.
  // Account creation is handled by POST /api/customer-auth/signup (org-scoped via slug).
  const [wantRegister, setWantRegister] = useState(false);
  // K1 — contesto MARKETPLACE (arrivo dalla landing directory): il
  // checkout e' l'unica cosa che l'utente deve vedere; alla chiusura
  // si torna alla landing. Il flag persiste in sessionStorage per la
  // success page (redirect Stripe = full reload).
  const [mktpCheckout, setMktpCheckout] = useState(null);   // {returnTo} | null
  const [regPassword, setRegPassword] = useState('');
  const [regPasswordConfirm, setRegPasswordConfirm] = useState('');
  const [showRegPassword, setShowRegPassword] = useState(false);

  // Auto-fill form from customer account
  useEffect(() => {
    if (isCustomerAuthenticated && customer) {
      setForm(prev => ({
        ...prev,
        name: prev.name || customer.name || '',
        email: prev.email || customer.email || '',
      }));
    }
  }, [isCustomerAuthenticated, customer]);

  // NOTE: the `useEffect` that forces `wantRegister=true` when the cart
  // contains a course has been moved below — after `requiresCustomerAccount`
  // is declared (see the useMemo further down the file). Referencing a
  // `const` before its declaration triggers a TDZ ReferenceError that
  // crashes the page at first render.

  // Sprint 2 W2.2 — Live coupon discount lifted to main scope so OrderSummary
  // puo' renderizzare il breakdown discount in tempo reale (parity widget E4.1).
  // Computa cart subtotal client-side (mirror del calcolo OrderSummary) e lo
  // passa al hook useCouponValidation che fa POST debounced a
  // /coupons/validate/{slug}. Quando il coupon e' valid, discountAmount > 0
  // -> OrderSummary mostra riga 'Sconto coupon -X EUR' + ricalcola totale.
  const couponSubtotal = useMemo(() => {
    try {
      const prods = catalog?.products || [];
      return (selectedItems || []).reduce((sum, it) => {
        const p = prods.find((x) => x.id === it.product_id);
        if (!p) return sum;
        const price = Number(p.unit_price) || 0;
        return sum + price * (it.quantity || 1);
      }, 0);
    } catch {
      return 0;
    }
  }, [selectedItems, catalog?.products]);

  const couponValidation = useCouponValidation({
    slug,
    code: form.coupon_code,
    cartSubtotal: couponSubtotal,
    enabled: !!form.coupon_code,
  });

  // Shape compatto per props OrderSummary
  const couponValidationState = useMemo(() => ({
    discountAmount: couponValidation.valid ? couponValidation.discountAmount : 0,
    code: couponValidation.valid ? (form.coupon_code || '').trim().toUpperCase() : null,
  }), [couponValidation.valid, couponValidation.discountAmount, form.coupon_code]);

  // Release 4 (Courses) — an order containing at least one course line
  // cannot be submitted as guest. The enrollment is nominative and the
  // customer needs a portal login to access the player. When this flag
  // is true AND the customer is not already authenticated, the checkout
  // modal surfaces the inline login/signup form and disables the
  // "continue as guest" path.
  const requiresCustomerAccount = useMemo(() => {
    const prods = catalog?.products || [];
    return selectedItems.some(it => {
      const p = prods.find(pp => pp.id === it.product_id);
      return p?.item_type === 'course';
    });
  }, [selectedItems, catalog]);

  // Release 4 (Courses) — when the cart contains a course AND the customer
  // is not yet authenticated, force the "crea un account" branch on.
  // Guest checkout is server-side blocked for orders with courses, so
  // the UI mirrors that constraint. Idempotent setter → no render loop.
  // NOTE: placed here (after `requiresCustomerAccount` is declared) to
  // avoid a TDZ ReferenceError on the first render.
  useEffect(() => {
    if (requiresCustomerAccount && !isCustomerAuthenticated && !wantRegister) {
      setWantRegister(true);
    }
  }, [requiresCustomerAccount, isCustomerAuthenticated, wantRegister]);

  // v10.0: Determine if fulfillment choice is needed
  const fulfillmentContext = useMemo(() => {
    const prods = catalog?.products || [];
    const selectedTypes = selectedItems.map(it => prods.find(p => p.id === it.product_id)?.item_type).filter(Boolean);
    const hasPhysical = selectedTypes.includes('physical');
    const hasRental = selectedTypes.includes('rental');
    const storeModes = catalog?.fulfillment_modes || ['shipping'];

    if (hasRental) return { needsChoice: false, autoMode: 'manual_arrangement' };
    if (!hasPhysical) return { needsChoice: false, autoMode: null }; // not_required
    if (storeModes.length === 1) return { needsChoice: false, autoMode: storeModes[0] };
    return { needsChoice: true, modes: storeModes };
  }, [selectedItems, catalog]);

  // Set default fulfillment mode when context changes
  useEffect(() => {
    if (fulfillmentContext.autoMode) {
      setForm(f => ({ ...f, fulfillment_mode: fulfillmentContext.autoMode }));
    } else if (fulfillmentContext.needsChoice && !form.fulfillment_mode) {
      setForm(f => ({ ...f, fulfillment_mode: fulfillmentContext.modes?.[0] || 'shipping' }));
    }
  }, [fulfillmentContext]); // eslint-disable-line react-hooks/exhaustive-deps

  // Refetch shipping options when the checkout modal opens — covers the case
  // where the merchant just configured them in another tab while the customer
  // had the landing open, so they don't have to reload manually.
  useEffect(() => {
    if (!formOpen || !slug) return;
    let mounted = true;
    publicShippingOptions.get(slug)
      .then(res => { if (mounted) setShippingOptions(res.data?.options || []); })
      .catch(() => { /* keep whatever we had from the initial load */ });
    return () => { mounted = false; };
  }, [formOpen, slug]);

  // ── Shipping computation (storefront preview mirror of the backend) ──
  //
  // The backend recomputes shipping at order-create time, so this is a
  // live preview only — never a source of truth for pricing. When the
  // backend accepts the order it trusts ONLY `shipping_option_id` and
  // computes the cost again from the DB. If the two disagree (rare race
  // with the admin editing options), the backend value wins.
  //
  // Triggers:
  //   - cart items change (recomputes physical_subtotal for threshold)
  //   - fulfillment_mode flips to/from "shipping"
  //   - shipping_option_id selection changes
  //   - shipping options list loaded / reloaded
  const hasPhysicalCart = useMemo(() => {
    const prods = catalog?.products || [];
    return selectedItems.some(it =>
      prods.find(p => p.id === it.product_id)?.item_type === 'physical'
    );
  }, [selectedItems, catalog]);

  const physicalSubtotal = useMemo(() => {
    const prods = catalog?.products || [];
    let sum = 0;
    for (const it of selectedItems) {
      const p = prods.find(pp => pp.id === it.product_id);
      if (!p || p.item_type !== 'physical' || p.price_mode === 'inquiry') continue;
      sum += Number(p.unit_price || 0) * Number(it.quantity || 0);
    }
    return Math.round(sum * 100) / 100;
  }, [selectedItems, catalog]);

  const selectedShippingOption = useMemo(() => {
    if (!form.shipping_option_id) return null;
    return shippingOptions.find(o => o.id === form.shipping_option_id) || null;
  }, [form.shipping_option_id, shippingOptions]);

  const shippingSummary = useMemo(() => {
    // Summary feeds the OrderSummary (totals row) + the "add more for free"
    // hint. `active` gates the shipping line visibility.
    if (!hasPhysicalCart) return { active: false, cost: 0, label: null, addMoreForFree: 0 };
    if (form.fulfillment_mode === 'local_pickup') {
      return { active: true, cost: 0, label: t('storefront:checkout.fulfillment.localPickup'), addMoreForFree: 0 };
    }
    if (form.fulfillment_mode !== 'shipping') return { active: false, cost: 0, label: null, addMoreForFree: 0 };
    if (!selectedShippingOption) {
      // Physical + shipping picked but no option chosen yet — OrderSummary
      // suppresses the cost but the row is "active" so the caller can use
      // this flag for button gating.
      return { active: true, cost: 0, label: null, addMoreForFree: 0 };
    }
    const base = Number(selectedShippingOption.base_price || 0);
    const threshold = selectedShippingOption.free_shipping_threshold;
    const free = threshold != null && physicalSubtotal >= Number(threshold);
    const cost = free ? 0 : base;
    const add = (!free && threshold != null) ? Math.max(0, Number(threshold) - physicalSubtotal) : 0;
    return {
      active: true,
      cost,
      label: selectedShippingOption.label,
      addMoreForFree: Math.round(add * 100) / 100,
    };
  }, [hasPhysicalCart, form.fulfillment_mode, selectedShippingOption, physicalSubtotal]);

  // Clear shipping_option_id when the mode flips away from shipping so a
  // stale id doesn't silently travel with a pickup-mode submission.
  useEffect(() => {
    if (form.fulfillment_mode !== 'shipping' && form.shipping_option_id) {
      setForm(f => ({ ...f, shipping_option_id: '' }));
    }
  }, [form.fulfillment_mode]); // eslint-disable-line react-hooks/exhaustive-deps

  // Auto-preselect when there's exactly one shipping option (no-brainer UX).
  useEffect(() => {
    if (
      hasPhysicalCart &&
      form.fulfillment_mode === 'shipping' &&
      shippingOptions.length === 1 &&
      !form.shipping_option_id
    ) {
      setForm(f => ({ ...f, shipping_option_id: shippingOptions[0].id }));
    }
  }, [hasPhysicalCart, form.fulfillment_mode, shippingOptions, form.shipping_option_id]);

  // v5.8 / Onda 4 — read commerce.checkout_stripe flag from /meta payload.
  // When false (Free plan or any plan with Stripe Connect off), we force
  // the request-mode CTA regardless of what the products' transaction_mode
  // says — the backend will downgrade direct → request anyway, so show the
  // truthful CTA upfront ("Richiedi info" instead of "Acquista").
  const { checkoutStripeEnabled } = useStoreMeta();

  // Resolve mode-aware copy from selected products' transaction_mode
  // If direct mode contains rental/event-with-capacity items, direct checkout
  // will be blocked by backend safety — soften the CTA to match reality.
  const modeCopy = useMemo(() => {
    const prods = catalog?.products || [];
    const modes = selectedItems.map(it => prods.find(p => p.id === it.product_id)?.transaction_mode);
    const mode = resolveDominantMode(modes);

    // v5.8 / Onda 4 — if the merchant's plan has checkout_stripe disabled,
    // every order becomes a contact request regardless of product config.
    // Force request copy upfront so the customer sees the right CTA.
    if (checkoutStripeEnabled === false) {
      return resolveTransactionModeCopy(t, 'request');
    }

    if (mode === 'direct') {
      // Check if any item will prevent direct checkout
      const hasRental = selectedItems.some(it => {
        const p = prods.find(pp => pp.id === it.product_id);
        return p?.item_type === 'rental';
      });
      const hasCapEvent = selectedItems.some(it => {
        const p = prods.find(pp => pp.id === it.product_id);
        return p?.item_type === 'event_ticket' && it.occurrence_id;
        // Note: we can't check capacity client-side, but events with occurrences
        // that have capacity will be caught by backend. Conservative: still show
        // direct CTA for events, backend handles the gating truthfully.
      });

      if (hasRental) {
        // Rental in direct mode → checkout won't start, use request-like copy.
        // Lives in a dedicated `rentalOverride` key so the copy can drift
        // from the generic `request` mode without leaking semantics.
        return {
          headerCta:     t('storefront:transactionMode.rentalOverride.headerCta'),
          modalTitle:    t('storefront:transactionMode.rentalOverride.modalTitle'),
          modalDesc:     t('storefront:transactionMode.rentalOverride.modalDesc'),
          submitBtn:     t('storefront:transactionMode.rentalOverride.submitBtn'),
          inquiryToggle: t('storefront:transactionMode.rentalOverride.inquiryToggle'),
        };
      }
    }

    return resolveTransactionModeCopy(t, mode);
  }, [selectedItems, catalog, t, checkoutStripeEnabled]);

  // F1 Onda 8 — which items need per-seat holder forms
  // F3 Onda 10 — aggregate per-product (selectedItems may now contain
  // multiple line items per product, one per tier). `totalQty` is the
  // sum of quantities across tiers; `seatLabels` is a per-seat
  // annotation (e.g. "Biglietto 3 — VIP") used in the dialog.
  const itemsRequiringAttendees = useMemo(() => {
    const prods = catalog?.products || [];
    const byProduct = new Map();
    for (const it of selectedItems) {
      const product = prods.find(p => p.id === it.product_id);
      if (!product || product.item_type !== 'event_ticket') continue;
      if (!product.requires_attendee_details) continue;
      const existing = byProduct.get(it.product_id);
      if (existing) {
        existing.totalQty += Number(it.quantity || 0);
      } else {
        byProduct.set(it.product_id, {
          product,
          totalQty: Number(it.quantity || 0),
        });
      }
    }
    // Build per-seat labels using getOrderedTierEntries (keeps UI in sync
    // with the actual tier-line-items that will be POSTed).
    const out = [];
    for (const { product, totalQty } of byProduct.values()) {
      const tierEntries = getOrderedTierEntries(product.id);
      const seatLabels = [];
      if (tierEntries.length > 0) {
        let n = 1;
        for (const te of tierEntries) {
          for (let i = 0; i < te.qty; i++) {
            seatLabels.push(t('storefront:checkout.attendees.seatLabelWithTier', { index: n, tier: te.label || t('storefront:checkout.attendees.tierFallback') }));
            n++;
          }
        }
      } else {
        for (let i = 0; i < totalQty; i++) {
          seatLabels.push(`Biglietto ${i + 1}`);
        }
      }
      // For backward-compat with existing consumers we still expose
      // `item` with product_id + total quantity (same shape as a plain
      // single-line cart).
      out.push({
        item: { product_id: product.id, quantity: totalQty },
        product,
        seatLabels,
      });
    }
    return out;
  }, [selectedItems, catalog, getOrderedTierEntries]);

  // Keep attendeeDetails[pid] in sync with quantity: resize array up/down,
  // preserving already-filled entries so a qty bump doesn't clear names.
  useEffect(() => {
    setAttendeeDetails(prev => {
      let changed = false;
      const next = { ...prev };
      // Ensure entries for each relevant product
      for (const { item } of itemsRequiringAttendees) {
        const pid = item.product_id;
        const cur = Array.isArray(next[pid]) ? next[pid] : [];
        const qty = Number(item.quantity) || 0;
        if (cur.length !== qty) {
          const resized = Array.from({ length: qty }, (_, i) =>
            cur[i] || { name: '', email: '', phone: '' }
          );
          next[pid] = resized;
          changed = true;
        }
      }
      // Drop entries for products that are no longer in the cart or no
      // longer require attendees (e.g. merchant toggled the policy off).
      const keep = new Set(itemsRequiringAttendees.map(({ item }) => item.product_id));
      for (const pid of Object.keys(next)) {
        if (!keep.has(pid)) { delete next[pid]; changed = true; }
      }
      return changed ? next : prev;
    });
  }, [itemsRequiringAttendees]);

  // Validation helper — are all attendee forms complete and well-formed?
  // F2 Onda 9: respect product.require_attendee_email/phone flags and
  // check that required custom fields are filled.
  const attendeesValid = useMemo(() => {
    if (itemsRequiringAttendees.length === 0) return true;
    const emailRx = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    for (const { item, product } of itemsRequiringAttendees) {
      const entries = attendeeDetails[item.product_id] || [];
      if (entries.length !== Number(item.quantity)) return false;
      const emailReq = product.require_attendee_email !== false;  // default true
      const phoneReq = !!product.require_attendee_phone;
      const requiredCustom = (product.attendee_fields || []).filter(f => f?.required);
      for (const e of entries) {
        if (!e?.name?.trim()) return false;
        if (emailReq) {
          if (!emailRx.test((e?.email || '').trim())) return false;
        } else if (e?.email && !emailRx.test(e.email.trim())) {
          // Not required, but if provided must be valid
          return false;
        }
        if (phoneReq && !(e?.phone || '').trim()) return false;
        const cf = e?.custom_fields || {};
        for (const fc of requiredCustom) {
          const v = cf[fc.id];
          const empty = (v == null) || (typeof v === 'string' && v.trim() === '');
          if (empty) return false;
        }
      }
    }
    return true;
  }, [itemsRequiringAttendees, attendeeDetails]);

  // F2 Onda 9 — order-level custom fields validation. Looks across all
  // event_ticket products in the cart and requires every field marked as
  // `required` on any of them to be non-empty.
  const orderFieldsConfig = useMemo(() => {
    const prods = catalog?.products || [];
    const seen = new Map();
    for (const it of selectedItems) {
      const p = prods.find(pp => pp.id === it.product_id);
      if (!p || p.item_type !== 'event_ticket') continue;
      for (const fc of (p.order_fields || [])) {
        if (fc?.id && !seen.has(fc.id)) seen.set(fc.id, fc);
      }
    }
    // Stable order
    return Array.from(seen.values()).sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0));
  }, [selectedItems, catalog]);

  const orderFieldsValid = useMemo(() => {
    for (const fc of orderFieldsConfig) {
      if (!fc.required) continue;
      const v = orderFieldsData[fc.id];
      const empty = (v == null) || (typeof v === 'string' && v.trim() === '');
      if (empty) return false;
    }
    return true;
  }, [orderFieldsConfig, orderFieldsData]);

  // F5 Onda 12 — list of service products in cart that need the
  // radio options picker and/or slot picker at checkout.
  const serviceItemsInCart = useMemo(() => {
    const prods = catalog?.products || [];
    const out = [];
    for (const it of selectedItems) {
      const p = prods.find(pp => pp.id === it.product_id);
      if (!p || p.item_type !== 'service') continue;
      // Already in cart — dedup by product_id
      if (out.find(x => x.product.id === p.id)) continue;
      out.push({
        item: it,
        product: p,
        options: Array.isArray(p.service_options) ? p.service_options : [],
        hasSlots: !!p.has_availability_slots,
      });
    }
    return out;
  }, [selectedItems, catalog]);

  // Fetch available slots for each service product in cart
  useEffect(() => {
    for (const { product, hasSlots } of serviceItemsInCart) {
      if (!hasSlots) continue;
      if (serviceSlotsByProduct[product.id]) continue;  // already cached
      (async () => {
        try {
          const res = await fetch(`/api/public/services/${product.id}/slots?days=30`);
          if (!res.ok) return;
          const data = await res.json();
          setServiceSlotsByProduct(prev => ({ ...prev, [product.id]: data.slots || [] }));
        } catch { /* silent */ }
      })();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [serviceItemsInCart.length]);

  // F5 Onda 12 — service flow validity: if a product has options, one
  // must be selected; if it has slots, one must be picked.
  const servicesValid = useMemo(() => {
    for (const { product, options, hasSlots } of serviceItemsInCart) {
      if (options.length > 0 && !selectedServiceOptions[product.id]) return false;
      if (hasSlots && !selectedServiceSlots[product.id]?.date) return false;
    }
    return true;
  }, [serviceItemsInCart, selectedServiceOptions, selectedServiceSlots]);

  // F4 Onda 11 — effective T&C: first product (any type) whose
  // pre-resolved terms_content is non-empty. Uniform across events and
  // services (and any future type that populates the field).
  const effectiveTerms = useMemo(() => {
    const prods = catalog?.products || [];
    for (const it of selectedItems) {
      const p = prods.find(pp => pp.id === it.product_id);
      if (p && typeof p.terms_content === 'string' && p.terms_content.trim()) {
        return p.terms_content;
      }
    }
    return null;
  }, [selectedItems, catalog]);

  // AP-L — condizioni dell'operatore: politica di cancellazione del
  // primo prodotto in carrello che ne ha una (payment_plan esposto dal
  // catalogo pubblico) + requisiti del servizio (effectiveTerms sopra).
  const cartCancellationPolicy = useMemo(() => {
    const prods = catalog?.products || [];
    for (const it of selectedItems) {
      const p = prods.find(pp => pp.id === it.product_id);
      const policy = p?.payment_plan?.cancellation_policy;
      if (Array.isArray(policy) && policy.length > 0) return policy;
    }
    return null;
  }, [selectedItems, catalog]);

  // La checkbox dell'operatore esiste SOLO se ha compilato qualcosa.
  const hasOperatorConditions = !!(effectiveTerms || cartCancellationPolicy);

  // AP-L — le condizioni dell'operatore si accettano con la LORO
  // checkbox, per ogni acquisto e per chiunque (anche loggato: il
  // consenso Aurya sull'account non copre i patti del singolo servizio).
  const termsValid = !hasOperatorConditions || operatorTermsAccepted;

  // Wave GDPR-Commerce CG-5 — does this store require the new GDPR
  // consent block? True when the merchant has published their per-store
  // Privacy + Terms (CG-3 admin UI). Stays False for legacy stores so
  // the checkout flow is identical to pre-CG-5 behaviour.
  const gdprRequired = !!legalMeta && (
    legalMeta.status === 'published' || legalMeta.status === 'stale_draft'
  );
  // The two mandatory boxes must be ticked when gdprRequired AND the
  // block is actually rendered. Marketing is always optional even when
  // the block is rendered (GDPR Art. 7 granular consent).
  //
  // 2026-05-20 — Fix Bug #3: when the customer is already logged in,
  // the block is HIDDEN (CG-4 captured the snapshot at signup; the
  // re-consent modal handles version bumps before the customer can
  // even reach the checkout). For that case ``gdprValid`` is true by
  // construction — we don't have checkboxes to validate. The backend
  // mirrors this by accepting the customer_account snapshot in place
  // of the per-order payload flags for logged-in customers (Fix 3b).
  // RS3 — il blocco consensi si mostra SEMPRE ai guest (i documenti
  // /s/:slug/privacy|terms rispondono sempre: autogenerati finche'
  // l'operatore non pubblica i suoi), quindi si richiede sempre.
  // AP-L — l'atto primario e' la checkbox Aurya del guest (che porta
  // con se' i flag CG-5); chi e' loggato Aurya ha gia' accettato
  // sull'account e non ri-accetta nulla a livello piattaforma.
  const gdprValid =
    isCustomerAuthenticated
    || platformLoggedIn
    || (gdprTermsAccepted && gdprPrivacyAccepted);

  // Auto-fill first attendee from the main customer form: it's the most
  // common case (Michele buys 3 tickets, first is his own). Keeps friction
  // low; customer can still override if the first seat is for a guest.
  useEffect(() => {
    if (!form.name.trim() && !form.email.trim()) return;
    setAttendeeDetails(prev => {
      let changed = false;
      const next = { ...prev };
      for (const { item } of itemsRequiringAttendees) {
        const pid = item.product_id;
        const cur = next[pid];
        if (Array.isArray(cur) && cur.length > 0) {
          const first = cur[0] || {};
          if (!first.name && !first.email) {
            next[pid] = [
              { name: form.name.trim(), email: form.email.trim(), phone: form.phone?.trim() || '' },
              ...cur.slice(1),
            ];
            changed = true;
          }
        }
      }
      return changed ? next : prev;
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [form.name, form.email, form.phone, itemsRequiringAttendees.length]);

  const handleSubmit = async (e) => {
    // K3+ — in contesto marketplace il success attiva il Passaporto con
    // l'email dell'ordine (one-click, senza ridigitarla)
    if (mktpCheckout && form?.email) {
      try { sessionStorage.setItem('storefront:mktp_email', form.email); } catch { /* no-op */ }
    }
    e.preventDefault();
    if (!form.name.trim() || !form.email.trim() || selectedItems.length === 0) return;
    if (!attendeesValid) {
      toast.error(t('storefront:errors.fillAttendees'));
      return;
    }
    // AP-L — condizioni dell'operatore: checkbox dedicata obbligatoria
    // quando l'operatore le ha compilate (per chiunque, anche loggato).
    if (hasOperatorConditions && !operatorTermsAccepted) {
      toast.error(t('storefront:errors.termsRequired'));
      return;
    }
    // AP-L — atto primario Aurya: il guest deve spuntare la checkbox
    // Aurya; il loggato (piattaforma o portale cliente) e' gia' coperto.
    if (!gdprValid) {
      toast.error(t('storefront:errors.gdprRequired', {
        defaultValue: 'Devi accettare i Termini e la Privacy di Aurya per procedere.',
      }));
      return;
    }
    if (!servicesValid) {
      toast.error(t('storefront:errors.selectServiceOptionAndSlot'));
      return;
    }
    // Structured shipping address validation — runs only for mode=shipping.
    // Required fields mirror the backend Pydantic contract; soft pattern
    // check on CAP applies to IT only (other countries allow alphanumeric
    // postal codes).
    if (form.fulfillment_mode === 'shipping') {
      const a = form.shipping_address_details || {};
      const missing = [];
      if (!a.line1?.trim()) missing.push(t('storefront:checkout.address.streetField'));
      if (!a.civic?.trim()) missing.push(t('storefront:checkout.address.civicField'));
      if (!a.postal_code?.trim()) missing.push(t('storefront:checkout.address.postalCodeField'));
      if (!a.city?.trim()) missing.push(t('storefront:checkout.address.cityField'));
      if (missing.length) {
        toast.error(t('storefront:errors.completeAddress', { missing: missing.join(', ') }));
        return;
      }
      const countryIso = (a.country || 'IT').toUpperCase();
      if (countryIso === 'IT' && !/^\d{5}$/.test(a.postal_code.trim())) {
        toast.error(t('storefront:errors.invalidPostalCodeIT'));
        return;
      }
    }
    // Shipping option required when the cart contains a physical item
    // AND the customer chose mode=shipping. Backend re-validates this,
    // but surfacing the error client-side avoids a confusing round-trip.
    if (hasPhysicalCart && form.fulfillment_mode === 'shipping' && !form.shipping_option_id) {
      toast.error(t('storefront:errors.selectShippingOption'));
      return;
    }
    setSubmitting(true);
    // Fase C2: best-effort account creation BEFORE the order. By design the
    // account is created with email_verified=false — the customer will
    // confirm via email and, at first successful login, their orders on
    // this org are automatically linked by email match (backend
    // _link_account_to_existing_customers). The order itself is still
    // submitted as guest in this request; never block the order on a
    // signup hiccup.
    let registrationState = null; // null | 'created' | 'already' | 'failed' | 'auto_logged_in'
    if (wantRegister && !isCustomerAuthenticated) {
      const strength = computePasswordStrength(regPassword);
      if (!strength.ok) {
        toast.error(t('storefront:checkout.signup.passwordRequirementsToast'));
        setSubmitting(false);
        return;
      }
      if (regPassword !== regPasswordConfirm) {
        toast.error(t('storefront:checkout.signup.passwordMismatch'));
        setSubmitting(false);
        return;
      }

      // Release 4 (Courses) — when the cart contains a course we ask the
      // backend to `auto_login` so the signup response already carries a
      // Bearer token. This bypasses the email-verified gate that would
      // otherwise block a subsequent /login call (the account is freshly
      // created → email_verified=false → login 403). For non-course
      // carts the legacy fire-and-forget signup keeps working unchanged.
      const wantAutoLogin = !!requiresCustomerAccount;

      try {
        // Note: we call through the context's `signup` (not the raw
        // customerAuthAPI) so the token is persisted in localStorage +
        // React state atomically. The next `storefrontAPI.submitOrder`
        // will then attach the Bearer automatically via customerClient.
        // 2026-05-20 — Fix Bug #1 (checkout inline signup): the backend
        // CG-4 contract requires accepted_terms + accepted_privacy at
        // signup (and optionally accepted_marketing). Without these the
        // service raises "Devi accettare i Termini..." and the user sees
        // a generic "registrazione non completata". The checkout already
        // has these states (the GDPR block above forces the merchant's
        // ticked boxes before the submit) so we forward them verbatim.
        const result = await customerSignup({
          slug,
          email: form.email.trim(),
          name: form.name.trim(),
          password: regPassword,
          auto_login: wantAutoLogin,
          // CG-4 consent flags — required when merchant_legal_status is
          // "published" / "stale_draft". For stores that have NOT
          // published these are ignored server-side (backward compat).
          accepted_terms: !!gdprTermsAccepted,
          accepted_privacy: !!gdprPrivacyAccepted,
          accepted_marketing: !!gdprMarketingAccepted,
        });
        if (result && typeof result === 'object' && result.status === 'auto_logged_in') {
          registrationState = 'auto_logged_in';
        } else {
          registrationState = 'created';  // legacy verification_required flow
        }
      } catch (err) {
        const status = err?.response?.status;
        const rawDetail = err?.response?.data?.detail;
        const detail = typeof rawDetail === 'string' ? rawDetail
                       : (rawDetail?.message || rawDetail?.error || '');
        // 409 or "esiste già / already / exists" → account exists.
        // Regex widened to match Italian "esiste" (no accent needed).
        if (status === 409 || /email.*gi[aà]|already|existe?s?|esiste/i.test(String(detail))) {
          registrationState = 'already';
          if (requiresCustomerAccount) {
            toast.error(t('storefront:errors.emailAlreadyForCourse'));
            setSubmitting(false);
            return;
          }
          toast.info(t('storefront:errors.emailAlreadyInfo'));
        } else {
          registrationState = 'failed';
          if (requiresCustomerAccount) {
            // For courses we cannot proceed as guest — the server will
            // reject with course_requires_account. Stop here with a
            // clear message instead of letting the backend 400 bubble.
            toast.error(detail || t('storefront:errors.signupFailed'));
            setSubmitting(false);
            return;
          }
          // AP0 — messaggio onesto: quando il backend spiega il motivo
          // (detail), lo mostriamo invece del generico "non completata".
          // L'ordine parte comunque come ospite in entrambi i casi.
          if (detail) {
            toast.info(t('storefront:errors.signupNotCompletedReason', {
              reason: String(detail).replace(/\.\s*$/, ''),
            }));
          } else {
            toast.info(t('storefront:errors.signupNotCompleted'));
          }
        }
      }
    }
    try {
      const payload = {
        slug,
        customer_name: form.name.trim(),
        customer_email: form.email.trim(),
        customer_phone: form.phone.trim() || null,
        items: selectedItems,
        notes: form.notes.trim() || null,
        // GT1 — il canale viaggia con l'ordine: gli ordini nati dal
        // marketplace si incassano SOLO online. PS6.4 — la prop
        // esplicita della superficie reale vince sul flag di sessione
        // (mktp_ctx restava appeso e contaminava gli acquisti dal
        // profilo); il fallback legacy resta per lo storefront /s/.
        channel: channel || (() => {
          try { return sessionStorage.getItem('storefront:mktp_ctx') === '1' ? 'marketplace' : 'store'; }
          catch { return 'store'; }
        })(),
      };
      // F2 Onda 9 — send order-level custom fields only if we collected any
      if (orderFieldsData && Object.keys(orderFieldsData).length > 0) {
        payload.order_fields = orderFieldsData;
      }
      // AP-L — accettazione delle condizioni dell'operatore (politica di
      // cancellazione + requisiti del servizio): la checkbox dedicata.
      // Il flag legacy termsAccepted resta in OR per compatibilita'.
      payload.terms_accepted = !!(operatorTermsAccepted || termsAccepted);
      // Wave GDPR-Commerce CG-5 — per-order consent flags. Always sent
      // (legacy clients omit them, defaults to False). Backend enforces
      // them ONLY when the merchant has GDPR published — otherwise
      // they're harmlessly ignored and the legacy flow proceeds.
      payload.gdpr_terms_accepted = !!gdprTermsAccepted;
      payload.gdpr_privacy_accepted = !!gdprPrivacyAccepted;
      payload.gdpr_marketing_accepted = !!gdprMarketingAccepted;
      // AP-L — consenso Aurya del guest (checkbox unica): l'ordine lo
      // timbra con le versioni correnti dei documenti piattaforma. Per
      // i loggati Aurya il backend risale all'account (aurya_legal).
      payload.aurya_terms_accepted = !!auryaAccepted;
      // v10.0: fulfillment fields
      if (form.fulfillment_mode && form.fulfillment_mode !== 'manual_arrangement') {
        payload.fulfillment_mode = form.fulfillment_mode;
      }
      // Structured shipping address — only sent for mode=shipping. The
      // backend trusts this payload and synthesizes the flattened
      // `shipping_address` string server-side, so we intentionally do
      // NOT send the legacy key.
      if (form.fulfillment_mode === 'shipping') {
        const a = form.shipping_address_details || {};
        payload.shipping_address_details = {
          recipient_name: a.recipient_name?.trim() || null,
          line1: a.line1.trim(),
          civic: a.civic.trim(),
          postal_code: a.postal_code.trim(),
          city: a.city.trim(),
          province: a.province?.trim().toUpperCase() || null,
          country: (a.country || 'IT').toUpperCase(),
        };
      }
      // Shipping option id — only meaningful for mode=shipping. Backend
      // recomputes the cost from the ShippingOption doc so a malicious
      // client cannot alter the total by tampering with the payload.
      if (form.fulfillment_mode === 'shipping' && form.shipping_option_id) {
        payload.shipping_option_id = form.shipping_option_id;
      }
      if (form.fulfillment_notes?.trim()) {
        payload.fulfillment_notes = form.fulfillment_notes.trim();
      }
      if (form.coupon_code?.trim()) {
        payload.coupon_code = form.coupon_code.trim();
      }
      // customerClient injects customer_token automatically if present.
      //
      // Checkout consolidation: the API call + Stripe redirect + error
      // toast go through the shared useCheckoutSubmit hook (same path
      // used by EventLandingPage) so both pages honor
      // payment_checkout_url identically and future fixes land in one
      // place. The success branch still handles page-specific cleanup
      // (form close, password scrub, availability reload) that is
      // unique to the cart UX.
      const result = await submitCheckout(payload, {
        onSuccess: (data) => {
          setSubmitted({ ...data, registered: registrationState });
          setFormOpen(false);
          setRegPassword('');
          setRegPasswordConfirm('');
          setWantRegister(false);
          // Cart persisted in sessionStorage is now consumed — drop the
          // snapshot so a fresh visit starts clean. The in-memory state
          // reset happens when the user dismisses the success modal
          // (see the "Nuovo ordine" / reset button further down).
          // Phase 7.1: clearCartSnapshot routes through useStorefrontCart
          // so future cart-storage refactors land in one place.
          clearCartSnapshot();
          const bookingProduct = (catalog?.products || []).find(p => p.item_type === 'booking');
          if (bookingProduct) loadAvailability(bookingProduct.slot_duration_minutes || null, bookingProduct.id);
        },
        onError: (detail) => {
          toast.error(detail);
        },
      });
      // When redirected to Stripe, the return above effectively means
      // we never reach the finally block of submitting=false — the
      // browser has already left the page. Kept for parity with the
      // previous inline flow.
      if (result?.redirected) return;
    } catch (err) {
      // Same anti-crash guard as useCheckoutSubmit — the detail may be
      // a structured FastAPI object (e.g. `{error, message}` for the
      // course_requires_account gate) and React can't render it.
      const raw = err?.response?.data?.detail;
      const msg = typeof raw === 'string'
        ? raw
        : (raw && typeof raw === 'object' && (raw.message || raw.error))
          || t('storefront:errors.submitGeneric');
      toast.error(String(msg));
    } finally { setSubmitting(false); }
  };

  // PN2 — superficie del hook: tutto cio' che CheckoutForm e la pagina
  // leggevano dalle closure di StorefrontPage, esposto com'era.
  return {
    // stato modale / form
    form, setForm,
    formOpen, setFormOpen,
    submitting,
    submitted, setSubmitted,
    handleSubmit,
    // consensi (F4 / CG-5 / RS3 / AP-L)
    termsAccepted, setTermsAccepted,
    termsExpanded, setTermsExpanded,
    legalMeta,
    gdprRequired,
    gdprTermsAccepted, setGdprTermsAccepted,
    gdprPrivacyAccepted, setGdprPrivacyAccepted,
    gdprMarketingAccepted, setGdprMarketingAccepted,
    effectiveTerms, termsValid, gdprValid,
    marketingStatus,
    // AP-L — legal a due livelli
    platformAccount, setPlatformAccount, platformLoggedIn,
    auryaAccepted, setAuryaConsent,
    operatorTermsAccepted, setOperatorTermsAccepted,
    hasOperatorConditions, cartCancellationPolicy,
    // registrazione opzionale (Fase C1)
    wantRegister, setWantRegister,
    regPassword, setRegPassword,
    regPasswordConfirm, setRegPasswordConfirm,
    showRegPassword, setShowRegPassword,
    requiresCustomerAccount,
    // contesto marketplace (K1)
    mktpCheckout, setMktpCheckout,
    // fulfillment / spedizione (v10.0)
    fulfillmentContext,
    shippingOptions, setShippingOptions,
    hasPhysicalCart, physicalSubtotal,
    selectedShippingOption, shippingSummary,
    // coupon (Sprint 2 W2.1/W2.2)
    couponValidationState,
    // copy + validazioni derivate
    modeCopy,
    itemsRequiringAttendees, attendeesValid,
    orderFieldsConfig, orderFieldsValid,
    serviceItemsInCart, servicesValid,
  };
}
