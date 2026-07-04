/**
 * SetupProgressBar — visual progress indicator for the wizard widget.
 *
 * Renders:
 *   ▓▓▓▓▓▓▓░░░░░░░░░  62%   ·   8 di 13 fatti
 *
 * Pure presentational. No state. No data fetching.
 *
 * Props:
 *   percent     number (0-100)
 *   doneCount   number
 *   totalCount  number
 *   labelKey    optional i18n key for the trailing "X di Y fatti" copy.
 *               Defaults to 'widget.progress_label'.
 */

import React from 'react';
import { useTranslation } from 'react-i18next';

export function SetupProgressBar({
  percent = 0,
  doneCount = 0,
  totalCount = 0,
  labelKey = 'widget.progress_label',
}) {
  const { t } = useTranslation('setup_wizard');

  // Defensive clamp — never let a backend bug push the bar past 100% or
  // below 0.
  const clamped = Math.max(0, Math.min(100, Math.round(percent)));

  // Visual treatment changes once you cross the finish line. Green when
  // complete, brand color (currently the default --primary) otherwise.
  const isDone = clamped >= 100;
  const fillClass = isDone
    ? 'bg-emerald-500'
    : 'bg-primary';

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span className="font-semibold text-foreground tabular-nums">
          {clamped}%
        </span>
        <span>
          {t(labelKey, { done: doneCount, total: totalCount })}
        </span>
      </div>
      <div
        className="h-2 w-full rounded-full bg-muted overflow-hidden"
        role="progressbar"
        aria-valuenow={clamped}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div
          className={`h-full rounded-full transition-all duration-300 ease-out ${fillClass}`}
          style={{ width: `${clamped}%` }}
        />
      </div>
    </div>
  );
}
