/**
 * SkuField — Input + inline availability indicator.
 *
 * 2026-05-20 — Drop-in field that pairs with ``useSkuAvailability`` to
 * give the merchant immediate feedback on SKU conflicts while they
 * type. Used in PhysicalWizard, DigitalWizard, and any other place
 * where the form captures a free-text SKU.
 *
 * Props:
 *   value: string                       — current SKU
 *   onChange: (e) => void               — standard input handler
 *   excludeProductId?: string           — pass when editing an existing
 *                                         product so its own SKU is
 *                                         not flagged as a conflict.
 *   ...rest                             — forwarded to <Input>
 *
 * Visual states:
 *   idle       — no indicator
 *   checking   — pulsing dot
 *   available  — green check
 *   taken      — red X with tooltip "SKU già usato"
 *   error      — silently falls back to "available" (soft-fail UX)
 */

import React from 'react';
import { useTranslation } from 'react-i18next';
import { Check, Loader2, X } from 'lucide-react';

import { Input } from './input';
import { useSkuAvailability } from '../../hooks/useSkuAvailability';


export function SkuField({
  value,
  onChange,
  excludeProductId,
  className,
  ...rest
}) {
  const { t } = useTranslation('products');
  const { state } = useSkuAvailability(value, { excludeProductId });

  return (
    <div className={`relative ${className || ''}`}>
      <Input
        value={value || ''}
        onChange={onChange}
        autoComplete="off"
        spellCheck={false}
        className="pr-9"
        {...rest}
      />
      <div className="absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none">
        {state === 'checking' && (
          <Loader2
            className="h-4 w-4 text-muted-foreground animate-spin"
            aria-label={t('wizards.common.sku.checking', { defaultValue: 'Verifica in corso' })}
          />
        )}
        {state === 'available' && (
          <Check
            className="h-4 w-4 text-emerald-600"
            aria-label={t('wizards.common.sku.available', { defaultValue: 'SKU disponibile' })}
          />
        )}
        {state === 'taken' && (
          <X
            className="h-4 w-4 text-red-600"
            aria-label={t('wizards.common.sku.taken', { defaultValue: 'SKU già usato' })}
          />
        )}
      </div>
      {state === 'taken' && (
        <p className="text-xs text-red-600 mt-1">
          {t('wizards.common.sku.takenHint', {
            defaultValue: 'Questo SKU è già usato da un altro prodotto. Scegline uno diverso.',
          })}
        </p>
      )}
    </div>
  );
}


export default SkuField;
