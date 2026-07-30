/**
 * ListinoPage — /listino (TW1, docs/LISTINO_PIANO_2026-07.md).
 *
 * IL listino alla Treatwell: una pagina, righe inline, zero wizard.
 * Una riga = Product item_type=service (invariante I8: stessa API
 * products di sempre sotto, nessuna nuova collection). Default snelli:
 * transaction_mode=request (si riceve la richiesta, Stripe facoltativo),
 * agenda ufficiale, pubblicato subito.
 *
 * Lo store tecnico invisibile si garantisce da solo al primo accesso
 * (storesAPI.ensureDefault, idempotente): l'operatore non deve sapere
 * che esiste. "Impostazioni avanzate" apre /services/:id che da PS2
 * e' l'editor AVANZATO onesto (landing, traduzioni, orari, campi
 * ordine), non il percorso primario.
 */
import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import {
  ChevronDown, ChevronUp, Eye, EyeOff, ExternalLink, Loader2, Plus,
  Settings2, Trash2,
} from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '../../components/ui/button';
import { Card, CardContent } from '../../components/ui/card';
import { productsAPI } from '../../api/products';
import { storesAPI } from '../../api/stores';
import { serviceOptionsAPI } from '../../api/serviceOptions';
import api from '../../api/client';
import { trackEvent } from '../../lib/analytics';
import { AppLayout, Header } from '../../components/Layout';
// LM1 — riuso puro: l'editor opzioni e l'avviso Stripe sono gli stessi
// componenti di ServiceDashboardPage, nessuna copia locale.
import ServiceOptionsEditor from '../services/components/ServiceOptionsEditor';
import StripeRequiredAlert from '../../components/StripeRequiredAlert';
// PV7 — patto di responsabilita' (DPA art. 28): banner + dialog + gate
// alla creazione. Stato condiviso in cache (una GET /legal/dpa/status).
import DpaPactBanner from '../../components/legal/DpaPactBanner';
import DpaPactDialog from '../../components/legal/DpaPactDialog';
import useDpaStatus from '../../hooks/useDpaStatus';

// Tassonomia service (models/retreat_taxonomy.py) + fallback "altro"
const SERVICE_CATEGORIES = {
  trattamenti: 'Trattamenti & Massaggi',
  consulenze: 'Consulenze',
  lezioni: 'Lezioni private',
  cerimonie: 'Cerimonie',
};
const DURATIONS = [30, 45, 60, 75, 90, 120];
const MODES = [
  { key: 'in_person', label: 'In presenza' },
  { key: 'online', label: 'Online' },
  { key: 'both', label: 'Entrambe' },
];

const EMPTY_ROW = {
  name: '', category: 'consulenze', duration: 60, price: '',
  onRequest: false, mode: 'in_person', note: '',
};

function rowFromProduct(p) {
  const meta = p.metadata || {};
  return {
    id: p.id,
    name: p.name,
    category: p.category || '',
    duration: Number(meta.duration_minutes) || 60,
    price: p.unit_price != null ? String(p.unit_price) : '',
    onRequest: p.price_mode === 'inquiry',
    mode: meta.service_mode || 'in_person',
    note: p.description || '',
    published: !!p.is_published,
    transactionMode: p.transaction_mode || 'request',
    // LM1 — configurazione completa nella riga: foto, agenda, incasso.
    // Il calendario ufficiale e' ON di default (agenda unica): se il
    // flag non e' mai stato scritto, la riga lo mostra e salva attivo.
    imageUrl: p.image_url || '',
    useDefaultSchedule: 'use_default_schedule' in meta
      ? !!meta.use_default_schedule : true,
    // AP-L — requisiti e condizioni del servizio (terms_content, F4):
    // promossi in superficie, finiscono nella checkbox dinamica
    // "Accetto le condizioni di {operatore}" al checkout.
    termsContent: meta.terms_content || '',
    // metadata integrale del prodotto: serve al salvataggio per NON
    // perdere i campi avanzati (terms, order_fields, cover, ...)
    rawMeta: meta,
  };
}

