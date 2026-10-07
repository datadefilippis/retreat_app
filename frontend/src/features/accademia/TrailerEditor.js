/**
 * TrailerEditor — il VIDEO DI PRESENTAZIONE del corso (AC3, 7/10/2026).
 * Stesso ciclo delle lezioni video: trascini il file, upload diretto a
 * Bunny, «in codifica», «pronto». Uno per corso: il nuovo sostituisce.
 */
import React, { useEffect, useRef, useState } from 'react';
import { UploadCloud, CheckCircle2, AlertCircle, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { accademiaAPI, fmtDurata } from '../../api/accademia';
import { caricaVideo, FORMATI_VIDEO, MAX_VIDEO_BYTES } from './upload';

export default function TrailerEditor({ corso, ricarica }) {
  const [avanzamento, setAvanzamento] = useState(null);
  const [occupato, setOccupato] = useState(false);
  const uploadRef = useRef(null);
  const v = corso?.trailer;
  const inCorso = v && (v.stato === 'caricamento' || v.stato === 'codifica');

  useEffect(() => {
    if (!inCorso) return undefined;
    const t = setInterval(() => { accademiaAPI.trailerStato(corso.id).catch(() => {}); ricarica(); }, 6000);
    return () => clearInterval(t);
  }, [inCorso, corso?.id, ricarica]);

  const scegli = async (file) => {
    if (!file) return;
    if (file.size > MAX_VIDEO_BYTES) { toast.error('Il video supera i 5 GB.'); return; }
    setOccupato(true);
    try {
      const { data: cred } = await accademiaAPI.trailerPrepara(corso.id, { filename: file.name, size_bytes: file.size });
      setAvanzamento(0); ricarica();
      uploadRef.current = caricaVideo(file, cred, {
        onProgress: setAvanzamento,
        onSuccess: () => { setAvanzamento(100); toast.success('Presentazione caricata: ora Bunny la codifica.'); setTimeout(ricarica, 1500); },
        onError: () => { toast.error('Il caricamento si è interrotto: riprova, riparte da dove era.'); setOccupato(false); },
      });
    } catch (err) {
      const d = err?.response?.data?.detail;
      toast.error(d?.message || (typeof d === 'string' && d) || 'Non sono riuscito a preparare il caricamento.');
      setOccupato(false);
    }
  };
  const togli = async () => {
    if (!window.confirm('Togliere il video di presentazione?')) return;
    try { await accademiaAPI.trailerTogli(corso.id); ricarica(); } catch { toast.error('Non sono riuscito a toglierlo.'); }
  };

  if (!corso) return null;
  if (!corso.bunny_attivo && !v) {
    return <p className="rounded-xl bg-amber-50 px-4 py-3 text-xs text-amber-900">Il caricamento video non è ancora attivo su questo ambiente.</p>;
  }
  return (
    <div data-testid="trailer-editor">
      {v ? (
        <div className="flex flex-wrap items-center gap-3">
          {v.thumbnail_url && <img src={v.thumbnail_url} alt="" className="h-16 w-28 rounded-lg object-cover" />}
          <div className="min-w-0 flex-1 text-sm">
            {v.stato === 'caricamento' && (
              <div><div className="flex items-center justify-between text-xs text-gray-600"><span className="inline-flex items-center gap-1"><Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden /> Caricamento</span><span>{avanzamento != null ? `${avanzamento}%` : ''}</span></div>
              <div className="mt-1 h-2 w-full overflow-hidden rounded-full bg-gray-100"><div className="h-full bg-[#2f5749] transition-all" style={{ width: `${avanzamento || 0}%` }} /></div></div>
            )}
            {v.stato === 'codifica' && <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2.5 py-0.5 text-xs font-medium text-amber-800"><Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden /> In codifica</span>}
            {v.stato === 'pronto' && <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-medium text-emerald-800"><CheckCircle2 className="h-3.5 w-3.5" aria-hidden /> Pronto{v.duration_seconds ? ` · ${fmtDurata(v.duration_seconds)}` : ''}</span>}
            {v.stato === 'errore' && <span className="inline-flex items-center gap-1 rounded-full bg-red-50 px-2.5 py-0.5 text-xs font-medium text-red-800"><AlertCircle className="h-3.5 w-3.5" aria-hidden /> Errore: ricarica il file</span>}
          </div>
          {!inCorso && <label className="cursor-pointer text-xs font-medium text-gray-600 underline-offset-4 hover:underline">Sostituisci<input type="file" accept={FORMATI_VIDEO} className="hidden" onChange={e => scegli(e.target.files?.[0])} /></label>}
          <button type="button" onClick={togli} className="text-xs text-gray-500 hover:text-red-700">Togli</button>
        </div>
      ) : (
        <label className={`flex cursor-pointer items-center gap-3 rounded-xl border-2 border-dashed border-gray-300 px-4 py-4 text-sm text-gray-700 transition hover:border-[#2f5749] hover:bg-[#2f5749]/[0.03] ${occupato ? 'opacity-60' : ''}`}
               data-testid="trailer-dropzone" onDragOver={e => e.preventDefault()} onDrop={e => { e.preventDefault(); scegli(e.dataTransfer.files?.[0]); }}>
          <UploadCloud className="h-5 w-5 flex-none text-[#2f5749]" aria-hidden />
          <span><span className="block font-medium">Trascina qui il video di presentazione, o scegli il file</span><span className="block text-xs text-gray-500">MP4, MOV o WebM. Parte subito, riprende da solo se cade la rete.</span></span>
          <input type="file" accept={FORMATI_VIDEO} className="hidden" disabled={occupato} onChange={e => scegli(e.target.files?.[0])} />
        </label>
      )}
    </div>
  );
}
