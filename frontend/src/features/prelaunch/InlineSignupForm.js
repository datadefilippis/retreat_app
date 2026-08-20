/**
 * InlineSignupForm — la registrazione incorporata nella landing
 * professionisti (RD-bis, decisione founder 19/8: via il form di
 * candidatura, al suo posto la registrazione vera, li' dove prima si
 * «compilava il modulo»).
 *
 * NON e' un secondo flusso di registrazione: chiama la STESSA
 * `signup()` di AuthContext con la stessa firma di SignupPage, riusa
 * `validatePassword` ed `extractApiError` (esportate da AuthPages, non
 * copiate) e porta lo stesso honeypot (`website`) e gli stessi due
 * consensi obbligatori. Cambia solo il vestito: compatto, dentro la
 * card che ospitava il LeadForm.
 *
 * Dopo il successo: /benvenuto (citta', telefono, Instagram,
 * discipline → profilo). Se il backend chiede la verifica email, la
 * card si trasforma nel messaggio «controlla la posta» senza uscire
 * dalla pagina.
 */
import React, { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../../context/AuthContext';
import { validatePassword, extractApiError } from '../../pages/AuthPages';

const FIELD_CLS = 'w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm '
  + 'focus:border-[#376254] focus:outline-none';

export default function InlineSignupForm() {
  const { signup } = useAuth();
  const navigate = useNavigate();
  const { t, i18n } = useTranslation('auth');
  const { t: tl } = useTranslation('landings');

  const [name, setName] = useState('');
  const [organizationName, setOrganizationName] = useState('');
  // ID-quater — dal ponte «diventa professionista» in /account l'email
  // arriva gia' scritta: e' la STESSA che collegherà i due cappelli
  const [params] = useSearchParams();
  const [email, setEmail] = useState(params.get('email') || '');
  const [password, setPassword] = useState('');
  const [acceptedPrivacy, setAcceptedPrivacy] = useState(false);
  const [acceptedTerms, setAcceptedTerms] = useState(false);
  const [website, setWebsite] = useState('');   // honeypot: umani non lo vedono
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [verificationRequired, setVerificationRequired] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    const pwError = validatePassword(password, t);
    if (pwError) { setError(pwError); return; }
    setError('');
    setLoading(true);
    try {
      const result = await signup(email, password, name, organizationName,
        undefined, acceptedTerms && acceptedPrivacy, i18n.language, website);
      if (result === 'verification_required') {
        setVerificationRequired(true);
        return;
      }
      navigate('/benvenuto');
    } catch (err) {
      if (err.response?.status === 429) {
        setError(t('signup.too_fast', { defaultValue: 'Troppi tentativi ravvicinati: aspetta un minuto e riprova.' }));
        return;
      }
      if (err.response?.status === 202
          || err.response?.data?.status === 'verification_required') {
        setVerificationRequired(true);
        return;
      }
      setError(extractApiError(err, t('signup.error', { defaultValue: 'Errore nella creazione dell’account' })));
    } finally {
      setLoading(false);
    }
  };

  if (verificationRequired) {
    return (
      <div className="text-center py-6" data-testid="ol-signup-verify">
        <p className="font-display text-xl text-[#2e4b3f] mb-3">
          {t('signup.verify_email_title', { defaultValue: 'Controlla la tua email' })}
        </p>
        <p className="text-sm text-gray-600 leading-relaxed max-w-sm mx-auto">
          {t('signup.verify_email_message', { defaultValue: 'Ti abbiamo inviato un link di verifica. Clicca il link per attivare il tuo account.' })}
        </p>
      </div>
    );
  }

  return (
    <form onSubmit={submit} className="space-y-4" data-testid="ol-inline-signup">
      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            {t('signup.name', { defaultValue: 'Nome' })}
          </label>
          <input type="text" required value={name} autoComplete="name"
            onChange={(e) => setName(e.target.value)} className={FIELD_CLS} />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            {tl('opPro.orgField', { defaultValue: 'Nome della tua attività' })}
          </label>
          <input type="text" required value={organizationName} autoComplete="organization"
            onChange={(e) => setOrganizationName(e.target.value)} className={FIELD_CLS} />
        </div>
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
        <input type="email" required value={email} autoComplete="email"
          onChange={(e) => setEmail(e.target.value)} className={FIELD_CLS} />
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          {t('signup.password', { defaultValue: 'Password' })}
        </label>
        <input type="password" required value={password} autoComplete="new-password"
          onChange={(e) => setPassword(e.target.value)} className={FIELD_CLS} />
        <p className="mt-1 text-[11px] text-gray-400">
          {t('validation.password_hint2', { defaultValue: 'Almeno 12 caratteri, con maiuscole, minuscole e un numero. Le password comparse in fughe di dati pubbliche vengono rifiutate.' })}
        </p>
      </div>

      {/* honeypot: fuori dalla vista, i bot lo compilano e il backend
          li scarta — identico a SignupPage */}
      <input type="text" value={website} onChange={(e) => setWebsite(e.target.value)}
        name="website" tabIndex={-1} autoComplete="off" aria-hidden="true"
        style={{ position: 'absolute', left: '-9999px', height: 0, width: 0, opacity: 0 }} />

      <label className="flex items-start gap-2.5 text-xs text-gray-600">
        <input type="checkbox" checked={acceptedPrivacy}
          onChange={(e) => setAcceptedPrivacy(e.target.checked)}
          className="mt-0.5 accent-[#376254]" data-testid="ol-consent-privacy" />
        <span>
          {t('accept_privacy_prefix', { defaultValue: 'Ho letto e accetto la' })}{' '}
          <Link to="/privacy" target="_blank" className="underline text-[#2f5749]">
            {t('privacy_policy', { defaultValue: 'Privacy Policy' })}
          </Link>
        </span>
      </label>
      <label className="flex items-start gap-2.5 text-xs text-gray-600">
        <input type="checkbox" checked={acceptedTerms}
          onChange={(e) => setAcceptedTerms(e.target.checked)}
          className="mt-0.5 accent-[#376254]" data-testid="ol-consent-terms" />
        <span>
          {t('accept_terms_prefix', { defaultValue: 'Ho letto e accetto i' })}{' '}
          <Link to="/termini" target="_blank" className="underline text-[#2f5749]">
            {t('terms_of_service', { defaultValue: 'Termini di Servizio' })}
          </Link>
        </span>
      </label>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <button type="submit" data-testid="ol-signup-submit"
        disabled={loading || !acceptedTerms || !acceptedPrivacy}
        className="w-full rounded-lg bg-[#376254] px-6 py-3 text-sm font-semibold text-white hover:bg-[#2e5346] disabled:opacity-50">
        {loading
          ? t('signup.loading', { defaultValue: 'Creazione account…' })
          : tl('opPro.ctaContact2', { defaultValue: 'Crea il tuo account' })}
      </button>
      <p className="text-center text-xs text-gray-500">
        {tl('opPro.haveAccount', { defaultValue: 'Hai già un account?' })}{' '}
        <Link to="/accedi" className="underline text-[#2f5749]">
          {tl('opPro.loginLink', { defaultValue: 'Accedi' })}
        </Link>
      </p>
    </form>
  );
}
