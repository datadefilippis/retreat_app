import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from '../../../components/ui/card';
import { Button } from '../../../components/ui/button';
import { Badge } from '../../../components/ui/badge';
import { Skeleton } from '../../../components/ui/skeleton';
import { Input } from '../../../components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../../components/ui/select';
import {
  Accordion,
  AccordionItem,
  AccordionTrigger,
  AccordionContent,
} from '../../../components/ui/accordion';
import {
  FileText,
  RefreshCw,
  Calendar,
  TrendingUp,
  TrendingDown,
  TrendingUp as TrendUp,
  Activity,
  Clock,
  Sparkles,
  AlertTriangle,
  CheckCircle2,
  Target,
  Info,
} from 'lucide-react';
import { digestsAPI } from '../../../api';
import { toast } from 'sonner';
import { formatDate, formatCurrency } from '../../../lib/utils';
import { useAiAccess } from '../../../hooks/useAiAccess';

/**
 * DigestTab — Wave 12 redesign.
 *
 * The pre-Wave-12 markdown renderer only knew `**bold**` + bullet lists.
 * The pre-Wave-12 digest content was a 4-line summary ("Score / Revenue
 * / Outflows / Margin") that left the user with "4 numeri senza
 * intelligenza" — the audit's exact wording.
 *
 * Wave 12 changes (frontend side):
 *   - Enhanced markdown renderer: ## H2 / ### H3 / > callouts /
 *     numbered priority lists / inline KPI highlighting.
 *   - DigestHero: visual hero with health score chip + key KPIs above
 *     the fold so the merchant grasps the verdict in 2 seconds.
 *   - HealthDimensionsCard: mini-gauges for the 5 health dimensions
 *     with the WEAKEST one called out.
 *   - PriorityActionsPanel: numbered, color-coded actions parsed from
 *     "## Azioni Prioritarie" so they pop visually.
 *   - Section icons + colored dividers on the rendered digest.
 *
 * The new prompt produces 7 sections; the renderer maps each ## header
 * to an icon for visual scannability:
 *   TL;DR / Salute / Performance / Driver / Rischi / Azioni / Prospettive
 */

/* ── Section icon map ───────────────────────────────────────────────────── */

const SECTION_ICONS = {
  // Italian
  'tl;dr': Sparkles, 'tldr': Sparkles,
  'salute': Activity, 'salute finanziaria': Activity,
  'performance': TrendUp, 'performance del periodo': TrendUp,
  'driver': Target, 'driver del risultato': Target,
  'rischi': AlertTriangle, 'rischi e anomalie': AlertTriangle,
  'azioni': CheckCircle2, 'azioni prioritarie': CheckCircle2,
  'prospettive': TrendingUp,
  // English
  'summary': Sparkles, 'overview': Sparkles,
  'health': Activity, 'financial health': Activity,
  'drivers': Target,
  'risks': AlertTriangle, 'risks and anomalies': AlertTriangle,
  'actions': CheckCircle2, 'priority actions': CheckCircle2,
  'outlook': TrendingUp,
};

function iconForSection(title) {
  const key = (title || '').toLowerCase().trim();
  return SECTION_ICONS[key] || null;
}

/* ── Enhanced Markdown renderer ─────────────────────────────────────────── */

/**
 * Wave 12 renderer. Handles:
 *   - `## H2` → section with icon + colored divider
 *   - `### H3` → sub-section title
 *   - `> ` callout boxes
 *   - `1.` / `2.` numbered priority lists (color-coded by index)
 *   - `- ` / `* ` bullet lists
 *   - `**bold**` inline emphasis (KPI values)
 *   - blank lines as paragraph separators
 *
 * Numbered lists inside "Azioni Prioritarie" get color-coded urgency:
 *   1 = red (top priority), 2 = amber, 3+ = blue.
 */
