/**
 * Sentinel tests for <afianco-custom-request> — R4 (service custom request).
 *
 * Assert sul CONTRATTO EVENTI (`afianco:custom-request-changed`): è ciò che il
 * parent product-detail consuma per decidere se marcare l'order-item con
 * service_custom_request + booking_date/start/end. Indipendente dal DOM
 * interno (happy-dom non riflette in modo affidabile i cambi di @state da
 * event handler — vedi nota in afianco-date-range-picker.test.ts).
 *
 * Le spy contano SOLO eventi originati dal proprio elemento (no bleed
 * cross-test: gli eventi sono bubbles+composed e il document è condiviso).
 *
 * INV-CR-1  Registered in customElements
 * INV-CR-2  Solo data (parziale) → emette complete=false
 * INV-CR-3  data+inizio+fine validi → emette complete=true col payload
 * INV-CR-4  fine <= inizio → complete=false (range invalido)
 * INV-CR-5  note incluse nel payload
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { AfiancoCustomRequest } from '../src/components/afianco-custom-request.js';
import type { CustomRequestDetail } from '../src/components/afianco-custom-request.js';

function mount(): AfiancoCustomRequest {
  const el = document.createElement('afianco-custom-request') as AfiancoCustomRequest;
  document.body.appendChild(el);
  return el;
}

function changedSpyFor(el: AfiancoCustomRequest): ReturnType<typeof vi.fn> {
  const spy = vi.fn();
  el.addEventListener('afianco:custom-request-changed', (e: Event) => {
    if (e.target === el) spy(e as CustomEvent<CustomRequestDetail>);
  });
  return spy;
}

async function setField(
  el: AfiancoCustomRequest,
  id: string,
  value: string,
): Promise<void> {
  await el.updateComplete;
  const input = el.shadowRoot!.querySelector<HTMLInputElement>(`#${id}`)!;
  input.value = value;
  input.dispatchEvent(new Event('input'));
  await el.updateComplete;
}

function lastDetail(spy: ReturnType<typeof vi.fn>): CustomRequestDetail {
  return spy.mock.calls[spy.mock.calls.length - 1][0].detail as CustomRequestDetail;
}

describe('<afianco-custom-request> — R4', () => {
  let el: AfiancoCustomRequest;

  beforeEach(() => {
    el = mount();
  });

  afterEach(() => {
    el.remove();
  });

  it('INV-CR-1 — registered in customElements', () => {
    expect(customElements.get('afianco-custom-request')).toBe(AfiancoCustomRequest);
  });

  it('INV-CR-2 — solo data → complete=false', async () => {
    const changed = changedSpyFor(el);
    await setField(el, 'cr-date', '2099-06-01');
    expect(changed).toHaveBeenCalled();
    expect(lastDetail(changed).complete).toBe(false);
  });

  it('INV-CR-3 — data+inizio+fine validi → complete=true col payload', async () => {
    const changed = changedSpyFor(el);
    await setField(el, 'cr-date', '2099-06-01');
    await setField(el, 'cr-start', '10:00');
    await setField(el, 'cr-end', '11:00');
    const d = lastDetail(changed);
    expect(d).toMatchObject({
      date: '2099-06-01',
      start: '10:00',
      end: '11:00',
      complete: true,
    });
  });

  it('INV-CR-4 — fine <= inizio → complete=false', async () => {
    const changed = changedSpyFor(el);
    await setField(el, 'cr-date', '2099-06-01');
    await setField(el, 'cr-start', '11:00');
    await setField(el, 'cr-end', '10:00');
    expect(lastDetail(changed).complete).toBe(false);
  });

  it('INV-CR-5 — note incluse nel payload', async () => {
    const changed = changedSpyFor(el);
    await setField(el, 'cr-date', '2099-06-01');
    await setField(el, 'cr-start', '10:00');
    await setField(el, 'cr-end', '12:00');
    await setField(el, 'cr-notes', 'Preferirei il pomeriggio');
    const d = lastDetail(changed);
    expect(d.complete).toBe(true);
    expect(d.notes).toBe('Preferirei il pomeriggio');
  });
});
