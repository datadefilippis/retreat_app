/**
 * CustomerTopBar — top header for the customer portal layout.
 *
 *   ┌──────────────────────────────────────────────────────┐
 *   │  ☰   [logo] · Store    "Area riservata"   [Davide ▾]│
 *   └──────────────────────────────────────────────────────┘
 *
 * - Left: hamburger toggle (visible only <lg) + brand mark + store name
 * - Right: customer pill with name + email tooltip
 *
 * The brand mark resolves through the cascade Store > Org > Fallback:
 *   • `logoUrl` prop set → render <img> (the store logo, OR the
 *     org-wide default when the store doesn't have its own — the
 *     parent (CustomerLayout) does the resolution via getCatalog).
 *   • `logoUrl` absent → render the 🎓 emoji as a friendly default.
 *
 * The brand mark acts as a "back to start" shortcut on desktop. It
 * targets /account/orders (the customer portal's home after the
 * dashboard HomePage was removed). On mobile it's just a label —
 * the hamburger handles navigation via the drawer.
 *
 * Stays presentational. Drawer toggle state is owned by the parent
 * (CustomerLayout) so the sidebar drawer can be controlled from any
 * other location too (future: gesture swipe).
 */

import React from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Menu } from 'lucide-react';


export default function CustomerTopBar({
  customer,
  storeName = null,
  logoUrl = null,
  onToggleDrawer,
}) {
  const { t } = useTranslation('customer_portal');
  return (
    <header className="bg-white border-b sticky top-0 z-30">
      <div className="px-4 h-14 flex items-center justify-between gap-3">
        {/* Left cluster — hamburger + brand */}
        <div className="flex items-center gap-3 min-w-0">
          <button
            type="button"
            onClick={onToggleDrawer}
            className="lg:hidden p-2 -ml-2 rounded-md hover:bg-gray-100 transition-colors"
            aria-label={t('customer_portal:topbar.openMenu')}
          >
            <Menu className="h-5 w-5 text-gray-700" />
          </button>
          <Link
            to="/account/orders"
            className="flex items-center gap-2 min-w-0 hover:opacity-80 transition-opacity"
            aria-label={t('customer_portal:topbar.goOrdersAria')}
          >
            {/* Brand mark — logo from the resolved cascade (store >
                org > fallback). Falls back to a graduation emoji
                when no logo is configured at any level. The 8x8 box
                stays square so the layout doesn't shift between
                logo + emoji modes. `object-contain` keeps the
                aspect ratio of asymmetric logos. */}
            {logoUrl ? (
              <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-white border border-gray-200 overflow-hidden shrink-0">
                <img
                  src={logoUrl}
                  alt=""
                  className="h-full w-full object-contain"
                />
              </span>
            ) : (
              <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-gray-900 text-white text-sm shrink-0">
                🎓
              </span>
            )}
            <div className="min-w-0">
              <span className="font-semibold text-base text-gray-900 leading-none block truncate">
                {t('customer_portal:topbar.title')}
              </span>
              {storeName && (
                <p className="text-[11px] text-gray-500 leading-none mt-0.5 truncate">
                  {storeName}
                </p>
              )}
            </div>
          </Link>
        </div>

        {/* Right cluster — customer identity pill */}
        <div className="flex items-center gap-2 shrink-0">
          {customer && (
            <div
              className="flex items-center gap-2 px-2.5 py-1.5 rounded-full bg-gray-100"
              title={customer.email}
            >
              <div className="flex h-6 w-6 items-center justify-center rounded-full bg-gray-900 text-white text-[10px] font-bold shrink-0">
                {(customer.name || customer.email || '?').charAt(0).toUpperCase()}
              </div>
              <span className="text-xs font-semibold text-gray-800 max-w-[140px] truncate">
                {customer.name || customer.email}
              </span>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
