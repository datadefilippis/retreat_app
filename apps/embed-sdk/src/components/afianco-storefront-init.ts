/**
 * <afianco-storefront-init> — Phase 1 Step 22 (Track C root provider).
 *
 * Bootstrap del widget cross-origin Stream A. Va wrappato attorno a
 * QUALSIASI altro componente afianco-* che debba parlare con il backend:
 *
 *   <afianco-storefront-init slug="bottega-demo">
 *     <afianco-product-grid></afianco-product-grid>
 *     <afianco-cart-drawer></afianco-cart-drawer>
 *   </afianco-storefront-init>
 *
 * Cosa fa al mount:
 *   1. Istanzia ``AfiancoClient`` (api-client) con lo slug
 *   2. Chiama ``client.embed.getInit()`` → ottiene branding + categories
 *      + capabilities + currency
 *   3. Espone tutto via Lit context (vedi ``src/context.ts``)
 *   4. Espone CSS variables sul host con i valori di
 *      ``init.store_info.brand_color`` / brand_color_text
 *      → i componenti nested ereditano automaticamente
 *
 * Slots:
 *   - default: i child afianco-* components
 *   - ``loading``: opzionale custom loading state (default: skeleton)
 *   - ``error``: opzionale custom error UI (default: messaggio compatto)
 *
 * Custom events:
 *   - ``afianco:init-ready`` (detail: EmbedInitResponse) — bootstrap OK
 *   - ``afianco:init-error`` (detail: { message }) — bootstrap fallito
 *
 * Attributes:
 *   - ``slug`` (REQUIRED): identificatore del merchant store
 *   - ``base-url`` (OPTIONAL): backend URL override (dev: http://localhost:8000)
 */

import { LitElement, html, css, nothing, type PropertyValues } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { provide } from '@lit/context';
import { afiancoBaseStyles } from '@afianco/design-tokens';
import {
  createAfiancoClient,
  type AfiancoClient,
  type EmbedInitResponse,
} from '@afianco/api-client';
import {
  storefrontContext,
  STOREFRONT_INITIAL,
  type StorefrontContext,
} from '../context.js';
// Track E Step 4.5 — i18n initialization at mount
import { initLocale, getLocale } from '../i18n/index.js';

// ── Track E Step 4.3 — Design tokens (Phase 9) mapping ────────────────
// Mirror del React useDesignTokens (frontend/src/features/storefront/
// hooks/useDesignTokens.js). Manteniamo i nomi esatti dei token Phase 9
// per parita' tra storefront classico e widget embed.

/** font_family slug → CSS font-family stack. */
const FONT_STACKS: Record<string, string> = {
  manrope: "'Manrope', system-ui, -apple-system, sans-serif",
  inter:   "'Inter', system-ui, -apple-system, sans-serif",
  serif:   "Georgia, 'Times New Roman', serif",
  system:  "system-ui, -apple-system, sans-serif",
};

/** border_radius slug → px value (--afianco-radius-md base). */
const RADIUS_MAP: Record<string, number> = {
  sharp:    2,
  standard: 8,
  soft:     14,
  pill:     999,
};

/** density slug → multiplier per spacing scale (1.0 = baseline). */
const DENSITY_MAP: Record<string, number> = {
  compact:  0.75,
  standard: 1.0,
  spacious: 1.5,
};


@customElement('afianco-storefront-init')
export class AfiancoStorefrontInit extends LitElement {
  /** Store slug — required, no default. */
  @property({ type: String, reflect: true })
  slug = '';

  /** Backend base URL. Default to production. */
  @property({ type: String, attribute: 'base-url' })
  baseUrl = '';

  /**
   * Auto-bootstrap on mount. Default true. Set false per test in
   * isolation (il consumer chiamerà ``init()`` manualmente).
   */
  @property({ type: Boolean, attribute: 'no-auto-init' })
  noAutoInit = false;

  /**
   * Track E Step 4.5 — Explicit locale override.
   *
   * Priority chain per locale resolution:
   *   1. Questo attributo HTML (es. <afianco-storefront-init lang="en">)
   *   2. URL query ?lang=xx
   *   3. localStorage[`afianco_lang_{slug}`]
   *   4. navigator.language
   *   5. First in storefront_languages (tipicamente 'it')
   *
   * Quando settato, sovrascrive le fonti 2-5. Customer puo' comunque
   * cambiare via <afianco-language-switcher> a runtime.
   */
  @property({ type: String, attribute: 'lang' })
  lang = '';

