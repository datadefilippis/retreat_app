/**
 * OrderItemBase — shared shell every per-type item renderer wraps with.
 *
 * Why a base component
 * --------------------
 * The previous implementation in OrderDetailPage rendered all order
 * lines with the same layout (product_name on the left, qty x unit
 * + line_total on the right) and inlined a few `if (item.X)` blocks
 * for type-specific extras (event date, rental range). Adding a new
 * extra (booking time, ticket QR, download counter) was a question of
 * appending another `if` inside the same JSX block — eventually the
 * file becomes 200+ lines of conditionals.
 *
 * This shell isolates the "frame" — name, totals, divider — so each
 * per-type renderer owns ONLY its specific extras. New product type
 * tomorrow = one new file (e.g. `OrderItemMembership.jsx`) that
 * wraps OrderItemBase and passes its own `extras` content. No edits
 * to existing renderers, no edits to OrderDetailPage.
 *
 * Layout parity
 * -------------
 * The DOM mirrors the previous inline render byte-for-byte (same
 * Tailwind classes) so this commit produces zero visual diff. The
 * follow-up steps add the actual visual richness inside `extras`.
 *
 * Props
 * -----
 *   item         the order line (read for product_name, quantity,
 *                unit_price, line_total)
 *   currency     order.currency, threaded down for formatting
 *   extras       optional ReactNode rendered between the product name
 *                and the right-side totals — host of the type-specific
 *                richness added in subsequent steps
 *   children     full-width content rendered AFTER the totals row
 *                (e.g. ticket grids, download counters). Stays inside
 *                the same border-bottom block so the visual grouping
 *                stays per-line.
 */

import React from 'react';
import { useTranslation } from 'react-i18next';


function fmtCurrency(value, currency = 'EUR', locale = 'it-IT') {
  if (value == null) return '-';
  try {
    return new Intl.NumberFormat(locale, {
      style: 'currency', currency, maximumFractionDigits: 2,
    }).format(value);
  } catch { return `${value} ${currency}`; }
}


export default function OrderItemBase({ item, currency = 'EUR', extras = null, children = null }) {
  const { i18n } = useTranslation();
  return (
    <div className="py-1.5 border-b last:border-0">
      <div className="flex items-center justify-between text-sm">
        <div className="flex-1 min-w-0">
          <p className="font-medium truncate">{item.product_name}</p>
          {extras}
        </div>
        <div className="text-right ml-3">
          <p className="text-muted-foreground text-xs">
            {item.quantity} x {fmtCurrency(item.unit_price, currency, i18n.language)}
          </p>
          <p className="font-medium">{fmtCurrency(item.line_total, currency, i18n.language)}</p>
        </div>
      </div>
      {children}
    </div>
  );
}
