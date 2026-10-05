# Piano «Iscrizione senza attrito» — 5/10/2026 sera

Richiesta del founder, dopo la prova dal vivo del pixel: *«Il processo intero è poco user friendly. Il banner deve incentivare "Accetta tutto". Dopo l'iscrizione la pagina scorre e la persona non vede la conferma. Il pulsante delle meditazioni nell'email riporta al form. Analizza tutti i processi di iscrizione, conferma, email e pulsanti: tutto immediato, umano, senza annoiare, senza bug né regressioni.»*

Tre mappe complete sono alla base di questo piano (una per i form e i loro stati di successo, una per le email e dove atterrano i loro pulsanti, una per il testo integrale di ogni email automatica). I riferimenti file:riga sono riportati in ogni lotto.

## 0. Principi

1. **Un gesto, un risultato visibile.** Chi invia un form vede la conferma nel punto in cui ha cliccato, subito, con il passo successivo scritto. Mai un risultato fuori schermo.
2. **Il pulsante dell'email apre davvero.** Un clic da un'email porta la persona dentro, su qualunque dispositivo, senza rimettere l'email e senza un secondo form.
3. **Una voce sola.** Tutte le email parlano come Valentina e Davide: prima persona, chiare, corte, senza gergo, senza declinazioni di genere, con un passo successivo e un solo pulsante principale.
4. **Zero regressioni.** Nessun cambio ai dati, ai token, alle regole di consenso o ai flussi di pagamento. Solo: come si mostra il risultato, dove atterra il link, cosa dice il testo. Ogni lotto ha la sua guardia e la prova dal vivo in prod dal browser (la lezione della CSP).
5. **Niente consenso implicito.** Il banner spinge verso «Accetta tutto» con gerarchia visiva e copy, non nascondendo il rifiuto: resta a un clic, come chiede il Garante.

## 1. Cosa abbiamo trovato (fatti)

### 1.1 Form e conferme
- **Nessun form di iscrizione gestisce lo scroll o il focus dopo l'invio**: non c'è un solo `scrollIntoView`, `focus()` o `aria-live` su un box di successo. Il risultato sostituisce il form «in place» con un box più basso: la pagina si accorcia e la persona resta a guardare il punto dove il form era. Casi peggiori: `InvitoSound.jsx:57` (tutto il form diventa una riga), `GrazieCerchio.jsx:34`, `PortaAurya.jsx:126`, `InlineSignupForm.js:99` (/entra-nella-rete), `LeadForm.jsx:246` su /cerca-ritiro (il form più alto del sito), `ProfessionalLanding.jsx:416`, `CreaStudioLanding.jsx:261`, `AziendePage.js:69`.
- Due cancelli fanno il contrario: aggiungono l'avviso **sopra** il form che resta (`MeditazioniPage.js:196`, `CancelloLettera.jsx:104`): l'avviso può restare fuori schermo.
- Due pagine usano **un ricaricamento intero** come conferma (`BlogArticlePage.js:400` e `:422`): si perde la posizione e si rivede tutto da capo.
- **Un'iscrizione silenziosa**: nella registrazione professionista da /accedi, la casella «Lettera» iscrive al Cerchio ma il messaggio di successo non lo dice (`AccountLoginPage.js:384`).
- I testi «cosa succede adesso» sono scritti in sei posti diversi e alcuni sono **falsi col singolo opt-in acceso**: /cerca-ritiro dice ancora «apri la casella e conferma, appena confermi si aprono le meditazioni» (`TravelerLandingPage.js:75`), `InvitoSound.jsx:64` dice «un clic su un suo link apre anche le meditazioni intere» (vedi 1.2).

