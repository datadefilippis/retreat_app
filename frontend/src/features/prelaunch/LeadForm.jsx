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
import { creaAccount } from '../../utils/authLinks';
import { sblocca } from '../../lib/cerchio';

// FV5 (10/9/2026 sera) — le vie, il raggio, il budget e la mappa verso
// il vocabolario del backend vivono in PreferenzeRitiri: UN blocco per
// tutti i form (BASE_TO_EXP e' quella).
import PreferenzeRitiri, { BASE_TO_EXP, versoBackend } from './PreferenzeRitiri';
const ACTIVITIES = ['teacher', 'center', 'venue', 'organizer', 'therapist', 'other'];

// BN2 — mappa chip interessi (chiavi lead storiche) → topics della
// lettera (categorie editoriali del blog)
const INTEREST_TO_TOPIC = {
  yoga: 'yoga', meditation: 'meditazione', breathwork: 'breathwork',
  sound: 'suono', detox: 'detox', nature: 'cammini', women: 'femminile',
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
                                   onSbloccato = null,
                                   experiencesOptIn = false,
                                   // CN1 (founder 3/9/2026): sulla landing del Cerchio la
                                   // preferenza «ritiri ed esperienze» parte ACCESA — e'
                                   // una preferenza dentro lo stesso consenso, non un
                                   // secondo consenso (che resta esplicito e spento)
                                   experiencesDefault = false,
                                   // CN1 — nel primo schermo della landing il blocco
                                   // esperienze mostra SOLO la citta' (la cosa che rende
                                   // «nella tua zona» vero): raggio e interessi si
                                   // scelgono dopo, dalle preferenze
                                   experiencesLight = false,
                                   // RB4 (10/9/2026) — la porta «Trovami il mio ritiro»: il
                                   // modulo pieno di luglio (citta', interessi, raggio, budget)
                                   // iscrive al Cerchio con la preferenza ritiri SEMPRE accesa,
                                   // senza il flag: chi chiede un ritiro vuole essere avvisato
                                   wantsExperiencesAlways = false,
                                   // RB12 — il tema dell'articolo preseleziona il chip
                                   initialInterests = [] }) {
  const { t, i18n } = useTranslation('prelaunch');
  // RB13 (10/9/2026, onda 3) — la PORTA da cui si e' arrivati (home,
  // magazine, esperienze) viaggia nell'URL e finisce nella fonte
  // dell'iscritto («cerca-ritiro:magazine»): il cruscotto del lunedi'
  // e la lista iscritti dicono quale porta lavora.
  const porta = (typeof window !== 'undefined'
    ? (new URLSearchParams(window.location.search).get('porta') || '') : '')
    .replace(/[^a-z0-9_-]/gi, '').slice(0, 20);
  const fonte = [context || 'landing', porta].filter(Boolean).join(':').slice(0, 60);
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
  const [interests, setInterests] = useState(() => initialInterests || []);
  const [travel, setTravel] = useState('');
  const [budget, setBudget] = useState('');
  const [activity, setActivity] = useState('');
  const [link, setLink] = useState('');
  const [message, setMessage] = useState('');
  const [consent, setConsent] = useState(false);
  const [state, setState] = useState('idle');   // idle | sending | done | error
  // NW2 — il blocco esperienze del form progressivo
  const [wantsExperiences, setWantsExperiences] = useState(
    Boolean(experiencesOptIn && experiencesDefault));
  // FV5 — il blocco «avvisami» usa gli STESSI campi del modulo pieno
  // (interests, city, travel): un vocabolario, una struttura, ovunque
  const toggle = (setter) => (key) => setter((prev) =>
    prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key]);
  const toggleInterest = toggle(setInterests);

  const withName = showName === null ? !compact : Boolean(showName);

  /* OL3b — nella candidatura il nome e' OBBLIGATORIO: si risponde a una
     persona, non a un indirizzo. Resta facoltativo dove il nome e' un
     saluto e non un'identita' (la Lettera, il blog). */
  const [giaDentro, setGiaDentro] = useState(false);  // SB2: gia' confermato
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
          source: fonte,
          return_to: returnTo,
          topics: interests.length
            ? interests.map((i) => INTEREST_TO_TOPIC[i]).filter(Boolean)
            : null,
          wants_experiences: experiencesOptIn ? wantsExperiences : (wantsExperiencesAlways || null),
          // FV5 — le vie viaggiano solo se l'iscritto ha ACCESO i ritiri
          // (modulo pieno di /cerca-ritiro o flag «avvisami»): mai di passaggio
          interests: ((experiencesOptIn ? wantsExperiences : wantsExperiencesAlways) && interests.length)
            ? versoBackend(interests) : null,
          city: city.trim() || null,
          travel: travel || null,
          budget: budget || null,
          consent: true,
          // il cancello di una guida (onSbloccato presente) sblocca
          // con la chiamata successiva: niente magic link ridondante
          unlock_flow: !!onSbloccato,
        });
        trackEvent('generate_lead', { lead_type: 'subscriber', lead_context: context || 'landing', porta: porta || '(nessuna)' });
        // SB2 (20/8) — gia' confermato? La prova arriva subito e il
        // grazie dice la verita' («sei gia' dei nostri»), invece di
        // rimandare a una conferma gia' fatta.
        try {
          await sblocca(email);
          setGiaDentro(true);
          // il cancello ospite puo' aprirsi subito (es. la guida si ricarica)
          if (onSbloccato) { onSbloccato(); return; }
        } catch { /* nuovo/pending: si aspetta il click nell'email */ }
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
          {giaDentro
            ? t('form.thanksGia', { defaultValue: 'Questa email è già dei nostri: tutto sbloccato su questo dispositivo — guide, meditazioni, sessioni. Nessuna nuova conferma da fare.' })
            : (thanksBody
              || (isOperator
                ? t('form.thanksOp', { defaultValue: 'Grazie per esserti presentato: ti scriviamo personalmente prima del lancio.' })
                : t('form.thanksTr', { defaultValue: 'Al lancio riceverai una selezione di ritiri pensata per te. A presto.' })))}
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
            <a href={creaAccount(email, returnTo)} data-testid="lead-bridge-link"
              className="underline hover:no-underline" style={{ color: accent }}>
              {t('form.bridgeCta', { defaultValue: 'Crea il tuo account Aurya' })}
            </a>{' '}
            {t('form.bridgeHint2', { defaultValue: '(un minuto: o scegli una password, o entri dal link)' })}
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
          <PreferenzeRitiri accent={accent} interests={interests} onToggleInterest={toggleInterest}
                            city={city} setCity={setCity} travel={travel} setTravel={setTravel}
                            budget={budget} setBudget={setBudget} showBudget
                            inputCls={inputCls} selectCls={selectCls} ringStyle={ringStyle} />
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
            <div className="mt-3 duration-300 animate-in fade-in slide-in-from-top-2">
              <PreferenzeRitiri accent={accent} interests={interests} onToggleInterest={toggleInterest}
                                city={city} setCity={setCity} travel={travel} setTravel={setTravel}
                                light={experiencesLight}
                                inputCls={inputCls} selectCls={selectCls} ringStyle={ringStyle} />
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
