/**
 * BannerVerificaEmail — E6 (24/9/2026, founder): con il login senza
 * verifica l'operatore lavora subito; questo avviso, discreto e fisso
 * in cima al gestionale, gli ricorda che l'indirizzo non e' ancora
 * confermato e cosa resta chiuso finche' non clicca un link di una
 * nostra email (pagina online, Stripe/IBAN, pagamenti). Un solo gesto:
 * «Rimandami il link». Sparisce da solo quando /auth/me dice verificato.
 */
import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { MailCheck } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { authAPI } from '../api/auth';

export default function BannerVerificaEmail() {
  const { t } = useTranslation('common');
  const { user } = useAuth();
  const [stato, setStato] = useState('');   // '' | 'inviato' | 'errore'

  if (!user || user.role === 'system_admin' || user.email_verified !== false || !user.verifica_morbida) {
    return null;
  }

  const rimanda = async () => {
    try { await authAPI.resendVerification(user.email); setStato('inviato'); }
    catch { setStato('errore'); }
  };

  return (
    <div className="border-b border-amber-200 bg-amber-50 px-4 py-2.5 text-sm text-amber-900"
         data-testid="banner-verifica-email" role="status">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-3 gap-y-1">
        <MailCheck className="h-4 w-4 shrink-0" aria-hidden />
        <span className="flex-1 min-w-[16rem]">
          {t('verificaEmail.testo', { defaultValue: 'Ti abbiamo scritto a {{email}}: apri un link qualsiasi di quell’email e l’indirizzo è confermato. Fino ad allora la pagina non va online e i pagamenti restano chiusi.', email: user.email })}
        </span>
        {stato === 'inviato' ? (
          <span className="font-medium" data-testid="banner-verifica-inviato">
            {t('verificaEmail.inviato', { defaultValue: 'Fatto, controlla la posta.' })}
          </span>
        ) : (
          <button type="button" onClick={rimanda} data-testid="banner-verifica-rimanda"
                  className="font-semibold underline underline-offset-2 hover:text-amber-950">
            {t('verificaEmail.rimanda', { defaultValue: 'Rimandami il link' })}
          </button>
        )}
        {stato === 'errore' && (
          <span className="text-red-700">{t('verificaEmail.errore', { defaultValue: 'Non è partita, riprova tra un minuto.' })}</span>
        )}
      </div>
    </div>
  );
}
