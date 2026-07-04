/**
 * useCartCount — reactive hook that exposes the number of items currently
 * saved in sessionStorage for a given store slug.
 *
 * Used by landing pages (`ReservationLandingPage`, `PhysicalLandingPage`,
 * `DigitalLandingPage`, `ProductLandingPage`, `EventLandingPage`) to show
 * a "Torna al catalogo · Carrello · N" badge on the back link. The
 * badge reassures the customer that their in-progress cart from the
 * storefront survived the drill-in and lets them continue shopping.
 *
 * Why not Context-based subscription? sessionStorage has no native
 * change events inside the same tab (the `storage` event fires only for
 * cross-tab changes). We re-poll on:
 *   - mount (initial render)
 *   - window focus (user alt-tabs and comes back)
 *   - explicit custom event from StorefrontPage when the cart changes
 *     (via CustomEvent dispatched by the persist effect)
 *
 * This keeps the hook dependency-free and avoids wrapping the entire
 * storefront in a provider just for a number-display.
 */

import { useEffect, useState } from 'react';
import { readCartCount } from './useCartStorage';


export default function useCartCount(slug) {
  const [count, setCount] = useState(0);

  useEffect(() => {
    if (!slug) { setCount(0); return undefined; }

    const read = () => setCount(readCartCount(slug));
    read();

    // Cross-tab updates + re-focus (user navigates away and back).
    const onFocus = () => read();
    window.addEventListener('focus', onFocus);

    // Same-tab updates — StorefrontPage dispatches this when it mutates
    // the cart, so a landing page that stays mounted (e.g. back button
    // in a SPA navigation where the landing is still on the stack) sees
    // the new count immediately.
    const onCartChange = (e) => {
      if (!e?.detail?.slug || e.detail.slug === slug) read();
    };
    window.addEventListener('storefront:cart:change', onCartChange);

    return () => {
      window.removeEventListener('focus', onFocus);
      window.removeEventListener('storefront:cart:change', onCartChange);
    };
  }, [slug]);

  return count;
}
