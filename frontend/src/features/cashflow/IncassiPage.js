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
import { Wallet, TrendingUp, AlertTriangle, Receipt } from 'lucide-react';
import api from '../../api/client';
import { AppLayout, Header } from '../../components/Layout';
import { StatCard, TrendArea, DonutSplit } from '../../components/charts';
import ContactActions from '../../components/ContactActions';
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

function DueRow({ row, overdue, t, i18n, currency }) {
  return (
    <tr className="border-b border-border last:border-0">
      <td className="py-2.5 pr-3">
        <p className="text-sm font-medium text-foreground">{row.customer_name || '—'}</p>
        <p className="text-xs text-muted-foreground">{row.product_name || row.label || ''}</p>
      </td>
      <td className="py-2.5 pr-3 whitespace-nowrap">
        <span className={`text-xs ${overdue ? 'text-[#C97B5D] font-semibold' : 'text-muted-foreground'}`}>
          {overdue && '⚠ '}{dayLabel(row.due_at, i18n.language)}
        </span>
      </td>
      <td className="py-2.5 pr-3 text-right font-mono text-sm text-foreground whitespace-nowrap">
        {formatCurrency(row.amount, currency)}
      </td>
      <td className="py-2.5 text-right">
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

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get('/analytics/cashflow');
      setData(res.data);
    } catch { /* la pagina mostra gli empty state */ }
    finally { setLoading(false); }
  }, []);
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
                            t={t} i18n={i18n} currency={currency} />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        {/* composizione */}
        <section className="rounded-2xl border border-border bg-card p-5">
          <h2 className="font-heading text-base font-semibold text-foreground mb-3">
            {t('cashflow.byProductTitle', { defaultValue: 'Venduto per esperienza (12 mesi)' })}
          </h2>
          <DonutSplit data={products} valueFormatter={(n) => fmt(n)} />
        </section>
      </div>
    </AppLayout>
  );
}