const DigestMarkdown = ({ content }) => {
  if (!content) return null;

  const lines = content.split('\n');
  const elements = [];
  let listItems = [];
  let numberedItems = [];
  let calloutLines = [];
  let key = 0;
  let inActionsSection = false;

  const renderInline = (text) => {
    // **bold** → <strong>
    const parts = text.split(/\*\*(.*?)\*\*/g);
    return parts.map((part, i) =>
      i % 2 === 1 ? (
        <strong key={i} className="text-foreground font-semibold">{part}</strong>
      ) : (
        part
      )
    );
  };

  const flushBullets = () => {
    if (listItems.length > 0) {
      elements.push(
        <ul key={key++} className="my-2 pl-5 space-y-1.5 list-disc marker:text-muted-foreground/60">
          {listItems.map((item, i) => (
            <li key={i} className="text-[13px] text-muted-foreground leading-relaxed">
              {renderInline(item)}
            </li>
          ))}
        </ul>
      );
      listItems = [];
    }
  };

  const flushNumbered = () => {
    if (numberedItems.length > 0) {
      const colors = ['bg-red-500', 'bg-amber-500', 'bg-blue-500', 'bg-emerald-500'];
      elements.push(
        <ol key={key++} className="my-3 space-y-2">
          {numberedItems.map((item, i) => (
            <li key={i} className="flex gap-3 items-start">
              <span
                className={`flex-shrink-0 h-6 w-6 rounded-full ${colors[Math.min(i, 3)]} text-white text-xs font-bold flex items-center justify-center`}
              >
                {i + 1}
              </span>
              <span className="text-[13px] text-foreground leading-relaxed pt-0.5">
                {renderInline(item)}
              </span>
            </li>
          ))}
        </ol>
      );
      numberedItems = [];
    }
  };

  const flushCallout = () => {
    if (calloutLines.length > 0) {
      elements.push(
        <div key={key++} className="my-3 border-l-4 border-blue-400 bg-blue-50 dark:bg-blue-950/30 dark:border-blue-700 rounded-r-md py-2 px-3">
          <div className="flex gap-2 items-start">
            <Info className="h-4 w-4 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
            <div className="text-[13px] text-blue-900 dark:text-blue-200 leading-relaxed">
              {calloutLines.map((line, i) => (
                <p key={i} className={i > 0 ? 'mt-1' : ''}>{renderInline(line)}</p>
              ))}
            </div>
          </div>
        </div>
      );
      calloutLines = [];
    }
  };

  const flushAll = () => { flushBullets(); flushNumbered(); flushCallout(); };

  for (const line of lines) {
    const trimmed = line.trim();

    // Empty line → flush
    if (!trimmed) {
      flushAll();
      continue;
    }

    // ## H2 header
    const h2Match = trimmed.match(/^##\s+(.+)$/);
    if (h2Match) {
      flushAll();
      const title = h2Match[1].trim();
      inActionsSection = /azioni|action/i.test(title);
      const Icon = iconForSection(title);
      elements.push(
        <div key={key++} className="mt-5 mb-2 first:mt-0">
          <h3 className="text-sm font-bold text-foreground flex items-center gap-2 uppercase tracking-wide">
            {Icon && <Icon className="h-4 w-4 text-blue-600" />}
            {title}
          </h3>
          <div className="h-[2px] bg-gradient-to-r from-blue-500/60 to-transparent mt-1" />
        </div>
      );
      continue;
    }

    // ### H3 header
    const h3Match = trimmed.match(/^###\s+(.+)$/);
    if (h3Match) {
      flushAll();
      elements.push(
        <h4 key={key++} className="text-[13px] font-semibold text-foreground mt-3 mb-1">
          {renderInline(h3Match[1])}
        </h4>
      );
      continue;
    }

    // Callout (> text)
    if (trimmed.startsWith('>')) {
      flushBullets();
      flushNumbered();
      calloutLines.push(trimmed.replace(/^>\s?/, '').trim());
      continue;
    }
    if (calloutLines.length > 0 && !trimmed.startsWith('>')) {
      flushCallout();
    }

    // Numbered list item
    const numMatch = trimmed.match(/^(\d+)[.)]\s+(.+)/);
    if (numMatch && inActionsSection) {
      flushBullets();
      numberedItems.push(numMatch[2]);
      continue;
    }
    if (numMatch && !inActionsSection) {
      // Outside actions: render as plain numbered list (bullets style)
      flushBullets();
      listItems.push(numMatch[2]);
      continue;
    }

    // Bullet
    const bullMatch = trimmed.match(/^[-*•]\s+(.+)/);
    if (bullMatch) {
      flushNumbered();
      listItems.push(bullMatch[1]);
      continue;
    }

    // Single-bold line as header-ish
    const allBoldMatch = trimmed.match(/^\*\*(.+?)\*\*$/);
    if (allBoldMatch) {
      flushAll();
      elements.push(
        <h4 key={key++} className="text-sm font-semibold text-foreground mt-3 mb-1">
          {allBoldMatch[1]}
        </h4>
      );
      continue;
    }

    // Plain paragraph
    flushAll();
    elements.push(
      <p key={key++} className="text-[13px] leading-relaxed text-muted-foreground my-2">
        {renderInline(trimmed)}
      </p>
    );
  }

  flushAll();

  return <div>{elements}</div>;
};

/* ── Health Dimensions Card — Wave 12.C ─────────────────────────────────── */

const DIM_COLORS = {
  excellent: 'bg-emerald-500',
  ok: 'bg-emerald-500',
  warning: 'bg-amber-500',
  critical: 'bg-red-500',
  not_computable: 'bg-gray-300',
  disabled: 'bg-gray-200',
};

const DimensionBar = ({ dim }) => {
  const pts = dim.points;
  const max = dim.max || 1;
  const computable = pts != null;
  const pct = computable ? Math.round((pts / max) * 100) : 0;
  const colorClass = DIM_COLORS[dim.level] || DIM_COLORS.not_computable;
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between gap-2">
        <span className="text-[11px] font-medium text-foreground truncate">{dim.dimension}</span>
        <span className="text-[11px] text-muted-foreground tabular-nums whitespace-nowrap">
          {computable ? `${pts}/${max}` : 'N/D'}
        </span>
      </div>
      <div className="h-2 bg-gray-100 dark:bg-gray-800 rounded overflow-hidden">
        {computable && (
          <div
            className={`h-full ${colorClass} transition-all`}
            style={{ width: `${pct}%` }}
          />
        )}
      </div>
    </div>
  );
};

