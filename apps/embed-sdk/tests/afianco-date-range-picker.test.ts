/**
 * Sentinel tests for <afianco-date-range-picker> — R3 (rental embed parity).
 *
 * Le assert sono sul CONTRATTO EVENTI (ciò che il parent product-detail
 * ascolta), non sul DOM interno: il parent reagisce a
 * `afianco:date-range-selected`, mai al div d'errore. Questo rende i test
 * indipendenti dal rendering dello shadow DOM (happy-dom non riflette in
 * modo affidabile i cambi di @state da event handler).
 *
 * NB: gli eventi sono bubbles+composed e happy-dom condivide il document tra
 * test, quindi le spy contano SOLO gli eventi il cui target è il proprio
 * elemento (evita bleed cross-test).
 *
 * Invariants pinned
 * =================
 *  INV-DRP-1  Registered in customElements
 *  INV-DRP-2  Range valido senza blockedDates → emette date-range-selected
 *  INV-DRP-3  Stesso range con una data occupata DENTRO → NESSUN selected
 *  INV-DRP-4  Range adiacente ma NON sovrapposto a blockedDates → selected OK
 *  INV-DRP-5  blockedDates default [] → nessun falso blocco
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { AfiancoDateRangePicker } from '../src/components/afianco-date-range-picker.js';

function mount(): AfiancoDateRangePicker {
  const el = document.createElement('afianco-date-range-picker') as AfiancoDateRangePicker;
  document.body.appendChild(el);
  return el;
}

/** Spy che conta solo gli eventi originati dall'elemento `el` (no bleed). */
function selectedSpyFor(el: AfiancoDateRangePicker): ReturnType<typeof vi.fn> {
  const spy = vi.fn();
  el.addEventListener('afianco:date-range-selected', (e: Event) => {
    if (e.target === el) spy(e);
  });
  return spy;
}

async function setRange(el: AfiancoDateRangePicker, from: string, to: string): Promise<void> {
  await el.updateComplete;
  const root = el.shadowRoot!;
  const fromInput = root.querySelector<HTMLInputElement>('#rental-date-from')!;
  const toInput = root.querySelector<HTMLInputElement>('#rental-date-to')!;
  fromInput.value = from;
  fromInput.dispatchEvent(new Event('input'));
  toInput.value = to;
  toInput.dispatchEvent(new Event('input'));
  await el.updateComplete;
}

describe('<afianco-date-range-picker> — R3 blocked dates', () => {
  let el: AfiancoDateRangePicker;

  beforeEach(() => {
    el = mount();
  });

  afterEach(() => {
    el.remove();
  });

  it('INV-DRP-1 — registered in customElements', () => {
    expect(customElements.get('afianco-date-range-picker')).toBe(AfiancoDateRangePicker);
  });

  it('INV-DRP-2 — range valido senza blockedDates emette date-range-selected', async () => {
    const selected = selectedSpyFor(el);
    await setRange(el, '2099-01-10', '2099-01-12');
    expect(selected).toHaveBeenCalledTimes(1);
    expect(selected.mock.calls[0][0].detail).toMatchObject({
      from: '2099-01-10',
      to: '2099-01-12',
      days: 3,
    });
  });

  it('INV-DRP-3 — stesso range con data occupata dentro → NO selected', async () => {
    el.blockedDates = ['2099-01-11'];
    await el.updateComplete;
    const selected = selectedSpyFor(el);
    await setRange(el, '2099-01-10', '2099-01-12');
    // Range completo ma non disponibile: niente conferma al parent.
    expect(selected).not.toHaveBeenCalled();
  });

  it('INV-DRP-4 — range adiacente ma non sovrapposto → selected OK', async () => {
    el.blockedDates = ['2099-01-09', '2099-01-13'];
    await el.updateComplete;
    const selected = selectedSpyFor(el);
    await setRange(el, '2099-01-10', '2099-01-12');
    expect(selected).toHaveBeenCalledTimes(1);
  });

  it('INV-DRP-5 — blockedDates default [] non blocca nulla', async () => {
    expect(el.blockedDates).toEqual([]);
    const selected = selectedSpyFor(el);
    await setRange(el, '2099-02-01', '2099-02-05');
    expect(selected).toHaveBeenCalledTimes(1);
  });
});
