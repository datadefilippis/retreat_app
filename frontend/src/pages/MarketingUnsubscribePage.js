/**
 * Wave GDPR-Commerce Piece 1b — public marketing-consent unsubscribe page.
 *
 * Mounted at /u/:token (NO auth wrapper) so any customer — guest or
 * registered — can click an "unsubscribe" link from a newsletter footer
 * and revoke their marketing consent with one click. Required by GDPR
 * Art. 7(3) ("withdrawal must be as easy as giving consent") to cover
 * the GUEST checkout path that has no portal account to toggle.
 *
 * Two-step flow:
 *   1. On mount, GET /api/marketing-consent/unsubscribe/:token to
 *      VALIDATE the link and show the customer:
 *        - the masked email it targets (so they confirm it's theirs)
 *        - the merchant name (so they know which list they're leaving)
 *        - an "already unsubscribed" hint if they re-clicked an old link.
 *   2. User clicks "Confirm unsubscribe" → POST /confirm to act.
 *
 * The two-step flow defends against aggressive email-client link
 * prefetching (Outlook/Gmail/Apple Mail) and corporate-scanner GETs
 * that would otherwise unsubscribe customers without their intent.
 *
 * Error UX:
 *   - 401 (invalid_token)  → clear message + suggestion to contact merchant
 *   - 410 (expired_token)  → clear message + suggestion to contact merchant
 *   - 500 / network        → generic retry message; the POST is idempotent
 *                            so retrying is safe
 *
 * Public surface (no app chrome). Keeps the afianco brand light at the
 * top so the customer recognises the service, but the FOCUS is on the
 * merchant they're unsubscribing from.
 */