const HealthDimensionsCard = ({ digest, t }) => {
  // The health_score breakdown is not (yet) exposed via the Digest API
  // — for Wave 12 we read it from the digest's parsed sections content
  // via heuristic: if the markdown ## "Salute Finanziaria" section
  // mentions specific dimension names. Until the backend exposes the
  // breakdown explicitly on the Digest model, this card stays opt-in.
  //
  // For now this card stays HIDDEN unless the backend explicitly
  // exposes digest.health_breakdown (future enhancement). Returning
  // null is intentional — the DigestHero already shows the score.
  return null;
};

/* ── KPI chips ─────────────────────────────────────────────────────────────── */

const KpiChips = ({ kpis, currency = 'EUR', t }) => {
  if (!kpis) return null;
  const net = kpis.net_after_fixed;
  const score = kpis.health_score;
  const margin = kpis.operating_margin_pct;

  return (
    <div className="flex items-center gap-2 flex-wrap">
      {net != null && (
        <Badge
          variant="outline"
          className={`text-xs gap-1 whitespace-nowrap ${
            net >= 0
              ? 'border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-800 dark:bg-emerald-950 dark:text-emerald-400'
              : 'border-red-200 bg-red-50 text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-400'
          }`}
        >
          {net >= 0 ? (
            <TrendingUp className="h-3 w-3" />
          ) : (
            <TrendingDown className="h-3 w-3" />
          )}
          {formatCurrency(net, currency)}
        </Badge>
      )}
      {score != null && (
        <Badge
          variant="outline"
          className={`text-xs gap-1 whitespace-nowrap ${
            score >= 70
              ? 'border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-800 dark:bg-emerald-950 dark:text-emerald-400'
              : score >= 40
                ? 'border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-400'
                : 'border-red-200 bg-red-50 text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-400'
          }`}
        >
          <Activity className="h-3 w-3" />
          {score}/100
        </Badge>
      )}
      {margin != null && (
        <Badge variant="outline" className="text-xs gap-1 whitespace-nowrap">
          {t('digest.margin_label', { value: margin.toFixed(1) })}
        </Badge>
      )}
    </div>
  );
};

