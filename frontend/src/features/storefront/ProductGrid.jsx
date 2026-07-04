/**
 * ProductGrid — multi-section storefront catalog grid.
 *
 * Phase 7.3 — extracted from StorefrontPage.js so the upcoming
 * CategoryPage (Phase 7.5) can render the same grid with a
 * pre-filtered product subset.
 *
 * Responsibilities
 * ----------------
 *   1. Bucket the input `products` array by item_type into 7 logical
 *      sections (event_ticket / service / rental / physical / digital /
 *      course / catalog-rest).
 *   2. Sort each section deterministically.
 *   3. Render each non-empty section with a translated header + count,
 *      then a responsive grid of cards.
 *   4. Wire the inline ProductCard fallback (legacy products without a
 *      slug) with the cart slice setters from the parent.
 *
 * Responsibilities it does NOT own
 * --------------------------------
 *   - Cart state               (lives in useStorefrontCart at the parent)
 *   - Booking modal            (rendered at page level — needs to be
 *                              outside the grid because it's a global
 *                              modal positioned in the viewport)
 *   - Availability fetching    (the parent loads it once and passes the
 *                              cached result through)
 *   - Loading spinner          (parent renders it while the catalog
 *                              fetch is in flight)
 *
 * On `hideSectionTitles`
 * ----------------------
 * The CategoryPage in Phase 7.5 filters `products` to a single item_type
 * before passing it in. In that scenario the section header would
 * duplicate the page's h1 ("Eventi" / "Servizi" / ...) — set
 * `hideSectionTitles=true` to suppress the duplicate.
 *
 * On `availableSlots`
 * -------------------
 * Only relevant for legacy `booking` item_type products (deprecated).
 * Modern `service` items render via ServiceCard which deep-links to a
 * landing page where the slot picker lives. CategoryPage instances can
 * pass `availableSlots=null` and the inline picker will show its
 * loading spinner — which is fine because no booking product will
 * surface in a category-filtered view anyway (booking maps to
 * `servizi` and renders as ServiceCard).
 */

import React, { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Search as SearchIcon, X as XIcon } from 'lucide-react';

import {
  EventOccurrenceCard,
  ServiceCard,
  ReservationCard,
  PhysicalCard,
  DigitalCard,
  CourseCard,
  ProductCard,
} from './components/StorefrontCards';


/**
 * Bucket products into the 7 sections + sort each.
 *
 * Same ruleset as the legacy IIFE inside StorefrontPage: a product
 * surfaces in the deep-link section (eventCards / serviceCards / ...)
 * ONLY if it has a slug AND the corresponding landing route exists.
 * Anything else falls through to the inline `catalogProducts` bucket
 * which renders via ProductCard.
 */
function _bucketProducts(products) {
  const eventCards = [];
  const serviceCards = [];
  const reservationCards = [];
  const physicalCards = [];
  const digitalCards = [];
  const courseCards = [];
  const catalogProducts = [];

  for (const p of products) {
    // Events: one card per published occurrence (with a slug). A
    // product with N occurrences produces N event cards — one tile
    // per date.
    if (p.item_type === 'event_ticket' && Array.isArray(p.occurrences) && p.occurrences.length > 0) {
      const linkable = p.occurrences.filter(o => !!o.slug);
      if (linkable.length > 0) {
        for (const occ of linkable) eventCards.push({ product: p, occurrence: occ });
        continue;
      }
    }
    // Services with a slug → ServiceCard (deep-link to /p/:org/:slug)
    if (p.item_type === 'service' && p.slug) {
      serviceCards.push(p);
      continue;
    }
    // Rentals with a slug → ReservationCard (deep-link to /r/:org/:slug)
    if (p.item_type === 'rental' && p.slug) {
      reservationCards.push(p);
      continue;
    }
    // Physicals with a slug → PhysicalCard (deep-link to /ph/:org/:slug)
    if (p.item_type === 'physical' && p.slug) {
      physicalCards.push(p);
      continue;
    }
    // Digitals with a slug → DigitalCard (deep-link to /dg/:org/:slug)
    if (p.item_type === 'digital' && p.slug) {
      digitalCards.push(p);
      continue;
    }
    // Courses with a slug → CourseCard (deep-link to /co/:org/:slug)
    if (p.item_type === 'course' && p.slug) {
      courseCards.push(p);
      continue;
    }
    // Anything left — legacy products without a slug, deprecated
    // `booking` items, inquiry-mode products — render inline via
    // ProductCard.
    catalogProducts.push(p);
  }

  // Sort each section. Events sort by occurrence start_at so the
  // chronological order is preserved across multi-date products.
  // Other sections sort alphabetically for deterministic layout.
  eventCards.sort((a, b) =>
    (a.occurrence.start_at || '').localeCompare(b.occurrence.start_at || ''),
  );
  serviceCards.sort((a, b) => (a.name || '').localeCompare(b.name || ''));
  reservationCards.sort((a, b) => (a.name || '').localeCompare(b.name || ''));
  physicalCards.sort((a, b) => (a.name || '').localeCompare(b.name || ''));
  digitalCards.sort((a, b) => (a.name || '').localeCompare(b.name || ''));
  courseCards.sort((a, b) => (a.name || '').localeCompare(b.name || ''));

  return {
    eventCards, serviceCards, reservationCards,
    physicalCards, digitalCards, courseCards,
    catalogProducts,
  };
}


