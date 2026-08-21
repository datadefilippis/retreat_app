/**
 * Aurya Mode — tema «Sorgente», seconda stesura (22/8/2026).
 *
 * La prima stesura era LUCE ma troppo poca: un cuore, qualche velo,
 * polvere. Il founder ha chiesto la sua griglia di riferimenti per
 * intero — particelle che danzano, veli d'aurora, onde concentriche,
 * geometrie sacre che pulsano, flussi come acqua, energia che
 * irradia. Questa stesura li porta TUTTI, come strati di una stessa
 * scena, perche' i riquadri di quella griglia sono facce dello stesso
 * mondo: luce d'oro su un cielo di petrolio.
 *
 * Gli strati, dal fondo alla superficie:
 *   1. NEBULOSE — tre ammassi larghi che ruotano lenti: il cielo;
 *   2. NASTRI D'AURORA — fasce sinuose che attraversano la scena e
 *      ondeggiano coi medi: i «veli di luce eterea»;
 *   3. POLVERE — particelle nel campo di flusso, la risalita dolce;
 *   4. SCIAME — particelle in ORBITA ellittica attorno al cuore: e'
 *      lo strato che rende la scena viva anche a suono fermo, e coi
 *      picchi le orbite si allargano;
 *   5. GEOMETRIA SACRA — una corona di nodi con corde di luce che
 *      pulsa coi medi: tenue, fatta di bagliori, mai da CAD;
 *   6. RAGGI — sul colpo, lame di luce morbida che irradiano;
 *   7. CUORE — strati osso→oro con petali interni che ruotano.
 *
 * Tecnica invariata (sprite additivi pre-renderizzati, campo di
 * flusso): e' la DENSITA' e il movimento a piu' velocita' che fanno
 * l'immersione — strati lenti sotto, vivi sopra.
 *
 * Colori: solo la famiglia della marca. Oro dominante, osso per i
 * nuclei, viola e acqua nelle profondita'.
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
/* La scia: quanto del fotogramma precedente sopravvive. Piu' bassa di
   prima (0.16 → 0.11): con lo sciame in orbita le scie lunghe SONO il
   disegno — ogni particella si porta dietro il proprio filo di luce. */
const SCIA = 0.11;

