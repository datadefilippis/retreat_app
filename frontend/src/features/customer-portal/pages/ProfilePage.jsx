/**
 * ProfilePage — customer account settings.
 *
 * Phase 4 of the customer area refactor. New page (didn't exist
 * before — change-password and update-profile endpoints were
 * available on the backend but no UI consumed them).
 *
 * Three cards:
 *   1. 👤 Dati account     — name, phone (editable). Email + locale
 *      shown as read-only because the backend whitelist only allows
 *      name + phone updates.
 *   2. 🔒 Sicurezza        — change password (current + new, server
 *      validates strength).
 *   3. ✉️ Verifica email   — status + resend link when not verified.
 *      Hidden when already verified.
 *
 * Validation lives client-side as a UX gate; the backend always
 * re-validates so a tampered request never sneaks through.
 */

import React, { useEffect, useState } from 'react';
import { useTranslation, Trans } from 'react-i18next';
import { toast } from 'sonner';
import { useCustomerAuth } from '../../../context/CustomerAuthContext';
import { useStoreMeta } from '../../../hooks/useStoreMeta';
import { customerAuthAPI } from '../../../api/customerAuth';
import { customerPortalAPI } from '../../../api/customerPortal';
import { APP_SUPPORTED_LOCALES } from '../../../hooks/useStorefrontLocale';
import SectionCard from '../components/SectionCard';
import PageHeader from '../components/PageHeader';


/* ── Card 1: account profile (name, phone, read-only email) ─────────── */

