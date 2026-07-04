import React from 'react';
import { Button } from './ui/button';
import { cn } from '../lib/utils';

/**
 * PageSubheader — responsive subheader with tabs (left) + actions (right).
 *
 * Sits directly under the main <Header>. Designed to keep pages with
 * multiple tabs + contextual actions readable on small screens by
 * stacking the rows instead of cramming them into a single viewport-wide
 * flex bar.
 *
 * Layout rules:
 *   Desktop (≥768px): single row — tabs on the left, actions on the right
 *   Tablet  (640-767): single row, tighter gaps, short labels allowed
 *   Mobile  (<640px): tabs on their own row (scrollable if many),
 *                     actions wrap below on a second row
 *
 * Props:
 *   tabs     : array of { key, label, shortLabel?, icon? (lucide comp), disabled? }
 *   activeTab: key of the currently active tab
 *   onTabChange: (key) => void
 *   actions  : ReactNode (typically buttons — rendered as-is)
 *   sticky   : boolean (default true) — stick under the main Header
 *
 * This component renders NOTHING when both tabs and actions are empty —
 * callers do not need to guard.
 */
export const PageSubheader = ({
  tabs = [],
  activeTab,
  onTabChange,
  actions,
  sticky = true,
  className,
}) => {
  const hasTabs = Array.isArray(tabs) && tabs.length > 0;
  const hasActions = !!actions;
  if (!hasTabs && !hasActions) return null;

  const containerCls = cn(
    'border-b border-border/50 bg-white/70 backdrop-blur-xl',
    sticky && 'sticky top-14 md:top-16 z-20',
    className,
  );

  return (
    <div className={containerCls}>
      <div
        className={cn(
          'px-4 md:px-8 py-2',
          // Mobile: stack rows. Tablet+: single row with space-between.
          'flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between sm:gap-3',
        )}
      >
        {hasTabs && (
          <div
            className={cn(
              'flex items-center gap-1 bg-muted rounded-lg p-0.5',
              // Horizontal scroll as last-resort safety on extremely narrow screens
              'overflow-x-auto scrollbar-hide',
              // On mobile the tab group takes the full row so tap targets are big.
              // On tablet+ it hugs its content.
              'w-full sm:w-auto',
            )}
          >
            {tabs.map((tab) => {
              const Icon = tab.icon;
              const isActive = tab.key === activeTab;
              return (
                <Button
                  key={tab.key}
                  variant={isActive ? 'default' : 'ghost'}
                  size="sm"
                  disabled={tab.disabled}
                  onClick={() => onTabChange && onTabChange(tab.key)}
                  className={cn(
                    // Base: compact, touch-friendly (h-8 ≈ 32px)
                    'h-8 gap-1.5 text-xs shrink-0',
                    // Grow to share the row on mobile so 2-3 tabs fill it nicely;
                    // hug content on tablet+ so the group stays compact.
                    'flex-1 sm:flex-initial',
                    !isActive && 'text-muted-foreground hover:text-foreground',
                  )}
                >
                  {Icon && <Icon className="h-3.5 w-3.5 shrink-0" />}
                  {/* Short label on mobile if provided, full label from sm+ */}
                  {tab.shortLabel ? (
                    <>
                      <span className="sm:hidden">{tab.shortLabel}</span>
                      <span className="hidden sm:inline">{tab.label}</span>
                    </>
                  ) : (
                    <span>{tab.label}</span>
                  )}
                </Button>
              );
            })}
          </div>
        )}

        {hasActions && (
          <div
            className={cn(
              'flex items-center gap-2',
              // Mobile: actions row is full-width and can wrap; tablet+ hugs right.
              'w-full sm:w-auto sm:justify-end',
              'flex-wrap sm:flex-nowrap',
            )}
          >
            {actions}
          </div>
        )}
      </div>
    </div>
  );
};

export default PageSubheader;
