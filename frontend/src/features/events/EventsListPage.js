/**
 * EventsListPage — thin wrapper kept for backward-compat on the
 * /events route. After Onda 7 M1 the real implementation lives in
 * the shared <EventsGrid /> component so it can also be embedded
 * inside ProductsPage (the canonical "prodotti hub" entry).
 *
 * Once the redirect from /events to /products?type=event_ticket is
 * verified stable, this file can be removed entirely in favour of
 * the embedded view. Kept for now so direct bookmarks still open
 * a recognisable surface with "+ Nuovo evento" CTA.
 */

import React from 'react';
import { useNavigate } from 'react-router-dom';
import EventsGrid from './components/EventsGrid';


export default function EventsListPage() {
  const navigate = useNavigate();
  return (
    <EventsGrid
      embedded={false}
      onCreateClick={() => navigate('/events/new')}
    />
  );
}
