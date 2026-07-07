/**
 * OperatorsMapView — AN3: gli organizzatori sulla mappa.
 * Gemella di RetreatsMapView (Leaflet+OSM): pin dalla POSIZIONE DEL
 * PROFILO (public_profile.latitude/longitude), popup → /o/{slug}.
 * Chi non ha configurato la località non compare qui (resta in lista).
 */
import React, { useEffect } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png';
import markerIcon from 'leaflet/dist/images/marker-icon.png';
import markerShadow from 'leaflet/dist/images/marker-shadow.png';

L.Icon.Default.mergeOptions({
  iconRetinaUrl: markerIcon2x,
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
});

function FitBounds({ points }) {
  const map = useMap();
  useEffect(() => {
    if (!points.length) return;
    if (points.length === 1) {
      map.setView(points[0], 11);
    } else {
      map.fitBounds(L.latLngBounds(points), { padding: [40, 40] });
    }
  }, [points, map]);
  return null;
}

export default function OperatorsMapView({ items }) {
  const { t } = useTranslation('landings');
  const pinned = items.filter(i => i.latitude != null && i.longitude != null);
  const points = pinned.map(i => [i.latitude, i.longitude]);

  if (!pinned.length) {
    return (
      <p className="text-sm text-gray-500 py-16 text-center">
        {t('operators.mapEmpty', { defaultValue: 'Nessun organizzatore con posizione sulla mappa per questi filtri.' })}
      </p>
    );
  }

  return (
    <div className="rounded-2xl overflow-hidden border border-gray-200" style={{ height: 520 }}>
      <MapContainer center={points[0]} zoom={7} style={{ height: '100%', width: '100%' }}>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <FitBounds points={points} />
        {pinned.map(op => (
          <Marker key={op.org_slug} position={[op.latitude, op.longitude]}>
            <Popup>
              <div className="min-w-[180px]">
                <p className="font-semibold text-sm mb-0.5">
                  {op.featured && <span className="text-[#376254]">✦ </span>}{op.name}
                </p>
                <p className="text-xs text-gray-600 mb-1">
                  {[op.city, op.region].filter(Boolean).join(', ')}
                  {op.distance_km != null && <> · {op.distance_km} km</>}
                </p>
                {op.upcoming_retreats > 0 && (
                  <p className="text-xs text-gray-700 mb-1.5">
                    {t('operators.retreatCount', { count: op.upcoming_retreats, defaultValue: '{{count}} ritiri in programma' })}
                  </p>
                )}
                <Link to={`/o/${op.org_slug}`} className="text-xs font-semibold text-primary underline">
                  {t('operators.mapSee', { defaultValue: 'Vedi il profilo →' })}
                </Link>
              </div>
            </Popup>
          </Marker>
        ))}
      </MapContainer>
    </div>
  );
}
