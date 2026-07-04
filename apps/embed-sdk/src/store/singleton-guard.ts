/**
 * SingletonController — Embed à-la-carte, Fase 5 (refinement).
 *
 * Garantisce che ci sia UN SOLO componente "singleton" attivo per
 * (nome, slug) sulla pagina: cart-drawer, account, product-detail sono
 * overlay `position:fixed` — averne due (es. duplicati per-route in una SPA)
 * crea doppi overlay e doppie azioni (doppio add-to-cart).
 *
 * Comportamento
 * =============
 *   - Il primo che si connette per una chiave (`nome:slug`) e' ATTIVO.
 *   - I successivi restano PASSIVI: non renderizzano e i loro handler
 *     devono fare early-return su ``!active``.
 *   - Alla disconnessione dell'attivo, il successivo in coda viene PROMOSSO
 *     (utile in SPA: la route vecchia smonta, la nuova prende il controllo).
 *
 * Slug: ``store`` attr dell'host > slug di pagina (data-afianco-slug) >
 * ``__default__`` (pagina single-store senza slug esplicito).
 */

import type { ReactiveController, ReactiveControllerHost } from 'lit';

import { getPageConfig } from './page-config.js';

type Host = ReactiveControllerHost & Element;

const _registry = new Map<string, SingletonController[]>();

export class SingletonController implements ReactiveController {
  private readonly host: Host;
  private readonly name: string;
  private key = '';

  /** True se questo e' l'istanza attiva per la chiave (render + handler). */
  active = false;

  constructor(host: ReactiveControllerHost, name: string) {
    this.host = host as Host;
    this.name = name;
    this.host.addController(this);
  }

  private resolveKey(): string {
    let slug = '';
    try {
      // B6 — priorita': attributo store > slug del provider full-store (per
      // non collidere con elementi à-la-carte di slug diverso sulla stessa
      // pagina) > slug di pagina à-la-carte.
      const providerSlug =
        this.host.closest?.('afianco-storefront-init')?.getAttribute('slug') || '';
      slug = this.host.getAttribute('store') || providerSlug || getPageConfig().slug || '';
    } catch {
      slug = '';
    }
    return `${this.name}:${slug || '__default__'}`;
  }

  hostConnected(): void {
    this.key = this.resolveKey();
    const list = _registry.get(this.key) ?? [];
    list.push(this);
    _registry.set(this.key, list);
    this.active = list[0] === this;
    this.host.requestUpdate();
  }

  hostDisconnected(): void {
    const list = _registry.get(this.key);
    if (!list) return;
    const idx = list.indexOf(this);
    if (idx >= 0) list.splice(idx, 1);
    const wasActive = this.active;
    this.active = false;
    if (list.length === 0) {
      _registry.delete(this.key);
      return;
    }
    // Promuovi il nuovo capofila se eravamo noi l'attivo.
    if (wasActive) {
      const head = list[0];
      head.active = true;
      head.host.requestUpdate();
    }
  }
}

/** Test-only: svuota il registry singleton. */
export function __clearSingletonRegistryForTests(): void {
  _registry.clear();
}
