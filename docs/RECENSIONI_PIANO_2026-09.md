# Recensioni: com'è oggi e piano (ciclo RV, 5/9/2026)

Domande del founder: come funziona il rilascio delle recensioni,
chiunque può, differenza fra chi ha ordinato e chi no, entrambe sul
profilo pubblico, dov'è la pagina dell'operatore per leggerle e
rispondere. Analisi sul codice (`services/review_service.py`,
`routers/reviews.py`, `OperatorProfilePage.js`, `ReviewsAdminPage.js`,
`components/Layout.js`) e lettura in sola lettura di prod.

## Com'è oggi (ciclo PR2/PR3, luglio 2026)

**Chi può scrivere.** Chiunque apre il modulo «Scrivi una recensione»
sul profilo pubblico, ma per pubblicare deve dimostrare di possedere
un'email: codice a 6 cifre via email (hash a DB, 15 minuti, 5
tentativi, si brucia solo a recensione accettata). Il modulo dice
«usa l'email con cui hai prenotato».

**Verificata o no.** Al momento dell'invio il sistema controlla se
quell'email ha almeno un ordine non bozza e non annullato con quel
professionista (CRM clienti dell'organizzazione).
- Ha ordinato → recensione **verificata**, pubblicata subito, badge
  «Cliente verificato» sul profilo; l'operatore NON può rimuoverla né
  approvarla (credibilità del marketplace), può solo rispondere o
  segnalarla come abuso.
- Non ha ordinato → dipende dall'interruttore `reviews_open`
  dell'organizzazione (spento di default). Spento: rifiuto con
  messaggio «accetta recensioni solo da chi ha già prenotato». Acceso:
  la recensione nasce **in attesa**, l'operatore la approva o la
  rifiuta, e non avrà mai il badge.
- Una recensione per email per professionista: la nuova sostituisce la
  vecchia (segnata «aggiornata», risposta azzerata). L'email non è mai
  in chiaro sul documento.

**Sul profilo pubblico.** Compaiono solo le `published`: verificate e
non verificate approvate, con badge diverso; media e conteggio
denormalizzati sull'organizzazione; risposta del professionista sotto
la recensione.

**La pagina dell'operatore esiste**: `/reviews` (plancia con media,
distribuzione, tab Pubblicate / In attesa / Segnalate, risposta
inline, approva/rifiuta le non verificate, segnala abuso, interruttore
«accetta anche da chi non ha prenotato»). Ma **non è nel menu del
mondo snello**: la voce «Recensioni» vive solo nel menu legacy
(`legacy_commerce`), insieme a Store, Incassi, Visibilità. Nel mondo
snello (quello di tutti gli operatori oggi) ci si arriva solo dal
riquadro «Da fare» della home, e solo quando c'è una recensione in
attesa. È per questo che nel gestionale sembra non esserci.

**Altri buchi trovati.**
- Nessuna email all'operatore quando arriva una recensione (esiste
  solo l'email del codice a chi scrive).
- Chi non ha prenotato riceve il codice e viene rifiutato DOPO averlo
  inserito: la porta si chiude tardi.
- «Segnala abuso» toglie la recensione dal pubblico e scrive un log:
  nessuna coda per il system admin, nessuno la rilegge.
- Nessun invito a recensire dopo l'esperienza: le verificate arrivano
  solo se il cliente torna da solo sul profilo.
