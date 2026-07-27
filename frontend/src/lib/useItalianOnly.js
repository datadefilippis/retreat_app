/**
 * useItalianOnly — founder 27/7: il sito pubblico parla SOLO italiano.
 *
 * Il multilingua resta nel prodotto (back-office operatori, traduzioni
 * contenuti) ma la vetrina pubblica si fissa su it: niente selettore
 * lingua e niente UI in en/de/fr da browser stranieri. Si monta sulle
 * superfici pubbliche (MarketplaceShell + landing standalone); il
 * back-office non lo usa e conserva la scelta lingua dell'operatore.
 */
import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';

export default function useItalianOnly() {
  const { i18n } = useTranslation();
  useEffect(() => {
    if ((i18n.language || '').slice(0, 2) !== 'it') {
      i18n.changeLanguage('it');
    }
  }, [i18n]);
}
