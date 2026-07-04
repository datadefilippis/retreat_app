/**
 * CalendarListView — agenda-style table of calendar items for a month.
 *
 * Onda 15 Fase 2. An alternative to the month grid for operators who
 * need to find a specific order/booking without first drilling into a
 * day. The table is purely client-side: it filters and sorts the same
 * `items` array that the month grid receives, so no extra API call.
 *
 * Columns: Data · Ora · Cliente · Tipo · Titolo · Status · [Azione]
 * Interactions:
 *   - Text search across customer_name, title, order_id, code, email, phone
 *   - Type filter chips (All / Eventi / Consulenze / Noleggi)
 *   - Sort by date (default asc) or status
 *   - Tap a row to fire the same onNavigate handler the month grid uses
 */

import React, { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { ExternalLink, Search, ArrowUpDown } from 'lucide-react';
import { Input } from '../../../components/ui/input';
import { Badge } from '../../../components/ui/badge';

const TYPE_LABELS = {
  event_occurrence: { label: 'Evento', emoji: '🎟', className: 'bg-purple-50 text-purple-700 border-purple-200' },
  service_booking:  { label: 'Consulenza', emoji: '📅', className: 'bg-indigo-50 text-indigo-700 border-indigo-200' },
  rental_order:     { label: 'Affitto', emoji: '🧾', className: 'bg-orange-50 text-orange-700 border-orange-200' },
};

const STATUS_LABEL_FALLBACK = {
  published: 'Pubblicato', confirmed: 'Confermato', completed: 'Completato',
  draft: 'Bozza', cancelled: 'Annullato', closed: 'Chiuso', no_show: 'Mancato',
};

function itemMatchesQuery(item, q) {
  if (!q) return true;
  const needle = q.toLowerCase();
  const haystack = [
    item.title, item.customer_name, item.customer_email, item.customer_phone,
    item.order_id, item.booking_code, item.product_name, item.service_option_label,
    item.location,
  ].filter(Boolean).join(' ').toLowerCase();
  return haystack.includes(needle);
}

export default function CalendarListView({ items, onNavigate, year, month }) {
  const { t } = useTranslation('calendar');
  const [query, setQuery] = useState('');
  const [typeFilter, setTypeFilter] = useState('all');
  const [sortBy, setSortBy] = useState('date'); // 'date' | 'type' | 'status'

  const typesPresent = useMemo(() => {
    const s = new Set();
    items.forEach(i => s.add(i.type));
    return s;
  }, [items]);

  const filtered = useMemo(() => {
    const list = items
      .filter(it => typeFilter === 'all' || it.type === typeFilter)
      .filter(it => itemMatchesQuery(it, query));
    const cmp = {
      date: (a, b) => (a.date + (a.time || '')).localeCompare(b.date + (b.time || '')),
      type: (a, b) => (a.type || '').localeCompare(b.type || ''),
      status: (a, b) => (a.status || '').localeCompare(b.status || ''),
    }[sortBy] || ((a, b) => 0);
    return [...list].sort(cmp);
  }, [items, query, typeFilter, sortBy]);

  const monthLabel = new Date(year, month - 1, 1).toLocaleDateString('it-IT', {
    month: 'long', year: 'numeric',
  });

  return (
    <div className="rounded-xl border bg-card overflow-hidden">
      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-2 p-3 border-b bg-muted/20">
        <div className="relative flex-1 min-w-[180px] max-w-md">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
          <Input
            type="text"
            placeholder="Cerca cliente, ordine, codice…"
            value={query}
            onChange={e => setQuery(e.target.value)}
            className="pl-8 h-9 text-sm"
          />
        </div>

        <div className="flex items-center gap-1 rounded-lg border bg-card p-1">
          {[
            { key: 'all',              label: 'Tutti' },
            { key: 'event_occurrence', label: 'Eventi',     show: typesPresent.has('event_occurrence') },
            { key: 'service_booking',  label: 'Consulenze', show: typesPresent.has('service_booking') },
            { key: 'rental_order',     label: 'Affitti',    show: typesPresent.has('rental_order') },
          ].filter(opt => opt.key === 'all' || opt.show).map(opt => (
            <button
              key={opt.key}
              onClick={() => setTypeFilter(opt.key)}
              className={`px-2.5 py-1 rounded-md text-xs font-medium transition-colors ${
                typeFilter === opt.key
                  ? 'bg-primary text-primary-foreground'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>

        <span className="text-xs text-muted-foreground ml-auto capitalize">
          {filtered.length} {filtered.length === 1 ? 'risultato' : 'risultati'} · {monthLabel}
        </span>
      </div>

      {/* Empty state */}
      {filtered.length === 0 ? (
        <div className="p-10 text-center">
          <p className="text-sm text-muted-foreground">
            {query || typeFilter !== 'all'
              ? 'Nessun risultato con i filtri correnti.'
              : 'Nessun evento, consulenza o ordine in questo mese.'}
          </p>
          {(query || typeFilter !== 'all') && (
            <button
              onClick={() => { setQuery(''); setTypeFilter('all'); }}
              className="text-xs text-primary hover:underline mt-2"
            >
              Pulisci filtri
            </button>
          )}
        </div>
      ) : (
        <>
          {/* Desktop table */}
          <div className="hidden md:block overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-muted/30">
                  <SortableHeader label="Data" active={sortBy === 'date'} onClick={() => setSortBy('date')} />
                  <th className="text-left px-3 py-2 font-medium text-muted-foreground">Ora</th>
                  <th className="text-left px-3 py-2 font-medium text-muted-foreground">Cliente</th>
                  <SortableHeader label="Tipo" active={sortBy === 'type'} onClick={() => setSortBy('type')} />
                  <th className="text-left px-3 py-2 font-medium text-muted-foreground">Titolo</th>
                  <SortableHeader label="Stato" active={sortBy === 'status'} onClick={() => setSortBy('status')} />
                  <th className="px-3 py-2"></th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((it, i) => (
                  <ListRow key={`${it.type}-${it.id}-${i}`} item={it} onNavigate={onNavigate} />
                ))}
              </tbody>
            </table>
          </div>

          {/* Mobile card list — same data, card layout, no horizontal scroll */}
          <div className="md:hidden divide-y">
            {filtered.map((it, i) => (
              <MobileRow key={`m-${it.type}-${it.id}-${i}`} item={it} onNavigate={onNavigate} />
            ))}
          </div>
        </>
      )}
    </div>
  );
}

function SortableHeader({ label, active, onClick }) {
  return (
    <th
      className={`text-left px-3 py-2 font-medium cursor-pointer select-none ${
        active ? 'text-foreground' : 'text-muted-foreground hover:text-foreground'
      }`}
      onClick={onClick}
    >
      <span className="inline-flex items-center gap-1">
        {label} <ArrowUpDown className="h-3 w-3 opacity-60" />
      </span>
    </th>
  );
}

function formatDateLabel(date) {
  if (!date) return '—';
  try {
    const d = new Date(date + 'T12:00');
    return d.toLocaleDateString('it-IT', { weekday: 'short', day: 'numeric', month: 'short' });
  } catch {
    return date;
  }
}

function ListRow({ item, onNavigate }) {
  const type = TYPE_LABELS[item.type] || { label: item.type, emoji: '•', className: 'bg-gray-100 text-gray-700' };
  const statusLabel = item.status_label || STATUS_LABEL_FALLBACK[item.status] || item.status;
  const handleClick = () => onNavigate?.(item);
  return (
    <tr
      className="border-b last:border-0 hover:bg-muted/30 cursor-pointer transition-colors"
      onClick={handleClick}
    >
      <td className="px-3 py-2 text-xs capitalize whitespace-nowrap">
        {formatDateLabel(item.date)}
      </td>
      <td className="px-3 py-2 text-xs text-muted-foreground whitespace-nowrap">
        {item.time || '—'}{item.end_time ? `–${item.end_time}` : ''}
      </td>
      <td className="px-3 py-2 font-medium max-w-[180px] truncate">{item.customer_name || '—'}</td>
      <td className="px-3 py-2">
        <Badge className={`text-[10px] ${type.className}`}>
          <span className="mr-1">{type.emoji}</span>{type.label}
        </Badge>
      </td>
      <td className="px-3 py-2 max-w-[260px] truncate">
        {item.title}
        {item.service_option_label && (
          <span className="text-xs text-muted-foreground ml-1">· {item.service_option_label}</span>
        )}
      </td>
      <td className="px-3 py-2 text-xs text-muted-foreground whitespace-nowrap">{statusLabel}</td>
      <td className="px-3 py-2 text-right whitespace-nowrap">
        <button
          onClick={(e) => { e.stopPropagation(); handleClick(); }}
          className="inline-flex items-center gap-1 text-primary hover:underline text-xs"
        >
          <ExternalLink className="h-3 w-3" />
          Apri
        </button>
      </td>
    </tr>
  );
}

function MobileRow({ item, onNavigate }) {
  const type = TYPE_LABELS[item.type] || { label: item.type, emoji: '•', className: 'bg-gray-100 text-gray-700' };
  const statusLabel = item.status_label || STATUS_LABEL_FALLBACK[item.status] || item.status;
  return (
    <button
      onClick={() => onNavigate?.(item)}
      className="w-full text-left p-3 hover:bg-muted/30 transition-colors focus-visible:outline-none focus-visible:bg-muted/30"
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground capitalize">
            <span>{formatDateLabel(item.date)}</span>
            {item.time && <span>· {item.time}{item.end_time ? `–${item.end_time}` : ''}</span>}
          </div>
          <div className="font-medium text-sm mt-0.5 truncate">{item.title}</div>
          {item.customer_name && (
            <div className="text-xs text-muted-foreground mt-0.5 truncate">👤 {item.customer_name}</div>
          )}
          {item.service_option_label && (
            <div className="text-xs text-muted-foreground mt-0.5 truncate">· {item.service_option_label}</div>
          )}
        </div>
        <div className="flex flex-col items-end gap-1 shrink-0">
          <Badge className={`text-[10px] ${type.className}`}>
            <span className="mr-0.5">{type.emoji}</span>{type.label}
          </Badge>
          <span className="text-[10px] text-muted-foreground">{statusLabel}</span>
        </div>
      </div>
    </button>
  );
}
