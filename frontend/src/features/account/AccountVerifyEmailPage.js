/**
 * AccountVerifyEmailPage — /account/verifica?token=... (AP1b).
 *
 * Consuma il token di verifica email del signup (one-shot lato server).
 * Esiti onesti: verificata → invito ad accedere con la password;
 * token scaduto o gia' usato → spiegazione e strade di recupero.
 */
import React, { useEffect, useState } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Loader2, CheckCircle2, AlertTriangle } from 'lucide-react';
import platformApi from '../../api/platformClient';
import useSeoMeta from '../storefront/lib/useSeoMeta';
import MarketplaceShell from '../storefront/components/MarketplaceShell';

// Il token e' one-shot: StrictMode in dev monta l'effect due volte, la
// seconda POST perderebbe e mostrerebbe 'scaduto' su un link buono.
const attemptedTokens = new Set();

export default function AccountVerifyEmailPage() {
  const { t } = useTranslation('landings');
  const [params] = useSearchParams();
  const token = params.get('token');
  const [state, setState] = useState(token ? 'verifying' : 'invalid');

  useSeoMeta({ title: 'Conferma email', noindex: true });

  useEffect(() => {
    if (!token || attemptedTokens.has(token)) return;
    attemptedTokens.add(token);
    platformApi.post('/platform/auth/verify-email', { token })
      .then(() => setState('ok'))
      .catch(() => setState('invalid'));
  }, [token]);

  return (
    <MarketplaceShell>
    <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
      <div className="w-full max-w-sm rounded-2xl border border-gray-200 bg-white p-6 text-center">
        {state === 'verifying' && (
          <>
            <Loader2 className="h-8 w-8 animate-spin text-primary mx-auto" />
            <p className="mt-4 text-sm text-gray-600">
              {t('landings:account.verifyChecking', { defaultValue: 'Un attimo, confermiamo la tua email…' })}
            </p>
          </>
        )}

        {state === 'ok' && (
          <>
            <CheckCircle2 className="h-8 w-8 text-primary mx-auto" />
            <h1 className="mt-3 text-lg font-bold text-gray-900" data-testid="verify-ok">
              {t('landings:account.verifyOkTitle', { defaultValue: 'Email confermata' })}
            </h1>
            <p className="mt-2 text-sm text-gray-600">
              {t('landings:account.verifyOkBody', { defaultValue: 'Il tuo account Aurya è attivo. Ora puoi accedere con la tua password.' })}
            </p>
            <Link to="/account/accedi"
              className="mt-4 block w-full rounded-xl bg-primary text-primary-foreground py-2.5 text-sm font-semibold">
              {t('landings:account.goToLogin', { defaultValue: 'Vai all\'accesso' })}
            </Link>
          </>
        )}

        {state === 'invalid' && (
          <>
            <AlertTriangle className="h-8 w-8 text-amber-500 mx-auto" />
            <h1 className="mt-3 text-lg font-bold text-gray-900" data-testid="verify-fail">
              {t('landings:account.verifyFailTitle', { defaultValue: 'Link non valido o scaduto' })}
            </h1>
            <p className="mt-2 text-sm text-gray-600">
              {t('landings:account.verifyFailBody', { defaultValue: 'Il link di conferma è scaduto o è già stato usato. Dalla pagina di accesso puoi usare Password dimenticata: il link che riceverai conferma anche la tua email.' })}
            </p>
            <Link to="/account/accedi"
              className="mt-4 block w-full rounded-xl bg-primary text-primary-foreground py-2.5 text-sm font-semibold">
              {t('landings:account.goToLogin', { defaultValue: 'Vai all\'accesso' })}
            </Link>
          </>
        )}

        <p className="mt-6 text-xs text-gray-400">
          <Link to="/" className="hover:underline">
            {t('landings:account.backToRetreats', { defaultValue: '← Torna ai ritiri' })}
          </Link>
        </p>
      </div>
    </div>
    </MarketplaceShell>
  );
}
