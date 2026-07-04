/**
 * useBunnyManager — single hook that powers the unified Bunny UI.
 *
 * Every surface (BunnyManagerDialog, BunnyManagerCard, future widgets
 * like BunnyStatusWidget) consumes this hook. Centralizes data
 * fetching, mode resolution, and CRUD actions so adding a new entry
 * point is "import + call hook".
 *
 * Mode resolver:
 *   - editTarget !== null         → 'edit'  (form, internal modal state)
 *   - libraries.length > 0        → 'list'  (multi-library list)
 *   - legacy `bunny` populated    → 'migrate' (promote-to-multi banner)
 *   - everything else             → 'empty' (first-library CTA)
 *
 * Why one hook instead of separate fetchers + actions:
 *   - Modes share the same data (libraries + legacy detection)
 *   - The dialog and the inline card share identical body — they MUST
 *     have identical state to render identically
 *   - Adding a new entry point should be free (no fetch logic to copy)
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';
import { bunnyIntegrationAPI } from '../../../api/courses';
import { organizationsAPI } from '../../../api/organizations';


/**
 * @returns {{
 *   mode: 'migrate'|'empty'|'list'|'edit',
 *   libraries: Array<object>,
 *   legacy: object|null,
 *   loading: boolean,
 *   editTarget: object|null,
 *   testingIds: object,
 *   setEditTarget: (target: object|null) => void,
 *   refresh: () => Promise<void>,
 *   migrate: () => Promise<void>,
 *   testLibrary: (lib: object, payloadOverride?: object) => Promise<object|null>,
 *   testCredentialsAdHoc: (payload: object) => Promise<object|null>,
 *   setDefaultLibrary: (lib: object) => Promise<void>,
 *   deleteLibrary: (lib: object) => Promise<boolean>,
 *   createLibrary: (payload: object) => Promise<object>,
 *   updateLibrary: (id: string, payload: object) => Promise<object>,
 * }}
 */
