/**
 * AdminPageShell — SA-R (10/9/2026 sera, founder: «l'area system admin
 * è un mappazzone: pagine specifiche nel menu laterale, esperienza
 * semplice»).
 *
 * Lo scheletro unico delle pagine del system admin: testata, avviso
 * «area riservata», tab dichiarati come dati e sincronizzati con
 * `?tab=` (link profondi dalle email e dal pannello restano validi).
 * Ogni pagina e' una lista di tab: niente logica qui dentro.
 */
import React from 'react';
import { useSearchParams } from 'react-router-dom';
import { AlertTriangle } from 'lucide-react';
import { AppLayout, Header } from '../../components/Layout';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../components/ui/tabs';

export default function AdminPageShell({ title, subtitle, tabs, testid = 'admin-page' }) {
  const [params, setParams] = useSearchParams();
  const richiesto = params.get('tab');
  const attivo = tabs.some((t) => t.value === richiesto) ? richiesto : tabs[0].value;
  const cambia = (v) => {
    const next = new URLSearchParams(params);
    next.set('tab', v);
    setParams(next, { replace: true });
  };
  return (
    <AppLayout>
      <Header title={title} subtitle={subtitle}>
        <div className="flex items-center gap-1.5 rounded-md bg-red-50 border border-red-200 px-2.5 py-1 text-xs font-medium text-red-700 shrink-0">
          <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
          <span className="hidden sm:inline">Area riservata</span>
        </div>
      </Header>
      <div className="p-4 md:p-8 animate-fade-in" data-testid={testid}>
        {tabs.length > 1 ? (
          <Tabs value={attivo} onValueChange={cambia}>
            <TabsList className="mb-6 w-full sm:w-auto overflow-x-auto scrollbar-hide justify-start">
              {tabs.map((t) => (
                <TabsTrigger key={t.value} value={t.value} className="flex items-center gap-2 shrink-0"
                             data-testid={`admin-tab-${t.value}`}>
                  {t.icon ? <t.icon className="h-4 w-4" /> : null}
                  {t.label}
                </TabsTrigger>
              ))}
            </TabsList>
            {tabs.map((t) => (
              <TabsContent key={t.value} value={t.value}>{t.element}</TabsContent>
            ))}
          </Tabs>
        ) : tabs[0].element}
      </div>
    </AppLayout>
  );
}
