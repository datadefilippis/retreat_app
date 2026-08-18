/**
 * Frequenze by Aurya — pagina pubblica di ascolto (FQ1, 18/8/2026).
 *
 * /frequenze/:slug — il player risintetizza la RICETTA col motore
 * (stesso engine del compositore): niente file audio da servire.
 * Stesso mondo visivo del compositore (frequenze.css, .fqz).
 *
 * CANCELLO (soft-wall, non DRM: il contenuto e' gratuito, il gate e'
 * la cattura del contatto): anteprima libera di 90 secondi, poi
 * l'ascolto completo chiede l'iscrizione alla Lettera o un account
 * Aurya (platform_token gia' in sessione sblocca da solo).
 */
import React, { useEffect, useRef, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import api from '../../api/client';
import { frequenciesAPI } from '../../api/frequencies';
import { startPreview } from './engine/synth';
import { resolveAudioLayers } from './engine/assets';
import './frequenze.css';

const PREVIEW_SEC = 90;
const UNLOCK_KEY = 'fqz_listener_ok';
const INTENTS = {
  dormire: 'Dormire', meditare: 'Meditare', rilassare: 'Rilassare',
  concentrare: 'Concentrare', elaborare: 'Elaborare', energizzare: 'Energizzare',
};
const fmt = (s) => {
  s = Math.max(0, Math.round(s));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
};

export default function PublicFrequencyPage() {
  const { slug } = useParams();
  const [track, setTrack] = useState(null);
  const [notFound, setNotFound] = useState(false);
  const [playing, setPlaying] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [loadingAudio, setLoadingAudio] = useState(false);
  const [gateOpen, setGateOpen] = useState(false);
  const [unlocked, setUnlocked] = useState(() =>
    localStorage.getItem(UNLOCK_KEY) === '1' || !!localStorage.getItem('platform_token'));
  const [email, setEmail] = useState('');
  const [consent, setConsent] = useState(false);
  const [subscribing, setSubscribing] = useState(false);
  const [gateMsg, setGateMsg] = useState('');

  const ctxRef = useRef(null);
  const liveRef = useRef(null);
  const timerRef = useRef(null);
  const soundsRef = useRef({});
  const playedRef = useRef(false);

  useEffect(() => {
    frequenciesAPI.getPublic(slug)
      .then((r) => setTrack(r.data))
      .catch(() => setNotFound(true));
    frequenciesAPI.listSounds()
      .then((r) => {
        soundsRef.current = Object.fromEntries(
          (r.data.items || []).map((s) => [s.id, s]));
      })
      .catch(() => { /* la sessione suona senza basi */ });
  }, [slug]);

  const stop = () => {
    if (liveRef.current) { liveRef.current.stop(); liveRef.current = null; }
    if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null; }
    setPlaying(false);
  };
  useEffect(() => () => stop(), []);

  const play = async (fromT = 0) => {
    stop();
    if (!track) return;
    ctxRef.current = ctxRef.current || new (window.AudioContext || window.webkitAudioContext)();
    const ctx = ctxRef.current;
    await ctx.resume();
    let audioLayers = [];
    if ((track.score.layers || []).some((l) => l.kind === 'audio')) {
      setLoadingAudio(true);
      audioLayers = await resolveAudioLayers(ctx, track.score, soundsRef.current);
      setLoadingAudio(false);
    }
    if (!playedRef.current) {
      playedRef.current = true;
      frequenciesAPI.registerPlay(slug).catch(() => { /* solo un contatore */ });
    }
    const startedAt = fromT;
    liveRef.current = startPreview(ctx, track.score, { fromT, audioLayers });
    setPlaying(true);
    timerRef.current = setInterval(() => {
      const el = startedAt + (liveRef.current ? liveRef.current.elapsed() - startedAt : 0);
      const cur = liveRef.current ? liveRef.current.elapsed() : 0;
      if (cur >= track.score.duration_sec) { stop(); setElapsed(0); return; }
      setElapsed(Math.max(0, cur));
      if (!unlocked && cur >= PREVIEW_SEC) { stop(); setGateOpen(true); }
    }, 200);
  };

  const subscribe = async (e) => {
    e.preventDefault();
    if (!consent) { setGateMsg('Serve il consenso alla Lettera'); return; }
    setSubscribing(true);
    setGateMsg('');
    try {
      await api.post('/public/newsletter/subscribe', {
        email, consent: true, language: 'it',
        source: `frequenze:${slug}`, wants_experiences: true,
      });
      localStorage.setItem(UNLOCK_KEY, '1');
      setUnlocked(true);
      setGateOpen(false);
      setGateMsg('');
      play(0);
    } catch (err) {
      setGateMsg(err?.response?.data?.detail || 'Iscrizione non riuscita, riprova');
    } finally { setSubscribing(false); }
  };

  if (notFound) {
    return (
      <div className="fqz">
        <main style={{ paddingTop: 60, textAlign: 'center' }}>
          <h1>Aurya <em>Frequenze</em></h1>
          <p className="soundlead" style={{ marginTop: 18 }}>
            Questa traccia non è in ascolto pubblico.
          </p>
          <p><Link to="/" className="readmore" style={{ textDecoration: 'none' }}>Vai su Aurya</Link></p>
        </main>
      </div>
    );
  }
  if (!track) return <div className="fqz" style={{ minHeight: '100vh' }} />;

  const d = track.score.duration_sec;
  const frac = Math.min(1, elapsed / d);

  return (
    <div className="fqz" data-testid="fqz-public">
      <header>
        <div>
          <h1>Aurya <em>Frequenze</em></h1>
          <div className="sub">sessione vibrazionale</div>
        </div>
      </header>
      <main style={{ maxWidth: 720 }}>
        <section className="bib">
          {track.intent && <div className="learn-kicker">{INTENTS[track.intent] || track.intent}</div>}
          <h2 style={{ fontSize: 27 }}>{track.title}</h2>
          {track.operator?.name && (
            <p>composta da{' '}
              {track.operator.slug ? (
                <Link to={`/o/${track.operator.slug}`}
                  style={{ color: 'var(--water)' }}>{track.operator.name}</Link>
              ) : <b>{track.operator.name}</b>}
              {' '}· {Math.round(d / 60)} min
            </p>
          )}
          {track.description && <p>{track.description}</p>}

          <div className="createbar" style={{ position: 'static', marginTop: 16 }}>
            <button type="button" className="cb-play" data-testid="fqp-play"
              onClick={() => (playing ? stop() : play(elapsed >= d - 1 ? 0 : elapsed))}>
              {loadingAudio ? 'Preparo…' : playing ? `⏸ ${fmt(elapsed)}` : elapsed > 0 ? '▶ Riprendi' : '▶ Ascolta'}
            </button>
            <div className="seekwrap" style={{ display: 'flex' }}>
              <span className="seek-cur">{fmt(elapsed)}</span>
              <div className="seekbar">
                <div className="seek-fill" style={{ width: `${frac * 100}%` }} />
                <div className="seek-knob" style={{ left: `${frac * 100}%` }} />
              </div>
              <span className="seek-tot">{fmt(d)}</span>
            </div>
          </div>

          {(track.score.phases || []).length > 0 && (
            <div className="legend" style={{ marginTop: 14 }}>
              {track.score.phases.map((p, i) => (
                <span key={i}><b style={{ width: 'auto', padding: '0 6px', borderRadius: 999 }}>{fmt(p.t)}</b> {p.name}</span>
              ))}
            </div>
          )}

          <p className="note" style={{ marginTop: 16 }}>
            🎧 Le componenti binaurali funzionano solo in cuffia. Volume
            moderato. Non è un dispositivo medico e non sostituisce percorsi
            clinici; non usare in caso di epilessia, con pacemaker, alla
            guida. In caso di disagio, interrompere l'ascolto.
          </p>
        </section>
      </main>

      {gateOpen && !unlocked && (
        <div className="gate">
          <div className="gatebox" style={{ maxWidth: 520 }}>
            <h2>Continua l'ascolto</h2>
            <p>
              I primi {PREVIEW_SEC} secondi sono liberi. Per ascoltare tutta la
              sessione iscriviti alla <b>Lettera di Aurya</b> — pratiche,
              ritiri e nuove tracce, senza rumore — oppure entra col tuo
              account.
            </p>
            <form onSubmit={subscribe}>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                <input type="email" required value={email}
                  placeholder="la tua email"
                  onChange={(e) => setEmail(e.target.value)}
                  style={{ flex: 1, minWidth: 200 }} />
                <button type="submit" className="primary" disabled={subscribing}>
                  {subscribing ? 'Un attimo…' : 'Iscriviti e ascolta'}
                </button>
              </div>
              <label style={{ display: 'flex', gap: 8, alignItems: 'flex-start',
                              fontSize: 12, color: 'var(--dim)', marginTop: 10, cursor: 'pointer' }}>
                <input type="checkbox" checked={consent}
                  onChange={(e) => setConsent(e.target.checked)} />
                <span>Acconsento a ricevere la Lettera di Aurya. Confermerai
                  dall'email che ti arriva; disiscrizione in un click.
                  {' '}<a href="/privacy" target="_blank" rel="noreferrer"
                    style={{ color: 'var(--water)' }}>Privacy</a></span>
              </label>
            </form>
            {gateMsg && <p style={{ color: 'var(--alert)', fontSize: 12, marginTop: 8 }}>{gateMsg}</p>}
            <p style={{ fontSize: 12.5, color: 'var(--dim)', marginTop: 14 }}>
              Hai un account Aurya?{' '}
              <a href={`/account/accedi?next=/frequenze/${slug}`}
                style={{ color: 'var(--water)' }}>Accedi</a>
              {' '}· oppure{' '}
              <button type="button" className="ghost" style={{ padding: 0, color: 'var(--dim)', textDecoration: 'underline' }}
                onClick={() => setGateOpen(false)}>riascolta l'anteprima</button>
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
