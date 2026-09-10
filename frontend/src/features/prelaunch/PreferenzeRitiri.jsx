/**
 * PreferenzeRitiri — IL blocco delle preferenze sui ritiri, uno solo
 * (FV5, 10/9/2026 sera, founder: «tutti i posti in cui c'e' l'iscrizione
 * al Cerchio, le preferenze e i ritiri devono avere la stessa struttura
 * dell'iscrizione della landing principale»).
 *
 * Prima c'erano DUE blocchi con due vocabolari: il modulo pieno di
 * /cerca-ritiro (14 vie storiche + citta' + dove + budget) e il blocco
 * «avvisami» della Lettera (14 vie nel vocabolario del backend + citta'
 * + «vicino/anche lontano»). Stessa domanda, due forme. Ora la forma e'
 * questa, ovunque: nel modulo di /cerca-ritiro, dentro il flag «avvisami»
 * dei form della Lettera (home, /newsletter, Magazine) e nella pagina
 * delle preferenze. Le chiavi salvate restano quelle del backend
 * (BASE_TO_EXP), le etichette quelle di prelaunch.json form.interests.
 */
import React from 'react';
import { useTranslation } from 'react-i18next';

// Le quattordici vie (chiavi storiche dei chip; etichette i18n form.interests.*)
export const VIE = ['yoga', 'meditation', 'breathwork', 'sound', 'reiki', 'constellations',
                    'astrology', 'ayurveda', 'tantra', 'detox', 'nature', 'women',
                    'growth', 'mixed'];
// chip → vocabolario del backend (EXPERIENCE_INTERESTS in routers/subscribers.py)
export const BASE_TO_EXP = {
  yoga: 'yoga', meditation: 'meditazione', breathwork: 'breathwork',
  sound: 'suono', reiki: 'reiki', constellations: 'costellazioni',
  astrology: 'astrologia', ayurveda: 'ayurveda', tantra: 'tantra',
  detox: 'detox', nature: 'cammini', women: 'femminile', growth: 'crescita',
  mixed: 'misto',
};
export const EXP_TO_BASE = Object.fromEntries(Object.entries(BASE_TO_EXP).map(([b, e]) => [e, b]));
export const TRAVELS = ['near', 'italy', 'abroad'];
export const BUDGETS = ['under500', '500to1000', 'over1000', 'flexible'];

export const versoBackend = (interessi) =>
  [...new Set((interessi || []).map((i) => BASE_TO_EXP[i]).filter(Boolean))];
export const dalBackend = (interessi) =>
  [...new Set((interessi || []).map((i) => EXP_TO_BASE[i]).filter(Boolean))];

const INPUT = 'w-full rounded-xl border border-gray-300 bg-white px-4 py-3 text-sm text-foreground outline-none';

export default function PreferenzeRitiri({
  accent = '#376254',
  interests = [], onToggleInterest,
  city = '', setCity,
  travel = '', setTravel,
  budget = '', setBudget = null, showBudget = false,
  light = false,                 // solo la citta' (variante leggera della home)
  inputCls = INPUT, selectCls = null, ringStyle = {},
}) {
  const { t } = useTranslation('prelaunch');
  const sel = (v) => (selectCls ? selectCls(v) : `${INPUT} ${v ? '' : 'text-gray-500'}`);
  return (
    <div className="space-y-3" data-testid="preferenze-ritiri">
      <input
        type="text" value={city} onChange={(e) => setCity(e.target.value)} maxLength={120}
        aria-label={t('form.trCity', { defaultValue: 'Dove vivi? Città o zona' })}
        placeholder={t('form.trCity', { defaultValue: 'Dove vivi? Città o zona' })}
        className={inputCls} style={ringStyle}
      />
      {!light && (
        <>
          <div>
            <p className="mb-1.5 text-xs font-medium text-muted-foreground">
              {t('form.interestsLabel', { defaultValue: 'Cosa ti chiama? Scegli pure più di una via' })}
            </p>
            <div className="flex flex-wrap gap-1.5">
              {VIE.map((k) => {
                const on = interests.includes(k);
                return (
                  <button key={k} type="button" onClick={() => onToggleInterest(k)} aria-pressed={on}
                    className="rounded-full border px-3 py-1.5 text-xs font-medium transition-colors"
                    style={on
                      ? { background: accent, borderColor: accent, color: '#fff' }
                      : { borderColor: `${accent}44`, color: '#4b5563', background: '#fff' }}>
                    {t(`form.interests.${k}`, { defaultValue: k })}
                  </button>
                );
              })}
            </div>
          </div>
          <select value={travel} onChange={(e) => setTravel(e.target.value)}
                  className={sel(travel)} style={ringStyle}
                  aria-label={t('form.travelLabel', { defaultValue: 'Dove ti immagini il tuo ritiro?' })}>
            <option value="">{t('form.travelLabel', { defaultValue: 'Dove ti immagini il tuo ritiro?' })}</option>
            {TRAVELS.map((k) => (
              <option key={k} value={k}>{t(`form.travel.${k}`, { defaultValue: k })}</option>
            ))}
          </select>
          {showBudget && setBudget && (
            <select value={budget} onChange={(e) => setBudget(e.target.value)}
                    className={sel(budget)} style={ringStyle}
                    aria-label={t('form.budgetLabel', { defaultValue: 'Quanto vorresti investire in un ritiro?' })}>
              <option value="">{t('form.budgetLabel', { defaultValue: 'Quanto vorresti investire in un ritiro?' })}</option>
              {BUDGETS.map((k) => (
                <option key={k} value={k}>{t(`form.budget.${k}`, { defaultValue: k })}</option>
              ))}
            </select>
          )}
        </>
      )}
    </div>
  );
}
