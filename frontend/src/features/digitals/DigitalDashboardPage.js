/**
 * DigitalDashboardPage — admin control center for one digital product.
 *
 * Release 3 (Digital) B8. Mirrors PhysicalDashboardPage with the digital-
 * specific additions:
 *   - File digitale card (show current filename / size + replace uploader)
 *   - Policy card (max_downloads_per_delivery + access_expiry_days)
 *   - Consegne card (IssuedDownload list with status / count / resend)
 */

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import ProductSalesStats from '../products/components/ProductSalesStats';
import { toast } from 'sonner';
import { productsAPI } from '../../api';
import { storesAPI } from '../../api/stores';
import { productExtrasAPI } from '../../api/productExtras';
import { issuedDownloadsAPI } from '../../api/digitals';
import ProductExtrasEditor from '../reservations/components/ProductExtrasEditor';
import useLandingUrl from '../products/hooks/useLandingUrl';
// W1.S5/Phase 2.8 — additive cost composition editor for edits.
import CostSourceEditor from '../products/components/CostSourceEditor';
import { useCurrency } from '../../context/AuthContext';
import { formatAmount } from '../../utils/currency';
import MultiLangSection from '../../components/MultiLangSection';


function formatEuro(n, currency = 'EUR', locale = 'it-IT') {
  if (n == null || n === '') return '—';
  // CH compliance v1: route CHF through the shared Swiss-style formatter.
  if (String(currency || '').toUpperCase() === 'CHF') {
    return formatAmount(Number(n), 'CHF');
  }
  try {
    return new Intl.NumberFormat(locale, { style: 'currency', currency }).format(Number(n));
  } catch { return `${n} ${currency}`; }
}

function formatBytes(n) {
  if (!n || n <= 0) return '';
  const kb = n / 1024;
  if (kb < 1024) return `${kb.toFixed(0)} KB`;
  const mb = kb / 1024;
  if (mb < 1024) return `${mb.toFixed(1)} MB`;
  return `${(mb / 1024).toFixed(2)} GB`;
}

function formatDateTime(iso, locale = 'it-IT') {
  if (!iso) return '';
  try {
    const d = new Date(iso);
    return d.toLocaleString(locale, { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });
  } catch { return iso; }
}


function StatusPill({ isPublished }) {
  const { t } = useTranslation('products');
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${
      isPublished ? 'bg-green-100 text-green-900' : 'bg-gray-100 text-gray-700'
    }`}>
      {isPublished ? t('dashboards.common.statusOnline') : t('dashboards.common.statusOffline')}
    </span>
  );
}


function DownloadStatusBadge({ status }) {
  const { t } = useTranslation('products');
  const presets = {
    active:    { key: 'active',    cls: 'bg-green-100 text-green-900' },
    exhausted: { key: 'exhausted', cls: 'bg-amber-100 text-amber-900' },
    cancelled: { key: 'cancelled', cls: 'bg-gray-200 text-gray-700' },
  };
  const cfg = presets[status] || { key: null, cls: 'bg-gray-100 text-gray-700' };
  const label = cfg.key ? t(`dashboards.digital.downloadStatus.${cfg.key}`) : status;
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-semibold ${cfg.cls}`}>
      {label}
    </span>
  );
}


