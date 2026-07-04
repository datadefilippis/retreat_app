/**
 * ModuleStatusBanner — v2.3 synthetic health status strip.
 *
 * Renders a colored banner that communicates the module health level in one
 * glance.  Consumes the `status` block returned by the overview endpoint:
 *   { level, color, label, primary_driver, message, data_warnings }
 *
 * Props:
 *   status  {object|null}  — status block from overview.status, or null
 *   loading {bool}         — show skeleton while data is being fetched
 *
 * Color levels:
 *   healthy           → green    (all clear)
 *   monitor           → yellow   (attention, still profitable)
 *   warning           → orange   (margin under pressure / negative net)
 *   critical          → red      (immediate action needed)
 *   insufficient_data → gray     (not enough data to evaluate)
 */
import React from 'react';
import {
  CheckCircle2,
  Eye,
  AlertTriangle,
  AlertOctagon,
  Info,
} from 'lucide-react';


// ── Level → visual config ─────────────────────────────────────────────────────

const LEVEL_CONFIG = {
  healthy: {
    bg:         'bg-green-50 dark:bg-green-950/30',
    border:     'border-green-200 dark:border-green-800',
    iconColor:  'text-green-600 dark:text-green-400',
    labelColor: 'text-green-800 dark:text-green-200',
    textColor:  'text-green-700 dark:text-green-300',
    warnColor:  'text-green-600 dark:text-green-400',
    Icon:       CheckCircle2,
  },
  monitor: {
    bg:         'bg-yellow-50 dark:bg-yellow-950/30',
    border:     'border-yellow-200 dark:border-yellow-800',
    iconColor:  'text-yellow-600 dark:text-yellow-400',
    labelColor: 'text-yellow-800 dark:text-yellow-200',
    textColor:  'text-yellow-700 dark:text-yellow-300',
    warnColor:  'text-yellow-600 dark:text-yellow-400',
    Icon:       Eye,
  },
  warning: {
    bg:         'bg-orange-50 dark:bg-orange-950/30',
    border:     'border-orange-200 dark:border-orange-800',
    iconColor:  'text-orange-600 dark:text-orange-400',
    labelColor: 'text-orange-800 dark:text-orange-200',
    textColor:  'text-orange-700 dark:text-orange-300',
    warnColor:  'text-orange-600 dark:text-orange-400',
    Icon:       AlertTriangle,
  },
  critical: {
    bg:         'bg-red-50 dark:bg-red-950/30',
    border:     'border-red-200 dark:border-red-800',
    iconColor:  'text-red-600 dark:text-red-400',
    labelColor: 'text-red-800 dark:text-red-200',
    textColor:  'text-red-700 dark:text-red-300',
    warnColor:  'text-red-600 dark:text-red-400',
    Icon:       AlertOctagon,
  },
  insufficient_data: {
    bg:         'bg-gray-50 dark:bg-gray-900/40',
    border:     'border-gray-200 dark:border-gray-700',
    iconColor:  'text-gray-500 dark:text-gray-400',
    labelColor: 'text-gray-700 dark:text-gray-300',
    textColor:  'text-gray-600 dark:text-gray-400',
    warnColor:  'text-gray-500 dark:text-gray-500',
    Icon:       Info,
  },
};

// Fallback for any unexpected level value
const DEFAULT_CONFIG = LEVEL_CONFIG.insufficient_data;


// ── Loading skeleton ──────────────────────────────────────────────────────────

const BannerSkeleton = () => (
  <div className="w-full rounded-lg border border-gray-100 bg-gray-50 px-4 py-3 dark:border-gray-800 dark:bg-gray-900/30 animate-pulse">
    <div className="flex items-center gap-3">
      <div className="h-5 w-5 rounded-full bg-gray-200 dark:bg-gray-700 flex-shrink-0" />
      <div className="flex-1 space-y-1.5">
        <div className="h-3.5 w-28 rounded bg-gray-200 dark:bg-gray-700" />
        <div className="h-3 w-64 rounded bg-gray-100 dark:bg-gray-800" />
      </div>
    </div>
  </div>
);


// ── Main component ────────────────────────────────────────────────────────────

export const ModuleStatusBanner = ({ status, loading }) => {
  // Show skeleton while first load is in progress
  if (loading && !status) {
    return <BannerSkeleton />;
  }

  // Nothing to show — hide entirely (no status returned by backend)
  if (!status) {
    return null;
  }

  const cfg = LEVEL_CONFIG[status.level] ?? DEFAULT_CONFIG;
  const { Icon } = cfg;
  const warnings = status.data_warnings ?? [];

  return (
    <div
      className={`w-full rounded-lg border px-4 py-3 ${cfg.bg} ${cfg.border}`}
      data-testid="module-status-banner"
      data-level={status.level}
    >
      {/* ── Main row: icon + label + message ─────────────────────────────── */}
      <div className="flex items-start gap-3">
        <Icon
          className={`mt-0.5 h-5 w-5 flex-shrink-0 ${cfg.iconColor}`}
          aria-hidden="true"
        />
        <div className="min-w-0 flex-1">
          <span className={`font-semibold text-sm ${cfg.labelColor}`}>
            {status.label}
          </span>
          {status.message && (
            <span className={`ml-2 text-sm ${cfg.textColor}`}>
              — {status.message}
            </span>
          )}
        </div>
      </div>

      {/* ── Data warnings (informational, smaller) ────────────────────────── */}
      {warnings.length > 0 && (
        <ul className="mt-2 ml-8 space-y-0.5">
          {warnings.map((w, i) => (
            <li
              key={i}
              className={`text-xs ${cfg.warnColor} flex items-start gap-1.5`}
            >
              <span className="mt-0.5 flex-shrink-0">⚠</span>
              <span>{w}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

export default ModuleStatusBanner;
