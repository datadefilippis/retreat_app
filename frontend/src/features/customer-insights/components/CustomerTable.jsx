/**
 * CustomerTable — paginated listing with all filter chain wired in.
 *
 * Columns (compact desktop view):
 *   Name | Segment | Status | Revenue | # Tx | Last purchase | Risk | Trend
 *
 * Mobile collapses to: Name + Segment + Risk badge.
 *
 * Each row triggers ``onSelectCustomer(customerId)`` so the parent
 * page can open the slide-over profile.
 *
 * Phase-3 hook: an actions column will be added later (email /
 * WhatsApp / task buttons). Today we render a "Profilo" link.
 */
import React from 'react';
import { useTranslation } from 'react-i18next';
import { Card, CardContent, CardHeader, CardTitle } from '../../../components/ui/card';
import { Skeleton } from '../../../components/ui/skeleton';
import { Button } from '../../../components/ui/button';
import { Badge } from '../../../components/ui/badge';
import {
  ChevronLeft, ChevronRight, ExternalLink, Download,
  // CI-admin-vis: icons for the two new columns (Marketing + Account).
  CheckCircle2, XCircle, UserCheck, UserX, Minus,
  // Piece 1b banner — GDPR hint about the unsubscribe_url merge tag.
  ShieldCheck,
} from 'lucide-react';
import { useCurrency } from '../../../context/AuthContext';
import { formatCurrency } from '../../../lib/utils';
import { SegmentFilters } from './SegmentFilters';
import ContactActions from '../../../components/ContactActions';

const SEGMENT_VARIANT = {
  top: 'default',
  active: 'default',
  occasional: 'secondary',
  inactive: 'outline',
  new: 'default',
};

const STATUS_COLOR = {
  healthy: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300',
  watch: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300',
  at_risk: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300',
  lost: 'bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-300',
};

const TREND_GLYPH = {
  growing: '↑',
  declining: '↓',
  stable: '→',
  new: '✦',
};

