/**
 * Kit grafico condiviso (CF1, INSIGHTS_ACTION_PLAN).
 *
 * Le pagine feature importano SOLO da qui — mai recharts direttamente
 * (guardia: backend/tests/test_charts_kit_guard.py). Quattro forme,
 * scelte per rispondere alle tre domande dell'operatore:
 *   StatCard   → "come sta andando?"        (numero + delta)
 *   TrendArea  → "che direzione ha preso?"  (reale vs atteso nel tempo)
 *   MiniBars   → "gli ultimi giorni?"       (sparkline compatta)
 *   DonutSplit → "com'è composto?"          (max 5 fette + "altro")
 *
 * Regola realtà dei dati: nessun dato → empty state onesto, mai
 * skeleton infiniti né assi vuoti.
 */
import React, { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import {
  ResponsiveContainer,
  AreaChart, Area,
  BarChart, Bar,
  PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend,
} from 'recharts';
import { CHART_COLORS, SERIES_COLORS, OTHER_COLOR } from './palette';

export { CHART_COLORS, SERIES_COLORS, OTHER_COLOR };

// ── Empty state onesto ───────────────────────────────────────────────────────

function ChartEmpty({ text, height = 180 }) {
  const { t } = useTranslation('common');
  return (
    <div
      className="flex items-center justify-center rounded-xl border border-dashed border-border"
      style={{ height }}
      data-testid="chart-empty"
    >
      <p className="text-sm text-muted-foreground px-6 text-center">
        {text || t('charts.empty', { defaultValue: 'Ancora nessun dato: arriverà col primo ordine.' })}
      </p>
    </div>
  );
}

const hasData = (data) => Array.isArray(data) && data.some((d) => (d?.value || 0) !== 0);

// ── StatCard — l'UNICO formato KPI dell'app ──────────────────────────────────
//
// value: stringa GIÀ formattata dal chiamante (valuta/percentuale — il kit
// non indovina i formati). delta: variazione % vs periodo precedente
// (null/undefined = niente freccia). invertDelta: true dove crescere è male
// (es. "in ritardo").

export function StatCard({ label, value, delta, deltaLabel, sublabel, icon: Icon, invertDelta = false, accent = false, loading = false }) {
  const { t } = useTranslation('common');
  if (loading) {
    return (
      <div className="rounded-xl border border-border bg-card p-4">
        <div className="h-3 w-20 rounded bg-secondary animate-pulse mb-3" />
        <div className="h-7 w-24 rounded bg-secondary animate-pulse" />
      </div>
    );
  }
  const deltaNum = typeof delta === 'number' && Number.isFinite(delta) ? delta : null;
  const good = deltaNum != null && (invertDelta ? deltaNum < 0 : deltaNum > 0);
  const flat = deltaNum === 0;
  return (
    <div className={`rounded-xl border bg-card p-4 ${accent ? 'border-[#C97B5D]/60' : 'border-border'}`}>
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs text-muted-foreground truncate">{label}</span>
        {Icon && <Icon className="h-4 w-4 shrink-0 text-muted-foreground" aria-hidden />}
      </div>
      <p className={`font-heading text-2xl font-bold mt-1 ${accent ? 'text-[#C97B5D]' : 'text-foreground'}`}>
        {value ?? '—'}
      </p>
      {(deltaNum != null || sublabel) && (
        <p className="text-xs mt-1 flex items-center gap-1.5 flex-wrap">
          {deltaNum != null && (
            <span className={flat ? 'text-muted-foreground' : good ? 'text-[#376254] font-semibold' : 'text-[#C97B5D] font-semibold'}>
              {flat ? '=' : deltaNum > 0 ? '▲' : '▼'} {Math.abs(deltaNum).toFixed(deltaNum % 1 ? 1 : 0)}%
              <span className="font-normal text-muted-foreground"> {deltaLabel || t('charts.vsPrev', { defaultValue: 'vs periodo prec.' })}</span>
            </span>
          )}
          {sublabel && <span className="text-muted-foreground">{sublabel}</span>}
        </p>
      )}
    </div>
  );
}

// ── TrendArea — reale (pieno) vs atteso (tratteggiato) nel tempo ─────────────
//
// data: [{label, value, expected?}] — expected opzionale per riga.
// valueFormatter: (n) => string per tooltip/asse (es. valuta).

export function TrendArea({ data, height = 220, valueFormatter, expectedLabel, valueLabel, empty }) {
  const { t } = useTranslation('common');
  const fmt = valueFormatter || ((n) => String(n));
  const withExpected = useMemo(() => (data || []).some((d) => d.expected != null), [data]);
  if (!hasData(data) && !(data || []).some((d) => (d?.expected || 0) !== 0)) {
    return <ChartEmpty text={empty} height={height} />;
  }
  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 8, right: 8, left: 8, bottom: 0 }}>
        <CartesianGrid stroke={CHART_COLORS.grid} strokeDasharray="3 3" vertical={false} />
        <XAxis dataKey="label" tick={{ fontSize: 11, fill: CHART_COLORS.expected }} tickLine={false} axisLine={false} />
        <YAxis tick={{ fontSize: 11, fill: CHART_COLORS.expected }} tickLine={false} axisLine={false} width={54} tickFormatter={fmt} />
        <Tooltip formatter={(v, name) => [fmt(v), name]} contentStyle={{ fontSize: 12, borderRadius: 10 }} />
        {withExpected && (
          <Area
            type="monotone" dataKey="expected"
            name={expectedLabel || t('charts.expected', { defaultValue: 'Atteso' })}
            stroke={CHART_COLORS.expected} strokeDasharray="6 4" strokeWidth={2}
            fill="none" dot={false}
          />
        )}
        <Area
          type="monotone" dataKey="value"
          name={valueLabel || t('charts.actual', { defaultValue: 'Reale' })}
          stroke={CHART_COLORS.primary} strokeWidth={2.5}
          fill={CHART_COLORS.primary} fillOpacity={0.12} dot={false}
        />
        {withExpected && <Legend wrapperStyle={{ fontSize: 12 }} />}
      </AreaChart>
    </ResponsiveContainer>
  );
}

