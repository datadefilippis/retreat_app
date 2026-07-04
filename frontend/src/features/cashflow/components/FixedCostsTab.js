import React from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../../components/ui/card';
import { Badge } from '../../../components/ui/badge';
import { Skeleton } from '../../../components/ui/skeleton';
import { formatCurrency, chartTickFormatter } from '../../../lib/utils';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts';
import { PinToDashboardButton } from '../../dashboard/PinToDashboardButton';
import { useTranslation } from 'react-i18next';

const FREQUENCY_LABELS = {
  monthly:   'Mensile',
  weekly:    'Settimanale',
  quarterly: 'Trimestrale',
  annual:    'Annuale',
  one_off:   'Una tantum',
};

const FREQUENCY_COLORS = {
  monthly:   'bg-blue-100 text-blue-800',
  weekly:    'bg-purple-100 text-purple-800',
  quarterly: 'bg-orange-100 text-orange-800',
  annual:    'bg-green-100 text-green-800',
  one_off:   'bg-gray-100 text-gray-700',
};

/**
 * FixedVsVariableChart — stacked bar showing fixed costs vs variable expenses.
 *
 * Props:
 *   fixedCostsTotal   — float from enriched KPIs
 *   variableExpenses  — float (total_expenses from enriched KPIs)
 *   widgetKey / isPinned / onTogglePin — dashboard pin support
 */
export const FixedVsVariableChart = ({ fixedCostsTotal, variableExpenses, widgetKey, isPinned, onTogglePin, currency = 'EUR' }) => {
  const { t } = useTranslation('cashflow_monitor');
  const data = [
    {
      name: 'Composizione Spese',
      'Costi Fissi': fixedCostsTotal ?? 0,
      'Spese Variabili': variableExpenses ?? 0,
    },
  ];

  return (
    <Card className="border border-border">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="font-heading text-lg">{t('fixed_costs_tab.chart_title')}</CardTitle>
            <CardDescription>
              Costi fissi proratizzati al periodo vs spese variabili da file
            </CardDescription>
          </div>
          {widgetKey && onTogglePin && (
            <PinToDashboardButton widgetKey={widgetKey} isPinned={isPinned} onToggle={onTogglePin} />
          )}
        </div>
      </CardHeader>
      <CardContent>
        <div className="h-48">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
              <XAxis
                type="number"
                tickFormatter={(v) => chartTickFormatter(v, currency)}
                stroke="#94A3B8"
                fontSize={12}
              />
              <YAxis type="category" dataKey="name" stroke="#94A3B8" fontSize={12} width={140} />
              <Tooltip formatter={(v) => formatCurrency(v, currency)} />
              <Legend />
              <Bar dataKey="Costi Fissi" stackId="a" fill="#8B5CF6" radius={[0, 0, 0, 0]} />
              <Bar dataKey="Spese Variabili" stackId="a" fill="#EF4444" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
};


/**
 * FixedCostsTab — shows fixed cost list + fixed vs variable chart.
 *
 * Props:
 *   fixedCosts        — array from GET /fixed-costs
 *   fixedCostsTotal   — float from enriched KPIs (prorated to period)
 *   variableExpenses  — float (total_expenses from enriched KPIs)
 *   loading           — skeleton mode
 */
export const FixedCostsTab = ({
  fixedCosts,
  fixedCostsTotal,
  variableExpenses,
  loading,
  fixedVsVariableWidgetKey,
  isFixedVsVariablePinned,
  onTogglePin,
  currency = 'EUR',
}) => {
  const { t } = useTranslation('cashflow_monitor');
  return (
    <div className="mt-6 space-y-6">
      {/* Summary cards */}
      <div className="grid gap-4 sm:grid-cols-3">
        <Card className="border border-border">
          <CardContent className="p-4">
            <p className="text-sm text-muted-foreground">Costi Fissi nel Periodo</p>
            {loading ? <Skeleton className="h-8 w-28 mt-1" /> : (
              <p className="text-2xl font-bold">{formatCurrency(fixedCostsTotal ?? 0, currency)}</p>
            )}
            <p className="text-xs text-muted-foreground mt-1">Proratizzati</p>
          </CardContent>
        </Card>
        <Card className="border border-border">
          <CardContent className="p-4">
            <p className="text-sm text-muted-foreground">Spese Variabili</p>
            {loading ? <Skeleton className="h-8 w-28 mt-1" /> : (
              <p className="text-2xl font-bold text-red-600">{formatCurrency(variableExpenses ?? 0, currency)}</p>
            )}
            <p className="text-xs text-muted-foreground mt-1">Da file caricati</p>
          </CardContent>
        </Card>
        <Card className="border border-border">
          <CardContent className="p-4">
            <p className="text-sm text-muted-foreground">Costi Fissi Attivi</p>
            {loading ? <Skeleton className="h-8 w-16 mt-1" /> : (
              <p className="text-2xl font-bold">{fixedCosts?.length ?? 0}</p>
            )}
            <p className="text-xs text-muted-foreground mt-1">Voci registrate</p>
          </CardContent>
        </Card>
      </div>

      {/* Fixed vs Variable chart */}
      <FixedVsVariableChart
        fixedCostsTotal={fixedCostsTotal}
        variableExpenses={variableExpenses}
        widgetKey={fixedVsVariableWidgetKey}
        isPinned={isFixedVsVariablePinned}
        onTogglePin={onTogglePin}
        currency={currency}
      />

      {/* Fixed costs list */}
      <Card className="border border-border">
        <CardHeader className="pb-2">
          <CardTitle className="font-heading text-lg">{t('fixed_costs_tab.table_title')}</CardTitle>
          <CardDescription>
            Gestisci i costi fissi dalla sezione Impostazioni → Costi Fissi
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="space-y-3">
              {[1, 2, 3].map((i) => <Skeleton key={i} className="h-14 w-full" />)}
            </div>
          ) : fixedCosts?.length > 0 ? (
            <div className="divide-y">
              {fixedCosts.map((cost) => (
                <div key={cost.id} className="flex items-center justify-between py-3">
                  <div className="flex-1 min-w-0">
                    <p className="font-medium truncate">{cost.name}</p>
                    <p className="text-xs text-muted-foreground">
                      {cost.category ?? 'Senza categoria'}
                      {cost.description ? ` · ${cost.description}` : ''}
                    </p>
                  </div>
                  <div className="flex items-center gap-3 ml-4">
                    <Badge className={FREQUENCY_COLORS[cost.frequency] ?? 'bg-gray-100 text-gray-700'}>
                      {FREQUENCY_LABELS[cost.frequency] ?? cost.frequency}
                    </Badge>
                    <span className="font-semibold tabular-nums">
                      {formatCurrency(cost.amount, currency)}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="py-12 text-center text-muted-foreground">
              <p className="font-medium">Nessun costo fisso registrato</p>
              <p className="text-sm mt-1">
                Aggiungi affitti, abbonamenti e altri costi ricorrenti per una visione completa della cassa.
              </p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default FixedCostsTab;
