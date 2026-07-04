/**
 * DpaPage — Wave GDPR-Commerce Phase CG-7.
 *
 * Admin page at ``/settings/legal/dpa`` that renders the Data
 * Processing Agreement between afianco (Processor) and the merchant
 * org (Controller), required by GDPR Art. 28.
 *
 * Behaviour
 * ---------
 * - Fetches the DPA in the admin's preferred locale (defaults to the
 *   user's UI language) via GET /api/legal/dpa?lang=xx — variables
 *   (merchant_name, merchant_email, merchant_country, org_id, date)
 *   are interpolated server-side from the user's organization doc.
 * - Renders via the existing LegalMarkdownRenderer.
 * - "Print / Save as PDF" button → ``window.print()``. Browser handles
 *   PDF generation natively — no WeasyPrint dependency.
 * - "Acknowledge receipt" button → POST /acknowledge (idempotent).
 *   First confirmation goes via a Dialog; subsequent calls are
 *   no-ops surfaced as toast.info.
 * - Status badge reflects current state: "Not yet acknowledged" or
 *   "Acknowledged on <date>".
 *
 * Locale switcher: 4 buttons let the admin preview the doc in each
 * language they may want to keep on file. The acknowledgement records
 * the locale that was visible at the moment of click.
 */

import React, { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { AppLayout, Header } from '../components/Layout';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from '../components/ui/dialog';
import { FileText, Printer, ShieldCheck, AlertCircle, Loader2, CheckCircle2 } from 'lucide-react';
import { toast } from 'sonner';

import LegalMarkdownRenderer from '../components/legal/LegalMarkdownRenderer';
import { dpaAPI } from '../api/auth';


const LOCALES = ['it', 'en', 'de', 'fr'];
const LOCALE_LABELS = { it: 'Italiano', en: 'English', de: 'Deutsch', fr: 'Français' };


export default function DpaPage() {
  const { t, i18n } = useTranslation('legal');

  // Locale of the rendered preview.
  const initialLocale = LOCALES.includes(i18n.language) ? i18n.language : 'it';
  const [locale, setLocale] = useState(initialLocale);

  const [doc, setDoc] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);

  const [statusDoc, setStatusDoc] = useState(null);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [acking, setAcking] = useState(false);

  // Load DPA content whenever locale changes.
  useEffect(() => {
    let active = true;
    setLoading(true);
    setLoadError(false);
    dpaAPI.get(locale).then(
      (data) => { if (active) { setDoc(data); setLoading(false); } },
      (err) => {
        console.error('DPA load failed:', err);
        if (active) { setLoadError(true); setLoading(false); }
      }
    );
    return () => { active = false; };
  }, [locale]);

  // Load acknowledgement status once on mount.
  useEffect(() => {
    let active = true;
    dpaAPI.status().then(
      (s) => { if (active) setStatusDoc(s); },
      (err) => { console.warn('DPA status fetch failed:', err); }
    );
    return () => { active = false; };
  }, []);

  const handleAcknowledge = useCallback(async () => {
    setConfirmOpen(false);
    if (acking) return;
    setAcking(true);
    try {
      const result = await dpaAPI.acknowledge(locale);
      if (result.status === 'already_acknowledged') {
        // Backend is idempotent — surface a soft info message.
        toast.info(t('dpa.ack_already_done'));
      } else {
        toast.success(t('dpa.ack_success'));
      }
      // Refresh the status badge.
      const fresh = await dpaAPI.status();
      setStatusDoc(fresh);
    } catch (err) {
      console.error('DPA acknowledge failed:', err);
      toast.error(t('dpa.ack_error'));
    } finally {
      setAcking(false);
    }
  }, [acking, locale, t]);

  const handlePrint = useCallback(() => {
    window.print();
  }, []);

  const acknowledged = !!(statusDoc && statusDoc.acknowledged);
  const ackDate = acknowledged && statusDoc.acknowledged_at
    ? new Date(statusDoc.acknowledged_at).toLocaleDateString(i18n.language)
    : null;

  return (
    <AppLayout>
      <Header title={t('dpa.page_title')} />

      {/* The wrapper below carries a ``print:show`` class so the
          on-screen chrome (back link, locale switcher, action buttons)
          collapses to a clean A4-style print. The print CSS rules
          live inline below for self-contained portability. */}
      <style>{`
        @media print {
          .no-print { display: none !important; }
          .print-only { display: block !important; }
          body { background: white !important; }
        }
        .print-only { display: none; }
      `}</style>

      <div className="max-w-4xl mx-auto px-4 py-6 space-y-4">
        <div className="no-print">
          <Link
            to="/store/settings"
            className="text-xs text-muted-foreground hover:underline"
          >
            {t('dpa.back_to_settings')}
          </Link>
          <p className="mt-2 text-sm text-muted-foreground">
            {t('dpa.page_subtitle')}
          </p>
        </div>

        {/* Status + locale switcher row */}
        <Card className="no-print">
          <CardContent className="p-4 flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-2">
              <ShieldCheck className="h-5 w-5 text-primary" />
              {acknowledged ? (
                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-100 text-emerald-800">
                  <CheckCircle2 className="h-3 w-3 mr-1" />
                  {t('dpa.status_acknowledged', { date: ackDate })}
                </span>
              ) : (
                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-800">
                  <AlertCircle className="h-3 w-3 mr-1" />
                  {t('dpa.status_not_acknowledged')}
                </span>
              )}
            </div>

            <div className="flex items-center gap-1 ml-auto">
              <span className="text-xs text-muted-foreground mr-1">
                {t('dpa.locale_label')}:
              </span>
              {LOCALES.map((loc) => (
                <button
                  key={loc}
                  type="button"
                  onClick={() => setLocale(loc)}
                  disabled={loading}
                  className={`px-2 py-1 rounded text-xs border ${
                    locale === loc
                      ? 'border-primary bg-primary/10 text-primary'
                      : 'border-gray-300 bg-white text-gray-600 hover:border-gray-400'
                  }`}
                >
                  {LOCALE_LABELS[loc]}
                </button>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* DPA content */}
        <Card>
          <CardContent className="p-6">
            {loading && (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" />
                {t('dpa.loading')}
              </div>
            )}
            {loadError && (
              <div className="flex items-start gap-3 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                <AlertCircle className="h-5 w-5 shrink-0 mt-0.5" />
                {t('dpa.load_error')}
              </div>
            )}
            {doc && (
              <LegalMarkdownRenderer content={doc.content} />
            )}
          </CardContent>
        </Card>

        {/* Action bar */}
        <div className="no-print flex flex-col-reverse sm:flex-row gap-2 justify-end">
          <Button
            variant="outline"
            onClick={handlePrint}
            disabled={loading || !doc}
          >
            <Printer className="h-4 w-4 mr-1" />
            {t('dpa.print_button')}
          </Button>
          <Button
            onClick={() => setConfirmOpen(true)}
            disabled={loading || !doc || acking || acknowledged}
          >
            {acking && <Loader2 className="h-4 w-4 animate-spin mr-1" />}
            {acknowledged
              ? t('dpa.ack_already_done')
              : (acking ? t('dpa.ack_loading') : t('dpa.ack_button'))
            }
          </Button>
        </div>
      </div>

      {/* Confirmation dialog */}
      <Dialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5 text-primary" />
              {t('dpa.ack_confirm_title')}
            </DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground">
            {t('dpa.ack_confirm_body')}
          </p>
          <DialogFooter>
            <Button variant="outline" onClick={() => setConfirmOpen(false)}>
              {t('dpa.ack_confirm_cancel')}
            </Button>
            <Button onClick={handleAcknowledge}>
              {t('dpa.ack_confirm_ok')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </AppLayout>
  );
}
