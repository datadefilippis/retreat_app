/**
 * InlineServiceCheckout — acquisto di un servizio TUTTO dentro il
 * profilo pubblico /o/:org_slug (PN3, PROFILO_NEGOZIO_PIANO_2026-07).
 *
 * Harness che compone i pezzi GIA' esistenti del checkout storefront
 * senza forkare nulla:
 *   - catalogo pubblico via storefrontAPI.getCatalog (serve al hook per
 *     prezzi/validazioni, identico allo storefront)
 *   - carrello via useStorefrontCart (stessa persistenza sessionStorage
 *     dello store: la selezione sopravvive a un giro sulla landing /p/)
 *   - scelta opzione (radio) / slot reale (AvailabilityCalendarSlotPicker
 *     + getServiceSlots) / richiesta libera (ServiceCustomRequestForm),
 *     stessi 4 scenari di ProductLandingPage (needsScheduling)
 *   - form + riepilogo via useCheckoutForm + CheckoutForm + OrderSummary:
 *     payload, consensi GDPR/RS3, coupon e redirect Stripe sono ESATTAMENTE
 *     quelli dello storefront (un solo checkout nel codice, I2/I3).
 *
 * Scelte deliberate:
 *   - selectedItems contiene SOLO il servizio della riga espansa: il
 *     profilo non e' una superficie carrello — eventuali altri articoli
 *     nel carrello store restano intatti in sessionStorage e NON vengono
 *     ne' mostrati ne' acquistati da qui.
 *   - clearCartSnapshot passato al hook rimuove solo questo prodotto
 *     (non svuota il carrello dell'intero store).
 *   - transaction_mode=request → il submit standard crea la richiesta e
 *     il successo si mostra inline; direct → useCheckoutSubmit fa il
 *     redirect Stripe come dallo storefront (ritorno su /s/checkout-success).
 */

import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { storefrontAPI } from '../../../../api/storefront';
import { useCustomerAuth } from '../../../../context/CustomerAuthContext';
import useStorefrontCart from '../../hooks/useStorefrontCart';
import { hydrateCart, persistCart, clearCart } from '../../hooks/useCartStorage';
import useCheckoutForm from '../../hooks/useCheckoutForm';
import OrderSummary from './OrderSummary';
import CheckoutForm from './CheckoutForm';
import AvailabilityCalendarSlotPicker from '../AvailabilityCalendarSlotPicker';
import ServiceCustomRequestForm from '../ServiceCustomRequestForm';
import { fmtPrice } from '../StorefrontCards';


