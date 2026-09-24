"""Lotto C · Igiene invii e sequenze (24/9/2026) — le guardie.

C1 header List-Unsubscribe solo con unsubscribe_url; C2 gate anche sugli
iscritti + webhook Brevo che li segna + niente bypass_gate sulle email
editoriali; C3 link verificanti con ripiego; C4 interruttore
CERCHIO_SINGOLO_OPTIN (spento = tutto come oggi) e sospensione a 90 giorni
che segna e non cancella.
"""
import asyncio
import inspect
import sys
import types
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
SEQ = (BACKEND / "services" / "sequenze.py").read_text(encoding="utf-8")
REM = (BACKEND / "services" / "cerchio_reminder.py").read_text(encoding="utf-8")
GATE = (BACKEND / "services" / "email_gate.py").read_text(encoding="utf-8")
HOOK = (BACKEND / "routers" / "webhooks" / "brevo.py").read_text(encoding="utf-8")
BG = (BACKEND / "services" / "background_service.py").read_text(encoding="utf-8")
SUBS = (BACKEND / "routers" / "subscribers.py").read_text(encoding="utf-8")


def _off(monkeypatch):
    monkeypatch.delenv("CERCHIO_SINGOLO_OPTIN", raising=False)


def _on(monkeypatch):
    monkeypatch.setenv("CERCHIO_SINGOLO_OPTIN", "1")


# ── C1 ───────────────────────────────────────────────────────────────────────

class TestC1Header:
    def test_send_email_ha_il_parametro_nuovo_e_nulla_di_rotto(self):
        from services.email_service import send_email
        p = inspect.signature(send_email).parameters
        assert "unsubscribe_url" in p and p["unsubscribe_url"].default is None
        assert p["unsubscribe_url"].kind is inspect.Parameter.KEYWORD_ONLY
        assert "bypass_gate" in p and p["bypass_gate"].default is False

    def test_gli_header_ci_sono_solo_con_unsubscribe_url(self):
        import services.email_service as es
        senza = es._payload_brevo("a@b.it", "x", "<p>x</p>")
        assert "headers" not in senza, "le transazionali non cambiano"
        url = "https://aurya.life/newsletter/preferenze/TOKEN"
        con = es._payload_brevo("a@b.it", "x", "<p>x</p>", unsubscribe_url=url)
        h = con["headers"]
        assert h["List-Unsubscribe-Post"] == "List-Unsubscribe=One-Click"
        assert h["List-Unsubscribe"] == f"<mailto:{es.CASELLA_AURYA}?subject=unsubscribe>, <{url}>"
        assert con["replyTo"] == senza["replyTo"] and con["to"] == senza["to"]
        assert "headers" not in es._payload_brevo("a@b.it", "x", "<p>x</p>", unsubscribe_url=None)

    def test_il_link_dell_header_e_nudo_e_quello_del_corpo_verificante(self):
        from services import email_sequenze as T
        assert T.url_preferenze_nudo("TOK") == f"{T.APP_URL}/newsletter/preferenze/TOK"
        assert T.url_preferenze_nudo("") == f"{T.APP_URL}/newsletter"

    def test_le_sequenze_del_cerchio_passano_l_url_e_non_il_bypass(self, monkeypatch):
        import services.email_service as es
        from services import sequenze as S
        chiamate = []
        monkeypatch.setattr(es, "send_email", lambda *a, **k: chiamate.append((a, k)) or True)
        monkeypatch.setattr(es, "_configured", True)
        cerchio = S.PASSI["cerchio"][0]
        ctx = {"nome": "Giulia", "email": "g@esempio.it", "token": "TOK", "citta": "", "interessi": [],
               "travel": "", "porta": "altro", "vuole_ritiri": True}
        assert S._manda(cerchio, ctx) is True
        a, k = chiamate[-1]
        assert a[0] == "g@esempio.it"
        assert k["unsubscribe_url"] == f"{S.T.APP_URL}/newsletter/preferenze/TOK"
        assert "bypass_gate" not in k, "le editoriali passano dal gate"
        # operatore: niente token, niente header (ma nemmeno bypass)
        op = next(p for p in S.PASSI["operatore"] if p.nome == "np5")
        ctx_op = {"nome": "Marta", "email": "m@esempio.it", "org": {"name": "S"}, "fondatori": None,
                  "stato": {"pagina": False, "listino": False, "n_servizi": 0, "online": False,
                            "ritiro": False, "slug": None, "iban": False}}
        assert S._manda(op, ctx_op) is True
        _, k2 = chiamate[-1]
        assert k2["unsubscribe_url"] is None and "bypass_gate" not in k2

    def test_il_promemoria_passa_l_url_e_non_il_bypass(self, monkeypatch):
        _off(monkeypatch)
        import services.email_service as es
        from services import cerchio_reminder as R
        chiamate = []
        monkeypatch.setattr(es, "send_email", lambda *a, **k: chiamate.append((a, k)) or True)
        assert R._send_reminder_email("g@esempio.it", "Giulia", "TOK") is True
        a, k = chiamate[-1]
        assert a[1] == "Ti manca un clic per entrare nel Cerchio di Aurya"
        assert k["unsubscribe_url"].endswith("/newsletter/preferenze/TOK")
        assert "bypass_gate" not in k


