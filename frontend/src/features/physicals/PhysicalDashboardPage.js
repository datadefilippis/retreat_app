/**
 * PhysicalDashboardPage — admin control center for one physical product.
 *
 * Release 2 (Physical pattern parity, A3). Mirrors ReservationDashboardPage /
 * ServiceDashboardPage / EventDashboardPage so the whole catalog follows one
 * consistent admin pattern.
 *
 * Route: /physicals/:product_id (authenticated)
 *
 * Sections:
 *   - Hero: cover + name + stock badge + status pill
 *   - Status card (publish toggle)
 *   - Action bar: landing preview · copy link · duplicate
 *   - Collapsible panels:
 *       1. Inventario (stock quantity + tracking toggle)
 *       2. Identità (name, description, image, cover, long_description, sku, category)
 *       3. Prezzo (unit_price, transaction_mode)
 *       4. Fulfillment (notes + store modes preview)
 *       5. Extras (shared ProductExtrasEditor)
 *       6. Termini (terms override)
 *       7. Distribuzione (store assignment)
 *   - Ordini recenti con questo prodotto
 */

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import ProductSalesStats from '../products/components/ProductSalesStats';
import { toast } from 'sonner';
import { productsAPI, ordersAPI } from '../../api';
import { storesAPI } from '../../api/stores';
import { productExtrasAPI } from '../../api/productExtras';
import ProductExtrasEditor from '../reservations/components/ProductExtrasEditor';
import useLandingUrl from '../products/hooks/useLandingUrl';
// W1.S5/Phase 2.5 — additive cost composition editor for edits.
import { useCurrency } from '../../context/AuthContext';
import { formatAmount } from '../../utils/currency';
import MultiLangSection from '../../components/MultiLangSection';


