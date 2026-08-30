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
  preparaContinuo, continuoDisponibile, continuoSupportato, lettoreDaUrl,
} from './engine/continuo';
import { SafetyLine, useSafetyGate } from './SafetyCurtain';
import { prova, migraVecchieChiavi } from '../../lib/cerchio';
import CancelloLettera from './CancelloLettera';
import './frequenze.css';
import './meditazioni.css';
import SoundTopbar from './SoundTopbar';
import SeekBar from './SeekBar';
import AuryaMode from './visual/AuryaMode';
import { creaLettore } from './visual/analisi';
import { creaLettoreDaRicetta } from './visual/ricetta';
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
  /* 24/8 — anche l'OPERATORE e' sbloccato: il suo login vive in
     `token` (non platform_token) e per giorni il player lo ha
     trattato da visitatore qualunque — sul suo telefono finiva sul
     percorso pesante (crash) o sul cancello della SUA newsletter. */
  const [unlocked, setUnlocked] = useState(() =>
    !!prova() || !!localStorage.getItem('platform_token')
    || !!localStorage.getItem('token'));

  /* FN1 (30/8, il fix del founder) — IL PEDAGGIO SI PAGA UNA VOLTA.
     Chi arriva dalla landing con l'anteprima gia' consumata
     (?da=anteprima, o il segno di sessione lasciato a fine corsa)
     non deve riascoltare 90 secondi per vedere il cancello: il
     cancello lo accoglie all'arrivo. Chi e' sbloccato non lo vede
     comunque (la condizione di render resta gateOpen && !unlocked);
     chi arriva freddo da un link condiviso vive il flusso di sempre. */
  useEffect(() => {
    if (!track || unlocked) return;
    let daAnteprima = false;
    try {
      daAnteprima = new URLSearchParams(window.location.search).get('da') === 'anteprima'
        || sessionStorage.getItem('fqz_anteprima_finita') === '1';
    } catch { /* private mode: pazienza */ }
    if (daAnteprima) setGateOpen(true);
  }, [track, unlocked]);
  const [gateMsg, setGateMsg] = useState('');

  const ctxRef = useRef(null);
  const liveRef = useRef(null);
  const timerRef = useRef(null);
  const soundsRef = useRef({});
  const masterKORef = useRef(false);      /* master fallito: si sintetizza */
  const passRef = useRef(null);           /* il pass del master, PRE-SCORTATO */
  /* LA DIAGNOSI D'ASCOLTO (?ascolto=1) — dopo giorni di «solita
     situazione» dal telefono del founder, si misura sul dispositivo:
     ramo scelto, stati, errori JS catturati. Zero costi senza flag. */
  const diagOn = /[?&]ascolto=1/.test(window.location.search);
  const [diag, setDiag] = useState([]);
  const annota = (riga) => { if (diagOn) setDiag((d) => [...d.slice(-7), riga]); };
  useEffect(() => {
    if (!diagOn) return undefined;
    const suErr = (e) => annota('ERR ' + (e.message || e.reason?.message || String(e.reason || e)).slice(0, 90));
    window.addEventListener('error', suErr);
    window.addEventListener('unhandledrejection', suErr);
    return () => {
      window.removeEventListener('error', suErr);
      window.removeEventListener('unhandledrejection', suErr);
    };
  }, [diagOn]);  // eslint-disable-line react-hooks/exhaustive-deps
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

  /* VS1/VS3 (24/8) — LA SCENA HA BISOGNO DI UN'ANALISI VIVA.
     Col master il suono esce da un <audio> PURO, e puro deve restare:
     un grafo in mezzo lo rimetterebbe sotto il tasto silenzioso e lo
     ucciderebbe a schermo bloccato (lezione AT3). Si tenta quindi la
     presa sul FLUSSO — una copia, l'uscita non si tocca — e dove il
     browser non la offre (Safari non ha captureStream sui media:
     proprio l'iPhone, dov'e' nato «Guarda il suono») si dipinge la
     RICETTA. Due strade, una sola scena, e il suono identico. */
  const agganciaVisual = (ctx, h, score) => {
    const dallaRicetta = (perche) => {
      const l = creaLettoreDaRicetta(ctx, score, () => h.currentTime());
      lettoreRef.current = l;
      setLettore(l);
      annota('visual: ricetta dipinta (' + perche + ')');
    };
    const vero = creaLettore(ctx);
    h.presaAnalisi(ctx, vero.analyser, (ok) => {
      if (!ok) { dallaRicetta('flusso non disponibile'); return; }
      lettoreRef.current = vero;
      setLettore(vero);
      annota('visual: flusso vero');
      /* La rete che nessuno vede: il flusso puo' esserci e non portare
         niente (copia muta). Se dopo qualche secondo di suono vero
         l'energia e' ancora zero, la scena non e' ferma per scelta —
         e' morta, e si passa alla ricetta. */
      setTimeout(() => {
        if (lettoreRef.current !== vero) return;
        if (h.currentTime() > 1 && vero.leggi().energia < 0.002) {
          dallaRicetta('flusso muto');
        }
      }, 3500);
    });
  };

  useEffect(() => {
    // SB1 — vecchie chiavi HMAC → prova unica (poi si ricontrolla)
    migraVecchieChiavi().then(() => { if (prova()) setUnlocked(true); });
    frequenciesAPI.getPublic(slug)
      .then((r) => {
        setTrack(r.data);
        /* LA PRE-SCORTA DEL PASS (24/8, lezione del gesto su iOS):
           un el.play() dopo un giro di rete perde il gesto utente e
           viene rifiutato in silenzio — «clicco una volta niente,
           riclicco e parte» (founder). Il pass si chiede ORA, cosi'
           al click il lettore nasce sincrono, dentro il gesto. */
        if (r.data.master_pronto
            && (prova() || localStorage.getItem('platform_token')
                || localStorage.getItem('token'))) {
          frequenciesAPI.masterPass(slug, prova())
            .then((rp) => { passRef.current = rp.data.pass; annota('pre-scorta pass: OK'); })
            .catch((e) => annota('pre-scorta pass KO: ' + (e?.response?.status || 'rete')));
        }
      })
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
    /* IL MASTER (23/8) — se la traccia ha il mix renderizzato alla
       pubblicazione e l'ascolto e' sbloccato, si suona QUEL file in
       streaming (come una canzone: partenza immediata, RAM da
       streaming, schermo bloccato nativo) invece di risintetizzare
       le basi. Qualunque intoppo -> percorso synth di sempre. */
    /* L'ANTEPRIMA-FILE (M3, 24/8) — chi NON e' sbloccato (chiunque
       riceva un link condiviso) prima sintetizzava i 90 secondi col
       percorso pesante: sul telefono il tab moriva di RAM. Ora
       ascolta un file di ~2 MB ritagliato dal master; il cancello
       arriva ai 90 secondi come sempre. */
    const avviaAnteprima = () => {
      annota('ramo: ANTEPRIMA (file 90s)');
      const h = lettoreDaUrl(track.anteprima_url,
        Math.min(PREVIEW_SEC, track.score.duration_sec),
        { titolo: track.title, autore: track.operator?.name }, {
          onPlay: () => setPlaying(true),
          onPause: () => setPlaying(false),
          onEnd: () => { setPlaying(false); setGateOpen(true); },
          onTime: (t2) => {
            setElapsed(t2);
            if (t2 >= PREVIEW_SEC) { h.pause(); setGateOpen(true); }
          },
        });
      contRef.current = h;
      setContinuo(true);
      agganciaVisual(ctx, h, track.score);
      segnaAscolto();
      h.seek(fromT);
      h.play();
    };
    if (!unlocked && track.anteprima_url && !contRef.current && !masterKORef.current) {
      try {
        avviaAnteprima();
        return;
      } catch (err) {
        annota('anteprima KO: ' + (err?.message || 'errore'));
        console.warn('[anteprima] non disponibile, sintetizzo:', err?.message);  // eslint-disable-line no-console
        masterKORef.current = true;
      }
    }
    if (track.master_pronto && unlocked && !contRef.current && !masterKORef.current) {
      try {
        annota('ramo: MASTER (pass ' + (passRef.current ? 'pre-scortato' : 'da chiedere') + ')');
        /* col pass pre-scortato niente rete tra il tocco e il play */
        let passo = passRef.current;
        if (!passo) {
          const risp = await frequenciesAPI.masterPass(slug, prova());
          passo = risp.data.pass;
          passRef.current = passo;
        }
        const base = process.env.REACT_APP_BACKEND_URL || '';
        const src = `${base}/api/frequencies/public/${slug}/master?pass=${encodeURIComponent(passo)}`;
        const h = lettoreDaUrl(src, track.score.duration_sec,
          { titolo: track.title, autore: track.operator?.name }, {
            onPlay: () => setPlaying(true),
            onPause: () => setPlaying(false),
            onEnd: () => { setPlaying(false); setElapsed(0); },
            onTime: (t2) => setElapsed(t2),
          });
        contRef.current = h;
        setContinuo(true);
        agganciaVisual(ctx, h, track.score);
        segnaAscolto();
        h.seek(fromT);
        h.play();
        return;
      } catch (err) {
        /* LA TRAPPOLA CHIUSA (24/8): qui si ripiegava sul SYNTH — la
           strada che sui telefoni muore di RAM. Un token scaduto nel
           localStorage bastava: unlocked sembrava vero, il server
           diceva 401, e il fallback era il crash. Ora il ripiego e'
           l'ANTEPRIMA leggera (90s + cancello): se il server ti
           rifiuta, per lui non sei sbloccato — e il telefono vive. */
        annota('master KO: ' + (err?.response?.status || err?.message || 'errore'));
        console.warn('[master] non disponibile:', err?.message);  // eslint-disable-line no-console
        if (track.anteprima_url) {
          /* la verita' del server vince: per lui non sei sbloccato.
             E il ripiego parte SUBITO — mai piu' il synth che uccide
             i telefoni quando esiste la via leggera. */
          setUnlocked(false);
          try { avviaAnteprima(); return; } catch (e2) { /* si scende al synth */ }
        }
        masterKORef.current = true;
      }
    }
    annota('ramo: SYNTH (risintesi delle basi)');
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
      agganciaVisual(ctxRef.current, h, track.score);
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

  /* FN2 (30/8) — la meccanica del form vive in CancelloLettera; qui
     resta il gesto di casa: a sblocco avvenuto si smonta il lettore
     dell'anteprima e si riparte da zero col master. */
  const dopoSblocco = () => {
    setUnlocked(true);
    setGateOpen(false);
    setGateMsg('');
    if (contRef.current) {
      try { contRef.current.dispose(); } catch (e2) { /* niente */ }
      contRef.current = null;
      setContinuo(false);
    }
    play(0);
  };

  const pannelloDiag = diagOn ? (
    <div style={{ position: 'fixed', left: 8, bottom: 8, zIndex: 90,
                  background: 'rgba(3,2,8,.88)', color: '#9ef7c3',
                  font: '10px/1.6 monospace', padding: '8px 10px',
                  borderRadius: 8, maxWidth: '92vw', whiteSpace: 'pre-wrap' }}>
      {'build ascolto 24/8\n'
        + 'sbloccato ' + String(unlocked)
        + ' | master ' + String(!!track?.master_pronto)
        + ' | anteprima ' + String(!!track?.anteprima_url)
        + ' | token ' + String(!!localStorage.getItem('token'))
        + '\n' + (diag.length ? diag.join('\n') : '(nessun evento)')}
    </div>
  ) : null;

  if (notFound) {
    return (
      <div className="fqz med">
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
  if (!track) return <div className="fqz med" style={{ minHeight: '100vh' }} />;

  const d = track.score.duration_sec;
  const avvisoTelefono = avvisoCuffieScore(track.score);
  const continuoPossibile = unlocked && continuoSupportato()
    && continuoDisponibile(track.score);

  return (
    <div className="fqz med" data-testid="fqz-public">
      {pannelloDiag}
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

          {/* AV1 — Aurya Mode. Si accende con un gesto: mai da sola,
              disegnare consuma.

              VS1 (24/8) — qui c'era anche `!continuo`. Nacque quando
              l'ascolto continuo era il caso raro e non si sapeva
              analizzare un <audio> senza dirottarlo; poi e' arrivato
              IL MASTER e il caso raro e' diventato l'UNICO — quella
              condizione non proteggeva piu' niente, spegneva il visual
              su ogni meditazione (founder: «il suono non si visualizza
              piu'»). Ora si disegna quando c'e' un'analisi viva,
              qualunque strada l'abbia portata (agganciaVisual): il
              suono non si tocca in nessuna delle due. */}
          {guarda && lettore && (
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
          {/* VS4 (25/8) — l'INTERRUTTORE resta acceso mentre si ascolta.
              Anche qui c'era `!continuo`: ieri ho tolto quella
              condizione dalla SCENA e ho lasciato quella del PULSANTE,
              cosi' il visual si vedeva solo se lo chiedevi PRIMA di
              premere play — premuto play, il pulsante spariva e non
              c'era piu' modo di chiederlo (founder). Il fix di ieri era
              meta' del fix: la stessa condizione viveva in due posti.
              Restare opt-in e' voluto (disegnare consuma: AV1), ma la
              scelta dev'essere disponibile QUANDO viene voglia — cioe'
              mentre il suono suona. */}
          <div className="continuo-riga">
            <button type="button" className="readmore"
              data-testid="fqp-guarda"
              onClick={() => setGuarda((v) => !v)}>
              {guarda ? 'Nascondi Aurya Mode' : '✦ Guarda il suono'}
            </button>
          </div>
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
            <CancelloLettera slug={slug} durataSec={track?.score?.duration_sec}
              onSbloccato={dopoSblocco}>
              <p style={{ fontSize: 12.5, color: 'var(--dim)', marginTop: 8 }}>
                Oppure{' '}
                <button type="button" className="ghost"
                  style={{ padding: 0, color: 'var(--dim)', textDecoration: 'underline' }}
                  onClick={() => setGateOpen(false)}>riascolta l'anteprima</button>
                {' '}· <a href="/meditazioni" style={{ color: 'var(--water)' }}
                  data-testid="cancello-tutte">tutte le Meditazioni</a>
              </p>
            </CancelloLettera>
            {gateMsg && <p style={{ color: 'var(--alert)', fontSize: 12, marginTop: 8 }}>{gateMsg}</p>}
          </div>
        </div>
      )}
    </div>
  );
}
