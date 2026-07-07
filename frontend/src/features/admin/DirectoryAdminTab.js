/**
 * DirectoryAdminTab — SA3: la plancia del marketplace.
 *
 * Una riga per operatore con lo stato di listing calcolato dalle
 * STESSE condizioni del calendario pubblico (GT1b, via
 * /admin/platform/directory): chi è dentro, chi è fuori e PERCHÉ,
 * quanti ritiri porta, quanti ordini gli arrivano dal calendario.
 *
 * I "bloccati solo da Stripe" sono i lead di attivazione più caldi:
 * hanno già i ritiri pronti, manca un collegamento.
 */
import React, { useCallback, useEffect, useState } from 'react';
import { RefreshCw, ExternalLink, CheckCircle2, XCircle } from 'lucide-react';
import api from '../../api/client';
import { StatCard } from '../../components/charts';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { Globe2, CalendarCheck, Zap } from 'lucide-react';

const REASON_LABELS = {
  stripe_not_ready: 'Stripe non attivo',
  no_public_page: 'Nessuna pagina pubblica',
  no_direct_retreats: 'Nessun ritiro prenotabile online',
};

export default function DirectoryAdminTab() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all'); // all | listed | blocked

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get('/admin/platform/directory');
      setData(res.data);
    } finally { setLoading(false); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const c = data?.counters || {};
  const rows = (data?.rows || []).filter((r) => {
    if (filter === 'listed') return r.listed;
    if (filter === 'blocked') return !r.listed;
    return true;
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          Lo stato del calendario pubblico, con le stesse condizioni del gate: chi è visibile, chi no e perché.
        </p>
        <Button variant="outline" size="sm" onClick={load} disabled={loading}>
          <RefreshCw className={`h-3.5 w-3.5 mr-1.5 ${loading ? 'animate-spin' : ''}`} /> Aggiorna
        </Button>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <StatCard loading={loading} icon={Globe2}
                  label="Operatori attivi" value={c.orgs_total ?? '—'} />
        <StatCard loading={loading} icon={Globe2}
                  label="In directory" value={c.orgs_listed ?? '—'} />
        <StatCard loading={loading} icon={CalendarCheck}
                  label="Ritiri nel calendario" value={c.retreats_listed ?? '—'} />
        <StatCard loading={loading} icon={Zap}
                  accent={Boolean(c.orgs_blocked_stripe_only)}
                  label="Bloccati solo da Stripe" value={c.orgs_blocked_stripe_only ?? '—'} />
      </div>

      <div className="flex gap-2">
        {[['all', 'Tutti'], ['listed', 'In directory'], ['blocked', 'Fuori']].map(([k, label]) => (
          <button key={k} type="button" onClick={() => setFilter(k)}
                  className={`rounded-full px-3 py-1 text-xs font-semibold ${
                    filter === k ? 'bg-gray-900 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}>{label}</button>
        ))}
      </div>

      <div className="rounded-2xl border border-border bg-card overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-border text-left">
              <th className="px-4 py-2.5 text-xs font-medium text-muted-foreground">Operatore</th>
              <th className="px-4 py-2.5 text-xs font-medium text-muted-foreground">Piano</th>
              <th className="px-4 py-2.5 text-xs font-medium text-muted-foreground">Directory</th>
              <th className="px-4 py-2.5 text-xs font-medium text-muted-foreground text-right">Ritiri dentro</th>
              <th className="px-4 py-2.5 text-xs font-medium text-muted-foreground text-right">Esclusi</th>
              <th className="px-4 py-2.5 text-xs font-medium text-muted-foreground text-right">Ordini mktp / tot (30gg)</th>
              <th className="px-4 py-2.5 text-xs font-medium text-muted-foreground text-right">Rating</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.organization_id} className="border-b border-border last:border-0">
                <td className="px-4 py-2.5">
                  <span className="text-sm font-medium text-foreground">
                    {r.featured && <span className="text-[#376254] mr-1" title="In evidenza">✦</span>}
                    {r.name || r.organization_id}
                  </span>
                </td>
                <td className="px-4 py-2.5">
                  <Badge variant="outline" className="text-[11px]">{r.plan_slug || '—'}</Badge>
                </td>
                <td className="px-4 py-2.5">
                  {r.listed ? (
                    <span className="inline-flex items-center gap-1 text-xs text-[#376254] font-semibold">
                      <CheckCircle2 className="h-3.5 w-3.5" /> Visibile
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 text-xs text-red-700"
                          title={r.reasons.map((x) => REASON_LABELS[x] || x).join(' · ')}>
                      <XCircle className="h-3.5 w-3.5" />
                      {(r.reasons || []).map((x) => REASON_LABELS[x] || x).join(' · ') || 'Fuori'}
                    </span>
                  )}
                </td>
                <td className="px-4 py-2.5 text-right font-mono text-sm">{r.retreats_listed}</td>
                <td className={`px-4 py-2.5 text-right font-mono text-sm ${r.retreats_excluded ? 'text-red-700' : ''}`}>
                  {r.retreats_excluded}
                </td>
                <td className="px-4 py-2.5 text-right font-mono text-sm">
                  {r.orders_marketplace_30d} / {r.orders_total_30d}
                </td>
                <td className="px-4 py-2.5 text-right text-sm">
                  {r.reviews_stats?.count > 0
                    ? <>★ {r.reviews_stats.avg} <span className="text-muted-foreground text-xs">({r.reviews_stats.count})</span></>
                    : <span className="text-muted-foreground">—</span>}
                </td>
              </tr>
            ))}
            {!loading && rows.length === 0 && (
              <tr><td colSpan={7} className="px-4 py-8 text-center text-sm text-muted-foreground">
                Nessun operatore in questo filtro.
              </td></tr>
            )}
          </tbody>
        </table>
      </div>
      <p className="text-xs text-muted-foreground">
        <ExternalLink className="inline h-3 w-3 mr-1" aria-hidden />
        Le azioni per operatore (piano, trial, impersona) vivono nel tab Organizations — qui il polso, lì la leva.
      </p>
    </div>
  );
}