function payloadFromRow(row) {
  return {
    name: row.name.trim(),
    category: row.category || null,
    description: row.note.trim() || null,
    unit_price: row.onRequest ? null : (Number(row.price) || 0),
    price_mode: row.onRequest ? 'inquiry' : 'fixed',
    metadata: {
      duration_minutes: Number(row.duration) || 60,
      service_mode: row.mode,
    },
  };
}

function RowFields({ value, onChange }) {
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
      <div className="sm:col-span-2">
        <label className="mb-1 block text-xs font-medium text-gray-600">Nome del servizio *</label>
        <input value={value.name}
               onChange={e => onChange({ ...value, name: e.target.value })}
               placeholder="Es. Seduta di reiki, Lezione privata di yoga…"
               className="w-full rounded-lg border border-input px-3 py-2 text-sm" />
      </div>
      <div>
        <label className="mb-1 block text-xs font-medium text-gray-600">Categoria</label>
        <select value={value.category}
                onChange={e => onChange({ ...value, category: e.target.value })}
                className="w-full rounded-lg border border-input px-3 py-2 text-sm bg-white">
          {Object.entries(SERVICE_CATEGORIES).map(([k, l]) => (
            <option key={k} value={k}>{l}</option>
          ))}
        </select>
      </div>
      <div>
        <label className="mb-1 block text-xs font-medium text-gray-600">Durata</label>
        <select value={value.duration}
                onChange={e => onChange({ ...value, duration: Number(e.target.value) })}
                className="w-full rounded-lg border border-input px-3 py-2 text-sm bg-white">
          {DURATIONS.map(d => <option key={d} value={d}>{d} minuti</option>)}
        </select>
      </div>
      <div>
        <label className="mb-1 block text-xs font-medium text-gray-600">Prezzo</label>
        <div className="flex items-center gap-2">
          <input type="number" min="0" step="1" value={value.price}
                 disabled={value.onRequest}
                 onChange={e => onChange({ ...value, price: e.target.value })}
                 placeholder="60"
                 className="w-24 rounded-lg border border-input px-3 py-2 text-sm disabled:bg-gray-50 disabled:text-gray-400" />
          <span className="text-sm text-gray-500">€</span>
          <label className="ml-2 flex items-center gap-1.5 text-xs text-gray-600">
            <input type="checkbox" checked={value.onRequest}
                   onChange={e => onChange({ ...value, onRequest: e.target.checked })} />
            su richiesta
          </label>
        </div>
      </div>
      <div>
        <label className="mb-1 block text-xs font-medium text-gray-600">Come si svolge</label>
        <div className="flex gap-1.5">
          {MODES.map(m => (
            <button key={m.key} type="button"
                    onClick={() => onChange({ ...value, mode: m.key })}
                    className={`rounded-full border px-3 py-1.5 text-xs font-medium ${
                      value.mode === m.key
                        ? 'border-primary bg-primary text-white'
                        : 'border-gray-300 bg-white text-gray-600'}`}>
              {m.label}
            </button>
          ))}
        </div>
      </div>
      <div className="sm:col-span-2">
        <label className="mb-1 block text-xs font-medium text-gray-600">Note (facoltative)</label>
        <input value={value.note}
               onChange={e => onChange({ ...value, note: e.target.value })}
               placeholder="Es. Prima seduta conoscitiva inclusa. Porta un tappetino."
               className="w-full rounded-lg border border-input px-3 py-2 text-sm" />
      </div>
    </div>
  );
}

