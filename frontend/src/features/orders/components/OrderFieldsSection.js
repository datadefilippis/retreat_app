/**
 * OrderFieldsSection — renders the custom order_fields_data collected from the
 * checkout form (Modulo F2 Onda 9).
 *
 * Each merchant can configure arbitrary custom fields per store; the customer
 * fills them at checkout and the values land in order.order_fields_data as a
 * dict. This component surfaces them in the admin detail panel so the merchant
 * can actually see what the customer wrote (delivery instructions, size notes,
 * special requests, etc.).
 *
 * Collapsed by default when there are more than 4 entries to keep the panel
 * scannable.
 */

import { useState } from 'react';
import { ClipboardList, ChevronDown, ChevronUp } from 'lucide-react';

export default function OrderFieldsSection({ order, t }) {
  const data = order?.order_fields_data;
  const entries = data && typeof data === 'object' ? Object.entries(data) : [];
  const initialCollapsed = entries.length > 4;
  const [collapsed, setCollapsed] = useState(initialCollapsed);

  if (entries.length === 0) return null;

  const visible = collapsed ? entries.slice(0, 2) : entries;

  const formatValue = (v) => {
    if (v == null || v === '') return '—';
    if (Array.isArray(v)) return v.join(', ');
    if (typeof v === 'boolean') return v ? '✓' : '✗';
    if (typeof v === 'object') return JSON.stringify(v);
    return String(v);
  };

  // Humanize snake_case keys into Title Case for display.
  const humanize = (key) =>
    String(key)
      .replace(/[_-]+/g, ' ')
      .replace(/\b\w/g, (c) => c.toUpperCase());

  return (
    <div className="rounded-lg border p-3 space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-xs font-medium text-muted-foreground uppercase tracking-wide">
          <ClipboardList className="h-3.5 w-3.5" />
          {t?.('detail.order_fields', { defaultValue: 'Info dal checkout' })}
        </div>
        {initialCollapsed && (
          <button
            type="button"
            onClick={() => setCollapsed((v) => !v)}
            className="text-[11px] text-primary hover:underline inline-flex items-center gap-1"
          >
            {collapsed
              ? t?.('detail.show_all_fields', { count: entries.length, defaultValue: `Mostra tutti (${entries.length})` })
              : t?.('detail.show_less', { defaultValue: 'Mostra meno' })}
            {collapsed ? <ChevronDown className="h-3 w-3" /> : <ChevronUp className="h-3 w-3" />}
          </button>
        )}
      </div>
      <dl className="text-sm space-y-1">
        {visible.map(([k, v]) => (
          <div key={k} className="flex items-start gap-2">
            <dt className="text-xs text-muted-foreground shrink-0 w-1/3 pt-0.5">{humanize(k)}</dt>
            <dd className="flex-1 break-words">{formatValue(v)}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
