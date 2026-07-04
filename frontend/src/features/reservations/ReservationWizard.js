/**
 * ReservationWizard — guided 5-step flow to create a rental product
 * in either flavor (Onda 16 Prenotazione consolidation).
 *
 * Tabs:
 *   1. Identità       — name, image, description, store assignment
 *   2. Flavor         — range (B&B / auto / attrezzi) vs slot (sala / campo / ora)
 *   3. Prezzo & unità — unit_price, rental_unit (for range) or
 *                       slot_duration_minutes (for slot), transaction_mode
 *   4. Disponibilità  — availability_rules (slot only) OR merchant note (range)
 *   5. Extras         — ProductExtrasEditor (mandatory / optional / radio groups)
 *   6. Pubblica       — T&C override + is_published toggle
 *
 * Submission: creates the product with item_type=rental and metadata
 * carrying reservation_flavor + the flavor-specific knobs, then posts
 * extras + availability rules as sub-steps. Failure of a sub-step
 * surfaces a warning toast and leaves the product in-place so the
 * merchant can retry from the dashboard.
 */

import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';
import { productsAPI } from '../../api';
import { storesAPI } from '../../api/stores';
import { availabilityAPI } from '../../api/availability';
import { productExtrasAPI } from '../../api/productExtras';
import ProductExtrasEditor from './components/ProductExtrasEditor';
import AvailabilityRulesEditor from '../services/components/AvailabilityRulesEditor';
import StripeRequiredAlert from '../../components/StripeRequiredAlert';
// Wave 1 (W1.S5/Phase 2.2) — additive cost composition editor.
// Mounted in the "pricing" step so the rental price + its cost basis
// are configured together. See PRODUCTS_ARCHITECTURE.md §4 R6.
import CostSourceEditor from '../products/components/CostSourceEditor';

// 2026-05-20 — Hardening helpers (audit fix wave). See PhysicalWizard
// for the design rationale.
import { useAuth } from '../../context/AuthContext';
import { PriceInput } from '../../components/ui/PriceInput';
import { UnsavedChangesDialog } from '../../components/ui/UnsavedChangesDialog';
import { DraftRestoreBanner } from '../../components/ui/DraftRestoreBanner';
import { useSubmitLock } from '../../hooks/useSubmitLock';
import { useUnsavedChangesPrompt } from '../../hooks/useUnsavedChangesPrompt';
import { useWizardDraft } from '../../hooks/useWizardDraft';
import { useAbortableUpload } from '../../hooks/useAbortableUpload';
import { showImageUploadFailedToast } from '../../lib/imageUploadFailedToast';


// Tabs are addressed by stable `key`. Visible labels are resolved at
// render time via t('wizards.reservation.tabs.<key>') so translations
// stay in the JSON catalog.
const TABS = [
  { key: 'identity', n: 1 },
  { key: 'flavor',   n: 2 },
  { key: 'pricing',  n: 3 },
  { key: 'when',     n: 4 },
  { key: 'extras',   n: 5 },
  { key: 'publish',  n: 6 },
];

// Static presentation parts (emoji) — labels/descs/examples come from
// t('wizards.reservation.flavorOptions.<key>.{label,desc,example}').
const FLAVOR_PRESENTATION = {
  range: { emoji: '🏠' },
  slot:  { emoji: '📅' },
};

// Stable rental-unit option keys; labels resolved via
// t('wizards.reservation.rentalUnits.<value>').
const RENTAL_UNIT_VALUES = ['giorno', 'settimana', 'mese'];


function validateIdentity(v, t) {
  const e = {};
  if (!v.name?.trim()) e.name = t('wizards.common.validation.nameRequired');
  return e;
}

function validatePricing(v, flavor, t) {
  const e = {};
  if (v.unit_price !== '' && Number(v.unit_price) < 0) e.unit_price = t('wizards.common.validation.priceInvalid');
  if (flavor === 'range' && !v.rental_unit) e.rental_unit = t('wizards.reservation.validation.rentalUnitRequired');
  if (flavor === 'slot') {
    const n = Number(v.slot_duration_minutes);
    if (!n || n < 5 || n > 480) e.slot_duration_minutes = t('wizards.reservation.validation.slotDurationRange');
  }
  return e;
}


