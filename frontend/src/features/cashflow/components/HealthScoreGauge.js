/**
 * HealthScoreGauge — Semicircular gauge showing composite financial health (0-100).
 *
 * Zones: 0-40 red, 41-60 orange, 61-80 yellow, 81-100 green.
 * Renders a pure SVG semicircle gauge with animated needle.
 * Breakdown is always visible below the gauge.
 * Default explanation is rule-based (zero API cost). AI available on-demand.
 *
 * Front: gauge + score + breakdown + explanation
 * Back:  full explainer of how the score works and what each dimension means
 */
import React, { useState, useCallback } from 'react';
import { Card, CardContent } from '../../../components/ui/card';
import { Skeleton } from '../../../components/ui/skeleton';
import { Button } from '../../../components/ui/button';
import { Sparkles, Loader2, Info, RotateCcw } from 'lucide-react';
import { PinToDashboardButton } from '../../dashboard/PinToDashboardButton';
import api from '../../../api/client';
import { useAiAccess } from '../../../hooks/useAiAccess';
import { useTranslation } from 'react-i18next';

/* ── SVG geometry ─────────────────────────────────────────────────────────── */
const W = 220;
const STROKE = 20;
const R = (W - STROKE) / 2;
const CX = W / 2;
const CY = R + STROKE / 2 + 4;
const ARC_LEN = Math.PI * R;
const SVG_H = CY + 40;

/* ── Zone colors ──────────────────────────────────────────────────────────── */
function getScoreColor(score) {
  if (score <= 40) return '#EF4444';
  if (score <= 60) return '#F97316';
  if (score <= 80) return '#EAB308';
  return '#22C55E';
}

function GaugeSVG({ score, color }) {
  const pct = Math.max(0, Math.min(100, score)) / 100;
  const offset = ARC_LEN * (1 - pct);
  const angle = (180 - pct * 180) * Math.PI / 180;
  const needleLen = R - 14;
  const nx = CX + needleLen * Math.cos(angle);
  const ny = CY - needleLen * Math.sin(angle);
  const arcLeft = STROKE / 2;
  const arcRight = W - STROKE / 2;

  return (
    <svg width="100%" viewBox={`0 0 ${W} ${SVG_H}`} className="mx-auto max-w-[220px]">
      <path d={`M ${arcLeft} ${CY} A ${R} ${R} 0 0 1 ${arcRight} ${CY}`} fill="none" stroke="#E2E8F0" strokeWidth={STROKE} strokeLinecap="round" />
      <path d={`M ${arcLeft} ${CY} A ${R} ${R} 0 0 1 ${arcRight} ${CY}`} fill="none" stroke={color} strokeWidth={STROKE} strokeLinecap="round" strokeDasharray={ARC_LEN} strokeDashoffset={offset} style={{ transition: 'stroke-dashoffset 0.8s ease-out, stroke 0.3s ease' }} />
      <line x1={CX} y1={CY} x2={nx} y2={ny} stroke="#1E293B" strokeWidth={2.5} strokeLinecap="round" style={{ transition: 'x2 0.8s ease-out, y2 0.8s ease-out' }} />
      <circle cx={CX} cy={CY} r={4} fill="#1E293B" />
      <text x={CX} y={CY + 28} textAnchor="middle" dominantBaseline="middle" className="font-bold" fontSize={30} fill={color}>{score}</text>
    </svg>
  );
}


function BreakdownList({ breakdown, t }) {
  if (!breakdown?.length) return null;
  return (
    <div className="space-y-1.5 pt-2 border-t border-border">
      {breakdown.map((item) => {
        const isInactive = item.disabled === true || item.status === 'disabled' || item.status === 'not_computable' || item.points == null;
        const pct = !isInactive && item.max > 0 ? (item.points / item.max) * 100 : 0;
        const barColor = pct >= 70 ? '#22C55E' : pct >= 40 ? '#EAB308' : '#EF4444';
        const dimLabel = t(`health.dimensions.${item.dimension}`, item.dimension);
        return (
          <div key={item.dimension || item.key} className={`flex items-center text-xs gap-1.5 ${isInactive ? 'opacity-35' : ''}`}>
            <span className={`truncate min-w-0 flex-1 ${isInactive ? 'line-through text-muted-foreground/50' : 'text-muted-foreground'}`}>
              {dimLabel}
            </span>
            <div className="w-14 h-1.5 bg-muted rounded-full overflow-hidden flex-shrink-0">
              {!isInactive && (
                <div className="h-full rounded-full transition-all duration-500" style={{ width: `${pct}%`, backgroundColor: barColor }} />
              )}
            </div>
            <span className="text-muted-foreground text-right font-mono text-[10px] flex-shrink-0 w-9">
              {isInactive ? `— / ${item.max}` : `${item.points}/${item.max}`}
            </span>
          </div>
        );
      })}
    </div>
  );
}


