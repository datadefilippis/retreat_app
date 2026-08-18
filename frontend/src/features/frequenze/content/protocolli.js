/**
 * Frequenze by Aurya — protocolli pronti (FQ0, 18/8/2026).
 *
 * Le ricette del prototipo, portate da funzioni imperative a DATI:
 * ogni protocollo costruisce { layers, phases } per una durata data.
 * I gradi (B/C) e le note di evidenza sono contenuto del founder,
 * verbatim: fanno parte del patto di onesta' scientifica del brand.
 */

let _uid = 0;
// Portante di default: 400 Hz per il binaurale (percezione del battito più
// nitida con portanti 200-500 Hz), 180 Hz per gli altri metodi.
const layer = (cfg) => ({
  id: ++_uid,
  kind: 'neuro',
  name: cfg.name || 'Livello',
  method: cfg.method || 'bin',
  timbre: cfg.timbre || 'warm',
  carrier: cfg.carrier ?? ((cfg.method || 'bin') === 'bin' ? 400 : 180),
  f0: cfg.f0 ?? 10,
  f1: cfg.f1 ?? cfg.f0 ?? 10,
  curve: cfg.curve || 'lin',
  start: cfg.start ?? 0,
  end: cfg.end ?? cfg.duration,
  gain: cfg.gain ?? 0.25,
  breath: true,
  mute: false,
});

