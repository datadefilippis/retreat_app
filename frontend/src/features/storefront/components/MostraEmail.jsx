/**
 * MostraEmail — l'email pubblica dell'operatore arriva al CLIC, non nel
 * JSON del profilo (AS2, 25/9/2026, anti-scrape senza toccare la SEO).
 *
 * Il profilo dice solo «c'è un'email» (contacts.has_email); chi vuole
 * scriverle preme e il server la consegna da una rotta a parte, con un
 * limite stretto per IP (GET /public/operator/{slug}/contatti). Google
 * non perde nulla: l'email non era mai stata nell'HTML che indicizza.
 * Il telefono invece resta in chiaro (LocalBusiness, SEO locale).
 */
import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import api from '../../../api/client';

export default function MostraEmail({ slug, className = '' }) {
  const { t } = useTranslation();
  const [email, setEmail] = useState(null);
  const [stato, setStato] = useState('chiuso');   // chiuso | carico | aperto | errore

  const mostra = async () => {
    setStato('carico');
    try {
      const r = await api.get(`/public/operator/${slug}/contatti`);
      const e = r.data?.public_email || null;
      setEmail(e);
      setStato(e ? 'aperto' : 'errore');
    } catch {
      setStato('errore');
    }
  };

  if (stato === 'aperto' && email) {
    return (
      <a href={`mailto:${email}`} className={`text-primary hover:underline break-all ${className}`}
         data-testid="mostra-email-link">{email}</a>
    );
  }
  if (stato === 'errore') {
    return (
      <span className={`text-muted-foreground ${className}`} data-testid="mostra-email-errore">
        {t('landings:operator.emailNonDisponibile', { defaultValue: 'Email non disponibile ora, riprova tra poco.' })}
      </span>
    );
  }
  return (
    <button type="button" onClick={mostra} disabled={stato === 'carico'}
            className={`text-primary underline underline-offset-2 hover:opacity-80 disabled:opacity-50 ${className}`}
            data-testid="mostra-email">
      {stato === 'carico'
        ? t('landings:operator.emailCarico', { defaultValue: 'Un attimo…' })
        : t('landings:operator.mostraEmail', { defaultValue: 'Mostra l’email' })}
    </button>
  );
}
