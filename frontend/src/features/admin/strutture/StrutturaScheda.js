/**
 * La scheda della struttura, a pagina intera (SR, fase 0): /admin/strutture/{id}.
 *
 * Una sezione per accordion, ognuna con il suo «Salva» (il PATCH e'
 * per sezione: chi compila dal telefono in visita non perde niente).
 * Le liste chiuse arrivano dallo schema dell'API: form e filtri non
 * duplicano mai una lista. Stessa scheda che in fase 1 usera' la
 * struttura dalla sua area.
 */
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { toast } from 'sonner';
import { AppLayout, Header } from '../../../components/Layout';
import { Button } from '../../../components/ui/button';
import { aggiungiStoria, caricaFoto, caricaSchema, elimina, etichetta, salva, scheda } from './api';
import { Area, Campo, Chip, Righe, SiNo, Tendina, Testo, cls } from './campi';

function Sezione({ titolo, sotto, aperta, onToggle, sporca, onSalva, salvando, children, testid }) {
  return (
    <section className="rounded-2xl border border-border bg-card" data-testid={testid}>
      <button type="button" onClick={onToggle} className="w-full flex items-center justify-between p-4 text-left">
        <span><b className="text-sm">{titolo}</b>{sotto && <span className="block text-xs text-muted-foreground">{sotto}</span>}</span>
        <span className="text-xs text-muted-foreground">{sporca ? 'modifiche non salvate' : ''} {aperta ? '▴' : '▾'}</span>
      </button>
      {aperta && (
        <div className="border-t border-border p-4 space-y-3">
          {children}
          <div className="flex items-center gap-3 pt-1">
            <Button size="sm" onClick={onSalva} disabled={!sporca || salvando} data-testid={`${testid}-salva`}>{salvando ? 'Salvo…' : 'Salva questa sezione'}</Button>
            {!sporca && <span className="text-xs text-muted-foreground">salvato</span>}
          </div>
        </div>
      )}
    </section>
  );
}

