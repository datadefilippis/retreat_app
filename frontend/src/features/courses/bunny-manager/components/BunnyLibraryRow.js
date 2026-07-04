/**
 * BunnyLibraryRow — single library card in the list view.
 *
 * Pure presentational. Receives the library doc and a bag of action
 * handlers from the parent (orchestrator). The orchestrator is either
 * `BunnyManagerDialog` (modal) or `BunnyManagerCard` (inline) — both
 * pull the actions from `useBunnyManager`.
 *
 * Renders:
 *   - Alias + ⭐ Default flag + status badge
 *   - Library_id + video_count + "ultimo controllo X min fa"
 *   - Actionable error message when status is non-OK
 *   - Action buttons: Test / Set default / Edit / Delete
 */

import React from 'react';
import { useTranslation } from 'react-i18next';
import BunnyStatusBadge from './BunnyStatusBadge';
import { formatTimeAgo } from '../visuals';


export default function BunnyLibraryRow({
  library,
  isTesting = false,
  onTest,
  onEdit,
  onDelete,
  onSetDefault,
}) {
  const { t } = useTranslation('products');
  const status = library.last_verification_status || 'unknown';
  const isOk = status === 'ok';
  const lastVerifiedAgo = formatTimeAgo(library.last_verified_at, t);

  return (
    <li className="rounded-lg border border-gray-200 p-3 space-y-2">
      <div className="flex items-start gap-3 flex-wrap">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-semibold text-gray-900 truncate">
              {library.alias}
            </span>
            {library.is_default && (
              <span className="inline-flex items-center rounded-full bg-blue-100 text-blue-900 px-2 py-0.5 text-[10px] font-semibold">
                {t('dashboards.course.bunnyManager.defaultBadge')}
              </span>
            )}
            <BunnyStatusBadge status={status} />
          </div>
          <p className="text-[11px] text-gray-500 mt-0.5">
            library_id <code className="font-mono">{library.library_id}</code>
            {isOk && library.video_count != null && (
              <> · <span className="tabular-nums">{library.video_count}</span> {t('dashboards.course.bunnyManager.videoSuffix')}</>
            )}
            {lastVerifiedAgo && <> · {lastVerifiedAgo}</>}
          </p>
          {!isOk && library.last_verification_error && (
            <p className="text-[11px] text-red-700 mt-1 leading-relaxed">
              {library.last_verification_error}
            </p>
          )}
        </div>

        <div className="flex items-center gap-1.5 shrink-0">
          <button
            type="button"
            onClick={() => onTest?.(library)}
            disabled={isTesting}
            className="text-xs font-semibold text-gray-700 hover:text-gray-900 disabled:opacity-50 px-2 py-1"
            title={t('dashboards.course.bunnyManager.testTitle')}
          >
            {isTesting ? t('dashboards.course.bunnyManager.testingBtn') : t('dashboards.course.bunnyManager.testBtn')}
          </button>
          {!library.is_default && (
            <button
              type="button"
              onClick={() => onSetDefault?.(library)}
              className="text-xs font-semibold text-blue-700 hover:text-blue-900 px-2 py-1"
              title={t('dashboards.course.bunnyManager.setDefaultTitle')}
            >
              {t('dashboards.course.bunnyManager.setDefaultBtn')}
            </button>
          )}
          <button
            type="button"
            onClick={() => onEdit?.(library)}
            className="text-xs font-semibold text-gray-700 hover:text-gray-900 px-2 py-1"
          >
            {t('dashboards.course.bunnyManager.editBtn')}
          </button>
          <button
            type="button"
            onClick={() => onDelete?.(library)}
            className="text-xs font-semibold text-red-700 hover:text-red-900 px-2 py-1"
            title={t('dashboards.course.bunnyManager.removeTitle')}
          >
            ×
          </button>
        </div>
      </div>
    </li>
  );
}
