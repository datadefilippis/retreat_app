/**
 * La pagina «Strutture» del system admin (SR, fase 0): /admin/strutture.
 *
 * Pagina PROPRIA nel menu System, sotto Aurya Sound (voluta cosi' dal
 * founder: non un tab dell'Admin Panel). La lista con i filtri sempre
 * visibili e nell'URL (una ricerca si condivide con un link), i
 * conteggi vivi per regione, tipo e stato, la creazione in due campi
 * (nome e regione) e la vista con le richieste degli operatori
 * (?vista=richieste). La scheda vive in una pagina intera:
 * /admin/strutture/{id} (e' lunga, non sta in un modale).
 */
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { toast } from 'sonner';
import { AppLayout, Header } from '../../../components/Layout';
import { Button } from '../../../components/ui/button';
import { caricaSchema, crea, etichetta, lista, richieste, salvaRichiesta } from './api';
import { cls } from './campi';

const FILTRI_LISTA = ['regione', 'tipo', 'stato_pipeline', 'adatta_a', 'cucina'];
const FILTRI_BOOL = ['sala', 'piscina', 'aria', 'spazi_esterni', 'uso_esclusivo'];

function filtriDaUrl(sp) {
  const f = {};
  FILTRI_LISTA.forEach((k) => { const v = sp.getAll(k); if (v.length) f[k] = v; });
  FILTRI_BOOL.forEach((k) => { if (sp.get(k) === '1') f[k] = true; });
  ['q', 'visibilita', 'ordine'].forEach((k) => { if (sp.get(k)) f[k] = sp.get(k); });
  ['posti_letto_min', 'sala_mq_min', 'prezzo_max', 'pagina'].forEach((k) => { if (sp.get(k)) f[k] = Number(sp.get(k)); });
  return f;
}

