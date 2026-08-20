/**
 * AuryaQuickLogin — accesso rapido al checkout con l'account Aurya (AP1,
 * docs/ACCOUNT_UNICO_PIANO_2026-07.md).
 *
 * Pannello inline per i guest: email → codice a 6 cifre → sessione
 * piattaforma. Riusa ESATTAMENTE gli endpoint passwordless di
 * AccountLoginPage (/platform/auth/magic-link + /platform/auth/code/verify
 * via platformApi) e il token in localStorage (PLATFORM_TOKEN_KEY).
 *
 * Al successo (o se un token valido e' gia' in localStorage): profilo da
 * GET /platform/me, saluto inline e callback onProfile per prefillare
 * nome/email nel form del checkout.
 *
 * NON tocca la logica consensi: chi accede qui resta guest per CG-4
 * (le checkbox privacy/termini del checkout restano obbligatorie).
 */
import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import platformApi, { PLATFORM_TOKEN_KEY } from '../../../../api/platformClient';
import { salvaProva } from '../../../../lib/cerchio';

export default function AuryaQuickLogin({ onProfile }) {
  const { t, i18n } = useTranslation('storefront');
  // idle → (click) email → (codice inviato) sent → (verificato) done
  // AP1b: da 'email' si passa a 'password' (login email+password) col
  // toggle "Hai una password? Accedi" — l'OTP resta il default visivo.
  const [phase, setPhase] = useState('idle');
  const [account, setAccount] = useState(null);
  const [email, setEmail] = useState('');
  const [code, setCode] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  // callback stabile: il parent puo' ricreare la closure a ogni render
  const onProfileRef = useRef(onProfile);
  useEffect(() => { onProfileRef.current = onProfile; });

  // Gia' loggato platform (token valido in localStorage): prefill
  // automatico + saluto, senza aprire il pannello. Token scaduto o
  // invalido → silenzio, resta il link Accedi (niente redirect: vedi
  // platformClient, i 401 li gestisce chi chiama).
  useEffect(() => {
    const token = localStorage.getItem(PLATFORM_TOKEN_KEY);
    if (!token) return;
    let active = true;
    platformApi.get('/platform/me')
      .then(res => {
        if (!active) return;
        setAccount(res.data);
        setPhase('done');
        onProfileRef.current?.(res.data);
      })
      .catch(() => { /* token non valido: il link Accedi resta */ });
    return () => { active = false; };
  }, []);

  // R2a — la lingua UI viaggia con la richiesta OTP (stessa logica di
  // AccountLoginPage): il backend localizza l'email del codice.
  const emailLang = () => {
    const lang = (i18n.language || '').slice(0, 2).toLowerCase();
    return ['it', 'en', 'de', 'fr'].includes(lang) ? lang : undefined;
  };

  const sendCode = async (e) => {
    e.preventDefault();
    if (!email.includes('@')) return;
    setBusy(true); setError(null);
    try {
      await platformApi.post('/platform/auth/magic-link',
        { email: email.trim(), language: emailLang() });
      setPhase('sent');
      setCode('');
    } catch {
      setError(t('storefront:checkout.auryaLogin.sendError', {
        defaultValue: 'Qualcosa non ha funzionato. Riprova tra un minuto.',
      }));
    } finally {
      setBusy(false);
    }
  };

  const verifyCode = async (e) => {
    e.preventDefault();
    if (code.trim().length !== 6) return;
    setBusy(true); setError(null);
    try {
      const res = await platformApi.post('/platform/auth/code/verify',
        { email: email.trim(), code: code.trim() });
      localStorage.setItem(PLATFORM_TOKEN_KEY, res.data.access_token);
      // AP2 — iscritto confermato alla lettera di Aurya: il token che
      // sblocca le guide (stessa chiave letta dal blog BN3). Solo se
      // il backend lo ha emesso.
      if (res.data.subscriber_token) {
        salvaProva(res.data.subscriber_token);
      }
      // profilo fresco (nome incluso) per prefill e saluto
      const me = await platformApi.get('/platform/me');
      setAccount(me.data);
      setPhase('done');
      onProfileRef.current?.(me.data);
    } catch {
      setError(t('storefront:checkout.auryaLogin.codeError', {
        defaultValue: 'Codice non valido o scaduto. Controlla e riprova.',
      }));
    } finally {
      setBusy(false);
    }
  };

  // AP1b — login password: stessa gestione token/subscriber_token e
  // stesso prefill via GET /platform/me delle altre strade.
  const passwordLogin = async (e) => {
    e.preventDefault();
    if (!email.includes('@') || !password) return;
    setBusy(true); setError(null);
    try {
      const res = await platformApi.post('/platform/auth/login',
        { email: email.trim(), password });
      localStorage.setItem(PLATFORM_TOKEN_KEY, res.data.access_token);
      if (res.data.subscriber_token) {
        salvaProva(res.data.subscriber_token);
      }
      const me = await platformApi.get('/platform/me');
      setAccount(me.data);
      setPhase('done');
      onProfileRef.current?.(me.data);
    } catch (err) {
      const status = err?.response?.status;
      const detail = err?.response?.data?.detail || '';
      if (status === 423) {
        setError(t('storefront:checkout.auryaLogin.passwordLocked', {
          defaultValue: 'Troppi tentativi: riprova più tardi o accedi senza password.',
        }));
      } else if (status === 403 && detail === 'EMAIL_NOT_VERIFIED') {
        setError(t('storefront:checkout.auryaLogin.passwordNotVerified', {
          defaultValue: 'Prima conferma la tua email: controlla la posta.',
        }));
      } else {
        setError(t('storefront:checkout.auryaLogin.passwordError', {
          defaultValue: 'Email o password non corretti.',
        }));
      }
    } finally {
      setBusy(false);
    }
  };

  const inputCls = 'w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-gray-800 focus:border-transparent outline-none';

  if (phase === 'done' && account) {
    return (
      <div className="rounded-lg border border-emerald-200 bg-emerald-50/60 px-3 py-2 flex items-center gap-2"
           data-testid="aurya-login-greeting">
        <img src="/logo-aurya-128.png" alt="" aria-hidden
             className="h-4 w-4 select-none" draggable={false} />
        <p className="text-xs text-emerald-900">
          {account.name
            ? t('storefront:checkout.auryaLogin.greeting', {
                defaultValue: 'Ciao {{name}}, ordini come {{email}}',
                name: account.name, email: account.email,
              })
            : t('storefront:checkout.auryaLogin.greetingNoName', {
                defaultValue: 'Ordini come {{email}}',
                email: account.email,
              })}
        </p>
      </div>
    );
  }

  if (phase === 'idle') {
    return (
      <p className="text-xs text-gray-600">
        <button
          type="button"
          onClick={() => setPhase('email')}
          className="underline text-gray-700 hover:text-gray-900 font-medium"
          data-testid="aurya-login-open"
        >
          {t('storefront:checkout.auryaLogin.open', {
            defaultValue: 'Hai già un account Aurya? Accedi',
          })}
        </button>
      </p>
    );
  }

  return (
    <div className="rounded-lg border border-gray-200 bg-gray-50/60 p-3 space-y-2"
         data-testid="aurya-login-panel">
      <div className="flex items-center justify-between gap-2">
        <p className="text-xs font-medium text-gray-800 flex items-center gap-1.5">
          <img src="/logo-aurya-128.png" alt="" aria-hidden
               className="h-4 w-4 select-none" draggable={false} />
          {t('storefront:checkout.auryaLogin.title', {
            defaultValue: 'Accedi con il tuo account Aurya',
          })}
        </p>
        <button
          type="button"
          onClick={() => { setPhase('idle'); setError(null); }}
          className="text-[11px] text-gray-500 hover:text-gray-700"
        >
          {t('storefront:checkout.auryaLogin.cancel', { defaultValue: 'Annulla' })}
        </button>
      </div>

      {phase === 'email' && (
        <div className="space-y-2">
          <p className="text-[11px] text-gray-500">
            {t('storefront:checkout.auryaLogin.emailHint', {
              defaultValue: 'Niente password: ti mandiamo un codice via email.',
            })}
          </p>
          <div className="flex gap-2">
            <input
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              // il pannello vive DENTRO il <form> del checkout: Enter qui
              // deve inviare il codice, non l'ordine
              onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); sendCode(e); } }}
              placeholder={t('storefront:checkout.auryaLogin.emailPlaceholder', {
                defaultValue: 'La tua email',
              })}
              className={inputCls}
            />
            <button
              type="button"
              onClick={sendCode}
              disabled={busy || !email.includes('@')}
              className="shrink-0 rounded-lg bg-gray-900 text-white px-3 py-2 text-sm font-medium disabled:opacity-50"
              data-testid="aurya-login-send"
            >
              {busy
                ? t('storefront:checkout.auryaLogin.sending', { defaultValue: 'Invio…' })
                : t('storefront:checkout.auryaLogin.send', { defaultValue: 'Inviami il codice' })}
            </button>
          </div>
          <button
            type="button"
            onClick={() => { setPhase('password'); setError(null); }}
            className="text-[11px] text-gray-500 underline hover:text-gray-700"
            data-testid="aurya-login-have-password"
          >
            {t('storefront:checkout.auryaLogin.havePassword', {
              defaultValue: 'Hai una password? Accedi',
            })}
          </button>
        </div>
      )}

      {phase === 'password' && (
        <div className="space-y-2">
          <p className="text-[11px] text-gray-500">
            {t('storefront:checkout.auryaLogin.passwordHint', {
              defaultValue: 'Entra con la tua email e la tua password.',
            })}
          </p>
          <input
            type="email"
            value={email}
            onChange={e => setEmail(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); passwordLogin(e); } }}
            placeholder={t('storefront:checkout.auryaLogin.emailPlaceholder', {
              defaultValue: 'La tua email',
            })}
            className={inputCls}
          />
          <div className="flex gap-2">
            <input
              type="password"
              value={password}
              autoComplete="current-password"
              onChange={e => setPassword(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); passwordLogin(e); } }}
              placeholder={t('storefront:checkout.auryaLogin.passwordPlaceholder', {
                defaultValue: 'La tua password',
              })}
              className={inputCls}
              data-testid="aurya-login-password"
            />
            <button
              type="button"
              onClick={passwordLogin}
              disabled={busy || !email.includes('@') || !password}
              className="shrink-0 rounded-lg bg-gray-900 text-white px-3 py-2 text-sm font-medium disabled:opacity-50"
              data-testid="aurya-login-password-submit"
            >
              {busy
                ? t('storefront:checkout.auryaLogin.verifying', { defaultValue: 'Verifico…' })
                : t('storefront:checkout.auryaLogin.verify', { defaultValue: 'Entra' })}
            </button>
          </div>
          <button
            type="button"
            onClick={() => { setPhase('email'); setError(null); }}
            className="text-[11px] text-gray-500 underline hover:text-gray-700"
            data-testid="aurya-login-no-password"
          >
            {t('storefront:checkout.auryaLogin.noPassword', {
              defaultValue: 'Accedi senza password',
            })}
          </button>
        </div>
      )}

      {phase === 'sent' && (
        <div className="space-y-2">
          <p className="text-[11px] text-gray-500">
            {t('storefront:checkout.auryaLogin.sentHint', {
              defaultValue: 'Codice a 6 cifre inviato a {{email}}. Vale 15 minuti.',
              email: email.trim(),
            })}
          </p>
          <div className="flex gap-2">
            <input
              type="text" inputMode="numeric" autoComplete="one-time-code"
              maxLength={6} value={code}
              onChange={e => setCode(e.target.value.replace(/\D/g, ''))}
              onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); verifyCode(e); } }}
              placeholder="••••••"
              className={`${inputCls} text-center tracking-[0.4em] font-semibold`}
              data-testid="aurya-login-code"
              autoFocus
            />
            <button
              type="button"
              onClick={verifyCode}
              disabled={busy || code.length !== 6}
              className="shrink-0 rounded-lg bg-gray-900 text-white px-3 py-2 text-sm font-medium disabled:opacity-50"
              data-testid="aurya-login-verify"
            >
              {busy
                ? t('storefront:checkout.auryaLogin.verifying', { defaultValue: 'Verifico…' })
                : t('storefront:checkout.auryaLogin.verify', { defaultValue: 'Entra' })}
            </button>
          </div>
          <button
            type="button"
            onClick={() => { setPhase('email'); setError(null); }}
            className="text-[11px] text-gray-500 underline hover:text-gray-700"
          >
            {t('storefront:checkout.auryaLogin.changeEmail', {
              defaultValue: 'Usa un\'altra email',
            })}
          </button>
        </div>
      )}

      {error && <p className="text-[11px] text-red-600">{error}</p>}
    </div>
  );
}
