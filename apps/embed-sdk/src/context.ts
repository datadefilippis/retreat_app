/**
 * Lit Context — Phase 1 Step 22 (Track C).
 *
 * Definisce il context condiviso tra ``<afianco-storefront-init>`` (provider)
 * e tutti i componenti afianco-* nested (consumer): cart drawer, product
 * card, checkout button, login form, customer portal, ecc.
 *
 * Cosa contiene il context:
 *   - ``client``: l'istanza ``AfiancoClient`` (api-client) configurata
 *     per lo slug del merchant. I componenti chiamano ``client.embed.*``
 *     senza dover ri-istanziare per ogni request.
 *   - ``init``: il bootstrap data (``EmbedInitResponse``) — null durante
 *     loading, non-null dopo successo, oggetto con ``error`` quando fail.
 *   - ``status``: stato del bootstrap (``loading | ready | error``).
 *
 * Pattern Lit: il provider chiama ``@provide({ context: storefrontContext })``,
 * i consumer chiamano ``@consume({ context: storefrontContext, subscribe: true })``.
 */

import { createContext } from '@lit/context';
import type {
  AfiancoClient,
} from '@afianco/api-client';
import type {
  EmbedInitResponse,
} from '@afianco/api-client';

export type StorefrontStatus = 'loading' | 'ready' | 'error';

export interface StorefrontContext {
  /** Client instance — null finche' l'init non e' completato. */
  readonly client: AfiancoClient | null;
  /** Bootstrap response — null durante loading o on error. */
  readonly init: EmbedInitResponse | null;
  /** Status machine. */
  readonly status: StorefrontStatus;
  /** Message error se status === 'error'. */
  readonly error: string | null;
  /**
   * Sprint 4 W4.6 — Locale corrente attiva.
   *
   * Bug fix critico: pre-W4.6 solo 2 componenti su 35 (header,
   * language-switcher) ascoltavano l'event document 'afianco:locale-changed'.
   * Risultato: cambio lingua merchant -> initLocale dispatcha event ->
   * solo header e switcher re-renderizzano, ma cart/checkout/account/
   * signup/login/product-grid/ecc. continuavano a mostrare la vecchia
   * lingua.
   *
   * Fix: il locale fa parte del context Lit. Quando initLocale cambia
   * locale, il provider <afianco-storefront-init> propaga la nuova
   * context value -> TUTTI i consumer con @consume({ subscribe: true })
   * re-renderizzano automaticamente via Lit reactive. Zero subscription
   * boilerplate nei singoli componenti.
   */
  readonly locale: string;
}

/**
 * Initial value (loading). I consumer che fanno mount prima dell'init
 * completion vedono questo state.
 */
export const STOREFRONT_INITIAL: StorefrontContext = {
  client: null,
  init: null,
  status: 'loading',
  error: null,
  locale: 'it',
};

/**
 * Lit Context handle. Esportato come unico, condiviso tra provider e
 * consumer per type-safety automatica via @consume({ context: ..., subscribe }).
 */
export const storefrontContext = createContext<StorefrontContext>(
  Symbol('afianco-storefront-context'),
);
