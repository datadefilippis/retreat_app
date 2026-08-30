/**
 * LA PAGINA-SCHEDA (FA7, piano FARO, 30/8/2026) — /sound/esplora/{slug}.
 *
 * Ogni scheda della biblioteca ha il suo indirizzo: per Google (il
 * contenuto intero e' servito anche dalla shell SSR, stessa fonte)
 * e per le persone (link condivisibile, breadcrumb, sorelle, e il
 * ponte verso la stanza del Lab dove PROVARE il fenomeno). Il testo
 * e' VERBATIM da content/biblioteca.js — una fonte, due padroni.
 */
import React, { useEffect, useMemo } from 'react';
import { Link, useParams } from 'react-router-dom';
import SoundTopbar from './SoundTopbar';
import { BIB } from './content/biblioteca';
import { sluggifica } from './content/slugScheda';
import './frequenze.css';

const GRADI = {
  A: 'Evidenza solida', B: 'Ricerca in corso', C: 'Tradizione e simbolismo',
};

function trova(slug) {
  for (const [categoria, schede] of Object.entries(BIB)) {
    for (const s of schede) {
      if (sluggifica(s.t) === slug) return { ...s, categoria };
    }
  }
  return null;
}

export default function SchedaBibliotecaPage() {
  const { slug } = useParams();
  const scheda = useMemo(() => trova(slug), [slug]);

  useEffect(() => {
    if (scheda) {
      document.title = `${scheda.t} — ${scheda.uso} | Aurya Sound`;
    }
  }, [scheda]);

  if (!scheda) {
    return (
      <div className="fqz" data-testid="scheda-biblioteca-404">
        <SoundTopbar firma="Sound" qui="/sound/esplora" />
        <main>
          <h1>Scheda non trovata</h1>
          <p><Link to="/sound/esplora">← Torna alla biblioteca</Link></p>
        </main>
      </div>
    );
  }

  const sorelle = (BIB[scheda.categoria] || [])
    .filter((s) => sluggifica(s.t) !== slug).slice(0, 3);
  const labRisonanze = /risonanz|schumann/i.test(scheda.t);
  const labUrl = labRisonanze ? '/sound/lab/risonanze' : '/sound/lab/banco';
  const labNome = labRisonanze ? 'Le Risonanze' : 'Il Banco del Lab';

  return (
    <div className="fqz" data-testid="scheda-biblioteca">
      <SoundTopbar firma="Sound" qui="/sound/esplora" />
      <main className="fqz-scheda-pagina">
        <p className="fqz-briciole" data-testid="scheda-briciole">
          <Link to="/sound">Aurya Sound</Link> ›{' '}
          <Link to="/sound/esplora">Esplora</Link> › {scheda.t}
        </p>
        <header>
          <h1>{scheda.t}</h1>
          <p className="fqz-scheda-sotto">
            <b>{scheda.hz}</b> · {scheda.uso}
          </p>
          <p className="fqz-scheda-grado" data-testid="scheda-grado">
            <span className={`grado grado-${scheda.g}`}>{scheda.g}</span>{' '}
            {GRADI[scheda.g] || ''}
          </p>
        </header>
        {/* il testo editoriale VERBATIM della biblioteca — nostro,
            scritto in casa: l'inserimento diretto e' voluto */}
        <article className="fqz-scheda-testo" data-testid="scheda-testo"
          dangerouslySetInnerHTML={{ __html: scheda.full || `<p>${scheda.body}</p>` }} />
        <div className="fqz-scheda-gesti">
          <Link to="/sound/esplora" className="primo"
            data-testid="scheda-ascolta">
            ▶ Ascoltala nella biblioteca
          </Link>
          <Link to={labUrl} data-testid="scheda-lab">
            Provala dal vivo: {labNome} →
          </Link>
        </div>
        {sorelle.length > 0 && (
          <p className="fqz-scheda-sorelle" data-testid="scheda-sorelle">
            Schede sorelle:{' '}
            {sorelle.map((s, i) => (
              <React.Fragment key={s.t}>
                {i > 0 && ' · '}
                <Link to={`/sound/esplora/${sluggifica(s.t)}`}>{s.t}</Link>
              </React.Fragment>
            ))}
          </p>
        )}
      </main>
      <footer className="fqzfoot">
        <Link to="/sound/esplora">← La biblioteca</Link>
        <Link to="/sound/impara">Le fondamenta</Link>
        <Link to="/sound/lab">Il Lab</Link>
      </footer>
    </div>
  );
}