/* ── DigestHero — Wave 12.C visual band ─────────────────────────────────── */

const DigestHero = ({ digest, currency, t }) => {
  if (!digest) return null;
  const kpis = digest.kpis_summary || {};
  const score = kpis.health_score;
  const net = kpis.net_after_fixed;
  const sales = kpis.total_sales;
  const margin = kpis.operating_margin_pct;

  const scoreColor =
    score >= 70 ? 'emerald' :
    score >= 40 ? 'amber' : 'red';

  const scoreBg = {
    emerald: 'bg-emerald-500/10 border-emerald-500/30 text-emerald-700 dark:text-emerald-300',
    amber: 'bg-amber-500/10 border-amber-500/30 text-amber-700 dark:text-amber-300',
    red: 'bg-red-500/10 border-red-500/30 text-red-700 dark:text-red-300',
  }[scoreColor];

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-2">
      {/* Score gauge */}
      <div className={`rounded-lg border-2 ${scoreBg} p-3 flex flex-col justify-between min-h-[88px]`}>
        <div className="text-[10px] uppercase tracking-wider opacity-70 font-semibold">
          Health Score
        </div>
        <div className="flex items-baseline gap-1">
          <span className="text-3xl font-bold tabular-nums">
            {score != null ? score : '—'}
          </span>
          <span className="text-[11px] opacity-60">/100</span>
        </div>
      </div>
      {/* Net result */}
      <div className={`rounded-lg border p-3 flex flex-col justify-between min-h-[88px] ${
        net >= 0
          ? 'border-emerald-200 bg-emerald-50/50 dark:border-emerald-800 dark:bg-emerald-950/20'
          : 'border-red-200 bg-red-50/50 dark:border-red-800 dark:bg-red-950/20'
      }`}>
        <div className="text-[10px] uppercase tracking-wider text-muted-foreground font-semibold">
          {t('digest.hero_net', 'Risultato netto')}
        </div>
        <div className={`text-xl font-bold tabular-nums ${net >= 0 ? 'text-emerald-700 dark:text-emerald-300' : 'text-red-700 dark:text-red-300'}`}>
          {net != null ? formatCurrency(net, currency) : '—'}
        </div>
      </div>
      {/* Revenue */}
      <div className="rounded-lg border border-border bg-card p-3 flex flex-col justify-between min-h-[88px]">
        <div className="text-[10px] uppercase tracking-wider text-muted-foreground font-semibold">
          {t('digest.hero_revenue', 'Ricavi')}
        </div>
        <div className="text-xl font-bold tabular-nums text-foreground">
          {sales != null ? formatCurrency(sales, currency) : '—'}
        </div>
      </div>
      {/* Margin */}
      <div className="rounded-lg border border-border bg-card p-3 flex flex-col justify-between min-h-[88px]">
        <div className="text-[10px] uppercase tracking-wider text-muted-foreground font-semibold">
          {t('digest.hero_margin', 'Margine')}
        </div>
        <div className={`text-xl font-bold tabular-nums ${
          (margin ?? 0) >= 10
            ? 'text-emerald-700 dark:text-emerald-300'
            : (margin ?? 0) >= 0
              ? 'text-amber-700 dark:text-amber-300'
              : 'text-red-700 dark:text-red-300'
        }`}>
          {margin != null ? `${margin.toFixed(1)}%` : '—'}
        </div>
      </div>
    </div>
  );
};

/* ── Type label helper ─────────────────────────────────────────────────────── */

const typeLabel = (type, t) => (type === 'weekly' ? t('digest.type_weekly') : t('digest.type_monthly'));

/* ── Featured Digest Card (latest, always expanded) ────────────────────────── */

