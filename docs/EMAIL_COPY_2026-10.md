# Le email automatiche di Aurya: prima / dopo (FL3, 5/10/2026)

> **Stato (5/10 notte): il founder ha riletto e riscritto tutte le email; la sua versione è in `EMAIL_COPY_2026-10_FOUNDER.md` ed è quella applicata nel codice (commit FL3). Questo file resta come storia delle proposte.**

Da leggere prima che tocchi il codice. Per ogni email: cosa dice oggi (in breve, verbatim dove conta) e come la propongo. Correggi direttamente qui sotto, anche a penna: il tono deve essere il tuo. Le regole che ho applicato a tutte:

- **Una voce**: prima persona plurale, come scrivono Valentina e Davide nelle sequenze. Via il dizionario e-commerce («con successo», «store», «pack», «upgrade», «regolarizzare»).
- **Mai declinato**: «Benvenuto» → «Sei nel Cerchio»; «Se non sei stato tu» → «Se non eri tu»; «Sei stato invitato» → «Hai un invito»; «chi ha prenotato con lui» → «chi ha prenotato con questa persona».
- **Una cosa per email, un pulsante principale con un verbo**, il passo successivo scritto, mai «click» (si dice «clic» o «tocca»), accenti veri, nessun elenco di campi stile modulo.
- **Piè di pagina coerente**: dove il corpo dice «rispondi a questa email», il piè di pagina non dice più «scrivi a aurya.life@gmail.com». Il piè di pagina diventa: «Aurya · Ritiri ed esperienze olistiche, in un posto solo · aurya.life». Le risposte arrivano comunque alla casella Aurya (Reply-To).
- Niente cambia in trigger, link, token, tempi: solo le parole. Dove segnalo **[FIX]** c'è anche un errore vero da correggere.

Legenda: ⟶ = pulsante. `{…}` = valore che il sistema inserisce.

---

## A. Il Cerchio

### 1. Conferma iscrizione (doppio opt-in, oggi spento in prod: resta per quando serve)
**Prima**: oggetto «Un clic per entrare nel Cerchio di Aurya»; «un clic e sei nel Cerchio di Aurya. Da subito: • le meditazioni riservate, gratis; • i ritiri…»; chiusa con «Se non ti sei iscritto tu, ignora questa email».
**Dopo**:
> Oggetto: **Un clic e sei nel Cerchio di Aurya**
> Ciao {Nome},
> un clic e sei nel Cerchio di Aurya: le meditazioni riservate, i ritiri e le esperienze in anteprima, la Lettera quando vale la pena.
> ⟶ Entro nel Cerchio
> Se il pulsante non funziona, copia questo link nel browser: {url}
> Se non eri tu, ignora questa email: senza il clic non ti scriviamo.

### 2a. Promemoria 48 ore (doppio opt-in)
**Prima**: «…Se non ti interessa piu', non devi fare nulla: e' l'ultima email che ricevi da noi.»
**Dopo**:
> Oggetto: **Ti manca un clic per entrare nel Cerchio**
> Ciao {Nome},
> ti manca un clic per entrare nel Cerchio di Aurya: le meditazioni riservate, i ritiri in anteprima, la Lettera quando vale la pena.
> ⟶ Entro nel Cerchio
> Se non ti va, non devi fare nulla: non ti scriviamo più.

### 2b. Promemoria 48 ore (singolo opt-in, quello acceso oggi)
**Prima**: oggetto «Un clic e si aprono le meditazioni riservate»; «…Un clic qui sotto apre anche i contenuti riservati…».
**Dopo**:
> Oggetto: **Un tocco e si aprono le meditazioni**
> Ciao {Nome},
> sei nel Cerchio di Aurya: la Lettera ti arriva già. Un tocco sul pulsante apre anche le meditazioni, le guide e i ritiri in anteprima, su qualunque telefono.
> ⟶ Apro le meditazioni
> Se non ti interessano, non devi fare nulla: la Lettera continua ad arrivare e da lì ti cancelli con un clic.

