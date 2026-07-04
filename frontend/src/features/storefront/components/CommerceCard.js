/**
 * CommerceCard — shared card shell for the public storefront.
 *
 * Replaces the two divergent card implementations that existed in
 * StorefrontPage.js (EventOccurrenceCard + service branch of ProductCard).
 * One visual language for anything that deep-links to a landing page:
 *   variant="event"   → links to /e/:org/:slug (EventLandingPage)
 *   variant="service" → links to /p/:org/:slug (ProductLandingPage)
 *
 * Physical / rental / booking products keep using ProductCard because they
 * carry inline pickers (date range, slot grid, qty) that belong on the card.
 *
 * Props are intentionally primitive (strings, small objects) so the caller
 * owns the data-to-view mapping. See buildEventCardProps / buildServiceCardProps
 * in CommerceCardVariants.js for the canonical mapping.
 */
import React from 'react';
import { Link } from 'react-router-dom';

function HeroImage({ src, fallbackLetter, grayscale, className = '' }) {
  return (
    <div className={`relative aspect-[16/10] overflow-hidden ${grayscale ? 'grayscale' : ''} ${className}`}>
      {src ? (
        <img
          src={src}
          alt=""
          className="w-full h-full object-cover group-hover:scale-[1.03] transition-transform duration-300"
        />
      ) : (
        <div className="w-full h-full bg-gradient-to-br from-gray-800 to-gray-600 flex items-center justify-center text-white/30 text-5xl font-bold">
          {(fallbackLetter || '?').toUpperCase()}
        </div>
      )}
    </div>
  );
}

function DateBadge({ day, month }) {
  if (!day && !month) return null;
  return (
    <div className="absolute top-3 left-3 bg-white/95 backdrop-blur rounded-lg shadow px-3 py-1.5 text-center min-w-[52px]">
      {month && (
        <p className="text-[10px] uppercase tracking-wider font-semibold text-gray-600 leading-none">{month}</p>
      )}
      {day && (
        <p className="text-xl font-bold leading-none mt-0.5 text-gray-900">{day}</p>
      )}
    </div>
  );
}

function TypeBadge({ label }) {
  if (!label) return null;
  return (
    <div className="absolute top-3 left-3 bg-white/95 backdrop-blur rounded-full shadow px-3 py-1 text-[11px] font-semibold uppercase tracking-wider text-gray-800">
      {label}
    </div>
  );
}

function StatusBadge({ variant, label }) {
  if (!label) return null;
  const cls = variant === 'danger'
    ? 'bg-red-600'
    : variant === 'warning'
      ? 'bg-amber-500'
      : 'bg-gray-700';
  return (
    <div className={`absolute top-3 right-3 ${cls} text-white text-[10px] font-bold uppercase tracking-wider px-2 py-1 rounded`}>
      {label}
    </div>
  );
}

/**
 * CommerceCard
 *
 * @param {object} props
 * @param {string} [props.href]              - Landing URL. If present + !disabled, card is <a>.
 * @param {string} [props.heroSrc]
 * @param {string} [props.heroFallbackLetter]
 * @param {{day?: string, month?: string}} [props.dateBadge]
 * @param {string} [props.typeBadge]         - "Consulenza", "Servizio" — rendered as pill in hero
 * @param {{label: string, variant?: 'danger'|'warning'|'default'}} [props.statusBadge]
 * @param {string} [props.overline]          - small uppercase line above title (e.g. "Sabato · 21:00")
 * @param {string} props.title
 * @param {string} [props.subtitle]          - single line below title (e.g. "📍 Milano")
 * @param {string} [props.description]       - line-clamp-2 body snippet
 * @param {string} [props.priceCaption]      - "A partire da" / "Prezzo"
 * @param {string} [props.priceFormatted]    - "€50"
 * @param {{label: string, variant?: 'primary'|'muted'|'neutral'}} [props.cta]
 * @param {boolean} [props.disabled]
 * @param {boolean} [props.soldOut]
 */
