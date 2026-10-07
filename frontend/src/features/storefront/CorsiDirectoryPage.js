/**
 * CorsiDirectoryPage — LA DIRECTORY DEI CORSI ONLINE (RF, 8/10/2026).
 * Rotte: /corsi e /corsi/:categoria (la categoria e' una famiglia delle
 * discipline, la stessa che l'operatore sceglie creando il corso).
 *
 * Testata, pastiglie delle categorie (solo quelle con corsi), ricerca,
 * ordine, «solo con anteprima gratuita», griglia di card con copertina,
 * professionista, lezioni · durata · accesso, prezzo. Vuota: «I primi corsi
 * stanno arrivando» con le porte verso i professionisti e le esperienze.
 * Dati: GET /api/public/corsi (routers/public.py, directory_corsi).
 */
import React, { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { GraduationCap, Search, Play, Film, Clock, ShieldCheck } from 'lucide-react';
import { storefrontAPI } from '../../api/storefront';
import { fmtEuro } from '../../api/prodotti';
import { fmtDurata } from '../../api/accademia';
import useSeoMeta from './lib/useSeoMeta';
import MarketplaceShell from './components/MarketplaceShell';

const ORDINI = [
  { value: 'recenti', label: 'Più recenti' },
  { value: 'prezzo', label: 'Prezzo: dal più basso' },
  { value: 'prezzo_desc', label: 'Prezzo: dal più alto' },
  { value: 'durata', label: 'Più lunghi' },
];

export function CardCorso({ c }) {
  const accesso = c.access_policy === 'expiring' && c.access_expiry_days ? `${c.access_expiry_days} giorni` : 'per sempre';
  return (
    <Link to={c.url} className="group flex flex-col overflow-hidden rounded-2xl border border-gray-200 bg-white transition hover:-translate-y-0.5 hover:shadow-md" data-testid="corsi-card">
      <div className="relative aspect-[16/10] overflow-hidden bg-gradient-to-br from-[#eef3ef] to-[#dfe8e2]">
        {c.image_url
          ? <img src={c.image_url} alt="" loading="lazy" className="h-full w-full object-cover transition duration-500 group-hover:scale-[1.03]" />
          : <span className="flex h-full w-full items-center justify-center text-[#376254]/30"><GraduationCap className="h-10 w-10" aria-hidden /></span>}
        {(c.has_trailer || c.anteprime > 0) && (
          <span className="absolute left-3 top-3 inline-flex items-center gap-1 rounded-full bg-white/90 px-2.5 py-1 text-[11px] font-semibold text-gray-900 shadow-sm">
            <Play className="h-3 w-3 fill-current" aria-hidden /> Anteprima gratuita
          </span>
        )}
        {c.categoria_label && (
          <span className="absolute bottom-3 left-3 rounded-full bg-black/55 px-2.5 py-1 text-[11px] font-medium text-white">{c.categoria_label}</span>
        )}
      </div>
      <div className="flex flex-1 flex-col p-4">
        <h3 className="font-semibold leading-snug text-gray-900 line-clamp-2">{c.name}</h3>
        <p className="mt-1 flex items-center gap-2 text-xs text-gray-500">
          <span className="h-5 w-5 overflow-hidden rounded-full bg-gray-200">{c.org?.portrait_url && <img src={c.org.portrait_url} alt="" className="h-full w-full object-cover" />}</span>
          <span className="truncate">{c.instructor_name || c.org?.name}{c.org?.city ? ` · ${c.org.city}` : ''}</span>
        </p>
        {c.description && <p className="mt-2 text-sm text-gray-600 line-clamp-2">{c.description}</p>}
        <div className="mt-auto flex items-end justify-between gap-3 pt-3">
          <p className="text-xs text-gray-500">
            <Film className="mr-1 inline h-3.5 w-3.5 align-[-2px]" aria-hidden />{c.lezioni_count} lezion{c.lezioni_count === 1 ? 'e' : 'i'}
            {c.durata_totale_seconds > 0 && <> · <Clock className="mr-1 inline h-3.5 w-3.5 align-[-2px]" aria-hidden />{fmtDurata(c.durata_totale_seconds)}</>}
            <span className="block">Accesso {accesso}</span>
          </p>
          <span className="text-lg font-bold text-[#2f5749]">{fmtEuro(c.price)}</span>
        </div>
      </div>
    </Link>
  );
}

export default function CorsiDirectoryPage() {
  const { categoria } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState('');
  const [ordina, setOrdina] = useState('recenti');
  const [soloAnteprima, setSoloAnteprima] = useState(false);

  useEffect(() => {
    let vivo = true;
    setLoading(true);
    const params = { ordina };
    if (categoria) params.categoria = categoria;
    if (q.trim()) params.q = q.trim();
    if (soloAnteprima) params.anteprima = true;
    const t = setTimeout(() => {
      storefrontAPI.getCorsiDirectory(params)
        .then(res => { if (vivo) { setData(res.data); setLoading(false); } })
        .catch(() => { if (vivo) { setData({ corsi: [], categorie: [], total: 0 }); setLoading(false); } });
    }, q ? 250 : 0);
    return () => { vivo = false; clearTimeout(t); };
  }, [categoria, q, ordina, soloAnteprima]);

  const categorie = data?.categorie || [];
  const corsi = data?.corsi || [];
  const catLabel = useMemo(() => categorie.find(c => c.slug === categoria)?.label || null, [categorie, categoria]);
  const vuotaDavvero = !loading && corsi.length === 0 && !q && !soloAnteprima && !categoria;

  useSeoMeta({
    title: catLabel ? `Corsi online di ${catLabel} | Aurya` : 'Corsi online di benessere e pratiche olistiche | Aurya',
    description: 'I corsi online dei professionisti della rete Aurya: video lezioni da seguire dal tuo account, con un\'anteprima gratuita prima di comprare.',
    canonicalPath: categoria ? `/corsi/${categoria}` : '/corsi',
    noindex: !loading && corsi.length === 0,
  });

  return (
    <MarketplaceShell>
      <div className="bg-[#faf8f3]" data-testid="corsi-directory">
        {/* ── testata ── */}
        <div className="border-b border-gray-200/70 bg-gradient-to-br from-[#eef3ef] to-[#faf8f3]">
          <div className="mx-auto max-w-6xl px-4 pb-6 pt-8 sm:pb-8 sm:pt-12">
            <p className="text-[11px] font-semibold uppercase tracking-wider text-[#2f5749]">Aurya Accademia</p>
            <h1 className="mt-1 font-display text-3xl text-gray-900 sm:text-4xl" data-testid="corsi-titolo">
              {catLabel ? `Corsi online di ${catLabel}` : 'Corsi online'}
            </h1>
            <p className="mt-2 max-w-2xl text-base text-gray-600">
              Video lezioni dei professionisti della rete, da seguire dal tuo account quando vuoi. Ogni corso ha un'anteprima gratuita: guardi, poi decidi.
            </p>
          </div>
        </div>

        {/* ── pastiglie delle categorie: solo quelle con corsi ── */}
        {categorie.length > 0 && (
          <div className="border-b border-gray-200/70 bg-white/70 backdrop-blur">
            <div className="mx-auto flex max-w-6xl gap-2 overflow-x-auto px-4 py-3 [scrollbar-width:none]" data-testid="corsi-categorie">
              <button type="button" onClick={() => navigate('/corsi')}
                className={`flex-none rounded-full px-4 py-1.5 text-sm font-medium transition ${!categoria ? 'bg-[#2f5749] text-white' : 'bg-white text-gray-700 ring-1 ring-gray-200 hover:bg-gray-50'}`}>
                Tutti
              </button>
              {categorie.map(c => (
                <button key={c.slug} type="button" onClick={() => navigate(`/corsi/${c.slug}`)} aria-pressed={categoria === c.slug}
                  className={`flex-none rounded-full px-4 py-1.5 text-sm font-medium transition ${categoria === c.slug ? 'bg-[#2f5749] text-white' : 'bg-white text-gray-700 ring-1 ring-gray-200 hover:bg-gray-50'}`}>
                  {c.label} <span className="opacity-60">· {c.n}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        <main className="mx-auto max-w-6xl px-4 py-6 sm:py-8">
          {/* ── ricerca e ordine ── */}
          {!vuotaDavvero && (
            <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-center">
              <label className="relative flex-1">
                <Search className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" aria-hidden />
                <input value={q} onChange={e => setQ(e.target.value)} placeholder="Cerca un corso o un professionista" data-testid="corsi-cerca"
                  className="w-full rounded-full border border-gray-200 bg-white py-2.5 pl-10 pr-4 text-sm outline-none focus:border-[#2f5749] focus:ring-2 focus:ring-[#2f5749]/15" />
              </label>
              <div className="flex items-center gap-2">
                <select value={ordina} onChange={e => setOrdina(e.target.value)} aria-label="Ordina" data-testid="corsi-ordina"
                  className="rounded-full border border-gray-200 bg-white px-3.5 py-2.5 text-sm outline-none focus:border-[#2f5749]">
                  {ORDINI.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
                <button type="button" onClick={() => setSoloAnteprima(v => !v)} aria-pressed={soloAnteprima} data-testid="corsi-anteprima"
                  className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-3.5 py-2.5 text-sm font-medium ${soloAnteprima ? 'bg-[#2f5749] text-white' : 'border border-gray-200 bg-white text-gray-700 hover:bg-gray-50'}`}>
                  <Play className="h-3.5 w-3.5 fill-current" aria-hidden /> Con anteprima
                </button>
              </div>
            </div>
          )}

          {loading ? (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {[0, 1, 2].map(i => <div key={i} className="h-72 animate-pulse rounded-2xl bg-gray-100" />)}
            </div>
          ) : corsi.length > 0 ? (
            <>
              <p className="mb-3 text-xs text-gray-500" data-testid="corsi-conteggio">{corsi.length} cors{corsi.length === 1 ? 'o' : 'i'}</p>
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3" data-testid="corsi-griglia">
                {corsi.map(c => <CardCorso key={c.product_id} c={c} />)}
              </div>
            </>
          ) : vuotaDavvero ? (
            <div className="mx-auto max-w-lg rounded-3xl border border-dashed border-gray-300 bg-white px-6 py-12 text-center" data-testid="corsi-vuota">
              <span className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-[#2f5749]/10 text-[#2f5749]"><GraduationCap className="h-7 w-7" aria-hidden /></span>
              <h2 className="mt-4 font-display text-2xl text-gray-900">I primi corsi stanno arrivando.</h2>
              <p className="mt-2 text-sm text-gray-600">I professionisti della rete li stanno preparando. Intanto puoi conoscerli, o scegliere un'esperienza dal vivo.</p>
              <div className="mt-6 flex flex-wrap justify-center gap-2">
                <Link to="/operatori" className="rounded-full bg-[#2f5749] px-5 py-2.5 text-sm font-semibold text-white">I professionisti</Link>
                <Link to="/esperienze" className="rounded-full border border-gray-200 bg-white px-5 py-2.5 text-sm font-medium text-gray-800">Le esperienze</Link>
              </div>
            </div>
          ) : (
            <div className="rounded-2xl border border-gray-200 bg-white px-6 py-10 text-center" data-testid="corsi-nessun-risultato">
              <p className="text-sm text-gray-600">Nessun corso con questi filtri.</p>
              <button type="button" onClick={() => { setQ(''); setSoloAnteprima(false); navigate('/corsi'); }} className="mt-3 text-sm font-medium text-[#2f5749] underline-offset-4 hover:underline">Togli i filtri</button>
            </div>
          )}

          <p className="mt-10 flex items-start gap-2 text-xs text-gray-500">
            <ShieldCheck className="mt-0.5 h-4 w-4 flex-none text-[#2f5749]" aria-hidden />
            Compri con il tuo account Aurya e paghi con carta. Il corso resta nel tuo account: riprendi da dove eri, lezione dopo lezione.
          </p>
        </main>
      </div>
    </MarketplaceShell>
  );
}
