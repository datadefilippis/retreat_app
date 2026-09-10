"""
LE EMAIL DELLE SEQUENZE (FV, 10/9/2026) — un posto solo, scritte bene.

Regola di casa: ogni email fa UNA cosa, si puo' rispondere (legge
Valentina), niente urgenza finta, niente «cordiali saluti». I testi
vivono qui e non nei dizionari generici di email_service, cosi' si
leggono per intero e si cambiano insieme.

Qui: il giorno zero dell'operatore. I passi successivi (profilo online,
5/10/15 senza profilo, 14 senza ritiro, 30 «come va») stanno in
services/sequenze.py, che usa gli stessi mattoni.
"""
import logging
import os

logger = logging.getLogger(__name__)

APP_URL = (os.environ.get("FRONTEND_URL") or os.environ.get("PUBLIC_BASE_URL") or "https://aurya.life").rstrip("/")


def _saluto(nome: str) -> str:
    nome = (nome or "").strip().split(" ")[0]
    return f"Ciao {nome}," if nome else "Ciao,"


def benvenuto_operatore(email: str, nome: str, verification_token: str, locale: str = "it") -> bool:
    """Giorno zero: un saluto, UN bottone che verifica ed entra, i tre passi,
    cosa succede dopo. Sostituisce «Benvenuto su Aurya — Verifica la tua email»."""
    try:
        from services.email_service import _link_block, _wrap_template, send_email, ADMIN_EMAIL
        url = f"{APP_URL}/verify-email?token={verification_token}&lang={locale or 'it'}"
        html = _wrap_template(f"""
            <p>{_saluto(nome)}</p>
            <p>il tuo spazio su Aurya è aperto. Un clic qui sotto conferma la tua email
            e ti porta dentro: non serve rifare il login.</p>
            <p style="text-align: center;">
                <a href="{url}" class="btn">Entra nel tuo spazio</a>
            </p>
            {_link_block(url)}
            <p><strong>Cosa trovi dentro, in tre passi.</strong></p>
            <ol>
                <li><strong>La tua pagina.</strong> Una foto, due righe su di te, il primo
                servizio con il prezzo. Dieci minuti, e sei online con un link da mettere
                nella bio.</li>
                <li><strong>I tuoi ritiri ed eventi.</strong> Data, luogo, posti e prezzo:
                le persone chiedono un posto dalla tua pagina e tu confermi. Senza
                commissioni, mai.</li>
                <li><strong>La rete.</strong> Quando il profilo è online entri nel gruppo
                Telegram degli operatori Aurya: le novità, le richieste che arrivano, noi a
                un messaggio di distanza.</li>
            </ol>
            <p>Se qualcosa non torna, rispondi a questa email: la legge Valentina.</p>
            <p>A presto,<br>Valentina e Davide</p>
        """, locale or "it")
        send_email(email, "Il tuo spazio su Aurya è aperto: un clic e sei dentro",
                   html, reply_to=ADMIN_EMAIL)
        return True
    except Exception as exc:  # noqa: BLE001 — la registrazione non si blocca mai per un'email
        logger.warning("benvenuto_operatore: email non inviata a %s: %s", email[:2] + "***", exc)
        return False
