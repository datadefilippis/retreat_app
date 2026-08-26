/**
 * LA PARTITURA — lo score disegnato (M-D/1, 26/8/2026).
 *
 * La risposta VISIVA a «cosa succederà durante questa sessione?»:
 * ogni protocollo si disegna da solo, dai suoi dati veri. Le bande
 * sono i livelli che entrano ed escono nel tempo; lo spessore è
 * l'intensità; la linea sottile dentro una banda è il battito che
 * scivola. Niente è decorativo: se si vede, è nello score.
 *
 * (Si chiama SPARTITO — il foglio — perché la veste si chiama
 * Partitura.jsx, e sul Mac due file che differiscono solo per la
 * maiuscola collidono.)
 *
 * PURO E SENZA IMPORT, come il compilatore: stesso input → stessa
 * geometria, byte per byte. Gira in Node (i test la misurano) e nel
 * browser (il componente Partitura.jsx la veste in SVG). Qui non c'è
 * React, non c'è DOM, non c'è un colore hex: solo numeri — i colori
 * sono NOMI di famiglia, e la veste li risolve sulle variabili del
 * tema (.fqz), così la partitura è del mondo Sound senza saperlo.
 *
 * LE FAMIGLIE, con le parole delle schede:
 *   continuo  un tono che sta (tone, drone)
 *   ritmo     un battito o un'alternanza (bin, iso, mono, bil, shepard)
 *   soffio    la banda larga (noise)
 *   respiro   la guida respiratoria (breath)
 *   materia   basi audio e voce (kind audio/voice)
 */

export const FAMIGLIE = Object.freeze({
  continuo: ['tone', 'drone'],
  ritmo: ['bin', 'iso', 'mono', 'bil', 'shepard'],
  soffio: ['noise'],
  respiro: ['breath'],
});

export function famiglia(layer) {
  if (layer.kind === 'audio' || layer.kind === 'voice') return 'materia';
  for (const [nome, metodi] of Object.entries(FAMIGLIE)) {
    if (metodi.includes(layer.method)) return nome;
  }
  return 'continuo';
}

/* il battito al tempo u∈[0,1] dentro la barra: le stesse quattro
   curve del contratto, in forma minima (per DISEGNARE, non suonare —
   il suono resta del motore) */
function battito(l, u) {
  const f0 = l.f0 ?? 10, f1 = l.f1 ?? f0;
  switch (l.curve) {
    case 'exp': {
      const a = Math.max(0.01, f0), b = Math.max(0.01, f1);
      return a * Math.pow(b / a, u);
    }
    case 'steps': {
      const passi = 4;
      const k = Math.min(passi - 1, Math.floor(u * passi));
      return f0 + (f1 - f0) * (k / (passi - 1));
    }
    case 'wave': {
      const periodo = Math.max(2, l.period || 40);
      const span = Math.max(1, (l.end ?? 0) - (l.start ?? 0));
      return f0 + (f1 - f0) * (1 - Math.cos((2 * Math.PI * u * span) / periodo)) / 2;
    }
    default:
      return f0 + (f1 - f0) * u;
  }
}

/**
 * score → geometria. Deterministica.
 *
 * @returns {{
 *   w, h, durata,
 *   bande: [{ x0, x1, yc, alto, famiglia, opacita, punta }],
 *   curve: [{ punti: [[x,y]...], famiglia }],
 *   fasi:  [{ x, nome }],
 * }}
 * `punta` è la lunghezza dell'affusolatura (l'entrata e l'uscita
 * morbide del suono, disegnate come si sentono).
 */
export function partitura(score, { w = 600, h = 120, margine = 8 } = {}) {
  const durata = Math.max(1, score?.duration_sec || 1);
  const layers = (score?.layers || []).filter((l) => !l.mute);
  const n = Math.max(1, layers.length);
  const utile = h - margine * 2;
  const corsia = utile / n;
  const X = (t) => (Math.max(0, Math.min(durata, t)) / durata) * w;

  const bande = [];
  const curve = [];
  layers.forEach((l, i) => {
    const x0 = X(l.start ?? 0);
    const x1 = X(l.end ?? durata);
    if (x1 - x0 < 1) return;
    const fam = famiglia(l);
    const gain = Math.max(0, Math.min(1, l.gain ?? 0.25));
    /* lo spessore È il volume: da un filo a quasi tutta la corsia */
    const alto = Math.max(2, corsia * (0.25 + 0.6 * gain));
    const yc = margine + corsia * i + corsia / 2;
    /* l'affusolatura: il suono entra e esce morbido, la banda pure */
    const punta = Math.min((x1 - x0) * 0.22, w * 0.05);
    bande.push({
      x0: r2(x0), x1: r2(x1), yc: r2(yc), alto: r2(alto),
      famiglia: fam,
      opacita: r2(0.35 + 0.5 * gain),
      punta: r2(punta),
    });
    /* il battito che scivola: una linea dentro la banda, solo dove
       c'è davvero un tragitto da raccontare */
    const f0 = l.f0 ?? 10, f1 = l.f1 ?? f0;
    const ritmico = fam === 'ritmo' || fam === 'respiro';
    if (ritmico && (f0 !== f1 || l.curve === 'wave')) {
      const lo = Math.min(f0, f1), hi = Math.max(f0, f1);
      const ampiezza = Math.max(0.05, hi - lo);
      const passi = 24;
      const punti = [];
      for (let k = 0; k <= passi; k++) {
        const u = k / passi;
        const f = battito(l, u);
        /* battito alto = linea alta dentro la banda */
        const q = (f - lo) / ampiezza;
        const y = yc + (alto / 2 - 1) * (1 - 2 * q) * 0.8;
        punti.push([r2(x0 + (x1 - x0) * u), r2(y)]);
      }
      curve.push({ punti, famiglia: fam });
    }
  });

  const fasi = (score?.phases || [])
    .filter((p) => p && p.name && Number.isFinite(p.t))
    .map((p) => ({ x: r2(X(p.t)), nome: p.name }));

  return { w, h, durata, bande, curve, fasi };
}

/** le famiglie presenti, nell'ordine della partitura: per la legenda */
export function famiglie(score) {
  const viste = [];
  (score?.layers || []).filter((l) => !l.mute).forEach((l) => {
    const f = famiglia(l);
    if (!viste.includes(f)) viste.push(f);
  });
  return viste;
}

const r2 = (x) => Math.round(x * 100) / 100;
