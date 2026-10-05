"""PE (24/9/2026, founder) — le email automatiche, coerenti: dopo
l'inventario (docs/ANALISI_ONBOARDING_PROFILO_2026-09-24.md §8) si e'
tenuto fermo qui cio' che era rotto o fuorviante.

  PE1  via «Da 2 giorni su Aurya» (a noi): nessun passo admin nella sequenza
  PE2  «La tua pagina e' online» parte quando NASCE la pagina (condizione
       `pagina`), col blocco listino che dice il vero
  PE3  np5/10/15 in due varianti (senza pagina / pagina senza listino):
       chi ha solo un ritiro ha la pagina e non legge «non hai la pagina»
  PE4  quota 80%: chiavi i18n giuste (era l'oggetto letterale della chiave)
  PE5  «pagamento a rischio» risponde al cliente
  PE6  la richiesta GDPR manda davvero la nota alla casella Aurya
  PE7  il lead pre-lancio va alla casella Aurya, non a un indirizzo nel codice
  PE8  la conferma del Cerchio non si chiama «Benvenuto»
  PE9  `send_welcome` (il vecchio benvenuto) non esiste piu'
  PE10 alert critici: un admin dell'org + ops, non tutti
"""
import re
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
SEQ = (BACKEND / "services" / "sequenze.py").read_text(encoding="utf-8")
TXT = (BACKEND / "services" / "email_sequenze.py").read_text(encoding="utf-8")
ES = (BACKEND / "services" / "email_service.py").read_text(encoding="utf-8")
QUOTA = (BACKEND / "services" / "quota_email_service.py").read_text(encoding="utf-8")
PAY = (BACKEND / "services" / "payment_email_service.py").read_text(encoding="utf-8")
CRIT = (BACKEND / "services" / "critical_alert_service.py").read_text(encoding="utf-8")
LEADS = (BACKEND / "routers" / "leads.py").read_text(encoding="utf-8")
PORTAL = (BACKEND / "routers" / "customer_portal.py").read_text(encoding="utf-8")


class TestSequenzaOperatore:
    def test_nessuna_email_a_noi_e_niente_g2(self):
        from services.sequenze import PASSI
        assert all(p.a == "utente" for p in PASSI["operatore"])
        assert "g2" not in [p.nome for p in PASSI["operatore"]]
        assert "op_g2_admin" not in TXT and "Da 2 giorni su Aurya" not in TXT

    def test_stato_operatore_ha_tre_fatti(self):
        blocco = SEQ.split("async def stato_operatore")[1].split("async def _destinatario_org")[0]
        for chiave in ('"pagina": pagina', '"listino": n_servizi > 0', '"n_servizi": n_servizi', '"online":', '"ritiro":'):
            assert chiave in blocco, chiave
        assert "pagina = bool(slug) and bool(pp.get(\"bio\"))" in blocco

    def test_pagina_online_parte_alla_nascita_della_pagina(self):
        from services.sequenze import PASSI
        p = next(p for p in PASSI["operatore"] if p.nome == "profilo_online")
        assert p.condizione == "pagina" and p.giorno is None

    def test_le_varianti_np_dicono_il_vero(self):
        from services import email_sequenze as T
        base = {"nome": "Giulia", "email": "g@esempio.it", "org": {"name": "Studio"}, "fondatori": None}
        senza = {**base, "stato": {"pagina": False, "listino": False, "n_servizi": 0, "online": False,
                                   "ritiro": False, "slug": None, "iban": False}}
        meta = {**base, "stato": {"pagina": True, "listino": False, "n_servizi": 0, "online": False,
                                  "ritiro": True, "slug": "studio", "iban": False}}
        for fn in (T.op_np5, T.op_np10, T.op_np15):
            o1, c1 = fn(senza)
            o2, c2 = fn(meta)
            assert o1 != o2 or fn in (T.op_np10, T.op_np15), fn.__name__   # FL3: np10/np15 stesso oggetto nelle due varianti (founder)
            assert "/public-profile" in c1 and "/listino" not in c1
            assert ("/listino" in c2 and "/public-profile" not in c2) or fn is T.op_np15   # FL3: np15 = «Apro la mia pagina»
            assert "non è ancora online" not in c2                       # FL3: con la pagina, mai «non e' online»
        _, c15 = T.op_np15(senza)
        assert "resta aperto, gratis" in c15 and "grazie di essere su Aurya" in c15   # FL3 (5/10): testo del founder

    def test_il_blocco_listino_della_pagina_online(self):
        from services import email_sequenze as T
        assert "prossimo passo è il listino" in T._blocco_listino({"n_servizi": 0})
        assert "un servizio" in T._blocco_listino({"n_servizi": 1})
        assert "4 servizi" in T._blocco_listino({"n_servizi": 4})
        # un link, non un secondo bottone: l'email fa una cosa sola
        assert 'class="btn"' not in T._blocco_listino({"n_servizi": 0})


class TestBugEIncoerenze:
    def test_quota_80_usa_le_chiavi_che_esistono(self):
        assert 'chiave = "quota_warning" if level == "warn_80" else "quota_exceeded"' in QUOTA
        assert 'f"quota_{level}_subject"' not in QUOTA and 'f"quota_{level}_intro"' not in QUOTA
        for lingua_blocco in ES.split("_TRANSLATIONS")[1:2] or [ES]:
            pass
        for k in ("quota_warning_subject", "quota_warning_intro", "quota_exceeded_subject", "quota_exceeded_intro"):
            assert ES.count(f'"{k}"') >= 4, f"{k} manca in una lingua"

    def test_pagamento_a_rischio_risponde_al_cliente(self):
        blocco = PAY.split("async def send_at_risk_to_operator")[1]
        assert 'reply_to=order.get("customer_email") or None' in blocco
        assert "reply_to=None, store_name=" not in blocco

    def test_la_nota_gdpr_parte_davvero(self):
        from services.email_service import send_admin_notification  # noqa: F401
        assert "send_admin_notification(" in PORTAL
        assert "def send_admin_notification(subject: str, body: str)" in ES
        assert "CASELLA_AURYA, subject" in ES.split("def send_admin_notification")[1][:600]

    def test_il_lead_va_alla_casella_aurya(self):
        assert '"info@aurya.life"' not in LEADS
        assert "send_email(CASELLA_AURYA," in LEADS

    def test_il_vecchio_benvenuto_non_esiste_piu(self):
        import services.email_service as es
        assert not hasattr(es, "send_welcome")
        for f in ("routers/auth.py", "services/auth_service.py"):
            assert "send_welcome" not in (BACKEND / f).read_text(encoding="utf-8"), f

    def test_alert_critici_a_un_admin_piu_ops(self):
        blocco = CRIT.split("async def _collect_recipients")[1].split("def _build_alert_html")[0]
        assert "find_one(" in blocco and 'sort=[("created_at", 1)]' in blocco
        assert "async for user in users_collection.find(" not in blocco
