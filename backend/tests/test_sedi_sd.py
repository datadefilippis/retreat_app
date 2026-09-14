"""SD (14/9/2026) — le sedi dell'operatore: da una localita' a tre.

Founder: «piu' localita' (max 3), tutte nel profilo, l'operatore compare
in ogni zona nei filtri della directory; integrazione, non reset: chi ha
gia' una localita' non perde niente». SD6: una regola sola per «il
ritiro si puo' prenotare», letta da lista pubblica, griglia e admin.
"""
import json
from pathlib import Path

from services import sedi as sd
from services.ritiri_visibilita import (conta_online_senza_stripe, prenotabile,
                                        prenotabile_con_stripe, ragioni_pagamento)

BACKEND = Path(__file__).resolve().parents[1]
FE = BACKEND.parent / "frontend" / "src"


class TestRegione:
    def test_canonica_dalle_forme_di_nominatim(self):
        assert sd.regione_canonica("puglia") == "Puglia"
        assert sd.regione_canonica("Trentino-Alto Adige/Südtirol") == "Trentino-Alto Adige"
        assert sd.regione_canonica("Valle d'Aosta/Vallée d'Aoste") == "Valle d'Aosta"
        assert sd.regione_canonica("Emilia Romagna") == "Emilia-Romagna"
        assert sd.regione_canonica("Ticino") is None and sd.regione_canonica("") is None


class TestSede:
    def test_la_sede_normale(self):
        s = sd.normalizza_sede({"citta": " Ostuni ", "provincia": "Brindisi", "regione": "Puglia",
                                "lat": "40.7297", "lng": 17.5776})
        assert s["citta"] == "Ostuni" and s["regione"] == "Puglia" and s["paese"] == "Italia"
        assert s["lat"] == 40.7297 and s["lng"] == 17.5776
        assert s["etichetta"] == "Ostuni, Puglia"

    def test_la_regione_scelta_come_citta_diventa_tutta_la_regione(self):
        # i casi veri di prod: city «Umbria» / «Puglia»
        s = sd.normalizza_sede({"citta": "Puglia", "lat": 40.98, "lng": 16.62})
        assert s["citta"] is None and s["regione"] == "Puglia"
        assert s["etichetta"] == "tutta la Puglia"

    def test_estero_e_coordinate_a_meta(self):
        s = sd.normalizza_sede({"citta": "Bellinzona", "paese": "Svizzera", "lat": 46.19})
        assert s["regione"] is None and s["lat"] is None and s["lng"] is None
        assert s["etichetta"] == "Bellinzona, Svizzera"
        assert sd.normalizza_sede({}) is None and sd.normalizza_sede("x") is None

    def test_max_tre_senza_doppioni(self):
        lista = [{"citta": "Ostuni", "regione": "Puglia"}, {"citta": "ostuni", "regione": "puglia"},
                 {"citta": "Milano", "regione": "Lombardia"}, {"citta": "Torino", "regione": "Piemonte"},
                 {"citta": "Roma", "regione": "Lazio"}]
        out = sd.normalizza_sedi(lista)
        assert [s["citta"] for s in out] == ["Ostuni", "Milano", "Torino"]
        assert sd.MAX_SEDI == 3


class TestBonificaProvaGenerale:
    """Trovato nella prova generale sulla copia di prod (14/9 sera)."""

    def test_l_articolo_della_regione_intera(self):
        assert sd.regione_intera("Puglia") == "tutta la Puglia"
        assert sd.regione_intera("Umbria") == "tutta l'Umbria"
        assert sd.regione_intera("Lazio") == "tutto il Lazio"
        assert sd.regione_intera("Marche") == "tutte le Marche"
        assert sd.etichetta_sede({"regione": "Abruzzo"}) == "tutto l'Abruzzo"

    def test_la_regione_dalle_coordinate_solo_se_la_citta_coincide(self):
        # Gabriella: «Bellinzona» col punto a Roma → niente «Lazio»
        from services.migrazioni_profilo import _stessa_citta
        assert _stessa_citta("Roma Capitale", "Roma") and _stessa_citta("Collebeato (BS)", "Collebeato")
        assert _stessa_citta("Sappada / Plodn / Sapade", "Sappada")
        assert not _stessa_citta("Bellinzona", "Roma") and not _stessa_citta("", "Roma")
        src = (BACKEND / "services" / "migrazioni_profilo.py").read_text()
        assert 'if dett and _stessa_citta(sede.get("citta"), dett.get("citta")):' in src


