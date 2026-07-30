/**
 * InlineEventCheckout — acquisto di un ritiro TUTTO dentro la landing
 * /e/:org_slug/:slug (PN4, PROFILO_NEGOZIO_PIANO_2026-07).
 *
 * Harness sul modello di InlineServiceCheckout (PN3): compone i pezzi
 * GIA' esistenti del checkout senza forkare nulla:
 *   - catalogo pubblico via storefrontAPI.getCatalog (il hook risolve
 *     prezzi/validazioni dagli stessi dati dello storefront, mai dallo
 *     stato della landing: niente dati stantii)
 *   - selezione tier/quantita' arriva dalla landing come `preload`
 *     ({productId, occurrenceId, qty, tier_quantities}) — la STESSA
 *     forma che StorefrontPage idratava dal vecchio handoff
 *   - form + riepilogo via useCheckoutForm + CheckoutForm + OrderSummary:
 *     payload (fan-out per tier con ticket_tier_id + occurrence_id +
 *     attendees), consensi GDPR/RS3, coupon e redirect Stripe sono
 *     ESATTAMENTE quelli dello storefront (un solo checkout: I2/I3).
 *     L'OrderSummary con effectivePlan mostra la caparra come oggi (I3).
 *
 * Scelte deliberate:
 *   - NIENTE useStorefrontCart: la landing e' una superficie a
 *     acquisto singolo, la selezione vive nello stato della pagina.
 *     Cosi' non nasce nessun "carrello fantasma" in sessionStorage e
 *     la chiusura del pannello non lascia tracce.
 *   - contesto marketplace timbrato in sessionStorage (mktp_ctx) come
 *     faceva il vecchio handoff K1: l'ordine viaggia con
 *     channel=marketplace (GT1) e la success page /s/checkout-success
 *     mostra il Passaporto invece del ritorno alla vetrina.
 *   - transaction_mode=direct con Stripe attivo → redirect Stripe e
 *     ritorno su /s/checkout-success (gia' vivo, unica eccezione /s/
 *     ammessa); senza Stripe il backend risponde con payment_reason e
 *     la conferma si mostra QUI, inline, con il messaggio standard.
 */

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { storefrontAPI } from '../../../../api/storefront';
import { useCustomerAuth } from '../../../../context/CustomerAuthContext';
import useCheckoutForm from '../../hooks/useCheckoutForm';
import OrderSummary from './OrderSummary';
import CheckoutForm from './CheckoutForm';

const EMPTY_OBJ = {};

