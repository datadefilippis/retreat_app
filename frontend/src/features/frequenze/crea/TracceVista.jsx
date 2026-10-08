/**
 * TracceVista — LE MIE TRACCE, il vestito nuovo (CR4, 8/10/2026 sera).
 *
 * Card compatte in griglia (copertina quadrata, titolo, stato come
 * pastiglia, durata · livelli · ascolti), UN gesto primario per stato
 * (gli stessi handler e testid di sempre), «Apri» che porta in Crea con
 * ?bozza=, «Modifica» che apre i campi della casa (CampiCasa, intatto) in
 * un foglio. Filtri in testa (Tutte · Bozze · Riservate · Nelle
 * Meditazioni) e cerca; le playlist nel loro pannello sotto, com'è.
 * Riceve `kit` da FrequenzePage: nessuno stato di dati qui dentro.
 */
import React, { useMemo, useState } from 'react';
import { CampiCasa, PlaylistPannello } from '../CasaCampi';
import CondivisioniTraccia from '../pro/Condivisioni';
import { SelettoreCrea, Foglio } from './CreaVista';
import './crea.css';

const FILTRI = [['tutte', 'Tutte'], ['bozze', 'Bozze'], ['riservate', 'Riservate'], ['pubbliche', 'Nelle Meditazioni']];
const statoDi = (d) => (d.status !== 'published' ? 'bozza' : d.visibility === 'private' ? 'riservata' : 'pubblica');
const ETICHETTA = { bozza: 'Bozza', riservata: 'Riservata', pubblica: 'Nelle Meditazioni' };

