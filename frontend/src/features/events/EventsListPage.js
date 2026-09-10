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
// SR fase 0 — «Cerco una struttura per un ritiro»: l'unica cosa che il
// gestionale sa delle strutture; la risposta arriva a mano da Aurya.
import RichiestaStrutturaDialog from './components/RichiestaStrutturaDialog';


export default function EventsListPage() {
  const navigate = useNavigate();
  const { t } = useTranslation('products');
  const [pactOpen, setPactOpen] = useState(false);
  const [strutturaOpen, setStrutturaOpen] = useState(false);
  const [strutturaTipo, setStrutturaTipo] = useState('struttura');   // P13: struttura | regia
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
        <div className="flex justify-end gap-2 mb-2">
          <Button size="sm" variant="outline" onClick={() => { setStrutturaTipo('struttura'); setStrutturaOpen(true); }}
                  data-testid="events-cerca-struttura">
            Cerco una struttura
          </Button>
          {/* P13 (10/9/2026) — la regia del ritiro, stessa scheda */}
          <Button size="sm" variant="outline" onClick={() => { setStrutturaTipo('regia'); setStrutturaOpen(true); }}
                  data-testid="events-chiedi-regia">
            Chiedi la regia
          </Button>
          <RichiestaStrutturaDialog aperto={strutturaOpen} tipoIniziale={strutturaTipo} onClose={() => setStrutturaOpen(false)} />
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
