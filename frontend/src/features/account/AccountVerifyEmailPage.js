/**
 * AccountVerifyEmailPage — /account/verifica?token=... (AP1b).
 *
 * Consuma il token di verifica email del signup (one-shot lato server).
 * FL5 (5/10/2026 sera, founder): il clic FA ENTRARE, come per il
 * professionista (FV1). Il server, con la verifica, rilascia la stessa
 * sessione del magic link (e la prova del Cerchio se c'e'): la pagina la
 * adotta e porta dove la persona stava andando (`next`, dalla porta dei
 * contatti) o all'account. Se la sessione non arriva (client/server
 * vecchi, account non attivo) resta la strada di ieri: «Vai all'accesso»
 * con l'email precompilata. Token scaduto o gia' usato → spiegazione e
 * strade di recupero.
 */
import React, { useEffect, useState } from 'react';
import { useSearchParams, Link, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Loader2, CheckCircle2, AlertTriangle } from 'lucide-react';
import platformApi, { PLATFORM_TOKEN_KEY } from '../../api/platformClient';
import useSeoMeta from '../storefront/lib/useSeoMeta';
import MarketplaceShell from '../storefront/components/MarketplaceShell';
import { entraInAurya } from '../../utils/authLinks';
import { salvaProva } from '../../lib/cerchio';

// Il token e' one-shot: StrictMode in dev monta l'effect due volte, la
// seconda POST perderebbe e mostrerebbe 'scaduto' su un link buono.
const attemptedTokens = new Set();

export default function AccountVerifyEmailPage() {
  const { t } = useTranslation('landings');
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const token = params.get('token');
  // 26/9 — `next` arriva SOLO dai link nati dalla porta dei contatti: dopo la
  // conferma si torna dove si era. Solo percorsi interni.
  const rawNext = params.get('next') || '';
  const next = rawNext.startsWith('/') && !rawNext.startsWith('//') ? rawNext : '';
  const [emailConfermata, setEmailConfermata] = useState('');
  const [dentro, setDentro] = useState(false);     // FL5: la sessione e' arrivata ed e' salvata
  const [state, setState] = useState(token ? 'verifying' : 'invalid');

  useSeoMeta({ title: 'Conferma email', noindex: true });

  useEffect(() => {
    if (!token || attemptedTokens.has(token)) return;
    attemptedTokens.add(token);
    platformApi.post('/platform/auth/verify-email', { token })
      .then((res) => {
        const d = res.data || {};
        setEmailConfermata(d.email || '');
        // FL5 — stessa adozione di sessione del login (AccountLoginPage.saveSession)
        if (d.access_token) {
          try {
            localStorage.setItem(PLATFORM_TOKEN_KEY, d.access_token);
            if (d.subscriber_token) salvaProva(d.subscriber_token);
            setDentro(true);
          } catch { /* storage inaccessibile: resta la strada del login */ }
        }
        setState('ok');
      })
      .catch(() => setState('invalid'));
  }, [token]);

  const destinazione = next || '/account';

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
              {dentro
                ? t('landings:account.verifyOkTitleDentro', { defaultValue: 'Email confermata: sei dentro' })
                : t('landings:account.verifyOkTitle', { defaultValue: 'Email confermata' })}
            </h1>
            <p className="mt-2 text-sm text-gray-600">
              {dentro
                ? t('landings:account.verifyOkBodyDentro', { defaultValue: 'Il tuo account Aurya è attivo e sei già connesso su questo dispositivo.' })
                : t('landings:account.verifyOkBody', { defaultValue: 'Il tuo account Aurya è attivo. Ora puoi accedere con la tua password.' })}
            </p>
            {dentro ? (
              <button type="button" onClick={() => navigate(destinazione)} data-testid="verify-vai"
                className="mt-4 block w-full rounded-xl bg-primary text-primary-foreground py-2.5 text-sm font-semibold">
                {next
                  ? t('landings:account.verifyTornaDentro', { defaultValue: 'Torna dove eri' })
                  : t('landings:account.verifyVaiAccount', { defaultValue: 'Vai al tuo account' })}
              </button>
            ) : next ? (
              <a href={entraInAurya(emailConfermata, next)} data-testid="verify-torna"
                className="mt-4 block w-full rounded-xl bg-primary text-primary-foreground py-2.5 text-sm font-semibold">
                {t('landings:account.verifyTorna', { defaultValue: 'Entra e torna dove eri' })}
              </a>
            ) : (
              <Link to="/accedi"
                className="mt-4 block w-full rounded-xl bg-primary text-primary-foreground py-2.5 text-sm font-semibold">
                {t('landings:account.goToLogin', { defaultValue: 'Vai all\'accesso' })}
              </Link>
            )}
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
            <Link to="/accedi"
              className="mt-4 block w-full rounded-xl bg-primary text-primary-foreground py-2.5 text-sm font-semibold">
              {t('landings:account.goToLogin', { defaultValue: 'Vai all\'accesso' })}
            </Link>
          </>
        )}

        <p className="mt-6 text-xs text-gray-400">
          <Link to="/" className="hover:underline">
            {t('landings:account.backToAurya2', { defaultValue: '← Torna su Aurya' })}
          </Link>
        </p>
      </div>
    </div>
    </MarketplaceShell>
  );
}
