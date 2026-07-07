/**
 * DownloadLandingPage — public token-gated landing for a digital delivery.
 *
 * Release 3 (Digital) B9. Route: /d/:access_token
 *
 * Public (no login). Fetches GET /api/public/downloads/:token, renders the
 * right copy per status, and offers a single CTA that opens
 * GET /api/public/downloads/:token/file in a new tab — the browser handles
 * the actual download via Content-Disposition: attachment from the backend.
 *
 * States:
 *   active    → "Scarica {filename}" button + remaining count + expiry
 *   exhausted → "Hai raggiunto il limite di download"
 *   expired   → "Il link è scaduto"
 *   cancelled → "Ordine annullato"
 *   unknown   → 404-like fallback ("Link non valido")
 */

import React, { useEffect, useState } from 'react';
import { FolderDown, Lock } from 'lucide-react';
import { useParams } from 'react-router-dom';
import { Trans, useTranslation } from 'react-i18next';
import { storefrontAPI } from '../../api/storefront';
import PublicStorefrontShell from './PublicStorefrontShell';


function formatBytes(n) {
  if (!n || n <= 0) return '';
  const kb = n / 1024;
  if (kb < 1024) return `${kb.toFixed(0)} KB`;
  const mb = kb / 1024;
  if (mb < 1024) return `${mb.toFixed(1)} MB`;
  return `${(mb / 1024).toFixed(2)} GB`;
}

function formatDate(iso, locale = 'it-IT') {
  if (!iso) return '';
  try {
    const d = new Date(iso);
    return d.toLocaleDateString(locale, { day: 'numeric', month: 'long', year: 'numeric' });
  } catch { return iso; }
}


export default function DownloadLandingPage() {
  const { access_token: token } = useParams();
  const { t, i18n } = useTranslation('landings');
  const [payload, setPayload] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = () => {
    setLoading(true);
    storefrontAPI.getPublicDownload(token)
      .then(res => setPayload(res.data))
      .catch(err => {
        setError(err?.response?.status === 404 ? 'not_found' : 'generic');
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-gray-400">{t('landings:download.loading')}</div>
      </div>
    );
  }

  if (error === 'not_found' || !payload) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
        <div className="max-w-md w-full bg-white rounded-2xl shadow-sm border p-8 text-center">
          <div className="mb-3 flex justify-center"><Lock className="h-10 w-10 text-gray-300" aria-hidden /></div>
          <h1 className="text-xl font-bold text-gray-900 mb-2">{t('landings:download.invalidLink.title')}</h1>
          <p className="text-sm text-gray-600">
            {t('landings:download.invalidLink.body')}
          </p>
        </div>
      </div>
    );
  }

  const status = payload.status;
  const filename = payload.download_filename || t('landings:download.fallbackFilename');
  const sizeTxt = formatBytes(payload.download_size_bytes);

  // Build the CTA URL by piggybacking on the same client/base used elsewhere.
  // We reach the backend through the same /api prefix the customer app
  // already uses so cookies/host rules apply uniformly.
  const downloadUrl = `/api/public/downloads/${encodeURIComponent(token)}/file`;

  // Status → i18n title key. Unknown/other statuses fall back to the generic
  // "Download" heading so we never display an empty <h1>.
  const titleKeyByStatus = {
    active: 'landings:download.title.active',
    exhausted: 'landings:download.title.exhausted',
    expired: 'landings:download.title.expired',
    cancelled: 'landings:download.title.cancelled',
  };
  const title = t(titleKeyByStatus[status] || 'landings:download.title.fallback');

  // Wrap success render in PublicStorefrontShell — page picks up the
  // storefront's i18n.language instead of leaking from prior visits.
  return (
    <PublicStorefrontShell slug={payload.store_slug || null}>
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="max-w-lg w-full bg-white rounded-2xl shadow-sm border overflow-hidden">
        <div className="p-6 sm:p-8">
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-gray-500 mb-1">
            {t('landings:download.eyebrow')}
          </div>
          <h1 className="text-2xl font-bold text-gray-900 mb-1">{title}</h1>
          <p className="text-sm text-gray-600">{payload.product_name}</p>

          {/* File row — always rendered when we have filename */}
          {payload.download_filename && (
            <div className="mt-6 rounded-xl border border-gray-200 bg-gray-50 p-4">
              <div className="flex items-center gap-3">
                <FolderDown className="h-6 w-6 text-gray-500" aria-hidden />
                <div className="min-w-0 flex-1">
                  <div className="font-semibold text-gray-900 truncate">{filename}</div>
                  {sizeTxt && <div className="text-xs text-gray-500">{sizeTxt}</div>}
                </div>
              </div>
            </div>
          )}

          {/* CTA area — status-aware */}
          <div className="mt-6 space-y-2">
            {status === 'active' && (
              <>
                <a
                  href={downloadUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={() => {
                    // Refresh the payload after a short delay so the counter
                    // updates in-place. This runs in the background — if the
                    // user navigates away, nothing breaks.
                    setTimeout(load, 1500);
                  }}
                  className="block w-full rounded-md bg-[var(--sf-accent,#111827)] text-[var(--sf-accent-fg,#ffffff)] px-4 py-3 text-sm font-semibold hover:bg-[var(--sf-accent-hover,#1f2937)] text-center"
                >
                  {t('landings:download.ctaDownload')}
                </a>
                <div className="flex items-center justify-between text-xs text-gray-500 mt-2">
                  {payload.max_downloads != null ? (
                    // Trans because the count is wrapped in <strong>; <1> binds
                    // to the first child <strong> in the JSX.
                    <span>
                      <Trans
                        i18nKey="landings:download.remaining"
                        values={{ remaining: payload.downloads_remaining ?? 0, max: payload.max_downloads }}
                        components={[<strong />]}
                      />
                    </span>
                  ) : (
                    <span>{t('landings:download.unlimited')}</span>
                  )}
                  {payload.expires_at && (
                    <span>{t('landings:download.validUntil', { date: formatDate(payload.expires_at, i18n.language) })}</span>
                  )}
                </div>
              </>
            )}

            {status === 'exhausted' && (
              <div className="rounded-md bg-amber-50 border border-amber-200 px-4 py-3 text-sm text-amber-900">
                {payload.max_downloads != null
                  ? t('landings:download.exhaustedNoticeWithMax', { max: payload.max_downloads })
                  : t('landings:download.exhaustedNotice')}
              </div>
            )}

            {status === 'expired' && (
              <div className="rounded-md bg-amber-50 border border-amber-200 px-4 py-3 text-sm text-amber-900">
                {t('landings:download.expiredNotice', { date: formatDate(payload.expires_at, i18n.language) })}
              </div>
            )}

            {status === 'cancelled' && (
              <div className="rounded-md bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-900">
                {t('landings:download.cancelledNotice')}
              </div>
            )}
          </div>

          <div className="mt-6 pt-4 border-t border-gray-100 text-[11px] text-gray-400 font-mono">
            {t('landings:download.orderCodeLabel', { code: payload.code })}
          </div>
        </div>
      </div>
    </div>
    </PublicStorefrontShell>
  );
}
