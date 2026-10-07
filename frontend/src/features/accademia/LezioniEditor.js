/**
 * LezioniEditor — LE LEZIONI di un corso (AC1, 7/10/2026). Usato dal wizard
 * (gesto 2) e dalla scheda del corso.
 *
 * Un elenco, non un gestionale: ogni lezione ha un titolo, un video (si
 * trascina il file: upload diretto a Bunny con la barra, poi «in codifica»,
 * poi «pronto · 12 min») oppure un testo; «anteprima gratuita» a scelta;
 * frecce per l'ordine. I moduli sono separatori con un titolo: il primo c'e'
 * gia', gli altri si aggiungono solo se servono.
 */
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { ArrowDown, ArrowUp, FileText, Film, Music, Waves, Paperclip, Plus, Trash2, UploadCloud, CheckCircle2, AlertCircle, Loader2, Eye } from 'lucide-react';
import { toast } from 'sonner';
import { accademiaAPI, fmtDurata, ETICHETTA_STATO_VIDEO, durataAudio, FORMATI_AUDIO, MAX_AUDIO_BYTES, FORMATI_ALLEGATO, MAX_ALLEGATO_BYTES, fmtBytes } from '../../api/accademia';
import { Bottone, campo } from '../prodotti/ui';
import { caricaVideo, FORMATI_VIDEO, MAX_VIDEO_BYTES } from './upload';

function StatoVideo({ video, avanzamento }) {
  if (!video) return null;
  const stato = video.stato;
  if (stato === 'caricamento') {
    return (
      <div className="w-full" data-testid="video-caricamento">
        <div className="flex items-center justify-between text-xs text-gray-600">
          <span className="inline-flex items-center gap-1"><Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden /> Caricamento</span>
          <span>{avanzamento != null ? `${avanzamento}%` : ''}</span>
        </div>
        <div className="mt-1 h-2 w-full overflow-hidden rounded-full bg-gray-100"><div className="h-full bg-[#2f5749] transition-all" style={{ width: `${avanzamento || 0}%` }} /></div>
      </div>
    );
  }
  if (stato === 'codifica') return <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2.5 py-0.5 text-xs font-medium text-amber-800"><Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden /> In codifica: pochi minuti, puoi continuare</span>;
  if (stato === 'pronto') return <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-medium text-emerald-800"><CheckCircle2 className="h-3.5 w-3.5" aria-hidden /> Pronto{video.duration_seconds ? ` · ${fmtDurata(video.duration_seconds)}` : ''}</span>;
  if (stato === 'errore') return <span className="inline-flex items-center gap-1 rounded-full bg-red-50 px-2.5 py-0.5 text-xs font-medium text-red-800"><AlertCircle className="h-3.5 w-3.5" aria-hidden /> Errore in codifica: ricarica il file</span>;
  return <span className="text-xs text-gray-500">{ETICHETTA_STATO_VIDEO[stato] || stato}</span>;
}

const ICONA_TIPO = { testo: FileText, video: Film, audio: Music, suono: Waves };

