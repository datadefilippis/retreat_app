"""ET1-ET4 (2/10/2026) — la fascia d'eta' nel Cerchio.

Facoltativa, dalla rosa chiusa ETA_FASCE, stesso giro del budget: modulo →
subscribe → profile.eta → preferenze dell'iscritto → regia (riga, filtro,
ripartizione, modifica con audit, CSV in coda) → Brevo → numeri del lunedi'.
Zero regressioni sulla pagina sponsorizzata: payload senza `eta` (bundle
vecchio) o con `eta` vuota = identico a oggi; valori fuori rosa scartati.
Piano: docs/PIANO_ETA_CERCHIO_2026-10-02.md
"""
import json
import os
from pathlib import Path

import pytest
import requests

RADICE = Path(__file__).resolve().parents[2]
BACKEND = RADICE / "backend"
FE = RADICE / "frontend" / "src"
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8000")
SUBS = (BACKEND / "routers" / "subscribers.py").read_text(encoding="utf-8")


class TestBackend:
    def test_rosa_e_validazione(self):
        from routers.subscribers import ETA_FASCE, _eta_valida, SubscribePayload, PreferencesPayload, PreferenzeAdminPayload
        assert ETA_FASCE == ("18-29", "30-44", "45-59", "60+")
        assert all("<18" not in f and not f.startswith("0") for f in ETA_FASCE)   # mai una fascia minorenne
        for ok in ETA_FASCE:
            assert _eta_valida(ok) == ok and _eta_valida(f" {ok} ") == ok
        for no in ("", None, "17", "25", "18-30", "60", "sessanta", "18-29; drop"):
            assert _eta_valida(no) is None, no
        for modello in (SubscribePayload, PreferencesPayload, PreferenzeAdminPayload):
            campo = modello.model_fields["eta"]
            assert not campo.is_required(), modello.__name__        # mai obbligatoria
            assert campo.default is None

    def test_subscribe_scrive_solo_la_rosa(self):
        blocco = SUBS[SUBS.index('for field in ("city", "travel", "budget", "eta")'):][:600]
        assert 'if field == "eta" and val not in ETA_FASCE:' in blocco and "continue" in blocco

    def test_set_eta_scrive_toglie_ignora(self):
        from routers.subscribers import _set_eta
        s, u = {}, {}
        _set_eta(s, u, None)
        assert s == {} and u == {}                       # assente = non toccare
        _set_eta(s, u, "")
        assert s == {} and u == {"profile.eta": ""}      # vuota = togli
        s, u = {}, {}
        _set_eta(s, u, "45-59")
        assert s == {"profile.eta": "45-59"} and u == {}
        s, u = {}, {}
        _set_eta(s, u, "banana")
        assert s == {} and u == {}                       # fuori rosa = ignorata

    def test_riga_filtro_stats_csv_brevo(self):
        from routers.subscribers import _riga_iscritto, _query_iscritti
        riga = _riga_iscritto({"email": "a@b.it", "profile": {"eta": "30-44"}})
        assert riga["eta"] == "30-44"
        assert _riga_iscritto({"email": "a@b.it", "profile": {"eta": "boh"}})["eta"] is None
        assert _riga_iscritto({"email": "a@b.it"})["eta"] is None
        q = _query_iscritti(None, None, None, None, None, None, None, eta="60+")
        assert q["profile.eta"] == "60+"
        assert "profile.eta" not in _query_iscritti(None, None, None, None, None, None, None, eta="x")
        stats = SUBS[SUBS.index("async def newsletter_stats("):SUBS.index("def _riga_iscritto(")]
        assert '"by_eta": by_eta' in stats and 'for f in ETA_FASCE if conta_eta.get(f)' in stats
        csv_ = SUBS[SUBS.index("async def export_subscribers("):SUBS.index("class DisiscriviPayload")]
        testata = csv_[csv_.index("w.writerow(["):csv_.index("async for d in")]
        assert '"n_email",\n                "eta"])' in testata, "la colonna eta va IN CODA (le vecchie restano dove sono)"
        assert 'r["eta"] or ""])' in csv_
        for rotta in ("async def list_subscribers(", "async def export_subscribers("):
            firma = SUBS[SUBS.index(rotta):][:1200]
            assert "eta: Optional[str] = None" in firma, rotta
        assert SUBS.count("_set_eta(doc_set, doc_unset, payload.eta)") == 2   # PUT pubblico + PATCH regia
        assert '"budget", "eta", "name"' in SUBS                      # l'audit vede il campo
        brevo = (BACKEND / "services" / "subscriber_brevo_sync.py").read_text(encoding="utf-8")
        assert '"AURYA_ETA": profile.get("eta") or ""' in brevo
        lunedi = (BACKEND / "routers" / "admin_platform.py").read_text(encoding="utf-8")
        assert '"con_eta": con_eta' in lunedi and '"profile.eta": {"$nin": [None, ""]}' in lunedi
        seq = (BACKEND / "services" / "sequenze.py").read_text(encoding="utf-8")
        assert '"eta": profilo.get("eta") or ""' in seq

    def test_dal_vivo_payload_vecchio_e_fuori_rosa(self):
        """Il bundle in cache non manda `eta`: il subscribe deve rispondere
        come oggi. E un valore fuori rosa non deve dare 422."""
        try:
            r = requests.get(f"{BASE_URL}/api/health", timeout=5)
        except Exception:
            pytest.skip("backend su :8000 spento")
        if r.status_code != 200:
            pytest.skip("backend su :8000 non in salute")
        base = {"email": "eta-guardia-nonesiste@example.invalid", "consent": False}
        senza = requests.post(f"{BASE_URL}/api/public/newsletter/subscribe", json=base, timeout=10)
        con = requests.post(f"{BASE_URL}/api/public/newsletter/subscribe", json={**base, "eta": "banana"}, timeout=10)
        # consent False → stessa risposta (422/400) nei due casi: il campo non cambia il percorso
        assert senza.status_code == con.status_code and senza.status_code != 500


