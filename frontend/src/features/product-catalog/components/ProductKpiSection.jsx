/**
 * ProductKpiSection — the headline KPI grid for Product Performance.
 *
 * Mirrors the pattern used by Customer Insights' ``KpiOverviewSection``:
 * each card is an ``InsightCard`` driven by an ``ORDER`` array and the
 * three-part i18n tooltip (def + calc + read) so non-technical users
 * understand what every number means and how it's computed.
 *
 * Layout
 * ──────
 * Renders TWO rows logically: Tier 1 (headline) and Tier 2
 * (operational). Both use the same responsive grid; the Tier label is
 * rendered above each group so the page tells a story rather than
 * dumping ten cards in a single flat row.
 *
 * Drill-down
 * ──────────
 * ``onProductDrill(productId)`` is invoked when the user clicks the
 * Top seller or Most profitable card. The parent page is responsible
 * for opening the right detail view (slide-over, modal, or navigate).
 *
 * Loading
 * ───────
 * Forwarded to every InsightCard which already renders a skeleton.
 */

import React, { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { useCurrency } from '../../../context/AuthContext';
import InsightCard from '../../../components/insights/InsightCard';


// Each entry maps a KPI key (matching the backend ``kpi`` envelope) to:
//   - i18nKey:  i18n group under ``kpi.<i18nKey>.{title,def,calc,read}``
//   - format:   InsightCard format ('currency'|'number'|'percent'|'raw')
//   - inverse:  true when a higher value is bad (none for products today)
//   - subType:  'pair' for KPIs that ship {value, subvalue, product_id}
//               instead of {value, previous, delta_pct}
//   - drill:    when present, the card surfaces a drill arrow

const ORDER_TIER1 = [
  { key: 'totalRevenue',     i18nKey: 'totalRevenue',     format: 'currency' },
  { key: 'totalCost',        i18nKey: 'totalCost',        format: 'currency' },
  { key: 'weightedMargin',   i18nKey: 'weightedMargin',   format: 'percent' },
  { key: 'avgMargin',        i18nKey: 'avgMargin',        format: 'percent' },
  { key: 'activeProducts',   i18nKey: 'activeProducts',   format: 'number'  },
  { key: 'productsWithSales',i18nKey: 'productsWithSales',format: 'number'  },
];

const ORDER_TIER2 = [
  { key: 'topSeller',        i18nKey: 'topSeller',        subType: 'pair',  drill: true },
  { key: 'mostProfitable',   i18nKey: 'mostProfitable',   subType: 'pair',  drill: true },
  { key: 'costCoverage',     i18nKey: 'costCoverage',     format: 'percent' },
  { key: 'top10Concentration', i18nKey: 'top10Concentration', format: 'percent' },
];


export default function ProductKpiSection({ kpi, loading, onProductDrill }) {
  const { t } = useTranslation('product_catalog');
  const currency = useCurrency();

  const renderCard = ({ key, i18nKey, format, subType, drill }) => {
    const data = kpi?.[key] || {};
    const tooltip = {
      def:  t(`kpi.${i18nKey}.def`),
      calc: t(`kpi.${i18nKey}.calc`),
      read: t(`kpi.${i18nKey}.read`),
    };

    if (subType === 'pair') {
      // Pair-shape KPIs (topSeller, mostProfitable) carry a primary
      // string + a subvalue (revenue/profit). Use 'raw' format so the
      // card renders the value as-is rather than trying to format
      // a product name as currency.
      const productId = data.product_id;
      const onClick = (drill && productId)
        ? () => onProductDrill?.(productId)
        : undefined;
      return (
        <InsightCard
          key={key}
          title={t(`kpi.${i18nKey}.title`)}
          value={data.value || '—'}
          format="raw"
          comparison={null}
          tooltip={tooltip}
          loading={loading}
          onClick={onClick}
          drillLabel={onClick ? '→' : undefined}
        />
      );
    }

    return (
      <InsightCard
        key={key}
        title={t(`kpi.${i18nKey}.title`)}
        value={data.value}
        format={format}
        currency={currency}
        comparison={data.delta_pct != null
          ? { value: data.delta_pct, label: t('period.comparedTo') }
          : null}
        tooltip={tooltip}
        loading={loading}
      />
    );
  };

  return (
    <div className="space-y-4">
      {/* Tier 1 — Headline */}
      <div>
        <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
          {t('sections.headline')}
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
          {ORDER_TIER1.map(renderCard)}
        </div>
      </div>

      {/* Tier 2 — Operational insights */}
      <div>
        <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
          {t('sections.operational')}
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3">
          {ORDER_TIER2.map(renderCard)}
        </div>
      </div>
    </div>
  );
}
