/**
 * ServiceDashboardPage — admin control center for one service product
 * (Onda 13 redesign).
 *
 * Route: /services/:product_id (authenticated)
 *
 * Layout mirrors EventDashboardPage:
 *   - Hero: cover image + title + quick-status pill (Online/Offline)
 *   - Stato servizio card (with dropdown + description)
 *   - Action bar: Anteprima landing / Copia link / Duplica
 *   - Product panel (name, description, image, unit_price, duration,
 *     transaction_mode, allow_custom_request)
 *   - Cover image + long_description card
 *   - Availability rules editor
 *   - Service options editor
 *   - Distribuzione panel (store assignment)
 *   - Termini e condizioni + order_fields
 */

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';
import { productsAPI } from '../../api';
import { storesAPI } from '../../api/stores';
import { availabilityAPI } from '../../api/availability';
import { serviceOptionsAPI } from '../../api/serviceOptions';
import FieldEditorList from '../events/components/FieldEditorList';
import { pruneFieldConfigs } from '../events/components/fieldConfigUtils';
import ServiceOptionsEditor from './components/ServiceOptionsEditor';
import AvailabilityRulesEditor from './components/AvailabilityRulesEditor';
import useLandingUrl from '../products/hooks/useLandingUrl';
// W1.S5/Phase 2.6 — additive cost composition editor for edits.
import CostSourceEditor from '../products/components/CostSourceEditor';
import MultiLangSection from '../../components/MultiLangSection';


