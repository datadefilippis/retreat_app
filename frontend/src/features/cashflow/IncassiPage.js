/**
 * IncassiPage — /incassi (CF3, INSIGHTS_ACTION_PLAN).
 *
 * La tesoreria dell'operatore in una pagina, tre blocchi in ordine
 * di priorità (come va → direzione → cosa faccio adesso):
 *   1. 4 StatCard: incassato 12m / in arrivo / in ritardo / ticket medio
 *   2. TrendArea 12 mesi: incassato pieno + atteso tratteggiato —
 *      la stagionalità e i saldi futuri già contrattualizzati
 *   3. "Da incassare": righe scadute e in scadenza 30gg, OGNI riga
 *      col sollecito WhatsApp/email a un click (ContactActions,
 *      contesto payment_reminder) + venduto per prodotto (donut)
 *
 * Fonte: GET /analytics/cashflow (libro mastro payment_schedules).
 */
import React, { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Wallet, TrendingUp, AlertTriangle, Receipt, CheckCircle2, Sparkles } from 'lucide-react';
import { toast } from 'sonner';
import api from '../../api/client';
import { AppLayout, Header } from '../../components/Layout';
import { StatCard, TrendArea, DonutSplit } from '../../components/charts';
import ContactActions from '../../components/ContactActions';
import { UpgradeDialog } from '../../components/UpgradeDialog';
import { formatCurrency } from '../../lib/utils';
import { useCurrency } from '../../context/AuthContext';

function monthLabel(ym, lang) {
  try {
    const [y, m] = ym.split('-').map(Number);
    return new Date(y, m - 1, 1).toLocaleDateString(lang, { month: 'short', year: '2-digit' });
  } catch { return ym; }
}

function dayLabel(iso, lang) {
  try {
    return new Date(iso).toLocaleDateString(lang, { day: 'numeric', month: 'short', year: 'numeric' });
  } catch { return (iso || '').slice(0, 10); }
}

// CG2 — semantica fissa: ogni anima ha il suo colore in tutta l'app
const TYPE_COLORS = {
  event_ticket: '#376254',  // ritiri — salvia
  service: '#5E8073',       // consulenze — salvia chiara
  physical: '#B9A96B',      // fisici — oliva
  digital: '#A9695B',       // digitali — argilla
  course: '#C97B5D',        // corsi — terracotta
  rental: '#8A9088',        // noleggi — neutro
  manual: '#C9CDC5',        // entrate manuali — grigio
};
const TYPE_LABEL_KEYS = {
  event_ticket: 'cashflow.typeRetreats',
  service: 'cashflow.typeServices',
  physical: 'cashflow.typePhysical',
  digital: 'cashflow.typeDigital',
  course: 'cashflow.typeCourses',
  rental: 'cashflow.typeRentals',
  manual: 'cashflow.typeManual',
};

const SOURCE_LABELS = {
  ledger: null,                      // caparra/saldo: label già nella riga
  order: 'cashflow.sourceOrder',     // ordine del gestionale
  manual: 'cashflow.sourceManual',   // entrata manuale pagina Dati
};

function DueRow({ row, overdue, t, i18n, currency, onMarkPaid }) {
  return (
    <tr className="border-b border-border last:border-0">
      <td className="py-2.5 pr-3">
        <p className="text-sm font-medium text-foreground">{row.customer_name || '—'}</p>
        <p className="text-xs text-muted-foreground">
          {row.product_name || row.label || ''}
          {SOURCE_LABELS[row.source] && (
            <span className="ml-1.5 rounded-full border border-border px-1.5 py-0.5 text-[10px] text-muted-foreground">
              {t(SOURCE_LABELS[row.source], { defaultValue: row.source === 'order' ? 'Ordine' : 'Manuale' })}
            </span>
          )}
        </p>
      </td>
      <td className="py-2.5 pr-3 whitespace-nowrap">
        <span className={`text-xs ${overdue ? 'text-[#C97B5D] font-semibold' : 'text-muted-foreground'}`}>
          {overdue && '⚠ '}{dayLabel(row.due_at, i18n.language)}
        </span>
      </td>
      <td className="py-2.5 pr-3 text-right font-mono text-sm text-foreground whitespace-nowrap">
        {formatCurrency(row.amount, currency)}
      </td>
      <td className="py-2.5 text-right whitespace-nowrap">
        {row.source === 'order' && row.order_id && (
          <button
            type="button"
            onClick={() => onMarkPaid(row.order_id)}
            title={t('cashflow.markPaid', { defaultValue: 'Registra pagamento (contanti/bonifico)' })}
            className="mr-1.5 inline-flex h-7 items-center gap-1 rounded-lg border border-[#376254]/40 px-2 text-xs text-[#376254] hover:bg-[#376254]/10"
          >
            <CheckCircle2 className="h-3.5 w-3.5" aria-hidden />
            {t('cashflow.markPaidShort', { defaultValue: 'Incassato' })}
          </button>
        )}
        <ContactActions
          name={row.customer_name}
          email={row.customer_email}
          phone={row.customer_phone}
          customerId={row.customer_id}
          context="payment_reminder"
          vars={{
            amount: formatCurrency(row.amount, currency),
            due_date: dayLabel(row.due_at, i18n.language),
            order_number: row.order_number ? `#${row.order_number}` : '',
          }}
        />
      </td>
    </tr>
  );
}

