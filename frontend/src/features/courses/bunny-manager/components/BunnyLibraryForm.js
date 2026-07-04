/**
 * BunnyLibraryForm — create/edit form for a single Bunny library.
 *
 * Used inside `BunnyManagerDialog`/`BunnyManagerCard` when the mode
 * is 'edit'. The orchestrator passes `target`:
 *   - `{}`       → create mode (all fields required)
 *   - `{id, …}`  → edit mode (api_key/library_id can stay blank to
 *                   preserve saved values)
 *
 * Pure form: never fetches by itself. The save/test actions are
 * delegated to the orchestrator's hook.
 */

import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';


export default function BunnyLibraryForm({
  target,
  onCancel,
  onSave,             // (payload) => Promise<library>
  onTestAdHoc,        // (payload) => Promise<probe>  // for create mode
  onTestSaved,        // (lib, payloadOverride) => Promise<probe>  // for edit mode
  saving = false,
  testing = false,
}) {
  const { t } = useTranslation('products');
  const isEdit = !!target?.id;
  const [draft, setDraft] = useState({
    alias: '',
    library_id: '',
    api_key: '',
    token_security_key: '',
    cdn_hostname: '',
    watermark_enabled: true,
  });
  const [probeResult, setProbeResult] = useState(null);

  // Seed/reset draft when target changes (open / switch library).
  useEffect(() => {
    if (!target) return;
    setDraft({
      alias: target.alias || '',
      library_id: target.library_id || '',
      api_key: '',                                // never pre-fill secrets
      token_security_key: '',
      cdn_hostname: target.cdn_hostname || '',
      watermark_enabled: target.watermark_enabled ?? true,
    });
    setProbeResult(null);
  }, [target]);

  const buildPayload = () => {
    const payload = { alias: draft.alias.trim() };
    if (draft.library_id.trim()) payload.library_id = draft.library_id.trim();
    if (draft.api_key.trim()) payload.api_key = draft.api_key.trim();
    if (draft.token_security_key.trim()) payload.token_security_key = draft.token_security_key.trim();
    // Only include cdn_hostname when it differs from saved (edit mode)
    // or is non-empty (create mode).
    if (draft.cdn_hostname.trim() !== (target?.cdn_hostname || '')) {
      payload.cdn_hostname = draft.cdn_hostname.trim() || null;
    }
    if (draft.watermark_enabled !== (target?.watermark_enabled ?? true)) {
      payload.watermark_enabled = draft.watermark_enabled;
    }
    return payload;
  };

  const handleSubmit = async () => {
    if (!draft.alias.trim()) {
      toast.error(t('dashboards.course.bunnyManager.form.aliasRequired'));
      return;
    }
    if (!isEdit) {
      if (!draft.library_id.trim() || !draft.api_key.trim()) {
        toast.error(t('dashboards.course.bunnyManager.form.credsRequired'));
        return;
      }
    }
    const payload = buildPayload();
    try {
      await onSave?.(payload);
    } catch {
      // Toast surfaced by the hook; nothing else to do here.
    }
  };

  const handleTest = async () => {
    // Build a payload that includes ALL credentials that have a value
    // in the form (incl. token_security_key + cdn_hostname). The
    // backend uses these to run the extended 3-check probe; missing
    // ones cause those specific checks to be skipped (null in the
    // checklist) — never a failure on their own. Edit-mode inherits
    // saved values for any field left blank in the draft.
    const testPayload = {};
    if (draft.library_id.trim()) testPayload.library_id = draft.library_id.trim();
    if (draft.api_key.trim()) testPayload.api_key = draft.api_key.trim();
    if (draft.token_security_key.trim()) testPayload.token_security_key = draft.token_security_key.trim();
    if (draft.cdn_hostname.trim()) testPayload.cdn_hostname = draft.cdn_hostname.trim();

    let result;
    if (isEdit) {
      result = await onTestSaved?.(target, testPayload);
    } else {
      // Create mode: no id yet; use ad-hoc probe.
      if (!testPayload.library_id || !testPayload.api_key) {
        toast.error(t('dashboards.course.bunnyManager.form.testCredsRequired'));
        return;
      }
      result = await onTestAdHoc?.(testPayload);
    }
    if (result) setProbeResult(result);
  };

  // Map the granular check booleans to a checklist line per check.
  // Each entry: { label, status: 'pass' | 'fail' | 'skipped' | 'pending' }.
  // - pass: explicit true from backend
  // - fail: explicit false (admin must act)
  // - skipped: null (e.g. embed check skipped because library is empty)
  // - pending: probe hasn't run for this layer yet
  const buildChecklist = (probe) => {
    if (!probe) return null;
    const map = (val) => {
      if (val === true) return 'pass';
      if (val === false) return 'fail';
      return 'skipped';
    };
    return [
      { key: 'api',   label: t('dashboards.course.bunnyManager.form.checkApi'),    status: map(probe.api_check_passed) },
      { key: 'embed', label: t('dashboards.course.bunnyManager.form.checkEmbed'),  status: map(probe.embed_check_passed) },
      { key: 'cdn',   label: t('dashboards.course.bunnyManager.form.checkCdn'),    status: map(probe.cdn_check_passed) },
    ];
  };

  // Headline color reflects the overall status, but the checklist below
  // tells the merchant exactly which line is broken — far more useful
  // than a single binary "ok / fail".
  const probeBadgeCls = (() => {
    if (!probeResult) return '';
    if (probeResult.status === 'ok') return 'border-emerald-200 bg-emerald-50 text-emerald-900';
    if (probeResult.status === 'no_videos') return 'border-amber-200 bg-amber-50 text-amber-900';
    return 'border-red-200 bg-red-50 text-red-900';
  })();

  const checklistIcon = (status) => {
    if (status === 'pass')    return <span className="text-emerald-600">✓</span>;
    if (status === 'fail')    return <span className="text-red-600">✗</span>;
    if (status === 'skipped') return <span className="text-gray-400">·</span>;
    return <span className="text-gray-300">○</span>;
  };

  return (
    <div className="space-y-3">
      <div>
        <label className="block text-xs font-semibold uppercase tracking-wider text-gray-600 mb-1">
          {t('dashboards.course.bunnyManager.form.aliasLabel')}
        </label>
        <input
          type="text"
          value={draft.alias}
          onChange={e => setDraft({ ...draft, alias: e.target.value })}
          maxLength={64}
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
          placeholder={t('dashboards.course.bunnyManager.form.aliasPlaceholder')}
          autoFocus
        />
        <p className="text-[10px] text-gray-500 mt-1">
          {t('dashboards.course.bunnyManager.form.aliasHint')}
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div>
          <label className="block text-xs font-semibold uppercase tracking-wider text-gray-600 mb-1">
            {isEdit ? t('dashboards.course.bunnyManager.form.libIdLabelEdit') : t('dashboards.course.bunnyManager.form.libIdLabelCreate')}
          </label>
          <input
            type="text"
            value={draft.library_id}
            onChange={e => setDraft({ ...draft, library_id: e.target.value })}
            maxLength={64}
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm font-mono"
            placeholder={isEdit ? (target?.library_id || '') : t('dashboards.course.bunnyManager.form.libIdPlaceholder')}
          />
        </div>
        <div>
          <label className="block text-xs font-semibold uppercase tracking-wider text-gray-600 mb-1">
            {isEdit ? t('dashboards.course.bunnyManager.form.apiKeyLabelEdit') : t('dashboards.course.bunnyManager.form.apiKeyLabelCreate')}
          </label>
          <input
            type="password"
            value={draft.api_key}
            onChange={e => setDraft({ ...draft, api_key: e.target.value })}
            maxLength={255}
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm font-mono"
            placeholder={isEdit ? t('dashboards.course.bunnyManager.form.apiKeyMaskPlaceholder') : t('dashboards.course.bunnyManager.form.apiKeyPlaceholder')}
            autoComplete="new-password"
          />
        </div>
      </div>

      <div>
        <label className="block text-xs font-semibold uppercase tracking-wider text-gray-600 mb-1">
          {isEdit ? t('dashboards.course.bunnyManager.form.tokenLabelEdit') : t('dashboards.course.bunnyManager.form.tokenLabelCreate')}
        </label>
        <input
          type="password"
          value={draft.token_security_key}
          onChange={e => setDraft({ ...draft, token_security_key: e.target.value })}
          maxLength={255}
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm font-mono"
          placeholder={isEdit ? t('dashboards.course.bunnyManager.form.apiKeyMaskPlaceholder') : t('dashboards.course.bunnyManager.form.tokenPlaceholder')}
          autoComplete="new-password"
        />
        <p className="text-[10px] text-gray-500 mt-1" dangerouslySetInnerHTML={{ __html: t('dashboards.course.bunnyManager.form.tokenHint') }} />
      </div>

      <div>
        <label className="block text-xs font-semibold uppercase tracking-wider text-gray-600 mb-1">
          {t('dashboards.course.bunnyManager.form.cdnLabel')}
        </label>
        <input
          type="text"
          value={draft.cdn_hostname}
          onChange={e => setDraft({ ...draft, cdn_hostname: e.target.value })}
          maxLength={255}
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm font-mono"
          placeholder={t('dashboards.course.bunnyManager.form.cdnPlaceholder')}
        />
      </div>

      <label className="inline-flex items-center gap-2 text-sm text-gray-700">
        <input
          type="checkbox"
          checked={!!draft.watermark_enabled}
          onChange={e => setDraft({ ...draft, watermark_enabled: e.target.checked })}
          className="rounded border-gray-300"
        />
        {t('dashboards.course.bunnyManager.form.watermarkToggle')}
      </label>

      {/* Inline probe result — shown after a manual "Testa" click.
          The 3-line checklist surfaces which layer of the Bunny pipeline
          works: API access, signed-URL signing, and Pull Zone CDN access
          (via referrer). The deep-link button only appears when there's
          a specific Bunny panel page that fixes the failing check. */}
      {probeResult && (
        <div className={`rounded-lg border p-3 text-xs space-y-2 ${probeBadgeCls}`}>
          <div className="font-semibold">
            {probeResult.status === 'ok'
              ? (probeResult.video_count != null
                  ? t('dashboards.course.bunnyManager.form.probeOkVideos', { count: probeResult.video_count })
                  : t('dashboards.course.bunnyManager.form.probeOk'))
              : probeResult.status === 'no_videos'
              ? t('dashboards.course.bunnyManager.form.probeNoVideos')
              : probeResult.error_message || t('dashboards.course.bunnyManager.form.probeFailed')}
          </div>

          {buildChecklist(probeResult) && (
            <ul className="space-y-1 mt-1.5">
              {buildChecklist(probeResult).map(item => (
                <li key={item.key} className="flex items-start gap-1.5">
                  <span className="mt-0.5 w-3 inline-block">{checklistIcon(item.status)}</span>
                  <span className={item.status === 'fail' ? 'font-semibold' : ''}>
                    {item.label}
                    {item.status === 'skipped' && (
                      <span className="ml-1 text-[10px] opacity-70">{t('dashboards.course.bunnyManager.form.checkSkippedSuffix')}</span>
                    )}
                  </span>
                </li>
              ))}
            </ul>
          )}

          {probeResult.bunny_panel_url && (
            <a
              href={probeResult.bunny_panel_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 mt-1 underline text-xs font-medium hover:opacity-80"
            >
              {t('dashboards.course.bunnyManager.form.openBunnyPanel')}
            </a>
          )}
        </div>
      )}

      {/* Action row: Test / Cancel / Save */}
      <div className="flex items-center justify-end gap-2 pt-2 border-t border-gray-100">
        <button
          type="button"
          onClick={handleTest}
          disabled={testing || saving}
          className="rounded-md border border-gray-300 text-gray-800 text-sm font-semibold px-3 py-2 hover:bg-gray-50 disabled:opacity-60"
        >
          {testing ? t('dashboards.course.bunnyManager.form.testingBtn') : t('dashboards.course.bunnyManager.form.testBtn')}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="text-sm font-semibold text-gray-600 hover:text-gray-900 px-3 py-2"
        >
          {t('dashboards.course.bunnyManager.form.cancelBtn')}
        </button>
        <button
          type="button"
          onClick={handleSubmit}
          disabled={saving || testing}
          className="rounded-md bg-gray-900 text-white text-sm font-semibold px-4 py-2 hover:bg-gray-800 disabled:opacity-60"
        >
          {saving ? t('dashboards.course.bunnyManager.form.savingBtn') : (isEdit ? t('dashboards.course.bunnyManager.form.saveEdit') : t('dashboards.course.bunnyManager.form.saveCreate'))}
        </button>
      </div>
    </div>
  );
}