// PS6.4 — `mktpContext` arriva dalla landing e dice se l'utente e'
// DAVVERO in un viaggio marketplace (provenienza directory/home o
// mktp_return gia' in sessione). Default true = comportamento storico
// per eventuali chiamanti che non passano la prop.
export default function InlineEventCheckout({ orgSlug, preload, onClose, mktpContext = true }) {
  // Il hook checkout parla il namespace `storefront` (stesse chiavi
  // dello storefront); i testi di contorno usano `landings`.
  const { t, i18n } = useTranslation(['storefront', 'landings']);
  const { customer, isCustomerAuthenticated, signup: customerSignup } = useCustomerAuth();

  const productId = preload?.productId || null;
  const occurrenceId = preload?.occurrenceId || null;

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

  // ── Contesto marketplace (K1/GT1): stesso timbro del vecchio handoff.
  // L'ordine viaggia con channel=marketplace e la success page dopo
  // Stripe non rimanda alla vetrina ma al Passaporto.
  // PS6.4 — il timbro NON e' piu' incondizionato: solo quando l'utente
  // arriva davvero dal marketplace (prop mktpContext dalla landing).
  // Una landing raggiunta dal profilo /o/ e' vetrina dell'operatore:
  // nessun flag, ordine canale store, success page verso l'operatore.
  useEffect(() => {
    if (!mktpContext) return;
    try {
      sessionStorage.setItem('storefront:mktp_ctx', '1');
      sessionStorage.setItem('storefront:mktp_return', window.location.pathname);
    } catch { /* no-op */ }
  }, [mktpContext]);

  // ── Prodotto + occorrenza risolti dal CATALOGO (non dalla landing) ───
  const product = useMemo(
    () => (catalog?.products || []).find(p => p.id === productId) || null,
    [catalog, productId],
  );
  const occurrence = useMemo(() => {
    if (!product || !occurrenceId) return null;
    return (product.occurrences || []).find(o => o.id === occurrenceId) || null;
  }, [product, occurrenceId]);

  // Mappa {tierId: qty} normalizzata (solo qty > 0), come l'idratazione
  // F3 del vecchio preloadCart in StorefrontPage.
  const tierMap = useMemo(() => {
    const src = preload?.tier_quantities;
    if (!src || typeof src !== 'object') return null;
    const out = {};
    for (const [tid, q] of Object.entries(src)) {
      const n = Math.max(0, Number(q) || 0);
      if (n > 0) out[tid] = n;
    }
    return Object.keys(out).length > 0 ? out : null;
  }, [preload]);

  // ── Stato locale del form partecipanti / campi ordine ────────────────
  const [attendeeDetails, setAttendeeDetails] = useState({});
  const [orderFieldsData, setOrderFieldsData] = useState({});

  // F3 — stesso helper di StorefrontPage: tier ordinati come
  // occurrence.tiers (sort_order), fallback per id sconosciuti.
  const getOrderedTierEntries = useCallback((pid) => {
    if (pid && pid !== productId) return [];
    if (!tierMap) return [];
    const tierDefs = occurrence?.tiers || [];
    const out = [];
    for (const td of tierDefs) {
      const q = Number(tierMap[td.id] || 0);
      if (q > 0) out.push({ id: td.id, label: td.label, qty: q });
    }
    for (const [tid, q] of Object.entries(tierMap)) {
      if (out.find(x => x.id === tid)) continue;
      const qn = Number(q || 0);
      if (qn > 0) out.push({ id: tid, label: null, qty: qn });
    }
    return out;
  }, [productId, tierMap, occurrence]);

  // ── selectedItems: stesso fan-out multi-tier di StorefrontPage ───────
  const selectedItems = useMemo(() => {
    if (!product) return [];
    const qty = Math.max(1, Number(preload?.qty) || 1);
    const tierEntries = getOrderedTierEntries(product.id);
    const totalQty = tierEntries.length > 0
      ? tierEntries.reduce((sum, te) => sum + te.qty, 0)
      : qty;
    const allAttendees = attendeeDetails[product.id];
    const attendeesMatch = Array.isArray(allAttendees) && allAttendees.length === totalQty;
    const toAttendeeShape = (x) => ({
      name: (x?.name || '').trim(),
      email: (x?.email || '').trim() || null,
      phone: x?.phone ? x.phone.trim() : null,
      custom_fields: x?.custom_fields || {},
    });

    if (tierEntries.length > 0) {
      const items = [];
      let cursor = 0;
      for (const te of tierEntries) {
        const item = {
          product_id: product.id,
          quantity: te.qty,
          ticket_tier_id: te.id,
        };
        if (occurrence) item.occurrence_id = occurrence.id;
        if (attendeesMatch) {
          item.attendees = allAttendees.slice(cursor, cursor + te.qty).map(toAttendeeShape);
        }
        cursor += te.qty;
        items.push(item);
      }
      return items;
    }

    const item = { product_id: product.id, quantity: qty };
    if (occurrence) item.occurrence_id = occurrence.id;
    if (attendeesMatch) item.attendees = allAttendees.map(toAttendeeShape);
    return [item];
  }, [product, occurrence, preload, getOrderedTierEntries, attendeeDetails]);

  // Superfici che OrderSummary/hook si aspettano (forma dello store).
  const selectedOccurrences = useMemo(
    () => (product && occurrence ? { [product.id]: occurrence } : EMPTY_OBJ),
    [product, occurrence],
  );
  const selectedTiers = useMemo(
    () => (product && tierMap ? { [product.id]: tierMap } : EMPTY_OBJ),
    [product, tierMap],
  );

  const noop = useCallback(() => {}, []);

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
    selectedServiceOptions: EMPTY_OBJ,
    selectedServiceSlots: EMPTY_OBJ,
    clearCartSnapshot: noop,   // nessun carrello persistito da pulire
    loadAvailability: noop,
    t,
    // PS6.4 — il canale deriva dalla superficie reale, non dal flag di
    // sessione: marketplace solo quando il viaggio e' davvero partito
    // dalla directory.
    channel: mktpContext ? 'marketplace' : 'store',
  });
  const {
    submitted, shippingSummary, couponValidationState, modeCopy, setMktpCheckout,
  } = checkout;

  // K2 — checkout marketplace: il form mostra il Passaporto (niente
  // account del venditore) e il submit salva l'email per l'attivazione
  // one-click sulla success page. Stesso flag del vecchio handoff.
  // PS6.4 — solo in vero contesto marketplace: l'attivazione one-click
  // sulla success page esiste solo quando mktp_ctx e' timbrato.
  useEffect(() => {
    if (!mktpContext) return;
    setMktpCheckout({ returnTo: window.location.pathname });
  }, [setMktpCheckout, mktpContext]);

  // ── Stati di caricamento / errore ────────────────────────────────────
  if (loadState === 'loading') {
    return (
      <p className="text-sm text-gray-500 p-6" data-testid="inline-event-checkout-loading">
        {t('landings:product.loading', { defaultValue: 'Caricamento…' })}
      </p>
    );
  }
  if (loadState === 'error' || !catalog) {
    return (
      <div className="p-6 space-y-3" data-testid="inline-event-checkout-error">
        <p className="text-sm text-red-700">
          {t('landings:product.errorBody', { defaultValue: 'Qualcosa non ha funzionato, riprova più tardi.' })}
        </p>
        {onClose && (
          <button type="button" onClick={onClose}
                  className="rounded-full border border-gray-300 bg-white px-5 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50">
            {t('landings:operator.inlineClose', { defaultValue: 'Chiudi' })}
          </button>
        )}
      </div>
    );
  }

  // ── Conferma inline (successo non-Stripe: request/approval o direct
  //    con pagamento non attivabile → payment_reason, nessun crash) ────
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
      <div className="p-6" data-testid="inline-event-checkout-success">
        <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-center space-y-2">
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
      </div>
    );
  }

  if (!product) {
    // Il ritiro non e' (piu') nel catalogo pubblico: nessun crash,
    // messaggio chiaro e via d'uscita.
    return (
      <div className="p-6 space-y-3" data-testid="inline-event-checkout-missing">
        <p className="text-sm text-gray-500">
          {t('landings:event.notFoundBody')}
        </p>
        {onClose && (
          <button type="button" onClick={onClose}
                  className="rounded-full border border-gray-300 bg-white px-5 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50">
            {t('landings:operator.inlineClose', { defaultValue: 'Chiudi' })}
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="p-6" data-testid="inline-event-checkout">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-lg font-bold">{modeCopy.modalTitle}</h2>
        {onClose && (
          <button type="button" onClick={onClose}
                  aria-label={t('landings:operator.inlineClose', { defaultValue: 'Chiudi' })}
                  className="text-gray-400 hover:text-gray-600 text-xl">&times;</button>
        )}
      </div>

      <p className="text-sm text-gray-500 mb-4">{modeCopy.modalDesc}</p>

      {/* Riepilogo + form: gli STESSI componenti dello storefront.
          Niente onRemove/onQtyChange: qui si prenota UN ritiro, la
          selezione si cambia chiudendo il pannello (un click). */}
      <OrderSummary
        items={selectedItems}
        products={catalog.products || []}
        selectedOccurrences={selectedOccurrences}
        selectedTiers={selectedTiers}
        rentalDates={EMPTY_OBJ}
        bookingSlots={EMPTY_OBJ}
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
        selectedServiceOptions={EMPTY_OBJ}
        selectedServiceSlots={EMPTY_OBJ}
      />
    </div>
  );
}
