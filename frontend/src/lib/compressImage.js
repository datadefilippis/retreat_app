// PV1 (docs/PROFILO_VERIFICATO_PIANO_2026-07.md) — compressione foto
// lato client, nativa e senza dipendenze: createImageBitmap → canvas →
// toBlob('image/webp'). Un file da 8-12MB scende a 150-400KB PRIMA di
// partire, così l'operatore non pensa mai a peso e formati (il limite
// 2MB backend resta come cintura di sicurezza).
//
// Contratto fail-safe: questa funzione NON lancia mai. Se il file non
// è un'immagine decodificabile dal browser (es. HEIC su Chrome), se il
// canvas fallisce, o se il risultato compresso è più pesante
// dell'originale, ritorna il File originale e lascia fare al server
// (che da PV1 converte anche HEIC/HEIF in WebP).

// Formati da NON ricomprimere: svg è vettoriale (il canvas lo
// rasterizzerebbe), gif può essere animata (il canvas terrebbe solo il
// primo frame).
const SKIP_TYPES = new Set(['image/svg+xml', 'image/gif']);

function canvasToBlob(canvas, type, quality) {
  return new Promise(resolve => {
    try {
      canvas.toBlob(blob => resolve(blob), type, quality);
    } catch {
      resolve(null);
    }
  });
}

// Decodifica il file in qualcosa di disegnabile su canvas.
// 1. createImageBitmap con imageOrientation:'from-image' (EXIF corretto)
// 2. createImageBitmap senza opzioni (browser che non supportano l'opzione)
// 3. <img> + objectURL (fallback storico; i browser recenti applicano
//    comunque l'orientamento EXIF alle <img>)
async function decodeImage(file) {
  if (typeof createImageBitmap === 'function') {
    try {
      return await createImageBitmap(file, { imageOrientation: 'from-image' });
    } catch { /* opzione non supportata o decode fallito: si riprova */ }
    try {
      return await createImageBitmap(file);
    } catch { /* formato non decodificabile: si tenta via <img> */ }
  }
  return new Promise(resolve => {
    const url = URL.createObjectURL(file);
    const img = new Image();
    img.onload = () => { URL.revokeObjectURL(url); resolve(img); };
    img.onerror = () => { URL.revokeObjectURL(url); resolve(null); };
    img.src = url;
  });
}

/**
 * Comprimi un'immagine lato client prima dell'upload.
 *
 * @param {File} file       il file scelto dall'utente
 * @param {object} [opts]
 * @param {number} [opts.maxSide=1600]  lato lungo massimo in px
 * @param {number} [opts.quality=0.82]  qualità WebP (0-1)
 * @returns {Promise<File>} un nuovo File .webp (o .jpg se il browser
 *   non produce WebP), oppure il file ORIGINALE se non decodificabile
 *   o se già più leggero del risultato compresso.
 */
export async function compressImage(file, { maxSide = 1600, quality = 0.82 } = {}) {
  try {
    if (!file || !(file instanceof Blob)) return file;
    if (SKIP_TYPES.has(file.type)) return file;

    const source = await decodeImage(file);
    if (!source) return file; // es. HEIC su Chrome → ci pensa il server

    const srcW = source.width || source.naturalWidth;
    const srcH = source.height || source.naturalHeight;
    if (!srcW || !srcH) return file;

    const scale = Math.min(1, maxSide / Math.max(srcW, srcH));
    const w = Math.max(1, Math.round(srcW * scale));
    const h = Math.max(1, Math.round(srcH * scale));

    const canvas = document.createElement('canvas');
    canvas.width = w;
    canvas.height = h;
    const ctx = canvas.getContext('2d');
    if (!ctx) return file;
    ctx.drawImage(source, 0, 0, w, h);
    if (typeof source.close === 'function') source.close();

    let blob = await canvasToBlob(canvas, 'image/webp', quality);
    let ext = '.webp';
    if (!blob || blob.type !== 'image/webp') {
      // Safari vecchi: niente WebP encoder → jpeg q0.85
      blob = await canvasToBlob(canvas, 'image/jpeg', 0.85);
      ext = '.jpg';
    }
    if (!blob) return file;

    // Se l'originale era già più leggero (foto piccola/molto
    // compressa), usare il più piccolo dei due.
    if (blob.size >= file.size) return file;

    const base = (file.name || 'foto').replace(/\.[^.]*$/, '') || 'foto';
    return new File([blob], `${base}${ext}`, { type: blob.type });
  } catch {
    return file; // mai bloccare un upload per colpa della compressione
  }
}

export default compressImage;
