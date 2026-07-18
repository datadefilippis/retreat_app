/**
 * DigitalWizard — guided 6-step flow to create a digital product.
 *
 * Release 3 (Digital) B8. Mirrors PhysicalWizard with two additions:
 *   - Tab "File digitale": upload the payload via the dedicated private
 *     storage endpoint (NOT the public StaticFiles mount). Publishing is
 *     gated on a successful upload so no customer can land on a product
 *     with no file attached.
 *   - Tab "Policy accesso": max_downloads_per_delivery + access_expiry_days
 *     knobs that flow into the IssuedDownload rows at confirm_order time.
 *
 * Tabs:
 *   1. Identità       — name, description, image, SKU, category
 *   2. Prezzo & stock — unit_price, stock tracking toggle + quantity,
 *                       transaction_mode
 *   3. File digitale  — upload with size/type preview + replace
 *   4. Policy         — max downloads per delivery, link TTL days,
 *                       long_description
 *   5. Extras         — shared ProductExtrasEditor
 *   6. Pubblica       — T&C override, distribution, is_published
 *                       (disabled until file is uploaded)
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
// Wave 1 (W1.S5/Phase 2.3) — additive cost composition. Digital
// products typically have low/zero unit cost (hosting amortised) so
// the empty state is the common case — the editor is still shown so
// merchants who care can declare it.

// 2026-05-20 — Hardening helpers (audit fix wave). See PhysicalWizard
// for the design rationale of each.
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
import MultiLangSection from '../../components/MultiLangSection';


// Tabs are addressed by stable `key`. Visible labels are resolved at
// render time via t('wizards.digital.tabs.<key>') so translations stay
// in the JSON catalog.
const TABS = [
  { key: 'identity', n: 1 },
  { key: 'pricing',  n: 2 },
  { key: 'file',     n: 3 },
  { key: 'policy',   n: 4 },
  { key: 'extras',   n: 5 },
  { key: 'publish',  n: 6 },
];


function validateIdentity(v, t) {
  const e = {};
  if (!v.name?.trim()) e.name = t('wizards.common.validation.nameRequired');
  return e;
}

function validatePricing(v, t) {
  const e = {};
  if (v.unit_price !== '' && Number(v.unit_price) < 0) e.unit_price = t('wizards.common.validation.priceInvalid');
  if (v.track_stock) {
    const n = Number(v.stock_quantity);
    if (v.stock_quantity === '' || Number.isNaN(n) || n < 0 || !Number.isInteger(n)) {
      e.stock_quantity = t('wizards.digital.validation.stockInvalid');
    }
  }
  return e;
}

function validatePolicy(v, t) {
  const e = {};
  if (v.max_downloads !== '' && v.max_downloads !== null) {
    const n = Number(v.max_downloads);
    if (!Number.isInteger(n) || n < 1 || n > 100) {
      e.max_downloads = t('wizards.digital.validation.maxDownloadsRange');
    }
  }
  if (v.access_expiry_days !== '' && v.access_expiry_days !== null) {
    const n = Number(v.access_expiry_days);
    if (!Number.isInteger(n) || n < 1 || n > 3650) {
      e.access_expiry_days = t('wizards.digital.validation.expiryRange');
    }
  }
  return e;
}


function formatBytes(n) {
  if (!n || n <= 0) return '';
  const kb = n / 1024;
  if (kb < 1024) return `${kb.toFixed(0)} KB`;
  const mb = kb / 1024;
  if (mb < 1024) return `${mb.toFixed(1)} MB`;
  return `${(mb / 1024).toFixed(2)} GB`;
}


export default function DigitalWizard() {
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
  const [storeIds, setStoreIds] = useState([]);
  const [availableStores, setAvailableStores] = useState([]);

  // Step 2 — pricing + stock
  const [pricing, setPricing] = useState({
    unit_price: '',
    track_stock: false,
    stock_quantity: '',
    transaction_mode: 'direct',
  });
  // Wave 1 (W1.S5/Phase 2.3) — cost composition for margin calculation.
  // Null when unconfigured; resolver returns margin=N/D. Digital
  // products typically leave this null (negligible unit cost).
  const [costSource, setCostSource] = useState(null);

  // Step 3 — digital file. The upload happens AFTER product creation (we
  // need product.id for the API path), so here we only stage the File.
  const [digitalFile, setDigitalFile] = useState(null);
  // Step 4 — policy
  const [policy, setPolicy] = useState({
    max_downloads: '',
    access_expiry_days: '',
    long_description: '',
  });

  // Multilingua manuale — le lingue offerte decidono dove il prodotto appare
  const [trName, setTrName] = useState({});
  const [trDescription, setTrDescription] = useState({});
  const [trLong, setTrLong] = useState({});

  // Step 5 — extras
  const [extras, setExtras] = useState([]);

  // Step 6 — publish + legal
  const [publishNow, setPublishNow] = useState(false);
  const [termsContent, setTermsContent] = useState('');

  const loadStores = useCallback(async () => {
    try {
      const res = await storesAPI.list();
      setAvailableStores(res.data?.stores || []);
    } catch { /* optional */ }
  }, []);
  useEffect(() => { loadStores(); }, [loadStores]);

  // ── 2026-05-20 — Hardening hooks ────────────────────────────────────
  // ``digitalFile`` is intentionally excluded from the draft (File obj
  // can't be JSON-serialised). On restore the merchant re-attaches the
  // file before publishing.
  const formData = useMemo(() => ({
    identity, pricing, costSource, policy,
    extras, publishNow, termsContent, storeIds,
  }), [
    identity, pricing, costSource, policy,
    extras, publishNow, termsContent, storeIds,
  ]);

  const applyDraft = useCallback((d) => {
    if (!d || typeof d !== 'object') return;
    if (d.identity) setIdentity(d.identity);
    if (d.pricing) setPricing(d.pricing);
    if ('costSource' in d) setCostSource(d.costSource);
    if (d.policy) setPolicy(d.policy);
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
      || imageFile !== null || digitalFile !== null;
  }, [formData, imageFile, digitalFile, submittedSuccessfully]);

  const submitLock = useSubmitLock();
  const { blocker } = useUnsavedChangesPrompt(isDirty);
  const { user } = useAuth();
  const scopeKey = user?.id || user?.email || 'anonymous';
  const draft = useWizardDraft({
    wizardKey: 'digital-create',
    scopeKey,
    formData,
    setFormData: applyDraft,
  });
  const imageUpload = useAbortableUpload();
  const digitalUpload = useAbortableUpload();

  const errorsIdentity = useMemo(() => validateIdentity(identity, t), [identity, t]);
  const errorsPricing = useMemo(() => validatePricing(pricing, t), [pricing, t]);
  const errorsPolicy = useMemo(() => validatePolicy(policy, t), [policy, t]);

  const identityValid = Object.keys(errorsIdentity).length === 0;
  const pricingValid = Object.keys(errorsPricing).length === 0;
  const fileValid = !!digitalFile;          // upload required before publish
  const policyValid = Object.keys(errorsPolicy).length === 0;
  const extrasValid = extras.every(e => {
    if (!e.label?.trim()) return false;
    if (e.kind === 'radio_variant' && !e.group_key) return false;
    if (e.price !== 0 && e.price !== '' && Number(e.price) < 0) return false;
    return true;
  });
  // Publish is blocked without a file — enforces the backend "digital_file_missing"
  // validation at admin time so the merchant fixes it here rather than via a
  // customer-facing 400.
  const canPublish = identityValid && pricingValid && fileValid && policyValid && extrasValid;
  const canDraft = identityValid && pricingValid && policyValid && extrasValid;
  const allValid = publishNow ? canPublish : canDraft;

  const tabHasErrors = {
    identity: !identityValid,
    pricing: !pricingValid,
    file: false,
    policy: !policyValid,
    extras: !extrasValid,
    publish: publishNow && !canPublish,
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
      // Policy + copy go into DigitalMetadata. Empty strings become null so
      // the backend default (unlimited downloads, no expiry) kicks in.
      const _num = (v) => {
        const n = Number(v);
        return v === '' || v === null || Number.isNaN(n) || n <= 0 ? null : n;
      };
      const metadata = {
        long_description: policy.long_description?.trim() || null,
        terms_content: termsContent?.trim() || null,
      };
      const mx = _num(policy.max_downloads);
      const exp = _num(policy.access_expiry_days);
      if (mx) metadata.max_downloads_per_delivery = mx;
      if (exp) metadata.access_expiry_days = exp;

      const productPayload = {
        name: identity.name.trim(),
        description: identity.description?.trim() || null,
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
        image_url: identity.image_url?.trim() || null,
        unit_price: pricing.unit_price !== '' ? Number(pricing.unit_price) : null,
        sku: identity.sku?.trim() || null,
        category: identity.category?.trim() || null,
        item_type: 'digital',
        price_mode: 'fixed',
        transaction_mode: pricing.transaction_mode,
        // Publish NEVER flips to true when the file upload step failed —
        // the create_order validator would reject orders downstream.
        is_published: publishNow && !!digitalFile,
        store_ids: storeIds,
        stock_quantity: pricing.track_stock && pricing.stock_quantity !== ''
          ? Number(pricing.stock_quantity)
          : null,
        metadata,
        // Wave 1 (W1.S5/Phase 2.3) — additive cost composition.
        cost_source: costSource,
      };

      const createRes = await productsAPI.create(productPayload);
      const productId = createRes.data?.id;
      if (!productId) throw new Error('Product creation returned no id');

      if (imageFile) {
        // 2026-05-20 — Abortable upload + persistent retry toast.
        const fileToUpload = imageFile;
        try {
          await imageUpload.run((signal) =>
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

      // Upload the payload after the product exists. This fills in
      // metadata.download_filename / size / mime server-side.
      // 2026-05-20 — Abortable + still toggles is_published=false on
      // failure so the product can't leak without a file.
      if (digitalFile) {
        const fileToUpload = digitalFile;
        try {
          await digitalUpload.run((signal) =>
            productsAPI.uploadDigitalFile(productId, fileToUpload, { signal }),
          );
        } catch (err) {
          const detail = err?.response?.data?.detail || t('wizards.digital.validation.uploadFailed');
          toast.error(t('wizards.digital.validation.draftFallback', { detail }));
          if (publishNow) {
            try { await productsAPI.update(productId, { is_published: false }); }
            catch { /* ignore */ }
          }
        }
      }

      for (const ex of extras) {
        try {
          await productExtrasAPI.create(productId, {
            kind: ex.kind,
            group_key: ex.group_key || null,
            label: ex.label.trim(),
            description: ex.description?.trim() || null,
            price: ex.price === '' ? 0 : Number(ex.price),
            price_modifier_type: ex.price_modifier_type || 'flat',
            is_default: !!ex.is_default,
            sort_order: ex.sort_order ?? 0,
            is_active: ex.is_active !== false,
          });
        } catch (e) {
          toast.warning(t('wizards.common.extras.notCreated', { label: ex.label }));
        }
      }

      // 2026-05-20 — clear draft + suppress prompt on navigate.
      draft.discard();
      setSubmittedSuccessfully(true);
      toast.success(t('wizards.digital.createdToast'));
      navigate(`/digitals/${productId}`);
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
            <button onClick={() => navigate('/products?type=digital')} className="text-sm text-gray-600 hover:text-gray-900">
              {t('wizards.common.backToProducts')}
            </button>
            <h1 className="text-lg sm:text-xl font-bold text-gray-900 mt-0.5">{t('wizards.digital.title')}</h1>
          </div>
          <div className="hidden sm:flex items-center gap-1 text-xs text-gray-500">
            {t('wizards.common.stepCounter', { current: currentTabIdx + 1, total: TABS.length })}
          </div>
        </div>

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
                <span>{t(`wizards.digital.tabs.${tab.key}`)}</span>
                {err && <span aria-hidden>!</span>}
                {done && <span aria-hidden>✓</span>}
              </button>
            );
          })}
        </div>
      </div>

      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-6 space-y-5">

        {/* 2026-05-20 — Draft restore banner (24h TTL, per-user scoped). */}
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
            <div className="border-l-[3px] border-primary/60 pl-3">
              <h2 className="text-base font-semibold text-gray-900">{t('wizards.common.identityTitle')}</h2>
              <p className="text-xs text-gray-500 mt-0.5">{t('wizards.common.identitySubtitle')}</p>
            </div>

            <MultiLangSection fields={[
              { key: 'name', label: t('wizards.common.nameLabel'), it: identity.name,
                value: trName, onChange: setTrName, input: true, maxLength: 255 },
              { key: 'description', label: t('wizards.common.shortDescriptionLabel'), it: identity.description,
                value: trDescription, onChange: setTrDescription, rows: 2, maxLength: 2000 },
            ]}>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">{t('wizards.common.nameLabel')}</label>
              <input
                type="text" value={identity.name}
                onChange={e => setIdentity({ ...identity, name: e.target.value })}
                maxLength={255}
                placeholder={t('wizards.digital.identity.namePlaceholder')}
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
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none resize-none"
              />
            </div>
            </MultiLangSection>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">{t('wizards.common.skuLabel')}</label>
                {/* 2026-05-20 — SkuField: debounced live uniqueness check. */}
                <SkuField
                  value={identity.sku}
                  onChange={e => setIdentity({ ...identity, sku: e.target.value })}
                  maxLength={120}
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">{t('wizards.common.categoryLabel')}</label>
                {/* V4 — dropdown dalla tassonomia (mai testo libero) */}
                <select
                  value={identity.category || ''}
                  onChange={e => setIdentity({ ...identity, category: e.target.value })}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none bg-white"
                >
                  <option value="">{t('wizards.common.categoryNone', { defaultValue: 'Nessuna categoria' })}</option>
                  {Object.entries(taxonomies.digital || {}).map(([k, label]) => (
                    <option key={k} value={k}>{t(`taxonomy.${k}`, { defaultValue: label })}</option>
                  ))}
                </select>
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">{t('wizards.digital.identity.imageLabel')}</label>
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
            <div className="border-l-[3px] border-primary/60 pl-3">
              <h2 className="text-base font-semibold text-gray-900">{t('wizards.digital.pricing.title')}</h2>
              <p className="text-xs text-gray-500 mt-0.5">
                {t('wizards.digital.pricing.subtitle')}
              </p>
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">{t('wizards.digital.pricing.priceLabel')}</label>
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
                      stock_quantity: on ? (p.stock_quantity !== '' ? p.stock_quantity : '0') : '',
                    }));
                  }}
                  className="mt-0.5 rounded border-gray-300 text-gray-900 focus:ring-gray-900"
                />
                <span>
                  <span className="text-sm font-medium text-gray-900">{t('wizards.digital.pricing.trackStockTitle')}</span>
                  <p className="text-xs text-gray-500 mt-0.5">
                    {t('wizards.digital.pricing.trackStockDesc')}
                  </p>
                </span>
              </label>
              {pricing.track_stock && (
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">{t('wizards.digital.pricing.stockQuantityLabel')}</label>
                  {/* 2026-05-20 — Added max=1000000 to prevent silent overflow. */}
                  <input
                    type="number" min="0" step="1" max="1000000"
                    value={pricing.stock_quantity}
                    onChange={e => setPricing({ ...pricing, stock_quantity: e.target.value })}
                    className="w-full max-w-[180px] rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:border-gray-900 focus:outline-none"
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
              <StripeRequiredAlert whenTransactionMode={pricing.transaction_mode} />
            </div>

            {/* Sezione "Costo del prodotto" (COGS) rimossa dalla UI su
                richiesta founder 16/7/2026: agli operatori Aurya non
                serve la contabilita' margini. Lo stato costSource resta
                e viaggia nel salvataggio, cosi' i dati gia' configurati
                non vengono cancellati. */}
          </div>
        )}

        {/* ── TAB 3: File ─────────────────────────────────────────────── */}
        {activeTab === 'file' && (
          <div className="rounded-xl border border-gray-200 bg-white p-5 space-y-4">
            <div className="border-l-[3px] border-primary/60 pl-3">
              <h2 className="text-base font-semibold text-gray-900">{t('wizards.digital.file.title')}</h2>
              <p className="text-xs text-gray-500 mt-0.5">
                {t('wizards.digital.file.subtitle')}
              </p>
            </div>

            <label className="flex items-center gap-2 cursor-pointer rounded-md border border-dashed border-gray-300 px-3 py-4 text-sm text-gray-600 hover:border-gray-900">
              <span className="text-2xl">📁</span>
              <span className="flex-1">
                {digitalFile
                  ? <><strong>{digitalFile.name}</strong> · {formatBytes(digitalFile.size)}</>
                  : t('wizards.digital.file.placeholder')}
              </span>
              <input
                type="file" className="hidden"
                onChange={e => setDigitalFile(e.target.files?.[0] || null)}
              />
            </label>
            {digitalFile && (
              <button
                type="button"
                onClick={() => setDigitalFile(null)}
                className="text-xs text-red-600 hover:text-red-800"
              >
                {t('wizards.digital.file.removeButton')}
              </button>
            )}

            <div className="rounded-lg bg-blue-50 border border-blue-200 p-3 text-xs text-blue-900">
              {t('wizards.digital.file.privacyHint')}
            </div>
          </div>
        )}

        {/* ── TAB 4: Policy ───────────────────────────────────────────── */}
        {activeTab === 'policy' && (
          <div className="rounded-xl border border-gray-200 bg-white p-5 space-y-4">
            <div className="border-l-[3px] border-primary/60 pl-3">
              <h2 className="text-base font-semibold text-gray-900">{t('wizards.digital.policy.title')}</h2>
              <p className="text-xs text-gray-500 mt-0.5">
                {t('wizards.digital.policy.subtitle')}
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">{t('wizards.digital.policy.maxDownloadsLabel')}</label>
                <input
                  type="number" min="1" max="100" step="1"
                  value={policy.max_downloads}
                  onChange={e => setPolicy({ ...policy, max_downloads: e.target.value })}
                  placeholder={t('wizards.digital.policy.maxDownloadsPlaceholder')}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none"
                />
                {fieldError(errorsPolicy.max_downloads)}
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">{t('wizards.digital.policy.expiryLabel')}</label>
                <input
                  type="number" min="1" max="3650" step="1"
                  value={policy.access_expiry_days}
                  onChange={e => setPolicy({ ...policy, access_expiry_days: e.target.value })}
                  placeholder={t('wizards.digital.policy.expiryPlaceholder')}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none"
                />
                {fieldError(errorsPolicy.access_expiry_days)}
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">{t('wizards.digital.policy.longDescLabel')}</label>
              <MultiLangSection fields={[
                { key: 'long_description', label: null, it: policy.long_description,
                  value: trLong, onChange: setTrLong, rows: 5, maxLength: 5000 },
              ]}>
              <textarea
                value={policy.long_description}
                onChange={e => setPolicy({ ...policy, long_description: e.target.value })}
                rows={5} maxLength={5000}
                placeholder={t('wizards.digital.policy.longDescPlaceholder')}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none resize-none"
              />
              </MultiLangSection>
            </div>
          </div>
        )}

        {/* ── TAB 5: Extras ───────────────────────────────────────────── */}
        {activeTab === 'extras' && (
          <div className="rounded-xl border border-gray-200 bg-white p-5 space-y-4">
            <ProductExtrasEditor
              extras={extras}
              onChange={setExtras}
              productItemType="digital"
              title={t('wizards.digital.extras.title')}
            />
          </div>
        )}

        {/* ── TAB 6: Publish ──────────────────────────────────────────── */}
        {activeTab === 'publish' && (
          <div className="rounded-xl border border-gray-200 bg-white p-5 space-y-4">
            <div className="border-l-[3px] border-primary/60 pl-3">
              <h2 className="text-base font-semibold text-gray-900">{t('wizards.common.publishTitle')}</h2>
              <p className="text-xs text-gray-500 mt-0.5">{t('wizards.common.publishSubtitle')}</p>
            </div>

            {!fileValid && (
              <div className="rounded-lg bg-amber-50 border border-amber-200 p-3 text-xs text-amber-900">
                <Trans
                  i18nKey="wizards.digital.publish.fileMissingWarning"
                  ns="products"
                  components={{ strong: <strong /> }}
                />
              </div>
            )}

            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">{t('wizards.common.termsTitle')}</label>
              <textarea
                value={termsContent}
                onChange={e => setTermsContent(e.target.value)}
                rows={4} maxLength={5000}
                placeholder={t('wizards.digital.publish.termsPlaceholder')}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none resize-none"
              />
              <p className="text-[11px] text-gray-400 mt-1">{t('wizards.common.termsHint')}</p>
            </div>

            <div className="rounded-lg border border-gray-200 p-3 space-y-2">
              <h3 className="text-sm font-semibold text-gray-900">{t('wizards.common.distribution.title')}</h3>
              {availableStores.length <= 1 ? (
                <>
                  <p className="text-xs text-gray-500">{t('wizards.digital.publish.distributionDesc')}</p>
                  <div className="rounded-md bg-gray-50 border border-gray-200 px-3 py-2 text-sm text-gray-700 flex items-center gap-2">
                    <span aria-hidden>✓</span>
                    <span>{t('wizards.common.distribution.visibleAutoPrefix')} <strong>{availableStores[0]?.name || t('wizards.common.distribution.allStoresFallback')}</strong></span>
                  </div>
                </>
              ) : (
                <>
                  <p className="text-xs text-gray-500">{t('wizards.digital.publish.distributionMultiDesc')}</p>
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
                disabled={!fileValid}
                className="mt-0.5"
              />
              <div>
                <div className="text-sm font-medium text-gray-900">
                  {t('wizards.digital.publish.publishToggleTitle')} {!fileValid && <span className="text-xs text-gray-500">{t('wizards.digital.publish.publishToggleDisabledHint')}</span>}
                </div>
                <div className="text-xs text-gray-500 mt-0.5">
                  {t('wizards.digital.publish.publishToggleDesc')}
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
