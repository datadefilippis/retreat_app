/**
 * OrderItemPhysical — order line for `item_type=physical`.
 *
 * Step 1 (this file): no extras at the line level — physical product
 * details (shipping address, tracking, dates) live in the Fulfillment
 * card at the top of OrderDetailPage and are shared across every
 * physical line in the same order. Showing them here too would be
 * duplicative.
 *
 * Step 7 will reconsider: per-line tracking when an order ships in
 * multiple parcels (one tracking number per shipment) — but that
 * requires a Fulfillment shape change first.
 */

import React from 'react';
import OrderItemBase from './OrderItemBase';


export default function OrderItemPhysical({ item, currency = 'EUR' }) {
  return <OrderItemBase item={item} currency={currency} />;
}
