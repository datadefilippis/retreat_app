# Il nuovo AFianco — Business Concept
**Piattaforma italiana dei ritiri olistici · Rebrand + intersezione Masseria Montanari · Luglio 2026**

> Questo documento risponde a tre domande rimaste aperte: (1) qual è la visione completa della nuova app, (2) rende di più una directory di strutture o il gestionale con prenotazione diretta per gli organizzatori, (3) quali modifiche concrete servono ad AFianco per il nuovo deploy. Chiude con modello di business, numeri e roadmap.

---

## 1. La visione — cos'è la nuova app, vista da chi la usa

Il modo più rapido per "vederla" è seguire i tre attori. La piattaforma è **il punto d'incontro tra chi organizza ritiri, chi li cerca e chi li ospita** — con i pagamenti al centro.

### 1.1 Sara, insegnante di yoga con 4.000 follower (l'organizzatrice)
Oggi: annuncia il ritiro su Instagram, riceve DM, manda l'IBAN per la caparra, segna i nomi su un foglio, rincorre i saldi su WhatsApp, gestisce una rinuncia con imbarazzo.
Con la piattaforma: crea la **pagina di vendita del ritiro in 15 minuti** (foto, programma, location, prezzi per tipologia camera), imposta **caparra 30% + saldo 30 giorni prima**, condivide il link in bio. Le prenotazioni entrano da sole: caparra incassata con carta, promemoria saldo automatico, lista partecipanti sempre aggiornata, email pre-ritiro programmate. A fine anno ha lo storico clienti e la newsletter per riempire il ritiro successivo.

### 1.2 Marco, 41 anni, stressato, cerca "ritiro yoga Puglia settembre" (il partecipante)
Oggi: trova blog, gruppi Facebook, EventiYoga — e poi comunque deve *scrivere una mail e aspettare*.
Con la piattaforma: atterra sul **calendario pubblico dei ritiri** — filtri per disciplina, regione, data, budget, in presenza/weekend/settimana — apre la pagina del ritiro di Sara, vede posti rimasti e **prenota pagando la caparra online, subito**. Riceve conferma, promemoria e le info pratiche senza che nessuno gli scriva a mano.

### 1.3 Masseria Montanari (la location — e il vantaggio sleale)
La Masseria è la **location-faro** della piattaforma: i ritiri ospitati lì sono i primi contenuti del calendario, la sala a volta è l'immagine del brand, e ogni organizzatore contattato per affittare la struttura riceve anche il sistema di vendita ("porti il tuo ritiro qui, ti diamo pagina + pagamenti + partecipanti"). La piattaforma dà alla Masseria un motivo di contatto che nessun'altra struttura ha; la Masseria dà alla piattaforma eventi veri, foto vere, credibilità vera dal giorno uno.

**In una frase: "EventiYoga + WeTravel, italiana"** — la scoperta (calendario) più la transazione (caparre, rate, partecipanti), che oggi in Italia nessuno unisce.

---

## 2. La domanda chiave: directory di strutture o gestionale per organizzatori?

È il nodo strategico, e la risposta razionale è netta. Confronto sulle tre opzioni:

| Criterio | Directory di strutture (venue) | Calendario pubblico dei ritiri | Gestionale + prenotazione diretta (organizzatori) |
|---|---|---|---|
| Chi ha il dolore | Le strutture vogliono occupazione, ma ricevono già lead gratis dai listing esistenti | Il partecipante cerca e non può prenotare online da nessuna parte | **L'organizzatore: caparre, rate, no-show, Excel — dolore alto e quotidiano** |
| Chi paga, e quanto | Strutture pagano poco per listing (modello Holly Maps: visibilità, tetto basso) | Il consumer non paga; genera domanda, non ricavo diretto | **Paga volentieri: su un ritiro da 8.000€ una fee del 4% o 29€/mese è invisibile** |
| Conflitto con la Masseria | **SÌ, grave: listeresti i concorrenti della Masseria e manderesti da loro i tuoi organizzatori** | No: amplifica i ritiri ovunque si tengano, inclusi quelli in Masseria | No: più organizzatori usano il tool, più ne conosci per la Masseria |
| Valore SEO | Medio (già coperto da EventiYoga "strutture per regione") | **Alto: "ritiro yoga Puglia settembre" è ricerca transazionale** | Nullo diretto (è un tool), ma ogni ritiro pubblicato È una pagina SEO |
| Effort tecnico | Basso | Basso (5–10 gg) | Medio (il grosso esiste già; manca il motore caparre) |
| Difendibilità | Bassa (replicabile) | Media (SEO composto nel tempo) | **Alta: dentro il tool ci sono i soldi e i dati dell'organizzatore — switching cost reale** |

