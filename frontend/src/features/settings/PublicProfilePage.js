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
import { Link, Link as RouterLink } from 'react-router-dom';
import {
  ExternalLink, Copy, Check, Upload, Loader2, Instagram, Globe, Facebook,
  Eye, Mic, ChevronDown,
} from 'lucide-react';
import { toast } from 'sonner';
import api from '../../api/client';
import { BRAND_EMAIL } from '../../config/brand';
import { compressImage } from '../../lib/compressImage';
import OnboardingStrip from '../onboarding/OnboardingStrip';
// LK3 — la pagina link per la bio di Instagram: card autonoma,
// salvataggio immediato, fuori dal circuito snapshot/dirty del form
import LinkPageCard from './LinkPageCard';

const FIELDS = ['bio', 'city', 'region', 'cover_url', 'instagram', 'website', 'facebook', 'public_email', 'public_phone',
  // PR1 — carta d'identità
  'tagline', 'portrait_url', 'founded_year'];
const PROFILE_LANGS = ['it', 'en', 'de', 'fr', 'es', 'pt'];

// AC3 — la fotografia dei soli campi che il Salva persiste: serve al
// confronto "ci sono modifiche non salvate?" (la barra fissa in basso).
const snapshot = (f, name) => JSON.stringify({
  fields: FIELDS.map(k => (f?.[k] ?? null) || null),
  photos: f?.photos || [],
  languages: f?.languages || [],
  translations: f?.translations || {},
  show_contacts: Boolean(f?.show_contacts),
  name: (name || '').trim(),
});

