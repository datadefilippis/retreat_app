/**
 * OrgProfiloAdminTab — SA4 (24/9/2026): il system admin corregge il profilo
 * pubblico di un operatore senza impersonarlo e senza chiederglielo.
 *
 * Form COMPATTO (non l'editor intero: la pagina link resta dell'operatore):
 * SA6 (25/9 sera, founder: «foto profilo o copertina completamente fuori
 * luogo») copertina, ritratto e galleria si SOSTITUISCONO o RIMUOVONO qui,
 * subito, col motivo e una riga di audit ciascuna; poi
 * nome persona, attività (marchio), tagline, bio con
 * contatore e guida in sei punti, telefono + mostrato/privato, discipline
 * (lo stesso SelettoreDiscipline), sede principale (LocationAutocomplete),
 * Instagram/sito/Facebook, e il MOTIVO obbligatorio che finisce in
 * audit_logs. Si inviano SOLO i campi cambiati: l'audit racconta il vero.
 * Anteprima «Nome · Marchio» con la stessa regola dell'operatore
 * (lib/nomePubblico). Salva → PATCH /admin/organizations/{id}/public-profile.
 * Nessuna email all'operatore: gli scrive il founder.
 */
import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { ImageOff, Loader2, Lock, RefreshCw, Trash2, Unlock, X } from 'lucide-react';
import { toast } from 'sonner';
import { adminAPI } from '../../api';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Textarea } from '../../components/ui/textarea';
import { Skeleton } from '../../components/ui/skeleton';
import SelettoreDiscipline from '../../components/SelettoreDiscipline';
import LocationAutocomplete, { etichettaSede, sedeDaLuogo } from '../../components/LocationAutocomplete';
import { DISCIPLINES_MAX, disciplineLabel } from '../../lib/disciplines';
import { nomePubblico, NOME_PERSONA_MAX } from '../../lib/nomePubblico';
import { sediDaProfilo } from '../../lib/sedi';
import { compressImage } from '../../lib/compressImage';

// P2 — stessi tetti dell'editor dell'operatore (whitelist 1000, «buona» a 300)
const BIO_MAX = 1000;
const BIO_BUONA = 300;
const BIO_COMPLETA = 600;
const MOTIVO_MIN = 3;
const MOTIVO_MAX = 300;
const BIO_GUIDA = [
  'di cosa ti occupi', 'quali pratiche o percorsi proponi', 'a chi ti rivolgi',
  'qual è la tua visione del benessere', 'qual è il tuo approccio e il tuo modo di lavorare',
  'cosa può aspettarsi chi decide di intraprendere un percorso con te',
];
// i campi testo che il form tocca (chiavi = quelle del payload dell'operatore)
const TESTI = ['nome_persona', 'name', 'tagline', 'bio', 'public_phone', 'instagram', 'website', 'facebook'];

const pulito = (v) => String(v || '').trim();
const sediUguali = (a, b) => JSON.stringify((a || []).map(etichettaSede)) === JSON.stringify((b || []).map(etichettaSede));

const PHOTOS_MAX = 8;

function immaginiDaPayload(data) {
  return {
    cover_url: data?.cover_url || null,
    portrait_url: data?.portrait_url || null,
    photos: Array.isArray(data?.photos) ? data.photos : [],
  };
}

function daPayload(data) {
  return {
    nome_persona: data?.nome_persona || '',
    name: data?.name || '',
    tagline: data?.tagline || '',
    bio: data?.bio || '',
    public_phone: data?.public_phone || '',
    show_contacts: Boolean(data?.show_contacts),
    instagram: data?.instagram || '',
    website: data?.website || '',
    facebook: data?.facebook || '',
    disciplines: data?.disciplines || [],
    sedi: sediDaProfilo(data),
  };
}

