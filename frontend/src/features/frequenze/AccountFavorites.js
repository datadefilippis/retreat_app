/**
 * Le mie meditazioni — sezione preferiti dentro /account (FQ3).
 *
 * Componente ISOLATO del modulo Frequenze innestato nell'hub account:
 * carica da solo, stile del mondo marketplace (non fqz); vuoto mostra
 * l'invito (RF 8/10: nell'hub ogni sezione esiste sempre). L'hub consolidato non cambia:
 * un import e una riga.
 */
import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import platformApi from '../../api/platformClient';

const INTENTS = {
  dormire: 'Dormire', meditare: 'Meditare', rilassare: 'Rilassare',
  concentrare: 'Concentrare', elaborare: 'Elaborare', energizzare: 'Energizzare',
};

export default function AccountFavorites() {
  const [items, setItems] = useState([]);

  useEffect(() => {
    platformApi.get('/frequencies/favorites')
      .then((r) => setItems(r.data.items || []))
      .catch(() => { /* sezione silenziosa se l'endpoint non risponde */ });
  }, []);

  // RF (8/10/2026, founder): nell'hub ogni cosa ha la sua sezione anche
  // quando e' vuota, con l'invito — prima qui non c'era nulla e la tessera
  // «Meditazioni» atterrava sulla sezione dopo
  if (!items.length) {
    return (
      <section data-testid="account-meditations">
        <h2 className="text-sm font-semibold text-gray-900 mb-2">Le mie meditazioni</h2>
        <div className="rounded-2xl border border-dashed border-gray-300 bg-white p-5 text-center" data-testid="account-meditations-vuoto">
          <p className="text-sm text-gray-600">Nessuna meditazione salvata ancora. Ascolta su Aurya Sound e tocca il cuore: le ritrovi qui.</p>
          <Link to="/meditazioni" className="mt-2 inline-block text-sm font-medium text-primary hover:underline">Scopri le meditazioni →</Link>
        </div>
      </section>
    );
  }

  return (
    <section data-testid="account-meditations">
      <h2 className="text-sm font-semibold text-gray-900 mb-2">
        Le mie meditazioni
      </h2>
      <div className="space-y-2">
        {items.map((t) => (
          <Link key={t.slug} to={`/frequenze/${t.slug}`}
            className="flex items-center justify-between rounded-xl border border-gray-200 bg-white px-4 py-3 hover:bg-gray-50 transition-colors">
            <div className="text-sm">
              <p className="font-semibold text-gray-900">♥ {t.title}</p>
              <p className="text-xs text-gray-600">
                {t.intent ? `${INTENTS[t.intent] || t.intent} · ` : ''}
                {Math.round((t.duration_sec || 0) / 60)} min
              </p>
            </div>
            <span className="text-xs text-primary font-medium">Ascolta →</span>
          </Link>
        ))}
      </div>
      <Link to="/meditazioni" className="inline-block mt-2 text-sm font-medium text-primary hover:underline">
        Tutte le meditazioni →
      </Link>
    </section>
  );
}
