/**
 * CashflowPagination — domain pagination footer for the cashflow tables.
 *
 * Phase 2 (2026-05-20). Sits below each Section's table and lets the
 * merchant browse pages of records served by the new ``/search``
 * backend endpoints.
 *
 * Why a custom component, not shadcn's Pagination
 * -----------------------------------------------
 * shadcn's ``components/ui/pagination.jsx`` is a primitive scaffold
 * (nav / ul / li / a) — composing it into "←  Pagina 3 di 12 (587
 * record)  →" would be more boilerplate at every Section than just
 * baking the pattern here once. The visual is also tighter: a single
 * row with prev / counter / next, no overflowing on small viewports.
 *
 * Contract
 * --------
 *   total       int  — total records matching the current filters
 *   page        int  — 1-based current page
 *   pageSize    int  — records per page (default 50)
 *   onChange    fn   — (newPage) => void; called when user clicks a button
 *   hasMore     bool — backend-provided flag (skip + items.length < total)
 *   loading     bool — disable buttons while a fetch is in flight
 *   className?  string
 *
 * Hidden when total ≤ pageSize — a single-page result set doesn't
 * need pagination chrome.
 */

import React from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { useTranslation } from 'react-i18next';

import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';


export function CashflowPagination({
  total,
  page,
  pageSize = 50,
  onChange,
  hasMore = false,
  loading = false,
  className,
}) {
  const { t } = useTranslation('cashflow_monitor');

  // Hide the chrome entirely when there's nothing to paginate.
  if (!total || total <= pageSize) return null;

  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const canGoPrev = page > 1 && !loading;
  const canGoNext = (hasMore || page < totalPages) && !loading;

  const fromIdx = (page - 1) * pageSize + 1;
  const toIdx = Math.min(page * pageSize, total);

  return (
    <div
      className={cn(
        'flex flex-wrap items-center justify-between gap-2 px-2 py-2 border-t',
        'text-sm text-muted-foreground',
        className,
      )}
      role="navigation"
      aria-label="Pagination"
    >
      <span>
        {t('pagination.range', {
          from: fromIdx,
          to: toIdx,
          total,
          defaultValue: `${fromIdx}–${toIdx} di ${total}`,
        })}
      </span>

      <div className="flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          disabled={!canGoPrev}
          onClick={() => onChange(page - 1)}
          aria-label={t('pagination.prev', { defaultValue: 'Pagina precedente' })}
        >
          <ChevronLeft className="h-4 w-4" />
        </Button>

        <span className="px-2 text-foreground tabular-nums">
          {t('pagination.page', {
            page,
            totalPages,
            defaultValue: `${page} / ${totalPages}`,
          })}
        </span>

        <Button
          variant="outline"
          size="sm"
          disabled={!canGoNext}
          onClick={() => onChange(page + 1)}
          aria-label={t('pagination.next', { defaultValue: 'Pagina successiva' })}
        >
          <ChevronRight className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}


export default CashflowPagination;
