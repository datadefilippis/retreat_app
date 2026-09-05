/**
 * IL MOTORE DEL LAB (25/8/2026; due sorgenti dal 27/8, ciclo LB1) —
 * React-free, come prototipo.js.
 *
 * Un solo grafo per tutto il Laboratorio:
 *
 *   sorgente A ─ livello ─ pan ─┐
 *                               ├→ master ─┬→ analyser (osservatore)
 *   sorgente B ─ livello ─ pan ─┘          └→ ponte.nodo → <audio>
 *
 * Tre regole ereditate dal resto del motore, pagate in produzione:
 *
 * 1. Il suono esce SOLO dal ponte (engine/ponte.js): su iOS il grafo
 *    collegato a ctx.destination e' suono «di contorno», azzerabile
 *    dal silenziatore. MAI connect(ctx.destination) in questo file.
 * 2. L'analisi e' un ospite: guarda, non trasporta (visual/analisi.js).
 *    `analisi.sorgente(nodo)` accetta QUALSIASI nodo — oggi il mix
 *    delle sorgenti, domani un MediaStreamSource dal microfono: e' la
 *    presa per tutto il futuro del Lab, e i moduli che leggono
 *    l'analyser non sapranno mai da dove viene il segnale.
 * 3. Nessun parametro salta: ampiezza e frequenza si muovono con
 *    rampe (DK = 12 ms, la costante di casa), il cambio di forma o di
 *    fase e' un CROSSFADE fra due oscillatori — cambiare `type` a
 *    caldo produce un click.
 *
 * LB1 — LA SECONDA SORGENTE. Le due voci sono GEMELLE: la stessa
 * fabbrica (creaSorgente) le costruisce entrambe, quindi la A si
 * comporta al bit come prima e la B non puo' divergere. Ognuna ha il
 * suo livello (ampiezza + declick), il suo pan («dove suona»:
 * entrambe le orecchie, solo sinistra, solo destra — e' cosi' che
 * l'interferenza e il binaurale da banco diventano un gesto) e un
 * rubinetto privato per il modo XY dell'oscilloscopio (le figure di
 * Lissajous vogliono i DUE segnali separati, il mix non basta).
 * Il ponte si rilascia solo quando TUTTE le voci tacciono.
 *
 * LA FASE. L'OscillatorNode nativo non ce l'ha: si ottiene con
 * setPeriodicWave. La serie di Fourier della forma, con ogni armonica
 * ruotata di k·fase, da' esattamente sin(k(ωt+φ)) — e siccome la
 * PeriodicWave e' band-limitata dal browser, e' pure anti-aliasata.
 * A fase 0 si usano i tipi nativi (purezza massima, zero calcoli).
 */
import { creaPonte } from '../engine/ponte';
import { liberaTutto } from '../../../lib/contestiAudio';

const DK = 0.012;           // declick: nessun salto piu' rapido di 12 ms
const XFADE = 0.024;        // crossfade cambio forma/fase
const ARMONICHE = 512;      // fino a ~20 kHz gia' da un fondamentale di 40 Hz

export const FORME = ['sine', 'square', 'triangle', 'sawtooth'];
export const ORECCHIE = ['entrambe', 'sinistra', 'destra'];
const CANALI = { entrambe: [1, 1], sinistra: [1, 0], destra: [0, 1] };

/* Coefficiente b_k della serie di Fourier (seno) della forma.
   Le stesse serie delle forme native — la normalizzazione del
   browser riporta il picco a 1, quindi il volume non cambia
   passando da nativa a PeriodicWave. */
function coeff(forma, k) {
  switch (forma) {
    case 'sine': return k === 1 ? 1 : 0;
    case 'square': return k % 2 ? 4 / (k * Math.PI) : 0;
    case 'sawtooth': return (2 / (k * Math.PI)) * (k % 2 ? 1 : -1);
    case 'triangle':
      return k % 2 ? (8 / (Math.PI * Math.PI * k * k)) * ((k % 4 === 1) ? 1 : -1) : 0;
    default: return 0;
  }
}