# ── C2 ───────────────────────────────────────────────────────────────────────

class _Coll:
    def __init__(self, doc=None, boom=False):
        self.doc, self.boom = doc, boom

    def find_one(self, *_a, **_k):
        if self.boom:
            raise RuntimeError("db giu'")
        return self.doc


class _Db(dict):
    def __getitem__(self, k):
        return dict.get(self, k) or _Coll()


class TestC2Gate:
    def test_il_gate_legge_anche_gli_iscritti(self, monkeypatch):
        import services.email_gate as G
        assert "aurya_subscribers" in G._COLLEZIONI and "users" in G._COLLEZIONI
        G.invalidate_cache()
        monkeypatch.setattr(G, "_get_db", lambda: _Db(aurya_subscribers=_Coll({"email_status": "bounced"})))
        assert G.is_email_blocked("Iscritto@Esempio.it") == (True, "bounced")
        # stessa cache: la seconda lettura non tocca il db
        monkeypatch.setattr(G, "_get_db", lambda: _Db(aurya_subscribers=_Coll(boom=True)))
        assert G.is_email_blocked("iscritto@esempio.it") == (True, "bounced")
        G.invalidate_cache()
        # complaint non blocca (stessa regola di sempre)
        monkeypatch.setattr(G, "_get_db", lambda: _Db(aurya_subscribers=_Coll({"email_status": "complaint"})))
        assert G.is_email_blocked("altro@esempio.it") == (False, None)
        G.invalidate_cache()
        # fail-open
        monkeypatch.setattr(G, "_get_db", lambda: _Db(aurya_subscribers=_Coll(boom=True)))
        assert G.is_email_blocked("terzo@esempio.it") == (False, None)
        G.invalidate_cache()

    def test_il_webhook_segna_l_iscritto(self):
        from routers.webhooks import brevo as W
        now = datetime(2026, 9, 24, 12, 0, tzinfo=timezone.utc)
        b = W._aggiornamento_iscritto("bounced", now)
        assert b == {"email_status": "bounced", "email_status_at": now}
        u = W._aggiornamento_iscritto("unsubscribed", now)
        assert u["status"] == "unsubscribed" and u["unsubscribed_by"] == "brevo"
        assert u["unsubscribed_at"] == now and u["email_status"] == "unsubscribed"
        assert W._aggiornamento_iscritto("complaint", now)["email_status"] == "complaint"
        assert W.TRACKED_EVENTS["hard_bounce"] == "bounced" and W.TRACKED_EVENTS["spam"] == "complaint"
        assert "db.aurya_subscribers.update_one" in HOOK
        assert "_aggiornamento_iscritto(new_status, now_dt)" in HOOK

    def test_niente_bypass_sulle_editoriali_si_su_conferma_e_magic_link(self):
        manda = SEQ[SEQ.index("def _manda"):SEQ.index("async def _marca")]
        utente = manda[manda.index("risposte = T.risposte_a()"):]
        assert "bypass_gate" not in utente
        assert "send_email(CASELLA_AURYA, oggetto, _wrap_template(corpo, \"it\"), bypass_gate=True)" in manda
        assert "bypass_gate" not in REM
        # non nostri, ma il contratto li vuole cosi': conferma e magic link scavalcano il gate
        assert SUBS.count("bypass_gate=True") >= 2


# ── C3 ───────────────────────────────────────────────────────────────────────

