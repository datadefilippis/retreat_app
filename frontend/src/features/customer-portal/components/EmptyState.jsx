/**
 * EmptyState — reusable placeholder shown when a list is empty.
 *
 * Replaces the bespoke <Card><CardContent>"Nessun ordine ancora"</…>
 * pattern scattered across the customer portal. Centralizes the
 * visual identity (border, padding, icon size, copy hierarchy) so
 * the orders/courses/notifications/wishlist surfaces all read the
 * same to first-time customers.
 *
 * Usage:
 *   <EmptyState
 *     icon="🎓"
 *     title="Nessun corso ancora"
 *     description="Quando acquisterai un corso lo troverai qui."
 *     cta={{ to: '/s/store-slug', label: 'Esplora il catalogo' }}
 *   />
 */

import React from 'react';
import { Link } from 'react-router-dom';
import { Card, CardContent } from '../../../components/ui/card';


export default function EmptyState({
  icon = '📭',
  title,
  description,
  cta = null,
  variant = 'card',
}) {
  const inner = (
    <>
      <div className="text-4xl mb-2 leading-none">{icon}</div>
      {title && (
        <h3 className="text-base font-semibold text-gray-900">{title}</h3>
      )}
      {description && (
        <p className="text-sm text-gray-600 mt-1 max-w-md mx-auto">
          {description}
        </p>
      )}
      {cta && (
        <div className="mt-4">
          {cta.to ? (
            <Link
              to={cta.to}
              className="inline-block rounded-md bg-gray-900 text-white px-4 py-2 text-sm font-semibold hover:bg-gray-800"
            >
              {cta.label}
            </Link>
          ) : (
            <button
              type="button"
              onClick={cta.onClick}
              className="rounded-md bg-gray-900 text-white px-4 py-2 text-sm font-semibold hover:bg-gray-800"
            >
              {cta.label}
            </button>
          )}
        </div>
      )}
    </>
  );

  if (variant === 'plain') {
    return <div className="py-12 text-center">{inner}</div>;
  }
  return (
    <Card>
      <CardContent className="py-12 text-center">{inner}</CardContent>
    </Card>
  );
}