/* AU (8/10/2026) — gli allegati scaricabili di una lezione (pdf, schede, audio) */
function Allegati({ corso, lezione, ricarica }) {
  const [occupato, setOccupato] = useState(false);
  const carica = async (file) => {
    if (!file) return;
    if (file.size > MAX_ALLEGATO_BYTES) { toast.error('L’allegato supera i 20 MB.'); return; }
    setOccupato(true);
    try { await accademiaAPI.allegatoCarica(corso.id, lezione.id, file, file.name.replace(/\.[^.]+$/, '')); ricarica(); }
    catch (err) { const d = err?.response?.data?.detail; toast.error(d?.message || 'Non sono riuscito a caricare l’allegato.'); }
    finally { setOccupato(false); }
  };
  const togli = async (a) => {
    if (!window.confirm(`Togliere l’allegato «${a.label}»?`)) return;
    try { await accademiaAPI.allegatoTogli(corso.id, lezione.id, a.id); ricarica(); } catch { toast.error('Non sono riuscito a toglierlo.'); }
  };
  const allegati = lezione.allegati || [];
  return (
    <div className="flex flex-wrap items-center gap-2" data-testid="lezione-allegati">
      {allegati.map(a => (
        <span key={a.id} className="inline-flex items-center gap-1.5 rounded-full bg-gray-100 px-2.5 py-1 text-xs text-gray-700">
          <Paperclip className="h-3 w-3" aria-hidden /> {a.label}{a.size_bytes ? ` · ${fmtBytes(a.size_bytes)}` : ''}
          <button type="button" onClick={() => togli(a)} aria-label={`Togli ${a.label}`} className="ml-0.5 text-gray-400 hover:text-red-700">×</button>
        </span>
      ))}
      {allegati.length < 10 && (
        <label className={`inline-flex cursor-pointer items-center gap-1 text-xs text-gray-500 underline-offset-4 hover:underline ${occupato ? 'opacity-60' : ''}`}>
          <Paperclip className="h-3.5 w-3.5" aria-hidden /> {occupato ? 'Carico…' : 'Aggiungi allegato'}
          <input type="file" accept={FORMATI_ALLEGATO} className="hidden" disabled={occupato} onChange={e => { carica(e.target.files?.[0]); e.target.value = ''; }} />
        </label>
      )}
    </div>
  );
}

