/**
 * SetupStepRow — one step inside a section group.
 *
 * Layout:
 *   [icon] Title
 *          One-line description.
 *          (hint, only when present)
 *          [primary CTA] [secondary CTA] [ghost CTA]
 *
 * Visual treatments:
 *   - done=true:    title strikethrough-free but muted, status icon green
 *   - required=false: title gets a subtle "consigliato" tag
 *   - hint_key set: small info microcopy under the body
 *
 * Pure presentational. The CTAs row is delegated to <SetupStepCTAs />.
 *
 * Props:
 *   step: SetupStep   from the backend
 */

import React from 'react';
import { useTranslation } from 'react-i18next';
import { CheckCircle2, Circle } from 'lucide-react';
import { Badge } from '../../../components/ui/badge';
import { SetupStepCTAs } from './SetupStepCTAs';


export function SetupStepRow({ step }) {
  const { t } = useTranslation('setup_wizard');

  if (!step) return null;

  const StatusIcon = step.done ? CheckCircle2 : Circle;
  const statusColor = step.done
    ? 'text-emerald-500'
    : 'text-muted-foreground/40';

  // Title color: muted when done (less attention-grabbing once handled).
  const titleColor = step.done
    ? 'text-muted-foreground line-through decoration-1 decoration-muted-foreground/50'
    : 'text-foreground';

  return (
    <div className="flex items-start gap-3 py-2">
      {/* Status icon */}
      <StatusIcon
        className={`mt-0.5 h-4 w-4 shrink-0 ${statusColor}`}
        aria-label={step.done ? t('widget.status_done') : t('widget.status_pending')}
      />

      {/* Body */}
      <div className="flex-1 min-w-0 space-y-1">
        <div className="flex items-baseline gap-2 flex-wrap">
          <span className={`text-sm font-medium ${titleColor}`}>
            {t(step.title_key)}
          </span>
          {!step.required && !step.done && (
            <Badge variant="secondary" className="text-[10px] uppercase tracking-wide">
              {t('widget.optional')}
            </Badge>
          )}
        </div>

        {step.body_key && (
          <p className="text-xs text-muted-foreground leading-snug">
            {t(step.body_key)}
          </p>
        )}

        {step.hint_key && !step.done && (
          <p className="text-xs text-muted-foreground/80 italic leading-snug">
            {t(step.hint_key)}
          </p>
        )}

        {/* CTAs only if not yet done */}
        {!step.done && step.cta_options?.length > 0 && (
          <div className="pt-1">
            <SetupStepCTAs ctas={step.cta_options} />
          </div>
        )}
      </div>
    </div>
  );
}
