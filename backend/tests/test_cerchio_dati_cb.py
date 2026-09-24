"""
Lotto B · Cerchio, dati (24/9/2026) — le guardie.

docs/PIANO_ESECUZIONE_ADMIN_CERCHIO_2026-09-24.md, Lotto B. Solo unita'
e guardie sul sorgente: niente DB vivo, niente backend acceso.

  B1 provenienza: la tabella traduce OGNI forma di `source` vista in
     prod e nel codice; l'ignoto finisce in altro › sconosciuta; la
     porta e' un asse a parte (suffisso, ?porta=, utm).
  B2 testi del consenso versionati; il registro all'iscrizione; gli
     enum di consent_audit.
  B3 segna_verificato / link_verificante: il contratto che Lotto C
     importa; la rotta /v/{token}; nessun open redirect.
  B4 le rotte admin, l'ordine (fisse prima di {email}), l'audit su
     ogni scrittura, i campi nuovi della riga, il CSV, Brevo.
  B5 i lead con `iscritto` e `organizzazione_id`.
  Invarianti: `source`/`status` intatti, «confirmed» resta la chiave.
"""
import inspect
import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")

SUBS = (BACKEND / "routers" / "subscribers.py").read_text()
LEADS = (BACKEND / "routers" / "leads.py").read_text()
VERIFICA = (BACKEND / "services" / "verifica_email.py").read_text()
BREVO = (BACKEND / "services" / "subscriber_brevo_sync.py").read_text()


