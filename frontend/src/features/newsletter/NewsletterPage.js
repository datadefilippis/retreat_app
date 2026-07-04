import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { AppLayout, Header } from '../../components/Layout';
import { PageSubheader } from '../../components/PageSubheader';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Textarea } from '../../components/ui/textarea';
import { Checkbox } from '../../components/ui/checkbox';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription,
} from '../../components/ui/dialog';
import {
  Plus, Trash2, Loader2, Mail, RefreshCw, Code2, Users, Copy, Pencil,
} from 'lucide-react';
import FieldEditorList from '../events/components/FieldEditorList';
import { pruneFieldConfigs } from '../events/components/fieldConfigUtils';
import { newsletterAPI, buildNewsletterSnippet } from '../../api/newsletter';
import { storesAPI, storeLegalAPI } from '../../api/stores';
import MerchantLegalDialog from '../stores/components/MerchantLegalDialog';
import NewsletterFormPreview from './components/NewsletterFormPreview';
import { toast } from 'sonner';

const NL_FIELD_TYPES = ['text', 'textarea', 'number', 'email', 'tel', 'checkbox'];

const EMPTY_FORM = {
  name: '',
  collect_name: false,
  collect_phone: false,
  privacy_required: true,
  consent_text: '',
  success_message: '',
  field_configs: [],
  allowed_origins: '', // textarea: un origin per riga
  // F8 — layout
  layout: 'vertical',
  // F7 — colori
  custom_colors: false,
  primary_color: '#4b72ce',
  primary_text_color: '#ffffff',
  // F7 — privacy policy
  privacy_mode: 'none', // 'none' | 'store' | 'custom'
  privacy_store_id: '',
  privacy_custom_url: '',
};