function StatoBadge({ stato, schema }) {
  const colori = { da_contattare: 'bg-gray-100 text-gray-700', contattata: 'bg-sky-100 text-sky-800',
                   visitata: 'bg-amber-100 text-amber-800', in_lista: 'bg-emerald-100 text-emerald-800',
                   sospesa: 'bg-red-100 text-red-800' };
  return <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${colori[stato] || 'bg-gray-100'}`}>{etichetta(schema, 'stati_pipeline', stato)}</span>;
}

function Lista({ schema }) {
  const [sp, setSp] = useSearchParams();
  const navigate = useNavigate();
  const filtri = useMemo(() => filtriDaUrl(sp), [sp]);
  const [dati, setDati] = useState(null);
  const [nuova, setNuova] = useState({ nome: '', regione: '', tipo: '' });
  const [busy, setBusy] = useState(false);

  const setFiltro = (k, v) => {
    const next = new URLSearchParams(sp);
    next.delete(k); next.delete('pagina');
    if (Array.isArray(v)) v.forEach((x) => next.append(k, x));
    else if (v === true) next.set(k, '1');
    else if (v !== null && v !== undefined && v !== '' && v !== false) next.set(k, String(v));
    setSp(next, { replace: true });
  };
  const toggleLista = (k, valore) => {
    const attuali = filtri[k] || [];
    setFiltro(k, attuali.includes(valore) ? attuali.filter((x) => x !== valore) : [...attuali, valore]);
  };

  const carica = useCallback(async () => {
    try { setDati(await lista(filtri)); }
    catch { toast.error('Lista non caricata'); }
  }, [filtri]);
  useEffect(() => { carica(); }, [carica]);

  const creaStruttura = async (e) => {
    e.preventDefault();
    if (!nuova.nome.trim() || !nuova.regione) { toast.error('Servono nome e regione'); return; }
    setBusy(true);
    try {
      const doc = await crea({ nome: nuova.nome.trim(), regione: nuova.regione, tipo: nuova.tipo || null });
      toast.success('Struttura creata: ora la scheda');
      navigate(`/admin/strutture/${doc.id}`);
    } catch (err) {
      toast.error(String(err?.response?.data?.detail || 'Errore'));
    } finally { setBusy(false); }
  };

  const facet = (k) => (dati?.facet?.[k] || []);
  const righe = dati?.righe || [];
  const nFiltri = Object.keys(filtri).filter((k) => !['ordine', 'pagina'].includes(k)).length;

  return (
    <div className="space-y-4" data-testid="strutture-lista">
      {/* nuova struttura: due campi, poi la scheda */}
      <form onSubmit={creaStruttura} className="rounded-2xl border border-border bg-card p-4 flex flex-col sm:flex-row gap-2 sm:items-end">
        <label className="flex-1"><span className={cls.label}>Nuova struttura · nome</span>
          <input value={nuova.nome} onChange={(e) => setNuova({ ...nuova, nome: e.target.value })} placeholder="es. Masseria Montanari" className={cls.input} data-testid="strutture-nuova-nome" /></label>
        <label className="sm:w-52"><span className={cls.label}>Regione</span>
          <select value={nuova.regione} onChange={(e) => setNuova({ ...nuova, regione: e.target.value })} className={cls.input} data-testid="strutture-nuova-regione">
            <option value="">—</option>{(schema?.regioni || []).map((r) => <option key={r} value={r}>{r}</option>)}
          </select></label>
        <label className="sm:w-48"><span className={cls.label}>Tipo</span>
          <select value={nuova.tipo} onChange={(e) => setNuova({ ...nuova, tipo: e.target.value })} className={cls.input}>
            <option value="">—</option>{(schema?.liste?.tipi_struttura || []).map((o) => <option key={o.valore} value={o.valore}>{o.etichetta}</option>)}
          </select></label>
        <Button type="submit" disabled={busy} data-testid="strutture-nuova-crea">Crea e apri la scheda</Button>
      </form>

      {/* filtri: sempre visibili, nell'URL */}
      <div className="rounded-2xl border border-border bg-card p-4 space-y-3" data-testid="strutture-filtri">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
          <label className="md:col-span-2"><span className={cls.label}>Cerca</span>
            <input value={filtri.q || ''} onChange={(e) => setFiltro('q', e.target.value)} placeholder="nome, comune, descrizione" className={cls.input} /></label>
          <label><span className={cls.label}>Posti letto minimo</span>
            <input type="number" min="1" value={filtri.posti_letto_min || ''} onChange={(e) => setFiltro('posti_letto_min', e.target.value)} className={cls.input} /></label>
          <label><span className={cls.label}>Prezzo massimo a persona a notte (€)</span>
            <input type="number" min="0" value={filtri.prezzo_max || ''} onChange={(e) => setFiltro('prezzo_max', e.target.value)} className={cls.input} /></label>
        </div>
        <div className="flex flex-wrap gap-1.5">
          {[['sala', 'Ha una sala'], ['piscina', 'Piscina'], ['aria', 'Aria condizionata'], ['spazi_esterni', 'Spazi esterni'], ['uso_esclusivo', 'Uso esclusivo']].map(([k, t]) => (
            <button key={k} type="button" onClick={() => setFiltro(k, !filtri[k])}
                    className={`min-h-[36px] rounded-full border px-3 text-xs ${filtri[k] ? 'bg-primary text-white border-primary' : 'border-input bg-background'}`}>{t}</button>
          ))}
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
          {[['regione', 'Regione', facet('regione').map((f) => ({ valore: f.valore, etichetta: `${f.valore} (${f.n})` }))],
            ['tipo', 'Tipo', facet('tipo').map((f) => ({ valore: f.valore, etichetta: `${etichetta(schema, 'tipi_struttura', f.valore)} (${f.n})` }))],
            ['stato_pipeline', 'Stato', facet('stato_pipeline').map((f) => ({ valore: f.valore, etichetta: `${etichetta(schema, 'stati_pipeline', f.valore)} (${f.n})` }))]]
            .map(([k, titolo, voci]) => (
              <div key={k}>
                <p className={cls.label}>{titolo}</p>
                <div className="flex flex-wrap gap-1">
                  {voci.length === 0 && <span className="text-muted-foreground">—</span>}
                  {voci.map((o) => (
                    <button key={o.valore} type="button" onClick={() => toggleLista(k, o.valore)}
                            className={`min-h-[32px] rounded-full border px-2.5 ${(filtri[k] || []).includes(o.valore) ? 'bg-primary text-white border-primary' : 'border-input bg-background'}`}>{o.etichetta}</button>
                  ))}
                </div>
              </div>
            ))}
        </div>
        <div>
          <p className={cls.label}>Adatta a</p>
          <div className="flex flex-wrap gap-1">
            {(schema?.liste?.adatta_a || []).map((o) => (
              <button key={o.valore} type="button" onClick={() => toggleLista('adatta_a', o.valore)}
                      className={`min-h-[32px] rounded-full border px-2.5 text-xs ${(filtri.adatta_a || []).includes(o.valore) ? 'bg-primary text-white border-primary' : 'border-input bg-background'}`}>{o.etichetta}</button>
            ))}
          </div>
        </div>
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span>{dati ? `${dati.totale} strutture` : 'Carico…'}{nFiltri > 0 && ` · ${nFiltri} filtri`}</span>
          <div className="flex items-center gap-2">
            <span>Ordina</span>
            <select value={filtri.ordine || 'aggiornato'} onChange={(e) => setFiltro('ordine', e.target.value)} className="rounded-md border border-input bg-background px-2 py-1">
              <option value="aggiornato">Ultima modifica</option><option value="nome">Nome</option>
              <option value="prezzo">Prezzo da</option><option value="posti">Posti letto</option>
            </select>
            {nFiltri > 0 && <button type="button" onClick={() => setSp(new URLSearchParams(), { replace: true })} className="underline">Azzera</button>}
          </div>
        </div>
      </div>

      {/* la tabella */}
      <div className="overflow-x-auto rounded-2xl border border-border bg-card">
        <table className="w-full text-sm">
          <thead className="text-left text-xs text-muted-foreground">
            <tr><th className="p-3">Struttura</th><th className="p-3">Dove</th><th className="p-3 text-right">Posti letto</th><th className="p-3 text-right">Sala</th><th className="p-3 text-right">Da €/notte</th><th className="p-3">Stato</th><th className="p-3">Aggiornata</th></tr>
          </thead>
          <tbody>
            {righe.length === 0 && (
              <tr><td colSpan={7} className="p-6 text-center text-muted-foreground">Nessuna struttura con questi filtri.</td></tr>
            )}
            {righe.map((r) => (
              <tr key={r.id} className="border-t border-border hover:bg-muted/40 cursor-pointer" onClick={() => navigate(`/admin/strutture/${r.id}`)} data-testid="strutture-riga">
                <td className="p-3"><b>{r.identita?.nome}</b><div className="text-xs text-muted-foreground">{etichetta(schema, 'tipi_struttura', r.identita?.tipo)}{r.visibilita === 'pubblica' && ' · pubblica'}</div></td>
                <td className="p-3">{[r.luogo?.comune, r.luogo?.regione].filter(Boolean).join(', ')}</td>
                <td className="p-3 text-right tabular-nums">{r.derivati?.posti_letto_totali ?? '—'}</td>
                <td className="p-3 text-right tabular-nums">{r.derivati?.ha_sala ? `${r.derivati.sala_mq_max ? `${r.derivati.sala_mq_max} m²` : 'sì'}` : '—'}</td>
                <td className="p-3 text-right tabular-nums">{r.derivati?.prezzo_da != null ? r.derivati.prezzo_da : '—'}</td>
                <td className="p-3"><StatoBadge stato={r.derivati?.stato_pipeline} schema={schema} /></td>
                <td className="p-3 text-xs text-muted-foreground">{(r.aggiornato_il || '').slice(0, 10)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {dati && dati.totale > dati.per_pagina && (
          <div className="flex items-center justify-between p-3 text-xs">
            <button type="button" disabled={(filtri.pagina || 1) <= 1} onClick={() => setFiltro('pagina', (filtri.pagina || 1) - 1)} className="rounded-full border px-3 py-1 disabled:opacity-40">← Precedenti</button>
            <span>pagina {filtri.pagina || 1} di {Math.ceil(dati.totale / dati.per_pagina)}</span>
            <button type="button" disabled={(filtri.pagina || 1) >= Math.ceil(dati.totale / dati.per_pagina)} onClick={() => setFiltro('pagina', (filtri.pagina || 1) + 1)} className="rounded-full border px-3 py-1 disabled:opacity-40">Successive →</button>
          </div>
        )}
      </div>
    </div>
  );
}

function Richieste({ schema }) {
  const [righe, setRighe] = useState(null);
  const carica = useCallback(async () => {
    try { setRighe((await richieste()).righe || []); } catch { toast.error('Richieste non caricate'); setRighe([]); }
  }, []);
  useEffect(() => { carica(); }, [carica]);
  const cambia = async (id, patch) => {
    try { await salvaRichiesta(id, patch); toast.success('Richiesta aggiornata'); carica(); }
    catch { toast.error('Errore, riprova'); }
  };
  const STATI = [['nuova', 'Nuova'], ['in_lavorazione', 'In lavorazione'], ['proposta', 'Proposta'], ['chiusa', 'Chiusa']];
  return (
    <div className="space-y-3" data-testid="strutture-richieste">
      {righe === null && <p className="text-sm text-muted-foreground">Carico…</p>}
      {righe && righe.length === 0 && <div className="rounded-2xl border border-dashed border-border p-8 text-center text-sm text-muted-foreground">Nessuna richiesta dagli operatori, per ora.</div>}
      {(righe || []).map((r) => (
        <article key={r.id} className="rounded-2xl border border-border bg-card p-4" data-testid="strutture-richiesta">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <b>{r.organization_nome || 'Professionista'}</b>
            <span className="text-xs text-muted-foreground">{(r.creato_il || '').slice(0, 10)} · {r.email}</span>
          </div>
          {/* P13 — il tipo (struttura, regia, team building) e i contatti dell'azienda */}
          <p className="mt-1 text-xs font-semibold uppercase tracking-wide text-[#2f5749]" data-testid="strutture-richiesta-tipo">
            {({ regia: 'Regia', team_building: 'Team building' })[r.tipo] || 'Struttura'}{r.formula ? ` · ${r.formula}` : ''}
          </p>
          {r.tipo === 'team_building' && <p className="mt-1 text-sm">{r.nome}{r.telefono ? ` · ${r.telefono}` : ''}</p>}
          <p className="mt-1 text-sm">{r.zona} · {r.periodo} · {r.persone} persone{r.notti ? ` · ${r.notti} notti` : ''}{r.budget_persona ? ` · ${r.budget_persona} € a persona` : ''}{r.tipo_ritiro ? ` · ${r.tipo_ritiro}` : ''}</p>
          {r.messaggio && <p className="mt-1 text-sm text-muted-foreground">{r.messaggio}</p>}
          {r.esigenze && <p className="mt-1 text-sm text-muted-foreground">{r.esigenze}</p>}
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <select value={r.stato} onChange={(e) => cambia(r.id, { stato: e.target.value })} className="rounded-md border border-input bg-background px-2 py-1.5 text-sm">
              {STATI.map(([v, t]) => <option key={v} value={v}>{t}</option>)}
            </select>
            <input defaultValue={r.nota_interna || ''} placeholder="nota interna (solo voi)"
                   onBlur={(e) => e.target.value !== (r.nota_interna || '') && cambia(r.id, { nota_interna: e.target.value })}
                   className="flex-1 min-w-[200px] rounded-md border border-input bg-background px-3 py-1.5 text-sm" />
          </div>
        </article>
      ))}
    </div>
  );
}

export default function StrutturePage() {
  const [schema, setSchema] = useState(null);
  const [sp, setSp] = useSearchParams();
  const vista = sp.get('vista') === 'richieste' ? 'richieste' : 'lista';
  useEffect(() => { caricaSchema().then(setSchema).catch(() => toast.error('Schema non caricato')); }, []);
  const cambiaVista = (v) => { const next = new URLSearchParams(); if (v === 'richieste') next.set('vista', 'richieste'); setSp(next, { replace: true }); };
  return (
    <AppLayout>
      <Header title="Strutture" subtitle="Le strutture ricettive per i ritiri: schede, filtri e richieste degli operatori" />
      <div className="p-4 md:p-8 space-y-4" data-testid="strutture-pagina">
      <div className="flex gap-2">
        {[['lista', 'Strutture'], ['richieste', 'Richieste degli operatori']].map(([v, t]) => (
          <button key={v} type="button" onClick={() => cambiaVista(v)}
                  className={`rounded-full px-4 py-1.5 text-sm font-medium ${vista === v ? 'bg-primary text-white' : 'border border-border'}`} data-testid={`strutture-vista-${v}`}>{t}</button>
        ))}
      </div>
      {vista === 'lista' ? <Lista schema={schema} /> : <Richieste schema={schema} />}
      </div>
    </AppLayout>
  );
}
