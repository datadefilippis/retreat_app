"""24/9/2026 — il punto di sutura fra Lotto B (subscribe) e Lotto C
(invia_subito_se_singolo): con l'interruttore acceso la prima email e'
il benvenuto coi link verificanti; spento resta l'email di conferma."""
from pathlib import Path

SRC = (Path(__file__).resolve().parents[1] / "routers" / "subscribers.py").read_text(encoding="utf-8")


def test_subscribe_usa_il_benvenuto_solo_con_interruttore():
    i = SRC.index("inviato = await invia_subito_se_singolo(email) if singolo_optin() else None")
    blocco = SRC[i:i + 400]
    assert "if not inviato:" in blocco and "_send_confirm_email(" in blocco
    # spento: singolo_optin() e' falso e la conferma parte come sempre
    from services.sequenze import singolo_optin
    import os
    os.environ.pop("CERCHIO_SINGOLO_OPTIN", None)
    assert singolo_optin() is False
