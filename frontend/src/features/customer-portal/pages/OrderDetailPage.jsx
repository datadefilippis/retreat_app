/**
 * OrderDetailPage — single-order detail view.
 *
 * Phase 3 extraction from CustomerPortalPages.js:
 *   - Removed the local header replication (TopBar comes from CustomerLayout)
 *   - Removed the bg-slate-50 + min-h-screen wrapper (the layout owns
 *     the background)
 *   - Removed the local "back" button (PageHeader renders it instead)
 *   - Reused STATUS_BADGES from utils/orderStatus (single source of truth)
 *   - Reused FULFILLMENT_*_LABELS from utils/orderStatus
 *
 * Behavior preserved 1:1:
 *   - Course CTA banner when the order contains an item_type=course line
 *   - Structured shipping address rendering with legacy fallback
 *   - Fulfillment status badge + dates (shipped_at, delivered_at)
 *   - Line items + totals
 *   - Notes block when present
 */

import React, { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Truck, MapPin, Package } from 'lucide-react';
import { customerAuthAPI } from '../../../api/customerAuth';
import {
  resolveOrderBadge,
  getFulfillmentStatusLabel,
  getFulfillmentModeLabel,
} from '../utils/orderStatus';
import { Card, CardContent, CardHeader, CardTitle } from '../../../components/ui/card';
import { Badge } from '../../../components/ui/badge';
import PageHeader from '../components/PageHeader';
import OrderDetailSkeleton from '../components/skeletons/OrderDetailSkeleton';
import EmptyState from '../components/EmptyState';
import OrderItemRenderer from '../components/order-items/OrderItemRenderer';


// View-specific maps. Kept inline because they're only consumed here;
// promote to utils/ if a second surface ever needs them.
const FF_MODE_ICONS = {
  shipping: Truck,
  local_pickup: MapPin,
  manual_arrangement: Package,
};
const FF_STATUS_CLASSES = {
  pending:           'bg-amber-100 text-amber-700',
  shipped:           'bg-blue-100 text-blue-700',
  delivered:         'bg-emerald-100 text-emerald-700',
  ready_for_pickup:  'bg-indigo-100 text-indigo-700',
  picked_up:         'bg-emerald-100 text-emerald-700',
  fulfilled:         'bg-emerald-100 text-emerald-700',
};


function fmtCurrency(value, currency = 'EUR', locale = 'it-IT') {
  if (value == null) return '-';
  try {
    return new Intl.NumberFormat(locale, {
      style: 'currency', currency, maximumFractionDigits: 2,
    }).format(value);
  } catch { return `${value} ${currency}`; }
}


function formatLongDate(iso, locale = 'it-IT') {
  if (!iso) return '';
  try {
    return new Date(iso).toLocaleDateString(locale, {
      day: '2-digit', month: 'long', year: 'numeric',
    });
  } catch { return ''; }
}


// "3 giorni fa", "ieri", "oggi" — relative wrapper for shipped_at/
// delivered_at so the customer knows recency without scanning a date.
// Falls back to formatLongDate for anything older than ~30 days.
function formatRelativeDate(iso, t, locale) {
  if (!iso) return '';
  try {
    const d = new Date(iso);
    const now = new Date();
    const diffMs = now - d;
    const day = 24 * 60 * 60 * 1000;
    const diffDays = Math.floor(diffMs / day);
    if (diffDays < 0) return formatLongDate(iso, locale);
    if (diffDays === 0) return t('customer_portal:orderDetail.relative.today');
    if (diffDays === 1) return t('customer_portal:orderDetail.relative.yesterday');
    if (diffDays < 30) return t('customer_portal:orderDetail.relative.daysAgo', { count: diffDays });
    return formatLongDate(iso, locale);
  } catch { return formatLongDate(iso, locale); }
}


