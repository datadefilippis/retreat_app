/**
 * CategorySigil — MG2: il segno della categoria, in SVG.
 *
 * PERCHE'. Ogni categoria ha gia' una geometria, disegnata dal
 * generatore di copertine (backend/services/article_cover.py): il loto
 * per lo yoga, la spirale per il breathwork, i tre cerchi per
 * l'ayurveda. Compare su ogni copertina di ogni articolo, ma non
 * compariva da nessuna altra parte — quindi il colore della scheda di
 * categoria era l'unico aggancio, e un colore da solo si confonde
 * (salvia e salvia profondo sono due categorie diverse).
 *
 * Con il segno, la scheda "Yoga" e la copertina di un articolo di yoga
 * mostrano LA STESSA FIGURA. E' l'unica cosa che rende un sistema di
 * colori riconoscibile invece che decorativo.
 *
 * COME. Le figure sono ricalcolate qui con la stessa matematica del
 * Python, non ridisegnate a occhio: stessi raggi, stessi angoli,
 * stesse proporzioni rispetto al raggio di riferimento. Se una
 * geometria cambia di la', va rifatta anche qui — e' un duplicato
 * consapevole, come le palette in MagazineCategoryNav, perche'
 * l'alternativa sarebbe servire un SVG dal backend per un disegno che
 * non cambia mai.
 *
 * Il tratto usa `currentColor`: chi lo usa decide colore e opacita'
 * dal contenitore, e lo stesso componente fa da filigrana chiara su
 * fondo scuro e da segno scuro su fondo chiaro.
 *
 * E' decorativo: `aria-hidden`, sempre. Il nome della categoria e'
 * gia' scritto accanto in testo vero.
 */
import React from 'react';

/* Il sistema di riferimento: una tela 100×100, centro 50,50, raggio
   44 — lo stesso rapporto fra segno e medaglione delle copertine. */
const C = 50;
const R = 44;
const rad = (g) => (g * Math.PI) / 180;

/* Nel Python alcune figure usano `cy - sin` (asse verticale rivoltato)
   e altre `cy + sin`. Qui la distinzione resta identica, perche' e'
   quella che decide se il bivio si apre in alto o in basso. */
const cerchio = (cx, cy, r, k) => (
  <circle key={k} cx={cx} cy={cy} r={r} />
);

function loto() {                                    // yoga
  return Array.from({ length: 8 }, (_, k) => {
    const a = rad(k * 45);
    return cerchio(C + Math.cos(a) * R * 0.45, C + Math.sin(a) * R * 0.45,
                   R * 0.55, k);
  });
}

function fioreDellaVita() {                          // meditazione
  const r = R * 0.38;
  const out = [cerchio(C, C, r, 'c')];
  [[6, r, 0], [6, r * Math.sqrt(3), 30], [6, 2 * r, 0]].forEach(
    ([n, dist, off], i) => {
      for (let k = 0; k < n; k += 1) {
        const a = rad(k * 60 + off);
        out.push(cerchio(C + Math.cos(a) * dist, C + Math.sin(a) * dist,
                         r, `${i}-${k}`));
      }
    });
  return out;
}

function semeDellaVita() {                           // detox
  const r = R * 0.5;
  const out = [cerchio(C, C, r, 'c')];
  for (let k = 0; k < 6; k += 1) {
    const a = rad(k * 60);
    out.push(cerchio(C + Math.cos(a) * r, C + Math.sin(a) * r, r, k));
  }
  return out;
}

function onde() {                                    // suono
  return Array.from({ length: 6 },
                    (_, k) => cerchio(C, C, (R * (k + 1)) / 6, k));
}

function vesica() {                                  // massaggio
  const r = R * 0.62;
  return [
    cerchio(C - r / 2, C, r, 'a'),
    cerchio(C + r / 2, C, r, 'b'),
    cerchio(C, C, r * 1.55, 'c'),
  ];
}

function spirale() {                                 // breathwork
  const a = R * 0.02;
  const b = 0.16;
  const punti = [];
  for (let i = 0; i < 1700; i += 5) {
    const t = rad(i);
    const r = a * Math.exp(b * t);
    if (r > R) break;
    punti.push(`${(C + Math.cos(t) * r).toFixed(2)},${(C + Math.sin(t) * r).toFixed(2)}`);
  }
  return <polyline points={punti.join(' ')} />;
}

function esagramma() {                               // cammini
  const out = [cerchio(C, C, R * 0.9, 'c')];
  [0, 180].forEach((rot) => {
    const p = Array.from({ length: 3 }, (_, k) => {
      const a = rad(rot + 90 + k * 120);
      return `${(C + Math.cos(a) * R * 0.78).toFixed(2)},${(C - Math.sin(a) * R * 0.78).toFixed(2)}`;
    });
    out.push(<polygon key={rot} points={p.join(' ')} />);
  });
  return out;
}

