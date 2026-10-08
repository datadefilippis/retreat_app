/**
 * SoundAscoltiSezione — CS4 (8/10/2026): Regia → Sound → gli ASCOLTI.
 * Il founder: «per ogni utente quali registrazioni ascolta, quante volte,
 * quando, se la completa, per quanti minuti; uno score di chi segue di più;
 * chi aggiunge ai preferiti». Quattro viste sugli eventi gia' registrati:
 * panoramica, per meditazione (con la curva di abbandono), per persona (con
 * la linea del tempo e lo score «seguito», spiegato nelle sue cinque parti),
 * e il CSV. Solo lettura: la regia guarda, non tocca.
 */
import { useEffect, useMemo, useState } from 'react';
import api from '../../api/client';

const PERIODI = [['7', '7 giorni'], ['30', '30 giorni'], ['90', '90 giorni'], ['tutto', 'Tutto']];
const FASCE = { mattina: 'Mattina', pausa: 'Pausa', sera: 'Sera', notte: 'Notte' };
const PARTI = { frequenza: 'Frequenza', costanza: 'Costanza', profondita: 'Profondità', ampiezza: 'Ampiezza', affetto: 'Affetto' };
const pct = (x) => `${Math.round((x || 0) * 100)}%`;
const quando = (iso) => { if (!iso) return '—'; const d = new Date(iso); return d.toLocaleString('it-IT', { day: '2-digit', month: '2-digit', year: '2-digit', hour: '2-digit', minute: '2-digit' }); };
const giorno = (iso) => (iso ? new Date(iso).toLocaleDateString('it-IT', { day: '2-digit', month: '2-digit', year: '2-digit' }) : '—');

function Numero({ etichetta, valore, nota }) {
  return (
    <div className="rounded-lg border bg-white px-3 py-2">
      <div className="text-xs text-gray-500">{etichetta}</div>
      <div className="text-xl font-semibold text-gray-900">{valore}</div>
      {nota && <div className="text-[11px] text-gray-400">{nota}</div>}
    </div>
  );
}

function Barre({ dati, etichetta }) {
  const max = Math.max(1, ...dati.map((d) => d.v));
  return (
    <div className="rounded-lg border bg-white p-3">
      <div className="text-xs text-gray-500 mb-2">{etichetta}</div>
      <div className="flex items-end gap-[2px] h-16">
        {dati.map((d) => (
          <div key={d.k} className="flex-1 bg-[#2f5749]/70 rounded-sm" style={{ height: `${Math.max(2, (d.v / max) * 100)}%` }} title={`${d.k}: ${d.v}`} />
        ))}
      </div>
      {dati.length <= 8 && <div className="mt-1 flex gap-[2px] text-[10px] text-gray-500">{dati.map((d) => <span key={d.k} className="flex-1 text-center truncate">{d.k}</span>)}</div>}
    </div>
  );
}

