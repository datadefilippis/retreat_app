"""Interruttori d'ambiente letti al momento della chiamata (24/9/2026).

Letti a ogni chiamata, non all'import: cosi' i test li accendono con
monkeypatch e prod li accende con un riavvio del backend, senza
ricostruire nulla. Spenti = comportamento identico a prima.
"""
import os

_ACCESO = ("1", "true", "yes", "on")


def _acceso(nome: str) -> bool:
    return (os.getenv(nome) or "").strip().lower() in _ACCESO


def login_senza_verifica() -> bool:
    """E6 (founder 24/9): l'operatore entra subito dopo la registrazione;
    la verifica dell'email arriva «per uso» (primo clic su un link di
    una nostra email) e resta obbligatoria solo per soldi e terzi
    (Stripe/IBAN, pagamenti, embed, pagina online)."""
    return _acceso("LOGIN_SENZA_VERIFICA")
