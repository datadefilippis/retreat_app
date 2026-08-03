/**
 * Le introduzioni delle pagine di categoria del Magazine (PC1).
 *
 * PERCHE' ESISTONO. Le pagine /blog/categoria/:slug erano un titolo e
 * una griglia: indicizzabili, ma senza niente da dire. Una pagina di
 * categoria che si limita a elencare i figli non e' un hub, e' un
 * indice. Con un'introduzione diventa la porta d'ingresso di un
 * argomento: dice di che si tratta, cosa ci si trova e da dove
 * conviene partire, e passa autorita' ai figli con link che hanno
 * un'ancora vera.
 *
 * E' anche il modo piu' economico di dare senso ai cluster magri: una
 * categoria con un articolo solo ma un'introduzione seria e' una
 * pagina; con il solo titolo e' un vicolo.
 *
 * PERCHE' NON E' i18n. Il sito pubblico e' solo italiano dal 2/8/2026
 * (decisione del founder): tenere duemila parole di prosa dentro un
 * file di chiavi le renderebbe illeggibili a chi le deve rivedere, e
 * non servirebbe a nessuno. Se un giorno torna il multilingua, questo
 * modulo e' il posto da cui partire.
 *
 * COME SI AGGIUNGE UNA CATEGORIA. Si aggiunge la voce qui: la pagina
 * la usa se c'e' e resta com'era se manca. Niente e' obbligatorio.
 *
 * Forma di ogni voce:
 *   lede      una riga, sostituisce il sottotitolo generico
 *   paragrafi il corpo dell'introduzione
 *   porte     "da dove partire": ancore vere verso i figli
 */

