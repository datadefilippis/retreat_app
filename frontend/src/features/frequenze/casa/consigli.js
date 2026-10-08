/**
 * CONSIGLI — il motore della casa delle meditazioni (lotto CS, 8/10/2026).
 *
 * docs/PIANO_CASA_CONSIGLI_2026-10-08.md. Un motore a SEGNALI, deterministico
 * e spiegabile: nessun modello, una tabella di pesi e una somma leggibile.
 * La casa non e' piu' una lista di liste che filtrano lo stesso catalogo
 * (e con un titolo solo lo ripetono sette volte): e' COMPOSTA da un
 * bacino, una carta una volta sola, con sezioni che compaiono solo se
 * hanno abbastanza carte e che dicono il PERCHE'.
 *
 * Tutto e' puro: niente React, niente rete. Si prova con i test.
 */

export const PESI = Object.freeze({
  momento: 3, affinita: 3, continuita: 4, scoperta: 2, popolarita: 2, novita: 2, stanchezza: 3,
});
export const SOGLIE = Object.freeze({
  catalogoPiccolo: 5,     // fino a qui: vetrina, riprendi e la griglia
  minimoRiga: 3,          // una riga compare solo con almeno 3 carte residue
  minimoSpazio: 2,        // «Il tuo spazio» con almeno 2 (o il riprendi)
  perMomento: 6,          // quante carte in «Per questo momento»
  novitaGiorni: 90,       // la novita' decade a zero dopo 90 giorni
  novitaPiena: 14,        // ...e resta piena per 14
  preferitaRiposo: 7,     // una preferita non sentita da 7 giorni torna su
  m: 5,                   // la «m» della media bayesiana: con un ascolto solo non vince nessuno
});

const INTENTO_FASCIA = { dormire: 'notte', energizzare: 'mattina', concentrare: 'pausa', rilassare: 'sera', meditare: null, elaborare: 'sera' };

/** la fascia dell'ora: mattina 5–11, pausa 11–17, sera 17–22, notte 22–5 */
export function fasciaOra(h) {
  if (h >= 5 && h < 11) return 'mattina';
  if (h >= 11 && h < 17) return 'pausa';
  if (h >= 17 && h < 22) return 'sera';
  return 'notte';
}

export const FRASE_FASCIA = {
  mattina: 'È mattina: per cominciare con calma',
  pausa: 'Una pausa nel mezzo della giornata',
  sera: 'È sera: per lasciare andare',
  notte: 'È notte: per scivolare nel sonno',
};

const giorni = (a, b) => Math.max(0, (b - a) / 86400000);

/** la media bayesiana degli ascolti: (plays + m·μ) / (n + m), normalizzata 0–1 sul catalogo */
function popolarita(t, stats) {
  const plays = t.plays_total || 0;
  const bayes = (plays + SOGLIE.m * stats.media) / (1 + SOGLIE.m);
  return stats.max > 0 ? Math.min(1, bayes / stats.max) : 0;
}

function novita(t, adesso) {
  const data = t.published_at ? new Date(t.published_at).getTime() : null;
  if (!data) return 0;
  const g = giorni(data, adesso);
  if (g <= SOGLIE.novitaPiena) return 1;
  if (g >= SOGLIE.novitaGiorni) return 0;
  return 1 - (g - SOGLIE.novitaPiena) / (SOGLIE.novitaGiorni - SOGLIE.novitaPiena);
}

/**
 * Il punteggio di UNA meditazione per QUESTA persona, ADESSO.
 * persona: { recenti: [slug], riprendi: {slug, secondo}|null, preferite: Set(slug),
 *            fascia: 'sera'|null (abitudine), durataMedia: sec|0,
 *            completati: {slug: n}, ascoltatiOggi: Set(slug), categorieViste: Set }
 * Ritorna { totale, parti: {...}, perche: string|null }.
 */
