/**
 * AfiancoStoreKernel — Embed à-la-carte, Fase 1.
 *
 * "Cervello" condiviso PER SLUG a livello di pagina. Disaccoppia il binding
 * dei dati dalla posizione nel DOM: qualunque elemento afianco-*, ovunque si
 * trovi (menu, body, pagine diverse), si connette allo STESSO kernel via slug
 * e condivide init/carrello/auth/locale come unica fonte di verita'.
 *
 * Pattern: micro-frontend shared kernel (Shopify Buy Buttons / Stripe Elements).
 *
 * Responsabilita'
 * ===============
 *   - possiede l'``AfiancoClient`` per lo slug;
 *   - ``ensureInit()``: fetch ``/embed/init/{slug}`` UNA sola volta (dedup
 *     delle chiamate concorrenti), poi cache in ``state.init``;
 *   - store reattivo: ``subscribe(listener)`` → notify su ogni cambio stato;
 *   - refresh automatico (visibilitychange + polling 90s + storage cross-tab),
 *     attivo solo quando c'e' >=1 subscriber;
 *   - i18n: inizializza la locale al primo init, la aggiorna su
 *     ``afianco:locale-changed``.
 *
 * Registry
 * ========
 * Un solo kernel per slug per pagina, in ``window.__afiancoStores``. La
 * factory ``getStoreKernel(slug)`` ritorna l'istanza esistente o la crea.
 *
 * NB Fase 1: questo modulo e' ADDITIVO. I componenti esistenti continuano a
 * usare il Lit context via ``<afianco-storefront-init>``. I componenti
 * à-la-carte (Fase 2) consumano il kernel via ``StoreConsumerController``.
 */

import {
  createAfiancoClient,
  type AfiancoClient,
  type EmbedInitResponse,
} from '@afianco/api-client';
import { initLocale, getLocale } from '../i18n/index.js';

export type KernelStatus = 'idle' | 'loading' | 'ready' | 'error';

export interface KernelState {
  readonly status: KernelStatus;
  readonly init: EmbedInitResponse | null;
  readonly error: string | null;
  readonly locale: string;
}

export interface KernelOptions {
  baseUrl?: string;
  /** Fase 5 — token preview read-only (anteprima dashboard). */
  previewToken?: string;
  /** Test-only: inietta un client gia' pronto (bypassa createAfiancoClient). */
  client?: AfiancoClient;
}

const _MIN_REINIT_INTERVAL_MS = 60_000;
const _POLLING_INTERVAL_MS = 90_000;

export class AfiancoStoreKernel {
  readonly slug: string;
  readonly baseUrl: string;
  readonly client: AfiancoClient;

  private _state: KernelState = {
    status: 'idle',
    init: null,
    error: null,
    locale: getLocale(),
  };

  private readonly _listeners = new Set<() => void>();
  private _initPromise: Promise<void> | null = null;
  private _lastInitAt = 0;
  private _pollingTimer: ReturnType<typeof setInterval> | null = null;

  constructor(slug: string, opts: KernelOptions = {}) {
    if (!slug) throw new Error('AfiancoStoreKernel: slug is required');
    this.slug = slug;
    this.baseUrl = opts.baseUrl ?? '';
    this.client =
      opts.client ??
      createAfiancoClient({
        slug,
        ...(opts.baseUrl ? { baseUrl: opts.baseUrl } : {}),
        ...(opts.previewToken ? { previewToken: opts.previewToken } : {}),
      });
  }

  // ── Reactive store ──────────────────────────────────────────────────

  get state(): KernelState {
    return this._state;
  }

  /** Sottoscrive ai cambi di stato. Ritorna la funzione di unsubscribe.
   *  Il primo subscriber avvia i timer di refresh + l'init; l'ultimo a
   *  disconnettersi li ferma. */
  subscribe(listener: () => void): () => void {
    const wasEmpty = this._listeners.size === 0;
    this._listeners.add(listener);
    if (wasEmpty) {
      this._attachGlobalListeners();
      this._startPolling();
    }
    // Bootstrap pigro: il primo consumer fa partire l'init.
    if (this._state.status === 'idle') {
      void this.ensureInit();
    }
    return () => {
      this._listeners.delete(listener);
      if (this._listeners.size === 0) {
        this._detachGlobalListeners();
        this._stopPolling();
      }
    };
  }

  private _setState(patch: Partial<KernelState>): void {
    this._state = { ...this._state, ...patch };
    this._listeners.forEach((fn) => {
      try {
        fn();
      } catch {
        // un listener rotto non deve bloccare gli altri
      }
    });
  }

  // ── Bootstrap ───────────────────────────────────────────────────────

  /** Fetch init una sola volta. Le chiamate concorrenti condividono la
   *  stessa promise in volo (dedup). */
  ensureInit(): Promise<void> {
    if (this._state.status === 'ready') return Promise.resolve();
    if (this._initPromise) return this._initPromise;
    this._initPromise = this._doInit({ bypassCache: false }).finally(() => {
      this._initPromise = null;
    });
    return this._initPromise;
  }

