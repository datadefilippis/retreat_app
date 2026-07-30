# Piano Potatura Store + Header utente — 30 lug 2026

Ciclo PS. Richieste founder: (1) back sbagliato dalle impostazioni di
una voce di listino verso la vecchia pagina prodotti; (2) valutare se
la pagina impostazioni completa serve o confonde; (3) bonifica
olistica dei riferimenti a vecchia pagina prodotti e a "store" in
listino, ritiri e admin; (4) icona omino nell'header pubblico per
l'account UTENTE, distinta dall'area operatori.

## Parte 1 — Cosa dice il codice (verificato nel browser)

1. Il back di ServiceDashboardPage e' un path hardcoded a
   /products?type=service (riga 390, piu' 359 e 372 negli stati di
   errore): riporta alla ProductsPage legacy, fuori menu nel mondo
   snello ma raggiungibile solo cosi'. Stesse uscite sbagliate:
   EventDashboardPage not-found (689) e CheckInPage (429) → /products.
   Il wizard ritiri invece torna correttamente a /events.
2. ServiceDashboardPage (911 righe, 12 sezioni): meta' e' DUPLICATO
   della riga listino LM1 (stato, base, opzioni, requisiti), una
   sezione e' MORTA (Distribuzione multi-store: lo store tecnico e'
   invisibile by design), quattro cose NON hanno altra casa:
   descrizione lunga della landing, traduzioni multilingua, regole
   orari per-giorno, campi ordine custom (+ anteprima/duplica).
3. Superfici store ancora raggiungibili da operatore snello: banner
   "Crea il tuo store" nel passo Pubblica del wizard ritiri (CTA
   /stores); sezione "Indirizzo catalogo pubblico" in Impostazioni con
   prefisso /s/ e placeholder "il-tuo-negozio"; copy "Distribuzione /
   Tutti gli store" nel wizard e nelle dashboard; copy piani "Negozio
   online incluso"; step legacy in /inizia; rotta /store-settings mai
   linkata e autodichiarata deprecata. Piu' codice morto (operationsNav,
   setup_wizard copy irraggiungibile).
4. Header pubblico: in fase network NON esiste alcun entry point per
   l'account utente (la pill "Le mie esperienze" appare solo in fase
   marketplace e solo desktop). Il token vive in
   localStorage[platform_token]; /account fa gia' da gate. App.js ha
   /account registrato due volte + rotte del vecchio customer-portal
   (/account/login, /account/signup, /account/orders) con un auth
   store parallelo: due login utente in vita.

## Parte 2 — Onde PS

### PS1 — Back onesti (subito, rischio basso)
1. ServiceDashboardPage: le tre destinazioni /products* → /listino,
   label "Torna al listino".
2. EventDashboardPage not-found e CheckInPage → /events.
3. Guardia: nessun navigate/Link verso /products fuori dal mondo
   legacy_commerce.

### PS2 — Impostazioni servizio ridotte a editor avanzato onesto
DECISIONE: non eliminare la pagina (4 sezioni non hanno altra casa),
ridurla. Alternativa piu' aggressiva (tutto in accordion nella riga
listino ed eliminare la rotta) rinviata: tocca il merge rawMeta e le
traduzioni, rischio alto senza valore immediato.
1. Restano: anteprima landing + copia link + duplica; descrizione
   lunga (con multilingua); regole orari per-giorno (con toggle);
   campi ordine custom; traduzioni del nome/nota.
2. Via: hero duplicato, dropdown stato (c'e' il toggle in listino),
   pannello base duplicato (nome/prezzo/durata/incasso/foto), opzioni
   duplicate, requisiti duplicati, sezione Distribuzione store,
   stats vendite (Incassi/Ordini coprono).
3. Titolo onesto: "Impostazioni avanzate del servizio". La riga
   listino resta il posto primario; il link "Tutte le impostazioni"
   diventa "Impostazioni avanzate".

### PS3 — Bonifica store e prodotti (olistica)
1. Wizard ritiri passo Pubblica: via il banner "Crea il tuo store";
   ensureDefault silenzioso come gia' fa il listino. Via il copy
   "Distribuzione / Tutti gli store" quando gli store sono <=1
   (ovunque: wizard + dashboard prodotto superstiti).