  /**
   * Context provided to children. Lit recomputes when @state updates.
   */
  @provide({ context: storefrontContext })
  @state()
  contextValue: StorefrontContext = STOREFRONT_INITIAL;

  static styles = [
    afiancoBaseStyles,
    css`
      :host {
        display: block;
      }
      .skeleton {
        padding: var(--afianco-spacing-xl);
        text-align: center;
        color: var(--afianco-color-text-muted);
        font-size: var(--afianco-font-size-sm);
      }
      .error {
        padding: var(--afianco-spacing-lg);
        background: #fff5f5;
        border: 1px solid #fed7d7;
        border-radius: var(--afianco-radius-md);
        color: var(--afianco-color-danger);
        font-size: var(--afianco-font-size-sm);
      }
    `,
  ];

  // ── Lifecycle ─────────────────────────────────────────────────────────

  /**
   * W4.4 + W4.5 — Throttle re-init per evitare fetch ad ogni
   * micro-switch tab + polling backup.
   *
   * Trade-off:
   *   - Customer torna al tab dopo 5+ min -> visibilitychange -> fetch fresh
   *   - Customer fa Cmd+Tab rapido -> throttle 60s -> no fetch
   *   - Customer rimane sul tab da >90s -> polling backup -> fetch fresh
   *   - Admin cambia lingua in altra tab stessa origin -> storage event -> fetch
   *
   * Polling 90s < cache TTL backend (300s) garantisce pickup veloce dei
   * cambi merchant senza dipendere da visibilitychange (che NON fires se
   * customer rimane sempre sulla stessa tab).
   */
  private _lastInitAt: number = 0;
  private static readonly _MIN_REINIT_INTERVAL_MS = 60_000;
  private static readonly _POLLING_INTERVAL_MS = 90_000;
  private _pollingTimer: number | null = null;

  /**
   * W4.4 — re-fetch /init/{slug} quando il customer torna al tab.
   *
   * Bug fix: pre-W4.4 il widget chiamava init() SOLO al primo mount.
   * Se il merchant cambiava storefront_languages, brand_color, custom_nav_links,
   * design_tokens, ecc., il customer doveva hard-refresh la pagina per
   * vedere il cambio.
   */
  private _onVisibilityChange = (): void => {
    if (document.hidden) return;
    if (this.contextValue.status !== 'ready') return;
    void this._maybeReinit(/* force */ false);
  };

  /**
   * W4.5 — re-fetch on cross-tab storage signal. Admin nello stesso
   * browser (es. localhost dev OR merchant gestisce store dal proprio
   * site con widget embedded) puo' scrivere `afianco_admin_changed_{slug}`
   * in localStorage per signalare config update.
   *
   * Cross-origin NON funziona via storage event (browser security), per
   * quel caso il polling backup garantisce comunque pickup entro 90s.
   */
  private _onStorageChange = (e: StorageEvent): void => {
    if (!e.key) return;
    if (e.key !== `afianco_admin_changed_${this.slug}`) return;
    if (this.contextValue.status !== 'ready') return;
    void this._maybeReinit(/* force */ true);
  };

  /**
   * W4.5 — guarded re-init helper. Honour throttle 60s salvo `force=true`
   * (cross-tab signal e' user-intent, no throttle).
   */
  private async _maybeReinit(force: boolean): Promise<void> {
    if (!force) {
      const now = Date.now();
      if (now - this._lastInitAt < AfiancoStorefrontInit._MIN_REINIT_INTERVAL_MS) {
        return; // throttle
      }
    }
    await this.init({ bypassCache: true });
  }

  /**
   * W4.5 — Start polling timer per re-fetch periodico.
   * Fires every 90s, runs only when document is visible (e.g. tab
   * attiva) per ridurre wasted requests su tab background.
   */
  private _startPolling(): void {
    this._stopPolling();
    this._pollingTimer = window.setInterval(() => {
      if (document.hidden) return; // skip background tab
      if (this.contextValue.status !== 'ready') return;
      void this._maybeReinit(/* force */ false);
    }, AfiancoStorefrontInit._POLLING_INTERVAL_MS);
  }

  private _stopPolling(): void {
    if (this._pollingTimer !== null) {
      clearInterval(this._pollingTimer);
      this._pollingTimer = null;
    }
  }