const FeaturedDigestCard = ({ digest, currency = 'EUR', t, onDownloadPdf }) => {
  if (!digest) return null;

  return (
    <Card className="border-2 border-primary/20 shadow-sm">
      <CardHeader className="pb-3">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
          <div className="space-y-1.5">
            <div className="flex items-center gap-2">
              <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary/10">
                <Sparkles className="h-3.5 w-3.5 text-primary" />
              </div>
              <CardTitle className="text-base">
                Digest {typeLabel(digest.digest_type, t)}
              </CardTitle>
              <Badge className="text-[10px] bg-primary/10 text-primary border-0 hover:bg-primary/10">
                {t('digest.badge_latest')}
              </Badge>
            </div>
            <CardDescription className="flex items-center gap-2 flex-wrap">
              <span className="flex items-center gap-1">
                <Calendar className="h-3 w-3" />
                {formatDate(digest.period_start)} → {formatDate(digest.period_end)}
              </span>
              {digest.model_version && (
                <span className="text-[10px] bg-muted px-1.5 py-0.5 rounded font-mono">
                  {digest.model_version}
                </span>
              )}
              <span className="flex items-center gap-1 text-[11px] text-muted-foreground/60">
                <Clock className="h-3 w-3" />
                {formatDate(digest.created_at)}
              </span>
            </CardDescription>
          </div>
        </div>
        {/* Wave 12.C — visual hero band replaces the small KpiChips at the top */}
        <DigestHero digest={digest} currency={currency} t={t} />
      </CardHeader>
      <CardContent className="pt-0">
        <div className="border-t pt-4">
          <DigestMarkdown content={digest.content} />
          {digest.has_pdf && (
            <div className="mt-4 pt-3 border-t">
              <Button
                size="sm"
                variant="outline"
                onClick={() => onDownloadPdf(digest.id)}
                className="gap-2"
              >
                <FileText className="h-4 w-4" />
                {t('digest.download_pdf', 'Scarica Report PDF')}
              </Button>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
};

/* ── Empty state ───────────────────────────────────────────────────────────── */

const EmptyDigests = ({ t }) => (
  <Card className="border border-dashed">
    <CardContent className="py-12 text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-muted mx-auto mb-3">
        <FileText className="h-6 w-6 text-muted-foreground" />
      </div>
      <p className="text-sm font-medium">{t('digest.empty_title')}</p>
      <p className="text-xs text-muted-foreground mt-1">
        {t('digest.empty_desc')}
      </p>
    </CardContent>
  </Card>
);

/* ── Digest Generate Controls ──────────────────────────────────────────────── */

/**
 * Read the active cashflow filter from localStorage, set by
 * features/cashflow/CashflowModulePage.js whenever the user picks a
 * period in the dashboard. Returns null if no usable filter is stored
 * (e.g. user has never visited the cashflow page in this browser).
 *
 * Wave 13.7 — exposed so the digest generator can offer "use the
 * filter I'm currently viewing" as an explicit option, eliminating
 * the pre-13.7 mismatch where a merchant on YTD generated a digest
 * that was always 7 or 30 days regardless of what the dashboard showed.
 */
function readActiveCashflowPeriod() {
  try {
    const raw = localStorage.getItem('cashflow_active_period');
    if (!raw) return null;
    const ctx = JSON.parse(raw);
    // Require explicit start+end — bare label tokens (e.g. 7d/30d/90d
    // without computed dates) coincide with the existing weekly/monthly
    // options and would be confusing as a separate menu choice.
    if (ctx?.start && ctx?.end) {
      return { label: ctx.label || 'custom', start: ctx.start, end: ctx.end };
    }
    return null;
  } catch {
    return null;
  }
}

const DigestGenerateControls = ({ generating, generateDisabled, aiEnabled, quotaExhausted, onGenerate, t }) => {
  const [periodType, setPeriodType] = useState('weekly');
  const [customStart, setCustomStart] = useState('');
  const [customEnd, setCustomEnd] = useState('');

  // Wave 13.7 — peek at the cashflow filter once on mount. If the user
  // is currently viewing a custom range (YTD, MTD, custom dates) we
  // surface a NEW option "active filter" in the dropdown. Computed
  // once + memoised because localStorage is sync but reading it on
  // every render is wasteful.
  const activeFilter = useMemo(() => readActiveCashflowPeriod(), []);

  const handleClick = () => {
    if (periodType === 'active_filter') {
      // Wave 13.7 — generate using the cashflow dashboard's current
      // filter dates. The button is only enabled when activeFilter
      // exists so this branch always has valid dates.
      if (!activeFilter) {
        toast.error(t('digest.no_active_filter', 'Nessun filtro Cashflow attivo'));
        return;
      }
      onGenerate('custom', activeFilter.start, activeFilter.end);
      return;
    }
    if (periodType === 'custom') {
      if (!customStart || !customEnd) {
        toast.error(t('digest.custom_dates_required', 'Seleziona data inizio e fine'));
        return;
      }
      const diff = Math.ceil((new Date(customEnd) - new Date(customStart)) / (1000 * 60 * 60 * 24));
      if (diff < 1) {
        toast.error(t('digest.date_order_error', 'La data di fine deve essere successiva alla data di inizio'));
        return;
      }
      if (diff > 366) {
        toast.error(t('digest.max_period_error', 'Il periodo massimo e\' di 366 giorni'));
        return;
      }
      onGenerate(periodType, customStart, customEnd);
    } else {
      onGenerate(periodType);
    }
  };

  const today = new Date().toISOString().split('T')[0];

  return (
    <div className="space-y-3">
      <div className="flex items-end gap-3 flex-wrap">
        <div className="space-y-1">
          <label className="text-xs font-medium text-muted-foreground">
            {t('digest.period_label', 'Periodo')}
          </label>
          <Select value={periodType} onValueChange={setPeriodType}>
            <SelectTrigger className="w-48 h-9 text-sm">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="weekly">{t('digest.period_week', 'Ultima settimana')}</SelectItem>
              <SelectItem value="monthly">{t('digest.period_month', 'Ultimo mese')}</SelectItem>
              {/* Wave 13.7 — only show when the user actually has an
                  active cashflow filter that's NOT already weekly/monthly. */}
              {activeFilter && (
                <SelectItem value="active_filter">
                  {t('digest.period_active_filter', 'Filtro Cashflow attivo')}
                  {' '}({activeFilter.start} → {activeFilter.end})
                </SelectItem>
              )}
              <SelectItem value="custom">{t('digest.period_custom', 'Personalizzato')}</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {periodType === 'custom' && (
          <>
            <div className="space-y-1">
              <label className="text-xs font-medium text-muted-foreground">
                {t('digest.from', 'Da')}
              </label>
              <Input
                type="date"
                value={customStart}
                max={customEnd || today}
                onChange={(e) => setCustomStart(e.target.value)}
                className="w-40 h-9 text-sm"
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs font-medium text-muted-foreground">
                {t('digest.to', 'A')}
              </label>
              <Input
                type="date"
                value={customEnd}
                min={customStart}
                max={today}
                onChange={(e) => setCustomEnd(e.target.value)}
                className="w-40 h-9 text-sm"
              />
            </div>
          </>
        )}

        <Button
          size="sm"
          onClick={handleClick}
          disabled={generating || generateDisabled}
          className="gap-2 h-9"
        >
          {generating ? (
            <RefreshCw className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <Sparkles className="h-3.5 w-3.5" />
          )}
          {!aiEnabled
            ? t('digest.ai_unavailable')
            : quotaExhausted('digest')
              ? t('digest.quota_exhausted')
              : t('digest.generate', 'Genera Report')}
        </Button>
      </div>
    </div>
  );
};


/* ── DigestTab ─────────────────────────────────────────────────────────────── */

export const DigestTab = ({ isAdmin = false, currency = 'EUR' }) => {
  const { t } = useTranslation('ai_analysis');
  const { aiEnabled, canUse, quotaExhausted } = useAiAccess();
  const generateDisabled = !canUse('digest');
  const [digests, setDigests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);

  const fetchDigests = useCallback(async () => {
    setLoading(true);
    try {
      const res = await digestsAPI.list(null, 20);
      const list = res.data || [];
      // Sort by created_at descending (most recent first)
      list.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
      setDigests(list);
    } catch {
      setDigests([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDigests();
  }, [fetchDigests]);

  const handleGenerate = async (periodType, startDate = null, endDate = null) => {
    setGenerating(true);
    try {
      let period, digestType;
      if (periodType === 'custom' && startDate && endDate) {
        const diff = Math.ceil((new Date(endDate) - new Date(startDate)) / (1000 * 60 * 60 * 24));
        period = diff;
        digestType = diff > 14 ? 'monthly' : 'weekly';
        await digestsAPI.generate(period, digestType, 'report', startDate, endDate);
      } else {
        period = periodType === 'weekly' ? 7 : 30;
        digestType = periodType;
        await digestsAPI.generate(period, digestType, 'report');
      }
      toast.success(t('digest.toast_success', { type: typeLabel(digestType, t).toLowerCase() }));
      await fetchDigests();
    } catch (err) {
      const raw = err?.response?.data?.detail;
      const message = typeof raw === 'object' ? raw?.message : raw;
      toast.error(message || t('digest.toast_error'));
    } finally {
      setGenerating(false);
    }
  };

  const handleDownloadPdf = async (digestId) => {
    try {
      const response = await digestsAPI.downloadPdf(digestId);
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `afianco_report.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch {
      toast.error(t('digest.pdf_error', 'Errore nel download del PDF'));
    }
  };

  // First digest = most recent, always expanded
  const [latestDigest, ...olderDigests] = digests;

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-12 w-64 rounded-lg" />
        <Skeleton className="h-64 w-full rounded-xl" />
        <Skeleton className="h-16 w-full rounded-xl" />
        <Skeleton className="h-16 w-full rounded-xl" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Generate controls (admin only) */}
      {isAdmin && (
        <DigestGenerateControls
          generating={generating}
          generateDisabled={generateDisabled}
          aiEnabled={aiEnabled}
          quotaExhausted={quotaExhausted}
          onGenerate={handleGenerate}
          t={t}
        />
      )}

      {/* No digests at all */}
      {digests.length === 0 && <EmptyDigests t={t} />}

      {/* Latest digest — always expanded with featured card */}
      {latestDigest && (
        <FeaturedDigestCard digest={latestDigest} currency={currency} t={t} onDownloadPdf={handleDownloadPdf} />
      )}

      {/* Older digests — collapsed accordion */}
      {olderDigests.length > 0 && (
        <div className="space-y-3">
          <h3 className="text-sm font-semibold text-muted-foreground flex items-center gap-2">
            <Clock className="h-3.5 w-3.5" />
            {t('digest.previous_title')}
          </h3>
          <Accordion type="single" collapsible className="space-y-2">
            {olderDigests.map((item) => (
              <AccordionItem
                key={item.id}
                value={item.id}
                className="border border-border rounded-lg overflow-hidden px-0"
              >
                <AccordionTrigger className="px-4 py-3 hover:no-underline hover:bg-muted/50">
                  <div className="flex items-center gap-2 sm:gap-3 min-w-0 flex-1 text-left">
                    <Badge
                      variant="outline"
                      className="text-[11px] flex-shrink-0"
                    >
                      {typeLabel(item.digest_type, t)}
                    </Badge>
                    <span className="text-xs text-muted-foreground truncate">
                      {formatDate(item.period_start)} →{' '}
                      {formatDate(item.period_end)}
                    </span>
                    {item.kpis_summary?.net_after_fixed != null && (
                      <Badge
                        variant="outline"
                        className={`text-[11px] gap-1 whitespace-nowrap flex-shrink-0 ml-auto ${
                          item.kpis_summary.net_after_fixed >= 0
                            ? 'border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-800 dark:bg-emerald-950 dark:text-emerald-400'
                            : 'border-red-200 bg-red-50 text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-400'
                        }`}
                      >
                        {formatCurrency(item.kpis_summary.net_after_fixed, currency)}
                      </Badge>
                    )}
                  </div>
                </AccordionTrigger>
                <AccordionContent className="px-4 pb-4">
                  <DigestMarkdown content={item.content} />
                  {item.model_version && (
                    <p className="mt-3 text-[11px] text-muted-foreground/60 font-mono">
                      {item.model_version}
                    </p>
                  )}
                </AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>
        </div>
      )}
    </div>
  );
};

export default DigestTab;
