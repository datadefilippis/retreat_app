/**
 * I SEGNALI DEL BANCO (LM1, 5/9/2026) — suoni sintetici per collaudare
 * il ritrattista SENZA microfono: campane con modi inarmonici e
 * doppietti che battono, voce tenuta con vibrato, glissando, parlato,
 * bicchiere, corda. Il rumore e' SEEDATO (mulberry32): due esecuzioni
 * danno gli stessi campioni, altrimenti un caso al limite cambia
 * verdetto fra un giro e l'altro (pagato il 5/9).
 *
 * Il banco riproduce il bug della campana forte del founder (il
 * tracker salta fra i modi → «melodia»); la CURA si tara sui WAV veri
 * (LM0), e quando arriva questi casi passano da «attesi» a «pretesi».
 */
let semeRnd = 20260905;
function mulberry32() {
  semeRnd |= 0; semeRnd = (semeRnd + 0x6D2B79F5) | 0;
  let t = Math.imul(semeRnd ^ (semeRnd >>> 15), 1 | semeRnd);
  t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
}
export function riseminaRnd(seme = 20260905) { semeRnd = seme; }
export const sr = 48000, N = sr * 6;
const rnd = () => mulberry32() - 0.5;
export function campana({ forza = 0.6, acuti = [0.9, 0.6, 0.3], batti = [0, 0, 0, 0], limiter = false, clip = false, wah = 0, f0 = 214 }) {
  const modi = [[1, 1.0, 9.0], [2.71, acuti[0], 3.5], [5.15, acuti[1], 1.6], [8.3, acuti[2], 0.8]];
  const x = new Float32Array(N); const t0 = Math.floor(sr * 0.4);
  for (let i = 0; i < N; i++) {
    let v = rnd() * 0.002;
    if (i >= t0) {
      const t = (i - t0) / sr;
      modi.forEach(([r, g, tau], k) => {
        const b = batti[k] ? (0.5 + 0.5 * Math.cos(2 * Math.PI * batti[k] * t)) : 1;
        v += forza * g * b * Math.exp(-t / tau) * Math.sin(2 * Math.PI * r * f0 * t);
      });
      if (wah) v *= 1 + wah * Math.sin(2 * Math.PI * 0.7 * t);
      if (t < 0.03) v += forza * rnd() * 0.8 * Math.exp(-t / 0.008);
    }
    if (limiter) v = Math.tanh(v * 2.5) / 1.2;
    if (clip) v = Math.max(-1, Math.min(1, v));
    x[i] = v;
  }
  return x;
}
/* voce tenuta: armoniche intere, vibrato ±1,2% a 5,5 Hz, attacco 0,3 s, tenuta fino alla fine */
export function voce({ f0 = 146, vib = 0.012, forza = 0.4, glide = 0, parlato = false }) {
  const x = new Float32Array(N); let fase = 0;
  const arm = [1, 0.7, 0.5, 0.35, 0.2, 0.12, 0.08, 0.05];
  for (let i = 0; i < N; i++) {
    const t = i / sr;
    let f = f0 * (1 + vib * Math.sin(2 * Math.PI * 5.5 * t)) * Math.pow(2, glide * t / 6);
    if (parlato) f = f0 * (1 + 0.25 * Math.sin(2 * Math.PI * 0.9 * t) + 0.1 * Math.sin(2 * Math.PI * 3.1 * t));
    fase += 2 * Math.PI * f / sr;
    const env = Math.min(1, t / 0.3) * (parlato ? (0.6 + 0.4 * Math.abs(Math.sin(2 * Math.PI * 2.2 * t))) : 1);
    let v = 0; arm.forEach((g, k) => { v += g * Math.sin((k + 1) * fase); });
    x[i] = forza * env * v / 3 + rnd() * 0.003;
  }
  return x;
}
/* bicchiere: due modi, il secondo quasi armonico ma non esatto, coda breve */
export function bicchiere({ forza = 0.5 }) {
  const x = new Float32Array(N); const t0 = Math.floor(sr * 0.5);
  for (let i = 0; i < N; i++) {
    let v = rnd() * 0.002;
    if (i >= t0) { const t = (i - t0) / sr;
      v += forza * Math.exp(-t / 2.2) * Math.sin(2 * Math.PI * 1180 * t) + forza * 0.35 * Math.exp(-t / 0.9) * Math.sin(2 * Math.PI * 2570 * t);
      if (t < 0.01) v += forza * rnd() * 0.6; }
    x[i] = v;
  }
  return x;
}
/* corda pizzicata: armonica, decade */
export function corda({ forza = 0.5, f0 = 110 }) {
  const x = new Float32Array(N); const t0 = Math.floor(sr * 0.5);
  for (let i = 0; i < N; i++) {
    let v = rnd() * 0.002;
    if (i >= t0) { const t = (i - t0) / sr;
      for (let k = 1; k <= 10; k++) v += forza * Math.exp(-t * k / 3) / k * Math.sin(2 * Math.PI * k * f0 * (1 + 0.0004 * k * k) * t); }
    x[i] = v;
  }
  return x;
}
export function casi() {
  const fabbrica = (f) => { riseminaRnd(); return f(); };
  return {
    'campana delicata + doppietti': fabbrica(() => campana({ forza: 0.12, acuti: [0.2, 0.05, 0.02], batti: [2.3, 4, 6, 0] })),
    'campana FORTE + doppietti': fabbrica(() => campana({ forza: 0.7, batti: [2.3, 4, 6, 0] })),
    'campana forte + limiter mic': fabbrica(() => campana({ forza: 1.2, limiter: true, batti: [2.3, 4, 6, 0] })),
    'campana fortissima clip + wah': fabbrica(() => campana({ forza: 2.0, clip: true, batti: [2.3, 4, 6, 0], wah: 0.5 })),
    'campana acuti dominanti': fabbrica(() => campana({ forza: 0.7, acuti: [1.6, 1.2, 0.6], batti: [2.3, 4, 6, 3] })),
    'campana grave 110 Hz forte': fabbrica(() => campana({ forza: 0.8, f0: 110, batti: [1.5, 3, 5, 0] })),
    'voce tenuta con vibrato': fabbrica(() => voce({})),
    'voce tenuta forte': fabbrica(() => voce({ forza: 0.9 })),
    'voce glissando (melodia)': fabbrica(() => voce({ glide: 0.8, vib: 0.004 })),
    'parlato': fabbrica(() => voce({ parlato: true })),
    'bicchiere': fabbrica(() => bicchiere({})),
    'corda pizzicata': fabbrica(() => corda({})),
  };
}
/* il verdetto atteso; «lm1:» = oggi sbaglia, la cura arriva coi WAV veri */
export const ATTESO = {
  'campana delicata + doppietti': 'modi', 'campana FORTE + doppietti': 'lm1:modi', 'campana forte + limiter mic': 'lm1:modi',
  'campana fortissima clip + wah': 'lm1:modi', 'campana acuti dominanti': 'lm1:modi', 'campana grave 110 Hz forte': 'lm1:modi',
  /* la voce sintetica con vibrato cade sul cancello armonico (le bande
     laterali contano come picchi «forti»): anche questa e' materia LM1 */
  'voce tenuta con vibrato': 'lm1:intonato', 'voce tenuta forte': 'intonato|modi', 'voce glissando (melodia)': 'melodia',
  'parlato': 'melodia', 'bicchiere': 'modi', 'corda pizzicata': 'intonato|modi',
};
