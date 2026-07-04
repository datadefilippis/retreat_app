/**
 * CustomerReconsentModal — Wave GDPR-Commerce Phase CG-4.
 *
 * Mirror of the admin-side ReconsentModal (Wave GDPR-Admin Phase E),
 * but for END CUSTOMERS on the storefront / customer-portal surface.
 *
 * Behaviour
 * =========
 * - Self-gates on ``customer.consent_needs_refresh`` from /api/customer/me.
 *   Renders nothing when False — zero cost in the happy path.
 * - Bloccante: Escape + outside-click are intercepted; the customer's
 *   only paths forward are (a) accept the merchant's current Privacy
 *   + Terms, or (b) log out.
 * - On accept: POST /api/customer/me/re-consent (server reads the
 *   live version from the customer's signup_slug — the client never
 *   sends a version string), then refreshes the customer context so
 *   the modal unmounts.
 *
 * Mounted in CustomerLayout so EVERY authenticated customer page on
 * the portal surfaces the prompt.
 */

import React, { useState, useCallback } from 'react';
import * as DialogPrimitive from '@radix-ui/react-dialog';
import { useTranslation } from 'react-i18next';
import { ShieldCheck, ExternalLink, LogOut, Loader2 } from 'lucide-react';

import { useCustomerAuth } from '../../context/CustomerAuthContext';
import { customerAuthAPI } from '../../api/customerAuth';


export default function CustomerReconsentModal() {
  const { t } = useTranslation('legal');
  const { customer, refreshCustomer, logout } = useCustomerAuth();

  const [checked, setChecked] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  // Render gate
  const open = Boolean(customer && customer.consent_needs_refresh);

  // Legacy customers (pre-CG-4) have no accepted_store_*_version → we
  // show "first acceptance" copy. Otherwise we show "we updated" copy.
  const isFirstConsent = open && !customer.accepted_store_terms_version;

  // The customer's signup slug drives the docs URLs (CG-2 endpoints).
  // Falls back to org_slug for very old accounts that pre-date the
  // multi-store schema; in that case the link may 404 gracefully and
  // the customer can still re-accept (they just won't be able to
  // open the docs from the modal).
  const slug = customer?.signup_slug || customer?.org_slug || '';

  const handleAccept = useCallback(async () => {
    if (!checked || submitting) return;
    setSubmitting(true);
    setError(null);
    try {
      await customerAuthAPI.reConsent();
      // Refresh the customer object so consent_needs_refresh flips False.
      if (refreshCustomer) await refreshCustomer();
    } catch (err) {
      console.error('customer re-consent failed:', err);
      setError(t('customer_reconsent.error_generic'));
      setSubmitting(false);
    }
  }, [checked, submitting, refreshCustomer, t]);

  const handleLogout = useCallback(() => {
    if (submitting) return;
    if (logout) logout();
  }, [submitting, logout]);

  return (
    <DialogPrimitive.Root open={open}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay
          className="fixed inset-0 z-[100] bg-black/70 backdrop-blur-sm data-[state=open]:animate-in data-[state=open]:fade-in-0"
        />
        <DialogPrimitive.Content
          className="fixed left-1/2 top-1/2 z-[101] w-[95vw] max-w-xl -translate-x-1/2 -translate-y-1/2 rounded-lg border bg-background p-6 shadow-2xl data-[state=open]:animate-in data-[state=open]:zoom-in-95 sm:rounded-xl"
          onEscapeKeyDown={(e) => e.preventDefault()}
          onPointerDownOutside={(e) => e.preventDefault()}
          onInteractOutside={(e) => e.preventDefault()}
        >
          <div className="flex items-start gap-3">
            <div className="rounded-full bg-blue-100 p-2 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400">
              <ShieldCheck className="h-5 w-5" />
            </div>
            <div className="flex-1">
              <DialogPrimitive.Title className="text-lg font-semibold leading-tight tracking-tight">
                {t('customer_reconsent.title')}
              </DialogPrimitive.Title>
              <DialogPrimitive.Description className="mt-1 text-sm text-muted-foreground">
                {isFirstConsent
                  ? t('customer_reconsent.intro_first')
                  : t('customer_reconsent.intro_update')}
              </DialogPrimitive.Description>
            </div>
          </div>

          {!isFirstConsent && (
            <div className="mt-4 rounded-md border border-blue-200 bg-blue-50 p-3 text-sm text-blue-900 dark:border-blue-900/40 dark:bg-blue-900/20 dark:text-blue-100">
              <p className="font-medium">
                {t('customer_reconsent.what_changed_title')}
              </p>
              <p className="mt-1 text-blue-800 dark:text-blue-200">
                {t('customer_reconsent.what_changed_body')}
              </p>
            </div>
          )}

          {slug && (
            <div className="mt-4 flex flex-col gap-2 text-sm">
              <a
                href={`/s/${encodeURIComponent(slug)}/privacy`}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-blue-600 underline-offset-2 hover:underline"
              >
                <ExternalLink className="h-3.5 w-3.5" />
                {t('customer_reconsent.read_privacy')}
              </a>
              <a
                href={`/s/${encodeURIComponent(slug)}/terms`}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-blue-600 underline-offset-2 hover:underline"
              >
                <ExternalLink className="h-3.5 w-3.5" />
                {t('customer_reconsent.read_terms')}
              </a>
            </div>
          )}

          <label className="mt-5 flex cursor-pointer items-start gap-2 rounded-md border p-3 hover:bg-muted/40">
            <input
              type="checkbox"
              checked={checked}
              onChange={(e) => setChecked(e.target.checked)}
              disabled={submitting}
              className="mt-0.5 h-4 w-4 cursor-pointer accent-blue-600"
            />
            <span className="text-sm leading-snug">
              {t('customer_reconsent.checkbox_label')}
            </span>
          </label>

          {error && (
            <div className="mt-3 rounded-md border border-red-200 bg-red-50 p-2 text-xs text-red-700">
              {error}
            </div>
          )}

          {customer?.current_store_legal_version && (
            <p className="mt-3 text-[11px] text-muted-foreground">
              {t('customer_reconsent.version_notice', {
                version: customer.current_store_legal_version,
              })}
            </p>
          )}

          <div className="mt-5 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
            <button
              type="button"
              onClick={handleLogout}
              disabled={submitting}
              className="inline-flex items-center justify-center gap-1.5 rounded-md border border-input bg-background px-4 py-2 text-sm font-medium hover:bg-accent disabled:opacity-50"
            >
              <LogOut className="h-4 w-4" />
              {t('customer_reconsent.logout_button')}
            </button>
            <button
              type="button"
              onClick={handleAccept}
              disabled={!checked || submitting}
              className="inline-flex items-center justify-center gap-1.5 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
              {submitting
                ? t('customer_reconsent.accepting')
                : t('customer_reconsent.accept_button')}
            </button>
          </div>
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}
