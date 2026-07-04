/**
 * useStorefrontLocaleSync — apply the resolved storefront locale to the
 * shared i18next instance.
 *
 * Mounted by storefront-side surfaces:
 *   - StorefrontPage (`/s/:slug`)
 *   - Customer auth pages (`/account/login`, `/account/signup`, …)
 *   - Customer portal layout (`/account/*` post-login)
 *   - 12 landing pages (via PublicStorefrontShell — Step 4)
 *
 * Why a separate hook (not just calling i18n.changeLanguage inline)
 * -----------------------------------------------------------------
 * 1. Centralises the "resolved locale → i18n.language" wiring so future
 *    callers don't reinvent it.
 * 2. Keeps the side-effect (i18n mutation) inside a useEffect so it
 *    runs at the right point in the React lifecycle and is skipped
 *    when the locale didn't actually change (i18next no-ops a same-
 *    language change anyway, but cheap correctness).
 * 3. Pairs symmetrically with the existing admin-side
 *    `AuthContext` → `i18n.changeLanguage(user.locale)` effect:
 *      - admin layouts: AuthContext drives i18n
 *      - storefront layouts: this hook drives i18n
 *    The "last context to mount wins" because each effect fires when
 *    the relevant component mounts, and unmounted contexts never write.
 *    No conflict, no flicker.
 *
 * 'pending' source — the IT-flicker fix
 * --------------------------------------
 * Before Step 3, `useStorefrontLocale` collapsed to FALLBACK_LOCALE='it'
 * whenever the merchant list was unknown (e.g. catalog still loading on
 * back-nav, or a landing page that lacks the list). This effect would
 * then call `changeLanguage('it')` for a frame, producing a visible IT
 * flash even on stores configured exclusively in DE/EN/FR.
 *
 * Now the resolver returns `source='pending'` in that scenario and we
 * skip the change call entirely — i18n keeps whatever locale the
 * previous render left it in (typically the correct one, since the
 * catalog usually mounts the locale-sync once at startup). When the
 * supported list eventually arrives (catalog response, /meta response),
 * the hook re-runs with a real locale and the changeLanguage fires
 * once with the correct value.
 *
 * Returns the resolved locale string for callers that want to render
 * locale-aware UI (e.g. the language switcher's active state). Returns
 * null + source='pending' during the unknown-supported-list window;
 * consumers must handle that state if they render an "active language"
 * indicator.
 */

import { useEffect } from 'react';
import i18n from '../../../i18n';
import { useStorefrontLocale } from '../../../hooks/useStorefrontLocale';


export function useStorefrontLocaleSync({ storeSlug, supportedLanguages } = {}) {
  const { locale, source } = useStorefrontLocale({ storeSlug, supportedLanguages });

  useEffect(() => {
    // Skip during 'pending' — leaves i18n at its previous value rather
    // than flickering to the fallback. This is the back-nav fix.
    if (source === 'pending' || !locale) return;
    if (i18n.language === locale) return;
    i18n.changeLanguage(locale);
  }, [locale, source]);

  return { locale, source };
}