export default function CommerceCard({
  href,
  heroSrc,
  heroFallbackLetter,
  dateBadge,
  typeBadge,
  statusBadge,
  overline,
  title,
  subtitle,
  description,
  priceCaption,
  priceFormatted,
  cta,
  disabled = false,
  soldOut = false,
}) {
  const linkable = href && !disabled;
  // Phase 9 — card visuals driven by the design tokens. The
  // storefront root injects --sf-radius, --sf-card-shadow,
  // --sf-card-shadow-hover, and --sf-card-border (from useDesignTokens);
  // inline style here pulls them so a token change ripples through
  // every card without touching this file.
  //
  // The hover lift (shadow + translate) is wired via inline style
  // event handlers because the hover shadow lives in a CSS variable
  // — Tailwind's `hover:shadow-md` would override the token. Cards
  // that aren't `linkable` (sold-out / disabled) skip the hover
  // handlers and stay at the resting shadow.
  const outerBase = 'h-full border bg-white overflow-hidden flex flex-col transition duration-150';
  const outerStyle = {
    borderRadius: 'var(--sf-radius, 1rem)',
    boxShadow: 'var(--sf-card-shadow, 0 1px 2px 0 rgb(0 0 0 / 0.05))',
    borderColor: 'var(--sf-card-border, transparent)',
  };
  const outerLink = 'group';
  const outerDimmed = soldOut || disabled ? 'opacity-75' : '';

  // Hover handlers: bump shadow + lift. Only attached for clickable
  // cards (linkable === true). The `currentTarget` access guard is
  // a defensive null-check because synthetic events can fire on
  // unmount during React's strict-mode double-render in dev.
  const hoverProps = linkable ? {
    onMouseEnter: (e) => {
      if (!e?.currentTarget) return;
      e.currentTarget.style.boxShadow = 'var(--sf-card-shadow-hover, 0 4px 6px -1px rgb(0 0 0 / 0.1))';
      e.currentTarget.style.transform = 'translateY(-2px)';
    },
    onMouseLeave: (e) => {
      if (!e?.currentTarget) return;
      e.currentTarget.style.boxShadow = 'var(--sf-card-shadow, 0 1px 2px 0 rgb(0 0 0 / 0.05))';
      e.currentTarget.style.transform = '';
    },
  } : {};

  const body = (
    <>
      <div className="relative">
        <HeroImage src={heroSrc} fallbackLetter={heroFallbackLetter || title?.charAt(0)} grayscale={soldOut} />
        {dateBadge ? <DateBadge day={dateBadge.day} month={dateBadge.month} /> : typeBadge ? <TypeBadge label={typeBadge} /> : null}
        {statusBadge && <StatusBadge variant={statusBadge.variant} label={statusBadge.label} />}
      </div>

      <div className="p-4 flex-1 flex flex-col">
        {overline && (
          <p className="text-[11px] uppercase tracking-widest text-gray-500 font-semibold">
            {overline}
          </p>
        )}
        <h3 className="font-bold text-lg text-gray-900 mt-1 leading-tight line-clamp-2 min-h-[3.25rem]">
          {title}
        </h3>
        {subtitle && (
          <p className="text-sm text-gray-600 mt-1.5 line-clamp-1">
            {subtitle}
          </p>
        )}
        {description && (
          <p className="text-sm text-gray-500 mt-2 line-clamp-2">
            {description}
          </p>
        )}

        <div className="flex items-end justify-between gap-3 mt-auto pt-4">
          <div className="min-w-0">
            {priceFormatted && (
              <>
                {priceCaption && (
                  <p className="text-[10px] text-gray-500 uppercase tracking-wide font-medium">{priceCaption}</p>
                )}
                <p className="text-xl font-bold text-gray-900 leading-none whitespace-nowrap">{priceFormatted}</p>
              </>
            )}
          </div>
          {cta && cta.label && (
            <span
              className={
                cta.variant === 'muted'
                  ? 'inline-flex items-center bg-gray-200 text-gray-600 text-sm font-semibold px-3 py-2 rounded-lg whitespace-nowrap'
                  : cta.variant === 'neutral'
                    ? 'inline-flex items-center bg-gray-100 text-gray-500 text-xs font-medium px-3 py-2 rounded-lg whitespace-nowrap'
                    : 'inline-flex items-center gap-1 bg-[var(--sf-accent,#111827)] text-[var(--sf-accent-fg,#ffffff)] text-sm font-semibold px-3 py-2 rounded-lg group-hover:bg-[var(--sf-accent-hover,#1f2937)] whitespace-nowrap'
              }
            >
              {cta.label}
            </span>
          )}
        </div>
      </div>
    </>
  );

  if (linkable) {
    // Onda 15 — React Router Link keeps navigation client-side: instant
    // SPA transition, no full-page reload, no loss of React state, no
    // risk of auth-guard / interceptor re-runs that could swallow the
    // navigation. Crucial for /p/:slug landing pages that rely on
    // location.state for the checkout handoff.
    return (
      <Link
        to={href}
        className={`${outerBase} ${outerLink}`}
        style={outerStyle}
        {...hoverProps}
      >
        {body}
      </Link>
    );
  }
  return <div className={`${outerBase} ${outerDimmed}`} style={outerStyle}>{body}</div>;
}