function Lezione({ corso, modulo, lezione, prima, ultima, onSposta, ricarica, bunnyAttivo, tracce, soundAttivo }) {
  const [titolo, setTitolo] = useState(lezione.title || '');
  const [testo, setTesto] = useState(lezione.testo || '');
  const [avanzamento, setAvanzamento] = useState(null);
  const [occupato, setOccupato] = useState(false);
  const uploadRef = useRef(null);
  useEffect(() => { setTitolo(lezione.title || ''); setTesto(lezione.testo || ''); }, [lezione.title, lezione.testo]);

  const salva = async (dati) => {
    try { await accademiaAPI.lezioneModifica(corso.id, lezione.id, dati); ricarica(); }
    catch { toast.error('Non sono riuscito a salvare la lezione.'); }
  };
  const togli = async () => {
    if (!window.confirm(`Togliere la lezione «${lezione.title}»?${lezione.video ? ' Il video viene cancellato.' : ''}`)) return;
    try { await accademiaAPI.lezioneElimina(corso.id, lezione.id); ricarica(); }
    catch { toast.error('Non sono riuscito a togliere la lezione.'); }
  };
  const scegliVideo = async (file) => {
    if (!file) return;
    if (file.size > MAX_VIDEO_BYTES) { toast.error('Il video supera i 5 GB: comprimilo o dividilo in due lezioni.'); return; }
    setOccupato(true);
    try {
      const { data: cred } = await accademiaAPI.videoPrepara(corso.id, lezione.id, { filename: file.name, size_bytes: file.size });
      setAvanzamento(0);
      ricarica();
      uploadRef.current = caricaVideo(file, cred, {
        onProgress: setAvanzamento,
        onSuccess: () => { setAvanzamento(100); toast.success('Video caricato: ora Bunny lo codifica.'); setTimeout(ricarica, 1500); },
        onError: (err) => { toast.error('Il caricamento si è interrotto: riprova, riparte da dove era.'); console.error(err); setOccupato(false); },
      });
    } catch (err) {
      const d = err?.response?.data?.detail;
      toast.error(d?.message || (typeof d === 'string' && d) || 'Non sono riuscito a preparare il caricamento.');
      setOccupato(false);
    }
  };
  const togliVideo = async () => {
    if (!window.confirm('Togliere il video di questa lezione?')) return;
    try { await accademiaAPI.videoTogli(corso.id, lezione.id); ricarica(); }
    catch { toast.error('Non sono riuscito a togliere il video.'); }
  };
  const v = lezione.video;
  const inCorso = v && (v.stato === 'caricamento' || v.stato === 'codifica');
  // AU — l'audio mp3: la durata la misura il browser, poi l'upload con la barra
  const scegliAudio = async (file) => {
    if (!file) return;
    if (file.size > MAX_AUDIO_BYTES) { toast.error('L’audio supera i 50 MB: comprimilo (mp3 a 128 kbps basta).'); return; }
    setOccupato(true); setAvanzamento(0);
    try {
      const durata = await durataAudio(file);
      await accademiaAPI.audioCarica(corso.id, lezione.id, file, durata, setAvanzamento);
      toast.success('Audio caricato: è già pronto.'); ricarica();
    } catch (err) {
      const d = err?.response?.data?.detail;
      toast.error(d?.message || (typeof d === 'string' && d) || 'Non sono riuscito a caricare l’audio.');
    } finally { setOccupato(false); setAvanzamento(null); }
  };
  const togliAudio = async () => {
    if (!window.confirm('Togliere l’audio di questa lezione?')) return;
    try { await accademiaAPI.audioTogli(corso.id, lezione.id); ricarica(); } catch { toast.error('Non sono riuscito a togliere l’audio.'); }
  };
  const IconaTipo = ICONA_TIPO[lezione.tipo] || Film;

  return (
    <li className="rounded-xl border border-gray-200 bg-white p-3 sm:p-4" data-testid={`lezione-${lezione.id}`}>
      <div className="flex items-start gap-3">
        <span className="mt-1 flex h-7 w-7 flex-none items-center justify-center rounded-full bg-[#2f5749]/10 text-[#2f5749]">
          <IconaTipo className="h-3.5 w-3.5" aria-hidden />
        </span>
        <div className="min-w-0 flex-1 space-y-3">
          <input className={`${campo} font-medium`} value={titolo} maxLength={255} aria-label="Titolo della lezione"
                 onChange={e => setTitolo(e.target.value)} onBlur={() => { if (titolo.trim() && titolo !== lezione.title) salva({ title: titolo.trim() }); }} />
          {lezione.tipo === 'testo' ? (
            <textarea className={`${campo} resize-y`} rows={4} maxLength={20000} value={testo} placeholder="Il testo della lezione."
                      onChange={e => setTesto(e.target.value)} onBlur={() => { if (testo !== (lezione.testo || '')) salva({ testo }); }} />
          ) : lezione.tipo === 'audio' ? (
            lezione.audio ? (
              <div className="flex flex-wrap items-center gap-3" data-testid="lezione-audio">
                <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-medium text-emerald-800"><CheckCircle2 className="h-3.5 w-3.5" aria-hidden /> Pronto{lezione.audio.duration_seconds ? ` · ${fmtDurata(lezione.audio.duration_seconds)}` : ''}{lezione.audio.size_bytes ? ` · ${fmtBytes(lezione.audio.size_bytes)}` : ''}</span>
                <span className="truncate text-xs text-gray-500">{lezione.audio.original_name}</span>
                <label className="cursor-pointer text-xs font-medium text-gray-600 underline-offset-4 hover:underline">
                  Sostituisci<input type="file" accept={FORMATI_AUDIO} className="hidden" onChange={e => scegliAudio(e.target.files?.[0])} />
                </label>
                <button type="button" onClick={togliAudio} className="text-xs text-gray-500 hover:text-red-700">Togli audio</button>
              </div>
            ) : (
              <label className={`flex cursor-pointer items-center gap-3 rounded-xl border-2 border-dashed border-gray-300 px-4 py-4 text-sm text-gray-700 transition hover:border-[#2f5749] hover:bg-[#2f5749]/[0.03] ${occupato ? 'opacity-60' : ''}`}
                     data-testid="audio-dropzone" onDragOver={e => e.preventDefault()} onDrop={e => { e.preventDefault(); scegliAudio(e.dataTransfer.files?.[0]); }}>
                <Music className="h-5 w-5 flex-none text-[#2f5749]" aria-hidden />
                <span className="min-w-0 flex-1">
                  <span className="block font-medium">{occupato ? `Carico… ${avanzamento != null ? `${avanzamento}%` : ''}` : 'Trascina qui l’audio, o scegli il file'}</span>
                  <span className="block text-xs text-gray-500">MP3, M4A, WAV o OGG fino a 50 MB. È pronto appena caricato: anche una traccia esportata da Aurya Sound.</span>
                </span>
                <input type="file" accept={FORMATI_AUDIO} className="hidden" disabled={occupato} onChange={e => scegliAudio(e.target.files?.[0])} />
              </label>
            )
          ) : lezione.tipo === 'suono' ? (
            <div className="space-y-2" data-testid="lezione-suono">
              {soundAttivo ? (
                <select className={campo} value={lezione.suono?.track_id || ''} data-testid="suono-select"
                        onChange={e => salva({ suono_track_id: e.target.value })}>
                  <option value="">Scegli una delle tue tracce Aurya Sound…</option>
                  {(tracce || []).map(tr => (
                    <option key={tr.id} value={tr.id}>{tr.title || 'Senza titolo'} · {fmtDurata(tr.duration_sec) || `${tr.duration_sec} s`}{tr.status === 'published' ? '' : ' · bozza'}</option>
                  ))}
                </select>
              ) : (
                <p className="rounded-xl bg-amber-50 px-4 py-3 text-xs text-amber-900">Le lezioni con una traccia Aurya Sound si aprono con Crea Studio.</p>
              )}
              {soundAttivo && (tracce || []).length === 0 && (
                <p className="text-xs text-gray-500">Non hai ancora tracce tue: <a href="/sound/crea" className="underline underline-offset-4">creane una in Aurya Sound</a>, poi torna qui.</p>
              )}
            </div>
          ) : v ? (
            <div className="flex flex-wrap items-center gap-3">
              {v.thumbnail_url && <img src={v.thumbnail_url} alt="" className="h-14 w-24 rounded-lg object-cover" />}
              <div className="min-w-0 flex-1"><StatoVideo video={v} avanzamento={avanzamento} /></div>
              {!inCorso && (
                <label className="cursor-pointer text-xs font-medium text-gray-600 underline-offset-4 hover:underline">
                  Sostituisci<input type="file" accept={FORMATI_VIDEO} className="hidden" onChange={e => scegliVideo(e.target.files?.[0])} />
                </label>
              )}
              <button type="button" onClick={togliVideo} className="text-xs text-gray-500 hover:text-red-700">Togli video</button>
            </div>
          ) : bunnyAttivo ? (
            <label className={`flex cursor-pointer items-center gap-3 rounded-xl border-2 border-dashed border-gray-300 px-4 py-4 text-sm text-gray-700 transition hover:border-[#2f5749] hover:bg-[#2f5749]/[0.03] ${occupato ? 'opacity-60' : ''}`}
                   data-testid="video-dropzone"
                   onDragOver={e => e.preventDefault()} onDrop={e => { e.preventDefault(); scegliVideo(e.dataTransfer.files?.[0]); }}>
              <UploadCloud className="h-5 w-5 flex-none text-[#2f5749]" aria-hidden />
              <span><span className="block font-medium">Trascina qui il video, o scegli il file</span><span className="block text-xs text-gray-500">MP4, MOV o WebM fino a 5 GB. Parte subito, riprende da solo se cade la rete.</span></span>
              <input type="file" accept={FORMATI_VIDEO} className="hidden" disabled={occupato} onChange={e => scegliVideo(e.target.files?.[0])} />
            </label>
          ) : (
            <p className="rounded-xl bg-amber-50 px-4 py-3 text-xs text-amber-900" data-testid="video-non-attivo">
              Il caricamento video non è ancora attivo su questo ambiente: intanto prepara titoli e testi, i video li carichi appena si accende.
            </p>
          )}
          <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
            <label className="inline-flex cursor-pointer items-center gap-1.5 text-xs text-gray-600">
              <input type="checkbox" className="h-4 w-4 accent-[#2f5749]" checked={!!lezione.is_preview} onChange={e => salva({ is_preview: e.target.checked })} />
              <Eye className="h-3.5 w-3.5" aria-hidden /> Anteprima gratuita
            </label>
            {lezione.tipo === 'video' && !v && (
              <button type="button" onClick={() => salva({ tipo: 'testo' })} className="text-xs text-gray-500 underline-offset-4 hover:underline">Trasforma in lezione di testo</button>
            )}
            {lezione.tipo === 'testo' && (
              <button type="button" onClick={() => salva({ tipo: 'video' })} className="text-xs text-gray-500 underline-offset-4 hover:underline">Trasforma in lezione video</button>
            )}
          </div>
          <Allegati corso={corso} lezione={lezione} ricarica={ricarica} />
        </div>
        <div className="flex flex-none flex-col items-center gap-1">
          <button type="button" onClick={() => onSposta(-1)} disabled={prima} aria-label="Sposta su" className="rounded-full p-1.5 text-gray-500 hover:bg-gray-100 disabled:opacity-30"><ArrowUp className="h-4 w-4" /></button>
          <button type="button" onClick={() => onSposta(1)} disabled={ultima} aria-label="Sposta giù" className="rounded-full p-1.5 text-gray-500 hover:bg-gray-100 disabled:opacity-30"><ArrowDown className="h-4 w-4" /></button>
          <button type="button" onClick={togli} aria-label="Togli lezione" className="rounded-full p-1.5 text-gray-400 hover:bg-red-50 hover:text-red-700"><Trash2 className="h-4 w-4" /></button>
        </div>
      </div>
    </li>
  );
}

