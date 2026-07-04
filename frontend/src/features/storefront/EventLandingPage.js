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
import OpenCheckoutButton from './components/OpenCheckoutButton';
import useCartCount from './hooks/useCartCount';
import { effectivePlan } from './lib/paymentPlan';


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

  const handleProceed = () => {
    if (needsTierSelection) return;
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
        onClick={handleProceed}
        disabled={needsTierSelection}
        className="w-full rounded-md bg-[var(--sf-accent,#111827)] text-[var(--sf-accent-fg,#ffffff)] px-4 py-3 text-sm font-semibold hover:bg-[var(--sf-accent-hover,#1f2937)] disabled:opacity-50 flex items-center justify-center gap-2"
      >
        {isDirectMode && <span aria-hidden>💳</span>}
        {needsTierSelection
          ? t('landings:event.ctaSelectTier')
          : t('landings:event.ctaAdd')}
      </button>

      <p className="text-[11px] text-gray-500 text-center">
        {t('landings:event.checkoutHint')}
      </p>
    </div>
  );
}


// ── Main component ─────────────────────────────────────────────────────────

export default function EventLandingPage() {
  const { org_slug: orgSlug, slug } = useParams();
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

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    storefrontAPI.getEventLanding(orgSlug, slug)
      .then(res => { if (mounted) { setData(res.data); setLoading(false); } })
      .catch(err => {
        if (!mounted) return;
        setError(err?.response?.status === 404 ? 'not_found' : 'generic');
        setLoading(false);
      });
    return () => { mounted = false; };
  }, [orgSlug, slug]);

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

  const { product, occurrence, is_buyable: isBuyable, store_info: storeInfo, org_name: orgName, currency } = data;
  const effectiveCurrency = product.currency || 'EUR';
  const heroImage = occurrence.cover_image_url || product.image_url;

  return (
    <div className="min-h-screen bg-gray-50">
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
                🛒 {cartCount}
              </span>
            )}
          </Link>
        }
      />

      {/* "Vai al checkout" banner — appears when the cart has items. Gives
          customers a clear way to exit the multi-add flow and proceed. */}
      {cartCount > 0 && (
        <div className="max-w-4xl mx-auto px-4 sm:px-6 pt-4">
          <OpenCheckoutButton slug={orgSlug} itemCount={cartCount} variant="landing" />
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
            <h1 className="text-3xl sm:text-4xl md:text-5xl font-bold leading-tight">
              {product.name}
            </h1>
            {dt && (
              <div className="mt-4 flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-4 text-sm sm:text-base">
                <span className="flex items-center gap-2">
                  <span aria-hidden>📅</span>
                  <span className="capitalize">{dt.date}</span>
                </span>
                <span className="flex items-center gap-2">
                  <span aria-hidden>🕒</span>
                  <span>
                    {dt.time}{dtEnd ? ` – ${dtEnd.time}` : ''}
                  </span>
                </span>
                {(occurrence.venue_name || occurrence.city) && (
                  <span className="flex items-center gap-2">
                    <span aria-hidden>📍</span>
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

          {/* Fase 3 — Galleria */}
          {(occurrence.gallery_urls || []).length > 0 && (
            <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
              <h2 className="text-base font-semibold text-gray-900 mb-3">{t('landings:event.gallery.heading')}</h2>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                {occurrence.gallery_urls.map((url, i) => (
                  <img
                    key={i}
                    src={url}
                    alt=""
                    loading="lazy"
                    className="w-full h-32 sm:h-36 object-cover rounded-lg"
                  />
                ))}
              </div>
            </div>
          )}

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
        <aside className="md:sticky md:top-4 md:self-start space-y-4">
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
            </>
          )}
        </aside>
      </div>

      <footer className="max-w-4xl mx-auto px-4 sm:px-6 py-8 text-center text-xs text-gray-500">
        <Trans
          i18nKey="landings:event.footerOrganizedBy"
          values={{ name: storeInfo?.display_name || orgName }}
          components={[<span className="font-medium text-gray-700" />]}
        />
        <span aria-hidden className="mx-2">·</span>
        <Link to={`/s/${orgSlug}`} className="underline hover:text-gray-900">{t('landings:event.seeOtherEvents')}</Link>
      </footer>
    </div>
  );
}
