/**
 * CustomerLayout — shared shell for every authenticated customer
 * portal page (Phase 2 of the customer area refactor).
 *
 * Anatomy:
 *
 *   ┌─ TopBar (mobile + desktop, sticky) ─────────────────────┐
 *   ├─────────┬───────────────────────────────────────────────┤
 *   │ Sidebar │  EmailVerificationBanner (sticky if unverified)│
 *   │ (desk-  │  ─────────────────────────────────────────────│
 *   │ top    │  <Outlet>  ← page-specific content            │
 *   │ ≥1024  │                                                │
 *   │ px)    │                                                │
 *   └─────────┴───────────────────────────────────────────────┘
 *
 * Behavior:
 *   - Sidebar is fixed on desktop (≥lg), becomes a drawer on mobile
 *     toggleable from the TopBar hamburger.
 *   - Auto-closes the drawer on route change (UX expectation).
 *   - EmailVerificationBanner is rendered in-line at the top of the
 *     main scroll area — visible on every page until the customer
 *     verifies their email.
 *   - Reads `useMyCourses` to decide whether to surface the "I miei
 *     corsi" sidebar entry. Empty/error → sidebar skips it silently.
 *
 * NOT YET WIRED INTO ROUTES — Phase 2 ships the component as a
 * standalone primitive. Phase 3 will migrate each existing customer
 * page to mount under <CustomerLayout> via a nested <Route>, after
 * we strip the page-local headers that would otherwise duplicate
 * the chrome here.
 */

import React, { useCallback, useEffect, useState } from 'react';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { X } from 'lucide-react';
import { useCustomerAuth } from '../../../context/CustomerAuthContext';
import { StoreMetaProvider } from '../../../context/StoreMetaContext';
import { useStorefrontLocaleSync } from '../../storefront/hooks/useStorefrontLocaleSync';
import FloatingLanguageSwitcher from '../../storefront/components/FloatingLanguageSwitcher';
import useMyCourses from '../hooks/useMyCourses';
import CustomerSidebar from './CustomerSidebar';
import CustomerTopBar from './CustomerTopBar';
import EmailVerificationBanner from './EmailVerificationBanner';
// Reuse the storefront catalog hook from AuthShell so the post-login
// chrome receives the same branding cascade (store > org > fallback)
// that the auth pages already render. This avoids a second API client
// duplicating the lookup logic.
import { useStoreInfo } from '../auth/AuthShell';


/**
 * LocaleSyncBridge — calls `useStorefrontLocaleSync` INSIDE the
 * StoreMetaProvider so the resolver can read the merchant's allowed
 * languages from context. Hooks can't be called above the provider
 * that supplies their data; this child component is the canonical
 * pattern (mirrors PublicStorefrontShell).
 *
 * Why is this needed in the customer area?
 * ----------------------------------------
 * Pre-Step 11, `CustomerAuthContext.useEffect` directly called
 * `i18n.changeLanguage(customer.locale)` whenever the customer logged
 * in. That bypassed the storefront resolver chain — a customer with
 * locale='it' on a store configured with `storefront_languages=['de']`
 * would see Italian even though the merchant's storefront speaks
 * German. The customer's preference is honored ONLY when it's in the
 * store's allowed list (resolver priority 2: customer.locale ∈ list);
 * otherwise the resolver falls through to storeDefault (priority 4).
 *
 * Now the resolver is the single writer. CustomerAuthContext keeps
 * customer.locale on the context object (used by ProfilePage's picker
 * and the resolver's priority chain) but no longer touches i18n
 * directly. Same architectural pattern AuthContext (admin) already
 * follows after the Step 8 path-gate.
 */
function LocaleSyncBridge({ children }) {
  // No props — resolver reads slug + supportedLanguages from context.
  useStorefrontLocaleSync();
  return children;
}