export default function ReservationWizard() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { t } = useTranslation('products');

  const [activeTab, setActiveTab] = useState('identity');
  const [submitting, setSubmitting] = useState(false);

  // Step 1 — identity
  const [identity, setIdentity] = useState({
    name: '',
    description: '',
    image_url: '',
  });
  const [imageFile, setImageFile] = useState(null);
  const [storeIds, setStoreIds] = useState([]);
  const [availableStores, setAvailableStores] = useState([]);

  // Step 2 — flavor (range | slot).
  // Accept ?flavor=range|slot as a URL hint so the TypePicker in ProductsPage
  // can route the merchant to the right wizard variant in one click. The
  // flavor tab remains interactive so they can change their mind.
  const [flavor, setFlavor] = useState(() => {
    const q = searchParams.get('flavor');
    return q === 'slot' || q === 'range' ? q : 'range';
  });

  // Step 3 — pricing
  const [pricing, setPricing] = useState({
    unit_price: '',
    rental_unit: 'giorno',        // range only
    slot_duration_minutes: 60,     // slot only — "suggested/fallback" duration
    // Onda 17 — variable duration + cross-day (slot flavor only). Empty
    // strings mean "use slot_duration_minutes fallback" on the backend.
    slot_min_duration_minutes: '',
    slot_step_minutes: '',
    slot_max_duration_minutes: '',
    transaction_mode: 'direct',
    rental_notes: '',
  });

  // Step 4 — availability (slot only)
  // use_default_schedule mirrors the ServiceWizard flag (Onda 15). When true,
  // the slot flavor falls back to the store-level availability rules instead
  // of requiring per-product custom rules.
  const [rules, setRules] = useState([]);
  const [useDefaultSchedule, setUseDefaultSchedule] = useState(true);

  // Wave 1 (W1.S5/Phase 2.2) — cost composition for margin calculation.
  // Null when unconfigured; backend resolver returns margin=N/D.
  const [costSource, setCostSource] = useState(null);

  // Step 5 — extras
  const [extras, setExtras] = useState([]);

  // Step 6 — publish + legal
  const [publishNow, setPublishNow] = useState(false);
  const [termsContent, setTermsContent] = useState('');

  // ── 2026-05-20 — Hardening hooks ────────────────────────────────────
  const formData = useMemo(() => ({
    identity, flavor, pricing, rules, useDefaultSchedule, costSource,
    extras, publishNow, termsContent, storeIds,
  }), [
    identity, flavor, pricing, rules, useDefaultSchedule, costSource,
    extras, publishNow, termsContent, storeIds,
  ]);

  const applyDraft = useCallback((d) => {
    if (!d || typeof d !== 'object') return;
    if (d.identity) setIdentity(d.identity);
    if (d.flavor === 'slot' || d.flavor === 'range') setFlavor(d.flavor);
    if (d.pricing) setPricing(d.pricing);
    if (Array.isArray(d.rules)) setRules(d.rules);
    if ('useDefaultSchedule' in d) setUseDefaultSchedule(!!d.useDefaultSchedule);
    if ('costSource' in d) setCostSource(d.costSource);
    if (Array.isArray(d.extras)) setExtras(d.extras);
    if ('publishNow' in d) setPublishNow(!!d.publishNow);
    if ('termsContent' in d) setTermsContent(d.termsContent);
    if (Array.isArray(d.storeIds)) setStoreIds(d.storeIds);
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
    wizardKey: 'reservation-create',
    scopeKey,
    formData,
    setFormData: applyDraft,
  });
  const upload = useAbortableUpload();

  const loadStores = useCallback(async () => {
    try {
      const res = await storesAPI.list();
      setAvailableStores(res.data?.stores || []);
    } catch { /* optional */ }
  }, []);
  useEffect(() => { loadStores(); }, [loadStores]);

  const errorsIdentity = useMemo(() => validateIdentity(identity, t), [identity, t]);
  const errorsPricing = useMemo(() => validatePricing(pricing, flavor, t), [pricing, flavor, t]);

  const identityValid = Object.keys(errorsIdentity).length === 0;
  const pricingValid = Object.keys(errorsPricing).length === 0;
  const rulesValid = flavor !== 'slot' ? true : rules.every(r =>
    r.start_time < r.end_time && Number(r.slot_duration_minutes || 0) > 0
  );
  const extrasValid = extras.every(e => {
    if (!e.label?.trim()) return false;
    if (e.kind === 'radio_variant' && !e.group_key) return false;
    if (e.price !== 0 && e.price !== '' && Number(e.price) < 0) return false;
    return true;
  });
  const allValid = identityValid && pricingValid && rulesValid && extrasValid;

  const tabHasErrors = {
    identity: !identityValid,
    flavor: false,
    pricing: !pricingValid,
    when: !rulesValid,
    extras: !extrasValid,
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
      const metadata = {
        reservation_flavor: flavor,
        rental_notes: pricing.rental_notes?.trim() || null,
        terms_content: termsContent?.trim() || null,
      };
      if (flavor === 'range') {
        metadata.rental_unit = pricing.rental_unit;
      } else {
        metadata.slot_duration_minutes = Number(pricing.slot_duration_minutes) || 60;
        // Onda 17 — variable duration + cross-day knobs. Empty string → omit
        // (backend falls back to slot_duration_minutes at read time so legacy
        // products keep working without a migration).
        const _toNumOrNull = (v) => {
          const n = Number(v);
          return v === '' || v === null || Number.isNaN(n) || n <= 0 ? null : n;
        };
        const minDur = _toNumOrNull(pricing.slot_min_duration_minutes);
        const stepDur = _toNumOrNull(pricing.slot_step_minutes);
        const maxDur = _toNumOrNull(pricing.slot_max_duration_minutes);
        if (minDur) metadata.slot_min_duration_minutes = minDur;
        if (stepDur) metadata.slot_step_minutes = stepDur;
        if (maxDur) metadata.slot_max_duration_minutes = maxDur;
        // Onda 15 parity — when true the merchant defers to the store-level
        // calendar; we skip creating per-product availability_rules entries
        // below so the backend falls back to product_id=None rules.
        metadata.use_default_schedule = useDefaultSchedule;
      }

      const productPayload = {
        name: identity.name.trim(),
        description: identity.description?.trim() || null,
        image_url: identity.image_url?.trim() || null,
        unit_price: pricing.unit_price !== '' ? Number(pricing.unit_price) : null,
        item_type: 'rental',
        price_mode: 'fixed',
        transaction_mode: pricing.transaction_mode,
        is_published: publishNow,
        store_ids: storeIds,
        metadata,
        // Wave 1 (W1.S5/Phase 2.2) — additive cost composition. Null
        // when the merchant skipped the cost section; resolver returns
        // margin=N/D for those products.
        cost_source: costSource,
      };

      const createRes = await productsAPI.create(productPayload);
      const productId = createRes.data?.id;
      if (!productId) throw new Error('Product creation returned no id');

      if (imageFile) {
        // 2026-05-20 — Abortable upload + persistent retry toast.
        const fileToUpload = imageFile;
        try {
          await upload.run((signal) =>
            productsAPI.uploadImage(productId, fileToUpload, { signal }),
          );
        } catch {
          showImageUploadFailedToast({
            t,
            context: identity.name,
            onRetry: async () => {
              try {
                await productsAPI.uploadImage(productId, fileToUpload);
                toast.success(t('wizards.common.imageUpload.retrySuccess', {
                  defaultValue: 'Immagine caricata correttamente.',
                }));
              } catch {
                showImageUploadFailedToast({ t, context: identity.name });
              }
            },
          });
        }
      }

      // Step — availability rules (slot flavor only, custom rules only).
      // When useDefaultSchedule is on we skip creating per-product rows so
      // the backend falls back to the store-level (product_id=None) rules.
      if (flavor === 'slot' && !useDefaultSchedule) {
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
            toast.warning(t('wizards.reservation.validation.ruleNotCreated', { day: r.day_of_week }));
          }
        }
      }

      // Step — extras
      for (const ex of extras) {
        try {
          await productExtrasAPI.create(productId, {
            kind: ex.kind,
            group_key: ex.group_key || null,
            label: ex.label.trim(),
            description: ex.description?.trim() || null,
            price: ex.price === '' ? 0 : Number(ex.price),
            price_modifier_type: ex.price_modifier_type || 'flat',
            duration_minutes_override: ex.duration_minutes_override
              ? Number(ex.duration_minutes_override) : null,
            is_default: !!ex.is_default,
            sort_order: ex.sort_order ?? 0,
            is_active: ex.is_active !== false,
          });
        } catch (e) {
          toast.warning(t('wizards.common.extras.notCreated', { label: ex.label }));
        }
      }

      // 2026-05-20 — Clear draft + suppress unsaved prompt on navigate.
      draft.discard();
      setSubmittedSuccessfully(true);
      toast.success(t('wizards.reservation.createdToast'));
      // Redirect to the dedicated product dashboard (aligned with Event/Service wizards).
      navigate(`/reservations/${productId}`);
    } catch (err) {
      toast.error(err?.response?.data?.detail || t('wizards.common.creationError'));
    } finally {
      setSubmitting(false);
      submitLock.unlock();
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 pb-20">
      {/* Header */}
      <div className="bg-white border-b sticky top-0 z-10">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 py-3 flex items-center justify-between gap-3">
          <div className="min-w-0">
            <button onClick={() => navigate('/products?type=rental')} className="text-sm text-gray-600 hover:text-gray-900">
              {t('wizards.common.backToProducts')}
            </button>
            <h1 className="text-lg sm:text-xl font-bold text-gray-900 mt-0.5">{t('wizards.reservation.title')}</h1>
          </div>
          <div className="hidden sm:flex items-center gap-1 text-xs text-gray-500">
            {t('wizards.common.stepCounter', { current: currentTabIdx + 1, total: TABS.length })}
          </div>
        </div>

        {/* Tab bar */}
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
                <span>{t(`wizards.reservation.tabs.${tab.key}`)}</span>
                {err && <span aria-hidden>!</span>}
                {done && <span aria-hidden>✓</span>}
              </button>
            );
          })}
        </div>
      </div>

      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-6 space-y-5">

        {/* 2026-05-20 — Draft restore banner. */}
        {draft.hasDraft && (
          <DraftRestoreBanner
            savedAt={draft.savedAt}
            onRestore={draft.restore}
            onDiscard={draft.discard}
          />
        )}

        {/* ── TAB 1: Identity ─────────────────────────────────────────── */}
        {activeTab === 'identity' && (
          <div className="rounded-xl border border-gray-200 bg-white p-5 space-y-4">
            <div>
              <h2 className="text-base font-semibold text-gray-900">{t('wizards.common.identityTitle')}</h2>
              <p className="text-xs text-gray-500 mt-0.5">{t('wizards.common.identitySubtitle')}</p>
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">{t('wizards.common.nameLabel')}</label>
              <input
                type="text" value={identity.name}
                onChange={e => setIdentity({ ...identity, name: e.target.value })}
                maxLength={255}
                placeholder={t('wizards.reservation.identity.namePlaceholder')}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none"
              />
              {fieldError(errorsIdentity.name)}
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">{t('wizards.common.shortDescriptionLabel')}</label>
              <textarea
                value={identity.description}
                onChange={e => setIdentity({ ...identity, description: e.target.value })}
                rows={2} maxLength={2000}
                placeholder={t('wizards.common.shortDescriptionPlaceholder')}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none resize-none"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">{t('wizards.common.imageLabel')}</label>
              <label className="flex items-center gap-2 cursor-pointer rounded-md border border-dashed border-gray-300 px-3 py-2 text-sm text-gray-600 hover:border-gray-900">
                <span>{imageFile ? `📎 ${imageFile.name}` : t('wizards.common.imageFileLabel')}</span>
                <input
                  type="file" accept=".jpg,.jpeg,.png,.webp" className="hidden"
                  onChange={e => { setImageFile(e.target.files?.[0] || null); setIdentity(i => ({ ...i, image_url: '' })); }}
                />
              </label>
              <input
                type="url" value={identity.image_url}
                onChange={e => { setIdentity({ ...identity, image_url: e.target.value }); if (e.target.value) setImageFile(null); }}
                maxLength={500}
                placeholder={t('wizards.common.imageUrlPlaceholder')}
                className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none"
              />
            </div>

            {/* Store selection moved to the Publish tab (aligned with ServiceWizard). */}
          </div>
        )}

        {/* ── TAB 2: Flavor ───────────────────────────────────────────── */}
        {activeTab === 'flavor' && (
          <div className="rounded-xl border border-gray-200 bg-white p-5 space-y-4">
            <div>
              <h2 className="text-base font-semibold text-gray-900">{t('wizards.reservation.flavor.title')}</h2>
              <p className="text-xs text-gray-500 mt-0.5">{t('wizards.reservation.flavor.subtitle')}</p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {Object.entries(FLAVOR_PRESENTATION).map(([key, presentation]) => {
                const active = flavor === key;
                return (
                  <button
                    key={key}
                    type="button"
                    onClick={() => setFlavor(key)}
                    className={`text-left rounded-xl border p-4 transition-all ${
                      active
                        ? 'border-gray-900 bg-gray-50 shadow-sm'
                        : 'border-gray-200 hover:border-gray-400 bg-white'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="text-2xl" aria-hidden>{presentation.emoji}</div>
                      {active && <div className="text-xs font-semibold text-gray-900">{t('wizards.reservation.flavor.selected')}</div>}
                    </div>
                    <div className="text-sm font-semibold text-gray-900">{t(`wizards.reservation.flavorOptions.${key}.label`)}</div>
                    <p className="text-xs text-gray-600 mt-1 leading-snug">{t(`wizards.reservation.flavorOptions.${key}.desc`)}</p>
                    <div className="mt-2 text-[11px] text-gray-500 italic">{t(`wizards.reservation.flavorOptions.${key}.example`)}</div>
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* ── TAB 3: Pricing ──────────────────────────────────────────── */}
        {activeTab === 'pricing' && (
          <div className="rounded-xl border border-gray-200 bg-white p-5 space-y-4">
            <div>
              <h2 className="text-base font-semibold text-gray-900">{t('wizards.reservation.pricing.title')}</h2>
              <p className="text-xs text-gray-500 mt-0.5">
                {flavor === 'range'
                  ? t('wizards.reservation.pricing.subtitleRange')
                  : t('wizards.reservation.pricing.subtitleSlot')}
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">
                  {flavor === 'range'
                    ? t('wizards.reservation.pricing.priceLabelRange', { unit: t(`wizards.reservation.rentalUnits.${pricing.rental_unit}`, { defaultValue: pricing.rental_unit }) })
                    : t('wizards.reservation.pricing.priceLabelSlot')}
                </label>
                {/* 2026-05-20 — Locale-aware PriceInput. */}
                <PriceInput
                  value={pricing.unit_price}
                  onValueChange={(_n, raw) => setPricing({ ...pricing, unit_price: raw })}
                  min={0}
                  decimals={2}
                  placeholder="0,00"
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none"
                />
                {fieldError(errorsPricing.unit_price)}
              </div>

              {flavor === 'range' && (
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">{t('wizards.reservation.pricing.rentalUnitLabel')}</label>
                  <select
                    value={pricing.rental_unit}
                    onChange={e => setPricing({ ...pricing, rental_unit: e.target.value })}
                    className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none"
                  >
                    {RENTAL_UNIT_VALUES.map(value => (
                      <option key={value} value={value}>{t(`wizards.reservation.rentalUnits.${value}`, { defaultValue: value })}</option>
                    ))}
                  </select>
                  {fieldError(errorsPricing.rental_unit)}
                </div>
              )}

              {flavor === 'slot' && (
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">{t('wizards.reservation.pricing.slotDurationLabel')}</label>
                  <input
                    type="number" min="5" max="480" step="5"
                    value={pricing.slot_duration_minutes}
                    onChange={e => setPricing({ ...pricing, slot_duration_minutes: e.target.value })}
                    className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none"
                  />
                  <p className="text-[11px] text-gray-500 mt-0.5">
                    {t('wizards.reservation.pricing.slotDurationHint')}
                  </p>
                  {fieldError(errorsPricing.slot_duration_minutes)}
                </div>
              )}
            </div>

            {flavor === 'slot' && (
              <div className="rounded-lg border border-gray-200 bg-gray-50 p-3 space-y-3">
                <div>
                  <h3 className="text-sm font-semibold text-gray-900">{t('wizards.reservation.pricing.variableTitle')}</h3>
                  <p className="text-[11px] text-gray-500 mt-0.5">
                    {t('wizards.reservation.pricing.variableDescPrefix')}<span className="font-semibold">{t('wizards.reservation.pricing.variableDescHourly')}</span>: <span className="tabular-nums">{pricing.unit_price || '0.00'}</span>{t('wizards.reservation.pricing.variableDescSuffix')}
                  </p>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <div>
                    <label className="block text-[11px] font-medium text-gray-700 mb-1">{t('wizards.reservation.pricing.minDurationLabel')}</label>
                    <input
                      type="number" min="5" max="1440" step="5"
                      value={pricing.slot_min_duration_minutes}
                      onChange={e => setPricing({ ...pricing, slot_min_duration_minutes: e.target.value })}
                      placeholder={t('wizards.reservation.pricing.minDurationPlaceholder')}
                      className="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:border-gray-900 focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] font-medium text-gray-700 mb-1">{t('wizards.reservation.pricing.stepLabel')}</label>
                    <input
                      type="number" min="5" max="120" step="5"
                      value={pricing.slot_step_minutes}
                      onChange={e => setPricing({ ...pricing, slot_step_minutes: e.target.value })}
                      placeholder={t('wizards.reservation.pricing.stepPlaceholder')}
                      className="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:border-gray-900 focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] font-medium text-gray-700 mb-1">{t('wizards.reservation.pricing.maxDurationLabel')}</label>
                    <input
                      type="number" min="5" max="43200" step="5"
                      value={pricing.slot_max_duration_minutes}
                      onChange={e => setPricing({ ...pricing, slot_max_duration_minutes: e.target.value })}
                      placeholder={t('wizards.reservation.pricing.maxDurationPlaceholder')}
                      className="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:border-gray-900 focus:outline-none"
                    />
                  </div>
                </div>
              </div>
            )}

            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">{t('wizards.common.transactionModeLabel')}</label>
              <select
                value={pricing.transaction_mode}
                onChange={e => setPricing({ ...pricing, transaction_mode: e.target.value })}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none"
              >
                <option value="direct">{t('wizards.common.transactionMode.direct')}</option>
                <option value="approval">{t('wizards.common.transactionMode.approval')}</option>
                <option value="request">{t('wizards.common.transactionMode.request')}</option>
              </select>
              <StripeRequiredAlert whenTransactionMode={pricing.transaction_mode} />
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">{t('wizards.reservation.pricing.notesLabel')}</label>
              <textarea
                value={pricing.rental_notes}
                onChange={e => setPricing({ ...pricing, rental_notes: e.target.value })}
                rows={2} maxLength={500}
                placeholder={t('wizards.reservation.pricing.notesPlaceholder')}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none resize-none"
              />
            </div>

            {/* W1.S5/Phase 2.2 — Cost composition (optional). Drives
                gross-margin display in Performance Prodotti. Empty
                here is fine; margin shows N/D until configured. */}
            <div className="rounded-lg border border-gray-200 bg-gray-50 p-3 space-y-2">
              <div>
                <span className="text-sm font-medium text-gray-900">
                  {t('product_cost:section.title', 'Costo del prodotto')}
                </span>
                <p className="text-xs text-gray-500 mt-0.5">
                  {t('product_cost:section.subtitle', 'Definisci come calcolare il margine per questo prodotto.')}
                </p>
              </div>
              <CostSourceEditor
                value={costSource}
                onChange={setCostSource}
              />
            </div>
          </div>
        )}

        {/* ── TAB 4: Availability ─────────────────────────────────────── */}
        {activeTab === 'when' && (
          <div className="rounded-xl border border-gray-200 bg-white p-5 space-y-4">
            <div>
              <h2 className="text-base font-semibold text-gray-900">{t('wizards.reservation.when.title')}</h2>
              <p className="text-xs text-gray-500 mt-0.5">
                {flavor === 'range'
                  ? t('wizards.reservation.when.subtitleRange')
                  : t('wizards.reservation.when.subtitleSlot')}
              </p>
            </div>

            {flavor === 'slot' && (
              <div className="space-y-3">
                {/* Onda 15 parity with ServiceWizard: let the merchant defer to
                    the store-level calendar instead of defining per-product rules. */}
                <label className="flex items-start gap-2 rounded-lg border border-gray-200 bg-gray-50/50 p-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={useDefaultSchedule}
                    onChange={(e) => setUseDefaultSchedule(e.target.checked)}
                    className="mt-0.5"
                  />
                  <span className="text-sm">
                    <span className="font-medium text-gray-900">
                      {t('wizards.reservation.when.useStoreCalendarTitle')}
                    </span>
                    <p className="text-xs text-gray-500 mt-0.5">
                      {t('wizards.reservation.when.useStoreCalendarDesc')}
                    </p>
                  </span>
                </label>

                {useDefaultSchedule ? (
                  <div className="rounded-lg bg-blue-50 border border-blue-200 p-3 text-xs text-blue-900">
                    {t('wizards.reservation.when.storeCalendarHint')}
                  </div>
                ) : (
                  <AvailabilityRulesEditor rules={rules} onChange={setRules} />
                )}
              </div>
            )}

            {flavor === 'range' && (
              <div className="rounded-lg bg-blue-50 border border-blue-200 p-3 text-xs text-blue-900">
                {t('wizards.reservation.when.rangeNoRulesHint')}
              </div>
            )}
          </div>
        )}

        {/* ── TAB 5: Extras ───────────────────────────────────────────── */}
        {activeTab === 'extras' && (
          <div className="rounded-xl border border-gray-200 bg-white p-5 space-y-4">
            <ProductExtrasEditor
              extras={extras}
              onChange={setExtras}
              productItemType="rental"
              title={t('wizards.reservation.extras.title')}
            />
          </div>
        )}

        {/* ── TAB 6: Publish ──────────────────────────────────────────── */}
        {activeTab === 'publish' && (
          <div className="rounded-xl border border-gray-200 bg-white p-5 space-y-4">
            <div>
              <h2 className="text-base font-semibold text-gray-900">{t('wizards.common.publishTitle')}</h2>
              <p className="text-xs text-gray-500 mt-0.5">
                {t('wizards.common.publishSubtitle')}
              </p>
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">{t('wizards.common.termsTitle')}</label>
              <textarea
                value={termsContent}
                onChange={e => setTermsContent(e.target.value)}
                rows={4} maxLength={5000}
                placeholder={t('wizards.reservation.publish.termsPlaceholder')}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none resize-none"
              />
              <p className="text-[11px] text-gray-400 mt-1">{t('wizards.common.termsHint')}</p>
            </div>

            {/* Distribuzione — canonical store assignment pattern (mirror ServiceWizard).
                Always visible so the merchant understands where the product will appear.
                Single-store: banner informativo.
                Multi-store: checkbox "Tutti gli store" + checkbox per singolo store. */}
            <div className="rounded-lg border border-gray-200 p-3 space-y-2">
              <h3 className="text-sm font-semibold text-gray-900">{t('wizards.common.distribution.title')}</h3>
              {availableStores.length <= 1 ? (
                <>
                  <p className="text-xs text-gray-500">
                    {t('wizards.reservation.publish.distributionDesc')}
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
                  <p className="text-xs text-gray-500">{t('wizards.reservation.publish.distributionMultiDesc')}</p>
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

            <label className="flex items-start gap-2 rounded-lg border border-gray-200 p-3 bg-gray-50/50 cursor-pointer">
              <input
                type="checkbox"
                checked={publishNow}
                onChange={e => setPublishNow(e.target.checked)}
                className="mt-0.5"
              />
              <div>
                <div className="text-sm font-medium text-gray-900">{t('wizards.reservation.publish.publishToggleTitle')}</div>
                <div className="text-xs text-gray-500 mt-0.5">
                  {t('wizards.reservation.publish.publishToggleDesc')}
                </div>
              </div>
            </label>
          </div>
        )}

        {/* Nav */}
        <div className="flex items-center justify-between gap-3 pt-2">
          <button
            type="button"
            onClick={prevTab}
            disabled={currentTabIdx === 0}
            className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-40"
          >{t('wizards.common.back')}</button>

          {activeTab !== 'publish' ? (
            <button
              type="button"
              onClick={nextTab}
              className="rounded-md bg-gray-900 text-white px-4 py-2 text-sm font-semibold hover:bg-gray-800"
            >{t('wizards.common.next')}</button>
          ) : (
            <button
              type="button"
              onClick={onSubmit}
              disabled={!allValid || submitting}
              className="rounded-md bg-gray-900 text-white px-4 py-2 text-sm font-semibold hover:bg-gray-800 disabled:opacity-50"
            >
              {submitting ? t('wizards.common.creating') : (publishNow ? t('wizards.common.createPublishCta') : t('wizards.common.createDraftCta'))}
            </button>
          )}
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