export const PROTOCOLLI = Object.freeze({
  Dormire: {
    intent: 'dormire', grade: 'B',
    ev: "Sonno: efficacia da piccola a moderata nelle review; NON è un trattamento dell'insonnia clinica (per quella la CBT-I è superiore). Qui: accompagnamento al rilassamento pre-sonno.",
    build: (d) => ({
      layers: [
        layer({ name: 'Alpha ingresso', method: 'iso', f0: 10, f1: 8, curve: 'exp', end: d * 0.25, duration: d }),
        layer({ name: 'Theta discesa', method: 'iso', f0: 8, f1: 5, curve: 'exp', start: d * 0.2, end: d * 0.55, duration: d }),
        layer({ name: 'Delta', method: 'noise', f0: 5, f1: 2.5, curve: 'exp', start: d * 0.5, gain: 0.3, duration: d }),
      ],
      phases: [{ t: 0, name: 'quiete' }, { t: d * 0.25, name: 'discesa' }, { t: d * 0.55, name: 'sonno' }],
    }),
  },
  Meditare: {
    intent: 'meditare', grade: 'B',
    ev: "Arco alpha→theta descritto in protocolli di induzione. Il theta (4–8 Hz) è la banda più studiata. Effetti reali ma modesti. Termina con il rientro.",
    build: (d) => ({
      layers: [
        layer({ name: 'Alpha ingresso', method: 'bin', f0: 12, f1: 8, curve: 'exp', end: d * 0.2, duration: d }),
        layer({ name: 'Theta', method: 'bin', f0: 8, f1: 6, curve: 'exp', start: d * 0.18, end: d * 0.45, duration: d }),
        layer({ name: 'Theta plateau 6 Hz', method: 'bin', f0: 6, f1: 6, start: d * 0.45, end: d * 0.8, duration: d }),
        layer({ name: 'Rientro', method: 'bin', f0: 6, f1: 12, curve: 'lin', start: d * 0.8, duration: d }),
      ],
      phases: [{ t: 0, name: 'ingresso' }, { t: d * 0.2, name: 'discesa' }, { t: d * 0.45, name: 'profondità' }, { t: d * 0.8, name: 'rientro' }],
    }),
  },
  Rilassare: {
    intent: 'rilassare', grade: 'B',
    ev: "L'uso meglio supportato: riduzione dell'ansia e rilassamento già dopo ~10 minuti di ascolto. Stato stabile in alpha: nessuna discesa, nessun rientro necessario.",
    build: (d) => ({
      layers: [
        layer({ name: 'Ingresso alpha', method: 'bin', f0: 11, f1: 10, curve: 'exp', end: d * 0.15, duration: d }),
        layer({ name: 'Alpha 10 Hz', method: 'bin', f0: 10, f1: 10, start: d * 0.12, duration: d }),
      ],
      phases: [{ t: 0, name: 'ingresso' }, { t: d * 0.15, name: 'alpha stabile' }],
    }),
  },
  Concentrare: {
    intent: 'concentrare', grade: 'C',
    ev: "Il più debole: le prove sul potenziamento cognitivo sono scarse e alcuni studi lo dicono persino controproducente su compiti complessi. Stato attivo voluto: nessun rientro.",
    build: (d) => ({
      layers: [
        layer({ name: 'Ingresso', method: 'iso', f0: 10, f1: 12, curve: 'exp', end: d * 0.12, duration: d }),
        layer({ name: 'Salita in SMR', method: 'iso', f0: 12, f1: 14, curve: 'lin', start: d * 0.1, end: d * 0.32, duration: d }),
        layer({ name: 'Focus 14 Hz', method: 'iso', f0: 14, f1: 14, start: d * 0.3, end: d * 0.9, duration: d }),
        layer({ name: 'Assestamento', method: 'iso', f0: 14, f1: 13, start: d * 0.9, duration: d }),
      ],
      phases: [{ t: 0, name: 'ingresso' }, { t: d * 0.32, name: 'focus' }, { t: d * 0.9, name: 'assestamento' }],
    }),
  },
  Elaborare: {
    intent: 'elaborare', grade: 'C',
    ev: "Alternanza dx/sx su fondo theta. La stimolazione bilaterale audio è un componente usato nell'EMDR, ma l'EMDR è un protocollo clinico condotto da terapeuti: questo strumento non lo sostituisce. Termina con il rientro.",
    build: (d) => ({
      layers: [
        layer({ name: 'Theta di fondo', method: 'mono', f0: 6, f1: 6, gain: 0.2, duration: d }),
        layer({ name: 'Bilaterale 1 Hz', method: 'bil', f0: 1, f1: 1, carrier: 220, gain: 0.22, start: d * 0.1, end: d * 0.82, duration: d }),
        layer({ name: 'Rientro alpha', method: 'mono', f0: 6, f1: 11, curve: 'lin', start: d * 0.82, duration: d }),
      ],
      phases: [{ t: 0, name: 'radicamento' }, { t: d * 0.1, name: 'alternanza' }, { t: d * 0.82, name: 'rientro' }],
    }),
  },
  Energizzare: {
    intent: 'energizzare', grade: 'C',
    ev: "Salita verso beta con un breve picco a 40 Hz — il 40 Hz è la singola frequenza con le basi più solide (cognizione, memoria). Stato attivo voluto: finisce in alto, senza rientro verso il basso.",
    build: (d) => ({
      layers: [
        layer({ name: 'Ingresso alpha', method: 'iso', f0: 10, f1: 12, curve: 'exp', end: d * 0.2, duration: d }),
        layer({ name: 'Salita in beta', method: 'iso', f0: 12, f1: 16, curve: 'lin', start: d * 0.18, end: d * 0.55, duration: d }),
        layer({ name: 'Beta', method: 'iso', f0: 16, f1: 18, curve: 'lin', start: d * 0.52, end: d * 0.82, duration: d }),
        layer({ name: 'Picco 40 Hz', method: 'iso', f0: 40, f1: 40, carrier: 200, gain: 0.15, start: d * 0.6, end: d * 0.75, duration: d }),
        layer({ name: 'Assestamento', method: 'iso', f0: 16, f1: 14, start: d * 0.82, duration: d }),
      ],
      phases: [{ t: 0, name: 'risveglio' }, { t: d * 0.2, name: 'salita' }, { t: d * 0.55, name: 'energia' }, { t: d * 0.82, name: 'assestamento' }],
    }),
  },
});