export default function InlineServiceCheckout({ orgSlug, row, onClose }) {
  // Il hook checkout parla il namespace `storefront` (stesse chiavi dello
  // store); la UI di selezione riusa le chiavi `landings` della landing /p/.
  const { t, i18n } = useTranslation(['storefront', 'landings']);
  const { customer, isCustomerAuthenticated, signup: customerSignup } = useCustomerAuth();

  const productId = row.product_id;
  const hasOptions = Array.isArray(row.service_options) && row.service_options.length > 0;
  const hasSlots = !!row.has_availability_slots;
  const allowCustom = !!row.allow_custom_request;

  // PS6.4 — decontaminazione: il profilo /o/ e' superficie DELL'OPERATORE.
  // Un giro precedente sul marketplace (overlay ritiro, L2) lascia in
  // sessione mktp_ctx/mktp_return: qui vanno puliti (specchio della
  // pulizia legacy di StorefrontPage all'apertura di un checkout store),
  // altrimenti l'ordine nasce marcato marketplace (niente incasso
  // manuale per l'operatore, analytics falsate) e la success page
  // mostra CTA marketplace stantie.
  useEffect(() => {
    try {
      sessionStorage.removeItem('storefront:mktp_ctx');
      sessionStorage.removeItem('storefront:mktp_return');
    } catch { /* no-op */ }
  }, []);

  // ── Catalogo pubblico (stessa fonte dello storefront) ────────────────
  const [catalog, setCatalog] = useState(null);
  const [loadState, setLoadState] = useState('loading'); // loading | ready | error
  useEffect(() => {
    let mounted = true;
    setLoadState('loading');
    storefrontAPI.getCatalog(orgSlug, (i18n.language || 'it').slice(0, 2))
      .then(res => { if (mounted) { setCatalog(res.data); setLoadState('ready'); } })
      .catch(() => { if (mounted) setLoadState('error'); });
    return () => { mounted = false; };
  }, [orgSlug, i18n.language]);

  // ── Carrello condiviso con lo store (persistenza per-slug) ───────────
  const {
    quantities, setQuantities,
    attendeeDetails, setAttendeeDetails,
    orderFieldsData, setOrderFieldsData,
    selectedServiceOptions, setSelectedServiceOptions,
    selectedServiceSlots, setSelectedServiceSlots,
  } = useStorefrontCart({ slug: orgSlug, t, productsLookup: catalog?.products });

  // Preselezione: la riga espansa entra in "carrello" con quantita' 1.
  useEffect(() => {
    if (!productId || loadState !== 'ready') return;
    setQuantities(q => (q[productId] > 0 ? q : { ...q, [productId]: 1 }));
  }, [productId, loadState, setQuantities]);

  // ── Slot reali (stesso endpoint pubblico della landing /p/) ──────────
  const [slots, setSlots] = useState(null); // null = loading
  useEffect(() => {
    if (!hasSlots || !productId) { setSlots([]); return; }
    let mounted = true;
    storefrontAPI.getServiceSlots(productId, 30)
      .then(res => { if (mounted) setSlots(res.data?.slots || []); })
      .catch(() => { if (mounted) setSlots([]); });
    return () => { mounted = false; };
  }, [productId, hasSlots]);

  // ── Selezione (opzione / slot / richiesta libera) ────────────────────
  const selectedOptionId = selectedServiceOptions[productId] || null;
  const storedSlot = selectedServiceSlots[productId] || null;
  const realSlot = storedSlot && !storedSlot.custom_request ? storedSlot : null;

  const [customRequest, setCustomRequest] = useState(null);
  const [customRequestOpen, setCustomRequestOpen] = useState(!hasSlots && allowCustom);

  const pickOption = (optionId) => {
    setSelectedServiceOptions(prev => ({ ...prev, [productId]: optionId }));
  };

  const pickSlot = (s) => {
    setSelectedServiceSlots(prev => ({ ...prev, [productId]: s }));
    setCustomRequestOpen(false);
    setCustomRequest(null);
  };

  const dropSlot = useCallback(() => {
    setSelectedServiceSlots(prev => {
      if (!prev || prev[productId] === undefined) return prev;
      const next = { ...prev };
      delete next[productId];
      return next;
    });
  }, [productId, setSelectedServiceSlots]);

  const handleCustomChange = (v) => {
    setCustomRequest(v);
    if (v?.date && v?.start_time && v?.end_time) {
      // Stessa forma del preloadCart.service_slot della landing /p/:
      // la proposta libera viaggia come slot con flag custom_request.
      setSelectedServiceSlots(prev => ({
        ...prev,
        [productId]: {
          date: v.date,
          start_time: v.start_time,
          end_time: v.end_time,
          custom_request: true,
          notes: v.notes || null,
        },
      }));
    } else if (storedSlot?.custom_request) {
      dropSlot();
    }
  };

  const openCustomPanel = () => {
    setCustomRequestOpen(true);
    if (realSlot) dropSlot();
  };
  const closeCustomPanel = () => {
    setCustomRequestOpen(false);
    setCustomRequest(null);
    if (storedSlot?.custom_request) dropSlot();
  };

  // ── PV6 — percorso a passi (SOLO presentazione; payload/logica intatti) ──
  //
  // Tre passi progressivi nella stessa card: 1 giorno (+ opzione), 2 orario,
  // 3 dati. Il giorno scelto ha UNA sola fonte di verita': `pickedDay` qui
  // nel parent — il calendario e la griglia orari lo ricevono controllati
  // (AvailabilityCalendarSlotPicker activeDate/onActiveDateChange), quindi
  // non esistono copie locali che possano divergere.
  //
  // "Recursivo": i passi completati restano visibili collassati con la
  // scelta fatta e un bottone Modifica (`editStep`); tornare indietro non
  // butta via nulla — cambia il giorno? Lo slot decade da solo (dropSlot),
  // tutto il resto (opzione, dati form) resta.
  const [pickedDay, setPickedDay] = useState(null);
  const [editStep, setEditStep] = useState(null);
  const stepInteractedRef = useRef(false);
  const stepRefs = { 1: useRef(null), 2: useRef(null), 3: useRef(null) };

  // Deep-link PV5 / idratazione di sessione: se uno slot reale e' gia'
  // in carrello (selezione fatta sulla landing /p/), il passo 1 e 2 sono
  // gia' compiuti e si atterra direttamente al passo 3 col riepilogo.
  useEffect(() => {
    if (realSlot?.date) setPickedDay(realSlot.date);
  }, [realSlot?.date]);

  const selectedOption = hasOptions
    ? (row.service_options || []).find(o => o.id === selectedOptionId) || null
    : null;
  const optionChosen = !hasOptions || !!selectedOptionId;
  const customChosen = !!storedSlot?.custom_request;
  const inCustomFlow = hasSlots && customRequestOpen;

  // Il passo "naturale" derivato dalla selezione; `editStep` puo' solo
  // riportare indietro (mai saltare avanti oltre quanto gia' scelto).
  const autoStep = inCustomFlow
    ? (customChosen && optionChosen ? 3 : 1)
    : (!optionChosen || !pickedDay) ? 1
      : (!realSlot?.date ? 2 : 3);
  const currentStep = Math.min(editStep ?? autoStep, autoStep);

  const handlePickDay = (iso) => {
    if (!iso) return;
    stepInteractedRef.current = true;
    setPickedDay(iso);
    // Giorno diverso → l'orario scelto non vale piu'; stesso giorno →
    // lo slot resta e si torna dolcemente al riepilogo.
    if (realSlot && realSlot.date !== iso) dropSlot();
    setEditStep(null);
  };

  const handlePickSlot = (s) => {
    stepInteractedRef.current = true;
    pickSlot(s);
    setEditStep(null);
  };

  const goEditStep = (n) => {
    stepInteractedRef.current = true;
    setEditStep(n);
  };

  // Auto-avanzamento dolce: al cambio passo si scorre sul passo attivo.
  // Solo dopo un'interazione dell'utente — all'atterraggio (deep-link
  // PV5) lo scroll lo governa gia' OperatorProfilePage sull'ancora riga.
  useEffect(() => {
    if (!stepInteractedRef.current) return;
    const el = stepRefs[currentStep]?.current;
    if (!el) return undefined;
    const id = setTimeout(
      () => el.scrollIntoView({ behavior: 'smooth', block: 'start' }), 80);
    return () => clearTimeout(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentStep]);

  const fmtDay = (iso) => {
    if (!iso) return '';
    try {
      return new Date(iso + 'T12:00').toLocaleDateString(
        i18n.language, { weekday: 'long', day: 'numeric', month: 'long' });
    } catch { return iso; }
  };

  // ── selectedItems: SOLO questo servizio (stessa forma dello store) ───
  const selectedItems = useMemo(() => {
    const qty = quantities[productId];
    if (!productId || !(qty > 0)) return [];
    const item = { product_id: productId, quantity: qty };
    const sOpt = selectedServiceOptions[productId];
    if (sOpt) item.service_option_id = sOpt;
    const sSlot = selectedServiceSlots[productId];
    if (sSlot?.date && sSlot?.start_time && sSlot?.end_time) {
      item.booking_date = sSlot.date;
      item.booking_start_time = sSlot.start_time;
      item.booking_end_time = sSlot.end_time;
      if (sSlot.custom_request) item.service_custom_request = true;
      if (sSlot.notes) item.rental_notes = sSlot.notes;
    }
    return [item];
  }, [productId, quantities, selectedServiceOptions, selectedServiceSlots]);

  // I servizi non hanno tier evento: superficie vuota ma stabile.
  const getOrderedTierEntries = useCallback(() => [], []);

  // Il success del hook chiama clearCartSnapshot: qui rimuove SOLO il
  // servizio acquistato — eventuali altri articoli del carrello store
  // restano al loro posto (il persist di useStorefrontCart aggiorna
  // sessionStorage da solo).
  const clearSelection = useCallback(() => {
    const drop = (setter) => setter(prev => {
      if (!prev || prev[productId] === undefined) return prev;
      const next = { ...prev };
      delete next[productId];
      return next;
    });
    drop(setQuantities);
    drop(setSelectedServiceOptions);
    drop(setSelectedServiceSlots);
  }, [productId, setQuantities, setSelectedServiceOptions, setSelectedServiceSlots]);

  const loadAvailabilityNoop = useCallback(() => {}, []);

  // ── Il checkout VERO: stesso hook, stesso form dello storefront ──────
  const checkout = useCheckoutForm({
    slug: orgSlug,
    catalog,
    selectedItems,
    getOrderedTierEntries,
    customer,
    isCustomerAuthenticated,
    customerSignup,
    attendeeDetails,
    setAttendeeDetails,
    orderFieldsData,
    selectedServiceOptions,
    selectedServiceSlots,
    clearCartSnapshot: clearSelection,
    loadAvailability: loadAvailabilityNoop,
    t,
    // PS6.4 — l'acquisto dal profilo pubblico e' SEMPRE canale store:
    // la superficie reale decide, non il flag di sessione.
    channel: 'store',
  });
  const { submitted, shippingSummary, couponValidationState } = checkout;

  // Chiusura senza acquisto: l'espansione della riga NON deve lasciare
  // un "carrello fantasma" sullo store (la preselezione qty=1 viene
  // persistita in sessionStorage da useStorefrontCart). Al momento
  // dell'unmount i setter React non ripersistono piu', quindi la
  // pulizia tocca direttamente lo snapshot via useCartStorage e
  // notifica i badge (stesso evento del hook). Dopo un submit andato
  // a buon fine non serve: clearSelection ha gia' rimosso il prodotto.
  const submittedRef = useRef(false);
  useEffect(() => { submittedRef.current = !!submitted; }, [submitted]);
  useEffect(() => {
    return () => {
      if (submittedRef.current) return;
      try {
        const snap = hydrateCart(orgSlug);
        if (!snap) return;
        let touched = false;
        for (const k of ['quantities', 'selectedServiceOptions', 'selectedServiceSlots']) {
          if (snap[k] && snap[k][productId] !== undefined) {
            delete snap[k][productId];
            touched = true;
          }
        }
        if (!touched) return;
        const hasAny = Object.values(snap).some(
          v => v && typeof v === 'object' && Object.keys(v).length > 0
        );
        if (hasAny) persistCart(orgSlug, snap); else clearCart(orgSlug);
        window.dispatchEvent(new CustomEvent('storefront:cart:change', { detail: { slug: orgSlug } }));
      } catch { /* no-op */ }
    };
  }, [orgSlug, productId]);

  // ── Stati di caricamento / errore ────────────────────────────────────
  if (loadState === 'loading') {
    return (
      <p className="text-sm text-gray-500 py-3">
        {t('landings:product.loading', { defaultValue: 'Caricamento…' })}
      </p>
    );
  }
  if (loadState === 'error' || !catalog) {
    return (
      <p className="text-sm text-red-700 py-3">
        {t('landings:product.errorBody', { defaultValue: 'Qualcosa non ha funzionato, riprova più tardi.' })}
      </p>
    );
  }

  // ── Conferma inline (successo non-Stripe: request/approval) ──────────
  if (submitted) {
    const heading = submitted.payment_checkout_url
      ? t('storefront:submitted.orderReceived')
      : t('storefront:submitted.requestRegistered');
    const bodyKeyByMode = {
      direct: 'storefront:submitted.body.direct',
      approval: 'storefront:submitted.body.approval',
      request: 'storefront:submitted.body.request',
    };
    const bodyKey = bodyKeyByMode[submitted.transaction_mode];
    const body = bodyKey ? t(bodyKey) : (submitted.message || t('storefront:submitted.body.request'));
    const orderRef = submitted.order_id ? `#${submitted.order_id.slice(0, 8)}` : '';
    return (
      <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-center space-y-2"
           data-testid="inline-checkout-success">
        <div className="w-10 h-10 mx-auto rounded-full bg-emerald-100 flex items-center justify-center">
          <svg className="w-5 h-5 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden>
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        </div>
        <p className="font-semibold text-gray-900">{heading}</p>
        <p className="text-sm text-gray-700">{body}</p>
        {orderRef && (
          <p className="text-xs text-gray-500">{t('storefront:submitted.reference', { ref: orderRef })}</p>
        )}
        <p className="text-xs text-gray-500">{t('storefront:submitted.confirmEmailSoon')}</p>
        {onClose && (
          <button type="button" onClick={onClose}
                  className="mt-1 rounded-full border border-gray-300 bg-white px-5 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50">
            {t('landings:operator.inlineClose', { defaultValue: 'Chiudi' })}
          </button>
        )}
      </div>
    );
  }

  const product = (catalog.products || []).find(p => p.id === productId);
  if (!product) {
    // Il servizio non e' nel catalogo pubblico (spublicato nel frattempo):
    // la landing /p/ resta la via di uscita.
    return (
      <p className="text-sm text-gray-500 py-3">
        {t('landings:product.notFoundBody', { defaultValue: 'Questo servizio non è al momento disponibile.' })}
      </p>
    );
  }

  // ── Pezzi condivisi tra percorso a passi (hasSlots) e passo unico ────

  // Opzione servizio (radio), come la landing /p/. Nel percorso a passi
  // vive DENTRO il passo 1, sopra il calendario; senza calendario resta
  // il primo blocco del passo unico.
  const optionsBlock = hasOptions && (
        <div className="space-y-2">
          <p className="text-sm font-semibold text-gray-900">
            {t('landings:product.optionsHeading', { defaultValue: 'Scegli l’opzione' })}
          </p>
          {row.service_options.map(o => (
            <label key={o.id}
                   className={`flex items-center justify-between gap-3 rounded-lg border px-3 py-2.5 cursor-pointer transition ${
                     selectedOptionId === o.id
                       ? 'border-gray-900 bg-gray-50'
                       : 'border-gray-200 bg-white hover:border-gray-400'
                   }`}>
              <span className="flex items-center gap-2 min-w-0">
                <input
                  type="radio"
                  name={`inline-svc-opt-${productId}`}
                  checked={selectedOptionId === o.id}
                  onChange={() => pickOption(o.id)}
                />
                <span className="text-sm font-medium text-gray-900">{o.label}</span>
              </span>
              <span className="text-sm font-semibold text-gray-900 whitespace-nowrap">
                {fmtPrice(o.price, catalog.currency)}
              </span>
            </label>
          ))}
        </div>
  );


  // Pannello richiesta libera (slot reali attivi ma nessun orario adatto):
  // stesso contenuto di prima, riusato dentro il passo 1 del percorso.
  const customPanel = (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-900">
          {t('landings:product.customRequestPanelHeading', { defaultValue: 'Proponi data e ora' })}
        </h3>
        <button type="button" onClick={closeCustomPanel}
                className="text-xs text-gray-500 hover:text-gray-700">
          {t('landings:product.customRequestCancel', { defaultValue: 'Annulla' })}
        </button>
      </div>
      <ServiceCustomRequestForm
        durationMinutes={row.duration_minutes || product.service_duration_minutes}
        value={customRequest}
        onChange={handleCustomChange}
      />
    </div>
  );

  // Riepilogo + form: gli STESSI componenti dello storefront.
  // Niente onRemove/onQtyChange: qui si compra un solo servizio,
  // la riga non deve potersi svuotare da dentro il riepilogo.
  const summaryAndForm = (
    <>
      <OrderSummary
        items={selectedItems}
        products={catalog.products || []}
        selectedOccurrences={{}}
        selectedTiers={{}}
        rentalDates={{}}
        bookingSlots={Object.fromEntries(
          Object.entries(selectedServiceSlots).map(([pid, s]) => [
            pid, { date: s.date, start: s.start_time, end: s.end_time },
          ])
        )}
        currency={catalog.currency}
        shipping={shippingSummary}
        couponDiscount={couponValidationState?.discountAmount || 0}
        couponLabel={couponValidationState?.code || null}
      />

      <CheckoutForm
        checkout={checkout}
        slug={orgSlug}
        catalog={catalog}
        selectedItems={selectedItems}
        isCustomerAuthenticated={isCustomerAuthenticated}
        attendeeDetails={attendeeDetails}
        setAttendeeDetails={setAttendeeDetails}
        orderFieldsData={orderFieldsData}
        setOrderFieldsData={setOrderFieldsData}
        selectedServiceOptions={selectedServiceOptions}
        selectedServiceSlots={selectedServiceSlots}
        inlineServiceSelection
      />
    </>
  );

  // ── PV6 — testata di un passo: pallino numerato + etichetta + riga
  // riassuntiva della scelta fatta + "Modifica" (il percorso e' sempre
  // reversibile senza perdere il resto). Sobrio, brand Salvia.
  const stepHeader = (n, label, { done, summary, editable }) => {
    const active = currentStep === n;
    return (
      <div className="flex items-center gap-2.5 px-3 py-2.5">
        <span aria-hidden
              className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-bold ${
                active || done ? 'bg-[#376254] text-white' : 'bg-gray-200 text-gray-500'
              }`}>
          {done && !active ? (
            <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none"
                 stroke="currentColor" strokeWidth={3} aria-hidden>
              <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
            </svg>
          ) : n}
        </span>
        <div className="min-w-0 flex-1">
          <p className={`text-sm font-semibold ${active || done ? 'text-gray-900' : 'text-gray-400'}`}>
            {label}
          </p>
          {done && !active && summary && (
            <p className="text-xs text-gray-600 truncate first-letter:capitalize"
               data-testid={`booking-step-${n}-summary`}>
              {summary}
            </p>
          )}
        </div>
        {done && !active && editable && (
          <button type="button"
                  data-testid={`booking-step-edit-${n}`}
                  onClick={() => goEditStep(n)}
                  className="shrink-0 rounded-full border border-gray-300 bg-white px-3 py-1 text-xs font-medium text-gray-700 hover:bg-gray-50">
            {t('landings:product.steps.edit', { defaultValue: 'Modifica' })}
          </button>
        )}
      </div>
    );
  };

  const stepShell = (n, children) => (
    <section key={`step-${n}`} ref={stepRefs[n]}
             data-testid={`booking-step-${n}`}
             className={`scroll-mt-24 rounded-xl border bg-white ${
               currentStep === n ? 'border-[#376254]/50 shadow-sm' : 'border-gray-200'
             }`}>
      {children}
    </section>
  );

  // Bottone mostrato quando si sta MODIFICANDO un passo gia' compiuto
  // senza cambiare nulla: riporta avanti senza toccare i dati.
  const confirmEdit = (
    <div className="pt-1">
      <button type="button"
              data-testid="booking-step-confirm"
              onClick={() => { stepInteractedRef.current = true; setEditStep(null); }}
              className="w-full rounded-full bg-[#376254] px-4 py-2 text-sm font-semibold text-white hover:bg-[#2c4f43]">
        {t('landings:product.steps.confirm', { defaultValue: 'Conferma' })}
      </button>
    </div>
  );

  const step1Done = optionChosen && (inCustomFlow ? customChosen : !!pickedDay);
  const step2Done = !!realSlot?.date || customChosen;

  return (
    <div className="space-y-4" data-testid="inline-service-checkout">
      {hasSlots ? (
        /* ── PV6 — percorso guidato a 3 passi nella stessa card
           (progressive disclosure): 1 giorno (+ opzione), 2 orario,
           3 dati. I passi compiuti restano collassati con la scelta
           fatta e il bottone Modifica. */
        <div className="space-y-3" data-testid="booking-steps">
          {stepShell(1, (
            <>
              {stepHeader(1,
                t('landings:product.steps.day', { defaultValue: 'Scegli il giorno' }),
                {
                  done: step1Done,
                  editable: true,
                  summary: inCustomFlow
                    ? [fmtDay(storedSlot?.date), storedSlot?.start_time].filter(Boolean).join(' · ')
                    : [fmtDay(pickedDay), selectedOption?.label].filter(Boolean).join(' · '),
                })}
              {currentStep === 1 && (
                <div className="px-3 pb-3 space-y-3">
                  {optionsBlock}
                  {customRequestOpen ? customPanel : (
                    slots == null ? (
                      <p className="text-sm text-gray-500">{t('landings:product.loadingSlots', { defaultValue: 'Carico le disponibilità…' })}</p>
                    ) : (
                      <AvailabilityCalendarSlotPicker
                        slots={slots}
                        selected={realSlot}
                        onSelect={handlePickSlot}
                        activeDate={pickedDay}
                        onActiveDateChange={handlePickDay}
                        showSlots={false}
                      />
                    )
                  )}
                  {allowCustom && !customRequestOpen && (
                    <div className="border-t border-gray-100 pt-3">
                      <button type="button" onClick={openCustomPanel}
                              className="text-sm font-medium text-gray-700 hover:text-gray-900 underline">
                        {t('landings:product.customRequestToggle', { defaultValue: 'Nessun orario ti va bene? Proponi tu data e ora' })}
                      </button>
                    </div>
                  )}
                  {editStep === 1 && step1Done && confirmEdit}
                </div>
              )}
            </>
          ))}

          {!inCustomFlow && stepShell(2, (
            <>
              {stepHeader(2,
                t('landings:product.steps.time', { defaultValue: 'Scegli l’orario' }),
                {
                  done: step2Done,
                  editable: true,
                  summary: realSlot?.date
                    ? `${realSlot.start_time} - ${realSlot.end_time}`
                    : '',
                })}
              {currentStep === 2 && (
                <div className="px-3 pb-3 space-y-2">
                  <AvailabilityCalendarSlotPicker
                    slots={slots || []}
                    selected={realSlot}
                    onSelect={handlePickSlot}
                    activeDate={pickedDay}
                    onActiveDateChange={handlePickDay}
                    showCalendar={false}
                  />
                  {editStep === 2 && step2Done && confirmEdit}
                </div>
              )}
            </>
          ))}

          {stepShell(3, (
            <>
              {stepHeader(3,
                t('landings:product.steps.details', { defaultValue: 'I tuoi dati' }),
                { done: false, editable: false, summary: '' })}
              {currentStep === 3 && (
                <div className="px-3 pb-4 space-y-4">
                  {summaryAndForm}
                </div>
              )}
            </>
          ))}
        </div>
      ) : (
        /* ── Servizi SENZA calendario: passo unico com'era (nessuna
           regressione) — opzione, eventuale preferenza libera, dati. */
        <>
          {optionsBlock}

          {/* Scenario 3 — niente regole, richiesta libera attiva */}
          {allowCustom && (
        <div className="space-y-2">
          <p className="text-sm font-semibold text-gray-900">
            {t('landings:product.customRequest.headingNoSlots', { defaultValue: 'Proponi data e ora' })}
          </p>
          <ServiceCustomRequestForm
            durationMinutes={row.duration_minutes || product.service_duration_minutes}
            value={customRequest}
            onChange={handleCustomChange}
          />
        </div>
          )}

          {summaryAndForm}
        </>
      )}

      {/* La landing /p/ resta viva come approfondimento (SEO + link
          esterni), mai piu' come passaggio obbligato. PV5 — il link
          appare SOLO se la landing ha contenuto reale (has_landing). */}
      {row.slug && row.has_landing && (
        <p className="text-[11px] text-gray-500 text-center">
          <Link to={`/p/${orgSlug}/${row.slug}`} className="underline hover:text-gray-800">
            {t('landings:operator.inlineDetailsLink', { defaultValue: 'Vedi la pagina completa del servizio' })}
          </Link>
        </p>
      )}
    </div>
  );
}
