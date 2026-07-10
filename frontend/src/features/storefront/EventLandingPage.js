/**
 * EventLandingPage — public landing page for a single event occurrence.
 *
 * Route: /e/:org_slug/:slug
 * Backed by GET /api/public/events/{org_slug}/{slug} (E3).
 *
 * Role in the checkout flow — PURELY A PRESENTER:
 *   The landing shows the event richly (hero, description, venue + map,
 *   tier picker, qty stepper) and collects ONE piece of state from the
 *   user: which tier and how many seats. When the user clicks
 *   "Procedi al checkout", the page navigates to the storefront
 *   /s/:org_slug with that selection embedded in React Router state;
 *   StorefrontPage reads the state, hydrates its cart, and opens the
 *   EXISTING checkout dialog (customer data, coupon, fulfillment,
 *   Stripe redirect — the same form used for every other purchase).
 *
 *   The landing itself never submits an order. There is one form
 *   and one submit handler in the whole app.
 *
 * Design:
 *   - Mobile-first, single-column layout on phones, two-column on md+.
 *   - Hero image full-width with date/title overlay.
 *   - "A colpo d'occhio" summary (data, luogo) immediately below the hero.
 *   - Markdown-rendered long description (safe inline renderer — no deps).
 *   - Tier cards with live remaining.
 *   - Sticky right column on md+ with the "Procedi al checkout" CTA.
 */