2. Impostazioni: "Indirizzo catalogo pubblico" ricopy in chiave
   profilo pubblico /o/ (lo slug si governa li'); via prefisso /s/ e
   "il-tuo-negozio".
3. Copy piani/billing: "Negozio online incluso" e simili → "Profilo
   pubblico". IniziaPage: "il tuo negozio insieme" → "la tua vetrina
   insieme"; step legacy solo per org legacy_commerce.
4. Rotta /store-settings rimossa (redirect a /settings). Potatura
   codice morto: operationsNav/moduleNavMap con /stores, copy
   setup_wizard irraggiungibile.
5. Guardia: scan superfici snelle senza "store"/"negozio" nel copy
   operatore (esclusioni motivate per il mondo legacy).

### PS4 — Icona account utente nell'header + un solo login utente
1. Icona CircleUserRound nel blocco destro dell'header marketplace,
   TUTTI i breakpoint (accanto all'hamburger su mobile): token
   assente → /account/accedi; presente → /account, aria-label
   "Il tuo account". Lettura sincrona da localStorage, nessun
   provider nuovo. RACCOMANDAZIONE: accesa anche in fase network
   (gli acquisti da /o/ e /e/ funzionano gia'; chi ha prenotato deve
   ritrovare la sua history).
2. Distinzione operatori: resta il link testuale "Sei un operatore?"
   + footer Area operatori → /login. L'omino e' solo utente.
3. Potatura doppio /account in App.js + rotte customer-portal legacy
   (/account/login, /account/signup, /account/orders...) → redirect
   alle rotte Aurya; il player corsi legacy resta sulla sua rotta.
4. Guardia: un solo entry point login utente; redirect verificati.

### PS5 — Consolidamento GDPR operatore (analisi 30 lug)

FATTI (verificati nel browser e nel DB dev):
1. L'editor legale merchant (MerchantLegalDialog, 1105 righe) e' un
   mondo a se': wizard 7 campi, 8 slot markdown (privacy+terms x4
   lingue), publish con versioning e re-consent, ~2000 righe dedicate.
   Nel DB dev: 0 store con legal pubblicato, 1 bozza con dati sporchi
   ("test / dav@gmail.com / iitallia") che VINCONO sui dati veri dello
   store (precedenza template_vars > store doc).
2. BUG LINGUA CONFERMATO: /api/legal/storefront/{slug}/privacy|terms
   non accetta lang; la lingua e' storefront_languages[0] (scelta CG-1
   store-centrica). Utente italiano al checkout → informativa in
   inglese su masseria-demo. Bonus: i template EN/DE/FR dichiarano
   "fa fede la versione italiana" mentre la pagina dice "lingua di
   riferimento: English"; i default piattaforma nei TemplateVars sono
   ancora afianco (da ribrandizzare Aurya).
3. Ruoli gia' codificati (AP-L): Aurya titolare per account/newsletter/
   marketplace (documenti Aurya v2.3); operatore titolare autonomo per
   ordini/clienti suoi, Aurya responsabile art. 28. L'autogen produce
   gia' l'informativa dell'operatore con gli stessi template
   dell'editor. Il DPA (CG-7) esiste ma e' una pagina ORFANA mai
   linkata e mai firmata: gap di compliance reale.

DECISIONE: l'operatore NON scrive privacy. Bastano i documenti Aurya
+ informativa autogenerata automatica + le sue condizioni (policy +
requisiti). Onda:
1. Congelare l'editor custom: via la voce "Documenti personalizzati"
   da SalesConditionsCard e il MerchantLegalDialog dal mondo snello;
   chi ha gia' pubblicato (prod da verificare, dev 0) resta servito
   dall'envelope esistente in sola lettura. Macchina consensi CG-4/5
   intatta.
2. Informativa solo autogen multilingua: ?lang= sugli endpoint
   storefront legal (default lingua store, override lingua utente da
   StorefrontLegalPage e dai link checkout); riga "fa fede la
   versione in {lingua primaria}"; via il boilerplate contraddittorio
   dai template EN/DE/FR.
3. Dati anagrafici del titolare: precedenza invertita (store/org doc
   vince sui template_vars stantii) o template_vars eliminati; al
   posto del wizard 7 campi un mini-form 3 campi (nome, email, paese)
   in SalesConditionsCard; default piattaforma ribrandizzati Aurya.
