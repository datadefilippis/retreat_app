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
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { frequenciesAPI } from '../../api/frequencies';
import {
  METHOD_LABELS, CURVE_LABELS, startPreview, startCardLive,
} from './engine/synth';
import { resolveAudioLayers, fileDuration } from './engine/assets';
import { renderPcm, wavBlob, mp3Blob } from './engine/render';
import { PROTOCOLLI } from './content/protocolli';
import { BIB, SOUND_KEYS, LEARN_KEYS } from './content/biblioteca';
import './frequenze.css';

const fmt = (s) => {
  s = Math.max(0, Math.round(s));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
};
let _uid = 5000;

const LISTEN = {
  bin: '🎧 Solo in cuffia', bil: '🎧 In cuffia (consigliato)',
  iso: '🔊 Anche in altoparlante', mono: '🔊 Anche in altoparlante',
  noise: '🔊 Anche in altoparlante', tone: '🔊 Anche in altoparlante',
};
const SOUND_CATS = ['Ambient', 'Droni', 'Campane', 'Natura', 'Ritmi', 'Voce'];

export default function FrequenzePage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const isSystemAdmin = user?.role === 'system_admin';
  const [view, setView] = useState('explore');           // explore | impara | create
  const [world, setWorld] = useState('freq');            // freq | sound (Esplora)
  const [curTab, setCurTab] = useState(SOUND_KEYS[0]);
  const [soundCat, setSoundCat] = useState(SOUND_CATS[0]);
  const [gateOk, setGateOk] = useState(() => localStorage.getItem('fqz_gate_ok') === '1');
  const [ask, setAsk] = useState(null);                  // {title,msg,opts:[[label,fn]]}
  const [learn, setLearn] = useState(null);              // {title,body}

  const [durationMin, setDurationMin] = useState(20);
  const [fadeIn, setFadeIn] = useState(10);
  const [fadeOut, setFadeOut] = useState(20);
  const [sr, setSr] = useState(44100);
  const [fmtOut, setFmtOut] = useState('mp3');
  const [layers, setLayers] = useState([]);
  const [phases, setPhases] = useState([]);
  const [title, setTitle] = useState('');
  const [intent, setIntent] = useState(null);
  const [trackId, setTrackId] = useState(null);
  const [trackStatus, setTrackStatus] = useState('draft');
  const [trackSlug, setTrackSlug] = useState(null);
  const [drafts, setDrafts] = useState([]);
  const [playing, setPlaying] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [status, setStatus] = useState('');
  const [exporting, setExporting] = useState(null);
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

  const score = useMemo(() => ({
    score_version: 1, duration_sec: duration,
    fade_in_sec: fadeIn, fade_out_sec: fadeOut, layers, phases,
  }), [duration, fadeIn, fadeOut, layers, phases]);

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
  useEffect(() => { loadDrafts(); }, []);

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
  useEffect(() => { loadSounds(); }, []);

  const stopSoundPreview = () => {
    if (previewAudioRef.current) {
      previewAudioRef.current.pause();
      previewAudioRef.current.src = '';
    }
    setPreviewingId(null);
  };
  const toggleSoundPreview = (asset) => {
    if (previewingId === asset.id) { stopSoundPreview(); return; }
    stopSoundPreview();
    if (!previewAudioRef.current) previewAudioRef.current = new Audio();
    const el = previewAudioRef.current;
    el.src = asset.stream_url;
    el.loop = true;
    el.volume = 0.8;
    el.play().catch(() => setStatus('Anteprima non disponibile'));
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

  /* ── ascolto sessione ── */
  const stopSession = () => {
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
    const ctx = audioCtx();
    await ctx.resume();
    let audioLayers = [];
    if (layers.some((l) => l.kind === 'audio')) {
      setStatus('Carico le basi…');
      audioLayers = await resolveAudioLayers(ctx, score, soundsById);
    }
    liveRef.current = startPreview(ctx, score, { fromT, audioLayers });
    setPlaying(true);
    timerRef.current = setInterval(() => {
      const el = liveRef.current ? liveRef.current.elapsed() : 0;
      if (el >= duration) { stopSession(); setElapsed(0); setStatus('Ascolto terminato'); return; }
      setElapsed(Math.max(0, el));
      setStatus(`Ascolto · ${fmt(Math.max(0, el))} / ${fmt(duration)}`);
    }, 150);
  };
  const seekTo = (t) => { if (layers.length) playSession(t); };

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
      carrier: cfg.carrier ?? 180,
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
        setStatus(`Bozza «${name}» salvata`);
      }
      loadDrafts();
    } catch (e) {
      setStatus(e?.response?.data?.detail || 'Errore nel salvataggio');
    } finally { setSaving(false); }
  };
  const openDraft = async (id) => {
    stopSession();
    try {
      const t = (await frequenciesAPI.get(id)).data, s = t.score || {};
      setTrackId(t.id); setTitle(t.title || ''); setIntent(t.intent || null);
      setTrackStatus(t.status || 'draft'); setTrackSlug(t.slug || null);
      setDurationMin(Math.round((s.duration_sec || 1200) / 60));
      setFadeIn(s.fade_in_sec ?? 10); setFadeOut(s.fade_out_sec ?? 20);
      setLayers((s.layers || []).map((l) => ({ ...l, id: ++_uid })));
      setPhases(s.phases || []);
      setView('create');
      setStatus(`Bozza «${t.title}» caricata`);
    } catch { setStatus('Bozza non trovata'); }
  };
  const removeDraft = (id, name) => setAsk({
    title: 'Eliminare la bozza?',
    msg: `«${name}» verrà eliminata. Non si può annullare.`,
    opts: [['Sì, elimina', async () => {
      try {
        await frequenciesAPI.remove(id);
        if (id === trackId) setTrackId(null);
        loadDrafts();
      } catch { setStatus('Errore'); }
    }]],
  });

  const publishTrack = async () => {
    if (!trackId) return;
    await save();
    try {
      const r = await frequenciesAPI.publish(trackId);
      setTrackStatus('published'); setTrackSlug(r.data.slug);
      const url = `${window.location.origin}/frequenze/${r.data.slug}`;
      try { await navigator.clipboard.writeText(url); } catch { /* niente clipboard */ }
      setStatus(`In ascolto pubblico su ${url} — link copiato`);
    } catch (e) { setStatus(e?.response?.data?.detail || 'Pubblicazione fallita'); }
  };
  const unpublishTrack = async () => {
    if (!trackId) return;
    try {
      await frequenciesAPI.unpublish(trackId);
      setTrackStatus('draft');
      setStatus('Traccia riportata in bozza: il link pubblico non risponde più');
    } catch { setStatus('Errore'); }
  };

  const resetSession = () => {
    if (!layers.length) return;
    stopSession();
    setAsk({
      title: 'Svuotare la sessione?',
      msg: `Rimuove tutte le tracce dalla linea del tempo. Non si può annullare.`,
      opts: [['Sì, svuota', () => {
        setLayers([]); setPhases([]); setTrackId(null); setTitle(''); setIntent(null);
        setTrackStatus('draft'); setTrackSlug(null);
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

  /* ── export ── */
  const doExport = async () => {
    if (!layers.length) return;
    stopSession();
    setExporting({ pct: 0, phase: 'Render' });
    try {
      const audioLayers = layers.some((l) => l.kind === 'audio')
        ? await resolveAudioLayers(audioCtx(), score, soundsById) : [];
      const pcm = await renderPcm(score, {
        sampleRate: sr, audioLayers,
        onProgress: (p) => setExporting({ pct: p, phase: 'Render' }),
      });
      let blob, ext;
      if (fmtOut === 'mp3') {
        setExporting({ pct: 0, phase: 'Codifica MP3' });
        blob = await mp3Blob(pcm, sr, (p) => setExporting({ pct: p, phase: 'Codifica MP3' }));
        ext = 'mp3';
      } else { blob = wavBlob(pcm, sr); ext = 'wav'; }
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `aurya-frequenze-${new Date().toISOString().slice(0, 10)}-${durationMin}min.${ext}`;
      a.click();
      setTimeout(() => URL.revokeObjectURL(url), 4000);
      setStatus(`Traccia salvata (${ext.toUpperCase()}) · ${fmt(duration)}`);
    } catch { setStatus('Render interrotto: memoria insufficiente. Riduci la durata.'); }
    finally { setExporting(null); }
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
    const clamped = body.length > 150 && !entry.info;
    return (
      <div key={key} className={`card${live ? ' playing' : ''}${g ? ` g${g}` : ''}`}>
        <div className="head">
          <h3>{entry.t}</h3>
          {g && <span className={`badge ${g}`}>{g}</span>}
        </div>
        {entry.hz && <div className="hz">{entry.hz}</div>}
        {entry.uso && <div className="uso">{entry.uso}</div>}
        {entry.cfg && <div className="listen">{LISTEN[entry.cfg.method] || ''}</div>}
        <div className="body">
          {clamped ? `${body.slice(0, 150).trim()}…` : body}
        </div>
        {(clamped || entry.full) && (
          <button type="button" className="readmore"
            onClick={() => setLearn({ title: entry.t, body: entry.full || entry.body })}>
            Approfondisci
          </button>
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
                  if (!isNaN(v)) (live.method === 'tone' ? live.setCarrier(v) : live.setBeat(v));
                }}
                style={{ width: 70 }} /> Hz
            </label>
          </div>
        )}
        {entry.cfg && (
          <div className="foot">
            <button type="button" className="live" data-testid={`fq-card-live-${idx}`}
              onClick={() => toggleCard(key, entry)}>
              {live ? 'Ferma' : 'Ascolta'}
            </button>
            <button type="button" className="add"
              onClick={() => addCardToSession(entry)}>+ sessione</button>
          </div>
        )}
      </div>
    );
  };

  const bibKeys = view === 'impara' ? LEARN_KEYS : SOUND_KEYS;
  const activeTab = bibKeys.includes(curTab) ? curTab : bibKeys[0];
  const hasGrades = (BIB[activeTab] || []).some((e) => e.g);

  const layerLabel = (l) => {
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
        <div className="ctrls timerow">
          <span className="lbl" title="Secondo in cui il suono entra">entra a</span>
          <input className="mini t-in" type="text" defaultValue={fmt(l.start)} key={`in${l.id}-${Math.round(l.start)}`}
            onBlur={(e) => { const v = parseT(e.target.value); if (v !== null) patchLayer(l.id, { start: Math.max(0, Math.min(v, l.end - 0.5)) }); }} />
          <span className="lbl" title="Secondo in cui il suono esce">esce a</span>
          <input className="mini t-out" type="text" defaultValue={fmt(l.end)} key={`out${l.id}-${Math.round(l.end)}`}
            onBlur={(e) => { const v = parseT(e.target.value); if (v !== null) patchLayer(l.id, { end: Math.max(l.start + 0.5, Math.min(v, duration)) }); }} />
          <span className="lbl dur-tot">({fmt(l.end - l.start)})</span>
        </div>
        {l.kind === 'audio' ? (
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
          <select className="minisel" value={l.timbre}
            onChange={(e) => patchLayer(l.id, { timbre: e.target.value })}>
            <option value="pure">puro</option><option value="warm">caldo</option>
          </select>
          <button type="button" className={`chip m${l.mute ? ' on' : ''}`}
            onClick={() => patchLayer(l.id, { mute: !l.mute })}>muto</button>
        </div>
        <div className="ctrls r4">
          {l.method === 'tone' ? (
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
              <input className="mini" type="number" min="0.2" max="60" step="0.5" value={l.f0}
                onChange={(e) => { const v = +e.target.value; if (!isNaN(v)) patchLayer(l.id, l.method === 'bil' ? { f0: v, f1: v } : { f0: v }); }} />
              {l.method !== 'bil' && (
                <>
                  <span className="lbl" title="Frequenza a fine barra: uguale = ferma, diversa = discesa/salita">a</span>
                  <input className="mini" type="number" min="0.2" max="60" step="0.5" value={l.f1}
                    onChange={(e) => { const v = +e.target.value; if (!isNaN(v)) patchLayer(l.id, { f1: v }); }} />
                  <span className="lbl">Hz</span>
                  <select className="minisel" value={l.curve}
                    onChange={(e) => patchLayer(l.id, { curve: e.target.value })}>
                    {Object.entries(CURVE_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                  </select>
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
        <div className="bar"
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

  /* ─────────────────────────── RENDER ─────────────────────────── */
  return (
    <div className="fqz" data-testid="fqz-root">
      <header>
        <div>
          <h1>Aurya <em>Frequenze</em></h1>
          <div className="sub">stimolazione neuroacustica su linea del tempo</div>
        </div>
        <div className="headnav">
          <div className="viewswitch">
            <button type="button" className={`vbtn${view === 'explore' ? ' on' : ''}`}
              onClick={() => setView('explore')}>Esplora</button>
            <button type="button" className={`vbtn${view === 'create' ? ' on' : ''}`}
              onClick={() => setView('create')}>
              Crea {layers.length > 0 && <span className="vcount">{layers.length}</span>}
            </button>
            <button type="button" className={`vbtn${view === 'impara' ? ' on' : ''}`}
              onClick={() => setView('impara')}>Impara</button>
          </div>
          <button type="button" className="backcard" data-testid="fqz-back"
            title="Torna al gestionale Aurya"
            onClick={() => navigate('/dashboard')}>
            <span className="bc-ic">⌂</span>
            <span>
              <span className="bc-t">Gestionale</span><br />
              <span className="bc-s">torna ad Aurya</span>
            </span>
          </button>
        </div>
      </header>

      <main>
        {(view === 'explore' || view === 'impara') && (
          <section className="bib">
            {view === 'explore' && (
              <div className="worldswitch" data-testid="fq-worldswitch">
                <button type="button" className={`wbtn${world === 'freq' ? ' on' : ''}`}
                  onClick={() => setWorld('freq')}>Frequenze</button>
                <button type="button" data-world="sound" className={`wbtn${world === 'sound' ? ' on' : ''}`}
                  onClick={() => setWorld('sound')}>Suoni</button>
              </div>
            )}
            <h2>
              {view === 'impara' ? 'Le fondamenta'
                : world === 'sound' ? 'Le basi sonore' : 'La biblioteca delle frequenze'}
            </h2>
            {view === 'impara' ? (
              <p>Onde cerebrali, entrainment, la differenza tra i metodi e quando servono le cuffie, più il glossario. Quando vuoi mettere in pratica, passa a <b>Esplora</b>.</p>
            ) : world === 'sound' ? (
              <p className="soundlead">Le basi sonore sono la tela su cui posare le frequenze — e potrai sovrapporne più di una. Le sceglierai qui e le combinerai nella sessione, esattamente come le frequenze.</p>
            ) : (
              <p>Premi <b>Ascolta</b> su una scheda e la frequenza parte subito; puoi combinarne più insieme. Quando una ti convince, <b>+ sessione</b> la manda nella tua sessione (scheda «Crea»).</p>
            )}

            {view === 'explore' && world === 'sound' ? (
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
                {(() => {
                  const inCat = sounds.filter((s) => s.category === soundCat.toLowerCase());
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
                                  {previewingId === s.id ? 'Ferma' : 'Ascolta'}
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
                    <button type="button" onClick={composeAllLive}>+ tutte alla sessione</button>
                    <button type="button" onClick={stopAllCards}>Ferma tutto</button>
                  </div>
                )}
                <div className="tabs">
                  <div className="tabgroup">
                    <div className="tabgroup-row">
                      {bibKeys.map((k) => (
                        <button key={k} type="button"
                          className={`tab ${view === 'impara' ? 'tab-learn' : 'tab-sound'}${activeTab === k ? ' on' : ''}`}
                          onClick={() => setCurTab(k)}>
                          {k}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
                {hasGrades && (
                  <div className="legend">
                    <span className="la"><b>A</b> neuroscienza consolidata</span>
                    <span className="lb"><b>B</b> evidenza promettente ma mista</span>
                    <span className="lc"><b>C</b> tradizione — valore simbolico, non fisiologico dimostrato</span>
                  </div>
                )}
                <div className="cards">
                  {(BIB[activeTab] || []).map(renderCard)}
                </div>
              </>
            )}
          </section>
        )}

        {view === 'create' && (
          <section>
            <div className="createbar">
              <button type="button" className="cb-play" data-testid="fq-play"
                disabled={!layers.length}
                onClick={() => (playing ? stopSession() : playSession(0))}>
                {playing ? '⏸ Pausa' : '▶ Ascolta sessione'}
              </button>
              <button type="button" className="cb-reset" disabled={!layers.length}
                onClick={resetSession}>Reset</button>
              <div className="cb-collapse open" style={{ display: 'contents' }}>
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
                <div className="cb-export">
                  <span className="status">{exporting ? `${exporting.phase} · ${Math.round(exporting.pct * 100)}%` : status}</span>
                  <button type="button" data-testid="fq-save" disabled={saving || !layers.length}
                    onClick={save}>{saving ? 'Salvo…' : trackId ? 'Aggiorna bozza' : 'Salva bozza'}</button>
                  {trackId && (trackStatus === 'published' ? (
                    <button type="button" data-testid="fq-unpublish"
                      title={trackSlug ? `Pubblica su /frequenze/${trackSlug}` : ''}
                      style={{ borderColor: 'var(--water)', color: 'var(--water)' }}
                      onClick={unpublishTrack}>● Pubblica­ta — ritira</button>
                  ) : (
                    <button type="button" data-testid="fq-publish"
                      onClick={publishTrack}>Pubblica</button>
                  ))}
                  <select value={sr} onChange={(e) => setSr(+e.target.value)}
                    title="44.1 kHz standard; 48 kHz per video">
                    <option value="44100">44.1 kHz</option><option value="48000">48 kHz</option>
                  </select>
                  <select value={fmtOut} onChange={(e) => setFmtOut(e.target.value)}
                    title="MP3 320 kbps: qualità massima. WAV: non compresso, per lavorarci in studio">
                    <option value="mp3">MP3 · 320</option><option value="wav">WAV</option>
                  </select>
                  <button type="button" className="primary" disabled={!layers.length || !!exporting}
                    onClick={doExport}>Scarica</button>
                </div>
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

            {drafts.length > 0 && (
              <div className="protrow" data-testid="fq-drafts">
                <span className="tag">Le tue bozze</span>
                <div style={{ display: 'flex', gap: 7, flexWrap: 'wrap', alignItems: 'center' }}>
                  {drafts.map((d) => (
                    <span key={d.id} style={{ display: 'inline-flex', alignItems: 'center' }}>
                      <button type="button" className="prot"
                        style={d.id === trackId ? { borderColor: 'var(--water)', color: 'var(--water)' } : undefined}
                        title={`${d.layers_count} livelli · ${fmt(d.duration_sec || 0)}`}
                        onClick={() => openDraft(d.id)}>
                        {d.title}
                      </button>
                      <button type="button" className="ghost" title="Elimina bozza"
                        onClick={() => removeDraft(d.id, d.title)}>×</button>
                    </span>
                  ))}
                </div>
              </div>
            )}

            <div className="legend" style={{ marginTop: 14 }}>
              <span className="la"><b>A</b> neuroscienza consolidata</span>
              <span className="lb"><b>B</b> evidenza promettente ma mista</span>
              <span className="lc"><b>C</b> tradizione — valore simbolico, non fisiologico dimostrato</span>
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
              <b>Binaurale</b> funziona solo in cuffia. <b>Isocronico</b> e <b>monoaurale</b> anche in altoparlante — per grotta e aula usa questi.
              Timbro <b>caldo</b> più tollerabile del puro sulle sessioni lunghe; il <b>soffio</b> nasconde l'entrainment in un rumore rosa.
            </p>
          </section>
        )}
      </main>

      {view !== 'create' && layers.length > 0 && (
        <div className="sessionfoot">
          <span className="sf-dot">◆</span>
          <span className="sf-txt">La tua sessione · {layers.length} {layers.length === 1 ? 'livello' : 'livelli'} · {durationMin} min</span>
          <div className="spacer" style={{ flex: 1 }} />
          <button type="button" className="primary" onClick={() => setView('create')}>Vai a Crea →</button>
        </div>
      )}

      {/* gate sicurezza (prima visita) */}
      {!gateOk && (
        <div className="gate">
          <div className="gatebox">
            <h2>Aurya <em>Frequenze</em> — prima di iniziare</h2>
            <p>Questo strumento genera stimolazione uditiva (battiti binaurali, toni isocronici e monoaurali, stimolazione bilaterale, toni puri). Non è un dispositivo medico e non diagnostica, cura o previene alcuna condizione.</p>
            <div className="warnbox"><strong>Non usare</strong> in caso di epilessia o storia di convulsioni, con pacemaker o dispositivi impiantati. In gravidanza, consultare prima il medico. <strong>Mai</strong> durante la guida o l'uso di macchinari.</div>
            <ul>
              <li><strong>Volume moderato.</strong> Se il battito si sente nettamente sopra il resto, è troppo forte.</li>
              <li><strong>Rientro.</strong> Ogni sessione profonda termina con una risalita graduale — i protocolli la contengono già.</li>
              <li><strong>Stimolazione bilaterale.</strong> Componente sonoro usato anche nell'EMDR, ma l'EMDR è un protocollo clinico condotto da terapeuti formati: questo strumento non lo sostituisce.</li>
              <li><strong>Disagio.</strong> In caso di vertigini, nausea o malessere, interrompere l'ascolto.</li>
            </ul>
            <div className="gatefoot">
              <button type="button" className="primary"
                onClick={() => { localStorage.setItem('fqz_gate_ok', '1'); setGateOk(true); }}>
                Ho letto e compreso
              </button>
            </div>
          </div>
        </div>
      )}

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
              {(learn.body || '').split(/\n\n+/).map((p, i) => <p key={i}>{p.replace(/\n/g, ' ')}</p>)}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
