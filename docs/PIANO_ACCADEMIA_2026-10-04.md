# Aurya Accademia e Negozio — piano profondo (v2)

*4 ottobre 2026. Segue l'analisi di fattibilità (`ANALISI_ACCADEMIA_ECOMMERCE_2026-10-04.md`). Qui: quanto c'è da fare davvero, quanto il piano è solido, scalabile e isolato, e com'è l'esperienza, semplice, per l'operatore che crea e per la persona che compra e segue.*

## 0. Il giudizio in una pagina

**Quanto c'è da fare.** Circa 16 giorni di lavoro per l'accademia completa (guide digitali, videocorsi, prodotti fisici, directory), più 2 giorni di fondamenta che servono comunque. Non 16 giorni di invenzione: il 60% è codice che esiste e va saldato all'Aurya di oggi, il 40% è nuovo e sta in tre punti precisi: video gestito da Aurya, consegna nell'account unico, commissione per riga.

**Quanto è solido il materiale.** Il legacy è ben fatto nelle fondamenta (modelli, emissione degli accessi alla conferma, download a token, firma dei video, progresso idempotente) e debole nelle superfici (editor e wizard da 900-1.100 righe ciascuno, scritti per un gestionale generico, in inglese nei testi, con troppi passi). Si tengono le fondamenta, si riscrivono le superfici in tre gesti, come si è fatto per il listino.

**Quanto è isolato.** Ogni modulo è un contesto chiuso con il suo registro, le sue rotte, i suoi flag. Ritiri, servizi, Cerchio, Sound e il motore pagamenti non cambiano se non in un punto, la commissione per riga, coperto da guardie. Un modulo spento è invisibile: non una pagina, non una voce di menu, non una riga di listino.

**Quanto è scalabile.** Video e file non passano mai dal nostro server: Bunny serve i video dalla sua CDN, lo storage serve i file; il backend firma, conta e registra. Il server di oggi regge mille studenti come ne regge dieci. Il costo è variabile e piccolo, coperto dalla commissione.

**Quanto è semplice.** Operatore: tre gesti per una guida (carica, prezzo, pubblica), tre per un corso (titolo e copertina, lezioni trascinando i video, prezzo e pubblica). Studente: compra dal profilo con l'account Aurya, trova tutto in «I miei corsi» e «I miei file», riprende da dove era, da qualunque dispositivo.

## 1. Architettura: sette contesti, un solo cliente

```
 Catalogo (tipi)      Consegna (accessi)      Media (video, file)
 product_types        IssuedDownload           Bunny gestito da Aurya
 digital | course |   IssuedCourseAccess       storage privato + firma
 physical             legati a platform_account_id
          \                 |                   /
           \                |                  /
            Pagamenti (Stripe Connect, fee per riga, registro)
                            |
            Account Aurya (/account: ordini, corsi, file, biglietti)
                            |
            Vetrina (profilo /o/, landing /dg /co /ph, directory)
                            |
            Regia (Strumenti, moduli a piano, flag di emergenza, audit)
```

Regole del disegno:
1. **Un solo cliente**: `platform_account_id` è la chiave di ogni accesso. Il cliente legacy per negozio non entra nelle superfici nuove; il player legacy resta solo per le email già spedite (zero iscrizioni in prod: si dismette al primo giro utile).
2. **Il profilo è il negozio**: ogni cosa in vendita è una sezione del profilo con acquisto inline, come i servizi oggi. Le landing per tipo sono le pagine di dettaglio indicizzabili.
3. **Il server non trasporta byte pesanti**: upload diretti da browser a Bunny e allo storage con credenziali firmate e a scadenza; riproduzione e download diretti; il backend emette firme e registra eventi.
4. **Moduli a piano, non flag sparsi**: tre moduli nuovi nel registro (`guide`, `corsi`, `prodotti`), ciascuno con tier per piano e un flag di emergenza per organizzazione. `legacy_commerce` non si riaccende mai.
5. **Commissione per riga**: la fee la decide il tipo di riga e il piano dell'organizzazione, non l'organizzazione da sola. Ritiri e servizi restano a zero per sempre; i tipi nuovi pagano la percentuale del piano (zero col Pro).

