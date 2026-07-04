/**
 * Wave GDPR-Commerce Phase CG-3 — markdown editor with live preview.
 *
 * Used inside the GDPR settings card to let the merchant edit each
 * of the 8 content slots (privacy/terms × it/en/de/fr).
 *
 * Design choices
 * --------------
 * - NO new npm dependency (CodeMirror / Monaco / TipTap would all
 *   blow the bundle for what is essentially a 30K markdown textarea).
 * - Split-pane editor + preview using a plain ``<textarea>`` for the
 *   source and the existing ``LegalMarkdownRenderer`` for the preview.
 * - Variables panel sits ABOVE the split — clicking a variable copies
 *   its ``{{placeholder}}`` to the clipboard and shows a quick visual
 *   feedback. The merchant pastes it where needed.
 *
 * Props
 * -----
 * - ``value``: current markdown string (controlled)
 * - ``onChange(newValue)``: called on every keystroke
 * - ``disabled``: gray-out + readonly while saving/publishing
 * - ``placeholder``: optional placeholder shown when value=""
 *
 * Designed to be REUSED by both the per-locale editor tabs and any
 * future legal-docs surface — it has no GDPR-card-specific knowledge.
 */
import React, { useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { Copy, Check } from 'lucide-react';

import LegalMarkdownRenderer from './LegalMarkdownRenderer';


/**
 * The set of template variables that the standard-draft generator
 * supports. Kept in sync with backend's TemplateVars manually — there
 * are only 12 of them and they don't change often. If a new variable
 * is added in CG-N, mirror it here.
 */
const AVAILABLE_VARIABLES = [
  'merchant_name',
  'merchant_email',
  'merchant_country',
  'store_name',
  'store_country',
  'collects_phone',
  'collects_shipping_address',
  'uses_marketing',
  'ships_to_eu',
  'platform_name',
  'platform_controller_name',
  'platform_controller_email',
  'platform_controller_country',
];


function VariableChip({ name, onCopy }) {
  const [copied, setCopied] = useState(false);
  const handleClick = useCallback(() => {
    const placeholder = `{{${name}}}`;
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(placeholder).then(
        () => {
          setCopied(true);
          if (onCopy) onCopy(placeholder);
          setTimeout(() => setCopied(false), 1500);
        },
        () => {
          // Clipboard API failed (insecure context / permissions denied).
          // Fall through silently — the merchant can still type it manually.
        }
      );
    }
  }, [name, onCopy]);

  return (
    <button
      type="button"
      onClick={handleClick}
      className="inline-flex items-center gap-1 rounded-md border px-2 py-1 text-xs font-mono text-gray-700 hover:bg-gray-50 hover:border-gray-400 transition-colors"
    >
      {copied ? <Check className="h-3 w-3 text-green-600" /> : <Copy className="h-3 w-3" />}
      {`{{${name}}}`}
    </button>
  );
}


export default function MerchantLegalEditor({
  value,
  onChange,
  disabled = false,
  placeholder = '',
}) {
  const { t } = useTranslation('legal');

  return (
    <div className="space-y-3">
      {/* Variables panel */}
      <div className="rounded-md border bg-gray-50 p-3">
        <p className="text-xs font-medium text-gray-700 mb-1">
          {t('admin_gdpr.variables_title')}
        </p>
        <p className="text-xs text-gray-500 mb-2">
          {t('admin_gdpr.variables_help')}
        </p>
        <div className="flex flex-wrap gap-1.5">
          {AVAILABLE_VARIABLES.map((v) => (
            <VariableChip key={v} name={v} />
          ))}
        </div>
      </div>

      {/* Split editor + preview */}
      <div className="grid gap-3 md:grid-cols-2">
        <div className="flex flex-col">
          <label className="text-xs uppercase tracking-wide text-gray-500 mb-1">
            {t('admin_gdpr.editor_label')}
          </label>
          <textarea
            value={value || ''}
            onChange={(e) => onChange(e.target.value)}
            disabled={disabled}
            placeholder={placeholder}
            className="flex-1 w-full min-h-[400px] resize-y rounded-md border border-gray-300 p-3 font-mono text-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
            spellCheck="false"
          />
          <p className="text-xs text-gray-400 mt-1">
            {(value || '').length.toLocaleString()} / 30,000
          </p>
        </div>

        <div className="flex flex-col">
          <label className="text-xs uppercase tracking-wide text-gray-500 mb-1">
            {t('admin_gdpr.preview_label')}
          </label>
          <div className="flex-1 w-full min-h-[400px] overflow-y-auto rounded-md border border-gray-300 bg-white p-3 text-sm">
            {value
              ? <LegalMarkdownRenderer content={value} />
              : <p className="text-gray-400 italic">—</p>
            }
          </div>
        </div>
      </div>
    </div>
  );
}