export default function DigitalDashboardPage() {
  const orgCurrency = useCurrency();
  const { product_id: productId } = useParams();
  const navigate = useNavigate();
  const { t, i18n } = useTranslation('products');

  const [product, setProduct] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);


  // Multilingua manuale — lingue offerte dall'operatore (per campo);
  // salvate sul prodotto via PATCH translations
  const [trName, setTrName] = useState({});
  const [trDescription, setTrDescription] = useState({});
  const [trLong, setTrLong] = useState({});
  const buildTranslationsPayload = () => {
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
  };
  const [productForm, setProductForm] = useState({
    name: '',
    description: '',
    image_url: '',
    cover_image_url: '',
    long_description: '',
    unit_price: '',
    sku: '',
    category: '',
    transaction_mode: 'direct',
    is_published: false,
    store_ids: [],
    terms_content: '',
    track_stock: false,
    stock_quantity: '',
    max_downloads: '',
    access_expiry_days: '',
  });
  const [savingProduct, setSavingProduct] = useState(false);
  const [duplicating, setDuplicating] = useState(false);
  // orgSlug no longer computed client-side — useLandingUrl resolves server-side.

  const [extras, setExtras] = useState([]);
  const [stores, setStores] = useState([]);
  const [downloads, setDownloads] = useState([]);
  const [downloadsLoading, setDownloadsLoading] = useState(false);
  const [resendingId, setResendingId] = useState(null);

  // Replace-file uploader — staged File until the merchant clicks "Sostituisci".
  const [replaceFile, setReplaceFile] = useState(null);
  const [uploadingFile, setUploadingFile] = useState(false);

  // Collapsible panels. File + Consegne are open by default since they are
  // the most frequently visited parts of a digital dashboard.
  const [fileOpen, setFileOpen] = useState(true);
  const [inventoryOpen, setInventoryOpen] = useState(false);
  const [identityOpen, setIdentityOpen] = useState(false);
  const [pricingOpen, setPricingOpen] = useState(false);
  const [policyOpen, setPolicyOpen] = useState(false);
  const [extrasOpen, setExtrasOpen] = useState(false);
  const [termsOpen, setTermsOpen] = useState(false);
  const [distributionOpen, setDistributionOpen] = useState(false);
  const [downloadsOpen, setDownloadsOpen] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [prodRes, storesRes] = await Promise.all([
        productsAPI.list(false),
        storesAPI.list().catch(() => ({ data: { stores: [] } })),
      ]);
      const prod = (prodRes.data || []).find(p => p.id === productId);
      if (!prod) { setError('not_found'); return; }
      if (prod.item_type !== 'digital') {
        setError('wrong_type');
        return;
      }
      setProduct(prod);
      setStores(storesRes.data?.stores || []);


      const meta = prod.metadata || {};
      const ptr = prod.translations || {};
      const trN = {}, trD = {}, trL = {};
      Object.entries(ptr).forEach(([l, f]) => {
        if (f?.name) trN[l] = f.name;
        if (f?.description) trD[l] = f.description;
        if (f?.long_description) trL[l] = f.long_description;
      });
      setTrName(trN);
      setTrDescription(trD);
      setTrLong(trL);
      setProductForm({
        name: prod.name || '',
        description: prod.description || '',
        image_url: prod.image_url || '',
        cover_image_url: meta.cover_image_url || '',
        long_description: meta.long_description || '',
        unit_price: prod.unit_price != null ? String(prod.unit_price) : '',
        sku: prod.sku || '',
        category: prod.category || '',
        transaction_mode: prod.transaction_mode || 'direct',
        is_published: !!prod.is_published,
        store_ids: prod.store_ids || [],
        terms_content: meta.terms_content || '',
        track_stock: prod.stock_quantity != null,
        stock_quantity: prod.stock_quantity != null ? String(prod.stock_quantity) : '',
        max_downloads: meta.max_downloads_per_delivery != null ? String(meta.max_downloads_per_delivery) : '',
        access_expiry_days: meta.access_expiry_days != null ? String(meta.access_expiry_days) : '',
        // W1.S5/Phase 2.8 — hydrate cost composition.
        cost_source: prod.cost_source || null,
      });

      const extrasRes = await productExtrasAPI.list(productId).catch(() => ({ data: { extras: [] } }));
      setExtras(extrasRes.data?.extras || extrasRes.data || []);
      setError(null);
    } catch (err) {
      setError(err?.response?.status === 404 ? 'not_found' : 'generic');
    } finally {
      setLoading(false);
    }
  }, [productId]);

  useEffect(() => { load(); }, [load]);

  const loadDownloads = useCallback(async () => {
    if (!productId) return;
    setDownloadsLoading(true);
    try {
      const res = await issuedDownloadsAPI.list({ product_id: productId, limit: 100 });
      setDownloads(res.data?.downloads || []);
    } catch {
      setDownloads([]);
    } finally {
      setDownloadsLoading(false);
    }
  }, [productId]);

  useEffect(() => { loadDownloads(); }, [loadDownloads]);

  const saveProduct = async () => {
    setSavingProduct(true);
    try {
      const _num = (v) => {
        const n = Number(v);
        return v === '' || v === null || Number.isNaN(n) || n <= 0 ? null : n;
      };
      const existingMeta = product?.metadata || {};
      const metaUpdate = {
        ...existingMeta,
        cover_image_url: productForm.cover_image_url?.trim() || null,
        long_description: productForm.long_description?.trim() || null,
        terms_content: productForm.terms_content?.trim() || null,
        max_downloads_per_delivery: _num(productForm.max_downloads),
        access_expiry_days: _num(productForm.access_expiry_days),
      };

      const upd = {
        name: productForm.name.trim(),
        description: productForm.description?.trim() || null,
        translations: buildTranslationsPayload(),
        image_url: productForm.image_url?.trim() || null,
        unit_price: productForm.unit_price !== '' ? Number(productForm.unit_price) : null,
        sku: productForm.sku?.trim() || null,
        category: productForm.category?.trim() || null,
        transaction_mode: productForm.transaction_mode,
        is_published: productForm.is_published,
        store_ids: productForm.store_ids || [],
        stock_quantity: productForm.track_stock && productForm.stock_quantity !== ''
          ? Number(productForm.stock_quantity)
          : null,
        metadata: metaUpdate,
        // W1.S5/Phase 2.8 — additive cost composition.
        cost_source: productForm.cost_source || null,
      };
      const res = await productsAPI.update(productId, upd);
      const updatedProd = res.data || upd;
      setProduct(prev => prev ? { ...prev, ...updatedProd } : prev);
      toast.success(t('dashboards.common.productUpdated'));
    } catch (err) {
      toast.error(err?.response?.data?.detail || t('dashboards.common.saveError'));
    } finally {
      setSavingProduct(false);
    }
  };

  const quickTogglePublish = async (next) => {
    // Refuse to publish when no file has been uploaded — mirrors the wizard
    // gate so the merchant can't accidentally publish a broken product.
    const meta = product?.metadata || {};
    if (next && !meta.download_filename) {
      toast.error(t('dashboards.digital.toasts.fileMissingPublish'));
      return;
    }
    setProductForm(f => ({ ...f, is_published: next }));
    try {
      await productsAPI.update(productId, { is_published: next });
      setProduct(prev => prev ? { ...prev, is_published: next } : prev);
      toast.success(next ? t('dashboards.digital.toasts.online') : t('dashboards.digital.toasts.offline'));
    } catch {
      setProductForm(f => ({ ...f, is_published: !next }));
      toast.error(t('dashboards.digital.toasts.statusError'));
    }
  };

  const handleReplaceFile = async () => {
    if (!replaceFile) return;
    setUploadingFile(true);
    try {
      const res = await productsAPI.uploadDigitalFile(productId, replaceFile);
      const snap = res.data || {};
      setProduct(prev => prev ? {
        ...prev,
        metadata: {
          ...(prev.metadata || {}),
          download_filename: snap.filename,
          download_size_bytes: snap.size_bytes,
          download_mime_type: snap.mime_type,
        },
      } : prev);
      setReplaceFile(null);
      toast.success(t('dashboards.digital.toasts.fileReplaced'));
    } catch (err) {
      toast.error(err?.response?.data?.detail || t('dashboards.digital.toasts.uploadFailed'));
    } finally {
      setUploadingFile(false);
    }
  };

  const handleResendDownload = async (downloadId) => {
    setResendingId(downloadId);
    try {
      await issuedDownloadsAPI.resend(downloadId);
      toast.success(t('dashboards.digital.toasts.emailResent'));
    } catch (err) {
      toast.error(err?.response?.data?.detail || t('dashboards.digital.toasts.resendError'));
    } finally {
      setResendingId(null);
    }
  };

  // Server-resolved landing URL — consistent across all dashboards.
  const {
    landingPath: landingUrl,
    landingUrl: landingUrlAbsolute,
    blockers: landingBlockers,
    refresh: refreshLandingInfo,
  } = useLandingUrl(productId);

  useEffect(() => { refreshLandingInfo(); }, [productForm.is_published, refreshLandingInfo]);

  const copyLandingUrl = async () => {
    if (!landingUrlAbsolute) return;
    try {
      await navigator.clipboard.writeText(landingUrlAbsolute);
      toast.success(t('dashboards.common.linkCopied'));
    } catch {
      toast.error(t('dashboards.digital.toasts.copyError'));
    }
  };

  const handleDuplicate = async () => {
    if (!product) return;
    setDuplicating(true);
    try {
      // Duplicate via backend: the endpoint does a deep copy but NOT the
      // digital payload — the admin uploads a new file for the copy.
      const res = await productsAPI.duplicate(productId);
      const newId = res.data?.id;
      if (newId) {
        toast.success(t('dashboards.digital.toasts.duplicated'));
        navigate(`/digitals/${newId}`);
      }
    } catch (err) {
      toast.error(err?.response?.data?.detail || t('dashboards.digital.toasts.duplicateError'));
    } finally {
      setDuplicating(false);
    }
  };

  const saveExtras = async (nextExtras) => {
    try {
      const existing = await productExtrasAPI.list(productId).then(r => r.data?.extras || r.data || []).catch(() => []);
      for (const ex of existing) {
        try { await productExtrasAPI.delete(productId, ex.id); } catch { /* ignore */ }
      }
      const updated = [];
      for (const ex of nextExtras) {
        if (!ex.label?.trim()) continue;
        try {
          const res = await productExtrasAPI.create(productId, {
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
          updated.push(res.data);
        } catch { /* ignore */ }
      }
      setExtras(updated);
      toast.success(t('dashboards.digital.toasts.extrasUpdated'));
    } catch {
      toast.error(t('dashboards.digital.toasts.extrasError'));
    }
  };

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center text-sm text-gray-500">{t('dashboards.common.loading')}</div>;
  }
  if (error === 'not_found') {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-6">
        <div className="max-w-md text-center bg-white rounded-xl border p-8">
          <h1 className="text-2xl font-bold mb-2">{t('dashboards.digital.notFound')}</h1>
          <button onClick={() => navigate('/products?type=digital')} className="rounded-md bg-gray-900 text-white px-4 py-2 text-sm">
            {t('dashboards.common.backToProducts')}
          </button>
        </div>
      </div>
    );
  }
  if (error === 'wrong_type') {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-6">
        <div className="max-w-md text-center bg-white rounded-xl border p-8">
          <h1 className="text-2xl font-bold mb-2">{t('dashboards.digital.invalidType')}</h1>
          <p className="text-gray-600 mb-4">{t('dashboards.digital.invalidTypeDesc')}</p>
          <button onClick={() => navigate('/products')} className="rounded-md bg-gray-900 text-white px-4 py-2 text-sm">{t('dashboards.common.backToProducts')}</button>
        </div>
      </div>
    );
  }

  const meta = product?.metadata || {};
  const hero = productForm.cover_image_url || productForm.image_url;
  const hasFile = !!meta.download_filename;

  return (
    <div className="min-h-screen bg-gray-50 pb-20">
      {/* Hero */}
      <div className="relative bg-gray-900 text-white overflow-hidden">
        {hero && (
          <img src={hero} alt="" className="absolute inset-0 w-full h-full object-cover opacity-50" />
        )}
        <div className="relative max-w-4xl mx-auto px-4 sm:px-6 py-6 sm:py-10">
          <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
            <div className="min-w-0">
              <Link to="/products?type=digital" className="inline-flex items-center gap-1 text-sm font-medium text-white/70 hover:text-white transition-colors">{t('dashboards.digital.back')}</Link>
              <p className="text-[10px] uppercase tracking-widest opacity-70 mt-2">{t('dashboards.digital.typeLabel')}</p>
              <h1 className="text-2xl sm:text-3xl font-bold mt-1">{productForm.name || t('dashboards.digital.fallbackName')}</h1>
              {productForm.unit_price !== '' && (
                <div className="mt-2 text-sm sm:text-base opacity-90">{formatEuro(productForm.unit_price, productForm.currency || orgCurrency, i18n.language)}</div>
              )}
            </div>
            <div className="shrink-0 flex flex-col sm:items-end gap-2">
              <StatusPill isPublished={productForm.is_published} />
              {!hasFile && (
                <span className="inline-flex items-center rounded-full bg-amber-100 text-amber-900 px-2.5 py-0.5 text-xs font-semibold">
                  {t('dashboards.digital.fileMissingBadge')}
                </span>
              )}
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-4 sm:px-6 py-5 sm:py-8 space-y-5">
        {/* CG3 — i numeri del digitale (ricavo, consegne) */}
        <ProductSalesStats productId={productId} productName={productForm.name} />

        {/* Stato */}
        <div className="rounded-xl border border-gray-200 bg-white px-5 py-4">
          <div className="flex items-center justify-between gap-3">
            <div className="min-w-0">
              <h2 className="text-sm font-semibold text-gray-900">{t('dashboards.digital.statusTitle')}</h2>
              <p className="text-xs text-gray-500 mt-0.5">
                {productForm.is_published
                  ? t('dashboards.digital.statusOnlineDesc')
                  : hasFile
                    ? t('dashboards.digital.statusOfflineDesc')
                    : t('dashboards.digital.statusFileMissingDesc')}
              </p>
            </div>
            <div className="relative inline-flex shrink-0">
              <select
                value={productForm.is_published ? 'published' : 'draft'}
                onChange={(e) => quickTogglePublish(e.target.value === 'published')}
                disabled={!hasFile && !productForm.is_published}
                className={`rounded-full pl-4 pr-8 py-1.5 text-sm font-semibold border-0 cursor-pointer appearance-none focus:outline-none focus:ring-2 focus:ring-gray-900/10 ${
                  productForm.is_published ? 'bg-green-100 text-green-900' : 'bg-gray-100 text-gray-700'
                } disabled:opacity-50 disabled:cursor-not-allowed`}
              >
                <option value="draft">{t('dashboards.common.statusOffline')}</option>
                <option value="published">{t('dashboards.common.statusOnline')}</option>
              </select>
              <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-[10px] opacity-60">▾</span>
            </div>
          </div>
        </div>

        {/* Action bar */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
          {landingUrl ? (
            <a
              href={landingUrl}
              target="_blank" rel="noopener noreferrer"
              className="rounded-xl border border-gray-300 bg-white px-4 py-3 text-sm font-semibold text-gray-900 hover:border-gray-900 text-center"
            >{t('dashboards.digital.landingPreview')}</a>
          ) : (
            <div
              className="rounded-xl border border-dashed border-gray-300 bg-gray-50 px-4 py-3 text-sm text-gray-500 text-center"
              title={landingBlockers.length ? landingBlockers.join('\n') : undefined}
            >
              {t('dashboards.digital.landingUnavailable')}
              {landingBlockers.length > 0 && (
                <p className="text-[11px] mt-0.5 text-gray-400">{landingBlockers[0]}</p>
              )}
            </div>
          )}
          <button
            type="button" onClick={copyLandingUrl}
            disabled={!landingUrl}
            title={!landingUrl && landingBlockers.length ? landingBlockers.join('\n') : undefined}
            className="rounded-xl border border-gray-300 bg-white px-4 py-3 text-sm font-semibold text-gray-900 hover:border-gray-900 disabled:opacity-50"
          >{t('dashboards.digital.landingCopy')}</button>
          <button
            type="button"
            onClick={handleDuplicate}
            disabled={duplicating}
            className="rounded-xl border border-gray-300 bg-white px-4 py-3 text-sm font-semibold text-gray-900 hover:border-gray-900 disabled:opacity-50"
          >{duplicating ? t('dashboards.digital.duplicateLoading') : t('dashboards.digital.duplicateBtn')}</button>
        </div>

        {/* File digitale */}
        <div className="rounded-xl border border-gray-200 bg-white overflow-hidden">
          <button
            type="button"
            onClick={() => setFileOpen(v => !v)}
            className="w-full flex items-center justify-between px-5 py-3 text-left hover:bg-gray-50"
          >
            <span className="text-sm font-semibold text-gray-900">{t('dashboards.digital.file.title')}</span>
            <span className="text-gray-400 text-xs">{fileOpen ? '▲' : '▼'}</span>
          </button>
          {fileOpen && (
            <div className="border-t border-gray-100 px-5 py-4 space-y-3">
              {hasFile ? (
                <div className="rounded-lg bg-green-50 border border-green-200 p-3 text-sm text-green-900">
                  ✅ <strong>{meta.download_filename}</strong> · {formatBytes(meta.download_size_bytes)}
                  {meta.download_mime_type && <span className="text-xs text-green-700"> · {meta.download_mime_type}</span>}
                </div>
              ) : (
                <div className="rounded-lg bg-amber-50 border border-amber-200 p-3 text-sm text-amber-900">
                  {t('dashboards.digital.file.missingWarning')}
                </div>
              )}

              <label className="flex items-center gap-2 cursor-pointer rounded-md border border-dashed border-gray-300 px-3 py-3 text-sm text-gray-600 hover:border-gray-900">
                <span className="text-xl">⬆️</span>
                <span className="flex-1">
                  {replaceFile
                    ? <><strong>{replaceFile.name}</strong> · {formatBytes(replaceFile.size)}</>
                    : (hasFile ? t('dashboards.digital.file.replaceLabel') : t('dashboards.digital.file.uploadLabel'))}
                </span>
                <input
                  type="file" className="hidden"
                  onChange={e => setReplaceFile(e.target.files?.[0] || null)}
                />
              </label>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={handleReplaceFile}
                  disabled={!replaceFile || uploadingFile}
                  className="rounded-md bg-gray-900 text-white px-4 py-2 text-sm font-semibold hover:bg-gray-800 disabled:opacity-50"
                >{uploadingFile ? t('dashboards.digital.file.uploadingBtn') : (hasFile ? t('dashboards.digital.file.replaceBtn') : t('dashboards.digital.file.uploadBtn'))}</button>
                {replaceFile && !uploadingFile && (
                  <button
                    type="button"
                    onClick={() => setReplaceFile(null)}
                    className="text-xs text-gray-500 hover:text-gray-900"
                  >{t('dashboards.digital.file.cancelBtn')}</button>
                )}
              </div>

              <p className="text-[11px] text-gray-400">
                {t('dashboards.digital.file.privacyHint')}
              </p>
            </div>
          )}
        </div>

        {/* Consegne (IssuedDownload) */}
        <div className="rounded-xl border border-gray-200 bg-white overflow-hidden">
          <button
            type="button"
            onClick={() => setDownloadsOpen(v => !v)}
            className="w-full flex items-center justify-between px-5 py-3 text-left hover:bg-gray-50"
          >
            <span className="text-sm font-semibold text-gray-900">{t('dashboards.digital.downloads.title')}</span>
            <span className="text-gray-400 text-xs">
              {downloadsLoading ? '…' : `${downloads.length}`} {downloadsOpen ? '▲' : '▼'}
            </span>
          </button>
          {downloadsOpen && (
            <div className="border-t border-gray-100 px-5 py-4">
              {downloadsLoading ? (
                <p className="text-sm text-gray-500">{t('dashboards.common.loading')}</p>
              ) : downloads.length === 0 ? (
                <p className="text-sm text-gray-500">{t('dashboards.digital.downloads.empty')}</p>
              ) : (
                <ul className="divide-y divide-gray-100">
                  {downloads.map(d => {
                    const used = d.download_count || 0;
                    const cap = d.max_downloads;
                    const remaining = cap != null ? Math.max(0, cap - used) : null;
                    return (
                      <li key={d.id} className="py-2 flex items-center gap-3 text-sm flex-wrap">
                        <span className="font-mono text-xs text-gray-700 tabular-nums">{d.code}</span>
                        <DownloadStatusBadge status={d.status} />
                        <span className="text-gray-600 min-w-0 flex-1 truncate">
                          {d.holder_name || d.holder_email || '—'}
                        </span>
                        <span className="text-xs text-gray-500 tabular-nums">
                          {used}{cap != null ? `/${cap}` : ''} {t('dashboards.digital.downloads.downloadCount')}
                          {remaining != null && remaining === 0 && ` · ${t('dashboards.digital.downloads.exhaustedCount')}`}
                        </span>
                        {d.last_downloaded_at && (
                          <span className="text-[11px] text-gray-400 whitespace-nowrap">
                            {formatDateTime(d.last_downloaded_at, i18n.language)}
                          </span>
                        )}
                        <button
                          type="button"
                          disabled={d.status === 'cancelled' || resendingId === d.id}
                          onClick={() => handleResendDownload(d.id)}
                          className="text-xs text-primary hover:underline disabled:opacity-40"
                        >
                          {resendingId === d.id ? t('dashboards.digital.downloads.resending') : t('dashboards.digital.downloads.resendBtn')}
                        </button>
                      </li>
                    );
                  })}
                </ul>
              )}
            </div>
          )}
        </div>

        {/* Inventario */}
        <div className="rounded-xl border border-gray-200 bg-white overflow-hidden">
          <button
            type="button"
            onClick={() => setInventoryOpen(v => !v)}
            className="w-full flex items-center justify-between px-5 py-3 text-left hover:bg-gray-50"
          >
            <span className="text-sm font-semibold text-gray-900">{t('dashboards.digital.inventory.title')}</span>
            <span className="text-gray-400 text-xs">{inventoryOpen ? '▲' : '▼'}</span>
          </button>
          {inventoryOpen && (
            <div className="border-t border-gray-100 px-5 py-4 space-y-3">
              <label className="flex items-start gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={productForm.track_stock}
                  onChange={e => {
                    const on = e.target.checked;
                    setProductForm(p => ({
                      ...p,
                      track_stock: on,
                      stock_quantity: on ? (p.stock_quantity !== '' ? p.stock_quantity : '0') : '',
                    }));
                  }}
                  className="mt-0.5 rounded border-gray-300"
                />
                <span>
                  <span className="text-sm font-medium text-gray-900">{t('dashboards.digital.inventory.trackStockTitle')}</span>
                  <p className="text-xs text-gray-500 mt-0.5">
                    {t('dashboards.digital.inventory.trackStockDesc')}
                  </p>
                </span>
              </label>
              {productForm.track_stock && (
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">{t('dashboards.digital.inventory.stockLabel')}</label>
                  <input
                    type="number" min="0" step="1"
                    value={productForm.stock_quantity}
                    onChange={e => setProductForm({ ...productForm, stock_quantity: e.target.value })}
                    className="w-full max-w-[180px] rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none"
                  />
                </div>
              )}
              <div className="pt-1">
                <button
                  type="button"
                  onClick={saveProduct}
                  disabled={savingProduct}
                  className="rounded-md bg-gray-900 text-white px-4 py-2 text-sm font-semibold hover:bg-gray-800 disabled:opacity-50"
                >{savingProduct ? t('dashboards.common.saving') : t('dashboards.digital.inventory.saveBtn')}</button>
              </div>
            </div>
          )}
        </div>

        {/* Identità */}
        <div className="rounded-xl border border-gray-200 bg-white overflow-hidden">
          <button
            type="button"
            onClick={() => setIdentityOpen(v => !v)}
            className="w-full flex items-center justify-between px-5 py-3 text-left hover:bg-gray-50"
          >
            <span className="text-sm font-semibold text-gray-900">{t('dashboards.digital.identity.title')}</span>
            <span className="text-gray-400 text-xs">{identityOpen ? '▲' : '▼'}</span>
          </button>
          {identityOpen && (
            <div className="border-t border-gray-100 px-5 py-4 space-y-3">
              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">{t('dashboards.digital.identity.nameLabel')}</label>
                <input
                  type="text" value={productForm.name}
                  onChange={e => setProductForm({ ...productForm, name: e.target.value })}
                  maxLength={255}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm bg-white"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">{t('dashboards.digital.identity.shortDescLabel')}</label>
                <textarea
                  rows={2} maxLength={2000}
                  value={productForm.description}
                  onChange={e => setProductForm({ ...productForm, description: e.target.value })}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm bg-white resize-none"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">{t('dashboards.digital.identity.longDescLabel')}</label>
                <textarea
                  rows={5} maxLength={5000}
                  value={productForm.long_description}
                  onChange={e => setProductForm({ ...productForm, long_description: e.target.value })}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm bg-white resize-none"
                />
              </div>
              <MultiLangSection fields={[
                { key: 'name', label: t('dashboards.digital.identity.nameLabel', { defaultValue: 'Nome' }), it: productForm.name,
                  value: trName, onChange: setTrName, input: true, maxLength: 255 },
                { key: 'description', label: t('dashboards.digital.identity.shortDescLabel'), it: productForm.description,
                  value: trDescription, onChange: setTrDescription, rows: 2, maxLength: 2000 },
                { key: 'long_description', label: t('dashboards.digital.identity.longDescLabel'), it: productForm.long_description,
                  value: trLong, onChange: setTrLong, rows: 4, maxLength: 5000 },
              ]}>{null}</MultiLangSection>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-gray-700 mb-1">{t('dashboards.digital.identity.skuLabel')}</label>
                  <input
                    type="text" value={productForm.sku}
                    onChange={e => setProductForm({ ...productForm, sku: e.target.value })}
                    maxLength={120}
                    className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm bg-white"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-gray-700 mb-1">{t('dashboards.digital.identity.categoryLabel')}</label>
                  <input
                    type="text" value={productForm.category}
                    onChange={e => setProductForm({ ...productForm, category: e.target.value })}
                    maxLength={120}
                    className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm bg-white"
                  />
                </div>
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">{t('dashboards.digital.identity.imageLabel')}</label>
                <input
                  type="url" value={productForm.image_url}
                  onChange={e => setProductForm({ ...productForm, image_url: e.target.value })}
                  maxLength={500}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm bg-white"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">{t('dashboards.digital.identity.coverLabel')}</label>
                <input
                  type="url" value={productForm.cover_image_url}
                  onChange={e => setProductForm({ ...productForm, cover_image_url: e.target.value })}
                  maxLength={500}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm bg-white"
                />
              </div>
              <div className="pt-1">
                <button
                  type="button"
                  onClick={saveProduct}
                  disabled={savingProduct}
                  className="rounded-md bg-gray-900 text-white px-4 py-2 text-sm font-semibold hover:bg-gray-800 disabled:opacity-50"
                >{savingProduct ? t('dashboards.common.saving') : t('dashboards.digital.identity.saveBtn')}</button>
              </div>
            </div>
          )}
        </div>

        {/* Prezzo */}
        <div className="rounded-xl border border-gray-200 bg-white overflow-hidden">
          <button
            type="button"
            onClick={() => setPricingOpen(v => !v)}
            className="w-full flex items-center justify-between px-5 py-3 text-left hover:bg-gray-50"
          >
            <span className="text-sm font-semibold text-gray-900">{t('dashboards.digital.pricing.title')}</span>
            <span className="text-gray-400 text-xs">{pricingOpen ? '▲' : '▼'}</span>
          </button>
          {pricingOpen && (
            <div className="border-t border-gray-100 px-5 py-4 space-y-3">
              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">{t('dashboards.digital.pricing.priceLabel')}</label>
                <input
                  type="number" step="0.01" min="0"
                  value={productForm.unit_price}
                  onChange={e => setProductForm({ ...productForm, unit_price: e.target.value })}
                  className="w-full max-w-[180px] rounded-md border border-gray-300 px-3 py-2 text-sm bg-white"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">{t('dashboards.digital.pricing.modeLabel')}</label>
                <select
                  value={productForm.transaction_mode}
                  onChange={e => setProductForm({ ...productForm, transaction_mode: e.target.value })}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm bg-white"
                >
                  <option value="direct">{t('dashboards.digital.pricing.modeDirect')}</option>
                  <option value="approval">{t('dashboards.digital.pricing.modeApproval')}</option>
                  <option value="request">{t('dashboards.digital.pricing.modeRequest')}</option>
                </select>
              </div>

              {/* W1.S5/Phase 2.8 — Cost composition (edit). */}
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
                  value={productForm.cost_source}
                  onChange={(next) => setProductForm({ ...productForm, cost_source: next })}
                />
              </div>

              <div className="pt-1">
                <button
                  type="button"
                  onClick={saveProduct}
                  disabled={savingProduct}
                  className="rounded-md bg-gray-900 text-white px-4 py-2 text-sm font-semibold hover:bg-gray-800 disabled:opacity-50"
                >{savingProduct ? t('dashboards.common.saving') : t('dashboards.digital.pricing.saveBtn')}</button>
              </div>
            </div>
          )}
        </div>

        {/* Policy */}
        <div className="rounded-xl border border-gray-200 bg-white overflow-hidden">
          <button
            type="button"
            onClick={() => setPolicyOpen(v => !v)}
            className="w-full flex items-center justify-between px-5 py-3 text-left hover:bg-gray-50"
          >
            <span className="text-sm font-semibold text-gray-900">{t('dashboards.digital.policy.title')}</span>
            <span className="text-gray-400 text-xs">{policyOpen ? '▲' : '▼'}</span>
          </button>
          {policyOpen && (
            <div className="border-t border-gray-100 px-5 py-4 space-y-3">
              <p className="text-xs text-gray-500">
                {t('dashboards.digital.policy.hint')}
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-gray-700 mb-1">{t('dashboards.digital.policy.maxDownloadsLabel')}</label>
                  <input
                    type="number" min="1" max="100" step="1"
                    value={productForm.max_downloads}
                    onChange={e => setProductForm({ ...productForm, max_downloads: e.target.value })}
                    placeholder={t('dashboards.digital.policy.maxDownloadsPlaceholder')}
                    className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm bg-white"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-gray-700 mb-1">{t('dashboards.digital.policy.expiryLabel')}</label>
                  <input
                    type="number" min="1" max="3650" step="1"
                    value={productForm.access_expiry_days}
                    onChange={e => setProductForm({ ...productForm, access_expiry_days: e.target.value })}
                    placeholder={t('dashboards.digital.policy.expiryPlaceholder')}
                    className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm bg-white"
                  />
                </div>
              </div>
              <div className="pt-1">
                <button
                  type="button"
                  onClick={saveProduct}
                  disabled={savingProduct}
                  className="rounded-md bg-gray-900 text-white px-4 py-2 text-sm font-semibold hover:bg-gray-800 disabled:opacity-50"
                >{savingProduct ? t('dashboards.common.saving') : t('dashboards.digital.policy.saveBtn')}</button>
              </div>
            </div>
          )}
        </div>

        {/* Extras */}
        <div className="rounded-xl border border-gray-200 bg-white overflow-hidden">
          <button
            type="button"
            onClick={() => setExtrasOpen(v => !v)}
            className="w-full flex items-center justify-between px-5 py-3 text-left hover:bg-gray-50"
          >
            <span className="text-sm font-semibold text-gray-900">{t('dashboards.digital.extras.title')}</span>
            <span className="text-gray-400 text-xs">{extrasOpen ? '▲' : '▼'}</span>
          </button>
          {extrasOpen && (
            <div className="border-t border-gray-100 px-5 py-4">
              <ProductExtrasEditor
                extras={extras}
                onChange={saveExtras}
                productItemType="digital"
                title=""
              />
            </div>
          )}
        </div>

        {/* Termini */}
        <div className="rounded-xl border border-gray-200 bg-white overflow-hidden">
          <button
            type="button"
            onClick={() => setTermsOpen(v => !v)}
            className="w-full flex items-center justify-between px-5 py-3 text-left hover:bg-gray-50"
          >
            <span className="text-sm font-semibold text-gray-900">{t('dashboards.digital.terms.title')}</span>
            <span className="text-gray-400 text-xs">{termsOpen ? '▲' : '▼'}</span>
          </button>
          {termsOpen && (
            <div className="border-t border-gray-100 px-5 py-4 space-y-3">
              <textarea
                rows={5} maxLength={5000}
                value={productForm.terms_content}
                onChange={e => setProductForm({ ...productForm, terms_content: e.target.value })}
                placeholder={t('dashboards.digital.terms.placeholder')}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm bg-white resize-none"
              />
              <div className="pt-1">
                <button
                  type="button"
                  onClick={saveProduct}
                  disabled={savingProduct}
                  className="rounded-md bg-gray-900 text-white px-4 py-2 text-sm font-semibold hover:bg-gray-800 disabled:opacity-50"
                >{savingProduct ? t('dashboards.common.saving') : t('dashboards.common.saveTerms')}</button>
              </div>
            </div>
          )}
        </div>

        {/* Distribuzione */}
        <div className="rounded-xl border border-gray-200 bg-white overflow-hidden">
          <button
            type="button"
            onClick={() => setDistributionOpen(v => !v)}
            className="w-full flex items-center justify-between px-5 py-3 text-left hover:bg-gray-50"
          >
            <span className="text-sm font-semibold text-gray-900">{t('dashboards.common.distributionTitle')}</span>
            <span className="text-gray-400 text-xs">{distributionOpen ? '▲' : '▼'}</span>
          </button>
          {distributionOpen && (
            <div className="border-t border-gray-100 px-5 py-4 space-y-2">
              {stores.length <= 1 ? (
                <div className="rounded-md bg-gray-50 border border-gray-200 px-3 py-2 text-sm text-gray-700">
                  {t('dashboards.digital.distribution.visibleIn')} <strong>{stores[0]?.name || t('dashboards.common.distributionAllStoresFallback')}</strong>
                </div>
              ) : (
                <>
                  <label className="flex items-center gap-2 text-sm cursor-pointer">
                    <input
                      type="checkbox"
                      checked={!productForm.store_ids?.length}
                      onChange={() => setProductForm(f => ({ ...f, store_ids: [] }))}
                      className="rounded border-gray-300"
                    />
                    <span className={!productForm.store_ids?.length ? 'font-medium' : 'text-gray-500'}>
                      {t('dashboards.common.distributionAllStoresLabel')}
                    </span>
                  </label>
                  {stores.map(s => {
                    const isSpecific = (productForm.store_ids || []).length > 0;
                    const checked = isSpecific && (productForm.store_ids || []).includes(s.id);
                    return (
                      <label key={s.id} className="flex items-center gap-2 text-sm cursor-pointer">
                        <input
                          type="checkbox"
                          checked={checked}
                          onChange={() => {
                            const cur = productForm.store_ids || [];
                            const next = cur.includes(s.id)
                              ? cur.filter(id => id !== s.id)
                              : [...cur, s.id];
                            setProductForm(f => ({ ...f, store_ids: next }));
                          }}
                          className="rounded border-gray-300"
                        />
                        <span>{s.name}</span>
                      </label>
                    );
                  })}
                </>
              )}
              <div className="pt-1">
                <button
                  type="button"
                  onClick={saveProduct}
                  disabled={savingProduct}
                  className="rounded-md bg-gray-900 text-white px-4 py-2 text-sm font-semibold hover:bg-gray-800 disabled:opacity-50"
                >{savingProduct ? t('dashboards.common.saving') : t('dashboards.common.saveDistribution')}</button>
              </div>
            </div>
          )}
        </div>

      </div>
    </div>
  );
}
