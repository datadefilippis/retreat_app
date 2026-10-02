/**
 * Discipline olistiche (ciclo DI, founder 14/8/2026) — specchio del
 * backend models/disciplines.py: STESSA lista, STESSO ordine, stessi
 * slug. Una guardia backend impone la parita': se tocchi una voce,
 * toccala in ENTRAMBI i file.
 *
 * ~40 voci in 6 famiglie tematiche: complete ma leggibili a colpo
 * d'occhio (richiesta esplicita: "in maniera ordinata e non casinara").
 * Le label sono italiane e definitive (contenuti nuovi solo IT dal 2/8).
 */

import { useEffect, useState } from 'react';

export const DISCIPLINE_FAMILIES = Object.freeze([
  {
    slug: 'corpo', label: 'Corpo & Movimento',
    items: [
      { slug: 'yoga', label: 'Yoga' },
      { slug: 'pilates', label: 'Pilates' },
      { slug: 'tai-chi', label: 'Tai Chi' },
      { slug: 'qi-gong', label: 'Qi Gong' },
      { slug: 'danzaterapia', label: 'Danzaterapia' },
      { slug: 'bioenergetica', label: 'Bioenergetica' },
      { slug: 'feldenkrais', label: 'Feldenkrais' },
      { slug: 'biodanza', label: 'Biodanza' },
      { slug: 'danze-sacre', label: 'Danze sacre & Danza della Dea' },
      // 29/9/2026 (founder): l'allineamento della colonna come lavoro sul corpo
      { slug: 'allineamento', label: 'Allineamento (colonna & postura)' },
    ],
  },
  {
    slug: 'mente', label: 'Meditazione & Mente',
    items: [
      { slug: 'meditazione', label: 'Meditazione' },
      { slug: 'mindfulness', label: 'Mindfulness' },
      { slug: 'breathwork', label: 'Breathwork' },
      { slug: 'training-autogeno', label: 'Training autogeno' },
      { slug: 'ipnosi', label: 'Ipnosi & Rilassamento guidato' },
      // 2/10/2026 (founder): la regressione alle vite passate, generica (il metodo di marchio e' un sinonimo)
      { slug: 'regressione-vite-passate', label: 'Regressione & Vite passate' },
      // 29/9/2026 (founder): visualizzazione guidata del futuro desiderato
      { slug: 'mind-movie', label: 'Mind movie' },
    ],
  },
  {
    slug: 'massaggio', label: 'Massaggio & Bodywork',
    items: [
      // 29/9/2026 (founder): il massaggio senza aggettivi, accanto all'olistico
      { slug: 'massaggio', label: 'Massaggio' },
      { slug: 'massaggio-olistico', label: 'Massaggio olistico' },
      { slug: 'shiatsu', label: 'Shiatsu' },
      { slug: 'massaggio-ayurvedico', label: 'Massaggio ayurvedico' },
      { slug: 'massaggio-thai', label: 'Massaggio thai' },
      { slug: 'riflessologia', label: 'Riflessologia' },
      { slug: 'craniosacrale', label: 'Craniosacrale' },
      { slug: 'linfodrenaggio', label: 'Linfodrenaggio' },
      { slug: 'hot-stone', label: 'Hot stone' },
    ],
  },
  {
    slug: 'energia', label: 'Energia & Vibrazione',
    items: [
      { slug: 'reiki', label: 'Reiki' },
      { slug: 'pranoterapia', label: 'Pranoterapia' },
      { slug: 'cristalloterapia', label: 'Cristalloterapia' },
      // 29/9/2026 (founder): pulizia e purificazione energetica (aura, ambienti)
      { slug: 'pulizia-energetica', label: 'Pulizia energetica' },
      // 24/9/2026 (founder): due voci sui chakra, generiche, non di marchio
      { slug: 'allineamento-chakra', label: 'Allineamento chakra' },
      { slug: 'lavoro-energetico-chakra', label: 'Lavoro energetico coi chakra' },
      { slug: 'sound-healing', label: 'Sound healing & Campane tibetane' },
      { slug: 'theta-healing', label: 'Theta healing' },
      { slug: 'access-bars', label: 'Access Bars' },
      { slug: 'kinesiologia', label: 'Kinesiologia' },
    ],
  },
  {
    slug: 'natura', label: 'Natura & Rimedi',
    items: [
      { slug: 'naturopatia', label: 'Naturopatia' },
      { slug: 'aromaterapia', label: 'Aromaterapia' },
      { slug: 'floriterapia', label: 'Floriterapia & Fiori di Bach' },
      { slug: 'erboristeria', label: 'Erboristeria' },
      { slug: 'alimentazione-olistica', label: 'Alimentazione olistica' },
      { slug: 'bagni-di-bosco', label: 'Bagni di bosco' },
      { slug: 'consulenza-ayurvedica', label: 'Consulenza ayurvedica' },
    ],
  },
  {
    // 24/9/2026 (founder): professioni psicologiche, famiglia propria
    slug: 'psiche', label: 'Psicologia & Psicoterapia',
    items: [
      { slug: 'psicologia', label: 'Psicologia' },
      { slug: 'psicoterapia', label: 'Psicoterapia' },
      { slug: 'sostegno-psicologico', label: 'Sostegno psicologico' },
      { slug: 'psicologia-perinatale', label: 'Psicologia perinatale' },
    ],
  },
  {
    slug: 'anima', label: 'Anima & Percorsi interiori',
    items: [
      { slug: 'costellazioni-familiari', label: 'Costellazioni familiari' },
      { slug: 'counseling-olistico', label: 'Counseling olistico' },
      // 1/10/2026 (founder): l'etichetta diventa «Gestalt counseling», lo slug resta
      { slug: 'counseling-gestalt', label: 'Gestalt counseling' },
      { slug: 'coaching-olistico', label: 'Coaching olistico' },
      { slug: 'cerchi-di-donne', label: 'Cerchi di donne' },
      { slug: 'sacro-femminile', label: 'Sacro femminile & Ciclicità' },
      { slug: 'sciamanesimo', label: 'Pratiche sciamaniche' },
      // 25/9/2026 (founder): la ricerca spirituale come pratica accompagnata
      { slug: 'percorsi-spirituali', label: 'Percorsi spirituali' },
      // 1/10/2026 (founder): due voci di crescita, personale e spirituale
      { slug: 'crescita-personale', label: 'Crescita personale' },
      { slug: 'crescita-spirituale', label: 'Crescita spirituale' },
      { slug: 'astrologia', label: 'Astrologia' },
      { slug: 'numerologia', label: 'Numerologia' },
      { slug: 'tarocchi-evolutivi', label: 'Tarocchi evolutivi' },
    ],
  },
]);

