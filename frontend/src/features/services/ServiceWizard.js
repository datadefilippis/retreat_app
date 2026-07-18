/**
 * ServiceWizard — guided 4-step flow to create a service product
 * (F5 Onda 12). Mirrors EventWizard structurally so the admin UX is
 * consistent across product types.
 *
 * Tabs:
 *   1. Cosa offri    — base product: name, description, image, price,
 *                      transaction_mode, duration_minutes
 *   2. Disponibilità — weekly availability_rules for slot picking
 *   3. Opzioni       — service_options (radio-select at checkout)
 *   4. Pubblica      — T&C override + F1/F2 config + is_published toggle
 *
 * Submission strategy:
 *   The backend wizard endpoint for events creates product + occurrence +
 *   tiers atomically. For services we don't have occurrences — we use
 *   the generic products endpoint plus a sequence of calls to create
 *   availability rules and service options. Failure of any one step
 *   surfaces a toast; the merchant can retry the sub-step from the
 *   dashboard later (the product is still saved).
 */

import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import useProductTaxonomies from '../../hooks/useProductTaxonomies';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';
import { productsAPI, storeSettingsAPI } from '../../api';
import { storesAPI } from '../../api/stores';
import { availabilityAPI } from '../../api/availability';
import { serviceOptionsAPI } from '../../api/serviceOptions';
import { useCurrency, useAuth } from '../../context/AuthContext';

// 2026-05-20 — Hardening helpers (audit fix wave). See PhysicalWizard
// for the design rationale of each. Pure additive imports.
import { PriceInput } from '../../components/ui/PriceInput';
import { UnsavedChangesDialog } from '../../components/ui/UnsavedChangesDialog';
import { DraftRestoreBanner } from '../../components/ui/DraftRestoreBanner';
import { useSubmitLock } from '../../hooks/useSubmitLock';
import { useUnsavedChangesPrompt } from '../../hooks/useUnsavedChangesPrompt';
import { useWizardDraft } from '../../hooks/useWizardDraft';
import { useAbortableUpload } from '../../hooks/useAbortableUpload';
import { showImageUploadFailedToast } from '../../lib/imageUploadFailedToast';
import { formatCurrency as fmtCurrency } from '../../lib/utils';
import FieldEditorList from '../events/components/FieldEditorList';
import { pruneFieldConfigs } from '../events/components/fieldConfigUtils';
import ServiceOptionsEditor from './components/ServiceOptionsEditor';
import AvailabilityRulesEditor from './components/AvailabilityRulesEditor';
import StripeRequiredAlert from '../../components/StripeRequiredAlert';
import MultiLangSection from '../../components/MultiLangSection';


// Tabs are addressed by stable `key`. Visible labels are resolved at
// render time via t('wizards.service.tabs.<key>') so translations stay
// in the JSON catalog. The `n` index is the 1-based step number shown
// in the tab pill — also used for the "Step n of N" header.
const TABS = [
  { key: 'base',     n: 1 },
  { key: 'when',     n: 2 },
  { key: 'options',  n: 3 },
  { key: 'publish',  n: 4 },
];


function validateBase(base, t) {
  const e = {};
  if (!base.name?.trim()) e.name = t('wizards.common.validation.nameRequired');
  if (base.unit_price !== '' && Number(base.unit_price) < 0) e.unit_price = t('wizards.common.validation.priceInvalid');
  if (base.duration_minutes !== '' && (Number(base.duration_minutes) < 5 || Number(base.duration_minutes) > 1440)) {
    e.duration_minutes = t('wizards.service.validation.durationRange');
  }
  return e;
}


