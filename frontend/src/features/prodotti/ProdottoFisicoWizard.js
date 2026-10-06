/**
 * /prodotti/nuovo/fisico — PRODOTTO FISICO IN TRE GESTI (P2, 6/10/2026;
 * design DP la sera stessa).
 *
 *   1. Cos'è        titolo, due righe, prezzo, immagine, quantita' (o
 *                   illimitata); dietro «Altro»: il racconto completo
 *   2. Come arriva  ritiro di persona e/o spedizione a costo fisso (vale per
 *                   tutti i tuoi fisici: una scelta sola, si cambia quando vuoi)
 *   3. Pubblica     anteprima della card (senza etichetta di tipo) + «Pubblica»
 *
 * Il prodotto nasce in bozza al passo 1; la consegna scrive i modi dello
 * store e l'opzione «Spedizione» (riusa spedizione, magazzino e stati di
 * evasione gia' nel gestionale). La pubblicazione passa dai lucchetti del
 * backend (409 con le ragioni). Il patto DPA, se manca, apre il dialog.
 */
import React, { useEffect, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowLeft, CheckCircle2, Store, Truck } from 'lucide-react';
import { toast } from 'sonner';
import { AppLayout, Header } from '../../components/Layout';
import DpaPactDialog from '../../components/legal/DpaPactDialog';
import { prodottiAPI, fmtEuro } from '../../api/prodotti';
import { AnteprimaProdotto, Bottone, Campo, Ragioni, Scheda, SceltaImmagine, campo, classePasso } from './ui';

const PASSI = [
  { key: 'cosa', label: "Cos'è" },
  { key: 'arriva', label: 'Come arriva' },
  { key: 'pubblica', label: 'Pubblica' },
];

function Modo({ attivo, onChange, Icona, titolo, testo, testid, children }) {
  return (
    <label className={`block cursor-pointer rounded-2xl border p-4 transition ${attivo ? 'border-[#2f5749] bg-[#2f5749]/[0.04]' : 'border-gray-200 hover:border-gray-300'}`}>
      <span className="flex items-start gap-3">
        <input type="checkbox" className="mt-1 h-5 w-5 flex-none accent-[#2f5749]" checked={attivo} data-testid={testid} onChange={e => onChange(e.target.checked)} />
        <span className="flex h-9 w-9 flex-none items-center justify-center rounded-xl bg-[#2f5749]/10 text-[#2f5749]"><Icona className="h-4.5 w-4.5" aria-hidden /></span>
        <span className="min-w-0 flex-1">
          <span className="block text-sm font-semibold text-gray-900">{titolo}</span>
          <span className="block text-xs leading-snug text-gray-500">{testo}</span>
          {attivo && children}
        </span>
      </span>
    </label>
  );
}

