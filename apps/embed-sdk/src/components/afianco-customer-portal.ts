/**
 * <afianco-customer-portal> — Phase 1 Step 28 (Track C, final).
 *
 * Customer "Area Personale" auth-gated. Mostra tab Profilo / Ordini con
 * dati live dal backend (/api/customer/me + /api/customer/orders). Se il
 * customer non e' loggato (token assente in storage), prompt-a un CTA
 * "Accedi" e dispatcha `afianco:auth-required` cosi' il merchant puo'
 * mostrare un <afianco-login> o redirect ad una pagina /accedi.
 *
 * Design choices
 * ==============
 *  · Read-only V1 — edit profile + order detail page sono V2. La maggior
 *    parte dei merchant usa la portal solo come "storico ordini" quindi
 *    il MVP read-only e' sufficiente per Phase 1.
 *  · Token detection via ctx.client.tokenStorage.get() — no fetch network
 *    per stabilire lo stato. La me() call lazy-load solo quando il tab e'
 *    visibile.
 *  · Tab switching client-side (no router) — il merchant puo' linkare
 *    direttamente con attribute initial-tab="orders".
 *  · Logout pulisce il token + dispatcha afianco:portal-logout. Il merchant
 *    decide se redirect o se rimanere sulla pagina.
 *
 * Custom events
 *   - `afianco:portal-loaded` (detail: { profile, ordersCount }) — emesso
 *     dopo che profile + orders sono fetched con successo.
 *   - `afianco:portal-logout` (detail: { customer_id }) — emesso quando il
 *     customer clicca "Esci".
 *   - `afianco:auth-required` (detail: {}) — emesso quando il portal monta
 *     ma non c'e' token (customer non loggato). Il merchant deve mostrare
 *     <afianco-login> o redirect.
 *
 * Uso:
 *   <afianco-storefront-init slug="acme">
 *     <afianco-customer-portal initial-tab="profile"></afianco-customer-portal>
 *   </afianco-storefront-init>
 */

import { LitElement, html, css, type PropertyValues } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { consume } from '@lit/context';
import { afiancoBaseStyles } from '@afianco/design-tokens';
// Sprint 4 W4.7 — i18n wiring
import { t } from '../i18n/index.js';
import {
  AfiancoAuthError,
  type CustomerProfile,
  type CustomerOrderSummary,
} from '@afianco/api-client';
import {
  storefrontContext,
  STOREFRONT_INITIAL,
  type StorefrontContext,
} from '../context.js';

// Track E Step 2.4.8 — side-effect import per registrare i sub-component
// usati nelle tab "Corsi", "Download", "Prenotazioni".
import './afianco-my-courses.js';
import './afianco-course-player.js';
import './afianco-my-downloads.js';
import './afianco-my-bookings.js';
// Track E Step 4.4 — profile editor (edit profile + change password + GDPR erasure)
import './afianco-profile-editor.js';

type PortalTab =
  | 'profile'
  | 'orders'
  | 'courses'
  | 'downloads'
  | 'bookings';

@customElement('afianco-customer-portal')
export class AfiancoCustomerPortal extends LitElement {
  /** Titolo del portal — default "Area Personale". */
  @property({ type: String })
  title = 'Area Personale';

  /** Tab iniziale ("profile" | "orders"). Default "profile". */
  @property({ type: String, attribute: 'initial-tab' })
  initialTab: PortalTab = 'profile';

  /**
   * Mostra il pulsante "Esci" (default true). Alcuni merchant preferiscono
   * gestire il logout via header globale del proprio sito.
   */
  @property({ type: Boolean, attribute: 'show-logout' })
  showLogout = true;

  @consume({ context: storefrontContext, subscribe: true })
  @state()
  ctx: StorefrontContext = STOREFRONT_INITIAL;

  @state()
  private activeTab: PortalTab = 'profile';

  // Track E Step 2.4.8 — enrollment_id selezionato per il course-player.
  // Quando settato e tab=courses, sostituisce la grid <afianco-my-courses>
  // con il player <afianco-course-player>. Click "← Torna" la resetta.
  @state()
  private activeEnrollmentId: string | null = null;

