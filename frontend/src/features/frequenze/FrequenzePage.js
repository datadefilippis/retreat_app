/**
 * Frequenze by Aurya — compositore (FQ0, 18/8/2026).
 *
 * Prima versione dentro il gestionale: protocolli pronti, editor dei
 * livelli (metodo, battiti, curva, tempi, volume), ascolto live via
 * engine/synth, bozze salvate per-org via API, export MP3/WAV locale.
 * La base musicale caricata resta locale alla sessione (persistenza
 * con FQ2 / audio_assets). La timeline drag del prototipo e' FQ0.5:
 * qui i tempi si scrivono, non si trascinano.
 */
import React, { useEffect, useMemo, useRef, useState } from 'react';
import { toast } from 'sonner';
import { AppLayout, Header } from '../../components/Layout';
import { Button } from '../../components/ui/button';
import { frequenciesAPI } from '../../api/frequencies';
import { METHOD_LABELS, CURVE_LABELS, startPreview } from './engine/synth';
import { renderPcm, wavBlob, mp3Blob } from './engine/render';
import { PROTOCOLLI } from './content/protocolli';

const fmt = (s) => {
  s = Math.max(0, Math.round(s));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
};
let _uid = 1000;

const GRADE_COLORS = { A: 'text-emerald-700 border-emerald-600', B: 'text-amber-700 border-amber-600', C: 'text-violet-700 border-violet-600' };

