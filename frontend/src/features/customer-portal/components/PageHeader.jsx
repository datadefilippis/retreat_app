/**
 * PageHeader — title + optional back link / action consistent across
 * all customer portal pages.
 *
 * Pattern: every page (Home / Courses / Orders / OrderDetail / Profile)
 * needs roughly the same anatomy: an optional ← back link, a big title,
 * an optional secondary description line, and an optional CTA on the
 * right (e.g. "Esporta", "Apri carrello", "Salva modifiche"). This
 * component owns that pattern so the layout stays uniform when we
 * migrate page by page.
 */

import React from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { ArrowLeft } from 'lucide-react';


export default function PageHeader({
  title,
  description = null,
  backTo = null,
  backLabel,
  action = null,
  meta = null,
}) {
  const { t } = useTranslation('customer_portal');
  const resolvedBackLabel = backLabel ?? t('customer_portal:nav.back');
  return (
    <div className="space-y-2">
      {backTo && (
        <Link
          to={backTo}
          className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          {resolvedBackLabel}
        </Link>
      )}
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div className="min-w-0">
          <h1 className="text-2xl font-bold text-gray-900 leading-tight">
            {title}
          </h1>
          {description && (
            <p className="text-sm text-muted-foreground mt-1">{description}</p>
          )}
          {meta && (
            <div className="mt-1.5 flex items-center gap-2 flex-wrap text-xs text-muted-foreground">
              {meta}
            </div>
          )}
        </div>
        {action && <div className="shrink-0">{action}</div>}
      </div>
    </div>
  );
}
