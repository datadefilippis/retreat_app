/**
 * DirectoryListingHint — GT7: accanto al selettore "modalità" dei
 * RITIRI spiega quando l'evento non comparirà nel calendario
 * pubblico (/ritiri), che dal GT1b elenca SOLO ritiri prenotabili
 * online all'istante (transaction_mode=direct + Stripe pronto).
 *
 * Due casi, mai insieme:
 *   - mode 'request'          → il ritiro resta sullo store, ma è
 *                               fuori dalla directory: lo diciamo
 *                               SUBITO, non a pubblicazione avvenuta.
 *   - mode 'direct' + !ready  → una riga complementare a
 *                               StripeRequiredAlert (che ha già la
 *                               CTA di configurazione): esplicita la
 *                               conseguenza-directory.
 *
 * Solo per prodotti evento: gli altri tipi non vivono nel calendario.
 */

import React from 'react';
import { Info } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useStripeReadiness } from '../hooks/useStripeReadiness';

export default function DirectoryListingHint({ mode, className = '' }) {
  const { t } = useTranslation('common');
  const { loading, ready } = useStripeReadiness();

  let message = null;
  if (mode === 'request') {
    message = t('directoryHint.request', {
      defaultValue: 'Con la prenotazione su richiesta questo ritiro NON comparirà nel calendario pubblico: la directory elenca solo ritiri prenotabili online all’istante. Resta prenotabile dal tuo store.',
    });
  } else if (mode === 'direct' && !loading && !ready) {
    message = t('directoryHint.stripeNote', {
      defaultValue: 'Finché Stripe non è attivo questo ritiro non comparirà nel calendario pubblico, anche se pubblicato.',
    });
  }
  if (!message) return null;

  return (
    <div
      className={`mt-2 rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-900 ${className}`}
      role="note"
      data-testid="directory-listing-hint"
    >
      <div className="flex items-start gap-2">
        <Info className="h-4 w-4 mt-0.5 shrink-0 text-amber-700" aria-hidden="true" />
        <p className="leading-snug">{message}</p>
      </div>
    </div>
  );
}
