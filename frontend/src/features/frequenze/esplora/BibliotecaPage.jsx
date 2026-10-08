/**
 * BibliotecaPage — ES1 (8/10/2026): LE FREQUENZE, un catalogo visivo.
 *
 * /sound/esplora: le quattro famiglie come card grandi col loro tono;
 * /sound/esplora?famiglia=bande-cerebrali: la griglia delle schede
 * (nome, Hz, uso in una riga, il grado come puntino), ▶ suona una scheda
 * alla volta nella barra in basso (decisione del founder), il titolo apre
 * la pagina-scheda. Cerca su tutte le 36. Le informazioni al posto giusto:
 * la legenda A/B/C e «come leggere» in un foglio ⓘ; l'avviso vero sta nel
 * sipario prima del primo suono. Niente gesti da atelier, niente basi, niente
 * stanze: quello e' di Crea.
 */
import React, { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import SoundTopbar from '../SoundTopbar';
import { SafetyLine } from '../SafetyCurtain';
import { BIB } from '../content/biblioteca';
import { sluggifica } from '../content/slugScheda';
import { FAMIGLIE, famigliaDaSlug, CAT_INTRO, METODI_CHIAVE, GRADI, HOWTO_BODY } from '../content/biblioteca_testi';
import SelettoreTre from './SelettoreTre';
import BarraAnteprima from './BarraAnteprima';
import { useAnteprimaFrequenza } from './anteprima';
import '../frequenze.css';
import '../meditazioni.css';
import '../casa/casa.css';
import './esplora.css';

const Play = () => (<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8 5v14l11-7z" /></svg>);
const Stop = () => (<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 7h10v10H7z" /></svg>);

export function CardScheda({ s, famiglia, anteprima }) {
  const slug = sluggifica(s.t);
  const suona = anteprima.inAscolto(s);
  return (
    <div className={`scheda-card tono-${famiglia?.tono || 'oro'}${suona ? ' suona' : ''}`} data-testid="esp-scheda">
      {s.g && <span className={`grado-punto ${s.g}`} title={`${s.g} · ${GRADI[s.g]?.label || ''}: ${GRADI[s.g]?.spiega || ''}`}>{s.g}</span>}
      <Link to={`/sound/esplora/${slug}${famiglia ? `?famiglia=${famiglia.slug}` : ''}`} style={{ textDecoration: 'none', color: 'inherit' }}>
        <h3>{s.t}</h3>
        <span className="hz">{s.hz}</span>
      </Link>
      <span className="uso">{s.uso}</span>
      <div className="gesti">
        <button type="button" className="play" onClick={() => anteprima.toggle(s)} aria-label={suona ? `Ferma ${s.t}` : `Ascolta ${s.t}`} data-testid="esp-play">
          {suona ? <Stop /> : <Play />}
        </button>
        <Link to={`/sound/esplora/${slug}${famiglia ? `?famiglia=${famiglia.slug}` : ''}`} className="apri">La scheda →</Link>
      </div>
    </div>
  );
}

function FoglioInfo({ aperto, onChiudi }) {
  if (!aperto) return null;
  return (
    <div className="gate foglio-info" onClick={onChiudi} data-testid="esp-info-foglio">
      <div className="gatebox" onClick={(e) => e.stopPropagation()}>
        <h2 style={{ marginTop: 0 }}>Come leggere la biblioteca</h2>
        <div className="legenda">
          {Object.entries(GRADI).map(([g, v]) => <div key={g}><b>{g}</b><span><strong style={{ color: 'var(--bone)', fontWeight: 500 }}>{v.label}.</strong> {v.spiega}</span></div>)}
        </div>
        <div className="howto" dangerouslySetInnerHTML={{ __html: HOWTO_BODY }} />
        <div className="gatefoot" style={{ marginTop: 14 }}><button type="button" onClick={onChiudi}>Chiudi</button></div>
      </div>
    </div>
  );
}

export default function BibliotecaPage() {
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const famiglia = famigliaDaSlug(params.get('famiglia'));
  const [q, setQ] = useState(params.get('q') || '');
  const [info, setInfo] = useState(false);
  const anteprima = useAnteprimaFrequenza();
  useEffect(() => { document.title = famiglia ? `${famiglia.chiave} · Le frequenze | Aurya Sound` : 'Le frequenze | Aurya Sound'; }, [famiglia]);
  useEffect(() => { window.scrollTo({ top: 0 }); }, [famiglia]);

  const tutte = useMemo(() => FAMIGLIE.flatMap((f) => (BIB[f.chiave] || []).map((s) => ({ ...s, famiglia: f }))), []);
  const cercando = q.trim().length >= 2;
  const risultati = useMemo(() => {
    const qq = q.trim().toLowerCase();
    if (!cercando) return [];
    return tutte.filter((s) => `${s.t} ${s.hz} ${s.uso} ${s.body || ''}`.toLowerCase().includes(qq));
  }, [q, cercando, tutte]);

  const vaiAFamiglia = (f) => { setParams(f ? { famiglia: f.slug } : {}); setQ(''); };

  return (
    <div className={`fqz esplora${anteprima.scheda ? ' con-anteprima' : ''}`} data-testid="biblioteca-page">
      <SoundTopbar firma="Sound" qui="/sound/esplora" />
      <header>
        <div>
          <h1>Le <em>frequenze</em></h1>
          <p className="esp-sub">36 schede in quattro famiglie: cosa sono, a cosa servono, come si ascoltano. Tocca ▶ per sentirle, una alla volta.</p>
        </div>
      </header>
      <main>
        <SelettoreTre attiva="frequenze" />
        <div className="cerca" data-testid="esp-cerca">
          <input type="search" value={q} placeholder="Cerca una frequenza, un ritmo, un metodo" aria-label="Cerca" onChange={(e) => setQ(e.target.value)} />
          <button type="button" className="esp-info" onClick={() => setInfo(true)} title="Come leggere la biblioteca" aria-label="Come leggere la biblioteca" data-testid="esp-info">i</button>
        </div>

        {cercando ? (
          <section className="gruppo" data-testid="esp-risultati">
            <h3>{risultati.length} {risultati.length === 1 ? 'scheda' : 'schede'}</h3>
            {risultati.length ? (
              <div className="schede">{risultati.map((s) => <CardScheda key={s.t} s={s} famiglia={s.famiglia} anteprima={anteprima} />)}</div>
            ) : <p className="esp-sub">Nessuna scheda con queste parole. <button type="button" className="esp-torna" onClick={() => setQ('')}>Togli la ricerca</button></p>}
          </section>
        ) : !famiglia ? (
          <div className="famiglie" data-testid="esp-famiglie">
            {FAMIGLIE.map((f) => (
              <Link key={f.slug} to={`/sound/esplora?famiglia=${f.slug}`} className={`famiglia tono-${f.tono}`} data-testid={`esp-famiglia-${f.slug}`}>
                <span className="etichetta">{(BIB[f.chiave] || []).length} schede</span>
                <h2>{f.chiave}</h2>
                <p>{f.riga}</p>
                <span className="conta">Entra →</span>
              </Link>
            ))}
          </div>
        ) : (
          <section data-testid="esp-famiglia">
            <button type="button" className="esp-torna" onClick={() => vaiAFamiglia(null)} data-testid="esp-torna">← Le famiglie</button>
            <div className="esp-famiglia-testa">
              <div>
                <h2>{famiglia.chiave}</h2>
                <p>{CAT_INTRO[famiglia.chiave]?.p || famiglia.riga}</p>
              </div>
            </div>
            {famiglia.slug === 'metodi' && (
              <ul className="chiave" data-testid="esp-chiave-metodi">
                {METODI_CHIAVE.map(([n, d]) => <li key={n}><b>{n}</b> · {d}</li>)}
              </ul>
            )}
            {(() => {
              const list = BIB[famiglia.chiave] || [];
              if (!list.some((s) => s.group)) return <div className="schede">{list.map((s) => <CardScheda key={s.t} s={s} famiglia={famiglia} anteprima={anteprima} />)}</div>;
              const gruppi = [];
              list.forEach((s) => { const g = s.group || ''; const u = gruppi[gruppi.length - 1]; if (u && u.nome === g) u.items.push(s); else gruppi.push({ nome: g, items: [s] }); });
              return gruppi.map((g) => (
                <section key={g.nome} className="gruppo">
                  {g.nome && <h3>{g.nome}</h3>}
                  <div className="schede">{g.items.map((s) => <CardScheda key={s.t} s={s} famiglia={famiglia} anteprima={anteprima} />)}</div>
                </section>
              ));
            })()}
          </section>
        )}
        <div style={{ marginTop: 28 }}><SafetyLine onOpen={anteprima.openReview} /></div>
      </main>
      <footer className="fqzfoot" data-testid="fqz-foot">
        <a href="/meditazioni">Le meditazioni</a><Link to="/sound/impara">Le fondamenta</Link><Link to="/sound/lab">Il Lab</Link><a href="/sound">Aurya Sound</a>
      </footer>
      <BarraAnteprima anteprima={anteprima} famigliaSlug={famiglia?.slug || ''} />
      <FoglioInfo aperto={info} onChiudi={() => setInfo(false)} />
      {anteprima.curtain}
      {/* eslint-disable-next-line no-unused-vars */}
      {false && navigate}
    </div>
  );
}
