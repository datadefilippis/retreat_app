"""SEO1 — guardie sui costruttori schema.org (services/seo_schema).

Funzioni pure: qui si inchioda che i frammenti JSON-LD siano conformi e
che le regole d'oro reggano (aggregateRating solo con recensioni, date
leggibili, sameAs assoluti, niente campi vuoti).
"""

import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")

from services import seo_schema as sx


class TestHumanDate:
    def test_italian(self):
        assert sx.human_date("2026-10-04T09:30:00") == "4 ottobre 2026"

    def test_english(self):
        assert sx.human_date("2026-10-04T09:30:00", "en") == "October 4, 2026"

    def test_no_iso_grezzo_mai(self):
        # niente 'YYYY-MM-DD' nei title: sempre forma leggibile
        out = sx.human_date("2026-01-15")
        assert out == "15 gennaio 2026"
        assert "-" not in out

    def test_empty_and_garbage(self):
        assert sx.human_date(None) == ""
        assert sx.human_date("") == ""


class TestPostalAddress:
    def test_full(self):
        a = sx.postal_address(street="Via X", city="Ostuni", region="Puglia",
                              postal_code="72017", country="IT")
        assert a["@type"] == "PostalAddress"
        assert a["addressLocality"] == "Ostuni"
        assert a["addressRegion"] == "Puglia"
        assert a["postalCode"] == "72017"
        assert a["addressCountry"] == "IT"

    def test_none_if_empty(self):
        assert sx.postal_address() is None
        assert sx.postal_address(city=None, region=None) is None

    def test_partial_ok(self):
        a = sx.postal_address(city="Lecce", region="Puglia")
        assert set(a) == {"@type", "addressLocality", "addressRegion"}


class TestGeo:
    def test_ok(self):
        g = sx.geo_coordinates(40.7, 17.5)
        assert g == {"@type": "GeoCoordinates", "latitude": 40.7, "longitude": 17.5}

    def test_none_if_missing(self):
        assert sx.geo_coordinates(None, 17.5) is None
        assert sx.geo_coordinates(40.7, None) is None


class TestOffer:
    def test_ok(self):
        o = sx.offer(price=800.0, currency=None, url="/e/x")
        assert o["price"] == 800.0
        assert o["priceCurrency"] == "EUR"          # fallback
        assert o["availability"] == "https://schema.org/InStock"
        assert o["url"] == "/e/x"

    def test_none_if_no_price(self):
        assert sx.offer(price=None) is None


class TestAggregateRating:
    def test_ok(self):
        r = sx.aggregate_rating({"avg": 4.6, "count": 12})
        assert r["ratingValue"] == 4.6
        assert r["reviewCount"] == 12
        assert r["bestRating"] == 5

    def test_none_without_reviews(self):
        # mai stelle finte: 0 recensioni = niente aggregateRating
        assert sx.aggregate_rating({"avg": None, "count": 0}) is None
        assert sx.aggregate_rating({}) is None
        assert sx.aggregate_rating(None) is None


class TestSameAs:
    def test_normalizza_domini_nudi(self):
        out = sx.same_as("instagram.com/x", "https://facebook.com/y", None, "")
        assert out == ["https://instagram.com/x", "https://facebook.com/y"]
