/**
 * DpaPactBanner — PV7. Banner sobrio ma ben visibile nelle superfici
 * di vendita (/listino, /events) quando il patto di responsabilita'
 * (DPA art. 28) non e' ancora stato accettato.
 *
 * Volutamente "dumb": lo stato arriva da useDpaStatus (cache condivisa,
 * una sola GET /legal/dpa/status per sessione) e il bottone delega al
 * parent l'apertura del DpaPactDialog (onRead) — cosi' la pagina usa
 * UN solo dialog sia per il banner sia per il gate alla creazione.
 * Se il patto e' gia' accettato (o lo status non e' noto) non rende
 * nulla: zero rumore.
 */
import React from 'react';
import { useTranslation } from 'react-i18next';
import { ShieldAlert } from 'lucide-react';
import { Button } from '../ui/button';
import useDpaStatus from '../../hooks/useDpaStatus';

export default function DpaPactBanner({ onRead, className = '' }) {
  const { t } = useTranslation('legal');
  const { known, acknowledged } = useDpaStatus();

  if (!known || acknowledged) return null;

  return (
    <div
      className={`flex flex-wrap items-center gap-3 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 ${className}`}
      data-testid="dpa-pact-banner"
    >
      <ShieldAlert className="h-5 w-5 shrink-0 text-amber-600" aria-hidden />
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium text-amber-900">
          {t('dpa.pact.bannerTitle', {
            defaultValue: 'Prima di vendere: leggi e accetta la tua informativa di responsabilità',
          })}
        </p>
        <p className="text-xs text-amber-800/80">
          {t('dpa.pact.bannerBody', {
            defaultValue: 'Una firma sola per tutta la tua attività: l’accordo sul trattamento dei dati dei tuoi clienti (art. 28 GDPR).',
          })}
        </p>
      </div>
      <Button size="sm" variant="outline"
              className="border-amber-300 bg-white text-amber-900 hover:bg-amber-100"
              onClick={onRead} data-testid="dpa-pact-banner-cta">
        {t('dpa.pact.bannerCta', { defaultValue: 'Leggi e accetta' })}
      </Button>
    </div>
  );
}
