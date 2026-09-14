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
