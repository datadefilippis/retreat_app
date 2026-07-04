/**
 * MerchantLegalDialog — Wave GDPR-Commerce Phase CG-3.
 *
 * Admin modal to edit and publish a single store's Privacy + Terms
 * docs. Mounted from the per-store action menu in StoresPage,
 * alongside the Shipping action.
 *
 * Architecture
 * ============
 * Single dialog with two doc tabs (Privacy, Termini) × four locale
 * tabs (it/en/de/fr). The merchant edits each slot independently;
 * the SAVE button persists ONE slot at a time (drafts iterate freely).
 * The PUBLISH button computes the hash of the display-locale bundle
 * and bumps the version; it warns about customer re-consent first.
 *
 * Display-locale selector is a separate control above the tabs —
 * the chosen locale gets a ★ marker on its tab, and IS the legally
 * binding language shown to all customers regardless of UI language.
 *
 * Wizard first-time mode
 * ----------------------
 * When ``status === "not_configured"`` we show a single 7-field form
 * INSTEAD of the editor. Submitting calls generate-draft for both docs
 * in all 4 locales sequentially, then renders the editor with the
 * generated content pre-filled. The merchant reviews & saves each
 * slot they care about.
 *
 * State machine
 * -------------
 *   not_configured  → wizard
 *   draft          → editor + "save" enabled, "publish" disabled until
 *                    display_locale + content are set
 *   published      → editor + "save" enabled, "publish" enabled
 *                    (idempotent when no content change)
 *   stale_draft    → same as published + amber badge nudging republish
 */

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  ResponsiveDialog,
  ResponsiveDialogContent,
  ResponsiveDialogHeader,
  ResponsiveDialogTitle,
  ResponsiveDialogFooter,
} from '../../../components/ui/responsive-dialog';
import { Button } from '../../../components/ui/button';
import { Input } from '../../../components/ui/input';
import { Label } from '../../../components/ui/label';
import { Badge } from '../../../components/ui/badge';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '../../../components/ui/dialog';
import {
  Shield,
  Loader2,
  AlertCircle,
  CheckCircle2,
  Star,
  Sparkles,
} from 'lucide-react';
import { toast } from 'sonner';

import { storeLegalAPI } from '../../../api/stores';
import MerchantLegalEditor from '../../../components/legal/MerchantLegalEditor';


const LOCALES = ['it', 'en', 'de', 'fr'];
const LOCALE_FLAGS = { it: '🇮🇹', en: '🇬🇧', de: '🇩🇪', fr: '🇫🇷' };
const LOCALE_LABELS = { it: 'Italiano', en: 'English', de: 'Deutsch', fr: 'Français' };
const DOC_TYPES = ['privacy', 'terms'];


/**
 * Status → tailwind badge styling.
 */
