"""
Transactional email service via Brevo HTTP API.

Usage:
    from services.email_service import send_email, send_password_reset, send_welcome

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
        "ignore": "Se non hai richiesto tu questa azione, ignora questa email.",
        "footer_brand": "Aurya — Ritiri ed esperienze olistiche, in un posto solo.",
        "footer_auto": "Questa email e' stata inviata automaticamente, non rispondere.",
        "footer_reply_to": "Per rispondere, scrivi a {email}.",
        # Invite request confirmation
        "invite_request_confirm_subject": "Candidatura ricevuta — Aurya",
        "invite_request_confirm_body": "Abbiamo ricevuto la tua richiesta di accesso ad Aurya.",
        "invite_request_confirm_next": "Ti contatteremo al piu presto per fornirti l'accesso.",
        # Welcome / verify
        "welcome_subject": "Benvenuto su Aurya — Verifica la tua email",
        "welcome_subject_no_token": "Benvenuto su Aurya!",
        "welcome_body": "Benvenuto su Aurya! Il tuo account e' stato creato con successo.",
        "welcome_verify": "Per completare la registrazione, verifica il tuo indirizzo email:",
        "welcome_cta": "Verifica Email",
        "welcome_no_token_body": "Puoi accedere alla piattaforma usando la tua email e password:",
        "welcome_no_token_cta": "Accedi ad Aurya",
        "welcome_expiry": "Il link scade tra <strong>24 ore</strong>.",
        # Verification (resend)
        "verify_subject": "Verifica il tuo indirizzo email — Aurya",
        "verify_body": "Clicca il pulsante qui sotto per verificare il tuo indirizzo email:",
        "verify_cta": "Verifica Email",
        "verify_expiry": "Il link scade tra <strong>24 ore</strong>.",
        # Password reset
        "reset_subject": "Reimposta la tua password — Aurya",
        "reset_body": "Hai richiesto il reset della tua password. Clicca il pulsante qui sotto per impostarne una nuova:",
        "reset_cta": "Reimposta Password",
        "reset_expiry": "Il link scade tra <strong>1 ora</strong>.",
        # Password changed
        "changed_subject": "Password modificata — Aurya",
        "changed_body": "La tua password e' stata modificata con successo.",
        "changed_warning": "Se non sei stato tu a effettuare questa modifica, contattaci immediatamente o usa il link \"Password dimenticata\" per reimpostarla.",
        "lockout_alert_subject": "Tentativi sospetti sul tuo account Aurya",
        "lockout_alert_body": "Abbiamo rilevato 5 tentativi falliti di accesso al tuo account. Per sicurezza, abbiamo bloccato temporaneamente l'accesso fino a {unlock_at}.",
        "lockout_alert_warning": "Se non sei stato tu, ti consigliamo di reimpostare la password immediatamente.",
        "lockout_alert_cta": "Reimposta password",
        "lockout_alert_safety_note": "Se sei stato tu a sbagliare, riprova dopo che il blocco scade, oppure reimposta la password se l'hai dimenticata.",
        # Team invite
        "team_subject": "Sei stato invitato su Aurya — {org_name}",
        "team_body": "<strong>{inviter}</strong> ti ha invitato a unirti a <strong>{org_name}</strong> su Aurya.",
        "team_credentials": "Le tue credenziali temporanee:",
        "team_cta": "Accedi ad Aurya",
        "team_change_password": "<strong>Ti consigliamo di cambiare la password al primo accesso.</strong>",
        # Deactivation
        "deactivation_subject": "Account Aurya disattivato — {org_name}",
        "deactivation_body": "L'account dell'organizzazione <strong>{org_name}</strong> su Aurya e' stato disattivato.",
        "deactivation_deletion": "Tutti i dati saranno <strong>eliminati definitivamente il {date}</strong> (30 giorni dalla disattivazione).",
        "deactivation_reactivate": "Se desideri riattivare l'account, contatta l'amministratore della tua organizzazione prima di tale data.",
        "deactivation_no_action": "Se non desideri piu' utilizzare il servizio, non e' necessaria alcuna azione.",
        # GDPR-Admin Phase A — Final warning before hard delete (7 days before)
        "final_delete_warning_subject": "ULTIMO AVVISO — Eliminazione definitiva tra 7 giorni — {org_name}",
        "final_delete_warning_intro": "Ti scriviamo per ricordarti che l'account <strong>{org_name}</strong> e' stato disattivato {days_ago} giorni fa.",
        "final_delete_warning_body": "Conformemente alla nostra Privacy Policy (Art. 17 GDPR), tutti i dati associati a questa organizzazione saranno <strong>eliminati definitivamente il {delete_date}</strong> (tra 7 giorni). Questa azione e' irreversibile.",
        "final_delete_warning_reactivate": "Se vuoi recuperare l'account, devi <strong>riattivarlo entro tale data</strong>. Dopo l'eliminazione non sara' piu' possibile recuperare i dati.",
        "final_delete_warning_export": "Se desideri scaricare una copia dei tuoi dati prima dell'eliminazione, puoi farlo dalla sezione 'Impostazioni > Dati personali' del tuo account (se ancora attivo) o contattando il supporto.",
        "final_delete_warning_no_action": "Se desideri procedere con l'eliminazione, non e' necessaria alcuna azione: la cancellazione avverra' automaticamente alla scadenza.",
        # Platform invite
        "platform_invite_subject": "Sei stato invitato su Aurya",
        "platform_invite_body": "Sei stato invitato a registrarti su <strong>Aurya</strong>, la piattaforma di gestione finanziaria per PMI.",
        "platform_invite_cta_label": "Clicca il pulsante qui sotto per creare il tuo account:",
        "platform_invite_cta": "Registrati su Aurya",
        "platform_invite_expiry": "Il link scade tra <strong>7 giorni</strong>.",
        # Customer account (v9.0)
        "customer_welcome_subject": "Benvenuto — Il tuo account e' stato creato",
        "customer_welcome_body": "Il tuo account e' stato creato con successo. Verifica il tuo indirizzo email per iniziare:",
        "customer_welcome_cta": "Verifica Email",
        "customer_verify_subject": "Verifica il tuo indirizzo email",
        "customer_verify_body": "Clicca il pulsante qui sotto per verificare il tuo indirizzo email:",
        "customer_verify_cta": "Verifica Email",
        "customer_reset_subject": "Reimposta la tua password",
        "customer_reset_body": "Hai richiesto il reset della tua password. Clicca il pulsante qui sotto:",
        "customer_reset_cta": "Reimposta Password",
        "customer_changed_subject": "Password modificata",
        "customer_changed_body": "La tua password e' stata modificata con successo.",
        # Order transactional emails (v10.1)
        "order_received_subject": "Richiesta ricevuta — {store_name}",
        "order_received_body": "La tua richiesta e' stata registrata. Ti contatteremo a breve.",
        "order_received_ref": "Riferimento ordine: <strong>{order_ref}</strong>",
        "order_received_items": "Articoli: {count}",
        "order_received_total": "Totale: {total}",
        "order_received_cta": "I miei ordini",
        "order_merchant_subject": "Nuova richiesta — {customer_name}",
        "order_merchant_body": "Una nuova richiesta e' arrivata dal catalogo pubblico.",
        "order_merchant_customer": "Cliente: <strong>{customer_name}</strong> ({customer_email})",
        "order_merchant_items": "Articoli: {count}",
        "order_merchant_total": "Totale stimato: {total}",
        "order_merchant_fulfillment": "Consegna: {mode}",
        "order_merchant_cta": "Vai agli ordini",
        "order_merchant_notes": "<strong>Note:</strong> {notes}",
        "order_merchant_draft_hint": "Questo ordine e' in stato bozza. Confermalo dalla pagina Ordini.",
        "order_confirmed_subject": "Ordine confermato — {store_name}",
        "order_confirmed_body": "Il tuo ordine e' stato confermato ed e' in lavorazione.",
        "order_confirmed_ref": "Ordine: <strong>{order_ref}</strong>",
        "order_confirmed_cta": "Vedi dettaglio ordine",
        # Fase 2 S2 (retreat) — riepilogo piano pagamenti in email conferma
        "payment_plan_heading": "Il tuo piano di pagamenti",
        "payment_plan_paid_row": "{label}: <strong>{amount}</strong> — pagata &#10003;",
        "payment_plan_pending_row": "{label}: <strong>{amount}</strong> — entro il {due_date}",
        "payment_plan_reminder_note": "Ti manderemo un promemoria con il link di pagamento prima di ogni scadenza: non devi fare nulla ora.",
        # Fase 2 S3 — promemoria/solleciti saldo e notifica at-risk operatore
        "pay_reminder_subject_t7": "Promemoria: {amount} in scadenza — {store_name}",
        "pay_reminder_subject_t0": "Scade oggi: {amount} — {store_name}",
        "pay_sollecito_subject": "Pagamento in ritardo: {amount} — {store_name}",
        "pay_reminder_body": "Ti ricordiamo la scadenza per l'ordine <strong>{order_ref}</strong>: {label} di <strong>{amount}</strong> entro il <strong>{due_date}</strong>. Puoi pagare in un click dal bottone qui sotto.",
        "pay_sollecito_body": "La scadenza per l'ordine <strong>{order_ref}</strong> e' passata: {label} di <strong>{amount}</strong> era dovuta entro il <strong>{due_date}</strong>. Ti chiediamo di regolarizzare il pagamento dal bottone qui sotto.",
        "pay_now_cta": "Paga ora",
        "pay_reminder_footer": "Il link genera un pagamento sicuro via Stripe. Se hai gia' pagato con bonifico, ignora questa email: l'organizzatore aggiornera' la tua posizione.",
        "pay_atrisk_merchant_subject": "Pagamento a rischio: {customer} — {amount}",
        "pay_atrisk_merchant_body": "Il pagamento <strong>{label}</strong> di <strong>{amount}</strong> per l'ordine <strong>{order_ref}</strong> ({customer}) era dovuto entro il {due_date}. Dopo 3 promemoria automatici non risulta ancora pagato.",
        "pay_atrisk_merchant_actions": "Cosa puoi fare dalla dashboard incassi del ritiro: segnarlo pagato (se ha pagato con bonifico), condonarlo, prorogare la scadenza o liberare il posto. Nessuna azione automatica verra' presa senza di te.",
        # R2a — conferma prenotazione (Onda 16), prima hardcoded it
        "reservation_confirm_subject": "Prenotazione confermata — {product}",
        "reservation_confirm_body": "La tua prenotazione e' confermata. Trovi tutti i dettagli qui sotto.",
        "reservation_keep_note": "Conserva questa email, il link sopra e' privato.",
        "reservation_code_label": "Codice",
        "reservation_view_cta": "Vedi prenotazione",
        # R2a — Passaporto: login OTP/magic link + claim post-acquisto
        # (l'email piu' vista dai viaggiatori — prima hardcoded it)
        "passport_login_subject": "Il tuo accesso — un click e sei dentro",
        "passport_code_intro": "Il tuo codice di accesso (vale {minutes} minuti):",
        "passport_code_hint": "Digitalo nella pagina da cui l'hai richiesto — oppure usa il link qui sotto.",
        "passport_link_intro": "Link di accesso — vale {minutes} minuti e funziona una volta sola:",
        "passport_login_cta": "Accedi al tuo account",
        "passport_login_ignore": "Se non hai richiesto tu questo link, ignora questa email: nessuno puo' accedere senza di essa.",
        "passport_claim_subject": "Le tue prenotazioni, in un unico posto",
        "passport_claim_body": "Grazie della tua prenotazione! Con un click attivi il tuo account: ritrovi tutte le prenotazioni, i pagamenti e i biglietti in un unico posto — anche se prenoti con organizzatori diversi.",
        "passport_claim_cta": "Gestisci le tue prenotazioni",
        "passport_claim_footer": "Il link vale {minutes} minuti. Nessuna password da ricordare: quando ti serve, te ne mandiamo uno nuovo.",
        # PR2 — OTP recensione operatore
        "review_otp_subject": "Il tuo codice per lasciare una recensione",
        "review_otp_body": "Stai per lasciare una recensione. Ecco il tuo codice di verifica:",
        "review_otp_hint": "Vale {minutes} minuti. Se non hai richiesto tu questo codice, ignora questa email.",

        # Fase 4 — follow-up post ritiro
        "event_email_broadcast_followup_subject": "Grazie per aver partecipato — {event}",
        "event_email_broadcast_followup_body": "Grazie di cuore per aver fatto parte di <strong>{event}</strong>. Speriamo che l'esperienza ti abbia lasciato qualcosa di buono.",
        "event_email_broadcast_followup_outro": "Se ti va di restare in contatto e sapere dei prossimi appuntamenti, rispondi pure a questa email: ci fa sempre piacere.",        "order_cancelled_subject": "Ordine annullato — {store_name}",
        "order_cancelled_body": "Il tuo ordine e' stato annullato.",
        "order_cancelled_ref": "Riferimento: <strong>{order_ref}</strong>",
        "order_cancelled_contact": "Per qualsiasi domanda, rispondi a questa email.",
        "fulfillment_shipped_subject": "Il tuo ordine e' stato spedito — {store_name}",
        "fulfillment_shipped_body": "Il tuo ordine e' stato spedito.",
        "fulfillment_ready_subject": "Il tuo ordine e' pronto per il ritiro — {store_name}",
        "fulfillment_ready_body": "Il tuo ordine e' pronto per il ritiro.",
        "fulfillment_delivered_subject": "Ordine consegnato — {store_name}",
        "fulfillment_delivered_body": "Il tuo ordine e' stato consegnato.",
        "fulfillment_picked_up_subject": "Ordine ritirato — {store_name}",
        "fulfillment_picked_up_body": "Il tuo ordine e' stato ritirato con successo.",
        "fulfillment_fulfilled_subject": "Ordine completato — {store_name}",
        "fulfillment_fulfilled_body": "Il tuo ordine e' stato completato.",
        "fulfillment_ref": "Riferimento: <strong>{order_ref}</strong>",
        "fulfillment_mode_shipping": "Spedizione",
        "fulfillment_mode_local_pickup": "Ritiro in sede",
        "fulfillment_mode_manual_arrangement": "Accordo manuale",
        "fulfillment_tracking_label": "Codice tracking",
        "fulfillment_tracking_cta": "Traccia il pacco",
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
        "event_email_greeting_attendee_fallback": "partecipante",
        "event_email_ticket_resend_intro": "come richiesto, ecco nuovamente il tuo biglietto per <strong>{event}</strong>.",
        "event_email_ticket_personal_intro": "Ecco il tuo biglietto personale per <strong>{event}</strong>.",
        "event_email_ticket_label": "Il tuo biglietto",
        "event_email_ticket_seat_hint": "Biglietto {seat_index} di {seat_count}",
        "event_email_ticket_open_cta": "Apri biglietto e QR \u2192",
        "event_email_ticket_qr_hint": "Mostra il QR o dettalo all'ingresso per il check-in. Conserva questa email.",
        "event_email_ticket_link_privacy_hint": "Apri il link dal tuo telefono all'ingresso. Il link e' privato \u2014 non condividerlo.",
        "event_email_subject_ticket": "Il tuo biglietto \u2014 {event}",
        "event_email_fallback_event_name": "Evento",
        "event_email_broadcast_reminder_subject": "Ci vediamo presto \u2014 {event}",
        "event_email_broadcast_reminder_body": "Ti aspettiamo al tuo evento!",
        "event_email_broadcast_reminder_outro": "Ricordati di portare il biglietto (email o QR code). A breve ci vediamo.",
        "event_email_broadcast_logistics_subject": "Informazioni pratiche \u2014 {event}",
        "event_email_broadcast_logistics_body": "Qualche info pratica per il tuo evento:",
        "event_email_broadcast_logistics_outro": "Per domande rispondi a questa email.",
        "event_email_broadcast_cancellation_subject": "Evento annullato \u2014 {event}",
        "event_email_broadcast_cancellation_body": "<strong>Ci dispiace informarti che l'evento e' stato annullato.</strong>",
        "event_email_broadcast_cancellation_outro": "Riceverai presto istruzioni sul rimborso. Scusaci per il disagio.",
        "event_email_broadcast_custom_subject_fallback": "Aggiornamento \u2014 {event}",
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
        "order_section_tickets_privacy_hint": "Clicca \"Apri biglietto\" per vedere il QR all'ingresso. Ogni link e' privato \u2014 conservalo.",
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
        "order_section_downloads_privacy_hint": "\U0001F512 Il link e' personale. Conservalo \u2014 se lo perdi puoi recuperarlo dal tuo account.",
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
        "store_alert_degraded_subject": "Attenzione: {store_name} ha problemi di configurazione",
        "store_alert_degraded_intro": "Il tuo store <strong>{store_name}</strong> ha configurazioni critiche che richiedono attenzione.",
        "store_alert_degraded_outro": "Il tuo storefront e' ancora accessibile, ma alcune funzionalita' potrebbero non funzionare correttamente.",
        "store_alert_recovery_subject": "{store_name} e' di nuovo operativo",
        "store_alert_recovery_intro": "Ottimo! Il tuo store <strong>{store_name}</strong> e' di nuovo completamente operativo.",
        "store_alert_recovery_outro": "Tutte le configurazioni necessarie sono a posto. Il tuo storefront funziona correttamente.",
        "store_alert_settings_cta": "Vai alle impostazioni",
        "store_alert_configure_link": "Configura",
        "store_alert_check_public_slug": "Indirizzo pubblico storefront",
        "store_alert_check_display_name": "Nome pubblico del business",
        "store_alert_check_contact_email": "Email di contatto pubblica",
        "store_alert_check_payment_provider": "Provider di pagamento",
        "store_alert_check_publishable_offer": "Prodotto pubblicato",
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
        "quota_warning_subject": "Stai per raggiungere il limite di {metric}",
        "quota_warning_intro": "Il tuo store ha utilizzato {used} su {limit} {metric} questo mese — siamo all'80%.",
        "quota_warning_outro": "Per non interrompere il servizio, valuta un pack aggiuntivo o passa al piano superiore.",
        "quota_warning_cta_addon": "Acquista pack",
        "quota_warning_cta_upgrade": "Aggiorna piano",
        "quota_exceeded_subject": "Limite {metric} raggiunto",
        "quota_exceeded_intro": "Hai raggiunto il limite di {metric} per questo mese ({used}/{limit}).",
        "quota_exceeded_outro_blocking": "Le richieste future saranno bloccate fino al rinnovo del periodo o all'attivazione di un pack/piano superiore.",
        "quota_exceeded_outro_soft": "Il servizio prosegue (le email transazionali non sono mai bloccate). Per coerenza con il tuo piano, valuta un pack o un upgrade.",
        "quota_metric_chat": "chat AI",
        "quota_metric_orders_monthly": "ordini ecommerce",
        "quota_metric_data_rows": "righe dataset",
        "quota_metric_products": "prodotti",
        "quota_metric_stores_max": "store",
        "quota_metric_digest": "digest AI",
        "quota_metric_email_alerts": "alert email",
        "quota_metric_fallback": "utilizzo",
        "quota_addon_offer_chat": "Pack +50 chat AI a soli €9/mese",
        "quota_addon_offer_orders_monthly": "Pack +200 ordini a soli €15/mese",
        "quota_addon_offer_stores_max": "Pack +1 store a soli €19/mese",
        "quota_addon_offer_fallback": "Aggiorna il piano per estendere il limite",
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
        "passport_login_subject": "Your sign-in — one click and you're in",
        "passport_code_intro": "Your access code (valid for {minutes} minutes):",
        "passport_code_hint": "Type it on the page where you requested it — or use the link below.",
        "passport_link_intro": "Sign-in link — valid for {minutes} minutes, works once:",
        "passport_login_cta": "Sign in to your account",
        "passport_login_ignore": "If you didn't request this link, just ignore this email: nobody can sign in without it.",
        "passport_claim_subject": "All your bookings, in one place",
        "passport_claim_body": "Thanks for your booking! One click activates your account: find all your bookings, payments and tickets in one place — even across different organizers.",
        "passport_claim_cta": "Manage your bookings",
        "passport_claim_footer": "The link is valid for {minutes} minutes. No password to remember: whenever you need one, we'll send you a fresh link.",
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
        "passport_login_subject": "Dein Zugang — ein Klick und du bist drin",
        "passport_code_intro": "Dein Zugangscode (gueltig fuer {minutes} Minuten):",
        "passport_code_hint": "Gib ihn auf der Seite ein, auf der du ihn angefordert hast — oder nutze den Link unten.",
        "passport_link_intro": "Anmeldelink — gueltig fuer {minutes} Minuten, funktioniert einmal:",
        "passport_login_cta": "In deinem Konto anmelden",
        "passport_login_ignore": "Wenn du diesen Link nicht angefordert hast, ignoriere diese E-Mail: ohne ihn kann sich niemand anmelden.",
        "passport_claim_subject": "Alle deine Buchungen, an einem Ort",
        "passport_claim_body": "Danke fuer deine Buchung! Ein Klick aktiviert dein Konto: alle Buchungen, Zahlungen und Tickets an einem Ort — auch bei verschiedenen Veranstaltern.",
        "passport_claim_cta": "Buchungen verwalten",
        "passport_claim_footer": "Der Link ist {minutes} Minuten gueltig. Kein Passwort noetig: wenn du einen brauchst, senden wir dir einen neuen Link.",
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
        "passport_login_subject": "Votre acces — un clic et vous y etes",
        "passport_code_intro": "Votre code d'acces (valable {minutes} minutes) :",
        "passport_code_hint": "Saisissez-le sur la page ou vous l'avez demande — ou utilisez le lien ci-dessous.",
        "passport_link_intro": "Lien de connexion — valable {minutes} minutes, utilisable une seule fois :",
        "passport_login_cta": "Acceder a votre compte",
        "passport_login_ignore": "Si vous n'avez pas demande ce lien, ignorez cet email : personne ne peut se connecter sans lui.",
        "passport_claim_subject": "Toutes vos reservations, au meme endroit",
        "passport_claim_body": "Merci pour votre reservation ! Un clic active votre compte : retrouvez toutes vos reservations, paiements et billets au meme endroit — meme avec des organisateurs differents.",
        "passport_claim_cta": "Gerer vos reservations",
        "passport_claim_footer": "Le lien est valable {minutes} minutes. Aucun mot de passe a retenir : quand vous en avez besoin, nous vous en envoyons un nouveau.",
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
) -> bool:
    """
    Send a single transactional email via Brevo HTTP API.
    Returns True on success, False on failure.
    Never raises — errors are logged.

    Optional keyword args (backward-compatible — existing callers unchanged):
      reply_to:    email address for Reply-To header (Brevo replyTo field)
      sender_name: override sender display name (default: SMTP_FROM_NAME)
      bypass_gate: when True, skip the pre-flight email gate (Track G G1).
                   Use sparingly — currently no caller sets it. Reserved
                   for future cases like unsubscribe-confirmation emails
                   where we MUST send even to known-bad addresses.
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

    data = {
        "sender": {"name": sender_name or SMTP_FROM_NAME, "email": SMTP_FROM_EMAIL},
        "to": [{"email": to_email}],
        "subject": subject,
        "htmlContent": html_body,
    }
    if reply_to:
        data["replyTo"] = {"email": reply_to}

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
  .header .motto { margin: 7px 0 0; font-family: 'Cinzel', 'Palatino Linotype', Georgia, serif; text-transform: uppercase; letter-spacing: 0.3em; font-size: 10px; color: rgba(203,181,120,0.85); }
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


