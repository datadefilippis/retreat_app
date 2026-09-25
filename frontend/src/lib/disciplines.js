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
    ],
  },
  {
    slug: 'massaggio', label: 'Massaggio & Bodywork',
    items: [
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
      { slug: 'counseling-gestalt', label: 'Counseling Gestalt' },
      { slug: 'coaching-olistico', label: 'Coaching olistico' },
      { slug: 'cerchi-di-donne', label: 'Cerchi di donne' },
      { slug: 'sacro-femminile', label: 'Sacro femminile & Ciclicità' },
      { slug: 'sciamanesimo', label: 'Pratiche sciamaniche' },
      // 25/9/2026 (founder): la ricerca spirituale come pratica accompagnata
      { slug: 'percorsi-spirituali', label: 'Percorsi spirituali' },
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

export const disciplineLabel = (slug) => DISCIPLINE_LABELS[slug] || slug;

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
  'counseling-gestalt': ['gestalt', 'counselor gestalt', 'gestaltico'],
  'coaching-olistico': ['coach', 'life coach'],
  'massaggio-olistico': ['massaggio', 'massaggiatrice', 'massaggiatore', 'massaggi'],
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
  pranoterapia: ['pranoterapeuta'],
  cristalloterapia: ['cristalli', 'pietre'],
  'access-bars': ['bars'],
  'theta-healing': ['theta'],
  kinesiologia: ['kinesiologo', 'kinesiologa'],
  ipnosi: ['ipnoterapia', 'rilassamento'],
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
  DISCIPLINE_FAMILIES.forEach((fam) => {
    fam.items.forEach((d) => {
      const testi = [d.label, d.slug.replace(/-/g, ' '), fam.label, ...(CERCA_ANCHE[d.slug] || [])];
      if (testi.some((t) => norm(t).includes(q))) out.push(d);
    });
  });
  return out;
}
