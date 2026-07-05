/**
 * MultiLangSection — processo multilingua unificato (founder 7/7/2026):
 * "stesso processo semplice in tutti i tipi prodotto, passando
 * facilmente tra le lingue".
 *
 * Una riga di tab [🇮🇹 Italiano][🇬🇧 English][🇩🇪 Deutsch][🇫🇷 Français]
 * sopra una sezione di campi. In Italiano si vedono i campi originali
 * (children); nelle altre tab gli STESSI campi, col testo italiano come
 * placeholder. Pallino verde sulle lingue compilate. Stesso pattern
 * dell'editor del programma (RetreatContentEditor).
 *
 * fields: [{key, label, it, value:{en:'...'}, onChange(next), input?,
 *           rows?, maxLength?}]
 *   - `it` = valore italiano corrente (diventa il placeholder)
 *   - `value`/`onChange` = dict per-lingua del campo ({en:'text'})
 *   - `input: true` → <input>, altrimenti <textarea rows>
 */
import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';

const LANGS = [
  { code: 'it', label: 'Italiano', flag: '🇮🇹' },
  { code: 'en', label: 'English', flag: '🇬🇧' },
  { code: 'de', label: 'Deutsch', flag: '🇩🇪' },
  { code: 'fr', label: 'Français', flag: '🇫🇷' },
];

export default function MultiLangSection({ fields, children, hint }) {
  const { t } = useTranslation('products');
  // Senza children la sezione è SOLO traduzioni (i campi italiani vivono
  // già sopra, sempre visibili): niente tab Italiano, si parte da EN.
  const translationsOnly = children === null || children === undefined;
  const [lang, setLang] = useState(translationsOnly ? 'en' : 'it');

  const langFilled = (code) =>
    fields.some(f => ((f.value || {})[code] || '').trim());

  const inputCls = 'w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:border-gray-900 focus:outline-none';

  return (
    <div>
      <div className="flex items-center gap-1 mb-2">
        {(translationsOnly ? LANGS.filter(l => l.code !== 'it') : LANGS).map(l => (
          <button
            key={l.code}
            type="button"
            onClick={() => setLang(l.code)}
            className={`rounded-full px-2.5 py-0.5 text-[11px] font-medium transition-colors ${
              lang === l.code
                ? 'bg-gray-900 text-white'
                : 'text-gray-500 hover:bg-gray-100'
            }`}
          >
            <span aria-hidden className="mr-0.5">{l.flag}</span>{l.label}
            {l.code !== 'it' && langFilled(l.code) && (
              <span className={`ml-1 ${lang === l.code ? 'text-white/80' : 'text-emerald-600'}`}>●</span>
            )}
          </button>
        ))}
      </div>

      {lang === 'it' ? children : (
        <div className="space-y-3 rounded-lg border border-gray-200 bg-gray-50/60 p-3">
          {fields.map(f => (
            <div key={f.key}>
              {f.label && (
                <label className="block text-xs font-medium text-gray-600 mb-1">{f.label}</label>
              )}
              {f.input ? (
                <input
                  type="text"
                  value={(f.value || {})[lang] || ''}
                  maxLength={f.maxLength}
                  placeholder={f.it || ''}
                  onChange={e => f.onChange({ ...(f.value || {}), [lang]: e.target.value })}
                  className={inputCls}
                />
              ) : (
                <textarea
                  value={(f.value || {})[lang] || ''}
                  rows={f.rows || 3}
                  maxLength={f.maxLength}
                  placeholder={f.it || ''}
                  onChange={e => f.onChange({ ...(f.value || {}), [lang]: e.target.value })}
                  className={`${inputCls} resize-y`}
                />
              )}
            </div>
          ))}
          <p className="text-[11px] text-gray-400">
            {hint || t('multilang.sectionHint', {
              defaultValue: 'Il testo italiano è il suggerimento nel campo. Le lingue con la descrizione compilata sono le lingue in cui il prodotto appare al pubblico; i campi vuoti restano in italiano.',
            })}
          </p>
        </div>
      )}
    </div>
  );
}
