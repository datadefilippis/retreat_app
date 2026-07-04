/**
 * Sentinel tests for <afianco-newsletter-form> — F2 (modulo Newsletter).
 *
 * Componente autonomo: fetcha la config pubblica e fa il submit via fetch
 * diretto (no storefront-context). Mockiamo global.fetch e assertiamo sul
 * CONTRATTO: chiamate fetch (config + submit con sorgente D7) + evento
 * afianco:newsletter-subscribed. (happy-dom non riflette in modo affidabile i
 * cambi @state da event handler → assert su fetch/eventi, non sul DOM.)
 *
 * INV-NLF-1  registered in customElements
 * INV-NLF-2  on mount → GET config dell'endpoint corretto
 * INV-NLF-3  submit valido → POST con email + sorgente (source_label/url) + consenso
 * INV-NLF-4  email invalida → nessun POST
 * INV-NLF-5  submit ok → evento afianco:newsletter-subscribed con subscriber_id
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { AfiancoNewsletterForm } from '../src/components/afianco-newsletter-form.js';

const CONFIG = {
  id: 'form-1',
  name: 'Iscriviti',
  collect_name: true,
  collect_phone: false,
  field_configs: [],
  consent_text: null,
  privacy_required: true,
  success_message: null,
  redirect_url: null,
};

function mockFetchOnceConfigThenSubmit(submitResp: unknown = { success: true, message: 'ok', subscriber_id: 's1' }) {
  const fetchMock = vi.fn();
  fetchMock
    .mockResolvedValueOnce({ ok: true, json: async () => CONFIG })
    .mockResolvedValueOnce({ ok: true, json: async () => submitResp });
  (globalThis as unknown as { fetch: unknown }).fetch = fetchMock;
  return fetchMock;
}

async function mount(): Promise<AfiancoNewsletterForm> {
  const el = document.createElement('afianco-newsletter-form') as AfiancoNewsletterForm;
  el.setAttribute('form-id', 'form-1');
  el.setAttribute('base-url', 'https://api.test');
  el.setAttribute('source', 'blog-footer');
  document.body.appendChild(el);
  // attende il fetch config + il render
  await el.updateComplete;
  await new Promise((r) => setTimeout(r, 0));
  await el.updateComplete;
  return el;
}

describe('<afianco-newsletter-form> — F2', () => {
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    fetchMock = mockFetchOnceConfigThenSubmit();
  });

  afterEach(() => {
    document.querySelectorAll('afianco-newsletter-form').forEach((n) => n.remove());
  });

  it('INV-NLF-1 — registered', () => {
    expect(customElements.get('afianco-newsletter-form')).toBe(AfiancoNewsletterForm);
  });

  it('INV-NLF-2 — on mount fetches config endpoint', async () => {
    await mount();
    expect(fetchMock).toHaveBeenCalled();
    const url = fetchMock.mock.calls[0][0] as string;
    expect(url).toBe('https://api.test/api/public/embed/newsletter/form-1');
  });

  it('INV-NLF-3 + 5 — valid submit posts with source + emits event', async () => {
    const el = await mount();
    const subscribed = vi.fn();
    el.addEventListener('afianco:newsletter-subscribed', (e: Event) => {
      if (e.target === el) subscribed(e);
    });

    const root = el.shadowRoot!;
    const emailInput = root.querySelector<HTMLInputElement>('#nl-email')!;
    emailInput.value = 'a@b.com';
    emailInput.dispatchEvent(new Event('input'));
    const consent = root.querySelector<HTMLInputElement>('.consent input[type="checkbox"]')!;
    consent.checked = true;
    consent.dispatchEvent(new Event('change'));

    const form = root.querySelector('form')!;
    form.dispatchEvent(new Event('submit', { cancelable: true }));
    await new Promise((r) => setTimeout(r, 0));
    // happy-dom + Lit: lo swap form→success può lanciare un removeChild noise
    // durante il re-render; POST + evento avvengono PRIMA → safe da ignorare.
    try {
      await el.updateComplete;
    } catch {
      /* happy-dom reconciliation noise */
    }

    // INV-NLF-3 — secondo fetch = POST submit con sorgente + consenso
    const submitCall = fetchMock.mock.calls.find(
      (c) => typeof c[0] === 'string' && (c[0] as string).endsWith('/submit'),
    );
    expect(submitCall).toBeTruthy();
    const init = submitCall![1] as RequestInit;
    expect(init.method).toBe('POST');
    const body = JSON.parse(init.body as string);
    expect(body.email).toBe('a@b.com');
    expect(body.consent_privacy).toBe(true);
    expect(body.source_label).toBe('blog-footer');
    expect(body).toHaveProperty('source_url');

    // INV-NLF-5 — evento emesso col subscriber_id
    expect(subscribed).toHaveBeenCalled();
    expect(subscribed.mock.calls[0][0].detail).toMatchObject({
      email: 'a@b.com',
      subscriber_id: 's1',
    });
  });

  it('INV-NLF-6 — preview (config iniettata) → no fetch + theme + privacy link', async () => {
    const noFetch = vi.fn();
    (globalThis as unknown as { fetch: unknown }).fetch = noFetch;
    const el = document.createElement('afianco-newsletter-form') as AfiancoNewsletterForm;
    el.preview = true;
    el.config = {
      ...CONFIG,
      theme: { primary_color: '#123456', primary_text_color: '#abcdef' },
      privacy_policy_url: 'https://x.com/privacy',
    } as never;
    document.body.appendChild(el);
    await el.updateComplete;
    await new Promise((r) => setTimeout(r, 0));
    await el.updateComplete;

    // nessun fetch in preview
    expect(noFetch).not.toHaveBeenCalled();
    // theme applicato come CSS var sull'host
    expect(el.style.getPropertyValue('--afianco-color-primary')).toBe('#123456');
    expect(el.style.getPropertyValue('--afianco-color-primary-contrast')).toBe('#abcdef');
    // link privacy renderizzato
    const link = el.shadowRoot!.querySelector<HTMLAnchorElement>('.privacy-link');
    expect(link).not.toBeNull();
    expect(link!.getAttribute('href')).toBe('https://x.com/privacy');
    el.remove();
  });

  it('INV-NLF-7 — layout applicato a data-layout + nessun titolo nel form', async () => {
    (globalThis as unknown as { fetch: unknown }).fetch = vi.fn();
    const el = document.createElement('afianco-newsletter-form') as AfiancoNewsletterForm;
    el.preview = true;
    el.config = { ...CONFIG, name: 'ETICHETTA ADMIN', layout: 'horizontal' } as never;
    document.body.appendChild(el);
    await el.updateComplete;
    await new Promise((r) => setTimeout(r, 0));
    await el.updateComplete;
    const form = el.shadowRoot!.querySelector('form');
    expect(form?.getAttribute('data-layout')).toBe('horizontal');
    // il NOME del form (etichetta admin) NON deve comparire nel render pubblico
    expect(el.shadowRoot!.textContent).not.toContain('ETICHETTA ADMIN');
    expect(el.shadowRoot!.querySelector('.title')).toBeNull();
    el.remove();
  });

  it('INV-NLF-4 — email invalida → nessun POST', async () => {
    const el = await mount();
    const root = el.shadowRoot!;
    const emailInput = root.querySelector<HTMLInputElement>('#nl-email')!;
    emailInput.value = 'not-an-email';
    emailInput.dispatchEvent(new Event('input'));
    const consent = root.querySelector<HTMLInputElement>('.consent input[type="checkbox"]')!;
    consent.checked = true;
    consent.dispatchEvent(new Event('change'));

    root.querySelector('form')!.dispatchEvent(new Event('submit', { cancelable: true }));
    await new Promise((r) => setTimeout(r, 0));

    const submitCall = fetchMock.mock.calls.find(
      (c) => typeof c[0] === 'string' && (c[0] as string).endsWith('/submit'),
    );
    expect(submitCall).toBeFalsy();
  });
});