// ── MiniBars — sparkline compatta (es. vendite ultimi 30 giorni) ─────────────

export function MiniBars({ data, height = 64, valueFormatter, empty, accent = false }) {
  const fmt = valueFormatter || ((n) => String(n));
  if (!hasData(data)) return <ChartEmpty text={empty} height={height} />;
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 2, right: 0, left: 0, bottom: 0 }}>
        <Tooltip
          formatter={(v) => [fmt(v), '']}
          labelStyle={{ fontSize: 11 }}
          contentStyle={{ fontSize: 12, borderRadius: 10, padding: '4px 8px' }}
          cursor={{ fill: CHART_COLORS.grid, opacity: 0.5 }}
        />
        <Bar dataKey="value" fill={accent ? CHART_COLORS.accent : CHART_COLORS.primary} radius={[2, 2, 0, 0]} isAnimationActive={false} />
      </BarChart>
    </ResponsiveContainer>
  );
}

// ── DonutSplit — composizione, max 5 fette poi "altro" ───────────────────────
//
// data: [{key, label, value}]. colors: mappa opzionale key→colore per
// semantiche fisse (es. segmenti clienti); altrimenti SERIES_COLORS in ordine.

export function DonutSplit({ data, colors, maxSlices = 5, height = 200, valueFormatter, otherLabel, empty }) {
  const { t } = useTranslation('common');
  const fmt = valueFormatter || ((n) => String(n));
  const slices = useMemo(() => {
    const sorted = [...(data || [])].filter((d) => (d?.value || 0) > 0).sort((a, b) => b.value - a.value);
    if (sorted.length <= maxSlices) return sorted;
    const head = sorted.slice(0, maxSlices);
    const rest = sorted.slice(maxSlices).reduce((s, d) => s + d.value, 0);
    return [...head, {
      key: '__other', value: rest,
      label: otherLabel || t('charts.other', { defaultValue: 'Altro' }),
    }];
  }, [data, maxSlices, otherLabel, t]);
  if (!hasData(slices)) return <ChartEmpty text={empty} height={height} />;
  return (
    <ResponsiveContainer width="100%" height={height}>
      <PieChart>
        <Pie data={slices} dataKey="value" nameKey="label" cx="50%" cy="50%" innerRadius="55%" outerRadius="85%" paddingAngle={2}>
          {slices.map((s, i) => (
            <Cell
              key={s.key || i}
              fill={s.key === '__other' ? OTHER_COLOR : (colors && colors[s.key]) || SERIES_COLORS[i % SERIES_COLORS.length]}
            />
          ))}
        </Pie>
        <Tooltip formatter={(v, name) => [fmt(v), name]} contentStyle={{ fontSize: 12, borderRadius: 10 }} />
        <Legend wrapperStyle={{ fontSize: 12 }} iconType="circle" />
      </PieChart>
    </ResponsiveContainer>
  );
}
