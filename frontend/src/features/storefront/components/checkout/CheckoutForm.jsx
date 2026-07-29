/**
 * CheckoutForm — il <form> del modale checkout storefront.
 *
 * PN2 (PROFILO_NEGOZIO_PIANO_2026-07) — JSX spostato TALE E QUALE da
 * StorefrontPage.js (blocco ~2372-3138). Parametrizzato via l'oggetto
 * `checkout` (ritorno di useCheckoutForm) + le slice carrello della
 * pagina. Nessuna stringa, classe o condizione cambiata; l'indentazione
 * originale e' preservata di proposito (diff-friendly col blocco fonte).
 */
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import MarkdownLite from '../../../../components/MarkdownLite';
// Sprint 2 W2.1 — coupon dry-run validation (parity widget E4.1)
import CouponInput from '../CouponInput';
import { fmtPrice } from '../StorefrontCards';
import { formatAmount } from '../../../../utils/currency';
import { computePasswordStrength } from '../../hooks/useCheckoutForm';
// AP1 — accesso rapido con l'account Aurya (magic link/OTP piattaforma)
import AuryaQuickLogin from './AuryaQuickLogin';

export default function CheckoutForm({
  checkout,
  slug,
  catalog,
  selectedItems,
  isCustomerAuthenticated,
  attendeeDetails,
  setAttendeeDetails,
  orderFieldsData,
  setOrderFieldsData,
  selectedServiceOptions,
  selectedServiceSlots,
}) {
  const { t, i18n } = useTranslation('storefront');
  // PN2 — stati + setter + derivati arrivano impacchettati da
  // useCheckoutForm: stessa superficie delle vecchie closure di pagina.
  const {
    form, setForm,
    submitting,
    handleSubmit,
    fulfillmentContext,
    shippingOptions,
    hasPhysicalCart, physicalSubtotal,
    serviceItemsInCart,
    itemsRequiringAttendees,
    orderFieldsConfig,
    attendeesValid, orderFieldsValid, termsValid, gdprValid, servicesValid,
    effectiveTerms,
    termsExpanded, setTermsExpanded,
    gdprTermsAccepted, setGdprTermsAccepted,
    gdprPrivacyAccepted, setGdprPrivacyAccepted,
    gdprMarketingAccepted, setGdprMarketingAccepted,
    marketingStatus,
    requiresCustomerAccount,
    wantRegister, setWantRegister,
    regPassword, setRegPassword,
    regPasswordConfirm, setRegPasswordConfirm,
    showRegPassword, setShowRegPassword,
    modeCopy,
  } = checkout;
  return (
              <form onSubmit={handleSubmit} className="mt-4 space-y-3">
                {/* Onda 15 — item-specific sections come FIRST (slot review,
                    event attendees) so the customer confirms what they're
                    buying before typing personal/payment data. Customer
                    info, fulfillment, coupon, T&C follow in a second
                    logical block. */}

                {/* Onda 13 — service products in cart: read-only summary.
                    Option + slot are picked on the dedicated product landing
                    (/p/:org/:slug) and arrive here via preloadCart. If the
                    customer opened the checkout without first visiting the
                    landing (unusual path), we show a link back so they can
                    complete the selection. */}
                {serviceItemsInCart.map(({ product, options, hasSlots }) => {
                  const pid = product.id;
                  const selectedOpt = (options || []).find(o => o.id === selectedServiceOptions[pid]);
                  const selectedSlot = selectedServiceSlots[pid];
                  const needsSelection = (options.length > 0 && !selectedOpt) || (hasSlots && !selectedSlot?.date);
                  const landingUrl = product.slug ? `/p/${slug}/${product.slug}` : null;
                  return (
                    <div key={`svc-${pid}`} className="rounded-lg border border-indigo-200 bg-indigo-50/30 p-3">
                      <div className="flex items-start justify-between gap-2">
                        <p className="text-sm font-semibold text-gray-900">{product.name}</p>
                        {landingUrl && (
                          <Link
                            to={landingUrl}
                            className="text-xs text-indigo-700 hover:underline font-medium shrink-0"
                          >{t('storefront:checkout.service.editLink')}</Link>
                        )}
                      </div>
                      {selectedOpt && (
                        <p className="text-xs text-gray-700 mt-1">
                          <span className="text-gray-500">{t('storefront:checkout.service.optionPrefix')}</span> <strong>{selectedOpt.label}</strong> — {formatAmount(Number(selectedOpt.price), catalog?.currency)}
                        </p>
                      )}
                      {selectedSlot?.date && (
                        <p className="text-xs text-gray-700 mt-0.5">
                          <strong>{new Date(selectedSlot.date + 'T12:00').toLocaleDateString(i18n.language, { weekday: 'long', day: 'numeric', month: 'long' })}</strong>
                          {' · '}{selectedSlot.start_time}
                          {selectedSlot.end_time ? ` – ${selectedSlot.end_time}` : ''}
                        </p>
                      )}
                      {needsSelection && (
                        <div className="mt-2 flex items-start gap-2 rounded-md bg-amber-50 border border-amber-200 p-2 text-xs">
                          <span className="text-amber-900">
                            {t('storefront:checkout.service.selectionRequired')}
                          </span>
                          {landingUrl && (
                            <Link
                              to={landingUrl}
                              className="underline text-amber-900 font-semibold"
                            >{t('storefront:checkout.service.openProductLink')}</Link>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}

                {/* F1 Onda 8 — per-ticket holder forms for events that
                    require attendee details. One block per product; one
                    sub-form per seat. */}
                {itemsRequiringAttendees.map(({ item, product, seatLabels }) => {
                  const pid = item.product_id;
                  const entries = attendeeDetails[pid] || [];
                  return (
                    <div key={`attendees-${pid}`} className="rounded-lg border border-blue-200 bg-blue-50/30 p-3 space-y-3">
                      <div>
                        <p className="text-sm font-semibold text-gray-900">
                          {t('storefront:checkout.attendees.title', { name: product.name })}
                        </p>
                        <p className="text-xs text-gray-600 mt-0.5">
                          {t('storefront:checkout.attendees.subtitle')}
                        </p>
                      </div>
                      {entries.map((entry, idx) => {
                        // F2 Onda 9 — pull per-field flags from the product
                        const emailReq = product.require_attendee_email !== false;
                        const phoneReq = !!product.require_attendee_phone;
                        const attendeeFieldsCfg = (product.attendee_fields || [])
                          .slice().sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0));
                        const setCustomField = (fid, value) => setAttendeeDetails(prev => {
                          const next = { ...prev };
                          next[pid] = [...(next[pid] || [])];
                          const cur = next[pid][idx] || {};
                          next[pid][idx] = {
                            ...cur,
                            custom_fields: { ...(cur.custom_fields || {}), [fid]: value },
                          };
                          return next;
                        });
                        return (
                          <div key={idx} className="rounded-md bg-white border border-gray-200 p-3 space-y-2">
                            <p className="text-xs font-semibold text-gray-700">
                              {seatLabels?.[idx] || t('storefront:checkout.attendees.ticketIndex', { index: idx + 1 })}
                            </p>
                            <input
                              type="text"
                              required
                              value={entry.name}
                              onChange={e => setAttendeeDetails(prev => {
                                const next = { ...prev };
                                next[pid] = [...(next[pid] || [])];
                                next[pid][idx] = { ...next[pid][idx], name: e.target.value };
                                return next;
                              })}
                              placeholder={t('storefront:checkout.attendees.fullNamePlaceholder')}
                              className="w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:ring-1 focus:ring-gray-800 focus:border-gray-800 outline-none"
                            />
                            <input
                              type="email"
                              required={emailReq}
                              value={entry.email}
                              onChange={e => setAttendeeDetails(prev => {
                                const next = { ...prev };
                                next[pid] = [...(next[pid] || [])];
                                next[pid][idx] = { ...next[pid][idx], email: e.target.value };
                                return next;
                              })}
                              placeholder={emailReq ? t('storefront:checkout.attendees.emailRequired') : t('storefront:checkout.attendees.emailOptional')}
                              className="w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:ring-1 focus:ring-gray-800 focus:border-gray-800 outline-none"
                            />
                            <input
                              type="tel"
                              required={phoneReq}
                              value={entry.phone}
                              onChange={e => setAttendeeDetails(prev => {
                                const next = { ...prev };
                                next[pid] = [...(next[pid] || [])];
                                next[pid][idx] = { ...next[pid][idx], phone: e.target.value };
                                return next;
                              })}
                              placeholder={phoneReq ? t('storefront:checkout.attendees.phoneRequired') : t('storefront:checkout.attendees.phoneOptional')}
                              className="w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:ring-1 focus:ring-gray-800 focus:border-gray-800 outline-none"
                            />

                            {/* F2 Onda 9 — attendee custom fields */}
                            {attendeeFieldsCfg.map(fc => {
                              const v = entry.custom_fields?.[fc.id] ?? '';
                              const common = {
                                className: "w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:ring-1 focus:ring-gray-800 focus:border-gray-800 outline-none",
                                placeholder: fc.placeholder || '',
                              };
                              return (
                                <div key={fc.id}>
                                  <label className="block text-[11px] font-medium text-gray-700 mb-0.5">
                                    {fc.label}{fc.required && ' *'}
                                  </label>
                                  {fc.type === 'textarea' ? (
                                    <textarea {...common} rows={2} value={v} onChange={e => setCustomField(fc.id, e.target.value)} />
                                  ) : fc.type === 'number' ? (
                                    <input {...common} type="number" value={v} onChange={e => setCustomField(fc.id, e.target.value)} />
                                  ) : (
                                    <input {...common} type="text" value={v} onChange={e => setCustomField(fc.id, e.target.value)} />
                                  )}
                                  {fc.help_text && (
                                    <p className="text-[10px] text-gray-500 mt-0.5">{fc.help_text}</p>
                                  )}
                                </div>
                              );
                            })}
                          </div>
                        );
                      })}
                    </div>
                  );
                })}

                {/* AP1 — accesso rapido: chi ha gia' un account Aurya entra
                    con email + codice a 6 cifre (endpoint platform riusati
                    da AccountLoginPage) e si ritrova nome/email prefillati.
                    Il login piattaforma NON cambia lo stato consensi: per
                    CG-4 l'utente resta guest (checkbox privacy/termini
                    invariate qui sotto). */}
                {!isCustomerAuthenticated && (
                  <AuryaQuickLogin
                    onProfile={(acc) => setForm(f => ({
                      ...f,
                      name: acc?.name || f.name,
                      email: acc?.email || f.email,
                    }))}
                  />
                )}

                {/* Customer personal info — comes AFTER item-specific selections
                    so the user first confirms the what, then fills in the who. */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">{t('storefront:checkout.customer.nameLabel')}</label>
                  <input
                    type="text" required value={form.name}
                    onChange={e => setForm({ ...form, name: e.target.value })}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-gray-800 focus:border-transparent outline-none"
                    placeholder={t('storefront:checkout.customer.namePlaceholder')}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">{t('storefront:checkout.customer.emailLabel')}</label>
                  <input
                    type="email" required value={form.email}
                    onChange={e => setForm({ ...form, email: e.target.value })}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-gray-800 focus:border-transparent outline-none"
                    placeholder={t('storefront:checkout.customer.emailPlaceholder')}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">{t('storefront:checkout.customer.phoneLabel')}</label>
                  <input
                    type="tel" value={form.phone}
                    onChange={e => setForm({ ...form, phone: e.target.value })}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-gray-800 focus:border-transparent outline-none"
                    placeholder={t('storefront:checkout.customer.phoneOptional')}
                  />
                </div>
                {/* v10.0 + Sprint 2 W2.3 — Fulfillment mode choice.
                    Supporta 3 modes (parity widget afianco-fulfillment-picker):
                    - shipping (con shipping address required)
                    - local_pickup (ritiro merchant location)
                    - pickup_at_store (ritiro punto vendita specifico
                      configurato dal merchant — gap fix W2.3) */}
                {fulfillmentContext.needsChoice && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">{t('storefront:checkout.fulfillment.label')}</label>
                    <div className="flex gap-2 flex-wrap">
                      {fulfillmentContext.modes.map(mode => {
                        const labelMap = {
                          shipping: t('storefront:checkout.fulfillment.shipping'),
                          local_pickup: t('storefront:checkout.fulfillment.localPickup'),
                          pickup_at_store: t('storefront:checkout.fulfillment.pickupAtStore', 'Ritiro in negozio'),
                        };
                        return (
                          <button
                            key={mode}
                            type="button"
                            onClick={() => setForm({ ...form, fulfillment_mode: mode })}
                            className={`flex-1 rounded-lg border px-3 py-2 text-sm font-medium transition-colors min-w-[120px] ${
                              form.fulfillment_mode === mode
                                ? 'border-[var(--sf-accent-hover,#1f2937)] bg-[var(--sf-accent,#111827)] text-[var(--sf-accent-fg,#ffffff)]'
                                : 'border-gray-300 text-gray-700 hover:border-gray-400'
                            }`}
                          >
                            {labelMap[mode] || mode}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                )}
                {/* Single mode hint (not a selector). Sprint 2 W2.3 — supporta
                    anche pickup_at_store con label corretta. */}
                {!fulfillmentContext.needsChoice && fulfillmentContext.autoMode && fulfillmentContext.autoMode !== 'manual_arrangement' && (
                  <div className="text-xs text-gray-500 bg-gray-50 rounded-lg px-3 py-2">
                    {(() => {
                      const labelMap = {
                        shipping: t('storefront:checkout.fulfillment.shipping'),
                        local_pickup: t('storefront:checkout.fulfillment.localPickup'),
                        pickup_at_store: t('storefront:checkout.fulfillment.pickupAtStore', 'Ritiro in negozio'),
                      };
                      return labelMap[fulfillmentContext.autoMode] || fulfillmentContext.autoMode;
                    })()}
                  </div>
                )}
                {form.fulfillment_mode === 'shipping' && (() => {
                  // Structured shipping address block. Replaces the legacy
                  // single textarea — each field is validated separately at
                  // submit. `updateAddr` is a small helper to update one
                  // field without clobbering siblings.
                  const addr = form.shipping_address_details || {};
                  const updateAddr = (patch) => setForm(f => ({
                    ...f,
                    shipping_address_details: { ...(f.shipping_address_details || {}), ...patch },
                  }));
                  const commonInput = 'w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-gray-800 focus:border-transparent outline-none';
                  return (
                    <div className="space-y-2">
                      <label className="block text-sm font-medium text-gray-700">{t('storefront:checkout.address.label')}</label>

                      <input
                        type="text"
                        value={addr.recipient_name || ''}
                        onChange={e => updateAddr({ recipient_name: e.target.value })}
                        placeholder={t('storefront:checkout.address.recipientPlaceholder')}
                        maxLength={160}
                        className={commonInput}
                      />

                      <div className="grid grid-cols-[1fr_110px] gap-2">
                        <input
                          type="text"
                          value={addr.line1 || ''}
                          onChange={e => updateAddr({ line1: e.target.value })}
                          placeholder={t('storefront:checkout.address.streetPlaceholder')}
                          maxLength={200}
                          className={commonInput}
                        />
                        <input
                          type="text"
                          value={addr.civic || ''}
                          onChange={e => updateAddr({ civic: e.target.value })}
                          placeholder={t('storefront:checkout.address.civicPlaceholder')}
                          maxLength={20}
                          className={commonInput}
                        />
                      </div>

                      <div className="grid grid-cols-[120px_1fr_90px] gap-2">
                        <input
                          type="text"
                          value={addr.postal_code || ''}
                          onChange={e => updateAddr({ postal_code: e.target.value })}
                          placeholder={t('storefront:checkout.address.postalCodePlaceholder')}
                          maxLength={16}
                          inputMode="numeric"
                          className={`${commonInput} tabular-nums`}
                        />
                        <input
                          type="text"
                          value={addr.city || ''}
                          onChange={e => updateAddr({ city: e.target.value })}
                          placeholder={t('storefront:checkout.address.cityPlaceholder')}
                          maxLength={120}
                          className={commonInput}
                        />
                        <input
                          type="text"
                          value={addr.province || ''}
                          onChange={e => updateAddr({ province: e.target.value.toUpperCase() })}
                          placeholder={t('storefront:checkout.address.provincePlaceholder')}
                          maxLength={2}
                          className={`${commonInput} uppercase tracking-wide`}
                        />
                      </div>

                      <select
                        value={addr.country || 'IT'}
                        onChange={e => updateAddr({ country: e.target.value })}
                        className={commonInput}
                      >
                        <option value="IT">{t('storefront:checkout.address.country.IT')}</option>
                        <option value="FR">{t('storefront:checkout.address.country.FR')}</option>
                        <option value="DE">{t('storefront:checkout.address.country.DE')}</option>
                        <option value="CH">{t('storefront:checkout.address.country.CH')}</option>
                        <option value="AT">{t('storefront:checkout.address.country.AT')}</option>
                        <option value="ES">{t('storefront:checkout.address.country.ES')}</option>
                        <option value="SI">{t('storefront:checkout.address.country.SI')}</option>
                        <option value="HR">{t('storefront:checkout.address.country.HR')}</option>
                      </select>
                    </div>
                  );
                })()}

                {/* Shipping option picker — visible only when the cart has
                    physical items AND the customer picked "shipping" mode.
                    Empty options list surfaces a banner so the merchant is
                    nudged to configure at least one option. */}
                {hasPhysicalCart && form.fulfillment_mode === 'shipping' && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">{t('storefront:checkout.shippingOptions.label')}</label>
                    {shippingOptions.length === 0 ? (
                      <div className="rounded-lg bg-amber-50 border border-amber-200 px-3 py-2 text-xs text-amber-900">
                        {t('storefront:checkout.shippingOptions.empty')}
                      </div>
                    ) : (
                      <div className="space-y-1.5">
                        {shippingOptions.map(opt => {
                          const base = Number(opt.base_price || 0);
                          const threshold = opt.free_shipping_threshold;
                          const free = threshold != null && physicalSubtotal >= Number(threshold);
                          const selected = form.shipping_option_id === opt.id;
                          return (
                            <label
                              key={opt.id}
                              className={`flex items-start gap-2 rounded-lg border px-3 py-2 cursor-pointer transition-colors ${
                                selected
                                  ? 'border-gray-800 bg-gray-50'
                                  : 'border-gray-300 hover:border-gray-400 bg-white'
                              }`}
                            >
                              <input
                                type="radio"
                                name="shipping_option"
                                value={opt.id}
                                checked={selected}
                                onChange={() => setForm({ ...form, shipping_option_id: opt.id })}
                                className="mt-0.5"
                              />
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center justify-between gap-2">
                                  <span className="text-sm font-medium text-gray-900">{opt.label}</span>
                                  <span className="text-sm tabular-nums">
                                    {free ? (
                                      <>
                                        <span className="line-through text-gray-400 mr-1">
                                          {fmtPrice(base, catalog.currency)}
                                        </span>
                                        <span className="text-green-700 font-semibold">{t('storefront:summary.shippingFree')}</span>
                                      </>
                                    ) : (
                                      <span className="font-semibold">{fmtPrice(base, catalog.currency)}</span>
                                    )}
                                  </span>
                                </div>
                                {opt.description && (
                                  <p className="text-[11px] text-gray-500 mt-0.5">{opt.description}</p>
                                )}
                                {threshold != null && !free && (
                                  <p className="text-[11px] text-blue-700 mt-0.5">
                                    {t('storefront:summary.addMoreForFree', { amount: fmtPrice(Math.max(0, Number(threshold) - physicalSubtotal), catalog.currency) })}
                                  </p>
                                )}
                              </div>
                            </label>
                          );
                        })}
                      </div>
                    )}
                  </div>
                )}
                {/* F2 Onda 9 — order-level custom fields, rendered inline
                    as standalone fields (F4 fix: removed "Dati ordine"
                    wrapper). Each field uses its own label as the title,
                    same style as Nome/Email/Note above. */}
                {orderFieldsConfig.map(fc => {
                  const v = orderFieldsData[fc.id] ?? '';
                  const setV = (next) => setOrderFieldsData(prev => ({ ...prev, [fc.id]: next }));
                  const common = {
                    className: "w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-gray-800 focus:border-transparent outline-none",
                    placeholder: fc.placeholder || '',
                  };
                  return (
                    <div key={fc.id}>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        {fc.label}{fc.required && ' *'}
                      </label>
                      {fc.type === 'textarea' ? (
                        <textarea {...common} rows={2} value={v} onChange={e => setV(e.target.value)} />
                      ) : fc.type === 'number' ? (
                        <input {...common} type="number" value={v} onChange={e => setV(e.target.value)} />
                      ) : (
                        <input {...common} type="text" value={v} onChange={e => setV(e.target.value)} />
                      )}
                      {fc.help_text && (
                        <p className="text-[11px] text-gray-500 mt-0.5">{fc.help_text}</p>
                      )}
                    </div>
                  );
                })}

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">{t('storefront:checkout.notesLabel')}</label>
                  <textarea
                    value={form.notes}
                    onChange={e => setForm({ ...form, notes: e.target.value })}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-gray-800 focus:border-transparent outline-none"
                    rows={2} placeholder={t('storefront:checkout.notesPlaceholder')}
                  />
                </div>

                {/* Onda 15 — service slot review + event attendees blocks
                    were moved up above the customer info form so the "what"
                    comes before the "who". Keeping an empty marker here for
                    reviewer orientation. */}

                {/* F1 Onda 8 — per-ticket holder forms for events that
                    require attendee details. MOVED UP (Onda 15). */}
                {/* Attendees block moved up above customer info (Onda 15). */}

                {/* Sprint 2 W2.1 — coupon dry-run validation (parity
                    widget E4.1). CouponInput component wraps useCouponValidation
                    hook che fa debounced POST /coupons/validate/{slug}
                    con cart subtotal. Customer vede badge verde/rosso
                    live invece di scoprire al checkout. */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">{t('storefront:checkout.couponLabel')}</label>
                  <CouponInput
                    slug={slug}
                    value={form.coupon_code}
                    onChange={(v) => setForm({ ...form, coupon_code: v })}
                    cartSubtotal={(() => {
                      // Subtotal = somma items * qty * rentalMult (mirror del
                      // calcolo OrderSummary). Calcolato inline per essere
                      // reattivo a cambi cart senza extra state.
                      try {
                        const prods = catalog?.products || [];
                        return (selectedItems || []).reduce((sum, it) => {
                          const p = prods.find(x => x.id === it.product_id);
                          if (!p) return sum;
                          const price = Number(p.unit_price) || 0;
                          return sum + price * (it.quantity || 1);
                        }, 0);
                      } catch {
                        return 0;
                      }
                    })()}
                    placeholder={t('storefront:checkout.couponPlaceholder')}
                  />
                </div>

                {/* RS3 — la checkbox T&C legacy (F4) e' FUSA nel blocco
                    consensi unico qui sotto: le condizioni specifiche
                    del prodotto si leggono da un link dentro la riga
                    Termini. Un solo blocco, una sola spunta. */}

                {/* Wave GDPR-Commerce CG-5 — per-order GDPR consent block.
                    Renders ONLY when the merchant has published their
                    per-store Privacy + Terms (CG-3 admin UI). Legacy
                    stores skip this entire block — backward compat.

                    2026-05-20 — Two INDEPENDENT visibility rules:
                      a. Privacy + Terms checkboxes appear ONLY for
                         guests. Logged-in customers have a fresh CG-4
                         snapshot (the re-consent modal blocks the UI
                         before they reach checkout when versions
                         change), so re-asking is redundant.
                      b. Marketing checkbox appears ONLY when the
                         customer is NOT already opted-in, regardless
                         of guest vs registered. ``useIsMarketingOptedIn``
                         resolves the state from customer.accepted_*
                         (logged-in path) or the public marketing-status
                         endpoint (guest path with debounced lookup).
                         When already opted-in we show a small info line
                         pointing to the unsubscribe link instead.

                    The two outer guards (block visibility) are now
                    OR-composed: render the container if AT LEAST one
                    of the inner sections will appear. */}
                {(!isCustomerAuthenticated || !marketingStatus.isOptedIn) && (
                  <div className="rounded-lg border border-blue-200 bg-blue-50/40 p-3 space-y-2">
                    <p className="text-xs font-medium text-blue-900 uppercase tracking-wide">
                      {t('storefront:checkout.gdpr.title', { defaultValue: 'Privacy e Termini' })}
                    </p>
                    {/* Privacy + Terms — guest only (CG-4 covers registered). */}
                    {!isCustomerAuthenticated && (
                      <>
                        <label className="flex items-start gap-2 cursor-pointer select-none">
                          <input
                            type="checkbox"
                            checked={gdprPrivacyAccepted}
                            onChange={e => setGdprPrivacyAccepted(e.target.checked)}
                            className="mt-0.5 shrink-0 h-4 w-4 rounded border-gray-300 text-gray-900 focus:ring-gray-900"
                            required
                          />
                          <span className="text-sm text-gray-800">
                            {t('storefront:checkout.gdpr.privacy_prefix', { defaultValue: 'Ho letto l\u2019' })}
                            <a
                              href={`/s/${encodeURIComponent(slug || '')}/privacy`}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="underline text-blue-700 hover:no-underline"
                            >
                              {t('storefront:checkout.gdpr.privacy_link', { defaultValue: 'Informativa sulla Privacy' })}
                            </a>
                            {' *'}
                          </span>
                        </label>
                        <label className="flex items-start gap-2 cursor-pointer select-none">
                          <input
                            type="checkbox"
                            checked={gdprTermsAccepted}
                            onChange={e => setGdprTermsAccepted(e.target.checked)}
                            className="mt-0.5 shrink-0 h-4 w-4 rounded border-gray-300 text-gray-900 focus:ring-gray-900"
                            required
                          />
                          <span className="text-sm text-gray-800">
                            {t('storefront:checkout.gdpr.terms_prefix', { defaultValue: 'Accetto i' })}{' '}
                            <a
                              href={`/s/${encodeURIComponent(slug || '')}/terms`}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="underline text-blue-700 hover:no-underline"
                            >
                              {t('storefront:checkout.gdpr.terms_link', { defaultValue: 'Termini e Condizioni' })}
                            </a>
                            {' *'}
                          </span>
                        </label>
                        {/* RS3 — condizioni specifiche del prodotto (caparra,
                            cancellazione custom): stesse checkbox, testo in
                            espansione */}
                        {effectiveTerms && (
                          <div className="pl-6">
                            <button
                              type="button"
                              onClick={() => setTermsExpanded(v => !v)}
                              className="text-xs underline text-blue-700 hover:no-underline"
                            >
                              {t('storefront:checkout.gdpr.specific_terms', { defaultValue: 'Leggi le condizioni specifiche di questo acquisto' })}
                            </button>
                            {termsExpanded && (
                              <div className="mt-2 max-h-64 overflow-y-auto bg-white rounded-md border border-gray-200 p-3">
                                <MarkdownLite source={effectiveTerms} />
                              </div>
                            )}
                          </div>
                        )}
                      </>
                    )}
                    {/* Marketing — visible only when NOT already opted-in.
                        Replaced by a small info line otherwise. */}
                    {!marketingStatus.isOptedIn ? (
                      <label className="flex items-start gap-2 cursor-pointer select-none">
                        <input
                          type="checkbox"
                          checked={gdprMarketingAccepted}
                          onChange={e => setGdprMarketingAccepted(e.target.checked)}
                          className="mt-0.5 shrink-0 h-4 w-4 rounded border-gray-300 text-gray-900 focus:ring-gray-900"
                        />
                        <span className="text-sm text-gray-600">
                          {t('storefront:checkout.gdpr.marketing', {
                            defaultValue: 'Desidero ricevere comunicazioni promozionali (opzionale, revocabile in qualsiasi momento)'
                          })}
                        </span>
                      </label>
                    ) : (
                      <p className="text-xs text-gray-600 italic">
                        ℹ️ {t('storefront:checkout.gdpr.already_opted_in', {
                          defaultValue: 'Sei già iscritto alla newsletter. Per disiscriverti usa il link in fondo a ogni email.',
                        })}
                      </p>
                    )}
                    {/* RS5 — la promessa sull'email, in una riga */}
                    <p className="text-[11px] text-gray-500" data-testid="email-promise">
                      {t('storefront:checkout.gdpr.email_promise', {
                        defaultValue: 'La tua email serve solo per questa prenotazione e per il link alle tue prenotazioni. Niente promozioni senza la spunta qui sopra.',
                      })}
                    </p>
                  </div>
                )}

                {/* ── Optional ecommerce registration (Fase C1) ─────────────
                    Visible only for guest shoppers: a logged-in customer has
                    nothing to do here. Isolated from admin auth by using the
                    customer-auth endpoints (handled in Fase C2). */}
                {/* AP1 — niente piu' scelta 'crea account' con password per
                    i guest: al suo posto il blocco informativo Passaporto
                    (l'account Aurya arriva via email dopo l'ordine, claim
                    RS5 gia' attivo a pagamento/conferma). Vale su OGNI
                    superficie del checkout, non solo marketplace (K2). */}
                {!requiresCustomerAccount && !isCustomerAuthenticated && (
                  <div className="rounded-lg border border-primary/25 bg-primary/5 p-3 flex items-start gap-2"
                       data-testid="aurya-passport-hint">
                    <img src="/logo-aurya-128.png" alt="" aria-hidden className="h-5 w-5 mt-0.5 select-none" draggable={false} />
                    <p className="text-xs text-gray-700">
                      {t('storefront:checkout.auryaPassportHint', { defaultValue: 'I tuoi acquisti in un posto solo: dopo l\'ordine ricevi via email il link al tuo account Aurya.' })}
                    </p>
                  </div>
                )}
                {/* AP1/R1 — il blocco registrazione con password resta nel
                    codice ma e' GATED ai soli carrelli con corso (dove
                    l'account cliente e' strutturalmente obbligatorio):
                    reversibile riallargando questa condizione. */}
                {requiresCustomerAccount && !isCustomerAuthenticated && (() => {
                  const emailOk = !!form.email && form.email.includes('@');
                  const strength = computePasswordStrength(regPassword);
                  const mismatch = wantRegister && regPassword && regPasswordConfirm && regPassword !== regPasswordConfirm;
                  return (
                    <div className={`rounded-lg border p-3 space-y-2 ${
                      requiresCustomerAccount
                        ? 'border-blue-300 bg-blue-50/60'
                        : 'border-gray-200 bg-gray-50/60'
                    }`}>
                      {/* Release 4 (Courses) — contextual banner when the cart
                          contains a course. The account is MANDATORY here:
                          the checkbox is forced-on and non-dismissable. */}
                      {requiresCustomerAccount && (
                        <div className="flex items-start gap-2 rounded-md bg-blue-100/60 border border-blue-200 px-2 py-1.5">
                          <span aria-hidden />
                          <p className="text-xs text-blue-900">
                            <strong>{t('storefront:checkout.signup.courseAlertTitle')}</strong>{' '}
                            {t('storefront:checkout.signup.courseAlertBody')}
                          </p>
                        </div>
                      )}
                      <label className={`flex items-start gap-2 select-none ${
                        requiresCustomerAccount ? 'cursor-default' : 'cursor-pointer'
                      }`}>
                        <input
                          type="checkbox"
                          checked={wantRegister || requiresCustomerAccount}
                          disabled={!emailOk || requiresCustomerAccount}
                          onChange={e => {
                            if (requiresCustomerAccount) return;   // cannot opt out
                            setWantRegister(e.target.checked);
                          }}
                          className="mt-0.5 shrink-0"
                          aria-describedby="reg-hint"
                        />
                        <span className="text-sm text-gray-800">
                          <span className="font-medium">
                            {requiresCustomerAccount ? t('storefront:checkout.signup.createAccountRequired') : t('storefront:checkout.signup.createAccount')}
                          </span>
                          <span className="text-gray-600">
                            {requiresCustomerAccount
                              ? t('storefront:checkout.signup.suffixCourse')
                              : t('storefront:checkout.signup.suffixOrders')}
                          </span>
                          {!emailOk && (
                            <span className="block text-[11px] text-gray-500 mt-0.5">
                              {t('storefront:checkout.signup.fillEmailFirst')}
                            </span>
                          )}
                        </span>
                      </label>
                      {/* Alternative path for shoppers who already have an account */}
                      <p className="text-[11px] text-gray-500 pl-6">
                        {t('storefront:checkout.signup.alreadyHaveAccount')}{' '}
                        <Link
                          to={`/account/login?slug=${encodeURIComponent(slug || '')}`}
                          className="text-gray-700 underline hover:no-underline"
                        >
                          {t('storefront:checkout.signup.loginLink')}
                        </Link>
                      </p>
                      {wantRegister && emailOk && (
                        <div id="reg-hint" className="pl-6 space-y-2">
                          <div>
                            <label className="block text-xs font-medium text-gray-700 mb-1">{t('storefront:checkout.signup.passwordLabel')}</label>
                            <div className="relative">
                              <input
                                type={showRegPassword ? 'text' : 'password'}
                                value={regPassword}
                                onChange={e => setRegPassword(e.target.value)}
                                autoComplete="new-password"
                                aria-describedby="reg-strength"
                                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-gray-800 focus:border-transparent outline-none pr-16"
                                placeholder={t('storefront:checkout.signup.passwordPlaceholder')}
                              />
                              <button
                                type="button"
                                onClick={() => setShowRegPassword(s => !s)}
                                className="absolute right-2 top-1/2 -translate-y-1/2 text-[11px] text-gray-500 hover:text-gray-700"
                                tabIndex={-1}
                              >
                                {showRegPassword ? t('storefront:checkout.signup.hidePw') : t('storefront:checkout.signup.showPw')}
                              </button>
                            </div>
                            {/* Strength meter — visual only; server re-validates */}
                            <div id="reg-strength" className="mt-1">
                              <div className="flex gap-1 h-1" aria-hidden="true">
                                {[0, 1, 2, 3].map(i => (
                                  <span
                                    key={i}
                                    className={`flex-1 rounded-full transition-colors ${
                                      i < strength.score
                                        ? strength.score >= 3 ? 'bg-emerald-500' : strength.score >= 2 ? 'bg-amber-500' : 'bg-red-400'
                                        : 'bg-gray-200'
                                    }`}
                                  />
                                ))}
                              </div>
                              {regPassword && !strength.ok && (
                                <p className="text-[11px] text-gray-500 mt-1">
                                  {strength.reasonCodes.map(c => t(`storefront:password.${c}`)).join(' · ')}
                                </p>
                              )}
                            </div>
                          </div>
                          <div>
                            <label className="block text-xs font-medium text-gray-700 mb-1">{t('storefront:checkout.signup.passwordConfirmLabel')}</label>
                            <input
                              type={showRegPassword ? 'text' : 'password'}
                              value={regPasswordConfirm}
                              onChange={e => setRegPasswordConfirm(e.target.value)}
                              autoComplete="new-password"
                              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-gray-800 focus:border-transparent outline-none"
                              placeholder={t('storefront:checkout.signup.passwordConfirmPlaceholder')}
                            />
                            {mismatch && (
                              <p className="text-[11px] text-red-500 mt-1">{t('storefront:checkout.signup.passwordMismatch')}</p>
                            )}
                          </div>
                          <p className="text-[11px] text-gray-500">
                            {t('storefront:checkout.signup.confirmEmailHint')}
                          </p>
                        </div>
                      )}
                    </div>
                  );
                })()}

                <button
                  type="submit"
                  disabled={submitting || selectedItems.length === 0 || !attendeesValid || !orderFieldsValid || !termsValid || !gdprValid || !servicesValid || (wantRegister && !isCustomerAuthenticated && (!computePasswordStrength(regPassword).ok || regPassword !== regPasswordConfirm))}
                  className="w-full py-2.5 rounded-lg text-sm font-medium disabled:opacity-50 transition-colors"
                  style={catalog?.store_info?.brand_color
                    ? { backgroundColor: catalog.store_info.brand_color, color: catalog.store_info.brand_color_text || '#fff' }
                    : { backgroundColor: '#1a1a1a', color: '#fff' }
                  }
                >
                  {submitting ? t('storefront:checkout.submittingBtn') : modeCopy.submitBtn}
                </button>
              </form>
  );
}
