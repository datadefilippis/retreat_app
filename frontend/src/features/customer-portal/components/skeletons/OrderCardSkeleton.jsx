/**
 * OrderCardSkeleton — placeholder matching OrderCard's footprint.
 *
 * Same outer Card chrome + same vertical rhythm as OrderCard so the
 * page doesn't shift when real data arrives. Three visible elements:
 *   1. Order number line + status pill (top-left cluster)
 *   2. Date + items summary (meta line)
 *   3. Price (top-right)
 *
 * The fulfillment hint line and the "Apri corso" CTA are intentionally
 * NOT skeletoned — they're conditional on the real order data, so
 * placeholders for them would over-promise content that may not exist.
 *
 * Used by OrdersPage during the initial fetch and by HomePage in the
 * "Ultimi ordini" section.
 */

import React from 'react';
import { Card, CardContent } from '../../../../components/ui/card';
import Skeleton from '../Skeleton';


export default function OrderCardSkeleton() {
  return (
    <Card>
      <CardContent className="py-3 px-4">
        <div className="flex items-center justify-between gap-3">
          <div className="space-y-1.5 min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <Skeleton className="h-3.5 w-24" />
              <Skeleton className="h-4 w-16 rounded-full" />
            </div>
            <Skeleton.Text width="70%" />
          </div>
          <Skeleton className="h-4 w-16 shrink-0" />
        </div>
      </CardContent>
    </Card>
  );
}
