import React from 'react';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { computePeriodDates } from '../lib/utils';
import { useTranslation } from 'react-i18next';

/**
 * PeriodSelector — reusable dropdown for period selection.
 * Labels are translated via common:period.* keys.
 */
export const PeriodSelector = ({
  period,
  onPeriodChange,
  dataDateRange,
  className = 'w-36 sm:w-44',
}) => {
  const { t } = useTranslation('common');

  return (
    <Select value={period} onValueChange={onPeriodChange}>
      <SelectTrigger className={className} data-testid="period-select">
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="7d">{t('period.7d')}</SelectItem>
        <SelectItem value="30d">{t('period.30d')}</SelectItem>
        <SelectItem value="90d">{t('period.90d')}</SelectItem>
        <SelectItem value="ytd">{t('period.ytd')}</SelectItem>
        <SelectItem value="mtd">{t('period.mtd')}</SelectItem>
        <SelectItem value="custom">{t('period.custom')}</SelectItem>
        {dataDateRange?.has_data && (
          <SelectItem value="data_range">
            {t('period.data_range', { days: dataDateRange.days_of_data })}
          </SelectItem>
        )}
      </SelectContent>
    </Select>
  );
};

export default PeriodSelector;