export default function LezioniEditor({ corso, ricarica }) {
  const [nuova, setNuova] = useState({});           // {moduloId: titolo}
  const [nuovoModulo, setNuovoModulo] = useState('');
  const moduli = corso?.moduli || [];
  const bunnyAttivo = !!corso?.bunny_attivo;
  // AU — le tracce Aurya Sound dell'operatore (una lettura per editor, solo col privilegio)
  const soundAttivo = !!corso?.sound_attivo;
  const [tracce, setTracce] = useState(null);
  useEffect(() => {
    if (!soundAttivo || !corso?.id) return undefined;
    let vivo = true;
    accademiaAPI.tracce(corso.id).then(res => { if (vivo) setTracce(res.data?.tracce || []); }).catch(() => { if (vivo) setTracce([]); });
    return () => { vivo = false; };
  }, [soundAttivo, corso?.id]);

  // le lezioni in lavorazione si rileggono ogni 6 secondi (il webhook puo' tardare)
  const inLavorazione = moduli.some(m => (m.lezioni || []).some(l => l.video && (l.video.stato === 'caricamento' || l.video.stato === 'codifica')));
  useEffect(() => {
    if (!inLavorazione) return undefined;
    const t = setInterval(() => {
      moduli.forEach(m => (m.lezioni || []).forEach(l => {
        if (l.video && l.video.stato === 'codifica') accademiaAPI.videoStato(corso.id, l.id).catch(() => {});
      }));
      ricarica();
    }, 6000);
    return () => clearInterval(t);
  }, [inLavorazione, corso?.id, moduli, ricarica]);

  const ordineAttuale = useCallback(() => moduli.map(m => ({ id: m.id, lezioni: (m.lezioni || []).map(l => l.id) })), [moduli]);
  const sposta = async (mi, li, delta) => {
    const ord = ordineAttuale();
    const arr = ord[mi].lezioni;
    const j = li + delta;
    if (j < 0 || j >= arr.length) return;
    [arr[li], arr[j]] = [arr[j], arr[li]];
    try { await accademiaAPI.ordine(corso.id, ord); ricarica(); } catch { toast.error('Non sono riuscito a riordinare.'); }
  };
  const aggiungi = async (moduloId, tipo) => {
    const titolo = (nuova[moduloId] || '').trim();
    if (!titolo) { toast.error('Scrivi il titolo della lezione.'); return; }
    try {
      await accademiaAPI.lezioneCrea(corso.id, { title: titolo, tipo, module_id: moduloId });
      setNuova(n => ({ ...n, [moduloId]: '' })); ricarica();
    } catch (err) {
      const d = err?.response?.data?.detail;
      toast.error(d?.message || (typeof d === 'string' && d) || 'Non sono riuscito ad aggiungere la lezione.');
    }
  };
  const aggiungiModulo = async () => {
    const t = nuovoModulo.trim();
    if (!t) return;
    try { await accademiaAPI.moduloCrea(corso.id, { title: t }); setNuovoModulo(''); ricarica(); }
    catch { toast.error('Non sono riuscito ad aggiungere il modulo.'); }
  };
  const rinominaModulo = async (m) => {
    const t = window.prompt('Il titolo del modulo', m.title || '');
    if (t == null || !t.trim() || t.trim() === m.title) return;
    try { await accademiaAPI.moduloModifica(corso.id, m.id, { title: t.trim() }); ricarica(); }
    catch { toast.error('Non sono riuscito a rinominare il modulo.'); }
  };
  const togliModulo = async (m) => {
    if (!window.confirm(`Togliere il modulo «${m.title}»? Le sue lezioni passano al modulo precedente.`)) return;
    try { await accademiaAPI.moduloElimina(corso.id, m.id); ricarica(); }
    catch (err) { const d = err?.response?.data?.detail; toast.error((typeof d === 'string' && d) || 'Non sono riuscito a togliere il modulo.'); }
  };

  if (!corso) return null;
  return (
    <div className="space-y-6" data-testid="lezioni-editor">
      {moduli.map((m, mi) => (
        <section key={m.id} data-testid={`modulo-${m.id}`}>
          <div className="mb-2 flex items-center justify-between gap-2">
            <h3 className="text-sm font-semibold text-gray-900">
              {moduli.length > 1 ? `Modulo ${mi + 1} · ` : ''}{m.title}
            </h3>
            <div className="flex gap-3 text-xs text-gray-500">
              <button type="button" onClick={() => rinominaModulo(m)} className="underline-offset-4 hover:underline">Rinomina</button>
              {moduli.length > 1 && <button type="button" onClick={() => togliModulo(m)} className="hover:text-red-700">Togli modulo</button>}
            </div>
          </div>
          <ol className="space-y-2">
            {(m.lezioni || []).map((l, li) => (
              <Lezione key={l.id} corso={corso} modulo={m} lezione={l} prima={li === 0} ultima={li === (m.lezioni || []).length - 1}
                       onSposta={(d) => sposta(mi, li, d)} ricarica={ricarica} bunnyAttivo={bunnyAttivo} tracce={tracce} soundAttivo={soundAttivo} />
            ))}
          </ol>
          <div className="mt-2 flex flex-col gap-2 rounded-xl border border-dashed border-gray-300 p-3 sm:flex-row sm:items-center">
            <input className={campo} placeholder="Titolo della nuova lezione" value={nuova[m.id] || ''} data-testid={`nuova-lezione-${m.id}`}
                   onChange={e => setNuova(n => ({ ...n, [m.id]: e.target.value }))}
                   onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); aggiungi(m.id, 'video'); } }} />
            <div className="flex flex-none gap-2">
              <Bottone variante="secondario" onClick={() => aggiungi(m.id, 'video')} className="min-h-[40px] px-4"><Film className="h-4 w-4" aria-hidden /> Video</Bottone>
              <Bottone variante="secondario" onClick={() => aggiungi(m.id, 'audio')} className="min-h-[40px] px-4" data-testid="aggiungi-audio"><Music className="h-4 w-4" aria-hidden /> Audio</Bottone>
              {soundAttivo && <Bottone variante="secondario" onClick={() => aggiungi(m.id, 'suono')} className="min-h-[40px] px-4" data-testid="aggiungi-suono"><Waves className="h-4 w-4" aria-hidden /> Suono</Bottone>}
              <Bottone variante="secondario" onClick={() => aggiungi(m.id, 'testo')} className="min-h-[40px] px-4"><FileText className="h-4 w-4" aria-hidden /> Testo</Bottone>
            </div>
          </div>
        </section>
      ))}
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
        <input className={campo} placeholder="Un modulo nuovo (facoltativo): es. «Settimana 2»" value={nuovoModulo}
               onChange={e => setNuovoModulo(e.target.value)} onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); aggiungiModulo(); } }} />
        <Bottone variante="secondario" onClick={aggiungiModulo} disabled={!nuovoModulo.trim()} className="min-h-[40px] flex-none px-4"><Plus className="h-4 w-4" aria-hidden /> Aggiungi modulo</Bottone>
      </div>
    </div>
  );
}
