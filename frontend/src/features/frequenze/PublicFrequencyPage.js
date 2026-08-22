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
import { frequenciesAPI } from '../../api/frequencies';
import { startPreview } from './engine/synth';
import { resolveAudioLayers, resolveVoiceLayers } from './engine/assets';
import { avvisoCuffieScore } from './engine/altoparlante';
import { schermoAcceso, schermoLibero, sorvegliaContesto } from './engine/veglia';
import {
  preparaContinuo, continuoDisponibile, continuoSupportato,
} from './engine/continuo';
import { SafetyLine, useSafetyGate } from './SafetyCurtain';
import { creaAccount, entraInAurya } from '../../utils/authLinks';
import { prova, sblocca, iscriviESblocca, migraVecchieChiavi } from '../../lib/cerchio';
import './frequenze.css';
import SoundTopbar from './SoundTopbar';
import SeekBar from './SeekBar';
import AuryaMode from './visual/AuryaMode';
import { creaLettore } from './visual/analisi';
import { creaPonte } from './engine/ponte';

const PREVIEW_SEC = 90;
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
  /* SB1/SB4 (20/8) — apre la PROVA UNICA del cerchio (o l'account),
     non piu' un flag locale scritto al solo subscribe: quel flag
     faceva ascoltare la traccia intera a chiunque digitasse un
     indirizzo qualsiasi, senza conferma. */
  const [unlocked, setUnlocked] = useState(() =>
    !!prova() || !!localStorage.getItem('platform_token'));
  const [attesaConferma, setAttesaConferma] = useState(false);
  const [email, setEmail] = useState('');
  const [consent, setConsent] = useState(false);
  const [subscribing, setSubscribing] = useState(false);
  const [gateMsg, setGateMsg] = useState('');

  const ctxRef = useRef(null);
  const liveRef = useRef(null);
  const timerRef = useRef(null);
  const soundsRef = useRef({});
  const playedRef = useRef(false);
  /* AT3 — ascolto continuo: il lettore <audio> preparato (sopravvive
     al blocco schermo), il progresso del render, il flag per la UI */
  const contRef = useRef(null);
  const [contProg, setContProg] = useState(null);
  const [continuo, setContinuo] = useState(false);
  const [contErrore, setContErrore] = useState('');
  /* AV1 — Aurya Mode: si chiede, non parte da solo. Il lettore si
     innesta nel grafo UNA volta e resta li'; la tela puo' andare e
     venire senza toccare il suono. */
  const [guarda, setGuarda] = useState(false);
  const [lettore, setLettore] = useState(null);
  const lettoreRef = useRef(null);

  useEffect(() => {
    // SB1 — vecchie chiavi HMAC → prova unica (poi si ricontrolla)
    migraVecchieChiavi().then(() => { if (prova()) setUnlocked(true); });
    frequenciesAPI.getPublic(slug)
      .then((r) => setTrack(r.data))
      .catch(() => setNotFound(true));
    frequenciesAPI.listSounds()
      .then((r) => {
        soundsRef.current = Object.fromEntries(
          (r.data.items || []).map((s) => [s.id, s]));
      })
      .catch(() => { /* la sessione suona senza basi */ });
    /* AT3 — cambio di traccia SENZA smontaggio (da /frequenze/a a
       /frequenze/b il componente resta vivo): il file preparato e'
       quello della traccia di prima — lasciarlo in piedi farebbe
       suonare A dentro la pagina di B. Si butta via tutto e si
       riparte, come per elapsed e per il contatore d'ascolto. */
    return () => {
      if (liveRef.current) { liveRef.current.stop(); liveRef.current = null; }
      if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null; }
      if (contRef.current) { contRef.current.dispose(); contRef.current = null; }
      setContinuo(false);
      setContProg(null);
      setPlaying(false);
      setElapsed(0);
      playedRef.current = false;
    };
  }, [slug]);

  const stopRef = useRef(() => {});
  const stop = () => {
    if (liveRef.current) { liveRef.current.stop(); liveRef.current = null; }
    if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null; }
    if (contRef.current) contRef.current.pause();   // il suo onPause fa il resto
    /* la pausa del ponte, ritardata: via la vibrazione iOS (v. Crea) */
    ctxRef.current?._fqzPonte?.rilascia?.();
    setPlaying(false);
  };
  stopRef.current = stop;
  useEffect(() => () => {
    stop();
    // AT3 — il file renderizzato non deve sopravvivere alla pagina
    if (contRef.current) { contRef.current.dispose(); contRef.current = null; }
  }, []);   // eslint-disable-line react-hooks/exhaustive-deps

  /* AT2 — finche' suona il motore dal vivo, lo schermo non si spegne
     da solo. In modalita' continua non serve: li' l'audio sopravvive
     al blocco, che e' proprio lo scopo. */
  useEffect(() => {
    if (playing && !continuo) { schermoAcceso(); return schermoLibero; }
    return undefined;
  }, [playing, continuo]);

  const segnaAscolto = () => {
    if (playedRef.current) return;
    playedRef.current = true;
    frequenciesAPI.registerPlay(slug).catch(() => { /* solo un contatore */ });
  };

  /* Basi e voce: le stesse per l'ascolto dal vivo e per il render
     continuo — un solo caricamento, non due percorsi che divergono. */
  const caricaLayers = async (ctx) => {
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
    return { audioLayers, voiceLayers };
  };

  const play = async (fromT = 0) => {
    stop();
    if (!track) return;
    // AT3 — a lettore pronto si comanda LUI: partenza immediata, e il
    // suono continua anche a schermo bloccato
    if (contRef.current) {
      segnaAscolto();
      contRef.current.seek(fromT);
      contRef.current.play();
      return;
    }
    if (!ctxRef.current) {
      ctxRef.current = new (window.AudioContext || window.webkitAudioContext)();
      sorvegliaContesto(ctxRef.current, () => stopRef.current());
    }
    const ctx = ctxRef.current;
    /* il canale-musica: parte nel gesto (vedi engine/ponte.js) */
    const ponte = creaPonte(ctx);
    ponte.avvia();
    if (!lettoreRef.current) {
      // l'analizzatore OSSERVA il suono da un ramo parallelo (vedi
      // synth.js): l'altoparlante resta collegato direttamente, e la
      // strada del suono e' identica a quella di sempre
      const l = creaLettore(ctx);
      lettoreRef.current = l;
      setLettore(l);
    }
    await ctx.resume();
    const { audioLayers, voiceLayers } = await caricaLayers(ctx);
    segnaAscolto();
    liveRef.current = startPreview(ctx, track.score,
      { fromT, audioLayers, voiceLayers,
        voiceDuck: !!track.score.voice_duck,
        sbocco: ctx._fqzPonte?.nodo,
        uscita: lettoreRef.current?.analyser });
    setPlaying(true);
    timerRef.current = setInterval(() => {
      const cur = liveRef.current ? liveRef.current.elapsed() : 0;
      if (cur >= track.score.duration_sec) { stop(); setElapsed(0); return; }
      setElapsed(Math.max(0, cur));
      if (!unlocked && cur >= PREVIEW_SEC) { stop(); setGateOpen(true); }
    }, 200);
  };
  const playGuarded = guard(play);

  /* AT3 — la preparazione: renderizza la sessione in un file e
     accende il lettore. Passa dal sipario come ogni altra via al
     suono, e la pagina la offre solo a sblocco avvenuto: un file
     intero in mano all'anteprima sarebbe il cancello demolito. */
  const preparaGuarded = guard(async (fromT = 0) => {
    if (!track || contRef.current || contProg != null) return;
    stop();
    setContProg(0);
    setContErrore('');
    try {
      ctxRef.current = ctxRef.current || new (window.AudioContext || window.webkitAudioContext)();
      const { audioLayers, voiceLayers } = await caricaLayers(ctxRef.current);
      const h = await preparaContinuo({
        score: track.score, audioLayers, voiceLayers,
        voiceDuck: !!track.score.voice_duck,
        titolo: track.title, autore: track.operator?.name,
        onProgress: (p) => setContProg(p),
      }, {
        onPlay: () => setPlaying(true),
        onPause: () => setPlaying(false),
        onEnd: () => { setPlaying(false); setElapsed(0); },
        onTime: (t) => setElapsed(t),
      });
      contRef.current = h;
      setContinuo(true);
      segnaAscolto();
      h.seek(fromT);
      h.play();
    } catch (err) {
      /* Un fallimento QUI non deve essere muto: la pagina resta
         identica a prima e l'utente crede di aver premuto a vuoto.
         (Successo davvero: un refactor ha rotto questo percorso e il
         catch silenzioso me l'ha nascosto.) */
      console.error('[continuo] preparazione fallita:', err);   // eslint-disable-line no-console
      setGateMsg('');
      setContErrore("Non sono riuscito a preparare l'ascolto continuo. L'ascolto normale funziona.");
    } finally { setContProg(null); }
  });

  const subscribe = async (e) => {
    e.preventDefault();
    if (!consent) { setGateMsg('Serve il consenso alla Lettera'); return; }
    setSubscribing(true);
    setGateMsg('');
    try {
      const esito = await iscriviESblocca({
        email, source: `frequenze:${slug}`, returnTo: `/frequenze/${slug}`,
      });
      if (esito === 'sbloccato') {
        setUnlocked(true);
        setGateOpen(false);
        setGateMsg('');
        play(0);
      } else {
        // prima iscrizione: la traccia intera si apre col click
        // nell'email — che riporta QUI (SB3)
        setAttesaConferma(true);
      }
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
  const avvisoTelefono = avvisoCuffieScore(track.score);
  const continuoPossibile = unlocked && continuoSupportato()
    && continuoDisponibile(track.score);

  return (
    <div className="fqz" data-testid="fqz-public">
      {/* MD (20/8) — chi arriva da un link condiviso restava chiuso
          qui dentro: il menu del sito non c'e' e il design e' un altro
          mondo. Stesso rimedio di Aurya Sound (SP-ter): marchio in
          alto a sinistra e uscite in fondo. */}
      <SoundTopbar firma="Sound" />
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

          {/* AV1 — Aurya Mode. Si accende con un gesto (mai da sola:
              disegnare consuma) e vive solo mentre il motore suona dal
              vivo: in ascolto continuo il suono esce da un <audio>, e
              su iOS portarlo dentro WebAudio lo rimetterebbe sotto il
              tasto silenzioso. Del resto guardare e ascoltare a
              schermo bloccato si escludono a vicenda. */}
          {guarda && lettore && !continuo && (
            <AuryaMode lettore={lettore} attivo={playing || elapsed > 0}
              altezza={300}
              /* VC1 — la scena e' dell'AUTORE (decisione founder): se
                 l'ha scelta in Crea viaggia nella ricetta e chi
                 ascolta vede quella; senza, l'ambiente di default */
              visual={track.score?.visual || null} />
          )}
          <SafetyLine onOpen={openReview} />
          <div className="createbar" style={{ position: 'static', marginTop: 16 }}>
            <button type="button" className={`cb-play${playing ? ' suona' : ''}`} data-testid="fqp-play"
              onClick={() => (playing ? stop() : playGuarded(elapsed >= d - 1 ? 0 : elapsed))}>
              {loadingAudio ? <><span className="prep">◌</span> Preparo…</>
                : playing ? `⏸ ${fmt(elapsed)}` : elapsed > 0 ? '▶ Riprendi' : '▶ Ascolta'}
            </button>
            {/* TS2 — la barra segue il dito e fa UN commit al
                rilascio. Le due regole della pagina restano nel
                commit: sipario (playGuarded) e, senza sblocco, mai
                oltre l'anteprima. */}
            <SeekBar cur={elapsed} tot={d} fmt={fmt}
              testid="fqp-seekbar"
              titolo="Trascina o tocca per spostarti nella meditazione"
              onCommit={(tRaw) => {
                const t = unlocked ? tRaw : Math.min(tRaw, PREVIEW_SEC - 1);
                setElapsed(t);
                playGuarded(t);
              }} />
          </div>

          {/* AT1 — l'avviso vive NEL momento del play, non in un
              cartello all'ingresso: compare solo su telefono (stessa
              media query di .solo-telefono) e solo se questa sessione
              ha davvero frequenze che l'altoparlante non riproduce. */}
          {playing && avvisoTelefono && (
            <div className="cuffie-avviso solo-telefono-block"
              data-testid="fqp-avviso-cuffie">
              🎧 {avvisoTelefono}
            </div>
          )}

          {/* AT3 — l'ascolto che sopravvive al blocco schermo: si
              prepara con un tocco (render visibile), poi il telefono
              si puo' bloccare — comandi sulla schermata di blocco
              compresi. Solo a sblocco avvenuto: il cancello dei 90
              secondi resta sovrano. */}
          {continuoPossibile && !continuo && (
            <div className="continuo-riga solo-telefono-block">
              {contProg == null ? (
                <button type="button" className="readmore"
                  data-testid="fqp-continuo"
                  onClick={() => preparaGuarded(elapsed)}>
                  Prepara l'ascolto a schermo bloccato
                </button>
              ) : (
                <span data-testid="fqp-continuo-prog">
                  <span className="prep">◌</span> Preparo l'ascolto continuo…
                  {' '}{Math.round(contProg * 100)}%
                </span>
              )}
            </div>
          )}
          {!continuo && (
            <div className="continuo-riga">
              <button type="button" className="readmore"
                data-testid="fqp-guarda"
                onClick={() => setGuarda((v) => !v)}>
                {guarda ? 'Nascondi Aurya Mode' : '✦ Guarda il suono'}
              </button>
            </div>
          )}
          {contErrore && (
            <div className="continuo-riga" data-testid="fqp-continuo-errore"
              style={{ color: 'var(--alert)' }}>{contErrore}</div>
          )}
          {continuo && (
            <div className="continuo-riga attivo" data-testid="fqp-continuo-attivo">
              Ascolto continuo attivo: puoi bloccare lo schermo.
            </div>
          )}

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
            {attesaConferma && (
              <div className="warnbox" style={{ margin: '12px 0', textAlign: 'left' }}
                data-testid="fqz-attesa-conferma">
                Ti abbiamo scritto: apri l’email e clicca il link di conferma.
                Il link ti riporta qui, con la sessione intera sbloccata.
              </div>
            )}
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
            {/* SB2 — chi e' GIA' iscritto non rifa' la fila: dichiara
                l'email e riprende l'ascolto, come sulle meditazioni */}
            <p style={{ fontSize: 12.5, color: 'var(--dim)', marginTop: 14 }}>
              Sei già iscritto alla Lettera?{' '}
              <button type="button" className="readmore" style={{ display: 'inline' }}
                data-testid="fqz-gate-already"
                onClick={async () => {
                  if (!email) { setGateMsg('Scrivi la tua email qui sopra e ripremi'); return; }
                  setSubscribing(true); setGateMsg('');
                  try {
                    await sblocca(email);
                    setUnlocked(true); setGateOpen(false); play(0);
                  } catch (err) {
                    setGateMsg(err?.response?.data?.detail || 'Email non riconosciuta');
                  } finally { setSubscribing(false); }
                }}>Sblocca con la tua email</button>
            </p>
            <p style={{ fontSize: 12.5, color: 'var(--dim)', marginTop: 8 }}>
              Hai un account Aurya?{' '}
              <a href={entraInAurya(email, `/frequenze/${slug}`)}
                data-testid="fqz-gate-accedi"
                style={{ color: 'var(--water)' }}>Accedi</a>
              {' '}· non ce l'hai?{' '}
              <a href={creaAccount(email, `/frequenze/${slug}`)}
                data-testid="fqz-gate-crea"
                style={{ color: 'var(--water)' }}>Crealo gratis</a>
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