/**
 * Single section header + grid. Extracted out of the JSX body so the
 * 6 deep-link sections share one rendering path.
 */
function Section({ titleKey, count, hideTitle, children }) {
  const { t } = useTranslation('storefront');
  if (count === 0) return null;
  return (
    <section className="max-w-6xl mx-auto px-4 pt-6">
      {!hideTitle && (
        <div className="flex items-baseline justify-between mb-4">
          <h2 className="text-xl sm:text-2xl font-bold text-gray-900">{t(titleKey)}</h2>
          <p className="text-xs text-gray-500">
            {t(`${titleKey.replace('.title', '.count')}`, { count })}
          </p>
        </div>
      )}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {children}
      </div>
    </section>
  );
}


/**
 * Public component.
 *
 * @param {{
 *   products: Array<object>,
 *   currency?: string,
 *   orgSlug: string,
 *   hideSectionTitles?: boolean,
 *   // Cart slice values + setters (consumed by inline ProductCard fallback)
 *   quantities: object,
 *   setQuantities: (updater) => void,
 *   selectedOccurrences: object,
 *   setSelectedOccurrences: (updater) => void,
 *   rentalDates: object,
 *   setRentalDates: (updater) => void,
 *   bookingSlots: object,
 *   setBookingSlots: (updater) => void,
 *   availableSlots: Array | null,
 * }} props
 */
