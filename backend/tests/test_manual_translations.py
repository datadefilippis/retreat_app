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
        out = sanitize_translations({
            "en": {"description": "ok", "name": "NO", "price": 1}
        })
        assert out == {"en": {"description": "ok"}}

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
