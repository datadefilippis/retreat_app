/**
 * /prodotti — I TUOI PRODOTTI (P1, 6/10/2026; design DP la sera stessa).
 *
 * La casa dei prodotti fisici e digitali venduti dal profilo. Tre cose:
 *   1. i prerequisiti per vendere (incassi, patto, pagina pubblica): una
 *      riga verde quando ci sono, una lista con il gesto giusto quando manca
 *      qualcosa;
 *   2. la lista: foto, nome, stato (bozza/online), prezzo, venduti 30 giorni,
 *      il link della pagina da condividere;
 *   3. «Nuovo prodotto» → due carte: digitale, fisico. La formazione in
 *      presenza si crea da Ritiri (ha una data, zero commissioni).
 * Il backend impone i lucchetti (routers/prodotti.py); qui si mostrano.
 * Il tipo non e' un'etichetta in vetrina: qui resta solo come dato utile
 * (file, quantita').
 */
import React, { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { CheckCircle2, AlertCircle, FileDown, Package, Loader2, Plus, Link2, ChevronRight } from 'lucide-react';
import { toast } from 'sonner';
import { AppLayout, Header } from '../../components/Layout';
import { prodottiAPI, fmtBytes, fmtEuro } from '../../api/prodotti';
import { Bottone, Scheda, Vignetta, urlPagina } from './ui';

function Prerequisito({ ok, label, hint, to, testid }) {
  return (
    <li className="flex items-start gap-3" data-testid={testid}>
      {ok
        ? <CheckCircle2 className="mt-0.5 h-5 w-5 flex-none text-emerald-600" aria-hidden />
        : <AlertCircle className="mt-0.5 h-5 w-5 flex-none text-amber-600" aria-hidden />}
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium text-gray-900">{label}</p>
        {!ok && hint && <p className="mt-0.5 text-xs leading-snug text-gray-500">{hint}</p>}
      </div>
      {!ok && to && (
        <Link to={to} className="inline-flex min-h-[36px] items-center gap-1 rounded-full border border-gray-200 px-3 text-xs font-medium text-gray-800 hover:bg-gray-50">
          Vai <ChevronRight className="h-3.5 w-3.5" aria-hidden />
        </Link>
      )}
    </li>
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
  const orgSlug = data?.public_slug;

  const togli = async (p) => {
    if (!window.confirm(`Togliere «${p.name}» dai tuoi prodotti? Gli ordini passati restano.`)) return;
    try { await prodottiAPI.elimina(p.id); toast.success('Prodotto tolto.'); load(); }
    catch { toast.error('Non sono riuscito a toglierlo. Riprova.'); }
  };

  const copiaLink = async (p) => {
    const url = urlPagina(orgSlug, p.slug);
    if (!url) return;
    try { await navigator.clipboard.writeText(url); toast.success('Link della pagina copiato.'); }
    catch { toast.error('Non sono riuscito a copiare il link.'); }
  };

  return (
    <AppLayout>
      <Header
        title="Prodotti"
        subtitle="Quello che vendi dal tuo profilo: guide, audio, libri, kit."
      >
        <Bottone onClick={() => setScegli(s => !s)} data-testid="prodotti-nuovo" className="min-h-[40px]">
          <Plus className="h-4 w-4" aria-hidden /> <span className="hidden sm:inline">Nuovo prodotto</span><span className="sm:hidden">Nuovo</span>
        </Bottone>
      </Header>
      {/* lo stesso contenitore della Dashboard (p-4 md:p-8), l'Header fuori */}
      <div className="p-4 md:p-8 animate-fade-in max-w-4xl space-y-5" data-testid="prodotti-page">

        {errore && (
          <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900" data-testid="prodotti-errore">
            {errore}
          </div>
        )}

        {/* le due carte della tipologia */}
        {scegli && (
          <div className="space-y-3" data-testid="prodotti-tipologie">
            <div className="grid gap-3 sm:grid-cols-2">
              <button type="button" onClick={() => navigate('/prodotti/nuovo/digitale')} data-testid="tipologia-digitale"
                className="group flex gap-4 rounded-2xl border border-gray-200 bg-white p-5 text-left shadow-sm transition hover:-translate-y-0.5 hover:border-[#2f5749]/40 hover:shadow-md">
                <span className="flex h-11 w-11 flex-none items-center justify-center rounded-xl bg-[#2f5749]/10 text-[#2f5749]"><FileDown className="h-5 w-5" aria-hidden /></span>
                <span className="min-w-0">
                  <span className="block font-semibold text-gray-900">Prodotto digitale</span>
                  <span className="mt-1 block text-sm leading-relaxed text-gray-600">Una guida, un audio, un e-book: carichi il file, chi compra lo scarica dal suo account Aurya.</span>
                </span>
              </button>
              <button type="button" onClick={() => navigate('/prodotti/nuovo/fisico')} data-testid="tipologia-fisico"
                className="group flex gap-4 rounded-2xl border border-gray-200 bg-white p-5 text-left shadow-sm transition hover:-translate-y-0.5 hover:border-[#2f5749]/40 hover:shadow-md">
                <span className="flex h-11 w-11 flex-none items-center justify-center rounded-xl bg-[#2f5749]/10 text-[#2f5749]"><Package className="h-5 w-5" aria-hidden /></span>
                <span className="min-w-0">
                  <span className="block font-semibold text-gray-900">Prodotto fisico</span>
                  <span className="mt-1 block text-sm leading-relaxed text-gray-600">Libri, kit, oggetti: lo spedisci o lo consegni di persona, come preferisci.</span>
                </span>
              </button>
            </div>
            {/* P2 (founder 6/10): la formazione in presenza NON sta qui. E' un'esperienza
                con una data (zero commissioni, Stripe facoltativo) e si crea da Ritiri. */}
            <p className="text-xs leading-relaxed text-gray-500" data-testid="prodotti-nota-formazione">
              Un corso in presenza non è un prodotto: ha una data e dei posti, quindi si crea da{' '}
              <Link to="/events/new?formato=formazione" className="font-medium underline">Ritiri ed esperienze</Link>, senza commissioni.
            </p>
          </div>
        )}

        {/* prerequisiti: una riga quando ci sono, la lista quando manca qualcosa */}
        {data && (prontoAVendere ? (
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900" data-testid="prodotti-prerequisiti">
            <CheckCircle2 className="h-4 w-4 text-emerald-600" aria-hidden />
            <span className="font-medium">Sei pronto a vendere.</span>
            <span className="text-emerald-800/80">Incassi collegati, patto accettato, pagina online.</span>
            <span className="hidden" data-testid="pre-stripe" /><span className="hidden" data-testid="pre-patto" /><span className="hidden" data-testid="pre-pagina" />
          </div>
        ) : (
          <Scheda title="Prima di vendere" sub="Tre cose, una volta sola." data-testid="prodotti-prerequisiti">
            <ul className="space-y-3">
              <Prerequisito ok={pre.stripe_pronto} testid="pre-stripe"
                label="Incassi collegati con Stripe"
                hint={pre.stripe_motivo || 'I prodotti si pagano subito, online, sul tuo conto.'} to="/settings" />
              <Prerequisito ok={pre.patto} testid="pre-patto"
                label="Patto di responsabilità accettato"
                hint="Lo stesso di listino e ritiri: in Impostazioni → Condizioni dell'operatore." to="/settings" />
              <Prerequisito ok={pre.pagina_pubblica} testid="pre-pagina"
                label="La tua pagina pubblica è online"
                hint="Senza la pagina non c'è dove comprare." to="/profilo" />
            </ul>
          </Scheda>
        ))}

        {/* lista */}
        {!data && !errore && <Loader2 className="h-5 w-5 animate-spin text-gray-400" />}
        {data && prodotti.length === 0 && (
          <div className="rounded-2xl border border-dashed border-gray-300 p-8 text-center" data-testid="prodotti-vuoto">
            <span className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-[#2f5749]/10 text-[#2f5749]"><Package className="h-6 w-6" aria-hidden /></span>
            <p className="mt-3 font-medium text-gray-900">Ancora nessun prodotto.</p>
            <p className="mt-1 text-sm text-gray-500">Il primo lo crei in tre gesti.</p>
            <Bottone variante="secondario" onClick={() => setScegli(true)} className="mt-4">
              <Plus className="h-4 w-4" aria-hidden /> Nuovo prodotto
            </Bottone>
          </div>
        )}
        {prodotti.length > 0 && (
          <ul className="space-y-3" data-testid="prodotti-lista">
            {prodotti.map(p => {
              const meta = [
                p.file ? `${p.file.filename} · ${fmtBytes(p.file.size_bytes)}` : (p.item_type === 'digital' ? 'file da caricare' : null),
                p.item_type === 'physical' && p.stock_quantity != null ? `${p.stock_quantity} disponibili` : null,
              ].filter(Boolean).join(' · ');
              return (
                <li key={p.id} data-testid={`prodotto-${p.id}`}
                    className="rounded-2xl border border-gray-200/80 bg-white p-3 shadow-[0_1px_2px_rgba(16,24,40,0.04)] transition hover:border-gray-300 sm:p-4">
                  <div className="flex gap-3 sm:gap-4">
                    <Link to={`/prodotti/${p.id}`} className="flex-none" aria-label={`Apri ${p.name}`}>
                      <Vignetta prodotto={p} className="h-20 w-20 rounded-xl sm:h-24 sm:w-24" />
                    </Link>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-start justify-between gap-2">
                        <Link to={`/prodotti/${p.id}`} className="min-w-0 font-semibold leading-snug text-gray-900 line-clamp-2 hover:underline">{p.name}</Link>
                        <span className={`flex-none rounded-full px-2.5 py-0.5 text-[11px] font-semibold ${p.is_published ? 'bg-emerald-100 text-emerald-800' : 'bg-gray-100 text-gray-600'}`}
                              data-testid={`prodotto-${p.id}-stato`}>
                          {p.is_published ? 'Online' : 'Bozza'}
                        </span>
                      </div>
                      {meta && <p className="mt-0.5 truncate text-xs text-gray-500">{meta}</p>}
                      <div className="mt-2 flex items-baseline gap-3">
                        <span className="text-base font-bold text-[#2f5749]">{fmtEuro(p.unit_price)}</span>
                        <span className="text-xs text-gray-500">
                          {p.venduti_30gg} vendut{p.venduti_30gg === 1 ? 'o' : 'i'} <span className="text-gray-400">· 30 giorni</span>
                        </span>
                      </div>
                    </div>
                  </div>
                  {/* le azioni sotto, a tutta larghezza su telefono */}
                  <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-gray-100 pt-3">
                    <Link to={`/prodotti/${p.id}`} className="inline-flex min-h-[36px] items-center rounded-full border border-gray-200 px-4 text-xs font-medium text-gray-800 hover:bg-gray-50">Modifica</Link>
                    {p.is_published && orgSlug && p.slug && (
                      <button type="button" onClick={() => copiaLink(p)}
                        className="inline-flex min-h-[36px] items-center gap-1.5 rounded-full border border-gray-200 px-4 text-xs font-medium text-gray-800 hover:bg-gray-50"
                        data-testid={`prodotto-${p.id}-link`}>
                        <Link2 className="h-3.5 w-3.5" aria-hidden /> Copia link
                      </button>
                    )}
                    <button type="button" onClick={() => togli(p)} className="ml-auto min-h-[36px] px-2 text-xs text-gray-400 hover:text-red-700">Togli</button>
                  </div>
                </li>
              );
            })}
          </ul>
        )}

        {/* la commissione in chiaro, con il piano; il limite del piano accanto */}
        {data?.commissione && (
          <p className="text-xs leading-relaxed text-gray-500" data-testid="prodotti-commissione">
            {Math.max(data.commissione.digital || 0, data.commissione.physical || 0) > 0
              ? <>Sui prodotti venduti Aurya trattiene il <b className="text-gray-700">{data.commissione.digital}%</b> col tuo piano, più i costi Stripe. Ritiri, eventi e servizi restano senza commissioni.</>
              : <>Col tuo piano Aurya non trattiene commissioni sui prodotti: resta solo il costo di Stripe.</>}
            {' '}<Link to="/costi" className="underline">Come funziona</Link>
            {data.limiti?.products_max > 0 && <> · Il tuo piano: fino a {data.limiti.products_max} prodotti, file fino a {data.limiti.max_file_mb} MB.</>}
          </p>
        )}
      </div>
    </AppLayout>
  );
}
