# Registrazione e profilo pubblico: analisi e piano di rifinitura

24 settembre 2026. Analisi in sola lettura del codice e dei 20 operatori reali in produzione, dopo le inefficienze viste dal founder: profili intestati a un nome impersonale, bio corte, telefono assente, listino mai compilato, nessun modo per l'admin di correggere un profilo se l'operatore non risponde.

Regola del piano: **niente si rompe per chi è già dentro**. Ogni cambiamento è additivo, i profili esistenti restano identici finché il founder non approva una lista di correzioni una per una.

---

## 1. Come funziona oggi (fatti dal codice)

### 1.1 Registrazione (`/accedi?vista=crea`, interruttore «Sono un professionista»)

| Campo | Obbligatorio | Dove finisce |
|---|---|---|
| «Il tuo nome» (un campo solo) | sì | `users.name` |
| «Nome della tua attività» | **sì** | `organizations.name` |
| Email, password (≥12, maiuscola, cifra) | sì | `users` |
| Consenso termini + privacy | sì | `users.accepted_terms_*` |
| Telefono | **non esiste** | — |

File: `frontend/src/features/account/AccountLoginPage.js` 701-805, `backend/services/auth_service.py` 82-159. Non esistono nome e cognome separati, né telefono, né nel modello `User` né in `Organization`.

**È qui che nasce il problema dei nomi impersonali**: il campo «Nome della tua attività» è obbligatorio, quindi chi non ha un marchio se ne inventa uno («La Nuova Alba», «Casa Coco», «Cerchio Angelico») o ci scrive il proprio mestiere («Life Coach e Insegnante di Yoga»). E quel campo è **l'unico nome pubblico**: `organizations.name` va sulla pagina `/o/{slug}`, sulle card della directory, nel titolo SEO «Nome · Discipline a Città | Aurya», nella pagina link, nelle email. Il nome della persona (`users.name`) non compare mai in pubblico (`backend/routers/public.py` 4390, 4649; `seo_shell.py` 2308-2416; guardia `test_op4_profile.py`).

### 1.2 /benvenuto (subito dopo la verifica email)

Chiede, tutto facoltativo e saltabile: discipline, città, **telefono**, Instagram. Il telefono va in `public_profile.public_phone` (max 40). Chi salta non viene più richiamato. File: `WelcomeRetePage.js` 25-203.

### 1.3 Editor del profilo pubblico (`/public-profile`)

- Sezione essenziale: copertina, ritratto, tagline (80), **bio (max 600, nessun minimo)**, sedi (3), discipline (10), social.
- Hint della bio oggi: **«Racconta chi sei e che esperienze crei — 2-3 frasi bastano.»** (`locales/it/settings.json` 720) più un aiutino a bio vuota con tre domande. È il testo che ha prodotto bio da 130-300 caratteri.
- Il **nome pubblico è modificabile anche qui**, ma dentro l'accordion «Per approfondire», chiuso di default (`PublicProfilePage.js` 811-822), e coincide con il nome azienda delle Impostazioni. Il founder non lo trovava perché è nascosto.
- Telefono e email pubblici sono nello stesso accordion, con la spunta `show_contacts` (default spento): il numero, se c'è, è già privato finché non lo si espone.
- Completezza: 4 check (copertina, bio non vuota, sede, un social). **La qualità della bio non conta**, contano solo i byte > 0.

### 1.4 Stato «online» e sequenze email

`online = slug AND bio non vuota AND (copertina o social) AND almeno un servizio pubblicato`. Guida le email np5/np10/np15 («ti manca solo la pagina») e la «pagina online». Le email chiedono già «un servizio con il prezzo», ma **nessuna email è dedicata al listino** e la home dell'operatore (`OperatorHome.js`) **non mostra nessun promemoria**: la striscia-guida vive solo dentro `/public-profile` e `/listino`.

### 1.5 System admin

