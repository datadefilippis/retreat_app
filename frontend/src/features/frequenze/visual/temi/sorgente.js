/**
 * Aurya Mode — tema «Sorgente» (AV1-bis, 21/8/2026).
 *
 * Il primo tentativo (un mandala di archi e cerchi) era GEOMETRIA:
 * il founder l'ha bocciato con ragione — i suoi riferimenti sono
 * LUCE. Particelle che danzano, veli come aurore, onde che nascono da
 * un centro luminoso, oro su nero. Questo tema e' costruito con quel
 * linguaggio: niente tratti, solo bagliori morbidi che si sommano.
 *
 * Come si ottiene quel look a 60 fps: NON si disegnano gradienti a
 * ogni fotogramma (costerebbe troppo e sembrerebbe comunque «vettoriale»).
 * Si pre-renderizza UNA volta uno sprite di luce morbida per colore, e
 * poi lo si timbra centinaia di volte in modalita' additiva: dove i
 * timbri si sovrappongono la luce si somma, ed e' la somma a creare
 * nuclei caldi, veli e nebbie — come nei riferimenti.
 *
 * Il movimento e' un CAMPO DI FLUSSO (somma di seni lenti): le
 * particelle non vanno in linea retta e non tremano a caso — scorrono
 * come dentro un fluido, con una risalita dolce. E' la differenza fra
 * «particelle che danzano» e coriandoli.
 *
 * Col suono:
 * - il CUORE respira coi bassi, e' il corpo del suono;
 * - il FLUSSO accelera con energia e medi — la parte che canta muove;
 * - le SCINTILLE d'osso si accendono sugli alti, l'aria;
 * - un colpo apre un'ONDA morbida dal cuore (un anello di luce, non
 *   un cerchio tracciato).
 *
 * Colori: SOLO la famiglia della marca. L'oro domina come nei
 * riferimenti; il viola e l'acqua esistono appena, nei veli piu'
 * profondi — la sfumatura «trascendente», mai un arcobaleno.
 */

export const COLORI = {
  fondo: '#0C1618',      // --ink
  oro: '#C9B37E',        // --lamp
  osso: '#E9E4D9',       // --bone
  acqua: '#66B79C',      // --water
  viola: '#9B8BC4',      // --violet
};

export const NOME = 'Sorgente';
export const DESCRIZIONE = 'Luce che respira col suono';

const TAU = Math.PI * 2;
/* La scia: quanto del fotogramma precedente sopravvive. Bassa = scie
   lunghe e accumulo luminoso (il look dei riferimenti). Non scendere
   troppo o il nero smette di essere nero. */
const SCIA = 0.16;