export default function NewsletterPage() {
  const { t } = useTranslation('newsletter');
  const [forms, setForms] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [embedTarget, setEmbedTarget] = useState(null);
  const [subsTarget, setSubsTarget] = useState(null);
  // F7 — stores dell'org (per linkare la privacy) + dialog legale riusato.
  const [stores, setStores] = useState([]);
  const [legalStore, setLegalStore] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await newsletterAPI.list();
      setForms(res.data || []);
    } catch { /* empty */ }
    finally { setLoading(false); }
  }, []);

  const loadStores = useCallback(async () => {
    try {
      const res = await storesAPI.list();
      // GET /stores ritorna { stores: [...], total }, non un array nudo.
      const list = Array.isArray(res.data) ? res.data : (res.data?.stores || []);
      setStores(list);
    } catch { setStores([]); }
  }, []);

  useEffect(() => { load(); loadStores(); }, [load, loadStores]);

  // F7 — config per l'anteprima live (riflette lo stato non salvato del form).
  const previewConfig = useMemo(() => {
    const resolvePrivacyUrl = () => {
      if (form.privacy_mode === 'custom') {
        const u = (form.privacy_custom_url || '').trim();
        if (!u) return null;
        // Senza schema → assoluto https:// (altrimenti link relativo errato).
        return /^https?:\/\//i.test(u) ? u : `https://${u}`;
      }
      if (form.privacy_mode === 'store' && form.privacy_store_id) {
        const st = stores.find((s) => s.id === form.privacy_store_id);
        if (st?.slug) return `${window.location.origin}/s/${st.slug}/privacy`;
      }
      return null;
    };
    return {
      id: 'preview',
      name: form.name || t('dialog.name_ph'),
      collect_name: form.collect_name,
      collect_phone: form.collect_phone,
      field_configs: (form.field_configs || []).filter((f) => f.label && f.label.trim()),
      consent_text: form.consent_text || null,
      privacy_required: form.privacy_required,
      success_message: form.success_message || null,
      layout: form.layout,
      theme: form.custom_colors
        ? { primary_color: form.primary_color || null, primary_text_color: form.primary_text_color || null }
        : null,
      privacy_policy_url: resolvePrivacyUrl(),
    };
  }, [form, stores, t]);

  const openCreate = () => {
    setEditingId(null);
    setForm(EMPTY_FORM);
    setDialogOpen(true);
  };

  const openEdit = (f) => {
    setEditingId(f.id);
    setForm({
      name: f.name || '',
      collect_name: !!f.collect_name,
      collect_phone: !!f.collect_phone,
      privacy_required: f.privacy_required !== false,
      consent_text: f.consent_text || '',
      success_message: f.success_message || '',
      field_configs: f.field_configs || [],
      allowed_origins: (f.allowed_origins || []).join('\n'),
      layout: f.layout || 'vertical',
      custom_colors: !!f.theme,
      primary_color: f.theme?.primary_color || '#4b72ce',
      primary_text_color: f.theme?.primary_text_color || '#ffffff',
      privacy_mode: f.privacy_mode || 'none',
      privacy_store_id: f.privacy_store_id || '',
      privacy_custom_url: f.privacy_custom_url || '',
    });
    setDialogOpen(true);
  };

  const parseOrigins = (raw) =>
    raw.split('\n').map((s) => s.trim()).filter(Boolean);

  const handleSave = async () => {
    if (!form.name.trim()) {
      toast.error(t('toast.name_required'));
      return;
    }
    setSaving(true);
    const origins = parseOrigins(form.allowed_origins);
    const payload = {
      name: form.name.trim(),
      collect_name: form.collect_name,
      collect_phone: form.collect_phone,
      privacy_required: form.privacy_required,
      consent_text: form.consent_text.trim() || null,
      success_message: form.success_message.trim() || null,
      field_configs: pruneFieldConfigs(form.field_configs),
      layout: form.layout,
      // F7 — colori (solo se personalizzati) + privacy
      theme: form.custom_colors
        ? { primary_color: form.primary_color || null, primary_text_color: form.primary_text_color || null }
        : null,
      privacy_mode: form.privacy_mode,
      privacy_store_id: form.privacy_mode === 'store' ? (form.privacy_store_id || null) : null,
      privacy_custom_url: form.privacy_mode === 'custom' ? (form.privacy_custom_url.trim() || null) : null,
    };
    try {
      if (editingId) {
        await newsletterAPI.update(editingId, payload);
        await newsletterAPI.updateOrigins(editingId, origins);
        toast.success(t('toast.updated'));
      } else {
        await newsletterAPI.create({ ...payload, allowed_origins: origins });
        toast.success(t('toast.created'));
      }
      setDialogOpen(false);
      load();
    } catch (err) {
      toast.error(err?.response?.data?.detail || t('toast.save_error'));
    } finally { setSaving(false); }
  };

  const handleToggle = async (f) => {
    try {
      await newsletterAPI.update(f.id, { is_active: !f.is_active });
      setForms((prev) => prev.map((x) => (x.id === f.id ? { ...x, is_active: !x.is_active } : x)));
    } catch { toast.error(t('toast.error')); }
  };

  const handleDelete = async (f) => {
    if (!window.confirm(t('confirm_delete', { name: f.name }))) return;
    try {
      await newsletterAPI.delete(f.id);
      setForms((prev) => prev.filter((x) => x.id !== f.id));
      toast.success(t('toast.deleted'));
    } catch { toast.error(t('toast.error')); }
  };

  return (
    <AppLayout>
      <Header title={t('title')} subtitle={t('subtitle')} />
      <PageSubheader
        actions={
          <>
            <Button variant="outline" size="sm" onClick={load} aria-label={t('refresh')}>
              <RefreshCw className="h-4 w-4" />
            </Button>
            <Button size="sm" onClick={openCreate} className="gap-1.5">
              <Plus className="h-4 w-4" /> {t('new_form')}
            </Button>
          </>
        }
      />

      <div className="p-4 md:p-6 max-w-4xl mx-auto space-y-4">
        {loading ? (
          <div className="flex justify-center py-16"><Loader2 className="h-6 w-6 animate-spin text-muted-foreground" /></div>
        ) : forms.length === 0 ? (
          <div className="text-center py-16 space-y-3">
            <Mail className="h-12 w-12 text-muted-foreground/40 mx-auto" />
            <h3 className="font-semibold">{t('empty_title')}</h3>
            <p className="text-sm text-muted-foreground">{t('empty_subtitle')}</p>
            <Button onClick={openCreate}><Plus className="h-4 w-4 mr-2" /> {t('new_form')}</Button>
          </div>
        ) : (
          <div className="space-y-2">
            {forms.map((f) => (
              <div key={f.id} className={`rounded-xl border p-4 flex items-center justify-between gap-3 ${!f.is_active ? 'opacity-50' : ''}`}>
                <div className="space-y-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-semibold text-sm truncate">{f.name}</span>
                    {!f.is_active && <Badge className="text-[10px] bg-gray-100 text-gray-500">{t('badge.inactive')}</Badge>}
                    {(f.allowed_origins || []).length === 0 && (
                      <Badge className="text-[10px] bg-amber-100 text-amber-700">{t('badge.no_origins')}</Badge>
                    )}
                  </div>
                  <div className="flex gap-3 text-xs text-muted-foreground flex-wrap">
                    <span>{t('list.extra_fields', { count: (f.field_configs || []).length })}</span>
                    {f.collect_name && <span>{t('list.with_name')}</span>}
                    {f.collect_phone && <span>{t('list.with_phone')}</span>}
                    <span>{t('list.origins', { count: (f.allowed_origins || []).length })}</span>
                  </div>
                </div>
                <div className="flex items-center gap-1 shrink-0">
                  <Button variant="outline" size="sm" className="gap-1 text-xs" onClick={() => setEmbedTarget(f)}>
                    <Code2 className="h-3.5 w-3.5" /> {t('actions.embed')}
                  </Button>
                  <Button variant="outline" size="sm" className="gap-1 text-xs" onClick={() => setSubsTarget(f)}>
                    <Users className="h-3.5 w-3.5" /> {t('actions.subscribers')}
                  </Button>
                  <Button variant="ghost" size="sm" onClick={() => openEdit(f)} aria-label={t('actions.edit')}>
                    <Pencil className="h-3.5 w-3.5" />
                  </Button>
                  <Button variant="ghost" size="sm" className="text-xs" onClick={() => handleToggle(f)}>
                    {f.is_active ? t('actions.deactivate') : t('actions.activate')}
                  </Button>
                  <Button variant="ghost" size="sm" className="text-destructive" onClick={() => handleDelete(f)} aria-label={t('actions.delete')}>
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Create / Edit dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="sm:max-w-lg max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editingId ? t('dialog.edit_title') : t('dialog.new_title')}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div>
              <Label>{t('dialog.name')} *</Label>
              <Input value={form.name} maxLength={120}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                placeholder={t('dialog.name_ph')} />
            </div>

            <div>
              <Label className="text-xs">{t('dialog.collected_fields')}</Label>
              <div className="flex flex-col gap-2 mt-1">
                {/* Email: sempre raccolta, non disattivabile, non un campo extra. */}
                <label className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Checkbox checked disabled />
                  {t('dialog.email_always')} <span className="text-xs">{t('dialog.email_always_hint')}</span>
                </label>
                <label className="flex items-center gap-2 text-sm">
                  <Checkbox checked={form.collect_name}
                    onCheckedChange={(v) => setForm((f) => ({ ...f, collect_name: !!v }))} />
                  {t('dialog.field_name')}
                </label>
                <label className="flex items-center gap-2 text-sm">
                  <Checkbox checked={form.collect_phone}
                    onCheckedChange={(v) => setForm((f) => ({ ...f, collect_phone: !!v }))} />
                  {t('dialog.field_phone')}
                </label>
              </div>
            </div>

            <label className="flex items-center gap-2 text-sm">
              <Checkbox checked={form.privacy_required}
                onCheckedChange={(v) => setForm((f) => ({ ...f, privacy_required: !!v }))} />
              {t('dialog.require_consent')}
            </label>

            {form.privacy_required && (
              <div className="space-y-3 rounded-lg border p-3 bg-muted/20">
                <div>
                  <Label className="text-xs">{t('dialog.consent_text')}</Label>
                  <Textarea value={form.consent_text} rows={2} maxLength={2000}
                    onChange={(e) => setForm((f) => ({ ...f, consent_text: e.target.value }))}
                    placeholder={t('dialog.consent_text_ph')} />
                </div>

                <div>
                  <Label className="text-xs">{t('privacy.label')}</Label>
                  <select
                    className="w-full mt-1 rounded-md border border-input bg-background px-3 py-2 text-sm"
                    value={form.privacy_mode}
                    onChange={(e) => setForm((f) => ({ ...f, privacy_mode: e.target.value }))}
                  >
                    <option value="none">{t('privacy.mode_none')}</option>
                    <option value="store">{t('privacy.mode_store')}</option>
                    <option value="custom">{t('privacy.mode_custom')}</option>
                  </select>
                </div>

                {form.privacy_mode === 'store' && (
                  <div className="space-y-2">
                    {stores.length === 0 ? (
                      <div className="text-[11px] rounded-md border border-amber-200 bg-amber-50 p-2 text-amber-800">
                        {t('privacy.no_stores')}
                      </div>
                    ) : (
                      <>
                        <select
                          className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                          value={form.privacy_store_id}
                          onChange={(e) => setForm((f) => ({ ...f, privacy_store_id: e.target.value }))}
                        >
                          <option value="">{t('privacy.choose_store')}</option>
                          {stores.map((s) => (
                            <option key={s.id} value={s.id}>{s.name}</option>
                          ))}
                        </select>
                        {form.privacy_store_id && (
                          <PrivacyStoreStatus
                            store={stores.find((s) => s.id === form.privacy_store_id)}
                            onCreate={(st) => setLegalStore(st)}
                          />
                        )}
                      </>
                    )}
                  </div>
                )}

                {form.privacy_mode === 'custom' && (
                  <Input value={form.privacy_custom_url} maxLength={500}
                    onChange={(e) => setForm((f) => ({ ...f, privacy_custom_url: e.target.value }))}
                    placeholder={t('privacy.custom_ph')} />
                )}
              </div>
            )}

            <div>
              <Label className="text-xs">{t('dialog.success_message')}</Label>
              <Input value={form.success_message} maxLength={500}
                onChange={(e) => setForm((f) => ({ ...f, success_message: e.target.value }))}
                placeholder={t('dialog.success_message_ph')} />
            </div>

            {/* F8 — layout */}
            <div className="space-y-1.5">
              <Label className="text-xs">{t('layout.label')}</Label>
              <div className="grid grid-cols-3 gap-2">
                {['vertical', 'horizontal', 'inline'].map((lay) => (
                  <button
                    key={lay}
                    type="button"
                    onClick={() => setForm((f) => ({ ...f, layout: lay }))}
                    className={`rounded-lg border px-2 py-2 text-xs font-medium transition ${
                      form.layout === lay
                        ? 'border-primary bg-primary/10 text-primary'
                        : 'border-input bg-background text-muted-foreground hover:bg-muted/50'
                    }`}
                  >
                    {t(`layout.${lay}`)}
                  </button>
                ))}
              </div>
            </div>

            {/* F7 — colori */}
            <div className="space-y-2">
              <label className="flex items-center gap-2 text-sm">
                <Checkbox checked={form.custom_colors}
                  onCheckedChange={(v) => setForm((f) => ({ ...f, custom_colors: !!v }))} />
                {t('colors.toggle')}
              </label>
              {form.custom_colors && (
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <Label className="text-xs">{t('colors.button')}</Label>
                    <input type="color" className="w-full h-9 rounded-md border border-input bg-background"
                      value={form.primary_color}
                      onChange={(e) => setForm((f) => ({ ...f, primary_color: e.target.value }))} />
                  </div>
                  <div>
                    <Label className="text-xs">{t('colors.button_text')}</Label>
                    <input type="color" className="w-full h-9 rounded-md border border-input bg-background"
                      value={form.primary_text_color}
                      onChange={(e) => setForm((f) => ({ ...f, primary_text_color: e.target.value }))} />
                  </div>
                </div>
              )}
            </div>

            <FieldEditorList
              fields={form.field_configs}
              onChange={(next) => setForm((f) => ({ ...f, field_configs: next }))}
              title={t('dialog.extra_fields_title')}
              subtitle={t('dialog.extra_fields_subtitle')}
              allowedTypes={NL_FIELD_TYPES}
            />

            <div>
              <Label className="text-xs">{t('dialog.allowed_origins')}</Label>
              <Textarea value={form.allowed_origins} rows={3}
                onChange={(e) => setForm((f) => ({ ...f, allowed_origins: e.target.value }))}
                placeholder={'https://www.miosito.com\nhttps://blog.miosito.com'} />
              <p className="text-[11px] text-muted-foreground mt-1">
                {t('dialog.allowed_origins_hint')}
              </p>
            </div>

            {/* F7 — anteprima live (riusa il web component dell'embed) */}
            <NewsletterFormPreview config={previewConfig} />
          </div>
          <DialogFooter>
            <Button variant="outline" size="sm" onClick={() => setDialogOpen(false)}>{t('actions.cancel')}</Button>
            <Button size="sm" onClick={handleSave} disabled={saving} className="gap-1.5">
              {saving ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Mail className="h-3.5 w-3.5" />}
              {editingId ? t('actions.save') : t('actions.create')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <EmbedDialog form={embedTarget} onClose={() => setEmbedTarget(null)} />
      <SubmissionsDialog form={subsTarget} onClose={() => setSubsTarget(null)} />

      {/* F7 — riuso dell'editor legale dell'ecommerce per creare/personalizzare
          la privacy dello store scelto, e auto-linkarla. Zero duplicazione. */}
      <MerchantLegalDialog
        open={!!legalStore}
        store={legalStore}
        onClose={() => { setLegalStore(null); loadStores(); }}
      />
    </AppLayout>
  );
}


function PrivacyStoreStatus({ store, onCreate }) {
  const { t } = useTranslation('newsletter');
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let alive = true;
    if (!store?.id) { setStatus(null); return undefined; }
    setLoading(true);
    // storeLegalAPI.get ritorna già il payload (.data) → res.status è lo
    // stato legale (non l'HTTP status).
    storeLegalAPI.get(store.id)
      .then((res) => { if (alive) setStatus(res?.status || 'not_configured'); })
      .catch(() => { if (alive) setStatus('not_configured'); })
      .finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, [store?.id]);

  if (!store) return null;
  if (loading) return <p className="text-[11px] text-muted-foreground">{t('privacy.checking')}</p>;

  const published = status === 'published' || status === 'stale_draft';
  return (
    <div className="text-[11px] flex items-center justify-between gap-2">
      {published ? (
        <span className="text-emerald-700">{t('privacy.published')}</span>
      ) : (
        <>
          <span className="text-amber-700">{t('privacy.not_configured')}</span>
          <Button type="button" variant="outline" size="sm" className="h-7 text-xs"
            onClick={() => onCreate(store)}>
            {t('privacy.create')}
          </Button>
        </>
      )}
    </div>
  );
}


function EmbedDialog({ form, onClose }) {
  const { t } = useTranslation('newsletter');
  const snippet = form ? buildNewsletterSnippet(form.id) : '';
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(snippet);
      toast.success(t('toast.snippet_copied'));
    } catch { toast.error(t('toast.copy_failed')); }
  };
  return (
    <Dialog open={!!form} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>{t('embed.title')}</DialogTitle>
          <DialogDescription>{t('embed.desc')}</DialogDescription>
        </DialogHeader>
        {(form?.allowed_origins || []).length === 0 && (
          <p className="text-xs text-amber-700 bg-amber-50 rounded-md p-2">
            {t('embed.warning')}
          </p>
        )}
        <pre className="text-[11px] bg-muted rounded-lg p-3 overflow-x-auto whitespace-pre-wrap break-all">{snippet}</pre>
        <DialogFooter>
          <Button variant="outline" size="sm" onClick={onClose}>{t('actions.close')}</Button>
          <Button size="sm" onClick={copy} className="gap-1.5"><Copy className="h-3.5 w-3.5" /> {t('actions.copy')}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}


function SubmissionsDialog({ form, onClose }) {
  const { t } = useTranslation('newsletter');
  const [subs, setSubs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [source, setSource] = useState('');

  const load = useCallback(async (formId, src) => {
    setLoading(true);
    try {
      const res = await newsletterAPI.submissions(formId, src || undefined);
      setSubs(res.data || []);
    } catch { setSubs([]); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => {
    if (form) { setSource(''); load(form.id, ''); }
  }, [form, load]);

  return (
    <Dialog open={!!form} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="sm:max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{t('subs.title', { name: form?.name || '' })}</DialogTitle>
        </DialogHeader>
        <div className="flex gap-2 items-end">
          <div className="flex-1">
            <Label className="text-xs">{t('subs.filter_label')}</Label>
            <Input value={source} onChange={(e) => setSource(e.target.value)}
              placeholder={t('subs.filter_ph')} />
          </div>
          <Button size="sm" variant="outline" onClick={() => form && load(form.id, source)}>{t('actions.filter')}</Button>
        </div>
        {loading ? (
          <div className="flex justify-center py-10"><Loader2 className="h-5 w-5 animate-spin text-muted-foreground" /></div>
        ) : subs.length === 0 ? (
          <p className="text-sm text-muted-foreground py-8 text-center">{t('subs.empty')}</p>
        ) : (
          <div className="space-y-1.5 text-sm">
            {subs.map((s) => (
              <div key={s.id} className="rounded-lg border p-2.5 flex items-center justify-between gap-3">
                <div className="min-w-0">
                  <div className="font-medium truncate">{s.email}</div>
                  <div className="text-xs text-muted-foreground truncate">
                    {s.name && <span>{s.name} · </span>}
                    {(s.source_label || s.source_origin || s.source_url) && (
                      <span>{t('subs.from', { source: s.source_label || s.source_origin || s.source_url })}</span>
                    )}
                  </div>
                </div>
                {s.status === 'unsubscribed'
                  ? <Badge className="text-[10px] bg-gray-100 text-gray-500 shrink-0">{t('subs.status_unsubscribed')}</Badge>
                  : <Badge className="text-[10px] bg-emerald-100 text-emerald-700 shrink-0">{t('subs.status_subscribed')}</Badge>}
              </div>
            ))}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
