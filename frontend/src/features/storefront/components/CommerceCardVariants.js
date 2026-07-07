/**
 * CommerceCardVariants — canonical mapping from backend shapes to CommerceCard props.
 *
 * Keeps the data-to-view logic out of StorefrontPage so the card stays dumb
 * and the data shapes (which can change with backend versions) stay in one spot.
 *
 * i18n contract
 * -------------
 * Each builder accepts `t` (the react-i18next translator from the
 * `storefront` namespace) and `locale` (e.g. `i18n.language`) so the
 * static copy ("Esaurito", "Vedi evento →", weekday names…) and the
 * Intl date/currency formatters follow the active language. Callers
 * MUST be inside a React component that already calls
 * `useTranslation('storefront')` and pass the resulting `t`.
 *
 * `t` accepts an optional fallback signature `t(key, { defaultValue })`
 * — used here only as a defensive net so the card still paints when a
 * caller forgets to thread the namespace.
 */

const fmtCurrency = (value, currency = 'EUR', locale = 'it-IT') => {
  if (value == null) return null;
  return new Intl.NumberFormat(locale, {
    style: 'currency',
    currency,
    maximumFractionDigits: 0,
  }).format(value);
};

/**
 * Build CommerceCard props for an event occurrence (one per published occurrence).
 */
export function buildEventCardProps({ product, occurrence, orgSlug, currency, t, locale = 'it-IT' }) {
  const tiers = Array.isArray(occurrence.tiers) ? occurrence.tiers : [];
  const activeTierPrices = tiers
    .filter(tier => tier.remaining === null || tier.remaining === undefined || tier.remaining > 0)
    .map(tier => Number(tier.price) || 0);
  const hasTiers = tiers.length > 0;
  const displayPrice = activeTierPrices.length > 0
    ? Math.min(...activeTierPrices)
    : (occurrence.price_override != null
        ? Number(occurrence.price_override)
        : (product.unit_price ?? null));
  const isMultiPrice = hasTiers && new Set(activeTierPrices).size > 1;
  const priceFormatted = fmtCurrency(displayPrice, currency, locale);

  // Date parts
  let day = '', month = '', weekday = '', time = '';
  try {
    const d = new Date(occurrence.start_at);
    day = d.toLocaleDateString(locale, { day: 'numeric' });
    month = d.toLocaleDateString(locale, { month: 'short' }).replace('.', '').toUpperCase();
    weekday = d.toLocaleDateString(locale, { weekday: 'long' });
    time = d.toLocaleTimeString(locale, { hour: '2-digit', minute: '2-digit' });
  } catch {}

  const remaining = occurrence.remaining;
  const isSoldOut = remaining === 0;
  const isRunningOut = remaining != null && remaining > 0 && remaining <= 5;

  const venueLine = [occurrence.venue_name, occurrence.city]
    .filter(Boolean)
    .join(' · ') || occurrence.location || '';

  // ?store=1 — contesto negozio: la landing mantiene la barra menu dello
  // store e i link profilo puntano a /s/:slug/chi-siamo (mai uscire).
  const href = orgSlug && occurrence.slug ? `/e/${orgSlug}/${occurrence.slug}?store=1` : null;

  let statusBadge = null;
  if (isSoldOut) statusBadge = { variant: 'danger', label: t('storefront:cards.event.statusSoldOut') };
  else if (isRunningOut) statusBadge = { variant: 'warning', label: t('storefront:cards.event.statusLastN', { count: remaining }) };

  let cta = null;
  if (isSoldOut) cta = { label: t('storefront:cards.event.ctaSoldOut'), variant: 'muted' };
  else if (href) cta = { label: t('storefront:cards.event.ctaSee'), variant: 'primary' };
  else cta = { label: t('storefront:cards.common.ctaUnpublished'), variant: 'neutral' };

  return {
    href: isSoldOut ? null : href,
    heroSrc: occurrence.cover_image_url || product.image_url,
    heroFallbackLetter: product.name?.charAt(0),
    dateBadge: { day, month },
    statusBadge,
    overline: (weekday || time) ? `${weekday || ''}${weekday && time ? ' · ' : ''}${time || ''}` : null,
    title: product.name,
    subtitle: venueLine ? `${venueLine}` : null,
    description: !occurrence.long_description ? product.description : null,
    priceCaption: priceFormatted ? (isMultiPrice ? t('storefront:cards.common.priceFrom') : t('storefront:cards.common.price')) : null,
    priceFormatted,
    cta,
    soldOut: isSoldOut,
  };
}

