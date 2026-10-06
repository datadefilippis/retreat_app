/**
 * /prodotti/nuovo/fisico — PRODOTTO FISICO IN TRE GESTI (P2, 6/10/2026).
 *
 *   1. Cos'è        titolo, due righe, prezzo, foto, quantità (o illimitata)
 *   2. Come arriva  ritiro di persona e/o spedizione a costo fisso (vale per
 *                   tutti i tuoi fisici: una scelta sola, si cambia quando vuoi)
 *   3. Pubblica     anteprima della scheda + «Pubblica» (o «Salva in bozza»)
 *
 * Il prodotto nasce in bozza al passo 1; la consegna scrive i modi dello
 * store e l'opzione «Spedizione» (riusa spedizione, magazzino e stati di
 * evasione gia' nel gestionale). La pubblicazione passa dai lucchetti del
 * backend (409 con le ragioni). Il patto DPA, se manca, apre il dialog.
 */
import React, { useEffect, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Loader2, CheckCircle2 } from 'lucide-react';
import { toast } from 'sonner';
import { AppLayout, Header } from '../../components/Layout';
import DpaPactDialog from '../../components/legal/DpaPactDialog';
import { prodottiAPI, fmtEuro } from '../../api/prodotti';

const PASSI = [
  { key: 'cosa', label: "Cos'è" },
  { key: 'arriva', label: 'Come arriva' },
  { key: 'pubblica', label: 'Pubblica' },
];

