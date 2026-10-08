/**
 * CasaCampi — SN0 (8/10/2026, piano Aurya Sound): i campi della «casa delle
 * meditazioni» dentro «Le mie tracce», e il pannello delle PLAYLIST.
 *
 * CampiCasa (per traccia): la copertina (foto del founder, decisione 4),
 * il chip dell'accesso Cerchio/Più (decisione 5: il Più è un'etichetta
 * finché l'abbonamento non si accende), «In vetrina», il momento, i tag.
 * Tutto facoltativo: senza, la traccia resta com'era.
 *
 * PlaylistPannello: le raccolte curate — titolo, racconto, copertina,
 * accesso, le tracce in ordine (solo le proprie, pubblicate, non riservate),
 * pubblica (chiave 1) / ritira / togli. Niente motore: solo dati.
 */
import React, { useCallback, useEffect, useState } from 'react';
import { frequenciesAPI } from '../../api/frequencies';
import { compressImage } from '../../lib/compressImage';

export const MOMENTI = [['mattina', 'Mattina'], ['pausa', 'Pausa'], ['sera', 'Sera'], ['notte', 'Notte']];
const COPERTINA_ACCEPT = '.jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp';

const riga = { display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 8, marginTop: 8 };
const chip = (on) => ({
  padding: '3px 10px', borderRadius: 999, fontSize: 12, cursor: 'pointer',
  border: `1px solid ${on ? 'var(--water)' : 'var(--line)'}`, color: on ? 'var(--water)' : 'var(--dimmer)', background: 'transparent',
});
const campo = { background: 'transparent', color: 'inherit', border: '1px solid var(--line)', borderRadius: 8, padding: '4px 8px', fontSize: 12 };

/* SN2 (8/10/2026, piano §4.5) — L'ANNUNCIO AL CERCHIO: un bottone, una prova
   a secco che dice a quante persone si scrive, la conferma, l'invio. Una
   volta sola per contenuto: dopo, resta la riga «Annunciata il …». */
const dataBreve = (iso) => { try { return new Date(iso).toLocaleDateString('it-IT', { day: 'numeric', month: 'long' }); } catch { return ''; } };
export function AnnunciaCerchio({ annuncio, cosa = 'meditazione', aSecco, invia, onFatto }) {
  const [occupato, setOccupato] = useState(false);
  const [esito, setEsito] = useState('');
  if (annuncio?.at) {
    return (
      <span style={{ fontSize: 12, color: 'var(--dimmer)' }} data-testid="fq-annunciata">
        ✉ Annunciata al Cerchio il {dataBreve(annuncio.at)}{annuncio.stato === 'fatto' ? ` · ${annuncio.inviati} email` : ' · in corso'}
      </span>
    );
  }
  const vai = async () => {
    setOccupato(true); setEsito('');
    try {
      const prova = (await aSecco()).data;
      if (!prova.destinatari) { setEsito('Nessun destinatario nel Cerchio.'); return; }
      if (!window.confirm(`Scrivo a ${prova.destinatari} ${prova.destinatari === 1 ? 'persona' : 'persone'} del Cerchio:\n«${prova.oggetto}»\n\nProcedo? Si fa una volta sola.`)) return;
      await invia();
      setEsito('Annuncio partito.');
      await onFatto?.();
    } catch (err) {
      const d = err?.response?.data?.detail;
      setEsito((typeof d === 'string' && d) || 'Annuncio non riuscito.');
    } finally { setOccupato(false); }
  };
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
      <button type="button" style={chip(false)} disabled={occupato} data-testid="fq-annuncia" onClick={vai}
        title={`Scrive al Cerchio che c'è una nuova ${cosa}, con il link che apre già sbloccato`}>✉ Annuncia al Cerchio</button>
      {esito && <span style={{ fontSize: 12, color: 'var(--dimmer)' }}>{esito}</span>}
    </span>
  );
}

