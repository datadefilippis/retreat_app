/**
 * L'ASCOLTO — il player condiviso delle esperienze integrate
 * (STEP 8 consolidamento, 26/8/2026).
 *
 * Non e' un motore e non e' un'astrazione nuova: e' la SEQUENZA che
 * CALM e il player degli operatori facevano ognuno per conto suo,
 * scritta una volta sola. L'audit l'ha trovata duplicata dodici gesti
 * su dodici — ed e' esattamente da li' che sono nati i due buchi di
 * CALM (l'avviso cuffie mancante e lo schermo bloccato): due copie
 * divergono sempre, e la copia nuova aveva perso dei pezzi.
 *
 * Non aggiunge nulla al motore. Usa le primitive di casa:
 *   engine/ponte.js       il canale «musica» (l'unico che iPhone non azzera)
 *   engine/veglia.js      lo schermo che non si spegne, e la sorveglianza
 *   engine/synth.js       startPreview: il suono
 *   engine/altoparlante.js  l'avviso cuffie, con la soglia di casa
 *
 * React-free, come il motore del Lab: chi lo usa e' una pagina, non il
 * contrario.
 *
 * UN SOLO OROLOGIO. Il battito di 250 ms serve a due cose che prima
 * erano separate: scrivere quanto manca e accorgersi della fine
 * naturale. Il SUONO non dipende da lui — e' gia' tutto programmato
 * sull'AudioContext dal motore: se questo orologio si fermasse,
 * l'esperienza continuerebbe identica fino in fondo.
 *
 * LO SCHERMO BLOCCATO, e il limite che non si aggira. I browser
 * mobili SOSPENDONO WebAudio quando lo schermo si blocca: e' una
 * regola loro. Il wake lock (veglia) tiene acceso lo schermo per
 * tutta l'esperienza ed e' la difesa giusta; se il sistema lo nega
 * (risparmio energetico) o se l'utente blocca a mano, il contesto
 * muore e `onPerso` lo dice — invece di lasciare l'utente davanti a
 * un silenzio inspiegato. L'unica vera cura sarebbe renderizzare
 * l'esperienza in un file prima di suonarla (engine/continuo.js,
 * AT3): costa l'attesa del render, e per un'esperienza che promette
 * di potersi fare ADESSO quel prezzo e' troppo alto. Resta la scelta
 * giusta per le sessioni lunghe degli operatori, dove infatti vive.
 */
import { startPreview } from '../engine/synth';
import { creaPonte } from '../engine/ponte';
import { schermoAcceso, schermoLibero, sorvegliaContesto } from '../engine/veglia';
import { avvisoCuffieScore } from '../engine/altoparlante';

const BATTITO_MS = 250;

/**
 * @param score  lo score dell'esperienza (dati)
 * @param onTic  (secondi) — quanto e' passato, per l'interfaccia
 * @param onFine ()        — l'esperienza e' arrivata in fondo da sola
 * @param onPerso ()       — il contesto audio e' morto (schermo bloccato)
 * @param analisi (M4, 26/8) — true per avere il RUBINETTO: un
 *        AnalyserNode inserito fra il motore e il ponte, per chi
 *        vuole DISEGNARE cio' che suona (le onde del rito
 *        professionale). Additivo per contratto: senza l'opzione non
 *        nasce nessun nodo e il percorso audio e' identico a prima —
 *        CALM e GROUND non passano di qui e non cambiano.
 */
export function creaAscolto(score, { onTic, onFine, onPerso, analisi } = {}) {
  const durata = score.duration_sec;
  /* la soglia dell'altoparlante del telefono NON si ricopia qui:
     la decide engine/altoparlante.js, come per il player pubblico */
  const avviso = avvisoCuffieScore(score);
  let ctx = null, live = null, tic = null, sonda = null;
  /* LA BANDIERINA DEL GESTO (P0, 26/8). `avvia()` aspetta il resume
     del contesto PRIMA di assegnare `live`: due tocchi rapidi — sul
     telefono capita — passavano entrambi la guardia e partivano DUE
     sessioni. La seconda sovrascriveva la prima, che restava a suonare
     senza che nessuno potesse piu' fermarla: «Termina» ne spegneva una
     e l'altra tornava udibile al riavvio, sovrapposta.
     MISURATO: dopo il doppio tocco il picco era 0,32 invece di 0,08.
     Qui la porta si chiude SUBITO, prima di ogni attesa. */
  let avviando = false;

  const spegni = () => {
    clearInterval(tic); tic = null;
    if (live) { live.stop(); live = null; }
    schermoLibero();
    /* il ponte si rilascia, non si chiude: la sua coda morbida deve
       uscire tutta (engine/ponte.js) */
    try { ctx?._fqzPonte?.rilascia(); } catch { /* niente */ }
  };

  return {
    avviso,
    durata,
    inAscolto: () => !!live,
    trascorso: () => (live ? Math.max(0, live.elapsed()) : 0),
    /* il rubinetto per i pittori: null finche' non si e' avviato,
       o se l'analisi non e' stata chiesta */
    analisi: () => sonda,

    /** Da chiamare DENTRO il gesto: contesto e ponte lo esigono. */
    async avvia() {
      if (live || avviando) return;
      avviando = true;
      try {
        const Ctx = window.AudioContext || window.webkitAudioContext;
        if (!ctx) ctx = new Ctx();
        const ponte = creaPonte(ctx);
        ponte.avvia();
        await ctx.resume();
        schermoAcceso();
        sorvegliaContesto(ctx, () => { spegni(); onPerso?.(); });
        /* il rubinetto: il suono ci passa ATTRAVERSO e arriva
           identico al ponte — l'analyser non colora, legge */
        if (analisi && !sonda) {
          sonda = ctx.createAnalyser();
          sonda.fftSize = 2048;
          sonda.smoothingTimeConstant = 0.85;
          sonda.connect(ponte.nodo);
        }
        live = startPreview(ctx, score, { sbocco: sonda || ponte.nodo });
        tic = setInterval(() => {
          if (!live) return;
          const t = Math.max(0, live.elapsed());
          if (t >= durata) { spegni(); onFine?.(); return; }
          onTic?.(t);
        }, BATTITO_MS);
      } finally {
        avviando = false;
      }
    },

    /** Interruzione voluta: il motore ha la sua discesa morbida. */
    ferma() { spegni(); },

    /** Uscendo dalla pagina non resta niente acceso. */
    smonta() {
      spegni();
      try { ctx?.close(); } catch { /* niente */ }
      ctx = null;
    },
  };
}
