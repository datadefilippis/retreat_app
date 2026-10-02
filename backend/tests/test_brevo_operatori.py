"""OP1-OP3 (2/10/2026 sera) — gli operatori in Brevo e la base legale.

OP1 informativa 1-bis + Termini 19.4 (v2.10): comunicazioni di servizio agli
Operatori per contratto e legittimo interesse, opposizione da ogni email.
OP2 sync operatori: registro ATTRIBUTI_BREVO_OP, AURYA_TIPO su entrambe le
sync, AURYA_OP_COMUNICAZIONI true solo per il cliente attivo che non si e'
opposto, stesso contatto dell'iscritto al Cerchio.
OP3 webhook: «unsubscribed» → users.comunicazioni_opposizione_at.
"""
from datetime import datetime, timezone
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
OP = (BACKEND / "services" / "operatori_brevo_sync.py").read_text(encoding="utf-8")
SUB = (BACKEND / "services" / "subscriber_brevo_sync.py").read_text(encoding="utf-8")
SCRIPT = (BACKEND / "scripts" / "brevo_segmentazione.py").read_text(encoding="utf-8")
WEBHOOK = (BACKEND / "routers" / "webhooks" / "brevo.py").read_text(encoding="utf-8")

FATTI = {
    "email": "op@example.com", "org_id": "o1", "attivo": True, "attivita": "  Studio   Sole ",
    "slug": "studio-sole", "bozza": True, "directory": True, "discipline": ["yoga", "reiki"],
    "regione": "puglia", "citta": "Bari", "piano": "pro", "listino": True, "stripe": False, "sound": True,
    "registrato_il": datetime(2026, 9, 1, tzinfo=timezone.utc), "ultimo_accesso": None,
    "verificato": True, "opposizione": False, "cerchio": "confirmed",
}


class TestAttributiOperatore:
    def test_registro_e_chiavi(self):
        from services.operatori_brevo_sync import ATTRIBUTI_BREVO_OP, attributi_operatore
        got = attributi_operatore(FATTI)
        assert set(got) | {"AURYA_OP_ULTIMO_ACCESSO"} == set(ATTRIBUTI_BREVO_OP)   # data vuota omessa
        assert got["AURYA_TIPO"] == "operatore+cerchio" and got["AURYA_OP"] is True
        assert got["AURYA_OP_COMUNICAZIONI"] is True and got["AURYA_OP_STATO"] == "online"
        assert got["AURYA_OP_ATTIVITA"] == "Studio Sole" and got["AURYA_OP_PAGINA"].endswith("/o/studio-sole")
        assert got["AURYA_OP_DISCIPLINE"] == "yoga,reiki" and got["AURYA_OP_PIANO"] == "pro"
        assert got["AURYA_OP_REGISTRATO_IL"] == "2026-09-01" and got["AURYA_OP_DIRECTORY"] is True
        for k, t in ATTRIBUTI_BREVO_OP.items():
            assert t in ("text", "date", "boolean"), k
            if t == "boolean" and k in got:
                assert isinstance(got[k], bool), k

    def test_opposizione_e_stati(self):
        from services.operatori_brevo_sync import attributi_operatore, _in_blacklist
        opp = attributi_operatore({**FATTI, "opposizione": True})
        assert opp["AURYA_OP_COMUNICAZIONI"] is False and _in_blacklist({**FATTI, "opposizione": True})
        spento = attributi_operatore({**FATTI, "attivo": False})
        assert spento["AURYA_OP"] is False and spento["AURYA_OP_COMUNICAZIONI"] is False
        solo = attributi_operatore({**FATTI, "cerchio": None, "slug": None, "bozza": False})
        assert solo["AURYA_TIPO"] == "operatore" and solo["AURYA_OP_STATO"] == "account" and solo["AURYA_OP_PAGINA"] == ""
        assert attributi_operatore({**FATTI, "slug": None})["AURYA_OP_STATO"] == "bozza"
        # il Cerchio disiscritto resta in blacklist anche se l'operatore e' attivo
        assert _in_blacklist({**FATTI, "cerchio": "unsubscribed"}) and not _in_blacklist(FATTI)

    def test_cerchio_porta_il_tipo(self):
        from services.subscriber_brevo_sync import _attributes, ATTRIBUTI_BREVO
        assert ATTRIBUTI_BREVO["AURYA_TIPO"] == "text"
        assert _attributes({"status": "pending"})["AURYA_TIPO"] == "cerchio"
        assert _attributes({"status": "pending"}, "operatore+cerchio")["AURYA_TIPO"] == "operatore+cerchio"
        assert _attributes({"status": "pending"}, "boh")["AURYA_TIPO"] == "cerchio"
        assert "tipo = await tipo_contatto(email)" in SUB and "_attributes(doc, tipo)" in SUB


class TestAgganci:
    def test_profilo_scheduler_script_webhook(self):
        prof = (BACKEND / "services" / "profilo_pubblico.py").read_text(encoding="utf-8")
        assert "sync_operatore_background(org_id)" in prof
        sched = (BACKEND / "services" / "scheduler_service.py").read_text(encoding="utf-8")
        assert '@register_job("brevo_operatori", interval_seconds=24 * 3600)' in sched
        assert '"--operatori"' in SCRIPT and "ATTRIBUTI_BREVO_OP" in SCRIPT and "await tipo_contatto(d[\"email\"])" in SCRIPT
        # un solo asyncio.run per i gesti sul DB (Motor e' legato al primo loop)
        assert SCRIPT.count("asyncio.run(") == 1 and "asyncio.run(_gesti_db())" in SCRIPT
        for vietato in ("smtp", "sendTransacEmail", "emailCampaigns", "listIds", "sendEmail"):
            assert vietato not in SCRIPT and vietato not in OP, vietato
        assert 'update_users["comunicazioni_opposizione_at"] = now_iso' in WEBHOOK
        assert 'if new_status == "unsubscribed":' in WEBHOOK
        # il criterio «pagina online» e' quello della regia e della directory
        assert '"is_published": True, "is_active": True,\n         "visibility": "public", "slug": {"$nin": [None, ""]}' in OP
        assert 'is_storefront_published' in OP and 'org.get("is_sample") or org.get("is_demo")' in OP


class TestInformativaOP1:
    def test_riga_1bis_e_termini_x4(self):
        attese = {"it": ("| 1-bis |", "Comunicazioni di servizio e aggiornamenti agli Operatori", "comunicazioni di servizio e gli aggiornamenti sulla Piattaforma"),
                  "en": ("| 1-bis |", "Service communications and updates to Operators", "service communications and updates about the Platform"),
                  "de": ("| 1-bis |", "Service-Mitteilungen und Aktualisierungen an die Veranstalter", "Service-Mitteilungen und Aktualisierungen zur Plattform"),
                  "fr": ("| 1-bis |", "Communications de service et mises à jour aux Opérateurs", "communications de service et mises à jour sur la Plateforme")}
        for lang, (riga, titolo, termini) in attese.items():
            priv = (BACKEND / "legal" / f"privacy_{lang}.md").read_text(encoding="utf-8")
            r = next(l for l in priv.splitlines() if l.startswith(riga))
            assert titolo in r and ("6.1.f" in r or "lit. f" in r) and "info@aurya.life" in r, lang
            t = (BACKEND / "legal" / f"terms_{lang}.md").read_text(encoding="utf-8")
            assert termini in t and "19.3" in t, lang
        from core.legal_versions import CURRENT_VERSION_TAG
        assert CURRENT_VERSION_TAG == "v2.10"