### 1.2 Il pulsante delle meditazioni (il bug visto dal founder)
Il benvenuto del Cerchio ha il pulsante «Ascolta le meditazioni» costruito con il link verificante `/api/public/newsletter/v/{token}?to=/meditazioni` (`services/email_sequenze.py:447`, `services/verifica_email.py:43`). Il server segna l'indirizzo come verificato, conferma l'iscritto, manda il benvenuto se serve, e poi **rimanda a `/meditazioni` nudo** (`routers/subscribers.py:595`): niente token, niente parametro, niente cookie. La pagina legge la prova solo dal browser (`localStorage aurya_nl_token`, `lib/cerchio.js:36`), quindi trova il lucchetto e un campo email vuoto. Succede su qualunque dispositivo, anche quello da cui ci si è iscritti (lì la prova non c'è perché al momento dell'iscrizione l'indirizzo era «in attesa» e lo sblocco immediato dà 404, `routers/subscribers.py:662`).

Gli altri link della stessa email funzionano: «Le tue preferenze» e «dicci le tue vie» atterrano su `/newsletter/preferenze/{token}` che salva la prova; conferma, promemoria e «Riapri il mio accesso» passano da `/newsletter/conferma/{token}` che la salva. **Il difetto è solo nel pulsante principale.** Col doppio opt-in non si vedeva perché si passava sempre dalla pagina di conferma.

### 1.3 Email
Quarantasette email automatiche verso persone e professionisti (inventario completo nella mappa). Tre problemi sistemici:
1. **Due voci.** Le sequenze del Cerchio e dei professionisti sono scritte a mano, firmate Valentina e Davide. Tutto ciò che passa dal dizionario `EMAIL_TRANSLATIONS` (`services/email_service.py:163-500`) è e-commerce tradotto: «Clicca il pulsante qui sotto», «con successo», «store», «pack», «upgrade», «regolarizzare il pagamento», «la tua posizione». La stessa persona le riceve entrambe nella stessa settimana.
2. **Maschile di default**: «Benvenuto nel Cerchio» (soggetto di 3 benvenuti + account negozio), «Sei stato invitato» (2), «Se non sei stato tu» (3), «Grazie di esserti iscritto», «Se non ti sei iscritto tu», «chi ha prenotato con lui».
3. **Passo successivo assente o smentito**: ordine annullato senza dire chi e se c'è rimborso; «Vedi dettaglio ordine» che porta all'hub; «Richiesta ricevuta: ti contatteremo» sopra un blocco che dice di fare il bonifico; stato «chiusa» delle richieste senza spiegazione; aggiornamenti di consegna con oggetto e corpo identici.
Più tre errori veri: la ricevuta «servizi Pro» dice «la tua richiesta: **i suoi** eventi» (`strutture_email.py` ETICHETTE_PRO in terza persona); gli avvisi di stato producono «la tua richiesta è **abbiamo una o più proposte**»; l'invito da admin parla di «piattaforma di gestione finanziaria per PMI» (residuo di un altro prodotto, `email_service.py:1849`). Accenti sostituiti da apostrofi («e'», «piu'», «gia'») in decine di stringhe del dizionario, e il piè di pagina dice «scrivi a aurya.life@gmail.com» anche quando il corpo dice «rispondi a questa email».

## 2. I lotti

### FL0 — Banner cookie: spingere «Accetta tutto» restando nel Garante (0,5 g)
**Oggi**: tre pulsanti uguali in fila (Solo essenziali · Statistiche · Accetta tutto) + X. Tre scelte di pari peso: il rifiuto è visivamente il primo.
**Domani**, primo livello:
- titolo caldo e un rigo di beneficio: «Un sì ci aiuta a far trovare Aurya a chi la cerca. Cookie tecnici sempre; misurazione e inserzioni solo se accetti.»
- **un solo pulsante pieno, largo, scuro: «Accetta tutto»**;
- sotto, in testo piccolo: «Personalizza» e, a destra, «Continua senza accettare» (= solo essenziali). La X resta con la stessa etichetta.
- Secondo livello (Personalizza): due interruttori con una riga ciascuno (Statistiche: «capire quali pagine servono»; Marketing: «misurare le inserzioni, niente profili venduti a nessuno») + «Salva la scelta» + «Accetta tutto».
- Il «ricompare una volta» per chi aveva il banner vecchio resta com'è.
**Perché è lecito**: il Garante (linee guida 10/6/2021) chiede che proseguire senza consenso sia possibile dal primo livello con un gesto equivalente (X o link «continua senza accettare») e che personalizzare sia a portata: entrambi restano. Non si usa nessun dark pattern (nessun pulsante «rifiuta» nascosto o grigio illeggibile; il link ha contrasto leggibile).
**Non cambia**: `lib/consenso.js`, `salvaConsenso`, pixel, GA. Solo il componente e le quattro chiavi di copy.
**Guardia**: aggiornare `TestMP1Consenso` (testid: `cookie-accetta-tutto`, `cookie-personalizza`, `cookie-continua-senza`, `cookie-salva`), vietare consenso implicito (nessun `salvaConsenso(true…)` fuori da un clic), copy senza declinazioni.

