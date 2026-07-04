/**
 * OrderItemRenderer — dispatch a single OrderLine to the right
 * per-type component.
 *
 * The dispatch table mirrors the canonical product types defined in
 * backend/models/product_types.py (event_ticket, service, rental,
 * physical, digital, course). Legacy / unknown types fall through to
 * OrderItemDefault — which shows the basic layout instead of breaking
 * the page when a new type is added server-side before the frontend
 * has a dedicated renderer.
 *
 * Why a dispatcher (and not a single switch in OrderDetailPage)
 * --------------------------------------------------------------
 * Before this refactor OrderDetailPage rendered all lines via an
 * inline map() with a few `if (item.X)` blocks. Adding richer
 * per-type details (ticket QR, booking time, download counter)
 * meant pushing more conditionals into the same JSX block — quickly
 * unreadable and impossible to test in isolation.
 *
 * With this dispatcher each per-type component owns its own file
 * and its own data dependencies. Adding a new product type tomorrow:
 *   1. Create OrderItemMembership.jsx (wraps OrderItemBase)
 *   2. Add one entry to RENDERERS below
 * — no edits to OrderDetailPage, no edits to other renderers.
 *
 * Props are deliberately uniform across all renderers (item, currency,
 * order, …) so the dispatcher doesn't need to know which fields each
 * one consumes. Renderers ignore props they don't use.
 */

import React from 'react';
import OrderItemEvent from './OrderItemEvent';
import OrderItemRental from './OrderItemRental';
import OrderItemService from './OrderItemService';
import OrderItemPhysical from './OrderItemPhysical';
import OrderItemDigital from './OrderItemDigital';
import OrderItemCourse from './OrderItemCourse';
import OrderItemDefault from './OrderItemDefault';


// Lookup table: item_type -> Component. The default branch handles
// missing/unknown types so a malformed line never crashes the page.
const RENDERERS = {
  event_ticket: OrderItemEvent,
  rental:       OrderItemRental,
  service:      OrderItemService,
  booking:      OrderItemService,    // legacy alias — same UX as service
  physical:     OrderItemPhysical,
  digital:      OrderItemDigital,
  course:       OrderItemCourse,
};


export default function OrderItemRenderer({ item, currency = 'EUR', order = null }) {
  const Component = RENDERERS[item?.item_type] || OrderItemDefault;
  return <Component item={item} currency={currency} order={order} />;
}