export default function StrutturaScheda() {
  const { id } = useParams();
  const [schema, setSchema] = useState(null);
  const [doc, setDoc] = useState(null);
  const [bozza, setBozza] = useState({});          // sezione → dati modificati
  const [aperte, setAperte] = useState({ identita: true });
  const [salvando, setSalvando] = useState(null);
  const [nota, setNota] = useState('');

  const carica = useCallback(async () => {
    try { const d = await scheda(id); setDoc(d); setBozza({}); }
    catch { toast.error('Scheda non trovata'); }
  }, [id]);
  useEffect(() => { caricaSchema().then(setSchema); carica(); }, [carica]);

  const L = (k) => schema?.liste?.[k] || [];
  const sez = (nome) => bozza[nome] ?? doc?.[nome] ?? {};
  const set = (nome, patch) => setBozza((b) => ({ ...b, [nome]: { ...(b[nome] ?? doc?.[nome] ?? {}), ...patch } }));
  const sporca = (nome) => bozza[nome] !== undefined;
  const toggle = (nome) => setAperte((a) => ({ ...a, [nome]: !a[nome] }));

  const salvaSezione = async (nome) => {
    setSalvando(nome);
    try {
      const d = await salva(id, { [nome]: bozza[nome] });
      setDoc(d);
      setBozza((b) => { const c = { ...b }; delete c[nome]; return c; });
      toast.success('Sezione salvata');
    } catch (err) {
      const det = err?.response?.data?.detail;
      toast.error(Array.isArray(det) ? det.join(' · ') : String(det || 'Errore nel salvataggio'));
    } finally { setSalvando(null); }
  };

  const onFoto = async (e) => {
    const file = e.target.files?.[0]; if (!file) return;
    try { await caricaFoto(id, file); toast.success('Foto caricata'); carica(); }
    catch (err) { toast.error(String(err?.response?.data?.detail || 'Foto non caricata')); }
    e.target.value = '';
  };
  const copertina = async (url) => { try { setDoc(await salva(id, { foto_copertina: url })); toast.success('Copertina impostata'); } catch { toast.error('Errore'); } };
  const togliFoto = async (url) => {
    const foto = (doc.foto || []).filter((f) => f.url !== url);
    try { setDoc(await salva(id, { foto, foto_copertina: doc.foto_copertina === url ? (foto[0]?.url || '') : doc.foto_copertina })); } catch { toast.error('Errore'); }
  };
  const visibilita = async (v) => { try { setDoc(await salva(id, { visibilita: v })); toast.success(v === 'pubblica' ? 'Scheda pubblica (la pagina arriverà con la fase 1)' : 'Scheda riservata'); } catch { toast.error('Errore'); } };
  const aggiungiNota = async () => { if (!nota.trim()) return; try { setDoc(await aggiungiStoria(id, nota.trim())); setNota(''); } catch { toast.error('Errore'); } };
  const eliminaScheda = async () => {
    if (!window.confirm('Eliminare questa struttura? Se è mai stata pubblica viene solo sospesa.')) return;
    try { const r = await elimina(id); toast.success(r.esito === 'eliminata' ? 'Eliminata' : 'Sospesa'); window.location.assign('/admin/strutture'); } catch { toast.error('Errore'); }
  };

  const derivati = doc?.derivati || {};
  const postiCalcolati = useMemo(() => (sez('ricettivita').camere || []).reduce((s, c) => s + (Number(c.quantita) || 0) * (Number(c.letti) || 0), 0), [bozza, doc]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!doc || !schema) {
    return <AppLayout><Header title="Struttura" /><div className="p-8 text-sm text-muted-foreground">Carico…</div></AppLayout>;
  }
  const idn = sez('identita'), lg = sez('luogo'), ric = sez('ricettivita'), sp = sez('spazi'), cf = sez('comfort'),
        cu = sez('cucina'), pz = sez('prezzi'), ad = sez('adatta'), dp = sez('disponibilita'), ct = sez('contatti'), rd = sez('redazione');

  return (
    <AppLayout>
      <Header title={doc.identita?.nome || 'Struttura'}
              subtitle={[etichetta(schema, 'tipi_struttura', doc.identita?.tipo), doc.luogo?.comune, doc.luogo?.regione].filter(Boolean).join(' · ')} />
      <div className="p-4 md:p-8 max-w-4xl space-y-4" data-testid="struttura-scheda">
        <div className="flex flex-wrap items-center gap-3 text-sm">
          <Link to="/admin/strutture" className="underline">← Tutte le strutture</Link>
          <span className="text-muted-foreground">·</span>
          <span>Posti letto <b>{derivati.posti_letto_totali ?? '—'}</b></span>
          <span>Da <b>{derivati.prezzo_da != null ? `${derivati.prezzo_da} €` : '—'}</b> a persona a notte</span>
          <span className="rounded-full bg-muted px-2 py-0.5 text-xs">{etichetta(schema, 'stati_pipeline', derivati.stato_pipeline)}</span>
          <label className="ml-auto flex items-center gap-2 text-xs">
            <span>Visibilità</span>
            <select value={doc.visibilita} onChange={(e) => visibilita(e.target.value)} className="rounded-md border border-input bg-background px-2 py-1" data-testid="struttura-visibilita">
              {L('visibilita').map((o) => <option key={o.valore} value={o.valore}>{o.etichetta}</option>)}
            </select>
          </label>
        </div>

        <Sezione titolo="1 · Identità e foto" sotto="nome, tipo, descrizione pubblicabile, sito, foto" aperta={!!aperte.identita} onToggle={() => toggle('identita')} sporca={sporca('identita')} onSalva={() => salvaSezione('identita')} salvando={salvando === 'identita'} testid="sez-identita">
          <div className={cls.riga}>
            <Campo label="Nome"><Testo value={idn.nome} onChange={(v) => set('identita', { nome: v })} /></Campo>
            <Campo label="Tipo"><Tendina value={idn.tipo} onChange={(v) => set('identita', { tipo: v })} opzioni={L('tipi_struttura')} /></Campo>
            <Campo label="Sito web"><Testo value={idn.sito} onChange={(v) => set('identita', { sito: v })} placeholder="https://…" /></Campo>
            <Campo label="Descrizione" hint="pubblicabile: com'è il posto, per chi" wide><Area value={idn.descrizione} onChange={(v) => set('identita', { descrizione: v })} rows={5} /></Campo>
          </div>
          <div>
            <p className={cls.label}>Foto ({(doc.foto || []).length}/20)</p>
            <div className="flex flex-wrap gap-2">
              {(doc.foto || []).map((f) => (
                <div key={f.url} className={`relative h-24 w-32 overflow-hidden rounded-lg border ${doc.foto_copertina === f.url ? 'border-primary ring-2 ring-primary/30' : 'border-border'}`}>
                  <img src={f.url} alt="" className="h-full w-full object-cover" />
                  <div className="absolute inset-x-0 bottom-0 flex justify-between bg-black/50 px-1 py-0.5 text-[10px] text-white">
                    <button type="button" onClick={() => copertina(f.url)}>{doc.foto_copertina === f.url ? 'copertina' : 'usa'}</button>
                    <button type="button" onClick={() => togliFoto(f.url)}>togli</button>
                  </div>
                </div>
              ))}
              <label className="flex h-24 w-32 cursor-pointer items-center justify-center rounded-lg border border-dashed border-primary text-xs text-primary">
                + Foto<input type="file" accept="image/*" onChange={onFoto} className="hidden" data-testid="struttura-foto-input" />
              </label>
            </div>
          </div>
        </Sezione>

        <Sezione titolo="2 · Luogo" sotto="indirizzo, regione, come si arriva, contesto, silenzio" aperta={!!aperte.luogo} onToggle={() => toggle('luogo')} sporca={sporca('luogo')} onSalva={() => salvaSezione('luogo')} salvando={salvando === 'luogo'} testid="sez-luogo">
          <div className={cls.riga}>
            <Campo label="Indirizzo" wide><Testo value={lg.indirizzo} onChange={(v) => set('luogo', { indirizzo: v })} /></Campo>
            <Campo label="Comune"><Testo value={lg.comune} onChange={(v) => set('luogo', { comune: v })} /></Campo>
            <Campo label="Provincia" hint="sigla"><Testo value={lg.provincia} onChange={(v) => set('luogo', { provincia: v })} maxLength={4} /></Campo>
            <Campo label="Regione"><Tendina value={lg.regione} onChange={(v) => set('luogo', { regione: v })} opzioni={schema.regioni} /></Campo>
            <Campo label="CAP"><Testo value={lg.cap} onChange={(v) => set('luogo', { cap: v })} /></Campo>
            <Campo label="Latitudine"><Testo type="number" step="any" value={lg.latitudine} onChange={(v) => set('luogo', { latitudine: v })} /></Campo>
            <Campo label="Longitudine"><Testo type="number" step="any" value={lg.longitudine} onChange={(v) => set('luogo', { longitudine: v })} /></Campo>
            <Campo label="Stazione più vicina (km)"><Testo type="number" value={lg.stazione_km} onChange={(v) => set('luogo', { stazione_km: v })} /></Campo>
            <Campo label="Aeroporto più vicino (km)"><Testo type="number" value={lg.aeroporto_km} onChange={(v) => set('luogo', { aeroporto_km: v })} /></Campo>
            <Campo label="Silenzio" hint="1 rumoroso · 5 totale"><Tendina value={lg.silenzio} onChange={(v) => set('luogo', { silenzio: v ? Number(v) : null })} opzioni={[1, 2, 3, 4, 5].map((n) => ({ valore: n, etichetta: String(n) }))} /></Campo>
            <SiNo label="Raggiungibile senza auto" value={lg.raggiungibile_senza_auto} onChange={(v) => set('luogo', { raggiungibile_senza_auto: v })} />
            <Campo label="Come si arriva" wide><Area value={lg.come_si_arriva} onChange={(v) => set('luogo', { come_si_arriva: v })} /></Campo>
            <Campo label="Contesto" wide><Chip value={lg.contesto || []} onChange={(v) => set('luogo', { contesto: v })} opzioni={L('contesti')} /></Campo>
          </div>
        </Sezione>

        <Sezione titolo="3 · Ricettività" sotto={`camere per tipologia, letti, bagni · posti letto calcolati: ${postiCalcolati}`} aperta={!!aperte.ricettivita} onToggle={() => toggle('ricettivita')} sporca={sporca('ricettivita')} onSalva={() => salvaSezione('ricettivita')} salvando={salvando === 'ricettivita'} testid="sez-ricettivita">
          <Righe righe={ric.camere || []} onChange={(v) => set('ricettivita', { camere: v })} nomeRiga="tipologia di camera"
                 vuota={{ tipologia: 'doppia', quantita: 1, letti: 2, tipo_letti: null, bagno: null, note: null }}
                 render={(r, setR) => (
                   <div className={cls.riga}>
                     <Campo label="Tipologia"><Tendina value={r.tipologia} onChange={(v) => setR({ tipologia: v })} opzioni={L('tipologie_camera')} vuoto="scegli" /></Campo>
                     <Campo label="Quante camere così"><Testo type="number" min="1" value={r.quantita} onChange={(v) => setR({ quantita: v })} /></Campo>
                     <Campo label="Letti per camera"><Testo type="number" min="1" value={r.letti} onChange={(v) => setR({ letti: v })} /></Campo>
                     <Campo label="Tipo di letti"><Tendina value={r.tipo_letti} onChange={(v) => setR({ tipo_letti: v })} opzioni={L('tipi_letto')} /></Campo>
                     <Campo label="Bagno"><Tendina value={r.bagno} onChange={(v) => setR({ bagno: v })} opzioni={L('bagno')} /></Campo>
                     <Campo label="Note"><Testo value={r.note} onChange={(v) => setR({ note: v })} /></Campo>
                   </div>
                 )} />
          <div className={cls.riga}>
            <Campo label="Posti letto dichiarati" hint="se diverso dal calcolo"><Testo type="number" value={ric.posti_letto_dichiarati} onChange={(v) => set('ricettivita', { posti_letto_dichiarati: v })} /></Campo>
            <Campo label="Bagni totali"><Testo type="number" value={ric.bagni_totali} onChange={(v) => set('ricettivita', { bagni_totali: v })} /></Campo>
            <Campo label="Persone minime per un gruppo"><Testo type="number" value={ric.persone_min} onChange={(v) => set('ricettivita', { persone_min: v })} /></Campo>
            <Campo label="Persone massime"><Testo type="number" value={ric.persone_max} onChange={(v) => set('ricettivita', { persone_max: v })} /></Campo>
            <SiNo label="Accetta letti condivisi" value={ric.accetta_letti_condivisi} onChange={(v) => set('ricettivita', { accetta_letti_condivisi: v })} />
            <SiNo label="Uso esclusivo possibile" value={ric.uso_esclusivo_possibile} onChange={(v) => set('ricettivita', { uso_esclusivo_possibile: v })} />
          </div>
        </Sezione>

        <Sezione titolo="4 · Spazi di pratica" sotto="sale con metri quadri e comfort, spazi esterni" aperta={!!aperte.spazi} onToggle={() => toggle('spazi')} sporca={sporca('spazi')} onSalva={() => salvaSezione('spazi')} salvando={salvando === 'spazi'} testid="sez-spazi">
          <p className={cls.label}>Sale</p>
          <Righe righe={sp.sale || []} onChange={(v) => set('spazi', { sale: v })} nomeRiga="sala"
                 vuota={{ nome: null, mq: null, altezza_m: null, pavimento: null, capienza_persone: null, riscaldata: null, climatizzata: null, luce_naturale: null, attrezzata: [], note: null }}
                 render={(r, setR) => (
                   <div className={cls.riga}>
                     <Campo label="Nome"><Testo value={r.nome} onChange={(v) => setR({ nome: v })} placeholder="es. Sala a volta" /></Campo>
                     <Campo label="Metri quadri"><Testo type="number" value={r.mq} onChange={(v) => setR({ mq: v })} /></Campo>
                     <Campo label="Altezza (m)"><Testo type="number" step="0.1" value={r.altezza_m} onChange={(v) => setR({ altezza_m: v })} /></Campo>
                     <Campo label="Pavimento"><Tendina value={r.pavimento} onChange={(v) => setR({ pavimento: v })} opzioni={L('pavimenti')} /></Campo>
                     <Campo label="Capienza (persone in pratica)"><Testo type="number" value={r.capienza_persone} onChange={(v) => setR({ capienza_persone: v })} /></Campo>
                     <SiNo label="Riscaldata" value={r.riscaldata} onChange={(v) => setR({ riscaldata: v })} />
                     <SiNo label="Climatizzata" value={r.climatizzata} onChange={(v) => setR({ climatizzata: v })} />
                     <SiNo label="Luce naturale" value={r.luce_naturale} onChange={(v) => setR({ luce_naturale: v })} />
                     <Campo label="Attrezzata con" wide><Chip value={r.attrezzata || []} onChange={(v) => setR({ attrezzata: v })} opzioni={L('attrezzature_sala')} /></Campo>
                     <Campo label="Note" wide><Testo value={r.note} onChange={(v) => setR({ note: v })} /></Campo>
                   </div>
                 )} />
          <p className={cls.label}>Spazi esterni</p>
          <Righe righe={sp.spazi_esterni || []} onChange={(v) => set('spazi', { spazi_esterni: v })} nomeRiga="spazio esterno"
                 vuota={{ tipo: 'prato', mq: null, ombra: null, adatto_pratica: null, note: null }}
                 render={(r, setR) => (
                   <div className={cls.riga}>
                     <Campo label="Tipo"><Tendina value={r.tipo} onChange={(v) => setR({ tipo: v })} opzioni={L('tipi_spazio_esterno')} vuoto="scegli" /></Campo>
                     <Campo label="Metri quadri"><Testo type="number" value={r.mq} onChange={(v) => setR({ mq: v })} /></Campo>
                     <SiNo label="Ombra" value={r.ombra} onChange={(v) => setR({ ombra: v })} />
                     <SiNo label="Adatto alla pratica" value={r.adatto_pratica} onChange={(v) => setR({ adatto_pratica: v })} />
                     <Campo label="Note" wide><Testo value={r.note} onChange={(v) => setR({ note: v })} /></Campo>
                   </div>
                 )} />
        </Sezione>

        <Sezione titolo="5 · Comfort e servizi" sotto="aria condizionata, piscina, wifi, parcheggio, accessibilità" aperta={!!aperte.comfort} onToggle={() => toggle('comfort')} sporca={sporca('comfort')} onSalva={() => salvaSezione('comfort')} salvando={salvando === 'comfort'} testid="sez-comfort">
          <div className={cls.riga}>
            <Campo label="Aria condizionata"><Tendina value={cf.aria_condizionata} onChange={(v) => set('comfort', { aria_condizionata: v })} opzioni={L('aria_condizionata')} /></Campo>
            <Campo label="Piscina"><Tendina value={cf.piscina} onChange={(v) => set('comfort', { piscina: v })} opzioni={L('piscina')} /></Campo>
            <Campo label="Wifi"><Tendina value={cf.wifi} onChange={(v) => set('comfort', { wifi: v })} opzioni={L('wifi')} /></Campo>
            <SiNo label="Riscaldamento" value={cf.riscaldamento} onChange={(v) => set('comfort', { riscaldamento: v })} />
            <SiNo label="Sauna" value={cf.sauna} onChange={(v) => set('comfort', { sauna: v })} />
            <SiNo label="Vasca idromassaggio" value={cf.vasca_idromassaggio} onChange={(v) => set('comfort', { vasca_idromassaggio: v })} />
            <Campo label="Parcheggio (posti)"><Testo type="number" value={cf.parcheggio_posti} onChange={(v) => set('comfort', { parcheggio_posti: v })} /></Campo>
            <SiNo label="Accessibile a persone con disabilità" value={cf.accessibile_disabili} onChange={(v) => set('comfort', { accessibile_disabili: v })} />
            <SiNo label="Animali ammessi" value={cf.animali} onChange={(v) => set('comfort', { animali: v })} />
            <SiNo label="Lavanderia" value={cf.lavanderia} onChange={(v) => set('comfort', { lavanderia: v })} />
            <Campo label="Altri servizi" hint="separati da virgola" wide><Testo value={(cf.altri_servizi || []).join(', ')} onChange={(v) => set('comfort', { altri_servizi: (v || '').split(',').map((x) => x.trim()).filter(Boolean) })} /></Campo>
          </div>
        </Sezione>

        <Sezione titolo="6 · Cucina" sotto="chi cucina, regimi, pasti inclusi" aperta={!!aperte.cucina} onToggle={() => toggle('cucina')} sporca={sporca('cucina')} onSalva={() => salvaSezione('cucina')} salvando={salvando === 'cucina'} testid="sez-cucina">
          <div className={cls.riga}>
            <Campo label="Cucina"><Tendina value={cu.cucina} onChange={(v) => set('cucina', { cucina: v })} opzioni={L('cucina')} /></Campo>
            <Campo label="Pasti inclusi"><Tendina value={cu.pasti_inclusi} onChange={(v) => set('cucina', { pasti_inclusi: v })} opzioni={L('pasti')} /></Campo>
            <SiNo label="Prodotti propri" value={cu.prodotti_propri} onChange={(v) => set('cucina', { prodotti_propri: v })} />
            <Campo label="Regimi possibili" wide><Chip value={cu.regimi || []} onChange={(v) => set('cucina', { regimi: v })} opzioni={L('regimi')} /></Campo>
            <Campo label="Note" wide><Area value={cu.note} onChange={(v) => set('cucina', { note: v })} /></Campo>
          </div>
        </Sezione>

        <Sezione titolo="7 · Prezzi" sotto={`stagioni e tariffe, affitto esclusivo, minimi, acconto · da ${derivati.prezzo_da != null ? `${derivati.prezzo_da} €` : '—'} a persona a notte`} aperta={!!aperte.prezzi} onToggle={() => toggle('prezzi')} sporca={sporca('prezzi')} onSalva={() => salvaSezione('prezzi')} salvando={salvando === 'prezzi'} testid="sez-prezzi">
          <p className={cls.label}>Stagioni</p>
          <Righe righe={pz.stagioni || []} onChange={(v) => set('prezzi', { stagioni: v })} nomeRiga="stagione"
                 vuota={{ nome: 'bassa', dal: null, al: null, tariffe: [{ base: 'persona_notte', tipologia_camera: null, trattamento: 'pensione_completa', prezzo: null }] }}
                 render={(st, setSt) => (
                   <div className="space-y-3">
                     <div className={cls.riga}>
                       <Campo label="Nome stagione"><Testo value={st.nome} onChange={(v) => setSt({ nome: v || '' })} placeholder="bassa, media, alta" /></Campo>
                       <Campo label="Dal" hint="MM-GG, ogni anno"><Testo value={st.dal} onChange={(v) => setSt({ dal: v })} placeholder="06-01" /></Campo>
                       <Campo label="Al" hint="MM-GG"><Testo value={st.al} onChange={(v) => setSt({ al: v })} placeholder="09-30" /></Campo>
                     </div>
                     <p className={cls.label}>Tariffe di questa stagione</p>
                     <Righe righe={st.tariffe || []} onChange={(v) => setSt({ tariffe: v })} nomeRiga="tariffa"
                            vuota={{ base: 'persona_notte', tipologia_camera: null, trattamento: null, prezzo: null }}
                            render={(t, setT) => (
                              <div className={cls.riga}>
                                <Campo label="Base"><Tendina value={t.base} onChange={(v) => setT({ base: v })} opzioni={L('basi_tariffa')} vuoto="scegli" /></Campo>
                                <Campo label="Tipologia camera" hint="vuoto = tutte"><Tendina value={t.tipologia_camera} onChange={(v) => setT({ tipologia_camera: v })} opzioni={L('tipologie_camera')} vuoto="tutte" /></Campo>
                                <Campo label="Trattamento"><Tendina value={t.trattamento} onChange={(v) => setT({ trattamento: v })} opzioni={L('trattamenti')} /></Campo>
                                <Campo label="Prezzo (€)"><Testo type="number" min="0" step="0.5" value={t.prezzo} onChange={(v) => setT({ prezzo: v })} /></Campo>
                              </div>
                            )} />
                   </div>
                 )} />
          <div className={cls.riga}>
            <Campo label="Affitto esclusivo a notte (€)"><Testo type="number" value={pz.affitto_esclusivo_notte} onChange={(v) => set('prezzi', { affitto_esclusivo_notte: v })} /></Campo>
            <Campo label="Minimo notti"><Testo type="number" value={pz.minimo_notti} onChange={(v) => set('prezzi', { minimo_notti: v })} /></Campo>
            <Campo label="Minimo persone"><Testo type="number" value={pz.minimo_persone} onChange={(v) => set('prezzi', { minimo_persone: v })} /></Campo>
            <Campo label="Acconto (%)"><Testo type="number" min="0" max="100" value={pz.acconto_percento} onChange={(v) => set('prezzi', { acconto_percento: v })} /></Campo>
            <SiNo label="Tassa di soggiorno" value={pz.tassa_soggiorno} onChange={(v) => set('prezzi', { tassa_soggiorno: v })} />
            <Campo label="Tassa di soggiorno (€ a persona a notte)"><Testo type="number" step="0.5" value={pz.tassa_soggiorno_importo} onChange={(v) => set('prezzi', { tassa_soggiorno_importo: v })} /></Campo>
            <Campo label="Politica di cancellazione" wide><Area value={pz.cancellazione} onChange={(v) => set('prezzi', { cancellazione: v })} /></Campo>
            <Campo label="Note sui prezzi" wide><Area value={pz.note} onChange={(v) => set('prezzi', { note: v })} rows={2} /></Campo>
          </div>
        </Sezione>

        <Sezione titolo="8 · Adatta a" sotto="per quali ritiri va bene, esperienza" aperta={!!aperte.adatta} onToggle={() => toggle('adatta')} sporca={sporca('adatta')} onSalva={() => salvaSezione('adatta')} salvando={salvando === 'adatta'} testid="sez-adatta">
          <Campo label="Adatta a" wide><Chip value={ad.adatta_a || []} onChange={(v) => set('adatta', { adatta_a: v })} opzioni={L('adatta_a')} /></Campo>
          <div className={cls.riga}>
            <Campo label="Esperienza con i ritiri"><Tendina value={ad.esperienza_ritiri} onChange={(v) => set('adatta', { esperienza_ritiri: v })} opzioni={L('esperienza_ritiri')} /></Campo>
            <Campo label="Ritiri ospitati, note" wide><Area value={ad.ritiri_ospitati_note} onChange={(v) => set('adatta', { ritiri_ospitati_note: v })} rows={2} /></Campo>
          </div>
        </Sezione>

        <Sezione titolo="9 · Disponibilità" sotto="apertura, mesi di chiusura" aperta={!!aperte.disponibilita} onToggle={() => toggle('disponibilita')} sporca={sporca('disponibilita')} onSalva={() => salvaSezione('disponibilita')} salvando={salvando === 'disponibilita'} testid="sez-disponibilita">
          <div className={cls.riga}>
            <Campo label="Apertura"><Tendina value={dp.stagionalita} onChange={(v) => set('disponibilita', { stagionalita: v })} opzioni={L('stagionalita')} /></Campo>
            <Campo label="Mesi di chiusura" wide><Chip value={dp.chiusura_mesi || []} onChange={(v) => set('disponibilita', { chiusura_mesi: v })} opzioni={L('mesi')} /></Campo>
            <Campo label="Note" wide><Area value={dp.note} onChange={(v) => set('disponibilita', { note: v })} rows={2} /></Campo>
          </div>
        </Sezione>

        <Sezione titolo="10 · Contatti" sotto="referente, telefono, email · mai pubblici" aperta={!!aperte.contatti} onToggle={() => toggle('contatti')} sporca={sporca('contatti')} onSalva={() => salvaSezione('contatti')} salvando={salvando === 'contatti'} testid="sez-contatti">
          <div className={cls.riga}>
            <Campo label="Referente"><Testo value={ct.referente} onChange={(v) => set('contatti', { referente: v })} /></Campo>
            <Campo label="Ruolo"><Testo value={ct.ruolo} onChange={(v) => set('contatti', { ruolo: v })} placeholder="proprietaria, gestore" /></Campo>
            <Campo label="Preferisce"><Tendina value={ct.preferisce} onChange={(v) => set('contatti', { preferisce: v })} opzioni={L('preferenza_contatto')} /></Campo>
            <Campo label="Telefono"><Testo value={ct.telefono} onChange={(v) => set('contatti', { telefono: v })} /></Campo>
            <Campo label="Email"><Testo type="email" value={ct.email} onChange={(v) => set('contatti', { email: v })} /></Campo>
          </div>
        </Sezione>

        <Sezione titolo="11 · Redazione" sotto="stato del contatto, visita, giudizio, storia · solo voi" aperta={!!aperte.redazione} onToggle={() => toggle('redazione')} sporca={sporca('redazione')} onSalva={() => salvaSezione('redazione')} salvando={salvando === 'redazione'} testid="sez-redazione">
          <div className={cls.riga}>
            <Campo label="Stato"><Tendina value={rd.stato_pipeline} onChange={(v) => set('redazione', { stato_pipeline: v })} opzioni={L('stati_pipeline')} /></Campo>
            <Campo label="Visitata da"><Testo value={rd.visitata_da} onChange={(v) => set('redazione', { visitata_da: v })} /></Campo>
            <Campo label="Visitata il" hint="AAAA-MM-GG"><Testo value={rd.visitata_il} onChange={(v) => set('redazione', { visitata_il: v })} placeholder="2026-09-20" /></Campo>
            <Campo label="Giudizio" hint="1-5"><Tendina value={rd.giudizio} onChange={(v) => set('redazione', { giudizio: v ? Number(v) : null })} opzioni={[1, 2, 3, 4, 5].map((n) => ({ valore: n, etichetta: '★'.repeat(n) }))} /></Campo>
            <Campo label="Prossimo passo" wide><Testo value={rd.prossimo_passo} onChange={(v) => set('redazione', { prossimo_passo: v })} /></Campo>
            <Campo label="Punti forti" wide><Area value={rd.punti_forti} onChange={(v) => set('redazione', { punti_forti: v })} /></Campo>
            <Campo label="Punti deboli" wide><Area value={rd.punti_deboli} onChange={(v) => set('redazione', { punti_deboli: v })} /></Campo>
          </div>
          <div className="rounded-lg border border-border p-3">
            <p className={cls.label}>Storia dei contatti</p>
            <div className="flex gap-2">
              <input value={nota} onChange={(e) => setNota(e.target.value)} placeholder="es. Chiamata con Anna: disponibile a ottobre, manda listino" className={cls.input} data-testid="struttura-storia-nota" />
              <Button size="sm" onClick={aggiungiNota} disabled={!nota.trim()} data-testid="struttura-storia-aggiungi">Aggiungi</Button>
            </div>
            <ul className="mt-3 space-y-1 text-sm">
              {(doc.storia || []).map((v, i) => <li key={i}><span className="text-xs text-muted-foreground">{v.quando} · {v.chi}</span> — {v.nota}</li>)}
              {(doc.storia || []).length === 0 && <li className="text-xs text-muted-foreground">Ancora nessuna nota.</li>}
            </ul>
          </div>
        </Sezione>

        <div className="flex items-center justify-between pt-2 text-xs text-muted-foreground">
          <span>Creata il {(doc.creato_il || '').slice(0, 10)} da {doc.creato_da} · aggiornata il {(doc.aggiornato_il || '').slice(0, 10)} · slug futuro <code>/strutture/{doc.slug}</code></span>
          <button type="button" onClick={eliminaScheda} className="underline text-red-700" data-testid="struttura-elimina">Elimina</button>
        </div>
      </div>
    </AppLayout>
  );
}
