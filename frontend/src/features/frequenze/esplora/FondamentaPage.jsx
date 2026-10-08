/**
 * FondamentaPage — ES4 (8/10/2026): LE FONDAMENTA a capitoli.
 *
 * /sound/impara: la guida (GuidaView, intatta: e' editoriale e pinnata dai
 * test) letta per capitoli: un indice sticky con il capitolo corrente, le
 * ancore condivisibili (#gd-metodi), «capitolo successivo» in fondo a ogni
 * capitolo. /sound/impara/glossario: il glossario. Stesso selettore a tre.
 */
import React, { useEffect, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import SoundTopbar from '../SoundTopbar';
import GuidaView from '../GuidaView';
import { PERCORSO } from '../content/guida';
import { famigliaDaChiave } from '../content/biblioteca_testi';
import SelettoreTre from './SelettoreTre';
import '../frequenze.css';
import '../meditazioni.css';
import '../casa/casa.css';
import './esplora.css';

export default function FondamentaPage() {
  const navigate = useNavigate();
  const { pathname, hash } = useLocation();
  const glossario = /\/glossario\/?$/.test(pathname);
  const [corrente, setCorrente] = useState(PERCORSO[0]?.id);
  const [learn, setLearn] = useState(null);
  useEffect(() => { document.title = glossario ? 'Glossario del suono | Aurya Sound' : 'Le fondamenta del suono | Aurya Sound'; }, [glossario]);

  /* il capitolo corrente: il primo visibile sotto l'indice */
  useEffect(() => {
    if (glossario) return undefined;
    const sez = PERCORSO.map((p) => document.getElementById(p.id)).filter(Boolean);
    if (!sez.length || typeof IntersectionObserver === 'undefined') return undefined;
    const io = new IntersectionObserver((entries) => {
      const visibili = entries.filter((e) => e.isIntersecting).sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
      if (visibili[0]) setCorrente(visibili[0].target.id);
    }, { rootMargin: '-130px 0px -60% 0px', threshold: 0 });
    sez.forEach((s) => io.observe(s));
    return () => io.disconnect();
  }, [glossario]);
  /* l'ancora nell'indirizzo: ci si arriva anche da un link condiviso */
  useEffect(() => {
    if (!hash) return;
    const el = document.getElementById(hash.slice(1));
    if (el) setTimeout(() => el.scrollIntoView({ behavior: 'smooth', block: 'start' }), 120);
  }, [hash, glossario]);

  const vai = (id) => {
    const el = document.getElementById(id);
    if (el) { el.scrollIntoView({ behavior: 'smooth', block: 'start' }); window.history.replaceState(window.history.state, '', `${pathname}#${id}`); setCorrente(id); }
  };
  const idx = PERCORSO.findIndex((p) => p.id === corrente);
  const prossimo = PERCORSO[idx + 1];

  return (
    <div className="fqz fondamenta" data-testid="fondamenta-page">
      <SoundTopbar firma="Sound" qui="/sound/impara" />
      <header>
        <div>
          <h1>Le <em>fondamenta</em></h1>
          <p className="esp-sub">Capire il suono prima di usarlo: sei capitoli brevi, poi il glossario.</p>
        </div>
      </header>
      <main>
        <SelettoreTre attiva="fondamenta" />
        <div className="capitoli" data-testid="fondamenta-capitoli">
          {!glossario && PERCORSO.map((p) => (
            <button key={p.id} type="button" className={`capitolo${corrente === p.id ? ' on' : ''}`} onClick={() => vai(p.id)} data-testid={`fondamenta-cap-${p.id}`}>{p.n} · {p.short}</button>
          ))}
          <Link to={glossario ? '/sound/impara' : '/sound/impara/glossario'} className={`capitolo${glossario ? ' on' : ''}`} data-testid="fondamenta-glossario">{glossario ? '← La guida' : 'Glossario'}</Link>
        </div>
        <GuidaView tab={glossario ? 'Glossario' : 'Guida'} onExplore={(chiave) => { const f = famigliaDaChiave(chiave); navigate(f ? `/sound/esplora?famiglia=${f.slug}` : '/sound/esplora'); }} onLearn={(l) => setLearn(l)} />
        {!glossario && prossimo && (
          <div className="prossimo"><button type="button" className="casa-cta" style={{ border: 0, cursor: 'pointer' }} onClick={() => vai(prossimo.id)} data-testid="fondamenta-prossimo">Capitolo {prossimo.n}: {prossimo.short} →</button></div>
        )}
      </main>
      <footer className="fqzfoot" data-testid="fqz-foot">
        <a href="/meditazioni">Le meditazioni</a><Link to="/sound/esplora">Le frequenze</Link><Link to="/sound/lab">Il Lab</Link><a href="/sound">Aurya Sound</a>
      </footer>
      {learn && (
        <div className="gate" onClick={() => setLearn(null)} data-testid="fondamenta-learn">
          <div className="gatebox" style={{ textAlign: 'left' }} onClick={(e) => e.stopPropagation()}>
            {(learn.title || learn.t) && <h2 style={{ marginTop: 0 }}>{learn.title || learn.t}</h2>}
            {(learn.body || learn.full) && <div className="howto" dangerouslySetInnerHTML={{ __html: learn.body || learn.full }} />}
            <div className="gatefoot" style={{ marginTop: 14 }}><button type="button" onClick={() => setLearn(null)}>Chiudi</button></div>
          </div>
        </div>
      )}
    </div>
  );
}
