import React, { useState, useEffect } from 'react';
import { AppLayout, Header } from '../../components/Layout';
import { PageSubheader } from '../../components/PageSubheader';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { Skeleton } from '../../components/ui/skeleton';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { alertsAPI } from '../../api';
import { formatDate } from '../../lib/utils';
import {
  AlertTriangle,
  CheckCircle2,
  Clock,
  RefreshCw,
  Filter,
  Calendar,
  Eye
} from 'lucide-react';
import { toast } from 'sonner';
import { useTranslation } from 'react-i18next';

export const AlertsPage = () => {
  const { t } = useTranslation('alerts');
  const severityLabels = { high: t('severity.high'), medium: t('severity.medium'), low: t('severity.low') };
  const statusLabels = { new: t('status.new'), acknowledged: t('status.acknowledged'), resolved: t('status.resolved') };
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('all');
  const [severityFilter, setSeverityFilter] = useState('all');
  const [categoryFilter, setCategoryFilter] = useState('all');
  const [counts, setCounts] = useState({ total: 0, new: 0, acknowledged: 0, resolved: 0 });
  const [generatingAlerts, setGeneratingAlerts] = useState(false);

  const fetchAlerts = async () => {
    setLoading(true);
    try {
      const status = statusFilter === 'all' ? undefined : statusFilter;
      const severity = severityFilter === 'all' ? undefined : severityFilter;

      const category = categoryFilter === 'all' ? undefined : categoryFilter;

      const [alertsRes, countsRes] = await Promise.all([
        alertsAPI.list(status, severity, 100, category),
        alertsAPI.getCounts()
      ]);

      setAlerts(alertsRes.data);
      setCounts(countsRes.data);
    } catch (error) {
      toast.error(t('toast.load_error'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAlerts();
  }, [statusFilter, severityFilter, categoryFilter]);

  const handleUpdateStatus = async (alertId, newStatus) => {
    try {
      await alertsAPI.updateStatus(alertId, newStatus);
      toast.success(`Anomalia ${statusLabels[newStatus]?.toLowerCase() || newStatus}`);
      fetchAlerts();
    } catch (error) {
      toast.error(t('toast.update_error'));
    }
  };

  const handleGenerateAlerts = async () => {
    setGeneratingAlerts(true);
    try {
      const response = await alertsAPI.generate();
      toast.success(`${response.data.alerts_generated} nuove anomalie rilevate`);
      fetchAlerts();
    } catch (error) {
      toast.error(t('toast.generate_error'));
    } finally {
      setGeneratingAlerts(false);
    }
  };

  const severityColors = {
    high: 'bg-red-100 text-red-800 border-red-200',
    medium: 'bg-yellow-100 text-yellow-800 border-yellow-200',
    low: 'bg-blue-100 text-blue-800 border-blue-200'
  };

  const severityAccent = {
    high: 'border-l-red-500',
    medium: 'border-l-yellow-500',
    low: 'border-l-blue-500'
  };

  const severityIcons = {
    high: <AlertTriangle className="h-4 w-4 text-red-600" />,
    medium: <AlertTriangle className="h-4 w-4 text-yellow-600" />,
    low: <AlertTriangle className="h-4 w-4 text-blue-600" />
  };

  const statusColors = {
    new: 'bg-blue-100 text-blue-800',
    acknowledged: 'bg-yellow-100 text-yellow-800',
    resolved: 'bg-green-100 text-green-800'
  };

  return (
    <AppLayout>
      <Header title={t('page.title')} subtitle={t('page.subtitle')} />
      <PageSubheader
        actions={
          <Button
            variant="outline"
            size="sm"
            onClick={handleGenerateAlerts}
            disabled={generatingAlerts}
            data-testid="run-analysis-btn"
            className="text-xs sm:text-sm"
          >
            {generatingAlerts ? (
              <>
                <RefreshCw className="h-4 w-4 mr-1.5 animate-spin" />
                <span className="hidden sm:inline">{t('actions.analyzing')}</span>
                <span className="sm:hidden">{t('actions.analyzing_short')}</span>
              </>
            ) : (
              <>
                <AlertTriangle className="h-4 w-4 mr-1.5" />
                <span className="hidden sm:inline">{t('actions.run_analysis')}</span>
                <span className="sm:hidden">{t('actions.run_analysis_short')}</span>
              </>
            )}
          </Button>
        }
      />

      <div className="p-4 md:p-8 space-y-4 md:space-y-6 animate-fade-in">
        {/* Stats Cards */}
        <div className="grid gap-3 md:gap-4 grid-cols-4">
          <Card className="border border-border">
            <CardContent className="p-3 md:p-4">
              <div className="text-[11px] md:text-sm text-muted-foreground">{t('summary.total')}</div>
              <div className="text-xl md:text-2xl font-bold">{counts.total}</div>
            </CardContent>
          </Card>
          <Card className="border border-blue-200 bg-blue-50/50">
            <CardContent className="p-3 md:p-4">
              <div className="text-[11px] md:text-sm text-blue-800">{t('summary.new')}</div>
              <div className="text-xl md:text-2xl font-bold text-blue-800">{counts.new}</div>
            </CardContent>
          </Card>
          <Card className="border border-yellow-200 bg-yellow-50/50">
            <CardContent className="p-3 md:p-4">
              <div className="text-[11px] md:text-sm text-yellow-800">{t('summary.acknowledged')}</div>
              <div className="text-xl md:text-2xl font-bold text-yellow-800">{counts.acknowledged}</div>
            </CardContent>
          </Card>
          <Card className="border border-green-200 bg-green-50/50">
            <CardContent className="p-3 md:p-4">
              <div className="text-[11px] md:text-sm text-green-800">{t('summary.resolved')}</div>
              <div className="text-xl md:text-2xl font-bold text-green-800">{counts.resolved}</div>
            </CardContent>
          </Card>
        </div>

        {/* Filters */}
        <div className="flex items-center gap-3">
          <Filter className="h-4 w-4 text-muted-foreground flex-shrink-0" />
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="flex-1 sm:w-40 sm:flex-none" data-testid="status-filter">
              <SelectValue placeholder="Stato" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">{t('filters.all_statuses')}</SelectItem>
              <SelectItem value="new">{t('filters.new')}</SelectItem>
              <SelectItem value="acknowledged">{t('filters.acknowledged')}</SelectItem>
              <SelectItem value="resolved">{t('filters.resolved')}</SelectItem>
            </SelectContent>
          </Select>
          <Select value={severityFilter} onValueChange={setSeverityFilter}>
            <SelectTrigger className="flex-1 sm:w-40 sm:flex-none" data-testid="severity-filter">
              <SelectValue placeholder="Gravità" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">{t('filters.all_severities')}</SelectItem>
              <SelectItem value="high">{t('filters.high')}</SelectItem>
              <SelectItem value="medium">{t('filters.medium')}</SelectItem>
              <SelectItem value="low">{t('filters.low')}</SelectItem>
            </SelectContent>
          </Select>
          <Select value={categoryFilter} onValueChange={setCategoryFilter}>
            <SelectTrigger className="flex-1 sm:w-48 sm:flex-none" data-testid="category-filter">
              <SelectValue placeholder={t('filters.all_categories', 'Tutte le categorie')} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">{t('filters.all_categories', 'Tutte le categorie')}</SelectItem>
              <SelectItem value="A">{t('filters.category_a', 'Liquidità')}</SelectItem>
              <SelectItem value="B">{t('filters.category_b', 'Marginalità')}</SelectItem>
              <SelectItem value="C">{t('filters.category_c', 'Ciclo di cassa')}</SelectItem>
              <SelectItem value="D">{t('filters.category_d', 'Pattern')}</SelectItem>
              <SelectItem value="E">{t('filters.category_e', 'Dipendenze')}</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Alerts List */}
        <Card className="border border-border">
          <CardContent className="p-0">
            {loading ? (
              <div className="space-y-0">
                {[1, 2, 3, 4, 5].map((i) => (
                  <div key={i} className="p-4 border-b border-border">
                    <Skeleton className="h-20 w-full" />
                  </div>
                ))}
              </div>
            ) : alerts.length > 0 ? (
              <div className="divide-y divide-border" data-testid="alerts-list">
                {alerts.map((alert) => (
                  <div
                    key={alert.id}
                    className={`p-4 hover:bg-muted/50 transition-colors border-l-4 ${severityAccent[alert.severity] || 'border-l-transparent'}`}
                  >
                    {/* ── Mobile/Tablet layout: tutto impilato verticalmente ── */}
                    <div className="lg:hidden space-y-2.5">
                      {/* Row 1: badges */}
                      <div className="flex items-center gap-2 flex-wrap">
                        <Badge className={`${severityColors[alert.severity]} text-[11px] px-2 py-0.5`}>
                          {severityIcons[alert.severity]}
                          <span className="ml-1">{severityLabels[alert.severity]}</span>
                        </Badge>
                        <Badge className={`${statusColors[alert.status]} text-[11px] px-2 py-0.5`}>
                          {statusLabels[alert.status]}
                        </Badge>
                      </div>

                      {/* Row 2: titolo */}
                      <h3 className="font-semibold text-sm leading-snug">{alert.title}</h3>

                      {/* Row 3: descrizione a tutta larghezza */}
                      <p className="text-sm text-muted-foreground leading-relaxed">{alert.summary}</p>

                      {/* Row 3b: suggested action */}
                      {alert.suggested_action && (
                        <div className="bg-blue-50 border border-blue-200 rounded-md px-3 py-2 text-sm text-blue-800">
                          <span className="font-medium">{t('actions.suggestion', 'Azione suggerita')}:</span>{' '}
                          {alert.suggested_action}
                        </div>
                      )}

                      {/* Row 4: date info */}
                      <div className="flex items-center gap-3 text-xs text-muted-foreground">
                        <span className="flex items-center gap-1">
                          <Calendar className="h-3 w-3" />
                          {alert.date_reference}
                        </span>
                        <span>·</span>
                        <span>{formatDate(alert.created_at)}</span>
                      </div>

                      {/* Row 5: bottoni a tutta larghezza */}
                      {alert.status !== 'resolved' && (
                        <div className="flex gap-2 pt-1">
                          {alert.status === 'new' && (
                            <Button
                              variant="outline"
                              size="sm"
                              className="flex-1 text-xs h-8"
                              onClick={() => handleUpdateStatus(alert.id, 'acknowledged')}
                              data-testid={`acknowledge-${alert.id}`}
                            >
                              <Eye className="h-3 w-3 mr-1.5" />
                              {t('actions.acknowledge')}
                            </Button>
                          )}
                          <Button
                            variant="outline"
                            size="sm"
                            className="flex-1 text-xs h-8"
                            onClick={() => handleUpdateStatus(alert.id, 'resolved')}
                            data-testid={`resolve-${alert.id}`}
                          >
                            <CheckCircle2 className="h-3 w-3 mr-1.5" />
                            {t('actions.resolve')}
                          </Button>
                        </div>
                      )}
                    </div>

                    {/* ── Desktop layout: icona + contenuto + bottoni su una riga ── */}
                    <div className="hidden lg:flex items-start gap-4">
                      <div className="mt-0.5 flex-shrink-0">{severityIcons[alert.severity]}</div>
                      <div className="flex-1 min-w-0">
                        <div className="flex flex-wrap items-center gap-2 mb-1.5">
                          <span className="font-semibold">{alert.title}</span>
                          <Badge className={severityColors[alert.severity]}>{severityLabels[alert.severity]}</Badge>
                          <Badge className={statusColors[alert.status]}>{statusLabels[alert.status]}</Badge>
                        </div>
                        <p className="text-sm text-muted-foreground mb-2">{alert.summary}</p>
                        {alert.suggested_action && (
                          <div className="bg-blue-50 border border-blue-200 rounded-md px-3 py-2 text-sm text-blue-800 mb-2">
                            <span className="font-medium">{t('actions.suggestion', 'Azione suggerita')}:</span>{' '}
                            {alert.suggested_action}
                          </div>
                        )}
                        <div className="flex items-center gap-4 text-xs text-muted-foreground">
                          <span className="flex items-center gap-1">
                            <Calendar className="h-3 w-3" />
                            Riferimento: {alert.date_reference}
                          </span>
                          <span>Creata: {formatDate(alert.created_at)}</span>
                        </div>
                      </div>
                      <div className="flex gap-2 flex-shrink-0">
                        {alert.status === 'new' && (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleUpdateStatus(alert.id, 'acknowledged')}
                            data-testid={`acknowledge-${alert.id}`}
                          >
                            <Eye className="h-3 w-3 mr-1" />
                            {t('actions.acknowledge')}
                          </Button>
                        )}
                        {alert.status !== 'resolved' && (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleUpdateStatus(alert.id, 'resolved')}
                            data-testid={`resolve-${alert.id}`}
                          >
                            <CheckCircle2 className="h-3 w-3 mr-1" />
                            {t('actions.resolve')}
                          </Button>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center py-16 text-center px-4">
                <div className="flex h-16 w-16 items-center justify-center rounded-full bg-green-100">
                  <CheckCircle2 className="h-8 w-8 text-green-600" />
                </div>
                <p className="mt-4 font-medium">{t('empty.title')}</p>
                <p className="text-sm text-muted-foreground mt-1">
                  {statusFilter !== 'all' || severityFilter !== 'all'
                    ? t('empty.filtered_desc')
                    : t('empty.clean_desc')}
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </AppLayout>
  );
};

export default AlertsPage;
