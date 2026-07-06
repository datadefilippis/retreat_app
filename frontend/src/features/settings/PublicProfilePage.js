/**
 * PublicProfilePage — /public-profile (F2.0, 5/7/2026).
 *
 * L'editor della pagina profilo pubblica dell'operatore (/o/:slug):
 * cover, bio, città/regione, social, contatti opzionali. Con anteprima
 * live, "Copia link" e indicatore di completezza — l'operatore la
 * compila in <5 minuti e la usa come biglietto da visita.
 */
import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { AppLayout, Header } from '../../components/Layout';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Skeleton } from '../../components/ui/skeleton';
import {
  ExternalLink, Copy, Check, Upload, Loader2, Instagram, Globe, Facebook,
} from 'lucide-react';
import { toast } from 'sonner';
import api from '../../api/client';

const FIELDS = ['bio', 'city', 'region', 'cover_url', 'instagram', 'website', 'facebook', 'public_email', 'public_phone',
  // PR1 — carta d'identità
  'tagline', 'portrait_url', 'founded_year'];
const PROFILE_LANGS = ['it', 'en', 'de', 'fr', 'es', 'pt'];

export default function PublicProfilePage() {
  const { t } = useTranslation('settings');
  const [form, setForm] = useState(null);
  const [slug, setSlug] = useState(null);
  const [orgName, setOrgName] = useState('');
  const [logoUrl, setLogoUrl] = useState(null);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [copied, setCopied] = useState(false);
  const fileRef = useRef(null);

  useEffect(() => {
    let mounted = true;
    Promise.allSettled([
      api.get('/organizations/current/public-profile'),
      api.get('/organizations/current'),
    ]).then(([ppRes, orgRes]) => {
      if (!mounted) return;
      setForm(ppRes.status === 'fulfilled'
        ? { show_contacts: false, ...ppRes.value.data }
        : { show_contacts: false });
      if (orgRes.status === 'fulfilled') {
        const o = orgRes.value.data || {};
        setSlug(o.public_slug || o.store_slug || null);
        setOrgName(o.name || '');
        setLogoUrl(o.branding?.logo_url || null);
      }
    });
    return () => { mounted = false; };
  }, []);

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));

  const completeness = useMemo(() => {
    if (!form) return 0;
    const checks = [form.cover_url, form.bio, form.city,
      form.instagram || form.website || form.facebook];
    return Math.round(checks.filter(Boolean).length / checks.length * 100);
  }, [form]);

  const profileUrl = slug ? `${window.location.origin}/o/${slug}` : null;

  const save = async () => {
    setSaving(true);
    try {
      const payload = {};
      FIELDS.forEach(k => { payload[k] = form[k] || null; });
      payload.show_contacts = Boolean(form.show_contacts);
      payload.photos = form.photos || [];
      payload.languages = form.languages || [];
      const res = await api.patch('/organizations/current/public-profile', payload);
      setForm({ show_contacts: false, ...res.data });
      toast.success(t('publicProfile.saved', { defaultValue: 'Profilo salvato' }));
    } catch {
      toast.error(t('publicProfile.saveError', { defaultValue: 'Errore nel salvataggio' }));
    } finally {
      setSaving(false);
    }
  };

  const uploadCover = async (file) => {
    if (!file) return;
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append('file', file);
      const res = await api.post('/organizations/current/public-profile/cover', fd,
        { headers: { 'Content-Type': 'multipart/form-data' } });
      set('cover_url', res.data.cover_url);
      toast.success(t('publicProfile.coverUploaded', { defaultValue: 'Cover caricata' }));
    } catch (err) {
      const detail = err?.response?.data?.detail;
      toast.error(typeof detail === 'string' ? detail
        : t('publicProfile.coverError', { defaultValue: 'Errore nel caricamento' }));
    } finally {
      setUploading(false);
    }
  };

  // PR1 — ritratto (foto a lato nella carta d'identità)
  const uploadPortrait = async (file) => {
    if (!file) return;
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append('file', file);
      const res = await api.post('/organizations/current/public-profile/portrait', fd,
        { headers: { 'Content-Type': 'multipart/form-data' } });
      set('portrait_url', res.data.portrait_url);
      toast.success(t('publicProfile.portraitUploaded', { defaultValue: 'Ritratto caricato' }));
    } catch (err) {
      toast.error(err?.response?.data?.detail || t('publicProfile.coverError', { defaultValue: 'Errore nel caricamento' }));
    } finally { setUploading(false); }
  };

  // PR1 — galleria (max 8, un file per volta; ordine = ordine di lista)
  const uploadPhoto = async (file) => {
    if (!file) return;
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append('file', file);
      const res = await api.post('/organizations/current/public-profile/photos', fd,
        { headers: { 'Content-Type': 'multipart/form-data' } });
      set('photos', res.data.photos);
      toast.success(t('publicProfile.photoUploaded', { defaultValue: 'Foto aggiunta' }));
    } catch (err) {
      toast.error(err?.response?.data?.detail || t('publicProfile.coverError', { defaultValue: 'Errore nel caricamento' }));
    } finally { setUploading(false); }
  };

  const removePhoto = (url) => set('photos', (form.photos || []).filter(u => u !== url));

  const copyLink = async () => {
    if (!profileUrl) return;
    try {
      await navigator.clipboard.writeText(profileUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch { /* clipboard non disponibile */ }
  };

  if (!form) {
    return (
      <AppLayout>
        <Header title={t('publicProfile.title', { defaultValue: 'Profilo pubblico' })} />
        <div className="p-4 md:p-8"><Skeleton className="h-64 w-full rounded-xl" /></div>
      </AppLayout>
    );
  }

  const inputCls = 'w-full';

  return (
    <AppLayout>
      <Header
        title={t('publicProfile.title', { defaultValue: 'Profilo pubblico' })}
        subtitle={t('publicProfile.subtitle', { defaultValue: 'La tua pagina biglietto-da-visita nella directory dei ritiri' })}
      >
        {profileUrl && (
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={copyLink}>
              {copied ? <Check className="h-4 w-4 mr-1.5" /> : <Copy className="h-4 w-4 mr-1.5" />}
              {copied
                ? t('publicProfile.copied', { defaultValue: 'Copiato!' })
                : t('publicProfile.copyLink', { defaultValue: 'Copia link' })}
            </Button>
            <a href={profileUrl} target="_blank" rel="noreferrer">
              <Button variant="outline" size="sm">
                <ExternalLink className="h-4 w-4 mr-1.5" />
                {t('publicProfile.view', { defaultValue: 'Apri' })}
              </Button>
            </a>
          </div>
        )}
      </Header>

      <div className="p-4 md:p-8 grid gap-6 lg:grid-cols-2 max-w-6xl">
        {/* ── Form ── */}
        <div className="space-y-5">
          {/* Completezza */}
          <div className="rounded-xl border bg-card p-4">
            <div className="flex items-center justify-between text-sm">
              <span className="font-medium">
                {t('publicProfile.completeness', { defaultValue: 'Profilo completo al' })} {completeness}%
              </span>
            </div>
            <div className="mt-2 h-2 rounded-full bg-muted overflow-hidden">
              <div className="h-full rounded-full bg-primary transition-all"
                   style={{ width: `${completeness}%` }} />
            </div>
            <p className="mt-2 text-xs text-muted-foreground">
              {t('publicProfile.completenessHint', { defaultValue: 'Foto, bio e social aumentano la fiducia — e le prenotazioni.' })}
            </p>
          </div>

          {/* Cover */}
          <div className="rounded-xl border bg-card p-4 space-y-2">
            <Label>{t('publicProfile.cover', { defaultValue: 'Foto di copertina' })}</Label>
            <input ref={fileRef} type="file" accept="image/jpeg,image/png,image/webp"
                   className="hidden" onChange={e => uploadCover(e.target.files?.[0])} />
            <div
              className="relative h-36 rounded-lg border-2 border-dashed border-border bg-muted/40 overflow-hidden cursor-pointer hover:border-primary/50 transition-colors"
              onClick={() => fileRef.current?.click()}
            >
              {form.cover_url ? (
                <img src={form.cover_url} alt="" className="w-full h-full object-cover" />
              ) : (
                <div className="h-full flex flex-col items-center justify-center text-muted-foreground text-sm gap-1">
                  <Upload className="h-5 w-5" />
                  {t('publicProfile.coverHint', { defaultValue: 'Clicca per caricare (max 2MB)' })}
                </div>
              )}
              {uploading && (
                <div className="absolute inset-0 bg-white/70 flex items-center justify-center">
                  <Loader2 className="h-6 w-6 animate-spin text-primary" />
                </div>
              )}
            </div>
          </div>

          {/* PR1 — Carta d'identità: tagline, ritratto, galleria, anno, lingue */}
          <div className="rounded-xl border bg-card p-4 space-y-3">
            <div>
              <Label>{t('publicProfile.tagline', { defaultValue: 'Tagline (una frase che ti descrive)' })}</Label>
              <input
                value={form.tagline || ''}
                onChange={e => set('tagline', e.target.value.slice(0, 80))}
                maxLength={80}
                placeholder={t('publicProfile.taglinePlaceholder', { defaultValue: 'Es. "Yoga e silenzio tra gli ulivi di Ostuni"' })}
                className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label>{t('publicProfile.foundedYear', { defaultValue: 'Attivo dal (anno)' })}</Label>
                <input
                  value={form.founded_year || ''}
                  onChange={e => set('founded_year', e.target.value.replace(/\D/g, '').slice(0, 4))}
                  inputMode="numeric" maxLength={4} placeholder="2018"
                  className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                />
              </div>
              <div>
                <Label>{t('publicProfile.languages', { defaultValue: 'Lingue parlate' })}</Label>
                <div className="mt-1 flex flex-wrap gap-1.5">
                  {PROFILE_LANGS.map(l => {
                    const active = (form.languages || []).includes(l);
                    return (
                      <button key={l} type="button"
                        onClick={() => set('languages', active
                          ? (form.languages || []).filter(x => x !== l)
                          : [...(form.languages || []), l])}
                        className={`rounded-full px-2.5 py-1 text-xs font-semibold uppercase transition-colors ${
                          active ? 'bg-primary text-white' : 'border border-border text-muted-foreground hover:border-primary'}`}>
                        {l}
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>
            <div>
              <Label>{t('publicProfile.portrait', { defaultValue: 'Ritratto (foto a lato del profilo)' })}</Label>
              <input type="file" accept="image/jpeg,image/png,image/webp" className="hidden" id="pp-portrait"
                     onChange={e => uploadPortrait(e.target.files?.[0])} />
              <label htmlFor="pp-portrait"
                     className="mt-1 block h-32 w-32 rounded-xl border-2 border-dashed border-border bg-muted/40 overflow-hidden cursor-pointer hover:border-primary/50 transition-colors">
                {form.portrait_url
                  ? <img src={form.portrait_url} alt="" className="w-full h-full object-cover" />
                  : <span className="h-full flex items-center justify-center text-xs text-muted-foreground px-2 text-center">
                      {t('publicProfile.portraitHint', { defaultValue: 'Carica (max 2MB)' })}
                    </span>}
              </label>
            </div>
            <div>
              <Label>{t('publicProfile.gallery', { defaultValue: 'Galleria foto (max 8)' })}</Label>
              <div className="mt-1 grid grid-cols-4 gap-2">
                {(form.photos || []).map(url => (
                  <div key={url} className="relative h-20 rounded-lg overflow-hidden group">
                    <img src={url} alt="" className="w-full h-full object-cover" />
                    <button type="button" onClick={() => removePhoto(url)}
                            aria-label="Rimuovi"
                            className="absolute top-1 right-1 h-5 w-5 rounded-full bg-black/60 text-white text-xs opacity-0 group-hover:opacity-100 transition-opacity">×</button>
                  </div>
                ))}
                {(form.photos || []).length < 8 && (
                  <>
                    <input type="file" accept="image/jpeg,image/png,image/webp" className="hidden" id="pp-photo"
                           onChange={e => { uploadPhoto(e.target.files?.[0]); e.target.value = ''; }} />
                    <label htmlFor="pp-photo"
                           className="h-20 rounded-lg border-2 border-dashed border-border bg-muted/40 flex items-center justify-center text-xl text-muted-foreground cursor-pointer hover:border-primary/50 transition-colors">+</label>
                  </>
                )}
              </div>
              <p className="text-[11px] text-muted-foreground mt-1">
                {t('publicProfile.galleryHint', { defaultValue: 'Ricorda: rimuovere una foto qui richiede Salva per rendere effettivo.' })}
              </p>
            </div>
          </div>

          {/* Bio + luogo */}
          <div className="rounded-xl border bg-card p-4 space-y-3">
            <div>
              <Label>{t('publicProfile.bio', { defaultValue: 'Chi sei (bio)' })}</Label>
              <textarea
                value={form.bio || ''}
                onChange={e => set('bio', e.target.value.slice(0, 600))}
                rows={4} maxLength={600}
                placeholder={t('publicProfile.bioPlaceholder', { defaultValue: 'Racconta chi sei e che esperienze crei — 2-3 frasi bastano.' })}
                className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring resize-y"
              />
              <p className="text-right text-[11px] text-muted-foreground">{(form.bio || '').length}/600</p>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label>{t('publicProfile.city', { defaultValue: 'Città' })}</Label>
                <Input className={inputCls} value={form.city || ''} onChange={e => set('city', e.target.value)} />
              </div>
              <div>
                <Label>{t('publicProfile.region', { defaultValue: 'Regione' })}</Label>
                <Input className={inputCls} value={form.region || ''} onChange={e => set('region', e.target.value)} />
              </div>
            </div>
          </div>

          {/* Social */}
          <div className="rounded-xl border bg-card p-4 space-y-3">
            <Label>{t('publicProfile.socials', { defaultValue: 'Social e sito' })}</Label>
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <Instagram className="h-4 w-4 text-muted-foreground shrink-0" />
                <Input placeholder="instagram.com/iltuoprofilo" value={form.instagram || ''}
                       onChange={e => set('instagram', e.target.value)} />
              </div>
              <div className="flex items-center gap-2">
                <Globe className="h-4 w-4 text-muted-foreground shrink-0" />
                <Input placeholder="iltuosito.it" value={form.website || ''}
                       onChange={e => set('website', e.target.value)} />
              </div>
              <div className="flex items-center gap-2">
                <Facebook className="h-4 w-4 text-muted-foreground shrink-0" />
                <Input placeholder="facebook.com/latuapagina" value={form.facebook || ''}
                       onChange={e => set('facebook', e.target.value)} />
              </div>
            </div>
          </div>

          {/* Contatti opzionali */}
          <div className="rounded-xl border bg-card p-4 space-y-3">
            <label className="flex items-start gap-3 cursor-pointer">
              <input type="checkbox" checked={Boolean(form.show_contacts)}
                     onChange={e => set('show_contacts', e.target.checked)}
                     className="mt-0.5 h-4 w-4 rounded border-input" />
              <div>
                <span className="block text-sm font-medium">
                  {t('publicProfile.showContacts', { defaultValue: 'Mostra contatti sul profilo' })}
                </span>
                <span className="block text-xs text-muted-foreground">
                  {t('publicProfile.showContactsHint', { defaultValue: 'Decidi tu cosa esporre pubblicamente.' })}
                </span>
              </div>
            </label>
            {form.show_contacts && (
              <div className="grid grid-cols-2 gap-3">
                <Input placeholder="Email pubblica" type="email" value={form.public_email || ''}
                       onChange={e => set('public_email', e.target.value)} />
                <Input placeholder="Telefono" value={form.public_phone || ''}
                       onChange={e => set('public_phone', e.target.value)} />
              </div>
            )}
          </div>

          <Button onClick={save} disabled={saving} className="w-full h-11 font-semibold">
            {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            {t('publicProfile.save', { defaultValue: 'Salva profilo' })}
          </Button>
        </div>

        {/* ── Anteprima live ── */}
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
            {t('publicProfile.preview', { defaultValue: 'Anteprima' })}
          </p>
          <div className="rounded-2xl border bg-white overflow-hidden shadow-sm">
            <div className="relative h-32 bg-gradient-sidebar">
              {form.cover_url && (
                <img src={form.cover_url} alt="" className="w-full h-full object-cover" />
              )}
              <div className="absolute -bottom-7 left-5 h-14 w-14 rounded-full border-4 border-white bg-muted overflow-hidden">
                {logoUrl
                  ? <img src={logoUrl} alt="" className="w-full h-full object-cover" />
                  : <div className="w-full h-full flex items-center justify-center text-xl" aria-hidden>🧘</div>}
              </div>
            </div>
            <div className="pt-9 px-5 pb-5">
              <h3 className="font-bold text-gray-900">{orgName || '—'}</h3>
              {(form.city || form.region) && (
                <p className="text-xs text-gray-500">
                  {[form.city, form.region].filter(Boolean).join(', ')}
                </p>
              )}
              <p className="mt-2 text-sm text-gray-700 leading-relaxed whitespace-pre-line">
                {form.bio || <span className="text-gray-400 italic">
                  {t('publicProfile.bioEmpty', { defaultValue: 'La tua bio apparirà qui…' })}
                </span>}
              </p>
              {(form.instagram || form.website || form.facebook) && (
                <div className="mt-3 flex gap-3 text-gray-500">
                  {form.instagram && <Instagram className="h-4 w-4" />}
                  {form.website && <Globe className="h-4 w-4" />}
                  {form.facebook && <Facebook className="h-4 w-4" />}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </AppLayout>
  );
}
