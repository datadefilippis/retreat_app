/**
 * AccountLoginPage — /account/accedi (P3, Passaporto Ritiri).
 *
 * Due modalita':
 *  - ?token=... (dal magic link email): consuma il token, salva la
 *    sessione piattaforma e porta a /account
 *  - senza token: form email → richiede un nuovo magic link (202 sempre)
 *
 * Mobile-first (si apre quasi sempre dal telefono, dall'email). noindex.
 */
import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Loader2, Mail, CheckCircle2 } from 'lucide-react';
import platformApi, { PLATFORM_TOKEN_KEY } from '../../api/platformClient';
import useSeoMeta from '../storefront/lib/useSeoMeta';

// Guard module-level: il magic token e' ONE-SHOT lato server, ma in dev
// React StrictMode monta l'effect due volte → due verify concorrenti, la
// seconda perde e mostrerebbe 'scaduto' anche con link valido. Una sola
// POST per token, sempre.
const attemptedTokens = new Set();

export default function AccountLoginPage() {
  const { t } = useTranslation('landings');
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const token = params.get('token');

  const [state, setState] = useState(token ? 'verifying' : 'form');
  const [email, setEmail] = useState('');
  const [sending, setSending] = useState(false);
  const [error, setError] = useState(null);

  useSeoMeta({ title: 'Accedi — le tue prenotazioni' });
  useEffect(() => {
    const meta = document.createElement('meta');
    meta.name = 'robots'; meta.content = 'noindex';
    document.head.appendChild(meta);
    return () => { document.head.removeChild(meta); };
  }, []);

  useEffect(() => {
    if (!token || attemptedTokens.has(token)) return;
    attemptedTokens.add(token);
    platformApi.post('/platform/auth/magic-link/verify', { token })
      .then(res => {
        // salva SEMPRE (anche se lo StrictMode ha smontato questo mount:
        // la sessione e' valida e il remount la trovera')
        localStorage.setItem(PLATFORM_TOKEN_KEY, res.data.access_token);
        navigate('/account', { replace: true });
      })
      .catch(() => setState('expired'));
  }, [token, navigate]);

  const requestLink = async (e) => {
    e.preventDefault();
    setSending(true); setError(null);
    try {
      await platformApi.post('/platform/auth/magic-link', { email });
      setState('sent');
    } catch {
      setError(t('landings:account.requestError', {
        defaultValue: 'Qualcosa non ha funzionato. Riprova tra un minuto.',
      }));
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
      <div className="w-full max-w-sm rounded-2xl border border-gray-200 bg-white p-6 text-center">
        {state === 'verifying' && (
          <>
            <Loader2 className="h-8 w-8 animate-spin text-primary mx-auto" />
            <p className="mt-4 text-sm text-gray-600">
              {t('landings:account.verifying', { defaultValue: 'Un attimo, ti facciamo entrare…' })}
            </p>
          </>
        )}

        {state === 'expired' && (
          <>
            <h1 className="text-lg font-bold text-gray-900">
              {t('landings:account.expiredTitle', { defaultValue: 'Link scaduto o già usato' })}
            </h1>
            <p className="mt-2 text-sm text-gray-600">
              {t('landings:account.expiredBody', { defaultValue: 'Nessun problema: inserisci la tua email e te ne mandiamo uno nuovo.' })}
            </p>
            <button onClick={() => setState('form')}
              className="mt-4 w-full rounded-xl bg-primary text-primary-foreground py-2.5 text-sm font-semibold">
              {t('landings:account.requestNew', { defaultValue: 'Richiedi un nuovo link' })}
            </button>
          </>
        )}

        {state === 'form' && (
          <>
            <Mail className="h-8 w-8 text-primary mx-auto" />
            <h1 className="mt-3 text-lg font-bold text-gray-900">
              {t('landings:account.loginTitle', { defaultValue: 'Le tue prenotazioni' })}
            </h1>
            <p className="mt-1 text-sm text-gray-600">
              {t('landings:account.loginBody', { defaultValue: 'Niente password: ti mandiamo un link di accesso via email.' })}
            </p>
            <form onSubmit={requestLink} className="mt-4 space-y-3">
              <input
                type="email" required value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder={t('landings:account.emailPlaceholder', { defaultValue: 'La tua email' })}
                className="w-full rounded-xl border border-gray-300 px-3 py-2.5 text-sm focus:border-primary focus:outline-none"
              />
              {error && <p className="text-xs text-red-600">{error}</p>}
              <button type="submit" disabled={sending}
                className="w-full rounded-xl bg-primary text-primary-foreground py-2.5 text-sm font-semibold disabled:opacity-60">
                {sending
                  ? t('landings:account.sending', { defaultValue: 'Invio…' })
                  : t('landings:account.sendLink', { defaultValue: 'Inviami il link' })}
              </button>
            </form>
          </>
        )}

        {state === 'sent' && (
          <>
            <CheckCircle2 className="h-8 w-8 text-primary mx-auto" />
            <h1 className="mt-3 text-lg font-bold text-gray-900">
              {t('landings:account.sentTitle', { defaultValue: 'Controlla la tua email' })}
            </h1>
            <p className="mt-2 text-sm text-gray-600">
              {t('landings:account.sentBody', { defaultValue: 'Se esiste un account per questo indirizzo, riceverai un link di accesso valido 15 minuti.' })}
            </p>
          </>
        )}

        <p className="mt-6 text-xs text-gray-400">
          <Link to="/ritiri" className="hover:underline">
            {t('landings:account.backToRetreats', { defaultValue: '← Torna ai ritiri' })}
          </Link>
        </p>
      </div>
    </div>
  );
}