import React, { useEffect, useState, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { CheckCircle2, AlertTriangle, MailX, Loader2, TrendingUp } from 'lucide-react';

import {
  previewMarketingUnsubscribe,
  confirmMarketingUnsubscribe,
} from '../services/legalService';


// ── Status state machine ──────────────────────────────────────────────────
//
// loading              → calling preview on mount
// ready                → preview returned valid info; user can confirm
// already_unsubscribed → preview says the last marketing event is a revoke;
//                        still let the user re-confirm (idempotent), but show
//                        the hint up front
// confirming           → POST /confirm in-flight
// done                 → POST returned success
// error_invalid        → 401 from preview or confirm
// error_expired        → 410 from preview or confirm
// error_other          → 500 / network — retry button visible

function _extractErrorCode(err) {
  // Axios shape: err.response?.data?.detail?.error_code
  try {
    return err?.response?.data?.detail?.error_code || null;
  } catch {
    return null;
  }
}

function _statusFromError(err) {
  if (!err) return 'error_other';
  const code = _extractErrorCode(err);
  if (code === 'invalid_token') return 'error_invalid';
  if (code === 'expired_token') return 'error_expired';
  return 'error_other';
}


export default function MarketingUnsubscribePage() {
  const { t } = useTranslation('legal');
  const { token } = useParams();

  const [status, setStatus] = useState('loading');
  const [info, setInfo] = useState(null);   // { email_masked, organization_name, already_unsubscribed }
  const [_lastError, setLastError] = useState(null);

  // ── Step 1: validate token on mount ───────────────────────────────────
  useEffect(() => {
    let active = true;
    setStatus('loading');
    previewMarketingUnsubscribe(token)
      .then((data) => {
        if (!active) return;
        setInfo(data);
        setStatus(data.already_unsubscribed ? 'already_unsubscribed' : 'ready');
      })
      .catch((err) => {
        if (!active) return;
        setLastError(err);
        setStatus(_statusFromError(err));
      });
    return () => { active = false; };
  }, [token]);

  // ── Step 2: confirm action ────────────────────────────────────────────
  const handleConfirm = useCallback(async () => {
    setStatus('confirming');
    try {
      await confirmMarketingUnsubscribe(token);
      setStatus('done');
    } catch (err) {
      setLastError(err);
      setStatus(_statusFromError(err));
    }
  }, [token]);

  const merchantName = info?.organization_name
    || t('marketing_unsubscribe.merchant_fallback', { defaultValue: 'il negozio' });

  return (
    <div className="min-h-screen bg-background flex flex-col">
      {/* Brand chrome — afianco logo only, no nav */}
      <header className="border-b border-border">
        <div className="max-w-2xl mx-auto px-6 py-4 flex items-center">
          <Link to="/" className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded bg-primary">
              <TrendingUp className="h-4 w-4 text-primary-foreground" />
            </div>
            <span className="font-heading text-xl font-bold tracking-tight">
              AFianco
            </span>
          </Link>
        </div>
      </header>

      <main className="flex-1 flex items-center justify-center px-6 py-12">
        <div className="w-full max-w-md">
          {/* ── Loading ────────────────────────────────────────────────── */}
          {status === 'loading' && (
            <div className="text-center">
              <Loader2 className="mx-auto h-8 w-8 animate-spin text-muted-foreground" />
              <p className="mt-4 text-sm text-muted-foreground">
                {t('marketing_unsubscribe.loading', {
                  defaultValue: 'Verifica del link in corso…',
                })}
              </p>
            </div>
          )}

          {/* ── Ready / Already unsubscribed (confirm step) ───────────── */}
          {(status === 'ready' || status === 'already_unsubscribed' || status === 'confirming') && (
            <div className="rounded-lg border bg-card p-6 shadow-sm">
              <div className="flex items-start gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-amber-100 dark:bg-amber-900/30">
                  <MailX className="h-5 w-5 text-amber-700 dark:text-amber-400" />
                </div>
                <div className="flex-1">
                  <h1 className="text-xl font-semibold">
                    {t('marketing_unsubscribe.title', {
                      defaultValue: 'Disiscriviti dalle email marketing',
                    })}
                  </h1>
                  <p className="mt-2 text-sm text-muted-foreground">
                    {t('marketing_unsubscribe.intro', {
                      defaultValue:
                        "Stai per annullare l'iscrizione alle email marketing di {{merchant}} per l'indirizzo {{email}}.",
                      merchant: merchantName,
                      email: info?.email_masked || '—',
                    })}
                  </p>
                  {status === 'already_unsubscribed' && (
                    <div className="mt-4 rounded-md bg-blue-50 border border-blue-200 px-3 py-2 text-xs text-blue-800 dark:bg-blue-900/20 dark:border-blue-900/40 dark:text-blue-300">
                      {t('marketing_unsubscribe.already_hint', {
                        defaultValue:
                          'Risulti già disiscritto. Puoi confermare di nuovo se vuoi essere sicuro.',
                      })}
                    </div>
                  )}
                </div>
              </div>

              <button
                type="button"
                onClick={handleConfirm}
                disabled={status === 'confirming'}
                className="mt-6 w-full rounded-md bg-red-600 hover:bg-red-700 disabled:bg-red-300 disabled:cursor-not-allowed text-white font-medium px-4 py-2.5 text-sm transition-colors flex items-center justify-center gap-2"
              >
                {status === 'confirming' ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    {t('marketing_unsubscribe.confirming', { defaultValue: 'Disiscrizione in corso…' })}
                  </>
                ) : (
                  t('marketing_unsubscribe.confirm_button', {
                    defaultValue: 'Conferma disiscrizione',
                  })
                )}
              </button>

              <p className="mt-3 text-center text-xs text-muted-foreground">
                {t('marketing_unsubscribe.note_transactional', {
                  defaultValue:
                    'Continuerai a ricevere le sole email transazionali (conferme ordine, ricevute).',
                })}
              </p>
            </div>
          )}

          {/* ── Done ─────────────────────────────────────────────────── */}
          {status === 'done' && (
            <div className="rounded-lg border bg-card p-6 shadow-sm text-center">
              <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-emerald-100 dark:bg-emerald-900/30">
                <CheckCircle2 className="h-6 w-6 text-emerald-600 dark:text-emerald-400" />
              </div>
              <h1 className="mt-4 text-xl font-semibold">
                {t('marketing_unsubscribe.done_title', {
                  defaultValue: 'Disiscrizione completata',
                })}
              </h1>
              <p className="mt-2 text-sm text-muted-foreground">
                {t('marketing_unsubscribe.done_body', {
                  defaultValue:
                    'Non riceverai più email marketing da {{merchant}}. La modifica ha effetto immediato.',
                  merchant: merchantName,
                })}
              </p>
            </div>
          )}

          {/* ── Error states ─────────────────────────────────────────── */}
          {(status === 'error_invalid' || status === 'error_expired' || status === 'error_other') && (
            <div className="rounded-lg border bg-card p-6 shadow-sm text-center">
              <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-red-100 dark:bg-red-900/30">
                <AlertTriangle className="h-6 w-6 text-red-600 dark:text-red-400" />
              </div>
              <h1 className="mt-4 text-xl font-semibold">
                {status === 'error_expired'
                  ? t('marketing_unsubscribe.error_expired_title', {
                      defaultValue: 'Link scaduto',
                    })
                  : status === 'error_invalid'
                  ? t('marketing_unsubscribe.error_invalid_title', {
                      defaultValue: 'Link non valido',
                    })
                  : t('marketing_unsubscribe.error_other_title', {
                      defaultValue: 'Si è verificato un errore',
                    })}
              </h1>
              <p className="mt-2 text-sm text-muted-foreground">
                {status === 'error_expired'
                  ? t('marketing_unsubscribe.error_expired_body', {
                      defaultValue:
                        'Questo link di disiscrizione è scaduto. Contatta il negozio per chiedere di essere rimosso dalla lista.',
                    })
                  : status === 'error_invalid'
                  ? t('marketing_unsubscribe.error_invalid_body', {
                      defaultValue:
                        'Questo link di disiscrizione non è valido. Contatta il negozio per chiedere di essere rimosso dalla lista.',
                    })
                  : t('marketing_unsubscribe.error_other_body', {
                      defaultValue:
                        'Non siamo riusciti a registrare la richiesta. Riprova fra qualche secondo.',
                    })}
              </p>
              {status === 'error_other' && (
                <button
                  type="button"
                  onClick={handleConfirm}
                  className="mt-6 rounded-md bg-primary hover:bg-primary/90 text-primary-foreground font-medium px-4 py-2 text-sm"
                >
                  {t('marketing_unsubscribe.retry_button', { defaultValue: 'Riprova' })}
                </button>
              )}
            </div>
          )}
        </div>
      </main>

      <footer className="border-t border-border py-4 text-center text-xs text-muted-foreground">
        <Link to="/privacy" className="hover:text-foreground">
          {t('marketing_unsubscribe.footer_privacy', { defaultValue: 'Privacy di afianco' })}
        </Link>
      </footer>
    </div>
  );
}