  @state()
  private profile: CustomerProfile | null = null;

  @state()
  private orders: CustomerOrderSummary[] | null = null;

  @state()
  private loadingProfile = false;

  @state()
  private loadingOrders = false;

  @state()
  private profileError: string | null = null;

  @state()
  private ordersError: string | null = null;

  @state()
  private authRequired = false;

  /** One-shot guard — evita refetch loop dal updated() lifecycle. */
  private _started = false;

  // ── Styles ────────────────────────────────────────────────────────────

  static styles = [
    afiancoBaseStyles,
    css`
      :host {
        display: block;
        max-width: 720px;
        font-family: var(--afianco-font-family);
        color: var(--afianco-color-text-primary);
      }
      .card {
        background: var(--afianco-color-bg);
        border: 1px solid var(--afianco-color-border);
        border-radius: var(--afianco-radius-lg);
        box-shadow: var(--afianco-shadow-sm);
        overflow: hidden;
      }
      .header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: var(--afianco-spacing-lg) var(--afianco-spacing-xl);
        border-bottom: 1px solid var(--afianco-color-border);
      }
      .title {
        margin: 0;
        font-size: var(--afianco-font-size-xl);
        font-weight: var(--afianco-font-weight-bold);
      }
      .logout-btn {
        background: transparent;
        color: var(--afianco-color-text-secondary);
        border: 1px solid var(--afianco-color-border);
        border-radius: var(--afianco-radius-md);
        padding: var(--afianco-spacing-xs) var(--afianco-spacing-md);
        font-family: var(--afianco-font-family);
        font-size: var(--afianco-font-size-sm);
        cursor: pointer;
      }
      .logout-btn:hover {
        background: var(--afianco-color-surface);
      }
      /* ── Tabs: scroll orizzontale su mobile, distribuiti su desktop ── */
      .tabs {
        display: flex;
        border-bottom: 1px solid var(--afianco-color-border);
        background: var(--afianco-color-surface);
        overflow-x: auto;
        scrollbar-width: thin;
        gap: 2px;
      }
      .tab {
        flex: 0 0 auto;
        background: transparent;
        border: none;
        padding: 12px 16px;
        font-family: var(--afianco-font-family);
        font-size: 13px;
        font-weight: var(--afianco-font-weight-medium);
        color: var(--afianco-color-text-secondary);
        cursor: pointer;
        border-bottom: 3px solid transparent;
        transition: all var(--afianco-duration-fast) var(--afianco-easing-standard);
        display: inline-flex;
        align-items: center;
        gap: 6px;
        white-space: nowrap;
      }
      @media (min-width: 720px) {
        .tab { flex: 1 1 auto; justify-content: center; }
      }
      .tab:hover {
        color: var(--afianco-color-text-primary);
        background: var(--afianco-color-muted, #f9fafb);
      }
      .tab[aria-selected='true'] {
        color: var(--afianco-color-primary);
        border-bottom-color: var(--afianco-color-primary);
        background: var(--afianco-color-primary-soft, #eef2ff);
      }
      .content {
        padding: var(--afianco-spacing-xl);
        min-height: 200px;
      }
      .skeleton {
        background: var(--afianco-color-surface);
        border-radius: var(--afianco-radius-sm);
        height: 16px;
        margin-bottom: var(--afianco-spacing-sm);
        animation: pulse 1.4s ease-in-out infinite;
      }
      .skeleton.wide { width: 80%; }
      .skeleton.medium { width: 60%; }
      .skeleton.narrow { width: 40%; }
      @keyframes pulse {
        0%, 100% { opacity: 0.6; }
        50% { opacity: 1; }
      }
      .field-row {
        display: grid;
        grid-template-columns: 140px 1fr;
        gap: var(--afianco-spacing-md);
        padding: var(--afianco-spacing-sm) 0;
        border-bottom: 1px solid var(--afianco-color-border);
        font-size: var(--afianco-font-size-md);
      }
      .field-row:last-child { border-bottom: none; }
      .field-label {
        color: var(--afianco-color-text-secondary);
        font-weight: var(--afianco-font-weight-medium);
      }
      .field-value {
        color: var(--afianco-color-text-primary);
      }
      .badge {
        display: inline-block;
        padding: 2px var(--afianco-spacing-sm);
        border-radius: var(--afianco-radius-pill);
        font-size: var(--afianco-font-size-xs);
        font-weight: var(--afianco-font-weight-medium);
      }
      .badge.verified {
        background: #f0fdf4;
        color: var(--afianco-color-success);
      }
      .badge.unverified {
        background: #fef3c7;
        color: var(--afianco-color-warning);
      }
      .order-list {
        display: grid;
        gap: var(--afianco-spacing-md);
      }
      .order-card {
        display: grid;
        grid-template-columns: 1fr auto;
        gap: var(--afianco-spacing-md);
        padding: var(--afianco-spacing-md) var(--afianco-spacing-lg);
        border: 1px solid var(--afianco-color-border);
        border-radius: var(--afianco-radius-md);
        background: var(--afianco-color-bg);
      }
      .order-meta {
        display: flex;
        flex-direction: column;
        gap: 4px;
      }
      .order-number {
        font-weight: var(--afianco-font-weight-medium);
        font-size: var(--afianco-font-size-md);
      }
      .order-date {
        font-size: var(--afianco-font-size-sm);
        color: var(--afianco-color-text-muted);
      }
      .order-amount {
        text-align: right;
      }
      .order-total {
        font-weight: var(--afianco-font-weight-bold);
        font-size: var(--afianco-font-size-lg);
      }
      .status-badge {
        display: inline-block;
        padding: 2px var(--afianco-spacing-sm);
        border-radius: var(--afianco-radius-pill);
        font-size: var(--afianco-font-size-xs);
        text-transform: capitalize;
        margin-top: 4px;
      }
      .status-confirmed, .status-fulfilled, .status-completed {
        background: #f0fdf4;
        color: var(--afianco-color-success);
      }
      .status-draft, .status-pending {
        background: #fef3c7;
        color: var(--afianco-color-warning);
      }
      .status-cancelled, .status-refunded {
        background: #fff5f5;
        color: var(--afianco-color-danger);
      }
      .empty-state {
        text-align: center;
        padding: var(--afianco-spacing-xxl);
        color: var(--afianco-color-text-muted);
      }
      .error-banner {
        background: #fff5f5;
        border: 1px solid #fed7d7;
        color: var(--afianco-color-danger);
        padding: var(--afianco-spacing-sm) var(--afianco-spacing-md);
        border-radius: var(--afianco-radius-sm);
        font-size: var(--afianco-font-size-sm);
        margin-bottom: var(--afianco-spacing-md);
      }
      .auth-prompt {
        text-align: center;
        padding: var(--afianco-spacing-xxl);
      }
      .auth-prompt h3 {
        margin: 0 0 var(--afianco-spacing-md);
        font-size: var(--afianco-font-size-lg);
      }
      .auth-prompt p {
        color: var(--afianco-color-text-secondary);
        margin-bottom: var(--afianco-spacing-lg);
      }
      .auth-btn {
        background: var(--afianco-color-primary);
        color: var(--afianco-color-primary-text);
        border: none;
        border-radius: var(--afianco-radius-md);
        padding: var(--afianco-spacing-sm) var(--afianco-spacing-xl);
        font-family: var(--afianco-font-family);
        font-size: var(--afianco-font-size-md);
        font-weight: var(--afianco-font-weight-medium);
        cursor: pointer;
      }
    `,
  ];

