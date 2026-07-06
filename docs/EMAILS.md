# EMAILS.md — matrice delle email transazionali (fonte unica)

> Aggiornata al 6/7/2026 (R2a lingua + R2b redesign). Ogni email indossa
> il template comune `_wrap_template` + `_BASE_STYLE`
> (backend/services/email_service.py): header salvia con wordmark 🌿
> (store-branded «{store} · via Aurya» quando c'è contesto negozio),
> bottoni pill terracotta `#CB774D`, footer crema con tagline, link
> aurya.life e riga reply-to/no-reply. UNA modifica lì veste tutto.

## Come si risolve la lingua (R2a)

| Destinatario | Catena |
|---|---|
| Compratore (ordine) | `order.locale` (lingua UI al checkout) → account store → 1ª lingua storefront → it |
| Viaggiatore (Passaporto) | `platform_account.language` (aggiornata a ogni richiesta OTP con la lingua UI) → it; la claim usa `order.locale` |
| Cliente store (auth) | `customer.locale` → store → it |
| Operatore | `user.locale` del destinatario → 1ª lingua storefront → it |

Tutte le stringhe vivono in `EMAIL_TRANSLATIONS` (4 lingue: it/en/de/fr,
`_t()` ripiega su it per chiave mancante — guard-test
`tests/test_email_locale_r2a.py` copre i cluster critici).

## Viaggiatore / compratore (store E directory)

| # | Email | Trigger | Funzione |
|---|---|---|---|
| 1 | Ordine ricevuto | submit checkout (request/approval; direct: dal webhook) | `order_email_service.notify_customer_order_received` |
| 2 | Ordine confermato (+ piano pagamenti caparra/saldo, + blocco prenotazioni) | conferma operatore / pagamento riuscito | `notify_customer_order_confirmed` |
| 3 | Ordine annullato | annullo operatore | `notify_customer_order_cancelled` |
| 4 | Aggiornamento spedizione/ritiro | cambio fulfillment | `notify_customer_fulfillment_update` |
| 5 | Promemoria pagamento T-7 / T-0 | scheduler dunning | `payment_email_service.send_payment_reminder` |
| 6 | Sollecito pagamento in ritardo | scheduler dunning (overdue) | `send_payment_reminder` (fase sollecito) |
| 7 | Conferma prenotazione (rental/slot) | emissione/resend | `email_service.send_reservation_confirmation_email` |
| 8 | Biglietti individuali evento | ordine evento confermato | `event_email_service.send_individual_tickets_for_order` |
| 9 | Reinvio biglietto | richiesta pubblica per codice | `resend_ticket_email_by_code` |
| 10 | Broadcast partecipanti (promemoria/aggiornamento/follow-up) | invio manuale operatore | `broadcast_to_attendees` |
| 11 | Passaporto — accesso OTP + magic link | richiesta login / attivazione post-acquisto | `platform_account_service._send_magic_link_email` |
| 12 | Passaporto — claim «le tue prenotazioni in un posto solo» | primo pagamento riuscito (cooldown 24h) | `_send_claim_email` |

## Cliente store (account org-scoped, solo vetrina)

| # | Email | Trigger | Funzione |
|---|---|---|---|
| 13 | Benvenuto cliente | signup store | `send_customer_welcome` |
| 14 | Verifica email cliente | signup / reinvio | `send_customer_verification` |
| 15 | Reset password cliente | richiesta | `send_customer_password_reset` |
| 16 | Password cambiata | conferma | `send_customer_password_changed` |
| 17 | Account bloccato (lockout) | troppi tentativi | `send_account_lockout_alert` |

## Operatore (admin dell'organizzazione)

| # | Email | Trigger | Funzione |
|---|---|---|---|
| 18 | Nuovo ordine | ordine in arrivo | `notify_merchant_new_order` |
| 19 | Pagamento a rischio | dunning esaurito (T+7) | `payment_email_service.send_at_risk_to_operator` |
| 20 | Contestazione pagamento (dispute) | webhook Stripe | `critical_alert_service` (dispute) |
| 21 | Incasso ok ma conferma ordine fallita | reconciler | `critical_alert_service` (order-fail) |
| 22 | Store degradato (requisiti persi) | transizione readiness | `routers/store_settings._handle_status_transition` |
| 23 | Store di nuovo operativo | transizione readiness | idem (recovery) |
| 24 | Avviso quota piano | soglie consumo | `quota_email_service.notify_quota_warning_email` |
| 25 | Alert critici (batch) | scheduler alert (fascia B, spenta dai piani retreat) | `alert_notification_service.notify_high_severity_batch` |
| 26 | Riepilogo settimanale alert | scheduler (fascia B) | `send_weekly_alert_digest` |
| 27 | Report periodico (settimanale/mensile) | scheduler (fascia B) | `send_digest_report_email` |

## Auth operatore & piattaforma

| # | Email | Trigger | Funzione |
|---|---|---|---|
| 28 | Reset password | richiesta | `send_password_reset` |
| 29 | Benvenuto + verifica email | registrazione | `send_welcome` |
| 30 | Verifica email (reinvio) | richiesta | `send_verification` |
| 31 | Password cambiata | conferma | `send_password_changed` |
| 32 | Invito nel team | invito admin | `send_team_invite` |
| 33 | Invito piattaforma | invito operatore | `send_platform_invite` |
| 34 | Richiesta di accesso (notifica interna) | form /inizia | `send_invite_request_notification` |
| 35 | Candidatura ricevuta (conferma al richiedente) | form /inizia | `send_invite_request_confirmation` |
| 36 | Preavviso disattivazione account | GDPR/inattività | `send_deactivation_notice` |
| 37 | Ultimo avviso cancellazione | GDPR | `send_final_delete_warning` |
| 38 | Export dati / allegati | richiesta GDPR | `send_email_with_attachment` |
| 39 | Catalog drift digest (interna piattaforma) | scheduler QA | `background_service` |

## Email mancanti (valutate, non ancora costruite)

- **Conferma rimborso al cliente** — oggi il rimborso vive nel flusso
  Stripe (ricevuta Stripe) e nello stato ordine; un'email esplicita
  «ti abbiamo rimborsato X» aumenterebbe la fiducia. → candidata post-lancio.
- **Benvenuto Passaporto post-claim** — dopo il primo login il
  viaggiatore non riceve nulla; la claim email di fatto copre il caso.
  → solo se le metriche mostrano attivazioni che si perdono.

## Verifica di resa (R6)

L'invio è dry-run senza `BREVO_API_KEY`. Prima del lancio: 5 campioni
reali via Brevo (Gmail, Apple Mail, Outlook) — ordine confermato con
piano pagamenti, OTP Passaporto, biglietto evento, promemoria T-7,
nuovo ordine operatore.
