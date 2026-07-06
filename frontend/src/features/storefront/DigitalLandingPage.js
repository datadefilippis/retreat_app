/**
 * DigitalLandingPage — public landing for a digital product.
 *
 * Release 3 (Digital) B9. Route: /dg/:org_slug/:product_slug
 *
 * Mirrors PhysicalLandingPage but with digital-specific copy:
 *   - Stock indicator tied to the license cap (when tracked)
 *   - "Link download inviato dopo il pagamento" reassurance block
 *   - No fulfillment picker (digital = no shipping)
 *   - Access policy preview (max downloads + validity) when set
 */

import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import i18nInstance from '../../i18n';
import { toast } from 'sonner';
import { storefrontAPI } from '../../api/storefront';
import useProductSeo from './lib/useProductSeo';
import ProductExtrasPicker from './components/ProductExtrasPicker';
import PricePreview, { usePricePreview } from './components/PricePreview';
import OpenCheckoutButton from './components/OpenCheckoutButton';
import useCartCount from './hooks/useCartCount';
import { formatAmount } from '../../utils/currency';
import StoreContextNav from './components/StoreContextNav';


function StockIndicator({ stockQuantity }) {
  const { t } = useTranslation('landings');
  if (stockQuantity == null) return null;
  const n = Number(stockQuantity);
  if (n <= 0) {
    return (
      <span className="inline-flex items-center rounded-full bg-red-100 text-red-900 px-2.5 py-0.5 text-xs font-semibold">
        {t('landings:digital.stockOut')}
      </span>
    );
  }
  if (n <= 5) {
    return (
      <span className="inline-flex items-center rounded-full bg-amber-100 text-amber-900 px-2.5 py-0.5 text-xs font-semibold">
        {t('landings:digital.stockLow', { count: n })}
      </span>
    );
  }
  return (
    <span className="inline-flex items-center rounded-full bg-green-100 text-green-900 px-2.5 py-0.5 text-xs font-semibold">
      {t('landings:digital.stockAvailable')}
    </span>
  );
}


