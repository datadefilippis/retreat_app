/**
 * /accademia/nuovo — UN CORSO IN TRE GESTI (AC1, 7/10/2026).
 *   1. Il corso     titolo, due righe, prezzo, copertina, durata dell'accesso;
 *                   «Altro»: racconto completo, chi insegna
 *   2. Le lezioni   l'editor: video (upload diretto) o testo, anteprime, ordine
 *   3. Pubblica     anteprima della card + lucchetti in chiaro
 * Il corso nasce al passo 1 (cosi' le lezioni hanno un id a cui agganciarsi).
 */
import React, { useCallback, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowLeft, CheckCircle2 } from 'lucide-react';
import { toast } from 'sonner';
import { AppLayout, Header } from '../../components/Layout';
import DpaPactDialog from '../../components/legal/DpaPactDialog';
import { accademiaAPI, fmtDurata } from '../../api/accademia';
import { AnteprimaProdotto, Bottone, Campo, Ragioni, Scheda, SceltaImmagine, campo, classePasso } from '../prodotti/ui';
import LezioniEditor from './LezioniEditor';

const PASSI = [
  { key: 'corso', label: 'Il corso' },
  { key: 'lezioni', label: 'Le lezioni' },
  { key: 'pubblica', label: 'Pubblica' },
];

