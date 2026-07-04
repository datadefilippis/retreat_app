/**
 * @afianco/embed-sdk — Italian (base) translations.
 *
 * Track E Step 4.5 — Fase A: stringhe piu' visibili dei componenti core
 * (checkout, cart, header, account, profile). Estrazione completa di
 * tutti i 28+ componenti rinviata a fase B (extraction massiva).
 *
 * Convention key naming: snake_case section.action_or_label
 * (es. "checkout.submit", "cart.empty_state")
 */

export const it: Record<string, string> = {
  // ── Common ───────────────────────────────────────────────────────
  'common.loading': 'Caricamento…',
  'common.error': 'Errore',
  'common.save': 'Salva',
  'common.cancel': 'Annulla',
  'common.confirm': 'Conferma',
  'common.close': 'Chiudi',
  'common.required': 'Obbligatorio',
  'common.optional': 'Opzionale',
  'common.email': 'Email',
  'common.phone': 'Telefono',
  'common.name': 'Nome',
  'common.password': 'Password',

  // ── Header ───────────────────────────────────────────────────────
  'header.account_login': 'Accedi',
  'header.account_logged': 'Account',
  'header.cart': 'Carrello',
  'header.cart_empty_aria': 'Carrello vuoto',

  // ── Cart drawer ──────────────────────────────────────────────────
  'cart.title': 'Il tuo carrello',
  'cart.empty': 'Il carrello è vuoto.',
  'cart.subtotal': 'Subtotale',
  'cart.total': 'Totale',
  'cart.proceed_checkout': 'Procedi al checkout',
  'cart.remove': 'Rimuovi',
  'cart.qty_decrease': 'Diminuisci quantità',
  'cart.qty_increase': 'Aumenta quantità',
  'cart.item_count_singular': '{{count}} articolo',
  'cart.item_count_plural': '{{count}} articoli',

  // ── Account drawer ───────────────────────────────────────────────
  'account.title': 'Area Personale',
  'account.tab_login': 'Accedi',
  'account.tab_signup': 'Registrati',
  'account.welcome': 'Bentornato',
  'account.no_account_question': 'Non hai un account?',
  'account.signup_cta': 'Registrati',
  'account.have_account_question': 'Hai già un account?',
  'account.login_cta': 'Accedi',

  // ── Login form ───────────────────────────────────────────────────
  'login.title': 'Accedi al tuo account',
  'login.email_label': 'Email',
  'login.password_label': 'Password',
  'login.submit': 'Accedi',
  'login.forgot_password': 'Password dimenticata?',
  'login.error_invalid': 'Email o password non corretti',

  // ── Signup form ──────────────────────────────────────────────────
  'signup.title': 'Crea un account',
  'signup.name_label': 'Nome',
  'signup.email_label': 'Email',
  'signup.password_label': 'Password (min 8 caratteri)',
  'signup.phone_label': 'Telefono (opzionale)',
  'signup.privacy_label': 'Accetto la Privacy Policy*',
  'signup.terms_label': 'Accetto i Termini di Servizio*',
  'signup.marketing_label': 'Voglio ricevere email promozionali (opzionale)',
  // Track E Step 7.4 — Linked GDPR labels (3-part: prefix + <a>link</a> + suffix)
  'signup.gdpr_privacy_prefix': 'Accetto la',
  'signup.gdpr_privacy_link': 'Privacy Policy',
  'signup.gdpr_terms_prefix': 'Accetto i',
  'signup.gdpr_terms_link': 'Termini di Servizio',
  'signup.submit': 'Crea account',
  'signup.check_email': 'Controlla la tua email per verificare l\'account.',

  // ── Checkout modal ───────────────────────────────────────────────
  'checkout.title': 'Completa l\'ordine',
  'checkout.section_data': 'I tuoi dati',
  'checkout.section_attendees': 'Dati partecipanti',
  'checkout.section_additional': 'Informazioni aggiuntive',
  'checkout.section_fulfillment': 'Come vuoi ricevere il tuo ordine?',
  'checkout.section_shipping_option': 'Scegli un\'opzione di spedizione',
  'checkout.section_shipping_address': 'Indirizzo di spedizione',
  'checkout.section_coupon': 'Codice promo',
  'checkout.section_consent': 'Consenso',
  'checkout.name_required': 'Nome*',
  'checkout.email_required': 'Email*',
  'checkout.phone_optional': 'Telefono (opzionale)',
  'checkout.gdpr_privacy': 'Accetto la Privacy Policy del merchant*',
  'checkout.gdpr_terms': 'Accetto i Termini di Servizio*',
  'checkout.gdpr_marketing': 'Voglio ricevere email promozionali (opzionale)',
  // Track E Step 7.4 — Linked GDPR labels (3-part: prefix + <a>link</a> + suffix)
  'checkout.gdpr_privacy_prefix': 'Accetto la',
  'checkout.gdpr_privacy_link': 'Privacy Policy del merchant',
  'checkout.gdpr_terms_prefix': 'Accetto i',
  'checkout.gdpr_terms_link': 'Termini di Servizio',
  'checkout.create_account_checkbox': 'Crea un account per tracciare il mio ordine',
  'checkout.account_password_label': 'Password account (min 8 caratteri)',
  'checkout.submit': 'Procedi al pagamento',
  'checkout.submitting': 'Elaborazione…',
  'checkout.loading_fields': 'Caricamento campi…',
  'checkout.error_name_empty': 'Inserisci il tuo nome.',
  'checkout.error_email_invalid': 'Email non valida.',
  'checkout.error_gdpr_missing': 'Devi accettare Privacy + Termini per procedere.',
  'checkout.error_password_short': 'Password account: minimo 8 caratteri.',
  'checkout.error_field_required': 'Compila il campo "{{label}}" per procedere.',
  'checkout.error_shipping_address': 'Compila tutti i campi indirizzo spedizione.',
  'checkout.error_postal_it': 'CAP italiano: deve essere 5 cifre.',
  'checkout.error_shipping_option': 'Seleziona un\'opzione di spedizione.',

  // ── Coupon ───────────────────────────────────────────────────────
  'coupon.title': 'Codice promo',
  'coupon.placeholder': 'Inserisci codice',
  'coupon.apply': 'Applica',
  'coupon.remove': 'Rimuovi',
  'coupon.applied': 'Codice {{code}} applicato — sconto {{amount}}',
  'coupon.empty_input': 'Inserisci un codice promo.',
  'coupon.invalid': 'Codice promo non valido',

  // ── Shipping address ─────────────────────────────────────────────
  'shipping.recipient_label': 'Destinatario (opzionale)',
  'shipping.recipient_placeholder': 'Lascia vuoto per usare il tuo nome',
  'shipping.line1_label': 'Via*',
  'shipping.civic_label': 'N. civico',
  'shipping.postal_label': 'CAP*',
  'shipping.city_label': 'Città*',
  'shipping.province_label': 'Provincia',
  'shipping.country_label': 'Paese*',

  // ── Fulfillment modes ────────────────────────────────────────────
  'fulfillment.shipping': 'Spedizione',
  'fulfillment.shipping_desc': 'Ricevi a casa con corriere',
  'fulfillment.local_pickup': 'Ritiro in negozio',
  'fulfillment.local_pickup_desc': 'Vieni a ritirare in negozio',
  'fulfillment.pickup_at_store': 'Ritiro presso punto',
  'fulfillment.pickup_at_store_desc': 'Ritira in un punto convenzionato',

  // ── Profile editor ───────────────────────────────────────────────
  'profile.section_profile': 'Modifica profilo',
  'profile.section_password': 'Cambia password',
  'profile.section_erasure': 'Cancellazione dati (GDPR Art.17)',
  'profile.email_verified': 'Verificata',
  'profile.name_label': 'Nome*',
  'profile.phone_label': 'Telefono',
  'profile.locale_label': 'Lingua',
  'profile.save': 'Salva modifiche',
  'profile.saving': 'Salvataggio…',
  'profile.success_updated': 'Profilo aggiornato con successo.',
  'profile.error_name_empty': 'Il nome non può essere vuoto.',
  'password.current_label': 'Password attuale*',
  'password.new_label': 'Nuova password* (min 8 caratteri)',
  'password.confirm_label': 'Conferma nuova password*',
  'password.submit': 'Cambia password',
  'password.success': 'Password aggiornata con successo.',
  'password.error_min_length': 'La nuova password deve avere almeno 8 caratteri.',
  'password.error_mismatch': 'Le due password non corrispondono.',
  'erasure.warning': 'La cancellazione è irreversibile. Tutti i tuoi dati verranno rimossi entro 30 giorni in conformità con l\'Art.17 GDPR.',
  'erasure.reason_label': 'Motivo (opzionale)',
  'erasure.reason_placeholder': 'Aiutaci a capire perché vuoi cancellare l\'account',
  'erasure.confirm_label': 'Confermo di voler richiedere la cancellazione del mio account e di tutti i dati associati.',
  'erasure.submit': 'Richiedi cancellazione',
  'erasure.submitting': 'Invio in corso…',
  'erasure.confirm_required': 'Devi confermare per procedere.',

  // ── My courses ────────────────────────────────────────────────────
  'courses.empty_title': 'Nessun corso acquistato',
  'courses.empty_desc': 'I videocorsi che acquisterai compariranno qui.',
  'courses.lessons_label': 'Lezioni',
  'courses.duration_label': 'Durata',
  'courses.progress_label': 'Progresso',
  'courses.completed_badge': '✓ Completato',
  'courses.back_to_list': '← Torna ai miei corsi',
  'courses.select_lesson_hint': 'Seleziona una lezione per iniziare',
  'courses.player_loading': 'Caricamento video…',
  'courses.progress_save_hint': 'Il progresso viene salvato automaticamente. Puoi riprendere la lezione da dove l\'hai lasciata.',

  // ── My downloads ─────────────────────────────────────────────────
  'downloads.empty_title': 'Nessun download disponibile',
  'downloads.empty_desc': 'I file digitali acquistati compariranno qui.',
  'downloads.status_issued': 'Disponibile',
  'downloads.status_downloaded': 'Scaricato',
  'downloads.status_expired': 'Scaduto',
  'downloads.action_download': 'Scarica',
  'downloads.action_exhausted': 'Esaurito',

  // ── My bookings ──────────────────────────────────────────────────
  'bookings.empty_title': 'Nessuna prenotazione',
  'bookings.empty_desc': 'Le tue prenotazioni servizi e noleggi compariranno qui.',
  'bookings.type_service': 'Servizio',
  'bookings.type_rental': 'Noleggio',
  'bookings.status_confirmed': 'Confermato',
  'bookings.status_pending': 'In attesa',
  'bookings.status_cancelled': 'Cancellato',

  // ── Portal tabs ──────────────────────────────────────────────────
  'portal.tab_profile': 'Profilo',
  'portal.tab_orders': 'Ordini',
  'portal.tab_courses': 'I miei corsi',
  'portal.tab_downloads': 'Download',
  'portal.tab_bookings': 'Prenotazioni',
  'portal.logout': 'Esci',
  'portal.auth_required_title': 'Accedi per vedere la tua area personale',
  'portal.auth_required_desc': 'Effettua il login per consultare profilo, ordini, corsi e prenotazioni.',

  // ── Sprint 4 W4.7 — Extensive i18n coverage (~70 nuove key per
  //    chiudere il gap hardcoded italiano nei flow critical) ────────
  // Checkout error/UX messages
  'checkout.error_storefront_not_ready': 'Storefront non pronto o carrello mancante.',
  'checkout.opening_payment': 'Apertura pagamento sicuro...',
  'checkout.payment_pending': 'Finestra di pagamento aperta. Completa il pagamento per proseguire…',
  'checkout.order_completed': 'Ordine completato. Grazie!',
  'checkout.popup_blocked': 'Impossibile aprire la finestra di pagamento. Disabilita il popup-blocker.',
  'checkout.error_generic': 'Errore durante il checkout.',
  'checkout.attendee_label': 'Partecipante {{n}}',
  'checkout.merchant_suffix': 'del merchant*',
  'checkout.notes_label': 'Note al merchant (opzionale)',
  'checkout.notes_placeholder': 'Es. orari di consegna preferiti, richieste speciali…',
  'checkout.close_label': 'Chiudi',
  'checkout.recipient_placeholder': 'Lascia vuoto per usare il tuo nome',
  'checkout.address_line_placeholder': 'es. Via Roma',
  'checkout.civic_placeholder': '12B',
  'checkout.postal_placeholder': '20100',
  'checkout.city_placeholder': 'Milano',
  'checkout.province_placeholder': 'MI',

  // Cart
  'cart.error_storefront_not_ready': 'Storefront non ancora pronto.',
  'cart.error_update': 'Errore aggiornamento carrello.',
  'cart.open_label': 'Apri carrello',
  'cart.trigger_label': '🛒 Carrello',
  'cart.items_aria_label': '{{count}} elementi',
  'cart.close_label': 'Chiudi carrello',

  // Login extra
  'login.error_storefront_not_ready': 'Storefront non pronto.',
  'login.error_email_invalid': 'Email non valida.',
  'login.error_password_required': 'Password obbligatoria.',
  'login.error_credentials': 'Credenziali non valide o account non verificato.',
  'login.error_generic': 'Errore di login.',
  'login.welcome_message': 'Benvenuto, {{name}}! Sei connesso.',
  'login.account_locked_prefix': '🔒 Account temporaneamente bloccato. Riprova fra',
  'login.show_password': 'Mostra password',
  'login.hide_password': 'Nascondi password',
  'login.submitting': 'Accesso in corso…',
  'login.create_account_link': 'Crea un account',

  // Signup extra
  'signup.error_storefront_not_ready': 'Storefront non pronto.',
  'signup.error_name_required': 'Inserisci il tuo nome.',
  'signup.error_email_invalid': 'Email non valida.',
  'signup.error_password_min': 'La password deve avere almeno 8 caratteri.',
  'signup.error_gdpr_required': 'Devi accettare Privacy e Termini per registrarti.',
  'signup.error_generic': 'Errore di registrazione.',
  'signup.email_verification_message': 'Account creato! Controlla la tua casella email per attivarlo.',
  'signup.show_password': 'Mostra password',
  'signup.hide_password': 'Nascondi password',
  'signup.password_hint': 'Minimo 8 caratteri',
  'signup.submitting': 'Registrazione in corso…',
  'signup.login_prompt': 'Hai già un account?',
  'signup.login_link': 'Accedi',

  // Password strength levels (parity React computePasswordStrength)
  'password_strength.too_short': 'Troppo corta',
  'password_strength.weak': 'Debole',
  'password_strength.fair': 'Discreta',
  'password_strength.good': 'Buona',
  'password_strength.strong': 'Forte',

  // Account drawer
  'account.open_authenticated': 'Apri area utente',
  'account.open_guest': 'Accedi o registrati',
  'account.title_authenticated': 'Il tuo account',
  'account.title_signup': 'Crea account',
  'account.title_login': 'Accedi',
  'account.close_label': 'Chiudi',

  // Product detail
  'product.close_label': 'Chiudi dettaglio',
  'product.loading': 'Caricamento in corso…',
  'product.not_found': 'Nessun prodotto selezionato.',
  'product.out_of_stock': 'Esaurito',
  'product.limited_stock': 'Solo {{count}} disponibili',
  'product.no_image': 'Nessuna immagine',
  'product.price_inquiry': 'Prezzo su richiesta',
  'product.quantity_label': 'Quantità',
  'product.decrease_qty': 'Diminuisci quantità',
  'product.increase_qty': 'Aumenta quantità',
  'product.service_options_label': 'Scegli un\'opzione',

  // Fulfillment picker (component-level group label)
  'fulfillment.group_label': 'Come vuoi ricevere il tuo ordine?',
  'fulfillment.external_pickup_label': 'Ritiro presso punto',
  'fulfillment.external_pickup_desc': 'Ritira in un punto convenzionato',

  // Shipping
  'shipping.loading': 'Caricamento opzioni spedizione…',
  'shipping.free_threshold': 'Spedizione gratuita per ordini > {{amount}}',
  'shipping.group_label': 'Scegli un\'opzione di spedizione',

  // Extras/Tier component-level labels
  'extras.title': 'Aggiungi al tuo ordine',
  'tier.title': 'Tipo di biglietto',

  // Price preview
  'price.total': 'Totale',

  // Loading states (post-purchase / portal sub-pages)
  'course.loading': 'Caricamento corso…',
  'course.loading_list': 'Caricamento corsi…',
  'course.video_loading': 'Caricamento video…',
  'download.loading': 'Caricamento download…',
  'booking.loading': 'Caricamento prenotazioni…',
  'availability.loading': 'Caricamento disponibilità…',
  'profile.loading': 'Caricamento profilo…',

  // W4.8 — Residual hardcoded fix
  'product.cta_discover': 'Scopri di più',
  'product.cta_add_to_cart': 'Aggiungi al carrello',
  'product.cta_buy_ticket': 'Acquista biglietto',
  'product.cta_enroll_course': 'Iscriviti al corso',
  'product.cta_rent': 'Noleggia',
  'product.cta_buy': 'Acquista',
  'product.cta_request_quote': 'Richiedi preventivo',
  'product.cta_request_info': 'Richiedi info',
  'product.cta_request_rental': 'Richiedi noleggio',
  'product.cta_request': 'Richiedi',
  'price.summary_title': 'Riepilogo prezzo',
  'price.subtotal': 'Subtotale',
  'price.subtotal_with_days_one': 'Subtotale ({{count}} giorno)',
  'price.subtotal_with_days_other': 'Subtotale ({{count}} giorni)',

  // ── W4.9 — Final hardcoded sweep (60+ new keys) ───────────────────
  // Product (type badges + extras)
  'product.type_service': 'Servizio',
  'product.type_event': 'Evento',
  'product.type_rental': 'Noleggio',
  'product.type_course': 'Corso',
  'product.type_digital': 'Digitale',
  'product.type_physical': 'Prodotto',
  'product.detail_header_fallback': 'Dettaglio prodotto',
  'product.error_load': 'Errore nel caricamento del prodotto.',
  'product.error_storefront_not_ready': 'Storefront non ancora pronto. Riprova tra un istante.',
  'product.remaining_seats_one': 'Solo {{count}} posto rimasto',
  'product.remaining_seats_other': 'Solo {{count}} posti rimasti',
  'product.empty_catalog': 'Nessun prodotto disponibile.',

  // Occurrence picker (event)
  'occurrence.group_label': 'Scegli una data',
  'occurrence.empty': 'Nessuna data disponibile per questo evento.',
  'occurrence.sold_out': 'Esaurito',
  'occurrence.map_link': 'mappa',

  // Tier picker
  'tier.sold_out': 'Esaurito',
  'tier.qty_label': 'Quantità',
  'tier.decrease_aria': 'Diminuisci',
  'tier.increase_aria': 'Aumenta',
  'tier.limited_one': 'Solo {{count}} disponibile',
  'tier.limited_other': 'Solo {{count}} disponibili',

  // Service options
  'service.group_label': 'Scegli un\'opzione',
  'service.empty_options': 'Nessuna opzione configurata.',

  // Availability picker (service slots)
  'availability.error_load': 'Errore caricamento slot.',
  'availability.empty_n_days': 'Nessuno slot disponibile per i prossimi {{days}} giorni. Contatta il merchant per disponibilità su misura.',
  'availability.choose_date_time': 'Scegli data e orario',
  'availability.dates_available_aria': 'Date disponibili',
  'availability.times_aria': 'Orari disponibili',
  'availability.empty_day': 'Nessuno slot disponibile per questo giorno.',
  'availability.change_btn': 'Cambia',

  // Rental date-range picker
  'rental.group_label': 'Scegli le date del noleggio',
  'rental.error_invalid_date': 'Data non valida.',
  'rental.error_end_before_start': 'La data di fine deve essere uguale o successiva alla data di inizio.',
  'rental.error_min_days_one': 'Il noleggio richiede almeno {{count}} giorno.',
  'rental.error_min_days_other': 'Il noleggio richiede almeno {{count}} giorni.',
  'rental.error_max_days': 'Massimo {{count}} giorni per noleggio.',
  'rental.error_dates_unavailable': 'Alcune date selezionate non sono disponibili.',
  'rental.no_slot_hint': 'Nessuno slot fisso disponibile. Dopo l\'aggiunta al carrello, potrai indicare la data e l\'orario preferiti nel form di richiesta.',
  'rental.custom_request_hint': 'Configurazione orari noleggio specifici. Indica le tue preferenze nel form di richiesta dopo l\'aggiunta al carrello.',
  // R4 — richiesta personalizzata servizio (slot proposto fuori dalle regole)
  'custom_request.group_label': 'Proponi data e orario',
  'custom_request.hint': 'Nessuno slot fisso: proponi una preferenza (facoltativa). La richiesta sarà confermata dall\'operatore.',
  'custom_request.date_label': 'Data',
  'custom_request.start_label': 'Inizio',
  'custom_request.end_label': 'Fine',
  'custom_request.notes_label': 'Note (facoltative)',
  // F2 — modulo Newsletter
  'newsletter.loading': 'Caricamento…',
  'newsletter.email_label': 'Email',
  'newsletter.name_label': 'Nome',
  'newsletter.phone_label': 'Telefono',
  'newsletter.privacy_label': 'Accetto il trattamento dei dati per ricevere comunicazioni.',
  'newsletter.submit': 'Iscriviti',
  'newsletter.submitting': 'Invio…',
  'newsletter.success': 'Iscrizione completata. Grazie!',
  'newsletter.error_email': 'Inserisci un indirizzo email valido.',
  'newsletter.error_consent': 'Devi accettare per procedere.',
  'newsletter.error_required': 'Compila i campi obbligatori.',
  'newsletter.error_submit': 'Iscrizione non riuscita. Riprova.',
  'newsletter.error_load': 'Impossibile caricare il modulo.',
  'newsletter.privacy_link': 'Informativa privacy',
  'newsletter.error_misconfigured': 'Modulo non configurato correttamente.',

  // Course preview
  'course.preview_title': 'Cosa include il corso',
  'course.lessons_label_short': 'Lezioni',
  'course.duration_label_short': 'Durata',
  'course.access_expiry_days': 'Accesso {{count}} giorni dall\'acquisto',
  'course.access_lifetime': 'Accesso a vita',
  'course.access_unlimited': 'Accesso illimitato',
  'course.profile_access_hint': 'Dopo l\'acquisto, accedi al tuo profilo per riprodurre le lezioni dal tuo computer o smartphone.',
  'course.empty_lessons': 'Nessuna lezione disponibile.',
  'course.error_load': 'Errore caricamento corso.',
  'course.error_video': 'Errore caricamento video.',
  'course.error_load_list': 'Errore caricamento corsi.',
  'course.empty_purchased': 'Nessun corso acquistato',

  // Event empty hint
  'event.empty_occurrence_hint': 'Nessuna data al momento programmata per questo evento. Contatta il fornitore per disponibilità.',

  // Profile editor full coverage
  'profile.error_load': 'Errore caricamento profilo.',
  'profile.error_update': 'Errore aggiornamento profilo.',
  'profile.empty': 'Nessun profilo trovato.',
  'profile.section_title_edit': 'Modifica profilo',
  'profile.password_change_btn': 'Cambia password',
  'profile.password_section_title': 'Cambia password',
  'profile.password_min_label_full': 'Nuova password* (min 8 caratteri)',
  'profile.erasure_section_title': 'Cancellazione dati (GDPR Art.17)',
  'profile.erasure_submitting': 'Invio in corso…',
  'profile.erasure_submit': 'Richiedi cancellazione',
  'profile.erasure_confirm_label': 'Confermo di voler richiedere la cancellazione del mio account e di tutti i dati associati.',
  'profile.erasure_reason_label': 'Motivo (opzionale)',
  'profile.error_password_fill': 'Compila tutti i campi password.',
  'profile.error_password_min': 'La nuova password deve avere almeno 8 caratteri.',
  'profile.error_password_mismatch': 'Le due password non corrispondono.',
  'profile.error_confirm_required': 'Devi confermare per procedere.',
  'profile.error_password_change': 'Errore cambio password.',
  'profile.error_erasure_request': 'Errore invio richiesta.',
  'profile.phone_label_full': 'Telefono',
  'profile.locale_italian': 'Italiano',

  // Downloads
  'download.empty': 'Nessun download disponibile',
  'download.purchased_at': 'Acquistato {{date}}',
  'download.expires_at': 'Scade {{date}}',
  'download.expired_badge': 'Scaduto',
  'download.exhausted_badge': 'Esaurito',
  'download.action_download': 'Scarica',
  'download.error_load': 'Errore caricamento download.',

  // Bookings
  'booking.error_load': 'Errore caricamento prenotazioni.',
  'booking.status_confirmed': 'Confermato',
  'booking.empty': 'Nessuna prenotazione',
  'booking.error_cancel': 'Errore cancellazione.',

  // Shipping (extra)
  'shipping.error_load': 'Errore caricamento opzioni spedizione.',
  'shipping.empty': 'Nessuna opzione di spedizione configurata.',

  // Price preview (extra)
  'price.error_calc': 'Errore calcolo prezzo',

  // Account drawer forgot password
  'account.forgot_password_success': 'Se l\'email è registrata, riceverai un link per reimpostare la password.',
  'account.forgot_password_error': 'Errore invio richiesta.',

  // Customer portal extras
  'portal.error_load_profile': 'Errore nel caricamento del profilo.',
  'portal.error_load_orders': 'Errore nel caricamento degli ordini.',
  'portal.empty_profile': 'Nessun profilo disponibile.',

  // Signup verification message
  'signup.verification_message_full': 'Account creato! Controlla la tua casella {{email}} per verificare l\'email prima di accedere.',

  // Login dispatch error fallback
  'login.dispatch_error': 'Errore login',
};
