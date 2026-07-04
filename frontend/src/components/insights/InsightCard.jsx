/**
 * InsightCard — generic KPI card with info-box flip and optional drill-down.
 *
 * Replica of the cashflow KPICard (frontend/src/features/cashflow/
 * components/KPIStrip.js) with three additions:
 *
 *   • format="currency|number|percent" so the same card renders
 *     EUR 1'234.50, 47, or 12.3 % with no caller boilerplate.
 *   • drillTo prop to declare a click target that filters a sibling
 *     table — the parent page wires the actual navigation.
 *   • actions inline button row (Phase 3 outreach buttons land here).
 *
 * Designed to be domain-agnostic: cashflow could in principle adopt
 * it later. For now it lives next to the cashflow component and the
 * customer-insights feature both consume it from
 * components/insights/.
 */
import React, { useState, useCallback } from 'react';
import { Card, CardContent } from '../ui/card';
import { Skeleton } from '../ui/skeleton';
import { Info, RotateCcw, ArrowUpRight } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { formatCurrency } from '../../lib/utils';

/**
 * @param {object} props
 * @param {string} props.title           label rendered as the card heading
 * @param {number|string|null} props.value
 * @param {'currency'|'number'|'percent'|'raw'} [props.format='number']
 * @param {string} [props.currency='EUR'] for format="currency"
 * @param {{value:number, label?:string, inverse?:boolean}|null} [props.comparison]
 *        delta info for the trend badge
 * @param {{def:string, calc:string, read:string}|string|null} [props.tooltip]
 *        info-box copy. Object → 3-part panel; string → single paragraph.
 * @param {boolean} [props.loading]
 * @param {'success'|'danger'|undefined} [props.variant]
 * @param {boolean} [props.diagnostic] muted styling for supplementary metrics
 * @param {()=>void} [props.onClick]   makes the card itself clickable
 * @param {string} [props.drillLabel]  small "View →" hint on the front side
 * @param {Array<{icon:any,label:string,onClick:()=>void}>} [props.actions]
 */
export const InsightCard = ({
  title,
  value,
  format = 'number',
  currency = 'EUR',
  comparison,
  tooltip,
  loading,
  variant,
  diagnostic,
  onClick,
  drillLabel,
  actions,
}) => {
  const { t, i18n } = useTranslation('customerInsights');
  const [flipped, setFlipped] = useState(false);
  // i18n.language drives every Intl.* call so 47 → "47" (en) /
  // "47" (it) / "47" (de) all render identically for ints, but
  // 1234.5 → "1,234.5" (en) / "1.234,5" (it) — the difference
  // matters for big numbers and the merchant's preferred locale.
  const localeBcp = i18nToBcp47(i18n.language);

  const flip = useCallback((to) => (e) => {
    if (e) e.stopPropagation();
    setFlipped(to);
  }, []);

  const bgClass =
    variant === 'success'
      ? 'bg-emerald-50/40 dark:bg-emerald-950/10 border-emerald-200/70'
      : variant === 'danger'
        ? 'bg-red-50/40 dark:bg-red-950/10 border-red-200/70'
        : diagnostic
          ? 'border-border/50 bg-muted/20'
          : 'border-border';

  if (loading) {
    return (
      <Card className="border border-border">
        <CardContent className="p-4 md:p-5">
          <Skeleton className="h-4 w-24 mb-2" />
          <Skeleton className="h-8 w-32 mb-2" />
          <Skeleton className="h-3.5 w-20" />
        </CardContent>
      </Card>
    );
  }

  // ── BACK SIDE (info-box) ──────────────────────────────────────────
  if (flipped && tooltip) {
    const structured = typeof tooltip === 'object' && tooltip.def;
    return (
      <Card className="border border-primary/20 bg-primary/[0.02]">
        <CardContent className="p-4 md:p-5 flex flex-col justify-between min-h-[130px]">
          <div>
            <p className="text-sm font-semibold text-primary/80 mb-1.5">
              {title}
            </p>
            {structured ? (
              <div className="space-y-1.5 text-xs text-muted-foreground leading-relaxed">
                <p>{tooltip.def}</p>
                <p className="text-muted-foreground/70 italic">
                  {tooltip.calc}
                </p>
                <p className="font-medium text-foreground/70">
                  {tooltip.read}
                </p>
              </div>
            ) : (
              <p className="text-xs text-muted-foreground leading-relaxed">
                {tooltip}
              </p>
            )}
          </div>
          <button
            onClick={flip(false)}
            className="mt-3 flex items-center gap-1 text-xs font-medium text-primary hover:text-primary/80 transition-colors self-start"
          >
            <RotateCcw className="h-3 w-3" />
            {t('insightCard.backButton')}
          </button>
        </CardContent>
      </Card>
    );
  }

  // ── FRONT SIDE ────────────────────────────────────────────────────
  const displayValue = formatValue(value, format, currency, localeBcp);

  const cardContent = (
    <CardContent className="p-4 md:p-5">
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-sm font-medium text-muted-foreground flex items-center gap-1 truncate">
          {title}
          {tooltip && (
            <button
              onClick={flip(true)}
              className="text-muted-foreground/40 hover:text-primary transition-colors flex-shrink-0"
              aria-label={t('insightCard.infoButton')}
              type="button"
            >
              <Info className="h-3 w-3" />
            </button>
          )}
        </span>
        {drillLabel && onClick && (
          <span className="text-xs text-primary/70 hover:text-primary flex items-center gap-0.5">
            {drillLabel}
            <ArrowUpRight className="h-3 w-3" />
          </span>
        )}
      </div>

      <p
        className={`font-heading text-2xl font-bold tracking-tight ${
          diagnostic ? 'text-muted-foreground' : ''
        }`}
      >
        {displayValue}
      </p>

      {comparison?.value != null && (
        <div className="mt-2">
          <TrendBadgeInline {...comparison} />
        </div>
      )}

      {actions && actions.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {actions.map((a, i) => (
            <button
              key={i}
              onClick={(e) => { e.stopPropagation(); a.onClick(); }}
              className="inline-flex items-center gap-1 text-xs px-2 py-1 rounded-md bg-muted hover:bg-muted/80 text-foreground/80 hover:text-foreground transition-colors"
              type="button"
            >
              {a.icon ? <a.icon className="h-3 w-3" /> : null}
              {a.label}
            </button>
          ))}
        </div>
      )}
    </CardContent>
  );

  // Wrap in clickable shell only when onClick is present so non-clickable
  // cards don't steal the cursor pointer.
  if (onClick) {
    return (
      <Card
        className={`border transition-colors hover:border-primary/30 cursor-pointer ${bgClass} ${
          diagnostic ? 'opacity-75' : ''
        }`}
        onClick={onClick}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            onClick();
          }
        }}
      >
        {cardContent}
      </Card>
    );
  }

  return (
    <Card
      className={`border transition-colors hover:border-primary/30 ${bgClass} ${
        diagnostic ? 'opacity-75' : ''
      }`}
    >
      {cardContent}
    </Card>
  );
};