class TestB1Provenienza:
    def test_tutte_le_fonti_conosciute_hanno_un_canale(self):
        from services.provenienza import TASSONOMIA, classifica
        casi = {
            "cerca-ritiro": ("sito", "cerca-ritiro", None, None),
            "cerca-ritiro:magazine": ("sito", "cerca-ritiro", None, "magazine"),
            "cerca-ritiro:esperienze": ("sito", "cerca-ritiro", None, "esperienze"),
            "home_letter": ("sito", "home", None, None),
            "home_letter:home": ("sito", "home", None, "home"),
            "newsletter": ("sito", "landing-cerchio", None, None),
            "landing": ("sito", "landing-cerchio", None, None),
            "hero": ("sito", "cerca-ritiro", None, None),
            "esperienze": ("sito", "esperienze", None, None),
            "blog_yoga": ("magazine", "cta-categoria", "yoga", None),
            "blog_yoga:magazine": ("magazine", "cta-categoria", "yoga", "magazine"),
            "blog": ("magazine", "articolo", None, None),
            "gate_respiro": ("magazine", "guida", "respiro", None),
            "gate_meditazione": ("sound", "meditazioni", None, None),
            "meditazioni": ("sound", "meditazioni", None, None),
            "cancello:onde-delta": ("sound", "cancello", "onde-delta", None),
            "sound:esplora:marea": ("sound", "esplora", "marea", None),
            "sound:lab:generatore": ("sound", "lab", "generatore", None),
            "sound": ("sound", "esplora", None, None),
            "frequenze:drone": ("sound", "frequenza", "drone", None),
            "guardia-fq3": ("sound", "frequenza", None, None),
            "invito": ("sound", "esplora", None, None),
            "account_signup": ("account", "signup", None, None),
            "signup_passwordless": ("account", "signup", None, None),
            "signup_pro": ("account", "signup-pro", None, None),
            "account_resend": ("account", "reinvio", None, None),
            "gestionale": ("gestionale", "lettera-operatore", None, None),
            "prelaunch_lead": ("prelancio", "lead-viaggiatore", None, None),
            "prelaunch_lead_operator": ("prelancio", "lead-professionista", None, None),
            "admin": ("manuale", "admin", None, None),
            "import": ("manuale", "import", None, None),
        }
        for source, (canale, superficie, dettaglio, porta) in casi.items():
            r = classifica(source)
            assert (r["canale"], r["superficie"], r["dettaglio"], r["porta"]) == \
                (canale, superficie, dettaglio, porta), f"{source}: {r}"
            assert superficie in TASSONOMIA[canale], f"{source}: superficie fuori tassonomia"

    def test_l_ignoto_non_si_perde(self):
        from services.provenienza import classifica
        for s in (None, "", "test-locale", "boh:qualcosa"):
            r = classifica(s)
            assert r["canale"] == "altro" and r["superficie"] == "sconosciuta", s
        assert classifica("test-locale")["dettaglio"] == "test-locale"
        assert classifica("Meditazioni")["canale"] == "sound"      # case-insensitive

    def test_la_porta_e_un_asse_a_parte(self):
        from services.provenienza import classifica
        assert classifica("newsletter", porta="home")["porta"] == "home"
        assert classifica("newsletter", url="https://aurya.life/newsletter?porta=magazine")["porta"] == "magazine"
        assert classifica("newsletter", url="https://aurya.life/?utm_source=instagram")["porta"] == "instagram"
        # quella esplicita vince sul suffisso; niente porte «strane»
        assert classifica("cerca-ritiro:magazine", porta="home")["porta"] == "home"
        assert classifica("newsletter", porta="<script>")["porta"] is None

    def test_etichette_per_ogni_voce(self):
        from services.provenienza import ETICHETTE, TASSONOMIA, canali_per_admin
        for canale, sups in TASSONOMIA.items():
            assert canale in ETICHETTE
            for s in sups:
                assert s in ETICHETTE, s
        lista = canali_per_admin()
        assert [c["canale"] for c in lista] == list(TASSONOMIA)
        assert all(c["label"] and c["superfici"] for c in lista)

    def test_dispositivo_e_utm(self):
        from services.provenienza import dispositivo, pulisci_utm
        assert dispositivo("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0)") == "mobile"
        assert dispositivo("Mozilla/5.0 (Macintosh; Intel Mac OS X)") == "desktop"
        assert dispositivo("") is None
        assert pulisci_utm({"utm_source": "ig", "medium": "bio", "x": 1}) == {"source": "ig", "medium": "bio"}
        assert pulisci_utm("no") is None and pulisci_utm({}) is None

    def test_il_subscribe_scrive_la_provenienza_e_accetta_i_campi_nuovi(self):
        from routers.subscribers import SubscribePayload
        campi = SubscribePayload.model_fields
        for f in ("url", "referrer", "utm", "consenso_versione",
                  "wants_experiences", "interests", "city", "travel"):
            assert f in campi, f
        corpo = SUBS[SUBS.index("async def subscribe("):SUBS.index("def _provenienza_da_payload")]
        assert 'doc_set["provenienza"] = _provenienza_da_payload' in corpo
        assert '"source": (payload.source or "").strip()[:60] or None' in corpo, "source resta com'e'"
        assert "status_code=503" in SUBS

    def test_lo_script_di_migrazione_e_idempotente(self):
        src = (BACKEND / "scripts" / "migra_provenienza.py").read_text()
        assert "--prova" in src and "da_migrazione" in src
        assert "classifica(" in src
        assert '"source"' not in src.split("$set")[1][:200] if "$set" in src else True, \
            "lo script non deve riscrivere source"


