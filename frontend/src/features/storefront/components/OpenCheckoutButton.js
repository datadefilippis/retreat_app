/**
 * OpenCheckoutButton — reusable "Vai al checkout" CTA.
 *
 * Deep-links to `/s/${slug}?checkout=1` so that StorefrontPage can auto-open
 * the checkout modal from any entry point (the catalog header, the mini-cart
 * bar, or a landing page). StorefrontPage strips the `?checkout=1` query
 * param after consuming it, so a page refresh does not re-trigger the modal.
 *
 * Variants:
 *   - "header"  : compact pill for the storefront header rightSlot
 *   - "bar"     : inline text button for the mini-cart summary bar
 *   - "landing" : prominent sticky card for landing pages (cart > 0)
 *
 * The component renders nothing when `slug` is missing or `itemCount` is 0,
 * so call sites can render it unconditionally.
 */

import React from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';

function CartIcon({ className = 'h-4 w-4' }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      <circle cx="9" cy="21" r="1" />
      <circle cx="20" cy="21" r="1" />
      <path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6" />
    </svg>
  );
}

export default function OpenCheckoutButton({
  slug,
  itemCount,
  variant = 'bar',
  className = '',
  // K1+ — contesto marketplace: il checkout si apre col SIPARIO (la
  // vetrina resta invisibile) e alla chiusura si torna a questo path.
  mktpReturnTo = null,
}) {
  const { t } = useTranslation('storefront');
  if (!slug || !itemCount) return null;

  const href = `/s/${encodeURIComponent(slug)}?checkout=1`;
  const linkProps = mktpReturnTo
    ? { to: `/s/${encodeURIComponent(slug)}`, state: { mktpOpen: { returnTo: mktpReturnTo } } }
    : { to: href };

  if (variant === 'landing') {
    return (
      <Link
        {...linkProps}
        className={`flex items-center justify-between gap-3 rounded-xl bg-[var(--sf-accent,#111827)] text-[var(--sf-accent-fg,#ffffff)] px-4 py-3 shadow-md hover:bg-[var(--sf-accent-hover,#1f2937)] transition-colors ${className}`}
      >
        <span className="flex items-center gap-2 font-semibold text-sm">
          <CartIcon className="h-4 w-4" />
          {t('storefront:miniCart.itemsInCart', { count: itemCount })}
        </span>
        <span className="text-sm font-bold">{t('storefront:openCheckoutBtn.goCheckout')}</span>
      </Link>
    );
  }

  if (variant === 'header') {
    return (
      <Link
        to={href}
        aria-label={t('storefront:openCheckoutBtn.openCheckoutAria')}
        className={`inline-flex items-center gap-1.5 rounded-full bg-[var(--sf-accent,#111827)] text-[var(--sf-accent-fg,#ffffff)] px-3 py-1.5 text-xs font-semibold hover:bg-[var(--sf-accent-hover,#1f2937)] transition-colors ${className}`}
      >
        <CartIcon className="h-3.5 w-3.5" />
        <span className="hidden sm:inline">{t('storefront:openCheckoutBtn.checkoutShort')}</span>
        <span className="inline-flex items-center justify-center rounded-full bg-white text-gray-900 text-[10px] font-bold min-w-[18px] h-[18px] px-1">
          {itemCount}
        </span>
      </Link>
    );
  }

  // variant === 'bar'
  return (
    <Link
      to={href}
      className={`inline-flex items-center gap-1 rounded-md bg-[var(--sf-accent,#111827)] text-[var(--sf-accent-fg,#ffffff)] px-3 py-1 text-xs font-semibold hover:bg-[var(--sf-accent-hover,#1f2937)] transition-colors ${className}`}
    >
      {t('storefront:openCheckoutBtn.goCheckout')}
    </Link>
  );
}
