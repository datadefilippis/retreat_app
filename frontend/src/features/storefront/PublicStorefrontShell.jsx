/**
 * PublicStorefrontShell — route-level wrapper for every public surface.
 *
 * Mounts the building blocks every storefront page needs to render
 * with the correct locale and store branding, so individual landing
 * pages don't have to repeat the wiring:
 *
 *   ┌─ <StoreMetaProvider slug={...}>
 *   │    Fetches /api/public/storefront/{slug}/meta once per slug,
 *   │    caches in localStorage, exposes via useStoreMeta() context.
 *   │
 *   ├──── <LocaleSyncBridge>
 *   │       Calls useStorefrontLocaleSync() which now reads the
 *   │       storefrontLanguages list from the context — drives
 *   │       i18n.changeLanguage() with the resolver's chain.
 *   │       During the loading window the resolver returns
 *   │       source='pending' and the sync hook skips its
 *   │       changeLanguage call, so i18n stays at the previous
 *   │       value (fix for the IT-flicker on back-navigation).
 *   │
 *   └────── {children}        ← the actual landing page
 *
 * Slug resolution priority (first match wins)
 * -------------------------------------------
 *   1. Explicit `slug` prop. Used by token-routes (TicketLanding,
 *      BookingLanding, DownloadLanding, ReservationConfirmation) where
 *      the slug isn't in the URL — the page passes it imperatively
 *      AFTER fetching the payload (which carries `store_slug`).
 *   2. URL param specified via `slugParamName`. Default 'org_slug'
 *      matches /e, /p, /co, /r, /ph, /dg routes. The catalog route
 *      /s/:slug must override to 'slug'.
 *   3. Fallback to `slug` URL param (catches the catalog without the
 *      override prop too — safety net).
 *   4. null — provider stays in 'idle' state, no fetch, children
 *      render normally with whatever locale i18n has.
 *
 * Token-based routes (/t/:token, /b/:token, /d/:access_token, /rsv/:token)
 * intentionally do NOT use the shell at the route level. They render
 * their own <PublicStorefrontShell slug={data.store_slug}> AFTER the
 * payload arrives, so the provider mounts with the right slug. This
 * mirrors how AuthShell already does it for customer auth pages.
 *
 * Backward compatibility
 * ----------------------
 * The shell does NOT remove the existing inline `useStorefrontLocaleSync`
 * call in StorefrontPage / CheckoutResultPage / AuthShell. Those keep
 * working unchanged because:
 *   • They pass `supportedLanguages` explicitly → resolver gives prop
 *     priority over the context (Step 3).
 *   • Mounting the sync hook twice in the same tree is idempotent —
 *     i18next no-ops same-language calls.
 *
 * Future cleanup (Step 7) can collapse those inline calls once the
 * shell has been live for a release cycle.
 */

import React from 'react';
import { useParams } from 'react-router-dom';
import { StoreMetaProvider } from '../../context/StoreMetaContext';
import { useStorefrontLocaleSync } from './hooks/useStorefrontLocaleSync';
import FloatingLanguageSwitcher from './components/FloatingLanguageSwitcher';


// Tiny child component — its sole job is to call the sync hook INSIDE
// the StoreMetaProvider so the resolver can read the context. Hooks
// can't be called above the provider that supplies their data, so this
// "bridge" pattern is the canonical way to wire context-aware effects
// at the wrapper level.
function LocaleSyncBridge({ children }) {
  // No props — the hook reads everything it needs from context now.
  useStorefrontLocaleSync();
  return children;
}


export default function PublicStorefrontShell({
  slug,
  slugParamName = 'org_slug',
  // Set to false on pages that already render their own switcher (e.g.
  // the catalog has one in StorefrontHeader). Default true: every other
  // surface gets the floating switcher gratis. Step 7 may flip this
  // around once the inline switcher is removed in favor of the floating
  // one app-wide.
  showFloatingSwitcher = true,
  children,
}) {
  const params = useParams();
  // Resolve the slug from the explicit prop OR the configured URL
  // param OR the catalog `:slug` fallback. null is a valid result —
  // the provider just stays idle and children render unchanged.
  const resolvedSlug = slug || params[slugParamName] || params.slug || null;

  return (
    <StoreMetaProvider slug={resolvedSlug}>
      <LocaleSyncBridge>
        {children}
        {/* The floating switcher reads `useStoreMeta()` from the
            provider above and self-hides on single-language stores or
            during loading, so it's safe to render unconditionally.
            Sits at z=30: above content, below modals (which use 50+). */}
        {showFloatingSwitcher && <FloatingLanguageSwitcher />}
      </LocaleSyncBridge>
    </StoreMetaProvider>
  );
}
