/**
 * Palette grafici — Salvia & Terracotta (CF1, INSIGHTS_ACTION_PLAN).
 *
 * UNICA fonte colore per ogni grafico dell'app. I componenti feature
 * non scelgono mai colori: passano dati, il kit decide.
 *  - primary    → la metrica principale (incassato, iscritti, vendite)
 *  - accent     → attenzione/urgenza (in ritardo, a rischio)
 *  - expected   → serie "atteso/previsto" (tratteggiata, mai piena)
 *  - series     → composizioni (DonutSplit): 5 tinte famiglia + grigio "altro"
 */

export const CHART_COLORS = {
  primary: '#376254',   // salvia — il numero che conta
  accent: '#C97B5D',    // terracotta — ciò che chiede attenzione
  expected: '#8A9088',  // neutro — l'atteso, mai in competizione col reale
  grid: '#E7E3D8',      // linee/assi, quasi invisibili
  amber: '#D9A441',     // SOLO rating stelle
};

export const SERIES_COLORS = [
  '#376254', // salvia
  '#C97B5D', // terracotta
  '#5E8073', // salvia chiara
  '#B9A96B', // oliva
  '#A9695B', // argilla
];

export const OTHER_COLOR = '#C9CDC5'; // fetta "altro" — sempre l'ultima, sempre grigia