/**
 * Build CommerceCard props for a service product (consulenza).
 *
 * Strategy: the card is a teaser that links to /p/:org/:slug (ProductLandingPage),
 * where the user picks service_option + slot and proceeds to checkout.
 * We show the minimum price across active service_options when available,
 * otherwise the product.unit_price.
 */
export function buildServiceCardProps({ product, orgSlug, currency, t, locale = 'it-IT' }) {
  const options = Array.isArray(product.service_options)
    ? product.service_options.filter(o => o.is_active !== false)
    : [];
  const optionPrices = options
    .map(o => Number(o.price))
    .filter(n => !Number.isNaN(n));
  const displayPrice = optionPrices.length > 0
    ? Math.min(...optionPrices)
    : (product.unit_price ?? null);
  const isMultiPrice = optionPrices.length > 1 && new Set(optionPrices).size > 1;
  const priceFormatted = fmtCurrency(displayPrice, currency, locale);

  const href = orgSlug && product.slug ? `/p/${orgSlug}/${product.slug}?store=1` : null;

  // Subtitle: prefer a location hint (store city) then fall back to category.
  const subtitleParts = [];
  if (product.store_city) subtitleParts.push(`${product.store_city}`);
  else if (product.category) subtitleParts.push(product.category);
  const subtitle = subtitleParts.join(' · ') || null;

  // Overline: duration of the service.
  const overline = product.duration_label || null;

  return {
    href,
    heroSrc: product.image_url,
    heroFallbackLetter: product.name?.charAt(0),
    typeBadge: t('storefront:cards.service.typeBadge'),
    overline,
    title: product.name,
    subtitle,
    description: product.description,
    priceCaption: priceFormatted ? (isMultiPrice ? t('storefront:cards.common.priceFrom') : t('storefront:cards.common.price')) : null,
    priceFormatted,
    cta: href ? { label: t('storefront:cards.service.ctaDiscover'), variant: 'primary' } : { label: t('storefront:cards.common.ctaUnavailable'), variant: 'neutral' },
  };
}


/**
 * Release 2 (Physical) — storefront card for item_type=physical.
 *
 * Deep-links to `/ph/:org/:slug` where the customer picks qty + extras with
 * live price preview. Surfaces stock urgency ("Ultimi N", "Esaurito") so the
 * customer can decide quickly without drilling in.
 */