  // ── Lifecycle ─────────────────────────────────────────────────────────

  connectedCallback(): void {
    super.connectedCallback();
    this.activeTab = this.initialTab;
  }

  protected updated(_changed: PropertyValues): void {
    if (this._started) return;
    if (this.ctx.status !== 'ready' || !this.ctx.client) return;
    this._started = true;
    void this.bootstrap();
  }

  // ── Public API ────────────────────────────────────────────────────────

  /**
   * Bootstrap: rileva auth state. Se manca il token → auth-required event
   * + render prompt login. Se presente → fetch profile (e orders se il tab
   * attivo e' 'orders' al mount).
   */
  async bootstrap(): Promise<void> {
    if (!this.ctx.client) return;
    const token = this.ctx.client.tokenStorage.get();
    if (!token) {
      this.authRequired = true;
      this.dispatchEvent(
        new CustomEvent('afianco:auth-required', {
          detail: {},
          bubbles: true,
          composed: true,
        }),
      );
      return;
    }
    await this.fetchProfile();
    if (this.activeTab === 'orders') {
      await this.fetchOrders();
    }
  }

  /** Fetch /api/customer/me. */
  async fetchProfile(): Promise<void> {
    if (!this.ctx.client || this.loadingProfile) return;
    this.loadingProfile = true;
    this.profileError = null;
    try {
      this.profile = await this.ctx.client.customer.me();
      this.maybeDispatchLoaded();
    } catch (e) {
      if (e instanceof AfiancoAuthError) {
        // Token scaduto / invalid → forza re-auth
        this.ctx.client.customerAuth.logout();
        this.authRequired = true;
        this.dispatchEvent(
          new CustomEvent('afianco:auth-required', {
            detail: {},
            bubbles: true,
            composed: true,
          }),
        );
      } else {
        this.profileError =
          (e as Error)?.message ?? t('portal.error_load_profile');
      }
    } finally {
      this.loadingProfile = false;
    }
  }