// AN3 — autocomplete località per il profilo: stesso backend della
// barra "Dove?" della directory (/public/geo/search, Nominatim+cache).
function LocationAutocomplete({ value, onSelect, onTextChange }) {
  const [text, setText] = useState(value || '');
  const [results, setResults] = useState([]);
  const [open, setOpen] = useState(false);
  // CS4 (founder, 13/8) — il dropdown restava aperto dopo la scelta:
  // selezionare scriveva form.city → value → setText, e il cambio di
  // text rilanciava la ricerca riaprendo la lista. Si cerca (e si apre)
  // solo se il testo l'ha battuto l'utente.
  const typedRef = useRef(false);
  useEffect(() => { setText(value || ''); }, [value]);
  useEffect(() => {
    if (!typedRef.current) return undefined;
    if (!text || text.length < 2) { setResults([]); setOpen(false); return undefined; }
    const timer = setTimeout(() => {
      api.get('/public/geo/search', { params: { q: text } })
        .then(res => { setResults(res.data?.results || []); setOpen(true); })
        .catch(() => setResults([]));
    }, 400);
    return () => clearTimeout(timer);
  }, [text]);
  return (
    <div className="relative">
      <Input
        value={text}
        onChange={e => { typedRef.current = true; setText(e.target.value); onTextChange?.(e.target.value); }}
        onFocus={() => results.length && setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 150)}
        placeholder="Ostuni, Puglia…"
        className="mt-1"
      />
      {open && results.length > 0 && (
        <ul className="absolute z-20 mt-1 w-full rounded-md border border-border bg-white shadow-lg max-h-52 overflow-auto">
          {results.map((r) => (
            <li key={`${r.lat}-${r.lng}`}>
              <button
                type="button"
                onMouseDown={() => { typedRef.current = false; onSelect(r); setOpen(false); setResults([]); }}
                className="w-full text-left px-3 py-2 text-sm hover:bg-muted/60"
              >
                📍 {r.label}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default function PublicProfilePage() {
  const { t } = useTranslation('settings');
  const [form, setForm] = useState(null);
  const [slug, setSlug] = useState(null);
  const [orgName, setOrgName] = useState('');
  const [logoUrl, setLogoUrl] = useState(null);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  // PV1 — fase "Ottimizzo la foto": compressione client in corso
  const [optimizing, setOptimizing] = useState(false);
  const [copied, setCopied] = useState(false);
  // AC1 — ogni salvataggio che può cambiare lo stato onboarding
  // incrementa la chiave: la striscia-guida si riaggiorna da sola
  const [obKey, setObKey] = useState(0);
  // AC2 — il form era un muro di ~15 blocchi: l'essenziale (foto, bio,
  // località, un social) resta in vista, il resto vive qui sotto,
  // chiuso finché l'operatore non lo cerca
  const [advancedOpen, setAdvancedOpen] = useState(false);
  // AC3 — l'ultima fotografia SALVATA di form+nome: se quella attuale
  // è diversa, compare la barra fissa "Modifiche non salvate". Gli
  // upload (che il server persiste da soli) aggiornano solo il proprio
  // campo nella fotografia, senza coprire altre modifiche in corso.
  const [savedSnap, setSavedSnap] = useState(null);
  const savedFormRef = useRef(null);
  const markSaved = (f, name) => {
    savedFormRef.current = { form: f, name };
    setSavedSnap(snapshot(f, name));
  };
  const markFieldSaved = (key, value) => {
    const base = savedFormRef.current || { form: {}, name: '' };
    markSaved({ ...base.form, [key]: value }, base.name);
  };
  const dirty = Boolean(form) && savedSnap != null
    && snapshot(form, orgName) !== savedSnap;
  const fileRef = useRef(null);

  useEffect(() => {
    let mounted = true;
    Promise.allSettled([
      api.get('/organizations/current/public-profile'),
      api.get('/organizations/current'),
    ]).then(([ppRes, orgRes]) => {
      if (!mounted) return;
      const loadedForm = ppRes.status === 'fulfilled'
        ? { show_contacts: false, ...ppRes.value.data }
        : { show_contacts: false };
      setForm(loadedForm);
      let loadedName = '';
      if (ppRes.status === 'fulfilled' && ppRes.value.data?.name) {
        loadedName = ppRes.value.data.name;
        setOrgName(loadedName);
      }
      if (orgRes.status === 'fulfilled') {
        const o = orgRes.value.data || {};
        setSlug(o.public_slug || o.store_slug || null);
        loadedName = o.name || '';
        setOrgName(loadedName);
        setLogoUrl(o.branding?.logo_url || null);
      }
      // AC3 — la base del confronto "modifiche non salvate"
      markSaved(loadedForm, loadedName);
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
      // OP4 — il titolo pubblico e' organizations.name (stessa riga
      // delle Impostazioni): si salva solo se non vuoto
      if ((orgName || '').trim()) payload.name = orgName.trim();
      // AN3 — coordinate dall'autocomplete (numeri, non stringhe)
      if (form.latitude != null && form.longitude != null) {
        payload.latitude = form.latitude;
        payload.longitude = form.longitude;
      }
      payload.show_contacts = Boolean(form.show_contacts);
      payload.photos = form.photos || [];
      payload.languages = form.languages || [];
      // OP2 — traduzioni manuali bio/tagline (stesso processo dei prodotti)
      payload.translations = form.translations || {};
      // PV2 — l'intervista non si invia più: la scrive e pubblica il
      // team Aurya dal pannello admin (il backend la ignorerebbe comunque)
      const res = await api.patch('/organizations/current/public-profile', payload);
      const savedForm = { show_contacts: false, ...res.data };
      setForm(savedForm);
      if (res.data?.name) setOrgName(res.data.name);
      // CS4 (founder, 13/8) — il primo salvataggio genera lo slug (GT6):
      // senza questa riga il pulsante "Vedi il tuo profilo online"
      // compariva solo dopo un refresh manuale della pagina.
      if (res.data?.public_slug) setSlug(res.data.public_slug);
      // AC3 — quello che il server ha risposto E' lo stato salvato
      markSaved(savedForm, res.data?.name || orgName);
      setObKey(k => k + 1); // AC1 — la striscia-guida rilegge lo stato
      toast.success(t('publicProfile.saved', { defaultValue: 'Profilo salvato' }));
    } catch {
      toast.error(t('publicProfile.saveError', { defaultValue: 'Errore nel salvataggio' }));
    } finally {
      setSaving(false);
    }
  };

  // PV1 — messaggio d'errore upload: legge detail (FastAPI) E error
  // (formato slowapi storico), così il 429 non diventa un toast muto.
  const uploadErrorMessage = (err) => {
    const data = err?.response?.data || {};
    const msg = data.detail || data.error;
    return typeof msg === 'string' && msg
      ? msg
      : t('publicProfile.coverError', { defaultValue: 'Errore nel caricamento' });
  };

  // PV1 — compressione client prima della FormData ("Ottimizzo la foto")
  const prepareImage = async (file) => {
    setOptimizing(true);
    try { return await compressImage(file); }
    finally { setOptimizing(false); }
  };

  const uploadCover = async (file) => {
    if (!file) return;
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append('file', await prepareImage(file));
      const res = await api.post('/organizations/current/public-profile/cover', fd,
        { headers: { 'Content-Type': 'multipart/form-data' } });
      set('cover_url', res.data.cover_url);
      markFieldSaved('cover_url', res.data.cover_url); // AC3 — già persistita
      setObKey(k => k + 1); // AC1 — la cover può completare "Presentati"
      toast.success(t('publicProfile.coverUploaded', { defaultValue: 'Cover caricata' }));
    } catch (err) {
      toast.error(uploadErrorMessage(err));
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
      fd.append('file', await prepareImage(file));
      const res = await api.post('/organizations/current/public-profile/portrait', fd,
        { headers: { 'Content-Type': 'multipart/form-data' } });
      set('portrait_url', res.data.portrait_url);
      markFieldSaved('portrait_url', res.data.portrait_url); // AC3
      toast.success(t('publicProfile.portraitUploaded', { defaultValue: 'Ritratto caricato' }));
    } catch (err) {
      toast.error(uploadErrorMessage(err));
    } finally { setUploading(false); }
  };

  // PR1 — galleria (max 8, un file per volta; ordine = ordine di lista)
  const uploadPhoto = async (file) => {
    if (!file) return;
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append('file', await prepareImage(file));
      const res = await api.post('/organizations/current/public-profile/photos', fd,
        { headers: { 'Content-Type': 'multipart/form-data' } });
      set('photos', res.data.photos);
      markFieldSaved('photos', res.data.photos); // AC3
      toast.success(t('publicProfile.photoUploaded', { defaultValue: 'Foto aggiunta' }));
    } catch (err) {
      toast.error(uploadErrorMessage(err));
    } finally { setUploading(false); }
  };

  // AC4 — rimozione istantanea come il caricamento: prima togliere una
  // foto richiedeva ANCHE il Salva (con una nota che lo spiegava — se
  // serve una nota, il modello e' sbagliato). Ora un click persiste.
  const removePhoto = async (url) => {
    const filtered = (form.photos || []).filter(u => u !== url);
    set('photos', filtered);
    try {
      await api.patch('/organizations/current/public-profile', { photos: filtered });
      markFieldSaved('photos', filtered);
      toast.success(t('publicProfile.photoRemoved', { defaultValue: 'Foto rimossa' }));
    } catch {
      toast.error(t('publicProfile.saveError', { defaultValue: 'Errore nel salvataggio' }));
    }
  };

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
            {/* CS3 (founder, 13/8) — "Apri" outline non si vedeva: il
                pulsante che mostra il risultato e' quello primario. */}
            <a href={profileUrl} target="_blank" rel="noreferrer"
               data-testid="profile-view-online">
              <Button size="sm" className="font-semibold">
                <ExternalLink className="h-4 w-4 mr-1.5" />
                {t('publicProfile.view', { defaultValue: 'Vedi il tuo profilo online' })}
              </Button>
            </a>
            {/* PN0 — le condizioni si trovano da qui, non solo in
                fondo a Impostazioni */}
            <RouterLink to="/settings" data-testid="conditions-shortcut">
              <Button variant="outline" size="sm">
                {t('publicProfile.conditionsLink', { defaultValue: 'Condizioni di vendita' })}
              </Button>
            </RouterLink>
          </div>
        )}
      </Header>

      <div className="p-4 md:p-8 grid gap-6 lg:grid-cols-2 max-w-6xl">
        {/* AC1 — la guida non ti molla: a configurazione incompleta la
            striscia dice a che punto sei e dove andare dopo il salva */}
        <OnboardingStrip step="profile" refreshKey={obKey} className="lg:col-span-2" />
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

          {/* AC2 — qui sotto SOLO l'essenziale: foto, chi sei, dove
              sei, un social. Nome pubblico, carta d'identità, contatti
              e specchietto Visibilità vivono in "Per approfondire". */}

          {/* Cover */}
          <div className="rounded-xl border bg-card p-4 space-y-2">
            <Label>{t('publicProfile.cover', { defaultValue: 'Foto di copertina' })}</Label>
            <input ref={fileRef} type="file" accept="image/*"
                   className="hidden"
                   onChange={e => { uploadCover(e.target.files?.[0]); e.target.value = ''; }} />
            <div
              className="relative h-36 rounded-lg border-2 border-dashed border-border bg-muted/40 overflow-hidden cursor-pointer hover:border-primary/50 transition-colors"
              onClick={() => fileRef.current?.click()}
            >
              {form.cover_url ? (
                <img src={form.cover_url} alt="" className="w-full h-full object-cover" />
              ) : (
                <div className="h-full flex flex-col items-center justify-center text-muted-foreground text-sm gap-1">
                  <Upload className="h-5 w-5" />
                  {t('publicProfile.coverHint', { defaultValue: 'Clicca per caricare una foto' })}
                </div>
              )}
              {uploading && (
                <div className="absolute inset-0 bg-white/70 flex items-center justify-center gap-2">
                  <Loader2 className="h-6 w-6 animate-spin text-primary" />
                  <span className="text-sm font-medium text-primary">
                    {optimizing
                      ? t('publicProfile.optimizing', { defaultValue: 'Ottimizzo la foto…' })
                      : t('publicProfile.uploadingPhoto', { defaultValue: 'Carico la foto…' })}
                  </span>
                </div>
              )}
            </div>
          </div>

          {/* Tagline + bio + luogo */}
          <div className="rounded-xl border bg-card p-4 space-y-3">
            {/* AC8 (founder, 13/8) — linea "solo italiano" (2/8): le
                tab di traduzione EN/DE/FR spariscono dall'editor per
                coerenza. Le traduzioni GIA' salvate restano in DB e
                continuano a uscire in pubblico: qui si scrive solo
                l'italiano. (Sostituisce il consolidato OP4c-bis.) */}
              <div className="space-y-3">
                <div>
                  <Label>{t('publicProfile.tagline', { defaultValue: 'Una frase che ti presenta' })}</Label>
                  <input
                    value={form.tagline || ''}
                    onChange={e => set('tagline', e.target.value.slice(0, 80))}
                    maxLength={80}
                    placeholder={t('publicProfile.taglinePlaceholder', { defaultValue: 'Es. "Yoga e silenzio tra gli ulivi di Ostuni"' })}
                    className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                  />
                </div>
                <div>
                  <Label>{t('publicProfile.bio', { defaultValue: 'Chi sei (bio)' })}</Label>
                  <textarea
                    value={form.bio || ''}
                    onChange={e => set('bio', e.target.value.slice(0, 600))}
                    rows={4} maxLength={600}
                    placeholder={t('publicProfile.bioPlaceholder', { defaultValue: 'Racconta chi sei e che esperienze crei: 2-3 frasi bastano.' })}
                    className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring resize-y"
                  />
                  <p className="text-right text-[11px] text-muted-foreground">{(form.bio || '').length}/600</p>
                  {/* AC6 — per l'operatore poco digitale lo scoglio
                      non e' tecnico: e' scrivere di se'. Tre domande e
                      un esempio vero sbloccano piu' di qualsiasi campo.
                      Compare solo a bio vuota: poi non serve piu'. */}
                  {!(form.bio || '').trim() && (
                    <div className="mt-1 rounded-lg bg-muted/50 px-3 py-2.5 text-xs text-muted-foreground"
                         data-testid="bio-helper">
                      <p className="font-medium text-foreground">
                        {t('publicProfile.bioHelperTitle', { defaultValue: 'Non sai da dove iniziare? Rispondi a tre domande:' })}
                      </p>
                      <p className="mt-0.5">
                        {t('publicProfile.bioHelperQuestions', { defaultValue: 'Chi sei? · Che pratica porti? · Da quanto tempo la vivi?' })}
                      </p>
                      <p className="mt-1.5 italic">
                        {t('publicProfile.bioHelperExample', { defaultValue: 'Es. «Sono Lucia, insegno yoga da dodici anni. Accompagno chi ha bisogno di rallentare, con lezioni individuali e piccoli gruppi tra gli ulivi della mia terra.»' })}
                      </p>
                    </div>
                  )}
                </div>
              </div>
            {/* AN3 — località con autocomplete (Nominatim via /geo/search):
                compila città E coordinate → l'operatore compare sulla
                mappa e nel raggio "vicino a me" della directory */}
            <div>
              <Label>{t('publicProfile.locationSearch', { defaultValue: 'Località (cerca e seleziona)' })}</Label>
              <LocationAutocomplete
                value={form.city || ''}
                onSelect={(place) => {
                  setForm(f => ({
                    ...f,
                    city: (place.label || '').split(',')[0].trim(),
                    latitude: place.lat,
                    longitude: place.lng,
                  }));
                }}
                onTextChange={(txt) => set('city', txt)}
              />
              {form.latitude != null && (
                <p className="text-[11px] text-muted-foreground mt-1">
                  📍 {t('publicProfile.locationPinned', { defaultValue: 'Posizione agganciata alla mappa' })} ({Number(form.latitude).toFixed(3)}, {Number(form.longitude).toFixed(3)})
                </p>
              )}
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

          <Button onClick={save} disabled={saving} className="w-full h-11 font-semibold">
            {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            {t('publicProfile.save', { defaultValue: 'Salva profilo' })}
          </Button>

          {/* PV2 — l'intervista non si scrive più da qui: la realizza
              il team Aurya. Pannello informativo puro (nessun campo),
              con l'incentivo del badge Verificato. AC2: vive DOPO il
              Salva, cosi' non interrompe la compilazione. */}
          <div className="rounded-xl border border-[#8a7440]/30 bg-[#8a7440]/5 p-4 space-y-2"
               data-testid="interview-invite-panel">
            <div className="flex items-center gap-2">
              <Mic className="h-4 w-4 text-[#8a7440] shrink-0" aria-hidden />
              <p className="text-sm font-semibold text-foreground">
                {t('publicProfile.interviewInviteTitle', { defaultValue: 'Fatti intervistare da Aurya' })}
              </p>
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed">
              {t('publicProfile.interviewInviteBody', { defaultValue: 'L’intervista la realizza il team Aurya insieme a te: quando viene pubblicata diventi operatore verificato, con il badge sul tuo profilo e nel marketplace.' })}
            </p>
            {/* CS3 (founder, 13/8) — l'indirizzo si LEGGE, non solo si
                clicca: il mailto dipende dal client di posta configurato
                e su molti computer non apre niente. L'email in chiaro e'
                selezionabile e copiabile comunque. */}
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
              <a href={`mailto:${BRAND_EMAIL}?subject=Intervista%20Aurya`}
                 className="inline-flex items-center gap-1.5 text-xs font-semibold text-[#8a7440] hover:underline">
                {t('publicProfile.interviewInviteCta', { defaultValue: 'Scrivici per candidarti' })}
                <ExternalLink className="h-3 w-3" aria-hidden />
              </a>
              <span className="text-xs text-muted-foreground select-all"
                    data-testid="interview-email-plain">
                {BRAND_EMAIL}
              </span>
            </div>
          </div>

          {/* AC2 — "Per approfondire": tutto cio' che arricchisce il
              profilo ma non serve per andare online. Chiuso finche'
              l'operatore non lo cerca: il primo giro resta corto. */}
          <div className="rounded-xl border bg-card">
            <button type="button"
                    onClick={() => setAdvancedOpen(o => !o)}
                    data-testid="profile-advanced-toggle"
                    className="flex w-full items-center justify-between px-4 py-3 text-left">
              <span>
                <span className="block text-sm font-semibold">
                  {t('publicProfile.advancedTitle', { defaultValue: 'Per approfondire' })}
                </span>
                <span className="block text-xs text-muted-foreground">
                  {t('publicProfile.advancedHint', { defaultValue: 'Ritratto, galleria, contatti pubblici e altri dettagli. Tutto facoltativo.' })}
                </span>
              </span>
              <ChevronDown className={`h-4 w-4 shrink-0 text-muted-foreground transition-transform ${advancedOpen ? 'rotate-180' : ''}`} aria-hidden />
            </button>
            {advancedOpen && (
              <div className="space-y-5 border-t px-4 py-4" data-testid="profile-advanced-body">

                {/* OP4 — Nome pubblico: LA stessa riga delle Impostazioni.
                    E' il titolo che il pubblico vede su directory, profilo
                    e nei risultati di ricerca. */}
                <div className="space-y-2">
                  <Label>{t('publicProfile.publicName', { defaultValue: 'Nome pubblico' })}</Label>
                  <input
                    value={orgName}
                    onChange={e => setOrgName(e.target.value.slice(0, 120))}
                    maxLength={120}
                    className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                  />
                  <p className="text-[11px] text-muted-foreground">
                    {t('publicProfile.publicNameHint', { defaultValue: 'Compare su directory, profilo e motori di ricerca. Coincide con il nome azienda delle Impostazioni: cambiarlo qui lo cambia ovunque.' })}
                  </p>
                </div>

                {/* PR1 — Carta d'identità: ritratto, galleria, anno, lingue */}
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
                  <input type="file" accept="image/*" className="hidden" id="pp-portrait"
                         onChange={e => { uploadPortrait(e.target.files?.[0]); e.target.value = ''; }} />
                  <label htmlFor="pp-portrait"
                         className="mt-1 block h-32 w-32 rounded-xl border-2 border-dashed border-border bg-muted/40 overflow-hidden cursor-pointer hover:border-primary/50 transition-colors">
                    {form.portrait_url
                      ? <img src={form.portrait_url} alt="" className="w-full h-full object-cover" />
                      : <span className="h-full flex items-center justify-center text-xs text-muted-foreground px-2 text-center">
                          {t('publicProfile.portraitHint', { defaultValue: 'Carica una foto' })}
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
                        <input type="file" accept="image/*" className="hidden" id="pp-photo"
                               onChange={e => { uploadPhoto(e.target.files?.[0]); e.target.value = ''; }} />
                        <label htmlFor="pp-photo"
                               className="h-20 rounded-lg border-2 border-dashed border-border bg-muted/40 flex items-center justify-center text-xl text-muted-foreground cursor-pointer hover:border-primary/50 transition-colors">+</label>
                      </>
                    )}
                  </div>
                </div>

                {/* Regione (la località essenziale sta sopra) */}
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <Label>{t('publicProfile.region', { defaultValue: 'Regione' })}</Label>
                    <Input className={inputCls} value={form.region || ''} onChange={e => set('region', e.target.value)} />
                  </div>
                </div>

                {/* Contatti opzionali */}
                <div className="space-y-3">
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

                {/* VT5 — il ponte verso lo specchietto: quante persone
                    vedono questo profilo */}
                <Link to="/visibilita" className="flex items-center gap-3 rounded-xl border border-[#376254]/40 bg-[#376254]/5 p-4 hover:bg-[#376254]/10 transition-colors">
                  <Eye className="h-5 w-5 text-[#376254] shrink-0" aria-hidden />
                  <div className="min-w-0">
                    <p className="text-sm font-semibold text-foreground">
                      {t('publicProfile.visibilityTitle', { defaultValue: 'Quante persone ti vedono?' })}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {t('publicProfile.visibilityHint', { defaultValue: 'Quante volte sei comparso nelle ricerche, visite e prenotazioni: tutto nella pagina Visibilità.' })}
                    </p>
                  </div>
                </Link>

                <Button onClick={save} disabled={saving} variant="outline" className="w-full">
                  {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  {t('publicProfile.save', { defaultValue: 'Salva profilo' })}
                </Button>
              </div>
            )}
          </div>
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

        {/* LK3 — la pagina link: attiva → copia → incolla in bio.
            Vive fuori dallo snapshot del form: si salva da sola. */}
        {form.link_page !== undefined && (
          <LinkPageCard slug={slug} initial={form.link_page} />
        )}
      </div>

      {/* AC3 — Salva sempre a portata di mano: su un form lungo chi
          modifica la bio in alto non trova il bottone in fondo. La
          barra compare SOLO con modifiche non salvate e sparisce al
          salvataggio: mai rumore a riposo. md:left-64 = la sidebar. */}
      {dirty && (
        <div className="fixed inset-x-0 bottom-0 z-40 md:left-64"
             data-testid="unsaved-bar">
          <div className="mx-auto max-w-6xl px-4 pb-4">
            <div className="flex items-center justify-between gap-3 rounded-xl border border-primary/40 bg-card px-4 py-3 shadow-lg">
              <p className="text-sm font-medium text-foreground">
                {t('publicProfile.unsaved', { defaultValue: 'Hai modifiche non salvate' })}
              </p>
              <Button size="sm" onClick={save} disabled={saving} className="font-semibold shrink-0">
                {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                {t('publicProfile.save', { defaultValue: 'Salva profilo' })}
              </Button>
            </div>
          </div>
        </div>
      )}
    </AppLayout>
  );
}
