# Aurya — Come si monetizza davvero

## Commissioni, abbonamenti, prezzi, promesse e date, dalla parte dell'operatore olistico

Analisi e piano · 10 settembre 2026 · Davide, Valentina, Claude

---

## 0. In una pagina

**Il problema.** Oggi la pagina operatori dice «gratis fino al 31 dicembre 2026» e poi si ferma: chi legge non sa cosa succede a gennaio. Il modello attuale (Gratis col 5% solo sugli incassi online, Pro a 19 €/mese senza commissioni) ha un difetto strutturale: la commissione si paga solo se colleghi Stripe, e collegare Stripe è facoltativo, faticoso e per molti spaventoso. Un operatore razionale non lo collega, prende le richieste e incassa a parte. Aurya non guadagna, l'operatore non ha fatto niente di sbagliato, e il vincolo «senza Stripe non appari nel marketplace» punisce proprio chi sta iniziando.

**La scoperta nel codice.** Il ritiro «su richiesta» esiste già: l'operatore riceve la richiesta via email, conferma lui, e il pagamento lo concordano a parte. Stripe serve solo per la «prenotazione online» (posto confermato subito con caparra). Non ho trovato nel codice un vincolo che nasconda dal marketplace chi non ha Stripe: la regola vive nella tua testa, non nel prodotto, e quindi la possiamo decidere da zero.

**La tesi.** Non si vende lo strumento, si vende la fila. Gli strumenti (profilo, listino, richieste, calendario, clienti, eventi e ritiri su richiesta, un link solo) restano gratis per sempre: costano zero, costruiscono la rete, e sono il motivo per cui il pagato vende. Si paga la **visibilità** (stare in Ritiri ed esperienze, nella selezione, nella Lettera del Cerchio, su Instagram) e la **libertà dalle commissioni**. La commissione del 5% resta solo dove Aurya incassa davvero, e nessuno è obbligato a Stripe per niente.

**I tre piani (versione definitiva, decisione del founder 10/9 sera: zero commissioni, sempre).** Gratis (per sempre, con tutto per lavorare, Stripe compreso se lo vuoi: Aurya non prende mai commissioni) · Club Aurya, 49 €/anno (la prima fila: ritiri ed eventi nel marketplace, nella selezione, nella Lettera per zona, un post su Instagram per ritiro) · Pro, 119 €/anno (il Club, più Crea Studio, WhatsApp con Valentina, il racconto con precedenza). Annuali, non mensili: il prezzo di un weekend, pagato una volta. Nessuna commissione da nessuna parte: una frase sola, che si capisce e non si aggira.

**Quando.** Fino al 31/12/2026 tutto gratis come promesso. Dal 1° gennaio 2027 i piani esistono e sono scritti, ma **il Club si vende solo quando la fila c'è**: tre numeri pubblici che devono essere veri prima di chiedere un euro per la visibilità (300 iscritti confermati al Cerchio, 10 ritiri in programma, 1.000 visite al mese). I fondatori (i primi venti entro il 31/10/2026) hanno il Club regalato per tutto il 2027.

**Quanto vale.** Nel 2027, con 60 operatori, i piani rendono circa 2.000-3.000 € e le commissioni altri 2.000-4.000: non ci vive nessuno. Il loro valore nel 2027 è un altro: rendono la rete auto-selezionante (chi paga 49 € è serio), pagano gli strumenti, e mettono in piedi la macchina che nell'anno 2 del piano strategico vale 8.900 € di Club e 4.000 di commissioni. I soldi veri restano dove il piano li aveva messi: chi cerca (abbonamento alle meditazioni, esperienze) e il corso.

---

## 1. Come funziona oggi, verificato nel codice

