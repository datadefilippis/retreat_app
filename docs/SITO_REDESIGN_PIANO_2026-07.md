# Redesign del sito sul Blueprint — piano operativo (31 lug 2026)

Ciclo SW. Il Blueprint (docs/AURYA_BLUEPRINT_2026-07.md) e' la fonte:
ogni pagina deve superare il test "costruisce fiducia o spiega un
prodotto?" e parlare col dispositivo a coppia. L'ordine e' quello del
Blueprint: HOME → MANIFESTO → OPERATORI → CHI SIAMO → MAGAZINE →
PROFILO OPERATORE → PROFILO LUOGO → ESPERIENZE.

Stato: HOME fatta (HP2-HP4). PROFILO OPERATORE fatto (PV3-PV4).
ESPERIENZE costruite, si accendono col flip. Restano cinque onde di
pagina piu' una trasversale.

## SW1 — Il Manifesto sulla teoria
La pagina piu' linkata del sito (CTA di home e landing) e' ancora
nella voce vecchia ("la rete degli operatori olistici").
1. Riscrittura nella voce v3, struttura in quattro movimenti:
   a. LA TEORIA: "Ogni percorso di benessere inizia da un incontro
      di fiducia." aperta come frase sola, grande.
   b. IL MONDO COME LO VEDIAMO: il problema detto piano (scegliere
      alla cieca, promesse, elenchi).
   c. COME LAVORIAMO: i gesti (incontriamo, ascoltiamo, scriviamo,
      diciamo anche i limiti), il badge come provenienza.
   d. COSA NON FAREMO MAI: la lista dei divieti resa pubblica e'
      un atto di fiducia raro (nessun competitor la fa).
   Firma finale dei fondatori (foto vera + due righe), che fa da
   ponte a Chi siamo.
2. Visual: kit editoriale, una ancora verde, la foto vera.
3. SEO e i18n x4 riallineati.

## SW2 — Landing operatori: il visual (OL2, gia' impostata)
Il copy OL1 e' committato; manca il passaggio visivo interrotto.
Brief gia' pronto: hero fotografico, quattro blocchi a schede, due
ancore verdi non adiacenti, Chi siamo con la foto reale, form caldo.
Riparte cosi' com'era.

## SW3 — Chi siamo: pagina propria
Decisione proposta: pagina dedicata (non dentro il Manifesto). Il
Manifesto e' la posizione; Chi siamo sono le persone. Due domande
diverse meritano due pagine, e il footer gia' punta a /chi-siamo.
1. Rimontare AboutAuryaPage sulla rotta vera, riscritta in voce v3:
   apertura "Non siamo un'agenzia. Non siamo un software. Non siamo
   una directory." (eco della landing), poi Davide e Valentina col
   materiale reale esistente, il perche' personale, la foto.
2. Il redirect /chi-siamo → /manifesto si toglie.

## SW4 — Magazine: vetrina e copertine
1. Indice /blog allineato al kit editoriale (lead grande + griglia,
   come la sezione della home): oggi ha un hero fotografico generico
   e card vecchie.
2. LE COPERTINE: via il titolo stampato dentro l'immagine
   autogenerata (il difetto segnalato in HP3: titolo doppio nel
   lead, rumore nelle miniature). Nuovo template di copertina: segno
   grafico + categoria + palette, senza testo del titolo. Rigenerare
   le copertine esistenti con lo script.
3. Decisione canonical /blog → /magazine: SI PUO' fare qui (301
   server, sitemap, IndexNow) o rinviare. Da decidere col founder.

## SW5 — La rete (/operatori): le persone con la loro voce
1. La pagina dei membri passa dallo schema "elenco con criteri" allo
   schema "Le persone" del Blueprint: card grandi con foto, nome,
   pratica, luogo e UNA CITAZIONE dall'intervista.
2. Richiede i due campi mancanti nel payload pubblico (quote scelta
   dall'admin nell'editor intervista + categoria/pratica): chiude il
   gap noto dalla v3 della home.
3. Criteri di ingresso riscritti come gesti, non come requisiti.

## SW6 — Profilo luogo (progetto nuovo)
Il primo tipo di pagina che NON esiste: la casa di masserie, centri
e spazi (Masseria Montanari come primo). Non un restyle: un progetto.
Da fare per ultima, con una analisi propria (modello dati, rotte,
relazione coi ritiri che ospita). Nel frattempo nessun link rotto:
la pagina non e' promessa da nessuna parte.

## SW7 — Trasversale: coerenza e guardie
1. Navigazione e footer allineati in tutte le fasi; 404 e pagine di
   servizio nella voce del brand.
2. Meta SEO di ogni pagina pubblica riletti nella voce (niente
   "rete degli operatori olistici" residuo).
3. GUARDIA DELLE PAROLE VIETATE a livello sito: il capitolo 8 del
   Blueprint diventa un test che scandisce i locales pubblici
   (trasforma la tua vita, ritrova te stesso, marketplace,
   directory, gestionale, piattaforma innovativa, gratuito come
   promessa fuori FAQ...). Oggi esistono guardie sparse (trattini,
   Passaporto, gratuito sulla landing): si unificano.
4. Newsletter landing: gia' in voce accettabile, solo rilettura.

## Ordine di esecuzione proposto
SW2 (gia' pronta a partire) → SW1 → SW3 → SW4 → SW5 → SW7 → SW6.
Motivo: la landing operatori e' il canale di acquisizione attivo
OGGI (ogni giorno senza visual e' un lead piu' debole); il Manifesto
subito dopo perche' e' la destinazione di meta' delle CTA del sito.

## Regole del ciclo (valgono per ogni onda)
1. Copy nel dispositivo a coppia; ogni frase passa il test del
   Blueprint.
2. Kit editoriale condiviso, mai stili nuovi per pagina.
3. Foto solo reali, aperte e scelte una a una.
4. Contrasto AA misurato, reduced-motion, zero librerie nuove.
5. Suite verde e guardie per onda; commit per onda; prod ferma.