// LM1 — sezione richiudibile della riga espansa: la configurazione
// avanza per momenti progressivi, mai tutto aperto insieme.
function RowSection({ id, title, hint, open, onToggle, children }) {
  return (
    <div className="rounded-lg border border-gray-200 bg-gray-50/40">
      <button type="button" onClick={onToggle}
              data-testid={`listino-sezione-${id}`}
              className="flex w-full items-center justify-between gap-2 px-3 py-2.5 text-left">
        <span className="text-sm font-medium text-gray-800">{title}</span>
        <span className="flex items-center gap-2">
          {hint && <span className="text-xs text-gray-400">{hint}</span>}
          {open
            ? <ChevronUp className="h-4 w-4 text-gray-400" aria-hidden />
            : <ChevronDown className="h-4 w-4 text-gray-400" aria-hidden />}
        </span>
      </button>
      {open && (
        <div className="border-t border-gray-100 bg-white px-3 py-3 rounded-b-lg">
          {children}
        </div>
      )}
    </div>
  );
}

export default function ListinoPage() {
  // PS2 — i label verso l'editor avanzato vivono nel namespace
  // 'products' (bundle admin, caricato dal Layout).
  const { t } = useTranslation('products');
  const navigate = useNavigate();
  const [rows, setRows] = useState(null);       // null = loading
  const [profileSlug, setProfileSlug] = useState(null);
  const [adding, setAdding] = useState(false);
  const [draft, setDraft] = useState(EMPTY_ROW);
  const [expandedId, setExpandedId] = useState(null);
  const [edit, setEdit] = useState(null);
  const [busy, setBusy] = useState(false);
  // LM1 — accordion della riga espansa ('varianti' | 'incasso') e
  // opzioni del servizio: options e' la bozza in modifica, savedOptions
  // lo stato del server (serve al diff in salvataggio).
  const [openSection, setOpenSection] = useState(null);
  const [options, setOptions] = useState([]);
  const [savedOptions, setSavedOptions] = useState([]);
  // PV7 — gate del patto: se il DPA non e' accettato, la creazione si
  // ferma, si apre il dialog e alla firma l'azione RIPRENDE da sola.
  const { known: dpaKnown, acknowledged: dpaAcknowledged } = useDpaStatus();
  const [pactOpen, setPactOpen] = useState(false);
  const pactPendingRef = useRef(false);

  const load = async () => {
    const res = await productsAPI.list(true, 500);
    const services = (res.data?.products || res.data || [])
      .filter(p => p.item_type === 'service')
      .map(rowFromProduct);
    setRows(services);
  };

  useEffect(() => {
    // store tecnico garantito PRIMA di qualsiasi pubblicazione: cosi'
    // il gate store-first non si presenta mai all'operatore
    storesAPI.ensureDefault().catch(() => { /* best-effort, il publish riprova */ });
    load().catch(() => setRows([]));
    // il link "vedi il tuo profilo" (public_slug o slug store)
    api.get('/organizations/current/public-profile')
      .then(res => setProfileSlug(res.data?.public_slug || null))
      .catch(() => {});
  }, []);

  // LM1 — le opzioni si caricano quando una riga salvata si espande
  // (serve il product id: per questo gli accordion non esistono sulla
  // riga nuova). Caricamento anticipato: cosi' l'intestazione
  // dell'accordion puo' dire subito quante varianti ci sono.
  useEffect(() => {
    setOpenSection(null);
    setOptions([]);
    setSavedOptions([]);
    if (!expandedId) return undefined;
    let alive = true;
    serviceOptionsAPI.list(expandedId)
      .then(res => {
        if (!alive) return;
        const opts = res.data?.options || [];
        setOptions(opts);
        setSavedOptions(opts);
      })
      .catch(() => {});
    return () => { alive = false; };
  }, [expandedId]);

  const grouped = useMemo(() => {
    const g = {};
    (rows || []).forEach(r => {
      const key = SERVICE_CATEGORIES[r.category] ? r.category : '_altro';
      (g[key] = g[key] || []).push(r);
    });
    return g;
  }, [rows]);

  const anyPublished = (rows || []).some(r => r.published);

  const saveNew = async () => {
    if (!draft.name.trim()) { toast.error('Dai un nome al servizio'); return; }
    // PV7 — prima di vendere si firma il patto: il dialog appare PRIMA
    // della creazione e alla firma l'azione riparte (performSaveNew,
    // SENZA ripassare dal gate: lo stato dell'hook potrebbe non essere
    // ancora ri-renderizzato nel closure corrente).
    if (dpaKnown && !dpaAcknowledged) {
      pactPendingRef.current = true;
      setPactOpen(true);
      return;
    }
    await performSaveNew();
  };

  const performSaveNew = async () => {
    setBusy(true);
    // TW4 — metrica di attivazione: il PRIMO servizio che va online
    const isFirstOnline = !(rows || []).some(r => r.published);
    try {
      await storesAPI.ensureDefault();     // idempotente, race-safe
      const res = await productsAPI.create({
        ...payloadFromRow(draft),
        item_type: 'service',
        transaction_mode: 'request',       // default snello: richiesta
        is_published: true,                // online subito
      });
      if (isFirstOnline) trackEvent('first_service_online');
      setDraft(EMPTY_ROW);
      setAdding(false);
      await load();
      // LM1 — la riga appena creata si apre subito in modifica: ora ha
      // un id, quindi opzioni, prenotazione e foto si rifiniscono qui.
      const created = res.data;
      if (created?.id) {
        setExpandedId(created.id);
        setEdit(rowFromProduct(created));
      }
      toast.success('Servizio nel listino, gia’ online');
    } catch (e) {
      // PV7 — rete di sicurezza: se lo status in cache era stantio, il
      // server risponde comunque 409 DPA_REQUIRED; niente toast di
      // errore, si apre il dialog del patto e si riprende alla firma.
      if (e?.response?.status === 409
          && e?.response?.data?.detail?.code === 'DPA_REQUIRED') {
        pactPendingRef.current = true;
        setPactOpen(true);
      } else {
        toast.error(e?.response?.data?.detail?.message
          || e?.response?.data?.detail || 'Salvataggio non riuscito');
      }
    } finally { setBusy(false); }
  };

  // LM1 — persiste le opzioni con lo stesso diff di ServiceDashboardPage
  // (delete assenti, update per id, create nuove). Le righe senza
  // etichetta sono bozze incomplete: si ignorano.
  const saveRowOptions = async (productId) => {
    const wanted = options.filter(o => (o.label || '').trim());
    const body = (o) => ({
      label: o.label,
      description: o.description || null,
      price: Number(o.price) || 0,
      duration_minutes_override: o.duration_minutes_override
        ? Number(o.duration_minutes_override) : null,
      sort_order: o.sort_order ?? 0,
      is_active: o.is_active !== false,
    });
    const oldById = new Map(savedOptions.filter(o => o.id).map(o => [o.id, o]));
    for (const existing of savedOptions) {
      if (existing.id && !wanted.find(n => n.id === existing.id)) {
        try { await serviceOptionsAPI.delete(productId, existing.id); } catch { /* ignore */ }
      }
    }
    for (const o of wanted) {
      if (o.id && oldById.has(o.id)) {
        try { await serviceOptionsAPI.update(productId, o.id, body(o)); } catch { /* ignore */ }
      } else {
        try { await serviceOptionsAPI.create(productId, body(o)); } catch { /* ignore */ }
      }
    }
  };

  const saveEdit = async () => {
    if (!edit?.name.trim()) { toast.error('Il nome non puo’ restare vuoto'); return; }
    setBusy(true);
    try {
      const base = payloadFromRow(edit);
      await productsAPI.update(edit.id, {
        ...base,
        transaction_mode: edit.transactionMode,
        image_url: edit.imageUrl?.trim() || null,
        // merge attento del metadata: rawMeta preserva i campi avanzati
        // (terms, order_fields, cover, ...), base.metadata porta i campi
        // della riga, il flag agenda si scrive esplicito.
        metadata: {
          ...edit.rawMeta,
          ...base.metadata,
          use_default_schedule: !!edit.useDefaultSchedule,
          // AP-L — requisiti del servizio: testo vuoto = nessuna
          // checkbox condizioni al checkout (null, non stringa vuota)
          terms_content: edit.termsContent?.trim() || null,
        },
      });
      await saveRowOptions(edit.id);
      setExpandedId(null); setEdit(null);
      await load();
      toast.success('Servizio aggiornato');
    } catch { toast.error('Aggiornamento non riuscito'); }
    finally { setBusy(false); }
  };

  const togglePublish = async (row) => {
    try {
      if (!row.published) await storesAPI.ensureDefault();
      await productsAPI.update(row.id, { is_published: !row.published });
      await load();
    } catch { toast.error('Operazione non riuscita'); }
  };

  const toggleAll = async (publish) => {
    setBusy(true);
    try {
      if (publish) await storesAPI.ensureDefault();
      await Promise.all((rows || [])
        .filter(r => r.published !== publish)
        .map(r => productsAPI.update(r.id, { is_published: publish })));
      await load();
      toast.success(publish ? 'Listino online' : 'Listino nascosto');
    } catch { toast.error('Operazione non riuscita'); }
    finally { setBusy(false); }
  };

  const removeRow = async (row) => {
    // eslint-disable-next-line no-alert
    if (!window.confirm(`Togliere "${row.name}" dal listino?`)) return;
    try {
      await productsAPI.delete(row.id);
      await load();
      toast.success('Servizio rimosso');
    } catch { toast.error('Rimozione non riuscita'); }
  };

  const fmtPrice = (r) => r.onRequest
    ? 'Su richiesta'
    : (r.price !== '' ? `${Number(r.price).toFixed(0)} €` : '—');



  // RS0 — la pagina vive DENTRO la shell dell'app come tutte le
  // altre (AppLayout + Header): il menu non deve mai sparire
  if (rows === null) {
    return (
      <AppLayout>
        <Header title="Il tuo listino" />
        <div className="flex justify-center py-24">
          <Loader2 className="h-7 w-7 animate-spin text-primary" aria-label="…" /></div>
      </AppLayout>
    );
  }

  return (
    <AppLayout>
      <Header
        title="Il tuo listino"
        subtitle="I servizi che offri, come appaiono sul tuo profilo pubblico. Una riga, un servizio."
      />
      <div className="p-4 md:p-8">
    <div className="mx-auto max-w-3xl space-y-5" data-testid="listino-page">
      {/* PV7 — patto di responsabilita' non ancora firmato: banner
          sobrio ma visibile. Firmato → nessun rumore (il banner si
          auto-nasconde, lo stato vive in SalesConditionsCard). */}
      <DpaPactBanner onRead={() => { pactPendingRef.current = false; setPactOpen(true); }} />
      <div className="flex flex-wrap items-center justify-end gap-3">
        <div className="flex items-center gap-2">
          {profileSlug && (
            <a href={`/o/${profileSlug}`} target="_blank" rel="noreferrer"
               className="inline-flex items-center gap-1.5 text-sm font-medium text-primary hover:underline">
              <ExternalLink className="h-4 w-4" aria-hidden />
              Vedi il tuo profilo
            </a>
          )}
          {rows.length > 0 && (
            <Button variant="outline" size="sm" disabled={busy}
                    onClick={() => toggleAll(!anyPublished)}
                    data-testid="listino-toggle-all">
              {anyPublished
                ? <><EyeOff className="mr-1.5 h-4 w-4" />Nascondi listino</>
                : <><Eye className="mr-1.5 h-4 w-4" />Metti online</>}
            </Button>
          )}
        </div>
      </div>

      {/* riga nuova */}
      {adding ? (
        <Card><CardContent className="pt-5">
          <RowFields value={draft} onChange={setDraft} />
          <div className="mt-4 flex gap-2">
            <Button onClick={saveNew} disabled={busy} data-testid="listino-save-new">
              {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Aggiungi al listino'}
            </Button>
            <Button variant="ghost" onClick={() => { setAdding(false); setDraft(EMPTY_ROW); }}>
              Annulla
            </Button>
          </div>
        </CardContent></Card>
      ) : (
        <Button onClick={() => setAdding(true)} data-testid="listino-add">
          <Plus className="mr-1.5 h-4 w-4" />
          Aggiungi un servizio
        </Button>
      )}

      {rows.length === 0 && !adding && (
        <Card><CardContent className="py-10 text-center text-sm text-muted-foreground">
          Il listino è vuoto. Aggiungi il tuo primo servizio: bastano nome e prezzo,
          al resto pensiamo noi (richieste dei clienti in arrivo via email, calendario
          ufficiale, pagamento online attivabile dopo con Stripe).
        </CardContent></Card>
      )}

      {/* righe per categoria */}
      {Object.entries(grouped).map(([catKey, catRows]) => (
        <div key={catKey}>
          <p className="mb-2 mt-2 font-brand text-[11px] uppercase tracking-[0.25em] text-[#8a7440] select-none">
            {SERVICE_CATEGORIES[catKey] || 'Altro'}
          </p>
          <div className="space-y-2">
            {catRows.map(row => (
              <Card key={row.id} className={row.published ? '' : 'opacity-60'}>
                <CardContent className="py-3">
                  <div className="flex items-center gap-3">
                    <button type="button" className="flex-1 text-left"
                            onClick={() => {
                              if (expandedId === row.id) { setExpandedId(null); setEdit(null); }
                              else { setExpandedId(row.id); setEdit({ ...row }); }
                            }}>
                      <span className="font-medium text-gray-900">{row.name}</span>
                      <span className="ml-2 text-xs text-gray-400">
                        {row.duration} min · {MODES.find(m => m.key === row.mode)?.label}
                        {row.transactionMode === 'direct' ? ' · pagamento online' : ''}
                      </span>
                    </button>
                    <span className="text-sm font-semibold text-gray-900 whitespace-nowrap">{fmtPrice(row)}</span>
                    <button type="button" title={row.published ? 'Nascondi' : 'Pubblica'}
                            onClick={() => togglePublish(row)}
                            className="text-gray-400 hover:text-primary">
                      {row.published ? <Eye className="h-4 w-4" /> : <EyeOff className="h-4 w-4" />}
                    </button>
                    <button type="button" onClick={() => {
                      if (expandedId === row.id) { setExpandedId(null); setEdit(null); }
                      else { setExpandedId(row.id); setEdit({ ...row }); }
                    }} className="text-gray-400 hover:text-gray-700">
                      {expandedId === row.id ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                    </button>
                  </div>

                  {expandedId === row.id && edit && (
                    <div className="mt-4 border-t border-gray-100 pt-4">
                      <RowFields value={edit} onChange={setEdit} />

                      {/* LM1 — configurazione completa in un passo: due
                          momenti progressivi, solo su righe salvate
                          (le opzioni vivono sul product id) */}
                      <div className="mt-4 space-y-2">
                        <RowSection
                          id="varianti"
                          title="Opzioni e varianti"
                          hint={options.length > 0
                            ? `${options.length} ${options.length === 1 ? 'variante' : 'varianti'}`
                            : 'facoltative'}
                          open={openSection === 'varianti'}
                          onToggle={() => setOpenSection(s => s === 'varianti' ? null : 'varianti')}>
                          <p className="mb-2 text-xs text-gray-500">
                            Stesso servizio, più formule: 30, 60 o 90 minuti, ognuna col suo prezzo.
                            Il cliente ne sceglie una quando prenota.
                          </p>
                          <ServiceOptionsEditor
                            options={options}
                            onChange={setOptions}
                            title=""
                            subtitle=""
                            emptyHint="Nessuna variante ancora: vale il prezzo base per tutti."
                          />
                          <p className="mt-2 text-[11px] text-gray-400">
                            Le opzioni si salvano col bottone Salva qui sotto.
                          </p>
                        </RowSection>

                        <RowSection
                          id="incasso"
                          title="Prenotazione e incasso"
                          hint={edit.transactionMode === 'direct' ? 'paga online' : 'su richiesta'}
                          open={openSection === 'incasso'}
                          onToggle={() => setOpenSection(s => s === 'incasso' ? null : 'incasso')}>
                          <div className="space-y-4">
                            <div>
                              <label className="flex items-start gap-2">
                                <input type="checkbox"
                                       checked={edit.useDefaultSchedule}
                                       onChange={e => setEdit(v => ({ ...v, useDefaultSchedule: e.target.checked }))}
                                       className="mt-0.5 rounded border-gray-300"
                                       data-testid="listino-agenda-toggle" />
                                <span>
                                  <span className="block text-sm font-medium text-gray-800">
                                    Prenotabile sul calendario ufficiale
                                  </span>
                                  <span className="block text-xs text-gray-500">
                                    Gli orari si governano dal <Link to="/calendar" className="underline">Calendario</Link>:
                                    un'agenda sola per tutti i servizi.
                                  </span>
                                </span>
                              </label>
                              {!edit.useDefaultSchedule && (
                                <p className="mt-1.5 pl-6 text-xs text-gray-500">
                                  Orari solo per questo servizio? {' '}
                                  <button type="button"
                                          onClick={() => navigate(`/services/${row.id}`)}
                                          className="underline hover:text-primary">
                                    {t('listino.advancedHours', { defaultValue: 'Regole orari nelle impostazioni avanzate' })}
                                  </button>
                                </p>
                              )}
                            </div>

                            <div>
                              <p className="mb-1.5 text-xs font-medium text-gray-600">Come incassi</p>
                              <div className="flex gap-1.5">
                                {[{ k: 'request', l: 'Su richiesta' }, { k: 'direct', l: 'Paga online' }].map(m => (
                                  <button key={m.k} type="button"
                                          onClick={() => setEdit(v => ({ ...v, transactionMode: m.k }))}
                                          className={`rounded-full border px-3 py-1.5 text-xs font-medium ${
                                            edit.transactionMode === m.k
                                              ? 'border-primary bg-primary text-white'
                                              : 'border-gray-300 bg-white text-gray-600'}`}>
                                    {m.l}
                                  </button>
                                ))}
                              </div>
                              <p className="mt-1 text-xs text-gray-500">
                                {edit.transactionMode === 'direct'
                                  ? 'Il cliente sceglie lo slot e paga subito online.'
                                  : 'Ricevi la richiesta via email e confermi tu: nessun pagamento richiesto.'}
                              </p>
                              <StripeRequiredAlert whenTransactionMode={edit.transactionMode} />
                            </div>

                            <div>
                              <p className="mb-1.5 text-xs font-medium text-gray-600">Foto del servizio</p>
                              <label className="flex cursor-pointer items-center gap-2 rounded-md border border-dashed border-gray-300 px-3 py-2 text-sm text-gray-600 hover:border-gray-900">
                                <span>Carica una foto</span>
                                <input type="file" accept="image/*" className="hidden"
                                       onChange={async e => {
                                         const file = e.target.files?.[0];
                                         if (!file) return;
                                         try {
                                           const res = await productsAPI.uploadImage(row.id, file);
                                           const url = res.data?.image_url;
                                           if (url) setEdit(v => ({ ...v, imageUrl: url }));
                                           toast.success('Foto caricata');
                                         } catch { toast.error('Caricamento non riuscito'); }
                                         e.target.value = '';
                                       }} />
                              </label>
                              <input type="url" value={edit.imageUrl}
                                     onChange={e => setEdit(v => ({ ...v, imageUrl: e.target.value }))}
                                     placeholder="oppure incolla l'indirizzo di un'immagine"
                                     data-testid="listino-foto-url"
                                     className="mt-1 w-full rounded-lg border border-input px-3 py-2 text-sm" />
                              {edit.imageUrl && (
                                <img src={edit.imageUrl} alt=""
                                     className="mt-2 h-16 w-full rounded-md border object-cover" />
                              )}
                            </div>
                          </div>
                        </RowSection>

                        {/* AP-L — requisiti e condizioni del servizio in
                            superficie: il testo compare al checkout nella
                            checkbox "Accetto le condizioni di {operatore}"
                            insieme alla politica di cancellazione. */}
                        <RowSection
                          id="condizioni"
                          title="Requisiti e condizioni del servizio"
                          hint={edit.termsContent?.trim() ? 'compilati' : 'facoltativi'}
                          open={openSection === 'condizioni'}
                          onToggle={() => setOpenSection(s => s === 'condizioni' ? null : 'condizioni')}>
                          <p className="mb-2 text-xs text-gray-500">
                            Cosa deve sapere o dichiarare il cliente prima di prenotare.
                            Se compili questo campo, al checkout compare una casella
                            "Accetto le condizioni" con questo testo.
                          </p>
                          <textarea
                            value={edit.termsContent}
                            onChange={e => setEdit(v => ({ ...v, termsContent: e.target.value }))}
                            rows={4} maxLength={20000}
                            placeholder="Es. dichiarazione di assenza di controindicazioni mediche, cosa portare, requisiti di eta'…"
                            data-testid="listino-requisiti"
                            className="w-full rounded-lg border border-input px-3 py-2 text-sm resize-y"
                          />
                        </RowSection>
                      </div>

                      <div className="mt-4 flex flex-wrap items-center gap-2">
                        <Button size="sm" onClick={saveEdit} disabled={busy}>Salva</Button>
                        <Button size="sm" variant="ghost"
                                onClick={() => { setExpandedId(null); setEdit(null); }}>
                          Annulla
                        </Button>
                        <div className="ml-auto flex items-center gap-3 text-xs">
                          {/* PS2: /services/:id = editor AVANZATO onesto
                              (landing, traduzioni, orari, campi ordine) */}
                          <button type="button"
                                  onClick={() => navigate(`/services/${row.id}`)}
                                  className="inline-flex items-center gap-1 text-gray-500 hover:text-primary">
                            <Settings2 className="h-3.5 w-3.5" />
                            {t('listino.advancedSettings', { defaultValue: 'Impostazioni avanzate' })}
                          </button>
                          <button type="button" onClick={() => removeRow(row)}
                                  className="inline-flex items-center gap-1 text-red-400 hover:text-red-600">
                            <Trash2 className="h-3.5 w-3.5" />
                            Rimuovi
                          </button>
                        </div>
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      ))}

      {rows.length > 0 && (
        <p className="text-xs text-gray-400">
          I servizi ricevono richieste di appuntamento via email. Vuoi incassare
          online con slot prenotabili? Attiva il pagamento online dalla riga del
          servizio, sezione "Prenotazione e incasso" (serve <Link to="/settings" className="underline">Stripe</Link>).
        </p>
      )}

      {/* PV7 — UN solo dialog per banner e gate: alla firma l'azione
          in sospeso (saveNew) riparte da sola, mai piu' richiesto. */}
      <DpaPactDialog
        open={pactOpen}
        onOpenChange={setPactOpen}
        onAccepted={() => {
          if (pactPendingRef.current) {
            pactPendingRef.current = false;
            performSaveNew();
          }
        }}
      />
    </div>
      </div>
    </AppLayout>
  );
}
