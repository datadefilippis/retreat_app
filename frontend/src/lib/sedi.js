/* SD (14/9/2026) — le sedi dell'operatore: specchio di services/sedi.py
   (il tetto vive in un posto solo per lato). */
export const SEDI_MAX = 3;

export function sediDaProfilo(pp) {
  if (!pp) return [];
  if (Array.isArray(pp.sedi) && pp.sedi.length) return pp.sedi;
  if (!pp.city && !pp.region) return [];
  return [{ citta: pp.city || null, regione: pp.region || null, lat: pp.latitude ?? null,
    lng: pp.longitude ?? null, etichetta: [pp.city, pp.region].filter(Boolean).join(', ') }];
}

/* gli specchi della sede principale: city/latitude/longitude che il resto
   dell'editor (anteprima, completezza) continua a leggere */
export function specchiSede(sedi) {
  const p = (sedi || [])[0];
  if (!p) return { city: null, region: null, latitude: null, longitude: null };
  return { city: p.citta || p.regione || null, region: p.regione || null,
    latitude: p.lat ?? null, longitude: p.lng ?? null };
}

/* SEO-L (founder, 14/9 sera) — il complemento di luogo per titolo e
   description del profilo: «a Lecce», «in Puglia», «nel Lazio», «ad Acri».
   Stessa regola di services/sedi.py luogo_seo: la shell per i crawler e il
   client devono produrre lo STESSO titolo. */
const IN_REGIONE = { Lazio: 'nel Lazio', Marche: 'nelle Marche' };
export function luogoSeo(data) {
  const sede = sediDaProfilo(data)[0];
  if (!sede) return '';
  if (sede.citta) return `${/^a/i.test(sede.citta) ? 'ad' : 'a'} ${sede.citta}`;
  if (sede.regione) return IN_REGIONE[sede.regione] || `in ${sede.regione}`;
  return '';
}
