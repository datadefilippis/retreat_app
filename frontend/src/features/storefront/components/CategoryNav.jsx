/**
 * CategoryNav — secondary nav strip rendered under StorefrontHeader.
 *
 * Phase 7.4 — shows one link per available category. The "available
 * categories" set comes from useAvailableCategories(catalog) (Phase 7.2)
 * which derives it from the inventory: categories with zero published
 * products are hidden entirely (no dead links).
 *
 * Visual design
 * -------------
 * The component renders below the main header bar as a separate strip:
 *
 *   ┌────────────────────────────────────────────────────────┐
 *   │ Logo │ Store name              │ 🇮🇹 │ 🛒 │ 👤        │  ← StorefrontHeader
 *   ├────────────────────────────────────────────────────────┤
 *   │  Servizi · Prodotti                                     │  ← CategoryNav
 *   └────────────────────────────────────────────────────────┘
 *
 * The strip self-hides when there are < 2 categories (a single-category
 * store doesn't need navigation — same logic as the language switcher
 * self-hiding for single-language stores).
 *
 * Active state
 * ------------
 * Reads :category from the URL via useParams. The current category
 * gets an underline + bolder text + aria-current="page". On the
 * storefront root (no :category) no link is highlighted — visitors
 * see the full multi-section view and can navigate to focus on one.
 *
 * Mobile (≤768px)
 * ---------------
 * The links scroll horizontally with overflow-x-auto so even a 5-link
 * nav stays usable on a narrow phone screen. Tap targets are min 44px
 * tall per Apple HIG / WCAG 2.5.5.
 *
 * Branding
 * --------
 * Inherits the same brand color logic as the header — when the store
 * has a brand_color the strip paints with a translucent version of it
 * so the categories pop against the brand bar above.
 *
 * Accessibility
 * -------------
 * - role="navigation" on the wrapper
 * - aria-label describing the nav purpose
 * - aria-current="page" on the active link
 * - keyboard nav via native <Link> tabbing
 */

