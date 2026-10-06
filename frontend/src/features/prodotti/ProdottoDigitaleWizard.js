/**
 * /prodotti/nuovo/digitale — PRODOTTO DIGITALE IN TRE GESTI (P1, 6/10/2026).
 *
 *   1. Cos'è      titolo, due righe, prezzo, copertina facoltativa
 *   2. Il file    PDF, ePub, audio, zip; barra di avanzamento; limite del piano
 *   3. Pubblica   anteprima della scheda + «Pubblica» (o «Salva in bozza»)
 *
 * Dietro «Altro»: scaricamenti massimi e scadenza del link. Il prodotto
 * nasce in bozza al passo 1 (cosi' il file ha un id a cui agganciarsi);
 * la pubblicazione passa dai tre lucchetti del backend (409 con le
 * ragioni, mostrate in chiaro). Il patto DPA, se manca, apre il dialog
 * come nei wizard di listino e ritiri.
 */
import React, { useEffect, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Loader2, UploadCloud, CheckCircle2 } from 'lucide-react';
import { toast } from 'sonner';
import { AppLayout, Header } from '../../components/Layout';
import DpaPactDialog from '../../components/legal/DpaPactDialog';
import { prodottiAPI, fmtBytes } from '../../api/prodotti';

const PASSI = [
  { key: 'cosa', label: "Cos'è" },
  { key: 'file', label: 'Il file' },
  { key: 'pubblica', label: 'Pubblica' },
];
const ACCETTA = '.pdf,.epub,.mp3,.m4a,.wav,.zip,.mobi,.png,.jpg,.jpeg';

