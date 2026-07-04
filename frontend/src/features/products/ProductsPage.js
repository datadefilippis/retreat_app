import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { useSearchParams, useNavigate, Link } from 'react-router-dom';
import { AppLayout, Header } from '../../components/Layout';
import { PageSubheader } from '../../components/PageSubheader';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { useCurrency } from '../../context/AuthContext';
import { useEntitlements } from '../../hooks/useEntitlements';
import { formatCurrency as fmtCurrency } from '../../lib/utils';
// PR-4 cleanup: Dialog primitives now only serve the TypePicker; the
// legacy create/edit Dialog (with its CostSourceEditor / Textarea /
// StripeRequiredAlert / DialogFooter dependencies) is gone.
import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
} from '../../components/ui/dialog';
import {
  Package, Plus, Trash2, Search, Loader2, Info, RefreshCw,
} from 'lucide-react';
import { productsAPI } from '../../api';
import { storesAPI } from '../../api/stores';
import { useAuth } from '../../context/AuthContext';
import { toast } from 'sonner';
import { getProductIssues } from '../../constants/itemTypes';
import EventsGrid from '../events/components/EventsGrid';
// Per-type dashboard dispatch (PR-3).  ProductCard's "Modifica" button
// no longer calls back into a local Dialog; it navigates to the type's
// dedicated route resolved via productDashboardPath() — adding a new
// product type means a single case in utils/productPaths.js, not a new
// branch here.
import { productDashboardPath } from '../../utils/productPaths';
import ServicesGrid from '../services/components/ServicesGrid';
import ReservationsGrid from '../reservations/components/ReservationsGrid';
import PhysicalsGrid from '../physicals/components/PhysicalsGrid';
import DigitalsGrid from '../digitals/components/DigitalsGrid';
// Release 4 (Courses) — embedded grid for item_type=course products
import CoursesGrid from '../courses/components/CoursesGrid';
// Release 4 (Courses) — modal Bunny config gate before creating the
// first course (TypePicker entry) so the admin doesn't reach
// /courses/new without the integration set up.
import BunnyManagerDialog from '../courses/bunny-manager/BunnyManagerDialog';
import { organizationsAPI } from '../../api/organizations';

// Note: OccurrenceEditorPanel (features/events/components) is no longer
// imported here — the legacy Dialog that mounted it was removed in PR-4.
// The component file is intentionally kept; a future "manage occurrences
// for an event product" surface (e.g. a dedicated route) can re-mount it
// with the same controlled-component contract. See PRODUCTS_ARCHITECTURE
// Phase 4 for the rationale.

// TYPE_CFG holds non-localized presentation only (icon + gradient). Labels
// are resolved via t('products.typeLabels.<key>') so translations stay in
// the JSON catalog. The `_labelKey` field documents the i18n key used.
const TYPE_CFG = {
  physical:     { icon: '📦', _labelKey: 'physical',     gradient: 'from-gray-700 to-gray-500' },
  service:      { icon: '🛠', _labelKey: 'service',      gradient: 'from-blue-700 to-blue-500' },
  rental:       { icon: '🔑', _labelKey: 'rental',       gradient: 'from-amber-700 to-amber-500' },
  booking:      { icon: '📅', _labelKey: 'booking',      gradient: 'from-purple-700 to-purple-500' },
  digital:      { icon: '💾', _labelKey: 'digital',      gradient: 'from-teal-700 to-teal-500' },
  event_ticket: { icon: '🎫', _labelKey: 'event_ticket', gradient: 'from-rose-700 to-rose-500' },
};

