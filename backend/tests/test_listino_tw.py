"""TW1 — il Listino (docs/LISTINO_PIANO_2026-07.md) + INVARIANTI.

Il listino e' un'interfaccia NUOVA sopra il motore VECCHIO: queste
guardie assicurano che resti cosi'. TestInvariants e' il contratto
anti-sfascio della Parte 0 del piano: se un'onda TW lo rompe, si
torna indietro.
"""

import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8000")
FRONTEND_SRC = BACKEND_DIR.parent / "frontend" / "src"


# ── PV7 — patto di responsabilita' (DPA art. 28) e la suite ──────────────
#
# Dal 30/7 la CREAZIONE di prodotti vendibili (service, event_ticket) e'
# gateata dal DPA acknowledgement (409 DPA_REQUIRED, services/dpa_guard).
# I test che creano prodotti via HTTP con l'org demo devono quindi
# firmare il patto PRIMA — con UN helper unico, mai copia-incolla.
#
# La firma della suite e' MARCATA (User-Agent dedicato) e viene rimossa
# a fine modulo: l'org demo torna allo stato onesto "non firmato",
# perche' la firma vera deve restare una scelta del founder (PV7.5:
# niente ack d'ufficio).

_PV7_SUITE_UA = "aurya-suite-dpa-guard-pv7"


def _pv7_live_db():
    """DB del server live (backend/.env), NON il test_db di default."""
    import re
    import pymongo
    env = (BACKEND_DIR / ".env").read_text()
    mongo = re.search(r'MONGO_URL="?([^"\n]+?)"?\n', env).group(1)
    name = re.search(r'DB_NAME="?([^"\n]+?)"?\n', env).group(1)
    return pymongo.MongoClient(mongo)[name]


def _ensure_dpa_ack(headers):
    """Firma il patto per l'org del token, se non gia' firmato.

    Idempotente e best-effort: se lo status non risponde si tenta
    comunque l'acknowledge (che e' a sua volta idempotente). La firma
    porta lo User-Agent marcatore cosi' il cleanup di fine modulo
    rimuove SOLO le firme della suite, mai una firma reale.
    """
    try:
        st = requests.get(f"{BASE_URL}/api/legal/dpa/status",
                          headers=headers, timeout=10).json()
        if st.get("acknowledged"):
            return
    except Exception:
        pass
    requests.post(
        f"{BASE_URL}/api/legal/dpa/acknowledge",
        headers={**headers, "User-Agent": _PV7_SUITE_UA},
        json={"locale": "it"}, timeout=10)


@pytest.fixture(scope="module", autouse=True)
def _pv7_suite_dpa_cleanup():
    """A fine modulo rimuove le firme DPA aggiunte dalla suite.

    Riconoscimento tramite lo User-Agent marcatore sull'audit row: una
    firma vera (fatta dal founder nel browser) ha un UA diverso e NON
    viene mai toccata. Per ogni firma della suite si rimuove sia
    l'audit row sia lo stamp durevole merchant_dpa_ack sull'org.
    """
    yield
    try:
        db = _pv7_live_db()
        rows = list(db.consent_audit.find({
            "document_type": "merchant_dpa",
            "user_agent": _PV7_SUITE_UA,
        }))
        for row in rows:
            db.consent_audit.delete_one({"id": row["id"]})
            if row.get("organization_id"):
                db.organizations.update_one(
                    {"id": row["organization_id"]},
                    {"$unset": {"merchant_dpa_ack": ""}})
    except Exception:
        pass  # cleanup best-effort: mai far fallire la suite qui


class TestInvariants:
    """Parte 0 del piano: cio' che il Listino NON deve mai toccare."""

    def test_i1_event_landing_alive(self):
        # la landing evento resta la pagina di vendita completa
        r = requests.get(f"{BASE_URL}/__seo/e/masseria-demo/"
                         "ritiro-yoga-test-s1-2026-10-02", timeout=10)
        assert r.status_code == 200

    def test_i1_service_landing_alive(self):
        # /p/ resta vivo (retrocompatibilita' + slot picker)
        app = (FRONTEND_SRC / "App.js").read_text()
        assert '/p/:orgSlug' in app or 'path="/p/' in app

    def test_i2_i3_checkout_untouched(self):
        """Il listino non riscrive il checkout: le firme chiave del
        motore ordini/booking restano al loro posto."""
        occ = (BACKEND_DIR / "services" / "order_creation_service.py").read_text()
        assert "dominant_mode" in occ
        bs = (BACKEND_DIR / "services" / "booking_service.py").read_text()
        assert "issue_bookings_for_order" in bs

    def test_i4_slot_engine_untouched(self):
        sg = (BACKEND_DIR / "services" / "slot_generator.py").read_text()
        assert "generate_available_slots" in sg

    def test_i8_no_new_collection(self):
        """Una riga di listino E' un Product service: la pagina usa la
        API products, nessuna collection nuova."""
        page = (FRONTEND_SRC / "features" / "listino"
                / "ListinoPage.js").read_text()
        assert "productsAPI.create" in page
        assert "productsAPI.update" in page
        assert "item_type: 'service'" in page

    def test_store_guard_source_unchanged(self):
        """Il gate store-first NON e' stato ammorbidito: il listino lo
        soddisfa creando lo store tecnico, non aggirandolo."""
        sg = (BACKEND_DIR / "services" / "store_guard.py").read_text()
        assert "store_required" in sg
        assert "require_public_home" in sg


class TestListinoTW1:
    def test_ensure_default_endpoint_exists(self):
        src = (BACKEND_DIR / "routers" / "stores.py").read_text()
        assert '"/ensure-default"' in src
        assert "_ensure_default_store(org_id, current_user)" in src

    def test_ensure_default_requires_auth(self):
        r = requests.post(f"{BASE_URL}/api/stores/ensure-default", timeout=10)
        assert r.status_code in (401, 403)

    def test_listino_defaults_are_lean(self):
        """Default snelli: richiesta (niente Stripe richiesto), agenda
        ufficiale (nessuna regola custom), pubblicato subito."""
        page = (FRONTEND_SRC / "features" / "listino"
                / "ListinoPage.js").read_text()
        assert "transaction_mode: 'request'" in page
        assert "is_published: true" in page
        # lo store tecnico si garantisce PRIMA di pubblicare
        assert "storesAPI.ensureDefault()" in page

    def test_services_new_redirects_to_listino(self):
        app = (FRONTEND_SRC / "App.js").read_text()
        assert 'path="/listino"' in app
        block = app.split('path="/services/new"')[1][:120]
        assert 'Navigate to="/listino"' in block
        # il wizard resta l'editor avanzato su /services/:id
        assert 'path="/services/:product_id"' in app

    def test_nav_has_listino(self):
        layout = (FRONTEND_SRC / "components" / "Layout.js").read_text()
        assert "'/listino'" in layout


class TestCs3ProfiloVisibile:
    """CS3 (founder, test d'uso 13/8) — l'operatore deve VEDERE il
    frutto delle sue configurazioni: bottone pieno «Vedi il tuo profilo
    online» su Listino e Profilo pubblico, e l'email dell'intervista
    leggibile in chiaro (il mailto da solo non sempre apre qualcosa)."""

    def test_listino_slug_dalla_fonte_giusta(self):
        """Il bug: /organizations/current/public-profile non espone
        public_slug, quindi il link non compariva MAI. La fonte e'
        /organizations/current, con fallback allo slug store."""
        src = (FRONTEND_SRC / "features" / "listino"
               / "ListinoPage.js").read_text()
        assert "api.get('/organizations/current')" in src
        assert "store_slug" in src, "manca il fallback allo slug store"
        assert "current/public-profile')" not in src, \
            "la fonte sbagliata (senza public_slug) e' tornata"
        assert 'data-testid="listino-view-profile"' in src
        assert "Vedi il tuo profilo online" in src

    def test_profilo_pubblico_bottone_primario(self):
        src = (FRONTEND_SRC / "features" / "settings"
               / "PublicProfilePage.js").read_text()
        assert 'data-testid="profile-view-online"' in src
        # niente variant="outline" sul bottone che mostra il risultato
        blocco = src.split('data-testid="profile-view-online"')[1][:300]
        assert 'variant="outline"' not in blocco

    def test_email_intervista_in_chiaro(self):
        src = (FRONTEND_SRC / "features" / "settings"
               / "PublicProfilePage.js").read_text()
        assert "from '../../config/brand'" in src and "BRAND_EMAIL" in src
        assert 'data-testid="interview-email-plain"' in src
        assert "mailto:info@aurya.life" not in src, \
            "l'indirizzo va preso da BRAND_EMAIL, non hardcodato"


class TestCs4PrimoSalvataggio:
    """CS4 (founder, test d'uso 13/8) — tre attriti del primo giro di
    configurazione: il link al profilo che appare solo dopo un refresh,
    il dropdown localita' che resta aperto dopo la scelta, e il gradino
    «Presentati» che resta muto anche a profilo mezzo compilato."""

    def test_public_profile_espone_lo_slug_risolto(self):
        """Il salvataggio genera lo slug (GT6) ma la risposta non lo
        diceva: la pagina lo scopriva solo con un refresh. La risposta
        usa il resolver vero (store pubblicato → public_slug legacy),
        non org.public_slug da solo, che mente alle org con store."""
        src = (BACKEND_DIR / "routers" / "organizations.py").read_text()
        blocco = src.split('@router.get("/current/public-profile")')[1]
        blocco = blocco.split('@router.patch')[0]
        assert "_resolve_public_slug_for_org" in blocco
        assert '"public_slug": resolved_slug' in blocco

    def test_save_aggiorna_lo_slug_senza_refresh(self):
        src = (FRONTEND_SRC / "features" / "settings"
               / "PublicProfilePage.js").read_text()
        assert "setSlug(res.data.public_slug)" in src, \
            "dopo il salvataggio lo slug deve arrivare dalla risposta"

    def test_dropdown_localita_si_chiude_dopo_la_scelta(self):
        """Selezionare scriveva form.city → value → setText, e il cambio
        di testo rilanciava la ricerca riaprendo la lista: si cerca solo
        se il testo l'ha battuto l'utente."""
        src = (FRONTEND_SRC / "features" / "settings"
               / "PublicProfilePage.js").read_text()
        assert "typedRef" in src
        assert "if (!typedRef.current) return undefined;" in src
        blocco = src.split("onMouseDown")[1][:120]
        assert "typedRef.current = false" in blocco

    def test_onboarding_presentati_dice_cosa_manca(self):
        """Backend: steps_detail.profile con percent (stessi 4 check
        della barra dell'editor: bio, cover, city, social) e missing."""
        src = (BACKEND_DIR / "routers" / "organizations.py").read_text()
        blocco = src.split("TW4 mondo snello")[1][:2400]
        for chiave in ('"bio"', '"cover"', '"city"', '"social"'):
            assert chiave in blocco, f"manca il check {chiave}"
        assert '"steps_detail": {"profile": profile_detail}' in src

    def test_inizia_mostra_progresso_e_suggerimenti(self):
        src = (FRONTEND_SRC / "features" / "onboarding"
               / "IniziaPage.js").read_text()
        assert "steps_detail" in src
        assert 'data-testid="inizia-profile-hint"' in src
        # il suggerimento cover/social scatta solo se mancano ENTRAMBI:
        # per spuntare il passo ne basta uno
        assert "missing?.includes('cover') && " \
               "profileDetail.missing?.includes('social')" in src


class TestAc1StrisciaGuida:
    """AC1 (ciclo Accompagnamento, 13/8) — la guida non ti molla:
    l'operatore poco digitale esce da /inizia per compilare profilo o
    listino e la striscia in testa gli dice a che punto e' e qual e'
    il prossimo passo. A configurazione completa sparisce."""

    STRIP = FRONTEND_SRC / "features" / "onboarding" / "OnboardingStrip.js"

    def test_striscia_derivata_e_silenziosa_a_fine_corsa(self):
        src = self.STRIP.read_text()
        # stato SEMPRE derivato dall'endpoint, mai flag locali
        assert "organizations/current/onboarding-status" in src
        # zero rumore per chi ha finito, e niente striscia nel legacy
        assert "if (!status || status.is_complete) return null;" in src
        assert "if (!('online' in s)) return null;" in src
        assert 'data-testid="onboarding-strip"' in src
        assert 'data-testid="strip-next-cta"' in src

    def test_profilo_monta_la_striscia_e_la_aggiorna_al_salva(self):
        src = (FRONTEND_SRC / "features" / "settings"
               / "PublicProfilePage.js").read_text()
        assert 'OnboardingStrip step="profile"' in src
        # il salvataggio E la cover (che puo' completare il passo)
        # incrementano la chiave: la striscia rilegge lo stato
        assert src.count("setObKey(k => k + 1)") >= 2

    def test_listino_monta_la_striscia_su_stato_derivato(self):
        src = (FRONTEND_SRC / "features" / "listino"
               / "ListinoPage.js").read_text()
        assert 'OnboardingStrip step="listino"' in src
        # refreshKey dai servizi PUBBLICATI: primo servizio online →
        # la striscia passa da "passo 2" a "ti manca Presentati"
        assert "rows.filter(r => r.published).length" in src


class TestAc2ProfiloEssenziale:
    """AC2 — il form del profilo era un muro di ~15 blocchi per un
    operatore poco digitale. L'essenziale (foto, chi sei, dove sei, un
    social) resta in vista; nome pubblico, carta d'identita', regione,
    contatti e specchietto Visibilita' vivono in "Per approfondire",
    chiuso finche' non lo si cerca. L'intervista resta visibile ma
    DOPO il Salva: invito, non interruzione."""

    PAGE = FRONTEND_SRC / "features" / "settings" / "PublicProfilePage.js"

    def test_avanzato_chiuso_di_default_con_toggle(self):
        src = self.PAGE.read_text()
        assert "const [advancedOpen, setAdvancedOpen] = useState(false)" in src
        assert 'data-testid="profile-advanced-toggle"' in src
        assert 'data-testid="profile-advanced-body"' in src
        assert "{advancedOpen && (" in src

    def test_campi_secondari_dentro_l_avanzato(self):
        """Nome pubblico, anno, ritratto, galleria, regione, contatti e
        Visibilita' stanno DOPO il toggle: se uno di loro risale
        nell'essenziale, il muro sta tornando."""
        src = self.PAGE.read_text()
        # si giudica solo il RENDER (dal marcatore Form in giu'):
        # le funzioni di upload sopra usano le stesse chiavi nei toast
        render = src.split("── Form ──")[1]
        avanzato = render.split('data-testid="profile-advanced-toggle"')[1]
        prima = render.split('data-testid="profile-advanced-toggle"')[0]
        # LK6 (founder, 14/8) — il ritratto e' SALITO in primo piano
        # accanto alla copertina: si controlla sotto, fuori da questa
        # lista.
        for chiave in ("publicName", "foundedYear",
                       "gallery", "region", "showContacts",
                       "visibilityTitle"):
            assert f"publicProfile.{chiave}" in avanzato, \
                f"{chiave} deve vivere in Per approfondire"
            assert f"publicProfile.{chiave}" not in prima, \
                f"{chiave} e' risalito nell'essenziale"
        # LK6 — ritratto accanto alla copertina, PRIMA dell'avanzato
        assert "publicProfile.portraitShort" in prima, \
            "il ritratto deve stare in primo piano, vicino alla copertina"

    def test_essenziale_prima_del_toggle(self):
        """Cover, bio, localita' e social restano nell'essenziale."""
        src = self.PAGE.read_text()
        prima = src.split('data-testid="profile-advanced-toggle"')[0]
        for chiave in ("publicProfile.cover", "publicProfile.bio",
                       "publicProfile.locationSearch",
                       "publicProfile.socials"):
            assert chiave in prima, f"{chiave} deve restare in vista"

    def test_intervista_dopo_il_salva_ma_visibile(self):
        """Il pannello intervista non interrompe la compilazione: sta
        dopo il bottone Salva, MAI dentro l'accordion (il badge
        Verificato deve restare un invito visibile)."""
        src = self.PAGE.read_text()
        salva = src.index("{t('publicProfile.save'")
        intervista = src.index('data-testid="interview-invite-panel"')
        toggle = src.index('data-testid="profile-advanced-toggle"')
        assert salva < intervista < toggle


class TestAc3SalvaAPortata:
    """AC3 — su un form lungo chi modifica in alto non trova il Salva
    in fondo: barra fissa "Hai modifiche non salvate" che compare SOLO
    a modifiche pendenti e sparisce al salvataggio."""

    PAGE = FRONTEND_SRC / "features" / "settings" / "PublicProfilePage.js"

    def test_barra_solo_a_modifiche_pendenti(self):
        src = self.PAGE.read_text()
        assert 'data-testid="unsaved-bar"' in src
        assert "{dirty && (" in src, "la barra deve comparire solo se dirty"
        # dirty = confronto con l'ultima fotografia SALVATA, mai un flag
        assert "snapshot(form, orgName) !== savedSnap" in src

    def test_base_del_confronto_a_load_e_save(self):
        """La fotografia si aggiorna al load e a ogni salvataggio:
        senza, la barra resterebbe accesa dopo il Salva."""
        src = self.PAGE.read_text()
        assert src.count("markSaved(") >= 3  # definizione + load + save

    def test_upload_non_lasciano_la_barra_accesa(self):
        """Cover/ritratto/foto sono persistiti dal server al volo: ogni
        upload aggiorna il proprio campo nella fotografia salvata senza
        coprire altre modifiche in corso (markFieldSaved puntuale)."""
        src = self.PAGE.read_text()
        assert "markFieldSaved('cover_url'" in src
        assert "markFieldSaved('portrait_url'" in src
        assert "markFieldSaved('photos'" in src


class TestAc4RimozioneFotoIstantanea:
    """AC4 — modello di salvataggio coerente: gli upload erano
    istantanei ma la rimozione richiedeva ANCHE il Salva, con una nota
    che lo spiegava. Se serve una nota, il modello e' sbagliato: ora
    un click rimuove e persiste."""

    PAGE = FRONTEND_SRC / "features" / "settings" / "PublicProfilePage.js"

    def test_rimozione_persiste_subito(self):
        src = self.PAGE.read_text()
        blocco = src.split("const removePhoto")[1][:700]
        assert "api.patch('/organizations/current/public-profile'" in blocco
        assert "markFieldSaved('photos', filtered)" in blocco, \
            "la rimozione persistita non deve accendere la barra AC3"
        assert "photoRemoved" in blocco, "serve la conferma a schermo"

    def test_via_la_nota_richiede_salva(self):
        src = self.PAGE.read_text()
        assert "galleryHint" not in src
        assert "richiede Salva" not in src


class TestAc5ParoleUmane:
    """AC5 — passata microcopy per il non-tecnico: via il gergo
    ("Tagline", "Impression"), via l'intestazione "Dati base" orfana
    nel menu snello, etichetta aria dedicata alla X del banner cookie."""

    def _locale(self, lang, ns):
        import json
        return json.loads(
            (FRONTEND_SRC / "locales" / lang / f"{ns}.json").read_text())

    def test_tagline_diventa_una_frase_che_ti_presenta(self):
        it = self._locale("it", "settings")["publicProfile"]
        assert it["tagline"] == "Una frase che ti presenta"
        assert "Tagline" not in it["tagline"]
        # anche l'hint Visibilita' parla italiano, non ad-tech
        assert "Impression" not in it["visibilityHint"]

    def test_impression_diventa_apparizioni(self):
        vis = self._locale("it", "common")["visibility"]
        assert vis["impressions"] == "Apparizioni"
        dash = self._locale("it", "dashboard")["home"]
        assert dash["visibility_impressions"] == "apparizioni"

    def test_menu_snello_senza_intestazione_orfana(self):
        """entityNav e' vuoto nel mondo snello: l'intestazione "Dati
        base" non deve galleggiare sopra il nulla."""
        src = (FRONTEND_SRC / "components" / "Layout.js").read_text()
        assert "entityNav.length > 0 && (" in src

    def test_x_del_banner_cookie_con_etichetta_propria(self):
        src = (FRONTEND_SRC / "components" / "legal"
               / "CookieConsentBanner.js").read_text()
        assert "cookie_banner.close_button" in src
        for lang in ("it", "en", "de", "fr"):
            legal = self._locale(lang, "legal")["cookie_banner"]
            assert legal.get("close_button"), f"{lang}: manca close_button"


class TestAc6AiutoBio:
    """AC6 — lo scoglio del primo giro non e' tecnico: e' scrivere di
    se'. Sotto il campo bio, tre domande-guida e un esempio vero. Solo
    a bio vuota: chi ha gia' scritto non vede rumore."""

    PAGE = FRONTEND_SRC / "features" / "settings" / "PublicProfilePage.js"

    def test_aiuto_solo_a_bio_vuota(self):
        src = self.PAGE.read_text()
        assert 'data-testid="bio-helper"' in src
        blocco = src.split('data-testid="bio-helper"')[0][-400:]
        assert "!(form.bio || '').trim() && (" in blocco, \
            "l'aiuto deve sparire appena la bio esiste"

    def test_tre_domande_e_un_esempio(self):
        import json
        pp = json.loads((FRONTEND_SRC / "locales" / "it"
                         / "settings.json").read_text())["publicProfile"]
        assert pp["bioHelperQuestions"].count("?") == 3
        assert "Es." in pp["bioHelperExample"]
        # l'esempio e' una bio VERA e completa, non un frammento
        assert len(pp["bioHelperExample"]) > 80


class TestLiAuryaInTesta:
    """LI (founder, 13/8) — contratto e GDPR si leggono con AURYA, non
    con la persona fisica. Il titolare NON cambia (art. 13 GDPR: deve
    restare identificabile): cambia l'ordine di presentazione. Queste
    guardie impediscono al nome di tornare in primo piano da solo."""

    LEGAL_DIR = BACKEND_DIR / "legal"

    def test_nome_mai_da_solo_a_inizio_riga(self):
        """In privacy/termini/DPA il nome della persona compare SOLO
        preceduto da una formula "servizio di" (o equivalente per
        lingua) o accanto ad Aurya: mai come intestazione a se'."""
        ok_prefissi = ("servizio di", "a service of", "ein Dienst von",
                       "un service de")
        for doc in self.LEGAL_DIR.glob("*.md"):
            for n, riga in enumerate(doc.read_text("utf-8").splitlines(), 1):
                if "Davide De Filippis" not in riga:
                    continue
                pulita = riga.strip().lstrip("*-\u2022 ").strip()
                assert not pulita.startswith("Davide De Filippis"), \
                    f"{doc.name}:{n} - il nome e' tornato in primo piano"
                assert ("Aurya" in riga
                        or any(p in riga for p in ok_prefissi)), \
                    f"{doc.name}:{n} - il nome senza Aurya accanto"

    def test_dpa_ha_aurya_come_parte(self):
        """Le parti del DPA: il Responsabile e' platform_controller_name
        = Aurya, identificato da platform_controller_legal."""
        from services.merchant_legal_template_service import TemplateVars
        v = TemplateVars(merchant_name="Test", merchant_email="t@t.it")
        assert v.platform_controller_name == "Aurya"
        assert v.platform_controller_legal == "Davide De Filippis"
        for lang in ("it", "en", "de", "fr"):
            tpl = (self.LEGAL_DIR / f"dpa_{lang}.md").read_text("utf-8")
            assert "{{platform_controller_legal}}" in tpl, \
                f"dpa_{lang}: manca l'identita' legale accanto ad Aurya"

    def test_sub_processors_espone_aurya(self):
        src = (BACKEND_DIR / "routers" / "legal.py").read_text()
        blocco = src.split('"controller": {')[1][:400]
        assert '"name": BRAND_NAME' in blocco
        assert '"legal_entity": "Davide De Filippis"' in blocco
        # e la pagina mostra la riga secondaria solo se presente
        page = (FRONTEND_SRC / "pages" / "SubProcessorsPage.js").read_text()
        assert "legal_entity" in page

    def test_hash_v24_allineato_ai_testi(self):
        import hashlib
        from core.legal_versions import (CURRENT_VERSION_TAG,
                                         CURRENT_VERSION_HASH)
        assert CURRENT_VERSION_TAG == "v2.6"
        priv = (self.LEGAL_DIR / "privacy_it.md").read_text("utf-8")
        terms = (self.LEGAL_DIR / "terms_it.md").read_text("utf-8")
        atteso = hashlib.sha256(
            (priv + "\n\n--- TERMS BUNDLE ---\n\n" + terms).encode()
        ).hexdigest()[:16]
        assert CURRENT_VERSION_HASH == atteso


class TestAc7CondividiWhatsapp:
    """AC7 — la pagina e' viva ma nessuno la vedra' finche' l'operatore
    non la condivide, e il suo canale e' WhatsApp: nel riquadro "Sei
    online!" un bottone wa.me con il messaggio gia' scritto e il link
    assoluto alla pagina."""

    PAGE = FRONTEND_SRC / "features" / "onboarding" / "IniziaPage.js"

    def test_bottone_wa_me_con_messaggio_pronto(self):
        src = self.PAGE.read_text()
        assert 'data-testid="share-whatsapp"' in src
        assert "https://wa.me/?text=" in src
        assert "encodeURIComponent" in src, "il messaggio va URL-encodato"
        # link ASSOLUTO: wa.me su un path relativo non porta da nessuna parte
        assert "window.location.origin}${links.profile}" in src

    def test_messaggio_x4_lingue(self):
        import json
        for lang in ("it", "en", "de", "fr"):
            ob = json.loads((FRONTEND_SRC / "locales" / lang
                             / "dashboard.json").read_text())["onboarding"]
            assert ob.get("wa_share_cta"), f"{lang}: manca wa_share_cta"
            assert "{{url}}" in ob.get("wa_share_message", ""), \
                f"{lang}: il messaggio deve contenere il link"


class TestProfileListinoTW2:
    """TW2 — il profilo E' il negozio: listino sull'endpoint pubblico,
    card rete con da-X-euro, OfferCatalog nella shell. I bottoni
    portano alla landing /p/ esistente (zero nuovo checkout: I3)."""

    def test_operator_endpoint_exposes_listino(self):
        r = requests.get(f"{BASE_URL}/api/public/operator/masseria-demo",
                         timeout=10)
        assert r.status_code == 200
        listino = r.json().get("listino")
        assert isinstance(listino, list) and len(listino) >= 1
        row = listino[0]
        for field in ("name", "slug", "price", "on_request",
                      "transaction_mode", "service_mode"):
            assert field in row

    def test_network_members_have_price_from(self):
        """LC8 — la lista membri puo' essere legittimamente VUOTA:
        LC3 ha tolto le org demo dalla rete e i membri veri arrivano
        con le interviste. La guardia sul payload (services_count,
        price_from) si riarma da sola al primo membro reale."""
        r = requests.get(f"{BASE_URL}/api/public/network/members", timeout=10)
        assert r.status_code == 200
        items = r.json()["items"]
        for m in items:
            assert "services_count" in m and "price_from" in m

    def test_shell_has_offer_catalog(self):
        r = requests.get(f"{BASE_URL}/__seo/o/masseria-demo", timeout=10)
        assert r.status_code == 200
        assert '"@type": "OfferCatalog"' in r.text
        assert '"@type": "Service"' in r.text

    def test_profile_buttons_link_to_existing_landing(self):
        page = (FRONTEND_SRC / "features" / "storefront"
                / "OperatorProfilePage.js").read_text()
        assert "profile-listino" in page
        # il bottone usa la landing /p/ esistente, non un checkout nuovo
        assert "/p/${org_slug}/${row.slug}" in page
        assert "Richiedi appuntamento" in page and "Prenota" in page


class TestPotaturaTW3:
    """TW3 — potatura REVERSIBILE: mondo snello di default, commerce
    legacy dietro flag per-org. Codice mai eliminato (R1), ritorno in
    un click senza deploy (R2, R5)."""

    def test_flag_defaults_off(self):
        """Il flag vive sul modello Organization, default False."""
        src = (BACKEND_DIR / "models" / "organization.py").read_text()
        assert "legacy_commerce: bool = False" in src

    def test_admin_toggle_endpoint(self):
        """R2: il system admin riaccende il legacy senza deploy."""
        src = (BACKEND_DIR / "routers" / "admin.py").read_text()
        assert "legacy-commerce" in src
        r = requests.put(
            f"{BASE_URL}/api/admin/organizations/x/legacy-commerce",
            json={"enabled": True}, timeout=10)
        assert r.status_code in (401, 403)

    def test_lean_menu_gated_in_layout(self):
        """Mondo snello: le voci legacy (store, prodotti, corsi) e il
        menu entita' compaiono SOLO con legacyCommerce acceso."""
        layout = (FRONTEND_SRC / "components" / "Layout.js").read_text()
        assert "legacyCommerce" in layout
        assert "!legacyCommerce" in layout
        # il mondo snello contiene le 5 voci operative
        lean = layout.split("!legacyCommerce")[1]
        for href in ("'/listino'", "'/events'", "'/calendar'",
                     "'/orders'", "'/public-profile'"):
            assert href in lean[:900]

    def test_r5_legacy_menu_still_in_source(self):
        """R5: il menu legacy NON e' stato eliminato, e' solo dietro
        flag — con legacyCommerce true torna tutto."""
        layout = (FRONTEND_SRC / "components" / "Layout.js").read_text()
        assert "&& legacyCommerce" in layout
        for legacy_href in ("'/stores'", "'/products'", "'/courses'"):
            assert legacy_href in layout

    def test_storefront_redirects_to_profile(self):
        """I6: /s/ vetrina non muore, redirige al profilo /o/."""
        app = (FRONTEND_SRC / "App.js").read_text()
        assert "StoreToProfileRedirect" in app
        # legal e checkout RESTANO vivi (servono a Stripe e GDPR: I2, I7)
        assert 'path="/s/:slug/privacy"' in app
        assert 'path="/s/:slug/terms"' in app
        assert "checkout-success" in app

    def test_shell_storefront_serves_operator_meta(self):
        """La shell SEO di /s/{slug} risponde col profilo operatore."""
        r = requests.get(f"{BASE_URL}/__seo/s/masseria-demo", timeout=10)
        assert r.status_code == 200
        assert '/o/masseria-demo"' in r.text

    def test_store_guard_now_self_heals(self):
        """Profile-first: il gate store auto-crea lo store tecnico
        invece di fermare l'operatore (il 409 resta ultima difesa)."""
        sg = (BACKEND_DIR / "services" / "store_guard.py").read_text()
        assert "_ensure_default_store" in sg


class TestOnboardingTW4:
    """TW4 — onboarding a 3 passi: Presentati → Listino → Online.
    Il ritiro e' un suggerimento DOPO, non un gradino. Le org legacy
    tengono i 5 passi storici (coerenza con R5)."""

    def test_endpoint_has_lean_and_legacy_paths(self):
        src = (BACKEND_DIR / "routers" / "organizations.py").read_text()
        # ramo snello sui 3 passi...
        assert '"listino_filled"' in src
        assert '"online"' in src
        # ...gated dal flag TW3, col ramo legacy intatto
        assert 'legacy_commerce' in src
        assert '"retreat_published"' in src

    def test_lean_status_exposes_signals(self):
        """La dashboard (GT1b) legge stripe/ritiri anche nel mondo
        snello: vivono in `signals`, fuori dalla checklist."""
        src = (BACKEND_DIR / "routers" / "organizations.py").read_text()
        assert '"signals"' in src
        home = (FRONTEND_SRC / "features" / "dashboard"
                / "OperatorHome.js").read_text()
        assert "signals" in home

    def test_inizia_page_is_lean_first(self):
        page = (FRONTEND_SRC / "features" / "onboarding"
                / "IniziaPage.js").read_text()
        # i 3 passi snelli puntano a profilo e listino
        assert "'/public-profile'" in page and "'/listino'" in page
        assert "listino_filled" in page and "'online' in s" in page
        # il ritiro e' il suggerimento post-onboarding
        assert "inizia-next-retreat" in page
        assert "'/events/new'" in page
        # il percorso legacy a 5 passi resta nel sorgente (R5)
        assert "store_created" in page and "retreat_published" in page

    def test_ga4_first_service_online(self):
        page = (FRONTEND_SRC / "features" / "listino"
                / "ListinoPage.js").read_text()
        assert "trackEvent('first_service_online')" in page

    def test_deploy_runbook_exists(self):
        doc = (BACKEND_DIR.parent / "docs"
               / "RUNBOOK_DEPLOY_LISTINO.md").read_text()
        assert "legacy_commerce" in doc and "Rollback" in doc


class TestRitiriRS:
    """Ciclo Ritiri (docs/RITIRI_INTEGRITA_PIANO_2026-07.md).
    RS0: /listino dentro la shell dell'app. RS1: /events e' una
    pagina di soli ritiri, non un redirect all'hub prodotti."""

    def test_rs0_listino_in_app_shell(self):
        page = (FRONTEND_SRC / "features" / "listino"
                / "ListinoPage.js").read_text()
        assert "<AppLayout>" in page and "<Header" in page

    def test_rs1_events_is_dedicated_page(self):
        app = (FRONTEND_SRC / "App.js").read_text()
        # /events monta la pagina ritiri, non il redirect all'hub
        block = app.split('path="/events"')[1][:160]
        assert "EventsListPage" in block
        assert 'Navigate to="/products?type=event_ticket"' not in app

    def test_rs1_events_page_speaks_ritiri(self):
        page = (FRONTEND_SRC / "features" / "events"
                / "EventsListPage.js").read_text()
        assert "<AppLayout>" in page
        assert "EventsGrid" in page
        # niente vocabolario e-commerce nella casa dei ritiri
        assert "prodott" not in page.lower().replace(
            "hub multi-tipo: productspage", "")

    def test_rs1_products_hub_still_alive_for_legacy(self):
        """R1/R5: l'hub multi-tipo resta raggiungibile su /products."""
        app = (FRONTEND_SRC / "App.js").read_text()
        assert 'path="/products"' in app
        assert (FRONTEND_SRC / "features" / "products"
                / "ProductsPage.js").exists()


class TestWizardRS2:
    """RS2 — il wizard del ritiro: 4 passi, linguaggio esplicativo,
    stesso motore (payload e endpoint INTATTI: I1-I3)."""

    def _src(self):
        return (FRONTEND_SRC / "features" / "events"
                / "EventWizard.js").read_text()

    def test_four_steps_only(self):
        src = self._src()
        i = src.index("const TABS = [")
        block = src[i:i + 400]
        for key in ("'ritiro'", "'prezzo'", "'regole'", "'publish'"):
            assert key in block
        for gone in ("'base'", "'where'", "'tickets'", "'program'",
                     "'payments'"):
            assert gone not in block

    def test_payload_engine_untouched(self):
        """Il submit parla ancora la stessa lingua del backend: nessun
        campo del payload wizard e' stato perso nella riorganizzazione."""
        src = self._src()
        for field in ("payment_plan", "transaction_mode", "store_ids",
                      "cost_source: costSource", "wizardCreate",
                      "cancellation_policy", "attendee_fields"):
            assert field in src, field

    def test_explicative_language(self):
        src = self._src()
        # come si prenota, spiegato; preset di cancellazione; opzioni
        assert "Come si prenota" in src
        assert "policy-presets" in src and "CANCELLATION_PRESETS" in src
        assert "tiers-toggle" in src
        assert "Opzioni di partecipazione" in src
        # il percorso ritiri non manda piu' all'hub prodotti
        assert "/products?type=event_ticket" not in src

    def test_deep_link_i18n_loaded(self):
        """Fix bug preesistente: al deep-link su /events/new i bundle
        i18n admin non erano caricati (li portava solo Layout)."""
        assert "import '../../i18n-admin'" in self._src()

    def test_dashboard_back_goes_to_events(self):
        dash = (FRONTEND_SRC / "features" / "events"
                / "EventDashboardPage.js").read_text()
        assert '"/products?type=event_ticket"' not in dash


class TestPattiChiariRS3:
    """RS3 — le condizioni dell'operatore: un posto per scriverle
    (Impostazioni), un blocco solo per accettarle (checkout), sempre
    presenti (fallback autogenerato), timbrate sull'ordine."""

    def test_org_default_policy_endpoint(self):
        """La policy org-level si salva via PUT /organizations/current
        con validazione degli scaglioni."""
        src = (BACKEND_DIR / "routers" / "organizations.py").read_text()
        assert "default_cancellation_policy" in src
        assert "giorni decrescenti e rimborsi non crescenti" in src

    def test_conditions_card_in_settings(self):
        """Raggiungibile nel mondo snello: vive in Impostazioni, non
        dentro Stores. (PS5: l'editor legale custom non e' piu' qui —
        vedi TestPotaturaPs5 — ma la politica di cancellazione resta.)"""
        card = (FRONTEND_SRC / "features" / "settings" / "sections"
                / "SalesConditionsCard.jsx").read_text()
        assert "default_cancellation_policy" in card
        settings = (FRONTEND_SRC / "features" / "settings"
                    / "SettingsPage.js").read_text()
        assert "SalesConditionsCard" in settings

    def test_wizard_inherits_org_policy(self):
        wiz = (FRONTEND_SRC / "features" / "events"
               / "EventWizard.js").read_text()
        assert "default_cancellation_policy" in wiz
        assert "Le mie condizioni" in wiz

    def test_checkout_single_consent_block(self):
        """Un solo blocco consensi: niente checkbox T&C legacy separata,
        blocco GDPR visibile anche senza legal pubblicati."""
        # PN2 — il JSX del checkout e' estratto da StorefrontPage.js in
        # components/checkout/ + hooks/useCheckoutForm.js: l'invariante
        # vale sull'unione dei sorgenti del checkout, non su un file solo.
        storefront = FRONTEND_SRC / "features" / "storefront"
        sf = "\n".join(p.read_text() for p in [
            storefront / "StorefrontPage.js",
            storefront / "components" / "checkout" / "CheckoutForm.jsx",
            storefront / "components" / "checkout" / "OrderSummary.jsx",
            storefront / "hooks" / "useCheckoutForm.js",
        ])
        # la checkbox legacy F4 standalone non esiste piu'
        assert "checked={termsAccepted}" not in sf
        # le condizioni specifiche vivono DENTRO il blocco unico
        assert "condizioni specifiche" in sf
        # il blocco non e' piu' gated da gdprRequired
        assert ("{gdprRequired && (!isCustomerAuthenticated"
                not in sf)

    def test_consents_stamped_even_without_published_legal(self):
        """Il backend timbra i consensi espressi anche con legal
        autogenerati (versione autogen:v0); l'enforcement resta gated."""
        ocs = (BACKEND_DIR / "services"
               / "order_creation_service.py").read_text()
        assert "gdpr_flags_given" in ocs
        assert '"autogen:v0"' in ocs
        # RS3 — la policy di cancellazione resta timbrata sull'ordine
        assert "cancellation_policy_snapshot" in ocs

    def test_checkout_handoff_survives_redirect(self):
        """Fix regressione TW3: /s/x?checkout=1 e il preloadCart delle
        landing NON redirigono al profilo (il motore di acquisto
        resta intatto: I2, I3)."""
        app = (FRONTEND_SRC / "App.js").read_text()
        assert "wantsCheckout" in app
        assert "preloadCart" in app

    def test_conditions_links_on_public_pages(self):
        prof = (FRONTEND_SRC / "features" / "storefront"
                / "OperatorProfilePage.js").read_text()
        assert "profile-conditions" in prof
        for page in ("ProductLandingPage.js", "ReservationLandingPage.js"):
            src = (FRONTEND_SRC / "features" / "storefront" / page).read_text()
            assert "landing-conditions" in src, page


class TestClientiRS4:
    """RS4 — Clienti e newsletter tornano nel mondo snello: il consenso
    raccolto (RS3) deve essere VISIBILE e azionabile dall'operatore."""

    def test_customers_in_lean_menu(self):
        layout = (FRONTEND_SRC / "components" / "Layout.js").read_text()
        lean = layout.split("!legacyCommerce")[1][:1400]
        assert "customers-light" in lean

    def test_insights_links_newsletter_forms(self):
        page = (FRONTEND_SRC / "features" / "customer-insights"
                / "CustomerInsightsPage.jsx").read_text()
        assert "newsletter-forms-link" in page
        assert "'/newsletter-forms'" in page or '"/newsletter-forms"' in page

    def test_insights_endpoints_declare_module(self):
        """Coerenza MD2: la vista Clienti era protetta solo dal menu,
        ora il backend dichiara il modulo customers_light."""
        ma = (BACKEND_DIR / "services" / "module_access.py").read_text()
        assert '"customer_insights": "customers_light"' in ma
        router = (BACKEND_DIR / "modules" / "customer_insights"
                  / "router.py").read_text()
        assert "_require_insights_module" in router
        # tutte le route autenticate portano il gate
        assert router.count("_require_insights_module()") >= 6

    def test_insights_still_open_for_active_module(self):
        """MD1 attiva tutto di default: il gate non deve chiudere fuori
        le org esistenti (403 solo a modulo spento)."""
        r = requests.get(f"{BASE_URL}/api/customer-insights/overview",
                         timeout=10)
        # senza auth: 401/403 auth, NON un 500 da dependency rotta
        assert r.status_code in (401, 403)


class TestFunnelRS5:
    """RS5 — integrita' del funnel: fonte unica del consenso, Passaporto
    onesto, audit senza doppioni, promessa sull'email."""

    def test_magic_link_on_request_confirm(self):
        """Il magic link parte anche alla CONFERMA di una richiesta,
        non solo al pagamento (prima l'account restava pending e
        irraggiungibile)."""
        src = (BACKEND_DIR / "routers" / "orders.py").read_text()
        assert "send_claim_email_if_needed" in src

    def test_doc_audit_only_on_real_click(self):
        """Niente doppioni: l'audit dei documenti si scrive solo su
        click reale (il loggato ha gia' il record CG-4 dal signup)."""
        ocs = (BACKEND_DIR / "services"
               / "order_creation_service.py").read_text()
        assert "_clicked_docs" in ocs

    def test_newsletter_stats_include_checkout_optins(self):
        """Fonte unica: la vista newsletter conta anche i consensi
        dal checkout (email distinte, revoche escluse, unione onesta)."""
        nf = (BACKEND_DIR / "routers" / "newsletter_forms.py").read_text()
        assert "checkout_optins" in nf and "reachable_total" in nf
        page = (FRONTEND_SRC / "features" / "newsletter"
                / "NewsletterPage.js").read_text()
        assert "checkout-optins-line" in page
        assert "customers-light" in page  # il link 'Vedile in Clienti'

    def test_checkout_email_promise(self):
        # PN2 — la promessa email vive nel form estratto (CheckoutForm).
        sf = (FRONTEND_SRC / "features" / "storefront" / "components"
              / "checkout" / "CheckoutForm.jsx").read_text()
        assert "email-promise" in sf


class TestProfiloNegozioPN0:
    """PN0 (docs/PROFILO_NEGOZIO_PIANO_2026-07.md) — condizioni
    trovabili, ritiri sempre sul profilo, zero 'store' nei percorsi
    snelli."""

    def test_profile_shows_retreats_in_every_phase(self):
        prof = (FRONTEND_SRC / "features" / "storefront"
                / "OperatorProfilePage.js").read_text()
        # la sezione ritiri non e' piu' gated dalla fase del sito
        i = prof.index('id="ritiri"')
        assert "sitePhase !== 'network' && (" not in prof[max(0, i - 400):i]
        # e il bottone 'Visita il negozio' non esiste piu'
        assert "visitStore" not in prof

    def test_no_store_copy_in_retreat_path(self):
        hint = (FRONTEND_SRC / "components"
                / "DirectoryListingHint.jsx").read_text()
        assert "dal tuo store" not in hint
        assert "profilo pubblico" in hint
        import json as _json
        prod = _json.loads((FRONTEND_SRC / "locales" / "it"
                            / "products.json").read_text())
        flat = _json.dumps(prod, ensure_ascii=False)
        assert "pubblica lo store" not in flat.lower()
        assert "Pubblica uno store" not in flat
        dash = (FRONTEND_SRC / "locales" / "it"
                / "dashboard.json").read_text()
        assert "appare sul tuo profilo" in dash

    def test_conditions_discoverable(self):
        """La card Condizioni sta in alto in Impostazioni e ha rimandi
        da Profilo pubblico e da /inizia."""
        settings = (FRONTEND_SRC / "features" / "settings"
                    / "SettingsPage.js").read_text()
        assert (settings.index("<SalesConditionsCard />")
                < settings.index("<LanguageSelector />"))
        pub = (FRONTEND_SRC / "features" / "settings"
               / "PublicProfilePage.js").read_text()
        assert "conditions-shortcut" in pub
        inizia = (FRONTEND_SRC / "features" / "onboarding"
                  / "IniziaPage.js").read_text()
        assert "lean_profile_conditions" in inizia

    def test_pn1_listino_rows_ready_for_inline(self):
        """PN1 — la riga di listino pubblica porta cio' che serve
        all'acquisto inline: product_id, flag slot, opzioni."""
        r = requests.get(f"{BASE_URL}/api/public/operator/masseria-demo",
                         timeout=10)
        row = r.json()["listino"][0]
        for field in ("product_id", "has_availability_slots",
                      "service_options", "allow_custom_request"):
            assert field in row, field


class TestInlineCheckoutPN3:
    """PN3 — compra dal profilo, tutto in pagina: la riga di listino si
    espande su un harness (InlineServiceCheckout) che RIUSA il checkout
    dello storefront. La landing /p/ resta viva come link secondario."""

    def test_profile_primary_cta_expands_inline(self):
        """Il CTA primario della riga e' un bottone che espande in
        pagina (niente navigazione a /p/); il link /p/ resta come
        'Vedi dettagli' secondario."""
        prof = (FRONTEND_SRC / "features" / "storefront"
                / "OperatorProfilePage.js").read_text()
        assert "InlineServiceCheckout" in prof
        assert 'data-testid="listino-cta"' in prof
        # il bottone primario espande (aria-expanded), non naviga
        i = prof.index('data-testid="listino-cta"')
        assert "aria-expanded" in prof[i - 200:i + 200]
        # la landing /p/ sopravvive come link secondario sulla riga
        assert "/p/${org_slug}/${row.slug}" in prof
        assert "Vedi dettagli" in prof

    def test_inline_checkout_reuses_shared_form(self):
        """Un solo checkout nel codice (I2/I3): l'harness monta
        CheckoutForm/OrderSummary/useCheckoutForm dello storefront e
        NON reimplementa submit/consensi."""
        inline = (FRONTEND_SRC / "features" / "storefront" / "components"
                  / "checkout" / "InlineServiceCheckout.jsx").read_text()
        assert "import CheckoutForm from './CheckoutForm'" in inline
        assert "import OrderSummary from './OrderSummary'" in inline
        assert "useCheckoutForm" in inline
        assert "useStorefrontCart" in inline
        # zero secondo submit: l'ordine parte SOLO dal form condiviso
        assert "submitOrder" not in inline
        assert "order-request" not in inline
        # slot reali dallo stesso endpoint pubblico della landing /p/
        assert "getServiceSlots" in inline
        assert "AvailabilityCalendarSlotPicker" in inline

    def test_p_landing_still_alive(self):
        """La landing /p/ resta viva (SEO + link esterni): route nel
        router e payload pubblico che risponde."""
        app = (FRONTEND_SRC / "App.js").read_text()
        assert '/p/:orgSlug' in app or 'path="/p/' in app
        r = requests.get(
            f"{BASE_URL}/api/public/products/masseria-demo/seduta-di-reiki",
            timeout=10)
        assert r.status_code == 200
        assert r.json()["product"]["name"]


class TestRitiroSenzaStorePN4:
    """PN4/PN5 — il ritiro si compra senza mai vedere lo store: in
    contesto marketplace il CTA della landing /e/ apre il checkout
    CONDIVISO in pagina (InlineEventCheckout); l'handoff a /s/ resta
    SOLO per il guscio store (?store=1, org legacy_commerce)."""

    def _landing_src(self):
        return (FRONTEND_SRC / "features" / "storefront"
                / "EventLandingPage.js").read_text()

    def test_marketplace_checkout_opens_inline_not_on_s(self):
        """(a) niente piu' navigazione a /s/ per il checkout
        marketplace: il vecchio handoff openCheckout/mktp e' sparito,
        il ramo !fromStore apre l'overlay inline e basta."""
        src = self._landing_src()
        assert "InlineEventCheckout" in src
        # il vecchio handoff marketplace non esiste piu'
        assert "preloadCart.openCheckout" not in src
        assert "preloadCart.mktp" not in src
        # dentro handleProceed: prima il gate marketplace (inline),
        # POI l'unica navigate a /s/ (ramo store)
        i = src.index("const handleProceed")
        block = src[i:i + 1600]
        j = block.index("if (!fromStore)")
        inline_branch = block[j:block.index("}", j)]
        assert "setInlineOpen(true)" in inline_branch
        assert "navigate(" not in inline_branch
        assert j < block.index("navigate(`/s/${orgSlug}`")

    def test_inline_event_checkout_reuses_shared_form(self):
        """(b) un solo checkout nel codice (I2/I3): l'harness monta
        CheckoutForm/OrderSummary/useCheckoutForm dello storefront e
        NON reimplementa submit/consensi."""
        inline = (FRONTEND_SRC / "features" / "storefront" / "components"
                  / "checkout" / "InlineEventCheckout.jsx").read_text()
        assert "import CheckoutForm from './CheckoutForm'" in inline
        assert "import OrderSummary from './OrderSummary'" in inline
        assert "useCheckoutForm" in inline
        # zero secondo submit: l'ordine parte SOLO dal form condiviso
        assert "submitOrder" not in inline
        assert "order-request" not in inline
        # il payload evento resta quello dello store (fan-out F3)
        assert "ticket_tier_id" in inline
        assert "occurrence_id" in inline

    def test_no_store_copy_in_marketplace_path(self):
        """PN5 — copy pass: niente 'negozio' nel percorso marketplace
        (harness inline + chiave gdprRequired neutralizzata)."""
        inline = (FRONTEND_SRC / "features" / "storefront" / "components"
                  / "checkout" / "InlineEventCheckout.jsx").read_text()
        # (il nome del piano PROFILO_NEGOZIO nei commenti non conta)
        assert "negozio" not in inline.lower().replace(
            "profilo_negozio_piano", "")
        import json as _json
        sf = _json.loads((FRONTEND_SRC / "locales" / "it"
                          / "storefront.json").read_text())
        assert "negozio" not in sf["errors"]["gdprRequired"].lower()

    def test_i1_event_landing_still_alive(self):
        """(c) invariante I1: la landing /e/ risponde 200 anche col
        checkout inline a bordo."""
        r = requests.get(f"{BASE_URL}/__seo/e/masseria-demo/"
                         "ritiro-yoga-test-s1-2026-10-02", timeout=10)
        assert r.status_code == 200


class TestListinoUnPassoLM1:
    """LM1 (docs/LISTINO_MARKETPLACE_PIANO_2026-07.md) — la voce di
    listino si configura in un passo: base sempre visibile + due
    accordion progressivi sulla riga espansa (solo righe salvate)."""

    PAGE = FRONTEND_SRC / "features" / "listino" / "ListinoPage.js"

    def test_accordion_progressivi_nella_riga(self):
        """I due momenti LM1 esistono nella riga espansa e 'Impostazioni
        avanzate' (label PS2) resta il percorso avanzato."""
        page = self.PAGE.read_text()
        assert "Opzioni e varianti" in page
        assert "Prenotazione e incasso" in page
        assert "Impostazioni avanzate" in page
        # progressione: una sezione aperta alla volta, mai tutte
        assert "openSection" in page

    def test_riuso_editor_opzioni_senza_copia(self):
        """ServiceOptionsEditor e StripeRequiredAlert sono riusati
        as-is: import dai moduli originali, nessuna copia locale."""
        page = self.PAGE.read_text()
        assert "from '../services/components/ServiceOptionsEditor'" in page
        assert "from '../../components/StripeRequiredAlert'" in page
        assert "serviceOptionsAPI" in page
        listino_dir = FRONTEND_SRC / "features" / "listino"
        copie = [f.name for f in listino_dir.iterdir()
                 if "Options" in f.name or "Stripe" in f.name]
        assert copie == [], f"copie locali vietate: {copie}"

    def test_salvataggio_conserva_metadata(self):
        """use_default_schedule e transaction_mode si salvano dalla
        riga SENZA perdere gli altri campi metadata (merge su rawMeta);
        i default snelli di saveNew restano intatti (vedi anche
        test_listino_defaults_are_lean)."""
        page = self.PAGE.read_text()
        assert "use_default_schedule: !!edit.useDefaultSchedule" in page
        assert "...edit.rawMeta" in page
        assert "transaction_mode: edit.transactionMode" in page
        # payloadFromRow resta il payload base identico di TW1
        assert "payloadFromRow(draft)" in page
        assert "payloadFromRow(edit)" in page


class TestCardOperatoreLM2:
    """LM2 (docs/LISTINO_MARKETPLACE_PIANO_2026-07.md) — card operatore
    ricca: rating + aggregato listino + anteprima su /public/operators,
    vista rapida in card, footer con 'Esplora operatori' in entrambe
    le fasi."""

    def test_operators_endpoint_exposes_card_fields(self):
        """rating / services_count / price_from / listino_preview
        viaggiano sugli item, derivati dalla stessa query prodotti
        (niente N+1 per pagina)."""
        src = (BACKEND_DIR / "routers" / "public.py").read_text()
        blocco = src.split("async def public_operators_index")[1]
        blocco = blocco.split("async def _operator_listino")[0]
        for campo in ('"rating"', '"services_count"', '"price_from"',
                      '"listino_preview"'):
            assert campo in blocco, f"campo mancante sull'item: {campo}"
        # una sola query prodotti per tutte le org della pagina
        assert "svc_by_org" in blocco
        assert "_operator_listino(" not in blocco, "niente N+1 in loop"
        r = requests.get(f"{BASE_URL}/api/public/operators", timeout=10)
        assert r.status_code == 200
        # quando la fase corrente mostra operatori, i campi ci sono
        for item in r.json()["items"][:1]:
            for campo in ("rating", "services_count", "price_from",
                          "listino_preview"):
                assert campo in item, f"campo mancante live: {campo}"

    def test_card_vista_rapida_in_pagina(self):
        """La card espande l'anteprima IN CARD (bottone aria-expanded,
        pattern PN3): niente navigazione, il profilo resta la CTA."""
        page = (FRONTEND_SRC / "features" / "storefront"
                / "OperatorsIndexPage.js").read_text()
        assert "Vista rapida" in page
        assert "operator-quick-view" in page
        assert "aria-expanded={quickOpen}" in page
        assert "listino_preview" in page
        assert "Vai al profilo" in page
        # fiducia e prezzo di partenza sulla card
        assert "op.rating" in page
        assert "da {{price}} euro" in page

    def test_footer_voce_operatori_entrambe_le_fasi(self):
        """La voce di footer verso /operatori non e' dietro isNetwork ne'
        prelaunch: vive in rete E in marketplace.
        HP2 — cambia solo l'ETICHETTA: in rete si chiama "Operatori"
        (specifica founder), in marketplace resta "Esplora operatori",
        che promette una ricerca che in fase rete non esiste ancora."""
        shell = (FRONTEND_SRC / "features" / "storefront" / "components"
                 / "MarketplaceShell.jsx").read_text()
        righe = [l for l in shell.splitlines()
                 if 'to="/operatori"' in l and "hover:text-white" in l]
        assert righe, "voce footer verso /operatori assente"
        assert all("isNetwork &&" not in l and "prelaunch &&" not in l
                   for l in righe), "la voce non deve sparire in una fase"
        assert "marketplace.footerExploreOperators" in shell, \
            "etichetta marketplace mancante"
        # LC8 — l'etichetta di fase rete oggi e' la stessa del menu
        # ("La Rete", marketplace.navNetwork): navNetworkMembers e'
        # uscita con la riscrittura founder del 2/8.
        assert "marketplace.navNetwork" in shell, \
            "etichetta fase rete mancante"


class TestRicercaLM3:
    """LM3 (docs/LISTINO_MARKETPLACE_PIANO_2026-07.md) — ricerca stile
    Treatwell su /operatori: barra sticky Dove/Cosa/Ordina, geo via
    indice 2dsphere ($geoNear) e nuovi parametri API."""

    def _blocco_endpoint(self):
        src = (BACKEND_DIR / "routers" / "public.py").read_text()
        blocco = src.split("async def public_operators_index")[1]
        return blocco.split("async def _operator_listino")[0]

    def test_endpoint_accetta_sort_e_service_category(self):
        """sort=distance|rating|price e service_category (categorie
        delle righe di listino) esistono e rispondono live; sort
        sconosciuto degrada al default (rating senza geo)."""
        blocco = self._blocco_endpoint()
        assert "service_category" in blocco
        assert '("distance", "rating", "price")' in blocco
        # default sensato: distance se geo attivo, rating altrimenti
        assert '"distance" if _geo_active else "rating"' in blocco
        r = requests.get(f"{BASE_URL}/api/public/operators",
                         params={"sort": "rating"}, timeout=10)
        assert r.status_code == 200
        assert r.json().get("sort") == "rating"
        r2 = requests.get(f"{BASE_URL}/api/public/operators",
                          params={"service_category": "consulenze",
                                  "sort": "boh"}, timeout=10)
        assert r2.status_code == 200
        assert r2.json().get("sort") == "rating"

    def test_geo_via_indice_2dsphere_con_fallback(self):
        """La distanza arriva da $geoNear sull'indice an3_org_geo
        (public_profile.geo); l'haversine resta SOLO come fallback
        per-item per i doc con lat/lng senza campo geo."""
        blocco = self._blocco_endpoint()
        assert "$geoNear" in blocco
        assert '"key": "public_profile.geo"' in blocco
        assert "maxDistance" in blocco
        # fallback dichiarato: doc legacy fuori dall'indice sparse
        assert "_haversine_km" in blocco
        assert "distance_km" in blocco
        # niente piu' ciclo haversine post-lista su tutti gli item
        assert 'i["distance_km"] = (round(_haversine_km' not in blocco

    def test_barra_sticky_dove_cosa_ordina(self):
        """La barra unica sticky vive in testa a /operatori: Dove
        (GeoSearchBar fluida), Cosa (select categorie), Ordina per
        (?ordina= in URL) e il toggle Mappa dentro la barra."""
        page = (FRONTEND_SRC / "features" / "storefront"
                / "OperatorsIndexPage.js").read_text()
        assert 'data-testid="operators-search-bar"' in page
        assert "sticky top-14" in page
        # URL fonte di verita': ?ordina= + categoria come path segment
        assert "SORT_PARAM" in page
        assert "params.get('ordina')" in page
        # 28992cf — la stessa pagina risponde anche su /esplora-operatori:
        # la categoria resta path segment ma sul basePath dinamico
        assert "${basePath}/${next}" in page
        assert "'/esplora-operatori'" in page
        # Dove dentro la barra, in versione fluida
        assert "<GeoSearchBar value={geoValue} onChange={setGeo} fluid />" in page
        # Distanza offerta solo con geo attivo (come il backend)
        assert '{geoValue && (' in page
        geobar = (FRONTEND_SRC / "features" / "storefront" / "components"
                  / "GeoSearchBar.jsx").read_text()
        assert "fluid = false" in geobar


class TestQuandoLM4:
    """LM4 (docs/LISTINO_MARKETPLACE_PIANO_2026-07.md) — filtro Quando
    cross-operatore su indice denormalizzato availability_index.
    INVARIANTE ASSOLUTA: l'indice serve SOLO alla ricerca; checkout e
    slot veri restano sul motore esistente (slot_generator)."""

    SERVICE = BACKEND_DIR / "services" / "availability_index_service.py"

    def _blocco_endpoint(self):
        src = (BACKEND_DIR / "routers" / "public.py").read_text()
        blocco = src.split("async def public_operators_index")[1]
        return blocco.split("async def _operator_listino")[0]

    def test_servizio_indice_riusa_il_motore_slot(self):
        """Il servizio esiste e materializza l'indice CHIAMANDO
        generate_available_slots (scope agenda, stessa chiamata di
        GET /public/services/{id}/slots) — zero regole duplicate:
        niente letture dirette di availability_rules/blocked_slots,
        niente ciclo su day_of_week."""
        src = self.SERVICE.read_text()
        assert "from services.slot_generator import generate_available_slots" in src
        assert 'scope="agenda"' in src
        assert "rebuild_for_product" in src and "rebuild_for_org" in src
        # il motore non si duplica: il servizio non rilegge le regole
        assert "availability_rules_collection" not in src
        assert "blocked_slots_collection" not in src
        assert "day_of_week" not in src

    def test_endpoint_quando_con_date_filter_ready(self):
        """/public/operators accetta date (+ time_from/to), espone
        date_filter_ready (feature flag implicito: indice vuoto → il
        frontend nasconde il campo) e next_available sugli item."""
        blocco = self._blocco_endpoint()
        assert "date_filter_ready" in blocco
        assert '"next_available"' in blocco
        assert "availability_index_collection" in blocco
        from datetime import date as _d, timedelta as _td
        domani = (_d.today() + _td(days=1)).isoformat()
        r = requests.get(f"{BASE_URL}/api/public/operators",
                         params={"date": domani}, timeout=10)
        assert r.status_code == 200
        body = r.json()
        assert "date_filter_ready" in body
        # indice vuoto → lista vuota, MAI un errore
        if not body["date_filter_ready"]:
            assert body["items"] == []
        # data malformata → 400 esplicito, non 500
        r2 = requests.get(f"{BASE_URL}/api/public/operators",
                          params={"date": "31-12-2026"}, timeout=10)
        assert r2.status_code == 400

    def test_hook_best_effort_nei_punti_di_scrittura(self):
        """Chi cambia la disponibilita' riallinea l'indice in
        background: regole/blocchi (routers/availability.py), slot
        consumato da prenotazione e rilascio (booking_availability),
        annullamento ordine (order_service). Sempre best-effort:
        import dentro try, mai nel percorso critico."""
        hook = "from services.availability_index_service import schedule_rebuild"
        av = (BACKEND_DIR / "routers" / "availability.py").read_text()
        # regole (create+delete) e blocchi (create/delete/batch/group)
        assert av.count("schedule_rebuild(") >= 6
        assert hook in av
        ba = (BACKEND_DIR / "services" / "booking_availability.py").read_text()
        assert hook in ba and "schedule_rebuild(org_id)" in ba
        osrc = (BACKEND_DIR / "services" / "order_service.py").read_text()
        assert hook in osrc
        # best-effort dichiarato: ogni import dell'hook vive dentro un
        # try (un rebuild rotto non deve MAI rompere il flusso primario)
        for src in (av, ba, osrc):
            for prima in src.split(hook)[:-1]:
                coda = "\n".join(prima.rstrip().splitlines()[-3:])
                assert "try:" in coda, "hook schedule_rebuild fuori da un try"

    def test_invariante_indice_solo_ricerca(self):
        """Il motore slot e il checkout NON sanno che l'indice esiste:
        slot_generator intoccato (nessun riferimento all'indice) e
        nessuna lettura di availability_index nei percorsi d'acquisto.
        L'unico lettore e' la ricerca /public/operators."""
        sg = (BACKEND_DIR / "services" / "slot_generator.py").read_text()
        assert "availability_index" not in sg
        for nome in ("order_creation_service.py", "product_type_validators.py",
                     "payment_checkout_service.py", "cart_service.py"):
            src = (BACKEND_DIR / "services" / nome).read_text()
            assert "availability_index" not in src, f"checkout legge l'indice: {nome}"
        # lo slot picker pubblico resta sul motore vero
        pub = (BACKEND_DIR / "routers" / "public.py").read_text()
        picker = pub.split("async def get_service_slots")[1].split("@router.get")[0]
        assert "generate_available_slots" in picker
        assert "availability_index" not in picker


class TestAnteprimaMarketplace:
    """PN (richiesta founder 29/7) — anteprima VERA del marketplace su
    rotte non linkate (/esplora-operatori, /esplora-ritiri): preview=1
    bypassa il filtro solo-campioni della fase (PL8) SOLO per quella
    risposta; il default resta identico (le guardie PL8 non cambiano)."""

    def test_preview_1_mostra_org_vere(self):
        """preview=1 → comportamento marketplace: operatori/ritiri VERI,
        mai marcati sample, identita' non redatta (PL9 non serve: i
        campioni escono dal perimetro)."""
        src = (BACKEND_DIR / "routers" / "public.py").read_text()
        op = src.split("async def public_operators_index")[1] \
                .split("async def _operator_listino")[0]
        assert "_prelaunch = prelaunch_mode() and not preview" in op
        rt = src.split("async def list_public_retreats")[1] \
                .split("def _haversine_km")[0]
        assert "if prelaunch_mode() and not preview:" in rt
        r = requests.get(f"{BASE_URL}/api/public/operators",
                         params={"preview": 1}, timeout=10)
        assert r.status_code == 200
        for it in r.json()["items"]:
            assert it["sample"] is False
            assert it["name"], "identita' redatta con preview=1"
        r2 = requests.get(f"{BASE_URL}/api/public/retreats",
                          params={"preview": 1}, timeout=10)
        assert r2.status_code == 200
        for it in r2.json()["items"]:
            assert it["sample"] is False
            assert it["org_name"], "org_name redatto con preview=1"

    def test_default_resta_campioni(self):
        """Senza preview NULLA cambia: in fase non-marketplace i listing
        mostrano solo campioni (sample=True) e le guardie PL8 restano
        scritte come prima."""
        src = (BACKEND_DIR / "routers" / "public.py").read_text()
        # le guardie PL8 esistenti (test_prelaunch_pl) restano intatte
        assert "pay_ready = set(sample_orgs)" in src
        assert "if _is_sample != _prelaunch:" in src
        cfg = requests.get(f"{BASE_URL}/api/public/site-config",
                           timeout=10).json()
        prelaunch = bool(cfg.get("prelaunch"))
        for ep in ("operators", "retreats"):
            r = requests.get(f"{BASE_URL}/api/public/{ep}", timeout=10)
            assert r.status_code == 200
            for it in r.json()["items"]:
                # fase spenta: solo campioni; marketplace: solo veri
                assert it["sample"] is prelaunch, \
                    f"default cambiato su /{ep} (fase prelaunch={prelaunch})"

    def test_rotte_esplora_presenti_e_indicizzabili(self):
        """LA DECISIONE E' CAMBIATA (ES, 25/8). Questa guardia chiedeva
        `noindex` sulle rotte /esplora-*: giusto finche' quelle pagine
        mostravano i CAMPIONI del pre-lancio (sei organizzazioni senza
        proprietario, dieci ritiri inventati in localita' reali).
        Rimossi i campioni, li' dentro ci sono i professionisti VERI e
        sono le uniche due directory della fase rete: il founder ha
        chiesto di indicizzarle ORA, cosi' al primo ritiro pubblicato
        non ci sara' niente da fare.

        Cosa resta sotto guardia: le rotte esistono in ogni fase,
        chiedono `preview=1` (i dati veri, non lo specchio di fase), e
        nessuna voce di menu le linka — restano porte laterali per chi
        arriva dai motori, non voci di navigazione."""
        app = (FRONTEND_SRC / "App.js").read_text()
        assert 'path="/esplora-ritiri"' in app
        assert 'path="/esplora-ritiri/:categoria"' in app
        assert 'path="/esplora-ritiri/:categoria/:regione"' in app
        assert 'path="/esplora-operatori"' in app
        cal = (FRONTEND_SRC / "features" / "storefront"
               / "RetreatsCalendarPage.js").read_text()
        assert "'/esplora-ritiri'" in cal
        assert "q.preview = 1" in cal
        # ES — il noindex ora dipende dai DATI, non dalla rotta.
        # Si ancora alla forma CODICE (con la virgola): i commenti qui
        # accanto citano la riga vecchia per raccontare il cambio, e
        # una guardia che inciampa nella prosa non custodisce niente.
        assert "noindex: isPreview," not in cal
        assert "!loading && (data?.items || []).length === 0" in cal
        assert "${basePath}/${category}" in cal   # navigazione interna
        ops = (FRONTEND_SRC / "features" / "storefront"
               / "OperatorsIndexPage.js").read_text()
        assert "q.preview = 1" in ops
        assert "noindex: isPreview ||" not in ops
        assert "!loading && items.length === 0" in ops
        # nessun link di menu/footer verso le rotte anteprima
        shell = (FRONTEND_SRC / "features" / "storefront" / "components"
                 / "MarketplaceShell.jsx").read_text()
        assert "/esplora-ritiri" not in shell
        assert "/esplora-operatori" not in shell


class TestPolishLM5:
    """LM5 (docs/LISTINO_MARKETPLACE_PIANO_2026-07.md) — polish visivo
    stile Treatwell su /operatori: skeleton al posto dei flash vuoti,
    empty state onesto con il suggerimento giusto per il filtro attivo."""

    def test_skeleton_cards_durante_il_caricamento(self):
        """Il loading usa il pattern Skeleton di components/ui con la
        STESSA geometria della card (cover 16/9): niente flash vuoti
        e niente salto di layout a fetch finito."""
        page = (FRONTEND_SRC / "features" / "storefront"
                / "OperatorsIndexPage.js").read_text()
        assert "from '../../components/ui/skeleton'" in page
        assert "OperatorCardSkeleton" in page
        assert 'data-testid="operator-card-skeleton"' in page
        # la cover skeleton condivide il ratio della cover vera
        assert page.count("aspect-[16/9]") >= 2, \
            "cover della card e dello skeleton con lo stesso ratio 16/9"

    def test_empty_state_con_suggerimento(self):
        """Zero risultati = messaggio onesto + gesto suggerito legato
        al filtro attivo: togli la data, allarga il raggio, tutti i
        servizi. Mai un vuoto muto."""
        page = (FRONTEND_SRC / "features" / "storefront"
                / "OperatorsIndexPage.js").read_text()
        assert 'data-testid="operators-empty"' in page
        # Evoluta 30/8 (founder): il filtro «Quando?» e' uscito dalla
        # pagina — con lui il gesto «Togli la data». Restano i gesti
        # legati ai filtri vivi: raggio e categoria.
        assert "Togli la data" not in page
        assert "Allarga il raggio" in page
        # i suggerimenti sono azioni vere sui filtri, non solo testo
        # (il gesto della data e' uscito col filtro Quando, 30/8)
        assert "setGeo({ ...geoValue, radius: 250 })" in page


class TestAccountAp0:
    """AP0 (docs/ACCOUNT_UNICO_PIANO_2026-07.md) — il signup cliente
    funziona anche con legal autogenerato (coerenza RS3): snapshot
    consensi 'autogen:v0' come gia' fanno gli ordini; il 400 resta
    SOLO se lo store non esiste; il catch del checkout dice il motivo
    vero invece del generico 'registrazione non completata'."""

    @staticmethod
    def _signup_patches(store_doc, captured_account, captured_audit):
        from unittest.mock import AsyncMock, patch

        async def _create(doc):
            captured_account.update(doc)
            return doc

        async def _record(**kw):
            captured_audit.append(kw)

        return [
            patch("services.customer_auth_service."
                  "customer_account_repository.find_by_email",
                  new=AsyncMock(return_value=None)),
            patch("services.customer_auth_service."
                  "customer_account_repository.create", new=_create),
            patch("services.customer_auth_service."
                  "_link_account_to_existing_customers", new=AsyncMock()),
            patch("database.stores_collection.find_one",
                  new=AsyncMock(return_value=store_doc)),
            patch("repositories.consent_audit_repository.record_consent",
                  new=_record),
            patch("services.customer_auth_service._load_email_context",
                  new=AsyncMock(return_value={
                      "sender_name": "", "reply_to": "", "store_name": "",
                  })),
            patch("services.customer_auth_service.resolve_slug_for_org",
                  new=AsyncMock(return_value="acme")),
            patch("services.customer_auth_service.send_customer_welcome",
                  new=lambda *a, **kw: None),
        ]

    async def test_ap0_signup_ok_con_store_autogen(self):
        """Store esistente ma legal not_configured: il signup PASSA e
        lo snapshot CG-4 e' 'autogen:v0' (stessa sentinella degli
        ordini RS3), audit con tag 'autogen' + hash 'v0'."""
        from contextlib import ExitStack
        from services import customer_auth_service

        store = {
            "id": "store-ap0", "organization_id": "org-ap0",
            "slug": "acme", "name": "Acme",
            "storefront_languages": ["it"],
            # nessun merchant_*_content → merchant_legal_status
            # = not_configured
        }
        account, audit = {}, []
        with ExitStack() as stack:
            for p in self._signup_patches(store, account, audit):
                stack.enter_context(p)
            result = await customer_auth_service.customer_signup(
                org_id="org-ap0", email="ap0@example.com", name="Ap0",
                password="StrongPass12", signup_slug="acme",
                accepted_terms=True, accepted_privacy=True,
            )

        assert result["status"] == "verification_required"
        assert account["accepted_store_terms_version"] == "autogen:v0"
        assert account["accepted_store_privacy_version"] == "autogen:v0"
        assert account["accepted_store_terms_locale"] == "it"
        assert [r["version_tag"] for r in audit] == ["autogen", "autogen"]
        assert [r["version_hash"] for r in audit] == ["v0", "v0"]

    async def test_ap0_400_solo_se_store_inesistente(self):
        """L'unico rifiuto legale rimasto: lo store NON esiste (niente
        documenti serviti, nemmeno autogenerati → nulla a cui legare
        il consenso)."""
        import pytest
        from contextlib import ExitStack
        from services import customer_auth_service

        account, audit = {}, []
        with ExitStack() as stack:
            for p in self._signup_patches(None, account, audit):
                stack.enter_context(p)
            with pytest.raises(ValueError, match="configurazione"):
                await customer_auth_service.customer_signup(
                    org_id="org-ap0", email="ap0b@example.com", name="B",
                    password="StrongPass12", signup_slug="ghost",
                    accepted_terms=True, accepted_privacy=True,
                )
        assert not account and not audit

    def test_ap0_catch_onesto_nel_checkout(self):
        """Il ramo else del catch signup mostra il motivo vero quando
        il backend fornisce `detail` (chiave i18n con {{reason}}); il
        generico resta solo come fallback. Per i corsi il flusso resta
        bloccante com'era."""
        hook = (FRONTEND_SRC / "features" / "storefront" / "hooks"
                / "useCheckoutForm.js").read_text()
        assert "signupNotCompletedReason" in hook
        assert "reason: String(detail)" in hook
        # fallback generico ancora presente per errori senza detail
        assert "storefront:errors.signupNotCompleted'" in hook
        # corsi: sempre bloccanti (return dopo il toast.error)
        assert "toast.error(detail || t('storefront:errors.signupFailed'))" in hook
        # la chiave esiste in tutte e 4 le lingue, con {{reason}}
        import json
        for lang in ("it", "en", "de", "fr"):
            data = json.loads((FRONTEND_SRC / "locales" / lang
                               / "storefront.json").read_text())
            msg = data["errors"]["signupNotCompletedReason"]
            assert "{{reason}}" in msg


class TestCheckoutAuryaAp1:
    """AP1 (docs/ACCOUNT_UNICO_PIANO_2026-07.md) — il checkout parla
    solo Aurya: la registrazione con password e' gated ai soli corsi,
    i guest vedono l'hint Passaporto, e chi ha gia' un account entra
    inline con gli endpoint passwordless della piattaforma."""

    CHECKOUT_DIR = ("features", "storefront", "components", "checkout")

    def _checkout_file(self, name):
        p = FRONTEND_SRC
        for part in self.CHECKOUT_DIR:
            p = p / part
        return (p / name).read_text()

    def test_ap1_password_gated_ai_soli_corsi(self):
        """La sezione 'crea account' con password NON e' piu' una scelta:
        appare SOLO quando il carrello contiene un corso (dove resta
        obbligatoria e invariata). R1: il codice wantRegister resta nel
        hook, la condizione e' riallargabile."""
        form = self._checkout_file("CheckoutForm.jsx")
        # gate: solo corsi (requiresCustomerAccount), mai scelta libera
        assert ("{requiresCustomerAccount && !isCustomerAuthenticated"
                " && (() => {") in form
        assert "(!mktpCheckout || requiresCustomerAccount)" not in form
        # dentro il blocco la registrazione resta forzata e invariata
        assert "checked={wantRegister || requiresCustomerAccount}" in form
        assert "disabled={!emailOk || requiresCustomerAccount}" in form
        # R1 — la logica signup del hook NON e' stata eliminata
        hook = (FRONTEND_SRC / "features" / "storefront" / "hooks"
                / "useCheckoutForm.js").read_text()
        assert "wantRegister" in hook
        assert "customerSignup({" in hook

    def test_ap1_hint_passport_per_guest(self):
        """Al posto della scelta account, i guest (senza corso) vedono
        il blocco informativo Passaporto — su OGNI superficie del
        checkout, non solo marketplace. Copy in 4 lingue, senza
        'negozio' e senza trattini lunghi."""
        form = self._checkout_file("CheckoutForm.jsx")
        assert 'data-testid="aurya-passport-hint"' in form
        assert ("{!requiresCustomerAccount && !isCustomerAuthenticated"
                " && (") in form
        import json
        for lang in ("it", "en", "de", "fr"):
            data = json.loads((FRONTEND_SRC / "locales" / lang
                               / "storefront.json").read_text())
            msg = data["checkout"]["auryaPassportHint"]
            assert "Aurya" in msg, lang
            assert "—" not in msg, lang       # niente em dash
            assert "negozio" not in msg.lower(), lang

    def test_ap1_pannello_accesso_endpoint_platform(self):
        """L'accesso rapido inline riusa ESATTAMENTE il passwordless
        della piattaforma (stessi endpoint di AccountLoginPage) e il
        token in localStorage; il profilo per il prefill arriva da
        GET /platform/me."""
        panel = self._checkout_file("AuryaQuickLogin.jsx")
        assert "'/platform/auth/magic-link'" in panel
        assert "'/platform/auth/code/verify'" in panel
        assert "'/platform/me'" in panel
        assert "PLATFORM_TOKEN_KEY" in panel
        # montato nel form del checkout, solo per i guest
        form = self._checkout_file("CheckoutForm.jsx")
        assert "AuryaQuickLogin" in form
        assert "{!isCustomerAuthenticated && (\n                  <AuryaQuickLogin" in form


class TestHubAccountAp2:
    """AP2 (docs/ACCOUNT_UNICO_PIANO_2026-07.md, adattata) — l'hub
    /account racconta lo stato vero di richieste e ritiri e apre le
    guide della lettera di Aurya agli iscritti confermati."""

    def test_ap2_orders_espongono_stato_e_slot(self):
        """La proiezione /platform/me/orders porta status +
        transaction_mode dominante + l'appuntamento scelto al checkout
        servizi (service_slot dai booking_* della riga) e NON nasconde
        piu' gli ordini annullati (badge 'Annullato')."""
        src = (BACKEND_DIR / "routers" / "platform_accounts.py").read_text()
        assert '"items.booking_date": 1' in src
        assert '"items.transaction_mode": 1' in src
        assert '"service_slot"' in src
        assert '"transaction_mode": (modes.pop() if len(modes) == 1' in src
        # gli annullati ora si vedono (prima erano filtrati via).
        # TA2: il filtro-status e' vietato sulla query degli ORDINI —
        # le prenotazioni cancellate (issued_bookings) e' giusto
        # filtrarle. Stessa precisazione della guardia AP2 in
        # test_platform_accounts.
        orders_query = src.split("orders_collection.find(")[1].split(".sort(")[0]
        assert "cancelled" not in orders_query

    def test_ap2_login_emette_token_newsletter_solo_confirmed(self):
        """Il login Passaporto (magic link E codice) risponde con
        newsletter_subscriber e, SOLO per iscrizioni aurya_subscribers
        confermate, col subscriber_token (riuso core/subscriber_token,
        la stessa chiave che sblocca le guide BN3)."""
        svc = (BACKEND_DIR / "services"
               / "platform_account_service.py").read_text()
        assert "async def newsletter_status" in svc
        assert 'doc.get("status") == "confirmed"' in svc
        assert "generate_subscriber_token" in svc
        # il token si firma DENTRO il ramo confirmed, mai fuori
        confirmed_branch = svc.split('doc.get("status") == "confirmed"')[1]
        assert "generate_subscriber_token" in confirmed_branch
        router = (BACKEND_DIR / "routers" / "platform_accounts.py").read_text()
        # TUTTE le strade di login arricchiscono la risposta (magic link,
        # OTP e — da AP1b — anche il login password)
        assert router.count("**await newsletter_status(account[\"email\"])") == 3
        # /platform/me espone il booleano per il render (senza token)
        assert "with_token=False" in router

    def test_ap2_sezione_guide_frontend(self):
        """/account ha la sezione Guide e materiale: lista delle guide
        riservate (endpoint pubblico del blog) per gli iscritti, invito
        a /newsletter per gli altri; i login salvano aurya_nl_token
        solo se il backend lo ha emesso. Copy in 4 lingue, senza
        trattini lunghi e senza 'negozio'."""
        page = (FRONTEND_SRC / "features" / "account"
                / "AccountPage.js").read_text()
        assert 'data-testid="account-guides"' in page
        assert "newsletter_subscriber" in page
        assert "'/public/articles'" in page
        assert 'to="/newsletter"' in page
        assert ".filter(a => a.gated)" in page
        login = (FRONTEND_SRC / "features" / "account"
                 / "AccountLoginPage.js").read_text()
        # SB1 — la prova si salva dal posto unico (lib/cerchio, che
        # scrive aurya_nl_token), mai a mano
        assert "salvaProva" in login
        assert "subscriber_token" in login
        quick = (FRONTEND_SRC / "features" / "storefront" / "components"
                 / "checkout" / "AuryaQuickLogin.jsx").read_text()
        assert "salvaProva" in quick
        import json
        for lang in ("it", "en", "de", "fr"):
            data = json.loads((FRONTEND_SRC / "locales" / lang
                               / "landings.json").read_text())
            acc = data["account"]
            for key in ("statusRequestSent", "statusConfirmed",
                        "statusCompleted", "statusCancelled",
                        "appointment", "guidesTitle", "guidesInvite",
                        "guidesCta"):
                msg = acc[key]
                assert "—" not in msg, (lang, key)
                assert "negozio" not in msg.lower(), (lang, key)


class TestAccountAp1b:
    """AP1b (docs/ACCOUNT_UNICO_PIANO_2026-07.md, revisione founder) —
    email+password sull'account Aurya: signup con verifica email,
    login password con lockout, reset che vale anche come "imposta
    password" per gli account nati passwordless. Il passwordless resta
    identico come alternativa."""

    PASSWORD = "StrongPass12"

    class _MemAccounts:
        """platform_accounts in memoria: il minimo che serve al service
        (find_one per uguaglianza, insert_one, update_one con $set)."""

        def __init__(self):
            self.docs = {}

        async def find_one(self, q, proj=None):
            for d in self.docs.values():
                if all(d.get(k) == v for k, v in q.items()):
                    return dict(d)
            return None

        async def insert_one(self, doc):
            self.docs[doc["id"]] = dict(doc)

        async def update_one(self, q, u):
            for d in self.docs.values():
                if all(d.get(k) == v for k, v in q.items()):
                    for k, v in u.get("$set", {}).items():
                        d[k] = v
                    return

    def _ctx(self, fake, sent):
        """Patch comuni: collection in memoria, email catturate (il token
        in chiaro viaggia SOLO li'), claim e rate-limit neutralizzati."""
        from unittest.mock import AsyncMock, patch
        from services import platform_account_service as svc

        return [
            patch("database.platform_accounts_collection", fake),
            patch.object(svc, "_send_verify_email",
                         lambda e, t, n, locale="it": sent.update(
                             {"verify_email": e, "verify_token": t})),
            patch.object(svc, "_send_reset_email",
                         lambda e, t, n, locale="it": sent.update(
                             {"reset_email": e, "reset_token": t})),
            patch.object(svc, "retroactive_claim", AsyncMock()),
            patch("core.rate_limiting.check_email_rate",
                  new=lambda *a, **kw: True),
        ]

    async def test_ap1b_signup_verifica_login_felice(self):
        """Signup → email di verifica (token in chiaro solo li', a DB
        l'hash) → verify → login password: sessione e contatori ok."""
        from contextlib import ExitStack
        from services import platform_account_service as svc

        fake, sent = self._MemAccounts(), {}
        with ExitStack() as stack:
            for p in self._ctx(fake, sent):
                stack.enter_context(p)

            out = await svc.password_signup(
                name="Anna", email="Anna@Ap1b.it", password=self.PASSWORD)
            assert out == {"status": "verification_required"}
            acc = list(fake.docs.values())[0]
            assert acc["email"] == "anna@ap1b.it"          # normalizzata
            assert acc["email_verified"] is False
            assert acc["password_hash"].startswith("$2")   # bcrypt
            token = sent["verify_token"]
            assert token and token not in str(acc)         # MAI in chiaro a DB
            assert acc["verification_token_hash"] == svc._hash_token(token)

            out = await svc.verify_signup_email(token)
            assert out == {"status": "verified"}
            acc = list(fake.docs.values())[0]
            assert acc["email_verified"] is True
            assert acc["verification_token_hash"] is None  # one-shot

            logged = await svc.password_login("anna@ap1b.it", self.PASSWORD)
            assert logged["id"] == acc["id"]
            assert logged["last_login_at"]
            assert logged["failed_login_attempts"] == 0

    async def test_ap1b_login_prima_della_verifica_rifiutato(self):
        """Password giusta ma email non verificata: EMAIL_NOT_VERIFIED
        (il router lo traduce in 403). Prima della password giusta,
        invece, SOLO 401 generico: niente enumeration."""
        import pytest
        from contextlib import ExitStack
        from services import platform_account_service as svc

        fake, sent = self._MemAccounts(), {}
        with ExitStack() as stack:
            for p in self._ctx(fake, sent):
                stack.enter_context(p)
            await svc.password_signup(
                name="B", email="b@ap1b.it", password=self.PASSWORD)
            with pytest.raises(ValueError, match="EMAIL_NOT_VERIFIED"):
                await svc.password_login("b@ap1b.it", self.PASSWORD)
            # password sbagliata su account non verificato: 401 generico,
            # mai lo stato dell'account
            with pytest.raises(ValueError, match="INVALID_CREDENTIALS"):
                await svc.password_login("b@ap1b.it", "WrongPass1234")

    async def test_ap1b_email_gia_registrata_409(self):
        """Account gia' verificato (o con password) → EMAIL_EXISTS, che
        il router mappa su un 409 onesto. ECCEZIONE voluta: il guscio
        passwordless pending nato da un acquisto guest viene ADOTTATO
        dal signup (la proprieta' resta provata dal link di verifica)."""
        import pytest
        from contextlib import ExitStack
        from services import platform_account_service as svc

        fake, sent = self._MemAccounts(), {}
        with ExitStack() as stack:
            for p in self._ctx(fake, sent):
                stack.enter_context(p)
            await svc.password_signup(
                name="C", email="c@ap1b.it", password=self.PASSWORD)
            await svc.verify_signup_email(sent["verify_token"])
            with pytest.raises(ValueError, match="EMAIL_EXISTS"):
                await svc.password_signup(
                    name="C2", email="C@AP1B.IT", password=self.PASSWORD)

            # guscio pending (claim acquisto): il signup lo adotta
            fake.docs["shell-1"] = {"id": "shell-1", "email": "guest@ap1b.it",
                                    "email_verified": False,
                                    "password_hash": None}
            out = await svc.password_signup(
                name="Guest", email="guest@ap1b.it", password=self.PASSWORD)
            assert out == {"status": "verification_required"}
            shell = fake.docs["shell-1"]
            assert shell["password_hash"].startswith("$2")
            assert shell["email_verified"] is False        # verifica ancora dovuta

        # il router mappa EMAIL_EXISTS su 409
        router = (BACKEND_DIR / "routers" / "platform_accounts.py").read_text()
        block = router.split('"/auth/signup"')[1]
        assert "HTTP_409_CONFLICT" in block.split("@router.post")[0]

    async def test_ap1b_lockout_dopo_n_tentativi(self):
        """Stesse soglie dei customer (core/security_config): dopo
        LOCKOUT_THRESHOLD password sbagliate l'account si blocca e
        ANCHE la password giusta risponde ACCOUNT_LOCKED (recupero via
        reset)."""
        import pytest
        from contextlib import ExitStack
        from core.security_config import LOCKOUT_ERROR_CODE, LOCKOUT_THRESHOLD
        from services import platform_account_service as svc

        fake, sent = self._MemAccounts(), {}
        with ExitStack() as stack:
            for p in self._ctx(fake, sent):
                stack.enter_context(p)
            await svc.password_signup(
                name="D", email="d@ap1b.it", password=self.PASSWORD)
            await svc.verify_signup_email(sent["verify_token"])

            for _ in range(LOCKOUT_THRESHOLD):
                with pytest.raises(ValueError, match="INVALID_CREDENTIALS"):
                    await svc.password_login("d@ap1b.it", "WrongPass1234")

            acc = list(fake.docs.values())[0]
            assert acc["locked_until"]                     # lockout scattato
            with pytest.raises(ValueError,
                               match=f"^{LOCKOUT_ERROR_CODE}:"):
                await svc.password_login("d@ap1b.it", self.PASSWORD)

    async def test_ap1b_reset_imposta_password_su_passwordless(self):
        """Il reset e' anche il flusso "imposta la password" per gli
        account nati passwordless (claim acquisto): password_hash None →
        scritto; il link usato prova la casella → email_verified True;
        token one-shot."""
        import pytest
        from contextlib import ExitStack
        from services import platform_account_service as svc

        fake, sent = self._MemAccounts(), {}
        fake.docs["pl-1"] = {"id": "pl-1", "email": "senza@ap1b.it",
                             "email_verified": False, "password_hash": None,
                             "language": "it"}
        with ExitStack() as stack:
            for p in self._ctx(fake, sent):
                stack.enter_context(p)
            await svc.request_password_reset("senza@ap1b.it")
            token = sent["reset_token"]
            assert token not in str(fake.docs["pl-1"])     # a DB solo l'hash

            out = await svc.confirm_password_reset(token, self.PASSWORD)
            assert out == {"status": "ok"}
            acc = fake.docs["pl-1"]
            assert acc["password_hash"].startswith("$2")
            assert acc["email_verified"] is True           # casella provata
            assert acc["reset_token_hash"] is None         # one-shot

            logged = await svc.password_login("senza@ap1b.it", self.PASSWORD)
            assert logged["id"] == "pl-1"

            # secondo uso dello stesso token: rifiutato
            with pytest.raises(ValueError, match="INVALID_TOKEN"):
                await svc.confirm_password_reset(token, self.PASSWORD)

    async def test_ap1b_reset_request_neutra_se_email_ignota(self):
        """Nessun account per l'email → nessuna email inviata, nessun
        errore: il router risponde comunque 200 (enumeration-safe)."""
        from contextlib import ExitStack
        from services import platform_account_service as svc

        fake, sent = self._MemAccounts(), {}
        with ExitStack() as stack:
            for p in self._ctx(fake, sent):
                stack.enter_context(p)
            await svc.request_password_reset("ignota@ap1b.it")
        assert "reset_token" not in sent

    def test_ap1b_risposta_login_password_con_newsletter(self):
        """La risposta del login password ha lo STESSO shape delle altre
        strade: access_token + account + newsletter_status AP2 (le guide
        si sbloccano anche col login password)."""
        router = (BACKEND_DIR / "routers" / "platform_accounts.py").read_text()
        block = router.split('"/auth/login"')[1].split("@router.post")[0]
        assert "_login_response(account)" in block
        assert '**await newsletter_status(account["email"])' in block
        # errori: 423 lockout, 403 non verificata, 401 generico
        assert "HTTP_423_LOCKED" in block
        assert "HTTP_403_FORBIDDEN" in block
        assert "HTTP_401_UNAUTHORIZED" in block

    def test_ap1b_frontend_percorsi_e_copy(self):
        """AccountLoginPage: password primaria + link secondari (OTP e
        reset) + signup; pagine verify/nuova-password instradate; il
        checkout inline ha il toggle password. Copy x4 lingue: mai
        'Passaporto', mai trattini lunghi."""
        login = (FRONTEND_SRC / "features" / "account"
                 / "AccountLoginPage.js").read_text()
        # ID (20/8) — il login password parla con la porta unica; il
        # recupero e' unificato (/auth/recupero copre entrambi i mondi).
        # NL1 (20/8) — la REGISTRAZIONE non usa piu' /platform/auth/signup:
        # l'account nasce senza password dal magic link (find-or-create).
        assert "'/auth/entra'" in login
        assert "'/platform/auth/magic-link'" in login
        assert "'/auth/recupero'" in login
        assert 'data-testid="login-no-password"' in login
        assert 'data-testid="login-forgot"' in login
        assert 'data-testid="login-to-signup"' in login

        verify = (FRONTEND_SRC / "features" / "account"
                  / "AccountVerifyEmailPage.js").read_text()
        assert "'/platform/auth/verify-email'" in verify
        reset = (FRONTEND_SRC / "features" / "account"
                 / "AccountResetPasswordPage.js").read_text()
        assert "'/platform/auth/password-reset/confirm'" in reset

        app = (FRONTEND_SRC / "App.js").read_text()
        assert 'path="/account/verifica"' in app
        assert 'path="/account/nuova-password"' in app

        quick = (FRONTEND_SRC / "features" / "storefront" / "components"
                 / "checkout" / "AuryaQuickLogin.jsx").read_text()
        assert "'/platform/auth/login'" in quick
        assert 'data-testid="aurya-login-have-password"' in quick
        assert "PLATFORM_TOKEN_KEY" in quick

        import json
        new_account_keys = (
            "passwordLoginBody", "passwordPlaceholder", "otpLink",
            "forgotLink", "signupLink", "signupTitle", "signupSentBody",
            "signupExists", "resetTitle", "resetBody", "resetSentBody",
            "passwordHint", "verifyOkBody", "verifyFailBody",
            "newPasswordTitle", "newPasswordOkBody", "newPasswordFailBody",
            "goToLogin", "backToLogin",
        )
        for lang in ("it", "en", "de", "fr"):
            acc = json.loads((FRONTEND_SRC / "locales" / lang
                              / "landings.json").read_text())["account"]
            for key in new_account_keys:
                msg = acc[key]
                assert "—" not in msg, (lang, key)         # niente em dash
                assert "assaporto" not in msg, (lang, key)  # mai Passaporto
            store = json.loads((FRONTEND_SRC / "locales" / lang
                                / "storefront.json").read_text())
            aq = store["checkout"]["auryaLogin"]
            for key in ("havePassword", "passwordHint", "passwordPlaceholder",
                        "noPassword", "passwordError", "passwordNotVerified",
                        "passwordLocked"):
                msg = aq[key]
                assert "—" not in msg, (lang, key)
                assert "assaporto" not in msg, (lang, key)

    def test_ap1b_email_transazionali_x4(self):
        """Le email di verifica e reset esistono nelle 4 lingue, dentro
        lo stesso sistema template (EMAIL_TRANSLATIONS + _wrap_template),
        senza la parola Passaporto nei testi nuovi."""
        from services.email_service import EMAIL_TRANSLATIONS

        keys = ("aurya_verify_subject", "aurya_verify_body",
                "aurya_verify_cta", "aurya_verify_footer",
                "aurya_reset_subject", "aurya_reset_body",
                "aurya_reset_cta", "aurya_reset_footer")
        for lang in ("it", "en", "de", "fr"):
            for key in keys:
                msg = EMAIL_TRANSLATIONS[lang][key]
                assert msg, (lang, key)
                assert "—" not in msg, (lang, key)
                assert "assaporto" not in msg, (lang, key)
        svc_src = (BACKEND_DIR / "services"
                   / "platform_account_service.py").read_text()
        assert "_wrap_template" in svc_src.split("def _send_verify_email")[1]
        assert "/account/verifica?token=" in svc_src
        assert "/account/nuova-password?token=" in svc_src


class TestAccountApL:
    """AP-L (docs/ACCOUNT_UNICO_PIANO_2026-07.md, revisione founder) —
    legal a due livelli gestito da Aurya: consenso Aurya timbrato
    sull'account alla creazione (aurya_legal + audit immutabile),
    checkout con atto primario Aurya (guest checkbox / loggato coperto
    dall'account) e checkbox DINAMICA delle condizioni dell'operatore
    solo se compilate; l'ordine timbra lo snapshot di TUTTO."""

    PASSWORD = "StrongPass12"

    # ── infrastruttura live (stesso server dei test RS/PN/LM) ────────

    _admin_token_cache = None

    @classmethod
    def _admin_headers(cls):
        import pytest
        if cls._admin_token_cache:
            return {"Authorization": f"Bearer {cls._admin_token_cache}"}
        r = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@demo.com", "password": "demo1234"}, timeout=10)
        if r.status_code != 200:
            pytest.skip("demo login unavailable (rate limit?)")
        cls._admin_token_cache = r.json()["access_token"]
        return {"Authorization": f"Bearer {cls._admin_token_cache}"}

    @staticmethod
    def _db():
        """DB del server live (backend/.env), NON il test_db di default."""
        import re
        import pymongo
        env = (BACKEND_DIR / ".env").read_text()
        mongo = re.search(r'MONGO_URL="?([^"\n]+?)"?\n', env).group(1)
        name = re.search(r'DB_NAME="?([^"\n]+?)"?\n', env).group(1)
        return pymongo.MongoClient(mongo)[name]

    @classmethod
    def _cleanup_email(cls, email):
        """Ripulisce TUTTE le tracce dei dati di guardia per email."""
        db = cls._db()
        email = email.lower()
        pa_ids = [a["id"] for a in
                  db.platform_accounts.find({"email": email}, {"id": 1})]
        cust_ids = [c["id"] for c in
                    db.customers.find({"email": email}, {"id": 1})]
        db.orders.delete_many({"$or": [
            {"customer_id": {"$in": cust_ids}},
            {"platform_account_id": {"$in": pa_ids}},
        ]})
        db.customers.delete_many({"email": email})
        db.customer_accounts.delete_many({"email": email})
        db.platform_magic_tokens.delete_many({"account_id": {"$in": pa_ids}})
        db.platform_accounts.delete_many({"email": email})
        db.consent_audit.delete_many({"customer_email": email})

    def _make_service(self, headers, name, metadata=None):
        # PV7 — la creazione richiede il patto firmato (helper unico,
        # firma marcata e rimossa a fine modulo)
        _ensure_dpa_ack(headers)
        r = requests.post(f"{BASE_URL}/api/products", headers=headers, json={
            "name": name, "item_type": "service",
            "transaction_mode": "request", "is_published": True,
            "unit_price": 30, "price_mode": "fixed",
            "metadata": metadata or {},
        }, timeout=10)
        assert r.status_code in (200, 201), r.text
        return r.json()

    def _delete_product(self, headers, product_id):
        requests.delete(f"{BASE_URL}/api/products/{product_id}",
                        headers=headers, timeout=10)
        # l'API fa soft-delete (is_active=False): il doc di guardia si
        # rimuove del tutto, cosi' i run ripetuti non accumulano residui
        try:
            self._db().products.delete_one({"id": product_id})
        except Exception:
            pass

    # ── 1. signup con consenso timbrato + audit (unit, in memoria) ───

    async def test_apl_signup_consenso_timbrato_e_audit(self):
        """password_signup con accepted_terms=True timbra aurya_legal
        (versioni correnti, source signup) sull'account e scrive
        l'audit immutabile (privacy_terms, platform_signup). Senza
        accepted_terms (chiamanti legacy): nessun timbro, nessun
        audit — il router pero' rende la spunta obbligatoria (400)."""
        from contextlib import ExitStack
        from unittest.mock import patch

        from core.legal_versions import (CURRENT_VERSION_TAG,
                                         current_version_string)
        from services import platform_account_service as svc

        # riuso dell'infrastruttura in-memory di AP1b (stesso modulo)
        Ap1b = TestAccountAp1b
        fake, sent, audit = Ap1b._MemAccounts(), {}, []

        async def _record(**kw):
            audit.append(kw)

        with ExitStack() as stack:
            for p in Ap1b()._ctx(fake, sent):
                stack.enter_context(p)
            stack.enter_context(
                patch("repositories.consent_audit_repository.record_consent",
                      new=_record))

            out = await svc.password_signup(
                name="Apl", email="apl-signup@example.com",
                password=self.PASSWORD, language="it",
                accepted_terms=True, request_ip="10.0.0.1",
                user_agent="guardia-apl")
            assert out == {"status": "verification_required"}
            acc = list(fake.docs.values())[0]
            legal = acc["aurya_legal"]
            assert legal["terms_version"] == current_version_string()
            assert legal["privacy_version"] == current_version_string()
            assert legal["source"] == "signup"
            assert legal["locale"] == "it"
            assert legal["accepted_at"]
            assert len(audit) == 1
            rec = audit[0]
            assert rec["document_type"] == "privacy_terms"
            assert rec["source"] == "platform_signup"
            assert rec["version_tag"] == CURRENT_VERSION_TAG
            assert rec["user_id"] == acc["id"]
            assert rec["customer_email"] == "apl-signup@example.com"
            assert rec["ip_address"] == "10.0.0.1"

            # chiamante legacy senza consenso: nessun timbro, nessun audit
            await svc.password_signup(
                name="NoLegal", email="apl-nolegal@example.com",
                password=self.PASSWORD)
            acc2 = [d for d in fake.docs.values()
                    if d["email"] == "apl-nolegal@example.com"][0]
            assert "aurya_legal" not in acc2
            assert len(audit) == 1

        # il router impone la checkbox: 400 senza accepted_terms, e
        # inoltra accepted_terms=True + ip/ua al service
        router = (BACKEND_DIR / "routers" / "platform_accounts.py").read_text()
        block = router.split('"/auth/signup"')[1].split("@router.post")[0]
        assert "accepted_terms" in block
        assert "HTTP_400_BAD_REQUEST" in block
        assert "accepted_terms=True" in block

    # ── 2. ordine GUEST: snapshot Aurya + operatore sull'ordine ──────

    def test_apl_ordine_guest_snapshot_aurya_e_operatore(self):
        """Ordine guest con checkbox Aurya spuntata e condizioni
        dell'operatore accettate: l'ordine timbra aurya_* (versioni
        correnti, source checkout), terms_content_snapshot (RS3
        esteso) e i gdpr_* merchant; l'account piattaforma nato
        dall'acquisto porta aurya_legal (source checkout) e l'audit
        immutabile ha il record platform_checkout con order_id."""
        from core.legal_versions import current_version_string

        email = "apl-guest@example.com"
        headers = self._admin_headers()
        self._cleanup_email(email)
        prod = self._make_service(
            headers, "Guardia AP-L guest",
            metadata={"terms_content": "Requisiti guardia AP-L: nessuna "
                                       "controindicazione medica."})
        try:
            r = requests.post(f"{BASE_URL}/api/public/order-request", json={
                "slug": "masseria-demo",
                "customer_name": "Guardia Apl",
                "customer_email": email,
                "items": [{"product_id": prod["id"], "quantity": 1}],
                "terms_accepted": True,
                "gdpr_terms_accepted": True,
                "gdpr_privacy_accepted": True,
                "gdpr_marketing_accepted": False,
                "aurya_terms_accepted": True,
                "locale": "it",
                "channel": "store",
            }, timeout=15)
            assert r.status_code == 200, r.text
            order_id = r.json()["order_id"]

            db = self._db()
            order = db.orders.find_one({"id": order_id})
            assert order["aurya_terms_version"] == current_version_string()
            assert order["aurya_privacy_version"] == current_version_string()
            assert order["aurya_source"] == "checkout"
            assert order["aurya_locale"] == "it"
            assert order["aurya_accepted_at"]
            # RS3 esteso: i requisiti accettati restano timbrati
            assert "controindicazione" in order["terms_content_snapshot"]
            assert order["terms_accepted_at"]
            # macchina merchant CG-5 intatta (autogen fallback)
            assert order["gdpr_terms_version"]

            account = db.platform_accounts.find_one({"email": email})
            assert account and account.get("aurya_legal")
            assert account["aurya_legal"]["source"] == "checkout"
            assert (account["aurya_legal"]["terms_version"]
                    == current_version_string())

            recs = list(db.consent_audit.find(
                {"customer_email": email, "source": "platform_checkout"}))
            assert len(recs) == 1
            assert recs[0]["order_id"] == order_id
            assert recs[0]["document_type"] == "privacy_terms"
        finally:
            self._delete_product(headers, prod["id"])
            self._cleanup_email(email)

    # ── 3. ordine da LOGGATO: niente ri-accettazione Aurya ───────────

    def test_apl_ordine_loggato_snapshot_da_account(self):
        """Compratore con account Aurya e consenso gia' timbrato: ordina
        SENZA flag aurya/gdpr (la checkbox non compare) accettando solo
        le condizioni dell'operatore: l'ordine eredita lo snapshot
        aurya_* dall'account (source account, stesso accepted_at) e
        NESSUN nuovo audit platform_checkout viene scritto."""
        import uuid
        from datetime import datetime, timezone

        from core.legal_versions import current_version_string

        email = "apl-logged@example.com"
        headers = self._admin_headers()
        self._cleanup_email(email)
        accepted_at = datetime.now(timezone.utc).isoformat()
        db = self._db()
        db.platform_accounts.insert_one({
            "id": str(uuid.uuid4()), "email": email, "name": "Apl Loggata",
            "language": "it", "email_verified": True, "is_active": True,
            "failed_login_attempts": 0, "lockout_count_today": 0,
            "created_at": accepted_at,
            "aurya_legal": {
                "terms_version": current_version_string(),
                "privacy_version": current_version_string(),
                "accepted_at": accepted_at,
                "source": "signup", "locale": "it",
            },
        })
        prod = self._make_service(
            headers, "Guardia AP-L loggato",
            metadata={"terms_content": "Condizioni operatore guardia."})
        try:
            r = requests.post(f"{BASE_URL}/api/public/order-request", json={
                "slug": "masseria-demo",
                "customer_name": "Apl Loggata",
                "customer_email": email,
                "items": [{"product_id": prod["id"], "quantity": 1}],
                "terms_accepted": True,          # condizioni operatore: si'
                "gdpr_terms_accepted": False,    # niente checkbox Aurya
                "gdpr_privacy_accepted": False,
                "aurya_terms_accepted": False,
                "locale": "it",
                "channel": "store",
            }, timeout=15)
            assert r.status_code == 200, r.text
            order = db.orders.find_one({"id": r.json()["order_id"]})
            assert order["aurya_source"] == "account"
            assert order["aurya_accepted_at"] == accepted_at
            assert order["aurya_terms_version"] == current_version_string()
            assert "operatore" in order["terms_content_snapshot"]
            # nessun nuovo audit piattaforma: il record vive dal signup
            assert db.consent_audit.count_documents(
                {"customer_email": email, "source": "platform_checkout"}) == 0
        finally:
            self._delete_product(headers, prod["id"])
            self._cleanup_email(email)

    # ── 4. senza condizioni operatore: nessuna checkbox, nessun gate ─

    def test_apl_senza_condizioni_niente_checkbox_operatore(self):
        """Servizio SENZA terms_content ne' policy: il catalogo pubblico
        espone terms_content nullo (la checkbox dinamica non esiste) e
        l'ordine passa senza terms_accepted, senza snapshot condizioni."""
        email = "apl-nocond@example.com"
        headers = self._admin_headers()
        self._cleanup_email(email)
        prod = self._make_service(headers, "Guardia AP-L senza condizioni")
        try:
            cat = requests.get(
                f"{BASE_URL}/api/public/catalog/masseria-demo",
                timeout=10).json()
            entry = next(p for p in cat["products"] if p["id"] == prod["id"])
            assert not entry.get("terms_content")
            assert not (entry.get("payment_plan") or {}).get(
                "cancellation_policy")

            r = requests.post(f"{BASE_URL}/api/public/order-request", json={
                "slug": "masseria-demo",
                "customer_name": "Apl NoCond",
                "customer_email": email,
                "items": [{"product_id": prod["id"], "quantity": 1}],
                "terms_accepted": False,
                "gdpr_terms_accepted": True,
                "gdpr_privacy_accepted": True,
                "aurya_terms_accepted": True,
                "locale": "it",
                "channel": "store",
            }, timeout=15)
            assert r.status_code == 200, r.text
            order = self._db().orders.find_one({"id": r.json()["order_id"]})
            assert "terms_content_snapshot" not in order
            assert order["aurya_source"] == "checkout"   # livello Aurya c'e'
        finally:
            self._delete_product(headers, prod["id"])
            self._cleanup_email(email)

        # frontend: la checkbox operatore e' gated dalle condizioni reali
        sf_dir = FRONTEND_SRC / "features" / "storefront"
        form = (sf_dir / "components" / "checkout"
                / "CheckoutForm.jsx").read_text()
        assert "{hasOperatorConditions && (" in form
        assert 'data-testid="operator-terms-checkbox"' in form
        hook = (sf_dir / "hooks" / "useCheckoutForm.js").read_text()
        assert ("const hasOperatorConditions = "
                "!!(effectiveTerms || cartCancellationPolicy)") in hook

    # ── 5. i requisiti dal listino arrivano al checkout ──────────────

    def test_apl_requisiti_dal_listino_al_checkout(self):
        """Il campo promosso nel listino (metadata.terms_content) esce
        risolto sul catalogo pubblico che alimenta il checkout
        condiviso (F4/terms_resolver): stessa strada del wizard."""
        headers = self._admin_headers()
        prod = self._make_service(headers, "Guardia AP-L listino")
        try:
            # stesso salvataggio della riga listino: merge del metadata
            r = requests.patch(
                f"{BASE_URL}/api/products/{prod['id']}", headers=headers,
                json={"metadata": {**(prod.get("metadata") or {}),
                                   "terms_content": "Requisiti dal listino."}},
                timeout=10)
            assert r.status_code == 200, r.text
            cat = requests.get(
                f"{BASE_URL}/api/public/catalog/masseria-demo",
                timeout=10).json()
            entry = next(p for p in cat["products"] if p["id"] == prod["id"])
            assert entry["terms_content"] == "Requisiti dal listino."
        finally:
            self._delete_product(headers, prod["id"])

        # superfici admin: textarea nel listino e nel passo Regole del
        # wizard ritiro (non piu' sepolta nel passo publish)
        listino = (FRONTEND_SRC / "features" / "listino"
                   / "ListinoPage.js").read_text()
        assert 'data-testid="listino-requisiti"' in listino
        assert "terms_content: edit.termsContent?.trim() || null" in listino
        assert "Requisiti e condizioni del servizio" in listino
        wiz = (FRONTEND_SRC / "features" / "events"
               / "EventWizard.js").read_text()
        assert 'data-testid="wizard-requisiti"' in wiz
        assert "wizards.event.regole.requisitiTitle" in wiz
        assert "wizards.event.publish.termsTitle')" not in wiz

    # ── 6. cablaggio a due livelli del checkout condiviso ────────────

    def test_apl_checkout_due_livelli_frontend(self):
        """CheckoutForm: checkbox Aurya per i guest (link /termini e
        /privacy), riga discreta per i loggati piattaforma, payload col
        flag aurya_terms_accepted; il merchant legal in Impostazioni e'
        ridimensionato a 'Condizioni dell'operatore' (custom = opzione
        avanzata, dialog esistente NON rimosso)."""
        sf_dir = FRONTEND_SRC / "features" / "storefront"
        form = (sf_dir / "components" / "checkout"
                / "CheckoutForm.jsx").read_text()
        assert 'data-testid="aurya-terms-checkbox"' in form
        assert 'data-testid="aurya-terms-already"' in form
        assert 'href="/termini"' in form and 'href="/privacy"' in form
        assert "{platformLoggedIn ? (" in form
        # niente doppia coppia di checkbox merchant: l'atto primario e' Aurya
        assert "checked={gdprPrivacyAccepted}" not in form
        assert "checked={gdprTermsAccepted}" not in form

        hook = (sf_dir / "hooks" / "useCheckoutForm.js").read_text()
        assert "payload.aurya_terms_accepted = !!auryaAccepted" in hook
        assert "PLATFORM_TOKEN_KEY" in hook
        assert "setAuryaConsent" in hook
        # loggato Aurya: gdprValid senza checkbox
        assert "|| platformLoggedIn" in hook

        # signup Aurya: riga consenso con link, obbligatoria
        login = (FRONTEND_SRC / "features" / "account"
                 / "AccountLoginPage.js").read_text()
        assert 'data-testid="signup-consent"' in login
        assert "accepted_terms: !!signupConsent" in login

        card = (FRONTEND_SRC / "features" / "settings" / "sections"
                / "SalesConditionsCard.jsx").read_text()
        assert "Condizioni dell'operatore" in card
        # PS5: l'editor legale custom e' congelato fuori dal mondo
        # snello (vive solo in /stores e /newsletter-forms); al suo
        # posto il mini-form titolare (vedi TestPotaturaPs5)
        assert 'data-testid="owner-data-form"' in card
        assert 'data-testid="service-requirements-hint"' in card

    # ── 7. testi Aurya estesi (bozza) + versioning coerente ──────────

    def test_apl_testi_aurya_v23_bozza_marcata(self):
        """I testi x4 lingue hanno le sezioni nuove (due livelli, art.
        28), il marcatore bozza vive SOLO come commento nei sorgenti e
        NON arriva all'utente finale; la versione corrente e' v2.3 e
        l'hash corrisponde al bundle IT su disco."""
        import hashlib

        from core.legal_versions import (CURRENT_VERSION_HASH,
                                         CURRENT_VERSION_TAG,
                                         get_legal_document)

        legal_dir = BACKEND_DIR / "legal"
        for lang in ("it", "en", "de", "fr"):
            for doc in ("privacy", "terms"):
                src = (legal_dir / f"{doc}_{lang}.md").read_text()
                assert "BOZZA IN ATTESA DI REVISIONE LEGALE" in src, (doc, lang)
                served = get_legal_document(doc, lang)["content"]
                assert "BOZZA" not in served, (doc, lang)
                assert "<!--" not in served, (doc, lang)
            # sezioni nuove servite (marker per lingua)
            assert "2.3" in get_legal_document("privacy", lang)["content"]

        assert CURRENT_VERSION_TAG == "v2.6"   # TR5: 9.1 nomina le composizioni audio
        priv = (legal_dir / "privacy_it.md").read_text()
        terms = (legal_dir / "terms_it.md").read_text()
        digest = hashlib.sha256(
            (priv + "\n\n--- TERMS BUNDLE ---\n\n" + terms).encode()
        ).hexdigest()[:16]
        assert digest == CURRENT_VERSION_HASH

        # l'audit accetta le nuove source piattaforma
        from repositories.consent_audit_repository import _VALID_SOURCES
        assert "platform_signup" in _VALID_SOURCES
        assert "platform_checkout" in _VALID_SOURCES


class TestAccountAp4:
    """AP4 (docs/ACCOUNT_UNICO_PIANO_2026-07.md, revisione founder) —
    il concetto 'Passaporto' e' eliminato dall'esperienza utente:
    l'account e' uno, classico, 'il tuo account Aurya'. Queste guardie
    scansionano i VALORI (le stringhe che l'utente legge) e diventano
    rosse se il vecchio nome ricompare in una qualsiasi lingua.

    Esclusioni motivate:
    - NOMI INTERNI (chiavi i18n 'auryaPassportHint'/'passportLink'/
      'activatePassport', chiavi email 'passport_*', testid
      'aurya-passport-hint', commenti): rinominarli costerebbe
      regressioni su guardie e template senza alcun effetto visibile.
      Si scansionano solo i valori, mai le chiavi.
    - backend/legal/*.md: i testi legali definiscono ancora l'account
      'Passaporto Ritiri' e sono blindati dall'hash consensi v2.3
      (test_consent_version_bumped_and_hash_matches_files): la loro
      riscrittura passa dal legale con bump versione + re-consent
      (AP-L / pre-lancio), non da un copy pass.
    """

    import re as _re
    # copre Passaporto/Passaporti (it), Passport (en/de), Passeport (fr)
    PATTERN = _re.compile(r"pass[ae]?port", _re.IGNORECASE)

    def _iter_strings(self, node):
        if isinstance(node, dict):
            for value in node.values():
                yield from self._iter_strings(value)
        elif isinstance(node, list):
            for value in node:
                yield from self._iter_strings(value)
        elif isinstance(node, str):
            yield node

    def test_ap4_locales_senza_passaporto(self):
        """Tutti i namespace i18n, tutte e 4 le lingue: nessuna stringa
        user-facing contiene piu' Passaporto/Passport/Passeport."""
        import json
        offenders = []
        for lang in ("it", "en", "de", "fr"):
            for path in sorted((FRONTEND_SRC / "locales" / lang).glob("*.json")):
                data = json.loads(path.read_text())
                for text in self._iter_strings(data):
                    if self.PATTERN.search(text):
                        offenders.append((lang, path.name, text[:80]))
        assert not offenders, offenders

    def test_ap4_email_transazionali_senza_passaporto(self):
        """EMAIL_TRANSLATIONS (4 lingue): i testi delle email non
        nominano mai il Passaporto (le chiavi passport_* restano come
        nomi interni)."""
        from services.email_service import EMAIL_TRANSLATIONS
        offenders = []
        for lang, table in EMAIL_TRANSLATIONS.items():
            for key, msg in table.items():
                if isinstance(msg, str) and self.PATTERN.search(msg):
                    offenders.append((lang, key, msg[:80]))
        assert not offenders, offenders

    def test_ap4_claim_email_invita_alla_password(self):
        """La claim post-acquisto ora parla dell'account Aurya e invita
        a impostare la password (assetto password-first AP1b)."""
        from services.email_service import EMAIL_TRANSLATIONS
        expectations = {
            "it": ("account Aurya", "password"),
            "en": ("Aurya account", "password"),
            "de": ("Aurya Konto", "Passwort"),
            "fr": ("compte Aurya", "mot de passe"),
        }
        for lang, (brand, pwd) in expectations.items():
            blob = " ".join(
                EMAIL_TRANSLATIONS[lang][key] for key in
                ("passport_claim_subject", "passport_claim_body",
                 "passport_claim_cta", "passport_claim_footer"))
            assert brand in blob, lang
            assert pwd in blob, lang
            assert "—" not in blob, lang        # mai trattini lunghi


class TestAccountAp5:
    """AP5 (docs/ACCOUNT_UNICO_PIANO_2026-07.md) — chiusura del ciclo
    Account Unico: guardie SOLO per i buchi della matrice E2E. Il resto
    della matrice e' gia' coperto (censimento 29/7):

      1. guest da profilo  → TestAccountApL.test_apl_ordine_guest_* (consensi
         due livelli + account pending + audit); QUI: marketing nel CRM e
         claim email alla conferma della richiesta.
      2. acquisto diretto  → QUI: viaggio live ordine→session→webhook
         simulato→claim→hub (i pezzi unitari vivono in
         test_payment_checkout_integration e TestP2ClaimEmail).
      3. login tre vie     → TestLoginCode/TestMagicLinkService/AP1b; QUI:
         le TRE strade live sullo STESSO account, stessa identita'.
      4. guide/newsletter  → TestHubAccountAp2 + test_f1/f2 newsletter; QUI
         (dentro il login tre vie): newsletter_subscriber coerente.
      5. password lifecycle→ TestAccountAp1b; QUI: il reset su account
         passwordless AGGANCIA lo storico (retroactive_claim).
      6. errori onesti     → AP1b (409/403/401/423, reset one-shot) +
         TestLoginCode (OTP); QUI: token verifica/reset SCADUTI.
      7. GDPR              → TestP4Gdpr (unit); QUI: export+delete live via
         HTTP col nuovo assetto, ordini operatore intatti.
      8. isolamento        → TestP2OrderLinking (unit); QUI: due org VERE,
         un account, /me/orders con entrambi, customer per-org separati.
      9. regressione       → TestInvariants, CG2/CG4, TW/RS/PN/LM: gia'
         tutte guardie vive nella suite (nessun doppione qui).
    """

    PASSWORD = "StrongPass12"

    # ── riuso infrastruttura live AP-L ──────────────────────────────────
    @classmethod
    def _admin_headers(cls):
        return TestAccountApL._admin_headers()

    @staticmethod
    def _db():
        return TestAccountApL._db()

    @classmethod
    def _cleanup_email(cls, email):
        """AP-L cleanup + artefatti della conferma (sales, schedule,
        ledger, ticket) che gli ordini AP5 confermati generano."""
        db = cls._db()
        email = email.lower()
        pa_ids = [a["id"] for a in
                  db.platform_accounts.find({"email": email}, {"id": 1})]
        cust_ids = [c["id"] for c in
                    db.customers.find({"email": email}, {"id": 1})]
        order_ids = [o["id"] for o in db.orders.find({"$or": [
            {"customer_id": {"$in": cust_ids}},
            {"platform_account_id": {"$in": pa_ids}},
        ]}, {"id": 1})]
        if order_ids:
            db.sales_records.delete_many(
                {"metadata.order_id": {"$in": order_ids}})
            db.payment_schedules.delete_many({"order_id": {"$in": order_ids}})
            db.platform_fee_ledger.delete_many({"order_id": {"$in": order_ids}})
            db.issued_tickets.delete_many({"order_id": {"$in": order_ids}})
            db.issued_bookings.delete_many({"order_id": {"$in": order_ids}})
            db.orders.delete_many({"id": {"$in": order_ids}})
        TestAccountApL._cleanup_email(email)
        db.aurya_subscribers.delete_many({"email": email})

    @classmethod
    def _insert_magic_token(cls, account_id):
        """Token magic con hash noto (la via del browser/dei test live:
        il chiaro non e' mai recuperabile dal DB)."""
        import hashlib
        import secrets
        import uuid
        from datetime import datetime, timedelta, timezone

        token = secrets.token_urlsafe(24)
        code = f"{secrets.randbelow(1_000_000):06d}"
        cls._db().platform_magic_tokens.insert_one({
            "id": str(uuid.uuid4()),
            "account_id": account_id,
            "token_hash": hashlib.sha256(token.encode()).hexdigest(),
            "code_hash": hashlib.sha256(code.encode()).hexdigest(),
            "code_attempts": 0,
            "used_at": None,
            "expires_at": (datetime.now(timezone.utc)
                           + timedelta(minutes=10)).isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        return token, code

    @classmethod
    def _platform_login(cls, account_id):
        token, _ = cls._insert_magic_token(account_id)
        r = requests.post(f"{BASE_URL}/api/platform/auth/magic-link/verify",
                          json={"token": token}, timeout=10)
        assert r.status_code == 200, r.text
        body = r.json()
        return {"Authorization": f"Bearer {body['access_token']}"}, body

    @staticmethod
    def _order_request(email, product_id, *, slug="masseria-demo",
                       name="Guardia Ap5", marketing=False):
        r = requests.post(f"{BASE_URL}/api/public/order-request", json={
            "slug": slug, "customer_name": name, "customer_email": email,
            "items": [{"product_id": product_id, "quantity": 1}],
            "terms_accepted": False,
            "gdpr_terms_accepted": True, "gdpr_privacy_accepted": True,
            "gdpr_marketing_accepted": bool(marketing),
            "aurya_terms_accepted": True,
            "locale": "it", "channel": "store",
        }, timeout=30)
        assert r.status_code == 200, r.text
        return r.json()

    # ── 1. guest da profilo: marketing nel CRM + claim alla conferma ────

    def test_ap5_richiesta_guest_marketing_e_claim_su_conferma(self):
        """Richiesta servizio da guest con opt-in marketing: il CRM
        timbra accepted_marketing_at + audit merchant_marketing; la
        CONFERMA della richiesta (RS5) fa partire la claim email
        dell'account Aurya pending (timestamp + token magic emesso)."""
        email = "ap5-guest@example.com"
        headers = self._admin_headers()
        self._cleanup_email(email)
        apl = TestAccountApL()
        prod = apl._make_service(headers, "Guardia AP5 guest marketing")
        try:
            out = self._order_request(email, prod["id"], marketing=True)
            order_id = out["order_id"]
            db = self._db()

            cust = db.customers.find_one({"email": email})
            assert cust and cust.get("accepted_marketing_at")
            assert not cust.get("marketing_revoked_at")
            mk = list(db.consent_audit.find(
                {"customer_email": email,
                 "document_type": "merchant_marketing"}))
            assert len(mk) == 1
            assert mk[0]["source"] == "customer_marketing_optin"

            account = db.platform_accounts.find_one({"email": email})
            assert account and not account.get("email_verified")   # pending
            assert not account.get("claim_last_sent_at")           # non ancora

            r = requests.post(f"{BASE_URL}/api/orders/{order_id}/confirm",
                              headers=headers, timeout=15)
            assert r.status_code == 200, r.text

            account = db.platform_accounts.find_one({"email": email})
            assert account.get("claim_last_sent_at")               # claim inviata
            assert db.platform_magic_tokens.count_documents(
                {"account_id": account["id"]}) >= 1                # link emesso
        finally:
            apl._delete_product(headers, prod["id"])
            self._cleanup_email(email)

    # ── 2. acquisto diretto: session → webhook simulato → claim → hub ───

    def test_ap5_acquisto_diretto_webhook_claim_e_hub(self):
        """Ordine direct: session Stripe creata (fin dove il dev arriva),
        webhook checkout.session.completed SIMULATO col reconciler vero
        (stesso pattern verify_/synthetic della suite) → ordine
        confermato, incasso registrato, claim email partita, ordine
        visibile in /account via /platform/me/orders."""
        import json as _json
        import os as _os
        import subprocess

        email = "ap5-direct@example.com"
        headers = self._admin_headers()
        self._cleanup_email(email)
        apl = TestAccountApL()
        _ensure_dpa_ack(headers)   # PV7 — gate creazione prodotti vendibili
        r = requests.post(f"{BASE_URL}/api/products", headers=headers, json={
            "name": "Guardia AP5 direct", "item_type": "service",
            "transaction_mode": "direct", "is_published": True,
            "unit_price": 40, "price_mode": "fixed"}, timeout=10)
        assert r.status_code in (200, 201), r.text
        prod = r.json()
        try:
            out = self._order_request(email, prod["id"])
            assert out["transaction_mode"] == "direct"
            order_id = out["order_id"]
            db = self._db()
            order = db.orders.find_one({"id": order_id})
            assert order["payment_intent"] == "required"
            # fin dove il dev consente: la session test viene creata e
            # l'URL di redirect e' quello di Stripe Checkout (se la rete
            # verso Stripe manca, il reconcile sotto resta comunque valido)
            if out.get("payment_checkout_url"):
                assert out["payment_checkout_url"].startswith(
                    "https://checkout.stripe.com/")

            # webhook simulato: evento sintetico sul reconciler canonico,
            # eseguito nel venv del backend contro il DB del server live
            ref = (order.get("payment_checkout") or {}).get("reference")
            script = f"""
import asyncio, json
async def main():
    from services.payment_checkout_service import reconcile_checkout_event
    event = {{
        "id": "evt_ap5_guard_{order_id[:8]}",
        "type": "checkout.session.completed",
        "account": None,
        "data": {{"object": {{
            "id": {ref!r} or "cs_test_ap5_guard",
            "payment_status": "paid",
            "payment_intent": "pi_ap5_guard",
            "currency": "eur",
            "metadata": {{"source": "afianco",
                          "org_id": {order["organization_id"]!r},
                          "order_id": {order_id!r},
                          "schedule_row_seq": "0"}},
            "amount_total": 4000,
        }}}},
    }}
    print(json.dumps(await reconcile_checkout_event(event)))
asyncio.run(main())
"""
            env = {k: v for k, v in _os.environ.items()
                   if k not in ("MONGO_URL", "DB_NAME")}
            proc = subprocess.run(
                [str(BACKEND_DIR / "venv" / "bin" / "python"), "-"],
                input=script, capture_output=True, text=True,
                cwd=BACKEND_DIR, env=env, timeout=120)
            assert proc.returncode == 0, proc.stderr[-2000:]
            result = _json.loads(proc.stdout.strip().splitlines()[-1])
            assert result["action"] == "confirmed", result

            order = db.orders.find_one({"id": order_id})
            assert order["status"] == "confirmed"
            assert order["payment_intent"] == "collected"

            # claim email al pagamento riuscito (account ancora pending)
            account = db.platform_accounts.find_one({"email": email})
            assert account.get("claim_last_sent_at")

            # l'ordine e' nel suo /account
            ph, _ = self._platform_login(account["id"])
            r = requests.get(f"{BASE_URL}/api/platform/me/orders",
                             headers=ph, timeout=10)
            assert r.status_code == 200, r.text
            rows = [o for o in r.json()["orders"] if o["id"] == order_id]
            assert rows and rows[0]["status"] == "confirmed"
            assert rows[0]["transaction_mode"] == "direct"
        finally:
            apl._delete_product(headers, prod["id"])
            self._cleanup_email(email)

    # ── 3+4. login tre vie sullo stesso account + newsletter coerente ───

    def test_ap5_login_tre_vie_stesso_account(self):
        """Password, OTP e magic link entrano tutte nello STESSO account
        (stessa identita', stesso shape di risposta) e il flag
        newsletter_subscriber e' coerente: False da non iscritto, True +
        subscriber_token appena l'iscrizione e' confermata."""
        import uuid
        from datetime import datetime, timezone

        from auth import get_password_hash

        email = "ap5-tre-vie@example.com"
        self._cleanup_email(email)
        db = self._db()
        account_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        db.platform_accounts.insert_one({
            "id": account_id, "email": email, "name": "Tre Vie",
            "language": "it", "email_verified": True, "is_active": True,
            "password_hash": get_password_hash(self.PASSWORD),
            "failed_login_attempts": 0, "lockout_count_today": 0,
            "locked_until": None, "sessions_invalidated_at": None,
            "created_at": now,
        })
        try:
            # 1. password
            r = requests.post(f"{BASE_URL}/api/platform/auth/login", json={
                "email": email, "password": self.PASSWORD}, timeout=10)
            assert r.status_code == 200, r.text
            pw = r.json()
            assert pw["account"]["id"] == account_id
            assert pw["newsletter_subscriber"] is False
            assert "subscriber_token" not in pw

            # 2. OTP (codice a 6 cifre)
            _, code = self._insert_magic_token(account_id)
            r = requests.post(f"{BASE_URL}/api/platform/auth/code/verify",
                              json={"email": email, "code": code}, timeout=10)
            assert r.status_code == 200, r.text
            otp = r.json()
            assert otp["account"]["id"] == account_id

            # 3. magic link
            token, _ = self._insert_magic_token(account_id)
            r = requests.post(
                f"{BASE_URL}/api/platform/auth/magic-link/verify",
                json={"token": token}, timeout=10)
            assert r.status_code == 200, r.text
            ml = r.json()
            assert ml["account"]["id"] == account_id
            # stesso shape su tutte le strade
            for body in (pw, otp, ml):
                assert set(body) >= {"access_token", "token_type",
                                     "account", "newsletter_subscriber"}

            # iscrizione confermata → il login porta il token guide
            db.aurya_subscribers.insert_one({
                "id": str(uuid.uuid4()), "email": email,
                "status": "confirmed", "created_at": now})
            r = requests.post(f"{BASE_URL}/api/platform/auth/login", json={
                "email": email, "password": self.PASSWORD}, timeout=10)
            assert r.status_code == 200, r.text
            assert r.json()["newsletter_subscriber"] is True
            assert r.json()["subscriber_token"]
        finally:
            self._cleanup_email(email)

    # ── 5+6. reset aggancia lo storico + token scaduti rifiutati ────────

    async def test_ap5_reset_aggancia_storico_e_token_scaduti(self):
        """(a) confirm_password_reset su account nato passwordless chiama
        retroactive_claim (lo storico ordini si aggancia); (b) token di
        verifica e di reset SCADUTI → INVALID_TOKEN (con l'hash ancora a
        DB: il rifiuto e' sulla scadenza, non sull'assenza)."""
        from contextlib import ExitStack
        from datetime import timedelta
        from unittest.mock import AsyncMock, patch

        import pytest
        from models.common import utc_now
        from services import platform_account_service as svc

        Ap1b = TestAccountAp1b
        fake, sent = Ap1b._MemAccounts(), {}
        claim = AsyncMock()
        with ExitStack() as stack:
            for p in Ap1b()._ctx(fake, sent):
                stack.enter_context(p)
            stack.enter_context(patch.object(svc, "retroactive_claim", claim))

            # (a) account passwordless da acquisto guest: reset = imposta
            # password + claim retroattivo dello storico
            fake.docs["g1"] = {"id": "g1", "email": "ap5-claim@x.it",
                               "email_verified": False, "password_hash": None,
                               "language": "it"}
            await svc.request_password_reset("ap5-claim@x.it")
            await svc.confirm_password_reset(sent["reset_token"],
                                             self.PASSWORD)
            assert claim.await_count == 1          # storico agganciato
            assert claim.await_args[0][0]["id"] == "g1"

            # (b) verifica scaduta: hash presente ma oltre il TTL
            await svc.password_signup(name="S", email="ap5-scad@x.it",
                                      password=self.PASSWORD)
            acc = [d for d in fake.docs.values()
                   if d["email"] == "ap5-scad@x.it"][0]
            acc["verification_token_expires"] = (
                utc_now() - timedelta(hours=1)).isoformat()
            with pytest.raises(ValueError, match="INVALID_TOKEN"):
                await svc.verify_signup_email(sent["verify_token"])

            # (b) reset scaduto: stesso rifiuto
            await svc.request_password_reset("ap5-scad@x.it")
            acc["reset_token_expires"] = (
                utc_now() - timedelta(minutes=5)).isoformat()
            with pytest.raises(ValueError, match="INVALID_TOKEN"):
                await svc.confirm_password_reset(sent["reset_token"],
                                                 self.PASSWORD)

    # ── 7. GDPR live: export + delete col nuovo assetto ─────────────────

    def test_ap5_gdpr_export_delete_live(self):
        """Export via HTTP porta identita' + ordini (vista cliente);
        DELETE /platform/me cancella l'identita' e i token ma NON tocca
        l'ordine ne' il CRM dell'operatore (solo unlink dello stamp)."""
        email = "ap5-gdpr@example.com"
        headers = self._admin_headers()
        self._cleanup_email(email)
        apl = TestAccountApL()
        prod = apl._make_service(headers, "Guardia AP5 gdpr")
        try:
            out = self._order_request(email, prod["id"])
            order_id = out["order_id"]
            db = self._db()
            account = db.platform_accounts.find_one({"email": email})
            ph, _ = self._platform_login(account["id"])

            r = requests.get(f"{BASE_URL}/api/platform/me/export",
                             headers=ph, timeout=10)
            assert r.status_code == 200, r.text
            exp = r.json()
            assert exp["account"]["email"] == email
            assert [o["id"] for o in exp["orders"]] == [order_id]
            blob = str(exp)
            for banned in ("cost_price", "application_fee", "notes"):
                assert banned not in blob

            r = requests.delete(f"{BASE_URL}/api/platform/me",
                                headers=ph, timeout=10)
            assert r.status_code == 200, r.text
            assert r.json()["status"] == "deleted"

            # identita' e token VIA; dati operatore INTATTI, solo unlink
            assert not db.platform_accounts.find_one({"email": email})
            assert db.platform_magic_tokens.count_documents(
                {"account_id": account["id"]}) == 0
            order = db.orders.find_one({"id": order_id})
            assert order and "platform_account_id" not in order
            assert db.customers.find_one({"email": email})   # CRM operatore
        finally:
            apl._delete_product(headers, prod["id"])
            self._cleanup_email(email)

    # ── 8. isolamento: due org vere, UN account, dati mai mescolati ─────

    def test_ap5_isolamento_due_org_live(self):
        """Stessa email compra su masseria-demo E borgo-sereno: nasce UN
        solo platform account, /me/orders mostra entrambi gli ordini coi
        nomi dei DUE operatori, il CRM resta un record per org."""
        import uuid

        email = "ap5-iso@example.com"
        headers = self._admin_headers()
        self._cleanup_email(email)
        apl = TestAccountApL()
        prod_a = apl._make_service(headers, "Guardia AP5 iso masseria")
        db = self._db()
        # per l'org borgo non abbiamo credenziali admin nei test: il
        # prodotto di guardia nasce come CLONE dello schema del prodotto
        # vero (stessa forma dati), con org e id propri
        borgo_org = "afca4458-6b11-44d1-811a-60e79df8a928"
        prod_b = dict(db.products.find_one({"id": prod_a["id"]}, {"_id": 0}))
        prod_b.update({"id": str(uuid.uuid4()),
                       "organization_id": borgo_org,
                       "name": "Guardia AP5 iso borgo", "slug": None})
        db.products.insert_one(dict(prod_b))
        try:
            out_a = self._order_request(email, prod_a["id"],
                                        slug="masseria-demo")
            out_b = self._order_request(email, prod_b["id"],
                                        slug="borgo-sereno")

            accounts = list(db.platform_accounts.find({"email": email}))
            assert len(accounts) == 1                     # UNA identita'
            aid = accounts[0]["id"]
            for oid in (out_a["order_id"], out_b["order_id"]):
                assert db.orders.find_one({"id": oid})[
                    "platform_account_id"] == aid

            custs = list(db.customers.find({"email": email}))
            assert len(custs) == 2                        # CRM per-org separati
            assert ({c["organization_id"] for c in custs}
                    == {"2393033b-80a8-47c9-8529-b7810c0b2123", borgo_org})

            ph, _ = self._platform_login(aid)
            r = requests.get(f"{BASE_URL}/api/platform/me/orders",
                             headers=ph, timeout=10)
            assert r.status_code == 200, r.text
            rows = {o["id"]: o for o in r.json()["orders"]}
            assert {out_a["order_id"], out_b["order_id"]} <= set(rows)
            names = {rows[out_a["order_id"]]["operator_name"],
                     rows[out_b["order_id"]]["operator_name"]}
            assert len(names) == 2                        # due operatori veri
        finally:
            apl._delete_product(headers, prod_a["id"])
            db.products.delete_many({"id": prod_b["id"]})
            self._cleanup_email(email)


class TestPotaturaPs1:
    """PS1 (30/7/2026) — back onesti: le dashboard raggiungibili dal
    mondo snello non riportano MAI alla ProductsPage legacy.

    ServiceDashboardPage (da /listino "Impostazioni avanzate") torna a
    /listino in tutti e tre i punti (hero back + due stati di errore);
    EventDashboardPage not-found e CheckInPage tornano a /events. La
    ProductsPage resta viva SOLO per le org legacy_commerce (voce di
    menu dietro flag, Layout.js): qui si vieta solo la strada dal
    mondo snello.
    """

    def test_ps1_service_dashboard_torna_al_listino(self):
        page = (FRONTEND_SRC / "features" / "services"
                / "ServiceDashboardPage.js").read_text()
        assert 'to="/products' not in page \
            and "navigate('/products" not in page, \
            "ServiceDashboardPage non deve piu' linkare la ProductsPage legacy"
        assert page.count("'/listino'") + page.count('"/listino"') >= 3, \
            "attesi 3 ritorni a /listino (hero + not_found + wrong_type)"

    def test_ps1_ecosistema_ritiri_torna_ai_ritiri(self):
        for rel in (("features", "events", "EventDashboardPage.js"),
                    ("features", "events", "CheckInPage.js")):
            src = FRONTEND_SRC.joinpath(*rel).read_text()
            assert 'to="/products"' not in src and "navigate('/products')" not in src, \
                f"{rel[-1]} non deve riportare alla ProductsPage legacy"


class TestPotaturaPs2:
    """PS2 (30/7/2026) — /services/:id ridotta a editor AVANZATO onesto
    (docs/POTATURA_STORE_PIANO_2026-07.md). Restano SOLO le sezioni che
    non hanno altra casa: descrizione estesa + copertina landing (con
    multilingua), traduzioni di nome/nota, regole orari per-giorno,
    campi ordine custom, anteprima/copia link/duplica. Tutto cio' che
    duplicava la riga espansa del listino (LM1) e la sezione morta
    Distribuzione sono stati potati. Il salvataggio manda un payload
    PARZIALE (exclude_unset lato API) con merge del metadata esistente:
    i campi del listino non possono essere azzerati da qui."""

    PAGE = (FRONTEND_SRC / "features" / "services"
            / "ServiceDashboardPage.js")
    LISTINO = FRONTEND_SRC / "features" / "listino" / "ListinoPage.js"

    def test_ps2_sezioni_duplicate_potate(self):
        page = self.PAGE.read_text()
        assert "ProductSalesStats" not in page      # Incassi/Ordini coprono
        assert "ServiceOptionsEditor" not in page   # opzioni: nel listino
        assert "distribu" not in page.lower()       # sezione morta
        assert "quickTogglePublish" not in page \
            and "statusTitle" not in page           # stato: toggle Eye listino
        assert "terms_content" not in page          # requisiti: nel listino
        assert "transaction_mode" not in page       # incasso: nel listino
        assert "unit_price" not in page             # prezzo: nel listino
        assert "is_published" not in page           # stato: nel listino
        assert "upcomingTitle" not in page          # agenda: nel Calendario

    def test_ps2_sezioni_superstiti(self):
        page = self.PAGE.read_text()
        assert "AvailabilityRulesEditor" in page    # regole orari per-giorno
        assert "use_default_schedule" in page       # toggle calendario ufficiale
        assert "long_description" in page           # descrizione estesa landing
        assert "cover_image_url" in page            # copertina landing
        assert "FieldEditorList" in page            # campi ordine custom
        assert "MultiLangSection" in page           # traduzioni
        assert "service_allow_custom_request" in page
        assert "handleDuplicate" in page and "copyLandingUrl" in page
        assert "Impostazioni avanzate del servizio" in page  # titolo onesto

    def test_ps2_payload_parziale_con_merge_metadata(self):
        """Nessun campo del listino nel payload di update: il metadata
        fa merge sull'esistente, il resto viaggia via exclude_unset."""
        page = self.PAGE.read_text()
        assert "...existingMeta" in page
        assert "translations: buildTranslationsPayload()" in page
        # le due strade di salvataggio: saveProduct + flag immediati
        assert page.count("productsAPI.update(") == 2

    def test_ps2_label_listino_impostazioni_avanzate(self):
        listino = self.LISTINO.read_text()
        assert "Tutte le impostazioni" not in listino
        assert "Impostazioni avanzate" in listino
        assert "impostazioni avanzate" in listino   # link regole orari

    def test_ps2_niente_store_nel_copy_pagina(self):
        page = self.PAGE.read_text()
        assert "store" not in page.lower()
        assert "negozio" not in page.lower()

    def test_ps2_i18n_x4(self):
        """Chiavi nuove presenti e chiavi morte assenti nei 4 locales."""
        import json as _json
        for lang in ("it", "en", "de", "fr"):
            loc = _json.loads((FRONTEND_SRC / "locales" / lang
                               / "products.json").read_text())
            svc = loc["dashboards"]["service"]
            for key in ("pageTitle", "baseHint", "translationsTitle",
                        "translationsSave", "coverLabel",
                        "allowCustomTitle", "orderFieldsSave"):
                assert key in svc, f"{lang}: manca {key}"
            for key in ("statusTitle", "product", "orderFieldsHint",
                        "distributionDesc", "optionsTitle", "termsTitle",
                        "upcomingTitle"):
                assert key not in svc, f"{lang}: chiave morta {key}"
            assert "advancedSettings" in loc.get("listino", {}), \
                f"{lang}: manca listino.advancedSettings"


class TestPotaturaPs3:
    """PS3 (30/7/2026) — bonifica olistica di "store" e vecchia pagina
    prodotti dalle superfici raggiungibili da un operatore snello
    (docs/POTATURA_STORE_PIANO_2026-07.md, onda PS3).

    Il wizard ritiri garantisce lo store tecnico in silenzio
    (ensureDefault, stesso pattern del Listino) e non mostra mai banner
    o CTA verso /stores; la sezione Distribuzione (wizard + dashboard
    prodotto superstiti) esiste SOLO nel mondo multi-store legacy
    (>1 store); le Impostazioni parlano di profilo pubblico /o/, non di
    catalogo /s/; il copy piani parla di profilo pubblico, non di
    negozio online; /store-settings redirige a /settings. Le scansioni
    sono ancorate a file e sezioni intere, mai a offset di riga.
    """

    WIZARD = FRONTEND_SRC / "features" / "events" / "EventWizard.js"
    SETTINGS = FRONTEND_SRC / "features" / "settings" / "SettingsPage.js"
    APP = FRONTEND_SRC / "App.js"

    def test_ps3_wizard_senza_cta_stores_con_ensure_default(self):
        src = self.WIZARD.read_text()
        assert 'href="/stores"' not in src and "storeRequired" not in src, \
            "il passo Pubblica non deve mai chiedere di creare uno store"
        assert "storesAPI.ensureDefault()" in src, \
            "lo store tecnico va garantito in silenzio (pattern Listino)"

    def test_ps3_wizard_distribuzione_solo_multi_store(self):
        src = self.WIZARD.read_text()
        assert "availableStores.length > 1 && (" in src, \
            "la Distribuzione appare solo col multi-store legacy"
        # il ramo <=1 ("Visibile automaticamente in: <store>") e' potato
        assert "visibleAutoPrefix" not in src
        assert "distributionDesc" not in src

    def test_ps3_dashboard_distribuzione_solo_multi_store(self):
        for rel in (("features", "physicals", "PhysicalDashboardPage.js"),
                    ("features", "digitals", "DigitalDashboardPage.js"),
                    ("features", "reservations",
                     "ReservationDashboardPage.js")):
            src = FRONTEND_SRC.joinpath(*rel).read_text()
            assert "stores.length > 1 && (" in src, \
                f"{rel[-1]}: sezione Distribuzione senza gate multi-store"
        event = (FRONTEND_SRC / "features" / "events"
                 / "EventDashboardPage.js").read_text()
        assert "availableStores.length > 1 && (" in event
        assert "availableStores.length > 0 && (" not in event

    def test_ps3_settings_indirizzo_in_chiave_profilo(self):
        src = self.SETTINGS.read_text()
        assert "/s/" not in src, "niente prefisso storefront legacy"
        assert "negozio" not in src.lower() \
            and "catalogo" not in src.lower(), \
            "la sezione indirizzo parla di profilo, non di commerce"
        assert "/o/" in src and "Indirizzo pubblico del tuo profilo" in src
        # lo slug del profilo e dello store tecnico restano allineati
        # (il sync vive in handleSave, solo se erano gia' allineati)
        assert "storesAPI.list()" in src and "storesAPI.update(" in src

    def test_ps3_rotta_store_settings_redirect(self):
        app = self.APP.read_text()
        assert "StoreSettingsPage" not in app, \
            "la pagina StoreSettingsPage non deve piu' essere importata"
        assert ('path="/store-settings" '
                'element={<Navigate to="/settings" replace />}') in app

    def test_ps3_nav_store_settings_rimossa_x4(self):
        import json as _json
        for lang in ("it", "en", "de", "fr"):
            nav = _json.loads((FRONTEND_SRC / "locales" / lang
                               / "common.json").read_text())["nav"]
            assert "store_settings" not in nav, f"{lang}: label morta"

    def test_ps3_copy_piani_profilo_pubblico_x4(self):
        """Le feature dei piani parlano di profilo pubblico, mai di
        negozio online (IT) o equivalenti nelle altre lingue."""
        import json as _json

        def _find_parent(node, key):
            if isinstance(node, dict):
                if key in node:
                    return node
                for v in node.values():
                    r = _find_parent(v, key)
                    if r is not None:
                        return r
            elif isinstance(node, list):
                for v in node:
                    r = _find_parent(v, key)
                    if r is not None:
                        return r
            return None

        forbidden = {"it": ("negozio",),
                     "en": ("online store",),
                     "de": ("online-shop",),
                     "fr": ("boutique en ligne",)}
        for lang, bads in forbidden.items():
            loc = _json.loads((FRONTEND_SRC / "locales" / lang
                               / "settings.json").read_text())
            feats = _find_parent(loc, "retreat_ecommerce")
            assert feats is not None, f"{lang}: piani retreat_* spariti?"
            for key, val in feats.items():
                if not key.startswith("retreat_"):
                    continue
                for bad in bads:
                    assert bad not in val.lower(), f"{lang}:{key}: {val}"
            # il profilo pubblico e' entrato nel copy della feature clou
            assert "profil" in feats["retreat_ecommerce"].lower(), \
                f"{lang}: retreat_ecommerce non parla di profilo"

    def test_ps3_inizia_lean_vetrina_non_negozio(self):
        src = (FRONTEND_SRC / "features" / "onboarding"
               / "IniziaPage.js").read_text()
        assert "la tua vetrina insieme" in src
        assert "il tuo negozio insieme" not in src
        # gli step legacy ("Crea il tuo store") restano SOLO nel ramo
        # LEGACY_STEPS, selezionato dallo shape dello status backend
        # (org.legacy_commerce): il mondo lean usa LEAN_STEPS
        assert "lean ? LEAN_STEPS : LEGACY_STEPS" in src

    def test_ps3_legal_dialog_senza_link_stores(self):
        src = (FRONTEND_SRC / "features" / "stores" / "components"
               / "MerchantLegalDialog.js").read_text()
        assert 'href="/stores"' not in src, \
            "il dialog si apre anche dal mondo snello: CTA neutra"
        assert "active_locale_link_text" not in src

    def test_ps3_layout_codice_morto_potato(self):
        src = (FRONTEND_SRC / "components" / "Layout.js").read_text()
        assert "const operationsNav" not in src \
            and "const moduleNavMap" not in src, \
            "nav morta con /stores: va rimossa, non lasciata dormiente"
        # la voce Store resta SOLO dietro il flag legacy_commerce
        assert "legacyCommerce" in src


class TestPotaturaPs4:
    """PS4 (30/7/2026) — icona account utente nell'header pubblico +
    UN SOLO login utente (docs/POTATURA_STORE_PIANO_2026-07.md, onda
    PS4). L'omino CircleUserRound e' l'entry point universale (tutti i
    breakpoint, tutte le fasi, network inclusa: decisione founder); il
    token piattaforma si legge in modo sincrono da localStorage; senza
    token si atterra su /account/accedi, con token su /account. Del
    portale clienti legacy restano vive SOLO le rotte strutturali del
    player corsi; signup/ordini/profilo legacy redirigono ad Aurya.
    """

    SHELL = (FRONTEND_SRC / "features" / "storefront" / "components"
             / "MarketplaceShell.jsx")
    APP = FRONTEND_SRC / "App.js"

    def test_ps4_icona_account_nello_shell(self):
        src = self.SHELL.read_text()
        assert "CircleUserRound" in src, \
            "l'omino account deve vivere nell'header marketplace"
        assert "PLATFORM_TOKEN_KEY" in src, \
            "lo stato loggato si legge dal token piattaforma (sincrono)"
        assert "'/account'" in src and "'/accedi'" in src, \
            "destinazioni: /account da loggato, /accedi da sloggato (ID)"
        assert "marketplace.accountAria" in src, \
            "aria-label i18n dell'icona account"
        # LR1: l'omino e' il trigger del menu dei due mondi (un <button,
        # non piu' un Link). Non e' nascosto dietro breakpoint: nessun
        # hidden sul bottone trigger (il pill myTrips resta hidden sm)
        icon_at = src.index("CircleUserRound className")
        btn_open = src.rindex("<button", 0, icon_at)
        assert 'data-testid="account-menu-trigger"' in src[btn_open:icon_at], \
            "l'omino deve essere il trigger del menu account (LR1)"
        assert "hidden" not in src[btn_open:icon_at], \
            "l'icona account deve essere visibile a TUTTI i breakpoint"

    def test_ps4_icona_anche_in_fase_network(self):
        """L'entry point account (<AccountMenu>) NON sta in un ramo
        !isNetwork dell'header."""
        src = self.SHELL.read_text()
        use_at = src.index("<AccountMenu")
        # il ramo condizionale della pill myTrips si CHIUDE prima
        # dell'entry point (l'omino sta fuori dal ramo di fase)
        pill_close = src.index("</Link>", src.index("marketplace.myTrips"))
        assert pill_close < use_at, \
            "l'entry point account deve seguire la pill myTrips"
        between = src[pill_close:use_at]
        assert ")}" in between, \
            "il ramo !isNetwork della pill deve chiudersi prima dell'omino"
        assert "{!isNetwork" not in between and "{isNetwork" not in between, \
            "l'entry point account non deve essere gated dalla fase network"
        # accanto all'hamburger: il bottone menu mobile segue l'entry point
        assert src.index("setMobileNavOpen((o) => !o)") > use_at

    def test_ps4_i18n_x4_senza_passaporto(self):
        import json as _json
        for lang in ("it", "en", "de", "fr"):
            loc = _json.loads((FRONTEND_SRC / "locales" / lang
                               / "landings.json").read_text())
            val = loc["marketplace"].get("accountAria", "")
            assert val, f"{lang}: manca marketplace.accountAria"
            assert "Passaporto" not in val and "—" not in val \
                and "–" not in val, f"{lang}: copy vietato"

    def test_ps4_una_sola_rotta_account_attiva(self):
        app = self.APP.read_text()
        assert app.count('path="/account"') == 1, \
            "/account deve essere registrato UNA volta (AccountPage)"
        assert 'path="/account" element={<AccountPage />}' in app
        # le rotte Aurya continuano a vincere (registrate e distinte)
        for p in ("/account/accedi", "/account/verifica",
                  "/account/nuova-password"):
            assert f'path="{p}"' in app, f"manca la rotta {p}"

    def test_ps4_legacy_redirette_e_player_vivo(self):
        app = self.APP.read_text()
        # redirette alle rotte Aurya
        assert ('path="/account/signup" '
                'element={<Navigate to="/accedi?vista=crea" replace />}') in app
        for p in ("/account/orders", "/account/orders/:orderId",
                  "/account/profile"):
            assert (f'path="{p}" '
                    'element={<Navigate to="/account" replace />}') in app, \
                f"{p}: attesa redirect all'account Aurya"
        # strutturali del player corsi legacy: restano vive
        assert 'path="/account/login" element={<RedirectPreservingQuery to="/accedi" />}' in app
        assert "CustomerCoursePlayerPage" in app \
            and 'path="/account/courses/:enrollment_id"' in app
        assert 'path="/account/forgot-password"' in app \
            and 'path="/account/reset-password"' in app \
            and 'path="/account/verify-email"' in app
        # il vecchio portale ordini/profilo non e' piu' importato
        for dead in ("CustomerOrdersPage", "CustomerOrderDetailPageNew",
                     "CustomerProfilePage", "CustomerSignupPage"):
            assert dead not in app, f"import morto: {dead}"

    def test_ps4_nessun_nuovo_passaporto(self):
        shell = self.SHELL.read_text()
        assert "Passaporto" not in shell
        # App.js: resta solo il commento storico P3 (nessuna new entry)
        assert self.APP.read_text().count("Passaporto") <= 1


class TestPotaturaPs5:
    """PS5 (30/7/2026) — consolidamento GDPR operatore
    (docs/POTATURA_STORE_PIANO_2026-07.md, onda PS5).

    L'operatore NON scrive privacy: documenti Aurya + informativa
    autogenerata multilingua + le sue condizioni. L'editor custom
    (MerchantLegalDialog) resta raggiungibile SOLO dal mondo legacy
    (/stores, /newsletter-forms); gli endpoint storefront legal
    accettano ?lang= e espongono binding_locale; i dati anagrafici
    correnti dello store vincono sui template_vars stantii; il DPA
    art. 28 e' in superficie in SalesConditionsCard.
    """

    CARD = (FRONTEND_SRC / "features" / "settings" / "sections"
            / "SalesConditionsCard.jsx")

    def test_ps5_storefront_privacy_multilingua(self):
        """masseria-demo (org demo, nessun legal custom PUBBLICATO,
        binding EN da storefront_languages) risponde nella lingua
        richiesta: autogen x4."""
        base = f"{BASE_URL}/api/legal/storefront/masseria-demo/privacy"
        r_en = requests.get(base, params={"lang": "en"}, timeout=10)
        assert r_en.status_code == 200
        d_en = r_en.json()
        assert d_en["display_locale"] == "en"
        assert "Data Controller" in d_en["content"]
        r_it = requests.get(base, params={"lang": "it"}, timeout=10)
        d_it = r_it.json()
        assert d_it["display_locale"] == "it"
        assert "Titolare del trattamento" in d_it["content"]
        # binding_locale sempre presente e uguale nelle due risposte
        assert d_en["binding_locale"] == d_it["binding_locale"]
        assert d_it["binding_locale"] in ("it", "en", "de", "fr")
        # lang invalido → default (comportamento pre-PS5)
        r_bad = requests.get(base, params={"lang": "xx"}, timeout=10)
        d_bad = r_bad.json()
        assert d_bad["locale_requested"] is None
        assert d_bad["display_locale"] == d_bad["binding_locale"]

    def test_ps5_dati_titolare_correnti_vincono(self):
        """La precedenza e' invertita SOLO sui campi identitari: i dati
        correnti dello store doc battono i template_vars stantii; i
        flag di raccolta restano dai template_vars."""
        from routers.legal import _build_autogen_template_vars
        store = {
            "name": "Store Vero",
            "contact_email": "vero@example.com",
            "country": "Italia",
            "fulfillment_modes": [],
            "merchant_legal_template_vars": {
                "merchant_name": "test",
                "merchant_email": "dav@gmail.com",
                "merchant_country": "iitallia",
                "store_name": "test",
                "store_country": "iitallia",
                "collects_phone": True,
                "platform_name": "afianco",
                "platform_controller_email": "davide@afianco.ch",
            },
        }
        v = _build_autogen_template_vars(store)
        assert v.merchant_name == "Store Vero"
        assert v.merchant_email == "vero@example.com"
        assert v.merchant_country == "Italia"
        assert v.store_name == "Store Vero"
        assert v.store_country == "Italia"
        # i flag non identitari restano dai template_vars salvati
        assert v.collects_phone is True
        # platform_*: sempre il brand corrente, mai i valori salvati
        assert "afianco" not in v.platform_name.lower()
        assert "afianco" not in v.platform_controller_email.lower()
        # fallback: campo corrente vuoto → template_vars come riserva
        store_no_email = {**store, "contact_email": None}
        assert _build_autogen_template_vars(
            store_no_email).merchant_email == "dav@gmail.com"

    def test_ps5_template_vars_default_senza_afianco(self):
        """I default piattaforma leggono core/brand.py (Aurya)."""
        from services.merchant_legal_template_service import TemplateVars
        dump = TemplateVars().model_dump()
        for key, val in dump.items():
            assert "afianco" not in str(val).lower(), f"{key}: {val}"
        assert dump["platform_name"] == "Aurya"

    def test_ps5_templates_senza_boilerplate_lingua(self):
        """Niente 'fa fede la versione italiana' hardcoded nei
        template: la lingua di riferimento e' binding_locale dinamico
        (riga renderizzata da StorefrontLegalPage)."""
        from services.merchant_legal_template_service import (
            list_template_files,
        )
        files = list_template_files()
        assert len(files) == 8, "matrice template 2 doc x 4 lingue"
        for path in files:
            text = path.read_text(encoding="utf-8").lower()
            for bad in ("legally binding", "verbindliche",
                        "prévaut", "legalmente vincolante",
                        "afianco"):
                assert bad not in text, f"{path.name}: '{bad}'"

    def test_ps5_card_senza_editor_custom(self):
        """SalesConditionsCard: editor custom congelato (resta solo nel
        mondo legacy /stores e /newsletter-forms), informativa autogen
        come riga semplice, mini-form titolare, riga DPA."""
        card = self.CARD.read_text()
        assert "MerchantLegalDialog" not in card, \
            "l'editor custom non deve essere raggiungibile da Impostazioni"
        assert "owner-data-form" in card and "save-owner-data" in card
        assert "generata automaticamente" in card       # riga informativa
        assert "/privacy" in card                        # link autogen
        assert "dpa-row" in card and "/settings/legal/dpa" in card
        # il mini-form scrive sullo store doc (autogen coerente)
        assert "storesAPI.update(" in card
        assert "contact_email" in card and "country" in card
        # il dialog resta vivo SOLO nel mondo legacy
        for legacy in (("features", "stores", "StoresPage.js"),
                       ("features", "newsletter", "NewsletterPage.js")):
            src = FRONTEND_SRC.joinpath(*legacy).read_text()
            assert "MerchantLegalDialog" in src, \
                f"{legacy[-1]}: il mondo legacy tiene l'editor custom"

    def test_ps5_dpa_raggiungibile(self):
        """Rotta /settings/legal/dpa registrata + endpoint status vivo
        (auth-gated: 401/403 senza token)."""
        app = (FRONTEND_SRC / "App.js").read_text()
        assert 'path="/settings/legal/dpa"' in app
        r = requests.get(f"{BASE_URL}/api/legal/dpa/status", timeout=10)
        assert r.status_code in (401, 403)

    def test_ps5_pagina_legale_lingua_utente(self):
        """StorefrontLegalPage chiede la lingua utente e mostra la riga
        'fa fede' quando la lingua servita differisce dal binding."""
        page = (FRONTEND_SRC / "pages"
                / "StorefrontLegalPage.js").read_text()
        assert "fetcher(slug, userLang || undefined)" in page
        assert "binding_note" in page and "binding-locale-note" in page
        svc = (FRONTEND_SRC / "services" / "legalService.js").read_text()
        assert "fetchStorefrontPrivacy(slug, locale)" in svc
        assert "fetchStorefrontTerms(slug, locale)" in svc


class TestPotaturaPs6:
    """PS6 (30/7/2026) — funnel checkout pertinenti alla superficie di
    partenza (docs/POTATURA_STORE_PIANO_2026-07.md, onda PS6).

    ROTTI: latch del consenso checkout in StoreToProfileRedirect (il
    param ?checkout=1 viene strippato DOPO il mount, la guardia non deve
    rivalutare); recupero lingua nel handoff /p/ → /s/ (catalogo senza
    filtro lingua + toast onesto se manca davvero); /pay/{token} in
    stati non pagabili REINDIRIZZA a una pagina umana, mai piu' JSON
    nudo nelle email. FUORVIANTI: canale ordine dalla superficie reale
    (prop channel, decontaminazione mktp in InlineServiceCheckout,
    timbro condizionato in InlineEventCheckout); cancel/success/
    breadcrumb con copy e CTA oneste.
    """

    APP = FRONTEND_SRC / "App.js"
    SF = FRONTEND_SRC / "features" / "storefront"

    # ── 1. latch: /s/:slug?checkout=1 non rimbalza piu' al profilo ──

    def test_ps6_latch_store_to_profile_redirect(self):
        src = self.APP.read_text()
        assert "function StoreToProfileRedirect" in src
        seg = src.split("function StoreToProfileRedirect")[1][:700]
        # il consenso e' LATCHATO al mount con lo useState-initializer:
        # lo strip del param/state non fa piu' rimbalzare al profilo
        assert "React.useState(() =>" in seg, \
            "manca il latch useState(() => wantsCheckout) nel redirect"
        assert "has('checkout')" in seg and "preloadCart" in seg

    # ── 2. handoff /p/ → /s/: recupero lingua + toast onesto ─────────

    def test_ps6_preload_recupero_lingua(self):
        page = (self.SF / "StorefrontPage.js").read_text()
        # niente piu' bail silenzioso: refetch senza filtro lingua...
        assert "preloadRecoveryRef" in page
        assert "storefrontAPI.getCatalog(slug)" in page
        # ...e toast onesto quando il prodotto manca davvero
        assert "preloadUnavailableInLanguage" in page

    # ── 3. pay-token: mai JSON nudo, sempre redirect umano ───────────

    def test_ps6_pay_token_ignoto_redirect(self):
        r = requests.get(
            f"{BASE_URL}/api/public/pay/token-inesistente-1234567890",
            allow_redirects=False, timeout=10)
        assert r.status_code in (303, 307), r.text
        assert "/s/pay-non-disponibile" in r.headers.get("Location", "")

    def test_ps6_pay_token_non_pagabile_redirect(self):
        """HTTP reale: ordine+schedule fixture con riga in stato non
        pagabile → redirect alla pagina onesta CON lo slug operatore."""
        import uuid as _uuid
        db = self._db()
        store = db.stores.find_one({"slug": "masseria-demo"},
                                   {"id": 1, "organization_id": 1})
        assert store, "store demo masseria-demo assente"
        token = "ps6-guard-" + _uuid.uuid4().hex
        order_id = "ps6-guard-order-" + _uuid.uuid4().hex[:8]
        sched_id = "ps6-guard-sched-" + _uuid.uuid4().hex[:8]
        try:
            db.orders.insert_one({
                "id": order_id,
                "organization_id": store["organization_id"],
                "store_id": store["id"],
                "status": "draft", "total": 10.0,
            })
            db.payment_schedules.insert_one({
                "id": sched_id, "order_id": order_id,
                "organization_id": store["organization_id"],
                "rows": [{"seq": 1, "kind": "balance",
                          "amount_minor": 1000,
                          "status": "suspended",   # fuori da PAYABLE e da paid
                          "pay_token": token}],
            })
            r = requests.get(f"{BASE_URL}/api/public/pay/{token}",
                             allow_redirects=False, timeout=10)
            assert r.status_code in (303, 307), r.text
            loc = r.headers.get("Location", "")
            assert "/s/pay-non-disponibile" in loc
            assert "slug=masseria-demo" in loc, \
                "l'org e' nota: la pagina deve poter offrire 'Torna all'operatore'"
        finally:
            db.payment_schedules.delete_one({"id": sched_id})
            db.orders.delete_one({"id": order_id})

    def test_ps6_pay_page_frontend_registrata(self):
        app = self.APP.read_text()
        assert '"/s/pay-non-disponibile"' in app.replace("'", '"')
        crp = (self.SF / "CheckoutResultPage.js").read_text()
        assert "PayLinkUnavailablePage" in crp
        assert 'to="/account"' in crp        # CTA "Vai al tuo account"
        assert "/o/${slug}" in crp           # CTA "Torna all'operatore"

    # ── 4. canale = superficie reale + decontaminazione mktp ─────────

    def test_ps6_inline_service_decontaminazione(self):
        src = (self.SF / "components" / "checkout"
               / "InlineServiceCheckout.jsx").read_text()
        assert "removeItem('storefront:mktp_ctx')" in src
        assert "removeItem('storefront:mktp_return')" in src
        assert "channel: 'store'" in src

    def test_ps6_channel_prop_in_use_checkout_form(self):
        src = (self.SF / "hooks" / "useCheckoutForm.js").read_text()
        assert "  channel,\n}) {" in src, "il hook accetta la prop channel"
        # prop esplicita vince, fallback legacy al flag di sessione
        assert "channel: channel ||" in src
        assert "storefront:mktp_ctx" in src

    def test_ps6_inline_event_timbro_condizionato(self):
        src = (self.SF / "components" / "checkout"
               / "InlineEventCheckout.jsx").read_text()
        # niente piu' timbro incondizionato: solo in vero contesto mktp
        assert "mktpContext" in src
        assert "if (!mktpContext) return;" in src
        assert "channel: mktpContext ? 'marketplace' : 'store'" in src
        # la landing calcola la provenienza reale e passa la prop
        elp = (self.SF / "EventLandingPage.js").read_text()
        assert "computeMktpContext" in elp
        assert "aurya:nav:prev" in elp
        assert "mktpContext={mktpCtx}" in elp

    # ── 5. cancel page: funnel + copy onesta + niente importo ────────

    def test_ps6_cancel_page_funnel(self):
        crp = (self.SF / "CheckoutResultPage.js").read_text()
        cancel = crp.split("export function CheckoutCancelPage")[1]
        assert "mktp_return" in cancel       # CTA "Riprova: torna al ritiro"
        assert "cancelRetryRetreat" in cancel
        assert "hideAmount" in cancel        # niente totale-ordine spacciato per caparra

    def test_ps6_cancel_copy_onesta_x4(self):
        import json as _json
        for lang in ("it", "en", "de", "fr"):
            loc = _json.loads((FRONTEND_SRC / "locales" / lang
                               / "storefront.json").read_text())
            cr = loc["checkoutResult"]
            desc = cr["cancelDesc"]
            # la vecchia promessa "sarai contattato per procedere" e' via
            assert "contattato" not in desc and "contacted" not in desc \
                and "kontaktiert" not in desc and "contacté" not in desc, \
                f"{lang}: la cancel page non deve promettere ricontatti su un draft"
            for key in ("cancelRetryRetreat", "backToRetreat", "backToHome"):
                assert key in cr, f"{lang}: manca checkoutResult.{key}"
            for key in ("title", "body", "tempTitle", "tempBody",
                        "ctaAccount", "ctaOperator"):
                assert key in cr["payUnavailable"], \
                    f"{lang}: manca payUnavailable.{key}"

    # ── 6. success + breadcrumb: mai label bugiarde ──────────────────

    def test_ps6_success_ritorno_onesto(self):
        crp = (self.SF / "CheckoutResultPage.js").read_text()
        success = crp.split("export function CheckoutSuccessPage")[1] \
                     .split("export function")[0]
        # mktp_return quando esiste, label neutra "Torna alla home" altrimenti
        assert "mktp_return" in success
        assert "backToHome" in success and "backToRetreat" in success

    def test_ps6_breadcrumb_landing_onesto(self):
        elp = (self.SF / "EventLandingPage.js").read_text()
        # fase network: crumb "Aurya" → home, o /esplora-ritiri se anteprima
        assert "sitePhase === 'network'" in elp
        assert "/esplora-ritiri" in elp
        assert "breadcrumbRetreats" in elp

    # ── 9/10. attriti: avviso doppio via, ?checkout=1 con carrello vuoto ──

    def test_ps6_avviso_doppio_pannello_servizio(self):
        form = (self.SF / "components" / "checkout"
                / "CheckoutForm.jsx").read_text()
        assert "inlineServiceSelection" in form
        assert "needsSelection && !inlineServiceSelection" in form
        inline = (self.SF / "components" / "checkout"
                  / "InlineServiceCheckout.jsx").read_text()
        assert "inlineServiceSelection" in inline

    def test_ps6_checkout_param_carrello_vuoto(self):
        page = (self.SF / "StorefrontPage.js").read_text()
        assert "checkoutEmptyCart" in page
        # il param viene strippato anche nel ramo vuoto (stripParam)
        assert "stripParam" in page

    @staticmethod
    def _db():
        """DB del server live (backend/.env), NON il test_db di default."""
        import re as _re
        import pymongo
        env = (BACKEND_DIR / ".env").read_text()
        mongo = _re.search(r'MONGO_URL="?([^"\n]+?)"?\n', env).group(1)
        name = _re.search(r'DB_NAME="?([^"\n]+?)"?\n', env).group(1)
        return pymongo.MongoClient(mongo)[name]


class TestProfiloPv1:
    """PV1 (PROFILO_VERIFICATO_PIANO_2026-07) — foto solide.

    Guardie: MIME map canonica nei chiamanti, filename NON deterministico
    per cover/ritratto/logo (sostituzione mai in cache) + cleanup dei
    vecchi file, HEIC accettato e convertito WebP, limite 2MB ancora
    attivo, helper compressImage presente nelle superfici frontend.
    """

    UPLOADS = BACKEND_DIR / "uploads"

    # ── infrastruttura live (stessi helper dei cicli TW/RS/PN/LM) ────

    _admin_token_cache = None

    @classmethod
    def _admin_headers(cls):
        import pytest
        if cls._admin_token_cache:
            return {"Authorization": f"Bearer {cls._admin_token_cache}"}
        r = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@demo.com", "password": "demo1234"}, timeout=10)
        if r.status_code != 200:
            pytest.skip("demo login unavailable (rate limit?)")
        cls._admin_token_cache = r.json()["access_token"]
        return {"Authorization": f"Bearer {cls._admin_token_cache}"}

    @staticmethod
    def _db():
        import re as _re
        import pymongo
        env = (BACKEND_DIR / ".env").read_text()
        mongo = _re.search(r'MONGO_URL="?([^"\n]+?)"?\n', env).group(1)
        name = _re.search(r'DB_NAME="?([^"\n]+?)"?\n', env).group(1)
        return pymongo.MongoClient(mongo)[name]

    @classmethod
    def _org_id(cls):
        r = requests.get(f"{BASE_URL}/api/organizations/current",
                         headers=cls._admin_headers(), timeout=10)
        assert r.status_code == 200
        return r.json()["id"]

    @staticmethod
    def _png_bytes(size=(900, 500), color=(60, 120, 90)):
        import io
        from PIL import Image
        buf = io.BytesIO()
        Image.new("RGB", size, color).save(buf, format="PNG")
        return buf.getvalue()

    @classmethod
    def _snapshot_local(cls, url):
        """(path, bytes) del file locale dietro un URL /uploads/*, o None."""
        if not url or not str(url).startswith("/uploads/"):
            return None
        path = cls.UPLOADS / str(url)[len("/uploads/"):]
        if path.is_file():
            return path, path.read_bytes()
        return None

    # ── 1. MIME map canonica (il bug "image/jpg") ────────────────────

    def test_mime_map_no_fstring_ext(self):
        """Nessun chiamante costruisce più il MIME con f"image/{ext}"
        (produceva "image/jpg" → ottimizzazione WebP saltata)."""
        routers = BACKEND_DIR / "routers"
        offenders = []
        for p in routers.glob("*.py"):
            if 'f"image/{ext' in p.read_text():
                offenders.append(p.name)
        assert offenders == [], f"MIME da estensione grezza in: {offenders}"

    def test_mime_map_helper_used(self):
        storage = (BACKEND_DIR / "services" / "object_storage.py").read_text()
        assert "def content_type_for_ext" in storage
        assert '".jpg": "image/jpeg"' in storage
        for router in ("organizations.py", "products.py",
                       "event_occurrences.py"):
            src = (BACKEND_DIR / "routers" / router).read_text()
            assert "content_type_for_ext" in src, router

    # ── 2. filename non deterministico + cleanup (bug sostituzione) ──

    def test_random_suffix_in_source(self):
        """Cover, ritratto e logo org usano il pattern gallery
        {org_id}-{uuid4[:10]}{ext}: URL nuovo a ogni upload."""
        src = (BACKEND_DIR / "routers" / "organizations.py").read_text()
        occurrences = src.count('-{uuid.uuid4().hex[:10]}{ext}')
        assert occurrences >= 4, occurrences  # logo, cover, ritratto, gallery
        storage = (BACKEND_DIR / "services" / "object_storage.py").read_text()
        assert "def delete_public_uploads" in storage
        assert "delete_objects" in storage  # simmetria S3 del cleanup

    def test_cover_replacement_new_url_old_file_gone(self):
        """Due upload cover consecutivi → URL DIVERSI e il vecchio file
        rimosso da uploads/ (riproduzione HTTP del bug sostituzione)."""
        import pytest
        headers = self._admin_headers()
        org_id = self._org_id()
        db = self._db()
        org = db.organizations.find_one({"id": org_id},
                                        {"public_profile.cover_url": 1})
        original_url = ((org or {}).get("public_profile")
                        or {}).get("cover_url")
        original_file = self._snapshot_local(original_url)
        try:
            urls = []
            for color in ((200, 30, 30), (30, 30, 200)):
                r = requests.post(
                    f"{BASE_URL}/api/organizations/current/public-profile/cover",
                    headers=headers, timeout=20,
                    files={"file": ("guardia-pv1.png",
                                    self._png_bytes(color=color),
                                    "image/png")})
                if r.status_code == 429:
                    pytest.skip("rate limit cover raggiunto (rerun <1min)")
                assert r.status_code == 200, r.text
                urls.append(r.json()["cover_url"])
            first, second = urls
            assert first != second, "URL cover identico: sostituzione in cache"
            assert f"{org_id}-" in first.rsplit("/", 1)[-1]
            first_local = self.UPLOADS / first[len("/uploads/"):]
            second_local = self.UPLOADS / second[len("/uploads/"):]
            assert not first_local.exists(), "vecchio file cover non rimosso"
            assert second_local.exists(), "nuovo file cover mancante"
        finally:
            # ripristino com'era: file originale (se locale) + puntatore DB
            for p in (self.UPLOADS / "profile-covers").glob(f"{org_id}*"):
                try:
                    p.unlink()
                except OSError:
                    pass
            if original_file:
                path, data = original_file
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
            db.organizations.update_one(
                {"id": org_id},
                {"$set": {"public_profile.cover_url": original_url}})

    # ── 3. HEIC accettato e convertito WebP ──────────────────────────

    def test_heic_upload_converted_to_webp(self):
        import io
        import pytest
        from PIL import Image
        heif = pytest.importorskip("pillow_heif")
        heif.register_heif_opener()
        headers = self._admin_headers()
        org_id = self._org_id()
        db = self._db()
        org = db.organizations.find_one({"id": org_id},
                                        {"public_profile.portrait_url": 1})
        original_url = ((org or {}).get("public_profile")
                        or {}).get("portrait_url")
        original_file = self._snapshot_local(original_url)
        buf = io.BytesIO()
        Image.new("RGB", (2200, 1300), (90, 60, 120)).save(buf, format="HEIF")
        try:
            r = requests.post(
                f"{BASE_URL}/api/organizations/current/public-profile/portrait",
                headers=headers, timeout=20,
                files={"file": ("iphone-pv1.heic", buf.getvalue(),
                                "image/heic")})
            if r.status_code == 429:
                pytest.skip("rate limit portrait raggiunto (rerun <1min)")
            assert r.status_code == 200, r.text
            url = r.json()["portrait_url"]
            assert url.endswith(".webp"), url  # convertito, mai .heic servito
            saved = self.UPLOADS / url[len("/uploads/"):]
            assert saved.is_file()
            img = Image.open(io.BytesIO(saved.read_bytes()))
            assert img.format == "WEBP"
            assert max(img.size) <= 1600  # resize S6 applicato
        finally:
            for p in (self.UPLOADS / "profile-portraits").glob(f"{org_id}*"):
                try:
                    p.unlink()
                except OSError:
                    pass
            if original_file:
                path, data = original_file
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
            db.organizations.update_one(
                {"id": org_id},
                {"$set": {"public_profile.portrait_url": original_url}})

    def test_heic_in_whitelists(self):
        for router in ("organizations.py", "products.py",
                       "event_occurrences.py"):
            src = (BACKEND_DIR / "routers" / router).read_text()
            assert '".heic"' in src, router
            assert "image/heic" in src, router
        req = (BACKEND_DIR / "requirements.txt").read_text()
        assert "pillow-heif" in req
        storage = (BACKEND_DIR / "services" / "object_storage.py").read_text()
        assert "register_heif_opener" in storage
        assert "image/heic" in storage  # in _OPTIMIZE_TYPES
        assert "_FORCE_CONVERT_TYPES" in storage  # heic mai servito com'è

    # ── 4. cintura 2MB ancora attiva ─────────────────────────────────

    def test_oversize_still_rejected(self):
        import pytest
        headers = self._admin_headers()
        blob = b"\x00" * (2 * 1024 * 1024 + 1)
        r = requests.post(
            f"{BASE_URL}/api/organizations/current/public-profile/cover",
            headers=headers, timeout=20,
            files={"file": ("troppo-grande.png", blob, "image/png")})
        if r.status_code == 429:
            pytest.skip("rate limit cover raggiunto (rerun <1min)")
        assert r.status_code == 400
        assert "2MB" in r.json()["detail"]

    # ── 5. messaggio 429 leggibile ───────────────────────────────────

    def test_429_has_detail_key(self):
        """L'handler slowapi custom risponde con detail E error, così
        il toast del frontend mostra il messaggio vero."""
        server = (BACKEND_DIR / "server.py").read_text()
        assert "_rate_limit_handler" in server
        assert '"detail": msg' in server
        assert '"error": msg' in server

    # ── 6. helper compressImage nelle superfici frontend ─────────────

    def test_compress_helper_exists(self):
        helper = (FRONTEND_SRC / "lib" / "compressImage.js").read_text()
        assert "createImageBitmap" in helper
        assert "imageOrientation" in helper           # EXIF from-image
        assert "'image/webp'" in helper
        assert "'image/jpeg'" in helper               # fallback Safari
        assert "return file" in helper                # fail-safe: mai bloccare

    def test_compress_helper_wired_in_api_wrappers(self):
        """La compressione avviene PRIMA della FormData in TUTTI i
        wrapper API di upload immagine (quindi in ogni superficie)."""
        for api_file in ("products.js", "orgBranding.js", "stores.js",
                         "storeSettings.js", "eventOccurrences.js"):
            src = (FRONTEND_SRC / "api" / api_file).read_text()
            assert "compressImage" in src, api_file
            assert "await compressImage(file)" in src, api_file

    def test_profile_page_compresses_and_resets(self):
        page = (FRONTEND_SRC / "features" / "settings"
                / "PublicProfilePage.js").read_text()
        assert "compressImage" in page
        assert page.count("e.target.value = ''") >= 3  # cover+ritratto+gallery
        assert 'accept="image/*"' in page
        assert "max 2MB" not in page                   # copy percepito rimosso
        assert "optimizing" in page                    # stato "Ottimizzo la foto"

    def test_image_inputs_accept_any_image(self):
        surfaces = (
            "features/settings/PublicProfilePage.js",
            "features/stores/components/OrgBrandingDialog.jsx",
            "features/stores/StoresPage.js",
            "features/services/ServiceWizard.js",
            "features/listino/ListinoPage.js",
            "features/physicals/PhysicalWizard.js",
            "features/digitals/DigitalWizard.js",
            "features/reservations/ReservationWizard.js",
            "features/events/EventWizard.js",
            "features/events/EventDashboardPage.js",
        )
        for rel in surfaces:
            src = (FRONTEND_SRC / Path(rel)).read_text()
            assert 'accept="image/*"' in src, rel
            assert 'accept=".jpg' not in src, rel


class TestProfiloPv2:
    """PV2 (PROFILO_VERIFICATO_PIANO_2026-07) — intervista al system admin.

    Guardie: PUT admin (bozza → pubblica → verified_at timbrato UNA volta
    → spubblica → azzerato), 403 per non-sysadmin, video YouTube
    normalizzato all'URL canonico (422 per host estranei), PATCH
    self-service che IGNORA interview, pubblico che espone l'intervista
    SOLO se pubblicata (has_interview coerente), interview_status in
    _org_summary, editor operatore sostituito dal pannello informativo.
    """

    _sys_token_cache = None
    _op_token_cache = None

    # ── infrastruttura live (stessi helper di TestProfiloPv1) ────────

    @classmethod
    def _sys_headers(cls):
        import pytest
        if cls._sys_token_cache:
            return {"Authorization": f"Bearer {cls._sys_token_cache}"}
        for pwd in ("DevLocal1234!", "demo1234"):
            r = requests.post(f"{BASE_URL}/api/auth/login", json={
                "email": "sysadmin@demo.com", "password": pwd}, timeout=10)
            if r.status_code == 200:
                cls._sys_token_cache = r.json()["access_token"]
                return {"Authorization": f"Bearer {cls._sys_token_cache}"}
        pytest.skip("sysadmin login unavailable (rate limit?)")

    @classmethod
    def _op_headers(cls):
        import pytest
        if cls._op_token_cache:
            return {"Authorization": f"Bearer {cls._op_token_cache}"}
        r = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@demo.com", "password": "demo1234"}, timeout=10)
        if r.status_code != 200:
            pytest.skip("demo login unavailable (rate limit?)")
        cls._op_token_cache = r.json()["access_token"]
        return {"Authorization": f"Bearer {cls._op_token_cache}"}

    @staticmethod
    def _db():
        import re as _re
        import pymongo
        env = (BACKEND_DIR / ".env").read_text()
        mongo = _re.search(r'MONGO_URL="?([^"\n]+?)"?\n', env).group(1)
        name = _re.search(r'DB_NAME="?([^"\n]+?)"?\n', env).group(1)
        return pymongo.MongoClient(mongo)[name]

    @classmethod
    def _org_id(cls):
        r = requests.get(f"{BASE_URL}/api/organizations/current",
                         headers=cls._op_headers(), timeout=10)
        assert r.status_code == 200
        return r.json()["id"]

    # SW5 — interview_quote entra nello snapshot: e' parte del blocco
    # intervista, e senza di lui il ripristino lascerebbe in giro le
    # citazioni di prova
    _IV_FIELDS = ("interview", "interview_video_url", "interview_quote",
                  "interview_published", "interview_verified_at")

    @classmethod
    def _snapshot_interview(cls, db, org_id):
        """{campo: valore} SOLO dei campi presenti (assenti → da $unset)."""
        org = db.organizations.find_one({"id": org_id},
                                        {"public_profile": 1}) or {}
        pp = org.get("public_profile") or {}
        return {f: pp[f] for f in cls._IV_FIELDS if f in pp}

    @classmethod
    def _restore_interview(cls, db, org_id, snap):
        ops = {}
        sets = {f"public_profile.{f}": v for f, v in snap.items()}
        unsets = {f"public_profile.{f}": ""
                  for f in cls._IV_FIELDS if f not in snap}
        if sets:
            ops["$set"] = sets
        if unsets:
            ops["$unset"] = unsets
        if ops:
            db.organizations.update_one({"id": org_id}, ops)

    UA = {"User-Agent": "Mozilla/5.0 (Macintosh) Chrome/126 Safari/537.36"}

    def _public_profile(self):
        r = requests.get(f"{BASE_URL}/api/public/operator/masseria-demo",
                         headers=self.UA, timeout=10)
        assert r.status_code == 200, r.text
        return r.json()

    def _member_row(self):
        r = requests.get(f"{BASE_URL}/api/public/network/members",
                         headers=self.UA, timeout=10)
        assert r.status_code == 200
        rows = [m for m in r.json()["items"] if m["slug"] == "masseria-demo"]
        return rows[0] if rows else None

    def _summary_row(self, org_id):
        r = requests.get(f"{BASE_URL}/api/admin/organizations",
                         headers=self._sys_headers(),
                         params={"limit": 200}, timeout=10)
        assert r.status_code == 200
        rows = [o for o in r.json()["items"] if o["id"] == org_id]
        assert rows, "org demo assente dalla lista admin"
        return rows[0]

    # ── 1. ciclo di vita completo: bozza → pubblica → spubblica ─────

    def test_admin_put_full_lifecycle(self):
        sys_h = self._sys_headers()
        org_id = self._org_id()
        db = self._db()
        snap = self._snapshot_interview(db, org_id)
        url = f"{BASE_URL}/api/admin/organizations/{org_id}/interview"
        body = {"items": [{"question": "Guardia PV2?",
                           "answer": "Risposta integrale PV2."}],
                "video_url": "https://youtu.be/dQw4w9WgXcQ",
                "published": False}
        try:
            # BOZZA: salvata ma invisibile al pubblico
            r = requests.put(url, headers=sys_h, json=body, timeout=10)
            assert r.status_code == 200, r.text
            assert r.json()["verified_at"] is None
            pub = self._public_profile()
            assert pub["interview"] == []
            assert pub["interview_video_url"] is None
            assert pub["interview_verified_at"] is None
            assert self._summary_row(org_id)["interview_status"] == "draft"
            member = self._member_row()
            if member:
                assert member["has_interview"] is False

            # GET admin: l'editor ricarica lo stato (bozza inclusa)
            r = requests.get(url, headers=sys_h, timeout=10)
            assert r.status_code == 200
            state = r.json()
            assert state["items"][0]["question"] == "Guardia PV2?"
            assert state["published"] is False

            # PUBBLICA: verified_at timbrato
            body["published"] = True
            r = requests.put(url, headers=sys_h, json=body, timeout=10)
            assert r.status_code == 200, r.text
            first_stamp = r.json()["verified_at"]
            assert first_stamp

            # ri-salvataggio da pubblicata: il timbro NON cambia
            r = requests.put(url, headers=sys_h, json=body, timeout=10)
            assert r.json()["verified_at"] == first_stamp

            # pubblico: intervista + video canonico + timbro
            pub = self._public_profile()
            assert pub["interview"][0]["question"] == "Guardia PV2?"
            assert (pub["interview_video_url"]
                    == "https://www.youtube.com/watch?v=dQw4w9WgXcQ")
            assert pub["interview_verified_at"] == first_stamp
            assert self._summary_row(org_id)["interview_status"] == "published"
            member = self._member_row()
            if member:
                assert member["has_interview"] is True

            # SPUBBLICA: timbro azzerato, pubblico ripulito
            body["published"] = False
            r = requests.put(url, headers=sys_h, json=body, timeout=10)
            assert r.status_code == 200
            assert r.json()["verified_at"] is None
            pub = self._public_profile()
            assert pub["interview"] == []
            assert pub["interview_verified_at"] is None
            member = self._member_row()
            if member:
                assert member["has_interview"] is False

            # RIMUOVI: items vuoti → stato none in lista
            r = requests.put(url, headers=sys_h, timeout=10,
                             json={"items": [], "video_url": None,
                                   "published": False})
            assert r.status_code == 200
            assert self._summary_row(org_id)["interview_status"] == "none"
        finally:
            self._restore_interview(db, org_id, snap)

    # ── 2. solo il system admin ──────────────────────────────────────

    def test_put_requires_system_admin(self):
        op_h = self._op_headers()
        org_id = self._org_id()
        url = f"{BASE_URL}/api/admin/organizations/{org_id}/interview"
        r = requests.put(url, headers=op_h, timeout=10,
                         json={"items": [], "published": False})
        assert r.status_code == 403
        r = requests.get(url, headers=op_h, timeout=10)
        assert r.status_code == 403

    # ── 3. video: normalizzazione YouTube + rifiuto host estranei ────

    def test_video_url_normalized_and_rejected(self):
        sys_h = self._sys_headers()
        org_id = self._org_id()
        db = self._db()
        snap = self._snapshot_interview(db, org_id)
        url = f"{BASE_URL}/api/admin/organizations/{org_id}/interview"
        canonical = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        accepted = (
            "https://youtu.be/dQw4w9WgXcQ",
            "https://youtu.be/dQw4w9WgXcQ?t=42",
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ&ab_channel=x",
            "https://m.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://www.youtube.com/shorts/dQw4w9WgXcQ",
        )
        rejected = (
            "https://vimeo.com/123456789",
            "https://example.com/watch?v=dQw4w9WgXcQ",
            "https://youtube.com.evil.io/watch?v=dQw4w9WgXcQ",
            "non-un-url",
        )
        try:
            for raw in accepted:
                r = requests.put(url, headers=sys_h, timeout=10,
                                 json={"items": [], "video_url": raw,
                                       "published": False})
                assert r.status_code == 200, (raw, r.text)
                assert r.json()["video_url"] == canonical, raw
            for raw in rejected:
                r = requests.put(url, headers=sys_h, timeout=10,
                                 json={"items": [], "video_url": raw,
                                       "published": False})
                assert r.status_code == 422, (raw, r.status_code)
        finally:
            self._restore_interview(db, org_id, snap)

    # ── 4. regole di validazione ereditate dal vecchio PATCH ─────────

    def test_items_rules_max12_lengths_empty_dropped(self):
        sys_h = self._sys_headers()
        org_id = self._org_id()
        db = self._db()
        snap = self._snapshot_interview(db, org_id)
        url = f"{BASE_URL}/api/admin/organizations/{org_id}/interview"
        items = [{"question": f"D{i}? " + "q" * 300,
                  "answer": "a" * 3000} for i in range(15)]
        items.append({"question": "Solo domanda", "answer": "  "})
        try:
            r = requests.put(url, headers=sys_h, timeout=10,
                             json={"items": items, "published": False})
            assert r.status_code == 200, r.text
            saved = r.json()["items"]
            assert len(saved) == 12                      # max 12, vuote fuori
            assert all(len(qa["question"]) <= 200 for qa in saved)
            assert all(len(qa["answer"]) <= 2500 for qa in saved)
        finally:
            self._restore_interview(db, org_id, snap)

    # ── 5. il self-service è chiuso (retrocompat: ignorato, no errore) ─

    def test_patch_self_service_ignores_interview(self):
        op_h = self._op_headers()
        org_id = self._org_id()
        db = self._db()
        snap = self._snapshot_interview(db, org_id)
        before = snap.get("interview")
        # payload con SOLO interview: il caso peggiore del client vecchio
        r = requests.patch(
            f"{BASE_URL}/api/organizations/current/public-profile",
            headers=op_h, timeout=15,
            json={"interview": [{"question": "INTRUSO",
                                 "answer": "Self-service chiuso."}]})
        assert r.status_code == 200, r.text          # niente 4xx: ignorato
        org = db.organizations.find_one({"id": org_id}, {"public_profile": 1})
        after = (org.get("public_profile") or {}).get("interview")
        assert after == before, "il PATCH self-service ha scritto interview"

    def test_patch_source_no_longer_writes_interview(self):
        src = (BACKEND_DIR / "routers" / "organizations.py").read_text()
        assert 'updates["public_profile.interview"]' not in src

    # ── 6. superfici frontend: editor via, pannello invito al suo posto ─

    def test_operator_editor_replaced_by_invite_panel(self):
        page = (FRONTEND_SRC / "features" / "settings"
                / "PublicProfilePage.js").read_text()
        assert "payload.interview" not in page        # non si invia più
        assert "interview-invite-panel" in page       # pannello informativo
        assert "interviewInviteTitle" in page
        # CS3 (13/8): il mailto usa BRAND_EMAIL (non hardcodato) e
        # accanto c'e' l'indirizzo in chiaro, leggibile e copiabile.
        assert "mailto:${BRAND_EMAIL}" in page        # CTA contatto
        assert "set('interview'" not in page          # niente campi compilabili

    def test_admin_tab_registered(self):
        tab = (FRONTEND_SRC / "features" / "admin"
               / "InterviewsTab.js").read_text()
        assert "getOrgInterview" in tab
        assert "setOrgInterview" in tab
        assert "ytVideoId" in tab                     # anteprima ID video
        admin_page = (FRONTEND_SRC / "features" / "admin"
                      / "AdminPage.js").read_text()
        assert "InterviewsTab" in admin_page
        assert 'value="interviews"' in admin_page

    def test_invite_panel_i18n_x4(self):
        import json
        for lang in ("it", "en", "de", "fr"):
            data = json.loads(
                (FRONTEND_SRC / "locales" / lang / "settings.json")
                .read_text())
            pp = data.get("publicProfile") or {}
            for key in ("interviewInviteTitle", "interviewInviteBody",
                        "interviewInviteCta"):
                assert pp.get(key), f"{lang}: publicProfile.{key} mancante"
            # le chiavi del vecchio editor self-service sono sparite
            assert "interviewAdd" not in pp, lang

    # ── 7. interview_status esposto dalla lista admin ────────────────

    def test_org_summary_has_interview_status(self):
        r = requests.get(f"{BASE_URL}/api/admin/organizations",
                         headers=self._sys_headers(),
                         params={"limit": 50}, timeout=10)
        assert r.status_code == 200
        items = r.json()["items"]
        assert items
        for row in items:
            assert row["interview_status"] in ("none", "draft", "published")
            assert "interview_verified_at" in row


class TestProfiloPv3:
    """PV3 (PROFILO_VERIFICATO_PIANO_2026-07) — pagina intervista pubblica.

    Guardie: rotta /o/:slug/intervista registrata, embed SOLO
    youtube-nocookie (mai youtube.com/embed in tutto il frontend),
    redirect al profilo quando l'intervista non è pubblicata, testata
    identitaria CONDIVISA col profilo (stesso componente, slot badge
    PV4 previsto), blocco compatto con bottone sul profilo, link nuovo
    dalla pagina rete, fascia "Continua a scoprire", i18n x4.
    """

    PAGE = FRONTEND_SRC / "features" / "storefront" / "OperatorInterviewPage.js"
    PROFILE = FRONTEND_SRC / "features" / "storefront" / "OperatorProfilePage.js"
    HEADER = (FRONTEND_SRC / "features" / "storefront" / "components"
              / "OperatorIdentityHeader.jsx")

    # ── 1. rotta registrata dentro le rotte /o/ ──────────────────────

    def test_route_registered(self):
        app = (FRONTEND_SRC / "App.js").read_text()
        assert 'path="/o/:org_slug/intervista"' in app
        assert "OperatorInterviewPage" in app

    # ── 2. embed: youtube-nocookie e MAI youtube.com/embed diretto ───

    def test_embed_nocookie_only(self):
        page = self.PAGE.read_text()
        assert "youtube-nocookie.com/embed" in page
        for f in FRONTEND_SRC.rglob("*.js"):
            src = f.read_text()
            assert "www.youtube.com/embed" not in src, f
            assert "//youtube.com/embed" not in src, f

    def test_video_lazy_titled_with_poster(self):
        page = self.PAGE.read_text()
        assert 'loading="lazy"' in page
        assert "interviewVideoTitle" in page        # title accessibile
        assert "i.ytimg.com/vi/" in page            # poster/facade pre-play

    # ── 3. non pubblicata → redirect al profilo, nessun 404 crudo ────

    def test_redirect_when_not_published(self):
        page = self.PAGE.read_text()
        assert "if (notFound || !data || !published)" in page
        assert "Navigate" in page and "replace" in page
        assert "data.interview.length > 0" in page   # pubblicata = lista piena

    # ── 4. continuità: testata identitaria condivisa + slot badge PV4 ─

    def test_identity_header_shared(self):
        assert "OperatorIdentityHeader" in self.PAGE.read_text()
        assert "OperatorIdentityHeader" in self.PROFILE.read_text()
        header = self.HEADER.read_text()
        assert "verified-badge-slot" in header       # slot badge PV4 previsto
        assert "bg-black/45" in header               # stesso overlay cover

    def test_back_to_profile_always_visible(self):
        page = self.PAGE.read_text()
        assert "back-to-profile" in page
        assert "sticky" in page

    def test_continue_band_links_profile_anchors(self):
        page = self.PAGE.read_text()
        assert "continue-band" in page
        for anchor in ("#ritiri", "#listino", "#recensioni"):
            assert anchor in page, anchor

    # ── 5. profilo: blocco compatto con anteprima e bottone ──────────

    def test_profile_compact_block(self):
        profile = self.PROFILE.read_text()
        assert "interview-teaser" in profile
        assert "read-interview-cta" in profile
        assert "line-clamp-3" in profile             # anteprima con ellissi
        assert "data.interview[0].question" in profile
        assert "data.interview.map" not in profile   # niente Q&A integrali inline

    # ── 6. la pagina rete linka la pagina nuova ──────────────────────

    def test_network_page_links_interview_page(self):
        page = (FRONTEND_SRC / "features" / "network"
                / "NetworkOperatorsPage.js").read_text()
        assert "/intervista" in page

    # ── 7. i18n x4 ───────────────────────────────────────────────────

    def test_i18n_x4(self):
        import json
        for lang in ("it", "en", "de", "fr"):
            data = json.loads(
                (FRONTEND_SRC / "locales" / lang / "landings.json")
                .read_text())
            op = data.get("operator") or {}
            for key in ("interviewReadCta", "interviewBackToProfile",
                        "interviewByAurya", "interviewContinueTitle",
                        "interviewSeoTitle", "interviewVideoTitle"):
                assert op.get(key), f"{lang}: operator.{key} mancante"

    # ── 8. il prerender crawler risponde 200 anche sul path nuovo ────

    def test_seo_shell_serves_interview_path(self):
        r = requests.get(f"{BASE_URL}/__seo/o/masseria-demo/intervista",
                         timeout=10)
        assert r.status_code == 200


class TestProfiloPv4:
    """PV4 (PROFILO_VERIFICATO_PIANO_2026-07) — badge "Verificato Aurya".

    Guardie: /public/operators espone verified (bool, additivo) coerente
    con interview_verified_at (pubblica → True, spubblica → False, mai
    per i campioni), /network/members idem; componente VerifiedAuryaBadge
    con le due varianti (on-photo blur / on-light ori brand) e il glifo
    del logo esistente; montato e CONDIZIONATO nei 3 posti (hero
    condiviso profilo+intervista, card marketplace + quick view, card
    rete); ordine Verificato PRIMA di In evidenza; tooltip i18n x4.
    """

    UA = {"User-Agent": "Mozilla/5.0 (Macintosh) Chrome/126 Safari/537.36"}

    BADGE = FRONTEND_SRC / "components" / "VerifiedAuryaBadge.jsx"
    HEADER = (FRONTEND_SRC / "features" / "storefront" / "components"
              / "OperatorIdentityHeader.jsx")
    INDEX = FRONTEND_SRC / "features" / "storefront" / "OperatorsIndexPage.js"
    NETWORK = FRONTEND_SRC / "features" / "network" / "NetworkOperatorsPage.js"

    # ── helper: le due liste pubbliche, con verified sempre bool ─────

    def _operators_items(self):
        # preview=1: in pre-lancio la vetrina mostra i campioni (PL8),
        # l'anteprima /esplora-operatori mostra gli operatori VERI
        r = requests.get(f"{BASE_URL}/api/public/operators",
                         params={"preview": 1}, headers=self.UA, timeout=10)
        assert r.status_code == 200, r.text
        items = r.json()["items"]
        for i in items:
            assert isinstance(i.get("verified"), bool), i.get("org_slug")
        return items

    def _members_items(self):
        r = requests.get(f"{BASE_URL}/api/public/network/members",
                         headers=self.UA, timeout=10)
        assert r.status_code == 200, r.text
        items = r.json()["items"]
        for i in items:
            assert isinstance(i.get("verified"), bool), i.get("slug")
        return items

    def _demo_rows(self, org_name):
        ops = [i for i in self._operators_items() if i["name"] == org_name]
        mem = [i for i in self._members_items()
               if i["slug"] == "masseria-demo"]
        return (ops[0] if ops else None), (mem[0] if mem else None)

    # ── 1. HTTP: verified segue pubblica/spubblica dell'intervista ───

    def test_verified_follows_interview_publication(self):
        P = TestProfiloPv2
        sys_h = P._sys_headers()
        org_id = P._org_id()
        r = requests.get(f"{BASE_URL}/api/organizations/current",
                         headers=P._op_headers(), timeout=10)
        assert r.status_code == 200
        org_name = r.json()["name"]
        db = P._db()
        snap = P._snapshot_interview(db, org_id)
        url = f"{BASE_URL}/api/admin/organizations/{org_id}/interview"
        body = {"items": [{"question": "Guardia PV4?",
                           "answer": "Il badge segue il timbro."}],
                "published": True}
        try:
            # PUBBLICA → verified True su entrambe le liste
            r = requests.put(url, headers=sys_h, json=body, timeout=10)
            assert r.status_code == 200, r.text
            assert r.json()["verified_at"]
            op_row, mem_row = self._demo_rows(org_name)
            assert op_row is not None, "org demo assente da /public/operators"
            assert op_row["verified"] is True
            # nessun campione porta mai il sigillo (identita' redatta)
            for i in self._operators_items():
                if i.get("sample"):
                    assert i["verified"] is False
            if mem_row:
                assert mem_row["verified"] is True

            # SPUBBLICA → timbro azzerato, verified False ovunque
            body["published"] = False
            r = requests.put(url, headers=sys_h, json=body, timeout=10)
            assert r.status_code == 200
            assert r.json()["verified_at"] is None
            op_row, mem_row = self._demo_rows(org_name)
            assert op_row is not None
            assert op_row["verified"] is False
            if mem_row:
                assert mem_row["verified"] is False
        finally:
            P._restore_interview(db, org_id, snap)

    # ── 2. componente: varianti, glifo del logo, accessibilita' ─────

    def test_badge_component_variants_and_glyph(self):
        comp = self.BADGE.read_text()
        assert "on-photo" in comp and "on-light" in comp
        assert "backdrop-blur" in comp                # variante su foto
        assert "#8a7440" in comp and "#cbb578" in comp  # ori brand
        assert "logo-aurya" in comp                   # glifo dal logo, no asset nuovi
        assert "aria-label" in comp and "title=" in comp
        assert "verifiedBadge.tooltip" in comp

    # ── 3. montato e CONDIZIONATO nei 3 posti ────────────────────────

    def test_badge_mounted_and_gated_everywhere(self):
        header = self.HEADER.read_text()
        assert "VerifiedAuryaBadge" in header
        assert "data.interview_verified_at &&" in header   # mai incondizionato
        assert "verified-badge-slot" in header

        index = self.INDEX.read_text()
        assert "VerifiedAuryaBadge" in index
        assert "op.verified &&" in index
        # anche nella vista rapida (due montaggi nella card)
        assert index.count("<VerifiedAuryaBadge") >= 2

        # SW5 — la card della rete non e' piu' scritta a mano dentro la
        # pagina: /operatori monta PersonCard del kit editoriale, ed e'
        # LI' che vive il sigillo. L'invariante non cambia (il badge c'e'
        # e non e' mai incondizionato), cambia il file che lo dice.
        network = self.NETWORK.read_text()
        assert "PersonCard" in network, \
            "/operatori non monta piu' la scheda persona del kit"
        card = (FRONTEND_SRC / "components" / "editorial"
                / "PersonCard.jsx").read_text()
        assert "VerifiedAuryaBadge" in card
        assert "verified && (" in card

    # ── 4. ordine: Verificato PRIMA di In evidenza (hero e card) ─────

    def test_verified_before_featured(self):
        header = self.HEADER.read_text()
        assert (header.index("VerifiedAuryaBadge", header.index("return"))
                < header.index("calendar.featured"))
        index = self.INDEX.read_text()
        card = index[index.index("function OperatorCard"):]
        assert card.index("<VerifiedAuryaBadge") < card.index("calendar.featured")

    # ── 5. tooltip e testi i18n x4 ───────────────────────────────────

    def test_badge_i18n_x4(self):
        import json
        for lang in ("it", "en", "de", "fr"):
            data = json.loads(
                (FRONTEND_SRC / "locales" / lang / "landings.json")
                .read_text())
            vb = data.get("verifiedBadge") or {}
            for key in ("label", "short", "tooltip"):
                assert vb.get(key), f"{lang}: verifiedBadge.{key} mancante"


class TestProfiloPv5:
    """PV5 (PROFILO_VERIFICATO_PIANO_2026-07) — la landing /p/ "esiste"
    solo se ha contenuto; nessun servizio rimanda mai al vecchio store.

    Guardie: has_landing nel listino pubblico coerente col contenuto
    (racconto lungo o cover dedicata → True, senza → False, additivo);
    legacy_commerce (bool, additivo) sul payload landing /p/; gate del
    link "Vedi dettagli" su has_landing (OperatorProfilePage + link
    gemello in InlineServiceCheckout); landing servizi nel mondo snello
    dentro il guscio del profilo (MarketplaceShell, breadcrumb, back a
    /o/, niente StorefrontHeader/banner carrello store); CTA acquisto →
    checkout inline del profilo (persistCart + navigate /o/ con state
    expandService, consumato da OperatorProfilePage); handoff legacy
    /p/→/s/ INTATTO dietro il ramo profileWorld; i18n x4.
    """

    UA = {"User-Agent": "Mozilla/5.0 (Macintosh) Chrome/126 Safari/537.36"}

    PROFILE = FRONTEND_SRC / "features" / "storefront" / "OperatorProfilePage.js"
    LANDING = FRONTEND_SRC / "features" / "storefront" / "ProductLandingPage.js"
    INLINE = (FRONTEND_SRC / "features" / "storefront" / "components"
              / "checkout" / "InlineServiceCheckout.jsx")

    # ── helper: riga di listino pubblica del servizio demo ───────────

    def _listino_row(self, slug="seduta-di-reiki"):
        r = requests.get(f"{BASE_URL}/api/public/operator/masseria-demo",
                         headers=self.UA, timeout=10)
        assert r.status_code == 200, r.text
        rows = [x for x in r.json().get("listino", []) if x.get("slug") == slug]
        assert rows, f"servizio {slug} assente dal listino demo"
        return rows[0]

    def _demo_service(self, headers, slug="seduta-di-reiki"):
        r = requests.get(f"{BASE_URL}/api/products", headers=headers,
                         params={"limit": 200}, timeout=10)
        assert r.status_code == 200, r.text
        prods = r.json()
        rows = [p for p in prods if p.get("slug") == slug]
        assert rows, f"prodotto {slug} non trovato"
        return rows[0]

    def _patch_meta(self, headers, product, **fields):
        meta = {**(product.get("metadata") or {}), **fields}
        r = requests.patch(f"{BASE_URL}/api/products/{product['id']}",
                           headers=headers, json={"metadata": meta}, timeout=10)
        assert r.status_code == 200, r.text

    # ── 1. HTTP: has_landing segue il contenuto della landing ────────

    def test_has_landing_follows_content(self):
        op_h = TestProfiloPv2._op_headers()
        prod = self._demo_service(op_h)
        orig_meta = prod.get("metadata") or {}
        snap = {"long_description": orig_meta.get("long_description"),
                "cover_image_url": orig_meta.get("cover_image_url")}
        try:
            # senza contenuto → False (baseline demo)
            self._patch_meta(op_h, prod, long_description=None,
                             cover_image_url=None)
            assert self._listino_row()["has_landing"] is False
            # racconto lungo → True
            self._patch_meta(op_h, prod,
                             long_description="Racconto PV5", cover_image_url=None)
            assert self._listino_row()["has_landing"] is True
            # solo cover dedicata → True
            self._patch_meta(op_h, prod, long_description=None,
                             cover_image_url="/uploads/x.webp")
            assert self._listino_row()["has_landing"] is True
            # spazi bianchi non contano come contenuto
            self._patch_meta(op_h, prod, long_description="   ",
                             cover_image_url=None)
            assert self._listino_row()["has_landing"] is False
        finally:
            self._patch_meta(op_h, prod, **snap)

    def test_has_landing_bool_on_every_row(self):
        r = requests.get(f"{BASE_URL}/api/public/operator/masseria-demo",
                         headers=self.UA, timeout=10)
        assert r.status_code == 200
        for row in r.json().get("listino", []):
            assert isinstance(row.get("has_landing"), bool), row.get("slug")

    # ── 2. HTTP: la landing /p/ dichiara il mondo dell'org ───────────

    def test_landing_payload_exposes_legacy_commerce(self):
        r = requests.get(
            f"{BASE_URL}/api/public/products/masseria-demo/seduta-di-reiki",
            headers=self.UA, timeout=10)
        assert r.status_code == 200, r.text
        body = r.json()
        assert isinstance(body.get("legacy_commerce"), bool)
        # l'org demo e' nel mondo snello: il guscio profilo deve valere
        assert body["legacy_commerce"] is False

    # ── 3. scan: gate del bottone "Vedi dettagli" ────────────────────

    def test_view_details_gated_by_has_landing(self):
        page = self.PROFILE.read_text()
        assert "row.slug && row.has_landing && (" in page, \
            "il link Vedi dettagli deve essere condizionato a has_landing"
        inline = self.INLINE.read_text()
        assert "row.slug && row.has_landing && (" in inline, \
            "il link gemello nel pannello inline deve avere lo stesso gate"

    # ── 4. scan: landing servizi nel mondo snello senza varchi /s/ ───

    def test_service_landing_lives_in_profile_world(self):
        page = self.LANDING.read_text()
        # il mondo decide il guscio: flag org + tipo servizio
        assert "!data.legacy_commerce" in page
        assert "item_type === 'service'" in page
        # guscio profilo: shell marketplace + breadcrumb + back a /o/
        assert "MarketplaceShell" in page
        assert 'data-testid="landing-profile-breadcrumb"' in page
        assert "/o/${orgSlug}#listino" in page
        # niente header store né banner carrello store nel mondo snello
        assert "{!profileWorld && (\n        <StorefrontHeader" in page
        assert "{!profileWorld && cartCount > 0 && (" in page
        # il not-found riporta al profilo, non alla vetrina
        assert 'to={`/o/${orgSlug}`}' in page

    # ── 5. scan: CTA acquisto → checkout inline del profilo ──────────

    def test_cta_deep_links_profile_inline_checkout(self):
        page = self.LANDING.read_text()
        # la selezione persiste nello snapshot che idrata il profilo
        assert "persistCart(orgSlug, next)" in page
        assert ("navigate(`/o/${orgSlug}`, { state: { expandService: "
                "product.id } })") in page
        # il profilo consuma lo state: riga espansa + scroll all'ancora
        profile = self.PROFILE.read_text()
        assert "navState?.expandService" in profile
        assert "setExpandedService(row.product_id || row.slug || row.name)" \
            in profile
        assert 'id={`servizio-${row.slug || row.product_id}`}' in profile

    # ── 6. scan: handoff legacy /p/→/s/ intatto dietro il ramo ───────

    def test_legacy_handoff_intact_behind_flag(self):
        page = self.LANDING.read_text()
        # il ramo profileWorld esce PRIMA dell'handoff storico
        idx_guard = page.find("if (profileWorld) {")
        idx_handoff = page.find("navigate(`/s/${orgSlug}`, { state: { preloadCart } })")
        assert idx_guard != -1 and idx_handoff != -1
        assert idx_guard < idx_handoff, \
            "l'handoff legacy deve restare, gato dal ramo profileWorld"
        # il toast legacy col deep-link ?checkout=1 resta per lo store
        assert "navigate(`/s/${orgSlug}?checkout=1`)" in page

    # ── 7. i18n x4 ───────────────────────────────────────────────────

    def test_pv5_i18n_x4(self):
        import json as _json
        for lang in ("it", "en", "de", "fr"):
            data = _json.loads(
                (FRONTEND_SRC / "locales" / lang / "landings.json")
                .read_text())
            assert (data.get("operator") or {}).get("viewDetails"), \
                f"{lang}: operator.viewDetails mancante"
            assert (data.get("product") or {}).get("backToProfile"), \
                f"{lang}: product.backToProfile mancante"


class TestProfiloPv6:
    """PV6 (PROFILO_VERIFICATO_PIANO_2026-07) — consolidamento della
    prenotazione inline sul profilo /o/: calendario solido + percorso
    a passi.

    Guardie: fix del calendario ("oggi" non e' piu' un chip pieno color
    accent — prima restava arancio anche selezionando un altro giorno —
    e il giorno attivo ha UNA sola fonte di verita', controllata dal
    parent); stepper a 3 passi con riassunti collassati, Modifica e
    Conferma; deep-link PV5 che atterra al passo giusto (slot gia'
    scelto → passo 3); caso senza calendario INTATTO (passo unico);
    i18n x4 per le etichette nuove.
    """

    INLINE = (FRONTEND_SRC / "features" / "storefront" / "components"
              / "checkout" / "InlineServiceCheckout.jsx")
    PICKER = (FRONTEND_SRC / "features" / "storefront" / "components"
              / "AvailabilityCalendarSlotPicker.js")
    DAYPICKER = (FRONTEND_SRC / "features" / "storefront" / "components"
                 / "AvailabilityDayPicker.js")

    # ── 1. scan: "oggi" e' un segno discreto, mai un chip pieno ──────

    def test_today_marker_is_not_a_filled_chip(self):
        picker = self.DAYPICKER.read_text()
        # l'override day_today esiste e NON riusa il riempimento accent
        # del default shadcn (bg-accent pieno = il bug dei due giorni
        # "selezionati"); il segno discreto e' testo accent + puntino.
        assert "day_today:" in picker
        assert "'relative font-semibold text-accent '" in picker
        assert "bg-accent text-accent-foreground" not in picker
        # quando oggi E' selezionato vince la livrea selezione
        assert "aria-selected:text-primary-foreground" in picker

    # ── 2. scan: giorno attivo con UNA sola fonte di verita' ─────────

    def test_active_day_single_source_of_truth(self):
        picker = self.PICKER.read_text()
        # modalita' controllata additiva: il parent detiene il giorno
        assert "const isControlled = controlledActiveDate !== undefined;" \
            in picker
        assert ("const activeDate = isControlled ? controlledActiveDate "
                ": internalActiveDate;") in picker
        # niente auto-selezione del primo giorno quando controllato
        assert "if (isControlled) return;" in picker
        # il picker sa rendere solo calendario o solo orari (passi)
        assert "showCalendar = true" in picker
        assert "showSlots = true" in picker
        # il checkout inline usa DAVVERO la modalita' controllata
        inline = self.INLINE.read_text()
        assert "const [pickedDay, setPickedDay] = useState(null);" in inline
        assert inline.count("activeDate={pickedDay}") == 2
        assert inline.count("onActiveDateChange={handlePickDay}") == 2

    # ── 3. scan: stepper a 3 passi con Modifica e Conferma ───────────

    def test_stepper_three_steps_with_edit(self):
        inline = self.INLINE.read_text()
        assert 'data-testid="booking-steps"' in inline
        for n in (1, 2, 3):
            assert f"stepShell({n}, (" in inline, f"passo {n} assente"
        # riassunto collassato + Modifica per tornare indietro
        assert "booking-step-edit-" in inline
        assert "booking-step-" in inline and "-summary" in inline
        assert "steps.edit" in inline
        # Conferma per riavanzare quando non si cambia nulla
        assert 'data-testid="booking-step-confirm"' in inline
        assert "steps.confirm" in inline
        # cambio giorno → lo slot scelto decade (mai selezioni ambigue)
        assert "if (realSlot && realSlot.date !== iso) dropSlot();" in inline

    # ── 4. scan: deep-link PV5 atterra al passo giusto ───────────────

    def test_deeplink_lands_on_right_step(self):
        inline = self.INLINE.read_text()
        # slot idratato dalla sessione → il giorno del passo 1 e' suo
        assert "if (realSlot?.date) setPickedDay(realSlot.date);" in inline
        # passo derivato: senza giorno 1, senza orario 2, altrimenti 3
        assert ": (!realSlot?.date ? 2 : 3);" in inline
        assert "const currentStep = Math.min(editStep ?? autoStep, autoStep);" \
            in inline

    # ── 5. scan: caso senza calendario INTATTO (passo unico) ─────────

    def test_no_calendar_flow_untouched(self):
        inline = self.INLINE.read_text()
        # il percorso a passi vale SOLO con slot reali
        assert "{hasSlots ? (" in inline
        # il ramo passo-unico conserva opzioni, richiesta libera e form
        assert "customRequest.headingNoSlots" in inline
        assert inline.count("{summaryAndForm}") == 2
        assert inline.count("{optionsBlock}") == 2
        # la richiesta libera parte aperta come sempre in scenario 3
        assert "useState(!hasSlots && allowCustom)" in inline

    # ── 6. i18n x4 ───────────────────────────────────────────────────

    def test_pv6_i18n_x4(self):
        import json as _json
        for lang in ("it", "en", "de", "fr"):
            data = _json.loads(
                (FRONTEND_SRC / "locales" / lang / "landings.json")
                .read_text())
            steps = ((data.get("product") or {}).get("steps") or {})
            for key in ("day", "time", "details", "edit", "confirm"):
                assert steps.get(key), f"{lang}: product.steps.{key} mancante"


class TestProfiloPv7:
    """PV7 (PROFILO_VERIFICATO_PIANO_2026-07) — il patto di
    responsabilita': prima di vendere l'operatore DEVE leggere e
    accettare il suo DPA art. 28 (macchina CG-7 riusata, zero testi
    duplicati).

    Scelte documentate:
      - GATE ALLA CREAZIONE (non alla pubblicazione): nel mondo snello
        la creazione E' la pubblicazione (listino LM1 crea
        is_published=true, wizard RS2 crea+pubblica); le porte di
        pubblicazione sono molte e gate-arle bloccherebbe i contenuti
        GIA' esistenti delle org attive. Porte gateate: POST /products
        (service|event_ticket), POST /products/{id}/duplicate, POST
        /event-occurrences/wizard.
      - FONTE A DUE LIVELLI: stamp durevole merchant_dpa_ack sull'org
        (il gate, senza TTL) + record consent_audit immutabile (la
        prova, TTL 365g). Vedi services/dpa_guard.py.
      - SUITE: helper unico _ensure_dpa_ack con firma marcata via UA,
        rimossa a fine modulo (mai ack d'ufficio permanenti).

    Guardie runtime su ORG DI TEST VERGINE (creata ad hoc nel DB live +
    JWT mintato col secret del server): l'org demo non si tocca.
    """

    PREFIX = "pv7guard"

    # ── infrastruttura: org vergine + token sul server live ──────────

    @classmethod
    def _live_env(cls):
        import re
        env = (BACKEND_DIR / ".env").read_text()
        secret = re.search(
            r'JWT_SECRET_KEY="?([^"\n]+?)"?\n', env).group(1)
        return secret

    @classmethod
    def _make_virgin_org(cls, tag):
        """Org + admin verificato nel DB live, token JWT valido.

        Nessuna firma DPA: e' esattamente lo stato di un operatore
        nuovo che prova a vendere.
        """
        import uuid
        from datetime import datetime, timedelta, timezone
        from jose import jwt as jose_jwt

        db = _pv7_live_db()
        org_id = f"{cls.PREFIX}-org-{tag}-{uuid.uuid4().hex[:8]}"
        user_id = f"{cls.PREFIX}-user-{tag}-{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc)
        db.organizations.insert_one({
            "id": org_id, "name": f"PV7 Guard {tag}",
            "is_active": True, "created_at": now.isoformat(),
        })
        db.users.insert_one({
            "id": user_id, "email": f"{org_id}@example.com",
            "organization_id": org_id, "role": "admin",
            "is_active": True, "email_verified": True,
            "created_at": now.isoformat(),
        })
        token = jose_jwt.encode(
            {"sub": user_id, "org_id": org_id,
             "iat": int(now.timestamp()),
             "exp": now + timedelta(minutes=20)},
            cls._live_env(), algorithm="HS256")
        return org_id, user_id, {"Authorization": f"Bearer {token}"}

    @classmethod
    def _cleanup_org(cls, org_id, user_id):
        db = _pv7_live_db()
        db.products.delete_many({"organization_id": org_id})
        db.event_occurrences.delete_many({"organization_id": org_id})
        db.event_ticket_tiers.delete_many({"organization_id": org_id})
        db.stores.delete_many({"organization_id": org_id})
        db.consent_audit.delete_many({"organization_id": org_id})
        db.users.delete_one({"id": user_id})
        db.organizations.delete_one({"id": org_id})

    @staticmethod
    def _service_payload(name):
        return {"name": name, "item_type": "service",
                "transaction_mode": "request", "is_published": False,
                "unit_price": 30, "price_mode": "fixed"}

    # ── 1. HTTP reale: senza firma la creazione risponde DPA_REQUIRED ─

    def test_pv7_creazione_gated_senza_ack(self):
        org_id, user_id, headers = self._make_virgin_org("gate")
        try:
            # riga di listino (service)
            r = requests.post(f"{BASE_URL}/api/products", headers=headers,
                              json=self._service_payload("PV7 gate svc"),
                              timeout=10)
            assert r.status_code == 409, r.text
            assert r.json()["detail"]["code"] == "DPA_REQUIRED"

            # ritiro (wizard event_ticket) — stessa risposta
            r = requests.post(
                f"{BASE_URL}/api/event-occurrences/wizard",
                headers=headers, timeout=10,
                json={"product": {"name": "PV7 gate ritiro",
                                  "category": "yoga",
                                  "unit_price": 100,
                                  "price_mode": "fixed",
                                  "transaction_mode": "request",
                                  "is_published": False},
                      "occurrence": {"start_at": "2027-10-01T10:00:00",
                                     "status": "draft"},
                      "tiers": []})
            assert r.status_code == 409, r.text
            assert r.json()["detail"]["code"] == "DPA_REQUIRED"

            # nessun prodotto creato
            db = _pv7_live_db()
            assert db.products.count_documents(
                {"organization_id": org_id}) == 0
        finally:
            self._cleanup_org(org_id, user_id)

    # ── 2. HTTP reale: firma → si vende; una volta sola, immutabile ──

    def test_pv7_ack_sblocca_una_volta_per_sempre(self):
        org_id, user_id, headers = self._make_virgin_org("ack")
        try:
            # firma il patto (macchina CG-7)
            r = requests.post(f"{BASE_URL}/api/legal/dpa/acknowledge",
                              headers=headers, json={"locale": "it"},
                              timeout=10)
            assert r.status_code == 200, r.text
            first = r.json()
            assert first["status"] == "acknowledged"

            db = _pv7_live_db()
            # stamp durevole sul doc org (il gate NON dipende dal TTL
            # dell'audit: la firma non "scade")
            org = db.organizations.find_one({"id": org_id})
            stamp = org.get("merchant_dpa_ack")
            assert stamp and stamp["acknowledged_at"] == \
                first["acknowledged_at"]
            assert stamp["user_id"] == user_id
            # audit immutabile scritto (fonte probatoria CG-7)
            assert db.consent_audit.count_documents({
                "organization_id": org_id,
                "document_type": "merchant_dpa",
                "source": "merchant_dpa_acknowledged"}) == 1

            # la creazione ora passa — e non viene MAI piu' richiesta
            r = requests.post(f"{BASE_URL}/api/products", headers=headers,
                              json=self._service_payload("PV7 ack svc"),
                              timeout=10)
            assert r.status_code in (200, 201), r.text

            # ri-firma → idempotente: timestamp originale, zero righe
            # audit duplicate (l'acknowledgement e' una-volta-sola)
            r = requests.post(f"{BASE_URL}/api/legal/dpa/acknowledge",
                              headers=headers, json={"locale": "en"},
                              timeout=10)
            assert r.status_code == 200
            again = r.json()
            assert again["status"] == "already_acknowledged"
            assert again["acknowledged_at"] == first["acknowledged_at"]
            assert db.consent_audit.count_documents({
                "organization_id": org_id,
                "document_type": "merchant_dpa"}) == 1

            # /dpa/status riflette lo stesso stato del gate
            st = requests.get(f"{BASE_URL}/api/legal/dpa/status",
                              headers=headers, timeout=10).json()
            assert st["acknowledged"] is True
            assert st["acknowledged_at"] == first["acknowledged_at"]
        finally:
            self._cleanup_org(org_id, user_id)

    # ── 3. HTTP reale: contenuti esistenti MAI bloccati ──────────────

    def test_pv7_contenuti_esistenti_non_bloccati(self):
        """Org esistente (pre-gate) con prodotti gia' in catalogo:
        modifiche e toggle di pubblicazione restano liberi — il gate
        vale SOLO per le nuove creazioni (che mostrano il patto:
        corretto e voluto)."""
        import uuid
        from datetime import datetime, timezone
        org_id, user_id, headers = self._make_virgin_org("legacy")
        db = _pv7_live_db()
        pid = f"{self.PREFIX}-prod-{uuid.uuid4().hex[:8]}"
        try:
            now = datetime.now(timezone.utc).isoformat()
            db.products.insert_one({
                "id": pid, "organization_id": org_id,
                "name": "PV7 legacy svc", "item_type": "service",
                "transaction_mode": "request", "price_mode": "fixed",
                "unit_price": 25.0, "is_active": True,
                "is_published": False, "slug": pid,
                "created_at": now, "updated_at": now,
            })
            # update (nome) senza firma: 200 — la modifica del gia'
            # esistente non e' mai gateata
            r = requests.patch(f"{BASE_URL}/api/products/{pid}",
                             headers=headers,
                             json={"name": "PV7 legacy svc v2"},
                             timeout=10)
            assert r.status_code == 200, r.text
        finally:
            self._cleanup_org(org_id, user_id)

    # ── 4. scan: gate sulle porte giuste, enforcement riusabile ──────

    def test_pv7_gate_backend_sulle_porte_di_creazione(self):
        guard = (BACKEND_DIR / "services" / "dpa_guard.py").read_text()
        assert "DPA_REQUIRED" in guard
        assert "async def require_dpa_acknowledged" in guard
        # fonte a due livelli: stamp org durevole + audit (TTL 365g)
        assert "merchant_dpa_ack" in guard
        assert "find_latest_for_org_dpa" in guard

        products = (BACKEND_DIR / "routers" / "products.py").read_text()
        # creazione + duplicate gateate, per i soli tipi vendibili
        assert products.count("require_dpa_acknowledged") >= 2
        assert "SELLABLE_ITEM_TYPES" in products

        wizard = (BACKEND_DIR / "routers"
                  / "event_occurrences.py").read_text()
        assert "require_dpa_acknowledged" in wizard

        # l'acknowledge scrive lo stamp durevole (il gate non scade col
        # TTL dell'audit) e resta idempotente via get_dpa_ack
        legal = (BACKEND_DIR / "routers" / "legal.py").read_text()
        assert '"$set": {"merchant_dpa_ack"' in legal
        assert "get_dpa_ack" in legal

    # ── 5. scan: frontend — dialog, intercettazione, ripresa azione ──

    def test_pv7_frontend_dialog_e_intercettazione(self):
        dialog = (FRONTEND_SRC / "components" / "legal"
                  / "DpaPactDialog.jsx").read_text()
        # sintesi + testo DPA riusato + informativa autogenerata + firma
        assert 'data-testid="dpa-pact-summary"' in dialog
        assert "dpaAPI.get(" in dialog          # GET /legal/dpa (CG-7)
        assert "dpaAPI.acknowledge(" in dialog  # POST /acknowledge
        assert "/privacy" in dialog             # link informativa autogen
        assert 'data-testid="dpa-pact-checkbox"' in dialog
        assert 'data-testid="dpa-pact-accept"' in dialog
        assert "onAccepted" in dialog           # ripresa azione in sospeso

        # stato condiviso: UNA GET /dpa/status, cache modulo + listener
        hook = (FRONTEND_SRC / "hooks" / "useDpaStatus.js").read_text()
        assert "let cache" in hook and "listeners" in hook
        assert "markDpaAcknowledged" in hook

        # listino: gate PRIMA della creazione + intercetta DPA_REQUIRED
        listino = (FRONTEND_SRC / "features" / "listino"
                   / "ListinoPage.js").read_text()
        assert "useDpaStatus" in listino
        assert "DPA_REQUIRED" in listino
        assert "DpaPactDialog" in listino
        assert "pactPendingRef" in listino      # l'azione riprende da sola

        # wizard ritiri: stesso giro
        wizard = (FRONTEND_SRC / "features" / "events"
                  / "EventWizard.js").read_text()
        assert "useDpaStatus" in wizard
        assert "DPA_REQUIRED" in wizard
        assert "DpaPactDialog" in wizard

    # ── 6. scan: banner gated dallo status in /listino e Ritiri ──────

    def test_pv7_banner_listino_e_ritiri(self):
        banner = (FRONTEND_SRC / "components" / "legal"
                  / "DpaPactBanner.jsx").read_text()
        # gated dallo stato condiviso: firmato (o ignoto) → niente rumore
        assert "useDpaStatus" in banner
        assert "if (!known || acknowledged) return null;" in banner
        assert 'data-testid="dpa-pact-banner"' in banner

        listino = (FRONTEND_SRC / "features" / "listino"
                   / "ListinoPage.js").read_text()
        assert "DpaPactBanner" in listino
        events = (FRONTEND_SRC / "features" / "events"
                  / "EventsListPage.js").read_text()
        assert "DpaPactBanner" in events

    # ── 7. i18n x4 ───────────────────────────────────────────────────

    def test_pv7_i18n_x4(self):
        import json as _json
        for lang in ("it", "en", "de", "fr"):
            data = _json.loads(
                (FRONTEND_SRC / "locales" / lang / "legal.json")
                .read_text())
            pact = ((data.get("dpa") or {}).get("pact") or {})
            for key in ("title", "intro", "point1", "point2", "point3",
                        "point4", "checkbox", "accept", "acceptedBadge",
                        "bannerTitle", "bannerBody", "bannerCta"):
                assert pact.get(key), f"{lang}: dpa.pact.{key} mancante"


class TestUtentiUt1:
    """UT1 — tab Utenti (clientela FINALE) nel pannello system admin.

    Guardie: 403 per non-sysadmin su lista e dettaglio; la lista unisce
    account Aurya e guest (ordini senza account) per email con conteggi
    giusti (total_spent SOLO confirmed/completed — coerenza tesoreria
    RF1), join newsletter corretto; filtri e search; dettaglio coerente
    (ordini con operatore, schede CRM, consensi); paginazione con cap
    100. Endpoint di sola lettura: la fixture vive nel DB live e viene
    rimossa a fine classe.
    """

    _sys_token_cache = None
    _op_token_cache = None

    ACC_EMAIL = "ut1-account@test.aurya"
    GUEST_EMAIL = "ut1-guest@test.aurya"
    _ids: dict = {}

    # ── infrastruttura live (stessi helper di TestProfiloPv2) ────────

    @classmethod
    def _sys_headers(cls):
        import pytest
        if cls._sys_token_cache:
            return {"Authorization": f"Bearer {cls._sys_token_cache}"}
        for pwd in ("DevLocal1234!", "demo1234"):
            r = requests.post(f"{BASE_URL}/api/auth/login", json={
                "email": "sysadmin@demo.com", "password": pwd}, timeout=10)
            if r.status_code == 200:
                cls._sys_token_cache = r.json()["access_token"]
                return {"Authorization": f"Bearer {cls._sys_token_cache}"}
        pytest.skip("sysadmin login unavailable (rate limit?)")

    @classmethod
    def _op_headers(cls):
        import pytest
        if cls._op_token_cache:
            return {"Authorization": f"Bearer {cls._op_token_cache}"}
        r = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@demo.com", "password": "demo1234"}, timeout=10)
        if r.status_code != 200:
            pytest.skip("demo login unavailable (rate limit?)")
        cls._op_token_cache = r.json()["access_token"]
        return {"Authorization": f"Bearer {cls._op_token_cache}"}

    @staticmethod
    def _db():
        import re as _re
        import pymongo
        env = (BACKEND_DIR / ".env").read_text()
        mongo = _re.search(r'MONGO_URL="?([^"\n]+?)"?\n', env).group(1)
        name = _re.search(r'DB_NAME="?([^"\n]+?)"?\n', env).group(1)
        return pymongo.MongoClient(mongo)[name]

    # ── fixture: 1 account (2 ordini, 1 confermato) + 1 guest ────────

    @classmethod
    def setup_class(cls):
        import uuid
        from datetime import datetime, timezone
        db = cls._db()
        cls._teardown_docs(db)  # residui di run precedenti
        org = db.users.find_one({"email": "admin@demo.com"},
                                {"organization_id": 1})
        assert org and org.get("organization_id"), "org demo assente"
        org_id = org["organization_id"]
        cls._ids["org_id"] = org_id
        cls._ids["org_name"] = (db.organizations.find_one(
            {"id": org_id}, {"name": 1}) or {}).get("name")
        now = datetime.now(timezone.utc).isoformat()

        acc_id = str(uuid.uuid4())
        db.platform_accounts.insert_one({
            "id": acc_id, "email": cls.ACC_EMAIL, "name": "UT1 Account",
            "email_verified": True, "is_active": True,
            "created_at": now, "last_login_at": now,
            "aurya_legal": {"terms_version": "vtest",
                            "privacy_version": "vtest",
                            "accepted_at": now, "source": "checkout",
                            "locale": "it"},
        })
        cls._ids["account_id"] = acc_id

        cust_acc = str(uuid.uuid4())
        cust_guest = str(uuid.uuid4())
        # NW4 — il consenso marketing vive nei TIMESTAMP (accepted/
        # revoked), non nel vecchio flag booleano che nessuno scrive:
        # la fixture parla la lingua vera del checkout.
        db.customers.insert_many([
            {"id": cust_acc, "organization_id": org_id,
             "email": cls.ACC_EMAIL, "name": "UT1 Account",
             "accepted_marketing_at": now, "marketing_revoked_at": None,
             "created_at": now},
            {"id": cust_guest, "organization_id": org_id,
             "email": cls.GUEST_EMAIL, "name": "UT1 Guest",
             "accepted_marketing_at": None, "created_at": now},
        ])

        order_ids = [str(uuid.uuid4()) for _ in range(3)]
        db.orders.insert_many([
            # account: confermato 100 + draft 50 → spent 100, count 2
            {"id": order_ids[0], "organization_id": org_id,
             "customer_id": cust_acc, "platform_account_id": acc_id,
             "status": "confirmed", "total": 100.0, "currency": "EUR",
             "sales_channel": "marketplace", "order_number": None,
             "created_at": now, "items": []},
            {"id": order_ids[1], "organization_id": org_id,
             "customer_id": cust_acc, "platform_account_id": acc_id,
             "status": "draft", "total": 50.0, "currency": "EUR",
             "sales_channel": "store", "order_number": None,
             "created_at": now, "items": []},
            # guest: confermato 80 → riga Ospite
            {"id": order_ids[2], "organization_id": org_id,
             "customer_id": cust_guest,
             "status": "confirmed", "total": 80.0, "currency": "EUR",
             "sales_channel": "store", "order_number": None,
             "created_at": now, "items": []},
        ])
        cls._ids["order_ids"] = order_ids

        db.aurya_subscribers.insert_one({
            "email": cls.ACC_EMAIL, "status": "confirmed",
            "source": "ut1-guard", "created_at": now, "confirmed_at": now,
        })

    @classmethod
    def _teardown_docs(cls, db):
        emails = [cls.ACC_EMAIL, cls.GUEST_EMAIL]
        db.platform_accounts.delete_many({"email": {"$in": emails}})
        db.aurya_subscribers.delete_many({"email": {"$in": emails}})
        cust_ids = [c["id"] for c in
                    db.customers.find({"email": {"$in": emails}}, {"id": 1})]
        db.customers.delete_many({"email": {"$in": emails}})
        if cust_ids:
            db.orders.delete_many({"customer_id": {"$in": cust_ids}})

    @classmethod
    def teardown_class(cls):
        try:
            cls._teardown_docs(cls._db())
        except Exception:
            pass  # cleanup best-effort

    def _list(self, **params):
        r = requests.get(f"{BASE_URL}/api/admin/platform/users",
                         headers=self._sys_headers(),
                         params={"search": "ut1-", "page_size": 50,
                                 **params},
                         timeout=15)
        assert r.status_code == 200, r.text
        return r.json()

    # ── 1. perimetro: solo il system admin entra ─────────────────────

    def test_403_non_sysadmin(self):
        op = self._op_headers()
        r = requests.get(f"{BASE_URL}/api/admin/platform/users",
                         headers=op, timeout=10)
        assert r.status_code == 403
        r = requests.get(f"{BASE_URL}/api/admin/platform/users/detail",
                         headers=op, params={"email": self.ACC_EMAIL},
                         timeout=10)
        assert r.status_code == 403

    # ── 2. lista: account + guest, conteggi e join newsletter ────────

    def test_lista_account_e_guest(self):
        data = self._list()
        rows = {i["email"]: i for i in data["items"]}
        assert self.ACC_EMAIL in rows and self.GUEST_EMAIL in rows

        acc = rows[self.ACC_EMAIL]
        assert acc["type"] == "account"
        assert acc["email_verified"] is True
        assert acc["newsletter_status"] == "confirmed"   # join corretto
        assert acc["orders_count"] == 2
        assert acc["confirmed_orders"] == 1
        # RF1: il draft da 50 NON conta nello speso
        assert acc["total_spent"] == 100.0
        assert self._ids["org_name"] in acc["operators"]
        assert acc["operators_count"] == 1
        assert acc["marketing_opted_in"] is True
        assert acc["aurya_accepted_at"]                  # consenso Aurya
        assert acc["last_order_at"]

        guest = rows[self.GUEST_EMAIL]
        assert guest["type"] == "guest"
        assert guest["email_verified"] is False
        assert guest["newsletter_status"] is None
        assert guest["orders_count"] == 1
        assert guest["total_spent"] == 80.0
        assert self._ids["org_name"] in guest["operators"]

        # le StatCard sono globali e contano anche la fixture
        assert data["stats"]["users_total"] >= 2
        assert data["stats"]["with_orders"] >= 2

    # ── 3. filtri e search ───────────────────────────────────────────

    def test_filtri_e_search(self):
        emails = lambda d: {i["email"] for i in d["items"]}  # noqa: E731
        assert emails(self._list(guests_only=True)) == {self.GUEST_EMAIL}
        assert emails(self._list(accounts_only=True)) == {self.ACC_EMAIL}
        assert emails(self._list(newsletter=True)) == {self.ACC_EMAIL}
        assert emails(self._list(verified=True)) == {self.ACC_EMAIL}
        both = emails(self._list(has_orders=True))
        assert {self.ACC_EMAIL, self.GUEST_EMAIL} <= both
        # search per nome (non solo email)
        by_name = self._list(search="UT1 Guest")
        assert emails(by_name) == {self.GUEST_EMAIL}

    # ── 4. dettaglio coerente ────────────────────────────────────────

    def test_detail_account(self):
        r = requests.get(f"{BASE_URL}/api/admin/platform/users/detail",
                         headers=self._sys_headers(),
                         params={"email": self.ACC_EMAIL}, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["type"] == "account"
        assert d["account"]["id"] == self._ids["account_id"]
        # MAI segreti nell'anagrafica admin
        assert "password_hash" not in (d["account"] or {})
        assert d["orders_count"] == 2
        assert d["total_spent"] == 100.0
        assert all(o["operator_name"] == self._ids["org_name"]
                   for o in d["orders"])
        assert {o["status"] for o in d["orders"]} == {"confirmed", "draft"}
        assert len(d["customers"]) == 1
        assert d["customers"][0]["marketing_opted_in"] is True
        assert d["newsletter"]["status"] == "confirmed"
        assert d["consents"]["aurya_legal"]["accepted_at"]

    def test_detail_guest(self):
        r = requests.get(f"{BASE_URL}/api/admin/platform/users/detail",
                         headers=self._sys_headers(),
                         params={"email": self.GUEST_EMAIL}, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["type"] == "guest"
        assert d["account"] is None
        assert d["orders_count"] == 1
        assert d["total_spent"] == 80.0

    def test_detail_sconosciuto_404(self):
        r = requests.get(f"{BASE_URL}/api/admin/platform/users/detail",
                         headers=self._sys_headers(),
                         params={"email": "ut1-nessuno@test.aurya"},
                         timeout=15)
        assert r.status_code == 404

    # ── 5. paginazione: cap 100 e pagine coerenti ────────────────────

    def test_paginazione(self):
        r = requests.get(f"{BASE_URL}/api/admin/platform/users",
                         headers=self._sys_headers(),
                         params={"page_size": 500}, timeout=15)
        assert r.status_code == 422  # cap 100 imposto dallo schema

        p1 = self._list(page_size=1, page=1, sort="spent")
        p2 = self._list(page_size=1, page=2, sort="spent")
        assert p1["total"] == 2 and p2["total"] == 2
        assert len(p1["items"]) == 1 and len(p2["items"]) == 1
        # spent desc: prima l'account (100), poi il guest (80)
        assert p1["items"][0]["email"] == self.ACC_EMAIL
        assert p2["items"][0]["email"] == self.GUEST_EMAIL


class TestLoginRegia:
    """LR1 (31/7) riscritta dal ciclo ID (20/8): la regia NON e' piu'
    «due login» ma UNA porta (/accedi) che decide il mondo dal server.
    Il menu dell'omino da sloggato offre un solo accesso; i vecchi
    soccorsi incrociati sono spariti perche' non c'e' piu' niente da
    incrociare. Esci rimuove il token piattaforma E aurya_nl_token.
    I flussi di autenticazione (password, OTP, magic link) NON
    cambiano: cambia solo chi risponde (POST /api/auth/entra).
    """

    SHELL = (FRONTEND_SRC / "features" / "storefront" / "components"
             / "MarketplaceShell.jsx")
    ACCOUNT_LOGIN = (FRONTEND_SRC / "features" / "account"
                     / "AccountLoginPage.js")
    OPERATOR_LOGIN = FRONTEND_SRC / "pages" / "AuthPages.js"

    # ── 1. il menu dell'omino: due sezioni, le voci giuste ───────────

    def test_lr1_menu_due_sezioni_etichettate(self):
        src = self.SHELL.read_text()
        # sezione utente
        assert "marketplace.accountMenuUser" in src \
            and "'Il tuo account Aurya'" in src, \
            "manca l'etichetta della sezione utente"
        # sezione operatori (dopo un separatore). LC8 — l'etichetta e'
        # quella OF3: "professionisti del benessere", non "operatori"
        # (la parola scelta dal founder per tutto il sito).
        assert "marketplace.accountMenuOperators" in src \
            and "'Per i professionisti del benessere'" in src, \
            "manca l'etichetta della sezione operatori"
        assert "DropdownMenuSeparator" in src, \
            "le due sezioni vanno separate (desktop)"

    def test_lr1_voci_utente(self):
        src = self.SHELL.read_text()
        # ID — da sloggato: Accedi + Crea il tuo account → /accedi
        assert "marketplace.signIn" in src, "manca la voce Accedi"
        assert "marketplace.accountMenuCreate" in src \
            and "'Crea il tuo account'" in src, \
            "manca la voce Crea il tuo account"
        # DN2 (21/8) — le destinazioni vivono nel modello unico
        # (lib/cappelli), che veste sia questo menu sia l'omino del
        # mondo scuro; qui restano le traduzioni.
        assert "vociAccount" in src, "il menu non usa il modello unico"
        modello = (FRONTEND_SRC / "lib" / "cappelli.js").read_text()
        assert "'/accedi'" in modello and "'/accedi?vista=crea'" in modello
        assert "'/account/accedi'" not in modello and "'/account/accedi'" not in src, \
            "il menu punta ancora alla porta vecchia"
        # da loggato: Il mio account → /account + Esci
        assert "marketplace.accountMenuMy" in src \
            and "'Il mio account'" in src, "manca la voce Il mio account"
        assert "marketplace.accountMenuLogout" in src \
            and "'Esci'" in src, "manca la voce Esci"

    def test_lr1_voci_operatori(self):
        src = self.SHELL.read_text()
        # ID — nel MENU dell'omino «Area professionisti» NON esiste
        # piu' (una voce doppia rifarebbe il bivio); nei footer resta
        # come destinazione, ma sulla porta unica
        menu = src.split("const operatorLinks")[1].split("];")[0]
        assert "operatorLogin" not in menu, \
            "e' tornata la voce Area professionisti nel menu"
        assert 'to="/login"' not in src, \
            "un link della shell punta ancora alla porta vecchia"
        # Lavora con Aurya → operatorTo (stessa logica del link testuale:
        # /entra-nella-rete in fase network, /inizia in marketplace)
        assert "marketplace.accountMenuWork" in src \
            and "'Lavora con Aurya'" in src, \
            "manca la voce Lavora con Aurya"
        assert "operatorTo={operatorTo}" in src, \
            "Lavora con Aurya deve seguire la fase (operatorTo)"
        assert "'/entra-nella-rete'" in src and "'/inizia'" in src

    def test_lr1_dropdown_desktop_sheet_mobile(self):
        src = self.SHELL.read_text()
        assert "DropdownMenuContent" in src, "desktop: dropdown ancorato"
        assert "SheetContent" in src and 'side="bottom"' in src, \
            "mobile: sheet dal basso"

    # ── 2. Esci: rimuove ENTRAMBI i token, pallino spento ────────────

    def test_lr1_logout_rimuove_entrambi_i_token(self):
        src = self.SHELL.read_text()
        assert "localStorage.removeItem(PLATFORM_TOKEN_KEY)" in src, \
            "Esci deve rimuovere il token piattaforma"
        assert "scordaProva()" in src, \
            "Esci deve scordare la prova del cerchio (subscriber token)"
        # il pallino si spegne senza reload (stato con setter)
        assert "setHasPlatformToken(false)" in src

    # ── 3. il link testuale professionisti resta nell'header ─────────

    def test_lr1_link_testuale_operatori_resta(self):
        """LC8 — il founder (2/8) ha sostituito la domanda ('Sei un
        operatore?') con una destinazione ('Per i professionisti'):
        il DISPOSITIVO da difendere e' che nell'header resti un link
        testuale al funnel professionisti, che segue la fase
        (operatorTo: /entra-nella-rete in rete, /inizia in
        marketplace)."""
        src = self.SHELL.read_text()
        assert "marketplace.forProfessionals" in src \
            and "'Per i professionisti'" in src, \
            "il link testuale professionisti dell'header deve restare"
        assert "const operatorTo = isNetwork" in src, \
            "il link deve seguire la fase (operatorTo)"

    # ── 4. link di soccorso incrociati nelle due login ───────────────

    def test_lr1_soccorso_su_login_utente(self):
        """ID — sulla porta unica il soccorso «sei un operatore?» non
        ha piu' senso (stessa porta): resta solo l'invito per chi lo
        spazio non ce l'ha ancora."""
        src = self.ACCOUNT_LOGIN.read_text()
        assert 'data-testid="operator-rescue-link"' in src
        assert 'to="/login"' not in src, \
            "la porta unica rimanda ancora alla porta vecchia"
        assert 'to="/entra-nella-rete"' in src

    def test_lr1_soccorso_su_login_operatori(self):
        src = self.OPERATOR_LOGIN.read_text()
        assert 'data-testid="aurya-rescue-link"' in src
        assert 'to="/account/accedi"' in src, \
            "il soccorso deve portare al login utente Aurya"
        assert "login.aurya_hint" in src and "login.aurya_link" in src

    # ── 5. i form di autenticazione NON si toccano ───────────────────

    def test_lr1_form_utente_intoccati(self):
        # ID — il form password parla con la porta unica; le strade
        # senza password restano sui flussi di piattaforma.
        # NL1 — la registrazione e' anch'essa senza password (magic link).
        src = self.ACCOUNT_LOGIN.read_text()
        for marker in ('data-testid="password-login-form"',
                       "'/auth/entra'",
                       "'/platform/auth/magic-link'",
                       "'/platform/auth/code/verify'",
                       "'/auth/recupero'",
                       'data-testid="signup-form"'):
            assert marker in src, f"flusso auth utente sparito: {marker}"

    def test_lr1_form_operatori_intoccato(self):
        src = self.OPERATOR_LOGIN.read_text()
        for marker in ('data-testid="login-email-input"',
                       'data-testid="login-password-input"',
                       'data-testid="login-submit-btn"',
                       "await login(email, password)"):
            assert marker in src, f"flusso auth operatori sparito: {marker}"

    # ── 6. i18n x4, copy pulito ──────────────────────────────────────

    def test_lr1_i18n_x4_copy_pulito(self):
        import json as _json
        mkt_keys = ("accountMenuUser", "accountMenuCreate", "accountMenuMy",
                    "accountMenuLogout", "accountMenuOperators",
                    "accountMenuWork")
        for lang in ("it", "en", "de", "fr"):
            loc = _json.loads((FRONTEND_SRC / "locales" / lang
                               / "landings.json").read_text())
            for k in mkt_keys:
                val = loc["marketplace"].get(k, "")
                assert val, f"{lang}: manca marketplace.{k}"
                assert "Passaporto" not in val and "—" not in val \
                    and "–" not in val and "negozio" not in val.lower(), \
                    f"{lang}: copy vietato in marketplace.{k}"
            for k in ("operatorHint", "operatorHintLink"):
                val = loc["account"].get(k, "")
                assert val, f"{lang}: manca account.{k}"
                assert "—" not in val and "–" not in val
            auth = _json.loads((FRONTEND_SRC / "locales" / lang
                                / "auth.json").read_text())
            for k in ("aurya_hint", "aurya_link"):
                val = auth["login"].get(k, "")
                assert val, f"{lang}: manca login.{k}"
                assert "—" not in val and "–" not in val

    def test_ritorni_al_login_puntano_alla_porta_unica(self):
        """S0 sposto' la login dalla root a /login; ID (20/8) l'ha
        unificata su /accedi. Ogni uscita «Accedi» dentro AuthPages
        deve portare alla porta unica, mai alla homepage.
        """
        src = self.OPERATOR_LOGIN.read_text()
        # ID-octies: l'etichetta della verifica non dice piu' «vai al
        # login» ma «entra in Aurya», e porta al secondo passo
        for label in ("signup.login_link", "forgot_password.back_to_login",
                      "verify_email.go_to_welcome"):
            i = src.index(label)
            # il target sta nel tag/handler subito sopra l'etichetta
            before = src[max(0, i - 400):i]
            anchor = before.rfind('to="/')
            nav = before.rfind('navigate(`/')
            target_at = max(anchor, nav)
            assert target_at != -1, f"{label}: nessun target trovato"
            target = before[target_at:target_at + 20]
            assert target.startswith(('to="/accedi', 'navigate(`/accedi',
                                      'to="/login', 'navigate(`/login')), \
                f"{label} porta a {target!r}: deve portare alla porta"
            # ID-octies: dalla verifica si passa dalla porta ma si
            # atterra sul benvenuto (?next=), non sul login nudo
            if label == "verify_email.go_to_welcome":
                assert "benvenuto" in before[target_at:target_at + 90], \
                    "dopo la verifica non si va piu' al secondo passo"


class TestHomeHp2:
    """HP2 (31/7/2026) — la homepage della fase rete, specifica
    DEFINITIVA del founder. Supera e SOSTITUISCE TestHomeHp1: il copy
    della v3 non esiste piu' da nessuna parte, quindi la classe e'
    riscritta, non affiancata.

    Sette sezioni nell'ordine: hero, cosa troverai (tre colonne),
    perche' esiste Aurya, dal Magazine, la rete, per gli operatori,
    la lettera. Il copy e' CHIUSO parola per parola.

    Queste guardie difendono le decisioni che si perdono per prime in
    un refactor: le due CTA dell'hero e la loro destinazione, la terza
    colonna che NON e' un link, la sezione dati che sparisce invece di
    mostrare una griglia vuota, le cinque voci del footer di rete, la
    rotta /magazine che non deve diventare canonica di nascosto e il
    payoff di brand ovunque.

    Fuori scopo: la home della fase MARKETPLACE (HomeGate →
    RetreatsCalendarPage) e' un'altra pagina e non e' toccata qui.
    """

    HOME = FRONTEND_SRC / "features" / "network" / "NetworkHomePage.js"
    EDITORIAL = FRONTEND_SRC / "components" / "editorial"
    SHELL = (FRONTEND_SRC / "features" / "storefront" / "components"
             / "MarketplaceShell.jsx")
    APP = FRONTEND_SRC / "App.js"

    # ── 1. le sei sezioni brand v3, nell'ordine ──────────────────────
    # LC8 — la riscrittura founder del 2/8 ("la home in sette battute")
    # ha sostituito la specifica HP2: hp-network e' stata assorbita da
    # hp-pros e il copy e' nuovo. La guardia segue il DISPOSITIVO:
    # testid in ordine, titolo dalla chiave giusta.

    _SEZIONI = (
        ("hp-hero", "nwHome.heroTitle"),
        ("hp-pillars", "nwHome.findTitle"),
        ("hp-why", "nwHome.whyTitle"),
        ("hp-magazine", "nwHome.magTitle"),
        ("hp-pros", "nwHome.prosTitle"),
        ("hp-letter", "nwHome.letterTitle"),
    )

    def test_hp2_sette_sezioni_nell_ordine(self):
        src = self.HOME.read_text()
        pos = -1
        for testid, chiave in self._SEZIONI:
            marker = f'data-testid="{testid}"'
            assert marker in src, f"sezione {testid} mancante"
            assert chiave in src, f"{testid}: manca la chiave {chiave}"
            here = src.index(marker)
            assert here > pos, f"{testid}: sezione fuori ordine"
            pos = here

    def test_hp2_copy_lungo_parola_per_parola(self):
        """LC8 — il copy e' del founder e cambia senza chiedere permesso
        ai test: la guardia tiene solo le due frasi portanti dell'hero
        brand v3, quelle che definiscono la pagina."""
        src = self.HOME.read_text()
        for frase in ("Il benessere inizia dalle persone.",
                      "non dovrebbe essere una questione di fortuna"):
            assert frase in src, f"copy portante mancante: {frase[:50]}…"

    def test_hp2_gerarchia_titoli(self):
        """Un solo h1 (l'hero), tutto il resto h2; le colonne h3."""
        src = self.HOME.read_text()
        assert src.count('as="h1"') == 1, "l'h1 deve essere uno solo"
        assert src.count('as="h2"') == 5, "le altre cinque sezioni sono h2"
        pillar = (self.EDITORIAL / "PillarCard.jsx").read_text()
        assert "<h3" in pillar, "il titolo di una colonna e' un h3"

    def test_hp2_sezione_rete_non_nomina_il_commercio(self):
        """Vincolo del founder: la sezione professionisti (che ha
        assorbito la vecchia sezione rete) parla di presenza e
        racconto, non di pagamenti, marketplace o Stripe."""
        src = self.HOME.read_text()
        blocco = src[src.index('data-testid="hp-pros"'):
                     src.index('data-testid="hp-letter"')]
        for vietata in ("Stripe", "stripe", "pagament", "marketplace",
                        "abbonament", "prezzo"):
            assert vietata not in blocco, \
                f"sezione professionisti: parola vietata '{vietata}'"

    # ── 2. hero: due azioni, di peso diverso, verso il magazine ──────

    def test_hp2_hero_due_cta_e_destinazioni(self):
        src = self.HOME.read_text()
        blocco = src[src.index('data-testid="hp-hero"'):
                     src.index('data-testid="hp-pillars"')]
        assert blocco.count("<EditorialCta") == 2, \
            "l'hero ha esattamente due azioni: magazine e professionisti"
        assert 'variant="solid"' in blocco, "la primaria e' quella piena"
        assert blocco.count('variant="quiet"') == 1, \
            "la secondaria e' sottovoce, non un secondo bottone pieno"
        # LC6 — la secondaria usa la parola dell'header
        assert "Per i professionisti" in blocco
        assert "JOIN_PATH" in blocco, \
            "la secondaria porta al funnel professionisti"
        # la primaria punta al Magazine passando dalla costante
        i_solid = blocco.index('variant="solid"')
        intorno = blocco[max(0, i_solid - 200):i_solid + 200]
        assert "MAGAZINE_PATH" in intorno, \
            "la CTA primaria dell'hero deve portare al Magazine"

    def test_hp2_payoff_occhiello_sopra_l_h1(self):
        """Il payoff di brand resta l'occhiello dell'hero, sopra l'h1."""
        src = self.HOME.read_text()
        assert "<BrandPayoff" in src, "payoff sparito dall'hero"
        assert src.index("<BrandPayoff") < src.index('as="h1"'), \
            "il payoff sta SOPRA l'h1, non sotto"

    # ── 3. le tre colonne: la terza non e' un link ───────────────────

    def test_hp2_tre_colonne_nell_ordine(self):
        # LC8 — via il requisito delle emoji: il segno in testa alle
        # colonne e' diventato fotografico ('plain' nel kit), per
        # decisione di design successiva a HP2.
        src = self.HOME.read_text()
        pos = -1
        for key, titolo in (("magazine", "Magazine"),
                            ("professionisti", "Professionisti"),
                            ("esperienze", "Esperienze")):
            marker = f"id: '{key}'"
            assert marker in src, f"colonna {key} mancante"
            here = src.index(marker)
            assert here > pos, f"colonna {key} fuori ordine"
            pos = here
            assert titolo in src

    def test_hp2_terza_colonna_non_cliccabile(self):
        """L'etichetta di stato (oggi 'Prossimamente') non e' un link
        e nemmeno un bottone disabilitato."""
        src = self.HOME.read_text()
        blocco = src[src.index("id: 'esperienze'"):src.index("];", src.index("id: 'esperienze'"))]
        assert "to:" not in blocco, \
            "la terza colonna non ha destinazione: e' una promessa"
        assert "pillarExpBadge" in blocco, \
            "la terza colonna porta l'etichetta di stato"
        pillar = (self.EDITORIAL / "PillarCard.jsx").read_text()
        # il ramo senza `to` rende uno <span>, non un Link/button
        ramo = pillar[pillar.index("{to ? ("):]
        chiusura = ramo[ramo.index(") : ("):]
        assert "<span" in chiusura, "lo stato 'in arrivo' e' un <span>"
        assert "<Link" not in chiusura and "<button" not in chiusura, \
            "'In arrivo' non deve essere cliccabile ne' focalizzabile"
        assert "disabled" not in chiusura, \
            "niente bottone disabilitato: promette un clic che non arriva"

    def test_hp2_colonne_spazio_riservato_e_focus(self):
        pillar = (self.EDITORIAL / "PillarCard.jsx").read_text()
        assert "h-full" in pillar and "mt-auto" in pillar, \
            "le tre schede devono allinearsi in altezza e nel piede"
        assert "focus-visible:ring" in pillar, "focus non visibile"
        assert "aria-hidden" in pillar, \
            "il segno in testa e' decorativo: va nascosto agli screen reader"

    # ── 4. la sezione con i dati sparisce se i dati non ci sono ──────

    def test_hp2_magazine_gated_sui_dati(self):
        src = self.HOME.read_text()
        assert "{articles.length > 0 && (" in src, \
            "senza articoli la sezione Dal Magazine non deve esistere"
        assert "'/public/articles'" in src, "sorgente articoli sbagliata"
        # il gate deve avvolgere DAVVERO la sezione Dal Magazine
        # (LC8 — hp-network non esiste piu': la sezione dopo e' hp-pros)
        i_gate = src.index("{articles.length > 0 && (")
        assert i_gate < src.index('data-testid="hp-magazine"')
        assert src.index('data-testid="hp-magazine"') < src.index('data-testid="hp-pros"')

    def test_hp2_niente_sezione_persone(self):
        """HP2 toglie la griglia dei volti: la rete si racconta a
        parole finche' i profili non ci sono davvero."""
        src = self.HOME.read_text()
        assert "<PersonCard" not in src, "la sezione 'Le persone' e' uscita"
        assert "api.get('/public/network/members'" not in src, \
            "la home non deve piu' chiamare la rotta dei membri"
        # ma il componente resta nel kit, per /operatori
        assert (self.EDITORIAL / "PersonCard.jsx").exists()

    # ── 5. le destinazioni delle CTA ─────────────────────────────────

    def test_hp2_destinazioni_cta(self):
        # LC8 — le destinazioni vivono nelle costanti di pagina
        # (NETWORK_PATH/JOIN_PATH), non piu' inline
        src = self.HOME.read_text()
        for dest in ("MAGAZINE_PATH = '/blog'",
                     "NETWORK_PATH = '/operatori'",
                     "JOIN_PATH = '/entra-nella-rete'",
                     'to="/manifesto"',
                     'to="/newsletter"'):
            assert dest in src, f"destinazione mancante: {dest}"

    def test_hp2_ancora_form_operatori_esiste_e_scrolla(self):
        """'Parliamone' punta all'ancora del form: l'ancora c'e' e chi
        arriva da fuori ci atterra davvero."""
        landing = (FRONTEND_SRC / "features" / "prelaunch"
                   / "OperatorLandingPage.js").read_text()
        assert 'id="presentati"' in landing, "ancora del form mancante"
        assert "prefers-reduced-motion" in landing, \
            "lo scorrimento interno alla pagina deve rispettare reduced-motion"

    def test_hp2_scroll_to_top_rispetta_le_ancore(self):
        """ScrollToTop rimandava in cima ANCHE i link con ancora: con un
        hash si atterra sull'elemento, non sull'intestazione."""
        app = self.APP.read_text()
        blocco = app[app.index("function ScrollToTop()"):]
        blocco = blocco[:blocco.index("return null;")]
        assert "const { pathname, hash } = useLocation();" in blocco, \
            "ScrollToTop deve leggere anche l'hash"
        assert "if (!hash) {" in blocco and "window.scrollTo(0, 0);" in blocco, \
            "senza hash si riparte dall'alto, come prima"
        assert "scrollIntoView" in blocco, "con hash si salta all'ancora"
        # il bersaglio arriva in ritardo (rotte lazy): serve un riprova
        assert "setTimeout" in blocco, \
            "senza riprova le pagine lazy perdono l'ancora"
        assert "requestAnimationFrame" not in blocco, \
            "rAF si ferma in scheda di sfondo: l'ancora andrebbe persa"

    def test_hp2_rotta_magazine_redirige_su_blog(self):
        """La specifica dice /magazine, la canonica indicizzata resta
        /blog: alias sì, rinomina no."""
        app = self.APP.read_text()
        assert '<Route path="/magazine" element={<Navigate to="/blog" replace />} />' in app, \
            "/magazine deve esistere come redirect a /blog"
        assert '<Route path="/blog" element={<BlogIndexPage />} />' in app, \
            "la rotta canonica /blog non si tocca"
        # e dalla home si linka la canonica, non l'alias
        src = self.HOME.read_text()
        assert 'to="/magazine"' not in src and "'/magazine'" not in src, \
            "dalla home si linka /blog: il redirect e' per chi arriva da fuori"

    # ── 6. il footer della fase rete: cinque voci ────────────────────

    # LC8 — l'ordine e le etichette sono quelli della riscrittura
    # founder del 2/8: Magazine prima del Manifesto, "La Rete"
    # (navNetwork) al posto di navNetworkMembers, la Lettera nella
    # colonna Risorse (footer-nw-lettera, navLetter).
    _FOOTER_NETWORK = (
        ("footer-nw-magazine", "/blog", "navBlog"),
        ("footer-nw-manifesto", "/manifesto", "navManifesto"),
        ("footer-nw-operatori", "/operatori", "navNetwork"),
        ("footer-nw-chisiamo", "/chi-siamo", "footerAbout"),
        ("footer-nw-lettera", "/newsletter", "navLetter"),
    )

    def test_hp2_footer_rete_cinque_voci_nell_ordine(self):
        shell = self.SHELL.read_text()
        pos = -1
        for testid, to, key in self._FOOTER_NETWORK:
            marker = f'data-testid="{testid}"'
            assert marker in shell, f"voce di footer mancante: {testid}"
            here = shell.index(marker)
            assert here > pos, f"voce {testid} fuori ordine"
            pos = here
            blocco = shell[max(0, here - 260):here + 260]
            assert f'to="{to}"' in blocco, f"{testid}: destinazione sbagliata"
            assert f"marketplace.{key}" in blocco, f"{testid}: etichetta non tradotta"

    def test_hp2_footer_rete_senza_manifesto_duplicato(self):
        """In fase rete il Manifesto sta UNA volta sola nel footer: la
        vecchia lista sotto il payoff e' ora riservata al marketplace."""
        shell = self.SHELL.read_text()
        assert shell.count('data-testid="footer-nw-manifesto"') == 1
        # la colonna del brand tiene il suo elenco solo fuori dalla rete
        i_payoff = shell.index("marketplace.payoff")
        blocco = shell[i_payoff:shell.index("marketplace.footerNetwork")]
        assert "{!isNetwork && (" in blocco, \
            "in fase rete l'elenco sotto il payoff deve sparire"
        assert blocco.count('to="/manifesto"') == 1 and "howPage.title" in blocco, \
            "quell'elenco e' il ramo marketplace (Manifesto + Come funziona)"

    # ── 7. SEO della home ────────────────────────────────────────────

    def test_hp2_seo_home(self):
        src = self.HOME.read_text()
        assert "Aurya | Il benessere inizia dalle persone" in src
        # LC8 — la description e' del founder e cambia: si difende il
        # dispositivo (chiave nwHome.seoDesc, canonical sulla radice)
        assert "nwHome.seoDesc" in src, "la description non passa dall'i18n"
        assert "canonicalPath: '/'" in src

    def test_hp2_seo_description_entro_i_158_caratteri(self):
        import json as _json
        for lang in ("it", "en", "de", "fr"):
            loc = _json.loads((FRONTEND_SRC / "locales" / lang
                               / "landings.json").read_text())
            desc = loc["nwHome"]["seoDesc"]
            assert 0 < len(desc) <= 158, \
                f"{lang}: description da {len(desc)} caratteri, il taglio e' 158"
            titolo = loc["nwHome"]["seoTitle"]
            assert "Aurya" in titolo and len(titolo) <= 65, \
                f"{lang}: title fuori misura"

    # ── 8. il payoff nuovo c'e', il vecchio motto non esiste piu' ────

    _PAYOFF = {
        # CS2c (founder, 7/8): il payoff italiano e' diventato un
        # descrittore di cosa si trova su Aurya. Le altre tre lingue
        # restano al payoff v3 (contenuti IT-only dal 2/8).
        "it": "Pratiche, eventi e ritiri di benessere",
        "en": "Trust is placed in someone, not something.",
        "de": "Man vertraut jemandem, nicht etwas.",
        "fr": "On fait confiance à quelqu'un, pas à quelque chose.",
    }

    def test_hp2_payoff_costanti(self):
        js = (FRONTEND_SRC / "config" / "brand.js").read_text()
        assert f"BRAND_PAYOFF = '{self._PAYOFF['it']}'" in js
        assert "BRAND_MOTTO" not in js, "la vecchia costante deve sparire"
        from core.brand import BRAND_PAYOFF
        assert BRAND_PAYOFF == self._PAYOFF

    def test_hp2_vecchio_motto_assente_ovunque(self):
        """Scan frontend + backend: del vecchio motto non resta traccia
        (i test sono esclusi: e' qui che il testo va nominato)."""
        vietati = ("Connect · Heal · Grow", "CONNECT · HEAL · GROW",
                   "Connect. Heal. Grow.", "BRAND_MOTTO")
        radici = ((FRONTEND_SRC, (".js", ".jsx", ".json", ".css")),
                  (BACKEND_DIR, (".py",)))
        colpevoli = []
        for radice, exts in radici:
            for path in radice.rglob("*"):
                if not path.is_file() or path.suffix not in exts:
                    continue
                if "tests" in path.parts or "node_modules" in path.parts:
                    continue
                testo = path.read_text(errors="ignore")
                for v in vietati:
                    if v in testo:
                        colpevoli.append(f"{path}: {v}")
        assert not colpevoli, f"vecchio motto superstite: {colpevoli[:5]}"

    def test_hp2_payoff_nelle_superfici_di_brand(self):
        assert "marketplace.payoff" in self.SHELL.read_text(), "footer senza payoff"
        logo = (FRONTEND_SRC / "components" / "BrandLogo.jsx").read_text()
        assert "marketplace.payoff" in logo, "wordmark senza payoff"
        email = (BACKEND_DIR / "services" / "email_service.py").read_text()
        assert "BRAND_PAYOFF" in email, "template email senza payoff"

    # ── 9. il kit editoriale riusabile ───────────────────────────────

    def test_hp2_kit_editoriale_completo(self):
        for name in ("Section.jsx", "DisplayTitle.jsx", "Lede.jsx",
                     "Quote.jsx", "PersonCard.jsx", "ArticleCard.jsx",
                     "PillarCard.jsx", "EditorialCta.jsx", "index.js"):
            assert (self.EDITORIAL / name).exists(), \
                f"componente editoriale mancante: {name}"
        idx = (self.EDITORIAL / "index.js").read_text()
        assert "PillarCard" in idx and "TitleLine" in idx, \
            "i mattoni nuovi devono passare dal barile del kit"

    def test_hp2_movimento_solo_dissolvenza_e_reduced_motion(self):
        reveal = (self.EDITORIAL / "useReveal.js").read_text()
        assert "prefers-reduced-motion: reduce" in reveal
        css = (FRONTEND_SRC / "index.css").read_text()
        idx = css.index(".editorial-reveal {")
        blocco = css[idx:css.index("/* Filo d'oro", idx)]
        # solo opacita': nessuna traslazione → nessun layout shift
        assert "translate" not in blocco and "transform:" not in blocco
        assert "opacity" in blocco
        assert "prefers-reduced-motion: reduce" in blocco

    # ── 10. i18n x4 delle chiavi nuove, copy pulito ──────────────────

    _NWHOME_KEYS = (
        "seoTitle", "seoDesc",
        "heroTitleA", "heroTitleB", "heroBody", "heroCta", "heroCtaAlt",
        "findTitle", "findSubA", "findSubB",
        "pillarMagTitle", "pillarMagText", "pillarMagCta",
        "pillarProTitle", "pillarProText", "pillarProCta",
        "pillarExpTitle", "pillarExpText", "pillarExpBadge",
        "whyTitle", "whyP1", "whyP2", "whyP3", "whyCta",
        "magTitle", "magSub", "magCta",
        "netTitleA", "netTitleB", "netBody", "netCta",
        "prosEyebrow", "prosTitle", "prosP1", "prosP2", "prosP3",
        "prosCta", "prosCtaAlt",
        "letterTitle", "letterBody", "letterClose", "letterCta",
    )

    _FOOTER_KEYS = ("navManifesto", "navBlog", "navNetworkMembers",
                    "footerAbout", "navNewsletter")

    def test_hp2_i18n_x4_chiavi_nuove(self):
        """LC8 — il payoff resta l'unica frase tradotta x4 (e' il
        brand, sta anche nel footer di tutte le lingue). Il copy della
        home e' SOLO italiano dal 2/8: si pretende l'italiano completo
        delle chiavi che la pagina usa davvero."""
        import json as _json
        for lang in ("it", "en", "de", "fr"):
            loc = _json.loads((FRONTEND_SRC / "locales" / lang
                               / "landings.json").read_text())
            assert loc["marketplace"].get("payoff") == self._PAYOFF[lang], \
                f"{lang}: payoff mancante o diverso"
        it = _json.loads((FRONTEND_SRC / "locales" / "it"
                          / "landings.json").read_text())
        nw = it.get("nwHome") or {}
        for k in ("seoTitle", "seoDesc", "heroTitle", "heroP1",
                  "heroCta", "heroCtaAlt", "findTitle", "whyTitle",
                  "magTitle", "prosTitle", "letterTitle", "letterCta"):
            assert nw.get(k), f"[it] manca nwHome.{k}"
        for k, v in nw.items():
            assert v and v.strip(), f"[it] nwHome.{k} vuota"

    def test_hp2_copy_nuovo_senza_trattini_lunghi(self):
        import json as _json
        for lang in ("it", "en", "de", "fr"):
            loc = _json.loads((FRONTEND_SRC / "locales" / lang
                               / "landings.json").read_text())
            valori = list((loc.get("nwHome") or {}).values())
            valori.append(loc["marketplace"]["payoff"])
            valori += [loc["marketplace"][k] for k in self._FOOTER_KEYS]
            for val in valori:
                assert "—" not in val and "–" not in val, \
                    f"{lang}: trattino lungo nel copy nuovo: {val[:40]}"
        # anche nel copy inline della home (i defaultValue), non nei
        # commenti: i trattini lunghi sono vietati a chi legge il sito
        import re as _re
        home = self.HOME.read_text()
        defaults = _re.findall(r'defaultValue: "([^"]*)"', home)
        assert len(defaults) >= 42, \
            f"i defaultValue della home sono {len(defaults)}, ne servono 42"
        for val in defaults:
            assert "—" not in val and "–" not in val, \
                f"trattino lungo nel copy della home: {val[:40]}"


class TestLandingOperatoriOl1:
    """OL1 (31/7/2026) — la landing operatori (/entra-nella-rete) segue
    la specifica del founder.

    La regola che vale piu' di tutte: il "profilo gratuito" NON e' piu'
    un argomento di vendita (abbassava il valore percepito). La parola
    resta ammessa SOLO nella domanda e nella risposta della FAQ, dove e'
    una risposta onesta a una domanda legittima. Fuori da li', neanche
    nella description SEO, che prima diceva "Gratuitamente".
    """

    PAGE = FRONTEND_SRC / "features" / "prelaunch" / "OperatorLandingPage.js"
    LOCALES = ("it", "en", "de", "fr")

    def _page(self):
        return self.PAGE.read_text()

    def _locale(self, lang):
        import json
        path = FRONTEND_SRC / "locales" / lang / "prelaunch.json"
        return json.loads(path.read_text())

    @staticmethod
    def _strings(node, prefix=""):
        """Tutte le stringhe del blocco i18n, con la loro chiave."""
        if isinstance(node, dict):
            for k, v in node.items():
                yield from TestLandingOperatoriOl1._strings(v, f"{prefix}.{k}")
        elif isinstance(node, str):
            yield prefix, node

    def test_ol1_le_otto_sezioni(self):
        """OL3 (riscrittura del founder) + LC4 — la guardia lessicale
        sul copy pre-OL3 era rimasta indietro di una riscrittura intera:
        ora si guarda il DISPOSITIVO, le nove sezioni col loro testid.
        Il copy dentro le sezioni e' del founder e cambia senza chiedere
        permesso ai test."""
        page = self._page()
        for tid in ("ol-hero", "ol-now", "ol-join", "ol-go", "ol-for",
                    "ol-faq", "ol-who", "ol-form", "ol-end"):
            assert f'data-testid="{tid}"' in page, f"manca la sezione {tid}"

    def test_ol1_quattro_blocchi_cosa_trovi(self):
        """OL3 — la sezione 'cosa significa entrare' sono TRE schede
        fotografiche (r03, r08, r09), non piu' i quattro blocchi del
        copy vecchio."""
        page = self._page()
        assert "ol-card-" in page, "sparite le schede della sezione rete"
        for foto in ("r03.jpg", "r08.jpg", "r09.jpg"):
            assert foto in page, f"manca la fotografia {foto}"

    def test_lc4_cta_nel_hero_e_payoff_al_posto_delle_negazioni(self):
        """LC4 (revisione pre-lancio) — due decisioni che non devono
        regredire: 1) il hero scuro ha una CTA verso #presentati
        (misurata: prima azione a 3,4 schermate, form a 26 — chi
        arrivava gia' convinto doveva farsi tutta la pagina); 2) la
        sezione dei fondatori apre col payoff del brand, non con le tre
        negazioni ("Non siamo un'agenzia/software/directory")."""
        import re
        page = self._page()
        assert 'data-testid="ol-hero-cta-top"' in page, \
            "sparita la CTA del hero verso il form"
        assert "Pratiche, eventi e ritiri" in page
        assert "di benessere" in page
        # il commento che racconta la decisione cita le negazioni:
        # si giudica solo il copy che il lettore puo' vedere
        visibile = re.sub(r"/\*.*?\*/", "", page, flags=re.DOTALL)
        visibile = re.sub(r"^\s*//.*$", "", visibile, flags=re.MULTILINE)
        assert "Non siamo un" not in visibile, \
            "le negazioni sono tornate nella sezione fondatori"

    def test_ol1_gratuito_solo_nella_faq(self):
        """Ne' la pagina ne' i quattro locales usano gratuito/gratis
        fuori dalla FAQ. Le occorrenze nei commenti del sorgente sono
        ammesse: spiegano proprio questa regola."""
        import re
        page = self._page()
        # via i commenti, poi si guardano solo le stringhe di copy
        senza_commenti = re.sub(r"/\*.*?\*/", "", page, flags=re.DOTALL)
        senza_commenti = re.sub(r"^\s*//.*$", "", senza_commenti,
                                flags=re.MULTILINE)
        for m in re.finditer(r"gratuit|gratis", senza_commenti, re.I):
            finestra = senza_commenti[max(0, m.start() - 200):m.start() + 60]
            # AB2 (13/8): la FAQ del costo e' faq1 (tre punti + link
            # /costi); l'intento resta lo stesso — la parola vive SOLO
            # nella risposta alla domanda sul prezzo
            assert re.search(r"faq1b|faq3", finestra), \
                f"'gratuito' fuori dalla FAQ nella landing: ...{finestra[-90:]}"
        for lang in self.LOCALES:
            blocco = self._locale(lang).get("opNw", {})
            for chiave, valore in self._strings(blocco):
                if re.search(r"gratuit|gratis|kostenlos|free of charge",
                             valore, re.I):
                    assert "faq3" in chiave, \
                        f"[{lang}] '{chiave}' usa gratuito fuori dalla FAQ"

    def test_ol1_mai_connect_ne_gestionale(self):
        """L'evoluzione si racconta com'e' scritta: niente nomi di
        prodotto, niente gergo da software."""
        import re
        page = re.sub(r"/\*.*?\*/", "", self._page(), flags=re.DOTALL)
        page = re.sub(r"^\s*//.*$", "", page, flags=re.MULTILINE)
        assert "Aurya Connect" not in page
        assert "gestionale" not in page.lower()
        for lang in self.LOCALES:
            for _, valore in self._strings(self._locale(lang).get("opNw", {})):
                assert "Aurya Connect" not in valore
                assert "gestionale" not in valore.lower()

    def test_ol1_tre_cta_al_form(self):
        """Le CTA della landing portano tutte all'ancora #presentati,
        dove da RD-bis (19/8) non vive piu' un modulo di candidatura ma
        la registrazione vera: il bottone crea l'account."""
        page = self._page()
        assert page.count("#presentati") >= 3, \
            "servono tre CTA verso l'ancora del form"
        assert 'id="presentati"' in page, "manca l'ancora del form"
        assert "InlineSignupForm" in page, \
            "all'ancora deve vivere la registrazione incorporata"
        assert "ctaContact2" in page, \
            "manca la chiave del bottone «Crea il tuo account»"

    def test_ol1_i18n_x4_e_niente_trattini_lunghi(self):
        """OL3 — il copy della landing vive in `opPro`, SOLO in
        italiano (decisione founder 2/8: i contenuti nuovi non si
        traducono piu' x4; con fallbackLng='it' le altre lingue leggono
        queste chiavi). La guardia pretende l'italiano completo e
        niente trattini lunghi, non piu' la parita' su 4 lingue."""
        chiavi_it = {k for k, _ in self._strings(self._locale("it")["opPro"])}
        assert len(chiavi_it) >= 40, \
            f"chiavi opPro in italiano: {len(chiavi_it)}, troppo poche"
        for chiave, valore in self._strings(self._locale("it")["opPro"]):
            assert "—" not in valore and "–" not in valore, \
                f"[it] trattino lungo in {chiave}"


class TestManifestoSw1:
    """SW1 (31/7/2026) — il Manifesto riscritto sulla teoria del
    Blueprint (docs/AURYA_BLUEPRINT_2026-07.md, cap. 0/2/9).

    Quattro movimenti nell'ordine: la teoria (frase sola, grande), il
    mondo come lo vediamo, come lavoriamo, cosa non faremo mai (l'unica
    ancora verde). Poi la firma coi fondatori REALI (materiale
    aboutPage.faces* gia' esistente, niente inventato) e la doppia CTA
    discreta. Ogni frase segue il dispositivo a coppia: prima una
    verita' sul mondo, poi un nostro gesto.

    Queste guardie difendono: l'ordine dei movimenti, la teoria come
    h1 unico, la lista dei mai (almeno 4 voci) col suo epilogo, il
    badge detto come provenienza e mai come medaglia, la firma vera,
    le due destinazioni finali, e il lessico: niente parole vietate
    dal Blueprint, niente trattini lunghi, x4 lingue complete.

    Il copy VECCHIO ("la rete degli operatori olistici", "Da dove
    nasce Aurya", il "Gratuitamente" nella CTA) non deve riapparire.
    """

    PAGE = FRONTEND_SRC / "features" / "network" / "ManifestoPage.js"
    LOCALES = ("it", "en", "de", "fr")

    def _page(self):
        return self.PAGE.read_text()

    def _copy(self):
        """Il sorgente senza commenti: le guardie lessicali giudicano
        quello che il lettore puo' vedere, non le note di lavoro."""
        import re
        src = re.sub(r"/\*.*?\*/", "", self._page(), flags=re.DOTALL)
        return re.sub(r"^\s*//.*$", "", src, flags=re.MULTILINE)

    def _manifesto(self, lang):
        import json
        path = FRONTEND_SRC / "locales" / lang / "landings.json"
        return json.loads(path.read_text()).get("manifesto") or {}

    # ── 1. gli otto movimenti brand v3, nell'ordine ──────────────────
    # LC8 — la riscrittura founder del 2/8 ha sostituito i quattro
    # movimenti SW1 (teoria/mondo/lavoro/mai/firma) con otto sezioni
    # nuove. La guardia segue il DISPOSITIVO: testid in ordine, titolo
    # di sezione dalla chiave giusta.

    _MOVIMENTI = (
        ("mf-open", "manifesto.heroTitle"),
        ("mf-why", "manifesto.whyTitle"),
        ("mf-believe", "manifesto.believeTitle"),
        ("mf-how", "manifesto.howTitle"),
        ("mf-principles", "manifesto.principlesTitle"),
        ("mf-building", "manifesto.buildingTitle"),
        ("mf-pro", "manifesto.proTitle"),
        ("mf-follow", "manifesto.followTitle"),
    )

    def test_sw1_quattro_movimenti_nell_ordine(self):
        src = self._page()
        pos = -1
        for testid, chiave in self._MOVIMENTI:
            marker = f'data-testid="{testid}"'
            assert marker in src, f"movimento {testid} mancante"
            assert chiave in src, f"{testid}: manca la chiave {chiave}"
            here = src.index(marker)
            assert here > pos, f"{testid}: movimento fuori ordine"
            pos = here

    def test_sw1_teoria_frase_sola_e_h1_unico(self):
        """L'apertura e' una frase sola, grande (la misura 'manifesto'
        del kit), ed e' l'unico h1. LC8 — la frase oggi e' la domanda
        del brand v3, non piu' la teoria del Blueprint."""
        src = self._page()
        assert src.count('as="h1"') == 1, "l'h1 e' uno solo"
        i_h1 = src.index('as="h1"')
        intorno = src[max(0, i_h1 - 200):i_h1 + 300]
        assert 'size="manifesto"' in intorno, \
            "l'apertura usa la misura 'manifesto' del kit (frase sola)"
        assert "Ogni percorso di benessere inizia da una domanda." \
            in intorno, "l'h1 e' la domanda del manifesto"

    def test_sw1_mondo_constatazione_mai_lamento(self):
        """Il problema si constata, non si attacca: nessun concorrente
        nominato, niente gergo da piattaforme."""
        copy = self._copy()
        for vietata in ("Treatwell", "Fresha", "Mindbody", "social",
                        "algoritm", "ciarlatan"):
            assert vietata not in copy, \
                f"il manifesto constata, non attacca: via '{vietata}'"

    def test_sw1_badge_provenienza_mai_medaglia(self):
        """LC8 — il badge Verificato Aurya non vive piu' nel copy del
        Manifesto (brand v3: 'criterio invisibile, badge = provenienza'
        si racconta sui profili, non qui). Quello che resta in guardia:
        la selezione non si proclama MAI."""
        copy = self._copy()
        for proclama in ("i migliori", "selezione rigorosa", "eccellenza",
                         "solo i più", "d'élite"):
            assert proclama.lower() not in copy.lower(), \
                f"la selezione non si proclama: via '{proclama}'"

    # ── 2. i cinque principi sull'ancora verde ───────────────────────

    def test_sw1_lista_dei_mai(self):
        """LC8 — la lista dei mai e' uscita col brand v3: al suo posto
        I NOSTRI PRINCIPI, cinque, ognuno con titolo e riga che lo
        spiega. La guardia difende che restino cinque e pieni."""
        src = self._page()
        it = self._manifesto("it")
        for n in range(1, 6):
            assert it.get(f"p{n}Title") and it.get(f"p{n}Body"), \
                f"principio {n} incompleto (manifesto.p{n}Title/Body)"
            assert f"manifesto.p{n}Title" in src, \
                f"la pagina non monta il principio {n}"
        assert "manifesto.principlesIntro" in src, \
            "manca l'introduzione dei principi"

    def test_sw1_ancora_verde_una_sola_ed_e_il_movimento_4(self):
        """Una sola ancora tonale, e sta sui principi: e' li' che il
        verde diventa solenne al punto giusto (brand v3)."""
        src = self._page()
        assert src.count('tone="sage"') == 1, \
            "il Manifesto ha UNA ancora verde, non di piu'"
        i_sage = src.index('tone="sage"')
        assert 'data-testid="mf-principles"' in src[i_sage:i_sage + 400], \
            "l'ancora verde e' la sezione dei principi"

    # ── 3. la firma: fondatori reali, CTA finali ─────────────────────

    def test_sw1_firma_materiale_reale(self):
        """La fotografia dei fondatori e' quella vera, e nessuna
        biografia viene gonfiata (niente date, premi, numeri)."""
        import re
        src = self._page()
        assert "/media/chisiamo-aurya.jpg" in src, "manca la foto vera"
        copy = self._copy()
        assert not re.search(r"\b(19|20)\d{2}\b", copy), \
            "nessuna data va inventata nel Manifesto"
        for inventato in ("premio", "certificat", "clienti soddisfatti"):
            assert inventato.lower() not in copy.lower(), \
                f"fatto non verificato nel copy: '{inventato}'"

    def test_sw1_doppia_cta_discreta(self):
        """LC8 — le uscite del Manifesto brand v3: due CTA a meta'
        pagina (Magazine e Lettera, quiet) e le due chiusure — la
        sezione professionisti (mf-cta-pro → /entra-nella-rete) e la
        sezione seguire il progetto (Lettera + Magazine)."""
        src = self._page()
        assert 'data-testid="mf-cta-magazine-top"' in src
        assert 'data-testid="mf-cta-letter-top"' in src
        blocco_pro = src[src.index('data-testid="mf-pro"'):]
        assert 'to="/entra-nella-rete"' in blocco_pro[:2200], \
            "la sezione professionisti deve portare a /entra-nella-rete"
        blocco_follow = src[src.index('data-testid="mf-follow"'):]
        assert 'to="/newsletter"' in blocco_follow, \
            "la chiusura deve offrire la Lettera"
        assert 'to="/blog"' in blocco_follow, \
            "la chiusura deve offrire il Magazine"

    # ── 4. SEO nella voce ────────────────────────────────────────────

    def test_sw1_seo(self):
        src = self._page()
        assert ("Il manifesto di Aurya | Ogni percorso di benessere "
                "inizia da una domanda") in src
        assert "canonicalPath: '/manifesto'" in src
        # LC8 — solo italiano (fallbackLng='it')
        it = self._manifesto("it")
        desc = it.get("seoDesc") or ""
        assert 0 < len(desc) <= 158, \
            f"[it] description da {len(desc)} caratteri, taglio 158"
        assert "Aurya" in (it.get("seoTitle") or ""), "[it] title senza brand"

    # ── 5. il lessico: parole vietate e trattini lunghi ──────────────

    # Blueprint cap. 9, "Cosa non diremo mai" + il divieto sul
    # gratuito-come-promessa. Si scandiscono il copy del sorgente
    # (senza commenti, senza il nome tecnico MarketplaceShell) e le
    # chiavi manifesto.* dei quattro locales.
    _VIETATE = ("marketplace", "directory", "gestionale", "piattaform",
                "trasforma la tua vita", "ritrova te stesso",
                "gratuit", "gratis", "kostenlos", "free of charge")

    def test_sw1_parole_vietate_assenti(self):
        """LC8 — lessico giudicato sull'italiano (solo-italiano dal
        2/8). Il principio 1 del founder ('Le persone vengono prima
        delle piattaforme.') e' un contrasto voluto, non un uso della
        parola: si esenta la frase esatta."""
        eccezione = "prima delle piattaforme"
        copy = (self._copy().replace("MarketplaceShell", "")
                .replace(eccezione, ""))
        for vietata in self._VIETATE:
            assert vietata.lower() not in copy.lower(), \
                f"parola vietata nel sorgente del Manifesto: '{vietata}'"
        for chiave, valore in self._manifesto("it").items():
            valore_scan = valore.replace(eccezione, "")
            for vietata in self._VIETATE:
                assert vietata.lower() not in valore_scan.lower(), \
                    f"[it] manifesto.{chiave} usa '{vietata}'"

    def test_sw1_copy_vecchio_sparito(self):
        """Della voce vecchia non resta niente: ne' nel sorgente ne'
        nei locales."""
        src = self._page()
        for morto in ("la rete degli operatori olistici",
                      "Da dove nasce Aurya",
                      "Cosa non ci convince del settore",
                      "Gratuitamente", "manifesto.p1t", "manifesto.ctaTitle",
                      "manifesto.toolsLine", "aboutPage.missionTitle"):
            assert morto not in src, f"copy vecchio superstite: {morto}"
        for lang in self.LOCALES:
            blocco = self._manifesto(lang)
            for morto in ("p1t", "p1b", "p2t", "p2b", "p3t", "p3b",
                          "ctaTitle", "ctaBody", "ctaButton", "toolsLine",
                          "title", "intro"):
                assert morto not in blocco, \
                    f"[{lang}] chiave vecchia superstite: manifesto.{morto}"

    def test_sw1_niente_trattini_lunghi(self):
        import re
        # nel copy inline (i defaultValue, apici singoli o doppi)...
        defaults = re.findall(r"defaultValue:\s*(?:'([^']*)'|\"([^\"]*)\")",
                              self._page())
        valori = [a or b for a, b in defaults]
        assert len(valori) >= 20, \
            f"i defaultValue del Manifesto sono {len(valori)}, attesi almeno 20"
        for val in valori:
            assert "—" not in val and "–" not in val, \
                f"trattino lungo nel copy del Manifesto: {val[:40]}"
        # ...e nelle chiavi manifesto.* dei quattro locales
        for lang in self.LOCALES:
            for chiave, valore in self._manifesto(lang).items():
                assert "—" not in valore and "–" not in valore, \
                    f"[{lang}] trattino lungo in manifesto.{chiave}"

    def test_sw1_i18n_x4_complete(self):
        """LC8 — copy brand v3, SOLO italiano (fallbackLng='it'): via
        la parita' x4. Italiano completo, nessuna chiave vuota, e i
        defaultValue del sorgente coincidono con l'italiano."""
        it = self._manifesto("it")
        assert len(it) >= 25, f"chiavi manifesto in italiano: {len(it)}"
        for k, v in it.items():
            assert v and v.strip(), f"[it] manifesto.{k} vuota"
        # il fallback inline e' l'italiano vero, non una variante
        src = self._page()
        for k, v in it.items():
            if f"manifesto.{k}" in src and f"'{v}'" not in src:
                assert v.replace("’", "'") in src.replace("’", "'"), \
                    f"defaultValue di manifesto.{k} diverso dall'italiano"


class TestChiSiamoSw3:
    """SW3 (31/7/2026) — Chi siamo diventa una pagina propria
    (docs/SITO_REDESIGN_PIANO_2026-07.md).

    La decisione: il Manifesto e' la posizione, Chi siamo sono le
    persone. Due domande diverse, due pagine. Il footer di fase rete
    puntava gia' a /chi-siamo, che pero' era un Navigate sul Manifesto:
    due voci nella stessa colonna che portavano allo stesso posto.

    Queste guardie difendono: la rotta con la pagina vera (mai piu' un
    redirect), le tre negazioni in apertura (l'eco della landing
    operatori), i ritratti fatti coi SOLI fatti verificati dei
    fondatori, la teoria indicata e non riscritta (il Manifesto non si
    duplica), la doppia CTA finale verso il manifesto e la mail, il
    lessico del Blueprint e l'i18n x4.

    La pagina vecchia (features/storefront/AboutAuryaPage.js, voce
    2025) non deve tornare: e' stata rimossa, non lasciata a marcire.
    """

    PAGE = FRONTEND_SRC / "features" / "network" / "ChiSiamoPage.js"
    VECCHIA = FRONTEND_SRC / "features" / "storefront" / "AboutAuryaPage.js"
    LOCALES = ("it", "en", "de", "fr")
    MAIL = "info@aurya.life"

    def _page(self):
        return self.PAGE.read_text()

    def _copy(self):
        """Il sorgente senza commenti: le guardie lessicali giudicano
        quello che il lettore puo' vedere, non le note di lavoro."""
        import re
        src = re.sub(r"/\*.*?\*/", "", self._page(), flags=re.DOTALL)
        return re.sub(r"^\s*//.*$", "", src, flags=re.MULTILINE)

    def _blocco(self, lang):
        import json
        path = FRONTEND_SRC / "locales" / lang / "landings.json"
        return json.loads(path.read_text()).get("chiSiamo") or {}

    # ── 1. la rotta: una pagina vera, non un redirect ────────────────

    def test_sw3_rotta_monta_la_pagina_vera(self):
        app = (FRONTEND_SRC / "App.js").read_text()
        assert 'path="/chi-siamo" element={<ChiSiamoPage />}' in app, \
            "/chi-siamo deve montare la pagina, non un Navigate"
        assert "features/network/ChiSiamoPage" in app, "manca l'import lazy"
        # LC8 — mirata alla rotta: un divieto globale su qualunque
        # Navigate verso /manifesto bloccava anche il gate LC2 di
        # /come-funziona, che al Manifesto ci manda apposta.
        assert 'path="/chi-siamo" element={<Navigate' not in app, \
            "regressione: il redirect /chi-siamo → /manifesto e' tornato"
        # la rotta OMONIMA degli store non si tocca: e' un'altra cosa
        assert 'path="/s/:slug/chi-siamo"' in app, \
            "regressione: sparita la rotta store /s/:slug/chi-siamo"
        assert self.PAGE.exists(), "la pagina non esiste"
        # e il footer di fase rete continua a linkarla
        shell = (FRONTEND_SRC / "features" / "storefront" / "components"
                 / "MarketplaceShell.jsx").read_text()
        assert 'data-testid="footer-nw-chisiamo"' in shell
        assert 'to="/chi-siamo"' in shell

    def test_sw3_vecchia_pagina_rimossa_niente_codice_morto(self):
        """Non restano due Chi siamo: la pagina 2025 e' sparita, e con
        lei le chiavi di copy che serviva solo a lei."""
        assert not self.VECCHIA.exists(), \
            "AboutAuryaPage.js e' ancora nel repo: due pagine simili"
        import json
        # LC8 — brand v3 (2/8) ha ripopolato aboutPage con il copy
        # nuovo, SOLO in italiano (fallbackLng='it'): seoTitle/seoDesc
        # sono tornate vive, e la parita' x4 non e' piu' richiesta.
        # Restano morte le chiavi della pagina 2025.
        about = json.loads((FRONTEND_SRC / "locales" / "it"
                            / "landings.json").read_text())["aboutPage"]
        for morta in ("intro", "missionTitle", "missionBody",
                      "visionTitle", "visionBody", "forSeekersTitle",
                      "forOrganizersTitle", "cta"):
            assert morta not in about, \
                f"[it] chiave morta superstite: aboutPage.{morta}"
        # le chiavi che la pagina usa oggi devono esserci
        for viva in ("title", "facesAlt", "seoTitle", "seoDesc"):
            assert about.get(viva), f"[it] persa aboutPage.{viva}"

    # ── 2. l'apertura: le tre negazioni ──────────────────────────────

    def test_sw3_apertura_tre_negazioni(self):
        """Brand v3 (2/8, riscrittura founder) + LC4/LC6 — la guardia
        era rimasta al copy SW3: le tre negazioni in apertura non
        esistono piu' (definirsi per sottrazione e' uscito dalla voce
        del brand, vedi anche la landing professionisti). Oggi
        l'apertura e' una domanda: un solo h1, la domanda in corsivo
        subito sotto, e mai piu' negazioni identitarie nel copy."""
        src = self._page()
        assert src.count('as="h1"') == 1, "l'h1 e' uno solo"
        assert 'id="cs-open-title"' in src, "sparita l'apertura"
        assert "domanda" in src, "l'apertura e' la domanda, non un elenco"
        assert "Non siamo un" not in self._copy(), \
            "le negazioni identitarie sono tornate in Chi siamo"

    # ── 3. i ritratti: soltanto fatti reali ──────────────────────────

    def test_sw3_ritratti_solo_fatti_reali(self):
        """Valentina e Davide raccontati col materiale verificato dei
        fondatori: nessun titolo, premio o data inventata.
        CS2b (7/8) — i ritratti sono tornati al testo che il founder
        aveva scritto per il sito precedente, ripreso alla lettera: i
        fatti oggi sono Reiki di terzo livello, tarocchi e oracoli e
        mappe natali per Valentina, il mondo digitale per Davide. La
        regola che non cambia e' NIENTE biografia gonfiata: nessun
        titolo, premio o data inventata (le assert sotto)."""
        import re
        src = self._page()
        for fatto in ("Reiki", "tarocchi", "mappe natali",
                      "mondo digitale"):
            assert fatto in src, f"fatto reale mancante nei ritratti: {fatto}"
        # la foto vera, con l'alt riusato (nessun alt nuovo)
        assert "/media/chisiamo-aurya.jpg" in src, "manca la foto vera"
        assert "aboutPage.facesAlt" in src, "l'alt della foto va riusato"
        blocco = src[src.index('data-testid="cs-paths"'):]
        assert 'grayscale' not in blocco, \
            "la fotografia va lasciata com'e': niente filtri"
        # niente biografia gonfiata: date, anni, numeri di clienti
        copy = self._copy()
        assert not re.search(r"\b(19|20)\d{2}\b", copy), \
            "nessuna data va inventata nei ritratti"
        for inventato in ("fondata nel", "da oltre", "premio", "certificat",
                          "master", "clienti soddisfatti", "esperti"):
            assert inventato.lower() not in copy.lower(), \
                f"fatto non verificato nel copy: '{inventato}'"

    # ── 4. la teoria si indica, non si riscrive ──────────────────────

    def test_sw3_teoria_indicata_e_manifesto_non_duplicato(self):
        """LC8 — brand v3 ha tolto la citazione letterale della teoria
        (la pagina oggi racconta le persone, non la posizione): quello
        che NON deve regredire e' la separazione dei compiti — il
        Manifesto non si ricopia in Chi siamo — e la disciplina tonale
        (una sola ancora verde)."""
        src = self._page()
        copy = self._copy()
        for pezzo_di_manifesto in ("Cosa non faremo mai", "Il mondo come lo vediamo",
                                   "Non venderemo posizioni in classifica",
                                   "Verificato Aurya"):
            assert pezzo_di_manifesto not in copy, \
                f"il Manifesto non si duplica qui: '{pezzo_di_manifesto}'"
        # una sola ancora tonale in tutta la pagina
        assert src.count('tone="sage"') == 1, \
            "Chi siamo ha UNA ancora verde, non di piu'"

    # ── 5. la chiusura: manifesto e mail ─────────────────────────────

    def test_sw3_chiusura_doppia_cta_discreta(self):
        """LC8 — la chiusura brand v3 (cs-together) ha TRE porte:
        Magazine (l'unica cosa gia' viva, solid), professionisti e
        Lettera (quiet, aggiunta in LC6). E il canale diretto resta:
        la mail scritta per esteso, cliccabile come mailto."""
        src = self._page()
        blocco = src[src.index('data-testid="cs-together"'):]
        for porta in ("cs-cta-magazine", "cs-cta-pro", "cs-cta-letter"):
            assert f'data-testid="{porta}"' in blocco, \
                f"manca la porta {porta} nella chiusura"
        assert 'to="/newsletter"' in blocco, \
            "la porta Lettera deve portare a /newsletter"
        # la mail vera (dalla costante di brand), visibile e cliccabile
        assert "href={`mailto:${BRAND_EMAIL}`}" in blocco, \
            "la mail deve aprire un mailto vero"
        brand = (FRONTEND_SRC / "config" / "brand.js").read_text()
        assert f"'{self.MAIL}'" in brand, \
            f"BRAND_EMAIL non e' piu' {self.MAIL}"

    # ── 6. SEO e i18n x4 ─────────────────────────────────────────────

    def test_sw3_seo_e_i18n_x4(self):
        """LC8 — il copy brand v3 vive in `aboutPage`, SOLO italiano
        (decisione founder 2/8, fallbackLng='it'): niente parita' x4.
        La guardia pretende l'italiano completo, la description entro
        il taglio Google e il brand nel title."""
        import json
        src = self._page()
        assert "'Chi siamo | Aurya'" in src, "title della pagina sbagliato"
        assert "canonicalPath: '/chi-siamo'" in src
        it = json.loads((FRONTEND_SRC / "locales" / "it"
                         / "landings.json").read_text())["aboutPage"]
        assert len(it) >= 40, f"chiavi aboutPage in italiano: {len(it)}"
        for k, v in it.items():
            assert v and v.strip(), f"[it] aboutPage.{k} vuota"
        desc = it.get("seoDesc") or ""
        assert 0 < len(desc) <= 158, \
            f"[it] description da {len(desc)} caratteri, taglio 158"
        assert "Aurya" in (it.get("seoTitle") or ""), "[it] title senza brand"
        # i defaultValue inline sono l'italiano vero, non una variante
        for k, v in it.items():
            if f"aboutPage.{k}" in src and f"'{v}'" not in src:
                # apostrofo tipografico vs dritto: confronto tollerante
                assert v.replace("’", "'") in src.replace("’", "'"), \
                    f"defaultValue di aboutPage.{k} diverso dall'italiano"

    # ── 7. il lessico del Blueprint ──────────────────────────────────

    # LC8 — le negazioni sono uscite dal copy (brand v3): niente piu'
    # eccezioni, il lessico vietato vale su tutto. "piattaforma" resta
    # ammessa nell'unico punto in cui e' una smentita voluta del copy
    # founder ("Non come una piattaforma. / Come un ponte.").
    _VIETATE = ("marketplace", "gestionale",
                "trasforma la tua vita", "ritrova te stesso",
                "gratuit", "gratis", "kostenlos", "free of charge")

    def test_sw3_parole_vietate_e_trattini_lunghi(self):
        import json, re
        copy = self._copy().replace("MarketplaceShell", "")
        # le smentite volute del copy founder non contano come uso
        for smentita in ("Non come una piattaforma.",
                         "Non abbiamo creato Aurya per lanciare una piattaforma."):
            copy = copy.replace(smentita, "")
        # CS2b (7/8) — ECCEZIONE DICHIARATA, decisione del founder: il
        # ritratto di Davide e' ripreso alla lettera dal sito
        # precedente e dice "costruendo piattaforme". Qui la parola non
        # descrive Aurya (che due sezioni sopra si nega come
        # piattaforma) ma il mestiere di una persona, ed e' l'unico
        # punto in cui e' ammessa in positivo. Se il copy di Davide
        # cambia, questa riga va tolta, non allargata.
        copy = copy.replace(
            "costruendo piattaforme capaci di connettere le persone.", "")
        for vietata in self._VIETATE + ("directory", "piattaform"):
            assert vietata.lower() not in copy.lower(), \
                f"parola vietata nel sorgente di Chi siamo: '{vietata}'"
        it = json.loads((FRONTEND_SRC / "locales" / "it"
                         / "landings.json").read_text())["aboutPage"]
        for chiave, valore in it.items():
            for vietata in self._VIETATE:
                assert vietata.lower() not in valore.lower(), \
                    f"[it] aboutPage.{chiave} usa '{vietata}'"
            assert "—" not in valore and "–" not in valore, \
                f"[it] trattino lungo in aboutPage.{chiave}"
        # zero trattini lunghi anche nel copy inline
        defaults = re.findall(r"defaultValue:\s*(?:'([^']*)'|\"([^\"]*)\")",
                              self._page())
        valori = [a or b for a, b in defaults]
        assert len(valori) >= 15, \
            f"i defaultValue di Chi siamo sono {len(valori)}, attesi almeno 15"
        for val in valori:
            assert "—" not in val and "–" not in val, \
                f"trattino lungo nel copy di Chi siamo: {val[:40]}"


class TestMagazineSw4:
    """SW4 (31/7/2026) — il Magazine: l'indice nel kit editoriale e le
    copertine senza titolo stampato
    (docs/SITO_REDESIGN_PIANO_2026-07.md).

    Due difetti chiusi insieme, perche' erano lo stesso difetto visto
    da due lati. L'indice /blog era rimasto alla grammatica vecchia
    (hero fotografico generico, card con bordo e bottone "Leggi")
    mentre home, Manifesto e Chi siamo parlavano gia' il kit. E la
    cover autogenerata stampava il TITOLO dentro l'immagine: nella
    scheda grande il titolo compariva due volte (immagine + h3) e
    nelle miniature da 128 px diventava un intrico illeggibile.

    Queste guardie difendono: l'apertura nella voce (il dispositivo a
    coppia del Blueprint cap. 9), il kit al posto degli stili di
    pagina, i filtri come chip-link sobri, gli stati vuoti onesti, il
    lessico, l'i18n x4, e dal lato backend il fatto che il generatore
    NON disegni piu' il titolo ma disegni ancora la categoria.
    """

    PAGE = FRONTEND_SRC / "features" / "storefront" / "BlogIndexPage.js"
    COVER = BACKEND_DIR / "services" / "article_cover.py"
    LOCALES = ("it", "en", "de", "fr")

    def _page(self):
        return self.PAGE.read_text()

    def _copy(self):
        """Il sorgente senza commenti: le guardie lessicali giudicano
        quello che il lettore puo' vedere, non le note di lavoro."""
        import re
        src = re.sub(r"/\*.*?\*/", "", self._page(), flags=re.DOTALL)
        return re.sub(r"^\s*//.*$", "", src, flags=re.MULTILINE)

    def _blocco(self, lang):
        import json
        path = FRONTEND_SRC / "locales" / lang / "landings.json"
        return json.loads(path.read_text()).get("blog") or {}

    # ── 1. l'indice parla il kit editoriale ──────────────────────────

    def test_sw4_indice_sul_kit_editoriale(self):
        """Stessi mattoni di home, Manifesto e Chi siamo: nessuno
        stile di pagina, nessuna card promozionale superstite."""
        src = self._page()
        assert "from '../../components/editorial'" in src, \
            "l'indice non importa il kit editoriale"
        for mattone in ("Section", "DisplayTitle", "TitleLine", "Lede",
                        "ArticleCard"):
            assert mattone in src, f"il kit non usa {mattone}"
        # l'apertura grande + la griglia: la gerarchia della rivista
        assert "variant=\"lead\"" not in src, \
            "il variant della scheda passa dal helper, non a mano"
        assert "'lead'" in src and "'compact'" in src, \
            "servono l'articolo di apertura e i secondari"
        # la roba vecchia e' uscita davvero
        # `hero-blog.webp` e `text-hero-shadow` sono usciti da questo
        # elenco: non sono residui della pagina vecchia, li ha aggiunti
        # DS3 di proposito (l'apertura fotografica del Magazine e
        # l'ombra che tiene leggibile il titolo sulla foto). Una guardia
        # che vieta una decisione presa dopo di lei non protegge niente.
        for morto in ("rounded-2xl border border-gray-200",
                      "hover:shadow-md", "CATEGORY_TONES", "blog.readMore"):
            assert morto not in src, f"residuo della pagina vecchia: {morto}"
        # i fondi: crema, bianco, sabbia. Nessuna ancora verde piena.
        assert 'tone="cream"' in src and 'tone="paper"' in src
        assert 'tone="sage"' not in src, \
            "niente fascia verde: il verde e' nelle copertine"

    def test_sw4_apertura_dispositivo_a_coppia(self):
        """Titolo nuovo: una verita' sul mondo, poi il nostro gesto.
        Due <TitleLine>, un solo h1, e la riga su cosa ci trovi."""
        src = self._page()
        # MG3 — il testo del titolo vive in i18n e cambia: la guardia
        # controlla il DISPOSITIVO (due meta', in quest'ordine), non le
        # parole. Una guardia sulle parole si rompe a ogni revisione di
        # copy e insegna a disattivarla.
        assert "blog.lead1" in src, "manca la prima meta' del dispositivo"
        assert "blog.lead2" in src, "manca il gesto"
        assert src.index("blog.lead1") < src.index("blog.lead2"), \
            "mai l'ordine inverso: se si parte da noi diventa pubblicita'"
        assert self._copy().count("<TitleLine>") == 2, \
            "il titolo e' due frasi, non un a-capo estetico"
        # MG1 — nel sorgente gli h1 sono DUE perche' sono i due rami di
        # un ternario: l'indice porta la coppia sulla fotografia, la
        # pagina di categoria il nome della categoria in una testata
        # compatta. A schermo ne renderizza sempre uno solo — verificato
        # nel browser su /blog e su /blog/categoria/yoga.
        assert src.count('as="h1"') == 2, \
            "i rami dell'apertura sono due: indice e categoria"
        assert src.count('id="mag-title"') == 2, \
            "entrambi i rami portano l'id che labella l'apertura"
        # il vecchio titolo generico e' uscito dall'apertura
        assert "blog.title" not in src, \
            "l'apertura non usa piu' il titolo generico 'Il Magazine di Aurya'"
        # cosa ci trovi
        assert "blog.subtitle" in src

    def test_sw4_chip_sobri_e_rotta_vera(self):
        """MG1 — i filtri hanno cambiato vestito, non natura: da fila di
        pastiglie testuali a schede colorate col segno della categoria
        (MagazineCategoryNav). Con dodici categorie una fila di parole
        costringeva a leggerle tutte per trovarne una.

        Quello che deve restare vero e' quello che la guardia proteggeva
        davvero: la categoria e' una ROTTA indicizzabile e non un
        bottone che naviga, e quella corrente si dice anche a chi
        ascolta."""
        nav = (FRONTEND_SRC / "features" / "storefront" / "components"
               / "MagazineCategoryNav.jsx").read_text()
        assert "`/blog/categoria/${slug}`" in nav, \
            "la scheda deve essere un link alla rotta di categoria"
        assert "useNavigate" not in nav, \
            "niente navigate() nei filtri: sono link"
        assert "aria-current" in nav, \
            "la categoria corrente va detta anche a chi ascolta"
        assert 'data-testid="mag-cat-nav"' in nav
        assert 'data-testid="mag-cat-card"' in nav

    def test_sw4_stati_vuoti_onesti(self):
        """Nessuna promessa nel vuoto: si dice che non c'e' niente,
        non che 'le storie stanno arrivando'."""
        src = self._page()
        assert "blog.emptyCat" in src, \
            "la pagina di categoria vuota ha il suo messaggio"
        it = self._blocco("it")
        for chiave in ("empty", "emptyCat"):
            testo = it[chiave]
            for promessa in ("stanno arrivando", "presto", "a breve",
                            "in arrivo"):
                assert promessa not in testo.lower(), \
                    f"blog.{chiave} promette invece di constatare: '{promessa}'"
        # la promessa BN3 resta visibile in lista
        assert 'data-testid="blog-card-gated"' in src, \
            "regressione BN3: il badge 'Per gli iscritti' e' sparito dalla lista"
        kit = (FRONTEND_SRC / "components" / "editorial"
               / "ArticleCard.jsx").read_text()
        assert "badge" in kit, "lo slot del badge vive nel kit, non nella pagina"

    # ── 2. le copertine: un segno, non un manifesto ──────────────────

    def test_sw4_cover_non_stampa_il_titolo(self):
        """La guardia centrale dell'onda: il generatore non disegna
        piu' testo del titolo, ne' direttamente ne' via wrapping."""
        src = self.COVER.read_text()
        assert "_wrap_title" not in src, \
            "il wrapping del titolo e' ancora li': la cover lo stampa"
        assert "PlayfairDisplay" not in src, \
            "il font del titolo non serve piu' alla cover"
        # nessun draw.text riceve il titolo
        import re
        for chiamata in re.findall(r"draw\.text\(([^\n]*)", src):
            assert "title" not in chiamata, \
                f"draw.text stampa ancora il titolo: {chiamata[:60]}"
        # e il chiamante non glielo passa nemmeno
        router = (BACKEND_DIR / "routers" / "articles.py").read_text()
        assert "render_article_cover, None," in router, \
            "il router passa ancora il titolo al generatore"

    def test_sw4_cover_dice_la_categoria(self):
        """Quello che resta dentro l'immagine: il segno della
        categoria, il suo nome e la firma. Ogni categoria del Magazine
        (anche quelle editoriali) ha palette e geometria proprie."""
        from models.article import ARTICLE_CATEGORIES
        from services.article_cover import (EDITORIAL_GEOMETRY,
                                            EDITORIAL_PALETTES,
                                            _geo_aura, geometry_for,
                                            palette_for)
        src = self.COVER.read_text()
        assert "category_label or BRAND_NAME" in src, \
            "il nome della categoria deve stare nella cover"
        assert "A U R Y A" in src, "la firma resta"
        assert set(EDITORIAL_PALETTES) == set(EDITORIAL_GEOMETRY)
        segni = set()
        for slug in ARTICLE_CATEGORIES:
            assert palette_for(slug) is not None
            geo = geometry_for(slug)
            assert geo is not _geo_aura, \
                f"la categoria '{slug}' cade sul segno di ripiego"
            segni.add(geo.__name__)
        assert len(segni) == len(ARTICLE_CATEGORIES), \
            "due categorie condividono lo stesso segno"

    def test_sw4_cover_resta_og_perfetta(self):
        """1200x630 WebP: la misura che og:image vuole. Li' il titolo
        non serve, lo stampa la card social."""
        from io import BytesIO

        from PIL import Image
        from services.article_cover import render_article_cover
        data = render_article_cover(None, "operatori", "Per gli operatori")
        assert data and data[:4] == b"RIFF"
        assert Image.open(BytesIO(data)).size == (1200, 630)
        # og:image dell'articolo = la sua cover, senza ritocchi
        shell = (BACKEND_DIR / "routers" / "seo_shell.py").read_text()
        assert '_abs_image(doc.get("featured_image_url"))' in shell, \
            "og:image dell'articolo non e' piu' la copertina"

    # ── 3. lessico e i18n x4 ─────────────────────────────────────────

    _VIETATE = ("marketplace", "directory", "gestionale", "piattaform",
                "trasforma la tua vita", "ritrova te stesso",
                "gratuit", "gratis", "kostenlos", "free of charge")

    def test_sw4_parole_vietate_e_trattini_lunghi(self):
        import re
        copy = self._copy().replace("MarketplaceShell", "")
        for vietata in self._VIETATE:
            assert vietata.lower() not in copy.lower(), \
                f"parola vietata nel sorgente dell'indice: '{vietata}'"
        for lang in self.LOCALES:
            for chiave, valore in self._blocco(lang).items():
                for vietata in self._VIETATE:
                    assert vietata.lower() not in valore.lower(), \
                        f"[{lang}] blog.{chiave} usa '{vietata}'"
                assert "—" not in valore and "–" not in valore, \
                    f"[{lang}] trattino lungo in blog.{chiave}"
        defaults = re.findall(r"defaultValue:\s*(?:'([^']*)'|\"([^\"]*)\")",
                              self._page())
        valori = [a or b for a, b in defaults]
        assert len(valori) >= 10, \
            f"i defaultValue dell'indice sono {len(valori)}, attesi almeno 10"
        for val in valori:
            assert "—" not in val and "–" not in val, \
                f"trattino lungo nel copy del Magazine: {val[:40]}"

    def test_sw4_i18n_x4(self):
        """MG3 — la guardia chiedeva le chiavi del Magazine in tutte e
        quattro le lingue. Dal 2/8/2026 il sito pubblico e' SOLO
        ITALIANO (decisione del founder): i contenuti nuovi non si
        traducono piu' x4, e pretendere la parita' significava tenere la
        suite rossa per abitudine — che e' il modo migliore per smettere
        di leggerla.

        Resta il controllo che conta: l'italiano e' completo e nessuna
        sua voce e' vuota. Se un giorno torna il multilingua, il ciclo
        di lavoro parte da qui."""
        src = self._page()
        it = self._blocco("it")
        for chiave in ("eyebrow", "lead1", "lead2", "subtitle",
                       "catSubtitle", "moreTitle", "empty", "emptyCat",
                       "gatedBadge", "allArticles"):
            assert it.get(chiave), f"[it] blog.{chiave} mancante"
        for k, v in it.items():
            assert v and v.strip(), f"[it] blog.{k} vuota"
        # i defaultValue inline sono l'italiano vero, non una variante
        for k, v in it.items():
            if f"blog.{k}" in src:
                assert v in src, \
                    f"defaultValue di blog.{k} diverso dall'italiano"


class TestReteSw5:
    """SW5 (31/7/2026) — /operatori diventa "Le persone"
    (docs/SITO_REDESIGN_PIANO_2026-07.md, AURYA_BLUEPRINT cap. 2 e 9).

    La pagina passa dallo schema "elenco con criteri" allo schema del
    Blueprint: schede grandi con foto, nome, pratica, luogo e UNA
    citazione presa dall'intervista. Per farlo servivano i due campi
    che mancavano nel payload pubblico, e sono il cuore di queste
    guardie:

      quote     scelta A MANO dal system admin nell'editor
                dell'intervista (public_profile.interview_quote), MAI
                estratta in automatico. Esce in pubblico solo con
                l'intervista pubblicata: una frase presa da
                un'intervista non pubblica sarebbe una perdita.
      category  la pratica, derivata dai prodotti pubblicati dell'org
                come fa /operators. Una stringa sola (la piu'
                frequente) o niente, e SEMPRE con una sola aggregate
                su tutti gli org_ids: mai una query per organizzazione.

    Piu' le guardie della pagina: i criteri di ingresso riscritti come
    GESTI (non come requisiti del lettore), il kit editoriale al posto
    degli stili a mano, lo stato vuoto onesto, il lessico e l'i18n x4.
    """

    PAGE = FRONTEND_SRC / "features" / "network" / "NetworkOperatorsPage.js"
    CARD = FRONTEND_SRC / "components" / "editorial" / "PersonCard.jsx"
    TAB = FRONTEND_SRC / "features" / "admin" / "InterviewsTab.js"
    LOCALES = ("it", "en", "de", "fr")
    SLUG = "masseria-demo"
    QUOTE_MAX = 280

    UA = {"User-Agent": "Mozilla/5.0 (Macintosh) Chrome/126 Safari/537.36"}

    # ── infrastruttura: si riusa quella di PV2, stessa area ──────────

    # LC8 — LC3 ha tolto network_member alle org demo, quindi la rete
    # pubblica e' (giustamente) vuota. Queste guardie pero' esercitano
    # comportamento vero (gate della quote, category derivata, limite
    # 280) e hanno bisogno di UN membro: si accende il flag sulla demo
    # per la durata della classe e lo si spegne alla fine — il sito
    # pubblico non lo vede mai, i test si'.
    @classmethod
    def setup_class(cls):
        cls._orgs = _pv7_live_db()["organizations"]
        cls._orgs.update_one({"public_slug": cls.SLUG},
                             {"$set": {"network_member": True}})

    @classmethod
    def teardown_class(cls):
        cls._orgs.update_one({"public_slug": cls.SLUG},
                             {"$unset": {"network_member": ""}})

    def _member_row(self):
        r = requests.get(f"{BASE_URL}/api/public/network/members",
                         headers=self.UA, timeout=10)
        assert r.status_code == 200, r.text
        rows = [m for m in r.json()["items"] if m["slug"] == self.SLUG]
        assert rows, "l'org demo non e' fra i membri della rete"
        return rows[0]

    def _page(self):
        return self.PAGE.read_text()

    def _copy(self):
        """Il sorgente senza commenti: le guardie lessicali giudicano
        quello che il lettore puo' vedere, non le note di lavoro."""
        import re
        src = re.sub(r"/\*.*?\*/", "", self._page(), flags=re.DOTALL)
        return re.sub(r"^\s*//.*$", "", src, flags=re.MULTILINE)

    def _blocco(self, lang):
        import json
        path = FRONTEND_SRC / "locales" / lang / "landings.json"
        return json.loads(path.read_text()).get("nwOps") or {}

    # ── 1. la citazione esce SOLO a intervista pubblicata ────────────

    def test_sw5_quote_solo_a_intervista_pubblicata(self):
        P = TestProfiloPv2
        sys_h = P._sys_headers()
        org_id = P._org_id()
        db = P._db()
        snap = P._snapshot_interview(db, org_id)
        url = f"{BASE_URL}/api/admin/organizations/{org_id}/interview"
        frase = "Guardia SW5: una frase sola, scelta a mano."
        body = {"items": [{"question": "Guardia SW5?",
                           "answer": "Risposta integrale SW5."}],
                "quote": frase, "published": False}
        try:
            # BOZZA: la citazione e' salvata ma il pubblico non la vede
            r = requests.put(url, headers=sys_h, json=body, timeout=10)
            assert r.status_code == 200, r.text
            assert r.json()["quote"] == frase
            row = self._member_row()
            assert row["has_interview"] is False
            assert row["quote"] is None, \
                "citazione trapelata da un'intervista NON pubblicata"

            # PUBBLICATA: esce, identica a come e' stata scritta
            body["published"] = True
            r = requests.put(url, headers=sys_h, json=body, timeout=10)
            assert r.status_code == 200, r.text
            row = self._member_row()
            assert row["has_interview"] is True
            assert row["quote"] == frase

            # SPUBBLICATA: rientra, insieme all'intervista
            body["published"] = False
            r = requests.put(url, headers=sys_h, json=body, timeout=10)
            assert r.status_code == 200
            assert self._member_row()["quote"] is None
        finally:
            P._restore_interview(db, org_id, snap)

    # ── 2. senza citazione la scheda non si rompe ────────────────────

    def test_sw5_quote_assente_se_non_impostata(self):
        """Il campo c'e' SEMPRE nel payload (additivo, mai mancante) e
        vale None quando nessuno ha scelto una frase: la scheda ripiega
        sulla tagline, non su un buco."""
        P = TestProfiloPv2
        sys_h = P._sys_headers()
        org_id = P._org_id()
        db = P._db()
        snap = P._snapshot_interview(db, org_id)
        url = f"{BASE_URL}/api/admin/organizations/{org_id}/interview"
        try:
            r = requests.put(url, headers=sys_h, json={
                "items": [{"question": "Guardia SW5 senza frase?",
                           "answer": "Nessuna citazione scelta."}],
                "published": True}, timeout=10)
            assert r.status_code == 200, r.text
            assert r.json()["quote"] is None
            row = self._member_row()
            assert "quote" in row, "campo quote sparito dal payload"
            assert row["quote"] is None
            assert row["has_interview"] is True

            # stringa vuota e soli spazi valgono "nessuna citazione"
            for vuota in ("", "   \n  "):
                r = requests.put(url, headers=sys_h, json={
                    "items": [{"question": "Q", "answer": "A"}],
                    "quote": vuota, "published": True}, timeout=10)
                assert r.status_code == 200
                assert r.json()["quote"] is None, repr(vuota)
        finally:
            P._restore_interview(db, org_id, snap)

    # ── 3. il tetto dei 280 caratteri ────────────────────────────────

    def test_sw5_quote_limite_280_caratteri(self):
        """Una citazione e' una frase. Oltre il tetto viene tagliata dal
        backend, non lasciata passare: la scheda deve reggere anche se
        qualcuno incolla una risposta intera."""
        P = TestProfiloPv2
        sys_h = P._sys_headers()
        org_id = P._org_id()
        db = P._db()
        snap = P._snapshot_interview(db, org_id)
        url = f"{BASE_URL}/api/admin/organizations/{org_id}/interview"
        lunga = "x" * 400
        try:
            r = requests.put(url, headers=sys_h, json={
                "items": [{"question": "Q", "answer": "A"}],
                "quote": f"  {lunga}  ", "published": True}, timeout=10)
            assert r.status_code == 200, r.text
            salvata = r.json()["quote"]
            assert len(salvata) == self.QUOTE_MAX
            assert salvata == "x" * self.QUOTE_MAX     # .strip() prima del taglio
            assert len(self._member_row()["quote"]) == self.QUOTE_MAX
        finally:
            P._restore_interview(db, org_id, snap)
        # e il tetto e' lo stesso nei due posti che lo devono sapere
        admin_src = (BACKEND_DIR / "routers" / "admin.py").read_text()
        assert f"_INTERVIEW_QUOTE_MAX = {self.QUOTE_MAX}" in admin_src
        assert f"MAX_QUOTE = {self.QUOTE_MAX}" in self.TAB.read_text(), \
            "l'editor admin non conosce lo stesso tetto del backend"

    # ── 4. il PUT salva e il GET rilegge ─────────────────────────────

    def test_sw5_quote_salvata_e_riletta_dal_get_admin(self):
        P = TestProfiloPv2
        sys_h = P._sys_headers()
        org_id = P._org_id()
        db = P._db()
        snap = P._snapshot_interview(db, org_id)
        url = f"{BASE_URL}/api/admin/organizations/{org_id}/interview"
        frase = "La fiducia non si dichiara: si lascia verificare."
        try:
            r = requests.put(url, headers=sys_h, json={
                "items": [{"question": "Q", "answer": "A"}],
                "quote": frase, "published": False}, timeout=10)
            assert r.status_code == 200, r.text
            r = requests.get(url, headers=sys_h, timeout=10)
            assert r.status_code == 200
            assert r.json()["quote"] == frase
            # e vive dentro public_profile: nessuna migrazione
            org = db.organizations.find_one({"id": org_id},
                                            {"public_profile": 1})
            assert (org["public_profile"]["interview_quote"]) == frase
        finally:
            P._restore_interview(db, org_id, snap)
        # l'editor admin la manda SEMPRE: ometterla equivarrebbe a
        # cancellarla al primo salvataggio di bozza
        api_src = (FRONTEND_SRC / "api" / "admin.js").read_text()
        assert "items, video_url, quote, published" in api_src
        tab = self.TAB.read_text()
        assert "interview-quote-input" in tab
        assert "quote: (quote || '').trim() || null" in tab
        assert "setQuote(data.quote || '')" in tab

    # ── 5. la pratica derivata ───────────────────────────────────────

    def test_sw5_category_derivata_dai_prodotti_pubblicati(self):
        """Stessa fonte di /operators (prodotti pubblicati e attivi),
        ma UNA sola stringa: la piu' frequente, con l'ordine alfabetico
        come spareggio stabile."""
        P = TestProfiloPv2
        db = P._db()
        org_id = P._org_id()
        conteggi = {}
        for p in db.products.find({"organization_id": org_id,
                                   "is_published": True, "is_active": True},
                                  {"category": 1}):
            cat = p.get("category")
            if cat:
                conteggi[cat] = conteggi.get(cat, 0) + 1
        attesa = (min(conteggi.items(), key=lambda kv: (-kv[1], kv[0]))[0]
                  if conteggi else None)
        row = self._member_row()
        assert "category" in row, "campo category sparito dal payload"
        assert row["category"] == attesa, \
            f"pratica derivata {row['category']!r}, attesa {attesa!r}"
        assert row["category"] is None or isinstance(row["category"], str)

    def test_sw5_category_una_sola_aggregate_mai_per_org(self):
        """La derivazione NON puo' costare una query per organizzazione:
        il corpo dell'endpoint fa aggregate solo prima del ciclo, e
        sempre con $in su tutti gli org_ids."""
        src = (BACKEND_DIR / "routers" / "public.py").read_text()
        start = src.index("async def public_network_members(")
        corpo = src[start:src.index("@router.get(\"/operators\")", start)]
        assert corpo.count("products_collection.aggregate(") == 2, \
            "il numero di aggregate dell'endpoint e' cambiato"
        ciclo = corpo[corpo.index("    items = []"):]
        for vietata in ("aggregate(", "find_one(", "await organizations_collection",
                        ".find("):
            assert vietata not in ciclo, \
                f"query dentro il ciclo per organizzazione: {vietata}"
        assert corpo.count('{"$in": org_ids}') >= 3, \
            "un'aggregate non filtra su tutti gli org_ids insieme"

    # ── 6. la pagina: kit editoriale, schede grandi, niente elenco ───

    def test_sw5_pagina_usa_il_kit_e_le_schede_grandi(self):
        src = self._page()
        assert "components/editorial" in src, "il kit editoriale non e' importato"
        # LC8 — brand v3: TitleLine e' uscito (titoli a frase unica).
        # Founder 26/8: col layout a righe grandi e' uscita anche la
        # Quote DALLA PAGINA — la voce vive dentro PersonCard, che e'
        # l'unico posto dove le persone si mostrano. Il resto del kit
        # resta il dispositivo da difendere.
        for pezzo in ("Section", "DisplayTitle", "Lede",
                      "PersonCard", "EditorialCta"):
            assert pezzo in src, f"manca dal kit: {pezzo}"
        assert src.count('as="h1"') == 1, "l'h1 e' uno solo"
        # la citazione e la pratica arrivano davvero dal payload nuovo
        assert "m.category" in src, "la pratica non viene passata alla scheda"
        card = self.CARD.read_text()
        assert "Quote" in card, "la voce della scheda e' sparita dal kit"
        assert "quote" in card and "category" in card
        # niente vestito fatto a mano: era il difetto della pagina vecchia
        for vecchio in ("bg-gradient-sidebar", "rounded-2xl border",
                        "lucide-react", "text-xs text-gray-600"):
            assert vecchio not in src, f"stile della pagina vecchia: {vecchio}"
        # e nemmeno una vetrina: qui non si vendono servizi
        for commercio in ("price_from", "services_count", "priceFrom"):
            assert commercio not in src, \
                f"la pagina della rete mostra di nuovo il listino: {commercio}"
        # una sola ancora verde, e in chiusura
        assert src.count('tone="sage"') == 1

    def test_sw5_criteri_riscritti_come_gesti(self):
        """LC8 — brand v3 e' andata oltre SW5: la sezione criteri e'
        SPARITA del tutto ('criterio invisibile', niente regolamento;
        le chiavi nwOps.how* sono state rimosse dal locale). Quello che
        non deve regredire: mai requisiti del lettore, mai un elenco
        numerato di condizioni, e mai giudizi proclamati. La crescita
        si racconta come gesto nostro ('una persona alla volta')."""
        # _copy(): il commento di testa RACCONTA la rimozione di
        # nwOps.how* e citarla non e' reintrodurla
        src = self._copy()
        for requisito in ("nwOps.c1", "nwOps.c2", "nwOps.c3",
                          "criteriaTitle", "Con che criterio",
                          "Una pratica reale", "La disponibilità a raccontarsi",
                          "padStart", "nwOps.how"):
            assert requisito not in src, f"requisito superstite: {requisito}"
        it = self._blocco("it")
        for chiave in ("growTitle", "growP1", "growP2"):
            assert it.get(chiave), f"manca il racconto nwOps.{chiave}"
        assert "una persona alla volta" in it["growTitle"].lower()
        # e nessun giudizio proclamato (Blueprint cap. 2.3)
        for giudizio in ("i migliori", "selezioniamo", "selezionati",
                         "solo i più", "eccellenza"):
            assert giudizio.lower() not in self._copy().lower(), \
                f"il criterio si proclama: '{giudizio}'"

    def test_sw5_stato_vuoto_onesto_e_griglia_che_regge(self):
        """Con poche persone la pagina non deve sembrare rotta, e senza
        nessuna non deve sembrare in errore.
        LC8 — brand v3: lo stato vuoto e' il pannello salvia 'In
        arrivo' (nw-people-soon) con la CTA Lettera — verificato in
        pagina dopo LC3, quando la rete e' rimasta davvero vuota.
        Founder 26/8, coi primi profili VERI in produzione: il layout
        a righe grandi (few) e' morto sul campo — ritratti enormi e,
        con object-contain, ognuno del suo formato. La griglia e' UNA,
        uniforme, fino a 4 colonne su desktop, e le schede hanno un
        formato unico (4/5, cover ancorato in alto)."""
        src = self._page()
        assert 'data-testid="nw-people-soon"' in src, \
            "manca il pannello d'attesa dello stato vuoto"
        assert "nwOps.soonTitle" in src and "nwOps.letterCta" in src, \
            "lo stato vuoto deve dire cosa succede e offrire la Lettera"
        assert "members === null" in src, "lo stato di caricamento e' sparito"
        assert "list.length === 0" in src, "il ramo vuoto e' sparito"
        assert "few ?" not in src, \
            "il layout a righe grandi e' tornato (founder 26/8: griglia unica)"
        assert "lg:grid-cols-4" in src, \
            "su desktop la griglia deve arrivare a 4 colonne"
        card = self.CARD.read_text()
        assert "aspect-[4/5]" in card and "object-cover" in card, \
            "il formato delle schede non e' piu' uniforme"

    def test_sw5_intervista_resta_raggiungibile(self):
        """La citazione invita, la pagina dell'intervista mantiene: il
        link alla pagina dedicata (PV3) resta, e solo dove c'e'."""
        src = self._page()
        assert "/intervista" in src
        assert "m.has_interview &&" in src, \
            "il link all'intervista non e' piu' condizionato"

    # ── 7. lessico del Blueprint e i18n x4 ───────────────────────────

    _VIETATE = ("marketplace", "directory", "gestionale", "piattaform",
                "trasforma la tua vita", "ritrova te stesso", "community",
                "gratuit", "gratis", "kostenlos", "free of charge")

    def test_sw5_parole_vietate_e_trattini_lunghi(self):
        """LC8 — il lessico si giudica sull'italiano (il copy vivo:
        solo-italiano dal 2/8, le altre lingue leggono l'it via
        fallback; i blocchi en/de/fr sono residui della pagina vecchia
        e non arrivano al lettore)."""
        copy = self._copy().replace("MarketplaceShell", "")
        # eccezione di copy founder (followP2): la Lettera E' gratuita
        # e dirlo non e' un argomento di vendita ai professionisti —
        # la regola anti-"gratuito" nasceva per l'offerta della rete
        eccezione = "puoi iscriverti gratuitamente"
        copy = copy.replace(eccezione, "")
        for vietata in self._VIETATE:
            assert vietata.lower() not in copy.lower(), \
                f"parola vietata nel sorgente della pagina: '{vietata}'"
        for chiave, valore in self._blocco("it").items():
            valore_scan = valore.replace(eccezione, "")
            for vietata in self._VIETATE:
                assert vietata.lower() not in valore_scan.lower(), \
                    f"[it] nwOps.{chiave} usa '{vietata}'"
            assert "—" not in valore and "–" not in valore, \
                f"[it] trattino lungo in nwOps.{chiave}"

    def test_sw5_i18n_x4(self):
        """LC8 — copy brand v3, SOLO italiano (fallbackLng='it'): via
        la parita' x4, si pretende l'italiano completo delle chiavi
        che la pagina usa davvero."""
        import re
        src = self._page()
        it = self._blocco("it")
        for chiave in ("seoTitle", "seoDesc", "title", "leadP1",
                       "growTitle", "growP1", "peopleTitle", "loading",
                       "soonTitle", "letterCta", "readInterview"):
            assert it.get(chiave), f"[it] nwOps.{chiave} mancante"
        for k, v in it.items():
            assert v and v.strip(), f"[it] nwOps.{k} vuota"
        # i defaultValue inline sono l'italiano vero, non una variante
        for k, v in it.items():
            if f"nwOps.{k}" in src and f"'{v}'" not in src:
                assert v.replace("’", "'") in src.replace("’", "'"), \
                    f"defaultValue di nwOps.{k} diverso dall'italiano"
        defaults = re.findall(r"defaultValue:\s*(?:'([^']*)'|\"([^\"]*)\")", src)
        valori = [a or b for a, b in defaults]
        assert len(valori) >= 18, \
            f"i defaultValue della pagina sono {len(valori)}, attesi almeno 18"
        for val in valori:
            assert "—" not in val and "–" not in val, \
                f"trattino lungo nel copy della rete: {val[:40]}"

    def test_sw5_label_della_pratica_tradotte_x4(self):
        """La pratica arriva come slug: senza label la scheda
        stamperebbe 'cibo_tisane'. Le categorie della tassonomia
        prodotti devono esistere in tutte e quattro le lingue."""
        import json
        for lang in self.LOCALES:
            landings = json.loads((FRONTEND_SRC / "locales" / lang
                                   / "landings.json").read_text())
            taxonomy = json.loads((FRONTEND_SRC / "locales" / lang
                                   / "products.json").read_text())["taxonomy"]
            cats = landings.get("categories") or {}
            mancanti = set(taxonomy) - set(cats)
            assert not mancanti, \
                f"[{lang}] categorie senza label in landings: {sorted(mancanti)}"
        # LC8 — la label passa da catLabel(slug), stesso dispositivo
        assert "categories.${slug}" in self._page(), \
            "la pagina stampa lo slug grezzo invece della label"


class TestFeeTruthNeiTermini:
    """v2.5 (founder, 13/8) — i Termini devono dire la stessa cosa che
    fa il checkout: fee su TUTTI i pagamenti online elaborati tramite
    la piattaforma (5% Gratis, 0% Pro), zero fee sull'offline. Le due
    bugie del testo vecchio (2% Pro inesistente, perimetro "solo
    Calendario pubblico") non devono tornare."""

    LEGAL = Path(__file__).resolve().parent.parent / "legal"

    def _terms(self, lang):
        return (self.LEGAL / f"terms_{lang}.md").read_text(encoding="utf-8")

    def test_pro_zero_commissioni_mai_2_percento(self):
        # il "2%" come fee del Pro non esiste piu' in nessuna lingua
        for lang, morto in [("it", "2% con il piano Pro"),
                            ("en", "2% on the Pro plan"),
                            ("de", "2 % im Pro-Plan"),
                            ("fr", "2 % avec le plan Pro")]:
            assert morto not in self._terms(lang), \
                f"terms_{lang}: promette ancora il 2% sul Pro (v2.5)"

    def test_perimetro_fee_tutti_i_pagamenti_online(self):
        vivi = {"it": "tutti i pagamenti online elaborati tramite la Piattaforma",
                "en": "all online payments processed through the Platform",
                "de": "alle über die Plattform abgewickelten Online-Zahlungen",
                "fr": "tous les paiements en ligne traités via la Plateforme"}
        for lang, frase in vivi.items():
            assert frase in self._terms(lang), \
                f"terms_{lang}: manca il perimetro vero della fee (v2.5)"

    def test_link_listino_vivo(self):
        # /pricing e' un 404: il rimando contrattuale punta a /costi
        for lang in ("it", "en", "de", "fr"):
            src = self._terms(lang)
            assert "aurya.life/pricing" not in src, f"terms_{lang}: link 404"
            assert "aurya.life/costi" in src, f"terms_{lang}: manca /costi"

    def test_hash_agganciato_ai_file(self):
        """Se qualcuno tocca i legal senza rifare il giro versione,
        questa guardia lo dice subito (il re-consent vive sull'hash)."""
        import hashlib
        from core.legal_versions import CURRENT_VERSION_HASH
        priv = (self.LEGAL / "privacy_it.md").read_text(encoding="utf-8")
        terms = (self.LEGAL / "terms_it.md").read_text(encoding="utf-8")
        atteso = hashlib.sha256(
            (priv + "\n\n--- TERMS BUNDLE ---\n\n" + terms).encode()
        ).hexdigest()[:16]
        assert CURRENT_VERSION_HASH == atteso, (
            "legal modificati senza aggiornare CURRENT_VERSION_HASH: "
            f"atteso {atteso}, trovato {CURRENT_VERSION_HASH}")


class TestSuperficieSubitoLk9:
    """LK9 (founder in prod, 14/8) — con bio salvata l'indirizzo
    pubblico deve esistere APPENA si apre l'editor: in prod l'org del
    founder aveva bio + store attivo mai pubblicato (senza slug) e
    restava senza superficie — toggle pagina link morto e bottoni
    profilo nascosti, con l'invito beffardo a "salvare prima"."""

    ORG_SRC = (Path(__file__).resolve().parent.parent
               / "routers" / "organizations.py").read_text()

    def test_get_assicura_la_superficie_prima_di_risolvere(self):
        blocco = self.ORG_SRC.split("async def get_public_profile")[1] \
                             .split("\n@router.")[0]
        ensure = blocco.find("_ensure_public_surface")
        resolve = blocco.find("_resolve_public_slug_for_org")
        assert ensure != -1, "la GET non assicura piu' la superficie"
        assert resolve != -1
        assert ensure < resolve, \
            "la GET risolve lo slug PRIMA di assicurare la superficie"

    def test_cancello_store_solo_se_pubblicato_con_slug(self):
        blocco = self.ORG_SRC.split("async def _ensure_public_surface")[1]
        gate = blocco.split("updates = {}")[0]
        assert '"is_published": True' in gate, \
            "il cancello store ignora is_published: le org con store " \
            "attivo mai pubblicato restano senza indirizzo"
        assert '"slug"' in gate, \
            "il cancello store non pretende uno slug vero"

    def test_rimozione_listino_usa_un_metodo_che_esiste(self):
        """Bug prod 14/8: removeRow chiamava productsAPI.delete, che
        non esiste (il metodo e' deactivate) — TypeError client-side
        e rimozione sempre fallita, zero richieste al server."""
        pagina = (FRONTEND_SRC / "features" / "listino"
                  / "ListinoPage.js").read_text()
        api_src = (FRONTEND_SRC / "api" / "products.js").read_text()
        assert "productsAPI.delete(" not in pagina, \
            "removeRow torna a chiamare productsAPI.delete (inesistente)"
        assert "productsAPI.deactivate(" in pagina
        assert "deactivate:" in api_src


class TestDisciplineDi:
    """DI (founder, 14/8) — le discipline olistiche DICHIARATE:
    tassonomia unica a famiglie, selettore nel profilo, filtro in
    /esplora-operatori, badge su card e profilo."""

    UA = {"User-Agent": "Mozilla/5.0 (Macintosh) Chrome/126 Safari/537.36"}

    def test_parita_tassonomia_backend_frontend(self):
        """Lo specchio JS deve avere ESATTAMENTE gli slug del backend."""
        import re
        from models.disciplines import DISCIPLINES, DISCIPLINE_FAMILIES
        js = (FRONTEND_SRC / "lib" / "disciplines.js").read_text()
        js_slugs = set(re.findall(r"\{ slug: '([a-z0-9-]+)', label:", js))
        assert js_slugs == set(DISCIPLINES), (
            "tassonomie divergenti: solo backend "
            f"{set(DISCIPLINES) - js_slugs}, solo frontend "
            f"{js_slugs - set(DISCIPLINES)}")
        # le famiglie coprono tutto senza doppioni
        flat = [s for _f, _l, items in DISCIPLINE_FAMILIES for s, _ in items]
        assert len(flat) == len(set(flat)), "slug duplicato tra famiglie"
        # le voci chieste esplicitamente dal founder esistono
        for slug in ("reiki", "shiatsu", "naturopatia", "meditazione",
                     "yoga", "breathwork", "aromaterapia",
                     "cristalloterapia", "costellazioni-familiari"):
            assert slug in DISCIPLINES, f"manca {slug}"

    def test_patch_valida_e_get_riflette(self):
        """Slug fuori tassonomia scartati in silenzio; dedup; roundtrip."""
        try:
            r = requests.post(f"{BASE_URL}/api/auth/login", json={
                "email": "admin@demo.com", "password": "demo1234"},
                timeout=10)
        except requests.RequestException:
            pytest.skip("backend non raggiungibile")
        if r.status_code != 200:
            pytest.skip("demo login unavailable (rate limit?)")
        hdr = {"Authorization": f"Bearer {r.json()['access_token']}"}
        prima = requests.get(
            f"{BASE_URL}/api/organizations/current/public-profile",
            headers=hdr, timeout=10).json().get("disciplines", [])
        try:
            r2 = requests.patch(
                f"{BASE_URL}/api/organizations/current/public-profile",
                json={"disciplines": ["reiki", "shiatsu", "reiki",
                                      "non-esiste", 42]},
                headers=hdr, timeout=30)
            assert r2.status_code == 200, r2.text
            assert r2.json().get("disciplines") == ["reiki", "shiatsu"]
        finally:
            requests.patch(
                f"{BASE_URL}/api/organizations/current/public-profile",
                json={"disciplines": prima}, headers=hdr, timeout=30)

    def test_filtro_e_payloads_cablati(self):
        pub = (Path(__file__).resolve().parent.parent / "routers"
               / "public.py").read_text()
        assert "discipline: str = Query" in pub, \
            "manca il param discipline su /operators"
        assert "if discipline and discipline not in _decl" in pub
        assert '"disciplines": all_disciplines' in pub, \
            "manca l'aggregato discipline nella risposta"
        assert pub.count('"disciplines":') >= 3, \
            "disciplines mancante su item o payload profilo"

    def test_superfici_frontend(self):
        editor = (FRONTEND_SRC / "features" / "settings"
                  / "PublicProfilePage.js").read_text()
        assert 'data-testid={`pp-disc-${d.slug}`}' in editor, \
            "spariti i chip discipline dall'editor profilo"
        assert "payload.disciplines" in editor
        # DI2 — la sezione e' COMPATTA: chiusa di default (riga sola),
        # si apre col toggle e dentro c'e' la ricerca
        assert 'data-testid="pp-disc-toggle"' in editor, \
            "sparito il toggle Modifica/Fatto: la sezione torna a muro"
        assert "discQuery" in editor, "sparita la ricerca discipline"
        esplora = (FRONTEND_SRC / "features" / "storefront"
                   / "OperatorsIndexPage.js").read_text()
        assert 'data-testid="operators-discipline-filter"' in esplora
        assert "q.discipline = disciplina" in esplora
        # DI5 — solo le discipline PRESENTI (conteggio accanto),
        # raggruppate per famiglia: mai il catalogo intero che
        # "non filtra nulla" (decisione founder 14/8, sera)
        assert "optgroup" in esplora and "DISCIPLINE_FAMILIES" in esplora
        assert "presenti" in esplora and "data?.disciplines?.[d.slug]" in esplora, \
            "il filtro mostra di nuovo il catalogo intero"
        profilo = (FRONTEND_SRC / "features" / "storefront"
                   / "OperatorProfilePage.js").read_text()
        assert 'data-testid="profile-disciplines"' in profilo


class TestLucchettoListingXl1:
    """XL1 (founder, 14/8) — exclude_from_listings: l'org marchiata non
    compare MAI in /operators ne' tra i membri della rete, qualunque
    cosa succeda al suo store. Requisito: l'org personale del founder
    non deve mai apparire in vetrina."""

    def test_lucchetto_cablato_e_proiettato(self):
        pub = (Path(__file__).resolve().parent.parent / "routers"
               / "public.py").read_text()
        assert pub.count("exclude_from_listings") >= 3, \
            "lucchetto sparito da un listing o dalla proiezione"
        # nel loop aggregatore il salto avviene PRIMA dello specchio
        # sample/prelaunch (mai contato da nessuna parte)
        blocco = pub.split('if org.get("exclude_from_listings")')[1][:120]
        assert "continue" in blocco
        # senza proiezione il filtro leggerebbe sempre None
        assert '"exclude_from_listings": 1' in pub


class TestMenuMobileMb1:
    """MB1 (founder, 13/8) — nel pannello mobile del guscio marketplace
    "Chi siamo" appariva due volte in fase rete: una da NETWORK_NAV_ITEMS
    e una cablata dall'era AN2. Le voci extra (chi-siamo, come-funziona)
    vivono SOLO in fase marketplace, dietro !isNetwork."""

    def test_voci_extra_dietro_il_gate_di_fase(self):
        src = (FRONTEND_SRC / "features" / "storefront" / "components"
               / "MarketplaceShell.jsx").read_text()
        # zona: dal pannello mobile in giu'
        pannello = src.split("AN2 — pannello mobile")[1]
        # ogni link cablato a /chi-siamo e /come-funziona nel pannello
        # deve stare dentro un blocco {!isNetwork && ...}
        for rotta in ('to="/chi-siamo"', 'to="/come-funziona"'):
            i = pannello.find(rotta)
            assert i != -1, f"{rotta} sparita dal pannello mobile"
            prima = pannello[:i]
            apertura = prima.rfind("{!isNetwork && (")
            assert apertura != -1 and "navItems.map" not in prima[apertura:], (
                f"{rotta} non e' dietro !isNetwork nel pannello mobile: "
                "in fase rete torna il doppione di Chi siamo (MB1)")


class TestLinkPageLk1:
    """LK1 (piano pagina link, 14/8) — la pagina per la bio di
    Instagram. Il backend: validazione https-only e tetti, GET
    normalizzato coi default, esposizione pubblica SOLO se attivata
    e coi soli link attivi."""

    _token = None

    @classmethod
    def _hdr(cls):
        import pytest
        if cls._token:
            return {"Authorization": f"Bearer {cls._token}"}
        r = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@demo.com", "password": "demo1234"}, timeout=10)
        if r.status_code != 200:
            pytest.skip("demo login unavailable (rate limit?)")
        cls._token = r.json()["access_token"]
        return {"Authorization": f"Bearer {cls._token}"}

    def _patch(self, link_page):
        return requests.patch(
            f"{BASE_URL}/api/organizations/current/public-profile",
            json={"link_page": link_page}, headers=self._hdr(), timeout=10)

    def _restore_off(self):
        # lascia l'org demo com'era: pagina disattivata, zero link
        self._patch({"enabled": False, "links": []})

    def test_get_normalizzato_coi_default(self):
        r = requests.get(
            f"{BASE_URL}/api/organizations/current/public-profile",
            headers=self._hdr(), timeout=10)
        assert r.status_code == 200
        lp = r.json().get("link_page")
        assert lp is not None, "GET senza link_page: l'editor non puo' partire"
        assert set(lp) == {"enabled", "theme", "links", "blocks", "order"}
        assert lp["theme"] in ("salvia", "terra", "notte", "carta",
                               "aurora", "cosmo", "quarzo")   # LK8
        assert set(lp["blocks"]) == {
            "upcoming", "listino", "profile", "whatsapp", "socials"}

    def test_validazione_https_tetti_e_tema(self):
        try:
            r = self._patch({
                "enabled": True, "theme": "vaporwave",   # fuori rosa
                "links": [
                    {"label": "Il mio canale", "url": "https://youtube.com/@x"},
                    {"label": "cattivo", "url": "javascript:alert(1)"},
                    {"label": "insicuro", "url": "http://example.com"},
                    {"label": "", "url": "https://senza-etichetta.it"},
                    {"label": "L" * 200, "url": "https://etichetta-lunga.it"},
                ],
            })
            assert r.status_code == 200, r.text
            lp = r.json()["link_page"]
            assert lp["theme"] == "salvia"          # fallback dalla rosa
            urls = [l["url"] for l in lp["links"]]
            assert all(u.startswith("https://") for u in urls)
            assert "javascript:alert(1)" not in urls
            assert not any(u.startswith("http://") for u in urls)
            labels = [l["label"] for l in lp["links"]]
            assert all(0 < len(x) <= 60 for x in labels)
            # ogni link sopravvissuto ha un id server-side
            assert all(l.get("id") for l in lp["links"])
        finally:
            self._restore_off()

    def test_pubblico_solo_se_attivata_e_solo_link_attivi(self):
        try:
            # spenta -> il payload pubblico NON la porta
            self._patch({"enabled": False, "links": []})
            r = requests.get(f"{BASE_URL}/api/public/operator/masseria-demo",
                             timeout=10)
            assert r.status_code == 200
            assert "link_page" not in r.json(), \
                "pagina disattivata ma esposta al pubblico"

            # accesa con un link attivo e uno spento
            self._patch({
                "enabled": True, "theme": "notte",
                "links": [
                    {"label": "Video", "url": "https://youtube.com/@x",
                     "active": True},
                    {"label": "Nascosto", "url": "https://segreto.it",
                     "active": False},
                ],
                "blocks": {"upcoming": True, "listino": False,
                           "profile": True, "whatsapp": True,
                           "socials": True},
            })
            r = requests.get(f"{BASE_URL}/api/public/operator/masseria-demo",
                             timeout=10)
            lp = r.json().get("link_page")
            assert lp, "pagina attivata ma non esposta"
            assert lp["theme"] == "notte"
            labels = [l["label"] for l in lp["links"]]
            assert "Video" in labels and "Nascosto" not in labels
            assert lp["blocks"]["listino"] is False
        finally:
            self._restore_off()


class TestLinkPageLk5:
    """LK5 — chiusura ciclo pagina link: E2E vivo (attiva -> guscio SEO
    -> click tracciato -> Visibilita') + guardie sorgente sulle promesse
    (footer Aurya, noindex, 4 temi, nginx, editor)."""

    _token = None

    @classmethod
    def _hdr(cls):
        import pytest
        if cls._token:
            return {"Authorization": f"Bearer {cls._token}"}
        r = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@demo.com", "password": "demo1234"}, timeout=10)
        if r.status_code != 200:
            pytest.skip("demo login unavailable (rate limit?)")
        cls._token = r.json()["access_token"]
        return {"Authorization": f"Bearer {cls._token}"}

    _UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
           "AppleWebKit/605.1.15")

    def test_e2e_attiva_guscio_click_visibilita(self):
        hdr = self._hdr()
        db = None
        try:
            # 1) attiva con un link custom
            r = requests.patch(
                f"{BASE_URL}/api/organizations/current/public-profile",
                json={"link_page": {"enabled": True, "theme": "salvia",
                      "links": [{"label": "Guardia LK5",
                                 "url": "https://esempio-lk5.it"}]}},
                headers=hdr, timeout=10)
            assert r.status_code == 200
            lk5_id = r.json()["link_page"]["links"][-1]["id"]

            # 2) guscio SEO: noindex + OG (vive nelle chat)
            shell = requests.get(f"{BASE_URL}/__seo/@masseria-demo",
                                 timeout=10).text
            assert "noindex" in shell
            assert "og:title" in shell

            # 3) click tracciato sul link custom
            r = requests.post(f"{BASE_URL}/api/public/track", json={
                "surface": "link_click", "slug": "masseria-demo",
                "channel": "direct", "link_id": lk5_id},
                headers={"User-Agent": self._UA}, timeout=10)
            assert r.status_code == 204

            # 4) la Visibilita' lo racconta con l'etichetta giusta
            r = requests.get(f"{BASE_URL}/api/analytics/visibility",
                             headers=hdr, timeout=20)
            assert r.status_code == 200
            lp = r.json().get("link_page") or {}
            assert lp.get("enabled") is True
            labels = {row["label"] for row in lp.get("top", [])}
            assert "Guardia LK5" in labels
        finally:
            # pulizia: pagina spenta + click della guardia rimossi
            requests.patch(
                f"{BASE_URL}/api/organizations/current/public-profile",
                json={"link_page": {"enabled": False, "links": []}},
                headers=hdr, timeout=10)
            try:
                import re as _re
                import pymongo
                env = (BACKEND_DIR / ".env").read_text()
                mongo = _re.search(r'MONGO_URL="?([^"\n]+?)"?\n', env).group(1)
                name = _re.search(r'DB_NAME="?([^"\n]+?)"?\n', env).group(1)
                live = pymongo.MongoClient(mongo)[name]
                live.link_clicks.delete_many({"slug": "masseria-demo"})
                live.page_views.delete_many({"surface": "links",
                                             "slug": "masseria-demo"})
            except Exception:
                pass

    # ── guardie sorgente ─────────────────────────────────────────────

    def _page_src(self):
        return (FRONTEND_SRC / "features" / "storefront"
                / "LinkPage.js").read_text()

    def test_footer_aurya_e_loop_di_fase(self):
        src = self._page_src()
        assert "Sei un professionista del benessere?" in src, \
            "sparito il footer Aurya: e' il loop di crescita (LK2)"
        # Founder 14/8: la CTA porta al login (chi si riconosce entra
        # o si iscrive da li') col gesto "Crea il tuo profilo".
        # ID (20/8): la porta e' /accedi.
        assert 'to="/accedi"' in src, "la CTA footer non porta piu' alla porta"
        assert "Crea il tuo profilo" in src

    def test_quattro_temi_registrati(self):
        # LK8: rosa a 7 — i 4 storici + le tre atmosfere sceniche
        src = self._page_src()
        for tema in ("salvia:", "terra:", "notte:", "carta:",
                     "aurora:", "cosmo:", "quarzo:"):
            assert tema in src, f"tema {tema} sparito dalla rosa"
        # cosmo monta il cielo CSS: se la classe sparisce da index.css
        # il tema diventa un fondo piatto senza stelle
        css = (FRONTEND_SRC / "index.css").read_text()
        assert ".lk-stars" in css, "cielo stellato di cosmo sparito"

    def test_noindex_nel_guscio_e_nginx_instradati(self):
        shell_src = (Path(__file__).resolve().parent.parent / "routers"
                     / "seo_shell.py").read_text()
        assert "_meta_link_page" in shell_src
        assert '"noindex": True' in shell_src.split("_meta_link_page")[1][:1200]
        for conf in ("nginx.conf", "nginx-bootstrap.conf"):
            ngx = (Path(__file__).resolve().parent.parent.parent
                   / "deploy" / "nginx" / conf).read_text()
            assert "^/@" in ngx, f"{conf}: manca la location /@ (OG rotti)"
            assert "|l|" in ngx, f"{conf}: /l/ fuori dal guscio SEO"
        # LK10 — l'anteprima dell'editor e' un iframe su /l/{slug}:
        # senza la location dedicata con SAMEORIGIN gli header globali
        # (DENY + frame-ancestors 'none') la bloccano in prod.
        prod_ngx = (Path(__file__).resolve().parent.parent.parent
                    / "deploy" / "nginx" / "nginx.conf").read_text()
        assert "^/l/[^/]+/?$" in prod_ngx, \
            "nginx.conf: sparita la location /l/ incorniciabile (LK10)"
        # split su "\n    location": "geolocation" (Permissions-Policy)
        # contiene "location" e troncherebbe lo slice a meta' blocco
        lloc = prod_ngx.split("^/l/[^/]+/?$")[1].split("\n    location")[0]
        assert 'X-Frame-Options "SAMEORIGIN"' in lloc
        assert "frame-ancestors 'self'" in lloc
        # LK10b — il blocco era DOPPIO: anche la pagina che incornicia
        # (l'editor) deve poterlo fare — la CSP globale limitava
        # frame-src ai soli video Bunny. Senza 'self' l'anteprima
        # resta bloccata dal lato genitore.
        assert "frame-src 'self' https://iframe.mediadelivery.net" \
            in prod_ngx, "frame-src globale senza 'self': iframe interni vietati"

    def test_editor_tre_gesti(self):
        card = (FRONTEND_SRC / "features" / "settings"
                / "LinkPageCard.js").read_text()
        # attiva -> copia -> incolla: i tre pezzi devono esserci
        assert 'data-testid="linkpage-toggle"' in card
        assert 'data-testid="linkpage-copy"' in card
        assert "navigator.clipboard" in card
        # salvataggio immediato, mai un bottone Salva da ricordare
        assert "api.patch" in card

    def test_click_tracciati_su_tutte_le_righe(self):
        src = self._page_src()
        for lid in ("block:upcoming", "block:listino", "block:whatsapp",
                    "block:profile"):
            assert lid in src, f"click non tracciato su {lid} (LK4)"
        assert "trackClick(org_slug, l.id)" in src, \
            "click non tracciato sui link personalizzati (LK4)"


class TestFormatiServizio:
    """Formati servizio (founder, 16/8) — due assi complementari:
    Disciplina = cosa pratichi (dichiarata sul profilo), Servizio =
    in che FORMATO lo compri (tassonomia minimale di erogazione).
    Slug storici invariati, label riallineate, due formati nuovi,
    filtro esplora rinominato «Formato»."""

    ATTESI = {"trattamenti", "consulenze", "lezioni",
              "corsi-gruppo", "cerimonie", "percorsi"}

    def test_tassonomia_sei_formati(self):
        """6 formati esatti; gli slug storici restano (no migrazione)."""
        from models.retreat_taxonomy import PRODUCT_TAXONOMIES
        service = PRODUCT_TAXONOMIES["service"]
        assert set(service) == self.ATTESI
        # label riallineate: i formati sono erogazione, non discipline
        assert service["trattamenti"] == "Trattamenti individuali"
        assert service["consulenze"] == "Consulenze & Colloqui"
        assert service["cerimonie"] == "Cerimonie & Cerchi"

    def test_specchio_listino_frontend(self):
        """SERVICE_CATEGORIES in ListinoPage = stessa tassonomia."""
        import re
        src = (FRONTEND_SRC / "features" / "listino" /
               "ListinoPage.js").read_text()
        m = re.search(r"const SERVICE_CATEGORIES = \{(.*?)\};",
                      src, re.S)
        assert m, "SERVICE_CATEGORIES sparito da ListinoPage"
        slugs = set(re.findall(r"['\"]?([a-z-]+)['\"]?:\s*'", m.group(1)))
        assert slugs == self.ATTESI, (
            f"specchio listino divergente: {slugs ^ self.ATTESI}")

    def test_label_nelle_locales(self):
        """I due formati nuovi risolvono in TUTTE le lingue, nei due
        namespace che li mostrano (esplora=landings, wizard=products)."""
        import json
        for lang in ("it", "en", "de", "fr"):
            landings = json.loads(
                (FRONTEND_SRC / "locales" / lang / "landings.json")
                .read_text())
            products = json.loads(
                (FRONTEND_SRC / "locales" / lang / "products.json")
                .read_text())
            for slug in ("corsi-gruppo", "percorsi"):
                assert slug in landings["categories"], \
                    f"{lang}/landings categories.{slug} mancante"
                assert slug in products["taxonomy"], \
                    f"{lang}/products taxonomy.{slug} mancante"
        # label italiana definitiva
        it = json.loads((FRONTEND_SRC / "locales" / "it" /
                         "landings.json").read_text())
        assert it["categories"]["trattamenti"] == "Trattamenti individuali"
        assert it["categories"]["percorsi"] == "Percorsi & Pacchetti"

    def test_filtro_esplora_rinominato_formato(self):
        """In esplora il filtro si chiama «Formato» (voce vuota «Ogni
        formato»), non piu' «Tutti i servizi»."""
        import json
        src = (FRONTEND_SRC / "features" / "storefront" /
               "OperatorsIndexPage.js").read_text()
        assert "defaultValue: 'Formato'" in src
        assert "defaultValue: 'Ogni formato'" in src
        assert "Tutti i servizi" not in src
        it = json.loads((FRONTEND_SRC / "locales" / "it" /
                         "landings.json").read_text())
        assert it["operators"]["whatLabel"] == "Formato"
        assert it["operators"]["whatAll"] == "Ogni formato"


class TestAuthSoloItaliano:
    """Founder 16/8: via il selettore IT/EN/FR/DE da login e
    registrazione — il sito pubblico parla solo italiano. Il ?lang=
    resta per i deep link dalle email gia' inviate."""

    def test_niente_selettore_lingua_in_auth(self):
        src = (FRONTEND_SRC / "pages" / "AuthPages.js").read_text()
        assert "LanguageSwitcher" not in src, \
            "selettore lingua tornato nelle pagine auth"
        # l'anonimo con una preferenza straniera residua vede l'italiano
        assert "i18n.changeLanguage('it')" in src
        # ...ma il ?lang= dei deep link email resta rispettato
        assert "searchParams.get('lang')" in src


class TestDisciplineDi6:
    """DI6 (operatrice via founder, 16/8) — due voci ombrello per il
    mondo delle danze rituali e del femminile, e un canale di
    segnalazione che funziona anche senza client di posta."""

    def test_voci_nuove_in_entrambe_le_fonti(self):
        from models.disciplines import DISCIPLINES, DISCIPLINE_FAMILIES
        js = (FRONTEND_SRC / "lib" / "disciplines.js").read_text()
        for slug in ("danze-sacre", "sacro-femminile"):
            assert slug in DISCIPLINES, f"{slug} assente dal backend"
            assert f"slug: '{slug}'" in js, f"{slug} assente dallo specchio JS"
        # la label italiana nomina la pratica che l'operatrice cerca
        assert "Danza della Dea" in DISCIPLINES["danze-sacre"]
        # famiglie coerenti: danza nel corpo, femminile nell'anima
        fam = {s: f for f, _l, items in DISCIPLINE_FAMILIES
               for s, _ in items}
        assert fam["danze-sacre"] == "corpo"
        assert fam["sacro-femminile"] == "anima"

    def test_email_in_chiaro_non_solo_mailto(self):
        """Il mailto da solo non basta (posta letta nel browser): si
        vede l'indirizzo, si copia, e se pure la clipboard e' negata
        il testo viene selezionato — mai un gesto senza esito."""
        src = (FRONTEND_SRC / "features" / "settings" /
               "PublicProfilePage.js").read_text()
        assert "{BRAND_EMAIL}\n" in src or ">\n                    {BRAND_EMAIL}" in src, \
            "indirizzo non mostrato in chiaro nella riga suggerimento"
        assert 'data-testid="pp-disc-copy-email"' in src
        assert "copyEmail" in src and "selectNodeContents" in src, \
            "manca il ripiego selezione quando la clipboard e' negata"

    def test_chiavi_copia_in_quattro_lingue(self):
        import json
        for lang in ("it", "en", "de", "fr"):
            d = json.loads((FRONTEND_SRC / "locales" / lang /
                            "settings.json").read_text())["publicProfile"]
            for k in ("disciplinesCopyEmail", "disciplinesEmailCopied",
                      "disciplinesEmailSelected"):
                assert d.get(k), f"{lang}: manca publicProfile.{k}"
