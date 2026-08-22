/**
 * Aurya Mode — LE TABELLE dello standard (VC1, 22/8/2026).
 *
 * Decisione founder: /sound/visual E' lo standard — «se aggiungeremo
 * nuovi preset o nuove variabili, compariranno anche in Crea». Perche'
 * cio' accada da solo, le tabelle vivono qui, in un modulo SENZA Three
 * (Crea le importa senza pagare 500KB di motore), e le leggono in due:
 * - prototipo.js (la stanza a schermo pieno e il motore incorporato);
 * - i controlli della scena in Crea (il velo React).
 * Contenuto ESTRATTO verbatim dal prototipo del founder: qui non si
 * inventa, si sposta. Ogni riga e' sua.
 */
export const SLIDERS = [
  ['intensity','Intensity',0,200,72,'%'],
  ['scale','Scale',40,220,126,'%'],
  ['speed','Speed',10,180,44,'%'],
  ['breath','Breath cycle',4,16,9,'s'],
  ['drift','Drift',0,200,80,'%'],
  ['particles','Particles',2000,24000,17000,''],
  ['glow','Glow',10,200,104,'%'],
  ['trails','Trails',0,96,88,'%'],
  ['depth','Depth',20,260,120,'%'],
  ['brightness','Brightness',20,200,100,'%'],
  ['contrast','Contrast',30,180,96,'%'],
];
/* deep, luminous triads: shadow → body → light */
export const PALETTES = [
  { name:'Aurea',   sw:'#8b5cf6', c:['#160f3a','#8b5cf6','#ffd9a0'] },
  { name:'Quartz',  sw:'#e879b9', c:['#2b0a2e','#e879b9','#ffe6ef'] },
  { name:'Amber',   sw:'#f59e0b', c:['#2e1206','#f59e0b','#fff2c2'] },
  { name:'Jade',    sw:'#2dd4a7', c:['#03271f','#2dd4a7','#e2fff5'] },
  { name:'Abyss',   sw:'#38bdf8', c:['#061c46','#38bdf8','#e6f8ff'] },
  { name:'Prism',   sw:'conic-gradient(#f59e0b,#ec4899,#8b5cf6,#22d3ee,#f59e0b)', c:['#f59e0b','#a855f7','#8ff0ff'] },
];
export const MODES = [
  ['Breath','M12 4v16M8 8c-2 2-2 6 0 8M16 8c2 2 2 6 0 8'],
  ['Nebula','M6 14a4 4 0 0 1 1-7 5 5 0 0 1 9-1 4 4 0 0 1 2 8z'],
  ['Spiral','M12 12a3 3 0 1 0 3 3c0-3-3-5-6-5s-6 2.7-6 6'],
  ['Flow','M4 8c4-4 8 4 12 0M4 16c4-4 8 4 12 0'],
  ['Mandala','M12 3c2.6 3.4 2.6 6 0 8.4-2.6-2.4-2.6-5 0-8.4M21 12c-3.4 2.6-6 2.6-8.4 0 2.4-2.6 5-2.6 8.4 0M12 21c-2.6-3.4-2.6-6 0-8.4 2.6 2.4 2.6 5 0 8.4M3 12c3.4-2.6 6-2.6 8.4 0-2.4 2.6-5 2.6-8.4 0'],
  ['Helix','M8 3c8 4-8 14 0 18M16 3c-8 4 8 14 0 18'],
  ['Ripple','M12 12h.01M12 12a4 4 0 0 1 0 0M6 12a6 6 0 0 1 12 0M3 12a9 9 0 0 1 18 0'],
];
export const PRESETS = [
  { name:'Aurya',     mode:4, pal:2, over:{intensity:80,scale:94,speed:36,trails:55,glow:96,drift:16,breath:10,depth:100,brightness:100,contrast:100} },
  { name:'Cosmos',    mode:2, pal:0, over:{intensity:72,scale:126,speed:44,trails:88,glow:104,drift:80,breath:9,depth:120,brightness:100} },
  { name:'Anahata',   mode:4, pal:3, over:{intensity:82,scale:118,speed:34,trails:90,glow:112,drift:52,breath:11,depth:90} },
  { name:'Prana',     mode:0, pal:4, over:{intensity:64,scale:132,speed:26,trails:92,glow:120,drift:66,breath:12,depth:130} },
  { name:'Nirvana',   mode:1, pal:1, over:{intensity:90,scale:140,speed:30,trails:86,glow:130,drift:120,breath:10,depth:150} },
  { name:'Kundalini', mode:5, pal:2, over:{intensity:86,scale:120,speed:52,trails:84,glow:106,drift:70,breath:8,depth:140} },
  { name:'Samadhi',   mode:6, pal:5, over:{intensity:76,scale:134,speed:38,trails:91,glow:98,drift:44,breath:13,depth:110} },
];
export const CAMS = ['Orbit','Still','Breathe','Drift'];
