/**
 * CALM — la prima esperienza di Aurya Sound (STEP 8, 26/8/2026).
 *
 * Qui non c'e' un motore: c'e' una PORTA. La pagina chiede al motore
 * di casa (engine/synth.js) di suonare un protocollo scritto come
 * dati (content/calm.js), e per il resto tace.
 *
 *   esperienza (questa pagina) → protocollo (dati) → synth → ponte → audio
 *
 * Cio' che l'utente vede: un titolo, una riga, un pulsante. Durante
 * l'ascolto: quanto manca, e nient'altro. Nessun hertz, nessuna forma
 * d'onda, nessuna scelta tecnica — quelle stanno nel Laboratorio, che
 * e' lo strumento con cui NOI progettiamo queste esperienze.
 *
 * IL TEMPO DEL SUONO NON PASSA DA QUI. Ogni evoluzione (le rampe, le
 * finestre dei livelli, le dissolvenze) e' programmata dal motore
 * sull'AudioContext. L'orologio di questa pagina serve SOLO a
 * scrivere quanto manca: se si fermasse, il suono continuerebbe
 * identico.
 */
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import SoundTopbar from '../SoundTopbar';
import { SafetyLine, useSafetyGate } from '../SafetyCurtain';
import { startPreview } from '../engine/synth';
import { creaPonte } from '../engine/ponte';
import { schermoAcceso, schermoLibero, sorvegliaContesto } from '../engine/veglia';
import { costruisciCalm, CALM_DURATA } from '../content/calm';
import '../frequenze.css';
import './calm.css';

const mmss = (s) => {
  const t = Math.max(0, Math.round(s));
  return `${Math.floor(t / 60)}:${String(t % 60).padStart(2, '0')}`;
};

export default function CalmPage() {
  useEffect(() => {
    document.title = 'CALM — una breve esperienza sonora | Aurya Sound';
  }, []);

  const [stato, setStato] = useState('pronto');    // pronto | ascolto | fine
  const [trascorso, setTrascorso] = useState(0);
  const ctxRef = useRef(null);
  const liveRef = useRef(null);
  const orologio = useRef(null);
  const { guard, curtain, openReview } = useSafetyGate();

  /* Il congedo: si chiude tutto con l'ordine giusto — prima il
     motore (che ha la sua discesa morbida), poi lo schermo, poi il
     ponte. `dolce` distingue la fine naturale dall'interruzione. */
  const chiudi = useCallback((dolce) => {
    clearInterval(orologio.current); orologio.current = null;
    if (liveRef.current) { liveRef.current.stop(); liveRef.current = null; }
    schermoLibero();
    try { ctxRef.current?._fqzPonte?.rilascia(); } catch { /* niente */ }
    setStato(dolce ? 'fine' : 'pronto');
    if (!dolce) setTrascorso(0);
  }, []);

  /* smontando la pagina non resta niente acceso */
  useEffect(() => () => {
    clearInterval(orologio.current);
    try { liveRef.current?.stop(); } catch { /* niente */ }
    schermoLibero();
    try { ctxRef.current?.close(); } catch { /* niente */ }
  }, []);

  const avvia = async () => {
    if (stato === 'ascolto') return;
    const Ctx = window.AudioContext || window.webkitAudioContext;
    if (!ctxRef.current) ctxRef.current = new Ctx();
    const ctx = ctxRef.current;
    /* il canale-musica va aperto NEL GESTO: e' l'unico che iPhone non
       azzera (engine/ponte.js) */
    const ponte = creaPonte(ctx);
    ponte.avvia();
    await ctx.resume();
    /* sei minuti a occhi chiusi: lo schermo non deve spegnersi, o il
       suono se ne va con lui */
    schermoAcceso();
    sorvegliaContesto(ctx, () => chiudi(false));

    const score = costruisciCalm();
    liveRef.current = startPreview(ctx, score, { sbocco: ponte.nodo });
    setStato('ascolto');
    setTrascorso(0);
    /* SOLO PER SCRIVERE QUANTO MANCA: il suono e' gia' tutto
       programmato sull'AudioContext e non dipende da questo battito. */
    orologio.current = setInterval(() => {
      const t = liveRef.current ? liveRef.current.elapsed() : 0;
      if (t >= CALM_DURATA) { chiudi(true); return; }
      setTrascorso(Math.max(0, t));
    }, 250);
  };

  const avviaGuardato = guard(avvia);
  const quota = Math.min(1, trascorso / CALM_DURATA);

  return (
    <div className="fqz calm" data-testid="calm-page">
      <SoundTopbar firma="Sound" qui="/sound" />

      {stato === 'ascolto' ? (
        <main className="calm-ascolto" data-testid="calm-ascolto">
          <p className="calm-invito">Chiudi gli occhi, se puoi.</p>
          <div className="calm-barra" role="progressbar" aria-label="Avanzamento"
            aria-valuemin={0} aria-valuemax={CALM_DURATA}
            aria-valuenow={Math.round(trascorso)}
            aria-valuetext={`mancano ${mmss(CALM_DURATA - trascorso)}`}>
            <i style={{ transform: `scaleX(${quota})` }} />
          </div>
          <p className="calm-resta" data-testid="calm-resta">
            {mmss(CALM_DURATA - trascorso)}
          </p>
          <button type="button" className="calm-esci" data-testid="calm-termina"
            onClick={() => chiudi(false)}>Termina</button>
        </main>
      ) : (
        <main className="calm-porta">
          <h1>CALM</h1>
          {stato === 'fine' ? (
            <>
              <p className="calm-lead" data-testid="calm-fine" aria-live="polite">
                Fine. Resta ancora un momento, prima di tornare.
              </p>
              <button type="button" className="calm-inizia"
                data-testid="calm-ricomincia" onClick={avviaGuardato}>
                Ricomincia
              </button>
            </>
          ) : (
            <>
              <p className="calm-lead">
                Una breve esperienza sonora per creare uno spazio di calma.
              </p>
              <p className="calm-nota">
                Sei minuti. Un suono che rallenta, e ti lascia rallentare.
                Con le cuffie puoi percepire anche un battito lento fra i
                due canali; senza cuffie l'esperienza resta intera.
              </p>
              <button type="button" className="calm-inizia"
                data-testid="calm-inizia" onClick={avviaGuardato}>
                Inizia
              </button>
              <p className="calm-patto">
                Non è una terapia e non promette effetti: è un ascolto
                costruito con cura. Quello che il suono fa, e quello che
                non sappiamo, è raccontato{' '}
                <Link to="/sound/esplora">nella biblioteca</Link>.
              </p>
              <SafetyLine onOpen={openReview} />
            </>
          )}
        </main>
      )}

      {curtain}
      <footer className="fqzfoot">
        <a href="/sound">← Aurya Sound</a>
        <a href="/sound/esplora">La biblioteca</a>
        <a href="/meditazioni">Meditazioni</a>
      </footer>
    </div>
  );
}
