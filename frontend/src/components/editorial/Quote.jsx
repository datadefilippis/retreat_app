/**
 * Quote — la voce di una persona, non un testo di servizio: corsivo
 * serif, corpo generoso, righe corte (BRAND_HOME §6.3).
 * Semantica <blockquote> anche quando sta dentro una scheda.
 */
import React from 'react';

const SIZES = {
  card: 'text-base sm:text-lg',
  page: 'text-xl sm:text-2xl lg:text-3xl',
};

export default function Quote({ size = 'card', className = '', children }) {
  return (
    <blockquote
      className={`font-display italic leading-snug max-w-[42ch] ${SIZES[size] || SIZES.card} ${className}`}
    >
      {children}
    </blockquote>
  );
}
