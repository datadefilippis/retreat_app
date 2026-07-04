import React from 'react';
import { Link } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../../components/ui/card';
import { Badge } from '../../../components/ui/badge';
import { Lightbulb, AlertTriangle, CheckCircle2, ArrowRight } from 'lucide-react';
import { formatDate } from '../../../lib/utils';

/**
 * LatestInsightWidget — compact read-only card showing the latest AI insight.
 * Designed for the dashboard. Shows title, date and a truncated preview.
 *
 * Props:
 *   insight  — latest Insight object from overview.last_insight (or null)
 *   loading  — skeleton mode
 */
export const LatestInsightWidget = ({ insight, loading }) => {
  if (loading) {
    return (
      <Card className="border border-border">
        <CardContent className="p-5 space-y-2">
          <div className="h-4 w-32 bg-muted rounded animate-pulse" />
          <div className="h-4 w-full bg-muted rounded animate-pulse" />
          <div className="h-4 w-3/4 bg-muted rounded animate-pulse" />
        </CardContent>
      </Card>
    );
  }

  if (!insight) {
    return (
      <Card className="border border-border">
        <CardContent className="p-5 flex flex-col items-center justify-center py-10 text-center">
          <Lightbulb className="h-8 w-8 text-muted-foreground/50" />
          <p className="mt-3 text-sm text-muted-foreground">
            Nessuna analisi disponibile
          </p>
          <Link to="/modules/cashflow" className="mt-2 text-xs text-primary hover:underline flex items-center gap-1">
            Genera dal Cashflow Monitor <ArrowRight className="h-3 w-3" />
          </Link>
        </CardContent>
      </Card>
    );
  }

  // Truncate content to ~200 chars for compact display
  const preview = insight.content?.length > 200
    ? insight.content.slice(0, 200) + '…'
    : insight.content;

  return (
    <Card className="border border-border">
      <CardHeader className="pb-2">
        <CardTitle className="font-heading text-lg flex items-center gap-2">
          <Lightbulb className="h-4 w-4 text-yellow-500" />
          Ultima Analisi AI
        </CardTitle>
        <CardDescription>
          {formatDate(insight.created_at)} · {formatDate(insight.period_start)} → {formatDate(insight.period_end)}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <p className="text-sm leading-relaxed text-muted-foreground whitespace-pre-wrap">
          {preview}
        </p>
        <Link to="/modules/cashflow" className="mt-3 text-xs text-primary hover:underline flex items-center gap-1">
          Vedi analisi completa <ArrowRight className="h-3 w-3" />
        </Link>
      </CardContent>
    </Card>
  );
};


/**
 * AlertsSummaryWidget — compact card showing alert counts by severity.
 * Designed for the dashboard. Links to the full AlertsTab.
 *
 * Props:
 *   alerts   — array of alert objects (already filtered by module_key)
 *   loading  — skeleton mode
 */
export const AlertsSummaryWidget = ({ alerts, loading }) => {
  if (loading) {
    return (
      <Card className="border border-border">
        <CardContent className="p-5 space-y-2">
          <div className="h-4 w-32 bg-muted rounded animate-pulse" />
          <div className="h-6 w-full bg-muted rounded animate-pulse" />
        </CardContent>
      </Card>
    );
  }

  const alertList = alerts || [];
  const highCount   = alertList.filter((a) => a.severity === 'high').length;
  const mediumCount = alertList.filter((a) => a.severity === 'medium').length;
  const lowCount    = alertList.filter((a) => a.severity === 'low').length;

  return (
    <Card className="border border-border">
      <CardHeader className="pb-2">
        <CardTitle className="font-heading text-lg flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 text-yellow-500" />
          Anomalie Rilevate
        </CardTitle>
        <CardDescription>{alertList.length} alert attivi</CardDescription>
      </CardHeader>
      <CardContent>
        {alertList.length > 0 ? (
          <div className="space-y-3">
            <div className="flex gap-2 flex-wrap">
              {highCount > 0 && (
                <Badge className="bg-red-100 text-red-800">
                  {highCount} alta
                </Badge>
              )}
              {mediumCount > 0 && (
                <Badge className="bg-yellow-100 text-yellow-800">
                  {mediumCount} media
                </Badge>
              )}
              {lowCount > 0 && (
                <Badge className="bg-blue-100 text-blue-800">
                  {lowCount} bassa
                </Badge>
              )}
            </div>
            {/* Show first 2 alert titles */}
            <div className="space-y-1">
              {alertList.slice(0, 2).map((alert) => (
                <p key={alert.id} className="text-sm text-muted-foreground truncate">
                  • {alert.title}
                </p>
              ))}
              {alertList.length > 2 && (
                <p className="text-xs text-muted-foreground">
                  + {alertList.length - 2} altri alert
                </p>
              )}
            </div>
          </div>
        ) : (
          <div className="flex items-center gap-2 py-4">
            <CheckCircle2 className="h-5 w-5 text-green-600" />
            <span className="text-sm text-muted-foreground">Nessuna anomalia rilevata</span>
          </div>
        )}
        <Link to="/modules/cashflow" className="mt-3 text-xs text-primary hover:underline flex items-center gap-1">
          Vai alle anomalie <ArrowRight className="h-3 w-3" />
        </Link>
      </CardContent>
    </Card>
  );
};