class TestC3LinkVerificanti:
    def test_ripiego_sul_link_nudo_se_il_modulo_manca(self, monkeypatch):
        from services import email_sequenze as T
        monkeypatch.setitem(sys.modules, "services.verifica_email", None)   # import → ImportError
        assert T._link("a@b.it", "/meditazioni") == f"{T.APP_URL}/meditazioni"

    def test_usa_link_verificante_quando_c_e(self, monkeypatch):
        from services import email_sequenze as T
        finto = types.ModuleType("services.verifica_email")
        finto.link_verificante = lambda email, path: f"https://x/v/{email}?to={path}"
        monkeypatch.setitem(sys.modules, "services.verifica_email", finto)
        assert T._link("a@b.it", "/meditazioni") == "https://x/v/a@b.it?to=/meditazioni"
        ctx = {"nome": "G", "email": "a@b.it", "token": "TOK", "citta": "", "interessi": [],
               "travel": "", "porta": "meditazioni", "vuole_ritiri": False}
        for fn in (T.benvenuto_cerchio_meditazioni, T.benvenuto_cerchio_generico, T.benvenuto_cerchio_ritiri):
            _, corpo = fn(ctx)
            assert "https://x/v/a@b.it?to=/meditazioni" in corpo, fn.__name__
            assert "https://x/v/a@b.it?to=/newsletter/preferenze/TOK" in corpo, fn.__name__
        # e se la funzione solleva, il link nudo
        finto.link_verificante = lambda email, path: 1 / 0
        assert T._link("a@b.it", "/meditazioni") == f"{T.APP_URL}/meditazioni"

    def test_il_promemoria_usa_il_link_verificante(self, monkeypatch):
        _off(monkeypatch)
        import services.email_service as es
        from services import cerchio_reminder as R
        finto = types.ModuleType("services.verifica_email")
        finto.link_verificante = lambda email, path: f"https://x/v/{email}?to={path}"
        monkeypatch.setitem(sys.modules, "services.verifica_email", finto)
        chiamate = []
        monkeypatch.setattr(es, "send_email", lambda *a, **k: chiamate.append((a, k)) or True)
        R._send_reminder_email("g@esempio.it", None, "TOK")
        a, _ = chiamate[-1]
        assert "https://x/v/g@esempio.it?to=/newsletter/conferma/TOK" in a[2]


# ── C4 ───────────────────────────────────────────────────────────────────────

class TestC4Interruttore:
    def test_spento_e_il_filtro_di_oggi(self, monkeypatch):
        _off(monkeypatch)
        from services import sequenze as S
        assert S.singolo_optin() is False
        assert S.filtro_sub() == {"status": "confirmed", "consent": True} == S._FILTRO_SUB
        assert '"status": "confirmed", "consent": True' in SEQ
        sub = {"confirmed_at": None, "created_at": datetime(2026, 9, 1, tzinfo=timezone.utc)}
        assert S.orologio_sub(sub) is None, "spento: senza conferma non c'e' orologio"
        conf = {"confirmed_at": datetime(2026, 9, 2, tzinfo=timezone.utc), "created_at": datetime(2026, 9, 1, tzinfo=timezone.utc)}
        assert S.orologio_sub(conf) == datetime(2026, 9, 2, tzinfo=timezone.utc)

    def test_acceso_e_il_filtro_nuovo(self, monkeypatch):
        _on(monkeypatch)
        from services import sequenze as S
        assert S.singolo_optin() is True
        assert S.filtro_sub() == {"status": {"$in": ["pending", "confirmed"]}, "consent": True,
                                  "sospeso_at": {"$exists": False}}
        assert S._FILTRO_SUB == {"status": "confirmed", "consent": True}, "la costante di oggi non cambia"
        creato = datetime(2026, 9, 1, tzinfo=timezone.utc)
        assert S.orologio_sub({"created_at": creato}) == creato
        conf = datetime(2026, 9, 2, tzinfo=timezone.utc)
        assert S.orologio_sub({"confirmed_at": conf, "created_at": creato}) == conf, "la conferma vince"
        assert "os.getenv(\"CERCHIO_SINGOLO_OPTIN\")" in SEQ, "si legge a ogni chiamata"

    def test_invia_subito_se_singolo(self, monkeypatch):
        from services import sequenze as S
        chiamate = []

        async def finto(pubblico, email):
            chiamate.append((pubblico, email))
            return "benvenuto_altro"
        monkeypatch.setattr(S, "invia_subito", finto)
        _off(monkeypatch)
        assert asyncio.run(S.invia_subito_se_singolo("a@b.it")) is None and chiamate == []
        _on(monkeypatch)
        assert asyncio.run(S.invia_subito_se_singolo("a@b.it")) == "benvenuto_altro"
        assert chiamate == [("cerchio", "a@b.it")]

    def test_il_giro_del_cerchio_guarda_created_at_solo_acceso(self):
        giro = SEQ[SEQ.index("async def _giro_cerchio"):SEQ.index("async def run_sequenze_sweep")]
        assert "if singolo_optin():" in giro and '"created_at": {"$gte": piu_vecchia}' in giro
        assert "filtro_sub()" in giro and "orologio_sub(sub)" in giro

    def test_il_promemoria_cambia_parole_solo_acceso(self, monkeypatch):
        from services import cerchio_reminder as R
        _off(monkeypatch)
        o, c = R._testo_promemoria("Ciao,", "https://u", "")
        assert o == "Ti manca un clic per entrare nel Cerchio di Aurya"
        assert "Entro nel Cerchio" in c and "l'ultima\n            email che ricevi da noi" in c
        _on(monkeypatch)
        o, c = R._testo_promemoria("Ciao,", "https://u", "")
        assert o == "Un clic e si aprono le meditazioni riservate"
        assert "la Lettera ti arriva" in c and "riservati" in c and "ultima" not in c
        assert 'href="https://u"' in c
        assert "ogni due settimane" not in REM


