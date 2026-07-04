import React, { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate, Link } from 'react-router-dom';
import { AppLayout, Header } from '../../components/Layout';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Store, Loader2, CheckCircle2, AlertTriangle, Circle, Truck, MapPin, Globe, EyeOff, Sparkles, RotateCcw, Package, ShoppingBag } from 'lucide-react';
import { storeSettingsAPI } from '../../api/storeSettings';
import { useAuth } from '../../context/AuthContext';
import { toast } from 'sonner';

/* ── Readiness Section ─────────────────────────────────────────────────── */

const READINESS_GROUPS = ['storefront', 'trust', 'commerce'];

// Map readiness check keys to action targets.
// type: 'scroll' = in-page anchor, 'link' = navigate to another page
const CHECK_ACTION_MAP = {
  public_slug: { type: 'link', target: '/stores' },  // slug now managed per-store
  display_name: { type: 'scroll', target: 'section-identity' },
  contact_email: { type: 'scroll', target: 'section-identity' },
  notification_email: { type: 'scroll', target: 'section-notifications' },
  reply_to_email: { type: 'scroll', target: 'section-email' },
  payment_provider: { type: 'link', target: '/settings' },
  publishable_offer: { type: 'link', target: '/products' },
};

function ReadinessSection({ readiness, t, navigate }) {
  if (!readiness) return null;

  const overallColors = {
    ready: 'bg-emerald-100 text-emerald-700',
    needs_setup: 'bg-amber-100 text-amber-700',
    blocked: 'bg-red-100 text-red-700',
  };

  const grouped = {};
  for (const check of readiness.checks) {
    const g = check.group || 'commerce';
    if (!grouped[g]) grouped[g] = [];
    grouped[g].push(check);
  }

  const scrollTo = (sectionId) => {
    const el = document.getElementById(sectionId);
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">{t('readiness.title')}</CardTitle>
          <Badge className={`text-xs ${overallColors[readiness.overall] || overallColors.blocked}`}>
            {t(`readiness.overall_${readiness.overall}`)}
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {READINESS_GROUPS.filter(g => grouped[g]?.length).map(group => (
            <div key={group}>
              <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground/60 mb-1.5">
                {t(`readiness.group.${group}`)}
              </p>
              <div className="space-y-1.5">
                {grouped[group].map(check => {
                  const action = CHECK_ACTION_MAP[check.key];
                  const canFix = check.status !== 'ok' && action;
                  const handleFix = () => {
                    if (!action) return;
                    if (action.type === 'scroll') scrollTo(action.target);
                    else if (action.type === 'link' && navigate) navigate(action.target);
                  };
                  return (
                    <div key={check.key} className="flex items-center justify-between text-sm">
                      <span className="text-muted-foreground">{t(`readiness.check.${check.key}`)}</span>
                      <div className="flex items-center gap-2">
                        {check.status === 'ok' ? (
                          <><CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" /><span className="text-xs text-emerald-600">{t('readiness.status_ok')}</span></>
                        ) : check.blocking ? (
                          <><AlertTriangle className="h-3.5 w-3.5 text-red-500" /><span className="text-xs text-red-600">{t('readiness.status_blocking')}</span></>
                        ) : (
                          <><Circle className="h-3.5 w-3.5 text-amber-400" /><span className="text-xs text-amber-600">{t('readiness.status_missing')}</span></>
                        )}
                        {canFix && (
                          <button
                            onClick={handleFix}
                            className="text-[10px] text-primary hover:underline font-medium"
                          >
                            {t('readiness.action_configure')}
                          </button>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

/* ── Main Page ─────────────────────────────────────────────────────────── */

export default function StoreSettingsPage() {
  const { t } = useTranslation('store_settings');
  const navigate = useNavigate();
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  // AI setup moved to /setup page — this page is for store management only
  const [form, setForm] = useState({
    display_name: '',
    contact_email: '',
    contact_phone: '',
    store_description: '',
    notification_email: '',
    sender_display_name: '',
    reply_to_email: '',
    fulfillment_modes: ['shipping'],
    // Branding (v13.0)
    logo_url: '',
    brand_color: '',
    brand_color_text: '',
    // SEO (v13.0)
    seo_title: '',
    seo_description: '',
  });

  // Fase 2 Track F — Setup Wizard deep-link: when arriving with a #section
  // hash in the URL (e.g. /store/settings#section-identity from a wizard
  // CTA), scroll the matching anchor into view after first render. Pure
  // additive: no hash → no behavioural change. Uses requestAnimationFrame
  // to wait for the page layout to stabilise before scrolling.
  useEffect(() => {
    if (typeof window === 'undefined' || !window.location.hash) return;
    const targetId = window.location.hash.slice(1);
    if (!targetId) return;
    // Wait one frame so the cards have rendered.
    const raf = requestAnimationFrame(() => {
      const el = document.getElementById(targetId);
      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
    return () => cancelAnimationFrame(raf);
  }, []);  // run once on mount only

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await storeSettingsAPI.get();
      setData(res.data);
      const s = res.data?.settings || {};
      setForm({
        display_name: s.display_name || '',
        contact_email: s.contact_email || '',
        contact_phone: s.contact_phone || '',
        notification_email: s.notification_email || '',
        sender_display_name: s.sender_display_name || '',
        store_description: s.store_description || '',
        reply_to_email: s.reply_to_email || '',
        fulfillment_modes: s.fulfillment_modes || ['shipping'],
        logo_url: s.logo_url || '',
        brand_color: s.brand_color || '',
        brand_color_text: s.brand_color_text || '',
        seo_title: s.seo_title || '',
        seo_description: s.seo_description || '',
      });
    } catch { /* empty */ }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);


  const handleSave = async () => {
    setSaving(true);
    try {
      const payload = {};
      Object.entries(form).forEach(([k, v]) => {
        if (Array.isArray(v)) {
          payload[k] = v;
        } else {
          payload[k] = typeof v === 'string' ? (v.trim() || null) : v;
        }
      });
      const res = await storeSettingsAPI.update(payload);
      setData(res.data);
      toast.success(t('toast.saved'), {
        action: { label: t('toast.back_to_setup', { defaultValue: 'Torna al setup' }), onClick: () => navigate('/dashboard') },
      });
    } catch (err) {
      toast.error(err?.response?.data?.detail || t('toast.error'));
    } finally { setSaving(false); }
  };

  if (loading) {
    return (
      <AppLayout>
        <Header title={t('page.title')} subtitle={t('page.subtitle')} />
        <div className="flex justify-center py-16"><Loader2 className="h-6 w-6 animate-spin text-muted-foreground" /></div>
      </AppLayout>
    );
  }

  return (
    <AppLayout>
      <Header title={t('page.title')} subtitle={t('page.subtitle')}>
        <Button size="sm" onClick={handleSave} disabled={saving} className="gap-1.5">
          {saving ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Store className="h-3.5 w-3.5" />}
          {saving ? t('actions.saving') : t('actions.save')}
        </Button>
      </Header>

      <div className="p-4 md:p-6 max-w-3xl mx-auto space-y-6">
        {/*
          Phase 6 (Store consolidation) — deprecation banner.

          This page writes to the legacy `PATCH /store-settings`
          endpoint which is on a sunset path (target: 2026-05-31).
          The new admin UI on `/stores` is the source of truth for
          multi-store environments and the only place where features
          like per-store branding, multi-language, fulfillment_modes,
          and the publish toggle land first.

          For Phase 6 the legacy endpoint stays fully functional —
          every save here is automatically mirrored to the org's
          default store via dual-write at the backend (see
          routers/store_settings._dual_write_to_default_store). So
          the merchant doesn't have to migrate immediately; the
          banner just signals that the new "Store" page is the
          go-to surface going forward.

          NOT a blocker. Not destructive. Just a heads-up.
        */}
        <Card className="border-amber-200 bg-amber-50">
          <CardContent className="py-3 px-4">
            <div className="flex items-start gap-3">
              <AlertTriangle className="h-4 w-4 text-amber-600 mt-0.5 shrink-0" />
              <div className="flex-1 text-sm">
                <p className="font-medium text-amber-900">
                  {t('deprecation.title', 'Questa pagina sarà sostituita')}
                </p>
                <p className="text-amber-800 mt-0.5">
                  {t(
                    'deprecation.body',
                    'Le configurazioni store si stanno spostando sulla pagina “Store”, dove puoi gestire branding, lingue e modalità di evasione per ogni punto vendita. Le modifiche fatte qui restano sincronizzate.',
                  )}
                </p>
                <Link
                  to="/stores"
                  className="inline-flex items-center gap-1 mt-1.5 text-amber-900 font-medium underline-offset-2 hover:underline"
                >
                  {t('deprecation.cta', 'Apri la pagina Store')}
                  <span aria-hidden>→</span>
                </Link>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Setup hint card removed in Fase 2 Track F Step 9. The
            previous link to /setup pointed at a dedicated wizard page
            that no longer exists — onboarding now lives as the
            SetupWizardWidget on the dashboard. New merchants discover
            the wizard there automatically; the old hint card here was
            duplicated guidance. */}
        {/* Readiness */}
        <ReadinessSection readiness={data?.readiness} t={t} navigate={navigate} />

        {/* Publish Control (v11.0) */}
        {data?.readiness && (() => {
          const isPublished = !!data.readiness.is_storefront_published;
          const isBlocked = data.readiness.overall === 'blocked';
          const canPublish = !isBlocked && !isPublished;

          const handlePublish = async () => {
            if (!window.confirm(t('publish.publish_confirm'))) return;
            try {
              const res = await storeSettingsAPI.update({ is_storefront_published: true });
              setData(res.data);
              toast.success(t('publish.published_badge'));
            } catch (err) {
              toast.error(err?.response?.data?.detail || t('toast.error'));
            }
          };

          const handleUnpublish = async () => {
            if (!window.confirm(t('publish.unpublish_confirm'))) return;
            try {
              const res = await storeSettingsAPI.update({ is_storefront_published: false });
              setData(res.data);
              toast.success(t('publish.unpublished_badge'));
            } catch (err) {
              toast.error(err?.response?.data?.detail || t('toast.error'));
            }
          };

          return (
            <Card className={isPublished ? 'border-emerald-200' : ''}>
              <CardContent className="py-4 px-5">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    {isPublished ? (
                      <Globe className="h-5 w-5 text-emerald-600" />
                    ) : (
                      <EyeOff className="h-5 w-5 text-muted-foreground" />
                    )}
                    <div>
                      <h3 className="text-sm font-semibold">{t('publish.title')}</h3>
                      <p className="text-xs text-muted-foreground">
                        {isPublished ? t('publish.published_hint')
                          : isBlocked ? t('publish.blocked_hint')
                          : t('publish.ready_hint')}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge className={isPublished ? 'bg-emerald-100 text-emerald-700 text-xs' : 'bg-slate-100 text-slate-600 text-xs'}>
                      {isPublished ? t('publish.published_badge') : t('publish.unpublished_badge')}
                    </Badge>
                    {canPublish && (
                      <Button size="sm" onClick={handlePublish} className="gap-1.5">
                        <Globe className="h-3.5 w-3.5" /> {t('publish.publish_btn')}
                      </Button>
                    )}
                    {isPublished && (
                      <Button variant="outline" size="sm" onClick={handleUnpublish} className="gap-1.5 text-muted-foreground">
                        <EyeOff className="h-3.5 w-3.5" /> {t('publish.unpublish_btn')}
                      </Button>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })()}

        {/* Business Identity */}
        <Card id="section-identity">
          <CardHeader><CardTitle className="text-base">{t('identity.title')}</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label>{t('identity.display_name')} <span className="text-red-500">*</span></Label>
              <Input value={form.display_name} onChange={e => setForm(f => ({ ...f, display_name: e.target.value }))} placeholder={data?.org_name || ''} />
              <p className="text-[11px] text-muted-foreground mt-0.5">{t('identity.display_name_hint')} · <span className="text-red-500/70">{t('identity.required_for_publish')}</span></p>
            </div>
            <div>
              <Label>{t('identity.store_description')}</Label>
              <textarea
                value={form.store_description}
                onChange={e => setForm(f => ({ ...f, store_description: e.target.value }))}
                maxLength={500}
                rows={3}
                placeholder={t('identity.store_description_placeholder')}
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              />
              <p className="text-[11px] text-muted-foreground mt-0.5">{t('identity.store_description_hint')}</p>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label>{t('identity.contact_email')} <span className="text-red-500">*</span></Label>
                <Input type="email" value={form.contact_email} onChange={e => setForm(f => ({ ...f, contact_email: e.target.value }))} />
                <p className="text-[11px] text-red-500/70 mt-0.5">{t('identity.required_for_publish')}</p>
              </div>
              <div>
                <Label>{t('identity.contact_phone')}</Label>
                <Input type="tel" value={form.contact_phone} onChange={e => setForm(f => ({ ...f, contact_phone: e.target.value }))} />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Notifications */}
        <Card id="section-notifications">
          <CardHeader><CardTitle className="text-base">{t('notifications.title')}</CardTitle></CardHeader>
          <CardContent>
            <div>
              <Label>{t('notifications.notification_email')}</Label>
              <Input type="email" value={form.notification_email} onChange={e => setForm(f => ({ ...f, notification_email: e.target.value }))} />
              <p className="text-[11px] text-muted-foreground mt-0.5">{t('notifications.notification_email_hint')}</p>
            </div>
          </CardContent>
        </Card>

        {/* Customer Emails */}
        <Card id="section-email">
          <CardHeader><CardTitle className="text-base">{t('email.title')}</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            {/* Platform managed explanation */}
            <div className="rounded-lg bg-muted/50 border border-border/50 p-3 text-xs text-muted-foreground space-y-1">
              <p className="font-medium text-foreground/80">{t('email.platform_managed_title')}</p>
              <p>{t('email.platform_managed_desc')}</p>
            </div>
            <div>
              <Label>{t('email.sender_display_name')}</Label>
              <Input value={form.sender_display_name} onChange={e => setForm(f => ({ ...f, sender_display_name: e.target.value }))} placeholder={data?.org_name || ''} />
              <p className="text-[11px] text-muted-foreground mt-0.5">{t('email.sender_display_name_hint')}</p>
            </div>
            <div>
              <Label>{t('email.reply_to_email')}</Label>
              <Input type="email" value={form.reply_to_email} onChange={e => setForm(f => ({ ...f, reply_to_email: e.target.value }))} />
              <p className="text-[11px] text-muted-foreground mt-0.5">{t('email.reply_to_email_hint')}</p>
            </div>
            {/* Email preview */}
            <div className="rounded-lg bg-muted/30 border border-dashed border-border p-3 text-xs space-y-1.5">
              <p className="font-medium text-muted-foreground text-[10px] uppercase tracking-wider mb-1">{t('email.preview_title')}</p>
              <p><span className="text-muted-foreground">{t('email.preview_from')}:</span> <span className="font-medium">{form.sender_display_name || data?.org_name || 'AFianco'}</span> <span className="text-muted-foreground/60">via AFianco</span></p>
              <p><span className="text-muted-foreground">{t('email.preview_reply_to')}:</span> <span className="font-medium">{form.reply_to_email || <span className="text-muted-foreground/60 italic">{t('email.preview_not_configured')}</span>}</span></p>
              <p><span className="text-muted-foreground">{t('email.preview_notifications')}:</span> <span className="font-medium">{form.notification_email || <span className="text-muted-foreground/60 italic">{t('email.preview_admin_fallback')}</span>}</span></p>
            </div>
          </CardContent>
        </Card>

        {/* Fulfillment (v10.0) */}
        <Card>
          <CardHeader><CardTitle className="text-base">{t('fulfillment.title')}</CardTitle></CardHeader>
          <CardContent>
            <div>
              <Label>{t('fulfillment.modes_label')}</Label>
              <p className="text-[11px] text-muted-foreground mb-2">{t('fulfillment.modes_hint')}</p>
              <div className="flex gap-3">
                {[
                  { key: 'shipping', icon: Truck, label: t('fulfillment.mode_shipping') },
                  { key: 'local_pickup', icon: MapPin, label: t('fulfillment.mode_local_pickup') },
                ].map(({ key, icon: Icon, label }) => {
                  const active = (form.fulfillment_modes || []).includes(key);
                  return (
                    <button
                      key={key}
                      type="button"
                      onClick={() => {
                        setForm(f => {
                          const current = f.fulfillment_modes || [];
                          const next = active
                            ? current.filter(m => m !== key)
                            : [...current, key];
                          // Must have at least one mode
                          return { ...f, fulfillment_modes: next.length > 0 ? next : current };
                        });
                      }}
                      className={`flex items-center gap-2 rounded-lg border px-4 py-2.5 text-sm font-medium transition-colors ${
                        active
                          ? 'border-primary bg-primary/5 text-primary'
                          : 'border-border text-muted-foreground hover:border-primary/30'
                      }`}
                    >
                      <Icon className="h-4 w-4" />
                      {label}
                      {active && <CheckCircle2 className="h-3.5 w-3.5 text-primary" />}
                    </button>
                  );
                })}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Branding & SEO redirect */}
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium">Branding, SEO & Email per store</p>
                <p className="text-xs text-muted-foreground">Logo, colori, SEO e configurazione email si impostano per ogni singolo store.</p>
              </div>
              <a href="/stores" className="text-xs text-primary hover:underline font-medium">
                Vai a I miei Store →
              </a>
            </div>
          </CardContent>
        </Card>
      </div>
    </AppLayout>
  );
}
