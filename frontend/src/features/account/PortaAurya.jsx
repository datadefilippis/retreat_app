/**
 * PortaAurya — la porta unica dell'account cliente, in linea (R1, 25/9/2026).
 *
 * Piano docs/ANALISI_REGISTRAZIONE_OBBLIGATORIA_2026-09-25.md: la stessa
 * porta si monta dove serve un'identita' — il checkout (R3), i contatti
 * dell'operatore (R2), oggi il pannello inline del checkout. Decisione
 * del founder (25/9 sera): l'account si CREA con una password; per chi
 * ce l'ha gia' l'accesso e' email+password.
 *
 * Due viste (26/9, founder: «solo account veri con password» — niente
 * codice a 6 cifre qui; resta su /accedi e nel pannello del checkout):
 *   entra — email + password (→ /platform/auth/login), «Password
 *           dimenticata», «Non hai un account? Crealo»;
 *   crea  — nome, email, password (le 4 regole di AccountLoginPage), la
 *           casella legale obbligatoria (accepted_terms) e la casella del
 *           Cerchio SEPARATA e SPENTA (wants_newsletter + consenso_versione:
 *           il testo e' quello unico e versionato di lib/testiConsenso).
 *           → /platform/auth/signup. Con l'interruttore E6 acceso il server
 *           risponde gia' con la sessione (access_token) e la porta si
 *           chiude; spento, resta «Ti abbiamo scritto: conferma l'email,
 *           poi entra con la password».
 *
 * Al successo: token in localStorage (PLATFORM_TOKEN_KEY), eventuale
 * prova del Cerchio (subscriber_token), profilo fresco da /platform/me e
 * callback onDentro(account). Nessun redirect: chi monta decide.
 * Vive DENTRO altri <form>: ogni Enter e' intercettato, mai un submit
 * del padre.
 */
import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import platformApi, { PLATFORM_TOKEN_KEY } from '../../api/platformClient';
import { salvaProva } from '../../lib/cerchio';
import { testoConsenso, VERSIONE_CORRENTE } from '../../lib/testiConsenso';

const INPUT = 'w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-gray-800 focus:border-transparent outline-none';
const BOTTONE = 'w-full rounded-lg bg-gray-900 text-white px-3 py-2 text-sm font-medium disabled:opacity-50';
const LINK = 'text-[11px] text-gray-500 underline hover:text-gray-700';

export const REGOLE_PASSWORD = [
  ['len', (p) => p.length >= 12, 'almeno 12 caratteri'],
  ['low', (p) => /[a-z]/.test(p), 'una minuscola'],
  ['up', (p) => /[A-Z]/.test(p), 'una maiuscola'],
  ['num', (p) => /\d/.test(p), 'un numero'],
];
export const passwordValida = (p) => REGOLE_PASSWORD.every(([, ok]) => ok(p || ''));

