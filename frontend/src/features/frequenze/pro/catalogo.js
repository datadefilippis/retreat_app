/**
 * IL CATALOGO AURYA CORE — la libreria curata (S1, 26/8/2026).
 *
 * La decisione di prodotto (audit 26/8): Sound Professional non è un
 * editor — l'operatore SCEGLIE un protocollo curato, non compone.
 * Questo file è il catalogo: l'elenco editoriale di ciò che si può
 * scegliere, con la scheda onesta di ciascun protocollo.
 *
 * È DATI, e vive qui e non in Mongo, per la stessa ragione di
 * content/esperienze.js: i protocolli curati sono contenuto NOSTRO —
 * versionato in git, sotto guardia nei test, rivisto come si rivede
 * un testo. I protocolli DELL'OPERATORE vivono invece in
 * `sound_protocols` (P2): privati, versionati per documento, con
 * audit. Due scaffali, due nature.
 *
 * NIENTE RICETTE NUOVE E NIENTE COPIE: questo file AVVOLGE ciò che
 * esiste — le due esperienze (content/esperienze.js) e i sei
 * protocolli per intento (content/protocolli.js, i gradi B/C del
 * founder). Se una ricetta cambia là, il catalogo la riflette; se
 * questo file contenesse una `layer(...)`, sarebbe una copia che
 * diverge (guardia nei test).
 *
 * LA SCHEDA ONESTA. Ogni voce dichiara la sua origine:
 *   - 'benessere'   pratica di progettazione/tradizione del benessere:
 *                   nessun grado, e la nota dice cosa NON promette;
 *   - 'letteratura' derivato da letteratura sull'entrainment, con il
 *                   GRADO del founder (B/C) e la sua nota verbatim —
 *                   inclusi i punti deboli. Il patto di onestà del
 *                   brand sta proprio nel non nasconderli.
 * Le controindicazioni non si riscrivono qui: il testo unico è
 * content/safety.js (ciclo SF), una voce sola in tutta Aurya Sound.
 *
 * Due strati, sempre: la SCHEDA (questo file) è ciò che l'operatore
 * legge; lo SCORE (costruisci()) è ciò che il motore suona. La
 * matematica non compare mai sulla scheda.
 *
 * LA VOCE DELLE EVIDENZE (C0, feedback founder 26/8: «siamo troppo
 * critici contro noi stessi»): l'onestà non è autocritica. La regola:
 * PRIMA ciò che è documentato, POI il confine — e il confine detto
 * come professionalità («sappiamo dove finisce»), mai come resa.
 * Ogni scheda NOMINA la sua teoria (`teoria`): entrainment uditivo e
 * ASSR, respirazione di risonanza, psicoacustica — come i programmi
 * internazionali nominano la polivagale, ma con àncore misurabili.
 * Stessi fatti di prima, ordine giusto. Le frasi da autosabotaggio
 * («il più debole», «la più severa») sono VIETATE da guardia.
 */
import { ESPERIENZE } from '../content/esperienze';
import { PROTOCOLLI } from '../content/protocolli';

/* la durata dei protocolli per intento: quella che Crea già usa
   quando li carica (durataMin || 20 — FrequenzePage) */
const DURATA_INTENTO_SEC = 20 * 60;
/* i fade di casa per le ricette di Crea (gli stessi default del
   compositore); le esperienze portano i loro nello score */
const FADE_IN = 10, FADE_OUT = 20;

export const ORIGINI = Object.freeze({
  benessere: 'Pratica di benessere',
  letteratura: 'Derivato da letteratura',
});

/** Avvolge una build di content/protocolli.js in uno score v1. */
const scoreIntento = (build, durata) => {
  const b = build(durata);
  return {
    score_version: 1,
    duration_sec: durata,
    fade_in_sec: FADE_IN,
    fade_out_sec: FADE_OUT,
    layers: b.layers,
    phases: b.phases,
  };
};

/* le due esperienze: la scheda cita il registro, lo score è il loro */
const daEsperienza = (id, extra) => {
  const e = ESPERIENZE[id];
  return {
    id: e.id,
    titolo: e.titolo,
    sottotitolo: e.sottotitolo,
    racconto: e.racconto,
    cuffie_testo: e.cuffie,
    durata_sec: e.durata,
    origine: 'benessere',
    evidenza: {
      grado: null,
      nota: 'Esperienza progettata e misurata al banco Aurya: '
        + 'un ascolto strutturato, senza pretese di effetto oltre '
        + "l'ascolto stesso.",
      revisione: '2026-08',
    },
    stato: 'attivo',
    versione: 1,
    costruisci: () => e.costruisci(e.durata),
    ...extra,
  };
};