export default function CustomerLayout() {
  const { customer, storeSlug, logout } = useCustomerAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const { t } = useTranslation('customer_portal');

  // Mobile drawer state — toggled by the TopBar hamburger and closed
  // automatically on every route change so the user never has a
  // stale overlay covering the new page.
  const [drawerOpen, setDrawerOpen] = useState(false);

  useEffect(() => { setDrawerOpen(false); }, [location.pathname]);

  // Sidebar gets the "courses" entry only when the customer actually
  // owns at least one. Silent fetch on mount; failures degrade to
  // "no courses" which is identical to a customer who hasn't bought
  // any yet — both correct.
  const { hasAnyCourse, courses } = useMyCourses();
  const coursesBadge = courses.length > 0 ? courses.length : null;

  // Branding cascade for the post-login header. Reads the public
  // catalog (which already runs `branding_service.resolve_for_store`
  // server-side) so the logo follows the Store > Org > fallback
  // priority. Silent on failure — the TopBar falls back to its
  // emoji default if the fetch never resolves.
  const { storeInfo } = useStoreInfo(storeSlug);
  const brandLogoUrl = storeInfo?.logo_url || null;

  const handleLogout = useCallback(() => {
    const slug = storeSlug;
    logout();
    navigate(`/account/login${slug ? `?store=${slug}` : ''}`);
  }, [logout, navigate, storeSlug]);

  return (
    // StoreMetaProvider hydrates the merchant's storefront_languages
    // list (via /api/public/storefront/{slug}/meta + localStorage cache
    // SWR) so the LocaleSyncBridge below can drive i18n with the same
    // resolver chain the public storefront uses. Without this, the
    // customer-area pages would have no way to know the merchant's
    // allowed languages and would fall back to whatever was last set
    // on i18n by another writer.
    //
    // The provider is mounted with `slug={storeSlug}` from
    // CustomerAuthContext (set on login via /customer-auth/login).
    // When storeSlug is null (legacy customers without a slug), the
    // provider stays in 'idle' state, the resolver returns
    // source='pending', and the sync hook leaves i18n at whatever it
    // was — degrades gracefully without crashing.
    <StoreMetaProvider slug={storeSlug}>
      <LocaleSyncBridge>
        <div className="min-h-screen bg-slate-50 flex flex-col">
          <CustomerTopBar
            customer={customer}
            storeName={customer?.org_name || null}
            logoUrl={brandLogoUrl}
            onToggleDrawer={() => setDrawerOpen(o => !o)}
          />

      <div className="flex-1 flex">
        {/* ── Desktop sidebar — always visible at ≥lg ───────────── */}
        <aside className="hidden lg:flex w-60 border-r bg-white sticky top-14 h-[calc(100vh-3.5rem)]">
          <div className="w-full overflow-y-auto">
            <CustomerSidebar
              hasAnyCourse={hasAnyCourse}
              coursesBadge={coursesBadge}
              storeSlug={storeSlug}
              onLogout={handleLogout}
            />
          </div>
        </aside>

        {/* ── Mobile drawer (off-canvas) ────────────────────────── */}
        {drawerOpen && (
          <>
            {/* Backdrop — click to close */}
            <div
              className="lg:hidden fixed inset-0 z-40 bg-black/40"
              onClick={() => setDrawerOpen(false)}
              aria-hidden
            />
            <aside className="lg:hidden fixed top-0 left-0 z-50 w-64 h-screen bg-white border-r shadow-xl">
              <div className="flex items-center justify-between p-3 border-b">
                <span className="font-semibold text-sm text-gray-900">{t('customer_portal:layout.menu')}</span>
                <button
                  type="button"
                  onClick={() => setDrawerOpen(false)}
                  className="p-1 rounded-md hover:bg-gray-100"
                  aria-label={t('customer_portal:layout.closeMenu')}
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
              <CustomerSidebar
                hasAnyCourse={hasAnyCourse}
                coursesBadge={coursesBadge}
                storeSlug={storeSlug}
                onLogout={handleLogout}
                onItemClick={() => setDrawerOpen(false)}
              />
            </aside>
          </>
        )}

        {/* ── Main content area ─────────────────────────────────── */}
        <main className="flex-1 min-w-0">
          <div className="max-w-5xl mx-auto px-4 sm:px-6 py-4 sm:py-6 space-y-4">
            {/* Sticky banner — only renders when email_verified=false. */}
            <EmailVerificationBanner />

            {/* Page-specific content lives here. Phase 3 will mount
                migrated pages (HomePage, OrdersPage, OrderDetailPage,
                CoursesIndexPage, CoursePlayerPage, ProfilePage) under
                a parent <Route element={<CustomerLayout />}>. */}
            <Outlet />
          </div>
        </main>
      </div>
        {/* Floating language switcher — auto-hides on single-language
            stores (MVP-friendly: invisible for merchants with one
            language). On multi-language stores, lets the customer
            switch from any page in their post-login area; the click
            persists via PATCH /customer/me so the choice follows the
            account across devices. */}
        <FloatingLanguageSwitcher />
      </div>
      </LocaleSyncBridge>
    </StoreMetaProvider>
  );
}
