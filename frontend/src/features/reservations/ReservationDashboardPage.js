/**
 * ReservationDashboardPage — admin control center for one rental/reservation
 * product (Onda 16 consolidamento UI prodotti).
 *
 * Route: /reservations/:product_id (authenticated)
 *
 * Mirrors ServiceDashboardPage structure so the whole catalog shares one
 * consistent pattern:
 *   - Hero: cover image + title + type badge + status pill
 *   - Stato prenotazione card (status dropdown)
 *   - Action bar: Anteprima landing · Copia link · Duplica
 *   - Collapsible panels:
 *       - Identità (name, description, image_url, cover_image_url, long_description)
 *       - Flavor & prezzo (flavor range/slot, unit_price, rental_unit | slot_duration)
 *       - Disponibilità (AvailabilityRulesEditor — slot flavor only)
 *       - Extras (ProductExtrasEditor — mandatory / optional / radio_variant)
 *       - Termini & condizioni + order_fields
 *       - Distribuzione (store assignment)
 *       - Prossime prenotazioni (IssuedReservation list for this product)
 *
 * Handles both flavors of the unified Prenotazione umbrella:
 *   - range: multi-day rentals (B&B, car, equipment)
 *   - slot:  single-shot time windows (meeting room, court)
 *
 * Supports legacy products with item_type='booking' (pre-Fase 6 migration)
 * by treating them equivalently to rental+slot.
 */

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';
import { productsAPI } from '../../api';
import { storesAPI } from '../../api/stores';
import { availabilityAPI } from '../../api/availability';
import { productExtrasAPI } from '../../api/productExtras';
import { issuedReservationsAPI } from '../../api/issuedReservations';
import FieldEditorList from '../events/components/FieldEditorList';
import { pruneFieldConfigs } from '../events/components/fieldConfigUtils';
import AvailabilityRulesEditor from '../services/components/AvailabilityRulesEditor';
import ProductExtrasEditor from './components/ProductExtrasEditor';
import useLandingUrl from '../products/hooks/useLandingUrl';
// W1.S5/Phase 2.7 — additive cost composition editor for edits.
import CostSourceEditor from '../products/components/CostSourceEditor';
import { useCurrency } from '../../context/AuthContext';
import { formatAmount } from '../../utils/currency';


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


/**
 * Derive flavor from product metadata + item_type.
 * Handles legacy booking (pre-Fase 6) and missing metadata.
 */
function deriveFlavor(product) {
  const meta = product?.metadata || {};
  if (meta.reservation_flavor) return meta.reservation_flavor;
  if (product?.item_type === 'booking') return 'slot';
  if (meta.rental_unit === 'ora') return 'slot';
  return 'range';
}