export function punteggio(t, { ora = new Date(), persona = null, stats, categorieCatalogo = [] }) {
  const p = persona || {};
  const fascia = fasciaOra(ora.getHours());
  const parti = {};
  const perche = [];

  // momento: il momento della traccia (o il suo intento) coincide con l'ora, o con l'abitudine
  let m = 0;
  if (t.momento && t.momento === fascia) { m = 1; perche.push(FRASE_FASCIA[fascia]); }
  else if (t.momento && p.fascia && t.momento === p.fascia) { m = 0.8; perche.push(`Di solito ascolti di ${p.fascia}`); }
  else if (!t.momento && INTENTO_FASCIA[t.intent] === fascia) { m = 0.7; perche.push(FRASE_FASCIA[fascia]); }
  parti.momento = m * PESI.momento;

  // affinita': categoria/intento gia' scelti o salvati; durata vicina alla propria
  let a = 0;
  if (p.categorieViste && t.categoria && p.categorieViste.has(t.categoria)) { a += 0.6; }
  if (p.intentiVisti && t.intent && p.intentiVisti.has(t.intent)) { a += 0.2; }
  if (p.durataMedia && t.duration_sec) {
    const r = Math.abs(t.duration_sec - p.durataMedia) / Math.max(p.durataMedia, 60);
    if (r < 0.35) a += 0.2;
  }
  parti.affinita = Math.min(1, a) * PESI.affinita;

  // continuita': riprendi > preferita a riposo
  let c = 0;
  if (p.riprendi && p.riprendi.slug === t.slug && (p.riprendi.secondo || 0) > 5) { c = 1; perche.unshift('Da dove eri rimasta o rimasto'); }
  else if (p.preferite && p.preferite.has(t.slug)) {
    const ultimo = p.ultimoAscolto && p.ultimoAscolto[t.slug];
    const riposo = !ultimo || giorni(ultimo, ora.getTime()) >= SOGLIE.preferitaRiposo;
    c = riposo ? 0.6 : 0.3;
    if (riposo) perche.push('Una tua preferita che non senti da un po’');
  }
  parti.continuita = c * PESI.continuita;

  // scoperta: mai ascoltata; bonus se la categoria e' nuova per la persona
  const ascoltata = p.ascoltate ? p.ascoltate.has(t.slug) : false;
  let s = 0;
  if (p.ascoltate && !ascoltata) {
    s = 0.6;
    if (t.categoria && p.categorieViste && p.categorieViste.size > 0 && !p.categorieViste.has(t.categoria)) { s = 1; perche.push('Una categoria che non hai ancora provato'); }
    else perche.push('Non l’hai ancora ascoltata');
  }
  parti.scoperta = s * PESI.scoperta;

  parti.popolarita = popolarita(t, stats) * PESI.popolarita;
  const nv = novita(t, ora.getTime());
  parti.novita = nv * PESI.novita;
  if (nv >= 1) perche.push('Appena arrivata');

  // stanchezza: ascoltata oggi/ieri, o finita tre volte nell'ultima settimana
  let st = 0;
  if (p.ascoltatiOggi && p.ascoltatiOggi.has(t.slug)) st = 1;
  else if (p.completati && (p.completati[t.slug] || 0) >= 3) st = 0.6;
  parti.stanchezza = -st * PESI.stanchezza;

  const totale = Object.values(parti).reduce((x, y) => x + y, 0);
  return { totale, parti, perche: perche[0] || null };
}

/** le statistiche del catalogo che servono al punteggio */
export function statistiche(tutte) {
  const plays = tutte.map((t) => t.plays_total || 0);
  const media = plays.length ? plays.reduce((x, y) => x + y, 0) / plays.length : 0;
  return { media, max: plays.length ? Math.max(...plays, 1) : 1, n: tutte.length };
}

/** la persona, dai dati del profilo (sound_recenti, sound_riprendi, abitudine) e dai preferiti */
export function persona({ recenti = [], riprendi = null, preferite = [], abitudine = null, perSlug = {} }) {
  const ascoltate = new Set(recenti);
  const categorieViste = new Set();
  const intentiVisti = new Set();
  [...recenti, ...preferite].forEach((s) => { const t = perSlug[s]; if (t?.categoria) categorieViste.add(t.categoria); if (t?.intent) intentiVisti.add(t.intent); });
  return {
    recenti, riprendi, preferite: new Set(preferite), ascoltate, categorieViste, intentiVisti,
    fascia: abitudine?.fascia || null,
    durataMedia: abitudine?.durata_media_sec || 0,
    completati: abitudine?.completati || {},
    ascoltatiOggi: new Set(abitudine?.ascoltati_oggi || []),
    ultimoAscolto: abitudine?.ultimo_ascolto || {},
  };
}

export const FASCE_DURATA = [['breve', '≤ 10 min'], ['media', '10–20 min'], ['lunga', '20+ min']];
export const fasciaDurata = (sec) => ((sec || 0) <= 10 * 60 ? 'breve' : (sec || 0) <= 20 * 60 ? 'media' : 'lunga');

