/**
 * /prodotti/:id — UN PRODOTTO (P1, 6/10/2026; design DP la sera stessa).
 *
 * Quattro schede, nell'ordine in cui servono: la scheda (titolo, due righe,
 * prezzo, immagine, racconto completo per la pagina), il file o la
 * quantita', la pagina da condividere, le vendite. Pubblica/Togli
 * nell'intestazione. Il tipo non e' un'etichetta: si vede dal file o
 * dalla quantita'.
 */
import React, { useCallback, useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ArrowLeft, Loader2, UploadCloud, CheckCircle2 } from 'lucide-react';
import { toast } from 'sonner';
import { AppLayout, Header } from '../../components/Layout';
import { prodottiAPI, fmtBytes, fmtEuro } from '../../api/prodotti';
import { Bottone, Campo, LinkPagina, Ragioni, Scheda, SceltaImmagine, campo } from './ui';

export default function ProdottoPage() {
  const { id } = useParams();
  const [p, setP] = useState(null);
  const [form, setForm] = useState(null);
  const [vendite, setVendite] = useState(null);
  const [salvando, setSalvando] = useState(false);
  const [file, setFile] = useState(null);
  const [cover, setCover] = useState(null);
  const [avanzamento, setAvanzamento] = useState(null);
  const [ragioni, setRagioni] = useState([]);
  const [sporco, setSporco] = useState(false);

  const load = useCallback(() => {
    prodottiAPI.get(id).then(res => {
      setP(res.data);
      setForm({
        name: res.data.name || '', description: res.data.description || '',
        long_description: res.data.long_description || '',
        unit_price: res.data.unit_price != null ? String(res.data.unit_price) : '',
        max_downloads: res.data.max_downloads_per_delivery || '',
        expiry_days: res.data.access_expiry_days || '',
        stock_quantity: res.data.stock_quantity != null ? String(res.data.stock_quantity) : '',
      });
      setSporco(false);
    }).catch(() => toast.error('Prodotto non trovato.'));
    prodottiAPI.vendite(id).then(res => setVendite(res.data)).catch(() => {});
  }, [id]);
  useEffect(() => { load(); }, [load]);

  const set = (k, v) => { setForm(f => ({ ...f, [k]: v })); setSporco(true); };

  const salva = async () => {
    if (!form || salvando) return;
    setSalvando(true);
    try {
      const upd = {
        name: form.name.trim(), description: form.description.trim() || '',
        long_description: form.long_description,
        unit_price: form.unit_price !== '' ? Number(form.unit_price) : undefined,
      };
      if (p.item_type === 'digital') {
        upd.max_downloads_per_delivery = form.max_downloads ? Number(form.max_downloads) : 0;
        upd.access_expiry_days = form.expiry_days ? Number(form.expiry_days) : 0;
      } else if (form.stock_quantity !== '') {
        upd.stock_quantity = Number(form.stock_quantity);
      }
      let res = await prodottiAPI.update(id, upd);
      if (cover) {
        try { await prodottiAPI.uploadImage(id, cover); setCover(null); res = await prodottiAPI.get(id); }
        catch { toast.error('L\'immagine non è stata caricata: riprova.'); }
      }
      setP(res.data); setSporco(false); toast.success('Salvato.');
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

  if (!p || !form) {
    return <AppLayout><div className="p-8"><Loader2 className="h-5 w-5 animate-spin text-gray-400" /></div></AppLayout>;
  }
  const digitale = p.item_type === 'digital';

  return (
    <AppLayout>
      <Header title={p.name} subtitle={p.is_published ? 'Online sul tuo profilo' : 'Bozza: non si vede ancora'}>
        {p.is_published
          ? <Bottone variante="secondario" onClick={ritira} disabled={salvando} className="min-h-[40px]" data-testid="prodotto-ritira">Togli dal profilo</Bottone>
          : <Bottone onClick={pubblica} disabled={salvando} className="min-h-[40px]" data-testid="prodotto-pubblica">Pubblica</Bottone>}
      </Header>
      <div className="p-4 md:p-8 animate-fade-in max-w-3xl space-y-5" data-testid="prodotto-page">
        <Link to="/prodotti" className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-900">
          <ArrowLeft className="h-4 w-4" aria-hidden /> I tuoi prodotti
        </Link>

        <Ragioni ragioni={ragioni} testid="prodotto-ragioni" />

        <Scheda title="La scheda" sub="Quello che chi compra legge sul profilo e sulla pagina del prodotto.">
          <div className="space-y-4">
            <Campo label="Titolo" obbligatorio>
              <input className={campo} value={form.name} maxLength={255} onChange={e => set('name', e.target.value)} />
            </Campo>
            <Campo label="Due righe per chi compra" hint="Cosa c'è dentro e a chi serve. Si legge sulla card del profilo.">
              <textarea className={`${campo} resize-none`} rows={2} maxLength={2000} value={form.description} onChange={e => set('description', e.target.value)} />
            </Campo>
            <Campo label="Il racconto completo" hint="Facoltativo. Vive sulla pagina del prodotto: cosa contiene, come usarlo, a chi è pensato. Vai a capo quando vuoi.">
              <textarea className={`${campo} resize-y`} rows={6} maxLength={20000} value={form.long_description}
                        data-testid="prodotto-racconto" onChange={e => set('long_description', e.target.value)} />
            </Campo>
            <div className="grid gap-4 sm:grid-cols-2">
              <Campo label="Prezzo" obbligatorio hint="Pagamento subito con carta, sul tuo conto Stripe.">
                <div className="relative">
                  <input className={`${campo} pr-9`} type="number" inputMode="decimal" min="0" step="0.5" value={form.unit_price} onChange={e => set('unit_price', e.target.value)} />
                  <span className="pointer-events-none absolute inset-y-0 right-3.5 flex items-center text-sm text-gray-400">€</span>
                </div>
              </Campo>
              <SceltaImmagine file={cover} onFile={(f) => { setCover(f); setSporco(true); }} attuale={p.image_url} label="Immagine" />
            </div>
            {digitale ? (
              <div className="grid gap-4 sm:grid-cols-2">
                <Campo label="Scaricamenti per acquisto" hint="Vuoto = illimitati.">
                  <input className={campo} type="number" inputMode="numeric" min="0" max="1000" value={form.max_downloads} placeholder="Illimitati" onChange={e => set('max_downloads', e.target.value)} />
                </Campo>
                <Campo label="Il link scade dopo" hint="Giorni. Vuoto = mai.">
                  <input className={campo} type="number" inputMode="numeric" min="0" max="3650" value={form.expiry_days} placeholder="Mai" onChange={e => set('expiry_days', e.target.value)} />
                </Campo>
              </div>
            ) : (
              <Campo label="Quantità disponibile" hint="Vuoto = illimitata. Con una quantità, sparisce dal profilo quando finisce." className="sm:max-w-xs">
                <input className={campo} type="number" inputMode="numeric" min="0" value={form.stock_quantity} placeholder="Illimitata" onChange={e => set('stock_quantity', e.target.value)} />
              </Campo>
            )}
            <div className="flex items-center justify-between gap-3 border-t border-gray-100 pt-4">
              <span className="text-xs text-gray-400">{sporco ? 'Modifiche non salvate' : 'Tutto salvato'}</span>
              <Bottone onClick={salva} disabled={salvando || !sporco} caricando={salvando} data-testid="prodotto-salva">Salva</Bottone>
            </div>
          </div>
        </Scheda>

        {digitale && (
          <Scheda title="Il file" sub="Resta privato: si scarica solo dall'account di chi ha comprato." data-testid="prodotto-file">
            {p.file
              ? <p className="flex items-center gap-1.5 text-sm text-emerald-800"><CheckCircle2 className="h-4 w-4" aria-hidden /> {p.file.filename} · {fmtBytes(p.file.size_bytes)}</p>
              : <p className="text-sm text-amber-800">Nessun file ancora: senza, non si può pubblicare.</p>}
            <label className="mt-3 flex cursor-pointer items-center gap-3 rounded-xl border border-dashed border-gray-300 px-4 py-3 text-sm text-gray-700 transition hover:border-[#2f5749] hover:bg-[#2f5749]/[0.03]">
              <UploadCloud className="h-5 w-5 flex-none text-gray-400" aria-hidden />
              <span className="min-w-0 truncate">{file ? `${file.name} (${fmtBytes(file.size)})` : (p.file ? 'Sostituisci il file' : 'Scegli il file')}</span>
              <input type="file" className="hidden" onChange={e => setFile(e.target.files?.[0] || null)} />
            </label>
            {avanzamento != null && <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-gray-100"><div className="h-full bg-[#2f5749] transition-all" style={{ width: `${avanzamento}%` }} /></div>}
            {file && <div className="mt-3 flex justify-end"><Bottone variante="secondario" onClick={caricaFile} disabled={salvando} caricando={salvando}>Carica</Bottone></div>}
          </Scheda>
        )}

        <Scheda title="Condividi">
          <LinkPagina orgSlug={p.public_slug} slug={p.slug} online={p.is_published} />
        </Scheda>

        <Scheda title="Vendite" data-testid="prodotto-vendite">
          <div className="grid grid-cols-3 gap-3">
            {[
              [p.venduti_30gg, '30 giorni'],
              [vendite?.total_quantity ?? '—', 'in tutto'],
              [vendite?.total_revenue != null ? fmtEuro(vendite.total_revenue) : '—', 'incassati'],
            ].map(([n, l]) => (
              <div key={l} className="rounded-xl bg-gray-50 px-3 py-3 text-center">
                <p className="text-lg font-bold text-gray-900">{n}</p>
                <p className="text-xs text-gray-500">{l}</p>
              </div>
            ))}
          </div>
          <p className="mt-3 text-xs text-gray-400">Gli ordini completi sono in <Link to="/orders" className="underline">Ordini</Link>, gli incassi in <Link to="/incassi" className="underline">Incassi</Link>.</p>
        </Scheda>
      </div>
    </AppLayout>
  );
}
