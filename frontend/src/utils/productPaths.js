/**
 * productPaths — single source of truth for "where do I navigate when
 * the admin clicks on a product / order / calendar item?"
 *
 * Two helpers:
 *
 *   calendarItemPath(item)
 *     For items returned by GET /api/calendar/items. Each item has a
 *     `type` field and the relevant ids; this resolves the right admin
 *     page URL. Replaces the inline navigate(...) blocks in
 *     CalendarPage onNavigate, which used to point everything at the
 *     deprecated /products?product_id=... generic editor.
 *
 *   productDashboardPath({ itemType, productId, occurrenceId })
 *     For "open the dashboard of a product" surfaces (e.g. a future
 *     button on a sales card). Maps the typed-products family to the
 *     dedicated wizards/dashboards introduced after Onda 12. Falls
 *     back to the legacy generic editor only when the type is
 *     unrecognised, so nothing silently breaks.
 *
 * Why a utility (and not three inline switches across the codebase)
 * --------------------------------------------------------------------
 * Until today the calendar hardcoded `/products?product_id=...` for
 * every item type. The result was that clicking "Apri prodotto" on an
 * event_occurrence landed on the old generic ProductsPage instead of
 * the new EventDashboardPage (E6). With this utility, adding a new
 * product type (e.g. `membership` tomorrow) is a one-line change here
 * — every call site picks it up automatically.
 *
 * Backend reference
 * --------------------------------------------------------------------
 * The calendar item shape is defined in backend/routers/calendar.py
 *   - event_occurrence: id = occurrence_id, product_id present
 *   - rental_order:     id = `${order_id}_${product_id}`, order_id + product_id present
 *   - service_booking:  id = booking_id, order_id + product_id present
 *
 * Frontend reference
 * --------------------------------------------------------------------
 * Routes are registered in frontend/src/App.js:
 *   /events/:occurrence_id        EventDashboardPage      (E6)
 *   /services/:product_id         ServiceDashboardPage    (Onda 12)
 *   /reservations/:product_id     ReservationDashboardPage (Onda 16)
 *   /physicals/:product_id        PhysicalDashboardPage    (Release 2)
 *   /digitals/:product_id         DigitalDashboardPage     (Release 3)
 *   /courses/:course_id           CourseEditor             (Release 4)
 *   /orders?order_id=...          OrdersPage (filtered)
 *   /products?product_id=...      ProductsPage (legacy fallback only)
 */


/**
 * URL to navigate to when the admin clicks a calendar item.
 *
 * @param {object} item - one entry from /api/calendar/items
 * @param {string} item.type - "event_occurrence" | "rental_order" | "service_booking"
 * @param {string} [item.id]
 * @param {string} [item.order_id]
 * @param {string} [item.product_id]
 * @returns {string|null} - admin URL or null when there's nothing to navigate to
 */
export function calendarItemPath(item) {
  if (!item || !item.type) return null;

  switch (item.type) {
    case 'event_occurrence':
      // The merchant clicks "Apri prodotto" on a scheduled event ->
      // they want the dashboard for that occurrence (E6 dashboard with
      // tickets list, check-in, capacity, etc.) — not the product
      // catalog row. `item.id` IS the occurrence id (see calendar.py).
      return item.id ? `/events/${item.id}` : null;

    case 'rental_order':
    case 'service_booking':
      // For booked-against-order items the admin's intent is to look
      // at the SPECIFIC order (customer, payment, status) — not at
      // the product the booking refers to. The order page filters by
      // ?order_id and opens the right detail panel.
      return item.order_id ? `/orders?order_id=${item.order_id}` : null;

    default:
      // Unknown future types: do nothing rather than guessing. Caller
      // can show a no-op cursor or surface a toast.
      return null;
  }
}


/**
 * URL to the admin dashboard of a single product, dispatched by item_type.
 *
 * Used wherever a button means "open the dashboard for THIS product"
 * (not "open the order that booked this product"). Today the calendar
 * doesn't expose this directly, but other surfaces (sales cards,
 * landing-page "modify product" links, future analytics drilldowns)
 * benefit from a centralised mapping.
 *
 * @param {object} args
 * @param {string} args.itemType - "event_ticket" | "service" | "rental" |
 *                                  "physical" | "digital" | "course" |
 *                                  legacy aliases ("event_occurrence",
 *                                  "service_booking", "rental_order")
 * @param {string} [args.productId] - the product id (NOT used for events,
 *                                    where occurrenceId is the right key)
 * @param {string} [args.occurrenceId] - the occurrence id, required for
 *                                       events (event_ticket / event_occurrence)
 * @returns {string|null}
 */
export function productDashboardPath({ itemType, productId, occurrenceId }) {
  if (!itemType) return null;

  switch (itemType) {
    // Events are keyed by occurrence (one product, many dates) — the
    // dashboard takes occurrence_id, not product_id. If a caller passes
    // only product_id we cannot guess which occurrence; return null and
    // let the caller decide whether to fall back to the events list.
    case 'event_ticket':
    case 'event_occurrence':
      return occurrenceId ? `/events/${occurrenceId}` : null;

    // The rest are 1:1 with product_id.
    case 'service':
    case 'service_booking':
      return productId ? `/services/${productId}` : '/services';

    case 'rental':
    case 'rental_order':
      return productId ? `/reservations/${productId}` : '/reservations';

    case 'physical':
      return productId ? `/physicals/${productId}` : null;

    case 'digital':
      return productId ? `/digitals/${productId}` : null;

    case 'course':
      // Courses use course_id (a separate doc from the linked product).
      // Caller is expected to pass course_id as productId here; we keep
      // the param name uniform for the dispatch table.
      return productId ? `/courses/${productId}` : '/courses';

    default:
      // Unknown / legacy type — fall back to the generic editor so
      // nothing breaks visibly. New typed-products always have a
      // dedicated case above; this branch should be reached only by
      // historic data with item_type values we no longer produce.
      return productId ? `/products?product_id=${productId}` : '/products';
  }
}