export function buildPhysicalCardProps({ product, orgSlug, currency, t, locale = 'it-IT' }) {
  const href = orgSlug && product.slug ? `/ph/${orgSlug}/${product.slug}?store=1` : null;
  const displayPrice = product.unit_price ?? null;
  const priceFormatted = fmtCurrency(displayPrice, currency, locale);

  const subtitleParts = [];
  if (product.store_city) subtitleParts.push(`${product.store_city}`);
  else if (product.category) subtitleParts.push(product.category);

  // Stock overline: tracked → badge + count; untracked → SKU (when present).
  let overline = null;
  const stockQty = product.stock_quantity;
  if (stockQty != null) {
    const n = Number(stockQty);
    if (n <= 0) overline = t('storefront:cards.physical.stockOut');
    else if (n <= 5) overline = t('storefront:cards.physical.stockLastN', { count: n });
    else overline = t('storefront:cards.physical.stockAvailable');
  } else if (product.sku) {
    overline = t('storefront:cards.physical.skuLine', { sku: product.sku });
  }

  const outOfStock = stockQty != null && Number(stockQty) <= 0;

  return {
    href: outOfStock ? null : href,
    heroSrc: product.image_url,
    heroFallbackLetter: product.name?.charAt(0),
    typeBadge: t('storefront:cards.physical.typeBadge'),
    overline,
    title: product.name,
    subtitle: subtitleParts.join(' · ') || null,
    description: product.description,
    priceCaption: priceFormatted ? t('storefront:cards.common.price') : null,
    priceFormatted,
    cta: outOfStock
      ? { label: t('storefront:cards.physical.ctaSoldOut'), variant: 'neutral' }
      : (href ? { label: t('storefront:cards.physical.ctaBuy'), variant: 'primary' } : { label: t('storefront:cards.common.ctaUnavailable'), variant: 'neutral' }),
  };
}


/**
 * Release 3 (Digital) — storefront card for item_type=digital.
 *
 * Deep-links to `/dg/:org/:slug` where the customer picks qty + extras.
 * Surfaces the "Acquisto istantaneo / link via email" promise inline so
 * customers know what to expect before entering the landing.
 */
export function buildDigitalCardProps({ product, orgSlug, currency, t, locale = 'it-IT' }) {
  const href = orgSlug && product.slug ? `/dg/${orgSlug}/${product.slug}?store=1` : null;
  const displayPrice = product.unit_price ?? null;
  const priceFormatted = fmtCurrency(displayPrice, currency, locale);

  const subtitleParts = [];
  if (product.category) subtitleParts.push(product.category);

  // Overline: either stock urgency or generic "Download digitale".
  let overline = t('storefront:cards.digital.instantDownload');
  const stockQty = product.stock_quantity;
  if (stockQty != null) {
    const n = Number(stockQty);
    if (n <= 0) overline = t('storefront:cards.physical.stockOut');
    else if (n <= 5) overline = t('storefront:cards.digital.licensesLeft', { count: n });
  }

  const outOfStock = stockQty != null && Number(stockQty) <= 0;

  return {
    href: outOfStock ? null : href,
    heroSrc: product.image_url,
    heroFallbackLetter: product.name?.charAt(0),
    typeBadge: t('storefront:cards.digital.typeBadge'),
    overline,
    title: product.name,
    subtitle: subtitleParts.join(' · ') || null,
    description: product.description,
    priceCaption: priceFormatted ? t('storefront:cards.common.price') : null,
    priceFormatted,
    cta: outOfStock
      ? { label: t('storefront:cards.physical.ctaSoldOut'), variant: 'neutral' }
      : (href ? { label: t('storefront:cards.physical.ctaBuy'), variant: 'primary' } : { label: t('storefront:cards.common.ctaUnavailable'), variant: 'neutral' }),
  };
}


/**
 * Release 4 (Courses) — storefront card for item_type=course.
 *
 * Deep-links to `/co/:org/:slug` where the customer sees the curriculum
 * and adds the course to cart (account required at checkout).
 *
 * Subtitle mixes lesson count + total duration so the card gives an
 * immediate sense of the content length before drilling in.
 */
