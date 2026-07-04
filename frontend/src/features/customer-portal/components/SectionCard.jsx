/**
 * SectionCard — content container with a structured header.
 *
 * The customer portal repeats this pattern at every section:
 *   ┌── 🎯 Title ─────────────── action  ─┐
 *   │                                       │
 *   │  [content]                            │
 *   │                                       │
 *   └───────────────────────────────────────┘
 *
 * Centralizing it means the HomePage carousel ("Continua un corso"),
 * the OrdersPage list, the ProfilePage forms, etc. all read with the
 * same visual hierarchy. Action slot lets the parent inject a "View
 * all →" link or a "+" button without owning the layout.
 *
 * Two variants:
 *   - default: white card with shadow + border
 *   - plain:   transparent (when nesting inside another card)
 */

import React from 'react';


export default function SectionCard({
  icon = null,
  title,
  description = null,
  action = null,
  children,
  variant = 'default',
  className = '',
}) {
  const wrapper = variant === 'plain'
    ? `space-y-3 ${className}`
    : `bg-white rounded-2xl border border-gray-200 shadow-sm p-5 space-y-4 ${className}`;

  return (
    <section className={wrapper}>
      {(title || action) && (
        <div className="flex items-baseline justify-between gap-3 flex-wrap">
          <div className="min-w-0">
            {title && (
              <h2 className="text-base font-semibold text-gray-900 flex items-center gap-2">
                {icon && <span aria-hidden>{icon}</span>}
                {title}
              </h2>
            )}
            {description && (
              <p className="text-xs text-gray-500 mt-0.5">{description}</p>
            )}
          </div>
          {action && <div className="shrink-0">{action}</div>}
        </div>
      )}
      {children}
    </section>
  );
}
