import React from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../../components/ui/card';
import { Badge } from '../../../components/ui/badge';
import { Button } from '../../../components/ui/button';
import { Skeleton } from '../../../components/ui/skeleton';
import { AlertTriangle, CheckCircle2, RefreshCw } from 'lucide-react';
import { PinToDashboardButton } from '../../dashboard/PinToDashboardButton';
import { useTranslation } from 'react-i18next';

const SEVERITY_STYLES = {
  high:   { badge: 'bg-red-100 text-red-800',    icon: 'text-red-600'    },
  medium: { badge: 'bg-yellow-100 text-yellow-800', icon: 'text-yellow-600' },
  low:    { badge: 'bg-blue-100 text-blue-800',   icon: 'text-blue-600'   },
};

// SEVERITY_LABELS and STATUS_LABELS are resolved inside AlertsTab via useTranslation


/**
 * AlertsTab — displays the cashflow alerts list with severity grouping.
 *
 * Props:
 *   alerts           — filtered alert array (module_key === 'cashflow_monitor')
 *   loading          — skeleton mode
 *   generatingAlerts — spinner on the "Run Analysis" button
 *   onGenerate       — () => void
 */
export const AlertsTab = ({ alerts, loading, generatingAlerts, onGenerate, alertsWidgetKey, isAlertsPinned, onTogglePin }) => {
  const { t } = useTranslation('cashflow_monitor');
  const SEVERITY_LABELS = { high: t('alerts_tab.severity_high'), medium: t('alerts_tab.severity_medium'), low: t('alerts_tab.severity_low') };
  const STATUS_LABELS = { new: t('alerts_tab.status_new'), acknowledged: t('alerts_tab.status_acknowledged'), resolved: t('alerts_tab.status_resolved') };
  const highCount   = alerts.filter((a) => a.severity === 'high').length;
  const mediumCount = alerts.filter((a) => a.severity === 'medium').length;
  const lowCount    = alerts.filter((a) => a.severity === 'low').length;

  return (
    <div className="mt-6 space-y-4">
      {/* Severity counters */}
      {!loading && alerts.length > 0 && (
        <div className="flex gap-3 flex-wrap">
          {highCount > 0 && (
            <Badge className="bg-red-100 text-red-800">
              {highCount} {t('alerts_tab.high_severity')}
            </Badge>
          )}
          {mediumCount > 0 && (
            <Badge className="bg-yellow-100 text-yellow-800">
              {mediumCount} {t('alerts_tab.medium_severity')}
            </Badge>
          )}
          {lowCount > 0 && (
            <Badge className="bg-blue-100 text-blue-800">
              {lowCount} {t('alerts_tab.low_severity')}
            </Badge>
          )}
        </div>
      )}

      <Card className="border border-border">
        <CardHeader className="flex flex-row items-center justify-between pb-4">
          <div>
            <CardTitle className="font-heading text-lg">{t('alerts_tab.title')}</CardTitle>
            <CardDescription>{t('alerts_tab.description')}</CardDescription>
          </div>
          <div className="flex items-center gap-2">
            {alertsWidgetKey && onTogglePin && (
              <PinToDashboardButton widgetKey={alertsWidgetKey} isPinned={isAlertsPinned} onToggle={onTogglePin} />
            )}
          <Button
            variant="outline"
            onClick={onGenerate}
            disabled={generatingAlerts}
            data-testid="generate-alerts-btn"
          >
            {generatingAlerts ? (
              <>
                <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                {t('alerts_tab.analyzing')}
              </>
            ) : (
              <>
                <AlertTriangle className="mr-2 h-4 w-4" />
                {t('alerts_tab.run_analysis')}
              </>
            )}
          </Button>
          </div>
        </CardHeader>

        <CardContent>
          {loading ? (
            <div className="space-y-3">
              {[1, 2, 3].map((i) => <Skeleton key={i} className="h-20 w-full" />)}
            </div>
          ) : alerts.length > 0 ? (
            <div className="space-y-3" data-testid="module-alerts-list">
              {alerts.map((alert) => {
                const style = SEVERITY_STYLES[alert.severity] ?? SEVERITY_STYLES.low;
                return (
                  <div
                    key={alert.id}
                    className="flex items-start gap-4 rounded-lg border border-border p-4"
                  >
                    <AlertTriangle className={`h-5 w-5 mt-0.5 flex-shrink-0 ${style.icon}`} />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1 flex-wrap">
                        <span className="font-medium">{alert.title}</span>
                        <Badge className={style.badge}>
                          {SEVERITY_LABELS[alert.severity] ?? alert.severity}
                        </Badge>
                        <Badge variant="outline">
                          {STATUS_LABELS[alert.status] ?? alert.status}
                        </Badge>
                      </div>
                      <p className="text-sm text-muted-foreground">{alert.summary}</p>
                      {alert.ai_analysis && (
                        <div className="mt-2 p-2.5 bg-blue-50 dark:bg-blue-950/30 rounded-md border border-blue-100 dark:border-blue-900">
                          <p className="text-[11px] font-semibold text-blue-800 dark:text-blue-300 mb-0.5">{t('alerts_tab.ai_analysis')}</p>
                          <p className="text-xs text-blue-700 dark:text-blue-400 leading-relaxed">{alert.ai_analysis}</p>
                        </div>
                      )}
                      <p className="text-xs text-muted-foreground mt-1">
                        {t('alerts_tab.reference')}{alert.date_reference}
                      </p>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <CheckCircle2 className="h-12 w-12 text-green-600" />
              <p className="mt-4 font-medium">{t('alerts_tab.no_alerts_title')}</p>
              <p className="text-sm text-muted-foreground">
                {t('alerts_tab.no_alerts_desc')}
              </p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default AlertsTab;
