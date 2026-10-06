/**
 * ProdottoLandingPage — LA PAGINA DI UN PRODOTTO (DP, 6/10/2026 sera).
 * Rotta: /prodotto/:org_slug/:slug
 *
 * Founder: «come per gli eventi: un link da condividere, la descrizione del
 * prodotto e le informazioni in più, e si compra anche da lì». Niente
 * etichetta di tipo (fisico/digitale): lo racconta l'operatore. Si compra
 * in pagina con lo stesso checkout del profilo (InlineProdottoCheckout:
 * account Aurya obbligatorio, Stripe). Su telefono la barra con prezzo e
 * «Compra» resta in basso finche' non si apre l'acquisto.
 *
 * Dati: GET /public/prodotto/{org}/{slug} (risolve dal public_slug, come
 * il profilo). Le landing legacy /dg e /ph restano, ma non si linkano piu'.
 */
import React, { useEffect, useRef, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ArrowLeft, Check, Download, Share2, ShieldCheck, Store, Truck, Package, FileDown, SearchX } from 'lucide-react';
import { toast } from 'sonner';
import { storefrontAPI } from '../../api/storefront';
import { fmtBytes, fmtEuro } from '../../api/prodotti';
import useSeoMeta from './lib/useSeoMeta';

const InlineProdottoCheckout = React.lazy(() => import('./components/checkout/InlineProdottoCheckout'));

function testoStelle(stats) {
  const avg = Number(stats?.avg || stats?.average || 0);
  const n = Number(stats?.count || stats?.total || 0);
  if (!n || !avg) return null;
  return `★ ${avg.toFixed(1)} · ${n} recension${n === 1 ? 'e' : 'i'}`;
}

