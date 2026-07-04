/**
 * Sentinel tests for <afianco-test-card> — Phase 0 Step 11.
 *
 * Verifica la pipeline Vite + TS + Lit + happy-dom:
 *   - Custom element registrato correttamente
 *   - Attributi reattivi (re-render on attribute change)
 *   - Default messages quando store/message mancano
 *   - Shadow DOM presente (CSS isolation)
 */

import { describe, it, expect, beforeAll } from 'vitest';

// Importa il componente — il side-effect lo registra nel customElements registry.
import { AfiancoTestCard } from '../src/components/afianco-test-card';

describe('<afianco-test-card>', () => {
  beforeAll(() => {
    // happy-dom registra automaticamente customElements, ma il side-effect
    // dell'import dovrebbe già essere completato.
  });

  it('is registered in customElements', () => {
    const ctor = customElements.get('afianco-test-card');
    expect(ctor).toBeDefined();
    expect(ctor).toBe(AfiancoTestCard);
  });

  it('creates an instance via document.createElement', () => {
    const el = document.createElement('afianco-test-card');
    expect(el).toBeInstanceOf(AfiancoTestCard);
  });

  it('uses Shadow DOM for style isolation', async () => {
    const el = document.createElement('afianco-test-card') as AfiancoTestCard;
    document.body.appendChild(el);
    // Lit renders asynchronously
    await el.updateComplete;
    expect(el.shadowRoot).not.toBeNull();
    document.body.removeChild(el);
  });

  it('renders default message when message attribute is absent', async () => {
    const el = document.createElement('afianco-test-card') as AfiancoTestCard;
    el.setAttribute('store', 'acme');
    document.body.appendChild(el);
    await el.updateComplete;
    const text = el.shadowRoot?.textContent ?? '';
    expect(text).toContain('Afianco embed SDK is loaded correctly');
    expect(text).toContain('acme');
    document.body.removeChild(el);
  });

  it('renders the custom message attribute when provided', async () => {
    const el = document.createElement('afianco-test-card') as AfiancoTestCard;
    el.setAttribute('store', 'acme');
    el.setAttribute('message', 'Hello world from custom merchant.');
    document.body.appendChild(el);
    await el.updateComplete;
    const text = el.shadowRoot?.textContent ?? '';
    expect(text).toContain('Hello world from custom merchant');
    document.body.removeChild(el);
  });

  it('renders a warning when store attribute is missing', async () => {
    const el = document.createElement('afianco-test-card') as AfiancoTestCard;
    document.body.appendChild(el);
    await el.updateComplete;
    const text = el.shadowRoot?.textContent ?? '';
    expect(text).toMatch(/Missing required attribute/i);
    document.body.removeChild(el);
  });

  it('reactively re-renders when store attribute changes', async () => {
    const el = document.createElement('afianco-test-card') as AfiancoTestCard;
    el.setAttribute('store', 'first-store');
    document.body.appendChild(el);
    await el.updateComplete;
    expect(el.shadowRoot?.textContent).toContain('first-store');

    el.setAttribute('store', 'second-store');
    await el.updateComplete;
    expect(el.shadowRoot?.textContent).toContain('second-store');
    expect(el.shadowRoot?.textContent).not.toContain('first-store');
    document.body.removeChild(el);
  });
});