export function CampiCasa({ traccia, onCambio, composer }) {
  const [occupato, setOccupato] = useState(false);
  const [tags, setTags] = useState((traccia.tags || []).join(', '));
  useEffect(() => { setTags((traccia.tags || []).join(', ')); }, [traccia.tags]);
  const pubblica = traccia.status === 'published' && traccia.visibility !== 'private';

  const salva = async (dati) => {
    setOccupato(true);
    try { await frequenciesAPI.update(traccia.id, dati); await onCambio?.(); } catch { /* resta com'era */ } finally { setOccupato(false); }
  };
  const copertina = async (file) => {
    if (!file) return;
    setOccupato(true);
    try { await frequenciesAPI.uploadCover(traccia.id, await compressImage(file)); await onCambio?.(); } catch { /* resta com'era */ } finally { setOccupato(false); }
  };

  return (
    <div data-testid="fq-campi-casa" style={{ marginTop: 6 }}>
      <div style={riga}>
        {/* la copertina */}
        <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }} title="La copertina della meditazione (jpg, png, webp)">
          <span style={{ width: 44, height: 44, borderRadius: 8, overflow: 'hidden', background: 'var(--line)', display: 'inline-block', flex: 'none' }}>
            {traccia.cover_url && <img src={traccia.cover_url} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />}
          </span>
          <span style={{ fontSize: 12, color: 'var(--dimmer)', textDecoration: 'underline' }}>{traccia.cover_url ? 'Cambia copertina' : 'Copertina'}</span>
          <input type="file" accept={COPERTINA_ACCEPT} style={{ display: 'none' }} disabled={occupato} data-testid="fq-copertina" onChange={(e) => { copertina(e.target.files?.[0]); e.target.value = ''; }} />
        </label>
        {traccia.cover_url && (
          <button type="button" style={{ ...chip(false), fontSize: 11 }} disabled={occupato}
            onClick={async () => { setOccupato(true); try { await frequenciesAPI.removeCover(traccia.id); await onCambio?.(); } finally { setOccupato(false); } }}>togli</button>
        )}
        {/* il momento */}
        <select style={campo} value={traccia.momento || ''} disabled={occupato} data-testid="fq-momento" aria-label="Momento della giornata"
          onChange={(e) => salva({ momento: e.target.value })}>
          <option value="">Momento: nessuno</option>
          {MOMENTI.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
        </select>
        {/* i tag */}
        <input style={{ ...campo, minWidth: 160 }} value={tags} placeholder="tag, separati da virgola" aria-label="Tag" data-testid="fq-tags"
          onChange={(e) => setTags(e.target.value)}
          onBlur={() => { const arr = tags.split(',').map((t) => t.trim()).filter(Boolean); if (arr.join(',') !== (traccia.tags || []).join(',')) salva({ tags: arr }); }} />
      </div>
      {pubblica && (
        <div style={riga} data-testid="fq-accesso">
          <span style={{ fontSize: 11, color: 'var(--dimmer)' }}>Accesso</span>
          <button type="button" style={chip((traccia.accesso || 'cerchio') === 'cerchio')} disabled={occupato} data-testid="fq-accesso-cerchio"
            onClick={() => salva({ accesso: 'cerchio' })} aria-pressed={(traccia.accesso || 'cerchio') === 'cerchio'}>Cerchio · gratis</button>
          <button type="button" style={chip(traccia.accesso === 'piu')} disabled={occupato} data-testid="fq-accesso-piu"
            onClick={() => salva({ accesso: 'piu' })} aria-pressed={traccia.accesso === 'piu'} title="Per gli abbonati: finché il Più non è acceso resta ascoltabile col Cerchio, con la scritta «Presto nel Più»">Più</button>
          {composer && (
            <button type="button" style={chip(!!traccia.in_vetrina)} disabled={occupato} data-testid="fq-vetrina"
              onClick={() => salva({ in_vetrina: !traccia.in_vetrina })} aria-pressed={!!traccia.in_vetrina}>{traccia.in_vetrina ? '★ In vetrina' : 'In vetrina'}</button>
          )}
          {composer && (
            <AnnunciaCerchio annuncio={traccia.annuncio} cosa="meditazione"
              aSecco={() => frequenciesAPI.annuncia(traccia.id, true)} invia={() => frequenciesAPI.annuncia(traccia.id)} onFatto={onCambio} />
          )}
        </div>
      )}
    </div>
  );
}

