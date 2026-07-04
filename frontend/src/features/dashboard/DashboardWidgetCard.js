import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { X, ChevronUp, ChevronDown } from 'lucide-react';
import { useTranslation } from 'react-i18next';

/**
 * DashboardWidgetCard — wrapper for each pinned widget rendered in the dashboard.
 *
 * Shows:
 *   - Widget title (from registry) in a minimal header
 *   - Reorder arrows (up / down) to shift position
 *   - Remove button (X) to unpin from dashboard
 *   - The actual widget component rendered as children
 *
 * Props:
 *   title      — human-readable name from WIDGET_REGISTRY (fallback)
 *   nameKey    — optional i18n key for the widget title
 *   nameNS     — optional i18n namespace for nameKey (default: module namespace)
 *   size       — 'full' | 'half' (drives col-span in parent grid)
 *   isFirst    — disable "move up" arrow
 *   isLast     — disable "move down" arrow
 *   onMoveUp   — callback to shift widget one position up
 *   onMoveDown — callback to shift widget one position down
 *   onRemove   — callback to remove widget from dashboard
 *   children   — the rendered widget component
 */
export const DashboardWidgetCard = ({
  title,
  nameKey,
  nameNS,
  size = 'half',
  isFirst,
  isLast,
  onMoveUp,
  onMoveDown,
  onRemove,
  children,
}) => {
  const { t } = useTranslation(nameNS || 'common');
  const displayTitle = nameKey ? t(nameKey) : title;
  return (
  <div className={size === 'full' ? 'lg:col-span-2' : ''}>
    <Card className="border border-border group relative">
      {/* Floating toolbar — visible on hover */}
      <div className="absolute -top-3 right-3 z-10 flex items-center gap-0.5 rounded-md border border-border bg-background px-1 py-0.5 opacity-0 shadow-sm transition-opacity group-hover:opacity-100">
        <Button
          variant="ghost"
          size="icon"
          className="h-6 w-6"
          disabled={isFirst}
          onClick={onMoveUp}
          title={t('widget_actions.move_up')}
        >
          <ChevronUp className="h-3.5 w-3.5" />
        </Button>
        <Button
          variant="ghost"
          size="icon"
          className="h-6 w-6"
          disabled={isLast}
          onClick={onMoveDown}
          title={t('widget_actions.move_down')}
        >
          <ChevronDown className="h-3.5 w-3.5" />
        </Button>
        <Button
          variant="ghost"
          size="icon"
          className="h-6 w-6 text-destructive hover:text-destructive"
          onClick={onRemove}
          title={t('widget_actions.remove')}
        >
          <X className="h-3.5 w-3.5" />
        </Button>
      </div>

      {/* Minimal header with widget name */}
      <CardHeader className="pb-0 pt-3 px-4">
        <CardTitle className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
          {displayTitle}
        </CardTitle>
      </CardHeader>

      {/* Widget content */}
      <CardContent className="p-0">
        {children}
      </CardContent>
    </Card>
  </div>
  );
};

export default DashboardWidgetCard;
