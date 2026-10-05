"""P2 (24/9/2026, founder) — la bio che presenta davvero.

L'hint «2-3 frasi bastano» e il tetto a 600 avevano prodotto bio da 130
caratteri (8 su 20 in prod sotto i 300). Ora: tetto 1000, la guida del
founder in sei punti sempre a vista, un contatore che dice se basta, e il
quinto check di completezza («bio_completa», >= 300) uguale nell'editor e
nel server. Il gate «online» NON cambia.
"""
import json
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
FE = BACKEND.parent / "frontend" / "src"
PAGE = (FE / "features" / "settings" / "PublicProfilePage.js").read_text(encoding="utf-8")
STRIP = (FE / "features" / "onboarding" / "OnboardingStrip.js").read_text(encoding="utf-8")
ORGS = (BACKEND / "routers" / "organizations.py").read_text(encoding="utf-8")
TXT = (BACKEND / "services" / "email_sequenze.py").read_text(encoding="utf-8")

PUNTI = ("di cosa ti occupi", "quali pratiche o percorsi proponi", "a chi ti rivolgi",
         "qual è la tua visione del benessere", "qual è il tuo approccio e il tuo modo di lavorare",
         "cosa può aspettarsi chi decide di intraprendere un percorso con te")


class TestTettoEGuida:
    def test_tetto_1000_in_parita(self):
        assert '"bio": 1000' in ORGS
        assert "const BIO_MAX = 1000;" in PAGE and "maxLength={BIO_MAX}" in PAGE
        assert "maxLength={600}" not in PAGE and "2-3 frasi" not in PAGE

    def test_la_guida_del_founder_in_sei_punti(self):
        assert 'data-testid="bio-guida"' in PAGE
        for p in PUNTI:
            assert p in PAGE, p
        for lang in ("it", "en", "de", "fr"):
            pp = json.loads((FE / "locales" / lang / "settings.json").read_text(encoding="utf-8"))["publicProfile"]
            for k in ("Cosa", "Pratiche", "Chi", "Visione", "Approccio", "Aspettarsi"):
                assert pp.get(f"bioGuida{k}"), f"{lang}: bioGuida{k}"
            assert "2-3" not in pp.get("bioPlaceholder", ""), f"{lang}: l'hint «2-3 frasi» e' ancora li'"

    def test_il_contatore_dice_se_basta(self):
        assert 'data-testid="bio-contatore"' in PAGE
        assert "const BIO_BUONA = 300;" in PAGE and "const BIO_COMPLETA = 600;" in PAGE


class TestCompletezza:
    def test_quinto_check_uguale_in_editor_e_server(self):
        assert '"bio_completa": len((pp.get("bio") or "").strip()) >= 300' in ORGS
        assert "(form.bio || '').trim().length >= BIO_BUONA" in PAGE

    def test_il_gate_online_non_cambia(self):
        blocco = ORGS.split("# ── TW4 mondo snello")[1].split("profile_checks = {")[0]
        assert 'profile_ok = bool(pp.get("bio")) and bool(' in blocco
        assert "bio_completa" not in blocco
        assert "hint_bio_completa" in STRIP

    def test_le_email_non_dicono_piu_due_righe(self):
        assert "due righe" not in TXT.lower() and "Due righe bastano" not in TXT
        assert "Chi apre la tua pagina vuole conoscerti" in TXT   # FL3 (5/10): le parole del founder
