/**
 * LA VERITÀ DEI PIANI (ciclo PA, 30/8/2026) — fonte unica.
 *
 * Il founder: «voglio la verità di Aurya e basta» — l'admin mostrava
 * slug crudi, palette di piani estinti (free/core/enterprise),
 * metriche AI-chat di moduli spenti e stati in inglese. Qui vive la
 * mappa unica: chi mostra un piano, uno stato o una metrica in
 * system admin passa da qui. I piani sono QUATTRO e sono tutti veri:
 * Gratis e Pro (pubblici), Founding e Partner (leve del founder,
 * 4-5/7/2026: riservati, solo-admin, invisibili al pricing).
 */

export const PIANI = {
  retreat_free: { nome: 'Gratis', classe: 'bg-gray-100 text-gray-700' },
  retreat_pro: { nome: 'Pro', classe: 'bg-violet-100 text-violet-700' },
  retreat_founding: {
    nome: 'Founding', classe: 'bg-amber-100 text-amber-700', riservato: true,
  },
  retreat_partner: {
    nome: 'Partner', classe: 'bg-emerald-100 text-emerald-700', riservato: true,
  },
};

export const nomePiano = (slug) => PIANI[slug]?.nome || slug || '—';
export const classePiano = (slug) =>
  PIANI[slug]?.classe || 'bg-gray-100 text-gray-700';

/* gli stati di fatturazione, in italiano */
export const STATI = {
  active: 'attivo',
  trialing: 'in prova',
  past_due: 'pagamento scaduto',
  canceled: 'annullato',
  manual: 'manuale',
  none: '—',
};
export const nomeStato = (s) => STATI[s] || s || '—';

/* le metriche d'uso col loro nome vero; i moduli spenti (status
   'off' — l'AI chat che non esiste) NON si mostrano */
export const METRICHE = {
  'cashflow_monitor.data_rows': 'Movimenti registrati',
  'commerce.orders_monthly': 'Ordini (mese)',
  'product_catalog.products': 'Voci a listino',
};
export const nomeMetrica = (modulo, chiave) =>
  METRICHE[`${modulo}.${chiave}`] || `${modulo}.${chiave}`;
