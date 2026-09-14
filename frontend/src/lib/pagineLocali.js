/* SEO-B (14/9/2026 sera) — le pagine locali della directory:
   /operatori/{disciplina}, /operatori/{regione}, /operatori/{disciplina}/{regione}.
   Il risolutore e' lo specchio di services/pagine_locali.risolvi: prima la
   disciplina, poi la regione, poi la categoria di prodotto (legacy). Titoli,
   description e noindex NON vivono qui: li manda il backend in `pagina`
   (stessa verita' della shell per i crawler). */
import { DISCIPLINE_LABELS } from './disciplines';
import { REGIONE_DA_SLUG, slugRegione } from './sedi';

export function risolviSegmenti(a, b) {
  const out = { disciplina: null, regione: null, categoria: null, valida: true };
  const x = (a || '').toLowerCase() || null;
  const y = (b || '').toLowerCase() || null;
  if (x && DISCIPLINE_LABELS[x]) {
    out.disciplina = x;
    if (y) { if (REGIONE_DA_SLUG[y]) out.regione = REGIONE_DA_SLUG[y]; else out.valida = false; }
  } else if (x && REGIONE_DA_SLUG[x]) {
    out.regione = REGIONE_DA_SLUG[x];
    if (y) out.valida = false;
  } else if (x) {
    out.categoria = x;
    if (y) out.valida = false;
  }
  return out;
}

export function percorsoLocale(disciplina, regione) {
  const seg = [disciplina, regione ? slugRegione(regione) : null].filter(Boolean);
  return '/operatori' + (seg.length ? '/' + seg.join('/') : '');
}
