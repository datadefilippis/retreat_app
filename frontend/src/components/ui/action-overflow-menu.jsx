import React from 'react';
import { MoreVertical } from 'lucide-react';
import { Button } from './button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
} from './dropdown-menu';
import { cn } from '../../lib/utils';

/**
 * ActionOverflowMenu — responsive collection of row/card actions.
 *
 * Purpose:
 *   Today's admin rows (store cards, order rows, coupon entries) expose
 *   4-5 action buttons side-by-side. This wraps awkwardly on phones and
 *   truncates labels. This component shows a small set of primary
 *   actions inline and hides the rest behind a "⋮" dropdown.
 *
 * Responsive behavior:
 *   Desktop (≥768px): primary + secondary both rendered inline as Buttons.
 *   Mobile  (<768px): only primary is inline; secondary collapses into
 *                    the overflow dropdown.
 *
 * Props:
 *   primary:   [{ icon?, label, onClick, variant?, disabled? }]
 *     - Rendered as always-visible Buttons. Keep to 1-2 items on mobile.
 *   secondary: [{ icon?, label, onClick, variant?, disabled?, destructive? }]
 *     - Rendered inline on desktop, inside overflow dropdown on mobile.
 *   triggerIcon: lucide component (default MoreVertical)
 *   triggerAriaLabel: a11y label for the trigger button
 *   align: DropdownMenu alignment — "end" (default) | "start"
 *   alwaysShowOverflow: if true, the overflow menu renders even on desktop
 *                      (so you never lose the ⋮ affordance)
 *   className: extra classes on the outer container
 *
 * The component itself does NOT manage disclosure of primary items on
 * hover/focus — callers control visibility via disabled. Any button
 * passed in is rendered as-is via shadcn Button so variants (ghost,
 * outline, destructive) work verbatim.
 */
export const ActionOverflowMenu = ({
  primary = [],
  secondary = [],
  triggerIcon: TriggerIcon = MoreVertical,
  triggerAriaLabel = 'More actions',
  align = 'end',
  alwaysShowOverflow = false,
  className,
}) => {
  const hasPrimary = Array.isArray(primary) && primary.length > 0;
  const hasSecondary = Array.isArray(secondary) && secondary.length > 0;
  if (!hasPrimary && !hasSecondary) return null;

  const renderPrimaryButton = (item, i) => {
    const Icon = item.icon;
    return (
      <Button
        key={`p-${i}`}
        variant={item.variant || 'outline'}
        size={item.size || 'sm'}
        disabled={item.disabled}
        onClick={item.onClick}
        className={cn('gap-1.5', item.className)}
        title={item.label}
      >
        {Icon && <Icon className="h-3.5 w-3.5 shrink-0" />}
        {/* Label visible from sm+ so phones keep the button compact. */}
        <span className={cn(item.hideLabelMobile !== false && 'hidden sm:inline')}>
          {item.label}
        </span>
      </Button>
    );
  };

  const renderSecondaryInline = (item, i) => {
    const Icon = item.icon;
    const isDestructive = item.destructive;
    return (
      <Button
        key={`s-inline-${i}`}
        variant={item.variant || 'ghost'}
        size={item.size || 'sm'}
        disabled={item.disabled}
        onClick={item.onClick}
        className={cn(
          'gap-1.5',
          isDestructive && 'text-destructive hover:text-destructive hover:bg-destructive/10',
          item.className,
        )}
        title={item.label}
      >
        {Icon && <Icon className="h-3.5 w-3.5 shrink-0" />}
        <span className="hidden sm:inline">{item.label}</span>
      </Button>
    );
  };

  return (
    <div className={cn('flex items-center gap-1.5', className)}>
      {/* Primary actions — always visible */}
      {hasPrimary && primary.map(renderPrimaryButton)}

      {/* Secondary actions — inline from md+, inside dropdown on mobile */}
      {hasSecondary && !alwaysShowOverflow && (
        <div className="hidden md:flex items-center gap-1.5">
          {secondary.map(renderSecondaryInline)}
        </div>
      )}

      {/* Overflow menu — renders on mobile, or always if alwaysShowOverflow */}
      {hasSecondary && (
        <div className={cn(!alwaysShowOverflow && 'md:hidden')}>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8 shrink-0"
                aria-label={triggerAriaLabel}
              >
                <TriggerIcon className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align={align} className="w-48">
              {secondary.map((item, i) => {
                if (item.separator) {
                  return <DropdownMenuSeparator key={`sep-${i}`} />;
                }
                const Icon = item.icon;
                return (
                  <DropdownMenuItem
                    key={`s-menu-${i}`}
                    disabled={item.disabled}
                    onClick={item.onClick}
                    className={cn(
                      'gap-2 cursor-pointer',
                      item.destructive && 'text-destructive focus:text-destructive focus:bg-destructive/10',
                    )}
                  >
                    {Icon && <Icon className="h-4 w-4 shrink-0" />}
                    <span>{item.label}</span>
                  </DropdownMenuItem>
                );
              })}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      )}
    </div>
  );
};

export default ActionOverflowMenu;
