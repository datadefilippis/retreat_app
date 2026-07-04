/**
 * OrderDetailSkeleton — placeholder matching OrderDetailPage layout.
 *
 * The real page renders (top to bottom):
 *   1. Page header with order number + status badge
 *   2. (Conditional) blue course CTA banner
 *   3. (Conditional) fulfillment card
 *   4. Items card with line-by-line breakdown + total
 *   5. (Conditional) notes card
 *
 * The skeleton shows just (1) + (4) because they're always present —
 * the conditional sections would create visual flicker if a "phantom
 * banner" disappeared once the real data revealed the order didn't
 * have that section.
 *
 * Used by OrderDetailPage during the per-order fetch.
 */

import React from 'react';
import { Card, CardContent, CardHeader } from '../../../../components/ui/card';
import Skeleton from '../Skeleton';


export default function OrderDetailSkeleton() {
  return (
    <div className="space-y-4" role="status" aria-busy="true" aria-label="Caricamento ordine">
      {/* Page header — order number + date + status */}
      <div className="flex items-center justify-between">
        <div className="space-y-2 flex-1">
          <Skeleton className="h-6 w-40" />
          <Skeleton.Text width="50%" />
        </div>
        <Skeleton className="h-5 w-20 rounded-full" />
      </div>

      {/* Items card */}
      <Card>
        <CardHeader className="pb-2">
          <Skeleton className="h-4 w-20" />
        </CardHeader>
        <CardContent className="space-y-3">
          {[1, 2, 3].map(i => (
            <div key={i} className="flex items-center justify-between gap-3 py-1.5 border-b last:border-0">
              <div className="flex-1 min-w-0 space-y-1.5">
                <Skeleton.Text width="65%" tall />
                <Skeleton.Text width="35%" />
              </div>
              <div className="text-right space-y-1.5 shrink-0">
                <Skeleton className="h-3 w-16 ml-auto" />
                <Skeleton className="h-3.5 w-14 ml-auto" />
              </div>
            </div>
          ))}
          {/* Total row */}
          <div className="flex items-center justify-between pt-2 border-t">
            <Skeleton className="h-4 w-16" />
            <Skeleton className="h-5 w-24" />
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
