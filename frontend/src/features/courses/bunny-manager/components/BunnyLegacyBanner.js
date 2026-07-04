/**
 * BunnyLegacyBanner — "Promuovi a multi-library" CTA.
 *
 * Shown when the org has the legacy `integrations.bunny` field
 * populated AND no `bunny_libraries[]` (the typical "I configured
 * Bunny once and now I want to add a second library" state).
 *
 * Pure presentational — the orchestrator wires the migrate action.
 */

import React from 'react';
import { useTranslation } from 'react-i18next';


export default function BunnyLegacyBanner({ onMigrate, onCancel = null }) {
  const { t } = useTranslation('products');
  return (
    <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 space-y-3">
      <div className="flex items-start gap-3">
        <span aria-hidden className="text-2xl">🐰</span>
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-semibold text-blue-900">
            {t('dashboards.course.bunnyManager.legacy.title')}
          </h3>
          <p className="text-xs text-blue-800 mt-1 leading-relaxed">
            {t('dashboards.course.bunnyManager.legacy.text')}
          </p>
        </div>
      </div>
      <div className="flex items-center justify-end gap-2">
        {onCancel && (
          <button
            type="button"
            onClick={onCancel}
            className="text-sm font-semibold text-gray-600 hover:text-gray-900 px-3 py-2"
          >
            {t('dashboards.course.bunnyManager.legacy.later')}
          </button>
        )}
        <button
          type="button"
          onClick={onMigrate}
          className="rounded-md bg-blue-900 text-white text-sm font-semibold px-3 py-1.5 hover:bg-blue-800"
        >
          {t('dashboards.course.bunnyManager.legacy.promote')}
        </button>
      </div>
    </div>
  );
}
