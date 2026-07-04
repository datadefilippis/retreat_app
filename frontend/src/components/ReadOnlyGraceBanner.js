/**
 * ReadOnlyGraceBanner — v5.2 hardening.
 *
 * Listens for 'billing:read-only-grace' custom events dispatched by the
 * Axios interceptor when a 403 with code READ_ONLY_GRACE is received.
 *
 * Displays a dismissible top banner explaining that the org is in a
 * read-only grace period after a downgrade, with a link to upgrade.
 */
import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { AlertTriangle, X } from 'lucide-react';

export function ReadOnlyGraceBanner({ onUpgradeClick }) {
  const { t } = useTranslation('settings');
  const [visible, setVisible] = useState(false);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    const handler = () => {
      if (!dismissed) setVisible(true);
    };
    window.addEventListener('billing:read-only-grace', handler);
    return () => window.removeEventListener('billing:read-only-grace', handler);
  }, [dismissed]);

  if (!visible || dismissed) return null;

  return (
    <div
      // v5.8 / Onda 9.R — sticky + z-[55] above sidebar (z-50) and header (z-30)
      className="sticky top-0 bg-amber-50 border-b border-amber-200 px-4 py-2 flex items-center justify-between text-sm text-amber-800"
      style={{ zIndex: 55 }}
    >
      <div className="flex items-center gap-2">
        <AlertTriangle className="h-4 w-4 flex-shrink-0" />
        <span>
          {t(
            'billing.read_only_grace',
            'Il tuo piano e stato declassato. Hai ancora accesso in sola lettura per 7 giorni. Aggiorna il piano per ripristinare l\'accesso completo.'
          )}
        </span>
        {onUpgradeClick && (
          <button
            onClick={onUpgradeClick}
            className="ml-2 underline font-medium hover:text-amber-900"
          >
            {t('billing.upgrade_now', 'Aggiorna ora')}
          </button>
        )}
      </div>
      <button
        onClick={() => setDismissed(true)}
        className="ml-4 text-amber-600 hover:text-amber-800 min-w-[44px] min-h-[44px] flex items-center justify-center -my-2"
        aria-label={t('billing.banner_dismiss', { defaultValue: 'Dismiss' })}
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  );
}

export default ReadOnlyGraceBanner;