  /** Fetch /api/customer/orders. */
  async fetchOrders(): Promise<void> {
    if (!this.ctx.client || this.loadingOrders) return;
    this.loadingOrders = true;
    this.ordersError = null;
    try {
      this.orders = await this.ctx.client.customer.orders();
      this.maybeDispatchLoaded();
    } catch (e) {
      if (e instanceof AfiancoAuthError) {
        this.ctx.client.customerAuth.logout();
        this.authRequired = true;
      } else {
        this.ordersError =
          (e as Error)?.message ?? t('portal.error_load_orders');
      }
    } finally {
      this.loadingOrders = false;
    }
  }

  /** Switch tab. Lazy-fetch orders se richiesto la prima volta. */
  selectTab(tab: PortalTab): void {
    if (this.activeTab === tab) return;
    this.activeTab = tab;
    if (tab === 'orders' && this.orders === null && !this.loadingOrders) {
      void this.fetchOrders();
    }
  }

  /** Logout: drop token, reset state, dispatch event. */
  logout(): void {
    if (!this.ctx.client) return;
    const customerId = this.profile?.id ?? null;
    this.ctx.client.customerAuth.logout();
    this.profile = null;
    this.orders = null;
    this.authRequired = true;
    this.dispatchEvent(
      new CustomEvent<{ customer_id: string | null }>('afianco:portal-logout', {
        detail: { customer_id: customerId },
        bubbles: true,
        composed: true,
      }),
    );
  }

  // ── Internal helpers ──────────────────────────────────────────────────

  private maybeDispatchLoaded(): void {
    // Emette afianco:portal-loaded solo quando entrambi profile+orders sono
    // arrivati (o solo profile se siamo nel tab profile e orders e' lazy).
    if (this.profile && (this.activeTab !== 'orders' || this.orders)) {
      this.dispatchEvent(
        new CustomEvent<{
          profile: CustomerProfile;
          ordersCount: number | null;
        }>('afianco:portal-loaded', {
          detail: {
            profile: this.profile,
            ordersCount: this.orders?.length ?? null,
          },
          bubbles: true,
          composed: true,
        }),
      );
    }
  }

  private formatDate(iso: string): string {
    try {
      const d = new Date(iso);
      return d.toLocaleDateString('it-IT', {
        day: '2-digit',
        month: 'short',
        year: 'numeric',
      });
    } catch {
      return iso;
    }
  }

  private formatMoney(amount: number, currency: string): string {
    try {
      return new Intl.NumberFormat('it-IT', {
        style: 'currency',
        currency,
      }).format(amount);
    } catch {
      return `${amount.toFixed(2)} ${currency}`;
    }
  }

  // ── Render ────────────────────────────────────────────────────────────