export function PlaylistPannello({ tracce, composer }) {
  const [items, setItems] = useState(null);
  const [aperta, setAperta] = useState(null);     // id della playlist in modifica
  const [nuova, setNuova] = useState('');
  const [esito, setEsito] = useState('');
  const carica = useCallback(async () => {
    try { const r = await frequenciesAPI.playlists.mine(); setItems(r.data.items || []); } catch { setItems([]); }
  }, []);
  useEffect(() => { carica(); }, [carica]);

  const pubblicabili = (tracce || []).filter((t) => t.status === 'published' && t.visibility !== 'private');
  const crea = async () => {
    const t = nuova.trim();
    if (!t) return;
    try { const r = await frequenciesAPI.playlists.create({ title: t }); setNuova(''); await carica(); setAperta(r.data.id); }
    catch { setEsito('Non sono riuscito a creare la playlist.'); }
  };
  const salva = async (id, dati) => {
    try { await frequenciesAPI.playlists.update(id, dati); await carica(); } catch (err) { setEsito(err?.response?.data?.detail || 'Non sono riuscito a salvare.'); }
  };
  const azione = async (fn, ok) => {
    setEsito('');
    try { await fn(); await carica(); if (ok) setEsito(ok); }
    catch (err) { const d = err?.response?.data?.detail; setEsito((typeof d === 'string' && d) || d?.message || 'Operazione non riuscita.'); }
  };

  return (
    <section className="bib" data-testid="fq-playlist" style={{ marginTop: 28 }}>
      <h2>Le mie playlist</h2>
      <p>Raccolte curate di meditazioni pubblicate: copertina, racconto, ordine. {composer ? 'Pubblicate, compaiono nella casa delle meditazioni.' : 'Le playlist pubbliche sono su invito, come le Meditazioni di Aurya.'}</p>
      <div style={{ ...riga, marginTop: 12 }}>
        <input style={{ ...campo, minWidth: 220, fontSize: 14, padding: '8px 10px' }} value={nuova} placeholder="Titolo della nuova playlist" data-testid="fq-playlist-nuova"
          onChange={(e) => setNuova(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); crea(); } }} />
        <button type="button" className="primo" onClick={crea} disabled={!nuova.trim()}>Crea playlist</button>
      </div>
      {items === null ? null : items.length === 0 ? (
        <div className="emptycreate" style={{ marginTop: 14 }}><p>Ancora nessuna playlist. Dai un titolo qui sopra e scegli le meditazioni da mettere in fila.</p></div>
      ) : (
        <div className="cards" style={{ marginTop: 14 }}>
          {items.map((p) => {
            const inModifica = aperta === p.id;
            const scelte = p.tracce.map((t) => t.id);
            return (
              <div key={p.id} className={`card mine-card${p.status === 'published' ? ' playing' : ''}`} data-testid={`fq-playlist-${p.id}`}>
                <div className="head" style={{ alignItems: 'center', gap: 10 }}>
                  <span style={{ width: 44, height: 44, borderRadius: 8, overflow: 'hidden', background: 'var(--line)', flex: 'none' }}>
                    {p.cover_url && <img src={p.cover_url} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />}
                  </span>
                  <h3 style={{ flex: 1 }}>{p.title}</h3>
                  <span className="badge" style={p.status !== 'published' ? { color: 'var(--dimmer)', borderColor: 'var(--line)' } : { color: 'var(--water)', borderColor: 'var(--water)' }}>
                    {p.status !== 'published' ? 'BOZZA' : 'PUBBLICA'}
                  </span>
                </div>
                <div className="hz">
                  {p.tracce_count} {p.tracce_count === 1 ? 'meditazione' : 'meditazioni'} · {Math.round((p.duration_sec || 0) / 60)} min · {(p.accesso || 'cerchio') === 'piu' ? 'Più' : 'Cerchio'}
                  {p.in_vetrina ? ' · ★ in vetrina' : ''}{p.status === 'published' && p.slug ? ` · /meditazioni/playlist/${p.slug}` : ''}
                </div>
                {inModifica && (
                  <div style={{ marginTop: 10 }} data-testid="fq-playlist-editor">
                    <input style={{ ...campo, width: '100%', fontSize: 14, padding: '8px 10px' }} defaultValue={p.title} aria-label="Titolo"
                      onBlur={(e) => { const v = e.target.value.trim(); if (v && v !== p.title) salva(p.id, { title: v }); }} />
                    <textarea style={{ ...campo, width: '100%', marginTop: 6, fontSize: 13, padding: '8px 10px', resize: 'vertical' }} rows={2} defaultValue={p.description || ''} placeholder="Due righe: per chi è, cosa contiene" aria-label="Racconto"
                      onBlur={(e) => { if (e.target.value !== (p.description || '')) salva(p.id, { description: e.target.value }); }} />
                    <div style={riga}>
                      <label style={{ fontSize: 12, color: 'var(--dimmer)', textDecoration: 'underline', cursor: 'pointer' }}>
                        {p.cover_url ? 'Cambia copertina' : 'Copertina'}
                        <input type="file" accept={COPERTINA_ACCEPT} style={{ display: 'none' }}
                          onChange={async (e) => { const f = e.target.files?.[0]; e.target.value = ''; if (f) azione(async () => frequenciesAPI.playlists.cover(p.id, await compressImage(f))); }} />
                      </label>
                      <span style={{ fontSize: 11, color: 'var(--dimmer)' }}>Accesso</span>
                      <button type="button" style={chip((p.accesso || 'cerchio') === 'cerchio')} onClick={() => salva(p.id, { accesso: 'cerchio' })}>Cerchio · gratis</button>
                      <button type="button" style={chip(p.accesso === 'piu')} onClick={() => salva(p.id, { accesso: 'piu' })}>Più</button>
                      {composer && p.status === 'published' && (
                        <button type="button" style={chip(!!p.in_vetrina)} onClick={() => salva(p.id, { in_vetrina: !p.in_vetrina })}>{p.in_vetrina ? '★ In vetrina' : 'In vetrina'}</button>
                      )}
                    </div>
                    <p style={{ fontSize: 12, color: 'var(--dimmer)', margin: '10px 0 4px' }}>Le meditazioni, nell'ordine (solo le tue pubblicate, non riservate):</p>
                    <ol style={{ listStyle: 'none', padding: 0, margin: 0 }} data-testid="fq-playlist-tracce">
                      {p.tracce.map((t, i) => (
                        <li key={t.id} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '4px 0', borderBottom: '1px solid var(--line)' }}>
                          <span style={{ fontSize: 12, color: 'var(--dimmer)', width: 18 }}>{i + 1}.</span>
                          <span style={{ flex: 1, fontSize: 13 }}>{t.title}</span>
                          <button type="button" style={chip(false)} disabled={i === 0} aria-label="Sposta su"
                            onClick={() => { const a = [...scelte]; [a[i - 1], a[i]] = [a[i], a[i - 1]]; salva(p.id, { tracce: a }); }}>↑</button>
                          <button type="button" style={chip(false)} disabled={i === p.tracce.length - 1} aria-label="Sposta giù"
                            onClick={() => { const a = [...scelte]; [a[i + 1], a[i]] = [a[i], a[i + 1]]; salva(p.id, { tracce: a }); }}>↓</button>
                          <button type="button" style={chip(false)} aria-label="Togli dalla playlist"
                            onClick={() => salva(p.id, { tracce: scelte.filter((x) => x !== t.id) })}>×</button>
                        </li>
                      ))}
                    </ol>
                    {pubblicabili.filter((t) => !scelte.includes(t.id)).length > 0 && (
                      <select style={{ ...campo, marginTop: 8 }} value="" data-testid="fq-playlist-aggiungi" aria-label="Aggiungi una meditazione"
                        onChange={(e) => { if (e.target.value) salva(p.id, { tracce: [...scelte, e.target.value] }); }}>
                        <option value="">+ Aggiungi una meditazione…</option>
                        {pubblicabili.filter((t) => !scelte.includes(t.id)).map((t) => <option key={t.id} value={t.id}>{t.title}</option>)}
                      </select>
                    )}
                  </div>
                )}
                <div className="foot mine-foot">
                  {p.status !== 'published' ? (
                    composer
                      ? <button type="button" className="primo" data-testid="fq-playlist-pubblica" onClick={() => azione(() => frequenciesAPI.playlists.publish(p.id), 'Playlist pubblicata.')}>Pubblica</button>
                      : <span style={{ fontSize: 12, color: 'var(--dimmer)' }}>Pubblicazione su invito</span>
                  ) : (
                    <button type="button" className="add" onClick={() => azione(() => frequenciesAPI.playlists.unpublish(p.id), 'Playlist ritirata.')}>Ritira</button>
                  )}
                  {composer && p.status === 'published' && (
                    <AnnunciaCerchio annuncio={p.annuncio} cosa="playlist"
                      aSecco={() => frequenciesAPI.playlists.annuncia(p.id, true)} invia={() => frequenciesAPI.playlists.annuncia(p.id)} onFatto={carica} />
                  )}
                  <button type="button" className="live" onClick={() => setAperta(inModifica ? null : p.id)}>{inModifica ? 'Chiudi' : 'Modifica'}</button>
                  <button type="button" className="add" style={{ marginLeft: 'auto' }}
                    onClick={() => { if (window.confirm(`Togliere la playlist «${p.title}»? Le meditazioni restano.`)) azione(() => frequenciesAPI.playlists.remove(p.id), 'Playlist tolta.'); }}>Togli</button>
                </div>
              </div>
            );
          })}
        </div>
      )}
      {esito && <p className="soundlead" style={{ marginTop: 12 }}>{esito}</p>}
    </section>
  );
}