## 2. Pezzo per pezzo: riusa, adatta, rifai

| Pezzo | Stato | Verdetto | Perché |
|---|---|---|---|
| Registro tipi, validatori per tipo | solido | **riusa** | fonte unica, già usata dal checkout |
| Modelli Course / Module / Lesson / Resource | solido | **riusa** (+ `materiali` come digitali collegati, `ordine` già c'è) | gerarchia giusta, preview per lezione, scadenza accesso |
| IssuedCourseAccess, IssuedDownload, emissione alla conferma, revoca al rimborso | solido | **riusa** (+ campo `platform_account_id`, indice) | idempotenti, legati all'ordine, già nel `confirm_order` |
| Progresso lezione (`watched_seconds` monotono, `completed_at` fisso) | solido | **riusa** | esattamente ciò che serve per «riprendi da dove eri» |
| Firma URL Bunny (sha256 + scadenza 2h, margine 5') | solido | **riusa** | standard Bunny, già testata |
| Resolver librerie Bunny per lezione | solido | **adatta** | si aggiunge la libreria «gestita da Aurya» come voce con `managed=true` e priorità |
| Client Bunny | parziale | **estendi** | oggi legge soltanto: servono creazione libreria, upload (TUS/presigned), stato codifica, cancellazione |
| Verificatore Bunny (stato credenziali) | solido | **riusa** | utile per il pannello di regia |
| Download a token (streaming, contatore atomico, 410 a esaurimento) | solido | **adatta** | il file deve stare su storage durevole (volume o S3 privato), non nel container |
| Checkout condiviso (spedizione, indirizzo, coupon, piani di pagamento) | solido | **riusa** | già inline sul profilo per i servizi |
| Email di consegna («Vai al corso», file pronto) | solido | **adatta** | i link devono portare in `/account/...` dell'account Aurya, voce di Aurya |
| Editor corsi (1.156 righe), wizard digitale (863), wizard fisico (850) | funzionanti ma pesanti | **rifai in tre gesti** | troppi passi, lessico da gestionale, testi inglesi; il modello sotto resta |
| Dashboard digitali/fisici (1.000 righe l'una) | ridondanti | **non riportare** | i dati di vendita stanno già negli Ordini e nei numeri del gestionale |
| Player corsi legacy | funzionante | **rifai dentro /account** | deve usare l'account Aurya e l'identità grafica di oggi |
| Landing `/dg/`, `/co/`, `/ph/` | esistenti | **adatta** | shell SEO, JSON-LD, acquisto inline, stesso telaio delle landing dei ritiri |
| Vetrina `/s/{slug}` | morta | **lascia morta** | il profilo è il negozio |

## 3. Esperienza operatore: tre gesti, sempre

**Dove**: Strumenti → scheda «Guide e file» / «Corsi» / «Prodotti». Ogni scheda ha tre stati: *incluso nel tuo piano*, *attiva* (un clic, se il piano lo prevede), *in arrivo*. Appena attiva, compare la voce nel menu del gestionale, al posto giusto accanto a Listino.

**Prerequisiti risolti dentro il modulo, non prima**:
- *Incassi*: se Stripe non è collegato, il primo riquadro della scheda è «Collega gli incassi» con il bottone che apre l'onboarding Stripe Express. Niente da pubblicare finché non è verde. Oggi è il vero muro: zero operatori collegati.
- *Condizioni di vendita*: il template per-negozio viene precompilato con i dati del profilo (nome, partita IVA se c'è, email) e pubblicato con un solo «Confermo». Prodotti digitali e recesso sono già nel template.

**Una guida o un file** (lotto A): titolo, descrizione breve, copertina (facoltativa: si genera dalla copertina del profilo), file (PDF, ePub, audio, zip fino a 300 MB), prezzo, pubblica. Facoltativi dietro «Altro»: anteprima gratuita (prime pagine), numero massimo di scaricamenti, scadenza del link.

**Un corso** (lotto B):
1. *Il corso*: titolo, copertina, due righe di presentazione, prezzo, durata dell'accesso (per sempre, 12 mesi, 6 mesi).
2. *Le lezioni*: un elenco a trascinamento. Ogni lezione: titolo, video (si trascina il file: parte l'upload diretto a Bunny, si vede «in codifica» poi «pronto», la durata si legge da Bunny), materiali (un PDF, un audio: diventano file digitali inclusi), «anteprima gratuita». I moduli sono facoltativi: separatori con un titolo, per chi ha più di sei lezioni.
3. *Pubblica*: anteprima della landing e del player con un clic, poi «Pubblica». Si può salvare in bozza quante volte si vuole.

**Un prodotto fisico** (lotto C): titolo, foto, prezzo, quantità (o illimitato), spedizione (ritiro di persona, spedizione con costo fisso, consegna da concordare), pubblica. Gli ordini arrivano nel gestionale con gli stati di evasione già esistenti.

**Cosa vede dopo**: nel gestionale, Ordini mostra anche questi; in Corsi un riquadro «Studenti» per corso (quanti, a che punto, ultima lezione vista), senza grafici: numeri e nomi.

## 4. Esperienza studente: compra, trova, riprendi

1. Sul profilo dell'operatore, sezioni «Guide e libri», «Corsi», «Prodotti» sotto il listino, stesse card del listino. Clic → landing di dettaglio (programma del corso con le lezioni e le anteprime gratuite riproducibili senza acquisto, durata totale, chi insegna, prezzo, recensioni dell'operatore).
2. «Acquista» → checkout inline con l'account Aurya (già richiesto per contatti e, con R3, per ordinare): email, nome, carta. Stripe sul conto dell'operatore.
3. Email di conferma: «Il tuo corso è pronto» con un solo bottone → `/account/corsi/<id>`. Per i file: «Il tuo file è pronto» → `/account/file`.
4. In `/account`: due sezioni nuove, **I miei corsi** (card con barra di progresso e «Continua») e **I miei file** (nome, scaricamenti rimasti, bottone). Tutto cross-operatore, da qualunque dispositivo, con lo stesso login.
5. Il player: video grande, elenco lezioni a lato (sotto, da telefono), spunta automatica a fine lezione, «Prossima lezione», materiali della lezione scaricabili, «riprendi da dove eri» (secondo salvato). Link video firmati, rinnovati in silenzio prima della scadenza. Nessuna app, nessuna password in più.
6. Accesso scaduto o rimborsato: la card resta visibile con «accesso terminato», il video non parte, i materiali no. Niente sparizioni mute.

## 5. Dati e API, in breve

**Nuovo o modificato**
- `products`: nessuna modifica di schema; i tipi `digital`, `course`, `physical` tornano offerti dalla UI del modulo.
- `issued_course_accesses`, `issued_downloads`: `+ platform_account_id` (indice), `customer_account_id` resta per lo storico.
- `organizations.integrations.bunny_libraries[]`: `+ managed: bool`, `+ quota` (minuti caricati, GB al mese), `+ created_by: 'aurya'`.
- `organizations.application_fee_percent` → resta; si aggiunge `fee_per_tipo` **nel piano**: `{digital: 10, course: 10, physical: 10, service: 0, event_ticket: 0}` (Pro: tutti 0). La sessione Stripe calcola la fee sommando per riga; il registro delle commissioni salva la ripartizione.
- `modules`: tre chiavi nuove nel registro e nei tier dei piani (`guide`, `corsi`, `prodotti`); `feature_flags.{guide,corsi,prodotti}_spento` come interruttori di emergenza per organizzazione.
- Storage: `private_uploads` su volume Docker subito (A0); S3 privato con URL firmati quando si supera il singolo server.

**API** (tutte sotto i prefissi del modulo, con `require_module`)
- Operatore: `/guide/*` (crea, carica con URL firmato, pubblica), `/corsi/*` (corso, lezioni con riordino, upload Bunny: `POST /corsi/{id}/lezioni/{lid}/video` → credenziali TUS a scadenza; `GET .../stato` codifica), `/prodotti/*`.
- Studente (account Aurya): `/account/corsi`, `/account/corsi/{iscrizione}`, `/account/corsi/{iscrizione}/lezioni/{lid}/play-url`, `/account/corsi/{iscrizione}/progresso`, `/account/file`, `/account/file/{token}/scarica`.
- Pubblico: `/public/operator/{slug}` arricchito con `guide`, `corsi`, `prodotti` pubblicati (stessa cache di 45 s); landing per tipo; `/public/corsi`, `/public/guide` per le directory.
- Webhook Bunny (codifica finita) → stato lezione, durata.

## 6. Isolamento, sicurezza, scalabilità: le garanzie

**Isolamento**
- Un modulo spento non registra rotte nel frontend, non aggiunge voci di menu, non aggiunge sezioni al profilo, non entra nella sitemap. Il backend risponde 403 `MODULE_NOT_AVAILABLE` (meccanismo esistente).
- Il motore pagamenti cambia in un solo punto (fee per riga) con guardie su: ordine solo ritiri (fee 0 identica a oggi, byte per byte), ordine misto, rimborso parziale, Pro attivo, Pro scaduto.
- `confirm_order` già emette gli accessi per tipo: si aggiunge solo la chiave dell'account Aurya.
- Guardie di parità: registro moduli ↔ tier dei piani ↔ schede Strumenti ↔ menu; registro tipi ↔ wizard; rotte pubbliche ↔ `rotte.json`.

**Sicurezza**
- Video: URL firmati a 2 ore, rinnovo lato server, dominio di riproduzione limitato ai nostri (impostazione Bunny «allowed referrers»), nessun URL del file sorgente mai esposto, download disabilitato nel player Bunny.
- File: mai statici, sempre via token con contatore atomico e scadenza; limite dimensione; scansione del tipo MIME; nome file non indovinabile.
- Upload: credenziali firmate a scadenza, limiti per piano, mai la chiave API Bunny nel browser.
- Accessi: ogni richiesta studente verifica `platform_account_id` + stato (attivo, scaduto, revocato); rate limit sul play-url e sul download.
- Regia: ogni attivazione di modulo, cambio fee, revoca accesso con motivo e audit (lo stesso schema delle foto e delle discipline).

**Scalabilità e costi**
- Byte pesanti fuori dal server. Un corso da 10 lezioni × 15 minuti in 1080p ≈ 4-5 GB caricati una volta, ≈ 1,5 GB serviti per studente che lo guarda tutto: con Bunny circa 0,02 € di archivio al mese e 0,015 € per studente. Mille studenti ≈ 15 €. La commissione del 10% su un corso da 49 € ne vale 4,90.
- Indici: `(platform_account_id, status)` sugli accessi; `(organization_id, item_type, is_published)` sui prodotti per le sezioni del profilo; TTL sui token di upload.
- Cache: profilo pubblico 45 s come oggi; landing con la shell SEO già in cache.
- Quando serve il secondo server: lo storage privato passa a S3 con URL firmati (adapter già scritto per la parte pubblica), Bunny non cambia.

## 6-bis. Lotto S — Stripe giusto (il muro prima del muro)

**Il sintomo** (segnalato dagli operatori il 4/10): chi prova a collegare Stripe dall'Italia si ritrova un modulo che lo tratta come svizzero, con indirizzo svizzero e IBAN svizzero richiesti. Fuorviante, e infatti nessuno ha mai finito.

**La causa, verificata in prod.** La piattaforma Stripe di Aurya è registrata in **Svizzera** (paese CH, valuta CHF). Quando creiamo l'account Express dell'operatore (`stripe_connect_express._create_express_account`) non passiamo il paese: Stripe allora assegna **il paese della piattaforma**. I tre account collegati finora sono tutti `country=CH`, due in CHF e uno in EUR, nessuno completato; i requisiti che Stripe chiede loro sono quelli svizzeri. Il paese di un account Stripe **non si può cambiare dopo la creazione**. Nel nostro database `payment_connections` e `organizations` non hanno nemmeno un campo paese: 44 su 44 senza. In più chiediamo sempre la capacità TWINT, che ha senso solo in Svizzera.

**La correzione, isolata in un punto.**
1. **Il paese lo dice l'operatore, prima di andare da Stripe.** Nel riquadro «Collega gli incassi» (Impostazioni oggi, Strumenti domani) un select con **Italia preselezionata**, Svizzera e gli altri paesi UE dove Stripe Express esiste. Si salva su `organizations.country` e `payment_connections.country`, e viaggia nella creazione dell'account: `country`, `default_currency` coerente (EUR per IT, CHF per CH), `twint_payments` richiesta **solo** per CH. Il modulo Stripe parla italiano e chiede dati italiani.
2. **Ricomincia col paese giusto.** Per i tre account nati svizzeri (e per chiunque abbia un account non completato col paese sbagliato): un bottone «Ricomincia con il paese giusto» che, solo se Stripe dice `details_submitted=false` e `charges_enabled=false`, elimina l'account connesso via API, azzera la connessione e ne crea una nuova. Audit con motivo. Un account già operativo non si tocca mai: in quel caso il messaggio spiega e rimanda al supporto.
3. **Il webhook `account.updated` salva anche `country` e `default_currency`**, così la regia vede a colpo d'occhio chi è nato nel paese giusto, e il pannello Operatori mostra una colonna «Incassi: non collegato · in corso (IT) · pronto».
4. **Copy onesto nel riquadro**: «Stripe ti chiederà i dati della tua attività e l'IBAN del paese che scegli qui. Se sei in Italia lascia Italia.» E la riga di stato in italiano (oggi è «needs_auth»).

**Una verifica prima di promettere commissioni.** Piattaforma svizzera e operatore italiano con addebiti diretti funzionano (l'operatore incassa sul suo conto nel suo paese). La **commissione di piattaforma** su addebiti diretti tra piattaforma CH e account IT va provata in modalità test prima di scriverla nei piani: una sessione con `application_fee` su un account IT di prova, e si legge cosa risponde Stripe. Se Stripe la rifiuta tra paesi diversi, la via è una piattaforma Stripe italiana per Aurya (decisione societaria, non tecnica) oppure il modello «moduli nel Pro» senza commissione. Oggi la fee è zero, quindi il lotto S sblocca gli incassi comunque.

**Isolamento e sicurezza.** Si tocca una funzione (creazione account), un webhook (salvataggio paese), un endpoint nuovo (ricomincia, con le due condizioni di Stripe come lucchetto), un select nel riquadro. Il checkout, gli ordini, i rimborsi e il motore delle fee non cambiano. Guardie: il paese scelto arriva a Stripe; IT non chiede TWINT; CH sì; «ricomincia» rifiuta un account con `charges_enabled` o `details_submitted`; la copia è in italiano. Prova in modalità test con un account IT fino a «pronto».

**Tempo: 1 giorno**, e va fatto per primo: senza, né i ritiri né i corsi incassano. Ai tre operatori che hanno provato, una riga di cortesia dalla regia dopo il deploy: «Abbiamo corretto: ricomincia da Impostazioni, ora ti chiede i dati italiani».

## 7. I lotti, con i tempi veri

| Lotto | Contenuto | Giorni | Dipende |
|---|---|---|---|
| **S Stripe giusto** | paese scelto dall'operatore (Italia preselezionata) e passato a Stripe con valuta coerente; TWINT solo CH; «Ricomincia col paese giusto» per gli account non completati; paese nel webhook e nella regia; copy italiano; prova della commissione CH→IT in test | 1 | — |
| **A0 Fondamenta** | volume per `private_uploads`; «Collega gli incassi» negli Strumenti; condizioni per-negozio precompilate e pubblicate in un passo; fee per riga nel motore + piani con `fee_per_tipo` + testi (Termini, /costi, landing: «ritiri e servizi senza commissioni, sempre; guide, corsi e prodotti 10%, zero col Pro»); registro moduli con le tre chiavi e le schede «in arrivo» | 3 | S, decisioni 1 e 3 |
| **A Guide e file** | wizard in tre gesti; upload diretto; sezione sul profilo + landing `/dg/`; accessi su account Aurya; «I miei file» in `/account`; email; regia (vendite, revoca) | 3 | A0 |
| **B Videocorsi** | Bunny gestito (account Aurya, libreria per org via API, upload TUS, webhook codifica, quote); editor in tre gesti con lezioni a trascinamento e materiali; sezione sul profilo + landing `/co/` con anteprime; player in `/account/corsi` con progresso e rinnovo firme; email; regia studenti | 6 | A |
| **C Prodotti fisici** | wizard in tre gesti; spedizione e magazzino già pronti; sezione sul profilo + landing `/ph/`; stati di evasione nel gestionale | 2 | A0 |
| **D Directory** | `/guide`, `/corsi`, `/prodotti` con filtri per disciplina dal registro vivo, soglia minima di voci (come le pagine locali), sitemap, llms.txt, JSON-LD | 2 | contenuti veri |
| **Totale** | | **17** | |

Ogni lotto: suite al baseline, prova in locale, deploy separato, interruttore di emergenza, documento e memoria. A0+A si consegnano in una settimana e già vendono guide. B è il cuore dell'accademia e vale la settimana e mezza che costa. C e D sono brevi perché quasi tutto esiste.

## 8. Rischi veri e risposte

| Rischio | Risposta |
|---|---|
| Nessun operatore collega Stripe | la causa era il paese svizzero ereditato dalla piattaforma (lotto S); poi A0 lo mette come primo riquadro con un bottone; la regia vede chi non l'ha fatto; l'operatore pilota lo fa con noi al telefono |
| Commissione rifiutata tra piattaforma CH e account IT | prova in test nel lotto S, prima dei testi sui piani; vie d'uscita: piattaforma Stripe italiana o modello «moduli nel Pro» |
| L'operatore carica video enormi o in formati strani | limiti per piano, Bunny codifica tutto, stato «in codifica» visibile, email quando è pronto |
| Il player non parte su iPhone / Safari | iframe Bunny (HLS nativo), già usato; prova sui tre browser prima del rilascio come per il Lab |
| Rimborso dopo che il corso è stato visto | regola nelle condizioni per-negozio (recesso escluso per contenuti digitali avviati con consenso), revoca automatica dell'accesso al rimborso già esistente |
| Promessa «senza commissioni» | i testi cambiano prima della fee, e la distinzione è netta: ritiri e servizi restano a zero per sempre |
| Pirateria dei video | firma a scadenza + referrer limitati + nessun download: lo standard dei corsi online; il resto non vale il costo |
| Due identità cliente | tutto il nuovo su `platform_account_id`; il legacy si dismette al primo giro utile (zero iscrizioni storiche in prod) |
| Crescita dello storage | volume subito, S3 firmato quando serve, con l'adapter già previsto |

## 9. Decisioni per partire

1. **Modello economico**: 10% su guide, corsi e prodotti, zero col Pro, ritiri e servizi sempre a zero. Confermi la percentuale?
2. **Ordine**: A0 + A subito (una settimana, si vendono guide), poi B con l'operatore pilota; oppure B per primo se l'operatore ha già i video pronti.
3. **Bunny di Aurya**: apro l'account a nome Aurya; costi variabili come sopra.
4. **Directory**: dopo i primi contenuti veri, con soglia di tre voci come per le pagine locali.