export function buildCourseCardProps({ product, orgSlug, currency, t, locale = 'it-IT' }) {
  const href = orgSlug && product.slug ? `/co/${orgSlug}/${product.slug}?store=1` : null;
  const displayPrice = product.unit_price ?? null;
  const priceFormatted = fmtCurrency(displayPrice, currency, locale);

  const lessonsCount = product.course_lessons_count;
  const durationSec = product.course_duration_seconds;

  const subtitleParts = [];
  if (lessonsCount != null && lessonsCount > 0) {
    subtitleParts.push(t('storefront:cards.course.lessonsCount', { count: lessonsCount }));
  }
  if (durationSec != null && durationSec > 0) {
    const mins = Math.round(durationSec / 60);
    if (mins < 60) subtitleParts.push(t('storefront:cards.course.minutes', { count: mins }));
    else {
      const h = Math.floor(mins / 60);
      const m = mins % 60;
      subtitleParts.push(m === 0
        ? t('storefront:cards.course.hoursOnly', { count: h })
        : t('storefront:cards.course.hoursMinutes', { hours: h, minutes: m }));
    }
  }

  // Overline: access policy callout, or a generic "Video corso" label.
  let overline = t('storefront:cards.course.videoCourse');
  if (product.course_access_policy === 'expiring' && product.course_access_expiry_days) {
    overline = t('storefront:cards.course.accessDays', { count: product.course_access_expiry_days });
  } else if (product.course_access_policy === 'lifetime') {
    overline = t('storefront:cards.course.accessLifetime');
  }

  return {
    href,
    heroSrc: product.image_url,
    heroFallbackLetter: product.name?.charAt(0),
    typeBadge: t('storefront:cards.course.typeBadge'),
    overline,
    title: product.name,
    subtitle: subtitleParts.join(' · ') || (product.category || null),
    description: product.description,
    priceCaption: priceFormatted ? t('storefront:cards.common.price') : null,
    priceFormatted,
    cta: href
      ? { label: t('storefront:cards.course.ctaSee'), variant: 'primary' }
      : { label: t('storefront:cards.common.ctaUnavailable'), variant: 'neutral' },
  };
}


/**
 * Build CommerceCard props for a rental product (Onda 16).
 *
 * Same shape and visual language as event/service cards so the public
 * catalog feels uniform. Deep-links to /r/:org/:slug where the customer
 * picks dates / slot + extras with live price preview.
 *
 * Flavor-aware copy:
 *   - range → "Noleggio" badge, "€X / <unit>" price
 *   - slot  → "Prenotazione" badge, "€X / slot" price
 */
export function buildReservationCardProps({ product, orgSlug, currency, t, locale = 'it-IT' }) {
  const flavor = product.reservation_flavor
    || (product.rental_unit === 'ora' ? 'slot' : 'range');
  const href = orgSlug && product.slug ? `/r/${orgSlug}/${product.slug}?store=1` : null;

  const displayPrice = product.unit_price ?? null;
  const priceFormatted = fmtCurrency(displayPrice, currency, locale);

  const unitLabel = flavor === 'range'
    ? (product.rental_unit || t('storefront:cards.reservation.unitFallback'))
    : t('storefront:cards.reservation.slot');

  const subtitleParts = [];
  if (product.store_city) subtitleParts.push(`${product.store_city}`);
  else if (product.category) subtitleParts.push(product.category);

  // Overline: show slot duration for slot flavor, unit for range.
  const overline = flavor === 'slot'
    ? (product.duration_label
        || (product.slot_duration_minutes ? t('storefront:cards.reservation.minutes', { count: product.slot_duration_minutes }) : null))
    : (product.rental_unit ? t('storefront:cards.reservation.perUnit', { unit: product.rental_unit }) : null);

  return {
    href,
    heroSrc: product.image_url,
    heroFallbackLetter: product.name?.charAt(0),
    typeBadge: flavor === 'range' ? t('storefront:cards.reservation.typeRange') : t('storefront:cards.reservation.typeSlot'),
    overline,
    title: product.name,
    subtitle: subtitleParts.join(' · ') || null,
    description: product.description,
    priceCaption: priceFormatted
      ? (flavor === 'range'
          ? t('storefront:cards.reservation.priceFromUnit', { unit: unitLabel })
          : t('storefront:cards.reservation.pricePerSlot'))
      : null,
    priceFormatted,
    cta: href ? { label: t('storefront:cards.reservation.ctaBook'), variant: 'primary' } : { label: t('storefront:cards.common.ctaUnavailable'), variant: 'neutral' },
  };
}