  render() {
    if (this.authRequired) {
      return html`
        <div class="card">
          <div class="auth-prompt">
            <h3>${t('portal.auth_required_title')}</h3>
            <p>${t('portal.auth_required_desc')}</p>
            <button
              class="auth-btn"
              type="button"
              @click=${this.handleAuthCtaClick}>
              ${t('header.account_login')}
            </button>
          </div>
        </div>
      `;
    }

    // Track E Step 2.4.8 — definizione delle tab in ordine di display
    // Sprint 4 W4.7 — labels via t() (parity 4 lingue)
    const tabs: Array<{ id: PortalTab; label: string; icon: string }> = [
      { id: 'profile',   label: t('portal.tab_profile'),   icon: '👤' },
      { id: 'orders',    label: t('portal.tab_orders'),    icon: '🧾' },
      { id: 'courses',   label: t('portal.tab_courses'),   icon: '📚' },
      { id: 'downloads', label: t('portal.tab_downloads'), icon: '📥' },
      { id: 'bookings',  label: t('portal.tab_bookings'),  icon: '📅' },
    ];

    return html`
      <div class="card">
        <div class="header">
          <h2 class="title">${this.title}</h2>
          ${this.showLogout && this.profile
            ? html`<button
                class="logout-btn"
                type="button"
                @click=${this.logout}>
                Esci
              </button>`
            : ''}
        </div>
        <div class="tabs" role="tablist">
          ${tabs.map((t) => html`
            <button
              class="tab"
              role="tab"
              type="button"
              aria-selected=${this.activeTab === t.id ? 'true' : 'false'}
              @click=${() => this.selectTab(t.id)}>
              <span aria-hidden="true">${t.icon}</span>
              <span>${t.label}</span>
            </button>
          `)}
        </div>
        <div class="content">
          ${this.renderActiveTab()}
        </div>
      </div>
    `;
  }

  /**
   * Track E Step 2.4.8 — dispatch della tab attiva. Ogni tab e' un
   * sub-component standalone che fa fetch internamente (lazy load).
   */
  private renderActiveTab() {
    switch (this.activeTab) {
      case 'profile':
        // Track E Step 4.4 — Profile editable (was read-only).
        // <afianco-profile-editor> gestisce profile edit + password change +
        // GDPR erasure in accordion compatto.
        return html`<afianco-profile-editor></afianco-profile-editor>`;
      case 'orders':
        return this.renderOrdersTab();
      case 'courses':
        return this.renderCoursesTab();
      case 'downloads':
        return html`<afianco-my-downloads></afianco-my-downloads>`;
      case 'bookings':
        return html`<afianco-my-bookings></afianco-my-bookings>`;
      default:
        return html`<afianco-profile-editor></afianco-profile-editor>`;
    }
  }

  /**
   * Track E Step 2.4.8 — tab "I miei corsi" gestisce 2 view:
   *   1. Grid <afianco-my-courses> (default, listing)
   *   2. Player <afianco-course-player> quando user clicca un corso
   * La scelta e' tracked da this.activeEnrollmentId.
   */
  private renderCoursesTab() {
    if (this.activeEnrollmentId) {
      return html`
        <afianco-course-player
          enrollment-id=${this.activeEnrollmentId}
          @afianco:course-back=${() => { this.activeEnrollmentId = null; }}>
        </afianco-course-player>
      `;
    }
    return html`
      <afianco-my-courses
        @afianco:course-selected=${(e: CustomEvent) => {
          this.activeEnrollmentId = e.detail?.enrollment_id ?? null;
        }}>
      </afianco-my-courses>
    `;
  }

