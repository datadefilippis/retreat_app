/**
 * LettoreBarra — MR3: la barra fissa in basso che suona dove sei, il foglio
 * del cancello (a 90 s senza Cerchio) e il foglio di dettaglio della
 * meditazione (copertina grande, racconto, cuore, Ascolta, Apri la pagina).
 */
import React from 'react';
import { Link } from 'react-router-dom';
import SeekBar from '../SeekBar';
import CancelloLettera from '../CancelloLettera';
import Cuore from './Cuore';
import { usePreferite } from './preferite';
import { useLettore } from './lettore';
import { INTENTI, fmtMin, fmtMinSec } from './MeditazioniCasa';

const Ico = ({ d }) => (<svg viewBox="0 0 24 24" aria-hidden="true"><path d={d} /></svg>);
const ICO = {
  play: 'M8 5v14l11-7z', pausa: 'M7 5h4v14H7zM13 5h4v14h-4z',
  prev: 'M6 5h2v14H6zM19 5l-10 7 10 7z', next: 'M16 5h2v14h-2zM5 5l10 7-10 7z', chiudi: 'M6 6l12 12M18 6L6 18',
};

export function LettoreBarra() {
  const L = useLettore();
  const pref = usePreferite();
  if (!L || !L.traccia) return null;
  const t = L.traccia;
  const d = L.unlocked ? (t.score?.duration_sec || t.duration_sec || 0) : Math.min(90, t.score?.duration_sec || t.duration_sec || 90);
  const guida = t.guida_nome || t.operator?.name || '';
  return (
    <>
      <div className="lettore" data-testid="lettore-barra" role="region" aria-label="In ascolto">
        <div className="lettore-cover">{t.cover_url && <img src={t.cover_url} alt="" />}</div>
        <div className="lettore-testo">
          <button type="button" className="lettore-titolo" onClick={() => L.apriScheda(t)} title="Apri la scheda">{t.title}</button>
          <span className="lettore-meta">
            {guida}{L.playlist && L.posizione >= 0 ? ` · ${L.posizione + 1} di ${L.playlist.tracce.length}` : ''}{!L.unlocked ? ' · anteprima 90 s' : ''}
          </span>
          <SeekBar cur={L.elapsed} tot={d} fmt={fmtMinSec} testid="lettore-seek" titolo="Spostati nella meditazione" onCommit={(sec) => L.seek(sec)} />
        </div>
        <div className="lettore-gesti">
          {L.playlist && <button type="button" className="lettore-g" onClick={L.precedente} disabled={L.posizione <= 0} aria-label="Precedente" data-testid="lettore-prev"><Ico d={ICO.prev} /></button>}
          <button type="button" className="lettore-g lettore-play" onClick={L.toggle} aria-label={L.playing ? 'Pausa' : 'Ascolta'} data-testid="lettore-play">
            {L.caricamento ? <span className="lettore-spin">◌</span> : <Ico d={L.playing ? ICO.pausa : ICO.play} />}
          </button>
          {L.playlist && <button type="button" className="lettore-g" onClick={L.prossima} disabled={L.posizione < 0 || L.posizione >= L.playlist.tracce.length - 1} aria-label="Successiva" data-testid="lettore-next"><Ico d={ICO.next} /></button>}
          <Cuore variante="riga" on={pref.isFav(t.slug)} onClick={() => pref.toggle(t.slug)} titolo={t.title} testid="lettore-cuore" />
          <button type="button" className="lettore-g lettore-chiudi" onClick={L.chiudi} aria-label="Chiudi" data-testid="lettore-chiudi"><Ico d={ICO.chiudi} /></button>
        </div>
      </div>

      {/* il cancello, a 90 s senza Cerchio: lo stesso di sempre, nel foglio */}
      {L.cancello && !L.unlocked && (
        <div className="gate" data-testid="lettore-cancello">
          <div className="gatebox" style={{ maxWidth: 520 }}>
            <CancelloLettera slug={t.slug} durataSec={t.score?.duration_sec} cover={t.cover_url} titolo={t.title} playlist={L.playlist}
              onSbloccato={L.sbloccaERiparti}>
              <p style={{ fontSize: 12.5, color: 'var(--dim)', marginTop: 8 }}>
                Oppure{' '}
                <button type="button" className="ghost" style={{ padding: 0, color: 'var(--dim)', textDecoration: 'underline' }}
                  onClick={() => { L.setCancello(false); L.seek(0); L.toggle(); }}>riascolta l'anteprima</button>
                {' '}· <button type="button" className="ghost" style={{ padding: 0, color: 'var(--dim)', textDecoration: 'underline' }} onClick={() => L.setCancello(false)}>chiudi</button>
              </p>
            </CancelloLettera>
          </div>
        </div>
      )}
    </>
  );
}

/** il foglio di dettaglio: si legge qui, si ascolta qui; la pagina intera resta per chi la vuole */
export function SchedaMeditazione() {
  const L = useLettore();
  const pref = usePreferite();
  if (!L || !L.scheda) return null;
  const t = L.scheda;
  const guida = t.guida_nome || t.operator?.name || '';
  const copia = async () => { try { await navigator.clipboard.writeText(`${window.location.origin}/frequenze/${t.slug}`); } catch { /* niente */ } };
  return (
    <div className="gate" onClick={L.chiudiScheda} data-testid="scheda-meditazione">
      <div className="gatebox scheda" onClick={(e) => e.stopPropagation()}>
        <div className="scheda-cover">{t.cover_url && <img src={t.cover_url} alt="" />}
          <Cuore on={pref.isFav(t.slug)} onClick={() => pref.toggle(t.slug)} titolo={t.title} testid="scheda-cuore" />
        </div>
        <div className="scheda-corpo">
          <span className="etichetta">{t.intent ? INTENTI[t.intent] || t.intent : 'Meditazione'}{t.has_voce ? ' · con la voce' : ''}</span>
          <h2>{t.title}</h2>
          <p className="scheda-meta">{guida}{guida ? ' · ' : ''}{fmtMin(t.duration_sec || t.score?.duration_sec)}</p>
          {t.description && <p className="scheda-testo">{t.description}</p>}
          <div className="scheda-gesti">
            <button type="button" className="primary" data-testid="scheda-ascolta" onClick={() => { L.chiudiScheda(); L.avvia(t, { da: 'scheda' }); }}>▶ Ascolta</button>
            <button type="button" onClick={copia} title="Copia il link della meditazione">Condividi</button>
            <Link to={`/frequenze/${t.slug}?da=scheda`} className="scheda-link">Apri la pagina</Link>
            <button type="button" className="ghost" onClick={L.chiudiScheda}>Chiudi</button>
          </div>
        </div>
      </div>
    </div>
  );
}
