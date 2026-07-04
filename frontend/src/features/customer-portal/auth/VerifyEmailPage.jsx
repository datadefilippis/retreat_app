/**
 * VerifyEmailPage — clicked from the verification email.
 *
 * Phase 5 of the customer area refactor. Logic extracted verbatim
 * from CustomerPortalPages.js (CustomerVerifyEmailPage).
 *
 * Three states:
 *   - verifying  → spinner while we hit /customer-auth/verify-email
 *   - success    → email_verified=true server-side, prompt to login
 *   - error      → token missing/expired/used, prompt to retry login
 *
 * No form here — verification is a one-shot side-effect of opening
 * the URL, run inside useEffect on mount. We never show the storefront
 * header (no `slug` prop) because the customer arrived directly from
 * the email and the slug context is lost.
 *
 * Slug resolution priority (so the post-verify "Accedi" button always
 * routes to the right storefront login, even when localStorage is
 * stale or empty — e.g. user clicked the link on a different device):
 *
 *   1. `?store=` query param embedded in the email link (set by the
 *      backend at signup time).
 *   2. `org_slug` field returned in the verify-email response (server-
 *      authoritative; survives links sent before the email-side fix).
 *   3. localStorage `customer_store_slug` — historical fallback only.
 *
 * The first slug we resolve is also persisted to localStorage so other
 * customer-portal pages (login, orders, etc.) pick it up on subsequent
 * navigation.
 */

import React, { useEffect, useMemo, useState } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Loader2, CheckCircle2 } from 'lucide-react';
import { customerAuthAPI } from '../../../api/customerAuth';
import { Button } from '../../../components/ui/button';
import { Card, CardContent } from '../../../components/ui/card';
import AuthShell, { useStoreInfo } from './AuthShell';


export default function VerifyEmailPage() {
  const { t } = useTranslation('customer_auth');
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token') || '';
  const slugFromUrl = searchParams.get('store') || '';

  const [status, setStatus] = useState('verifying'); // verifying | success | error
  const [slugFromResponse, setSlugFromResponse] = useState('');

  // Single source of truth for the slug used in the "Accedi" link.
  // Recomputed when the verify response lands.
  const resolvedSlug = useMemo(() => (
    slugFromUrl
    || slugFromResponse
    || localStorage.getItem('customer_store_slug')
    || ''
  ), [slugFromUrl, slugFromResponse]);

  const { storeInfo, orgName, storefrontLanguages } = useStoreInfo(resolvedSlug);

  useEffect(() => {
    if (!token) {
      setStatus('error');
      return;
    }
    customerAuthAPI.verifyEmail(token)
      .then((res) => {
        const respSlug = res?.data?.org_slug || '';
        if (respSlug) setSlugFromResponse(respSlug);
        // Persist the authoritative slug so /account/login + the rest
        // of the customer portal pick it up on the next paint.
        const persistSlug = slugFromUrl || respSlug;
        if (persistSlug) {
          localStorage.setItem('customer_store_slug', persistSlug);
        }
        setStatus('success');
      })
      .catch(() => setStatus('error'));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  const loginHref = `/account/login${resolvedSlug ? `?store=${resolvedSlug}` : ''}`;

  return (
    <AuthShell storeInfo={storeInfo} orgName={orgName} slug={resolvedSlug} storefrontLanguages={storefrontLanguages}>
      <Card>
        <CardContent className="pt-6 text-center space-y-3">
          {status === 'verifying' && (
            <>
              <Loader2 className="h-8 w-8 animate-spin mx-auto text-muted-foreground" />
              <p className="text-sm text-muted-foreground">{t('customer_auth:verify.verifying')}</p>
            </>
          )}
          {status === 'success' && (
            <>
              <CheckCircle2 className="h-10 w-10 text-emerald-500 mx-auto" />
              <p className="text-sm font-medium">{t('customer_auth:verify.success')}</p>
              <Link to={loginHref}>
                <Button size="sm">{t('customer_auth:login.submit')}</Button>
              </Link>
            </>
          )}
          {status === 'error' && (
            <>
              <p className="text-sm text-red-600">{t('customer_auth:verify.tokenInvalid')}</p>
              <Link to={loginHref}>
                <Button variant="outline" size="sm">{t('customer_auth:verify.goLogin')}</Button>
              </Link>
            </>
          )}
        </CardContent>
      </Card>
    </AuthShell>
  );
}
