/**
 * /prodotti — I TUOI PRODOTTI (P1, 6/10/2026).
 *
 * La casa dei prodotti fisici e digitali venduti dal profilo. Tre cose:
 *   1. i prerequisiti per vendere (incassi, patto, pagina pubblica) con
 *      il gesto giusto per ciascuno;
 *   2. la lista: tipo, stato (bozza/online), prezzo, venduti 30 giorni;
 *   3. «Nuovo prodotto» → tre carte: digitale (ora), fisico (P2, in
 *      arrivo), formazione in presenza (apre il wizard eventi con il
 *      formato gia' scelto).
 * Il backend impone i lucchetti (routers/prodotti.py); qui si mostrano.
 */
import React, { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { CheckCircle2, AlertCircle, FileDown, Package, Loader2, Plus } from 'lucide-react';
import { toast } from 'sonner';
import { AppLayout, Header } from '../../components/Layout';
import { prodottiAPI, fmtBytes, fmtEuro } from '../../api/prodotti';

function Prerequisito({ ok, label, hint, to, testid }) {
  return (
    <div className="flex items-start gap-2.5" data-testid={testid}>
      {ok
        ? <CheckCircle2 className="mt-0.5 h-4 w-4 text-emerald-600 flex-none" aria-hidden />
        : <AlertCircle className="mt-0.5 h-4 w-4 text-amber-600 flex-none" aria-hidden />}
      <div className="min-w-0">
        <p className="text-sm text-gray-900">{label}</p>
        {!ok && hint && (
          <p className="text-xs text-gray-500">
            {hint}{' '}
            {to && <Link to={to} className="underline text-[#376254]">Vai</Link>}
          </p>
        )}
      </div>
    </div>
  );
}

export default function ProdottiPage() {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [errore, setErrore] = useState(null);
  const [scegli, setScegli] = useState(false);

  const load = useCallback(() => {
    prodottiAPI.list()
      .then(res => setData(res.data))
      .catch(err => {
        const d = err?.response?.data?.detail;
        setErrore(d?.error === 'module_not_active'
          ? (d.message || 'Il modulo Prodotti non è attivo per la tua organizzazione.')
          : 'Non riesco a caricare i prodotti. Riprova fra poco.');
      });
  }, []);
  useEffect(() => { load(); }, [load]);

  const pre = data?.prerequisiti || {};
  const prontoAVendere = !!(pre.stripe_pronto && pre.patto && pre.pagina_pubblica);
  const prodotti = data?.prodotti || [];

  const togli = async (p) => {
    if (!window.confirm(`Togliere «${p.name}» dai tuoi prodotti? Gli ordini passati restano.`)) return;
    try { await prodottiAPI.elimina(p.id); toast.success('Prodotto tolto.'); load(); }
    catch { toast.error('Non sono riuscito a toglierlo. Riprova.'); }
  };

  return (
    <AppLayout>
        <Header
          title="Prodotti"
          subtitle="Quello che vendi dal tuo profilo: guide, audio, libri, kit. Chi compra usa l'account Aurya, tu incassi con Stripe."
        >
          <button type="button" onClick={() => setScegli(s => !s)} data-testid="prodotti-nuovo"
            className="inline-flex items-center gap-1.5 rounded-full px-4 py-2 text-sm font-medium text-white"
            style={{ background: '#2f5749' }}>
            <Plus className="h-4 w-4" aria-hidden /> Nuovo prodotto
          </button>
        </Header>
      {/* 6/10 sera (founder: «margini giusti come nelle altre pagine»): lo
          stesso contenitore della Dashboard (p-4 md:p-8), l'Header fuori */}
      <div className="p-4 md:p-8 animate-fade-in max-w-4xl space-y-6" data-testid="prodotti-page">

        {errore && (
          <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900" data-testid="prodotti-errore">
            {errore}
          </div>
        )}

        {/* le tre carte della tipologia */}
        {scegli && (
          <div className="grid gap-4 md:grid-cols-3" data-testid="prodotti-tipologie">
            <button type="button" onClick={() => navigate('/prodotti/nuovo/digitale')} data-testid="tipologia-digitale"
              className="rounded-2xl border bg-white p-5 text-left shadow-sm transition hover:-translate-y-0.5 hover:shadow-md">
              <FileDown className="h-6 w-6 text-[#376254]" aria-hidden />
              <p className="mt-2 font-semibold text-gray-900">Prodotto digitale</p>
              <p className="mt-1 text-sm text-gray-600">Una guida, un audio, un e-book: carichi il file, chi compra lo scarica dal suo account Aurya.</p>
            </button>
            <button type="button" onClick={() => navigate('/prodotti/nuovo/fisico')} data-testid="tipologia-fisico"
              className="rounded-2xl border bg-white p-5 text-left shadow-sm transition hover:-translate-y-0.5 hover:shadow-md">
              <Package className="h-6 w-6 text-[#376254]" aria-hidden />
              <p className="mt-2 font-semibold text-gray-900">Prodotto fisico</p>
              <p className="mt-1 text-sm text-gray-600">Libri, kit, oggetti: lo spedisci o lo consegni di persona, come preferisci.</p>
            </button>
            {/* P2 (founder 6/10): la formazione in presenza NON sta qui. E' un'esperienza
                con una data (zero commissioni, Stripe facoltativo) e si crea da Ritiri. */}
            <p className="md:col-span-2 text-xs text-gray-500" data-testid="prodotti-nota-formazione">
              Un corso in presenza non è un prodotto: ha una data e dei posti, quindi si crea da{' '}
              <Link to="/events/new?formato=formazione" className="underline">Ritiri ed esperienze</Link>, senza commissioni.
            </p>
          </div>
        )}

        {/* P2 — la commissione in chiaro, con il piano */}
        {data?.commissione && (
          <p className="text-sm text-gray-600" data-testid="prodotti-commissione">
            {Math.max(data.commissione.digital || 0, data.commissione.physical || 0) > 0
              ? <>Sui prodotti venduti Aurya trattiene il <b>{data.commissione.digital}%</b> col tuo piano, più i costi Stripe. Ritiri, eventi e servizi restano senza commissioni. <Link to="/costi" className="underline">Come funziona</Link></>
              : <>Col tuo piano Aurya non trattiene commissioni sui prodotti: resta solo il costo di Stripe. <Link to="/costi" className="underline">Come funziona</Link></>}
          </p>
        )}

        {/* prerequisiti */}
        {data && (
          <section className="rounded-2xl border bg-white p-5" data-testid="prodotti-prerequisiti">
            <h2 className="text-sm font-semibold text-gray-900">
              {prontoAVendere ? 'Sei pronto a vendere' : 'Prima di vendere'}
            </h2>
            <div className="mt-3 space-y-2.5">
              <Prerequisito ok={pre.stripe_pronto} testid="pre-stripe"
                label="Incassi collegati con Stripe"
                hint={pre.stripe_motivo || 'I prodotti si pagano subito, online, sul tuo conto.'} to="/settings" />
              <Prerequisito ok={pre.patto} testid="pre-patto"
                label="Patto di responsabilità accettato"
                hint="Lo stesso di listino e ritiri: lo trovi in Impostazioni → Condizioni dell'operatore." to="/settings" />
              <Prerequisito ok={pre.pagina_pubblica} testid="pre-pagina"
                label="La tua pagina pubblica è online"
                hint="Senza la pagina non c'è dove comprare." to="/profilo" />
            </div>
            {data.limiti?.products_max > 0 && (
              <p className="mt-3 text-xs text-gray-400">
                Il tuo piano: fino a {data.limiti.products_max} prodotti, file fino a {data.limiti.max_file_mb} MB.
              </p>
            )}
          </section>
        )}

        {/* lista */}
        {!data && !errore && <Loader2 className="h-5 w-5 animate-spin text-gray-400" />}
        {data && prodotti.length === 0 && (
          <div className="rounded-2xl border border-dashed p-8 text-center text-gray-500" data-testid="prodotti-vuoto">
            <p className="text-sm">Ancora nessun prodotto. Il primo lo crei in tre gesti.</p>
            <button type="button" onClick={() => setScegli(true)}
              className="mt-3 inline-flex items-center gap-1.5 rounded-full border px-4 py-2 text-sm text-gray-700 hover:bg-gray-50">
              <Plus className="h-4 w-4" aria-hidden /> Nuovo prodotto
            </button>
          </div>
        )}
        {prodotti.length > 0 && (
          <div className="grid gap-3 sm:grid-cols-2" data-testid="prodotti-lista">
            {prodotti.map(p => (
              <div key={p.id} className="flex gap-3 rounded-2xl border bg-white p-3 shadow-sm" data-testid={`prodotto-${p.id}`}>
                <Link to={`/prodotti/${p.id}`} className="h-16 w-16 flex-none overflow-hidden rounded-xl bg-gray-100">
                  {p.image_url
                    ? <img src={p.image_url} alt="" className="h-full w-full object-cover" />
                    : <span className="flex h-full w-full items-center justify-center text-gray-300">
                        {p.item_type === 'digital' ? <FileDown className="h-6 w-6" /> : <Package className="h-6 w-6" />}
                      </span>}
                </Link>
                <div className="min-w-0 flex-1">
                  <div className="flex items-start justify-between gap-2">
                    <Link to={`/prodotti/${p.id}`} className="min-w-0 font-medium text-gray-900 leading-snug line-clamp-2 hover:underline">{p.name}</Link>
                    <span className={`flex-none rounded-full px-2 py-0.5 text-[11px] font-medium ${p.is_published ? 'bg-emerald-100 text-emerald-800' : 'bg-gray-100 text-gray-600'}`}
                          data-testid={`prodotto-${p.id}-stato`}>
                      {p.is_published ? 'Online' : 'Bozza'}
                    </span>
                  </div>
                  <p className="mt-0.5 text-xs text-gray-500 truncate">
                    {p.tipo_etichetta}
                    {p.file ? ` · ${p.file.filename} (${fmtBytes(p.file.size_bytes)})` : (p.item_type === 'digital' ? ' · file da caricare' : '')}
                    {p.item_type === 'physical' && p.stock_quantity != null ? ` · ${p.stock_quantity} disponibili` : ''}
                  </p>
                  <div className="mt-2 flex items-center justify-between gap-2">
                    <span className="text-sm font-bold text-[#376254]">{fmtEuro(p.unit_price)}</span>
                    <span className="text-[11px] text-gray-400">{p.venduti_30gg} vendut{p.venduti_30gg === 1 ? 'o' : 'i'} in 30 giorni</span>
                    <span className="flex items-center gap-2">
                      <Link to={`/prodotti/${p.id}`} className="rounded-full border px-3 py-1 text-xs text-gray-700 hover:bg-gray-50">Modifica</Link>
                      <button type="button" onClick={() => togli(p)} className="text-xs text-gray-400 hover:text-red-700">Togli</button>
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </AppLayout>
  );
}
