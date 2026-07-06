/**
 * OutreachConfirmDialog — preview the rendered subject + body and
 * give the merchant THREE ways to send:
 *
 *   1. Open default mail client (mailto:) — best UX when the
 *      merchant has Apple Mail / Outlook / Thunderbird installed.
 *   2. Open Gmail web compose — works for the (large) cohort of
 *      Gmail-on-browser users who never registered Gmail as a
 *      mailto: handler. Without this option the mailto: button
 *      silently does nothing for them.
 *   3. Copy to clipboard — last-resort fallback. The merchant pastes
 *      into whatever they use.
 *
 * For WhatsApp the modal collapses to a single "Apri WhatsApp" button
 * since wa.me works uniformly across desktop/mobile.
 */
import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from './ui/dialog';
import { Button } from './ui/button';
import { Mail, MessageCircle, ExternalLink, Copy, Check } from 'lucide-react';

export function OutreachConfirmDialog({
  open,
  onOpenChange,
  channel,        // 'mailto' | 'whatsapp'
  recipient,      // email or phone display string
  subject,        // rendered (locale-aware) subject; mailto only
  body,           // rendered body
  url,            // backend-built deep-link
}) {
  const { t } = useTranslation('customerInsights');
  const [copied, setCopied] = useState(false);

  const isEmail = channel === 'mailto';

  const onCopy = async () => {
    const text = isEmail && subject ? `${subject}\n\n${body}` : body;
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // ignore
    }
  };

  const onOpenMailto = () => {
    if (url) window.location.href = url;
    onOpenChange(false);
  };

  const onOpenGmailWeb = () => {
    if (!isEmail) return;
    const params = new URLSearchParams({
      view: 'cm',
      fs: '1',
      to: recipient || '',
      su: subject || '',
      body: body || '',
    });
    window.open(`https://mail.google.com/mail/?${params.toString()}`, '_blank', 'noopener,noreferrer');
    onOpenChange(false);
  };

  const onOpenOutlookWeb = () => {
    if (!isEmail) return;
    const params = new URLSearchParams({
      to: recipient || '',
      subject: subject || '',
      body: body || '',
    });
    window.open(`https://outlook.live.com/mail/0/deeplink/compose?${params.toString()}`, '_blank', 'noopener,noreferrer');
    onOpenChange(false);
  };

  const onOpenWhatsApp = () => {
    if (url) window.open(url, '_blank', 'noopener,noreferrer');
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-base">
            {isEmail ? <Mail className="h-4 w-4" /> : <MessageCircle className="h-4 w-4" />}
            {isEmail
              ? t('outreach.dialog.titleEmail', { defaultValue: 'Anteprima email' })
              : t('outreach.dialog.titleWhatsapp', { defaultValue: 'Anteprima WhatsApp' })}
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-3">
          {/* Recipient */}
          <div className="text-xs">
            <span className="text-muted-foreground mr-1">
              {t('outreach.dialog.toLabel', { defaultValue: 'A:' })}
            </span>
            <span className="font-mono">{recipient || '—'}</span>
          </div>

          {/* Subject (email only) */}
          {isEmail && (
            <div>
              <p className="text-[10px] uppercase tracking-wide text-muted-foreground mb-1">
                {t('outreach.dialog.subjectLabel', { defaultValue: 'Oggetto' })}
              </p>
              <p className="text-sm font-medium border border-border rounded p-2 bg-muted/20">
                {subject || '—'}
              </p>
            </div>
          )}

          {/* Body */}
          <div>
            <p className="text-[10px] uppercase tracking-wide text-muted-foreground mb-1">
              {t('outreach.dialog.bodyLabel', { defaultValue: 'Messaggio' })}
            </p>
            <pre className="text-xs font-sans whitespace-pre-wrap border border-border rounded p-3 bg-muted/10 max-h-64 overflow-y-auto">
              {body}
            </pre>
          </div>

          {/* Hint — explain the 3 ways we offer for sending */}
          {isEmail && (
            <p className="text-[11px] text-muted-foreground leading-relaxed">
              {t('outreach.dialog.hint', {
                defaultValue:
                  'Gmail web e Outlook web aprono il compose nel tuo browser (sempre funziona). "Mail di default" funziona solo se hai un programma email come predefinito di sistema.',
              })}
            </p>
          )}
        </div>

        <DialogFooter className="flex flex-col-reverse sm:flex-row sm:justify-between gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={onCopy}
            className="text-xs"
          >
            {copied ? (
              <><Check className="h-3.5 w-3.5 mr-1.5" />
              {t('outreach.dialog.copied', { defaultValue: 'Copiato' })}</>
            ) : (
              <><Copy className="h-3.5 w-3.5 mr-1.5" />
              {t('outreach.dialog.copy', { defaultValue: 'Copia testo' })}</>
            )}
          </Button>

          <div className="flex gap-2 flex-wrap justify-end">
            {isEmail && (
              <>
                {/* Default = Gmail web because it's the broadest-working
                    path: any browser, no OS handler config required. */}
                <Button
                  variant="default"
                  size="sm"
                  onClick={onOpenGmailWeb}
                  className="text-xs"
                >
                  <ExternalLink className="h-3.5 w-3.5 mr-1.5" />
                  {t('outreach.dialog.openGmail', { defaultValue: 'Apri Gmail web' })}
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={onOpenOutlookWeb}
                  className="text-xs"
                >
                  <ExternalLink className="h-3.5 w-3.5 mr-1.5" />
                  {t('outreach.dialog.openOutlook', { defaultValue: 'Apri Outlook web' })}
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={onOpenMailto}
                  className="text-xs"
                  title={t('outreach.dialog.mailtoTooltip', {
                    defaultValue: 'Apre il programma email impostato come predefinito sul sistema (Mail / Outlook / Thunderbird). Funziona solo se ne hai uno configurato.',
                  })}
                >
                  <Mail className="h-3.5 w-3.5 mr-1.5" />
                  {t('outreach.dialog.openDefault', { defaultValue: 'Mail di default' })}
                </Button>
              </>
            )}
            {!isEmail && (
              <Button
                variant="default"
                size="sm"
                onClick={onOpenWhatsApp}
                className="text-xs"
              >
                <MessageCircle className="h-3.5 w-3.5 mr-1.5" />
                {t('outreach.dialog.openWhatsApp', { defaultValue: 'Apri WhatsApp' })}
              </Button>
            )}
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default OutreachConfirmDialog;