export default function ReservationDashboardPage() {
  const orgCurrency = useCurrency();
  const { product_id: productId } = useParams();
  const navigate = useNavigate();
  const { t, i18n } = useTranslation('products');

  const [product, setProduct] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [productForm, setProductForm] = useState({
    name: '',
    description: '',
    image_url: '',
    unit_price: '',
    transaction_mode: 'request',
    is_published: false,
    cover_image_url: '',
    long_description: '',
    store_ids: [],
    terms_content: '',
    order_fields: [],
    // flavor-specific
    reservation_flavor: 'range',
    rental_unit: 'giorno',
    slot_duration_minutes: 60,
    duration_label: '',
    // Onda 17 — variable-duration cross-day slot knobs (slot flavor only).
    slot_min_duration_minutes: '',
    slot_step_minutes: '',
    slot_max_duration_minutes: '',
  });
  const [savingProduct, setSavingProduct] = useState(false);
  const [duplicating, setDuplicating] = useState(false);
  // orgSlug no longer computed client-side — useLandingUrl (server-resolved)
  // is the source of truth for landing URLs.

  const [rules, setRules] = useState([]);
  const [extras, setExtras] = useState([]);
  const [stores, setStores] = useState([]);

  // Collapsible panel state
  const [editProductOpen, setEditProductOpen] = useState(true);
  const [editPricingOpen, setEditPricingOpen] = useState(true);
  const [editAvailabilityOpen, setEditAvailabilityOpen] = useState(false);
  const [editExtrasOpen, setEditExtrasOpen] = useState(false);
  const [editTermsOpen, setEditTermsOpen] = useState(false);
  const [editDistributionOpen, setEditDistributionOpen] = useState(false);
  const [reservationsOpen, setReservationsOpen] = useState(true);

  const [upcomingReservations, setUpcomingReservations] = useState([]);
  const [reservationsLoading, setReservationsLoading] = useState(false);

  const flavor = productForm.reservation_flavor || deriveFlavor(product);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [prodRes, storesRes] = await Promise.all([
        productsAPI.list(false),
        storesAPI.list().catch(() => ({ data: { stores: [] } })),
      ]);
      const prod = (prodRes.data || []).find(p => p.id === productId);
      if (!prod) { setError('not_found'); return; }
      // Accept both the canonical "rental" and legacy "booking" types.
      if (prod.item_type !== 'rental' && prod.item_type !== 'booking') {
        setError('wrong_type');
        return;
      }
      setProduct(prod);
      setStores(storesRes.data?.stores || []);


      const meta = prod.metadata || {};
      const derivedFlavor = deriveFlavor(prod);
      setProductForm({
        name: prod.name || '',
        description: prod.description || '',
        image_url: prod.image_url || '',
        unit_price: prod.unit_price != null ? String(prod.unit_price) : '',
        transaction_mode: prod.transaction_mode || 'request',
        is_published: !!prod.is_published,
        cover_image_url: meta.cover_image_url || '',
        long_description: meta.long_description || '',
        store_ids: prod.store_ids || [],
        terms_content: meta.terms_content || '',
        order_fields: meta.order_fields || [],
        reservation_flavor: derivedFlavor,
        rental_unit: meta.rental_unit || 'giorno',
        slot_duration_minutes: meta.slot_duration_minutes ?? 60,
        duration_label: meta.duration_label || '',
        slot_min_duration_minutes: meta.slot_min_duration_minutes ?? '',
        slot_step_minutes: meta.slot_step_minutes ?? '',
        slot_max_duration_minutes: meta.slot_max_duration_minutes ?? '',
        // W1.S5/Phase 2.7 — hydrate cost composition.
        cost_source: prod.cost_source || null,
      });

      // Availability rules are relevant for slot flavor only.
      if (derivedFlavor === 'slot') {
        const rulesRes = await availabilityAPI.listRules(null, productId).catch(() => ({ data: { rules: [] } }));
        setRules(rulesRes.data?.rules || []);
      } else {
        setRules([]);
      }

      const extrasRes = await productExtrasAPI.list(productId).catch(() => ({ data: { extras: [] } }));
      // Endpoint may return either { extras: [...] } or a bare list.
      setExtras(extrasRes.data?.extras || extrasRes.data || []);
      setError(null);
    } catch (err) {
      setError(err?.response?.status === 404 ? 'not_found' : 'generic');
    } finally {
      setLoading(false);
    }
  }, [productId]);

  useEffect(() => { load(); }, [load]);

  // Upcoming reservations (IssuedReservation) for this product.
  const loadUpcoming = useCallback(async () => {
    if (!productId) return;
    setReservationsLoading(true);
    try {
      // Server-side filter on product is not currently exposed; use status filter
      // and resolve client-side. Dataset per product stays small in practice.
      const res = await issuedReservationsAPI.list({ status: 'active', limit: 100 });
      const rows = (res.data?.reservations || []).filter(r => r.product_id === productId);
      setUpcomingReservations(rows.slice(0, 10));
    } catch {
      setUpcomingReservations([]);
    } finally {
      setReservationsLoading(false);
    }
  }, [productId]);

  useEffect(() => { loadUpcoming(); }, [loadUpcoming]);

  const saveProduct = async () => {
    setSavingProduct(true);
    try {
      const existingMeta = product?.metadata || {};
      const metaUpdate = {
        ...existingMeta,
        reservation_flavor: productForm.reservation_flavor,
        cover_image_url: productForm.cover_image_url?.trim() || null,
        long_description: productForm.long_description?.trim() || null,
        terms_content: productForm.terms_content?.trim() || null,
        order_fields: pruneFieldConfigs(productForm.order_fields),
        duration_label: productForm.duration_label?.trim() || null,
      };
      if (productForm.reservation_flavor === 'range') {
        metaUpdate.rental_unit = productForm.rental_unit?.trim() || 'giorno';
        // Slot-only keys are irrelevant for range; keep them if set by caller
        // but don't introduce them here.
      } else {
        metaUpdate.slot_duration_minutes = Number(productForm.slot_duration_minutes) || 60;
        // Onda 17 — persist variable-duration knobs when filled; null-out
        // when cleared so the backend reverts to slot_duration_minutes fallback.
        const _num = (v) => {
          const n = Number(v);
          return v === '' || v === null || Number.isNaN(n) || n <= 0 ? null : n;
        };
        metaUpdate.slot_min_duration_minutes = _num(productForm.slot_min_duration_minutes);
        metaUpdate.slot_step_minutes = _num(productForm.slot_step_minutes);
        metaUpdate.slot_max_duration_minutes = _num(productForm.slot_max_duration_minutes);
      }

      const upd = {
        name: productForm.name.trim(),
        description: productForm.description?.trim() || null,
        image_url: productForm.image_url?.trim() || null,
        unit_price: productForm.unit_price !== '' ? Number(productForm.unit_price) : null,
        transaction_mode: productForm.transaction_mode,
        is_published: productForm.is_published,
        store_ids: productForm.store_ids || [],
        metadata: metaUpdate,
        // W1.S5/Phase 2.7 — additive cost composition.
        cost_source: productForm.cost_source || null,
      };
      const res = await productsAPI.update(productId, upd);
      const updatedProd = res.data || upd;
      setProduct(prev => prev ? { ...prev, ...updatedProd } : prev);
      toast.success(t('dashboards.reservation.toasts.updated'));
    } catch (err) {
      toast.error(err?.response?.data?.detail || t('dashboards.common.saveError'));
    } finally {
      setSavingProduct(false);
    }
  };

  const quickTogglePublish = async (next) => {
    const prev = productForm.is_published;
    setProductForm(f => ({ ...f, is_published: next }));
    setProduct(p => p ? { ...p, is_published: next } : p);
    try {
      await productsAPI.update(productId, { is_published: next });
      toast.success(next ? t('dashboards.reservation.toasts.online') : t('dashboards.reservation.toasts.offline'));
    } catch {
      setProductForm(f => ({ ...f, is_published: prev }));
      setProduct(p => p ? { ...p, is_published: prev } : p);
      toast.error(t('dashboards.reservation.toasts.statusError'));
    }
  };

  const handleDuplicate = async () => {
    if (duplicating) return;
    setDuplicating(true);
    try {
      const res = await productsAPI.duplicate(productId);
      toast.success(t('dashboards.reservation.toasts.duplicated'));
      const newId = res.data?.id;
      if (newId) navigate(`/reservations/${newId}`);
    } catch (err) {
      toast.error(err?.response?.data?.detail || t('dashboards.reservation.toasts.duplicateError'));
    } finally {
      setDuplicating(false);
    }
  };

  // Consolidated landing resolution — server resolves the store-scoped URL
  // honoring product.store_ids, visibility, publish state. Replaces the
  // old "pick first published store" client-side heuristic.
  const {
    landingPath: landingUrl,
    landingUrl: landingUrlAbsolute,
    blockers: landingBlockers,
    refresh: refreshLandingInfo,
  } = useLandingUrl(productId);

  // Re-fetch landing info whenever publish state flips so the button updates
  // immediately after quickTogglePublish.
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

  // Availability rules: delete-all + recreate (dataset tiny; mirrors ServiceDashboardPage).
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
      toast.success(t('dashboards.reservation.toasts.availabilityUpdated'));
    } catch {
      toast.error(t('dashboards.reservation.toasts.availabilityError'));
    }
  };

  const saveExtras = async (nextExtras) => {
    try {
      const oldById = new Map(extras.filter(e => e.id).map(e => [e.id, e]));
      // Delete removed
      for (const existing of extras) {
        if (!existing.id) continue;
        const stillThere = nextExtras.find(n => n.id === existing.id);
        if (!stillThere) {
          try { await productExtrasAPI.delete(productId, existing.id); } catch { /* ignore */ }
        }
      }
      const updated = [];
      for (const e of nextExtras) {
        const payload = {
          kind: e.kind,
          group_key: e.group_key || null,
          label: e.label,
          description: e.description || null,
          price: Number(e.price) || 0,
          price_modifier_type: e.price_modifier_type || 'flat',
          duration_minutes_override: e.duration_minutes_override
            ? Number(e.duration_minutes_override) : null,
          is_default: !!e.is_default,
          sort_order: e.sort_order ?? 0,
          is_active: e.is_active !== false,
        };
        if (e.id && oldById.has(e.id)) {
          try {
            const res = await productExtrasAPI.update(productId, e.id, payload);
            updated.push(res.data);
          } catch { updated.push(e); }
        } else {
          try {
            const res = await productExtrasAPI.create(productId, payload);
            updated.push(res.data);
          } catch { /* ignore */ }
        }
      }
      setExtras(updated);
      toast.success(t('dashboards.reservation.toasts.extrasUpdated'));
    } catch {
      toast.error(t('dashboards.reservation.toasts.extrasError'));
    }
  };

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center text-sm text-gray-500">{t('dashboards.common.loading')}</div>;
  }
  if (error === 'not_found') {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-6">
        <div className="max-w-md text-center bg-white rounded-xl border p-8">
          <h1 className="text-2xl font-bold mb-2">{t('dashboards.reservation.notFound')}</h1>
          <button onClick={() => navigate('/products?type=rental')} className="rounded-md bg-gray-900 text-white px-4 py-2 text-sm">
            {t('dashboards.reservation.back')}
          </button>
        </div>
      </div>
    );
  }
  if (error === 'wrong_type') {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-6">
        <div className="max-w-md text-center bg-white rounded-xl border p-8">
          <h1 className="text-2xl font-bold mb-2">{t('dashboards.reservation.invalidType')}</h1>
          <p className="text-gray-600 mb-4">{t('dashboards.reservation.invalidTypeDesc')}</p>
          <button onClick={() => navigate('/products')} className="rounded-md bg-gray-900 text-white px-4 py-2 text-sm">{t('dashboards.common.backToProducts')}</button>
        </div>
      </div>
    );
  }

  const hero = productForm.cover_image_url || productForm.image_url;
  const flavorLabel = t(`dashboards.reservation.flavorLabel.${flavor === 'range' ? 'range' : 'slot'}`);
  const flavorEmoji = flavor === 'range' ? '🔑' : '📅';

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
              <Link to="/products?type=rental" className="inline-flex items-center gap-1 text-sm font-medium text-white/70 hover:text-white transition-colors">{t('dashboards.reservation.back')}</Link>
              <p className="text-[10px] uppercase tracking-widest opacity-70 mt-2">{flavorEmoji} {flavorLabel}</p>
              <h1 className="text-2xl sm:text-3xl font-bold mt-1">{productForm.name || t('dashboards.reservation.fallbackName')}</h1>
              {flavor === 'range' && productForm.rental_unit && (
                <div className="mt-2 text-sm sm:text-base opacity-90">
                  {t('dashboards.reservation.perRentalUnit', { unit: t(`dashboards.reservation.pricing.rentalUnits.${productForm.rental_unit}`, { defaultValue: productForm.rental_unit }) })}
                </div>
              )}
              {flavor === 'slot' && productForm.slot_duration_minutes && (
                <div className="mt-2 text-sm sm:text-base opacity-90">
                  {t('dashboards.reservation.slotDurationDisplay', { minutes: productForm.slot_duration_minutes })}
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

        {/* Stato affitto */}
        <div className="rounded-xl border border-gray-200 bg-white px-5 py-4">
          <div className="flex items-center justify-between gap-3">
            <div className="min-w-0">
              <h2 className="text-sm font-semibold text-gray-900">{t('dashboards.reservation.statusTitle')}</h2>
              <p className="text-xs text-gray-500 mt-0.5">
                {productForm.is_published
                  ? t('dashboards.reservation.statusOnlineDesc')
                  : t('dashboards.reservation.statusOfflineDesc')}
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
            >{t('dashboards.reservation.landingPreview')}</a>
          ) : (
            <div
              className="rounded-xl border border-dashed border-gray-300 bg-gray-50 px-4 py-3 text-sm text-gray-500 text-center"
              title={landingBlockers.length ? landingBlockers.join('\n') : undefined}
            >
              {t('dashboards.reservation.landingUnavailable')}
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
          >{t('dashboards.reservation.landingCopy')}</button>
          <button
            type="button"
            onClick={handleDuplicate}
            disabled={duplicating}
            className="rounded-xl border border-gray-300 bg-white px-4 py-3 text-sm font-semibold text-gray-900 hover:border-gray-900 disabled:opacity-50"
          >{duplicating ? t('dashboards.reservation.duplicateLoading') : t('dashboards.reservation.duplicateBtn')}</button>
        </div>

        {/* Prossime prenotazioni */}
        <div className="rounded-xl border border-gray-200 bg-white overflow-hidden">
          <button
            type="button"
            onClick={() => setReservationsOpen(v => !v)}
            className="w-full flex items-center justify-between px-5 py-3 text-left hover:bg-gray-50"
          >
            <span className="text-sm font-semibold text-gray-900">
              {t('dashboards.reservation.upcoming.title')}
              {upcomingReservations.length > 0 && (
                <span className="ml-2 inline-flex items-center justify-center rounded-full bg-gray-900 text-white text-[10px] font-bold h-5 min-w-[20px] px-1.5">
                  {upcomingReservations.length}
                </span>
              )}
            </span>
            <span className="text-gray-400 text-xs">{reservationsOpen ? '▲' : '▼'}</span>
          </button>
          {reservationsOpen && (
            <div className="border-t border-gray-100 px-5 py-4 space-y-3">
              {reservationsLoading ? (
                <p className="text-sm text-gray-500">{t('dashboards.reservation.upcoming.loading')}</p>
              ) : upcomingReservations.length === 0 ? (
                <div className="rounded-md bg-gray-50 border border-dashed border-gray-200 px-3 py-3 text-sm text-gray-600">
                  {t('dashboards.reservation.upcoming.empty')}
                </div>
              ) : (
                <>
                  <ul className="divide-y divide-gray-100">
                    {upcomingReservations.map((r) => {
                      const when = r.reservation_flavor === 'range'
                        ? `${r.date_from || ''}${r.date_to && r.date_to !== r.date_from ? ` → ${r.date_to}` : ''}`
                        : `${r.slot_date || ''}${r.slot_start_time ? ` · ${r.slot_start_time}` : ''}${r.slot_end_time ? ` → ${r.slot_end_time}` : ''}`;
                      return (
                        <li key={r.id} className="py-2 flex items-center justify-between gap-2">
                          <div className="min-w-0">
                            <p className="text-sm font-mono text-gray-900 truncate">{r.code}</p>
                            <p className="text-xs text-gray-500 truncate">
                              {r.holder_name || '—'}{r.holder_email ? ` · ${r.holder_email}` : ''}
                            </p>
                          </div>
                          <div className="text-right shrink-0">
                            <p className="text-xs text-gray-700">{when || '—'}</p>
                            {r.access_token && (
                              <Link
                                to={`/rsv/${r.access_token}`}
                                target="_blank" rel="noopener noreferrer"
                                className="text-[11px] text-blue-600 hover:underline"
                              >{t('dashboards.reservation.upcoming.openLanding')}</Link>
                            )}
                          </div>
                        </li>
                      );
                    })}
                  </ul>
                  <Link
                    to="/reservations"
                    className="inline-block text-[11px] text-gray-600 hover:text-gray-900 hover:underline"
                  >{t('dashboards.reservation.upcoming.seeAll')}</Link>
                </>
              )}
            </div>
          )}
        </div>

        {/* Identità */}
        <div className="rounded-xl border border-gray-200 bg-white overflow-hidden">
          <button
            type="button"
            onClick={() => setEditProductOpen(v => !v)}
            className="w-full flex items-center justify-between px-5 py-3 text-left hover:bg-gray-50"
          >
            <span className="text-sm font-semibold text-gray-900">{t('dashboards.reservation.identity.title')}</span>
            <span className="text-gray-400 text-xs">{editProductOpen ? '▲' : '▼'}</span>
          </button>
          {editProductOpen && (
            <div className="border-t border-gray-100 px-5 py-4 space-y-3">
              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">{t('dashboards.reservation.identity.nameLabel')}</label>
                <input
                  type="text"
                  value={productForm.name}
                  onChange={(e) => setProductForm(f => ({ ...f, name: e.target.value }))}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">{t('dashboards.reservation.identity.shortDescLabel')}</label>
                <textarea
                  rows={2}
                  value={productForm.description}
                  onChange={(e) => setProductForm(f => ({ ...f, description: e.target.value }))}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none"
                />
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-gray-700 mb-1">{t('dashboards.reservation.identity.imageLabel')}</label>
                  <input
                    type="url"
                    value={productForm.image_url}
                    onChange={(e) => setProductForm(f => ({ ...f, image_url: e.target.value }))}
                    className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-gray-700 mb-1">{t('dashboards.reservation.identity.coverLabel')}</label>
                  <input
                    type="url"
                    value={productForm.cover_image_url}
                    onChange={(e) => setProductForm(f => ({ ...f, cover_image_url: e.target.value }))}
                    className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none"
                  />
                </div>
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">{t('dashboards.reservation.identity.longDescLabel')}</label>
                <textarea
                  rows={5}
                  value={productForm.long_description}
                  onChange={(e) => setProductForm(f => ({ ...f, long_description: e.target.value }))}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none"
                />
              </div>
              <div className="pt-1">
                <button
                  type="button"
                  onClick={saveProduct}
                  disabled={savingProduct}
                  className="rounded-md bg-gray-900 text-white px-4 py-2 text-sm font-semibold hover:bg-gray-800 disabled:opacity-50"
                >{savingProduct ? t('dashboards.common.saving') : t('dashboards.reservation.identity.saveBtn')}</button>
              </div>
            </div>
          )}
        </div>

        {/* Flavor & prezzo */}
        <div className="rounded-xl border border-gray-200 bg-white overflow-hidden">
          <button
            type="button"
            onClick={() => setEditPricingOpen(v => !v)}
            className="w-full flex items-center justify-between px-5 py-3 text-left hover:bg-gray-50"
          >
            <span className="text-sm font-semibold text-gray-900">{t('dashboards.reservation.pricing.title')}</span>
            <span className="text-gray-400 text-xs">{editPricingOpen ? '▲' : '▼'}</span>
          </button>
          {editPricingOpen && (
            <div className="border-t border-gray-100 px-5 py-4 space-y-3">
              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">{t('dashboards.reservation.pricing.flavorTitle')}</label>
                <select
                  value={productForm.reservation_flavor}
                  onChange={(e) => setProductForm(f => ({ ...f, reservation_flavor: e.target.value }))}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm bg-white"
                >
                  <option value="range">{t('dashboards.reservation.pricing.flavorRange')}</option>
                  <option value="slot">{t('dashboards.reservation.pricing.flavorSlot')}</option>
                </select>
                <p className="text-[11px] text-gray-500 mt-1">
                  {productForm.reservation_flavor === 'range'
                    ? t('dashboards.reservation.pricing.flavorRangeDesc')
                    : t('dashboards.reservation.pricing.flavorSlotDesc')}
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-gray-700 mb-1">{flavor === 'range' ? t('dashboards.reservation.pricing.priceLabelRange') : t('dashboards.reservation.pricing.priceLabelSlot')}</label>
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    value={productForm.unit_price}
                    onChange={(e) => setProductForm(f => ({ ...f, unit_price: e.target.value }))}
                    className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none"
                  />
                  <p className="text-[11px] text-gray-500 mt-1">{t('dashboards.reservation.pricing.currentLabel', { value: formatEuro(productForm.unit_price, productForm.currency || orgCurrency, i18n.language) })}</p>
                </div>
                {flavor === 'range' ? (
                  <div>
                    <label className="block text-xs font-semibold text-gray-700 mb-1">{t('dashboards.reservation.pricing.rentalUnitLabel')}</label>
                    <select
                      value={productForm.rental_unit}
                      onChange={(e) => setProductForm(f => ({ ...f, rental_unit: e.target.value }))}
                      className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm bg-white"
                    >
                      <option value="giorno">{t('dashboards.reservation.pricing.rentalUnits.giorno')}</option>
                      <option value="notte">{t('dashboards.reservation.pricing.rentalUnits.notte')}</option>
                      <option value="settimana">{t('dashboards.reservation.pricing.rentalUnits.settimana')}</option>
                      <option value="mese">{t('dashboards.reservation.pricing.rentalUnits.mese')}</option>
                      <option value="ora">{t('dashboards.reservation.pricing.rentalUnits.ora')}</option>
                    </select>
                  </div>
                ) : (
                  <div>
                    <label className="block text-xs font-semibold text-gray-700 mb-1">{t('dashboards.reservation.pricing.slotDurationLabel')}</label>
                    <select
                      value={productForm.slot_duration_minutes}
                      onChange={(e) => setProductForm(f => ({ ...f, slot_duration_minutes: Number(e.target.value) }))}
                      className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm bg-white"
                    >
                      {[15, 30, 45, 60, 90, 120, 180].map(m => (
                        <option key={m} value={m}>{t('dashboards.reservation.pricing.slotDurationOption', { minutes: m })}</option>
                      ))}
                    </select>
                    <p className="text-[11px] text-gray-500 mt-0.5">
                      {t('dashboards.reservation.pricing.slotDurationFallback')}
                    </p>
                  </div>
                )}
              </div>

              {flavor === 'slot' && (
                <div className="rounded-lg border border-gray-200 bg-gray-50 p-3 space-y-3">
                  <div>
                    <div className="text-sm font-semibold text-gray-900">{t('dashboards.reservation.pricing.variableTitle')}</div>
                    <p className="text-[11px] text-gray-500 mt-0.5">
                      {t('dashboards.reservation.pricing.variableDesc', { price: Number(productForm.unit_price) || 0 })}
                    </p>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    <div>
                      <label className="block text-[11px] font-medium text-gray-700 mb-1">{t('dashboards.reservation.pricing.minDurationLabel')}</label>
                      <input
                        type="number" min="5" max="1440" step="5"
                        value={productForm.slot_min_duration_minutes}
                        onChange={(e) => setProductForm(f => ({ ...f, slot_min_duration_minutes: e.target.value }))}
                        placeholder={t('dashboards.reservation.pricing.minDurationPlaceholder')}
                        className="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:border-gray-900 focus:outline-none"
                      />
                    </div>
                    <div>
                      <label className="block text-[11px] font-medium text-gray-700 mb-1">{t('dashboards.reservation.pricing.stepLabel')}</label>
                      <input
                        type="number" min="5" max="120" step="5"
                        value={productForm.slot_step_minutes}
                        onChange={(e) => setProductForm(f => ({ ...f, slot_step_minutes: e.target.value }))}
                        placeholder={t('dashboards.reservation.pricing.stepPlaceholder')}
                        className="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:border-gray-900 focus:outline-none"
                      />
                    </div>
                    <div>
                      <label className="block text-[11px] font-medium text-gray-700 mb-1">{t('dashboards.reservation.pricing.maxDurationLabel')}</label>
                      <input
                        type="number" min="5" max="43200" step="5"
                        value={productForm.slot_max_duration_minutes}
                        onChange={(e) => setProductForm(f => ({ ...f, slot_max_duration_minutes: e.target.value }))}
                        placeholder={t('dashboards.reservation.pricing.maxDurationPlaceholder')}
                        className="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:border-gray-900 focus:outline-none"
                      />
                    </div>
                  </div>
                </div>
              )}

              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">{t('dashboards.reservation.pricing.modeLabel')}</label>
                <select
                  value={productForm.transaction_mode}
                  onChange={(e) => setProductForm(f => ({ ...f, transaction_mode: e.target.value }))}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm bg-white"
                >
                  <option value="request">{t('dashboards.reservation.pricing.modeRequest')}</option>
                  <option value="direct">{t('dashboards.reservation.pricing.modeDirect')}</option>
                  <option value="approval">{t('dashboards.reservation.pricing.modeApproval')}</option>
                </select>
              </div>

              {/* W1.S5/Phase 2.7 — Cost composition (edit). */}
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

              <div className="pt-1">
                <button
                  type="button"
                  onClick={saveProduct}
                  disabled={savingProduct}
                  className="rounded-md bg-gray-900 text-white px-4 py-2 text-sm font-semibold hover:bg-gray-800 disabled:opacity-50"
                >{savingProduct ? t('dashboards.common.saving') : t('dashboards.reservation.pricing.saveBtn')}</button>
              </div>
            </div>
          )}
        </div>

        {/* Availability — slot flavor only */}
        {flavor === 'slot' && (
          <div className="rounded-xl border border-gray-200 bg-white overflow-hidden">
            <button
              type="button"
              onClick={() => setEditAvailabilityOpen(v => !v)}
              className="w-full flex items-center justify-between px-5 py-3 text-left hover:bg-gray-50"
            >
              <span className="text-sm font-semibold text-gray-900">{t('dashboards.reservation.availability.title')}</span>
              <span className="text-gray-400 text-xs">{editAvailabilityOpen ? '▲' : '▼'}</span>
            </button>
            {editAvailabilityOpen && (
              <div className="border-t border-gray-100 px-5 py-4">
                <AvailabilityRulesEditor
                  rules={rules}
                  onChange={saveRules}
                  defaultSlotDurationMinutes={Number(productForm.slot_duration_minutes) || 60}
                />
              </div>
            )}
          </div>
        )}

        {/* Extras */}
        <div className="rounded-xl border border-gray-200 bg-white overflow-hidden">
          <button
            type="button"
            onClick={() => setEditExtrasOpen(v => !v)}
            className="w-full flex items-center justify-between px-5 py-3 text-left hover:bg-gray-50"
          >
            <span className="text-sm font-semibold text-gray-900">
              {t('dashboards.reservation.extras.title')}
              {extras.length > 0 && (
                <span className="ml-2 inline-flex items-center justify-center rounded-full bg-gray-900 text-white text-[10px] font-bold h-5 min-w-[20px] px-1.5">
                  {extras.length}
                </span>
              )}
            </span>
            <span className="text-gray-400 text-xs">{editExtrasOpen ? '▲' : '▼'}</span>
          </button>
          {editExtrasOpen && (
            <div className="border-t border-gray-100 px-5 py-4 space-y-3">
              {/* Local state edits only — API save is explicit via the button below.
                  This avoids creating duplicate rows on every keystroke when a new
                  extra has no backend id yet. */}
              <ProductExtrasEditor
                extras={extras}
                onChange={setExtras}
                productItemType="rental"
              />
              <div className="pt-1">
                <button
                  type="button"
                  onClick={() => saveExtras(extras)}
                  className="rounded-md bg-gray-900 text-white px-4 py-2 text-sm font-semibold hover:bg-gray-800"
                >{t('dashboards.reservation.extras.saveBtn')}</button>
                <span className="ml-3 text-[11px] text-gray-500">
                  {t('dashboards.reservation.extras.unsavedHint')}
                </span>
              </div>
            </div>
          )}
        </div>

        {/* T&C + order_fields */}
        <div className="rounded-xl border border-gray-200 bg-white overflow-hidden">
          <button
            type="button"
            onClick={() => setEditTermsOpen(v => !v)}
            className="w-full flex items-center justify-between px-5 py-3 text-left hover:bg-gray-50"
          >
            <span className="text-sm font-semibold text-gray-900">{t('dashboards.reservation.terms.title')}</span>
            <span className="text-gray-400 text-xs">{editTermsOpen ? '▲' : '▼'}</span>
          </button>
          {editTermsOpen && (
            <div className="border-t border-gray-100 px-5 py-4 space-y-3">
              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">{t('dashboards.reservation.terms.termsLabel')}</label>
                <textarea
                  rows={4}
                  value={productForm.terms_content}
                  onChange={(e) => setProductForm(f => ({ ...f, terms_content: e.target.value }))}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none"
                  placeholder={t('dashboards.reservation.terms.termsHint')}
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">{t('dashboards.reservation.terms.orderFieldsLabel')}</label>
                <FieldEditorList
                  fields={productForm.order_fields}
                  onChange={(next) => setProductForm(f => ({ ...f, order_fields: next }))}
                />
              </div>
              <div className="pt-1">
                <button
                  type="button"
                  onClick={saveProduct}
                  disabled={savingProduct}
                  className="rounded-md bg-gray-900 text-white px-4 py-2 text-sm font-semibold hover:bg-gray-800 disabled:opacity-50"
                >{savingProduct ? t('dashboards.common.saving') : t('dashboards.reservation.terms.saveBtn')}</button>
              </div>
            </div>
          )}
        </div>

        {/* Distribution */}
        <div className="rounded-xl border border-gray-200 bg-white overflow-hidden">
          <button
            type="button"
            onClick={() => setEditDistributionOpen(v => !v)}
            className="w-full flex items-center justify-between px-5 py-3 text-left hover:bg-gray-50"
          >
            <span className="text-sm font-semibold text-gray-900">
              {t('dashboards.reservation.distribution.title')}
              {productForm.store_ids?.length > 0 && (
                <span className="ml-2 inline-flex items-center justify-center rounded-full bg-gray-900 text-white text-[10px] font-bold h-5 min-w-[20px] px-1.5">
                  {productForm.store_ids.length}
                </span>
              )}
            </span>
            <span className="text-gray-400 text-xs">{editDistributionOpen ? '▲' : '▼'}</span>
          </button>
          {editDistributionOpen && (
            <div className="border-t border-gray-100 px-5 py-4 space-y-2">
              {stores.length === 0 ? (
                <p className="text-sm text-gray-500">{t('dashboards.reservation.distribution.noStores')}</p>
              ) : stores.length === 1 ? (
                <div className="rounded-md bg-gray-50 border border-gray-200 px-3 py-2 text-sm text-gray-700 flex items-center gap-2">
                  <span aria-hidden>✓</span>
                  <span>
                    {t('dashboards.common.distributionVisibleAutoPrefix')} <strong>{stores[0]?.name || t('dashboards.common.distributionAllStoresFallback')}</strong>
                  </span>
                </div>
              ) : (
                <>
                  <p className="text-xs text-gray-500">{t('dashboards.reservation.distribution.multiDesc')}</p>
                  <label className="flex items-center gap-2 text-sm cursor-pointer">
                    <input
                      type="checkbox"
                      checked={!(productForm.store_ids?.length)}
                      onChange={() => setProductForm(f => ({ ...f, store_ids: [] }))}
                      className="rounded border-gray-300"
                    />
                    <span className={!(productForm.store_ids?.length) ? 'font-medium' : 'text-gray-500'}>
                      {t('dashboards.common.distributionAllStoresLabel')}
                    </span>
                  </label>
                  {stores.map((s) => {
                    const hasAny = (productForm.store_ids || []).length > 0;
                    const checked = hasAny && (productForm.store_ids || []).includes(s.id);
                    return (
                      <label key={s.id} className="flex items-center gap-2 text-sm cursor-pointer">
                        <input
                          type="checkbox"
                          checked={checked}
                          onChange={() => {
                            const current = productForm.store_ids || [];
                            const next = current.includes(s.id)
                              ? current.filter(x => x !== s.id)
                              : [...current, s.id];
                            setProductForm(f => ({ ...f, store_ids: next }));
                          }}
                          className="rounded border-gray-300"
                        />
                        <span>{s.name}</span>
                        {s.is_published && (
                          <span className="text-[10px] text-green-800 bg-green-100 rounded-full px-1.5 py-0.5">{t('dashboards.common.statusOnline')}</span>
                        )}
                      </label>
                    );
                  })}
                </>
              )}
              <div className="pt-2">
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