export default function FrequenzePage() {
  const [durationMin, setDurationMin] = useState(20);
  const [fadeIn, setFadeIn] = useState(10);
  const [fadeOut, setFadeOut] = useState(20);
  const [layers, setLayers] = useState([]);
  const [phases, setPhases] = useState([]);
  const [audioLayers, setAudioLayers] = useState([]); // basi locali (non persistite)
  const [title, setTitle] = useState('');
  const [intent, setIntent] = useState(null);
  const [trackId, setTrackId] = useState(null); // bozza corrente sul server
  const [drafts, setDrafts] = useState([]);
  const [playing, setPlaying] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [exporting, setExporting] = useState(null); // {pct, phase} | null
  const [saving, setSaving] = useState(false);

  const ctxRef = useRef(null);
  const liveRef = useRef(null);
  const timerRef = useRef(null);
  const fileRef = useRef(null);
  const duration = Math.max(60, durationMin * 60);

  const score = useMemo(() => ({
    score_version: 1,
    duration_sec: duration,
    fade_in_sec: fadeIn,
    fade_out_sec: fadeOut,
    layers,
    phases,
  }), [duration, fadeIn, fadeOut, layers, phases]);

  const loadDrafts = async () => {
    try {
      const r = await frequenciesAPI.list();
      setDrafts(r.data.items || []);
    } catch { /* lista non bloccante */ }
  };
  useEffect(() => { loadDrafts(); }, []);

  const stop = () => {
    if (liveRef.current) { liveRef.current.stop(); liveRef.current = null; }
    if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null; }
    setPlaying(false);
  };
  useEffect(() => () => stop(), []);

  const play = async (fromT = 0) => {
    stop();
    if (!layers.length && !audioLayers.length) return;
    ctxRef.current = ctxRef.current || new (window.AudioContext || window.webkitAudioContext)();
    await ctxRef.current.resume();
    liveRef.current = startPreview(ctxRef.current, score, { fromT, audioLayers });
    setPlaying(true);
    timerRef.current = setInterval(() => {
      const el = liveRef.current ? liveRef.current.elapsed() : 0;
      if (el >= duration) { stop(); setElapsed(0); return; }
      setElapsed(Math.max(0, el));
    }, 200);
  };

  // le modifiche strutturali entrano al prossimo avvio (come nel
  // prototipo); il volume invece e' vivo subito
  const patchLayer = (id, patch) => {
    setLayers((ls) => ls.map((l) => (l.id === id ? { ...l, ...patch } : l)));
    if (patch.gain !== undefined && liveRef.current) liveRef.current.setLayerGain(id, patch.gain);
  };
  const removeLayer = (id) => { stop(); setLayers((ls) => ls.filter((l) => l.id !== id)); };

  const loadProtocol = (name) => {
    stop();
    const built = PROTOCOLLI[name].build(duration);
    setLayers(built.layers);
    setPhases(built.phases);
    setIntent(PROTOCOLLI[name].intent);
    if (!title) setTitle(name);
    toast.message(`Protocollo «${name}» caricato`, { description: PROTOCOLLI[name].ev });
  };

  const addLayer = () => {
    setLayers((ls) => [...ls, {
      id: ++_uid, kind: 'neuro', name: 'Livello', method: 'bin', timbre: 'warm',
      carrier: 180, f0: 10, f1: 10, curve: 'lin', start: 0, end: duration,
      gain: 0.25, breath: true, mute: false,
    }]);
  };

  const addBaseFiles = async (files) => {
    const audio = [...files].filter((f) => f.type.startsWith('audio') || /\.(wav|mp3|flac|ogg|m4a|aac)$/i.test(f.name));
    if (!audio.length) return;
    ctxRef.current = ctxRef.current || new (window.AudioContext || window.webkitAudioContext)();
    for (const f of audio) {
      try {
        const buf = await ctxRef.current.decodeAudioData(await f.arrayBuffer());
        setAudioLayers((ls) => [...ls, {
          id: ++_uid, name: f.name.replace(/\.[^.]+$/, '').slice(0, 38),
          buffer: buf, start: 0, end: duration, gain: 0.7,
          loop: buf.duration < duration, mute: false,
        }]);
      } catch { toast.error(`Impossibile leggere ${f.name}`); }
    }
  };

  const save = async () => {
    if (!layers.length) { toast.error('La sessione è vuota'); return; }
    const name = title.trim() || 'Senza titolo';
    setSaving(true);
    try {
      if (trackId) {
        await frequenciesAPI.update(trackId, { title: name, score, intent });
        toast.success('Bozza aggiornata');
      } else {
        const r = await frequenciesAPI.create({ title: name, score, intent });
        setTrackId(r.data.id);
        toast.success('Bozza salvata');
      }
      loadDrafts();
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Errore nel salvataggio');
    } finally { setSaving(false); }
  };

  const openDraft = async (id) => {
    stop();
    try {
      const r = await frequenciesAPI.get(id);
      const t = r.data, s = t.score || {};
      setTrackId(t.id);
      setTitle(t.title || '');
      setIntent(t.intent || null);
      setDurationMin(Math.round((s.duration_sec || 1200) / 60));
      setFadeIn(s.fade_in_sec ?? 10);
      setFadeOut(s.fade_out_sec ?? 20);
      setLayers((s.layers || []).map((l) => ({ ...l, id: ++_uid })));
      setPhases(s.phases || []);
      setAudioLayers([]);
    } catch { toast.error('Bozza non trovata'); }
  };

  const removeDraft = async (id) => {
    try {
      await frequenciesAPI.remove(id);
      if (id === trackId) setTrackId(null);
      loadDrafts();
      toast.success('Bozza eliminata');
    } catch { toast.error('Errore'); }
  };

  const nuova = () => {
    stop();
    setTrackId(null); setTitle(''); setIntent(null);
    setLayers([]); setPhases([]); setAudioLayers([]);
  };

  const doExport = async (format) => {
    if (!layers.length && !audioLayers.length) return;
    stop();
    setExporting({ pct: 0, phase: 'Sintesi' });
    try {
      const pcm = await renderPcm(score, {
        sampleRate: 44100, audioLayers,
        onProgress: (p) => setExporting({ pct: p, phase: 'Sintesi' }),
      });
      let blob, ext;
      if (format === 'mp3') {
        setExporting({ pct: 0, phase: 'Codifica MP3' });
        blob = await mp3Blob(pcm, 44100, (p) => setExporting({ pct: p, phase: 'Codifica MP3' }));
        ext = 'mp3';
      } else { blob = wavBlob(pcm, 44100); ext = 'wav'; }
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${(title || 'frequenze').replace(/[^\w\s-]/g, '').trim().replace(/\s+/g, '-').toLowerCase() || 'frequenze'}-${durationMin}min.${ext}`;
      a.click();
      setTimeout(() => URL.revokeObjectURL(url), 4000);
      toast.success(`Traccia esportata (${ext.toUpperCase()})`);
    } catch (e) {
      toast.error('Export interrotto: riduci la durata o usa MP3');
    } finally { setExporting(null); }
  };

  const numField = (value, onChange, { min, max, step = 1, w = 'w-20' } = {}) => (
    <input type="number" value={value} min={min} max={max} step={step}
      onChange={(e) => { const v = parseFloat(e.target.value); if (!isNaN(v)) onChange(v); }}
      className={`${w} rounded-md border border-gray-300 px-2 py-1 text-sm focus:border-gray-900 focus:outline-none`} />
  );

  return (
    <AppLayout>
      <Header title="Frequenze" />
      <div className="p-4 md:p-8 max-w-5xl space-y-5">
        <p className="text-sm text-muted-foreground max-w-2xl">
          Componi una sessione vibrazionale: parti da un protocollo, regola i
          livelli, ascolta. Le bozze si salvano qui; l'export MP3/WAV serve per
          l'uso in aula. Il binaurale funziona solo in cuffia; isocronico e
          monoaurale anche in altoparlante.
        </p>

        {/* protocolli */}
        <div className="rounded-xl border bg-card p-4">
          <div className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
            Parti da un protocollo
          </div>
          <div className="flex flex-wrap gap-2">
            {Object.entries(PROTOCOLLI).map(([name, p]) => (
              <button key={name} type="button" title={p.ev}
                data-testid={`fq-prot-${p.intent}`}
                onClick={() => loadProtocol(name)}
                className="rounded-full border px-3.5 py-1.5 text-sm hover:border-[#376254] hover:text-[#376254] transition-colors">
                {name}{' '}
                <span className={`text-[10px] font-mono border rounded-full px-1.5 ${GRADE_COLORS[p.grade]}`}>{p.grade}</span>
              </button>
            ))}
          </div>
          <p className="text-[11px] text-muted-foreground mt-2">
            A = neuroscienza consolidata · B = evidenza promettente ma mista ·
            C = tradizione, valore simbolico. Nessun protocollo sostituisce un
            percorso clinico.
          </p>
        </div>

        {/* barra sessione */}
        <div className="rounded-xl border bg-card p-4 flex flex-wrap items-end gap-3" data-testid="fq-createbar">
          <div className="flex flex-col gap-1">
            <label className="text-xs text-muted-foreground">Titolo</label>
            <input value={title} onChange={(e) => setTitle(e.target.value)}
              placeholder="La mia sessione"
              className="w-48 rounded-md border border-gray-300 px-2 py-1 text-sm focus:border-gray-900 focus:outline-none" />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs text-muted-foreground">Durata (min)</label>
            {numField(durationMin, setDurationMin, { min: 1, max: 60 })}
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs text-muted-foreground">Apertura (s)</label>
            {numField(fadeIn, setFadeIn, { min: 0, max: 120, w: 'w-16' })}
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs text-muted-foreground">Chiusura (s)</label>
            {numField(fadeOut, setFadeOut, { min: 0, max: 120, w: 'w-16' })}
          </div>
          <div className="flex-1" />
          <Button type="button" data-testid="fq-play"
            disabled={!layers.length && !audioLayers.length}
            onClick={() => (playing ? stop() : play(0))}>
            {playing ? `⏸ ${fmt(elapsed)} / ${fmt(duration)}` : '▶ Ascolta'}
          </Button>
          <Button type="button" variant="outline" data-testid="fq-save"
            disabled={saving || !layers.length} onClick={save}>
            {saving ? 'Salvo…' : trackId ? 'Aggiorna bozza' : 'Salva bozza'}
          </Button>
          <Button type="button" variant="outline" onClick={nuova}>Nuova</Button>
        </div>

        {/* livelli */}
        <div className="space-y-3" data-testid="fq-layers">
          {layers.map((l) => (
            <div key={l.id} className={`rounded-xl border bg-card p-3 space-y-2 ${l.mute ? 'opacity-50' : ''}`}>
              <div className="flex flex-wrap items-center gap-2">
                <input value={l.name} onChange={(e) => patchLayer(l.id, { name: e.target.value })}
                  className="w-44 rounded-md border border-gray-300 px-2 py-1 text-sm font-medium focus:border-gray-900 focus:outline-none" />
                <select value={l.method} onChange={(e) => patchLayer(l.id, { method: e.target.value })}
                  className="rounded-md border border-gray-300 px-2 py-1 text-sm bg-white">
                  {Object.entries(METHOD_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                </select>
                <select value={l.timbre} onChange={(e) => patchLayer(l.id, { timbre: e.target.value })}
                  className="rounded-md border border-gray-300 px-2 py-1 text-sm bg-white">
                  <option value="warm">caldo</option><option value="pure">puro</option>
                </select>
                <button type="button" onClick={() => patchLayer(l.id, { mute: !l.mute })}
                  className={`rounded-full border px-2.5 py-0.5 text-xs ${l.mute ? 'bg-gray-800 text-white' : ''}`}>
                  muto
                </button>
                <div className="flex-1" />
                <button type="button" onClick={() => removeLayer(l.id)}
                  className="text-muted-foreground hover:text-red-600 text-lg leading-none px-1">×</button>
              </div>
              <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-muted-foreground">
                {l.method !== 'noise' && (
                  <span className="flex items-center gap-1.5"
                    title="Il tono udibile che trasporta il battito">
                    {l.method === 'tone' ? 'frequenza' : 'portante'}
                    {numField(l.carrier, (v) => patchLayer(l.id, { carrier: v }), { min: 20, max: 2000, step: 5, w: 'w-20' })} Hz
                  </span>
                )}
                {l.method !== 'tone' && (
                  <>
                    <span className="flex items-center gap-1.5"
                      title="Frequenza del battito a inizio e fine barra: uguali = ferma, diverse = discesa o salita">
                      battito da {numField(l.f0, (v) => patchLayer(l.id, { f0: v }), { min: 0.2, max: 60, step: 0.5, w: 'w-16' })}
                      a {numField(l.f1, (v) => patchLayer(l.id, { f1: v }), { min: 0.2, max: 60, step: 0.5, w: 'w-16' })} Hz
                    </span>
                    <select value={l.curve} onChange={(e) => patchLayer(l.id, { curve: e.target.value })}
                      className="rounded-md border border-gray-300 px-2 py-1 bg-white">
                      {Object.entries(CURVE_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                    </select>
                  </>
                )}
                <span className="flex items-center gap-1.5">
                  entra a {numField(Math.round(l.start), (v) => patchLayer(l.id, { start: Math.max(0, Math.min(v, l.end - 1)) }), { min: 0, max: duration, w: 'w-20' })}
                  esce a {numField(Math.round(l.end), (v) => patchLayer(l.id, { end: Math.max(l.start + 1, Math.min(v, duration)) }), { min: 0, max: duration, w: 'w-20' })} s
                </span>
                <span className="flex items-center gap-1.5">
                  volume
                  <input type="range" min="0" max="1" step="0.01" value={l.gain}
                    onChange={(e) => patchLayer(l.id, { gain: +e.target.value })} className="w-24" />
                  {Math.round(l.gain * 100)}%
                </span>
              </div>
            </div>
          ))}
          {audioLayers.map((l) => (
            <div key={l.id} className="rounded-xl border border-dashed bg-card p-3 flex flex-wrap items-center gap-3 text-sm">
              <span className="font-medium">♫ {l.name}</span>
              <span className="text-xs text-muted-foreground">{l.buffer.duration.toFixed(0)}s · base locale, non salvata nella bozza</span>
              <div className="flex-1" />
              <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
                volume
                <input type="range" min="0" max="1" step="0.01" value={l.gain}
                  onChange={(e) => { const v = +e.target.value; setAudioLayers((ls) => ls.map((x) => x.id === l.id ? { ...x, gain: v } : x)); if (liveRef.current) liveRef.current.setLayerGain(l.id, v); }}
                  className="w-24" />
              </span>
              <button type="button" onClick={() => { stop(); setAudioLayers((ls) => ls.filter((x) => x.id !== l.id)); }}
                className="text-muted-foreground hover:text-red-600 text-lg leading-none px-1">×</button>
            </div>
          ))}
          <div className="flex gap-2">
            <Button type="button" variant="outline" size="sm" onClick={addLayer} data-testid="fq-add-layer">
              + Livello frequenza
            </Button>
            <Button type="button" variant="outline" size="sm" onClick={() => fileRef.current?.click()}>
              + Musica di base
            </Button>
            <input ref={fileRef} type="file" accept="audio/*" multiple hidden
              onChange={(e) => { addBaseFiles(e.target.files); e.target.value = ''; }} />
          </div>
        </div>

        {/* export */}
        <div className="rounded-xl border bg-card p-4 flex flex-wrap items-center gap-3">
          <div className="text-sm font-medium">Esporta per l'aula</div>
          <span className="text-xs text-muted-foreground">MP3 320 ≈ 45 MB per 20 min · WAV non compresso per lavorarci in studio</span>
          <div className="flex-1" />
          {exporting ? (
            <span className="text-sm text-muted-foreground" data-testid="fq-export-progress">
              {exporting.phase} · {Math.round(exporting.pct * 100)}%
            </span>
          ) : (
            <>
              <Button type="button" variant="outline" size="sm" disabled={!layers.length && !audioLayers.length}
                onClick={() => doExport('mp3')} data-testid="fq-export-mp3">Scarica MP3</Button>
              <Button type="button" variant="outline" size="sm" disabled={!layers.length && !audioLayers.length}
                onClick={() => doExport('wav')}>Scarica WAV</Button>
            </>
          )}
        </div>

        {/* bozze */}
        <div className="rounded-xl border bg-card p-4" data-testid="fq-drafts">
          <div className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
            Le tue bozze
          </div>
          {drafts.length === 0 ? (
            <p className="text-sm text-muted-foreground">Nessuna bozza ancora: componi e salva.</p>
          ) : (
            <ul className="divide-y">
              {drafts.map((d) => (
                <li key={d.id} className="py-2 flex items-center gap-3 text-sm">
                  <button type="button" onClick={() => openDraft(d.id)}
                    className={`font-medium hover:underline ${d.id === trackId ? 'text-[#376254]' : ''}`}>
                    {d.title}
                  </button>
                  <span className="text-xs text-muted-foreground">
                    {d.layers_count} {d.layers_count === 1 ? 'livello' : 'livelli'} · {fmt(d.duration_sec || 0)}
                  </span>
                  <div className="flex-1" />
                  <button type="button" onClick={() => removeDraft(d.id)}
                    className="text-xs text-muted-foreground hover:text-red-600">elimina</button>
                </li>
              ))}
            </ul>
          )}
        </div>

        <p className="text-[11px] text-muted-foreground max-w-2xl">
          Strumento di accompagnamento al rilassamento: non è un dispositivo
          medico e non sostituisce percorsi clinici. La stimolazione bilaterale
          è un componente usato nell'EMDR, ma l'EMDR è un protocollo clinico
          condotto da terapeuti formati.
        </p>
      </div>
    </AppLayout>
  );
}
