/**
 * BunnyEmptyState — "Configura la prima libreria" CTA.
 *
 * Shown when the org has neither `integrations.bunny` nor
 * `bunny_libraries[]` (cold-start org that's never touched Bunny).
 *
 * Pure presentational — the orchestrator wires the "+ Aggiungi" action.
 */

import React from 'react';
import { useTranslation } from 'react-i18next';


export default function BunnyEmptyState({ onAdd }) {
  const { t } = useTranslation('products');
  return (
    <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 flex items-start gap-3">
      <span aria-hidden className="text-2xl">🐰</span>
      <div className="flex-1 min-w-0">
        <h3 className="text-sm font-semibold text-amber-900">
          {t('dashboards.course.bunnyManager.empty.title')}
        </h3>
        <p className="text-xs text-amber-800 mt-1 leading-relaxed">
          {t('dashboards.course.bunnyManager.empty.text')}
        </p>
      </div>
      <button
        type="button"
        onClick={onAdd}
        className="rounded-md bg-amber-900 text-white text-sm font-semibold px-3 py-1.5 hover:bg-amber-800 whitespace-nowrap"
      >
        {t('dashboards.course.bunnyManager.empty.addBtn')}
      </button>
    </div>
  );
}