/* ── Health Score Back Side — full explainer ─────────────────────────────── */
function HealthScoreBack({ t, onFlipBack, onConfigChanged }) {
  const [config, setConfig] = React.useState(null);
  const [saving, setSaving] = React.useState(false);

  const DIMS = [
    { key: 'net_margin', i18n: 'info_dim_net_margin' },
    { key: 'revenue_dynamics', i18n: 'info_dim_dynamics' },
    { key: 'structural_strength', i18n: 'info_dim_structural' },
    { key: 'cash_cycle', i18n: 'info_dim_cash_cycle' },
    { key: 'operational_risk', i18n: 'info_dim_risk' },
  ];

  React.useEffect(() => {
    api.get('/modules/cashflow_monitor/health-score-config')
      .then(res => setConfig(res.data.health_score_dimensions))
      .catch(() => {
        // Default all enabled
        const defaults = {};
        DIMS.forEach(d => { defaults[d.key] = true; });
        setConfig(defaults);
      });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleToggle = async (dimKey) => {
    if (!config) return;
    const updated = { ...config, [dimKey]: !config[dimKey] };
    // Prevent disabling all — at least 2 must remain active
    const activeCount = Object.values(updated).filter(Boolean).length;
    if (activeCount < 2) return;

    setConfig(updated);
    setSaving(true);
    try {
      await api.patch('/modules/cashflow_monitor/health-score-config', {
        health_score_dimensions: updated,
      });
      if (onConfigChanged) onConfigChanged();
    } catch { /* non-critical */ }
    finally { setSaving(false); }
  };

  return (
    <Card className="border border-primary/20 bg-primary/[0.02] overflow-hidden">
      <CardContent className="pt-4 pb-4 px-4">
        <h3 className="font-heading text-sm font-semibold text-primary/80 mb-2">
          {t('health.config_title', 'Configura Salute Finanziaria')}
        </h3>
        <p className="text-xs text-muted-foreground leading-relaxed mb-3">
          {t('health.config_desc', 'Abilita o disabilita le dimensioni da includere nel calcolo. Il peso viene ridistribuito automaticamente.')}
        </p>

        <div className="space-y-1.5 border-t border-border pt-2">
          {DIMS.map(({ key, i18n }) => (
            <label key={key} className="flex items-center gap-2 cursor-pointer group">
              <input
                type="checkbox"
                checked={config?.[key] ?? true}
                onChange={() => handleToggle(key)}
                disabled={saving || !config}
                className="rounded border-border accent-primary h-3.5 w-3.5"
              />
              <span className={`text-[10px] leading-relaxed transition-opacity ${
                config?.[key] === false ? 'text-muted-foreground/50 line-through' : 'text-muted-foreground'
              }`}>
                {t(`health.${i18n}`)}
              </span>
            </label>
          ))}
        </div>

        {saving && (
          <p className="text-[10px] text-primary/60 mt-2 flex items-center gap-1">
            <Loader2 className="h-3 w-3 animate-spin" />
            {t('health.config_saving', 'Salvataggio...')}
          </p>
        )}

        <button
          onClick={onFlipBack}
          className="mt-3 flex items-center gap-1 text-[11px] font-medium text-primary hover:text-primary/80 transition-colors"
        >
          <RotateCcw className="h-3 w-3" />
          {t('health.info_back')}
        </button>
      </CardContent>
    </Card>
  );
}


/* ── Main component ────────────────────────────────────────────────────────── */

export const HealthScoreGauge = ({
  healthScore,
  loading,
  widgetKey,
  isPinned,
  onTogglePin,
  period,
  onRefresh,
}) => {
  const { t } = useTranslation('cashflow_monitor');
  const { canUse } = useAiAccess();
  const [aiExplanation, setAiExplanation] = useState(null);
  const [aiSource, setAiSource] = useState(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [showBack, setShowBack] = useState(false);
  const showAiButton = canUse('health_explanation');

  const requestAiExplanation = useCallback(async () => {
    setAiLoading(true);
    try {
      // Pass period + custom date range so AI analyzes the correct timeframe
      const searchParams = new URLSearchParams();
      if (period?.label) searchParams.append('period', period.label);
      if (period?.start) searchParams.append('start_date', period.start);
      if (period?.end) searchParams.append('end_date', period.end);
      const qs = searchParams.toString();
      const res = await api.post(`/modules/cashflow_monitor/health-explanation-ai${qs ? '?' + qs : ''}`);
      setAiExplanation(res.data.explanation);
      setAiSource(res.data.source || null);
    } catch (err) {
      const detail = err?.response?.data?.detail;
      if (detail === 'No data') {
        setAiExplanation(t('health.ai_no_data', 'Dati insufficienti per generare l\'analisi AI nel periodo selezionato.'));
        setAiSource('info');
      } else {
        setAiExplanation(t('health.ai_error', 'Impossibile generare l\'analisi AI. Riprova più tardi.'));
        setAiSource('error');
      }
    } finally {
      setAiLoading(false);
    }
  }, [period]);

  if (loading) {
    return <Skeleton className="h-48 w-full rounded-lg" />;
  }

  if (!healthScore || healthScore.score == null) {
    return null;
  }

  const { score, breakdown, label, color, explanation } = healthScore;
  const displayColor = color || getScoreColor(score);
  const displayLabel = t(`health.labels.${label}`, label);
  const displayExplanation = aiExplanation || explanation;

  // ── BACK SIDE: full explainer ──────────────────────────────────────────
  if (showBack) {
    return <HealthScoreBack t={t} onFlipBack={() => setShowBack(false)} onConfigChanged={onRefresh} />;
  }

  // ── FRONT SIDE: gauge + data ───────────────────────────────────────────
  return (
    <Card className="border border-border overflow-hidden">
      <CardContent className="pt-4 pb-4 px-4">
        <div className="flex items-start justify-between mb-2">
          <div>
            <h3 className="font-heading text-sm font-semibold text-muted-foreground flex items-center gap-1">
              {t('health.title')}
              <button
                onClick={() => setShowBack(true)}
                className="text-muted-foreground/40 hover:text-primary transition-colors"
                aria-label={t('health.info_button')}
              >
                <Info className="h-3 w-3" />
              </button>
            </h3>
            <p className="text-lg font-bold mt-0.5" style={{ color: displayColor }}>
              {displayLabel}
            </p>
          </div>
          {widgetKey && onTogglePin && (
            <PinToDashboardButton widgetKey={widgetKey} isPinned={isPinned} onToggle={onTogglePin} />
          )}
        </div>

        <GaugeSVG score={score} color={displayColor} />

        {displayExplanation && (
          <p className="text-[11px] text-muted-foreground leading-relaxed mt-1 mb-1">
            {displayExplanation}
          </p>
        )}

        {aiSource === 'ai' && (
          <span className="inline-block text-[9px] text-primary/60 mb-1">
            {t('health.ai_source')}
          </span>
        )}

        {!aiExplanation && showAiButton && (
          <Button
            variant="ghost"
            size="sm"
            className="h-6 text-[10px] text-primary/70 hover:text-primary px-2 gap-1 mb-1"
            onClick={requestAiExplanation}
            disabled={aiLoading}
          >
            {aiLoading
              ? <Loader2 className="h-3 w-3 animate-spin" />
              : <Sparkles className="h-3 w-3" />
            }
            {aiLoading ? t('health.ai_loading') : t('health.ai_button')}
          </Button>
        )}

        <BreakdownList breakdown={breakdown} t={t} />
      </CardContent>
    </Card>
  );
};

export default HealthScoreGauge;
