/**
 * StoreConsumerController — Embed à-la-carte, Fase 2.
 *
 * ReactiveController che permette a un componente afianco-* di funzionare
 * ANCHE fuori da ``<afianco-storefront-init>``, agganciandosi allo Store
 * Kernel per-slug (vedi ``store/kernel.ts``).
 *
 * Logica (zero-impatto sui casi esistenti)
 * ========================================
 *   hostConnected:
 *     1. Se l'host e' dentro un ``<afianco-storefront-init>`` (rilevato con
 *        ``closest()`` nel light DOM del sito merchant) → NON fa nulla: il
 *        Lit context del provider gestisce ``host.ctx`` come sempre.
 *     2. Altrimenti risolve lo slug: attributo ``store="..."`` sull'host,
 *        oppure lo slug di default della pagina (``data-afianco-slug``).
 *        Se NON c'e' slug → NON fa nulla (es. ambiente di test, o card con
 *        ``.product`` iniettata): il comportamento esistente e' preservato.
 *     3. Con uno slug: prende il kernel, si sottoscrive e popola ``host.ctx``
 *        (stessa shape del Lit context) ad ogni cambio di stato.
 *
 * In questo modo il retrofit di un componente esistente e' UNA riga
 * (``new StoreConsumerController(this)``) senza toccare i suoi ``this.ctx.*``.
 */

import type { ReactiveController, ReactiveControllerHost } from 'lit';
import { ContextProvider } from '@lit/context';

import {
  storefrontContext,
  STOREFRONT_INITIAL,
  type StorefrontContext,
  type StorefrontStatus,
} from '../context.js';
import { getPageConfig } from './page-config.js';
import { getStoreKernel, type AfiancoStoreKernel, type KernelStatus } from './kernel.js';

type HostEl = ReactiveControllerHost & Element & Record<string, unknown>;

function mapStatus(s: KernelStatus): StorefrontStatus {
  return s === 'idle' ? 'loading' : s;
}

export interface StoreConsumerOptions {
  /** Nome della property dell'host da popolare (default "ctx"). */
  property?: string;
}

export class StoreConsumerController implements ReactiveController {
  private readonly host: HostEl;
  private readonly prop: string;
  private kernel: AfiancoStoreKernel | null = null;
  private unsubscribe: (() => void) | null = null;
  /**
   * In modalita' à-la-carte l'host diventa lui stesso un PROVIDER del context
   * (sourced dal kernel) → i figli annidati (calendario/availability-picker,
   * sezioni account, price-preview, shipping…) ricevono il context esattamente
   * come dentro <afianco-storefront-init>. Creato solo se standalone.
   */
  private provider: ContextProvider<typeof storefrontContext> | null = null;

  constructor(host: ReactiveControllerHost, opts: StoreConsumerOptions = {}) {
    this.host = host as HostEl;
    this.prop = opts.property ?? 'ctx';
    this.host.addController(this);
  }

  /** Kernel risolto (null finche' standalone non e' attivato). */
  get activeKernel(): AfiancoStoreKernel | null {
    return this.kernel;
  }

  hostConnected(): void {
    // (1) C'e' un provider antenato? → modalita' legacy, lascia fare al context.
    try {
      if (this.host.closest && this.host.closest('afianco-storefront-init')) return;
    } catch {
      // closest non disponibile (ambiente non-DOM) → prosegui con kernel.
    }

    // (2) Risolvi lo slug: attributo `store` > slug di default pagina.
    const attrSlug = this.host.getAttribute?.('store') || '';
    const pageCfg = getPageConfig();
    const slug = attrSlug || pageCfg.slug;
    if (!slug) return; // niente slug → nessun take-over (preserva esistente).

    // (3) Diventa provider del context per il proprio sottoalbero (così i
    //     componenti annidati ricevono client/init come in full-store).
    this.provider = new ContextProvider(this.host as unknown as HTMLElement & ReactiveControllerHost, {
      context: storefrontContext,
      initialValue: STOREFRONT_INITIAL,
    });

    // (4) Aggancia il kernel e sincronizza.
    this.kernel = getStoreKernel(slug, {
      ...(pageCfg.baseUrl ? { baseUrl: pageCfg.baseUrl } : {}),
      ...(pageCfg.previewToken ? { previewToken: pageCfg.previewToken } : {}),
    });
    this.sync();
    this.unsubscribe = this.kernel.subscribe(() => this.sync());
  }

  hostDisconnected(): void {
    this.unsubscribe?.();
    this.unsubscribe = null;
  }

  private sync(): void {
    if (!this.kernel) return;
    const s = this.kernel.state;
    const ctx: StorefrontContext = {
      client: this.kernel.client,
      init: s.init,
      status: mapStatus(s.status),
      error: s.error,
      locale: s.locale,
    };
    // Propaga ai figli annidati via context provider…
    this.provider?.setValue(ctx);
    // …e setta la property dell'host per il suo render immediato.
    this.host[this.prop] = ctx;
    this.host.requestUpdate();
  }
}
