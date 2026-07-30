/**
 * EventsListPage — /events (RS1, 28/7/2026).
 * docs/RITIRI_INTEGRITA_PIANO_2026-07.md
 *
 * La casa dei ritiri nel back-office: SOLO ritiri, dentro la shell
 * dell'app (AppLayout), col linguaggio dell'operatore. Niente hub
 * multi-tipo: ProductsPage resta viva su /products per le org con
 * commerce legacy (R1/R5 del piano Listino).
 */

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Plus } from 'lucide-react';
import { AppLayout, Header } from '../../components/Layout';
import { Button } from '../../components/ui/button';
import EventsGrid from './components/EventsGrid';
// PV7 — patto di responsabilita' (DPA art. 28): banner ben visibile
// finche' non firmato; la firma vera avviene nel dialog (o al gate di
// creazione dentro EventWizard). Stato condiviso via useDpaStatus.
import DpaPactBanner from '../../components/legal/DpaPactBanner';
import DpaPactDialog from '../../components/legal/DpaPactDialog';


export default function EventsListPage() {
  const navigate = useNavigate();
  const { t } = useTranslation('products');
  const [pactOpen, setPactOpen] = useState(false);
  return (
    <AppLayout>
      <Header
        title={t('grids.event.title', { defaultValue: 'Ritiri' })}
        subtitle={t('grids.event.subtitle', {
          defaultValue: "Gestisci tutti i tuoi ritiri, date e check-in in un'unica schermata.",
        })}
      />
      <div className="p-4 md:p-8" data-testid="events-home">
        <DpaPactBanner className="mb-3" onRead={() => setPactOpen(true)} />
        <DpaPactDialog open={pactOpen} onOpenChange={setPactOpen} />
        <div className="flex justify-end mb-2">
          <Button size="sm" onClick={() => navigate('/events/new')}
                  data-testid="events-new-cta">
            <Plus className="mr-1.5 h-4 w-4" />
            {t('grids.event.createCta', { defaultValue: 'Crea un ritiro' })}
          </Button>
        </div>
        {/* embedded: la griglia porta filtri, stati e card; il titolo
            e la CTA li mette questa pagina */}
        <EventsGrid embedded onCreateClick={() => navigate('/events/new')} />
      </div>
    </AppLayout>
  );
}
