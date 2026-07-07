import React, { useState, useEffect } from 'react';
import { useNavigate, Link, useSearchParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import i18n from '../i18n';
import { useAuth } from '../context/AuthContext';
import { authAPI } from '../api';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { ArrowRight, Eye, EyeOff, Mail, KeyRound, CheckCircle2, XCircle, Loader2 } from 'lucide-react';
// 2026-05-22 — new brand identity. Replaces the legacy
// <TrendingUp /> + "AFianco" wordmark combo on every auth screen.
import { BrandLogo } from '../components/BrandLogo';
import { toast } from 'sonner';

const SUPPORTED_LANGS = ['it', 'en', 'fr', 'de'];
const LANG_LABELS = { it: 'IT', en: 'EN', fr: 'FR', de: 'DE' };

const LanguageSwitcher = () => {
  const { i18n: i18nInstance } = useTranslation();
  const handleChange = (lang) => {
    i18nInstance.changeLanguage(lang);
    localStorage.setItem('i18n_lang', lang);
  };
  return (
    <div className="flex gap-1">
      {SUPPORTED_LANGS.map((lang) => (
        <button
          key={lang}
          onClick={() => handleChange(lang)}
          className={`px-2 py-1 text-xs font-medium rounded transition-colors ${
            i18nInstance.language === lang
              ? 'bg-primary text-primary-foreground'
              : 'text-muted-foreground hover:text-foreground hover:bg-muted'
          }`}
        >
          {LANG_LABELS[lang]}
        </button>
      ))}
    </div>
  );
};

const useLangParam = () => {
  const [searchParams] = useSearchParams();
  useEffect(() => {
    const lang = searchParams.get('lang');
    if (lang && SUPPORTED_LANGS.includes(lang)) {
      i18n.changeLanguage(lang);
      localStorage.setItem('i18n_lang', lang);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps
};

export const LoginPage = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [registrationMode, setRegistrationMode] = useState('open');
  const [emailNotVerified, setEmailNotVerified] = useState(false);
  const [resendingVerification, setResendingVerification] = useState(false);
  const [accountDeactivated, setAccountDeactivated] = useState(null); // {deactivated_at, is_org_admin}
  const [reactivating, setReactivating] = useState(false);
  // Onda 30 — anti-bruteforce per-account lockout state.
  // `lockoutUntilIso` is the ISO UTC timestamp from the backend
  // (HTTP 423 detail.unlock_at). When set, a red banner with a live
  // 1Hz countdown is rendered above the form and the submit button
  // is disabled until the timer expires.
  const [lockoutUntilIso, setLockoutUntilIso] = useState(null);
  const [lockoutSecondsLeft, setLockoutSecondsLeft] = useState(0);
  const { login } = useAuth();
  const navigate = useNavigate();
  const { t } = useTranslation('auth');
  useLangParam();

  useEffect(() => {
    authAPI.getRegistrationMode()
      .then((data) => setRegistrationMode(data.registration_mode))
      .catch(() => {}); // fallback: show signup link (open)
  }, []);

  // Onda 30 — live countdown for the per-account lockout banner.
  // Recomputes seconds-left every 1s while a lockout is active.
  // When the timer hits zero we clear the lockout state automatically
  // so the user can retry without refreshing the page. Mirror of the
  // customer-side useEffect in features/customer-portal/auth/AuthPage.jsx.
  useEffect(() => {
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
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [lockoutUntilIso]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setEmailNotVerified(false);

    try {
      const userData = await login(email, password);
      if (userData?.must_change_password) {
        toast.warning(t('login.security_password'));
        navigate('/settings');
      } else {
        toast.success(t('login.welcome_back'));
        navigate('/dashboard');
      }
    } catch (error) {
      const data = error.response?.data || {};
      const detail = data.detail || '';
      const status = error.response?.status;
      if (detail === 'Account deactivated') {
        setAccountDeactivated({
          deactivated_at: data.deactivated_at,
          is_org_admin: data.is_org_admin,
        });
      } else if (detail === 'Email not verified') {
        setEmailNotVerified(true);
      } else if (status === 423 || (typeof detail === 'object' && detail?.code === 'ACCOUNT_LOCKED')) {
        // Onda 30 — backend signalled per-account lockout.
        // detail is an OBJECT here ({code, message, unlock_at}),
        // not the string variant handled in the branches above.
        const detailObj = typeof detail === 'object' ? detail : {};
        const unlockAt = detailObj.unlock_at;
        if (unlockAt) {
          setLockoutUntilIso(unlockAt);
        } else {
          toast.error(t('login.account_locked_generic'));
        }
      } else {
        const msg = typeof detail === 'string' ? detail : '';
        toast.error(msg || t('login.error'));
      }
    } finally {
      setLoading(false);
    }
  };

  const handleReactivate = async () => {
    setReactivating(true);
    try {
      const response = await authAPI.reactivateAccount(email, password);
      const { access_token, user: userData } = response.data;
      if (access_token) {
        localStorage.setItem('token', access_token);
        toast.success(t('login.reactivate_success', 'Account riattivato con successo!'));
        window.location.href = '/dashboard'; // full reload to reset auth state
      } else {
        toast.success(response.data?.message || t('login.reactivate_success', 'Account riattivato!'));
        setAccountDeactivated(null);
      }
    } catch (error) {
      const detail = error.response?.data?.detail || '';
      if (error.response?.status === 410) {
        toast.error(t('login.account_deleted', 'Questo account e\' stato eliminato definitivamente'));
      } else {
        toast.error(detail || t('login.reactivate_error'));
      }
    } finally {
      setReactivating(false);
    }
  };

  const handleResendVerification = async () => {
    setResendingVerification(true);
    try {
      await authAPI.resendVerification(email);
      toast.success(t('login.resend_verification_sent', 'Email di verifica inviata!'));
    } catch {
      toast.error(t('login.resend_error'));
    } finally {
      setResendingVerification(false);
    }
  };

  return (
    <div className="min-h-screen flex">
      {/* Left side - Form */}
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="w-full max-w-md">
          <div className="flex items-center justify-between mb-8">
            <BrandLogo />
            <LanguageSwitcher />
          </div>

          <Card className="border border-border">
            <CardHeader className="space-y-1">
              <CardTitle className="font-heading text-2xl">{t('login.title')}</CardTitle>
              <CardDescription>
                {t('login.description')}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="email">{t('login.email')}</Label>
                  <Input
                    id="email"
                    type="email"
                    placeholder={t('placeholders.email_login')}
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    data-testid="login-email-input"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="password">{t('login.password')}</Label>
                  <div className="relative">
                    <Input
                      id="password"
                      type={showPassword ? 'text' : 'password'}
                      placeholder=""
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      required
                      data-testid="login-password-input"
                    />
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      className="absolute right-0 top-0 h-full px-3"
                      onClick={() => setShowPassword(!showPassword)}
                    >
                      {showPassword ? (
                        <EyeOff className="h-4 w-4 text-muted-foreground" />
                      ) : (
                        <Eye className="h-4 w-4 text-muted-foreground" />
                      )}
                    </Button>
                  </div>
                </div>
                <Button
                  type="submit"
                  className="w-full"
                  disabled={loading || (lockoutUntilIso && lockoutSecondsLeft > 0)}
                  data-testid="login-submit-btn"
                >
                  {loading ? t('login.loading') : t('login.submit')}
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </form>

              {/* Onda 30 — anti-bruteforce lockout banner with live countdown.
                  Renders only while lockoutUntilIso is set; the useEffect
                  above clears it automatically when seconds-left hits zero. */}
              {lockoutUntilIso && lockoutSecondsLeft > 0 && (
                <div className="mt-4 rounded-md bg-red-50 border border-red-200 p-4 text-sm" role="alert">
                  <p className="font-semibold text-red-800">
                    {t('login.account_locked_title', 'Account temporaneamente bloccato')}
                  </p>
                  <p className="text-red-700 mt-1">
                    {t('login.account_locked_countdown', 'Per troppi tentativi falliti, riprova fra {{minutes}} minuti.', {
                      minutes: Math.ceil(lockoutSecondsLeft / 60),
                    })}
                  </p>
                  <p className="text-red-700 mt-2 text-xs">
                    {t('login.account_locked_forgot_hint', 'Oppure, se hai dimenticato la password,')}{' '}
                    <Link
                      to="/forgot-password"
                      className="underline font-medium"
                    >
                      {t('login.forgot_password', 'Password dimenticata?')}
                    </Link>
                  </p>
                </div>
              )}

              {emailNotVerified && (
                <div className="mt-4 space-y-3">
                  <div className="rounded-md bg-amber-50 border border-amber-200 p-4 text-sm text-amber-800">
                    <p className="font-medium">{t('login.email_not_verified', 'Email non verificata. Controlla la tua casella email.')}</p>
                  </div>
                  <Button
                    variant="outline"
                    className="w-full"
                    onClick={handleResendVerification}
                    disabled={resendingVerification || !email}
                  >
                    <Mail className="h-4 w-4 mr-2" />
                    {resendingVerification
                      ? t('forgot_password.loading')
                      : t('login.resend_verification', 'Reinvia email di verifica')}
                  </Button>
                </div>
              )}

              {accountDeactivated && (
                <div className="mt-4 space-y-3">
                  <div className="rounded-md bg-red-50 border border-red-200 p-4 text-sm text-red-800 space-y-1">
                    <p className="font-medium">{t('login.account_deactivated', 'Il tuo account e\' stato disattivato')}</p>
                    {accountDeactivated.is_org_admin ? (
                      <>
                        {accountDeactivated.deactivated_at && (() => {
                          const deactivatedDate = new Date(accountDeactivated.deactivated_at);
                          const deadlineDate = new Date(deactivatedDate.getTime() + 30 * 24 * 60 * 60 * 1000);
                          const daysLeft = Math.max(0, Math.ceil((deadlineDate - Date.now()) / (24 * 60 * 60 * 1000)));
                          return <p>{t('login.reactivate_prompt', 'Hai ancora {{days}} giorni per riattivarlo').replace('{{days}}', daysLeft)}</p>;
                        })()}
                      </>
                    ) : (
                      <p>{t('login.account_deactivated_member', 'L\'account della tua organizzazione e\' stato disattivato dall\'amministratore. Contatta l\'admin per la riattivazione.')}</p>
                    )}
                  </div>
                  {accountDeactivated.is_org_admin && (
                    <Button
                      variant="outline"
                      className="w-full border-red-200 text-red-700 hover:bg-red-50"
                      onClick={handleReactivate}
                      disabled={reactivating || !email || !password}
                    >
                      {reactivating ? t('login.loading') : t('login.reactivate_button', 'Riattiva account')}
                    </Button>
                  )}
                </div>
              )}

              <div className="mt-4 text-center text-sm">
                <Link
                  to="/forgot-password"
                  className="text-muted-foreground hover:text-primary hover:underline"
                  data-testid="forgot-password-link"
                >
                  {t('login.forgot_password')}
                </Link>
              </div>

              <div className="mt-4 text-center text-sm">
                <span className="text-muted-foreground">
                  {registrationMode === 'invite_only' ? t('login.want_access') : t('login.no_account')}{' '}
                </span>
                <Link
                  to="/signup"
                  className="font-medium text-primary hover:underline"
                  data-testid="signup-link"
                >
                  {registrationMode === 'invite_only' ? t('login.request_access_link') : t('login.signup_link')}
                </Link>
              </div>

            </CardContent>
          </Card>
        </div>
      </div>

      {/* Right side - Visual */}
      <div className="hidden lg:flex flex-1 items-center justify-center bg-muted/50 p-8">
        <div className="max-w-lg text-center">
          <h2 className="font-heading text-3xl font-bold tracking-tight mb-4">
            {t('marketing.tagline')}
          </h2>
          <p className="text-lg text-muted-foreground">
            {t('marketing.description')}
          </p>
        </div>
      </div>
    </div>
  );
};

const validatePassword = (pw, t) => {
  const errors = [];
  if (pw.length < 12) errors.push(t('validation.password_min_length'));
  if (!/[a-z]/.test(pw)) errors.push(t('validation.password_lowercase'));
  if (!/[A-Z]/.test(pw)) errors.push(t('validation.password_uppercase'));
  if (!/\d/.test(pw)) errors.push(t('validation.password_digit'));
  return errors.length ? errors.join(', ') + '.' : '';
};

const extractApiError = (error, fallback) => {
  const detail = error.response?.data?.detail;
  if (Array.isArray(detail)) return detail.map((d) => d.msg).join('; ');
  if (typeof detail === 'string') return detail;
  // v5.8 / Onda 9.Z Step C — backend now returns structured detail dict
  // for 409 conflicts (e.g. {code:'EMAIL_ALREADY_REGISTERED', message,
  // field}). Use .message verbatim — it's already localized in IT and
  // can be replaced via i18n key by the caller if a locale-specific
  // override is available.
  if (detail && typeof detail === 'object') {
    return detail.message || fallback;
  }
  return fallback;
};

// v5.8 / Onda 9.Z Step C — code-aware error rendering for signup.
// Returns the localized message for known error codes, falls back to
// the backend-provided `message` (already in Italian) for unknowns.
const localizeSignupError = (error, t, fallback) => {
  const detail = error.response?.data?.detail;
  if (detail && typeof detail === 'object' && detail.code) {
    const i18nKey = `signup.error_codes.${detail.code}`;
    const localized = t(i18nKey, { defaultValue: '__MISSING__' });
    if (localized !== '__MISSING__') return localized;
    if (detail.message) return detail.message;
  }
  return extractApiError(error, fallback);
};

export const SignupPage = () => {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [organizationName, setOrganizationName] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [passwordError, setPasswordError] = useState('');
  // Track O Step 5.1 — honeypot field state. Hidden via CSS in the
  // form below; humans never see it, naive bots fill it. Backend
  // (core/honeypot.py) returns uniform 202 success on trigger.
  const [website, setWebsite] = useState('');
  const { signup } = useAuth();
  const navigate = useNavigate();
  const { t } = useTranslation('auth');
  useLangParam();
  const [searchParams] = useSearchParams();

  // ── Controlled Access (v6.0) ──────────────────────────────────────────
  const [registrationMode, setRegistrationMode] = useState(null); // null = loading
  const [inviteToken] = useState(searchParams.get('invite') || '');
  const [inviteValid, setInviteValid] = useState(null); // null = loading, true/false
  const [inviteEmail, setInviteEmail] = useState('');
  const [verificationRequired, setVerificationRequired] = useState(false);
  const [acceptedTerms, setAcceptedTerms] = useState(false);
  // AN4 — consenso granulare: privacy e termini sono accettazioni
  // DISTINTE (GDPR art. 7); il payload accepted_terms parte solo
  // quando entrambe sono vere (bundle versionato v2.0)
  const [acceptedPrivacy, setAcceptedPrivacy] = useState(false);
  // ── Invite request form ──────────────────────────────────────────────
  const [showRequestForm, setShowRequestForm] = useState(false);
  const [requestName, setRequestName] = useState('');
  const [requestEmail, setRequestEmail] = useState('');
  const [requestBusiness, setRequestBusiness] = useState('');
  const [requestLoading, setRequestLoading] = useState(false);
  const [requestSent, setRequestSent] = useState(false);

  useEffect(() => {
    // 1. Check registration mode
    authAPI.getRegistrationMode()
      .then((data) => setRegistrationMode(data.registration_mode))
      .catch(() => setRegistrationMode('open'));

    // 2. If invite token in URL, validate it
    if (inviteToken) {
      authAPI.validateInvite(inviteToken)
        .then((data) => {
          setInviteValid(data.valid);
          if (data.valid && data.email) {
            setInviteEmail(data.email);
            setEmail(data.email);
          }
        })
        .catch(() => setInviteValid(false));
    }
  }, [inviteToken]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    const pwError = validatePassword(password, t);
    if (pwError) {
      setPasswordError(pwError);
      return;
    }
    setPasswordError('');
    setLoading(true);

    try {
      const result = await signup(email, password, name, organizationName, inviteToken || undefined, acceptedTerms && acceptedPrivacy, i18n.language, website);
      if (result === 'verification_required') {
        setVerificationRequired(true);
        return;
      }
      toast.success(t('signup.success'));
      navigate('/dashboard');
    } catch (error) {
      // Check if backend returned 202 (verification required)
      if (error.response?.status === 202 || error.response?.data?.status === 'verification_required') {
        setVerificationRequired(true);
        return;
      }
      // v5.8 / Onda 9.Z Step C — route via code-aware localizer so
      // 409 conflicts (EMAIL_ALREADY_REGISTERED, REGISTRATION_CONFLICT)
      // get the right copy in the user's current locale.
      toast.error(localizeSignupError(error, t, t('signup.error')));
    } finally {
      setLoading(false);
    }
  };

  // Still loading registration mode
  if (registrationMode === null) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-pulse text-muted-foreground">{t('signup.page_loading')}</div>
      </div>
    );
  }

  // v6.0: Show verification required screen after successful signup
  if (verificationRequired) {
    return (
      <div className="min-h-screen flex">
        <div className="flex-1 flex items-center justify-center p-8">
          <div className="w-full max-w-md">
            <div className="flex items-center justify-between mb-8">
              <BrandLogo />
              <LanguageSwitcher />
            </div>
            <Card className="border border-border">
              <CardHeader className="space-y-1">
                <CardTitle className="font-heading text-2xl flex items-center gap-2">
                  <Mail className="h-5 w-5" />
                  {t('signup.verify_email_title', 'Controlla la tua email')}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="rounded-md bg-green-50 border border-green-200 p-4 text-sm text-green-800">
                  {t('signup.verify_email_message', 'Ti abbiamo inviato un link di verifica. Clicca il link per attivare il tuo account.')}
                </div>
                <div className="text-center text-sm">
                  <Link to="/" className="font-medium text-primary hover:underline">
                    {t('signup.login_link', 'Accedi')}
                  </Link>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
        <div className="hidden lg:flex flex-1 items-center justify-center bg-muted/50 p-8">
          <div className="max-w-lg text-center">
            <h2 className="font-heading text-3xl font-bold tracking-tight mb-4">{t('marketing.tagline')}</h2>
            <p className="text-lg text-muted-foreground">{t('marketing.description')}</p>
          </div>
        </div>
      </div>
    );
  }

  // Invite-only mode without a valid token — show blocked message
  const isInviteOnly = registrationMode === 'invite_only';
  const showBlockedMessage = isInviteOnly && (!inviteToken || inviteValid === false);
  const showForm = !isInviteOnly || (inviteToken && inviteValid === true);
  // Still validating invite token
  const isValidatingInvite = isInviteOnly && inviteToken && inviteValid === null;

  if (isValidatingInvite) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-pulse text-muted-foreground">{t('signup.invite_loading')}</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex">
      {/* Left side - Form */}
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="w-full max-w-md">
          <div className="flex items-center justify-between mb-8">
            <BrandLogo />
            <LanguageSwitcher />
          </div>

          {showBlockedMessage ? (
            <Card className="border border-border">
              <CardHeader className="space-y-1">
                <CardTitle className="font-heading text-2xl flex items-center gap-2">
                  <Mail className="h-5 w-5" />
                  {t('signup.invite_only_title', 'Registrazione su invito')}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {inviteToken && inviteValid === false ? (
                  <div className="rounded-md bg-red-50 border border-red-200 p-4 text-sm text-red-800">
                    {t('signup.invite_invalid')}
                  </div>
                ) : requestSent ? (
                  <div className="rounded-md bg-green-50 border border-green-200 p-4 text-sm text-green-800">
                    {t('signup.request_invite_success')}
                  </div>
                ) : showRequestForm ? (
                  <form onSubmit={async (e) => {
                    e.preventDefault();
                    setRequestLoading(true);
                    try {
                      await authAPI.requestInvite(requestName, requestEmail, requestBusiness, i18n.language);
                      setRequestSent(true);
                    } catch {
                      toast.error(t('signup.request_invite_error'));
                    } finally {
                      setRequestLoading(false);
                    }
                  }} className="space-y-3">
                    <div className="space-y-2">
                      <Label>{t('signup.request_invite_name')}</Label>
                      <Input
                        value={requestName}
                        onChange={(e) => setRequestName(e.target.value)}
                        required
                        minLength={2}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>{t('signup.request_invite_email')}</Label>
                      <Input
                        type="email"
                        value={requestEmail}
                        onChange={(e) => setRequestEmail(e.target.value)}
                        required
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>{t('signup.request_invite_business')}</Label>
                      <Input
                        value={requestBusiness}
                        onChange={(e) => setRequestBusiness(e.target.value)}
                        required
                        minLength={2}
                      />
                    </div>
                    <Button type="submit" className="w-full" disabled={requestLoading}>
                      {requestLoading ? t('signup.request_invite_loading') : t('signup.request_invite_submit')}
                      <ArrowRight className="ml-2 h-4 w-4" />
                    </Button>
                    <div className="text-center">
                      <button
                        type="button"
                        onClick={() => setShowRequestForm(false)}
                        className="text-sm text-muted-foreground hover:text-primary hover:underline"
                      >
                        {t('signup.request_invite_back')}
                      </button>
                    </div>
                  </form>
                ) : (
                  <>
                    <p className="text-muted-foreground">
                      {t('signup.invite_only_message')}
                    </p>
                    <Button
                      variant="outline"
                      className="w-full"
                      onClick={() => setShowRequestForm(true)}
                    >
                      {t('signup.request_invite_cta')}
                    </Button>
                  </>
                )}
                <div className="text-center text-sm">
                  <Link to="/" className="font-medium text-primary hover:underline">
                    {t('signup.login_link')}
                  </Link>
                </div>
              </CardContent>
            </Card>
          ) : showForm ? (
            <Card className="border border-border">
              <CardHeader className="space-y-1">
                <CardTitle className="font-heading text-2xl">{t('signup.title')}</CardTitle>
                <CardDescription>
                  {t('signup.description')}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleSubmit} className="space-y-4">
                  {/*
                    Track O Step 5.1 — Honeypot anti-bot field.
                    Hidden via CSS (off-screen + zero size + no tab focus).
                    Humans never see it; naive bots that scrape rendered
                    HTML and fill every input will populate it → backend
                    detects + returns uniform 202 success (anti-enumeration).
                    NB: NOT type="hidden" because some bots skip those.
                    Visible-text-input + CSS hidden is the canonical pattern.
                    See backend/core/honeypot.py for full threat model.
                  */}
                  <input
                    type="text"
                    name="website"
                    value={website}
                    onChange={(e) => setWebsite(e.target.value)}
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
                  <div className="space-y-2">
                    <Label htmlFor="name">{t('signup.name')}</Label>
                    <Input
                      id="name"
                      type="text"
                      placeholder={t('placeholders.name')}
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      required
                      data-testid="signup-name-input"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="email">
                      {t('signup.email')}
                      {inviteEmail && (
                        <span className="ml-2 text-xs text-muted-foreground">
                          ({t('signup.invite_email_locked', 'Email impostata dall\'invito')})
                        </span>
                      )}
                    </Label>
                    <Input
                      id="email"
                      type="email"
                      placeholder={t('placeholders.email_signup')}
                      value={email}
                      onChange={(e) => !inviteEmail && setEmail(e.target.value)}
                      readOnly={!!inviteEmail}
                      required
                      className={inviteEmail ? 'bg-muted' : ''}
                      data-testid="signup-email-input"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="organization">{t('signup.org_name')}</Label>
                    <Input
                      id="organization"
                      type="text"
                      placeholder={t('placeholders.org_name')}
                      value={organizationName}
                      onChange={(e) => setOrganizationName(e.target.value)}
                      data-testid="signup-org-input"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="password">{t('signup.password')}</Label>
                    <div className="relative">
                      <Input
                        id="password"
                        type={showPassword ? 'text' : 'password'}
                        placeholder={t('placeholders.password_create')}
                        value={password}
                        onChange={(e) => { setPassword(e.target.value); setPasswordError(''); }}
                        required
                        minLength={12}
                        className={passwordError ? 'border-destructive' : ''}
                        data-testid="signup-password-input"
                      />
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        className="absolute right-0 top-0 h-full px-3"
                        onClick={() => setShowPassword(!showPassword)}
                      >
                        {showPassword ? (
                          <EyeOff className="h-4 w-4 text-muted-foreground" />
                        ) : (
                          <Eye className="h-4 w-4 text-muted-foreground" />
                        )}
                      </Button>
                    </div>
                    {passwordError ? (
                      <p className="text-xs text-destructive">{passwordError}</p>
                    ) : (
                      <p className="text-xs text-muted-foreground">
                        {t('validation.password_min_length')}, {t('validation.password_lowercase')}, {t('validation.password_uppercase')}, {t('validation.password_digit')}.
                      </p>
                    )}
                  </div>
                  {/* AN4 — due consensi distinti (granularita' art. 7 GDPR),
                      come gia' fa il signup cliente. Il locale passa nei
                      link cosi' l'utente legge il documento nella SUA lingua
                      (backend fallback IT, defense in depth). */}
                  <div className="flex items-start gap-2">
                    <input
                      type="checkbox"
                      id="accept-privacy"
                      checked={acceptedPrivacy}
                      onChange={(e) => setAcceptedPrivacy(e.target.checked)}
                      className="mt-1 h-4 w-4 rounded border-border"
                      data-testid="signup-privacy-checkbox"
                    />
                    <label htmlFor="accept-privacy" className="text-xs text-muted-foreground leading-relaxed">
                      {t('signup.accept_privacy', "Ho letto l'informativa sulla")}{' '}
                      <a href={`/privacy?lang=${i18n.language || 'it'}`} target="_blank" rel="noopener noreferrer" className="text-primary underline hover:text-primary/80">
                        {t('signup.privacy_policy', 'Privacy Policy')}
                      </a>
                    </label>
                  </div>
                  <div className="flex items-start gap-2">
                    <input
                      type="checkbox"
                      id="accept-terms"
                      checked={acceptedTerms}
                      onChange={(e) => setAcceptedTerms(e.target.checked)}
                      className="mt-1 h-4 w-4 rounded border-border"
                      data-testid="signup-terms-checkbox"
                    />
                    <label htmlFor="accept-terms" className="text-xs text-muted-foreground leading-relaxed">
                      {t('signup.accept_terms_only', 'Accetto i')}{' '}
                      <a href={`/terms?lang=${i18n.language || 'it'}`} target="_blank" rel="noopener noreferrer" className="text-primary underline hover:text-primary/80">
                        {t('signup.terms_of_service', 'Termini di Servizio')}
                      </a>
                    </label>
                  </div>
                  <Button
                    type="submit"
                    className="w-full"
                    disabled={loading || !acceptedTerms || !acceptedPrivacy}
                    data-testid="signup-submit-btn"
                  >
                    {loading ? t('signup.loading') : t('signup.submit')}
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </Button>
                </form>

                <div className="mt-6 text-center text-sm">
                  <span className="text-muted-foreground">{t('signup.has_account')} </span>
                  <Link
                    to="/"
                    className="font-medium text-primary hover:underline"
                    data-testid="login-link"
                  >
                    {t('signup.login_link')}
                  </Link>
                </div>
              </CardContent>
            </Card>
          ) : null}
        </div>
      </div>

      {/* Right side - Visual */}
      <div className="hidden lg:flex flex-1 items-center justify-center bg-muted/50 p-8">
        <div className="max-w-lg text-center">
          <h2 className="font-heading text-3xl font-bold tracking-tight mb-4">
            {t('marketing.tagline')}
          </h2>
          <p className="text-lg text-muted-foreground">
            {t('marketing.description')}
          </p>
        </div>
      </div>
    </div>
  );
};

