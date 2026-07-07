/**
 * StorefrontHeader — shared top bar for every public storefront surface
 * (/s/:slug catalog, /e/:org_slug/:slug event landing, future /checkout
 * success pages that want the same look).
 *
 * Before this component each page rolled its own header (the catalog
 * page had a rich branded bar with logo + cart + login; the event
 * landing had only a dark hero with the event title). Customers
 * navigating from the landing into the storefront saw a UI change
 * that read as "you're leaving the shop", and there was no way back
 * to the home from the landing other than the footer link.
 *
 * Contract:
 *   <StorefrontHeader
 *     orgSlug={slug}
 *     storeInfo={catalog.store_info}       // logo_url, display_name, brand_color, brand_color_text
 *     orgName={catalog.org_name}
 *     subtitle="Catalogo prodotti"         // optional, below the name
 *     rightSlot={ <button>...</button> }   // optional, renders in the right column
 *   />
 *
 * Logo + name are wrapped in a <Link to={`/s/${orgSlug}`}> so clicking
 * them always takes the customer back to the catalog home, from any
 * page that uses the header.
 *
 * Branding: when store_info.brand_color is set, the bar paints itself
 * with that background and uses store_info.brand_color_text for
 * foreground. Without brand colors it falls back to white + slate-900.
 *
 * Sticky: `top-0` with a z-index so the bar stays visible on scroll.
 */

import React from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import StorefrontLanguageSwitcher from './StorefrontLanguageSwitcher';
import CategoryNav from './CategoryNav';


