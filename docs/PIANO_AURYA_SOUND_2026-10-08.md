# Aurya Sound — da prodotto primordiale a luogo esperienziale che aggancia e monetizza

**Data:** 8 ottobre 2026 · **Stato:** piano v3, tutte le decisioni prese dal founder (§9): si parte da SN0 su «procedi»
**Richiesta del founder:** «Userò Crea per fare meditazioni gratuite come aggancio per gli iscritti. La parte meditazioni deve diventare un luogo esperienziale e facile da navigare, con playlist, come le app di meditazione. In futuro meditazioni o playlist bloccate per chi ha un abbonamento. Le meditazioni si usano anche nei corsi. Un pacchetto di meditazioni: meglio Meditazioni o Corsi? Tutto facile da gestire per me e da esplorare per chi ascolta. Con ricerca di mercato. In futuro un'app Android e iOS.»

---

## 1. La risposta in una pagina

**Aurya Sound diventa l'app di meditazione di Aurya, dentro il sito, con tre cerchi di accesso e una sola cassa.**

| Cerchio | Chi | Cosa ascolta | Cosa paga |
|---|---|---|---|
| **Aperto** | chiunque, anche senza email | l'assaggio di 90 secondi di ogni meditazione, il Lab, le schede del suono | niente |
| **Cerchio** | chi ha confermato l'email | **tutto il catalogo gratuito, per intero**, le playlist, i preferiti e il «riprendi da dove eri» (con l'account) | niente: è l'aggancio |
| **Più** (dal 2027) | chi sottoscrive l'abbonamento ascoltatore | tutto il Cerchio **più** le playlist e le meditazioni marcate «Più» | 39 €/anno (già nel piano business, P9) |

E **un pacchetto di meditazioni specifiche si vende come corso dell'Accademia**, con lezioni di tipo «Suono». Non si costruisce una seconda cassa dentro Sound: l'Accademia ha già account, Stripe, commissione per riga, pagina di vendita, directory, categorie, email, regia. In Sound il pacchetto compare come «Percorso» e porta alla pagina del corso. Tre parole, tre oggetti, niente ambiguità:

- **Meditazione** = una traccia (gratis col Cerchio, o «Più»).
- **Playlist** = una raccolta curata di meditazioni, con copertina e ordine (gratis col Cerchio, o «Più»).
- **Percorso** = un corso a pagamento con dentro meditazioni, video, testi, allegati (Accademia).

Cosa cambia per chi ascolta: una **casa delle meditazioni** che si esplora come un'app (una «di oggi» in cima, righe per obiettivo e durata, playlist, ricerca, preferiti, riprendi), copertine vere, il player che passa da sola alla prossima. Cosa cambia per te: in Crea crei playlist, metti una copertina, scegli cosa va in vetrina, vedi gli ascolti. Tutto il resto, motore, Lab, Crea Studio, Professional, non si tocca.

---

## 1-bis. La promessa: consolidare, non rifare

Oggi comporre e ascoltare funzionano bene. Il piano **non tocca** il motore (synth, ponte, veglia, continuo, anello, render), il cancello del Cerchio, Crea Studio, le tracce riservate, il Lab, Professional, il player dei corsi. Le novità sono **dati e vetrina**: campi nuovi sulle tracce, una collezione nuova per le playlist, pagine nuove sopra le stesse API.

Come si garantisce, onda per onda:
- ogni campo nuovo è **facoltativo con un default** (una traccia senza copertina ha il fallback, senza `accesso` è «cerchio», senza playlist resta nel catalogo come oggi): nessuna migrazione che riscriva le tracce esistenti;
- le pagine nuove nascono **accanto** alle vecchie dietro un flag (`SOUND_CASA_NUOVA`) e si scambiano solo quando la prova dal vivo è passata; `/frequenze/:slug` resta lo stesso URL con lo stesso cancello;
- i test di casa (motore, cancello, Crea, condivisioni, Lab, esperienze, parità frontend/backend dei cataloghi) restano la suite di regressione; ogni onda aggiunge i suoi;
- prova dal vivo prima del deploy su: una meditazione pubblicata, una riservata con link, un corso con lezione Suono, Calm/Ground/Respiro, il Lab, su telefono e desktop;
- deploy a onde brevi, mai tutto insieme, solo su «deploy».

## 2. Dove siamo (fatti dal codice, 8/10/2026)

Il prodotto ha un **motore eccellente** e una **vetrina primordiale**.

**Quello che c'è e funziona**
- Le meditazioni sono ricette (≈581 byte), il server non fa calcoli per ascolto; il master mp3 viene renderizzato dal browser di chi compone e custodito su disco; il costo marginale per ascolto è zero (docs Scalabilità ed Economia).
- Il cancello è giusto e provato: **assaggio di 90 s per tutti → email confermata → ascolto intero** (converte 2 su 2 secondo il piano business); una sola prova (`lib/cerchio.js`), controllo server (`_has_catalog_access`), master dietro nginx.
- Crea Studio: privilegio per org (chiave manuale o Pro), tracce riservate con link revocabili, voce registrata in app, spazi, guida del respiro, visual.
- Mobile: avviso cuffie, wake lock, ascolto continuo a schermo bloccato via file pre-renderizzato, ponte audio iOS.
- Corsi: la lezione «Suono» esiste (AU, 8/10): una traccia tua dentro un corso, solo le tue, solo col privilegio.

**Quello che manca per essere «un'app di meditazione»**
1. **Un solo asse di scoperta**: `intent` (6 valori). Niente ricerca, niente durata, niente tag, niente ordinamento; le tab compaiono solo con più di un intento. Con 1 meditazione pubblicata oggi, il catalogo è una lista.
2. **Niente copertina**: il modello della traccia non ha un'immagine; le card sono testo su un colore.
3. **Niente playlist/serie** per chi ascolta; i «percorsi» esistono solo lato Professional.
4. **Niente vetrina**: la meditazione in home di /sound è una costante nel codice (`VETRINA_SLUG`).
5. **Niente misura**: solo `plays_total`; nessun evento di avvio/completamento/provenienza.
6. **Niente «tuo spazio»**: preferiti sì (con account), ma nessun «riprendi», nessuno storico, nessuna «di oggi».
7. **Niente paywall ascoltatore**: previsto nel piano business (P9, 39 €/anno, seconda metà 2027), nessun codice.
8. **Niente app**: PWA analizzata ad agosto, mai costruita (nessun manifest né service worker, icona 511×512).