Può: rete Aurya, badge, lucchetto directory, intervista (5 campi), stato org, impersonare. **Non può modificare nome, bio, telefono, tagline, discipline, sedi di un operatore.** L'unica via è l'impersonation (`admin.py` 2451), che non lascia traccia di «modificato da Aurya».

---

## 2. Cosa dicono i dati di produzione (20 operatori reali, 24/9)

| Misura | Valore |
|---|---|
| Nome pubblico = solo marchio, senza la persona | **7 su 20** (Metodo Oltre, Life Coach e Insegnante di Yoga, Studio ZENITH, essenzaluce, La Nuova Alba, Casa Coco, Cerchio Angelico) |
| Nome pubblico misto (persona + marchio) | 6 su 20 (spesso per intervento manuale del founder) |
| Nome pubblico = solo persona | 7 su 20 |
| Bio sotto 300 caratteri | **8 su 20** |
| Bio sotto 500 caratteri | 15 su 20 |
| Nessun servizio a listino | **4 su 20**; altri 5 hanno un solo servizio |
| Nessun telefono | **9 su 20** |
| Contatti mostrati (`show_contacts`) | 6 su 20 |
| Nella rete Aurya (`network_member`) | 10 su 20, tutti iscritti prima del 15/9 |

Il campo `users.name` è a qualità mista: «Valentina», «Esther» (solo nome), «Ilaria Barbaccia Barbaccia» (doppio cognome per errore), «claudia Rossato» (minuscola), «Anpoche» (marchio nel campo persona). Quindi **un ricalcolo automatico del nome pubblico dai dati esistenti non è affidabile**: va proposto e rivisto a mano, una volta, per i 20 di oggi. Per i nuovi il flusso deve produrre il dato giusto da solo.

Il peggioramento è recente: i 9 iscritti dal 17/9 hanno bio medie più corte (126-533) e 5 di loro zero o un servizio. Il flusso «unico» è più veloce e produce profili più vuoti.

---

## 3. Diagnosi in cinque righe

1. Il nome pubblico è l'organizzazione perché il modello non ha mai avuto una persona: il campo obbligatorio sbagliato al momento sbagliato.
2. La bio è corta perché glielo diciamo noi («2-3 frasi bastano») e perché niente misura la qualità.
3. Il telefono manca perché è facoltativo, chiesto una sola volta, nella pagina che si salta.
4. Il listino resta vuoto perché il promemoria vive nelle due pagine che chi non compila non apre; la home, che aprono tutti, tace.
5. L'admin non può correggere perché non esiste l'endpoint: si è sempre supplito con l'impersonation.

---

## 4. Il piano, a fasi rilasciabili e reversibili

### P1 · Identità: la persona prima del marchio (2 giorni)

**Modello.** Nuovo campo `public_profile.nome_persona` (max 80, whitelist). `organizations.name` resta e diventa «il marchio» (facoltativo nel nuovo flusso). Una sola funzione backend `nome_pubblico(org)` decide cosa si mostra:

- persona e marchio presenti e diversi → «Valentina · Brillare | Il Sole Dentro»;
- solo persona → «Valentina»;
- solo marchio (operatori di oggi, senza `nome_persona`) → il marchio, **identico a oggi**;
- marchio che contiene già la persona → il marchio così com'è, senza duplicare.

Il payload pubblico porta `name` (già composto, così card, pagina, link e SEO non cambiano codice) più `nome_persona` e `marchio` separati per il layout dell'intestazione: nome grande, marchio sotto. Lo slug non cambia mai da solo.

**Editor.** «Il tuo nome» e «La tua attività (se ne hai una)» salgono nella sezione essenziale, prima della tagline. L'accordion perde il «Nome pubblico». Le Impostazioni mantengono il nome azienda (fatturazione, email), con la nota «è il marchio che compare accanto al tuo nome».

**Registrazione.** «Nome e cognome» obbligatorio (con controllo morbido: se una parola sola, un avviso «meglio nome e cognome», non un blocco). «Nome della tua attività» diventa **facoltativo**: se vuoto, `organizations.name` = nome della persona, e il profilo nasce già personale. Nessun campo nuovo obbligatorio oltre al telefono (P3).