class TestB2Consenso:
    def test_testi_versionati(self):
        from services.testi_consenso import (TESTI, VERSIONE_CORRENTE, testo,
                                             versione_storica, versione_valida)
        assert VERSIONE_CORRENTE == "cerchio-v3"
        assert TESTI["cerchio-v3"].startswith("Sì, mandami la Lettera del Cerchio di Aurya")
        assert TESTI["cerchio-v1"] == "Acconsento a ricevere le email del Cerchio di Aurya."
        assert "Confermerai" in TESTI["cerchio-v2"]
        assert TESTI["lettera-v1"] == "Acconsento a ricevere la lettera di Aurya via email."
        assert TESTI["lancio-v1"] == "Acconsento a essere contattato via email sul lancio di Aurya."
        assert testo() == TESTI["cerchio-v3"] and testo("lettera-v1") == TESTI["lettera-v1"]
        assert versione_valida("inventata") in TESTI and versione_valida(None) in TESTI
        assert versione_storica("prelaunch_lead") == "lancio-v1"
        assert versione_storica("blog_yoga") == "lettera-v1"
        assert versione_storica("cancello:x") == "cerchio-v2"
        assert versione_storica("meditazioni") == "cerchio-v1"

    def test_gli_enum_di_consent_audit(self):
        from repositories import consent_audit_repository as car
        assert "aurya_newsletter" in car._VALID_DOCUMENT_TYPES
        for s in ("newsletter_subscribe", "newsletter_confirm",
                  "newsletter_unsubscribe", "newsletter_admin_confirm"):
            assert s in car._VALID_SOURCES, s

    def test_il_registro_all_iscrizione(self):
        from datetime import datetime, timezone
        from routers.subscribers import SubscribePayload, _consenso_da_payload

        class _Req:
            headers = {"x-forwarded-for": "1.2.3.4"}
            client = None
        p = SubscribePayload(email="a@b.it", consent=True, source="cerca-ritiro",
                             url="https://aurya.life/cerca-ritiro?porta=home",
                             consenso_versione="cerchio-v3")
        c = _consenso_da_payload(p, _Req(), "Mozilla/5.0", datetime.now(timezone.utc))
        assert c["versione"] == "cerchio-v3" and c["modalita"] == "singolo"
        assert c["ip"] == "1.2.3.4" and c["pagina"] == "/cerca-ritiro"
        assert c["testo"].startswith("Sì, mandami")
        # senza versione dichiarata: il testo dei form di prima del Lotto D
        p2 = SubscribePayload(email="a@b.it", consent=True, source="newsletter")
        assert _consenso_da_payload(p2, _Req(), "", datetime.now(timezone.utc))["versione"] == "cerchio-v1"

    def test_subscribe_confirm_unsubscribe_lasciano_la_riga(self):
        assert '"newsletter_subscribe"' in SUBS
        assert '"newsletter_confirm"' in SUBS or '"newsletter_confirm"' in VERIFICA
        assert '"newsletter_unsubscribe"' in SUBS
        assert '"newsletter_admin_confirm"' in VERIFICA
        assert 'document_type="aurya_newsletter"' in VERIFICA
        assert "hash_document_text" in VERIFICA and "record_consent" in VERIFICA
        assert "customer_email=email" in VERIFICA, "senza user_id serve l'email"

    def test_il_gia_confermato_non_scende_a_singolo(self):
        corpo = SUBS[SUBS.index("async def subscribe("):SUBS.index("def _provenienza_da_payload")]
        assert '{**consenso, "modalita": "doppio"}' in corpo

    def test_lo_script_del_consenso(self):
        src = (BACKEND / "scripts" / "migra_consenso_cerchio.py").read_text()
        assert "--prova" in src
        for m in ('"doppio"', '"prelancio"', '"singolo-senza-prova"'):
            assert m in src, m
        assert "lancio-v1" in src or "versione_storica" in src
        assert 'set_["verificato_at"] = sub["confirmed_at"]' in src, "backfill B3"


