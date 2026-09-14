/**
 * RetreatPlansPage — la pagina «Piani e costi» del gestionale.
 *
 * Blocco B (4/7/2026): due card e la fee in evidenza. P1 (10/9/2026):
 * la fee e' zero per tutti, per sempre. P4 (10/9/2026 sera, founder:
 * «impostiamoli gia' correttamente e consolidiamo»): il catalogo del
 * 2027 — Gratis, Club 49 €/anno (solo annuale), Pro 119 €/anno o
 * 12 €/mese — si VEDE da oggi e si COMPRA dalla data in `available_from`
 * (1° gennaio 2027): fino ad allora il bottone dice la data. Via gli
 * esempi «su un incasso di 100 €» (founder 10/9): non c'e' niente da
 * calcolare, la commissione e' zero.
 *
 * I bullet vengono dal catalogo (plan.features_display → chiavi i18n):
 * cambiare il catalogo aggiorna la pagina senza redeploy frontend.
 */
import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { AppLayout, Header } from '../components/Layout';
import { Button } from '../components/ui/button';
import { Check, Loader2, ArrowLeft, Sparkles, CalendarClock } from 'lucide-react';
import { toast } from 'sonner';
import { billingAPI } from '../api/billing';
import { useBilling } from '../hooks/useBilling';
import api from '../api/client';
import RichiestaStrutturaDialog from '../features/events/components/RichiestaStrutturaDialog';

const NOMI_CTA = { retreat_pro: 'Passa a Pro' };

/* AB-R4 (14/9/2026): i servizi del Pro (e del patto 2026) si chiedono da
   qui, con la stessa scheda della regia. Studio segue il piano. */
const SERVIZI = [
  { tipo: 'lettera_eventi', label: 'I tuoi eventi nella Lettera del Cerchio' },
  { tipo: 'social', label: 'I tuoi eventi sui social di Aurya' },
  { tipo: 'intervista_reel', label: 'L’intervista e i reel' },
];

