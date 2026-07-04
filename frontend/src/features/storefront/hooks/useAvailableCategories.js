/**
 * useAvailableCategories — derive the list of categories that have at
 * least one product in the current catalog.
 *
 * Phase 7 of the storefront redesign: the header nav and the root
 * `/s/:slug` redirect both need to know which categories carry
 * inventory. Categories with ZERO products in this store stay hidden
 * (user decision: "nascoste") so visitors don't see dead links.
 *
 * Architecture: ZERO backend change
 * ---------------------------------
 * The catalog response already includes every product (with its
 * `item_type`), so deriving categories is a pure client-side
 * computation. No new endpoint, no DB query, no extra round trip.
 *
 * Memoized on `catalog?.products` reference so:
 *   - Re-renders triggered by unrelated state (qty change, etc.)
 *     don't recompute the array.
 *   - When the catalog refetches (e.g. language switch), the array
 *     identity changes once, and downstream `<CategoryNav>` /
 *     `<Redirect>` recompute exactly once.
 *
 * Result shape
 * ------------
 * Returns the SAME entries as CATEGORY_DEFS (with one extra `count`
 * field), filtered to only those with count > 0, in CATEGORY_DEFS
 * order. Callers (CategoryNav, redirect logic) can render directly
 * — no further sorting needed.
 *
 *   [
 *     { slug: 'eventi',   itemTypes: ['event_ticket'], labelKey: '…', count: 2 },
 *     { slug: 'servizi',  itemTypes: ['service','booking'], labelKey: '…', count: 4 },
 *     { slug: 'prodotti', itemTypes: ['physical','digital'], labelKey: '…', count: 2 },
 *   ]
 *
 * `count` is provided for future UX needs (e.g. badge "Servizi (4)")
 * but consumers can ignore it — Phase 7.4 nav doesn't surface it yet.
 *
 * Edge cases
 * ----------
 *   - catalog === null               → returns []
 *   - catalog.products === undefined → returns []
 *   - catalog.products === []        → returns []
 *   - catalog.products has only unknown item_types → returns []
 *
 * `useMemo` not `useState` — this is purely derived data with no
 * setter contract. Avoids the trap where two stale states (catalog +
 * derived array) can diverge.
 */

import { useMemo } from 'react';
import { CATEGORY_DEFS } from '../categories';


/**
 * @param {{ products?: Array<{ item_type?: string }> } | null | undefined} catalog
 * @returns {Array<{
 *   slug: string,
 *   itemTypes: ReadonlyArray<string>,
 *   labelKey: string,
 *   titleKey: string,
 *   emptyKey: string,
 *   emptyHintKey: string,
 *   count: number,
 * }>}
 */
export default function useAvailableCategories(catalog) {
  return useMemo(() => {
    const products = catalog?.products || [];
    if (products.length === 0) return [];

    // Bucket counts by item_type. Single pass over the products array.
    const countsByType = new Map();
    for (const p of products) {
      const t = p?.item_type;
      if (!t) continue;
      countsByType.set(t, (countsByType.get(t) || 0) + 1);
    }

    // Filter CATEGORY_DEFS (preserves order) and attach the count.
    // Sum across all matching item_types so the merged "servizi"
    // category (service + booking) gets the combined count.
    const out = [];
    for (const cat of CATEGORY_DEFS) {
      let total = 0;
      for (const itemType of cat.itemTypes) {
        total += countsByType.get(itemType) || 0;
      }
      if (total > 0) {
        out.push({ ...cat, count: total });
      }
    }
    return out;
  }, [catalog?.products]);
}