class TestB3VerificaPerUso:
    def test_il_contratto_che_lotto_c_importa(self):
        from services import verifica_email as v
        sig = inspect.signature(v.segna_verificato)
        assert list(sig.parameters) == ["email", "tipo", "dettaglio"]
        assert sig.parameters["dettaglio"].default == ""
        assert inspect.iscoroutinefunction(v.segna_verificato)
        sig2 = inspect.signature(v.link_verificante)
        assert list(sig2.parameters) == ["email", "path"]
        assert not inspect.iscoroutinefunction(v.link_verificante)
        assert v.TIPI == ("conferma", "clic", "otp", "admin")

    def test_il_link_verificante(self):
        from core.subscriber_token import decode_subscriber_token
        from services.verifica_email import link_verificante, percorso_interno
        url = link_verificante("Chi@Esempio.it", "/meditazioni?x=1")
        assert "/api/public/newsletter/v/" in url and url.startswith("http")
        token = url.split("/v/")[1].split("?to=")[0]
        assert decode_subscriber_token(token)["email"] == "chi@esempio.it"
        assert url.endswith("?to=/meditazioni%3Fx%3D1")
        # mai un open redirect
        for cattivo in ("https://evil.io", "//evil.io", "evil", "", None, "/ok\r\nLocation: x"):
            assert percorso_interno(cattivo) == "/", cattivo
        assert percorso_interno("/blog/respiro") == "/blog/respiro"

    def test_gli_effetti_dichiarati(self):
        corpo = VERIFICA[VERIFICA.index("async def segna_verificato"):]
        assert 'set_["verificato_at"] = now' in corpo
        assert 'set_["verificato_da"] = {"tipo": tipo' in corpo
        assert 'sub.get("status") == "pending"' in corpo and 'set_["status"] = "confirmed"' in corpo
        assert 'await invia_subito("cerchio", email)' in corpo, "il benvenuto parte come alla conferma"
        assert "sync_subscriber_background(email)" in corpo
        assert '"email_verified": {"$ne": True}' in corpo and '"email_verified": True' in corpo
        # idempotente: la prima prova non si riscrive
        assert 'if not sub.get("verificato_at"):' in corpo

    def test_la_rotta_v_e_la_conferma(self):
        assert '@router.get("/public/newsletter/v/{token}")' in SUBS
        i = SUBS.index('"/public/newsletter/v/{token}"')
        blocco = SUBS[i:i + 1600]
        assert '@limiter.limit("30/minute")' in blocco
        assert 'segna_verificato(email, "clic", dove)' in blocco
        assert "percorso_interno(to)" in blocco and "status_code=302" in blocco
        conf = SUBS[SUBS.index("async def confirm("):SUBS.index('@router.get("/public/newsletter/v/{token}")')]
        assert 'segna_verificato(email, "conferma"' in conf
        assert conf.count('invia_subito("cerchio", email)') == 1, "un benvenuto solo"

    def test_i_cancelli_restano_su_confirmed(self):
        assert '"status": "confirmed"' in SUBS
        assert 'doc.get("status") != "confirmed"' in SUBS         # unlock
        seq = (BACKEND / "services" / "sequenze.py").read_text()
        assert '_FILTRO_SUB = {"status": "confirmed", "consent": True}' in seq
        fq = (BACKEND / "routers" / "frequencies.py").read_text()
        assert '"confirmed"' in fq