const esa = (hex) => {
  const n = parseInt(hex.slice(1), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
};

/* ── gli sprite di luce: pre-renderizzati una volta ─────────────── */
let SPRITES = null;
function spriteLuce(hex, dim) {
  const c = document.createElement('canvas');
  c.width = c.height = dim;
  const g = c.getContext('2d');
  const [r, gg, b] = esa(hex);
  const gr = g.createRadialGradient(dim / 2, dim / 2, 0, dim / 2, dim / 2, dim / 2);
  gr.addColorStop(0, `rgba(${r},${gg},${b},0.85)`);
  gr.addColorStop(0.25, `rgba(${r},${gg},${b},0.32)`);
  gr.addColorStop(0.6, `rgba(${r},${gg},${b},0.08)`);
  gr.addColorStop(1, `rgba(${r},${gg},${b},0)`);
  g.fillStyle = gr;
  g.fillRect(0, 0, dim, dim);
  return c;
}
function spriteAnello(hex, dim) {
  const c = document.createElement('canvas');
  c.width = c.height = dim;
  const g = c.getContext('2d');
  const [r, gg, b] = esa(hex);
  const gr = g.createRadialGradient(dim / 2, dim / 2, 0, dim / 2, dim / 2, dim / 2);
  gr.addColorStop(0.62, `rgba(${r},${gg},${b},0)`);
  gr.addColorStop(0.78, `rgba(${r},${gg},${b},0.5)`);
  gr.addColorStop(0.9, `rgba(${r},${gg},${b},0.12)`);
  gr.addColorStop(1, `rgba(${r},${gg},${b},0)`);
  g.fillStyle = gr;
  g.fillRect(0, 0, dim, dim);
  return c;
}
function sprites() {
  if (!SPRITES) {
    SPRITES = {
      oro: spriteLuce(COLORI.oro, 128),
      osso: spriteLuce(COLORI.osso, 128),
      acqua: spriteLuce(COLORI.acqua, 128),
      viola: spriteLuce(COLORI.viola, 128),
      anello: spriteAnello(COLORI.oro, 256),
    };
  }
  return SPRITES;
}

/* ── il campo di flusso: un fluido lento, non il caso ───────────── */
function flusso(x, y, t) {
  return Math.sin(x * 0.0016 + t * 0.19)
       + Math.cos(y * 0.0013 - t * 0.16)
       + Math.sin((x + y) * 0.0007 + t * 0.10);
}

/* Lo stato vive per-canvas: la stessa pagina puo' avere piu' tele
   senza che si rubino le particelle a vicenda. */
const STATI = new WeakMap();
function statoDi(g, w, h) {
  let s = STATI.get(g);
  if (s && s.w === w && s.h === h) return s;
  const N = 240;
  s = {
    w, h,
    particelle: Array.from({ length: N }, (_, i) => ({
      x: Math.random() * w,
      y: Math.random() * h,
      z: 0.35 + Math.random() * 0.65,       // profondita': dimensione e velocita'
      col: i % 17 === 0 ? 'viola' : i % 11 === 0 ? 'acqua'
        : i % 5 === 0 ? 'osso' : 'oro',
      fase: Math.random() * TAU,
    })),
    veli: Array.from({ length: 6 }, (_, i) => ({
      a: (i / 6) * TAU,
      r: 0.22 + (i % 3) * 0.14,
      col: i === 4 ? 'viola' : i === 5 ? 'acqua' : 'oro',
      giro: 0.05 + (i % 3) * 0.03,
    })),
  };
  STATI.set(g, s);
  return s;
}

/**
 * @param g    contesto 2D
 * @param L    la lettura (analisi.js)
 * @param t    secondi dall'inizio
 * @param dim  { w, h } pixel del canvas
 */
export function disegna(g, L, t, { w, h }) {
  const S = sprites();
  const st = statoDi(g, w, h);
  const cx = w / 2, cy = h * 0.56;          // il cuore poco sotto il centro, come nei riferimenti
  const base = Math.min(w, h);

  // il velo del tempo: la scia che accumula la luce
  g.globalCompositeOperation = 'source-over';
  g.fillStyle = `rgba(12,22,24,${SCIA})`;   // COLORI.fondo
  g.fillRect(0, 0, w, h);
  g.globalCompositeOperation = 'lighter';

  const { bassi, medi, alti } = L.bande;
  const respiro = 0.8 + bassi * 0.5;
  const vento = 0.25 + L.energia * 1.1 + medi * 0.5;

  // ── 1. i veli: aurore larghe, quasi invisibili una a una ──
  for (const v of st.veli) {
    const a = v.a + t * v.giro;
    const r = base * v.r;
    const x = cx + Math.cos(a) * r * 0.7;
    const y = cy + Math.sin(a * 0.8) * r * 0.5;
    const dim = base * (0.55 + v.r) * respiro;
    g.globalAlpha = (v.col === 'oro' ? 0.05 : 0.03) + bassi * 0.04;
    g.drawImage(S[v.col], x - dim / 2, y - dim / 2, dim, dim);
  }

  // ── 2. la colonna: l'asse di luce che sale dal cuore ──
  /* passo fitto e dimensioni sovrapposte: a passi larghi la colonna
     diventava una collana di perle (visto al primo giro), non un
     fascio. Con 18 timbri che si coprono a meta' la luce e' continua. */
  const colH = base * (0.5 + medi * 0.35);
  for (let i = 0; i < 18; i++) {
    const u = i / 18;
    const y = cy - u * colH;
    const dim = base * (0.15 - u * 0.09) * respiro;
    g.globalAlpha = (0.022 + medi * 0.03) * (1 - u * 0.5);
    g.drawImage(S.oro, cx - dim / 2, y - dim / 2, dim, dim);
  }

  // ── 3. le particelle nel flusso ──
  for (const p of st.particelle) {
    const ang = flusso(p.x, p.y, t) * Math.PI;
    const vel = vento * p.z * (base / 900);
    p.x += Math.cos(ang) * vel * 1.6;
    p.y += Math.sin(ang) * vel * 1.6 - vel * 0.9;   // la risalita dolce
    // rientro morbido dai bordi
    if (p.y < -20) { p.y = h + 20; p.x = Math.random() * w; }
    if (p.x < -20) p.x = w + 20;
    if (p.x > w + 20) p.x = -20;
    if (p.y > h + 20) p.y = -20;

    const twinkle = 0.7 + 0.3 * Math.sin(t * 2.1 + p.fase);
    const vicino = 1 - Math.min(1, Math.hypot(p.x - cx, p.y - cy) / (base * 0.75));
    const dim = base * 0.012 * p.z * (1 + bassi * 0.7) * (0.7 + vicino * 0.8);
    g.globalAlpha = (0.10 + L.energia * 0.30) * twinkle * p.z
      * (p.col === 'oro' ? 1 : p.col === 'osso' ? 0.9 : 0.45);
    g.drawImage(S[p.col], p.x - dim / 2, p.y - dim / 2, dim, dim);
  }

  // ── 4. le scintille dell'aria: brevi, d'osso, sugli alti ──
  const nSc = Math.round(alti * 26);
  for (let i = 0; i < nSc; i++) {
    const a = i * 2.399963 + t * 0.6;       // angolo aureo: mai una griglia
    const r = base * (0.1 + ((i * 0.173 + t * 0.05) % 1) * 0.5);
    const dim = base * 0.008 * (0.6 + alti);
    g.globalAlpha = 0.2 + alti * 0.4;
    g.drawImage(S.osso, cx + Math.cos(a) * r - dim / 2,
      cy + Math.sin(a) * r * 0.8 - dim / 2, dim, dim);
  }

  // ── 5. l'onda del colpo: un anello di luce, non un cerchio tracciato ──
  if (L.picco > 0.02) {
    const dim = base * (0.35 + (1 - L.picco) * 1.1);
    g.globalAlpha = L.picco * 0.5;
    g.drawImage(S.anello, cx - dim / 2, cy - dim / 2, dim, dim);
  }

  // ── 6. il cuore: strati di luce, dal bianco caldo all'oro ──
  const cuori = [
    ['osso', 0.10, 0.5 + L.energia * 0.5],
    ['oro', 0.22, 0.30 + bassi * 0.30],
    ['oro', 0.45, 0.12 + bassi * 0.12],
  ];
  for (const [col, dim, alfa] of cuori) {
    const d = base * dim * respiro;
    g.globalAlpha = alfa;
    g.drawImage(S[col], cx - d / 2, cy - d / 2, d, d);
  }

  g.globalAlpha = 1;
  g.globalCompositeOperation = 'source-over';
}