export default function IncassiPage() {
  const { t, i18n } = useTranslation('common');
  const currency = useCurrency();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [upgradeOpen, setUpgradeOpen] = useState(false);

  const load = useCallback(async (fresh = false) => {
    setLoading(true);
    try {
      const res = await api.get('/analytics/cashflow', { params: fresh ? { fresh: true } : {} });
      setData(res.data);
    } catch { /* la pagina mostra gli empty state */ }
    finally { setLoading(false); }
  }, []);

  // CG1 — incasso registrato a mano (contanti/bonifico): la riga ordine
  // si chiude da qui, senza passare da /orders
  const markPaid = useCallback(async (orderId) => {
    try {
      await api.post(`/orders/${orderId}/mark-paid`);
      // GT4 — recensioni-moat: l'incasso manuale non genera recensioni
      // verificate; il nudge lo ricorda senza bloccare niente
      toast.success(t('cashflow.markPaidOk', { defaultValue: 'Pagamento registrato' }), {
        description: t('cashflow.reviewNudge', { defaultValue: 'Gli incassi manuali non generano recensioni verificate: porta la prossima prenotazione sul calendario pubblico.' }),
      });
      load(true);
    } catch {
      toast.error(t('cashflow.markPaidError', { defaultValue: 'Impossibile registrare il pagamento' }));
    }
  }, [load, t]);
  useEffect(() => { load(); }, [load]);

  const s = data?.summary || {};
  const fmt = (n) => formatCurrency(n || 0, currency);
  const months = (data?.months || []).map((m) => ({
    label: monthLabel(m.month, i18n.language),
    value: m.incassato,
    expected: m.atteso,
  }));
  const dueRows = [
    ...(data?.overdue || []).map((r) => ({ ...r, _overdue: true })),
    ...(data?.upcoming || []),
  ];
  const products = (data?.by_product || []).map((p) => ({
    key: p.product_name, label: p.product_name, value: p.revenue,
  }));
  const typeLabel = (k) => t(TYPE_LABEL_KEYS[k] || 'cashflow.typeOther', { defaultValue: k });
  const types = (data?.by_type || []).map((x) => ({
    key: x.item_type, label: typeLabel(x.item_type), value: x.revenue,
  }));
  const typesTotal = types.reduce((s2, x) => s2 + (x.value > 0 ? x.value : 0), 0);
  const mainType = types.filter((x) => x.value > 0).sort((a, b) => b.value - a.value)[0];
  // GT2 — il banner appare solo quando il Pro conviene DAVVERO (calcolo server)
  const feeSaver = data?.fee_saver;

  return (
    <AppLayout>
      <Header
        title={t('cashflow.title', { defaultValue: 'Incassi' })}
        subtitle={t('cashflow.subtitle', { defaultValue: 'La tua tesoreria: cosa è entrato, cosa arriva, cosa sollecitare.' })}
      />
      <div className="p-4 md:p-8 max-w-5xl space-y-6">

        {/* 1 — come sta andando */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <StatCard loading={loading} icon={Wallet}
                    label={t('cashflow.collected', { defaultValue: 'Incassato (12 mesi)' })}
                    value={fmt(s.incassato)} />
          <StatCard loading={loading} icon={TrendingUp}
                    label={t('cashflow.incoming', { defaultValue: 'In arrivo' })}
                    value={fmt(s.in_arrivo)} />
          <StatCard loading={loading} icon={AlertTriangle} accent={Boolean(s.in_ritardo)}
                    label={t('cashflow.overdue', { defaultValue: 'In ritardo' })}
                    value={fmt(s.in_ritardo)} />
          <StatCard loading={loading} icon={Receipt}
                    label={t('cashflow.avgTicket', { defaultValue: 'Ticket medio' })}
                    value={s.ticket_medio != null ? fmt(s.ticket_medio) : '—'} />
        </div>

        {/* GT2 — calcolatore fee → Pro: numeri veri, mai sotto soglia */}
        {feeSaver?.show && (
          <section className="rounded-2xl border border-[#376254]/30 bg-[#376254]/5 p-4 flex flex-col sm:flex-row sm:items-center gap-3">
            <div className="flex items-start gap-3 flex-1">
              <Sparkles className="h-5 w-5 text-[#376254] mt-0.5 shrink-0" aria-hidden />
              <div>
                <p className="text-sm font-semibold text-foreground">
                  {t('cashflow.feeSaverTitle', {
                    defaultValue: 'Questo mese hai incassato {{volume}} online',
                    volume: fmt(feeSaver.online_volume),
                  })}
                </p>
                <p className="text-xs text-muted-foreground mt-0.5">
                  {t('cashflow.feeSaverBody', {
                    defaultValue: 'Col piano Pro (zero commissioni invece del {{fee}}%) avresti risparmiato {{saving}} questo mese, canone incluso.',
                    fee: feeSaver.current_fee_percent,
                    saving: fmt(feeSaver.monthly_saving),
                  })}
                </p>
              </div>
            </div>
            <button
              type="button"
              onClick={() => setUpgradeOpen(true)}
              className="shrink-0 inline-flex h-9 items-center justify-center rounded-lg bg-[#376254] px-4 text-sm font-medium text-white hover:bg-[#2c4f43]"
            >
              {t('cashflow.feeSaverCta', { defaultValue: 'Scopri il piano Pro' })}
            </button>
          </section>
        )}

        {/* 2 — che direzione ha preso */}
        <section className="rounded-2xl border border-border bg-card p-5">
          <h2 className="font-heading text-base font-semibold text-foreground mb-3">
            {t('cashflow.trendTitle', { defaultValue: 'Incassato e atteso, mese per mese' })}
          </h2>
          <TrendArea
            data={months}
            valueFormatter={(n) => fmt(n)}
            valueLabel={t('cashflow.trendActual', { defaultValue: 'Incassato' })}
            expectedLabel={t('cashflow.trendExpected', { defaultValue: 'Atteso' })}
          />
          <p className="text-xs text-muted-foreground mt-2">
            {t('cashflow.trendHint', { defaultValue: 'La linea tratteggiata include caparre e saldi futuri già concordati: è la tua pianificazione.' })}
          </p>
        </section>

        {/* 3 — cosa faccio adesso */}
        <section className="rounded-2xl border border-border bg-card p-5">
          <h2 className="font-heading text-base font-semibold text-foreground mb-1">
            {t('cashflow.dueTitle', { defaultValue: 'Da incassare' })}
          </h2>
          <p className="text-xs text-muted-foreground mb-3">
            {t('cashflow.dueHint', { defaultValue: 'Scaduti e in scadenza nei prossimi 30 giorni. Il sollecito è a un click — il messaggio è già scritto.' })}
          </p>
          {dueRows.length === 0 ? (
            <div className="rounded-xl border border-dashed border-border p-8 text-center">
              <p className="text-sm text-muted-foreground">
                {t('cashflow.dueEmpty', { defaultValue: 'Nessun pagamento in sospeso. Tutto incassato ✓' })}
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-border text-left">
                    <th className="pb-2 text-xs font-medium text-muted-foreground">{t('cashflow.colCustomer', { defaultValue: 'Cliente' })}</th>
                    <th className="pb-2 text-xs font-medium text-muted-foreground">{t('cashflow.colDue', { defaultValue: 'Scadenza' })}</th>
                    <th className="pb-2 text-xs font-medium text-muted-foreground text-right">{t('cashflow.colAmount', { defaultValue: 'Importo' })}</th>
                    <th className="pb-2 text-xs font-medium text-muted-foreground text-right">{t('cashflow.colAction', { defaultValue: 'Sollecita' })}</th>
                  </tr>
                </thead>
                <tbody>
                  {dueRows.map((r, i) => (
                    <DueRow key={`${r.order_id}-${r.kind}-${i}`} row={r} overdue={Boolean(r._overdue)}
                            t={t} i18n={i18n} currency={currency} onMarkPaid={markPaid} />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        {/* composizione — CG2: prima le ANIME, poi i singoli prodotti */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <section className="rounded-2xl border border-border bg-card p-5">
            <h2 className="font-heading text-base font-semibold text-foreground mb-1">
              {t('cashflow.byTypeTitle', { defaultValue: 'Da cosa guadagni (12 mesi)' })}
            </h2>
            {mainType && typesTotal > 0 && (
              <p className="text-xs text-muted-foreground mb-3">
                {t('cashflow.mainType', {
                  defaultValue: 'Anima principale: {{type}} — {{pct}}% del venduto',
                  type: mainType.label,
                  pct: Math.round((mainType.value / typesTotal) * 100),
                })}
              </p>
            )}
            <DonutSplit data={types} colors={TYPE_COLORS} valueFormatter={(n) => fmt(n)} />
          </section>
          <section className="rounded-2xl border border-border bg-card p-5">
            <h2 className="font-heading text-base font-semibold text-foreground mb-3">
              {t('cashflow.byProductTitle', { defaultValue: 'Venduto per esperienza (12 mesi)' })}
            </h2>
            <DonutSplit data={products} valueFormatter={(n) => fmt(n)} />
          </section>
        </div>
      </div>
      <UpgradeDialog open={upgradeOpen} onOpenChange={setUpgradeOpen} />
    </AppLayout>
  );
}
