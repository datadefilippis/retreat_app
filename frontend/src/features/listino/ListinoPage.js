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
 * che esiste. "Tutte le impostazioni" apre il vecchio editor service
 * (/services/:id) che da TW1 e' l'editor AVANZATO, non il percorso.
 */
import React, { useEffect, useMemo, useState } from 'react';
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
import api from '../../api/client';
import { trackEvent } from '../../lib/analytics';
import { AppLayout, Header } from '../../components/Layout';

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

export default function ListinoPage() {
  const { t } = useTranslation('catalog');
  const navigate = useNavigate();
  const [rows, setRows] = useState(null);       // null = loading
  const [profileSlug, setProfileSlug] = useState(null);
  const [adding, setAdding] = useState(false);
  const [draft, setDraft] = useState(EMPTY_ROW);
  const [expandedId, setExpandedId] = useState(null);
  const [edit, setEdit] = useState(null);
  const [busy, setBusy] = useState(false);

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
    setBusy(true);
    // TW4 — metrica di attivazione: il PRIMO servizio che va online
    const isFirstOnline = !(rows || []).some(r => r.published);
    try {
      await storesAPI.ensureDefault();     // idempotente, race-safe
      await productsAPI.create({
        ...payloadFromRow(draft),
        item_type: 'service',
        transaction_mode: 'request',       // default snello: richiesta
        is_published: true,                // online subito
      });
      if (isFirstOnline) trackEvent('first_service_online');
      setDraft(EMPTY_ROW);
      setAdding(false);
      await load();
      toast.success('Servizio nel listino, gia’ online');
    } catch (e) {
      toast.error(e?.response?.data?.detail?.message
        || e?.response?.data?.detail || 'Salvataggio non riuscito');
    } finally { setBusy(false); }
  };

  const saveEdit = async () => {
    if (!edit?.name.trim()) { toast.error('Il nome non puo’ restare vuoto'); return; }
    setBusy(true);
    try {
      await productsAPI.update(edit.id, payloadFromRow(edit));
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
                      <div className="mt-4 flex flex-wrap items-center gap-2">
                        <Button size="sm" onClick={saveEdit} disabled={busy}>Salva</Button>
                        <Button size="sm" variant="ghost"
                                onClick={() => { setExpandedId(null); setEdit(null); }}>
                          Annulla
                        </Button>
                        <div className="ml-auto flex items-center gap-3 text-xs">
                          {/* il vecchio wizard = editor AVANZATO (calendario
                              dedicato, opzioni, pagamento online, campi custom) */}
                          <button type="button"
                                  onClick={() => navigate(`/services/${row.id}`)}
                                  className="inline-flex items-center gap-1 text-gray-500 hover:text-primary">
                            <Settings2 className="h-3.5 w-3.5" />
                            Tutte le impostazioni
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
          online con slot prenotabili? Apri "Tutte le impostazioni" del servizio
          e attiva il pagamento online (serve <Link to="/settings" className="underline">Stripe</Link>).
        </p>
      )}
    </div>
      </div>
    </AppLayout>
  );
}
