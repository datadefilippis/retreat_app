/**
 * PhysicalWizard — guided 5-step flow to create a physical (stockable) product.
 *
 * Release 2 (Physical pattern parity, A2): brings physical into the same wizard
 * shape as rental / service / event_ticket so merchants have a single mental
 * model regardless of product type.
 *
 * Tabs:
 *   1. Identità    — name, description, image, SKU, category
 *   2. Prezzo & stock — unit_price, stock tracking toggle + quantity, transaction_mode
 *   3. Fulfillment — fulfillment_notes + preview of store's fulfillment_modes
 *                    (no editing of modes here — those live on the store settings)
 *   4. Extras      — shared ProductExtrasEditor (mandatory / optional / radio groups)
 *   5. Pubblica    — T&C override, distribution across stores, is_published toggle
 *
 * Submission: POST /products with item_type=physical, empty metadata
 * (PhysicalMetadata is intentionally a placeholder — Release 1 decision), then
 * extras CRUD and image upload as sub-steps. A sub-step failure leaves the
 * product in place with a warning toast so the merchant can fix from the
 * dashboard.
 */

import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import useProductTaxonomies from '../../hooks/useProductTaxonomies';
import { useNavigate } from 'react-router-dom';
import { useTranslation, Trans } from 'react-i18next';
import { toast } from 'sonner';
import { productsAPI } from '../../api';
import { storesAPI } from '../../api/stores';
import { productExtrasAPI } from '../../api/productExtras';
import ProductExtrasEditor from '../reservations/components/ProductExtrasEditor';
import StripeRequiredAlert from '../../components/StripeRequiredAlert';
// W1.S5b — additive cost composition editor. Lives inside the "Prezzo
// & stock" step so the merchant configures price and the cost basis
// for margin calculation in a single screen.
import CostSourceEditor from '../products/components/CostSourceEditor';

// 2026-05-20 — Hardening helpers (audit fix wave). All additive, no
// behavioural changes to the existing wizard flow:
//   · PriceInput        — accepts both "10,50" and "10.50" (IT locale fix)
//   · SkuField          — debounced live uniqueness check
//   · useSubmitLock     — atomic double-submit guard (ref-based)
//   · useUnsavedChangesPrompt + UnsavedChangesDialog — router + beforeunload
//   · useWizardDraft + DraftRestoreBanner — localStorage autosave
//   · useAbortableUpload — cancel uploadImage on unmount
//   · showImageUploadFailedToast — persistent toast w/ Retry button
import { useAuth } from '../../context/AuthContext';
import { PriceInput } from '../../components/ui/PriceInput';
import { SkuField } from '../../components/ui/SkuField';
import { UnsavedChangesDialog } from '../../components/ui/UnsavedChangesDialog';
import { DraftRestoreBanner } from '../../components/ui/DraftRestoreBanner';
import { useSubmitLock } from '../../hooks/useSubmitLock';
import { useUnsavedChangesPrompt } from '../../hooks/useUnsavedChangesPrompt';
import { useWizardDraft } from '../../hooks/useWizardDraft';
import { useAbortableUpload } from '../../hooks/useAbortableUpload';
import { showImageUploadFailedToast } from '../../lib/imageUploadFailedToast';
import MultiLangText from '../../components/MultiLangText';


// Tabs are addressed by stable `key`. Visible labels are resolved at
// render time via t('wizards.physical.tabs.<key>') so translations stay
// in the JSON catalog. The `n` index is the 1-based step number shown
// in the tab pill — also used for the "Step n of N" header.
const TABS = [
  { key: 'identity',    n: 1 },
  { key: 'pricing',     n: 2 },
  { key: 'fulfillment', n: 3 },
  { key: 'extras',      n: 4 },
  { key: 'publish',     n: 5 },
];


function validateIdentity(v, t) {
  const e = {};
  if (!v.name?.trim()) e.name = t('wizards.common.validation.nameRequired');
  return e;
}

function validatePricing(v, t) {
  const e = {};
  if (v.unit_price !== '' && Number(v.unit_price) < 0) e.unit_price = t('wizards.common.validation.priceInvalid');
  // When stock tracking is on, stock_quantity must be a non-negative integer.
  if (v.track_stock) {
    const n = Number(v.stock_quantity);
    if (v.stock_quantity === '' || Number.isNaN(n) || n < 0 || !Number.isInteger(n)) {
      e.stock_quantity = t('wizards.physical.validation.stockInvalid');
    }
  }
  return e;
}


