/**
 * OrderItemDigital — order line for `item_type=digital`.
 *
 * Renders, for each issued download on this line:
 *   - file name + formatted size
 *   - usage counter ("3 / 10 download usati") when max_downloads is set
 *   - expiry hint when expires_at is in the future
 *   - status badge (active / exhausted / cancelled)
 *   - "Scarica →" CTA -> /d/<access_token>
 *
 * The /d/<token> landing handles the actual signed download — we just
 * navigate to it. The customer's click count is incremented server-side
 * by that landing.
 *
 * Empty / fallback follows the same three-case pattern as other
 * issued-aware renderers.
 */

import React from 'react';
import { useTranslation } from 'react-i18next';
import OrderItemBase from './OrderItemBase';


function fmtBytes(n) {
  const num = Number(n);
  if (!num || num <= 0) return '';
  const kb = num / 1024;
  if (kb < 1024) return `${kb.toFixed(0)} KB`;
  const mb = kb / 1024;
  if (mb < 1024) return `${mb.toFixed(1)} MB`;
  return `${(mb / 1024).toFixed(2)} GB`;
}


function fmtDate(iso, locale = 'it-IT') {
  if (!iso) return '';
  try {
    return new Date(iso).toLocaleDateString(locale, {
      day: '2-digit', month: 'long', year: 'numeric',
    });
  } catch { return iso.slice(0, 10); }
}


function downloadStatusBadge(status, downloadCount, maxDownloads, t) {
  if (status === 'cancelled') {
    return { label: t('customer_portal:orderItemDigital.status.cancelled'), classes: 'bg-red-50 text-red-700 border-red-200' };
  }
  if (status === 'exhausted') {
    return { label: t('customer_portal:orderItemDigital.status.exhausted'), classes: 'bg-amber-50 text-amber-700 border-amber-200' };
  }
  // active — show usage when capped
  if (maxDownloads) {
    return {
      label: t('customer_portal:orderItemDigital.status.usage', { used: downloadCount || 0, max: maxDownloads }),
      classes: 'bg-blue-50 text-blue-700 border-blue-200',
    };
  }
  return { label: t('customer_portal:orderItemDigital.status.available'), classes: 'bg-blue-50 text-blue-700 border-blue-200' };
}


export default function OrderItemDigital({ item, currency = 'EUR', order = null }) {
  const { t, i18n } = useTranslation('customer_portal');
  const allDownloads = (order && order._issued_downloads) || [];
  const lineDownloads = allDownloads.filter(d => d.product_id === item.product_id);

  const hasIssuedField = order && Array.isArray(order._issued_downloads);
  if (!hasIssuedField) {
    return <OrderItemBase item={item} currency={currency} />;
  }

  if (lineDownloads.length === 0) {
    return (
      <OrderItemBase item={item} currency={currency}>
        <div className="mt-2 rounded-md border border-dashed border-amber-300 bg-amber-50 px-3 py-2 text-xs text-amber-900">
          {t('customer_portal:orderItemDigital.pendingHint')}
        </div>
      </OrderItemBase>
    );
  }

  return (
    <OrderItemBase item={item} currency={currency}>
      <ul className="mt-2 space-y-1.5">
        {lineDownloads.map((d) => {
          const badge = downloadStatusBadge(d.status, d.download_count, d.max_downloads, t);
          const url = d.access_token ? `/d/${d.access_token}` : null;
          const filename = d.download_filename || t('customer_portal:orderItemDigital.fallbackFilename');
          const size = fmtBytes(d.download_size_bytes);
          const expiresLabel = d.expires_at ? t('customer_portal:orderItemDigital.expiresLabel', { date: fmtDate(d.expires_at, i18n.language) }) : '';
          const isAccessible = d.status === 'active';
          return (
            <li
              key={d.id || d.code}
              className="rounded-lg border border-gray-200 bg-white px-3 py-2 flex items-start gap-3"
            >
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-gray-900 truncate">📦 {filename}</p>
                <div className="text-[11px] text-muted-foreground mt-0.5 space-x-1.5">
                  {size && <span>{size}</span>}
                  {expiresLabel && (
                    <>
                      {size && <span aria-hidden>·</span>}
                      <span>{expiresLabel}</span>
                    </>
                  )}
                </div>
                <div className="flex items-center gap-2 mt-1">
                  <span className="font-mono text-[10px] text-muted-foreground">{d.code}</span>
                  <span
                    className={`px-1.5 py-0.5 text-[10px] font-medium rounded border ${badge.classes}`}
                  >
                    {badge.label}
                  </span>
                </div>
              </div>
              {url && isAccessible && (
                <a
                  href={url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="shrink-0 inline-flex items-center gap-1 px-3 py-1.5 rounded-md bg-gray-900 text-white text-xs font-semibold hover:bg-gray-800 transition-colors"
                >
                  {t('customer_portal:orderItemDigital.downloadCta')}
                </a>
              )}
            </li>
          );
        })}
      </ul>
    </OrderItemBase>
  );
}
