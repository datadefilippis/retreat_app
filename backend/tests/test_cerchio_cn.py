"""
IL CERCHIO (3/9/2026, docs/NEWSLETTER_CONVERSIONE_PIANO_2026-09.md).

Founder: «la landing della Lettera deve convertire meglio... nessuno
si e' iscritto da li'... ragionare come marketing manager senza perdere
umanita'». Decisioni: nome «Il Cerchio di Aurya»; preferenza ritiri
accesa di default; promemoria a 48h ai non confermati; in pagina solo
«meditazioni riservate», senza conteggi ne' date.

Le tre regole di conversione, guardiate: il form nel PRIMO schermo,
promesse concrete senza numeri, si dice cosa ricevi (mai «notifiche/
rumore» in apertura).
"""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

FE = Path(__file__).resolve().parents[1].parent / "frontend" / "src"
BACKEND = Path(__file__).resolve().parents[1]
PRE = FE / "features" / "prelaunch"


class TestCn1Landing:
    def test_il_form_sta_nel_primo_schermo(self):
        src = (PRE / "NewsletterLandingPage.js").read_text()
        # il form vive nell'apertura (PhotoOpener), prima di ogni sezione
        assert src.index('id="iscriviti"') < src.index('data-testid="nl-find"')
        assert src.index("<SchedaForm") < src.index("</PhotoOpener>")
        assert 'context="fondo"' in src and "`nl-form-${context}`" in src, \
            "il form si ripete in fondo"

    def test_nome_e_pila_di_valore_senza_conteggi(self):
        it = json.loads((FE / "locales" / "it" / "prelaunch.json").read_text())["nl"]
        assert it["eyebrow"] == "Il Cerchio di Aurya"
        assert it["title"] == "Entra nel Cerchio di Aurya."
        assert it["cta"] == "Entra nel Cerchio"
        for k in ("r1t", "r2t", "r3t"):
            assert it[k]
        assert "riservate" in it["r1t"] and "anteprima" in it["r2t"] and "Lettera" in it["r3t"]
        # niente conteggi, niente «in arrivo», niente cadenza dichiarata
        # (founder 3/9: «meno dettagli inutili»; «ogni due settimane mi
        # vincolo»), niente anti-promesse in apertura
        testo = " ".join(it.values()).lower()
        for vietato in ("1 meditazione", "in arrivo", "ogni due settimane",
                        "notifiche", "rumore", "nessun automatismo"):
            assert vietato not in testo, f"in landing non si dice «{vietato}»"

    def test_preferenza_ritiri_accesa_con_la_citta(self):
        src = (PRE / "NewsletterLandingPage.js").read_text()
        # founder 3/9 sera: nome e interessi restano nel form della
        # landing (niente variante leggera qui; la home la usa)
        assert "experiencesOptIn" in src and "experiencesDefault" in src
        assert "experiencesLight" not in src, "la landing mostra citta', raggio e interessi"
        i = src.index("<LeadForm")
        assert "showName\n" in src[i:i + 400] or "showName " in src[i:i + 400], "il nome resta nel form"
        form = (PRE / "LeadForm.jsx").read_text()
        assert "useState(\n    Boolean(experiencesOptIn && experiencesDefault))" in form
        assert "{!experiencesLight && (<>" in form, "la variante leggera mostra solo la citta'"
        # il consenso resta esplicito e SPENTO (e' un consenso, non una preferenza)
        assert "const [consent, setConsent] = useState(false);" in form

    def test_la_shell_seo_dice_lo_stesso_title(self):
        shell = (BACKEND / "routers" / "seo_shell.py").read_text()
        it = json.loads((FE / "locales" / "it" / "prelaunch.json").read_text())["nl"]
        assert it["seoTitle"].split(" | ")[0] == "Il Cerchio di Aurya"
        assert '"Il Cerchio di Aurya | Meditazioni riservate, ritiri in "' in shell
        assert 'href="/newsletter">Il Cerchio di Aurya</a>' in shell
        assert "Scopri la Lettera" not in shell


class TestCn2DoppioOptIn:
    def test_l_email_di_conferma_dice_cosa_si_sblocca(self):
        src = (BACKEND / "routers" / "subscribers.py").read_text()
        i = src.index("def _send_confirm_email")
        corpo = src[i:src.index("def _send_access_email")]
        assert "Un clic e sei nel Cerchio di Aurya" in corpo
        assert "meditazioni riservate" in corpo and "anteprima" in corpo and "Lettera" in corpo
        assert "Entro nel Cerchio" in corpo
        assert "lettera di Aurya</strong>" not in corpo

    def test_la_conferma_apre_le_meditazioni(self):
        src = (PRE / "NewsletterConfirmPage.js").read_text()
        assert "Sei nel Cerchio di Aurya" in src
        assert 'data-testid="nl-confirm-meditazioni"' in src and 'to="/meditazioni"' in src

    def test_il_promemoria_e_uno_solo_nella_finestra(self):
        src = (BACKEND / "services" / "cerchio_reminder.py").read_text()
        assert "REMINDER_AFTER_HOURS = 48" in src and "REMINDER_WINDOW_DAYS = 7" in src
        assert '"reminder_sent_at": {"$exists": False}' in src
        # si marca PRIMA di inviare: mai due promemoria
        assert src.index('{"$set": {"reminder_sent_at": now}}') < src.index("if _send_reminder_email(email")
        bg = (BACKEND / "services" / "background_service.py").read_text()
        assert 'name="cerchio_reminder_job"' in bg


class TestCn3Ribrand:
    def test_le_porte_del_sito_dicono_cerchio(self):
        landings = json.loads((FE / "locales" / "it" / "landings.json").read_text())
        assert landings["nwHome"]["letterTitle"] == "Entra nel Cerchio di Aurya."
        assert landings["nwHome"]["letterCta"] == "Entra nel Cerchio"
        assert landings["manifesto"]["ctaLetterPrimary"] == "Entra nel Cerchio di Aurya"
        cancello = (FE / "features" / "frequenze" / "CancelloLettera.jsx").read_text()
        assert "per chi è nel Cerchio di Aurya" in cancello
        med = (FE / "features" / "frequenze" / "MeditazioniPage.js").read_text()
        assert "nel Cerchio di Aurya" in med and "Sei già nel Cerchio?" in med
        shell_fe = (FE / "features" / "storefront" / "components" / "MarketplaceShell.jsx").read_text()
        assert "'Il Cerchio di Aurya'" in shell_fe
        # la Lettera resta il nome dell'email dentro il Cerchio: non sparisce,
        # ma senza cadenza dichiarata (founder: «altrimenti mi vincolo»)
        assert landings["nwHome"]["letterP4"] == "La Lettera, quando vale la pena."
        for f in ("features/network/NetworkHomePage.js", "features/frequenze/CancelloLettera.jsx",
                  "features/prelaunch/NewsletterConfirmPage.js", "features/prelaunch/NewsletterLandingPage.js"):
            assert "ogni due settimane" not in (FE / f).read_text(), f"{f}: cadenza dichiarata"
        for f in ("routers/subscribers.py", "services/cerchio_reminder.py"):
            assert "ogni due settimane" not in (BACKEND / f).read_text(), f"{f}: cadenza dichiarata"


class TestCn4PaginaLink:
    def test_il_footer_del_link_porta_alla_landing(self):
        src = (FE / "features" / "storefront" / "LinkPage.js").read_text()
        i = src.index('data-testid="link-page-join"')
        assert 'to="/entra-nella-rete"' in src[i - 120:i]
        assert 'to="/accedi" data-testid="link-page-join"' not in src
