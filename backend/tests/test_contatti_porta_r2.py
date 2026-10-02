"""R2 + R5 (25/9/2026 sera) — i recapiti dell'operatore dietro la porta
dell'account Aurya, con il lead all'operatore; informativa v2.8.

  R5  privacy/termini v2.8: account per contatti e prenotazione, riga
      7-ter (richieste di contatto, 12 mesi), Cerchio mai condizione,
      verifica «per uso» (E6); tag e hash allineati.
  R2  interruttore CONTATTI_DIETRO_PORTA (spento = come prima): il profilo
      JSON dice solo cosa c'e' (contacts.porta + has_*), /contatti vuole il
      Bearer piattaforma (401 «account_richiesto»), registra UNA richiesta
      per (operatore, account, giorno) con TTL 12 mesi; l'operatore la vede
      in GET /organizations/current/contact-requests e nella pagina Clienti;
      il telefono esce dal LocalBusiness; /@slug non cambia.
"""
import hashlib
import os
from pathlib import Path

import pytest
import requests

RADICE = Path(__file__).resolve().parents[2]
BACKEND = RADICE / "backend"
FE = RADICE / "frontend" / "src"
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8000")

PUBLIC = (BACKEND / "routers" / "public.py").read_text(encoding="utf-8")
ORGS = (BACKEND / "routers" / "organizations.py").read_text(encoding="utf-8")
SHELL = (BACKEND / "routers" / "seo_shell.py").read_text(encoding="utf-8")
FLAGS = (BACKEND / "core" / "flags.py").read_text(encoding="utf-8")
COMP = (FE / "features" / "storefront" / "components" / "ContattiOperatore.jsx").read_text(encoding="utf-8")
PROF = (FE / "features" / "storefront" / "OperatorProfilePage.js").read_text(encoding="utf-8")
ABOUT = (FE / "features" / "storefront" / "components" / "StoreAbout.jsx").read_text(encoding="utf-8")
LINK = (FE / "features" / "storefront" / "LinkPage.js").read_text(encoding="utf-8")
CLIENTI = (FE / "features" / "customers-mgmt" / "CustomersMgmtPage.js").read_text(encoding="utf-8")


class TestR5Legale:
    def test_v28_e_hash_allineato(self):
        from core.legal_versions import CURRENT_VERSION_HASH, CURRENT_VERSION_TAG
        assert CURRENT_VERSION_TAG == "v2.10"    # v2.8 R5 → v2.9 ET4 → v2.10 OP1 (2/10)
        priv = (BACKEND / "legal" / "privacy_it.md").read_text("utf-8")
        terms = (BACKEND / "legal" / "terms_it.md").read_text("utf-8")
        atteso = hashlib.sha256((priv + "\n\n--- TERMS BUNDLE ---\n\n" + terms).encode()).hexdigest()[:16]
        assert CURRENT_VERSION_HASH == atteso
        assert "| 7-ter |" in priv and "12 mesi, poi eliminazione automatica" in priv
        assert "Richieste di contatto agli Operatori (art. 4, riga 7-ter) | 12 mesi" in priv
        assert "l'iscrizione al Cerchio (art. 4, riga 7-bis) resta separata e facoltativa" in priv
        assert "non e' mai condizione per prenotare" in terms
        assert "consultabili dagli Utenti che dispongono di un account Aurya" in terms
        assert "(/@nome) resta liberamente consultabile" in terms
        assert "verificato anche al primo utilizzo di un link personale" in terms
        # il Cerchio resta consenso specifico e non preselezionato (7-bis intatta)
        assert "specifico, non preselezionato e revocabile" in priv