---

## 3. Ricerca di mercato: come fanno gli altri

| App | Modello | Prezzo | Cosa insegna ad Aurya |
|---|---|---|---|
| **Insight Timer** | freemium con la più grande libreria gratuita (250k tracce, 17k insegnanti); MemberPlus per corsi e offline; **agli insegnanti il 40% delle entrate, ripartito sugli ascolti** | 9,99 $/mese · 59,99 $/anno | il gratis generoso vince l'acquisizione; la community di insegnanti è il catalogo; la quota sugli ascolti è il modello della «libreria a pagamento» del tuo piano 2028 |
| **Calm** | premium con gratis sottile; il **Daily Calm** (10 min, ogni mattina) è il rito che tiene; Sleep Stories con voci note; libreria per obiettivo (sonno, ansia, focus…) | 16,99 $/mese · 69,99–79,99 $/anno | serve una «di oggi»; organizzare per obiettivo e momento; le serie con un volto |
| **Headspace** | premium, gratis quasi solo tour | 12,99 $/mese · 69,99 $/anno | non è la nostra strada: senza marca mondiale il muro sottile non converte |
| **Petit BamBou** (il riferimento in Italia) | gratis «Scoperta» (programmi introduttivi, 3 meditazioni quotidiane, respirazione) + abbonamento | 6,99–8,99 €/mese · 39,99–59,90 €/anno · 240 € a vita | l'ancora di prezzo italiana: **39–60 €/anno**; il gratis di scoperta con poche meditazioni «quotidiane» |
| **Serenity** | tutto a pagamento | 19,99 € ogni 6 mesi | prezzo basso, nessun gratis: non per noi |
| **Medito** | gratis per sempre, non profit, donazioni | 0 | il gratis totale esiste e fa numeri: la nostra versione è «gratis col Cerchio» |
| **Balance** | onboarding che chiede obiettivo, esperienza, umore e compone la seduta del giorno | abbonamento | tre domande all'ingresso bastano per personalizzare |
| **Waking Up** | premium alto + borsa di studio per chi non può pagare | 129,99 $/anno | la generosità dichiarata è marketing |
| **Creator su Gumroad/Podia** | pacchetti di 6–20 meditazioni venduti una tantum | **17–59 $** a pacchetto | un Percorso Aurya da 5–7 meditazioni a **19–29 €** è nel mercato |