function formatEuro(n, locale = 'it-IT') {
  if (n == null || n === '') return '—';
  try { return new Intl.NumberFormat(locale, { style: 'currency', currency: 'EUR' }).format(Number(n)); }
  catch { return `${n} €`; }
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


export default function ServiceDashboardPage() {
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
    name: '', description: '', image_url: '',
    unit_price: '', transaction_mode: 'request', is_published: false,
    duration_minutes: 60,
    service_allow_custom_request: false,
    // Onda 15 — "Usa calendario ufficiale" flag (see wizard for rationale)
    use_default_schedule: false,
    terms_content: '',
    order_fields: [],
    long_description: '',
    cover_image_url: '',
    store_ids: [],
  });
  const [savingProduct, setSavingProduct] = useState(false);
  const [duplicating, setDuplicating] = useState(false);
  // orgSlug no longer computed client-side — useLandingUrl resolves server-side.

  const [rules, setRules] = useState([]);
  const [options, setOptions] = useState([]);
  const [stores, setStores] = useState([]);

  // Collapsible panel state — mirrors EventDashboardPage pattern.
  const [editProductOpen, setEditProductOpen] = useState(true);
  const [editLongDescOpen, setEditLongDescOpen] = useState(false);
  const [editTermsOpen, setEditTermsOpen] = useState(false);
  const [editDistributionOpen, setEditDistributionOpen] = useState(false);

  // Onda 14 Parte C — upcoming bookings list for this service.
  const [bookings, setBookings] = useState([]);
  const [bookingsLoading, setBookingsLoading] = useState(false);
  const [bookingsOpen, setBookingsOpen] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [prodRes, storesRes] = await Promise.all([
        productsAPI.list(false),
        storesAPI.list().catch(() => ({ data: { stores: [] } })),
      ]);
      const prod = (prodRes.data || []).find(p => p.id === productId);
      if (!prod) { setError('not_found'); return; }
      if (prod.item_type !== 'service') { setError('wrong_type'); return; }
      setProduct(prod);
      setStores(storesRes.data?.stores || []);

      // First published store slug — for the landing URL.

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
        unit_price: prod.unit_price != null ? String(prod.unit_price) : '',
        transaction_mode: prod.transaction_mode || 'request',
        is_published: prod.is_published || false,
        duration_minutes: meta.duration_minutes ?? 60,
        service_allow_custom_request: !!meta.service_allow_custom_request,
        use_default_schedule: !!meta.use_default_schedule,
        terms_content: meta.terms_content || '',
        order_fields: meta.order_fields || [],
        long_description: meta.long_description || '',
        cover_image_url: meta.cover_image_url || '',
        store_ids: prod.store_ids || [],
        // W1.S5/Phase 2.6 — hydrate cost composition.
        cost_source: prod.cost_source || null,
      });

      const [rulesRes, optionsRes] = await Promise.all([
        availabilityAPI.listRules(null, productId).catch(() => ({ data: { rules: [] } })),
        serviceOptionsAPI.list(productId).catch(() => ({ data: { options: [] } })),
      ]);
      setRules(rulesRes.data?.rules || []);
      setOptions(optionsRes.data?.options || []);
      setError(null);
    } catch (err) {
      setError(err?.response?.status === 404 ? 'not_found' : 'generic');
    } finally {
      setLoading(false);
    }
  }, [productId]);

  useEffect(() => { load(); }, [load]);

  // Onda 14 Parte C — load upcoming bookings for the "Prossimi
  // appuntamenti" panel. Runs once the product is resolved.
  const loadBookings = useCallback(async () => {
    if (!productId) return;
    setBookingsLoading(true);
    try {
      const res = await productsAPI.listBookings(productId, { upcoming: 1, limit: 10 });
      setBookings(res.data?.bookings || []);
    } catch {
      setBookings([]);
    } finally {
      setBookingsLoading(false);
    }
  }, [productId]);

  useEffect(() => { loadBookings(); }, [loadBookings]);

  const saveProduct = async () => {
    setSavingProduct(true);
    try {
      const existingMeta = product?.metadata || {};
      const upd = {
        name: productForm.name.trim(),
        description: productForm.description?.trim() || null,
        translations: buildTranslationsPayload(),
        image_url: productForm.image_url?.trim() || null,
        unit_price: productForm.unit_price !== '' ? Number(productForm.unit_price) : null,
        transaction_mode: productForm.transaction_mode,
        is_published: productForm.is_published,
        store_ids: productForm.store_ids || [],
        metadata: {
          ...existingMeta,
          duration_minutes: Number(productForm.duration_minutes) || 60,
          service_allow_custom_request: !!productForm.service_allow_custom_request,
          use_default_schedule: !!productForm.use_default_schedule,
          terms_content: productForm.terms_content?.trim() || null,
          order_fields: pruneFieldConfigs(productForm.order_fields),
          long_description: productForm.long_description?.trim() || null,
          cover_image_url: productForm.cover_image_url?.trim() || null,
        },
        // W1.S5/Phase 2.6 — additive cost composition.
        cost_source: productForm.cost_source || null,
      };
      const res = await productsAPI.update(productId, upd);
      // Merge backend response to pick up slug updates
      const updatedProd = res.data || upd;
      setProduct(prev => prev ? { ...prev, ...updatedProd } : prev);
      toast.success(t('dashboards.service.toasts.updated'));
    } catch (err) {
      toast.error(err?.response?.data?.detail || t('dashboards.common.saveError'));
    } finally { setSavingProduct(false); }
  };

  const quickTogglePublish = async (next) => {
    const prev = productForm.is_published;
    setProductForm(f => ({ ...f, is_published: next }));
    setProduct(p => p ? { ...p, is_published: next } : p);
    try {
      await productsAPI.update(productId, { is_published: next });
      toast.success(next ? t('dashboards.service.toasts.online') : t('dashboards.service.toasts.offline'));
    } catch {
      setProductForm(f => ({ ...f, is_published: prev }));
      setProduct(p => p ? { ...p, is_published: prev } : p);
      toast.error(t('dashboards.service.toasts.statusError'));
    }
  };

  const handleDuplicate = async () => {
    if (duplicating) return;
    setDuplicating(true);
    try {
      const res = await productsAPI.duplicate(productId);
      toast.success(t('dashboards.service.toasts.duplicated'));
      const newId = res.data?.id;
      if (newId) navigate(`/services/${newId}`);
    } catch (err) {
      toast.error(err?.response?.data?.detail || t('dashboards.service.toasts.duplicateError'));
    } finally {
      setDuplicating(false);
    }
  };

  // Server-resolved landing URL (respects store_ids / visibility / publish).
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
      toast.error(t('dashboards.common.linkCopyError'));
    }
  };

  // Rules: delete-all + recreate (dataset is tiny)
  const saveRules = async (nextRules) => {
    try {
      for (const old of rules) {
        if (old.id) {
          try { await availabilityAPI.deleteRule(old.id); } catch { /* ignore */ }
        }
      }
      const created = [];
      for (const r of nextRules) {
        try {
          const res = await availabilityAPI.createRule({
            product_id: productId,
            day_of_week: r.day_of_week,
            start_time: r.start_time,
            end_time: r.end_time,
            slot_duration_minutes: r.slot_duration_minutes || 60,
          });
          created.push(res.data);
        } catch { /* ignore individual failures */ }
      }
      setRules(created.length ? created : nextRules);
      toast.success(t('dashboards.service.toasts.availabilityUpdated'));
    } catch {
      toast.error(t('dashboards.service.toasts.availabilityError'));
    }
  };

  const saveOptions = async (nextOptions) => {
    try {
      const oldOptsById = new Map(options.filter(o => o.id).map(o => [o.id, o]));
      for (const existing of options) {
        if (!existing.id) continue;
        const stillThere = nextOptions.find(n => n.id === existing.id);
        if (!stillThere) {
          try { await serviceOptionsAPI.delete(productId, existing.id); } catch { /* ignore */ }
        }
      }
      const updated = [];
      for (const o of nextOptions) {
        if (o.id && oldOptsById.has(o.id)) {
          try {
            const res = await serviceOptionsAPI.update(productId, o.id, {
              label: o.label,
              description: o.description || null,
              price: Number(o.price) || 0,
              duration_minutes_override: o.duration_minutes_override ? Number(o.duration_minutes_override) : null,
              sort_order: o.sort_order ?? 0,
              is_active: o.is_active !== false,
            });
            updated.push(res.data);
          } catch { updated.push(o); }
        } else {
          try {
            const res = await serviceOptionsAPI.create(productId, {
              label: o.label,
              description: o.description || null,
              price: Number(o.price) || 0,
              duration_minutes_override: o.duration_minutes_override ? Number(o.duration_minutes_override) : null,
              sort_order: o.sort_order ?? 0,
              is_active: o.is_active !== false,
            });
            updated.push(res.data);
          } catch { /* ignore */ }
        }
      }
      setOptions(updated);
      toast.success(t('dashboards.service.toasts.optionsUpdated'));
    } catch {
      toast.error(t('dashboards.service.toasts.optionsError'));
    }
  };

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center text-sm text-gray-500">{t('dashboards.common.loading')}</div>;
  }
  if (error === 'not_found') {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-6">
        <div className="max-w-md text-center bg-white rounded-xl border p-8">
          <h1 className="text-2xl font-bold mb-2">{t('dashboards.service.notFound')}</h1>
          <button onClick={() => navigate('/products')} className="rounded-md bg-gray-900 text-white px-4 py-2 text-sm">
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
          <h1 className="text-2xl font-bold mb-2">{t('dashboards.service.invalidType')}</h1>
          <p className="text-gray-600 mb-4">{t('dashboards.service.invalidTypeDesc')}</p>
          <button onClick={() => navigate('/products')} className="rounded-md bg-gray-900 text-white px-4 py-2 text-sm">{t('dashboards.common.backToProducts')}</button>
        </div>
      </div>
    );
  }

  const hero = productForm.cover_image_url || productForm.image_url;

  return (
    <div className="min-h-screen bg-gray-50 pb-20">
      {/* Hero — mirror EventDashboardPage */}
      <div className="relative bg-gray-900 text-white overflow-hidden">
        {hero && (
          <img src={hero} alt="" className="absolute inset-0 w-full h-full object-cover opacity-50" />
        )}
        <div className="relative max-w-4xl mx-auto px-4 sm:px-6 py-6 sm:py-10">
          <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
            <div className="min-w-0">
              <Link to="/products?type=service" className="inline-flex items-center gap-1 text-sm font-medium text-white/70 hover:text-white transition-colors">{t('dashboards.service.back')}</Link>
              <p className="text-[10px] uppercase tracking-widest opacity-70 mt-2">{t('dashboards.service.typeLabel')}</p>
              <h1 className="text-2xl sm:text-3xl font-bold mt-1">{productForm.name || t('dashboards.service.fallbackName')}</h1>
              {productForm.duration_minutes && (
                <div className="mt-2 text-sm sm:text-base opacity-90">
                  ⏱ {productForm.duration_minutes} minuti
                </div>
              )}
            </div>
            <div className="shrink-0 flex flex-col sm:items-end gap-2">
              <StatusPill isPublished={productForm.is_published} />
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-4 sm:px-6 py-5 sm:py-8 space-y-5">

        {/* Stato servizio — dedicated, prominent status control */}
        <div className="rounded-xl border border-gray-200 bg-white px-5 py-4">
          <div className="flex items-center justify-between gap-3">
            <div className="min-w-0">
              <h2 className="text-sm font-semibold text-gray-900">{t('dashboards.service.statusTitle')}</h2>
              <p className="text-xs text-gray-500 mt-0.5">
                {productForm.is_published
                  ? t('dashboards.service.statusOnlineDesc')
                  : t('dashboards.service.statusOfflineDesc')}
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
            >{t('dashboards.service.landingPreview')}</a>
          ) : (
            <div
              className="rounded-xl border border-dashed border-gray-300 bg-gray-50 px-4 py-3 text-sm text-gray-500 text-center"
              title={landingBlockers.length ? landingBlockers.join('\n') : undefined}
            >
              {t('dashboards.service.landingUnavailable')}
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
          >{t('dashboards.service.landingCopy')}</button>
          <button
            type="button"
            onClick={handleDuplicate}
            disabled={duplicating}
            className="rounded-xl border border-gray-300 bg-white px-4 py-3 text-sm font-semibold text-gray-900 hover:border-gray-900 disabled:opacity-50"
          >{duplicating ? t('dashboards.service.duplicateLoading') : t('dashboards.service.duplicateBtn')}</button>
        </div>

        {/* ── Prossimi appuntamenti (Onda 14 Parte C) ──────────────── */}
        <div className="rounded-xl border border-gray-200 bg-white overflow-hidden">
          <button
            type="button"
            onClick={() => setBookingsOpen(v => !v)}
            className="w-full flex items-center justify-between px-5 py-3 text-left hover:bg-gray-50"
          >
            <span className="text-sm font-semibold text-gray-900">
              {t('dashboards.service.upcomingTitle')}
              {bookings.length > 0 && (
                <span className="ml-2 inline-flex items-center justify-center rounded-full bg-gray-900 text-white text-[10px] font-bold h-5 min-w-[20px] px-1.5">
                  {bookings.length}
                </span>
              )}
            </span>
            <span className="text-gray-400 text-xs">{bookingsOpen ? '▲' : '▼'}</span>
          </button>
          {bookingsOpen && (
            <div className="border-t border-gray-100 px-5 py-4 space-y-3">
              {bookingsLoading ? (
                <p className="text-sm text-gray-500">{t('dashboards.service.upcomingLoading')}</p>
              ) : bookings.length === 0 ? (
                <div className="rounded-md bg-gray-50 border border-dashed border-gray-200 px-3 py-3 text-sm text-gray-600">
                  {t('dashboards.service.upcomingEmpty')}
                </div>
              ) : (
                <>
                  <ul className="divide-y divide-gray-100">
                    {bookings.map((b, idx) => {
                      const dt = b.date ? new Date(b.date + 'T12:00') : null;
                      const dateLbl = dt
                        ? dt.toLocaleDateString(i18n.language, { weekday: 'short', day: 'numeric', month: 'short' })
                        : b.date;
                      const statusLbl = b.order_status === 'confirmed'
                        ? t('dashboards.service.bookingConfirmed')
                        : b.order_status === 'draft' || b.order_status === 'pending'
                          ? t('dashboards.service.bookingPending')
                          : (b.order_status || '—');
                      return (
                        <li key={b.order_id || idx} className="py-2">
                          <Link
                            to={b.order_id ? `/orders/${b.order_id}` : '#'}
                            className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm hover:bg-gray-50 rounded px-1 -mx-1 py-1"
                          >
                            <span className="font-semibold text-gray-900 tabular-nums">
                              {dateLbl} · {b.start_time}
                            </span>
                            <span className="text-gray-600">
                              {b.customer_name || t('dashboards.service.customerAnonymous')}
                            </span>
                            {b.order_number && (
                              <span className="text-gray-400 font-mono text-xs">#{b.order_number}</span>
                            )}
                            <span className={`text-xs font-medium ${
                              b.order_status === 'confirmed' ? 'text-green-700' : 'text-amber-700'
                            }`}>
                              {statusLbl}
                            </span>
                          </Link>
                        </li>
                      );
                    })}
                  </ul>
                  <Link
                    to={`/calendar?product_id=${productId}`}
                    className="block text-xs font-medium text-gray-600 hover:text-gray-900 pt-1 border-t border-gray-100"
                  >
                    {t('dashboards.service.seeAllInCalendar')}
                  </Link>
                </>
              )}
            </div>
          )}
        </div>

        {/* ── Product panel (collapsible) ───────────────────────────── */}
        <div className="rounded-xl border border-gray-200 bg-white overflow-hidden">
          <button
            type="button"
            onClick={() => setEditProductOpen(v => !v)}
            className="w-full flex items-center justify-between px-5 py-3 text-left hover:bg-gray-50"
          >
            <span className="text-sm font-semibold text-gray-900">{t('dashboards.service.product.title')}</span>
            <span className="text-gray-400 text-xs">{editProductOpen ? '▲' : '▼'}</span>
          </button>
          {editProductOpen && (
            <div className="border-t border-gray-100 px-5 py-4 space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="sm:col-span-2">
                  <label className="block text-xs font-medium text-gray-700 mb-1">{t('dashboards.service.product.nameLabel')}</label>
                  <input type="text" value={productForm.name}
                    onChange={e => setProductForm(f => ({ ...f, name: e.target.value }))}
                    className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none" />
                </div>
                <div className="sm:col-span-2">
                  <label className="block text-xs font-medium text-gray-700 mb-1">{t('dashboards.service.product.descriptionLabel')}</label>
                  <textarea value={productForm.description}
                    onChange={e => setProductForm(f => ({ ...f, description: e.target.value }))}
                    rows={2}
                    className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none resize-none" />
                  <MultiLangSection fields={[
                    { key: 'name', label: t('dashboards.service.product.nameLabel'), it: productForm.name,
                      value: trName, onChange: setTrName, input: true, maxLength: 255 },
                    { key: 'description', label: t('dashboards.service.product.descriptionLabel'), it: productForm.description,
                      value: trDescription, onChange: setTrDescription, rows: 2, maxLength: 2000 },
                  ]}>{null}</MultiLangSection>
                </div>

                {/* Product image */}
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">{t('dashboards.service.product.imageLabel')}</label>
                  <label className="flex items-center gap-2 cursor-pointer rounded-md border border-dashed border-gray-300 px-3 py-2 text-sm text-gray-600 hover:border-gray-900">
                    <span>{t('dashboards.common.uploadButton')}</span>
                    <input
                      type="file" accept=".jpg,.jpeg,.png,.webp" className="hidden"
                      onChange={async e => {
                        const file = e.target.files?.[0];
                        if (!file) return;
                        try {
                          const res = await productsAPI.uploadImage(productId, file);
                          const url = res.data?.image_url;
                          setProductForm(f => ({ ...f, image_url: url }));
                          setProduct(p => p ? { ...p, image_url: url } : p);
                          toast.success(t('dashboards.common.imageUploaded'));
                        } catch { toast.error(t('dashboards.common.imageUploadError')); }
                        e.target.value = '';
                      }}
                    />
                  </label>
                  <input type="url" value={productForm.image_url}
                    onChange={e => setProductForm(f => ({ ...f, image_url: e.target.value }))}
                    placeholder={t('dashboards.common.imageUrlPlaceholder')}
                    className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none" />
                  {productForm.image_url && (
                    <img src={productForm.image_url} alt="" className="mt-2 h-16 w-full object-cover rounded-md border" />
                  )}
                </div>

                {/* Cover image (landing hero) */}
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">{t('dashboards.service.product.coverLabel')}</label>
                  <input type="url" value={productForm.cover_image_url}
                    onChange={e => setProductForm(f => ({ ...f, cover_image_url: e.target.value }))}
                    placeholder={t('dashboards.service.product.coverPlaceholder')}
                    className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none" />
                  <p className="text-[10px] text-gray-400 mt-0.5">{t('dashboards.service.product.coverHint')}</p>
                  {productForm.cover_image_url && (
                    <img src={productForm.cover_image_url} alt="" className="mt-2 h-16 w-full object-cover rounded-md border" />
                  )}
                </div>

                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">{t('dashboards.service.product.priceLabel')}</label>
                  <input type="number" step="0.01" min="0" value={productForm.unit_price}
                    onChange={e => setProductForm(f => ({ ...f, unit_price: e.target.value }))}
                    className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none" />
                  <p className="text-[10px] text-gray-400 mt-0.5">{t('dashboards.service.product.priceHint')}</p>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">{t('dashboards.service.product.durationLabel')}</label>
                  <input type="number" min="5" max="1440" value={productForm.duration_minutes}
                    onChange={e => setProductForm(f => ({ ...f, duration_minutes: e.target.value }))}
                    className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none" />
                </div>
              </div>

              <div>
                <p className="text-xs font-medium text-gray-700 mb-1.5">{t('dashboards.service.product.modeLabel')}</p>
                <div className="flex gap-1.5">
                  {[{ v: 'request', labelKey: 'dashboards.service.product.modeRequest' }, { v: 'direct', labelKey: 'dashboards.service.product.modeDirect' }].map(opt => (
                    <button key={opt.v} type="button"
                      onClick={() => setProductForm(f => ({ ...f, transaction_mode: opt.v }))}
                      className={`rounded-full px-3 py-1 text-xs font-semibold border transition ${
                        productForm.transaction_mode === opt.v
                          ? 'bg-gray-900 text-white border-gray-900'
                          : 'bg-white text-gray-700 border-gray-300 hover:border-gray-900'
                      }`}
                    >{t(opt.labelKey)}</button>
                  ))}
                </div>
              </div>

              <label className="flex items-start gap-3 cursor-pointer rounded-lg border border-gray-200 bg-gray-50 p-3">
                <input
                  type="checkbox"
                  checked={productForm.service_allow_custom_request}
                  onChange={e => setProductForm(f => ({ ...f, service_allow_custom_request: e.target.checked }))}
                  className="mt-0.5 h-4 w-4 rounded border-gray-300"
                />
                <div className="flex-1">
                  <span className="block text-sm font-semibold text-gray-900">
                    {t('dashboards.service.product.allowCustomTitle')}
                  </span>
                  <span className="block text-xs text-gray-500 mt-0.5">
                    {t('dashboards.service.product.allowCustomHint')}
                  </span>
                </div>
              </label>

              {/* W1.S5/Phase 2.6 — Cost composition (edit). */}
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
                  onChange={(next) => setProductForm(f => ({ ...f, cost_source: next }))}
                />
              </div>

              <div className="flex justify-end">
                <button type="button" disabled={savingProduct || !productForm.name.trim()}
                  onClick={saveProduct}
                  className="rounded-md bg-gray-900 text-white px-4 py-2 text-sm font-semibold hover:bg-gray-800 disabled:opacity-50"
                >{savingProduct ? t('dashboards.common.saving') : t('dashboards.common.saveProduct')}</button>
              </div>
            </div>
          )}
        </div>

        {/* ── Long description (collapsible) ────────────────────────── */}
        <div className="rounded-xl border border-gray-200 bg-white overflow-hidden">
          <button
            type="button"
            onClick={() => setEditLongDescOpen(v => !v)}
            className="w-full flex items-center justify-between px-5 py-3 text-left hover:bg-gray-50"
          >
            <span className="text-sm font-semibold text-gray-900">{t('dashboards.service.longDescTitle')}</span>
            <span className="text-gray-400 text-xs">{editLongDescOpen ? '▲' : '▼'}</span>
          </button>
          {editLongDescOpen && (
            <div className="border-t border-gray-100 px-5 py-4 space-y-3">
              <p className="text-xs text-gray-500">
                {t('dashboards.service.longDescDescPrefix')}<code>##</code>{t('dashboards.service.longDescDescSuffix')}<code>{t('dashboards.service.longDescBoldNote')}</code>, <code>{t('dashboards.service.longDescListNote')}</code>.
              </p>
              <textarea
                value={productForm.long_description}
                onChange={e => setProductForm(f => ({ ...f, long_description: e.target.value }))}
                rows={8} maxLength={5000}
                placeholder={t('dashboards.service.longDescPlaceholder')}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-xs font-mono focus:border-gray-900 focus:outline-none resize-y"
              />
              <MultiLangSection fields={[
                { key: 'long_description', label: null, it: productForm.long_description,
                  value: trLong, onChange: setTrLong, rows: 5, maxLength: 5000 },
              ]}>{null}</MultiLangSection>
              <div className="flex justify-end">
                <button type="button" onClick={saveProduct}
                  disabled={savingProduct}
                  className="rounded-md bg-gray-900 text-white px-4 py-2 text-sm font-semibold hover:bg-gray-800 disabled:opacity-50"
                >{savingProduct ? t('dashboards.common.saving') : t('dashboards.common.saveDescription')}</button>
              </div>
            </div>
          )}
        </div>

        {/* ── Availability (Onda 15: toggle calendario standard) ───── */}
        <div className="rounded-xl border border-gray-200 bg-white p-4 space-y-3">
          <label className="flex items-start gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={!!productForm.use_default_schedule}
              onChange={(e) => {
                const next = e.target.checked;
                setProductForm(f => ({ ...f, use_default_schedule: next }));
                // Persistenza immediata come per le altre modifiche
                // inline del dashboard.
                (async () => {
                  try {
                    const existingMeta = product?.metadata || {};
                    await productsAPI.update(productId, {
                      metadata: {
                        ...existingMeta,
                        use_default_schedule: next,
                      },
                    });
                    toast.success(next ? t('dashboards.service.toasts.calendarOn') : t('dashboards.service.toasts.calendarOff'));
                  } catch {
                    setProductForm(f => ({ ...f, use_default_schedule: !next }));
                    toast.error(t('dashboards.common.saveError'));
                  }
                })();
              }}
              className="mt-1 rounded border-gray-300"
            />
            <div className="min-w-0 flex-1">
              <p className="text-sm font-semibold text-gray-900">
                {t('dashboards.service.calendarTitle')}
              </p>
              <p className="text-xs text-gray-500 mt-1">
                {t('dashboards.service.calendarDesc')}
              </p>
            </div>
          </label>

          {productForm.use_default_schedule ? (
            <div className="rounded-md bg-gray-50 border border-gray-200 px-3 py-2 text-xs text-gray-600 flex items-center justify-between gap-3">
              <span>{t('dashboards.service.calendarFilterHint')}</span>
              <Link
                to="/calendar"
                className="shrink-0 font-medium text-gray-900 underline hover:no-underline"
              >
                {t('dashboards.service.openCalendar')}
              </Link>
            </div>
          ) : (
            <AvailabilityRulesEditor
              rules={rules}
              onChange={(next) => {
                setRules(next);
                saveRules(next);
              }}
              defaultSlotMinutes={Number(productForm.duration_minutes) || 60}
            />
          )}
        </div>

        {/* ── Service Options ──────────────────────────────────────── */}
        <ServiceOptionsEditor
          options={options}
          onChange={(next) => {
            setOptions(next);
            saveOptions(next);
          }}
          title={t('dashboards.service.optionsTitle')}
          subtitle={t('dashboards.service.optionsSubtitle')}
        />

        {/* ── Distribuzione — store assignment (collapsible) ─────────
            Onda 14: sempre visibile, anche con 1 solo store (read-only info). */}
        <div className="rounded-xl border border-gray-200 bg-white overflow-hidden">
          <button
            type="button"
            onClick={() => setEditDistributionOpen(v => !v)}
            className="w-full flex items-center justify-between px-5 py-3 text-left hover:bg-gray-50"
          >
            <span className="text-sm font-semibold text-gray-900">{t('dashboards.common.distributionTitle')}</span>
            <span className="text-gray-400 text-xs">{editDistributionOpen ? '▲' : '▼'}</span>
          </button>
          {editDistributionOpen && (
            <div className="border-t border-gray-100 px-5 py-4 space-y-2">
              {stores.length <= 1 ? (
                <>
                  <p className="text-xs text-gray-500">{t('dashboards.service.distributionDesc')}</p>
                  <div className="rounded-md bg-gray-50 border border-gray-200 px-3 py-2 text-sm text-gray-700 flex items-center gap-2">
                    <span aria-hidden>✓</span>
                    <span>
                      {t('dashboards.common.distributionVisibleAutoPrefix')} <strong>{stores[0]?.name || t('dashboards.common.distributionAllStoresFallback')}</strong>
                    </span>
                  </div>
                </>
              ) : (
                <>
                  <p className="text-xs text-gray-500">{t('dashboards.service.distributionMultiDesc')}</p>
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
                    const isSpecific = productForm.store_ids?.length > 0;
                    const checked = isSpecific && productForm.store_ids.includes(s.id);
                    return (
                      <label key={s.id} className="flex items-center gap-2 text-sm cursor-pointer">
                        <input
                          type="checkbox"
                          checked={checked}
                          onChange={() => {
                            setProductForm(f => {
                              const ids = f.store_ids || [];
                              return {
                                ...f,
                                store_ids: ids.includes(s.id)
                                  ? ids.filter(id => id !== s.id)
                                  : [...ids, s.id],
                              };
                            });
                          }}
                          className="rounded border-gray-300"
                        />
                        <span>{s.name}</span>
                      </label>
                    );
                  })}
                  <div className="flex justify-end pt-2">
                    <button type="button" onClick={saveProduct}
                      disabled={savingProduct}
                      className="rounded-md bg-gray-900 text-white px-4 py-2 text-sm font-semibold hover:bg-gray-800 disabled:opacity-50"
                    >{t('dashboards.common.saveDistribution')}</button>
                  </div>
                </>
              )}
            </div>
          )}
        </div>

        {/* ── Terms & Conditions (collapsible) ─────────────────────── */}
        <div className="rounded-xl border border-gray-200 bg-white overflow-hidden">
          <button
            type="button"
            onClick={() => setEditTermsOpen(v => !v)}
            className="w-full flex items-center justify-between px-5 py-3 text-left hover:bg-gray-50"
          >
            <span className="text-sm font-semibold text-gray-900">{t('dashboards.service.termsTitle')}</span>
            <span className="text-gray-400 text-xs">{editTermsOpen ? '▲' : '▼'}</span>
          </button>
          {editTermsOpen && (
            <div className="border-t border-gray-100 px-5 py-4 space-y-3">
              <p className="text-xs text-gray-500">
                {t('dashboards.common.termsHint')}
              </p>
              <textarea
                value={productForm.terms_content || ''}
                onChange={e => setProductForm(f => ({ ...f, terms_content: e.target.value }))}
                rows={6} maxLength={20000}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-xs font-mono focus:border-gray-900 focus:outline-none resize-y"
              />
              <div className="flex justify-end">
                <button type="button" onClick={saveProduct}
                  disabled={savingProduct}
                  className="rounded-md bg-gray-900 text-white px-4 py-2 text-sm font-semibold hover:bg-gray-800 disabled:opacity-50"
                >{t('dashboards.common.saveTerms')}</button>
              </div>
            </div>
          )}
        </div>

        {/* ── Order custom fields (FieldEditorList) ────────────────── */}
        <FieldEditorList
          fields={productForm.order_fields || []}
          onChange={(next) => {
            setProductForm(f => ({ ...f, order_fields: next }));
          }}
          title={t('dashboards.service.orderFieldsTitle')}
          subtitle={t('dashboards.service.orderFieldsSubtitle')}
          emptyHint={t('dashboards.service.orderFieldsEmpty')}
        />
        {/* No auto-save for order_fields: user clicks Salva prodotto to persist */}
        <p className="text-[11px] text-gray-400 -mt-3">{t('dashboards.service.orderFieldsHint')}</p>
      </div>
    </div>
  );
}