**Operatori esistenti.** Uno script propone `nome_persona` per i 20 da `users.name` ripulito (maiuscole, doppioni) in un CSV; il founder lo rivede riga per riga; si applica solo il CSV approvato. Fino ad allora tutti i profili restano come sono. Poi il founder smette di scrivere agli operatori uno a uno.

**Rischi e guardie.** Il titolo SEO cambia per chi avrà persona + marchio: è voluto. Le guardie `test_op4_profile` vanno estese a `nome_pubblico()`. `display_name` fantasma in `frequencies.py` si allinea alla stessa funzione.

### P2 · La bio che presenta davvero (1 giorno)

- Hint nuovo, con i sei punti del founder, sopra il campo: di cosa ti occupi, quali pratiche o percorsi proponi, a chi ti rivolgi, la tua visione del benessere, il tuo approccio, cosa può aspettarsi chi inizia un percorso con te. Chiusura: «l'obiettivo è permettere a chi arriva sul tuo profilo di conoscerti meglio».
- Limite da 600 a **1000** caratteri (la guardia esistente ammette ≤ 1000), contatore che cambia colore: sotto 300 «troppo breve per farti conoscere», 300-600 «buona», oltre «completa».
- L'aiutino a bio vuota diventa sei micro-domande cliccabili che inseriscono un capoverso vuoto con l'attacco («Mi occupo di…», «Mi rivolgo a…»).
- **Il gate «online» non cambia**: una bio corta non toglie nessuno dalla directory. La qualità entra solo nella barra di completezza (quinto check «bio di almeno 300 caratteri») e nel punteggio interno della directory (ordinamento, non esclusione).
- Le email np5/np10 e la «pagina online» ricevono la stessa formula in una riga.

### P3 · Il telefono, privato di default (mezza giornata)

- Alla registrazione: campo «Telefono» obbligatorio, con la riga «serve ad Aurya per contattarti; non compare sul profilo finché non lo decidi tu». Validazione: solo cifre, `+`, spazi; da 8 a 15 cifre.
- Si salva in `public_profile.public_phone` con `show_contacts` che resta spento: **nessun numero diventa pubblico**. Nell'editor la spunta cambia etichetta: «Mostra il telefono sul profilo pubblico».
- /benvenuto smette di chiederlo se c'è già.
- Per i 9 operatori senza numero: una riga nella home «Aurya non ha un tuo recapito: aggiungi un telefono, resta privato» con il campo inline, finché non lo mettono.
- La scheda 360° dell'admin mostra il numero anche quando è privato (è il motivo per cui lo chiediamo).

### P4 · Il listino come passo naturale (1 giornata) — rivisto il 24/9 con il founder

**Il fatto che cambia la risposta.** L'email «La tua pagina è online» (`op_profilo_online`) parte solo quando `online` è vero, cioè anche con almeno un servizio pubblicato. Chi pubblica il profilo senza listino **non la riceve mai**; al giorno 5 riceve invece «Ti manca solo la pagina» (`op_np5`), che per lui è falsa: la pagina l'ha appena fatta. Lo perdiamo nel momento in cui si aspetta una conferma.

Decisione del founder: niente esempi per disciplina (troppo complesso), niente popup. Tre pezzi piccoli:

