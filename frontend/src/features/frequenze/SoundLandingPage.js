import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { BIB, SOUND_KEYS } from './content/biblioteca';
import { PERCORSO } from './content/guida';
import { PRO_ENTRY } from './links';
import { SafetyCurtain, SafetyLine } from './SafetyCurtain';
import './frequenze.css';

/*
 * SP4 — /sound: la porta pubblica di Aurya Sound.
 *
 * Non un doppione della biblioteca: un INDICE curato. Cos'e' in tre
 * battute, le tre categorie con un assaggio, il percorso della Guida,
 * UNA CTA primaria per gli operatori, il ponte verso le esperienze
 * pubblicate. Zero motore audio: qui si legge.
 */

const CAT_DESC = {
  'Bande cerebrali': "I ritmi dell'attività elettrica del cervello: cosa osserva l'EEG, cosa significano delta, theta, alpha, beta e gamma — e cosa non significano.",
  'Altre frequenze': 'Frequenze sonore, fenomeni fisici, accordature e tradizioni: dal 40 Hz alla risonanza di Schumann, dal 432 Hz alle frequenze del solfeggio, con il loro livello di evidenza.',
  'Metodi': 'Come si costruisce uno stimolo ritmico: battiti binaurali, monoaurali, toni isocronici, stimolazione bilaterale — e la differenza reale tra loro.',
};
const CAT_LINK = {
  'Bande cerebrali': '/sound/esplora?categoria=bande-cerebrali',
  'Altre frequenze': '/sound/esplora?categoria=altre-frequenze',
  'Metodi': '/sound/esplora?categoria=metodi',
};

export default function SoundLandingPage() {
  useEffect(() => { document.title = 'Aurya Sound — Il suono, spiegato'; }, []);
  const [safety, setSafety] = useState(false);   // SF — lettura su richiesta

  return (
    <div className="fqz sld" data-testid="fqz-landing">
      {/* SP-ter — la porta pubblica porta anche il ritorno */}
      <div className="topbar">
        <a className="fqzbrand" href="/" data-testid="fqz-brand" title="Torna su Aurya">
          <img src="/logo-aurya-512.png" alt="" width="26" height="26" />
          <span>
            <b>Aurya</b>
            <i>torna al sito</i>
          </span>
        </a>
      </div>
      <header>
        <div>
          <h1>Aurya <em>Sound</em></h1>
          <div className="sub">Esperienze sonore progettate per accompagnare diversi stati di presenza.</div>
        </div>
      </header>
      <main>
        <section className="bib">
          <h2>Il suono, spiegato con onestà</h2>
          <p className="sld-lead">
            Una biblioteca educativa su onde cerebrali, frequenze e metodi di
            stimolazione sonora. Ogni scheda dichiara il suo livello di evidenza:
            ciò che è documentato, ciò che è ricerca in corso, ciò che appartiene
            alla tradizione. Si legge, si approfondisce — e si ascolta.
          </p>

          <div className="sld-cats" data-testid="fqz-landing-cats">
            {SOUND_KEYS.map((k) => (
              <Link key={k} to={CAT_LINK[k]} className="sld-cat">
                <b>{k}</b>
                <p>{CAT_DESC[k]}</p>
                <span className="sld-n">{(BIB[k] || []).length} schede →</span>
              </Link>
            ))}
          </div>

          <div className="sld-guide">
            <div className="sld-ghead">
              <b>Le fondamenta</b>
              <span>La guida per partire da zero · circa 5 minuti</span>
            </div>
            <div className="sld-gsteps">
              {PERCORSO.map((s) => (
                <Link key={s.id} to={`/sound/impara#${s.id}`}>
                  <i>{s.n}</i> {s.short}
                </Link>
              ))}
            </div>
            <Link className="sld-glink" to="/sound/impara">Leggi la Guida →</Link>
          </div>

          {/* SP3 — LA CTA primaria: una, qui */}
          <div className="probox" data-testid="fqz-cta-landing">
            <b>Vuoi andare oltre l'esplorazione?</b>
            <p>
              Le frequenze le ascolti liberamente. Gli operatori possono anche
              combinarle con metodi e con la propria voce, e pubblicare la sessione
              con un link da condividere.
            </p>
            <Link to={PRO_ENTRY}>
              <button type="button" className="pro-cta">Scopri Aurya Sound per operatori →</button>
            </Link>
          </div>

          {/* SF — la porta pubblica dice subito com'è fatto l'ascolto */}
          <SafetyLine onOpen={() => setSafety(true)} />

          <div className="sld-bridge" data-testid="fqz-landing-meditazioni">
            <span>Preferisci un'esperienza già composta?</span>{' '}
            <Link to="/meditazioni">Scopri le meditazioni degli operatori →</Link>
          </div>
        </section>
      </main>
      {safety && <SafetyCurtain mode="review" onClose={() => setSafety(false)} />}
      <footer className="fqzfoot" data-testid="fqz-foot">
        <a href="/">← Torna su Aurya</a>
        <a href="/blog">Magazine</a>
        <a href="/newsletter">La Lettera</a>
        <a href="/meditazioni">Meditazioni</a>
      </footer>
    </div>
  );
}
