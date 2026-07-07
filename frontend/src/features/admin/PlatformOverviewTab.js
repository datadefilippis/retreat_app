/**
 * PlatformOverviewTab — SA2: il business Aurya a colpo d'occhio.
 *
 * DUE motori, una vista: le fee sul transato marketplace (ledger SA1,
 * /admin/platform/overview) + il canone (MRR, endpoint esistente).
 * Poi il marketplace: GMV 12 mesi (linea piena) con il transato
 * online tratteggiato (la parte che genera fee), ordini per canale
 * (30gg), GMV per anima, stato directory.
 *
 * Kit grafico condiviso components/charts — l'admin non ha un design
 * system a parte. Sola lettura, cache server 60s.
 */
import React, { useCallback, useEffect, useState } from 'react';
import { Wallet, TrendingUp, Globe2, CalendarCheck, RefreshCw } from 'lucide-react';
import api from '../../api/client';
import { adminAPI } from '../../api';
import { StatCard, TrendArea, DonutSplit } from '../../components/charts';
import { Button } from '../../components/ui/button';

const eur = (v) => `€${Number(v || 0).toLocaleString('it-IT', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

const CHANNEL_LABELS = {
  marketplace: 'Calendario pubblico',
  store: 'Store operatore',
  manual: 'Manuale',
  pos: 'POS',
};
const TYPE_LABELS = {
  event_ticket: 'Ritiri', service: 'Consulenze', physical: 'Fisici',
  digital: 'Digitali', course: 'Corsi', rental: 'Noleggi',
};
const TYPE_COLORS = {
  event_ticket: '#376254', service: '#5E8073', physical: '#B9A96B',
  digital: '#A9695B', course: '#C97B5D', rental: '#8A9088',
};

function monthLabel(ym) {
  try {
    const [y, m] = ym.split('-').map(Number);
    return new Date(y, m - 1, 1).toLocaleDateString('it-IT', { month: 'short', year: '2-digit' });
  } catch { return ym; }
}

export default function PlatformOverviewTab() {
  const [data, setData] = useState(null);
  const [mrr, setMrr] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [ovRes, mrrRes] = await Promise.allSettled([
        api.get('/admin/platform/overview'),
        adminAPI.getMrrOverview(),
      ]);
      if (ovRes.status === 'fulfilled') setData(ovRes.value.data);
      if (mrrRes.status === 'fulfilled') setMrr(mrrRes.value);
    } finally { setLoading(false); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const money = data?.money || {};
  const dir = data?.directory || {};
  const mrrCurrent = mrr?.mrr_current ?? mrr?.mrr ?? null;
  const months = (data?.months || []).map((m) => ({
    label: monthLabel(m.month), value: m.gmv, expected: m.online,
  }));
  const channels = Object.entries(data?.by_channel_30d || {}).map(([k, v]) => ({
    key: k, label: CHANNEL_LABELS[k] || k, value: Math.round(v.gmv * 100) / 100,
  }));
  const types = (data?.by_type_12m || []).map((x) => ({
    key: x.item_type, label: TYPE_LABELS[x.item_type] || x.item_type, value: x.revenue,
  }));

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          I due motori del business: fee sul transato online + canoni. Solo dati timbrati, niente stime.
        </p>
        <Button variant="outline" size="sm" onClick={load} disabled={loading}>
          <RefreshCw className={`h-3.5 w-3.5 mr-1.5 ${loading ? 'animate-spin' : ''}`} /> Aggiorna
        </Button>
      </div>

      {/* Riga 1 — i miei soldi */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <StatCard loading={loading} icon={Wallet}
                  label="Fee incassate (mese)" value={eur(money.fees_month)} />
        <StatCard loading={loading} icon={Wallet}
                  label="Fee incassate (12 mesi)" value={eur(money.fees_12m)} />
        <StatCard loading={loading} icon={TrendingUp}
                  label="MRR abbonamenti"
                  value={mrrCurrent != null ? eur(mrrCurrent) : '—'} />
        <StatCard loading={loading} icon={TrendingUp}
                  label="Transato online (mese)" value={eur(money.online_month)} />
      </div>

      {/* Riga 2 — il marketplace */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <StatCard loading={loading} icon={Globe2}
                  label="Operatori attivi" value={dir.orgs_total ?? '—'} />
        <StatCard loading={loading} icon={Globe2}
                  label="Operatori in directory" value={dir.orgs_listed ?? '—'} />
        <StatCard loading={loading} icon={CalendarCheck}
                  label="Ritiri nel calendario" value={dir.retreats_listed ?? '—'} />
        <StatCard loading={loading} icon={CalendarCheck}
                  accent={Boolean(dir.orgs_blocked_stripe_only)}
                  label="Bloccati solo da Stripe" value={dir.orgs_blocked_stripe_only ?? '—'} />
      </div>

      {/* Trend GMV */}
      <section className="rounded-2xl border border-border bg-card p-5">
        <h2 className="font-heading text-base font-semibold text-foreground mb-3">
          GMV piattaforma, mese per mese
        </h2>
        <TrendArea
          data={months}
          valueFormatter={eur}
          valueLabel="GMV totale"
          expectedLabel="Transato online (fee)"
        />
        <p className="text-xs text-muted-foreground mt-2">
          La linea tratteggiata è il transato che genera fee: più si avvicina alla piena, più il business è on-platform.
        </p>
      </section>

      {/* Composizione */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <section className="rounded-2xl border border-border bg-card p-5">
          <h2 className="font-heading text-base font-semibold text-foreground mb-3">
            GMV per canale (30 giorni)
          </h2>
          <DonutSplit data={channels} valueFormatter={eur} />
        </section>
        <section className="rounded-2xl border border-border bg-card p-5">
          <h2 className="font-heading text-base font-semibold text-foreground mb-3">
            GMV per anima (12 mesi)
          </h2>
          <DonutSplit data={types} colors={TYPE_COLORS} valueFormatter={eur} />
        </section>
      </div>
    </div>
  );
}
