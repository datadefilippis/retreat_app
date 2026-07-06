/**
 * ContactActions — l'azione accanto all'insight (CF2, INSIGHTS_ACTION_PLAN).
 *
 * Due icon-button (WhatsApp / Email) da mettere INLINE ovunque ci sia
 * una persona da contattare: riga pagamento in ritardo, partecipante,
 * cliente da ricontattare. Il click chiama POST /outreach/build che
 * compone il messaggio contestuale nella lingua giusta e restituisce
 * il deep-link; il dialog mostra l'anteprima e l'operatore decide.
 * Nessun invio automatico: l'ultimo gesto è sempre umano.
 *
 * Contesti: payment_reminder | pre_retreat | post_retreat_review |
 * winback | generic. Il winback è marketing → il backend lo blocca
 * (403 no_marketing_consent) senza consenso; qui pre-disabilitiamo
 * col tooltip se marketingConsent è passato esplicitamente false.
 */
import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Mail, MessageCircle } from 'lucide-react';
import { toast } from 'sonner';
import api from '../api/client';
import { OutreachConfirmDialog } from './OutreachConfirmDialog';

export default function ContactActions({
  name,
  email,
  phone,
  customerId,
  context = 'generic',
  vars,
  marketingConsent,          // undefined = non noto (decide il backend)
  size = 'sm',               // 'sm' | 'md'
}) {
  const { t, i18n } = useTranslation('common');
  const [busy, setBusy] = useState(false);
  const [confirm, setConfirm] = useState(null);

  const hasEmail = Boolean(email && String(email).trim());
  const hasPhone = Boolean(phone && String(phone).trim());
  const consentBlocked = context === 'winback' && marketingConsent === false;

  const fire = async (channel) => {
    setBusy(true);
    try {
      const res = await api.post('/outreach/build', {
        context,
        channel,
        locale: i18n.language,
        customer_id: customerId || undefined,
        contact_name: customerId ? undefined : name,
        contact_email: customerId ? undefined : email,
        contact_phone: customerId ? undefined : phone,
        vars: vars || undefined,
      });
      setConfirm({
        channel,
        recipient: channel === 'mailto' ? email : phone,
        subject: res.data?.subject || '',
        body: res.data?.body || '',
        url: res.data?.url,
      });
    } catch (err) {
      const detail = err?.response?.data?.detail;
      const code = typeof detail === 'object' ? detail?.error : null;
      toast.error(
        code === 'no_marketing_consent'
          ? t('outreachShared.noConsent', { defaultValue: 'Questo cliente non ha dato il consenso marketing' })
          : t('outreachShared.error', { defaultValue: 'Impossibile preparare il messaggio, riprova' }),
      );
    } finally {
      setBusy(false);
    }
  };

  const btnCls = `inline-flex items-center justify-center rounded-lg border transition-colors disabled:opacity-35 disabled:cursor-not-allowed ${
    size === 'md' ? 'h-9 w-9' : 'h-7 w-7'}`;
  const iconCls = size === 'md' ? 'h-4.5 w-4.5' : 'h-3.5 w-3.5';

  const waTitle = !hasPhone
    ? t('outreachShared.noPhone', { defaultValue: 'Nessun telefono' })
    : consentBlocked
      ? t('outreachShared.noConsent', { defaultValue: 'Questo cliente non ha dato il consenso marketing' })
      : t('outreachShared.whatsapp', { defaultValue: 'Scrivi su WhatsApp' });
  const mailTitle = !hasEmail
    ? t('outreachShared.noEmail', { defaultValue: 'Nessuna email' })
    : consentBlocked
      ? t('outreachShared.noConsent', { defaultValue: 'Questo cliente non ha dato il consenso marketing' })
      : t('outreachShared.email', { defaultValue: 'Scrivi una email' });

  return (
    <span className="inline-flex items-center gap-1.5" data-testid="contact-actions">
      <button
        type="button"
        className={`${btnCls} border-[#376254]/40 text-[#376254] hover:bg-[#376254]/10`}
        disabled={!hasPhone || consentBlocked || busy}
        onClick={() => fire('whatsapp')}
        title={waTitle}
        aria-label={waTitle}
      >
        <MessageCircle className={iconCls} aria-hidden />
      </button>
      <button
        type="button"
        className={`${btnCls} border-border text-muted-foreground hover:bg-secondary`}
        disabled={!hasEmail || consentBlocked || busy}
        onClick={() => fire('mailto')}
        title={mailTitle}
        aria-label={mailTitle}
      >
        <Mail className={iconCls} aria-hidden />
      </button>

      {confirm && (
        <OutreachConfirmDialog
          open={Boolean(confirm)}
          onOpenChange={(o) => { if (!o) setConfirm(null); }}
          channel={confirm.channel}
          recipient={confirm.recipient}
          subject={confirm.subject}
          body={confirm.body}
          url={confirm.url}
        />
      )}
    </span>
  );
}
