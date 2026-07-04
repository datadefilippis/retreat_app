/**
 * BunnyStatusBadge — pill that shows a Bunny verification status.
 *
 * Single-source-of-truth visual for "is this library/integration
 * working?". Used in the library list rows, in the CourseEditor
 * sidebar widget, and (future) in any read-only place that needs
 * to surface the status at a glance.
 *
 * The visual mapping lives in `../visuals.js` so adding a new status
 * is a one-file change.
 */

import React from 'react';
import { useTranslation } from 'react-i18next';
import { statusVisuals } from '../visuals';


export default function BunnyStatusBadge({ status, className = '' }) {
  const { t } = useTranslation('products');
  const v = statusVisuals(status, t);
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold ${v.badgeCls} ${className}`}
      // Aria: parent context normally identifies the library; the
      // badge itself is decorative + textual, no need for a separate
      // aria-label here.
    >
      <span aria-hidden>{v.icon}</span>
      {v.label}
    </span>
  );
}
