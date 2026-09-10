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
import { Wallet, TrendingUp, Globe2, CalendarCheck, RefreshCw, Users, Eye, Inbox, Sparkles } from 'lucide-react';
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
  const [lunedi, setLunedi] = useState(null);   // RB14
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [ovRes, mrrRes, lunRes] = await Promise.allSettled([
        api.get('/admin/platform/overview'),
        adminAPI.getMrrOverview(),
        api.get('/admin/platform/lunedi'),
      ]);
      if (ovRes.status === 'fulfilled') setData(ovRes.value.data);
      if (mrrRes.status === 'fulfilled') setMrr(mrrRes.value);
      if (lunRes.status === 'fulfilled') setLunedi(lunRes.value.data);
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

      {/* RB14 (10/9/2026) — I NUMERI DEL LUNEDI': i cinque numeri del
          piano di business (§7.8), senza stime. Prima dei soldi perche'
          in fase rete i soldi sono zero e la fila e' tutto. */}
      <div data-testid="numeri-lunedi" className="rounded-2xl border border-[#2f5749]/30 bg-[#f4f7f5] p-4">
        <div className="flex flex-wrap items-baseline justify-between gap-2 mb-3">
          <p className="text-sm font-semibold text-[#2f5749]">I numeri del lunedì</p>
          <p className="text-xs text-muted-foreground">
            {lunedi?.generated_at ? `al ${new Date(lunedi.generated_at).toLocaleString('it-IT')}` : ''}
          </p>
        </div>
        <div className="grid grid-cols-2 lg:grid-cols-6 gap-3">
          <StatCard loading={loading} icon={Users} label="Il Cerchio (confermati)"
                    value={lunedi ? `${lunedi.cerchio.confermati}` : '—'}
                    sublabel={lunedi ? `${lunedi.cerchio.con_citta} con la città · ${lunedi.cerchio.con_ritiri} vogliono i ritiri · +${lunedi.cerchio.nuovi_7g} in 7 giorni` : ''} />
          <StatCard loading={loading} icon={CalendarCheck} label="Ritiri in programma"
                    value={lunedi ? `${lunedi.ritiri.in_programma}` : '—'}
                    sublabel={lunedi ? `${lunedi.ritiri.online} online · ${lunedi.ritiri.su_richiesta} su richiesta` : ''} />
          <StatCard loading={loading} icon={Eye} label="Visite ai profili (7 giorni)"
                    value={lunedi ? `${lunedi.visite.ultimi_7g}` : '—'}
                    sublabel={lunedi ? `i 7 prima: ${lunedi.visite.precedenti_7g}` : ''} />
          <StatCard loading={loading} icon={Sparkles} label="Operatori attivi (90 giorni)"
                    value={lunedi ? `${lunedi.operatori.attivi_90g} / ${lunedi.operatori.totali}` : '—'}
                    sublabel={lunedi ? `${lunedi.operatori.nella_rete} nella rete · fondatori ${lunedi.operatori.fondatori_presi}/${lunedi.operatori.fondatori_tetto}` : ''} />
          <StatCard loading={loading} icon={Inbox} label="Richieste (30 giorni)"
                    value={lunedi ? `${lunedi.richieste.regia + lunedi.richieste.team_building + lunedi.richieste.struttura}` : '—'}
                    sublabel={lunedi ? `${lunedi.richieste.regia} regia · ${lunedi.richieste.team_building} team building · ${lunedi.richieste.struttura} strutture · ${lunedi.richieste.aperte} aperte` : ''} />
          <StatCard loading={loading} icon={Wallet} label="Ritiri incassati (30 giorni)"
                    value={lunedi ? eur(lunedi.euro.ritiri_30g) : '—'}
                    sublabel="servizi e piani: ordini manuali, fuori da qui" />
        </div>
        {lunedi && Object.keys(lunedi.cerchio.porte_30g || {}).length > 0 && (
          <p className="mt-3 text-xs text-muted-foreground" data-testid="numeri-lunedi-porte">
            Porte degli ultimi 30 giorni: {Object.entries(lunedi.cerchio.porte_30g).sort((a, b) => b[1] - a[1]).map(([k, n]) => `${k} ${n}`).join(' · ')}
          </p>
        )}
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