export default function OrgProfiloAdminTab({ orgId, onSaved }) {
  const { t } = useTranslation('settings');
  const [base, setBase] = useState(null);     // com'era al caricamento
  const [form, setForm] = useState(null);
  const [errore, setErrore] = useState(false);
  const [saving, setSaving] = useState(false);
  const [motivo, setMotivo] = useState('');
  const [discQuery, setDiscQuery] = useState('');
  const [slug, setSlug] = useState(null);
  // SA6 — le immagini vivono fuori dal diff del form: ogni gesto e' immediato
  const [immagini, setImmagini] = useState(null);
  const [inCorso, setInCorso] = useState(null);      // 'cover' | 'portrait' | url foto | 'photo+'
  const motivoRef = useRef(null);
  const fileRef = useRef(null);
  const [pendente, setPendente] = useState(null);    // { tipo, sostituisci } in attesa del file

  useEffect(() => {
    if (!orgId) return;
    setBase(null); setForm(null); setErrore(false); setMotivo('');
    adminAPI.getOrgPublicProfile(orgId)
      .then((data) => { const f = daPayload(data); setBase(f); setForm(f); setSlug(data?.public_slug || null); setImmagini(immaginiDaPayload(data)); })
      .catch(() => setErrore(true));
  }, [orgId]);

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  // solo i campi CAMBIATI: l'audit deve raccontare cio' che e' successo
  const modifiche = useMemo(() => {
    if (!base || !form) return {};
    const out = {};
    TESTI.forEach((k) => {
      if (pulito(form[k]) !== pulito(base[k])) out[k] = pulito(form[k]) || null;
    });
    if (out.name === null) delete out.name;   // il vuoto NON cancella il marchio (OP4)
    if (Boolean(form.show_contacts) !== Boolean(base.show_contacts)) out.show_contacts = Boolean(form.show_contacts);
    if (JSON.stringify(form.disciplines || []) !== JSON.stringify(base.disciplines || [])) out.disciplines = form.disciplines || [];
    if (!sediUguali(form.sedi, base.sedi)) {
      out.sedi = (form.sedi || []).map((s) => ({
        citta: s.citta || null, provincia: s.provincia || null, regione: s.regione || null,
        paese: s.paese || 'Italia', lat: s.lat ?? null, lng: s.lng ?? null, etichetta: s.etichetta || null,
      }));
    }
    return out;
  }, [base, form]);
  const nModifiche = Object.keys(modifiche).length;
  const motivoOk = pulito(motivo).length >= MOTIVO_MIN && pulito(motivo).length <= MOTIVO_MAX;

  const bioLen = (form?.bio || '').trim().length;
  const bioLivello = bioLen >= BIO_COMPLETA ? 'completa' : bioLen >= BIO_BUONA ? 'buona' : 'breve';

  // la sede principale cambia, le altre restano
  const scegliSede = (place) => {
    const sede = sedeDaLuogo(place);
    if (!sede) return;
    setForm((f) => ({ ...f, sedi: [sede, ...(f.sedi || []).slice(1)] }));
  };
  const togliSede = (i) => setForm((f) => ({ ...f, sedi: (f.sedi || []).filter((_, k) => k !== i) }));

  /* SA6 — un motivo serve anche per le foto: senza, si va a scriverlo */
  const chiediMotivo = () => {
    if (motivoOk) return true;
    toast.error(t('adminProfilo.motivoPrima', { defaultValue: 'Scrivi prima il motivo, in fondo al foglio: resta nel registro.' }));
    motivoRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    motivoRef.current?.focus();
    return false;
  };
  const applicaPayload = (data) => {
    setImmagini(immaginiDaPayload(data));
    onSaved?.(data);
  };
  // apre il selettore: il file arriva in caricaImmagine con il tipo pendente
  const scegliFile = (tipo, sostituisci = null) => {
    if (!chiediMotivo()) return;
    setPendente({ tipo, sostituisci });
    fileRef.current?.click();
  };
  const caricaImmagine = async (file) => {
    const p = pendente; setPendente(null);
    if (!file || !p) return;
    setInCorso(p.sostituisci || (p.tipo === 'photo' ? 'photo+' : p.tipo));
    try {
      let pronto = file;
      try { pronto = await compressImage(file); } catch { /* si manda l'originale */ }
      const data = await adminAPI.uploadOrgProfileImage(orgId, {
        tipo: p.tipo, file: pronto, motivo: pulito(motivo), sostituisci: p.sostituisci || undefined,
      });
      applicaPayload(data);
      toast.success(t('adminProfilo.fotoSostituita', { defaultValue: 'Foto aggiornata: è già sul profilo pubblico.' }));
    } catch (err) {
      toast.error(err?.response?.data?.detail || t('adminProfilo.fotoErrore', { defaultValue: 'Caricamento non riuscito' }));
    } finally { setInCorso(null); }
  };
  const rimuoviImmagine = async (tipo, url = null) => {
    if (!chiediMotivo()) return;
    const cosa = tipo === 'cover' ? 'la copertina' : tipo === 'portrait' ? 'il ritratto' : 'questa foto della galleria';
    if (!window.confirm(`Rimuovere ${cosa} dal profilo pubblico? L’operatore non riceve avvisi: se serve, scrivigli tu.`)) return;
    setInCorso(url || tipo);
    try {
      const data = await adminAPI.deleteOrgProfileImage(orgId, { tipo, url: url || undefined, motivo: pulito(motivo) });
      applicaPayload(data);
      toast.success(t('adminProfilo.fotoRimossa', { defaultValue: 'Foto rimossa dal profilo pubblico.' }));
    } catch (err) {
      toast.error(err?.response?.data?.detail || t('adminProfilo.fotoErrore', { defaultValue: 'Rimozione non riuscita' }));
    } finally { setInCorso(null); }
  };

  const salva = async () => {
    if (!nModifiche) {
      toast.message(t('adminProfilo.nienteDaSalvare', { defaultValue: 'Niente da salvare: non hai cambiato nulla.' }));
      return;
    }
    if (!motivoOk) return;
    setSaving(true);
    try {
      const data = await adminAPI.setOrgPublicProfile(orgId, { ...modifiche, motivo: pulito(motivo) });
      const f = daPayload(data);
      setBase(f); setForm(f); setMotivo('');
      if (data?.public_slug) setSlug(data.public_slug);
      toast.success(t('adminProfilo.salvato', { defaultValue: 'Profilo aggiornato. Ricorda di avvisare l’operatore, se serve.' }));
      onSaved?.(data);
    } catch (err) {
      toast.error(err?.response?.data?.detail || t('adminProfilo.errore', { defaultValue: 'Salvataggio non riuscito' }));
    } finally {
      setSaving(false);
    }
  };

  if (errore) {
    return <p className="text-sm text-red-700">{t('adminProfilo.caricamentoFallito', { defaultValue: 'Impossibile caricare il profilo.' })}</p>;
  }
  if (!form) return <Skeleton className="h-64 w-full rounded-xl" />;

  return (
    <form data-testid="admin-profilo-form" className="space-y-4 text-sm"
      onSubmit={(e) => { e.preventDefault(); salva(); }}>
      <p className="text-xs text-muted-foreground">
        {t('adminProfilo.intro', { defaultValue: 'Correggi solo quello che serve: si salvano i campi cambiati e ogni modifica resta nel registro con il tuo motivo. Le foto si sostituiscono o rimuovono subito, qui sotto; la pagina link resta all’operatore.' })}
      </p>

      {/* SA6 — le foto: copertina, ritratto, galleria. Gesti immediati,
          ciascuno col motivo (quello in fondo) e la sua riga di audit. */}
      <input ref={fileRef} type="file" accept="image/*" className="hidden" data-testid="admin-foto-file"
        onChange={(e) => { caricaImmagine(e.target.files?.[0]); e.target.value = ''; }} />
      <div className="rounded-xl border p-3 space-y-3" data-testid="admin-foto">
        <div className="flex items-center justify-between gap-2">
          <Label>{t('adminProfilo.foto', { defaultValue: 'Foto del profilo pubblico' })}</Label>
          <span className="text-[11px] text-muted-foreground">
            {t('adminProfilo.fotoNota', { defaultValue: 'Ogni sostituzione o rimozione è immediata e va nel registro col motivo.' })}
          </span>
        </div>
        <div className="grid gap-3 sm:grid-cols-[1fr_auto]">
          {/* copertina */}
          <div>
            <p className="text-[11px] text-muted-foreground mb-1">{t('adminProfilo.copertina', { defaultValue: 'Copertina' })}</p>
            <div className="relative h-28 overflow-hidden rounded-lg border bg-muted/40" data-testid="admin-foto-cover">
              {immagini?.cover_url
                ? <img src={immagini.cover_url} alt="" className="h-full w-full object-cover" />
                : <div className="flex h-full items-center justify-center gap-1.5 text-xs text-muted-foreground"><ImageOff className="h-4 w-4" aria-hidden />{t('adminProfilo.nessunaFoto', { defaultValue: 'nessuna' })}</div>}
              {inCorso === 'cover' && <div className="absolute inset-0 flex items-center justify-center bg-white/70"><Loader2 className="h-5 w-5 animate-spin" aria-hidden /></div>}
            </div>
            <div className="mt-1.5 flex flex-wrap gap-1.5">
              <button type="button" onClick={() => scegliFile('cover')} disabled={!!inCorso} data-testid="admin-foto-cover-sostituisci"
                className="inline-flex items-center gap-1 rounded-md border px-2 py-1 text-xs hover:bg-muted/40 disabled:opacity-50">
                <RefreshCw className="h-3 w-3" aria-hidden />{immagini?.cover_url ? t('adminProfilo.sostituisci', { defaultValue: 'Sostituisci' }) : t('adminProfilo.carica', { defaultValue: 'Carica' })}
              </button>
              {immagini?.cover_url && (
                <button type="button" onClick={() => rimuoviImmagine('cover')} disabled={!!inCorso} data-testid="admin-foto-cover-rimuovi"
                  className="inline-flex items-center gap-1 rounded-md border border-red-200 px-2 py-1 text-xs text-red-700 hover:bg-red-50 disabled:opacity-50">
                  <Trash2 className="h-3 w-3" aria-hidden />{t('adminProfilo.rimuovi', { defaultValue: 'Rimuovi' })}
                </button>
              )}
            </div>
          </div>
          {/* ritratto */}
          <div className="sm:w-36">
            <p className="text-[11px] text-muted-foreground mb-1">{t('adminProfilo.ritratto', { defaultValue: 'Ritratto' })}</p>
            <div className="relative h-28 w-28 overflow-hidden rounded-full border bg-muted/40" data-testid="admin-foto-portrait">
              {immagini?.portrait_url
                ? <img src={immagini.portrait_url} alt="" className="h-full w-full object-cover" />
                : <div className="flex h-full items-center justify-center text-xs text-muted-foreground">{t('adminProfilo.nessunaFoto', { defaultValue: 'nessuna' })}</div>}
              {inCorso === 'portrait' && <div className="absolute inset-0 flex items-center justify-center bg-white/70"><Loader2 className="h-5 w-5 animate-spin" aria-hidden /></div>}
            </div>
            <div className="mt-1.5 flex flex-wrap gap-1.5">
              <button type="button" onClick={() => scegliFile('portrait')} disabled={!!inCorso} data-testid="admin-foto-portrait-sostituisci"
                className="inline-flex items-center gap-1 rounded-md border px-2 py-1 text-xs hover:bg-muted/40 disabled:opacity-50">
                <RefreshCw className="h-3 w-3" aria-hidden />{immagini?.portrait_url ? t('adminProfilo.sostituisci', { defaultValue: 'Sostituisci' }) : t('adminProfilo.carica', { defaultValue: 'Carica' })}
              </button>
              {immagini?.portrait_url && (
                <button type="button" onClick={() => rimuoviImmagine('portrait')} disabled={!!inCorso} data-testid="admin-foto-portrait-rimuovi"
                  className="inline-flex items-center gap-1 rounded-md border border-red-200 px-2 py-1 text-xs text-red-700 hover:bg-red-50 disabled:opacity-50">
                  <Trash2 className="h-3 w-3" aria-hidden />{t('adminProfilo.rimuovi', { defaultValue: 'Rimuovi' })}
                </button>
              )}
            </div>
          </div>
        </div>
        {/* galleria */}
        <div>
          <p className="text-[11px] text-muted-foreground mb-1">
            {t('adminProfilo.galleria', { defaultValue: 'Galleria' })} · {(immagini?.photos || []).length}/{PHOTOS_MAX}
          </p>
          <div className="grid grid-cols-4 gap-2 sm:grid-cols-6" data-testid="admin-foto-galleria">
            {(immagini?.photos || []).map((url) => (
              <div key={url} className="group relative h-20 overflow-hidden rounded-lg border" data-testid="admin-foto-photo">
                <img src={url} alt="" className="h-full w-full object-cover" />
                {inCorso === url
                  ? <div className="absolute inset-0 flex items-center justify-center bg-white/70"><Loader2 className="h-4 w-4 animate-spin" aria-hidden /></div>
                  : (
                    <div className="absolute inset-x-0 bottom-0 flex justify-center gap-1 bg-black/55 p-1 opacity-0 transition-opacity group-hover:opacity-100 group-focus-within:opacity-100">
                      <button type="button" onClick={() => scegliFile('photo', url)} disabled={!!inCorso} aria-label="Sostituisci foto"
                        className="rounded bg-white/90 p-1 text-gray-800 hover:bg-white"><RefreshCw className="h-3 w-3" aria-hidden /></button>
                      <button type="button" onClick={() => rimuoviImmagine('photo', url)} disabled={!!inCorso} aria-label="Rimuovi foto"
                        className="rounded bg-white/90 p-1 text-red-700 hover:bg-white"><Trash2 className="h-3 w-3" aria-hidden /></button>
                    </div>
                  )}
              </div>
            ))}
            {(immagini?.photos || []).length < PHOTOS_MAX && (
              <button type="button" onClick={() => scegliFile('photo')} disabled={!!inCorso} data-testid="admin-foto-photo-aggiungi"
                className="flex h-20 items-center justify-center rounded-lg border-2 border-dashed text-xl text-muted-foreground hover:border-primary/50 disabled:opacity-50">
                {inCorso === 'photo+' ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : '+'}
              </button>
            )}
          </div>
        </div>
      </div>

      {/* identita': persona + marchio, anteprima «Nome · Marchio» */}
      <div className="grid gap-3 sm:grid-cols-2">
        <div>
          <Label htmlFor="ap-nome-persona">{t('adminProfilo.nomePersona', { defaultValue: 'Nome e cognome' })}</Label>
          <Input id="ap-nome-persona" value={form.nome_persona} maxLength={NOME_PERSONA_MAX}
            onChange={(e) => set('nome_persona', e.target.value)} data-testid="admin-profilo-nome-persona" />
        </div>
        <div>
          <Label htmlFor="ap-marchio">{t('adminProfilo.marchio', { defaultValue: 'Nome dell’attività (marchio)' })}</Label>
          <Input id="ap-marchio" value={form.name} maxLength={120}
            onChange={(e) => set('name', e.target.value)} data-testid="admin-profilo-marchio" />
        </div>
      </div>
      <p className="text-xs text-muted-foreground" data-testid="admin-profilo-anteprima">
        {t('adminProfilo.anteprimaNome', { defaultValue: 'Il pubblico leggerà:' })}{' '}
        <strong className="text-foreground">{nomePubblico(form.nome_persona, form.name) || '—'}</strong>
        {slug && <> · <a href={`/o/${slug}`} target="_blank" rel="noreferrer" className="underline underline-offset-2">/o/{slug}</a></>}
      </p>

      <div>
        <Label htmlFor="ap-tagline">{t('adminProfilo.tagline', { defaultValue: 'Una riga che presenta (tagline)' })}</Label>
        <Input id="ap-tagline" value={form.tagline} maxLength={80} onChange={(e) => set('tagline', e.target.value)} />
      </div>

      {/* bio con contatore e guida */}
      <div>
        <div className="flex items-center justify-between gap-2">
          <Label htmlFor="ap-bio">{t('adminProfilo.bio', { defaultValue: 'Descrizione' })}</Label>
          <span className={`text-[11px] ${bioLivello === 'breve' ? 'text-amber-700' : 'text-muted-foreground'}`} data-testid="admin-profilo-bio-contatore">
            {bioLen}/{BIO_MAX} · {bioLivello === 'breve'
              ? t('adminProfilo.bioBreve', { defaultValue: 'breve: sotto i 300 caratteri presenta poco' })
              : bioLivello === 'buona'
                ? t('adminProfilo.bioBuona', { defaultValue: 'buona' })
                : t('adminProfilo.bioCompleta', { defaultValue: 'completa' })}
          </span>
        </div>
        <Textarea id="ap-bio" rows={7} maxLength={BIO_MAX} value={form.bio}
          onChange={(e) => set('bio', e.target.value.slice(0, BIO_MAX))} data-testid="admin-profilo-bio" />
        <details className="mt-1 text-xs text-muted-foreground" open={bioLen < BIO_BUONA}>
          <summary className="cursor-pointer">{t('adminProfilo.bioGuidaTitolo', { defaultValue: 'La guida in sei punti (quella dell’operatore)' })}</summary>
          <ul className="list-disc pl-5 mt-1 space-y-0.5">
            {BIO_GUIDA.map((p) => <li key={p}>{p}</li>)}
          </ul>
        </details>
      </div>

      {/* telefono + pubblico/privato */}
      <div className="grid gap-3 sm:grid-cols-2">
        <div>
          <Label htmlFor="ap-telefono">{t('adminProfilo.telefono', { defaultValue: 'Telefono' })}</Label>
          <Input id="ap-telefono" type="tel" value={form.public_phone} maxLength={40}
            onChange={(e) => set('public_phone', e.target.value)} data-testid="admin-profilo-telefono" />
        </div>
        <div className="flex items-end">
          <button type="button" data-testid="admin-profilo-show-contacts"
            onClick={() => set('show_contacts', !form.show_contacts)}
            className="inline-flex items-center gap-1.5 rounded-md border px-3 py-2 text-xs hover:bg-muted/40">
            {form.show_contacts ? <Unlock className="h-3.5 w-3.5" aria-hidden /> : <Lock className="h-3.5 w-3.5" aria-hidden />}
            {form.show_contacts
              ? t('adminProfilo.contattiMostrati', { defaultValue: 'Contatti mostrati sul profilo' })
              : t('adminProfilo.contattiPrivati', { defaultValue: 'Contatti privati (solo per Aurya)' })}
          </button>
        </div>
      </div>

      {/* discipline: lo stesso selettore dell'operatore */}
      <div>
        <Label>{t('adminProfilo.discipline', { defaultValue: 'Discipline' })}</Label>
        <div className="mt-1 rounded-xl border p-3">
          <SelettoreDiscipline
            value={form.disciplines || []}
            query={discQuery}
            onQuery={setDiscQuery}
            max={DISCIPLINES_MAX}
            onToggle={(s) => setForm((f) => {
              const cur = f.disciplines || [];
              if (!cur.includes(s) && cur.length >= DISCIPLINES_MAX) return f;
              return { ...f, disciplines: cur.includes(s) ? cur.filter((x) => x !== s) : [...cur, s] };
            })}
          />
        </div>
        {(form.disciplines || []).length > 0 && (
          <p className="mt-1 text-[11px] text-muted-foreground">
            {(form.disciplines || []).map(disciplineLabel).join(' · ')}
          </p>
        )}
      </div>

      {/* sede principale */}
      <div>
        <Label>{t('adminProfilo.sede', { defaultValue: 'Sede principale' })}</Label>
        {(form.sedi || []).length > 0 && (
          <ul className="mt-1 space-y-1">
            {form.sedi.map((s, i) => (
              <li key={`${etichettaSede(s)}-${i}`} className="flex items-center justify-between gap-2 rounded-md border px-2.5 py-1.5 text-xs">
                <span>{i === 0 ? <strong>{etichettaSede(s)}</strong> : etichettaSede(s)}{i === 0 && (form.sedi.length > 1) && (
                  <span className="ml-1 text-muted-foreground">{t('adminProfilo.sedePrincipale', { defaultValue: '(principale)' })}</span>
                )}</span>
                <button type="button" onClick={() => togliSede(i)} aria-label={`Togli ${etichettaSede(s)}`}
                  className="rounded p-0.5 text-muted-foreground hover:bg-muted hover:text-foreground">
                  <X className="h-3.5 w-3.5" aria-hidden />
                </button>
              </li>
            ))}
          </ul>
        )}
        <LocationAutocomplete
          key={`sede-${(form.sedi || []).length}-${etichettaSede((form.sedi || [])[0])}`}
          value=""
          placeholder={(form.sedi || []).length
            ? t('adminProfilo.sedeCambia', { defaultValue: 'Cambia la sede principale: cerca e scegli dalla lista…' })
            : 'Ostuni, Puglia…'}
          onSelect={scegliSede}
        />
      </div>

      {/* social */}
      <div className="grid gap-3 sm:grid-cols-3">
        <div>
          <Label htmlFor="ap-ig">Instagram</Label>
          <Input id="ap-ig" value={form.instagram} maxLength={120} placeholder="nome_utente"
            onChange={(e) => set('instagram', e.target.value)} />
        </div>
        <div>
          <Label htmlFor="ap-sito">{t('adminProfilo.sito', { defaultValue: 'Sito' })}</Label>
          <Input id="ap-sito" value={form.website} maxLength={200} placeholder="www.esempio.it"
            onChange={(e) => set('website', e.target.value)} />
        </div>
        <div>
          <Label htmlFor="ap-fb">Facebook</Label>
          <Input id="ap-fb" value={form.facebook} maxLength={200}
            onChange={(e) => set('facebook', e.target.value)} />
        </div>
      </div>

      {/* motivo + salva */}
      <div className="rounded-xl border border-[#376254]/30 bg-[#376254]/5 p-3 space-y-2">
        <Label htmlFor="ap-motivo">{t('adminProfilo.motivo', { defaultValue: 'Motivo della modifica (resta nel registro, vale anche per le foto)' })}</Label>
        <Input id="ap-motivo" ref={motivoRef} value={motivo} maxLength={MOTIVO_MAX} data-testid="admin-profilo-motivo"
          placeholder={t('adminProfilo.motivoPlaceholder', { defaultValue: 'es. bio riscritta su richiesta al telefono del 24/9' })}
          onChange={(e) => setMotivo(e.target.value)} />
        <div className="flex items-center justify-between gap-2 flex-wrap">
          <span className="text-[11px] text-muted-foreground">
            {nModifiche
              ? t('adminProfilo.nCampi', { defaultValue: '{{n}} campi da salvare', n: nModifiche })
              : t('adminProfilo.nessunaModifica', { defaultValue: 'Nessuna modifica' })}
            {nModifiche > 0 && !motivoOk && ` · ${t('adminProfilo.motivoServe', { defaultValue: 'scrivi il motivo (almeno 3 caratteri)' })}`}
          </span>
          <Button type="submit" size="sm" disabled={saving || !nModifiche || !motivoOk} data-testid="admin-profilo-salva">
            {saving ? t('adminProfilo.salvo', { defaultValue: 'Salvo…' }) : t('adminProfilo.salva', { defaultValue: 'Salva le modifiche' })}
          </Button>
        </div>
      </div>
    </form>
  );
}