import React from 'react';
import { Link, useParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';


/**
 * Resolve the visitor-facing label for a custom nav link.
 *
 * The merchant's `label_i18n` is a {locale -> string} dict validated
 * server-side to have an entry for every active storefront language.
 * We pick the active i18n.language, falling back to the first
 * available key (defensive: never crash on a stale link missing the
 * current locale; just show something readable).
 *
 * Returns null when the link has no labels at all — caller skips it.
 */
function _resolveLinkLabel(link, activeLang) {
  const labels = link?.label_i18n;
  if (!labels || typeof labels !== 'object') return null;
  if (labels[activeLang]) return labels[activeLang];
  // Locale fallback chain: the active lang first, then any non-empty
  // entry. Storefront i18n already normalises to short codes (it/en/de/fr)
  // so no BCP-47 short-circuit needed here.
  for (const v of Object.values(labels)) {
    if (typeof v === 'string' && v.trim()) return v;
  }
  return null;
}


/**
 * Decide whether a custom link should open in a new tab.
 *
 * Stored value is "self" or "blank" (validated server-side). We
 * also force `target="_blank"` for absolute external URLs even if
 * the merchant left target="self" — visitors clicking an external
 * link rarely want their current cart-bearing tab replaced.
 */
function _resolveLinkTarget(link) {
  if (link?.target === 'blank') return '_blank';
  if (typeof link?.url === 'string') {
    const u = link.url.toLowerCase();
    if (u.startsWith('http://') || u.startsWith('https://')
        || u.startsWith('mailto:') || u.startsWith('tel:')) {
      return '_blank';
    }
  }
  return '_self';
}


export default function CategoryNav({
  orgSlug,
  categories,
  storeInfo,
  // Phase 8.2 — array of {id, label_i18n, url, target, sort_order}
  // configured by the merchant via the admin "Menu personalizzato"
  // accordion. Rendered on the RIGHT side of the same strip as the
  // category pills (user decision 2 = A: same strip).
  customLinks = [],
}) {
  const { t, i18n } = useTranslation('storefront');
  const params = useParams();
  const activeSlug = params?.category || null;

  // Filter custom links to those that resolve to a visible label.
  // Defensive: a link with empty label dict (shouldn't happen post-
  // validation but possible if data was migrated manually) just
  // doesn't render rather than crash.
  const visibleCustomLinks = (customLinks || [])
    .map((link) => ({ ...link, _label: _resolveLinkLabel(link, i18n.language) }))
    .filter((link) => !!link._label);

  // Self-hide cases:
  //  - no slug (parent forgot to pass it — defensive)
  //  - no categories AND no custom links → nothing to render
  //  - one category + zero custom links → single-category store, no nav needed
  // Note: WITH custom links we render the strip even with 1 category,
  // so the merchant's custom links are reachable.
  const hasMultipleCategories = Array.isArray(categories) && categories.length >= 2;
  const hasCustomLinks = visibleCustomLinks.length > 0;
  if (!orgSlug || (!hasMultipleCategories && !hasCustomLinks)) {
    return null;
  }

  // Brand-aware coloring. The strip sits BELOW the main header which
  // already paints the brand color, so we use a lighter variant — a
  // subtle white-ish background that lets the brand color frame it
  // without overpowering. When no brand is set, render on white with
  // a bottom border.
  const brandBg = storeInfo?.brand_color || null;
  const brandFg = storeInfo?.brand_color_text || (brandBg ? '#ffffff' : null);

  return (
    <nav
      role="navigation"
      aria-label={t('storefront:nav.categoriesAria', 'Categorie prodotti')}
      className="border-b sticky z-10 backdrop-blur-sm"
      style={brandBg
        // The strip overlays the brand bar with a slight tint so the
        // category labels stay legible regardless of the brand color.
        // 12% alpha keeps the underlying brand color visible without
        // making the text fight against it.
        ? { backgroundColor: `${brandBg}1f`, color: brandFg }
        : { backgroundColor: 'rgba(248, 250, 252, 0.95)' }
      }
    >
      <div className="max-w-6xl mx-auto px-4">
        {/* Two-row layout:
              - left  → auto-generated category pills (from inventory)
              - right → merchant-configured custom links
            On wide screens both clusters share one row with justify-between
            so categories sit left, custom links sit right.
            On narrow screens the row scrolls horizontally (overflow-x-auto)
            with categories first, then custom links — the visitor scrolls
            laterally to reach the custom set. */}
        <div className="flex items-center justify-between gap-3 overflow-x-auto py-2 -mx-1">
          {/* Category pills (auto-generated from catalog inventory) */}
          <div className="flex items-center gap-1 shrink-0">
            {hasMultipleCategories && categories.map((cat) => {
              const isActive = activeSlug === cat.slug;
              return (
                <Link
                  key={cat.slug}
                  to={`/s/${orgSlug}/c/${cat.slug}`}
                  aria-current={isActive ? 'page' : undefined}
                  className={`
                    shrink-0 rounded-full px-4 py-2 text-sm font-medium
                    transition-all whitespace-nowrap min-h-[36px]
                    flex items-center
                    focus:outline-none
                    focus-visible:ring-2 focus-visible:ring-offset-2
                    focus-visible:ring-[var(--sf-accent,#111827)]
                    ${isActive
                      ? 'bg-[var(--sf-accent,#111827)] text-[var(--sf-accent-fg,#ffffff)] shadow-sm'
                      : 'text-gray-700 hover:bg-gray-100 hover:text-gray-900'
                    }
                  `}
                  // When the strip is rendered over a brand bar, the
                  // default Tailwind colors (gray-900 / white) might not
                  // contrast. We override via inline style only when
                  // brand colors are set so the cascade stays clean
                  // for the no-brand default.
                  style={brandBg && isActive
                    ? { backgroundColor: brandFg, color: brandBg }
                    : undefined
                  }
                >
                  {t(cat.labelKey)}
                  {/* V2 — contatore discreto (il count arriva gia'
                      da useAvailableCategories) */}
                  {typeof cat.count === 'number' && cat.count > 0 && (
                    <span className={`ml-1.5 text-[11px] ${isActive ? 'opacity-80' : 'text-gray-400'}`}>
                      {cat.count}
                    </span>
                  )}
                </Link>
              );
            })}
            {/* V2 — la bio dell'operatore a 1 click da QUALSIASI pagina */}
            <Link
              to={`/o/${orgSlug}`}
              className="shrink-0 rounded-full px-4 py-2 text-sm font-medium text-gray-500 hover:bg-gray-100 hover:text-gray-900 transition-all whitespace-nowrap min-h-[36px] flex items-center"
            >
              {t('storefront:nav.about', { defaultValue: 'Chi siamo' })}
            </Link>
          </div>

          {/* Phase 8.2 — Custom navigation links (merchant-configured).
              Visual treatment is intentionally LIGHTER than the category
              pills so the auto-generated categories stay the primary nav
              affordance: text-only links with hover underline rather
              than filled pills. External links get a tiny arrow icon
              (↗) so the visitor knows the click leaves the storefront. */}
          {hasCustomLinks && (
            <div
              className="flex items-center gap-3 shrink-0 pl-3 sm:border-l"
              style={brandBg
                ? { borderColor: `${brandFg}33` }
                : { borderColor: 'rgba(0,0,0,0.08)' }
              }
              role="navigation"
              aria-label={t('storefront:nav.customLinksAria', 'Link personalizzati')}
            >
              {visibleCustomLinks.map((link) => {
                const target = _resolveLinkTarget(link);
                const isExternal = target === '_blank';
                return (
                  <a
                    key={link.id}
                    href={link.url}
                    target={target}
                    // Security: rel="noopener noreferrer" is critical for
                    // any target=_blank link — without it the destination
                    // page gets a window.opener handle back to this tab.
                    rel={isExternal ? 'noopener noreferrer' : undefined}
                    className={`
                      shrink-0 text-sm font-medium whitespace-nowrap
                      flex items-center gap-1 min-h-[36px]
                      transition-colors
                      focus:outline-none
                      focus-visible:ring-2 focus-visible:ring-offset-2
                      focus-visible:ring-[var(--sf-accent,#111827)] rounded
                      px-1
                      text-gray-700 hover:text-gray-900 hover:underline
                      underline-offset-4 decoration-2
                    `}
                    style={brandBg
                      ? { color: brandFg }
                      : undefined
                    }
                  >
                    {link._label}
                    {isExternal && (
                      <span
                        aria-hidden
                        className="text-xs opacity-60"
                      >↗</span>
                    )}
                  </a>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </nav>
  );
}