// Resolve the per-type dashboard URL the "Modifica" button on each
// ProductCard should navigate to. The two edge cases (event_ticket and
// course) are handled inline because they don't key off product_id:
//
//   - event_ticket: lives in N occurrences; without an occurrence_id we
//     can't dispatch, so we land on the type-filtered hub view (NOT the
//     deprecated ?product_id=... deep-link).
//
//   - course: keyed by metadata.course_id (separate doc). The product
//     itself carries that id in metadata, so we read it directly with
//     zero extra API calls — different from ProductProfileSlide which
//     has to do a lazy fetch because its summary lacks metadata.
//
// All other types go through productDashboardPath() so adding a new
// type is a one-line change there.
function productCardDashboardHref(product) {
  if (product?.item_type === 'event_ticket') {
    return '/products?type=event_ticket';
  }
  if (product?.item_type === 'course') {
    const courseId = product?.metadata?.course_id;
    return courseId ? `/courses/${courseId}` : '/courses';
  }
  return productDashboardPath({
    itemType: product?.item_type,
    productId: product?.id,
  }) || '/products';
}


function ProductCard({ product, onTogglePublish, onDeactivate }) {
  // CH compliance v1: prefer the product's snapshot currency, fall back
  // to the org's currency. Without this, every admin card on a CHF org
  // would still print "€" next to the price.
  const orgCurrency = useCurrency();
  const { t } = useTranslation('products');
  const cfg = TYPE_CFG[product.item_type] || TYPE_CFG.physical;
  const cfgLabel = t(`typeLabels.${cfg._labelKey}`);
  const issues = getProductIssues(product);
  const hasError = issues.some(i => i.severity === 'error');
  const fmtPrice = (v) => v != null
    ? fmtCurrency(parseFloat(v), product?.currency || orgCurrency)
    : null;
  // PR-3: dashboard href resolved once per render; the "Modifica" button
  // below is now a plain Link for every product type, no callback dance.
  const dashboardHref = productCardDashboardHref(product);

  return (
    <div className="rounded-xl border border-gray-200 bg-white shadow-sm overflow-hidden flex flex-col">
      {/* Hero — same aspect and gradient as EventCard */}
      <div className={`relative aspect-[16/9] bg-gradient-to-br ${cfg.gradient} overflow-hidden`}>
        {product.image_url ? (
          <img src={product.image_url} alt="" className="w-full h-full object-cover hover:scale-[1.02] transition-transform duration-200" />
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <span className="text-5xl opacity-50">{cfg.icon}</span>
          </div>
        )}

        {/* Online/Offline — top-left, clickable, same position as EventCard StatusChip */}
        <div className="absolute top-2 left-2 flex gap-1">
          <button
            type="button"
            onClick={(e) => { e.stopPropagation(); onTogglePublish(product); }}
            className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-semibold transition-all hover:opacity-80 active:scale-95 ${
              product.is_published
                ? 'bg-green-100 text-green-900'
                : 'bg-gray-100 text-gray-700'
            }`}
            title={product.is_published ? t('status.clickToOffline') : t('status.clickToOnline')}
          >
            {product.is_published ? t('status.online') : t('status.offline')}
          </button>
        </div>

        {/* Issues dot — bottom right */}
        {issues.length > 0 && (
          <span className={`absolute bottom-2 right-2 w-2.5 h-2.5 rounded-full ${hasError ? 'bg-red-500' : 'bg-amber-400'}`}
            title={issues.map(i => i.key).join(', ')} />
        )}
      </div>

      {/* Body — same padding and structure as EventCard */}
      <div className="p-4 flex-1 flex flex-col gap-2">
        <div>
          <p className="text-[11px] uppercase tracking-wide text-gray-500 font-semibold">
            {cfg.icon} {cfgLabel}
            {fmtPrice(product.unit_price) && <span className="ml-1 normal-case">· {fmtPrice(product.unit_price)}</span>}
          </p>
          <h3 className="font-bold text-gray-900 line-clamp-2 mt-0.5">{product.name}</h3>
          {product.category && (
            <p className="text-xs text-gray-600 mt-1 line-clamp-1">🏷 {product.category}</p>
          )}
          {product.description && !product.category && (
            <p className="text-xs text-gray-600 mt-1 line-clamp-1">{product.description}</p>
          )}
        </div>

        {/* Footer — same button layout as EventCard.
            PR-3: every type now navigates to its per-type dashboard
            via productCardDashboardHref(). The previous split (service
            on Link, others on button → legacy Dialog) is gone now that
            the 6 typed dashboards exist and event/course have explicit
            edge-case handling. Label kept as 'list.dashboardLink' for
            consistency with the legacy service branch. */}
        <div className="flex gap-2 mt-auto pt-2">
          <Link
            to={dashboardHref}
            className="flex-1 text-center text-xs font-semibold rounded-md bg-gray-900 text-white px-2 py-1.5 hover:bg-gray-800"
          >{t('list.dashboardLink')}</Link>
          {product.is_active !== false && (
            <button
              onClick={() => onDeactivate(product)}
              className="text-center text-xs font-semibold rounded-md border border-gray-300 text-gray-900 px-2 py-1.5 hover:border-gray-900"
              title={t('list.deactivateTitle')}
            ><Trash2 className="h-3.5 w-3.5" /></button>
          )}
        </div>
      </div>
    </div>
  );
}

export default function ProductsPage() {
  const { t } = useTranslation(['entities', 'catalog', 'products']);
  // Consolidamento WS-3 — il type-picker segue il piano: niente noleggi
  // nel verticale ritiri (riappaiono se il piano riabilita rentals).
  const { canUse } = useEntitlements();
  const { user } = useAuth();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  // PR-4: removed Dialog-only state (dialogOpen, editing, form, saving,
  // aiEnriching, showAdvanced, occurrences). The page is now a pure
  // hub: grid + filters + TypePicker + per-type embedded grids; all
  // create/edit lives in dedicated wizard/dashboard routes.

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [prodRes, storeRes] = await Promise.all([
        productsAPI.list(false),
        storesAPI.list().catch(() => ({ data: { stores: [] } })),
      ]);
      setItems(prodRes.data || []);
      setStores(storeRes.data?.stores || []);
    } catch { /* empty */ } finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  // Legacy deep-link compatibility — ``/products?product_id=<UUID>``.
  //
  // History: before the per-type dashboards existed, every product-edit
  // surface (calendar drill, email, AI tool suggestion, …) linked to
  // this URL and the page auto-opened the generic edit Dialog.
  //
  // PR-3 swap: the URL still works (no broken bookmarks / emails), but
  // instead of opening the deprecated Dialog we redirect to the right
  // per-type dashboard via productDashboardPath().  The query param is
  // stripped from the URL so a back-button doesn't re-trigger the
  // navigate loop.
  //
  // Telemetry: the console.warn flags the caller so we can hunt down
  // and update any remaining producer (calendar already uses the new
  // path map — see utils/productPaths.js — but there may be other
  // surfaces we haven't audited yet).  Safe to remove once the warning
  // has been silent for a full release cycle in production.
  useEffect(() => {
    const pid = searchParams.get('product_id');
    if (!pid || loading || items.length === 0) return;
    const product = items.find(p => p.id === pid);
    // eslint-disable-next-line no-console
    console.warn('[legacy] ProductsPage ?product_id deep-link', {
      productId: pid,
      itemType: product?.item_type,
      referrer: typeof document !== 'undefined' ? document.referrer : null,
    });
    searchParams.delete('product_id');
    setSearchParams(searchParams, { replace: true });
    if (!product) return;
    // Same dispatch the ProductCard uses (handles event_ticket + course
    // edge cases) — exact one-line policy for "where does this product
    // belong now?".
    const href = productCardDashboardHref(product);
    if (href && href !== '/products') {
      navigate(href, { replace: true });
    }
  }, [loading, items, searchParams, setSearchParams, navigate]);

  const [stores, setStores] = useState([]);
  const [storeFilter, setStoreFilter] = useState('all'); // 'all' | store_id
  const [filterSetup, setFilterSetup] = useState('all'); // 'all' | 'issues' | 'storefront_errors'
  const [triageContext, setTriageContext] = useState(null); // 'storefront_errors' | null
  // Onda 7 M1.d — TypePicker modal state
  const [typePickerOpen, setTypePickerOpen] = useState(false);

  // Release 4 (Courses) — Bunny config gate. Triggered when the admin
  // clicks "🎓 Corso video" in the TypePicker but the org doesn't have
  // Bunny credentials yet. We show the BunnyConfigDialog inline; on
  // save we resume the original navigation to /courses/new. The gate
  // is non-blocking — admin can also dismiss the dialog and proceed
  // anyway (creating a course without Bunny works, the videos just
  // aren't playable until config is added later).
  const [bunnyDialogOpen, setBunnyDialogOpen] = useState(false);
  const [pendingNav, setPendingNav] = useState(null);
  // Step 5 of bunny consolidation: gate on the REAL verification
  // status, not the "fields are filled in" heuristic. The previous
  // logic let the admin pass through with bad credentials, leading
  // to a broken create-course flow when the URL minting failed
  // downstream. Now: only `last_verification_status === 'ok'` lets
  // the navigation proceed; anything else opens the dialog so the
  // admin sees the honest red/amber badge and can fix it immediately.
  const checkBunnyAndProceed = async (destination) => {
    try {
      const { data } = await organizationsAPI.getCurrent();
      const b = data?.integrations?.bunny;
      const isOk = b?.last_verification_status === 'ok';
      if (isOk) {
        navigate(destination);
        return;
      }
    } catch {
      // Network failure → just proceed; admin can configure later.
    }
    // Not configured / errored → gate the navigation behind the dialog.
    setPendingNav(destination);
    setBunnyDialogOpen(true);
  };

  // Onda 7 M1 — type filter chip bar. Reads/syncs with ?type= URL param
  // so navigation from the sidebar "Eventi" shortcut (→ /products?
  // type=event_ticket) preselects the filter + swaps to the events
  // view. Valid values: '' (all), 'physical', 'service', 'rental',
  // 'booking', 'event_ticket'.
  const [typeFilter, setTypeFilter] = useState(searchParams.get('type') || 'physical');

  // Keep URL in sync with typeFilter so the browser back button works
  // and the filter state survives a reload.
  useEffect(() => {
    const current = searchParams.get('type') || '';
    if (typeFilter && typeFilter !== current) {
      searchParams.set('type', typeFilter);
      setSearchParams(searchParams, { replace: true });
    } else if (!typeFilter && current) {
      searchParams.delete('type');
      setSearchParams(searchParams, { replace: true });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [typeFilter]);

  // Handle URL params: ?triage=storefront_errors, ?store_id=xxx
  useEffect(() => {
    if (loading) return;
    let changed = false;
    const triageParam = searchParams.get('triage');
    if (triageParam) {
      if (triageParam === 'storefront_errors') {
        setFilterSetup('storefront_errors');
        setTriageContext('storefront_errors');
      }
      searchParams.delete('triage');
      changed = true;
    }
    const storeIdParam = searchParams.get('store_id');
    if (storeIdParam) {
      setStoreFilter(storeIdParam);
      searchParams.delete('store_id');
      changed = true;
    }
    if (changed) setSearchParams(searchParams, { replace: true });
  }, [loading, searchParams, setSearchParams]);


  const filtered = useMemo(() => {
    let list = items;
    // event_ticket products are managed exclusively through EventsGrid ("🎫 Eventi" tab).
    // Hide them from all other views to avoid showing two different UIs for the same item.
    if (typeFilter !== 'event_ticket') {
      list = list.filter(p => p.item_type !== 'event_ticket');
    }
    // Onda 13 — same rule for services: ServicesGrid is the only UI for
    // item_type=service; exclude them elsewhere to avoid visual duplication.
    if (typeFilter !== 'service') {
      list = list.filter(p => p.item_type !== 'service');
    }
    // Consolidamento UI — rental (and legacy booking) are managed by ReservationsGrid.
    // Hide them from all other views for the same reason.
    if (typeFilter !== 'rental') {
      list = list.filter(p => p.item_type !== 'rental' && p.item_type !== 'booking');
    }
    // Release 3 (Digital) — DigitalsGrid is the only UI for item_type=digital;
    // exclude from the generic table so digitals don't double-render.
    if (typeFilter !== 'digital') {
      list = list.filter(p => p.item_type !== 'digital');
    }
    // Release 4 (Courses) — CoursesGrid is the only UI for item_type=course;
    // exclude from the generic table so courses don't double-render.
    if (typeFilter !== 'course') {
      list = list.filter(p => p.item_type !== 'course');
    }
    // Type chip filter — event_ticket, service, rental, digital, course handled separately by their grids
    if (typeFilter && typeFilter !== 'event_ticket' && typeFilter !== 'service' && typeFilter !== 'rental' && typeFilter !== 'digital' && typeFilter !== 'course') {
      list = list.filter(p => p.item_type === typeFilter);
    }
    // Store filter
    if (storeFilter !== 'all') {
      list = list.filter(p => !p.store_ids?.length || p.store_ids.includes(storeFilter));
    }
    if (search.trim()) {
      const q = search.toLowerCase();
      list = list.filter(p => p.name?.toLowerCase().includes(q) || p.sku?.toLowerCase().includes(q));
    }
    if (filterSetup === 'issues') {
      list = list.filter(p => getProductIssues(p).length > 0);
    } else if (filterSetup === 'storefront_errors') {
      list = list.filter(p => p.is_published && getProductIssues(p).some(i => i.severity === 'error'));
    }
    return list;
  }, [items, search, filterSetup, storeFilter, typeFilter]);

  // PR-4: legacy openCreate / openEdit / handleSave handlers removed
  // together with the Dialog JSX they served. Every entry point now
  // routes to a per-type wizard (creation) or dashboard (edit). The
  // validationErrors / hasAdvancedErrors helpers + the auto-expand
  // useEffect that depended on them were removed as part of the same
  // cleanup — they were only meaningful inside the Dialog's form.

  // ── Inline card actions ────────────────────────────────────────────────
  // These are bound to ProductCard via props (onTogglePublish,
  // onDeactivate). They survive PR-4 because the cards stay on the hub
  // page; only the legacy Dialog is gone.

  const handleTogglePublish = async (item) => {
    try {
      await productsAPI.update(item.id, { is_published: !item.is_published });
      setItems(prev => prev.map(p => p.id === item.id ? { ...p, is_published: !p.is_published } : p));
    } catch {
      toast.error(t('products.save_error'));
    }
  };

  const handleDeactivate = async (item) => {
    if (!window.confirm(t('products.deactivate_confirm'))) return;
    try {
      await productsAPI.deactivate(item.id);
      toast.success(t('products.delete_success'));
      load();
    } catch {
      toast.error(t('products.delete_error'));
    }
  };

  const fmtPrice = (v) => v != null ? `${parseFloat(v).toFixed(2)}` : '-';

  return (
    <AppLayout>
      <Header title={t('products.title')} subtitle={t('products.subtitle')} />
      <PageSubheader
        actions={
          <>
            <Button
              variant="outline"
              size="sm"
              onClick={load}
              className="gap-1 shrink-0"
              aria-label={t('products.refresh', { defaultValue: 'Refresh' })}
            >
              <RefreshCw className="h-4 w-4" />
            </Button>
            <Button size="sm" onClick={() => setTypePickerOpen(true)} className="gap-1.5">
              <Plus className="h-4 w-4" /> {t('products.add')}
            </Button>
          </>
        }
      />

      <div className="p-4 md:p-6 space-y-4 max-w-7xl mx-auto">
        {/* Guide text */}
        <div className="flex items-start gap-3 rounded-lg border border-blue-200 bg-blue-50/50 p-3 text-sm text-blue-800">
          <Info className="h-4 w-4 mt-0.5 flex-shrink-0" />
          <p>{t('products.guide')}</p>
        </div>

        {/* Onda 7 M1 — Type filter chips (horizontal). Clicking Eventi
            swaps the default table for the embedded EventsGrid so the
            merchant manages both worlds from the same page. */}
        <div className="flex flex-wrap items-center gap-2">
          {[
            // Order matters: physical first (default), then event_ticket,
            // service, rental (covers both range and slot post Onda 16
            // Fase 6 migration), digital (Release 3), course (Release 4
            // — redirects to /courses for the dedicated admin area).
            'physical',
            'event_ticket',
            'service',
            'rental',
            'digital',
            'course',
          ].map(chipKey => (
            <button
              key={chipKey || 'all'}
              type="button"
              onClick={() => setTypeFilter(chipKey)}
              className={`rounded-full px-3 py-1 text-xs font-semibold transition ${
                typeFilter === chipKey
                  ? 'bg-gray-900 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >{t(`products:list.typeFilter.${chipKey}`)}</button>
          ))}
        </div>

        {typeFilter !== 'event_ticket' && typeFilter !== 'service' && typeFilter !== 'rental' && typeFilter !== 'digital' && typeFilter !== 'course' && (
          <div className="flex items-center gap-3 flex-wrap">
            <div className="relative max-w-sm flex-1 min-w-[200px]">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input placeholder={t('products.search')} value={search} onChange={e => setSearch(e.target.value)} className="pl-9" />
            </div>
            {stores.length > 1 && (
              <select
                value={storeFilter}
                onChange={e => setStoreFilter(e.target.value)}
                className="rounded-md border border-input bg-background px-3 py-2 text-sm min-w-[160px]"
              >
                <option value="all">{t('catalog:form.all_stores')}</option>
                {stores.map(s => (
                  <option key={s.id} value={s.id}>{s.name}</option>
                ))}
              </select>
            )}
          </div>
        )}

        {typeFilter === 'event_ticket' ? (
          <EventsGrid embedded onCreateClick={() => navigate('/events/new')} />
        ) : typeFilter === 'service' ? (
          <ServicesGrid embedded onCreateClick={() => navigate('/services/new')} />
        ) : typeFilter === 'rental' ? (
          <ReservationsGrid embedded onCreateClick={() => navigate('/reservations/new')} />
        ) : typeFilter === 'physical' ? (
          <PhysicalsGrid embedded onCreateClick={() => navigate('/physicals/new')} />
        ) : typeFilter === 'digital' ? (
          <DigitalsGrid embedded onCreateClick={() => navigate('/digitals/new')} />
        ) : typeFilter === 'course' ? (
          <CoursesGrid embedded onCreateClick={() => navigate('/courses/new')} />
        ) : loading ? (
          <div className="flex justify-center py-16"><Loader2 className="h-6 w-6 animate-spin text-muted-foreground" /></div>
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <Package className="h-12 w-12 text-muted-foreground/40 mb-3" />
            <h3 className="font-semibold">{t('products.empty')}</h3>
            <p className="text-sm text-muted-foreground mt-1 max-w-md">{t('products.empty_desc')}</p>
            {/* PR-3: empty state CTA now opens the TypePicker (same as the
                header + button); the legacy ``openCreate`` path is dead. */}
            <Button className="mt-4" onClick={() => setTypePickerOpen(true)}><Plus className="h-4 w-4 mr-2" />{t('products.add')}</Button>
          </div>
        ) : (
          <div className="space-y-3">
            {/* Triage context banner */}
            {triageContext && (
              <div className="flex items-center justify-between rounded-lg border px-3 py-2 text-xs bg-primary/5 border-primary/20">
                <span className="text-primary font-medium">
                  {triageContext === 'storefront_errors' && t('triage.banner_storefront_errors', 'Prodotti pubblicati con errori')}
                </span>
                <button
                  onClick={() => { setTriageContext(null); setFilterSetup('all'); }}
                  className="text-muted-foreground hover:text-foreground ml-2"
                >
                  &times;
                </button>
              </div>
            )}

            {/* Catalog summary strip */}
            {(() => {
              const published = filtered.filter(p => p.is_published).length;
              // Count from full items list (not filtered) for accurate totals
              const totalIssues = items.filter(p => getProductIssues(p).length > 0).length;
              const storefrontErrors = items.filter(p => p.is_published && getProductIssues(p).some(i => i.severity === 'error')).length;
              return (
                <div className="flex items-center gap-3 text-xs flex-wrap">
                  <button onClick={() => setFilterSetup('all')}
                    className={`transition-colors ${filterSetup === 'all' ? 'font-medium text-foreground' : 'text-muted-foreground hover:text-foreground'}`}>
                    {t('products:list.productsCount', { count: items.length })}
                  </button>
                  <span className="text-muted-foreground">·</span>
                  <span className={published > 0 ? 'text-blue-600' : 'text-muted-foreground'}>{t('products:list.publishedCount', { count: published })}</span>
                  {totalIssues > 0 && (
                    <>
                      <span className="text-muted-foreground">·</span>
                      <button onClick={() => setFilterSetup(filterSetup === 'issues' ? 'all' : 'issues')}
                        className={`flex items-center gap-1 transition-colors ${
                          filterSetup === 'issues' ? 'font-medium text-amber-700' : 'text-amber-600 hover:text-amber-700'
                        }`}>
                        <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
                        {totalIssues} {t('summary.needs_setup', 'da completare')}
                      </button>
                    </>
                  )}
                  {storefrontErrors > 0 && (
                    <>
                      <span className="text-muted-foreground">·</span>
                      <button onClick={() => setFilterSetup(filterSetup === 'storefront_errors' ? 'all' : 'storefront_errors')}
                        className={`flex items-center gap-1 transition-colors ${
                          filterSetup === 'storefront_errors' ? 'font-medium text-red-700' : 'text-red-600 hover:text-red-700'
                        }`}>
                        <span className="w-1.5 h-1.5 rounded-full bg-red-500" />
                        {storefrontErrors} {t('summary.storefront_errors', 'problemi storefront')}
                      </button>
                    </>
                  )}
                  {filterSetup !== 'all' && (
                    <span className="text-muted-foreground">— {filtered.length} visibil{filtered.length === 1 ? 'e' : 'i'}</span>
                  )}
                </div>
              );
            })()}

          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3">
            {filtered.map(p => (
              <ProductCard
                key={p.id}
                product={p}
                onTogglePublish={handleTogglePublish}
                onDeactivate={handleDeactivate}
              />
            ))}
          </div>
          </div>
        )}
      </div>

      {/* M1.d — TypePicker: shown when clicking "+ Nuovo prodotto".
          event_ticket navigates to the full EventWizard; other types
          pre-fill the inline Create dialog with the selected item_type. */}
      <Dialog open={typePickerOpen} onOpenChange={setTypePickerOpen}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>{t('products:typePicker.title')}</DialogTitle>
          </DialogHeader>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 py-2">
            {[
              // Consolidamento WS-3 (retreat) — ordine per rilevanza nel
              // verticale: il ritiro per primo, poi servizi/prodotti/
              // digitale/corsi. I due flavor rental (Onda 16: range+slot,
              // wizard unificato) compaiono SOLO se il piano abilita i
              // noleggi — gating via canUse, coerente col menu (WS-2):
              // nessuna rimozione hardcoded, tutto reversibile dal piano.
              { k: 'event_ticket', icon: '🧘' },
              { k: 'service',      icon: '🛠' },
              { k: 'physical',     icon: '📦' },
              { k: 'digital',      icon: '💾' },
              { k: 'course',       icon: '🎓' },
              ...(canUse('commerce', 'rentals')
                ? [{ k: 'rental_range', icon: '🏠' },
                   { k: 'rental_slot',  icon: '📅' }]
                : []),
            ].map(({ k, icon }) => (
              <button
                key={k}
                type="button"
                onClick={() => {
                  setTypePickerOpen(false);
                  if (k === 'event_ticket') {
                    navigate('/events/new');
                  } else if (k === 'service') {
                    // F5 Onda 12 — dedicated guided wizard for services
                    navigate('/services/new');
                  } else if (k === 'rental_range') {
                    navigate('/reservations/new?flavor=range');
                  } else if (k === 'rental_slot') {
                    navigate('/reservations/new?flavor=slot');
                  } else if (k === 'physical') {
                    // Release 2 (Physical) — dedicated wizard aligned with the
                    // pattern used by rental/service/event.
                    navigate('/physicals/new');
                  } else if (k === 'digital') {
                    // Release 3 (Digital) — dedicated wizard with secure file upload.
                    navigate('/digitals/new');
                  } else if (k === 'course') {
                    // Release 4 (Courses) — gate the navigation behind a
                    // Bunny config check. If the org already has the
                    // integration set up → straight to /courses/new.
                    // If not → BunnyConfigDialog opens first; after the
                    // admin saves (or dismisses) we resume the navigation.
                    checkBunnyAndProceed('/courses/new');
                  } else {
                    // PR-3: all 7 declared types above have an explicit
                    // navigate branch. This fallback exists only to flag
                    // a developer typo (e.g. adding a new ``k`` entry to
                    // the array without a matching branch). We no longer
                    // route through the legacy openCreate Dialog from
                    // here — that path is dead.
                    // eslint-disable-next-line no-console
                    console.warn('[ProductsPage] TypePicker: no navigate branch for type', k);
                  }
                }}
                className="flex flex-col items-start gap-1 rounded-xl border border-gray-200 bg-white p-3 text-left hover:border-gray-900 hover:shadow-sm transition-all"
              >
                <span className="text-2xl">{icon}</span>
                <span className="font-semibold text-sm text-gray-900">{t(`products:typePicker.${k}.title`)}</span>
                <span className="text-[11px] text-gray-500 leading-snug">{t(`products:typePicker.${k}.desc`)}</span>
              </button>
            ))}
          </div>
        </DialogContent>
      </Dialog>

      {/* Release 4 (Courses) — Bunny config gate. Opened from the
          TypePicker when the admin selects "🎓 Corso video" without
          having configured Bunny yet. After the dialog closes (either
          via save or dismiss), `pendingNav` resumes the original
          navigation so the admin lands on /courses/new regardless. */}
      {/* Unified Bunny manager — shows the right mode (migrate / empty
          / list / edit) based on org state. Replaces the legacy
          single-library BunnyConfigDialog. The "resume gated nav"
          UX is preserved: when the admin closes the dialog (via save
          or dismiss), pendingNav fires to land them on /courses/new. */}
      <BunnyManagerDialog
        open={bunnyDialogOpen}
        onClose={() => {
          setBunnyDialogOpen(false);
          // Resume the gated navigation when the admin dismisses the
          // dialog: even without Bunny configured the editor is usable
          // (videos can be added later). We don't want to leave them
          // stranded if they prefer to fill credentials another time.
          if (pendingNav) {
            const dest = pendingNav;
            setPendingNav(null);
            navigate(dest);
          }
        }}
      />

      {/* PR-4: legacy create/edit Dialog removed.
          Every entry point now routes to the per-type wizard or dashboard
          via the TypePicker (above) or productCardDashboardHref (in
          ProductCard). The Dialog JSX, plus the openCreate/openEdit/
          handleSave handlers and their associated state (dialogOpen,
          editing, form, saving, showAdvanced, occurrences, aiEnriching,
          validationErrors), were all removed together.
          See docs/PRODUCTS_ARCHITECTURE.md Phase 4 for context. */}
    </AppLayout>
  );
}
