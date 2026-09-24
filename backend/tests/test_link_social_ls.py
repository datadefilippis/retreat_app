"""LS (14/9/2026) — i link social si normalizzano al salvataggio.

Founder: «gli operatori sbagliano a inserire i link dei social: alla
maggior parte viene spontaneo inserire solo il nome utente». In
produzione 4 Instagram su 10 erano il solo nome (link rotto), gli altri
URL con tracciamento. Decisione: si accetta tutto, si salva la forma
canonica (una funzione sola), il gestionale chiede il nome utente col
prefisso fisso e mostra «Si aprira': …» con «Prova il link».
"""
from pathlib import Path

from services.social_links import (nome_utente_instagram, normalizza_facebook,
                                   normalizza_instagram, normalizza_sito, normalizza_social)

BACKEND = Path(__file__).resolve().parents[1]
FE = BACKEND.parent / "frontend" / "src"


class TestInstagram:
    def test_il_nome_utente_nudo_diventa_l_url(self):
        # i quattro casi veri di produzione
        for nome in ("yoga_in_gocce_con_ilaria", "Olisticamente_silvia", "gabriella_balascio_di_nicola", "claudia.pietrantuoni"):
            assert normalizza_instagram(nome) == f"https://instagram.com/{nome}"
        assert normalizza_instagram("@ilsoledentro") == "https://instagram.com/ilsoledentro"
        assert normalizza_instagram("  @nome.utente/ ") == "https://instagram.com/nome.utente"

    def test_l_url_incollato_dall_app_perde_il_tracciamento(self):
        assert normalizza_instagram("https://www.instagram.com/ilsoledentro_brillare?igsi=MXNhanRuNWRobnNudQ==") \
            == "https://instagram.com/ilsoledentro_brillare"
        assert normalizza_instagram("https://www.instagram.com/_giuliaalbiero?stkn=MWg2&utm_source=qr") \
            == "https://instagram.com/_giuliaalbiero"
        assert normalizza_instagram("instagram.com/claudiacannata_ayurveda/") == "https://instagram.com/claudiacannata_ayurveda"
        assert nome_utente_instagram("https://instagram.com/goccia.di.luna333?igsi=x") == "goccia.di.luna333"

    def test_il_vuoto_resta_vuoto_e_l_illeggibile_si_conserva(self):
        assert normalizza_instagram("") is None and normalizza_instagram(None) is None
        # uno spazio dentro non e' un nome utente: non si perde, non si finge
        assert normalizza_instagram("nome con spazi") == "nome con spazi"


class TestFacebookESito:
    def test_facebook_tiene_i_link_che_funzionano(self):
        assert normalizza_facebook("https://www.facebook.com/profile.php?id=61552905928396") \
            == "https://www.facebook.com/profile.php?id=61552905928396"
        assert normalizza_facebook("https://www.facebook.com/share/19RWfyMMHr/?mibextid=wwXIfr") \
            == "https://www.facebook.com/share/19RWfyMMHr"
        assert normalizza_facebook("latuapagina") == "https://facebook.com/latuapagina"

    def test_il_sito_prende_https_e_perde_gli_utm(self):
        assert normalizza_sito("www.ayurvedicamente.it") == "https://www.ayurvedicamente.it"
        assert normalizza_sito("claudiapietrantuoni.com") == "https://claudiapietrantuoni.com"
        assert normalizza_sito("https://sites.google.com/view/x/home?utm_source=ig&fbclid=abc") \
            == "https://sites.google.com/view/x/home"
        assert normalizza_sito("") is None

    def test_normalizza_social_dice_solo_cio_che_cambia(self):
        pp = {"instagram": "nome_utente", "facebook": "https://www.facebook.com/profile.php?id=1", "website": "https://ok.it"}
        assert normalizza_social(pp) == {"instagram": "https://instagram.com/nome_utente"}


class TestDoveVive:
    def test_il_salvataggio_del_profilo_normalizza(self):
        src = (BACKEND / "routers" / "organizations.py").read_text() + (BACKEND / "services" / "profilo_pubblico.py").read_text()   # A3 (24/9): pulitore estratto
        assert "from services.social_links import NORMALIZZATORI" in src
        i = src.index("for field, max_len in _PUBLIC_PROFILE_FIELDS.items():")
        assert "NORMALIZZATORI" in src[i:i + 1500], "la normalizzazione sta subito dopo la whitelist"

    def test_la_bonifica_esiste_ed_e_registrata(self):
        assert "async def migrate_social_normalizzati_v1" in (BACKEND / "services" / "migrazioni_profilo.py").read_text()
        assert "migrate_social_normalizzati_v1()" in (BACKEND / "server.py").read_text()

    def test_il_gestionale_chiede_il_nome_utente_e_mostra_dove_si_apre(self):
        src = (FE / "features" / "settings" / "PublicProfilePage.js").read_text()
        assert ">instagram.com/</span>" in src and 'placeholder="iltuonomeutente"' in src
        assert 'placeholder="instagram.com/iltuoprofilo"' not in src, "il vecchio suggerimento chiedeva l'URL"
        assert "function AnteprimaLink" in src and "Prova il link" in src and "Si aprirà:" in src
        for tid in ("pp-instagram-anteprima", "pp-website-anteprima", "pp-facebook-anteprima"):
            assert f'testid="{tid}"' in src
        assert ">https://</span>" in src, "il sito ha il prefisso fisso"
