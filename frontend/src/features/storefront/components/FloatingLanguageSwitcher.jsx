/**
 * FloatingLanguageSwitcher — discreet always-visible language picker.
 *
 * Mounted by `PublicStorefrontShell` so every public storefront surface
 * (catalog + 12 landings) gets a language switcher automatically — no
 * per-page wiring required. Anchored bottom-right at z-index 30 so it
 * stays out of the way of:
 *   - Sticky headers (top of viewport, z=20)
 *   - Cart drawers (typically left or center, z=40+)
 *   - Modals (full overlay, z=50+)
 *
 * Auto-hide rules — the switcher renders nothing when:
 *   - The context is in a non-ready state (idle/loading/error). We don't
 *     want to flash a 1-language placeholder during loading.
 *   - The merchant has fewer than 2 supported languages (MVP single-
 *     language stores: no choice to make, no UI noise).
 *   - The store_slug is unknown (token-based pages before payload arrives).
 *
 * Behavioural contract — same as the inline StorefrontLanguageSwitcher:
 *   1. Click a language → `i18n.changeLanguage` immediately (UI updates).
 *   2. Persist via `persistStorefrontLocale(slug, lang)` so guests get
 *      the same language on next visit to this store.
 *   3. If a customer is logged in → `customerPortalAPI.updateProfile`
 *      with `{locale: lang}` so the choice follows them across devices.
 *      Errors are swallowed (the local change already happened, server
 *      sync is best-effort).
 *
 * Visual: pill button with the language code (uppercase) + chevron. On
 * click expands to a small popover listing the supported languages. The
 * design intentionally avoids flag emojis (🇩🇪 vs 🇨🇭 vs 🇦🇹 — many
 * countries share German, picking one is a political minefield) and
 * uses the language autonyms ("Deutsch", "English") instead.
 */

import React, { useState, useRef, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useStoreMeta } from '../../../hooks/useStoreMeta';
import { useCustomerAuth } from '../../../context/CustomerAuthContext';
import {
  APP_SUPPORTED_LOCALES,
  persistStorefrontLocale,
} from '../../../hooks/useStorefrontLocale';
import { customerPortalAPI } from '../../../api/customerPortal';


/**
 * Filter the merchant's allowed list down to languages the app
 * actually has translations for. Defensive: if the upstream config
 * has drifted (rare, but possible after a partial migration), we
 * silently drop unsupported entries rather than rendering a broken
 * picker.
 */
function _allowed(supportedLanguages) {
  if (!Array.isArray(supportedLanguages)) return [];
  return supportedLanguages.filter((l) => APP_SUPPORTED_LOCALES.includes(l));
}


export default function FloatingLanguageSwitcher() {
  const { t, i18n } = useTranslation('common');
  const meta = useStoreMeta();
  const { isCustomerAuthenticated, updateCustomer } = useCustomerAuth();
  const [open, setOpen] = useState(false);
  const popoverRef = useRef(null);

  // Click-outside-to-close: small enough that we wire it inline rather
  // than pulling in a portal/floating-ui library. The handler is mounted
  // only while the popover is open, so the cost is bounded.
  useEffect(() => {
    if (!open) return;
    const onDocClick = (e) => {
      if (popoverRef.current && !popoverRef.current.contains(e.target)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', onDocClick);
    return () => document.removeEventListener('mousedown', onDocClick);
  }, [open]);

  // Close popover on Escape too — standard accessibility expectation.
  useEffect(() => {
    if (!open) return;
    const onKey = (e) => { if (e.key === 'Escape') setOpen(false); };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [open]);

  // Render gates — see the JSDoc above for rationale.
  if (meta.status !== 'ready') return null;
  const allowed = _allowed(meta.storefrontLanguages);
  if (allowed.length < 2) return null;
  if (!meta.slug) return null;

  // Current effective language clamped to the allowed list. If i18n
  // somehow drifted outside the merchant's set (e.g. customer.locale
  // brought in from another store), we display the first allowed entry
  // as the "current" rather than an impossible value.
  const current = allowed.includes(i18n.language) ? i18n.language : allowed[0];

  const handlePick = async (next) => {
    setOpen(false);
    if (!next || next === current || !allowed.includes(next)) return;

    // 1. Immediate UI change.
    i18n.changeLanguage(next);

    // 2. Per-store guest cache.
    persistStorefrontLocale(meta.slug, next);

    // 3. Logged-in customer → server-side preference too.
    if (isCustomerAuthenticated) {
      try {
        await customerPortalAPI.updateProfile({ locale: next });
        updateCustomer({ locale: next });
      } catch {
        // Silent — local change is the contract; server sync is opportunistic.
      }
    }
  };

  return (
    <div
      ref={popoverRef}
      className="fixed bottom-4 right-4 z-30"
    >
      {/* Anchor button — always visible while the switcher is mounted.
          Compact 36px height matches typical floating-action button
          conventions without dominating the viewport. */}
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label={t('common:languageSwitcher.ariaLabel')}
        className="inline-flex items-center gap-1.5 rounded-full bg-white border border-gray-300 shadow-md px-3 py-2 text-xs font-semibold text-gray-800 hover:bg-gray-50 hover:border-gray-400 focus:outline-none focus:ring-2 focus:ring-gray-400 transition-colors"
      >
        <span className="uppercase tabular-nums">{current}</span>
        <svg
          className={`h-3 w-3 text-gray-500 transition-transform ${open ? 'rotate-180' : ''}`}
          viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden
        >
          <path d="M3 5l3 3 3-3" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </button>

      {/* Popover — lists allowed languages with autonyms.
          Anchors above the button (slides up) so it doesn't go below
          the viewport on phones. Closes on outside click or Escape. */}
      {open && (
        <ul
          role="listbox"
          aria-label={t('common:languageSwitcher.label')}
          className="absolute right-0 bottom-full mb-2 min-w-[140px] rounded-lg bg-white border border-gray-200 shadow-lg overflow-hidden"
        >
          {allowed.map((loc) => {
            const selected = loc === current;
            return (
              <li key={loc} role="option" aria-selected={selected}>
                <button
                  type="button"
                  onClick={() => handlePick(loc)}
                  className={`w-full flex items-center gap-2 px-3 py-2 text-left text-sm transition-colors ${
                    selected
                      ? 'bg-[var(--sf-accent,#111827)] text-[var(--sf-accent-fg,#ffffff)] font-semibold'
                      : 'text-gray-800 hover:bg-gray-100'
                  }`}
                >
                  <span className="text-[10px] uppercase tabular-nums w-6 shrink-0 opacity-70">
                    {loc}
                  </span>
                  <span className="flex-1 truncate">
                    {t(`common:language.${loc}`)}
                  </span>
                  {selected && (
                    <svg className="h-3.5 w-3.5 shrink-0" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
                      <path d="M3 8l4 4 6-7" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  )}
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
