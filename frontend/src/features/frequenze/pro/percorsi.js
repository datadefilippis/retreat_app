/**
 * I PERCORSI — i programmi del metodo (M2, 26/8/2026).
 *
 * La lezione strutturale di Unyte (piano di posizionamento): il
 * professionista serio non sceglie «una traccia», sceglie un
 * PROGRAMMA — con una dose, una cadenza, una progressione. SSP sono
 * 10 tracce da 30 minuti titolate su settimane; i nostri percorsi
 * sono sequenze di protocolli del catalogo, con la stessa disciplina
 * e la nostra onestà.
 *
 * DATI IN GIT, come il catalogo: i percorsi curati sono contenuto
 * editoriale nostro, versionato e sotto guardia. Ogni TAPPA cita un
 * protocollo del catalogo per id — MAI una ricetta propria: se una
 * tappa nominasse un protocollo che non esiste, i test rompono.
 *
 * LE PAROLE: un percorso non «cura» e non «tratta» — accompagna una
 * pratica regolare. La progressione è pedagogica (dal familiare al
 * profondo), non clinica. La cadenza è un ritmo consigliato, non una
 * prescrizione.
 */

export const PERCORSI = Object.freeze([
  {
    id: 'radicamento',
    titolo: 'Radicamento',
    sottotitolo: 'Quattro settimane per costruire una pratica di presenza.',
    racconto: 'Si comincia dal peso e si torna al peso: GROUND è la '
      + 'colonna del percorso, Rilassare il respiro fra una tappa e '
      + 'l’altra. La progressione è nella regolarità, non '
      + 'nell’intensità: lo stesso ascolto, ripetuto, diventa '
      + 'un’altra cosa.',
    indicazioni: 'Per chi arriva teso e «senza terra». Funziona come '
      + 'chiusura di un lavoro corporeo o come pratica a sé.',
    durata: { settimane: 4, a_settimana: 2 },
    tappe: [
      { protocollo: 'ground', nota: 'La prima volta: si ascolta e basta.' },
      { protocollo: 'rilassare', nota: 'Il contrappunto: uno stato stabile, senza discese.' },
      { protocollo: 'ground', nota: 'Il ritorno: il corpo riconosce l’arco.' },
      { protocollo: 'ground', nota: 'La ripetizione è il lavoro.' },
      { protocollo: 'rilassare', nota: 'Di nuovo il respiro fra le tappe.' },
      { protocollo: 'ground', nota: 'Da qui in poi il peso si trova prima.' },
      { protocollo: 'ground', nota: 'La penultima: come la quarta, ma più a fondo.' },
      { protocollo: 'ground', nota: 'L’ultima: il congedo del percorso.' },
    ],
    revisione: '2026-08',
  },
  {
    id: 'verso-il-sonno',
    titolo: 'Verso il sonno',
    sottotitolo: 'Tre settimane per accompagnare la fine della giornata.',
    racconto: 'Prima si impara a distendersi (Rilassare), poi si '
      + 'scende (Dormire). Le tappe serali si ascoltano già distesi, '
      + 'e non c’è un traguardo: c’è un’abitudine che '
      + 'si costruisce.',
    indicazioni: 'Pratica serale. Non è un trattamento '
      + 'dell’insonnia — la nota di evidenza di Dormire lo dice '
      + 'chiaramente, e vale per tutto il percorso.',
    durata: { settimane: 3, a_settimana: 2 },
    tappe: [
      { protocollo: 'rilassare', nota: 'Si parte da sdraiati, a metà pomeriggio se possibile.' },
      { protocollo: 'rilassare', nota: 'La seconda: stessa pratica, orario serale.' },
      { protocollo: 'dormire', nota: 'La prima discesa: luci basse, già a letto.' },
      { protocollo: 'dormire', nota: 'La discesa, ripetuta.' },
      { protocollo: 'rilassare', nota: 'Un passo indietro voluto: si consolida.' },
      { protocollo: 'dormire', nota: 'L’ultima: l’abitudine è la consegna.' },
    ],
    revisione: '2026-08',
  },
  {
    id: 'spazio-di-calma',
    titolo: 'Spazio di calma',
    sottotitolo: 'Due settimane di pratica breve, quasi quotidiana.',
    racconto: 'Sei minuti alla volta: CALM è pensata per entrare '
      + 'nelle giornate vere. Tre ascolti a settimana, brevi, '
      + 'con Rilassare come tappa lunga di metà percorso.',
    indicazioni: 'Per chi «non ha tempo»: la tappa più lunga dura '
      + 'venti minuti, le altre sei. Ottimo primo percorso.',
    durata: { settimane: 2, a_settimana: 3 },
    tappe: [
      { protocollo: 'calm', nota: 'Sei minuti. Solo questo.' },
      { protocollo: 'calm', nota: 'Stessa pratica, momento diverso della giornata.' },
      { protocollo: 'rilassare', nota: 'La tappa lunga: venti minuti, con calma.' },
      { protocollo: 'calm', nota: 'Si riparte breve.' },
      { protocollo: 'rilassare', nota: 'La seconda tappa lunga.' },
      { protocollo: 'calm', nota: 'L’ultima: sei minuti che ormai conosci.' },
    ],
    revisione: '2026-08',
  },
]);

export const percorso = (id) => PERCORSI.find((p) => p.id === id) || null;