export default function ServiceWizard() {
  const taxonomies = useProductTaxonomies();
  const orgCurrency = useCurrency();
  const navigate = useNavigate();
  const { t } = useTranslation('products');
  const prefillRef = useRef(null);

  const [activeTab, setActiveTab] = useState('base');
  const [submitting, setSubmitting] = useState(false);

  // Tab 1
  const [base, setBase] = useState({
    name: '',
    category: '',
    description: '',
    image_url: '',
    unit_price: '',
    transaction_mode: 'request',
    duration_minutes: 60,
  });
  const [imageFile, setImageFile] = useState(null);
  const [storeIds, setStoreIds] = useState([]);
  const [availableStores, setAvailableStores] = useState([]);
  // Wave 1 (W1.S5/Phase 2.1) — cost composition for margin calculation.
  // Null when the merchant hasn't configured any cost component. The
  // backend resolver returns margin=N/D for such products.
  const [costSource, setCostSource] = useState(null);

  // Tab 2
  const [rules, setRules] = useState([]);
  // Onda 15 — "Usa calendario ufficiale": when ON (default), skip the
  // per-service availability editor and rely on the synthetic
  // Mon-Fri 09:00-18:00 schedule computed server-side, minus any
  // blocked_slots from the calendar.
  const [useDefaultSchedule, setUseDefaultSchedule] = useState(true);

  // Tab 3
  const [options, setOptions] = useState([]);

  // Tab 4
  const [publishNow, setPublishNow] = useState(false);
  const [termsContent, setTermsContent] = useState('');
  const [attendeeFieldsCfg, setAttendeeFieldsCfg] = useState([]);
  const [orderFieldsCfg, setOrderFieldsCfg] = useState([]);
  const [serviceAllowCustomRequest, setServiceAllowCustomRequest] = useState(false);
  // Onda 13 — long description + cover image for the public landing
  const [longDescription, setLongDescription] = useState('');
  // Multilingua manuale — le lingue offerte decidono dove il servizio appare
  const [trName, setTrName] = useState({});
  const [trDescription, setTrDescription] = useState({});
  const [trLong, setTrLong] = useState({});
  const [coverImageUrl, setCoverImageUrl] = useState('');

  const loadStores = useCallback(async () => {
    try {
      const res = await storesAPI.list();
      setAvailableStores(res.data?.stores || []);
    } catch { /* optional */ }
  }, []);
  useEffect(() => { loadStores(); }, [loadStores]);

  // ── 2026-05-20 — Hardening hooks ────────────────────────────────────
  // Aggregate state into a single object for draft autosave / dirty
  // detection. ``imageFile`` excluded — File objects can't be JSON-serialised.
  const formData = useMemo(() => ({
    base, costSource, rules, useDefaultSchedule, options,
    publishNow, termsContent, attendeeFieldsCfg, orderFieldsCfg,
    serviceAllowCustomRequest, longDescription, coverImageUrl, storeIds,
  }), [
    base, costSource, rules, useDefaultSchedule, options,
    publishNow, termsContent, attendeeFieldsCfg, orderFieldsCfg,
    serviceAllowCustomRequest, longDescription, coverImageUrl, storeIds,
  ]);

  const applyDraft = useCallback((draft) => {
    if (!draft || typeof draft !== 'object') return;
    if (draft.base) setBase(draft.base);
    if ('costSource' in draft) setCostSource(draft.costSource);
    if (Array.isArray(draft.rules)) setRules(draft.rules);
    if ('useDefaultSchedule' in draft) setUseDefaultSchedule(!!draft.useDefaultSchedule);
    if (Array.isArray(draft.options)) setOptions(draft.options);
    if ('publishNow' in draft) setPublishNow(!!draft.publishNow);
    if ('termsContent' in draft) setTermsContent(draft.termsContent);
    if (Array.isArray(draft.attendeeFieldsCfg)) setAttendeeFieldsCfg(draft.attendeeFieldsCfg);
    if (Array.isArray(draft.orderFieldsCfg)) setOrderFieldsCfg(draft.orderFieldsCfg);
    if ('serviceAllowCustomRequest' in draft) setServiceAllowCustomRequest(!!draft.serviceAllowCustomRequest);
    if ('longDescription' in draft) setLongDescription(draft.longDescription);
    if ('coverImageUrl' in draft) setCoverImageUrl(draft.coverImageUrl);
    if (Array.isArray(draft.storeIds)) setStoreIds(draft.storeIds);
  }, []);

  const initialFormDataRef = useRef(null);
  useEffect(() => {
    if (initialFormDataRef.current === null) {
      initialFormDataRef.current = JSON.stringify(formData);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  const [submittedSuccessfully, setSubmittedSuccessfully] = useState(false);
  const isDirty = useMemo(() => {
    if (submittedSuccessfully) return false;
    if (initialFormDataRef.current === null) return false;
    return JSON.stringify(formData) !== initialFormDataRef.current
      || imageFile !== null;
  }, [formData, imageFile, submittedSuccessfully]);

  const submitLock = useSubmitLock();
  const { blocker } = useUnsavedChangesPrompt(isDirty);

  const { user } = useAuth();
  const scopeKey = user?.id || user?.email || 'anonymous';
  const draft = useWizardDraft({
    wizardKey: 'service-create',
    scopeKey,
    formData,
    setFormData: applyDraft,
  });

  const upload = useAbortableUpload();

  const errorsBase = useMemo(() => validateBase(base, t), [base, t]);
  const baseValid = Object.keys(errorsBase).length === 0;
  // Onda 15 — when the default schedule is active, we bypass the rules
  // editor entirely; validation passes without inspecting the empty
  // rules array.
  const rulesValid = useDefaultSchedule
    ? true
    : rules.every(r =>
        r.start_time < r.end_time &&
        Number(r.slot_duration_minutes || 0) > 0
      );
  const optionsValid = options.every(o => o.label?.trim() && (o.price === 0 || Number(o.price) >= 0));
  const allValid = baseValid && rulesValid && optionsValid;

  const tabHasErrors = {
    base: !baseValid,
    when: !rulesValid,
    options: !optionsValid,
    publish: !allValid,
  };

  const currentTabIdx = TABS.findIndex(t => t.key === activeTab);
  const nextTab = () => {
    const next = TABS[currentTabIdx + 1];
    if (next) setActiveTab(next.key);
  };
  const prevTab = () => {
    const prev = TABS[currentTabIdx - 1];
    if (prev) setActiveTab(prev.key);
  };

  const fieldError = (msg) => msg ? <p className="text-[11px] text-red-600 mt-0.5">{msg}</p> : null;

  const onSubmit = async () => {
    if (!allValid) { toast.error(t('wizards.common.correctErrors')); return; }
    // 2026-05-20 — atomic ref-based lock against fast double-click.
    if (!submitLock.tryLock()) return;
    setSubmitting(true);
    try {
      // Step 1 — create the product (item_type=service)
      const productPayload = {
        name: base.name.trim(),
        category: base.category || null,
        description: base.description?.trim() || null,
        translations: (() => {
          const langs = new Set([...Object.keys(trName), ...Object.keys(trDescription), ...Object.keys(trLong)]);
          const out = {};
          langs.forEach(l => {
            const e = {};
            if ((trName[l] || '').trim()) e.name = trName[l].trim();
            if ((trDescription[l] || '').trim()) e.description = trDescription[l].trim();
            if ((trLong[l] || '').trim()) e.long_description = trLong[l].trim();
            if (Object.keys(e).length) out[l] = e;
          });
          return out;
        })(),
        image_url: base.image_url?.trim() || null,
        unit_price: base.unit_price !== '' ? Number(base.unit_price) : null,
        item_type: 'service',
        price_mode: 'fixed',
        transaction_mode: base.transaction_mode,
        is_published: publishNow,
        store_ids: storeIds,
        metadata: {
          duration_minutes: Number(base.duration_minutes) || 60,
          service_allow_custom_request: serviceAllowCustomRequest,
          // Onda 15 — flag consumed by get_service_slots to synthesize
          // a virtual Mon-Fri 09-18 schedule when no DB rules exist.
          use_default_schedule: useDefaultSchedule,
          terms_content: termsContent?.trim() || null,
          attendee_fields: pruneFieldConfigs(attendeeFieldsCfg),
          order_fields: pruneFieldConfigs(orderFieldsCfg),
          // Onda 13 — landing fields
          long_description: longDescription?.trim() || null,
          cover_image_url: coverImageUrl?.trim() || null,
        },
        // Wave 1 (W1.S5/Phase 2.1) — additive cost composition. Null
        // when the merchant skipped the cost section; resolver returns
        // margin=N/D for those products. When set, takes precedence
        // over the deprecated cost_price field at margin compute time.
        cost_source: costSource,
      };
      const createRes = await productsAPI.create(productPayload);
      const productId = createRes.data?.id;
      if (!productId) throw new Error('Product creation returned no id');

      // Step 2 — upload image if user picked a file
      // 2026-05-20 — Abortable upload + persistent retry toast.
      if (imageFile) {
        const fileToUpload = imageFile;
        try {
          await upload.run((signal) =>
            productsAPI.uploadImage(productId, fileToUpload, { signal }),
          );
        } catch (e) {
          showImageUploadFailedToast({
            t,
            context: base.name,
            onRetry: async () => {
              try {
                await productsAPI.uploadImage(productId, fileToUpload);
                toast.success(t('wizards.common.imageUpload.retrySuccess', {
                  defaultValue: 'Immagine caricata correttamente.',
                }));
              } catch {
                showImageUploadFailedToast({ t, context: base.name });
              }
            },
          });
        }
      }

      // Step 3 — create availability rules (skipped when the admin
      // opted into the default schedule; in that case the backend
      // synthesizes Mon-Fri 09-18 virtual rules at slot-fetch time).
      if (!useDefaultSchedule) {
        for (const r of rules) {
          try {
            await availabilityAPI.createRule({
              product_id: productId,
              day_of_week: r.day_of_week,
              start_time: r.start_time,
              end_time: r.end_time,
              slot_duration_minutes: r.slot_duration_minutes,
            });
          } catch (e) {
            toast.warning(t('wizards.service.validation.ruleNotCreated', { day: r.day_of_week }));
          }
        }
      }

      // Step 4 — create service options
      for (const o of options) {
        try {
          await serviceOptionsAPI.create(productId, {
            label: o.label.trim(),
            description: o.description?.trim() || null,
            price: Number(o.price) || 0,
            duration_minutes_override: o.duration_minutes_override ? Number(o.duration_minutes_override) : null,
            sort_order: o.sort_order ?? 0,
            is_active: o.is_active !== false,
          });
        } catch (e) {
          toast.warning(t('wizards.service.validation.optionNotCreated', { label: o.label }));
        }
      }

      // 2026-05-20 — Clear draft + suppress unsaved-changes prompt
      // on the post-create navigate.
      draft.discard();
      setSubmittedSuccessfully(true);
      toast.success(t('wizards.service.createdToast'));
      navigate(`/services/${productId}`);
    } catch (err) {
      toast.error(err?.response?.data?.detail || t('wizards.service.validation.creationFailed'));
    } finally {
      setSubmitting(false);
      submitLock.unlock();
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 pb-20">
      {/* Header — sticky, same shape as EventWizard */}
      <div className="bg-white border-b sticky top-0 z-10">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 py-3 flex items-center justify-between gap-3">
          <div className="min-w-0">
            <button onClick={() => navigate('/products?type=service')} className="text-sm text-gray-600 hover:text-gray-900">
              {t('wizards.service.back')}
            </button>
            <h1 className="text-lg sm:text-xl font-bold text-gray-900 mt-0.5">{t('wizards.service.title')}</h1>
          </div>
          <div className="hidden sm:flex items-center gap-1 text-xs text-gray-500">
            {t('wizards.common.stepCounter', { current: currentTabIdx + 1, total: TABS.length })}
          </div>
        </div>

        {/* Tab bar — same visual as EventWizard (done/error/active states) */}
        <div className="max-w-3xl mx-auto px-4 sm:px-6 pb-3 flex gap-1 overflow-x-auto">
          {TABS.map((tab, i) => {
            const done = i < currentTabIdx && !tabHasErrors[tab.key];
            const active = tab.key === activeTab;
            const err = i < currentTabIdx && tabHasErrors[tab.key];
            return (
              <button
                key={tab.key}
                type="button"
                onClick={() => setActiveTab(tab.key)}
                className={`flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-semibold whitespace-nowrap ${
                  active
                    ? 'bg-gray-900 text-white'
                    : err
                      ? 'bg-red-100 text-red-800 border border-red-200'
                      : done
                        ? 'bg-green-100 text-green-900'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                <span className="tabular-nums">{tab.n}</span>
                <span>{t(`wizards.service.tabs.${tab.key}`)}</span>
                {err && <span aria-hidden>!</span>}
                {done && <span aria-hidden>✓</span>}
              </button>
            );
          })}
        </div>
      </div>

      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-6 space-y-5">
        <div className="space-y-4">

          {/* 2026-05-20 — Restore prompt for drafts <24h old. */}
          {draft.hasDraft && (
            <DraftRestoreBanner
              savedAt={draft.savedAt}
              onRestore={draft.restore}
              onDiscard={draft.discard}
            />
          )}

          {/* ── TAB 1: Cosa offri ───────────────────────────────────── */}
          {activeTab === 'base' && (
            <div className="rounded-xl border border-gray-200 bg-white p-5 space-y-4">
              <div className="border-l-[3px] border-primary/60 pl-3">
                <h2 className="text-base font-semibold text-gray-900">{t('wizards.service.base.title')}</h2>
                <p className="text-xs text-gray-500 mt-0.5">{t('wizards.service.base.subtitle')}</p>
              </div>

              <MultiLangSection fields={[
                { key: 'name', label: t('wizards.service.base.name'), it: base.name,
                  value: trName, onChange: setTrName, input: true, maxLength: 255 },
                { key: 'description', label: t('wizards.service.base.descriptionLabel'), it: base.description,
                  value: trDescription, onChange: setTrDescription, rows: 2, maxLength: 2000 },
              ]}>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">{t('wizards.service.base.name')}</label>
                <input
                  type="text" value={base.name}
                  onChange={e => setBase({ ...base, name: e.target.value })}
                  maxLength={255}
                  placeholder={t('wizards.service.base.namePlaceholder')}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none"
                />
                {fieldError(errorsBase.name)}
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">{t('wizards.service.base.descriptionLabel')}</label>
                <textarea
                  value={base.description}
                  onChange={e => setBase({ ...base, description: e.target.value })}
                  rows={2} maxLength={2000}
                  placeholder={t('wizards.service.base.descriptionPlaceholder')}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none resize-none"
                />
              </div>
              </MultiLangSection>


            {/* V4 — categoria dalla tassonomia servizi (opzionale) */}
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">
                {t('wizards.common.categoryLabel', { defaultValue: 'Categoria' })}
              </label>
              <select
                value={base.category || ''}
                onChange={e => setBase({ ...base, category: e.target.value })}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none bg-white"
              >
                <option value="">{t('wizards.common.categoryNone', { defaultValue: 'Nessuna categoria' })}</option>
                {Object.entries(taxonomies.service || {}).map(([k, label]) => (
                  <option key={k} value={k}>{t(`taxonomy.${k}`, { defaultValue: label })}</option>
                ))}
              </select>
            </div>

              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">{t('wizards.service.base.imageLabel')}</label>
                <label className="flex items-center gap-2 cursor-pointer rounded-md border border-dashed border-gray-300 px-3 py-2 text-sm text-gray-600 hover:border-gray-900">
                  <span>{imageFile ? `📎 ${imageFile.name}` : t('wizards.common.imageFileLabel')}</span>
                  <input
                    type="file" accept=".jpg,.jpeg,.png,.webp" className="hidden"
                    onChange={e => { setImageFile(e.target.files?.[0] || null); setBase(b => ({ ...b, image_url: '' })); }}
                  />
                </label>
                <input
                  type="url" value={base.image_url}
                  onChange={e => { setBase({ ...base, image_url: e.target.value }); if (e.target.value) setImageFile(null); }}
                  maxLength={500}
                  placeholder={t('wizards.common.imageUrlPlaceholder')}
                  className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">{t('wizards.service.base.priceLabel')}</label>
                  {/* 2026-05-20 — PriceInput accepts locale comma "10,50". */}
                  <PriceInput
                    value={base.unit_price}
                    onValueChange={(_n, raw) => setBase({ ...base, unit_price: raw })}
                    min={0}
                    decimals={2}
                    placeholder="0,00"
                    className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none"
                  />
                  <p className="text-[11px] text-gray-400 mt-1">{t('wizards.service.base.priceHint')}</p>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">{t('wizards.service.base.durationLabel')}</label>
                  <input
                    type="number" min="5" max="1440"
                    value={base.duration_minutes}
                    onChange={e => setBase({ ...base, duration_minutes: e.target.value })}
                    className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none"
                  />
                  {fieldError(errorsBase.duration_minutes)}
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">{t('wizards.service.base.modeLabel')}</label>
                  <div className="flex gap-1.5 mt-1">
                    {[{ v: 'request', labelKey: 'wizards.common.summary.modeRequest' }, { v: 'direct', labelKey: 'wizards.common.summary.modeDirect' }].map(opt => (
                      <button key={opt.v} type="button"
                        onClick={() => setBase({ ...base, transaction_mode: opt.v })}
                        className={`rounded-full px-3 py-1 text-xs font-semibold border transition ${
                          base.transaction_mode === opt.v
                            ? 'bg-gray-900 text-white border-gray-900'
                            : 'bg-white text-gray-700 border-gray-300 hover:border-gray-900'
                        }`}
                      >{t(opt.labelKey)}</button>
                    ))}
                  </div>
                  {/* Surfaces a warning when "Diretta" is selected on an org
                      that hasn't completed Stripe Connect onboarding — the
                      storefront would otherwise silently fall back to
                      "Richiesta" at checkout. Renders nothing in every other
                      case. See components/StripeRequiredAlert.jsx. */}
                  <StripeRequiredAlert whenTransactionMode={base.transaction_mode} />
                </div>
              </div>

              {/* Store assignment moved to Tab 4 (Pubblica) in Onda 13 for
                  consistency with EventWizard — it's a publish-decision, not
                  part of the base product info. */}

              {/* Sezione "Costo del prodotto" (COGS) rimossa dalla UI su
                  richiesta founder 16/7/2026: agli operatori Aurya non
                  serve la contabilita' margini. Lo stato costSource resta
                  e viaggia nel salvataggio, cosi' i dati gia' configurati
                  non vengono cancellati. */}
            </div>
          )}

          {/* ── TAB 2: Disponibilità ────────────────────────────────── */}
          {activeTab === 'when' && (
            <div className="space-y-3">
              {/* Onda 15 — toggle "Usa calendario ufficiale" */}
              <div className="rounded-xl border border-gray-200 bg-white p-4">
                <label className="flex items-start gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={useDefaultSchedule}
                    onChange={e => setUseDefaultSchedule(e.target.checked)}
                    className="mt-1 rounded border-gray-300"
                  />
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-semibold text-gray-900">
                      {t('wizards.service.when.useDefaultTitle')}
                    </p>
                    <p className="text-xs text-gray-500 mt-1">
                      {t('wizards.service.when.useDefaultDesc')}
                    </p>
                    <p className="text-[11px] text-gray-400 mt-2">
                      {t('wizards.service.when.useDefaultHint')}
                    </p>
                  </div>
                </label>
              </div>

              {!useDefaultSchedule && (
                <AvailabilityRulesEditor
                  rules={rules}
                  onChange={setRules}
                  defaultSlotMinutes={Number(base.duration_minutes) || 60}
                />
              )}
            </div>
          )}

          {/* ── TAB 3: Opzioni ──────────────────────────────────────── */}
          {activeTab === 'options' && (
            <ServiceOptionsEditor
              options={options}
              onChange={setOptions}
            />
          )}

          {/* ── TAB 4: Pubblica ─────────────────────────────────────── */}
          {activeTab === 'publish' && (
            <div className="space-y-4">
              <div className="rounded-xl border border-gray-200 bg-white p-5 space-y-3">
                <h2 className="text-base font-semibold text-gray-900">{t('wizards.common.summary.title')}</h2>
                <dl className="text-sm grid grid-cols-1 sm:grid-cols-2 gap-2">
                  <div><dt className="text-gray-500 text-xs">{t('wizards.common.summary.name')}</dt><dd className="font-medium">{base.name || t('wizards.common.summary.emptyValue')}</dd></div>
                  <div><dt className="text-gray-500 text-xs">{t('wizards.common.summary.mode')}</dt><dd className="font-medium">{base.transaction_mode === 'direct' ? t('wizards.common.summary.modeDirect') : t('wizards.common.summary.modeRequest')}</dd></div>
                  <div><dt className="text-gray-500 text-xs">{t('wizards.service.publish.summaryDuration')}</dt><dd className="font-medium">{base.duration_minutes} min</dd></div>
                  <div><dt className="text-gray-500 text-xs">{t('wizards.common.summary.basePrice')}</dt><dd className="font-medium">{base.unit_price !== '' ? fmtCurrency(Number(base.unit_price), orgCurrency) : t('wizards.common.summary.emptyValue')}</dd></div>
                  <div><dt className="text-gray-500 text-xs">{t('wizards.service.publish.summaryAvailability')}</dt><dd className="font-medium">{useDefaultSchedule ? t('wizards.service.publish.summaryAvailabilityCalendar') : (rules.length ? t('wizards.service.publish.summaryAvailabilityRules', { count: rules.length }) : t('wizards.service.publish.summaryAvailabilityNone'))}</dd></div>
                  <div><dt className="text-gray-500 text-xs">{t('wizards.service.publish.summaryOptions')}</dt><dd className="font-medium">{options.length || t('wizards.service.publish.summaryOptionsNone')}</dd></div>
                </dl>
              </div>

              {/* Onda 13 — Cover image + long description for the landing */}
              <div className="rounded-xl border border-gray-200 bg-white p-5 space-y-3">
                <h3 className="text-sm font-semibold text-gray-900">{t('wizards.service.publish.longDescTitle')}</h3>
                <p className="text-xs text-gray-500">
                  {t('wizards.service.publish.longDescDesc')}
                </p>
                <MultiLangSection fields={[
                  { key: 'long_description', label: null, it: longDescription,
                    value: trLong, onChange: setTrLong, rows: 5, maxLength: 5000 },
                ]}>
                <textarea
                  value={longDescription}
                  onChange={e => setLongDescription(e.target.value)}
                  rows={6} maxLength={5000}
                  placeholder={t('wizards.service.publish.longDescPlaceholder')}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-xs font-mono focus:border-gray-900 focus:outline-none resize-y"
                />
                </MultiLangSection>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1 mt-2">{t('wizards.service.publish.coverUrlLabel')}</label>
                  <input
                    type="url" value={coverImageUrl}
                    onChange={e => setCoverImageUrl(e.target.value)}
                    maxLength={500}
                    placeholder={t('wizards.service.publish.coverUrlPlaceholder')}
                    className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none"
                  />
                  <p className="text-[10px] text-gray-400 mt-0.5">{t('wizards.service.publish.coverUrlHint')}</p>
                </div>
              </div>

              {/* Onda 14 — Store assignment SEMPRE visibile.
                  Single-store: banner info read-only (il servizio è visibile
                  automaticamente nel tuo unico store). Multi-store: checkbox
                  editabili per scegliere gli store. */}
              <div className="rounded-xl border border-gray-200 bg-white p-5 space-y-2">
                <h3 className="text-sm font-semibold text-gray-900">{t('wizards.common.distribution.title')}</h3>
                {availableStores.length <= 1 ? (
                  <>
                    <p className="text-xs text-gray-500">
                      {t('wizards.service.publish.distributionDesc')}
                    </p>
                    <div className="rounded-md bg-gray-50 border border-gray-200 px-3 py-2 text-sm text-gray-700 flex items-center gap-2">
                      <span aria-hidden>✓</span>
                      <span>
                        {t('wizards.common.distribution.visibleAutoPrefix')} <strong>{availableStores[0]?.name || t('wizards.common.distribution.allStoresFallback')}</strong>
                      </span>
                    </div>
                  </>
                ) : (
                  <>
                    <p className="text-xs text-gray-500">{t('wizards.service.publish.distributionMultiDesc')}</p>
                    <label className="flex items-center gap-2 text-sm cursor-pointer">
                      <input
                        type="checkbox"
                        checked={!storeIds.length}
                        onChange={() => setStoreIds([])}
                        className="rounded border-gray-300"
                      />
                      <span className={!storeIds.length ? 'font-medium' : 'text-gray-500'}>
                        {t('wizards.common.distribution.allStoresLabel')}
                      </span>
                    </label>
                    {availableStores.map(s => {
                      const isSpecific = storeIds.length > 0;
                      const checked = isSpecific && storeIds.includes(s.id);
                      return (
                        <label key={s.id} className="flex items-center gap-2 text-sm cursor-pointer">
                          <input
                            type="checkbox"
                            checked={checked}
                            onChange={() => {
                              const next = storeIds.includes(s.id)
                                ? storeIds.filter(id => id !== s.id)
                                : [...storeIds, s.id];
                              setStoreIds(next);
                            }}
                            className="rounded border-gray-300"
                          />
                          <span>{s.name}</span>
                        </label>
                      );
                    })}
                  </>
                )}
              </div>

              <div className="rounded-xl border border-gray-200 bg-white p-5 space-y-3">
                <h3 className="text-sm font-semibold text-gray-900">{t('wizards.service.publish.termsTitle')}</h3>
                <p className="text-xs text-gray-500">
                  {t('wizards.service.publish.termsDesc')}
                </p>
                <textarea
                  value={termsContent}
                  onChange={e => setTermsContent(e.target.value)}
                  rows={5} maxLength={20000}
                  placeholder={t('wizards.service.publish.termsPlaceholder')}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-xs font-mono focus:border-gray-900 focus:outline-none resize-y"
                />
              </div>

              <FieldEditorList
                fields={orderFieldsCfg}
                onChange={setOrderFieldsCfg}
                title={t('wizards.service.publish.orderFieldsTitle')}
                subtitle={t('wizards.service.publish.orderFieldsSubtitle')}
                emptyHint={t('wizards.service.publish.orderFieldsEmpty')}
              />

              <label className="flex items-start gap-3 cursor-pointer rounded-xl border border-gray-200 bg-white p-4">
                <input
                  type="checkbox"
                  checked={serviceAllowCustomRequest}
                  onChange={e => setServiceAllowCustomRequest(e.target.checked)}
                  className="mt-0.5 h-4 w-4 rounded border-gray-300"
                />
                <div className="flex-1">
                  <span className="block text-sm font-semibold text-gray-900">
                    {t('wizards.service.publish.allowCustomTitle')}
                  </span>
                  <span className="block text-xs text-gray-500 mt-0.5">
                    {t('wizards.service.publish.allowCustomDesc')}
                  </span>
                </div>
              </label>

              <label className="flex items-center gap-3 cursor-pointer rounded-xl border border-gray-200 bg-white p-4">
                <input
                  type="checkbox"
                  checked={publishNow}
                  onChange={e => setPublishNow(e.target.checked)}
                  className="h-4 w-4 rounded border-gray-300"
                />
                <span className="text-sm font-semibold text-gray-900">{t('wizards.common.publishNow')}</span>
              </label>
            </div>
          )}

          {/* Nav buttons */}
          <div className="flex items-center justify-between pt-2">
            <button
              type="button" onClick={prevTab} disabled={currentTabIdx === 0}
              className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:border-gray-900 disabled:opacity-30"
            >{t('wizards.common.back')}</button>
            {currentTabIdx < TABS.length - 1 ? (
              <button
                type="button" onClick={nextTab}
                className="rounded-md bg-gray-900 text-white px-4 py-2 text-sm font-semibold hover:bg-gray-800"
              >{t('wizards.common.next')}</button>
            ) : (
              <button
                type="button" onClick={onSubmit}
                disabled={submitting || !allValid}
                className="rounded-md bg-gray-900 text-white px-4 py-2 text-sm font-semibold hover:bg-gray-800 disabled:opacity-50"
              >{submitting ? t('wizards.common.creating') : (publishNow ? t('wizards.service.publishCta') : t('wizards.common.saveDraft'))}</button>
            )}
          </div>
        </div>
      </div>

      {/* 2026-05-20 — Unsaved-changes confirm dialog. */}
      <UnsavedChangesDialog
        open={blocker?.state === 'blocked'}
        onConfirm={() => blocker?.proceed?.()}
        onCancel={() => blocker?.reset?.()}
      />
    </div>
  );
}