### FL1 — Vedere il risultato: un helper, quattordici punti (1 g)
**Un solo helper** `lib/esito.js`: `mostraEsito(el)` = dopo il render (60 ms) `scrollIntoView({block:'center', behavior: reduced-motion ? 'auto' : 'smooth'})` + `focus({preventScroll:true})` su un contenitore con `tabIndex=-1` e `role="status"` (lo legge anche lo screen reader). Nessuna dipendenza, zero logica di business.
**Dove si monta** (box di successo con `ref`):
1. `LeadForm.jsx:246` (tutte le landing e i blog) · 2. `InvitoSound.jsx:57` · 3. `GrazieCerchio.jsx:34` · 4. `PortaAurya.jsx:126` · 5. `InlineSignupForm.js:99` · 6. `ProfessionalLanding.jsx:416` · 7. `CreaStudioLanding.jsx:261` · 8. `AziendePage.js:69` · 9. `CancelloLettera.jsx:104` (avviso sopra il form) · 10. `MeditazioniPage.js:196` · 11. `SoundHomePage.jsx:134` · 12. `AccountLoginPage.js` stati `signupSent`/`signupSentPro` (card centrata: scroll in cima) · 13. `ContattiOperatore.jsx:128` (recapiti aperti dopo la porta) · 14. `OperatorProfilePage.js:243` (modale: già centrato, solo focus).
**Il salto di altezza**: il box di successo eredita la stessa cornice del form (stesso `rounded-2xl` e padding, `min-height` pari all'altezza del form misurata al momento dell'invio): la pagina non si accorcia sotto i piedi. Dove non ha senso (riga singola di InvitoSound) basta lo scroll al centro.
**Via i due reload** di `BlogArticlePage.js:400/422`: lo sblocco diventa in place (stato `sbloccato` → rifetch del solo contenuto riservato), la posizione resta.
**La riga che manca**: nel successo di `AccountLoginPage` pro, se la casella Lettera era spuntata, una riga: «Ti abbiamo iscritto anche al Cerchio: la prima Lettera è in arrivo.»
**Guardia** `TestFL1Esito`: ogni file della lista importa `mostraEsito`; un test in node con jsdom finto verifica che il box riceva focus e che `scrollIntoView` venga chiamato una volta; nessun `window.location.reload()` nei due punti.

