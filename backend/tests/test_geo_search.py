"""G1 — motore geografico (docs/GEO_SEARCH_PLAN.md).

Contratti puri: GeoJSON derivato, haversine, chiave di cache.
Il round-trip col DB/Nominatim e' verificato live (dev), non qui.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.geocoding import normalize_address, to_geojson  # noqa: E402


class TestToGeojson:
    def test_punto_valido_lng_lat(self):
        # GeoJSON vuole [lng, lat] — l'inversione e' l'errore classico
        assert to_geojson(40.73, 17.57) == {
            "type": "Point", "coordinates": [17.57, 40.73]}

    def test_none_su_coordinate_mancanti_o_invalide(self):
        assert to_geojson(None, 17.5) is None
        assert to_geojson(40.7, None) is None
        assert to_geojson("abc", 17.5) is None
        assert to_geojson(91, 0) is None       # lat fuori range
        assert to_geojson(0, 181) is None      # lng fuori range

    def test_stringhe_numeriche_accettate(self):
        # i form arrivano come stringhe
        out = to_geojson("40.73", "17.57")
        assert out["coordinates"] == [17.57, 40.73]


class TestNormalizeAddress:
    def test_chiave_stabile(self):
        a = normalize_address("Via Test 1", "Ostuni", "72017", "IT")
        b = normalize_address("  via test 1 ", " OSTUNI", "72017", "it")
        assert a == b == "via test 1, ostuni, 72017, it"

    def test_parti_mancanti(self):
        assert normalize_address(None, "Ostuni", None, None) == "ostuni"
        assert normalize_address(None, None, None, None) == ""


class TestHaversine:
    def test_distanze_note(self):
        from routers.public import _haversine_km
        # Ostuni → Bari ≈ 76 km in linea d'aria
        d = _haversine_km(40.7295, 17.5779, 41.1171, 16.8719)
        assert 70 < d < 85
        # stesso punto = 0
        assert _haversine_km(40.0, 17.0, 40.0, 17.0) == 0

    def test_radius_radianti(self):
        # il filtro $centerSphere usa km/6371: 100km ≈ 0.0157 rad
        assert abs(100 / 6371.0 - 0.0157) < 0.001


class TestGeocodeRouteOrder:
    """G2 — /event-occurrences/geocode deve stare PRIMA di
    /{occurrence_id} (stesso morso di payments-overview e taxonomies)."""

    def test_route_defined_before_dynamic_id(self):
        import os
        path = os.path.join(os.path.dirname(__file__), "..",
                            "routers", "event_occurrences.py")
        src = open(path).read()
        assert src.index('@router.get("/geocode")') \
            < src.index('@router.get("/{occurrence_id}")')
