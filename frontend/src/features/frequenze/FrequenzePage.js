/**
 * Frequenze by Aurya — l'app compositore (FQ0.5, 18/8/2026).
 *
 * DESIGN: quello del prototipo del founder, voluto cosi' — un prodotto a
 * se' stante, scuro (ink/lamp/water), perfettamente comunicante col
 * gestionale ma con la sua identita'. Il CSS e' frequenze.css (verbatim
 * dal prototipo, scopato sotto .fqz); il bottone «Gestionale» in testata
 * riporta all'app madre.
 *
 * INTEGRAZIONE: login operatore, bozze salvate per-org via API
 * (/api/frequencies), motore in engine/ (lo stesso del player pubblico
 * di FQ1).
 *
 * NIENTE UPLOAD (founder, 18/8): le tracce si compongono SOLO con le
 * frequenze e i suoni disponibili in piattaforma — l'operatore non
 * carica audio suo. Il mondo «Suoni» (basi curate) e' predisposto e
 * arriva con FQ2 (audio_assets).
 */
import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { frequenciesAPI } from '../../api/frequencies';
import {
  METHOD_LABELS, CURVE_LABELS, NOISE_COLORS, WAVE_PERIOD_SEC,
  startPreview, startCardLive,
} from './engine/synth';
import {
  loadAssetBuffer, resolveAudioLayers, resolveVoiceLayers, fileDuration,
} from './engine/assets';
import {
  VOICE_PRESETS, buildVoiceChain, cleanVoiceBuffer, connectVoiceSources,
} from './engine/voicefx';
import { PROTOCOLLI } from './content/protocolli';
import { BIB, SOUND_KEYS, LEARN_KEYS } from './content/biblioteca';
import GuidaView from './GuidaView';
import { PRO_ENTRY } from './links';
import { SafetyButton, SafetyLine, useSafetyGate } from './SafetyCurtain';
import './frequenze.css';
import SoundTopbar from './SoundTopbar';

const fmt = (s) => {
  s = Math.max(0, Math.round(s));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
};
let _uid = 5000;

const LISTEN = {
  bin: '🎧 Effetto solo in cuffia', bil: '🎧 In cuffia (consigliato)',
  iso: '🔊 Anche in altoparlante', mono: '🔊 Anche in altoparlante',
  noise: '🔊 Anche in altoparlante', tone: '🔊 Anche in altoparlante',
};
/* Le stesse chiavi di SOUND_CATEGORIES lato server, nello stesso
   ordine (guardia di parità nei test): il tab si traduce in categoria
   con un semplice toLowerCase. */
const SOUND_CATS = ['Ambient', 'Natura', 'Droni', 'Corpo', 'Campane',
  'Ritmi', 'Voce', 'Transizioni'];

/* Orientamento della biblioteca: una riga sotto le tab (che cosa sto
   guardando) e tre righe sopra le card (perché è diverso dagli altri).
   Acculturare senza appesantire: nessun tutorial, nessun onboarding. */
const CAT_HINT = {
  'Bande cerebrali': "Ritmi dell'attività elettrica del cervello.",
  'Altre frequenze': 'Frequenze sonore, fenomeni fisici, accordature e tradizioni.',
  'Ritmi del corpo': 'Respiro, cuore, passo: ritmi da seguire, non frequenze da subire.',
  'Metodi': 'Tecniche per costruire e modulare uno stimolo sonoro.',
};
/* Una riga per tab anche nel mondo dei suoni: chi arriva capisce a
   cosa serve quella famiglia senza aprire tutte le card. */
const SOUND_HINT = {
  Ambient: 'Atmosfere lunghe: il tappeto su cui appoggiare tutto il resto.',
  Natura: 'Ambienti registrati: acqua, uccelli, vento, temporale.',
  Droni: 'Toni tenuti, senza sviluppo. Il letto più semplice sotto una sessione.',
  Corpo: 'Una serie sola, in ordine: dalla radice alla testa.',
  Campane: 'Campane, ciotole e metalli: attacco netto e coda lunga.',
  Ritmi: 'Il passo del corpo: respiro e battito, e le fasi del breathwork.',
  Voce: 'Voce come materiale sonoro: vocali tenute e cori.',
  Transizioni: 'Passaggi brevi per cambiare momento dentro la sessione.',
};
const CAT_INTRO = {
  'Bande cerebrali': {
    t: 'Cosa sono le bande cerebrali?',
    p: "Il cervello presenta attività elettrica ritmica che possiamo osservare, per esempio, attraverso l'EEG. Delta, Theta, Alpha, Beta e Gamma descrivono diverse gamme di queste oscillazioni. Non sono semplicemente frequenze sonore: qui esploriamo il fenomeno cerebrale e, separatamente, come alcuni stimoli sonori cercano di interagire con esso.",
  },
  'Ritmi del corpo': {
    t: 'Qui il ritmo lo dai tu.',
    p: "Nelle altre sezioni il suono è l'oggetto dell'ascolto. Qui è un metronomo: un'onda che sale e scende per darti il passo del respiro, o una pulsazione per il cammino. La differenza conta anche per l'onestà di quello che possiamo dire — ciò che la ricerca documenta riguarda la pratica (respirare lentamente, muoversi a tempo), non il suono che la accompagna.",
  },
  'Altre frequenze': {
    t: 'Frequenze diverse, origini diverse.',
    p: "Qui incontrerai frequenze con origini molto diverse: ricerca neuroscientifica, fenomeni fisici, accordature musicali e tradizioni sonore. Il livello di evidenza ti aiuta a distinguere ciò che è documentato da ciò che appartiene soprattutto alla tradizione.",
  },
  'Metodi': {
    t: 'Una frequenza dice «cosa». Un metodo dice «come».',
    p: "I metodi descrivono modi diversi di costruire o modulare uno stimolo sonoro: dal battito binaurale al tono isocronico, fino alla modulazione di un paesaggio sonoro.",
  },
};
const HOWTO_BODY = '<h4>Frequenza</h4><p>La proprietà fisica di un suono, espressa in Hertz.</p>'
  + '<h4>Banda cerebrale</h4><p>Una gamma di oscillazioni dell\'attività elettrica cerebrale osservabile, per esempio, attraverso l\'EEG.</p>'
  + '<h4>Metodo</h4><p>Il modo in cui uno stimolo sonoro viene costruito o modulato.</p>'
  + '<h4>Badge A/B/C</h4><p>Indica il livello di evidenza relativo alle affermazioni presentate, non quanto una frequenza sia «potente».</p>'
  + '<h4>Ascolta</h4><p>Permette di fare esperienza diretta dello stimolo.</p>';