**Risposta: il business è il gestionale con prenotazione diretta; il calendario pubblico è il suo motore di domanda; la directory di strutture NON si fa nelle fasi 1–2.** Non solo rende meno — è *contro* il tuo interesse: finché la Masseria è in fase di lancio, una directory di venue significherebbe promuovere le masserie concorrenti presso gli stessi organizzatori che stai corteggiando. La rete di location diventa sensata solo in fase 3, quando la piattaforma potrà monetizzare il matching (fee sull'affitto location) più di quanto perde in esclusività — e a quel punto la Masseria sarà la location "founding partner" in evidenza, non una tra tante.

Il calendario pubblico invece **non è una directory di operatori né di strutture: è una directory di EVENTI**. Gli eventi scadono, ruotano, generano urgenza ("4 posti rimasti") e query SEO transazionali. È il modello che tiene vivi OlisticMap e EventiYoga — ma con la prenotazione integrata che loro non hanno.

---

## 3. Il prodotto — moduli e perimetro

### 3.1 Cosa vede l'organizzatore (area privata — il prodotto che si paga)
- **Editor del ritiro**: titolo, descrizione markdown, galleria, programma giorno-per-giorno, location con campi strutturati, FAQ.
- **Prezzi a tipologia**: camera condivisa / doppia / singola, early bird, coupon (tier pricing già esistente in AFianco).
- **Motore incassi** (il cuore, da costruire): caparra % o fissa, saldo con scadenza, promemoria automatici, rate opzionali, politica di cancellazione dichiarata.
- **Partecipanti**: lista con stato pagamenti, note (allergie/diete), export, email massive pre-evento.
- **Newsletter & clienti**: riuso del modulo esistente — l'audience si accumula ritiro dopo ritiro.
- **Incassi via Stripe Connect Express**: i soldi vanno sul conto dell'organizzatore, la piattaforma trattiene la fee automaticamente (application fee già nativa in AFianco).

### 3.2 Cosa vede il partecipante (pubblico)
- **Calendario dei ritiri** con filtri: disciplina, regione, data, durata (weekend/settimana), fascia prezzo.
- **Pagina ritiro** = landing di vendita con prenotazione e pagamento immediato della caparra.
- **Area personale minima**: le mie prenotazioni, pagamenti, documenti. (Account unificato cross-organizzatore: sì fin dall'inizio *sul nuovo deploy* — nota in §4.)

### 3.3 Cosa NON c'è (deliberatamente, fasi 1–2)
Directory di operatori · directory di strutture · recensioni · marketplace stile ClassPass · app mobile · multilingua. Ogni "no" è reversibile in fase 3.

---

## 4. Le modifiche ad AFianco — concrete, per il nuovo deploy

Dall'audit del codebase (v5.8+) e dalle verifiche di oggi:

### 4.1 Si riusa così com'è (≈70% del prodotto)
| Modulo AFianco | Uso nel nuovo brand | Note |
|---|---|---|
| Eventi (`event_occurrence`) | Il ritiro stesso | **Verificato oggi: ha `start_at` + `end_at` → multi-giorno nativo**, landing, venue strutturata, slug, tier pricing |
| Stripe Connect Express | Incassi organizzatore + fee piattaforma | `application_fee` già supportata: la commissione è una config, non uno sviluppo |
| Newsletter + form embed | Audience building organizzatore | Modulo appena rifinito, pronto |
| Customer portal | Area partecipante | Ordini, profilo, consensi già funzionanti |
| Corsi video (Bunny) | Upsell fase 2: contenuti pre/post ritiro | Nessun lavoro ora |
| Coupon | Early bird, sconti gruppo | Pronto |
| Branding org/store + design tokens | Pagina "vetrina" personalizzata per organizzatore | Pronto |

### 4.2 Da costruire (il vero sviluppo)
| Blocco | Contenuto | Effort |
|---|---|---|
| **Motore caparra/saldo/rate** | Piani di pagamento per prodotto-evento: checkout caparra, saldo schedulato con promemoria (Brevo), stato pagamenti per partecipante. **Verificato oggi: zero supporto attuale nel backend** | **2–3 settimane — è il cuore, si fa per primo** |
| Calendario pubblico ritiri | Endpoint pubblico cross-organizzatore con filtri (disciplina/regione/data/prezzo) + pagine SEO regionali | 5–10 giorni (pattern `/public/catalog` riusabile) |
| Profilo pubblico organizzatore | Bio, foto, discipline (tassonomia SIAF), prossimi ritiri | 3–5 giorni |
| Gestione partecipanti estesa | Campi custom (diete, taglie, camere), export, email di gruppo | 1 settimana |
| Onboarding organizzatore | Wizard registrazione → Stripe Connect → primo ritiro pubblicato | 1 settimana |

### 4.3 Il rebrand operativo (deploy separato — 3–5 giorni)
Fork dell'infrastruttura, non refactor multi-tenant. Checklist concreta:
- Nuovo VPS (o stesso Hetzner, container separati): `docker-compose.prod.yml` clonato — costo infra **~100–200€/mese**.
- Env: `DOMAIN`, `APP_URL`, `PUBLIC_APP_URL` → nuovo dominio; `SMTP_FROM_NAME` / `SMTP_FROM_EMAIL` → nuovo brand (già env var, zero codice).
- Brevo: nuovo sender + dominio verificato (SPF/DKIM) + webhook bounce.
- Stripe: **nuovo account piattaforma Connect** (separazione contabile pulita da AFianco).
- Frontend: logo, palette, copy — via `OrgBranding`/design tokens già esistenti + tema.
- MongoDB nuovo e vuoto → **nessuna migrazione dati**, e l'account cliente unificato costa zero qui: sul deploy nuovo si parte direttamente con un'unica "organizzazione piattaforma" logica per i partecipanti (il refactor da 4–6 settimane serviva solo per convertire AFianco *esistente*; su un'istanza vergine si modella subito nel modo giusto).

### 4.4 Da NON fare ora
Multi-tenant dual-brand sulla stessa istanza (2–3 settimane sprecate in fase di validazione) · recensioni · calendario disponibilità oraria settimanale · gift card · migrazione di qualsiasi dato AFianco.

**Totale sviluppo MVP: 6–8 settimane** di lavoro concentrato (rebrand 1 + caparre 3 + calendario/profili/onboarding 3–4), riusando il 70% di ciò che esiste.

---

## 5. Il rebrand — nome e dominio

Criteri: italiano, pronunciabile al telefono, .it libero, spazio per allargarsi oltre lo yoga (meditazione, digiuno, aziendale). Verifica registro .it fatta oggi (3 lug 2026):

| Candidato | .it | Note |
|---|---|---|
| **Ritirando** | **LIBERO** | Brandable, evocativo (gerundio = movimento, percorso), corto, memorabile — **preferito** |
| **RitiriInItalia** | **LIBERO** | Descrittivo/SEO, ottimo come *secondo* dominio che punta al calendario pubblico |
| RitiriItalia | LIBERO | Variante secca del precedente |
| PrenotaRitiri | LIBERO | Transazionale, un po' freddo |
| ritiriolistici.it / ritiribenessere.it / radura.it | occupati | — |

Suggerimento: **brand evocativo (es. Ritirando) + dominio descrittivo (ritiriinitalia.it) in redirect/landing SEO**. Costo: due registrazioni .it (~20€/anno). Prima di decidere: verifica marchio su EUIPO e handle Instagram — 30 minuti, da fare in Fase 0.

---

## 6. Modello di business e numeri

### 6.1 Ricavi — tre rubinetti, in ordine di apertura
1. **Fee sulle transazioni (dal giorno 1):** piano Free = pubblichi gratis, **5% sulla caparra/incassi** gestiti in piattaforma. Ancoraggio: BookRetreats/Retreat Guru prendono il **14–15%**, WeTravel costa 79$/mese+1% ma non porta domanda italiana. Il pitch: *"un terzo della commissione dei marketplace americani, e parli con noi in italiano"*.
2. **Abbonamento Pro (dal mese 3–4):** **29€/mese** → fee ridotta al 2%, promemoria/rate avanzate, newsletter illimitata, profilo in evidenza nel calendario. Sopra ~1.000€/mese di transato il Pro conviene da solo: l'upgrade si vende da sé.
3. **Location matching (fase 3, solo se le fasi 1–2 reggono):** fee 8–10% sull'affitto struttura per i match generati dalla piattaforma — con la Masseria *esente e in evidenza* come founding partner.

### 6.2 Unit economics del singolo ritiro (dati di mercato verificati)
Ritiro tipo Italia: weekend 350–600€ o settimana 800–1.500€ a persona; assumiamo prudenzialmente **12 partecipanti × 650€ = 7.800€ di transato**.
- Piano Free: 5% → **~390€ di ricavo piattaforma per ritiro**
- Piano Pro: 29€/mese + 2% → ~156€ fee + quota abbonamento
- Un organizzatore attivo fa 2–6 ritiri/anno → **valore cliente: 300–1.500€/anno**. Con churn basso: dentro il tool ci sono i suoi incassi, i suoi clienti e la sua newsletter.

### 6.3 Scenari a 24 mesi (solo software; la Masseria ha il suo conto economico)
| | Conservativo | Base | Ottimista |
|---|---|---|---|
| Organizzatori attivi | 12 | 35 | 70 |
| Ritiri/anno in piattaforma | 30 | 110 | 260 |
| Transato annuo | ~230k€ | ~860k€ | ~2,0M€ |
| Ricavo software (fee+SaaS) | **~10k€** | **~35k€** | **~85k€** |
| Costi vivi (infra, domini, tool) | ~3k€ | ~4k€ | ~6k€ |

Anche lo scenario base non è "una startup": è **una gamba da ~35k€/anno ad alto margine** dentro un ecosistema a tre gambe (studio web, Masseria, piattaforma) dove ogni gamba abbassa il costo di acquisizione delle altre. Lo scenario ottimista scatta solo se il calendario pubblico conquista il SEO — 12–18 mesi di contenuti.

### 6.4 Perché la Masseria guadagna comunque (l'intersezione economica)
- **Pipeline:** ogni organizzatore nel tool è un lead caldo per affittare la Masseria; ogni trattativa Masseria è una demo del tool. Un funnel, due prodotti.
- **Riempimento:** i ritiri in Masseria venduti col motore caparre convertono meglio di "scrivimi per info" → occupazione più alta della sala a volta.
- **Margine pieno sui ritiri propri:** i ritiri organizzati da voi (tu e la tua ragazza) incassano senza fee di terzi e fanno da vetrina.
- **Dato non ovvio:** il calendario rivela dove c'è domanda insoddisfatta (discipline, periodi, regioni) → guida la programmazione Masseria.

---

## 7. Roadmap con gate (invariata nella sostanza, aggiornata nei dettagli)

| Fase | Quando | Cosa | Gate per proseguire |
|---|---|---|---|
| **0 — Validazione** | lug–ago 2026, zero codice | 15–20 interviste organizzatori (contatti: networking Masseria, EventiYoga, IG); landing lista d'attesa; verifica marchio/handle | ≥10 "lo userei" **e** ≥2 ritiri ipotecati in Masseria |
| **1 — MVP dogfooding** | set–ott, 6–8 settimane dev | Deploy separato + rebrand; motore caparre; vendita online dei ritiri Masseria; 3–5 founding member gratis | ≥5.000€ transato reale entro dicembre |
| **2 — Apertura** | Q1 2027 | Calendario pubblico + SEO regionale; pricing attivo (Free 5% / Pro 29€) | 20+ organizzatori attivi, ≥1.000€/mese ricavo |
| **3 — Ecosistema** | dal Q2 2027 | Rete location con matching fee (Masseria founding partner), recensioni, eventuale estensione operatori 1:1 | — |

---

## 8. Rischi e risposte

1. **Focus** — tre fronti già aperti (studio, tesi fiduciari CH, Masseria). *Risposta:* Fase 0 ricicla il networking Masseria; il gate è una tagliola vera; il fronte CH resta prioritario finché il gate non passa.
2. **EventiYoga aggiunge i pagamenti** — è il competitor meglio piazzato per copiarti. *Risposta:* velocità + asset che non possono clonare (location fisica, eventi propri, rapporto diretto con gli organizzatori).
3. **Stagionalità/volumi piccoli** del mercato ritiri Italia. *Risposta:* break-even bassissimo (~3–4k€/anno di costi vivi), il calendario può includere weekend urbani e ritiri corti fuori stagione.
4. **Freeloading**: organizzatori che usano il calendario ma incassano fuori. *Risposta:* la caparra online È il valore per il partecipante (posti certi, urgenza); chi incassa fuori perde le prenotazioni immediate — il freeloading si auto-limita.
5. **Regolatorio pagamenti**: gestito — Stripe Connect Express tiene i fondi sui conti degli organizzatori; la piattaforma non fa mai da banca.

---

## 9. Sintesi esecutiva

- La nuova app **non è "AFianco per gli olistici"**: è la **piattaforma italiana dei ritiri** — calendario pubblico prenotabile (domanda) + motore caparre/rate/partecipanti (ricavo) — con la Masseria come location-faro e primo cliente.
- **Il business è il gestionale transazionale per organizzatori; la directory di strutture non si fa** nelle fasi 1–2 (rende meno E confligge con la Masseria); il calendario è una directory di *eventi*, non di operatori.
- Modifiche ad AFianco: **fork su deploy separato in 3–5 giorni** (brand in env var, DB vergine → niente migrazioni, account partecipante unificato gratis by design), **un solo sviluppo pesante: il motore caparra/saldo/rate (2–3 settimane)**, il resto è riuso al 70%. MVP totale: 6–8 settimane.
- Economia: fee 5% (vs 14–15% dei marketplace USA) + Pro 29€/mese; scenario base a 24 mesi **~35k€/anno di ricavo software** ad alto margine, più l'effetto pipeline sulla Masseria che resta il motore di ricavo principale dei primi 18 mesi.
- Nomi/domini verificati oggi: **ritirando.it e ritiriinitalia.it liberi** — brand evocativo + dominio SEO in coppia.
- Vincolo invariato: **niente codice prima del gate di Fase 0** (≥10 "lo userei" + 2 ritiri ipotecati in Masseria, entro agosto).
