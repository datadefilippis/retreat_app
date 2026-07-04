/**
 * OrderItemDefault — fallback renderer when item_type is unknown
 * (e.g. legacy data, future product types not yet wired into the
 * dispatcher).
 *
 * Renders the same minimal layout as the per-type files above: name +
 * qty x price + line_total. This keeps existing data visible during
 * any future migration window — a new product type added to the
 * backend doesn't break the customer portal until the corresponding
 * frontend renderer is shipped, it just gets the bare-bones layout.
 */

import React from 'react';
import OrderItemBase from './OrderItemBase';


export default function OrderItemDefault({ item, currency = 'EUR' }) {
  return <OrderItemBase item={item} currency={currency} />;
}
