/**
 * LA FONDERIA — la campana rifatta (LB4, 28/8/2026).
 *
 * Dal ritratto (dati) si rifonde il suono: sintesi ADDITIVA — un
 * oscillatore per parziale, il SUO inviluppo esponenziale (il T60
 * misurato), e per i doppietti la coppia vera di oscillatori: il
 * battimento rinasce da solo, perche' e' fisica, non un effetto.
 *
 * Due modi:
 *   - COLPO:  gli inviluppi misurati — il suono muore da solo, come
 *             la campana colpita;
 *   - TENUTO: i parziali reggono, come la campana strofinata — per
 *             la meditazione e la cimatica.
 *
 * React-free e senza contesto proprio: riceve ctx e USCITA (nel Lab
 * e' lab.ingresso → master → ponte; nell'export e' l'OfflineAudioContext)
 * — la regola del ponte resta intatta perche' qui non si decide dove
 * va il suono, lo si consegna.
 */

const ATTACCO_COLPO = 0.008;    // 8 ms: il «ting» senza click
const ATTACCO_TENUTO = 0.06;
const T60_RIPIEGO = 3;          // parziale senza vita misurata
const TETTO_SEC = 20;           // il colpo piu' lungo che rifondiamo
const USCITA_PICCO = 0.6;       // la somma delle ampiezze non supera questo

/* le voci della campana: per ogni parziale acceso (e per il gemello
   del doppietto) frequenza, ampiezza lineare, vita */
export function vociDelRitratto(ritratto, { respiro = 1, spenti = [] } = {}) {
  const voci = [];
  for (const p of ritratto.parziali) {
    if (spenti.includes(p.hz)) continue;
    const vita = (p.t60 || T60_RIPIEGO) * respiro;
    voci.push({ hz: p.hz, amp: Math.pow(10, p.db / 20), vita });
    if (p.doppietto) {
      voci.push({ hz: p.doppietto.hz,
        amp: Math.pow(10, (p.doppietto.db ?? p.db) / 20), vita });
    }
  }
  const somma = voci.reduce((s, v) => s + v.amp, 0) || 1;
  const scala = USCITA_PICCO / somma;
  voci.forEach((v) => { v.amp *= scala; });
  return voci;
}

/** Rifonde la campana dentro (ctx, uscita). Ritorna {ferma, durataSec}. */
export function campana(ctx, uscita, ritratto, opzioni = {}) {
  const { modo = 'colpo' } = opzioni;
  const voci = vociDelRitratto(ritratto, opzioni);
  if (!voci.length) return null;

  const t0 = ctx.currentTime + 0.02;
  const vive = [];
  let durataSec = 0;

  for (const v of voci) {
    const osc = ctx.createOscillator();
    osc.frequency.value = v.hz;
    const gain = ctx.createGain();
    gain.gain.value = 0;
    osc.connect(gain); gain.connect(uscita);
    if (modo === 'colpo') {
      const fine = Math.min(v.vita, TETTO_SEC);
      gain.gain.setValueAtTime(0, t0);
      gain.gain.linearRampToValueAtTime(v.amp, t0 + ATTACCO_COLPO);
      /* T60 = -60 dB: l'esponenziale vera del decadere */
      gain.gain.exponentialRampToValueAtTime(
        Math.max(v.amp * 0.001, 1e-6), t0 + ATTACCO_COLPO + fine);
      osc.start(t0);
      osc.stop(t0 + ATTACCO_COLPO + fine + 0.1);
      durataSec = Math.max(durataSec, ATTACCO_COLPO + fine + 0.1);
    } else {
      gain.gain.setValueAtTime(0, t0);
      gain.gain.linearRampToValueAtTime(v.amp, t0 + ATTACCO_TENUTO);
      osc.start(t0);
    }
    osc.onended = () => { try { gain.disconnect(); } catch { /* gia' */ } };
    vive.push({ osc, gain });
  }

  const ferma = () => {
    const t = ctx.currentTime;
    for (const v of vive) {
      try {
        v.gain.gain.cancelScheduledValues(t);
        v.gain.gain.setValueAtTime(v.gain.gain.value, t);
        v.gain.gain.linearRampToValueAtTime(0, t + 0.15);
        v.osc.stop(t + 0.25);
      } catch { /* gia' spenta */ }
    }
  };
  return { ferma, durataSec };
}

/* ── WAV: 16 bit PCM mono — il formato che ogni ampli capisce ──── */
function wavDaCampioni(campioni, sampleRate) {
  const n = campioni.length;
  const buf = new ArrayBuffer(44 + n * 2);
  const v = new DataView(buf);
  const scrivi = (o, s2) => { for (let i = 0; i < s2.length; i++) v.setUint8(o + i, s2.charCodeAt(i)); };
  scrivi(0, 'RIFF'); v.setUint32(4, 36 + n * 2, true); scrivi(8, 'WAVE');
  scrivi(12, 'fmt '); v.setUint32(16, 16, true);
  v.setUint16(20, 1, true); v.setUint16(22, 1, true);
  v.setUint32(24, sampleRate, true); v.setUint32(28, sampleRate * 2, true);
  v.setUint16(32, 2, true); v.setUint16(34, 16, true);
  scrivi(36, 'data'); v.setUint32(40, n * 2, true);
  for (let i = 0; i < n; i++) {
    const s2 = Math.max(-1, Math.min(1, campioni[i]));
    v.setInt16(44 + i * 2, s2 < 0 ? s2 * 0x8000 : s2 * 0x7FFF, true);
  }
  return new Blob([buf], { type: 'audio/wav' });
}

/** Il render OFFLINE della campana rifatta → Blob WAV. Per il colpo la
 *  durata viene dagli inviluppi; per il tenuto va dichiarata. */
export async function renderizzaWav(ritratto, opzioni = {}) {
  const { modo = 'colpo', secondi = null, sampleRate = 44100 } = opzioni;
  const durata = modo === 'colpo'
    ? Math.min(TETTO_SEC + 0.5,
        Math.max(...vociDelRitratto(ritratto, opzioni).map((v) => v.vita), 1) + 0.5)
    : Math.min(60, Math.max(1, +secondi || 10));
  const ctx = new OfflineAudioContext(1, Math.ceil(durata * sampleRate), sampleRate);
  const esito = campana(ctx, ctx.destination, ritratto, opzioni);
  if (!esito) return null;
  const reso = await ctx.startRendering();
  const campioni = reso.getChannelData(0);
  if (modo === 'tenuto') {
    /* dissolvenza finale di 200 ms scolpita nei campioni */
    const n = campioni.length, coda = Math.min(n, Math.floor(sampleRate * 0.2));
    for (let i = 0; i < coda; i++) campioni[n - 1 - i] *= i / coda;
  }
  return wavDaCampioni(campioni, sampleRate);
}

/* banco di prova per i collaudi dalla console */
try { window.__fqzFonderia = { vociDelRitratto, campana, renderizzaWav }; } catch { /* SSR */ }
