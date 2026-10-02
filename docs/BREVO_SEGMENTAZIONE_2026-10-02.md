# Segmentare il Cerchio in Brevo

*2 ottobre 2026. Il nostro database è la fonte di verità; Brevo è il braccio d'invio. La sync (`services/subscriber_brevo_sync.py`) scrive su ogni contatto gli attributi qui sotto a ogni iscrizione, conferma, cambio di preferenze, disiscrizione. Scoperta del 2/10: fino a oggi in Brevo non esisteva nessun attributo `AURYA_*` e i valori venivano scartati in silenzio. Da oggi esistono e sono riallineati per tutti gli iscritti (`scripts/brevo_segmentazione.py`).*

## La regola d'oro

**Ogni campagna si manda al segmento `AURYA_INVIABILE = true`.** È vero solo per chi è confermato e ha il consenso registrato: la stessa regola con cui il Cerchio scrive. Chi è in attesa del clic sta in Brevo (così la conferma lo trova già pronto) ma con `AURYA_INVIABILE = false`. I disiscritti sono in blacklist: Brevo non gli manda nulla, qualunque segmento.

## Gli attributi

| Attributo | Tipo | Valori | A cosa serve |
|---|---|---|---|
| `NOME` | testo | il nome, se dato | «Ciao {{ contact.NOME }}» |
| `AURYA_INVIABILE` | booleano | true / false | **la base di ogni segmento** |
| `AURYA_STATUS` | testo | pending · confirmed · unsubscribed · deleted | diagnostica |
| `AURYA_INTERESTS` | testo | csv delle vie: yoga, meditazione, breathwork, suono, reiki, costellazioni, astrologia, ayurveda, tantra, detox, cammini, femminile, crescita, misto | **le vie**: «contiene yoga» |
| `AURYA_ETA` | testo | 18-29 · 30-44 · 45-59 · 60+ | fascia d'età |
| `AURYA_CITY` | testo | città dichiarata | geografia fine |
| `AURYA_TRAVEL` | testo | near · italy · anywhere · abroad | quanto lontano |
| `AURYA_BUDGET` | testo | under500 · 500to1000 · over1000 · flexible | prezzo |
| `AURYA_ALERT` | testo | off · italy · csv regioni | avviso ritiri e dove |
| `AURYA_TOPICS` | testo | csv temi Magazine | contenuti |
| `AURYA_FORMAT` | testo | all · practices | formato Lettera |
| `AURYA_CANALE` | testo | sito · sound · magazine · account · social… | da dove è entrato |
| `AURYA_SUPERFICIE` | testo | cerca-ritiro · cancello · signup-pro · newsletter… | la pagina precisa |
| `AURYA_PORTA` | testo | meditazioni · altro | ha chiesto i ritiri o solo le meditazioni |
| `AURYA_SOURCE` | testo | fonte grezza | diagnostica |
| `AURYA_LANG` | testo | it · en · de · fr | lingua |
| `AURYA_ISCRITTO_IL` | data | YYYY-MM-DD | «iscritti negli ultimi 30 giorni» |
| `AURYA_CONFERMATO_IL` | data | YYYY-MM-DD (assente finché pending) | anzianità nel Cerchio |
| `AURYA_VERIFICATO` | booleano | true / false | indirizzo provato |
| `AURYA_CONSENSO_VERSIONE` | testo | cerchio-v1, v3… | quale casella ha accettato |

## Segmenti consigliati (da creare in Brevo → Contatti → Segmenti)