### FL2 — Il pulsante dell'email apre davvero (0,5 g)
**Il cambio**, in un punto: `GET /api/public/newsletter/v/{token}` (`routers/subscribers.py:573-595`) e `GET .../entra/{token}` (`:598-633`), quando rimandano a un percorso interno, aggiungono `?prova=<token>` all'URL di destinazione (il token è lo stesso JWT `newsletter_subscriber` che già viaggia nelle email).
**Il consumatore**, in un punto: `lib/cerchio.js` espone `raccogliProvaDaUrl()` chiamata in `index.js` prima del primo render: se c'è `?prova=`, la salva (`salvaProva`) e la toglie dall'indirizzo con `history.replaceState` (nessun token in cronologia, nessun referrer). Prima del render, così `MeditazioniPage`, la guida del blog, la scheda Sound trovano la prova già lì.
**Effetto**: un clic dal benvenuto → `/meditazioni` aperte, su qualunque dispositivo, senza rimettere l'email. Stesso effetto per «Apro le meditazioni» del promemoria e per i link delle ricevute d'ordine/recensione.
**Il campo email del cancello**, quando resta chiuso (prova assente), si precompila con `emailDellaProva()` se c'è, e il copy dice «Sei già nel Cerchio? Metti la tua email e si riapre» invece di proporre un'iscrizione nuova come prima scelta.
**Sicurezza**: identica a oggi (il token è già nelle URL delle email e nel path della pagina di conferma); scadenza invariata; nessun nuovo endpoint.
**Decisione per il founder (FL2b)**: sbloccare le meditazioni **subito dopo l'iscrizione sul dispositivo stesso**, senza aspettare il clic nell'email? Oggi il clic è la prova di qualità (`AURYA_VERIFICATO`, `LeadConfermato` a Meta). Se sì: `iscriviESblocca` riceve dal server un token «di cortesia» solo per quel browser; il clic nell'email resta la verifica. Consiglio: **no per ora**: col pulsante che apre davvero, il costo per la persona è un clic che ci serve.
**Guardia** `TestFL2Prova`: il redirect di `/v/` e `/entra/` porta `prova=` solo per percorsi interni; il consumatore salva e pulisce l'URL (test in node); prova dal vivo in locale con un token vero; e in prod, dal browser, il giro completo email → meditazioni aperte.

### FL3 — Le email: una voce sola, umana (1,5 g)
Riscrittura guidata dall'inventario, **senza toccare trigger, link, token o logica**. Regole di stile applicate a tutte: saluto «Ciao Nome,» (o «Ciao,»), prima persona plurale, una cosa per email, un solo pulsante principale con verbo («Apri le meditazioni», «Entra nel tuo spazio»), il passo successivo scritto, accenti veri, mai «click», mai declinazioni, firma dove ha senso, piè di pagina coerente col corpo («rispondi a questa email» quando il Reply-To è nostro).