export default function ProdottoFisicoWizard() {
  const navigate = useNavigate();
  const [passo, setPasso] = useState(0);
  const [form, setForm] = useState({ name: '', description: '', long_description: '', unit_price: '', quantita: '', illimitata: true });
  const [altro, setAltro] = useState(false);
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

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));
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
        long_description: form.long_description.trim() || null,
        unit_price: Number(form.unit_price),
        stock_quantity: form.illimitata ? null : Number(form.quantita),
      };
      let p;
      if (prodotto?.id) {
        const upd = { ...payload }; delete upd.item_type; delete upd.stock_quantity;
        upd.long_description = form.long_description;
        if (!form.illimitata) upd.stock_quantity = Number(form.quantita);
        p = (await prodottiAPI.update(prodotto.id, upd)).data;
      } else {
        p = (await prodottiAPI.create(payload)).data;
      }
      if (coverFile) {
        try { const res = await prodottiAPI.uploadImage(p.id, coverFile); p = { ...p, image_url: res.data?.image_url || p.image_url }; setCoverFile(null); }
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

  const rigaConsegna = [
    consegna.ritiro ? 'ritiro di persona' : null,
    consegna.spedizione ? `spedizione ${Number(consegna.costo_spedizione || 0) > 0 ? fmtEuro(consegna.costo_spedizione) : 'inclusa'}` : null,
  ].filter(Boolean).join(' · ') + (prodotto?.stock_quantity != null ? ` · ${prodotto.stock_quantity} disponibili` : '');

  return (
    <AppLayout>
      <Header title="Nuovo prodotto fisico" subtitle="Tre gesti: cos'è, come arriva, pubblica." />
      <div className="p-4 md:p-8 animate-fade-in max-w-3xl space-y-5" data-testid="wizard-fisico">
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
                <input className={campo} value={form.name} maxLength={255} data-testid="pf-nome"
                       onChange={e => set('name', e.target.value)} placeholder="Es. Kit tisane della sera" />
              </Campo>
              <Campo label="Due righe per chi compra" hint="Cosa c'è dentro e a chi serve. Si legge sulla card del profilo.">
                <textarea className={`${campo} resize-none`} rows={2} maxLength={2000} value={form.description}
                          onChange={e => set('description', e.target.value)} />
              </Campo>
              <div className="grid gap-4 sm:grid-cols-2">
                <Campo label="Prezzo" obbligatorio hint="Pagamento subito con carta, sul tuo conto Stripe.">
                  <div className="relative">
                    <input className={`${campo} pr-9`} type="number" inputMode="decimal" min="0.5" step="0.5" value={form.unit_price} data-testid="pf-prezzo"
                           onChange={e => set('unit_price', e.target.value)} placeholder="25" />
                    <span className="pointer-events-none absolute inset-y-0 right-3.5 flex items-center text-sm text-gray-400">€</span>
                  </div>
                </Campo>
                <SceltaImmagine file={coverFile} onFile={setCoverFile} label="Foto (facoltativa)" />
              </div>
              <Campo label="Quantità disponibile" hint="Con una quantità, il prodotto sparisce dal profilo quando finisce.">
                <div className="flex flex-wrap items-center gap-3">
                  <label className="inline-flex min-h-[42px] cursor-pointer items-center gap-2 rounded-xl border border-gray-200 px-3.5 text-sm text-gray-800">
                    <input type="checkbox" className="h-4 w-4 accent-[#2f5749]" checked={form.illimitata} onChange={e => set('illimitata', e.target.checked)} />
                    Illimitata
                  </label>
                  {!form.illimitata && (
                    <input className={`${campo} w-32`} type="number" inputMode="numeric" min="0" step="1" value={form.quantita} data-testid="pf-quantita"
                           onChange={e => set('quantita', e.target.value)} placeholder="10" />
                  )}
                </div>
              </Campo>
              <button type="button" onClick={() => setAltro(a => !a)} className="text-sm font-medium text-[#2f5749] underline-offset-4 hover:underline">
                {altro ? 'Nascondi' : 'Altro'}: il racconto completo per la pagina
              </button>
              {altro && (
                <div className="rounded-xl bg-gray-50 p-4">
                  <Campo label="Il racconto completo" hint="Vive sulla pagina del prodotto: cosa contiene, come usarlo, a chi è pensato.">
                    <textarea className={`${campo} resize-y`} rows={5} maxLength={20000} value={form.long_description}
                              data-testid="pf-racconto" onChange={e => set('long_description', e.target.value)} />
                  </Campo>
                </div>
              )}
              <div className="flex justify-end border-t border-gray-100 pt-4">
                <Bottone onClick={salvaBozza} disabled={!passo1Ok || salvando} caricando={salvando} data-testid="pf-avanti-1" className="w-full sm:w-auto">
                  Avanti: come arriva
                </Bottone>
              </div>
            </div>
          </Scheda>
        )}

        {passo === 1 && (
          <Scheda title="Come arriva" sub="Vale per tutti i tuoi prodotti fisici, lo cambi quando vuoi." data-testid="pf-consegna">
            <div className="space-y-3">
              {consegnaSalvata && (
                <p className="inline-flex items-center gap-1.5 text-xs text-emerald-800"><CheckCircle2 className="h-4 w-4" aria-hidden /> Già impostato: puoi confermare o cambiare.</p>
              )}
              <Modo attivo={consegna.ritiro} onChange={v => setConsegna({ ...consegna, ritiro: v })} Icona={Store} testid="pf-ritiro"
                    titolo="Ritiro di persona" testo="Chi compra lo ritira da te: ti scrive per accordarsi." />
              <Modo attivo={consegna.spedizione} onChange={v => setConsegna({ ...consegna, spedizione: v })} Icona={Truck} testid="pf-spedizione"
                    titolo="Spedizione a costo fisso" testo="Chi compra lascia l'indirizzo e paga la spedizione insieme al prodotto.">
                <span className="mt-3 grid gap-3 sm:grid-cols-2">
                  <Campo label="Costo di spedizione">
                    <div className="relative">
                      <input className={`${campo} pr-9`} type="number" inputMode="decimal" min="0" step="0.5" value={consegna.costo_spedizione} data-testid="pf-costo"
                             onChange={e => setConsegna({ ...consegna, costo_spedizione: e.target.value })} placeholder="6" />
                      <span className="pointer-events-none absolute inset-y-0 right-3.5 flex items-center text-sm text-gray-400">€</span>
                    </div>
                  </Campo>
                  <Campo label="Gratis sopra" hint="Facoltativo.">
                    <div className="relative">
                      <input className={`${campo} pr-9`} type="number" inputMode="decimal" min="0" step="1" value={consegna.soglia_gratis}
                             onChange={e => setConsegna({ ...consegna, soglia_gratis: e.target.value })} placeholder="50" />
                      <span className="pointer-events-none absolute inset-y-0 right-3.5 flex items-center text-sm text-gray-400">€</span>
                    </div>
                  </Campo>
                </span>
              </Modo>
              <div className="flex flex-col-reverse gap-2 border-t border-gray-100 pt-4 sm:flex-row sm:items-center sm:justify-between">
                <button type="button" onClick={() => setPasso(0)} className="min-h-[40px] text-sm text-gray-500 hover:text-gray-900">Indietro</button>
                <Bottone onClick={salvaConsegna} disabled={!consegnaOk || salvando} caricando={salvando} data-testid="pf-avanti-2">Avanti: pubblica</Bottone>
              </div>
            </div>
          </Scheda>
        )}

        {passo === 2 && prodotto && (
          <Scheda title="Pubblica" sub="Così lo vedranno sul tuo profilo." data-testid="pf-anteprima">
            <div className="space-y-4">
              <div className="sm:max-w-sm">
                <AnteprimaProdotto prodotto={prodotto} riga={rigaConsegna} />
              </div>
              <Ragioni ragioni={ragioni} testid="pf-ragioni" />
              <div className="flex flex-col-reverse gap-2 border-t border-gray-100 pt-4 sm:flex-row sm:items-center sm:justify-between">
                <button type="button" onClick={() => setPasso(1)} className="min-h-[40px] text-sm text-gray-500 hover:text-gray-900">Indietro</button>
                <div className="flex flex-col gap-2 sm:flex-row">
                  <Bottone variante="secondario" onClick={() => { toast.success('Salvato in bozza.'); navigate('/prodotti'); }}>Salva in bozza</Bottone>
                  <Bottone onClick={pubblica} disabled={salvando} caricando={salvando} data-testid="pf-pubblica">Pubblica</Bottone>
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
