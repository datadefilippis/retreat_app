/**
 * LeadForm v3 — cattura lead pre-lancio profilata (PL10 + PL13).
 *
 * type: "operator" | "traveler". Il form parla la lingua del suo pubblico:
 *  - viaggiatore: nome, email, dove vive, cosa lo chiama (interessi
 *    multi-scelta), DOVE farebbe il ritiro (vicino casa / Italia /
 *    estero), budget → al lancio proposte mirate, non spam.
 *  - operatore (OL3b, specifica del founder): nome e cognome, email,
 *    telefono, sito o Instagram, dove lavori, di cosa ti occupi e infine
 *    LA DOMANDA — "qual e' la cosa che vorresti far capire alle persone
 *    del tuo lavoro?" — che vale l'intera candidatura e quindi non e'
 *    una riga come le altre: etichetta visibile e campo alto.
 *    Il dettaglio condizionale di PL13 (discipline / tipo di struttura /
 *    capienza) e' stato tolto: erano domande da catalogo ritiri, non da
 *    conversazione, e allungavano il modulo proprio dove serve slancio.
 * Nella candidatura sono obbligatori nome, email e consenso; altrove
 * restano email + consenso: il form resta gentile.
 * POST /public/leads (dedup lato server, notifica a info@). Best-effort:
 * un errore non blocca mai l'utente.
 */
import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { ArrowRight, Check, Loader2 } from 'lucide-react';
import api from '../../api/client';
import platformApi from '../../api/platformClient';
import { useAuth } from '../../context/AuthContext';
import { trackEvent } from '../../lib/analytics';

// Chiavi stabili salvate nel DB (le etichette sono i18n)
const INTERESTS = ['yoga', 'meditation', 'breathwork', 'sound', 'detox',
                   'nature', 'women', 'mixed'];
const BUDGETS = ['under500', '500to1000', 'over1000', 'flexible'];
const TRAVELS = ['near', 'italy', 'abroad'];
const ACTIVITIES = ['teacher', 'center', 'venue', 'organizer', 'therapist', 'other'];

// BN2 — mappa chip interessi (chiavi lead storiche) → topics della
// lettera (categorie editoriali del blog)
const INTEREST_TO_TOPIC = {
  yoga: 'yoga', meditation: 'meditazione', breathwork: 'breathwork',
  sound: 'suono', detox: 'detox', nature: 'cammini', women: 'femminile',
};

// NW2 — interessi ESPERIENZIALI (vocabolario del backend, non i topics
// editoriali): servono alle proposte di ritiri/esperienze
const EXP_INTERESTS = ['yoga', 'meditazione', 'breathwork', 'reiki',
  'costellazioni', 'cerchi', 'suono', 'misto'];
const EXP_INTEREST_LABELS = {
  yoga: 'Yoga', meditazione: 'Meditazione', breathwork: 'Breathwork',
  reiki: 'Reiki', costellazioni: 'Costellazioni familiari',
  cerchi: 'Cerchi', suono: 'Bagni di suono', misto: "Un po' di tutto",
};

