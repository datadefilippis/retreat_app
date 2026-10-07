/**
 * upload.js — il video va DIRETTO dal browser a Bunny (AC1, 7/10/2026).
 *
 * Il backend ha gia' creato il video e firmato le credenziali TUS (10
 * minuti): qui si carica con tus-js-client, riprendibile (se cade la rete
 * riparte dal byte dove era), con la barra vera. La chiave API di Bunny
 * non e' mai qui: ci sono solo la firma e la scadenza.
 */
import * as tus from 'tus-js-client';

export const FORMATI_VIDEO = '.mp4,.mov,.m4v,.webm,video/mp4,video/quicktime,video/webm';
export const MAX_VIDEO_BYTES = 5 * 1024 ** 3;

export function caricaVideo(file, credenziali, { onProgress, onSuccess, onError } = {}) {
  const upload = new tus.Upload(file, {
    endpoint: credenziali.tus_endpoint,
    retryDelays: [0, 3000, 5000, 10000, 20000],
    headers: credenziali.headers,
    metadata: { filetype: file.type || 'video/mp4', title: file.name },
    chunkSize: 20 * 1024 * 1024,
    onError: (err) => { if (onError) onError(err); },
    onProgress: (sent, total) => { if (onProgress) onProgress(total ? Math.round((sent / total) * 100) : 0); },
    onSuccess: () => { if (onSuccess) onSuccess(); },
  });
  upload.findPreviousUploads().then((precedenti) => {
    if (precedenti && precedenti.length) upload.resumeFromPreviousUpload(precedenti[0]);
    upload.start();
  }).catch(() => upload.start());
  return upload;
}
