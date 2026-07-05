/**
 * MultiLangText — traduzioni manuali nel wizard (6/7/2026).
 *
 * Design snello (decisione founder): sotto il campo italiano, una riga
 * di pill [+ English] [+ Deutsch] [+ Français]. Un tap apre la textarea
 * per quella lingua; la (×) la rimuove. Le lingue compilate sono le
 * lingue che l'operatore ACCETTA: il prodotto appare nelle viste in
 * quella lingua. Zero lingue = solo italiano, zero pensieri.
 */
import React from 'react';
import { useTranslation } from 'react-i18next';

const LANGS = [
  { code: 'en', label: 'English', flag: '🇬🇧' },
  { code: 'de', label: 'Deutsch', flag: '🇩🇪' },
  { code: 'fr', label: 'Français', flag: '🇫🇷' },
];

/**
 * value: {en: "...", de: "..."} (solo il campo corrente)
 * onChange(next): nuovo dict
 */
export default function MultiLangText({ value = {}, onChange, rows = 3, maxLength = 2000, fieldLabel }) {
  const { t } = useTranslation('products');
  const active = LANGS.filter(l => value[l.code] !== undefined);
  const inactive = LANGS.filter(l => value[l.code] === undefined);

  const setLang = (code, text) => onChange({ ...value, [code]: text });
  const addLang = (code) => onChange({ ...value, [code]: '' });
  const removeLang = (code) => {
    const next = { ...value };
    delete next[code];
    onChange(next);
  };

  return (
    <div className="mt-2 space-y-2">
      {active.map(l => (
        <div key={l.code} className="rounded-lg border border-gray-200 bg-gray-50/60 p-2.5">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[11px] font-semibold text-gray-600">
              <span aria-hidden className="mr-1">{l.flag}</span>{l.label}
              {fieldLabel ? ` — ${fieldLabel}` : ''}
            </span>
            <button type="button" onClick={() => removeLang(l.code)}
                    className="text-gray-400 hover:text-red-600 text-sm leading-none px-1"
                    title={t('multilang.remove', { defaultValue: 'Rimuovi questa lingua' })}>
              ×
            </button>
          </div>
          <textarea
            value={value[l.code] || ''}
            onChange={e => setLang(l.code, e.target.value.slice(0, maxLength))}
            rows={rows}
            placeholder={t('multilang.placeholder', {
              lang: l.label,
              defaultValue: 'Scrivi qui il testo in {{lang}}…',
            })}
            className="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:border-gray-900 focus:outline-none resize-y"
          />
        </div>
      ))}
      {inactive.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-[11px] text-gray-400">
            {t('multilang.hint', { defaultValue: 'Offri questo testo anche in:' })}
          </span>
          {inactive.map(l => (
            <button key={l.code} type="button" onClick={() => addLang(l.code)}
                    className="rounded-full border border-dashed border-gray-300 px-2.5 py-1 text-[11px] font-medium text-gray-500 hover:border-primary hover:text-primary transition-colors">
              + {l.flag} {l.label}
            </button>
          ))}
        </div>
      )}
      {active.length > 0 && (
        <p className="text-[11px] text-gray-400">
          {t('multilang.visibility', { defaultValue: 'Il prodotto apparirà nelle viste in queste lingue. Senza traduzione resta visibile solo in italiano.' })}
        </p>
      )}
    </div>
  );
}
