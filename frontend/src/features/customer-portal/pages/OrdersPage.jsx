/**
 * OrdersPage — list of the customer's orders.
 *
 * Phase 3 of the customer area refactor: this page replaces the
 * inline `CustomerPortalPage` body that used to live in
 * CustomerPortalPages.js. The chrome (TopBar + Sidebar + email
 * verify banner) now comes from CustomerLayout, so this page only
 * renders its own concern: title + list of orders.
 *
 * Data fetching delegated to the `useMyOrders` hook (handles auto-
 * retry, 401 silent, inline error state). Rendering uses the
 * extracted `<OrderCard />` and `<EmptyState />` atoms — no inline
 * Card markup duplicated.
 */

import React from 'react';
import { useTranslation } from 'react-i18next';
import { useCustomerAuth } from '../../../context/CustomerAuthContext';
import useMyOrders from '../hooks/useMyOrders';
import OrderCard from '../components/OrderCard';
import OrderCardSkeleton from '../components/skeletons/OrderCardSkeleton';
import EmptyState from '../components/EmptyState';
import PageHeader from '../components/PageHeader';


export default function OrdersPage() {
  const { storeSlug } = useCustomerAuth();
  const { orders, loading, error, retry } = useMyOrders();
  const { t } = useTranslation('customer_portal');

  return (
    <div className="space-y-4">
      <PageHeader
        title={t('customer_portal:orders.title')}
        description={t('customer_portal:orders.description')}
      />

      {/* Inline error banner with retry — supersedes the previous
          transient toast pattern. The banner stays visible until
          the customer retries successfully. Phase 7 polish: softer
          copy ("non sono riuscito" reads less alarmist than the
          earlier "non riuscito"; "tra un momento" covers all
          transient causes without guessing connection issues). */}
      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-3 flex items-start gap-3">
          <span aria-hidden className="text-xl shrink-0">⚠️</span>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-red-900">{t('customer_portal:orders.errorTitle')}</p>
            <p className="text-xs text-red-800 mt-0.5">{t('customer_portal:orders.errorBody')}</p>
          </div>
          <button
            type="button"
            onClick={retry}
            className="rounded-md border border-red-300 bg-white text-red-900 hover:bg-red-100 text-xs font-semibold px-3 py-1.5"
          >
            {t('customer_portal:orders.retry')}
          </button>
        </div>
      )}

      {loading ? (
        // Phase 7 polish — skeleton list instead of a centered spinner.
        // Three placeholders feel "populated enough" without scrolling
        // off-screen. The real list will replace them in the same
        // vertical slots, avoiding layout shift.
        <div className="space-y-2" role="status" aria-busy="true" aria-label={t('customer_portal:orders.loadingAria')}>
          {[1, 2, 3].map(i => <OrderCardSkeleton key={i} />)}
        </div>
      ) : orders.length === 0 && !error ? (
        <EmptyState
          icon="🧾"
          title={t('customer_portal:orders.emptyTitle')}
          description={t('customer_portal:orders.emptyDescription')}
          cta={storeSlug ? { to: `/s/${storeSlug}`, label: t('customer_portal:orders.exploreCatalog') } : null}
        />
      ) : orders.length > 0 ? (
        <div className="space-y-2">
          {orders.map(order => <OrderCard key={order.id} order={order} />)}
        </div>
      ) : null}
    </div>
  );
}
