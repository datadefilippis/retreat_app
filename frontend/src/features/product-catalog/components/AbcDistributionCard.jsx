/**
 * AbcDistributionCard — visual ABC distribution with educational info-box.
 *
 * Renders a stacked bar (A green / B amber / C grey) above three
 * counters. The card title carries an info-box (def/calc/read) so a
 * merchant unfamiliar with ABC analysis understands the underlying
 * Pareto logic without leaving the page.
 *
 * Props:
 *   abc      — { A: count, B: count, C: count } as returned by /overview
 *   loading  — optional skeleton state
 */

import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Card, CardContent } from '../../../components/ui/card';
import { Badge } from '../../../components/ui/badge';
import { Skeleton } from '../../../components/ui/skeleton';
import { Info, X } from 'lucide-react';


export default function AbcDistributionCard({ abc, loading }) {
  const { t } = useTranslation('product_catalog');
  const [showInfo, setShowInfo] = useState(false);

  if (loading) {
    return (
      <Card>
        <CardContent className="p-4 space-y-3">
          <Skeleton className="h-4 w-32" />
          <Skeleton className="h-4 w-full" />
          <div className="grid grid-cols-3 gap-2">
            <Skeleton className="h-12" />
            <Skeleton className="h-12" />
            <Skeleton className="h-12" />
          </div>
        </CardContent>
      </Card>
    );
  }

  const total = (abc?.A || 0) + (abc?.B || 0) + (abc?.C || 0);
  const pA = total > 0 ? ((abc?.A || 0) / total) * 100 : 0;
  const pB = total > 0 ? ((abc?.B || 0) / total) * 100 : 0;

  return (
    <Card className="relative">
      <CardContent className="p-4 space-y-3">
        {/* Header with info-box trigger */}
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold">{t('abc.title')}</h3>
          <button
            type="button"
            onClick={() => setShowInfo(true)}
            aria-label={t('abc.title')}
            className="text-muted-foreground hover:text-foreground transition-colors"
          >
            <Info className="h-4 w-4" />
          </button>
        </div>

        {/* Stacked bar */}
        {total > 0 ? (
          <div className="flex h-4 rounded-full overflow-hidden bg-muted">
            <div className="bg-emerald-500" style={{ width: `${pA}%` }} />
            <div className="bg-amber-400" style={{ width: `${pB}%` }} />
            <div className="bg-gray-300 flex-1" />
          </div>
        ) : (
          <div className="h-4 rounded-full bg-muted" />
        )}

        {/* Three counters */}
        <div className="grid grid-cols-3 gap-2 text-xs">
          <div className="flex flex-col items-center">
            <Badge className="bg-emerald-100 text-emerald-800 mb-1">{t('abc.class_a')}</Badge>
            <span className="font-semibold tabular-nums">
              {t('abc.products_count', { count: abc?.A || 0 })}
            </span>
          </div>
          <div className="flex flex-col items-center">
            <Badge className="bg-amber-100 text-amber-800 mb-1">{t('abc.class_b')}</Badge>
            <span className="font-semibold tabular-nums">
              {t('abc.products_count', { count: abc?.B || 0 })}
            </span>
          </div>
          <div className="flex flex-col items-center">
            <Badge className="bg-gray-100 text-gray-600 mb-1">{t('abc.class_c')}</Badge>
            <span className="font-semibold tabular-nums">
              {t('abc.products_count', { count: abc?.C || 0 })}
            </span>
          </div>
        </div>

        {/* Info-box overlay (3-part) */}
        {showInfo && (
          <div className="absolute inset-0 bg-card/95 backdrop-blur-sm rounded-lg p-4 overflow-y-auto">
            <div className="flex items-start justify-between mb-2">
              <h4 className="text-sm font-semibold">{t('abc.title')}</h4>
              <button
                type="button"
                onClick={() => setShowInfo(false)}
                className="text-muted-foreground hover:text-foreground"
                aria-label="Close"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="space-y-2 text-xs">
              <div>
                <p className="font-semibold text-muted-foreground">{t('infoBox.def', 'Definizione')}</p>
                <p>{t('abc.def')}</p>
              </div>
              <div>
                <p className="font-semibold text-muted-foreground">{t('infoBox.calc', 'Calcolo')}</p>
                <p>{t('abc.calc')}</p>
              </div>
              <div>
                <p className="font-semibold text-muted-foreground">{t('infoBox.read', 'Come leggerlo')}</p>
                <p>{t('abc.read')}</p>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