1. **L'email che già esiste parte prima.** `op_profilo_online` si invia quando NASCE la pagina (primo salvataggio con bio → `_ensure_public_surface` conia lo slug), non al primo servizio. Un blocco dinamico: senza servizi → «Il prossimo passo è il listino: una riga, un prezzo, una durata. Senza, chi arriva sulla tua pagina non sa cosa può prenotare», link a `/listino`, un solo esempio generico («Trattamento individuale · 60 min · 60 €»); con servizi → «hai già N servizi». Una email sola, integrata in quella di oggi.
2. **np5/np10/np15 smettono di mentire.** Nuovo stato del motore `pagina_senza_listino` accanto a `senza_pagina` (`sequenze.stato_operatore`): stesse finestre, stesso passo, cambia il primo capoverso («La tua pagina c'è, manca il listino»). Chi non ha la pagina riceve i testi di oggi. La condizione `online` resta invariata per `r14` e per tutto il resto.
3. **Card fissa nella home dell'operatore** finché non esiste un servizio pubblicato: «La tua pagina è online ma non ha servizi» + «Aggiungi il primo servizio». Non un popup: resta, non interrompe, sparisce da sola. Dopo «Salva profilo» la striscia già esistente che rimanda al listino diventa il messaggio di conferma visibile.

Guardie: `test_sequenze` per i due stati e per l'evento «pagina nata»; nessuna email in più per chi ha già il listino (riceve la stessa di oggi, prima).

### P5 · Regia dell'admin: modificare quando l'operatore non risponde (1 giornata)

- Endpoint `PATCH /admin/organizations/{id}/public-profile` che riusa **la stessa funzione di pulizia** della PATCH dell'operatore (da estrarre in `services/profilo_pubblico.py`): niente seconda logica. Campi: nome persona, marchio, tagline, bio, telefono, `show_contacts`, discipline, sedi.
- Ogni salvataggio scrive un audit «modificato da Aurya (admin, motivo)» e, a scelta, manda all'operatore l'email «abbiamo sistemato la tua pagina: ecco cosa».
- UI: nel cassetto dell'organizzazione in `/admin/operatori`, tab «Profilo» con gli stessi campi dell'editor e la lista dei profili «da rivedere» (bio < 300, senza telefono, senza listino, nome solo marchio) come coda di lavoro.
- Il founder oggi fa questo a mano via chat: la coda gli dice dove intervenire e l'endpoint gli evita l'impersonation.

### P6 · Misura e deploy

- Un cruscotto in admin con le quattro misure di §2, ricalcolate ogni giorno: è il modo per vedere se il flusso nuovo produce profili migliori senza rincorrere gli operatori.
- Deploy in due giri: P1+P2+P3 (registrazione ed editor, con il CSV dei 20 applicato dopo il go) e P4+P5. Suite completa, prova generale sulla copia di produzione per lo script del CSV.

---

## 5. Cosa non cambia (invarianza dichiarata)

- Nessun profilo esistente cambia nome, bio o visibilità senza il CSV approvato.
- Slug e URL restano quelli di oggi.
- Il gate «online» e le sequenze email esistenti non cambiano condizione: si aggiunge solo `op_listino`.
- Nessun numero di telefono diventa pubblico per effetto del piano.
- La registrazione aggiunge un campo obbligatorio (telefono) e ne rende uno facoltativo (attività): il tempo per iscriversi non aumenta.

## 6. Ordine consigliato e stima

P1 (2 gg) → P3 (½) → P2 (1) → primo deploy → P4 (1) → P5 (1) → P6 (½) → secondo deploy. Circa sei giornate di lavoro, due giri di produzione.

## 7. Decisioni del founder (24/9)

1. Nome composto: **«Valentina · Brillare»**, punto mediano.
2. Telefono obbligatorio **solo per i professionisti**, non per chi si iscrive ad Aurya Sound.
3. Quando l'admin corregge una pagina **nessuna email automatica**: scrive il founder.
4. Listino: **niente esempi per disciplina**; l'email di pagina online parte alla nascita della pagina con il blocco listino, np5/10/15 con lo stato «pagina senza listino», card fissa in home (P4 rivisto).

Prossimo passo proposto: P1 identità, con il CSV dei 20 nomi da rivedere prima di applicarlo.

---

## 8. Le email automatiche: inventario, incoerenze, piano (PE)

Inventario completo su tutto il backend (24/9): **31 email all'operatore, 33 al cliente finale, 6 all'iscritto del Cerchio, 12 interne** alla casella Aurya. Mittente unico `noreply@aurya.life`, Reply-To sempre presente (di default la casella Aurya). Il «gate» email non c'entra col prelancio: è solo la lista dei rimbalzati.

### 8.1 Quello che parte davvero (produzione, ultimi 30 giorni)

| Email | Inviate | Nota |
|---|---|---|
| **«Da 2 giorni su Aurya: …» (interna, g2)** | **16** | la più inviata di tutte: una per ogni nuova org, condizione «sempre» |
| «La tua pagina è online» | 8 | |
| «Ti manca solo la pagina» (np5) | 6 | |
| «Cosa blocca, di solito» (np10) | 3 | |
| «Un'ultima cosa» (np15) | 2 | |
| «Il primo ritiro» (r14) | 1 | |
| Benvenuti Cerchio | 19 su 22 confermati | |

Il 44% delle email della sequenza operatore va a noi stessi. Nessun errore Brevo negli ultimi 7 giorni.

### 8.2 Incoerenze trovate

**Fuorvianti per l'operatore**
1. «Ti manca solo la pagina» (np5/10/15) parte a chi ha già la pagina ma non un servizio: la condizione `online` richiede un servizio pubblicato. Oggi in produzione non è ancora successo (0 casi), ma succederà: 4 operatori su 20 sono esattamente in quello stato. Peggio: chi ha pubblicato **solo un ritiro** (`event_ticket`) è «non online» e riceve «la tua pagina non è ancora online» pur avendo già lavorato.
2. «La tua pagina è online» parte solo con un servizio, quindi chi pubblica il profilo senza listino non la riceve mai (§4 P4). E può arrivare fino a 60 giorni dopo l'iscrizione con il tono del giorno zero.
3. «Un'ultima cosa, poi non insistiamo» promette l'ultima email sulla pagina, ma se l'operatore va online dopo riceve comunque «La tua pagina è online». Difendibile, da dire meglio.
4. **Bug**: l'email di quota all'80% ha oggetto e capoverso letterali `quota_warn_80_subject` / `quota_warn_80_intro` (chiave i18n inesistente, `quota_email_service.py:225-226`). Da correggere subito, è imbarazzante.
5. «Pagamento a rischio» all'operatore ha il piè di pagina «rispondi ad Aurya» ma parla di un cliente: il Reply-To va al cliente, come già fa «Nuova richiesta».

**Interne inutili o incoerenti**
6. **g2 «Da 2 giorni su Aurya»**: da eliminare (decisione del founder). In più il testo si contraddice: dice «non ha ancora la pagina online» e poi «controlla che sia entrato nei canali Telegram, i link li ha ricevuti con l'email della pagina online», che non ha ricevuto. E occupa il posto nel giro delle 6 ore: quando g2 e «pagina online» sono dovute insieme, la pagina online slitta di 6 ore. Le richieste struttura/regia/aziende/Pro, le segnalazioni di recensioni e le candidature restano: sono code di lavoro.
7. Il lead pre-lancio va a `info@aurya.life` scritto nel codice, non alla casella Aurya come tutto il resto.

**Doppioni**
8. Cerchio: «Benvenuto nel Cerchio: un clic e sei dentro» (conferma) e, al clic, «Benvenuto nel Cerchio di Aurya» (benvenuto): due oggetti quasi uguali nello stesso minuto. Il doppio opt-in serve; l'oggetto no.
9. Alert Stripe critici a tutti gli admin dell'org più ops: N+1 copie identiche.

**Codice morto e buchi**
10. `send_welcome` («Benvenuto su Aurya — Verifica la tua email») importata e mai chiamata; `send_email_with_attachment` senza chiamanti; `footer_auto` mai più letto.
11. **Buco legale**: la richiesta GDPR di cancellazione account importa `send_admin_notification`, che non esiste; l'errore è ingoiato e **nessuna email parte**, con un SLA di 30 giorni dichiarato in un testo mai spedito (`routers/customer_portal.py:1545-1565`).
12. Il re-consent legale non manda nessuna email: è solo in-app. Va bene così, ma va saputo.

### 8.3 Il percorso email dell'operatore, riscritto

Principio: **una email per momento, ogni email vera nello stato in cui arriva, nessuna email a noi che non sia una coda di lavoro.**

| Momento | Email | Condizione (nuovo motore) |
|---|---|---|
| Giorno 0 | «Il tuo spazio su Aurya è aperto» (verifica + tre passi) | registrazione |
| **Nasce la pagina** (primo salvataggio con bio → slug) | «La tua pagina è online: ecco il link» con blocco listino dinamico | evento, entro 60 giorni; se già passata non si ripete |
| Giorni 5-9 | «Ti manca solo la pagina» **oppure** «La tua pagina c'è, manca il listino» | `senza_pagina` / `pagina_senza_listino` |
| Giorni 10-14 | «Cosa blocca, di solito» nelle due varianti | idem |
| Giorni 15-21 | «Un'ultima cosa» nelle due varianti; testo: «l'ultima su questo passo» | idem |
| Giorni 14-20 | «Il primo ritiro» | pagina + servizio, nessun ritiro (chi ha già un ritiro non riceve niente) |
| Nuova richiesta, recensione, pagamento a rischio | come oggi, con Reply-To corretto | evento |

Stati del motore (`stato_operatore`): `pagina` (slug + bio), `listino` (servizio pubblicato), `ritiro`. `online` = pagina + listino resta per compatibilità. Chi ha solo il ritiro conta come «ha lavorato»: riceve la variante listino, non «non hai la pagina».

### 8.4 Fase PE · Email (1 giornata, nel primo giro di deploy)

- PE1 **Via g2**: rimosso il passo dalla tupla `PASSI["operatore"]` e il template; il motore non dipende da lei. Guardia: nessun passo con destinatario admin nella sequenza operatore.
- PE2 **Pagina online alla nascita della pagina** + blocco listino (= P4.1). Evento marcato una volta sola, come oggi.
- PE3 **Due stati** per np5/10/15 (= P4.2) e testo dell'«ultima» corretto.
- PE4 **Bug quota 80%**: chiave i18n giusta + test che ogni `_t()` usata nei servizi email abbia la chiave in it/en/de/fr (chiude anche il rischio per le altre famiglie).
- PE5 **Reply-To coerente**: «Pagamento a rischio» risponde al cliente; alert store e recensioni tengono la casella Aurya ma il piè di pagina lo dice senza il brand del negozio.
- PE6 **GDPR**: `send_admin_notification` implementata (casella Aurya, oggetto «[GDPR] Richiesta cancellazione account»), test che la richiesta la spedisce.
- PE7 **Lead** → casella Aurya invece di `info@` nel codice.
- PE8 **Cerchio**: oggetto della conferma «Un clic per entrare nel Cerchio», così il benvenuto non sembra un doppione. Contenuti invariati.
- PE9 **Pulizia**: `send_welcome`, `send_email_with_attachment`, `footer_auto` e le loro chiavi via; `passo_dovuto` resta per i test.
- PE10 **Alert critici**: una copia a ops e una al primo admin dell'org, non a tutti.
- Misura: il conteggio per passo esiste già in admin (`conta_invii`); si aggiunge la riga «email interne al mese» che dopo PE1 deve scendere di 16.

Fuori dal piano, da decidere a parte: le email del cliente finale (33) sono coerenti tra loro e con il brand del negozio; non le tocco in questo ciclo.

### 8.5 Ordine aggiornato

**Giro 1**: PE (1 g) → P1 identità (2 g) → P3 telefono (½) → P2 bio (1) → deploy, CSV dei 20 nomi dopo il go.
**Giro 2**: P4 listino in home (½, la parte email è già in PE) → P5 admin (1) → P6 misure (½) → deploy.
Totale circa sette giornate.
