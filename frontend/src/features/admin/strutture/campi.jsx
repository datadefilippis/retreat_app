/**
 * I campi della scheda struttura (SR, fase 0): pochi pezzi, usati ovunque.
 * Etichetta in italiano + esempio, tap da pollice, niente modali.
 */
import React from 'react';

export const cls = {
  input: 'w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring',
  label: 'block text-xs font-medium text-muted-foreground mb-1',
  riga: 'grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3',
};

export function Campo({ label, hint, children, wide }) {
  return (
    <label className={`block ${wide ? 'sm:col-span-2 lg:col-span-3' : ''}`}>
      <span className={cls.label}>{label}{hint && <span className="font-normal"> · {hint}</span>}</span>
      {children}
    </label>
  );
}

export function Testo({ value, onChange, placeholder, type = 'text', ...rest }) {
  return (
    <input type={type} value={value ?? ''} placeholder={placeholder}
           onChange={(e) => onChange(e.target.value === '' ? null : (type === 'number' ? Number(e.target.value) : e.target.value))}
           className={cls.input} {...rest} />
  );
}

export function Area({ value, onChange, placeholder, rows = 3 }) {
  return (
    <textarea rows={rows} value={value ?? ''} placeholder={placeholder}
              onChange={(e) => onChange(e.target.value || null)} className={cls.input} />
  );
}

export function Tendina({ value, onChange, opzioni, vuoto = '—' }) {
  return (
    <select value={value ?? ''} onChange={(e) => onChange(e.target.value || null)} className={cls.input}>
      <option value="">{vuoto}</option>
      {(opzioni || []).map((o) => (
        <option key={o.valore ?? o} value={o.valore ?? o}>{o.etichetta ?? o}</option>
      ))}
    </select>
  );
}

export function SiNo({ value, onChange, label }) {
  const stato = value === true ? 'si' : value === false ? 'no' : '';
  return (
    <label className="block">
      <span className={cls.label}>{label}</span>
      <div className="flex gap-1">
        {[['si', 'Sì'], ['no', 'No'], ['', '?']].map(([v, t]) => (
          <button key={v} type="button" onClick={() => onChange(v === '' ? null : v === 'si')}
                  className={`min-h-[40px] flex-1 rounded-md border text-sm ${stato === v ? 'bg-primary text-white border-primary' : 'border-input bg-background'}`}>
            {t}
          </button>
        ))}
      </div>
    </label>
  );
}

export function Chip({ value = [], onChange, opzioni }) {
  const toggle = (v) => onChange(value.includes(v) ? value.filter((x) => x !== v) : [...value, v]);
  return (
    <div className="flex flex-wrap gap-1.5">
      {(opzioni || []).map((o) => (
        <button key={o.valore} type="button" onClick={() => toggle(o.valore)}
                className={`min-h-[36px] rounded-full border px-3 text-xs ${value.includes(o.valore) ? 'bg-primary text-white border-primary' : 'border-input bg-background text-foreground'}`}>
          {o.etichetta}
        </button>
      ))}
    </div>
  );
}

/** Righe ripetibili (camere, sale, stagioni…): aggiungi, duplica, togli. */
export function Righe({ righe = [], onChange, vuota, render, nomeRiga = 'riga' }) {
  const set = (i, patch) => onChange(righe.map((r, j) => (j === i ? { ...r, ...patch } : r)));
  const via = (i) => onChange(righe.filter((_, j) => j !== i));
  const duplica = (i) => onChange([...righe.slice(0, i + 1), { ...righe[i] }, ...righe.slice(i + 1)]);
  return (
    <div className="space-y-3">
      {righe.map((r, i) => (
        <div key={i} className="rounded-lg border border-border bg-muted/30 p-3">
          {render(r, (patch) => set(i, patch), i)}
          <div className="mt-2 flex gap-2 text-xs">
            <button type="button" onClick={() => duplica(i)} className="rounded-full border border-border px-3 py-1">Duplica</button>
            <button type="button" onClick={() => via(i)} className="rounded-full border border-red-300 text-red-700 px-3 py-1">Togli</button>
          </div>
        </div>
      ))}
      <button type="button" onClick={() => onChange([...righe, { ...vuota }])}
              className="min-h-[40px] rounded-full border border-dashed border-primary px-4 text-sm text-primary">
        + Aggiungi {nomeRiga}
      </button>
    </div>
  );
}
