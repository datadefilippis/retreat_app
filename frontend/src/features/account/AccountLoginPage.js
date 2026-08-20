/**
 * AccountLoginPage — /accedi, LA PORTA UNICA (P3 + AP1b + ID 20/8).
 *
 * /login e /account/accedi vivono come alias redirect: qui una email e
 * una password valgono per QUALUNQUE cappello (operatore o cliente).
 *
 * AP1b: il login con EMAIL e PASSWORD e' il percorso primario. Sotto,
 * due strade secondarie: "Accedi senza password" (il flusso OTP/magic
 * link esistente, identico) e "Password dimenticata?" (richiesta reset,
 * che serve anche a IMPOSTARE la password per gli account nati
 * passwordless da un acquisto). Da qui si raggiunge anche la creazione
 * account ("Crea il tuo account Aurya").
 *
 * Modalita' con token in query:
 *  - ?token=... (dal magic link email): consuma il token, salva la
 *    sessione piattaforma e porta a /account
 *
 * Mobile-first (si apre quasi sempre dal telefono, dall'email). noindex.
 */
import React, { useEffect, useRef, useState } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Loader2, Mail, CheckCircle2, KeyRound, UserPlus, Briefcase } from 'lucide-react';
import platformApi, { PLATFORM_TOKEN_KEY } from '../../api/platformClient';
import useSeoMeta from '../storefront/lib/useSeoMeta';
import MarketplaceShell from '../storefront/components/MarketplaceShell';

// Guard module-level: il magic token e' ONE-SHOT lato server, ma in dev
// React StrictMode monta l'effect due volte → due verify concorrenti, la
// seconda perde e mostrerebbe 'scaduto' anche con link valido. Una sola
// POST per token, sempre.
const attemptedTokens = new Set();

// AP2 — se il login dice che l'email e' iscritta confermata alla lettera
// di Aurya, il subscriber_token va nella STESSA chiave che il blog (BN3)
// legge per sbloccare le guide riservate. Solo se presente: per chi non
// e' iscritto non si scrive (ne' si cancella) nulla.
const NL_TOKEN_KEY = 'aurya_nl_token';
const saveSubscriberToken = (data) => {
  if (!data?.subscriber_token) return;
  try { localStorage.setItem(NL_TOKEN_KEY, data.subscriber_token); } catch { /* private mode */ }
};

// AP1b — salvataggio sessione unico per TUTTE le strade di login
// (password, OTP, magic link): stesso token, stesso eventuale
// subscriber_token.
const saveSession = (data) => {
  localStorage.setItem(PLATFORM_TOKEN_KEY, data.access_token);
  saveSubscriberToken(data);
};

const inputCls = 'w-full rounded-xl border border-gray-300 px-3 py-2.5 text-sm focus:border-primary focus:outline-none';
const btnCls = 'w-full rounded-xl bg-primary text-primary-foreground py-2.5 text-sm font-semibold disabled:opacity-60';
const linkBtnCls = 'text-xs text-gray-500 underline hover:text-gray-700';

