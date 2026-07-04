/**
 * StatusBadge — generic colored pill used across the customer portal.
 *
 * Two ways to use it:
 *   1. Pass `order` and the badge auto-resolves via resolveOrderBadge().
 *   2. Pass `label` + `className` (or just `tone`) for any non-order use.
 *
 * Rendered with a base size that matches shadcn `Badge` so it sits
 * consistently next to other pills (course chip "🎓 Corso", etc).
 */

import React from 'react';
import { useTranslation } from 'react-i18next';
import { Badge } from '../../../components/ui/badge';
import { resolveOrderBadge } from '../utils/orderStatus';


const TONE_CLASSES = {
  neutral:  'bg-gray-100 text-gray-700',
  info:     'bg-blue-100 text-blue-700',
  success:  'bg-emerald-100 text-emerald-700',
  warning:  'bg-amber-100 text-amber-800',
  danger:   'bg-red-100 text-red-600',
  course:   'bg-blue-100 text-blue-900 hover:bg-blue-100',
};


export default function StatusBadge({ order, label, tone, className }) {
  const { t } = useTranslation('customer_portal');
  // Order-derived path: resolve via the canonical helper.
  if (order) {
    const badge = resolveOrderBadge(order, t);
    return (
      <Badge className={`text-[10px] ${badge.className} ${className || ''}`}>
        {badge.label}
      </Badge>
    );
  }

  // Manual path: caller picks a tone or passes raw classes.
  const cls = className || TONE_CLASSES[tone] || TONE_CLASSES.neutral;
  return (
    <Badge className={`text-[10px] ${cls}`}>
      {label}
    </Badge>
  );
}
