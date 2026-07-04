/**
 * HelpCheatsheet — keyboard shortcuts modal.
 *
 * Desktop-only power-user affordance, paired with the floating "?"
 * button in the bottom-right corner of the page (rendered by the
 * orchestrator). Lists the shortcuts that the `useLessonNavigation`
 * hook wires on the window keydown event.
 *
 * Why a dedicated file: it's a small, self-contained piece of UI
 * with its own escape semantics (backdrop click + ESC) that benefit
 * from isolation. Keeps the orchestrator free of modal markup.
 *
 * Behavioral contract:
 *   • Renders nothing when `open` is false (no portal / always-mounted)
 *   • Closes via backdrop click, X button, or ESC
 *   • Always lists the same 3 shortcuts — kept in sync manually with
 *     the hook (single-truth lock-step is documented there)
 */

import React from 'react';
import { useTranslation } from 'react-i18next';
import { X as XIcon } from 'lucide-react';


// Shortcut data (key glyphs are universal, labels come from i18n).
// Adding a shortcut: extend this array + add a new branch in
// useLessonNavigation + add a `shortcut<X>` key in customer_portal.json.
const SHORTCUTS = [
  { keys: ['←'], labelKey: 'customer_portal:helpCheatsheet.shortcutPrev' },
  { keys: ['→'], labelKey: 'customer_portal:helpCheatsheet.shortcutNext' },
  { keys: ['M'], labelKey: 'customer_portal:helpCheatsheet.shortcutMark' },
];


export default function HelpCheatsheet({ open, onClose }) {
  const { t } = useTranslation('customer_portal');
  if (!open) return null;
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center px-4"
      onKeyDown={(e) => { if (e.key === 'Escape') onClose?.(); }}
      tabIndex={-1}
    >
      {/* Backdrop — clicking dismisses */}
      <button
        type="button"
        aria-label={t('customer_portal:helpCheatsheet.closeAria')}
        onClick={onClose}
        className="absolute inset-0 bg-black/50 cursor-default"
      />
      {/* Panel */}
      <div className="relative bg-white rounded-2xl shadow-2xl max-w-sm w-full p-5 space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold text-gray-900">
            {t('customer_portal:helpCheatsheet.title')}
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="p-1 -mr-1 rounded-md hover:bg-gray-100"
            aria-label={t('customer_portal:helpCheatsheet.closeAria')}
          >
            <XIcon className="h-4 w-4 text-gray-700" />
          </button>
        </div>

        <ul className="space-y-2 text-sm">
          {SHORTCUTS.map((row, i) => (
            <li key={i} className="flex items-center justify-between gap-3">
              <span className="text-gray-700">{t(row.labelKey)}</span>
              <span className="flex items-center gap-1">
                {row.keys.map(k => (
                  <kbd
                    key={k}
                    className="inline-flex items-center justify-center min-w-[28px] h-7 px-2 rounded-md bg-gray-100 border border-gray-300 text-gray-800 text-xs font-mono shadow-[inset_0_-1px_0_rgba(0,0,0,0.08)]"
                  >
                    {k}
                  </kbd>
                ))}
              </span>
            </li>
          ))}
        </ul>

        <div className="text-xs text-gray-500 border-t border-gray-100 pt-3">
          {t('customer_portal:helpCheatsheet.footnote')}
        </div>
      </div>
    </div>
  );
}