export default function ProductGrid({
  products,
  currency,
  orgSlug,
  hideSectionTitles = false,
  // Sprint 2 W2.4 — search bar opt-in (parity widget E5.1)
  showSearch = true,
  // Sprint 3 W3.3 — sort + pagination opt-in (parity widget afianco-product-grid)
  showSort = true,
  pageSize = 24,
  // Cart slice props for inline ProductCard fallback
  quantities,
  setQuantities,
  selectedOccurrences,
  setSelectedOccurrences,
  rentalDates,
  setRentalDates,
  bookingSlots,
  setBookingSlots,
  availableSlots,
}) {
  const { t } = useTranslation('storefront');

  // Sprint 2 W2.4 — Search input client-side (parity widget afianco-product-grid
  // show-search attribute E5.1). React storefront ha gia' tutti i prodotti
  // dal /catalog endpoint quindi filtro client-side (no extra round-trip).
  // Mirror semantic widget: case-insensitive match su name + description.
  const [searchQuery, setSearchQuery] = useState('');
  const normalizedQuery = searchQuery.trim().toLowerCase();

  // Sprint 3 W3.3 — Sort mode (parity widget E5.1 sort whitelist)
  // Modes: name | price_asc | price_desc | newest
  const [sortMode, setSortMode] = useState('name');

  // Sprint 3 W3.3 — Pagination 'Show more' (parity widget pagination)
  const [shownCount, setShownCount] = useState(pageSize);

  const filteredProducts = useMemo(() => {
    let list = products || [];
    // Search filter
    if (normalizedQuery) {
      list = list.filter((p) => {
        const name = (p?.name || '').toLowerCase();
        const desc = (p?.description || '').toLowerCase();
        return name.includes(normalizedQuery) || desc.includes(normalizedQuery);
      });
    }
    // Sort (Sprint 3 W3.3 — match widget E5.1 whitelist)
    if (sortMode === 'price_asc') {
      list = [...list].sort((a, b) => (Number(a.unit_price) || 0) - (Number(b.unit_price) || 0));
    } else if (sortMode === 'price_desc') {
      list = [...list].sort((a, b) => (Number(b.unit_price) || 0) - (Number(a.unit_price) || 0));
    } else if (sortMode === 'newest') {
      list = [...list].sort((a, b) => {
        const ta = a.created_at ? new Date(a.created_at).getTime() : 0;
        const tb = b.created_at ? new Date(b.created_at).getTime() : 0;
        return tb - ta;
      });
    } else {
      // default 'name' alphabetical
      list = [...list].sort((a, b) => (a.name || '').localeCompare(b.name || ''));
    }
    return list;
  }, [products, normalizedQuery, sortMode]);

  // Sprint 3 W3.3 — Pagination apply: slice della lista filtrata
  const paginatedProducts = useMemo(
    () => filteredProducts.slice(0, shownCount),
    [filteredProducts, shownCount],
  );

  const hasMore = filteredProducts.length > shownCount;

  // Reset pagination quando cambia query/sort (UX safety)
  React.useEffect(() => {
    setShownCount(pageSize);
  }, [normalizedQuery, sortMode, pageSize]);

  const {
    eventCards, serviceCards, reservationCards,
    physicalCards, digitalCards, courseCards,
    catalogProducts,
  } = _bucketProducts(paginatedProducts);

  // Show the "Catalogo" h2 only when there are OTHER sections above
  // it AND the parent didn't suppress section titles. On CategoryPage
  // the parent's h1 already says "Prodotti" / "Servizi" etc., so the
  // duplicate is hidden.
  const hasUpperSections =
    eventCards.length + serviceCards.length + reservationCards.length
    + physicalCards.length + digitalCards.length + courseCards.length > 0;

  const hasZeroMatches =
    normalizedQuery.length > 0 &&
    eventCards.length === 0 &&
    serviceCards.length === 0 &&
    reservationCards.length === 0 &&
    physicalCards.length === 0 &&
    digitalCards.length === 0 &&
    courseCards.length === 0 &&
    catalogProducts.length === 0;

  return (
    <>
      {/* Sprint 2 W2.4 + Sprint 3 W3.3 — Search bar + Sort dropdown.
          Search filter client-side su name + description.
          Sort whitelist (mirror widget E5.1): name | price_asc |
          price_desc | newest. Layout flex: search 70% / sort 30% (mobile
          stack). */}
      {(showSearch || showSort) && (
        <section className="max-w-6xl mx-auto px-4 pt-6">
          <div className="flex flex-col sm:flex-row gap-2">
            {showSearch && (
              <div className="relative flex-1">
                <SearchIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400 pointer-events-none" />
                <input
                  type="search"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder={t('storefront:search.placeholder', 'Cerca prodotti...')}
                  className="w-full rounded-lg border border-gray-300 pl-9 pr-9 py-2 text-sm focus:ring-2 focus:ring-gray-800 focus:border-transparent outline-none"
                  aria-label={t('storefront:search.ariaLabel', 'Cerca nel catalogo')}
                />
                {searchQuery && (
                  <button
                    type="button"
                    onClick={() => setSearchQuery('')}
                    className="absolute right-2 top-1/2 -translate-y-1/2 p-1 rounded hover:bg-gray-100"
                    aria-label={t('storefront:search.clearAria', 'Cancella ricerca')}
                  >
                    <XIcon className="h-4 w-4 text-gray-500" />
                  </button>
                )}
              </div>
            )}
            {showSort && (
              <select
                value={sortMode}
                onChange={(e) => setSortMode(e.target.value)}
                aria-label={t('storefront:search.sortAriaLabel', 'Ordina prodotti')}
                className="rounded-lg border border-gray-300 px-3 py-2 text-sm bg-white focus:ring-2 focus:ring-gray-800 focus:border-transparent outline-none sm:w-48"
              >
                <option value="name">{t('storefront:search.sortName', 'Nome A-Z')}</option>
                <option value="price_asc">{t('storefront:search.sortPriceAsc', 'Prezzo: crescente')}</option>
                <option value="price_desc">{t('storefront:search.sortPriceDesc', 'Prezzo: decrescente')}</option>
                <option value="newest">{t('storefront:search.sortNewest', 'Piu\' recenti')}</option>
              </select>
            )}
          </div>
        </section>
      )}

      {/* Empty state quando search query no match */}
      {hasZeroMatches && (
        <section className="max-w-6xl mx-auto px-4 pt-6">
          <div className="rounded-lg border border-gray-200 bg-gray-50 p-6 text-center text-sm text-gray-600">
            <p className="font-medium text-gray-900">
              {t('storefront:search.noResults', 'Nessun prodotto trovato')}
            </p>
            <p className="mt-1">
              {t(
                'storefront:search.noResultsHint',
                'Prova a modificare la query o rimuovere i filtri.',
                { query: searchQuery }
              )}
            </p>
            <button
              type="button"
              onClick={() => setSearchQuery('')}
              className="mt-3 text-xs font-semibold text-gray-700 underline hover:text-gray-900"
            >
              {t('storefront:search.clearAll', 'Mostra tutti i prodotti')}
            </button>
          </div>
        </section>
      )}

      <Section titleKey="storefront:sections.events.title"
                count={eventCards.length}
                hideTitle={hideSectionTitles}>
        {eventCards.map(({ product, occurrence }) => (
          <EventOccurrenceCard
            key={occurrence.id}
            product={product}
            occurrence={occurrence}
            orgSlug={orgSlug}
            currency={currency}
          />
        ))}
      </Section>

      <Section titleKey="storefront:sections.services.title"
                count={serviceCards.length}
                hideTitle={hideSectionTitles}>
        {serviceCards.map(p => (
          <ServiceCard key={p.id} product={p} orgSlug={orgSlug} currency={currency} />
        ))}
      </Section>

      <Section titleKey="storefront:sections.reservations.title"
                count={reservationCards.length}
                hideTitle={hideSectionTitles}>
        {reservationCards.map(p => (
          <ReservationCard key={p.id} product={p} orgSlug={orgSlug} currency={currency} />
        ))}
      </Section>

      <Section titleKey="storefront:sections.physicals.title"
                count={physicalCards.length}
                hideTitle={hideSectionTitles}>
        {physicalCards.map(p => (
          <PhysicalCard key={p.id} product={p} orgSlug={orgSlug} currency={currency} />
        ))}
      </Section>

      <Section titleKey="storefront:sections.digitals.title"
                count={digitalCards.length}
                hideTitle={hideSectionTitles}>
        {digitalCards.map(p => (
          <DigitalCard key={p.id} product={p} orgSlug={orgSlug} currency={currency} />
        ))}
      </Section>

      <Section titleKey="storefront:sections.courses.title"
                count={courseCards.length}
                hideTitle={hideSectionTitles}>
        {courseCards.map(p => (
          <CourseCard key={p.id} product={p} orgSlug={orgSlug} currency={currency} />
        ))}
      </Section>

      {/* "Catalogo" fallback section — inline ProductCard rendering.
          Used for legacy products without a dedicated landing page. */}
      {catalogProducts.length > 0 && (
        <main className="max-w-6xl mx-auto px-4 py-6">
          {hasUpperSections && !hideSectionTitles && (
            <h2 className="text-xl sm:text-2xl font-bold text-gray-900 mb-4 mt-4">
              {t('storefront:sections.catalog.title')}
            </h2>
          )}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {catalogProducts.map(p => (
              <ProductCard
                key={p.id}
                product={p}
                qty={quantities[p.id] || 0}
                onQtyChange={(qty) => setQuantities(prev => ({ ...prev, [p.id]: qty }))}
                selectedOccurrence={selectedOccurrences[p.id] || null}
                onOccurrenceChange={(occ) => setSelectedOccurrences(prev => ({ ...prev, [p.id]: occ }))}
                rentalDate={rentalDates[p.id] || null}
                onRentalDateChange={(rd) => setRentalDates(prev => ({ ...prev, [p.id]: rd }))}
                bookingSlot={bookingSlots[p.id] || null}
                onBookingSlotChange={(bs) => setBookingSlots(prev => ({ ...prev, [p.id]: bs }))}
                availableSlots={availableSlots}
                currency={currency}
                orgSlug={orgSlug}
              />
            ))}
          </div>
        </main>
      )}

      {/* Sprint 3 W3.3 — Pagination footer "Show more" button (parity widget). */}
      {hasMore && !hasZeroMatches && (
        <section className="max-w-6xl mx-auto px-4 pt-6 pb-2 text-center">
          <p className="text-xs text-gray-500 mb-2">
            {t('storefront:search.paginationCount', '{{shown}} di {{total}} prodotti', {
              shown: paginatedProducts.length,
              total: filteredProducts.length,
            })}
          </p>
          <button
            type="button"
            onClick={() => setShownCount((c) => c + pageSize)}
            className="rounded-lg border border-gray-300 bg-white text-sm font-semibold px-5 py-2 hover:bg-gray-50"
          >
            {t('storefront:search.showMore', 'Mostra altri prodotti')}
          </button>
        </section>
      )}
    </>
  );
}
