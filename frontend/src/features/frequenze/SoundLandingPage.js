import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { BIB, SOUND_KEYS, CAT_DESC, CAT_LINK } from './content/biblioteca';
import { PERCORSO } from './content/guida';
import { ELENCO } from './content/esperienze';
import { SafetyCurtain, SafetyLine } from './SafetyCurtain';
import './frequenze.css';
import SoundTopbar from './SoundTopbar';

/*
 * SP4 — /sound: la porta pubblica di Aurya Sound.
 *
 * Non un doppione della biblioteca: un INDICE curato. Cos'e' in tre
 * battute, le tre categorie con un assaggio, il percorso della Guida,
 * UNA CTA primaria per gli operatori, il ponte verso le esperienze
 * pubblicate. Zero motore audio: qui si legge.
 */

/*
 * Nomi, slug e descrizioni delle categorie arrivano da content/biblioteca:
 * la landing NON tiene una sua copia (era il modo in cui «Ritmi del corpo»
 * usciva senza descrizione e senza link).
 */

export default function SoundLandingPage() {
  useEffect(() => { document.title = 'Aurya Sound — Il suono, spiegato'; }, []);
  const [safety, setSafety] = useState(false);   // SF — lettura su richiesta

  return (
    <div className="fqz sld" data-testid="fqz-landing">
      {/* SP-ter — la porta pubblica porta anche il ritorno */}
      <SoundTopbar firma="Sound" qui="/sound" />
      <header>
        <div>
          <h1>Aurya <em>Sound</em></h1>
          <div className="sub">Esperienze sonore progettate per accompagnare diversi stati di presenza.</div>
          {/* DN5 (21/8) — dichiarare la parentela costa una riga e rende
              ovvio cio' che il cambio di luce potrebbe far sembrare un
              altro sito. */}
          <p className="sld-parentela" data-testid="sound-parentela">
            Aurya Sound è lo studio di Aurya: qui si compone e si ascolta.
          </p>
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

          {/* LE ESPERIENZE (26/8) — stanno PRIMA delle schede, perche'
              si ascolta prima di studiare. L'elenco viene dal registro:
              aggiungerne una non tocca questa pagina. */}
          <div className="sld-esp" data-testid="sld-esperienze">
            {ELENCO.map((e) => (
              <Link key={e.id} to={`/sound/${e.id}`} data-testid={`sld-${e.id}`}>
                <b>{e.titolo}</b>
                <span>{e.sottotitolo}</span>
                <i>{Math.round(e.durata / 60)} minuti</i>
              </Link>
            ))}
          </div>

          <div className="sld-cats" data-testid="fqz-landing-cats">
            {SOUND_KEYS.map((k) => (
              <Link key={k} to={CAT_LINK(k)} className="sld-cat">
                <b>{k}</b>
                <p>{CAT_DESC[k]}</p>
                <span className="sld-n">{(BIB[k] || []).length} schede →</span>
              </Link>
            ))}
          </div>

          {/* AV2 — la stanza dello strumento: il TUO suono, guardato */}
          <p style={{ marginTop: 18 }}>
            <Link to="/sound/visual" className="readmore"
              data-testid="sld-visual" style={{ textDecoration: 'none' }}>
              ✦ Aurya Mode — porta una tua traccia o il microfono e
              guarda il suono diventare luce
            </Link>
          </p>

          {/* LAB — la biblioteca che si tocca: un vero generatore di
              segnali, e a passi l'intero banco (oscilloscopio, spettro,
              sweep sullo stesso motore) */}
          <p style={{ marginTop: 8 }}>
            <Link to="/sound/lab" className="readmore"
              data-testid="sld-lab" style={{ textDecoration: 'none' }}>
              ⚗ Il Laboratorio — genera un segnale vero e misuralo:
              frequenza, forma d'onda, ampiezza, fase
            </Link>
          </p>

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

          {/* SF — la porta pubblica dice subito com'è fatto l'ascolto */}
          <SafetyLine onOpen={() => setSafety(true)} />

          {/* Deciso dal founder (26/8 sera): la via professionale
              promossa e' CREA — comporre per i propri clienti — non
              piu' il catalogo Professional (che resta strumento, non
              vetrina, finche' non avra' un valore oltre il play). */}
          <div className="sld-pro" data-testid="sld-crea">
            <div>
              <strong>Per i professionisti del benessere</strong>
              <span>
                Crea è l’atelier con cui nascono le esperienze e le
                meditazioni di Aurya. Lo apriamo progressivamente a chi
                accompagna persone: componi le tue meditazioni e
                condividile con i tuoi clienti.
              </span>
            </div>
            <Link className="sld-pro-cta" to="/sound/studio"
              data-testid="sld-crea-link">Scopri come →</Link>
          </div>

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
