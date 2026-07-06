/**
 * StaticMiniMap — la mappa del luogo sulla landing (G4). Leaflet+OSM,
 * pin fisso, niente interazioni che rubano lo scroll. Caricata lazy
 * (React.lazy dal chiamante): zero peso sul first paint.
 */
import React from 'react';
import { MapContainer, TileLayer, Marker } from 'react-leaflet';
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

export default function StaticMiniMap({ latitude, longitude, height = 180 }) {
  if (latitude == null || longitude == null) return null;
  return (
    <div className="rounded-xl overflow-hidden border border-gray-200 mt-3" style={{ height }}>
      <MapContainer
        center={[latitude, longitude]}
        zoom={12}
        style={{ height: '100%', width: '100%' }}
        scrollWheelZoom={false}
        dragging={false}
        doubleClickZoom={false}
        zoomControl={false}
        attributionControl
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <Marker position={[latitude, longitude]} />
      </MapContainer>
    </div>
  );
}
