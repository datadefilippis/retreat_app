/**
 * PeriodSelector — button-group period picker for Insights pages.
 *
 * Originally created for Customer Insights (Phase 2) and moved to the
 * shared ``components/insights/`` directory once Product Performance
 * adopted the same UX pattern (Phase PP.0). The shared location keeps
 * the cross-feature contract explicit: any future Insights-style page
 * imports the same component.
 *
 * Not to be confused with ``components/PeriodSelector.js`` — that one
 * is a dropdown variant tailored to the Cashflow + Dashboard pages
 * (offers custom range and data_range). The two are intentionally
 * different UI affordances for different pages; they share no code.
 *
 * Reads its labels from the ``customerInsights`` i18n namespace
 * (loaded globally in ``i18n.js``), so any caller works out of the box.
 *
 * Props:
 *   value     — current period key ('7d'|'30d'|'90d'|'12m'|'all')
 *   onChange  — (newValue) => void
 */
import React from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../ui/button';

const OPTIONS = ['7d', '30d', '90d', '12m', 'all'];

export const PeriodSelector = ({ value, onChange }) => {
  const { t } = useTranslation('customerInsights');
  return (
    <div className="flex flex-wrap items-center gap-1.5">
      <span className="text-xs font-medium text-muted-foreground mr-2">
        {t('period.label')}
      </span>
      {OPTIONS.map((opt) => {
        const active = value === opt;
        return (
          <Button
            key={opt}
            size="sm"
            variant={active ? 'default' : 'outline'}
            className="h-7 text-xs px-2.5"
            onClick={() => onChange(opt)}
          >
            {t(`period.${opt}`)}
          </Button>
        );
      })}
    </div>
  );
};

export default PeriodSelector;
