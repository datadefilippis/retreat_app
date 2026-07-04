/**
 * Supported currencies for the frontend.
 *
 * Must stay in sync with backend SUPPORTED_CURRENCIES in
 * services/currency_service.py and core/checkout_minimums.py.
 * When a new currency ships there, add it here too.
 */

export const SUPPORTED_CURRENCIES = ['EUR', 'CHF'];

export const DEFAULT_CURRENCY = 'EUR';

/**
 * Options for `<select>` / dropdown inputs. The `label` is what the
 * merchant reads in the setup UI; the `value` is the ISO 4217 code we
 * send to the backend.
 */
export const CURRENCY_OPTIONS = [
  { value: 'EUR', label: 'Euro (€)', region: 'Italia / EU' },
  { value: 'CHF', label: 'Franco svizzero (CHF)', region: 'Svizzera' },
];

/**
 * Country → default currency suggestion. Used at signup to pre-select
 * a sensible currency based on the merchant's country. Not a hard
 * binding: a Swiss merchant can still pick EUR if they want.
 */
export const COUNTRY_DEFAULT_CURRENCY = {
  IT: 'EUR',
  CH: 'CHF',
  DE: 'EUR',
  FR: 'EUR',
  AT: 'EUR',
};