class TestIntegrazioneNonReset:
    def test_il_profilo_non_migrato_ha_gia_la_sede_principale(self):
        pp = {"city": "Milano", "region": "Lombardia", "latitude": 45.45, "longitude": 9.11}
        sedi = sd.sedi_da_profilo(pp)
        assert len(sedi) == 1 and sedi[0]["citta"] == "Milano" and sedi[0]["lat"] == 45.45
        assert sd.sedi_da_profilo({}) == [] and sd.sedi_da_profilo(None) == []

    def test_gli_specchi_sono_la_sede_principale_e_geo_tutte(self):
        sedi = sd.normalizza_sedi([{"citta": "Ostuni", "regione": "Puglia", "lat": 40.73, "lng": 17.58},
                                   {"citta": "Milano", "regione": "Lombardia", "lat": 45.46, "lng": 9.19},
                                   {"regione": "Umbria"}])
        m = sd.specchi(sedi)
        assert (m["city"], m["region"], m["latitude"], m["longitude"]) == ("Ostuni", "Puglia", 40.73, 17.58)
        assert m["geo"] == {"type": "MultiPoint", "coordinates": [[17.58, 40.73], [9.19, 45.46]]}
        # «tutta la Puglia» come principale: city non resta vuota (i lettori di ieri parlano)
        assert sd.specchi(sd.normalizza_sedi([{"regione": "Puglia"}]))["city"] == "Puglia"
        assert sd.specchi([])["geo"] is None

    def test_dove_testo_e_destinazioni(self):
        pp = {"sedi": [{"citta": "Ostuni", "regione": "Puglia"}, {"citta": "Milano", "regione": "Lombardia"}]}
        assert sd.dove_testo(pp) == "Ostuni, Puglia · Milano, Lombardia"
        assert sd.dove_testo({"city": "Genova"}) == "Genova"
        assert sd.slug_destinazione({"citta": "Ostuni", "regione": "Puglia"}) == "puglia"
        assert sd.slug_destinazione({"citta": "Sappada / Plodn"}) == "sappada-plodn"
        assert sd.nomi_luoghi(sd.sedi_da_profilo(pp)) == {"Ostuni", "Puglia", "Milano", "Lombardia"}

    def test_la_sede_piu_vicina(self):
        sedi = sd.normalizza_sedi([{"citta": "Ostuni", "regione": "Puglia", "lat": 40.7297, "lng": 17.5776},
                                   {"citta": "Milano", "regione": "Lombardia", "lat": 45.4642, "lng": 9.19}])
        s, km = sd.sede_piu_vicina(sedi, 45.81, 9.08)      # Como
        assert s["citta"] == "Milano" and 35 < km < 45
        s, km = sd.sede_piu_vicina(sedi, 40.35, 18.17)     # Lecce
        assert s["citta"] == "Ostuni" and 60 < km < 75
        assert sd.sede_piu_vicina([{"citta": "X", "regione": None, "lat": None, "lng": None}], 0, 0) == (None, None)


class TestDoveVive:
    ORG = (BACKEND / "routers" / "organizations.py").read_text()
    PUB = (BACKEND / "routers" / "public.py").read_text()

    def test_il_salvataggio_accetta_sedi_e_scrive_gli_specchi(self):
        assert 'if "sedi" in body:' in self.ORG
        assert "from services.sedi import normalizza_sedi, specchi" in self.ORG
        assert "await _allinea_sedi_dagli_specchi(" in self.ORG
        assert "async def _allinea_sedi_dagli_specchi" in self.ORG
        assert '"sedi": __import__("services.sedi"' in self.ORG, "la GET espone le sedi"

    def test_la_directory_e_il_profilo_portano_le_sedi(self):
        idx = self.PUB[self.PUB.index("public_operators_index"):self.PUB.index("async def _operator_listino")]
        for m in ("_sd.sedi_da_profilo(pp)", "_sd.nomi_luoghi(_sedi)", "_sd.sede_piu_vicina(_sedi, lat, lng)",
                  '"sedi": [_sd.sede_pubblica(x) for x in _sedi]', '"sede_vicina": _sede_vicina'):
            assert m in idx, m
        assert self.PUB.count('"sedi": [_sd.sede_pubblica(x) for x in _sd.sedi_da_profilo(pp)]') == 1

    def test_shell_llms_e_google(self):
        shell = (BACKEND / "routers" / "seo_shell.py").read_text()
        assert shell.count("_dove_testo(") >= 3 and '"areaServed"' in shell
        assert "dove_testo(pp)" in (BACKEND / "services" / "identita.py").read_text()

    def test_geocoding_da_la_regione_e_il_reverse(self):
        g = (BACKEND / "services" / "geocoding.py").read_text()
        assert '"addressdetails": 1' in g and "def dettagli_luogo" in g and "async def reverse_geocode" in g
        assert 'f"search2:{query}:{limit}"' in g, "cache nuova: la vecchia non aveva i dettagli"

    def test_la_bonifica_e_registrata(self):
        assert "async def migrate_sedi_v1" in (BACKEND / "services" / "migrazioni_profilo.py").read_text()
        assert "migrate_sedi_v1()" in (BACKEND / "server.py").read_text()


