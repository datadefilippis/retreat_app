"""Ciclo LP (16/7/2026) — le landing pubbliche dei prodotti non devono
MAI crashare per un simbolo usato ma non importato.

Bug reale in produzione: ProductLandingPage (servizi) chiamava
useProductSeo() senza import — ReferenceError a runtime, ErrorBoundary
"Qualcosa è andato storto" per il visitatore. ESLint era spento in dev
(DISABLE_ESLINT_PLUGIN) e CRA non blocca la build: questa guardia
copre il buco per TUTTE le landing, per sempre.
"""

import re
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

STOREFRONT = BACKEND_DIR.parent / "frontend" / "src" / "features" / "storefront"

LANDING_FILES = [
    "ProductLandingPage.js",      # servizi  (/p)
    "EventLandingPage.js",        # ritiri   (/e)
    "ReservationLandingPage.js",  # rental   (/r)
    "PhysicalLandingPage.js",     # fisici   (/ph)
    "DigitalLandingPage.js",      # digitali (/dg)
    "CourseLandingPage.js",       # corsi    (/co)
    "TicketLandingPage.js",       # biglietto (/t)
    "BookingLandingPage.js",      # prenotazione (/b)
    "StorefrontPage.js",          # vetrina  (/s)
]

REACT_BUILTIN_HOOKS = {
    "useState", "useEffect", "useMemo", "useCallback", "useRef",
    "useContext", "useReducer", "useLayoutEffect", "useId",
    "useTransition", "useDeferredValue", "useSyncExternalStore",
    "useImperativeHandle", "useDebugValue",
}


def _strip_comments(src: str) -> str:
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    src = re.sub(r"(?m)^\s*//.*$", "", src)
    src = re.sub(r"(?m)\{\s*/\*.*?\*/\s*\}", "", src, flags=re.S)
    return src


def _hooks_ok(path: Path):
    """Ritorna la lista di hook chiamati ma non importati/definiti."""
    src = _strip_comments(path.read_text())
    called = set(re.findall(r"\b(use[A-Z]\w*)\s*\(", src))
    imported = set()
    for clause in re.findall(r"import\s+([^;]+?)\s+from", src):
        imported |= set(re.findall(r"\b(\w+)\b", clause))
    defined = set(re.findall(r"(?:function|const|let)\s+(use[A-Z]\w*)", src))
    missing = []
    for h in sorted(called):
        if h in defined or h in imported:
            continue
        if h in REACT_BUILTIN_HOOKS:
            # deve comunque arrivare dall'import di react
            missing.append(h)
            continue
        missing.append(h)
    return missing


class TestLandingHooksImported:
    """Ogni hook chiamato in una landing pubblica DEVE essere importato
    o definito nel file: un ReferenceError qui è una pagina di vendita
    morta davanti a un cliente."""

    def test_all_landings_have_their_hooks(self):
        problems = {}
        for name in LANDING_FILES:
            p = STOREFRONT / name
            assert p.exists(), f"landing scomparsa: {name}"
            missing = _hooks_ok(p)
            if missing:
                problems[name] = missing
        assert not problems, (
            f"Hook usati ma non importati nelle landing: {problems} — "
            "e' il bug che ha rotto la pagina delle consulenze in prod."
        )

    def test_product_landing_uses_seo_hook(self):
        """SEO parity S1: la landing servizi monta useProductSeo (e
        quindi deve importarlo — il crash nasceva proprio qui)."""
        src = (STOREFRONT / "ProductLandingPage.js").read_text()
        assert "useProductSeo(" in src
        assert re.search(r"import\s+useProductSeo\s+from", src)