function AccountCard({ customer, onProfileUpdated }) {
  const { t: tCommon } = useTranslation('common');
  const { t } = useTranslation('customer_portal');
  const { updateCustomer } = useCustomerAuth();
  // Read the merchant's allowed-language list so the locale picker
  // shows ONLY the languages the customer can actually use right now
  // on this store. Without this filter, picking (e.g.) French on a
  // German-only store would PATCH `customer.locale='fr'` successfully
  // but the storefront resolver would still apply the store's primary
  // (German) — leaving the user wondering why their click had no
  // visible effect.
  //
  // Falls back to the full APP_SUPPORTED list when meta isn't ready
  // yet (initial render, network error). Once the meta resolves, the
  // picker re-renders with the filtered set.
  const meta = useStoreMeta();
  const [draft, setDraft] = useState({
    name: customer?.name || '',
    phone: customer?.phone || '',
  });
  const [saving, setSaving] = useState(false);
  // Independent saving flag for the locale select so a pending name/phone
  // edit doesn't block the picker (and vice-versa). Locale changes
  // commit immediately on `onChange` and don't share the dirty/save flow.
  const [savingLocale, setSavingLocale] = useState(false);

  // Re-sync the draft when the customer prop changes (e.g. after the
  // context re-fetches /me post-update).
  useEffect(() => {
    setDraft({
      name: customer?.name || '',
      phone: customer?.phone || '',
    });
  }, [customer?.name, customer?.phone]);

  const dirty =
    (draft.name || '') !== (customer?.name || '') ||
    (draft.phone || '') !== (customer?.phone || '');

  const handleSave = async () => {
    if (!draft.name.trim()) {
      toast.error(t('customer_portal:profile.account.nameRequired'));
      return;
    }
    setSaving(true);
    try {
      const payload = { name: draft.name.trim() };
      // Only send `phone` when the customer typed something — sending an
      // empty string would clobber an existing phone with "".
      if (draft.phone.trim() !== (customer?.phone || '').trim()) {
        payload.phone = draft.phone.trim();
      }
      await customerPortalAPI.updateProfile(payload);
      toast.success(t('customer_portal:profile.account.updatedToast'));
      onProfileUpdated?.();
    } catch (e) {
      const detail = e?.response?.data?.detail;
      const msg = typeof detail === 'string'
        ? detail
        : (detail && (detail.message || detail.error)) || t('customer_portal:profile.account.updateError');
      toast.error(String(msg));
    } finally {
      setSaving(false);
    }
  };

  // Locale picker — commits on every change (no dirty-button dance).
  // The CustomerAuthContext effect at line ~79 watches `customer.locale`
  // and calls `i18n.changeLanguage`, so the moment we merge the new
  // value into context the whole UI re-renders in the new language.
  // No-op when the customer picks the value that's already saved.
  const currentLocale = (customer?.locale || 'it').toLowerCase().split('-')[0];
  const handleLocaleChange = async (e) => {
    const next = e.target.value;
    if (!next || next === currentLocale || !APP_SUPPORTED_LOCALES.includes(next)) return;
    setSavingLocale(true);
    try {
      await customerPortalAPI.updateProfile({ locale: next });
      // Context merge fires the i18n.changeLanguage effect on the next
      // tick, so we don't have to call it manually here.
      updateCustomer({ locale: next });
      toast.success(t('customer_portal:profile.account.localeUpdatedToast'));
    } catch (err) {
      const detail = err?.response?.data?.detail;
      const msg = typeof detail === 'string'
        ? detail
        : (detail && (detail.message || detail.error)) || t('customer_portal:profile.account.localeUpdateError');
      toast.error(String(msg));
    } finally {
      setSavingLocale(false);
    }
  };

  return (
    <SectionCard icon="👤" title={t('customer_portal:profile.account.title')} description={t('customer_portal:profile.account.description')}>
      <div className="space-y-3">
        <Field label={t('customer_portal:profile.account.nameLabel')}>
          <input
            type="text"
            value={draft.name}
            onChange={e => setDraft({ ...draft, name: e.target.value })}
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none"
            placeholder={t('customer_portal:profile.account.namePlaceholder')}
            maxLength={120}
          />
        </Field>

        <Field label={t('customer_portal:profile.account.phoneLabel')} hint={t('customer_portal:profile.account.phoneHint')}>
          <input
            type="tel"
            value={draft.phone}
            onChange={e => setDraft({ ...draft, phone: e.target.value })}
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none"
            placeholder={t('customer_portal:profile.account.phonePlaceholder')}
            maxLength={40}
          />
        </Field>

        <Field label={t('customer_portal:profile.account.emailLabel')} hint={t('customer_portal:profile.account.emailHint')}>
          <input
            type="email"
            value={customer?.email || ''}
            disabled
            className="w-full rounded-md border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-600"
          />
        </Field>

        <Field label={t('customer_portal:profile.account.localeLabel')}>
          {/*
            Picker options are filtered to the merchant's allowed list:
              - meta ready + non-empty list → only those languages
              - meta loading/error/idle    → fall back to all 4 supported
                (graceful degradation; the resolver will still enforce
                the store list at i18n.changeLanguage time)

            We also keep the customer's CURRENT saved locale in the
            options even when out-of-list — otherwise the <select>
            would render in an invalid state (no option matches its
            `value`). The customer can still pick another option to
            "fix" it.
           */}
          {(() => {
            const merchantList = (
              meta?.status === 'ready'
              && Array.isArray(meta.storefrontLanguages)
              && meta.storefrontLanguages.length > 0
            )
              ? meta.storefrontLanguages.filter((l) => APP_SUPPORTED_LOCALES.includes(l))
              : APP_SUPPORTED_LOCALES;
            const optionLocales = merchantList.includes(currentLocale)
              ? merchantList
              : [currentLocale, ...merchantList];
            return (
              <select
                value={currentLocale}
                onChange={handleLocaleChange}
                disabled={savingLocale}
                aria-label={t('customer_portal:profile.account.localeSelectAria')}
                className="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:border-gray-900 focus:outline-none disabled:opacity-60"
              >
                {optionLocales.map((loc) => (
                  <option key={loc} value={loc}>
                    {tCommon(`common:language.${loc}`)}
                  </option>
                ))}
              </select>
            );
          })()}
        </Field>

        <div className="flex justify-end">
          <button
            type="button"
            onClick={handleSave}
            disabled={!dirty || saving}
            className="rounded-md bg-gray-900 text-white text-sm font-semibold px-4 py-2 hover:bg-gray-800 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {saving
              ? t('customer_portal:profile.account.saving')
              : dirty
                ? t('customer_portal:profile.account.saveDirty')
                : t('customer_portal:profile.account.saveClean')}
          </button>
        </div>
      </div>
    </SectionCard>
  );
}


/* ── Card 2: password ─────────────────────────────────────────────────── */

