/**
 * LeadForm v3 — cattura lead pre-lancio profilata (PL10 + PL13).
 *
 * type: "operator" | "traveler". Il form parla la lingua del suo pubblico:
 *  - viaggiatore: nome, email, dove vive, cosa lo chiama (interessi
 *    multi-scelta), DOVE farebbe il ritiro (vicino casa / Italia /
 *    estero), budget → al lancio proposte mirate, non spam.
 *  - operatore: nome e cognome, email, telefono, località, tipo di
 *    attività + DETTAGLIO CONDIZIONALE (chi insegna/facilita sceglie le
 *    discipline; chi ospita indica tipo di struttura e capienza),
 *    due righe di presentazione → follow-up personale.
 * Solo email + consenso sono obbligatori: il form resta gentile.
 * POST /public/leads (dedup lato server, notifica a info@). Best-effort:
 * un errore non blocca mai l'utente.
 */
import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { ArrowRight, Check, Loader2 } from 'lucide-react';
import api from '../../api/client';

// Chiavi stabili salvate nel DB (le etichette sono i18n)
const INTERESTS = ['yoga', 'meditation', 'breathwork', 'sound', 'detox',
                   'nature', 'women', 'mixed'];
const BUDGETS = ['under500', '500to1000', 'over1000', 'flexible'];
const TRAVELS = ['near', 'italy', 'abroad'];
const ACTIVITIES = ['teacher', 'center', 'venue', 'organizer', 'therapist', 'other'];
// Chi insegna/facilita/organizza specifica le discipline
const DISCIPLINE_ACTIVITIES = ['teacher', 'center', 'organizer', 'therapist'];
const DISCIPLINES = ['yoga', 'meditation', 'breathwork', 'sound', 'reiki',
                     'detox', 'nature', 'women', 'other'];
const VENUE_TYPES = ['masseria', 'villa', 'retreat_center', 'bnb', 'hermitage', 'other'];
const CAPACITIES = ['upTo10', '10to20', '20to40', 'over40'];