export default function PortaAurya({ vista: vistaIniziale = 'entra', emailIniziale = '', onDentro, contesto = 'porta' }) {
  const { t, i18n } = useTranslation('storefront');
  const [vista, setVista] = useState(vistaIniziale);       // entra | crea | inviata
  const [email, setEmail] = useState(emailIniziale || '');
  const [password, setPassword] = useState('');
  const [nome, setNome] = useState('');
  const [legale, setLegale] = useState(false);            // obbligatoria (AP-L)
  const [cerchio, setCerchio] = useState(false);          // SEPARATA, mai preselezionata (NL2)
  const [busy, setBusy] = useState(false);
  const [errore, setErrore] = useState(null);

  const lingua = () => {
    const l = (i18n.language || '').slice(0, 2).toLowerCase();
    return ['it', 'en', 'de', 'fr'].includes(l) ? l : 'it';
  };
  const emailOk = email.includes('@');

  /* la sessione: stessa strada di tutte le porte (AccountLoginPage, AuryaQuickLogin) */
  const apri = async (res) => {
    localStorage.setItem(PLATFORM_TOKEN_KEY, res.data.access_token);
    if (res.data.subscriber_token) salvaProva(res.data.subscriber_token);
    const me = await platformApi.get('/platform/me');
    onDentro?.(me.data, { verificaMorbida: !!res.data.verifica_morbida });
  };
  const gestisciErrore = (err, fallback) => {
    const status = err?.response?.status;
    const detail = err?.response?.data?.detail || '';
    if (status === 429) return setErrore(t('porta.troppi', { defaultValue: 'Troppi tentativi ravvicinati: aspetta un minuto e riprova.' }));
    if (status === 423) return setErrore(t('porta.bloccato', { defaultValue: 'Troppi tentativi: riprova più tardi o usa «Password dimenticata».' }));
    if (status === 403 && detail === 'EMAIL_NOT_VERIFIED') return setErrore(t('porta.nonVerificata', { defaultValue: 'Prima conferma la tua email: controlla la posta (anche lo spam).' }));
    if (status === 409) { setVista('entra'); return setErrore(t('porta.esiste', { defaultValue: 'Questa email ha già un account Aurya: entra con la tua password.' })); }
    if (status === 400 && detail) return setErrore(String(detail));
    setErrore(fallback);
  };

  const entra = async (e) => {
    e?.preventDefault();
    if (!emailOk || !password) return;
    setBusy(true); setErrore(null);
    try {
      const res = await platformApi.post('/platform/auth/login', { email: email.trim(), password });
      await apri(res);
    } catch (err) {
      gestisciErrore(err, t('porta.credenziali', { defaultValue: 'Email o password non corretti.' }));
    } finally { setBusy(false); }
  };

  const crea = async (e) => {
    e?.preventDefault();
    if (!emailOk || !passwordValida(password) || !legale) return;
    setBusy(true); setErrore(null);
    try {
      const res = await platformApi.post('/platform/auth/signup', {
        name: nome.trim() || undefined,
        email: email.trim(),
        password,
        language: lingua(),
        accepted_terms: true,
        wants_newsletter: !!cerchio,
        consenso_versione: VERSIONE_CORRENTE,
      });
      if (res.data?.access_token) await apri(res);   // E6 acceso: dentro subito
      else setVista('inviata');                        // spento: prima il clic nell'email
    } catch (err) {
      gestisciErrore(err, t('porta.creazioneFallita', { defaultValue: 'Registrazione non riuscita. Riprova tra un minuto.' }));
    } finally { setBusy(false); }
  };

  const invio = (fn) => (e) => { if (e.key === 'Enter') { e.preventDefault(); fn(e); } };

  if (vista === 'inviata') {
    return (
      <div className="rounded-lg border border-emerald-200 bg-emerald-50/60 p-3 space-y-2" data-testid="porta-aurya-inviata">
        <p className="text-sm text-emerald-900">
          {t('porta.inviata', { defaultValue: 'Ti abbiamo scritto a {{email}}: apri l’email e conferma. Poi entra con la tua password.', email: email.trim() })}
        </p>
        <button type="button" className={LINK} data-testid="porta-aurya-vai-entra"
          onClick={() => { setVista('entra'); setErrore(null); }}>
          {t('porta.hoConfermato', { defaultValue: 'Ho confermato: entro' })}
        </button>
      </div>
    );
  }

  if (vista === 'crea') {
    return (
      <div className="space-y-2" data-testid="porta-aurya-crea">
        <p className="text-xs font-medium text-gray-800">{t('porta.creaTitolo', { defaultValue: 'Crea il tuo account Aurya' })}</p>
        <input type="text" value={nome} maxLength={120} autoComplete="name" onChange={(e) => setNome(e.target.value)}
          onKeyDown={invio(crea)} placeholder={t('porta.nome', { defaultValue: 'Il tuo nome' })} className={INPUT} data-testid="porta-aurya-nome" />
        <input type="email" value={email} autoComplete="email" onChange={(e) => setEmail(e.target.value)}
          onKeyDown={invio(crea)} placeholder={t('porta.email', { defaultValue: 'La tua email' })} className={INPUT} data-testid="porta-aurya-email" />
        <input type="password" value={password} autoComplete="new-password" onChange={(e) => setPassword(e.target.value)}
          onKeyDown={invio(crea)} placeholder={t('porta.nuovaPassword', { defaultValue: 'Scegli una password' })} className={INPUT} data-testid="porta-aurya-password" />
        {password.length > 0 && !passwordValida(password) && (
          <ul className="flex flex-wrap gap-x-3 gap-y-0.5 text-[11px]" data-testid="porta-aurya-regole">
            {REGOLE_PASSWORD.map(([k, ok, label]) => (
              <li key={k} className={ok(password) ? 'text-emerald-700' : 'text-gray-500'}>{ok(password) ? '✓' : '·'} {label}</li>
            ))}
          </ul>
        )}
        {/* AP-L: senza questa spunta il server rifiuta (400) */}
        <label className="flex items-start gap-2 text-[12px] text-gray-700 cursor-pointer">
          <input type="checkbox" checked={legale} onChange={(e) => setLegale(e.target.checked)}
            className="mt-0.5 h-4 w-4 shrink-0" data-testid="porta-aurya-legale" />
          <span>
            {t('porta.legale', { defaultValue: 'Accetto i' })}{' '}
            <a href="/termini" target="_blank" rel="noopener noreferrer" className="underline">{t('porta.termini', { defaultValue: 'Termini' })}</a>
            {' '}{t('porta.eLa', { defaultValue: 'e la' })}{' '}
            <a href="/privacy" target="_blank" rel="noopener noreferrer" className="underline">{t('porta.privacy', { defaultValue: 'Privacy' })}</a>
            {' '}{t('porta.diAurya', { defaultValue: 'di Aurya' })}
          </span>
        </label>
        {/* NL2 / Lotto D: la casella del Cerchio e' SEPARATA e SPENTA; il testo e' quello unico e versionato */}
        <label className="flex items-start gap-2 text-[12px] text-gray-700 cursor-pointer rounded-lg border border-[#c9b37e]/50 bg-[#faf6ec] px-2.5 py-2">
          <input type="checkbox" checked={cerchio} onChange={(e) => setCerchio(e.target.checked)}
            className="mt-0.5 h-4 w-4 shrink-0" style={{ accentColor: '#2f5749' }} data-testid="porta-aurya-cerchio" />
          <span>
            {testoConsenso().testo}
            <span className="block text-[11px] text-gray-500">
              {t('porta.cerchioValore', { defaultValue: 'Con la Lettera ascolti le meditazioni complete e ricevi i ritiri in anteprima.' })}
            </span>
          </span>
        </label>
        <button type="button" onClick={crea} disabled={busy || !emailOk || !passwordValida(password) || !legale}
          className={BOTTONE} data-testid="porta-aurya-crea-submit">
          {busy ? t('porta.creo', { defaultValue: 'Creo l’account…' }) : t('porta.creaBottone', { defaultValue: 'Crea l’account' })}
        </button>
        <button type="button" className={LINK} data-testid="porta-aurya-vai-entra"
          onClick={() => { setVista('entra'); setErrore(null); }}>
          {t('porta.haiAccount', { defaultValue: 'Hai già un account? Entra' })}
        </button>
        {errore && <p className="text-[11px] text-red-600" data-testid="porta-aurya-errore">{errore}</p>}
      </div>
    );
  }

  return (
    <div className="space-y-2" data-testid="porta-aurya-entra">
      <input type="email" value={email} autoComplete="email" onChange={(e) => setEmail(e.target.value)} onKeyDown={invio(entra)}
        placeholder={t('porta.email', { defaultValue: 'La tua email' })} className={INPUT} data-testid="porta-aurya-email" />
      <div className="flex gap-2">
        <input type="password" value={password} autoComplete="current-password" onChange={(e) => setPassword(e.target.value)} onKeyDown={invio(entra)}
          placeholder={t('porta.password', { defaultValue: 'La tua password' })} className={INPUT} data-testid="porta-aurya-password" />
        <button type="button" onClick={entra} disabled={busy || !emailOk || !password}
          className="shrink-0 rounded-lg bg-gray-900 text-white px-3 py-2 text-sm font-medium disabled:opacity-50" data-testid="porta-aurya-entra-submit">
          {busy ? t('porta.verifico', { defaultValue: 'Verifico…' }) : t('porta.entra', { defaultValue: 'Entra' })}
        </button>
      </div>
      <div className="flex flex-wrap gap-x-3 gap-y-1">
        <button type="button" className={LINK} data-testid="porta-aurya-vai-crea" onClick={() => { setVista('crea'); setErrore(null); }}>
          {t('porta.nonHaiAccount', { defaultValue: 'Non hai un account? Crealo' })}
        </button>
        <a href={`/accedi?vista=recupero${email ? `&email=${encodeURIComponent(email.trim())}` : ''}`} className={LINK} data-testid="porta-aurya-reset">
          {t('porta.dimenticata', { defaultValue: 'Password dimenticata?' })}
        </a>
      </div>
      {errore && <p className="text-[11px] text-red-600" data-testid="porta-aurya-errore">{errore}</p>}
    </div>
  );
}
