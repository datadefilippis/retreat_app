/**
 * EmailVerificationBanner — sticky reminder shown across every
 * customer portal page until the customer's email is verified.
 *
 * Extracted from CustomerPortalPages.js (where it lived inline in
 * CustomerPortalPage). Now self-contained:
 *   - Reads `customer` from useCustomerAuth() instead of taking it
 *     as prop, so the parent (CustomerLayout) doesn't need to thread
 *     the value through.
 *   - Self-hides when `email_verified=true` so adding it to the
 *     layout shell is idempotent.
 *   - Idempotent on the resend button: once clicked, becomes "✓ Inviata"
 *     and the request is not re-fired even if the customer clicks
 *     again. (The backend rate-limits anyway, but this is friendlier.)
 *
 * Customer of the auto_login course-checkout flow lands here right
 * after signup. They can keep using the portal — the banner is the
 * only nudge to verify the email when it suits them.
 */

import React, { useState } from 'react';
import { useTranslation, Trans } from 'react-i18next';
import { toast } from 'sonner';
import { customerAuthAPI } from '../../../api/customerAuth';
import { useCustomerAuth } from '../../../context/CustomerAuthContext';


export default function EmailVerificationBanner() {
  const { customer, storeSlug } = useCustomerAuth();
  const { t } = useTranslation('customer_portal');
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(false);

  if (!customer || customer.email_verified) return null;

  const handleResend = async () => {
    if (sending || sent) return;
    if (!storeSlug) {
      toast.error(t('customer_portal:emailBanner.storeUnknown'));
      return;
    }
    setSending(true);
    try {
      await customerAuthAPI.resendVerification(storeSlug, customer.email);
      setSent(true);
      toast.success(t('customer_portal:emailBanner.resentToast'));
    } catch (e) {
      const detail = e?.response?.data?.detail;
      const msg = typeof detail === 'string'
        ? detail
        : (detail && (detail.message || detail.error)) || t('customer_portal:emailBanner.resendError');
      toast.error(String(msg));
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="rounded-xl border border-amber-200 bg-amber-50 p-3 flex items-start gap-3">
      <span aria-hidden className="text-xl shrink-0">⚠️</span>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold text-amber-900">
          {t('customer_portal:emailBanner.title')}
        </p>
        <p className="text-xs text-amber-800 mt-0.5">
          <Trans
            i18nKey="customer_portal:emailBanner.body"
            values={{ email: customer.email }}
            components={{ strong: <strong /> }}
          />
        </p>
      </div>
      <button
        type="button"
        onClick={handleResend}
        disabled={sending || sent}
        className="rounded-md border border-amber-300 bg-white text-amber-900 hover:bg-amber-100 text-xs font-semibold px-3 py-1.5 whitespace-nowrap disabled:opacity-60"
      >
        {sent ? t('customer_portal:emailBanner.sent') : sending ? t('customer_portal:emailBanner.sending') : t('customer_portal:emailBanner.resendBtn')}
      </button>
    </div>
  );
}