export default function useBunnyManager() {
  const { t } = useTranslation('products');
  const [libraries, setLibraries] = useState([]);
  const [legacy, setLegacy] = useState(null);
  const [loading, setLoading] = useState(true);
  // Ephemeral edit-mode state. null = list view, {} = create new,
  // {id, alias, ...} = edit existing.
  const [editTarget, setEditTarget] = useState(null);
  // Map of `library.id → boolean` for in-flight test probes. Lets the
  // list show per-row "Verifico…" without disabling the whole UI.
  const [testingIds, setTestingIds] = useState({});

  /* ─── Data fetch ───────────────────────────────────────────────── */

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      // Two parallel calls: one for the libraries array, one for the
      // legacy detection (org doc has `integrations.bunny`).
      const [libsRes, orgRes] = await Promise.all([
        bunnyIntegrationAPI.libraries.list().catch(() => ({ data: { libraries: [] } })),
        organizationsAPI.getCurrent().catch(() => ({ data: null })),
      ]);
      setLibraries(libsRes.data?.libraries || []);
      const legacyBunny = orgRes.data?.integrations?.bunny;
      // Legacy is "populated" when the credential fields exist. Empty
      // object or { bunny: null } both count as no legacy.
      setLegacy(legacyBunny?.library_id ? legacyBunny : null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  /* ─── Derived: mode resolver ───────────────────────────────────── */

  const mode = useMemo(() => {
    if (editTarget !== null) return 'edit';
    if (libraries.length > 0) return 'list';
    if (legacy) return 'migrate';
    return 'empty';
  }, [editTarget, libraries.length, legacy]);

  /* ─── Actions ──────────────────────────────────────────────────── */

  /**
   * Promote legacy `bunny` field to `bunny_libraries[0]`. Idempotent
   * server-side — calling on a non-legacy org returns 'noop'.
   */
  const migrate = useCallback(async () => {
    if (!window.confirm(t('dashboards.course.bunnyManager.toasts.migrateConfirm'))) return;
    try {
      const { data } = await bunnyIntegrationAPI.migrateLegacy();
      if (data?.status === 'migrated') {
        toast.success(t('dashboards.course.bunnyManager.toasts.migrated'));
      } else {
        toast.info(data?.message || t('dashboards.course.bunnyManager.toasts.noMigrationNeeded'));
      }
      await refresh();
    } catch (e) {
      const d = e?.response?.data?.detail;
      toast.error(typeof d === 'string' ? d : t('dashboards.course.bunnyManager.toasts.migrateError'));
    }
  }, [refresh, t]);

  /**
   * Probe a SAVED library against Bunny without persisting. Returns
   * the probe result for the caller to display, plus shows a toast
   * with the outcome. Sets per-id testing flag for UI feedback.
   */
  const testLibrary = useCallback(async (lib, payloadOverride = null) => {
    if (!lib?.id) return null;
    setTestingIds(s => ({ ...s, [lib.id]: true }));
    try {
      const { data } = await bunnyIntegrationAPI.libraries.test(lib.id, payloadOverride);
      if (data.status === 'ok') {
        toast.success(
          data.video_count != null
            ? t('dashboards.course.bunnyManager.toasts.connectedWithCount', { alias: lib.alias, count: data.video_count })
            : t('dashboards.course.bunnyManager.toasts.connected', { alias: lib.alias }),
        );
      } else if (data.error_message) {
        toast.error(`${lib.alias}: ${data.error_message}`);
      }
      // Reload to pick up any status change a parallel PATCH may have
      // written (defensive: tests don't persist but admin actions do).
      await refresh();
      return data;
    } catch (e) {
      const d = e?.response?.data?.detail;
      toast.error(typeof d === 'string' ? d : t('dashboards.course.bunnyManager.toasts.testError'));
      return null;
    } finally {
      setTestingIds(s => ({ ...s, [lib.id]: false }));
    }
  }, [refresh, t]);

  /**
   * Probe arbitrary credentials (used by the create-library form
   * before the library has been saved). Reuses the legacy single-
   * library /test endpoint which accepts arbitrary payloads.
   */
  const testCredentialsAdHoc = useCallback(async (payload) => {
    try {
      const { data } = await bunnyIntegrationAPI.testConnection(payload);
      if (data.status === 'ok') {
        toast.success(
          data.video_count != null
            ? t('dashboards.course.bunnyManager.toasts.adHocConnectedWithCount', { count: data.video_count })
            : t('dashboards.course.bunnyManager.toasts.adHocConnected'),
        );
      } else if (data.error_message) {
        toast.error(data.error_message);
      }
      return data;
    } catch (e) {
      const d = e?.response?.data?.detail;
      toast.error(typeof d === 'string' ? d : t('dashboards.course.bunnyManager.toasts.testError'));
      return null;
    }
  }, [t]);

  const setDefaultLibrary = useCallback(async (lib) => {
    if (!lib?.id || lib.is_default) return;
    try {
      await bunnyIntegrationAPI.libraries.setDefault(lib.id);
      toast.success(t('dashboards.course.bunnyManager.toasts.setDefaultSuccess', { alias: lib.alias }));
      await refresh();
    } catch {
      toast.error(t('dashboards.course.bunnyManager.toasts.setDefaultError'));
    }
  }, [refresh, t]);

  const deleteLibrary = useCallback(async (lib) => {
    if (!lib?.id) return false;
    if (!window.confirm(t('dashboards.course.bunnyManager.toasts.deleteConfirm', { alias: lib.alias }))) return false;
    try {
      await bunnyIntegrationAPI.libraries.remove(lib.id);
      toast.success(t('dashboards.course.bunnyManager.toasts.deleted', { alias: lib.alias }));
      await refresh();
      return true;
    } catch (e) {
      const d = e?.response?.data?.detail;
      if (typeof d === 'object' && d?.error === 'library_in_use') {
        toast.error(d.message);
      } else {
        toast.error(typeof d === 'string' ? d : t('dashboards.course.bunnyManager.toasts.deleteError'));
      }
      return false;
    }
  }, [refresh, t]);

  const createLibrary = useCallback(async (payload) => {
    try {
      const { data } = await bunnyIntegrationAPI.libraries.create(payload);
      // Surface the auto-verify outcome to the caller (form decides
      // whether to celebrate or warn).
      if (data?.last_verification_status === 'ok') {
        toast.success(
          data.video_count != null
            ? t('dashboards.course.bunnyManager.toasts.createConnectedWithCount', { alias: data.alias, count: data.video_count })
            : t('dashboards.course.bunnyManager.toasts.createSavedAlias', { alias: data.alias }),
        );
      } else if (data?.last_verification_error) {
        toast.warning(t('dashboards.course.bunnyManager.toasts.savedWithWarning', { error: data.last_verification_error }));
      } else {
        toast.success(t('dashboards.course.bunnyManager.toasts.configSaved'));
      }
      await refresh();
      return data;
    } catch (e) {
      const d = e?.response?.data?.detail;
      toast.error(typeof d === 'string' ? d : t('dashboards.course.bunnyManager.toasts.saveError'));
      throw e;
    }
  }, [refresh, t]);

  const updateLibrary = useCallback(async (id, payload) => {
    try {
      const { data } = await bunnyIntegrationAPI.libraries.update(id, payload);
      if (data?.last_verification_status === 'ok') {
        toast.success(t('dashboards.course.bunnyManager.toasts.updated', { alias: data.alias }));
      } else if (data?.last_verification_error) {
        toast.warning(t('dashboards.course.bunnyManager.toasts.savedWithWarning', { error: data.last_verification_error }));
      } else {
        toast.success(t('dashboards.course.bunnyManager.toasts.updatedGeneric'));
      }
      await refresh();
      return data;
    } catch (e) {
      const d = e?.response?.data?.detail;
      toast.error(typeof d === 'string' ? d : t('dashboards.course.bunnyManager.toasts.saveError'));
      throw e;
    }
  }, [refresh, t]);

  return {
    // state
    mode,
    libraries,
    legacy,
    loading,
    editTarget,
    testingIds,
    // controls
    setEditTarget,
    refresh,
    // actions
    migrate,
    testLibrary,
    testCredentialsAdHoc,
    setDefaultLibrary,
    deleteLibrary,
    createLibrary,
    updateLibrary,
  };
}
