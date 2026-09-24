"""
Lotto D (24/9/2026) — parita' dei testi del consenso fra i due mondi.

Il registro del consenso cita una VERSIONE e ne conserva il testo:
backend/services/testi_consenso.py e' la fonte, frontend/src/lib/
testiConsenso.js lo specchio che le caselle mostrano. Se divergono, la
persona ha letto una cosa e il registro ne conserva un'altra. Qui si
leggono entrambi i file (il JS con un parser minimo delle stringhe
concatenate) e si pretende l'identita' parola per parola, piu' la
stessa versione corrente.
"""
import os
import re
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")

JS = BACKEND.parent / "frontend" / "src" / "lib" / "testiConsenso.js"

_STRINGA = re.compile(r"'((?:[^'\\]|\\.)*)'")


def _testi_js() -> dict:
    src = JS.read_text()
    blocco = src[src.index("export const TESTI = {"):]
    blocco = blocco[:blocco.index("\n};")]
    out = {}
    # ogni voce: 'chiave': 'pezzo' + 'pezzo' ... , (anche su piu' righe)
    for m in re.finditer(r"'([\w-]+)':\s*((?:'(?:[^'\\]|\\.)*'\s*\+?\s*)+)", blocco):
        chiave, espr = m.group(1), m.group(2)
        pezzi = [p.replace("\\'", "'") for p in _STRINGA.findall(espr)]
        out[chiave] = "".join(pezzi)
    return out


def _versione_corrente_js() -> str:
    m = re.search(r"export const VERSIONE_CORRENTE = '([\w-]+)'", JS.read_text())
    assert m, "VERSIONE_CORRENTE manca nel JS"
    return m.group(1)


class TestParitaTestiConsenso:
    def test_lo_specchio_esiste(self):
        assert JS.exists(), "manca frontend/src/lib/testiConsenso.js"
        src = JS.read_text()
        for nome in ("export const TESTI", "export const VERSIONE_CORRENTE",
                     "export function testoConsenso", "export function provenienzaCorrente"):
            assert nome in src, nome

    def test_stesse_chiavi(self):
        from services.testi_consenso import TESTI
        js = _testi_js()
        assert set(js) == set(TESTI), f"chiavi diverse: solo JS {set(js) - set(TESTI)}, solo PY {set(TESTI) - set(js)}"

    def test_stessi_testi_parola_per_parola(self):
        from services.testi_consenso import TESTI
        js = _testi_js()
        for k, testo in TESTI.items():
            assert js.get(k) == testo, f"{k}: JS «{js.get(k)}» ≠ PY «{testo}»"

    def test_stessa_versione_corrente(self):
        from services.testi_consenso import TESTI, VERSIONE_CORRENTE
        assert _versione_corrente_js() == VERSIONE_CORRENTE
        assert VERSIONE_CORRENTE in TESTI

    def test_il_testo_corrente_non_promette_una_conferma(self):
        """Strada B: il testo della casella vale con o senza doppio opt-in."""
        from services.testi_consenso import testo
        t = testo().lower()
        assert "conferm" not in t and "ti cancelli con un clic" in t