export const CustomerTable = ({
  data,
  loading,
  page,
  pageSize,
  onPageChange,
  onSelectCustomer,
  onExportCsv,
  // Filters live INSIDE the table — they only affect the row set,
  // not the KPIs above. Keeping them on the table card prevents the
  // misleading "this filter changed my KPI cards" UX confusion.
  segment,
  onSegmentChange,
  customerStatus,
  onStatusChange,
  // CI-admin-vis: two new filter prop pairs. The setters are optional —
  // if the parent doesn't pass them, the corresponding chip row in
  // <SegmentFilters /> doesn't render (backward compat for any legacy
  // caller that doesn't know about these filters yet).
  hasAccount = null,
  onHasAccountChange,
  marketingOptedIn = null,
  onMarketingOptedInChange,
}) => {
  const { t } = useTranslation('customerInsights');
  const currency = useCurrency();

  const totalPages = Math.max(1, Math.ceil((data?.total || 0) / (pageSize || 50)));

  return (
    <Card>
      <CardHeader className="space-y-3 pb-3">
        <div className="flex flex-row items-center justify-between space-y-0">
          <div>
            <CardTitle className="text-base">{t('table.title')}</CardTitle>
            {!loading && data?.total != null ? (
              <p className="text-xs text-muted-foreground mt-0.5">
                {t('table.totalCount', { count: data.total })}
              </p>
            ) : null}
          </div>
          <Button
            size="sm"
            variant="outline"
            onClick={onExportCsv}
            disabled={loading || !data?.total}
            className="h-8 text-xs"
          >
            <Download className="h-3.5 w-3.5 mr-1.5" />
            {t('table.exportCsv')}
          </Button>
        </div>
        {/* Wave GDPR-Commerce Piece 1b (2026-05-19) — operator hint.
            The CSV now includes an ``unsubscribe_url`` column with a
            signed token per row. Mailchimp / Brevo / Sendgrid consume
            it as a merge tag in the campaign footer to satisfy GDPR
            Art. 7(3) (the revoke link must be in every marketing email
            for the consent chain to be operationally compliant — the
            tech is in place, the merchant needs to wire it up). Shown
            only when there's data to export so it doesn't clutter the
            empty state. */}
        {!loading && data?.total > 0 && (
          <div className="flex items-start gap-2 rounded-md border border-blue-200 bg-blue-50 px-3 py-2 text-xs text-blue-900 dark:border-blue-900/40 dark:bg-blue-900/20 dark:text-blue-200">
            <ShieldCheck className="h-3.5 w-3.5 mt-0.5 shrink-0" />
            <span className="leading-snug">
              {t('table.exportCsvGdprHint', {
                defaultValue:
                  'Il CSV include una colonna unsubscribe_url. Inseriscila come merge tag nei footer delle campagne marketing (es. Mailchimp / Brevo) per rispettare l\'Art. 7(3) GDPR.',
              })}
            </span>
          </div>
        )}
        {/* Filters live in the table card — they only affect the row
            set below, NOT the KPI grid above the table. */}
        {onSegmentChange && (
          <div className="pt-1 border-t border-border">
            <div className="pt-2">
              <SegmentFilters
                selectedSegment={segment}
                onSegmentChange={onSegmentChange}
                selectedStatus={customerStatus}
                onStatusChange={onStatusChange}
                selectedHasAccount={hasAccount}
                onHasAccountChange={onHasAccountChange}
                selectedMarketingOptedIn={marketingOptedIn}
                onMarketingOptedInChange={onMarketingOptedInChange}
              />
            </div>
          </div>
        )}
      </CardHeader>
      <CardContent className="p-0">
        {loading ? (
          <div className="px-4 py-3 space-y-2">
            {[...Array(5)].map((_, i) => (
              <Skeleton key={i} className="h-9 w-full" />
            ))}
          </div>
        ) : !data?.rows || data.rows.length === 0 ? (
          <div className="px-4 py-12 text-center text-sm text-muted-foreground">
            {t('table.noResults')}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-muted/40 text-xs text-muted-foreground">
                <tr>
                  <th className="text-left px-4 py-2 font-medium">{t('table.columnName')}</th>
                  <th className="text-left px-3 py-2 font-medium hidden md:table-cell">{t('table.columnSegment')}</th>
                  <th className="text-left px-3 py-2 font-medium hidden md:table-cell">{t('table.columnStatus')}</th>
                  <th className="text-right px-3 py-2 font-medium">{t('table.columnRevenue')}</th>
                  <th className="text-right px-3 py-2 font-medium hidden lg:table-cell">{t('table.columnTransactions')}</th>
                  <th className="text-left px-3 py-2 font-medium hidden lg:table-cell">{t('table.columnLastPurchase')}</th>
                  <th className="text-center px-3 py-2 font-medium hidden md:table-cell">{t('table.columnChurnRisk')}</th>
                  <th className="text-center px-3 py-2 font-medium hidden md:table-cell">{t('table.columnTrend')}</th>
                  {/* CI-admin-vis: 2 new columns at lg+ breakpoint to
                      avoid squashing on tablet. They follow the same
                      ``hidden lg:table-cell`` pattern as "# Tx" and
                      "Last purchase" — no mobile impact. */}
                  <th className="text-center px-3 py-2 font-medium hidden lg:table-cell">{t('table.columnAccount', { defaultValue: 'Account' })}</th>
                  <th className="text-center px-3 py-2 font-medium hidden lg:table-cell">{t('table.columnMarketing', { defaultValue: 'Marketing' })}</th>
                  {/* CF6 — l'azione accanto all'insight: contatto one-click */}
                  <th className="text-center px-3 py-2 font-medium">{t('table.columnContact', { defaultValue: 'Contatta' })}</th>
                  <th className="text-right px-4 py-2 font-medium"></th>
                </tr>
              </thead>
              <tbody>
                {data.rows.map((row) => (
                  <tr
                    key={row.customer_id}
                    className="border-t border-border hover:bg-muted/30 transition-colors"
                  >
                    <td className="px-4 py-2 font-medium truncate max-w-xs" title={row.customer_name}>
                      {row.customer_name || row.customer_id?.slice(0, 8)}
                    </td>
                    <td className="px-3 py-2 hidden md:table-cell">
                      <Badge variant={SEGMENT_VARIANT[row.segment] || 'outline'}>
                        {t(`segment.${row.segment}`, { defaultValue: row.segment })}
                      </Badge>
                    </td>
                    <td className="px-3 py-2 hidden md:table-cell">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${STATUS_COLOR[row.customer_status] || ''}`}>
                        {t(`status.${camelStatus(row.customer_status)}`, { defaultValue: row.customer_status })}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-right tabular-nums">
                      {formatCurrency(row.total_revenue || 0, currency)}
                    </td>
                    <td className="px-3 py-2 text-right tabular-nums hidden lg:table-cell">
                      {row.transaction_count}
                    </td>
                    <td className="px-3 py-2 hidden lg:table-cell whitespace-nowrap text-muted-foreground">
                      {row.last_purchase_date || '\u2014'}
                    </td>
                    <td className="px-3 py-2 text-center hidden md:table-cell tabular-nums">
                      <RiskScore score={row.churn_risk_score} />
                    </td>
                    <td className="px-3 py-2 text-center hidden md:table-cell">
                      <span title={t(`trend.${row.trend_direction}`, { defaultValue: row.trend_direction })}>
                        {TREND_GLYPH[row.trend_direction] || '\u2014'}
                      </span>
                    </td>
                    {/* CI-admin-vis: Account column.
                          - has_account === true → green UserCheck icon
                          - has_account === false → muted "Guest" label
                        Tooltip carries the textual answer for assistive
                        tech (icons alone are not enough for a11y). */}
                    <td className="px-3 py-2 text-center hidden lg:table-cell">
                      {row.has_account ? (
                        <span
                          className="inline-flex items-center text-emerald-600 dark:text-emerald-400"
                          title={t('table.accountRegistered', { defaultValue: 'Account registrato' })}
                          aria-label={t('table.accountRegistered', { defaultValue: 'Account registrato' })}
                        >
                          <UserCheck className="h-4 w-4" />
                        </span>
                      ) : (
                        <span
                          className="inline-flex items-center gap-1 text-muted-foreground text-xs"
                          title={t('table.accountGuest', { defaultValue: 'Cliente guest' })}
                        >
                          <UserX className="h-3.5 w-3.5" />
                          <span>{t('table.guestShort', { defaultValue: 'Guest' })}</span>
                        </span>
                      )}
                    </td>
                    {/* Marketing column.
                        2026-05-20 — Updated trichotomy (the previous
                        "guest = always n/a" assumption was obsoleted
                        when the checkout opt-in fix (commit d1a1d3b)
                        made marketing opt-in possible for guests too):
                          - opted_in=true   → green check  (registered OR guest)
                          - opted_in=false + has_account=true  → red X (account
                            exists but never opted in / revoked)
                          - opted_in=false + has_account=false → muted "—" (guest
                            who never opted in — neutral, NOT a no-vote)
                        The primary discriminator is opted_in, not
                        has_account. Backend ``_resolve_account_state``
                        now produces opted_in=True for guests with a
                        CRM-recorded opt-in, so the green check is
                        legitimate for them. */}
                    <td className="px-3 py-2 text-center hidden lg:table-cell">
                      {row.marketing_opted_in ? (
                        <span
                          className="inline-flex items-center text-emerald-600 dark:text-emerald-400"
                          title={t('table.marketingOptedIn', { defaultValue: 'Iscritto al marketing' })}
                          aria-label={t('table.marketingOptedIn', { defaultValue: 'Iscritto al marketing' })}
                        >
                          <CheckCircle2 className="h-4 w-4" />
                        </span>
                      ) : row.has_account ? (
                        <span
                          className="inline-flex items-center text-red-600 dark:text-red-400"
                          title={t('table.marketingNotOptedIn', { defaultValue: 'Non iscritto al marketing' })}
                          aria-label={t('table.marketingNotOptedIn', { defaultValue: 'Non iscritto al marketing' })}
                        >
                          <XCircle className="h-4 w-4" />
                        </span>
                      ) : (
                        <span
                          className="inline-flex items-center text-muted-foreground"
                          title={t('table.marketingGuestNotOptedIn', {
                            defaultValue: 'Cliente guest (nessun consenso al marketing)',
                          })}
                        >
                          <Minus className="h-4 w-4" />
                        </span>
                      )}
                    </td>
                    <td className="px-3 py-2 text-center whitespace-nowrap">
                      <ContactActions
                        name={row.customer_name}
                        email={row.email}
                        phone={row.phone}
                        customerId={row.customer_id}
                        context={row.segment === 'inactive' ? 'winback' : 'generic'}
                        marketingConsent={row.segment === 'inactive' ? Boolean(row.marketing_opted_in) : undefined}
                      />
                    </td>
                    <td className="px-4 py-2 text-right">
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => onSelectCustomer(row.customer_id)}
                        className="h-7 text-xs"
                      >
                        <ExternalLink className="h-3 w-3 mr-1" />
                        {t('table.viewProfile')}
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {!loading && data?.total > pageSize && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-border text-xs">
            <span className="text-muted-foreground">
              {t('table.page', { current: page, total: totalPages })}
            </span>
            <div className="flex items-center gap-1">
              <Button
                size="sm"
                variant="outline"
                disabled={page <= 1}
                onClick={() => onPageChange(page - 1)}
                className="h-7"
              >
                <ChevronLeft className="h-3 w-3 mr-1" />
                {t('table.previousPage')}
              </Button>
              <Button
                size="sm"
                variant="outline"
                disabled={page >= totalPages}
                onClick={() => onPageChange(page + 1)}
                className="h-7"
              >
                {t('table.nextPage')}
                <ChevronRight className="h-3 w-3 ml-1" />
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

function camelStatus(s) {
  return s === 'at_risk' ? 'atRisk' : s;
}

function RiskScore({ score }) {
  if (score == null) return <span className="text-muted-foreground">\u2014</span>;
  const color =
    score >= 60 ? 'text-red-600' :
    score >= 30 ? 'text-amber-600' :
    'text-emerald-600';
  return <span className={`font-medium ${color}`}>{score}</span>;
}

export default CustomerTable;