Fonti: [Insight Timer review 2026](https://www.choosingtherapy.com/insight-timer-review/) · [Insight Timer, come guadagnano gli insegnanti](https://help.insighttimer.com/support/solutions/articles/67000664874-how-can-teachers-earn-revenue-from-their-work-) · [Calm vs Headspace vs Insight Timer 2026](https://unstar.app/blog/calm-headspace-insight-timer-balance-ten-percent-happier-meditation-apps-ranked-2026) · [Calm, contenuti gratuiti](https://support.calm.com/hc/en-us/articles/360044707294-What-Free-Content-is-Available-on-the-Calm-App) · [Calm review 2026](https://carepaths.com/calm-app-review/) · [Petit BamBou prezzi 2026](https://www.spliiit.com/en/blog/petit-bambou-avis-prix-abonnement) · [App per meditare, Aranzulla](https://www.aranzulla.it/app-per-meditazione-1383085.html) · [Medito](https://meditofoundation.org/free-meditation-app/) · [Best meditation apps 2026](https://www.itechguides.com/best-meditation-apps-2026-top-picks-by-goal-free-tier-and-price/) · [Calm onboarding e UX](https://screensdesign.com/apps/calm/) · [Calm UX case study](https://usabilitygeek.com/ux-case-study-calm-mobile-app/) · [Gumroad, meditazioni](https://gumroad.com/audio/sleep-and-meditation) · [Teal Swan bundle](https://tealswan.gumroad.com/l/mGZa) · [Capacitor audio in background](https://capgo.app/blog/how-to-play-audio-in-the-background-in-capacitor/) · [Limiti PWA su iOS 2026](https://www.magicbell.com/blog/pwa-ios-limitations-safari-support-complete-guide)

**Sei regole che il mercato insegna, applicate ad Aurya**
1. **Il gratis generoso acquisisce, il rito trattiene.** Aurya ha già il gratis (col Cerchio); manca il rito: la «Meditazione della settimana» e la «di oggi» in cima alla casa.
2. **Si sceglie per obiettivo, durata e momento.** Gli intenti ci sono; mancano durata (5 · 10 · 20 · 30+) e momento (mattina, pausa, sera, notte).
3. **La copertina è metà della scelta.** Tutte le app vivono di immagini; noi oggi non abbiamo il campo.
4. **Le serie hanno un volto.** La tua voce e la tua faccia (la foto dei fondatori c'è già) sono il «Tamara Levitt» di Aurya.
5. **L'ancora di prezzo in Italia è 39–60 €/anno.** Il 39 €/anno del piano business è il punto basso giusto per entrare; i pacchetti una tantum stanno fra 19 e 29 €.
6. **Chi crea vuole una quota sugli ascolti.** Insight Timer dà il 40%: quando aprirai la libreria a pagamento agli operatori (2028), il 30% indicativo del piano business è conservativo ma leggibile.

---

## 4. L'architettura dell'esperienza

### 4.0 Prima di aggiungere: togliere. La mappa di Sound, prima e dopo

Oggi chi arriva su Sound trova **dodici porte sullo stesso piano**: la landing `/sound`, Esplora (36 schede di frequenze), Impara e il glossario, cinque stanze del Lab più i percorsi del Lab, tre esperienze, le Meditazioni, Visual, Professional, Studio, Crea, Le mie tracce, Pro. Sono due prodotti e un atelier mescolati: **chi vuole meditare** e **chi vuole capire il suono**, più **chi compone**. La confusione nasce da lì, non dal numero di funzioni.

**Dopo: tre porte, con la gerarchia giusta.**

| Porta | Per chi | Cosa contiene | Dove sta nel menu |
|---|---|---|---|
| **Meditazioni** (la casa, §4.1) | chi vuole ascoltare | catalogo, playlist, Di oggi, il tuo spazio. Solo meditazioni nate in Crea: **Calm, Ground e Respiro si ritirano** (decisione 7: non sono meditazioni create con Crea); i loro URL rimandano a `/meditazioni`, escono da `/sound`, dalla shell, dalla sitemap e da llms.txt; il codice resta una release come dismesso, poi si pota | voce principale, barra in basso su telefono |
| **Il suono** (`/sound`, la landing di sistema ridotta a un hub) | chi vuole capire | tre riquadri: Esplora le frequenze (le schede), Impara (fondamenta e glossario), Il Lab (le cinque stanze). Visual diventa uno strumento dentro il player (Aurya Mode), non una porta | seconda voce, sottovoce |
| **Crea** | chi compone (privilegio) | Crea, Le mie tracce, Playlist, Ascolti; Professional e Studio restano pagine di vendita raggiungibili dal gestionale, non dal pubblico | solo per chi ha la chiave, dall'omino dell'account |

Regole di semplificazione:
- **una passerella sola**: Meditazioni · Il suono (· Crea per chi può). Via la doppia navigazione (passerella + stanze); le stanze diventano la navigazione interna dell'hub «Il suono».
- **una sola home**: `/sound` non è più «la landing» con hero e vetrina duplicata rispetto a `/meditazioni`; la vetrina vive in Meditazioni; `/sound` racconta il suono e rimanda.
- **una parola per cosa**: Meditazione, Playlist, Percorso, Scheda (le frequenze), Stanza (il Lab).
- **Crea resta com'è** (decisione 8: «Crea in tre gesti», l'ingresso guidato sopra il compositore, si riprende più avanti).
- **le informazioni al posto giusto**: avvisi (cuffie, memoria, controindicazioni) una volta sola, nel momento in cui servono, mai sulla pagina del catalogo.

### 4.1 La casa delle meditazioni (`/meditazioni`, ridisegnata come un'app)

Dall'alto in basso, su telefono e desktop:

1. **Di oggi** — una card grande: la meditazione o playlist in vetrina (decisione 1: si ascolta intera **solo col Cerchio**, per tutti resta l'assaggio di 90 s) oppure, per chi è nel Cerchio con account, il «riprendi da dove eri».
2. **Per te in tre tocchi** — PREDISPOSTO, NON COSTRUITO (decisione 2): i campi `sound_preferenze` {obiettivo, durata, momento} nascono sull'account e sul browser, l'interfaccia delle tre domande arriverà dopo uno studio dedicato.
3. **Righe orizzontali** (carosello su telefono, griglia su desktop): Playlist · Per dormire · Per iniziare (≤10 min) · Novità · Le più ascoltate · Con la voce · Solo suono · Percorsi (i corsi con meditazioni, se esistono). Nessuna «Esperienza»: Calm, Ground e Respiro si ritirano (decisione 7).
4. **Cerca e filtra**: testo (titolo, descrizione, chi la guida), intento, durata, voce/senza voce, playlist.
5. **Il tuo spazio** (con account): Preferiti · Riprendi · Ascolti recenti.

**Barra fissa in basso su telefono** (la stessa logica dell'account, verde e oro): Esplora · Playlist · Cerca · I tuoi · Impara. Da desktop resta la passerella.

### 4.2 La pagina della meditazione (`/frequenze/:slug`)
Copertina grande, titolo, chi la guida, intento · durata · voce; il player con il «parte di: Playlist X · 3 di 7» e **avanti/indietro** dentro la playlist, **passa alla prossima da sola** a fine traccia (spegnibile); sotto, la descrizione, «Altre di questa playlist», «Altre per dormire». Il cancello resta identico (90 s, poi Cerchio), ma con la copertina e la playlist in vista: si capisce cosa si sta sbloccando.

### 4.3 La pagina della playlist (`/meditazioni/playlist/:slug`)
Copertina, titolo, racconto breve, durata totale, numero di meditazioni, «Ascolta tutta» (parte dalla prima, continua da sola), l'elenco ordinato con durata e assaggio. Se è «Più»: badge e invito, il gratis non cambia.

### 4.4 Lato tuo: Crea
- **Copertina** per ogni traccia e playlist (foto tue, decisione 4: caricate e compresse in browser come le foto dei prodotti); il fallback generato (gradiente per intento + titolo) resta solo come rete di sicurezza per una traccia senza foto.
- **Durata e voce** si leggono dalla ricetta; **momento** e **tag** (facoltativi) si scelgono.
- **Playlist**: nuova scheda in «Le mie tracce»: titolo, racconto, copertina, ordine con le frecce (come le lezioni), visibilità (Cerchio · Più) e «In vetrina».
- **Gratuita o Più: un interruttore per traccia e per playlist.** In «Le mie tracce» ogni riga ha il chip dell'accesso: **Cerchio** (default: gratuita per chi è nel Cerchio) oppure **Più** (per gli abbonati). Si cambia con un clic, vale subito: la pagina della meditazione mostra il badge e il cancello giusto. Finché l'abbonamento non è acceso (flag `SOUND_PIU_ATTIVO`), il chip «Più» si può impostare ma la meditazione resta ascoltabile col Cerchio e mostra «Presto nel Più»: così prepari il catalogo prima del lancio senza nascondere nulla. Una playlist «Più» può contenere tracce gratuite (l'assaggio è la playlist stessa); una traccia «Più» dentro una playlist gratuita si vede, con il badge, e si ascolta per 90 s.
- **In vetrina / Della settimana**: due interruttori, non più una costante nel codice.
- **Ascolti**: per traccia e playlist, avvii, completamenti, da dove (home, playlist, condivisione, corso).

### 4.5 Il gancio verso il Cerchio e verso l'account (la scala di FARO resta)
- Email = chiave del contenuto; account = chiave della persistenza. Nessun doppio invito, nessun popup, il gratuito resta gratuito.
- Aggiunte: la card «Entra nel Cerchio» con la **copertina della meditazione che stai per sbloccare**, e le **card social** (OG image) per traccia e playlist. Niente ascolto intero senza email (decisione 1): l'aggancio resta il Cerchio.
- L'email del Cerchio annuncia la nuova meditazione o playlist con il link diretto (la sequenza esiste già; va aggiunto il modello «nuova meditazione»).

---

## 5. I meccanismi: cosa si vende, dove, come

| Oggetto | Dove si crea | Dove si vede | Accesso | Cassa |
|---|---|---|---|---|
| Meditazione gratuita | Crea → Pubblica | /meditazioni, /frequenze/:slug, home /sound, email del Cerchio | 90 s per tutti; intera col Cerchio | nessuna: aggancio |
| Playlist gratuita | Crea → Playlist | /meditazioni (riga Playlist), pagina playlist | come sopra | nessuna |
| Meditazione / Playlist **Più** (2027) | Crea, interruttore «Più» | come sopra, col badge | abbonamento ascoltatore | Stripe, 39 €/anno (P9) |
| **Percorso** a pagamento | Accademia → corso con lezioni Suono (+ video, testi, allegati) | /corsi, /corso/{org}/{slug}, profilo, e in Sound nella riga «Percorsi» | chi compra, nel suo account | Stripe, commissione 15% Gratis / 0% Pro (già vivo) |
| Traccia riservata a un cliente | Crea → Riservata + link | /ascolta/:token | il link | nessuna (strumento del professionista) |
| Meditazione nei corsi di altri operatori | la loro Crea (Pro) | nei loro corsi | i loro studenti | la loro cassa |

**Perché i pacchetti vanno nei corsi e non in Sound**
- Un pacchetto è un acquisto una tantum con diritto d'accesso nominale: è esattamente l'iscrizione a un corso (account, Stripe, fee, rimborso, revoca, email, regia, directory per categoria). Rifarlo in Sound vorrebbe dire due casse, due account, due pagine di vendita, due regie.
- Un corso può contenere **anche** un video introduttivo, un pdf, testi: il pacchetto diventa più ricco senza costi.
- La Meditazione resta un oggetto gratuito o da abbonamento: la gente capisce «ascolto gratis / mi abbono / compro un percorso», non «questa singola traccia costa 3 €».
- Conseguenza pratica: in Sound la riga «Percorsi» mostra le card dei corsi che hanno almeno una lezione Suono (campo `categoria` e `has_suono` già calcolabili), con «Scopri» verso la pagina del corso.

**L'abbonamento Più (quando ci sarà)**: nasce sull'account Aurya, Stripe Billing, 39 €/anno (o 4,99 €/mese se vorrai un mensile), un flag `sound_piu_until` sull'account; il cancello passa da `email confermata` a `email confermata OR piu` per i contenuti marcati «Più». Tutto il gratuito resta gratuito (regola FARO). Termini: una voce nuova quando si accende, non prima. Prepariamo il modello (campo `accesso` su tracce e playlist, badge, componente «invito Più» spento dietro flag) così il giorno dello sblocco è un interruttore, non un cantiere.

---

### 5.2 L'abbonamento Più: la meccanica completa (quando si accende)

Vive **sull'account Aurya** (lo stesso dei corsi, dei file, delle prenotazioni), **non** sull'org e **non** sul Cerchio: l'email del Cerchio resta la chiave del gratuito, l'account è la chiave di tutto ciò che si paga o si conserva. Si riusano gli stessi binari del billing degli operatori (`routers/billing.py`: Stripe Checkout in modalità abbonamento, Customer Portal, webhook, sweep di riconciliazione), scritti una seconda volta per l'account piattaforma e non per l'organizzazione.

1. **Catalogo Stripe**: un prodotto «Aurya Sound Più» sull'account Stripe di Aurya (non Connect: è Aurya che vende), **un solo prezzo: annuale 39 €** (decisione 5); IVA gestita da Stripe Tax; ricevute e fatture da Stripe.
2. **Checkout**: da una meditazione o playlist «Più», o dalla pagina `/meditazioni/piu`, il pulsante «Abbonati» → se non hai l'account, la porta unica `/accedi` (email + codice, come per i corsi) → `POST /platform/me/piu/checkout` crea la Checkout Session (modalità `subscription`, `customer` = il cliente Stripe dell'account, creato alla prima volta e salvato in `stripe_customer_id` dell'account) → Stripe → ritorno su `/account#sound` con «Benvenuto nel Più».
3. **Verità**: i webhook `checkout.session.completed`, `customer.subscription.updated/deleted`, `invoice.paid`, `invoice.payment_failed` scrivono sull'account `piu = {status, stripe_subscription_id, current_period_end, cancel_at_period_end}`; come per i prodotti, il ritorno dal checkout fa anche una **verifica immediata** (non si aspetta il webhook) e uno **sweep** notturno riconcilia gli scaduti.
4. **Il cancello**: `_has_catalog_access` impara una seconda domanda: per i contenuti «Più» serve `account.piu.status in (active, trialing, past_due entro il periodo)`; per il resto basta il Cerchio. Un solo punto di decisione, come oggi.
5. **Gestione dall'account** (`/account` → sezione «Aurya Sound Più»): stato, prossimo rinnovo, importo, «Cambia carta» e «Disdici» → aprono il **Customer Portal di Stripe** (`POST /platform/me/piu/portal`), dove la persona disdice da sola; la disdetta vale a fine periodo (`cancel_at_period_end`), il contenuto resta fino alla scadenza, poi torna il Cerchio senza perdere preferiti, riprendi e storico. Email: conferma, rinnovo, pagamento fallito (grace di 7 giorni), disdetta ricevuta.
6. **Regia**: nella tab Utenti del system admin la colonna «Più» (stato, dal, scade), il conteggio degli abbonati e le entrate del mese; un interruttore per regalare il Più a un account (`piu_omaggio_until`) per prove e ambasciatori.
7. **Termini e /costi**: una voce nuova nei Termini per il cliente finale (il Più è un servizio di Aurya, 14 giorni di recesso sul digitale con l'eccezione dell'avvio immediato), `/costi` resta per i professionisti; la pagina `/meditazioni/piu` dice il prezzo. Il bump dei Termini si fa all'accensione, come per l'Accademia.
8. **Nell'app degli store** (§8): l'abbonamento si compra con StoreKit/Play Billing (commissione 15–30%), e un webhook dei negozi scrive lo stesso campo `piu` sull'account: un solo stato, due casse. Sul web resta Stripe.

Scalabile perché: lo stato vive in un campo solo, letto da un solo cancello; Stripe tiene la verità del denaro; il portale toglie il supporto manuale; l'omaggio e la regia sono già nel disegno; la stessa meccanica, domani, serve per un secondo abbonamento (es. l'Accademia) senza riscrivere nulla.

## 6. Modello dati (additivo, nessuna migrazione distruttiva)

**`frequency_tracks`** (+campi):
- `cover_url` (immagine caricata, come le copertine dei corsi), `momento` (mattina · pausa · sera · notte, facoltativo), `tags[]` (≤8), `has_voce` (derivato dalla ricetta al publish), `accesso` (`cerchio` | `piu`, default `cerchio`), `in_vetrina` (bool), `della_settimana_dal` (data, facoltativa), `guida_nome` (chi guida, default nome dell'org).
- Analitica: collezione `sound_ascolti` {track_id, playlist_id?, provenienza, avvio_at, quartili raggiunti, completato, account_id?, prova_hash?}; aggregati giornalieri per la dashboard.

**`sound_playlists`** (nuova): {id, organization_id, title, slug, slug_precedenti[], description, cover_url, intent?, tracce[] (slug ordinati), accesso (`cerchio`|`piu`), in_vetrina, status (`draft`|`published`), published_at, plays_total}.
- Regole: solo tracce **pubbliche e dell'org** (stessa guardia di `_traccia_mia`); una playlist pubblica richiede la chiave 1 (`sound_composer`), come le tracce pubbliche; una traccia può stare in più playlist; la playlist esce dal catalogo se resta senza tracce pubblicate.

**Account** (+campi): `sound_preferenze` {obiettivo, durata, momento}, `sound_riprendi` {slug, secondo}, `sound_recenti[]` (ultime 20), `stripe_customer_id`, e `piu` {status, stripe_subscription_id, current_period_end, cancel_at_period_end, omaggio_until} (vuoto finché il Più non si accende).

**Registro rotte**: `meditazioni/playlist/:slug` (pubblica), meta nella shell (CollectionPage), sitemap.

---

## 7. Il piano in onde (lotto «SN», Sound Nuovo)

Ogni onda: isolata, dietro flag dove tocca il pubblico, con guardie nei test, zero regressioni sul motore e su Crea; prova dal vivo sul corso/catalogo demo; commit; deploy solo su «deploy».

| Onda | Cosa | Giorni |
|---|---|---|
| **SN0 Fondamenta e mappa** | campi nuovi su tracce e account (tutti facoltativi, default = oggi); collezione playlist + API (lista, crea, ordina, pubblica, ritira, copertina); il chip **Cerchio/Più** per traccia e playlist (senza cancello finché il Più è spento); eventi di ascolto; le parole ufficiali; la **mappa a tre porte** decisa e scritta (quali URL restano, quali rimandano) | 2 |
| **SN1 La casa e la passerella** | `/meditazioni` ridisegnata (Di oggi, righe, ricerca e filtri, barra in basso su telefono), le tre esperienze come card dentro la casa, pagina playlist, pagina della meditazione con playlist e «prossima da sola», copertine con fallback generato, card social; **la passerella unica** (Meditazioni · Il suono · Crea) e `/sound` ridotto a hub del suono, dietro flag e con i vecchi URL che rimandano | 3,5 |
| **SN2 L'aggancio** | la vetrina a rotazione (intera solo col Cerchio), il cancello con la copertina e la playlist in vista, le card social, l'email del Cerchio «nuova meditazione / nuova playlist»; i campi delle preferenze predisposti senza interfaccia; il ritiro di Calm, Ground e Respiro con i rimandi | 1,5 |
| **SN3 Il tuo spazio** | riprendi da dove eri, ascolti recenti, preferiti nella casa, «I tuoi» nella barra; lato tuo la dashboard «Ascolti» in Crea («Crea in tre gesti» rimandato, decisione 8) | 2 |
| **SN4 La cassa pronta** | riga «Percorsi» in Sound (corsi con lezioni Suono); il badge Più e l'invito spento dietro flag; l'ossatura dell'abbonamento già scritta e provata in test Stripe (prodotto, checkout, webhook, portale, sezione nell'account, colonna in regia) ma **spenta** (`SOUND_PIU_ATTIVO=false`); testi di `/costi`, `/meditazioni/piu` e la voce dei Termini preparati, non applicati | 3 |
| **SN5 L'app** (più in là, decisione 6) | predisposizione dentro SN0–SN4: ogni meditazione e playlist ha il master pronto, i metadati per la Media Session, l'icona 512 vera e il colore tema; passo 1 PWA installabile e passo 2 guscio Capacitor con audio nativo si fanno quando lo deciderai | — |

Totale fino a SN4: **~11 giorni**. L'accensione del Più, quando vorrai, è un giorno: flag, bump dei Termini, prezzo vero in Stripe, annuncio al Cerchio.

**Cosa NON si fa** in questo lotto: nessun cambio al motore, a Crea Studio, al Lab, a Professional; nessun paywall acceso; nessuna cassa nuova; nessuna notifica push; nessun gioco a punti (streak aggressivi, badge): il rito di Aurya è la Meditazione della settimana, non la pressione.

---

## 8. L'app Android e iOS: come arrivarci senza rifare nulla

**Il vincolo tecnico** (documentato ad agosto): i browser sospendono WebAudio a schermo bloccato; il motore che sintetizza dal vivo funziona a schermo acceso; l'ascolto a schermo bloccato funziona solo col file pre-renderizzato (il master). Una PWA non risolve il background su iPhone.

**La strada in due passi**
1. **PWA** (SN5 passo 1, ~1 giorno): installabile, icona, schermo intero, cache del guscio. Costo quasi nullo, ritorno immediato su Android.
2. **App di guscio** (Capacitor, lo stesso codice React) con **audio nativo** (AVFoundation su iOS, Media3 su Android, plugin tipo capacitor-native-audio + media session): l'app riproduce **i master mp3** delle meditazioni e delle playlist in background con i controlli sullo schermo bloccato; il motore dal vivo resta per Crea e per il Lab dentro la WebView. Richiede account sviluppatore Apple (99 $/anno) e Google (25 $), la revisione degli store, e un giorno di lavoro sui pagamenti: **gli store pretendono l'acquisto in-app per gli abbonamenti digitali** (30% / 15% di commissione): l'abbonamento Più nell'app passa da StoreKit/Play Billing, sul web da Stripe. Questo va deciso prima di accendere Più.

**Prerequisito che il piano già pone**: ogni meditazione pubblicata ha il master (già oggi) e ogni playlist è una sequenza di master: l'app non deve inventare nulla. Quando gli ascolti supereranno la banda del VPS (170k ascolti/mese secondo le stime di agosto) i master passano su un CDN di storage (Bunny Storage, già conosciamo Bunny): un giro di infrastruttura, non di prodotto.

---

## 9. Decisioni del founder (8/10/2026)

1. **Niente ascolto intero senza email**: l'aggancio resta il Cerchio; la «Meditazione della settimana aperta a tutti» è tolta dal piano. Per tutti resta l'assaggio di 90 s.
2. **Le tre domande all'ingresso**: il sistema si predispone (campi delle preferenze), l'interfaccia no; si studia più avanti con precisione.
3. **Playlist pubbliche solo del founder** (chiave 1), come le meditazioni pubbliche.
4. **Copertine**: le foto le mette il founder; il fallback generato resta solo come rete di sicurezza.
5. **Più**: 39 €/anno, solo annuale.
6. **App**: si predispone (master, metadati, icona, colore), si costruisce più in là.
7. **Calm, Ground e Respiro si ritirano**: non sono meditazioni create con Crea. Rimandi a `/meditazioni`, fuori da `/sound`, shell, sitemap e llms.txt; codice dismesso per una release, poi potato.
8. **«Crea in tre gesti»**: rimandato, si riprende più avanti. Il compositore resta com'è.

## 10. Appendice: le guardie di coerenza

- Le parole: «Meditazione», «Playlist», «Percorso», «Cerchio», «Più». Mai «traccia» nel pubblico (resta nel gestionale), mai «playlist» per i corsi, mai «corso» per una playlist.
- Il gratuito resta gratuito: nessuna meditazione oggi gratuita diventa «Più» (regola FARO).
- Una sola cassa per gli acquisti una tantum: l'Accademia.
- Una sola prova per il Cerchio: `lib/cerchio.js`; il controllo server resta `_has_catalog_access`, che un giorno conoscerà anche «Più».
- Il motore non cambia: le novità sono dati e vetrina.
- Ogni onda ha i suoi test: modello, API, pin dei testi, rotte nel registro, meta nella shell.

---

## 11. Stato

**SN0 Fondamenta IMPLEMENTATO in locale (8/10/2026).** Nessun campo obbligatorio, nessuna migrazione, motore e cancello intatti.
- **Tracce**: `cover_url`, `accesso` (cerchio|piu, default cerchio), `momento`, `tags` (≤8), `in_vetrina`, `guida_nome`, `has_voce` (materializzato alla pubblicazione); `PATCH /frequencies/tracks/{id}` li accetta tutti facoltativi; `POST/DELETE /tracks/{id}/copertina` (jpg/png/webp ≤5 MB, storage pubblico `uploads/frequenze` come le copertine dei corsi). Lista, catalogo e payload pubblico portano i campi; gli scartati tornano al default (accesso ignoto → cerchio).
- **Playlist** (`routers/sound_playlists.py`, collezione `sound_playlists`): crea/modifica/ordina/copertina/pubblica/ritira/togli sotto `require_sound_crea`; **solo tracce proprie, pubblicate, non riservate** (le bozze cadono in silenzio, provato: 2 su 3); **pubblicare è della chiave 1**; slug dal titolo con i precedenti; pubblico `GET /frequencies/playlists` e `/{slug}` dietro **lo stesso cancello del catalogo** (403 `locked` + conteggio); solo pubblicate con almeno una traccia viva; contatore `plays_total`.
- **Eventi di ascolto** (`sound_ascolti`): `POST /public/{slug}/ascolto` {evento avvio|q25|q50|q75|fine, provenienza, playlist, secondo}, 120/min per IP, anonimo (account se Bearer piattaforma, mai IP/UA); `GET /tracks/{id}/ascolti` per il gestionale (eventi, provenienze, % completamento). Il player manda `avvio` al primo play e i quartili dal tempo mostrato; la provenienza viaggia in `?da=` e `?playlist=`.
- **Account**: campi predisposti (`sound_preferenze`, `sound_riprendi`, `sound_recenti`, `stripe_customer_id`, `piu`), nessuna interfaccia.
- **Crea → Le mie tracce**: su ogni traccia copertina (foto compressa in browser), momento, tag; sulle pubbliche il chip **Cerchio · gratis / Più** e «In vetrina» (chiave 1). Sotto, **Le mie playlist**: titolo → editor (racconto, copertina, accesso, vetrina, le meditazioni in ordine con frecce, «+ Aggiungi»), Pubblica/Ritira/Togli. Provato dal vivo: playlist «Sere di respiro» creata, traccia aggiunta, pubblicata → `/meditazioni/playlist/sere-di-respiro`.
- guardie: `tests/test_sound_sn0.py`; pin del portiere aggiornato (+3 endpoint sotto `require_sound_crea`).

**SN1 La casa e la passerella IMPLEMENTATO in locale (8/10/2026, sera).** Tutto dietro `features/frequenze/stato.js` → `SOUND_CASA_NUOVA` (true in locale): le pagine vecchie restano accanto, intatte, e i 17 file di test che le leggono continuano a passare.
- **/meditazioni = la casa** (`casa/MeditazioniCasa.jsx` + `casa.css`): **Di oggi** (traccia o playlist `in_vetrina`, altrimenti la più recente, link `?da=vetrina`), **cerca** (titolo, racconto, guida, tag) e **filtri** (intenti presenti, ≤10 / 10–20 / 20+ min, con la voce / solo suono), le **righe** con copertina (Playlist · Le tue preferite · Per iniziare ≤10 min · Novità · Le più ascoltate · Per dormire/meditare/… · Con la voce · Solo suono; una riga vuota non si vede), card con durata, chip PIÙ, cuore (account, mai email), velo di tono per chi non ha copertina. **Barra in basso solo telefono** (Esplora · Playlist · Cerca · Preferite · Impara), sparisce da 900px. Catalogo e playlist si chiedono come prima (account → Bearer, altrimenti la prova del Cerchio); **la soglia è una**: `SogliaCerchio` estratta da MeditazioniPage.js e usata da vetrina vecchia, casa e playlist (ciclo d'import spezzato col lazy).
- **/meditazioni/playlist/:slug** (`casa/PlaylistPage.jsx`): copertina, racconto, conteggio e durata, «Ascolta tutta», elenco in ordine; 403 → soglia, 404 → «non c'è più». Shell SEO `_meta_playlist` (ItemList con le sole tracce vive, in ordine; bozza = 404) e sitemap core con le playlist pubblicate.
- **Il player sa di essere «parte di»**: con `?playlist=` striscia «Parte di … n di N» con prec./succ.; a fine traccia (master, continuo, synth; mai l'anteprima) passa da solo alla successiva con `?auto=1` e prova a partire (stesso documento, gesto già dato; se il browser nega resta il tasto). Cambio slug nella stessa rotta = ricarica piena (il motore non si rimonta a metà).
- **/sound = l'hub del suono** (`casa/SoundHubPage.jsx`, guscio chiaro): Esplora le frequenze · Le fondamenta · Il Lab, e «Vuoi ascoltare?» → /meditazioni. Visual fuori dal menu. La landing vecchia resta sotto il flag.
- **Passerella a tre porte** (SoundTopbar): Meditazioni · Il suono · Crea (solo con il cappello del professionista; il portiere della stanza decide poi). La vecchia `PASSERELLA` resta letterale per i pin.
- **Verificato dal vivo**: casa a 375px e desktop, cuore e preferite, cerca «onde» = 3, playlist, player con striscia e frecce, hub; **il percorso email è intatto**: `/meditazioni?prova=<token>` (il pulsante della Lettera) salva la prova prima del primo render (`index.js → raccogliProvaDaUrl`), pulisce l'indirizzo e apre la casa, la playlist e il player senza rimettere l'email. `CI=false npm run build` passa.
- guardie: `tests/test_sound_sn1.py` (+ pin DN2 intatto grazie al nome `CASA_PASSERELLA`).

**SN2 L'aggancio IMPLEMENTATO in locale (8/10/2026, sera).**
- **Vetrina a rotazione**: fra tutto ciò che è «in vetrina» (meditazioni e playlist, chip in Crea) ne esce una al giorno, la stessa per tutti, decisa dal giorno; senza nulla in vetrina, la più recente. Intera solo col Cerchio, come tutta la casa.
- **Il cancello con la copertina in vista**: `CancelloLettera` accetta `cover`, `titolo`, `playlist` (facoltativi; la landing non cambia): «Stai per sbloccare · Titolo» con la foto, e «Parte della playlist …» quando la playlist è leggibile.
- **Card social**: la meta della meditazione usa la copertina caricata (`_abs_image(cover_url)`, og:image); la playlist già la aveva da SN1.
- **L'annuncio al Cerchio** (`services/annunci_sound.py`): `POST /frequencies/tracks/{id}/annuncia` e `POST /frequencies/playlists/{id}/annuncia`, solo chiave 1, solo contenuto pubblicato e non riservato, **una volta sola** (il documento si marca `annuncio` prima di spedire, come il promemoria del Cerchio); `?a_secco=1` conta i destinatari e mostra l'anteprima; l'invio vero parte in background, un'email alla volta fuori dal loop, con link verificante + prova (apre già sbloccato), header List-Unsubscribe, destinatari = `filtro_sub()` delle sequenze (interruttore singolo opt-in rispettato). In Crea → Le mie tracce e nelle playlist: «✉ Annuncia al Cerchio» → prova a secco → conferma con il numero → invio → «Annunciata il … · N email». In locale senza chiave Brevo le email vanno in dry-run (conteggiate come errori: artefatto locale).
- **Il tuo spazio, predisposto** (decisione 2): `GET /platform/me` espone `sound_preferenze / sound_riprendi / sound_recenti`; `PATCH /platform/me/sound` li scrive con pulizia (obiettivo tra i sei intenti, durata breve/media/lunga, momento, recenti ≤20 senza doppi). Nessuna interfaccia: una guardia lo verifica.
- **Ritiro di CALM, GROUND e RESPIRO** (decisione 7): registro `rimandi` → nginx 301 esatti verso `/meditazioni` (nginx.conf rigenerato), shell noindex con il rimando, fuori dalla sitemap, via dalla home del suono per i crawler, SPA `Navigate` dietro il flag (le rotte in App.js restano letterali, dismesse). I pin dei test delle tre esperienze aggiornati alla nuova verità; il loro codice resta una release, poi si pota.
- guardie: `tests/test_sound_sn2.py`; pin `require_sound_crea` = 16.

**SN3 Il tuo spazio IMPLEMENTATO in locale (8/10/2026, sera).** La persistenza è dell'account: senza account non si salva nulla.
- **Il player salva il punto**: `POST /platform/me/sound/ascolto` {slug, secondo?, fine?}: al via la meditazione entra nei recenti (senza doppi, venti al massimo), ogni quindici secondi di ascolto si salva il secondo per «riprendi», alla fine «riprendi» si spegne (solo se era di quella traccia). Con `?t=secondo` il tasto dice «▶ Riprendi» e parte da lì (mai dagli ultimi cinque secondi).
- **La sezione «Il tuo spazio»** nella casa (con account, solo se ha qualcosa da dire): la card «Riprendi da dove eri» (copertina, titolo, 0:42 di 2 min), la riga «Ascolti recenti» (solo le meditazioni ancora in catalogo), la riga «Le tue preferite». Nella barra «Preferite» diventa **«I tuoi»**; senza account apre l'invito a creare l'account (preferite, recenti e riprendi su ogni telefono).
- **La dashboard «Ascolti» in Crea**: su ogni traccia pubblicata un bottone «▸ Ascolti · N» apre avvii, a metà, fino in fondo (%), e da dove si entra (la casa, la ricerca, di oggi, una playlist, le preferite, i recenti, riprendi, l'email del Cerchio…). Dati da `GET /tracks/{id}/ascolti` (SN0); si conta dall'8 ottobre.
- guardie: `tests/test_sound_sn3.py`; pin SN1 («I tuoi», `tuo-spazio`) e SN2 (il no-UI vale per le preferenze) aggiornati.

**SN4 La cassa pronta IMPLEMENTATO in locale (8/10/2026, sera). Tutto SPENTO.**
- **Percorsi**: la directory pubblica dei corsi espone `suono_count` e il filtro `?suono=1`; nella casa la riga «Percorsi» mostra i corsi con lezioni Suono (card «PERCORSO», prezzo, quante meditazioni, chi) e porta alla pagina del corso: una sola cassa, l'Accademia.
- **L'ossatura del Più** (`services/sound_piu.py`, `routers/sound_piu.py`): sul conto Stripe di Aurya (non Connect), Customer dell'account Aurya, Checkout `subscription` con prezzo da `STRIPE_PIU_PRICE_ID` e metadata per ritrovare l'account, portale clienti, webhook dedicato `/api/public/sound/piu/webhook` con segreto proprio (`STRIPE_PIU_WEBHOOK_SECRET`, ripiego su quello di piattaforma) e lucchetto per evento (idempotente: il doppio è `duplicate`); gli eventi aggiornano `platform_accounts.piu` {status, stripe_subscription_id, current_period_end, cancel_at_period_end}; `stato_account` dice `abbonato` (active/trialing/past_due o omaggio valido). **Provato con Stripe finto**: checkout → cliente salvato → completed → active → updated (disdetta a fine periodo) → deleted → canceled; portale. `GET /platform/me/piu` risponde sempre; checkout e portale rispondono 404 finché `SOUND_PIU_ATTIVO` (ambiente, letto a ogni chiamata) è spento.
- **Frontend**: `SOUND_PIU_ATTIVO=false` e `PIU_PREZZO` in `stato.js`; `/meditazioni/piu` (PiuPage) rimanda alla casa finché spento, altrimenti lista cosa dà, «Entra nel Più · 39 € l'anno» o «Gestisci»; la sezione «Aurya Più» in `/account` (PiuAccount) si vede solo se acceso o se l'account ha una traccia (stato, scadenza, disdetta, portale); il badge sulle card e nel player dice **«Presto nel Più · oggi la ascolti col Cerchio»** (acceso: «Riservata al Più» con rimando). **Nessun paywall**: il cancello del Più si costruisce il giorno dell'accensione.
- **Regia**: la scheda utente (`/admin/users/detail`) porta `piu` e `stripe_customer_id`. Shell: `/meditazioni/piu` noindex finché spento.
- **Il giorno dell'accensione**: `docs/SOUND_PIU_ACCENSIONE_2026-10-08.md` (Stripe, ambiente, flag, cancello da costruire, testi di /costi e /meditazioni/piu, clausola Termini v2.14, comunicazione, omaggi).
- guardie: `tests/test_sound_sn4.py`.

**Gli annunci al Cerchio sono SPENTI (founder, 8/10 sera: «non voglio mandare email automatiche al Cerchio prima di aver creato le meditazioni»).** Verificato: l'annuncio non era mai automatico (solo il bottone con prova a secco e conferma), pubblicare una traccia o una playlist non manda nulla, nessuno sweep lo chiama. In più ora c'è l'interruttore `SOUND_ANNUNCI_ATTIVI`, spento di default: il server risponde 404 su entrambe le porte prima di qualsiasi altra cosa, il bottone in Crea non si vede (`stato.js`). Quando le meditazioni ci saranno: `SOUND_ANNUNCI_ATTIVI=1` nell'ambiente + `true` in `stato.js`. Le email che il Cerchio già manda da settimane restano quelle di prima e non riguardano le meditazioni nuove: il benvenuto (uno, nei primi due giorni, nelle tre varianti ritiri/meditazioni/altro), il promemoria a chi non ha confermato, la sospensione a 90 giorni (senza email).

**Il lotto SN0–SN4 è completo in locale.** Prossimo: il giro di deploy su «go» (vedi memoria `deploy-due-server`: build locale prima, pipefail, `docker restart ms-backend` dopo il frontend, nginx rigenerato per i rimandi) e poi SN5 (l'app) quando il founder lo deciderà.

