/**
 * VERSO LA CIMATICA — gli attrezzi (LB6, 28/8/2026).
 *
 * La cimatica (sabbia su piastra, acqua in coppa) chiede al software
 * quattro cose precise, e questo modulo le fornisce — React-free:
 *
 *   1. TONI E SWEEP DA PORTARE FUORI: il WAV renderizzato offline
 *      (encoder della fonderia) per gli amplificatori e gli attuatori
 *      esterni — l'altoparlante di un telefono sotto i ~200 Hz non
 *      muove niente, e va detto;
 *   2. I PICCHI DI RISONANZA: dalla curva eccitazione→risposta
 *      (misurata dal pannello Risonanze con sweep + microfono) si
 *      estraggono i massimi locali che emergono dal pavimento;
 *   3. IL QUADERNO: gli esperimenti si salvano SU QUESTO DISPOSITIVO
 *      (localStorage, dichiarato nel pannello) — data, campo esplorato,
 *      risonanze trovate. Un quaderno di banco, non un archivio cloud.
 */
import { wavDaCampioni } from './fonderia';

const CHIAVE_QUADERNO = 'fqz_lab_quaderno';
const QUADERNO_MAX = 40;

/* ── i WAV per il mondo fisico ─────────────────────────────────── */

export async function tonoWav(hz, secondi = 30, sampleRate = 44100) {
  const sec = Math.min(120, Math.max(1, +secondi || 30));
  const ctx = new OfflineAudioContext(1, Math.ceil(sec * sampleRate), sampleRate);
  const o = ctx.createOscillator();
  o.frequency.value = hz;
  const g = ctx.createGain();
  g.gain.setValueAtTime(0, 0);
  g.gain.linearRampToValueAtTime(0.9, 0.05);        // rampa: mai un fronte secco
  g.gain.setValueAtTime(0.9, sec - 0.05);
  g.gain.linearRampToValueAtTime(0, sec);
  o.connect(g); g.connect(ctx.destination);
  o.start();
  const reso = await ctx.startRendering();
  return wavDaCampioni(reso.getChannelData(0), sampleRate);
}

export async function sweepWav(da, a, secondi = 60, sampleRate = 44100) {
  const sec = Math.min(300, Math.max(5, +secondi || 60));
  const ctx = new OfflineAudioContext(1, Math.ceil(sec * sampleRate), sampleRate);
  const o = ctx.createOscillator();
  o.frequency.setValueAtTime(Math.max(1, da), 0);
  o.frequency.exponentialRampToValueAtTime(Math.max(1, a), sec);
  const g = ctx.createGain();
  g.gain.setValueAtTime(0, 0);
  g.gain.linearRampToValueAtTime(0.9, 0.05);
  g.gain.setValueAtTime(0.9, sec - 0.05);
  g.gain.linearRampToValueAtTime(0, sec);
  o.connect(g); g.connect(ctx.destination);
  o.start();
  const reso = await ctx.startRendering();
  return wavDaCampioni(reso.getChannelData(0), sampleRate);
}

/* ── i picchi della curva eccitazione→risposta ─────────────────── */

export function trovaPicchi(punti, { sopraDb = 6, massimo = 8 } = {}) {
  if (!punti || punti.length < 8) return [];
  const valori = punti.map((p) => p.db).slice().sort((x, y) => x - y);
  const pavimento = valori[Math.floor(valori.length / 2)];
  const picchi = [];
  /* massimo locale su un intorno di ±2 punti, sopra il pavimento */
  for (let i = 2; i < punti.length - 2; i++) {
    const v = punti[i].db;
    if (v < pavimento + sopraDb) continue;
    if (v >= punti[i - 1].db && v >= punti[i + 1].db
        && v >= punti[i - 2].db && v >= punti[i + 2].db) {
      picchi.push({ hz: punti[i].hz, db: +(v - pavimento).toFixed(1) });
      i += 2;                                     // un picco non si conta due volte
    }
  }
  picchi.sort((x, y) => y.db - x.db);
  return picchi.slice(0, massimo)
    .sort((x, y) => x.hz - y.hz)
    .map((p) => ({ ...p, hz: +p.hz.toFixed(1) }));
}

/* ── il quaderno di banco (localStorage, mai bloccante) ────────── */

export function leggiQuaderno() {
  try {
    const v = JSON.parse(localStorage.getItem(CHIAVE_QUADERNO) || '[]');
    return Array.isArray(v) ? v : [];
  } catch { return []; }
}

/* FA4 — il battesimo: ogni voce nasce con client_id e salvata_il,
   cosi' il quaderno remoto la riconosce su ogni dispositivo */
const _idNuovo = () =>
  Math.random().toString(16).slice(2) + Date.now().toString(16);

export function salvaListaQuaderno(voci) {
  try {
    localStorage.setItem(CHIAVE_QUADERNO,
      JSON.stringify((voci || []).slice(0, QUADERNO_MAX)));
  } catch { /* privato */ }
}

export function salvaNelQuaderno(voce) {
  try {
    const q = leggiQuaderno();
    q.unshift({ ...voce, client_id: _idNuovo(), salvata_il: Date.now() });
    localStorage.setItem(CHIAVE_QUADERNO,
      JSON.stringify(q.slice(0, QUADERNO_MAX)));
    return true;
  } catch { return false; }
}

export function cancellaDalQuaderno(indice) {
  try {
    const q = leggiQuaderno();
    q.splice(indice, 1);
    localStorage.setItem(CHIAVE_QUADERNO, JSON.stringify(q));
    return q;
  } catch { return leggiQuaderno(); }
}

/* banco di prova per i collaudi dalla console */
try { window.__fqzCimatica = { trovaPicchi, tonoWav, sweepWav }; } catch { /* SSR */ }