| Cosa | Oggi | Dove |
|---|---|---|
| Piani | Gratis e Pro (pubblici); Founding e Partner (leve del founder, riservati) | `pianiAurya.js`, catalogo `retreat_*` |
| Gratis | tutto: profilo, listino senza limiti, eventi e ritiri, clienti, calendario, pagina link; 5% sugli incassi online (`application_fee_percent`) | /costi, seed prezzi |
| Pro | 19 €/mese o 190 €/anno: zero commissioni, «in evidenza», supporto prioritario, Crea Studio (accesso derivato dal piano) | AB, TR |
| Fino al 31/12/2026 | nessun costo, nemmeno sulle prenotazioni online | promessa del founder, in /costi e nella FAQ |
| Prenotazione di un evento o ritiro | due modi nel wizard: **online** (paga sul sito, posto confermato, serve Stripe) e **su richiesta** (richiesta via email, confermi tu, pagamento concordato a parte) | `EventWizard` «Come si prenota» |
| Vincolo Stripe per il marketplace | **non trovato nel codice**: un ritiro su richiesta è pubblicabile come gli altri | listing pubblico senza condizioni su Stripe |
| Marketplace | spento in fase rete (decisione del 16/7): si riaccende a 1.000 visite/mese, 50 professionisti, 10 ritiri veri | piano strategico |
| Ordini con bonifico | esistono (ordine manuale con nota «bonifico ricevuto il…») | `order_service` |
| Numeri veri | 12 organizzazioni, 8 profili, 30 voci di listino, 2 eventi, 0 ritiri, 4 ordini, 0 € di commissioni | produzione, 10/9 |

Tre conseguenze. La prima: il tuo timore «non conviene collegare Stripe» è fondato ma non è un buco da tappare, è il segnale che stiamo facendo pagare la cosa sbagliata. La seconda: la fine del «gratis fino a dicembre» non è scritta da nessuna parte, e un operatore che non sa cosa succede a gennaio rimanda (è la stessa anti-urgenza dell'analisi comunicativa, vista dal lato prezzo). La terza: oggi non c'è nulla da monetizzare, perché non c'è ancora la fila. Il piano deve dire la verità anche su questo.

---

## 2. Nei panni dell'operatore: quattro persone, quattro conti

**Chiara, 31 anni, insegnante di yoga da un anno.** Nessuna partita IVA, incassa con bonifico e contanti, forse sotto i 5.000 € l'anno. Ha un Instagram con 900 follower, vuole fare il primo weekend a ottobre con dieci persone a 180 €. Stripe la spaventa per tre ragioni vere: non sa se può usarlo senza partita IVA, non vuole collegare il conto personale, e teme che «incassare online» renda visibile ciò che oggi è informale. Cosa le serve da Aurya: un profilo che la faccia trovare, un link per la bio, il weekend pubblicato «su richiesta» con la caparra via bonifico, e qualcuno che le mandi persone. Cosa pagherebbe: 49 € una volta l'anno se le porta anche solo due iscritte. Cosa non pagherebbe mai: 19 € al mese «per vedere».

**Silvia, 45, massaggi ayurvedici e Reiki in studio, con partita IVA.** Ha già un evento su Aurya e due recensioni. Il suo lavoro è il listino: appuntamenti singoli, 60-80 €. Le prenotazioni online le farebbero comodo (meno messaggi), ma il 5% su 70 € sono 3,50 € a seduta e lo sente. Cosa le serve: richieste di appuntamento che arrivino ordinate, un calendario che blocca gli orari, recensioni. Cosa pagherebbe: il Pro annuale, se zero commissioni e Stripe le tolgono i messaggi; 119 € l'anno si ripagano con 2.380 € incassati online, cioè 34 sedute.

**Marco, 38, organizza ritiri di respiro e cammini, 2-3 l'anno da 20 persone a 450 €.** Fattura, ha Stripe altrove, sa cosa sono le piattaforme (BookRetreats gli prende il 15-20%). Il 5% di Aurya per lui è un affare (27.000 € di ritiri l'anno: 1.350 € a noi, contro 4-5.000 altrove). Cosa gli serve: essere nel marketplace e nella selezione, la caparra online, la lista partecipanti, i promemoria. Cosa pagherebbe: il Pro subito, se la visibilità è vera; altrimenti resta Gratis e paga il 5% quando vende.

**Valentina (e chi le somiglia): la professionista con la voce.** Compone meditazioni, vuole pubblicarle e condividerle con i clienti. Crea Studio è il suo motivo per il Pro, indipendentemente dai ritiri.

