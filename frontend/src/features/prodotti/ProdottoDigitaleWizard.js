/**
 * /prodotti/nuovo/digitale — PRODOTTO DIGITALE IN TRE GESTI (P1, 6/10/2026;
 * design DP la sera stessa).
 *
 *   1. Cos'è      titolo, due righe, prezzo, immagine; dietro «Altro»: il
 *                 racconto completo per la pagina, scaricamenti, scadenza
 *   2. Il file    PDF, ePub, audio, zip; barra di avanzamento; limite del piano
 *   3. Pubblica   anteprima della card (senza etichetta di tipo) + «Pubblica»
 *
 * Il prodotto nasce in bozza al passo 1 (cosi' il file ha un id a cui
 * agganciarsi); la pubblicazione passa dai tre lucchetti del backend (409
 * con le ragioni, mostrate in chiaro). Il patto DPA, se manca, apre il
 * dialog come nei wizard di listino e ritiri.
 */
import React, { useEffect, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowLeft, UploadCloud, CheckCircle2 } from 'lucide-react';
import { toast } from 'sonner';
import { AppLayout, Header } from '../../components/Layout';
import DpaPactDialog from '../../components/legal/DpaPactDialog';
import { prodottiAPI, fmtBytes } from '../../api/prodotti';
import { AnteprimaProdotto, Bottone, Campo, Ragioni, Scheda, SceltaImmagine, campo, classePasso } from './ui';

const PASSI = [
  { key: 'cosa', label: "Cos'è" },
  { key: 'file', label: 'Il file' },
  { key: 'pubblica', label: 'Pubblica' },
];
const ACCETTA = '.pdf,.epub,.mp3,.m4a,.wav,.zip,.mobi,.png,.jpg,.jpeg';

