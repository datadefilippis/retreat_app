/**
 * StoresPage — multi-store management for the organization.
 *
 * Lists all stores, allows creating new ones, and provides
 * inline editing of store settings. Each store card shows
 * status, visibility, and quick actions.
 */

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import { AppLayout, Header } from '../../components/Layout';
import { PageSubheader } from '../../components/PageSubheader';
import { ActionOverflowMenu } from '../../components/ui/action-overflow-menu';
import {
  ResponsiveDialog, ResponsiveDialogContent, ResponsiveDialogHeader,
  ResponsiveDialogTitle, ResponsiveDialogFooter,
} from '../../components/ui/responsive-dialog';
import {
  Accordion, AccordionItem, AccordionTrigger, AccordionContent,
} from '../../components/ui/accordion';
import { Card, CardContent } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { useCurrency } from '../../context/AuthContext';
import { formatCurrency as fmtCurrency } from '../../lib/utils';
import { Label } from '../../components/ui/label';
import { Badge } from '../../components/ui/badge';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from '../../components/ui/dialog';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '../../components/ui/select';
import {
  Store, Plus, Loader2, Globe, EyeOff, ShoppingCart, Package,
  CheckCircle2, ExternalLink, Pencil, Eye, BarChart3, X, Tag, Trash2,
  Truck, Settings, Link2, Lock, ArrowUpCircle,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { storesAPI, productsAPI, ordersAPI, couponsAPI, orgBrandingAPI } from '../../api';
import { toast } from 'sonner';
import { handleApiError, isPaywallHandled } from '../../utils/handleApiError';
import ShippingDialog from './components/ShippingDialog';
import OrgBrandingDialog from './components/OrgBrandingDialog';
// Wave GDPR-Commerce CG-3 — admin dialog for per-store legal docs.
import MerchantLegalDialog from './components/MerchantLegalDialog';
// Track E Step 2.3 — modale "Condividi store" (hosted link + embed code).
import ShareStoreModal from './components/ShareStoreModal';
// Wave Design-StoreCard — single-store card with redesigned layout
// (single primary CTA + kebab dropdown for all secondary actions,
// badges collapsed to "+N" tooltip, copy-URL inline).
import StoreCard from './components/StoreCard';

const VISIBILITY_CONFIG = {
  public:  { labelKey: 'visibility.public.label',  icon: Globe,         badge: 'bg-emerald-100 text-emerald-700', descKey: 'visibility.public.desc' },
  private: { labelKey: 'visibility.private.label', icon: EyeOff,        badge: 'bg-slate-100 text-slate-600',     descKey: 'visibility.private.desc' },
  pos:     { labelKey: 'visibility.pos.label',     icon: ShoppingCart,  badge: 'bg-blue-100 text-blue-700',       descKey: 'visibility.pos.desc' },
};

export default function StoresPage() {
  const orgCurrency = useCurrency();
  // CH compliance v1: shared formatter so revenue/coupon labels in this
  // page read in the org's currency (and CHF goes Swiss-style).
  const fmtMoney = (v) => fmtCurrency(Number(v) || 0, orgCurrency);
  const { t } = useTranslation('stores');
  const navigateTo = useNavigate();
  const [stores, setStores] = useState([]);
  const [loading, setLoading] = useState(true);
  const [createOpen, setCreateOpen] = useState(false);
  const [editStore, setEditStore] = useState(null); // store object being edited
  const [saving, setSaving] = useState(false);
  // Shipping configuration dialog — set to a store object to open.
  const [shippingStore, setShippingStore] = useState(null);
  // Wave GDPR-Commerce CG-3 — Privacy + Terms editor dialog (parallel
  // to shippingStore: setting the store object opens the dialog).
  const [legalStore, setLegalStore] = useState(null);
  // Track E Step 2.3 — Share modal (hosted link + embed code).
  // Setting store object opens the modal; null closes.
  const [shareStore, setShareStore] = useState(null);
  // "Impostazioni globali" dialog — controls org-level branding cascade.
  // Open from the header action; on close we re-fetch orgBranding so the
  // inheritance hints in the per-store editor stay in sync if the admin
  // changed something while the store editor was open in another flow.
  const [globalSettingsOpen, setGlobalSettingsOpen] = useState(false);
  // Snapshot of the org-level branding cascade root. Populated on
  // mount; used by the per-store editor to render "Ereditato" hints
  // when the store leaves a field empty.
  const [orgBranding, setOrgBranding] = useState({});

  // Create form
  const [createForm, setCreateForm] = useState({ name: '', slug: '', visibility: 'public' });

  // Edit form
  const [editForm, setEditForm] = useState({});
  const [products, setProducts] = useState([]);

  // Active tab: 'stores' | 'stats' | 'coupons'
  const [activeTab, setActiveTab] = useState('stores');

  // Statistics panel
  const [statsStoreId, setStatsStoreId] = useState('all');
  const [statsData, setStatsData] = useState(null);
  const [statsLoading, setStatsLoading] = useState(false);

  // Coupons
  const [coupons, setCoupons] = useState([]);
  const [couponsLoading, setCouponsLoading] = useState(false);
  const [couponStoreFilter, setCouponStoreFilter] = useState('all');
  const [couponDialogOpen, setCouponDialogOpen] = useState(false);
  const [editingCoupon, setEditingCoupon] = useState(null);
  const [couponForm, setCouponForm] = useState({
    code: '', discount_pct: '', discount_amount: '', min_order_amount: '',
    max_uses: '', valid_from: '', valid_to: '', store_ids: [],
  });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      // Org-level branding fetched in parallel — failure is silent
      // because the inheritance hints are a "nice to have"; the editor
      // works fine without them, just without the badges.
      const [storeRes, prodRes, brandingRes] = await Promise.all([
        storesAPI.list(),
        productsAPI.list(true).catch(() => ({ data: [] })),
        orgBrandingAPI.get().catch(() => ({ data: {} })),
      ]);
      setStores(storeRes.data?.stores || []);
      setProducts(prodRes.data || []);
      setOrgBranding(brandingRes.data || {});
    } catch { /* empty */ }
    finally { setLoading(false); }
  }, []);

  // After the global settings dialog closes, refresh the org branding
  // snapshot so the per-store inheritance hints reflect any change.
  // We don't reload the full stores list — the snapshot alone is enough.
  const handleGlobalSettingsClose = useCallback(async () => {
    setGlobalSettingsOpen(false);
    try {
      const res = await orgBrandingAPI.get();
      setOrgBranding(res.data || {});
    } catch { /* silent */ }
  }, []);

  // Product counts per store
  const storeProductCounts = useMemo(() => {
    const counts = {};
    for (const s of stores) {
      counts[s.id] = products.filter(p =>
        !p.store_ids?.length || p.store_ids.includes(s.id)
      ).length;
    }
    return counts;
  }, [stores, products]);

  useEffect(() => { load(); }, [load]);

  // Fetch stats when tab is active or store filter changes
  useEffect(() => {
    if (activeTab !== 'stats') return;
    const fetchStats = async () => {
      setStatsLoading(true);
      try {
        const sid = statsStoreId === 'all' ? undefined : statsStoreId;
        const res = await ordersAPI.getDashboard(sid);
        setStatsData(res.data);
      } catch { setStatsData(null); }
      finally { setStatsLoading(false); }
    };
    fetchStats();
  }, [activeTab, statsStoreId]);

  // Fetch coupons when tab is active or store filter changes
  const loadCoupons = useCallback(async () => {
    setCouponsLoading(true);
    try {
      const sid = couponStoreFilter === 'all' ? undefined : couponStoreFilter;
      const res = await couponsAPI.list(sid);
      setCoupons(res.data || []);
    } catch { setCoupons([]); }
    finally { setCouponsLoading(false); }
  }, [couponStoreFilter]);

  useEffect(() => {
    if (activeTab === 'coupons') loadCoupons();
  }, [activeTab, couponStoreFilter, loadCoupons]);

  const handleSaveCoupon = async () => {
    setSaving(true);
    try {
      const data = {
        ...couponForm,
        discount_pct: couponForm.discount_pct ? parseFloat(couponForm.discount_pct) : null,
        discount_amount: couponForm.discount_amount ? parseFloat(couponForm.discount_amount) : null,
        min_order_amount: couponForm.min_order_amount ? parseFloat(couponForm.min_order_amount) : null,
        max_uses: couponForm.max_uses ? parseInt(couponForm.max_uses) : null,
        valid_from: couponForm.valid_from || null,
        valid_to: couponForm.valid_to || null,
        store_ids: couponForm.store_ids || [],
      };
      if (editingCoupon) {
        const { code, ...updateData } = data;
        await couponsAPI.update(editingCoupon.id, updateData);
        toast.success(t('coupons.toast.updated'));
      } else {
        await couponsAPI.create(data);
        toast.success(t('coupons.toast.created'));
      }
      setCouponDialogOpen(false);
      setEditingCoupon(null);
      setCouponForm({ code: '', discount_pct: '', discount_amount: '', min_order_amount: '', max_uses: '', valid_from: '', valid_to: '', store_ids: [] });
      loadCoupons();
    } catch (err) {
      toast.error(err?.response?.data?.detail || t('coupons.toast.error'));
    } finally { setSaving(false); }
  };

  const handleDeleteCoupon = async (couponId) => {
    if (!window.confirm(t('coupons.delete_confirm'))) return;
    try {
      await couponsAPI.delete(couponId);
      toast.success(t('coupons.toast.deleted'));
      loadCoupons();
    } catch { toast.error(t('coupons.toast.error')); }
  };

  const openEditCoupon = (coupon) => {
    setEditingCoupon(coupon);
    setCouponForm({
      code: coupon.code,
      discount_pct: coupon.discount_pct || '',
      discount_amount: coupon.discount_amount || '',
      min_order_amount: coupon.min_order_amount || '',
      max_uses: coupon.max_uses || '',
      valid_from: coupon.valid_from || '',
      valid_to: coupon.valid_to || '',
      store_ids: coupon.store_ids || [],
    });
    setCouponDialogOpen(true);
  };

  const handleCreate = async () => {
    if (!createForm.name.trim()) return;
    setSaving(true);
    try {
      const res = await storesAPI.create({
        name: createForm.name.trim(),
        slug: createForm.slug.trim() || undefined,
        visibility: createForm.visibility,
      });
      const newStore = res?.data;
      toast.success(t('toast.created'));
      setCreateOpen(false);
      setCreateForm({ name: '', slug: '', visibility: 'public' });
      await load();
      // Auto-open edit dialog for the new store so admin can configure branding/email
      if (newStore?.id) {
        const freshStores = (await storesAPI.list()).data?.stores || [];
        const created = freshStores.find(s => s.id === newStore.id);
        if (created) openEdit(created);
      }
    } catch (err) {
      // v5.8 / Onda 9.O — paywall opens automatically for QUOTA_EXCEEDED.
      // v5.8 / Onda 9.R — also CLOSE the create dialog so the user sees
      // the paywall on a clean slate (was: 2 stacked modals, X of dialog
      // covered by paywall backdrop, "popup duplicato" UX bug).
      if (isPaywallHandled(err)) {
        setCreateOpen(false);
      }
      handleApiError(err, t('toast.error'));
    } finally { setSaving(false); }
  };

  const openEdit = (store) => {
    setEditStore(store);
    setEditForm({
      name: store.name || '',
      slug: store.slug || '',
      description: store.description || '',
      contact_email: store.contact_email || '',
      contact_phone: store.contact_phone || '',
      visibility: store.visibility || 'public',
      // Branding
      brand_color: store.brand_color || '',
      brand_color_text: store.brand_color_text || '',
      seo_title: store.seo_title || '',
      seo_description: store.seo_description || '',
      // Email
      sender_display_name: store.sender_display_name || '',
      reply_to_email: store.reply_to_email || '',
      notification_email: store.notification_email || '',
      // Fulfillment
      fulfillment_modes: store.fulfillment_modes || ['shipping'],
      // Languages
      storefront_languages: store.storefront_languages || ['it'],
      // Phase 8 — Custom navigation links. Each item:
      //   { id, label_i18n: {it: '...', ...}, url, target, sort_order }
      // The backend validates label_i18n has an entry for every
      // active storefront_language. Default to empty array on first
      // edit so the admin sees the "Aggiungi link" CTA.
      custom_nav_links: store.custom_nav_links || [],
      // Phase 9 — Design tokens. Dict shape:
      //   { font_family, border_radius, density, header_style,
      //     card_style, accent_color }
      // All keys optional. The admin edits each via a select / color
      // picker; on save the backend validator drops empty strings
      // and normalizes hex colors. Default to {} so the form starts
      // showing the "default" pill highlighted for each enum.
      design_tokens: store.design_tokens || {},
    });
  };

  const handleSaveEdit = async () => {
    if (!editStore) return;
    setSaving(true);
    try {
      const updates = {};
      if (editForm.name.trim()) updates.name = editForm.name.trim();
      if (editForm.slug.trim()) updates.slug = editForm.slug.trim();
      updates.description = editForm.description?.trim() || null;
      updates.contact_email = editForm.contact_email?.trim() || null;
      updates.contact_phone = editForm.contact_phone?.trim() || null;
      updates.visibility = editForm.visibility;
      // Branding
      updates.brand_color = editForm.brand_color?.trim() || null;
      updates.brand_color_text = editForm.brand_color_text?.trim() || null;
      updates.seo_title = editForm.seo_title?.trim() || null;
      updates.seo_description = editForm.seo_description?.trim() || null;
      // Email
      updates.sender_display_name = editForm.sender_display_name?.trim() || null;
      updates.reply_to_email = editForm.reply_to_email?.trim() || null;
      updates.notification_email = editForm.notification_email?.trim() || null;
      // Fulfillment
      updates.fulfillment_modes = editForm.fulfillment_modes;
      // Storefront languages — MVP single-element array. The picker
      // (see "Storefront Languages" Accordion) guarantees the array
      // has exactly one entry on save. Was missing from this update
      // body before, causing the lang choice to never persist
      // (the picker reflected `editForm.storefront_languages` but
      // the PATCH never sent it, so the next dialog open re-read the
      // unchanged DB value and showed the legacy/initial language).
      updates.storefront_languages = editForm.storefront_languages;
      // Phase 8 — Custom nav links. Always send the array (even if
      // empty) so clearing a link saves correctly. Backend validates:
      //   · max 3 links
      //   · label_i18n has entry for every active store language
      //   · URL is safe (http/https/mailto/tel/internal)
      updates.custom_nav_links = editForm.custom_nav_links || [];
      // Phase 9 — Design tokens. Always send the dict (even empty)
      // so admin resetting to defaults clears DB-stored overrides.
      // Backend validator drops empty-string values + normalizes hex.
      updates.design_tokens = editForm.design_tokens || {};

      await storesAPI.update(editStore.id, updates);
      // Sprint 4 W4.5 — signal cross-tab al widget embed (se aperto
      // nello stesso browser stessa origin) di re-fetchare init perche'
      // il merchant ha cambiato storefront_languages / brand_color /
      // custom_nav_links / design_tokens. Widget ascolta storage event
      // su key `afianco_admin_changed_{slug}` e triggera re-init.
      // Cross-origin (es. widget su miosito.com) il polling 90s fallback
      // garantisce comunque pickup entro 1-2 minuti.
      try {
        const slug = editStore.slug;
        if (slug && typeof localStorage !== 'undefined') {
          localStorage.setItem(
            `afianco_admin_changed_${slug}`,
            String(Date.now()),
          );
        }
      } catch {
        // localStorage non disponibile - non blocca
      }
      toast.success(t('toast.updated'));
      setEditStore(null);
      await load();
    } catch (err) {
      toast.error(err?.response?.data?.detail || t('toast.error'));
    } finally { setSaving(false); }
  };

  const handleTogglePublish = async (store) => {
    try {
      if (store.is_published) {
        await storesAPI.unpublish(store.id);
        toast.success(t('toast.unpublished'));
      } else {
        await storesAPI.publish(store.id);
        toast.success(t('toast.published'));
      }
      await load();
    } catch (err) {
      toast.error(err?.response?.data?.detail || t('toast.error'));
    }
  };

  // Build tabs + contextual action for the PageSubheader. Each tab uses a
  // shortLabel fallback key so the phone viewport gets the compact variant
  // ("Stats" instead of "Statistiche") while desktop keeps the full one.
  const subheaderTabs = [
    { key: 'stores',  label: t('tabs.stores'),  shortLabel: t('tabs_short.stores',  { defaultValue: t('tabs.stores') }),  icon: Store },
    { key: 'stats',   label: t('tabs.stats'),   shortLabel: t('tabs_short.stats',   { defaultValue: t('tabs.stats') }),   icon: BarChart3 },
    { key: 'coupons', label: t('tabs.coupons'), shortLabel: t('tabs_short.coupons', { defaultValue: t('tabs.coupons') }), icon: Tag },
  ];

  const subheaderActions = (() => {
    if (activeTab === 'stores') {
      // Two actions: "Impostazioni globali" (org-level branding cascade)
      // sits to the LEFT of "Crea store" because creation is the more
      // frequent action and stays as the visually-primary CTA. The
      // settings button is outline-styled so the eye still lands on
      // the create action first. On phones we collapse the settings
      // label to just the gear icon to keep the row from wrapping.
      return (
        <div className="flex items-center gap-1.5">
          <Button
            size="sm"
            variant="outline"
            onClick={() => setGlobalSettingsOpen(true)}
            className="gap-1.5"
            // Same key used for both the button tooltip (always present
            // for accessibility/touch) and the visible label (sm+).
            // Single source of truth so a translation update propagates
            // to both surfaces with one edit.
            title={t('actions.global_settings')}
          >
            <Settings className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">{t('actions.global_settings')}</span>
          </Button>
          <Button size="sm" onClick={() => setCreateOpen(true)} className="gap-1.5">
            <Plus className="h-3.5 w-3.5" />
            <span className="sm:hidden">{t('actions.create_short', { defaultValue: t('actions.create') })}</span>
            <span className="hidden sm:inline">{t('actions.create')}</span>
          </Button>
        </div>
      );
    }
    if (activeTab === 'coupons') {
      return (
        <Button
          size="sm"
          onClick={() => {
            setEditingCoupon(null);
            setCouponForm({ code: '', discount_pct: '', discount_amount: '', min_order_amount: '', max_uses: '', valid_from: '', valid_to: '', store_ids: [] });
            setCouponDialogOpen(true);
          }}
          className="gap-1.5"
        >
          <Plus className="h-3.5 w-3.5" />
          <span className="sm:hidden">{t('coupons.new_btn_short', { defaultValue: t('coupons.new_btn') })}</span>
          <span className="hidden sm:inline">{t('coupons.new_btn')}</span>
        </Button>
      );
    }
    return null;
  })();

  return (
    <AppLayout>
      <Header title={t('title')} subtitle={t('subtitle')}>
        {/* UX round 5/7 — il profilo pubblico e' PERTINENTE qui: e' la
            vetrina dell'operatore, accanto ai suoi store. (Resta anche
            in Impostazioni, ma questo e' il posto dove lo cerchi.) */}
        <Link to="/public-profile">
          <Button variant="outline" size="sm">
            {t('publicProfileCta', { defaultValue: '🌿 Il tuo profilo pubblico' })}
          </Button>
        </Link>
      </Header>
      <PageSubheader
        tabs={subheaderTabs}
        activeTab={activeTab}
        onTabChange={setActiveTab}
        actions={subheaderActions}
      />

      <div className="p-4 md:p-6 max-w-4xl mx-auto space-y-4">
        {/* Statistics Tab */}
        {activeTab === 'stats' && (
          <Card className="border border-border mb-4">
            <CardContent className="p-5 space-y-4">
              <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                <h3 className="font-semibold text-lg flex items-center gap-2">
                  <BarChart3 className="h-5 w-5 text-primary" /> {t('stats.title')}
                </h3>
                <Select value={statsStoreId} onValueChange={setStatsStoreId}>
                  <SelectTrigger className="w-full sm:w-48 md:w-56">
                    <SelectValue placeholder={t('all_stores')} />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">{t('all_stores')}</SelectItem>
                    {stores.map(s => (
                      <SelectItem key={s.id} value={s.id}>{s.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {statsLoading ? (
                <div className="flex justify-center py-8"><Loader2 className="h-5 w-5 animate-spin text-muted-foreground" /></div>
              ) : !statsData?.has_data ? (
                <p className="text-sm text-muted-foreground text-center py-6">{statsStoreId !== 'all' ? t('stats.no_orders_store') : t('stats.no_orders')}</p>
              ) : (
                <>
                  {/* Quick stats row */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    {[
                      { label: t('stats.revenue_confirmed'), value: fmtMoney(statsData.stats?.revenue_confirmed_30d || 0), sub: t('stats.last_30d') },
                      { label: t('stats.orders_today'), value: statsData.stats?.orders_today || 0 },
                      { label: t('stats.completion'), value: `${statsData.stats?.completion_rate_pct || 0}%` },
                      { label: t('stats.cancellations_7d'), value: statsData.stats?.cancellations_7d || 0 },
                    ].map((s, i) => (
                      <div key={i} className="bg-muted/50 rounded-lg p-3 text-center">
                        <div className="text-lg font-bold">{s.value}</div>
                        <div className="text-xs text-muted-foreground">{s.label}</div>
                        {s.sub && <div className="text-[10px] text-muted-foreground/60">{s.sub}</div>}
                      </div>
                    ))}
                  </div>

                  {/* Pipeline */}
                  {statsData.pipeline && Object.keys(statsData.pipeline).length > 0 && (
                    <div>
                      <h4 className="text-sm font-medium mb-2">{t('stats.pipeline_title')}</h4>
                      <div className="flex gap-1 h-3 rounded-full overflow-hidden bg-muted">
                        {['draft', 'confirmed', 'completed', 'cancelled'].map(status => {
                          const d = statsData.pipeline[status];
                          if (!d?.count) return null;
                          const total = Object.values(statsData.pipeline).reduce((s, v) => s + (v?.count || 0), 0);
                          const pct = total > 0 ? (d.count / total * 100) : 0;
                          const colors = { draft: 'bg-slate-400', confirmed: 'bg-blue-500', completed: 'bg-emerald-500', cancelled: 'bg-red-400' };
                          return <div key={status} className={`${colors[status]} transition-all`} style={{ width: `${pct}%` }} title={`${status}: ${d.count}`} />;
                        })}
                      </div>
                      <div className="flex gap-3 mt-1.5 text-xs text-muted-foreground flex-wrap">
                        {['draft', 'confirmed', 'completed', 'cancelled'].map(status => {
                          const d = statsData.pipeline[status];
                          if (!d?.count) return null;
                          const labels = { draft: t('stats.pipeline.draft'), confirmed: t('stats.pipeline.confirmed'), completed: t('stats.pipeline.completed'), cancelled: t('stats.pipeline.cancelled') };
                          return <span key={status}>{labels[status]}: {d.count} ({fmtMoney(d.amount || 0)})</span>;
                        })}
                      </div>
                    </div>
                  )}

                  {/* Revenue by type */}
                  {statsData.revenue_by_type && Object.keys(statsData.revenue_by_type).length > 0 && (
                    <div>
                      <h4 className="text-sm font-medium mb-2">{t('stats.revenue_by_type_title')}</h4>
                      <div className="space-y-1.5">
                        {Object.entries(statsData.revenue_by_type).sort(([,a],[,b]) => b - a).map(([type, rev]) => {
                          const maxRev = Math.max(...Object.values(statsData.revenue_by_type));
                          const pct = maxRev > 0 ? (rev / maxRev * 100) : 0;
                          const labels = { physical: t('stats.item_types.physical'), event_ticket: t('stats.item_types.event_ticket'), booking: t('stats.item_types.booking'), rental: t('stats.item_types.rental'), service: t('stats.item_types.service') };
                          const colors = { physical: 'bg-gray-500', event_ticket: 'bg-purple-500', booking: 'bg-teal-500', rental: 'bg-orange-500', service: 'bg-blue-400' };
                          return (
                            <div key={type} className="flex items-center gap-2">
                              {/* Label: narrower on mobile so the bar + value still fit. */}
                              <span className="text-xs w-20 sm:w-24 shrink-0 text-muted-foreground truncate" title={labels[type] || type}>
                                {labels[type] || type}
                              </span>
                              <div className="flex-1 min-w-0 h-2 bg-muted rounded-full overflow-hidden">
                                <div className={`h-full ${colors[type] || 'bg-primary'} rounded-full`} style={{ width: `${pct}%` }} />
                              </div>
                              <span className="text-xs font-medium w-16 sm:w-20 shrink-0 text-right tabular-nums">
                                {fmtMoney(rev)}
                              </span>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}

                  {/* Payment at risk */}
                  {statsData.payment_at_risk?.count > 0 && (
                    <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                      <span className="text-sm font-medium text-red-700">
                        {t('stats.payment_at_risk', { count: statsData.payment_at_risk.count, amount: statsData.payment_at_risk.amount?.toLocaleString('it-IT') })}
                      </span>
                    </div>
                  )}
                </>
              )}
            </CardContent>
          </Card>
        )}

        {/* Store list */}
        {activeTab === 'stores' && (loading ? (
          <div className="flex justify-center py-16"><Loader2 className="h-6 w-6 animate-spin text-muted-foreground" /></div>
        ) : stores.length === 0 ? (
          <div className="text-center py-16 space-y-3">
            <Store className="h-12 w-12 text-muted-foreground/40 mx-auto" />
            <h3 className="font-semibold">{t('empty.title')}</h3>
            <p className="text-sm text-muted-foreground">{t('empty.desc')}</p>
            <Button onClick={() => setCreateOpen(true)} className="gap-1.5">
              <Plus className="h-4 w-4" /> {t('actions.create')}
            </Button>
          </div>
        ) : (
          // 2026-05-19 — inline-actions redesign: the card grew taller
          // (5-6 inline buttons in 1-2 rows instead of a single "Modifica"
          // + kebab) and the merchant feedback was "too small on desktop,
          // text + buttons look cramped". Cap the grid at 2 columns even
          // on wide viewports so each card gets ~50% of the page width
          // → buttons breathe, labels stay on one line, the storefront
          // URL doesn't truncate aggressively.
          //   · mobile (< sm)   1 column
          //   · sm+ (≥ 640px)   2 columns
          <div className="grid gap-4 sm:grid-cols-2">
            {stores.map(store => {
              const vis = VISIBILITY_CONFIG[store.visibility] || VISIBILITY_CONFIG.public;
              return (
                <StoreCard
                  key={store.id}
                  store={store}
                  storeProductCount={storeProductCounts[store.id] || 0}
                  visibilityConfig={vis}
                  t={t}
                  onEdit={openEdit}
                  onShipping={setShippingStore}
                  onGdpr={setLegalStore}
                  onShare={setShareStore}
                  onTogglePublish={handleTogglePublish}
                  onOpenPos={(s) => { window.location.href = `/pos/${s.id}`; }}
                  onPlanUpgrade={() => navigateTo('/plans')}
                />
              );
            })}
          </div>
        ))}
        {/* Coupons Tab */}
        {activeTab === 'coupons' && (
          <Card className="border border-border">
            <CardContent className="p-5 space-y-4">
              <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                <h3 className="font-semibold text-lg flex items-center gap-2">
                  <Tag className="h-5 w-5 text-primary" /> {t('coupons.title')}
                </h3>
                <Select value={couponStoreFilter} onValueChange={setCouponStoreFilter}>
                  <SelectTrigger className="w-full sm:w-48 md:w-56">
                    <SelectValue placeholder={t('all_stores')} />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">{t('all_stores')}</SelectItem>
                    {stores.map(s => (
                      <SelectItem key={s.id} value={s.id}>{s.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {couponsLoading ? (
                <div className="flex justify-center py-8"><Loader2 className="h-5 w-5 animate-spin text-muted-foreground" /></div>
              ) : coupons.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-8">
                  {couponStoreFilter !== 'all' ? t('coupons.empty_store') : t('coupons.empty')}
                </p>
              ) : (
                <div className="space-y-2">
                  {coupons.map(coupon => {
                    const storeNames = (coupon.store_ids || []).length > 0
                      ? stores.filter(s => coupon.store_ids.includes(s.id)).map(s => s.name)
                      : [];
                    return (
                      <div
                        key={coupon.id}
                        className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between p-3 rounded-lg border bg-card hover:bg-muted/50 transition-colors"
                      >
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <code className="text-sm font-bold bg-muted px-2 py-0.5 rounded break-all">{coupon.code}</code>
                            {coupon.discount_pct ? (
                              <Badge variant="secondary" className="text-xs">-{coupon.discount_pct}%</Badge>
                            ) : coupon.discount_amount ? (
                              <Badge variant="secondary" className="text-xs">-{fmtMoney(coupon.discount_amount)}</Badge>
                            ) : null}
                            {!coupon.is_active && <Badge variant="outline" className="text-xs text-red-500">{t('coupons.inactive')}</Badge>}
                            {storeNames.length > 0 ? (
                              storeNames.map(n => <Badge key={n} variant="outline" className="text-xs max-w-[10rem] truncate">{n}</Badge>)
                            ) : (
                              <Badge variant="outline" className="text-xs text-emerald-600">{t('coupons.all_stores_badge')}</Badge>
                            )}
                          </div>
                          <div className="flex gap-3 mt-1 text-xs text-muted-foreground flex-wrap">
                            <span>{t('coupons.uses')}: {coupon.current_uses}{coupon.max_uses ? `/${coupon.max_uses}` : ''}</span>
                            {coupon.min_order_amount && <span>{t('coupons.min_order')}: {fmtMoney(coupon.min_order_amount)}</span>}
                            {coupon.valid_to && <span>{t('coupons.expires')}: {coupon.valid_to}</span>}
                          </div>
                        </div>
                        {/* Actions: icons-only on mobile (sm:ml-2 pulls them tight on tablet+) */}
                        <div className="flex gap-1 self-end sm:self-center sm:ml-2 shrink-0">
                          <Button size="sm" variant="ghost" onClick={() => openEditCoupon(coupon)} aria-label={t('coupons.dialog.save')}>
                            <Pencil className="h-3.5 w-3.5" />
                          </Button>
                          <Button size="sm" variant="ghost" className="text-destructive" onClick={() => handleDeleteCoupon(coupon.id)} aria-label={t('coupons.dialog.cancel')}>
                            <Trash2 className="h-3.5 w-3.5" />
                          </Button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </CardContent>
          </Card>
        )}
      </div>

      {/* Coupon Dialog — ResponsiveDialog (Drawer on mobile) */}
      <ResponsiveDialog open={couponDialogOpen} onOpenChange={(v) => { setCouponDialogOpen(v); if (!v) setEditingCoupon(null); }}>
        <ResponsiveDialogContent className="sm:max-w-md max-h-[90vh] sm:max-h-[85vh] overflow-y-auto">
          <ResponsiveDialogHeader>
            <ResponsiveDialogTitle>{editingCoupon ? t('coupons.dialog.edit_title') : t('coupons.dialog.create_title')}</ResponsiveDialogTitle>
          </ResponsiveDialogHeader>
          <div className="space-y-3 px-4 sm:px-0 pb-2">
            {!editingCoupon && (
              <div>
                <Label>{t('coupons.dialog.code')}</Label>
                <Input value={couponForm.code} onChange={e => setCouponForm({...couponForm, code: e.target.value.toUpperCase().replace(/[^A-Z0-9_-]/g, '')})} placeholder="ES. ESTATE2026" maxLength={30} />
              </div>
            )}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <Label>{t('coupons.dialog.discount_pct')}</Label>
                <Input type="number" inputMode="decimal" value={couponForm.discount_pct} onChange={e => setCouponForm({...couponForm, discount_pct: e.target.value, discount_amount: ''})} placeholder="10" min="0" max="100" />
              </div>
              <div>
                <Label>{t('coupons.dialog.discount_fixed')}</Label>
                <Input type="number" inputMode="decimal" value={couponForm.discount_amount} onChange={e => setCouponForm({...couponForm, discount_amount: e.target.value, discount_pct: ''})} placeholder="5.00" min="0" step="0.01" />
              </div>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <Label>{t('coupons.dialog.min_order')}</Label>
                <Input type="number" inputMode="decimal" value={couponForm.min_order_amount} onChange={e => setCouponForm({...couponForm, min_order_amount: e.target.value})} placeholder="0" min="0" step="0.01" />
              </div>
              <div>
                <Label>{t('coupons.dialog.max_uses')}</Label>
                <Input type="number" inputMode="numeric" value={couponForm.max_uses} onChange={e => setCouponForm({...couponForm, max_uses: e.target.value})} placeholder={t('coupons.dialog.unlimited_placeholder')} min="1" />
              </div>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <Label>{t('coupons.dialog.valid_from')}</Label>
                <Input type="date" value={couponForm.valid_from} onChange={e => setCouponForm({...couponForm, valid_from: e.target.value})} />
              </div>
              <div>
                <Label>{t('coupons.dialog.valid_until')}</Label>
                <Input type="date" value={couponForm.valid_to} onChange={e => setCouponForm({...couponForm, valid_to: e.target.value})} />
              </div>
            </div>
            <div>
              <Label>{t('coupons.dialog.valid_stores')}</Label>
              <p className="text-xs text-muted-foreground mb-1.5">{t('coupons.dialog.valid_stores_hint')}</p>
              <div className="space-y-1 max-h-40 overflow-y-auto rounded-md border p-2">
                {stores.map(s => (
                  <label key={s.id} className="flex items-center gap-2 text-sm cursor-pointer py-1">
                    <input
                      type="checkbox"
                      checked={couponForm.store_ids.includes(s.id)}
                      onChange={e => {
                        const ids = e.target.checked
                          ? [...couponForm.store_ids, s.id]
                          : couponForm.store_ids.filter(id => id !== s.id);
                        setCouponForm({...couponForm, store_ids: ids});
                      }}
                      className="rounded shrink-0"
                    />
                    <span className="truncate">{s.name}</span>
                  </label>
                ))}
              </div>
            </div>
          </div>
          <ResponsiveDialogFooter>
            <Button variant="outline" onClick={() => setCouponDialogOpen(false)} className="w-full sm:w-auto">
              {t('coupons.dialog.cancel')}
            </Button>
            <Button
              onClick={handleSaveCoupon}
              disabled={saving || (!editingCoupon && !couponForm.code)}
              className="w-full sm:w-auto"
            >
              {saving ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : editingCoupon ? t('coupons.dialog.save') : t('coupons.dialog.create')}
            </Button>
          </ResponsiveDialogFooter>
        </ResponsiveDialogContent>
      </ResponsiveDialog>

      {/* Create Store Dialog — ResponsiveDialog (Drawer on mobile) */}
      <ResponsiveDialog open={createOpen} onOpenChange={setCreateOpen}>
        <ResponsiveDialogContent className="sm:max-w-md">
          <ResponsiveDialogHeader>
            <ResponsiveDialogTitle>{t('create.title')}</ResponsiveDialogTitle>
          </ResponsiveDialogHeader>
          <div className="space-y-4 py-2 px-4 sm:px-0">
            <div>
              <Label>{t('create.name')} *</Label>
              <Input value={createForm.name} onChange={e => setCreateForm(f => ({ ...f, name: e.target.value }))} placeholder={t('create.name_placeholder')} />
            </div>
            <div>
              <Label>{t('create.slug')}</Label>
              <Input value={createForm.slug} onChange={e => setCreateForm(f => ({ ...f, slug: e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, '') }))} placeholder={t('create.slug_placeholder')} />
              <p className="text-[10px] text-muted-foreground mt-0.5">{t('create.slug_hint')}</p>
            </div>
            <div>
              <Label>{t('create.visibility')}</Label>
              <div className="grid grid-cols-3 gap-2 mt-1">
                {Object.entries(VISIBILITY_CONFIG).map(([key, cfg]) => {
                  const Icon = cfg.icon;
                  return (
                    <button
                      key={key}
                      type="button"
                      onClick={() => setCreateForm(f => ({ ...f, visibility: key }))}
                      className={`flex flex-col items-center gap-1 rounded-lg border p-3 text-xs transition-colors ${
                        createForm.visibility === key ? 'border-primary bg-primary/5 text-primary font-medium' : 'border-border text-muted-foreground hover:border-primary/30'
                      }`}
                    >
                      <Icon className="h-4 w-4" />
                      {t(cfg.labelKey)}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
          <ResponsiveDialogFooter>
            <Button variant="outline" onClick={() => setCreateOpen(false)} className="w-full sm:w-auto">
              {t('create.cancel')}
            </Button>
            <Button
              disabled={saving || !createForm.name.trim()}
              onClick={handleCreate}
              className="gap-1.5 w-full sm:w-auto"
            >
              {saving ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Plus className="h-3.5 w-3.5" />}
              {t('create.submit')}
            </Button>
          </ResponsiveDialogFooter>
        </ResponsiveDialogContent>
      </ResponsiveDialog>

      {/* Edit Store Dialog — ResponsiveDialog (Drawer on mobile) + Accordion sections */}
      <ResponsiveDialog open={!!editStore} onOpenChange={(open) => { if (!open) setEditStore(null); }}>
        <ResponsiveDialogContent className="sm:max-w-lg max-h-[90vh] sm:max-h-[85vh] overflow-y-auto">
          <ResponsiveDialogHeader>
            <ResponsiveDialogTitle>{t('edit.title')}</ResponsiveDialogTitle>
          </ResponsiveDialogHeader>

          <div className="px-4 sm:px-0 pb-2">
            <Accordion
              type="multiple"
              defaultValue={['identity', 'visibility']}
              className="space-y-2"
            >
              {/* Identity */}
              <AccordionItem value="identity" className="border rounded-lg px-3">
                <AccordionTrigger className="text-sm font-semibold py-3 hover:no-underline">
                  {t('edit.section_identity', { defaultValue: 'Identità' })}
                </AccordionTrigger>
                <AccordionContent className="space-y-3 pt-1">
                  <div>
                    <Label>{t('create.name')} *</Label>
                    <Input value={editForm.name || ''} onChange={e => setEditForm(f => ({ ...f, name: e.target.value }))} />
                  </div>
                  <div>
                    <Label>{t('create.slug')}</Label>
                    <Input value={editForm.slug || ''} onChange={e => setEditForm(f => ({ ...f, slug: e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, '') }))} />
                  </div>
                  <div>
                    <Label>{t('edit.description')}</Label>
                    <textarea
                      value={editForm.description || ''}
                      onChange={e => setEditForm(f => ({ ...f, description: e.target.value.slice(0, 500) }))}
                      rows={2} maxLength={500}
                      className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                    />
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <Label>{t('edit.contact_email')}</Label>
                      <Input type="email" value={editForm.contact_email || ''} onChange={e => setEditForm(f => ({ ...f, contact_email: e.target.value }))} />
                    </div>
                    <div>
                      <Label>{t('edit.contact_phone')}</Label>
                      <Input type="tel" value={editForm.contact_phone || ''} onChange={e => setEditForm(f => ({ ...f, contact_phone: e.target.value }))} />
                    </div>
                  </div>
                </AccordionContent>
              </AccordionItem>

              {/* Branding */}
              <AccordionItem value="branding" className="border rounded-lg px-3">
                <AccordionTrigger className="text-sm font-semibold py-3 hover:no-underline">
                  {t('branding.title')}
                </AccordionTrigger>
                <AccordionContent className="space-y-3 pt-1">
                  {/* Per-store fields override the org-level cascade.
                      A field left empty inherits from the org branding
                      configured under "Impostazioni globali". The badges
                      below each empty field hint at the value the store
                      WILL show when published, without requiring the
                      admin to mentally cross-reference the global panel. */}

                  {/* Logo — show org logo as inherited preview when this
                      store has no logo of its own. */}
                  <div className="flex items-center gap-4">
                    {editStore?.logo_url ? (
                      <img src={editStore.logo_url} alt="" className="h-14 w-14 rounded-lg object-cover border" />
                    ) : orgBranding?.logo_url ? (
                      <div className="relative h-14 w-14 shrink-0">
                        <img
                          src={orgBranding.logo_url}
                          alt={t('inheritance.logo_alt')}
                          className="h-14 w-14 rounded-lg object-cover border opacity-60"
                          title={t('inheritance.tooltip')}
                        />
                        <span
                          className="absolute -top-1 -right-1 inline-flex h-4 w-4 items-center justify-center rounded-full bg-blue-100 border border-blue-300"
                          title={t('inheritance.tooltip')}
                        >
                          <Link2 className="h-2.5 w-2.5 text-blue-700" />
                        </span>
                      </div>
                    ) : (
                      <div className="h-14 w-14 rounded-lg bg-muted flex items-center justify-center text-muted-foreground text-xs border">Logo</div>
                    )}
                    <div className="flex-1 min-w-0 space-y-1">
                      <label className="text-xs text-primary hover:underline cursor-pointer inline-block">
                        {editStore?.logo_url ? t('branding.logo_replace') : t('branding.logo_upload')}
                        <input type="file" accept="image/jpeg,image/png,image/webp,image/svg+xml" className="hidden"
                          onChange={async (e) => {
                            const file = e.target.files?.[0];
                            if (!file || !editStore) return;
                            const inputEl = e.target;
                            try {
                              const res = await storesAPI.uploadLogo(editStore.id, file);
                              const newUrl = res.data?.logo_url;
                              if (newUrl) {
                                // Cache-bust so <img> reloads even when the
                                // server reuses the same path, and use the
                                // state setter so React re-renders the preview.
                                const bust = newUrl.includes('?') ? '&' : '?';
                                const busted = `${newUrl}${bust}t=${Date.now()}`;
                                setEditStore(prev => prev ? { ...prev, logo_url: busted } : prev);
                              }
                              toast.success(t('branding.logo_uploaded'));
                            } catch (err) {
                              toast.error(err?.response?.data?.detail || t('branding.logo_error'));
                            } finally {
                              if (inputEl) inputEl.value = '';
                            }
                          }}
                        />
                      </label>
                      {!editStore?.logo_url && orgBranding?.logo_url && (
                        <p className="text-[10px] text-blue-700 flex items-center gap-1">
                          <Link2 className="h-2.5 w-2.5" />
                          Ereditato dalle impostazioni globali
                        </p>
                      )}
                    </div>
                  </div>

                  {/* Brand colors — same inheritance hint pattern. The
                      color pickers default to the inherited value when
                      the store hasn't overridden, but the hex input
                      stays empty so saving the form doesn't write the
                      inherited value as an explicit override. */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <Label className="text-xs">{t('branding.brand_color')}</Label>
                      <div className="flex items-center gap-2">
                        <input
                          type="color"
                          value={editForm.brand_color || orgBranding?.brand_color || '#1a1a1a'}
                          onChange={e => setEditForm(f => ({ ...f, brand_color: e.target.value }))}
                          className="w-10 h-10 rounded border cursor-pointer shrink-0"
                        />
                        <Input
                          value={editForm.brand_color || ''}
                          onChange={e => setEditForm(f => ({ ...f, brand_color: e.target.value }))}
                          placeholder={orgBranding?.brand_color || '#1a1a1a'}
                          className="flex-1 text-sm"
                        />
                      </div>
                      {!editForm.brand_color && orgBranding?.brand_color && (
                        <p className="text-[10px] text-blue-700 mt-0.5 flex items-center gap-1">
                          <Link2 className="h-2.5 w-2.5" />
                          Ereditato: <code>{orgBranding.brand_color}</code>
                        </p>
                      )}
                    </div>
                    <div>
                      <Label className="text-xs">{t('branding.text_color')}</Label>
                      <div className="flex items-center gap-2">
                        <input
                          type="color"
                          value={editForm.brand_color_text || orgBranding?.brand_color_text || '#ffffff'}
                          onChange={e => setEditForm(f => ({ ...f, brand_color_text: e.target.value }))}
                          className="w-10 h-10 rounded border cursor-pointer shrink-0"
                        />
                        <Input
                          value={editForm.brand_color_text || ''}
                          onChange={e => setEditForm(f => ({ ...f, brand_color_text: e.target.value }))}
                          placeholder={orgBranding?.brand_color_text || '#ffffff'}
                          className="flex-1 text-sm"
                        />
                      </div>
                      {!editForm.brand_color_text && orgBranding?.brand_color_text && (
                        <p className="text-[10px] text-blue-700 mt-0.5 flex items-center gap-1">
                          <Link2 className="h-2.5 w-2.5" />
                          Ereditato: <code>{orgBranding.brand_color_text}</code>
                        </p>
                      )}
                    </div>
                  </div>

                  {/* Live preview — uses the resolved values (store
                      override > org default) so the admin sees what
                      visitors will see. Only renders when at least the
                      brand color is resolvable. */}
                  {(editForm.brand_color || orgBranding?.brand_color) && (
                    <div
                      className="rounded-lg p-2.5 text-sm"
                      style={{
                        backgroundColor: editForm.brand_color || orgBranding?.brand_color,
                        color: editForm.brand_color_text || orgBranding?.brand_color_text || '#fff',
                      }}
                    >
                      {t('branding.preview')}: {editForm.name || 'Store'}
                    </div>
                  )}
                </AccordionContent>
              </AccordionItem>

              {/* Phase 9.4 — Design tokens section.
                  Lets the merchant tune 6 visual knobs of the
                  storefront (radius / density / font / header style /
                  card style / accent color). All defaults keep the
                  current look — picking a non-default value changes
                  the storefront immediately on next load.
                  Each enum is a button row (radio-style) so the
                  current pick is obvious at a glance. */}
              <AccordionItem value="design_tokens" className="border rounded-lg px-3">
                <AccordionTrigger className="text-sm font-semibold py-3 hover:no-underline">
                  {t('design.title', 'Design')}
                </AccordionTrigger>
                <AccordionContent className="space-y-4 pt-1">
                  <p className="text-xs text-muted-foreground">
                    {t('design.hint', 'Personalizza l\'aspetto dello storefront. Tutti i campi sono opzionali; lasciali al valore predefinito per mantenere il look standard.')}
                  </p>

                  {/* Helper for rendering a token enum picker */}
                  {[
                    {
                      key: 'font_family',
                      label: t('design.fontFamily', 'Font'),
                      options: ['manrope', 'inter', 'serif', 'system'],
                      // Per-option preview labels (the option key itself
                      // is the canonical value, the label is what the
                      // admin sees in the button).
                      labels: {
                        manrope: 'Manrope (default)',
                        inter: 'Inter',
                        serif: 'Serif',
                        system: 'Sistema',
                      },
                    },
                    {
                      key: 'border_radius',
                      label: t('design.borderRadius', 'Bordi arrotondati'),
                      options: ['sharp', 'standard', 'soft', 'pill'],
                      labels: {
                        sharp: 'Squadrati',
                        standard: 'Standard (default)',
                        soft: 'Morbidi',
                        pill: 'Pill',
                      },
                    },
                    {
                      key: 'density',
                      label: t('design.density', 'Densità'),
                      options: ['compact', 'standard', 'spacious'],
                      labels: {
                        compact: 'Compatta',
                        standard: 'Standard (default)',
                        spacious: 'Ampia',
                      },
                    },
                    {
                      key: 'header_style',
                      label: t('design.headerStyle', 'Stile header'),
                      options: ['solid', 'translucent', 'minimal'],
                      labels: {
                        solid: 'Pieno (default)',
                        translucent: 'Frosted glass',
                        minimal: 'Minimale',
                      },
                    },
                    {
                      key: 'card_style',
                      label: t('design.cardStyle', 'Stile card prodotti'),
                      options: ['shadow', 'flat', 'outlined'],
                      labels: {
                        shadow: 'Ombra (default)',
                        flat: 'Piatte',
                        outlined: 'Solo bordo',
                      },
                    },
                    // Logo refinement — 3 sizes is enough to bound
                    // the visual chaos; finer granularity is a
                    // decision-fatigue trap.
                    {
                      key: 'logo_height',
                      label: t('design.logoHeight', 'Dimensione logo'),
                      options: ['sm', 'md', 'lg'],
                      labels: {
                        sm: 'Piccolo (32px)',
                        md: 'Medio — default (40px)',
                        lg: 'Grande (56px)',
                      },
                    },
                    // 'contain' is the new safe default — wide and
                    // tall logos render undistorted. 'cover' is the
                    // legacy square-crop opt-in.
                    {
                      key: 'logo_fit',
                      label: t('design.logoFit', 'Adattamento logo'),
                      options: ['contain', 'cover'],
                      labels: {
                        contain: 'Mantieni proporzioni (default)',
                        cover: 'Riempi quadrato (crop)',
                      },
                    },
                  ].map(({ key, label, options, labels }) => {
                    const currentValue = editForm.design_tokens?.[key] || options[0];
                    return (
                      <div key={key}>
                        <Label className="text-xs">{label}</Label>
                        <div className="flex gap-2 mt-1 flex-wrap">
                          {options.map(opt => {
                            const selected = currentValue === opt;
                            return (
                              <button
                                key={opt}
                                type="button"
                                onClick={() => setEditForm(f => ({
                                  ...f,
                                  design_tokens: {
                                    ...(f.design_tokens || {}),
                                    [key]: opt,
                                  },
                                }))}
                                className={`px-3 py-1.5 rounded-md border text-xs font-medium transition-colors ${
                                  selected
                                    ? 'border-primary bg-primary/5 text-primary'
                                    : 'border-border text-muted-foreground hover:border-primary/30'
                                }`}
                              >
                                {labels[opt] || opt}
                              </button>
                            );
                          })}
                        </div>
                      </div>
                    );
                  })}

                  {/* Accent color — separate from the enums since it
                      takes a hex string. Defaults to "" (clears the
                      override so the storefront falls back to the
                      store's brand_color). */}
                  <div>
                    <Label className="text-xs">
                      {t('design.accentColor', 'Colore accento')}
                    </Label>
                    <div className="flex items-center gap-2 mt-1">
                      <Input
                        type="color"
                        value={editForm.design_tokens?.accent_color || '#000000'}
                        onChange={(e) => setEditForm(f => ({
                          ...f,
                          design_tokens: {
                            ...(f.design_tokens || {}),
                            accent_color: e.target.value,
                          },
                        }))}
                        className="w-16 h-10 p-1 cursor-pointer"
                      />
                      <Input
                        type="text"
                        placeholder="#FF5500"
                        value={editForm.design_tokens?.accent_color || ''}
                        maxLength={9}
                        onChange={(e) => setEditForm(f => ({
                          ...f,
                          design_tokens: {
                            ...(f.design_tokens || {}),
                            accent_color: e.target.value,
                          },
                        }))}
                        className="flex-1 font-mono text-xs uppercase"
                      />
                      {editForm.design_tokens?.accent_color && (
                        <button
                          type="button"
                          onClick={() => setEditForm(f => {
                            const tokens = { ...(f.design_tokens || {}) };
                            delete tokens.accent_color;
                            return { ...f, design_tokens: tokens };
                          })}
                          className="text-xs text-muted-foreground hover:text-foreground"
                        >
                          {t('design.clear', 'Reset')}
                        </button>
                      )}
                    </div>
                    <p className="text-[11px] text-muted-foreground mt-1">
                      {t('design.accentHint', 'Lascia vuoto per usare il colore del brand come accento.')}
                    </p>
                  </div>

                  {/* Show store name toggle.
                      A bool token can't fit the enum-pill pattern
                      above; render as a simple checkbox-style row.
                      Defaults to TRUE — non-customized stores keep
                      seeing the store name next to the logo. */}
                  <div className="flex items-start gap-3 pt-2 border-t border-border">
                    <input
                      type="checkbox"
                      id="show_store_name"
                      checked={editForm.design_tokens?.show_store_name !== false}
                      onChange={(e) => setEditForm(f => ({
                        ...f,
                        design_tokens: {
                          ...(f.design_tokens || {}),
                          show_store_name: e.target.checked,
                        },
                      }))}
                      className="mt-0.5 h-4 w-4 rounded border-border accent-primary"
                    />
                    <div className="flex-1">
                      <label htmlFor="show_store_name" className="text-xs font-medium cursor-pointer">
                        {t('design.showStoreName', 'Mostra il nome dello store accanto al logo')}
                      </label>
                      <p className="text-[11px] text-muted-foreground mt-0.5">
                        {t('design.showStoreNameHint', 'Disattiva se il tuo logo include già il nome del brand.')}
                      </p>
                    </div>
                  </div>
                </AccordionContent>
              </AccordionItem>

              {/* SEO */}
              <AccordionItem value="seo" className="border rounded-lg px-3">
                <AccordionTrigger className="text-sm font-semibold py-3 hover:no-underline">
                  {t('seo.title')}
                </AccordionTrigger>
                <AccordionContent className="space-y-3 pt-1">
                  <div>
                    <Label className="text-xs">{t('seo.seo_title')}</Label>
                    <Input value={editForm.seo_title || ''} onChange={e => setEditForm(f => ({ ...f, seo_title: e.target.value }))} placeholder={editForm.name || ''} maxLength={100} />
                  </div>
                  <div>
                    <Label className="text-xs">{t('seo.seo_desc')}</Label>
                    <Input value={editForm.seo_description || ''} onChange={e => setEditForm(f => ({ ...f, seo_description: e.target.value }))} placeholder={t('seo.seo_desc_placeholder')} maxLength={300} />
                  </div>
                </AccordionContent>
              </AccordionItem>

              {/* Email */}
              <AccordionItem value="email" className="border rounded-lg px-3">
                <AccordionTrigger className="text-sm font-semibold py-3 hover:no-underline">
                  {t('email.title')}
                </AccordionTrigger>
                <AccordionContent className="space-y-3 pt-1">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <Label className="text-xs">{t('email.sender_name')}</Label>
                      <Input value={editForm.sender_display_name || ''} onChange={e => setEditForm(f => ({ ...f, sender_display_name: e.target.value }))} placeholder={t('email.placeholder.sender')} />
                    </div>
                    <div>
                      <Label className="text-xs">{t('email.notifications')}</Label>
                      <Input type="email" value={editForm.notification_email || ''} onChange={e => setEditForm(f => ({ ...f, notification_email: e.target.value }))} placeholder={t('email.placeholder.notifications')} />
                    </div>
                  </div>
                  <div>
                    <Label className="text-xs">{t('email.reply_to')}</Label>
                    <Input type="email" value={editForm.reply_to_email || ''} onChange={e => setEditForm(f => ({ ...f, reply_to_email: e.target.value }))} placeholder={t('email.placeholder.reply_to')} />
                  </div>
                </AccordionContent>
              </AccordionItem>

              {/* Fulfillment */}
              <AccordionItem value="fulfillment" className="border rounded-lg px-3">
                <AccordionTrigger className="text-sm font-semibold py-3 hover:no-underline">
                  {t('fulfillment.title')}
                </AccordionTrigger>
                <AccordionContent className="pt-1">
                  <div className="flex gap-2">
                    {[{key: 'shipping', label: t('fulfillment.shipping')}, {key: 'local_pickup', label: t('fulfillment.pickup')}].map(({key, label}) => {
                      const active = (editForm.fulfillment_modes || []).includes(key);
                      return (
                        <button key={key} type="button"
                          onClick={() => setEditForm(f => {
                            const modes = f.fulfillment_modes || [];
                            const next = active ? modes.filter(m => m !== key) : [...modes, key];
                            return { ...f, fulfillment_modes: next.length > 0 ? next : modes };
                          })}
                          className={`flex-1 rounded-lg border px-3 py-2.5 text-xs font-medium transition-colors ${active ? 'border-primary bg-primary/5 text-primary' : 'border-border text-muted-foreground'}`}
                        >{label}</button>
                      );
                    })}
                  </div>
                </AccordionContent>
              </AccordionItem>

              {/* Storefront Languages
                  --------------------------------------------------------------
                  MVP-LIMIT: single-language picker. The data model
                  (`storefront_languages: List[str]`) supports multi natively,
                  but the admin UI is intentionally clamped to a 1-of-4 radio
                  pattern for the MVP rollout.

                  Behaviour:
                    • Click on a language → array becomes [lang] (single
                      element). Previously selected language deselected.
                    • The array is NEVER allowed to be empty in this UI.
                    • Legacy stores (created before this clamp) may have
                      multiple entries — a banner notifies the admin that
                      saving will reduce them to one.

                  Future (multi-lang enablement):
                    Reverting this block to a multi-toggle chip pattern
                    enables the multi-language flow without any other code
                    changes (resolver, switcher, persistence are already
                    multi-ready). Reference commit for the multi version
                    lives in `git log` of this file. */}
              <AccordionItem value="languages" className="border rounded-lg px-3">
                <AccordionTrigger className="text-sm font-semibold py-3 hover:no-underline">
                  {t('languages.title')}
                </AccordionTrigger>
                <AccordionContent className="space-y-3 pt-1">
                  <p className="text-xs text-muted-foreground">{t('languages.singleSelectHint')}</p>

                  {/* Legacy banner — only renders when the store currently
                      has 2+ languages saved (configured before the MVP
                      single-select clamp). Surfaces the soft-downgrade
                      warning so the admin understands that picking a new
                      language collapses the array. */}
                  {(editForm.storefront_languages || []).length > 1 && (
                    <div className="rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-xs text-amber-900">
                      <p className="font-semibold mb-0.5">
                        {t('languages.legacyBannerTitle')}
                      </p>
                      <p className="leading-relaxed">
                        {t('languages.legacyBannerBody', {
                          count: editForm.storefront_languages.length,
                          langs: editForm.storefront_languages
                            .map(l => t(`languages.${l}`))
                            .join(', '),
                        })}
                      </p>
                    </div>
                  )}

                  {/* Radio-style chip group — exactly one selected at any
                      time. Picking a chip overwrites the array with
                      [picked] regardless of previous state, including
                      multi-language legacy values. Disabled state is
                      removed (compared to the old multi-select) because
                      with single-select there's never a "last one" to
                      protect from deselection. */}
                  <div className="flex gap-2 flex-wrap" role="radiogroup" aria-label={t('languages.title')}>
                    {['it', 'en', 'de', 'fr'].map(lang => {
                      const currentArr = editForm.storefront_languages || ['it'];
                      const selected = currentArr[0] === lang && currentArr.length === 1;
                      const wasInLegacy = currentArr.length > 1 && currentArr.includes(lang);
                      return (
                        <button
                          key={lang}
                          type="button"
                          role="radio"
                          aria-checked={selected}
                          onClick={() => setEditForm(f => ({
                            ...f,
                            // Single-element array always — collapses any
                            // prior legacy multi-config to [lang].
                            storefront_languages: [lang],
                          }))}
                          className={`px-3 py-2 rounded-lg border text-xs font-medium transition-colors ${
                            selected
                              ? 'border-primary bg-primary/5 text-primary'
                              : wasInLegacy
                                ? 'border-amber-300 bg-amber-50/50 text-amber-900 hover:border-amber-400'
                                : 'border-border text-muted-foreground hover:border-primary/30'
                          }`}
                        >
                          {t(`languages.${lang}`)}
                        </button>
                      );
                    })}
                  </div>
                </AccordionContent>
              </AccordionItem>

              {/* Phase 8.4 — Custom navigation links section.
                  Lets the merchant add up to 3 links to the storefront
                  header strip (next to the category pills). Labels are
                  per-language and required for every active store
                  locale; the helper below derives the required locale
                  set from `editForm.storefront_languages` so the
                  validation matches the backend rule exactly. */}
              <AccordionItem value="custom_nav" className="border rounded-lg px-3">
                <AccordionTrigger className="text-sm font-semibold py-3 hover:no-underline">
                  {t('customNav.title', 'Menu personalizzato')}
                </AccordionTrigger>
                <AccordionContent className="space-y-3 pt-1">
                  <p className="text-xs text-muted-foreground">
                    {t('customNav.hint', 'Aggiungi fino a 3 link al menu dello store. Possono puntare a una pagina esterna (sito personale, blog) o a un percorso interno (/about).')}
                  </p>

                  {(editForm.custom_nav_links || []).map((link, idx) => {
                    const activeLangs = editForm.storefront_languages || ['it'];
                    return (
                      <div key={link.id || idx} className="rounded-lg border border-border p-3 space-y-2">
                        <div className="flex items-center justify-between gap-2">
                          <span className="text-xs font-semibold text-muted-foreground">
                            {t('customNav.linkN', { n: idx + 1, defaultValue: 'Link {{n}}' })}
                          </span>
                          <button
                            type="button"
                            onClick={() => setEditForm(f => ({
                              ...f,
                              custom_nav_links: (f.custom_nav_links || []).filter((_, i) => i !== idx),
                            }))}
                            className="text-xs text-red-600 hover:text-red-700 font-medium"
                          >
                            {t('customNav.remove', 'Rimuovi')}
                          </button>
                        </div>

                        {/* URL */}
                        <div>
                          <Label className="text-xs">{t('customNav.urlLabel', 'URL')}</Label>
                          <Input
                            type="text"
                            placeholder="https://example.com  oppure  /about"
                            value={link.url || ''}
                            maxLength={2000}
                            onChange={(e) => setEditForm(f => ({
                              ...f,
                              custom_nav_links: (f.custom_nav_links || []).map((l, i) =>
                                i === idx ? { ...l, url: e.target.value } : l,
                              ),
                            }))}
                            className="mt-1"
                          />
                        </div>

                        {/* Target */}
                        <div>
                          <Label className="text-xs">{t('customNav.targetLabel', 'Apertura')}</Label>
                          <div className="flex gap-2 mt-1">
                            {['self', 'blank'].map(target => {
                              const selected = (link.target || 'self') === target;
                              return (
                                <button
                                  key={target}
                                  type="button"
                                  onClick={() => setEditForm(f => ({
                                    ...f,
                                    custom_nav_links: (f.custom_nav_links || []).map((l, i) =>
                                      i === idx ? { ...l, target } : l,
                                    ),
                                  }))}
                                  className={`px-3 py-1.5 rounded-md border text-xs font-medium transition-colors ${
                                    selected
                                      ? 'border-primary bg-primary/5 text-primary'
                                      : 'border-border text-muted-foreground hover:border-primary/30'
                                  }`}
                                >
                                  {target === 'self'
                                    ? t('customNav.targetSelf', 'Stessa scheda')
                                    : t('customNav.targetBlank', 'Nuova scheda')}
                                </button>
                              );
                            })}
                          </div>
                        </div>

                        {/* Per-language labels.
                            Renders one input PER ACTIVE storefront_language
                            (1 input for single-locale stores, up to 4 for
                            all-locale stores). The backend validator
                            requires a non-empty label for every active
                            locale — see decision 5. */}
                        <div className="space-y-2">
                          <Label className="text-xs">{t('customNav.labelHeader', 'Etichetta (per lingua)')}</Label>
                          {activeLangs.map(lang => (
                            <div key={lang} className="flex items-center gap-2">
                              <span className="text-[10px] font-bold uppercase text-muted-foreground w-6 shrink-0">
                                {lang}
                              </span>
                              <Input
                                type="text"
                                placeholder={t('customNav.labelPlaceholder', 'Es: Chi siamo')}
                                value={(link.label_i18n && link.label_i18n[lang]) || ''}
                                maxLength={80}
                                onChange={(e) => setEditForm(f => ({
                                  ...f,
                                  custom_nav_links: (f.custom_nav_links || []).map((l, i) =>
                                    i === idx
                                      ? {
                                          ...l,
                                          label_i18n: {
                                            ...(l.label_i18n || {}),
                                            [lang]: e.target.value,
                                          },
                                        }
                                      : l,
                                  ),
                                }))}
                                className="flex-1"
                              />
                            </div>
                          ))}
                        </div>
                      </div>
                    );
                  })}

                  {/* Add-link CTA. Disabled when at the cap (3). */}
                  {(editForm.custom_nav_links || []).length < 3 ? (
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => setEditForm(f => ({
                        ...f,
                        custom_nav_links: [
                          ...(f.custom_nav_links || []),
                          {
                            // No id — backend will assign on save.
                            label_i18n: {},
                            url: '',
                            target: 'self',
                            sort_order: (f.custom_nav_links || []).length,
                          },
                        ],
                      }))}
                      className="w-full"
                    >
                      + {t('customNav.add', 'Aggiungi link')}
                    </Button>
                  ) : (
                    <p className="text-xs text-muted-foreground text-center py-2">
                      {t('customNav.maxReached', 'Hai raggiunto il numero massimo di link (3).')}
                    </p>
                  )}
                </AccordionContent>
              </AccordionItem>

              {/* Visibility */}
              <AccordionItem value="visibility" className="border rounded-lg px-3">
                <AccordionTrigger className="text-sm font-semibold py-3 hover:no-underline">
                  {t('create.visibility')}
                </AccordionTrigger>
                <AccordionContent className="pt-1">
                  <div className="grid grid-cols-3 gap-2">
                    {Object.entries(VISIBILITY_CONFIG).map(([key, cfg]) => {
                      const Icon = cfg.icon;
                      return (
                        <button
                          key={key}
                          type="button"
                          onClick={() => setEditForm(f => ({ ...f, visibility: key }))}
                          className={`flex flex-col items-center gap-1 rounded-lg border p-3 text-xs transition-colors ${
                            editForm.visibility === key ? 'border-primary bg-primary/5 text-primary font-medium' : 'border-border text-muted-foreground hover:border-primary/30'
                          }`}
                        >
                          <Icon className="h-4 w-4" />
                          {t(cfg.labelKey)}
                        </button>
                      );
                    })}
                  </div>
                </AccordionContent>
              </AccordionItem>
            </Accordion>
          </div>

          <ResponsiveDialogFooter>
            <Button variant="outline" onClick={() => setEditStore(null)} className="w-full sm:w-auto">
              {t('create.cancel')}
            </Button>
            <Button
              disabled={saving || !editForm.name?.trim()}
              onClick={handleSaveEdit}
              className="gap-1.5 w-full sm:w-auto"
            >
              {saving ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <CheckCircle2 className="h-3.5 w-3.5" />}
              {t('edit.save')}
            </Button>
          </ResponsiveDialogFooter>
        </ResponsiveDialogContent>
      </ResponsiveDialog>

      {/* Shipping configuration dialog — open per-store. */}
      <ShippingDialog
        open={!!shippingStore}
        store={shippingStore}
        onClose={() => setShippingStore(null)}
      />

      {/* Wave GDPR-Commerce CG-3 — Privacy + T&C editor.
          Opens via the "Privacy & GDPR" action in the per-store menu.
          The dialog handles load / wizard / editor / publish flows
          internally and only emits onClose back to the page. */}
      <MerchantLegalDialog
        open={!!legalStore}
        store={legalStore}
        onClose={() => setLegalStore(null)}
      />

      {/* Org-level branding ("Impostazioni globali") — opens from the
          subheader action. Defaults that cascade to every store of
          the org. See OrgBrandingDialog for the cascade UX. */}
      <OrgBrandingDialog
        open={globalSettingsOpen}
        onClose={handleGlobalSettingsClose}
      />

      {/* Track E Step 2.3 — Share modal (hosted link + embed code).
          Opens via the "Condividi" inline action in StoreCard.
          Loads embed-info dal backend (snippet auto-generato + URL +
          allowed_origins management). Coerente con il pattern degli
          altri modal (state = null → closed, state = store → open). */}
      <ShareStoreModal
        store={shareStore}
        open={!!shareStore}
        onOpenChange={(open) => { if (!open) setShareStore(null); }}
      />
    </AppLayout>
  );
}