Il conto che tutti e quattro fanno, senza dirlo: **«mi porta persone?»**. Finché la risposta è «non ancora», nessuno paga la visibilità, e ha ragione. Per questo il piano lega ogni euro chiesto a un numero visibile.

---

## 3. Le alternative, una per una

| Modello | Come funziona | Perché sì | Perché no | Verdetto |
|---|---|---|---|---|
| **Solo commissione (5%) su Stripe** (oggi) | paghi quando incassi online | il più giusto in astratto, 5% batte il 15-20% dei concorrenti | si aggira con «su richiesta»; nessuna entrata stabile; obbliga a Stripe chi non è pronto | da tenere, ma non da solo |
| **Vincolo: senza Stripe niente marketplace** | visibilità solo a chi paga commissioni | protegge le commissioni | punisce chi inizia, spinge fuori proprio Chiara, e il marketplace oggi è vuoto: proteggi un incasso che non c'è | **togliere** |
| **Aurya incassa per tutti (merchant of record)** | il cliente paga Aurya, Aurya gira all'operatore | Stripe sparisce per l'operatore, la commissione non si aggira | Aurya diventa intermediario finanziario: fatture, IVA, responsabilità sui rimborsi, contabilità per 60 operatori, licenze; due persone non reggono | no, non ora |
| **Solo abbonamento, zero commissioni** | tutti pagano un canone | entrata stabile, semplice da spiegare | un canone d'ingresso uccide il funnel (12 operatori, 0 traffico): nessuno paga per entrare in una stanza vuota | no come unico modello |
| **Gratis + Club + Pro (annuali) + 5% solo online** | strumenti gratis, si paga la fila e la libertà dalle commissioni | stabile, onesto, non obbliga a Stripe, si aggancia ai numeri | richiede che la fila esista prima di venderla | **il piano** |
| **Pay-per-lead** (paghi a contatto ricevuto) | X € per ogni richiesta | pagamento legato al valore | conta i contatti, non i clienti; litigi su «era un lead vero?»; complesso da costruire | no |
| **Sponsor di settore** | scuole e strutture pagano per esserci | terzo lato, già nel piano strategico | serve traffico misurabile | dopo, come previsto |

---

## 4. I tre piani, per intero

### 4.1 Gratis — «Tutto per lavorare. Per sempre.»

| Cosa hai | Nota |
|---|---|
| Profilo pubblico indicizzato, nella directory dei professionisti | il motore della rete: non si tocca |
| Listino senza limiti, richieste di appuntamento, calendario che blocca gli orari | |
| Eventi e ritiri pubblicati sul tuo profilo e sulla tua pagina link, **su richiesta** (senza Stripe) o **online** (con Stripe) | il ritiro «su richiesta» è il modo di chi inizia: caparra con bonifico, confermi tu |
| Clienti, ordini, recensioni verificate, pagina link per Instagram | |
| Prenotazione online con caparra, se vuoi collegare Stripe | 5% ad Aurya solo sulle prenotazioni online che ti porta Aurya (marketplace, selezione, Lettera, directory); quelle dal tuo profilo e dal tuo link sono tue al 100%, come contanti e bonifici |
| Assistenza via email; il racconto (intervista) su invito | niente WhatsApp: due persone non possono seguire sessanta operatori gratis |

**Cosa non ha**: la prima fila. I tuoi ritiri non stanno in Ritiri ed esperienze, nella selezione, nella Lettera, su Instagram. Stanno sul tuo profilo, che è già tanto.

**Perché resta così generoso**: il costo marginale è zero, ogni profilo pieno è un pezzo di rete e di SEO, e il lock-in vero sono i dati (clienti, recensioni, listino). Togliere strumenti al Gratis per spingere il Pro è l'errore che uccide il funnel.

### 4.2 Club Aurya — 49 € l'anno — «La prima fila.»