  connectedCallback(): void {
    super.connectedCallback();
    document.addEventListener('visibilitychange', this._onVisibilityChange);
    window.addEventListener('storage', this._onStorageChange);
    // W4.6 — propaga locale changes via context (auto re-render tutti i consumer)
    document.addEventListener('afianco:locale-changed', this._onLocaleChanged);
    this._startPolling();
  }

  disconnectedCallback(): void {
    document.removeEventListener('visibilitychange', this._onVisibilityChange);
    window.removeEventListener('storage', this._onStorageChange);
    document.removeEventListener('afianco:locale-changed', this._onLocaleChanged);
    this._stopPolling();
    super.disconnectedCallback();
  }

  protected firstUpdated(_changed: PropertyValues): void {
    if (!this.noAutoInit) {
      void this.init();
    }
  }

  // ── Public API ────────────────────────────────────────────────────────

  /**
   * Bootstrap the widget. Safe to call multiple times — the second call
   * re-fetches init data (es. dopo lingua change merchant).
   *
   * W4.5 — `bypassCache` opt forza cache-bust via timestamp query param.
   * Usato dai re-init paths (visibilitychange, polling, storage event)
   * per garantire pickup veloce dei cambi merchant.
   */
  async init(opts: { bypassCache?: boolean } = {}): Promise<void> {
    if (!this.slug) {
      this.contextValue = {
        ...STOREFRONT_INITIAL,
        status: 'error',
        error: 'Missing "slug" attribute on <afianco-storefront-init>.',
      };
      this.dispatchInitErrorEvent('Missing slug');
      return;
    }

    // Loading state (skip se re-init silent in background, evita
    // skeleton flicker quando customer e' nel mezzo di una sessione)
    const isFirstInit = this.contextValue.status !== 'ready';
    if (isFirstInit) {
      this.contextValue = { ...STOREFRONT_INITIAL, status: 'loading' };
    }

    // Client setup (re-instantiate so baseUrl override is picked up
    // anche se cambia tra un init() e il successivo)
    const client: AfiancoClient = createAfiancoClient({
      slug: this.slug,
      ...(this.baseUrl ? { baseUrl: this.baseUrl } : {}),
    });

    try {
      const init: EmbedInitResponse = await client.embed.getInit({
        bypassCache: opts.bypassCache === true,
      });
      this._lastInitAt = Date.now(); // W4.4 throttle baseline
      this.applyBrandingCssVars(init);
      // Track E Step 4.5 — initialize i18n locale dal merchant config
      // (storefront_languages + browser language + localStorage persist).
      // W4.4 — initLocale e' chiamato anche su re-init (visibilitychange),
      // se il merchant ha aggiunto/rimosso lingue il switcher dropdown +
      // current locale vengono sincronizzati automaticamente.
      try {
        initLocale({
          slug: this.slug,
          supportedLanguages: init.storefront_languages ?? ['it'],
          explicitLang: this.lang || null,
        });
      } catch {
        // Soft fail: i18n init non blocca il bootstrap.
      }
      // W4.6 — set context AFTER initLocale cosi' contextValue.locale
      // riflette gia' il locale risolto. Tutti i consumer (con
      // @consume subscribe:true) re-renderizzano se locale cambia.
      this.contextValue = {
        client,
        init,
        status: 'ready',
        error: null,
        locale: getLocale(),
      };
      this.dispatchInitReadyEvent(init);
    } catch (e) {
      const msg = (e as Error)?.message ?? String(e);
      this.contextValue = {
        client,
        init: null,
        status: 'error',
        error: msg,
        locale: getLocale(),
      };
      this.dispatchInitErrorEvent(msg);
    }
  }

  /**
   * W4.6 — handler per propagare locale changes via context.
   *
   * Quando initLocale (o setLocale chiamato dal language-switcher)
   * cambia la lingua, dispatcha event document 'afianco:locale-changed'.
   * Questo handler aggiorna contextValue.locale -> trigger reactive
   * update di TUTTI i consumer Lit con @consume({ subscribe: true }).
   */
  private _onLocaleChanged = (): void => {
    const newLocale = getLocale();
    if (newLocale === this.contextValue.locale) return;
    this.contextValue = {
      ...this.contextValue,
      locale: newLocale,
    };
  };

  // ── Branding ─────────────────────────────────────────────────────────

