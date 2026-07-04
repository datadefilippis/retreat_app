/**
 * ResetPasswordPage — finalize a password reset with a token.
 *
 * Phase 5 of the customer area refactor. Logic extracted verbatim
 * from CustomerPortalPages.js (CustomerResetPasswordPage).
 *
 * Token comes from the URL (?token=…) — sent by the backend in the
 * reset email. We don't show the AuthShell store header here because
 * the customer may have never visited the storefront yet (e.g. the
 * link was forwarded to them) — generic "AFianco" branding fallback
 * applies.
 *
 * Password rules mirrored from the backend validator (same as signup).
 */

import React, { useState } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Eye, EyeOff, Loader2, CheckCircle2 } from 'lucide-react';
import { toast } from 'sonner';
import { customerAuthAPI } from '../../../api/customerAuth';
import { Button } from '../../../components/ui/button';
import { Input } from '../../../components/ui/input';
import { Label } from '../../../components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '../../../components/ui/card';
import AuthShell, { useStoreInfo } from './AuthShell';


export default function ResetPasswordPage() {
  const { t } = useTranslation('customer_auth');
  // Slug resolution priority — same pattern as VerifyEmailPage:
  //   1. `?store=` from the email link (backend embeds it now).
  //   2. `org_slug` returned by the reset-password response (auth.).
  //   3. localStorage — historical fallback.
  // Whichever wins is persisted to localStorage so the next paint of
  // /account/login picks it up automatically.
  const [searchParams] = useSearchParams();
  const slugFromUrl = searchParams.get('store') || '';
  const token = searchParams.get('token') || '';
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);
  const [slugFromResponse, setSlugFromResponse] = useState('');

  const resolvedSlug =
    slugFromUrl
    || slugFromResponse
    || localStorage.getItem('customer_store_slug')
    || '';

  // Pull store branding + storefront_languages so the AuthShell mounts
  // useStorefrontLocaleSync with the right supported list. Resolved
  // slug may be empty (legacy reset email without ?store=) — useStoreInfo
  // is a no-op in that case and the locale resolver falls through.
  const { storeInfo, orgName, storefrontLanguages } = useStoreInfo(resolvedSlug);

  const passwordValid =
    password.length >= 12 &&
    /[a-z]/.test(password) &&
    /[A-Z]/.test(password) &&
    /\d/.test(password);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!passwordValid) return;
    setLoading(true);
    try {
      const res = await customerAuthAPI.resetPassword(token, password);
      const respSlug = res?.data?.org_slug || '';
      if (respSlug) setSlugFromResponse(respSlug);
      const persistSlug = slugFromUrl || respSlug;
      if (persistSlug) {
        localStorage.setItem('customer_store_slug', persistSlug);
      }
      setDone(true);
    } catch (err) {
      const detail = err?.response?.data?.detail;
      toast.error(typeof detail === 'string' ? detail : t('customer_auth:reset.tokenInvalid'));
    } finally {
      setLoading(false);
    }
  };

  if (done) {
    return (
      <AuthShell storeInfo={storeInfo} orgName={orgName} slug={resolvedSlug} storefrontLanguages={storefrontLanguages}>
        <Card>
          <CardContent className="pt-6 text-center space-y-3">
            <CheckCircle2 className="h-10 w-10 text-emerald-500 mx-auto" />
            <p className="text-sm text-muted-foreground">{t('customer_auth:reset.successMsg')}</p>
            <Link to={`/account/login${resolvedSlug ? `?store=${resolvedSlug}` : ''}`}>
              <Button size="sm">{t('customer_auth:login.submit')}</Button>
            </Link>
          </CardContent>
        </Card>
      </AuthShell>
    );
  }

  return (
    <AuthShell storeInfo={storeInfo} orgName={orgName} slug={resolvedSlug} storefrontLanguages={storefrontLanguages}>
      <Card>
        <CardHeader className="text-center">
          <CardTitle className="text-xl">{t('customer_auth:reset.title')}</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <Label>{t('customer_auth:reset.newPasswordLabel')}</Label>
              <div className="relative">
                <Input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground"
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                {t('customer_auth:reset.passwordRules')}
              </p>
            </div>
            <Button type="submit" className="w-full" disabled={loading || !passwordValid}>
              {loading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
              {t('customer_auth:reset.submit')}
            </Button>
          </form>
        </CardContent>
      </Card>
    </AuthShell>
  );
}
