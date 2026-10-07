/**
 * InlineProdottoCheckout — compra un PRODOTTO (digitale o fisico) dal
 * profilo, in pagina (P1, 6/10/2026). Versione snella di
 * InlineServiceCheckout: niente slot, opzioni o richieste libere;
 * quantità 1 (per ora); stesso carrello, stesso hook, stesso form dello
 * storefront. L'account Aurya è OBBLIGATORIO: il file deve finire in
 * /account → «I miei file» e l'ordine deve appartenere a una persona.
 * Il backend lo impone (prodotto_richiede_account); qui si guida.
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
import GrazieCerchio from './GrazieCerchio';

export default function InlineProdottoCheckout({ orgSlug, row, onClose }) {
  const { t, i18n } = useTranslation(['storefront', 'landings']);
  const { customer, isCustomerAuthenticated, signup: customerSignup } = useCustomerAuth();
  const productId = row.product_id;

  useEffect(() => {
    try {
      sessionStorage.removeItem('storefront:mktp_ctx');
      sessionStorage.removeItem('storefront:mktp_return');
    } catch { /* no-op */ }
  }, []);

  const [catalog, setCatalog] = useState(null);
  const [loadState, setLoadState] = useState('loading');
  useEffect(() => {
    let mounted = true;
    setLoadState('loading');
    storefrontAPI.getCatalog(orgSlug, (i18n.language || 'it').slice(0, 2))
      .then(res => { if (mounted) { setCatalog(res.data); setLoadState('ready'); } })
      .catch(() => { if (mounted) setLoadState('error'); });
    return () => { mounted = false; };
  }, [orgSlug, i18n.language]);

  const {
    quantities, setQuantities,
    attendeeDetails, setAttendeeDetails,
    orderFieldsData, setOrderFieldsData,
    selectedServiceOptions, selectedServiceSlots,
  } = useStorefrontCart({ slug: orgSlug, t, productsLookup: catalog?.products });

  useEffect(() => {
    if (!productId || loadState !== 'ready') return;
    setQuantities(q => (q[productId] > 0 ? q : { ...q, [productId]: 1 }));
  }, [productId, loadState, setQuantities]);

  const selectedItems = useMemo(() => {
    const qty = quantities[productId];
    if (!productId || !(qty > 0)) return [];
    return [{ product_id: productId, quantity: qty }];
  }, [productId, quantities]);

  const getOrderedTierEntries = useCallback(() => [], []);
  const clearSelection = useCallback(() => {
    setQuantities(prev => {
      if (!prev || prev[productId] === undefined) return prev;
      const next = { ...prev };
      delete next[productId];
      return next;
    });
  }, [productId, setQuantities]);
  const loadAvailabilityNoop = useCallback(() => {}, []);

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
    channel: 'store',
  });
  const { submitted, shippingSummary, couponValidationState, setFormOpen } = checkout;
  // P2 — il gancio carica le opzioni di spedizione solo «a modale aperto»
  // (lo store): qui il checkout e' sempre aperto, quindi lo si dichiara.
  useEffect(() => { if (setFormOpen) setFormOpen(true); }, [setFormOpen]);

  const submittedRef = useRef(false);
  useEffect(() => { submittedRef.current = !!submitted; }, [submitted]);
  useEffect(() => {
    return () => {
      if (submittedRef.current) return;
      try {
        const snap = hydrateCart(orgSlug);
        if (!snap?.quantities || snap.quantities[productId] === undefined) return;
        delete snap.quantities[productId];
        const hasAny = Object.values(snap).some(v => v && typeof v === 'object' && Object.keys(v).length > 0);
        if (hasAny) persistCart(orgSlug, snap); else clearCart(orgSlug);
        window.dispatchEvent(new CustomEvent('storefront:cart:change', { detail: { slug: orgSlug } }));
      } catch { /* no-op */ }
    };
  }, [orgSlug, productId]);

  if (loadState === 'loading') {
    return <p className="text-sm text-gray-500 py-3">{t('landings:product.loading', { defaultValue: 'Caricamento…' })}</p>;
  }
  if (loadState === 'error' || !catalog) {
    return <p className="text-sm text-red-700 py-3">{t('landings:product.errorBody', { defaultValue: 'Qualcosa non ha funzionato, riprova più tardi.' })}</p>;
  }
  if (submitted) {
    return (
      <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-center space-y-2" data-testid="inline-prodotto-success">
        <p className="font-semibold text-gray-900">{t('storefront:submitted.orderReceived')}</p>
        <p className="text-sm text-gray-700">
          {row.item_type === 'course'
            ? 'Appena il pagamento è confermato, il corso è nel tuo account Aurya, in «I miei corsi», e ti arriva anche per email.'
            : row.item_type === 'digital'
              ? 'Appena il pagamento è confermato, il file è nel tuo account Aurya, in «I miei file», e ti arriva anche per email.'
              : 'Appena il pagamento è confermato, chi vende prepara la spedizione e ti scrive.'}
        </p>
        <Link to="/account" className="inline-block text-sm underline text-[#376254]">Vai al mio account</Link>
        <GrazieCerchio email={checkout.form?.email} className="mt-2" />
        {onClose && (
          <button type="button" onClick={onClose} className="mt-1 rounded-full border border-gray-300 bg-white px-5 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50">
            {t('landings:operator.inlineClose', { defaultValue: 'Chiudi' })}
          </button>
        )}
      </div>
    );
  }
  const product = (catalog.products || []).find(p => p.id === productId);
  if (!product) {
    return <p className="text-sm text-gray-500 py-3">Questo prodotto non è al momento disponibile.</p>;
  }

  return (
    <div className="space-y-4" data-testid="inline-prodotto-checkout">
      <OrderSummary
        items={selectedItems}
        products={catalog.products || []}
        selectedOccurrences={{}}
        selectedTiers={{}}
        rentalDates={{}}
        bookingSlots={{}}
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
        richiedeAccount
      />
    </div>
  );
}