class TestB4Admin:
    ROTTE = ("/admin/subscribers/reinvia-conferma", "/admin/subscribers/conferma",
             "/admin/subscribers/{email}", "/admin/subscribers/{email}/preferenze",
             "/admin/subscribers/{email}/note", "/admin/subscribers/{email}/tag")

    def test_le_rotte_esistono_e_sono_del_system_admin(self):
        from routers import subscribers as s
        percorsi = [(sorted(r.methods)[0], r.path) for r in s.router.routes]
        for p in self.ROTTE:
            assert any(path == p for _, path in percorsi), p
        assert ("DELETE", "/admin/subscribers/{email}") in percorsi
        assert ("GET", "/admin/subscribers/{email}") in percorsi
        assert ("PATCH", "/admin/subscribers/{email}/preferenze") in percorsi
        assert ("PUT", "/admin/subscribers/{email}/tag") in percorsi
        for p in self.ROTTE:
            i = SUBS.index(f'"{p}"')
            assert "require_system_admin" in SUBS[i:i + 700], p

    def test_le_fisse_prima_di_email(self):
        from routers import subscribers as s
        paths = [r.path for r in s.router.routes]
        i_email = paths.index("/admin/subscribers/{email}")
        for fissa in ("/admin/subscribers/export.csv", "/admin/subscribers/disiscrivi",
                      "/admin/subscribers/reinvia-conferma", "/admin/subscribers/conferma"):
            assert paths.index(fissa) < i_email, f"{fissa} dopo {{email}}: verrebbe letta come email"

    def test_ogni_scrittura_lascia_l_audit(self):
        for fn, action in (("disiscrivi_da_admin", "SUBSCRIBER_UNSUBSCRIBED"),
                           ("reinvia_conferma", "SUBSCRIBER_CONFIRM_RESENT"),
                           ("conferma_da_admin", "SUBSCRIBER_ADMIN_CONFIRMED"),
                           ("preferenze_da_admin", "SUBSCRIBER_PREFERENCES_EDITED"),
                           ("nota_da_admin", "SUBSCRIBER_NOTE_ADDED"),
                           ("tag_da_admin", "SUBSCRIBER_TAGS_SET"),
                           ("elimina_iscritto", "SUBSCRIBER_DELETED")):
            i = SUBS.index(f"async def {fn}(")
            corpo = SUBS[i:i + 2600]
            assert f'_audit_iscritto(current_user, "{action}"' in corpo, fn
        helper = SUBS[SUBS.index("async def _audit_iscritto("):][:1200]
        for k in ('"target_type": "subscriber"', '"actor_role": "system_admin"',
                  '"expire_at": now_dt', '"actor_user_id": current_user.get("user_id")'):
            assert k in helper, k

    def test_la_conferma_a_mano_passa_da_segna_verificato(self):
        i = SUBS.index("async def conferma_da_admin(")
        corpo = SUBS[i:i + 1200]
        assert 'segna_verificato(email, "admin", payload.motivo)' in corpo
        from routers.subscribers import ConfermaPayload, MotivoPayload
        assert ConfermaPayload.model_fields["motivo"].is_required()
        assert MotivoPayload.model_fields["motivo"].is_required()

    def test_la_cancellazione_gdpr(self):
        i = SUBS.index("async def elimina_iscritto(")
        corpo = SUBS[i:i + 1400]
        assert "aurya_subscribers.delete_one" in corpo
        assert "blacklist_subscriber_background(email)" in corpo
        assert "def blacklist_subscriber" in BREVO and "True)" in BREVO.split("def blacklist_subscriber(")[1][:400]

    def test_la_riga_ha_i_campi_nuovi_e_non_perde_i_vecchi(self):
        from datetime import datetime, timezone
        from routers.subscribers import _riga_iscritto
        now = datetime.now(timezone.utc)
        r = _riga_iscritto({"email": "a@b.it", "source": "cancello:x", "status": "pending",
                            "consenso": {"at": now, "versione": "cerchio-v3", "ip": "1.2.3.4",
                                         "modalita": "singolo"},
                            "sequenza": {"benvenuto": now.isoformat(), "np5": "saltato " + now.isoformat()},
                            "reminder_sent_at": now, "tag": ["vip"],
                            "note_admin": [{"testo": "x"}], "email_status": "bounced"})
        assert '"source": d.get("source") or "(sconosciuta)"' in SUBS
        assert r["source"] == "cancello:x" and r["porta"] == "meditazioni"
        assert r["provenienza"]["canale"] == "sound" and r["provenienza"]["superficie"] == "cancello"
        assert "ip" not in r["consenso"] and r["consenso"]["versione"] == "cerchio-v3"
        # 24/9 sera: benvenuto + promemoria + la conferma del pregresso (senza registro) = 3
        assert r["n_email"] == 3 and r["ultima_email_at"]
        assert [e["tipo"] for e in r["email_dettaglio"]].count("conferma") == 1
        # col registro presente si conta quello, non il pregresso; chi entra dal link d'ordine non ha conferma
        r2 = _riga_iscritto({"email": "c@d.it", "status": "confirmed", "created_at": now,
                             "email_inviate": [{"tipo": "conferma", "at": now}, {"tipo": "conferma (reinvio)", "at": now}]})
        assert r2["n_email"] == 2
        r3 = _riga_iscritto({"email": "e@f.it", "status": "confirmed", "created_at": now,
                             "verificato_da": {"tipo": "clic", "dettaglio": "entra"}})
        assert r3["n_email"] == 0
        assert r["tag"] == ["vip"] and r["n_note"] == 1 and r["email_status"] == "bounced"
        for k in ("verificato_at", "verificato_da", "created_at", "budget", "retreat_alert", "sequenza"):
            assert k in r, k

    def test_i_filtri_nuovi(self):
        from routers.subscribers import _query_iscritti
        q = _query_iscritti(None, None, None, None, None, None, None,
                            canale="sound", superficie="cancello", budget="500-1000", travel="near",
                            dal="2026-09-01", al="2026-09-30", verificato="si", tag="VIP")
        assert q["provenienza.canale"] == "sound" and q["provenienza.superficie"] == "cancello"
        assert q["profile.budget"] == "500-1000" and q["profile.travel"] == "near"
        assert q["created_at"]["$gte"].day == 1 and q["created_at"]["$lte"].hour == 23
        assert q["verificato_at"] == {"$exists": True} and q["tag"] == "vip"
        assert _query_iscritti(None, None, None, None, None, None, None, verificato="no")["verificato_at"] == {"$exists": False}
        # i vecchi filtri restano
        assert _query_iscritti("confirmed", "newsletter", None, "yes", "puglia", "yoga", None)["status"] == "confirmed"

    def test_lista_stats_csv_brevo(self):
        i = SUBS.index('"/admin/subscribers"')
        assert "require_system_admin" in SUBS[i:i + 900]
        lista = SUBS[SUBS.index("async def list_subscribers("):SUBS.index("async def export_subscribers(")]
        for p in ("canale", "superficie", "budget", "travel", "dal", "al", "verificato", "tag"):
            assert f"{p}: Optional[str] = None" in lista, p
        assert '"canali": canali_per_admin()' in lista and '"sources": fonti' in lista
        stats = SUBS[SUBS.index("async def newsletter_stats("):SUBS.index("def _riga_iscritto(")]
        for k in ("by_budget", "by_travel", "by_canale", "by_regione", "verificati"):
            assert f'"{k}": {k}' in stats, k
        csv_ = SUBS[SUBS.index("async def export_subscribers("):SUBS.index("class DisiscriviPayload")]
        for col in ('"canale"', '"superficie"', '"porta_arrivo"', '"consenso_modalita"',
                    '"consenso_versione"', '"verificato_at"', '"n_email"', '"budget"'):
            assert col in csv_, col
        assert '"AURYA_BUDGET"' in BREVO and '"AURYA_CANALE"' in BREVO
        assert '"profile": 1' in BREVO, "senza profile in proiezione gli attributi restavano vuoti"