/**
 * LA CASA COMPOSTA. Ritorna le sezioni nell'ordine in cui si pescano dal
 * bacino; ogni carta compare UNA volta (la vetrina e' l'eccezione).
 *   { piccolo, vetrina, riprendi, sezioni: [{id, titolo, perche, items, tutte}], griglia }
 */
export function componiCasa({ tutte, vetrina = null, persona: p = null, categorie = [], ora = new Date() }) {
  const stats = statistiche(tutte);
  const puntati = tutte.map((t) => ({ t, ...punteggio(t, { ora, persona: p, stats }) }));
  const perSlug = Object.fromEntries(puntati.map((x) => [x.t.slug, x]));
  const usate = new Set(vetrina ? [vetrina.slug] : []);
  const prendi = (lista, n) => {
    const out = [];
    for (const x of lista) { if (out.length >= n) break; if (!usate.has(x.t.slug)) { out.push(x); } }
    return out;
  };
  const segna = (xs) => xs.forEach((x) => usate.add(x.t.slug));
  const sezioni = [];
  const piccolo = tutte.length <= SOGLIE.catalogoPiccolo;

  // 2. riprendi: la carta grande, solo se c'e' (anche col catalogo piccolo)
  let riprendi = null;
  if (p?.riprendi && perSlug[p.riprendi.slug] && (p.riprendi.secondo || 0) > 5) {
    riprendi = { t: perSlug[p.riprendi.slug].t, secondo: p.riprendi.secondo };
    usate.add(riprendi.t.slug);
  }

  if (!piccolo) {
    // 3. per questo momento: i punteggi piu' alti, col perche' del primo
    const ordinati = [...puntati].sort((a, b) => b.totale - a.totale);
    const momento = prendi(ordinati, SOGLIE.perMomento);
    if (momento.length >= SOGLIE.minimoRiga) {
      const fascia = fasciaOra(ora.getHours());
      sezioni.push({ id: 'momento', titolo: 'Per questo momento', perche: momento[0].perche || FRASE_FASCIA[fascia], items: momento.map((x) => x.t) });
      segna(momento);
    }
    // 4. da scoprire: mai ascoltate (solo con una persona), per affinita' e popolarita'
    if (p?.ascoltate) {
      const nuove = ordinati.filter((x) => !p.ascoltate.has(x.t.slug))
        .sort((a, b) => (b.parti.affinita + b.parti.popolarita) - (a.parti.affinita + a.parti.popolarita));
      const scoperta = prendi(nuove, 12);
      if (scoperta.length >= SOGLIE.minimoRiga) {
        sezioni.push({ id: 'scoperta', titolo: 'Da scoprire', perche: 'Non le hai ancora ascoltate', items: scoperta.map((x) => x.t), tutte: nuove.map((x) => x.t) });
        segna(scoperta);
      }
    }
  }

  // 5. le preferite: solo quelle non gia' uscite sopra (almeno 2)
  let preferite = [];
  if (p?.preferite && p.preferite.size) {
    preferite = prendi(puntati.filter((x) => p.preferite.has(x.t.slug)), 12);
    if (preferite.length >= SOGLIE.minimoSpazio || (preferite.length && piccolo)) segna(preferite); else preferite = [];
  }

  // 6. le categorie: una riga per categoria, con almeno 3 carte residue
  const categorieRighe = [];
  if (!piccolo) {
    categorie.forEach((c) => {
      const della = prendi(puntati.filter((x) => x.t.categoria === c.slug).sort((a, b) => b.totale - a.totale), 12);
      if (della.length >= SOGLIE.minimoRiga) {
        categorieRighe.push({ id: `cat-${c.slug}`, titolo: c.label, perche: c.descrizione || null, items: della.map((x) => x.t), tutte: tutte.filter((t) => t.categoria === c.slug), categoria: c.slug });
        segna(della);
      }
    });
  }

  // 7. le altre: cio' che NESSUNA sezione ha preso (niente doppioni: la mappa
  //    intera sta dietro «Tutte le meditazioni»). Col catalogo piccolo e' la casa.
  const altre = puntati.filter((x) => !usate.has(x.t.slug)).map((x) => x.t);
  return {
    piccolo, vetrina, riprendi, sezioni, preferite: preferite.map((x) => x.t), categorieRighe,
    altre, tutte,
    fasceDurata: new Set(tutte.map((t) => fasciaDurata(t.duration_sec))),
  };
}
