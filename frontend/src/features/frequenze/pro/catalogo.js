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
    indicazioni: 'Sei minuti per creare uno spazio di calma, in '
      + 'qualsiasi momento della giornata.',
    cuffie: 'consigliate',
  }),
  daEsperienza('ground', {
    livello: 'base',
    indicazioni: 'Otto minuti per ritrovare peso e presenza, '
      + 'anche come chiusura di un lavoro corporeo.',
    cuffie: 'consigliate',
  }),
  daIntento('Rilassare', {
    livello: 'base',
    sottotitolo: 'Uno stato stabile, senza discese e senza rientri.',
    racconto: 'Un ingresso breve, poi un ritmo che resta fermo per '
      + 'tutta la durata. È il protocollo con l’uso meglio '
      + 'supportato del catalogo.',
    indicazioni: 'Per un momento di distensione. Funziona anche su '
      + 'ascolti brevi.',
    cuffie: 'necessarie',
    cuffie_testo: 'Il battito binaurale esiste solo in cuffia: senza, '
      + 'resta un tono semplice.',
  }),
  daIntento('Dormire', {
    livello: 'base',
    sottotitolo: 'Una discesa in tre tempi verso il pre-sonno.',
    racconto: 'Un arco che scende: quiete, discesa, e un soffio che '
      + 'resta. Pensato per la fine della giornata.',
    indicazioni: 'Per accompagnare il passaggio verso il sonno. '
      + 'Da ascoltare già distesi.',
    cuffie: 'consigliate',
  }),
  daIntento('Meditare', {
    livello: 'base',
    sottotitolo: 'Ingresso, profondità, e un rientro che riporta su.',
    racconto: 'L’arco classico dei protocolli di induzione: si '
      + 'scende, si resta, e alla fine si torna — il rientro fa '
      + 'parte del protocollo, non è un’aggiunta.',
    indicazioni: 'Per accompagnare una pratica meditativa seduta.',
    cuffie: 'necessarie',
    cuffie_testo: 'Il battito binaurale esiste solo in cuffia: senza, '
      + 'resta un tono semplice.',
  }),
  daIntento('Elaborare', {
    livello: 'attenzione',
    sottotitolo: 'Alternanza destra/sinistra su un fondo lento.',
    racconto: 'Un fondo fermo e un suono che passa da un orecchio '
      + 'all’altro, una volta al secondo. La nota di evidenza dice '
      + 'chiaramente cosa questo strumento NON è.',
    indicazioni: 'Per un lavoro interiore accompagnato, con qualcuno '
      + 'che guida. Non è uno strumento da lasciare da soli.',
    cuffie: 'necessarie',
    cuffie_testo: 'L’alternanza destra/sinistra esiste solo in cuffia.',
  }),
  daIntento('Concentrare', {
    livello: 'base',
    sottotitolo: 'Una salita verso un ritmo attivo, che poi si assesta.',
    racconto: 'Sale e resta alto: uno stato attivo voluto, senza '
      + 'rientro. La nota di evidenza è la più severa del catalogo, '
      + 'ed è giusto leggerla.',
    indicazioni: 'Come sottofondo attivante su compiti semplici e '
      + 'ripetitivi. Da evitare sui compiti complessi.',
    cuffie: 'consigliate',
  }),
  daIntento('Energizzare', {
    livello: 'base',
    sottotitolo: 'Una salita che finisce in alto, senza rientro.',
    racconto: 'Dal ritmo di ingresso a uno stato attivo, con un '
      + 'breve picco a 40 Hz — la singola frequenza più studiata '
      + 'della letteratura.',
    indicazioni: 'Per cominciare, o per riprendersi da un calo. '
      + 'Non a fine giornata.',
    cuffie: 'consigliate',
  }),
]);

export const protocolloCore = (id) => CATALOGO.find((p) => p.id === id) || null;
