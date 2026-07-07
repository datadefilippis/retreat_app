"""CF7 — mini-stats newsletter: invarianti.

  1. auth obbligatoria;
  2. shape: total / new_30d / months(12 consecutivi) / by_source;
  3. la route /stats è dichiarata PRIMA di /{form_id} (l'ordine di
     route in FastAPI conta: dopo, "stats" verrebbe interpretato
     come un form_id → 404).
"""

import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")

import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8000")


def test_requires_auth():
    r = requests.get(f"{BASE_URL}/api/newsletter-forms/stats", timeout=10)
    assert r.status_code in (401, 403)


def test_shape_and_month_window():
    r = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": "admin@demo.com", "password": "demo1234"}, timeout=10)
    if r.status_code != 200:
        import pytest
        pytest.skip("demo login unavailable (rate limit?)")
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
    d = requests.get(f"{BASE_URL}/api/newsletter-forms/stats",
                     headers=headers, timeout=15).json()
    for key in ("total", "new_30d", "months", "by_source"):
        assert key in d, f"chiave mancante: {key}"
    months = [m["month"] for m in d["months"]]
    assert len(months) == 12
    for a, b in zip(months, months[1:]):
        ya, ma = map(int, a.split("-"))
        yb, mb = map(int, b.split("-"))
        assert (yb * 12 + mb) - (ya * 12 + ma) == 1


def test_stats_route_declared_before_form_id():
    """Guardia sull'ordine di dichiarazione delle route."""
    from routers import newsletter_forms as nf
    paths = [r.path for r in nf.router.routes]
    stats_idx = next(i for i, p in enumerate(paths) if p.endswith("/stats"))
    formid_idx = next(i for i, p in enumerate(paths) if p.endswith("/{form_id}"))
    assert stats_idx < formid_idx, (
        "/stats deve precedere /{form_id} o verrà catturata come form_id")