| Cosa hai in più | Nota |
|---|---|
| I tuoi ritiri ed eventi in **Ritiri ed esperienze** e nella **selezione** (di primavera, d'autunno) | la porta di chi cerca porta qui |
| I tuoi ritiri nella **Lettera del Cerchio** agli iscritti della tua zona e dei tuoi temi | è quello che i tuoi 900 follower non possono darti: gente che ha chiesto un ritiro |
| **Un post su Instagram** per ogni ritiro pubblicato (massimo uno al mese per operatore) | lo fa Valentina: il tetto protegge il nostro tempo e il feed |
| Badge Club sul profilo e precedenza nella directory della tua zona | |
| Risposta entro due giorni lavorativi | |
| Le commissioni restano: 5% solo sulle prenotazioni online che la fila ti porta | il Club è il biglietto per la fila, il 5% la quota su ciò che la fila porta |

**Perché 49 e annuale**: è il prezzo di un weekend, si paga una volta e non si pensa più; un canone mensile da 4-9 € si disdice al primo mese vuoto, un annuale si giudica sull'anno. Per Chiara: se il Club le porta due iscritte a 180 € ha guadagnato sette volte la quota.

**Perché non lo vendiamo prima che la fila esista**: sarebbe una promessa falsa. Vedi §6.

### 4.3 Pro — 119 € l'anno (o 12 €/mese) — «Zero commissioni e la voce.»

| Cosa hai in più del Club | Nota |
|---|---|
| **Zero commissioni Aurya** sugli incassi online (restano quelle di Stripe, che non sono nostre e vanno dette) | si ripaga con 2.380 € l'anno incassati online |
| **Crea Studio**: componi meditazioni con la tua voce, le pubblichi con un link, le condividi coi clienti | è già così oggi (accesso derivato dal Pro) |
| WhatsApp con Valentina | il canale che oggi diamo a tutti diventa una cosa che si paga |
| Il racconto (intervista) con precedenza; una pagina nel Magazine | |
| Team (collaboratori) quando servirà | |

**Perché 119 e non 19 al mese**: 228 € l'anno è troppo per chi incassa 5-10 mila; 119 è «meno di 10 al mese» e si decide una volta. Per Marco è irrilevante (lo paga in un ritiro), per Silvia è la soglia giusta. Il mensile a 12 € resta per chi vuole provare.

**Il tuo 99 €**: possibile, ma 99 è troppo vicino a 49 per due cose diverse (visibilità vs. esenzione + Studio); 119 tiene la distanza e resta sotto la soglia psicologica dei 10 al mese. Decidi tu fra 99 e 119: cambia il seed, non il modello.

### 4.5 La caparra e la domanda «Stripe senza commissione?»

**La caparra non crolla.** Esiste in due forme, entrambe già nel prodotto: **online** (Stripe: il posto è confermato subito, la caparra è in tasca all'operatore prima che il partecipante ci ripensi) e **con bonifico** (su richiesta: l'operatore conferma e indica IBAN e scadenza; la caparra arriva in due giorni, il posto si conferma all'arrivo). La prima è migliore, e va detto: meno posti che saltano, meno messaggi, il saldo automatico. Ma la seconda è quella con cui Chiara comincia, e nessuna delle due dipende dal piano.

**Stripe senza commissione per tutti?** Si può, ed è la variante che risolve davvero il problema dei furbi, perché toglie ogni ragione per non collegare Stripe. Il costo è che Aurya rinuncia all'unico ricavo legato al valore consegnato. La via di mezzo, che era già nell'analisi di luglio, è questa:

> **Il 5% si paga solo sulle prenotazioni che ti porta Aurya.** Una prenotazione arrivata dal tuo profilo o dalla tua pagina link è tua: 0%, con o senza Stripe. Una prenotazione arrivata da Ritiri ed esperienze, dalla selezione, dalla Lettera o dalla directory l'ha portata Aurya: 5%, solo se incassata online. Il Pro azzera anche quella.

Tre effetti. Nessuno ha più motivo di evitare Stripe: sulle prenotazioni sue non paga nulla, e la caparra online gli conviene. Il 5% diventa una success fee sulla fila, cioè sulla cosa che il Club compra: il Club è il biglietto per la fila, il 5% è la quota su ciò che la fila porta, e chi non vuole pensarci prende il Pro. E Aurya smette di difendere una commissione aggirabile: difende la provenienza, che si misura (ogni ordine porta da dove è arrivato: profilo, link, marketplace, Lettera). Costo tecnico: registrare la provenienza sull'ordine e applicare la fee solo a quelle (M8, una giornata). **È la variante che raccomando.**

### 4.4 Fondatori e Partner (le leve, non piani in vendita)

- **Fondatori** (i primi venti che pubblicano il profilo entro il 31/10/2026): Club regalato per tutto il 2027, badge permanente, prezzo Pro bloccato per sempre a quello del 2027, precedenza nella selezione. È il patto già scritto nella landing: qui si aggiunge il Club, che è la cosa concreta.
- **Partner** (Masseria e strutture): 0% commissioni, invariato.

---

## 4.6 La versione definitiva: zero commissioni, e dove sta il trigger

Dopo aver letto §4.5 il founder ha chiuso così: «Stripe mi dà fastidio: ci vedo comportamenti opportunistici, una caparra piccola online per pagare poco e il resto offline. Voglio tutto il più semplice possibile: abbonamento. Le commissioni non porteranno a nulla. Ma abbiamo bisogno anche di operatori gratuiti che creano ritiri: dove sta il trigger?»

**Ha ragione sulla caparra piccola.** Qualunque commissione sull'incasso online invita a incassare online il meno possibile, e non c'è regola tecnica che lo impedisca senza diventare intrusivi (controllare i prezzi, imporre percentuali minime di caparra, litigare). La provenienza (§4.5) riduce il problema, non lo elimina. Un abbonamento lo elimina: non c'è niente da aggirare.

**Il modello definitivo.**

| Piano | Prezzo | Cosa compri |
|---|---|---|
| Gratis | 0, per sempre | tutto per lavorare: profilo, listino, richieste, calendario, clienti, recensioni, pagina link, eventi e ritiri sul tuo profilo (su richiesta o online con Stripe). **Aurya non prende commissioni, mai.** Restano solo quelle di Stripe, che non sono nostre |
| Club Aurya | 49 €/anno | la fila: i tuoi ritiri ed eventi in Ritiri ed esperienze e nella selezione, nella Lettera agli iscritti della tua zona e dei tuoi temi, un post su Instagram per ritiro (max uno al mese), badge, precedenza nella directory della tua zona, risposta in due giorni |
| Pro | 119 €/anno (o 12/mese) | il Club, più Crea Studio (componi e pubblichi meditazioni con la tua voce), WhatsApp con Valentina, il racconto con precedenza e una pagina nel Magazine, team quando servirà |

Cosa perde Aurya: la commissione, che nel 2027 valeva 1.500-3.000 € nello scenario più ottimista e che gli operatori avrebbero aggirato comunque. Cosa guadagna: una frase che si capisce in un secondo («Aurya non prende commissioni»), nessun incentivo perverso, nessun controllo da fare, e la differenza netta rispetto a BookRetreats e Tripaneer (15-20%): non «costiamo meno», ma «non costiamo sul tuo lavoro».

**Dove sta il trigger.** Un operatore gratuito crea ritiri perché gli serve una pagina da mandare ai suoi follower, e la nostra è gratis, bella e con la caparra: il ritiro nasce sul suo profilo, non nel marketplace. Il passaggio a pagamento non si spinge con i limiti (togliere strumenti al Gratis) ma con **cinque inneschi**, tutti fatti di domanda misurata mostrata al momento giusto:

1. **All'ultimo passo del wizard del ritiro.** «Il tuo ritiro è online sul tuo profilo. Nel Cerchio ci sono **{N} persone a meno di 80 km da {luogo} che hanno chiesto {yoga}**. Vuoi che glielo mandiamo? Club, 49 € l'anno.» Il numero è vero, calcolato dalle preferenze del Cerchio (città, raggio, interessi: esistono già). Se N è piccolo, la frase non compare: non si vende una fila vuota.
2. **Alla prima richiesta che arriva da Aurya.** Ogni richiesta dice da dove viene: «Questa richiesta arriva dalla directory Aurya». La seconda volta, la riga sotto: «Chi è nel Club riceve anche le richieste di chi cerca un ritiro nella sua zona».
3. **Due volte l'anno, la selezione con la scadenza.** «La selezione dei ritiri di primavera 2027 parte il 15 gennaio: i ritiri del Club ci entrano. Chiusura il 10 gennaio.» Una data vera muove più di qualsiasi sconto.
4. **Il cruscotto della visibilità nel gestionale.** Visite al profilo, da dove arrivano, e accanto: «{N} iscritti al Cerchio nella tua zona hanno chiesto i tuoi temi». Il numero cresce ogni settimana, e ogni settimana è un promemoria che non scriviamo noi.
5. **La voce (Pro).** Quando pubblica la prima meditazione dal telefono o chiede a Valentina di scrivere il racconto: «Con il Pro Crea Studio è tuo, e Valentina risponde su WhatsApp».

Tutti e cinque dipendono da una cosa sola: **che nel Cerchio ci siano persone, con città e interessi.** È per questo che la porta «Trovami il mio ritiro» (RB4) e i cinque ritiri seme vengono prima di qualsiasi prezzo: il trigger è un numero, e il numero oggi è 3.

**Cosa cambia nei passi**: M8 (provenienza + fee) esce; M2 (flag prima fila), M6 (Lettera per zona) ed M7 (i tre numeri) diventano il cuore, più M9: il contatore «persone nel Cerchio vicino a te che hanno chiesto i tuoi temi» esposto nel wizard e nel gestionale (mezza giornata: la query è quella delle preferenze).

## 5. Stripe: da vincolo a scelta (e il bonifico come strada principale)

**Decisione del founder (10/9 sera)**: «I primi operatori ci hanno già dimostrato che Stripe per loro era complesso e che preferiscono i bonifici. Stripe obbligatorio sarebbe un collo di bottiglia, e comunque c'è una responsabilità da parte nostra.» Conseguenza: **il bonifico è la strada principale, Stripe è l'opzione.** Non «su richiesta» come ripiego per chi non ha Stripe, ma il flusso di prima scelta, fatto bene:

- **Nelle impostazioni** l'operatore scrive una volta IBAN e intestatario.
- **Nel wizard** «su richiesta con caparra» è il modo predefinito: quanto vale la caparra (cifra o percentuale) e entro quanti giorni.
- **Chi prenota** riceve subito l'email con IBAN, importo, causale (nome del ritiro e suo nome) e scadenza; il posto è «in attesa della caparra».
- **L'operatore** vede la richiesta nel gestionale e, arrivato il bonifico, conferma con un clic («caparra ricevuta il…»): parte l'email di conferma e il promemoria del saldo. È l'ordine manuale con la nota che esiste già, reso un percorso invece di un'eccezione.
- **Scaduta la caparra** senza conferma, il posto si libera con un promemoria automatico prima.

Cosa ci guadagna Aurya oltre alla semplicità: **esce dal flusso del denaro.** Con Stripe Connect la piattaforma porta una responsabilità (contestazioni, rimborsi, verifiche sul conto della piattaforma, il «responsabilità perdite = esercente» che abbiamo accettato a luglio); col bonifico i soldi passano dal partecipante all'operatore e noi non tocchiamo un euro, coerente con «zero commissioni». Stripe resta per chi lo vuole (Marco, Silvia), acceso dalle impostazioni, mai proposto nel wizard a chi non l'ha collegato.

Nei passi: M4 cresce (IBAN nelle impostazioni, caparra nel wizard, email con le istruzioni, conferma con un clic, scadenza automatica: due giornate) e diventa il primo passo dell'onda 2 sul prodotto, prima di qualsiasi piano a pagamento.

### 5.1 Le tre verità su Stripe, per chi lo vuole

Tre verità da scrivere in una pagina propria (`/incassare-online`, linkata dal wizard e dalle impostazioni):

1. **Non sei obbligato.** Puoi pubblicare ritiri ed eventi «su richiesta»: ricevi la richiesta, confermi, la caparra arriva con un bonifico, il resto lo concordate. Aurya non prende nulla.
2. **Se vuoi incassare online, Stripe si può aprire anche senza partita IVA** come persona fisica (codice fiscale, documento, un IBAN a tuo nome). Il conto non lo vediamo noi: Stripe paga te direttamente. Le commissioni di Stripe (circa 1,5% + 0,25 € per carta europea) sono di Stripe.
3. **La parte fiscale non dipende da Stripe.** Incassare in contanti, con bonifico o online è la stessa cosa per il fisco: fino a 5.000 € lordi l'anno si parla di prestazione occasionale, oltre serve la partita IVA. Non siamo commercialisti: parla col tuo. Ma non è Stripe a renderti «visibile», è il lavoro.

Nel prodotto: il wizard propone «su richiesta» come predefinito a chi non ha Stripe (oggi lo mostra come opzione), con la riga «caparra con bonifico: scrivi qui l'IBAN e la scadenza» nel messaggio di conferma; e la pagina Impostazioni spiega Stripe con le tre verità, non con un bottone «Collega».

Cosa non facciamo: incassare noi per conto degli operatori. Non nel 2027.

---

## 6. Quando: date, cancelli e promesse vere

| Periodo | Cosa vale | Cosa diciamo in pagina |
|---|---|---|
| **Oggi → 31/12/2026** | tutto gratis, commissione 0% anche online (promessa fatta, si mantiene); Stripe facoltativo; fondatori fino al 31/10 | «Gratis fino al 31 dicembre 2026. Poi il Gratis resta gratis per sempre, e chi vuole la prima fila ha il Club a 49 € l'anno.» |
| **1/1/2027** | i piani esistono e sono pubblici (Gratis 5% online, Club 49, Pro 119); il 5% sugli incassi online parte | l'operatore sa da oggi cosa succede a gennaio |
| **Il Club si vende solo quando** | 300 iscritti confermati al Cerchio, 10 ritiri in Ritiri ed esperienze, 1.000 visite al mese sul sito (tre numeri, tutti pubblici su /costi) | «Il Club si accende quando la fila c'è: ecco i tre numeri, aggiornati ogni settimana.» |
| **Se al 1/1/2027 i numeri non ci sono** | il Club resta gratis per tutti fino al primo mese in cui i tre numeri sono veri; il Pro si vende comunque (zero commissioni e Studio non dipendono dalla fila) | si dice a dicembre, con la stessa frase di oggi |
| **Fondatori** | Club gratis tutto il 2027, Pro bloccato | già in landing |

Perché i cancelli pubblici: sono l'unico modo di vendere visibilità senza mentire, e sono anche marketing: un operatore che vede «230 iscritti su 300» capisce che la fila si sta formando e che gli conviene esserci prima.

---

## 7. Il nostro tempo: cosa promettiamo e cosa no

| Livello | Chi risponde | Come | Cosa NON facciamo |
|---|---|---|---|
| Gratis | le email automatiche (sequenza g0/g7/g14/g30), una casella | email, entro una settimana | telefonate, profili scritti a mano, post |
| Club | Valentina | email entro due giorni; un post IG per ritiro (max 1/mese) | racconto scritto da noi (su invito) |
| Pro | Valentina | WhatsApp; il racconto con precedenza | niente di illimitato: «prioritario», non «sempre» |
| Fondatori | come Pro nel 2027 | | |

Regola: **il gratuito è self-serve**. Chi non paga ha gli strumenti e le email; il tempo di Valentina si vende. L'intervista resta l'eccezione perché è il motore della rete: si fa a chi pubblica il profilo, con la coda decisa da noi (prima chi paga, poi chi è attivo).

---

## 8. I conti, senza illusioni

### 8.1 Scenario 2027 (60 operatori a fine anno)

| Voce | Ipotesi | Quanto |
|---|---|---|
| Club | 25 operatori a 49 € (20 fondatori gratis) | 1.225 € |
| Pro | 8 a 119 € | 952 € |
| Commissioni 5% | 30 ritiri × 12 posti × 350 €, metà online e di questi metà portati da Aurya | 1.575 € |
| Commissioni sui servizi | 10 profili con Stripe, 3.000 € l'anno online ciascuno, un terzo portato dalla directory | 500 € |
| **Totale lato operatori** | | **≈ 4.300 €** |

Con la metà dei ritiri o un quarto degli abbonati: 2.300 €. Con Marco che porta tre ritiri da 20 persone: +1.350 da lui solo. **Non ci si vive**, e lo sapevamo: il piano strategico mette il lato operatori a 12.900 € nell'anno 2 e i soldi veri altrove (corso 29.800, abbonamento meditazioni 15.600, esperienze 19.200).

### 8.2 Cosa comprano davvero questi soldi

- **Selezione**: chi paga 49 € è un operatore che pubblica, risponde, porta persone. La rete si pulisce da sola.
- **Un numero stabile**: 30 abbonati sono 2.000 € certi, i primi «ricavi ricorrenti» da mostrare a chiunque.
- **La macchina**: Lettera per zona, selezione, post, badge: costruita per 25 abbonati, funziona per 250.

### 8.3 Cosa cambia rispetto al modello di oggi

| | Oggi | Piano |
|---|---|---|
| Entrata stabile | solo Pro a 19/mese, 0 abbonati | Club + Pro annuali |
| Aggirabile | sì (su richiesta, senza Stripe) | la visibilità non si aggira |
| Obbliga a Stripe | di fatto, per il marketplace | mai |
| Gennaio 2027 | ignoto | scritto e datato |
| Chi sta iniziando | escluso dal marketplace | entra Gratis, sale al Club quando gli conviene |
| Il nostro tempo | dato a tutti, gratis | venduto nel Pro, misurato nel Club |

---

## 9. Cosa cambia nel prodotto (stima)

| Passo | Cosa | Effort |
|---|---|---|
| M1 | Piano `retreat_club` (49 €/anno) e Pro annuale a 119 (mensile 12) nel catalogo e in Stripe; migrazione flag-gated come per il 19 | 1 giornata |
| M2 | Il flag «prima fila»: ritiri ed eventi in Ritiri ed esperienze / selezione / Lettera filtrati per piano (Club, Pro, Founding, Partner); i Gratis restano sul profilo | 1 giornata |
| M3 | /costi riscritta con i tre piani, i tre cancelli pubblici (contatori veri), la pagina /incassare-online; FAQ della landing allineata | mezza giornata |
| M4 | Il bonifico come strada principale: IBAN nelle impostazioni, caparra nel wizard (default), email con le istruzioni, conferma con un clic, scadenza automatica; Stripe opzionale dalle impostazioni con le tre verità | 2 giornate |
| M5 | Fondatori: Club regalato per il 2027 (piano Founding = Club+Pro per 12 mesi), badge sul profilo | mezza giornata (con RB9) |
| M6 | Lettera per zona/temi coi ritiri Club: la query esiste (retreat_alert, città, interessi), manca l'invio; template + job | 1 giornata |
| M7 | Il cruscotto dei tre numeri (iscritti confermati, ritiri in programma, visite) in system admin e su /costi | mezza giornata |
| M9 | Il contatore «{N} persone nel Cerchio vicino a te che hanno chiesto i tuoi temi» nel wizard del ritiro e nel gestionale (query sulle preferenze del Cerchio) | mezza giornata |

Tutto sopra il motore di billing che c'è già (piani per modulo, abbonamenti Stripe, flag per organizzazione). Nessun rifacimento.

---

## 10. Le decisioni

| # | Decisione | Proposta |
|---|---|---|
| 1 | Togliere il vincolo Stripe per il marketplace; il bonifico con caparra è la strada principale, Stripe l'opzione (decisione founder 10/9 sera) | sì |
| 2 | Tre piani annuali: Gratis / Club 49 / Pro 119 (mensile 12) | sì; 99 se preferisci, ma non sotto |
| 3 | **Zero commissioni Aurya, sempre** (decisione founder 10/9 sera, §4.6); Stripe è uno strumento, restano solo le sue commissioni | sì |
| 4 | Dal 1/1/2027 i piani sono pubblici; il Club si vende solo coi tre cancelli veri; il trigger nel wizard compare solo se il numero è vero | sì |
| 5 | Fondatori: Club gratis per il 2027 e Pro bloccato | sì |
| 6 | Il nostro tempo: Gratis = email automatiche; Club = risposta in due giorni + un post per ritiro; Pro = WhatsApp | sì |
| 7 | Mai merchant of record nel 2027 | sì |
| 8 | Scrivere da subito, in landing e in /costi, cosa succede a gennaio | sì, nell'onda 1 del rebranding |

Con il sì, M3 e M8 (le parole) entrano subito nel rebranding; M1-M2-M5-M7 sono una settimana; M4 e M6 stanno nell'onda 2.