function StatusBadge({ status }) {
  const { t } = useTranslation('legal');
  const config = {
    not_configured: { color: 'bg-gray-100 text-gray-700', label: t('admin_gdpr.status_not_configured') },
    draft:          { color: 'bg-amber-100 text-amber-800', label: t('admin_gdpr.status_draft') },
    published:      { color: 'bg-emerald-100 text-emerald-800', label: t('admin_gdpr.status_published') },
    stale_draft:    { color: 'bg-amber-100 text-amber-800', label: t('admin_gdpr.status_stale_draft') },
  }[status] || { color: 'bg-gray-100 text-gray-700', label: status || '—' };

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${config.color}`}>
      {config.label}
    </span>
  );
}


/**
 * First-time setup form. 7 boolean/string fields → triggers
 * generate-draft for all 8 (4 locales × 2 doc types) combinations,
 * stamps the merchant_legal_display_locale, and switches the dialog
 * to editor mode with the drafts pre-filled.
 */
function FirstTimeWizard({ store, savedVars, onComplete }) {
  const { t } = useTranslation('legal');

  // CG-3-Polish: pre-populate from persisted template_vars if any.
  // The merchant who re-opens the wizard (e.g. after deleting drafts)
  // shouldn't re-type their identity data.
  const initial = savedVars || {};
  const [merchantName, setMerchantName] = useState(initial.merchant_name || '');
  const [merchantEmail, setMerchantEmail] = useState(
    initial.merchant_email || store.contact_email || '',
  );
  const [merchantCountry, setMerchantCountry] = useState(initial.merchant_country || '');
  const [storeCountry, setStoreCountry] = useState(initial.store_country || '');
  const [collectsPhone, setCollectsPhone] = useState(
    initial.collects_phone === undefined ? false : !!initial.collects_phone,
  );
  const [collectsShipping, setCollectsShipping] = useState(
    initial.collects_shipping_address === undefined ? true : !!initial.collects_shipping_address,
  );
  const [usesMarketing, setUsesMarketing] = useState(
    initial.uses_marketing === undefined ? false : !!initial.uses_marketing,
  );
  const [shipsEu, setShipsEu] = useState(
    initial.ships_to_eu === undefined ? true : !!initial.ships_to_eu,
  );

  const [generating, setGenerating] = useState(false);

  const canGenerate = merchantName.trim() && merchantEmail.trim() && merchantCountry.trim();

  const handleGenerate = useCallback(async () => {
    if (!canGenerate || generating) return;
    setGenerating(true);
    try {
      const vars = {
        merchant_name: merchantName.trim(),
        merchant_email: merchantEmail.trim(),
        merchant_country: merchantCountry.trim(),
        store_name: store.name || '',
        store_country: storeCountry.trim() || merchantCountry.trim(),
        collects_phone: !!collectsPhone,
        collects_shipping_address: !!collectsShipping,
        uses_marketing: !!usesMarketing,
        ships_to_eu: !!shipsEu,
      };

      // CG-3-Polish: PERSIST the vars FIRST so subsequent re-generation
      // calls (without explicit vars in the request) pick them up
      // server-side. The wizard's vars survive the dialog close.
      await storeLegalAPI.patchTemplateVars(store.id, vars);

      // Generate all 8 drafts sequentially. They're independent template
      // renders — no concurrency benefit, and serial keeps any failure
      // path easy to debug + the toast progress legible.
      const generated = {};
      for (const docType of DOC_TYPES) {
        for (const locale of LOCALES) {
          const r = await storeLegalAPI.generateDraft(store.id, {
            doc_type: docType, locale, vars,
          });
          generated[`${docType}_${locale}`] = r.content;
        }
      }

      // Persist each slot to the DB. We do this server-side now so the
      // editor state on next mount mirrors what was generated.
      for (const docType of DOC_TYPES) {
        for (const locale of LOCALES) {
          await storeLegalAPI.patchContent(store.id, {
            doc_type: docType,
            locale,
            content: generated[`${docType}_${locale}`],
          });
        }
      }

      // CG-3-Polish: NO LONGER call patchDisplayLocale. The active
      // locale is auto-derived from storefront_languages[0] server-side
      // via get_effective_display_locale. After the last patchContent
      // we fetch a fresh snapshot to surface effective_display_locale
      // back to the dialog.
      const fresh = await storeLegalAPI.get(store.id);

      toast.success(t('admin_gdpr.saved'));
      onComplete(fresh);
    } catch (err) {
      console.error('wizard generate failed:', err);
      toast.error(t('admin_gdpr.save_error'));
    } finally {
      setGenerating(false);
    }
  }, [
    canGenerate, generating, merchantName, merchantEmail, merchantCountry,
    storeCountry, store, collectsPhone, collectsShipping, usesMarketing,
    shipsEu, onComplete, t,
  ]);

  const RadioRow = ({ label, value, setValue }) => (
    <div className="flex items-center justify-between gap-3 py-1">
      <Label className="text-sm">{label}</Label>
      <div className="flex gap-1">
        <button
          type="button"
          onClick={() => setValue(true)}
          className={`px-3 py-1 rounded text-sm border ${
            value ? 'bg-primary text-white border-primary' : 'bg-white text-gray-600 border-gray-300'
          }`}
        >
          {t('admin_gdpr.yes')}
        </button>
        <button
          type="button"
          onClick={() => setValue(false)}
          className={`px-3 py-1 rounded text-sm border ${
            !value ? 'bg-primary text-white border-primary' : 'bg-white text-gray-600 border-gray-300'
          }`}
        >
          {t('admin_gdpr.no')}
        </button>
      </div>
    </div>
  );

  return (
    <div className="space-y-4 max-w-2xl">
      <div className="flex items-start gap-3 rounded-md border border-blue-200 bg-blue-50 p-3">
        <Sparkles className="h-5 w-5 text-blue-600 shrink-0 mt-0.5" />
        <div>
          <p className="font-medium text-sm">{t('admin_gdpr.wizard_title')}</p>
          <p className="text-xs text-blue-800 mt-1">{t('admin_gdpr.wizard_subtitle')}</p>
        </div>
      </div>

      <div className="space-y-3">
        <div>
          <Label className="text-sm">{t('admin_gdpr.wizard_field_merchant_name')} *</Label>
          <Input
            value={merchantName}
            onChange={(e) => setMerchantName(e.target.value)}
            disabled={generating}
            maxLength={255}
          />
        </div>
        <div>
          <Label className="text-sm">{t('admin_gdpr.wizard_field_merchant_email')} *</Label>
          <Input
            type="email"
            value={merchantEmail}
            onChange={(e) => setMerchantEmail(e.target.value)}
            disabled={generating}
            maxLength={255}
          />
        </div>
        <div>
          <Label className="text-sm">{t('admin_gdpr.wizard_field_merchant_country')} *</Label>
          <Input
            value={merchantCountry}
            onChange={(e) => setMerchantCountry(e.target.value)}
            disabled={generating}
            maxLength={100}
            placeholder="Italia, Svizzera, Germania…"
          />
        </div>
        <div>
          <Label className="text-sm">{t('admin_gdpr.wizard_field_store_country')}</Label>
          <Input
            value={storeCountry}
            onChange={(e) => setStoreCountry(e.target.value)}
            disabled={generating}
            maxLength={100}
            placeholder="(default = paese venditore)"
          />
        </div>

        <div className="border-t pt-3 space-y-1">
          <RadioRow
            label={t('admin_gdpr.wizard_field_collects_phone')}
            value={collectsPhone}
            setValue={setCollectsPhone}
          />
          <RadioRow
            label={t('admin_gdpr.wizard_field_collects_shipping_address')}
            value={collectsShipping}
            setValue={setCollectsShipping}
          />
          <RadioRow
            label={t('admin_gdpr.wizard_field_uses_marketing')}
            value={usesMarketing}
            setValue={setUsesMarketing}
          />
          <RadioRow
            label={t('admin_gdpr.wizard_field_ships_to_eu')}
            value={shipsEu}
            setValue={setShipsEu}
          />
        </div>
      </div>

      <div className="flex flex-col-reverse sm:flex-row gap-2 justify-end pt-3 border-t">
        <Button
          variant="outline"
          onClick={() => onComplete(null)}
          disabled={generating}
        >
          {t('admin_gdpr.wizard_skip_button')}
        </Button>
        <Button
          onClick={handleGenerate}
          disabled={!canGenerate || generating}
        >
          {generating && <Loader2 className="h-4 w-4 animate-spin mr-1" />}
          {generating ? t('admin_gdpr.wizard_generating') : t('admin_gdpr.wizard_generate_button')}
        </Button>
      </div>
    </div>
  );
}


/**
 * TemplateVarsPanel — Wave CG-3-Polish.
 *
 * Surfaces the persisted wizard variables (merchant_name, email,
 * country, etc.) in a read-only card. The merchant can edit them
 * inline and either save (no version bump) or save+regenerate all 8
 * documents from the template.
 *
 * Renders nothing when no vars are persisted (legacy stores). The
 * wizard handles the first-ever save.
 */
function TemplateVarsPanel({ legal, store, onChange }) {
  const { t } = useTranslation('legal');
  const vars = legal.template_vars || null;
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState(vars || {});

  useEffect(() => {
    if (!editing) {
      setForm(legal.template_vars || {});
    }
  }, [legal.template_vars, editing]);

  if (!vars && !editing) {
    return (
      <div className="rounded-md border bg-muted/30 p-3 text-xs text-muted-foreground">
        {t('admin_gdpr.vars_panel_no_vars')}
      </div>
    );
  }

  const handleSave = async (alsoRegenerate = false) => {
    if (saving) return;
    setSaving(true);
    try {
      // Submit only the fields we manage in this panel. The server-side
      // TemplateVars model fills unknowns with safe defaults.
      const payload = {
        merchant_name: form.merchant_name || '',
        merchant_email: form.merchant_email || '',
        merchant_country: form.merchant_country || '',
        store_name: form.store_name || store.name || '',
        store_country: form.store_country || '',
        collects_phone: !!form.collects_phone,
        collects_shipping_address: !!form.collects_shipping_address,
        uses_marketing: !!form.uses_marketing,
        ships_to_eu: !!form.ships_to_eu,
      };
      const fresh = await storeLegalAPI.patchTemplateVars(store.id, payload);

      if (alsoRegenerate) {
        // Re-render + save all 8 slots from the template using the
        // freshly-saved vars. Each generate-draft now auto-pulls
        // from store.merchant_legal_template_vars when vars is null.
        for (const docType of DOC_TYPES) {
          for (const locale of LOCALES) {
            const r = await storeLegalAPI.generateDraft(store.id, {
              doc_type: docType,
              locale,
              vars: null, // server fallback
            });
            await storeLegalAPI.patchContent(store.id, {
              doc_type: docType,
              locale,
              content: r.content,
            });
          }
        }
        // Re-fetch fresh snapshot so the editor buffers re-hydrate.
        const after = await storeLegalAPI.get(store.id);
        onChange(after);
      } else {
        onChange(fresh);
      }

      toast.success(t('admin_gdpr.saved'));
      setEditing(false);
    } catch (err) {
      console.error('save template vars failed:', err);
      toast.error(t('admin_gdpr.save_error'));
    } finally {
      setSaving(false);
    }
  };

  const handleRegenerateAll = () => {
    if (!window.confirm(t('admin_gdpr.vars_panel_regenerate_confirm'))) return;
    handleSave(true);
  };

  return (
    <div className="rounded-md border bg-card p-4 space-y-3">
      <div className="flex items-start justify-between gap-2">
        <div>
          <h4 className="text-sm font-semibold">
            {t('admin_gdpr.vars_panel_title')}
          </h4>
          <p className="text-xs text-muted-foreground mt-0.5">
            {t('admin_gdpr.vars_panel_subtitle')}
          </p>
        </div>
        {!editing && (
          <Button
            variant="outline"
            size="sm"
            onClick={() => setEditing(true)}
          >
            {t('admin_gdpr.vars_panel_edit')}
          </Button>
        )}
      </div>

      {!editing ? (
        // Read-only display: 2-col grid on desktop, 1-col on mobile
        <dl className="grid sm:grid-cols-2 gap-x-4 gap-y-1.5 text-xs">
          <div>
            <dt className="text-muted-foreground">{t('admin_gdpr.wizard_field_merchant_name')}</dt>
            <dd className="font-medium">{vars?.merchant_name || '—'}</dd>
          </div>
          <div>
            <dt className="text-muted-foreground">{t('admin_gdpr.wizard_field_merchant_email')}</dt>
            <dd className="font-medium break-all">{vars?.merchant_email || '—'}</dd>
          </div>
          <div>
            <dt className="text-muted-foreground">{t('admin_gdpr.wizard_field_merchant_country')}</dt>
            <dd className="font-medium">{vars?.merchant_country || '—'}</dd>
          </div>
          <div>
            <dt className="text-muted-foreground">{t('admin_gdpr.wizard_field_store_country')}</dt>
            <dd className="font-medium">{vars?.store_country || '—'}</dd>
          </div>
          <div className="sm:col-span-2 mt-1 pt-1 border-t flex flex-wrap gap-x-3 gap-y-0.5 text-muted-foreground">
            <span>
              📞 {t('admin_gdpr.wizard_field_collects_phone')}:&nbsp;
              <strong>{vars?.collects_phone ? t('admin_gdpr.yes') : t('admin_gdpr.no')}</strong>
            </span>
            <span>
              📮 {t('admin_gdpr.wizard_field_collects_shipping_address')}:&nbsp;
              <strong>{vars?.collects_shipping_address ? t('admin_gdpr.yes') : t('admin_gdpr.no')}</strong>
            </span>
            <span>
              📧 {t('admin_gdpr.wizard_field_uses_marketing')}:&nbsp;
              <strong>{vars?.uses_marketing ? t('admin_gdpr.yes') : t('admin_gdpr.no')}</strong>
            </span>
            <span>
              🚚 {t('admin_gdpr.wizard_field_ships_to_eu')}:&nbsp;
              <strong>{vars?.ships_to_eu ? t('admin_gdpr.yes') : t('admin_gdpr.no')}</strong>
            </span>
          </div>
        </dl>
      ) : (
        // Editable form
        <div className="space-y-2">
          <div className="grid sm:grid-cols-2 gap-2">
            <div>
              <Label className="text-xs">{t('admin_gdpr.wizard_field_merchant_name')} *</Label>
              <Input
                value={form.merchant_name || ''}
                onChange={(e) => setForm({ ...form, merchant_name: e.target.value })}
                disabled={saving}
                maxLength={255}
              />
            </div>
            <div>
              <Label className="text-xs">{t('admin_gdpr.wizard_field_merchant_email')} *</Label>
              <Input
                type="email"
                value={form.merchant_email || ''}
                onChange={(e) => setForm({ ...form, merchant_email: e.target.value })}
                disabled={saving}
                maxLength={255}
              />
            </div>
            <div>
              <Label className="text-xs">{t('admin_gdpr.wizard_field_merchant_country')} *</Label>
              <Input
                value={form.merchant_country || ''}
                onChange={(e) => setForm({ ...form, merchant_country: e.target.value })}
                disabled={saving}
                maxLength={100}
              />
            </div>
            <div>
              <Label className="text-xs">{t('admin_gdpr.wizard_field_store_country')}</Label>
              <Input
                value={form.store_country || ''}
                onChange={(e) => setForm({ ...form, store_country: e.target.value })}
                disabled={saving}
                maxLength={100}
              />
            </div>
          </div>
          <div className="flex flex-wrap gap-3 text-xs pt-1">
            {[
              ['collects_phone', t('admin_gdpr.wizard_field_collects_phone')],
              ['collects_shipping_address', t('admin_gdpr.wizard_field_collects_shipping_address')],
              ['uses_marketing', t('admin_gdpr.wizard_field_uses_marketing')],
              ['ships_to_eu', t('admin_gdpr.wizard_field_ships_to_eu')],
            ].map(([key, label]) => (
              <label key={key} className="inline-flex items-center gap-1.5 cursor-pointer">
                <input
                  type="checkbox"
                  checked={!!form[key]}
                  onChange={(e) => setForm({ ...form, [key]: e.target.checked })}
                  disabled={saving}
                  className="h-3.5 w-3.5 accent-primary"
                />
                {label}
              </label>
            ))}
          </div>
          <div className="flex flex-col-reverse sm:flex-row gap-2 justify-end pt-2 border-t">
            <Button
              variant="outline"
              size="sm"
              onClick={() => { setEditing(false); setForm(legal.template_vars || {}); }}
              disabled={saving}
            >
              {t('admin_gdpr.vars_panel_cancel')}
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleRegenerateAll}
              disabled={saving}
            >
              {saving && <Loader2 className="h-3.5 w-3.5 animate-spin mr-1" />}
              {t('admin_gdpr.vars_panel_regenerate')}
            </Button>
            <Button
              size="sm"
              onClick={() => handleSave(false)}
              disabled={saving}
            >
              {saving && <Loader2 className="h-3.5 w-3.5 animate-spin mr-1" />}
              {t('admin_gdpr.vars_panel_save')}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}


/**
 * Main editor view. Renders when status !== "not_configured".
 *
 * Wave CG-3-Polish changes:
 *   - Display-locale picker REMOVED. The active locale is derived
 *     server-side from ``storefront_languages[0]`` and surfaced via
 *     ``legal.effective_display_locale``.
 *   - ActiveLocaleBanner renders an info card pointing to store
 *     settings if the merchant wants to change the language.
 *   - TemplateVarsPanel surfaces the persisted wizard variables.
 *   - Locale tabs show a ✨ "Mostrato ai clienti" badge on the active
 *     one; tabs on non-active locales show an inline warning when the
 *     editor opens them.
 *   - Publish feedback uses ``no_change_reason`` from the backend to
 *     show a precise toast (vs the generic "no change" before).
 */
function EditorView({ legal, store, onChange, onAfterPublish }) {
  const { t, i18n } = useTranslation('legal');

  // The active locale is derived from the store's primary language
  // server-side; frontend just reads it. Falls back to "it" defensively.
  const activeDisplayLocale = legal.effective_display_locale || 'it';

  // Currently edited slot: { docType, locale }
  const [activeDoc, setActiveDoc] = useState('privacy');
  const [activeLocale, setActiveLocale] = useState(activeDisplayLocale);
  // Local editor buffer per slot (controlled). On mount we hydrate from
  // the legal snapshot; on save we PATCH and refresh.
  const [buffers, setBuffers] = useState({});
  const [saving, setSaving] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [confirmPublishOpen, setConfirmPublishOpen] = useState(false);

  // Initialize buffers from the snapshot on first mount AND every time
  // the legal snapshot changes (after a server save / publish round-trip).
  useEffect(() => {
    const next = {};
    for (const docType of DOC_TYPES) {
      for (const locale of LOCALES) {
        next[`${docType}_${locale}`] = legal[`${docType}_content_${locale}`] || '';
      }
    }
    setBuffers(next);
  }, [legal]);

  const slotKey = `${activeDoc}_${activeLocale}`;
  const currentValue = buffers[slotKey] ?? '';

  // Wave CG-3-Polish-4 — track which slots have unsaved local edits.
  // A "dirty" slot is one whose buffer differs from the corresponding
  // value in the server snapshot (legal[<doc>_content_<locale>]).
  // We compute this set on every render — it's at most 8 string compares.
  const dirtySlots = useMemo(() => {
    const dirty = new Set();
    for (const docType of DOC_TYPES) {
      for (const locale of LOCALES) {
        const key = `${docType}_${locale}`;
        const buffered = buffers[key] ?? '';
        const stored = legal[`${docType}_content_${locale}`] || '';
        if (buffered !== stored) dirty.add(key);
      }
    }
    return dirty;
  }, [buffers, legal]);

  const hasUnsavedChanges = dirtySlots.size > 0;
  const isCurrentSlotDirty = dirtySlots.has(slotKey);

  const handleEditorChange = useCallback((next) => {
    setBuffers((b) => ({ ...b, [slotKey]: next }));
  }, [slotKey]);

  // Internal helper: save every dirty slot sequentially. Returns the
  // freshest snapshot after the last write so the caller can update
  // the legal state. Throws on any failure (caller decides UX).
  const saveAllDirtySlots = useCallback(async () => {
    if (dirtySlots.size === 0) return null;
    let last = null;
    for (const key of dirtySlots) {
      const [docType, locale] = key.split('_');
      last = await storeLegalAPI.patchContent(store.id, {
        doc_type: docType,
        locale,
        content: buffers[key] ?? '',
      });
    }
    return last;
  }, [dirtySlots, buffers, store]);

  const handleSave = useCallback(async () => {
    if (saving) return;
    if (!isCurrentSlotDirty) return; // Already saved — no-op
    setSaving(true);
    try {
      const fresh = await storeLegalAPI.patchContent(store.id, {
        doc_type: activeDoc,
        locale: activeLocale,
        content: currentValue,
      });
      toast.success(t('admin_gdpr.saved'));
      onChange(fresh);
    } catch (err) {
      console.error('save failed:', err);
      toast.error(t('admin_gdpr.save_error'));
    } finally {
      setSaving(false);
    }
  }, [saving, isCurrentSlotDirty, store, activeDoc, activeLocale, currentValue, onChange, t]);

  const handleGenerateDraft = useCallback(async () => {
    if (!window.confirm(t('admin_gdpr.generate_draft_confirm'))) return;
    setSaving(true);
    try {
      // CG-3-Polish: pass vars=null so the server uses the persisted
      // template_vars from the store doc. No more silent fallback to
      // empty-string identity fields.
      const r = await storeLegalAPI.generateDraft(store.id, {
        doc_type: activeDoc,
        locale: activeLocale,
        vars: null,
      });
      // Update local buffer; user can then click Save to persist.
      setBuffers((b) => ({ ...b, [slotKey]: r.content }));
      toast.success(t('admin_gdpr.saved'));
    } catch (err) {
      console.error('generate draft failed:', err);
      toast.error(t('admin_gdpr.save_error'));
    } finally {
      setSaving(false);
    }
  }, [store, activeDoc, activeLocale, slotKey, t]);

  const handlePublish = useCallback(async () => {
    setConfirmPublishOpen(false);
    if (publishing) return;
    setPublishing(true);
    try {
      // Wave CG-3-Polish-4 — SMART PUBLISH.
      //
      // The user expectation: clicking "Pubblica" should publish their
      // current visible edits regardless of whether they remembered to
      // hit "Salva" first. Previously, an unsaved buffer meant the
      // backend read OLD content from the DB and treated the publish
      // as a no-op — the green-check would only appear after the
      // explicit Save round-trip.
      //
      // Now: we auto-save every dirty buffer before invoking publish,
      // so the publish call always sees the freshest content. This is
      // a transparent UX guarantee — if the user did already save, the
      // dirtySlots set is empty and we skip straight to publish.
      let snapshotAfterSave = null;
      if (dirtySlots.size > 0) {
        snapshotAfterSave = await saveAllDirtySlots();
        if (snapshotAfterSave) onChange(snapshotAfterSave);
      }

      const fresh = await storeLegalAPI.publish(store.id);
      if (fresh.no_change) {
        // CG-3-Polish: differentiated toast based on no_change_reason.
        if (fresh.no_change_reason === 'non_display_edits_only') {
          const editedList = (fresh.edited_non_display_locales || [])
            .map((l) => l.toUpperCase())
            .join(', ');
          const activeLabel = (fresh.active_locale || '').toUpperCase();
          toast.info(t('admin_gdpr.publish_no_display_edits', {
            locales: editedList,
            active: activeLabel,
          }));
        } else {
          toast.info(t('admin_gdpr.publish_identical_content'));
        }
      } else {
        // CG-3-Polish-4: include the new version_tag in the success
        // toast so the merchant has confirmation that something
        // actually changed server-side.
        toast.success(t('admin_gdpr.published_with_version', {
          version: fresh.version_tag || '',
        }));
      }
      onAfterPublish(fresh);
    } catch (err) {
      console.error('publish failed:', err);
      const detail = err?.response?.data?.detail;
      if (err?.response?.status === 422) {
        toast.error(detail || t('admin_gdpr.publish_missing_content_error'));
      } else {
        toast.error(t('admin_gdpr.publish_error'));
      }
    } finally {
      setPublishing(false);
    }
  }, [publishing, store, onAfterPublish, t, dirtySlots, saveAllDirtySlots, onChange]);

  const canPublish = useMemo(() => {
    const loc = activeDisplayLocale;
    return loc
      && (legal[`privacy_content_${loc}`] || '').trim()
      && (legal[`terms_content_${loc}`] || '').trim();
  }, [legal, activeDisplayLocale]);

  // True when the user is editing a tab that is NOT the customer-
  // visible one. Used to render an inline warning so the merchant
  // understands their changes won't trigger a re-consent.
  const isEditingNonActive = activeLocale !== activeDisplayLocale;

  return (
    <div className="space-y-4">
      {/* Status row */}
      <div className="flex flex-wrap items-center gap-3 text-sm">
        <StatusBadge status={legal.status} />
        {legal.version_tag && (
          <span className="text-xs text-gray-500">
            {t('admin_gdpr.version_label')}: <strong>{legal.version_tag}</strong>
          </span>
        )}
        {legal.published_at && (
          <span className="text-xs text-gray-500">
            {t('admin_gdpr.published_at', {
              date: new Date(legal.published_at).toLocaleDateString(i18n.language),
            })}
          </span>
        )}
        {legal.last_edited_at && (
          <span className="text-xs text-gray-500">
            {t('admin_gdpr.last_edited_at', {
              date: new Date(legal.last_edited_at).toLocaleDateString(i18n.language),
            })}
          </span>
        )}
      </div>

      {/* Template vars panel — persistent identity & config (CG-3-Polish) */}
      <TemplateVarsPanel
        legal={legal}
        store={store}
        onChange={onChange}
      />

      {/* Active locale banner — replaces the deprecated locale picker.
          The active locale is now auto-derived from the store's
          primary language (storefront_languages[0]). To change it,
          the admin goes to store settings — surfaced via a link. */}
      <div className="rounded-md border border-blue-200 bg-blue-50 p-3 flex items-start gap-2">
        <Star className="h-4 w-4 mt-0.5 text-blue-600 shrink-0 fill-blue-500" />
        <div className="flex-1 min-w-0 text-sm">
          <p className="font-medium text-blue-900">
            {t('admin_gdpr.active_locale_banner', {
              language: `${LOCALE_FLAGS[activeDisplayLocale]} ${LOCALE_LABELS[activeDisplayLocale] || activeDisplayLocale}`,
            })}
          </p>
          <p className="text-xs text-blue-800 mt-0.5">
            {t('admin_gdpr.active_locale_help', {
              store_settings_link: '',
            }).replace('{{store_settings_link}}', '')}{' '}
            <a
              href="/stores"
              target="_blank"
              rel="noopener noreferrer"
              className="underline font-medium hover:text-blue-700"
            >
              {t('admin_gdpr.active_locale_link_text')}
            </a>.
          </p>
        </div>
      </div>

      {/* Doc-type tabs (CG-3-Polish-4: dot indicator when any locale
          of the doc-type is dirty) */}
      <div className="flex gap-2 border-b">
        {DOC_TYPES.map((d) => {
          const docTypeIsDirty = LOCALES.some((loc) => dirtySlots.has(`${d}_${loc}`));
          return (
            <button
              key={d}
              type="button"
              onClick={() => setActiveDoc(d)}
              className={`px-4 py-2 text-sm border-b-2 -mb-px transition-colors inline-flex items-center gap-1.5 ${
                activeDoc === d
                  ? 'border-primary text-primary font-medium'
                  : 'border-transparent text-gray-600 hover:text-gray-900'
              }`}
            >
              {d === 'privacy' ? t('admin_gdpr.tab_privacy') : t('admin_gdpr.tab_terms')}
              {docTypeIsDirty && (
                <span
                  className="h-1.5 w-1.5 rounded-full bg-amber-500"
                  title={t('admin_gdpr.tab_unsaved_dot')}
                />
              )}
            </button>
          );
        })}
      </div>

      {/* Locale sub-tabs — active locale highlighted with badge.
          CG-3-Polish-4: dirty dot when the buffer for that locale
          (under the active doc-type) has unsaved changes. */}
      <div className="flex flex-wrap gap-1.5 items-center">
        {LOCALES.map((loc) => {
          const isActiveDisplay = loc === activeDisplayLocale;
          const isSelected = activeLocale === loc;
          const slotIsDirty = dirtySlots.has(`${activeDoc}_${loc}`);
          return (
            <button
              key={loc}
              type="button"
              onClick={() => setActiveLocale(loc)}
              className={`px-3 py-1 rounded text-xs border inline-flex items-center gap-1 ${
                isSelected
                  ? 'border-primary bg-primary/10 text-primary'
                  : 'border-gray-200 bg-white text-gray-600 hover:border-gray-300'
              } ${isActiveDisplay ? 'ring-1 ring-amber-300' : ''}`}
              title={isActiveDisplay ? t('admin_gdpr.tab_active_badge') : ''}
            >
              {LOCALE_FLAGS[loc]} {loc.toUpperCase()}
              {slotIsDirty && (
                <span
                  className="h-1.5 w-1.5 rounded-full bg-amber-500"
                  title={t('admin_gdpr.tab_unsaved_dot')}
                />
              )}
              {isActiveDisplay && (
                <span className="ml-0.5 px-1.5 py-0.5 rounded-full bg-amber-100 text-amber-800 text-[9px] font-semibold uppercase tracking-wide">
                  ✨ {t('admin_gdpr.tab_active_badge')}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Inline warning when editing a non-active locale */}
      {isEditingNonActive && (
        <div className="rounded-md border border-amber-200 bg-amber-50 p-2.5 text-xs text-amber-900 flex items-start gap-2">
          <AlertCircle className="h-3.5 w-3.5 mt-0.5 shrink-0" />
          <span>
            {t('admin_gdpr.tab_non_active_warning', {
              active: activeDisplayLocale.toUpperCase(),
            })}
          </span>
        </div>
      )}

      {/* Editor */}
      <MerchantLegalEditor
        value={currentValue}
        onChange={handleEditorChange}
        disabled={saving || publishing}
      />

      {/* CG-3-Polish-2: explicit "which language will be published"
          hint right above the action bar.
          CG-3-Polish-4: also surface the "unsaved changes" state so
          the merchant knows the smart-publish will auto-save first. */}
      <div className="rounded-md bg-amber-50 border border-amber-200 px-3 py-2 text-xs text-amber-900 flex items-center gap-2 flex-wrap">
        <Star className="h-3.5 w-3.5 fill-amber-500 text-amber-500 shrink-0" />
        <span className="flex-1 min-w-0">
          {t('admin_gdpr.publish_hint', {
            language: `${LOCALE_FLAGS[activeDisplayLocale]} ${LOCALE_LABELS[activeDisplayLocale] || activeDisplayLocale}`,
          })}
        </span>
        {hasUnsavedChanges && (
          <span className="inline-flex items-center gap-1 rounded-full bg-amber-200 text-amber-900 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide">
            <span className="h-1.5 w-1.5 rounded-full bg-amber-600" />
            {t('admin_gdpr.unsaved_changes')} ({dirtySlots.size})
          </span>
        )}
      </div>

      {/* Action bar */}
      <div className="flex flex-col-reverse sm:flex-row gap-2 justify-end pt-3 border-t">
        <Button
          variant="outline"
          onClick={handleGenerateDraft}
          disabled={saving || publishing}
        >
          {t('admin_gdpr.generate_draft_button')}
        </Button>
        <Button
          variant="outline"
          onClick={handleSave}
          // CG-3-Polish-4: disabled when clean (no unsaved changes for
          // the current slot) so the user can't accidentally re-save
          // unchanged content (no DB churn, no spurious last_edited_at).
          disabled={saving || publishing || !isCurrentSlotDirty}
        >
          {saving && <Loader2 className="h-4 w-4 animate-spin mr-1" />}
          {saving
            ? t('admin_gdpr.saving')
            : (isCurrentSlotDirty
                ? t('admin_gdpr.save_button')
                : t('admin_gdpr.save_button_clean'))
          }
        </Button>
        <Button
          onClick={() => setConfirmPublishOpen(true)}
          disabled={saving || publishing || !canPublish}
        >
          {publishing && <Loader2 className="h-4 w-4 animate-spin mr-1" />}
          {publishing
            ? (dirtySlots.size > 0
                ? t('admin_gdpr.auto_saving')
                : t('admin_gdpr.publishing'))
            : t('admin_gdpr.publish_button')}
        </Button>
      </div>

      {/* Publish confirmation dialog (nested) */}
      <Dialog open={confirmPublishOpen} onOpenChange={setConfirmPublishOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('admin_gdpr.publish_confirm_title')}</DialogTitle>
          </DialogHeader>
          <div className="space-y-2">
            {/* CG-3-Polish-2 — surface the active language INSIDE the
                confirm dialog too, so the user knows exactly what
                they're publishing right at click-time. */}
            <div className="rounded-md bg-amber-50 border border-amber-200 px-3 py-2 text-sm text-amber-900 flex items-start gap-2">
              <Star className="h-4 w-4 mt-0.5 fill-amber-500 text-amber-500 shrink-0" />
              <span>
                {t('admin_gdpr.publish_confirm_active_locale', {
                  language: `${LOCALE_FLAGS[activeDisplayLocale]} ${LOCALE_LABELS[activeDisplayLocale] || activeDisplayLocale}`,
                })}
              </span>
            </div>
            <p className="text-sm text-gray-600">
              {t('admin_gdpr.publish_confirm_body')}
            </p>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setConfirmPublishOpen(false)}>
              {t('admin_gdpr.publish_confirm_cancel')}
            </Button>
            <Button onClick={handlePublish}>
              {t('admin_gdpr.publish_confirm_ok')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}


export default function MerchantLegalDialog({ open, store, onClose }) {
  const { t } = useTranslation('legal');
  const [legal, setLegal] = useState(null);
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState(null);

  // Load snapshot whenever the dialog opens for a different store.
  useEffect(() => {
    if (!open || !store) {
      setLegal(null);
      return;
    }
    let active = true;
    setLoading(true);
    setLoadError(null);
    storeLegalAPI.get(store.id).then(
      (snap) => { if (active) { setLegal(snap); setLoading(false); } },
      (err) => {
        if (active) {
          console.error('load legal failed:', err);
          setLoadError(err);
          setLoading(false);
        }
      }
    );
    return () => { active = false; };
  }, [open, store]);

  if (!store) return null;

  return (
    <ResponsiveDialog open={open} onOpenChange={(o) => !o && onClose()}>
      <ResponsiveDialogContent className="max-w-4xl">
        <ResponsiveDialogHeader>
          <ResponsiveDialogTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5 text-primary" />
            {t('admin_gdpr.section_title')}
            <span className="text-sm text-muted-foreground font-normal">
              — {store.name}
            </span>
          </ResponsiveDialogTitle>
        </ResponsiveDialogHeader>

        <div className="px-1 py-2 max-h-[70vh] overflow-y-auto">
          {loading && (
            <div className="flex items-center gap-2 text-sm text-gray-500">
              <Loader2 className="h-4 w-4 animate-spin" />
              {t('admin_gdpr.saving')}
            </div>
          )}

          {loadError && (
            <div className="flex items-start gap-3 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
              <AlertCircle className="h-5 w-5 shrink-0 mt-0.5" />
              {t('admin_gdpr.load_error')}
            </div>
          )}

          {legal && legal.status === 'not_configured' && (
            <FirstTimeWizard
              store={store}
              // CG-3-Polish: pre-populate the wizard from any persisted
              // template_vars so the merchant doesn't re-type identity
              // data if they re-open the wizard.
              savedVars={legal.template_vars || null}
              onComplete={(fresh) => {
                if (fresh) setLegal(fresh);
                // If they skipped (fresh=null), keep the dialog in
                // not_configured state so they can re-enter the wizard
                // or close. No UI change needed.
              }}
            />
          )}

          {legal && legal.status !== 'not_configured' && (
            <EditorView
              legal={legal}
              store={store}
              onChange={(fresh) => setLegal(fresh)}
              onAfterPublish={(fresh) => setLegal(fresh)}
            />
          )}
        </div>

        <ResponsiveDialogFooter>
          <Button variant="outline" onClick={onClose}>
            Chiudi
          </Button>
        </ResponsiveDialogFooter>
      </ResponsiveDialogContent>
    </ResponsiveDialog>
  );
}
