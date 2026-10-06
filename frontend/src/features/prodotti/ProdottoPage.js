/**
 * /prodotti/:id — UN PRODOTTO (P1, 6/10/2026): modifica, file, stato, vendite.
 */
import React, { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { Loader2, UploadCloud } from 'lucide-react';
import { toast } from 'sonner';
import { AppLayout, Header } from '../../components/Layout';
import { prodottiAPI, fmtBytes } from '../../api/prodotti';

export default function ProdottoPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [p, setP] = useState(null);
  const [form, setForm] = useState(null);
  const [vendite, setVendite] = useState(null);
  const [salvando, setSalvando] = useState(false);
  const [file, setFile] = useState(null);
  const [avanzamento, setAvanzamento] = useState(null);
  const [ragioni, setRagioni] = useState([]);

  const load = useCallback(() => {
    prodottiAPI.get(id).then(res => {
      setP(res.data);
      setForm({
        name: res.data.name || '', description: res.data.description || '',
        unit_price: res.data.unit_price != null ? String(res.data.unit_price) : '',
        max_downloads: res.data.max_downloads_per_delivery || '',
        expiry_days: res.data.access_expiry_days || '',
        stock_quantity: res.data.stock_quantity != null ? String(res.data.stock_quantity) : '',
      });
    }).catch(() => toast.error('Prodotto non trovato.'));
    prodottiAPI.vendite(id).then(res => setVendite(res.data)).catch(() => {});
  }, [id]);
  useEffect(() => { load(); }, [load]);

  const salva = async () => {
    if (!form || salvando) return;
    setSalvando(true);
    try {
      const upd = {
        name: form.name.trim(), description: form.description.trim() || '',
        unit_price: form.unit_price !== '' ? Number(form.unit_price) : undefined,
      };
      if (p.item_type === 'digital') {
        upd.max_downloads_per_delivery = form.max_downloads ? Number(form.max_downloads) : 0;
        upd.access_expiry_days = form.expiry_days ? Number(form.expiry_days) : 0;
      } else if (form.stock_quantity !== '') {
        upd.stock_quantity = Number(form.stock_quantity);
      }
      const res = await prodottiAPI.update(id, upd);
      setP(res.data); toast.success('Salvato.');
    } catch (err) {
      const d = err?.response?.data?.detail;
      toast.error((typeof d === 'string' && d) || 'Non sono riuscito a salvare.');
    } finally { setSalvando(false); }
  };

  const caricaFile = async () => {
    if (!file || salvando) return;
    setSalvando(true); setAvanzamento(0);
    try {
      await prodottiAPI.uploadFile(id, file, {
        onUploadProgress: (e) => { if (e.total) setAvanzamento(Math.round((e.loaded / e.total) * 100)); },
      });
      toast.success('File aggiornato: chi compra da ora riceve questo.'); setFile(null); load();
    } catch (err) {
      const d = err?.response?.data?.detail;
      toast.error((typeof d === 'string' && d) || 'Il file non è stato caricato.');
    } finally { setSalvando(false); setAvanzamento(null); }
  };

  const caricaCover = async (f) => {
    if (!f) return;
    try { await prodottiAPI.uploadImage(id, f); toast.success('Copertina aggiornata.'); load(); }
    catch { toast.error('La copertina non è stata caricata.'); }
  };

  const pubblica = async () => {
    setSalvando(true); setRagioni([]);
    try { const res = await prodottiAPI.pubblica(id); setP(res.data); toast.success('Online sul tuo profilo.'); }
    catch (err) {
      const d = err?.response?.data?.detail;
      if (d?.code === 'non_pubblicabile') setRagioni(d.ragioni || []);
      else toast.error('Non sono riuscito a pubblicare.');
    } finally { setSalvando(false); }
  };
  const ritira = async () => {
    setSalvando(true);
    try { const res = await prodottiAPI.ritira(id); setP(res.data); toast.success('Tolto dal profilo: resta in bozza.'); }
    catch { toast.error('Non sono riuscito a ritirarlo.'); }
    finally { setSalvando(false); }
  };

  const campo = 'w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none';
  if (!p || !form) return <AppLayout><Loader2 className="h-5 w-5 animate-spin text-gray-400" /></AppLayout>;

  return (
    <AppLayout>
        <Header title={p.name} subtitle={`${p.tipo_etichetta} · ${p.is_published ? 'Online sul profilo' : 'Bozza'}`}>
          {p.is_published
            ? <button type="button" onClick={ritira} disabled={salvando} className="rounded-full border px-4 py-2 text-sm text-gray-700" data-testid="prodotto-ritira">Togli dal profilo</button>
            : <button type="button" onClick={pubblica} disabled={salvando} className="rounded-full px-4 py-2 text-sm font-medium text-white" style={{ background: '#2f5749' }} data-testid="prodotto-pubblica">Pubblica</button>}
        </Header>
      <div className="p-4 md:p-8 animate-fade-in max-w-3xl space-y-5" data-testid="prodotto-page">
        <Link to="/prodotti" className="text-xs text-gray-500 hover:underline">← I tuoi prodotti</Link>

        {ragioni.length > 0 && (
          <div className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900" data-testid="prodotto-ragioni">
            <p className="font-medium">Prima di pubblicare:</p>
            <ul className="mt-1 list-disc pl-5 space-y-0.5">{ragioni.map(r => <li key={r}>{r}</li>)}</ul>
          </div>
        )}

        <section className="rounded-2xl border bg-white p-5 space-y-4">
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">Titolo</label>
            <input className={campo} value={form.name} maxLength={255} onChange={e => setForm({ ...form, name: e.target.value })} />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">Due righe per chi compra</label>
            <textarea className={`${campo} resize-none`} rows={2} maxLength={2000} value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} />
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Prezzo (€)</label>
              <input className={campo} type="number" min="0" step="0.5" value={form.unit_price} onChange={e => setForm({ ...form, unit_price: e.target.value })} />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Copertina</label>
              <input type="file" accept="image/*" className="text-xs" onChange={e => caricaCover(e.target.files?.[0])} />
            </div>
            {p.item_type === 'digital' ? (
              <>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Scaricamenti massimi per acquisto</label>
                  <input className={campo} type="number" min="0" max="1000" value={form.max_downloads} placeholder="Illimitati" onChange={e => setForm({ ...form, max_downloads: e.target.value })} />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Il link scade dopo (giorni)</label>
                  <input className={campo} type="number" min="0" max="3650" value={form.expiry_days} placeholder="Mai" onChange={e => setForm({ ...form, expiry_days: e.target.value })} />
                </div>
              </>
            ) : (
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Quantità disponibile</label>
                <input className={campo} type="number" min="0" value={form.stock_quantity} placeholder="Illimitata" onChange={e => setForm({ ...form, stock_quantity: e.target.value })} />
              </div>
            )}
          </div>
          <div className="flex justify-end">
            <button type="button" onClick={salva} disabled={salvando} className="rounded-full px-5 py-2 text-sm font-medium text-white disabled:opacity-50" style={{ background: '#2f5749' }} data-testid="prodotto-salva">Salva</button>
          </div>
        </section>

        {p.item_type === 'digital' && (
          <section className="rounded-2xl border bg-white p-5 space-y-3" data-testid="prodotto-file">
            <p className="text-sm font-semibold text-gray-900">Il file</p>
            <p className="text-xs text-gray-500">{p.file ? `${p.file.filename} · ${fmtBytes(p.file.size_bytes)}` : 'Nessun file ancora: senza, non si può pubblicare.'}</p>
            <label className="flex cursor-pointer items-center gap-2 rounded-xl border border-dashed border-gray-300 px-4 py-3 text-sm text-gray-600 hover:border-gray-900">
              <UploadCloud className="h-5 w-5 text-gray-400" aria-hidden />
              <span>{file ? `${file.name} (${fmtBytes(file.size)})` : (p.file ? 'Sostituisci il file' : 'Scegli il file')}</span>
              <input type="file" className="hidden" onChange={e => setFile(e.target.files?.[0] || null)} />
            </label>
            {avanzamento != null && <div className="h-2 w-full overflow-hidden rounded-full bg-gray-100"><div className="h-full bg-[#2f5749]" style={{ width: `${avanzamento}%` }} /></div>}
            {file && <button type="button" onClick={caricaFile} disabled={salvando} className="rounded-full border px-4 py-1.5 text-sm text-gray-700">Carica</button>}
          </section>
        )}

        <section className="rounded-2xl border bg-white p-5" data-testid="prodotto-vendite">
          <p className="text-sm font-semibold text-gray-900">Vendite</p>
          <p className="mt-1 text-sm text-gray-600">{p.venduti_30gg} negli ultimi 30 giorni{vendite?.total_quantity != null ? ` · ${vendite.total_quantity} in tutto` : ''}{vendite?.total_revenue != null ? ` · ${Number(vendite.total_revenue).toFixed(2)} € incassati` : ''}</p>
          <p className="mt-1 text-xs text-gray-400">Gli ordini completi sono in Ordini, gli incassi in Incassi.</p>
        </section>

        <button type="button" onClick={() => navigate('/prodotti')} className="text-sm text-gray-500 underline">Torna ai prodotti</button>
      </div>
    </AppLayout>
  );
}
