/**
 * OrderLineItem — single row renderer for an order line, dispatching to the
 * right per-type details component.
 *
 * Centralises the line layout (product name + type badge + quantity/price on
 * the right) so per-type detail components can focus on their own info. The
 * legacy inline JSX in OrdersPage OrderDetailPanel previously did this with a
 * stack of conditional blocks — extracting here keeps each type bounded.
 */

import { ITEM_TYPE_LABELS, getItemTypeBadgeClass, TRANSACTION_MODE_OPTIONS } from '../../../constants/itemTypes';
import EventLineDetails from './EventLineDetails';
import ServiceLineDetails from './ServiceLineDetails';
import ReservationLineDetails from './ReservationLineDetails';
import DigitalLineDetails from './DigitalLineDetails';

const fmtEur = (v) => (v != null
  ? new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR', maximumFractionDigits: 2 }).format(v)
  : '-');

function renderTypeDetails(item, t) {
  // Note: booking item_type is deprecated (Onda 16) and maps to rental+flavor=slot,
  // but pre-migration orders retain item_type=booking in their snapshot — route
  // them to the reservation renderer which handles both flavors.
  const type = item?.item_type;
  if (type === 'event_ticket') return <EventLineDetails item={item} t={t} />;
  if (type === 'service') return <ServiceLineDetails item={item} t={t} />;
  if (type === 'rental' || type === 'booking') return <ReservationLineDetails item={item} t={t} />;
  if (type === 'digital') return <DigitalLineDetails item={item} t={t} />;
  return null;
}

export default function OrderLineItem({ item, t }) {
  if (!item) return null;
  const typeLabel = ITEM_TYPE_LABELS[item.item_type];
  const txMode = item.transaction_mode && item.transaction_mode !== 'request'
    ? TRANSACTION_MODE_OPTIONS.find((o) => o.value === item.transaction_mode)?.label || item.transaction_mode
    : null;

  return (
    <div className="flex items-start justify-between rounded-lg border p-3 text-sm">
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1.5 flex-wrap">
          <p className="font-medium truncate">{item.product_name}</p>
          {typeLabel && (
            <span className={`shrink-0 text-[10px] px-1.5 py-0.5 rounded-full font-medium ${getItemTypeBadgeClass(item.item_type)}`}>
              {typeLabel}
            </span>
          )}
          {txMode && (
            <span className="shrink-0 text-[10px] px-1.5 py-0.5 rounded-full font-medium bg-gray-100 text-gray-500">
              {txMode}
            </span>
          )}
        </div>
        {item.sku && <p className="text-xs text-muted-foreground">{item.sku}</p>}
        {renderTypeDetails(item, t)}
      </div>
      <div className="text-right ml-3 flex-shrink-0">
        {item.line_total <= 0 && item.quantity > 0 ? (
          <p className="text-xs text-amber-600 italic">{t?.('detail.price_tbd', { defaultValue: 'Da definire' })}</p>
        ) : (
          <>
            <p className="text-muted-foreground text-xs">{item.quantity} × {fmtEur(item.unit_price)}</p>
            <p className="font-semibold">{fmtEur(item.line_total)}</p>
            {item.extras_total != null && item.extras_total > 0 && (
              <p className="text-[10px] text-muted-foreground">
                {t?.('detail.includes_extras', { defaultValue: 'inclusi extras' })} {fmtEur(item.extras_total)}
              </p>
            )}
          </>
        )}
      </div>
    </div>
  );
}