export default function RetreatPlansPage() {
  const { t } = useTranslation('settings');
  const navigate = useNavigate();
  const {
    plans, plan: currentPlan, billingEnabled,
    hasStripeCustomer, isPaid, refresh,
  } = useBilling();
  const [loadingSlug, setLoadingSlug] = useState(null);
  // AB-R4 — la cadenza si sceglie (mese/anno); i vantaggi arrivano dal backend
  const [cadenza, setCadenza] = useState('month');
  const [vantaggi, setVantaggi] = useState(null);
  const [richiesta, setRichiesta] = useState(null);   // tipo aperto nella scheda
  useEffect(() => {
    api.get('/strutture/vantaggi-pro').then((r) => setVantaggi(r.data)).catch(() => setVantaggi(null));
  }, [richiesta]);

  const retreatPlans = (plans || [])
    .filter((p) => p.slug?.startsWith('retreat_') && !p.is_addon && p.is_public !== false)
    .sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0));
  const isFounding = currentPlan === 'retreat_founding' || vantaggi?.fonte === 'patto_2026';

  // P4 — quando si accende la vendita, e quale cadenza si compra
  const nonAncoraInVendita = (plan) => !!(plan?.available_from && new Date(plan.available_from) > new Date());
  const dataItaliana = (iso) => new Date(iso).toLocaleDateString('it-IT', { day: 'numeric', month: 'long', year: 'numeric' });
  const soloAnnuale = (plan) => Array.isArray(plan?.intervals) && !plan.intervals.includes('month');
  const cadenzaDi = (plan) => (soloAnnuale(plan) ? 'year' : cadenza);

  const handleUpgrade = async (plan) => {
    if (nonAncoraInVendita(plan)) return;
    if (!billingEnabled) {
      toast.error(t('billing.stripe_not_configured', 'Stripe non configurato.'));
      return;
    }
    const interval = cadenzaDi(plan);
    setLoadingSlug(plan.slug);
    try {
      if (hasStripeCustomer && isPaid) {
        await billingAPI.modifySubscription(plan.slug, interval);
        toast.success(t('billing.plan_changed', { plan: plan.name }));
        await refresh();
        setLoadingSlug(null);
        return;
      }
      const { url } = await billingAPI.createCheckoutSession(plan.slug, interval);
      if (url) { window.location.href = url; return; }
      toast.error(t('billing.checkout_no_url', 'Nessun URL di checkout dal server.'));
      setLoadingSlug(null);
    } catch (err) {
      const detail = err.response?.data?.detail;
      toast.error(
        (typeof detail === 'object' ? detail.message : detail)
        || t('billing.checkout_error', 'Errore nel checkout.'),
      );
      setLoadingSlug(null);
    }
  };

  const prezzo = (plan) => {
    if (soloAnnuale(plan) && plan.price_yearly > 0) {
      return { importo: `€${plan.price_yearly}`, periodo: t('billing.year_short', 'anno'), nota: null };
    }
    if (plan.price_monthly > 0) {
      if (cadenza === 'year' && plan.price_yearly > 0) {
        return { importo: `€${plan.price_yearly}`, periodo: t('billing.year_short', 'anno'),
                 nota: t('billing.retreat.monthly_hint_dynamic', { price: plan.price_monthly, defaultValue: 'oppure {{price}} €/mese' }) };
      }
      return {
        importo: `€${plan.price_monthly}`, periodo: t('billing.month_short', 'mese'),
        nota: plan.price_yearly > 0 ? t('billing.retreat.yearly_hint_dynamic', { price: plan.price_yearly, defaultValue: 'oppure {{price}} €/anno' }) : null,
      };
    }
    return { importo: t('billing.free_label', 'Gratis'), periodo: null, nota: null };
  };

  return (
    <AppLayout>
      <Header
        title={t('billing.retreat.title', 'Piani e costi')}
        subtitle={t('billing.retreat.subtitle', 'Il piano base è gratuito per sempre e Aurya non prende commissioni. Il Pro si accende il 1° gennaio 2027.')}
      >
        <Button variant="outline" size="sm" onClick={() => navigate('/settings')}>
          <ArrowLeft className="h-4 w-4 mr-1.5" />
          {t('billing.back_to_settings', 'Impostazioni')}
        </Button>
      </Header>

      <div className="p-4 md:p-8 space-y-6 animate-fade-in max-w-5xl mx-auto">
        {isFounding && (
          <div className="rounded-xl border border-amber-300 bg-amber-50 p-4 flex items-start gap-3" data-testid="plans-founding">
            <Sparkles className="h-5 w-5 text-amber-600 mt-0.5 flex-shrink-0" />
            <div>
              <p className="font-semibold text-amber-900 text-sm">
                {t('billing.retreat.founding_badge', 'Sei entrato nel 2026')}
              </p>
              <p className="text-sm text-amber-800 mt-0.5">{t('billing.retreat.founding_note')}</p>
            </div>
          </div>
        )}

        {/* P1 — una riga sola, per tutti i piani */}
        <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4" data-testid="plans-zero-fee">
          <p className="font-semibold text-emerald-900 text-sm">
            {t('billing.retreat.fee_value_zero', 'Zero commissioni')}
          </p>
          <p className="text-sm text-emerald-800 mt-0.5">
            {t('billing.retreat.fee_zero_note', 'Tieni il 100% di quello che incassi. Aurya non prende commissioni.')}
            {' '}
            {t('billing.retreat.stripe_fees_short', { defaultValue: 'Se incassi online con Stripe, le commissioni di Stripe (≈ 1,5% + 0,25 €) le incassa Stripe, non noi.' })}
          </p>
        </div>

        {/* AB-R4 — i vantaggi: dal Pro o dal patto 2026, con le richieste */}
        {vantaggi?.servizi && (
          <div className="rounded-xl border border-[#2f5749]/30 bg-white p-4" data-testid="plans-vantaggi">
            <p className="font-semibold text-sm text-foreground">{t('billing.retreat.vantaggi_title', 'I tuoi vantaggi')}</p>
            <ul className="mt-2 divide-y divide-gray-100">
              {SERVIZI.map((s) => {
                const r = (vantaggi.richieste || []).find((x) => x.tipo === s.tipo && x.stato !== 'chiusa');
                return (
                  <li key={s.tipo} className="flex items-center justify-between gap-3 py-2 text-sm">
                    <span>{s.label}</span>
                    {r ? (
                      <span className="text-xs text-muted-foreground">{t('billing.retreat.vantaggi_richiesto', 'richiesto')}</span>
                    ) : (
                      <Button size="sm" variant="outline" onClick={() => setRichiesta(s.tipo)} data-testid={`plans-chiedi-${s.tipo}`}>
                        {t('billing.retreat.vantaggi_chiedi', 'Chiedilo')}
                      </Button>
                    )}
                  </li>
                );
              })}
              <li className="flex items-center justify-between gap-3 py-2 text-sm">
                <span>Crea Studio (Aurya Sound)</span>
                {vantaggi.studio
                  ? <Button size="sm" variant="outline" onClick={() => navigate('/sound/studio')}>{t('billing.retreat.vantaggi_studio_on', 'Attivo: apri Crea Studio')}</Button>
                  : <span className="text-xs text-muted-foreground">{t('billing.retreat.vantaggi_studio_off', 'Nel Pro')}</span>}
              </li>
            </ul>
          </div>
        )}
        <RichiestaStrutturaDialog aperto={richiesta !== null} tipoIniziale={richiesta || 'regia'} onClose={() => setRichiesta(null)} />

        {/* AB-R4 — la cadenza del Pro: mese o anno */}
        <div className="flex justify-end" data-testid="plans-cadenza">
          <div className="inline-flex rounded-full border border-gray-200 bg-white p-0.5 text-xs font-medium">
            {[['month', t('billing.retreat.cadenza_mese', 'Mensile')], ['year', t('billing.retreat.cadenza_anno', 'Annuale')]].map(([k, label]) => (
              <button key={k} type="button" onClick={() => setCadenza(k)} aria-pressed={cadenza === k}
                      className={`rounded-full px-3 py-1 ${cadenza === k ? 'bg-gray-900 text-white' : 'text-gray-600'}`}>
                {label}
              </button>
            ))}
          </div>
        </div>

        {/* Card piani: Gratis e Pro (dal catalogo; il Club e' nascosto) */}
        <div className="grid gap-5 md:grid-cols-2">
          {retreatPlans.map((plan) => {
            const isCurrent = plan.slug === currentPlan;
            const chiuso = nonAncoraInVendita(plan);
            const p = prezzo(plan);
            const evidenza = plan.slug === 'retreat_pro';
            return (
              <div
                key={plan.slug}
                data-testid={`plans-card-${plan.slug}`}
                className={`relative rounded-2xl border-2 bg-white p-6 flex flex-col transition-all ${
                  isCurrent ? 'border-gray-900 ring-2 ring-gray-200'
                    : evidenza ? 'border-emerald-300 shadow-md' : 'border-gray-200'
                }`}
              >
                {isCurrent && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                    <span className="inline-flex items-center gap-1 bg-gray-900 text-white text-[11px] font-semibold px-3 py-1 rounded-full">
                      <Check className="h-3 w-3" />
                      {t('billing.retreat.current', 'Piano attuale')}
                    </span>
                  </div>
                )}
                <h3 className="font-bold text-lg">{plan.name}</h3>
                <p className="text-sm text-muted-foreground mt-0.5 min-h-[2.5em]">{plan.tagline}</p>
                <div className="mt-3 flex items-baseline gap-1">
                  <span className="text-3xl font-extrabold tracking-tight">{p.importo}</span>
                  {p.periodo && <span className="text-sm text-muted-foreground">/{p.periodo}</span>}
                </div>
                {p.nota && <p className="text-xs text-muted-foreground mt-1">{p.nota}</p>}
                {chiuso && (
                  <p className="mt-2 inline-flex items-center gap-1.5 text-xs font-medium text-[#2f5749]" data-testid={`plans-dal-${plan.slug}`}>
                    <CalendarClock className="h-3.5 w-3.5" aria-hidden />
                    {t('billing.retreat.available_from', { date: dataItaliana(plan.available_from), defaultValue: 'In vendita dal {{date}}' })}
                  </p>
                )}
                <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mt-5 mb-2">
                  {t('billing.retreat.included_title', 'Cosa è incluso')}
                </p>
                <ul className="space-y-2 flex-1">
                  {(plan.features_display || []).map((key) => (
                    <li key={key} className="flex items-start gap-2 text-sm">
                      <span className="inline-flex items-center justify-center h-4 w-4 rounded-full bg-green-100 mt-0.5 flex-shrink-0">
                        <Check className="h-2.5 w-2.5 text-green-600" />
                      </span>
                      <span>{t(key)}</span>
                    </li>
                  ))}
                </ul>
                <div className="mt-6">
                  {isCurrent ? (
                    <Button className="w-full" variant="outline" disabled>
                      {t('billing.retreat.current', 'Piano attuale')}
                    </Button>
                  ) : plan.is_self_serve && !isFounding ? (
                    <Button
                      className="w-full font-semibold"
                      variant={chiuso ? 'outline' : 'default'}
                      onClick={() => handleUpgrade(plan)}
                      disabled={chiuso || loadingSlug !== null}
                      data-testid={`plans-cta-${plan.slug}`}
                    >
                      {loadingSlug === plan.slug && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                      {chiuso
                        ? t('billing.available_from_label', { date: dataItaliana(plan.available_from), defaultValue: 'Dal {{date}}' })
                        : (NOMI_CTA[plan.slug] || t('billing.retreat.cta_upgrade', 'Passa a Pro'))}
                    </Button>
                  ) : plan.slug === 'retreat_free' && currentPlan !== 'retreat_free' ? (
                    <p className="text-xs text-muted-foreground text-center">
                      {t('billing.retreat.downgrade_hint')}
                    </p>
                  ) : null}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </AppLayout>
  );
}
