/**
 * AuthPage — combined login + signup with a tab toggle.
 *
 * Phase 5 of the customer area refactor. Logic extracted verbatim
 * from CustomerPortalPages.js (CustomerAuthPage). The two route entry
 * points — /account/login and /account/signup — both render this same
 * component with a different `initialMode` prop. The tab toggle lets
 * the customer switch mode without leaving the page.
 *
 * Why one component (not two separate Login + Signup pages)?
 *   1. Tab UX: switching mode is instant, no route change, no
 *      mount/unmount flicker.
 *   2. Shared chrome: the AuthShell + useStoreInfo + brandColor styling
 *      is identical for both tabs, so colocating avoids duplication.
 *   3. Behavior parity: this is the exact original implementation —
 *      we want zero behavioral drift while we move the file location.
 *
 * Each mode keeps its own state (loginEmail vs signupEmail etc.) so
 * a partial draft is preserved when the customer toggles tab.
 *
 * Auto-redirect: when isCustomerAuthenticated flips true (e.g. after
 * login success or after auto_login signup), useEffect navigates to
 * /account so the customer never sits on a stale form.
 */

import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Eye, EyeOff, Loader2, CheckCircle2 } from 'lucide-react';
import { toast } from 'sonner';
import { useCustomerAuth } from '../../../context/CustomerAuthContext';
import { customerAuthAPI } from '../../../api/customerAuth';
import { Button } from '../../../components/ui/button';
import { Input } from '../../../components/ui/input';
import { Label } from '../../../components/ui/label';
import { Card, CardContent } from '../../../components/ui/card';
import AuthShell, { useStoreInfo } from './AuthShell';


// Validate the `?next=` redirect target. Same-origin internal paths
// only — anything starting with http(s):// or // is rejected so this
// can't be turned into an open-redirect vector by a forged email link.
function _safeNextPath(raw) {
  if (!raw) return null;
  let decoded;
  try { decoded = decodeURIComponent(raw); } catch { return null; }
  // Must start with `/` and not with `//` (which browsers treat as
  // protocol-relative and would jump origin).
  if (!decoded.startsWith('/') || decoded.startsWith('//')) return null;
  // Must not embed a scheme. `decoded.indexOf(':')` could be a port or
  // a colon inside a query string — but a leading-slash path with a
  // colon before the first `?` is suspicious enough to reject.
  const beforeQuery = decoded.split('?')[0];
  if (beforeQuery.includes(':')) return null;
  return decoded;
}


