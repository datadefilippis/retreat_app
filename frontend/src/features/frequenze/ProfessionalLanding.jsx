/**
 * /sound/professional — LA PAGINA DI VENDITA (L4, 26/8/2026).
 *
 * Pubblica e indicizzata (a differenza dello strumento, /sound/pro,
 * che resta noindex): qui si SPIEGA e si DESIDERA, là si lavora.
 *
 * IL REGISTRO DELLA VOCE (C0): scienza in avanti — l'ASSR in
 * apertura, le review nominate, la risonanza respiratoria — e i
 * limiti presenti ma MAI in apertura. Persuasiva E difendibile:
 * niente percentuali da sondaggio, niente promesse di stati,
 * l'onestà detta come forza («i limiti sulla scheda, non a piè di
 * pagina»).
 *
 * LE PROVE VISIVE sono vere: le partiture qui dentro sono generate
 * dagli score reali del catalogo — nessun mockup.
 *
 * Il filo: ti fidi (prova gratis, adesso) → capisci (teorie,
 * partiture) → vuoi (rito, registro, «la volta scorsa») → chiedi
 * l'invito (funnel leads esistente, type=operator).
 */
import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../../api/client';
import SoundTopbar from './SoundTopbar';
import Partitura from './pro/Partitura';
import { CATALOGO } from './pro/catalogo';
import { PERCORSI } from './pro/percorsi';
import { messaggio } from './pro/errori';
import './frequenze.css';
import './pro/pro.css';

const PILASTRI = [
  {
    t: 'Il metodo',
    d: 'Protocolli d’ascolto con un arco preciso e basi dichiarate '
      + 'scheda per scheda, percorsi di più settimane con dose e '
      + 'cadenza, controindicazioni serie. Il suono smette di essere '
      + 'un sottofondo e diventa parte del tuo lavoro.',
  },
  {
    t: 'La memoria',
    d: 'Ogni sessione resta nel registro: con chi, cosa, com’è '
      + 'andata. Alla seduta dopo leggi «la volta scorsa: da 4 a 7» '
      + 'invece di andare a memoria. È la differenza fra mettere '
      + 'musica e condurre una pratica di cui rispondi.',
  },
  {
    t: 'La misura',
    d: 'Il vissuto dichiarato dalla persona, prima e dopo, disegnato '
      + 'nel tempo. E nella direzione di sviluppo: la variabilità '
      + 'cardiaca durante la respirazione guidata — l’evidenza più '
      + 'forte di tutto questo campo.',
  },
];

