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
 * (AvvisamiRitiri: form della Lettera in home, /newsletter, Magazine, e
 * i cancelli del mondo Sound) e nella pagina delle preferenze. Le chiavi
 * salvate restano quelle del backend (BASE_TO_EXP), le etichette quelle
 * di prelaunch.json form.interests.
 * US (10/9/2026 notte, founder): «integrarlo ovunque lo stesso sistema»
 * — via la variante leggera della home (solo citta') e il budget a
 * richiesta: quattro cose, sempre le stesse.
 */
import React, { useState } from 'react';
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
  budget = '', setBudget = null,
  vieAperte = false,             // le 14 vie aperte subito (solo /cerca-ritiro)
  scuro = false,                 // il mondo Sound: chip scelte col testo scuro sull'oro
  inputCls = INPUT, selectCls = null, ringStyle = {},
}) {
  const { t } = useTranslation('prelaunch');
  const sel = (v) => (selectCls ? selectCls(v) : `${INPUT} ${v ? '' : 'text-gray-500'}`);
  /* US (10/9/2026 notte): niente piu' variante «leggera» (solo la citta')
     ne' budget a richiesta — le quattro cose sono le stesse OVUNQUE:
     dove vivi, dove ti immagini il ritiro, quanto investire, le vie.
     Founder: «tutte le categorie creano qualcosa di mastodontico»: le 14
     vie stanno dietro una riga («Cosa ti chiama?») che si apre con un
     tocco e riassume le scelte fatte; aperte subito solo dove sono
     l'oggetto della pagina (/cerca-ritiro). */
  const [vieVisibili, setVieVisibili] = useState(Boolean(vieAperte));
  const scelte = interests.length;
  return (
    <div className="space-y-3" data-testid="preferenze-ritiri">
      <input
        type="text" value={city} onChange={(e) => setCity(e.target.value)} maxLength={120}
        aria-label={t('form.trCity', { defaultValue: 'Dove vivi? Città o zona' })}
        placeholder={t('form.trCity', { defaultValue: 'Dove vivi? Città o zona' })}
        className={inputCls} style={ringStyle}
      />
      <>
          <select value={travel} onChange={(e) => setTravel(e.target.value)}
                  className={sel(travel)} style={ringStyle}
                  aria-label={t('form.travelLabel', { defaultValue: 'Dove ti immagini il tuo ritiro?' })}>
            <option value="">{t('form.travelLabel', { defaultValue: 'Dove ti immagini il tuo ritiro?' })}</option>
            {TRAVELS.map((k) => (
              <option key={k} value={k}>{t(`form.travel.${k}`, { defaultValue: k })}</option>
            ))}
          </select>
          {setBudget && (
            <select value={budget} onChange={(e) => setBudget(e.target.value)}
                    className={sel(budget)} style={ringStyle}
                    aria-label={t('form.budgetLabel', { defaultValue: 'Quanto vorresti investire in un ritiro?' })}>
              <option value="">{t('form.budgetLabel', { defaultValue: 'Quanto vorresti investire in un ritiro?' })}</option>
              {BUDGETS.map((k) => (
                <option key={k} value={k}>{t(`form.budget.${k}`, { defaultValue: k })}</option>
              ))}
            </select>
          )}
          <div>
            {/* la riga che apre le vie: stile inline perche' nel mondo Sound
                il CSS globale veste ogni <button> da pulsante */}
            <button type="button" onClick={() => setVieVisibili((v) => !v)}
                    aria-expanded={vieVisibili} data-testid="preferenze-vie-toggle"
                    className="flex w-full items-center justify-between gap-2 text-left text-sm"
                    style={{ background: 'transparent', border: 'none', padding: '2px 0',
                             font: 'inherit', cursor: 'pointer',
                             // sul chiaro il testo e' quello del corpo anche dentro una
                             // scheda bianca posata su una foto (l'apertura di /cerca-ritiro
                             // eredita il crema dell'hero); sullo scuro eredita il --bone
                             color: scuro ? 'inherit' : '#1f2f28',
                             textTransform: 'none', letterSpacing: 0, boxShadow: 'none' }}>
              <span>
                <span className="font-medium">{t('form.interestsShort', { defaultValue: 'Cosa ti chiama?' })}</span>{' '}
                <span className="opacity-75">
                  {scelte
                    ? t('form.interestsCount', { count: scelte, defaultValue: '{{count}} vie scelte' })
                    : t('form.interestsOptional', { defaultValue: 'scegli le tue vie (facoltativo)' })}
                </span>
              </span>
              <span aria-hidden className="shrink-0 opacity-70">{vieVisibili ? '▴' : '▾'}</span>
            </button>
            {vieVisibili && (
              <div className="mt-2 flex flex-wrap gap-1.5" data-testid="preferenze-vie">
                {VIE.map((k) => {
                  const on = interests.includes(k);
                  return (
                    <button key={k} type="button" onClick={() => onToggleInterest(k)} aria-pressed={on}
                      className="rounded-full border px-2.5 py-1 text-xs font-medium transition-colors"
                      style={on
                        ? { background: accent, borderColor: accent, color: scuro ? '#14212b' : '#fff',
                            textTransform: 'none', letterSpacing: 0 }
                        : { borderColor: `${accent}55`, color: '#374151', background: '#fff',
                            textTransform: 'none', letterSpacing: 0 }}>
                      {t(`form.interests.${k}`, { defaultValue: k })}
                    </button>
                  );
                })}
              </div>
            )}
          </div>
      </>
    </div>
  );
}
