import React from 'react';
import { Pin, PinOff } from 'lucide-react';
import { Button } from '../../components/ui/button';

/**
 * PinToDashboardButton — small toggle button for pinning a widget to the dashboard.
 *
 * Props:
 *   widgetKey  — unique widget identifier (e.g. "cashflow_monitor:sales_expenses_chart")
 *   isPinned   — whether this widget is currently pinned
 *   onToggle   — callback(widgetKey) invoked on click; parent handles API call
 */
export const PinToDashboardButton = ({ widgetKey, isPinned, onToggle }) => (
  <Button
    variant="ghost"
    size="icon"
    className="h-8 w-8 shrink-0"
    title={isPinned ? 'Rimuovi dalla dashboard' : 'Aggiungi alla dashboard'}
    onClick={(e) => {
      e.stopPropagation();
      onToggle(widgetKey);
    }}
  >
    {isPinned ? (
      <PinOff className="h-3.5 w-3.5 text-primary" />
    ) : (
      <Pin className="h-3.5 w-3.5 text-muted-foreground" />
    )}
  </Button>
);

export default PinToDashboardButton;
