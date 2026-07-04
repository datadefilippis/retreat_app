/**
 * OutreachActions — Phase 3 button row for a single customer.
 *
 * Shows up to 3 buttons (Email / WhatsApp / Promemoria) gated by
 * what the customer supports:
 *   • mailto    → enabled when customer has email
 *   • whatsapp  → enabled when customer.phone normalises to E.164
 *                 (the backend supports() check is the source of
 *                 truth — frontend pre-filters for instant feedback
 *                 but the API would also reject an unsupported click).
 *   • task      → Phase 4 (placeholder for now)
 *
 * Click flow: open the template picker, user picks one, we hit
 * /actions/outreach which (a) renders the subject+body in the active
 * locale, (b) builds the deep-link URL, (c) logs the audit entry,
 * (d) returns the URL we open in a new tab.
 */
import React, { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Mail, MessageCircle } from 'lucide-react';
import { Button } from '../../../components/ui/button';
import { customerInsightsAPI } from '../../../api/customerInsights';
import { OutreachConfirmDialog } from './OutreachConfirmDialog';

// Defaults for the per-channel "quick send" template if the user just
// clicks the button without opening the picker. Aligned to the merchant's
// most likely intent for that channel + that customer status.
const QUICK_TEMPLATE_BY_INTENT = {
  at_risk_followup: 'at_risk_followup',
  new_welcome: 'new_welcome',
  top_personal_note: 'top_personal_note',
  default: 'general_check_in',
};

export const OutreachActions = ({ customer, suggestedIntent = 'default', compact = false }) => {
  const { t, i18n } = useTranslation('customerInsights');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [confirmDialog, setConfirmDialog] = useState(null);

  // Derive support flags client-side (matches backend supports()).
  const hasEmail = !!(customer?.email && customer.email.trim());
  const hasPhone = !!(customer?.phone && customer.phone.trim());

  const quickTemplate = useMemo(
    () => QUICK_TEMPLATE_BY_INTENT[suggestedIntent] || QUICK_TEMPLATE_BY_INTENT.default,
    [suggestedIntent],
  );

  const fireOutreach = async (channel, templateKey) => {
    if (!customer) return;
    setBusy(true);
    setError(null);
    try {
      const res = await customerInsightsAPI.buildOutreach({
        customerId: customer.customer_id || customer.id,
        channel,
        template: templateKey,
        locale: i18n.language,
      });
      // Open the confirm dialog with the rendered preview. The
      // merchant picks how to send (default mail / Gmail web /
      // WhatsApp / copy text). This avoids the silent-fail of
      // mailto: when no default handler is configured.
      setConfirmDialog({
        channel,
        recipient: channel === 'mailto' ? customer.email : customer.phone,
        subject: res.data?.subject || '',
        body: res.data?.body || res.data?.preview || '',
        url: res.data?.url,
      });
    } catch (err) {
      const detail = err?.response?.data?.detail;
      setError(typeof detail === 'string' ? detail : err?.message || 'unknown');
    } finally {
      setBusy(false);
    }
  };

  const sizeClass = compact ? 'h-7 text-xs' : 'h-8 text-xs';

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-1.5">
        <Button
          size="sm"
          variant="default"
          className={sizeClass}
          disabled={!hasEmail || busy}
          onClick={() => fireOutreach('mailto', quickTemplate)}
          title={!hasEmail ? t('outreach.noEmail') : undefined}
        >
          <Mail className="h-3.5 w-3.5 mr-1.5" />
          {t('outreach.emailButton')}
        </Button>

        <Button
          size="sm"
          variant="secondary"
          className={sizeClass}
          disabled={!hasPhone || busy}
          onClick={() => fireOutreach('whatsapp', quickTemplate)}
          title={!hasPhone ? t('outreach.noPhone') : undefined}
        >
          <MessageCircle className="h-3.5 w-3.5 mr-1.5" />
          {t('outreach.whatsappButton')}
        </Button>

      </div>

      {error && (
        <p className="text-xs text-red-600">
          {String(error)}
        </p>
      )}

      {/* Confirm dialog — preview + 3 send options (default mail /
          Gmail web / copy) for mailto, or single button for whatsapp */}
      {confirmDialog && (
        <OutreachConfirmDialog
          open={!!confirmDialog}
          onOpenChange={(o) => { if (!o) setConfirmDialog(null); }}
          channel={confirmDialog.channel}
          recipient={confirmDialog.recipient}
          subject={confirmDialog.subject}
          body={confirmDialog.body}
          url={confirmDialog.url}
        />
      )}

    </div>
  );
};

export default OutreachActions;
