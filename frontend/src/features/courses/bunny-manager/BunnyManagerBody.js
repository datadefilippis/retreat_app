/**
 * BunnyManagerBody — the shared body that renders the right view for
 * the current mode. Used by both `BunnyManagerCard` (inline) and
 * `BunnyManagerDialog` (modal). Identical content + identical
 * behavior — only the chrome (Card vs Dialog) changes.
 *
 * Modes (resolved by useBunnyManager):
 *   - 'migrate' → BunnyLegacyBanner
 *   - 'empty'   → BunnyEmptyState
 *   - 'list'    → header + library list + "+ Aggiungi" button
 *   - 'edit'    → BunnyLibraryForm
 */

import React from 'react';
import { useTranslation } from 'react-i18next';
import BunnyLibraryRow from './components/BunnyLibraryRow';
import BunnyLibraryForm from './components/BunnyLibraryForm';
import BunnyLegacyBanner from './components/BunnyLegacyBanner';
import BunnyEmptyState from './components/BunnyEmptyState';


export default function BunnyManagerBody({ manager, saving = false, testing = false }) {
  const { t } = useTranslation('products');
  const {
    mode, libraries, loading, editTarget, testingIds,
    setEditTarget,
    migrate,
    testLibrary,
    testCredentialsAdHoc,
    setDefaultLibrary,
    deleteLibrary,
    createLibrary,
    updateLibrary,
  } = manager;

  if (loading) {
    return (
      <div className="text-xs text-gray-400 py-4">
        {t('dashboards.course.bunnyManager.loading')}
      </div>
    );
  }

  /* ─── EDIT mode ──────────────────────────────────────────────────── */
  if (mode === 'edit') {
    const handleSave = async (payload) => {
      const isCreate = !editTarget?.id;
      if (isCreate) {
        await createLibrary(payload);
      } else {
        await updateLibrary(editTarget.id, payload);
      }
      setEditTarget(null);  // back to list
    };
    return (
      <BunnyLibraryForm
        target={editTarget}
        onCancel={() => setEditTarget(null)}
        onSave={handleSave}
        onTestAdHoc={testCredentialsAdHoc}
        onTestSaved={testLibrary}
        saving={saving}
        testing={testing}
      />
    );
  }

  /* ─── MIGRATE mode (legacy banner) ───────────────────────────────── */
  if (mode === 'migrate') {
    return <BunnyLegacyBanner onMigrate={migrate} />;
  }

  /* ─── EMPTY mode (no config at all) ──────────────────────────────── */
  if (mode === 'empty') {
    return <BunnyEmptyState onAdd={() => setEditTarget({})} />;
  }

  /* ─── LIST mode (1+ libraries) ───────────────────────────────────── */
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-sm font-semibold text-gray-900 flex items-center gap-2">
          {t('dashboards.course.bunnyManager.listHeader')}
        </h3>
        <button
          type="button"
          onClick={() => setEditTarget({})}
          className="rounded-md border border-gray-300 bg-white text-gray-800 hover:bg-gray-50 text-xs font-semibold px-3 py-1.5"
        >
          {t('dashboards.course.bunnyManager.addLibraryBtn')}
        </button>
      </div>

      <ul className="space-y-2">
        {libraries.map(lib => (
          <BunnyLibraryRow
            key={lib.id}
            library={lib}
            isTesting={!!testingIds[lib.id]}
            onTest={testLibrary}
            onEdit={(l) => setEditTarget(l)}
            onDelete={deleteLibrary}
            onSetDefault={setDefaultLibrary}
          />
        ))}
      </ul>

      {libraries.length > 1 && (
        <p className="text-[11px] text-gray-500 border-t border-gray-100 pt-3" dangerouslySetInnerHTML={{ __html: t('dashboards.course.bunnyManager.defaultHint') }} />
      )}
    </div>
  );
}