**3a. Cerchio (nn. 1-6 dell'inventario)**
- Soggetti: «Benvenuto nel Cerchio di Aurya» → **«Sei nel Cerchio di Aurya»**; variante meditazioni → «Sei nel Cerchio: le meditazioni sono aperte».
- **La frase del founder** nel benvenuto ritiri (`email_sequenze.py:458-471`): «Sei nel Cerchio di Aurya. **Sappiamo che ti interessano gli eventi e i ritiri di Aurya a Bari (zona).**» con le varianti: solo vie → «…ti interessano {yoga, meditazione} e i ritiri di Aurya»; solo luogo → «…ti interessano gli eventi e i ritiri di Aurya a Bari (zona)» / «in Italia» / «in Italia o all'estero»; niente → «…ti interessano gli eventi e i ritiri di Aurya».
- Conferma (n. 1): via «Se non ti sei iscritto tu» → «Se non eri tu, ignora questa email: senza il clic non ti scriviamo».
- Promemoria doppio opt-in (2a): via l'ultimatum «è l'ultima email che ricevi» → «Se non ti va, non devi fare nulla».
- «Dicci le tue vie» → «Dicci cosa ti interessa (yoga, respiro, suono…) e dove vivi».
- «Se le apri da un altro dispositivo e trovi il lucchetto» sparisce: con FL2 non serve più.
**3b. Account e accessi (nn. 7-15)**: le quattro email dell'account negozio (11-14) e il blocco account (15) riscritte nella voce di casa: via «con successo», «questa azione», «Verifica Email» in maiuscole, «Se non sei stato tu» → «Se non eri tu». L'email di verifica dalla porta dei contatti dice «il clic ti riporta alla pagina di {operatore}». La claim (n. 10): «Il link vale 15 minuti» → link di 7 giorni se il servizio lo consente (da verificare: oggi è il magic link) oppure dirlo prima del pulsante.
**3c. Professionisti (nn. 16-29)**: n. 17 «La tua pagina è online» spezzata: il link e il listino restano; i canali Telegram vanno in un'email propria il giorno dopo; la consulenza a pagamento esce da questa email (va nelle sequenze a 30 giorni, o nella Lettera). Reinvio verifica (22) e reset (23) nello stesso stile della n. 16. Invito nel team (25): mai la password in chiaro nel corpo → link di primo accesso. Invito da admin (27): copy giusto («Aurya, la rete dei professionisti del benessere»). Disattivazione (28-29): tono umano, un pulsante, un indirizzo a cui scrivere. Store/quote (30-31): «la tua pagina», mai «store/pack/upgrade».
**3d. Ordini e prenotazioni (nn. 37-44)**: «Richiesta ricevuta» con la riga vera in testa («{Operatore} ha la tua richiesta. Per tenere il posto: bonifico di X entro il Y» oppure «ti scrive per concordare») e via «Ti contatteremo a breve»; «Ordine confermato»: pulsante «Vai al tuo ordine» che porta all'ordine, non all'hub, e via «in lavorazione» per i ritiri; «Ordine annullato»: chi l'ha annullato, se e come arriva il rimborso, a chi scrivere; consegna/ritiro: una riga di informazione in più nel corpo; solleciti: via «regolarizzare» e «la tua posizione» → «Il saldo di 300 € era previsto per il 20 giugno. Se l'hai già fatto con bonifico, ignora pure»; date in formato italiano (n. 42); «Ciao partecipante» → «Ciao,»; «Riceverai presto istruzioni sul rimborso» → tempi e modo.
**3e. Recensioni e richieste (nn. 32-36, 45-47)**: OTP con il nome del professionista; «con lui» → «con questa persona»; ricevute con saluto; «Aggiornamento sulla tua richiesta» con oggetto per stato e stato «chiusa» spiegato; fix delle due frasi rotte (ETICHETTE_PRO in seconda persona; costruzione degli avvisi di stato).
**Metodo**: le stringhe nuove le propongo in un file `docs/EMAIL_COPY_2026-10.md` (prima/dopo, una tabella per email) **prima** di toccare il codice; il founder legge e corregge; poi si applica in un giro. Così il tono è suo, non mio.
**Guardia** `TestFL3Email`: nessuna delle parole proibite nel dizionario e nelle sequenze («con successo», «click», «store», «pack», «upgrade», «regolarizzare», «Benvenuto nel», «Sei stato», «sei stato tu», «iscritto tu», «con lui»); accenti veri (nessun «e'», «piu'», «gia'» nei testi IT); ogni email ha saluto e al massimo un pulsante principale (dove la struttura lo consente); i template si renderizzano con contesti pieni e vuoti senza frasi rotte (test di rendering per i 47 casi).

### FL4 — Un solo testo «cosa succede adesso» (0,5 g)
`lib/cerchio.js` diventa l'unica fonte dei tre stati (già dentro / benvenuto / conferma) con tre funzioni (`titoloEsito`, `corpoEsito`, `prossimoPasso`), usate da LeadForm, InvitoSound, GrazieCerchio, CancelloLettera, MeditazioniPage, SoundHomePage, modale recensione, NewsletterConfirmPage. Via i `thanksBody` sparsi nelle landing che oggi dicono il falso. Col singolo opt-in acceso il testo è uno: «Sei nel Cerchio. La prima Lettera è in arrivo: un suo pulsante apre le meditazioni, su qualunque telefono» (vero grazie a FL2).
**Guardia**: nessun `thanksBody=` con «conferma» nelle landing; i tre stati pinnati.

### FL5 — Account e professionista: il clic dell'email porta dentro (0,5 g)
- La verifica dell'**account cliente** (`AccountVerifyEmailPage.js`, `platform_account_service.verify_signup_email`) oggi conferma e rimanda al login; il professionista invece entra con un clic (FV1). Allineare: la verifica rilascia la sessione e porta a `next` (porta dei contatti) o a `/account`. Riusa la stessa funzione di sessione del magic link. Dietro l'interruttore già esistente `LOGIN_SENZA_VERIFICA`? No: è un comportamento sano di default, con guardia.
- Il campo email del login resta precompilato dall'email verificata (già c'è: `entraInAurya`).
**Guardia** `TestFL5Verifica`: la risposta della verifica porta `access_token` una sola volta (token monouso), il secondo clic dice «già confermato» e porta al login.

### FL6 — Guardie, suite, deploy, prova dal vivo (0,5 g)
Suite intera al baseline; copia dei locale per i bot AI se si toccano landing; giro backend+frontend (nessun nginx); **prova in prod dal browser interno**: banner nuovo → Accetta tutto → iscrizione su /cerca-ritiro con risultato visibile senza scroll → email di benvenuto → clic sul pulsante da un altro browser → meditazioni aperte senza form. Tag `prod-2026-10-0X-attrito`.

## 3. Ordine e tempi

| Ordine | Lotto | Giorni | Dipende da |
|---|---|---|---|
| 1 | FL2 pulsante dell'email (il bug) | 0,5 | — |
| 2 | FL1 vedere il risultato | 1 | — |
| 3 | FL0 banner | 0,5 | — |
| 4 | FL4 un solo testo | 0,5 | FL2 (il testo diventa vero) |
| 5 | FL3 email (prima il file prima/dopo, poi il codice) | 1,5 | lettura del founder |
| 6 | FL5 verifica account entra | 0,5 | — |
| 7 | FL6 suite + deploy + prova | 0,5 | tutti |
| | **Totale** | **5** | |

Un giro di deploy dopo FL2+FL1+FL0+FL4 (il grosso dell'attrito sparisce in un giorno e mezzo), un secondo giro con FL3+FL5 dopo la lettura dei testi.

## 4. Decisioni per il founder

1. **FL0**: primo livello = «Accetta tutto» pieno + «Personalizza» + «Continua senza accettare» in testo piccolo. Ok così?
2. **FL2b**: sblocco immediato sul dispositivo dell'iscrizione (senza aspettare il clic)? Consiglio di no per ora.
3. **FL3**: ti va bene leggere il file prima/dopo delle 47 email prima che tocchi il codice? Sono circa 20 minuti di lettura.
4. **FL5**: il clic di verifica dell'account cliente fa entrare direttamente (come il professionista)? Consiglio di sì.
5. Scelta del nome per l'oggetto del benvenuto: «Sei nel Cerchio di Aurya» (consigliato) o altro.

## 5. Stato (5/10/2026 notte): FL0-FL2, FL4, FL5 implementati in locale; FL3 in lettura; deploy sul via

| Lotto | Stato | Commit |
|---|---|---|
| FL2 pulsante dell'email | fatto | ea0d65c2 |
| FL1 risultato visibile (14 punti + via i reload) | fatto | 934e2753 + 4b766206 (fix build) |
| FL0 banner | fatto | 0d99a7f7 + 7c46d685 |
| FL4 frase unica | fatto | 748af6ae |
| FL5 verifica account = entra | fatto | 2f0bf411 |
| FL3 email | **prima/dopo in `docs/EMAIL_COPY_2026-10.md`, in lettura dal founder**; codice dopo | 935bcd73 |
| FL6 | script `deploy/giri/deploy-2026-10-05-attrito.sh` pronto; deploy solo sul via | — |

Verificato in locale dal browser interno: banner nuovo (primo e secondo livello), «Accetta tutto» salva marketing=sì, iscrizione da /cerca-ritiro con la pagina scorsa di 514 px → il box «Ci sei.» torna al centro dello schermo con il focus (role=status); il dev server compila senza errori (un commento ESLint malformato in esito.js avrebbe rotto il build di produzione: trovato e corretto prima del giro). Suite intera: nessun rosso nuovo rispetto alla base.

Decisioni del founder (5/10 sera): banner come proposto; il clic nell'email resta la prova (niente sblocco immediato); i testi delle email li verifica lui prima del codice; la verifica dell'account fa entrare; oggetto «Sei nel Cerchio di Aurya».
