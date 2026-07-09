/**
 * SignalsTab — SA5: da dati a proposte, il motore del GTM 1-a-1.
 *
 * Quattro liste da /admin/platform/signals, ognuna coi numeri che
 * giustificano la mossa:
 *   · Pro conviene   — Gratis sopra break-even: risparmio calcolato
 *   · Sbloccabili    — ritiri pronti, manca SOLO Stripe
 *   · A rischio      — fermi da 60gg o mai partiti
 *   · In crescita    — GMV in accelerazione: candidati featured/case
 *
 * Azioni one-click: scheda 360° e copia email. Le leve (piano/trial)
 * restano nel tab Organizations.
 */
import React, { useCallback, useEffect, useState } from 'react';
import { RefreshCw, Sparkles, Zap, AlertTriangle, TrendingUp, Copy } from 'lucide-react';
import { toast } from 'sonner';
import api from '../../api/client';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import OrgBusinessProfileDialog from './OrgBusinessProfileDialog';

const eur = (v) => `€${Number(v || 0).toLocaleString('it-IT', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

function SignalSection({ icon: Icon, title, hint, items, renderDetail, onOpen, accent }) {
  return (
    <section className="rounded-2xl border border-border bg-card p-4">
      <h3 className={`flex items-center gap-2 text-sm font-semibold ${accent || 'text-foreground'}`}>
        <Icon className="h-4 w-4" aria-hidden /> {title}
        <span className="ml-1 rounded-full bg-muted px-2 py-0.5 text-[11px] text-muted-foreground">{items.length}</span>
      </h3>
      <p className="text-xs text-muted-foreground mt-0.5 mb-3">{hint}</p>
      {items.length === 0 ? (
        <p className="text-sm text-muted-foreground py-2">Nessun operatore in questo segnale.</p>
      ) : (
        <ul className="space-y-2">
          {items.map((it) => (
            <li key={it.organization_id}
                className="flex flex-wrap items-center gap-2 rounded-xl border border-border px-3 py-2">
              <button type="button" onClick={() => onOpen(it.organization_id)}
                      className="text-sm font-medium text-foreground hover:text-primary hover:underline">
                {it.name || it.organization_id}
              </button>
              <Badge variant="outline" className="text-[10px]">{it.plan_slug || '—'}</Badge>
              <span className="text-xs text-muted-foreground flex-1">{renderDetail(it)}</span>
              {it.email && (
                <button type="button"
                        onClick={() => { navigator.clipboard.writeText(it.email); toast.success(`Email copiata: ${it.email}`); }}
                        title={it.email}
                        className="inline-flex items-center gap-1 rounded-lg border border-border px-2 py-1 text-xs hover:bg-muted/50">
                  <Copy className="h-3 w-3" aria-hidden /> Email
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export default function SignalsTab() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [profileOrg, setProfileOrg] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get('/admin/platform/signals');
      setData(res.data);
    } finally { setLoading(false); }
  }, []);
  useEffect(() => { load(); }, [load]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          A chi proporre cosa, oggi — ogni segnale porta i numeri che giustificano la mossa.
        </p>
        <Button variant="outline" size="sm" onClick={load} disabled={loading}>
          <RefreshCw className={`h-3.5 w-3.5 mr-1.5 ${loading ? 'animate-spin' : ''}`} /> Aggiorna
        </Button>
      </div>

      <SignalSection
        icon={Sparkles} accent="text-[#376254]"
        title="Pro conviene"
        hint="Piano Gratis sopra il break-even (~967 €/mese online): il Pro si ripaga da solo — proposta calda."
        items={data?.pro_ready || []}
        onOpen={setProfileOrg}
        renderDetail={(it) => <>transato online {eur(it.online_month)} questo mese → risparmierebbe {eur(it.monthly_saving)}/mese col Pro</>}
      />
      <SignalSection
        icon={Zap} accent="text-amber-700"
        title="Sbloccabili con Stripe"
        hint="Ritiri pronti e pagina pubblica ok: manca SOLO il collegamento Stripe per entrare nel calendario."
        items={data?.unlockable || []}
        onOpen={setProfileOrg}
        renderDetail={(it) => <>{it.retreats_ready} ritiri pronti a entrare in directory{it.visits_30d > 0 && <> · {it.visits_30d} visite negli ultimi 30gg che oggi non possono prenotare</>}</>}
      />
      <SignalSection
        icon={AlertTriangle} accent="text-amber-700"
        title="Traffico in calo"
        hint="Visite dimezzate rispetto ai 30 giorni precedenti: un nudge (nuove date, foto, blog) prima che il pubblico sparisca."
        items={data?.traffic_drop || []}
        onOpen={setProfileOrg}
        renderDetail={(it) => <>{it.visits_30d} visite negli ultimi 30gg (prima: {it.visits_prev_30d})</>}
      />
      <SignalSection
        icon={AlertTriangle} accent="text-red-700"
        title="A rischio"
        hint="Fermi da 60 giorni o mai partiti dopo 2 settimane: una chiamata vale più di un report."
        items={data?.at_risk || []}
        onOpen={setProfileOrg}
        renderDetail={(it) => it.kind === 'silent_60d'
          ? <>ultimo ordine il {it.last_order}</>
          : <>iscritto il {it.created_at}, mai pubblicato nulla</>}
      />
      <SignalSection
        icon={TrendingUp} accent="text-[#376254]"
        title="In crescita"
        hint="GMV in accelerazione (30gg vs precedenti): candidati featured, casi studio, testimonianze."
        items={data?.growing || []}
        onOpen={setProfileOrg}
        renderDetail={(it) => <>{eur(it.gmv_30d)} negli ultimi 30gg (prima: {eur(it.gmv_prev_30d)})</>}
      />

      <OrgBusinessProfileDialog
        orgId={profileOrg}
        open={Boolean(profileOrg)}
        onOpenChange={(o) => { if (!o) setProfileOrg(null); }}
      />
    </div>
  );
}
