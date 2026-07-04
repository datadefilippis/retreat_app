/**
 * OrderCard — single order row used in the orders list (and on the
 * upcoming HomePage "Ultimi ordini" section).
 *
 * Behavior preserved 1:1 from the inline implementation in
 * CustomerPortalPages.js:
 *   - Card-level click → navigate to /account/orders/:id
 *   - When the order contains a course, an "Apri corso →" CTA appears
 *     and stops propagation, taking the customer straight to
 *     /account/courses without going through order detail.
 *   - Status badge auto-resolves with the friendly request/payment copy
 *     via the shared resolveOrderBadge helper.
 *
 * The component is presentational — orchestration (sorting, filtering,
 * paginating) stays with the parent list page.
 */

import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Card, CardContent } from '../../../components/ui/card';
import { formatAmount } from '../../../utils/currency';
import StatusBadge from './StatusBadge';
import {
  orderHasCourse, formatItemsSummary,
  getFulfillmentModeLabel, getFulfillmentStatusLabel,
} from '../utils/orderStatus';


function formatDate(iso, locale = 'it-IT') {
  if (!iso) return '';
  try {
    return new Date(iso).toLocaleDateString(locale, {
      day: '2-digit', month: 'short', year: 'numeric',
    });
  } catch { return ''; }
}


/**
 * CH compliance v1: CHF orders render Swiss-style ("CHF 1'234.50")
 * regardless of the customer's UI locale, matching the email and the
 * PDF receipt. EUR (and any other currency we may support) keep the
 * locale-aware Intl.NumberFormat output, preserving how existing
 * customer portal cards have always looked.
 */
function formatCurrency(amount, currency, locale = 'it-IT') {
  if (String(currency || '').toUpperCase() === 'CHF') {
    // Strip a region suffix like "it-CH" → "it" so formatAmount can map it.
    const shortLocale = String(locale || 'it').split('-')[0].toLowerCase();
    return formatAmount(amount || 0, 'CHF', shortLocale);
  }
  try {
    return new Intl.NumberFormat(locale, {
      style: 'currency',
      currency: currency || 'EUR',
      maximumFractionDigits: 2,
    }).format(amount || 0);
  } catch {
    const symbol = (currency || 'EUR') === 'EUR' ? '\u20AC' : (currency || '');
    return `${symbol} ${(amount || 0).toFixed(2)}`;
  }
}


export default function OrderCard({ order }) {
  const navigate = useNavigate();
  const { t, i18n } = useTranslation('customer_portal');
  const hasCourse = orderHasCourse(order);
  const date = formatDate(order.created_at, i18n.language);
  const itemsSummary = formatItemsSummary(order, t);

  const ff = order.fulfillment;
  const showFulfillment = ff && ff.mode !== 'not_required';
  const ffMode = showFulfillment ? getFulfillmentModeLabel(ff.mode, t) : null;
  const ffStatus = showFulfillment ? getFulfillmentStatusLabel(ff.status, t) : null;

  return (
    <Card
      className="hover:shadow-sm transition-shadow cursor-pointer"
      onClick={() => navigate(`/account/orders/${order.id}`)}
    >
      <CardContent className="py-3 px-4">
        <div className="flex items-center justify-between">
          <div className="space-y-0.5 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-sm font-medium">
                {order.order_number || `#${order.id.slice(0, 8)}`}
              </span>
              <StatusBadge order={order} />
              {hasCourse && (
                <StatusBadge tone="course" label={t('customer_portal:orderCard.courseBadge')} />
              )}
            </div>
            <p className="text-xs text-muted-foreground truncate">
              {date} &middot; {itemsSummary}
              {order.org_name ? ` \u2014 ${order.org_name}` : ''}
            </p>
            {showFulfillment && (
              <p className="text-[10px] text-muted-foreground/70">
                {ffMode}
                {ffStatus ? ` \u2014 ${ffStatus}` : ''}
              </p>
            )}
          </div>
          <div className="flex items-center gap-3 shrink-0">
            {hasCourse && (
              <button
                type="button"
                onClick={(e) => { e.stopPropagation(); navigate('/account/courses'); }}
                className="rounded-md bg-blue-600 text-white text-xs font-semibold px-3 py-1.5 hover:bg-blue-700 whitespace-nowrap"
              >
                {t('customer_portal:orderCard.openCourse')}
              </button>
            )}
            <span className="text-sm font-semibold whitespace-nowrap">
              {formatCurrency(order.total, order.currency, i18n.language)}
            </span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