class TestC4Sospensione:
    def test_costanti_e_job(self):
        from services import cerchio_reminder as R
        assert R.SOSPENSIONE_DOPO_GIORNI == 90 and R._MAX_SOSPENSIONI_PER_TICK == 200
        assert R.REMINDER_AFTER_HOURS == 48 and R.REMINDER_WINDOW_DAYS == 7
        assert 'name="cerchio_sospensione_job"' in BG and 'name="cerchio_reminder_job"' in BG
        job = BG[BG.index("async def _cerchio_sospensione_job"):BG.index("async def _sequenze_job")]
        assert "interval_seconds = 6 * 3600" in job and "run_cerchio_sospensione_sweep" in job

    def test_segna_e_non_cancella(self):
        corpo = REM[REM.index("async def run_cerchio_sospensione_sweep"):]
        assert '{"$set": {"sospeso_at": now}}' in corpo
        assert "delete_one" not in corpo and "delete_many" not in corpo
        for chiave in ('"status": "pending"', '"consent": True', '"verificato_at": {"$exists": False}',
                       '"sospeso_at": {"$exists": False}', '"created_at": {"$lt": soglia}'):
            assert chiave in corpo, chiave

    def test_spento_non_tocca_il_db(self, monkeypatch):
        _off(monkeypatch)
        import database
        from services import cerchio_reminder as R
        monkeypatch.setattr(database, "db", None)   # se lo toccasse, esploderebbe
        assert asyncio.run(R.run_cerchio_sospensione_sweep()) == {"candidati": 0, "sospesi": 0}

    def test_acceso_segna_i_pending_vecchi(self, monkeypatch):
        _on(monkeypatch)
        import database
        from services import cerchio_reminder as R
        now = datetime(2026, 9, 24, tzinfo=timezone.utc)
        scritture = []

        class Cur:
            def __init__(self, docs):
                self.docs = docs

            def limit(self, n):
                assert n == 200
                return self

            def __aiter__(self):
                async def gen():
                    for d in self.docs:
                        yield d
                return gen()

        class Coll:
            def find(self, filtro, proiezione):
                assert filtro["created_at"]["$lt"] == now - timedelta(days=90)
                return Cur([{"email": "vecchio@esempio.it"}, {"email": ""}])

            async def update_one(self, filtro, update):
                scritture.append((filtro, update))
                return types.SimpleNamespace(modified_count=1)

        monkeypatch.setattr(database, "db", types.SimpleNamespace(aurya_subscribers=Coll()))
        assert asyncio.run(R.run_cerchio_sospensione_sweep(now)) == {"candidati": 2, "sospesi": 1}
        filtro, update = scritture[0]
        assert update == {"$set": {"sospeso_at": now}} and filtro["email"] == "vecchio@esempio.it"
        assert filtro["sospeso_at"] == {"$exists": False} and filtro["verificato_at"] == {"$exists": False}
