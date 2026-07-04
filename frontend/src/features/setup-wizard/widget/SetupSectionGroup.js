/**
 * SetupSectionGroup — one module's section in the wizard.
 *
 * Layout:
 *   [icon] Section title                  (3/6 fatti)
 *          optional description
 *          ──────────────────
 *          [step row 1]
 *          [step row 2]
 *          ...
 *
 * Renders nothing (returns null) when the section has zero steps. The
 * orchestrator (SetupWizardWidget) decides which sections to render based
 * on what the backend returns.
 *
 * Pure presentational. Section icon resolved via stepIcons.SECTION_ICONS.
 *
 * Props:
 *   section: SetupSection   from the backend
 */

import React from 'react';
import { useTranslation } from 'react-i18next';
import { getSectionIcon } from '../lib/stepIcons';
import { SetupStepRow } from './SetupStepRow';


export function SetupSectionGroup({ section }) {
  const { t } = useTranslation('setup_wizard');

  if (!section || !section.steps?.length) {
    return null;
  }

  const SectionIcon = getSectionIcon(section.module_key);
  const isComplete = section.done_count >= section.total_count;

  return (
    <section className="space-y-2">
      {/* Section header */}
      <div className="flex items-center justify-between gap-2 pb-1 border-b">
        <div className="flex items-center gap-2 min-w-0">
          <SectionIcon
            className={`h-4 w-4 shrink-0 ${isComplete ? 'text-emerald-500' : 'text-muted-foreground'}`}
          />
          <h3 className="text-sm font-semibold truncate">
            {t(section.title_key)}
          </h3>
          {section.badge_key && (
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground">
              {t(section.badge_key)}
            </span>
          )}
        </div>
        <span className="text-xs text-muted-foreground tabular-nums shrink-0">
          {section.done_count} / {section.total_count}
        </span>
      </div>

      {section.description_key && (
        <p className="text-xs text-muted-foreground leading-snug">
          {t(section.description_key)}
        </p>
      )}

      {/* Step rows */}
      <div className="divide-y divide-border/40">
        {section.steps.map((step) => (
          <SetupStepRow key={step.key} step={step} />
        ))}
      </div>
    </section>
  );
}
