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

/* FV4 (10/9/2026 sera) — L'ANTEPRIMA DELLE SEQUENZE. Il founder legge
   ogni email prima che parta, per un destinatario vero (email) o
   fittizio. Stesso codice che invia; qui niente parte. */
function SequenzeAnteprima() {
  const [passi, setPassi] = useState(null);
  const [pubblico, setPubblico] = useState('operatore');
  const [passo, setPasso] = useState('np5');
  const [email, setEmail] = useState('');
  const [reso, setReso] = useState(null);
  const [caricando, setCaricando] = useState(false);
  useEffect(() => {
    api.get('/admin/platform/sequenze/passi').then((r) => setPassi(r.data?.pubblici || null)).catch(() => setPassi({}));
  }, []);
  const mostra = async () => {
    setCaricando(true);
    try {
      const r = await api.get('/admin/platform/sequenze/anteprima', { params: { pubblico, passo, email: email || undefined } });
      setReso(r.data);
    } catch (e) {
      setReso({ nota: 'Anteprima non disponibile.' });
    } finally { setCaricando(false); }
  };
  const elenco = (passi && passi[pubblico]) || [];
  return (
    <div data-testid="sequenze-anteprima" className="rounded-2xl border border-border bg-card p-4">
      <p className="text-sm font-semibold text-foreground">Le email delle sequenze, in anteprima</p>
      <p className="mt-1 text-xs text-muted-foreground">Scegli il pubblico e il passo; con un’email vera vedi l’email come la riceverebbe quella persona. Da qui non parte niente.</p>
      <div className="mt-3 flex flex-wrap items-end gap-2">
        <label className="text-xs">Pubblico
          <select value={pubblico} onChange={(e) => { setPubblico(e.target.value); const primo = (passi?.[e.target.value] || [])[0]; if (primo) setPasso(primo.nome); }}
                  className="mt-1 block rounded-md border border-border bg-background px-2 py-1 text-sm" data-testid="seq-pubblico">
            <option value="operatore">operatore</option>
            <option value="cerchio">cerchio</option>
          </select>
        </label>
        <label className="text-xs">Passo
          <select value={passo} onChange={(e) => setPasso(e.target.value)}
                  className="mt-1 block rounded-md border border-border bg-background px-2 py-1 text-sm" data-testid="seq-passo">
            {elenco.map((p) => <option key={p.nome} value={p.nome}>{p.nome}{p.giorno != null ? ` · giorno ${p.giorno}` : ' · evento'}{p.a === 'admin' ? ' · a noi' : ''}</option>)}
          </select>
        </label>
        <label className="text-xs">Email (facoltativa)
          <input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="chi la riceverebbe"
                 className="mt-1 block w-56 rounded-md border border-border bg-background px-2 py-1 text-sm" data-testid="seq-email" />
        </label>
        <Button size="sm" onClick={mostra} disabled={caricando} data-testid="seq-mostra">{caricando ? 'Carico…' : 'Mostra'}</Button>
      </div>
      {reso && (
        <div className="mt-4">
          {reso.oggetto ? (
            <>
              <p className="text-sm"><span className="text-muted-foreground">A:</span> {reso.destinatario}{reso.trovato ? '' : ' (destinatario fittizio)'}</p>
              <p className="text-sm font-semibold" data-testid="seq-oggetto">{reso.oggetto}</p>
              <iframe title="anteprima email" srcDoc={reso.html} className="mt-2 h-[560px] w-full rounded-md border border-border bg-white" />
            </>
          ) : (
            <p className="text-sm text-muted-foreground" data-testid="seq-nota">{reso.nota || 'Niente da mostrare.'}</p>
          )}
        </div>
      )}
    </div>
  );
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
        {lunedi?.sequenze_30g && (
          <p className="mt-2 text-xs text-muted-foreground" data-testid="numeri-lunedi-sequenze">
            Email delle sequenze partite in 30 giorni: {Object.entries(lunedi.sequenze_30g).map(([pub, passi]) => `${pub} ${Object.entries(passi).map(([k, n]) => `${k} ${n}`).join(' ')}`).join(' · ')}
          </p>
        )}
      </div>

      <SequenzeAnteprima />

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
