/**
 * DirectoryListingHint — GT7: accanto al selettore «Come si prenota»
 * dei RITIRI dice cosa succede nel marketplace pubblico.
 *
 * Storia: dal GT1b (luglio) la directory elencava SOLO ritiri
 * prenotabili online con Stripe, e questo avviso spiegava l'esclusione.
 * P3 (10/9/2026, piano di business, decisione founder): il marketplace
 * «Ritiri ed esperienze» e' GRATIS per tutti i ritiri pubblicati, con o
 * senza Stripe. L'avviso ora racconta il percorso, non un'esclusione:
 *   - mode 'request'          → il ritiro compare; la richiesta arriva
 *                               via email e la caparra si chiede con un
 *                               bonifico (P2).
 *   - mode 'direct' + !ready  → una riga complementare a
 *                               StripeRequiredAlert: senza Stripe il
 *                               pagamento sul sito non parte e il ritiro
 *                               NON compare (SD6 14/9: la regola vera e'
 *                               services/ritiri_visibilita.py — prima qui
 *                               si prometteva «compare comunque»).
 *
 * Solo per prodotti evento: gli altri tipi non vivono nel marketplace.
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
      defaultValue: 'Su richiesta: il ritiro compare in Ritiri ed esperienze e sul tuo profilo pubblico. La richiesta ti arriva via email, e la caparra la chiedi con un bonifico (le istruzioni partono da sole se hai messo l’IBAN nelle Impostazioni).',
    });
  } else if (mode === 'direct' && !loading && !ready) {
    message = t('directoryHint.stripeNote', {
      // SD6 (14/9/2026): la lista pubblica ESCLUDE l'online senza Stripe
      // (non si potrebbe prenotare in nessun modo): l'avviso lo dice
      defaultValue: 'Prenotazione online: finché Stripe non è attivo il pagamento sul sito non parte e il ritiro non compare in Ritiri ed esperienze. Scegli «su richiesta» (compare subito, la richiesta ti arriva via email) oppure collega Stripe nelle Impostazioni.',
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
