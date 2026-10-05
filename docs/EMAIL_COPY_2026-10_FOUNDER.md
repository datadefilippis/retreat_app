# Le email automatiche: la versione del founder (5/10/2026 sera)

Il founder ha riletto `EMAIL_COPY_2026-10.md` e ha restituito la sua versione di tutte le 47 email (incollata in chat il 5/10/2026 sera). È la fonte di verità applicata nel codice con il lotto FL3: trigger, link, token e tempi sono rimasti quelli di prima; sono cambiate le parole.

Regole comuni dettate dal founder:
- prima persona plurale quando parliamo come Aurya;
- niente linguaggio da e-commerce o da software («con successo», «store», «pack», «upgrade», «regolarizzare»);
- niente formule impersonali o burocratiche;
- un'azione principale per email e un pulsante chiaro;
- il passo successivo deve essere comprensibile anche leggendo solo il testo;
- date e orari sempre in italiano;
- quando una risposta all'email è prevista, il testo lo dice;
- piè di pagina unico: «Aurya · Ritiri ed esperienze olistiche, in un posto solo · aurya.life»;
- mai declinare al maschile o al femminile («ti interessano», non «interessato»).

## Dove vive ogni testo nel codice

| N. | Email | Dove |
|---|---|---|
| 1, 3 | conferma doppio opt-in, «Riapro il mio accesso» | `routers/subscribers.py` `_send_confirm_email`, `_send_access_email` |
| 2a/2b | promemoria 48 ore | `services/cerchio_reminder.py` `_testo_promemoria` |
| 4, 5, 6 | Sei nel Cerchio (ritiri / meditazioni / altro) | `services/email_sequenze.py` `benvenuto_cerchio_*` |
| 7-10 | account Aurya (verifica, accesso, password, prenotazioni) | dizionario `EMAIL_TRANSLATIONS["it"]` in `services/email_service.py` + `services/platform_account_service.py` |
| 11-15 | account cliente di un negozio, accesso fermato | dizionario `customer_*`, `lockout_*` |
| 16 | giorno zero del professionista | `email_sequenze.benvenuto_operatore` |
| 17a/17b | pagina online, canali della rete (passo nuovo `canali`) | `email_sequenze.op_profilo_online`, `op_canali` + `services/sequenze.py` PASSI |
| 18-21 | sequenza giorni 5/10/15/14 | `email_sequenze.op_np5`, `op_np10`, `op_np15`, `op_r14` |
| 22-24, 27-29 | verifica, password, inviti, disattivazione | dizionario `verify_*`, `reset_*`, `changed_*`, `platform_invite_*`, `deactivation_*`, `final_delete_*` |
| 25 | invito nel team (link di prima password, mai la password in chiaro) | `email_service.send_team_invite` + `routers/organizations.py` |
| 26 | candidatura ricevuta | dizionario `invite_request_confirm_*` |
| 30, 31 | pagina in difficoltà, limiti di piano | dizionario `store_alert_*`, `quota_*` + `services/quota_email_service.py` |
| 32, 33, 45-47 | recensioni | `services/review_service.py` |
| 34, 35 | richieste (struttura, regia, aziende, servizi Pro) e stati | `services/strutture_email.py` |
| 36, 41 | pagamento a rischio, promemoria | dizionario `pay_*` + `services/payment_email_service.py` |
| 37-40 | richiesta ricevuta, ordine confermato, annullato, consegna | dizionario `order_*`, `fulfillment_*` + `services/order_email_service.py` |
| 42 | prenotazione confermata (date in italiano) | dizionario `reservation_*` + `email_service._reservation_block_html` |
| 43, 44 | biglietto, comunicazioni ai partecipanti | dizionario `event_email_*` + `services/event_email_service.py` |

## Scostamenti dichiarati
- **33b «Hai una risposta alla tua recensione»** (al recensore quando il professionista risponde) **non si può mandare**: per scelta del founder (RV6) l'email di chi recensisce non viene conservata in chiaro, quindi non c'è a chi scriverla. Al suo posto resta l'email al professionista «Abbiamo tolto la recensione che avevi segnalato» (33b originale), nel tono nuovo.
- **38 «Apri il mio ordine»**: il pulsante porta all'area account (l'hub con gli ordini), perché la pagina del singolo ordine oggi reindirizza lì; i dettagli (biglietti, prenotazioni, download) hanno i loro link nella stessa email.
- **39**: chi ha annullato non è registrato sull'ordine, quindi la frase dice «è stato annullato»; la riga sul rimborso c'è (pagato → «il rimborso parte da {operatore}»; non pagato → «niente da restituire»).
- **44a/44b**: i cinque modelli di comunicazione ai partecipanti restano (promemoria, informazioni, annullamento, grazie, personalizzata) con i testi del founder; «Ciao partecipante,» è diventato «Ciao,».
- Il **giorno zero** (16) tiene una riga che dice che il clic conferma l'email e porta dentro: senza, chi legge non sa perché cliccare.
