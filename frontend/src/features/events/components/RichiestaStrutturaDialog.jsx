/**
 * «Cerco una struttura per un ritiro» (SR, fase 0).
 *
 * L'unica cosa che il gestionale del professionista sa delle strutture:
 * un modulo breve che manda la richiesta ad Aurya. La risposta arriva a
 * mano, da Davide e Valentina, con le strutture che conoscono.
 */
import React, { useEffect, useState } from 'react';
import { toast } from 'sonner';
import api from '../../../api/client';
import { Button } from '../../../components/ui/button';

const input = 'w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring';

export default function RichiestaStrutturaDialog({ aperto, onClose }) {
  const [f, setF] = useState({ zona: '', periodo: '', persone: '', notti: '', budget_persona: '', tipo_ritiro: '', esigenze: '' });
  const [busy, setBusy] = useState(false);
  const [fatto, setFatto] = useState(false);
  const [mie, setMie] = useState([]);

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
          <h3 className="font-heading text-lg font-bold">Cerco una struttura per un ritiro</h3>
          <button type="button" onClick={onClose} aria-label="Chiudi" className="text-gray-400 hover:text-gray-600 text-xl leading-none">×</button>
        </div>
        {fatto ? (
          <div className="space-y-3">
            <p className="text-sm">Ricevuta. La leggiamo personalmente e ti scriviamo entro pochi giorni con le strutture che conosciamo e che rispondono a quello che cerchi. Ti abbiamo mandato una ricevuta via email.</p>
            <Button onClick={onClose}>Chiudi</Button>
          </div>
        ) : (
          <form onSubmit={invia} className="space-y-3">
            <p className="text-sm text-muted-foreground">Conosciamo strutture adatte ai ritiri, viste di persona. Dicci cosa cerchi: ti rispondiamo noi, con nomi, prezzi e capienze veri.</p>
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
              {mie.map((r) => <li key={r.id}>{r.zona} · {r.periodo} · {r.persone} persone — <i>{STATI[r.stato] || r.stato}</i></li>)}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
