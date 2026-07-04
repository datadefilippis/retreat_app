/**
 * VerifyEmailRequiredPage
 * =======================
 * Onda 28 Step 5 — blocking page shown to authenticated-but-unverified
 * users. Wrapped at routing layer by RequireAuthOnly (Onda 28 Step 4),
 * so:
 *   · unauthenticated users never reach here (bounced to "/")
 *   · already-verified or system_admin users bounce to /dashboard
 *
 * UX
 * --
 *   · Standalone layout (NO admin sidebar).
 *   · Centered card with email illustration, copy in user.locale,
 *     "resend verification email" button, and "use another account"
 *     escape hatch.
 *   · Background polling: every 30s we re-fetch /api/auth/me. If the
 *     server now reports email_verified=true (= the user clicked the
 *     link in the email from another tab/device), AuthContext updates
 *     the user object, the local useEffect detects the change, and we
 *     navigate to /dashboard with a success toast. No manual reload
 *     required.
 *
 * i18n
 * ----
 * All copy lives under the `auth.verify_email_required.*` namespace
 * in src/locales/{it,en,de,fr}/auth.json. The page mounts a small
 * useEffect that calls i18n.changeLanguage(user.locale) so the right
 * language renders even if the global app language was different
 * (this is the same pattern as AuthContext at user-load time).
 *
 * Resend rate limit
 * -----------------
 * Backend caps /api/auth/resend-verification at 3/min per IP via
 * slowapi (Onda 27.2 makes that a real per-IP limit). The button is
 * disabled while a request is in-flight; on success/error we show a
 * sonner toast. We don't try to client-side-cooldown beyond that —
 * 429 from the backend is shown as the error toast.
 */

import React, { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Mail, RefreshCw, LogOut, CheckCircle } from 'lucide-react';
import { toast } from 'sonner';
import i18n from '../../i18n';
import { useAuth } from '../../context/AuthContext';
import { authAPI } from '../../api/auth';
import { Button } from '../../components/ui/button';
import { Card, CardContent } from '../../components/ui/card';

const POLL_INTERVAL_MS = 30_000;

export default function VerifyEmailRequiredPage() {
  const { t } = useTranslation('auth');
  const { user, logout, refreshUser } = useAuth();
  const navigate = useNavigate();
  const [resending, setResending] = useState(false);

  // Onda 28 — sync UI language with user.locale (each user may have
  // a different preference; we don't assume the global app locale
  // matches). Mirror of AuthContext line 83.
  useEffect(() => {
    if (user?.locale) {
      i18n.changeLanguage(user.locale);
    }
  }, [user?.locale]);

  // Polling: every 30s, refresh /me. Cleanup on unmount.
  useEffect(() => {
    const id = setInterval(() => {
      refreshUser?.().catch(() => {
        // Silent — network blip during background poll is non-fatal.
      });
    }, POLL_INTERVAL_MS);
    return () => clearInterval(id);
  }, [refreshUser]);

  // When user.email_verified flips to true (= they clicked the link
  // in another tab/device), bounce to dashboard. The strict !== false
  // check ensures we don't redirect on transient undefined during
  // context load.
  useEffect(() => {
    if (user && user.email_verified === true) {
      toast.success(t('verify_email_required.verified_redirect_toast'));
      navigate('/dashboard', { replace: true });
    }
  }, [user, navigate, t]);

  const handleResend = useCallback(async () => {
    if (!user?.email || resending) return;
    setResending(true);
    try {
      await authAPI.resendVerification(user.email);
      toast.success(t('verify_email_required.resend_sent_toast'));
    } catch (err) {
      const status = err?.response?.status;
      const msg =
        status === 429
          ? t('verify_email_required.resend_rate_limited')
          : t('verify_email_required.resend_error_toast');
      toast.error(msg);
    } finally {
      setResending(false);
    }
  }, [user, resending, t]);

  const handleLogout = useCallback(() => {
    logout?.();
    navigate('/', { replace: true });
  }, [logout, navigate]);

  if (!user) {
    // Should not happen — RequireAuthOnly already gated this — but be
    // defensive in case of fast unmount/race.
    return null;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-indigo-50 flex items-center justify-center px-4 py-8">
      <Card className="w-full max-w-md shadow-lg">
        <CardContent className="p-6 sm:p-8 space-y-5">
          {/* Header icon + title */}
          <div className="flex flex-col items-center text-center">
            <div className="rounded-full bg-blue-100 p-3 mb-3">
              <Mail className="h-8 w-8 text-blue-600" aria-hidden />
            </div>
            <h1 className="text-2xl font-semibold text-gray-900">
              {t('verify_email_required.title')}
            </h1>
            <p className="text-sm text-gray-600 mt-2">
              {t('verify_email_required.subtitle')}
            </p>
          </div>

          {/* Email shown */}
          <div className="bg-gray-50 border border-gray-200 rounded-md p-3 text-center">
            <p className="text-xs text-gray-500 mb-1">
              {t('verify_email_required.email_sent_to')}
            </p>
            <p className="text-sm font-medium text-gray-900 break-all">
              {user.email}
            </p>
          </div>

          {/* Instructions */}
          <p className="text-sm text-gray-700 leading-relaxed">
            {t('verify_email_required.instructions')}
          </p>

          {/* Resend block */}
          <div className="border-t border-gray-200 pt-4 space-y-2">
            <p className="text-xs text-gray-500">
              {t('verify_email_required.no_email_received')}{' '}
              <span className="text-gray-400">
                {t('verify_email_required.check_spam')}
              </span>
            </p>
            <Button
              type="button"
              onClick={handleResend}
              disabled={resending}
              className="w-full"
            >
              {resending ? (
                <>
                  <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                  {t('verify_email_required.resending')}
                </>
              ) : (
                <>
                  <RefreshCw className="mr-2 h-4 w-4" />
                  {t('verify_email_required.resend_btn')}
                </>
              )}
            </Button>
          </div>

          {/* Auto-detect status (informational) */}
          <div className="flex items-center justify-center gap-2 text-xs text-gray-400">
            <CheckCircle className="h-3 w-3 animate-pulse" aria-hidden />
            <span>{t('verify_email_required.checking_status')}</span>
          </div>

          {/* Logout escape */}
          <div className="border-t border-gray-200 pt-4 text-center">
            <button
              type="button"
              onClick={handleLogout}
              className="text-xs text-gray-500 hover:text-gray-700 inline-flex items-center gap-1"
            >
              <LogOut className="h-3 w-3" aria-hidden />
              {t('verify_email_required.change_account_link')}
            </button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
