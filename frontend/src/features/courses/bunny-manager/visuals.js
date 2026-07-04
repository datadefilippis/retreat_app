/**
 * Bunny status visuals — single source of truth for `BunnyStatus → UI`.
 *
 * Every Bunny-status-aware surface (status badge, library row, action
 * button color, error banner) imports from here. Adding a new status
 * value (e.g. `RATE_LIMITED`) requires updating this one file +
 * matching the backend enum.
 *
 * Three viewer-tunable size profiles:
 *   - `pill`    — small inline badge ("✓ Connesso")
 *   - `banner`  — full-width error/warning banner
 *   - `widget`  — compact label for sidebar widgets ("✓ Connesso", short)
 *
 * The badge styling uses Tailwind — no inline styles, so the build
 * pipeline can purge unused classes.
 */


/**
 * Map a BunnyStatus value to badge visual props.
 *
 * @param {string|null|undefined} status — backend `last_verification_status`
 * @param {Function} t — react-i18next `t` (namespace `products`); pass null/undefined to fall back to Italian defaults
 * @returns {{label: string, icon: string, badgeCls: string, bannerCls: string, kind: 'success'|'error'|'transient'|'unknown'}}
 */
export function statusVisuals(status, t = null) {
  const tx = (key, fallback) => (t ? t(`dashboards.course.bunnyManager.status.${key}`) : fallback);
  switch (status) {
    case 'ok':
      return {
        label: tx('ok', 'Connesso'),
        icon: '✓',
        badgeCls: 'bg-emerald-100 text-emerald-900',
        bannerCls: '',
        kind: 'success',
      };
    case 'unauthorized':
      return {
        label: tx('unauthorized', 'Credenziali errate'),
        icon: '⚠',
        badgeCls: 'bg-red-100 text-red-900',
        bannerCls: 'border-red-200 bg-red-50 text-red-900',
        kind: 'error',
      };
    case 'library_not_found':
      return {
        label: tx('library_not_found', 'Libreria non trovata'),
        icon: '⚠',
        badgeCls: 'bg-red-100 text-red-900',
        bannerCls: 'border-red-200 bg-red-50 text-red-900',
        kind: 'error',
      };
    case 'network_error':
      return {
        label: tx('network_error', 'Bunny non raggiungibile'),
        icon: '⏱',
        badgeCls: 'bg-amber-100 text-amber-900',
        bannerCls: 'border-amber-200 bg-amber-50 text-amber-900',
        kind: 'transient',
      };
    case 'unknown':
      return {
        label: tx('unknown', 'Errore'),
        icon: '⚠',
        badgeCls: 'bg-amber-100 text-amber-900',
        bannerCls: 'border-amber-200 bg-amber-50 text-amber-900',
        kind: 'error',
      };
    default:
      // Includes 'not_configured' and any null/undefined value.
      return {
        label: tx('default', 'Mai testato'),
        icon: '○',
        badgeCls: 'bg-gray-100 text-gray-700',
        bannerCls: '',
        kind: 'unknown',
      };
  }
}


/**
 * Format an ISO timestamp as a human-readable relative time.
 * Lightweight inline replacement for date-fns.
 *
 * @param {string} iso — ISO timestamp
 * @param {Function} t — react-i18next `t` (namespace `products`); pass null/undefined to fall back to Italian defaults
 *
 * Examples: "ora", "12 min fa", "3 h fa", "2 giorni fa"
 */
export function formatTimeAgo(iso, t = null) {
  if (!iso) return null;
  const then = new Date(iso).getTime();
  if (!Number.isFinite(then)) return null;
  const diffSec = Math.max(0, Math.floor((Date.now() - then) / 1000));
  if (diffSec < 60) return t ? t('dashboards.course.bunnyManager.timeAgo.now') : 'ora';
  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) {
    return t
      ? t('dashboards.course.bunnyManager.timeAgo.minutes', { count: diffMin })
      : `${diffMin} min fa`;
  }
  const diffH = Math.floor(diffMin / 60);
  if (diffH < 24) {
    return t
      ? t('dashboards.course.bunnyManager.timeAgo.hours', { count: diffH })
      : `${diffH} h fa`;
  }
  const diffD = Math.floor(diffH / 24);
  if (t) return t('dashboards.course.bunnyManager.timeAgo.days', { count: diffD });
  return `${diffD} ${diffD === 1 ? 'giorno' : 'giorni'} fa`;
}


/**
 * Mask a credential string for display. "••••••••XYZ"-style.
 * Used uniformly across the Bunny UI surfaces — never echo full keys.
 */
export function maskKey(k) {
  if (!k) return '';
  const s = String(k);
  if (s.length <= 6) return '•'.repeat(s.length);
  return `${'•'.repeat(Math.max(0, s.length - 4))}${s.slice(-4)}`;
}