- Non si può avvisare chi ha scritto quando il professionista risponde
  (l'email è solo hash: scelta di privacy voluta).

**In prod oggi** (sola lettura): 2 recensioni, entrambe verificate e
pubblicate; nessuna organizzazione ha aperto le recensioni ai non
clienti.

## Piano proposto (ciclo RV)

**RV1. Recensioni nel gestionale snello.** Voce «Recensioni» nel menu
del mondo snello (dopo Profilo pubblico) con il conteggio delle
recensioni in attesa; tile «Recensioni» nella home operatore (media,
numero, in attesa) accanto agli altri numeri; link dalla pagina
Profilo pubblico. La plancia `/reviews` resta quella, si rifinisce
il copy nel lessico Aurya (professionista, non operatore). Zero
backend.

**RV2. L'operatore lo viene a sapere.** Email al professionista a ogni
recensione: verificata → «Nuova recensione pubblicata, rispondi»;
non verificata → «Una recensione aspetta la tua approvazione». Una
email per recensione, link diretto alla plancia, rispetta il gate
email esistente. Backend piccolo (hook in `submit_review`).

**RV3. La porta si chiude prima, e con onestà.** Il profilo pubblico
espone `reviews_open`: se chiuso, il modulo dice subito «le recensioni
qui sono riservate a chi ha prenotato: usa l'email della prenotazione»
prima di mandare il codice; se aperto, avvisa che la recensione senza
prenotazione sarà pubblicata dopo l'approvazione e senza badge. Il
codice parte comunque solo a email inserita.

**RV4. Invito a recensire dopo l'esperienza.** Il giorno dopo la fine
di un servizio, evento o ritiro con ordine pagato, un'email al cliente
«Com'è andata con X?» con link al profilo e il modulo già sul passo
del codice. Una sola email per ordine, mai per ordini annullati,
disattivabile dal professionista nelle impostazioni. È la leva vera
per le recensioni verificate. Backend: job nel background service
(stesso pattern del promemoria del Cerchio), campo `review_invite_sent_at`
sull'ordine.

**RV5. Coda delle segnalazioni per il system admin.** Tab
«Recensioni segnalate» nel pannello di sistema: rilegge, ripubblica o
rimuove, con nota. Oggi una segnalazione è un log e basta.

**RV6 (opzionale, da decidere).** Avvisare chi ha scritto quando il
professionista risponde: servirebbe conservare l'email cifrata con un
consenso esplicito nel modulo. Cambia la promessa di privacy: solo se
il founder lo vuole.

## Stato (5/9/2026, sera)

Decisione del founder: «se l'operatore ha disabilitato le recensioni da
chi non ha ordinato, chi non ha ordinato non deve nemmeno ricevere
l'email». Fatti:
- **RV1**: voce «Recensioni» nel menu del mondo snello dopo Profilo
  pubblico (verificato nel gestionale demo).
- **RV2**: email al professionista a ogni recensione (verificata →
  «rispondi», non verificata → «aspetta la tua approvazione» con link
  alla coda), destinatario come le email di quota (notification_email
  dello store, poi il primo admin attivo). Best-effort.
- **RV3**: la porta si chiude prima del codice: org riservata ai
  clienti + email senza prenotazioni = niente codice, una riga di
  cortesia con la cura; il profilo pubblico lo dice prima di chiedere
  l'email (copy diverso se le recensioni sono aperte). Risposta HTTP
  sempre 202: nulla trapela.
- **RV5** (secondo giro, stessa sera): segnalare porta un motivo
  (facoltativo, lo legge Aurya); la recensione esce dal pubblico e va
  nella coda del system admin (`/admin?tab=reviews`, endpoint
  `/admin/reviews/flagged` e `/admin/reviews/{id}/resolve`), la
  piattaforma riceve un'email; la decisione («ripubblica» o «rimuovi»)
  torna al professionista via email e la card nella sua tab Segnalate
  dice «in revisione da Aurya, riceverai l'esito». Le decisioni restano
  a DB (`resolution`).
- **Chi scrive non si perde**: al momento dell'invio (l'unico in cui
  l'email è in chiaro) riceve una ricevuta: «è pubblica» oppure «in
  attesa dell'approvazione del professionista». Le tappe successive
  (approvazione, risposta) non lo raggiungono senza RV6.
- **Impostazioni leggibili**: la scelta «solo clienti / chiunque» è una
  card con la regola scritta e lo stato di oggi, non più una casella in
  un angolo.
- Collaudo end-to-end sulla demo (script nello scratchpad, 30 passi:
  porta chiusa, cliente verificato, codice bruciato una volta sola,
  testo corto che non brucia il codice, risposta, nuova versione,
  segnalazione, coda, ripubblica/rimuovi, org aperta con approva e
  rifiuta, richiusura). Guardie in `tests/test_recensioni_rv.py`.

### La matrice delle notifiche (chi sa cosa)
| evento | chi scrive | professionista | piattaforma |
|---|---|---|---|
| chiede il codice, non cliente, org chiusa | email di cortesia (no codice) | – | – |
| chiede il codice, ammesso | codice a 6 cifre | – | – |
| recensione verificata pubblicata | ricevuta «è pubblica» | email «nuova recensione, rispondi» | – |
| recensione non verificata in attesa | ricevuta «in attesa» | email «aspetta la tua approvazione» | – |
| approva / rifiuta | – (RV6) | esito a schermo | – |
| risponde | – (RV6) | – | – |
| segnala abuso | – | «in revisione» nella tab | email con motivo + coda |
| ripubblica / rimuove | – | email con l'esito | – |

- **RV4 e RV6 da fare** (invito post-esperienza; avviso a chi scrive
  sulle tappe successive, che richiede un consenso a conservare
  l'email).

## Ordine e stima
RV1 e RV3 sono solo frontend e chiudono la domanda del founder (la
pagina c'è e si vede, la porta è onesta): un ciclo. RV2 e RV5 sono
backend piccolo. RV4 è il valore commerciale e vuole più attenzione
(consensi, timing, guardie). RV6 resta fuori finché non deciso.
