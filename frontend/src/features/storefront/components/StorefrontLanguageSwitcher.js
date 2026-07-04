/**
 * StorefrontLanguageSwitcher — language picker for public storefront surfaces.
 *
 * Mounted by storefront-side surfaces that want to expose a manual locale
 * change to visitors:
 *   - StorefrontHeader (used by /s/:slug, /e/:org_slug/:slug, /p/:org_slug/:slug)
 *   - Customer auth pages (login / signup)
 *   - Standalone landing pages that render their own header
 *
 * Behaviour
 * ---------
 * The switcher renders the merchant's allowed languages (intersected with
 * what the AFianco i18n stack actually has translations for) as a small
 * native `<select>`. On change it does, in order:
 *
 *   1. `i18n.changeLanguage(next)` — applies the new locale immediately so
 *      the current page re-renders without a refresh.
 *   2. `persistStorefrontLocale(storeSlug, next)` — writes a per-store key
 *      to localStorage so the same visitor lands in the same language next
 *      time on this storefront.
 *   3. If the visitor is a logged-in customer → fire-and-forget
 *      `customerPortalAPI.updateProfile({ locale: next })` and merge the
 *      new value into context via `updateCustomer({ locale: next })`. The
 *      backend whitelist accepts {it,en,de,fr}; a tampered code is rejected
 *      400 (we silently swallow errors here — the local UI already changed
 *      via step 1, so the worst case is the choice doesn't survive logout).
 *
 * Hidden when the merchant only enabled one language, since a 1-option
 * picker is just visual noise.
 *
 * Accessibility
 * -------------
 * The native `<select>` exposes a real keyboard-friendly menu and an
 * `aria-label` that reads "Change language" in the current locale. The
 * compact 32px height matches button heights used elsewhere in the
 * StorefrontHeader so layouts stay aligned.
 */

import React from 'react';
import { useTranslation } from 'react-i18next';
import { useCustomerAuth } from '../../../context/CustomerAuthContext';
import {
  APP_SUPPORTED_LOCALES,
  persistStorefrontLocale,
} from '../../../hooks/useStorefrontLocale';
import { customerPortalAPI } from '../../../api/customerPortal';


// Filter the merchant's allowed list down to languages the app actually
// has translations for. Defensive: if `supportedLanguages` is missing or
// empty (catalog still loading) we render nothing so the header stays
// stable until the data arrives.
function _allowed(supportedLanguages) {
  if (!Array.isArray(supportedLanguages) || supportedLanguages.length === 0) return [];
  return supportedLanguages.filter((l) => APP_SUPPORTED_LOCALES.includes(l));
}


export default function StorefrontLanguageSwitcher({
  storeSlug,
  supportedLanguages,
  className = '',
  variant = 'default',  // 'default' | 'header' (header gets transparent bg)
}) {
  const { t, i18n } = useTranslation('common');
  const { isCustomerAuthenticated, updateCustomer } = useCustomerAuth();

  const allowed = _allowed(supportedLanguages);
  // Hide when there's only one (or zero) language — no choice to make.
  if (allowed.length < 2) return null;

  // Current language clamped to the allowed list. If i18n.language somehow
  // drifted outside the merchant's set (e.g. customer.locale carried over
  // from another store) we pick the first allowed entry so the select
  // always shows a valid option rather than a phantom one.
  const current = allowed.includes(i18n.language) ? i18n.language : allowed[0];

  const handleChange = async (e) => {
    const next = e.target.value;
    if (!next || next === current || !allowed.includes(next)) return;

    // 1. Immediate UI change — i18next no-ops on same-language requests
    //    and the whole React tree re-renders against the new bundle.
    i18n.changeLanguage(next);

    // 2. Persist for this store's guest cache.
    persistStorefrontLocale(storeSlug, next);

    // 3. Logged-in customer → save preference server-side too so it
    //    follows the account across devices. Errors are non-fatal: the
    //    local change already happened, and the next /me on cold-start
    //    will reveal any drift if the request truly failed.
    if (isCustomerAuthenticated) {
      try {
        await customerPortalAPI.updateProfile({ locale: next });
        updateCustomer({ locale: next });
      } catch {
        // Silent — the immediate-UX change in step 1 is the contract.
      }
    }
  };

  const isHeader = variant === 'header';
  const baseCls = 'rounded-md border text-xs font-medium px-2 py-1.5 h-8 cursor-pointer focus:outline-none focus:ring-2 focus:ring-gray-300 transition-colors';
  const palette = isHeader
    ? 'bg-white/10 border-white/30 text-white hover:bg-white/20'
    : 'bg-white border-gray-300 text-gray-800 hover:border-gray-500';

  return (
    <select
      value={current}
      onChange={handleChange}
      aria-label={t('common:languageSwitcher.ariaLabel')}
      className={`${baseCls} ${palette} ${className}`}
    >
      {allowed.map((loc) => (
        <option key={loc} value={loc} className="text-gray-900">
          {t(`common:language.${loc}`)}
        </option>
      ))}
    </select>
  );
}