import React, { useEffect, useMemo, useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { Trans, useTranslation } from 'react-i18next';
import { toast } from 'sonner';
import { storefrontAPI } from '../../api/storefront';
import StorefrontHeader from './components/StorefrontHeader';
import MarkdownLite from '../../components/MarkdownLite';
import { CalendarDays, Clock, MapPin, CreditCard, ShoppingCart, ShieldCheck, Sprout, MailCheck, Flower2 } from 'lucide-react';
import OpenCheckoutButton from './components/OpenCheckoutButton';
import useCartCount from './hooks/useCartCount';
import { effectivePlan } from './lib/paymentPlan';
import useSeoMeta from './lib/useSeoMeta';
import useTrackView from './lib/useTrackView';
import api from '../../api/client';
import StoreContextNav from './components/StoreContextNav';
import MarketplaceShell from './components/MarketplaceShell';
// G4 — mappa lazy: Leaflet non pesa sul first paint della landing
const StaticMiniMap = React.lazy(() => import('./components/StaticMiniMap'));


// ── Utilities ──────────────────────────────────────────────────────────────

function formatDateTime(iso, locale = 'it-IT') {
  if (!iso) return '';
  try {
    const d = new Date(iso);
    const date = d.toLocaleDateString(locale, { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
    const time = d.toLocaleTimeString(locale, { hour: '2-digit', minute: '2-digit' });
    return { date, time, dateShort: d.toLocaleDateString(locale) };
  } catch { return { date: iso, time: '', dateShort: iso }; }
}

function formatPrice(n, currency = 'EUR', locale = 'it-IT') {
  if (n === null || n === undefined) return '';
  try {
    return new Intl.NumberFormat(locale, { style: 'currency', currency }).format(n);
  } catch { return `${n} ${currency}`; }
}

function composeAddress(o) {
  const parts = [o.address, o.postal_code, o.city, o.country].filter(Boolean);
  return parts.join(', ');
}


// ── Tier card ──────────────────────────────────────────────────────────────

function TierCard({ tier, currency, qty, onQtyChange }) {
  const { t, i18n } = useTranslation('landings');
  // F3 Onda 10 — card always exposes independent +/- counter. qty=0 means
  // "not in cart"; any tier can be combined with any other in the same
  // order, with capacity enforced per-tier.
  const soldOut = tier.remaining === 0;
  const isUnlimited = tier.remaining === null || tier.remaining === undefined;
  const inCart = qty > 0;
  const maxReached = !isUnlimited && qty >= (tier.remaining || 0);

  return (
    <div
      className={`rounded-xl border p-4 transition ${
        inCart ? 'border-gray-900 bg-gray-50' : 'border-gray-200 bg-white hover:border-gray-400'
      } ${soldOut ? 'opacity-60' : ''}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="font-semibold text-gray-900 truncate">{tier.label}</h3>
            {soldOut && (
              <span className="text-[10px] font-semibold uppercase tracking-wide text-red-700 bg-red-100 px-2 py-0.5 rounded">
                {t('landings:event.soldOutBadge')}
              </span>
            )}
          </div>
          {tier.description && (
            <p className="text-sm text-gray-600 mt-1">{tier.description}</p>
          )}
          <p className="text-xs text-gray-500 mt-2">
            {isUnlimited
              ? t('landings:event.tier.remainingUnlimited')
              : t('landings:event.tier.remaining', { count: tier.remaining })}
          </p>
        </div>
        <div className="text-right shrink-0">
          <p className="text-lg font-bold text-gray-900 whitespace-nowrap">
            {formatPrice(tier.price, currency, i18n.language)}
          </p>
        </div>
      </div>

      {!soldOut && (
        <div className="mt-3 flex items-center gap-2">
          <div className="flex items-center gap-1 rounded-md border border-gray-300 bg-white">
            <button
              type="button"
              onClick={() => onQtyChange(Math.max(0, qty - 1))}
              className="px-2 py-1 text-gray-700 hover:bg-gray-100 text-sm font-medium disabled:opacity-30"
              disabled={qty <= 0}
              aria-label={t('landings:event.tier.decAria')}
            >−</button>
            <span className="px-3 py-1 text-sm font-semibold min-w-[2ch] text-center">{qty}</span>
            <button
              type="button"
              onClick={() => onQtyChange(qty + 1)}
              className="px-2 py-1 text-gray-700 hover:bg-gray-100 text-sm font-medium disabled:opacity-30"
              disabled={maxReached}
              aria-label={t('landings:event.tier.incAria')}
            >+</button>
          </div>
          {inCart && (
            <span className="text-xs text-gray-600">{t('landings:event.tier.inCart')}</span>
          )}
        </div>
      )}
    </div>
  );
}


// ── Proceed to checkout bar ────────────────────────────────────────────────
//
// Consolidation (no-new-form): replaces the standalone form + success
// screen that used to live on the landing. The landing selects a tier
// + qty; clicking "Procedi al checkout" hands the selection over to
// /s/:orgSlug via React Router navigation state, where the existing
// storefront checkout dialog takes over (customer data, coupon,
// fulfillment, Stripe redirect — all the flows the storefront already
// supports). Exactly one form in the whole app handles payment.

// S5 — linking interno: "Altri ritiri di {categoria}" SOLO in contesto
// marketplace (nel guscio store non si mandano i clienti dai concorrenti).
// 3 link a foglie sorelle: equity interna + scoperta.
function RelatedRetreats({ category, excludePath, t }) {
  const [items, setItems] = React.useState([]);
  React.useEffect(() => {
    if (!category) return;
    let mounted = true;
    import('../../api/client').then(({ default: api }) =>
      api.get('/public/retreats', { params: { category } })
    ).then(res => {
      if (!mounted) return;
      setItems((res.data?.items || [])
        // PL13 — mai campioni nei correlati: titolo redatto e landing 404
        .filter(it => !it.sample && it.url !== excludePath)
        .slice(0, 3));
    }).catch(() => { /* best-effort */ });
    return () => { mounted = false; };
  }, [category, excludePath]);

  if (items.length === 0) return null;
  return (
    <section className="max-w-4xl mx-auto px-4 sm:px-6 pb-10">
      <h2 className="font-heading text-lg font-bold text-gray-900 mb-3">
        {t('landings:event.relatedHeading', {
          cat: t(`landings:categories.${category}`, { defaultValue: category }),
          defaultValue: 'Altri ritiri di {{cat}}',
        })}
      </h2>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {items.map(it => (
          <Link key={it.url} to={it.url}
                className="rounded-2xl border border-gray-200 bg-white p-4 hover:shadow-md transition-shadow">
            <p className="font-semibold text-gray-900 line-clamp-2">{it.title}</p>
            <p className="text-xs text-gray-500 mt-1">
              {(it.city || it.region || '')}{it.price_from != null ? ` · da ${it.price_from} €` : ''}
            </p>
          </Link>
        ))}
      </div>
    </section>
  );
}


// AN7 — le voci di chi ha gia' partecipato, dentro la landing: il
// momento della scelta e' dove la fiducia pesa di piu'. Prime 3
// recensioni pubbliche dell'organizzatore, con badge verificato.
function ReviewsSnippet({ orgSlug, rating, t }) {
  const [reviews, setReviews] = React.useState([]);
  React.useEffect(() => {
    let mounted = true;
    import('../../api/client').then(({ default: api }) =>
      api.get(`/public/reviews/${orgSlug}`, { params: { page_size: 3 } })
    ).then(res => {
      if (mounted) setReviews(res.data?.items || []);
    }).catch(() => { /* best-effort */ });
    return () => { mounted = false; };
  }, [orgSlug]);

  if (!reviews.length) return null;
  return (
    <section className="max-w-4xl mx-auto px-4 sm:px-6 pb-6" data-testid="landing-reviews">
      <div className="flex items-baseline justify-between gap-3 mb-3">
        <h2 className="font-heading text-lg font-bold text-gray-900">
          {t('landings:event.reviewsHeading', { defaultValue: 'Cosa dicono i partecipanti' })}
        </h2>
        {rating?.count > 0 && (
          <span className="text-sm text-gray-600 shrink-0">
            <span className="text-amber-500" aria-hidden>★</span>{' '}
            <span className="font-semibold text-gray-900">{rating.avg}</span> ({rating.count})
          </span>
        )}
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {reviews.map(r => (
          <figure key={r.id} className="rounded-2xl border border-gray-200 bg-white p-4 flex flex-col">
            <p className="text-amber-500 text-sm mb-1.5" aria-label={`${r.rating}/5`}>
              {'★'.repeat(r.rating)}<span className="text-gray-200">{'★'.repeat(5 - r.rating)}</span>
            </p>
            {r.comment && (
              <blockquote className="text-sm text-gray-700 leading-relaxed line-clamp-4 flex-1">
                {r.comment}
              </blockquote>
            )}
            <figcaption className="mt-3 flex items-center gap-2 text-xs text-gray-500">
              <span className="font-medium text-gray-700">{r.author_name}</span>
              {r.verified && (
                <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 text-emerald-700 px-2 py-0.5 font-medium">
                  ✓ {t('landings:event.verifiedBadge', { defaultValue: 'Cliente verificato' })}
                </span>
              )}
            </figcaption>
          </figure>
        ))}
      </div>
    </section>
  );
}


function ProceedToCheckoutBar({ orgSlug, product, occurrence, tierQuantities, plainQty, currency }) {
  const navigate = useNavigate();
  const { t, i18n } = useTranslation('landings');

  const hasTiers = (occurrence.tiers || []).length > 0;
  const isDirectMode = product?.transaction_mode === 'direct';

  // F3 Onda 10 — compute total seats + total price across ALL tiers
  // selected (multi-tier cart).
  const { totalSeats, totalPrice } = (() => {
    if (hasTiers) {
      let seats = 0, price = 0;
      for (const tier of (occurrence.tiers || [])) {
        const q = Number(tierQuantities[tier.id] || 0);
        if (q > 0) {
          seats += q;
          price += q * Number(tier.price || 0);
        }
      }
      return { totalSeats: seats, totalPrice: price };
    }
    const basePrice = occurrence.price_override ?? product.unit_price ?? 0;
    return { totalSeats: Math.max(1, Number(plainQty) || 1),
             totalPrice: basePrice * Math.max(1, Number(plainQty) || 1) };
  })();

  const needsTierSelection = hasTiers && totalSeats === 0;

  // K5 — carrello aperto di un ALTRO operatore? Un checkout serve un
  // operatore alla volta (un direct charge per org): meglio dirlo prima.
  const findOtherCartSlug = () => {
    try {
      for (let i = 0; i < sessionStorage.length; i++) {
        const k = sessionStorage.key(i);
        if (!k || !k.startsWith('storefront:cart:')) continue;
        const other = k.slice('storefront:cart:'.length);
        if (other === orgSlug) continue;
        const items = JSON.parse(sessionStorage.getItem(k) || '[]');
        if (Array.isArray(items) && items.length > 0) return other;
      }
    } catch { /* storage inaccessibile: nessun avviso */ }
    return null;
  };
  const [otherCartSlug, setOtherCartSlug] = useState(null);
  // contesto negozio? (param dei link delle card store — vedi M1)
  const fromStore = new URLSearchParams(window.location.search).get('store') === '1';

  const handleProceed = (skipOtherCartCheck = false) => {
    if (needsTierSelection) return;
    if (!skipOtherCartCheck) {
      const other = findOtherCartSlug();
      if (other) { setOtherCartSlug(other); return; }
    }
    // F3: pass the full tier_quantities map so StorefrontPage can
    // hydrate a multi-tier cart. Legacy single-tier/plain path is
    // backward-compatible via the `qty` field.
    const preloadCart = {
      productId: product.id,
      occurrenceId: occurrence.id,
      qty: Math.max(1, totalSeats),
    };
    if (hasTiers) {
      // Only include tiers with qty > 0 to keep the payload compact
      const tq = {};
      for (const [tid, q] of Object.entries(tierQuantities)) {
        if (Number(q) > 0) tq[tid] = Number(q);
      }
      preloadCart.tier_quantities = tq;
    }
    if (!fromStore) {
      // K1 — contesto MARKETPLACE: il checkout si apre subito, senza
      // passare per la vetrina; alla chiusura si torna QUI.
      preloadCart.openCheckout = true;
      preloadCart.mktp = true;
      preloadCart.returnTo = window.location.pathname;
      navigate(`/s/${orgSlug}`, { state: { preloadCart } });
      return;
    }
    navigate(`/s/${orgSlug}`, { state: { preloadCart } });
    toast.success(t('landings:event.toastAdded'), {
      action: {
        label: t('landings:event.toastAction'),
        onClick: () => navigate(`/s/${orgSlug}?checkout=1`),
      },
      duration: 4000,
    });
  };

  // Per-tier breakdown for the summary (multi-tier carts).
  // Renamed loop variable from `t` (tier) to `tier` to avoid shadowing the
  // i18n `t` function captured at the top of this component.
  const tierBreakdown = hasTiers
    ? (occurrence.tiers || [])
        .filter(tier => Number(tierQuantities[tier.id] || 0) > 0)
        .map(tier => ({ id: tier.id, label: tier.label, qty: Number(tierQuantities[tier.id]), subtotal: Number(tier.price || 0) * Number(tierQuantities[tier.id]) }))
    : [];

  return (
    <>
    <div className="rounded-xl border border-gray-200 bg-white p-5 space-y-3 shadow-sm">
      <div>
        <h3 className="font-semibold text-gray-900">{t('landings:event.summaryHeading')}</h3>
        {hasTiers ? (
          tierBreakdown.length === 0 ? (
            <p className="text-sm text-gray-500 mt-1">{t('landings:event.noTicketSelected')}</p>
          ) : (
            <div className="mt-1 space-y-0.5">
              {tierBreakdown.map(row => (
                <p key={row.id} className="text-sm text-gray-700 flex justify-between gap-3">
                  <span>{t('landings:event.tierLine', { qty: row.qty, label: row.label })}</span>
                  <span className="tabular-nums text-gray-900">{formatPrice(row.subtotal, currency, i18n.language)}</span>
                </p>
              ))}
              <p className="text-[11px] text-gray-500 pt-1">
                {t('landings:event.ticketsCount', { count: totalSeats })}
              </p>
            </div>
          )
        ) : (
          <p className="text-sm text-gray-600 mt-1">{t('landings:event.plainLine', { qty: plainQty, name: product.name })}</p>
        )}
        <p className="text-2xl font-bold text-gray-900 mt-2">
          {formatPrice(totalPrice, currency, i18n.language)}
        </p>
        {/* Fase 2 S2 — messaging caparra: "oggi paghi solo X" (calcolo
            speculare al backend; l'importo autoritativo resta server-side) */}
        {(() => {
          const ep = effectivePlan(
            product?.payment_plan, totalPrice, occurrence.start_at);
          if (ep.mode !== 'deposit' || totalPrice <= 0) return null;
          return (
            <div className="mt-2 rounded-lg bg-emerald-50 border border-emerald-200 px-3 py-2 text-sm text-emerald-900">
              <p className="font-semibold">
                {t('landings:event.deposit.payNow', {
                  amount: formatPrice(ep.depositMinor / 100, currency, i18n.language),
                })}
              </p>
              <p className="text-xs mt-0.5">
                {ep.installments
                  ? t('landings:event.deposit.restInstallments', {
                      amount: formatPrice(ep.balanceMinor / 100, currency, i18n.language),
                      count: ep.installments,
                      date: ep.balanceDueDate.toLocaleDateString(i18n.language),
                    })
                  : t('landings:event.deposit.restBalance', {
                      amount: formatPrice(ep.balanceMinor / 100, currency, i18n.language),
                      date: ep.balanceDueDate.toLocaleDateString(i18n.language),
                    })}
              </p>
            </div>
          );
        })()}
      </div>

      <button
        type="button"
        onClick={() => handleProceed(false)}
        disabled={needsTierSelection}
        className="w-full rounded-md bg-[var(--sf-accent,#111827)] text-[var(--sf-accent-fg,#ffffff)] px-4 py-3 text-sm font-semibold hover:bg-[var(--sf-accent-hover,#1f2937)] disabled:opacity-50 flex items-center justify-center gap-2"
      >
        {isDirectMode && <CreditCard className="h-4 w-4 inline-block" aria-hidden />}
        {needsTierSelection
          ? t('landings:event.ctaSelectTier')
          : t('landings:event.ctaAdd')}
      </button>

      <p className="text-[11px] text-gray-500 text-center">
        {t('landings:event.checkoutHint')}
      </p>
    </div>
    {/* K5 — avviso: hai gia' un carrello con un altro operatore */}
      {otherCartSlug && (
        <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4"
             role="dialog" aria-modal="true" onClick={() => setOtherCartSlug(null)}>
          <div className="max-w-sm w-full rounded-2xl bg-white p-5 shadow-xl"
               onClick={(e) => e.stopPropagation()}>
            <p className="font-semibold text-gray-900 mb-1.5">
              {t('landings:event.otherCartTitle', { defaultValue: 'Hai un altro carrello aperto' })}
            </p>
            <p className="text-sm text-gray-600 mb-4">
              {t('landings:event.otherCartBody', {
                defaultValue: 'Si acquista da un organizzatore alla volta: ogni prenotazione va direttamente al suo organizzatore. L\'altro carrello resta salvato — puoi completarlo dopo.',
              })}
            </p>
            <div className="space-y-2">
              <button type="button"
                onClick={() => { setOtherCartSlug(null); handleProceed(true); }}
                className="w-full rounded-full bg-accent text-accent-foreground px-4 py-2.5 text-sm font-bold">
                {t('landings:event.otherCartContinue', { defaultValue: 'Continua con questo ritiro' })}
              </button>
              <button type="button"
                onClick={() => navigate(`/s/${otherCartSlug}?checkout=1`)}
                className="w-full rounded-full border border-gray-300 px-4 py-2.5 text-sm font-semibold text-gray-700 hover:border-primary hover:text-primary">
                {t('landings:event.otherCartFinish', { defaultValue: 'Completa prima l\'altro carrello' })}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}


// ── Main component ─────────────────────────────────────────────────────────

export default function EventLandingPage() {
  const { org_slug: orgSlug, slug } = useParams();
  // VT2 — visita alla landing per lo specchietto Visibilità (ping 3s)
  useTrackView('event', slug);
  // 7/7 — contesto negozio: i link delle card store portano ?store=1;
  // la landing mantiene la barra menu dello store (mai uscire).
  const fromStore = new URLSearchParams(window.location.search).get('store') === '1';
  const [lightbox, setLightbox] = useState(null);   // indice foto aperta | null

  const { t, i18n } = useTranslation('landings');
  const cartCount = useCartCount(orgSlug);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  // F3 Onda 10 — multi-tier cart: user may combine any mix of tiers
  // (es. 2 Standard + 1 VIP). State is a dict {tierId: qty}; tiers with
  // qty=0 are omitted. For occurrences without tiers, fallback to the
  // legacy mono-qty counter via `plainQty`.
  const [tierQuantities, setTierQuantities] = useState({});
  const [plainQty, setPlainQty] = useState(1);
  // F2.1 — blocco "Organizzato da": profilo operatore (fetch leggero,
  // best-effort: se fallisce la landing vive senza)
  const [operator, setOperator] = useState(null);

  useEffect(() => {
    let mounted = true;
    api.get(`/public/operator/${orgSlug}`)
      .then(res => { if (mounted) setOperator(res.data); })
      .catch(() => {});
    return () => { mounted = false; };
  }, [orgSlug]);

  // F3 — SEO automatico della landing: title/description/og:image dai
  // dati del ritiro + JSON-LD Event (schema.org) per i rich results.
  const seoProduct = data?.product;
  const seoOcc = data?.occurrence;
  useSeoMeta({
    title: seoProduct
      ? `${seoProduct.name}${seoOcc?.city ? ` · ${seoOcc.city}` : ''} · prenota online`
      : undefined,
    description: seoProduct?.description
      ? String(seoProduct.description).slice(0, 155)
      : (seoProduct ? `Prenota ${seoProduct.name}: date, prezzi e disponibilità in tempo reale.` : undefined),
    image: seoOcc?.cover_image_url || seoProduct?.image_url || undefined,
    canonicalPath: `/e/${orgSlug}/${slug}`,
    // S1 — array JSON-LD: Event + FAQPage (le FAQ del ritiro sono già
    // nei dati → rich results "FAQ" sotto lo snippet in SERP).
    jsonLd: (seoProduct && seoOcc) ? [
      ...((seoOcc.faq || []).filter(f => f?.q && f?.a).length > 0 ? [{
        '@context': 'https://schema.org',
        '@type': 'FAQPage',
        mainEntity: (seoOcc.faq || []).filter(f => f?.q && f?.a).map(f => ({
          '@type': 'Question',
          name: f.q,
          acceptedAnswer: { '@type': 'Answer', text: f.a },
        })),
      }] : []),
      {
      '@context': 'https://schema.org',
      '@type': 'Event',
      name: seoProduct.name,
      startDate: seoOcc.start_at,
      ...(seoOcc.end_at ? { endDate: seoOcc.end_at } : {}),
      eventAttendanceMode: 'https://schema.org/OfflineEventAttendanceMode',
      eventStatus: 'https://schema.org/EventScheduled',
      ...(seoOcc.cover_image_url || seoProduct.image_url
        ? { image: [seoOcc.cover_image_url || seoProduct.image_url] } : {}),
      ...(seoProduct.description
        ? { description: String(seoProduct.description).slice(0, 500) } : {}),
      location: {
        '@type': 'Place',
        name: seoOcc.venue_name || seoOcc.city || 'Italia',
        address: {
          '@type': 'PostalAddress',
          ...(seoOcc.venue_name ? { streetAddress: seoOcc.venue_name } : {}),
          ...(seoOcc.city ? { addressLocality: seoOcc.city } : {}),
          ...(seoOcc.region ? { addressRegion: seoOcc.region } : {}),
          addressCountry: 'IT',
        },
        // SEO1 — geo allineato allo shell: segnale locale forte
        ...(seoOcc.latitude != null && seoOcc.longitude != null ? {
          geo: {
            '@type': 'GeoCoordinates',
            latitude: seoOcc.latitude,
            longitude: seoOcc.longitude,
          },
        } : {}),
      },
      ...(operator?.name ? {
        organizer: {
          '@type': 'Organization',
          name: operator.name,
          url: `${window.location.origin}/o/${orgSlug}`,
        },
      } : {}),
      ...(seoProduct.unit_price != null ? {
        offers: {
          '@type': 'Offer',
          price: seoProduct.unit_price,
          priceCurrency: data?.currency || 'EUR',
          availability: data?.is_buyable
            ? 'https://schema.org/InStock'
            : 'https://schema.org/SoldOut',
          url: `${window.location.origin}/e/${orgSlug}/${slug}`,
        },
      } : {}),
    }] : undefined,
  });

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    storefrontAPI.getEventLanding(orgSlug, slug, (i18n.language || 'it').slice(0, 2))
      .then(res => { if (mounted) { setData(res.data); setLoading(false); } })
      .catch(err => {
        if (!mounted) return;
        setError(err?.response?.status === 404 ? 'not_found' : 'generic');
        setLoading(false);
      });
    return () => { mounted = false; };
  }, [orgSlug, slug, i18n.language]);

  const dt = useMemo(() => data ? formatDateTime(data.occurrence.start_at, i18n.language) : null, [data, i18n.language]);
  const dtEnd = useMemo(() => data?.occurrence.end_at ? formatDateTime(data.occurrence.end_at, i18n.language) : null, [data, i18n.language]);
  const address = useMemo(() => data ? composeAddress(data.occurrence) : '', [data]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-6">
        <div className="text-gray-500 text-sm">{t('landings:event.loadingEvent')}</div>
      </div>
    );
  }

  if (error === 'not_found') {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-6">
        <div className="max-w-md text-center bg-white rounded-xl border border-gray-200 p-8 shadow-sm">
          <h1 className="text-2xl font-bold text-gray-900 mb-2">{t('landings:event.notFoundTitle')}</h1>
          <p className="text-gray-600 mb-4">
            {t('landings:event.notFoundBody')}
          </p>
          <Link to={`/s/${orgSlug}`} className="inline-block rounded-md bg-gray-900 text-white px-4 py-2 text-sm font-medium">
            {t('landings:event.seeOtherEvents')}
          </Link>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-6">
        <div className="text-sm text-gray-600">{t('landings:event.errorBody')}</div>
      </div>
    );
  }

  const { product, occurrence, is_buyable: isBuyable, store_info: storeInfo, org_name: orgName, org_rating: orgRating, currency } = data;
  const effectiveCurrency = product.currency || 'EUR';
  const heroImage = occurrence.cover_image_url || product.image_url;
  // M2 — le foto vendono i ritiri: cover + galleria in un'unica griglia
  // hero stile marketplace; lightbox senza dipendenze.
  const allPhotos = [heroImage, ...(occurrence.gallery_urls || [])]
    .filter(Boolean)
    .filter((u, i, a) => a.indexOf(u) === i);

  // M1 — doppio guscio: store (?store=1) tiene header+nav del negozio;
  // marketplace (directory, Google, link condivisi) indossa il guscio
  // comune: "dentro il marketplace non ti perdi mai".
  const Wrap = fromStore ? React.Fragment : MarketplaceShell;
  return (
    <Wrap>
    <div className={fromStore ? 'min-h-screen bg-gray-50' : 'bg-gray-50'}>
      {fromStore && (<>
        {/* Persistent storefront header — consistent brand across surfaces.
            Logo + store name click back to /s/:orgSlug (home). */}
        <StorefrontHeader
          orgSlug={orgSlug}
          storeInfo={storeInfo}
          orgName={orgName}
          subtitle={t('landings:event.headerSubtitle')}
          rightSlot={
            <Link
              to={`/s/${orgSlug}`}
              className="text-xs sm:text-sm font-medium opacity-80 hover:opacity-100 underline-offset-2 hover:underline inline-flex items-center gap-2"
              style={storeInfo?.brand_color ? { color: storeInfo.brand_color_text || '#fff' } : { color: '#374151' }}
            >
              <span>{t('landings:event.catalogLink')}</span>
              {cartCount > 0 && (
                <span className="inline-flex items-center rounded-full bg-white text-gray-900 text-[10px] font-bold px-2 py-0.5">
                  <ShoppingCart className="h-3 w-3 inline-block mr-0.5 align-[-1px]" aria-hidden /> {cartCount}
                </span>
              )}
            </Link>
          }
        />
      </>)}
      {fromStore && <StoreContextNav slug={orgSlug} />}

      {/* "Vai al checkout" banner — appears when the cart has items. Gives
          customers a clear way to exit the multi-add flow and proceed. */}
      {cartCount > 0 && (
        <div className="max-w-4xl mx-auto px-4 sm:px-6 pt-4">
          <OpenCheckoutButton slug={orgSlug} itemCount={cartCount} variant="landing"
            mktpReturnTo={!fromStore ? window.location.pathname : null} />
        </div>
      )}

      {/* M2 — breadcrumb + condividi (solo guscio marketplace) */}
      {!fromStore && (
        <div className="max-w-4xl mx-auto px-4 sm:px-6 pt-3 pb-1 flex items-center justify-between gap-2">
          <nav className="text-xs text-gray-500 truncate">
            <Link to="/" className="hover:text-primary hover:underline">
              {t('landings:calendar.title', { defaultValue: 'Ritiri' })}
            </Link>
            {product.category && (<>
              <span className="mx-1.5" aria-hidden>›</span>
              <Link to={`/ritiri?categoria=${product.category}`} className="hover:text-primary hover:underline">
                {t(`landings:categories.${product.category}`, { defaultValue: product.category })}
              </Link>
            </>)}
            <span className="mx-1.5" aria-hidden>›</span>
            <span className="text-gray-700">{product.name}</span>
          </nav>
          <button
            type="button"
            onClick={() => {
              if (navigator.share) {
                navigator.share({ title: product.name, url: window.location.href }).catch(() => {});
              } else {
                navigator.clipboard?.writeText(window.location.href);
              }
            }}
            className="shrink-0 rounded-full border border-gray-300 bg-white px-3 py-1 text-xs font-medium text-gray-600 hover:border-primary hover:text-primary transition-colors"
          >
            {t('landings:event.share', { defaultValue: 'Condividi' })} ↗
          </button>
        </div>
      )}

      {/* Hero */}
      <div className="relative w-full bg-gray-900 overflow-hidden">
        {heroImage && (
          <img
            src={heroImage}
            alt={product.name}
            className="absolute inset-0 w-full h-full object-cover opacity-60"
          />
        )}
        <div className="relative max-w-4xl mx-auto px-4 sm:px-6 pt-10 pb-16 sm:pt-16 sm:pb-24">
          <div className="text-white">
            {/* store name already shown in header; skip the eyebrow
                here to avoid the duplicate label */}
            <h1 className="font-display text-3xl sm:text-4xl md:text-5xl font-bold leading-tight">
              {product.name}
            </h1>
            {/* AN7 — la fiducia si vede prima di prenotare */}
            {orgRating?.count > 0 && (
              <p className="mt-2 text-sm sm:text-base" data-testid="landing-org-rating">
                <span className="text-amber-300" aria-hidden>★</span>{' '}
                <span className="font-semibold">{orgRating.avg}</span>{' '}
                <span className="opacity-80">
                  · {t('landings:event.verifiedReviews', { count: orgRating.count, defaultValue: '{{count}} recensioni verificate' })}
                </span>
              </p>
            )}
            {dt && (
              <div className="mt-4 flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-4 text-sm sm:text-base">
                <span className="flex items-center gap-2">
                  <CalendarDays className="h-4 w-4 shrink-0" aria-hidden />
                  <span className="capitalize">{dt.date}</span>
                </span>
                <span className="flex items-center gap-2">
                  <Clock className="h-4 w-4 shrink-0" aria-hidden />
                  <span>
                    {dt.time}{dtEnd ? ` – ${dtEnd.time}` : ''}
                  </span>
                </span>
                {(occurrence.venue_name || occurrence.city) && (
                  <span className="flex items-center gap-2">
                    <MapPin className="h-4 w-4 shrink-0" aria-hidden />
                    <span>
                      {occurrence.venue_name}{occurrence.venue_name && occurrence.city ? ', ' : ''}{occurrence.city}
                    </span>
                  </span>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* M2 — griglia foto (1 grande + 4): le foto vendono i ritiri */}
      {allPhotos.length > 1 && (
        <div className="max-w-4xl mx-auto px-4 sm:px-6 pt-6">
          <div className="grid grid-cols-2 sm:grid-cols-4 grid-rows-2 gap-2 rounded-2xl overflow-hidden h-56 sm:h-80">
            <button type="button" onClick={() => setLightbox(0)}
                    className="col-span-2 row-span-2 relative group">
              <img src={allPhotos[0]} alt={`${product.name}${occurrence.city ? ` — ${occurrence.city}` : ''}`} fetchpriority="high" className="absolute inset-0 w-full h-full object-cover group-hover:brightness-95 transition" />
              {/* mobile: le miniature sono nascoste — il contatore invita al lightbox */}
              <span className="sm:hidden absolute bottom-2 right-2 rounded-full bg-black/60 text-white text-[11px] font-semibold px-2.5 py-1">
                1 / {allPhotos.length}
              </span>
            </button>
            {allPhotos.slice(1, 5).map((url, i) => (
              <button key={i} type="button" onClick={() => setLightbox(i + 1)}
                      className="relative group hidden sm:block">
                <img src={url} alt={`${product.name} — foto ${i + 2}`} loading="lazy" className="absolute inset-0 w-full h-full object-cover group-hover:brightness-95 transition" />
                {i === 3 && allPhotos.length > 5 && (
                  <span className="absolute inset-0 bg-black/50 flex items-center justify-center text-white text-sm font-semibold">
                    +{allPhotos.length - 5} {t('landings:event.morePhotos', { defaultValue: 'foto' })}
                  </span>
                )}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* M2 — lightbox essenziale, zero dipendenze */}
      {lightbox != null && (
        <div className="fixed inset-0 z-50 bg-black/90 flex items-center justify-center p-4"
             role="dialog" aria-modal="true"
             onClick={() => setLightbox(null)}>
          <button type="button" aria-label="Chiudi"
                  className="absolute top-4 right-5 text-white text-3xl leading-none"
                  onClick={() => setLightbox(null)}>×</button>
          {allPhotos.length > 1 && (<>
            <button type="button" aria-label="Precedente"
                    className="absolute left-3 text-white text-4xl px-3 py-6"
                    onClick={(e) => { e.stopPropagation(); setLightbox((lightbox - 1 + allPhotos.length) % allPhotos.length); }}>‹</button>
            <button type="button" aria-label="Successiva"
                    className="absolute right-3 text-white text-4xl px-3 py-6"
                    onClick={(e) => { e.stopPropagation(); setLightbox((lightbox + 1) % allPhotos.length); }}>›</button>
          </>)}
          <img src={allPhotos[lightbox]} alt={`${product.name} — foto ${lightbox + 1}`}
               className="max-h-full max-w-full object-contain rounded-lg"
               onClick={(e) => e.stopPropagation()} />
          <span className="absolute bottom-4 text-white/70 text-xs">{lightbox + 1} / {allPhotos.length}</span>
        </div>
      )}

      <div className="max-w-4xl mx-auto px-4 sm:px-6 py-6 sm:py-10 grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Left column — content */}
        <div className="md:col-span-2 space-y-6">
          {/* Quick facts card */}
          <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
            <h2 className="text-base font-semibold text-gray-900 mb-3">{t('landings:event.ataGlance')}</h2>
            <dl className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
              <div>
                <dt className="text-gray-500 text-xs uppercase tracking-wide">{t('landings:event.dateLabel')}</dt>
                <dd className="text-gray-900 font-medium capitalize">{dt?.date}</dd>
              </div>
              <div>
                <dt className="text-gray-500 text-xs uppercase tracking-wide">{t('landings:event.timeLabel')}</dt>
                <dd className="text-gray-900 font-medium">
                  {dt?.time}{dtEnd ? ` – ${dtEnd.time}` : ''}
                </dd>
              </div>
              {occurrence.venue_name && (
                <div className="sm:col-span-2">
                  <dt className="text-gray-500 text-xs uppercase tracking-wide">{t('landings:event.locationLabel')}</dt>
                  <dd className="text-gray-900 font-medium">{occurrence.venue_name}</dd>
                  {address && <p className="text-gray-600 text-sm">{address}</p>}
                </div>
              )}
              {!occurrence.venue_name && occurrence.location && (
                <div className="sm:col-span-2">
                  <dt className="text-gray-500 text-xs uppercase tracking-wide">{t('landings:event.locationLabel')}</dt>
                  <dd className="text-gray-900 font-medium">{occurrence.location}</dd>
                </div>
              )}
            </dl>
            {/* G4 — DOVE si svolge, senza uscire dalla pagina */}
            {occurrence.latitude != null && occurrence.longitude != null && (
              <React.Suspense fallback={null}>
                <StaticMiniMap latitude={occurrence.latitude} longitude={occurrence.longitude} />
              </React.Suspense>
            )}
            {occurrence.map_url && (
              <a
                href={occurrence.map_url} target="_blank" rel="noopener noreferrer"
                className="inline-flex items-center gap-2 mt-3 text-sm font-medium text-gray-900 hover:underline"
              >
                {t('landings:event.openInMaps')}
                <span aria-hidden>→</span>
              </a>
            )}
          </div>

          {/* Long description */}
          {occurrence.long_description && (
            <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
              <h2 className="text-base font-semibold text-gray-900 mb-3">{t('landings:event.descriptionHeading')}</h2>
              <MarkdownLite source={occurrence.long_description} />
            </div>
          )}

          {/* Fallback short description */}
          {!occurrence.long_description && product.description && (
            <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
              <p className="text-gray-700 leading-relaxed">{product.description}</p>
            </div>
          )}

          {/* Fase 3 — Programma giorno per giorno */}
          {(occurrence.agenda || []).length > 0 && (
            <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
              <h2 className="text-base font-semibold text-gray-900 mb-4">{t('landings:event.program.heading')}</h2>
              <div className="space-y-5">
                {occurrence.agenda.map((day, di) => (
                  <div key={di}>
                    <h3 className="text-sm font-bold text-gray-900 uppercase tracking-wide mb-2">{day.label}</h3>
                    <div className="space-y-2 border-l-2 border-gray-100 pl-4">
                      {(day.items || []).map((item, ii) => (
                        <div key={ii} className="text-sm">
                          <span className="text-gray-500 tabular-nums mr-2">{item.time}</span>
                          <span className="font-medium text-gray-900">{item.title}</span>
                          {item.description && (
                            <p className="text-gray-600 text-xs mt-0.5">{item.description}</p>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* M2 — la galleria vive nella griglia hero + lightbox */}

          {/* Fase 3 — Incluso / Non incluso */}
          {((occurrence.included || []).length > 0 || (occurrence.excluded || []).length > 0) && (
            <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
              <h2 className="text-base font-semibold text-gray-900 mb-3">{t('landings:event.includes.heading')}</h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {(occurrence.included || []).length > 0 && (
                  <div>
                    <p className="text-xs font-semibold text-emerald-700 uppercase tracking-wide mb-1.5">
                      {t('landings:event.includes.included')}
                    </p>
                    <ul className="space-y-1">
                      {occurrence.included.map((x, i) => (
                        <li key={i} className="text-sm text-gray-700 flex gap-2">
                          <span className="text-emerald-600" aria-hidden>✓</span>{x}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                {(occurrence.excluded || []).length > 0 && (
                  <div>
                    <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5">
                      {t('landings:event.includes.excluded')}
                    </p>
                    <ul className="space-y-1">
                      {occurrence.excluded.map((x, i) => (
                        <li key={i} className="text-sm text-gray-500 flex gap-2">
                          <span aria-hidden>—</span>{x}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Fase 3 — FAQ */}
          {(occurrence.faq || []).length > 0 && (
            <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
              <h2 className="text-base font-semibold text-gray-900 mb-3">{t('landings:event.faq.heading')}</h2>
              <div className="space-y-3">
                {occurrence.faq.map((entry, i) => (
                  <details key={i} className="group">
                    <summary className="text-sm font-medium text-gray-900 cursor-pointer list-none flex items-center justify-between">
                      {entry.q}
                      <span className="text-gray-400 group-open:rotate-45 transition-transform" aria-hidden>+</span>
                    </summary>
                    <p className="text-sm text-gray-600 mt-1.5">{entry.a}</p>
                  </details>
                ))}
              </div>
            </div>
          )}

          {/* Fase 2 S2 — Come paghi + policy di cancellazione (dal piano
              configurato sul prodotto; la policy si mostra SEMPRE quando
              presente, anche in modalità pagamento unico: guida i rimborsi) */}
          {(() => {
            const plan = product?.payment_plan;
            if (!plan) return null;
            const showDeposit = plan.mode && plan.mode !== 'full';
            const policy = plan.cancellation_policy || [];
            if (!showDeposit && policy.length === 0) return null;
            return (
              <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
                <h2 className="text-base font-semibold text-gray-900 mb-3">
                  {t('landings:event.paymentPlan.heading')}
                </h2>
                {showDeposit && (
                  <p className="text-sm text-gray-700 mb-3">
                    {plan.deposit_type === 'percent'
                      ? t('landings:event.paymentPlan.depositPercent', {
                          percent: plan.deposit_value,
                          days: plan.balance_due_days_before,
                        })
                      : t('landings:event.paymentPlan.depositFixed', {
                          amount: formatPrice((plan.deposit_value || 0) / 100, effectiveCurrency, i18n.language),
                          days: plan.balance_due_days_before,
                        })}
                    {plan.mode === 'deposit_installments' &&
                      ' ' + t('landings:event.paymentPlan.installmentsNote', {
                        count: plan.installments_count,
                      })}
                  </p>
                )}
                {policy.length > 0 && (
                  <>
                    <h3 className="text-sm font-semibold text-gray-900 mb-1.5">
                      {t('landings:event.paymentPlan.policyHeading')}
                    </h3>
                    <ul className="text-sm text-gray-600 space-y-0.5">
                      {policy.map((tier, i) => (
                        <li key={i}>
                          {i < policy.length - 1
                            ? t('landings:event.paymentPlan.policyTier', {
                                days: tier.days_before, percent: tier.refund_percent,
                              })
                            : t('landings:event.paymentPlan.policyLast', {
                                percent: tier.refund_percent,
                              })}
                        </li>
                      ))}
                    </ul>
                  </>
                )}
              </div>
            );
          })()}
        </div>

        {/* Right column — tiers + checkout (sticky on desktop) */}
        <aside id="prenota" className="md:sticky md:top-20 md:self-start space-y-4 scroll-mt-20">
          {!isBuyable ? (
            <div className="rounded-xl border-2 border-red-200 bg-red-50 p-5 text-center">
              <p className="text-lg font-bold text-red-900 mb-1">{t('landings:event.soldOutTitle')}</p>
              <p className="text-sm text-red-700">
                {t('landings:event.soldOutBody')}
              </p>
            </div>
          ) : (
            <>
              {(occurrence.tiers && occurrence.tiers.length > 0) ? (
                <div className="space-y-3">
                  <h2 className="text-base font-semibold text-gray-900">{t('landings:event.tiersHeading')}</h2>
                  <p className="text-xs text-gray-500">
                    {t('landings:event.tiersHint')}
                  </p>
                  {occurrence.tiers.map(tier => (
                    <TierCard
                      key={tier.id}
                      tier={tier}
                      currency={effectiveCurrency}
                      qty={Number(tierQuantities[tier.id] || 0)}
                      onQtyChange={(next) => setTierQuantities(prev => {
                        const n = Math.max(0, Number(next) || 0);
                        const out = { ...prev };
                        if (n <= 0) delete out[tier.id];
                        else out[tier.id] = n;
                        return out;
                      })}
                    />
                  ))}
                </div>
              ) : (
                <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm space-y-3">
                  <h2 className="text-base font-semibold text-gray-900">{t('landings:event.ticketHeading')}</h2>
                  {occurrence.price_override !== null && occurrence.price_override !== undefined && (
                    <p className="text-2xl font-bold text-gray-900">
                      {formatPrice(occurrence.price_override, effectiveCurrency, i18n.language)}
                    </p>
                  )}
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-medium text-gray-700">{t('landings:event.qtyLabel')}</span>
                    <div className="flex items-center gap-1 rounded-md border border-gray-300 bg-white">
                      <button type="button" onClick={() => setPlainQty(Math.max(1, plainQty - 1))}
                        className="px-2 py-1 hover:bg-gray-100 text-sm" disabled={plainQty <= 1}>−</button>
                      <span className="px-3 py-1 text-sm font-semibold">{plainQty}</span>
                      <button type="button" onClick={() => setPlainQty(plainQty + 1)}
                        className="px-2 py-1 hover:bg-gray-100 text-sm">+</button>
                    </div>
                  </div>
                </div>
              )}

              {/* Consolidation: single checkout surface. The landing
                  never submits an order — clicking "Procedi al checkout"
                  navigates to /s/:orgSlug with the selection in
                  location.state, and the storefront hydrates its cart
                  and opens the existing checkout dialog. */}
              <ProceedToCheckoutBar
                orgSlug={orgSlug}
                product={product}
                occurrence={occurrence}
                tierQuantities={tierQuantities}
                plainQty={plainQty}
                currency={effectiveCurrency}
              />

              {/* M2 — blocco fiducia: la promessa di piattaforma sotto la CTA */}
              <ul className="rounded-xl border border-gray-200 bg-white p-4 space-y-2 text-xs text-gray-600">
                <li className="flex items-start gap-2">
                  <ShieldCheck className="h-4 w-4 shrink-0 text-[#376254]" aria-hidden />
                  <span>{t('landings:event.trustSecure', { defaultValue: 'Pagamento sicuro con carta. I tuoi dati non passano mai dall\'organizzatore.' })}</span>
                </li>
                <li className="flex items-start gap-2">
                  <Sprout className="h-4 w-4 shrink-0 text-[#376254]" aria-hidden />
                  <span>{t('landings:event.trustDeposit', { defaultValue: 'Dove previsto, blocchi il posto con la caparra e saldi più avanti.' })}</span>
                </li>
                <li className="flex items-start gap-2">
                  <MailCheck className="h-4 w-4 shrink-0 text-[#376254]" aria-hidden />
                  <span>{t('landings:event.trustTicket', { defaultValue: 'Biglietto e promemoria via email, subito dopo la prenotazione.' })}</span>
                </li>
              </ul>

              {/* AN7 — le domande che frenano una prenotazione, risolte qui */}
              <div className="rounded-xl border border-gray-200 bg-white p-4" data-testid="booking-faq">
                <p className="text-xs font-semibold uppercase tracking-wide text-gray-400 mb-2">
                  {t('landings:event.faqHeading', { defaultValue: 'Domande frequenti' })}
                </p>
                <details className="group border-b border-gray-100 pb-2 mb-2">
                  <summary className="cursor-pointer text-sm font-medium text-gray-800 list-none flex justify-between items-center">
                    {t('landings:event.faqDepositQ', { defaultValue: 'Come funziona la caparra?' })}
                    <span className="text-gray-400 group-open:rotate-180 transition-transform" aria-hidden>⌄</span>
                  </summary>
                  <p className="mt-1.5 text-xs text-gray-600 leading-relaxed">
                    {t('landings:event.faqDepositA', { defaultValue: 'Dove prevista, la caparra blocca il tuo posto: paghi ora solo una parte e saldi il resto secondo gli accordi con chi organizza. Il pagamento passa da Stripe, mai di mano in mano.' })}
                  </p>
                </details>
                <details className="group border-b border-gray-100 pb-2 mb-2">
                  <summary className="cursor-pointer text-sm font-medium text-gray-800 list-none flex justify-between items-center">
                    {t('landings:event.faqAfterQ', { defaultValue: 'Cosa succede dopo la prenotazione?' })}
                    <span className="text-gray-400 group-open:rotate-180 transition-transform" aria-hidden>⌄</span>
                  </summary>
                  <p className="mt-1.5 text-xs text-gray-600 leading-relaxed">
                    {t('landings:event.faqAfterA', { defaultValue: 'Ricevi subito il biglietto via email, con i dettagli del ritiro e i contatti di chi lo organizza. Tutte le tue esperienze restano raccolte nel tuo Passaporto Aurya.' })}
                  </p>
                </details>
                <details className="group">
                  <summary className="cursor-pointer text-sm font-medium text-gray-800 list-none flex justify-between items-center">
                    {t('landings:event.faqWhoQ', { defaultValue: 'Con chi posso parlare prima di prenotare?' })}
                    <span className="text-gray-400 group-open:rotate-180 transition-transform" aria-hidden>⌄</span>
                  </summary>
                  <p className="mt-1.5 text-xs text-gray-600 leading-relaxed">
                    {t('landings:event.faqWhoA', { defaultValue: 'Ogni ritiro ha un volto: trovi la presentazione e il profilo di chi organizza qui sotto, con la sua storia e le recensioni di chi ha già partecipato.' })}
                  </p>
                </details>
              </div>
            </>
          )}
        </aside>
      </div>

      {/* F5 — trasparenza: contenuti tradotti automaticamente */}
      {data.auto_translated && (
        <div className="max-w-4xl mx-auto px-4 sm:px-6 pb-2">
          <p className="text-[11px] text-gray-500 text-center">
            {t('landings:event.autoTranslated', { defaultValue: 'Contenuti tradotti automaticamente dall\'italiano.' })}{' '}
            <button type="button" onClick={() => i18n.changeLanguage('it')} className="underline hover:text-gray-700">
              {t('landings:event.seeOriginal', { defaultValue: 'Vedi originale' })}
            </button>
          </p>
        </div>
      )}

      {/* F2.1 — Organizzato da: la card fiducia che porta al profilo */}
      {operator?.name && (
        <section className="max-w-4xl mx-auto px-4 sm:px-6 pb-4">
          {/* Nel contesto store il profilo e' la pagina Chi siamo DENTRO
              il guscio del negozio; /o/ resta per la directory */}
          <Link to={fromStore ? `/s/${orgSlug}/chi-siamo` : `/o/${orgSlug}`}
                className="flex items-center gap-4 rounded-2xl border border-gray-200 bg-white p-4 hover:shadow-md transition-shadow">
            {operator.logo_url
              ? <img src={operator.logo_url} alt={`Logo di ${operator.name}`} className="h-14 w-14 rounded-full object-cover shrink-0" />
              : <div className="h-14 w-14 rounded-full bg-emerald-50 flex items-center justify-center shrink-0" aria-hidden><Flower2 className="h-7 w-7 text-[#376254]/60" /></div>}
            <div className="min-w-0 flex-1">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-gray-400">
                {t('landings:event.organizedBy', { defaultValue: 'Organizzato da' })}
              </p>
              <p className="font-semibold text-gray-900 truncate">{operator.name}</p>
              {operator.bio && (
                <p className="text-sm text-gray-600 line-clamp-2 mt-0.5">{operator.bio}</p>
              )}
            </div>
            <span className="shrink-0 text-sm font-medium text-emerald-700">
              {t('landings:event.viewProfile', { defaultValue: 'Vedi profilo' })} →
            </span>
          </Link>
        </section>
      )}

      {/* AN7 — recensioni verificate dove si decide */}
      {orgRating?.count > 0 && (
        <ReviewsSnippet orgSlug={orgSlug} rating={orgRating} t={t} />
      )}

      {/* S5 — correlati per categoria (solo marketplace) */}
      {!fromStore && product?.category && (
        <RelatedRetreats
          category={product.category}
          excludePath={`/e/${orgSlug}/${slug}`}
          t={t}
        />
      )}

      {/* M6 — mobile: prezzo+CTA sempre a portata di pollice */}
      {isBuyable && (
        <div className="md:hidden fixed bottom-0 inset-x-0 z-30 border-t border-gray-200 bg-white/95 backdrop-blur px-4 py-3 flex items-center justify-between gap-3">
          <div className="leading-tight">
            {(() => {
              const base = occurrence.price_override ?? product.unit_price;
              return base != null ? (<>
                <span className="text-[11px] text-gray-500 block">
                  {t('landings:calendar.from', { defaultValue: 'da' })}
                </span>
                <span className="font-bold text-gray-900">{Number(base).toLocaleString('it-IT')} €</span>
              </>) : (
                <span className="text-sm text-gray-600">{t('landings:event.tiersHeading')}</span>
              );
            })()}
          </div>
          <button
            type="button"
            onClick={() => document.getElementById('prenota')?.scrollIntoView({ block: 'start' })}
            className="rounded-full bg-accent text-accent-foreground px-6 py-2.5 text-sm font-bold shadow-md"
          >
            {t('landings:event.mobileBook', { defaultValue: 'Prenota' })}
          </button>
        </div>
      )}

      <footer className="max-w-4xl mx-auto px-4 sm:px-6 py-8 text-center text-xs text-gray-500">
        <Trans
          i18nKey="landings:event.footerOrganizedBy"
          values={{ name: storeInfo?.display_name || orgName }}
          components={[<span className="font-medium text-gray-700" />]}
        />
        <span aria-hidden className="mx-2">·</span>
        <Link to={`/s/${orgSlug}`} className="underline hover:text-gray-900">{t('landings:event.seeOtherEvents')}</Link>
        <span aria-hidden className="mx-2">·</span>
        <Link to="/" className="underline hover:text-gray-900">
          {t('landings:event.findMoreRetreats', { defaultValue: 'Scopri altri ritiri' })}
        </Link>
      </footer>
    </div>
    </Wrap>
  );
}
