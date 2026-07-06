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
import MarketplaceShell from '../storefront/components/MarketplaceShell';

// Guard module-level: il magic token e' ONE-SHOT lato server, ma in dev
// React StrictMode monta l'effect due volte → due verify concorrenti, la
// seconda perde e mostrerebbe 'scaduto' anche con link valido. Una sola
// POST per token, sempre.
const attemptedTokens = new Set();

export default function AccountLoginPage() {
  const { t, i18n } = useTranslation('landings');
  // R2a — la lingua UI viaggia con la richiesta OTP: il backend la salva
  // come preferenza del Passaporto e localizza l'email del codice.
  const emailLang = () => {
    const lang = (i18n.language || '').slice(0, 2).toLowerCase();
    return ['it', 'en', 'de', 'fr'].includes(lang) ? lang : undefined;
  };
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

  // OTP a 6 cifre: la strada IMMEDIATA (il link resta come fallback
  // nella stessa email)
  const [code, setCode] = useState('');
  const [verifyingCode, setVerifyingCode] = useState(false);
  const verifyCode = async (e) => {
    e.preventDefault();
    if (code.trim().length !== 6) return;
    setVerifyingCode(true); setError(null);
    try {
      const res = await platformApi.post('/platform/auth/code/verify',
        { email, code: code.trim() });
      localStorage.setItem(PLATFORM_TOKEN_KEY, res.data.access_token);
      navigate('/account');
    } catch {
      setError(t('landings:account.codeError', {
        defaultValue: 'Codice non valido o scaduto. Controlla e riprova.',
      }));
    } finally {
      setVerifyingCode(false);
    }
  };

  // arrivo dal success di un acquisto: codice GIA' inviato all'email
  // dell'ordine → dritti all'input del codice
  useEffect(() => {
    const p = new URLSearchParams(window.location.search);
    const em = p.get('email');
    if (em && p.get('sent') === '1') {
      setEmail(em);
      setState('sent');
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const requestLink = async (e) => {
    e.preventDefault();
    setSending(true); setError(null);
    try {
      await platformApi.post('/platform/auth/magic-link',
        { email, language: emailLang() });
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
    <MarketplaceShell>
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
              {t('landings:account.loginBody', { defaultValue: 'Niente password: ti mandiamo un codice via email, lo digiti qui e sei dentro.' })}
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
                  : t('landings:account.sendCode', { defaultValue: 'Inviami il codice' })}
              </button>
            </form>
          </>
        )}

        {state === 'sent' && (
          <>
            <CheckCircle2 className="h-8 w-8 text-primary mx-auto" />
            <h1 className="mt-3 text-lg font-bold text-gray-900">
              {t('landings:account.sentCodeTitle', { defaultValue: 'Inserisci il codice' })}
            </h1>
            <p className="mt-2 text-sm text-gray-600">
              {t('landings:account.sentCodeBody', { defaultValue: 'Ti abbiamo inviato un codice a 6 cifre (vale 15 minuti). Nella stessa email c\'è anche un link, se preferisci.' })}
            </p>
            <form onSubmit={verifyCode} className="mt-4 space-y-3">
              <input
                type="text" inputMode="numeric" autoComplete="one-time-code"
                maxLength={6} value={code}
                onChange={e => setCode(e.target.value.replace(/\D/g, ''))}
                placeholder="••••••"
                className="w-full rounded-xl border border-gray-300 px-3 py-2.5 text-center text-2xl tracking-[0.5em] font-bold focus:border-primary focus:outline-none"
                autoFocus
              />
              {error && <p className="text-xs text-red-600">{error}</p>}
              <button type="submit" disabled={verifyingCode || code.length !== 6}
                className="w-full rounded-xl bg-primary text-primary-foreground py-2.5 text-sm font-semibold disabled:opacity-60">
                {verifyingCode
                  ? t('landings:account.verifyingCode', { defaultValue: 'Verifico…' })
                  : t('landings:account.enter', { defaultValue: 'Entra' })}
              </button>
            </form>
          </>
        )}

        <p className="mt-6 text-xs text-gray-400">
          <Link to="/ritiri" className="hover:underline">
            {t('landings:account.backToRetreats', { defaultValue: '← Torna ai ritiri' })}
          </Link>
        </p>
      </div>
    </div>
    </MarketplaceShell>
  );
}
