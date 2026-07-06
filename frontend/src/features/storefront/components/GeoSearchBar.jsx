/**
 * GeoSearchBar — "Dove?" come i grandi booking (G3,
 * docs/GEO_SEARCH_PLAN.md). Autocomplete Nominatim (via backend,
 * cache aggressiva) + "Vicino a me" (geolocation browser, SOLO
 * on-click, coordinate mai salvate) + raggio a chips.
 *
 * value: {lat, lng, label, radius} | null
 * onChange(next | null)
 */
import React, { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import api from '../../../api/client';

const RADII = [25, 50, 100, 250];

function shortLabel(displayName) {
  return (displayName || '').split(',').slice(0, 2).join(',').trim();
}

export default function GeoSearchBar({ value, onChange }) {
  const { t } = useTranslation('landings');
  const [text, setText] = useState(value?.label || '');
  const [results, setResults] = useState([]);
  const [open, setOpen] = useState(false);
  const [locating, setLocating] = useState(false);
  const boxRef = useRef(null);

  useEffect(() => { setText(value?.label || ''); }, [value?.label]);

  // autocomplete debounced
  useEffect(() => {
    const q = text.trim();
    if (q.length < 2 || q === (value?.label || '')) { setResults([]); return; }
    const timer = setTimeout(() => {
      api.get('/public/geo/search', { params: { q } })
        .then(res => { setResults(res.data?.results || []); setOpen(true); })
        .catch(() => setResults([]));
    }, 400);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [text]);

  // chiudi il dropdown al click fuori
  useEffect(() => {
    const close = (e) => {
      if (boxRef.current && !boxRef.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener('mousedown', close);
    return () => document.removeEventListener('mousedown', close);
  }, []);

  const pick = (r) => {
    setOpen(false);
    setResults([]);
    onChange({ lat: r.lat, lng: r.lng, label: shortLabel(r.label),
               radius: value?.radius || 100 });
  };

  const nearMe = () => {
    if (!navigator.geolocation) return;
    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLocating(false);
        onChange({ lat: Number(pos.coords.latitude.toFixed(5)),
                   lng: Number(pos.coords.longitude.toFixed(5)),
                   label: t('calendar.nearMe', { defaultValue: 'Vicino a me' }),
                   radius: value?.radius || 100 });
      },
      () => setLocating(false),
      { timeout: 8000 },
    );
  };

  const active = !!(value?.lat != null && value?.lng != null);

  return (
    <div className="flex flex-wrap items-center gap-2" ref={boxRef}>
      <div className="relative">
        <input
          type="search"
          value={text}
          onChange={e => setText(e.target.value)}
          onFocus={() => results.length && setOpen(true)}
          placeholder={t('calendar.wherePlaceholder', { defaultValue: '📍 Dove? Città o zona…' })}
          className="rounded-full border border-gray-300 bg-white px-3.5 py-1.5 text-sm w-44 focus:w-60 transition-all focus:border-primary focus:outline-none"
        />
        {active && (
          <button
            type="button"
            aria-label={t('calendar.clearWhere', { defaultValue: 'Rimuovi il filtro luogo' })}
            onClick={() => { setText(''); onChange(null); }}
            className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-700"
          >×</button>
        )}
        {open && results.length > 0 && (
          <ul className="absolute z-30 mt-1 w-72 rounded-xl border border-gray-200 bg-white shadow-lg overflow-hidden">
            {results.map((r, i) => (
              <li key={i}>
                <button
                  type="button"
                  onClick={() => pick(r)}
                  className="w-full text-left px-3.5 py-2 text-sm hover:bg-gray-50 truncate"
                >
                  📍 {r.label}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      {!active && (
        <button
          type="button"
          onClick={nearMe}
          disabled={locating}
          className="rounded-full border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-700 hover:border-primary hover:text-primary transition-colors disabled:opacity-50"
        >
          {locating
            ? t('calendar.locating', { defaultValue: 'Ti localizzo…' })
            : t('calendar.nearMeBtn', { defaultValue: '📍 Vicino a me' })}
        </button>
      )}

      {active && (
        <div className="flex items-center gap-1">
          {RADII.map(r => (
            <button
              key={r}
              type="button"
              onClick={() => onChange({ ...value, radius: r })}
              className={`rounded-full px-2.5 py-1 text-xs font-medium transition-colors ${
                (value.radius || 100) === r
                  ? 'bg-primary text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {r} km
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
