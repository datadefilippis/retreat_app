/**
 * Order status helpers — single source of truth for the customer portal.
 *
 * Extracted from the monolithic CustomerPortalPages.js so that:
 *   1. The HomePage / OrdersPage / OrderDetailPage all read consistent
 *      labels — fixes the previous duplication where "draft" was shown
 *      as plain "Bozza" in the order detail but as "⏳ In attesa di
 *      conferma" in the orders list.
 *   2. New surfaces (e.g. a future RecentOrdersCard on the home
 *      dashboard) can reuse the same logic without copy-pasting.
 *
 * i18n contract
 * -------------
 * Helpers accept the react-i18next `t` function (namespace
 * `customer_portal`) and return resolved strings. The visual classes
 * (`className`) stay locale-independent so the helpers remain pure
 * for tree-shaking. When `t` is null/undefined we fall back to the
 * legacy Italian strings — that keeps the helpers callable from
 * non-React contexts (tests, CLI scripts) without forcing them to
 * mount the i18n stack.
 *
 * Unknown statuses degrade to a slate-gray badge instead of throwing.
 */

const _IT_FALLBACK = {
  status: {
    draft:     'Bozza',
    confirmed: '✓ Confermato',
    completed: '✓ Completato',
    cancelled: 'Annullato',
  },
  pendingConfirmation:  '⏳ In attesa di conferma',
  awaitingPayment:      '💳 Attesa pagamento',
  fulfillment: {
    pending:          'In attesa',
    shipped:          'Spedito',
    delivered:        'Consegnato',
    ready_for_pickup: 'Pronto per il ritiro',
    picked_up:        'Ritirato',
    fulfilled:        'Completato',
  },
  fulfillmentMode: {
    shipping:           'Spedizione',
    local_pickup:       'Ritiro',
    manual_arrangement: 'Accordo manuale',
  },
  itemsOne:    '1 articolo',
  itemsOther:  '{{count}} articoli',
};


function _tx(t, key, fallback, params) {
  if (!t) return fallback;
  return t(`customer_portal:${key}`, params);
}


export const STATUS_BADGE_CLASSES = {
  draft:     'bg-slate-100 text-slate-600',
  confirmed: 'bg-blue-100 text-blue-700',
  completed: 'bg-emerald-100 text-emerald-700',
  cancelled: 'bg-red-100 text-red-600',
};


/**
 * Resolve a friendlier badge for an order based on its status + the
 * transaction_mode of its first line. A request-mode order shown as
 * "Bozza" reads as if the customer left something incomplete — but
 * truthfully the merchant has the ball (waiting for confirmation).
 *
 * Falls back to the canonical status when no transaction_mode flag
 * applies (legacy orders missing the snapshot, or non-draft statuses).
 *
 * @returns {{ label: string, className: string }}
 */
export function resolveOrderBadge(order, t = null) {
  if (!order) {
    return {
      label: _tx(t, 'orderStatus.draft', _IT_FALLBACK.status.draft),
      className: STATUS_BADGE_CLASSES.draft,
    };
  }
  if (order.status !== 'draft') {
    const cls = STATUS_BADGE_CLASSES[order.status] || STATUS_BADGE_CLASSES.draft;
    const fallback = _IT_FALLBACK.status[order.status] || _IT_FALLBACK.status.draft;
    return {
      label: _tx(t, `orderStatus.${order.status}`, fallback),
      className: cls,
    };
  }
  const items = order.items || [];
  const tx = items.length > 0 ? items[0].transaction_mode : null;
  if (tx === 'request' || tx === 'approval') {
    return {
      label: _tx(t, 'orderStatus.pendingConfirmation', _IT_FALLBACK.pendingConfirmation),
      className: 'bg-amber-100 text-amber-800',
    };
  }
  if (tx === 'direct' && order.payment_status === 'pending') {
    return {
      label: _tx(t, 'orderStatus.awaitingPayment', _IT_FALLBACK.awaitingPayment),
      className: 'bg-violet-100 text-violet-800',
    };
  }
  return {
    label: _tx(t, 'orderStatus.draft', _IT_FALLBACK.status.draft),
    className: STATUS_BADGE_CLASSES.draft,
  };
}


/**
 * Whether an order contains at least one course line. Used to decide
 * if the order card should surface the "Apri corso" shortcut.
 */
export function orderHasCourse(order) {
  return (order?.items || []).some(it => it.item_type === 'course');
}


/**
 * Format the items summary line shown in the order card
 * ("3 articoli" / "Test corso" / "1 articolo").
 */
export function formatItemsSummary(order, t = null) {
  const items = order?.items || [];
  if (items.length === 0) return '';
  if (items.length === 1) {
    return items[0].product_name
      || _tx(t, 'orderStatus.itemsOne', _IT_FALLBACK.itemsOne);
  }
  return _tx(
    t,
    'orderStatus.itemsOther',
    _IT_FALLBACK.itemsOther.replace('{{count}}', items.length),
    { count: items.length },
  );
}


/**
 * Resolve a localized fulfillment status label.
 */
export function getFulfillmentStatusLabel(status, t = null) {
  const fallback = _IT_FALLBACK.fulfillment[status] || status;
  if (!status || !_IT_FALLBACK.fulfillment[status]) return fallback;
  return _tx(t, `fulfillmentStatus.${status}`, fallback);
}


/**
 * Resolve a localized fulfillment-mode label.
 */
export function getFulfillmentModeLabel(mode, t = null) {
  const fallback = _IT_FALLBACK.fulfillmentMode[mode] || mode;
  if (!mode || !_IT_FALLBACK.fulfillmentMode[mode]) return fallback;
  return _tx(t, `fulfillmentMode.${mode}`, fallback);
}


// Legacy named exports — still used by callers that haven't migrated.
// Built lazily from the IT fallback so existing imports keep working
// without the consumer needing to thread `t`. New code should call
// `getFulfillmentStatusLabel` / `getFulfillmentModeLabel` instead.
export const STATUS_BADGES = Object.fromEntries(
  Object.entries(_IT_FALLBACK.status).map(([k, label]) => (
    [k, { label, className: STATUS_BADGE_CLASSES[k] }]
  )),
);
export const FULFILLMENT_STATUS_LABELS = { ..._IT_FALLBACK.fulfillment };
export const FULFILLMENT_MODE_LABELS = { ..._IT_FALLBACK.fulfillmentMode };
