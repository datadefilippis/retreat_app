# Ricerca geografica — directory e eventi (piano, 8 luglio 2026)

Richiesta founder: il filtro "regione italiana" non ha senso (gli operatori
possono creare eventi in tutto il mondo). Serve posizione precisa, mappa
integrata, raggio di ricerca — come i grandi booking system. Vincolo duro:
**zero costi, per sempre** ("non voglio pagare, voglio geo map gratis e
funzionante e user-friendly").

## G0 · Lo stack gratuito (decisione tecnica)

| Bisogno | Soluzione | Costo | Note |
|---|---|---|---|
| Mappa interattiva | **Leaflet + react-leaflet** (tile OpenStreetMap) | 0 € | Lo standard open; niente API key |
| Geocoding (indirizzo → lat/lng) | **Nominatim** (OSM) | 0 € | Limite 1 req/s: per noi irrilevante (si geocoda solo al salvataggio evento e sull'autocomplete debounced) |
| Autocomplete località | **Nominatim search** (debounce 400ms + cache) | 0 € | Stessa API |
| "Vicino a me" | **navigator.geolocation** (browser) | 0 € | Nativo, chiede permesso |
| Ricerca per raggio | **MongoDB 2dsphere** (`$geoWithin` + `$centerSphere`) | 0 € | Già nel nostro DB, niente servizi esterni |

Obblighi (gratuiti ma obbligatori): attribuzione "© OpenStreetMap" sulla
mappa; User-Agent identificativo sulle chiamate Nominatim; cache dei
risultati di geocoding (mai ri-geocodare lo stesso indirizzo).
Piano B se il traffico tile crescesse molto: provider free-tier (Carto,
MapTiler) — cambio di UNA riga di config, decisione rimandabile.

**Cosa abbiamo già in casa** (verificato): `latitude`/`longitude` sul
modello occurrence (oggi mai valorizzati), indirizzo strutturato
(address/city/postal_code/country), `map_url` auto-derivato, filtro
`region` sulla directory (da declassare), campi lat/lng manuali nel
wizard "Quando e dove".

## G1 · Backend: il motore della distanza (0,5 gg)

- [ ] Campo GeoJSON `geo: {type:"Point", coordinates:[lng,lat]}` sulle
      occurrence, derivato da latitude/longitude al save (una fonte:
      lat/lng restano la verità, geo è l'indice)
- [ ] Indice **2dsphere** su `event_occurrences.geo`
- [ ] `/public/retreats`: nuovi param `lat`, `lng`, `radius_km`
      (default 100) → `$geoWithin $centerSphere`; risposta con
      `distance_km` per item (calcolo haversine in Python, niente
      aggregation complicata); `region` resta come fallback legacy
- [ ] Param `country` per il raggruppamento estero (IT default)
- [ ] **Geocoding service** (`services/geocoding.py`): Nominatim con
      User-Agent, cache su collection `geocode_cache` (chiave = indirizzo
      normalizzato), rate-limit interno, best-effort (MAI bloccare un
      salvataggio se Nominatim non risponde)
- [ ] Hook al save occurrence (create/update/wizard): se address/city
      presenti e lat/lng assenti → geocode automatico
- [ ] Script one-off `scripts/backfill_geo.py`: geocoda le occurrence
      esistenti senza lat/lng (1 req/s, idempotente)
- **DoD**: curl con lat/lng/radius restituisce solo eventi nel raggio,
  ordinabili per distanza; evento salvato senza coordinate le acquisisce.

## G2 · Wizard "Quando e dove": il pin che si sistema da solo (0,5 gg)

L'operatore non deve sapere cosa sono le coordinate.
- [ ] Mini-mappa Leaflet nel tab (sotto i campi indirizzo): appena
      city/address sono compilati → geocode debounced → il pin appare
- [ ] **Pin trascinabile**: se Nominatim sbaglia di 200m, l'operatore
      lo sposta col dito; lat/lng si aggiornano (la mappa È l'input)
- [ ] I campi lat/lng manuali restano (advanced, collassati)
- [ ] Nessun blocco: senza pin l'evento si salva lo stesso (appare
      nella directory senza filtro distanza, con la sola città)
- **DoD**: scrivo "Ostuni" → pin sulla mappa in 1 secondo → lo sposto
  sulla masseria → salvo → la landing ha la posizione giusta.

## G3 · Directory: "Dove?" come un booking system (1 gg)

Sostituisce il dropdown regioni.
- [ ] Barra **"Dove?"**: input con autocomplete Nominatim (città o zona,
      debounce, cache) + chip **"📍 Vicino a me"** (geolocation browser)
- [ ] Selettore **raggio**: chips 25 / 50 / 100 / 250 km (default 100)
- [ ] Card risultati con badge **"a 12 km"** (distance_km dal backend),
      ordinamento "più vicini prima" quando c'è una posizione attiva
- [ ] Toggle **Lista / 🗺 Mappa**: vista mappa Leaflet con marker per
      evento (cluster se >20 con leaflet.markercluster), popup = mini
      card (titolo, data, prezzo, "Vedi") → landing
- [ ] Eventi esteri: raggruppamento per paese quando nessuna posizione
      è attiva ("Italia (12) · Spagna (2) · Portogallo (1)"); la ricerca
      per raggio funziona ovunque nel mondo (Nominatim è globale)
- [ ] `region` sparisce dalla UI (il param backend resta per i vecchi
      link); URL condivisibili: /ritiri?lat=..&lng=..&r=50&q=Ostuni
- **DoD**: "Ostuni + 50km" → vedo solo i ritiri nel raggio con la
  distanza; "Vicino a me" funziona; la mappa mostra i pin e da un pin
  arrivo alla landing.

## G4 · Landing evento: la mappa al posto del link (0,25 gg)

- [ ] Sezione luogo: mini-mappa Leaflet embedded (pin non interattivo,
      zoom fisso) al posto del solo link "Apri in Google Maps" — il
      link resta sotto per le indicazioni stradali
- [ ] Attribuzione OSM; lazy-load della mappa (sotto la piega, niente
      peso sul first paint)
- **DoD**: la landing mostra DOVE si svolge il ritiro senza uscire.

## Rischi e paletti
- **Privacy**: "Vicino a me" solo on-click (mai geolocalizzare in
  automatico), coordinate utente MAI salvate né loggate.
- **Nominatim policy**: cache aggressiva + debounce; se un giorno
  l'autocomplete diventasse pesante → Photon (komoot, sempre gratis,
  stesso dato OSM) come drop-in.
- **Peso bundle**: Leaflet ~40KB gz, caricato lazy solo dove serve
  (directory vista mappa, wizard, landing).
- **Eventi senza pin**: restano visibili (mai nascondere inventario);
  esclusi solo dal filtro raggio, con nudge all'operatore in dashboard
  ("Aggiungi la posizione sulla mappa: i clienti ti trovano per zona").

## Ordine e stima
G1 (motore) → G2 (pin wizard) → G3 (directory) → G4 (landing) ≈ **2,5 gg**.
Ogni fase ha DoD verificabile in browser; suite soldi/pubblico intatta.
