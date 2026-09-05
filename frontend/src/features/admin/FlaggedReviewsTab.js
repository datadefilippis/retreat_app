/**
 * FlaggedReviewsTab — la coda delle recensioni segnalate (RV5, 5/9/2026).
 *
 * Un professionista segnala un abuso dalla sua plancia: la recensione
 * esce dal pubblico e arriva qui. Il system admin la rilegge e decide:
 * «Ripubblica» (nessuna violazione: torna sul profilo) o «Rimuovi»
 * (resta a DB per l'audit, mai piu' resa). In entrambi i casi il
 * professionista riceve l'esito via email: nessuna segnalazione nel
 * vuoto. Prima (PR3) segnalare era un log e basta.
 */
import React, { useCallback, useEffect, useState } from 'react';
import { RefreshCw, ShieldAlert } from 'lucide-react';
import { toast } from 'sonner';
import api from '../../api/client';
import { Button } from '../../components/ui/button';

function fmt(iso) {
  if (!iso) return 'data non registrata';          // segnalate prima di RV5
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return String(iso).slice(0, 10);
  return d.toLocaleDateString('it-IT', { day: 'numeric', month: 'short', year: 'numeric' });
}

function Riga({ r, onResolve }) {
  const [note, setNote] = useState('');
  const [busy, setBusy] = useState(false);
  const decidi = async (action) => {
    setBusy(true);
    try { await onResolve(r.id, action, note); } finally { setBusy(false); }
  };
  return (
    <article className="rounded-2xl border border-border bg-card p-4" data-testid="flagged-review">
      <div className="flex flex-wrap items-baseline justify-between gap-2 text-sm">
        <span><b>{r.org_name || r.org_slug}</b>
          {r.org_public_slug && (
            <a href={`/o/${r.org_public_slug}`} target="_blank" rel="noreferrer"
               className="ml-2 text-xs text-primary underline">profilo</a>
          )}
        </span>
        <span className="text-xs text-muted-foreground">segnalata il {fmt(r.flagged_at)}</span>
      </div>
      <p className="mt-2 text-sm">
        <b>{r.author_name}</b> · <span className="text-amber-500">{'★'.repeat(r.rating || 0)}</span>
        {r.verified ? <span className="ml-2 text-xs text-emerald-700">cliente verificato</span>
                    : <span className="ml-2 text-xs text-muted-foreground">non cliente</span>}
      </p>
      {r.title && <p className="mt-1 text-sm font-semibold">{r.title}</p>}
      <p className="mt-1 text-sm text-foreground whitespace-pre-wrap">{r.body}</p>
      <p className="mt-2 text-xs text-muted-foreground">
        Motivo del professionista: <i>{r.flag_reason || 'non indicato'}</i>
        {r.flagged_by && <> · da {r.flagged_by}</>}
      </p>
      <div className="mt-3 flex flex-col sm:flex-row gap-2">
        <input value={note} onChange={(e) => setNote(e.target.value)} maxLength={500}
               placeholder="nota per il professionista (facoltativa)"
               className="flex-1 rounded-md border border-input bg-background px-3 py-2 text-sm" />
        <Button size="sm" disabled={busy} onClick={() => decidi('restore')} data-testid="flag-restore">
          Ripubblica
        </Button>
        <Button size="sm" variant="destructive" disabled={busy} onClick={() => decidi('remove')} data-testid="flag-remove">
          Rimuovi
        </Button>
      </div>
    </article>
  );
}

export default function FlaggedReviewsTab() {
  const [items, setItems] = useState(null);
  const load = useCallback(async () => {
    try { const res = await api.get('/admin/reviews/flagged'); setItems(res.data.items || []); }
    catch { toast.error('Coda non caricata'); setItems([]); }
  }, []);
  useEffect(() => { load(); }, [load]);
  const onResolve = async (id, action, note) => {
    try {
      await api.patch(`/admin/reviews/${id}/resolve`, { action, note: note || null });
      toast.success(action === 'restore' ? 'Ripubblicata: il professionista è stato avvisato'
                                         : 'Rimossa: il professionista è stato avvisato');
      load();
    } catch { toast.error('Errore, riprova'); }
  };
  return (
    <div className="space-y-4" data-testid="admin-flagged-reviews">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground flex items-center gap-2">
          <ShieldAlert className="h-4 w-4" />
          Recensioni segnalate dai professionisti, in attesa della tua decisione.
        </p>
        <Button size="sm" variant="outline" onClick={load}><RefreshCw className="h-4 w-4 mr-1" />Aggiorna</Button>
      </div>
      {items === null ? (
        <p className="text-sm text-muted-foreground">Carico…</p>
      ) : items.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-border p-8 text-center text-sm text-muted-foreground">
          Nessuna segnalazione in attesa.
        </div>
      ) : items.map((r) => <Riga key={r.id} r={r} onResolve={onResolve} />)}
    </div>
  );
}