export default function ProdottoDigitaleWizard() {
  const navigate = useNavigate();
  const [passo, setPasso] = useState(0);
  const [form, setForm] = useState({ name: '', description: '', unit_price: '', max_downloads: '', expiry_days: '' });
  const [altro, setAltro] = useState(false);
  const [prodotto, setProdotto] = useState(null);        // creato al passo 1
  const [salvando, setSalvando] = useState(false);
  const [pactOpen, setPactOpen] = useState(false);
  const [coverFile, setCoverFile] = useState(null);
  const [file, setFile] = useState(null);
  const [avanzamento, setAvanzamento] = useState(null);   // 0..100 | null
  const [ragioni, setRagioni] = useState([]);
  const [limiti, setLimiti] = useState(null);
  const pendingRef = useRef(false);

  useEffect(() => {
    prodottiAPI.list().then(res => setLimiti(res.data?.limiti || null)).catch(() => {});
  }, []);

  const prezzoOk = form.unit_price !== '' && Number(form.unit_price) > 0;
  const passo1Ok = form.name.trim().length > 0 && prezzoOk;

  // ── passo 1: crea (o aggiorna) la bozza ──
  const salvaBozza = async () => {
    if (!passo1Ok || salvando) return;
    setSalvando(true);
    try {
      const payload = {
        item_type: 'digital',
        name: form.name.trim(),
        description: form.description.trim() || null,
        unit_price: Number(form.unit_price),
        max_downloads_per_delivery: form.max_downloads ? Number(form.max_downloads) : null,
        access_expiry_days: form.expiry_days ? Number(form.expiry_days) : null,
      };
      let p;
      if (prodotto?.id) {
        const upd = { ...payload };
        delete upd.item_type;
        upd.max_downloads_per_delivery = form.max_downloads ? Number(form.max_downloads) : 0;
        upd.access_expiry_days = form.expiry_days ? Number(form.expiry_days) : 0;
        p = (await prodottiAPI.update(prodotto.id, upd)).data;
      } else {
        p = (await prodottiAPI.create(payload)).data;
      }
      if (coverFile) {
        try {
          const res = await prodottiAPI.uploadImage(p.id, coverFile);
          p = { ...p, image_url: res.data?.image_url || p.image_url };
        } catch { toast.error('La copertina non è stata caricata: puoi riprovare dopo.'); }
      }
      setProdotto(p);
      setPasso(1);
    } catch (err) {
      const d = err?.response?.data?.detail;
      if (d?.code === 'DPA_REQUIRED') { pendingRef.current = true; setPactOpen(true); return; }
      toast.error((typeof d === 'string' && d) || d?.message || 'Non sono riuscito a salvare. Riprova.');
    } finally { setSalvando(false); }
  };

  // ── passo 2: il file ──
  const caricaFile = async () => {
    if (!file || !prodotto?.id || salvando) return;
    const maxMb = limiti?.max_file_mb;
    if (maxMb && file.size > maxMb * 1024 * 1024) {
      toast.error(`Il tuo piano accetta file fino a ${maxMb} MB. Questo pesa ${fmtBytes(file.size)}.`);
      return;
    }
    setSalvando(true); setAvanzamento(0);
    try {
      const res = await prodottiAPI.uploadFile(prodotto.id, file, {
        onUploadProgress: (e) => { if (e.total) setAvanzamento(Math.round((e.loaded / e.total) * 100)); },
      });
      setProdotto(p => ({ ...p, file: res.data }));
      setAvanzamento(100);
      setPasso(2);
    } catch (err) {
      const d = err?.response?.data?.detail;
      toast.error((typeof d === 'string' && d) || 'Il file non è stato caricato. Riprova.');
      setAvanzamento(null);
    } finally { setSalvando(false); }
  };

  // ── passo 3: pubblica ──
  const pubblica = async () => {
    if (!prodotto?.id || salvando) return;
    setSalvando(true); setRagioni([]);
    try {
      await prodottiAPI.pubblica(prodotto.id);
      toast.success('Il prodotto è online sul tuo profilo.');
      navigate('/prodotti');
    } catch (err) {
      const d = err?.response?.data?.detail;
      if (d?.code === 'non_pubblicabile') setRagioni(d.ragioni || []);
      else toast.error((typeof d === 'string' && d) || 'Non sono riuscito a pubblicare. Riprova.');
    } finally { setSalvando(false); }
  };

  const campo = 'w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none';

  return (
    <AppLayout>
      <div className="max-w-2xl space-y-5" data-testid="wizard-digitale">
        <Link to="/prodotti" className="text-xs text-gray-500 hover:underline">← I tuoi prodotti</Link>
        <Header title="Nuovo prodotto digitale" subtitle="Tre gesti: cos'è, il file, pubblica." />

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
              <input className={campo} value={form.name} maxLength={255} data-testid="dg-nome"
                     onChange={e => setForm({ ...form, name: e.target.value })}
                     placeholder="Es. Guida al respiro in 7 giorni" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Due righe per chi compra</label>
              <textarea className={`${campo} resize-none`} rows={2} maxLength={2000} value={form.description}
                        onChange={e => setForm({ ...form, description: e.target.value })}
                        placeholder="Cosa c'è dentro e a chi serve." />
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Prezzo (€) *</label>
                <input className={campo} type="number" min="0.5" step="0.5" value={form.unit_price} data-testid="dg-prezzo"
                       onChange={e => setForm({ ...form, unit_price: e.target.value })} placeholder="12" />
                <p className="mt-1 text-[11px] text-gray-400">Pagamento subito con carta, sul tuo conto Stripe.</p>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Copertina (facoltativa)</label>
                <input type="file" accept="image/*" className="text-xs" onChange={e => setCoverFile(e.target.files?.[0] || null)} />
              </div>
            </div>
            <button type="button" onClick={() => setAltro(a => !a)} className="text-xs text-gray-500 underline">
              {altro ? 'Nascondi' : 'Altro'}: scaricamenti massimi, scadenza del link
            </button>
            {altro && (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Scaricamenti massimi per acquisto</label>
                  <input className={campo} type="number" min="1" max="1000" value={form.max_downloads}
                         onChange={e => setForm({ ...form, max_downloads: e.target.value })} placeholder="Illimitati" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Il link scade dopo (giorni)</label>
                  <input className={campo} type="number" min="1" max="3650" value={form.expiry_days}
                         onChange={e => setForm({ ...form, expiry_days: e.target.value })} placeholder="Mai" />
                </div>
              </div>
            )}
            <div className="flex justify-end">
              <button type="button" onClick={salvaBozza} disabled={!passo1Ok || salvando} data-testid="dg-avanti-1"
                className="rounded-full px-5 py-2 text-sm font-medium text-white disabled:opacity-50" style={{ background: '#2f5749' }}>
                {salvando ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Avanti: il file'}
              </button>
            </div>
          </section>
        )}

        {passo === 1 && (
          <section className="rounded-2xl border bg-white p-5 space-y-4">
            <p className="text-sm text-gray-700">
              Il file che chi compra riceve. PDF, ePub, audio o zip
              {limiti?.max_file_mb ? `, fino a ${limiti.max_file_mb} MB` : ''}. Resta privato: si scarica solo dall'account di chi ha comprato.
            </p>
            {prodotto?.file?.filename && (
              <p className="text-xs text-emerald-700 flex items-center gap-1" data-testid="dg-file-presente">
                <CheckCircle2 className="h-3.5 w-3.5" /> Caricato: {prodotto.file.filename} ({fmtBytes(prodotto.file.size_bytes)})
              </p>
            )}
            <label className="flex cursor-pointer flex-col items-center gap-2 rounded-xl border border-dashed border-gray-300 p-6 text-sm text-gray-600 hover:border-gray-900">
              <UploadCloud className="h-6 w-6 text-gray-400" aria-hidden />
              <span>{file ? `${file.name} (${fmtBytes(file.size)})` : 'Scegli il file'}</span>
              <input type="file" className="hidden" accept={ACCETTA} data-testid="dg-file"
                     onChange={e => { setFile(e.target.files?.[0] || null); setAvanzamento(null); }} />
            </label>
            {avanzamento != null && (
              <div className="h-2 w-full overflow-hidden rounded-full bg-gray-100" aria-label="Avanzamento">
                <div className="h-full bg-[#2f5749] transition-all" style={{ width: `${avanzamento}%` }} />
              </div>
            )}
            <div className="flex justify-between">
              <button type="button" onClick={() => setPasso(0)} className="text-sm text-gray-500 underline">Indietro</button>
              <div className="flex gap-2">
                {prodotto?.file?.filename && !file && (
                  <button type="button" onClick={() => setPasso(2)} className="rounded-full border px-4 py-2 text-sm text-gray-700">Tieni questo file</button>
                )}
                <button type="button" onClick={caricaFile} disabled={!file || salvando} data-testid="dg-avanti-2"
                  className="rounded-full px-5 py-2 text-sm font-medium text-white disabled:opacity-50" style={{ background: '#2f5749' }}>
                  {salvando ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Carica e avanti'}
                </button>
              </div>
            </div>
          </section>
        )}

        {passo === 2 && prodotto && (
          <section className="rounded-2xl border bg-white p-5 space-y-4" data-testid="dg-anteprima">
            <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">Così lo vedranno sul tuo profilo</p>
            <div className="flex gap-4 rounded-xl border p-4">
              <div className="h-20 w-20 flex-none overflow-hidden rounded-lg bg-gray-100">
                {prodotto.image_url && <img src={prodotto.image_url} alt="" className="h-full w-full object-cover" />}
              </div>
              <div className="min-w-0">
                <span className="rounded-full bg-secondary px-2 py-0.5 text-[10px] font-semibold uppercase">Digitale</span>
                <p className="mt-1 font-semibold text-gray-900">{prodotto.name}</p>
                {prodotto.description && <p className="text-sm text-gray-600">{prodotto.description}</p>}
                <p className="mt-1 text-base font-bold text-[#376254]">{Number(prodotto.unit_price).toFixed(2)} €</p>
                <p className="text-xs text-gray-500">{prodotto.file?.filename} · {fmtBytes(prodotto.file?.size_bytes)}</p>
              </div>
            </div>
            {ragioni.length > 0 && (
              <div className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900" data-testid="dg-ragioni">
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
                <button type="button" onClick={pubblica} disabled={salvando} data-testid="dg-pubblica"
                  className="rounded-full px-5 py-2 text-sm font-medium text-white disabled:opacity-50" style={{ background: '#2f5749' }}>
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