/** GL — la galleria: la foto grande, sotto le altre; frecce, tastiera, dito */
function Galleria({ foto, nome, Segnaposto }) {
  const [i, setI] = useState(0);
  const touchX = useRef(null);
  const n = foto.length;
  const vai = (k) => setI(((k % n) + n) % n);
  useEffect(() => { setI(0); }, [foto]);
  if (n === 0) {
    return (
      <div className="overflow-hidden rounded-3xl bg-gradient-to-br from-[#eef3ef] to-[#dfe8e2] shadow-[0_24px_48px_-32px_rgba(30,47,40,0.35)]">
        <div className="flex aspect-[16/9] w-full items-center justify-center text-[#2f5749]/30 lg:aspect-[4/5]"><Segnaposto className="h-16 w-16" aria-hidden /></div>
      </div>
    );
  }
  return (
    <div data-testid="prodotto-landing-galleria">
      <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-[#eef3ef] to-[#dfe8e2] shadow-[0_24px_48px_-32px_rgba(30,47,40,0.35)]"
           tabIndex={n > 1 ? 0 : -1} role={n > 1 ? 'group' : undefined} aria-label={n > 1 ? `Foto ${i + 1} di ${n}` : undefined}
           onKeyDown={e => { if (e.key === 'ArrowRight') vai(i + 1); if (e.key === 'ArrowLeft') vai(i - 1); }}
           onTouchStart={e => { touchX.current = e.touches[0].clientX; }}
           onTouchEnd={e => {
             if (touchX.current == null) return;
             const dx = e.changedTouches[0].clientX - touchX.current; touchX.current = null;
             if (Math.abs(dx) > 40) vai(dx < 0 ? i + 1 : i - 1);
           }}>
        <img key={foto[i]} src={foto[i]} alt={`${nome}${n > 1 ? ` — foto ${i + 1} di ${n}` : ''}`}
             className="aspect-[4/3] w-full object-cover duration-300 animate-in fade-in lg:aspect-[4/5]" />
        {n > 1 && (
          <>
            <button type="button" onClick={() => vai(i - 1)} aria-label="Foto precedente" data-testid="galleria-prev"
              className="absolute left-3 top-1/2 flex h-10 w-10 -translate-y-1/2 items-center justify-center rounded-full bg-white/90 text-xl text-gray-800 shadow hover:bg-white">‹</button>
            <button type="button" onClick={() => vai(i + 1)} aria-label="Foto successiva" data-testid="galleria-next"
              className="absolute right-3 top-1/2 flex h-10 w-10 -translate-y-1/2 items-center justify-center rounded-full bg-white/90 text-xl text-gray-800 shadow hover:bg-white">›</button>
            <span className="absolute bottom-3 right-3 rounded-full bg-black/50 px-2.5 py-0.5 text-xs font-medium text-white">{i + 1} / {n}</span>
          </>
        )}
      </div>
      {n > 1 && (
        <div className="mt-3 flex gap-2 overflow-x-auto pb-1" data-testid="galleria-miniature">
          {foto.map((u, k) => (
            <button key={u} type="button" onClick={() => vai(k)} aria-label={`Vai alla foto ${k + 1}`} aria-current={k === i}
              className={`h-16 w-20 flex-none overflow-hidden rounded-xl ring-2 transition ${k === i ? 'ring-[#2f5749]' : 'ring-transparent opacity-70 hover:opacity-100'}`}>
              <img src={u} alt="" loading="lazy" className="h-full w-full object-cover" />
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export default function ProdottoLandingPage() {
  const { org_slug: orgSlug, slug } = useParams();
  const [data, setData] = useState(null);
  const [stato, setStato] = useState('loading');   // loading | ready | notfound | error
  const [compra, setCompra] = useState(false);
  const acquistaRef = useRef(null);

  useEffect(() => {
    let vivo = true;
    setStato('loading'); setCompra(false);
    storefrontAPI.getProdottoLanding(orgSlug, slug)
      .then(res => { if (vivo) { setData(res.data); setStato('ready'); } })
      .catch(err => { if (vivo) setStato(err?.response?.status === 404 ? 'notfound' : 'error'); });
    return () => { vivo = false; };
  }, [orgSlug, slug]);

  const pr = data?.prodotto;
  const org = data?.org;
  useSeoMeta({
    title: pr ? `${pr.name} · ${org?.name || ''} | Aurya` : 'Prodotto | Aurya',
    description: pr?.description || pr?.long_description?.slice(0, 160) || undefined,
    image: pr?.image_url || undefined,
    canonicalPath: `/prodotto/${orgSlug}/${slug}`,
  });

  const apriAcquisto = () => {
    setCompra(true);
    setTimeout(() => acquistaRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 50);
  };

  const condividi = async () => {
    const url = window.location.href;
    try {
      if (navigator.share) { await navigator.share({ title: pr?.name, url }); return; }
      await navigator.clipboard.writeText(url); toast.success('Link copiato.');
    } catch { /* annullato */ }
  };

  if (stato === 'loading') {
    return <div className="mx-auto max-w-5xl px-4 py-16 text-sm text-gray-500 sm:px-6">Caricamento…</div>;
  }
  if (stato !== 'ready' || !pr) {
    return (
      <div className="mx-auto max-w-md px-4 py-20 text-center" data-testid="prodotto-landing-404">
        <SearchX className="mx-auto h-10 w-10 text-gray-300" aria-hidden />
        <h1 className="mt-4 font-display text-2xl text-gray-900">Questo prodotto non c'è più.</h1>
        <p className="mt-2 text-sm text-gray-600">Forse è stato tolto dal profilo, o il link non è completo.</p>
        <Link to={`/o/${orgSlug}`} className="mt-6 inline-flex rounded-full bg-[#2f5749] px-5 py-2.5 text-sm font-semibold text-white">Vai al profilo</Link>
      </div>
    );
  }

  const digitale = pr.item_type === 'digital';
  const consegna = data.consegna || {};
  const Icona = digitale ? FileDown : Package;
  const esaurito = !digitale && pr.stock_quantity != null && Number(pr.stock_quantity) <= 0;

  return (
    <div className="bg-[#faf8f3]" data-testid="prodotto-landing">
      <div className="mx-auto max-w-5xl px-4 pb-28 pt-5 sm:px-6 sm:pb-16 sm:pt-8">
        <Link to={`/o/${orgSlug}`} className="inline-flex items-center gap-1.5 text-sm text-gray-600 hover:text-gray-900" data-testid="prodotto-landing-back">
          <ArrowLeft className="h-4 w-4" aria-hidden /> {org?.name || 'Il profilo'}
        </Link>

        {/* ── il prodotto: immagine e scheda ── */}
        <div className="mt-5 grid gap-6 lg:grid-cols-[1.05fr_1fr] lg:gap-10">
          <Galleria foto={(pr.galleria && pr.galleria.length ? pr.galleria : (pr.image_url ? [pr.image_url] : []))} nome={pr.name} Segnaposto={Icona} />

          <div className="lg:py-2">
            <h1 className="font-display text-3xl leading-tight text-gray-900 sm:text-4xl">{pr.name}</h1>

            {/* chi lo vende */}
            <Link to={`/o/${orgSlug}`} className="mt-4 inline-flex items-center gap-3 rounded-full bg-white/80 py-1.5 pl-1.5 pr-4 ring-1 ring-gray-200 hover:bg-white" data-testid="prodotto-landing-org">
              <span className="h-9 w-9 overflow-hidden rounded-full bg-gray-200">
                {org?.portrait_url && <img src={org.portrait_url} alt="" className="h-full w-full object-cover" />}
              </span>
              <span className="min-w-0 text-left">
                <span className="flex items-center gap-1 text-sm font-semibold text-gray-900">
                  {org?.name}{org?.verified && <ShieldCheck className="h-4 w-4 text-[#2f5749]" aria-label="Verificato Aurya" />}
                </span>
                <span className="block text-xs text-gray-500">
                  {[[org?.city, org?.region].filter(Boolean).join(', '), testoStelle(org?.reviews_stats)].filter(Boolean).join(' · ')}
                </span>
              </span>
            </Link>

            {pr.description && <p className="mt-5 text-lg leading-relaxed text-gray-700">{pr.description}</p>}

            <div className="mt-6 flex flex-wrap items-center gap-3">
              <span className="text-3xl font-bold text-[#2f5749]" data-testid="prodotto-landing-prezzo">{fmtEuro(pr.price)}</span>
              {!digitale && consegna.spedizione && Number(consegna.costo_spedizione || 0) > 0 && (
                <span className="text-sm text-gray-500">+ spedizione {fmtEuro(consegna.costo_spedizione)}{consegna.soglia_gratis ? `, gratis sopra ${fmtEuro(consegna.soglia_gratis)}` : ''}</span>
              )}
            </div>

            <div className="mt-5 hidden gap-2 sm:flex">
              <button type="button" onClick={apriAcquisto} disabled={esaurito || compra} data-testid="prodotto-landing-compra"
                className="inline-flex min-h-[46px] items-center justify-center rounded-full bg-[#2f5749] px-7 text-sm font-semibold text-white shadow-[0_8px_20px_-10px_rgba(47,87,73,0.7)] transition hover:bg-[#27493d] disabled:opacity-50">
                {esaurito ? 'Esaurito' : compra ? <><Check className="mr-1.5 h-4 w-4" aria-hidden /> Qui sotto</> : 'Compra'}
              </button>
              <button type="button" onClick={condividi} className="inline-flex min-h-[46px] items-center gap-2 rounded-full border border-gray-200 bg-white px-5 text-sm font-medium text-gray-800 hover:bg-gray-50" data-testid="prodotto-landing-condividi">
                <Share2 className="h-4 w-4" aria-hidden /> Condividi
              </button>
            </div>

            {/* come funziona, in tre righe vere */}
            <ul className="mt-6 space-y-2.5 rounded-2xl border border-gray-200 bg-white p-4 text-sm text-gray-700" data-testid="prodotto-landing-come">
              {digitale ? (
                <>
                  <li className="flex gap-2.5"><Download className="mt-0.5 h-4 w-4 flex-none text-[#2f5749]" aria-hidden /><span>Lo ricevi subito dopo il pagamento, nel tuo account Aurya, da qualunque telefono.{pr.file_ext ? ` File ${pr.file_ext.toUpperCase()}${pr.file_size_bytes ? ` · ${fmtBytes(pr.file_size_bytes)}` : ''}.` : ''}</span></li>
                  {(pr.max_downloads || pr.access_expiry_days) && (
                    <li className="flex gap-2.5"><Check className="mt-0.5 h-4 w-4 flex-none text-[#2f5749]" aria-hidden /><span>
                      {[pr.max_downloads ? `fino a ${pr.max_downloads} scaricamenti` : null, pr.access_expiry_days ? `link valido ${pr.access_expiry_days} giorni` : null].filter(Boolean).join(', ')}.
                    </span></li>
                  )}
                </>
              ) : (
                <>
                  {consegna.ritiro && <li className="flex gap-2.5"><Store className="mt-0.5 h-4 w-4 flex-none text-[#2f5749]" aria-hidden /><span>Ritiro di persona: dopo l'acquisto vi accordate per quando.</span></li>}
                  {consegna.spedizione && <li className="flex gap-2.5"><Truck className="mt-0.5 h-4 w-4 flex-none text-[#2f5749]" aria-hidden /><span>Spedizione {Number(consegna.costo_spedizione || 0) > 0 ? `a ${fmtEuro(consegna.costo_spedizione)}` : 'inclusa'}{consegna.soglia_gratis ? `, gratis sopra ${fmtEuro(consegna.soglia_gratis)}` : ''}: lasci l'indirizzo e paghi tutto insieme.</span></li>}
                  {pr.stock_quantity != null && !esaurito && Number(pr.stock_quantity) <= 5 && <li className="flex gap-2.5"><Check className="mt-0.5 h-4 w-4 flex-none text-amber-600" aria-hidden /><span>Ne restano {pr.stock_quantity}.</span></li>}
                </>
              )}
              <li className="flex gap-2.5"><ShieldCheck className="mt-0.5 h-4 w-4 flex-none text-[#2f5749]" aria-hidden /><span>Pagamento sicuro con carta. Serve un account Aurya: ci trovi acquisti e file, per sempre.</span></li>
            </ul>
          </div>
        </div>

        {/* ── l'acquisto, in pagina ── */}
        {compra && (
          <section ref={acquistaRef} id="acquista" className="mt-8 scroll-mt-24 rounded-3xl border border-gray-200 bg-white p-4 sm:p-6" data-testid="prodotto-landing-acquisto">
            <h2 className="font-display text-xl text-gray-900">Compra «{pr.name}»</h2>
            <div className="mt-4">
              <React.Suspense fallback={<p className="text-sm text-gray-500">Caricamento…</p>}>
                <InlineProdottoCheckout orgSlug={orgSlug} row={{ product_id: pr.product_id, item_type: pr.item_type, slug: pr.slug }} onClose={() => setCompra(false)} />
              </React.Suspense>
            </div>
          </section>
        )}

        {/* ── il racconto ── */}
        {pr.long_description && (
          <section className="mt-10 max-w-3xl" data-testid="prodotto-landing-racconto">
            <h2 className="font-display text-2xl text-gray-900">Il racconto</h2>
            <div className="mt-4 whitespace-pre-line text-[17px] leading-relaxed text-gray-700">{pr.long_description}</div>
          </section>
        )}

        {/* ── altro dello stesso operatore ── */}
        {(data.altri || []).length > 0 && (
          <section className="mt-12" data-testid="prodotto-landing-altri">
            <h2 className="font-display text-xl text-gray-900">Altro di {org?.name}</h2>
            <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
              {data.altri.map(a => (
                <Link key={a.product_id} to={`/prodotto/${orgSlug}/${a.slug}`} className="group overflow-hidden rounded-2xl border border-gray-200 bg-white transition hover:shadow-md">
                  <div className="aspect-[4/3] bg-gradient-to-br from-[#eef3ef] to-[#dfe8e2]">
                    {a.image_url && <img src={a.image_url} alt="" loading="lazy" className="h-full w-full object-cover transition group-hover:scale-[1.03]" />}
                  </div>
                  <div className="p-3">
                    <p className="text-sm font-semibold leading-snug text-gray-900 line-clamp-2">{a.name}</p>
                    <p className="mt-1 text-sm font-bold text-[#2f5749]">{fmtEuro(a.price)}</p>
                  </div>
                </Link>
              ))}
            </div>
          </section>
        )}
      </div>

      {/* la barra fissa su telefono: prezzo e Compra sempre a portata di pollice */}
      {!compra && (
        <div className="fixed inset-x-0 bottom-0 z-30 border-t border-gray-200 bg-white/95 px-4 py-3 backdrop-blur sm:hidden" data-testid="prodotto-landing-barra">
          <div className="flex items-center justify-between gap-3">
            <div className="min-w-0">
              <p className="truncate text-xs text-gray-500">{pr.name}</p>
              <p className="text-lg font-bold text-[#2f5749]">{fmtEuro(pr.price)}</p>
            </div>
            <div className="flex gap-2">
              <button type="button" onClick={condividi} aria-label="Condividi" className="flex h-11 w-11 items-center justify-center rounded-full border border-gray-200 bg-white text-gray-700"><Share2 className="h-4 w-4" aria-hidden /></button>
              <button type="button" onClick={apriAcquisto} disabled={esaurito} className="min-h-[44px] rounded-full bg-[#2f5749] px-6 text-sm font-semibold text-white disabled:opacity-50">
                {esaurito ? 'Esaurito' : 'Compra'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