  // Track E Step 4.4 — Sostituita da <afianco-profile-editor>. Keep here
  // come read-only fallback (es. merchant opt-out via attribute future).
  // Underscore prefix indica unused-on-purpose per evitare TS6133.
  // @ts-expect-error keep for future fallback usage
  private _renderProfileTabReadOnly() {
    if (this.loadingProfile && !this.profile) {
      return html`
        <div class="skeleton wide"></div>
        <div class="skeleton medium"></div>
        <div class="skeleton narrow"></div>
      `;
    }
    if (this.profileError) {
      return html`<div class="error-banner" role="alert">
        ${this.profileError}
      </div>`;
    }
    if (!this.profile) {
      return html`<div class="empty-state">${t('portal.empty_profile')}</div>`;
    }
    const p = this.profile;
    return html`
      <div class="field-row">
        <div class="field-label">Nome</div>
        <div class="field-value">${p.name}</div>
      </div>
      <div class="field-row">
        <div class="field-label">Email</div>
        <div class="field-value">
          ${p.email}
          ${p.email_verified
            ? html`<span class="badge verified">verificata</span>`
            : html`<span class="badge unverified">non verificata</span>`}
        </div>
      </div>
      ${p.phone
        ? html`<div class="field-row">
            <div class="field-label">Telefono</div>
            <div class="field-value">${p.phone}</div>
          </div>`
        : ''}
      <div class="field-row">
        <div class="field-label">Lingua</div>
        <div class="field-value">${p.locale}</div>
      </div>
      <div class="field-row">
        <div class="field-label">Iscritto dal</div>
        <div class="field-value">${this.formatDate(p.created_at)}</div>
      </div>
      ${p.accepted_marketing !== undefined
        ? html`<div class="field-row">
            <div class="field-label">Marketing</div>
            <div class="field-value">
              ${p.accepted_marketing ? 'Iscritto' : 'Non iscritto'}
            </div>
          </div>`
        : ''}
    `;
  }

  private renderOrdersTab() {
    if (this.loadingOrders && !this.orders) {
      return html`
        <div class="skeleton wide"></div>
        <div class="skeleton wide"></div>
        <div class="skeleton wide"></div>
      `;
    }
    if (this.ordersError) {
      return html`<div class="error-banner" role="alert">
        ${this.ordersError}
      </div>`;
    }
    if (!this.orders || this.orders.length === 0) {
      return html`<div class="empty-state">
        Non hai ancora effettuato ordini.
      </div>`;
    }
    // Track E Step 4.4 — Receipt URL helper (requires customer auth at fetch time;
    // browser navigates with current session cookies + Bearer impossible
    // su navigation diretta. Workaround: usiamo l'access_token JWT come
    // query param se servisse, ma backend usa cookies + JWT header. Per
    // ora apriamo URL in nuova tab — il customer puo' restare loggato).
    const receiptUrl = (orderId: string): string =>
      this.ctx?.client?.customer?.orderReceiptUrl?.(orderId) ?? '#';

    return html`
      <div class="order-list">
        ${this.orders.map(
          (o) => html`
            <div class="order-card">
              <div class="order-meta">
                <div class="order-number">
                  Ordine ${o.order_number ?? `#${o.id.slice(0, 8)}`}
                </div>
                <div class="order-date">${this.formatDate(o.created_at)}</div>
                <span class="status-badge status-${o.order_status}">
                  ${o.order_status}
                </span>
              </div>
              <div class="order-amount">
                <div class="order-total">
                  ${this.formatMoney(o.total, o.currency)}
                </div>
                <!-- Track E Step 4.4 — Scarica ricevuta PDF -->
                <a
                  href=${receiptUrl(o.id)}
                  target="_blank"
                  rel="noopener noreferrer"
                  title="Scarica ricevuta PDF"
                  style="display:inline-flex; align-items:center; gap:4px;
                         margin-top:6px; font-size:11px;
                         color: var(--afianco-color-primary, #4b72ce);
                         text-decoration: none; font-weight: 600;">
                  <span aria-hidden="true">📄</span> Scarica ricevuta
                </a>
              </div>
            </div>
          `,
        )}
      </div>
    `;
  }

  private handleAuthCtaClick(): void {
    // Dispatcha il auth-action — il merchant decide come gestirlo
    // (mostra <afianco-login> o redirect a /accedi).
    this.dispatchEvent(
      new CustomEvent('afianco:auth-action', {
        detail: { action: 'show-login' },
        bubbles: true,
        composed: true,
      }),
    );
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'afianco-customer-portal': AfiancoCustomerPortal;
  }
  interface HTMLElementEventMap {
    'afianco:portal-loaded': CustomEvent<{
      profile: CustomerProfile;
      ordersCount: number | null;
    }>;
    'afianco:portal-logout': CustomEvent<{ customer_id: string | null }>;
    'afianco:auth-required': CustomEvent<Record<string, never>>;
  }
}
