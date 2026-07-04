import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { AppLayout, Header } from '../components/Layout';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Skeleton } from '../components/ui/skeleton';
import { modulesAPI } from '../api';
import {
  TrendingUp,
  LineChart,
  PiggyBank,
  Package,
  CheckCircle2,
  Lock,
  ArrowRight
} from 'lucide-react';
import { toast } from 'sonner';
import { useTranslation } from 'react-i18next';

const iconMap = {
  TrendingUp,
  LineChart,
  PiggyBank,
  Package
};

export const ModulesPage = () => {
  const { t } = useTranslation('modules_page');
  const [availableModules, setAvailableModules] = useState([]);
  const [activeModules, setActiveModules] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();
  const notifyModulesChanged = () => window.dispatchEvent(new Event('modules-changed'));

  const fetchModules = async () => {
    setLoading(true);
    try {
      const [availableRes, activeRes] = await Promise.all([
        modulesAPI.listAvailable(),
        modulesAPI.listActive()
      ]);
      setAvailableModules(availableRes.data);
      setActiveModules(activeRes.data);
    } catch (error) {
      toast.error(t('toast.load_error'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchModules();
  }, []);

  // Co-activation descriptions — i18n keys (not hardcoded strings)
  const CO_ACTIVATE_KEYS = {
    commerce: 'confirm.activate_commerce',
    customers_light: 'confirm.activate_customers_light',
  };

  const handleActivate = async (moduleKey) => {
    const descKey = CO_ACTIVATE_KEYS[moduleKey];
    if (descKey && !window.confirm(t(descKey) + '\n\n' + t('confirm.proceed'))) return;
    try {
      await modulesAPI.activate(moduleKey);
      toast.success(t('toast.activated'));
      fetchModules();
      notifyModulesChanged();
    } catch (error) {
      toast.error(error.response?.data?.detail || t('toast.activate_error'));
    }
  };

  const handleDeactivate = async (moduleKey, moduleName) => {
    let confirmMsg = t('confirm.deactivate', { name: moduleName });
    if (moduleKey === 'cashflow_monitor') {
      confirmMsg += '\n\n' + t('confirm.deactivate_cashflow');
    }
    if (!window.confirm(confirmMsg)) return;
    try {
      await modulesAPI.deactivate(moduleKey);
      toast.success(t('toast.deactivated'));
      fetchModules();
      notifyModulesChanged();
    } catch (error) {
      toast.error(error.response?.data?.detail || t('toast.deactivate_error'));
    }
  };

  const activeKeySet = new Set(activeModules.map(m => m.module_key));

  // Central mapping: module_key → frontend route.
  // Keys use underscores (backend), routes use hyphens (React Router).
  const MODULE_ROUTES = {
    'cashflow_monitor':  '/modules/cashflow',
    'customers_light':   '/modules/customers-light',
    'product_catalog':   '/modules/product-catalog',
  };
  const getModulePath = (moduleKey) => MODULE_ROUTES[moduleKey] || null;

  // ── Catalog helpers: resolve localized name / description / category ────────
  // Falls back to the backend-provided value for unknown modules.
  const moduleName = (key, fallback) => t(`catalog.${key}.name`, fallback);
  const moduleDesc = (key, fallback) => t(`catalog.${key}.desc`, fallback);
  const moduleCat  = (key, fallback) => t(`catalog.${key}.category`, fallback);
  const moduleUnlocks = (key) => t(`catalog.${key}.unlocks`, { defaultValue: '' });

  // Hidden modules: commerce_signals (integrated into customers_light) + future placeholders
  const HIDDEN_MODULES = new Set(['commerce_signals', 'revenue_forecasting', 'expense_optimizer', 'inventory_tracker']);

  // ── Filter: available section excludes modules already active + hidden ─────
  const inactiveModules = availableModules.filter(m => !activeKeySet.has(m.key) && !HIDDEN_MODULES.has(m.key));

  return (
    <AppLayout>
      <Header title={t('page.title')} subtitle={t('page.subtitle')} />

      <div className="page-container section-gap animate-fade-in">
        {/* ── Active Modules ── */}
        {activeModules.filter(m => !HIDDEN_MODULES.has(m.module_key)).length > 0 && (
          <div>
            <h2 className="font-heading text-lg font-semibold mb-4">{t('sections.active_modules')}</h2>
            <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
              {activeModules.filter(m => !HIDDEN_MODULES.has(m.module_key)).map((module) => {
                const Icon = iconMap[module.icon] || TrendingUp;
                const path = getModulePath(module.module_key);
                return (
                  <Card
                    key={module.id}
                    className={`border border-green-200 bg-green-50/50 transition-colors ${path ? 'cursor-pointer hover:border-green-300' : ''}`}
                    onClick={() => path && navigate(path)}
                    data-testid={`active-module-${module.module_key}`}
                  >
                    <CardContent className="p-6">
                      <div className="flex items-start justify-between">
                        <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-green-100">
                          <Icon className="h-6 w-6 text-green-600" />
                        </div>
                        <Badge className="bg-green-100 text-green-800">
                          <CheckCircle2 className="h-3 w-3 mr-1" />
                          {t('status.active')}
                        </Badge>
                      </div>
                      <h3 className="mt-4 font-heading text-lg font-semibold">
                        {moduleName(module.module_key, module.name)}
                      </h3>
                      <p className="mt-2 text-sm text-muted-foreground line-clamp-2">
                        {moduleDesc(module.module_key, module.description)}
                      </p>
                      {moduleUnlocks(module.module_key) && (
                        <p className="mt-2 text-xs text-green-700">{moduleUnlocks(module.module_key)}</p>
                      )}
                      <div className="mt-4 space-y-2">
                        {path && (
                          <Button
                            variant="outline"
                            className="w-full"
                            data-testid={`open-module-${module.module_key}`}
                          >
                            {t('actions.open_module')}
                            <ArrowRight className="ml-2 h-4 w-4" />
                          </Button>
                        )}
                        <Button
                          variant="outline"
                          size="sm"
                          className="w-full text-xs text-muted-foreground hover:text-red-600 hover:border-red-200"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDeactivate(module.module_key, moduleName(module.module_key, module.name));
                          }}
                          data-testid={`deactivate-module-${module.module_key}`}
                        >
                          {t('actions.deactivate')}
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          </div>
        )}

        {/* ── Available / Coming Soon Modules (excludes already active) ── */}
        <div>
          <h2 className="font-heading text-lg font-semibold mb-4">{t('sections.available_modules')}</h2>
          {loading ? (
            <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
              {[1, 2, 3, 4].map((i) => (
                <Skeleton key={i} className="h-64 w-full" />
              ))}
            </div>
          ) : (
            <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
              {inactiveModules.map((module) => {
                const Icon = iconMap[module.icon] || TrendingUp;
                const isAvailable = module.is_available;

                return (
                  <Card
                    key={module.key}
                    className={`border transition-colors ${
                      isAvailable
                        ? 'border-border hover:border-primary/50'
                        : 'border-border bg-muted/30'
                    }`}
                    data-testid={`module-card-${module.key}`}
                  >
                    <CardContent className="p-6">
                      <div className="flex items-start justify-between">
                        <div className={`flex h-12 w-12 items-center justify-center rounded-lg ${
                          isAvailable ? 'bg-primary/10' : 'bg-muted'
                        }`}>
                          <Icon className={`h-6 w-6 ${
                            isAvailable ? 'text-primary' : 'text-muted-foreground'
                          }`} />
                        </div>
                        {!isAvailable && (
                          <Badge variant="outline" className="text-muted-foreground">
                            <Lock className="h-3 w-3 mr-1" />
                            {t('status.coming_soon')}
                          </Badge>
                        )}
                      </div>
                      <h3 className="mt-4 font-heading text-lg font-semibold">
                        {moduleName(module.key, module.name)}
                      </h3>
                      <Badge variant="outline" className="mt-2">
                        {moduleCat(module.key, module.category)}
                      </Badge>
                      <p className="mt-3 text-sm text-muted-foreground line-clamp-2">
                        {moduleDesc(module.key, module.description)}
                      </p>
                      {moduleUnlocks(module.key) && (
                        <p className="mt-2 text-xs text-muted-foreground italic">{moduleUnlocks(module.key)}</p>
                      )}
                      {isAvailable ? (
                        <Button
                          className="mt-4 w-full"
                          onClick={() => handleActivate(module.key)}
                          data-testid={`activate-module-${module.key}`}
                        >
                          {t('actions.activate')}
                        </Button>
                      ) : (
                        <Button
                          className="mt-4 w-full"
                          variant="outline"
                          disabled
                        >
                          {t('status.coming_soon')}
                        </Button>
                      )}
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </AppLayout>
  );
};

export default ModulesPage;
