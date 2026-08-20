/**
 * AccountResetPasswordPage — /account/nuova-password?token=... (AP1b).
 *
 * Imposta la nuova password col token ricevuto via email (one-shot).
 * Serve anche agli account nati passwordless (claim acquisto) per
 * scegliere la password la PRIMA volta. Esiti onesti: password
 * impostata → invito ad accedere; token scaduto o usato → spiegazione.
 */
import React, { useState } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { CheckCircle2, AlertTriangle, KeyRound } from 'lucide-react';
import platformApi from '../../api/platformClient';
import useSeoMeta from '../storefront/lib/useSeoMeta';
import MarketplaceShell from '../storefront/components/MarketplaceShell';

export default function AccountResetPasswordPage() {
  const { t } = useTranslation('landings');
  const [params] = useSearchParams();
  const token = params.get('token');
  const [state, setState] = useState(token ? 'form' : 'invalid');
  const [password, setPassword] = useState('');
  const [sending, setSending] = useState(false);
  const [error, setError] = useState(null);

  useSeoMeta({ title: 'Nuova password', noindex: true });

  const submit = async (e) => {
    e.preventDefault();
    setSending(true); setError(null);
    try {
      await platformApi.post('/platform/auth/password-reset/confirm',
        { token, new_password: password });
      setState('ok');
    } catch (err) {
      const status = err?.response?.status;
      const detail = err?.response?.data?.detail || '';
      if (status === 400 && detail.startsWith('Link non valido')) {
        setState('invalid');
      } else if (status === 400 && detail) {
        // policy password: il backend spiega cosa manca
        setError(String(detail));
      } else {
        setError(t('landings:account.requestError', {
          defaultValue: 'Qualcosa non ha funzionato. Riprova tra un minuto.',
        }));
      }
    } finally {
      setSending(false);
    }
  };

  return (
    <MarketplaceShell>
    <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
      <div className="w-full max-w-sm rounded-2xl border border-gray-200 bg-white p-6 text-center">
        {state === 'form' && (
          <>
            <KeyRound className="h-8 w-8 text-primary mx-auto" />
            <h1 className="mt-3 text-lg font-bold text-gray-900">
              {t('landings:account.newPasswordTitle', { defaultValue: 'Scegli la nuova password' })}
            </h1>
            <p className="mt-1 text-sm text-gray-600">
              {t('landings:account.newPasswordBody', { defaultValue: 'La userai per entrare nel tuo account Aurya con la tua email.' })}
            </p>
            <form onSubmit={submit} className="mt-4 space-y-3" data-testid="new-password-form">
              <input
                type="password" required value={password} autoComplete="new-password"
                onChange={e => setPassword(e.target.value)}
                placeholder={t('landings:account.newPasswordPlaceholder', { defaultValue: 'Nuova password' })}
                className="w-full rounded-xl border border-gray-300 px-3 py-2.5 text-sm focus:border-primary focus:outline-none"
                autoFocus
              />
              <p className="text-[11px] text-gray-400 text-left">
                {t('landings:account.passwordHint', { defaultValue: 'Almeno 12 caratteri, con maiuscole, minuscole e numeri.' })}
              </p>
              {error && <p className="text-xs text-red-600">{error}</p>}
              <button type="submit" disabled={sending || !password}
                className="w-full rounded-xl bg-primary text-primary-foreground py-2.5 text-sm font-semibold disabled:opacity-60"
                data-testid="new-password-submit">
                {sending
                  ? t('landings:account.sending', { defaultValue: 'Invio…' })
                  : t('landings:account.newPasswordSubmit', { defaultValue: 'Imposta la password' })}
              </button>
            </form>
          </>
        )}

        {state === 'ok' && (
          <>
            <CheckCircle2 className="h-8 w-8 text-primary mx-auto" />
            <h1 className="mt-3 text-lg font-bold text-gray-900" data-testid="new-password-ok">
              {t('landings:account.newPasswordOkTitle', { defaultValue: 'Password impostata' })}
            </h1>
            <p className="mt-2 text-sm text-gray-600">
              {t('landings:account.newPasswordOkBody', { defaultValue: 'Ora puoi accedere al tuo account Aurya con la tua email e la nuova password.' })}
            </p>
            <Link to="/accedi"
              className="mt-4 block w-full rounded-xl bg-primary text-primary-foreground py-2.5 text-sm font-semibold">
              {t('landings:account.goToLogin', { defaultValue: 'Vai all\'accesso' })}
            </Link>
          </>
        )}

        {state === 'invalid' && (
          <>
            <AlertTriangle className="h-8 w-8 text-amber-500 mx-auto" />
            <h1 className="mt-3 text-lg font-bold text-gray-900" data-testid="new-password-fail">
              {t('landings:account.newPasswordFailTitle', { defaultValue: 'Link non valido o scaduto' })}
            </h1>
            <p className="mt-2 text-sm text-gray-600">
              {t('landings:account.newPasswordFailBody', { defaultValue: 'Il link è scaduto o è già stato usato. Richiedine uno nuovo dalla pagina di accesso con Password dimenticata.' })}
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
