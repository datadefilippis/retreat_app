/**
 * StrisciaBentornato — «Ciao Marilisa, la tua pagina è al passo 1 di 3»
 * (25/9/2026, founder). Sulle pagine PUBBLICHE, a chi ha il cappello
 * operatore: una riga sottile sotto l'intestazione che dice che sei
 * dentro, a che punto sei e dove continuare. Nasce dal caso vero del
 * 24/9: un'operatrice con la sessione aperta ha rifatto la registrazione
 * perche' il sito non le diceva mai «sei dentro» (il puntino verde
 * sull'omino non basta al primo giorno).
 *
 * Lo stato arriva da /organizations/current/onboarding-status, letto
 * una volta per sessione (cache di modulo) e mai bloccante: senza
 * risposta la striscia dice solo «Il tuo spazio → Continua».
 */
import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../context/AuthContext';
import api from '../api/client';

let _cache = null;          // {passo, dest} per la sessione
let _inCorso = null;

function calcola(status) {
  const s = status?.steps || status || {};
  if (!status || status.is_complete || !('online' in s)) return { passo: null, dest: '/dashboard' };
  if (!s.profile_completed) return { passo: 1, dest: '/public-profile' };
  if (!s.listino_filled) return { passo: 2, dest: '/listino' };
  return { passo: 3, dest: '/inizia' };
}

export default function StrisciaBentornato() {
  const { t } = useTranslation('landings');
  const { user } = useAuth();
  const [stato, setStato] = useState(_cache);

  useEffect(() => {
    if (!user || user.role !== 'admin' || _cache) return undefined;
    let alive = true;
    _inCorso = _inCorso || api.get('/organizations/current/onboarding-status')
      .then((r) => calcola(r.data)).catch(() => ({ passo: null, dest: '/dashboard' }));
    _inCorso.then((v) => { _cache = v; if (alive) setStato(v); });
    return () => { alive = false; };
  }, [user]);

  if (!user || user.role !== 'admin') return null;
  const nome = (user.name || '').trim().split(' ')[0];
  const passo = stato?.passo;
  const dest = stato?.dest || '/dashboard';
  return (
    <div className="border-b border-[#e6dfcf] bg-[#f4f1ea] px-4 py-2 text-sm text-[#2e4b3f]"
         data-testid="striscia-bentornato" role="status">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-x-4 gap-y-1">
        <span>
          {nome
            ? t('bentornato.saluto', { defaultValue: 'Ciao {{nome}}, sei dentro.', nome })
            : t('bentornato.salutoSenzaNome', { defaultValue: 'Sei dentro.' })}{' '}
          {passo
            ? t('bentornato.passo', { defaultValue: 'La tua pagina è al passo {{passo}} di 3.', passo })
            : t('bentornato.pronta', { defaultValue: 'Il tuo spazio ti aspetta.' })}
        </span>
        <Link to={dest} data-testid="striscia-bentornato-cta"
              className="font-semibold underline underline-offset-2 hover:text-[#1f3a30]">
          {passo
            ? t('bentornato.continua', { defaultValue: 'Continua →' })
            : t('bentornato.vai', { defaultValue: 'Vai al tuo spazio →' })}
        </Link>
      </div>
    </div>
  );
}