const INTRO = {
  yoga: {
    lede: 'Una pratica antica che in Occidente si è divisa in molte forme, e la prima difficoltà è capire quale hai davanti.',
    paragrafi: [
      'Sul volantino di una scuola trovi sei nomi e nessuna spiegazione. Hatha, vinyasa, ashtanga, yin, kundalini: sembrano discipline diverse e invece sono modi diversi di dosare gli stessi ingredienti, cioè posizione, respiro, ritmo e attenzione.',
      'Qui raccontiamo lo yoga per quello che è nella pratica: cosa succede in una lezione, che ritmo ha, cosa lascia addosso. E anche la parte che in Occidente si perde di solito, perché le posizioni sono solo uno degli otto rami di cui è fatto.',
    ],
    porte: [
      { to: '/blog/differenze-tipi-di-yoga-hatha-vinyasa-ashtanga-yin-kundalini',
        label: 'Le differenze fra hatha, vinyasa, ashtanga, yin e kundalini' },
      { to: '/blog/meditazione-per-chi-inizia-guida-semplice',
        label: 'Meditazione per chi inizia' },
    ],
  },

  scegliere: {
    lede: 'La parte che nessuno spiega: come si riconosce chi lavora bene, prima di affidargli qualcosa di personale.',
    paragrafi: [
      'In Italia le professioni olistiche rientrano fra quelle non organizzate in albi. Non esiste un registro da consultare, e questo lascia chi cerca senza appigli: trenta profili si somigliano tutti, e nessuno sta mentendo.',
      'Gli appigli però esistono, e sono verificabili: cosa dice la legge, cosa vale un attestato, quali domande fare al primo contatto, e soprattutto qual è il confine che nessun operatore può superare. È il tema su cui abbiamo più da dire, perché è quello che ci ha fatto costruire Aurya.',
    ],
    porte: [
      { to: '/blog/come-capire-se-un-operatore-olistico-e-serio',
        label: 'Come capire se un operatore olistico è serio' },
    ],
  },

  breathwork: {
    lede: 'Respiriamo ventimila volte al giorno senza accorgercene. Queste sono le pratiche che lo fanno di proposito.',
    paragrafi: [
      'La famiglia è larga e si divide in due rami che vale la pena non confondere: le tecniche lente, che abbassano l’attivazione, e quelle intense, che la alzano prima di lasciarla cadere. Producono effetti opposti e hanno cautele diverse.',
      'Raccontiamo le une e le altre con la stessa attenzione, compresa la fisiologia di quello che si sente durante una sessione: sapere perché formicolano le mani toglie spavento senza togliere valore all’esperienza. E le controindicazioni stanno scritte, perché qui contano più che altrove.',
    ],
    porte: [
      { to: '/blog/breathwork-cose-tecniche-benefici',
        label: 'Breathwork: le tecniche principali' },
      { to: '/blog/rebirthing-cose-come-funziona-una-sessione',
        label: 'Rebirthing: come funziona una sessione' },
    ],
  },

  meditazione: {
    lede: 'Allenare l’attenzione, non svuotare la mente. Da qui parte quasi tutto il resto.',
    paragrafi: [
      'È la pratica su cui girano più malintesi: chi molla lo fa quasi sempre perché ha pensato di doverla fare bene subito, o di dover smettere di pensare. Sono due idee sbagliate che si tolgono in una riga, e cambiano tutto.',
      'Qui trovi come si comincia davvero, cosa succede nelle prime settimane, cosa dice la ricerca su ciò che funziona per lo stress, e come costruire una pratica breve che regga nel tempo invece di durare tre giorni.',
    ],
    porte: [
      { to: '/blog/meditazione-per-chi-inizia-guida-semplice',
        label: 'Meditazione per chi inizia' },
      { to: '/blog/pratiche-olistiche-contro-stress-cosa-funziona',
        label: 'Cosa funziona contro lo stress, secondo la ricerca' },
      { to: '/blog/kit-pratiche-quotidiane-15-minuti',
        label: 'Il kit delle pratiche quotidiane' },
    ],
  },

  energia: {
    lede: 'Reiki, costellazioni, tarocchi, tema natale: pratiche molto diverse che condividono un modo di guardare.',
    paragrafi: [
      'Sono le discipline su cui è più difficile trovare informazioni misurate: o vengono raccontate da chi le vende, o liquidate da chi non le ha mai viste. In mezzo resta chi vorrebbe capire cosa succede in una sessione prima di prenotarla.',
      'Le raccontiamo dicendo tre cose per ciascuna: com’è fatta una seduta, cosa dice la ricerca dove esiste, e come si riconosce chi la conduce con serietà. Dove le prove mancano, lo scriviamo.',
    ],
    porte: [
      { to: '/blog/reiki-cose-come-funziona-una-sessione',
        label: 'Reiki: come funziona una sessione' },
      { to: '/blog/costellazioni-familiari-cosa-sono-come-funzionano',
        label: 'Costellazioni familiari: cosa dice la ricerca' },
      { to: '/blog/come-capire-se-un-operatore-olistico-e-serio',
        label: 'Come capire se un operatore è serio' },
    ],
  },

  suono: {
    lede: 'Campane, gong, vibrazione: cosa succede a stare dentro un suono per un’ora.',
    paragrafi: [
      'Un bagno di suono si racconta male a parole, ed è il motivo per cui chi non l’ha provato lo immagina come un concerto o come una seduta di rilassamento guidato. È un’altra cosa, e conviene sapere cosa aspettarsi prima di sdraiarsi.',
      'Qui trovi come si svolge un trattamento, che differenza c’è fra gli strumenti, e le poche cautele che valgono la pena di conoscere prima di prenotare.',
    ],
    porte: [
      { to: '/blog/campane-tibetane-benefici-come-funzionano',
        label: 'Campane tibetane, e la differenza col cristallo' },
      { to: '/blog/bagno-di-gong-sound-healing-benefici',
        label: 'Bagno di gong: cosa aspettarsi' },
    ],
  },

  femminile: {
    lede: 'Spazi in cui si parla senza essere interrotte, e senza ricevere consigli non richiesti.',
    paragrafi: [
      'I cerchi sono una forma antica tornata in circolazione per una ragione precisa: in una vita che chiede di essere sempre performanti, uno spazio in cui si può stare senza dover risolvere niente è diventato raro.',
      'Raccontiamo cosa succede davanti a una candela accesa, come si svolge un incontro, e come si trova un cerchio serio vicino a casa.',
    ],
    porte: [
      { to: '/blog/cerchi-di-donne-cosa-sono-come-funzionano',
        label: 'Cerchi di donne: come funzionano e come trovarne uno' },
    ],
  },

  detox: {
    lede: 'Digiuno e depurazione: cosa dice la fisiologia, e cosa è marketing.',
    paragrafi: [
      'È l’area del benessere in cui circolano più affermazioni non verificabili, a partire dall’idea che il corpo abbia bisogno di aiuto per liberarsi delle tossine. La fisiologia racconta qualcosa di più interessante e meno semplice.',
      'Qui trovi cosa succede davvero durante un digiuno consapevole, a chi è adatto, chi dovrebbe starne lontano, e come si riconosce una struttura che lo propone in sicurezza.',
    ],
    porte: [
      { to: '/blog/digiuno-consapevole-detox-benefici-falsi-miti',
        label: 'Digiuno consapevole e detox: benefici e controindicazioni' },
    ],
  },

  // La sezione dei professionisti: fuori dall'indice del Magazine
  // (OF4), ma la sua pagina resta ed e' la porta della sezione.
  operatori: {
    lede: 'Le guide per chi il benessere lo pratica di mestiere: numeri, regole e mestiere.',
    paragrafi: [
      'Chi lavora nel benessere passa gli anni a formarsi sulla pratica e quasi nessuno gli spiega il resto: quando serve la partita IVA, come si calcola il prezzo di un ritiro senza lavorare in perdita, come si riempiono i posti senza svendersi.',
      'Queste guide stanno separate dal resto del Magazine perché parlano a un’altra persona. Sono scritte con i numeri veri e senza promesse di crescita facile.',
    ],
    porte: [
      { to: '/blog/partita-iva-operatore-olistico-fiscalita-guida',
        label: 'Partita IVA e fiscalità: la guida 2026' },
      { to: '/blog/prezzo-giusto-ritiro-come-calcolarlo',
        label: 'Come calcolare il prezzo di un ritiro' },
      { to: '/blog/come-promuovere-un-ritiro-e-riempire-i-posti',
        label: 'Come promuovere un ritiro e riempire i posti' },
    ],
  },
};

/** L'introduzione della categoria, o null se non ne ha una. */
export default function introPerCategoria(slug) {
  return (slug && INTRO[slug]) || null;
}
