/**
 * AuthShell — shared chrome for unauthenticated customer pages.
 *
 * Phase 5 of the customer area refactor. Extracted verbatim from
 * CustomerPortalPages.js so the visual identity stays bit-identical
 * across login / signup / forgot-password / reset-password /
 * verify-email. Now reusable independently — each auth page imports
 * `AuthShell` (default) and the tiny `useStoreInfo` hook (named).
 *
 * Layout:
 *   ┌─ Branded header (storefront logo + name, when slug is known) ┐
 *   ├─ Vertical centered card (auth form lives here) ───────────────┤
 *   └─ Brand-colored gradient background ───────────────────────────┘
 *
 * Per-store branding is best-effort: we look up `store_info.brand_color`
 * + `logo_url` via the catalog API. When the slug is missing or the
 * lookup fails, we fall back to a neutral slate gradient — never block
 * the form from rendering.
 *
 * Note: this file is JSX-only (no business logic). The form components
 * own their own state. AuthShell is purely presentational.
 */

import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { storefrontAPI } from '../../../api/storefront';
import { useStorefrontLocaleSync } from '../../storefront/hooks/useStorefrontLocaleSync';


/**
 * useStoreInfo — fetches the public storefront catalog to extract
 * branding (logo + brand color + org name) AND `storefront_languages`.
 *
 * The languages array is needed by the AuthShell-mounted
 * `useStorefrontLocaleSync` hook so customer auth pages (login,
 * signup, reset, verify) speak the same language the visitor would
 * have seen on the storefront — without each page wiring the
 * language plumbing manually.
 *
 * Silent on failure — auth pages must never block on a flaky catalog
 * fetch. If the lookup fails, the consumer falls back to neutral copy.
 */
export function useStoreInfo(slug) {
  const [storeInfo, setStoreInfo] = useState(null);
  const [orgName, setOrgName] = useState('');
  const [storefrontLanguages, setStorefrontLanguages] = useState(undefined);

  useEffect(() => {
    if (!slug) return;
    let cancelled = false;
    storefrontAPI.getCatalog(slug)
      .then(res => {
        if (cancelled) return;
        setStoreInfo(res.data?.store_info || null);
        setOrgName(res.data?.org_name || '');
        setStorefrontLanguages(res.data?.storefront_languages);
      })
      .catch(() => {}); // silent — fallback to generic branding
    return () => { cancelled = true; };
  }, [slug]);

  return { storeInfo, orgName, storefrontLanguages };
}


export default function AuthShell({ children, storeInfo, orgName, slug, storefrontLanguages }) {
  // Apply the storefront locale to i18n.changeLanguage. AuthShell is
  // mounted by every customer auth page, so threading the sync through
  // the shell guarantees login/signup/reset/verify all speak the right
  // language without each page wiring it manually.
  useStorefrontLocaleSync({
    storeSlug: slug,
    supportedLanguages: storefrontLanguages,
  });

  const brandColor = storeInfo?.brand_color;
  const brandText = storeInfo?.brand_color_text || '#ffffff';
  const logoUrl = storeInfo?.logo_url;
  const shopName = orgName || '';
  const shopLink = slug ? `/s/${slug}` : null;

  return (
    <div
      className="min-h-screen flex flex-col"
      style={brandColor
        ? { background: `linear-gradient(135deg, ${brandColor}11 0%, ${brandColor}22 100%)` }
        : { background: 'linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%)' }
      }
    >
      {/* Store header — matches storefront header, clickable to go back */}
      {slug && (
        <header
          className="border-b sticky top-0 z-10"
          style={brandColor
            ? { backgroundColor: brandColor, color: brandText }
            : { backgroundColor: 'white' }
          }
        >
          <div className="max-w-6xl mx-auto px-4 py-3 flex items-center">
            <Link to={shopLink} className="flex items-center gap-3 hover:opacity-80 transition-opacity">
              {logoUrl && (
                <img src={logoUrl} alt="" className="h-9 w-9 rounded-lg object-cover" />
              )}
              <span
                className="text-lg font-bold"
                style={{ color: brandColor ? brandText : '#1a1a1a' }}
              >
                {shopName}
              </span>
            </Link>
          </div>
        </header>
      )}

      {/* Centered auth card */}
      <div className="flex-1 flex items-center justify-center p-4">
        <div className="w-full max-w-md">
          {/* Shop name + "by AFianco" above the card */}
          <div className="flex flex-col items-center mb-5 gap-0.5">
            {shopName ? (
              <>
                <span
                  className="font-heading text-xl font-bold tracking-tight"
                  style={brandColor ? { color: brandColor } : undefined}
                >
                  {shopName}
                </span>
                <span className="text-[11px] text-muted-foreground">by AFianco</span>
              </>
            ) : (
              <span className="font-heading text-xl font-bold tracking-tight">AFianco</span>
            )}
          </div>
          {children}
        </div>
      </div>
    </div>
  );
}