export default function DigitalLandingPage() {
  const { org_slug: orgSlug, product_slug: productSlug } = useParams();
  // 7/7 — contesto negozio: i link delle card store portano ?store=1;
  // la landing mantiene la barra menu dello store (mai uscire).
  const fromStore = new URLSearchParams(window.location.search).get('store') === '1';

  const navigate = useNavigate();
  const { t } = useTranslation('landings');
  const cartCount = useCartCount(orgSlug);

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [qty, setQty] = useState(1);
  const [extraSelections, setExtraSelections] = useState({
    optional_ids: [],
    radio_picks: {},
  });

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    storefrontAPI.getProductLanding(orgSlug, productSlug, (i18nInstance.language || 'it').slice(0, 2))
      .then(res => { if (mounted) { setData(res.data); setLoading(false); } })
      .catch(err => {
        if (!mounted) return;
        setError(err?.response?.status === 404 ? 'not_found' : 'generic');
        setLoading(false);
      });
    return () => { mounted = false; };
  }, [orgSlug, productSlug, i18nInstance.language]);

  const product = data?.product;

  // S1 — parità SEO: meta + JSON-LD (vedi SEO_MASTER_PLAN)
  useProductSeo({ kind: 'dg', orgSlug, productSlug, product,
    storeName: data?.store_info?.display_name, currency: data?.currency });

  useEffect(() => {
    if (!product?.extras) return;
    const defaults = { ...extraSelections };
    const radiosByGroup = {};
    for (const ex of product.extras) {
      if (ex.kind === 'radio_variant' && ex.is_default) {
        radiosByGroup[ex.group_key || '_default'] = ex.id;
      }
    }
    if (Object.keys(radiosByGroup).length > 0 && Object.keys(defaults.radio_picks || {}).length === 0) {
      setExtraSelections({ ...defaults, radio_picks: radiosByGroup });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [product?.id]);

  const { result, loading: previewLoading } = usePricePreview({
    productId: product?.id,
    quantity: qty,
    discountPct: 0,
    dateFrom: null,
    dateTo: null,
    extraSelections,
  });

  // CH compliance v1: backend now ships the resolved currency at the
  // top level of PublicProductLanding. Fall back to store_info (legacy
  // shape) and finally to EUR so older deployments keep rendering.
  const currency = data?.currency || data?.store_info?.currency || 'EUR';

  const stockQty = product?.stock_quantity;
  const hasStock = stockQty == null || Number(stockQty) > 0;
  // Digital usually sells one license per order; cap the picker at 5 to keep
  // UX tight. If the product is stock-tracked, respect that ceiling too.
  const maxQty = stockQty != null ? Math.min(Number(stockQty) || 0, 5) : 5;

  const canProceed = !!product && hasStock && qty >= 1 && qty <= maxQty;

  const handleProceed = () => {
    if (!canProceed || !product) return;
    const preloadCart = {
      productId: product.id,
      qty,
      extra_selections: extraSelections,
    };
    navigate(`/s/${orgSlug}`, { state: { preloadCart } });
    toast.success(t('landings:digital.toast.added'), {
      action: {
        label: t('landings:digital.toast.action'),
        onClick: () => navigate(`/s/${orgSlug}?checkout=1`),
      },
      duration: 4000,
    });
  };

  const meta = product?.metadata || {};
  // Policy line — built from up to 2 numeric facts. Each piece uses an
  // i18next plural key (`_one`/`_other`) so the singular form reads
  // naturally when count === 1.
  const policyLine = useMemo(() => {
    const bits = [];
    if (meta.max_downloads_per_delivery) {
      bits.push(t('landings:digital.policyDownloads', { count: meta.max_downloads_per_delivery }));
    }
    if (meta.access_expiry_days) {
      bits.push(t('landings:digital.policyValidity', { count: meta.access_expiry_days }));
    }
    return bits.join(' · ');
  }, [meta.max_downloads_per_delivery, meta.access_expiry_days, t]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-gray-400">{t('landings:digital.loading')}</div>
      </div>
    );
  }

  if (error === 'not_found') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
        <div className="max-w-md w-full bg-white rounded-2xl shadow-sm border p-8 text-center">
          <div className="text-4xl mb-3">🔎</div>
          <h1 className="text-xl font-bold text-gray-900 mb-2">{t('landings:digital.notFoundTitle')}</h1>
          <p className="text-sm text-gray-600">{t('landings:digital.notFoundBody')}</p>
        </div>
      </div>
    );
  }

  if (error || !product) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
        <div className="max-w-md w-full bg-white rounded-2xl shadow-sm border p-8 text-center">
          <h1 className="text-xl font-bold text-gray-900 mb-2">{t('landings:digital.errorTitle')}</h1>
          <p className="text-sm text-gray-600">{t('landings:digital.errorBody')}</p>
        </div>
      </div>
    );
  }

  const hero = product.cover_image_url || product.image_url;

  return (
    <div className="min-h-screen bg-gray-50 pb-24">
      {fromStore && <StoreContextNav slug={orgSlug} />}
      <div className="max-w-5xl mx-auto px-4 py-4">
        <button
          onClick={() => navigate(`/s/${orgSlug}`)}
          className="text-sm text-gray-600 hover:text-gray-900 inline-flex items-center gap-2"
        >
          <span>{t('landings:digital.backToCatalog')}</span>
          {cartCount > 0 && (
            <span className="inline-flex items-center rounded-full bg-gray-900 text-white text-[10px] font-bold px-2 py-0.5">
              🛒 {cartCount}
            </span>
          )}
        </button>
      </div>

      {/* "Vai al checkout" banner — appears when the cart has items. Gives
          customers a clear way to exit the multi-add flow and proceed. */}
      {cartCount > 0 && (
        <div className="max-w-5xl mx-auto px-4 pb-3">
          <OpenCheckoutButton slug={orgSlug} itemCount={cartCount} variant="landing" />
        </div>
      )}

      <div className="max-w-5xl mx-auto px-4 grid grid-cols-1 lg:grid-cols-[1fr_360px] gap-6">
        <div className="space-y-6">
          <div className="bg-white rounded-2xl shadow-sm border overflow-hidden">
            {hero ? (
              <div className="aspect-[16/9] bg-gray-100 overflow-hidden">
                <img src={hero} alt={product.name} className="w-full h-full object-cover" />
              </div>
            ) : null}
            <div className="p-5 sm:p-6">
              <div className="flex items-center gap-2 mb-2 flex-wrap">
                <span className="text-xs font-semibold uppercase tracking-wider text-gray-500">
                  {t('landings:digital.eyebrow')}
                </span>
                {product.sku && (
                  <span className="text-xs text-gray-400">{t('landings:digital.skuLabel', { sku: product.sku })}</span>
                )}
                <span className="ml-auto">
                  <StockIndicator stockQuantity={stockQty} />
                </span>
              </div>
              <h1 className="text-2xl sm:text-3xl font-bold text-gray-900">{product.name}</h1>
              {product.description && (
                <p className="text-sm text-gray-600 mt-2 leading-relaxed">{product.description}</p>
              )}
              {product.long_description && (
                <div className="text-sm text-gray-700 mt-4 whitespace-pre-line leading-relaxed">
                  {product.long_description}
                </div>
              )}
              {product.unit_price != null && (
                <div className="mt-4 text-lg text-gray-700">
                  <span className="text-sm text-gray-500">{t('landings:digital.priceLabel')}</span>{' '}
                  <span className="font-semibold text-gray-900">{formatAmount(Number(product.unit_price), currency)}</span>
                </div>
              )}
            </div>
          </div>

          {/* Consegna digitale — reassurance + policy */}
          <div className="bg-white rounded-2xl shadow-sm border p-5 sm:p-6 space-y-2">
            <h2 className="text-base font-semibold text-gray-900">{t('landings:digital.howItWorks.title')}</h2>
            <ul className="text-sm text-gray-700 space-y-1">
              <li>{t('landings:digital.howItWorks.linkAfterPayment')}</li>
              <li>{t('landings:digital.howItWorks.notPublic')}</li>
              {policyLine && (
                <li>{t('landings:digital.howItWorks.policyPrefix')}{policyLine}</li>
              )}
            </ul>
          </div>

          {/* Quantity picker */}
          {hasStock && (
            <div className="bg-white rounded-2xl shadow-sm border p-5 sm:p-6 space-y-3">
              <h2 className="text-base font-semibold text-gray-900">{t('landings:digital.qty.heading')}</h2>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setQty(q => Math.max(1, q - 1))}
                  disabled={qty <= 1}
                  className="rounded-md border border-gray-300 bg-white w-9 h-9 text-sm font-semibold hover:border-gray-900 disabled:opacity-40"
                  aria-label={t('landings:digital.qty.decAria')}
                >−</button>
                <input
                  type="number"
                  min="1"
                  max={maxQty}
                  value={qty}
                  onChange={e => {
                    const n = Math.max(1, Math.min(maxQty, Number(e.target.value) || 1));
                    setQty(n);
                  }}
                  className="w-16 rounded-md border border-gray-300 px-2 py-1.5 text-sm text-center tabular-nums focus:border-gray-900 focus:outline-none"
                />
                <button
                  type="button"
                  onClick={() => setQty(q => Math.min(maxQty, q + 1))}
                  disabled={qty >= maxQty}
                  className="rounded-md border border-gray-300 bg-white w-9 h-9 text-sm font-semibold hover:border-gray-900 disabled:opacity-40"
                  aria-label={t('landings:digital.qty.incAria')}
                >+</button>
                {stockQty != null && (
                  <span className="text-xs text-gray-500 ml-1">{t('landings:digital.qty.maxLabel', { n: maxQty })}</span>
                )}
              </div>
            </div>
          )}

          {/* Extras */}
          {(product.extras || []).length > 0 && (
            <ProductExtrasPicker
              extras={product.extras}
              value={extraSelections}
              onChange={setExtraSelections}
              dayCount={null}
              currency={currency}
            />
          )}
        </div>

        <aside className="lg:sticky lg:top-4 lg:self-start space-y-4">
          <PricePreview result={result} loading={previewLoading} currency={currency} flavor="digital" />

          {canProceed ? (
            <button
              onClick={handleProceed}
              className="w-full rounded-md bg-[var(--sf-accent,#111827)] text-[var(--sf-accent-fg,#ffffff)] px-4 py-3 text-sm font-semibold hover:bg-[var(--sf-accent-hover,#1f2937)] flex items-center justify-center gap-2 transition-colors"
            >
              {t('landings:digital.cta.add')}
            </button>
          ) : (
            <div
              aria-disabled="true"
              className="w-full rounded-md bg-gray-100 text-gray-500 px-4 py-3 text-sm font-semibold flex items-center justify-center gap-2 border border-dashed border-gray-300 cursor-not-allowed select-none"
            >
              {hasStock ? t('landings:digital.cta.lockedQty') : t('landings:digital.cta.lockedOOS')}
            </div>
          )}

          <p className="text-[11px] text-gray-500 text-center px-2">
            {t('landings:digital.checkoutHint')}
          </p>
        </aside>
      </div>
    </div>
  );
}
