/**
 * L'ORECCHIO — il microfono nel Lab (LB2, 27/8/2026).
 *
 * Il raccolto dell'architettura ospite: aprire il microfono e' UN
 * cambio di sorgente (`analisi.sorgente(mic)`) — oscilloscopio,
 * spettro e spettrogramma leggono il mondo reale senza cambiare una
 * riga. Questo pannello aggiunge l'ACCORDATORE: la fondamentale in
 * tempo reale (autocorrelazione + vertice parabolico, la matematica
 * vive in accordatore.js), la nota piu' vicina e lo scarto in cents.
 *
 * La privacy e' un fatto di grafo, non una promessa: il nodo del mic
 * si collega SOLO all'analyser — nessuna via verso l'uscita, nessun
 * upload. Il suono non lascia il dispositivo.
 *
 * Il numero si aggiorna ~10 volte al secondo in coda al giro del
 * banco (il quadro e' l'unico che batte il tempo), e per non
 * tremolare si mostra la MEDIANA delle ultime 5 letture: un
 * accordatore che sfarfalla non si legge.
 */
import React, { useEffect, useRef, useState } from 'react';
import { iscrivi } from './quadro';
import { fondamentale } from './accordatore';
import { notaVicina } from './note';

export default function Orecchio({ ottieniLab, ottieniAnalisi }) {
  const [acceso, setAcceso] = useState(false);
  const [errore, setErrore] = useState(null);
  const [lettura, setLettura] = useState(null);   // {hz, nota, cents, chiarezza}
  const labRef = useRef(null);
  const bufRef = useRef(null);
  const ultime = useRef([]);                      // la mediana delle letture
  const ultimaVolta = useRef(0);

  const alterna = async () => {
    setErrore(null);
    const lab = ottieniLab();                     // nel gesto: iOS lo esige
    labRef.current = lab;
    if (acceso) {
      lab.orecchio.chiudi();
      setAcceso(false); setLettura(null); ultime.current = [];
      return;
    }
    try {
      await lab.orecchio.apri();
      setAcceso(true);
    } catch (e) {
      setErrore(e && e.name === 'NotAllowedError'
        ? 'Permesso negato: per ascoltare serve il consenso al microfono.'
        : 'Nessun microfono disponibile su questo dispositivo.');
    }
  };

  /* smontaggio = microfono chiuso, senza aspettare nessuno */
  useEffect(() => () => { labRef.current?.orecchio.chiudi(); }, []);

  useEffect(() => iscrivi(() => {
    const lab = labRef.current;
    if (!lab || !lab.orecchio.attivo()) return;
    const ora = performance.now();
    if (ora - ultimaVolta.current < 90) return;
    ultimaVolta.current = ora;

    const analisi = ottieniAnalisi();
    if (!analisi) return;
    const N = analisi.analyser.fftSize;
    if (!bufRef.current || bufRef.current.length !== N) {
      bufRef.current = new Float32Array(N);
    }
    analisi.tempo(bufRef.current);
    const f = fondamentale(bufRef.current, analisi.analyser.context.sampleRate);
    if (!f) {
      if (ultime.current.length) { ultime.current = []; setLettura(null); }
      return;
    }
    ultime.current.push(f.hz);
    if (ultime.current.length > 5) ultime.current.shift();
    const ordinate = [...ultime.current].sort((a, b) => a - b);
    const mediana = ordinate[Math.floor(ordinate.length / 2)];
    const nota = notaVicina(mediana);
    setLettura({ hz: mediana, nota, chiarezza: f.chiarezza });
  }), [ottieniAnalisi]);

  return (
    <section className="lab-card lab-orecchio" data-testid="lab-orecchio">
      <div className="lab-chead">
        <h2>L&rsquo;Orecchio</h2>
        <span className="lab-cnote">il banco ascolta il mondo: microfono → le stesse tre letture</span>
      </div>

      <div className="lab-azione">
        <button type="button" className={'lab-play' + (acceso ? ' fermo' : '')}
          data-testid="lab-orecchio-apri" onClick={alterna}>
          {acceso ? '■ Chiudi il microfono' : '🎙 Apri il microfono'}
        </button>
        {acceso && (
          <p className="lab-volume" data-testid="lab-orecchio-stato">
            Le tre letture ora guardano il microfono. Chiudilo per
            tornare alle sorgenti del banco.
          </p>
        )}
        {errore && (
          <p className="lab-volume lab-orecchio-errore"
            data-testid="lab-orecchio-errore">{errore}</p>
        )}
      </div>

      {acceso && (
        <div className="lab-accordatore" data-testid="lab-accordatore">
          {lettura ? (
            <>
              <div className="lab-freq-num lab-orecchio-num">
                <span data-testid="lab-orecchio-hz">{lettura.hz.toFixed(1)}</span>
                <b>Hz</b>
              </div>
              {lettura.nota && (
                <p className="lab-nota" data-testid="lab-orecchio-nota">
                  {lettura.nota.nome}
                  {lettura.nota.cents !== 0
                    && ` · ${lettura.nota.cents > 0 ? '+' : ''}${lettura.nota.cents} cent`}
                </p>
              )}
            </>
          ) : (
            <p className="lab-orecchio-attesa">
              In ascolto: suona o canta una nota tenuta.
            </p>
          )}
        </div>
      )}

      {/* la didascalia — ogni modulo si racconta (regola LB) */}
      <p className="lab-didascalia" data-testid="lab-orecchio-didascalia">
        <b>Cosa sta succedendo.</b> Il suono non lascia mai il tuo
        dispositivo: il microfono si collega solo all&rsquo;analisi, niente
        registrazioni, niente invii. I filtri da videochiamata del
        browser (riduzione rumore, guadagno automatico) sono spenti:
        mangerebbero proprio le code e i dettagli che vogliamo vedere.
        Colpisci un bicchiere davanti allo spettro e guarda i suoi modi.
      </p>
    </section>
  );
}