/** slug → label, piatto: risoluzione badge e filtri. */
export const DISCIPLINE_LABELS = Object.freeze(Object.fromEntries(
  DISCIPLINE_FAMILIES.flatMap(f => f.items.map(d => [d.slug, d.label])),
));

/** Tetto della multi-selezione (stesso valore del backend). */
export const DISCIPLINES_MAX = 10;

export const disciplineLabel = (slug) => etichette()[slug] || slug;

/* ── 24/9/2026 — orientarsi fra 52 voci (components/SelettoreDiscipline) ── */

/** Le otto che si scelgono più spesso: la prima riga, per partire senza sfogliare. */
export const PIU_SCELTE = Object.freeze([
  'yoga', 'meditazione', 'massaggio-olistico', 'reiki', 'breathwork',
  'naturopatia', 'counseling-olistico', 'psicoterapia',
]);

/** Parole con cui la gente cerca (professione, plurali, nomi comuni) →
    la voce della tassonomia. Si cerca su etichetta + famiglia + queste. */
export const CERCA_ANCHE = Object.freeze({
  psicologia: ['psicologo', 'psicologa'],
  psicoterapia: ['psicoterapeuta', 'terapia'],
  'sostegno-psicologico': ['colloqui', 'sostegno'],
  'counseling-olistico': ['counselor', 'counselling'],
  'counseling-gestalt': ['gestalt', 'counselor gestalt', 'gestaltico', 'counseling gestalt'],
  'crescita-personale': ['crescita', 'sviluppo personale', 'evoluzione personale', 'autostima', 'consapevolezza'],
  'crescita-spirituale': ['spirituale', 'evoluzione spirituale', 'risveglio', 'coscienza', 'anima'],
  'coaching-olistico': ['coach', 'life coach'],
  massaggio: ['massaggi', 'massaggiatrice', 'massaggiatore', 'massoterapia', 'massaggio rilassante', 'decontratturante', 'massaggio sportivo'],
  'massaggio-olistico': ['olistico', 'massaggiatrice olistica', 'massaggiatore olistico'],
  allineamento: ['colonna vertebrale', 'colonna', 'postura', 'posturale', 'allineamento posturale', 'schiena', 'riallineamento'],
  'pulizia-energetica': ['purificazione energetica', 'pulizia dell\'aura', 'aura', 'riequilibrio energetico', 'pulizia degli ambienti', 'purificazione'],
  'mind-movie': ['mind movies', 'visualizzazione', 'visualizzazione creativa', 'film mentale', 'manifestazione'],
  'massaggio-ayurvedico': ['ayurveda', 'abhyanga'],
  'massaggio-thai': ['thailandese'],
  riflessologia: ['riflessologo', 'riflessologa', 'plantare'],
  linfodrenaggio: ['linfatico', 'drenaggio'],
  craniosacrale: ['cranio'],
  'sound-healing': ['campane tibetane', 'bagno di gong', 'gong', 'suono', 'ciotole'],
  breathwork: ['respiro', 'respirazione'],
  meditazione: ['meditare'],
  mindfulness: ['consapevolezza'],
  'costellazioni-familiari': ['costellatore', 'costellatrice', 'costellazioni'],
  naturopatia: ['naturopata'],
  erboristeria: ['erborista', 'erbe'],
  aromaterapia: ['oli essenziali'],
  floriterapia: ['fiori di bach', 'bach'],
  'alimentazione-olistica': ['nutrizione', 'alimentazione', 'cibo'],
  'bagni-di-bosco': ['shinrin yoku', 'natura', 'foresta'],
  reiki: ['energia', 'energetico'],
  'allineamento-chakra': ['chakra'],
  'lavoro-energetico-chakra': ['chakra', 'energetico'],
  pranoterapia: ['pranoterapeuta', 'pranic healing', 'pranic healer', 'guaritore pranico', 'prana'],
  cristalloterapia: ['cristalli', 'pietre'],
  'access-bars': ['bars'],
  'theta-healing': ['theta'],
  kinesiologia: ['kinesiologo', 'kinesiologa'],
  ipnosi: ['ipnoterapia', 'rilassamento'],
  'regressione-vite-passate': ['vite passate', 'regressione', 'ipnosi regressiva', 'brian weiss', 'metodo weiss', 'vite precedenti'],
  'training-autogeno': ['autogeno'],
  yoga: ['hatha', 'vinyasa', 'yin', 'kundalini', 'insegnante di yoga'],
  pilates: ['postura'],
  'tai-chi': ['taiji'],
  'qi-gong': ['qigong', 'chi kung'],
  danzaterapia: ['danza', 'movimento'],
  biodanza: ['danza'],
  'danze-sacre': ['danza', 'dea'],
  bioenergetica: ['lowen'],
  feldenkrais: ['movimento'],
  'cerchi-di-donne': ['cerchio', 'donne'],
  'sacro-femminile': ['femminile', 'ciclicità', 'ciclo', 'luna'],
  sciamanesimo: ['sciamano', 'sciamana', 'sciamanico'],
  'percorsi-spirituali': ['spiritualità', 'spirituale', 'cammino spirituale', 'ricerca interiore', 'preghiera', 'guida spirituale'],
  astrologia: ['astrologo', 'astrologa', 'tema natale', 'oroscopo'],
  numerologia: ['numeri'],
  'tarocchi-evolutivi': ['tarocchi', 'tarologa', 'tarologo'],
  'hot-stone': ['pietre calde'],
  shiatsu: ['shiatzu'],
  'consulenza-ayurvedica': ['ayurveda', 'dosha'],
  'psicologia-perinatale': ['gravidanza', 'mamme', 'maternità', 'perinatale'],
});

