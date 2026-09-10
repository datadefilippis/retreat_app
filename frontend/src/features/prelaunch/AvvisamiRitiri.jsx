/**
 * AvvisamiRitiri — IL blocco «Avvisami anche quando Aurya propone
 * esperienze e ritiri», uno solo, ovunque si entra nel Cerchio.
 *
 * US (10/9/2026 notte, founder): «nelle varie newsletter oltre alla
 * landing dove proponiamo di essere notificati per i ritiri non abbiamo
 * messo lo stesso schema di informazioni che abbiamo per la landing,
 * non sarebbe il caso di integrarlo ovunque lo stesso sistema?» e
 * «nella newsletter delle meditazioni invece non mettiamo opzioni di
 * ritiri?».
 *
 * Prima: la home mostrava SOLO la citta' (variante «leggera»), i form
 * della Lettera (newsletter, Magazine) vie + citta' + dove senza il
 * budget, i cancelli delle meditazioni e InvitoSound solo l'email.
 * Ora: lo stesso flag (spento o acceso secondo la superficie) e, acceso,
 * le stesse quattro cose di /cerca-ritiro: dove vivi, le vie, dove ti
 * immagini il ritiro, quanto vorresti investire. Chi non accende il
 * flag non da' nulla: dati raccolti = dati scelti (FV5 resta).
 *
 * Due vestiti, una sostanza: chiaro (form della Lettera) e scuro (il
 * mondo Sound: meditazioni, cancello della traccia, InvitoSound).
 */
import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import PreferenzeRitiri, { versoBackend } from './PreferenzeRitiri';

/** lo stato del blocco per i form che non sono LeadForm (i cancelli) */
export function useAvvisamiRitiri(acceso = false) {
  const [enabled, setEnabled] = useState(acceso);
  const [interests, setInterests] = useState([]);
  const [city, setCity] = useState('');
  const [travel, setTravel] = useState('');
  const [budget, setBudget] = useState('');
  const onToggleInterest = (k) => setInterests((prev) =>
    (prev.includes(k) ? prev.filter((x) => x !== k) : [...prev, k]));
  /* cosa viaggia verso /public/newsletter/subscribe (vocabolario del
     backend): le preferenze SOLO se il flag e' acceso — mai di passaggio */
  const payload = () => (enabled ? {
    wants_experiences: true,
    interests: interests.length ? versoBackend(interests) : null,
    city: city.trim() || null, travel: travel || null, budget: budget || null,
  } : { wants_experiences: false });
  return { enabled, setEnabled, interests, onToggleInterest,
           city, setCity, travel, setTravel, budget, setBudget, payload };
}

const INPUT_CHIARO = 'w-full rounded-xl border border-input bg-white px-4 py-3 text-sm text-gray-900 focus:outline-none focus:ring-2';

export default function AvvisamiRitiri({
  enabled, setEnabled,
  interests, onToggleInterest, city, setCity, travel, setTravel, budget, setBudget,
  accent = '#376254', scuro = false,
  inputCls = INPUT_CHIARO, selectCls = null, ringStyle = {},
  testid = 'avvisami-ritiri',
}) {
  const { t } = useTranslation('prelaunch');
  const sel = selectCls || ((v) => `${inputCls} ${v ? 'text-gray-900' : 'text-gray-400'}`);
  /* nel mondo Sound il CSS globale (fqz) stringe input e select alla
     misura del contenuto: qui si impone la larghezza piena. Sul chiaro
     il testo e' sempre quello del foreground, anche dentro un pannello
     posato su una fotografia (la home). */
  const stile = scuro ? { width: '100%', boxSizing: 'border-box', ...ringStyle } : ringStyle;
  return (
    <div className={`rounded-xl border p-3 text-left ${scuro ? '' : 'text-foreground'}`}
         data-testid={testid}
         style={{ borderColor: `${accent}55`,
                  background: enabled ? `${accent}${scuro ? '22' : '0a'}` : 'transparent',
                  color: scuro ? '#f6f2e8' : undefined }}>
      <label className="flex items-start gap-2.5 text-sm leading-snug" style={{ cursor: 'pointer' }}>
        <input type="checkbox" checked={enabled}
               onChange={(e) => setEnabled(e.target.checked)}
               className="mt-0.5 h-5 w-5 shrink-0" style={{ accentColor: accent }}
               data-testid={`${testid}-flag`} />
        <span>
          {t('form.expFlag', { defaultValue: 'Avvisami anche quando Aurya propone esperienze e ritiri' })}
          <span className="block text-xs opacity-75">
            {t('form.expFlagHint', { defaultValue: 'Facoltativo: ci aiuti a proporti solo cose adatte a te.' })}
          </span>
        </span>
      </label>
      {enabled && (
        <div className="mt-3 duration-300 animate-in fade-in slide-in-from-top-2">
          <PreferenzeRitiri accent={accent} interests={interests} onToggleInterest={onToggleInterest}
                            city={city} setCity={setCity} travel={travel} setTravel={setTravel}
                            budget={budget} setBudget={setBudget} scuro={scuro}
                            inputCls={inputCls} selectCls={sel} ringStyle={stile} />
        </div>
      )}
    </div>
  );
}