// ──────────────────────────────────────────────────────────────────────
// helpers
// ──────────────────────────────────────────────────────────────────────


/**
 * Format a value according to the requested presentation.
 *
 * `null` and `undefined` render as the em-dash placeholder so the UI
 * never shows "0" for missing data (which would mislead the merchant).
 *
 * The ``locale`` parameter (BCP-47, derived from i18n.language) drives
 * the thousand/decimal separators so a German user sees "1.234,50" and
 * an English user "1,234.50". Without this, the previous hardcoded
 * 'it-IT' would force Italian formatting on every locale.
 */
function formatValue(value, format, currency, locale) {
  if (value == null) return '\u2014';
  if (format === 'currency' && typeof value === 'number') {
    return formatCurrency(value, currency);
  }
  if (format === 'percent' && typeof value === 'number') {
    return `${value.toLocaleString(locale, {
      maximumFractionDigits: 1,
      minimumFractionDigits: 0,
    })}\u00A0%`;
  }
  if (format === 'number' && typeof value === 'number') {
    return value.toLocaleString(locale, { maximumFractionDigits: 0 });
  }
  return String(value);
}


/**
 * Map react-i18next short language codes to BCP-47 locale tags. Falls
 * back to the input untouched for any unknown code so a future locale
 * works without a code change.
 *
 * Notes for Switzerland-adjacent merchants:
 *   • "de" → "de-CH" (apostrophe thousands, "1'234,50") so a Lugano /
 *     Zurich merchant sees CHF amounts in the local convention.
 *   • "fr" → "fr-CH" same reasoning for the Romande area.
 */
function i18nToBcp47(lang) {
  if (!lang) return 'it-IT';
  const l = lang.toLowerCase();
  if (l === 'it') return 'it-IT';
  if (l === 'en') return 'en-US';
  if (l === 'de') return 'de-CH';
  if (l === 'fr') return 'fr-CH';
  return l;
}


/**
 * Inline trend badge. Imports the cashflow TrendBadge would create a
 * tight cross-feature coupling we want to avoid; the implementation is
 * tiny so we keep an InsightCard-local copy.
 *
 * Convention: positive value = up arrow, green when inverse=false.
 */
function TrendBadgeInline({ value, label, inverse = false }) {
  const { i18n } = useTranslation();
  const locale = i18nToBcp47(i18n.language);

  const isPositive = value > 0;
  const isNegative = value < 0;

  // For "inverse" KPIs (like inactive_rate where down is good), flip the
  // sentiment colour without flipping the arrow direction.
  const goodDirection = inverse ? !isPositive : isPositive;
  const colorClass = isPositive || isNegative
    ? goodDirection
      ? 'text-emerald-700 bg-emerald-50 dark:text-emerald-300 dark:bg-emerald-950/30'
      : 'text-red-700 bg-red-50 dark:text-red-300 dark:bg-red-950/30'
    : 'text-muted-foreground bg-muted';

  const arrow = isPositive ? '↑' : isNegative ? '↓' : '→';
  const display =
    typeof value === 'number'
      ? `${arrow} ${Math.abs(value).toLocaleString(locale, {
          maximumFractionDigits: 1,
        })}\u00A0%`
      : arrow;

  return (
    <span
      className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[11px] font-medium ${colorClass}`}
    >
      {display}
      {label ? (
        <span className="text-muted-foreground/80 font-normal">
          {label}
        </span>
      ) : null}
    </span>
  );
}

export default InsightCard;
