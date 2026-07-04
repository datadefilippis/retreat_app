import React from 'react';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { useTranslation } from 'react-i18next';

import { CURRENCY_OPTIONS, DEFAULT_CURRENCY } from '../constants/currencies';

/**
 * CurrencySelector — dropdown to pick the organisation's currency.
 *
 * Single-currency-per-org policy: once any order has been written for
 * the org, the selector becomes disabled. The parent decides this from
 * `GET /api/me/can-change-currency` and passes `disabled` + an optional
 * reason copy to surface in a hint.
 *
 * Props:
 *   value           ISO 4217 code (eg. "EUR" / "CHF"). Default "EUR".
 *   onChange        (newCode: string) => void
 *   disabled        boolean — locks the input.
 *   disabledReason  short string shown under the input when disabled.
 *   className       optional override for the trigger width.
 *   testId          data-testid override (default "currency-select").
 */
export const CurrencySelector = ({
  value = DEFAULT_CURRENCY,
  onChange,
  disabled = false,
  disabledReason,
  className = 'w-56',
  testId = 'currency-select',
}) => {
  const { t } = useTranslation('settings');

  return (
    <div className="flex flex-col gap-1">
      <Select value={value} onValueChange={onChange} disabled={disabled}>
        <SelectTrigger className={className} data-testid={testId}>
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {CURRENCY_OPTIONS.map((opt) => (
            <SelectItem key={opt.value} value={opt.value}>
              {opt.label}
              {opt.region ? ` — ${opt.region}` : ''}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      {disabled && disabledReason ? (
        <p className="text-xs text-muted-foreground" data-testid={`${testId}-disabled-reason`}>
          {disabledReason}
        </p>
      ) : null}

      {!disabled ? (
        <p className="text-xs text-muted-foreground">
          {t(
            'currency.help',
            'Scegli la valuta della tua attività. Una volta creato il primo ordine non potrà più essere modificata.'
          )}
        </p>
      ) : null}
    </div>
  );
};

export default CurrencySelector;