  private async _doInit(opts: { bypassCache: boolean }): Promise<void> {
    const isFirst = this._state.status !== 'ready';
    if (isFirst) this._setState({ status: 'loading', error: null });
    try {
      const init = await this.client.embed.getInit({ bypassCache: opts.bypassCache });
      this._lastInitAt = Date.now();
      try {
        initLocale({
          slug: this.slug,
          supportedLanguages: init.storefront_languages ?? ['it'],
          explicitLang: null,
        });
      } catch {
        // i18n soft-fail: non blocca il bootstrap
      }
      this._setState({ status: 'ready', init, error: null, locale: getLocale() });
      this._dispatch('afianco:init-ready', init);
    } catch (e) {
      const message = (e as Error)?.message ?? String(e);
      this._setState({ status: 'error', init: null, error: message, locale: getLocale() });
      this._dispatch('afianco:init-error', { message });
    }
  }

  /** Re-fetch forzato (cache-bust). Rispetta il throttle salvo force. */
  async refresh(force = false): Promise<void> {
    if (this._state.status !== 'ready') return;
    if (!force && Date.now() - this._lastInitAt < _MIN_REINIT_INTERVAL_MS) return;
    await this._doInit({ bypassCache: true });
  }

  // ── Auto-refresh lifecycle ──────────────────────────────────────────

  private _onVisibility = (): void => {
    if (typeof document !== 'undefined' && document.hidden) return;
    void this.refresh(false);
  };

  private _onStorage = (e: StorageEvent): void => {
    if (e.key === `afianco_admin_changed_${this.slug}`) void this.refresh(true);
  };

  private _onLocaleChanged = (): void => {
    const next = getLocale();
    if (next !== this._state.locale) this._setState({ locale: next });
  };

  private _attachGlobalListeners(): void {
    if (typeof document === 'undefined') return;
    document.addEventListener('visibilitychange', this._onVisibility);
    document.addEventListener('afianco:locale-changed', this._onLocaleChanged);
    if (typeof window !== 'undefined') window.addEventListener('storage', this._onStorage);
  }

  private _detachGlobalListeners(): void {
    if (typeof document === 'undefined') return;
    document.removeEventListener('visibilitychange', this._onVisibility);
    document.removeEventListener('afianco:locale-changed', this._onLocaleChanged);
    if (typeof window !== 'undefined') window.removeEventListener('storage', this._onStorage);
  }

  private _startPolling(): void {
    this._stopPolling();
    if (typeof window === 'undefined') return;
    this._pollingTimer = setInterval(() => {
      if (typeof document !== 'undefined' && document.hidden) return;
      void this.refresh(false);
    }, _POLLING_INTERVAL_MS);
  }

  private _stopPolling(): void {
    if (this._pollingTimer !== null) {
      clearInterval(this._pollingTimer);
      this._pollingTimer = null;
    }
  }

  private _dispatch(name: string, detail: unknown): void {
    if (typeof document === 'undefined') return;
    document.dispatchEvent(new CustomEvent(name, { detail, bubbles: true, composed: true }));
  }
}

// ── Registry (un kernel per slug per pagina) ──────────────────────────

interface KernelRegistry {
  get(slug: string): AfiancoStoreKernel | undefined;
  set(slug: string, kernel: AfiancoStoreKernel): void;
}

function _registry(): KernelRegistry {
  const g = (typeof window !== 'undefined' ? window : globalThis) as unknown as {
    __afiancoStores?: Map<string, AfiancoStoreKernel>;
  };
  if (!g.__afiancoStores) {
    Object.defineProperty(g, '__afiancoStores', {
      value: new Map<string, AfiancoStoreKernel>(),
      writable: false,
      configurable: false,
      enumerable: false,
    });
  }
  const map = g.__afiancoStores!;
  return { get: (s) => map.get(s), set: (s, k) => void map.set(s, k) };
}

/**
 * Ritorna il kernel per lo slug, creandolo se assente. Primo-vince sul
 * ``baseUrl``: un secondo getStoreKernel con baseUrl diverso NON ricrea il
 * kernel (warning in console).
 */
export function getStoreKernel(slug: string, opts: KernelOptions = {}): AfiancoStoreKernel {
  const reg = _registry();
  const existing = reg.get(slug);
  if (existing) {
    if (opts.baseUrl && existing.baseUrl && opts.baseUrl !== existing.baseUrl) {
      // eslint-disable-next-line no-console
      console.warn(
        `[afianco] kernel "${slug}" gia' inizializzato con base-url "${existing.baseUrl}"; ` +
          `ignorato "${opts.baseUrl}".`,
      );
    }
    return existing;
  }
  const kernel = new AfiancoStoreKernel(slug, opts);
  reg.set(slug, kernel);
  return kernel;
}

/** Test-only: svuota il registry tra un test e l'altro. */
export function __clearStoreRegistryForTests(): void {
  const g = (typeof window !== 'undefined' ? window : globalThis) as unknown as {
    __afiancoStores?: Map<string, AfiancoStoreKernel>;
  };
  g.__afiancoStores?.clear();
}
