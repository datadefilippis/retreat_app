"""24/9/2026 — il punto di sutura fra Lotto B (subscribe) e Lotto C
(invia_subito_se_singolo): con l'interruttore acceso la prima email e'
il benvenuto coi link verificanti; spento resta l'email di conferma."""
from pathlib import Path

SRC = (Path(__file__).resolve().parents[1] / "routers" / "subscribers.py").read_text(encoding="utf-8")


def test_subscribe_usa_il_benvenuto_solo_con_interruttore():
    i = SRC.index("inviato = await invia_subito_se_singolo(email) if singolo_optin() else None")
    blocco = SRC[i:i + 400]
    assert "if not inviato:" in blocco and "_send_confirm_email" in blocco
    # 24/9 sera: l'email parte in un task (create_task) e il send gira in
    # un thread (to_thread): la richiesta non aspetta Brevo
    assert "asyncio.create_task(_dopo_iscrizione(" in SRC
    assert "await asyncio.to_thread(_send_confirm_email" in SRC
    seq = (Path(__file__).resolve().parents[1] / "services" / "sequenze.py").read_text(encoding="utf-8")
    assert "await asyncio.to_thread(lambda: _manda(passo, ctx))" in seq
    # spento: singolo_optin() e' falso e la conferma parte come sempre
    from services.sequenze import singolo_optin
    import os
    os.environ.pop("CERCHIO_SINGOLO_OPTIN", None)
    assert singolo_optin() is False


def test_il_grazie_dice_la_verita_senza_oracolo():
    """`modalita` nella risposta viene SOLO dall'interruttore: identica per
    nuovo, pending e gia' confermato (niente enumerazione)."""
    assert SRC.count('return {"ok": True, "modalita": _modalita_risposta()}') == 2
    assert "dallo\n    stato dell'iscritto" in SRC or "mai dallo" in SRC
    from routers.subscribers import _modalita_risposta
    import os
    os.environ.pop("CERCHIO_SINGOLO_OPTIN", None)
    assert _modalita_risposta() == "conferma"
    os.environ["CERCHIO_SINGOLO_OPTIN"] = "1"
    try:
        assert _modalita_risposta() == "benvenuto"
    finally:
        os.environ.pop("CERCHIO_SINGOLO_OPTIN", None)
    lead = (Path(__file__).resolve().parents[2] / "frontend" / "src" / "features" / "prelaunch" / "LeadForm.jsx").read_text(encoding="utf-8")
    assert "risposta?.data?.modalita === 'benvenuto'" in lead and "form.thanksBenvenuto" in lead