// BN1 — compact: la variante da fine articolo (blog). Solo email +
// consenso: nel flusso di lettura ogni campo in piu' e' attrito. La
// profilazione arriva dopo, dalle preferenze (BN2), non dal form.
// BN2 — subscribe: la strada della LETTERA (double opt-in): il submit
// va su /public/newsletter/subscribe e il grazie dice la verita'
// ("controlla la posta"), non "sei iscritto".
// LT1 — showName: il NOME acceso o spento a parte. La Lettera di Aurya
// chiede esattamente Nome, Email, consenso e bottone (founder): con il
// solo `compact` spariva anche il nome, che li' serve (e' il saluto
// delle email). Prop additiva e retrocompatibile: se non la passi, il
// nome c'e' quando il form non e' compatto — cioe' il comportamento di
// prima per tutti gli altri chiamanti. Non tocca ne' i campi
// obbligatori, ne' il consenso, ne' la chiamata.
// NW2 — experiencesOptIn: sulle superfici della Lettera accende il
// flag «avvisami su esperienze e ritiri» che ESPANDE il form (città,
// raggio, interessi). Il percorso base resta nome+email: zero attrito.
export default function LeadForm({ type = 'traveler', accent = '#376254', context = null,
                                   successExtra = null, compact = false,
                                   ctaLabel = null, thanksBody = null,
                                   consentText = null, subscribe = false,
                                   returnTo = null, showName = null,
                                   experiencesOptIn = false }) {
  const { t, i18n } = useTranslation('prelaunch');
  const isOperator = type === 'operator';

  /* NL-bis (20/8) — chi e' loggato non deve ridigitare la sua email, e
     soprattutto non deve iscriversi con un indirizzo diverso SENZA
     saperlo: la Lettera vive sull'indirizzo, non sull'account, quindi
     una svista si traduce in «il gestionale dice che non sei iscritto»
     mentre la ricevi altrove. Precompiliamo, e se la cambia glielo
     diciamo. Mai un blocco: l'indirizzo resta una sua scelta. */
  const { user } = useAuth();
  const [accountEmail, setAccountEmail] = useState(user?.email || null);
  useEffect(() => {
    if (isOperator || accountEmail) return;
    let token = null;
    try { token = localStorage.getItem('platform_token'); } catch { /* private mode */ }
    if (!token) return;
    let alive = true;
    platformApi.get('/platform/me')
      .then((r) => { if (alive && r.data?.email) setAccountEmail(r.data.email); })
      .catch(() => { /* pagina pubblica: si prosegue senza */ });
    return () => { alive = false; };
  }, [isOperator, accountEmail]);

  const [email, setEmail] = useState('');
  const [name, setName] = useState('');
  const [phone, setPhone] = useState('');
  useEffect(() => {
    if (!isOperator && accountEmail) setEmail((cur) => cur || accountEmail);
  }, [isOperator, accountEmail]);
  const [city, setCity] = useState('');
  const [interests, setInterests] = useState([]);
  const [travel, setTravel] = useState('');
  const [budget, setBudget] = useState('');
  const [activity, setActivity] = useState('');
  const [link, setLink] = useState('');
  const [message, setMessage] = useState('');
  const [consent, setConsent] = useState(false);
  const [state, setState] = useState('idle');   // idle | sending | done | error
  // NW2 — il blocco esperienze del form progressivo
  const [wantsExperiences, setWantsExperiences] = useState(false);
  const [expInterests, setExpInterests] = useState([]);
  const [expCity, setExpCity] = useState('');
  const [expTravel, setExpTravel] = useState('');

  const toggle = (setter) => (key) => setter((prev) =>
    prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key]);
  const toggleInterest = toggle(setInterests);
  const toggleExpInterest = toggle(setExpInterests);

  const withName = showName === null ? !compact : Boolean(showName);

  /* OL3b — nella candidatura il nome e' OBBLIGATORIO: si risponde a una
     persona, non a un indirizzo. Resta facoltativo dove il nome e' un
     saluto e non un'identita' (la Lettera, il blog). */
  const nameRequired = isOperator && withName;
  const missingName = nameRequired && !name.trim();

  const submit = async (e) => {
    e.preventDefault();
    if (!email || !consent || missingName || state === 'sending') return;
    setState('sending');
    try {
      if (subscribe) {
        // BN2 — iscrizione alla lettera: double opt-in lato backend
        // NW2 — il blocco esperienze viaggia solo se l'utente ha
        // acceso il flag: niente dati raccolti «di passaggio»
        await api.post('/public/newsletter/subscribe', {
          email: email.trim(), name: name.trim() || null,
          language: (i18n.language || 'it').slice(0, 2),
          source: context || 'landing',
          return_to: returnTo,
          topics: interests.length
            ? interests.map((i) => INTEREST_TO_TOPIC[i]).filter(Boolean)
            : null,
          wants_experiences: experiencesOptIn ? wantsExperiences : null,
          interests: wantsExperiences && expInterests.length ? expInterests : null,
          city: (wantsExperiences ? expCity.trim() : city.trim()) || null,
          travel: (wantsExperiences ? expTravel : travel) || null,
          budget: budget || null,
          consent: true,
        });
        trackEvent('generate_lead', { lead_type: 'subscriber', lead_context: context || 'landing' });
        setState('done');
        return;
      }
    } catch {
      // NW2 — sull'iscrizione alla Lettera l'errore si DICE (il backend
      // ora risponde 503 se non salva): un grazie finto perderebbe
      // l'iscritto in silenzio.
      setState('error');
      return;
    }
    try {
      await api.post('/public/leads', {
        email: email.trim(), name: name.trim() || null, type,
        phone: isOperator ? (phone.trim() || null) : null,
        city: city.trim() || null,
        interests: !isOperator && interests.length ? interests : null,
        travel: !isOperator ? (travel || null) : null,
        budget: !isOperator ? (budget || null) : null,
        activity: isOperator ? (activity || null) : null,
        link: isOperator ? (link.trim() || null) : null,
        message: isOperator ? (message.trim() || null) : null,
        consent: true, language: (i18n.language || 'it').slice(0, 2),
      });
    } catch { /* best-effort: mostriamo comunque il grazie */ }
    // GA1/SEO6 — il lead e' LA conversione del pre-lancio: senza questo
    // evento non sapremmo mai quale pagina/canale porta contatti.
    // RT4 — lead_context distingue le superfici (newsletter, landing,
    // candidatura) nelle conversioni GA4, con lo stesso evento
    trackEvent('generate_lead', { lead_type: type, lead_context: context || 'landing' });
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
          {thanksBody
            || (isOperator
              ? t('form.thanksOp', { defaultValue: 'Grazie per esserti presentato: ti scriviamo personalmente prima del lancio.' })
              : t('form.thanksTr', { defaultValue: 'Al lancio riceverai una selezione di ritiri pensata per te. A presto.' }))}
        </p>
        {/* NL2 (20/8) — il ponte verso l'account, nel momento in cui
            l'utente ha appena dato fiducia. Non un muro: un invito, con
            l'email gia' compilata e senza password da inventare.
            Solo lato utente: l'operatore ha il suo funnel.

            NL-ter (20/8, founder) — a chi e' GIA' dentro non si offre
            di crearsi un account: sarebbe un invito a fare una cosa
            gia' fatta. Se ha appena iscritto la SUA email, lo si porta
            dove la vedra' comparire; se ne ha usata un'altra, non gli
            si promette nulla (li' l'iscrizione non risultera'). */}
        {!isOperator && email && !accountEmail && (
          <p className="mt-4 text-xs text-muted-foreground" data-testid="lead-account-bridge">
            {t('form.bridgeBody', { defaultValue: 'Vuoi ritrovare guide ed esperienze su ogni dispositivo?' })}{' '}
            <a href={`/accedi?vista=crea&email=${encodeURIComponent(email)}`}
              className="underline hover:no-underline" style={{ color: accent }}>
              {t('form.bridgeCta', { defaultValue: 'Crea il tuo account Aurya' })}
            </a>{' '}
            {t('form.bridgeHint', { defaultValue: '(non serve una password)' })}
          </p>
        )}
        {!isOperator && accountEmail
          && email.trim().toLowerCase() === accountEmail.toLowerCase() && (
          <p className="mt-4 text-xs text-muted-foreground" data-testid="lead-account-here">
            {t('form.bridgeLogged', { defaultValue: 'È l’indirizzo del tuo account: appena confermi, guide e materiali compaiono qui.' })}{' '}
            <a href="/account" className="underline hover:no-underline" style={{ color: accent }}>
              {t('form.bridgeLoggedCta', { defaultValue: 'Vai al tuo account' })}
            </a>
          </p>
        )}
        {/* RT4 — spazio per la consegna del lead magnet (o altro) */}
        {successExtra ? <div className="mt-4">{successExtra}</div> : null}
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
      {withName && (
        <input
          type="text" value={name} onChange={(e) => setName(e.target.value)}
          required={nameRequired}
          aria-label={isOperator
            ? t('form.fullName', { defaultValue: 'Nome e cognome' })
            : t('form.name', { defaultValue: 'Il tuo nome' })}
          placeholder={isOperator
            ? t('form.fullName', { defaultValue: 'Nome e cognome' })
            : t('form.name', { defaultValue: 'Il tuo nome' })}
          className={inputCls} style={ringStyle}
        />
      )}
      <input
        type="email" required value={email} onChange={(e) => setEmail(e.target.value)}
        aria-label={t('form.email', { defaultValue: 'La tua email' })}
        placeholder={t('form.email', { defaultValue: 'La tua email' })}
        className={inputCls} style={ringStyle}
      />
      {!isOperator && accountEmail && email.trim()
        && email.trim().toLowerCase() !== accountEmail.toLowerCase() && (
        <p className="text-xs text-amber-700 text-left" data-testid="lead-other-email">
          {t('form.otherEmail', {
            email: accountEmail,
            defaultValue: 'Stai iscrivendo un indirizzo diverso da quello del tuo account ({{email}}): la lettera arriverà lì, e nel tuo account non risulterà.',
          })}
        </p>
      )}

      {compact ? null : isOperator ? (
        <>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <input
              type="tel" value={phone} onChange={(e) => setPhone(e.target.value)}
              aria-label={t('form.phone', { defaultValue: 'Telefono' })}
              placeholder={t('form.phone', { defaultValue: 'Telefono' })}
              className={inputCls} style={ringStyle}
            />
            {/* OL3b — il posto dove sei gia' raccontato: quasi tutti ne
                hanno uno, ed e' la prima cosa che guardiamo prima di
                rispondere. Type text e non url: chi scrive
                "@ilmionome" o "ilmiosito.it" non deve essere respinto
                da una validazione che pretende lo schema. */}
            <input
              type="text" value={link} onChange={(e) => setLink(e.target.value)}
              maxLength={200}
              aria-label={t('form.opLink', { defaultValue: 'Sito o Instagram' })}
              placeholder={t('form.opLink', { defaultValue: 'Sito o Instagram' })}
              className={inputCls} style={ringStyle}
            />
          </div>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <input
              type="text" value={city} onChange={(e) => setCity(e.target.value)}
              aria-label={t('form.opCity', { defaultValue: 'Dove lavori?' })}
              placeholder={t('form.opCity', { defaultValue: 'Dove lavori?' })}
              className={inputCls} style={ringStyle}
            />
            <select
              value={activity} onChange={(e) => setActivity(e.target.value)}
              aria-label={t('form.activityLabel', { defaultValue: 'Di cosa ti occupi?' })}
              className={selectCls(activity)} style={ringStyle}
            >
              <option value="">{t('form.activityLabel', { defaultValue: 'Di cosa ti occupi?' })}</option>
              {ACTIVITIES.map((k) => (
                <option key={k} value={k}>
                  {t(`form.activity.${k}`, { defaultValue: k })}
                </option>
              ))}
            </select>
          </div>

          {/* OL3b — LA DOMANDA CHE VALE ORO (founder). Non e' una riga
              come le altre e non deve sembrarlo: esce dalla griglia,
              ha un'etichetta VISIBILE (non un placeholder che sparisce
              appena si scrive), sta staccata da un filo sottile e il
              campo e' alto abbastanza da invitare un pensiero e non tre
              parole. E' l'ultima: si risponde dopo essersi presentati. */}
          <div className="border-t pt-4" style={{ borderColor: `${accent}22` }}>
            <label htmlFor="lead-gold"
                   className="block font-display text-[1.05rem] leading-snug text-foreground">
              {t('form.opGold', { defaultValue: 'Qual è la cosa che vorresti far capire alle persone del tuo lavoro?' })}
            </label>
            <textarea
              id="lead-gold"
              value={message} onChange={(e) => setMessage(e.target.value)}
              rows={6} maxLength={1000}
              placeholder={t('form.opGoldPh', { defaultValue: 'Scrivilo con parole tue. Non serve che sia perfetto.' })}
              className={`${inputCls} mt-2.5 resize-y`} style={ringStyle}
            />
          </div>
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

      {/* NW2 — il form progressivo della Lettera: il percorso base resta
          nome+email; questo flag apre il blocco esperienze SOLO se
          l'utente lo chiede. Dati raccolti = dati scelti. */}
      {subscribe && experiencesOptIn && (
        <div className="rounded-xl border p-3"
             style={{ borderColor: `${accent}33`,
                      background: wantsExperiences ? `${accent}0a` : 'transparent' }}>
          <label className="flex items-start gap-2 text-sm text-foreground">
            <input type="checkbox" checked={wantsExperiences}
                   onChange={(e) => setWantsExperiences(e.target.checked)}
                   className="mt-0.5 h-4 w-4 shrink-0" />
            <span>
              {t('form.expFlag', { defaultValue: 'Avvisami anche quando Aurya propone esperienze e ritiri' })}
              <span className="block text-xs text-muted-foreground">
                {t('form.expFlagHint', { defaultValue: 'Facoltativo: ci aiuti a proporti solo cose adatte a te.' })}
              </span>
            </span>
          </label>
          {wantsExperiences && (
            <div className="mt-3 space-y-3 duration-300 animate-in fade-in slide-in-from-top-2">
              <input
                type="text" value={expCity}
                onChange={(e) => setExpCity(e.target.value)} maxLength={120}
                aria-label={t('form.expCity', { defaultValue: 'Dove vivi? Città o zona' })}
                placeholder={t('form.expCity', { defaultValue: 'Dove vivi? Città o zona' })}
                className={inputCls} style={ringStyle}
              />
              <div>
                <p className="mb-1.5 text-xs font-medium text-muted-foreground">
                  {t('form.expTravelLabel', { defaultValue: 'Quanto lontano ti sposteresti?' })}
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {[['near', t('form.expTravel.near', { defaultValue: 'Vicino a dove vivo' })],
                    ['anywhere', t('form.expTravel.anywhere', { defaultValue: 'Anche lontano' })]].map(([k, label]) => (
                    <button key={k} type="button" aria-pressed={expTravel === k}
                      onClick={() => setExpTravel(expTravel === k ? '' : k)}
                      className="rounded-full border px-3 py-1.5 text-xs font-medium transition-colors"
                      style={expTravel === k
                        ? { background: accent, borderColor: accent, color: '#fff' }
                        : { borderColor: `${accent}44`, color: '#4b5563', background: '#fff' }}>
                      {label}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <p className="mb-1.5 text-xs font-medium text-muted-foreground">
                  {t('form.expInterestsLabel', { defaultValue: 'Cosa ti chiama? Scegli pure più di una via' })}
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {EXP_INTERESTS.map((k) => {
                    const on = expInterests.includes(k);
                    return (
                      <button key={k} type="button" aria-pressed={on}
                        onClick={() => toggleExpInterest(k)}
                        className="rounded-full border px-3 py-1.5 text-xs font-medium transition-colors"
                        style={on
                          ? { background: accent, borderColor: accent, color: '#fff' }
                          : { borderColor: `${accent}44`, color: '#4b5563', background: '#fff' }}>
                        {EXP_INTEREST_LABELS[k]}
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      <label className="flex items-start gap-2 text-xs text-muted-foreground">
        <input type="checkbox" checked={consent}
               onChange={(e) => setConsent(e.target.checked)}
               className="mt-0.5 h-4 w-4 shrink-0" required />
        <span>
          {consentText
            || t('form.consent', { defaultValue: 'Acconsento a essere contattato via email sul lancio di Aurya.' })}{' '}
          <a href="/privacy" target="_blank" rel="noreferrer" className="underline">
            {t('form.privacy', { defaultValue: 'Privacy' })}
          </a>
        </span>
      </label>
      {state === 'error' && (
        <p className="text-xs font-medium text-red-600" role="alert">
          {t('form.subscribeError', { defaultValue: 'Non siamo riusciti a salvarti, riprova tra un momento.' })}
        </p>
      )}
      <button
        type="submit" disabled={!email || !consent || missingName || state === 'sending'}
        className="inline-flex w-full items-center justify-center gap-2 rounded-xl px-5 py-3 text-sm font-semibold text-white transition-opacity disabled:opacity-50"
        style={{ background: accent }}
      >
        {state === 'sending'
          ? <Loader2 className="h-4 w-4 animate-spin" />
          : <>
              {ctaLabel
                || (isOperator
                  ? t('form.ctaOp', { defaultValue: 'Voglio esserci al lancio' })
                  : t('form.ctaTr', { defaultValue: 'Trovami il mio ritiro' }))}
              <ArrowRight className="h-4 w-4" />
            </>}
      </button>
    </form>
  );
}