const norm = (s) => String(s || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');

/** Le voci che rispondono a una parola: etichetta, famiglia, sinonimi. */
export function cercaDiscipline(query) {
  const q = norm(query).trim();
  if (!q) return [];
  const out = [];
  const extraSin = VIVO?.sinonimi || {};
  famiglieVive().forEach((fam) => {
    fam.items.forEach((d) => {
      const testi = [d.label, d.slug.replace(/-/g, ' '), fam.label, ...(CERCA_ANCHE[d.slug] || []), ...(extraSin[d.slug] || [])];
      if (testi.some((t) => norm(t).includes(q))) out.push(d);
    });
  });
  return out;
}

/* ── DV3 (2/10/2026) — IL REGISTRO VIVO ──────────────────────────────────
   Il system admin aggiunge discipline dalla regia (docs/ANALISI_DISCIPLINE_
   DINAMICHE_2026-10-02.md). Il server le unisce a quelle di codice e le
   serve da GET /public/discipline; qui si caricano UNA volta per sessione
   e tutto il modulo (famiglie, etichette, ricerca) legge l'unione. Se la
   rete manca o l'interruttore e' spento: lo specchio di codice qui sopra,
   identico a ieri. Nessuna schermata vuota, mai. */
let VIVO = null;            // { famiglie, sinonimi, extra, totale } dal server, o null
let promessa = null;
let etichetteCache = null;
const CHIAVE_SESSIONE = 'aurya_discipline_vive_v1';
const DURATA_MS = 10 * 60 * 1000;
const ascoltatori = new Set();

/** Le famiglie che il mondo vede: dal server se caricate, altrimenti il codice. */
export function famiglieVive() {
  return VIVO?.famiglie || DISCIPLINE_FAMILIES;
}

/** slug → etichetta, unione (le voci di codice vincono sempre). */
export function etichette() {
  if (!VIVO) return DISCIPLINE_LABELS;
  if (!etichetteCache) {
    const m = {};
    VIVO.famiglie.forEach((f) => f.items.forEach((d) => { m[d.slug] = d.label; }));
    etichetteCache = { ...m, ...DISCIPLINE_LABELS };
  }
  return etichetteCache;
}

function applica(dati) {
  // interruttore spento lato server (vive=false) o risposta strana → codice
  VIVO = (dati && dati.vive && Array.isArray(dati.famiglie) && dati.famiglie.length) ? dati : null;
  etichetteCache = null;
  ascoltatori.forEach((fn) => { try { fn(); } catch { /* un ascoltatore rotto non ferma gli altri */ } });
}

/** Carica il registro (una volta per sessione, 10 minuti in sessionStorage). */
export async function caricaDiscipline(forza = false) {
  if (!forza) {
    if (promessa) return promessa;
    try {
      const raw = sessionStorage.getItem(CHIAVE_SESSIONE);
      if (raw) {
        const { t, dati } = JSON.parse(raw);
        if (Date.now() - t < DURATA_MS) { applica(dati); promessa = Promise.resolve(VIVO); return promessa; }
      }
    } catch { /* private mode */ }
  }
  promessa = (async () => {
    try {
      const { default: api } = await import('../api/client');
      const r = await api.get('/public/discipline');
      applica(r.data);
      try { sessionStorage.setItem(CHIAVE_SESSIONE, JSON.stringify({ t: Date.now(), dati: r.data })); } catch { /* private mode */ }
    } catch {
      applica(null);                  // riserva: il codice
    }
    return VIVO;
  })();
  return promessa;
}

/** Per i componenti: si ri-renderizzano quando il registro arriva o cambia. */
export function useDiscipline() {
  const [, setGiro] = useState(0);
  useEffect(() => {
    const fn = () => setGiro((n) => n + 1);
    ascoltatori.add(fn);
    caricaDiscipline();
    return () => { ascoltatori.delete(fn); };
  }, []);
  return { famiglie: famiglieVive(), labels: etichette(), label: disciplineLabel, vive: !!VIVO };
}
