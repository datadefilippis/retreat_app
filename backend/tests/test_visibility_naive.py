"""
IG4 (3/9/2026) — /analytics/visibility crashava per gli operatori ATTIVI.

Mongo (client non tz_aware) restituisce i datetime senza fuso; il
router confrontava `created_at` con un inizio-mese aware → TypeError
«can't compare offset-naive and offset-aware datetimes» → 500 per ogni
org con un ordine confermato nel mese corrente o precedente. Scoperto
seedando la dashboard: 175 traceback nel log locale in una mattina.
Cura: _aware() normalizza (naive = UTC per contratto; stringhe ISO dei
doc storici parse-ate; il resto = nessuna data).
"""
from datetime import datetime, timezone, timedelta
from pathlib import Path

from routers.visibility import _aware, _month_bounds

BACKEND = Path(__file__).resolve().parents[1]


class TestAware:
    def test_naive_diventa_utc(self):
        d = _aware(datetime(2026, 9, 3, 10, 0))
        assert d.tzinfo is not None and d.utcoffset() == timedelta(0)

    def test_aware_resta_com_e(self):
        d = datetime(2026, 9, 3, 10, 0, tzinfo=timezone.utc)
        assert _aware(d) is d

    def test_stringa_iso_storica(self):
        assert _aware("2026-09-03T08:20:10.677573Z") == datetime(
            2026, 9, 3, 8, 20, 10, 677573, tzinfo=timezone.utc)
        assert _aware("2026-09-03T08:20:10") == datetime(2026, 9, 3, 8, 20, 10, tzinfo=timezone.utc)

    def test_spazzatura_e_nessuna_data(self):
        for v in (None, "", "ieri", 42, {"$date": 1}):
            assert _aware(v) is None

    def test_il_confronto_del_mese_non_lancia_piu(self):
        """La riga incriminata, riprodotta: naive dal DB vs aware del router."""
        now = datetime.now(timezone.utc)
        cur_start, _ = _month_bounds(now)
        dal_db = datetime.now()   # naive, come lo consegna Motor
        assert (_aware(dal_db) or cur_start) >= cur_start


class TestGuardia:
    def test_il_router_passa_da_aware(self):
        src = (BACKEND / "routers" / "visibility.py").read_text()
        assert '_aware(o.get("created_at"))' in src, \
            "il confronto created_at vs inizio-mese deve normalizzare il fuso"
        assert 'if (o.get("created_at") or prev_start) >= cur_start' not in src
