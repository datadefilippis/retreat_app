"""Traduzioni manuali dell'operatore (6/7/2026, decisione founder).

Contratto: services/manual_translations. Le lingue tradotte sono le
lingue che l'operatore ACCETTA — vista in lingua X mostra solo prodotti
con traduzione X; l'italiano (sorgente) è sempre disponibile; MAI
fallback silenzioso nelle viste filtrate.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.manual_translations import (  # noqa: E402
    SUPPORTED_LANGS,
    TRANSLATABLE_FIELDS,
    available_languages,
    is_available_in,
    merge_language,
    sanitize_translations,
)


class TestSanitize:
    def test_whitelist_lingue(self):
        out = sanitize_translations({
            "en": {"description": "hello"},
            "ru": {"description": "нет"},          # non supportata
            "es": {"description": "hola"},          # non supportata
        })
        assert set(out.keys()) == {"en"}

    def test_whitelist_campi(self):
        # name E description sono traducibili (founder 7/7); price no.
        out = sanitize_translations({
            "en": {"description": "ok", "name": "Title EN", "price": 1}
        })
        assert out == {"en": {"description": "ok", "name": "Title EN"}}

    def test_name_da_solo_non_accende_la_lingua(self):
        prod = {"translations": {"en": {"name": "Only title"}}}
        assert available_languages(prod) == ["it"]
        assert is_available_in(prod, "en") is False

    def test_taglio_lunghezze(self):
        desc_max = TRANSLATABLE_FIELDS["description"]
        out = sanitize_translations({"en": {"description": "x" * (desc_max + 500)}})
        assert len(out["en"]["description"]) == desc_max

    def test_strip_e_vuoti_scartati(self):
        out = sanitize_translations({
            "en": {"description": "  ok  "},
            "de": {"description": "   "},           # solo spazi → via
            "fr": {},                                # vuoto → via
        })
        assert out == {"en": {"description": "ok"}}

    def test_none_su_input_non_dict_o_vuoto(self):
        assert sanitize_translations(None) is None
        assert sanitize_translations("en") is None
        assert sanitize_translations({}) is None
        assert sanitize_translations({"ru": {"description": "x"}}) is None

    def test_valori_non_stringa_scartati(self):
        out = sanitize_translations({"en": {"description": 42,
                                            "long_description": ["a"]}})
        assert out is None


class TestAvailability:
    def test_italiano_sempre_disponibile(self):
        assert available_languages({}) == ["it"]
        assert is_available_in({}, "it") is True
        assert is_available_in({}, None) is True

    def test_lingua_conta_solo_con_description(self):
        prod = {"translations": {
            "en": {"description": "yes"},
            "de": {"long_description": "solo racconto lungo"},  # niente description
        }}
        langs = available_languages(prod)
        assert "en" in langs and "de" not in langs
        assert is_available_in(prod, "en") is True
        assert is_available_in(prod, "de") is False

    def test_lingua_mancante_esclude_il_prodotto(self):
        prod = {"translations": {"en": {"description": "yes"}}}
        assert is_available_in(prod, "fr") is False


class TestMerge:
    PROD = {
        "name": "Ritiro Yoga",
        "description": "Descrizione italiana",
        "translations": {"en": {"description": "English description",
                                "long_description": "Long EN"}},
    }

    def test_merge_sostituisce_i_campi_tradotti(self):
        merged = merge_language(self.PROD, "en")
        assert merged["description"] == "English description"
        assert merged["long_description"] == "Long EN"
        assert merged["name"] == "Ritiro Yoga"     # il nome è brand: mai tradotto

    def test_merge_non_muta_l_originale(self):
        merge_language(self.PROD, "en")
        assert self.PROD["description"] == "Descrizione italiana"

    def test_it_e_lingua_assente_ritornano_l_originale(self):
        assert merge_language(self.PROD, "it") is self.PROD
        assert merge_language(self.PROD, None) is self.PROD
        assert merge_language(self.PROD, "de") is self.PROD

    def test_supported_langs_stabili(self):
        # il frontend (MultiLangText) e le viste pubbliche assumono queste tre
        assert SUPPORTED_LANGS == ("en", "de", "fr")


class TestOccurrenceSanitize:
    def _occ_tr(self):
        from services.manual_translations import sanitize_occurrence_translations
        return sanitize_occurrence_translations

    def test_whitelist_lingue_e_blocchi(self):
        out = self._occ_tr()({
            "en": {"included": ["Breakfast"], "junk": ["no"]},
            "ru": {"included": ["нет"]},
        })
        assert set(out.keys()) == {"en"}
        assert out["en"] == {"included": ["Breakfast"]}

    def test_agenda_forma_e_lunghezze(self):
        out = self._occ_tr()({"en": {"agenda": [
            {"label": "Day 1", "items": [
                {"title": "x" * 999, "description": "d", "time": "07:00"}]},
        ]}})
        day = out["en"]["agenda"][0]
        assert day["label"] == "Day 1"
        assert len(day["items"][0]["title"]) == 200      # clamp
        assert "time" not in day["items"][0]              # orari solo in it

    def test_vuoto_ritorna_none(self):
        assert self._occ_tr()(None) is None
        assert self._occ_tr()({}) is None
        assert self._occ_tr()({"en": {"included": ["", "  "]}}) is None


class TestOccurrenceMerge:
    OCC = {
        "agenda": [{"label": "Giorno 1", "items": [
            {"time": "07:30", "title": "Yoga all'alba", "description": "In sala"}]}],
        "included": ["Colazione", "Cena"],
        "excluded": ["Viaggio"],
        "faq": [{"q": "Serve esperienza?", "a": "No"}],
        "translations": {"en": {
            "agenda": [{"label": "Day 1", "items": [
                {"title": "Sunrise yoga", "description": None}]}],
            "included": ["Breakfast", ""],
            "excluded": ["Travel"],
            "faq": [{"q": "Experience needed?", "a": None}],
        }},
    }

    def test_merge_completo_con_fallback_per_campo(self):
        from services.manual_translations import merge_occurrence_language
        m = merge_occurrence_language(self.OCC, "en")
        day = m["agenda"][0]
        assert day["label"] == "Day 1"
        assert day["items"][0]["title"] == "Sunrise yoga"
        assert day["items"][0]["description"] == "In sala"   # vuoto → italiano
        assert day["items"][0]["time"] == "07:30"             # struttura dalla sorgente
        assert m["included"] == ["Breakfast", "Cena"]         # riga vuota → italiano
        assert m["excluded"] == ["Travel"]
        assert m["faq"][0]["q"] == "Experience needed?"
        assert m["faq"][0]["a"] == "No"

    def test_cardinalita_divergente_blocco_torna_italiano(self):
        from services.manual_translations import merge_occurrence_language
        occ = {**self.OCC,
               "included": ["Colazione", "Cena", "Transfer"]}  # 3 vs 2 tradotte
        m = merge_occurrence_language(occ, "en")
        assert m["included"] == ["Colazione", "Cena", "Transfer"]  # fallback intero
        assert m["agenda"][0]["label"] == "Day 1"                  # gli altri blocchi ok

    def test_lingua_assente_ritorna_originale(self):
        from services.manual_translations import merge_occurrence_language
        assert merge_occurrence_language(self.OCC, "de") is self.OCC
        assert merge_occurrence_language(self.OCC, "it") is self.OCC
