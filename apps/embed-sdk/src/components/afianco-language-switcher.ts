/**
 * <afianco-language-switcher> — Track E Step 4.5 (i18n widget).
 *
 * Dropdown compatto per cambiare la lingua del widget runtime. Esposto
 * automaticamente dal <afianco-header> quando il merchant configura >1
 * lingua nello `storefront_languages` del store.
 *
 * UX:
 *   - Default: icona globo + codice lingua corrente (es. "🌐 IT")
 *   - Click → menu con tutte le lingue supportate del merchant
 *   - Click su lingua → setLocale() + dispatch 'afianco:locale-changed'
 *     → tutti i componenti requestUpdate() automaticamente
 *
 * Mostra SOLO le lingue che il merchant ha configurato nel suo store
 * (intersezione storefront_languages × locales bundled nel SDK).
 *
 * Non emette eventi custom esterni — il cambio lingua e' propagato via
 * document-level 'afianco:locale-changed' che i componenti ascoltano.
 *
 * Auto-hide se solo 1 lingua supportata (no senso del picker).
 */

import { LitElement, html, css, nothing } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { consume } from '@lit/context';
import { afiancoBaseStyles } from '@afianco/design-tokens';
import {
  storefrontContext,
  STOREFRONT_INITIAL,
  type StorefrontContext,
} from '../context.js';
import { getLocale, setLocale, getSupportedLocales } from '../i18n/index.js';


/** Lingue → display label (i18n del switcher stesso). */
const LANG_LABELS: Record<string, string> = {
  it: 'Italiano',
  en: 'English',
  de: 'Deutsch',
  fr: 'Français',
  es: 'Español',
};


@customElement('afianco-language-switcher')
export class AfiancoLanguageSwitcher extends LitElement {
  @consume({ context: storefrontContext, subscribe: true })
  @state()
  ctx: StorefrontContext = STOREFRONT_INITIAL;

  /** Variant: 'compact' (default — icona+codice) | 'full' (label completo). */
  @property({ type: String })
  variant: 'compact' | 'full' = 'compact';

  @state()
  private open = false;

  @state()
  private currentLang = getLocale();

  // ── Lifecycle ────────────────────────────────────────────────────────

  connectedCallback(): void {
    super.connectedCallback();
    // Listen per locale change da altre sorgenti (es. setLocale chiamato
    // direttamente dall'app merchant) per sync lo state visivo.
    document.addEventListener('afianco:locale-changed', this._onLocaleChanged);
    document.addEventListener('click', this._onOutsideClick);
  }

  disconnectedCallback(): void {
    document.removeEventListener('afianco:locale-changed', this._onLocaleChanged);
    document.removeEventListener('click', this._onOutsideClick);
    super.disconnectedCallback();
  }

  private _onLocaleChanged = (): void => {
    this.currentLang = getLocale();
  };

  private _onOutsideClick = (e: MouseEvent): void => {
    if (!this.open) return;
    // Se click NON e' dentro questo host, chiudi dropdown
    if (!e.composedPath().includes(this)) {
      this.open = false;
    }
  };

  // ── Compute supported langs (intersezione SDK × merchant config) ────

  private get supportedLangs(): string[] {
    const sdkLangs = new Set(getSupportedLocales());
    const merchantLangs = this.ctx?.init?.storefront_languages ?? ['it'];
    return merchantLangs.filter((l) => sdkLangs.has(l));
  }

  // ── Handlers ────────────────────────────────────────────────────────

  private toggleMenu(): void {
    this.open = !this.open;
  }

  private handleSelectLang(lang: string): void {
    setLocale(lang, { slug: this.ctx?.client?.slug ?? '' });
    this.open = false;
  }

  // ── Styles ──────────────────────────────────────────────────────────

  static styles = [
    afiancoBaseStyles,
    css`
      :host {
        display: inline-block;
        position: relative;
      }
      .trigger {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: transparent;
        border: 1px solid var(--afianco-color-border, #e5e7eb);
        border-radius: 9999px;
        padding: 6px 12px;
        font-family: inherit;
        font-size: 12px;
        font-weight: 500;
        color: var(--afianco-color-text, #111827);
        cursor: pointer;
        transition: background 0.15s ease;
      }
      .trigger:hover {
        background: var(--afianco-color-muted, #f3f4f6);
      }
      .trigger:focus-visible {
        outline: 2px solid var(--afianco-color-primary, #4b72ce);
        outline-offset: 2px;
      }
      .menu {
        position: absolute;
        top: calc(100% + 6px);
        right: 0;
        background: var(--afianco-color-bg, #ffffff);
        border: 1px solid var(--afianco-color-border, #e5e7eb);
        border-radius: 10px;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
        padding: 4px;
        min-width: 140px;
        z-index: 100;
      }
      .menu-item {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 8px 12px;
        border-radius: 6px;
        cursor: pointer;
        font-size: 13px;
        color: var(--afianco-color-text, #111827);
        transition: background 0.15s ease;
        width: 100%;
        text-align: left;
        background: transparent;
        border: none;
        font-family: inherit;
      }
      .menu-item:hover {
        background: var(--afianco-color-muted, #f3f4f6);
      }
      .menu-item[aria-current='true'] {
        background: var(--afianco-color-primary-soft, #eef2ff);
        color: var(--afianco-color-primary, #4b72ce);
        font-weight: 600;
      }
      .menu-item:focus-visible {
        outline: 2px solid var(--afianco-color-primary, #4b72ce);
        outline-offset: -2px;
      }
      .check {
        margin-left: auto;
        font-weight: 700;
      }
    `,
  ];

  // ── Render ──────────────────────────────────────────────────────────

  render() {
    const langs = this.supportedLangs;
    if (langs.length <= 1) return nothing;

    const displayLang = this.variant === 'full'
      ? (LANG_LABELS[this.currentLang] ?? this.currentLang.toUpperCase())
      : this.currentLang.toUpperCase();

    return html`
      <button
        class="trigger"
        type="button"
        aria-haspopup="listbox"
        aria-expanded=${this.open ? 'true' : 'false'}
        aria-label="Cambia lingua"
        @click=${(e: Event) => {
          e.stopPropagation();
          this.toggleMenu();
        }}>
        <span aria-hidden="true">🌐</span>
        ${displayLang}
        <span aria-hidden="true" style="font-size: 9px;">▾</span>
      </button>
      ${this.open
        ? html`
            <div class="menu" role="listbox" aria-label="Lingue disponibili">
              ${langs.map((lang) => html`
                <button
                  class="menu-item"
                  role="option"
                  type="button"
                  aria-current=${lang === this.currentLang ? 'true' : 'false'}
                  @click=${() => this.handleSelectLang(lang)}>
                  ${LANG_LABELS[lang] ?? lang.toUpperCase()}
                  ${lang === this.currentLang
                    ? html`<span class="check" aria-hidden="true">✓</span>`
                    : ''}
                </button>
              `)}
            </div>
          `
        : ''}
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'afianco-language-switcher': AfiancoLanguageSwitcher;
  }
  interface HTMLElementEventMap {
    'afianco:locale-changed': CustomEvent<{ locale: string }>;
  }
}
