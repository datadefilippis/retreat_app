/**
 * DraftRestoreBanner — shown at the top of a wizard when a saved draft
 * is detected on mount. Pairs with useWizardDraft.
 *
 * 2026-05-20 — Standardised look across all 5 wizards so the merchant
 * immediately recognises the affordance.
 *
 * Usage:
 *
 *   const { hasDraft, restore, discard, savedAt } = useWizardDraft({...});
 *
 *   {hasDraft && (
 *     <DraftRestoreBanner
 *       savedAt={savedAt}
 *       onRestore={restore}
 *       onDiscard={discard}
 *     />
 *   )}
 */

import React from 'react';
import { useTranslation } from 'react-i18next';
import { History, X } from 'lucide-react';

import { Button } from './button';


function _relativeAgo(savedAt) {
  if (!savedAt) return '';
  const minutes = Math.max(1, Math.round((Date.now() - savedAt) / 60_000));
  if (minutes < 60) return `${minutes} min`;
  const hours = Math.round(minutes / 60);
  return `${hours}h`;
}


export function DraftRestoreBanner({ savedAt, onRestore, onDiscard }) {
  const { t } = useTranslation('products');
  const ago = _relativeAgo(savedAt);

  return (
    <div className="flex items-start gap-3 rounded-md border border-blue-200 bg-blue-50 px-4 py-3 dark:border-blue-900/40 dark:bg-blue-900/20">
      <History className="h-4 w-4 mt-0.5 text-blue-700 dark:text-blue-300 shrink-0" />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-blue-900 dark:text-blue-200 leading-snug">
          {t('wizards.common.draft.title', {
            defaultValue: 'Bozza non salvata disponibile',
          })}
        </p>
        <p className="text-xs text-blue-800 dark:text-blue-300 mt-0.5 leading-snug">
          {t('wizards.common.draft.subtitle', {
            defaultValue:
              'Hai iniziato a compilare un form {{ago}} fa. Vuoi riprendere o ricominciare?',
            ago,
          })}
        </p>
        <div className="mt-2 flex flex-wrap gap-2">
          <Button
            type="button"
            size="sm"
            variant="default"
            onClick={onRestore}
            className="h-8 text-xs"
          >
            {t('wizards.common.draft.restore', { defaultValue: 'Riprendi bozza' })}
          </Button>
          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={onDiscard}
            className="h-8 text-xs"
          >
            <X className="h-3 w-3 mr-1" />
            {t('wizards.common.draft.discard', { defaultValue: 'Scarta bozza' })}
          </Button>
        </div>
      </div>
    </div>
  );
}


export default DraftRestoreBanner;
