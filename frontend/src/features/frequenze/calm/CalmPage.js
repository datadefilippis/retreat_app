/**
 * CALM — la prima esperienza di Aurya Sound (STEP 8, 26/8/2026).
 *
 * Qui non c'e' un motore e, dal consolidamento, non c'e' nemmeno un
 * player: c'e' una PORTA. La pagina prende i suoi dati dal registro
 * delle esperienze, chiede all'ascolto condiviso di suonarli, e per
 * il resto tace.
 *
 *   registro (dati) → protocollo (dati) → ascolto condiviso → synth
 *                                              → ponte → audio
 *
 * Cio' che l'utente vede: un titolo, una riga, un pulsante. Durante
 * l'ascolto: quanto manca, e nient'altro. Nessun hertz, nessuna forma
 * d'onda, nessuna scelta tecnica — quelle stanno nel Laboratorio, che
 * e' lo strumento con cui NOI progettiamo queste esperienze.
 */
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import SoundTopbar from '../SoundTopbar';
import { SafetyLine, useSafetyGate } from '../SafetyCurtain';
import { esperienza } from '../content/esperienze';
import { creaAscolto } from '../esperienze/ascolto';
import '../frequenze.css';
import './calm.css';

const mmss = (s) => {
  const t = Math.max(0, Math.round(s));
  return `${Math.floor(t / 60)}:${String(t % 60).padStart(2, '0')}`;
};

export default function CalmPage() {
  const exp = esperienza('calm');
  useEffect(() => {
    document.title = `${exp.titolo} — una breve esperienza sonora | Aurya Sound`;
  }, [exp.titolo]);

  const [stato, setStato] = useState('pronto');    // pronto | ascolto | fine
  const [trascorso, setTrascorso] = useState(0);
  const [perso, setPerso] = useState(false);
  const ascoltoRef = useRef(null);
  const { guard, curtain, openReview } = useSafetyGate();

  /* lo score si costruisce una volta: e' dati, non cambia */
  const score = useMemo(() => exp.costruisci(exp.durata), [exp]);

  const ascolto = useCallback(() => {
    if (!ascoltoRef.current) {
      ascoltoRef.current = creaAscolto(score, {
        onTic: setTrascorso,
        onFine: () => { setStato('fine'); },
        /* schermo bloccato o contesto perso: si dice cos'e' successo,
           invece di lasciare un silenzio inspiegato */
        onPerso: () => { setStato('pronto'); setTrascorso(0); setPerso(true); },
      });
    }
    return ascoltoRef.current;
  }, [score]);

  /* smontando la pagina non resta niente acceso */
  useEffect(() => () => { ascoltoRef.current?.smonta(); }, []);

  const avvia = async () => {
    setPerso(false);
    setTrascorso(0);
    const a = ascolto();
    await a.avvia();
    setStato('ascolto');
  };
  const avviaGuardato = guard(avvia);

  const termina = () => {
    ascoltoRef.current?.ferma();
    setStato('pronto'); setTrascorso(0);
  };

  const quota = Math.min(1, trascorso / exp.durata);
  const avvisoCuffie = ascoltoRef.current?.avviso || null;

  return (
    <div className="fqz calm" data-testid="calm-page">
      <SoundTopbar firma="Sound" qui="/sound" />

      {stato === 'ascolto' ? (
        <main className="calm-ascolto" data-testid="calm-ascolto">
          <p className="calm-invito">Chiudi gli occhi, se puoi.</p>
          <div className="calm-barra" role="progressbar" aria-label="Avanzamento"
            aria-valuemin={0} aria-valuemax={exp.durata}
            aria-valuenow={Math.round(trascorso)}
            aria-valuetext={`mancano ${mmss(exp.durata - trascorso)}`}>
            <i style={{ transform: `scaleX(${quota})` }} />
          </div>
          <p className="calm-resta" data-testid="calm-resta">
            {mmss(exp.durata - trascorso)}
          </p>
          {/* la soglia e il testo li decide engine/altoparlante.js, la
              stessa regola del player degli operatori; la classe li
              mostra SOLO sui telefoni */}
          {avvisoCuffie && (
            <div className="cuffie-avviso solo-telefono-block"
              data-testid="calm-avviso-cuffie">🎧 {avvisoCuffie}</div>
          )}
          <button type="button" className="calm-esci" data-testid="calm-termina"
            onClick={termina}>Termina</button>
        </main>
      ) : (
        <main className="calm-porta">
          <h1>{exp.titolo}</h1>
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
              <p className="calm-lead">{exp.sottotitolo}</p>
              {perso && (
                <p className="calm-perso" data-testid="calm-perso" aria-live="polite">
                  L'ascolto si è interrotto: sul telefono il suono dal vivo
                  si ferma quando lo schermo si spegne.
                </p>
              )}
              <p className="calm-nota">
                {exp.racconto} Con le cuffie percepisci anche un battito
                lento fra i due canali. Le cuffie non sono obbligatorie,
                ma dall'altoparlante di un telefono i toni gravi si
                perdono: se puoi, usale.
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
