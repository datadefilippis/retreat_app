/**
 * /accademia/:id — UN CORSO (AC1, 7/10/2026): la scheda, le lezioni, gli
 * studenti. Pubblica/Togli nell'intestazione. La pagina pubblica del corso
 * e la sezione «Condividi» arrivano con AC3.
 */
import React, { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { AppLayout, Header } from '../../components/Layout';
import { accademiaAPI, fmtDurata } from '../../api/accademia';
import { Bottone, Campo, LinkPagina, Ragioni, Scheda, SceltaImmagine, campo } from '../prodotti/ui';
import LezioniEditor from './LezioniEditor';
import TrailerEditor from './TrailerEditor';

const STATO_STUDENTE = { attivo: 'In corso', completato: 'Completato', scaduto: 'Scaduto', revocato: 'Revocato' };

export default function CorsoPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [c, setC] = useState(null);
  const [form, setForm] = useState(null);
  const [studenti, setStudenti] = useState(null);
  const [salvando, setSalvando] = useState(false);
  const [sporco, setSporco] = useState(false);
  const [ragioni, setRagioni] = useState([]);

  const load = useCallback(() => {
    accademiaAPI.get(id).then(res => {
      setC(res.data);
      setForm(f => f && sporco ? f : {
        title: res.data.title || '', description: res.data.description || '', long_description: res.data.long_description || '',
        instructor_name: res.data.instructor_name || '', unit_price: res.data.unit_price != null ? String(res.data.unit_price) : '',
        access_policy: res.data.access_policy || 'lifetime', access_expiry_days: res.data.access_expiry_days || '',
      });
    }).catch(() => toast.error('Corso non trovato.'));
    accademiaAPI.studenti(id).then(res => setStudenti(res.data.studenti || [])).catch(() => {});
  }, [id, sporco]);
  useEffect(() => { load(); }, [load]);

  const set = (k, v) => { setForm(f => ({ ...f, [k]: v })); setSporco(true); };
  const salva = async () => {
    if (!form || salvando) return;
    setSalvando(true);
    try {
      const res = await accademiaAPI.update(id, {
        title: form.title.trim(), description: form.description, long_description: form.long_description,
        instructor_name: form.instructor_name, unit_price: form.unit_price !== '' ? Number(form.unit_price) : undefined,
        access_policy: form.access_policy, access_expiry_days: form.access_policy === 'expiring' ? Number(form.access_expiry_days || 0) : 0,
      });
      setC(res.data); setSporco(false); toast.success('Salvato.');
    } catch (err) {
      const d = err?.response?.data?.detail;
      toast.error((typeof d === 'string' && d) || d?.message || 'Non sono riuscito a salvare.');
    } finally { setSalvando(false); }
  };
  const copertina = async (f) => {
    if (!f) return;
    try { const res = await accademiaAPI.copertina(id, f); setC(x => ({ ...x, cover_image_url: res.data.cover_image_url })); toast.success('Copertina aggiornata.'); }
    catch { toast.error('La copertina non è stata caricata.'); }
  };
  const pubblica = async () => {
    setSalvando(true); setRagioni([]);
    try { const res = await accademiaAPI.pubblica(id); setC(res.data); toast.success('Online sul tuo profilo.'); }
    catch (err) { const d = err?.response?.data?.detail; if (d?.code === 'non_pubblicabile') setRagioni(d.ragioni || []); else toast.error('Non sono riuscito a pubblicare.'); }
    finally { setSalvando(false); }
  };
  const ritira = async () => {
    setSalvando(true);
    try { const res = await accademiaAPI.ritira(id); setC(res.data); toast.success('Tolto dal profilo: resta in bozza.'); }
    catch { toast.error('Non sono riuscito a ritirarlo.'); } finally { setSalvando(false); }
  };
  const revoca = async (s) => {
    const motivo = window.prompt(`Perché revochi l'accesso a ${s.email || 'questo studente'}?`, 'Rimborso');
    if (!motivo || !motivo.trim()) return;
    try { await accademiaAPI.revoca(id, s.id, motivo.trim()); toast.success('Accesso revocato.'); load(); }
    catch { toast.error('Non sono riuscito a revocare.'); }
  };

  if (!c || !form) return <AppLayout><div className="p-8"><Loader2 className="h-5 w-5 animate-spin text-gray-400" /></div></AppLayout>;

  return (
    <AppLayout>
      <Header title={c.title} subtitle={c.is_published ? 'Online sul tuo profilo' : 'Bozza: non si vede ancora'}>
        {c.is_published
          ? <Bottone variante="secondario" onClick={ritira} disabled={salvando} className="min-h-[40px]" data-testid="corso-ritira">Togli dal profilo</Bottone>
          : <Bottone onClick={pubblica} disabled={salvando} className="min-h-[40px]" data-testid="corso-pubblica">Pubblica</Bottone>}
      </Header>
      <div className="p-4 md:p-8 animate-fade-in max-w-3xl space-y-5" data-testid="corso-page">
        <Link to="/accademia" className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-900"><ArrowLeft className="h-4 w-4" aria-hidden /> I tuoi corsi</Link>
        <Ragioni ragioni={ragioni} testid="corso-ragioni" />

        <Scheda title="La scheda" sub="Quello che chi compra legge sul profilo e sulla pagina del corso.">
          <div className="space-y-4">
            <Campo label="Titolo" obbligatorio><input className={campo} value={form.title} maxLength={255} onChange={e => set('title', e.target.value)} /></Campo>
            <Campo label="Due righe per chi compra"><textarea className={`${campo} resize-none`} rows={2} maxLength={2000} value={form.description} onChange={e => set('description', e.target.value)} /></Campo>
            <Campo label="Il racconto completo" hint="Facoltativo. Vive sulla pagina del corso."><textarea className={`${campo} resize-y`} rows={5} maxLength={20000} value={form.long_description} data-testid="corso-racconto" onChange={e => set('long_description', e.target.value)} /></Campo>
            <div className="grid gap-4 sm:grid-cols-2">
              <Campo label="Prezzo" obbligatorio hint="Pagamento subito con carta, sul tuo conto Stripe.">
                <div className="relative">
                  <input className={`${campo} pr-9`} type="number" inputMode="decimal" min="0" step="0.5" value={form.unit_price} onChange={e => set('unit_price', e.target.value)} />
                  <span className="pointer-events-none absolute inset-y-0 right-3.5 flex items-center text-sm text-gray-400">€</span>
                </div>
              </Campo>
              <Campo label="Chi insegna" hint="Se vuoto, il nome del tuo profilo."><input className={campo} value={form.instructor_name} maxLength={255} onChange={e => set('instructor_name', e.target.value)} /></Campo>
              <Campo label="Durata dell'accesso">
                <select className={campo} value={form.access_policy} onChange={e => set('access_policy', e.target.value)}>
                  <option value="lifetime">Per sempre</option><option value="expiring">A tempo</option>
                </select>
              </Campo>
              {form.access_policy === 'expiring' && (
                <Campo label="Giorni di accesso" obbligatorio><input className={campo} type="number" inputMode="numeric" min="1" max="3650" value={form.access_expiry_days} onChange={e => set('access_expiry_days', e.target.value)} /></Campo>
              )}
            </div>
            <SceltaImmagine file={null} onFile={copertina} attuale={c.cover_image_url} label="Copertina" hint="Si carica subito." />
            <div className="flex items-center justify-between gap-3 border-t border-gray-100 pt-4">
              <span className="text-xs text-gray-400">{sporco ? 'Modifiche non salvate' : 'Tutto salvato'}</span>
              <Bottone onClick={salva} disabled={salvando || !sporco} caricando={salvando} data-testid="corso-salva">Salva</Bottone>
            </div>
          </div>
        </Scheda>

        <Scheda title="Le lezioni" sub={`${c.lezioni_pronte}/${c.lezioni_count} pronte${c.durata_totale_seconds ? ` · ${fmtDurata(c.durata_totale_seconds)}` : ''}. I moduli sono facoltativi.`} data-testid="corso-lezioni">
          <LezioniEditor corso={c} ricarica={load} />
        </Scheda>

        <Scheda title="Il video di presentazione" sub="Uno o due minuti, lo vedono tutti dalla pagina del corso prima di comprare. Facoltativo ma convince." data-testid="corso-trailer">
          <TrailerEditor corso={c} ricarica={load} />
        </Scheda>

        <Scheda title="Condividi" data-testid="corso-condividi">
          <LinkPagina orgSlug={c.public_slug} slug={c.slug} online={c.is_published} prefisso="corso" cosa="corso" />
          <p className="mt-3 text-xs text-gray-500">Le lezioni segnate come «anteprima gratuita» si guardano dalla pagina senza comprare: una o due bastano per far capire di cosa si tratta.</p>
        </Scheda>

        <Scheda title="Studenti" sub="Chi ha comprato il corso e a che punto è." data-testid="corso-studenti">
          {studenti == null ? <Loader2 className="h-4 w-4 animate-spin text-gray-400" /> : studenti.length === 0 ? (
            <p className="text-sm text-gray-500">Ancora nessuno studente.</p>
          ) : (
            <ul className="divide-y divide-gray-100">
              {studenti.map(s => (
                <li key={s.id} className="flex flex-wrap items-center gap-x-4 gap-y-1 py-3 text-sm" data-testid={`studente-${s.id}`}>
                  <div className="min-w-0 flex-1">
                    <p className="font-medium text-gray-900">{s.nome || s.email || 'Studente'}</p>
                    <p className="text-xs text-gray-500">{s.email}{s.ultimo_accesso ? ` · ultima volta ${new Date(s.ultimo_accesso).toLocaleDateString('it-IT')}` : ''}</p>
                  </div>
                  <div className="w-32">
                    <div className="h-2 w-full overflow-hidden rounded-full bg-gray-100"><div className="h-full bg-[#2f5749]" style={{ width: `${s.percentuale}%` }} /></div>
                    <p className="mt-0.5 text-[11px] text-gray-500">{s.lezioni_fatte}/{s.lezioni_totali} lezioni</p>
                  </div>
                  <span className={`rounded-full px-2.5 py-0.5 text-[11px] font-semibold ${s.stato === 'attivo' || s.stato === 'completato' ? 'bg-emerald-100 text-emerald-800' : 'bg-gray-100 text-gray-600'}`}>{STATO_STUDENTE[s.stato] || s.stato}</span>
                  {s.stato !== 'revocato' && <button type="button" onClick={() => revoca(s)} className="text-xs text-gray-400 hover:text-red-700">Revoca</button>}
                </li>
              ))}
            </ul>
          )}
        </Scheda>

        <button type="button" onClick={async () => {
          if (!window.confirm(`Togliere «${c.title}» dal catalogo? Chi l'ha già comprato continua a seguirlo.`)) return;
          try { await accademiaAPI.elimina(id); toast.success('Corso tolto.'); navigate('/accademia'); } catch { toast.error('Non sono riuscito a toglierlo.'); }
        }} className="text-xs text-gray-400 hover:text-red-700">Togli il corso dal catalogo</button>
      </div>
    </AppLayout>
  );
}