function tripliceLuna() {                            // femminile
  const r = R * 0.36;
  const out = [cerchio(C, C, r, 'piena')];
  [-1, 1].forEach((lato) => {
    const x = C + lato * r * 1.7;
    out.push(cerchio(x, C, r * 0.78, `a${lato}`));
    out.push(cerchio(x + lato * r * 0.4, C, r * 0.7, `b${lato}`));
  });
  return out;
}

function metatron() {                                // aziendale
  const out = [cerchio(C, C, R * 0.92, 'c')];
  const v = Array.from({ length: 6 }, (_, k) => {
    const a = rad(k * 60 + 30);
    return [C + Math.cos(a) * R * 0.72, C + Math.sin(a) * R * 0.72];
  });
  for (let i = 0; i < 6; i += 1) {
    for (let j = i + 1; j < 6; j += 1) {
      out.push(<line key={`l${i}${j}`} x1={v[i][0]} y1={v[i][1]}
                     x2={v[j][0]} y2={v[j][1]} />);
    }
  }
  v.forEach(([x, y], k) => out.push(cerchio(x, y, R * 0.1, `v${k}`)));
  return out;
}

function cerchioDiPersone() {                        // ritiri
  const out = [cerchio(C, C, R * 0.92, 'c')];
  for (let k = 0; k < 12; k += 1) {
    const a = rad(k * 30);
    out.push(cerchio(C + Math.cos(a) * R * 0.92, C + Math.sin(a) * R * 0.92,
                     R * 0.1, k));
  }
  return out;
}

function raggiera() {                                // energia
  const out = [cerchio(C, C, R * 0.34, 'i'), cerchio(C, C, R * 0.95, 'o')];
  for (let k = 0; k < 12; k += 1) {
    const a = rad(k * 30 + 15);
    out.push(<line key={k}
                   x1={C + Math.cos(a) * R * 0.46} y1={C + Math.sin(a) * R * 0.46}
                   x2={C + Math.cos(a) * R * 0.84} y2={C + Math.sin(a) * R * 0.84} />);
  }
  return out;
}

function quadratoNelCerchio() {                      // operatori
  const p = Array.from({ length: 4 }, (_, k) => {
    const a = rad(k * 90 + 45);
    return `${(C + Math.cos(a) * R * 0.92).toFixed(2)},${(C + Math.sin(a) * R * 0.92).toFixed(2)}`;
  });
  return [
    cerchio(C, C, R * 0.92, 'o'),
    cerchio(C, C, R * 0.3, 'i'),
    <polygon key="q" points={p.join(' ')} />,
  ];
}

function bivio() {                                   // scegliere
  /* Le strade si aprono VERSO L'ALTO: `C - sin`, come nel Python.
     E' il significato della figura, non un dettaglio di disegno. */
  const oy = C + R * 0.6;
  const out = [cerchio(C, C, R * 0.92, 'c')];
  [128, 104, 76, 52].forEach((g) => {
    const a = rad(g);
    out.push(<line key={g} x1={C} y1={oy}
                   x2={C + Math.cos(a) * R * 0.88}
                   y2={C - Math.sin(a) * R * 0.88} />);
  });
  out.push(cerchio(C, oy, R * 0.09, 'o'));
  return out;
}

function treDosha() {                                // ayurveda
  const r = R * 0.42;
  const out = [cerchio(C, C, R * 0.95, 'c')];
  [90, 210, 330].forEach((g) => {
    const a = rad(g);
    out.push(cerchio(C + Math.cos(a) * r * 0.86, C - Math.sin(a) * r * 0.86,
                     r, g));
  });
  return out;
}

function aura() {                                    // ripiego
  return [1, 0.75, 0.5, 0.25].map((k) => cerchio(C, C, R * k, k));
}

const SEGNI = {
  yoga: loto,
  meditazione: fioreDellaVita,
  detox: semeDellaVita,
  suono: onde,
  massaggio: vesica,
  breathwork: spirale,
  cammini: esagramma,
  femminile: tripliceLuna,
  aziendale: metatron,
  ritiri: cerchioDiPersone,
  energia: raggiera,
  operatori: quadratoNelCerchio,
  scegliere: bivio,
  ayurveda: treDosha,
};

/**
 * @param {string} categoria  slug; sconosciuto → l'aura del marchio
 * @param {number} spessore   larghezza del tratto sulla tela 100×100
 */
export default function CategorySigil({
  categoria, className = '', spessore = 2.4, ...rest
}) {
  const disegna = SEGNI[categoria] || aura;
  return (
    <svg viewBox="0 0 100 100" className={className} aria-hidden focusable="false"
         fill="none" stroke="currentColor" strokeWidth={spessore}
         strokeLinecap="round" strokeLinejoin="round" {...rest}>
      {disegna()}
    </svg>
  );
}