export default function CorsoWizard() {
  const navigate = useNavigate();
  const [passo, setPasso] = useState(0);
  const [form, setForm] = useState({ title: '', description: '', long_description: '', instructor_name: '', unit_price: '', access_policy: 'lifetime', access_expiry_days: '' });
  const [altro, setAltro] = useState(false);
  const [cover, setCover] = useState(null);
  const [corso, setCorso] = useState(null);
  const [salvando, setSalvando] = useState(false);
  const [pactOpen, setPactOpen] = useState(false);
  const [ragioni, setRagioni] = useState([]);
  const pendingRef = useRef(false);

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));
  const prezzoOk = form.unit_price !== '' && Number(form.unit_price) > 0;
  const giorniOk = form.access_policy === 'lifetime' || Number(form.access_expiry_days) > 0;
  const passo1Ok = form.title.trim().length > 0 && prezzoOk && giorniOk;

  const ricarica = useCallback(() => {
    if (!corso?.id) return;
    accademiaAPI.get(corso.id).then(res => setCorso(res.data)).catch(() => {});
  }, [corso?.id]);

  const salvaCorso = async () => {
    if (!passo1Ok || salvando) return;
    setSalvando(true);
    try {
      const payload = {
        title: form.title.trim(), description: form.description.trim() || null,
        long_description: form.long_description.trim() || null, instructor_name: form.instructor_name.trim() || null,
        unit_price: Number(form.unit_price), access_policy: form.access_policy,
        access_expiry_days: form.access_policy === 'expiring' ? Number(form.access_expiry_days) : null,
      };
      let c;
      if (corso?.id) {
        const upd = { ...payload };
        if (upd.access_expiry_days == null) upd.access_expiry_days = 0;
        c = (await accademiaAPI.update(corso.id, upd)).data;
      } else {
        c = (await accademiaAPI.create(payload)).data;
      }
      if (cover) {
        try { const res = await accademiaAPI.copertina(c.id, cover); c = { ...c, cover_image_url: res.data?.cover_image_url || c.cover_image_url }; setCover(null); }
        catch { toast.error('La copertina non è stata caricata: puoi riprovare dalla scheda.'); }
      }
      setCorso(c); setPasso(1);
    } catch (err) {
      const d = err?.response?.data?.detail;
      if (d?.code === 'DPA_REQUIRED') { pendingRef.current = true; setPactOpen(true); return; }
      toast.error(d?.message || (typeof d === 'string' && d) || 'Non sono riuscito a salvare. Riprova.');
    } finally { setSalvando(false); }
  };

  const pubblica = async () => {
    if (!corso?.id || salvando) return;
    setSalvando(true); setRagioni([]);
    try { await accademiaAPI.pubblica(corso.id); toast.success('Il corso è online sul tuo profilo.'); navigate('/accademia'); }
    catch (err) {
      const d = err?.response?.data?.detail;
      if (d?.code === 'non_pubblicabile') setRagioni(d.ragioni || []);
      else toast.error((typeof d === 'string' && d) || 'Non sono riuscito a pubblicare.');
    } finally { setSalvando(false); }
  };

  return (
    <AppLayout>
      <Header title="Nuovo corso" subtitle="Tre gesti: il corso, le lezioni, pubblica." />
      <div className="p-4 md:p-8 animate-fade-in max-w-3xl space-y-5" data-testid="wizard-corso">
        <Link to="/accademia" className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-900"><ArrowLeft className="h-4 w-4" aria-hidden /> I tuoi corsi</Link>
        <ol className="grid grid-cols-3 gap-2" aria-label="Passi">
          {PASSI.map((p, i) => (
            <li key={p.key} data-testid={`passo-${p.key}`} aria-current={i === passo ? 'step' : undefined}
                className={`flex min-h-[40px] items-center justify-center gap-1.5 rounded-full border px-2 text-xs font-semibold transition sm:text-sm ${classePasso(i, passo)}`}>
              {i < passo ? <CheckCircle2 className="h-4 w-4" aria-hidden /> : <span>{i + 1}.</span>}<span className="truncate">{p.label}</span>
            </li>
          ))}
        </ol>

        {passo === 0 && (
          <Scheda title="Il corso" sub="Quello che chi compra legge prima di decidere.">
            <div className="space-y-4">
              <Campo label="Titolo" obbligatorio>
                <input className={campo} value={form.title} maxLength={255} data-testid="corso-titolo" onChange={e => set('title', e.target.value)} placeholder="Es. Respiro consapevole in 5 giorni" />
              </Campo>
              <Campo label="Due righe per chi compra" hint="Cosa impara e a chi è pensato. Si legge sulla card del profilo.">
                <textarea className={`${campo} resize-none`} rows={2} maxLength={2000} value={form.description} onChange={e => set('description', e.target.value)} />
              </Campo>
              <div className="grid gap-4 sm:grid-cols-2">
                <Campo label="Prezzo" obbligatorio hint="Pagamento subito con carta, sul tuo conto Stripe.">
                  <div className="relative">
                    <input className={`${campo} pr-9`} type="number" inputMode="decimal" min="0.5" step="0.5" value={form.unit_price} data-testid="corso-prezzo" onChange={e => set('unit_price', e.target.value)} placeholder="49" />
                    <span className="pointer-events-none absolute inset-y-0 right-3.5 flex items-center text-sm text-gray-400">€</span>
                  </div>
                </Campo>
                <SceltaImmagine file={cover} onFile={setCover} label="Copertina (facoltativa)" />
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <Campo label="Durata dell'accesso" hint="Per quanto chi compra può seguirlo.">
                  <select className={campo} value={form.access_policy} data-testid="corso-accesso" onChange={e => set('access_policy', e.target.value)}>
                    <option value="lifetime">Per sempre</option>
                    <option value="expiring">A tempo</option>
                  </select>
                </Campo>
                {form.access_policy === 'expiring' && (
                  <Campo label="Giorni di accesso" obbligatorio hint="Es. 365 per un anno.">
                    <input className={campo} type="number" inputMode="numeric" min="1" max="3650" value={form.access_expiry_days} onChange={e => set('access_expiry_days', e.target.value)} placeholder="365" />
                  </Campo>
                )}
              </div>
              <button type="button" onClick={() => setAltro(a => !a)} className="text-sm font-medium text-[#2f5749] underline-offset-4 hover:underline">
                {altro ? 'Nascondi' : 'Altro'}: il racconto completo, chi insegna
              </button>
              {altro && (
                <div className="space-y-4 rounded-xl bg-gray-50 p-4">
                  <Campo label="Il racconto completo" hint="Vive sulla pagina del corso: cosa contiene, come è organizzato, cosa serve per seguirlo.">
                    <textarea className={`${campo} resize-y`} rows={5} maxLength={20000} value={form.long_description} data-testid="corso-racconto" onChange={e => set('long_description', e.target.value)} />
                  </Campo>
                  <Campo label="Chi insegna" hint="Se vuoto, il nome del tuo profilo.">
                    <input className={campo} value={form.instructor_name} maxLength={255} onChange={e => set('instructor_name', e.target.value)} />
                  </Campo>
                </div>
              )}
              <div className="flex justify-end border-t border-gray-100 pt-4">
                <Bottone onClick={salvaCorso} disabled={!passo1Ok || salvando} caricando={salvando} data-testid="corso-avanti-1" className="w-full sm:w-auto">Avanti: le lezioni</Bottone>
              </div>
            </div>
          </Scheda>
        )}

        {passo === 1 && corso && (
          <Scheda title="Le lezioni" sub="Un titolo, poi il video o il testo. L'ordine lo cambi con le frecce. I moduli sono facoltativi.">
            <LezioniEditor corso={corso} ricarica={ricarica} />
            <div className="mt-5 flex flex-col-reverse gap-2 border-t border-gray-100 pt-4 sm:flex-row sm:items-center sm:justify-between">
              <button type="button" onClick={() => setPasso(0)} className="min-h-[40px] text-sm text-gray-500 hover:text-gray-900">Indietro</button>
              <Bottone onClick={() => { ricarica(); setPasso(2); }} data-testid="corso-avanti-2" disabled={!corso.lezioni_count}>Avanti: pubblica</Bottone>
            </div>
          </Scheda>
        )}

        {passo === 2 && corso && (
          <Scheda title="Pubblica" sub="Così lo vedranno sul tuo profilo." data-testid="corso-anteprima">
            <div className="space-y-4">
              <div className="sm:max-w-sm">
                <AnteprimaProdotto prodotto={{ name: corso.title, description: corso.description, unit_price: corso.unit_price, image_url: corso.cover_image_url, item_type: 'digital' }}
                                   riga={`${corso.lezioni_count} lezion${corso.lezioni_count === 1 ? 'e' : 'i'}${corso.durata_totale_seconds ? ` · ${fmtDurata(corso.durata_totale_seconds)}` : ''} · ${corso.access_etichetta}`} />
              </div>
              <Ragioni ragioni={ragioni.length ? ragioni : corso.ragioni_pubblicazione} testid="corso-ragioni" />
              <div className="flex flex-col-reverse gap-2 border-t border-gray-100 pt-4 sm:flex-row sm:items-center sm:justify-between">
                <button type="button" onClick={() => setPasso(1)} className="min-h-[40px] text-sm text-gray-500 hover:text-gray-900">Indietro</button>
                <div className="flex flex-col gap-2 sm:flex-row">
                  <Bottone variante="secondario" onClick={() => { toast.success('Salvato in bozza.'); navigate('/accademia'); }}>Salva in bozza</Bottone>
                  <Bottone onClick={pubblica} disabled={salvando} caricando={salvando} data-testid="corso-pubblica">Pubblica</Bottone>
                </div>
              </div>
            </div>
          </Scheda>
        )}
      </div>
      <DpaPactDialog open={pactOpen} onOpenChange={setPactOpen} onAccepted={() => { if (pendingRef.current) { pendingRef.current = false; salvaCorso(); } }} />
    </AppLayout>
  );
}
