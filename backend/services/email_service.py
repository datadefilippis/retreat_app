"""
Transactional email service via Brevo HTTP API.

Usage:
    from services.email_service import send_email, send_password_reset

If BREVO_API_KEY is not set, emails are logged but not sent.
This ensures the app never crashes due to missing email config.
"""

import os
import json
import logging
import urllib.request  # legacy import — solo per backward-compat type hints
import urllib.error
from typing import Optional

# Track O Step 1.3 — sostituiamo urllib (sync, no retry, no pool) con
# requests.Session + HTTPAdapter retry. Battle-tested production-grade,
# zero new dependency (requests gia' in requirements.txt).
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

# ── Config from env ───────────────────────────────────────────────────────────

BREVO_API_KEY = os.environ.get("BREVO_API_KEY", "")
# R1 — mittenti dal brand config (core/brand.py = fonte unica)
from core.brand import BRAND_FROM_EMAIL, BRAND_FROM_NAME, BRAND_TAGLINE  # noqa: E402
SMTP_FROM_EMAIL = os.environ.get("SMTP_FROM_EMAIL", BRAND_FROM_EMAIL)
SMTP_FROM_NAME = os.environ.get("SMTP_FROM_NAME", BRAND_FROM_NAME)
# FV6 (10/9/2026 sera, founder) — LA CASELLA DI AURYA: aurya.life@gmail.com.
# Il mittente resta noreply@aurya.life, ma OGNI email della piattaforma
# porta il Reply-To sulla casella (chi risponde al «noreply» arriva qui),
# e il piede lo dice invece di «non rispondere». I moduli verso di noi
# (regia, aziende, strutture, promemoria) scrivono qui.
CASELLA_AURYA = (os.environ.get("AURYA_INBOX_EMAIL") or "aurya.life@gmail.com").strip()
REPLY_TO_DEFAULT = (os.environ.get("REPLY_TO_EMAIL") or CASELLA_AURYA).strip()

# APP_URL is the canonical admin/auth host. We re-export from url_builder
# so legacy callers (`from services.email_service import APP_URL`) keep
# working while the actual env-reading + validation lives in one place.
# Adding a new email helper that needs the URL: prefer
# `from services.url_builder import build_app_url` (or build_public_url
# for /t/, /b/, /rsv/, /d/ post-purchase landings).
from services.url_builder import APP_URL  # noqa: E402  re-export

_configured = bool(BREVO_API_KEY)

# Brevo SMTP HTTP API endpoint
BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"

if _configured:
    logger.info("email_service: Brevo API configured (from=%s)", SMTP_FROM_EMAIL)
else:
    logger.warning("email_service: BREVO_API_KEY not set — emails will be logged only")


# ── HTTP session singleton con retry (Track O Step 1.3) ──────────────────
#
# Pre-O1.3: urllib.request.urlopen sync + zero retry + nessuna connection
# pool. Brevo timeout (~7/h SLA 99.5%) bloccava thread pool + nessun
# fallback su transient failure.
#
# Post-O1.3: requests.Session() con HTTPAdapter retry:
#   - max_retries=3 con exponential backoff (1s, 2s, 4s)
#   - retry su 429 (rate limit) + 5xx (server error)
#   - connection pooling (riutilizza HTTPS connection vs handshake ogni call)
#   - graceful close su shutdown (sessione module-scope)
#
# Sync interface preserved → no breaking change ai call site (send_email
# resta sync; chi vuole async usa asyncio.to_thread come prima).

def _build_brevo_session() -> requests.Session:
    """Build singleton requests.Session con retry adapter per Brevo API.

    Pure function (no side effects, no env read) → testabile in isolation
    + ricostruibile in test con mock adapter.
    """
    retry_strategy = Retry(
        total=3,                       # max 3 retry su transient failure
        backoff_factor=1.0,            # 1s × 2^n: 1s → 2s → 4s
        status_forcelist=[429, 500, 502, 503, 504],  # retry on these
        allowed_methods=["POST"],      # POST e' idempotent dato Idempotency-Key Brevo
        raise_on_status=False,         # gestisco status code manualmente
    )
    adapter = HTTPAdapter(
        max_retries=retry_strategy,
        pool_connections=10,           # conn pool size per host
        pool_maxsize=20,               # max concurrent connections
    )
    session = requests.Session()
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


# Module-scope singleton — initialized lazy on first import.
_brevo_session: Optional[requests.Session] = None


def _get_brevo_session() -> requests.Session:
    """Get-or-create session singleton (lazy init, thread-safe)."""
    global _brevo_session
    if _brevo_session is None:
        _brevo_session = _build_brevo_session()
    return _brevo_session


