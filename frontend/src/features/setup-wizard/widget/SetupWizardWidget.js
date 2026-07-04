/**
 * SetupWizardWidget — top-level container for the dashboard setup widget.
 *
 * Public entry point of the setup-wizard feature. The dashboard pins/
 * unpins THIS component; everything else (sections, rows, CTAs, icons)
 * is internal.
 *
 * States rendered:
 *   loading  → skeleton placeholders (no content yet)
 *   error    → inline error banner with retry button
 *   empty    → "no steps" message (backend returned 0 sections; rare —
 *               happens if all steps were filtered out by entitlements)
 *   complete → "setup completo!" celebratory state
 *   normal   → header (progress + headline) + collapsible section list
 *
 * Collapsed view (default): shows progress bar + "Hai N step rimasti" +
 * "next step" pointer + expand chevron.
 * Expanded view: full section list with all steps and CTAs.
 *
 * Pure presentational — data flows in via props from the
 * `useSetupWizard` hook (added in Step 6). The widget itself has only
 * UI state (collapsed/expanded).
 *
 * Props:
 *   data:             SetupWizardResponse | null
 *   loading:          boolean
 *   error:            Error | string | null
 *   onRefresh:        () => void          (optional manual refresh)
 *   onRemove:         () => void          (optional unpin handler)
 *   defaultExpanded:  boolean             (default: false)
 */