function PasswordCard() {
  const { t } = useTranslation('customer_portal');
  const [currentPwd, setCurrentPwd] = useState('');
  const [newPwd, setNewPwd] = useState('');
  const [confirmPwd, setConfirmPwd] = useState('');
  const [submitting, setSubmitting] = useState(false);

  // Server enforces 8+ chars; we mirror the rule client-side as a UX
  // gate. The backend stays the source of truth.
  const tooShort = newPwd.length > 0 && newPwd.length < 8;
  const mismatch = confirmPwd.length > 0 && newPwd !== confirmPwd;
  const canSubmit = currentPwd && newPwd && newPwd === confirmPwd && newPwd.length >= 8;

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!canSubmit || submitting) return;
    setSubmitting(true);
    try {
      await customerPortalAPI.changePassword({
        current_password: currentPwd,
        new_password: newPwd,
      });
      toast.success(t('customer_portal:profile.password.updatedToast'));
      setCurrentPwd('');
      setNewPwd('');
      setConfirmPwd('');
    } catch (err) {
      const detail = err?.response?.data?.detail;
      const msg = typeof detail === 'string'
        ? detail
        : (detail && (detail.message || detail.error)) || t('customer_portal:profile.password.updateError');
      toast.error(String(msg));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <SectionCard icon="🔒" title={t('customer_portal:profile.password.title')} description={t('customer_portal:profile.password.description')}>
      <form onSubmit={handleSubmit} className="space-y-3">
        <Field label={t('customer_portal:profile.password.currentLabel')}>
          <input
            type="password"
            autoComplete="current-password"
            value={currentPwd}
            onChange={e => setCurrentPwd(e.target.value)}
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none"
          />
        </Field>

        <Field label={t('customer_portal:profile.password.newLabel')} hint={t('customer_portal:profile.password.newHint')}>
          <input
            type="password"
            autoComplete="new-password"
            value={newPwd}
            onChange={e => setNewPwd(e.target.value)}
            className={`w-full rounded-md border px-3 py-2 text-sm focus:outline-none ${
              tooShort ? 'border-red-400 focus:border-red-500' : 'border-gray-300 focus:border-gray-900'
            }`}
          />
          {tooShort && (
            <p className="text-[11px] text-red-700 mt-1">{t('customer_portal:profile.password.minLengthError')}</p>
          )}
        </Field>

        <Field label={t('customer_portal:profile.password.confirmLabel')}>
          <input
            type="password"
            autoComplete="new-password"
            value={confirmPwd}
            onChange={e => setConfirmPwd(e.target.value)}
            className={`w-full rounded-md border px-3 py-2 text-sm focus:outline-none ${
              mismatch ? 'border-red-400 focus:border-red-500' : 'border-gray-300 focus:border-gray-900'
            }`}
          />
          {mismatch && (
            <p className="text-[11px] text-red-700 mt-1">{t('customer_portal:profile.password.mismatchError')}</p>
          )}
        </Field>

        <div className="flex justify-end">
          <button
            type="submit"
            disabled={!canSubmit || submitting}
            className="rounded-md bg-gray-900 text-white text-sm font-semibold px-4 py-2 hover:bg-gray-800 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {submitting ? t('customer_portal:profile.password.submitting') : t('customer_portal:profile.password.submit')}
          </button>
        </div>
      </form>
    </SectionCard>
  );
}


/* ── Card 3: email verification (renders only when not verified) ───── */

function EmailVerificationCard({ customer, storeSlug }) {
  const { t } = useTranslation('customer_portal');
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(false);

  if (!customer || customer.email_verified) return null;

  const handleResend = async () => {
    if (sending || sent) return;
    if (!storeSlug) {
      toast.error(t('customer_portal:profile.verify.storeUnknown'));
      return;
    }
    setSending(true);
    try {
      await customerAuthAPI.resendVerification(storeSlug, customer.email);
      setSent(true);
      toast.success(t('customer_portal:profile.verify.resentToast'));
    } catch (e) {
      const detail = e?.response?.data?.detail;
      const msg = typeof detail === 'string'
        ? detail
        : (detail && (detail.message || detail.error)) || t('customer_portal:profile.verify.resendError');
      toast.error(String(msg));
    } finally {
      setSending(false);
    }
  };

  return (
    <SectionCard
      icon="✉️"
      title={t('customer_portal:profile.verify.title')}
      description={t('customer_portal:profile.verify.description')}
    >
      <div className="rounded-lg border border-amber-200 bg-amber-50 p-3">
        <p className="text-sm text-amber-900">
          <Trans
            i18nKey="customer_portal:profile.verify.body"
            values={{ email: customer.email }}
            components={{ strong: <strong /> }}
          />
        </p>
        <p className="text-xs text-amber-800 mt-1">
          {t('customer_portal:profile.verify.hint')}
        </p>
        <button
          type="button"
          onClick={handleResend}
          disabled={sending || sent}
          className="mt-3 rounded-md border border-amber-300 bg-white text-amber-900 hover:bg-amber-100 text-xs font-semibold px-3 py-1.5 disabled:opacity-60"
        >
          {sent ? t('customer_portal:profile.verify.sent') : sending ? t('customer_portal:profile.verify.sending') : t('customer_portal:profile.verify.resendBtn')}
        </button>
      </div>
    </SectionCard>
  );
}


