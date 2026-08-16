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
    slug: 'anima', label: 'Anima & Percorsi interiori',
    items: [
      { slug: 'costellazioni-familiari', label: 'Costellazioni familiari' },
      { slug: 'counseling-olistico', label: 'Counseling olistico' },
      { slug: 'coaching-olistico', label: 'Coaching olistico' },
      { slug: 'cerchi-di-donne', label: 'Cerchi di donne' },
      { slug: 'sciamanesimo', label: 'Pratiche sciamaniche' },
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