export default function TracceVista({ kit: k }) {
  const [filtro, setFiltro] = useState('tutte');
  const [q, setQ] = useState('');
  const [modifica, setModifica] = useState(null);
  const conte = useMemo(() => {
    const c = { tutte: k.drafts.length, bozze: 0, riservate: 0, pubbliche: 0 };
    k.drafts.forEach((d) => { const s = statoDi(d); if (s === 'bozza') c.bozze += 1; else if (s === 'riservata') c.riservate += 1; else c.pubbliche += 1; });
    return c;
  }, [k.drafts]);
  const qq = q.trim().toLowerCase();
  const lista = k.drafts.filter((d) => {
    const s = statoDi(d);
    const ok = filtro === 'tutte' || (filtro === 'bozze' && s === 'bozza') || (filtro === 'riservate' && s === 'riservata') || (filtro === 'pubbliche' && s === 'pubblica');
    return ok && (!qq || (d.title || '').toLowerCase().includes(qq));
  });
  const inModifica = k.drafts.find((d) => d.id === modifica) || null;

  return (
    <section className="cr tracce" data-testid="tracce-vista">
      <SelettoreCrea attiva="tracce" badge={k.layers.length} navigate={k.navigate} onFonti={() => k.navigate('/sound/crea')} />
      <div className="cr-tracce-testa">
        <div className="cr-chips" data-testid="cr-tracce-filtri">
          {FILTRI.map(([id, label]) => (
            <button key={id} type="button" className={`cr-chip${filtro === id ? ' on' : ''}`} data-testid={`cr-filtro-${id}`}
              onClick={() => setFiltro(id)}>{label}{conte[id] > 0 && <span className="cr-conta">{conte[id]}</span>}</button>
          ))}
        </div>
        <input type="search" className="cr-cerca" value={q} onChange={(e) => setQ(e.target.value)}
          placeholder="Cerca fra le tue tracce" aria-label="Cerca" data-testid="cr-tracce-cerca" />
      </div>
      {k.status && <p className="cr-hint cr-tracce-stato" data-testid="cr-tracce-stato">{k.status}</p>}

      {k.drafts.length === 0 ? (
        <div className="cr-vuoto" data-testid="cr-tracce-vuoto">
          <p>Ancora nessuna traccia.</p>
          <div><button type="button" onClick={() => k.navigate('/sound/crea')}>Vai a Crea e salva la prima sessione</button></div>
        </div>
      ) : lista.length === 0 ? (
        <p className="cr-hint">Nessuna traccia con questo filtro.</p>
      ) : (
        <div className="cr-griglia" data-testid="cr-tracce">
          {lista.map((d) => {
            const s = statoDi(d);
            return (
              <article key={d.id} className={`cr-card stato-${s}`} data-testid="cr-traccia-card">
                <button type="button" className="cr-card-cover" title="Apri in Crea" aria-label={`Apri «${d.title || 'Senza titolo'}»`}
                  onClick={() => k.openDraft(d.id)}>
                  {d.cover_url ? <img src={d.cover_url} alt="" loading="lazy" /> : <span>{(d.title || '?').trim().slice(0, 1).toUpperCase()}</span>}
                </button>
                <div className="cr-card-corpo">
                  <div className="cr-card-testa">
                    <h3>{d.title || 'Senza titolo'}</h3>
                    <span className={`cr-stato-pill ${s}`}>{ETICHETTA[s]}</span>
                  </div>
                  <div className="cr-card-meta">
                    {k.fmt(d.duration_sec || 0)} · {d.layers_count} {d.layers_count === 1 ? 'livello' : 'livelli'}
                    {s === 'pubblica' && ` · ${d.plays_total || 0} ascolti`}
                    {s === 'riservata' && ` · ${d.shares_attivi || 0} ${(d.shares_attivi || 0) === 1 ? 'link attivo' : 'link attivi'}`}
                    {d.in_vetrina && ' · ★ in vetrina'}
                    {d.annuncio?.at && ' · ✉ annunciata'}
                  </div>
                  {s === 'pubblica' && d.slug && (
                    <a className="cr-card-link" href={`/frequenze/${d.slug}`} target="_blank" rel="noreferrer" data-testid="cr-traccia-link">/frequenze/{d.slug}</a>
                  )}
                  <div className="cr-card-gesti">
                    {s === 'bozza' ? (
                      k.composer ? (
                        <>
                          <button type="button" className="primo" data-testid="fq-pubblica-meditazioni"
                            onClick={() => k.confermaMeditazioni(d)}>Nelle Meditazioni</button>
                          <button type="button" data-testid="fq-pubblica-riservata"
                            onClick={() => k.pubblicaDaLista(d.id, 'private')}>Riservata</button>
                        </>
                      ) : (
                        <button type="button" className="primo" data-testid="fq-pubblica-riservata"
                          onClick={() => k.pubblicaDaLista(d.id, 'private')}>Pubblica per i tuoi clienti</button>
                      )
                    ) : s === 'riservata' ? (
                      <>
                        <button type="button" className="primo" data-testid="fq-link-riservati"
                          onClick={() => k.setCondividi({ id: d.id, titolo: d.title })}>Link riservati ({d.shares_attivi || 0})</button>
                        <button type="button" onClick={() => k.unpublishById(d.id)}>Riporta in bozza</button>
                      </>
                    ) : (
                      <>
                        <button type="button" className="primo" onClick={() => k.copyPublicLink(d.slug)}>Copia link</button>
                        <button type="button" onClick={() => k.unpublishById(d.id)}>Ritira</button>
                      </>
                    )}
                    <span className="cr-card-spazio" />
                    <button type="button" className="tenue" data-testid="cr-traccia-modifica" onClick={() => setModifica(d.id)}>Modifica</button>
                    <button type="button" className="tenue" onClick={() => k.openDraft(d.id)}>Apri</button>
                  </div>
                </div>
              </article>
            );
          })}
        </div>
      )}

      <div className="cr-playlist"><PlaylistPannello tracce={k.drafts} composer={k.composer} /></div>

      {k.condividi && (
        <CondivisioniTraccia trackId={k.condividi.id} titolo={k.condividi.titolo}
          onCambio={k.loadDrafts} onChiudi={() => k.setCondividi(null)} />
      )}
      {inModifica && (
        <Foglio aperto titolo={inModifica.title || 'Senza titolo'} testid="cr-foglio-modifica" onChiudi={() => setModifica(null)}>
          <div className="cr-modifica">
            <CampiCasa traccia={inModifica} onCambio={k.loadDrafts} composer={k.composer} />
          </div>
          <div className="cr-azioni">
            {statoDi(inModifica) === 'pubblica' && inModifica.slug && (
              <a className="cr-link" href={`/frequenze/${inModifica.slug}`} target="_blank" rel="noreferrer">Apri la pagina pubblica ↗</a>
            )}
            <button type="button" className="pericolo" data-testid="cr-traccia-elimina"
              onClick={() => { setModifica(null); k.removeDraft(inModifica.id, inModifica.title); }}>Elimina la traccia</button>
          </div>
        </Foglio>
      )}
    </section>
  );
}