export default function FrequenzePage() {
  const navigate = useNavigate();
  const { user, isAuthenticated, loading: authLoading } = useAuth();
  const isSystemAdmin = user?.role === 'system_admin';
  /* ── SP — pubblico e operatore, stessa pagina ─────────────────────
     Per il pubblico «Esplora» significa LEGGI → APPROFONDISCI →
     IMPARA. L'ascolto, la sessione e Crea restano valore degli
     operatori: canCompose governa SOLO cosa si disegna — la vera
     frontiera restano le API org-scoped, che per gli anonimi
     rispondono 401 comunque.

     Il token si legge SUBITO, `user` arriva solo dopo /auth/me: senza
     il secondo ramo l'operatore che ricarica vedrebbe la biblioteca
     pubblica (Ascolta e + Sessione spariti) per tutta la durata della
     chiamata — e per sempre, se il backend tarda. Se /auth/me fallisce,
     AuthContext cancella il token e il render si corregge da solo. */
  const canCompose = !!user || (authLoading && !!localStorage.getItem('token'));
  /* ── LN — ogni pagina ha il suo link ──────────────────────────────
     L'URL e' l'unica verita' per vista e tab: /sound/esplora|crea|
     impara|tracce (+ /impara/glossario), con lo stato fine nelle
     query (?categoria, ?mondo=suoni, ?bozza). Cosi' il refresh resta
     dove sei e ogni pagina si puo' linkare. Semantica history: cambio
     VISTA = push (il back torna alla vista prima), cambio tab/mondo =
     replace (il back non ripercorre ogni tab).
     Tutte le rotte /sound/* montano QUESTO stesso componente: la
     sessione in costruzione e l'audio sopravvivono alla navigazione. */
  const location = useLocation();
  const qs = useMemo(() => new URLSearchParams(location.search), [location.search]);
  const VIEW_PATH = { explore: 'esplora', create: 'crea', impara: 'impara', mine: 'tracce' };
  const PATH_VIEW = { esplora: 'explore', crea: 'create', impara: 'impara', tracce: 'mine' };
  /* LN — ogni vista ha il suo URL, quindi ogni categoria ha il suo
     slug. Una categoria senza slug NON si apre: il clic scrive
     `?categoria=` vuoto e la tab torna alla prima (successo con «Ritmi
     del corpo» il 21/8). Le due mappe vanno tenute gemelle. */
  const CAT_SLUG = { 'Bande cerebrali': 'bande-cerebrali', 'Altre frequenze': 'altre-frequenze',
    'Ritmi del corpo': 'ritmi-del-corpo', 'Metodi': 'metodi' };
  const SLUG_CAT = { 'bande-cerebrali': 'Bande cerebrali', 'altre-frequenze': 'Altre frequenze',
    'ritmi-del-corpo': 'Ritmi del corpo', 'metodi': 'Metodi' };

  const seg = location.pathname.split('/').filter(Boolean);   // ['sound','crea',...]
  const view = PATH_VIEW[seg[1]] || 'explore';
  const world = view === 'explore' && qs.get('mondo') === 'suoni' ? 'sound' : 'freq';
  const soundCat = SOUND_CATS.find((c) => c.toLowerCase() === (qs.get('categoria') || '')) || SOUND_CATS[0];
  const curTab = view === 'impara'
    ? (seg[2] === 'glossario' ? 'Glossario' : 'Guida')
    : (SLUG_CAT[qs.get('categoria')] || SOUND_KEYS[0]);

  const setView = (v) => navigate(`/sound/${VIEW_PATH[v]}`);
  const setWorld = (w) => navigate(w === 'sound' ? '/sound/esplora?mondo=suoni' : '/sound/esplora', { replace: true });
  const setSoundCat = (c) => navigate(`/sound/esplora?mondo=suoni&categoria=${c.toLowerCase()}`, { replace: true });
  const setCurTab = (k) => {
    if (view === 'impara') navigate(k === 'Glossario' ? '/sound/impara/glossario' : '/sound/impara', { replace: true });
    else navigate(`/sound/esplora?categoria=${CAT_SLUG[k] || ''}`, { replace: true });
  };

  // /sound nudo → forma canonica (replace: il back non deve vederlo)
  useEffect(() => {
    if (!seg[1]) navigate('/sound/esplora', { replace: true });
  }, [seg, navigate]);

  // ogni pagina col suo nome anche nella scheda del browser
  useEffect(() => {
    const name = view === 'impara'
      ? (curTab === 'Glossario' ? 'Glossario' : 'Le fondamenta')
      : { explore: 'Esplora', create: 'Crea', mine: 'Le mie tracce' }[view];
    document.title = `Aurya Sound — ${name}`;
  }, [view, curTab]);
  /* SF (20/8) — le controindicazioni si aprono prima del SUONO, non
     prima della pagina: chi arriva a leggere la Guida non trova un muro
     medico, chi sta per ascoltare le vede sempre (ogni 90 giorni). */
  const { guard, curtain, openReview } = useSafetyGate();
  const [ask, setAsk] = useState(null);                  // {title,msg,opts:[[label,fn]]}
  const [learn, setLearn] = useState(null);              // {title,body}

  const [durationMin, setDurationMin] = useState(20);
  const [fadeIn, setFadeIn] = useState(10);
  const [fadeOut, setFadeOut] = useState(20);
  const [layers, setLayers] = useState([]);
  const [phases, setPhases] = useState([]);
  const [title, setTitle] = useState('');
  const [intent, setIntent] = useState(null);
  const [trackId, setTrackId] = useState(null);
  const [trackStatus, setTrackStatus] = useState('draft');
  const [trackSlug, setTrackSlug] = useState(null);
  const [drafts, setDrafts] = useState([]);
  const [playing, setPlaying] = useState(false);
  const [preparing, setPreparing] = useState(false);  // decode in corso
  const [elapsed, setElapsed] = useState(0);
  const [status, setStatus] = useState('');
  const [saving, setSaving] = useState(false);
  // ascolto live delle schede: gli HANDLE vivono in un ref (side effect
  // fuori dagli updater React: in dev gli updater girano due volte e un
  // grafo orfano resterebbe a suonare per sempre — il bug dello stop);
  // lo stato tiene solo le chiavi accese, per la UI.
  const liveCardsRef = useRef({});
  const [liveKeys, setLiveKeys] = useState([]);

  const ctxRef = useRef(null);
  const liveRef = useRef(null);
  const timerRef = useRef(null);
  const duration = Math.max(60, durationMin * 60);

  // FV3 — le basi respirano piano sotto la voce (parte della ricetta)
  const [voiceDuck, setVoiceDuck] = useState(false);
  const hasVoiceLayers = layers.some((l) => l.kind === 'voice');

  // ONDA 2 — la versione la decide comunque il server (clean_score), ma
  // il client non deve dichiarare il falso: una marea e' v3.
  const hasWaveLayers = layers.some((l) => l.curve === 'wave');
  const score = useMemo(() => ({
    score_version: hasWaveLayers ? 3 : hasVoiceLayers ? 2 : 1, duration_sec: duration,
    fade_in_sec: fadeIn, fade_out_sec: fadeOut, layers, phases,
    ...(hasVoiceLayers ? { voice_duck: voiceDuck } : {}),
  }), [duration, fadeIn, fadeOut, layers, phases, hasVoiceLayers, hasWaveLayers, voiceDuck]);

  // per l'API: via i campi privati di lavoro (_laneEl e' un nodo DOM —
  // serializzarlo manderebbe in circolo JSON.stringify)
  const scorePayload = () => ({
    ...score,
    layers: layers.map((l) => {
      const clean = {};
      Object.keys(l).forEach((k) => { if (!k.startsWith('_')) clean[k] = l[k]; });
      return clean;
    }),
  });

  const audioCtx = () => {
    ctxRef.current = ctxRef.current || new (window.AudioContext || window.webkitAudioContext)();
    ctxRef.current.resume();
    return ctxRef.current;
  };

  /* ── bozze ── */
  const loadDrafts = async () => {
    try { setDrafts((await frequenciesAPI.list()).data.items || []); } catch { /* non bloccante */ }
  };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { if (canCompose) loadDrafts(); }, [canCompose]);

  /* ── libreria suoni (FQ2) ── */
  const [sounds, setSounds] = useState([]);
  const [uploading, setUploading] = useState(false);
  const soundFileRef = useRef(null);
  const previewAudioRef = useRef(null);          // <audio> condiviso anteprime
  const [previewingId, setPreviewingId] = useState(null);
  const soundsById = useMemo(
    () => Object.fromEntries(sounds.map((s) => [s.id, s])), [sounds]);
  const loadSounds = async () => {
    try { setSounds((await frequenciesAPI.listSounds()).data.items || []); } catch { /* non bloccante */ }
  };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { if (canCompose) loadSounds(); }, [canCompose]);

  const stopSoundPreview = () => {
    if (previewAudioRef.current) {
      previewAudioRef.current.pause();
      previewAudioRef.current.src = '';
    }
    setPreviewingId(null);
  };
  const [soundLoadingId, setSoundLoadingId] = useState(null);
  const toggleSoundPreview = (asset) => {
    if (previewingId === asset.id) { stopSoundPreview(); return; }
    stopSoundPreview();
    if (!previewAudioRef.current) previewAudioRef.current = new Audio();
    const el = previewAudioRef.current;
    el.src = asset.stream_url;
    el.loop = true;
    el.volume = 0.8;
    setSoundLoadingId(asset.id);
    el.onplaying = () => setSoundLoadingId(null);
    el.play().catch(() => { setSoundLoadingId(null); setStatus('Anteprima non disponibile'); });
    setPreviewingId(asset.id);
  };
  useEffect(() => () => stopSoundPreview(), []); // eslint-disable-line react-hooks/exhaustive-deps

  const addSoundToSession = (asset) => {
    setLayers((ls) => [...ls, {
      id: ++_uid, kind: 'audio', asset_id: asset.id,
      name: asset.title, start: 0, end: duration,
      gain: 0.7, loop: true, mute: false,
    }]);
    setStatus(`«${asset.title}» aggiunta alla sessione — vai a «Crea»`);
  };

  const uploadSound = async (file) => {
    if (!file) return;
    setUploading(true);
    setStatus(`Carico «${file.name}»…`);
    try {
      const durationSec = await fileDuration(audioCtx(), file);
      const title = file.name.replace(/\.[^.]+$/, '').replace(/[_-]+/g, ' ').slice(0, 80);
      await frequenciesAPI.uploadSound({
        file, title, category: soundCat.toLowerCase(),
        durationSec, licenseNote: 'caricata dal system admin',
      });
      await loadSounds();
      setStatus(`«${title}» in libreria (${SOUND_CATS.find((c) => c.toLowerCase() === soundCat.toLowerCase())})`);
    } catch (e) {
      setStatus(e?.response?.data?.detail || 'Upload fallito');
    } finally { setUploading(false); }
  };
  const removeSound = (asset) => setAsk({
    title: 'Eliminare dalla libreria?',
    msg: `«${asset.title}» sparirà per tutti gli operatori. Le tracce che la usano suoneranno senza questa base.`,
    opts: [['Sì, elimina', async () => {
      try { await frequenciesAPI.removeSound(asset.id); loadSounds(); } catch { setStatus('Errore'); }
    }]],
  });

  /* ── FV3: il leggio — spezzoni voce dell'operatore ──
   * SOLO registrazione in-app (decisione founder 18/8: niente upload).
   * Gli handle di MediaRecorder/stream vivono in ref, MAI negli updater. */
  const [voiceClips, setVoiceClips] = useState([]);
  const [recState, setRecState] = useState('idle');   // idle | rec
  const [recSecs, setRecSecs] = useState(0);
  const [prevFx, setPrevFx] = useState('dream');      // preset di prova
  const [voicePrevId, setVoicePrevId] = useState(null);
  const recRef = useRef(null);          // MediaRecorder
  const recChunksRef = useRef([]);
  const recSecsRef = useRef(0);
  const recTimerRef = useRef(null);
  const voicePrevRef = useRef(null);    // anteprima spezzone in corso
  const voiceById = useMemo(
    () => Object.fromEntries(voiceClips.map((c) => [c.id, c])), [voiceClips]);
  const loadVoice = async () => {
    try { setVoiceClips((await frequenciesAPI.listVoice()).data.items || []); }
    catch { /* non bloccante */ }
  };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { if (canCompose) loadVoice(); }, [canCompose]);

  /* FV6 — il taglio sta sullo SPEZZONE, non sul livello.
   * `trim_start`/`trim_end` sono i secondi che la sessione salta ai due
   * capi: la registrazione resta intera sul disco. Da qui in giu' tutto
   * (anteprima, «+ sessione», barra sulla linea del tempo) ragiona in
   * termini di durata UTILE. */
  const clipUseful = (c) => Math.max(1,
    (c.duration_sec || 0) - (c.trim_start || 0) - (c.trim_end || 0));

  const stopVoicePreview = () => {
    if (voicePrevRef.current) { voicePrevRef.current.stop(); voicePrevRef.current = null; }
    setVoicePrevId(null);
  };
  const [voicePrevLoading, setVoicePrevLoading] = useState(null);
  const toggleVoicePreview = async (clip) => {
    if (voicePrevRef.current?.id === clip.id) { stopVoicePreview(); return; }
    stopVoicePreview();
    const ctx = audioCtx();
    setVoicePrevLoading(clip.id);
    try {
      // stessa pulizia dell'ascolto in sessione: cio' che provi e' cio' che va in onda
      const buffer = cleanVoiceBuffer(ctx, await loadAssetBuffer(ctx, clip.stream_url));
      const chain = buildVoiceChain(ctx, prevFx, 0.6);
      chain.output.connect(ctx.destination);
      // si ascolta il taglio, non il file: cio' che provi e' cio' che va in onda
      const off = Math.min(clip.trim_start || 0, Math.max(0, buffer.duration - 0.2));
      const len = Math.min(clipUseful(clip), Math.max(0.2, buffer.duration - off));
      const sources = connectVoiceSources(ctx, buffer, chain);
      sources.forEach((s) => { s.start(ctx.currentTime, off); s.stop(ctx.currentTime + len); });
      sources[0].onended = () => {
        if (voicePrevRef.current?.id === clip.id) stopVoicePreview();
      };
      voicePrevRef.current = {
        id: clip.id,
        stop: () => {
          sources.forEach((s) => { try { s.stop(); } catch (e) { /* gia' fermo */ } });
          setTimeout(() => { try { chain.output.disconnect(); } catch (e) { /* idem */ } }, 900);
        },
      };
      setVoicePrevId(clip.id);
    } catch { setStatus('Anteprima non disponibile'); }
    finally { setVoicePrevLoading(null); }
  };

  const startRec = async () => {
    if (recState === 'rec') return;
    stopVoicePreview();
    let stream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true },
      });
    } catch { setStatus('Microfono non disponibile o permesso negato'); return; }
    const mime = ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4']
      .find((m) => window.MediaRecorder && window.MediaRecorder.isTypeSupported(m));
    const mr = new window.MediaRecorder(stream, mime ? { mimeType: mime } : undefined);
    recChunksRef.current = [];
    mr.ondataavailable = (e) => { if (e.data && e.data.size) recChunksRef.current.push(e.data); };
    mr.onstop = async () => {
      stream.getTracks().forEach((t) => t.stop());
      const blob = new Blob(recChunksRef.current, { type: mr.mimeType || 'audio/webm' });
      const dur = recSecsRef.current;
      if (dur < 1 || !blob.size) { setStatus('Registrazione troppo corta'); return; }
      setStatus('Salvo lo spezzone…');
      try {
        const n = voiceClips.length + 1;
        const r = await frequenciesAPI.recordVoice({
          blob, mime: blob.type, title: `Spezzone ${n}`, durationSec: dur });
        await loadVoice();
        setStatus(`«${r.data.title}» tra i tuoi spezzoni — rinominalo per ritrovarlo`);
      } catch (e) {
        setStatus(e?.response?.data?.detail || 'Registrazione non salvata');
      }
    };
    mr.start(250);
    recRef.current = mr;
    recSecsRef.current = 0;
    setRecSecs(0); setRecState('rec');
    setStatus('Sto registrando — parla pure. Cuffie se la sessione è in ascolto.');
    recTimerRef.current = setInterval(() => {
      recSecsRef.current += 1;
      setRecSecs(recSecsRef.current);
      if (recSecsRef.current >= 600) stopRec();   // tetto spezzone: 10 min
    }, 1000);
  };
  const stopRec = () => {
    if (recTimerRef.current) { clearInterval(recTimerRef.current); recTimerRef.current = null; }
    if (recRef.current && recRef.current.state !== 'inactive') recRef.current.stop();
    recRef.current = null;
    setRecState('idle');
  };
  useEffect(() => () => { stopRec(); stopVoicePreview(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const addVoiceToSession = (clip) => {
    const start = Math.max(0, Math.min(elapsed, duration - 1));
    const end = Math.min(duration, start + clipUseful(clip));
    setLayers((ls) => [...ls, {
      id: ++_uid, kind: 'voice', asset_id: clip.id, name: clip.title,
      start, end, gain: 0.9, fx: 'dream', fx_amount: 0.6, mute: false,
      clip_in: clip.trim_start || 0,
    }]);
    setStatus(`«${clip.title}» sulla linea del tempo a ${fmt(start)} — effetto Sogno`);
  };
  const renameVoiceClip = async (clip, name) => {
    const t = (name || '').trim();
    if (!t || t === clip.title) return;
    try { await frequenciesAPI.renameVoice(clip.id, t); loadVoice(); }
    catch { setStatus('Rinomina fallita'); }
  };

  /* FV6 — si taglia qui, una volta. Il salvataggio e' sullo spezzone e
   * i livelli gia' in sessione che lo usano si riallineano subito: la
   * barra sulla linea del tempo si accorcia da sola e l'operatore non
   * deve toccare due posti per la stessa cosa. */
  const [trimOpen, setTrimOpen] = useState(null);   // id spezzone aperto
  // barra di ascolto su telefono: titolo/durata/dissolvenze dietro un tocco
  const [setupOpen, setSetupOpen] = useState(false);
  const saveVoiceTrim = async (clip, nextStart, nextEnd) => {
    const dur = clip.duration_sec || 0;
    let s = Math.max(0, Math.min(nextStart, Math.max(0, dur - 1)));
    let e = Math.max(0, Math.min(nextEnd, Math.max(0, dur - s - 1)));
    s = Math.round(s * 2) / 2; e = Math.round(e * 2) / 2;
    if (s === (clip.trim_start || 0) && e === (clip.trim_end || 0)) return;
    setVoiceClips((cs) => cs.map((c) => (
      c.id === clip.id ? { ...c, trim_start: s, trim_end: e } : c)));
    const len = Math.max(1, dur - s - e);
    setLayers((ls) => ls.map((l) => (
      l.kind === 'voice' && l.asset_id === clip.id
        ? { ...l, clip_in: s, end: Math.min(duration, l.start + len) }
        : l)));
    try { await frequenciesAPI.trimVoice(clip.id, { trimStart: s, trimEnd: e }); }
    catch { setStatus('Taglio non salvato'); loadVoice(); }
  };
  const removeVoiceClip = (clip) => setAsk({
    title: 'Eliminare lo spezzone?',
    msg: `«${clip.title}» sparirà anche dalle sessioni che lo usano.`,
    opts: [['Sì, elimina', async () => {
      try { await frequenciesAPI.removeVoice(clip.id); loadVoice(); }
      catch { setStatus('Errore'); }
    }]],
  });

  /* ── ascolto sessione ──
   * playSession ha degli await in mezzo (resume del contesto, decodifica
   * delle basi): senza un token di sequenza un Ferma o un seek dato
   * durante l'attesa non trova ancora niente da fermare, e il grafo
   * nasce subito dopo orfano — suona fino in fondo senza che nessuno
   * lo possa spegnere. Ogni stop invalida gli avvii in volo. */
  const playTokenRef = useRef(0);
  const stopSession = () => {
    playTokenRef.current += 1;
    if (liveRef.current) { liveRef.current.stop(); liveRef.current = null; }
    if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null; }
    setPlaying(false);
  };
  const stopAllCards = () => {
    Object.values(liveCardsRef.current).forEach((h) => h.stop());
    liveCardsRef.current = {};
    setLiveKeys([]);
  };
  useEffect(() => () => { stopSession(); stopAllCards(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const playSession = async (fromT = 0) => {
    stopSession();
    stopSoundPreview();
    if (Object.keys(liveCardsRef.current).length) {
      stopAllCards();
      setStatus('Schede in ascolto fermate — ora suona la linea del tempo');
    }
    if (!layers.length) return;
    const token = playTokenRef.current;   // stopSession() l'ha appena incrementato
    setPreparing(true);                   // l'utente vede subito che arriva
    const ctx = audioCtx();
    await ctx.resume();
    if (playTokenRef.current !== token) { setPreparing(false); return; }
    let audioLayers = [];
    if (layers.some((l) => l.kind === 'audio')) {
      setStatus('Carico le basi…');
      audioLayers = await resolveAudioLayers(ctx, score, soundsById);
      if (playTokenRef.current !== token) { setPreparing(false); return; }
    }
    let vLayers = [];
    if (hasVoiceLayers) {
      setStatus('Carico la voce…');
      vLayers = await resolveVoiceLayers(ctx, score, voiceById);
      if (playTokenRef.current !== token) { setPreparing(false); return; }
    }
    liveRef.current = startPreview(ctx, score,
      { fromT, audioLayers, voiceLayers: vLayers, voiceDuck });
    setPreparing(false);
    setPlaying(true);
    timerRef.current = setInterval(() => {
      const el = liveRef.current ? liveRef.current.elapsed() : 0;
      if (el >= duration) { stopSession(); setElapsed(0); setStatus('Ascolto terminato'); return; }
      setElapsed(Math.max(0, el));
      setStatus(`Ascolto · ${fmt(Math.max(0, el))} / ${fmt(duration)}`);
    }, 150);
  };
  /* Un solo cancello per tutto ciò che suona la linea del tempo: il
     tasto Ascolta, il righello, la barra di scorrimento passano tutti
     di qui, quindi non esiste una scorciatoia che salti l'avviso. */
  const playGuarded = guard(playSession);
  const seekTo = (t) => { if (layers.length) playGuarded(t); };

  const patchLayer = (id, patch) => {
    setLayers((ls) => ls.map((l) => (l.id === id ? { ...l, ...patch } : l)));
    if (patch.gain !== undefined && liveRef.current) liveRef.current.setLayerGain(id, patch.gain);
  };
  const removeLayer = (id) => { stopSession(); setLayers((ls) => ls.filter((l) => l.id !== id)); };

  /* ── protocolli ── */
  const applyProtocol = (name) => {
    stopSession();
    const built = PROTOCOLLI[name].build(duration);
    setLayers(built.layers.map((l) => ({ ...l, id: ++_uid })));
    setPhases(built.phases);
    setIntent(PROTOCOLLI[name].intent);
    if (!title) setTitle(name);
    setView('create');
    setStatus(`Protocollo «${name}» · ${PROTOCOLLI[name].ev}`);
  };
  const loadProtocol = (name) => {
    if (layers.length) {
      setAsk({
        title: 'Sostituire la sessione?',
        msg: `Carico il protocollo «${name}» al posto di quello che hai adesso (${layers.length} ${layers.length === 1 ? 'livello' : 'livelli'}). Il lavoro attuale verrà sostituito.`,
        opts: [[`Sostituisci con «${name}»`, () => applyProtocol(name)]],
      });
    } else applyProtocol(name);
  };

  /* ── schede live (Esplora) — side effect PRIMA del setState ── */
  const toggleCard = (key, entry) => {
    const handles = liveCardsRef.current;
    if (handles[key]) {
      handles[key].stop();
      delete handles[key];
      setLiveKeys(Object.keys(handles));
      return;
    }
    stopSession();
    const cfg = entry.cfg || {};
    // ONDA 1 (21/8) — la scheda parte dal suo f0 e il motore la porta a
    // f1 con la sua curva: prima f1 e curva restavano scritti nei dati
    // e non si sentivano mai (Delta dichiarava «4 → 2,5» e suonava 4
    // fissi). Il cfg intero viaggia: il motore legge f1, curve, breath.
    const fval = cfg.method === 'tone' ? (cfg.carrier ?? 432) : (cfg.f0 ?? 10);
    const h = startCardLive(audioCtx(), cfg, cfg.gain ?? 0.25, fval);
    h._entry = entry;
    handles[key] = h;
    setLiveKeys(Object.keys(handles));
  };
  const addCardToSession = (entry) => {
    const cfg = entry.cfg || {};
    setLayers((ls) => [...ls, {
      id: ++_uid, kind: 'neuro', name: cfg.name || entry.t,
      method: cfg.method || 'bin', timbre: cfg.timbre || 'warm',
      carrier: cfg.carrier ?? ((cfg.method || 'bin') === 'bin' ? 400 : 180),
      f0: cfg.method === 'tone' ? 10 : (cfg.f0 ?? 10),
      f1: cfg.method === 'tone' ? 10 : (cfg.f1 ?? cfg.f0 ?? 10),
      curve: cfg.curve || 'lin', start: cfg.start ?? 0, end: duration,
      gain: cfg.gain ?? 0.25, breath: true, mute: false,
    }]);
    setStatus(`«${entry.t}» aggiunta alla sessione — vai a «Crea» per strutturarla`);
  };
  const composeAllLive = () => {
    const entries = Object.values(liveCardsRef.current);
    if (!entries.length) return;
    entries.forEach((h) => addCardToSession({
      t: h._entry.cfg?.name || h._entry.t,
      cfg: { ...h._entry.cfg, method: h.method, carrier: h.carrier,
             f0: h.method === 'tone' ? 10 : h.beat,
             f1: h.method === 'tone' ? 10 : h.beat, gain: h.gain },
    }));
    stopAllCards();
    setStatus(`${entries.length} frequenze aggiunte alla sessione`);
  };

  /* ── bozze: salva/carica ── */
  const save = async () => {
    if (!layers.length) { setStatus('La sessione è vuota: niente da salvare'); return; }
    const name = title.trim() || 'Senza titolo';
    setSaving(true);
    try {
      if (trackId) {
        await frequenciesAPI.update(trackId, { title: name, score: scorePayload(), intent });
        setStatus(`Bozza «${name}» aggiornata`);
      } else {
        const r = await frequenciesAPI.create({ title: name, score: scorePayload(), intent });
        setTrackId(r.data.id);
        // timbra la bozza appena nata nell'URL (replace: niente history)
        if (view === 'create') navigate(`/sound/crea?bozza=${r.data.id}`, { replace: true });
        setStatus(`Bozza «${name}» salvata`);
      }
      loadDrafts();
    } catch (e) {
      setStatus(e?.response?.data?.detail || 'Errore nel salvataggio');
    } finally { setSaving(false); }
  };
  const openDraft = async (id, nav = true) => {
    stopSession();
    try {
      const t = (await frequenciesAPI.get(id)).data, s = t.score || {};
      setTrackId(t.id); setTitle(t.title || ''); setIntent(t.intent || null);
      setTrackStatus(t.status || 'draft'); setTrackSlug(t.slug || null);
      setDurationMin(Math.round((s.duration_sec || 1200) / 60));
      setFadeIn(s.fade_in_sec ?? 10); setFadeOut(s.fade_out_sec ?? 20);
      setLayers((s.layers || []).map((l) => ({ ...l, id: ++_uid })));
      setPhases(s.phases || []);
      setVoiceDuck(!!s.voice_duck);
      // la bozza aperta sta nell'URL: il refresh la ricarica invece di
      // buttarti fuori (nav=false quando e' l'URL stesso a chiederla)
      if (nav) navigate(`/sound/crea?bozza=${t.id}`);
      setStatus(`Bozza «${t.title}» caricata`);
    } catch { setStatus('Bozza non trovata'); }
  };

  // refresh (o link diretto) su /sound/crea?bozza=x → ricarica la bozza
  const bozzaParam = view === 'create' ? qs.get('bozza') : null;
  useEffect(() => {
    if (canCompose && bozzaParam && bozzaParam !== trackId) openDraft(bozzaParam, false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [bozzaParam]);
  const removeDraft = (id, name) => setAsk({
    title: 'Eliminare la bozza?',
    msg: `«${name}» verrà eliminata. Non si può annullare.`,
    opts: [['Sì, elimina', async () => {
      try {
        await frequenciesAPI.remove(id);
        if (id === trackId) {
          setTrackId(null);
          // la bozza eliminata non deve restare nell'URL di Crea
          if (qs.get('bozza') === id) navigate('/sound/tracce', { replace: true });
        }
        loadDrafts();
      } catch { setStatus('Errore'); }
    }]],
  });

  const publishById = async (id) => {
    try {
      const r = await frequenciesAPI.publish(id);
      loadDrafts();
      if (id === trackId) { setTrackStatus('published'); setTrackSlug(r.data.slug); }
      const url = `${window.location.origin}/frequenze/${r.data.slug}`;
      try { await navigator.clipboard.writeText(url); } catch { /* niente clipboard */ }
      setStatus(`In ascolto pubblico su ${url} — link copiato`);
    } catch (e) { setStatus(e?.response?.data?.detail || 'Pubblicazione fallita'); }
  };
  const unpublishById = async (id) => {
    try {
      await frequenciesAPI.unpublish(id);
      loadDrafts();
      if (id === trackId) setTrackStatus('draft');
      setStatus('Traccia riportata in bozza: il link pubblico non risponde più');
    } catch { setStatus('Errore'); }
  };
  const copyPublicLink = async (slug) => {
    const url = `${window.location.origin}/frequenze/${slug}`;
    try { await navigator.clipboard.writeText(url); setStatus('Link copiato: ' + url); }
    catch { setStatus(url); }
  };

  const publishTrack = async () => {
    if (!trackId) return;
    await save();
    await publishById(trackId);
  };
  const unpublishTrack = () => unpublishById(trackId);

  const resetSession = () => {
    if (!layers.length) return;
    stopSession();
    setAsk({
      title: 'Svuotare la sessione?',
      msg: `Rimuove tutte le tracce dalla linea del tempo. Non si può annullare.`,
      opts: [['Sì, svuota', () => {
        setLayers([]); setPhases([]); setTrackId(null); setTitle(''); setIntent(null);
        setTrackStatus('draft'); setTrackSlug(null); setVoiceDuck(false);
        if (qs.get('bozza')) navigate('/sound/crea', { replace: true });
        setStatus('Sessione svuotata');
      }]],
    });
  };

  /* ── durata: riadatta o mantieni ── */
  const prevDurRef = useRef(duration);
  const onDurationChange = (mins) => {
    const newD = Math.max(60, mins * 60), oldD = prevDurRef.current;
    setDurationMin(mins);
    if (!layers.length || oldD === newD) { prevDurRef.current = newD; return; }
    stopSession();
    const rescale = () => {
      const k = newD / oldD;
      setLayers((ls) => ls.map((l) => ({
        ...l, start: Math.min(newD, l.start * k),
        end: Math.max(Math.min(newD, l.start * k) + 0.5, Math.min(newD, l.end * k)),
      })));
      setPhases((ps) => ps.map((p) => ({ ...p, t: Math.min(newD, p.t * k) })));
      setStatus(`Fasi riadattate a ${fmt(newD)}`);
    };
    const clamp = () => {
      setLayers((ls) => ls.map((l) => ({
        ...l, end: Math.min(l.end, newD), start: Math.min(l.start, newD - 1),
      })));
      setPhases((ps) => ps.filter((p) => p.t <= newD));
      setStatus(`Durata aggiornata a ${fmt(newD)}`);
    };
    setAsk({
      title: 'Durata cambiata',
      msg: `Come vuoi applicare la nuova durata di ${mins} min alla sessione?`,
      opts: [['Riadatta in proporzione', rescale], ['Mantieni le posizioni', clamp]],
    });
    prevDurRef.current = newD;
  };

  /* ── drag generico (barre, maniglie, fasi) ── */
  const dragX = (e, laneEl, cb) => {
    e.preventDefault(); e.stopPropagation();
    const r = laneEl.getBoundingClientRect();
    let last = e.clientX;
    const move = (ev) => { const dx = (ev.clientX - last) / r.width; last = ev.clientX; cb(dx); };
    const up = () => {
      window.removeEventListener('pointermove', move);
      window.removeEventListener('pointerup', up);
    };
    window.addEventListener('pointermove', move);
    window.addEventListener('pointerup', up);
  };

  /* ── pezzi di UI ── */
  const gstep = duration <= 300 ? 60 : duration <= 900 ? 120 : 300;
  const liveCount = liveKeys.length;

  const parseT = (s) => {
    s = (s || '').trim();
    if (/^\d+:\d{1,2}$/.test(s)) { const [m, x] = s.split(':'); return +m * 60 + +x; }
    const v = parseFloat(s);
    return isNaN(v) ? null : v;
  };

  const renderCard = (entry, idx) => {
    const key = `${curTab}:${idx}`;
    const live = liveCardsRef.current[key];
    const g = entry.g;
    const body = (entry.body || '').replace(/\n+/g, ' ').trim();
    // poche righe in primo piano OVUNQUE (anche in Guida): il resto
    // vive nel popup Approfondisci — e il taglio chiude la frase
    const limit = entry.info ? 220 : 150;
    let clamped = body.length > limit;
    let shown = body;
    if (clamped) {
      const cut = body.slice(0, limit);
      const dot = cut.lastIndexOf('. ');
      shown = dot > limit * 0.4 ? cut.slice(0, dot + 1)
        : `${cut.slice(0, cut.lastIndexOf(' ')).trim()}…`;
    }
    return (
      <div key={key} className={`card${live ? ' playing' : ''}${g ? ` g${g}` : ''}`}>
        <div className="head">
          <h3>{entry.t}</h3>
          {g && <span className={`badge ${g}`}>{g}</span>}
        </div>
        {entry.hz && <div className="hz">{entry.hz}</div>}
        {entry.uso && <div className="uso">{entry.uso}</div>}
        {entry.cfg && <div className="listen">{LISTEN[entry.cfg.method] || ''}</div>}
        <div className="body">{shown}</div>
        {(clamped || entry.full) && (
          <button type="button" className="readmore"
            onClick={() => setLearn({ title: entry.t, body: entry.full || entry.body, cta: !canCompose })}>
            Approfondisci
          </button>
        )}
        {live && live.sweepTo != null && (
          /* ONDA 1 — il tragitto e' un'informazione, non un effetto
             nascosto: chi ascolta deve sapere che il battito si sta
             muovendo, e dove sta andando. Sparisce se prende il
             comando col campo qui sotto. */
          <div className="cardsweep" data-testid="fq-card-sweep">
            <span className="cs-dot" aria-hidden />
            in movimento verso {String(live.sweepTo).replace('.', ',')} Hz
          </div>
        )}
        {live && (
          <div className="livectl" style={{ display: 'flex' }}>
            <label className="lbl" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              volume
              <input type="range" min="0" max="0.6" step="0.01" defaultValue={live.gain}
                onChange={(e2) => live.setGain(+e2.target.value)} style={{ flex: 1 }} />
            </label>
            <label className="lbl" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              {live.method === 'tone' ? 'frequenza' : 'battito'}
              <input type="number" step={live.method === 'tone' ? 1 : 0.5}
                defaultValue={live.method === 'tone' ? live.carrier : live.beat}
                onChange={(e2) => {
                  const v = +e2.target.value;
                  if (isNaN(v)) return;
                  if (live.method === 'tone') { live.setCarrier(v); return; }
                  live.setBeat(v);
                  // ONDA 1 — setBeat ferma il tragitto DENTRO il motore:
                  // senza questo risveglio la scheda continuerebbe a
                  // dire «in movimento verso...» a comando gia' preso.
                  // (`handles` vive dentro toggleCard: qui la mappa e'
                  // quella del ref, o e' un ReferenceError silenzioso.)
                  setLiveKeys(Object.keys(liveCardsRef.current));
                }}
                style={{ width: 70 }} /> Hz
            </label>
          </div>
        )}
        {entry.cfg && (
          /* SP-bis (decisione founder 19/8): le frequenze si ascoltano
             tutti. Resta professionale COMPORRE: «+ sessione» porta la
             frequenza nella linea del tempo, e quella e' un'altra cosa. */
          <div className="foot">
            <button type="button" className="live" data-testid={`fq-card-live-${idx}`}
              onClick={guard(() => toggleCard(key, entry))}>
              {live ? 'Ferma' : 'Ascolta'}
            </button>
            {canCompose && (
              <button type="button" className="add"
                onClick={() => addCardToSession(entry)}>+ sessione</button>
            )}
          </div>
        )}
      </div>
    );
  };

  const bibKeys = view === 'impara' ? LEARN_KEYS : SOUND_KEYS;
  const activeTab = bibKeys.includes(curTab) ? curTab : bibKeys[0];
  const hasGrades = (BIB[activeTab] || []).some((e) => e.g);

  // la barra delle tab e' la stessa per la biblioteca e per la Guida
  const tabsBar = (
    <div className="tabs">
      <div className="tabgroup">
        <div className="tabgroup-row">
          {bibKeys.map((k) => (
            <button key={k} type="button" title={CAT_HINT[k] || undefined}
              className={`tab ${view === 'impara' ? 'tab-learn' : 'tab-sound'}${activeTab === k ? ' on' : ''}`}
              onClick={() => setCurTab(k)}>
              {k}
            </button>
          ))}
        </div>
      </div>
    </div>
  );

  // dalla Guida si torna sempre alla biblioteca — mai a Crea.
  // Un solo navigate (push): cambio di vista vero, il back torna alla Guida.
  const goExplore = (cat) => {
    navigate(`/sound/esplora?categoria=${CAT_SLUG[cat] || ''}`);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const layerLabel = (l) => {
    if (l.kind === 'voice') {
      return `🎙 ${l.name} · ${(VOICE_PRESETS[l.fx] || VOICE_PRESETS.natural).label}`;
    }
    if (l.kind === 'audio') return `♫ ${l.name}`;
    if (l.method === 'tone') return `${l.name} · ${l.carrier} Hz`;
    const f = l.f0 === l.f1 ? `${l.f0} Hz` : `${l.f0}→${l.f1} Hz`;
    return `${l.name} · ${METHOD_LABELS[l.method]} · ${f}`;
  };

  const renderRow = (l) => (
    <div key={l.id} className={`row${l.mute ? ' muted' : ''}`}>
      <div className="meta">
        <div className="top">
          <input className="name" type="text" value={l.name}
            onChange={(e) => patchLayer(l.id, { name: e.target.value })} />
          <button type="button" className="ghost" onClick={() => removeLayer(l.id)}>×</button>
        </div>
        <div className="ctrls">
          <span className="lbl" title="Volume di questo livello nel mix">volume</span>
          <input className="sl vol" type="range" min="0" max="1" step="0.01" value={l.gain}
            onChange={(e) => patchLayer(l.id, { gain: +e.target.value })} />
          <span className="val v1">{Math.round(l.gain * 100)}%</span>
        </div>
        {/* FV6 — la voce ha lo STESSO specchietto degli altri suoni:
            entra a / esce a. Il taglio della registrazione si decide
            una volta sola nel leggio, qui sopra. */}
        <div className="ctrls timerow">
          <span className="lbl" title="Secondo in cui il suono entra">entra a</span>
          <input className="mini t-in" type="text" defaultValue={fmt(l.start)} key={`in${l.id}-${Math.round(l.start)}`}
            onBlur={(e) => { const v = parseT(e.target.value); if (v !== null) patchLayer(l.id, { start: Math.max(0, Math.min(v, l.end - 0.5)) }); }} />
          <span className="lbl" title="Secondo in cui il suono esce">esce a</span>
          <input className="mini t-out" type="text" defaultValue={fmt(l.end)} key={`out${l.id}-${Math.round(l.end)}`}
            onBlur={(e) => { const v = parseT(e.target.value); if (v !== null) patchLayer(l.id, { end: Math.max(l.start + 0.5, Math.min(v, duration)) }); }} />
          <span className="lbl dur-tot">({fmt(l.end - l.start)})</span>
        </div>
        {l.kind === 'voice' ? (
          <div className="ctrls r3">
            <select className="minisel" value={l.fx}
              title={(VOICE_PRESETS[l.fx] || VOICE_PRESETS.natural).hint}
              onChange={(e) => patchLayer(l.id, { fx: e.target.value })}>
              {Object.entries(VOICE_PRESETS).map(([k, p]) => (
                <option key={k} value={k}>{p.label}</option>
              ))}
            </select>
            <span className="lbl" title="Quanto effetto sopra la voce pulita">effetto</span>
            <input className="sl vol" type="range" min="0" max="1" step="0.05"
              value={l.fx_amount ?? 0.6}
              onChange={(e) => patchLayer(l.id, { fx_amount: +e.target.value })} />
            <span className="val v1">{Math.round((l.fx_amount ?? 0.6) * 100)}%</span>
            <button type="button" className={`chip m${l.mute ? ' on' : ''}`}
              onClick={() => patchLayer(l.id, { mute: !l.mute })}>muto</button>
            <span className="val" title="Silenzi ai bordi, fruscio nelle pause e volume sono sistemati da soli all'ascolto. Il taglio della registrazione si imposta nel riquadro «La tua voce», qui sopra.">
              🎙 tua voce · pulita
              {((voiceById[l.asset_id]?.trim_start || 0)
                + (voiceById[l.asset_id]?.trim_end || 0)) > 0 ? ' · tagliata' : ''}
            </span>
          </div>
        ) : l.kind === 'audio' ? (
          <div className="ctrls r3">
            <button type="button" className={`chip${l.loop !== false ? ' on' : ''}`}
              title="La base ricomincia da capo finche' la barra dura"
              onClick={() => patchLayer(l.id, { loop: l.loop === false })}>loop</button>
            <button type="button" className={`chip m${l.mute ? ' on' : ''}`}
              onClick={() => patchLayer(l.id, { mute: !l.mute })}>muto</button>
            <span className="val">base della libreria</span>
          </div>
        ) : (
          <>
        <div className="ctrls r3">
          <select className="minisel" value={l.method}
            onChange={(e) => patchLayer(l.id, { method: e.target.value })}>
            {Object.entries(METHOD_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
          {l.method === 'noise' ? (
            <select className="minisel" value={l.color || 'pink'}
              data-testid="fq-layer-color" title="Il colore del soffio"
              onChange={(e) => patchLayer(l.id, { color: e.target.value })}>
              {Object.entries(NOISE_COLORS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
          ) : (
            <select className="minisel" value={l.timbre}
              onChange={(e) => patchLayer(l.id, { timbre: e.target.value })}>
              <option value="pure">puro</option><option value="warm">caldo</option>
            </select>
          )}
          <button type="button" className={`chip m${l.mute ? ' on' : ''}`}
            onClick={() => patchLayer(l.id, { mute: !l.mute })}>muto</button>
        </div>
        <div className="ctrls r4">
          {/* ONDA 4 — il bordone non ha battito: come il tono puro ha
              solo la sua nota (la quinta e la terza le mette il motore) */}
          {(l.method === 'tone' || l.method === 'drone') ? (
            <>
              <span className="lbl">frequenza</span>
              <input className="mini" type="number" min="20" max="2000" step="1" value={l.carrier}
                onChange={(e) => { const v = +e.target.value; if (!isNaN(v)) patchLayer(l.id, { carrier: v }); }} />
              <span className="lbl">Hz</span>
            </>
          ) : (
            <>
              {l.method !== 'noise' && (
                <>
                  <span className="lbl" title="Il tono udibile che trasporta il battito">
                    {l.method === 'bil' ? 'tono' : 'portante'}
                  </span>
                  <input className="mini" type="number" min="40" max="800" step="5" value={l.carrier}
                    onChange={(e) => { const v = +e.target.value; if (!isNaN(v)) patchLayer(l.id, { carrier: v }); }} />
                  <span className="lbl">Hz</span>
                </>
              )}
              <span className="lbl" title="Frequenza del battito a inizio barra">
                {l.method === 'bil' ? 'alternanza' : 'battito da'}
              </span>
              <input className="mini" type="number" min="0.05" max="60" step="0.5" value={l.f0}
                onChange={(e) => { const v = +e.target.value; if (!isNaN(v)) patchLayer(l.id, l.method === 'bil' ? { f0: v, f1: v } : { f0: v }); }} />
              {l.method !== 'bil' && (
                <>
                  <span className="lbl" title={l.curve === 'wave'
                    ? "L'altro estremo della marea: il battito va qui e torna"
                    : 'Frequenza a fine barra: uguale = ferma, diversa = discesa/salita'}>a</span>
                  <input className="mini" type="number" min="0.05" max="60" step="0.5" value={l.f1}
                    onChange={(e) => { const v = +e.target.value; if (!isNaN(v)) patchLayer(l.id, { f1: v }); }} />
                  <span className="lbl">Hz</span>
                  <select className="minisel" value={l.curve}
                    onChange={(e) => {
                      const curve = e.target.value;
                      // ONDA 2 — scegliendo la marea il periodo deve
                      // esistere subito: senza, il campo nascerebbe vuoto
                      patchLayer(l.id, curve === 'wave' && l.period == null
                        ? { curve, period: WAVE_PERIOD_SEC } : { curve });
                    }}>
                    {Object.entries(CURVE_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                  </select>
                  {l.curve === 'wave' && (
                    <>
                      <span className="lbl" title="Quanto dura un giro completo: andata e ritorno">ogni</span>
                      <input className="mini" type="number" min="2" max="600" step="5"
                        data-testid="fq-layer-period"
                        value={l.period ?? WAVE_PERIOD_SEC}
                        onChange={(e) => { const v = +e.target.value; if (!isNaN(v)) patchLayer(l.id, { period: v }); }} />
                      <span className="lbl">s</span>
                    </>
                  )}
                </>
              )}
            </>
          )}
          <button type="button" className={`chip${l.breath ? ' on' : ''}`}
            title="Micro-oscillazione lenta del volume: toglie la fissità da «segnale di prova»"
            onClick={() => patchLayer(l.id, { breath: !l.breath })}>respiro</button>
        </div>
          </>
        )}
      </div>
      <div className="lane" ref={(el) => { if (el) l._laneEl = el; }}>
        <div className="grid">
          {Array.from({ length: Math.max(0, Math.ceil(duration / gstep) - 1) }, (_, i) => (
            <i key={i} style={{ left: `${((i + 1) * gstep / duration) * 100}%` }} />
          ))}
        </div>
        <div className={l.kind === 'voice' ? 'bar voice' : 'bar'}
          style={{ left: `${(l.start / duration) * 100}%`, width: `${((l.end - l.start) / duration) * 100}%` }}
          title={`${fmt(l.start)} → ${fmt(l.end)}`}
          onPointerDown={(e) => {
            if (e.target.classList.contains('handle')) return;
            const len = l.end - l.start;
            dragX(e, l._laneEl, (dx) => {
              const start = Math.max(0, Math.min(duration - len, l.start + dx * duration));
              l.start = start; l.end = start + len;
              patchLayer(l.id, { start: l.start, end: l.end });
            });
          }}>
          <div className="handle l" onPointerDown={(e) => dragX(e, l._laneEl, (dx) => {
            const v = Math.max(0, Math.min(l.end - 0.5, l.start + dx * duration));
            l.start = v; patchLayer(l.id, { start: v });
          })} />
          <b>{layerLabel(l)}</b>
          <div className="handle r" onPointerDown={(e) => dragX(e, l._laneEl, (dx) => {
            const v = Math.max(l.start + 0.5, Math.min(duration, l.end + dx * duration));
            l.end = v; patchLayer(l.id, { end: v });
          })} />
        </div>
        {playing && (
          <div className="playhead" style={{ left: `${Math.max(0, (elapsed / duration) * 100)}%` }} />
        )}
      </div>
    </div>
  );

  /* ── SP1 — cancello sulle viste professionali. Esplora e Impara
     sono pubbliche; Crea e Le mie tracce chiedono il login e POI
     riportano qui (?next=, meccanismo LN0). Replica anche il gate
     email-verificata di ProtectedRoute. */
  const needsAuth = view === 'create' || view === 'mine';
  if (needsAuth && authLoading) {
    return (
      <div className="fqz" data-testid="fqz-root">
        <main><section className="bib"><p>…</p></section></main>
      </div>
    );
  }
  if (needsAuth && !isAuthenticated) {
    const next = encodeURIComponent(location.pathname + location.search);
    return <Navigate to={`/accedi?next=${next}`} replace />;
  }
  if (needsAuth && user && user.role !== 'system_admin' && user.email_verified === false) {
    return <Navigate to="/verify-email-required" replace />;
  }

  /* ─────────────────────────── RENDER ─────────────────────────── */
  return (
    <div className="fqz" data-testid="fqz-root">
      {/* DN1/DN2/DN4 — testata condivisa del mondo Sound: marchio della
          marca (che e' anche la via di casa), passerella e omino. Gli
          strumenti di QUESTA vista viaggiano come extra. */}
      <SoundTopbar firma="Sound" qui="/sound" extra={<>
        {/* SF — sempre a portata, in ogni vista e per chiunque: le
            controindicazioni non si leggono una volta sola */}
        <SafetyButton onClick={openReview} />
        {/* DN8 — «Le mie tracce» parla come le altre voci della testata.
            Il «Gestionale» non e' piu' qui: vive nel menu dell'omino
            («Il tuo gestionale»), che ogni mondo Aurya ha ormai in
            alto a destra. */}
        {canCompose && (
          <button type="button" className={`tbpill${view === 'mine' ? ' on' : ''}`}
            data-testid="fqz-mine" title="Tutte le tracce che hai creato"
            onClick={() => setView('mine')}>
            <span aria-hidden>♫</span>
            Le mie tracce
          </button>
        )}
      </>} />
      <header>
        <div>
          <h1>Aurya <em>Sound</em></h1>
          <div className="sub">Esperienze sonore progettate per accompagnare diversi stati di presenza.</div>
        </div>
        <div className="viewswitch">
          <button type="button" className={`vbtn${view === 'explore' ? ' on' : ''}`}
            onClick={() => setView('explore')}>Esplora</button>
          {canCompose && (
            <button type="button" className={`vbtn${view === 'create' ? ' on' : ''}`}
              onClick={() => setView('create')}>
              Crea {layers.length > 0 && <span className="vcount">{layers.length}</span>}
            </button>
          )}
          <button type="button" className={`vbtn${view === 'impara' ? ' on' : ''}`}
            onClick={() => setView('impara')}>Impara</button>
        </div>
      </header>

      <main>
        {/* SF — dove si ascolta, la riga sta a vista; nella Guida no:
            lì il tema è trattato per esteso, e un cartello sopra un
            testo che spiega la stessa cosa è solo rumore. */}
        {view !== 'impara' && <SafetyLine onOpen={openReview} />}
        {(view === 'explore' || view === 'impara') && (
          <section className="bib">
            {view === 'explore' && canCompose && (
              <div className="worldswitch" data-testid="fq-worldswitch">
                <button type="button" className={`wbtn${world === 'freq' ? ' on' : ''}`}
                  onClick={() => setWorld('freq')}>Frequenze</button>
                <button type="button" data-world="sound" className={`wbtn${world === 'sound' ? ' on' : ''}`}
                  onClick={() => setWorld('sound')}>Suoni</button>
              </div>
            )}
            <h2>
              {view === 'impara' ? 'Le fondamenta'
                : world === 'sound' ? 'Le basi sonore' : 'Esplora le frequenze'}
            </h2>
            {view === 'impara' ? (
              <>
                <p className="gd-hero-sub">Capire il suono prima di usarlo.</p>
                <p>Una guida essenziale per orientarti tra onde cerebrali, stimolazione ritmica, frequenze e metodi di ascolto. Parti dalle basi, approfondisci ciò che ti interessa e poi torna alla biblioteca per ascoltare.</p>
              </>
            ) : world === 'sound' ? (
              <p className="soundlead">Le basi sonore sono la tela su cui posare le frequenze — e potrai sovrapporne più di una. Le sceglierai qui e le combinerai nella sessione, esattamente come le frequenze.</p>
            ) : (
              <p>Esplora frequenze, vibrazioni e metodi di ascolto. Scopri cosa sono, cosa sappiamo davvero su di esse e come vengono utilizzate nelle pratiche sonore. Puoi ascoltarle singolarmente, combinarle e portarle nelle tue sessioni.</p>
            )}

            {view === 'impara' ? (
              /* Le fondamenta: non una griglia di schede, una guida che
                 accompagna dal fenomeno fino all'invito a esplorare. */
              <>
                {tabsBar}
                {activeTab !== 'Glossario' && (
                  <div className="gd-time">Tempo di lettura · circa 5 min</div>
                )}
                <GuidaView tab={activeTab} onExplore={goExplore} onLearn={setLearn}
                  proCta={!canCompose} />
              </>
            ) : view === 'explore' && world === 'sound' ? (
              <>
                <div className="tabs">
                  <div className="tabgroup">
                    <div className="tabgroup-row">
                      {SOUND_CATS.map((c) => (
                        <button key={c} type="button"
                          className={`tab tab-sound${soundCat === c ? ' on' : ''}`}
                          onClick={() => setSoundCat(c)}>{c}</button>
                      ))}
                    </div>
                  </div>
                </div>
                <div className="tabhint" data-testid="fq-sound-hint">
                  {SOUND_HINT[soundCat]}
                </div>
                {(() => {
                  // ordine stabile e prevedibile: alfabetico con i numeri
                  // letti come numeri, cosi' «1 · Radice» apre la serie
                  const inCat = sounds
                    .filter((s) => s.category === soundCat.toLowerCase())
                    .sort((a, b) => a.title.localeCompare(b.title, 'it', { numeric: true }));
                  return (
                    <>
                      {inCat.length > 0 ? (
                        <div className="cards" data-testid="fq-sound-cards">
                          {inCat.map((s) => (
                            <div key={s.id} className={`card${previewingId === s.id ? ' playing' : ''}`}>
                              <div className="head"><h3>{s.title}</h3></div>
                              <div className="hz">{fmt(s.duration_sec || 0)} · {(s.size_bytes / 1048576).toFixed(1)} MB</div>
                              <div className="listen">🔊 Base sonora · va in loop sotto le frequenze</div>
                              <div className="foot">
                                {isSystemAdmin && (
                                  <button type="button" className="ghost" title="Elimina dalla libreria"
                                    onClick={() => removeSound(s)}>×</button>
                                )}
                                <button type="button" className="live"
                                  onClick={() => toggleSoundPreview(s)}>
                                  {soundLoadingId === s.id ? <span className="prep">◌</span>
                                    : previewingId === s.id ? 'Ferma' : 'Ascolta'}
                                </button>
                                <button type="button" className="add"
                                  onClick={() => addSoundToSession(s)}>+ sessione</button>
                              </div>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <div className="soundsoon" data-testid="fq-soundsoon">
                          <div className="soundsoon-ic">♫</div>
                          <div>
                            <strong>{sounds.length ? `Ancora nessuna base in ${soundCat}` : 'Libreria in arrivo'}</strong>
                            <span>Le basi sonore curate di Aurya, pronte da combinare con le frequenze. Le tracce si compongono solo con i suoni della piattaforma.</span>
                          </div>
                        </div>
                      )}
                      {isSystemAdmin && (
                        <div className="protrow" data-testid="fq-sound-upload">
                          <span className="tag">Regia piattaforma</span>
                          <button type="button" className="prot" disabled={uploading}
                            onClick={() => soundFileRef.current?.click()}>
                            {uploading ? 'Carico…' : `+ Carica una base in ${soundCat}`}
                          </button>
                          <span className="lbl" style={{ fontSize: 10 }}>
                            mp3 · m4a · ogg · wav, max 60MB — solo materiale licenziato o CC0
                          </span>
                          <input ref={soundFileRef} type="file" accept="audio/*" hidden
                            onChange={(e) => { uploadSound(e.target.files[0]); e.target.value = ''; }} />
                        </div>
                      )}
                      {status && <p className="soundlead" style={{ marginTop: 10 }}>{status}</p>}
                    </>
                  );
                })()}
              </>
            ) : (
              <>
                {liveCount > 0 && view === 'explore' && (
                  <div className="livebar on">
                    <span>{liveCount} in riproduzione — le frequenze si combinano</span>
                    <span className="spacer" style={{ flex: 1 }} />
                    {canCompose && (
                      <button type="button" onClick={composeAllLive}>+ tutte alla sessione</button>
                    )}
                    <button type="button" onClick={stopAllCards}>Ferma tutto</button>
                  </div>
                )}
                {tabsBar}
                {CAT_HINT[activeTab] && (
                  <div className="tabhint">{CAT_HINT[activeTab]}</div>
                )}
                {hasGrades && (
                  <div className="legend">
                    <span className="la" title="Il fenomeno è ben documentato dalla ricerca scientifica."><b>A</b> Evidenza solida</span>
                    <span className="lb" title="Esistono risultati interessanti, ma le evidenze non sono ancora conclusive."><b>B</b> Ricerca in corso</span>
                    <span className="lc" title="L'associazione appartiene soprattutto alla tradizione o alla cultura, senza una dimostrazione fisiologica consolidata."><b>C</b> Tradizione e simbolismo</span>
                    <button type="button" className="howto" data-testid="fqz-howto"
                      onClick={() => setLearn({ title: 'Come leggere questa biblioteca', body: HOWTO_BODY })}>
                      Come leggere questa biblioteca
                    </button>
                  </div>
                )}
                {CAT_INTRO[activeTab] && (
                  <div className="catintro" data-testid="fqz-catintro">
                    <b>{CAT_INTRO[activeTab].t}</b>
                    <p>{CAT_INTRO[activeTab].p}</p>
                  </div>
                )}
                {activeTab === 'Metodi' && (
                  <div className="methodkey">
                    <div className="mk-line"><b>Binaurale</b> due toni diversi, uno per orecchio → il battito lo percepisce il sistema uditivo</div>
                    <div className="mk-line"><b>Monaurale</b> due toni miscelati → il battito è già nel segnale</div>
                    <div className="mk-line"><b>Isocronico</b> un tono modulato → pulsazione molto evidente</div>
                    <div className="mk-line"><b>Bilaterale</b> il suono alterna destra e sinistra → movimento nello spazio</div>
                    <div className="mk-line"><b>Soffio</b> un rumore continuo modulato → ritmo immerso nel paesaggio</div>
                    <div className="mk-line"><b>Tono puro</b> una frequenza stabile → nessuna pulsazione</div>
                  </div>
                )}
                {(() => {
                  // gruppi tematici (Altre frequenze): titoli discreti, e
                  // l'INDICE ORIGINALE resta la chiave delle schede in
                  // ascolto — mai rinumerare, o gli handle live si perdono
                  const list = (BIB[activeTab] || []).map((e, i) => [e, i]);
                  if (!list.some(([e]) => e.group)) {
                    return <div className="cards">{list.map(([e, i]) => renderCard(e, i))}</div>;
                  }
                  const groups = [];
                  list.forEach(([e, i]) => {
                    const g = e.group || '';
                    const last = groups[groups.length - 1];
                    if (last && last.name === g) last.items.push([e, i]);
                    else groups.push({ name: g, items: [[e, i]] });
                  });
                  return groups.map((grp) => (
                    <div key={grp.name} className="cardgroup">
                      <div className="grouptitle"><span>{grp.name}</span></div>
                      <div className="cards">
                        {grp.items.map(([e, i]) => renderCard(e, i))}
                      </div>
                    </div>
                  ));
                })()}
                {!canCompose && view === 'explore' && (
                  /* SP3 — chi ha scorso tutta la biblioteca e' interessato:
                     un solo blocco, in fondo, mai sulle card */
                  <div className="probox" data-testid="fqz-cta-explore">
                    <b>Vuoi andare oltre l'esplorazione?</b>
                    <p>Ascoltare è solo l'inizio: gli operatori combinano frequenze, metodi
                      e la propria voce in una sessione, e la pubblicano con un link.</p>
                    <button type="button" className="pro-cta" onClick={() => navigate(PRO_ENTRY)}>
                      Scopri Aurya Sound per operatori →
                    </button>
                  </div>
                )}
              </>
            )}
          </section>
        )}

        {view === 'mine' && (
          <section className="bib" data-testid="fq-mine">
            <h2>Le mie tracce</h2>
            <p>Tutto quello che hai composto: le bozze restano tue, le pubblicate hanno un link d'ascolto da condividere ovunque.</p>
            {drafts.length === 0 ? (
              <div className="emptycreate" style={{ marginTop: 14 }}>
                <p>Ancora nessuna traccia. Vai su <b>Crea</b>, parti da un protocollo e salva la tua prima sessione.</p>
              </div>
            ) : (
              <div className="cards">
                {drafts.map((d) => (
                  <div key={d.id} className={`card${d.status === 'published' ? ' playing' : ''}`}>
                    <div className="head">
                      <h3>{d.title}</h3>
                      <span className="badge" style={d.status === 'published'
                        ? { color: 'var(--water)', borderColor: 'var(--water)' }
                        : { color: 'var(--dimmer)', borderColor: 'var(--line)' }}>
                        {d.status === 'published' ? 'PUBBLICA' : 'BOZZA'}
                      </span>
                    </div>
                    <div className="hz">
                      {fmt(d.duration_sec || 0)} · {d.layers_count} {d.layers_count === 1 ? 'livello' : 'livelli'}
                      {d.status === 'published' && ` · ${d.plays_total || 0} ascolti`}
                    </div>
                    {d.status === 'published' && d.slug && (
                      <div className="listen">/frequenze/{d.slug}</div>
                    )}
                    <div className="foot" style={{ flexWrap: 'wrap', gap: 6 }}>
                      <button type="button" className="ghost" title="Elimina"
                        onClick={() => removeDraft(d.id, d.title)}>×</button>
                      {d.status === 'published' && d.slug && (
                        <button type="button" className="add"
                          onClick={() => copyPublicLink(d.slug)}>Copia link</button>
                      )}
                      {d.status === 'published' ? (
                        <button type="button" className="add"
                          onClick={() => unpublishById(d.id)}>Ritira</button>
                      ) : (
                        <button type="button" className="add"
                          onClick={() => publishById(d.id)}>Pubblica</button>
                      )}
                      <button type="button" className="live"
                        onClick={() => openDraft(d.id)}>Apri</button>
                    </div>
                  </div>
                ))}
              </div>
            )}
            {status && <p className="soundlead" style={{ marginTop: 12 }}>{status}</p>}
          </section>
        )}

        {view === 'create' && (
          <section>
            <div className="createbar">
              <button type="button" className="cb-play" data-testid="fq-play"
                disabled={!layers.length}
                onClick={() => (playing ? stopSession() : playGuarded(0))}>
                {preparing ? <><span className="prep">◌</span> Preparo…</>
                  : playing ? '⏸ Pausa' : '▶ Ascolta sessione'}
              </button>
              <button type="button" className="cb-reset" disabled={!layers.length}
                onClick={resetSession}>Reset</button>
              {/* Su telefono i quattro campi occupavano quattro righe piene:
                  ora stanno dietro un tocco e la barra resta una striscia.
                  Su schermo largo il CSS li rimette in linea (display:contents). */}
              <button type="button" className="cb-opt" data-testid="fq-setup"
                aria-expanded={setupOpen}
                title="Titolo, durata, apertura e chiusura della sessione"
                onClick={() => setSetupOpen((o) => !o)}>
                {setupOpen ? '▴' : '▾'} {durationMin} min
              </button>
              <div className={`cb-collapse${setupOpen ? ' open' : ''}`}>
                <div className="cb-fields">
                  <label title="Nome della bozza salvata nel tuo account">titolo
                    <input type="text" value={title} style={{ width: 130 }}
                      placeholder="La mia sessione"
                      onChange={(e) => setTitle(e.target.value)} />
                  </label>
                  <label title="Lunghezza totale della sessione">durata
                    <input type="number" value={durationMin} min="1" max="60" step="1"
                      onChange={(e) => { const v = +e.target.value; if (!isNaN(v) && v > 0) onDurationChange(v); }} /> min
                  </label>
                  <label title="Dissolvenza iniziale in secondi">apertura
                    <input type="number" value={fadeIn} min="0" max="120" step="1"
                      onChange={(e) => setFadeIn(+e.target.value || 0)} /> s
                  </label>
                  <label title="Dissolvenza finale in secondi">chiusura
                    <input type="number" value={fadeOut} min="0" max="120" step="1"
                      onChange={(e) => setFadeOut(+e.target.value || 0)} /> s
                  </label>
                </div>
              </div>
              {/* salva/pubblica restano sempre a vista, anche a campi chiusi */}
              <div className="cb-export">
                  <span className="status">{status}</span>
                  <button type="button" data-testid="fq-save" className="cb-save"
                    disabled={saving || !layers.length}
                    onClick={save}>{saving ? 'Salvo…' : trackId ? 'Aggiorna bozza' : 'Salva bozza'}</button>
                  {trackId && (trackStatus === 'published' ? (
                    <button type="button" data-testid="fq-unpublish"
                      title={trackSlug ? `Pubblica su /frequenze/${trackSlug}` : ''}
                      style={{ borderColor: 'var(--water)', color: 'var(--water)' }}
                      onClick={unpublishTrack}>● Pubblica­ta — ritira</button>
                  ) : (
                    <button type="button" data-testid="fq-publish" className="primary"
                      disabled={!layers.length}
                      onClick={publishTrack}>Pubblica</button>
                  ))}
              </div>
              {layers.length > 0 && (
                <div className="seekwrap" style={{ display: 'flex' }}>
                  <span className="seek-cur">{fmt(elapsed)}</span>
                  <div className="seekbar" title="Clicca per spostarti nella sessione"
                    onClick={(e) => {
                      const r = e.currentTarget.getBoundingClientRect();
                      seekTo(Math.max(0, Math.min(1, (e.clientX - r.left) / r.width)) * duration);
                    }}>
                    <div className="seek-fill" style={{ width: `${(elapsed / duration) * 100}%` }} />
                    <div className="seek-knob" style={{ left: `${(elapsed / duration) * 100}%` }} />
                  </div>
                  <span className="seek-tot">{fmt(duration)}</span>
                </div>
              )}
            </div>

            <div className="protrow createprot">
              <span className="tag">Parti da un protocollo pronto</span>
              <div style={{ display: 'flex', gap: 7, flexWrap: 'wrap' }}>
                {Object.entries(PROTOCOLLI).map(([name, p]) => (
                  <button key={name} type="button" className="prot" title={p.ev}
                    data-testid={`fq-prot-${p.intent}`}
                    onClick={() => loadProtocol(name)}>
                    {name} <span className={`pbadge ${p.grade}`}>{p.grade}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* FV3 — il leggio: la tua voce dentro la sessione */}
            <div className="voicedesk" data-testid="fqz-voicedesk">
              <div className="vd-head">
                <span className="tag">🎙 La tua voce</span>
                <span className="vd-hint">
                  Registra brevi spezzoni, tagliali qui una volta sola e piazzali dove servono. Cuffie se la sessione è in ascolto.
                </span>
                {recState === 'rec' ? (
                  <button type="button" className="vd-rec on" onClick={stopRec}>
                    ■ Ferma · {fmt(recSecs)}
                  </button>
                ) : (
                  <button type="button" className="vd-rec" onClick={startRec}>
                    ● REC
                  </button>
                )}
              </div>
              {voiceClips.length > 0 && (
                <>
                  <div className="vd-tryrow">
                    <span className="lbl">prova gli spezzoni con</span>
                    <select className="minisel" value={prevFx}
                      title={(VOICE_PRESETS[prevFx] || {}).hint}
                      onChange={(e) => setPrevFx(e.target.value)}>
                      {Object.entries(VOICE_PRESETS).map(([k, p]) => (
                        <option key={k} value={k}>{p.label}</option>
                      ))}
                    </select>
                    <span className="vd-hint">{(VOICE_PRESETS[prevFx] || {}).hint}</span>
                  </div>
                  <div className="vd-clips">
                    {voiceClips.map((c) => (
                      <React.Fragment key={c.id}>
                      <div className={`vd-clip${voicePrevId === c.id ? ' playing' : ''}`}>
                        <input className="vd-name" type="text" defaultValue={c.title}
                          key={`${c.id}-${c.title}`}
                          onBlur={(e) => renameVoiceClip(c, e.target.value)} />
                        <span className="vd-dur"
                          title={(c.trim_start || c.trim_end)
                            ? `Registrazione intera ${fmt(c.duration_sec || 0)}, tagliata`
                            : 'Durata della registrazione'}>
                          {fmt(clipUseful(c))}
                        </span>
                        <button type="button" className="chip"
                          onClick={() => toggleVoicePreview(c)}>
                          {voicePrevLoading === c.id ? <span className="prep">◌</span>
                            : voicePrevId === c.id ? '■' : '▶'}
                        </button>
                        <button type="button"
                          className={`chip${trimOpen === c.id ? ' on' : ''}`}
                          title="Taglia i secondi di troppo all'inizio e alla fine di questa registrazione"
                          data-testid={`fq-trim-${c.id}`}
                          onClick={() => setTrimOpen(trimOpen === c.id ? null : c.id)}>
                          ✂ taglio{(c.trim_start || c.trim_end) ? ' ·' : ''}
                        </button>
                        <button type="button" className="add"
                          title="La piazza al punto del cursore"
                          onClick={() => addVoiceToSession(c)}>+ sessione</button>
                        <button type="button" className="ghost"
                          onClick={() => removeVoiceClip(c)}>×</button>
                      </div>
                      {trimOpen === c.id && (
                        <div className="vd-trim" data-testid="fq-trimrow">
                          <span className="lbl">togli dall'inizio</span>
                          <input className="mini" type="number" min="0" step="0.5"
                            value={c.trim_start || 0}
                            onChange={(e) => {
                              const v = +e.target.value;
                              if (!isNaN(v)) saveVoiceTrim(c, v, c.trim_end || 0);
                            }} />
                          <span className="lbl">togli dalla fine</span>
                          <input className="mini" type="number" min="0" step="0.5"
                            value={c.trim_end || 0}
                            onChange={(e) => {
                              const v = +e.target.value;
                              if (!isNaN(v)) saveVoiceTrim(c, c.trim_start || 0, v);
                            }} />
                          <span className="lbl">s</span>
                          <span className="vd-hint">
                            Restano {fmt(clipUseful(c))} di {fmt(c.duration_sec || 0)}.
                            Il file resta intero: puoi rimettere 0 quando vuoi.
                          </span>
                        </div>
                      )}
                      </React.Fragment>
                    ))}
                  </div>
                  {hasVoiceLayers && (
                    <label className="vd-duck">
                      <input type="checkbox" checked={voiceDuck}
                        onChange={(e) => setVoiceDuck(e.target.checked)} />
                      Abbassa le basi sotto la voce (consigliato)
                    </label>
                  )}
                </>
              )}
            </div>

            <div className="legend" style={{ marginTop: 14 }}>
              <span className="la" title="Il fenomeno è ben documentato dalla ricerca scientifica."><b>A</b> Evidenza solida</span>
              <span className="lb" title="Esistono risultati interessanti, ma le evidenze non sono ancora conclusive."><b>B</b> Ricerca in corso</span>
              <span className="lc" title="L'associazione appartiene soprattutto alla tradizione o alla cultura, senza una dimostrazione fisiologica consolidata."><b>C</b> Tradizione e simbolismo</span>
            </div>

            {layers.length > 0 ? (
              <div className="score" style={{ display: 'block' }}>
                <div className="helpstrip">
                  <b>Linea del tempo.</b> Ogni riga è un livello. Trascina la sua barra o scrivi «entra a / esce a» per decidere quando parte e finisce. <b>Battito da → a</b> è la discesa (valori uguali = frequenza ferma), la <b>curva</b> ne è la forma, la <b>portante</b> è il tono che la trasporta.
                </div>
                <div className="ruler" title="Clicca per ascoltare da questo punto"
                  style={{ cursor: 'pointer' }}
                  onClick={(e) => {
                    const r = e.currentTarget.getBoundingClientRect();
                    seekTo(Math.max(0, Math.min(1, (e.clientX - r.left) / r.width)) * duration);
                  }}>
                  {Array.from({ length: Math.floor(duration / gstep) + 1 }, (_, i) => (
                    <div key={i} className="tick" style={{ left: `${((i * gstep) / duration) * 100}%` }}>
                      <span>{fmt(i * gstep)}</span>
                    </div>
                  ))}
                </div>
                <div className="phases" title="Clicca per aggiungere una fase"
                  onClick={(e) => {
                    if (e.target !== e.currentTarget) return;
                    const r = e.currentTarget.getBoundingClientRect();
                    const t = ((e.clientX - r.left) / r.width) * duration;
                    setPhases((ps) => [...ps, { t, name: 'fase' }].sort((a, b) => a.t - b.t));
                  }}>
                  {phases.map((p, i) => (
                    <div key={i} className="phase" style={{ left: `${(p.t / duration) * 100}%` }}
                      onPointerDown={(e) => {
                        if (e.target.tagName === 'BUTTON') return;
                        const lane = e.currentTarget.parentElement;
                        dragX(e, lane, (dx) => {
                          setPhases((ps) => ps.map((x, j) => j === i
                            ? { ...x, t: Math.max(0, Math.min(duration, x.t + dx * duration)) } : x));
                        });
                      }}>
                      <span onDoubleClick={() => {
                        const name = window.prompt('Nome della fase', p.name);
                        if (name) setPhases((ps) => ps.map((x, j) => j === i ? { ...x, name } : x));
                      }}>{p.name}</span>
                      <button type="button" title="Rimuovi"
                        onClick={(e) => { e.stopPropagation(); setPhases((ps) => ps.filter((_, j) => j !== i)); }}>×</button>
                    </div>
                  ))}
                </div>
                <div>{layers.map(renderRow)}</div>
              </div>
            ) : (
              <div className="emptycreate" style={{ marginTop: 18 }}>
                <p>La tua sessione è vuota. Torna a <b>Esplora</b> per scegliere le frequenze, oppure parti da un <b>protocollo pronto</b> qui sopra.</p>
              </div>
            )}
            <p className="note">
              Il <b>binaurale</b> dà l'effetto solo in cuffia: dalle casse si sente comunque, ma resta un battimento fisico, non stimolazione binaurale. <b>Isocronico</b> e <b>monoaurale</b> portano il battito nel segnale — per grotta e aula usa questi.
              Timbro <b>caldo</b> più tollerabile del puro sulle sessioni lunghe; il <b>soffio</b> nasconde l'entrainment in un rumore rosa.
            </p>
          </section>
        )}
      </main>

      {!canCompose && (
        <footer className="fqzfoot" data-testid="fqz-foot">
          <a href="/">← Torna su Aurya</a>
          <a href="/blog">Magazine</a>
          <a href="/newsletter">La Lettera</a>
          <a href="/meditazioni">Meditazioni</a>
        </footer>
      )}

      {canCompose && view !== 'create' && layers.length > 0 && (
        <div className="sessionfoot">
          <span className="sf-dot">◆</span>
          <span className="sf-txt">La tua sessione · {layers.length} {layers.length === 1 ? 'livello' : 'livelli'} · {durationMin} min</span>
          <div className="spacer" style={{ flex: 1 }} />
          <button type="button" className="primary" onClick={() => setView('create')}>Vai a Crea →</button>
        </div>
      )}

      {/* SF — il sipario vive nel hook: si apre davanti al primo
          suono e su richiesta dal pulsante «Controindicazioni». */}
      {curtain}

      {/* dialogo conferme */}
      {ask && (
        <div className="gate">
          <div className="gatebox" style={{ maxWidth: 520 }}>
            <h2>{ask.title}</h2>
            <p>{ask.msg}</p>
            <div className="gatefoot" style={{ gap: 8, flexWrap: 'wrap' }}>
              {ask.opts.map(([label, fn], i) => (
                <button key={i} type="button" className={i === 0 ? 'primary' : undefined}
                  onClick={() => { setAsk(null); fn(); }}>{label}</button>
              ))}
              <button type="button" onClick={() => setAsk(null)}>Annulla</button>
            </div>
          </div>
        </div>
      )}

      {/* approfondimento scheda */}
      {learn && (
        <div className="gate" onClick={() => setLearn(null)}>
          <div className="gatebox learnbox" onClick={(e) => e.stopPropagation()}>
            <button type="button" className="learnclose" onClick={() => setLearn(null)}>×</button>
            <div className="learn-kicker">Approfondimento</div>
            <h2>{learn.title}</h2>
            <div className="learn-body">
              {/* i `full` della biblioteca sono HTML curato (tabelle):
                  contenuto statico del bundle, mai input utente */}
              {/^\s*</.test(learn.body || '') ? (
                <div dangerouslySetInnerHTML={{ __html: learn.body }} />
              ) : (learn.body || '').split(/\n\n+/).map((p, i) => <p key={i}>{p.replace(/\n/g, ' ')}</p>)}
            </div>
            {learn.cta && (
              /* SP3 — il momento di massima intenzione, la riga meno
                 invadente: solo visitatori, solo schede della biblioteca */
              <div className="proline" data-testid="fqz-cta-learn">
                Vuoi portarla dentro una tua sessione?{' '}
                <button type="button" onClick={() => navigate(PRO_ENTRY)}>
                  Scopri Aurya Sound per operatori →
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