4. DPA in superficie: link "Accordo trattamento dati (art. 28)" in
   SalesConditionsCard con stato firmato/da firmare; spinta
   all'acknowledgement (non bloccante).
5. Coda ciclo futuro: link "Condizioni di vendita" del profilo /o/
   punta al terms template e-commerce (parla di resi merce): valutare
   di puntarlo alle condizioni reali (policy cancellazione).
6. Guardie: informativa nella lingua utente al checkout; precedenza
   dati titolare; DPA raggiungibile; editor assente dal mondo snello.

### PS6 — Funnel checkout pertinenti (analisi 30 lug, matrice browser)

Matrice funnel (profilo /o/, landing /e/ da profilo o marketplace,
legacy /s/ e /p/, pay-token) x azioni (annullo, back, richiesta
inviata, Stripe cancel/success, back dopo successo, catena lunga).
Cosa FUNZIONA (verificato): annullo e riapertura puliti su tutte le
superfici inline, zero doppi ordini, catena lunga marketplace
perfetta (L2 rispettata), claim account dalla success ok.

ROTTO (priorita' 1):
1. /s/:slug?checkout=1 morto: StoreToProfileRedirect rivaluta
   wantsCheckout dopo lo strip del param e rimbalza al profilo senza
   modale. Fix: latch useState(() => wantsCheckout) nel redirect.
2. Handoff /p/ → /s/: "Aggiunto al carrello" ma catalogo filtrato per
   lingua non trova il prodotto → vetrina vuota e toast bugiardo
   (StorefrontPage preload bail silenzioso). Fix minimo: toast onesto;
   fix vero: preload con fallback lingua default. (Assorbe il chip
   "handoff carrello perso".)
3. /pay/{token} in stati non pagabili mostra JSON nudo (link che
   viaggiano via email). Fix: RedirectResponse a pagina frontend con
   copy e CTA account.

FUORVIANTE (priorita' 2):
4. Contaminazione mktp_ctx: InlineEventCheckout timbra il flag
   incondizionatamente e nessuno lo pulisce nel mondo /o/ → acquisto
   successivo dal profilo marcato sales_channel=marketplace (operatore
   non puo' registrare incasso manuale, analytics falsate). Fix:
   pulizia specchio in InlineServiceCheckout + channel derivato dalla
   superficie reale al submit (prop esplicita).
5. Pagina Stripe CANCEL cieca al funnel: mktp_return esiste ma non e'
   letto; niente "riprova"; copy che promette contatto su un draft;
   importo totale mostrato invece della caparra della session. Fix:
   CTA primaria "Riprova, torna al ritiro" da mktp_return, copy
   onesta "Nessun addebito, ordine non confermato", importo coerente.
6. Success "Torna ai ritiri" → / che in fase network e' la home rete
   senza ritiri (anche breadcrumb /e/). Fix: mktp_return quando
   esiste, altrimenti label neutra.

ATTRITO (priorita' 3, valutare):
7. Back del browser non chiude l'overlay ma la pagina (history senza
   entry; rischio medio, interazione con L2 — solo se vale la pena).
8. Titolo "Pagamento ricevuto" mentre ancora si conferma.
9. Doppio avviso ridondante nel pannello servizio con slot.
10. ?checkout=1 con carrello vuoto resta nell'URL senza feedback.

Guardie: latch handoff, canale ordine = superficie reale (profilo vs
marketplace), pay-token mai JSON nudo, cancel/success con CTA
pertinenti al funnel.

Ordine: PS1 → PS2 → PS3 → PS4 → PS5 → PS6 (o PS6 anticipata se il
founder preferisce partire dai funnel: i tre ROTTI sono fix piccoli).
Invarianti: motore ordini/slot intoccato, mondo legacy_commerce
funzionante dietro flag, /s/ redirect retrocompat intatto, macchina
consensi CG-4/CG-5 e AP-L intatta.

## Valore
L'operatore snello non incontra mai piu' "store", "prodotti" o pagine
doppie: listino e ritiri sono le uniche vie, con un solo editor
avanzato onesto. L'utente ha il suo posto visibile nell'header su
ogni pagina pubblica.