export default function ProfessionalLanding() {
  useEffect(() => {
    document.title = 'Aurya Sound Professional — l’ascolto guidato per professionisti';
  }, []);
  const [email, setEmail] = useState('');
  const [nome, setNome] = useState('');
  const [stato, setStato] = useState(null);   // null | 'invio' | 'fatto' | errore

  const ground = CATALOGO.find((p) => p.id === 'ground');
  const rilassare = CATALOGO.find((p) => p.id === 'rilassare');

  const chiedi = async (e) => {
    e.preventDefault();
    if (!email.trim() || stato === 'invio') return;
    setStato('invio');
    try {
      await api.post('/public/leads', {
        type: 'operator',
        email: email.trim(),
        name: nome.trim() || null,
        message: 'Aurya Sound Professional — richiesta di invito',
        interests: ['sound_professional'],
      });
      setStato('fatto');
    } catch (err) {
      setStato(messaggio(err, 'Non inviato: riprova fra un momento.'));
    }
  };

  return (
    <div className="fqz prof" data-testid="prof-landing">
      <SoundTopbar firma="Professional" />
      <main>
        {/* ── il fatto misurabile, in apertura ── */}
        <section className="prof-hero">
          <p className="sub">Aurya Sound Professional</p>
          <h1>L’ascolto <em>guidato</em></h1>
          <p className="prof-lead" data-testid="prof-lead">
            Il cervello segue la stimolazione sonora ritmica: si chiama
            risposta uditiva stazionaria (ASSR), è neurofisiologia
            consolidata. Su questa base, Aurya Sound Professional ti dà
            protocolli d’ascolto strutturati da condurre con i tuoi
            clienti — con le basi dichiarate, il registro di ogni
            sessione, e nessuna attrezzatura da comprare.
          </p>
          <div className="prof-azioni">
            <a className="sld-pro-cta" href="#invito">Richiedi l’invito</a>
            <Link className="prof-prova" to="/sound/ground">
              Ascolta GROUND, gratis, adesso →
            </Link>
          </div>
        </section>

        {/* ── i tre pilastri ── */}
        <section className="prof-pilastri" data-testid="prof-pilastri">
          {PILASTRI.map((p) => (
            <article key={p.t}>
              <h2>{p.t}</h2>
              <p>{p.d}</p>
            </article>
          ))}
        </section>

        {/* ── la prova visiva: partiture VERE ── */}
        <section className="prof-partiture" data-testid="prof-partiture">
          <h2>Ogni protocollo si vede, prima di sentirsi</h2>
          <p className="prof-testo">
            Questa è la partitura vera di GROUND — otto minuti di
            registro basso che si sente prima nel corpo che nelle
            orecchie. Le bande sono i suoni che entrano ed escono, lo
            spessore è l’intensità: niente è decorativo, se si vede è
            nel suono.
          </p>
          {ground && <Partitura score={ground.costruisci()} dettaglio />}
          <p className="prof-testo prof-quiete">
            E questa è Rilassare: l’uso meglio documentato del
            catalogo — un battito binaurale che si stabilizza e ci
            resta (review: Garcia-Argibay 2019, Chaieb 2015).
          </p>
          {rilassare && <Partitura score={rilassare.costruisci()} />}
        </section>

        {/* ── i percorsi ── */}
        <section className="prof-percorsi" data-testid="prof-percorsi">
          <h2>Percorsi, non playlist</h2>
          <p className="prof-testo">
            La pratica che funziona è quella che torna: percorsi di più
            settimane con una cadenza e una progressione, e il registro
            che ricorda a che punto è ogni persona.
          </p>
          <div className="prof-pc">
            {PERCORSI.map((pc) => (
              <div key={pc.id} className="prof-pc-card">
                <b>{pc.titolo}</b>
                <span>{pc.durata.settimane} settimane · {pc.durata.a_settimana} a settimana · {pc.tappe.length} tappe</span>
              </div>
            ))}
          </div>
        </section>

        {/* ── l'onestà come firma ── */}
        <section className="prof-onesta" data-testid="prof-onesta">
          <h2>Le basi, in faccia</h2>
          <p className="prof-testo">
            Ogni scheda nomina la sua teoria e le sue fonti —
            entrainment uditivo, psicoacustica delle basse frequenze,
            respirazione di risonanza — e dichiara il grado di
            evidenza, punti di forza e confini compresi. Nessuna
            percentuale da sondaggio, nessuna promessa di stati:
            chi sa dove finisce la propria evidenza è chi la sta
            usando davvero. È il motivo per cui puoi proporla ai tuoi
            clienti a testa alta.
          </p>
        </section>

        {/* ── la richiesta d'invito ── */}
        <section className="prof-invito" id="invito" data-testid="prof-invito">
          <h2>Su invito, per cominciare bene</h2>
          <p className="prof-testo">
            Stiamo aprendo Aurya Sound Professional a un gruppo
            ristretto di professionisti, per costruirlo con chi lo usa.
            Lascia la tua email: ti scriviamo noi.
          </p>
          {stato === 'fatto' ? (
            <p className="prof-grazie" data-testid="prof-grazie">
              Ricevuto. Ti scriviamo a breve — nel frattempo puoi
              <Link to="/sound"> esplorare Aurya Sound</Link>.
            </p>
          ) : (
            <form className="prof-form" onSubmit={chiedi}>
              <input type="text" value={nome} placeholder="Il tuo nome"
                onChange={(e) => setNome(e.target.value)}
                data-testid="prof-nome" />
              <input type="email" value={email} required
                placeholder="La tua email"
                onChange={(e) => setEmail(e.target.value)}
                data-testid="prof-email" />
              <button type="submit" className="primary" data-testid="prof-invia"
                disabled={stato === 'invio'}>
                {stato === 'invio' ? 'Invio…' : 'Richiedi l’invito'}
              </button>
            </form>
          )}
          {typeof stato === 'string' && stato !== 'invio' && stato !== 'fatto' && (
            <p className="pro-errore">{stato}</p>
          )}
          <p className="prof-nota">
            Niente spam: una richiesta, una risposta. I dati restano in
            Aurya (<Link to="/privacy">privacy</Link>).
          </p>
        </section>
      </main>
    </div>
  );
}