/* PeriodicWave della forma ruotata di `fase` radianti (sul
   fondamentale): real[k] = b_k·sin(k·fase), imag[k] = b_k·cos(k·fase). */
function ondaConFase(ctx, forma, fase) {
  const real = new Float32Array(ARMONICHE + 1);
  const imag = new Float32Array(ARMONICHE + 1);
  for (let k = 1; k <= ARMONICHE; k++) {
    const b = coeff(forma, k);
    if (!b) continue;
    real[k] = b * Math.sin(k * fase);
    imag[k] = b * Math.cos(k * fase);
  }
  return ctx.createPeriodicWave(real, imag);
}

export function creaLaboratorio(ctx) {
  if (ctx._fqzLab) return ctx._fqzLab;
  const ponte = creaPonte(ctx);
  const nyquist = ctx.sampleRate / 2;          // il limite VERO, non 20 kHz
  const clampF = (f) => Math.min(Math.max(+f || 1, 1), nyquist * 0.995);

  /* ── il rubinetto d'analisi ─────────────────────────────────── */
  const analyser = ctx.createAnalyser();
  analyser.fftSize = 8192;                     // ~5.4 Hz/bin a 44.1k
  analyser.smoothingTimeConstant = 0.55;

  /* ── l'uscita del banco: il MIX delle sorgenti ──────────────── */
  const master = ctx.createGain();
  master.gain.value = 1;                       // il volume vive nelle voci
  master.connect(analyser);                    // osserva
  master.connect(ponte.nodo);                  // trasporta — MAI ctx.destination

  let osservato = master;                      // cio' che l'analyser guarda ora

  /* LB4 — L'INGRESSO: la presa per i suonatori di banco (la campana
     rifatta della fonderia, il playback dell'originale nell'A/B).
     Entra nel master, quindi rispetta la regola del ponte e viene
     osservato dall'analyser come tutto il resto. */
  const ingresso = ctx.createGain();
  ingresso.gain.value = 1;
  ingresso.connect(master);

  /* onde con fase gia' calcolate: (forma, fase arrotondata) → wave.
     La cache e' del banco: le due sorgenti la condividono. */
  const cache = new Map();
  const onda = (forma, fase) => {
    const chiave = forma + '@' + Math.round(fase * 1000);
    if (!cache.has(chiave)) {
      if (cache.size > 128) cache.clear();   // il phase-lock ne conia di nuove
      cache.set(chiave, ondaConFase(ctx, forma, fase));
    }
    return cache.get(chiave);
  };

  /* il ponte si apre col primo suono e si chiude con l'ultimo:
     su iOS un <audio> lasciato in play su uno stream muto ripete
     l'ultimo buffer in loop (22/8) */
  const sorgenti = [];
  const qualcunoSuona = () => sorgenti.some((s) => s._attivo());
  let mic = null;                              // { stream, nodo } dell'orecchio

  /* ═══ LA FABBRICA DELLE SORGENTI (LB1) ═══
     Una macchina sola per la A e la B: stato, voce, corsa (sweep),
     livello (ampiezza+declick), pan, e il rubinetto XY. */
  function creaSorgente() {
    const stato = { forma: 'sine', freq: 440, amp: 0.25, fase: 0,
                    attivo: false, orecchio: 'entrambe' };
    let voce = null;                           // { osc, gain } vivo
    let corsa = null;                          // promemoria dello sweep

    const livello = ctx.createGain();          // ampiezza + declick della voce
    livello.gain.value = 0;
    /* «Dove suona» e' un INTERRUTTORE di canale, non un pan: lo
       StereoPanner a potenza costante toglieva 3 dB al centro
       (misurato: ampiezza 25% → picco 0,177) e lo strumento mentiva
       sull'ampiezza. Due guadagni espliciti L/R tengono il livello
       onesto: al centro 1 e 1, di lato 1 e 0. */
    const gL = ctx.createGain(); const gR = ctx.createGain();
    gL.gain.value = 1; gR.gain.value = 1;
    const unione = ctx.createChannelMerger(2);
    livello.connect(gL); livello.connect(gR);
    gL.connect(unione, 0, 0); gR.connect(unione, 0, 1);
    unione.connect(master);

    /* il rubinetto privato del modo XY: legge QUESTA voce, prima del
       pan — le figure di Lissajous vogliono i segnali separati */
    const tap = ctx.createAnalyser();
    tap.fftSize = 2048;
    livello.connect(tap);

    const freqOra = () => {
      if (!corsa) return stato.freq;
      const u = (ctx.currentTime - corsa.t0) / corsa.durata;
      if (u >= 1) { const fine = corsa.a; corsa = null; return fine; }
      if (u <= 0) return corsa.da;
      return corsa.da * Math.pow(corsa.a / corsa.da, u);
    };

    /* IL PHASE-LOCK (LB1, misurato al collaudo): due oscillatori
       partono in istanti diversi, quindi «fase 180°» sarebbe 180°
       rispetto a un riferimento CASUALE — la cancellazione prometteva
       e non manteneva (RMS giu' di 4:1 invece che a zero). La cura:
       ogni voce nasce a un istante PROGRAMMATO (osc.start(tS)) e la
       sua onda viene ruotata di 2π·f·tS in piu', cosi' la fase di
       TUTTE le voci e' riferita all'origine del contesto (t=0).
       A pari frequenza, 180° significa davvero opposizione.
       Il lock vale finche' la frequenza non scivola (slider, sweep):
       basta ridare un tocco alla fase per riallineare — la voce si
       ricrea e si riaggancia. */
    const DUE_PI = 2 * Math.PI;
    const vesti = (osc, faseEff) => {
      const f = ((faseEff % DUE_PI) + DUE_PI) % DUE_PI;
      if (f < 1e-4 || DUE_PI - f < 1e-4) osc.type = stato.forma;
      else osc.setPeriodicWave(onda(stato.forma, f));
    };

    const nuovaVoce = (guadagno) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      /* la voce nuova nasce DOVE SIAMO, non alla meta: se una corsa e'
         in atto (cambio di forma a meta' sweep) eredita il pezzo di
         rampa che resta, altrimenti si perderebbe lo sweep. */
      const ora = freqOra();
      const tS = ctx.currentTime + 0.006;      // partenza programmata
      vesti(osc, stato.fase + DUE_PI * ora * tS);
      osc.frequency.value = ora;
      if (corsa) {
        const resta = corsa.t0 + corsa.durata - tS;
        if (resta > 0) {
          osc.frequency.setValueAtTime(ora, tS);
          osc.frequency.exponentialRampToValueAtTime(corsa.a, tS + resta);
        }
      }
      gain.gain.value = guadagno;
      osc.connect(gain); gain.connect(livello);
      osc.start(tS);
      return { osc, gain };
    };

    /* cambio forma o fase a caldo: la voce vecchia scende, la nuova
       sale, si incrociano in XFADE — l'orecchio sente una sola nota */
    const rimpiazza = () => {
      if (!voce) return;
      const via = voce, t = ctx.currentTime;
      voce = nuovaVoce(0);
      voce.gain.gain.linearRampToValueAtTime(1, t + XFADE);
      via.gain.gain.setValueAtTime(1, t);
      via.gain.gain.linearRampToValueAtTime(0, t + XFADE);
      via.osc.stop(t + XFADE + 0.05);
      via.osc.onended = () => { try { via.gain.disconnect(); } catch { /* gia' */ } };
    };

    const api = {
      /* `freq` e' la frequenza che suona ADESSO (durante una corsa si
         muove); `meta` e' dove sta andando; `corsa` e' il promemoria
         della rampa, o null se non c'e'. */
      stato: () => ({ ...stato, freq: freqOra(), meta: stato.freq,
                      corsa: corsa ? { ...corsa } : null }),

      imposta(patch = {}) {
        const t = ctx.currentTime;
        if (patch.freq !== undefined) {
          /* CON `secondi` e' una corsa, SENZA e' il gesto di sempre —
             il comportamento vecchio non cambia di una virgola. */
          const secondi = Math.max(0, +patch.secondi || 0);
          const partenza = freqOra();          // dove siamo davvero ora
          stato.freq = clampF(patch.freq);
          if (voce) {
            const p = voce.osc.frequency;
            /* cancellare basta a interrompere: non ci sono timer da
               spegnere ne' animazioni da rincorrere, perche' non ce
               n'e' mai stato uno */
            p.cancelScheduledValues(t);
            if (secondi > 0) {
              p.setValueAtTime(partenza, t);
              p.exponentialRampToValueAtTime(stato.freq, t + secondi);
              corsa = { da: partenza, a: stato.freq, t0: t, durata: secondi };
            } else {
              /* setTargetAtTime: scivola senza zipper, qualunque sia
                 il passo del controllo */
              p.setTargetAtTime(stato.freq, t, DK / 3);
              corsa = null;
            }
          } else corsa = null;                 // a motore spento non si corre
        }
        if (patch.amp !== undefined) {
          stato.amp = Math.min(Math.max(+patch.amp || 0, 0), 1);
          if (stato.attivo) {
            livello.gain.cancelScheduledValues(t);
            livello.gain.setTargetAtTime(stato.amp, t, DK / 3);
          }
        }
        if (patch.orecchio !== undefined && ORECCHIE.includes(patch.orecchio)
            && patch.orecchio !== stato.orecchio) {
          stato.orecchio = patch.orecchio;
          const [vL, vR] = CANALI[stato.orecchio];
          gL.gain.setTargetAtTime(vL, t, DK / 3);
          gR.gain.setTargetAtTime(vR, t, DK / 3);
        }
        let rifare = false;
        if (patch.forma !== undefined && FORME.includes(patch.forma)
            && patch.forma !== stato.forma) { stato.forma = patch.forma; rifare = true; }
        if (patch.fase !== undefined) {
          const f = +patch.fase || 0;
          if (f !== stato.fase) { stato.fase = f; rifare = true; }
        }
        if (rifare && voce) rimpiazza();
      },

      /* da chiamare DENTRO il gesto (clic/tocco): il ponte e il
         resume del contesto vogliono l'attivazione dell'utente */
      async avvia() {
        if (stato.attivo) return;
        try { await ctx.resume(); } catch { /* gia' attivo */ }
        await ponte.avvia();
        voce = nuovaVoce(1);
        const t = ctx.currentTime;
        livello.gain.cancelScheduledValues(t);
        livello.gain.setValueAtTime(0, t);
        livello.gain.linearRampToValueAtTime(stato.amp, t + DK);
        stato.attivo = true;
      },

      ferma() {
        if (!stato.attivo) return;
        /* SI SPEGNE DOVE SIAMO. Prima si azzerava la corsa e basta:
           `stato.freq` restava la META, cosi' fermare uno sweep a
           1092 Hz faceva dire allo stato «100» — una frequenza mai
           suonata — e alla ripartenza il generatore attaccava di li'.
           Fissare la frequenza corrente PRIMA di chiudere la corsa
           tiene lo stato onesto. */
        stato.freq = freqOra();
        corsa = null;
        const t = ctx.currentTime;
        livello.gain.cancelScheduledValues(t);
        livello.gain.setValueAtTime(livello.gain.value, t);
        livello.gain.linearRampToValueAtTime(0, t + DK);
        if (voce) {
          voce.osc.stop(t + DK + 0.05);
          const via = voce;
          via.osc.onended = () => { try { via.gain.disconnect(); } catch { /* gia' */ } };
          voce = null;
        }
        stato.attivo = false;
        /* l'ultima voce che tace chiude il ponte */
        if (!qualcunoSuona()) ponte.rilascia();
      },

      /* il rubinetto XY: i campioni di QUESTA voce, per Lissajous */
      tempo(buf) { tap.getFloatTimeDomainData(buf); return buf; },

      _attivo: () => stato.attivo,
      _stacca() { try { livello.disconnect(); unione.disconnect(); } catch { /* via */ } },
    };
    sorgenti.push(api);
    return api;
  }

  const lab = {
    ctx,
    ponte,
    ingresso,
    limiti: { min: 1, max: nyquist },

    /* la voce A, l'interfaccia di sempre, non cambia di una virgola */
    generatore: creaSorgente(),
    /* la voce B (LB1), gemella: stessa fabbrica, stessi gesti */
    generatore2: creaSorgente(),

    /* ═══ L'ORECCHIO (LB2) — il microfono entra nel banco ═══
       Il mic e' un OSSERVATO, mai una sorgente sonora: si collega
       all'analyser via `analisi.sorgente(...)` e BASTA — nessuna via
       verso master o ponte, quindi niente feedback e niente audio che
       lascia il dispositivo. I filtri «da videochiamata» del browser
       si spengono: mangerebbero code di risonanza, parziali acuti e
       dinamica — esattamente cio' che il Lab vuole misurare. */
    orecchio: {
      attivo: () => !!mic,
      /* LM2 (5/9): il nodo del mic, per chi deve RIMETTERLO sotto
         l'analyser dopo averlo spostato sul master (l'A/B del
         Ritratto). Sola lettura: nessuna via nuova per il suono. */
      nodo: () => (mic ? mic.nodo : null),
      async apri() {
        if (mic) return;
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
          /* niente API: capita nei browser DENTRO le app (Instagram,
             Facebook) e nei contesti non sicuri. Il nome viaggia
             fino alla UI, che dira' la cura giusta. */
          const e = new Error('senza-mic');
          e.name = 'ApiMancante';
          throw e;
        }
        /* Il caso del telefono (founder 30/8): i tre filtri spenti
           sono la RICHIESTA giusta per misurare, ma se un dispositivo
           la rifiuta (vincoli non soddisfabili, stack audio strano)
           non deve morire tutto il microfono: si ritenta LISCIO
           (audio: true) e si annota che i filtri potrebbero essere
           accesi. Meglio una misura con l'asterisco che nessuna. */
        /* IL TERZO COLPEVOLE — LA CATEGORIA DELLA SESSIONE (referto
           del founder, 30/8 notte: «AudioSession category is not
           compatible with audio capture»): su iOS una pagina col
           motore audio in RIPRODUZIONE blocca la cattura — e noi il
           context lo creiamo sempre prima del microfono. Cura in
           due gradini: (1) si SOSPENDE il context prima del
           permesso, cosi' la categoria si libera; (2) se non basta,
           si CHIUDE e si chiede la rinascita col mic vivo — il lab
           nuovo nasce in PlayAndRecord e riproduzione e cattura
           convivono. */
        /* LA SERRATURA ERAVAMO NOI (indagine profonda 31/8, dopo
           quattro tentativi): il PONTE (22/8, meditazioni mute su
           iPhone) dichiara navigator.audioSession.type='playback' —
           e quella dichiarazione BLOCCA la sessione della pagina in
           sola-riproduzione: iOS risponde «AudioSession category is
           not compatible with audio capture» a qualunque richiesta
           di microfono, qualunque context si chiuda o sospenda. La
           cura e' l'altra faccia della stessa API: PRIMA del
           permesso si dichiara play-and-record (riproduzione E
           cattura convivono); chiudi() torna a playback, cosi' la
           garanzia del 22/8 resta intatta quando il mic non serve. */
        try {
          if (navigator.audioSession) {
            navigator.audioSession.type = 'play-and-record';
          }
        } catch { /* API assente: nessun blocco da sciogliere */ }
        const eraAttivo = ctx.state === 'running';
        if (eraAttivo) { try { await ctx.suspend(); } catch { /* pazienza */ } }
        /* IL QUARTO COLPEVOLE (referto «permesso-a-sessione-libera»,
           31/8): la SPA naviga senza ricaricare e i context delle
           ALTRE pagine (player, esplora, anteprima) restano vivi —
           su iOS uno solo in riproduzione tiene la sessione in
           playback e blocca la cattura OVUNQUE. Prima del permesso
           si libera l'audio dell'intera scheda: gli altri context si
           sospendono, i media si fermano. */
        try { await liberaTutto(ctx); } catch { /* best-effort */ }
        const chiedi = async () => {
          try {
            return await navigator.mediaDevices.getUserMedia({
              audio: {
                echoCancellation: false,
                noiseSuppression: false,
                autoGainControl: false,
              },
            });
          } catch (err) {
            if (err && (err.name === 'NotAllowedError'
                        || err.name === 'SecurityError')) {
              err.fase = 'permesso';
              throw err;
            }
            try {
              return await navigator.mediaDevices.getUserMedia({ audio: true });
            } catch (err2) {
              /* diagnosi remota: la FASE e il testo di WebKit
                 viaggiano fino alla UI — e' il referto */
              if (err2) err2.fase = 'permesso-liscio';
              throw err2;
            }
          }
        };
        let stream;
        try {
          stream = await chiedi();
        } catch (err) {
          if (err && err.name === 'InvalidStateError') {
            /* la sospensione non e' bastata: via il context, il
               permesso si richiede a sessione LIBERA, e il lab
               rinasce col mic gia' vivo.
               NB (31/8): close() e' ASINCRONO — senza await si
               chiedeva il microfono mentre iOS stava ancora
               smontando la sessione, che risultava ancora occupata
               e rifiutava di nuovo. Si aspetta la chiusura VERA, e
               un respiro perche' il sistema rilasci la categoria. */
            try { await ctx.close(); } catch { /* gia' */ }
            await new Promise((r) => setTimeout(r, 150));
            let s2;
            try {
              s2 = await navigator.mediaDevices.getUserMedia({ audio: true });
            } catch (err3) {
              if (err3) err3.fase = 'permesso-a-sessione-libera';
              throw err3;
            }
            const e2 = new Error('rinascita-mic');
            e2.name = 'RinascitaMic';
            e2.stream = s2;
            throw e2;
          }
          throw err;
        }
        if (eraAttivo) { try { await ctx.resume(); } catch { /* dopo */ } }
        try {
          try { await ctx.resume(); } catch { /* gia' attivo */ }
          const nodo = ctx.createMediaStreamSource(stream);
          mic = { stream, nodo };
          lab.analisi.sorgente(nodo);      // il banco ora guarda il mic
        } catch (err) {
          /* IL SECONDO COLPEVOLE DI iOS (founder 30/8 notte, stesso
             InvalidStateError anche a pagina fresca): su iPhone il
             context nasce alla frequenza dell'ALTOPARLANTE (44,1k)
             ma il microfono consegna 48k, e WebKit rifiuta
             createMediaStreamSource se le frequenze non coincidono.
             La cura canonica: si CHIUDE questo context e si chiede
             la RINASCITA col microfono gia' vivo — il context nuovo,
             nato in regime di cattura, adotta la frequenza giusta.
             Lo stream NON si spegne: e' il lasciapassare (il permesso
             gia' concesso) che il lab nuovo adottera'. */
          if (err && err.name === 'InvalidStateError') {
            try { ctx.close(); } catch { /* gia' */ }
            const e2 = new Error('rinascita-mic');
            e2.name = 'RinascitaMic';
            e2.stream = stream;
            e2.origine = err;
            throw e2;
          }
          if (err) err.fase = 'collegamento';
          /* ogni altro fallimento: lo stream va spento subito, o il
             telefono resta con la spia del microfono accesa a vuoto */
          stream.getTracks().forEach((t) => t.stop());
          throw err;
        }
      },
      /* la seconda meta' della rinascita: il lab NUOVO adotta lo
         stream gia' concesso, senza richiedere il permesso */
      async adottaStream(stream) {
        if (mic) return;
        try {
          try { await ctx.resume(); } catch { /* gia' attivo */ }
          const nodo = ctx.createMediaStreamSource(stream);
          mic = { stream, nodo };
          lab.analisi.sorgente(nodo);
        } catch (err) {
          if (err) {
            err.fase = 'adozione';
            /* il referto delle frequenze: la firma del mismatch iOS */
            try {
              const t = stream.getAudioTracks()[0];
              const st = t && t.getSettings ? t.getSettings() : {};
              err.dettaglio = `ctx ${ctx.sampleRate}Hz` +
                (st.sampleRate ? ` mic ${st.sampleRate}Hz` : '') +
                ` tracce ${stream.getAudioTracks().length}` +
                ` stato ${ctx.state}`;
            } catch { /* il referto non deve mai rompere */ }
          }
          stream.getTracks().forEach((t) => t.stop());
          throw err;
        }
      },
      chiudi() {
        if (!mic) return;
        mic.stream.getTracks().forEach((t) => t.stop());
        try { mic.nodo.disconnect(); } catch { /* gia' */ }
        mic = null;
        lab.analisi.sorgente(null);        // si torna al mix delle voci
        /* la sessione torna MUSICA: la garanzia del ponte (22/8) vale
           di nuovo appena il microfono non serve piu' */
        try {
          if (navigator.audioSession) {
            navigator.audioSession.type = 'playback';
          }
        } catch { /* niente */ }
      },
    },

    analisi: {
      analyser,
      tempo(buf) { analyser.getFloatTimeDomainData(buf); return buf; },
      spettro(buf) { analyser.getFloatFrequencyData(buf); return buf; },
      /* la presa del futuro: cambia CIO' CHE si osserva, non chi
         disegna. Il microfono sara' `sorgente(ctx.createMediaStreamSource(...))`
         e oscilloscopio/spettro non se ne accorgeranno. */
      sorgente(nodo) {
        try { osservato.disconnect(analyser); } catch { /* mai collegato */ }
        (nodo || master).connect(analyser);
        osservato = nodo || master;
      },
      hzPerBin: ctx.sampleRate / analyser.fftSize,

      /* LB3 — LA PRESA DI REGISTRAZIONE: cattura i campioni CRUDI di
         cio' che il banco sta guardando (il microfono se l'orecchio
         e' aperto, altrimenti il mix delle voci) — l'analyser tiene
         solo l'ultimo respiro (186 ms), il ritratto vuole secondi.
         ScriptProcessor: deprecato ma senza pari in semplicita', e
         per una cattura di pochi secondi e' lo strumento giusto (il
         worklet arrivera' se mai servira' in produzione). Il nodo ha
         bisogno di un'uscita per battere: la si manda nel master a
         guadagno ZERO — silenzio, non un percorso sonoro nuovo. */
      registra(secondi = 6) {
        const sr = ctx.sampleRate;
        const totale = Math.floor(Math.min(Math.max(+secondi || 6, 1), 12) * sr);
        return new Promise((risolvi, fallisci) => {
          let presi = 0;
          const campioni = new Float32Array(totale);
          const sp = ctx.createScriptProcessor(4096, 1, 1);
          const muto = ctx.createGain();
          muto.gain.value = 0;
          const fonte = osservato;
          const chiudi = () => {
            try { fonte.disconnect(sp); } catch { /* gia' */ }
            try { sp.disconnect(); muto.disconnect(); } catch { /* gia' */ }
          };
          sp.onaudioprocess = (e) => {
            const dentro = e.inputBuffer.getChannelData(0);
            const resta = totale - presi;
            campioni.set(resta >= dentro.length ? dentro
              : dentro.subarray(0, resta), presi);
            presi += Math.min(dentro.length, resta);
            if (presi >= totale) {
              chiudi();
              risolvi({ campioni, sampleRate: sr });
            }
          };
          try {
            fonte.connect(sp);
            sp.connect(muto); muto.connect(master);
          } catch (e) { chiudi(); fallisci(e); }
        });
      },
    },

    spegni() {
      lab.orecchio.chiudi();
      sorgenti.forEach((s) => { s.ferma(); s._stacca(); });
      try { master.disconnect(); } catch { /* niente */ }
      /* IL CASO DEL TELEFONO (founder 30/8, InvalidStateError su
         Safari E Brave = stesso WebKit): il context non veniva MAI
         chiuso — una stanza dopo l'altra li accumulava, e iOS oltre
         il suo limite (circa quattro) li UCCIDE. Il primo morto che
         incontra createMediaStreamSource risponde InvalidStateError.
         La stanza possiede il suo motore (LU): quando muore, chiude. */
      try { ctx.close(); } catch { /* gia' chiuso */ }
      delete ctx._fqzLab;
    },
  };

  ctx._fqzLab = lab;
  /* banco di prova: diagnosi dalla console (e dai collaudi) senza
     toccare React. Sola lettura, nessun segreto. */
  try { window.__fqzLab = lab; } catch { /* SSR/test */ }
  return lab;
}