def _post_brevo(payload_bytes: bytes, timeout: float = 10.0) -> tuple[bool, int, str]:
    """POST to Brevo API with retry + connection pool.

    Args:
        payload_bytes: JSON-encoded request body
        timeout: per-request timeout in seconds (default 10s send)

    Returns:
        (success, status_code, body_or_error)
        - success: True if 2xx, False otherwise
        - status_code: HTTP status (0 if connection error)
        - body_or_error: response body or exception string
    """
    session = _get_brevo_session()
    try:
        resp = session.post(
            BREVO_API_URL,
            data=payload_bytes,
            headers={
                "api-key": BREVO_API_KEY,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            timeout=timeout,
        )
        success = 200 <= resp.status_code < 300
        body = resp.text[:500] if not success else ""
        return success, resp.status_code, body
    except requests.exceptions.RequestException as e:
        # Network error / timeout dopo tutti i retry.
        # Track O Step 3.2 — capture to Sentry per alert rule [P1] 500 error
        # spike. Brevo final failure post-retry e' indicatore di Brevo down
        # OR API key invalid OR DNS issue → operatore deve sapere subito.
        try:
            from core.observability.sentry import capture_with_tags
            capture_with_tags(
                e,
                action="email_send",
                surface="api",
                extra={"brevo_endpoint": BREVO_API_URL, "stage": "network_post_retry"},
            )
        except Exception:
            # Capture deve mai bloccare il flow caller (return below).
            pass
        return False, 0, f"network_error: {type(e).__name__}: {str(e)[:200]}"


# ── i18n translations for email templates ────────────────────────────────────

SUPPORTED_LOCALES = {"it", "en", "de", "fr"}

EMAIL_TRANSLATIONS = {
    "it": {
        "greeting": "Ciao",
        "greeting_name": "Ciao <strong>{name}</strong>,",
        "or_copy_link": "Oppure copia e incolla questo link nel browser:",
        "ignore": "Se non l'hai chiesto tu, ignora questa email.",
        "footer_brand": "Aurya &middot; Ritiri ed esperienze olistiche, in un posto solo",
        "footer_auto": "Questa email è stata inviata automaticamente, non rispondere.",
        "footer_reply_to": "Per rispondere, scrivi a {email}.",
        # Invite request confirmation
        "invite_request_confirm_subject": "La tua richiesta è arrivata",
        "invite_request_confirm_body": "abbiamo ricevuto la tua richiesta di entrare su Aurya.",
        "invite_request_confirm_next": "La leggiamo noi, Valentina e Davide, e ti scriviamo entro due giorni lavorativi.",
        # Welcome / verify
        "welcome_subject": "Il tuo spazio su Aurya è aperto",
        "welcome_subject_no_token": "Il tuo spazio su Aurya è aperto",
        "welcome_body": "il tuo spazio su Aurya è aperto.",
        "welcome_verify": "Un clic conferma la tua email e ti porta dentro:",
        "welcome_cta": "Apro il mio spazio",
        "welcome_no_token_body": "Entri con la tua email e la password che hai scelto:",
        "welcome_no_token_cta": "Entro in Aurya",
        "welcome_expiry": "Il link vale 24 ore.",
        # Verification (resend)
        "verify_subject": "Conferma la tua email su Aurya",
        "verify_body": "con un clic puoi confermare la tua email e continuare ad accedere al tuo spazio su Aurya.",
        "verify_cta": "Confermo la mia email",
        "verify_expiry": "Il link vale 24 ore.",
        # Password reset
        "reset_subject": "Scegli la tua nuova password",
        "reset_body": "dal pulsante qui sotto puoi scegliere una nuova password per il tuo spazio su Aurya.",
        "reset_cta": "Scelgo la password",
        "reset_expiry": "Il link vale un'ora.",
        # Password changed
        "changed_subject": "Password cambiata",
        "changed_body": "la password del tuo spazio su Aurya è stata cambiata.",
        "changed_warning": "Se non eri tu, scegli subito una nuova password da «Password dimenticata» e rispondi a questa email: ti aiutiamo a controllare l'accesso.",
        "lockout_alert_subject": "Accesso fermato per sicurezza",
        "lockout_alert_body": "ci sono stati cinque tentativi di accesso sbagliati di fila. Per sicurezza, l'accesso resta fermo fino alle {unlock_at}.",
        "lockout_alert_warning": "Se eri tu, puoi riprovare dopo quell'ora oppure scegliere una nuova password. Se non eri tu, ti consigliamo di scegliere subito una nuova password.",
        "lockout_alert_cta": "Scelgo una nuova password",
        "lockout_alert_safety_note": "",
        # Team invite
        "team_subject": "{inviter} ti ha aggiunto a {org_name} su Aurya",
        "team_body": "<strong>{inviter}</strong> ti ha aggiunto allo spazio di <strong>{org_name}</strong> su Aurya.",
        "team_credentials": "Dal pulsante puoi scegliere la tua password ed entrare.",
        "team_cta": "Scelgo la password ed entro",
        "team_change_password": "Il link vale 7 giorni.",
        # Deactivation
        "deactivation_subject": "Il tuo spazio su Aurya è stato disattivato",
        "deactivation_body": "lo spazio di <strong>{org_name}</strong> su Aurya è stato disattivato.",
        "deactivation_deletion": "Conserviamo i dati per 30 giorni, fino al <strong>{date}</strong>. Entro quella data puoi chiedere di riattivarlo rispondendo a questa email.",
        "deactivation_reactivate": "Dopo quella data, i dati vengono eliminati.",
        "deactivation_no_action": "Se vuoi riattivare lo spazio, rispondi a questa email.",
        # GDPR-Admin Phase A — Final warning before hard delete (7 days before)
        "final_delete_warning_subject": "Tra 7 giorni eliminiamo i dati di {org_name}",
        "final_delete_warning_intro": "lo spazio di <strong>{org_name}</strong> su Aurya è stato disattivato {days_ago} giorni fa.",
        "final_delete_warning_body": "Il <strong>{delete_date}</strong> elimineremo i suoi dati.",
        "final_delete_warning_reactivate": "Se vuoi conservarli, rispondi a questa email entro quella data e possiamo riattivare lo spazio.",
        "final_delete_warning_export": "Se vuoi invece una copia dei dati, chiedila nella stessa risposta.",
        "final_delete_warning_no_action": "Se va bene così, non devi fare nulla.",
        # Platform invite
        "platform_invite_subject": "Hai un invito per Aurya",
        "platform_invite_body": "hai un invito per aprire il tuo spazio su <strong>Aurya</strong>, la rete dei professionisti del benessere.",
        "platform_invite_cta_label": "Dal pulsante puoi aprirlo in circa un minuto.",
        "platform_invite_cta": "Apro il mio spazio",
        "platform_invite_expiry": "Il link vale 7 giorni.",
        # Customer account (v9.0)
        "customer_welcome_subject": "Il tuo account è pronto: conferma l'email",
        "customer_welcome_body": "il tuo account è pronto. Un clic conferma la tua email e puoi iniziare.",
        "customer_welcome_cta": "Confermo la mia email",
        "customer_verify_subject": "Conferma la tua email",
        "customer_verify_body": "un clic e la tua email è confermata.",
        "customer_verify_cta": "Confermo la mia email",
        "customer_reset_subject": "Scegli la tua nuova password",
        "customer_reset_body": "dal pulsante qui sotto puoi scegliere una nuova password.",
        "customer_reset_cta": "Scelgo la password",
        "customer_changed_subject": "Password cambiata",
        "customer_changed_body": "la password del tuo account è stata cambiata.",
        # Order transactional emails (v10.1)
        "order_received_subject": "La tua richiesta è arrivata a {store_name}",
        "order_received_body": "{store_name} ha ricevuto la tua richiesta:",
        "order_received_ref": "Riferimento: <strong>{order_ref}</strong>",
        "order_received_items": "Articoli: {count}",
        "order_received_total": "Totale: {total}",
        "order_received_cta": "Vedo la mia richiesta",
        # P2 (10/9/2026) — caparra con bonifico: le istruzioni partono da sole
        "order_bank_title": "Per tenere il posto",
        "order_bank_body": "Per tenere il posto, devi versare la caparra di <strong>{amount}</strong> con un bonifico entro il <strong>{deadline}</strong>.",
        "order_bank_iban": "IBAN: <strong>{iban}</strong>",
        "order_bank_holder": "Intestato a: {holder}",
        "order_bank_reason": "Causale: <strong>{reason}</strong>",
        "order_bank_note": "Appena il pagamento arriva, ti confermiamo il posto. Se cambi idea prima, scrivici e basta.",
        "order_saldo_title": "Caparra ricevuta, grazie",
        "order_saldo_body": "Abbiamo ricevuto la caparra di <strong>{deposit}</strong>. Il saldo di <strong>{balance}</strong> si versa con un bonifico entro il <strong>{deadline}</strong>, sullo stesso IBAN.",
        "order_saldo_prima": "l’inizio del ritiro",
        "order_bank_body_full": "Per tenere il posto, devi versare il totale di <strong>{amount}</strong> con un bonifico entro il <strong>{deadline}</strong>.",
        "order_agree_body": "{store_name} ti scriverà a breve per confermare il posto e concordare il pagamento.",
        "order_agree_deposit": "È prevista una caparra di <strong>{deposit}</strong>.",
        # Consolidamento prodotti (6/10/2026): l'ordine PAGATO non e' una richiesta
        "order_merchant_paid_subject": "Nuovo ordine pagato — {customer_name}",
        "order_merchant_paid_body": "{customer_name} ha comprato e pagato dal tuo profilo. L'incasso è già sul tuo conto Stripe.",
        "order_merchant_paid_total": "Totale pagato: {total}",
        "order_merchant_phone": "Telefono: {phone}",
        "order_merchant_ship_to": "Da spedire a: <strong>{address}</strong>",
        "order_merchant_pickup": "Ritiro di persona: il cliente passa da te. Accordatevi per email o telefono.",
        "order_merchant_digital": "File consegnato in automatico: il cliente lo scarica dal suo account Aurya. Non devi fare nulla.",
        "order_merchant_paid_cta": "Vai all'ordine",
        "order_confirmed_body_digital": "Il pagamento è andato a buon fine e il tuo file è pronto. Lo scarichi dal pulsante qui sotto e lo ritrovi sempre in «I miei file», nel tuo account Aurya, da qualunque telefono.",
        "order_confirmed_body_shipping": "Il pagamento è andato a buon fine. {store_name} prepara la spedizione e ti scrive quando parte.",
        "order_confirmed_body_pickup": "Il pagamento è andato a buon fine. {store_name} ti aspetta per il ritiro: vi accordate per email o telefono.",
        "order_confirmed_cta_files": "Vai ai miei file",
        # AC2 (7/10/2026) — il corso online comprato con l'account Aurya
        "order_confirmed_body_corso": "Il pagamento è andato a buon fine e il tuo corso è pronto. Lo trovi in «I miei corsi», nel tuo account Aurya: riprendi da dove eri, da qualunque telefono, lezione dopo lezione.",
        "order_confirmed_cta_corsi": "Vai ai miei corsi",
        "order_merchant_subject": "Nuova richiesta — {customer_name}",
        "order_merchant_body": "Una nuova richiesta è arrivata dal catalogo pubblico.",
        "order_merchant_customer": "Cliente: <strong>{customer_name}</strong> ({customer_email})",
        "order_merchant_items": "Articoli: {count}",
        "order_merchant_total": "Totale stimato: {total}",
        "order_merchant_fulfillment": "Consegna: {mode}",
        "order_merchant_cta": "Vai agli ordini",
        "order_merchant_notes": "<strong>Note:</strong> {notes}",
        "order_merchant_draft_hint": "Questo ordine è in stato bozza. Confermalo dalla pagina Ordini.",
        "order_confirmed_subject": "{store_name} ha confermato il tuo ordine",
        "order_confirmed_body": "{store_name} ha confermato il tuo ordine.",
        "order_confirmed_ref": "Ordine: <strong>{order_ref}</strong>",
        "order_confirmed_cta": "Apri il mio ordine",
        # Fase 2 S2 (retreat) — riepilogo piano pagamenti in email conferma
        "payment_plan_heading": "Il tuo piano di pagamenti",
        "payment_plan_paid_row": "{label}: <strong>{amount}</strong> — pagata &#10003;",
        "payment_plan_pending_row": "{label}: <strong>{amount}</strong> — entro il {due_date}",
        "payment_plan_reminder_note": "Prima di ogni scadenza ti mandiamo un promemoria con il link per pagare: non devi fare nulla ora.",
        # Fase 2 S3 — promemoria/solleciti saldo e notifica at-risk operatore
        "pay_reminder_subject_t7": "{amount} per {store_name} entro il {due_date}",
        "pay_reminder_subject_t0": "Scade oggi: {amount} per {store_name}",
        "pay_sollecito_subject": "{amount} per {store_name}: la data è passata",
        "pay_reminder_body": "ti ricordiamo il {label} di <strong>{amount}</strong> per l'ordine <strong>{order_ref}</strong>, da pagare entro il <strong>{due_date}</strong>. Puoi pagarlo qui:",
        "pay_sollecito_body": "il {label} di <strong>{amount}</strong> per l'ordine <strong>{order_ref}</strong> era previsto entro il <strong>{due_date}</strong>. Puoi pagarlo adesso:",
        "pay_now_cta": "Pago ora",
        "pay_reminder_footer": "Se hai già pagato con bonifico, ignora pure questa email: chi organizza lo segnerà appena vedrà il pagamento.",
        "pay_atrisk_merchant_subject": "{customer}: il {label} di {amount} non è arrivato",
        "pay_atrisk_merchant_body": "il {label} di <strong>{amount}</strong> per l'ordine <strong>{order_ref}</strong> ({customer}) era previsto entro il {due_date}. Dopo tre promemoria, non risulta ancora pagato.",
        "pay_atrisk_merchant_actions": "Dalla sezione Incassi puoi: segnarlo come pagato, se hai ricevuto un bonifico; cancellarlo; dare più tempo; liberare il posto. Non facciamo nulla senza di te.",
        # R2a — conferma prenotazione (Onda 16), prima hardcoded it
        "reservation_confirm_subject": "La tua prenotazione è confermata",
        "reservation_confirm_body": "la tua prenotazione è confermata:",
        "reservation_keep_note": "Questo link è tuo: non condividerlo.",
        "reservation_code_label": "Codice",
        "reservation_view_cta": "Apri la prenotazione",
        # R2a — Passaporto: login OTP/magic link + claim post-acquisto
        # (l'email più vista dai viaggiatori — prima hardcoded it)
        "passport_login_subject": "Il tuo accesso ad Aurya",
        "passport_code_intro": "ecco il tuo codice di accesso, vale {minutes} minuti:",
        "passport_code_hint": "Puoi scriverlo nella pagina da cui hai richiesto l'accesso oppure entrare direttamente dal pulsante.",
        "passport_link_intro": "Il link funziona una volta sola e vale {minutes} minuti.",
        "passport_login_cta": "Entro in Aurya",
        "passport_login_ignore": "Se non hai chiesto tu questo accesso, ignora questa email.",
        "passport_claim_subject": "Le tue prenotazioni, in un posto solo",
        "passport_claim_body": "grazie per la prenotazione. Nel tuo account Aurya ritrovi prenotazioni, pagamenti e biglietti, anche se hai prenotato con professionisti diversi.",
        "passport_claim_cta": "Entro nel mio account",
        "passport_claim_footer": "Il link vale {minutes} minuti. Se è scaduto, da aurya.life/accedi puoi chiedere un nuovo accesso in un attimo. Una volta dentro puoi anche scegliere una password.",
        # AP1b — verifica email signup + reset password (account Aurya)
        "aurya_verify_subject": "Un clic e il tuo account Aurya è attivo",
        "aurya_verify_body": "il tuo account Aurya è quasi pronto. Un clic sul pulsante conferma la tua email e ti fa entrare.",
        "aurya_verify_cta": "Confermo e entro",
        "aurya_verify_footer": "Il link vale {hours} ore. Se non eri tu, ignora questa email: l'account non viene attivato.",
        "aurya_reset_subject": "Scegli la tua nuova password",
        "aurya_reset_body": "dal pulsante qui sotto puoi scegliere una nuova password per il tuo account Aurya. Il link vale un'ora.",
        "aurya_reset_cta": "Scelgo la password",
        "aurya_reset_footer": "Se non hai chiesto tu di cambiare la password, ignora questa email: la password attuale resta quella di prima.",
        # PR2 — OTP recensione operatore
        "review_otp_subject": "Il codice per la tua recensione a {operator}",
        "review_otp_body": "ecco il codice per lasciare la tua recensione a <strong>{operator}</strong>:",
        "review_otp_hint": "Il codice vale {minutes} minuti. Se non hai chiesto tu questo codice, ignora questa email.",

        # Fase 4 — follow-up post ritiro
        "event_email_broadcast_followup_subject": "Grazie per aver partecipato a {event}",
        "event_email_broadcast_followup_body": "grazie di cuore per aver fatto parte di <strong>{event}</strong>. Speriamo che l'esperienza ti abbia lasciato qualcosa di buono.",
        "event_email_broadcast_followup_outro": "Se ti va di restare in contatto e sapere dei prossimi appuntamenti, rispondi pure a questa email: ci fa sempre piacere.",        "order_cancelled_subject": "Ordine {order_ref} annullato — {store_name}",
        "order_cancelled_body": "l'ordine <strong>{order_ref}</strong> è stato annullato.",
        "order_cancelled_ref": "",
        "order_cancelled_refund_paid": "Se hai già pagato, il rimborso parte da {store_name}: in genere arriva entro 5-10 giorni lavorativi sullo stesso metodo di pagamento.",
        "order_cancelled_refund_none": "Non c'era nessun pagamento da restituire.",
        "pay_atrisk_merchant_cta": "Apro gli incassi",
        "order_cancelled_contact": "Per qualunque cosa, rispondi a questa email: arriva a {store_name}.",
        "fulfillment_shipped_subject": "Il tuo ordine è partito — {store_name}",
        "fulfillment_shipped_body": "è partito. Puoi seguirlo dal link qui sotto.",
        "fulfillment_ready_subject": "Il tuo ordine è pronto per il ritiro — {store_name}",
        "fulfillment_ready_body": "il tuo ordine è pronto. Lo trovi negli orari di apertura: porta con te questa email.",
        "fulfillment_delivered_subject": "Il tuo ordine è arrivato — {store_name}",
        "fulfillment_delivered_body": "è arrivato. Se qualcosa non va, rispondi a questa email e ti aiutiamo.",
        "fulfillment_picked_up_subject": "Il tuo ordine è completato — {store_name}",
        "fulfillment_picked_up_body": "tutto fatto. Grazie e a presto.",
        "fulfillment_fulfilled_subject": "Il tuo ordine è completato — {store_name}",
        "fulfillment_fulfilled_body": "tutto fatto. Grazie e a presto.",
        "fulfillment_ref": "Riferimento: <strong>{order_ref}</strong>",
        "fulfillment_mode_shipping": "Spedizione",
        "fulfillment_mode_local_pickup": "Ritiro in sede",
        "fulfillment_mode_manual_arrangement": "Accordo manuale",
        "fulfillment_tracking_label": "Codice",
        "fulfillment_tracking_cta": "Dov'è il pacco",
        "fulfillment_destination_label": "Destinazione",
        "fulfillment_pickup_label": "Ritiro presso",
        "fulfillment_shipping_free": "GRATIS",
        # Order summary table (rendered in the customer confirmation email)
        "order_summary_heading": "Riepilogo ordine",
        "order_summary_col_item": "Articolo",
        "order_summary_col_qty": "Qta",
        "order_summary_col_price": "Prezzo",
        "order_summary_subtotal": "Subtotale: {total}",
        "order_summary_shipping": "Spedizione: {cost}",
        "order_summary_total": "Totale: {total}",
        # Item type breakdown (receipt + admin lines)
        "order_typecount_event_one": "{count} evento",
        "order_typecount_event_other": "{count} eventi",
        "order_typecount_service_one": "{count} servizio",
        "order_typecount_service_other": "{count} servizi",
        "order_typecount_rental_one": "{count} prenotazione",
        "order_typecount_rental_other": "{count} prenotazioni",
        "order_typecount_physical_one": "{count} prodotto",
        "order_typecount_physical_other": "{count} prodotti",
        "order_typecount_digital_one": "{count} download",
        "order_typecount_digital_other": "{count} download",
        "order_typecount_course_one": "{count} corso",
        "order_typecount_course_other": "{count} corsi",
        "order_typecount_fallback": "Articoli: {count}",
        # Release 4 (Courses) Step 8 — enrollment section in the confirmation email
        "order_courses_heading": "I tuoi corsi",
        "order_courses_cta": "Vai al corso",
        "order_courses_access_lifetime": "Accesso a vita",
        "order_courses_access_expiry": "Accesso valido fino al {date}",
        # Event email service (Onda 2) — single-ticket resend, per-holder
        # ticket delivery, broadcast templates. Same shape across all 4
        # locales — keep the keys aligned when editing.
        "event_email_greeting": "Ciao {name},",
        "event_email_greeting_attendee_fallback": "",
        "event_email_ticket_resend_intro": "ecco di nuovo il tuo biglietto per <strong>{event}</strong>.",
        "event_email_ticket_personal_intro": "ecco il tuo biglietto per <strong>{event}</strong>.",
        "event_email_ticket_label": "Il tuo biglietto",
        "event_email_ticket_seat_hint": "Biglietto {seat_index} di {seat_count}",
        "event_email_ticket_open_cta": "Apro il mio biglietto",
        "event_email_ticket_qr_hint": "Puoi mostrarlo all'ingresso oppure leggerne il codice direttamente. Conserva questa email.",
        "event_email_ticket_link_privacy_hint": "Questo link è tuo: non condividerlo.",
        "event_email_subject_ticket": "Il tuo biglietto per {event}",
        "event_email_fallback_event_name": "Evento",
        "event_email_broadcast_reminder_subject": "Ci vediamo presto a {event}",
        "event_email_broadcast_reminder_body": "ti aspettiamo a <strong>{event}</strong>.",
        "event_email_broadcast_reminder_outro": "Ricordati di portare il biglietto (email o QR). A presto.",
        "event_email_broadcast_logistics_subject": "Qualche informazione pratica su {event}",
        "event_email_broadcast_logistics_body": "ti aspettiamo a <strong>{event}</strong>. Ecco qualche informazione pratica:",
        "event_email_broadcast_logistics_outro": "A presto.",
        "event_email_broadcast_cancellation_subject": "{event} è stato annullato",
        "event_email_broadcast_cancellation_body": "<strong>{event}</strong> è stato annullato. Ci dispiace.",
        "event_email_broadcast_cancellation_outro": "Per il rimborso ti scrive chi organizza entro pochi giorni. Se hai domande, rispondi a questa email.",
        "event_email_broadcast_custom_subject_fallback": "Un aggiornamento su {event}",
        "event_email_broadcast_code_label": "Codice",
        # Order email — 4 embedded sections inside the confirmation email
        # (Onda 5). One renderer per item-type (tickets / bookings /
        # reservations / downloads). Same shape across all 4 locales.
        # The 12 month-short keys feed the locale-aware date helper
        # `_fmt_short_date_localized` used by booking + reservation rows.
        "order_section_tickets_heading": "I tuoi biglietti",
        "order_section_tickets_open_cta": "Apri biglietto \u2192",
        "order_section_tickets_seat_hint": "Biglietto {seat_index} di {seat_count}",
        "order_section_tickets_event_fallback": "Evento",
        "order_section_tickets_privacy_hint": "Questo link è tuo: non condividerlo.",
        "order_section_bookings_heading": "Le tue prenotazioni",
        "order_section_bookings_open_cta": "Apri prenotazione \u2192",
        "order_section_bookings_product_fallback": "Consulenza",
        "order_section_bookings_help_hint": "Apri la prenotazione per vedere i dettagli o aggiungerla al tuo calendario.",
        "order_section_reservations_heading": "La tua prenotazione",
        "order_section_reservations_open_cta": "Vedi prenotazione \u2192",
        "order_section_reservations_product_fallback": "Prenotazione",
        "order_section_reservations_help_hint": "Apri la prenotazione per i dettagli completi o per aggiungerla al calendario.",
        "order_section_downloads_heading": "Il tuo download",
        "order_section_downloads_open_cta": "Vai al download \u2192",
        "order_section_downloads_product_fallback": "Download",
        "order_section_downloads_file_fallback": "File",
        "order_section_downloads_max_hint": "fino a {max} download",
        "order_section_downloads_expiry_hint": "valido fino al {date}",
        "order_section_downloads_privacy_hint": "Questo link è tuo: non condividerlo. Se lo perdi, lo ritrovi nel tuo account.",
        "month_short_1": "gen",
        "month_short_2": "feb",
        "month_short_3": "mar",
        "month_short_4": "apr",
        "month_short_5": "mag",
        "month_short_6": "giu",
        "month_short_7": "lug",
        "month_short_8": "ago",
        "month_short_9": "set",
        "month_short_10": "ott",
        "month_short_11": "nov",
        "month_short_12": "dic",
        # Store-status transition alerts (Onda 7) — operational email
        # to the merchant when their storefront drops to "degraded" or
        # recovers to "live". Recipient is `notification_email` or the
        # first admin of the org. Locale comes from the recipient's
        # User.locale > store.storefront_languages[0] > "it".
        "store_alert_degraded_subject": "Alla tua pagina mancano alcune cose",
        "store_alert_degraded_intro": "la tua pagina <strong>{store_name}</strong> è visibile, ma al momento le mancano alcune informazioni importanti:",
        "store_alert_degraded_outro": "Puoi sistemarle direttamente dalla pagina.",
        "store_alert_recovery_subject": "La tua pagina è a posto",
        "store_alert_recovery_intro": "tutto quello che serviva alla tua pagina <strong>{store_name}</strong> c'è.",
        "store_alert_recovery_outro": "Buon lavoro.",
        "store_alert_settings_cta": "Sistemo la pagina",
        "store_alert_configure_link": "Sistema",
        "store_alert_check_public_slug": "L'indirizzo pubblico della pagina",
        "store_alert_check_display_name": "Il nome",
        "store_alert_check_contact_email": "L'email di contatto",
        "store_alert_check_payment_provider": "Un modo per incassare",
        "store_alert_check_publishable_offer": "Un servizio pubblicato",
        # Cashflow alerts (Onda 7) — high-severity batch + weekly digest.
        # Same locale resolution chain as the store-status alerts.
        "cashflow_alert_high_heading_one": "{count} alert critico",
        "cashflow_alert_high_heading_other": "{count} alert critici",
        "cashflow_alert_high_remaining_one": "...e altro {count} alert critico",
        "cashflow_alert_high_remaining_other": "...e altri {count} alert critici",
        "cashflow_alert_category_label": "Cat. {category}",
        "cashflow_alert_view_all_cta": "Visualizza tutti gli alert",
        "cashflow_digest_heading": "Riepilogo settimanale alert",
        "cashflow_digest_view_cta": "Vai agli alert",
        "cashflow_severity_high_one": "{count} critico",
        "cashflow_severity_high_other": "{count} critici",
        "cashflow_severity_medium_one": "{count} moderato",
        "cashflow_severity_medium_other": "{count} moderati",
        "cashflow_severity_low_one": "{count} lieve",
        "cashflow_severity_low_other": "{count} lievi",
        "cashflow_alert_footer_view": "Visualizza alert",
        "cashflow_alert_footer_settings": "Gestisci notifiche",
        "cashflow_alert_footer_disable": "Puoi disattivare queste email nelle <a href=\"{settings_url}\" style=\"color:#2563EB;\">Impostazioni</a> &gt; Preferenze Alert.",
        # ── Quota warning emails (Onda 6) ────────────────────────────────────
        # Sent by quota_warning_sweep when an org reaches 80% / 100% of a
        # quota. `metric_label_*` are inlined into the subject + body so the
        # admin sees "AI chat" / "ordini" / "righe import" naturally.
        "quota_warning_subject": "Hai usato {used} su {limit} {metric} questo mese",
        "quota_warning_intro": "questo mese hai usato {used} su {limit} {metric}.",
        "quota_warning_outro": "Se te ne servono altri, da qui puoi vedere le possibilità disponibili.",
        "quota_warning_cta_addon": "Vedo le opzioni",
        "quota_warning_cta_upgrade": "Vedo le opzioni",
        "quota_exceeded_subject": "Hai usato tutti i {metric} di questo mese",
        "quota_exceeded_intro": "hai usato tutti i {metric} di questo mese ({used} su {limit}).",
        "quota_exceeded_outro_blocking": "Per continuare, da qui puoi vedere le possibilità disponibili.",
        "quota_exceeded_outro_soft": "Il servizio continua (le email importanti partono sempre). Se te ne servono altri, da qui vedi le possibilità disponibili.",
        "quota_metric_chat": "messaggi con l'assistente",
        "quota_metric_orders_monthly": "ordini",
        "quota_metric_data_rows": "righe di dati",
        "quota_metric_products": "prodotti",
        "quota_metric_stores_max": "pagine",
        "quota_metric_digest": "riepiloghi",
        "quota_metric_email_alerts": "avvisi email",
        "quota_metric_fallback": "utilizzo",
        "quota_addon_offer_chat": "",
        "quota_addon_offer_orders_monthly": "",
        "quota_addon_offer_stores_max": "",
        "quota_addon_offer_fallback": "",
        "quota_period_label": "periodo: {period}",
    },
    "en": {
        "greeting": "Hello",
        "greeting_name": "Hello <strong>{name}</strong>,",
        "or_copy_link": "Or copy and paste this link in your browser:",
        "ignore": "If you didn't request this action, please ignore this email.",
        "footer_brand": "Aurya — Holistic retreats and experiences, all in one place.",
        "footer_auto": "This email was sent automatically, please do not reply.",
        "footer_reply_to": "To reply, write to {email}.",
        "invite_request_confirm_subject": "Application received — Aurya",
        "invite_request_confirm_body": "We have received your request to access Aurya.",
        "invite_request_confirm_next": "We will contact you as soon as possible to provide you with access.",
        "welcome_subject": "Welcome to Aurya — Verify your email",
        "welcome_subject_no_token": "Welcome to Aurya!",
        "welcome_body": "Welcome to Aurya! Your account has been created successfully.",
        "welcome_verify": "To complete your registration, please verify your email address:",
        "welcome_cta": "Verify Email",
        "welcome_no_token_body": "You can access the platform using your email and password:",
        "welcome_no_token_cta": "Sign in to Aurya",
        "welcome_expiry": "The link expires in <strong>24 hours</strong>.",
        "verify_subject": "Verify your email address — Aurya",
        "verify_body": "Click the button below to verify your email address:",
        "verify_cta": "Verify Email",
        "verify_expiry": "The link expires in <strong>24 hours</strong>.",
        "reset_subject": "Reset your password — Aurya",
        "reset_body": "You requested a password reset. Click the button below to set a new password:",
        "reset_cta": "Reset Password",
        "reset_expiry": "The link expires in <strong>1 hour</strong>.",
        "changed_subject": "Password changed — Aurya",
        "changed_body": "Your password has been changed successfully.",
        "changed_warning": "If you didn't make this change, contact us immediately or use the \"Forgot password\" link to reset it.",
        "lockout_alert_subject": "Suspicious activity on your Aurya account",
        "lockout_alert_body": "We detected 5 failed login attempts on your account. For your security, we've temporarily locked access until {unlock_at}.",
        "lockout_alert_warning": "If this wasn't you, we recommend resetting your password immediately.",
        "lockout_alert_cta": "Reset password",
        "lockout_alert_safety_note": "If you were the one mistyping, please try again after the lock expires, or reset your password if you forgot it.",
        "team_subject": "You've been invited to Aurya — {org_name}",
        "team_body": "<strong>{inviter}</strong> has invited you to join <strong>{org_name}</strong> on Aurya.",
        "team_credentials": "Your temporary credentials:",
        "team_cta": "Sign in to Aurya",
        "team_change_password": "<strong>We recommend changing your password on first login.</strong>",
        "deactivation_subject": "Aurya account deactivated — {org_name}",
        "deactivation_body": "The organization account <strong>{org_name}</strong> on Aurya has been deactivated.",
        "deactivation_deletion": "All data will be <strong>permanently deleted on {date}</strong> (30 days after deactivation).",
        "deactivation_reactivate": "To reactivate the account, contact your organization's administrator before that date.",
        "deactivation_no_action": "If you no longer wish to use the service, no action is required.",
        # GDPR-Admin Phase A — Final warning before hard delete (7 days before)
        "final_delete_warning_subject": "FINAL WARNING — Permanent deletion in 7 days — {org_name}",
        "final_delete_warning_intro": "We are writing to remind you that the account <strong>{org_name}</strong> was deactivated {days_ago} days ago.",
        "final_delete_warning_body": "Pursuant to our Privacy Policy (GDPR Art. 17), all data associated with this organization will be <strong>permanently deleted on {delete_date}</strong> (in 7 days). This action is irreversible.",
        "final_delete_warning_reactivate": "If you want to recover the account, you must <strong>reactivate it by that date</strong>. After deletion, the data cannot be recovered.",
        "final_delete_warning_export": "If you wish to download a copy of your data before deletion, you can do so from the 'Settings > Personal data' section of your account (if still active) or by contacting support.",
        "final_delete_warning_no_action": "If you wish to proceed with deletion, no action is required: the deletion will happen automatically at the deadline.",
        "platform_invite_subject": "You've been invited to Aurya",
        "platform_invite_body": "You've been invited to sign up on <strong>Aurya</strong>, the financial management platform for SMEs.",
        "platform_invite_cta_label": "Click the button below to create your account:",
        "platform_invite_cta": "Sign up for Aurya",
        "platform_invite_expiry": "The link expires in <strong>7 days</strong>.",
        "customer_welcome_subject": "Welcome — Your account has been created",
        "customer_welcome_body": "Your account has been created successfully. Verify your email address to get started:",
        "customer_welcome_cta": "Verify Email",
        "customer_verify_subject": "Verify your email address",
        "customer_verify_body": "Click the button below to verify your email address:",
        "customer_verify_cta": "Verify Email",
        "customer_reset_subject": "Reset your password",
        "customer_reset_body": "You requested a password reset. Click the button below:",
        "customer_reset_cta": "Reset Password",
        "customer_changed_subject": "Password changed",
        "customer_changed_body": "Your password has been changed successfully.",
        "order_received_subject": "Request received — {store_name}",
        "order_received_body": "Your request has been registered. We will contact you shortly.",
        "order_received_ref": "Order reference: <strong>{order_ref}</strong>",
        "order_received_items": "Items: {count}",
        "order_received_total": "Total: {total}",
        "order_received_cta": "My orders",
        "order_bank_title": "To confirm your place",
        "order_bank_body": "Your place is confirmed with a deposit of <strong>{amount}</strong>, by bank transfer within <strong>{deadline}</strong>.",
        "order_bank_iban": "IBAN: <strong>{iban}</strong>",
        "order_bank_holder": "Account holder: {holder}",
        "order_bank_reason": "Reference: <strong>{reason}</strong>",
        "order_bank_note": "As soon as the transfer arrives we confirm your place. If you change your mind before, just write to us.",
        "order_saldo_title": "Deposit received, thank you",
        "order_saldo_body": "We received your deposit of <strong>{deposit}</strong>. The balance of <strong>{balance}</strong> is due by bank transfer by <strong>{deadline}</strong>, to the same IBAN.",
        "order_saldo_prima": "the start of the retreat",
        "order_bank_body_full": "Your place is confirmed with a payment of <strong>{amount}</strong>, by bank transfer within <strong>{deadline}</strong>.",
        "order_agree_body": "{store_name} received your request and will write to confirm your place and agree on the payment.",
        "order_agree_deposit": "A deposit of <strong>{deposit}</strong> applies to this retreat.",
        "order_merchant_subject": "New request — {customer_name}",
        "order_merchant_body": "A new request has arrived from your public catalog.",
        "order_merchant_customer": "Customer: <strong>{customer_name}</strong> ({customer_email})",
        "order_merchant_items": "Items: {count}",
        "order_merchant_total": "Estimated total: {total}",
        "order_merchant_fulfillment": "Fulfillment: {mode}",
        "order_merchant_cta": "Go to orders",
        "order_merchant_notes": "<strong>Notes:</strong> {notes}",
        "order_merchant_draft_hint": "This order is in draft state. Confirm it from the Orders page.",
        "order_confirmed_subject": "Order confirmed — {store_name}",
        "order_confirmed_body": "Your order has been confirmed and is being processed.",
        "order_confirmed_ref": "Order: <strong>{order_ref}</strong>",
        "order_confirmed_cta": "View order details",
        "payment_plan_heading": "Your payment plan",
        "payment_plan_paid_row": "{label}: <strong>{amount}</strong> — paid &#10003;",
        "payment_plan_pending_row": "{label}: <strong>{amount}</strong> — due by {due_date}",
        "payment_plan_reminder_note": "We will send you a reminder with a payment link before each due date — nothing to do now.",
        "pay_reminder_subject_t7": "Reminder: {amount} due soon — {store_name}",
        "pay_reminder_subject_t0": "Due today: {amount} — {store_name}",
        "pay_sollecito_subject": "Overdue payment: {amount} — {store_name}",
        "pay_reminder_body": "A payment for order <strong>{order_ref}</strong> is coming up: {label} of <strong>{amount}</strong> due by <strong>{due_date}</strong>. Pay in one click below.",
        "pay_sollecito_body": "The due date for order <strong>{order_ref}</strong> has passed: {label} of <strong>{amount}</strong> was due by <strong>{due_date}</strong>. Please settle the payment using the button below.",
        "pay_now_cta": "Pay now",
        "pay_reminder_footer": "The link opens a secure Stripe payment. If you already paid by bank transfer, ignore this email: the organizer will update your record.",
        "pay_atrisk_merchant_subject": "Payment at risk: {customer} — {amount}",
        "pay_atrisk_merchant_body": "The payment <strong>{label}</strong> of <strong>{amount}</strong> for order <strong>{order_ref}</strong> ({customer}) was due by {due_date}. After 3 automatic reminders it is still unpaid.",
        "pay_atrisk_merchant_actions": "From the retreat payments dashboard you can: mark it paid (bank transfer), waive it, postpone the due date, or free the seat. No automatic action will be taken without you.",
        # R2a — reservation confirmation (Onda 16), previously hardcoded it
        "reservation_confirm_subject": "Booking confirmed — {product}",
        "reservation_confirm_body": "Your booking is confirmed. All the details are below.",
        "reservation_keep_note": "Keep this email — the link above is private.",
        "reservation_code_label": "Code",
        "reservation_view_cta": "View booking",
        # R2a — Passport: OTP/magic-link login + post-purchase claim
        "passport_login_subject": "Your sign-in: one click and you're in",
        "passport_code_intro": "Your access code (valid for {minutes} minutes):",
        "passport_code_hint": "Type it on the page where you requested it, or use the link below.",
        "passport_link_intro": "Sign-in link: valid for {minutes} minutes, works once:",
        "passport_login_cta": "Sign in to your Aurya account",
        "passport_login_ignore": "If you didn't request this link, just ignore this email: nobody can sign in without it.",
        "passport_claim_subject": "Your bookings, in your Aurya account",
        "passport_claim_body": "Thanks for your booking! One click signs you in to your Aurya account: find your bookings, payments and tickets in one place, even across different organizers.",
        "passport_claim_cta": "Sign in to your Aurya account",
        "passport_claim_footer": "The link is valid for {minutes} minutes. Once you're in, you can set a password to sign in whenever you like.",
        # AP1b — signup email verification + password reset (Aurya account)
        "aurya_verify_subject": "Confirm your email to activate your Aurya account",
        "aurya_verify_body": "Thanks for creating your Aurya account. Confirm your email with the button below: from that moment you can sign in with your password.",
        "aurya_verify_cta": "Confirm your email",
        "aurya_verify_footer": "The link is valid for {hours} hours. If you didn't create this account, just ignore this email.",
        "aurya_reset_subject": "Set your new password",
        "aurya_reset_body": "We received a request to set or change the password of your Aurya account. Use the button below to choose your new password.",
        "aurya_reset_cta": "Choose your new password",
        "aurya_reset_footer": "The link is valid for {minutes} minutes. If you didn't make this request, ignore this email: your password stays unchanged.",
        "review_otp_subject": "Your code to leave a review",
        "review_otp_body": "You are about to leave a review. Here is your verification code:",
        "review_otp_hint": "Valid for {minutes} minutes. If you didn't request this code, just ignore this email.",

        "event_email_broadcast_followup_subject": "Thank you for joining — {event}",
        "event_email_broadcast_followup_body": "Thank you for being part of <strong>{event}</strong>. We hope the experience left you something good.",
        "event_email_broadcast_followup_outro": "If you'd like to stay in touch and hear about upcoming dates, just reply to this email — we always love that.",        "order_cancelled_subject": "Order cancelled — {store_name}",
        "order_cancelled_body": "Your order has been cancelled.",
        "order_cancelled_ref": "Reference: <strong>{order_ref}</strong>",
        "order_cancelled_contact": "For any questions, please reply to this email.",
        "fulfillment_shipped_subject": "Your order has been shipped — {store_name}",
        "fulfillment_shipped_body": "Your order has been shipped.",
        "fulfillment_ready_subject": "Your order is ready for pickup — {store_name}",
        "fulfillment_ready_body": "Your order is ready for pickup.",
        "fulfillment_delivered_subject": "Order delivered — {store_name}",
        "fulfillment_delivered_body": "Your order has been delivered.",
        "fulfillment_picked_up_subject": "Order picked up — {store_name}",
        "fulfillment_picked_up_body": "Your order has been picked up successfully.",
        "fulfillment_fulfilled_subject": "Order completed — {store_name}",
        "fulfillment_fulfilled_body": "Your order has been completed.",
        "fulfillment_ref": "Reference: <strong>{order_ref}</strong>",
        "fulfillment_mode_shipping": "Shipping",
        "fulfillment_mode_local_pickup": "Local pickup",
        "fulfillment_mode_manual_arrangement": "Manual arrangement",
        "fulfillment_tracking_label": "Tracking number",
        "fulfillment_tracking_cta": "Track your parcel",
        "fulfillment_destination_label": "Destination",
        "fulfillment_pickup_label": "Pickup at",
        "fulfillment_shipping_free": "FREE",
        # Order summary table (rendered in the customer confirmation email)
        "order_summary_heading": "Order summary",
        "order_summary_col_item": "Item",
        "order_summary_col_qty": "Qty",
        "order_summary_col_price": "Price",
        "order_summary_subtotal": "Subtotal: {total}",
        "order_summary_shipping": "Shipping: {cost}",
        "order_summary_total": "Total: {total}",
        # Item type breakdown (receipt + admin lines)
        "order_typecount_event_one": "{count} event",
        "order_typecount_event_other": "{count} events",
        "order_typecount_service_one": "{count} service",
        "order_typecount_service_other": "{count} services",
        "order_typecount_rental_one": "{count} booking",
        "order_typecount_rental_other": "{count} bookings",
        "order_typecount_physical_one": "{count} product",
        "order_typecount_physical_other": "{count} products",
        "order_typecount_digital_one": "{count} download",
        "order_typecount_digital_other": "{count} downloads",
        "order_typecount_course_one": "{count} course",
        "order_typecount_course_other": "{count} courses",
        "order_typecount_fallback": "Items: {count}",
        # Release 4 (Courses) Step 8
        "order_courses_heading": "Your courses",
        "order_courses_cta": "Go to course",
        "order_courses_access_lifetime": "Lifetime access",
        "order_courses_access_expiry": "Access valid until {date}",
        # Event email service (Onda 2)
        "event_email_greeting": "Hi {name},",
        "event_email_greeting_attendee_fallback": "guest",
        "event_email_ticket_resend_intro": "as requested, here is your ticket again for <strong>{event}</strong>.",
        "event_email_ticket_personal_intro": "Here is your personal ticket for <strong>{event}</strong>.",
        "event_email_ticket_label": "Your ticket",
        "event_email_ticket_seat_hint": "Ticket {seat_index} of {seat_count}",
        "event_email_ticket_open_cta": "Open ticket and QR \u2192",
        "event_email_ticket_qr_hint": "Show the QR code or read it out at the entrance for check-in. Please keep this email.",
        "event_email_ticket_link_privacy_hint": "Open the link from your phone at the entrance. The link is private \u2014 do not share it.",
        "event_email_subject_ticket": "Your ticket \u2014 {event}",
        "event_email_fallback_event_name": "Event",
        "event_email_broadcast_reminder_subject": "See you soon \u2014 {event}",
        "event_email_broadcast_reminder_body": "We are looking forward to seeing you at your event!",
        "event_email_broadcast_reminder_outro": "Remember to bring your ticket (email or QR code). See you soon.",
        "event_email_broadcast_logistics_subject": "Practical information \u2014 {event}",
        "event_email_broadcast_logistics_body": "Some practical information for your event:",
        "event_email_broadcast_logistics_outro": "For any questions, reply to this email.",
        "event_email_broadcast_cancellation_subject": "Event cancelled \u2014 {event}",
        "event_email_broadcast_cancellation_body": "<strong>We are sorry to inform you that the event has been cancelled.</strong>",
        "event_email_broadcast_cancellation_outro": "You will receive refund instructions shortly. We apologise for the inconvenience.",
        "event_email_broadcast_custom_subject_fallback": "Update \u2014 {event}",
        "event_email_broadcast_code_label": "Code",
        # Order email — 4 embedded sections (Onda 5)
        "order_section_tickets_heading": "Your tickets",
        "order_section_tickets_open_cta": "Open ticket \u2192",
        "order_section_tickets_seat_hint": "Ticket {seat_index} of {seat_count}",
        "order_section_tickets_event_fallback": "Event",
        "order_section_tickets_privacy_hint": "Click \"Open ticket\" to view the QR at the entrance. Each link is private \u2014 keep it safe.",
        "order_section_bookings_heading": "Your bookings",
        "order_section_bookings_open_cta": "Open booking \u2192",
        "order_section_bookings_product_fallback": "Consultation",
        "order_section_bookings_help_hint": "Open the booking to view details or add it to your calendar.",
        "order_section_reservations_heading": "Your reservation",
        "order_section_reservations_open_cta": "View reservation \u2192",
        "order_section_reservations_product_fallback": "Reservation",
        "order_section_reservations_help_hint": "Open the reservation for full details or to add it to your calendar.",
        "order_section_downloads_heading": "Your download",
        "order_section_downloads_open_cta": "Go to download \u2192",
        "order_section_downloads_product_fallback": "Download",
        "order_section_downloads_file_fallback": "File",
        "order_section_downloads_max_hint": "up to {max} downloads",
        "order_section_downloads_expiry_hint": "valid until {date}",
        "order_section_downloads_privacy_hint": "\U0001F512 The link is personal. Keep it safe \u2014 if you lose it you can retrieve it from your account.",
        "month_short_1": "Jan",
        "month_short_2": "Feb",
        "month_short_3": "Mar",
        "month_short_4": "Apr",
        "month_short_5": "May",
        "month_short_6": "Jun",
        "month_short_7": "Jul",
        "month_short_8": "Aug",
        "month_short_9": "Sep",
        "month_short_10": "Oct",
        "month_short_11": "Nov",
        "month_short_12": "Dec",
        # Store-status transition alerts (Onda 7)
        "store_alert_degraded_subject": "Attention: {store_name} has configuration issues",
        "store_alert_degraded_intro": "Your store <strong>{store_name}</strong> has critical configuration issues that need attention.",
        "store_alert_degraded_outro": "Your storefront is still accessible, but some features may not work correctly.",
        "store_alert_recovery_subject": "{store_name} is back online",
        "store_alert_recovery_intro": "Great news! Your store <strong>{store_name}</strong> is fully operational again.",
        "store_alert_recovery_outro": "All required configurations are in place. Your storefront is working correctly.",
        "store_alert_settings_cta": "Go to settings",
        "store_alert_configure_link": "Configure",
        "store_alert_check_public_slug": "Public storefront address",
        "store_alert_check_display_name": "Public business name",
        "store_alert_check_contact_email": "Public contact email",
        "store_alert_check_payment_provider": "Payment provider",
        "store_alert_check_publishable_offer": "Published product",
        # Cashflow alerts (Onda 7)
        "cashflow_alert_high_heading_one": "{count} critical alert",
        "cashflow_alert_high_heading_other": "{count} critical alerts",
        "cashflow_alert_high_remaining_one": "...and {count} more critical alert",
        "cashflow_alert_high_remaining_other": "...and {count} more critical alerts",
        "cashflow_alert_category_label": "Cat. {category}",
        "cashflow_alert_view_all_cta": "View all alerts",
        "cashflow_digest_heading": "Weekly alert digest",
        "cashflow_digest_view_cta": "Go to alerts",
        "cashflow_severity_high_one": "{count} critical",
        "cashflow_severity_high_other": "{count} critical",
        "cashflow_severity_medium_one": "{count} moderate",
        "cashflow_severity_medium_other": "{count} moderate",
        "cashflow_severity_low_one": "{count} low",
        "cashflow_severity_low_other": "{count} low",
        "cashflow_alert_footer_view": "View alerts",
        "cashflow_alert_footer_settings": "Manage notifications",
        "cashflow_alert_footer_disable": "You can disable these emails in <a href=\"{settings_url}\" style=\"color:#2563EB;\">Settings</a> &gt; Alert preferences.",
        # ── Quota warning emails (Onda 6) ────────────────────────────────────
        "quota_warning_subject": "Approaching your {metric} limit",
        "quota_warning_intro": "Your store has used {used} of {limit} {metric} this month — that's 80%.",
        "quota_warning_outro": "To avoid service interruption, consider an add-on pack or upgrading to the next plan.",
        "quota_warning_cta_addon": "Buy pack",
        "quota_warning_cta_upgrade": "Upgrade plan",
        "quota_exceeded_subject": "{metric} limit reached",
        "quota_exceeded_intro": "You've hit your {metric} limit for this month ({used}/{limit}).",
        "quota_exceeded_outro_blocking": "Further requests will be blocked until the period renews or you activate a pack / higher plan.",
        "quota_exceeded_outro_soft": "Service keeps running (transactional emails are never blocked). To stay aligned with your plan, consider a pack or upgrade.",
        "quota_metric_chat": "AI chats",
        "quota_metric_orders_monthly": "ecommerce orders",
        "quota_metric_data_rows": "dataset rows",
        "quota_metric_products": "products",
        "quota_metric_stores_max": "stores",
        "quota_metric_digest": "AI digests",
        "quota_metric_email_alerts": "email alerts",
        "quota_metric_fallback": "usage",
        "quota_addon_offer_chat": "Pack +50 AI chats for just €9/month",
        "quota_addon_offer_orders_monthly": "Pack +200 orders for just €15/month",
        "quota_addon_offer_stores_max": "Pack +1 store for just €19/month",
        "quota_addon_offer_fallback": "Upgrade your plan to extend the limit",
        "quota_period_label": "period: {period}",
    },
    "de": {
        "greeting": "Hallo",
        "greeting_name": "Hallo <strong>{name}</strong>,",
        "or_copy_link": "Oder kopieren Sie diesen Link in Ihren Browser:",
        "ignore": "Wenn Sie diese Aktion nicht angefordert haben, ignorieren Sie diese E-Mail.",
        "footer_brand": "Aurya — Holistische Retreats und Erlebnisse, an einem Ort.",
        "footer_auto": "Diese E-Mail wurde automatisch versendet, bitte nicht antworten.",
        "footer_reply_to": "Zum Antworten schreiben Sie an {email}.",
        "invite_request_confirm_subject": "Bewerbung eingegangen — Aurya",
        "invite_request_confirm_body": "Wir haben Ihre Zugriffsanfrage fuer Aurya erhalten.",
        "invite_request_confirm_next": "Wir werden Sie so schnell wie moeglich kontaktieren, um Ihnen den Zugang zu ermoeglichen.",
        "welcome_subject": "Willkommen bei Aurya — Bestaetigen Sie Ihre E-Mail",
        "welcome_subject_no_token": "Willkommen bei Aurya!",
        "welcome_body": "Willkommen bei Aurya! Ihr Konto wurde erfolgreich erstellt.",
        "welcome_verify": "Um die Registrierung abzuschliessen, bestaetigen Sie Ihre E-Mail-Adresse:",
        "welcome_cta": "E-Mail bestaetigen",
        "welcome_no_token_body": "Sie koennen sich mit Ihrer E-Mail und Ihrem Passwort anmelden:",
        "welcome_no_token_cta": "Bei Aurya anmelden",
        "welcome_expiry": "Der Link laeuft in <strong>24 Stunden</strong> ab.",
        "verify_subject": "Bestaetigen Sie Ihre E-Mail-Adresse — Aurya",
        "verify_body": "Klicken Sie auf die Schaltflaeche unten, um Ihre E-Mail-Adresse zu bestaetigen:",
        "verify_cta": "E-Mail bestaetigen",
        "verify_expiry": "Der Link laeuft in <strong>24 Stunden</strong> ab.",
        "reset_subject": "Passwort zuruecksetzen — Aurya",
        "reset_body": "Sie haben eine Passwortzuruecksetzung angefordert. Klicken Sie auf die Schaltflaeche unten:",
        "reset_cta": "Passwort zuruecksetzen",
        "reset_expiry": "Der Link laeuft in <strong>1 Stunde</strong> ab.",
        "changed_subject": "Passwort geaendert — Aurya",
        "changed_body": "Ihr Passwort wurde erfolgreich geaendert.",
        "changed_warning": "Wenn Sie diese Aenderung nicht vorgenommen haben, kontaktieren Sie uns sofort oder verwenden Sie \"Passwort vergessen\".",
        "lockout_alert_subject": "Verdaechtige Aktivitaet auf Ihrem Aurya-Konto",
        "lockout_alert_body": "Wir haben 5 fehlgeschlagene Anmeldeversuche auf Ihrem Konto festgestellt. Aus Sicherheitsgruenden haben wir den Zugriff voruebergehend bis {unlock_at} gesperrt.",
        "lockout_alert_warning": "Wenn Sie das nicht waren, empfehlen wir Ihnen, sofort Ihr Passwort zuruckzusetzen.",
        "lockout_alert_cta": "Passwort zuruecksetzen",
        "lockout_alert_safety_note": "Falls Sie sich nur vertippt haben, versuchen Sie es nach Ablauf der Sperre erneut oder setzen Sie Ihr Passwort zurueck, wenn Sie es vergessen haben.",
        "team_subject": "Sie wurden zu Aurya eingeladen — {org_name}",
        "team_body": "<strong>{inviter}</strong> hat Sie eingeladen, <strong>{org_name}</strong> auf Aurya beizutreten.",
        "team_credentials": "Ihre temporaeren Zugangsdaten:",
        "team_cta": "Bei Aurya anmelden",
        "team_change_password": "<strong>Wir empfehlen, Ihr Passwort beim ersten Login zu aendern.</strong>",
        "deactivation_subject": "Aurya-Konto deaktiviert — {org_name}",
        "deactivation_body": "Das Organisationskonto <strong>{org_name}</strong> auf Aurya wurde deaktiviert.",
        "deactivation_deletion": "Alle Daten werden <strong>am {date} endgueltig geloescht</strong> (30 Tage nach Deaktivierung).",
        "deactivation_reactivate": "Um das Konto zu reaktivieren, kontaktieren Sie den Administrator Ihrer Organisation vor diesem Datum.",
        "deactivation_no_action": "Wenn Sie den Dienst nicht mehr nutzen moechten, ist keine Aktion erforderlich.",
        # GDPR-Admin Phase A — Final warning before hard delete (7 days before)
        "final_delete_warning_subject": "LETZTE WARNUNG — Endgueltige Loeschung in 7 Tagen — {org_name}",
        "final_delete_warning_intro": "Wir moechten Sie daran erinnern, dass das Konto <strong>{org_name}</strong> vor {days_ago} Tagen deaktiviert wurde.",
        "final_delete_warning_body": "Gemaess unserer Datenschutzerklaerung (DSGVO Art. 17) werden alle Daten, die mit dieser Organisation verknuepft sind, <strong>am {delete_date} endgueltig geloescht</strong> (in 7 Tagen). Diese Aktion ist unwiderruflich.",
        "final_delete_warning_reactivate": "Wenn Sie das Konto wiederherstellen moechten, muessen Sie es <strong>vor diesem Datum reaktivieren</strong>. Nach der Loeschung koennen die Daten nicht mehr wiederhergestellt werden.",
        "final_delete_warning_export": "Wenn Sie eine Kopie Ihrer Daten vor der Loeschung herunterladen moechten, koennen Sie dies im Bereich 'Einstellungen > Persoenliche Daten' Ihres Kontos tun (sofern noch aktiv) oder den Support kontaktieren.",
        "final_delete_warning_no_action": "Wenn Sie mit der Loeschung fortfahren moechten, ist keine Aktion erforderlich: Die Loeschung erfolgt automatisch zum Stichtag.",
        "platform_invite_subject": "Sie wurden zu Aurya eingeladen",
        "platform_invite_body": "Sie wurden eingeladen, sich bei <strong>Aurya</strong> zu registrieren, der Finanzmanagement-Plattform fuer KMU.",
        "platform_invite_cta_label": "Klicken Sie auf die Schaltflaeche unten, um Ihr Konto zu erstellen:",
        "platform_invite_cta": "Bei Aurya registrieren",
        "platform_invite_expiry": "Der Link laeuft in <strong>7 Tagen</strong> ab.",
        "customer_welcome_subject": "Willkommen — Ihr Konto wurde erstellt",
        "customer_welcome_body": "Ihr Konto wurde erfolgreich erstellt. Bestaetigen Sie Ihre E-Mail-Adresse:",
        "customer_welcome_cta": "E-Mail bestaetigen",
        "customer_verify_subject": "Bestaetigen Sie Ihre E-Mail-Adresse",
        "customer_verify_body": "Klicken Sie auf die Schaltflaeche unten, um Ihre E-Mail-Adresse zu bestaetigen:",
        "customer_verify_cta": "E-Mail bestaetigen",
        "customer_reset_subject": "Passwort zuruecksetzen",
        "customer_reset_body": "Sie haben eine Passwortzuruecksetzung angefordert:",
        "customer_reset_cta": "Passwort zuruecksetzen",
        "customer_changed_subject": "Passwort geaendert",
        "customer_changed_body": "Ihr Passwort wurde erfolgreich geaendert.",
        "order_received_subject": "Anfrage eingegangen — {store_name}",
        "order_received_body": "Ihre Anfrage wurde registriert. Wir werden Sie in Kuerze kontaktieren.",
        "order_received_ref": "Bestellreferenz: <strong>{order_ref}</strong>",
        "order_received_items": "Artikel: {count}",
        "order_received_total": "Gesamt: {total}",
        "order_received_cta": "Meine Bestellungen",
        "order_merchant_subject": "Neue Anfrage — {customer_name}",
        "order_merchant_body": "Eine neue Anfrage ist ueber Ihren oeffentlichen Katalog eingegangen.",
        "order_merchant_customer": "Kunde: <strong>{customer_name}</strong> ({customer_email})",
        "order_merchant_items": "Artikel: {count}",
        "order_merchant_total": "Geschaetzter Gesamtbetrag: {total}",
        "order_merchant_fulfillment": "Lieferung: {mode}",
        "order_merchant_cta": "Zu den Bestellungen",
        "order_merchant_notes": "<strong>Notiz:</strong> {notes}",
        "order_merchant_draft_hint": "Diese Bestellung ist im Entwurfsstatus. Bestaetigen Sie sie auf der Bestellseite.",
        "order_confirmed_subject": "Bestellung bestaetigt — {store_name}",
        "order_confirmed_body": "Ihre Bestellung wurde bestaetigt und wird bearbeitet.",
        "order_confirmed_ref": "Bestellung: <strong>{order_ref}</strong>",
        "order_confirmed_cta": "Bestelldetails ansehen",
        "order_cancelled_subject": "Bestellung storniert — {store_name}",
        "order_cancelled_body": "Ihre Bestellung wurde storniert.",
        "order_cancelled_ref": "Referenz: <strong>{order_ref}</strong>",
        "order_cancelled_contact": "Bei Fragen antworten Sie bitte auf diese E-Mail.",
        "fulfillment_shipped_subject": "Ihre Bestellung wurde versendet — {store_name}",
        "fulfillment_shipped_body": "Ihre Bestellung wurde versendet.",
        "fulfillment_ready_subject": "Ihre Bestellung ist abholbereit — {store_name}",
        "fulfillment_ready_body": "Ihre Bestellung ist abholbereit.",
        "fulfillment_delivered_subject": "Bestellung zugestellt — {store_name}",
        "fulfillment_delivered_body": "Ihre Bestellung wurde zugestellt.",
        "fulfillment_picked_up_subject": "Bestellung abgeholt — {store_name}",
        "fulfillment_picked_up_body": "Ihre Bestellung wurde erfolgreich abgeholt.",
        "fulfillment_fulfilled_subject": "Bestellung abgeschlossen — {store_name}",
        "fulfillment_fulfilled_body": "Ihre Bestellung wurde abgeschlossen.",
        "fulfillment_ref": "Referenz: <strong>{order_ref}</strong>",
        "fulfillment_mode_shipping": "Versand",
        "fulfillment_mode_local_pickup": "Abholung vor Ort",
        "fulfillment_mode_manual_arrangement": "Manuelle Vereinbarung",
        "fulfillment_tracking_label": "Sendungsnummer",
        "fulfillment_tracking_cta": "Sendung verfolgen",
        "fulfillment_destination_label": "Zieladresse",
        "fulfillment_pickup_label": "Abholung bei",
        "fulfillment_shipping_free": "KOSTENLOS",
        # Order summary table (rendered in the customer confirmation email)
        "order_summary_heading": "Bestelluebersicht",
        "order_summary_col_item": "Artikel",
        "order_summary_col_qty": "Menge",
        "order_summary_col_price": "Preis",
        "order_summary_subtotal": "Zwischensumme: {total}",
        "order_summary_shipping": "Versand: {cost}",
        "order_summary_total": "Gesamt: {total}",
        # Item type breakdown (receipt + admin lines)
        "order_typecount_event_one": "{count} Veranstaltung",
        "order_typecount_event_other": "{count} Veranstaltungen",
        "order_typecount_service_one": "{count} Dienstleistung",
        "order_typecount_service_other": "{count} Dienstleistungen",
        "order_typecount_rental_one": "{count} Buchung",
        "order_typecount_rental_other": "{count} Buchungen",
        "order_typecount_physical_one": "{count} Produkt",
        "order_typecount_physical_other": "{count} Produkte",
        "order_typecount_digital_one": "{count} Download",
        "order_typecount_digital_other": "{count} Downloads",
        "order_typecount_course_one": "{count} Kurs",
        "order_typecount_course_other": "{count} Kurse",
        "order_typecount_fallback": "Artikel: {count}",
        # Release 4 (Courses) Step 8
        "order_courses_heading": "Deine Kurse",
        "order_courses_cta": "Zum Kurs",
        "order_courses_access_lifetime": "Lebenslanger Zugriff",
        "order_courses_access_expiry": "Zugriff gueltig bis zum {date}",
        # Event email service (Onda 2)
        "event_email_greeting": "Hallo {name},",
        "event_email_greeting_attendee_fallback": "Gast",
        "event_email_ticket_resend_intro": "wie gewuenscht hier nochmals dein Ticket fuer <strong>{event}</strong>.",
        "event_email_ticket_personal_intro": "Hier ist dein persoenliches Ticket fuer <strong>{event}</strong>.",
        "event_email_ticket_label": "Dein Ticket",
        "event_email_ticket_seat_hint": "Ticket {seat_index} von {seat_count}",
        "event_email_ticket_open_cta": "Ticket und QR oeffnen \u2192",
        "event_email_ticket_qr_hint": "Zeige den QR-Code am Eingang oder nenne ihn fuer den Check-in. Bewahre diese E-Mail auf.",
        "event_email_ticket_link_privacy_hint": "Oeffne den Link am Eingang vom Handy. Der Link ist privat \u2014 teile ihn nicht.",
        "event_email_subject_ticket": "Dein Ticket \u2014 {event}",
        "event_email_fallback_event_name": "Veranstaltung",
        "event_email_broadcast_reminder_subject": "Wir sehen uns bald \u2014 {event}",
        "event_email_broadcast_reminder_body": "Wir freuen uns auf deine Veranstaltung!",
        "event_email_broadcast_reminder_outro": "Denke daran, dein Ticket mitzubringen (E-Mail oder QR-Code). Bis bald.",
        "event_email_broadcast_logistics_subject": "Praktische Informationen \u2014 {event}",
        "event_email_broadcast_logistics_body": "Einige praktische Informationen zu deiner Veranstaltung:",
        "event_email_broadcast_logistics_outro": "Bei Fragen antworte auf diese E-Mail.",
        "event_email_broadcast_cancellation_subject": "Veranstaltung abgesagt \u2014 {event}",
        "event_email_broadcast_cancellation_body": "<strong>Leider muessen wir dir mitteilen, dass die Veranstaltung abgesagt wurde.</strong>",
        "event_email_broadcast_cancellation_outro": "Du erhaeltst in Kuerze Anweisungen zur Rueckerstattung. Wir bitten um Verstaendnis fuer die Unannehmlichkeiten.",
        "event_email_broadcast_custom_subject_fallback": "Update \u2014 {event}",
        "event_email_broadcast_code_label": "Code",
        # Order email — 4 embedded sections (Onda 5)
        "order_section_tickets_heading": "Deine Tickets",
        "order_section_tickets_open_cta": "Ticket oeffnen \u2192",
        "order_section_tickets_seat_hint": "Ticket {seat_index} von {seat_count}",
        "order_section_tickets_event_fallback": "Veranstaltung",
        "order_section_tickets_privacy_hint": "Klicke auf \"Ticket oeffnen\", um den QR-Code am Eingang anzuzeigen. Jeder Link ist privat \u2014 bewahre ihn sicher auf.",
        "order_section_bookings_heading": "Deine Buchungen",
        "order_section_bookings_open_cta": "Buchung oeffnen \u2192",
        "order_section_bookings_product_fallback": "Beratung",
        "order_section_bookings_help_hint": "Oeffne die Buchung, um Details zu sehen oder sie zu deinem Kalender hinzuzufuegen.",
        "order_section_reservations_heading": "Deine Reservierung",
        "order_section_reservations_open_cta": "Reservierung ansehen \u2192",
        "order_section_reservations_product_fallback": "Reservierung",
        "order_section_reservations_help_hint": "Oeffne die Reservierung fuer alle Details oder um sie zum Kalender hinzuzufuegen.",
        "order_section_downloads_heading": "Dein Download",
        "order_section_downloads_open_cta": "Zum Download \u2192",
        "order_section_downloads_product_fallback": "Download",
        "order_section_downloads_file_fallback": "Datei",
        "order_section_downloads_max_hint": "bis zu {max} Downloads",
        "order_section_downloads_expiry_hint": "gueltig bis {date}",
        "order_section_downloads_privacy_hint": "\U0001F512 Der Link ist persoenlich. Bewahre ihn auf \u2014 wenn du ihn verlierst, kannst du ihn aus deinem Konto wiederherstellen.",
        "month_short_1": "Jan",
        "month_short_2": "Feb",
        "month_short_3": "Mae",
        "month_short_4": "Apr",
        "month_short_5": "Mai",
        "month_short_6": "Jun",
        "month_short_7": "Jul",
        "month_short_8": "Aug",
        "month_short_9": "Sep",
        "month_short_10": "Okt",
        "month_short_11": "Nov",
        "month_short_12": "Dez",
        # Store-status transition alerts (Onda 7)
        "store_alert_degraded_subject": "Achtung: {store_name} hat Konfigurationsprobleme",
        "store_alert_degraded_intro": "Dein Store <strong>{store_name}</strong> hat kritische Konfigurationsprobleme, die deine Aufmerksamkeit erfordern.",
        "store_alert_degraded_outro": "Dein Storefront ist weiterhin erreichbar, aber einige Funktionen koennten nicht korrekt funktionieren.",
        "store_alert_recovery_subject": "{store_name} ist wieder online",
        "store_alert_recovery_intro": "Grossartig! Dein Store <strong>{store_name}</strong> ist wieder voll funktionsfaehig.",
        "store_alert_recovery_outro": "Alle erforderlichen Konfigurationen sind vorhanden. Dein Storefront funktioniert ordnungsgemaess.",
        "store_alert_settings_cta": "Zu den Einstellungen",
        "store_alert_configure_link": "Konfigurieren",
        "store_alert_check_public_slug": "Oeffentliche Storefront-Adresse",
        "store_alert_check_display_name": "Oeffentlicher Firmenname",
        "store_alert_check_contact_email": "Oeffentliche Kontakt-E-Mail",
        "store_alert_check_payment_provider": "Zahlungsanbieter",
        "store_alert_check_publishable_offer": "Veroeffentlichtes Produkt",
        # Cashflow alerts (Onda 7)
        "cashflow_alert_high_heading_one": "{count} kritischer Alert",
        "cashflow_alert_high_heading_other": "{count} kritische Alerts",
        "cashflow_alert_high_remaining_one": "...und {count} weiterer kritischer Alert",
        "cashflow_alert_high_remaining_other": "...und {count} weitere kritische Alerts",
        "cashflow_alert_category_label": "Kat. {category}",
        "cashflow_alert_view_all_cta": "Alle Alerts ansehen",
        "cashflow_digest_heading": "Woechentliche Alert-Uebersicht",
        "cashflow_digest_view_cta": "Zu den Alerts",
        "cashflow_severity_high_one": "{count} kritisch",
        "cashflow_severity_high_other": "{count} kritisch",
        "cashflow_severity_medium_one": "{count} moderat",
        "cashflow_severity_medium_other": "{count} moderat",
        "cashflow_severity_low_one": "{count} niedrig",
        "cashflow_severity_low_other": "{count} niedrig",
        "cashflow_alert_footer_view": "Alerts ansehen",
        "cashflow_alert_footer_settings": "Benachrichtigungen verwalten",
        "cashflow_alert_footer_disable": "Du kannst diese E-Mails in den <a href=\"{settings_url}\" style=\"color:#2563EB;\">Einstellungen</a> &gt; Alert-Praeferenzen deaktivieren.",
        # ── Quota warning emails (Onda 6) ────────────────────────────────────
        "quota_warning_subject": "Du naeherst dich dem {metric}-Limit",
        "quota_warning_intro": "Dein Store hat diesen Monat {used} von {limit} {metric} genutzt — 80% erreicht.",
        "quota_warning_outro": "Um keine Unterbrechung zu erleben, erwaege ein Zusatzpaket oder ein Upgrade auf den naechsten Plan.",
        "quota_warning_cta_addon": "Paket kaufen",
        "quota_warning_cta_upgrade": "Plan upgraden",
        "quota_exceeded_subject": "{metric}-Limit erreicht",
        "quota_exceeded_intro": "Du hast dein {metric}-Limit fuer diesen Monat erreicht ({used}/{limit}).",
        "quota_exceeded_outro_blocking": "Weitere Anfragen werden bis zur Periodenerneuerung oder zur Aktivierung eines Pakets / hoeheren Plans blockiert.",
        "quota_exceeded_outro_soft": "Der Service laeuft weiter (transaktionale E-Mails werden nie blockiert). Um konform mit deinem Plan zu bleiben, erwaege ein Paket oder Upgrade.",
        "quota_metric_chat": "AI-Chats",
        "quota_metric_orders_monthly": "E-Commerce-Bestellungen",
        "quota_metric_data_rows": "Datensatz-Zeilen",
        "quota_metric_products": "Produkte",
        "quota_metric_stores_max": "Stores",
        "quota_metric_digest": "AI-Digests",
        "quota_metric_email_alerts": "E-Mail-Alerts",
        "quota_metric_fallback": "Nutzung",
        "quota_addon_offer_chat": "Paket +50 AI-Chats fuer nur 9 EUR/Monat",
        "quota_addon_offer_orders_monthly": "Paket +200 Bestellungen fuer nur 15 EUR/Monat",
        "quota_addon_offer_stores_max": "Paket +1 Store fuer nur 19 EUR/Monat",
        "quota_addon_offer_fallback": "Upgrade deinen Plan, um das Limit zu erweitern",
        "quota_period_label": "Zeitraum: {period}",
        # R2a — Zahlungsplan + Erinnerungen (vorher nur it/en: _t fiel auf
        # Italienisch zurueck — genau der Fall, den order.locale jetzt
        # korrekt bedienen muss)
        "payment_plan_heading": "Dein Zahlungsplan",
        "payment_plan_paid_row": "{label}: <strong>{amount}</strong> — bezahlt &#10003;",
        "payment_plan_pending_row": "{label}: <strong>{amount}</strong> — bis zum {due_date}",
        "payment_plan_reminder_note": "Wir senden dir vor jeder Faelligkeit eine Erinnerung mit dem Zahlungslink: du musst jetzt nichts tun.",
        "pay_reminder_subject_t7": "Erinnerung: {amount} wird faellig — {store_name}",
        "pay_reminder_subject_t0": "Heute faellig: {amount} — {store_name}",
        "pay_sollecito_subject": "Zahlung ueberfaellig: {amount} — {store_name}",
        "pay_reminder_body": "Erinnerung an die Faelligkeit fuer Bestellung <strong>{order_ref}</strong>: {label} ueber <strong>{amount}</strong> bis zum <strong>{due_date}</strong>. Mit dem Button unten kannst du in einem Klick bezahlen.",
        "pay_sollecito_body": "Die Faelligkeit fuer Bestellung <strong>{order_ref}</strong> ist verstrichen: {label} ueber <strong>{amount}</strong> war bis zum <strong>{due_date}</strong> faellig. Bitte begleiche die Zahlung ueber den Button unten.",
        "pay_now_cta": "Jetzt bezahlen",
        "pay_reminder_footer": "Der Link oeffnet eine sichere Stripe-Zahlung. Falls du bereits per Ueberweisung bezahlt hast, ignoriere diese E-Mail: der Veranstalter aktualisiert deinen Stand.",
        "pay_atrisk_merchant_subject": "Zahlung gefaehrdet: {customer} — {amount}",
        "pay_atrisk_merchant_body": "Die Zahlung <strong>{label}</strong> ueber <strong>{amount}</strong> fuer Bestellung <strong>{order_ref}</strong> ({customer}) war bis zum {due_date} faellig. Nach 3 automatischen Erinnerungen ist sie weiterhin offen.",
        "pay_atrisk_merchant_actions": "Was du im Zahlungs-Dashboard des Retreats tun kannst: als bezahlt markieren (bei Ueberweisung), erlassen, die Faelligkeit verschieben oder den Platz freigeben. Ohne dich passiert nichts automatisch.",
        "reservation_confirm_subject": "Buchung bestaetigt — {product}",
        "reservation_confirm_body": "Deine Buchung ist bestaetigt. Alle Details findest du unten.",
        "reservation_keep_note": "Bewahre diese E-Mail auf — der Link oben ist privat.",
        "reservation_code_label": "Code",
        "reservation_view_cta": "Buchung ansehen",
        "passport_login_subject": "Dein Zugang: ein Klick und du bist drin",
        "passport_code_intro": "Dein Zugangscode (gueltig fuer {minutes} Minuten):",
        "passport_code_hint": "Gib ihn auf der Seite ein, auf der du ihn angefordert hast, oder nutze den Link unten.",
        "passport_link_intro": "Anmeldelink: gueltig fuer {minutes} Minuten, funktioniert einmal:",
        "passport_login_cta": "In deinem Aurya Konto anmelden",
        "passport_login_ignore": "Wenn du diesen Link nicht angefordert hast, ignoriere diese E-Mail: ohne ihn kann sich niemand anmelden.",
        "passport_claim_subject": "Deine Buchungen, in deinem Aurya Konto",
        "passport_claim_body": "Danke fuer deine Buchung! Ein Klick bringt dich in dein Aurya Konto: alle Buchungen, Zahlungen und Tickets an einem Ort, auch bei verschiedenen Veranstaltern.",
        "passport_claim_cta": "In deinem Aurya Konto anmelden",
        "passport_claim_footer": "Der Link ist {minutes} Minuten gueltig. Danach kannst du ein Passwort festlegen und dich jederzeit anmelden.",
        # AP1b — E-Mail-Bestaetigung Signup + Passwort-Reset (Aurya-Konto)
        "aurya_verify_subject": "Bestaetige deine E-Mail, um dein Aurya-Konto zu aktivieren",
        "aurya_verify_body": "Danke, dass du dein Aurya-Konto erstellt hast. Bestaetige deine E-Mail mit dem Button unten: ab dann kannst du dich mit deinem Passwort anmelden.",
        "aurya_verify_cta": "E-Mail bestaetigen",
        "aurya_verify_footer": "Der Link ist {hours} Stunden gueltig. Wenn du dieses Konto nicht erstellt hast, ignoriere diese E-Mail.",
        "aurya_reset_subject": "Lege dein neues Passwort fest",
        "aurya_reset_body": "Wir haben eine Anfrage erhalten, das Passwort deines Aurya-Kontos festzulegen oder zu aendern. Mit dem Button unten waehlst du dein neues Passwort.",
        "aurya_reset_cta": "Neues Passwort waehlen",
        "aurya_reset_footer": "Der Link ist {minutes} Minuten gueltig. Wenn du das nicht angefragt hast, ignoriere diese E-Mail: dein Passwort bleibt unveraendert.",
        "review_otp_subject": "Dein Code fuer eine Bewertung",
        "review_otp_body": "Du bist dabei, eine Bewertung zu hinterlassen. Hier ist dein Bestaetigungscode:",
        "review_otp_hint": "Gueltig fuer {minutes} Minuten. Wenn du diesen Code nicht angefordert hast, ignoriere diese E-Mail.",
    },
    "fr": {
        "greeting": "Bonjour",
        "greeting_name": "Bonjour <strong>{name}</strong>,",
        "or_copy_link": "Ou copiez et collez ce lien dans votre navigateur :",
        "ignore": "Si vous n'avez pas demande cette action, veuillez ignorer cet email.",
        "footer_brand": "Aurya — Retraites et expériences holistiques, au même endroit.",
        "footer_auto": "Cet email a ete envoye automatiquement, merci de ne pas repondre.",
        "footer_reply_to": "Pour repondre, ecrivez a {email}.",
        "invite_request_confirm_subject": "Candidature recue — Aurya",
        "invite_request_confirm_body": "Nous avons recu votre demande d'acces a Aurya.",
        "invite_request_confirm_next": "Nous vous contacterons dans les plus brefs delais pour vous fournir l'acces.",
        "welcome_subject": "Bienvenue sur Aurya — Verifiez votre email",
        "welcome_subject_no_token": "Bienvenue sur Aurya !",
        "welcome_body": "Bienvenue sur Aurya ! Votre compte a ete cree avec succes.",
        "welcome_verify": "Pour finaliser votre inscription, verifiez votre adresse email :",
        "welcome_cta": "Verifier l'email",
        "welcome_no_token_body": "Vous pouvez acceder a la plateforme avec votre email et mot de passe :",
        "welcome_no_token_cta": "Se connecter a Aurya",
        "welcome_expiry": "Le lien expire dans <strong>24 heures</strong>.",
        "verify_subject": "Verifiez votre adresse email — Aurya",
        "verify_body": "Cliquez sur le bouton ci-dessous pour verifier votre adresse email :",
        "verify_cta": "Verifier l'email",
        "verify_expiry": "Le lien expire dans <strong>24 heures</strong>.",
        "reset_subject": "Reinitialiser votre mot de passe — Aurya",
        "reset_body": "Vous avez demande une reinitialisation de mot de passe. Cliquez sur le bouton ci-dessous :",
        "reset_cta": "Reinitialiser le mot de passe",
        "reset_expiry": "Le lien expire dans <strong>1 heure</strong>.",
        "changed_subject": "Mot de passe modifie — Aurya",
        "changed_body": "Votre mot de passe a ete modifie avec succes.",
        "changed_warning": "Si vous n'avez pas effectue ce changement, contactez-nous immediatement ou utilisez \"Mot de passe oublie\".",
        "lockout_alert_subject": "Activite suspecte sur votre compte Aurya",
        "lockout_alert_body": "Nous avons detecte 5 tentatives de connexion echouees sur votre compte. Pour votre securite, nous avons temporairement bloque l'acces jusqu'a {unlock_at}.",
        "lockout_alert_warning": "Si ce n'etait pas vous, nous vous recommandons de reinitialiser votre mot de passe immediatement.",
        "lockout_alert_cta": "Reinitialiser le mot de passe",
        "lockout_alert_safety_note": "Si vous vous etes simplement trompe, reessayez apres l'expiration du blocage, ou reinitialisez votre mot de passe si vous l'avez oublie.",
        "team_subject": "Vous avez ete invite sur Aurya — {org_name}",
        "team_body": "<strong>{inviter}</strong> vous a invite a rejoindre <strong>{org_name}</strong> sur Aurya.",
        "team_credentials": "Vos identifiants temporaires :",
        "team_cta": "Se connecter a Aurya",
        "team_change_password": "<strong>Nous vous recommandons de changer votre mot de passe lors de votre premiere connexion.</strong>",
        "deactivation_subject": "Compte Aurya desactive — {org_name}",
        "deactivation_body": "Le compte de l'organisation <strong>{org_name}</strong> sur Aurya a ete desactive.",
        "deactivation_deletion": "Toutes les donnees seront <strong>definitivement supprimees le {date}</strong> (30 jours apres la desactivation).",
        "deactivation_reactivate": "Pour reactiver le compte, contactez l'administrateur de votre organisation avant cette date.",
        "deactivation_no_action": "Si vous ne souhaitez plus utiliser le service, aucune action n'est requise.",
        # GDPR-Admin Phase A — Final warning before hard delete (7 days before)
        "final_delete_warning_subject": "DERNIER AVERTISSEMENT — Suppression definitive dans 7 jours — {org_name}",
        "final_delete_warning_intro": "Nous vous rappelons que le compte <strong>{org_name}</strong> a ete desactive il y a {days_ago} jours.",
        "final_delete_warning_body": "Conformement a notre Politique de confidentialite (RGPD Art. 17), toutes les donnees associees a cette organisation seront <strong>definitivement supprimees le {delete_date}</strong> (dans 7 jours). Cette action est irreversible.",
        "final_delete_warning_reactivate": "Si vous souhaitez recuperer le compte, vous devez <strong>le reactiver avant cette date</strong>. Apres la suppression, les donnees ne pourront plus etre recuperees.",
        "final_delete_warning_export": "Si vous souhaitez telecharger une copie de vos donnees avant la suppression, vous pouvez le faire depuis la section 'Parametres > Donnees personnelles' de votre compte (s'il est encore actif) ou en contactant le support.",
        "final_delete_warning_no_action": "Si vous souhaitez proceder a la suppression, aucune action n'est requise : la suppression aura lieu automatiquement a l'echeance.",
        "platform_invite_subject": "Vous avez ete invite sur Aurya",
        "platform_invite_body": "Vous avez ete invite a vous inscrire sur <strong>Aurya</strong>, la plateforme de gestion financiere pour PME.",
        "platform_invite_cta_label": "Cliquez sur le bouton ci-dessous pour creer votre compte :",
        "platform_invite_cta": "S'inscrire sur Aurya",
        "platform_invite_expiry": "Le lien expire dans <strong>7 jours</strong>.",
        "customer_welcome_subject": "Bienvenue — Votre compte a ete cree",
        "customer_welcome_body": "Votre compte a ete cree avec succes. Verifiez votre adresse email pour commencer :",
        "customer_welcome_cta": "Verifier l'email",
        "customer_verify_subject": "Verifiez votre adresse email",
        "customer_verify_body": "Cliquez sur le bouton ci-dessous pour verifier votre adresse email :",
        "customer_verify_cta": "Verifier l'email",
        "customer_reset_subject": "Reinitialiser votre mot de passe",
        "customer_reset_body": "Vous avez demande une reinitialisation de mot de passe :",
        "customer_reset_cta": "Reinitialiser le mot de passe",
        "customer_changed_subject": "Mot de passe modifie",
        "customer_changed_body": "Votre mot de passe a ete modifie avec succes.",
        "order_received_subject": "Demande recue — {store_name}",
        "order_received_body": "Votre demande a ete enregistree. Nous vous contacterons sous peu.",
        "order_received_ref": "Reference de commande : <strong>{order_ref}</strong>",
        "order_received_items": "Articles : {count}",
        "order_received_total": "Total : {total}",
        "order_received_cta": "Mes commandes",
        "order_merchant_subject": "Nouvelle demande — {customer_name}",
        "order_merchant_body": "Une nouvelle demande est arrivee depuis votre catalogue public.",
        "order_merchant_customer": "Client : <strong>{customer_name}</strong> ({customer_email})",
        "order_merchant_items": "Articles : {count}",
        "order_merchant_total": "Total estime : {total}",
        "order_merchant_fulfillment": "Livraison : {mode}",
        "order_merchant_cta": "Voir les commandes",
        "order_merchant_notes": "<strong>Notes :</strong> {notes}",
        "order_merchant_draft_hint": "Cette commande est en brouillon. Confirmez-la depuis la page Commandes.",
        "order_confirmed_subject": "Commande confirmee — {store_name}",
        "order_confirmed_body": "Votre commande a ete confirmee et est en cours de traitement.",
        "order_confirmed_ref": "Commande : <strong>{order_ref}</strong>",
        "order_confirmed_cta": "Voir les details",
        "order_cancelled_subject": "Commande annulee — {store_name}",
        "order_cancelled_body": "Votre commande a ete annulee.",
        "order_cancelled_ref": "Reference : <strong>{order_ref}</strong>",
        "order_cancelled_contact": "Pour toute question, repondez a cet email.",
        "fulfillment_shipped_subject": "Votre commande a ete expediee — {store_name}",
        "fulfillment_shipped_body": "Votre commande a ete expediee.",
        "fulfillment_ready_subject": "Votre commande est prete a retirer — {store_name}",
        "fulfillment_ready_body": "Votre commande est prete a retirer.",
        "fulfillment_delivered_subject": "Commande livree — {store_name}",
        "fulfillment_delivered_body": "Votre commande a ete livree.",
        "fulfillment_picked_up_subject": "Commande retiree — {store_name}",
        "fulfillment_picked_up_body": "Votre commande a ete retiree avec succes.",
        "fulfillment_fulfilled_subject": "Commande finalisee — {store_name}",
        "fulfillment_fulfilled_body": "Votre commande a ete finalisee.",
        "fulfillment_ref": "Reference : <strong>{order_ref}</strong>",
        "fulfillment_mode_shipping": "Expedition",
        "fulfillment_mode_local_pickup": "Retrait sur place",
        "fulfillment_mode_manual_arrangement": "Arrangement manuel",
        "fulfillment_tracking_label": "Numero de suivi",
        "fulfillment_tracking_cta": "Suivre le colis",
        "fulfillment_destination_label": "Destination",
        "fulfillment_pickup_label": "Retrait chez",
        "fulfillment_shipping_free": "GRATUIT",
        # Order summary table (rendered in the customer confirmation email)
        "order_summary_heading": "Recapitulatif de la commande",
        "order_summary_col_item": "Article",
        "order_summary_col_qty": "Qte",
        "order_summary_col_price": "Prix",
        "order_summary_subtotal": "Sous-total : {total}",
        "order_summary_shipping": "Livraison : {cost}",
        "order_summary_total": "Total : {total}",
        # Item type breakdown (receipt + admin lines)
        "order_typecount_event_one": "{count} evenement",
        "order_typecount_event_other": "{count} evenements",
        "order_typecount_service_one": "{count} service",
        "order_typecount_service_other": "{count} services",
        "order_typecount_rental_one": "{count} reservation",
        "order_typecount_rental_other": "{count} reservations",
        "order_typecount_physical_one": "{count} produit",
        "order_typecount_physical_other": "{count} produits",
        "order_typecount_digital_one": "{count} telechargement",
        "order_typecount_digital_other": "{count} telechargements",
        "order_typecount_course_one": "{count} cours",
        "order_typecount_course_other": "{count} cours",
        "order_typecount_fallback": "Articles : {count}",
        # Release 4 (Courses) Step 8
        "order_courses_heading": "Vos cours",
        "order_courses_cta": "Acceder au cours",
        "order_courses_access_lifetime": "Acces a vie",
        "order_courses_access_expiry": "Acces valable jusqu'au {date}",
        # Event email service (Onda 2)
        "event_email_greeting": "Bonjour {name},",
        "event_email_greeting_attendee_fallback": "participant",
        "event_email_ticket_resend_intro": "comme demande, voici a nouveau votre billet pour <strong>{event}</strong>.",
        "event_email_ticket_personal_intro": "Voici votre billet personnel pour <strong>{event}</strong>.",
        "event_email_ticket_label": "Votre billet",
        "event_email_ticket_seat_hint": "Billet {seat_index} sur {seat_count}",
        "event_email_ticket_open_cta": "Ouvrir le billet et le QR \u2192",
        "event_email_ticket_qr_hint": "Montrez le QR ou dictez-le a l'entree pour le check-in. Conservez cet email.",
        "event_email_ticket_link_privacy_hint": "Ouvrez le lien depuis votre telephone a l'entree. Le lien est prive \u2014 ne le partagez pas.",
        "event_email_subject_ticket": "Votre billet \u2014 {event}",
        "event_email_fallback_event_name": "Evenement",
        "event_email_broadcast_reminder_subject": "A bientot \u2014 {event}",
        "event_email_broadcast_reminder_body": "Nous vous attendons a votre evenement !",
        "event_email_broadcast_reminder_outro": "Pensez a apporter votre billet (email ou QR code). A bientot.",
        "event_email_broadcast_logistics_subject": "Informations pratiques \u2014 {event}",
        "event_email_broadcast_logistics_body": "Quelques informations pratiques pour votre evenement :",
        "event_email_broadcast_logistics_outro": "Pour toute question, repondez a cet email.",
        "event_email_broadcast_cancellation_subject": "Evenement annule \u2014 {event}",
        "event_email_broadcast_cancellation_body": "<strong>Nous sommes desoles de vous informer que l'evenement a ete annule.</strong>",
        "event_email_broadcast_cancellation_outro": "Vous recevrez prochainement les instructions pour le remboursement. Veuillez nous excuser pour la gene occasionnee.",
        "event_email_broadcast_custom_subject_fallback": "Mise a jour \u2014 {event}",
        "event_email_broadcast_code_label": "Code",
        # Order email — 4 embedded sections (Onda 5)
        "order_section_tickets_heading": "Vos billets",
        "order_section_tickets_open_cta": "Ouvrir le billet \u2192",
        "order_section_tickets_seat_hint": "Billet {seat_index} sur {seat_count}",
        "order_section_tickets_event_fallback": "Evenement",
        "order_section_tickets_privacy_hint": "Cliquez sur \"Ouvrir le billet\" pour voir le QR a l'entree. Chaque lien est prive \u2014 conservez-le.",
        "order_section_bookings_heading": "Vos reservations",
        "order_section_bookings_open_cta": "Ouvrir la reservation \u2192",
        "order_section_bookings_product_fallback": "Consultation",
        "order_section_bookings_help_hint": "Ouvrez la reservation pour voir les details ou l'ajouter a votre calendrier.",
        "order_section_reservations_heading": "Votre reservation",
        "order_section_reservations_open_cta": "Voir la reservation \u2192",
        "order_section_reservations_product_fallback": "Reservation",
        "order_section_reservations_help_hint": "Ouvrez la reservation pour les details complets ou pour l'ajouter au calendrier.",
        "order_section_downloads_heading": "Votre telechargement",
        "order_section_downloads_open_cta": "Aller au telechargement \u2192",
        "order_section_downloads_product_fallback": "Telechargement",
        "order_section_downloads_file_fallback": "Fichier",
        "order_section_downloads_max_hint": "jusqu'a {max} telechargements",
        "order_section_downloads_expiry_hint": "valable jusqu'au {date}",
        "order_section_downloads_privacy_hint": "\U0001F512 Le lien est personnel. Conservez-le \u2014 si vous le perdez, vous pourrez le recuperer depuis votre compte.",
        "month_short_1": "janv.",
        "month_short_2": "fevr.",
        "month_short_3": "mars",
        "month_short_4": "avr.",
        "month_short_5": "mai",
        "month_short_6": "juin",
        "month_short_7": "juil.",
        "month_short_8": "aout",
        "month_short_9": "sept.",
        "month_short_10": "oct.",
        "month_short_11": "nov.",
        "month_short_12": "dec.",
        # Store-status transition alerts (Onda 7)
        "store_alert_degraded_subject": "Attention : {store_name} a des problemes de configuration",
        "store_alert_degraded_intro": "Votre store <strong>{store_name}</strong> a des configurations critiques qui necessitent votre attention.",
        "store_alert_degraded_outro": "Votre vitrine est toujours accessible, mais certaines fonctionnalites peuvent ne pas fonctionner correctement.",
        "store_alert_recovery_subject": "{store_name} est de nouveau operationnel",
        "store_alert_recovery_intro": "Excellente nouvelle ! Votre store <strong>{store_name}</strong> est de nouveau pleinement operationnel.",
        "store_alert_recovery_outro": "Toutes les configurations necessaires sont en place. Votre vitrine fonctionne correctement.",
        "store_alert_settings_cta": "Aller aux parametres",
        "store_alert_configure_link": "Configurer",
        "store_alert_check_public_slug": "Adresse publique de la vitrine",
        "store_alert_check_display_name": "Nom public de l'entreprise",
        "store_alert_check_contact_email": "E-mail de contact public",
        "store_alert_check_payment_provider": "Fournisseur de paiement",
        "store_alert_check_publishable_offer": "Produit publie",
        # Cashflow alerts (Onda 7)
        "cashflow_alert_high_heading_one": "{count} alerte critique",
        "cashflow_alert_high_heading_other": "{count} alertes critiques",
        "cashflow_alert_high_remaining_one": "...et {count} autre alerte critique",
        "cashflow_alert_high_remaining_other": "...et {count} autres alertes critiques",
        "cashflow_alert_category_label": "Cat. {category}",
        "cashflow_alert_view_all_cta": "Voir toutes les alertes",
        "cashflow_digest_heading": "Resume hebdomadaire des alertes",
        "cashflow_digest_view_cta": "Aller aux alertes",
        "cashflow_severity_high_one": "{count} critique",
        "cashflow_severity_high_other": "{count} critiques",
        "cashflow_severity_medium_one": "{count} modere",
        "cashflow_severity_medium_other": "{count} moderes",
        "cashflow_severity_low_one": "{count} mineure",
        "cashflow_severity_low_other": "{count} mineures",
        "cashflow_alert_footer_view": "Voir les alertes",
        "cashflow_alert_footer_settings": "Gerer les notifications",
        "cashflow_alert_footer_disable": "Vous pouvez desactiver ces e-mails dans <a href=\"{settings_url}\" style=\"color:#2563EB;\">Parametres</a> &gt; Preferences d'alerte.",
        # ── Quota warning emails (Onda 6) ────────────────────────────────────
        "quota_warning_subject": "Vous approchez de la limite de {metric}",
        "quota_warning_intro": "Votre store a utilise {used} sur {limit} {metric} ce mois — vous etes a 80%.",
        "quota_warning_outro": "Pour eviter une interruption, envisagez un pack supplementaire ou un upgrade vers le plan superieur.",
        "quota_warning_cta_addon": "Acheter un pack",
        "quota_warning_cta_upgrade": "Mettre a niveau",
        "quota_exceeded_subject": "Limite {metric} atteinte",
        "quota_exceeded_intro": "Vous avez atteint la limite {metric} pour ce mois ({used}/{limit}).",
        "quota_exceeded_outro_blocking": "Les futures requetes seront bloquees jusqu'au renouvellement de la periode ou a l'activation d'un pack / plan superieur.",
        "quota_exceeded_outro_soft": "Le service continue (les e-mails transactionnels ne sont jamais bloques). Pour rester aligne avec votre plan, envisagez un pack ou un upgrade.",
        "quota_metric_chat": "chats AI",
        "quota_metric_orders_monthly": "commandes ecommerce",
        "quota_metric_data_rows": "lignes de dataset",
        "quota_metric_products": "produits",
        "quota_metric_stores_max": "stores",
        "quota_metric_digest": "digests AI",
        "quota_metric_email_alerts": "alertes e-mail",
        "quota_metric_fallback": "utilisation",
        "quota_addon_offer_chat": "Pack +50 chats AI pour seulement 9 EUR/mois",
        "quota_addon_offer_orders_monthly": "Pack +200 commandes pour seulement 15 EUR/mois",
        "quota_addon_offer_stores_max": "Pack +1 store pour seulement 19 EUR/mois",
        "quota_addon_offer_fallback": "Mettez a niveau votre plan pour etendre la limite",
        "quota_period_label": "periode : {period}",
        # R2a — plan de paiement + rappels (avant: seulement it/en, _t
        # retombait sur l'italien)
        "payment_plan_heading": "Votre plan de paiement",
        "payment_plan_paid_row": "{label} : <strong>{amount}</strong> — payee &#10003;",
        "payment_plan_pending_row": "{label} : <strong>{amount}</strong> — avant le {due_date}",
        "payment_plan_reminder_note": "Nous vous enverrons un rappel avec le lien de paiement avant chaque echeance : vous n'avez rien a faire pour l'instant.",
        "pay_reminder_subject_t7": "Rappel : {amount} arrive a echeance — {store_name}",
        "pay_reminder_subject_t0": "Echeance aujourd'hui : {amount} — {store_name}",
        "pay_sollecito_subject": "Paiement en retard : {amount} — {store_name}",
        "pay_reminder_body": "Rappel de l'echeance pour la commande <strong>{order_ref}</strong> : {label} de <strong>{amount}</strong> avant le <strong>{due_date}</strong>. Vous pouvez payer en un clic avec le bouton ci-dessous.",
        "pay_sollecito_body": "L'echeance de la commande <strong>{order_ref}</strong> est depassee : {label} de <strong>{amount}</strong> etait due avant le <strong>{due_date}</strong>. Merci de regulariser le paiement avec le bouton ci-dessous.",
        "pay_now_cta": "Payer maintenant",
        "pay_reminder_footer": "Le lien ouvre un paiement securise via Stripe. Si vous avez deja paye par virement, ignorez cet email : l'organisateur mettra votre dossier a jour.",
        "pay_atrisk_merchant_subject": "Paiement a risque : {customer} — {amount}",
        "pay_atrisk_merchant_body": "Le paiement <strong>{label}</strong> de <strong>{amount}</strong> pour la commande <strong>{order_ref}</strong> ({customer}) etait du avant le {due_date}. Apres 3 rappels automatiques, il reste impaye.",
        "pay_atrisk_merchant_actions": "Depuis le tableau de bord des encaissements de la retraite, vous pouvez : le marquer paye (virement), l'annuler, reporter l'echeance ou liberer la place. Aucune action automatique ne sera prise sans vous.",
        "reservation_confirm_subject": "Reservation confirmee — {product}",
        "reservation_confirm_body": "Votre reservation est confirmee. Tous les details sont ci-dessous.",
        "reservation_keep_note": "Conservez cet email — le lien ci-dessus est prive.",
        "reservation_code_label": "Code",
        "reservation_view_cta": "Voir la reservation",
        "passport_login_subject": "Votre acces : un clic et vous y etes",
        "passport_code_intro": "Votre code d'acces (valable {minutes} minutes) :",
        "passport_code_hint": "Saisissez-le sur la page ou vous l'avez demande, ou utilisez le lien ci-dessous.",
        "passport_link_intro": "Lien de connexion : valable {minutes} minutes, utilisable une seule fois :",
        "passport_login_cta": "Acceder a votre compte Aurya",
        "passport_login_ignore": "Si vous n'avez pas demande ce lien, ignorez cet email : personne ne peut se connecter sans lui.",
        "passport_claim_subject": "Vos reservations, dans votre compte Aurya",
        "passport_claim_body": "Merci pour votre reservation ! Un clic vous connecte a votre compte Aurya : retrouvez vos reservations, paiements et billets au meme endroit, meme avec des organisateurs differents.",
        "passport_claim_cta": "Acceder a votre compte Aurya",
        "passport_claim_footer": "Le lien est valable {minutes} minutes. Une fois connecte, vous pouvez definir un mot de passe pour revenir quand vous voulez.",
        # AP1b — verification email signup + reset mot de passe (compte Aurya)
        "aurya_verify_subject": "Confirmez votre email pour activer votre compte Aurya",
        "aurya_verify_body": "Merci d'avoir cree votre compte Aurya. Confirmez votre email avec le bouton ci-dessous : vous pourrez ensuite vous connecter avec votre mot de passe.",
        "aurya_verify_cta": "Confirmer mon email",
        "aurya_verify_footer": "Le lien est valable {hours} heures. Si vous n'avez pas cree ce compte, ignorez cet email.",
        "aurya_reset_subject": "Definissez votre nouveau mot de passe",
        "aurya_reset_body": "Nous avons recu une demande pour definir ou changer le mot de passe de votre compte Aurya. Avec le bouton ci-dessous, choisissez votre nouveau mot de passe.",
        "aurya_reset_cta": "Choisir le nouveau mot de passe",
        "aurya_reset_footer": "Le lien est valable {minutes} minutes. Si vous n'etes pas a l'origine de cette demande, ignorez cet email : votre mot de passe reste inchange.",
        "review_otp_subject": "Votre code pour laisser un avis",
        "review_otp_body": "Vous etes sur le point de laisser un avis. Voici votre code de verification :",
        "review_otp_hint": "Valable {minutes} minutes. Si vous n'avez pas demande ce code, ignorez cet email.",
    },
}


def _t(key: str, locale: str = "it", **kwargs) -> str:
    """Get translated string for the given locale, with optional format kwargs."""
    loc = locale if locale in SUPPORTED_LOCALES else "it"
    translations = EMAIL_TRANSLATIONS.get(loc, EMAIL_TRANSLATIONS["it"])
    text = translations.get(key, EMAIL_TRANSLATIONS["it"].get(key, key))
    return text.format(**kwargs) if kwargs else text


# ── Core send function ────────────────────────────────────────────────────────
# NB: BREVO_API_URL definita in cima (con le altre const config, Track O 1.3).


def send_email(
    to_email: str, subject: str, html_body: str,
    *, reply_to: str = None, sender_name: str = None,
    bypass_gate: bool = False,
    unsubscribe_url: Optional[str] = None,
) -> bool:
    """
    Send a single transactional email via Brevo HTTP API.
    Returns True on success, False on failure.
    Never raises — errors are logged.

    Optional keyword args (backward-compatible — existing callers unchanged):
      reply_to:    email address for Reply-To header (Brevo replyTo field)
      sender_name: override sender display name (default: SMTP_FROM_NAME)
      bypass_gate: when True, skip the pre-flight email gate (Track G G1).
                   Serve solo dove DOBBIAMO scrivere anche a un indirizzo
                   segnato (conferma del Cerchio, magic link, note a noi).
      unsubscribe_url: (C1, 24/9) solo per le email editoriali (Cerchio:
                   benvenuto, promemoria, Lettera). Se c'e', il payload
                   porta gli header List-Unsubscribe e List-Unsubscribe-Post
                   che Gmail e Yahoo chiedono ai mittenti bulk. Le
                   transazionali non lo passano e non cambiano di una virgola.
    """
    if not _configured:
        logger.info("email_service [DRY RUN] to=%s subject=%s", to_email, subject)
        # Track O Step 3.3 — record dry_run per visibility (es. CI without
        # Brevo key → metric mostra perche' no email partono).
        try:
            from core.observability.metrics import record_email_send
            record_email_send("dry_run")
        except Exception:
            pass
        return False

    # ── Fase 2 Track G — Pre-flight email gate (G1) ─────────────────────────
    # Skip outbound delivery to addresses already flagged bounced/blocked/
    # unsubscribed by Brevo's webhook (Phase 1 Step B2). Wrapped in a
    # try/except so any gate failure (DB outage, import error, malformed
    # doc) NEVER kills the email flow — the gate fails-open by design.
    if not bypass_gate:
        try:
            from services.email_gate import is_email_blocked
            blocked, reason = is_email_blocked(to_email)
            if blocked:
                logger.info(
                    "email_service: SKIPPED (gated) to=%s subject=%s reason=%s",
                    to_email, subject, reason,
                )
                # Track O Step 3.3 — record gated (suppression list hit)
                try:
                    from core.observability.metrics import record_email_send
                    record_email_send("gated")
                except Exception:
                    pass
                return False
        except Exception as e:
            # Defensive fall-through: log + proceed with delivery.
            logger.warning(
                "email_service: gate check raised err=%s — proceeding with send",
                type(e).__name__,
            )

    data = _payload_brevo(to_email, subject, html_body, reply_to=reply_to, sender_name=sender_name,
                          unsubscribe_url=unsubscribe_url)

    payload = json.dumps(data).encode("utf-8")

    # Track O Step 1.3 — usa session pool + retry vs urllib sync
    success, status, body = _post_brevo(payload, timeout=10.0)
    if success:
        logger.info(
            "email_service: sent to=%s subject=%s status=%s",
            to_email, subject, status,
        )
        # Track O Step 3.3 — record success
        try:
            from core.observability.metrics import record_email_send
            record_email_send("success")
        except Exception:
            pass
        return True
    logger.error(
        "email_service: FAILED to=%s status=%s body=%s",
        to_email, status, body,
    )
    # Track O Step 3.2 — capture non-2xx Brevo response per [P1] alert.
    # status==0 → already captured by _post_brevo (network err). Skip dup.
    if status != 0:
        try:
            from core.observability.sentry import capture_with_tags
            capture_with_tags(
                RuntimeError(f"Brevo HTTP {status}: {body[:200]}"),
                action="email_send",
                surface="api",
                extra={"http_status": status, "stage": "send_email_response"},
            )
        except Exception:
            pass
    # Track O Step 3.3 — record terminal failure status per Grafana panel
    try:
        from core.observability.metrics import record_email_send
        record_email_send("network_error" if status == 0 else "http_error")
    except Exception:
        pass
    return False


def send_email_with_attachment(
    to_email: str,
    subject: str,
    html_body: str,
    attachment_bytes: bytes,
    attachment_name: str = "report.pdf",
    attachment_type: str = "application/pdf",
    *, bypass_gate: bool = False,
) -> bool:
    """Send email with a file attachment via Brevo HTTP API.

    Same as send_email() but includes a base64-encoded attachment.

    `bypass_gate=True` skips the pre-flight email gate — see send_email().
    """
    import base64

    if not _configured:
        logger.info(
            "email_service [DRY RUN] to=%s subject=%s attachment=%s (%d bytes)",
            to_email, subject, attachment_name, len(attachment_bytes),
        )
        # Track O Step 3.3 — record dry_run (attachment path)
        try:
            from core.observability.metrics import record_email_send
            record_email_send("dry_run")
        except Exception:
            pass
        return False

    # ── Fase 2 Track G — Pre-flight email gate (G1) ─────────────────────────
    # Same fail-open contract as send_email() above. Centralised exit when
    # blocked: caller never sees the difference vs a real failure.
    if not bypass_gate:
        try:
            from services.email_gate import is_email_blocked
            blocked, reason = is_email_blocked(to_email)
            if blocked:
                logger.info(
                    "email_service: SKIPPED with-attachment (gated) to=%s subject=%s file=%s reason=%s",
                    to_email, subject, attachment_name, reason,
                )
                # Track O Step 3.3 — record gated (attachment path)
                try:
                    from core.observability.metrics import record_email_send
                    record_email_send("gated")
                except Exception:
                    pass
                return False
        except Exception as e:
            logger.warning(
                "email_service: gate check (attachment) raised err=%s — proceeding with send",
                type(e).__name__,
            )

    encoded = base64.b64encode(attachment_bytes).decode("ascii")

    payload = json.dumps({
        "sender": {"name": SMTP_FROM_NAME, "email": SMTP_FROM_EMAIL},
        "to": [{"email": to_email}],
        "subject": subject,
        "htmlContent": html_body,
        "attachment": [{
            "content": encoded,
            "name": attachment_name,
        }],
    }).encode("utf-8")

    # Track O Step 1.3 — usa session pool + retry vs urllib sync
    # Timeout piu' alto (30s) per upload attachment binary
    success, status, body = _post_brevo(payload, timeout=30.0)
    if success:
        logger.info(
            "email_service: sent with attachment to=%s subject=%s file=%s status=%s",
            to_email, subject, attachment_name, status,
        )
        # Track O Step 3.3 — record success (attachment path)
        try:
            from core.observability.metrics import record_email_send
            record_email_send("success")
        except Exception:
            pass
        return True
    logger.error(
        "email_service: FAILED (attachment) to=%s status=%s body=%s",
        to_email, status, body,
    )
    # Track O Step 3.2 — capture non-2xx attachment response per [P1] alert.
    if status != 0:
        try:
            from core.observability.sentry import capture_with_tags
            capture_with_tags(
                RuntimeError(f"Brevo HTTP {status} (attachment): {body[:200]}"),
                action="email_send",
                surface="api",
                extra={"http_status": status, "stage": "send_email_attachment_response"},
            )
        except Exception:
            pass
    # Track O Step 3.3 — record terminal failure status (attachment path)
    try:
        from core.observability.metrics import record_email_send
        record_email_send("network_error" if status == 0 else "http_error")
    except Exception:
        pass
    return False


# ── Email templates ───────────────────────────────────────────────────────────

# R2b (2026-07-06) — template Salvia & Terracotta, la stessa faccia
# della piattaforma: salvia profonda per la struttura (#376254, il
# primary dell'app), terracotta per le azioni (#CB774D, l'accent),
# crema come carta (#F6F3EC). UNA modifica qui veste tutte le email.
_BASE_STYLE = """
<style>
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 0; background: #f6f3ec; }
  .container { max-width: 560px; margin: 40px auto; background: #ffffff; border-radius: 16px; overflow: hidden; border: 1px solid #e7e1d4; }
  .header { background: #376254; background: linear-gradient(135deg, #376254, #2e564e); padding: 26px 32px; }
  .header h1 { color: #f8f5ef; font-size: 21px; margin: 0; font-weight: 700; letter-spacing: -0.01em; }
  .header .wordmark { font-family: 'Cinzel', 'Iowan Old Style', 'Palatino Linotype', Palatino, Georgia, serif; text-transform: uppercase; letter-spacing: 0.3em; font-weight: 500; font-size: 22px; color: #cbb578; vertical-align: middle; }
  .header .motto { margin: 7px 0 0; font-family: 'Cinzel', 'Palatino Linotype', Georgia, serif; letter-spacing: 0.05em; font-size: 11px; color: rgba(203,181,120,0.9); }
  .header .via { margin: 4px 0 0; font-size: 12px; color: rgba(248,245,239,0.75); }
  .body { padding: 32px; color: #37463f; font-size: 15px; line-height: 1.65; }
  .body p { margin: 0 0 16px; }
  .body strong { color: #212c28; }
  .btn { display: inline-block; background: #cb774d; color: #ffffff !important; text-decoration: none; padding: 12px 30px; border-radius: 999px; font-weight: 600; font-size: 15px; margin: 8px 0 24px; }
  .footer { padding: 22px 32px; background: #f6f3ec; border-top: 1px solid #e7e1d4; text-align: center; color: #8a9088; font-size: 12px; line-height: 1.7; }
  .footer a { color: #376254; text-decoration: none; }
  .code { background: #f1ede3; padding: 4px 10px; border-radius: 6px; font-family: monospace; font-size: 14px; color: #212c28; }
</style>
"""


def _headers_unsubscribe(unsubscribe_url: str) -> dict:
    """C1 (24/9): i due header che i grandi provider chiedono a chi manda
    email editoriali. Il mailto va alla casella che qualcuno LEGGE (la
    casella di Aurya, non il noreply del mittente); il link e' la pagina
    delle preferenze dell'iscritto, nuda: Gmail ci fa una POST diretta
    (One-Click), quindi niente redirect verificanti qui."""
    return {
        "List-Unsubscribe": f"<mailto:{CASELLA_AURYA}?subject=unsubscribe>, <{unsubscribe_url}>",
        "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
    }


def _payload_brevo(to_email: str, subject: str, html_body: str, *,
                   reply_to: str = None, sender_name: str = None,
                   unsubscribe_url: Optional[str] = None) -> dict:
    """Il corpo della chiamata a Brevo. FV6: il Reply-To c'e' SEMPRE —
    quello passato (es. l'operatore, per le email della sua vetrina) o
    la casella di Aurya. C1: la chiave `headers` compare SOLO se c'e' un
    unsubscribe_url (le transazionali restano com'erano)."""
    data = {
        "sender": {"name": sender_name or SMTP_FROM_NAME, "email": SMTP_FROM_EMAIL},
        "to": [{"email": to_email}],
        "subject": subject,
        "htmlContent": html_body,
        "replyTo": {"email": reply_to or REPLY_TO_DEFAULT},
    }
    if unsubscribe_url:
        data["headers"] = _headers_unsubscribe(unsubscribe_url)
    return data


def _wrap_template(content: str, locale: str = "it", *, reply_to: str = None, store_name: str = None) -> str:
    lang = locale if locale in SUPPORTED_LOCALES else "it"
    # FV6 — il piede dice sempre DOVE si risponde (mai «non rispondere»):
    # la casella passata, o quella di Aurya, che e' anche il Reply-To
    # FL3 (5/10/2026, founder): il piede e' uno e non dice piu' «scrivi a ...»:
    # dove si risponde lo dice il corpo (e il Reply-To resta la casella Aurya)
    _ = reply_to or REPLY_TO_DEFAULT
    # Header: store-branded when context available, platform-only otherwise.
    # Logo ufficiale (loto+sole, 13/7/2026) hostato sul dominio: risolve
    # appena il sito è deployato; il testo accanto copre il frattempo e
    # i client che bloccano le immagini.
    from core.brand import BRAND_DOMAIN, BRAND_PAYOFF
    logo_img = (f'<img src="https://{BRAND_DOMAIN}/logo-aurya-128.png" alt="" '
                f'width="34" height="34" style="vertical-align:middle;'
                f'border-radius:50%;margin-right:9px;" />')
    if store_name:
        header_html = (f'<h1>{store_name}</h1>'
                       f'<p class="via">{logo_img}via '
                       f'<span class="wordmark" style="font-size:13px;">Aurya</span></p>')
    else:
        # HP1 — il payoff, nella lingua del destinatario
        payoff = BRAND_PAYOFF.get(lang, BRAND_PAYOFF["it"])
        header_html = (f'<h1>{logo_img}<span class="wordmark">Aurya</span></h1>'
                       f'<p class="motto">{payoff}</p>')
    return f"""<!DOCTYPE html>
<html lang="{lang}">
<head><meta charset="utf-8">{_BASE_STYLE}</head>
<body>
  <div class="container">
    <div class="header">{header_html}</div>
    <div class="body">{content}</div>
    <div class="footer">
      {_t("footer_brand", lang)} &middot; <a href="https://{BRAND_DOMAIN}">{BRAND_DOMAIN}</a>
    </div>
  </div>
</body>
</html>"""


def _link_block(url: str, locale: str = "it") -> str:
    """Reusable block: copy-paste link below the CTA button."""
    return f"""<p>{_t("or_copy_link", locale)}</p>
        <p style="word-break: break-all; font-size: 13px; color: #6b7280;">{url}</p>"""


# ── Pre-built email types ─────────────────────────────────────────────────────

def send_password_reset(to_email: str, reset_token: str, locale: str = "it") -> bool:
    """Send password reset email with link."""
    reset_url = f"{APP_URL}/reset-password?token={reset_token}&lang={locale}"
    html = _wrap_template(f"""
        <p>{_t("greeting", locale)},</p>
        <p>{_t("reset_body", locale)}</p>
        <p style="text-align: center;">
            <a href="{reset_url}" class="btn">{_t("reset_cta", locale)}</a>
        </p>
        {_link_block(reset_url, locale)}
        <p>{_t("reset_expiry", locale)} {_t("ignore", locale)}</p>
    """, locale)
    return send_email(to_email, _t("reset_subject", locale), html)


# (PE9, 24/9) — `send_welcome` («Benvenuto su Aurya — Verifica la tua
# email») non esiste piu': dal 10/9 il giorno zero dell'operatore e'
# services/email_sequenze.benvenuto_operatore, e questa era importata e
# mai chiamata.


def send_admin_notification(subject: str, body: str) -> bool:
    """PE6 (24/9) — una nota interna alla casella Aurya (CASELLA_AURYA),
    testo semplice. Nata per la richiesta GDPR di cancellazione account
    (routers/customer_portal.py), che la importava senza che esistesse:
    l'ImportError era ingoiato e nessuna email partiva. Salta il gate:
    la casella e' nostra."""
    righe = "".join(f"<p>{r}</p>" if r.strip() else "" for r in (body or "").split("\n\n"))
    righe = righe.replace("\n", "<br>")
    return bool(send_email(CASELLA_AURYA, subject, _wrap_template(righe, "it"), bypass_gate=True))


def send_verification(to_email: str, verification_token: str, locale: str = "it") -> bool:
    """Send a standalone email verification link (resend flow)."""
    verify_url = f"{APP_URL}/verify-email?token={verification_token}&lang={locale}"
    html = _wrap_template(f"""
        <p>{_t("greeting", locale)},</p>
        <p>{_t("verify_body", locale)}</p>
        <p style="text-align: center;">
            <a href="{verify_url}" class="btn">{_t("verify_cta", locale)}</a>
        </p>
        {_link_block(verify_url, locale)}
        <p>{_t("verify_expiry", locale)} {_t("ignore", locale)}</p>
    """, locale)
    return send_email(to_email, _t("verify_subject", locale), html)


def send_password_changed(to_email: str, user_name: str, locale: str = "it") -> bool:
    """Notify user that their password was changed."""
    html = _wrap_template(f"""
        <p>{_t("greeting_name", locale, name=user_name)}</p>
        <p>{_t("changed_body", locale)}</p>
        <p>{_t("changed_warning", locale)}</p>
    """, locale)
    return send_email(to_email, _t("changed_subject", locale), html)


def send_team_invite(to_email: str, org_name: str, inviter_name: str, temp_password: str = None,
                     locale: str = "it", reset_token: str = None) -> bool:
    """Notify a team member they've been added.

    FL3 (5/10/2026, founder) [FIX sicurezza]: niente password in chiaro nel
    corpo. Con `reset_token` il pulsante porta a «scegli la password»
    (stesso link del reset); `temp_password` resta accettato per i chiamanti
    vecchi ma NON viene piu' scritto nell'email."""
    if reset_token:
        url = f"{APP_URL}/reset-password?token={reset_token}&lang={locale}"
    else:
        url = f"{APP_URL}/forgot-password?lang={locale}"
    html = _wrap_template(f"""
        <p>{_t("greeting", locale)},</p>
        <p>{_t("team_body", locale, inviter=inviter_name, org_name=org_name)}</p>
        <p>{_t("team_credentials", locale)}</p>
        <p style="text-align: center;">
            <a href="{url}" class="btn">{_t("team_cta", locale)}</a>
        </p>
        {_link_block(url, locale)}
        <p>{_t("team_change_password", locale)}</p>
    """, locale)
    return send_email(to_email, _t("team_subject", locale, org_name=org_name, inviter=inviter_name), html)


def send_deactivation_notice(to_email: str, org_name: str, deletion_date_str: str, locale: str = "it") -> bool:
    """Notify a user that their organization account has been deactivated."""
    html = _wrap_template(f"""
        <p>{_t("greeting", locale)},</p>
        <p>{_t("deactivation_body", locale, org_name=org_name)}</p>
        <p>{_t("deactivation_deletion", locale, date=deletion_date_str)}</p>
        <p>{_t("deactivation_reactivate", locale)}</p>
        <p>{_t("deactivation_no_action", locale)}</p>
    """, locale)
    return send_email(to_email, _t("deactivation_subject", locale, org_name=org_name), html)


def send_final_delete_warning(
    to_email: str,
    org_name: str,
    days_ago: int,
    delete_date_str: str,
    locale: str = "it",
) -> bool:
    """Wave GDPR-Admin Phase A — final reminder 7 days before hard delete.

    Sent by the background ``_hard_delete_cleanup_job`` to org members
    when the org's ``deactivated_at`` is between 22 and 23 days old
    (i.e. ~7 days before the 30-day grace period elapses). Idempotent
    via the ``hard_delete_warning_sent_at`` flag on the organization
    document — the job marks the flag after sending so re-runs don't
    spam.

    The locale is the user's own ``user.locale`` (it/en/de/fr) so each
    member of the org gets the warning in their preferred language.
    """
    html = _wrap_template(f"""
        <p>{_t("greeting", locale)},</p>
        <p>{_t("final_delete_warning_intro", locale, org_name=org_name, days_ago=days_ago)}</p>
        <p>{_t("final_delete_warning_body", locale, delete_date=delete_date_str)}</p>
        <p>{_t("final_delete_warning_reactivate", locale)}</p>
        <p>{_t("final_delete_warning_export", locale)}</p>
        <p>{_t("final_delete_warning_no_action", locale)}</p>
    """, locale)
    return send_email(
        to_email,
        _t("final_delete_warning_subject", locale, org_name=org_name),
        html,
    )


def send_platform_invite(to_email: str, invite_url: str, locale: str = "it") -> bool:
    """Invite a new user to sign up on Aurya (platform-level, by system admin)."""
    # Append lang to invite URL if not already present
    sep = "&" if "?" in invite_url else "?"
    invite_url_with_lang = f"{invite_url}{sep}lang={locale}"
    html = _wrap_template(f"""
        <p>{_t("greeting", locale)},</p>
        <p>{_t("platform_invite_body", locale)}</p>
        <p>{_t("platform_invite_cta_label", locale)}</p>
        <p style="text-align: center;">
            <a href="{invite_url_with_lang}" class="btn">{_t("platform_invite_cta", locale)}</a>
        </p>
        {_link_block(invite_url_with_lang, locale)}
        <p>{_t("platform_invite_expiry", locale)} {_t("ignore", locale)}</p>
    """, locale)
    return send_email(to_email, _t("platform_invite_subject", locale), html)


# ── Invite request (public, no auth) ─────────────────────────────────────────

ADMIN_EMAIL = "davidedefilippis94@gmail.com"


def send_invite_request_notification(name: str, email: str, business: str) -> bool:
    """Notify platform admin about a new invite request. Always in Italian (for the admin)."""
    html = _wrap_template(f"""
        <p>Nuova candidatura ricevuta su Aurya:</p>
        <p>
            <strong>Nome:</strong> {name}<br>
            <strong>Email:</strong> {email}<br>
            <strong>Attivita:</strong> {business}
        </p>
        <p>Puoi inviare un invito dal pannello admin.</p>
    """, "it")
    # FV6 — anche questo e' un modulo verso di noi: la casella di Aurya
    return send_email(CASELLA_AURYA, f"Nuova candidatura Aurya — {name}", html)


def send_invite_request_confirmation(to_email: str, name: str, locale: str = "it") -> bool:
    """Confirm to the applicant that their invite request was received."""
    html = _wrap_template(f"""
        <p>{_t("greeting_name", locale, name=name)}</p>
        <p>{_t("invite_request_confirm_body", locale)}</p>
        <p>{_t("invite_request_confirm_next", locale)}</p>
        <p>A presto,<br>Valentina e Davide</p>
    """, locale)
    return send_email(to_email, _t("invite_request_confirm_subject", locale), html)


# ── Customer Identity Foundation (v9.0) ─────────────────────────────────────
# Customer-facing emails use /account/ URLs to separate from admin /verify-email, /reset-password.

def _append_store_slug(url: str, store_slug: str | None) -> str:
    """Append `&store=<slug>` to a URL when a slug is available.

    Verification / reset / password-changed emails embed the slug so the
    landing page can route the user back to the correct storefront login
    without relying on stale localStorage state. No-op when slug is None
    (legacy callers or admin-side flows).
    """
    if not store_slug:
        return url
    return f"{url}&store={store_slug}"


def send_customer_welcome(
    to_email: str, name: str, verification_token: str, locale: str = "it",
    *, sender_name: str = None, reply_to: str = None, store_name: str = None,
    store_slug: str | None = None,
) -> bool:
    """Send welcome + email verification to a new customer account."""
    verify_url = f"{APP_URL}/account/verify-email?token={verification_token}&lang={locale}"
    verify_url = _append_store_slug(verify_url, store_slug)
    html = _wrap_template(f"""
        <p>{_t("greeting_name", locale, name=name)}</p>
        <p>{_t("customer_welcome_body", locale)}</p>
        <p style="text-align: center;">
            <a href="{verify_url}" class="btn">{_t("customer_welcome_cta", locale)}</a>
        </p>
        {_link_block(verify_url, locale)}
        <p>{_t("welcome_expiry", locale)}</p>
    """, locale, reply_to=reply_to, store_name=store_name)
    return send_email(to_email, _t("customer_welcome_subject", locale), html,
                      sender_name=sender_name, reply_to=reply_to)


def send_customer_verification(
    to_email: str, verification_token: str, locale: str = "it",
    *, sender_name: str = None, reply_to: str = None, store_name: str = None,
    store_slug: str | None = None,
) -> bool:
    """Resend email verification link to a customer account."""
    verify_url = f"{APP_URL}/account/verify-email?token={verification_token}&lang={locale}"
    verify_url = _append_store_slug(verify_url, store_slug)
    html = _wrap_template(f"""
        <p>{_t("greeting", locale)},</p>
        <p>{_t("customer_verify_body", locale)}</p>
        <p style="text-align: center;">
            <a href="{verify_url}" class="btn">{_t("customer_verify_cta", locale)}</a>
        </p>
        {_link_block(verify_url, locale)}
        <p>{_t("verify_expiry", locale)} {_t("ignore", locale)}</p>
    """, locale, reply_to=reply_to, store_name=store_name)
    return send_email(to_email, _t("customer_verify_subject", locale), html,
                      sender_name=sender_name, reply_to=reply_to)


def send_customer_password_reset(
    to_email: str, reset_token: str, locale: str = "it",
    *, sender_name: str = None, reply_to: str = None, store_name: str = None,
    store_slug: str | None = None,
) -> bool:
    """Send password reset link to a customer account."""
    reset_url = f"{APP_URL}/account/reset-password?token={reset_token}&lang={locale}"
    reset_url = _append_store_slug(reset_url, store_slug)
    html = _wrap_template(f"""
        <p>{_t("greeting", locale)},</p>
        <p>{_t("customer_reset_body", locale)}</p>
        <p style="text-align: center;">
            <a href="{reset_url}" class="btn">{_t("customer_reset_cta", locale)}</a>
        </p>
        {_link_block(reset_url, locale)}
        <p>{_t("reset_expiry", locale)} {_t("ignore", locale)}</p>
    """, locale, reply_to=reply_to, store_name=store_name)
    return send_email(to_email, _t("customer_reset_subject", locale), html,
                      sender_name=sender_name, reply_to=reply_to)


def send_customer_password_changed(
    to_email: str, name: str, locale: str = "it",
    *, sender_name: str = None, reply_to: str = None, store_name: str = None,
) -> bool:
    """Notify customer that their password was changed."""
    html = _wrap_template(f"""
        <p>{_t("greeting_name", locale, name=name)}</p>
        <p>{_t("customer_changed_body", locale)}</p>
        <p>{_t("changed_warning", locale)}</p>
    """, locale, reply_to=reply_to, store_name=store_name)
    return send_email(to_email, _t("customer_changed_subject", locale), html,
                      sender_name=sender_name, reply_to=reply_to)


# ── Onda 29: Account lockout alert (customer) ──────────────────────────────
#
# Fires from inside the customer login HTTP handler when 5 consecutive
# failed attempts trigger a per-account lockout. Two design choices:
#
#   1. ASYNC wrapper around a sync sender. Other email helpers in this
#      module are sync because they're called from endpoints that don't
#      mind a 100-200ms HTTP round-trip to Brevo. Login is different —
#      it's already on the slow path (bcrypt). We use asyncio.to_thread
#      so the SMTP send doesn't pin the event loop AND so the calling
#      `_handle_failed_login` in customer_auth_service can `await` it
#      idiomatically.
#
#   2. Best-effort. The caller (customer_auth_service._handle_failed_login)
#      wraps this in try/except so a Brevo outage CAN'T turn a successful
#      lockout into a failed login response. The lockout is the security
#      signal; the email is just a courtesy heads-up to the user.
#
# i18n keys consumed (all 4 locales): lockout_alert_subject /
# _body / _warning / _cta / _safety_note. See EMAIL_TRANSLATIONS.

def _format_unlock_human(unlock_at_iso: str) -> str:
    """Render an ISO UTC timestamp as a short human-readable form
    suitable for inline email copy. Falls back to the raw ISO if
    parsing fails so we never crash the email send on a malformed
    timestamp upstream.
    """
    try:
        from datetime import datetime
        dt = datetime.fromisoformat(unlock_at_iso)
        # e.g. "07/05/2026 14:30 UTC" — locale-agnostic and unambiguous.
        return dt.strftime("%d/%m/%Y %H:%M") + " UTC"
    except Exception:
        return unlock_at_iso


def _send_account_lockout_alert_sync(
    customer_email: str, locale: str, unlock_at_iso: str,
    forgot_password_url: Optional[str] = None,
) -> bool:
    """Synchronous body of the lockout alert. Called via
    asyncio.to_thread from send_account_lockout_alert (below).

    Onda 30: `forgot_password_url` is now a parameter. Default
    behaviour (None / not passed) is the customer URL
    /account/forgot-password — backward compatible with Onda 29
    callers. The admin caller in services/auth_service passes
    the admin /forgot-password URL explicitly.
    """
    unlock_human = _format_unlock_human(unlock_at_iso)
    if forgot_password_url is None:
        forgot_password_url = f"{APP_URL}/account/forgot-password?lang={locale}"
    html = _wrap_template(f"""
        <p>{_t("greeting", locale)},</p>
        <p>{_t("lockout_alert_body", locale, unlock_at=unlock_human)}</p>
        <p style="font-weight: 600;">{_t("lockout_alert_warning", locale)}</p>
        <p style="text-align: center;">
            <a href="{forgot_password_url}" class="btn">{_t("lockout_alert_cta", locale)}</a>
        </p>
    """, locale)
    return send_email(customer_email, _t("lockout_alert_subject", locale), html)


async def send_account_lockout_alert(
    customer_email: str, locale: str, unlock_at_iso: str,
    forgot_password_url: Optional[str] = None,
) -> bool:
    """Async wrapper — delegates the blocking SMTP call to a worker
    thread so the customer login event loop doesn't stall.

    Returns True/False (the underlying send_email return value).
    Best-effort by design: the caller in customer_auth_service is
    responsible for catching exceptions and never letting them bubble
    into the user-facing 401/423 response.

    Onda 30 — added optional `forgot_password_url`. When None (the
    default), embeds the customer-portal /account/forgot-password
    URL — preserves Onda 29 behaviour exactly. The admin login path
    (services/auth_service._handle_failed_admin_login) passes the
    admin /forgot-password URL explicitly.
    """
    import asyncio
    return await asyncio.to_thread(
        _send_account_lockout_alert_sync,
        customer_email, locale, unlock_at_iso, forgot_password_url,
    )


# ── Onda 16: Reservation confirmation email ────────────────────────────────


def _reservation_block_html(reservation: dict, product_name: str, landing_url: str,
                            locale: str = "it") -> str:
    """Render the reservation summary block embedded in confirmation emails.

    Used both by the dedicated resend endpoint and by order_email_service
    when the order contains rental/slot lines.
    """
    # FL3 (5/10/2026, founder): date e orari in italiano, mai ISO grezzo
    from services.order_email_service import _fmt_short_date_localized as _fd
    flavor = reservation.get("reservation_flavor")
    if flavor == "range":
        date_from = reservation.get("date_from", "")
        date_to = reservation.get("date_to", "") or date_from
        when = (f"dal {_fd(date_from, locale)} al {_fd(date_to, locale)}"
                if date_to and date_to != date_from else _fd(date_from, locale))
    else:
        sd = reservation.get("slot_date", "")
        ss = reservation.get("slot_start_time", "")
        se = reservation.get("slot_end_time", "")
        when = f"{_fd(sd, locale)}, {ss}-{se}" if sd else ""

    extras_rows = ""
    for ex in reservation.get("extras_snapshot") or []:
        label = ex.get("label", "")
        amount = ex.get("line_total", 0)
        extras_rows += (
            f'<tr><td style="padding:2px 0;color:#555;">{label}</td>'
            f'<td style="padding:2px 0;text-align:right;color:#111;">€{amount:.2f}</td></tr>'
        )

    location_html = ""
    if reservation.get("location"):
        location_html = (
            f'<p style="margin:6px 0;color:#555;">📍 {reservation["location"]}</p>'
        )

    return f"""
    <div style="border:1px solid #e5e7eb;border-radius:8px;padding:16px;margin:16px 0;">
      <p style="margin:0 0 8px 0;font-weight:600;">{product_name}</p>
      <p style="margin:0 0 4px 0;color:#333;">📅 {when}</p>
      {location_html}
      <p style="margin:8px 0 4px 0;color:#555;">{_t("reservation_code_label", locale)}: <b>{reservation.get("code", "")}</b></p>
      {f'<table style="width:100%;margin-top:8px;font-size:13px;">{extras_rows}</table>' if extras_rows else ''}
      <p style="margin:12px 0 0 0;">
        <a href="{landing_url}" class="btn" style="margin:0;">
          {_t("reservation_view_cta", locale)}
        </a>
      </p>
    </div>
    """


async def send_reservation_confirmation_email(
    *,
    reservation_id: Optional[str] = None,
    reservation: Optional[dict] = None,
    org_id: Optional[str] = None,
) -> bool:
    """Send (or resend) a reservation confirmation email.

    Accepts either a resolved reservation dict or a reservation_id + org_id
    pair (which we'll fetch). Uses store_settings for sender branding.
    """
    from database import issued_reservations_collection, products_collection, organizations_collection

    if reservation is None:
        if not (reservation_id and org_id):
            return False
        reservation = await issued_reservations_collection.find_one(
            {"id": reservation_id, "organization_id": org_id},
            {"_id": 0},
        )
        if not reservation:
            return False

    email = reservation.get("holder_email")
    if not email:
        return False

    product = await products_collection.find_one(
        {"id": reservation.get("product_id")}, {"_id": 0, "name": 1}
    ) or {}
    product_name = product.get("name") or reservation.get("product_name") or "Prenotazione"

    org = await organizations_collection.find_one(
        {"id": reservation.get("organization_id")},
        {"_id": 0, "name": 1, "store_settings": 1},
    ) or {}
    store = (org.get("store_settings") or {})
    store_name = store.get("display_name") or org.get("name") or "Store"
    sender_name = store.get("sender_display_name") or SMTP_FROM_NAME
    # FV7 — il cliente risponde all'operatore anche senza reply_to impostato
    from services.order_email_service import contatto_operatore
    reply_to = store.get("reply_to_email") or await contatto_operatore(org_id, store)

    token = reservation.get("access_token") or ""
    landing_url = f"{APP_URL}/rsv/{token}" if token else APP_URL

    # R2a — lingua del compratore dall'ordine collegato (order.locale →
    # account store → lingua negozio → it), prima hardcoded "it".
    locale = "it"
    try:
        from database import orders_collection as _orders
        from services.order_email_service import _get_customer_email_and_locale
        _order = await _orders.find_one(
            {"id": reservation.get("order_id")},
            {"_id": 0, "locale": 1, "customer_account_id": 1,
             "organization_id": 1, "store_id": 1, "customer_id": 1},
        )
        if _order:
            _, locale = await _get_customer_email_and_locale(_order)
    except Exception as _exc:  # noqa: BLE001 — best-effort, mai bloccare l'invio
        logger.debug("reservation email: locale resolution failed: %s", _exc)

    block = _reservation_block_html(reservation, product_name, landing_url, locale)
    html = _wrap_template(f"""
        <p>{_t("greeting", locale)},</p>
        <p>{_t("reservation_confirm_body", locale)}</p>
        {block}
        <p style="color:#666;font-size:12px;">{_t("reservation_keep_note", locale)}</p>
    """, locale, reply_to=reply_to, store_name=store_name)

    subject = _t("reservation_confirm_subject", locale, product=product_name)
    ok = send_email(email, subject, html, reply_to=reply_to, sender_name=sender_name)

    # Update delivery audit.
    from models.common import utc_now as _now
    now = _now().isoformat()

    await issued_reservations_collection.update_one(
        {"id": reservation.get("id")},
        {"$set": {
            "delivery_status": "sent" if ok else "failed",
            "delivery_last_attempt_at": now,
            "sent_at": now if ok else reservation.get("sent_at"),
        },
         "$inc": {"delivery_attempts": 1}},
    )
    return ok
