"""E6 (24/9/2026, founder) — login operatore SENZA verifica dell'email,
dietro interruttore LOGIN_SENZA_VERIFICA (default spento).

Tenuto fermo qui:
  1. spento = identico a prima: login rifiutato, get_verified_user 403;
  2. acceso = si entra e get_verified_user lascia passare; ma il
     cancello RIGIDO (get_verified_user_strict) resta chiuso, e lo usano
     pagamenti, connessioni Stripe e fatturazione;
  3. /auth/me espone `verifica_morbida` e il client rimanda a
     /verify-email-required solo se e' falso; il banner esiste;
  4. il flag si legge a ogni chiamata (monkeypatch funziona).
"""
import asyncio
from pathlib import Path

import pytest
from fastapi import HTTPException

BACKEND = Path(__file__).resolve().parents[1]
FE = BACKEND.parent / "frontend" / "src"


def _run(coro):
    return asyncio.run(coro)


class TestInterruttore:
    def test_spento_di_default(self, monkeypatch):
        monkeypatch.delenv("LOGIN_SENZA_VERIFICA", raising=False)
        from core.flags import login_senza_verifica
        assert login_senza_verifica() is False
        monkeypatch.setenv("LOGIN_SENZA_VERIFICA", "1")
        assert login_senza_verifica() is True

    def test_gate_morbido_e_rigido(self, monkeypatch):
        from auth import get_verified_user, get_verified_user_strict
        utente = {"role": "admin", "email": "x@y.it", "email_verified": False}
        monkeypatch.delenv("LOGIN_SENZA_VERIFICA", raising=False)
        with pytest.raises(HTTPException) as e:
            _run(get_verified_user(utente))
        assert e.value.detail["error"] == "email_not_verified"
        monkeypatch.setenv("LOGIN_SENZA_VERIFICA", "1")
        assert _run(get_verified_user(utente)) is utente          # morbido: passa
        with pytest.raises(HTTPException):
            _run(get_verified_user_strict(utente))                 # rigido: no
        assert _run(get_verified_user_strict({**utente, "email_verified": True})) is not None


class TestDoveRestaRigido:
    def test_soldi_e_terzi(self):
        for f in ("routers/payments.py", "routers/payment_connections.py", "routers/billing.py"):
            src = (BACKEND / f).read_text(encoding="utf-8")
            assert "get_verified_user_strict as get_verified_user" in src, f
        src = (BACKEND / "auth.py").read_text(encoding="utf-8")
        assert "async def get_verified_user_strict" in src
        # l'embed resta rigido per conto suo
        assert "async def require_verified_admin" in src

    def test_la_pagina_va_online_solo_con_email_verificata(self):
        org = (BACKEND / "routers" / "organizations.py").read_text(encoding="utf-8")
        i = org.index("async def _ensure_public_surface")
        blocco = org[i:i + 2200]
        assert "login_senza_verifica()" in blocco
        assert 'if titolare and not titolare.get("email_verified", False):\n            return' in blocco
        # e al primo clic verificante la pagina esce da sola, dai due punti
        assert "from routers.organizations import _ensure_public_surface" in (BACKEND / "routers" / "auth.py").read_text()
        assert "from routers.organizations import _ensure_public_surface" in (BACKEND / "services" / "verifica_email.py").read_text()

    def test_login_rispetta_il_flag(self):
        src = (BACKEND / "services" / "auth_service.py").read_text(encoding="utf-8")
        assert 'if not is_sysadmin and not login_senza_verifica():' in src
        assert 'raise ValueError("Email not verified")' in src


class TestClient:
    def test_me_espone_verifica_morbida(self):
        assert "verifica_morbida: bool = False" in (BACKEND / "models" / "user.py").read_text()
        assert "verifica_morbida=login_senza_verifica()" in (BACKEND / "services" / "auth_service.py").read_text()

    def test_il_client_rimanda_solo_se_rigido(self):
        app = (FE / "App.js").read_text(encoding="utf-8")
        assert 'user.email_verified === false && !user.verifica_morbida' in app
        fq = (FE / "features" / "frequenze" / "FrequenzePage.js").read_text(encoding="utf-8")
        assert "user.email_verified === false && !user.verifica_morbida" in fq
        banner = (FE / "components" / "BannerVerificaEmail.js").read_text(encoding="utf-8")
        assert 'data-testid="banner-verifica-email"' in banner
        assert "!user.verifica_morbida" in banner and "resendVerification" in banner
        assert "<BannerVerificaEmail />" in (FE / "components" / "Layout.js").read_text(encoding="utf-8")
