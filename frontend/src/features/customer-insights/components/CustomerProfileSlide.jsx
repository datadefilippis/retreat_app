/**
 * CustomerProfileSlide — drill-down slide-over for a single customer.
 *
 * Loads the timeline lazily on open. Displays the materialized
 * metrics block on top, then a chronological event stream
 * (orders + sales) below. Phase 3 will add the action buttons
 * (email / WhatsApp / task) inline at the top.
 */
import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '../../../components/ui/sheet';
import { Skeleton } from '../../../components/ui/skeleton';
import { Button } from '../../../components/ui/button';
import {
  Mail, Phone,
  // CI-admin-vis: account/marketing section icons.
  UserCheck, UserX, CheckCircle2, XCircle,
} from 'lucide-react';
import { customerInsightsAPI } from '../../../api/customerInsights';
import { useCurrency } from '../../../context/AuthContext';
import { formatCurrency } from '../../../lib/utils';
import { OutreachActions } from './OutreachActions';

export const CustomerProfileSlide = ({ customerId, customerSummary, open, onOpenChange }) => {
  const { t } = useTranslation('customerInsights');
  const currency = useCurrency();
  const [timeline, setTimeline] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!open || !customerId) return;
    let cancelled = false;
    setLoading(true);
    customerInsightsAPI.getCustomerTimeline(customerId, { limit: 50 })
      .then((res) => {
        if (cancelled) return;
        setTimeline(res.data?.events || []);
      })
      .catch(() => {
        if (cancelled) return;
        setTimeline([]);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, [open, customerId]);

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="sm:max-w-md w-full overflow-y-auto">
        <SheetHeader>
          <SheetTitle className="text-base">
            {customerSummary?.customer_name || t('profile.title')}
          </SheetTitle>
        </SheetHeader>

        <div className="mt-4 space-y-5">
          {/* Contact strip — always visible at the top so the merchant
              can quickly read the email/phone without hunting through
              the metrics. Each row is its own copy-to-clipboard target. */}
          <ContactStrip
            email={customerSummary?.email}
            phone={customerSummary?.phone}
            t={t}
          />

          {/* Headline metrics */}
          <div className="grid grid-cols-2 gap-3 text-sm">
            <Stat
              label={t('profile.totalRevenue')}
              value={
                customerSummary?.total_revenue != null
                  ? formatCurrency(customerSummary.total_revenue, currency)
                  : '\u2014'
              }
            />
            <Stat
              label={t('profile.transactionCount')}
              value={customerSummary?.transaction_count ?? '\u2014'}
            />
            <Stat
              label={t('profile.avgValue')}
              value={
                customerSummary?.avg_transaction_value != null
                  ? formatCurrency(customerSummary.avg_transaction_value, currency)
                  : '\u2014'
              }
            />
            <Stat
              label={t('profile.lastPurchase')}
              value={customerSummary?.last_purchase_date || '\u2014'}
            />
          </div>

          {/* CI-admin-vis: Account + marketing section.
              Renders the registration date (if the customer has an
              account) and the current marketing consent state with the
              same iconography used in the table column. Sits between
              metrics and outreach so the merchant can decide WHO to
              contact and HOW (e.g. don't add an opted-out customer to
              a newsletter campaign). */}
          <AccountSection
            customer={customerSummary}
            t={t}
            i18nLang={null}
          />

          {/* Phase 3: outreach action buttons (deep links). The
              suggested intent is derived from the customer's status so
              the "quick send" button uses the right template. */}
          <OutreachActions
            customer={customerSummary}
            suggestedIntent={
              customerSummary?.customer_status === 'at_risk' ? 'at_risk_followup'
                : customerSummary?.segment === 'new'         ? 'new_welcome'
                : customerSummary?.segment === 'top'         ? 'top_personal_note'
                : 'default'
            }
          />

          {/* Timeline */}
          <div>
            <h4 className="text-sm font-semibold mb-2">{t('profile.timelineTitle')}</h4>
            {loading ? (
              <div className="space-y-2">
                {[...Array(4)].map((_, i) => (
                  <Skeleton key={i} className="h-12 w-full" />
                ))}
              </div>
            ) : timeline.length === 0 ? (
              <p className="text-xs text-muted-foreground">
                {t('profile.timelineEmpty')}
              </p>
            ) : (
              <ul className="space-y-1.5">
                {timeline.map((e, i) => (
                  <li
                    key={i}
                    className="flex items-center justify-between text-xs px-2 py-1.5 rounded border border-border hover:bg-muted/40"
                  >
                    <div className="flex items-center gap-2 min-w-0">
                      <span className="text-[10px] uppercase tracking-wide text-muted-foreground shrink-0">
                        {e.kind === 'order' ? t('profile.kindOrder') : t('profile.kindSale')}
                      </span>
                      <span className="text-foreground truncate">
                        {e.description || e.order_number || e.product_id || '\u2014'}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <span className="text-muted-foreground">{e.date || '\u2014'}</span>
                      <span className="font-medium tabular-nums">
                        {e.amount != null
                          ? formatCurrency(e.amount, e.currency || currency)
                          : '\u2014'}
                      </span>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
};

/**
 * AccountSection — Wave GDPR-Commerce CI-admin-vis.
 *
 * Surfaces the 3 fields the table-row carries (has_account,
 * marketing_opted_in, account_created_at) in human-readable form.
 *
 * 2026-05-20 — Marketing status is now ORTHOGONAL to has_account
 * (the checkout opt-in fix made guest opt-in legitimate; commit
 * d1a1d3b). We render Account and Marketing as two independent
 * lines so a guest with a marketing opt-in shows green correctly.
 *
 * Date rendering goes through the browser locale via toLocaleDateString
 * so an admin in Italian sees DD/MM/YYYY, in English MM/DD/YYYY etc.
 */
function AccountSection({ customer, t }) {
  if (!customer) return null;

  const hasAccount = !!customer.has_account;
  const optedIn = !!customer.marketing_opted_in;
  const accountCreatedAt = customer.account_created_at || null;

  let registeredDateStr = null;
  if (accountCreatedAt) {
    try {
      registeredDateStr = new Date(accountCreatedAt).toLocaleDateString();
    } catch {
      registeredDateStr = accountCreatedAt;
    }
  }

  return (
    <div className="rounded-md border border-border p-2.5 space-y-1.5">
      <p className="text-[10px] uppercase tracking-wide text-muted-foreground">
        {t('profile.accountSection', { defaultValue: 'Account' })}
      </p>

      {/* Account registration line — independent from marketing */}
      {hasAccount ? (
        <div className="flex items-center gap-2 text-sm">
          <UserCheck className="h-4 w-4 text-emerald-600 dark:text-emerald-400 shrink-0" />
          <span>
            {t('profile.accountRegistered', { defaultValue: 'Account registrato' })}
            {registeredDateStr && (
              <span className="text-muted-foreground">
                {' · '}
                {t('profile.accountRegisteredOn', {
                  defaultValue: 'dal {{date}}',
                  date: registeredDateStr,
                })}
              </span>
            )}
          </span>
        </div>
      ) : (
        <div className="flex items-center gap-2 text-sm">
          <UserX className="h-4 w-4 text-muted-foreground shrink-0" />
          <span className="text-muted-foreground">
            {t('profile.accountGuest', { defaultValue: 'Cliente guest (nessun account registrato)' })}
          </span>
        </div>
      )}

      {/* Marketing line — independent from has_account.
          2026-05-20: a guest can legitimately be opted-in via the
          checkout box, so we show the green check whenever
          marketing_opted_in is true regardless of registration. */}
      {optedIn ? (
        <div className="flex items-center gap-2 text-sm">
          <CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400 shrink-0" />
          <span>
            {t('profile.marketingOptedIn', { defaultValue: 'Iscritto al marketing' })}
          </span>
        </div>
      ) : hasAccount ? (
        <div className="flex items-center gap-2 text-sm">
          <XCircle className="h-4 w-4 text-red-600 dark:text-red-400 shrink-0" />
          <span className="text-muted-foreground">
            {t('profile.marketingNotOptedIn', { defaultValue: 'Non iscritto al marketing' })}
          </span>
        </div>
      ) : null /* guest + not opted-in: omit the marketing line entirely;
                   the absence is informative without adding clutter. */}
    </div>
  );
}


function Stat({ label, value }) {
  return (
    <div className="rounded-md border border-border p-2.5">
      <p className="text-[10px] uppercase tracking-wide text-muted-foreground">
        {label}
      </p>
      <p className="font-heading text-base font-semibold mt-0.5">
        {value}
      </p>
    </div>
  );
}


/**
 * ContactStrip — readable email + phone with click-to-copy.
 *
 * The merchant told us flat out: "voglio comunque che si vedessero in
 * maniera leggibile email e telefono". So we put them at the very top
 * of the slide-over with icons + monospace value + copy-on-click.
 *
 * If a field is missing, render the slot with the em-dash + a muted
 * label, so the merchant learns "this customer has no email" instead
 * of just seeing nothing.
 */
function ContactStrip({ email, phone, t }) {
  return (
    <div className="rounded-md border border-border p-2.5 space-y-1.5">
      <ContactRow
        icon={Mail}
        label={t('profile.emailLabel', { defaultValue: 'Email' })}
        value={email}
        emptyLabel={t('profile.noEmail', { defaultValue: 'nessuna email' })}
      />
      <ContactRow
        icon={Phone}
        label={t('profile.phoneLabel', { defaultValue: 'Telefono' })}
        value={phone}
        emptyLabel={t('profile.noPhone', { defaultValue: 'nessun telefono' })}
      />
    </div>
  );
}


function ContactRow({ icon: Icon, label, value, emptyLabel }) {
  const [copied, setCopied] = React.useState(false);

  const onCopy = async () => {
    if (!value) return;
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      setTimeout(() => setCopied(false), 1200);
    } catch {
      // Clipboard API may be unavailable on http:// origins or in
      // private windows — fail silently, the user can still select
      // the text manually.
    }
  };

  return (
    <div className="flex items-center justify-between gap-2 text-sm">
      <div className="flex items-center gap-2 min-w-0 flex-1">
        <Icon className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
        <span className="text-[10px] uppercase tracking-wide text-muted-foreground shrink-0 w-14">
          {label}
        </span>
        {value ? (
          <button
            onClick={onCopy}
            type="button"
            className="font-mono text-xs text-foreground hover:text-primary transition-colors truncate text-left"
            title={copied ? '✓' : value}
          >
            {value}
          </button>
        ) : (
          <span className="text-xs text-muted-foreground italic">
            {emptyLabel}
          </span>
        )}
      </div>
      {value && copied && (
        <span className="text-[11px] text-emerald-600 shrink-0">✓</span>
      )}
    </div>
  );
}

export default CustomerProfileSlide;
