/**
 * SetupStepCTAs — render 1..3 call-to-action buttons for a step.
 *
 * The first CTA is "primary" (filled), subsequent CTAs are "secondary"
 * or "ghost" depending on the variant declared by the backend. The user
 * sees a row of buttons and can choose any path (e.g. manual vs CSV
 * import for "Carica primi dati cashflow").
 *
 * Pure presentational — no state, no fetching. Click → navigate via
 * react-router <Link>. Anchors (`#section-foo`) inside hrefs are honoured.
 *
 * Props:
 *   ctas: SetupCTA[]   from the backend (max 3)
 */

import React from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../components/ui/button';
import { getCtaIcon } from '../lib/stepIcons';


function variantToButtonProps(variant) {
  // Map backend's symbolic variant → shadcn Button `variant` prop.
  // Defaults to "default" so a misconfigured CTA still renders something
  // visible (no invisible buttons).
  switch (variant) {
    case 'primary':   return { variant: 'default', className: '' };
    case 'secondary': return { variant: 'outline', className: '' };
    case 'ghost':     return { variant: 'ghost',   className: 'text-muted-foreground' };
    default:          return { variant: 'default', className: '' };
  }
}


export function SetupStepCTAs({ ctas = [] }) {
  const { t } = useTranslation('setup_wizard');

  if (!ctas.length) return null;

  return (
    <div className="flex flex-wrap items-center gap-2">
      {ctas.map((cta, idx) => {
        const Icon = getCtaIcon(cta.icon_key);
        const { variant, className } = variantToButtonProps(cta.variant);

        return (
          <Link key={`${cta.label_key}-${idx}`} to={cta.href}>
            <Button
              type="button"
              size="sm"
              variant={variant}
              className={`gap-1.5 ${className}`}
            >
              {Icon && <Icon className="h-3.5 w-3.5" />}
              {t(cta.label_key)}
            </Button>
          </Link>
        );
      })}
    </div>
  );
}
