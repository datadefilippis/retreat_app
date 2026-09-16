"""DF — Dati freschi nel gestionale (16/9/2026, segnalazione founder).

Una operatrice ha dovuto uscire e rientrare per «vedere» una recensione in
attesa. L'analisi (log nginx) ha mostrato che il server rispondeva sempre
correttamente: i difetti erano nel client. Queste guardie tengono fermi i
cinque interventi, tutti frontend, nessuna API cambiata:

  DF1  hook `useDatiFreschi`: ricarica al ritorno sulla scheda dopo
       un'assenza (>= 60 s), MAI a intervalli sulle pagine con liste;
       applicato a home, Recensioni, Ordini, Clienti, Calendario.
  DF2  la pagina Recensioni legge `?status=` (l'email e la home mandano
       a `/reviews?status=pending`: prima apriva su «Pubblicate»).
  DF3  403 «Not authenticated» senza token = sessione persa (il client
       riportava al login solo sui 401) — SOLO client, il backend resta
       403 per non toccare le pagine pubbliche che chiamano API protette.
  DF4  `storage`: login/logout in una scheda arrivano alle altre.
  DF5  la regia (system_admin) non chiede le recensioni dalla home
       (403 per ruolo: rumore nei log); badge recensioni in attesa nel
       menu solo per gli admin di organizzazione.
"""
from pathlib import Path

FE = Path(__file__).resolve().parents[2] / "frontend" / "src"


def _read(rel: str) -> str:
    return (FE / rel).read_text(encoding="utf-8")


class TestDF1HookRitorno:
    def test_hook_esiste_e_non_ricarica_a_intervalli_di_default(self):
        src = _read("hooks/useDatiFreschi.js")
        assert "visibilitychange" in src and "'focus'" in src
        assert "minNascostaMs = 60000" in src, "il ritorno conta solo dopo un'assenza vera"
        assert "ogniMs = 0" in src, "niente polling di default"

    def test_pagine_del_gestionale_usano_il_hook(self):
        for rel in ("features/dashboard/OperatorHome.js", "features/reviews/ReviewsAdminPage.js",
                    "features/orders/OrdersPage.js", "features/customers-mgmt/CustomersMgmtPage.js",
                    "features/calendar/CalendarPage.js"):
            src = _read(rel)
            assert "useDatiFreschi(" in src, f"{rel}: manca la ricarica al ritorno"
            assert "ogniMs" not in src, f"{rel}: le liste non si ricaricano a intervalli"

    def test_home_carica_ancora_al_montaggio(self):
        src = _read("features/dashboard/OperatorHome.js")
        assert "carica(() => mounted)" in src


class TestDF2RecensioniDaUrl:
    def test_pagina_legge_status_e_link_puntano_alle_in_attesa(self):
        page = _read("features/reviews/ReviewsAdminPage.js")
        assert "useSearchParams" in page and "searchParams.get('status')" in page
        assert "TAB_VALIDI" in page
        home = _read("features/dashboard/OperatorHome.js")
        assert 'to="/reviews?status=pending"' in home
        svc = (Path(__file__).resolve().parents[1] / "services" / "review_service.py").read_text(encoding="utf-8")
        assert "/reviews?status=pending" in svc, "l'email al professionista manda alle in attesa"


class TestDF3TokenMancante:
    def test_client_avvisa_e_authcontext_chiude(self):
        client = _read("api/client.js")
        assert "'Not authenticated'" in client and "auth:token-mancante" in client
        ctx = _read("context/AuthContext.js")
        assert "auth:token-mancante" in ctx

    def test_backend_non_cambia_il_403_del_bearer(self):
        # le pagine pubbliche che chiamano API protette senza token (benvenuto
        # nuovi operatori) non devono finire al login: il 403 resta.
        auth = (Path(__file__).resolve().parents[1] / "auth.py").read_text(encoding="utf-8")
        assert "security = HTTPBearer()" in auth


class TestDF4Schede:
    def test_storage_listener(self):
        ctx = _read("context/AuthContext.js")
        assert "addEventListener('storage'" in ctx and "removeEventListener('storage'" in ctx


class TestDF5Regia:
    def test_home_non_chiede_recensioni_alla_regia(self):
        home = _read("features/dashboard/OperatorHome.js")
        assert "user?.role !== 'system_admin'" in home
        layout = _read("components/Layout.js")
        assert "user.role === 'admin'" in layout and "nav-reviews-pending" in layout


class TestLocaleRecensioni:
    def test_segnaposto_count_non_visits(self):
        for lang in ("it", "en", "de", "fr"):
            src = _read(f"locales/{lang}/common.json")
            assert '"total_one": "{{count}}' in src and '"total_other": "{{count}}' in src, lang