// ── ForgotPasswordPage ────────────────────────────────────────────────────────

export const ForgotPasswordPage = () => {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [devResetUrl, setDevResetUrl] = useState(null);
  const { t } = useTranslation('auth');
  useLangParam();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const response = await authAPI.forgotPassword(email);
      setSubmitted(true);
      // Dev mode only — backend returns the reset URL so we can test without SMTP.
      if (response.data?.dev_reset_url) {
        setDevResetUrl(response.data.dev_reset_url);
      }
    } catch (error) {
      // Still show success to prevent email enumeration.
      setSubmitted(true);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex">
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="w-full max-w-md">
          <div className="flex items-center justify-between mb-8">
            <BrandLogo />
            <LanguageSwitcher />
          </div>

          <Card className="border border-border">
            <CardHeader className="space-y-1">
              <CardTitle className="font-heading text-2xl flex items-center gap-2">
                <Mail className="h-5 w-5" />
                {t('forgot_password.title')}
              </CardTitle>
              <CardDescription>
                {t('forgot_password.description')}
              </CardDescription>
            </CardHeader>
            <CardContent>
              {submitted ? (
                <div className="space-y-4">
                  <div className="rounded-md bg-green-50 border border-green-200 p-4 text-sm text-green-800">
                    {t('forgot_password.success')}
                  </div>
                  {devResetUrl && (
                    <div className="rounded-md bg-amber-50 border border-amber-200 p-4 text-sm space-y-2">
                      <p className="font-medium text-amber-800">Modalità sviluppo — link di reset:</p>
                      <a
                        href={devResetUrl}
                        className="block break-all text-amber-700 underline hover:text-amber-900"
                        data-testid="dev-reset-url"
                      >
                        {devResetUrl}
                      </a>
                    </div>
                  )}
                  <div className="text-center text-sm">
                    <Link to="/" className="font-medium text-primary hover:underline">
                      {t('forgot_password.back_to_login')}
                    </Link>
                  </div>
                </div>
              ) : (
                <form onSubmit={handleSubmit} className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="forgot-email">{t('forgot_password.email')}</Label>
                    <Input
                      id="forgot-email"
                      type="email"
                      placeholder={t('placeholders.email_login')}
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      required
                      data-testid="forgot-email-input"
                    />
                  </div>
                  <Button
                    type="submit"
                    className="w-full"
                    disabled={loading}
                    data-testid="forgot-submit-btn"
                  >
                    {loading ? t('forgot_password.loading') : t('forgot_password.submit')}
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </Button>
                  <div className="text-center text-sm">
                    <Link to="/" className="text-muted-foreground hover:text-primary hover:underline">
                      {t('forgot_password.back_to_login')}
                    </Link>
                  </div>
                </form>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      <div className="hidden lg:flex flex-1 items-center justify-center bg-muted/50 p-8">
        <div className="max-w-lg text-center">
          <h2 className="font-heading text-3xl font-bold tracking-tight mb-4">
            {t('marketing.tagline')}
          </h2>
          <p className="text-lg text-muted-foreground">
            {t('marketing.description')}
          </p>
        </div>
      </div>
    </div>
  );
};

// ── ResetPasswordPage ─────────────────────────────────────────────────────────

export const ResetPasswordPage = () => {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token') || '';
  const navigate = useNavigate();
  const { t } = useTranslation('auth');
  useLangParam();

  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);

  const [passwordError, setPasswordError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (newPassword !== confirmPassword) {
      setPasswordError(t('validation.passwords_mismatch'));
      return;
    }
    const pwError = validatePassword(newPassword, t);
    if (pwError) {
      setPasswordError(pwError);
      return;
    }
    setPasswordError('');
    if (!token) {
      toast.error(t('reset_password.token_missing'));
      return;
    }
    setLoading(true);
    try {
      await authAPI.resetPassword(token, newPassword);
      toast.success(t('reset_password.success'));
      navigate('/');
    } catch (error) {
      toast.error(extractApiError(error, 'Token non valido o scaduto.'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex">
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="w-full max-w-md">
          <div className="flex items-center justify-between mb-8">
            <BrandLogo />
            <LanguageSwitcher />
          </div>

          <Card className="border border-border">
            <CardHeader className="space-y-1">
              <CardTitle className="font-heading text-2xl flex items-center gap-2">
                <KeyRound className="h-5 w-5" />
                {t('reset_password.title')}
              </CardTitle>
              <CardDescription>
                {t('reset_password.description')}
              </CardDescription>
            </CardHeader>
            <CardContent>
              {!token ? (
                <div className="space-y-4">
                  <div className="rounded-md bg-red-50 border border-red-200 p-4 text-sm text-red-800">
                    {t('reset_password.invalid_link')}
                  </div>
                  <div className="text-center text-sm">
                    <Link to="/forgot-password" className="font-medium text-primary hover:underline">
                      {t('reset_password.request_new')}
                    </Link>
                  </div>
                </div>
              ) : (
                <form onSubmit={handleSubmit} className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="reset-new-password">{t('reset_password.new_password')}</Label>
                    <div className="relative">
                      <Input
                        id="reset-new-password"
                        type={showPassword ? 'text' : 'password'}
                        placeholder={t('placeholders.password_min')}
                        value={newPassword}
                        onChange={(e) => { setNewPassword(e.target.value); setPasswordError(''); }}
                        required
                        minLength={12}
                        autoComplete="new-password"
                        className={passwordError ? 'border-destructive' : ''}
                        data-testid="reset-new-password-input"
                      />
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        className="absolute right-0 top-0 h-full px-3"
                        onClick={() => setShowPassword(!showPassword)}
                      >
                        {showPassword ? (
                          <EyeOff className="h-4 w-4 text-muted-foreground" />
                        ) : (
                          <Eye className="h-4 w-4 text-muted-foreground" />
                        )}
                      </Button>
                    </div>
                    {passwordError ? (
                      <p className="text-xs text-destructive">{passwordError}</p>
                    ) : (
                      <p className="text-xs text-muted-foreground">
                        {t('validation.password_min_length')}, {t('validation.password_lowercase')}, {t('validation.password_uppercase')}, {t('validation.password_digit')}.
                      </p>
                    )}
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="reset-confirm-password">{t('reset_password.confirm_password')}</Label>
                    <Input
                      id="reset-confirm-password"
                      type="password"
                      placeholder={t('placeholders.password_confirm')}
                      value={confirmPassword}
                      onChange={(e) => { setConfirmPassword(e.target.value); setPasswordError(''); }}
                      required
                      minLength={12}
                      autoComplete="new-password"
                      data-testid="reset-confirm-password-input"
                    />
                  </div>
                  <Button
                    type="submit"
                    className="w-full"
                    disabled={loading}
                    data-testid="reset-submit-btn"
                  >
                    {loading ? t('reset_password.loading') : t('reset_password.submit')}
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </Button>
                  <div className="text-center text-sm">
                    <Link to="/" className="text-muted-foreground hover:text-primary hover:underline">
                      {t('forgot_password.back_to_login')}
                    </Link>
                  </div>
                </form>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      <div className="hidden lg:flex flex-1 items-center justify-center bg-muted/50 p-8">
        <div className="max-w-lg text-center">
          <h2 className="font-heading text-3xl font-bold tracking-tight mb-4">
            {t('marketing.tagline')}
          </h2>
          <p className="text-lg text-muted-foreground">
            {t('marketing.description')}
          </p>
        </div>
      </div>
    </div>
  );
};

export const VerifyEmailPage = () => {
  const { t } = useTranslation('auth');
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const token = searchParams.get('token');
  useLangParam();

  const [status, setStatus] = useState('loading'); // loading | success | error

  useEffect(() => {
    if (!token) {
      setStatus('error');
      return;
    }

    const verify = async () => {
      try {
        await authAPI.verifyEmail(token);
        setStatus('success');
      } catch (err) {
        setStatus('error');
      }
    };

    verify();
  }, [token]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-background px-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <div className="mx-auto mb-4">
            {status === 'loading' && <Loader2 className="h-12 w-12 text-primary animate-spin" />}
            {status === 'success' && <CheckCircle2 className="h-12 w-12 text-green-500" />}
            {status === 'error' && <XCircle className="h-12 w-12 text-destructive" />}
          </div>
          <CardTitle>
            {status === 'loading' && t('verify_email.verifying')}
            {status === 'success' && t('verify_email.verified_title')}
            {status === 'error' && t('verify_email.error_title')}
          </CardTitle>
          <CardDescription>
            {status === 'success' && t('verify_email.success')}
            {status === 'error' && (!token ? t('verify_email.invalid_link') : t('verify_email.error'))}
          </CardDescription>
        </CardHeader>
        <CardContent className="text-center">
          {status !== 'loading' && (
            <Button onClick={() => navigate(`/?lang=${i18n.language}`)} className="w-full">
              {t('verify_email.go_to_login', 'Vai al Login')}
              <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default LoginPage;