/* ── Card 4: GDPR Art. 17 erasure (Sprint 1 W1.2 — parity widget) ───── */

function EraseAccountCard({ customer }) {
  const { t } = useTranslation('customer_portal');
  const [expanded, setExpanded] = useState(false);
  const [reason, setReason] = useState('');
  const [confirmChecked, setConfirmChecked] = useState(false);
  const [emailConfirm, setEmailConfirm] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [requestId, setRequestId] = useState(null);

  // Safety gates — defense-in-depth oltre il backend confirm=true:
  //   1. confirmChecked: checkbox "Comprendo che e' irreversibile"
  //   2. emailConfirm: re-type dell'email per evitare click accidentale
  //      (pattern simile al GitHub delete-repo flow)
  const emailMatches =
    !!customer?.email &&
    emailConfirm.trim().toLowerCase() === customer.email.toLowerCase();
  const canSubmit = confirmChecked && emailMatches && !submitting && !requestId;

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!canSubmit) return;
    setSubmitting(true);
    try {
      const res = await customerPortalAPI.requestErasure({
        reason: reason.trim() || null,
        confirm: true,
      });
      const data = res?.data || {};
      setRequestId(data.request_id || 'submitted');
      toast.success(
        t(
          'customer_portal:profile.erasure.successToast',
          'Richiesta inviata. Riceverai un\'email di conferma.'
        )
      );
    } catch (err) {
      const detail = err?.response?.data?.detail;
      const msg =
        typeof detail === 'string'
          ? detail
          : (detail && (detail.message || detail.error)) ||
            t(
              'customer_portal:profile.erasure.errorGeneric',
              'Errore invio richiesta. Riprova piu\' tardi.'
            );
      toast.error(String(msg));
    } finally {
      setSubmitting(false);
    }
  };

  // Success state — richiesta gia' inviata in questa sessione
  if (requestId) {
    return (
      <SectionCard
        icon="🗑️"
        title={t(
          'customer_portal:profile.erasure.title',
          'Cancellazione account (GDPR Art. 17)'
        )}
        description={t(
          'customer_portal:profile.erasure.description',
          'Esercita il diritto all\'oblio: cancellazione dei tuoi dati personali.'
        )}
      >
        <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-900">
          <p className="font-semibold">
            {t(
              'customer_portal:profile.erasure.successTitle',
              'Richiesta registrata'
            )}
          </p>
          <p className="mt-1">
            {t(
              'customer_portal:profile.erasure.successBody',
              'La tua richiesta di cancellazione e\' stata registrata. Riceverai un\'email di conferma. La cancellazione completa avverra\' entro 30 giorni in conformita\' con l\'Art. 12 GDPR.'
            )}
          </p>
          <p className="mt-2 text-xs text-emerald-800">
            ID richiesta: <code>{requestId}</code>
          </p>
        </div>
      </SectionCard>
    );
  }

  return (
    <SectionCard
      icon="🗑️"
      title={t(
        'customer_portal:profile.erasure.title',
        'Cancellazione account (GDPR Art. 17)'
      )}
      description={t(
        'customer_portal:profile.erasure.description',
        'Esercita il diritto all\'oblio: cancellazione dei tuoi dati personali.'
      )}
    >
      {!expanded ? (
        <div className="space-y-3">
          <p className="text-sm text-gray-700">
            {t(
              'customer_portal:profile.erasure.intro',
              'Puoi richiedere la cancellazione del tuo account e di tutti i dati personali associati ai sensi dell\'Art. 17 GDPR.'
            )}
          </p>
          <button
            type="button"
            onClick={() => setExpanded(true)}
            className="rounded-md border border-red-200 bg-red-50 text-red-700 hover:bg-red-100 text-sm font-semibold px-4 py-2"
          >
            {t(
              'customer_portal:profile.erasure.openCta',
              'Procedi alla richiesta di cancellazione'
            )}
          </button>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-900">
            <p className="font-semibold">
              {t(
                'customer_portal:profile.erasure.warningTitle',
                '⚠️ Attenzione: questa operazione e\' irreversibile'
              )}
            </p>
            <p className="mt-1">
              {t(
                'customer_portal:profile.erasure.warningBody',
                'La cancellazione completa di tutti i dati personali avverra\' entro 30 giorni. Perderai accesso agli ordini, ai corsi e ai contenuti digitali acquistati.'
              )}
            </p>
          </div>

          <Field
            label={t(
              'customer_portal:profile.erasure.reasonLabel',
              'Motivo (opzionale, max 500 caratteri)'
            )}
          >
            <textarea
              rows={3}
              maxLength={500}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder={t(
                'customer_portal:profile.erasure.reasonPlaceholder',
                'Es. Non utilizzo piu\' il servizio'
              )}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:border-gray-900"
            />
          </Field>

          <Field
            label={t(
              'customer_portal:profile.erasure.emailConfirmLabel',
              'Per confermare, digita la tua email'
            )}
            hint={customer?.email}
          >
            <input
              type="email"
              autoComplete="off"
              value={emailConfirm}
              onChange={(e) => setEmailConfirm(e.target.value)}
              placeholder={customer?.email || ''}
              className={`w-full rounded-md border px-3 py-2 text-sm focus:outline-none ${
                emailConfirm && !emailMatches
                  ? 'border-red-400 focus:border-red-500'
                  : 'border-gray-300 focus:border-gray-900'
              }`}
            />
            {emailConfirm && !emailMatches && (
              <p className="text-[11px] text-red-700 mt-1">
                {t(
                  'customer_portal:profile.erasure.emailMismatch',
                  'L\'email non corrisponde.'
                )}
              </p>
            )}
          </Field>

          <label className="flex items-start gap-2 text-sm text-gray-700">
            <input
              type="checkbox"
              checked={confirmChecked}
              onChange={(e) => setConfirmChecked(e.target.checked)}
              className="mt-0.5"
            />
            <span>
              {t(
                'customer_portal:profile.erasure.confirmCheckbox',
                'Comprendo che la cancellazione e\' irreversibile e tutti i miei dati verranno rimossi entro 30 giorni.'
              )}
            </span>
          </label>

          <div className="flex justify-between gap-2 pt-2 border-t border-gray-200">
            <button
              type="button"
              onClick={() => {
                setExpanded(false);
                setReason('');
                setConfirmChecked(false);
                setEmailConfirm('');
              }}
              className="rounded-md border border-gray-300 text-gray-700 hover:bg-gray-50 text-sm font-semibold px-4 py-2"
            >
              {t('common:cancel', 'Annulla')}
            </button>
            <button
              type="submit"
              disabled={!canSubmit}
              className="rounded-md bg-red-700 text-white hover:bg-red-800 text-sm font-semibold px-4 py-2 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              {submitting
                ? t(
                    'customer_portal:profile.erasure.submitting',
                    'Invio richiesta...'
                  )
                : t(
                    'customer_portal:profile.erasure.submitCta',
                    'Conferma cancellazione'
                  )}
            </button>
          </div>
        </form>
      )}
    </SectionCard>
  );
}