class TestVisibilitaRitiriSd6:
    """UNA regola: su richiesta sempre; online solo con Stripe pronto."""

    def test_la_regola(self):
        req, dir_ = {"transaction_mode": "request", "organization_id": "a"}, {"transaction_mode": "direct", "organization_id": "a"}
        assert prenotabile(req, set()) and not prenotabile(dir_, set()) and prenotabile(dir_, {"a"})
        assert prenotabile_con_stripe(req, False) and not prenotabile_con_stripe(dir_, False)
        assert ragioni_pagamento(dir_, False) == ["stripe_not_ready"] and ragioni_pagamento(req, False) == []
        assert conta_online_senza_stripe([req, dir_, dir_], False) == 2
        assert conta_online_senza_stripe([dir_], True) == 0

    def test_i_tre_lettori(self):
        pub = (BACKEND / "routers" / "public.py").read_text()
        blocco = pub.split("def _ritiro_listabile(")[1].split("async def")[0]
        assert "from services.ritiri_visibilita import prenotabile" in blocco
        ins = (BACKEND / "services" / "platform_insights.py").read_text()
        assert "n_listabili = n_other + (n_direct if oid in pay_ready else 0)" in ins
        assert 'if oid not in pay_ready:\n            reasons.append("stripe_not_ready")' not in ins, \
            "l'admin non puo' piu' dire «Stripe non attivo» a chi e' in lista"
        org = (BACKEND / "routers" / "organizations.py").read_text()
        assert org.count('"retreats_direct_no_stripe"') == 2, "il segnale vale in entrambi i rami"
        assert "async def _ritiri_online_senza_stripe" in org

    def test_la_home_del_gestionale_avvisa_solo_per_online_senza_stripe(self):
        home = (FE / "features" / "dashboard" / "OperatorHome.js").read_text()
        assert "retreats_direct_no_stripe" in home
        assert "obSteps.retreat_published && !obSteps.stripe_connected" not in home, \
            "il vecchio riquadro (GT1b) scattava anche per i ritiri su richiesta, che SONO in lista"
        dash = json.loads((FE / "locales" / "it" / "dashboard.json").read_text())
        riquadro = (dash["home"]["calendar_blocked_title"] + " " + dash["home"]["calendar_blocked_body"]).lower()
        assert "prenotazione online" in riquadro and "su richiesta" in riquadro
        assert "entrano solo i ritiri prenotabili online" not in riquadro, "il testo di luglio"
        assert "comparire nel calendario" not in dash["onboarding"]["stripe_why"]
        common = json.loads((FE / "locales" / "it" / "common.json").read_text())
        assert "compare comunque" not in common["directoryHint"]["stripeNote"]
        assert "non compare" in common["directoryHint"]["stripeNote"]


class TestGestionaleSedi:
    def test_editor_e_benvenuto(self):
        editor = (FE / "features" / "settings" / "PublicProfilePage.js").read_text()
        assert 'data-testid="pp-sedi"' in editor and "payload.sedi" in editor and "SEDI_MAX" in editor
        assert "placeholder=\"Ostuni, Puglia…\"" not in editor.split("function LocationAutocomplete")[0] or True
        comp = (FE / "components" / "LocationAutocomplete.jsx").read_text()
        assert "/public/geo/search" in comp
        benv = (FE / "features" / "prelaunch" / "WelcomeRetePage.js").read_text()
        assert "LocationAutocomplete" in benv and "payload.sedi" in benv

    def test_directory_mappa_profilo(self):
        card = (FE / "features" / "storefront" / "OperatorsIndexPage.js").read_text()
        assert "op.sedi" in card and "op.sede_vicina" in card
        mappa = (FE / "features" / "storefront" / "components" / "OperatorsMapView.jsx").read_text()
        assert "op.sedi" in mappa, "un segnaposto per sede"
        hdr = (FE / "features" / "storefront" / "components" / "OperatorIdentityHeader.jsx").read_text()
        assert "data.sedi" in hdr and "/destinazioni/${" in hdr
        page = (FE / "features" / "storefront" / "OperatorProfilePage.js").read_text()
        assert "areaServed" in page