export default function LeadForm({ type = 'traveler', accent = '#376254' }) {
  const { t, i18n } = useTranslation('prelaunch');
  const isOperator = type === 'operator';

  const [email, setEmail] = useState('');
  const [name, setName] = useState('');
  const [phone, setPhone] = useState('');
  const [city, setCity] = useState('');
  const [interests, setInterests] = useState([]);
  const [travel, setTravel] = useState('');
  const [budget, setBudget] = useState('');
  const [activity, setActivity] = useState('');
  const [disciplines, setDisciplines] = useState([]);
  const [venueType, setVenueType] = useState('');
  const [capacity, setCapacity] = useState('');
  const [message, setMessage] = useState('');
  const [consent, setConsent] = useState(false);
  const [state, setState] = useState('idle');   // idle | sending | done

  const toggle = (setter) => (key) => setter((prev) =>
    prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key]);
  const toggleInterest = toggle(setInterests);
  const toggleDiscipline = toggle(setDisciplines);

  const askDisciplines = isOperator && DISCIPLINE_ACTIVITIES.includes(activity);
  const askVenue = isOperator && activity === 'venue';

  const submit = async (e) => {
    e.preventDefault();
    if (!email || !consent || state === 'sending') return;
    setState('sending');
    try {
      await api.post('/public/leads', {
        email: email.trim(), name: name.trim() || null, type,
        phone: isOperator ? (phone.trim() || null) : null,
        city: city.trim() || null,
        interests: !isOperator && interests.length ? interests : null,
        travel: !isOperator ? (travel || null) : null,
        budget: !isOperator ? (budget || null) : null,
        activity: isOperator ? (activity || null) : null,
        disciplines: askDisciplines && disciplines.length ? disciplines : null,
        venue_type: askVenue ? (venueType || null) : null,
        capacity: askVenue ? (capacity || null) : null,
        message: isOperator ? (message.trim() || null) : null,
        consent: true, language: (i18n.language || 'it').slice(0, 2),
      });
    } catch { /* best-effort: mostriamo comunque il grazie */ }
    setState('done');
  };

  if (state === 'done') {
    return (
      <div className="rounded-2xl border p-6 text-center"
           style={{ borderColor: `${accent}55`, background: `${accent}0d` }}>
        <div className="mx-auto mb-3 flex h-11 w-11 items-center justify-center rounded-full"
             style={{ background: accent }}>
          <Check className="h-6 w-6 text-white" />
        </div>
        <p className="font-heading text-lg font-semibold text-foreground">
          {t('form.thanksTitle', { defaultValue: 'Ci sei. Benvenuto.' })}
        </p>
        <p className="mt-1 text-sm text-muted-foreground">
          {isOperator
            ? t('form.thanksOp', { defaultValue: 'Grazie per esserti presentato: ti scriviamo personalmente prima del lancio.' })
            : t('form.thanksTr', { defaultValue: 'Al lancio riceverai una selezione di ritiri pensata per te. A presto.' })}
        </p>
      </div>
    );
  }

  const inputCls = 'w-full rounded-xl border border-input bg-white px-4 py-3 text-sm text-gray-900 focus:outline-none focus:ring-2';
  const ringStyle = { '--tw-ring-color': accent };
  const selectCls = (val) => `${inputCls} ${val ? 'text-gray-900' : 'text-gray-400'}`;

  const Chips = ({ options, active, onToggle, i18nPrefix }) => (
    <div className="flex flex-wrap gap-1.5">
      {options.map((k) => {
        const on = active.includes(k);
        return (
          <button
            key={k} type="button" onClick={() => onToggle(k)}
            aria-pressed={on}
            className="rounded-full border px-3 py-1.5 text-xs font-medium transition-colors"
            style={on
              ? { background: accent, borderColor: accent, color: '#fff' }
              : { borderColor: `${accent}44`, color: '#4b5563', background: '#fff' }}
          >
            {t(`${i18nPrefix}.${k}`, { defaultValue: k })}
          </button>
        );
      })}
    </div>
  );

  return (
    <form onSubmit={submit} className="space-y-3">
      <input
        type="text" value={name} onChange={(e) => setName(e.target.value)}
        placeholder={isOperator
          ? t('form.fullName', { defaultValue: 'Nome e cognome' })
          : t('form.name', { defaultValue: 'Il tuo nome' })}
        className={inputCls} style={ringStyle}
      />
      <input
        type="email" required value={email} onChange={(e) => setEmail(e.target.value)}
        placeholder={t('form.email', { defaultValue: 'La tua email' })}
        className={inputCls} style={ringStyle}
      />

      {isOperator ? (
        <>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <input
              type="tel" value={phone} onChange={(e) => setPhone(e.target.value)}
              placeholder={t('form.phone', { defaultValue: 'Telefono' })}
              className={inputCls} style={ringStyle}
            />
            <input
              type="text" value={city} onChange={(e) => setCity(e.target.value)}
              placeholder={t('form.opCity', { defaultValue: 'Dove si trova la tua attività' })}
              className={inputCls} style={ringStyle}
            />
          </div>
          <select
            value={activity} onChange={(e) => setActivity(e.target.value)}
            className={selectCls(activity)} style={ringStyle}
          >
            <option value="">{t('form.activityLabel', { defaultValue: 'Di cosa ti occupi?' })}</option>
            {ACTIVITIES.map((k) => (
              <option key={k} value={k}>
                {t(`form.activity.${k}`, { defaultValue: k })}
              </option>
            ))}
          </select>

          {/* PL13 — dettaglio condizionale: la domanda giusta al momento giusto */}
          {askDisciplines && (
            <div>
              <p className="mb-1.5 text-xs font-medium text-muted-foreground">
                {t('form.disciplinesLabel', { defaultValue: 'Quali discipline proponi?' })}
              </p>
              <Chips options={DISCIPLINES} active={disciplines}
                     onToggle={toggleDiscipline} i18nPrefix="form.disciplines" />
            </div>
          )}
          {askVenue && (
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <select
                value={venueType} onChange={(e) => setVenueType(e.target.value)}
                className={selectCls(venueType)} style={ringStyle}
              >
                <option value="">{t('form.venueTypeLabel', { defaultValue: 'Che struttura sei?' })}</option>
                {VENUE_TYPES.map((k) => (
                  <option key={k} value={k}>
                    {t(`form.venueType.${k}`, { defaultValue: k })}
                  </option>
                ))}
              </select>
              <select
                value={capacity} onChange={(e) => setCapacity(e.target.value)}
                className={selectCls(capacity)} style={ringStyle}
              >
                <option value="">{t('form.capacityLabel', { defaultValue: 'Quanti posti letto?' })}</option>
                {CAPACITIES.map((k) => (
                  <option key={k} value={k}>
                    {t(`form.capacity.${k}`, { defaultValue: k })}
                  </option>
                ))}
              </select>
            </div>
          )}

          <textarea
            value={message} onChange={(e) => setMessage(e.target.value)}
            rows={3} maxLength={1000}
            placeholder={t('form.description', { defaultValue: 'Raccontaci la tua attività in due righe: cosa proponi, da quanto, a chi.' })}
            className={`${inputCls} resize-none`} style={ringStyle}
          />
        </>
      ) : (
        <>
          <input
            type="text" value={city} onChange={(e) => setCity(e.target.value)}
            placeholder={t('form.trCity', { defaultValue: 'Dove vivi? Città o zona' })}
            className={inputCls} style={ringStyle}
          />
          <div>
            <p className="mb-1.5 text-xs font-medium text-muted-foreground">
              {t('form.interestsLabel', { defaultValue: 'Cosa ti chiama? Scegli pure più di una via' })}
            </p>
            <Chips options={INTERESTS} active={interests}
                   onToggle={toggleInterest} i18nPrefix="form.interests" />
          </div>
          {/* PL13 — raggio del viaggio: vicino casa, Italia o anche estero */}
          <select
            value={travel} onChange={(e) => setTravel(e.target.value)}
            className={selectCls(travel)} style={ringStyle}
          >
            <option value="">{t('form.travelLabel', { defaultValue: 'Dove ti immagini il tuo ritiro?' })}</option>
            {TRAVELS.map((k) => (
              <option key={k} value={k}>
                {t(`form.travel.${k}`, { defaultValue: k })}
              </option>
            ))}
          </select>
          <select
            value={budget} onChange={(e) => setBudget(e.target.value)}
            className={selectCls(budget)} style={ringStyle}
          >
            <option value="">{t('form.budgetLabel', { defaultValue: 'Quanto vorresti investire in un ritiro?' })}</option>
            {BUDGETS.map((k) => (
              <option key={k} value={k}>
                {t(`form.budget.${k}`, { defaultValue: k })}
              </option>
            ))}
          </select>
        </>
      )}

      <label className="flex items-start gap-2 text-xs text-muted-foreground">
        <input type="checkbox" checked={consent}
               onChange={(e) => setConsent(e.target.checked)}
               className="mt-0.5 h-4 w-4 shrink-0" required />
        <span>
          {t('form.consent', { defaultValue: 'Acconsento a essere contattato via email sul lancio di Aurya.' })}{' '}
          <a href="/privacy" target="_blank" rel="noreferrer" className="underline">
            {t('form.privacy', { defaultValue: 'Privacy' })}
          </a>
        </span>
      </label>
      <button
        type="submit" disabled={!email || !consent || state === 'sending'}
        className="inline-flex w-full items-center justify-center gap-2 rounded-xl px-5 py-3 text-sm font-semibold text-white transition-opacity disabled:opacity-50"
        style={{ background: accent }}
      >
        {state === 'sending'
          ? <Loader2 className="h-4 w-4 animate-spin" />
          : <>
              {isOperator
                ? t('form.ctaOp', { defaultValue: 'Voglio esserci al lancio' })
                : t('form.ctaTr', { defaultValue: 'Trovami il mio ritiro' })}
              <ArrowRight className="h-4 w-4" />
            </>}
      </button>
    </form>
  );
}
