/**
 * SoundCategorieSezione — MR4 (8/10/2026): Regia → Sound → le CATEGORIE delle
 * meditazioni. Il system admin aggiunge, rinomina, riordina, spegne (mai
 * cancella); ogni cambio e' subito nella scelta di Crea e nei filtri della
 * casa, senza deploy. Slug immutabile, dal titolo.
 */
import { useEffect, useState } from 'react';
import api from '../../api/client';

const TONI = { salvia: '#7FC9B0', viola: '#B5A6DE', acqua: '#7EC1C7', oro: '#C9B37E' };

export default function SoundCategorieSezione() {
  const [voci, setVoci] = useState([]);
  const [senza, setSenza] = useState(0);
  const [nuova, setNuova] = useState({ label: '', tono: 'salvia', descrizione: '' });
  const [esito, setEsito] = useState('');
  const carica = async () => {
    try { const r = await api.get('/admin/sound/categorie'); setVoci(r.data.categorie || []); setSenza(r.data.senza_categoria || 0); }
    catch { setEsito('Non riesco a leggere le categorie.'); }
  };
  useEffect(() => { carica(); }, []);
  const azione = async (fn, ok) => {
    setEsito('');
    try { await fn(); await carica(); if (ok) setEsito(ok); }
    catch (err) { setEsito(err?.response?.data?.detail || 'Operazione non riuscita.'); }
  };
  const crea = (e) => {
    e.preventDefault();
    if (!nuova.label.trim()) return;
    azione(async () => { await api.post('/admin/sound/categorie', nuova); setNuova({ label: '', tono: 'salvia', descrizione: '' }); }, 'Categoria creata: la vedi subito in Crea.');
  };
  const modifica = (slug, campi) => azione(() => api.patch(`/admin/sound/categorie/${slug}`, campi));

  return (
    <section className="mt-8" data-testid="admin-sound-categorie">
      <h2 className="text-base font-semibold text-gray-900">Categorie delle meditazioni</h2>
      <p className="mt-1 text-sm text-gray-600">Si scelgono quando si crea una meditazione e servono per pubblicare. Lo slug non cambia mai; una categoria non si cancella, si spegne.{senza ? ` Meditazioni pubblicate senza categoria: ${senza}.` : ''}</p>
      <form onSubmit={crea} className="mt-4 flex flex-wrap items-end gap-2 rounded-lg border bg-white p-3" data-testid="admin-sound-categorie-nuova">
        <label className="text-xs text-gray-600">Nome<br />
          <input className="mt-1 rounded border px-2 py-1 text-sm" value={nuova.label} maxLength={60} placeholder="es. Respiro guidato"
            onChange={(e) => setNuova({ ...nuova, label: e.target.value })} data-testid="admin-sound-categorie-label" /></label>
        <label className="text-xs text-gray-600">Tono<br />
          <select className="mt-1 rounded border px-2 py-1 text-sm" value={nuova.tono} onChange={(e) => setNuova({ ...nuova, tono: e.target.value })}>
            {Object.keys(TONI).map((t) => <option key={t} value={t}>{t}</option>)}
          </select></label>
        <label className="text-xs text-gray-600 flex-1 min-w-[200px]">Descrizione (facoltativa)<br />
          <input className="mt-1 w-full rounded border px-2 py-1 text-sm" value={nuova.descrizione} maxLength={300}
            onChange={(e) => setNuova({ ...nuova, descrizione: e.target.value })} /></label>
        <button type="submit" className="rounded-full bg-[#2f5749] px-4 py-2 text-sm font-semibold text-white" data-testid="admin-sound-categorie-crea">Aggiungi</button>
      </form>
      {esito && <p className="mt-2 text-sm text-gray-700" data-testid="admin-sound-categorie-esito">{esito}</p>}
      <div className="mt-3 rounded-lg border divide-y bg-white">
        {voci.map((c) => (
          <div key={c.slug} className="flex flex-wrap items-center gap-3 px-3 py-2 text-sm" data-testid={`admin-sound-categoria-${c.slug}`}>
            <span className="inline-block h-3 w-3 rounded-full" style={{ background: TONI[c.tono] || TONI.oro }} title={c.tono} />
            <input className="rounded border px-2 py-1 text-sm" defaultValue={c.label} maxLength={60}
              onBlur={(e) => { const v = e.target.value.trim(); if (v && v !== c.label) modifica(c.slug, { label: v }); }} />
            <code className="text-xs text-gray-500">{c.slug}</code>
            <select className="rounded border px-2 py-1 text-xs" value={c.tono} onChange={(e) => modifica(c.slug, { tono: e.target.value })}>
              {Object.keys(TONI).map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
            <input type="number" className="w-16 rounded border px-2 py-1 text-xs" defaultValue={c.ordine}
              onBlur={(e) => { const n = Number(e.target.value); if (n !== c.ordine) modifica(c.slug, { ordine: n }); }} title="Ordine" />
            <span className="text-xs text-gray-500">{c.meditazioni} meditazion{c.meditazioni === 1 ? 'e' : 'i'}</span>
            <button type="button" className={`ml-auto rounded-full border px-3 py-1 text-xs ${c.attiva ? 'border-gray-300 text-gray-700' : 'border-amber-400 text-amber-700'}`}
              onClick={() => modifica(c.slug, { attiva: !c.attiva })}>{c.attiva ? 'Spegni' : 'Riaccendi'}</button>
          </div>
        ))}
      </div>
    </section>
  );
}