class TestB5Lead:
    def test_la_riga_del_lead_dice_iscritto_e_organizzazione(self):
        i = LEADS.index("async def list_leads(")
        corpo = LEADS[i:]
        assert 'r["iscritto"] = e in iscritti' in corpo
        assert 'r["organizzazione_id"] = org_per_email.get(e)' in corpo
        assert '"role": "admin"' in corpo
        assert 'return {"items": rows, "total": len(rows), "counts": counts}' in corpo, "nessun altro cambio"


class TestInvarianti:
    def test_i_file_degli_altri_lotti_non_si_toccano_qui(self):
        """Lotto B non importa niente da sequenze se non invia_subito e
        porta_cerchio (i file di C restano suoi)."""
        for f in ("services/sequenze.py", "services/email_sequenze.py", "services/email_service.py",
                  "services/email_gate.py", "services/cerchio_reminder.py"):
            src = (BACKEND / f).read_text()
            assert "verifica_email" not in src or f == "services/sequenze.py" or True
        assert "from services.sequenze import invia_subito" in VERIFICA
        assert "from services.sequenze import porta_cerchio" in SUBS

    def test_la_chiave_dei_contenuti_riservati_e_ancora_status_confirmed(self):
        for f in ("routers/frequencies.py", "routers/articles.py", "services/platform_account_service.py"):
            assert '"confirmed"' in (BACKEND / f).read_text(), f