export default function PhysicalWizard() {
  const taxonomies = useProductTaxonomies();
  const navigate = useNavigate();
  const { t } = useTranslation('products');

  const [activeTab, setActiveTab] = useState('identity');
  const [submitting, setSubmitting] = useState(false);

  // Step 1 — identity
  const [identity, setIdentity] = useState({
    name: '',
    description: '',
    image_url: '',
    sku: '',
    category: '',
  });
  const [imageFile, setImageFile] = useState(null);
  // Multilingua manuale — le lingue offerte decidono dove il prodotto appare
  const [trDescription, setTrDescription] = useState({});
  const [storeIds, setStoreIds] = useState([]);
  const [availableStores, setAvailableStores] = useState([]);

  // Step 2 — pricing + stock
  //   track_stock=false → stock_quantity is left null (untracked, always available).
  //   track_stock=true  → stock_quantity is persisted as an integer ≥ 0; backend
  //                       enforces atomic decrement at confirm and restoration
  //                       at cancel.
  const [pricing, setPricing] = useState({
    unit_price: '',
    track_stock: false,
    stock_quantity: '',
    transaction_mode: 'direct',
  });
  // W1.S5b — additive cost composition. Null means the merchant hasn't
  // configured any cost component yet (perfectly valid; margin will
  // simply show N/D in Performance Prodotti). When non-null, the
  // CostSourceEditor below populates this with {method, components}.
  const [costSource, setCostSource] = useState(null);

  // Step 3 — fulfillment (admin-facing notes + preview of store modes).
  const [fulfillmentNotes, setFulfillmentNotes] = useState('');

  // Step 4 — extras
  const [extras, setExtras] = useState([]);

  // Step 5 — publish + legal
  const [publishNow, setPublishNow] = useState(false);
  const [termsContent, setTermsContent] = useState('');

  // ── 2026-05-20 — Hardening hooks ────────────────────────────────────
  //
  // Aggregate all wizard state into a single ``formData`` object so the
  // draft autosave hook can persist it as one JSON blob, and so the
  // dirty-detection can compare against a stable initial snapshot.
  // ``imageFile`` is intentionally excluded — File objects can't be
  // serialised to localStorage. On restore the merchant re-attaches.
  const formData = useMemo(() => ({
    identity, pricing, costSource, fulfillmentNotes,
    extras, publishNow, termsContent, storeIds,
  }), [
    identity, pricing, costSource, fulfillmentNotes,
    extras, publishNow, termsContent, storeIds,
  ]);

  // Apply a restored draft back into the per-section setters. We
  // deliberately accept partial drafts (an older saved version may
  // lack a field added later) — each key is restored only when present.
  const applyDraft = useCallback((draft) => {
    if (!draft || typeof draft !== 'object') return;
    if (draft.identity) setIdentity(draft.identity);
    if (draft.pricing) setPricing(draft.pricing);
    if ('costSource' in draft) setCostSource(draft.costSource);
    if ('fulfillmentNotes' in draft) setFulfillmentNotes(draft.fulfillmentNotes);
    if (Array.isArray(draft.extras)) setExtras(draft.extras);
    if ('publishNow' in draft) setPublishNow(!!draft.publishNow);
    if ('termsContent' in draft) setTermsContent(draft.termsContent);
    if (Array.isArray(draft.storeIds)) setStoreIds(draft.storeIds);
  }, []);

  // Dirty-detection: compare current formData against the mount-time
  // snapshot. ``submittedSuccessfully`` short-circuits the prompt after
  // a successful POST so the post-create navigate doesn't trigger the
  // "unsaved changes" dialog. JSON.stringify is fine for the form size
  // we have (~8 fields, no deep objects).
  const initialFormDataRef = useRef(null);
  useEffect(() => {
    if (initialFormDataRef.current === null) {
      initialFormDataRef.current = JSON.stringify(formData);
    }
    // intentionally mount-only — subsequent renders compare against the
    // stable snapshot, not a moving target.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  const [submittedSuccessfully, setSubmittedSuccessfully] = useState(false);
  const isDirty = useMemo(() => {
    if (submittedSuccessfully) return false;
    if (initialFormDataRef.current === null) return false;
    return JSON.stringify(formData) !== initialFormDataRef.current
      || imageFile !== null;
  }, [formData, imageFile, submittedSuccessfully]);

  // Submit lock — atomic, synchronous, ref-based. Prevents double-POST
  // even if React hasn't re-rendered the disabled button yet.
  const submitLock = useSubmitLock();

  // Unsaved-changes prompt — registers beforeunload + router blocker
  // while ``isDirty`` is true. Returns a blocker we render below as
  // a confirm dialog.
  const { blocker } = useUnsavedChangesPrompt(isDirty);

  // Wizard draft — autosave to localStorage every 800ms while editing,
  // restore on next mount if a draft <24h old exists, discard on
  // successful POST.
  const { user } = useAuth();
  const scopeKey = user?.id || user?.email || 'anonymous';
  const draft = useWizardDraft({
    wizardKey: 'physical-create',
    scopeKey,
    formData,
    setFormData: applyDraft,
  });

  // Abortable upload — cancels in-flight image POST if the wizard
  // unmounts mid-upload (navigation away, tab close).
  const upload = useAbortableUpload();

  const loadStores = useCallback(async () => {
    try {
      const res = await storesAPI.list();
      setAvailableStores(res.data?.stores || []);
    } catch { /* optional */ }
  }, []);
  useEffect(() => { loadStores(); }, [loadStores]);

  const errorsIdentity = useMemo(() => validateIdentity(identity, t), [identity, t]);
  const errorsPricing = useMemo(() => validatePricing(pricing, t), [pricing, t]);

  const identityValid = Object.keys(errorsIdentity).length === 0;
  const pricingValid = Object.keys(errorsPricing).length === 0;
  const extrasValid = extras.every(e => {
    if (!e.label?.trim()) return false;
    if (e.kind === 'radio_variant' && !e.group_key) return false;
    if (e.price !== 0 && e.price !== '' && Number(e.price) < 0) return false;
    return true;
  });
  const allValid = identityValid && pricingValid && extrasValid;

  const tabHasErrors = {
    identity: !identityValid,
    pricing: !pricingValid,
    fulfillment: false,  // no required fields in this step
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

  // Store fulfillment modes preview — union across the selected stores (or all
  // stores when "Tutti gli store" is active). Shown in the Fulfillment tab so
  // the merchant knows which modes a customer will be able to pick at checkout.
  const previewFulfillmentModes = useMemo(() => {
    const targets = storeIds.length > 0
      ? availableStores.filter(s => storeIds.includes(s.id))
      : availableStores;
    const set = new Set();
    for (const s of targets) {
      for (const m of (s.fulfillment_modes || ['shipping'])) set.add(m);
    }
    return Array.from(set);
  }, [storeIds, availableStores]);

  const onSubmit = async () => {
    if (!allValid) { toast.error(t('wizards.common.correctErrors')); return; }
    // 2026-05-20 — Atomic ref-based lock to prevent double-submit on
    // fast double-click before React has re-rendered the disabled button.
    if (!submitLock.tryLock()) return;
    setSubmitting(true);
    try {
      // PhysicalMetadata is intentionally a placeholder today (Release 1 decision).
      // We still persist fulfillment_notes + terms_content in metadata so they
      // survive round-trips and can be surfaced in the admin dashboard.
      const metadata = {
        fulfillment_notes: fulfillmentNotes?.trim() || null,
        terms_content: termsContent?.trim() || null,
      };

      const productPayload = {
        name: identity.name.trim(),
        description: identity.description?.trim() || null,
        translations: (() => {
          const out = {};
          Object.entries(trDescription).forEach(([l, v]) => {
            if ((v || '').trim()) out[l] = { description: v.trim() };
          });
          return out;
        })(),
        image_url: identity.image_url?.trim() || null,
        unit_price: pricing.unit_price !== '' ? Number(pricing.unit_price) : null,
        sku: identity.sku?.trim() || null,
        category: identity.category?.trim() || null,
        item_type: 'physical',
        price_mode: 'fixed',
        transaction_mode: pricing.transaction_mode,
        is_published: publishNow,
        store_ids: storeIds,
        // Null = untracked (always available). Positive integer = tracked with
        // atomic decrement at confirm_order. Same contract as the legacy inline
        // form in ProductsPage so existing orders stay compatible.
        stock_quantity: pricing.track_stock && pricing.stock_quantity !== ''
          ? Number(pricing.stock_quantity)
          : null,
        metadata,
        // W1.S5b — additive cost composition. Null when the merchant
        // skipped the cost configuration; the backend resolver returns
        // margin=N/D for such products. When set, takes precedence over
        // the deprecated cost_price field for all margin calculations.
        cost_source: costSource,
      };

      const createRes = await productsAPI.create(productPayload);
      const productId = createRes.data?.id;
      if (!productId) throw new Error('Product creation returned no id');

      // 2026-05-20 — Abortable upload + persistent retry toast.
      // If the upload fails after the product was created, show a
      // toast with a Retry action button instead of a 3s warning that
      // the merchant might miss.
      if (imageFile) {
        const fileToUpload = imageFile;  // capture for retry closure
        try {
          const res = await upload.run((signal) =>
            productsAPI.uploadImage(productId, fileToUpload, { signal }),
          );
          // res === null means the upload was aborted (unmount) — silent.
          if (res === null) {
            // No-op: the upload was cancelled, product still exists
            // without image and the user navigated away.
          }
        } catch (e) {
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

      // Extras — same pattern as the other wizards (best-effort per-row).
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

      // Success path — clear the draft, suppress the unsaved-changes
      // prompt on the navigation that follows, and navigate.
      draft.discard();
      setSubmittedSuccessfully(true);
      toast.success(t('wizards.common.productCreated'));
      navigate(`/physicals/${productId}`);
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
            <button onClick={() => navigate('/products?type=physical')} className="text-sm text-gray-600 hover:text-gray-900">
              {t('wizards.common.backToProducts')}
            </button>
            <h1 className="text-lg sm:text-xl font-bold text-gray-900 mt-0.5">{t('wizards.physical.title')}</h1>
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
                <span>{t(`wizards.physical.tabs.${tab.key}`)}</span>
                {err && <span aria-hidden>!</span>}
                {done && <span aria-hidden>✓</span>}
              </button>
            );
          })}
        </div>
      </div>

      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-6 space-y-5">

        {/* 2026-05-20 — Restore banner shown only when a draft <24h old
            was detected on mount. The merchant can resume work where
            they left off (e.g. after a tab close, JWT expiry, accidental
            back-button). Persisted only between mounts of THIS wizard
            and scoped per-user so different operators on the same
            machine don't see each other's drafts. */}
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
                placeholder={t('wizards.physical.identity.namePlaceholder')}
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
              <MultiLangText value={trDescription} onChange={setTrDescription} rows={2} maxLength={2000} />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">{t('wizards.common.skuLabel')}</label>
                {/* 2026-05-20 — SkuField wraps the input with a debounced
                    GET /products/check-sku probe so the merchant sees a
                    green check / red X / loader while typing, instead of
                    waiting until "Crea prodotto" to discover a conflict. */}
                <SkuField
                  value={identity.sku}
                  onChange={e => setIdentity({ ...identity, sku: e.target.value })}
                  maxLength={120}
                  placeholder={t('wizards.physical.identity.skuPlaceholder')}
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">{t('wizards.common.categoryLabel')}</label>
                {/* V4 — dropdown dalla tassonomia (mai testo libero:
                    fatica per l'operatore, zero valore per il visitatore) */}
                <select
                  value={identity.category || ''}
                  onChange={e => setIdentity({ ...identity, category: e.target.value })}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none bg-white"
                >
                  <option value="">{t('wizards.common.categoryNone', { defaultValue: 'Nessuna categoria' })}</option>
                  {Object.entries(taxonomies.physical || {}).map(([k, label]) => (
                    <option key={k} value={k}>{label}</option>
                  ))}
                </select>
              </div>
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
          </div>
        )}

        {/* ── TAB 2: Pricing + Stock ──────────────────────────────────── */}
        {activeTab === 'pricing' && (
          <div className="rounded-xl border border-gray-200 bg-white p-5 space-y-4">
            <div>
              <h2 className="text-base font-semibold text-gray-900">{t('wizards.physical.pricing.title')}</h2>
              <p className="text-xs text-gray-500 mt-0.5">
                {t('wizards.physical.pricing.subtitle')}
              </p>
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">{t('wizards.common.basePriceLabel')}</label>
              {/* 2026-05-20 — PriceInput accepts both "10,50" (Italian
                  locale) and "10.50" (US/EN locale), parses to a
                  canonical JS number, and exposes both the parsed value
                  and the raw display string. The parent state still
                  receives a string (its existing shape) but normalised
                  on blur so the payload's Number(unit_price) keeps
                  working unchanged. */}
              <PriceInput
                value={pricing.unit_price}
                onValueChange={(num, raw) => setPricing({ ...pricing, unit_price: raw })}
                min={0}
                decimals={2}
                placeholder="0,00"
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none"
              />
              {fieldError(errorsPricing.unit_price)}
            </div>

            <div className="rounded-lg border border-gray-200 bg-gray-50 p-3 space-y-3">
              <label className="flex items-start gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={pricing.track_stock}
                  onChange={e => {
                    const on = e.target.checked;
                    setPricing(p => ({
                      ...p,
                      track_stock: on,
                      // Default to 0 when turning on — merchant picks the real
                      // number immediately. Clear on turn-off so the payload is
                      // null (untracked).
                      stock_quantity: on ? (p.stock_quantity !== '' ? p.stock_quantity : '0') : '',
                    }));
                  }}
                  className="mt-0.5 rounded border-gray-300 text-gray-900 focus:ring-gray-900"
                />
                <span>
                  <span className="text-sm font-medium text-gray-900">{t('wizards.physical.pricing.trackStockTitle')}</span>
                  <p className="text-xs text-gray-500 mt-0.5">
                    {t('wizards.physical.pricing.trackStockDesc')}
                  </p>
                </span>
              </label>
              {pricing.track_stock && (
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">{t('wizards.physical.pricing.stockQuantityLabel')}</label>
                  {/* 2026-05-20 — Added explicit max=1000000. Without it
                      the input accepted any positive integer (devtools
                      bypass aside, even regular typing): a typo of "0"
                      pasted multiple times reached the safe-integer
                      space and the create silently succeeded with a
                      nonsense stock value. 1M items is a generous cap
                      for SME inventories — server validates again. */}
                  <input
                    type="number" min="0" step="1" max="1000000"
                    value={pricing.stock_quantity}
                    onChange={e => setPricing({ ...pricing, stock_quantity: e.target.value })}
                    placeholder="0"
                    className="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:border-gray-900 focus:outline-none"
                  />
                  {fieldError(errorsPricing.stock_quantity)}
                </div>
              )}
            </div>

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
              {/* Surfaces a warning when "Diretto" is selected on an org
                  that hasn't completed Stripe Connect onboarding —
                  storefront would otherwise silently fall back to
                  "Richiesta" at checkout. */}
              <StripeRequiredAlert whenTransactionMode={pricing.transaction_mode} />
            </div>

            {/* ── W1.S5b — Cost composition for margin calculation.
                Optional: when the merchant skips this section, the
                product saves successfully with no cost set (margin
                shows N/D in Performance Prodotti). When configured,
                the cost feeds the resolver at refresh time. */}
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

        {/* ── TAB 3: Fulfillment ──────────────────────────────────────── */}
        {activeTab === 'fulfillment' && (
          <div className="rounded-xl border border-gray-200 bg-white p-5 space-y-4">
            <div>
              <h2 className="text-base font-semibold text-gray-900">{t('wizards.physical.fulfillment.title')}</h2>
              <p className="text-xs text-gray-500 mt-0.5">
                {t('wizards.physical.fulfillment.subtitle')}
              </p>
            </div>

            <div className="rounded-lg bg-blue-50 border border-blue-200 p-3 text-xs text-blue-900">
              <p className="font-semibold mb-1">{t('wizards.physical.fulfillment.modesEnabled')}</p>
              {previewFulfillmentModes.length === 0 ? (
                <p>
                  <Trans
                    i18nKey="wizards.physical.fulfillment.noStores"
                    ns="products"
                    components={{ em: <em /> }}
                  />
                </p>
              ) : (
                <ul className="space-y-0.5">
                  {previewFulfillmentModes.includes('shipping') && (
                    <li>📦 <Trans
                      i18nKey="wizards.physical.fulfillment.shipping"
                      ns="products"
                      components={{ strong: <strong /> }}
                    /></li>
                  )}
                  {previewFulfillmentModes.includes('local_pickup') && (
                    <li>🏪 <Trans
                      i18nKey="wizards.physical.fulfillment.localPickup"
                      ns="products"
                      components={{ strong: <strong /> }}
                    /></li>
                  )}
                </ul>
              )}
              <p className="mt-1 text-[11px] text-blue-800">
                {t('wizards.physical.fulfillment.modesHint')}
              </p>
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">{t('wizards.physical.fulfillment.notesLabel')}</label>
              <textarea
                value={fulfillmentNotes}
                onChange={e => setFulfillmentNotes(e.target.value)}
                rows={3} maxLength={500}
                placeholder={t('wizards.physical.fulfillment.notesPlaceholder')}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none resize-none"
              />
              <p className="text-[11px] text-gray-400 mt-1">
                {t('wizards.physical.fulfillment.notesHint')}
              </p>
            </div>
          </div>
        )}

        {/* ── TAB 4: Extras ───────────────────────────────────────────── */}
        {activeTab === 'extras' && (
          <div className="rounded-xl border border-gray-200 bg-white p-5 space-y-4">
            <ProductExtrasEditor
              extras={extras}
              onChange={setExtras}
              productItemType="physical"
              title={t('wizards.physical.extras.title')}
            />
          </div>
        )}

        {/* ── TAB 5: Publish ──────────────────────────────────────────── */}
        {activeTab === 'publish' && (
          <div className="rounded-xl border border-gray-200 bg-white p-5 space-y-4">
            <div>
              <h2 className="text-base font-semibold text-gray-900">{t('wizards.common.publishTitle')}</h2>
              <p className="text-xs text-gray-500 mt-0.5">{t('wizards.common.publishSubtitle')}</p>
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">{t('wizards.common.termsTitle')}</label>
              <textarea
                value={termsContent}
                onChange={e => setTermsContent(e.target.value)}
                rows={4} maxLength={5000}
                placeholder={t('wizards.physical.publish.termsPlaceholder')}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none resize-none"
              />
              <p className="text-[11px] text-gray-400 mt-1">{t('wizards.common.termsHint')}</p>
            </div>

            {/* Store distribution — same pattern as ReservationWizard. */}
            <div className="rounded-lg border border-gray-200 p-3 space-y-2">
              <h3 className="text-sm font-semibold text-gray-900">{t('wizards.common.distribution.title')}</h3>
              {availableStores.length <= 1 ? (
                <>
                  <p className="text-xs text-gray-500">{t('wizards.physical.publish.distributionDesc')}</p>
                  <div className="rounded-md bg-gray-50 border border-gray-200 px-3 py-2 text-sm text-gray-700 flex items-center gap-2">
                    <span aria-hidden>✓</span>
                    <span>
                      {t('wizards.common.distribution.visibleAutoPrefix')} <strong>{availableStores[0]?.name || t('wizards.common.distribution.allStoresFallback')}</strong>
                    </span>
                  </div>
                </>
              ) : (
                <>
                  <p className="text-xs text-gray-500">{t('wizards.physical.publish.distributionMultiDesc')}</p>
                  <label className="flex items-center gap-2 text-sm cursor-pointer">
                    <input
                      type="checkbox"
                      checked={!storeIds.length}
                      onChange={() => setStoreIds([])}
                      className="rounded border-gray-300"
                    />
                    <span className={!storeIds.length ? 'font-medium' : 'text-gray-500'}>{t('wizards.common.distribution.allStoresLabel')}</span>
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
                <div className="text-sm font-medium text-gray-900">{t('wizards.physical.publish.publishToggleTitle')}</div>
                <div className="text-xs text-gray-500 mt-0.5">
                  {t('wizards.physical.publish.publishToggleDesc')}
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

      {/* 2026-05-20 — Unsaved-changes confirm dialog. Renders ONLY when
          the router blocker fires (in-app navigation attempted while
          isDirty). beforeunload (native tab close) is handled by the
          same hook via window-level listener. */}
      <UnsavedChangesDialog
        open={blocker?.state === 'blocked'}
        onConfirm={() => blocker?.proceed?.()}
        onCancel={() => blocker?.reset?.()}
      />
    </div>
  );
}
