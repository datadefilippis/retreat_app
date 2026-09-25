/**
 * GiaDentro — «Sei già dentro» (25/9/2026, founder).
 *
 * Caso vero in prod (24/9): un'operatrice, gia' registrata e con la
 * sessione aperta, torna sulla home, trova «Apri il tuo spazio», compila
 * di nuovo la registrazione (con la S maiuscola messa dal telefono) e si
 * ritrova con due account. Il sito non le aveva mai detto «sei gia'
 * dentro». Questa scheda lo dice, al posto del form, ovunque ci si
 * possa registrare o accedere come professionista: /accedi (tutte e due
 * le viste) e la landing /entra-nella-rete. Tre gesti: vai al gestionale,
 * completa la pagina, oppure «non sono io» → esci e il form riappare.
 */
import React from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { CheckCircle2 } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export default function GiaDentro({ compatto = false }) {
  const { t } = useTranslation('landings');
  const { user, logout } = useAuth();
  if (!user) return null;
  const nome = (user.name || '').trim().split(' ')[0];
  // il system admin non ha una pagina: solo la porta della regia
  const isSys = user.role === 'system_admin';
  const gestionale = isSys ? '/admin' : '/dashboard';
  return (
    <div className="text-center" data-testid="gia-dentro">
      <CheckCircle2 className="mx-auto h-8 w-8 text-[#2f5749]" aria-hidden />
      <p className="mt-3 font-display text-xl text-[#2e4b3f]">
        {nome
          ? t('giaDentro.titoloNome', { defaultValue: 'Sei già dentro, {{nome}}.', nome })
          : t('giaDentro.titolo', { defaultValue: 'Sei già dentro.' })}
      </p>
      <p className="mt-2 text-sm text-gray-600 leading-relaxed">
        {t('giaDentro.testo', { defaultValue: 'Il tuo spazio è già aperto con {{email}}: non serve registrarsi di nuovo.', email: user.email })}
      </p>
      <div className={`mt-5 flex flex-col gap-2 ${compatto ? '' : 'sm:flex-row sm:justify-center'}`}>
        {!isSys && (
          <Link to="/public-profile" data-testid="gia-dentro-pagina"
                className="rounded-xl bg-[#376254] px-5 py-2.5 text-sm font-semibold text-white hover:bg-[#2e5346]">
            {t('giaDentro.pagina', { defaultValue: 'Completa la tua pagina' })}
          </Link>
        )}
        <Link to={gestionale} data-testid="gia-dentro-gestionale"
              className="rounded-xl border border-gray-300 px-5 py-2.5 text-sm font-semibold text-gray-800 hover:border-[#376254] hover:text-[#376254]">
          {t('giaDentro.gestionale', { defaultValue: 'Vai al tuo gestionale' })}
        </Link>
      </div>
      <button type="button" onClick={() => logout()} data-testid="gia-dentro-esci"
              className="mt-4 text-xs text-gray-500 underline underline-offset-2 hover:text-gray-700">
        {t('giaDentro.esci', { defaultValue: 'Non sei tu? Esci e riprova con un altro indirizzo' })}
      </button>
    </div>
  );
}
