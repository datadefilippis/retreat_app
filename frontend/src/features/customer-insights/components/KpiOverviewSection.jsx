/**
 * KpiOverviewSection — the headline KPI grid powered by InsightCard.
 *
 * Each card has the 3-part info-box (def / calc / read) consumed
 * directly from the customerInsights i18n namespace. The overview
 * payload from the backend supplies value + previous + delta_pct
 * per KPI; we hand them straight to InsightCard.
 *
 * Drill-down: at_risk_count and inactive_rate cards are clickable
 * and notify the parent via onSegmentDrill so the table below
 * filters to that segment/status.
 */
import React, { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { useCurrency } from '../../../context/AuthContext';
import InsightCard from '../../../components/insights/InsightCard';

const ORDER = [
  { key: 'active_customers',     i18nKey: 'activeCustomers',     format: 'number' },
  { key: 'new_customers',        i18nKey: 'newCustomers',        format: 'number' },
  { key: 'purchasing_customers', i18nKey: 'purchasingCustomers', format: 'number' },
  { key: 'total_revenue',        i18nKey: 'totalRevenue',        format: 'currency' },
  { key: 'avg_customer_value',   i18nKey: 'avgCustomerValue',    format: 'currency' },
  { key: 'top_10_share_pct',     i18nKey: 'top10Share',          format: 'percent' },
  { key: 'at_risk_count',        i18nKey: 'atRiskCount',         format: 'number',  drill: 'at_risk_status' },
  { key: 'inactive_rate_pct',    i18nKey: 'inactiveRate',        format: 'percent', drill: 'inactive_segment' },
];

export const KpiOverviewSection = ({ kpis, loading, period, onSegmentDrill }) => {
  const { t } = useTranslation('customerInsights');
  const currency = useCurrency();

  const cards = useMemo(() => {
    return ORDER.map(({ key, i18nKey, format, drill }) => {
      const k = kpis?.[key] || {};
      const tooltip = {
        def:  t(`kpi.${i18nKey}.def`),
        calc: t(`kpi.${i18nKey}.calc`),
        read: t(`kpi.${i18nKey}.read`),
      };
      // ``inverse`` for KPIs where down is good (at-risk, inactive rate).
      const inverse = key === 'at_risk_count' || key === 'inactive_rate_pct';

      const onClick = drill ? () => onSegmentDrill?.(drill) : undefined;
      const drillLabel = drill ? '\u2192' : undefined;

      return {
        key,
        title: t(`kpi.${i18nKey}.title`),
        value: k.value,
        comparison: k.delta_pct != null
          ? { value: k.delta_pct, label: t('period.comparedTo'), inverse }
          : null,
        tooltip,
        format,
        currency,
        onClick,
        drillLabel,
      };
    });
  }, [kpis, t, currency, onSegmentDrill]);

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
      {cards.map((c) => (
        <InsightCard
          key={c.key}
          title={c.title}
          value={c.value}
          comparison={c.comparison}
          tooltip={c.tooltip}
          loading={loading}
          format={c.format}
          currency={c.currency}
          onClick={c.onClick}
          drillLabel={c.drillLabel}
        />
      ))}
    </div>
  );
};

export default KpiOverviewSection;
