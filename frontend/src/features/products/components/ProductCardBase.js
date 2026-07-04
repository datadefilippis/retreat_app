/**
 * ProductCardBase — shared visual skeleton for admin product grid cards.
 *
 * Single source of truth for the card look across all product types so that
 * extending the catalog with a new type is mostly a matter of wiring data —
 * not redesigning the card.
 *
 * Used by ServicesGrid, EventsGrid, ReservationsGrid, PhysicalGrid (and any
 * future type grid). The canonical reference today is ServicesGrid — this
 * component matches that design exactly.
 *
 * Contract:
 *   <ProductCardBase
 *     hero={{ src, gradientFrom, gradientTo, fallbackEmoji, typeBadge }}
 *     href="/services/abc123"               // dashboard link for the whole card
 *     title="Consulenza strategica"
 *     overline="Su richiesta · 60 min"      // optional
 *     description="Short 1–2 line description"
 *     price={120}                            // optional, formatted as "Da €X,XX"
 *     statusChip={<StatusChip ... />}       // caller-owned pill (status toggle logic)
 *     secondaryCta={{ href, label, title, target }}  // optional: e.g. preview landing
 *   />
 *
 * The caller supplies:
 *   - `href`: the dashboard URL (where "Dashboard" button and title click go)
 *   - `statusChip`: a ready-to-render status control. Kept external because
 *     the status mutation path (is_published toggle) is API-side and would
 *     drag reservation/event-specific concerns into this base component.
 *   - `hero`: visual config for the top image area.
 *
 * Intentionally unopinionated about state: no data fetching, no mutation,
 * no i18n. Pure presentational.
 */

import React from 'react';
import { Link } from 'react-router-dom';
import { formatAmount } from '../../../utils/currency';


const fmtMoney = (n, currency = 'EUR') => {
  if (n == null || n === '') return null;
  // CH compliance v1: CHF uses the shared Swiss-style formatter so cards
  // read consistently with the storefront, the email and the receipt.
  if (String(currency || '').toUpperCase() === 'CHF') {
    return formatAmount(Number(n), 'CHF');
  }
  try {
    return new Intl.NumberFormat('it-IT', { style: 'currency', currency }).format(Number(n));
  } catch {
    return `${n} ${currency}`;
  }
};


export default function ProductCardBase({
  hero = {},
  href,
  title,
  overline,
  description,
  price,
  currency = 'EUR',
  statusChip,
  secondaryCta,
  dashboardLabel = 'Dashboard',
}) {
  const {
    src,
    gradientFrom = 'from-gray-700',
    gradientTo = 'to-gray-500',
    fallbackEmoji,
    typeBadge,
  } = hero;

  const priceLabel = fmtMoney(price, currency);

  return (
    <div className="rounded-xl border border-gray-200 bg-white shadow-sm overflow-hidden flex flex-col">
      {/* Hero */}
      <Link
        to={href || '#'}
        className={`relative aspect-[16/9] bg-gradient-to-br ${gradientFrom} ${gradientTo} overflow-hidden block`}
      >
        {src && (
          <img
            src={src}
            alt=""
            className="w-full h-full object-cover hover:scale-[1.02] transition-transform duration-200"
          />
        )}
        {typeBadge && (
          <div className="absolute top-2 left-2 flex gap-1">
            <span className="inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-semibold bg-white/90 text-gray-900">
              {typeBadge}
            </span>
          </div>
        )}
        {!src && fallbackEmoji && (
          <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
            <span className="text-5xl opacity-60">{fallbackEmoji}</span>
          </div>
        )}
      </Link>

      {/* Body */}
      <div className="p-4 flex-1 flex flex-col gap-2">
        <div>
          <Link to={href || '#'} className="block hover:underline">
            <h3 className="font-bold text-gray-900 line-clamp-2">
              {title || 'Senza nome'}
            </h3>
          </Link>
          {overline && (
            <p className="text-[11px] uppercase tracking-wide text-gray-500 font-semibold mt-1">
              {overline}
            </p>
          )}
          {description && (
            <p className="text-xs text-gray-600 mt-1 line-clamp-2">{description}</p>
          )}
        </div>

        {priceLabel && (
          <p className="text-sm text-gray-700">
            Da <strong>{priceLabel}</strong>
          </p>
        )}

        <div className="mt-auto pt-2 space-y-2">
          {statusChip && (
            <div className="flex items-center justify-between gap-2">
              <span className="text-[10px] uppercase tracking-wide text-gray-500 font-semibold">
                Stato
              </span>
              {statusChip}
            </div>
          )}
          <div className="flex gap-2">
            <Link
              to={href || '#'}
              className="flex-1 text-center text-xs font-semibold rounded-md bg-gray-900 text-white px-2 py-1.5 hover:bg-gray-800"
            >
              {dashboardLabel}
            </Link>
            {secondaryCta?.href && (
              <Link
                to={secondaryCta.href}
                target={secondaryCta.target || '_blank'}
                rel="noopener noreferrer"
                title={secondaryCta.title}
                className="text-center text-xs font-semibold rounded-md border border-gray-300 text-gray-900 px-2 py-1.5 hover:border-gray-900"
              >
                {secondaryCta.label || '🔗'}
              </Link>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