### 3. Riapri il mio accesso
**Prima**: «…Se non hai richiesto tu questo link, ignora l'email: nessuno puo' usare il tuo accesso senza aprire questo messaggio.»
**Dopo**:
> Oggetto: **Il tuo accesso al Cerchio di Aurya**
> Ciao {Nome},
> sei già nel Cerchio con questa email. Il pulsante riapre il tuo accesso {e ti riporta alla guida che stavi leggendo | su questo dispositivo}: meditazioni, guide e preferenze, senza iscriverti di nuovo.
> ⟶ Riapro il mio accesso
> Se non l'hai chiesto tu, ignora questa email: il link funziona solo da qui dentro.

### 4. Sei nel Cerchio: variante «ritiri» (la tua frase)
**Prima**: oggetto «Benvenuto nel Cerchio di Aurya»; «sei nel Cerchio di Aurya. Cerchi un ritiro: ci hai detto che ti chiamano {lo yoga, la meditazione}, e che lo cerchi {vicino a Bari}.»
**Dopo**:
> Oggetto: **Sei nel Cerchio di Aurya**
> Ciao {Nome},
> sei nel Cerchio di Aurya. Sappiamo che ti interessano gli eventi e i ritiri di Aurya a {Bari (zona)} [varianti: «in Italia» · «in Italia o all'estero» · senza luogo: «gli eventi e i ritiri di Aurya»; con le vie: «ti interessano {yoga, meditazione} e i ritiri di Aurya a {Bari} (zona)»].
> **Come funziona.** Appena c'è un ritiro o un'esperienza che corrisponde, te lo scriviamo. Non un elenco per riempire una email: una proposta, quando c'è.
> [solo se mancano vie o luogo] Per proporti solo cose adatte a te, dicci cosa ti interessa e dove vivi: un minuto, e da lì in poi ricevi solo quello che ti somiglia. ⟶ Le mie preferenze
> Nel frattempo ci sono le meditazioni del Cerchio: si ascoltano dal telefono, con le cuffie, senza nessuna app. Un tocco e sono aperte.
> ⟶ Ascolta le meditazioni
> Se vuoi dirci di più su quello che cerchi, rispondi a questa email: la legge Valentina.
> A presto, Valentina e Davide
> Sei nel Cerchio con {email}. Le tue preferenze, e da lì ti cancelli con un clic.

### 5. Sei nel Cerchio: variante «meditazioni»
**Prima**: oggetto «Benvenuto nel Cerchio: le tue meditazioni»; «Se le apri da un altro dispositivo e trovi il lucchetto, metti la tua email…».
**Dopo**:
> Oggetto: **Sei nel Cerchio: le meditazioni sono aperte**
> Ciao {Nome},
> sei nel Cerchio di Aurya e le meditazioni sono aperte. Un tocco sul pulsante e si ascoltano, su qualunque telefono.
> ⟶ Ascolta le meditazioni
> Come ascoltarle: le cuffie, dieci minuti in cui nessuno ti cerca, il telefono a faccia in giù. Non c'è niente da fare bene; se la mente va via, torna.
> Se vuoi dirci com'è stata, rispondi a questa email con una parola: le leggiamo tutte.
> A presto, Valentina e Davide
> (piè di pagina come la 4)
*(Via la riga del lucchetto: con il fix del pulsante non serve più.)*

### 6. Sei nel Cerchio: variante «altro» (home, Magazine, account)
**Prima**: oggetto «Benvenuto nel Cerchio di Aurya»; «Ecco cosa c'è… I ritiri, se li cerchi. Dicci le tue vie e dove vivi…».
**Dopo**:
> Oggetto: **Sei nel Cerchio di Aurya**
> Ciao {Nome},
> sei nel Cerchio di Aurya. Ecco cosa c'è.
> **Le meditazioni.** Si ascoltano dal telefono, con le cuffie, senza nessuna app. Un tocco e sono aperte. ⟶ Ascolta le meditazioni
> **La Lettera.** Quando vale la pena: una pratica raccontata bene e una persona della rete. Mai per riempire una casella.
> **I ritiri, se li cerchi.** Dicci cosa ti interessa (yoga, respiro, suono…) e dove vivi: appena c'è un ritiro adatto te lo scriviamo. ⟶ Le mie preferenze
> Se vuoi dirci cosa cerchi, rispondi a questa email: la legge Valentina.
> A presto, Valentina e Davide

---

## B. Account Aurya (clienti)

### 7. Conferma la tua email (creazione account)
**Prima**: «Grazie per aver creato il tuo account Aurya. Conferma la tua email con il pulsante qui sotto: da quel momento potrai accedere con la tua password.»
**Dopo** (con FL5 il clic fa entrare):
> Oggetto: **Un clic e il tuo account Aurya è attivo**
> Ciao {Nome},
> il tuo account Aurya è quasi pronto. Un clic sul pulsante conferma la tua email e ti fa entrare {: ti riporta alla pagina di {operatore} | }.
> ⟶ Confermo e entro
> Il link vale 24 ore. Se non eri tu, ignora questa email: l'account non si attiva.

### 8. Accesso con codice / link
**Prima**: oggetto «Il tuo accesso: un click e sei dentro»; «…nessuno puo' accedere senza di essa.»
**Dopo**:
> Oggetto: **Il tuo accesso ad Aurya**
> Ciao {Nome},
> ecco il tuo codice, vale 15 minuti: **{123456}**. Scrivilo nella pagina da cui l'hai chiesto, oppure entra dal pulsante.
> ⟶ Entro in Aurya
> Il link funziona una volta sola. Se non l'hai chiesto tu, ignora questa email.

### 9. Nuova password
**Prima**: «Abbiamo ricevuto una richiesta di impostare o cambiare la password…»
**Dopo**:
> Oggetto: **Scegli la tua nuova password**
> Ciao {Nome},
> dal pulsante scegli la nuova password del tuo account Aurya. Il link vale un'ora.
> ⟶ Scelgo la password
> Se non l'hai chiesto tu, ignora questa email: la password resta quella di prima.

### 10. Le tue prenotazioni nel tuo account (dopo il primo acquisto)
**Prima**: «Grazie della tua prenotazione! Con un click accedi… Il link vale 15 minuti.»
**Dopo**:
> Oggetto: **Le tue prenotazioni, in un posto solo**
> Ciao {Nome},
> grazie della prenotazione. Nel tuo account Aurya ritrovi prenotazioni, pagamenti e biglietti, anche con professionisti diversi.
> ⟶ Entro nel mio account
> Il link vale 15 minuti: se è scaduto, da aurya.life/accedi te ne mandiamo un altro in un attimo. Una volta dentro puoi scegliere una password.

### 11-14. Account cliente di un negozio (quattro email) **[FIX tono]**
**Prima**: «Benvenuto — Il tuo account e' stato creato», «Clicca il pulsante qui sotto per verificare», «Reimposta Password», «La tua password e' stata modificata con successo. Se non sei stato tu…».
**Dopo**:
> 11 · Oggetto: **Il tuo account è pronto: conferma l'email** · «Ciao {Nome}, il tuo account è pronto. Un clic conferma la tua email e puoi iniziare.» ⟶ Confermo la mia email · «Il link vale 24 ore.»
> 12 · Oggetto: **Conferma la tua email** · «Ciao, un clic e la tua email è confermata.» ⟶ Confermo la mia email · «Il link vale 24 ore. Se non l'hai chiesto tu, ignora questa email.»
> 13 · Oggetto: **Scegli la tua nuova password** · «Ciao, dal pulsante scegli la nuova password. Il link vale un'ora.» ⟶ Scelgo la password · «Se non l'hai chiesto tu, ignora questa email: la password resta quella di prima.»
> 14 · Oggetto: **Password cambiata** · «Ciao {Nome}, la tua password è cambiata adesso. Se non eri tu, scegline subito una nuova da «Password dimenticata» e scrivici: rispondi a questa email.»

### 15. Accesso bloccato per tentativi sbagliati
**Prima**: «Abbiamo rilevato 5 tentativi falliti… Se non sei stato tu… Se sei stato tu a sbagliare…»
**Dopo**:
> Oggetto: **Accesso fermato per sicurezza**
> Ciao,
> cinque tentativi di accesso sbagliati di fila: per sicurezza l'accesso è fermo fino alle {ora}. Se eri tu, riprova dopo, o scegli una nuova password. Se non eri tu, scegli subito una nuova password.
> ⟶ Scelgo una nuova password

---

## C. Professionisti

### 16. Il tuo spazio è aperto (giorno zero)
**Prima**: va bene com'è. Due ritocchi: «un quarto d'ora» (qui) e «dieci minuti» (email 18b) per la stessa cosa → **«dieci minuti»** ovunque; «il gruppo Telegram degli operatori» → **«i canali Telegram della rete»**.

### 17. La tua pagina è online **[spezzare in due]**
**Prima**: la più lunga: link + listino + tre canali + ritiri + consulenza a pagamento.
**Dopo** (17a, subito):
> Oggetto: **La tua pagina è online: ecco il link**
> Ciao {Nome},
> la tua pagina su Aurya è online: aurya.life/o/{slug}. Mettila nella bio di Instagram, mandala a chi ti chiede «dove ti trovo?». Chi la apre vede chi sei, cosa fai, e può chiederti un posto. Senza abbonamenti e senza commissioni.
> ⟶ Apri la tua pagina
> [blocco listino, invariato: «Il prossimo passo è il listino…» oppure «Il tuo listino…»]
> Per tutto il resto rispondi a questa email: la legge Valentina.
> A presto, Valentina e Davide

**17b, il giorno dopo** (nuovo passo `canali`, solo chi è online):
> Oggetto: **I canali della rete Aurya**
> Ciao {Nome},
> ora che la tua pagina è online, ecco dove ci si trova.
> **Bacheca Aurya** (Telegram): le novità, le richieste di eventi e ritiri che arrivano, le cose utili per chi lavora nel benessere. {url}
> **Supporto** (Telegram): per ogni domanda sulla pagina o su qualcosa che non funziona; rispondiamo noi. {url}
> **Instagram**: raccontiamo la rete e i professionisti anche qui. {url}
> [se i link mancano] Rispondi a questa email con il tuo nome Telegram e ti mandiamo l'invito.
> A presto, Valentina e Davide
*(Il blocco ritiri e la consulenza a pagamento escono da qui: i ritiri hanno già l'email 21, la consulenza va nella Lettera o in una proposta a parte, mai nel benvenuto.)*

### 18-21. Sequenza giorni 5/10/14/15
Vanno bene. Ritocchi: 18b «dieci minuti» (coerente con la 16); 19b oggetto «Cosa blocca, di solito» → **«Le tre cose che fermano una pagina»**; 20b «Grazie di esserti iscritto» → **«Grazie di essere su Aurya»**; 21 «Non serve Stripe» → **«Non serve nessun sistema di pagamento»**.

### 22-24. Reinvio verifica, nuova password, password cambiata (professionista)
Stesso stile delle 12-14 (sopra), con «il tuo spazio su Aurya» al posto di «account».

### 25. Invito nel team **[FIX sicurezza]**
**Prima**: «Sei stato invitato…», password temporanea in chiaro nel corpo.
**Dopo**:
> Oggetto: **{Chi invita} ti ha aggiunto a {Organizzazione} su Aurya**
> Ciao,
> {Chi invita} ti ha aggiunto allo spazio di {Organizzazione} su Aurya. Dal pulsante scegli la tua password ed entri.
> ⟶ Scelgo la password ed entro
> Il link vale 7 giorni.
*(Tecnicamente: si manda un link di prima password al posto della password in chiaro. È un cambio piccolo nel codice dell'invito.)*

### 26. Candidatura ricevuta
**Prima**: «Abbiamo ricevuto la tua richiesta di accesso ad Aurya. Ti contatteremo al piu presto per fornirti l'accesso.»
**Dopo**:
> Oggetto: **La tua richiesta è arrivata**
> Ciao {Nome},
> abbiamo la tua richiesta di entrare su Aurya. La leggiamo noi, Valentina e Davide, e ti scriviamo entro due giorni lavorativi.

### 27. Invito dalla regia **[FIX: copy di un altro prodotto]**
**Prima**: «Sei stato invitato a registrarti su Aurya, la piattaforma di gestione finanziaria per PMI.»
**Dopo**:
> Oggetto: **Hai un invito per Aurya**
> Ciao,
> hai un invito per aprire il tuo spazio su Aurya, la rete dei professionisti del benessere. Dal pulsante lo apri in un minuto.
> ⟶ Apro il mio spazio
> Il link vale 7 giorni. Se non l'aspettavi, ignora questa email.

### 28-29. Spazio disattivato / ultimo avviso
**Prima**: «Conformemente alla nostra Privacy Policy (Art. 17 GDPR)… contattando il supporto…», oggetto in maiuscolo.
**Dopo**:
> 28 · Oggetto: **Il tuo spazio su Aurya è stato disattivato** · «Ciao, lo spazio di {Org} su Aurya è stato disattivato. I dati restano per 30 giorni, fino al {data}: entro quella data puoi riattivarlo rispondendo a questa email. Dopo, vengono eliminati per sempre.»
> 29 · Oggetto: **Tra 7 giorni eliminiamo i dati di {Org}** · «Ciao, il {data} eliminiamo per sempre i dati dello spazio di {Org}, disattivato {N} giorni fa. Se vuoi tenerli, rispondi a questa email entro quella data e lo riattiviamo. Se vuoi una copia dei dati, chiedila nella stessa risposta. Se va bene così, non devi fare nulla.»

### 30-31. Pagina «in difficoltà» e limiti di piano
**Prima**: «store», «storefront», «provider di pagamento», «pack», «upgrade», «a soli €9/mese».
**Dopo**: 30a → oggetto **«Alla tua pagina mancano {N} cose»**, corpo «Ciao, la tua pagina resta visibile, ma a {nome} mancano: {elenco in parole: l'indirizzo pubblico, il nome, l'email di contatto, un modo per incassare, un servizio pubblicato}. Dal pulsante le sistemi in un minuto.» ⟶ Sistemo la pagina. 30b → **«La tua pagina è a posto»**, «Ciao, tutto quello che serviva alla tua pagina c'è. Buon lavoro.» 31 → **«Hai usato {X} su {Y} {cosa} questo mese»**, «Ciao, questo mese hai usato {X} su {Y} {chat con l'assistente | ordini}. Se ti servono altri, da qui scegli come: ⟶ Vedo le opzioni». Senza «a soli», senza «pack».

### 32-33. Recensioni al professionista
Vanno bene; ritocchi: «Puoi rispondere dal gestionale» → **«Puoi rispondere dalla tua pagina Recensioni»**; 32b aggiungere **«Resta in attesa finché non decidi tu: non c'è fretta»**; 33a «non abbiamo trovato una violazione» → **«non va contro le regole delle recensioni»**; «risponderle» → **«rispondere pubblicamente»**.

### 34. Ricevuta della richiesta (struttura / regia / aziende / servizi Pro) **[FIX frase rotta]**
**Prima**: elenco di campi stile modulo; 34d «abbiamo ricevuto la tua richiesta: i suoi eventi nella Lettera del Cerchio».
**Dopo**:
> 34a · Oggetto: **La tua richiesta di struttura è arrivata** · «Ciao, abbiamo la tua richiesta di una struttura per un ritiro a {zona}, {periodo}, per {N} persone{, N notti}{, budget {B} € a persona}. La leggiamo noi e ti scriviamo entro pochi giorni con le strutture che conosciamo e che rispondono a quello che cerchi. Se intanto cambia qualcosa, rispondi a questa email.»
> 34b · regia: stessa forma, «…ti scriviamo entro pochi giorni con una proposta chiara: cosa facciamo noi, cosa resta a te, quanto costa ({formula}).»
> 34c · aziende: tutto al «voi»: «Ciao {Nome}, abbiamo la richiesta di {Azienda} per un'esperienza su misura: {periodo}, {N} persone. Vi scriviamo entro due giorni lavorativi: prima una chiamata, poi una proposta scritta con programma, chi conduce, dove e il prezzo.»
> 34d · servizi Pro: «Ciao, abbiamo la tua richiesta per **{i tuoi eventi nella Lettera del Cerchio | la pubblicazione dei tuoi eventi sui social di Aurya | l'intervista e i reel}**. Ti scriviamo entro pochi giorni per organizzare insieme cosa e quando.» *(le etichette passano alla seconda persona)*

### 35. Aggiornamento sulla richiesta **[FIX frase rotta]**
**Prima**: un solo oggetto per ogni stato; «la tua richiesta … è abbiamo una o più proposte per te»; stato «chiusa» muto.
**Dopo** (un'email per stato):
> in lavorazione · Oggetto: **Ci stiamo lavorando: {zona o azienda}, {periodo}** · «Ciao, la tua richiesta ({…}) è in lavorazione: stiamo {cercando fra le strutture che conosciamo | preparando la proposta}. Ti scriviamo appena c'è qualcosa di concreto.»
> proposta · Oggetto: **Abbiamo una proposta per te** · «Ciao, per la tua richiesta ({…}) abbiamo {una o più proposte | la proposta pronta}: ti scriviamo a parte con i dettagli, entro oggi.»
> chiusa · Oggetto: **La tua richiesta è chiusa** · «Ciao, abbiamo chiuso la tua richiesta ({…}). Se non è quello che ti aspettavi, o se vuoi riaprirla, rispondi a questa email: la legge Valentina.»

### 36. Pagamento a rischio (al professionista)
**Prima**: parte a freddo, «condonarlo», «dashboard incassi», nessun pulsante.
**Dopo**:
> Oggetto: **{Cliente}: il {saldo} di {importo} non è arrivato**
> Ciao {Nome},
> il {saldo} di {importo} per l'ordine {A-1024} ({cliente}) era previsto entro il {data}. Dopo tre promemoria non risulta pagato.
> Da Incassi puoi: segnarlo pagato (se è arrivato con bonifico), cancellarlo, dare più tempo, o liberare il posto. Non facciamo nulla senza di te.
> ⟶ Apro gli incassi

---

## D. Ordini e prenotazioni (clienti dei professionisti)

### 37. Richiesta ricevuta **[FIX: dice «aspetta» sopra un blocco che dice «paga»]**
**Prima**: «La tua richiesta e' stata registrata. Ti contatteremo a breve.» poi il blocco bonifico.
**Dopo**:
> Oggetto: **La tua richiesta è arrivata a {nome}**
> Ciao,
> {nome} ha la tua richiesta ({riferimento A-1024}, {1 evento, 2 prodotti}, totale {450 €}).
> [con IBAN] **Per tenere il posto**: {caparra di 150 € | il pagamento di 450 €} con un bonifico entro il {data}. IBAN {…} · intestato a {…} · causale {…}. Appena arriva, ti confermiamo il posto. Se cambi idea prima, scrivici e basta.
> [senza IBAN] {nome} ti scrive a breve per confermare il posto e concordare il pagamento{: è prevista una caparra di 150 €}.
> ⟶ Vedo la mia richiesta
> Vuoi la Lettera del Cerchio di Aurya? Un clic: entro nel Cerchio.

### 38. Ordine confermato
**Prima**: «Il tuo ordine e' stato confermato ed e' in lavorazione.»; pulsante «Vedi dettaglio ordine» che porta all'hub.
**Dopo**: «Ciao, {nome} ha confermato il tuo ordine {A-1024}.» Poi i blocchi di oggi (caparra ricevuta, piano dei pagamenti, biglietti, prenotazioni, download, corsi) con una regola: **un solo pulsante grande in testa** («⟶ Apri il mio ordine», che porta all'ordine), i link per voce restano come link. «in lavorazione» sparisce. «Ogni link e' privato — conservalo» → «Questo link è tuo: non condividerlo».

### 39. Ordine annullato **[FIX: non dice chi e il rimborso]**
**Prima**: «Il tuo ordine e' stato annullato. Riferimento: … Per qualsiasi domanda, rispondi a questa email.»
**Dopo**:
> Oggetto: **Ordine {A-1024} annullato da {nome | te}**
> Ciao,
> l'ordine {A-1024} è stato annullato {da {nome} | come ci hai chiesto}. {Se hai già pagato, il rimborso parte da {nome}: in genere arriva entro 5-10 giorni lavorativi sullo stesso metodo. | Non c'era nessun pagamento da restituire.}
> Per qualunque cosa rispondi a questa email: arriva a {nome}.

### 40. Consegna e ritiro (cinque varianti)
**Prima**: oggetto e corpo identici; «ritirato con successo».
**Dopo**: corpo con una riga in più e senza ripetere l'oggetto: spedito → «È partito: {corriere}, codice {…}. Lo segui da qui: ⟶ Dov'è il pacco»; pronto per il ritiro → «Lo trovi da {nome} a {indirizzo}, negli orari di apertura. Porta questa email»; consegnato → «È arrivato. Se qualcosa non va, rispondi a questa email»; ritirato/completato → «Tutto fatto. Grazie, e a presto».

### 41. Promemoria e sollecito di pagamento **[FIX accordo]**
**Prima**: «Ti chiediamo di regolarizzare il pagamento… l'organizzatore aggiornera' la tua posizione»; «Saldo di 300 € era dovuta».
**Dopo**:
> promemoria · Oggetto: **{Importo} per {nome} entro il {data}** · «Ciao, ti ricordiamo il {saldo} di {importo} per l'ordine {A-1024}, entro il {data}. Si paga in un clic: ⟶ Pago ora. Se l'hai già fatto con bonifico, ignora pure: {nome} lo segna appena lo vede.»
> scade oggi · Oggetto: **Scade oggi: {importo} per {nome}**
> in ritardo · Oggetto: **{Importo} per {nome}: la data è passata** · «Ciao, il {saldo} di {importo} per l'ordine {A-1024} era previsto entro il {data}. Puoi pagarlo adesso in un clic: ⟶ Pago ora. Se l'hai già fatto con bonifico, ignora pure.»

### 42. Prenotazione confermata **[FIX date]**
Date in italiano («12 giugno 2026», «12 giugno, 10:00-12:00») al posto di `2026-06-12`. Corpo: «Ciao, la tua prenotazione è confermata: {prodotto}, {quando}, {dove}. Codice {ABC123}. ⟶ Apri la prenotazione. Questo link è tuo: non condividerlo.»

### 43. Il tuo biglietto
«dettalo all'ingresso» → **«o leggilo all'ingresso»**; «check-in» → **«ingresso»**. Resto ok.

### 44. Comunicazioni ai partecipanti
«Ciao partecipante,» → **«Ciao,»**; «Ti aspettiamo al tuo evento!» → **«Ti aspettiamo a {evento}.»**; annullato: «Riceverai presto istruzioni sul rimborso. Scusaci per il disagio.» → **«Ci dispiace. Per il rimborso ti scrive {organizzatore} entro pochi giorni; se hai domande, rispondi a questa email.»**; «Qualche info pratica» → **«Qualche informazione pratica»**.

---

## E. Recensioni

### 45. Codice per la recensione
**Prima**: non dice per chi è.
**Dopo**: «Ciao, ecco il codice per la tua recensione a **{nome professionista}**: **{123456}**. Vale 10 minuti. Se non l'hai chiesto tu, ignora questa email.» + riga Cerchio.

### 46. Serve l'email della prenotazione
«riservate a chi ha prenotato con lui» → **«riservate a chi ha prenotato con questa persona»**; «non risulta nessuna prenotazione» → **«non troviamo una prenotazione»**.

### 47. Ricevuta della recensione
Aggiungere il saluto. 47a: «Ciao, grazie: la tua recensione per {nome} è già pubblica sulla sua pagina, con il segno «Cliente verificato». Se risponde, la risposta compare sotto la tua.» 47b oggetto «in attesa di approvazione» → **«La tua recensione per {nome} è arrivata»**; corpo: «Ciao, grazie: la tua recensione per {nome} è arrivata. Con questa email non troviamo una prenotazione, quindi la legge prima {nome}: se la approva, compare sulla sua pagina (senza il segno «Cliente verificato»). Non ti mandiamo altre email su questo.»

---

## Cosa succede dopo la tua lettura
1. Tu correggi qui (anche solo «ok» per ogni blocco, o riscrivi).
2. Io applico nel codice, email per email, senza toccare trigger, link e token. Dove c'è **[FIX]** correggo anche l'errore.
3. Guardia: le parole proibite non possono più entrare («con successo», «click», «store», «pack», «upgrade», «regolarizzare», «Benvenuto nel», «Sei stato», «sei stato tu», «iscritto tu», «con lui»), accenti veri, ogni template si renderizza con dati pieni e vuoti senza frasi rotte.
4. Ti mando le anteprime vere delle 6 email del Cerchio e delle 3 dell'account dal pannello (l'anteprima «[PROVA]» esiste già) prima del deploy.