def _wrap_template(content: str, locale: str = "it", *, reply_to: str = None, store_name: str = None) -> str:
    lang = locale if locale in SUPPORTED_LOCALES else "it"
    # If reply_to is configured, don't say "do not reply" — say where to reply
    if reply_to:
        footer_line = _t("footer_reply_to", lang, email=reply_to)
    else:
        footer_line = _t("footer_auto", lang)
    # Header: store-branded when context available, platform-only otherwise.
    # Logo ufficiale (loto+sole, 13/7/2026) hostato sul dominio: risolve
    # appena il sito è deployato; il testo accanto copre il frattempo e
    # i client che bloccano le immagini.
    from core.brand import BRAND_DOMAIN
    logo_img = (f'<img src="https://{BRAND_DOMAIN}/logo-aurya-128.png" alt="" '
                f'width="34" height="34" style="vertical-align:middle;'
                f'border-radius:50%;margin-right:9px;" />')
    if store_name:
        header_html = (f'<h1>{store_name}</h1>'
                       f'<p class="via">{logo_img}via '
                       f'<span class="wordmark" style="font-size:13px;">Aurya</span></p>')
    else:
        header_html = (f'<h1>{logo_img}<span class="wordmark">Aurya</span></h1>'
                       f'<p class="motto">Connect. Heal. Grow.</p>')
    return f"""<!DOCTYPE html>
<html lang="{lang}">
<head><meta charset="utf-8">{_BASE_STYLE}</head>
<body>
  <div class="container">
    <div class="header">{header_html}</div>
    <div class="body">{content}</div>
    <div class="footer">
      &copy; {_t("footer_brand", lang)}<br>
      <a href="https://{BRAND_DOMAIN}">{BRAND_DOMAIN}</a><br>
      {footer_line}
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


def send_welcome(to_email: str, user_name: str, verification_token: str = "", locale: str = "it") -> bool:
    """Send welcome email after registration, with verification link if token provided."""
    if verification_token:
        verify_url = f"{APP_URL}/verify-email?token={verification_token}&lang={locale}"
        html = _wrap_template(f"""
            <p>{_t("greeting_name", locale, name=user_name)}</p>
            <p>{_t("welcome_body", locale)}</p>
            <p>{_t("welcome_verify", locale)}</p>
            <p style="text-align: center;">
                <a href="{verify_url}" class="btn">{_t("welcome_cta", locale)}</a>
            </p>
            {_link_block(verify_url, locale)}
            <p>{_t("welcome_expiry", locale)}</p>
        """, locale)
        return send_email(to_email, _t("welcome_subject", locale), html)
    else:
        login_url = f"{APP_URL}/login?lang={locale}"
        html = _wrap_template(f"""
            <p>{_t("greeting_name", locale, name=user_name)}</p>
            <p>{_t("welcome_body", locale)}</p>
            <p>{_t("welcome_no_token_body", locale)}</p>
            <p style="text-align: center;">
                <a href="{login_url}" class="btn">{_t("welcome_no_token_cta", locale)}</a>
            </p>
        """, locale)
        return send_email(to_email, _t("welcome_subject_no_token", locale), html)


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


def send_team_invite(to_email: str, org_name: str, inviter_name: str, temp_password: str, locale: str = "it") -> bool:
    """Notify a team member they've been added."""
    login_url = f"{APP_URL}/login?lang={locale}"
    html = _wrap_template(f"""
        <p>{_t("greeting", locale)},</p>
        <p>{_t("team_body", locale, inviter=inviter_name, org_name=org_name)}</p>
        <p>{_t("team_credentials", locale)}</p>
        <p>
            Email: <span class="code">{to_email}</span><br>
            Password: <span class="code">{temp_password}</span>
        </p>
        <p style="text-align: center;">
            <a href="{login_url}" class="btn">{_t("team_cta", locale)}</a>
        </p>
        <p>{_t("team_change_password", locale)}</p>
    """, locale)
    return send_email(to_email, _t("team_subject", locale, org_name=org_name), html)


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
    return send_email(ADMIN_EMAIL, f"Nuova candidatura Aurya — {name}", html)


def send_invite_request_confirmation(to_email: str, name: str, locale: str = "it") -> bool:
    """Confirm to the applicant that their invite request was received."""
    html = _wrap_template(f"""
        <p>{_t("greeting_name", locale, name=name)}</p>
        <p>{_t("invite_request_confirm_body", locale)}</p>
        <p>{_t("invite_request_confirm_next", locale)}</p>
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
        <p style="font-size: 0.85em; color: #666;">{_t("lockout_alert_safety_note", locale)}</p>
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
    flavor = reservation.get("reservation_flavor")
    if flavor == "range":
        date_from = reservation.get("date_from", "")
        date_to = reservation.get("date_to", "") or date_from
        when = f"{date_from} → {date_to}" if date_to and date_to != date_from else date_from
    else:
        sd = reservation.get("slot_date", "")
        ss = reservation.get("slot_start_time", "")
        se = reservation.get("slot_end_time", "")
        when = f"{sd} · {ss}–{se}" if sd else ""

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
    reply_to = store.get("reply_to_email")

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