export default function SoundAscoltiSezione() {
  const [vista, setVista] = useState('panoramica');
  const [periodo, setPeriodo] = useState('30');
  const [pan, setPan] = useState(null);
  const [med, setMed] = useState([]);
  const [per, setPer] = useState([]);
  const [pesi, setPesi] = useState(null);
  const [aperto, setAperto] = useState(null);     // {tipo:'med'|'per', dati}
  const [esito, setEsito] = useState('');
  const [ordina, setOrdina] = useState({ med: 'ascolti', per: 'score' });

  useEffect(() => {
    let vivo = true;
    setEsito('');
    Promise.all([
      api.get('/admin/sound/ascolti/panoramica', { params: { periodo } }),
      api.get('/admin/sound/ascolti/meditazioni', { params: { periodo } }),
      api.get('/admin/sound/ascolti/persone', { params: { periodo } }),
    ]).then(([a, b, c]) => { if (!vivo) return; setPan(a.data); setMed(b.data.items || []); setPer(c.data.items || []); setPesi(c.data.pesi || null); })
      .catch(() => { if (vivo) setEsito('Non riesco a leggere gli ascolti.'); });
    return () => { vivo = false; };
  }, [periodo]);

  const apriMed = async (slug) => {
    try { const r = await api.get(`/admin/sound/ascolti/meditazioni/${encodeURIComponent(slug)}`, { params: { periodo } }); setAperto({ tipo: 'med', dati: r.data }); }
    catch { setEsito('Dettaglio non disponibile.'); }
  };
  const apriPer = async (id) => {
    try { const r = await api.get(`/admin/sound/ascolti/persone/${encodeURIComponent(id)}`); setAperto({ tipo: 'per', dati: r.data }); }
    catch { setEsito('Dettaglio non disponibile.'); }
  };
  const scarica = async (v) => {
    try {
      const r = await api.get('/admin/sound/ascolti/export.csv', { params: { vista: v, periodo }, responseType: 'blob' });
      const url = URL.createObjectURL(r.data); const a = document.createElement('a'); a.href = url; a.download = `aurya-ascolti-${v}-${periodo}.csv`; a.click(); URL.revokeObjectURL(url);
    } catch { setEsito('Esportazione non riuscita.'); }
  };
  const medOrd = useMemo(() => [...med].sort((a, b) => (b[ordina.med] || 0) - (a[ordina.med] || 0)), [med, ordina.med]);
  const perOrd = useMemo(() => [...per].sort((a, b) => (b[ordina.per] || 0) - (a[ordina.per] || 0)), [per, ordina.per]);

  const Testa = ({ campi, chiave }) => (
    <tr className="text-left text-xs text-gray-500">
      {campi.map(([k, l]) => (
        <th key={k} className={`py-1 pr-3 font-medium ${k && k !== 'titolo' && k !== 'nome' ? 'cursor-pointer hover:text-gray-900' : ''}`}
          onClick={() => k && k !== 'titolo' && k !== 'nome' && setOrdina({ ...ordina, [chiave]: k })}>{l}{ordina[chiave] === k ? ' ▾' : ''}</th>
      ))}
    </tr>
  );

  return (
    <section className="mt-10" data-testid="admin-sound-ascolti">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold text-gray-900">Gli ascolti</h2>
          <p className="mt-1 text-sm text-gray-600">Chi ascolta cosa, quando, per quanto, se la finisce. Solo chi ha l'account entra in «Persone»; chi ascolta col Cerchio senza account conta solo nei totali.</p>
        </div>
        <div className="flex items-center gap-2">
          <select className="rounded border px-2 py-1 text-sm" value={periodo} onChange={(e) => setPeriodo(e.target.value)} data-testid="admin-ascolti-periodo">
            {PERIODI.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
          <div className="flex rounded-full border overflow-hidden text-sm" data-testid="admin-ascolti-viste">
            {[['panoramica', 'Panoramica'], ['meditazioni', 'Meditazioni'], ['persone', 'Persone']].map(([v, l]) => (
              <button key={v} type="button" className={`px-3 py-1 ${vista === v ? 'bg-[#2f5749] text-white' : 'bg-white text-gray-700'}`} onClick={() => setVista(v)} data-testid={`admin-ascolti-vista-${v}`}>{l}</button>
            ))}
          </div>
        </div>
      </div>
      {esito && <p className="mt-2 text-sm text-red-600" data-testid="admin-ascolti-esito">{esito}</p>}

      {vista === 'panoramica' && pan && (
        <div className="mt-4 space-y-3" data-testid="admin-ascolti-panoramica">
          <div className="grid grid-cols-2 gap-2 md:grid-cols-4 lg:grid-cols-7">
            <Numero etichetta="Ascolti" valore={pan.ascolti} nota={pan.ascolti_anonimi ? `${pan.ascolti_anonimi} senza account` : undefined} />
            <Numero etichetta="Persone attive" valore={pan.persone} />
            <Numero etichetta="Nuovi ascoltatori" valore={pan.nuovi_ascoltatori} />
            <Numero etichetta="Minuti ascoltati" valore={Math.round(pan.minuti)} />
            <Numero etichetta="Completamento" valore={pct(pan.completamento)} nota="ascolti portati a fine" />
            <Numero etichetta="Preferiti aggiunti" valore={pan.preferiti_aggiunti} />
            <Numero etichetta="Periodo" valore={PERIODI.find(([v]) => v === periodo)?.[1]} />
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            <Barre etichetta="Ascolti per giorno" dati={pan.per_giorno.map((d) => ({ k: d.giorno.slice(5), v: d.ascolti }))} />
            <Barre etichetta="Quando si ascolta" dati={Object.entries(pan.per_fascia).map(([k, v]) => ({ k: FASCE[k] || k, v }))} />
          </div>
        </div>
      )}

      {vista === 'meditazioni' && (
        <div className="mt-4" data-testid="admin-ascolti-meditazioni">
          <div className="flex justify-end"><button type="button" className="text-xs underline text-gray-600" onClick={() => scarica('meditazioni')}>Esporta CSV</button></div>
          <div className="overflow-x-auto rounded-lg border bg-white mt-2">
            <table className="min-w-full text-sm">
              <thead className="bg-gray-50"><Testa chiave="med" campi={[['titolo', 'Meditazione'], ['ascolti', 'Ascolti'], ['persone', 'Persone'], ['minuti', 'Minuti'], ['completamento', 'Completa'], ['abbandono_medio', 'Arriva a'], ['preferiti', 'Preferiti'], ['momento_punta', 'Momento']]} /></thead>
              <tbody className="divide-y">
                {medOrd.map((m) => (
                  <tr key={m.slug} className="hover:bg-gray-50 cursor-pointer" onClick={() => apriMed(m.slug)} data-testid={`admin-ascolti-med-${m.slug}`}>
                    <td className="py-2 pr-3"><div className="font-medium text-gray-900">{m.titolo}</div><div className="text-[11px] text-gray-500">{m.stato === 'published' ? (m.visibilita === 'private' ? 'riservata' : 'nelle Meditazioni') : 'bozza'}{m.categoria ? ` · ${m.categoria}` : ''}</div></td>
                    <td className="py-2 pr-3">{m.ascolti}{m.anonimi ? <span className="text-[11px] text-gray-400"> (+{m.anonimi} anon.)</span> : null}</td>
                    <td className="py-2 pr-3">{m.persone}</td>
                    <td className="py-2 pr-3">{m.minuti}</td>
                    <td className="py-2 pr-3">{pct(m.completamento)}</td>
                    <td className="py-2 pr-3">{m.abbandono_medio}%</td>
                    <td className="py-2 pr-3">{m.preferiti}</td>
                    <td className="py-2 pr-3">{FASCE[m.momento_punta] || '—'}</td>
                  </tr>
                ))}
                {!medOrd.length && <tr><td className="py-3 text-gray-500" colSpan={8}>Nessun ascolto nel periodo.</td></tr>}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {vista === 'persone' && (
        <div className="mt-4" data-testid="admin-ascolti-persone">
          <div className="flex items-center justify-between">
            {pesi && <p className="text-[11px] text-gray-500">Score «seguito» = {Object.entries(pesi).map(([k, v]) => `${v}·${PARTI[k]?.toLowerCase()}`).join(' + ')}</p>}
            <button type="button" className="text-xs underline text-gray-600" onClick={() => scarica('persone')}>Esporta CSV</button>
          </div>
          <div className="overflow-x-auto rounded-lg border bg-white mt-2">
            <table className="min-w-full text-sm">
              <thead className="bg-gray-50"><Testa chiave="per" campi={[['nome', 'Persona'], ['score', 'Seguito'], ['ascolti', 'Ascolti'], ['minuti', 'Minuti'], ['completati', 'Finite'], ['titoli_diversi', 'Titoli'], ['preferite', 'Preferite'], ['giorni_attivi_30', 'Giorni/30'], ['settimane_consecutive', 'Settimane'], ['fascia_abituale', 'Quando'], ['ultimo_ascolto', 'Ultimo']]} /></thead>
              <tbody className="divide-y">
                {perOrd.map((p) => (
                  <tr key={p.account_id} className="hover:bg-gray-50 cursor-pointer" onClick={() => apriPer(p.account_id)} data-testid={`admin-ascolti-per-${p.account_id}`}>
                    <td className="py-2 pr-3"><div className="font-medium text-gray-900">{p.nome || '—'}</div><div className="text-[11px] text-gray-500">{p.email}</div></td>
                    <td className="py-2 pr-3"><span className="inline-block rounded-full bg-[#2f5749] px-2 py-[2px] text-xs font-semibold text-white" title={Object.entries(p.parti || {}).map(([k, v]) => `${PARTI[k]} ${Math.round(v * 100)}%`).join(' · ')}>{p.score}</span></td>
                    <td className="py-2 pr-3">{p.ascolti}</td>
                    <td className="py-2 pr-3">{p.minuti}</td>
                    <td className="py-2 pr-3">{p.completati}</td>
                    <td className="py-2 pr-3">{p.titoli_diversi}</td>
                    <td className="py-2 pr-3">{p.preferite}</td>
                    <td className="py-2 pr-3">{p.giorni_attivi_30}</td>
                    <td className="py-2 pr-3">{p.settimane_consecutive}</td>
                    <td className="py-2 pr-3">{FASCE[p.fascia_abituale] || '—'}</td>
                    <td className="py-2 pr-3 whitespace-nowrap">{quando(p.ultimo_ascolto)}</td>
                  </tr>
                ))}
                {!perOrd.length && <tr><td className="py-3 text-gray-500" colSpan={11}>Nessuna persona con l'account ha ascoltato nel periodo.</td></tr>}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {aperto && (
        <div className="fixed inset-0 z-40 bg-black/40 flex justify-end" onClick={() => setAperto(null)} data-testid="admin-ascolti-dettaglio">
          <div className="h-full w-full max-w-xl overflow-y-auto bg-white p-5 shadow-xl" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-start justify-between gap-3">
              <div>
                <h3 className="text-lg font-semibold text-gray-900">{aperto.tipo === 'med' ? aperto.dati.titolo : (aperto.dati.nome || aperto.dati.email || 'Persona')}</h3>
                <p className="text-xs text-gray-500">{aperto.tipo === 'med' ? `${aperto.dati.slug} · ${PERIODI.find(([v]) => v === periodo)?.[1]}` : `${aperto.dati.email || ''}${aperto.dati.iscritto_il ? ` · iscritta/o il ${giorno(aperto.dati.iscritto_il)}` : ''}`}</p>
              </div>
              <button type="button" className="rounded-full border px-3 py-1 text-sm" onClick={() => setAperto(null)}>Chiudi</button>
            </div>
            {aperto.tipo === 'med' && (
              <div className="mt-4 space-y-4">
                <div className="grid grid-cols-3 gap-2">
                  <Numero etichetta="Ascolti" valore={aperto.dati.ascolti} /><Numero etichetta="Persone" valore={aperto.dati.persone} /><Numero etichetta="Minuti" valore={aperto.dati.minuti} />
                </div>
                <div className="rounded-lg border p-3">
                  <div className="text-xs text-gray-500 mb-2">La curva: quanti arrivano a…</div>
                  <div className="space-y-1">
                    {[['q25', 'un quarto'], ['q50', 'metà'], ['q75', 'tre quarti'], ['fine', 'la fine']].map(([k, l]) => (
                      <div key={k} className="flex items-center gap-2 text-xs"><span className="w-20 text-gray-600">{l}</span><div className="flex-1 h-2 rounded bg-gray-100"><div className="h-2 rounded bg-[#2f5749]" style={{ width: pct(aperto.dati.curva?.[k]) }} /></div><span className="w-10 text-right">{pct(aperto.dati.curva?.[k])}</span></div>
                    ))}
                  </div>
                </div>
                <div>
                  <div className="text-xs text-gray-500 mb-1">Da dove si arriva</div>
                  <div className="flex flex-wrap gap-2 text-xs">{Object.entries(aperto.dati.provenienze || {}).map(([k, v]) => <span key={k} className="rounded-full border px-2 py-[2px]">{k} · {v}</span>)}</div>
                </div>
                <div>
                  <div className="text-xs text-gray-500 mb-1">Le persone</div>
                  <div className="rounded-lg border divide-y">
                    {(aperto.dati.persone_elenco || []).map((p) => (
                      <button key={p.account_id} type="button" className="w-full text-left px-3 py-2 text-sm hover:bg-gray-50" onClick={() => apriPer(p.account_id)}>
                        <span className="font-medium">{p.nome || p.email}</span> <span className="text-xs text-gray-500">· {p.ascolti} ascolti · {p.minuti} min · {p.completati} finite · ultimo {quando(p.ultimo)}</span>
                      </button>
                    ))}
                    {!(aperto.dati.persone_elenco || []).length && <div className="px-3 py-2 text-xs text-gray-500">Solo ascolti senza account.</div>}
                  </div>
                </div>
              </div>
            )}
            {aperto.tipo === 'per' && (
              <div className="mt-4 space-y-4">
                {aperto.dati.riepilogo && (
                  <div className="rounded-lg border p-3">
                    <div className="flex items-center gap-3"><span className="rounded-full bg-[#2f5749] px-3 py-1 text-sm font-semibold text-white">{aperto.dati.riepilogo.score}</span><span className="text-xs text-gray-600">score «seguito», da sempre</span></div>
                    <div className="mt-2 grid grid-cols-5 gap-1 text-[11px]">
                      {Object.entries(aperto.dati.riepilogo.parti || {}).map(([k, v]) => <div key={k}><div className="text-gray-500">{PARTI[k]}</div><div className="font-medium">{Math.round(v * 100)}%</div></div>)}
                    </div>
                    <div className="mt-2 text-xs text-gray-600">{aperto.dati.riepilogo.ascolti} ascolti · {aperto.dati.riepilogo.minuti} min · {aperto.dati.riepilogo.completati} finite · {aperto.dati.riepilogo.titoli_diversi} titoli · di solito {FASCE[aperto.dati.riepilogo.fascia_abituale] || '—'}</div>
                  </div>
                )}
                {!!aperto.dati.preferite?.length && <div className="text-xs text-gray-600"><span className="text-gray-500">Preferite:</span> {aperto.dati.preferite.map((p) => p.titolo).join(' · ')}</div>}
                {aperto.dati.riprendi && <div className="text-xs text-gray-600"><span className="text-gray-500">Riprendi aperto:</span> {aperto.dati.riprendi.slug} a {Math.round((aperto.dati.riprendi.secondo || 0) / 60)} min</div>}
                <div>
                  <div className="text-xs text-gray-500 mb-1">La linea del tempo</div>
                  <div className="rounded-lg border divide-y max-h-[50vh] overflow-y-auto" data-testid="admin-ascolti-linea">
                    {aperto.dati.linea.map((r, i) => (
                      <div key={i} className="px-3 py-2 text-sm">
                        <div className="flex justify-between gap-2"><span className="font-medium text-gray-900">{r.titolo}</span><span className="text-xs text-gray-500 whitespace-nowrap">{quando(r.at)}</span></div>
                        <div className="text-xs text-gray-500">{r.minuti} min · arrivata al {r.quartile}%{r.completata ? ' · completata' : ''} · da {r.provenienza}{r.playlist ? ` (${r.playlist})` : ''} · {FASCE[r.fascia]}</div>
                      </div>
                    ))}
                    {!aperto.dati.linea.length && <div className="px-3 py-2 text-xs text-gray-500">Nessun ascolto registrato.</div>}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </section>
  );
}
