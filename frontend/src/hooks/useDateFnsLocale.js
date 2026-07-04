/**
 * useDateFnsLocale — maps the active i18next language to a date-fns Locale.
 *
 * Date-fns `Locale` objects are needed by:
 *   - `react-day-picker` (Calendar wrapper) for month/weekday names
 *   - any future formatter that wants more control than `Intl.DateTimeFormat`
 *
 * The four locale modules are imported statically. Together they add
 * ~30 KB gzipped to the bundle — small enough to ship eagerly. Lazy
 * loading (via `import()`) would require an async boundary in every
 * picker, which is wildly out of proportion for the savings.
 *
 * Falls back to `it` when:
 *   - i18next hasn't initialised yet (rare)
 *   - the active language isn't one of {it, en, de, fr}
 *   - the active language has a region tag we don't ship (e.g. `pt-BR`)
 *
 * Usage:
 *   const dateFnsLocale = useDateFnsLocale();
 *   <Calendar locale={dateFnsLocale} ... />
 */

import { useTranslation } from 'react-i18next';
import { it, enUS, de, fr } from 'date-fns/locale';


// Map short codes to date-fns Locale objects. Keep the keys aligned with
// `APP_SUPPORTED_LOCALES` from `useStorefrontLocale.js` so this never
// returns undefined when i18n is in a normal state.
const LOCALES = { it, en: enUS, de, fr };


export function useDateFnsLocale() {
  const { i18n } = useTranslation();
  // i18n.language can be `it`, `it-IT`, `en`, `en-US`, etc. We strip
  // the region tag and lowercase the language tag — same normalisation
  // the storefront resolver uses.
  const code = String(i18n.language || 'it').toLowerCase().split('-')[0];
  return LOCALES[code] || LOCALES.it;
}
