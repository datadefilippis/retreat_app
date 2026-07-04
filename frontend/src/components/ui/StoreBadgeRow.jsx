/**
 * StoreBadgeRow — compact, overflow-safe badge stack.
 *
 * Problem solved
 * --------------
 * The previous store-card layout rendered up to 4 badges in a flex-wrap
 * row, which:
 *   - pushed the header to 2-3 lines on mobile,
 *   - made it hard to identify the most important status at a glance,
 *   - looked busy on a card with multiple action buttons.
 *
 * This helper takes a list of badge descriptors and renders at most
 * ``maxVisible`` of them; any extras collapse into a single "+N" badge
 * with a tooltip listing the hidden ones. The order of the input array
 * is the priority order — the caller controls which badges win.
 *
 * It's deliberately framework-light: 1 wrapper div, n Badge primitives
 * already in the design system, 1 Tooltip when overflow happens. No
 * portal allocation when there's no overflow.
 *
 * Props
 * -----
 * - ``badges``  array of { key, label, icon?, className?, title? }
 *               (only entries with truthy value are rendered — callers
 *               can inline conditionals like `cond && {…}`)
 * - ``maxVisible`` integer, default 2. The remainder collapses to "+N".
 * - ``className`` wrapper class merger
 *
 * The Badge primitive is imported from the existing shadcn ui/badge.
 */

import React from 'react';
import { Badge } from './badge';
import {
  Tooltip,
  TooltipTrigger,
  TooltipContent,
  TooltipProvider,
} from './tooltip';


function renderBadge(b) {
  const Icon = b.icon;
  return (
    <Badge
      key={b.key}
      className={`text-[10px] whitespace-nowrap ${b.className || ''}`}
      title={b.title || undefined}
    >
      {Icon && <Icon className="h-2.5 w-2.5 mr-0.5 inline" />}
      {b.label}
    </Badge>
  );
}


export default function StoreBadgeRow({ badges = [], maxVisible = 2, className = '' }) {
  // Filter out falsy entries — lets callers do `cond && {…}` inline.
  const real = (badges || []).filter(Boolean);

  if (real.length === 0) return null;

  if (real.length <= maxVisible) {
    return (
      <div className={`flex items-center gap-1 flex-wrap ${className}`}>
        {real.map(renderBadge)}
      </div>
    );
  }

  const visible = real.slice(0, maxVisible);
  const hidden = real.slice(maxVisible);

  return (
    <TooltipProvider delayDuration={200}>
      <div className={`flex items-center gap-1 flex-wrap ${className}`}>
        {visible.map(renderBadge)}
        <Tooltip>
          <TooltipTrigger asChild>
            <button
              type="button"
              className="inline-flex items-center rounded-full border bg-muted text-muted-foreground px-2 py-0.5 text-[10px] font-medium cursor-help hover:bg-muted/80 transition-colors"
              aria-label={`+${hidden.length} altri stati`}
            >
              +{hidden.length}
            </button>
          </TooltipTrigger>
          <TooltipContent side="top" className="max-w-xs">
            <ul className="space-y-0.5 text-xs">
              {hidden.map((b) => (
                <li key={b.key} className="whitespace-nowrap">
                  • {b.label}
                </li>
              ))}
            </ul>
          </TooltipContent>
        </Tooltip>
      </div>
    </TooltipProvider>
  );
}