export default function OrderDetailPage() {
  const { orderId } = useParams();
  const { t, i18n } = useTranslation('customer_portal');
  const [order, setOrder] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    customerAuthAPI.getOrder(orderId)
      .then(res => setOrder(res.data))
      .catch(() => setError('not_found'))
      .finally(() => setLoading(false));
  }, [orderId]);

  if (loading) {
    // Phase 7 polish — header + items skeleton instead of a centered
    // spinner. Reads "this is loading the right page" rather than
    // "is something wrong?" while the API call is in flight.
    return <OrderDetailSkeleton />;
  }

  if (error || !order) {
    // Phase 7 polish — same EmptyState chrome the rest of the portal
    // uses for "nothing to see here", with copy tuned to the most
    // likely cause (the customer landed on an old/foreign URL) without
    // being accusatory. The CTA leads back to the orders list — the
    // single recovery path that always works.
    return (
      <EmptyState
        icon="🔎"
        title={t('customer_portal:orderDetail.notFoundTitle')}
        description={t('customer_portal:orderDetail.notFoundDescription')}
        cta={{ to: '/account/orders', label: t('customer_portal:orderDetail.backToOrders') }}
      />
    );
  }

  const statusBadge = resolveOrderBadge(order, t);
  const ff = order.fulfillment || {};
  const hasFulfillment = ff.mode && ff.mode !== 'not_required';
  const FfModeIcon = FF_MODE_ICONS[ff.mode] || Package;
  const orderDate = formatLongDate(order.created_at, i18n.language);
  const hasCourse = (order.items || []).some(it => it.item_type === 'course');

  return (
    <div className="space-y-4">
      <PageHeader
        backTo="/account/orders"
        backLabel={t('customer_portal:orders.title')}
        title={order.order_number || `#${order.id.slice(0, 8)}`}
        meta={(
          <>
            <span>{orderDate}</span>
            {order.org_name && (
              <>
                <span aria-hidden>·</span>
                <span>{order.org_name}</span>
              </>
            )}
          </>
        )}
        action={<Badge className={`text-xs ${statusBadge.className}`}>{statusBadge.label}</Badge>}
      />

      {/* Course CTA — leads the customer from "I bought" to "Let me consume it". */}
      {hasCourse && (
        <Link
          to="/account/courses"
          className="block rounded-xl border border-blue-200 bg-blue-50 hover:bg-blue-100 transition-colors p-4 no-underline"
        >
          <div className="flex items-center gap-3">
            <span className="text-3xl" aria-hidden>🎓</span>
            <div className="flex-1 min-w-0">
              <p className="font-semibold text-blue-900">{t('customer_portal:orderDetail.courseCta.title')}</p>
              <p className="text-xs text-blue-800 mt-0.5">
                {t('customer_portal:orderDetail.courseCta.body')}
              </p>
            </div>
            <span className="text-blue-700 font-semibold text-sm whitespace-nowrap">
              {t('customer_portal:orderDetail.courseCta.openShort')}
            </span>
          </div>
        </Link>
      )}

      {/* Fulfillment block */}
      {hasFulfillment && (
        <Card>
          <CardContent className="py-3 px-4 space-y-1.5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-sm font-medium">
                <FfModeIcon className="h-4 w-4 text-muted-foreground" />
                {getFulfillmentModeLabel(ff.mode, t)}
              </div>
              <Badge className={`text-[10px] ${FF_STATUS_CLASSES[ff.status] || 'bg-slate-100 text-slate-600'}`}>
                {getFulfillmentStatusLabel(ff.status, t)}
              </Badge>
            </div>
            {/* Structured address takes precedence over legacy flattened string. */}
            {ff.shipping_address_details ? (() => {
              const d = ff.shipping_address_details;
              const streetLine = [d.line1, d.civic].filter(Boolean).join(' ');
              const cityLine = [d.postal_code, d.city, d.province ? `(${d.province})` : null]
                .filter(Boolean).join(' ');
              const country = d.country && d.country !== 'IT' ? d.country : null;
              return (
                <div className="text-xs text-muted-foreground space-y-0 leading-tight">
                  <p className="font-medium">{t('customer_portal:orderDetail.addressLabel')}</p>
                  {d.recipient_name && <p className="pl-3">{d.recipient_name}</p>}
                  {streetLine && <p className="pl-3">{streetLine}</p>}
                  {cityLine && <p className="pl-3">{cityLine}</p>}
                  {country && <p className="pl-3">{country}</p>}
                </div>
              );
            })() : ff.shipping_address ? (
              <p className="text-xs text-muted-foreground">{t('customer_portal:orderDetail.addressInline', { address: ff.shipping_address })}</p>
            ) : null}
            {ff.fulfillment_notes && (
              <p className="text-xs text-muted-foreground">{t('customer_portal:orderDetail.notesInline', { notes: ff.fulfillment_notes })}</p>
            )}
            {ff.shipped_at && (
              <p className="text-xs text-muted-foreground">
                {t('customer_portal:orderDetail.shippedAt', {
                  rel: formatRelativeDate(ff.shipped_at, t, i18n.language),
                  date: ff.shipped_at.slice(0, 10),
                })}
              </p>
            )}
            {ff.delivered_at && (
              <p className="text-xs text-muted-foreground">
                {ff.status === 'picked_up'
                  ? t('customer_portal:orderDetail.pickedUpAt', {
                      rel: formatRelativeDate(ff.delivered_at, t, i18n.language),
                      date: ff.delivered_at.slice(0, 10),
                    })
                  : ff.status === 'fulfilled'
                    ? t('customer_portal:orderDetail.fulfilledAt', {
                        rel: formatRelativeDate(ff.delivered_at, t, i18n.language),
                        date: ff.delivered_at.slice(0, 10),
                      })
                    : t('customer_portal:orderDetail.deliveredAt', {
                        rel: formatRelativeDate(ff.delivered_at, t, i18n.language),
                        date: ff.delivered_at.slice(0, 10),
                      })}
              </p>
            )}
            {/* Tracking — shown when the merchant attached a carrier. */}
            {(ff.tracking_number || ff.tracking_url) && (
              <div className="mt-1 pt-1 border-t border-gray-100 flex items-center justify-between gap-2 flex-wrap">
                {ff.tracking_number && (
                  <span className="text-xs text-muted-foreground">
                    {t('customer_portal:orderDetail.trackingLabel')}{' '}
                    <span className="font-mono text-foreground select-all">
                      {ff.tracking_number}
                    </span>
                  </span>
                )}
                {ff.tracking_url && (
                  <a
                    href={ff.tracking_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 px-3 py-1 rounded-md bg-gray-900 text-white text-xs font-semibold hover:bg-gray-800 transition-colors"
                  >
                    {t('customer_portal:orderDetail.trackShipment')}
                  </a>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Line items — dispatched per item_type via OrderItemRenderer. */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">{t('customer_portal:orderDetail.itemsTitle')}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {(order.items || []).map((item, i) => (
            <OrderItemRenderer
              key={i}
              item={item}
              currency={order.currency}
              order={order}
            />
          ))}
          <div className="flex justify-between items-center pt-2 border-t">
            <span className="font-semibold text-sm">{t('customer_portal:orderDetail.total')}</span>
            <span className="text-base font-bold">
              {fmtCurrency(order.total, order.currency, i18n.language)}
            </span>
          </div>
        </CardContent>
      </Card>

      {/* Notes */}
      {order.notes && (
        <Card>
          <CardContent className="py-3 px-4">
            <p className="text-xs text-muted-foreground mb-1">{t('customer_portal:orderDetail.notesHeading')}</p>
            <p className="text-sm">{order.notes}</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
