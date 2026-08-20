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
import { resolveAudioLayers, resolveVoiceLayers } from './engine/assets';
import { SafetyLine, useSafetyGate } from './SafetyCurtain';
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
  /* SF — questa è la pagina che l'operatore condivide: chi la apre non
     ha mai visto Aurya, quindi il sipario deve stare davanti al primo
     suono anche qui (il gate qui sotto è un'altra cosa: l'anteprima). */
  const { guard, curtain, openReview } = useSafetyGate();
  const [unlocked, setUnlocked] = useState(() =>
    localStorage.getItem(UNLOCK_KEY) === '1'
    || !!localStorage.getItem('platform_token')
    || !!localStorage.getItem('fqz_catalog_unlock'));
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
    // FV4 — la voce dell'operatore: gli URL arrivano col payload pubblico
    let voiceLayers = [];
    if ((track.score.layers || []).some((l) => l.kind === 'voice')) {
      setLoadingAudio(true);
      const voiceById = Object.fromEntries(
        (track.voice_assets || []).map((v) => [v.id, v]));
      voiceLayers = await resolveVoiceLayers(ctx, track.score, voiceById);
      setLoadingAudio(false);
    }
    if (!playedRef.current) {
      playedRef.current = true;
      frequenciesAPI.registerPlay(slug).catch(() => { /* solo un contatore */ });
    }
    const startedAt = fromT;
    liveRef.current = startPreview(ctx, track.score,
      { fromT, audioLayers, voiceLayers,
        voiceDuck: !!track.score.voice_duck });
    setPlaying(true);
    timerRef.current = setInterval(() => {
      const el = startedAt + (liveRef.current ? liveRef.current.elapsed() - startedAt : 0);
      const cur = liveRef.current ? liveRef.current.elapsed() : 0;
      if (cur >= track.score.duration_sec) { stop(); setElapsed(0); return; }
      setElapsed(Math.max(0, cur));
      if (!unlocked && cur >= PREVIEW_SEC) { stop(); setGateOpen(true); }
    }, 200);
  };
  const playGuarded = guard(play);

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
      try {
        const u = await frequenciesAPI.catalogUnlock(email);
        localStorage.setItem('fqz_catalog_unlock', JSON.stringify(u.data));
      } catch { /* la vetrina richiedera' l'email */ }
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
          <h1>Aurya <em>Sound</em></h1>
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
      {/* MD (20/8) — chi arriva da un link condiviso restava chiuso
          qui dentro: il menu del sito non c'e' e il design e' un altro
          mondo. Stesso rimedio di Aurya Sound (SP-ter): marchio in
          alto a sinistra e uscite in fondo. */}
      <div className="topbar">
        <a className="fqzbrand" href="/" data-testid="fqz-brand" title="Torna su Aurya">
          <img src="/logo-aurya-512.png" alt="" width="26" height="26" />
          <span>
            <b>Aurya</b>
            <i>torna al sito</i>
          </span>
        </a>
      </div>
      <header>
        <div>
          <h1>Aurya <em>Sound</em></h1>
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

          <SafetyLine onOpen={openReview} />
          <div className="createbar" style={{ position: 'static', marginTop: 16 }}>
            <button type="button" className="cb-play" data-testid="fqp-play"
              onClick={() => (playing ? stop() : playGuarded(elapsed >= d - 1 ? 0 : elapsed))}>
              {loadingAudio ? <><span className="prep">◌</span> Preparo…</>
                : playing ? `⏸ ${fmt(elapsed)}` : elapsed > 0 ? '▶ Riprendi' : '▶ Ascolta'}
            </button>
            <div className="seekwrap" style={{ display: 'flex' }}>
              <span className="seek-cur">{fmt(elapsed)}</span>
              {/* MD (20/8) — la barra era solo decorativa: nessun
                  gestore, quindi il cursore non si poteva spostare.
                  Ora si clicca (e si trascina col dito), rispettando
                  le due regole della pagina: le controindicazioni
                  passano dal sipario (playGuarded) e senza sblocco non
                  si va oltre l'anteprima. */}
              <div className="seekbar" title="Clicca per spostarti nella meditazione"
                style={{ cursor: 'pointer' }}
                data-testid="fqp-seekbar"
                onClick={(e) => {
                  const r = e.currentTarget.getBoundingClientRect();
                  const frazione = Math.max(0, Math.min(1, (e.clientX - r.left) / r.width));
                  let t = frazione * d;
                  if (!unlocked) t = Math.min(t, PREVIEW_SEC - 1);
                  setElapsed(t);
                  playGuarded(t);
                }}>
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

          <p style={{ marginTop: 14 }}>
            <Link to="/meditazioni" className="readmore"
              style={{ textDecoration: 'none', display: 'inline-block' }}>
              Tutte le meditazioni di Aurya →
            </Link>
          </p>
          {/* SF — l'avviso sta PRIMA del pulsante, non in fondo alla
              pagina: chi arriva da un link condiviso preme ▶ e basta. */}
        </section>
      </main>

      <footer className="fqzfoot" data-testid="fqz-foot">
        <a href="/">← Torna su Aurya</a>
        <a href="/meditazioni">Tutte le meditazioni</a>
        <a href="/sound">Aurya Sound</a>
        <a href="/blog">Magazine</a>
      </footer>
      {curtain}
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
              <a href={`/accedi?vista=crea&next=/frequenze/${slug}${email ? `&email=${encodeURIComponent(email)}` : ''}`}
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