function formatEuro(n, currency = 'EUR', locale = 'it-IT') {
  if (n == null || n === '') return '—';
  if (String(currency || '').toUpperCase() === 'CHF') {
    return formatAmount(Number(n), 'CHF');
  }
  try {
    return new Intl.NumberFormat(locale, { style: 'currency', currency }).format(Number(n));
  } catch {
    return `${n} ${currency}`;
  }
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


function StockBadge({ stockQuantity }) {
  const { t } = useTranslation('products');
  // null = not tracked → neutral gray
  if (stockQuantity == null) {
    return (
      <span className="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold bg-gray-100 text-gray-700">
        {t('dashboards.physical.stockBadge.notTracked')}
      </span>
    );
  }
  const n = Number(stockQuantity);
  if (n <= 0) {
    return (
      <span className="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold bg-red-100 text-red-900">
        {t('dashboards.physical.stockBadge.depleted')}
      </span>
    );
  }
  if (n <= 5) {
    return (
      <span className="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold bg-amber-100 text-amber-900">
        {t('dashboards.physical.stockBadge.lastN', { count: n })}
      </span>
    );
  }
  return (
    <span className="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold bg-green-100 text-green-900">
      {t('dashboards.physical.stockBadge.inStock', { count: n })}
    </span>
  );
}


export default function PhysicalDashboardPage() {
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
    fulfillment_notes: '',
    // Stock is modelled as a nullable integer. `track_stock` is a UI-level
    // toggle that collapses to `stock_quantity = null` when off.
    track_stock: false,
    stock_quantity: '',
    // W1.S5/Phase 2.5 — cost composition. Hydrated from product.cost_source
    // on load; null until the merchant configures the first component.
    cost_source: null,
  });
  const [savingProduct, setSavingProduct] = useState(false);
  const [duplicating, setDuplicating] = useState(false);
  // orgSlug no longer computed client-side — useLandingUrl resolves server-side.

  const [extras, setExtras] = useState([]);
  const [stores, setStores] = useState([]);
  const [recentOrders, setRecentOrders] = useState([]);
  const [recentOrdersLoading, setRecentOrdersLoading] = useState(false);

  // Collapsible panel state. Inventory + identity are open by default —
  // that's what a merchant lands here to check most often.
  const [inventoryOpen, setInventoryOpen] = useState(true);
  const [identityOpen, setIdentityOpen] = useState(true);
  const [pricingOpen, setPricingOpen] = useState(false);
  const [fulfillmentOpen, setFulfillmentOpen] = useState(false);
  const [extrasOpen, setExtrasOpen] = useState(false);
  const [termsOpen, setTermsOpen] = useState(false);
  const [distributionOpen, setDistributionOpen] = useState(false);
  const [recentOrdersOpen, setRecentOrdersOpen] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [prodRes, storesRes] = await Promise.all([
        productsAPI.list(false),
        storesAPI.list().catch(() => ({ data: { stores: [] } })),
      ]);
      const prod = (prodRes.data || []).find(p => p.id === productId);
      if (!prod) { setError('not_found'); return; }
      if (prod.item_type !== 'physical') {
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
        fulfillment_notes: meta.fulfillment_notes || '',
        track_stock: prod.stock_quantity != null,
        stock_quantity: prod.stock_quantity != null ? String(prod.stock_quantity) : '',
        // W1.S5/Phase 2.5 — hydrate cost composition from server
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

  // Recent orders containing this product. Client-side filter on the
  // confirmed+completed subset — physical products rarely have hundreds of
  // rows per month so this is fine for MVP.
  const loadRecentOrders = useCallback(async () => {
    if (!productId) return;
    setRecentOrdersLoading(true);
    try {
      const res = await ordersAPI.list(null, 200);
      const rows = (res.data?.orders || res.data || [])
        .filter(o => (o.items || []).some(it => it.product_id === productId))
        .slice(0, 20);
      setRecentOrders(rows);
    } catch {
      setRecentOrders([]);
    } finally {
      setRecentOrdersLoading(false);
    }
  }, [productId]);

  useEffect(() => { loadRecentOrders(); }, [loadRecentOrders]);

  const saveProduct = async () => {
    setSavingProduct(true);
    try {
      const existingMeta = product?.metadata || {};
      const metaUpdate = {
        ...existingMeta,
        cover_image_url: productForm.cover_image_url?.trim() || null,
        long_description: productForm.long_description?.trim() || null,
        terms_content: productForm.terms_content?.trim() || null,
        fulfillment_notes: productForm.fulfillment_notes?.trim() || null,
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
        // Null when tracking is off; integer ≥ 0 when on.
        stock_quantity: productForm.track_stock && productForm.stock_quantity !== ''
          ? Number(productForm.stock_quantity)
          : null,
        metadata: metaUpdate,
        // W1.S5/Phase 2.5 — additive cost composition.
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
    setProductForm(f => ({ ...f, is_published: next }));
    try {
      await productsAPI.update(productId, { is_published: next });
      setProduct(prev => prev ? { ...prev, is_published: next } : prev);
      toast.success(next ? t('dashboards.physical.toasts.online') : t('dashboards.physical.toasts.offline'));
    } catch {
      // Revert the optimistic toggle on failure.
      setProductForm(f => ({ ...f, is_published: !next }));
      toast.error(t('dashboards.physical.toasts.statusError'));
    }
  };

  // Server-resolved landing URL — matches what the public route accepts.
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
      toast.error(t('dashboards.physical.toasts.copyError'));
    }
  };

  const handleDuplicate = async () => {
    if (!product) return;
    setDuplicating(true);
    try {
      const payload = {
        name: `${product.name} (copia)`,
        description: product.description,
        image_url: product.image_url,
        unit_price: product.unit_price,
        sku: null,  // SKU is likely unique; let the merchant reset it
        category: product.category,
        item_type: 'physical',
        price_mode: product.price_mode || 'fixed',
        transaction_mode: product.transaction_mode || 'direct',
        is_published: false,
        store_ids: product.store_ids || [],
        stock_quantity: product.stock_quantity,
        metadata: product.metadata || {},
      };
      const res = await productsAPI.create(payload);
      const newId = res.data?.id;
      if (newId) {
        toast.success(t('dashboards.physical.toasts.duplicated'));
        navigate(`/physicals/${newId}`);
      }
    } catch (err) {
      toast.error(err?.response?.data?.detail || t('dashboards.physical.toasts.duplicateError'));
    } finally {
      setDuplicating(false);
    }
  };

  const saveExtras = async (nextExtras) => {
    try {
      // Naive reconciliation: delete existing rows and recreate from form
      // state. The same pattern used across the other dashboards; works fine
      // for the small extras lists typical of physical products.
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
      toast.success(t('dashboards.physical.toasts.extrasUpdated'));
    } catch {
      toast.error(t('dashboards.physical.toasts.extrasError'));
    }
  };

  // Preview of fulfillment modes across the selected stores (mirrors wizard).
  const previewFulfillmentModes = useMemo(() => {
    const targets = (productForm.store_ids && productForm.store_ids.length > 0)
      ? stores.filter(s => productForm.store_ids.includes(s.id))
      : stores;
    const set = new Set();
    for (const s of targets) {
      for (const m of (s.fulfillment_modes || ['shipping'])) set.add(m);
    }
    return Array.from(set);
  }, [productForm.store_ids, stores]);

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center text-sm text-gray-500">{t('dashboards.common.loading')}</div>;
  }
  if (error === 'not_found') {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-6">
        <div className="max-w-md text-center bg-white rounded-xl border p-8">
          <h1 className="text-2xl font-bold mb-2">{t('dashboards.physical.notFound')}</h1>
          <button onClick={() => navigate('/products?type=physical')} className="rounded-md bg-gray-900 text-white px-4 py-2 text-sm">
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
          <h1 className="text-2xl font-bold mb-2">{t('dashboards.physical.invalidType')}</h1>
          <p className="text-gray-600 mb-4">{t('dashboards.physical.invalidTypeDesc')}</p>
          <button onClick={() => navigate('/products')} className="rounded-md bg-gray-900 text-white px-4 py-2 text-sm">{t('dashboards.common.backToProducts')}</button>
        </div>
      </div>
    );
  }

  const hero = productForm.cover_image_url || productForm.image_url;
  const stockValue = productForm.track_stock && productForm.stock_quantity !== ''
    ? Number(productForm.stock_quantity)
    : (productForm.track_stock ? 0 : null);

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
              <Link to="/products?type=physical" className="inline-flex items-center gap-1 text-sm font-medium text-white/70 hover:text-white transition-colors">{t('dashboards.physical.back')}</Link>
              <p className="text-[10px] uppercase tracking-widest opacity-70 mt-2">{t('dashboards.physical.typeLabel')}</p>
              <h1 className="text-2xl sm:text-3xl font-bold mt-1">{productForm.name || t('dashboards.physical.fallbackName')}</h1>
              {productForm.unit_price !== '' && (
                <div className="mt-2 text-sm sm:text-base opacity-90">
                  {formatEuro(productForm.unit_price, productForm.currency || orgCurrency, i18n.language)}
                </div>
              )}
            </div>
            <div className="shrink-0 flex flex-col sm:items-end gap-2">
              <StatusPill isPublished={productForm.is_published} />
              <StockBadge stockQuantity={stockValue} />
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-4 sm:px-6 py-5 sm:py-8 space-y-5">
        {/* CG3 — i numeri del prodotto (venduto, ricavo, giacenza) */}
        <ProductSalesStats productId={productId} productName={productForm.name}
                           stockQuantity={stockValue} />

        {/* Stato prodotto */}
        <div className="rounded-xl border border-gray-200 bg-white px-5 py-4">
          <div className="flex items-center justify-between gap-3">
            <div className="min-w-0">
              <h2 className="text-sm font-semibold text-gray-900">{t('dashboards.physical.statusTitle')}</h2>
              <p className="text-xs text-gray-500 mt-0.5">
                {productForm.is_published
                  ? t('dashboards.physical.statusOnlineDesc')
                  : t('dashboards.physical.statusOfflineDesc')}
              </p>
            </div>
            <div className="relative inline-flex shrink-0">
              <select
                value={productForm.is_published ? 'published' : 'draft'}
                onChange={(e) => quickTogglePublish(e.target.value === 'published')}
                className={`rounded-full pl-4 pr-8 py-1.5 text-sm font-semibold border-0 cursor-pointer appearance-none focus:outline-none focus:ring-2 focus:ring-gray-900/10 ${
                  productForm.is_published ? 'bg-green-100 text-green-900' : 'bg-gray-100 text-gray-700'
                }`}
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
            >{t('dashboards.physical.landingPreview')}</a>
          ) : (
            <div
              className="rounded-xl border border-dashed border-gray-300 bg-gray-50 px-4 py-3 text-sm text-gray-500 text-center"
              title={landingBlockers.length ? landingBlockers.join('\n') : undefined}
            >
              {t('dashboards.physical.landingUnavailable')}
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
          >{t('dashboards.physical.landingCopy')}</button>
          <button
            type="button"
            onClick={handleDuplicate}
            disabled={duplicating}
            className="rounded-xl border border-gray-300 bg-white px-4 py-3 text-sm font-semibold text-gray-900 hover:border-gray-900 disabled:opacity-50"
          >{duplicating ? t('dashboards.physical.duplicateLoading') : t('dashboards.physical.duplicateBtn')}</button>
        </div>

        {/* Inventario */}
        <div className="rounded-xl border border-gray-200 bg-white overflow-hidden">
          <button
            type="button"
            onClick={() => setInventoryOpen(v => !v)}
            className="w-full flex items-center justify-between px-5 py-3 text-left hover:bg-gray-50"
          >
            <span className="text-sm font-semibold text-gray-900">{t('dashboards.physical.inventory.title')}</span>
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
                  <span className="text-sm font-medium text-gray-900">{t('dashboards.physical.inventory.trackStockTitle')}</span>
                  <p className="text-xs text-gray-500 mt-0.5">
                    {t('dashboards.physical.inventory.trackStockDesc')}
                  </p>
                </span>
              </label>
              {productForm.track_stock && (
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">{t('dashboards.physical.inventory.stockLabel')}</label>
                  <input
                    type="number" min="0" step="1"
                    value={productForm.stock_quantity}
                    onChange={e => setProductForm({ ...productForm, stock_quantity: e.target.value })}
                    placeholder="0"
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
                >{savingProduct ? t('dashboards.common.saving') : t('dashboards.physical.inventory.saveBtn')}</button>
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
            <span className="text-sm font-semibold text-gray-900">{t('dashboards.physical.identity.title')}</span>
            <span className="text-gray-400 text-xs">{identityOpen ? '▲' : '▼'}</span>
          </button>
          {identityOpen && (
            <div className="border-t border-gray-100 px-5 py-4 space-y-3">
              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">{t('dashboards.physical.identity.nameLabel')}</label>
                <input
                  type="text" value={productForm.name}
                  onChange={e => setProductForm({ ...productForm, name: e.target.value })}
                  maxLength={255}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm bg-white"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">{t('dashboards.physical.identity.shortDescLabel')}</label>
                <textarea
                  rows={2} maxLength={2000}
                  value={productForm.description}
                  onChange={e => setProductForm({ ...productForm, description: e.target.value })}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm bg-white resize-none"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">{t('dashboards.physical.identity.longDescLabel')}</label>
                <textarea
                  rows={4} maxLength={5000}
                  value={productForm.long_description}
                  onChange={e => setProductForm({ ...productForm, long_description: e.target.value })}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm bg-white resize-none"
                />
              </div>
              <MultiLangSection fields={[
                { key: 'name', label: t('dashboards.physical.identity.nameLabel', { defaultValue: 'Nome' }), it: productForm.name,
                  value: trName, onChange: setTrName, input: true, maxLength: 255 },
                { key: 'description', label: t('dashboards.physical.identity.shortDescLabel'), it: productForm.description,
                  value: trDescription, onChange: setTrDescription, rows: 2, maxLength: 2000 },
                { key: 'long_description', label: t('dashboards.physical.identity.longDescLabel'), it: productForm.long_description,
                  value: trLong, onChange: setTrLong, rows: 4, maxLength: 5000 },
              ]}>{null}</MultiLangSection>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-gray-700 mb-1">{t('dashboards.physical.identity.skuLabel')}</label>
                  <input
                    type="text" value={productForm.sku}
                    onChange={e => setProductForm({ ...productForm, sku: e.target.value })}
                    maxLength={120}
                    className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm bg-white"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-gray-700 mb-1">{t('dashboards.physical.identity.categoryLabel')}</label>
                  <input
                    type="text" value={productForm.category}
                    onChange={e => setProductForm({ ...productForm, category: e.target.value })}
                    maxLength={120}
                    className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm bg-white"
                  />
                </div>
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">{t('dashboards.physical.identity.imageLabel')}</label>
                <input
                  type="url" value={productForm.image_url}
                  onChange={e => setProductForm({ ...productForm, image_url: e.target.value })}
                  maxLength={500}
                  placeholder={t('dashboards.physical.identity.imageUrlLabel')}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm bg-white"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">{t('dashboards.physical.identity.coverLabel')}</label>
                <input
                  type="url" value={productForm.cover_image_url}
                  onChange={e => setProductForm({ ...productForm, cover_image_url: e.target.value })}
                  maxLength={500}
                  placeholder={t('dashboards.physical.identity.coverUrlPlaceholder')}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm bg-white"
                />
              </div>
              <div className="pt-1">
                <button
                  type="button"
                  onClick={saveProduct}
                  disabled={savingProduct}
                  className="rounded-md bg-gray-900 text-white px-4 py-2 text-sm font-semibold hover:bg-gray-800 disabled:opacity-50"
                >{savingProduct ? t('dashboards.common.saving') : t('dashboards.physical.identity.saveBtn')}</button>
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
            <span className="text-sm font-semibold text-gray-900">{t('dashboards.physical.pricing.title')}</span>
            <span className="text-gray-400 text-xs">{pricingOpen ? '▲' : '▼'}</span>
          </button>
          {pricingOpen && (
            <div className="border-t border-gray-100 px-5 py-4 space-y-3">
              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">{t('dashboards.physical.pricing.priceLabel')}</label>
                <input
                  type="number" step="0.01" min="0"
                  value={productForm.unit_price}
                  onChange={e => setProductForm({ ...productForm, unit_price: e.target.value })}
                  className="w-full max-w-[180px] rounded-md border border-gray-300 px-3 py-2 text-sm bg-white"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">{t('dashboards.physical.pricing.modeLabel')}</label>
                <select
                  value={productForm.transaction_mode}
                  onChange={e => setProductForm({ ...productForm, transaction_mode: e.target.value })}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm bg-white"
                >
                  <option value="direct">{t('dashboards.physical.pricing.modeDirect')}</option>
                  <option value="approval">{t('dashboards.physical.pricing.modeApproval')}</option>
                  <option value="request">{t('dashboards.physical.pricing.modeRequest')}</option>
                </select>
              </div>

              {/* Sezione "Costo del prodotto" (COGS) rimossa dalla UI su
                  richiesta founder 16/7/2026: cost_source resta nel form
                  e nel salvataggio, i dati esistenti non si toccano. */}

              <div className="pt-1">
                <button
                  type="button"
                  onClick={saveProduct}
                  disabled={savingProduct}
                  className="rounded-md bg-gray-900 text-white px-4 py-2 text-sm font-semibold hover:bg-gray-800 disabled:opacity-50"
                >{savingProduct ? t('dashboards.common.saving') : t('dashboards.physical.pricing.saveBtn')}</button>
              </div>
            </div>
          )}
        </div>

        {/* Fulfillment */}
        <div className="rounded-xl border border-gray-200 bg-white overflow-hidden">
          <button
            type="button"
            onClick={() => setFulfillmentOpen(v => !v)}
            className="w-full flex items-center justify-between px-5 py-3 text-left hover:bg-gray-50"
          >
            <span className="text-sm font-semibold text-gray-900">{t('dashboards.physical.fulfillment.title')}</span>
            <span className="text-gray-400 text-xs">{fulfillmentOpen ? '▲' : '▼'}</span>
          </button>
          {fulfillmentOpen && (
            <div className="border-t border-gray-100 px-5 py-4 space-y-3">
              <div className="rounded-lg bg-blue-50 border border-blue-200 p-3 text-xs text-blue-900">
                <p className="font-semibold mb-1">{t('dashboards.physical.fulfillment.modesEnabled')}</p>
                {previewFulfillmentModes.length === 0 ? (
                  <p>{t('dashboards.physical.fulfillment.noStoresShort')}</p>
                ) : (
                  <ul className="space-y-0.5">
                    {previewFulfillmentModes.includes('shipping') && <li>{t('dashboards.physical.fulfillment.shippingShort')}</li>}
                    {previewFulfillmentModes.includes('local_pickup') && <li>{t('dashboards.physical.fulfillment.pickupShort')}</li>}
                  </ul>
                )}
                <p className="mt-1 text-[11px] text-blue-800">
                  {t('dashboards.physical.fulfillment.modesHint')}
                </p>
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">{t('dashboards.physical.fulfillment.notesLabel')}</label>
                <textarea
                  rows={3} maxLength={500}
                  value={productForm.fulfillment_notes}
                  onChange={e => setProductForm({ ...productForm, fulfillment_notes: e.target.value })}
                  placeholder={t('dashboards.physical.fulfillment.notesPlaceholder')}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm bg-white resize-none"
                />
              </div>
              <div className="pt-1">
                <button
                  type="button"
                  onClick={saveProduct}
                  disabled={savingProduct}
                  className="rounded-md bg-gray-900 text-white px-4 py-2 text-sm font-semibold hover:bg-gray-800 disabled:opacity-50"
                >{savingProduct ? t('dashboards.common.saving') : t('dashboards.physical.fulfillment.saveBtn')}</button>
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
            <span className="text-sm font-semibold text-gray-900">{t('dashboards.physical.extras.title')}</span>
            <span className="text-gray-400 text-xs">{extrasOpen ? '▲' : '▼'}</span>
          </button>
          {extrasOpen && (
            <div className="border-t border-gray-100 px-5 py-4">
              <ProductExtrasEditor
                extras={extras}
                onChange={saveExtras}
                productItemType="physical"
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
            <span className="text-sm font-semibold text-gray-900">{t('dashboards.physical.terms.title')}</span>
            <span className="text-gray-400 text-xs">{termsOpen ? '▲' : '▼'}</span>
          </button>
          {termsOpen && (
            <div className="border-t border-gray-100 px-5 py-4 space-y-3">
              <textarea
                rows={5} maxLength={5000}
                value={productForm.terms_content}
                onChange={e => setProductForm({ ...productForm, terms_content: e.target.value })}
                placeholder={t('dashboards.physical.terms.hint')}
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
                  {t('dashboards.physical.distribution.visibleIn')} <strong>{stores[0]?.name || t('dashboards.common.distributionAllStoresFallback')}</strong>
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

        {/* Ordini recenti */}
        <div className="rounded-xl border border-gray-200 bg-white overflow-hidden">
          <button
            type="button"
            onClick={() => setRecentOrdersOpen(v => !v)}
            className="w-full flex items-center justify-between px-5 py-3 text-left hover:bg-gray-50"
          >
            <span className="text-sm font-semibold text-gray-900">{t('dashboards.physical.orders.title')}</span>
            <span className="text-gray-400 text-xs">{recentOrdersOpen ? '▲' : '▼'}</span>
          </button>
          {recentOrdersOpen && (
            <div className="border-t border-gray-100 px-5 py-4">
              {recentOrdersLoading ? (
                <p className="text-sm text-gray-500">{t('dashboards.common.loading')}</p>
              ) : recentOrders.length === 0 ? (
                <p className="text-sm text-gray-500">{t('dashboards.physical.orders.empty')}</p>
              ) : (
                <ul className="divide-y divide-gray-100">
                  {recentOrders.map(o => {
                    const qty = (o.items || [])
                      .filter(it => it.product_id === productId)
                      .reduce((acc, it) => acc + Number(it.quantity || 0), 0);
                    const ref = o.order_number || (o.id || '').slice(0, 12);
                    const ff = o.fulfillment?.status || '—';
                    return (
                      <li key={o.id} className="py-2 flex items-center justify-between gap-3 text-sm">
                        <div className="min-w-0 flex-1">
                          <button
                            type="button"
                            onClick={() => navigate(`/orders?selected=${o.id}`)}
                            className="font-medium text-gray-900 hover:underline"
                          >
                            #{ref}
                          </button>
                          <span className="text-gray-500 ml-2">{o.customer_name || '—'}</span>
                        </div>
                        <span className="text-xs text-gray-500 whitespace-nowrap tabular-nums">× {qty}</span>
                        <span className="text-[11px] text-gray-500 whitespace-nowrap">{ff}</span>
                      </li>
                    );
                  })}
                </ul>
              )}
            </div>
          )}
        </div>

      </div>
    </div>
  );
}