export default function AccountLoginPage() {
  const { t, i18n } = useTranslation('landings');
  // R2a — la lingua UI viaggia con le richieste (OTP, signup, reset): il
  // backend la salva come preferenza dell'account e localizza le email.
  const emailLang = () => {
    const lang = (i18n.language || '').slice(0, 2).toLowerCase();
    return ['it', 'en', 'de', 'fr'].includes(lang) ? lang : undefined;
  };
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const token = params.get('token');
  // ID — ?next= come su ogni porta: solo percorsi interni (mai '//')
  const rawNext = params.get('next');
  const next = rawNext && rawNext.startsWith('/') && !rawNext.startsWith('//')
    ? rawNext : null;

  // viste: verifying | expired | form (password, primaria) | otp |
  // sent (codice OTP) | reset | resetSent | signup | signupSent
  const [state, setState] = useState(
    token ? 'verifying'
      : params.get('vista') === 'crea' ? 'signup'
        : params.get('vista') === 'recupero' ? 'reset' : 'form');
  // NL2 — dal ponte «iscritto alla Lettera → crea l'account» l'email
  // arriva gia' scritta: un campo in meno da ridigitare
  const [email, setEmail] = useState(params.get('email') || '');

  // ID-sexies (20/8) — /accedi e /accedi?vista=crea sono la STESSA
  // rotta: cambiando solo la query React non rimonta e la vista
  // restava quella di prima (dal menu: «Crea account» poi «Accedi»
  // lasciava la registrazione a schermo, e viceversa). La vista segue
  // il parametro; la navigazione interna (goTo) resta libera perche'
  // l'effetto scatta solo quando la QUERY cambia davvero.
  const vista = params.get('vista');
  const primoGiro = useRef(true);
  useEffect(() => {
    if (primoGiro.current) { primoGiro.current = false; return; }
    if (token) return;                       // magic link in corso: non toccare
    setState(vista === 'crea' ? 'signup'
      : vista === 'recupero' ? 'reset' : 'form');
    setError(null);
  }, [vista, token]);
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [sending, setSending] = useState(false);
  const [error, setError] = useState(null);
  // AP-L — consenso a Termini + Privacy di Aurya: obbligatorio al signup,
  // timbrato sull'account (aurya_legal) e nell'audit consensi.
  const [signupConsent, setSignupConsent] = useState(false);

  const goTo = (view) => { setState(view); setError(null); };

  useSeoMeta({ title: 'Entra in Aurya', noindex: true });
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
        saveSession(res.data);
        navigate(next || '/account', { replace: true });
      })
      .catch(() => setState('expired'));
  }, [token, navigate]);

  // ID (20/8) — la PORTA UNICA: una chiamata, il server decide il mondo.
  // La password e' il selettore; col legame dei cappelli arrivano
  // entrambi i token (SSO). Le chiavi restano quelle di sempre.
  const passwordLogin = async (e) => {
    e.preventDefault();
    setSending(true); setError(null);
    try {
      const res = await platformApi.post('/auth/entra',
        { email: email.trim(), password });
      const worlds = res.data?.worlds || [];
      let operator = false;
      let welcomePending = false;
      worlds.forEach((w) => {
        if (w.type === 'operator') {
          operator = true;
          welcomePending = !!w.welcome_pending;
          localStorage.setItem('token', w.access_token);
        } else if (w.type === 'client') {
          saveSession(w);
        }
      });
      // operatore → il suo posto di lavoro; cliente → il suo account.
      // ID-octies: al primo accesso l'operatore passa dal benvenuto
      // (una volta sola: dopo compilato o saltato non torna piu'),
      // anche se il ?next= si e' perso verificando su un altro
      // dispositivo. Un ?next= esplicito ha comunque la precedenza.
      const dove = operator
        ? (welcomePending ? '/benvenuto' : '/dashboard')
        : '/account';
      // Un hard navigate: l'AuthContext deve rileggere il token da zero.
      window.location.assign(next || dove);
    } catch (err) {
      const status = err?.response?.status;
      const detail = err?.response?.data?.detail || '';
      if (status === 423) {
        setError(t('landings:account.loginLocked', {
          defaultValue: 'Troppi tentativi: accesso bloccato per qualche minuto. Puoi usare Password dimenticata o accedere senza password.',
        }));
      } else if (status === 403 && (detail === 'EMAIL_NOT_VERIFIED'
          || detail === 'Email not verified')) {
        setError(t('landings:account.loginNotVerified', {
          defaultValue: 'Prima conferma la tua email: controlla la posta (anche lo spam).',
        }));
      } else if (status === 403) {
        setError(t('landings:account.loginDisabled2', {
          defaultValue: 'Questo account non è più attivo.',
        }));
      } else {
        setError(t('landings:account.loginError', {
          defaultValue: 'Email o password non corretti.',
        }));
      }
    } finally {
      setSending(false);
    }
  };

  // NL1-bis — l'alternativa dichiarata: stesso nome/email/consensi, ma
  // si entra dal link. Riusa il magic link (find-or-create col consenso
  // timbrato) e NON tocca la strada con password.
  const submitSignupNoPassword = async () => {
    if (!signupConsent) {
      setError(t('landings:account.needConsent', {
        defaultValue: 'Per creare l’account devi accettare Termini e Privacy.',
      }));
      return;
    }
    if (!email.trim()) {
      setError(t('landings:account.needEmail', {
        defaultValue: 'Scrivi la tua email per ricevere il link di accesso.',
      }));
      return;
    }
    setSending(true); setError(null);
    try {
      await platformApi.post('/platform/auth/magic-link', {
        name: name.trim() || undefined,
        email: email.trim(),
        language: emailLang(),
        accepted_terms: true,
        wants_newsletter: !!wantsLetter,
      });
      setState('signupSent');
    } catch (err) {
      setError(err?.response?.status === 429
        ? t('landings:account.tooFast', { defaultValue: 'Troppi tentativi ravvicinati: aspetta un minuto e riprova.' })
        : t('landings:account.requestError', { defaultValue: 'Qualcosa non ha funzionato. Riprova tra un minuto.' }));
    } finally { setSending(false); }
  };

  // NL3 — i requisiti si spuntano mentre si scrive: il rifiuto non
  // arriva piu' a sorpresa dopo l'invio (era il muro del funnel).
  const pwChecks = [
    ['len', password.length >= 12, t('landings:account.pwLen', { defaultValue: 'almeno 12 caratteri' })],
    ['low', /[a-z]/.test(password), t('landings:account.pwLow', { defaultValue: 'una minuscola' })],
    ['up', /[A-Z]/.test(password), t('landings:account.pwUp', { defaultValue: 'una maiuscola' })],
    ['num', /\d/.test(password), t('landings:account.pwNum', { defaultValue: 'un numero' })],
  ];
  const pwOk = pwChecks.every(([, ok]) => ok);

  // OTP a 6 cifre: la strada senza password (invariata)
  const [code, setCode] = useState('');
  const [verifyingCode, setVerifyingCode] = useState(false);
  const verifyCode = async (e) => {
    e.preventDefault();
    if (code.trim().length !== 6) return;
    setVerifyingCode(true); setError(null);
    try {
      const res = await platformApi.post('/platform/auth/code/verify',
        { email, code: code.trim() });
      saveSession(res.data);
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

  // AP1b — richiesta reset password (risposta sempre neutra)
  const requestReset = async (e) => {
    e.preventDefault();
    setSending(true); setError(null);
    try {
      // ID — dalla porta unica il recupero vale per OGNI mondo in cui
      // l'email esiste (operatore incluso), risposta sempre neutra
      await platformApi.post('/auth/recupero',
        { email: email.trim(), language: emailLang() });
      setState('resetSent');
    } catch {
      setError(t('landings:account.requestError', {
        defaultValue: 'Qualcosa non ha funzionato. Riprova tra un minuto.',
      }));
    } finally {
      setSending(false);
    }
  };

  // AP1b — creazione account Aurya (nome, email, password)
  // NL1-bis (20/8, decisione founder) — la password torna la strada
  // PRINCIPALE della registrazione; «senza password» resta come
  // alternativa esplicita. Perche' allora il funnel non si rompe come
  // prima: i requisiti si spuntano MENTRE si scrive (pwChecks) invece
  // di essere scoperti sbagliando sei volte.
  const [wantsLetter, setWantsLetter] = useState(false);   // NL2, mai preselezionata
  const submitSignup = async (e) => {
    e.preventDefault();
    setSending(true); setError(null);
    try {
      await platformApi.post('/platform/auth/signup', {
        name: name.trim() || undefined,
        email: email.trim(),
        password,
        language: emailLang(),
        // AP-L — la checkbox e' required nel form: qui arriva sempre true
        accepted_terms: !!signupConsent,
        wants_newsletter: !!wantsLetter,
      });
      setState('signupSent');
    } catch (err) {
      const status = err?.response?.status;
      const detail = err?.response?.data?.detail;
      if (status === 429) {
        // NL3 — il rate limit dice cosa fare, non «errore»
        setError(t('landings:account.tooFast', {
          defaultValue: 'Troppi tentativi ravvicinati: aspetta un minuto e riprova.',
        }));
      } else if (status === 409) {
        setError(t('landings:account.signupExists', {
          defaultValue: 'Questa email ha già un account Aurya. Accedi oppure usa Password dimenticata.',
        }));
      } else if (status === 400 && detail) {
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
            <button onClick={() => goTo('otp')}
              className="mt-4 w-full rounded-xl bg-primary text-primary-foreground py-2.5 text-sm font-semibold">
              {t('landings:account.requestNew', { defaultValue: 'Richiedi un nuovo link' })}
            </button>
          </>
        )}

        {state === 'form' && (
          <>
            <KeyRound className="h-8 w-8 text-primary mx-auto" />
            <h1 className="mt-3 text-lg font-bold text-gray-900">
              {t('landings:account.loginTitle', { defaultValue: 'Il tuo account Aurya' })}
            </h1>
            <p className="mt-1 text-sm text-gray-600">
              {t('landings:account.passwordLoginBody', { defaultValue: 'Entra con la tua email e la tua password.' })}
            </p>
            <form onSubmit={passwordLogin} className="mt-4 space-y-3" data-testid="password-login-form">
              <input
                type="email" required value={email} autoComplete="email"
                onChange={e => setEmail(e.target.value)}
                placeholder={t('landings:account.emailPlaceholder', { defaultValue: 'La tua email' })}
                className={inputCls}
              />
              <input
                type="password" required value={password} autoComplete="current-password"
                onChange={e => setPassword(e.target.value)}
                placeholder={t('landings:account.passwordPlaceholder', { defaultValue: 'La tua password' })}
                className={inputCls}
              />
              {error && <p className="text-xs text-red-600">{error}</p>}
              <button type="submit" disabled={sending} className={btnCls} data-testid="password-login-submit">
                {sending
                  ? t('landings:account.entering', { defaultValue: 'Un attimo…' })
                  : t('landings:account.enter', { defaultValue: 'Entra' })}
              </button>
            </form>
            <div className="mt-4 flex flex-col items-center gap-2">
              <button type="button" onClick={() => goTo('otp')} className={linkBtnCls}
                data-testid="login-no-password">
                {t('landings:account.otpLink', { defaultValue: 'Accedi senza password' })}
              </button>
              <button type="button" onClick={() => goTo('reset')} className={linkBtnCls}
                data-testid="login-forgot">
                {t('landings:account.forgotLink', { defaultValue: 'Password dimenticata?' })}
              </button>
            </div>
            <div className="mt-5 border-t border-gray-100 pt-4">
              <button type="button" onClick={() => goTo('signup')}
                className="text-sm font-semibold text-primary hover:underline"
                data-testid="login-to-signup">
                {t('landings:account.signupLink', { defaultValue: 'Crea il tuo account Aurya' })}
              </button>
            </div>
          </>
        )}

        {state === 'otp' && (
          <>
            <Mail className="h-8 w-8 text-primary mx-auto" />
            <h1 className="mt-3 text-lg font-bold text-gray-900">
              {t('landings:account.otpTitle', { defaultValue: 'Accedi senza password' })}
            </h1>
            <p className="mt-1 text-sm text-gray-600">
              {t('landings:account.loginBody', { defaultValue: 'Niente password: ti mandiamo un codice via email, lo digiti qui e sei dentro.' })}
            </p>
            <form onSubmit={requestLink} className="mt-4 space-y-3">
              <input
                type="email" required value={email} autoComplete="email"
                onChange={e => setEmail(e.target.value)}
                placeholder={t('landings:account.emailPlaceholder', { defaultValue: 'La tua email' })}
                className={inputCls}
              />
              {error && <p className="text-xs text-red-600">{error}</p>}
              <button type="submit" disabled={sending} className={btnCls}>
                {sending
                  ? t('landings:account.sending', { defaultValue: 'Invio…' })
                  : t('landings:account.sendCode', { defaultValue: 'Inviami il codice' })}
              </button>
            </form>
            <button type="button" onClick={() => goTo('form')} className={`mt-4 ${linkBtnCls}`}>
              {t('landings:account.backToLogin', { defaultValue: 'Torna al login con password' })}
            </button>
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
              <button type="submit" disabled={verifyingCode || code.length !== 6} className={btnCls}>
                {verifyingCode
                  ? t('landings:account.verifyingCode', { defaultValue: 'Verifico…' })
                  : t('landings:account.enter', { defaultValue: 'Entra' })}
              </button>
            </form>
          </>
        )}

        {state === 'reset' && (
          <>
            <KeyRound className="h-8 w-8 text-primary mx-auto" />
            <h1 className="mt-3 text-lg font-bold text-gray-900">
              {t('landings:account.resetTitle', { defaultValue: 'Password dimenticata' })}
            </h1>
            <p className="mt-1 text-sm text-gray-600">
              {t('landings:account.resetBody', { defaultValue: 'Inserisci la tua email: ti mandiamo un link per impostare una nuova password. Funziona anche se non ne hai mai scelta una.' })}
            </p>
            <form onSubmit={requestReset} className="mt-4 space-y-3" data-testid="reset-request-form">
              <input
                type="email" required value={email} autoComplete="email"
                onChange={e => setEmail(e.target.value)}
                placeholder={t('landings:account.emailPlaceholder', { defaultValue: 'La tua email' })}
                className={inputCls}
              />
              {error && <p className="text-xs text-red-600">{error}</p>}
              <button type="submit" disabled={sending} className={btnCls} data-testid="reset-request-submit">
                {sending
                  ? t('landings:account.sending', { defaultValue: 'Invio…' })
                  : t('landings:account.resetSubmit', { defaultValue: 'Inviami il link' })}
              </button>
            </form>
            <button type="button" onClick={() => goTo('form')} className={`mt-4 ${linkBtnCls}`}>
              {t('landings:account.backToLogin', { defaultValue: 'Torna al login con password' })}
            </button>
          </>
        )}

        {state === 'resetSent' && (
          <>
            <CheckCircle2 className="h-8 w-8 text-primary mx-auto" />
            <h1 className="mt-3 text-lg font-bold text-gray-900">
              {t('landings:account.resetSentTitle', { defaultValue: 'Controlla la tua email' })}
            </h1>
            <p className="mt-2 text-sm text-gray-600" data-testid="reset-sent-body">
              {t('landings:account.resetSentBody', { defaultValue: 'Se l\'email corrisponde a un account Aurya, riceverai un link per impostare la nuova password. Vale 60 minuti.' })}
            </p>
            <button type="button" onClick={() => goTo('form')} className={`mt-4 ${linkBtnCls}`}>
              {t('landings:account.backToLogin', { defaultValue: 'Torna al login con password' })}
            </button>
          </>
        )}

        {state === 'signup' && (
          <>
            <UserPlus className="h-8 w-8 text-primary mx-auto" />
            <h1 className="mt-3 text-lg font-bold text-gray-900">
              {t('landings:account.signupTitle', { defaultValue: 'Crea il tuo account Aurya' })}
            </h1>
            <p className="mt-1 text-sm text-gray-600">
              {t('landings:account.signupBody2', { defaultValue: 'L\u2019account personale, per chi partecipa: prenotazioni, esperienze salvate e guide. Gratuito.' })}
            </p>
            {/* ID-septies (20/8) — lo split sta QUI, prima del form:
                in fondo l'operatore non lo vedeva e compilava la
                registrazione sbagliata. Sul login non c'e' affatto:
                la' la porta e' la stessa per tutti. */}
            <div className="mt-3 flex items-center gap-2.5 rounded-xl border border-primary/40 bg-primary/[0.06] px-3 py-2.5 text-left ring-1 ring-primary/15 shadow-[0_0_14px_-2px_hsl(158_28%_30%/0.35)]"
              data-testid="operator-rescue-link">
              <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-primary/10">
                <Briefcase className="h-4 w-4 text-primary" aria-hidden />
              </span>
              <p className="text-xs leading-snug text-gray-700">
                {t('landings:account.proSplit', { defaultValue: 'Sei un professionista del benessere?' })}{' '}
                <Link to="/entra-nella-rete" data-testid="pro-box-cta"
                  className="font-medium text-primary underline underline-offset-2 hover:no-underline">
                  {t('landings:account.proSplitCta', { defaultValue: 'Apri il tuo spazio' })}
                </Link>
              </p>
            </div>
            <form onSubmit={submitSignup} className="mt-4 space-y-3" data-testid="signup-form">
              <input
                type="text" value={name} autoComplete="name"
                onChange={e => setName(e.target.value)}
                placeholder={t('landings:account.namePlaceholder', { defaultValue: 'Il tuo nome' })}
                className={inputCls}
              />
              <input
                type="email" required value={email} autoComplete="email"
                onChange={e => setEmail(e.target.value)}
                placeholder={t('landings:account.emailPlaceholder', { defaultValue: 'La tua email' })}
                className={inputCls}
              />
              <input
                type="password" required value={password} autoComplete="new-password"
                onChange={e => setPassword(e.target.value)}
                placeholder={t('landings:account.passwordPlaceholder', { defaultValue: 'La tua password' })}
                className={inputCls}
                data-testid="signup-password"
              />
              {/* NL3 — i requisiti si accendono mentre scrivi: prima si
                  scoprivano solo sbagliando (ed era il muro del funnel) */}
              <ul className="text-left text-[11px] space-y-0.5" data-testid="pw-checklist">
                {pwChecks.map(([k, ok, label]) => (
                  <li key={k} className={ok ? 'text-primary' : 'text-gray-400'}>
                    <span aria-hidden>{ok ? '✓' : '○'}</span> {label}
                  </li>
                ))}
                <li className="text-gray-400 pt-0.5">
                  {t('landings:account.pwBreach', { defaultValue: '○ non deve essere una password già comparsa in fughe di dati pubbliche' })}
                </li>
              </ul>
              {/* NL2 — la Lettera e' un consenso A PARTE: si puo'
                  chiedere qui, ma non e' mai preselezionata (GDPR) */}
              <label className="flex items-start gap-2 text-left cursor-pointer select-none">
                <input
                  type="checkbox" checked={wantsLetter}
                  onChange={e => setWantsLetter(e.target.checked)}
                  className="mt-0.5 shrink-0 h-4 w-4 rounded border-gray-300"
                  data-testid="signup-letter"
                />
                <span className="text-xs text-gray-600">
                  {t('landings:account.signupLetter', { defaultValue: 'Iscrivimi anche alla Lettera di Aurya (guide e racconti, quando escono)' })}
                </span>
              </label>
              {/* AP-L — riga consenso: link ai documenti Aurya, spunta
                  obbligatoria (required + gate backend 400) */}
              <label className="flex items-start gap-2 text-left cursor-pointer select-none">
                <input
                  type="checkbox" required checked={signupConsent}
                  onChange={e => setSignupConsent(e.target.checked)}
                  className="mt-0.5 shrink-0 h-4 w-4 rounded border-gray-300"
                  data-testid="signup-consent"
                />
                <span className="text-xs text-gray-600">
                  {t('landings:account.signupConsentPrefix', { defaultValue: 'Accetto i' })}{' '}
                  <a href="/termini" target="_blank" rel="noopener noreferrer" className="underline text-primary hover:no-underline">
                    {t('landings:account.signupConsentTerms', { defaultValue: 'Termini' })}
                  </a>
                  {' '}{t('landings:account.signupConsentAnd', { defaultValue: 'e la' })}{' '}
                  <a href="/privacy" target="_blank" rel="noopener noreferrer" className="underline text-primary hover:no-underline">
                    {t('landings:account.signupConsentPrivacy', { defaultValue: 'Privacy' })}
                  </a>
                  {' '}{t('landings:account.signupConsentSuffix', { defaultValue: 'di Aurya' })}{' *'}
                </span>
              </label>
              {error && <p className="text-xs text-red-600">{error}</p>}
              <button type="submit" disabled={sending || !pwOk} className={btnCls} data-testid="signup-submit">
                {sending
                  ? t('landings:account.sending', { defaultValue: 'Invio…' })
                  : t('landings:account.signupSubmit', { defaultValue: 'Crea account' })}
              </button>
            </form>
            {/* NL1-bis — l'alternativa, dichiarata e secondaria */}
            <button type="button" onClick={submitSignupNoPassword}
              disabled={sending} className={`mt-3 ${linkBtnCls}`}
              data-testid="signup-no-password">
              {t('landings:account.signupNoPw', { defaultValue: 'Preferisci senza password? Ti mandiamo un link per entrare' })}
            </button>
            <button type="button" onClick={() => goTo('form')} className={`mt-4 ${linkBtnCls}`}>
              {t('landings:account.haveAccount', { defaultValue: 'Ho già un account: accedi' })}
            </button>
          </>
        )}

        {state === 'signupSent' && (
          <>
            <CheckCircle2 className="h-8 w-8 text-primary mx-auto" />
            <h1 className="mt-3 text-lg font-bold text-gray-900">
              {t('landings:account.signupSentTitle', { defaultValue: 'Controlla la tua email' })}
            </h1>
            <p className="mt-2 text-sm text-gray-600" data-testid="signup-sent-body">
              {t('landings:account.signupSentBody3', { defaultValue: 'Ti abbiamo scritto: apri l’email e conferma il tuo indirizzo. Da lì entri nel tuo account.' })}
            </p>
            <button type="button" onClick={() => goTo('form')} className={`mt-4 ${linkBtnCls}`}>
              {t('landings:account.backToLogin', { defaultValue: 'Torna al login con password' })}
            </button>
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
