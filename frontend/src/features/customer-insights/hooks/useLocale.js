/**
 * useLocale — derive a BCP-47 locale tag from the active i18n language.
 *
 * The whole customer-insights feature uses ``Intl.NumberFormat`` and
 * ``Intl.DateTimeFormat`` for thousands separators / decimal separators
 * / date order. Hardcoding ``"it-IT"`` (the legacy state) forces Italian
 * formatting on every locale; this hook returns the right tag per
 * language so a German user sees ``"1'234,50"`` (de-CH conventions)
 * and an English user sees ``"1,234.50"``.
 *
 * Switzerland-aware mapping: ``"de"`` → ``"de-CH"`` and ``"fr"`` →
 * ``"fr-CH"`` because the dominant audience is Ticino + Romandie. If
 * a non-Swiss German/French market becomes a real concern, the mapping
 * can be widened from a single constant to per-org config.
 */
import { useTranslation } from 'react-i18next';

const I18N_TO_BCP47 = {
  it: 'it-IT',
  en: 'en-US',
  de: 'de-CH',
  fr: 'fr-CH',
};

export function useLocale() {
  const { i18n } = useTranslation();
  const lang = (i18n.language || 'it').toLowerCase().slice(0, 2);
  return I18N_TO_BCP47[lang] || lang;
}

export default useLocale;
