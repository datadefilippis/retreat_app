/**
 * VerifiedAuryaBadge — la pillola "Verificato Aurya" (PV4,
 * docs/PROFILO_VERIFICATO_PIANO_2026-07.md).
 *
 * La verità del badge è UNA sola: public_profile.interview_verified_at,
 * timbrata dal system admin alla pubblicazione dell'intervista (PV2) e
 * azzerata allo spublica. Questo componente NON decide mai da solo se
 * apparire: chi lo monta lo condiziona al campo del payload
 * (interview_verified_at sul profilo, verified sulle card).
 *
 * Glifo: il loto+sole del marchio (/logo-aurya-128.png, asset già in
 * /public — niente asset nuovi). Ori brand #8a7440 / #cbb578.
 *
 * Props
 * -----
 *   variant  'on-photo' | 'on-light' (default 'on-light')
 *            on-photo: fondo bianco/25 + backdrop-blur (stesso pattern
 *            della pillola "In evidenza" GT3), testo bianco — per cover
 *            e hero. on-light: crema/oro tenue, testo oro scuro, bordo
 *            sottile — per superfici chiare (card, quick view).
 *   size     'sm' | 'md' (default 'md')
 *            sm: glifo + "Verificato" corto, per le card (su mobile la
 *            card non si affolla). md: glifo + "Verificato Aurya", hero.
 *   className  classi extra per la pillola
 */
import React from 'react';
import { useTranslation } from 'react-i18next';

export default function VerifiedAuryaBadge({
  variant = 'on-light',
  size = 'md',
  className = '',
}) {
  const { t } = useTranslation('landings');
  const tooltip = t('landings:verifiedBadge.tooltip', {
    defaultValue: 'Operatore intervistato e verificato dal team Aurya',
  });
  const label = size === 'sm'
    ? t('landings:verifiedBadge.short', { defaultValue: 'Verificato' })
    : t('landings:verifiedBadge.label', { defaultValue: 'Verificato Aurya' });

  // on-light: crema PIENA (non traslucida) così la pillola resta
  // leggibile anche appoggiata a una cover chiara o a una foto.
  const look = variant === 'on-photo'
    ? 'bg-white/25 backdrop-blur text-white shadow-sm'
    : 'bg-[#f8f3e3] text-[#8a7440] border border-[#cbb578]/70';
  const dims = size === 'sm'
    ? 'gap-1 px-2 py-0.5 text-[10px]'
    : 'gap-1.5 px-2.5 py-1 text-[11px]';
  const glyph = size === 'sm' ? 'h-3 w-3' : 'h-3.5 w-3.5';

  return (
    <span
      data-testid="verified-aurya-badge"
      title={tooltip}
      aria-label={tooltip}
      className={`inline-flex items-center rounded-full font-semibold whitespace-nowrap select-none ${dims} ${look} ${className}`}
    >
      {/* il glifo del marchio: cerchio dorato, loto e sole */}
      <img
        src="/logo-aurya-128.png"
        alt=""
        aria-hidden="true"
        draggable={false}
        className={`${glyph} shrink-0 object-contain`}
      />
      {label}
    </span>
  );
}
