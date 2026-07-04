/**
 * ForgotPasswordPage — request a reset link.
 *
 * Phase 5 of the customer area refactor. Logic extracted verbatim
 * from CustomerPortalPages.js (CustomerForgotPasswordPage).
 *
 * Privacy note: the success state ("Se l'email esiste, riceverai un
 * link…") is intentionally vague — we never reveal whether the email
 * is registered, to prevent enumeration attacks. The backend always
 * returns 200 even for non-existent emails.
 */

import React, { useState } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Loader2, CheckCircle2 } from 'lucide-react';
import { toast } from 'sonner';
import { customerAuthAPI } from '../../../api/customerAuth';
import { Button } from '../../../components/ui/button';
import { Input } from '../../../components/ui/input';
import { Label } from '../../../components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '../../../components/ui/card';
import AuthShell, { useStoreInfo } from './AuthShell';


export default function ForgotPasswordPage() {
  const [searchParams] = useSearchParams();
  const slug = searchParams.get('store') || localStorage.getItem('customer_store_slug') || '';
  const { storeInfo, orgName, storefrontLanguages } = useStoreInfo(slug);
  const { t, i18n } = useTranslation('customer_auth');
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!slug) { toast.error(t('customer_auth:errors.storeUnknown')); return; }
    setLoading(true);
    try {
      // Send the active locale so the reset email arrives in the
      // language the visitor is currently browsing in.
      await customerAuthAPI.forgotPassword(slug, email, (i18n.language || 'it').split('-')[0]);
      setSent(true);
    } catch {
      toast.error(t('customer_auth:errors.genericRetry'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthShell storeInfo={storeInfo} orgName={orgName} slug={slug} storefrontLanguages={storefrontLanguages}>
      <Card>
        <CardHeader className="text-center">
          <CardTitle className="text-xl">{t('customer_auth:forgot.title')}</CardTitle>
        </CardHeader>
        <CardContent>
          {sent ? (
            <div className="text-center space-y-3">
              <CheckCircle2 className="h-10 w-10 text-emerald-500 mx-auto" />
              <p className="text-sm text-muted-foreground">
                {t('customer_auth:forgot.sentMsg')}
              </p>
              <Link to={`/account/login${slug ? `?store=${slug}` : ''}`}>
                <Button variant="outline" size="sm">{t('customer_auth:forgot.backToLogin')}</Button>
              </Link>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <Label>{t('customer_auth:fields.email')}</Label>
                <Input type="email" value={email} onChange={e => setEmail(e.target.value)} required />
              </div>
              <Button type="submit" className="w-full" disabled={loading}>
                {loading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
                {t('customer_auth:forgot.submit')}
              </Button>
              <p className="text-center text-sm">
                <Link
                  to={`/account/login${slug ? `?store=${slug}` : ''}`}
                  className="text-primary hover:underline"
                >
                  {t('customer_auth:forgot.backToLogin')}
                </Link>
              </p>
            </form>
          )}
        </CardContent>
      </Card>
    </AuthShell>
  );
}
