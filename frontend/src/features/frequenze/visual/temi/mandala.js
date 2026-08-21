/**
 * Aurya Mode — tema «Mandala» (AV1, 21/8/2026).
 *
 * La firma visiva di casa: geometria che si apre e si chiude col
 * respiro del suono, nei colori della marca — oro, verde acqua, viola
 * tenue su petrolio. Niente arcobaleno: un video esportato da qui deve
 * essere riconoscibile come Aurya al primo sguardo (decisione founder
 * 21/8: «stile pulito di Aurya con colori trascendenti»).
 *
 * Come si muove, e perche':
 * - il RAGGIO respira coi bassi — il corpo del suono e' li';
 * - i PETALI ruotano coi medi, dove stanno voce e armoniche: e' la
 *   parte che «canta», ed e' giusto che sia lei a girare;
 * - le SCINTILLE nascono sugli alti, l'aria del suono;
 * - un colpo apre un'ONDA che si allarga e svanisce.
 *
 * Su una meditazione senza percussioni non pulsa: respira. E' voluto —
 * la scena deve accompagnare, non intrattenere.
 *
 * Canvas 2D e non WebGL: a questa densita' regge senza problemi, e non
 * porta in dote una libreria. WebGL entra quando entreranno i temi
 * densi (AV4), non prima.
 */

/* La famiglia di accenti e' quella del mondo Sound (frequenze.css):
   se cambia li', cambia qui — la guardia di parita' lo verifica. */
export const COLORI = {
  fondo: '#0C1618',      // --ink
  oro: '#C9B37E',        // --lamp
  acqua: '#66B79C',      // --water
  viola: '#9B8BC4',      // --violet
  osso: '#E9E4D9',       // --bone
};

const TAU = Math.PI * 2;
const rgba = (hex, a) => {
  const n = parseInt(hex.slice(1), 16);
  return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${a})`;
};

export const NOME = 'Mandala';
export const DESCRIZIONE = "La geometria che respira col suono";

/**
 * @param g      contesto 2D
 * @param L      la lettura (analisi.js)
 * @param t      secondi dall'inizio
 * @param dim    { w, h } in pixel del canvas
 */
export function disegna(g, L, t, { w, h }) {
  const cx = w / 2, cy = h / 2;
  const base = Math.min(w, h) * 0.5;

  /* Scia invece di cancellare: ogni fotogramma vela il precedente, e
     il movimento lascia una memoria luminosa. E' cio' che distingue
     una scena viva da un disegno che sbatte. */
  g.fillStyle = rgba(COLORI.fondo, 0.22);
  g.fillRect(0, 0, w, h);

  const { bassi, medi, medioAlti, alti } = L.bande;
  const respiro = 0.86 + bassi * 0.30 + L.energia * 0.10;
  const rotazione = t * 0.05 + medi * 1.4;

  g.save();
  g.translate(cx, cy);
  /* Somma della luce: i tratti che si sovrappongono si sommano invece
     di coprirsi — e' questo che fa il bagliore, non un filtro blur
     (che a 60 fps costerebbe caro). */
  g.globalCompositeOperation = 'lighter';

  // ── 1. l'alone: la presenza del suono prima di ogni forma ──
  const alone = g.createRadialGradient(0, 0, base * 0.05, 0, 0, base * respiro);
  alone.addColorStop(0, rgba(COLORI.osso, 0.10 + L.energia * 0.22));
  alone.addColorStop(0.35, rgba(COLORI.oro, 0.07 + bassi * 0.14));
  alone.addColorStop(0.75, rgba(COLORI.viola, 0.05 + medi * 0.08));
  alone.addColorStop(1, rgba(COLORI.fondo, 0));
  g.fillStyle = alone;
  g.beginPath(); g.arc(0, 0, base * respiro, 0, TAU); g.fill();

  // ── 2. i petali: tre corone che ruotano a velocita' diverse ──
  const CORONE = [
    { n: 12, r: 0.30, col: COLORI.oro, sp: 1.0, sp2: 0.55 },
    { n: 18, r: 0.44, col: COLORI.acqua, sp: -0.62, sp2: 0.42 },
    { n: 24, r: 0.58, col: COLORI.viola, sp: 0.38, sp2: 0.30 },
  ];
  for (const c of CORONE) {
    const r = base * c.r * respiro;
    const apertura = 0.35 + medi * 0.5 + L.picco * 0.25;
    g.lineWidth = Math.max(1, base * 0.0035);
    g.strokeStyle = rgba(c.col, 0.16 + L.energia * 0.34);
    for (let i = 0; i < c.n; i++) {
      const a = (i / c.n) * TAU + rotazione * c.sp;
      const lung = r * (0.22 + medioAlti * 0.20);
      // il petalo e' un arco, non un segmento: la curva rende la
      // geometria organica invece che meccanica
      g.beginPath();
      g.arc(Math.cos(a) * r, Math.sin(a) * r, lung, a - apertura, a + apertura);
      g.stroke();
    }
    // l'anello che tiene insieme la corona
    g.strokeStyle = rgba(c.col, 0.08 + bassi * 0.16);
    g.lineWidth = Math.max(1, base * 0.002);
    g.beginPath(); g.arc(0, 0, r, 0, TAU); g.stroke();
  }

  // ── 3. l'onda del colpo: si allarga e svanisce ──
  if (L.picco > 0.02) {
    const r = base * (0.55 + (1 - L.picco) * 0.55);
    g.strokeStyle = rgba(COLORI.osso, L.picco * 0.30);
    g.lineWidth = Math.max(1, base * 0.004 * L.picco);
    g.beginPath(); g.arc(0, 0, r, 0, TAU); g.stroke();
  }

  // ── 4. le scintille: l'aria del suono ──
  const quante = Math.round(alti * 90);
  for (let i = 0; i < quante; i++) {
    // deterministiche nell'angolo (non tremolano a caso), vive nel raggio
    const a = (i * 2.399963) + t * 0.35;      // angolo aureo: distribuzione mai regolare
    const r = base * (0.28 + ((i * 0.137 + t * 0.08) % 1) * 0.62 * respiro);
    const s = base * 0.0025 * (0.5 + alti);
    g.fillStyle = rgba(i % 3 === 0 ? COLORI.osso : COLORI.oro, 0.25 + alti * 0.5);
    g.beginPath(); g.arc(Math.cos(a) * r, Math.sin(a) * r, s, 0, TAU); g.fill();
  }

  // ── 5. il cuore ──
  const cuore = g.createRadialGradient(0, 0, 0, 0, 0, base * (0.09 + bassi * 0.06));
  cuore.addColorStop(0, rgba(COLORI.osso, 0.55 + L.energia * 0.4));
  cuore.addColorStop(0.5, rgba(COLORI.oro, 0.28));
  cuore.addColorStop(1, rgba(COLORI.oro, 0));
  g.fillStyle = cuore;
  g.beginPath(); g.arc(0, 0, base * (0.09 + bassi * 0.06), 0, TAU); g.fill();

  g.restore();
  g.globalCompositeOperation = 'source-over';
}
