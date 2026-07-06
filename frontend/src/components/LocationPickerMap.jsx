/**
 * LocationPickerMap — il pin che si sistema da solo (G2,
 * docs/GEO_SEARCH_PLAN.md). Leaflet + OpenStreetMap: gratis, zero key.
 *
 * Comportamento:
 *  - `geocodeQuery` (città/indirizzo, debounced dal chiamante) →
 *    GET /event-occurrences/geocode (cache Nominatim nel backend) →
 *    il pin appare/si sposta
 *  - il PIN È L'INPUT: trascinandolo si aggiornano lat/lng (onChange)
 *    e il geocoding smette di sovrascrivere finché la query non cambia
 *  - senza coordinate né query: placeholder discreto, niente mappa
 */
import React, { useEffect, useRef, useState } from 'react';
import { MapContainer, TileLayer, Marker, useMap } from 'react-leaflet';
import { useTranslation } from 'react-i18next';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import api from '../api/client';

// Fix icone default Leaflet sotto webpack/CRA (path degli asset)
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png';
import markerIcon from 'leaflet/dist/images/marker-icon.png';
import markerShadow from 'leaflet/dist/images/marker-shadow.png';

L.Icon.Default.mergeOptions({
  iconRetinaUrl: markerIcon2x,
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
});

function Recenter({ lat, lng }) {
  const map = useMap();
  useEffect(() => {
    if (lat != null && lng != null) map.setView([lat, lng], map.getZoom());
  }, [lat, lng, map]);
  return null;
}

export default function LocationPickerMap({ latitude, longitude, onChange, geocodeQuery }) {
  const { t } = useTranslation('products');
  const [geocoding, setGeocoding] = useState(false);
  // dopo un drag manuale il geocoding non sovrascrive più il pin,
  // finché la query (indirizzo) non cambia di nuovo
  const manualRef = useRef(false);
  const lastQueryRef = useRef(null);

  const hasPin = latitude != null && longitude != null
    && latitude !== '' && longitude !== '';
  const lat = hasPin ? Number(latitude) : null;
  const lng = hasPin ? Number(longitude) : null;

  useEffect(() => {
    const q = (geocodeQuery || '').trim();
    if (q.length < 3 || q === lastQueryRef.current) return;
    lastQueryRef.current = q;
    manualRef.current = false;
    let cancelled = false;
    setGeocoding(true);
    api.get('/event-occurrences/geocode', { params: { q } })
      .then(res => {
        if (cancelled || manualRef.current) return;
        if (res.data?.found) onChange(res.data.lat, res.data.lng);
      })
      .catch(() => {})
      .finally(() => { if (!cancelled) setGeocoding(false); });
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [geocodeQuery]);

  if (!hasPin) {
    return (
      <div className="rounded-lg border border-dashed border-gray-300 bg-gray-50 px-4 py-6 text-center text-xs text-gray-400">
        {geocoding
          ? t('locationMap.searching', { defaultValue: 'Cerco la posizione…' })
          : t('locationMap.empty', { defaultValue: 'Compila città o indirizzo: il pin apparirà qui sulla mappa.' })}
      </div>
    );
  }

  return (
    <div>
      <div className="rounded-lg overflow-hidden border border-gray-200" style={{ height: 220 }}>
        <MapContainer center={[lat, lng]} zoom={13} style={{ height: '100%', width: '100%' }}
                      scrollWheelZoom={false}>
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <Recenter lat={lat} lng={lng} />
          <Marker
            position={[lat, lng]}
            draggable
            eventHandlers={{
              dragend: (e) => {
                manualRef.current = true;
                const p = e.target.getLatLng();
                onChange(Number(p.lat.toFixed(6)), Number(p.lng.toFixed(6)));
              },
            }}
          />
        </MapContainer>
      </div>
      <p className="text-[11px] text-gray-400 mt-1">
        {t('locationMap.dragHint', { defaultValue: 'Trascina il pin per correggere la posizione esatta.' })}
      </p>
    </div>
  );
}
