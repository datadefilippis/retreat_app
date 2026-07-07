/**
 * OrgBusinessProfileDialog — SA4: la scheda 360° di un operatore.
 *
 * Si apre dalla riga della tab Directory (e ovunque serva un org_id):
 * presenza pubblica, transazioni per canale, quanto guadagna LUI e
 * quanto guadagno IO (fee ledger SA1 + canone), relazione. Con il
 * segnale break-even Pro (GT2 visto dalla piattaforma) quando la
 * proposta conviene DAVVERO all'operatore.
 *
 * Sola lettura: le leve (piano, trial, impersona) restano nel tab
 * Organizations — qui si decide, lì si agisce.
 */
import React, { useEffect, useState } from 'react';
import { ExternalLink, Sparkles } from 'lucide-react';
import api from '../../api/client';
import { MiniBars } from '../../components/charts';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription,
} from '../../components/ui/dialog';
import { Skeleton } from '../../components/ui/skeleton';

const eur = (v) => `€${Number(v || 0).toLocaleString('it-IT', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
const CHANNEL_LABELS = {
  marketplace: 'Calendario pubblico', store: 'Store', manual: 'Manuale', pos: 'POS',
};

function Stat({ label, value, accent }) {
  return (
    <div className={`rounded-xl border p-3 ${accent ? 'border-[#376254]/40 bg-[#376254]/5' : 'border-border bg-card'}`}>
      <p className="text-[11px] uppercase tracking-wide text-muted-foreground">{label}</p>
      <p className="text-lg font-bold font-heading text-foreground mt-0.5">{value}</p>
    </div>
  );
}

export default function OrgBusinessProfileDialog({ orgId, open, onOpenChange }) {
  const [data, setData] = useState(null);
  const [trials, setTrials] = useState(null);

  useEffect(() => {
    if (!open || !orgId) return;
    setData(null);
    setTrials(null);
    api.get(`/admin/platform/organizations/${orgId}/business-profile`)
      .then((res) => setData(res.data))
      .catch(() => setData({ error: true }));
    // SA6 — il trial-history esisteva solo via API: ora vive qui
    api.get(`/admin/organizations/${orgId}/trial-history`)
      .then((res) => setTrials(res.data))
      .catch(() => setTrials(null));
  }, [open, orgId]);

  const t = data?.transactions || {};
  const e = data?.platform_earnings || {};
  const p = data?.presence || {};
  const r = data?.relationship || {};
  const bars = (t.by_month || []).map((m) => ({ label: m.month.slice(5), value: m.gmv }));

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="font-heading">
            {data?.featured && <span className="text-[#376254] mr-1">✦</span>}
            {data?.name || 'Operatore'}
          </DialogTitle>
          <DialogDescription>
            {/* niente <Badge> (div) dentro DialogDescription (p): nesting
                HTML invalido — badge inline con span */}
            {data?.plan_slug && (
              <span className="mr-2 inline-flex items-center rounded-full border border-border px-2.5 py-0.5 text-xs font-semibold">
                {data.plan_slug}
              </span>
            )}
            {data?.plan_price_monthly != null && <>canone {eur(data.plan_price_monthly)}/mese · </>}
            fee {data?.fee_percent ?? '—'}% · dal {data?.created_at || '—'}
          </DialogDescription>
        </DialogHeader>

        {!data && <Skeleton className="h-64 w-full rounded-xl" />}
        {data?.error && <p className="text-sm text-red-700">Impossibile caricare la scheda.</p>}

        {data && !data.error && (
          <div className="space-y-5">
            {/* segnale break-even (GT2 lato piattaforma) */}
            {e.pro_breakeven_reached && (
              <div className="rounded-xl border border-[#376254]/40 bg-[#376254]/5 p-3 flex items-center gap-2 text-sm">
                <Sparkles className="h-4 w-4 text-[#376254]" aria-hidden />
                Sopra il break-even: a questo operatore il <strong>Pro conviene davvero</strong> — proposta calda.
              </div>
            )}

            {/* i miei guadagni */}
            <section>
              <h3 className="text-sm font-semibold text-foreground mb-2">I miei guadagni da questa org</h3>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                <Stat label="Fee (mese)" value={eur(e.fees_month)} />
                <Stat label="Fee (12 mesi)" value={eur(e.fees_12m)} />
                <Stat label="Fee (lifetime)" value={eur(e.fees_lifetime)} />
                <Stat label="Transato online (mese)" value={eur(e.online_month)} />
              </div>
            </section>

            {/* il suo business */}
            <section>
              <h3 className="text-sm font-semibold text-foreground mb-2">Il suo business (12 mesi)</h3>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                <Stat label="GMV" value={eur(t.gmv_12m)} />
                <Stat label="Ordini" value={t.orders_12m ?? '—'} />
                <Stat label="Ticket medio" value={t.avg_ticket != null ? eur(t.avg_ticket) : '—'} />
                <Stat label="Incassato online" value={eur(t.collected_online_12m)} />
              </div>
              <div className="mt-3 rounded-xl border border-border bg-card p-3">
                <MiniBars data={bars} valueFormatter={eur} />
              </div>
              <div className="mt-2 flex flex-wrap gap-2">
                {Object.entries(t.by_channel || {}).map(([k, v]) => (
                  <span key={k} className="rounded-full border border-border px-2.5 py-1 text-xs">
                    {CHANNEL_LABELS[k] || k}: <strong>{v.orders}</strong> ordini · {eur(v.gmv)}
                  </span>
                ))}
              </div>
            </section>

            {/* presenza */}
            <section>
              <h3 className="text-sm font-semibold text-foreground mb-2">Presenza pubblica</h3>
              <div className="text-sm space-y-1.5">
                <p>
                  Store: {(p.stores || []).length === 0 ? '—' : (p.stores || []).map((s) => (
                    <a key={s.slug} href={`/s/${s.slug}`} target="_blank" rel="noreferrer"
                       className="text-primary hover:underline mr-2">
                      /{s.slug}{!s.published && ' (bozza)'} <ExternalLink className="inline h-3 w-3" />
                    </a>
                  ))}
                </p>
                <p>
                  Profilo: {p.profile_slug
                    ? <a href={`/o/${p.profile_slug}`} target="_blank" rel="noreferrer" className="text-primary hover:underline">/o/{p.profile_slug} <ExternalLink className="inline h-3 w-3" /></a>
                    : <span className="text-muted-foreground">nessuna vetrina</span>}
                </p>
                <p>
                  Ritiri futuri: <strong>{p.future_events ?? 0}</strong>
                  {p.directory && (
                    <> — in directory: <strong>{p.directory.retreats_listed}</strong>, esclusi: <strong className={p.directory.retreats_excluded ? 'text-red-700' : ''}>{p.directory.retreats_excluded}</strong>
                      {!p.directory.listed && p.directory.reasons?.length > 0 && (
                        <span className="text-red-700 text-xs ml-1">({p.directory.reasons.join(', ')})</span>
                      )}
                    </>
                  )}
                </p>
              </div>
            </section>

            {/* relazione */}
            <section>
              <h3 className="text-sm font-semibold text-foreground mb-2">Relazione</h3>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                <Stat label="Recensioni"
                      value={r.reviews_stats?.count > 0 ? `★ ${r.reviews_stats.avg} (${r.reviews_stats.count})` : '—'} />
                <Stat label="Iscritti newsletter" value={r.newsletter_subscribers ?? 0} />
                <Stat label="Ultimo accesso" value={(r.last_login_at || '—').slice(0, 10)} />
                <Stat label="Trial"
                      value={(trials?.trials?.length ?? trials?.history?.length ?? 0) > 0
                        ? `${(trials.trials || trials.history).length} assegnati`
                        : 'mai'} />
              </div>
            </section>

            <p className="text-xs text-muted-foreground">
              Le azioni (piano, trial, impersona, addon) vivono nel tab Organizations.
            </p>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
