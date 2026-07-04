/**
 * <afianco-test-card> — Phase 0 Step 11 test Web Component.
 *
 * Scopo: validare end-to-end la pipeline Vite + TS + Lit:
 *   1. Custom element registrato in customElements registry
 *   2. Shadow DOM isolation dai CSS del merchant
 *   3. Attributi reattivi via @property decorator
 *   4. Bundle compatibile ES2017 (target legacy browser support)
 *
 * Real components (afianco-product-card, afianco-cart, afianco-checkout)
 * arriveranno in Stream A iniziando con un product browser semplice.
 *
 * Attributes:
 *   - ``store`` (required): slug del merchant Afianco. Usato in futuro per
 *     fetchare /api/public/embed/{store}/... endpoints.
 *   - ``message`` (opzionale): testo custom mostrato nella card. Default
 *     mostra un placeholder informativo.
 *
 * Esempio:
 *   <afianco-test-card store="acme" message="Hello from acme!"></afianco-test-card>
 */

import { LitElement, html, css } from 'lit';
import { customElement, property } from 'lit/decorators.js';

@customElement('afianco-test-card')
export class AfiancoTestCard extends LitElement {
  /**
   * Slug del merchant. Marcato required-by-convention: se mancante,
   * il componente renderizza un warning visibile (no crash).
   */
  @property({ type: String })
  store = '';

  /**
   * Testo custom mostrato nel body della card. Se non specificato,
   * mostra un placeholder di onboarding.
   */
  @property({ type: String })
  message = '';

  static styles = css`
    :host {
      display: inline-block;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      box-sizing: border-box;
    }

    .card {
      border: 1px solid #e2e8f0;
      border-radius: 12px;
      padding: 16px 20px;
      background: #ffffff;
      box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
      max-width: 320px;
      color: #1a202c;
      line-height: 1.5;
    }

    .card-title {
      margin: 0 0 8px;
      font-size: 14px;
      font-weight: 600;
      color: #2d3748;
      letter-spacing: -0.01em;
    }

    .card-body {
      font-size: 13px;
      color: #4a5568;
      margin: 0;
    }

    .warn {
      color: #c05621;
      background: #fffaf0;
      padding: 8px 12px;
      border-radius: 6px;
      font-size: 12px;
      margin-top: 8px;
    }

    .badge {
      display: inline-block;
      font-size: 11px;
      font-weight: 500;
      color: #6b7280;
      background: #f3f4f6;
      padding: 2px 8px;
      border-radius: 999px;
      margin-left: 6px;
    }
  `;

  render() {
    const displayMessage =
      this.message || 'Afianco embed SDK is loaded correctly.';
    return html`
      <div class="card" role="status" aria-live="polite">
        <h3 class="card-title">
          afianco-test-card<span class="badge">v0.1</span>
        </h3>
        <p class="card-body">${displayMessage}</p>
        ${this.store
          ? html`<p class="card-body">
              <small>store: <code>${this.store}</code></small>
            </p>`
          : html`<p class="warn">
              Missing required attribute <code>store</code>. Add e.g.
              <code>store="acme"</code> for cross-tenant scoping in future
              components.
            </p>`}
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'afianco-test-card': AfiancoTestCard;
  }
}