/* i sei per intento: scheda nostra, ricetta e nota di evidenza LORO */
const daIntento = (nome, extra) => {
  const p = PROTOCOLLI[nome];
  const durata = (p.durataMin || 20) * 60;
  return {
    id: p.intent,
    titolo: nome,
    origine: 'letteratura',
    evidenza: { grado: p.grade, nota: p.ev, revisione: '2026-08' },
    durata_sec: durata,
    stato: 'attivo',
    versione: 1,
    costruisci: () => scoreIntento(p.build, durata),
    ...extra,
  };
};

export const CATALOGO = Object.freeze([
  daEsperienza('calm', {
    livello: 'base',
    racconto: 'Sei minuti per aprire uno spazio: un fondo caldo che '
      + 'rallenta, un respiro sonoro che si allarga e, in cuffia, un '
      + 'battito lento che accompagna. È la soglia che molti operatori '
      + 'usano fra l’arrivo e il lavoro, o fra il lavoro e il ritorno '
      + 'al mondo.',
    indicazioni: 'Sei minuti per creare uno spazio di calma, in '
      + 'qualsiasi momento della giornata.',
    come: 'In cassa o in cuffia, a volume moderato. La persona seduta '
      + 'o distesa; tu presente, senza dover fare nulla: il suono '
      + 'tiene lo spazio.',
    teoria: 'Progettazione psicoacustica su un arco di distensione '
      + '(intensità e ritmo decrescenti); il battito lento in cuffia '
      + 'si appoggia all’entrainment uditivo. Misurata al banco Aurya.',
    cuffie: 'consigliate',
  }),
  daEsperienza('respiro', {
    livello: 'base',
    evidenza: {
      grado: 'A',
      nota: 'È la scheda con le basi più solide del catalogo, e per '
        + 'una ragione precisa: qui la pratica documentata non è '
        + '«ascoltare un suono», è RESPIRARE a un certo ritmo. La '
        + 'respirazione di risonanza (~6 atti al minuto, con '
        + 'espirazione più lunga dell’inspirazione) è la pratica con '
        + 'la letteratura più robusta di tutto questo campo, e un '
        + 'RCT del 2026 ha mostrato che il ritmo fisso a 6 vale '
        + 'quanto quello misurato persona per persona. Il suono qui '
        + 'fa una cosa sola, e la fa con precisione: dà il tempo.',
      revisione: '2026-08',
    },
    teoria: 'Respirazione di risonanza (Lehrer, Gevirtz): a circa sei '
      + 'atti al minuto la variabilità cardiaca raggiunge la sua '
      + 'ampiezza massima. Rapporto 4:6 fra inspirazione ed '
      + 'espirazione, come raccomandato. Il suono è un pacer: '
      + 'l’altezza sale e scende col respiro e un tocco segna ogni '
      + 'svolta, le convenzioni dei pacer uditivi studiati.',
    indicazioni: 'Dieci minuti di respirazione guidata: la pratica '
      + 'più «attiva» del catalogo, e la più facile da riportare a '
      + 'casa. Ottima come apertura o come lavoro a sé.',
    come: 'In cuffia o in cassa, indifferentemente: la guida è una '
      + 'nota, non un battito fra le orecchie. Persona seduta con la '
      + 'schiena dritta, o distesa. Dille solo: «segui il suono, non '
      + 'contare». Se all’inizio il ritmo sembra lento, è normale: '
      + 'sei atti al minuto sono meno di quanto si respiri di solito.',
    cuffie: 'consigliate',
  }),
  daEsperienza('ground', {
    livello: 'base',
    racconto: 'Un registro basso che si sente prima nel corpo che '
      + 'nelle orecchie, una materia sonora che va e viene come una '
      + 'marea, una pulsazione che rallenta. Verso la fine tutto si '
      + 'semplifica: resta il peso, e il peso è il punto. Progettata '
      + 'e misurata al banco Aurya, frequenza per frequenza.',
    indicazioni: 'Otto minuti per ritrovare peso e presenza, '
      + 'anche come chiusura di un lavoro corporeo.',
    come: 'Meglio un buon diffusore che scenda nei bassi, oppure '
      + 'cuffie. Persona distesa, luce bassa. Ottima come chiusura di '
      + 'un lavoro corporeo.',
    teoria: 'Psicoacustica delle basse frequenze, il suono grave è '
      + 'percezione anche corporea, non solo uditiva, nella scia '
      + 'della tradizione vibroacustica. Arco progettato e misurato '
      + 'al banco Aurya.',
    cuffie: 'consigliate',
  }),
  daIntento('Rilassare', {
    livello: 'base',
    evidenza: {
      grado: 'B',
      nota: 'Le review sulla stimolazione uditiva ritmica documentano '
        + 'effetti reali sull’ansia di stato e sul rilassamento, da '
        + 'piccoli a moderati, già dopo circa dieci minuti di ascolto. '
        + 'È l’uso meglio documentato di questa famiglia di suoni, e '
        + 'questa scheda ci sta dentro per intero: stato stabile, '
        + 'nessuna discesa, nessun rientro necessario.',
      revisione: '2026-08',
    },
    teoria: 'Entrainment uditivo (battiti binaurali): il cervello '
      + 'segue in modo misurabile una stimolazione ritmica, la '
      + 'risposta uditiva stazionaria (ASSR) è neurofisiologia '
      + 'consolidata. Review: Garcia-Argibay et al. 2019; Chaieb '
      + 'et al. 2015.',
    sottotitolo: 'Uno stato stabile, senza discese e senza rientri.',
    racconto: 'L’uso meglio documentato dell’intero catalogo: un '
      + 'battito binaurale che si stabilizza e ci resta, senza discese '
      + 'e senza sorprese. Non promette stati speciali: offre venti '
      + 'minuti stabili in cui il sistema può fare da sé.',
    indicazioni: 'Per un momento di distensione. Funziona anche su '
      + 'ascolti brevi.',
    come: 'Solo in cuffia: il battito binaurale nasce nel confronto '
      + 'fra le due orecchie, dalle casse resta un tono. Qualsiasi '
      + 'cuffia stereo decente va bene.',
    cuffie: 'necessarie',
    cuffie_testo: 'Il battito binaurale esiste solo in cuffia: senza, '
      + 'resta un tono semplice.',
  }),
  daIntento('Dormire', {
    livello: 'base',
    evidenza: {
      grado: 'B',
      nota: 'Le review documentano un accompagnamento reale al '
        + 'rilassamento pre-sonno (effetti da piccoli a moderati). Il '
        + 'confine, detto da professionisti: per l’insonnia clinica la '
        + 'via d’elezione è la CBT-I, questo protocollo la affianca, '
        + 'non la sostituisce.',
      revisione: '2026-08',
    },
    teoria: 'Entrainment uditivo verso ritmi lenti, sull’arco dei '
      + 'protocolli di induzione descritti in letteratura.',
    sottotitolo: 'Una discesa in tre tempi verso il pre-sonno.',
    racconto: 'Un arco che scende in tre tempi: la quiete '
      + 'dell’ingresso, la discesa, e un soffio che resta quando i '
      + 'toni si ritirano. Accompagna il passaggio, non lo forza.',
    indicazioni: 'Per accompagnare il passaggio verso il sonno. '
      + 'Da ascoltare già distesi.',
    come: 'Serale: già a letto o sul lettino, luci basse. Cuffie '
      + 'comode o un diffusore vicino; volume più basso del solito.',
    cuffie: 'consigliate',
  }),
  daIntento('Meditare', {
    livello: 'base',
    evidenza: {
      grado: 'B',
      nota: 'L’arco alpha→theta è la struttura classica dei '
        + 'protocolli di induzione descritti in letteratura, e il '
        + 'theta è la banda più studiata. Effetti documentati e '
        + 'onesti: reali, di entità modesta, il valore sta '
        + 'nell’accompagnare una pratica che esiste già. Il rientro '
        + 'finale fa parte del protocollo.',
      revisione: '2026-08',
    },
    teoria: 'Entrainment uditivo (ASSR) su banda theta; pratica '
      + 'contemplativa assistita dal suono.',
    sottotitolo: 'Ingresso, profondità, e un rientro che riporta su.',
    racconto: 'L’arco classico dei protocolli di induzione: si '
      + 'scende, si resta, e alla fine si RISALE, il rientro fa '
      + 'parte della pratica, perché nessuno va lasciato in fondo. '
      + 'Per accompagnare una meditazione seduta, tua o guidata da te.',
    indicazioni: 'Per accompagnare una pratica meditativa seduta.',
    come: 'In cuffia (binaurale). La tua voce può guidare sopra il '
      + 'suono, se è la tua pratica: il protocollo le lascia spazio.',
    cuffie: 'necessarie',
    cuffie_testo: 'Il battito binaurale esiste solo in cuffia: senza, '
      + 'resta un tono semplice.',
  }),
  daIntento('Elaborare', {
    livello: 'attenzione',
    evidenza: {
      grado: 'C',
      nota: 'La stimolazione bilaterale alternata è un componente '
        + 'sonoro presente in protocolli clinici strutturati (contesto '
        + 'EMDR), ed è questo a renderla interessante per un lavoro '
        + 'accompagnato. Il confine è netto e professionale: quei '
        + 'protocolli sono condotti da terapeuti formati, e questo '
        + 'strumento non li sostituisce, accompagna, con te presente.',
      revisione: '2026-08',
    },
    teoria: 'Stimolazione bilaterale alternata, componente sonoro '
      + 'studiato nel contesto EMDR (Shapiro); qui come '
      + 'accompagnamento condotto, su fondo theta.',
    sottotitolo: 'Alternanza destra/sinistra su un fondo lento.',
    racconto: 'Un fondo lento e fermo, e un suono che passa da un '
      + 'orecchio all’altro, una volta al secondo. L’alternanza '
      + 'bilaterale compare in protocolli clinici condotti da '
      + 'professionisti formati: QUESTO strumento non li sostituisce, '
      + 'è un accompagnamento, e va condotto, mai lasciato da solo.',
    indicazioni: 'Per un lavoro interiore accompagnato, con qualcuno '
      + 'che guida. Non è uno strumento da lasciare da soli.',
    come: 'Solo in cuffia: l’alternanza è destra/sinistra. Tu '
      + 'presente per tutta la durata, è la scheda col livello '
      + '«attenzione», ed è un livello che va preso sul serio.',
    cuffie: 'necessarie',
    cuffie_testo: 'L’alternanza destra/sinistra esiste solo in cuffia.',
  }),
  daIntento('Concentrare', {
    livello: 'base',
    evidenza: {
      grado: 'C',
      nota: 'Sul piano dell’attivazione il ritmo beta/SMR fa il suo '
        + 'lavoro di sottofondo; sul potenziamento cognitivo vero e '
        + 'proprio gli studi sono contrastanti, con segnali negativi '
        + 'sui compiti complessi. Uso giusto: attivare, non potenziare.',
      revisione: '2026-08',
    },
    teoria: 'Entrainment su ritmi beta/SMR; letteratura sul '
      + 'potenziamento cognitivo contrastante, la scheda si usa per '
      + 'l’attivazione, dove regge.',
    sottotitolo: 'Una salita verso un ritmo attivo, che poi si assesta.',
    racconto: 'Sale, resta alto, si assesta: uno stato attivo voluto, '
      + 'senza rientro. Dove funziona bene lo diciamo, come '
      + 'sottofondo attivante su lavoro semplice e ripetitivo, e '
      + 'dove la letteratura è contrastante lo diciamo pure: è così '
      + 'che si usa uno strumento da professionisti.',
    indicazioni: 'Come sottofondo attivante su compiti semplici e '
      + 'ripetitivi. Da evitare sui compiti complessi.',
    come: 'In cuffia o in cassa, come sottofondo. Non per sessioni '
      + 'sul lettino: è uno stato attivo.',
    cuffie: 'consigliate',
  }),
  daIntento('Energizzare', {
    livello: 'base',
    evidenza: {
      grado: 'C',
      nota: 'La salita verso beta è attivazione documentata nel suo '
        + 'piccolo; il passaggio a 40 Hz tocca la frequenza con la '
        + 'letteratura più viva degli ultimi anni (risposta gamma/ASSR, '
        + 'con una linea di ricerca importante in corso). Qui è un '
        + 'accento breve, non una promessa: uno stato attivo offerto '
        + 'al momento giusto.',
      revisione: '2026-08',
    },
    teoria: 'Entrainment uditivo; il 40 Hz è la singola frequenza con '
      + 'la letteratura più attiva (gamma/ASSR, inclusi i lavori del '
      + 'MIT sulla stimolazione a 40 Hz).',
    sottotitolo: 'Una salita che finisce in alto, senza rientro.',
    racconto: 'Dal ritmo d’ingresso a uno stato attivo, con un breve '
      + 'passaggio a 40 Hz, la singola frequenza più studiata della '
      + 'letteratura recente. Finisce in alto, senza rientro: come un '
      + 'caffè sonoro, va offerto al momento giusto.',
    indicazioni: 'Per cominciare, o per riprendersi da un calo. '
      + 'Non a fine giornata.',
    come: 'In cuffia o in cassa, mattina o primo pomeriggio. '
      + 'Mai a fine giornata.',
    cuffie: 'consigliate',
  }),
]);

export const protocolloCore = (id) => CATALOGO.find((p) => p.id === id) || null;
