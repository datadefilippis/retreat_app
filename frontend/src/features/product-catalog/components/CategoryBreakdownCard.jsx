/**
 * CategoryBreakdownCard — top product categories by revenue with
 * educational info-box.
 *
 * Same UX pattern as AbcDistributionCard: title + info icon, body
 * shows the data, info overlay surfaces the 3-part i18n explanation
 * when the user clicks the icon.
 *
 * Props:
 *   categories     — Array<{category, total_revenue}> sorted desc by /overview
 *   totalRevenue   — to compute % of total per row
 *   loading        — optional skeleton state
 */

import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Card, CardContent } from '../../../components/ui/card';
import { Skeleton } from '../../../components/ui/skeleton';
import { Info, X } from 'lucide-react';
import { useCurrency } from '../../../context/AuthContext';
import { formatCurrency } from '../../../lib/utils';


export default function CategoryBreakdownCard({ categories, totalRevenue, loading }) {
  const { t } = useTranslation('product_catalog');
  const currency = useCurrency();
  const [showInfo, setShowInfo] = useState(false);

  if (loading) {
    return (
      <Card>
        <CardContent className="p-4 space-y-3">
          <Skeleton className="h-4 w-32" />
          {[1,2,3,4,5].map(i => <Skeleton key={i} className="h-3 w-full" />)}
        </CardContent>
      </Card>
    );
  }

  const list = (categories || []).slice(0, 10);

  return (
    <Card className="relative">
      <CardContent className="p-4 space-y-3">
        {/* Header */}
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold">{t('categories.title')}</h3>
          <button
            type="button"
            onClick={() => setShowInfo(true)}
            aria-label={t('categories.title')}
            className="text-muted-foreground hover:text-foreground transition-colors"
          >
            <Info className="h-4 w-4" />
          </button>
        </div>

        {/* Body */}
        {list.length === 0 ? (
          <p className="text-xs text-muted-foreground italic py-4 text-center">
            {t('table.no_data')}
          </p>
        ) : (
          <div className="space-y-2">
            {list.map((c, i) => {
              const pct = totalRevenue > 0 ? (c.total_revenue / totalRevenue) * 100 : 0;
              return (
                <div key={i} className="flex items-center gap-3">
                  <span className="text-xs w-28 truncate text-muted-foreground">
                    {c.category || t('categories.no_category')}
                  </span>
                  <div className="flex-1 h-2 rounded-full bg-muted overflow-hidden">
                    <div
                      className="h-full bg-primary rounded-full"
                      style={{ width: `${Math.min(pct, 100)}%` }}
                    />
                  </div>
                  <span className="text-xs font-medium w-20 text-right tabular-nums">
                    {formatCurrency(c.total_revenue, currency)}
                  </span>
                </div>
              );
            })}
          </div>
        )}

        {/* Info-box overlay */}
        {showInfo && (
          <div className="absolute inset-0 bg-card/95 backdrop-blur-sm rounded-lg p-4 overflow-y-auto">
            <div className="flex items-start justify-between mb-2">
              <h4 className="text-sm font-semibold">{t('categories.title')}</h4>
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
                <p>{t('categories.def')}</p>
              </div>
              <div>
                <p className="font-semibold text-muted-foreground">{t('infoBox.calc', 'Calcolo')}</p>
                <p>{t('categories.calc')}</p>
              </div>
              <div>
                <p className="font-semibold text-muted-foreground">{t('infoBox.read', 'Come leggerlo')}</p>
                <p>{t('categories.read')}</p>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
