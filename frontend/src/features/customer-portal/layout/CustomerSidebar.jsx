/**
 * CustomerSidebar — vertical navigation for the customer portal.
 *
 * Layout pattern:
 *
 *   ┌────────────────────┐
 *   │  🎓 Corsi          │  ← visible only when the customer owns ≥1
 *   │  🧾 Ordini         │
 *   │  ⚙ Profilo        │
 *   │  ────────────────  │
 *   │  ↩ Torna al catalogo │
 *   │  ⏻ Esci             │
 *   └────────────────────┘
 *
 * The Home/dashboard entry was removed in a follow-up to Phase 7 — the
 * dashboard page didn't deliver value over the orders list, so /account
 * now redirects straight to /account/orders and the sidebar omits the
 * Home item entirely. The first sidebar entry (Corsi when present,
 * otherwise Ordini) is the customer's natural landing.
 *
 * The catalog link sits in a "secondary" group below a divider so it's
 * always reachable without competing visually with the main portal
 * sections. Logout is the last item — destructive actions always go
 * to the bottom in our design system.
 *
 * Behavior contract:
 *   - Active route is detected via `NavLink`. We compare against
 *     `end={true}` for /account so it doesn't match nested paths.
 *   - The "🎓 Corsi" item appears only when the customer owns at least
 *     one active enrollment (otherwise the section is irrelevant).
 *     This mirrors the existing conditional pill behavior on the home.
 *   - Mobile: caller passes `onItemClick` to close the drawer when an
 *     item is tapped.
 *
 * Stays presentational — no data fetching here. Data (`hasAnyCourse`,
 * `customer`, `storeSlug`) is provided by the parent layout via props
 * so this component is trivially testable in isolation.
 */

import React from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { GraduationCap, ShoppingBag, User, ExternalLink, LogOut } from 'lucide-react';


function NavItem({ to, end = false, icon: Icon, label, onClick, badge = null }) {
  return (
    <NavLink
      to={to}
      end={end}
      onClick={onClick}
      className={({ isActive }) => `
        flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors
        ${isActive
          ? 'bg-gray-900 text-white'
          : 'text-gray-700 hover:bg-gray-100'}
      `}
    >
      <Icon className="h-4 w-4 shrink-0" />
      <span className="flex-1 truncate">{label}</span>
      {badge != null && (
        <span className="shrink-0 inline-flex items-center justify-center min-w-[18px] h-[18px] px-1 rounded-full bg-blue-100 text-blue-900 text-[10px] font-bold">
          {badge}
        </span>
      )}
    </NavLink>
  );
}


export default function CustomerSidebar({
  hasAnyCourse = false,
  coursesBadge = null,
  storeSlug = null,
  onLogout,
  onItemClick = null,
}) {
  const navigate = useNavigate();
  const { t } = useTranslation('customer_portal');

  const handleLogout = () => {
    if (typeof onLogout === 'function') onLogout();
    else navigate('/account/login');
  };

  return (
    <nav className="flex flex-col h-full p-3 gap-1" aria-label={t('customer_portal:sidebar.navAria')}>
      {/* Primary group — main portal sections.
          Order: courses first (when owned) so the highest-value
          surface is the first item the eye lands on. Orders second
          (commerce ledger). Profile last. No "Home" entry — /account
          redirects to /account/orders, the sidebar's first reachable
          link is the natural home. */}
      <div className="space-y-0.5">
        {hasAnyCourse && (
          <NavItem
            to="/account/courses"
            icon={GraduationCap}
            label={t('customer_portal:sidebar.courses')}
            badge={coursesBadge}
            onClick={onItemClick}
          />
        )}
        <NavItem to="/account/orders" icon={ShoppingBag} label={t('customer_portal:sidebar.orders')} onClick={onItemClick} />
        <NavItem to="/account/profile" icon={User} label={t('customer_portal:sidebar.profile')} onClick={onItemClick} />
      </div>

      {/* Spacer → pushes secondary group to the bottom on tall sidebars */}
      <div className="flex-1" aria-hidden />

      {/* Divider before the secondary actions group */}
      <div className="my-2 border-t border-gray-200" aria-hidden />

      {/* Secondary group — exit-to-catalog + logout. Catalog link uses
          a regular `<a>` because it routes outside the SPA portal area
          (it's the public storefront). Browser handles the navigation;
          NavLink's active-state logic doesn't make sense here. */}
      <div className="space-y-0.5">
        {storeSlug && (
          <a
            href={`/s/${storeSlug}`}
            onClick={onItemClick}
            className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium text-gray-600 hover:bg-gray-100 transition-colors"
          >
            <ExternalLink className="h-4 w-4 shrink-0" />
            <span className="flex-1 truncate">{t('customer_portal:sidebar.backToCatalog')}</span>
          </a>
        )}
        <button
          type="button"
          onClick={() => { onItemClick?.(); handleLogout(); }}
          className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium text-gray-600 hover:bg-red-50 hover:text-red-700 transition-colors"
        >
          <LogOut className="h-4 w-4 shrink-0" />
          <span className="flex-1 text-left truncate">{t('customer_portal:sidebar.logout')}</span>
        </button>
      </div>
    </nav>
  );
}
