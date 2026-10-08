/**
 * I TESTI DELLA BIBLIOTECA (ES0, 8/10/2026) — una fonte sola per la pagina
 * nuova di Esplora (esplora/BibliotecaPage) e per la vista dentro il
 * compositore (FrequenzePage): le famiglie con il loro tono, una riga per
 * famiglia, l'intro, la legenda A/B/C e «come leggere».
 */

/* le quattro famiglie: slug per l'indirizzo (?famiglia=), tono della casa */
export const FAMIGLIE = [
  { chiave: 'Bande cerebrali', slug: 'bande-cerebrali', tono: 'viola', riga: "Ritmi dell'attività elettrica del cervello." },
  { chiave: 'Altre frequenze', slug: 'altre-frequenze', tono: 'oro', riga: 'Frequenze sonore, fenomeni fisici, accordature e tradizioni.' },
  { chiave: 'Ritmi del corpo', slug: 'ritmi-del-corpo', tono: 'salvia', riga: 'Respiro, cuore, passo: ritmi da seguire, non frequenze da subire.' },
  { chiave: 'Metodi', slug: 'metodi', tono: 'acqua', riga: 'Tecniche per costruire e modulare uno stimolo sonoro.' },
];
export const famigliaDaSlug = (slug) => FAMIGLIE.find((f) => f.slug === slug) || null;
export const famigliaDaChiave = (chiave) => FAMIGLIE.find((f) => f.chiave === chiave) || null;

export const CAT_HINT = Object.fromEntries(FAMIGLIE.map((f) => [f.chiave, f.riga]));

export const CAT_INTRO = {
  'Bande cerebrali': {
    t: 'Cosa sono le bande cerebrali?',
    p: "Il cervello presenta attività elettrica ritmica che possiamo osservare, per esempio, attraverso l'EEG. Delta, Theta, Alpha, Beta e Gamma descrivono diverse gamme di queste oscillazioni. Non sono semplicemente frequenze sonore: qui esploriamo il fenomeno cerebrale e, separatamente, come alcuni stimoli sonori cercano di interagire con esso.",
  },
  'Ritmi del corpo': {
    t: 'Qui il ritmo lo dai tu.',
    p: "Nelle altre sezioni il suono è l'oggetto dell'ascolto. Qui è un metronomo: un'onda che sale e scende per darti il passo del respiro, o una pulsazione per il cammino. La differenza conta anche per l'onestà di quello che possiamo dire, ciò che la ricerca documenta riguarda la pratica (respirare lentamente, muoversi a tempo), non il suono che la accompagna.",
  },
  'Altre frequenze': {
    t: 'Frequenze diverse, origini diverse.',
    p: "Qui incontrerai frequenze con origini molto diverse: ricerca neuroscientifica, fenomeni fisici, accordature musicali e tradizioni sonore. Il livello di evidenza ti aiuta a distinguere ciò che è documentato da ciò che appartiene soprattutto alla tradizione.",
  },
  'Metodi': {
    t: 'Una frequenza dice «cosa». Un metodo dice «come».',
    p: "I metodi descrivono modi diversi di costruire o modulare uno stimolo sonoro: dal battito binaurale al tono isocronico, fino alla modulazione di un paesaggio sonoro.",
  },
};

/* la chiave dei metodi: una riga ciascuno, nella famiglia «Metodi» */
export const METODI_CHIAVE = [
  ['Binaurale', 'due toni diversi, uno per orecchio: il battito lo percepisce il sistema uditivo'],
  ['Monaurale', 'due toni miscelati: il battito è già nel segnale'],
  ['Isocronico', 'un tono modulato: pulsazione molto evidente'],
  ['Bilaterale', 'il suono alterna destra e sinistra: movimento nello spazio'],
  ['Soffio', 'un rumore continuo modulato: ritmo immerso nel paesaggio'],
  ['Tono puro', 'una frequenza stabile: nessuna pulsazione'],
];

/* la legenda del grado di evidenza */
export const GRADI = {
  A: { label: 'Evidenza solida', spiega: 'Il fenomeno è ben documentato dalla ricerca scientifica.' },
  B: { label: 'Ricerca in corso', spiega: 'Esistono risultati interessanti, ma le evidenze non sono ancora conclusive.' },
  C: { label: 'Tradizione e simbolismo', spiega: "L'associazione appartiene soprattutto alla tradizione o alla cultura, senza una dimostrazione fisiologica consolidata." },
};

export const HOWTO_BODY = '<h4>Frequenza</h4><p>La proprietà fisica di un suono, espressa in Hertz.</p>'
  + '<h4>Banda cerebrale</h4><p>Una gamma di oscillazioni dell\'attività elettrica cerebrale osservabile, per esempio, attraverso l\'EEG.</p>'
  + '<h4>Metodo</h4><p>Il modo in cui uno stimolo sonoro viene costruito o modulato.</p>'
  + '<h4>Badge A/B/C</h4><p>Indica il livello di evidenza relativo alle affermazioni presentate, non quanto una frequenza sia «potente».</p>'
  + '<h4>Ascolta</h4><p>Permette di fare esperienza diretta dello stimolo.</p>';