export default function AuthPage({ initialMode = 'login' }) {
  const [searchParams] = useSearchParams();
  // store slug source priority: query param > localStorage (set by
  // CustomerProtectedRoute on first redirect) > empty (handled below).
  const slug = searchParams.get('store') || localStorage.getItem('customer_store_slug') || '';
  // Where the customer was trying to go before being bounced through
  // login. Set by CustomerProtectedRoute, present on email-driven
  // logins (the email link points at /account/orders/<id> which the
  // guard can't render until the JWT is in localStorage). Sanitised
  // so a malicious ?next=https://attacker.com cannot redirect off-site.
  const nextPath = _safeNextPath(searchParams.get('next'));
  const { storeInfo, orgName, storefrontLanguages } = useStoreInfo(slug);
  const [mode, setMode] = useState(initialMode);
  const navigate = useNavigate();
  const { t, i18n } = useTranslation('customer_auth');
  const { login, signup, isCustomerAuthenticated } = useCustomerAuth();

  // Login state
  const [loginEmail, setLoginEmail] = useState('');
  const [loginPassword, setLoginPassword] = useState('');
  const [loginShowPw, setLoginShowPw] = useState(false);
  const [loginLoading, setLoginLoading] = useState(false);
  const [emailNotVerified, setEmailNotVerified] = useState(false);
  // Onda 29 — anti-bruteforce per-account lockout state.
  // `lockoutUntilIso` is the ISO UTC timestamp returned by the backend
  // (HTTP 423 detail.unlock_at). When set, the form is disabled and a
  // live countdown banner is rendered. `lockoutSecondsLeft` ticks every
  // second so the UI shows real-time minutes remaining.
  const [lockoutUntilIso, setLockoutUntilIso] = useState(null);
  const [lockoutSecondsLeft, setLockoutSecondsLeft] = useState(0);

  // Signup state
  const [signupName, setSignupName] = useState('');
  const [signupEmail, setSignupEmail] = useState('');
  const [signupPassword, setSignupPassword] = useState('');
  const [signupShowPw, setSignupShowPw] = useState(false);
  const [signupLoading, setSignupLoading] = useState(false);
  const [verificationSent, setVerificationSent] = useState(false);
  // Track O Step 5.1 — honeypot anti-bot field. Hidden via CSS in the
  // form below; humans never see it, naive bots fill it.
  // Backend (core/honeypot.py) returns uniform 202 on trigger.
  const [signupWebsite, setSignupWebsite] = useState('');
  // Wave GDPR-Commerce CG-4 — explicit consent at signup.
  // Both terms + privacy are mandatory; marketing is optional.
  // The links open the merchant's own /s/:slug/{privacy,terms} pages
  // (CG-2) in a new tab so the customer can actually read what they're
  // accepting before checking the box.
  const [acceptedTerms, setAcceptedTerms] = useState(false);
  const [acceptedPrivacy, setAcceptedPrivacy] = useState(false);
  const [acceptedMarketing, setAcceptedMarketing] = useState(false);

  // Auto-redirect when already authenticated. Hits on first paint if
  // localStorage already had a valid customer token, AND on the
  // moment-after-login transition for new sessions.
  //
  // Destination priority:
  //   1. `?next=<path>` — set by CustomerProtectedRoute when the
  //      customer was trying to reach a deep page (e.g. /account/
  //      orders/<id> from the order-confirmed email). The path
  //      already carries its own query string if any; we don't try
  //      to merge `?store=` into it because the deep page is also
  //      gated by the guard, which will pick the slug back up from
  //      localStorage (just set by login()).
  //   2. /account/orders + ?store=<slug> — the historical default,
  //      lands on the orders list. Used when no `next` was preserved.
  useEffect(() => {
    if (isCustomerAuthenticated) {
      const dest = nextPath
        ? nextPath
        : `/account/orders${slug ? `?store=${slug}` : ''}`;
      navigate(dest, { replace: true });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isCustomerAuthenticated, navigate]);

  // Sync mode with route (when navigating directly to /login or /signup)
  useEffect(() => { setMode(initialMode); }, [initialMode]);

  const brandColor = storeInfo?.brand_color;

  // Password rules — mirrored from the backend validator. We re-validate
  // server-side so a tampered request can't bypass the gate.
  const passwordChecks = {
    length: signupPassword.length >= 12,
    lowercase: /[a-z]/.test(signupPassword),
    uppercase: /[A-Z]/.test(signupPassword),
    digit: /\d/.test(signupPassword),
  };
  const passwordValid = Object.values(passwordChecks).every(Boolean);

  // Onda 29 — live countdown for the per-account lockout banner.
  // Recomputes seconds-left every 1s while a lockout is active.
  // When the timer hits zero we clear the lockout state automatically
  // so the user can retry without refreshing the page.
  React.useEffect(() => {
    if (!lockoutUntilIso) {
      setLockoutSecondsLeft(0);
      return undefined;
    }
    const tick = () => {
      const target = new Date(lockoutUntilIso).getTime();
      const now = Date.now();
      const remaining = Math.max(0, Math.ceil((target - now) / 1000));
      setLockoutSecondsLeft(remaining);
      if (remaining === 0) {
        setLockoutUntilIso(null);
      }
    };
    tick(); // immediate
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [lockoutUntilIso]);

  const handleLogin = async (e) => {
    e.preventDefault();
    if (!slug) { toast.error(t('customer_auth:errors.storeUnknown')); return; }
    setLoginLoading(true);
    setEmailNotVerified(false);
    try {
      await login(slug, loginEmail, loginPassword);
      navigate(`/account/orders?store=${slug}`);
    } catch (err) {
      const detail = err?.response?.data?.detail;
      const status = err?.response?.status;
      if (detail?.code === 'EMAIL_NOT_VERIFIED') {
        setEmailNotVerified(true);
      } else if (status === 423 || detail?.code === 'ACCOUNT_LOCKED') {
        // Onda 29 — backend signalled per-account lockout.
        // detail.unlock_at is an ISO UTC timestamp; the live-countdown
        // banner (rendered above the form) reads it via lockoutUntilIso.
        const unlockAt = detail?.unlock_at;
        if (unlockAt) {
          setLockoutUntilIso(unlockAt);
        } else {
          // Defensive: backend should always include unlock_at when
          // returning 423/ACCOUNT_LOCKED, but if it doesn't, fall back
          // to a generic locked-without-time message.
          toast.error(t('customer_auth:errors.accountLockedGeneric'));
        }
      } else {
        toast.error(typeof detail === 'string' ? detail : t('customer_auth:errors.invalidCredentials'));
      }
    } finally { setLoginLoading(false); }
  };

  const handleResend = async () => {
    try {
      await customerAuthAPI.resendVerification(slug, loginEmail);
      toast.success(t('customer_auth:errors.verificationEmailSent'));
    } catch { toast.error(t('customer_auth:errors.emailSendFailed')); }
  };

  const handleSignup = async (e) => {
    e.preventDefault();
    if (!passwordValid || !slug) {
      if (!slug) toast.error(t('customer_auth:errors.storeUnknown'));
      return;
    }
    // Wave GDPR-Commerce CG-4: client-side guard so the user gets an
    // immediate inline error instead of a server 400 round-trip. The
    // service ALSO enforces this server-side — these are belt-and-
    // braces, not a substitute for the server check.
    if (!acceptedTerms || !acceptedPrivacy) {
      toast.error(t('customer_auth:signup.consent_required'));
      return;
    }
    setSignupLoading(true);
    try {
      // Send the currently active locale as the customer's preference.
      // The visitor sees the storefront / auth flow in language X,
      // signs up — backend creates the account with locale=X, so all
      // future emails (verify, welcome, order_confirmed) and post-login
      // UI default to that same language. Closes the i18n loop.
      const result = await signup({
        slug,
        email: signupEmail,
        name: signupName,
        password: signupPassword,
        locale: (i18n.language || 'it').split('-')[0],
        // CG-4: explicit consent flags. The server records the
        // version + locale the customer saw based on the store's
        // currently published bundle.
        accepted_terms: acceptedTerms,
        accepted_privacy: acceptedPrivacy,
        accepted_marketing: acceptedMarketing,
        // Track O Step 5.1 — honeypot anti-bot field (hidden in form).
        // Humans submit empty string; bots that fill all inputs trigger
        // backend detection (core/honeypot.py).
        website: signupWebsite,
      });
      if (result === 'verification_required') {
        // Backend chose the legacy double-opt-in flow — show success
        // screen and let the customer click the email link.
        setVerificationSent(true);
      } else {
        // auto_login path: token is already in localStorage, so the
        // navigate will land inside the protected area. Land on the
        // orders list directly (the dashboard /account was removed).
        navigate(`/account/orders${slug ? `?store=${slug}` : ''}`);
      }
    } catch (err) {
      const detail = err?.response?.data?.detail;
      toast.error(typeof detail === 'string' ? detail : t('customer_auth:errors.signupGeneric'));
    } finally { setSignupLoading(false); }
  };

  if (verificationSent) {
    return (
      <AuthShell storeInfo={storeInfo} orgName={orgName} slug={slug} storefrontLanguages={storefrontLanguages}>
        <Card>
          <CardContent className="pt-6 text-center space-y-3">
            <CheckCircle2 className="h-10 w-10 text-emerald-500 mx-auto" />
            <h2 className="text-lg font-semibold">{t('customer_auth:verificationSent.title')}</h2>
            <p className="text-sm text-muted-foreground"
               dangerouslySetInnerHTML={{ __html: t('customer_auth:verificationSent.body', { email: signupEmail }) }} />
            <button
              onClick={() => { setVerificationSent(false); setMode('login'); }}
              className="text-sm text-primary hover:underline mt-2"
            >
              {t('customer_auth:verificationSent.goLogin')}
            </button>
          </CardContent>
        </Card>
      </AuthShell>
    );
  }

  return (
    <AuthShell storeInfo={storeInfo} orgName={orgName} slug={slug} storefrontLanguages={storefrontLanguages}>
      <Card>
        {/* Tab toggle — mode switching without route change */}
        <div className="flex border-b">
          {[
            { key: 'login', labelKey: 'tabs.login' },
            { key: 'signup', labelKey: 'tabs.signup' },
          ].map(({ key, labelKey }) => (
            <button
              key={key}
              onClick={() => setMode(key)}
              className={`flex-1 py-3 text-sm font-medium transition-colors ${
                mode === key
                  ? 'border-b-2 text-foreground'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
              style={mode === key && brandColor ? { borderBottomColor: brandColor, color: brandColor } : undefined}
            >
              {t(`customer_auth:${labelKey}`)}
            </button>
          ))}
        </div>

        <CardContent className="pt-5">
          {mode === 'login' ? (
            /* ── Login form ────────────────────────────────────────── */
            <>
              {emailNotVerified && (
                <div className="mb-4 p-3 bg-amber-50 border border-amber-200 rounded-md text-sm">
                  <p className="text-amber-700">{t('customer_auth:login.verifyFirst')}</p>
                  <Button variant="link" size="sm" className="p-0 h-auto text-amber-700" onClick={handleResend}>
                    {t('customer_auth:login.resendVerification')}
                  </Button>
                </div>
              )}
              {/* Onda 29 — Anti-bruteforce lockout banner with live countdown.
                  Renders only while lockoutUntilIso is set; the useEffect above
                  clears it automatically when seconds-left hits zero. */}
              {lockoutUntilIso && lockoutSecondsLeft > 0 && (
                <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md text-sm" role="alert">
                  <p className="font-semibold text-red-800">
                    {t('customer_auth:login.accountLockedTitle')}
                  </p>
                  <p className="text-red-700 mt-1">
                    {t('customer_auth:login.accountLockedCountdown', {
                      minutes: Math.ceil(lockoutSecondsLeft / 60),
                    })}
                  </p>
                  <p className="text-red-700 mt-2 text-xs">
                    {t('customer_auth:login.accountLockedForgotHint')}{' '}
                    <Link
                      to={`/account/forgot-password${slug ? `?store=${slug}` : ''}`}
                      className="underline font-medium"
                    >
                      {t('customer_auth:login.forgotPassword')}
                    </Link>
                  </p>
                </div>
              )}
              <form onSubmit={handleLogin} className="space-y-4">
                <div>
                  <Label>{t('customer_auth:fields.email')}</Label>
                  <Input type="email" value={loginEmail} onChange={e => setLoginEmail(e.target.value)} required />
                </div>
                <div>
                  <Label>{t('customer_auth:fields.password')}</Label>
                  <div className="relative">
                    <Input
                      type={loginShowPw ? 'text' : 'password'}
                      value={loginPassword}
                      onChange={e => setLoginPassword(e.target.value)}
                      required
                    />
                    <button
                      type="button"
                      onClick={() => setLoginShowPw(!loginShowPw)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground"
                    >
                      {loginShowPw ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  </div>
                </div>
                <Button
                  type="submit"
                  className="w-full"
                  disabled={loginLoading || (lockoutUntilIso && lockoutSecondsLeft > 0)}
                  style={brandColor ? { backgroundColor: brandColor, color: storeInfo?.brand_color_text || '#fff' } : undefined}
                >
                  {loginLoading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
                  {t('customer_auth:login.submit')}
                </Button>
              </form>
              <div className="mt-3 text-center">
                <Link
                  to={`/account/forgot-password${slug ? `?store=${slug}` : ''}`}
                  className="text-xs text-muted-foreground hover:underline"
                >
                  {t('customer_auth:login.forgotPassword')}
                </Link>
              </div>
            </>
          ) : (
            /* ── Signup form ───────────────────────────────────────── */
            <form onSubmit={handleSignup} className="space-y-4">
              {/*
                Track O Step 5.1 — Honeypot anti-bot field.
                Hidden via CSS (off-screen, zero size, no tab focus,
                aria-hidden). Humans never see it; bots filling all
                inputs trigger backend honeypot detection.
                NOT type="hidden" — bots skip those.
                See backend/core/honeypot.py for full threat model.
              */}
              <input
                type="text"
                name="website"
                value={signupWebsite}
                onChange={e => setSignupWebsite(e.target.value)}
                tabIndex={-1}
                autoComplete="off"
                aria-hidden="true"
                style={{
                  position: 'absolute',
                  left: '-9999px',
                  top: 'auto',
                  width: '1px',
                  height: '1px',
                  overflow: 'hidden',
                  opacity: 0,
                }}
              />
              <div>
                <Label>{t('customer_auth:fields.name')}</Label>
                <Input value={signupName} onChange={e => setSignupName(e.target.value)} required />
              </div>
              <div>
                <Label>{t('customer_auth:fields.email')}</Label>
                <Input type="email" value={signupEmail} onChange={e => setSignupEmail(e.target.value)} required />
              </div>
              <div>
                <Label>{t('customer_auth:fields.password')}</Label>
                <div className="relative">
                  <Input
                    type={signupShowPw ? 'text' : 'password'}
                    value={signupPassword}
                    onChange={e => setSignupPassword(e.target.value)}
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setSignupShowPw(!signupShowPw)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground"
                  >
                    {signupShowPw ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
                {signupPassword.length > 0 && (
                  <div className="mt-2 space-y-1 text-xs">
                    {[
                      ['length', 'passwordChecks.minLength'],
                      ['lowercase', 'passwordChecks.lowercase'],
                      ['uppercase', 'passwordChecks.uppercase'],
                      ['digit', 'passwordChecks.digit'],
                    ].map(([key, labelKey]) => (
                      <p key={key} className={passwordChecks[key] ? 'text-emerald-600' : 'text-muted-foreground'}>
                        {passwordChecks[key] ? '\u2713' : '\u2022'} {t(`customer_auth:${labelKey}`)}
                      </p>
                    ))}
                  </div>
                )}
              </div>
              {/* Wave GDPR-Commerce CG-4 — explicit consent block.
                  Terms + privacy required; marketing optional. The
                  links open the MERCHANT's docs (not afianco's) in a
                  new tab so the visitor can read before accepting. */}
              <div className="space-y-2 pt-1">
                <label className="flex items-start gap-2 text-sm cursor-pointer">
                  <input
                    type="checkbox"
                    checked={acceptedTerms}
                    onChange={(e) => setAcceptedTerms(e.target.checked)}
                    className="mt-0.5 h-4 w-4 accent-primary cursor-pointer"
                    required
                  />
                  <span>
                    {t('customer_auth:signup.accept_terms_prefix', 'Accetto i')}{' '}
                    <a
                      href={`/s/${encodeURIComponent(slug || '')}/terms`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-primary underline hover:text-primary/80"
                    >
                      {t('customer_auth:signup.terms_link', 'Termini e Condizioni')}
                    </a>{' '}
                    *
                  </span>
                </label>
                <label className="flex items-start gap-2 text-sm cursor-pointer">
                  <input
                    type="checkbox"
                    checked={acceptedPrivacy}
                    onChange={(e) => setAcceptedPrivacy(e.target.checked)}
                    className="mt-0.5 h-4 w-4 accent-primary cursor-pointer"
                    required
                  />
                  <span>
                    {t('customer_auth:signup.accept_privacy_prefix', 'Ho letto l\u2019')}
                    <a
                      href={`/s/${encodeURIComponent(slug || '')}/privacy`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-primary underline hover:text-primary/80"
                    >
                      {t('customer_auth:signup.privacy_link', 'Informativa sulla Privacy')}
                    </a>{' '}
                    *
                  </span>
                </label>
                <label className="flex items-start gap-2 text-sm cursor-pointer">
                  <input
                    type="checkbox"
                    checked={acceptedMarketing}
                    onChange={(e) => setAcceptedMarketing(e.target.checked)}
                    className="mt-0.5 h-4 w-4 accent-primary cursor-pointer"
                  />
                  <span className="text-muted-foreground">
                    {t('customer_auth:signup.accept_marketing', 'Desidero ricevere comunicazioni promozionali (opzionale, revocabile in qualsiasi momento)')}
                  </span>
                </label>
              </div>

              <Button
                type="submit"
                className="w-full"
                disabled={signupLoading || !passwordValid || !acceptedTerms || !acceptedPrivacy}
                style={brandColor ? { backgroundColor: brandColor, color: storeInfo?.brand_color_text || '#fff' } : undefined}
              >
                {signupLoading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
                {t('customer_auth:signup.submit')}
              </Button>
            </form>
          )}
        </CardContent>
      </Card>
    </AuthShell>
  );
}