  /**
   * Applica CSS variables sul host element per branding + design tokens.
   *
   * Track E Step 4.3 — supporto completo dei design tokens Phase 9 oltre
   * ai brand colors. Customer-configurable in admin → propaga al widget
   * automaticamente. Customizable override via inline style sul host
   * element (es. <afianco-storefront-init style="--afianco-color-primary: red">).
   *
   * Priority chain (highest first):
   *   1. Merchant inline `style` override sul host (custom CSS)
   *   2. design_tokens.accent_color → --afianco-color-primary
   *   3. store_info.brand_color → --afianco-color-primary (legacy)
   *   4. afianco-base-styles defaults
   */
  private applyBrandingCssVars(init: EmbedInitResponse): void {
    // ── Brand colors (legacy + design tokens override) ──
    const si = init.store_info;
    if (si?.brand_color) {
      this.style.setProperty('--afianco-color-primary', si.brand_color);
    }
    if (si?.brand_color_text) {
      this.style.setProperty('--afianco-color-primary-text', si.brand_color_text);
    }

    // ── Track E Step 4.3 — Design tokens (Phase 9) ──
    const tokens = init.design_tokens;
    if (!tokens) return;

    // accent_color: prefer over brand_color (più specifico nel Phase 9)
    if (tokens.accent_color) {
      this.style.setProperty('--afianco-color-primary', tokens.accent_color);
    }

    // font_family: mapping da slug → CSS stack
    if (tokens.font_family) {
      const fontStack = FONT_STACKS[tokens.font_family] ?? null;
      if (fontStack) {
        this.style.setProperty('--afianco-font-family', fontStack);
        this.style.setProperty('--afianco-font-body', fontStack);
      }
    }

    // border_radius: mapping da slug → px value
    if (tokens.border_radius) {
      const radius = RADIUS_MAP[tokens.border_radius];
      if (radius != null) {
        this.style.setProperty('--afianco-radius-sm', `${Math.max(2, radius - 2)}px`);
        this.style.setProperty('--afianco-radius-md', `${radius}px`);
        this.style.setProperty('--afianco-radius-lg', `${radius + 4}px`);
      }
    }

    // density: mapping da slug → spacing scale
    if (tokens.density) {
      const scale = DENSITY_MAP[tokens.density];
      if (scale != null) {
        this.style.setProperty('--afianco-spacing-xs', `${4 * scale}px`);
        this.style.setProperty('--afianco-spacing-sm', `${8 * scale}px`);
        this.style.setProperty('--afianco-spacing-md', `${12 * scale}px`);
        this.style.setProperty('--afianco-spacing-lg', `${16 * scale}px`);
        this.style.setProperty('--afianco-spacing-xl', `${24 * scale}px`);
      }
    }

    // header_style + card_style: set as data attribute per CSS selectors
    // (componenti children possono fare :host-context(...) o data-style match)
    if (tokens.header_style) {
      this.dataset.afiancoHeaderStyle = tokens.header_style;
    }
    if (tokens.card_style) {
      this.dataset.afiancoCardStyle = tokens.card_style;
    }
  }

  // ── Events ───────────────────────────────────────────────────────────

  private dispatchInitReadyEvent(detail: EmbedInitResponse): void {
    this.dispatchEvent(
      new CustomEvent<EmbedInitResponse>('afianco:init-ready', {
        detail,
        bubbles: true,
        composed: true,
      }),
    );
  }

  private dispatchInitErrorEvent(message: string): void {
    this.dispatchEvent(
      new CustomEvent<{ message: string }>('afianco:init-error', {
        detail: { message },
        bubbles: true,
        composed: true,
      }),
    );
  }

  // ── Render ───────────────────────────────────────────────────────────

  render() {
    const status = this.contextValue.status;

    if (status === 'loading') {
      return html`
        <slot name="loading">
          <div class="skeleton" role="status" aria-live="polite">
            Loading storefront&hellip;
          </div>
        </slot>
        <slot></slot>
      `;
    }

    if (status === 'error') {
      return html`
        <slot name="error">
          <div class="error" role="alert">
            Cannot load storefront:
            ${this.contextValue.error ?? 'unknown error'}
          </div>
        </slot>
      `;
    }

    // ready: render children
    return html`<slot></slot>${nothing}`;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'afianco-storefront-init': AfiancoStorefrontInit;
  }
  interface HTMLElementEventMap {
    'afianco:init-ready': CustomEvent<EmbedInitResponse>;
    'afianco:init-error': CustomEvent<{ message: string }>;
  }
}
