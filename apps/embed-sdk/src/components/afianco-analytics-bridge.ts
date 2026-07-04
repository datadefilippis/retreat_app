/**
 * <afianco-analytics-bridge> — Track E Step 5.4 (analytics integration).
 *
 * Componente opt-in che listen ai document-level custom events del widget
 * e li propaga al `window.dataLayer` (Google Tag Manager) e/o `gtag()`
 * (Google Analytics 4) del merchant.
 *
 * Uso:
 *   <afianco-storefront-init slug="acme">
 *     ...
 *     <afianco-analytics-bridge gtm gtag></afianco-analytics-bridge>
 *   </afianco-storefront-init>
 *
 * Attributes:
 *   - gtm (boolean): push events to window.dataLayer (GTM)
 *   - gtag (boolean): call window.gtag() (GA4 direct)
 *   - prefix (string, default 'afianco_'): prefix per event names
 *
 * Eventi monitorati:
 *   - afianco:product-view-requested → 'view_item'
 *   - afianco:add-to-cart → 'add_to_cart'
 *   - afianco:checkout-requested → 'begin_checkout'
 *   - afianco:order-completed → 'purchase'
 *   - afianco:price-updated → (skip, troppo verbose per analytics)
 *   - afianco:customer-logged-in → 'login'
 *   - afianco:customer-signed-up → 'sign_up'
 *
 * Best practice e-commerce GA4: i nomi eventi sopra matchano lo
 * standard event taxonomy di GA4 (view_item, add_to_cart, etc.).
 *
 * Privacy: zero PII inviata al dataLayer (solo product_id, qty, totale).
 * Customer email/nome MAI inclusi nei push events.
 */

import { LitElement } from 'lit';
import { customElement, property } from 'lit/decorators.js';


// Map afianco event → GA4/GTM event name + payload extractor
type EventMapping = {
  ganame: string;
  extractor: (detail: Record<string, unknown>) => Record<string, unknown>;
};

const EVENT_MAP: Record<string, EventMapping> = {
  'afianco:product-view-requested': {
    ganame: 'view_item',
    extractor: (d) => ({
      product_id: (d.product_id as string) ?? (d.product as { id?: string })?.id,
      product_name: (d.product as { name?: string })?.name,
    }),
  },
  'afianco:add-to-cart': {
    ganame: 'add_to_cart',
    extractor: (d) => ({
      product_id: (d.product as { id?: string })?.id,
      product_name: (d.product as { name?: string })?.name,
      quantity: d.quantity,
      currency: (d.product as { currency?: string })?.currency ?? 'EUR',
      value: (d.product as { unit_price?: number })?.unit_price,
    }),
  },
  'afianco:checkout-requested': {
    ganame: 'begin_checkout',
    extractor: (d) => ({
      cart_id: (d.cart as { id?: string })?.id ?? d.cart_id,
      currency: (d.cart as { currency_snapshot?: string })?.currency_snapshot ?? 'EUR',
      value: (d.cart as { subtotal_snapshot?: number })?.subtotal_snapshot,
      items_count: (d.cart as { item_count?: number })?.item_count,
    }),
  },
  'afianco:order-completed': {
    ganame: 'purchase',
    extractor: (d) => ({
      transaction_id: d.order_id,
      order_status: d.order_status,
      payment_status: d.payment_status,
    }),
  },
  'afianco:customer-logged-in': {
    ganame: 'login',
    extractor: () => ({ method: 'afianco_widget' }),
  },
  'afianco:customer-signed-up': {
    ganame: 'sign_up',
    extractor: () => ({ method: 'afianco_widget' }),
  },
};


@customElement('afianco-analytics-bridge')
export class AfiancoAnalyticsBridge extends LitElement {
  /** Push events to window.dataLayer (GTM). */
  @property({ type: Boolean })
  gtm = false;

  /** Call window.gtag() directly (GA4). */
  @property({ type: Boolean })
  gtag = false;

  /** Prefix per event names (default 'afianco_'). */
  @property({ type: String })
  prefix = 'afianco_';

  /** Disable debug console.log (default false). */
  @property({ type: Boolean })
  debug = false;

  // ── Lifecycle ────────────────────────────────────────────────────────

  private _handlers = new Map<string, (e: Event) => void>();

  connectedCallback(): void {
    super.connectedCallback();
    for (const [eventName] of Object.entries(EVENT_MAP)) {
      const handler = (e: Event) => this.dispatchToAnalytics(eventName, e);
      this._handlers.set(eventName, handler);
      document.addEventListener(eventName, handler);
    }
  }

  disconnectedCallback(): void {
    for (const [eventName, handler] of this._handlers) {
      document.removeEventListener(eventName, handler);
    }
    this._handlers.clear();
    super.disconnectedCallback();
  }

  // ── Dispatch logic ───────────────────────────────────────────────────

  private dispatchToAnalytics(eventName: string, event: Event): void {
    const mapping = EVENT_MAP[eventName];
    if (!mapping) return;
    const detail = (event as CustomEvent).detail ?? {};
    let payload: Record<string, unknown>;
    try {
      payload = mapping.extractor(detail as Record<string, unknown>);
    } catch {
      payload = {};
    }
    const gaEvent = `${this.prefix}${mapping.ganame}`;

    if (this.debug && typeof console !== 'undefined') {
      // eslint-disable-next-line no-console
      console.info('[afianco-analytics]', gaEvent, payload);
    }

    // Push to GTM dataLayer
    if (this.gtm) {
      const win = window as unknown as { dataLayer?: Record<string, unknown>[] };
      if (Array.isArray(win.dataLayer)) {
        win.dataLayer.push({ event: gaEvent, ...payload });
      } else if (this.debug) {
        // eslint-disable-next-line no-console
        console.warn('[afianco-analytics] window.dataLayer not initialized — GTM not loaded?');
      }
    }

    // Call gtag() directly (GA4)
    if (this.gtag) {
      const win = window as unknown as { gtag?: (...args: unknown[]) => void };
      if (typeof win.gtag === 'function') {
        win.gtag('event', gaEvent, payload);
      } else if (this.debug) {
        // eslint-disable-next-line no-console
        console.warn('[afianco-analytics] window.gtag not defined — GA4 not loaded?');
      }
    }
  }

  // No render — il componente non ha UI (puro bridge invisibile).
  render() {
    return null;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'afianco-analytics-bridge': AfiancoAnalyticsBridge;
  }
}