class TestR2Backend:
    def test_flag_spento_di_default(self, monkeypatch):
        monkeypatch.delenv("CONTATTI_DIETRO_PORTA", raising=False)
        from core.flags import contatti_dietro_porta
        assert contatti_dietro_porta() is False
        monkeypatch.setenv("CONTATTI_DIETRO_PORTA", "on")
        assert contatti_dietro_porta() is True

    def test_profilo_e_contatti_dietro_la_porta(self):
        blocco = PUBLIC[PUBLIC.index("if contatti_dietro_porta():\n        _mostra"):][:700]
        for k in ('"has_phone"', '"has_email"', '"has_instagram"', '"has_facebook"', '"has_website"', '"porta": True', 'out["socials"] = {}'):
            assert k in blocco, k
        rotta = PUBLIC[PUBLIC.index('@router.get("/operator/{org_slug}/contatti")'):][:2600]
        assert "if not contatti_dietro_porta():" in rotta                      # spento = ieri
        assert 'raise HTTPException(status_code=401, detail="account_richiesto")' in rotta
        assert 'for k in ("instagram", "facebook", "website") if pp.get(k)' in rotta
        assert "await _registra_richiesta_contatto(org, identita, request)" in rotta
        # 26/9 (founder): chi e' gia' dentro con qualunque cappello non rifa' l'accesso;
        # il lead vale per clienti e operatori di ALTRE org, mai per la regia
        assert 'if identita.get("registra") and identita.get("org_id") != org.get("id"):' in rotta
        assert "send_email" not in rotta and "email_service" not in rotta          # nessuna email a nessuno
        # il lead: una riga per operatore/account/giorno, TTL 12 mesi, mai bloccante
        reg = PUBLIC[PUBLIC.index("async def _registra_richiesta_contatto"):][:1800]
        assert '[("org_id", 1), ("platform_account_id", 1), ("giorno", 1)], unique=True' in reg
        assert 'create_index("scade_il", expireAfterSeconds=0)' in reg and '"$setOnInsert"' in reg
        # il Bearer: solo type=platform, account attivo, mai enumerazione
        acc = PUBLIC[PUBLIC.index("async def _identita_dal_bearer"):][:2200]
        assert 'if tipo == "platform":' in acc and 'if tipo in (None, "access"):' in acc
        assert '"registra": not regia' in acc and 'regia = user.get("role") == "system_admin"' in acc

    def test_operatore_e_schema(self):
        rotta = ORGS[ORGS.index('@router.get("/current/contact-requests")'):][:1200]
        assert "Depends(require_admin)" in rotta and "timedelta(days=90)" in rotta and '"persone": persone' in rotta
        assert "and not contatti_dietro_porta():\n        jsonld[\"telephone\"]" in SHELL

    def test_dal_vivo_secondo_lo_stato_del_flag(self):
        r = requests.get(f"{BASE_URL}/api/public/operator/masseria-demo", timeout=15)
        if r.status_code != 200:
            pytest.skip("org demo non pubblica in locale")
        c = r.json().get("contacts") or {}
        cc = requests.get(f"{BASE_URL}/api/public/operator/masseria-demo/contatti", timeout=15)
        if c.get("porta"):
            assert set(c) == {"has_phone", "has_email", "has_instagram", "has_facebook", "has_website", "porta"}
            assert r.json().get("socials") == {}
            assert cc.status_code == 401 and cc.json().get("detail") == "account_richiesto"
        else:
            assert "has_instagram" not in c and cc.status_code in (200, 429)
        assert requests.get(f"{BASE_URL}/api/organizations/current/contact-requests", timeout=10).status_code in (401, 403)


class TestR2Frontend:
    def test_il_componente_decide_dal_json(self):
        assert "export function haContatti(data)" in COMP and "if (c.porta) return" in COMP
        assert "if (!c.porta) {" in COMP                                   # spento = i blocchi di ieri
        assert "<MostraEmail slug={slug}" in COMP                          # email al clic resta nel ramo spento
        for tid in ("contatti-aperti", "contatti-porta", "contatti-carico", "contatti-errore"):
            assert f'data-testid="{tid}"' in COMP, tid
        assert "client.get(`/public/operator/${slug}/contatti`)" in COMP
        assert "if (err?.response?.status === 401) { setStato('porta'); return; }" in COMP
        assert "if (localStorage.getItem('token')) return 'gestionale';" in COMP       # anche la sessione del gestionale
        assert "const client = sessione() === 'gestionale' ? api : platformApi;" in COMP
        assert '<PortaAurya contesto="contatti" onDentro={() => apri()} />' in COMP
        # 26/9 (founder): niente frase sull'operatore nel riquadro; l'informazione sta nell'Informativa (7-ter)
        assert "contatti-avviso" not in COMP and "L’operatore vedrà" not in COMP

    def test_le_pagine_montano_il_componente_e_la_link_page_no(self):
        assert '<ContattiOperatore slug={org_slug} data={data} variante="profilo" />' in PROF
        assert "haContatti(data)" in PROF and "contacts?.public_email" not in PROF and "socials.instagram" not in PROF
        assert '<ContattiOperatore slug={slug} data={data} variante="store" />' in ABOUT
        assert "ContattiOperatore" not in LINK and "/contatti" not in LINK      # /@slug resta libera
        # 26/9 (founder): la card «Chi ha chiesto i tuoi contatti» NON si mostra
        # all'operatore; i dati restano (12 mesi) per poterla riaccendere
        assert 'data-testid="richieste-contatto"' not in CLIENTI and "contactRequests" not in CLIENTI


