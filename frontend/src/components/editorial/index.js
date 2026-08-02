/**
 * Kit editoriale (HP1) — i mattoni delle superfici di racconto:
 * home di rete, manifesto, magazine e le pagine editoriali future.
 * Un solo posto dove vivono tipografia, misure di riga, ritmo
 * verticale, stati di focus e la dissolvenza d'ingresso.
 *
 * DS1 (2/8/2026) — i quattro mattoni che mancavano, e che mancavano a
 * TUTTE le pagine del ciclo, non a una sola: l'apertura fotografica
 * (PhotoOpener), la fascia a tutta larghezza (PhotoBand), la sezione a
 * due colonne foto/testo (PhotoSplit) e l'indice dei movimenti
 * (MovementIndex). Il velo delle prime due e' calcolato, non sperato:
 * le misure stanno nei commenti di testa dei rispettivi file.
 */
export { default as Section } from './Section';
export { default as DisplayTitle, TitleLine } from './DisplayTitle';
export { default as Lede } from './Lede';
export { default as Quote } from './Quote';
export { default as PersonCard, truncateWords } from './PersonCard';
export { default as ArticleCard } from './ArticleCard';
export { default as PillarCard } from './PillarCard';
export { default as EditorialCta } from './EditorialCta';
export { default as PhotoOpener } from './PhotoOpener';
export { default as PhotoBand } from './PhotoBand';
export { default as PhotoSplit } from './PhotoSplit';
export { default as MovementIndex } from './MovementIndex';
export { default as useReveal } from './useReveal';