class TestFrontend:
    def test_modulo_e_preferenze(self):
        pref = (FE / "features" / "prelaunch" / "PreferenzeRitiri.jsx").read_text(encoding="utf-8")
        assert "export const ETA = ['18-29', '30-44', '45-59', '60+'];" in pref
        assert "eta = '', setEta = null," in pref and "{setEta && (" in pref
        assert 'data-testid="preferenze-eta"' in pref and "form.etaHint" in pref and "form.etaLabel" in pref
        lead = (FE / "features" / "prelaunch" / "LeadForm.jsx").read_text(encoding="utf-8")
        assert "const [eta, setEta] = useState('');" in lead
        ramo_sub = lead[lead.index("api.post('/public/newsletter/subscribe'"):lead.index("api.post('/public/leads'")]
        assert "eta: eta || null," in ramo_sub
        ramo_lead = lead[lead.index("api.post('/public/leads'"):][:900]
        assert "eta" not in ramo_lead, "i lead delle landing restano fuori perimetro"
        assert lead.count("eta={eta} setEta={setEta}") == 2          # modulo pieno + blocco «avvisami»
        avv = (FE / "features" / "prelaunch" / "AvvisamiRitiri.jsx").read_text(encoding="utf-8")
        assert "eta = '', setEta = null," in avv
        hook = avv[avv.index("export function useAvvisamiRitiri"):avv.index("const INPUT_CHIARO")]
        assert "eta" not in hook, "i cancelli (hook proprio) non chiedono l'eta'"
        np_ = (FE / "features" / "prelaunch" / "NewsletterPreferencesPage.js").read_text(encoding="utf-8")
        assert "setEta(res.data.eta || '');" in np_ and "eta: eta || ''" in np_ and "eta={eta} setEta={setEta}" in np_

    def test_etichette_x4_senza_trattini_lunghi(self):
        for lang in ("it", "en", "de", "fr"):
            d = json.loads((FE / "locales" / lang / "prelaunch.json").read_text(encoding="utf-8"))
            form = d["form"]
            assert "etaLabel" in form and "etaHint" in form, lang
            assert set(form["eta"]) == {"18-29", "30-44", "45-59", "60+"}, lang
        it = json.loads((FE / "locales" / "it" / "prelaunch.json").read_text(encoding="utf-8"))["form"]
        assert it["etaLabel"] == "La tua età"            # founder 2/10: niente «(facoltativo)», lo e' e basta
        assert it["etaHint"].startswith("Molti ritiri sono pensati per età diverse")

    def test_regia(self):
        tab = (FE / "features" / "admin" / "IscrittiTab.js").read_text(encoding="utf-8")
        assert "const ETA = { '18-29'" in tab
        assert "{ k: 'eta', label: 'Età', nuova: true," in tab
        assert "COLONNE.slice(0, 12)" in tab
        assert "CHIAVE_OFFERTE" in tab and "c.nuova && !base.includes(c.k)" in tab   # si offre una volta
        assert 'testid="iscritti-rip-eta"' in tab                     # prop di <Ripartizione>
        for t in ("iscritti-f-eta", "iscritti-pref-eta"):
            assert f'data-testid="{t}"' in tab, t
        assert "toggleFiltro('eta'" in tab and "setFiltro('eta')" in tab
        assert '<Riga k="Età" v={ETA[s.eta] || \'—\'} />' in tab
        assert "eta: p.eta || ''," in tab and "eta: s.eta || ''," in tab
        assert "  eta: ''," in tab                                   # FILTRI_VUOTI
        over = (FE / "features" / "admin" / "PlatformOverviewTab.js").read_text(encoding="utf-8")
        assert "lunedi.cerchio.con_eta" in over


class TestInformativa:
    def test_riga_7bis_x4_e_versione(self):
        attese = {"it": "fascia d'eta' facoltativa", "en": "optional age range",
                  "de": "optionale Altersgruppe", "fr": "tranche d'âge facultative"}
        for lang, frase in attese.items():
            riga = next(l for l in (BACKEND / "legal" / f"privacy_{lang}.md").read_text(encoding="utf-8").splitlines()
                        if l.startswith("| 7-bis"))
            assert frase in riga, lang
        from core.legal_versions import CURRENT_VERSION_TAG
        assert CURRENT_VERSION_TAG == "v2.9"