export default function ProdottoFisicoWizard() {
  const navigate = useNavigate();
  const [passo, setPasso] = useState(0);
  const [form, setForm] = useState({ name: '', description: '', unit_price: '', quantita: '', illimitata: true });
  const [prodotto, setProdotto] = useState(null);
  const [coverFile, setCoverFile] = useState(null);
  const [consegna, setConsegna] = useState({ ritiro: false, spedizione: true, costo_spedizione: '', soglia_gratis: '' });
  const [consegnaSalvata, setConsegnaSalvata] = useState(false);
  const [salvando, setSalvando] = useState(false);
  const [pactOpen, setPactOpen] = useState(false);
  const [ragioni, setRagioni] = useState([]);
  const pendingRef = useRef(false);

  useEffect(() => {
    prodottiAPI.consegna().then(res => {
      const c = res.data || {};
      setConsegna({
        ritiro: !!c.ritiro, spedizione: c.spedizione !== false,
        costo_spedizione: c.costo_spedizione != null ? String(c.costo_spedizione) : '',
        soglia_gratis: c.soglia_gratis != null ? String(c.soglia_gratis) : '',
      });
      setConsegnaSalvata(!!c.configurata);
    }).catch(() => {});
  }, []);

  const prezzoOk = form.unit_price !== '' && Number(form.unit_price) > 0;
  const quantitaOk = form.illimitata || (form.quantita !== '' && Number(form.quantita) >= 0);
  const passo1Ok = form.name.trim().length > 0 && prezzoOk && quantitaOk;
  const consegnaOk = (consegna.ritiro || consegna.spedizione)
    && (!consegna.spedizione || (consegna.costo_spedizione !== '' && Number(consegna.costo_spedizione) >= 0));

  const salvaBozza = async () => {
    if (!passo1Ok || salvando) return;
    setSalvando(true);
    try {
      const payload = {
        item_type: 'physical', name: form.name.trim(), description: form.description.trim() || null,
        unit_price: Number(form.unit_price),
        stock_quantity: form.illimitata ? null : Number(form.quantita),
      };
      let p;
      if (prodotto?.id) {
        const upd = { ...payload }; delete upd.item_type; delete upd.stock_quantity;
        if (!form.illimitata) upd.stock_quantity = Number(form.quantita);
        p = (await prodottiAPI.update(prodotto.id, upd)).data;
      } else {
        p = (await prodottiAPI.create(payload)).data;
      }
      if (coverFile) {
        try { const res = await prodottiAPI.uploadImage(p.id, coverFile); p = { ...p, image_url: res.data?.image_url || p.image_url }; }
        catch { toast.error('La foto non è stata caricata: puoi riprovare dopo.'); }
      }
      setProdotto(p); setPasso(1);
    } catch (err) {
      const d = err?.response?.data?.detail;
      if (d?.code === 'DPA_REQUIRED') { pendingRef.current = true; setPactOpen(true); return; }
      toast.error((typeof d === 'string' && d) || d?.message || 'Non sono riuscito a salvare. Riprova.');
    } finally { setSalvando(false); }
  };

  const salvaConsegna = async () => {
    if (!consegnaOk || salvando) return;
    setSalvando(true);
    try {
      await prodottiAPI.salvaConsegna({
        ritiro: consegna.ritiro, spedizione: consegna.spedizione,
        costo_spedizione: consegna.spedizione ? Number(consegna.costo_spedizione || 0) : null,
        soglia_gratis: consegna.spedizione && consegna.soglia_gratis !== '' ? Number(consegna.soglia_gratis) : null,
      });
      setConsegnaSalvata(true); setPasso(2);
    } catch (err) {
      const d = err?.response?.data?.detail;
      toast.error((typeof d === 'string' && d) || 'Non sono riuscito a salvare la consegna.');
    } finally { setSalvando(false); }
  };

  const pubblica = async () => {
    if (!prodotto?.id || salvando) return;
    setSalvando(true); setRagioni([]);
    try { await prodottiAPI.pubblica(prodotto.id); toast.success('Il prodotto è online sul tuo profilo.'); navigate('/prodotti'); }
    catch (err) {
      const d = err?.response?.data?.detail;
      if (d?.code === 'non_pubblicabile') setRagioni(d.ragioni || []);
      else toast.error((typeof d === 'string' && d) || 'Non sono riuscito a pubblicare. Riprova.');
    } finally { setSalvando(false); }
  };

  const campo = 'w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none';
  const bottone = 'rounded-full px-5 py-2 text-sm font-medium text-white disabled:opacity-50';

  return (
    <AppLayout>
      <div className="max-w-2xl space-y-5" data-testid="wizard-fisico">
        <Link to="/prodotti" className="text-xs text-gray-500 hover:underline">← I tuoi prodotti</Link>
        <Header title="Nuovo prodotto fisico" subtitle="Tre gesti: cos'è, come arriva, pubblica." />
        <ol className="flex gap-2 text-xs" aria-label="Passi">
          {PASSI.map((p, i) => (
            <li key={p.key} data-testid={`passo-${p.key}`}
              className={`rounded-full px-3 py-1 ${i === passo ? 'bg-[#2f5749] text-white' : i < passo ? 'bg-emerald-100 text-emerald-800' : 'bg-gray-100 text-gray-500'}`}>
              {i + 1}. {p.label}
            </li>
          ))}
        </ol>

        {passo === 0 && (
          <section className="rounded-2xl border bg-white p-5 space-y-4">
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Titolo *</label>
              <input className={campo} value={form.name} maxLength={255} data-testid="pf-nome"
                     onChange={e => setForm({ ...form, name: e.target.value })} placeholder="Es. Kit tisane della sera" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Due righe per chi compra</label>
              <textarea className={`${campo} resize-none`} rows={2} maxLength={2000} value={form.description}
                        onChange={e => setForm({ ...form, description: e.target.value })} placeholder="Cosa c'è dentro e a chi serve." />
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Prezzo (€) *</label>
                <input className={campo} type="number" min="0.5" step="0.5" value={form.unit_price} data-testid="pf-prezzo"
                       onChange={e => setForm({ ...form, unit_price: e.target.value })} placeholder="25" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Foto (facoltativa)</label>
                <input type="file" accept="image/*" className="text-xs" onChange={e => setCoverFile(e.target.files?.[0] || null)} />
              </div>
              <div className="sm:col-span-2">
                <label className="block text-xs font-medium text-gray-700 mb-1">Quantità disponibile</label>
                <div className="flex items-center gap-3">
                  <label className="flex items-center gap-1.5 text-sm text-gray-700">
                    <input type="checkbox" checked={form.illimitata} onChange={e => setForm({ ...form, illimitata: e.target.checked })} />
                    Illimitata
                  </label>
                  {!form.illimitata && (
                    <input className={`${campo} w-32`} type="number" min="0" step="1" value={form.quantita} data-testid="pf-quantita"
                           onChange={e => setForm({ ...form, quantita: e.target.value })} placeholder="10" />
                  )}
                </div>
                <p className="mt-1 text-[11px] text-gray-400">Con una quantità, il prodotto sparisce dal profilo quando finisce.</p>
              </div>
            </div>
            <div className="flex justify-end">
              <button type="button" onClick={salvaBozza} disabled={!passo1Ok || salvando} data-testid="pf-avanti-1"
                className={bottone} style={{ background: '#2f5749' }}>
                {salvando ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Avanti: come arriva'}
              </button>
            </div>
          </section>
        )}

        {passo === 1 && (
          <section className="rounded-2xl border bg-white p-5 space-y-4" data-testid="pf-consegna">
            <p className="text-sm text-gray-700">
              Come arrivano i tuoi prodotti fisici. Vale per tutti, lo cambi quando vuoi.
              {consegnaSalvata && <span className="ml-1 inline-flex items-center gap-1 text-emerald-700 text-xs"><CheckCircle2 className="h-3.5 w-3.5" /> già impostato</span>}
            </p>
            <label className="flex items-start gap-3 rounded-xl border p-3 cursor-pointer">
              <input type="checkbox" className="mt-1" checked={consegna.ritiro} data-testid="pf-ritiro"
                     onChange={e => setConsegna({ ...consegna, ritiro: e.target.checked })} />
              <span>
                <span className="block text-sm font-medium text-gray-900">Ritiro di persona</span>
                <span className="block text-xs text-gray-500">Chi compra lo ritira da te: ti scrive per accordarsi.</span>
              </span>
            </label>
            <label className="flex items-start gap-3 rounded-xl border p-3 cursor-pointer">
              <input type="checkbox" className="mt-1" checked={consegna.spedizione} data-testid="pf-spedizione"
                     onChange={e => setConsegna({ ...consegna, spedizione: e.target.checked })} />
              <span className="flex-1">
                <span className="block text-sm font-medium text-gray-900">Spedizione a costo fisso</span>
                <span className="block text-xs text-gray-500">Chi compra lascia l'indirizzo e paga la spedizione insieme al prodotto.</span>
                {consegna.spedizione && (
                  <span className="mt-2 grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <span>
                      <span className="block text-xs font-medium text-gray-700 mb-1">Costo di spedizione (€)</span>
                      <input className={campo} type="number" min="0" step="0.5" value={consegna.costo_spedizione} data-testid="pf-costo"
                             onChange={e => setConsegna({ ...consegna, costo_spedizione: e.target.value })} placeholder="6" />
                    </span>
                    <span>
                      <span className="block text-xs font-medium text-gray-700 mb-1">Gratis sopra (€, facoltativo)</span>
                      <input className={campo} type="number" min="0" step="1" value={consegna.soglia_gratis}
                             onChange={e => setConsegna({ ...consegna, soglia_gratis: e.target.value })} placeholder="50" />
                    </span>
                  </span>
                )}
              </span>
            </label>
            <div className="flex justify-between">
              <button type="button" onClick={() => setPasso(0)} className="text-sm text-gray-500 underline">Indietro</button>
              <button type="button" onClick={salvaConsegna} disabled={!consegnaOk || salvando} data-testid="pf-avanti-2"
                className={bottone} style={{ background: '#2f5749' }}>
                {salvando ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Avanti: pubblica'}
              </button>
            </div>
          </section>
        )}

        {passo === 2 && prodotto && (
          <section className="rounded-2xl border bg-white p-5 space-y-4" data-testid="pf-anteprima">
            <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">Così lo vedranno sul tuo profilo</p>
            <div className="flex gap-4 rounded-xl border p-4">
              <div className="h-20 w-20 flex-none overflow-hidden rounded-lg bg-gray-100">
                {prodotto.image_url && <img src={prodotto.image_url} alt="" className="h-full w-full object-cover" />}
              </div>
              <div className="min-w-0">
                <span className="rounded-full bg-secondary px-2 py-0.5 text-[10px] font-semibold uppercase">Fisico</span>
                <p className="mt-1 font-semibold text-gray-900">{prodotto.name}</p>
                {prodotto.description && <p className="text-sm text-gray-600">{prodotto.description}</p>}
                <p className="mt-1 text-base font-bold text-[#376254]">{fmtEuro(prodotto.unit_price)}</p>
                <p className="text-xs text-gray-500">
                  {[consegna.ritiro ? 'ritiro di persona' : null,
                    consegna.spedizione ? `spedizione ${Number(consegna.costo_spedizione || 0) > 0 ? fmtEuro(consegna.costo_spedizione) : 'inclusa'}` : null]
                    .filter(Boolean).join(' · ')}
                  {prodotto.stock_quantity != null ? ` · ${prodotto.stock_quantity} disponibili` : ''}
                </p>
              </div>
            </div>
            {ragioni.length > 0 && (
              <div className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900" data-testid="pf-ragioni">
                <p className="font-medium">Prima di pubblicare:</p>
                <ul className="mt-1 list-disc pl-5 space-y-0.5">{ragioni.map(r => <li key={r}>{r}</li>)}</ul>
                <Link to="/settings" className="mt-2 inline-block text-xs underline">Vai alle impostazioni</Link>
              </div>
            )}
            <div className="flex justify-between">
              <button type="button" onClick={() => setPasso(1)} className="text-sm text-gray-500 underline">Indietro</button>
              <div className="flex gap-2">
                <button type="button" onClick={() => { toast.success('Salvato in bozza.'); navigate('/prodotti'); }}
                  className="rounded-full border px-4 py-2 text-sm text-gray-700">Salva in bozza</button>
                <button type="button" onClick={pubblica} disabled={salvando} data-testid="pf-pubblica"
                  className={bottone} style={{ background: '#2f5749' }}>
                  {salvando ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Pubblica'}
                </button>
              </div>
            </div>
          </section>
        )}
      </div>
      <DpaPactDialog open={pactOpen} onOpenChange={setPactOpen}
        onAccepted={() => { if (pendingRef.current) { pendingRef.current = false; salvaBozza(); } }} />
    </AppLayout>
  );
}
