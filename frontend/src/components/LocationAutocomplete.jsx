/**
 * LocationAutocomplete — AN3, estratto il 14/9/2026 (SD2) perche' ora lo
 * usano l'editor del profilo (le sedi, fino a 3) e il benvenuto.
 * Stesso backend della barra «Dove?» della directory: /public/geo/search
 * (Nominatim + cache), che dal SD1 restituisce anche citta', provincia,
 * regione e paese: la regione non si chiede piu' a nessuno.
 *
 * `onSelect(place)` riceve {label, lat, lng, citta, provincia, regione, paese}.
 * `sedeDaLuogo(place)` costruisce la sede da salvare (services/sedi.py
 * fa la stessa cosa lato server: la verita' e' la sua).
 */
import React, { useEffect, useRef, useState } from 'react';
import { Input } from './ui/input';
import api from '../api/client';

export function etichettaSede(s) {
  if (!s) return '';
  if (s.etichetta) return s.etichetta;
  if (s.citta && s.regione) return `${s.citta}, ${s.regione}`;
  if (s.citta) return s.paese && s.paese !== 'Italia' ? `${s.citta}, ${s.paese}` : s.citta;
  return s.regione ? `tutta la ${s.regione}` : '';
}

export function sedeDaLuogo(place) {
  if (!place) return null;
  const citta = place.citta || (place.label || '').split(',')[0].trim() || null;
  const sede = {
    citta: place.regione && citta && citta.toLowerCase() === place.regione.toLowerCase() ? null : citta,
    provincia: place.provincia || null,
    regione: place.regione || null,
    paese: place.paese || 'Italia',
    lat: place.lat ?? null,
    lng: place.lng ?? null,
  };
  if (!sede.citta && !sede.regione) return null;
  sede.etichetta = etichettaSede(sede);
  return sede;
}

// AN3 — autocomplete località per il profilo: stesso backend della
// barra "Dove?" della directory (/public/geo/search, Nominatim+cache).
export default function LocationAutocomplete({ value, onSelect, onTextChange, placeholder = 'Ostuni, Puglia…', className = 'mt-1' }) {
  const [text, setText] = useState(value || '');
  const [results, setResults] = useState([]);
  const [open, setOpen] = useState(false);
  // CS4 (founder, 13/8) — il dropdown restava aperto dopo la scelta:
  // selezionare scriveva form.city → value → setText, e il cambio di
  // text rilanciava la ricerca riaprendo la lista. Si cerca (e si apre)
  // solo se il testo l'ha battuto l'utente.
  const typedRef = useRef(false);
  useEffect(() => { setText(value || ''); }, [value]);
  useEffect(() => {
    if (!typedRef.current) return undefined;
    if (!text || text.length < 2) { setResults([]); setOpen(false); return undefined; }
    const timer = setTimeout(() => {
      api.get('/public/geo/search', { params: { q: text } })
        .then(res => { setResults(res.data?.results || []); setOpen(true); })
        .catch(() => setResults([]));
    }, 400);
    return () => clearTimeout(timer);
  }, [text]);
  return (
    <div className="relative">
      <Input
        value={text}
        onChange={e => { typedRef.current = true; setText(e.target.value); onTextChange?.(e.target.value); }}
        onFocus={() => results.length && setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 150)}
        placeholder={placeholder}
        className={className}
      />
      {open && results.length > 0 && (
        <ul className="absolute z-20 mt-1 w-full rounded-md border border-border bg-white shadow-lg max-h-52 overflow-auto">
          {results.map((r) => (
            <li key={`${r.lat}-${r.lng}`}>
              <button
                type="button"
                onMouseDown={() => { typedRef.current = false; onSelect(r); setOpen(false); setResults([]); }}
                className="w-full text-left px-3 py-2 text-sm hover:bg-muted/60"
              >
                📍 {r.label}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