export default function StorefrontHeader({
  orgSlug,
  storeInfo,
  orgName,
  subtitle,
  rightSlot = null,
  // Logo flexibility refinement — three optional props that drive
  // the rendering shape of the logo + store name. Defaults preserve
  // the pre-refinement look exactly (40px square, store name shown).
  //
  //   logoHeight       'sm' | 'md' | 'lg' resolved to pixel string
  //                    by the caller (StorefrontPage reads it from
  //                    useDesignTokens). Defaults to "40px".
  //   logoFit          'contain' | 'cover' — object-fit value.
  //                    Default 'contain' (respects aspect ratio).
  //   showStoreName    bool — when false, the store name + subtitle
  //                    cluster is omitted. Merchants with a
  //                    self-branded logo (word-mark + symbol baked
  //                    into the image) use this to avoid the visual
  //                    redundancy of seeing the name twice.
  logoHeight = '40px',
  logoFit = 'contain',
  showStoreName = true,
  // Optional: the merchant's `storefront_languages` array (top-level on
  // the catalog response). When provided and ≥2 entries, the language
  // switcher shows up on the right cluster. When missing or 1-entry the
  // switcher self-hides — landings that don't have the list available
  // from their own endpoint just don't show the picker (visitors can
  // always switch from the catalog instead).
  supportedLanguages = null,
  // Phase 7.4 — optional category nav strip rendered BELOW the main
  // bar. When the parent passes a non-empty `categories` array (from
  // useAvailableCategories on the catalog), the strip surfaces one
  // link per category with the current one highlighted. The strip
  // self-hides when 0-1 categories are available AND no custom links
  // are configured.
  categories = null,
  // Phase 8.2 — merchant-configured custom navigation links
  // (catalog.custom_nav_links). When non-empty the strip renders
  // them next to the category pills, on the right side.
  customNavLinks = null,
}) {
  const { t } = useTranslation('storefront');
  const brandBg = storeInfo?.brand_color || null;
  const brandFg = storeInfo?.brand_color_text || (brandBg ? '#ffffff' : null);
  // The header paints over a brand-colored bar when configured — the
  // switcher uses its `header` variant in that case so the select reads
  // legibly against either light or branded backgrounds.
  const switcherVariant = brandBg ? 'header' : 'default';

  return (
    <header
      // Phase 8.3 + Phase 9 — modernized header with design tokens.
      // The `--sf-header-bg-alpha` and `--sf-header-blur` tokens (set
      // on the storefront root by useDesignTokens) drive the
      // transparency + blur strength. Solid/translucent/minimal map to:
      //   solid       → alpha 1     blur 0  (opaque, traditional)
      //   translucent → alpha 0.8   blur 8px (frosted glass, default)
      //   minimal     → alpha 0.55  blur 12px (very transparent + strong blur)
      //
      // The brand color, when set, is the underlying background hue;
      // CSS color-mix with the alpha token gives the blend. When the
      // browser doesn't support color-mix (Safari < 16.4) we fall
      // back to the brand color at full opacity — graceful degrade.
      className="border-b sticky top-0 z-20"
      style={brandBg
        ? {
            color: brandFg,
            // color-mix yields `<brandBg> at alpha%` against transparent.
            // Browsers without color-mix support (Safari < 16.4)
            // ignore the rule and use the next valid declaration —
            // which we approximate via a plain brandBg fallback in
            // the backgroundImage trick: set both, the supported one
            // wins.
            backgroundColor: brandBg,
            background: `color-mix(in srgb, ${brandBg} calc(var(--sf-header-bg-alpha, 1) * 100%), transparent)`,
            backdropFilter: 'blur(var(--sf-header-blur, 8px))',
            WebkitBackdropFilter: 'blur(var(--sf-header-blur, 8px))',
          }
        : {
            // No brand color — white with token-driven alpha.
            background: `rgba(255,255,255, var(--sf-header-bg-alpha, 0.8))`,
            backdropFilter: 'blur(var(--sf-header-blur, 8px))',
            WebkitBackdropFilter: 'blur(var(--sf-header-blur, 8px))',
          }
      }
    >
      <div className="max-w-6xl mx-auto px-4 py-3 sm:py-4 flex items-center justify-between gap-3">
        {/* Logo + name — always a link back to the catalog home.
            Phase 8.3 — added subtle hover lift (group-hover scale on
            logo) + crisper typography. */}
        <Link
          to={`/s/${orgSlug}`}
          className="group flex items-center gap-3 min-w-0 transition-opacity hover:opacity-95"
          aria-label={t('storefront:submitted.backToCatalog')}
        >
          {storeInfo?.logo_url && (
            // Logo flexibility refinement — height + fit driven by
            // design tokens (logo_height / logo_fit).
            //   width: auto                preserves aspect ratio
            //   maxWidth: clamp responsive  bounds the logo on small
            //                              screens so a wide logo
            //                              doesn't eat the whole bar
            //   object-fit: cover|contain  square crop vs aspect-fit
            //
            // The rounded corners + ring only make sense for square
            // crops. With 'contain' we drop them so a wide logo
            // doesn't look like it's clipped by an invisible square.
            <img
              src={storeInfo.logo_url}
              alt=""
              className={`shrink-0 transition-transform group-hover:scale-[1.04] ${
                logoFit === 'cover' ? 'rounded-xl ring-1 ring-black/5' : ''
              }`}
              style={{
                height: logoHeight,
                width: 'auto',
                // Mobile clamp at 45vw (don't let a logo wider than
                // ~half the viewport push the language switcher off
                // screen). Desktop clamp at 280px so a really wide
                // word-mark stays manageable on the bar.
                maxWidth: 'min(45vw, 280px)',
                objectFit: logoFit,
              }}
            />
          )}
          {showStoreName && (
            <div className="min-w-0">
              {/* Modernization (Phase 8.3 + refinement) — tighter
                  tracking on the store name + larger font weight
                  (font-bold → font-extrabold) so the brand name reads
                  as the dominant identifier on the page.
                  tracking-tight (-0.025em) is the modern marketing-page
                  convention (Apple, Linear, Stripe).
                  Wrapped in `showStoreName` so merchants with a
                  self-branded logo can hide the redundant text and
                  let the logo carry the whole identity. */}
              <h1
                className="text-lg sm:text-xl font-extrabold truncate tracking-tight"
                style={brandFg ? { color: brandFg } : { color: '#0a0a0a' }}
              >
                {storeInfo?.display_name || orgName || ''}
              </h1>
              {subtitle && (
                // Subtitle gets a slightly stronger contrast (0.65 was
                // 0.7) and tighter font (text-[11px] sm:text-xs) so the
                // hierarchy between name + subtitle reads cleanly.
                <p
                  className="text-[11px] sm:text-xs truncate font-medium"
                  style={{ opacity: 0.65, letterSpacing: '0.01em' }}
                >
                  {subtitle}
                </p>
              )}
            </div>
          )}
        </Link>

        {/* Right cluster — language switcher (when ≥2 langs configured)
            + the optional caller-supplied slot (cart + login on the
            catalog, "Torna al catalogo" on sub-pages, etc.).
            The switcher self-hides on single-language stores so this
            cluster stays clean for merchants who haven't enabled i18n.
            Phase 8.3 — gap-2.5 (was gap-3) tightens the cluster so the
            cart pill (Phase 7 cleanup) reads as a single visual block
            with the support icons rather than floating in air. */}
        <div className="flex items-center gap-2.5 shrink-0">
          {/* AN2 — il ponte verso il marketplace: dentro uno store il
              visitatore non è più intrappolato. Discreto (lo store
              resta il protagonista), sparisce sugli schermi stretti
              dove il logo dello store ha la priorità. */}
          <Link
            to="/"
            className="hidden sm:inline-flex items-center gap-1 text-[11px] font-medium whitespace-nowrap opacity-60 hover:opacity-100 transition-opacity"
            style={brandFg ? { color: brandFg } : { color: '#0a0a0a' }}
            title="Aurya"
          >
            ✦ {t('storefront:partOfAurya', { defaultValue: 'Parte di Aurya' })}
          </Link>
          <StorefrontLanguageSwitcher
            storeSlug={orgSlug}
            supportedLanguages={supportedLanguages}
            variant={switcherVariant}
          />
          {rightSlot && (
            <div className="flex items-center gap-3 shrink-0">
              {rightSlot}
            </div>
          )}
        </div>
      </div>

      {/* Phase 7.4 — category nav strip. Sits inside the same <header>
          element so the sticky-positioning anchors the whole bar
          (main row + nav) to the top of the viewport on scroll.
          Self-hides when no categories are passed AND no custom
          links — see CategoryNav for the visibility rules.
          Phase 8.2 — also carries the merchant's custom_nav_links. */}
      <CategoryNav
        orgSlug={orgSlug}
        categories={categories}
        storeInfo={storeInfo}
        customLinks={customNavLinks}
      />
    </header>
  );
}
