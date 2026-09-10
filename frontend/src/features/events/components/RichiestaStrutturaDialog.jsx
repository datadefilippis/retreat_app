/**
 * «Cerco una struttura per un ritiro» (SR, fase 0) e «Chiedi la regia»
 * (P13, 10/9/2026, piano di business §3.1 A).
 *
 * L'unica cosa che il gestionale del professionista sa delle strutture:
 * un modulo breve che manda la richiesta ad Aurya. La risposta arriva a
 * mano, da Davide e Valentina, con le strutture che conoscono.
 *
 * P13: la stessa scheda, con un secondo tipo, chiede la REGIA del
 * ritiro — le due formule del piano (leggera 290 €, completa 690 € +
 * 40 € a partecipante oltre il sesto; la prima, in ottobre 2026, e' un
 * pilota a meta' prezzo). Stessi campi, un tipo e una formula in piu'.
 */
import React, { useEffect, useState } from 'react';
import { toast } from 'sonner';
import api from '../../../api/client';
import { Button } from '../../../components/ui/button';

const input = 'w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring';

const TIPI = { struttura: 'struttura', regia: 'regia', team_building: 'team building' };

export default function RichiestaStrutturaDialog({ aperto, onClose, tipoIniziale = 'struttura' }) {
  const [tipo, setTipo] = useState(tipoIniziale);
  const [formula, setFormula] = useState('non_so');
  const [f, setF] = useState({ zona: '', periodo: '', persone: '', notti: '', budget_persona: '', tipo_ritiro: '', esigenze: '' });
  const [busy, setBusy] = useState(false);
  const [fatto, setFatto] = useState(false);
  const [mie, setMie] = useState([]);

  useEffect(() => { if (aperto) { setTipo(tipoIniziale); setFatto(false); } }, [aperto, tipoIniziale]);
  useEffect(() => {
    if (!aperto) return;
    api.get('/strutture/richieste/mie').then((r) => setMie(r.data.righe || [])).catch(() => {});
  }, [aperto, fatto]);

  if (!aperto) return null;
  const set = (k, v) => setF((x) => ({ ...x, [k]: v }));
  const invia = async (e) => {
    e.preventDefault();
    if (!f.zona.trim() || !f.periodo.trim() || !f.persone) { toast.error('Servono zona, periodo e persone'); return; }
    setBusy(true);
    try {
      await api.post('/strutture/richieste', {
        zona: f.zona.trim(), periodo: f.periodo.trim(), persone: Number(f.persone),
        notti: f.notti ? Number(f.notti) : null, budget_persona: f.budget_persona ? Number(f.budget_persona) : null,
        tipo_ritiro: f.tipo_ritiro || null, esigenze: f.esigenze || null,
        tipo, formula: tipo === 'regia' ? formula : null,
      });
      setFatto(true);
    } catch (err) {
      toast.error(String(err?.response?.data?.detail || 'Richiesta non inviata, riprova'));
    } finally { setBusy(false); }
  };
  const STATI = { nuova: 'ricevuta', in_lavorazione: 'in lavorazione', proposta: 'proposta pronta', chiusa: 'chiusa' };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" role="dialog" aria-modal="true" data-testid="richiesta-struttura">
      <div className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-xl max-h-[92vh] overflow-y-auto">
        <div className="flex items-start justify-between mb-2">
          <h3 className="font-heading text-lg font-bold">{tipo === 'regia' ? 'Chiedi la regia del tuo ritiro' : 'Cerco una struttura per un ritiro'}</h3>
          <button type="button" onClick={onClose} aria-label="Chiudi" className="text-gray-400 hover:text-gray-600 text-xl leading-none">×</button>
        </div>
        {fatto ? (
          <div className="space-y-3">
            <p className="text-sm">{tipo === 'regia'
              ? 'Ricevuta. La leggiamo personalmente e ti scriviamo entro pochi giorni con una proposta chiara: cosa facciamo noi, cosa resta a te, quanto costa. Ti abbiamo mandato una ricevuta via email.'
              : 'Ricevuta. La leggiamo personalmente e ti scriviamo entro pochi giorni con le strutture che conosciamo e che rispondono a quello che cerchi. Ti abbiamo mandato una ricevuta via email.'}</p>
            <Button onClick={onClose}>Chiudi</Button>
          </div>
        ) : (
          <form onSubmit={invia} className="space-y-3">
            <div className="flex gap-2" role="tablist">
              {[['struttura', 'Cerco una struttura'], ['regia', 'Chiedi la regia']].map(([v, t]) => (
                <button key={v} type="button" role="tab" aria-selected={tipo === v} onClick={() => setTipo(v)}
                        data-testid={`richiesta-tab-${v}`}
                        className={`rounded-full border px-3 py-1 text-xs ${tipo === v ? 'border-[#2f5749] bg-[#2f5749] text-white' : 'border-border text-muted-foreground'}`}>
                  {t}
                </button>
              ))}
            </div>
            {tipo === 'regia' ? (
              <div className="space-y-2" data-testid="richiesta-regia-intro">
                <p className="text-sm text-muted-foreground">Ti organizziamo noi il ritiro: la struttura, la scheda, le persone. Due formule, prezzo fisso.</p>
                <ul className="text-sm space-y-1">
                  <li><b>Regia leggera, 290 €</b>: tre strutture proposte dalla nostra scheda, con condizioni e contatto; la scheda del ritiro scritta insieme; il piano di promozione.</li>
                  <li><b>Regia completa, 690 €</b> + 40 € a partecipante oltre il sesto: tutto sopra, più programma e prezzo costruiti insieme, caparre e iscrizioni gestite da noi col bonifico, il riempimento. Dal 2027.</li>
                </ul>
                <p className="text-xs text-muted-foreground">La prima regia, in ottobre 2026, è un pilota a metà prezzo.</p>
                <label className="block"><span className="block text-xs text-muted-foreground mb-1">Formula</span>
                  <select value={formula} onChange={(e) => setFormula(e.target.value)} className={input} data-testid="richiesta-formula">
                    <option value="non_so">Non lo so ancora</option>
                    <option value="leggera">Regia leggera (290 €)</option>
                    <option value="completa">Regia completa (690 € + 40 € a partecipante oltre il sesto)</option>
                  </select></label>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">Conosciamo strutture adatte ai ritiri, viste di persona. Dicci cosa cerchi: ti rispondiamo noi, con nomi, prezzi e capienze veri.</p>
            )}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <label className="block sm:col-span-2"><span className="block text-xs text-muted-foreground mb-1">Zona o regione</span><input value={f.zona} onChange={(e) => set('zona', e.target.value)} placeholder="es. Puglia, o «entro 2 ore da Milano»" className={input} required /></label>
              <label className="block"><span className="block text-xs text-muted-foreground mb-1">Periodo</span><input value={f.periodo} onChange={(e) => set('periodo', e.target.value)} placeholder="es. fine ottobre 2026" className={input} required /></label>
              <label className="block"><span className="block text-xs text-muted-foreground mb-1">Persone</span><input type="number" min="1" value={f.persone} onChange={(e) => set('persone', e.target.value)} className={input} required /></label>
              <label className="block"><span className="block text-xs text-muted-foreground mb-1">Notti</span><input type="number" min="1" value={f.notti} onChange={(e) => set('notti', e.target.value)} className={input} /></label>
              <label className="block"><span className="block text-xs text-muted-foreground mb-1">Budget a persona (€, soggiorno)</span><input type="number" min="0" value={f.budget_persona} onChange={(e) => set('budget_persona', e.target.value)} className={input} /></label>
              <label className="block sm:col-span-2"><span className="block text-xs text-muted-foreground mb-1">Tipo di ritiro</span><input value={f.tipo_ritiro} onChange={(e) => set('tipo_ritiro', e.target.value)} placeholder="es. yoga e meditazione" className={input} /></label>
              <label className="block sm:col-span-2"><span className="block text-xs text-muted-foreground mb-1">Esigenze</span><textarea rows={3} value={f.esigenze} onChange={(e) => set('esigenze', e.target.value)} placeholder="sala coperta, cucina vegana, camere singole, silenzio…" className={input} /></label>
            </div>
            <Button type="submit" disabled={busy} data-testid="richiesta-struttura-invia">{busy ? 'Invio…' : 'Manda la richiesta'}</Button>
          </form>
        )}
        {mie.length > 0 && (
          <div className="mt-5 border-t border-border pt-3">
            <p className="text-xs font-semibold text-muted-foreground mb-1">Le tue richieste</p>
            <ul className="space-y-1 text-sm">
              {mie.map((r) => <li key={r.id}>{TIPI[r.tipo] || 'struttura'} · {r.zona} · {r.periodo} · {r.persone} persone — <i>{STATI[r.stato] || r.stato}</i></li>)}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