class TestRitornoDopoLaConferma:
    """26/9 (founder, punto 2): il link di verifica riporta alla pagina
    dell'operatore — SOLO quando il signup nasce dalla porta dei contatti.
    Isolato: senza `return_to` link, pagina e risposte sono quelli di ieri."""

    def test_backend_isolato(self):
        router = (BACKEND / "routers" / "platform_accounts.py").read_text(encoding="utf-8")
        svc = (BACKEND / "services" / "platform_account_service.py").read_text(encoding="utf-8")
        assert "return_to: Optional[str] = Field(None, max_length=500)" in router
        assert "return_to=body.return_to)" in router
        invio = svc[svc.index("def _send_verify_email"):][:1400]
        assert "from services.verifica_email import percorso_interno" in invio       # mai un open redirect
        assert '_ritorno = percorso_interno(return_to) if return_to else "/"' in invio
        assert 'if _ritorno != "/":' in invio and "&next=" in invio
        assert 'return {"status": "verified", "email": account.get("email")}' in svc
        assert svc.count("_send_verify_email(") == 2      # def + signup: nessun altro chiamante cambia

    def test_il_link_porta_next_solo_se_chiesto(self, monkeypatch):
        """Deterministico: si cattura l'HTML dell'email. Con return_to interno
        il link ha &next=…; senza, o con un URL esterno, il link e' quello di ieri."""
        import services.email_service as es
        from services.platform_account_service import _send_verify_email
        catturate = []
        monkeypatch.setattr(es, "send_email", lambda to, subject, html, **kw: catturate.append(html))
        _send_verify_email("a@example.com", "TOK1", "Anna", return_to="/o/anpoche")
        _send_verify_email("b@example.com", "TOK2", None)
        _send_verify_email("c@example.com", "TOK3", None, return_to="https://evil.example/x")
        assert "/account/verifica?token=TOK1&next=/o/anpoche" in catturate[0]
        assert "token=TOK2" in catturate[1] and "next=" not in catturate[1]
        assert "token=TOK3" in catturate[2] and "next=" not in catturate[2] and "evil" not in catturate[2]

    def test_frontend_isolato(self):
        porta = (FE / "features" / "account" / "PortaAurya.jsx").read_text(encoding="utf-8")
        assert "...(contesto === 'contatti' ? { return_to: window.location.pathname } : {})," in porta
        verifica = (FE / "features" / "account" / "AccountVerifyEmailPage.js").read_text(encoding="utf-8")
        assert "const next = rawNext.startsWith('/') && !rawNext.startsWith('//') ? rawNext : '';" in verifica
        assert 'data-testid="verify-torna"' in verifica and "entraInAurya(emailConfermata, next)" in verifica
        assert "{next ? (" in verifica                                     # senza next: la pagina di sempre
        assert '<ContattiOperatore slug={org_slug} data={data} variante="profilo" />' in PROF
        assert 'contesto="contatti"' in COMP

    def test_percorso_interno(self):
        from services.verifica_email import percorso_interno
        assert percorso_interno("/o/anpoche") == "/o/anpoche"
        assert percorso_interno("https://evil.example/x") == "/"
        assert percorso_interno("//evil.example") == "/" and percorso_interno("") == "/"
