/**
 * Storefront categories — single source of truth.
 *
 * Phase 7 of the storefront redesign introduces per-category browsing.
 * Each category corresponds to one or more `item_type` values from the
 * backend canonical list (see backend/models/product_types.py).
 *
 * Design decisions captured here
 * ------------------------------
 *
 *  1. URL slugs are FIXED Italian — they DON'T change with the active
 *     locale. Rationale:
 *       - URLs stay stable across sessions / shares / bookmarks
 *       - SEO benefits from a single canonical URL per category
 *       - The merchant doesn't have to manage multilingual URL maps
 *     The page CONTENT (label, title, empty state) translates via i18n.
 *
 *  2. Order is FIXED — never reshuffled by product count. Confirmed
 *     by the user: Eventi → Corsi → Servizi → Affitti → Prodotti.
 *     A stable order matters for muscle-memory on the header nav.
 *
 *  3. Each category can match MULTIPLE item_types. This keeps the
 *     navigation simple (5 categories) while covering all 7 canonical
 *     item_types — including the deprecated `booking` (folded into
 *     `servizi` as a fallback during the migration window) and
 *     `digital` (folded into `prodotti` since it's a buy-and-receive
 *     flow, not service-based like `course`).
 *
 *  4. The category list is FIXED at build time. Admins don't create
 *     categories — the categories ARE the item_types. This sidesteps
 *     the entire problem of admin-managed taxonomy + i18n bundling.
 *
 * Adding a new category in the future
 * -----------------------------------
 * 1. Add the entry below in the correct order position.
 * 2. Add the 4 i18n strings (label, title, empty, empty_hint) to
 *    storefront.json in all 4 locale files (it/en/de/fr).
 * 3. Consumers (useAvailableCategories, CategoryNav, CategoryPage)
 *    pick it up automatically — they iterate this array.
 */

/**
 * Ordered list of categories. The order here is the order shown in
 * the header nav (DON'T sort downstream).
 *
 * @type {ReadonlyArray<{
 *   slug: string,                // URL slug (Italian, fixed)
 *   itemTypes: ReadonlyArray<string>,  // backend item_type values this category matches
 *   labelKey: string,            // i18n key for the header nav label
 *   titleKey: string,            // i18n key for the <h1> + document title
 *   emptyKey: string,            // i18n key for the empty-state message
 *   emptyHintKey: string,        // i18n key for the empty-state hint (takes {{org}})
 * }>}
 */
export const CATEGORY_DEFS = Object.freeze([
  {
    slug: 'eventi',
    itemTypes: ['event_ticket'],
    labelKey: 'storefront:category.eventi.label',
    titleKey: 'storefront:category.eventi.title',
    emptyKey: 'storefront:category.eventi.empty',
    emptyHintKey: 'storefront:category.eventi.emptyHint',
  },
  {
    slug: 'corsi',
    itemTypes: ['course'],
    labelKey: 'storefront:category.corsi.label',
    titleKey: 'storefront:category.corsi.title',
    emptyKey: 'storefront:category.corsi.empty',
    emptyHintKey: 'storefront:category.corsi.emptyHint',
  },
  {
    slug: 'servizi',
    // `booking` is the deprecated predecessor of `service` (Onda 16
    // Fase 6 migration in flight). Include it as a fallback so any
    // legacy product not yet migrated still surfaces on this page.
    itemTypes: ['service', 'booking'],
    labelKey: 'storefront:category.servizi.label',
    titleKey: 'storefront:category.servizi.title',
    emptyKey: 'storefront:category.servizi.empty',
    emptyHintKey: 'storefront:category.servizi.emptyHint',
  },
  {
    slug: 'affitti',
    itemTypes: ['rental'],
    labelKey: 'storefront:category.affitti.label',
    titleKey: 'storefront:category.affitti.title',
    emptyKey: 'storefront:category.affitti.empty',
    emptyHintKey: 'storefront:category.affitti.emptyHint',
  },
  {
    slug: 'prodotti',
    // Physical goods + downloadable digital goods share the same
    // "buy and receive" flow — different from `course` which has
    // an enrollment + portal-delivery semantics.
    itemTypes: ['physical', 'digital'],
    labelKey: 'storefront:category.prodotti.label',
    titleKey: 'storefront:category.prodotti.title',
    emptyKey: 'storefront:category.prodotti.empty',
    emptyHintKey: 'storefront:category.prodotti.emptyHint',
  },
]);


/**
 * Fast lookup: URL slug → category definition. Built once at module
 * load so React route components don't re-scan the list on every render.
 *
 * @type {Readonly<Record<string, typeof CATEGORY_DEFS[number]>>}
 */
export const CATEGORY_BY_SLUG = Object.freeze(
  CATEGORY_DEFS.reduce((acc, cat) => {
    acc[cat.slug] = cat;
    return acc;
  }, {}),
);


/**
 * Reverse index: item_type → category slug. Useful for the rare
 * caller that has a product in hand and wants to know "which category
 * would this appear under?" (e.g. linking from an admin-side preview).
 *
 * @type {Readonly<Record<string, string>>}
 */
export const ITEM_TYPE_TO_CATEGORY_SLUG = Object.freeze(
  CATEGORY_DEFS.reduce((acc, cat) => {
    for (const itemType of cat.itemTypes) {
      acc[itemType] = cat.slug;
    }
    return acc;
  }, {}),
);


/**
 * Returns true when the slug matches a known category. Used by
 * CategoryPage to redirect unknown slugs back to the storefront root
 * instead of crashing.
 *
 * @param {string|null|undefined} slug
 * @returns {boolean}
 */
export function isKnownCategorySlug(slug) {
  if (!slug || typeof slug !== 'string') return false;
  return slug in CATEGORY_BY_SLUG;
}