export default function ProdottoDigitaleWizard() {
  const navigate = useNavigate();
  const [passo, setPasso] = useState(0);
  const [form, setForm] = useState({ name: '', description: '', long_description: '', unit_price: '', max_downloads: '', expiry_days: '' });
  const [altro, setAltro] = useState(false);
  const [prodotto, setProdotto] = useState(null);        // creato al passo 1
  const [salvando, setSalvando] = useState(false);
  const [pactOpen, setPactOpen] = useState(false);
  const [coverFiles, setCoverFiles] = useState([]);   // GL: piu' foto, la prima e' la principale
  const [file, setFile] = useState(null);
  const [avanzamento, setAvanzamento] = useState(null);   // 0..100 | null
  const [ragioni, setRagioni] = useState([]);
  const [limiti, setLimiti] = useState(null);
  const pendingRef = useRef(false);

  useEffect(() => {
    prodottiAPI.list().then(res => setLimiti(res.data?.limiti || null)).catch(() => {});
  }, []);

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));
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
        long_description: form.long_description.trim() || null,
        unit_price: Number(form.unit_price),
        max_downloads_per_delivery: form.max_downloads ? Number(form.max_downloads) : null,
        access_expiry_days: form.expiry_days ? Number(form.expiry_days) : null,
      };
      let p;
      if (prodotto?.id) {
        const upd = { ...payload };
        delete upd.item_type;
        upd.long_description = form.long_description;
        upd.max_downloads_per_delivery = form.max_downloads ? Number(form.max_downloads) : 0;
        upd.access_expiry_days = form.expiry_days ? Number(form.expiry_days) : 0;
        p = (await prodottiAPI.update(prodotto.id, upd)).data;
      } else {
        p = (await prodottiAPI.create(payload)).data;
      }
      if (coverFiles.length) {
        try {
          let ultimo = null;
          for (const f of coverFiles) ultimo = (await prodottiAPI.aggiungiFoto(p.id, f)).data;
          if (ultimo) p = { ...p, image_url: ultimo.image_url, galleria: ultimo.galleria };
          setCoverFiles([]);
        } catch { toast.error('Una foto non è stata caricata: puoi riprovare dalla scheda.'); }
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

  return (
    <AppLayout>
      <Header title="Nuovo prodotto digitale" subtitle="Tre gesti: cos'è, il file, pubblica." />
      <div className="p-4 md:p-8 animate-fade-in max-w-3xl space-y-5" data-testid="wizard-digitale">
        <Link to="/prodotti" className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-900">
          <ArrowLeft className="h-4 w-4" aria-hidden /> I tuoi prodotti
        </Link>

        <ol className="grid grid-cols-3 gap-2" aria-label="Passi">
          {PASSI.map((p, i) => (
            <li key={p.key} data-testid={`passo-${p.key}`} aria-current={i === passo ? 'step' : undefined}
              className={`flex min-h-[40px] items-center justify-center gap-1.5 rounded-full border px-2 text-xs font-semibold transition sm:text-sm ${classePasso(i, passo)}`}>
              {i < passo ? <CheckCircle2 className="h-4 w-4" aria-hidden /> : <span>{i + 1}.</span>}
              <span className="truncate">{p.label}</span>
            </li>
          ))}
        </ol>

        {passo === 0 && (
          <Scheda title="Cos'è" sub="Quello che chi compra legge prima di decidere.">
            <div className="space-y-4">
              <Campo label="Titolo" obbligatorio>
                <input className={campo} value={form.name} maxLength={255} data-testid="dg-nome"
                       onChange={e => set('name', e.target.value)} placeholder="Es. Guida al respiro in 7 giorni" />
              </Campo>
              <Campo label="Due righe per chi compra" hint="Cosa c'è dentro e a chi serve. Si legge sulla card del profilo.">
                <textarea className={`${campo} resize-none`} rows={2} maxLength={2000} value={form.description}
                          onChange={e => set('description', e.target.value)} />
              </Campo>
              <div className="grid gap-4 sm:grid-cols-2">
                <Campo label="Prezzo" obbligatorio hint="Pagamento subito con carta, sul tuo conto Stripe.">
                  <div className="relative">
                    <input className={`${campo} pr-9`} type="number" inputMode="decimal" min="0.5" step="0.5" value={form.unit_price} data-testid="dg-prezzo"
                           onChange={e => set('unit_price', e.target.value)} placeholder="12" />
                    <span className="pointer-events-none absolute inset-y-0 right-3.5 flex items-center text-sm text-gray-400">€</span>
                  </div>
                </Campo>
                <SceltaImmagine multiple files={coverFiles} onFiles={setCoverFiles} label="Immagine (facoltativa)" />
              </div>
              <button type="button" onClick={() => setAltro(a => !a)} className="text-sm font-medium text-[#2f5749] underline-offset-4 hover:underline">
                {altro ? 'Nascondi' : 'Altro'}: racconto completo, scaricamenti, scadenza
              </button>
              {altro && (
                <div className="space-y-4 rounded-xl bg-gray-50 p-4">
                  <Campo label="Il racconto completo" hint="Vive sulla pagina del prodotto: cosa contiene, come usarlo, a chi è pensato.">
                    <textarea className={`${campo} resize-y`} rows={5} maxLength={20000} value={form.long_description}
                              data-testid="dg-racconto" onChange={e => set('long_description', e.target.value)} />
                  </Campo>
                  <div className="grid gap-4 sm:grid-cols-2">
                    <Campo label="Scaricamenti per acquisto" hint="Vuoto = illimitati.">
                      <input className={campo} type="number" inputMode="numeric" min="1" max="1000" value={form.max_downloads}
                             onChange={e => set('max_downloads', e.target.value)} placeholder="Illimitati" />
                    </Campo>
                    <Campo label="Il link scade dopo" hint="Giorni. Vuoto = mai.">
                      <input className={campo} type="number" inputMode="numeric" min="1" max="3650" value={form.expiry_days}
                             onChange={e => set('expiry_days', e.target.value)} placeholder="Mai" />
                    </Campo>
                  </div>
                </div>
              )}
              <div className="flex justify-end border-t border-gray-100 pt-4">
                <Bottone onClick={salvaBozza} disabled={!passo1Ok || salvando} caricando={salvando} data-testid="dg-avanti-1" className="w-full sm:w-auto">
                  Avanti: il file
                </Bottone>
              </div>
            </div>
          </Scheda>
        )}

        {passo === 1 && (
          <Scheda title="Il file" sub={`PDF, ePub, audio o zip${limiti?.max_file_mb ? `, fino a ${limiti.max_file_mb} MB` : ''}. Resta privato: si scarica solo dall'account di chi ha comprato.`}>
            <div className="space-y-4">
              {prodotto?.file?.filename && (
                <p className="flex items-center gap-1.5 text-sm text-emerald-800" data-testid="dg-file-presente">
                  <CheckCircle2 className="h-4 w-4" aria-hidden /> Caricato: {prodotto.file.filename} ({fmtBytes(prodotto.file.size_bytes)})
                </p>
              )}
              <label className="flex cursor-pointer flex-col items-center gap-2 rounded-2xl border-2 border-dashed border-gray-300 px-4 py-8 text-center text-sm text-gray-600 transition hover:border-[#2f5749] hover:bg-[#2f5749]/[0.03]">
                <span className="flex h-12 w-12 items-center justify-center rounded-full bg-[#2f5749]/10 text-[#2f5749]"><UploadCloud className="h-6 w-6" aria-hidden /></span>
                <span className="font-medium text-gray-800">{file ? file.name : 'Scegli il file'}</span>
                <span className="text-xs text-gray-500">{file ? fmtBytes(file.size) : 'oppure trascinalo qui'}</span>
                <input type="file" className="hidden" accept={ACCETTA} data-testid="dg-file"
                       onChange={e => { setFile(e.target.files?.[0] || null); setAvanzamento(null); }} />
              </label>
              {avanzamento != null && (
                <div className="h-2 w-full overflow-hidden rounded-full bg-gray-100" aria-label="Avanzamento">
                  <div className="h-full bg-[#2f5749] transition-all" style={{ width: `${avanzamento}%` }} />
                </div>
              )}
              <div className="flex flex-col-reverse gap-2 border-t border-gray-100 pt-4 sm:flex-row sm:items-center sm:justify-between">
                <button type="button" onClick={() => setPasso(0)} className="min-h-[40px] text-sm text-gray-500 hover:text-gray-900">Indietro</button>
                <div className="flex flex-col gap-2 sm:flex-row">
                  {prodotto?.file?.filename && !file && (
                    <Bottone variante="secondario" onClick={() => setPasso(2)}>Tieni questo file</Bottone>
                  )}
                  <Bottone onClick={caricaFile} disabled={!file || salvando} caricando={salvando} data-testid="dg-avanti-2">Carica e avanti</Bottone>
                </div>
              </div>
            </div>
          </Scheda>
        )}

        {passo === 2 && prodotto && (
          <Scheda title="Pubblica" sub="Così lo vedranno sul tuo profilo." data-testid="dg-anteprima">
            <div className="space-y-4">
              <div className="sm:max-w-sm">
                <AnteprimaProdotto prodotto={prodotto} riga={prodotto.file ? `${prodotto.file.filename} · ${fmtBytes(prodotto.file.size_bytes)} · consegnato dopo il pagamento` : null} />
              </div>
              <Ragioni ragioni={ragioni} testid="dg-ragioni" />
              <div className="flex flex-col-reverse gap-2 border-t border-gray-100 pt-4 sm:flex-row sm:items-center sm:justify-between">
                <button type="button" onClick={() => setPasso(1)} className="min-h-[40px] text-sm text-gray-500 hover:text-gray-900">Indietro</button>
                <div className="flex flex-col gap-2 sm:flex-row">
                  <Bottone variante="secondario" onClick={() => { toast.success('Salvato in bozza.'); navigate('/prodotti'); }}>Salva in bozza</Bottone>
                  <Bottone onClick={pubblica} disabled={salvando} caricando={salvando} data-testid="dg-pubblica">Pubblica</Bottone>
                </div>
              </div>
            </div>
          </Scheda>
        )}
      </div>
      <DpaPactDialog open={pactOpen} onOpenChange={setPactOpen}
        onAccepted={() => { if (pendingRef.current) { pendingRef.current = false; salvaBozza(); } }} />
    </AppLayout>
  );
}