const esa = (hex) => {
  const n = parseInt(hex.slice(1), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
};

/* ── sprite pre-renderizzati: tondo, allungato, anello ──────────── */
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
/* Il timbro allungato: lo stesso sprite tondo, schiacciato e ruotato.
   E' cosi' che nascono petali, raggi e segmenti di nastro senza
   pre-renderizzare una forma per ciascuno. */
function timbro(g, S, col, x, y, lung, larg, ang, alfa) {
  g.save();
  g.translate(x, y);
  g.rotate(ang);
  g.globalAlpha = alfa;
  g.drawImage(S[col], -lung / 2, -larg / 2, lung, larg);
  g.restore();
}

/* ── il campo di flusso: un fluido lento, non il caso ───────────── */
function flusso(x, y, t) {
  return Math.sin(x * 0.0016 + t * 0.19)
       + Math.cos(y * 0.0013 - t * 0.16)
       + Math.sin((x + y) * 0.0007 + t * 0.10);
}

/* Stato per-canvas: piu' tele senza rubarsi le particelle. */
const STATI = new WeakMap();
function statoDi(g, w, h) {
  let s = STATI.get(g);
  if (s && s.w === w && s.h === h) return s;
  s = {
    w, h,
    polvere: Array.from({ length: 240 }, (_, i) => ({
      x: Math.random() * w, y: Math.random() * h,
      z: 0.35 + Math.random() * 0.65,
      col: i % 17 === 0 ? 'viola' : i % 11 === 0 ? 'acqua'
        : i % 5 === 0 ? 'osso' : 'oro',
      fase: Math.random() * TAU,
    })),
    /* lo sciame: orbite ellittiche attorno al cuore, ognuna col suo
       raggio, inclinazione e verso — un piccolo sistema solare */
    sciame: Array.from({ length: 150 }, (_, i) => ({
      a: Math.random() * TAU,
      r: 0.14 + Math.random() * 0.45,
      ecc: 0.55 + Math.random() * 0.4,         // schiacciamento dell'ellisse
      incl: (i % 5) * (TAU / 10) + Math.random() * 0.3,
      vel: (0.12 + Math.random() * 0.3) * (i % 2 ? 1 : -1),
      z: 0.4 + Math.random() * 0.6,
      col: i % 13 === 0 ? 'acqua' : i % 7 === 0 ? 'osso' : 'oro',
      fase: Math.random() * TAU,
    })),
    nebulose: Array.from({ length: 3 }, (_, i) => ({
      a0: (i / 3) * TAU, r: 0.34 + i * 0.16,
      giro: (0.014 + i * 0.008) * (i % 2 ? 1 : -1),
      col: i === 1 ? 'viola' : i === 2 ? 'acqua' : 'oro',
      grumi: 8,
    })),
    nastri: Array.from({ length: 3 }, (_, i) => ({
      y0: 0.26 + i * 0.24,
      amp: 0.10 + (i % 2) * 0.06,
      onda: 1.6 + i * 0.7,
      velo: 0.10 + i * 0.05,
      col: i === 2 ? 'acqua' : 'oro',
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
  const base = Math.min(w, h);
  /* la camera respira: un dondolio impercettibile che toglie la
     fissita' fotografica — tutto lo strato profondo lo eredita */
  const cx = w / 2 + Math.sin(t * 0.07) * base * 0.012;
  const cy = h * 0.54 + Math.cos(t * 0.05) * base * 0.010;

  g.globalCompositeOperation = 'source-over';
  g.fillStyle = `rgba(12,22,24,${SCIA})`;   // COLORI.fondo
  g.fillRect(0, 0, w, h);
  g.globalCompositeOperation = 'lighter';

  const { bassi, medi, medioAlti, alti } = L.bande;
  const respiro = 0.8 + bassi * 0.5;
  const vento = 0.25 + L.energia * 1.1 + medi * 0.5;

  // ── 1. le nebulose: il cielo che ruota lento ──
  for (const n of st.nebulose) {
    const giro = n.a0 + t * n.giro;
    for (let i = 0; i < n.grumi; i++) {
      const a = giro + (i / n.grumi) * TAU;
      const rr = base * n.r * (0.8 + 0.2 * Math.sin(a * 2 + t * 0.1));
      const dim = base * 0.34 * respiro;
      g.globalAlpha = (n.col === 'oro' ? 0.028 : 0.02) + bassi * 0.02;
      g.drawImage(S[n.col], cx + Math.cos(a) * rr - dim / 2,
        cy + Math.sin(a) * rr * 0.72 - dim / 2, dim, dim);
    }
  }

  // ── 2. i nastri d'aurora: fasce sinuose che ondeggiano coi medi ──
  for (const nb of st.nastri) {
    const passi = 26;
    for (let i = 0; i <= passi; i++) {
      const u = i / passi;
      const x = u * w;
      const fase = u * nb.onda * TAU + t * (0.35 + medi * 0.8) * nb.velo * 6;
      const y = h * nb.y0
        + Math.sin(fase) * base * nb.amp * (0.7 + medi * 0.9)
        + Math.sin(u * 3 + t * 0.2) * base * 0.03;
      const ang = Math.atan2(
        Math.cos(fase) * nb.amp * nb.onda, 1 / (w / base));
      timbro(g, S, nb.col, x, y,
        base * 0.16, base * (0.035 + medioAlti * 0.02), ang,
        (nb.col === 'oro' ? 0.045 : 0.03) + medi * 0.05);
    }
  }

  // ── 3. la polvere nel flusso ──
  for (const p of st.polvere) {
    const ang = flusso(p.x, p.y, t) * Math.PI;
    const vel = vento * p.z * (base / 900);
    p.x += Math.cos(ang) * vel * 1.6;
    p.y += Math.sin(ang) * vel * 1.6 - vel * 0.9;
    if (p.y < -20) { p.y = h + 20; p.x = Math.random() * w; }
    if (p.x < -20) p.x = w + 20;
    if (p.x > w + 20) p.x = -20;
    if (p.y > h + 20) p.y = -20;
    const twinkle = 0.7 + 0.3 * Math.sin(t * 2.1 + p.fase);
    const dim = base * 0.011 * p.z * (1 + bassi * 0.6);
    g.globalAlpha = (0.08 + L.energia * 0.22) * twinkle * p.z
      * (p.col === 'oro' ? 1 : p.col === 'osso' ? 0.9 : 0.4);
    g.drawImage(S[p.col], p.x - dim / 2, p.y - dim / 2, dim, dim);
  }

  // ── 4. lo sciame in orbita: il moto che non si ferma mai ──
  for (const o of st.sciame) {
    o.a += o.vel * (0.35 + L.energia * 1.3 + medi * 0.6) * 0.03;
    const rr = base * o.r * (0.85 + bassi * 0.35 + L.picco * 0.25);
    // ellisse inclinata: x lungo l'asse maggiore, y schiacciata
    const ex = Math.cos(o.a) * rr;
    const ey = Math.sin(o.a) * rr * o.ecc;
    const x = cx + ex * Math.cos(o.incl) - ey * Math.sin(o.incl);
    const y = cy + (ex * Math.sin(o.incl) + ey * Math.cos(o.incl)) * 0.8;
    const scint = 0.75 + 0.25 * Math.sin(t * 3 + o.fase);
    const dim = base * 0.010 * o.z * (1 + alti * 0.8);
    g.globalAlpha = (0.14 + L.energia * 0.4) * o.z * scint
      * (o.col === 'oro' ? 1 : o.col === 'osso' ? 0.95 : 0.5);
    g.drawImage(S[o.col], x - dim / 2, y - dim / 2, dim, dim);
  }

  // ── 5. la geometria sacra: nodi e corde di luce che pulsano ──
  const NODI = 9;
  const rGeo = base * 0.30 * respiro;
  const giroGeo = t * 0.06 + medi * 0.5;
  const pulso = 0.05 + medi * 0.16 + L.picco * 0.10;
  const punti = [];
  for (let i = 0; i < NODI; i++) {
    const a = giroGeo + (i / NODI) * TAU;
    punti.push([cx + Math.cos(a) * rGeo, cy + Math.sin(a) * rGeo * 0.82]);
  }
  // le corde: segmenti di luce fra nodi a distanza 2 e 4 — abbastanza
  // fitte da leggere il fiore, abbastanza rade da non fare la ragnatela
  for (const salto of [2, 4]) {
    for (let i = 0; i < NODI; i++) {
      const [x1, y1] = punti[i], [x2, y2] = punti[(i + salto) % NODI];
      const mx = (x1 + x2) / 2, my = (y1 + y2) / 2;
      const lung = Math.hypot(x2 - x1, y2 - y1);
      timbro(g, S, 'oro', mx, my, lung, base * 0.012,
        Math.atan2(y2 - y1, x2 - x1), pulso * (salto === 2 ? 1 : 0.6));
    }
  }
  for (const [x, y] of punti) {
    const dim = base * 0.030 * (1 + medioAlti * 0.8);
    g.globalAlpha = 0.16 + medioAlti * 0.3;
    g.drawImage(S.osso, x - dim / 2, y - dim / 2, dim, dim);
  }

  // ── 6. i raggi del colpo: lame di luce che irradiano ──
  if (L.picco > 0.03) {
    const nR = 7;
    for (let i = 0; i < nR; i++) {
      const a = (i / nR) * TAU + t * 0.11;
      const lung = base * (0.35 + (1 - L.picco) * 0.4);
      timbro(g, S, 'oro',
        cx + Math.cos(a) * lung * 0.5, cy + Math.sin(a) * lung * 0.5 * 0.85,
        lung, base * 0.028, a, L.picco * 0.22);
    }
    const dim = base * (0.35 + (1 - L.picco) * 1.1);
    g.globalAlpha = L.picco * 0.45;
    g.drawImage(S.anello, cx - dim / 2, cy - dim / 2, dim, dim);
  }

  // ── 7. il cuore: strati e petali che ruotano ──
  for (let i = 0; i < 6; i++) {
    const a = t * 0.14 + (i / 6) * TAU;
    timbro(g, S, 'oro',
      cx + Math.cos(a) * base * 0.045, cy + Math.sin(a) * base * 0.04,
      base * 0.20 * respiro, base * 0.07 * respiro, a,
      0.10 + bassi * 0.14);
  }
  const cuori = [
    ['osso', 0.09, 0.5 + L.energia * 0.5],
    ['oro', 0.20, 0.28 + bassi * 0.30],
    ['oro', 0.42, 0.10 + bassi * 0.12],
  ];
  for (const [col, dim, alfa] of cuori) {
    const d = base * dim * respiro;
    g.globalAlpha = alfa;
    g.drawImage(S[col], cx - d / 2, cy - d / 2, d, d);
  }

  g.globalAlpha = 1;
  g.globalCompositeOperation = 'source-over';
}
