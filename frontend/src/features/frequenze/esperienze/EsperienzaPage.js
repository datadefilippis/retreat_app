/**
 * LA PORTA DELLE ESPERIENZE (STEP 9, 26/8/2026).
 *
 * Una sola presentazione per tutte le esperienze integrate: era la
 * pagina di CALM, ed e' rimasta identica a vedersi — solo che ora i
 * testi li prende dal registro invece di averli scritti dentro. Con
 * la seconda esperienza (GROUND) duplicarla avrebbe voluto dire
 * ricreare esattamente la duplicazione che il consolidamento aveva
 * appena tolto.
 *
 * Qui non c'e' un motore e non c'e' un player: c'e' una PORTA. La
 * pagina prende i suoi dati dal registro, chiede all'ascolto
 * condiviso di suonarli, e per il resto tace.
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
import { prova } from '../../../lib/cerchio';
import { creaAscolto } from './ascolto';
import '../frequenze.css';
import './esperienza.css';

const mmss = (s) => {
  const t = Math.max(0, Math.round(s));
  return `${Math.floor(t / 60)}:${String(t % 60).padStart(2, '0')}`;
};

export default function EsperienzaPage({ id }) {
  const exp = esperienza(id);
  useEffect(() => {
    document.title = `${exp.titolo} — un'esperienza sonora | Aurya Sound`;
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
    <div className={`fqz esp esp-${exp.id}`} data-testid="esp-page">
      <SoundTopbar firma="Sound" qui="/sound" />

      {stato === 'ascolto' ? (
        <main className="esp-ascolto" data-testid="esp-ascolto">
          <p className="esp-invito">Chiudi gli occhi, se puoi.</p>
          <div className="esp-barra" role="progressbar" aria-label="Avanzamento"
            aria-valuemin={0} aria-valuemax={exp.durata}
            aria-valuenow={Math.round(trascorso)}
            aria-valuetext={`mancano ${mmss(exp.durata - trascorso)}`}>
            <i style={{ transform: `scaleX(${quota})` }} />
          </div>
          <p className="esp-resta" data-testid="esp-resta">
            {mmss(exp.durata - trascorso)}
          </p>
          {/* la soglia e il testo li decide engine/altoparlante.js, la
              stessa regola del player degli operatori; la classe li
              mostra SOLO sui telefoni */}
          {avvisoCuffie && (
            <div className="cuffie-avviso solo-telefono-block"
              data-testid="esp-avviso-cuffie">🎧 {avvisoCuffie}</div>
          )}
          <button type="button" className="esp-esci" data-testid="esp-termina"
            onClick={termina}>Termina</button>
        </main>
      ) : (
        <main className="esp-porta">
          <h1>{exp.titolo}</h1>
          {stato === 'fine' ? (
            <>
              <p className="esp-lead" data-testid="esp-fine" aria-live="polite">
                Fine. Resta ancora un momento, prima di tornare.
              </p>
              {/* L2 (26/8, sistema) — l'INVITO, non un muro: il
                  momento dopo un'esperienza e' quello di massima
                  benevolenza. Chi e' gia' nel cerchio (prova) non
                  riceve inviti a entrarci. */}
              {!prova() && (
                <p className="esp-lettera" data-testid="esp-invito-lettera">
                  Ti è rimasta addosso? Nel <Link to="/newsletter">Cerchio di Aurya</Link> trovi
                  le meditazioni riservate e, ogni due settimane, la Lettera.
                </p>
              )}
              <button type="button" className="esp-inizia"
                data-testid="esp-ricomincia" onClick={avviaGuardato}>
                Ricomincia
              </button>
            </>
          ) : (
            <>
              <p className="esp-lead">{exp.sottotitolo}</p>
              {/* quanto dura si sa PRIMA di entrare: chi arriva da un
                  link diretto non deve scoprirlo premendo Inizia */}
              <p className="esp-durata" data-testid="esp-durata">
                {Math.round(exp.durata / 60)} minuti
              </p>
              {perso && (
                <p className="esp-perso" data-testid="esp-perso" aria-live="polite">
                  L'ascolto si è interrotto: sul telefono il suono dal vivo
                  si ferma quando lo schermo si spegne.
                </p>
              )}
              <p className="esp-nota">{exp.racconto} {exp.cuffie}</p>
              <button type="button" className="esp-inizia"
                data-testid="esp-inizia" onClick={avviaGuardato}>
                Inizia
              </button>
              <p className="esp-patto">
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
