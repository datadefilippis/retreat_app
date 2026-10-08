/**
 * PlaylistPage — LA PAGINA DI UNA PLAYLIST (SN1, 8/10/2026).
 * /meditazioni/playlist/:slug — copertina, titolo, racconto, quante
 * meditazioni e quanto durano, «Ascolta tutta» (parte dalla prima e il
 * player continua da solo), l'elenco in ordine. Stesso cancello del
 * catalogo: senza sblocco, la soglia del Cerchio.
 */
import React, { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import platformApi, { PLATFORM_TOKEN_KEY } from '../../../api/platformClient';
import { frequenciesAPI } from '../../../api/frequencies';
import { prova, migraVecchieChiavi } from '../../../lib/cerchio';
import useSeoMeta from '../../storefront/lib/useSeoMeta';
import SoundTopbar from '../SoundTopbar';
import { SafetyLine, SafetyCurtain } from '../SafetyCurtain';
import { SogliaCerchio } from '../MeditazioniPage';
import { INTENTI, fmtMin } from './MeditazioniCasa';
import Cuore, { InvitoAccount } from './Cuore';
import { usePreferite } from './preferite';
import { SOUND_LETTORE_IN_CASA } from '../stato';
import { LettoreProvider, useLettore } from './lettore';
import { LettoreBarra, SchedaMeditazione } from './LettoreBarra';
import '../frequenze.css';
import '../meditazioni.css';
import './casa.css';

/* MR3 — la playlist suona nella sua barra: «Ascolta tutta» e ogni riga */
export default function PlaylistPage() {
  return (
    <LettoreProvider>
      <PlaylistPageDentro />
    </LettoreProvider>
  );
}

function PlaylistPageDentro() {
  const { slug } = useParams();
  const L = useLettore();
  const suona = SOUND_LETTORE_IN_CASA && L ? (t, pl) => L.avvia(t, { da: 'playlist', playlist: pl }) : null;
  const hasAccount = !!localStorage.getItem(PLATFORM_TOKEN_KEY);
  const [p, setP] = useState(null);
  const [stato, setStato] = useState('loading');   // loading | ok | locked | notfound
  const [safety, setSafety] = useState(false);
  const pref = usePreferite();   // MR2 — il cuore sulla playlist e su ogni riga

  const carica = async () => {
    try {
      const r = hasAccount ? await platformApi.get(`/frequencies/playlists/${slug}`) : await frequenciesAPI.playlists.pubblica(slug, prova());
      setP(r.data); setStato('ok');
    } catch (e) {
      const st = e?.response?.status;
      setStato(st === 403 ? 'locked' : 'notfound');
    }
  };
  useEffect(() => { migraVecchieChiavi().finally(carica); }, [slug]); // eslint-disable-line react-hooks/exhaustive-deps

  useSeoMeta({
    title: p ? `${p.title} · Playlist | Aurya Sound` : 'Playlist | Aurya Sound',
    description: p?.description || 'Una raccolta di meditazioni di Aurya Sound.',
    image: p?.cover_url || undefined,
    canonicalPath: `/meditazioni/playlist/${slug}`,
  });

  if (stato === 'locked') return <SogliaCerchio teaserCount={0} onSbloccato={carica} />;
  if (stato === 'notfound') {
    return (
      <div className="fqz med casa"><SoundTopbar firma="Meditazioni" qui="/meditazioni" />
        <main style={{ paddingTop: 60, textAlign: 'center' }}><h1>Questa playlist non c'è più.</h1>
          <p className="soundlead" style={{ marginTop: 10 }}><Link to="/meditazioni" style={{ color: 'var(--water)' }}>Torna alle meditazioni</Link></p></main></div>
    );
  }
  if (!p) return <div className="fqz med casa"><SoundTopbar firma="Meditazioni" qui="/meditazioni" /></div>;

  const prima = p.tracce[0];
  return (
    <div className={`fqz med casa${L?.traccia ? ' con-lettore' : ''}`} data-testid="casa-playlist">
      <SoundTopbar firma="Meditazioni" qui="/meditazioni" />
      <main>
        <p style={{ margin: '6px 0 14px' }}><Link to="/meditazioni" style={{ color: 'var(--dimmer)', textDecoration: 'none', fontSize: 13 }}>← Le meditazioni</Link></p>
        <div className="pl-testa">
          <div className="pl-cover" style={{ position: 'relative' }}>{p.cover_url && <img src={p.cover_url} alt="" />}
            <Cuore on={pref.isFavPlaylist(p.slug)} onClick={() => pref.togglePlaylist(p.slug)} titolo={p.title} testid="playlist-cuore" />
          </div>
          <div>
            <span className="etichetta">Playlist{p.accesso === 'piu' ? ' · Più' : ''}</span>
            <h1 style={{ marginTop: 6 }}>{p.title}</h1>
            <p className="soundlead" style={{ marginTop: 6 }}>{p.tracce_count} {p.tracce_count === 1 ? 'meditazione' : 'meditazioni'} · {fmtMin(p.duration_sec)}</p>
            {p.description && <p style={{ color: 'var(--dim)', marginTop: 10, maxWidth: 560 }}>{p.description}</p>}
            {prima && (
              <p style={{ marginTop: 16 }}>
                {suona
                  ? <button type="button" className="casa-cta" style={{ border: 0, cursor: 'pointer' }} data-testid="casa-playlist-ascolta" onClick={() => suona(prima, p)}>▶ Ascolta tutta</button>
                  : <Link to={`/frequenze/${prima.slug}?da=playlist&playlist=${encodeURIComponent(p.slug)}`} className="casa-cta" data-testid="casa-playlist-ascolta">▶ Ascolta tutta</Link>}
              </p>
            )}
          </div>
        </div>
        <ol className="pl-lista" data-testid="casa-playlist-lista">
          {p.tracce.map((t, i) => (
            <li key={t.id}>
              <span className="n">{String(i + 1).padStart(2, '0')}</span>
              <span className="pl-mini">{t.cover_url && <img src={t.cover_url} alt="" loading="lazy" />}</span>
              <span className="t"><b>{t.title}</b><span>{t.intent ? `${INTENTI[t.intent] || t.intent} · ` : ''}{fmtMin(t.duration_sec)}{t.has_voce ? ' · con la voce' : ''}{t.accesso === 'piu' ? ' · Più' : ''}</span></span>
              <Cuore variante="riga" on={pref.isFav(t.slug)} onClick={() => pref.toggle(t.slug)} titolo={t.title} testid="playlist-riga-cuore" />
              {suona
                ? <button type="button" className="med-ascolta" style={{ cursor: 'pointer' }} data-testid="playlist-riga-ascolta" onClick={() => suona(t, p)}>{L?.traccia?.slug === t.slug && L.playing ? '⏸ In ascolto' : 'Ascolta'}</button>
                : <Link to={`/frequenze/${t.slug}?da=playlist&playlist=${encodeURIComponent(p.slug)}`} className="med-ascolta">Ascolta</Link>}
            </li>
          ))}
        </ol>
        <div style={{ marginTop: 28 }}><SafetyLine onOpen={() => setSafety(true)} /></div>
      </main>
      <footer className="fqzfoot" data-testid="fqz-foot">
        <a href="/">← Torna su Aurya</a><a href="/meditazioni">Le meditazioni</a><a href="/sound">Il suono</a><a href="/newsletter">Il Cerchio</a>
      </footer>
      {safety && <SafetyCurtain mode="review" onClose={() => setSafety(false)} />}
      <InvitoAccount aperto={pref.chiediAccount} onChiudi={() => pref.setChiediAccount(false)} ritorno={`/meditazioni/playlist/${slug}`} />
      <LettoreBarra />
      <SchedaMeditazione />
      {L?.curtain}
    </div>
  );
}
