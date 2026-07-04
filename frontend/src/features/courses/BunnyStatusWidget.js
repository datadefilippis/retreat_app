/**
 * BunnyStatusWidget — compact "Stato Bunny" card for the CourseEditor
 * sidebar. Shows the status of the org's DEFAULT library at a glance
 * + a button to open the unified `BunnyManagerDialog` for managing
 * everything.
 *
 * Step 5 of the UI unification: this widget used to be tied to the
 * legacy single-library `org.integrations.bunny` field. Now it
 * consumes `useBunnyManager` like every other Bunny surface, picks
 * the right "primary library" (default if any, first if no default,
 * legacy fallback otherwise), and renders the same status badge
 * everyone else uses.
 *
 * The "Modifica" button no longer opens a dialog scoped to a single
 * library — it opens the full multi-library manager so the admin can
 * see / add / remove / set-default any library, not just the one in
 * focus on this sidebar.
 */

import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import useBunnyManager from './bunny-manager/useBunnyManager';
import BunnyManagerDialog from './bunny-manager/BunnyManagerDialog';
import BunnyStatusBadge from './bunny-manager/components/BunnyStatusBadge';
import { maskKey } from './bunny-manager/visuals';


/**
 * Pick the "primary" library to surface in the compact widget.
 * Mirrors the resolver priority on the backend:
 *   1. The default library (`is_default=true`)
 *   2. The first library if no default is marked
 *   3. The legacy `bunny` field (when no multi-library exists)
 *   4. null (nothing configured)
 */
function pickPrimary({ libraries, legacy, legacyAlias }) {
  if (libraries && libraries.length > 0) {
    const def = libraries.find(l => l.is_default);
    return def || libraries[0];
  }
  if (legacy) {
    return {
      // Legacy doesn't have alias — invent one for display only.
      alias: legacyAlias,
      library_id: legacy.library_id,
      api_key: legacy.api_key,
      watermark_enabled: legacy.watermark_enabled,
      last_verification_status: legacy.last_verification_status,
      last_verification_error: legacy.last_verification_error,
      video_count: legacy.video_count,
      _isLegacy: true,
    };
  }
  return null;
}


export default function BunnyStatusWidget() {
  const { t } = useTranslation('products');
  const manager = useBunnyManager();
  const [open, setOpen] = useState(false);

  if (manager.loading) {
    return (
      <div className="bg-white border border-gray-200 rounded-xl shadow-sm p-3 text-xs text-gray-400">
        {t('dashboards.course.bunnyWidget.loading')}
      </div>
    );
  }

  const primary = pickPrimary({
    libraries: manager.libraries,
    legacy: manager.legacy,
    legacyAlias: t('dashboards.course.bunnyWidget.legacyAlias'),
  });

  // Empty state — no Bunny configured at any level.
  if (!primary) {
    return (
      <>
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-3 space-y-2">
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-amber-900 flex items-center gap-2">
              {t('dashboards.course.bunnyWidget.header')}
            </span>
            <BunnyStatusBadge status="not_configured" />
          </div>
          <p className="text-[11px] text-amber-800">
            {t('dashboards.course.bunnyWidget.emptyDesc')}
          </p>
          <button
            type="button"
            onClick={() => setOpen(true)}
            className="w-full rounded-md bg-amber-900 text-white hover:bg-amber-800 text-xs font-semibold px-3 py-1.5"
          >
            {t('dashboards.course.bunnyWidget.configureBtn')}
          </button>
        </div>
        <BunnyManagerDialog open={open} onClose={() => setOpen(false)} />
      </>
    );
  }

  const status = primary.last_verification_status || 'unknown';
  const isOk = status === 'ok';
  const libCount = manager.libraries.length;

  return (
    <>
      <div className={`bg-white border rounded-xl shadow-sm p-3 space-y-2 ${
        isOk ? 'border-gray-200' : 'border-red-200'
      }`}>
        <div className="flex items-center justify-between gap-2">
          <span className="text-sm font-semibold text-gray-900 flex items-center gap-2 truncate">
            🐰 {primary.alias}
            {primary.is_default && (
              <span className="text-[10px] text-blue-700">⭐</span>
            )}
          </span>
          <BunnyStatusBadge status={status} />
        </div>

        {isOk && primary.video_count != null && (
          <p className="text-[11px] text-gray-500">
            {t('dashboards.course.bunnyWidget.videoCount', { count: primary.video_count })}
          </p>
        )}
        {!isOk && primary.last_verification_error && (
          <p className="text-[11px] text-red-700 leading-relaxed">
            {primary.last_verification_error}
          </p>
        )}

        <dl className="grid grid-cols-[80px_1fr] gap-x-2 gap-y-0.5 text-[11px] text-gray-700">
          <dt className="text-gray-500">{t('dashboards.course.bunnyWidget.labelLibrary')}</dt>
          <dd className="font-mono">{primary.library_id}</dd>
          <dt className="text-gray-500">{t('dashboards.course.bunnyWidget.labelApiKey')}</dt>
          <dd className="font-mono">{maskKey(primary.api_key)}</dd>
          <dt className="text-gray-500">{t('dashboards.course.bunnyWidget.labelWatermark')}</dt>
          <dd>{primary.watermark_enabled ? t('dashboards.course.bunnyWidget.watermarkOn') : t('dashboards.course.bunnyWidget.watermarkOff')}</dd>
        </dl>

        {/* Hint when the org has more libraries than the one shown */}
        {libCount > 1 && (
          <p className="text-[10px] text-gray-500 border-t border-gray-100 pt-2">
            {t('dashboards.course.bunnyWidget.moreLibraries', { count: libCount - 1 })}
          </p>
        )}

        <button
          type="button"
          onClick={() => setOpen(true)}
          className="w-full rounded-md border border-gray-300 bg-white text-gray-800 hover:bg-gray-50 text-xs font-semibold px-3 py-1.5"
        >
          {primary._isLegacy ? t('dashboards.course.bunnyWidget.manageLegacy') : t('dashboards.course.bunnyWidget.manageMulti')}
        </button>
      </div>
      <BunnyManagerDialog open={open} onClose={() => setOpen(false)} />
    </>
  );
}