| Segmento | Condizioni |
|---|---|
| Cerchio inviabile | `AURYA_INVIABILE` = true |
| Vogliono i ritiri | inviabile + `AURYA_ALERT` ≠ off |
| Yoga | inviabile + `AURYA_INTERESTS` contiene `yoga` (idem per ogni via) |
| Suono e respiro | inviabile + (`AURYA_INTERESTS` contiene `suono` o contiene `breathwork`) |
| Puglia | inviabile + `AURYA_ALERT` contiene `puglia` |
| Vicino a casa | inviabile + `AURYA_TRAVEL` = near + `AURYA_CITY` non vuota |
| Budget alto | inviabile + `AURYA_BUDGET` = over1000 |
| 45 e oltre | inviabile + `AURYA_ETA` in (45-59, 60+) |
| Nuovi del mese | inviabile + `AURYA_ISCRITTO_IL` dopo [data] |
| Dalla pagina sponsorizzata | inviabile + `AURYA_SUPERFICIE` = cerca-ritiro |
| Solo meditazioni (mai chiesto dei ritiri) | inviabile + `AURYA_PORTA` = meditazioni |

## Gli operatori (OP1-OP3, 2/10 sera)

**Un contatto solo per email.** Un operatore che è anche nel Cerchio è lo stesso contatto, con le due facce. Nessuna lista separata: la distinzione la fanno tre attributi.

| Attributo | Valori | A cosa serve |
|---|---|---|
| `AURYA_TIPO` | cerchio · operatore · operatore+cerchio | chi è, a colpo d'occhio |
| `AURYA_INVIABILE` | true/false | **il Cerchio**: solo confermati col consenso |
| `AURYA_OP_COMUNICAZIONI` | true/false | **gli operatori**: cliente attivo che non si è opposto |

Gli altri attributi `AURYA_OP_*`: stato (account · bozza · online), attività, pagina, in directory, discipline (csv), regione e città, piano, listino pubblicato, Stripe collegato, Sound, registrato il, ultimo accesso, email verificata.

**Base legale (informativa 1-bis, Termini 19.4, v2.10):** l'operatore è cliente, riceve comunicazioni di servizio e aggiornamenti sulla Piattaforma per contratto e legittimo interesse; nessuna casella di consenso. Quindi **mai promozioni di terzi** a questo pubblico, e in ogni invio il link per opporsi (quello standard di Brevo basta). Chi clicca «disiscriviti» finisce in blacklist Brevo e il webhook scrive `comunicazioni_opposizione_at` sull'account: la sync spegne `AURYA_OP_COMUNICAZIONI`. Le email transazionali e di servizio dal backend continuano.

**Segmenti per gli operatori**

| Segmento | Condizioni |
|---|---|
| Tutti gli operatori raggiungibili | `AURYA_OP_COMUNICAZIONI` = true |
| Pagina online senza listino | raggiungibili + `AURYA_OP_STATO` = online + `AURYA_OP_LISTINO` = false |
| Registrati, mai andati online | raggiungibili + `AURYA_OP_STATO` ≠ online |
| Mai entrati | raggiungibili + `AURYA_OP_ULTIMO_ACCESSO` vuoto |
| Puglia, Reiki | raggiungibili + `AURYA_OP_REGIONE` = puglia + `AURYA_OP_DISCIPLINE` contiene reiki |
| Pro | raggiungibili + `AURYA_OP_PIANO` = pro |
| Operatori che sono anche nel Cerchio | `AURYA_TIPO` = operatore+cerchio |
| Cerchio senza operatori | `AURYA_INVIABILE` = true + `AURYA_TIPO` = cerchio |

**Quando si allinea:** al salvataggio del profilo, una volta al giorno per tutti (job `brevo_operatori`), e a mano con `python scripts/brevo_segmentazione.py --operatori`.

## Manutenzione

- Un attributo nuovo: si aggiunge a `ATTRIBUTI_BREVO` e a `_attributes()` (la guardia `test_brevo_segmentazione.py` pretende la parità), poi dal container `python scripts/brevo_segmentazione.py --attributi --backfill --verifica`.
- Lo script parla solo con l'API contatti: non può mandare email. Nessuna lista viene toccata (`BREVO_LIST_ID` resta spento in prod).
- Dal Mac l'API Brevo risponde 401 (IP non autorizzato, specie in IPv6): i gesti si fanno dal container del backend, che esce con l'IP autorizzato.
