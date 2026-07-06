/**
 * RetreatsMapView — la directory sulla mappa (G3). Leaflet+OSM gratis.
 * Marker per ogni ritiro con pin; popup = mini-card → landing.
 * Gli eventi senza coordinate non compaiono qui (restano in lista).
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

export default function RetreatsMapView({ items }) {
  const { t, i18n } = useTranslation('landings');
  const pinned = items.filter(i => i.latitude != null && i.longitude != null);
  const points = pinned.map(i => [i.latitude, i.longitude]);

  if (!pinned.length) {
    return (
      <p className="text-sm text-gray-500 py-16 text-center">
        {t('calendar.mapEmpty', { defaultValue: 'Nessun ritiro con posizione sulla mappa per questi filtri.' })}
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
        {pinned.map(item => (
          <Marker key={item.url} position={[item.latitude, item.longitude]}>
            <Popup>
              <div className="min-w-[180px]">
                <p className="font-semibold text-sm mb-0.5">{item.title}</p>
                <p className="text-xs text-gray-600 mb-1">
                  {item.start_at && new Date(item.start_at).toLocaleDateString(
                    i18n.language, { day: 'numeric', month: 'short', year: 'numeric' })}
                  {item.city && <> · {item.city}</>}
                </p>
                {item.price_from != null && (
                  <p className="text-xs text-gray-700 mb-1.5">
                    {t('calendar.fromPrice', { defaultValue: 'da {{price}} €', price: item.price_from })}
                  </p>
                )}
                <Link to={item.url} className="text-xs font-semibold text-primary underline">
                  {t('calendar.mapSee', { defaultValue: 'Vedi il ritiro →' })}
                </Link>
              </div>
            </Popup>
          </Marker>
        ))}
      </MapContainer>
    </div>
  );
}