/* ── Field — small label+hint helper used 6+ times above ────────────── */

function Field({ label, hint, children }) {
  return (
    <div>
      <label className="block text-xs font-semibold uppercase tracking-wider text-gray-600 mb-1">
        {label}
      </label>
      {children}
      {hint && <p className="text-[11px] text-gray-500 mt-1">{hint}</p>}
    </div>
  );
}


/* ── Page ─────────────────────────────────────────────────────────────── */

export default function ProfilePage() {
  const { customer, storeSlug } = useCustomerAuth();
  const { t } = useTranslation('customer_portal');

  // After a profile update we'd ideally re-fetch /me so the context
  // reflects the new name. The CustomerAuthContext currently doesn't
  // expose a refresh method — we rely on the next pageload (or a
  // manual refresh) to pull the new state. Toast confirms the success
  // so the customer never doubts the operation completed.
  const handleProfileUpdated = () => {
    // No-op for now. Future: useCustomerAuth().refreshMe() once the
    // context exposes it.
  };

  return (
    <div className="space-y-4">
      <PageHeader
        title={t('customer_portal:profile.pageTitle')}
        description={t('customer_portal:profile.pageDescription')}
      />

      <EmailVerificationCard customer={customer} storeSlug={storeSlug} />
      <AccountCard customer={customer} onProfileUpdated={handleProfileUpdated} />
      <PasswordCard />
      {/* Sprint 1 W1.2 — GDPR Art. 17 erasure (parity widget E4.4) */}
      <EraseAccountCard customer={customer} />
    </div>
  );
}