import React, { useState, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { Card, CardContent, CardHeader } from '../../../components/ui/card';
import { Button } from '../../../components/ui/button';
import { Skeleton } from '../../../components/ui/skeleton';
import {
  ChevronDown,
  ChevronUp,
  RefreshCw,
  PartyPopper,
  XCircle,
  CircleAlert,
  Sparkles,
} from 'lucide-react';
import { SetupProgressBar } from './SetupProgressBar';
import { SetupSectionGroup } from './SetupSectionGroup';


// ── Loading state ────────────────────────────────────────────────────────────

function LoadingState() {
  return (
    <Card>
      <CardHeader className="space-y-2 pb-3">
        <Skeleton className="h-4 w-1/3" />
        <Skeleton className="h-2 w-full" />
      </CardHeader>
      <CardContent className="space-y-3">
        <Skeleton className="h-3 w-2/3" />
        <Skeleton className="h-3 w-1/2" />
      </CardContent>
    </Card>
  );
}


// ── Error state ──────────────────────────────────────────────────────────────

function ErrorState({ error, onRetry }) {
  const { t } = useTranslation('setup_wizard');
  const message = typeof error === 'string'
    ? error
    : (error?.message || t('widget.error_generic'));
  return (
    <Card>
      <CardContent className="flex items-start gap-3 py-4">
        <CircleAlert className="h-5 w-5 text-destructive shrink-0 mt-0.5" />
        <div className="flex-1 min-w-0 space-y-2">
          <p className="text-sm font-medium">{t('widget.error_title')}</p>
          <p className="text-xs text-muted-foreground">{message}</p>
          {onRetry && (
            <Button size="sm" variant="outline" onClick={onRetry} className="gap-1.5">
              <RefreshCw className="h-3.5 w-3.5" />
              {t('widget.retry')}
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}


// ── Complete state ───────────────────────────────────────────────────────────

function CompleteState({ onRemove }) {
  const { t } = useTranslation('setup_wizard');
  return (
    <Card className="border-emerald-300 bg-emerald-50/40">
      <CardContent className="flex items-start gap-3 py-4">
        <PartyPopper className="h-5 w-5 text-emerald-600 shrink-0 mt-0.5" />
        <div className="flex-1 min-w-0 space-y-1">
          <p className="text-sm font-semibold text-emerald-700">
            {t('widget.complete_title')}
          </p>
          <p className="text-xs text-muted-foreground">
            {t('widget.complete_subtitle')}
          </p>
        </div>
        {onRemove && (
          <Button
            size="sm"
            variant="ghost"
            onClick={onRemove}
            className="gap-1.5 text-muted-foreground"
            aria-label={t('widget.remove_widget')}
          >
            <XCircle className="h-4 w-4" />
          </Button>
        )}
      </CardContent>
    </Card>
  );
}


// ── Empty state (no steps at all — usually means the user is on a plan
//    where everything is already configured, or all sections were
//    filtered out) ──────────────────────────────────────────────────────────

function EmptyState() {
  const { t } = useTranslation('setup_wizard');
  return (
    <Card>
      <CardContent className="py-6 text-center">
        <Sparkles className="mx-auto h-6 w-6 text-muted-foreground/50 mb-2" />
        <p className="text-sm text-muted-foreground">
          {t('widget.empty_title')}
        </p>
      </CardContent>
    </Card>
  );
}


// ── Helper: find next-step row by key (for the headline pointer) ─────────────

function findNextStep(data) {
  if (!data?.next_step_key) return null;
  for (const section of (data.sections || [])) {
    const step = (section.steps || []).find((s) => s.key === data.next_step_key);
    if (step) return step;
  }
  return null;
}


// ── Main widget ──────────────────────────────────────────────────────────────

export function SetupWizardWidget({
  data,
  loading = false,
  error = null,
  onRefresh,
  onRemove,
  defaultExpanded = false,
}) {
  // ── Hooks (MUST be called in the same order on every render — keep
  // them all at the top, before any early return) ───────────────────────
  const { t } = useTranslation('setup_wizard');
  const [expanded, setExpanded] = useState(defaultExpanded);

  // Memos receive `data` directly and handle null defensively, so they
  // can sit above the early-return guards.
  const nextStep = useMemo(() => findNextStep(data), [data]);
  const totalSteps = useMemo(
    () => (data?.sections || []).reduce((acc, sec) => acc + (sec.total_count || 0), 0),
    [data],
  );
  const doneSteps = useMemo(
    () => (data?.sections || []).reduce((acc, sec) => acc + (sec.done_count || 0), 0),
    [data],
  );

  // ── Early-return states (loading / error / empty) ─────────────────────
  if (loading) return <LoadingState />;
  if (error) return <ErrorState error={error} onRetry={onRefresh} />;
  if (!data) return null;

  // ── Complete state (no actionable steps left) ──────────────────────────
  if (data.is_complete) {
    return <CompleteState onRemove={onRemove} />;
  }

  // ── Empty state (zero sections — degenerate but possible) ──────────────
  if (totalSteps === 0) {
    return <EmptyState />;
  }

  const remaining = totalSteps - doneSteps;

  // ── Normal render ──────────────────────────────────────────────────────
  return (
    <Card>
      <CardHeader className="space-y-3 pb-3">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2 min-w-0">
            <Sparkles className="h-4 w-4 text-primary shrink-0" />
            <h2 className="text-sm font-semibold truncate">
              {t('widget.title')}
            </h2>
            {data.plan_name_key && (
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground shrink-0">
                {t(data.plan_name_key)}
              </span>
            )}
          </div>
          <div className="flex items-center gap-1 shrink-0">
            {onRefresh && (
              <Button
                size="icon"
                variant="ghost"
                onClick={onRefresh}
                className="h-7 w-7"
                aria-label={t('widget.refresh')}
              >
                <RefreshCw className="h-3.5 w-3.5" />
              </Button>
            )}
            <Button
              size="icon"
              variant="ghost"
              onClick={() => setExpanded((v) => !v)}
              className="h-7 w-7"
              aria-label={expanded ? t('widget.collapse') : t('widget.expand')}
              aria-expanded={expanded}
            >
              {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            </Button>
          </div>
        </div>

        <SetupProgressBar
          percent={data.progress_pct}
          doneCount={doneSteps}
          totalCount={totalSteps}
        />

        {/* Collapsed-view headline: pointer to the next step */}
        {!expanded && nextStep && (
          <div className="flex items-center justify-between gap-2 pt-1">
            <p className="text-xs text-muted-foreground truncate">
              {t('widget.next_label')}{' '}
              <span className="font-medium text-foreground">
                {t(nextStep.title_key)}
              </span>
            </p>
            <span className="text-[10px] text-muted-foreground shrink-0">
              {t('widget.remaining_count', { count: remaining })}
            </span>
          </div>
        )}
      </CardHeader>

      {/* Expanded body: section list */}
      {expanded && (
        <CardContent className="space-y-5 pt-0">
          {(data.sections || []).map((section) => (
            <SetupSectionGroup key={section.module_key} section={section} />
          ))}

          {onRemove && (
            <div className="pt-2 border-t flex justify-end">
              <Button
                size="sm"
                variant="ghost"
                onClick={onRemove}
                className="text-muted-foreground gap-1.5"
              >
                <XCircle className="h-3.5 w-3.5" />
                {t('widget.remove_widget')}
              </Button>
            </div>
          )}
        </CardContent>
      )}
    </Card>
  );
}
