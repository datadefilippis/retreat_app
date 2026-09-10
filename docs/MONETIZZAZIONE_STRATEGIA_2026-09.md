# Aurya — Il business, spiegato per intero

## Chi paga, cosa, quanto, quando. Il modello definitivo.

Piano di monetizzazione · 10 settembre 2026 (versione integrata; la roadmap completa con i servizi è in AURYA_ROADMAP_ZERO_AL_GUADAGNO_2026-09.md) · Davide, Valentina, Claude

---

> **Nota (10/9/2026, sera)**: questo documento è integrato in `AURYA_PIANO_BUSINESS_2026-09.md` (PDF `AURYA_Piano_Business_2026-09.pdf`), che è il riferimento. Resta qui come storia del ragionamento.


## 0. Il business in una pagina

Aurya guadagna da tre lati, in quest'ordine di tempo:

| Lato | Chi paga | Cosa compra | Quanto | Quando parte |
|---|---|---|---|---|
| **A. Gli operatori olistici** | chi lavora nel benessere | la fila (visibilità verso chi cerca) e gli strumenti in più | Spinta 19 € a ritiro · Club 49 €/anno · Pro 119 €/anno | i piani sono pubblici dal 1/1/2027; il Club si vende quando la fila esiste |
| **B. Chi cerca** | le persone che vogliono meditare, un ritiro, un professionista | le meditazioni complete di Aurya Sound e le esperienze dal vivo o online | abbonamento 39 €/anno · esperienze 30-60 € | abbonamento quando la libreria vale (2027); esperienze appena ci sono i primi ritiri |
| **C. La formazione** | gli operatori | il corso «il mestiere, oltre la pratica» | 99-199 € | 2027, sulla lista |

**La regola che tiene tutto insieme: Aurya non prende commissioni. Mai.** Né sui ritiri, né sui servizi, né online né offline. Il denaro passa dal partecipante all'operatore (con bonifico, o con Stripe se l'operatore lo vuole) e noi non lo tocchiamo. Si paga solo quello che Aurya aggiunge: la fila, la voce, il tempo di Valentina, il sapere.

**Perché così.** Perché la commissione sull'incasso online si aggira (caparra piccola online, il resto a parte), perché i primi operatori ci hanno detto che Stripe è complicato e preferiscono il bonifico, perché stare nel flusso del denaro è una responsabilità che due persone non devono prendersi, e perché il mercato dimostra che gli operatori pagano volentieri **il cliente nuovo** ma odiano la tassa sul lavoro. La promessa che convince, in tutto il settore, è «il tuo cliente è tuo»: noi la diciamo fino in fondo.

**Cosa resta gratis, per sempre**: tutto quello che serve per lavorare. Profilo pubblico nella directory, listino, richieste di appuntamento, calendario, clienti, recensioni verificate, pagina link per Instagram, eventi e ritiri sul proprio profilo con la caparra via bonifico o con Stripe. Il gratis costa zero, costruisce la rete e il posizionamento su Google, e il vero legame sono i dati dell'operatore (clienti, recensioni, listino). La sua unica condizione: il gratuito è self-serve, il tempo di Valentina si vende.

**I numeri, onesti.** Lato operatori, nel 2027 con 60 operatori: circa 3.000 €. Non ci si vive. Il valore del lato A nel 2027 è un altro: rende la rete auto-selezionante, paga gli strumenti, e costruisce la macchina (Lettera per zona, selezione, badge) che nell'anno 2 vale quattro volte tanto. I soldi con cui si vive vengono dal lato B e dal lato C, come dice il piano strategico di agosto: anno 2 ≈ 84.000 € in tutto, anno 3 ≈ 227.000.

**Dove sta il trigger.** L'operatore gratuito crea ritiri perché gli serve una pagina da mandare ai follower, e la nostra è gratis, bella, con la caparra. Il passaggio a pagamento non si spinge togliendo strumenti ma mostrando la domanda misurata nel momento giusto: «Nel Cerchio ci sono 47 persone a meno di 80 km da te che hanno chiesto yoga. Vuoi che glielo mandiamo?». Per questo, prima di ogni prezzo, viene il Cerchio pieno di città e interessi: oggi sono tre persone. La porta «Trovami il mio ritiro» e i cinque ritiri seme sono la premessa del business.

---

## 1. Da dove partiamo (verificato nel codice, 10/9/2026)

| Cosa | Oggi |
|---|---|
| Piani | Gratis e Pro 19 €/mese (pubblici); Founding e Partner (leve del founder, riservati) |
| Gratis | tutto: profilo, listino senza limiti, eventi e ritiri, clienti, calendario, pagina link; 5% sugli incassi online (`application_fee_percent`) |
| Pro | 19 €/mese o 190/anno: zero commissioni, in evidenza, supporto prioritario, Crea Studio |
| Promessa attuale | «nessun costo fino al 31 dicembre 2026»; **cosa succede dopo non è scritto** |
| Come si prenota un ritiro | due modi nel wizard: online (Stripe, posto confermato subito) o **su richiesta** (email all'operatore, pagamento concordato a parte) |
| Vincolo Stripe per il marketplace | **non esiste nel codice**: era solo un'intenzione |
| Ordini con bonifico | esistono (ordine manuale con nota) |
| Marketplace | spento in fase rete; si riaccende a 1.000 visite/mese, 50 professionisti, 10 ritiri |
| Numeri veri | 12 organizzazioni, 8 profili, 30 voci di listino, 2 eventi, 0 ritiri, 4 ordini, 0 € di commissioni, 3 iscritti confermati al Cerchio |

---

## 2. Il mercato: come si fanno pagare gli altri (rilevazione 10/9/2026)

| Chi | Modello | Numeri | Lezione per noi |
|---|---|---|---|
| **Treatwell** (beauty, Italia) | commissione sul **nuovo cliente** dalla vetrina, 0% su chi ritorna, 2% sui prepagamenti online; contratto minimo 12 mesi | 25% del primo servizio | si paga il cliente nuovo, una volta |
| **Fresha** (beauty) | canone (il gratis è stato chiuso nel 2026) + 20% sul primo appuntamento dal marketplace; «le prenotazioni dal tuo link non pagano mai» | 19,95 €/mese; 20% min 6 $; incassi 1,29% + 0,20 € | la promessa «il tuo link è tuo» |
| **Booksy** | canone + Boost 20-30% sul nuovo cliente | 25-80 €/mese | idem |
| **BookRetreats** (ritiri) | listare gratis; 15% sull'intero ritiro se il cliente paga tramite loro; 20-30% per salire in classifica; caparra minima 15%; +3% | 15-30% + 3% | il pay-to-rank è il nostro anti-modello |
| **Tripaneer** (ritiri) | commissione se il primo contatto nasce lì; organizzatori spinti dal 14 al 20% per la posizione | 15-30% | idem, con le recensioni furiose |
| **Momoyoga** (yoga) | gratis con 5% di piattaforma sui pagamenti online; a canone senza | 0 / 29 / 59 / 179 €/mese | è il nostro modello di oggi: lì regge perché lì si paga online |
| **Momence** (studi, USA) | gratis 5% + 4% al cliente; 60 $ col 2,5%; 199 $ senza | | «paghi per togliere la commissione» |
| **Eventbrite** | commissione a biglietto, pagata da chi compra | 3,5% + 0,49 € | la commissione la paga il partecipante |
| **MioDottore** | canone personalizzato per profilo premium e agenda | non pubblicato | la directory professionale in Italia si vende a canone |
| **Linktree** | pagina link gratis; a canone senza limiti | 4,50 / 10,50 / 27,50 €/mese | il nostro «link solo» vale già un Linktree |
| **Italia Olistica, ROOI** | directory gratis; registro 80 € una tantum | | l'operatore olistico paga poco o niente per «esserci» |
| **Gestionali italiani a canone** | canone fisso, zero commissioni | 600-1.200 €/anno; freelance sotto 100 €/anno | Club e Pro stanno nella fascia freelance |
| **Satispay, SumUp** | solo commissione per transazione | 0,95% | incassare costa poco quando non c'è niente da «collegare» |

**Le cinque lezioni.**

1. **Nessuno vende il software: tutti vendono il cliente nuovo.** Il 20-30% del primo appuntamento è accettato perché ha un nome e un volto, e poi è zero. È l'unica commissione che il mercato dimostra accettata: la teniamo in cassaforte (§9).
2. **«Gratis col 5% online» è Momoyoga.** Lì regge perché lo yoga digitale paga online. Da noi, con chi preferisce il bonifico, tassa una minoranza degli incassi e crea il furbo: non è sbagliato, è prematuro e nel posto sbagliato.
3. **Il pay-to-rank dei ritiri è il contrario del nostro criterio invisibile.** Il Club non vende un posto più alto: vende una fila in più.
4. **Il gratis per sempre non regge nemmeno ai grandi.** Il nostro regge a una sola condizione: niente assistenza a mano a chi non paga.
5. **La promessa vincente è «il tuo cliente è tuo».** Treatwell la dice «0% su chi ritorna», Fresha «il tuo link non paga mai», BookRetreats «ci paghi solo se ti paghiamo». Noi: «Aurya non prende commissioni. Mai.»

---

## 3. Nei panni dell'operatore: quattro persone, quattro conti

**Chiara, 31, insegnante di yoga da un anno.** Senza partita IVA, incassa con bonifico e contanti, un weekend a ottobre con dieci persone a 180 €. Stripe la spaventa (partita IVA? conto personale? visibilità del fisco?). Le serve: un profilo che la faccia trovare, il link per la bio, il weekend pubblicato con la caparra via bonifico, e qualcuno che le mandi persone. Pagherebbe: 19 € per spingere quel weekend, 49 € l'anno se le porta due iscritte. Non pagherebbe mai 19 € al mese «per vedere».

**Silvia, 45, massaggi ayurvedici e Reiki in studio, partita IVA.** Il suo lavoro è il listino: sedute da 60-80 €. Le serve: richieste ordinate, calendario che blocca gli orari, recensioni. Pagherebbe: il Pro annuale per WhatsApp con Valentina e il racconto; Stripe lo collega se le toglie i messaggi.

**Marco, 38, ritiri di respiro e cammini, 2-3 l'anno da 20 persone a 450 €.** Fattura, conosce BookRetreats (15-20%). Gli serve: il marketplace e la selezione, la lista partecipanti, i promemoria. Con Aurya non paga commissioni: su 27.000 € di ritiri l'anno risparmia 4-5.000 € rispetto alle piattaforme straniere. Pagherebbe: il Club subito, il Pro se il racconto e Valentina valgono.

**Valentina, e chi le somiglia: la professionista con la voce.** Compone meditazioni, vuole pubblicarle e condividerle coi clienti: Crea Studio è il suo motivo per il Pro.

Il conto che fanno tutti, senza dirlo: **«mi porta persone?»**. Finché la risposta è «non ancora», nessuno paga la visibilità, e ha ragione. Per questo ogni euro chiesto è legato a un numero visibile.

---

## 4. Il modello definitivo

### 4.1 I piani

| | Gratis | Spinta | Club Aurya | Pro |
|---|---|---|---|---|
| **Prezzo** | 0, per sempre | 19 € per un ritiro | 49 €/anno | 119 €/anno (o 12/mese) |
| **Per chi** | tutti | chi fa un ritiro l'anno | chi vuole la fila tutto l'anno | chi vuole la voce e il tempo di Valentina |
| Profilo pubblico nella directory, listino, richieste, calendario, clienti, recensioni, pagina link | ✓ | ✓ | ✓ | ✓ |
| Eventi e ritiri sul tuo profilo e sul tuo link, con caparra via bonifico o con Stripe | ✓ | ✓ | ✓ | ✓ |
| Commissioni Aurya | **nessuna** | nessuna | nessuna | nessuna |
| Il ritiro in Ritiri ed esperienze (il marketplace, in ordine di data, coi filtri) | ✓ | ✓ | ✓ | ✓ |
| In prima fila: nella selezione in cima al marketplace e nelle selezioni di stagione | – | quel ritiro | tutti | tutti |
| Il ritiro nella Lettera del Cerchio agli iscritti della tua zona e dei tuoi temi | – | quel ritiro | tutti | tutti |
| Un post su Instagram per ritiro (max uno al mese) | – | quel ritiro | ✓ | ✓ |
| Badge e precedenza nella directory della tua zona | – | – | ✓ | ✓ |
| Crea Studio: componi e pubblichi meditazioni con la tua voce | – | – | – | ✓ |
| Il racconto (intervista): per chi pubblica il profilo, gratis per sempre ai primi cinquanta | ✓ in coda | ✓ | ✓ | ✓ con precedenza, più una pagina nel Magazine |
| Assistenza | email, automatica | email | risposta entro 2 giorni | WhatsApp con Valentina |
| Team (collaboratori), quando servirà | – | – | – | ✓ |

**Perché questi prezzi.** Annuali, non mensili: il prezzo di un weekend, pagato una volta; un canone mensile da 4-9 € si disdice al primo mese vuoto, un annuale si giudica sull'anno. Il Club a 49 sta come un Linktree Starter (54 €/anno), sotto il registro ROOI (80 €), nella fascia «sotto 100 €/anno» dei gestionali per freelance, e a un decimo di quello che Treatwell prende su un solo cliente nuovo da 200 €. Il Pro a 119 è quasi regalato rispetto a Momoyoga (348), Fresha (239), Treatwell Connect (circa 230): nel 2028 può salire a 149. La Spinta a 19 è la porta piccola: chi la compra due volte ha quasi pagato un Club, e il passaggio glielo propone il prodotto. Se preferisci 99 per il Pro, cambia il seed, non il modello; sotto 99 no.

### 4.2 La caparra: bonifico prima, Stripe se vuoi

Il bonifico è la strada principale, non il ripiego. Nelle impostazioni l'operatore scrive una volta IBAN e intestatario; nel wizard «caparra con bonifico» è il modo predefinito (cifra o percentuale, entro quanti giorni); chi prenota riceve subito l'email con IBAN, importo, causale e scadenza e il posto resta «in attesa della caparra»; arrivato il bonifico l'operatore conferma con un clic e partono conferma e promemoria del saldo; scaduta la caparra senza conferma, il posto si libera dopo un avviso. È l'ordine manuale con la nota che esiste già, reso un percorso.

Stripe resta per chi lo vuole (Marco, Silvia), acceso dalle impostazioni con tre verità scritte: non sei obbligato; si apre anche senza partita IVA come persona fisica (codice fiscale, documento, IBAN) e Stripe paga te; la parte fiscale non dipende da Stripe (fino a 5.000 € lordi l'anno prestazione occasionale, oltre serve la partita IVA: parla col commercialista). Nel wizard Stripe non compare a chi non l'ha collegato. Aurya esce dal flusso del denaro: nessuna responsabilità su contestazioni e rimborsi, coerente con «zero commissioni».

### 4.3 Fondatori e Partner

**Fondatori** (i primi venti che pubblicano il profilo entro il 31/10/2026): Club regalato per tutto il 2027, badge permanente, prezzo Pro bloccato per sempre a quello del 2027, precedenza nella selezione. È il patto già scritto nella landing: il Club è la cosa concreta che contiene. **Partner** (Masseria e strutture): condizioni proprie, invariato.

---

## 5. Dove sta il trigger: i cinque inneschi

Il passaggio a pagamento non si spinge con i limiti ma con la domanda misurata, mostrata nel momento giusto. Tutti e cinque dipendono da una cosa sola: che nel Cerchio ci siano persone con città e interessi.

1. **All'ultimo passo del wizard del ritiro.** «Il tuo ritiro è online sul tuo profilo. Nel Cerchio ci sono **{N} persone a meno di 80 km da {luogo} che hanno chiesto {yoga}**. Vuoi che glielo mandiamo? Spinta 19 €, o Club 49 € l'anno.» Il numero è vero (preferenze del Cerchio: città, raggio, interessi, già raccolte). Se N è piccolo la frase non compare: non si vende una fila vuota.
2. **Alla prima richiesta arrivata da Aurya.** Ogni richiesta dice da dove viene («dalla directory Aurya»); la seconda volta propone il Club.
3. **Due volte l'anno, la selezione con la scadenza.** «La selezione dei ritiri di primavera 2027 parte il 15 gennaio: i ritiri del Club e con la Spinta ci entrano. Chiusura il 10.» Una data vera muove più di uno sconto.
4. **Il cruscotto della visibilità nel gestionale.** Visite al profilo, da dove arrivano, e «{N} iscritti al Cerchio nella tua zona hanno chiesto i tuoi temi»: un numero che cresce ogni settimana ed è un promemoria che non scriviamo noi.
5. **La voce.** Alla prima meditazione registrata dal telefono, o quando chiede a Valentina di scrivere il racconto: il Pro.

---

## 6. Quando: date, cancelli, promesse vere

| Periodo | Cosa vale | Cosa diciamo in pagina |
|---|---|---|
| **Oggi → 31/12/2026** | tutto gratis (promessa fatta, si mantiene); zero commissioni; bonifico e Stripe facoltativo; fondatori fino al 31/10 | «Gratis fino al 31 dicembre 2026. Poi il Gratis resta gratis per sempre, senza commissioni. Chi vuole la prima fila ha la Spinta a 19 € o il Club a 49 € l'anno.» |
| **1/1/2027** | i piani sono pubblici; Spinta e Pro si comprano; il Club anche, ma… | l'operatore sa da oggi cosa succede a gennaio |
| **…il Club si vende quando la fila c'è** | tre numeri pubblici su /costi: 300 iscritti confermati al Cerchio, 10 ritiri in programma, 1.000 visite al mese | «Il Club si accende quando la fila c'è: ecco i tre numeri, aggiornati ogni settimana.» |
| **Se al 1/1/2027 i numeri non ci sono** | il Club resta gratis per tutti fino al primo mese in cui sono veri; Spinta e Pro si vendono comunque (la Spinta si propone solo se N è vero) | si dice a dicembre, con la stessa frase |
| **Fondatori** | Club gratis 2027, Pro bloccato | già in landing |

I cancelli pubblici sono l'unico modo di vendere visibilità senza mentire, e sono marketing: «230 iscritti su 300» dice che la fila si sta formando e che conviene esserci prima.

---

## 7. Il nostro tempo: cosa promettiamo e cosa no

| Livello | Chi risponde | Come | Cosa NON facciamo |
|---|---|---|---|
| Gratis | le email automatiche (g0, g7, g14, g30) e una casella | email, entro una settimana | telefonate, profili scritti a mano, post |
| Spinta / Club | Valentina | email entro due giorni; un post per ritiro (max 1/mese) | racconto scritto da noi (su invito) |
| Pro | Valentina | WhatsApp; il racconto con precedenza | niente di illimitato: «prioritario», non «sempre» |

Regola: **il gratuito è self-serve.** L'intervista resta l'eccezione perché è il motore della rete: si fa a chi pubblica il profilo, con la coda decisa da noi (prima chi paga, poi chi è attivo).

---

## 8. I conti, senza illusioni

### 8.1 Lato operatori, 2027 (60 operatori a fine anno)

| Voce | Ipotesi | Quanto |
|---|---|---|
| Club | 25 a 49 € (i 20 fondatori sono gratis) | 1.225 € |
| Pro | 8 a 119 € | 952 € |
| Spinta | 40 ritiri spinti a 19 € | 760 € |
| Commissioni | nessuna | 0 € |
| **Totale lato A** | | **≈ 2.900 €** |

Con la metà degli abbonati: 1.500 €. Con Marco e altri due organizzatori seri: +400. **Non ci si vive**, e lo sapevamo.

### 8.2 Tutto il business, per anno (dal piano strategico di agosto, aggiornato)

| | Anno 1 (2026-27) | Anno 2 | Anno 3 |
|---|---|---|---|
| A. Operatori (Spinta, Club, Pro) | ≈ 2.900 | ≈ 12.000 (100 Club, 30 Pro, spinte) | ≈ 30.000 |
| B. Chi cerca: abbonamento meditazioni | 0-1.500 | ≈ 15.600 (400 a 39) | ≈ 46.800 (1.200) |
| B. Chi cerca: esperienze online e dal vivo | ≈ 2.000 | ≈ 19.200 | ≈ 60.000 |
| C. Corso per operatori | 0 | ≈ 29.800 (200 a 149) | ≈ 60.000 |
| Racconti e promozioni, sponsor di settore | 0 | ≈ 7.000 | ≈ 30.000 |
| **Totale** | **≈ 5-6.000** | **≈ 84.000** | **≈ 227.000** |

Due cose da leggere in questa tabella. La prima: **le commissioni non ci sono più, e il totale non cambia**: valevano 4.000 € nell'anno 2, sostituiti dal Club che cresce. La seconda: il lato operatori è la base stabile e la selezione, non il motore; il motore sono le persone che cercano (abbonamento e esperienze) e la formazione, ed entrambi dipendono dalla stessa cosa del Club: la fila. Tutto il business poggia su un numero solo, il Cerchio pieno di persone con città e interessi.

### 8.3 Cosa compra Aurya con questi soldi

- **Selezione**: chi paga 49 € pubblica, risponde, porta persone; la rete si pulisce da sola.
- **Un numero stabile**: 30 abbonati sono 2.000 € certi, i primi ricavi ricorrenti da mostrare a chiunque.
- **La macchina**: Lettera per zona, selezione, spinte, badge: costruita per 25 abbonati, funziona per 250.

---

## 9. In cassaforte: il modello «nuovo cliente» (2028, sui numeri)

Il mercato dimostra che gli operatori pagano volentieri **il primo cliente portato**, una volta sola, qualunque sia il modo di incassare (Fresha e Treatwell addebitano sulla carta dell'operatore al primo appuntamento). Per noi sarebbe: nessuna commissione sui ritiri, ma «il primo cliente dalla fila costa X», in alternativa al Club. Non ora, e forse mai: si decide nel 2028 su prenotazioni misurate, e se cambiasse varrebbe per i nuovi iscritti con la data scritta. Fino ad allora la frase è **«Aurya non prende commissioni. Mai.»** Mai invece il pay-to-rank, e mai Aurya come incassatore per conto terzi.

---

## 10. Cosa cambia nel prodotto

| Passo | Cosa | Effort | Quando |
|---|---|---|---|
| M3 | Le parole: landing e /costi dicono cosa succede a gennaio (i quattro piani, zero commissioni, i tre cancelli), FAQ allineata | mezza giornata | subito, nell'onda 1 del rebranding |
| M4 | Il bonifico come strada principale: IBAN nelle impostazioni, caparra nel wizard di default, email con le istruzioni, conferma con un clic, scadenza automatica; Stripe opzionale con le tre verità | 2 giornate | onda 2, primo passo |
| M1 | Piano Club (49/anno) e Pro annuale a 119 (mensile 12) nel catalogo e in Stripe; migrazione flag-gated come per il 19 | 1 giornata | onda 2 |
| M2 | Il flag «prima fila» su ritiri ed eventi (Club, Pro, Founding, Partner, Spinta) filtrato in Ritiri ed esperienze, selezione, Lettera | 1 giornata | onda 2 |
| M10 | La Spinta: pagamento una tantum sul nostro Stripe, flag sul singolo ritiro, proposta nel wizard e nel cruscotto | mezza giornata | onda 2 |
| M9 | Il contatore «{N} persone nel Cerchio vicino a te che hanno chiesto i tuoi temi» nel wizard e nel gestionale | mezza giornata | onda 2 |
| M6 | La Lettera per zona e temi coi ritiri in prima fila: la query esiste, manca l'invio (template + job) | 1 giornata | onda 2 |
| M5 | Fondatori: Club regalato per il 2027, badge sul profilo | mezza giornata | onda 2 (con la striscia) |
| M7 | Il cruscotto dei tre numeri in system admin e su /costi | mezza giornata | onda 3 |

Tutto sopra il motore di billing che c'è già (piani per modulo, abbonamenti Stripe, flag per organizzazione). Nessun rifacimento.

---

## 11. Le decisioni

| # | Decisione | Stato |
|---|---|---|
| 1 | Zero commissioni Aurya, sempre; Stripe è uno strumento, mai un obbligo | **deciso dal founder (10/9)** |
| 2 | Il bonifico con caparra è la strada principale; Aurya fuori dal flusso del denaro | **deciso dal founder (10/9)** |
| 3 | Quattro porte: Gratis / Spinta 19 / Club 49 / Pro 119 (mensile 12), annuali | da confermare (99 per il Pro accettabile, non meno) |
| 4 | Il Club si vende solo coi tre cancelli pubblici veri; la Spinta si propone solo se N è vero | da confermare |
| 5 | Fondatori: Club gratis per il 2027 e Pro bloccato | da confermare |
| 6 | Il nostro tempo: Gratis self-serve, Club due giorni + un post, Pro WhatsApp | da confermare |
| 7 | Mai pay-to-rank, mai incassare per conto terzi; il modello «nuovo cliente» resta in cassaforte per il 2028 | da confermare |
| 8 | Scrivere da subito, in landing e in /costi, cosa succede a gennaio | da confermare |

---

## Appendice — Le strade scartate, e perché

| Strada | Perché no |
|---|---|
| Solo commissione 5% sugli incassi online (oggi) | si aggira (caparra piccola online, resto a parte); tassa una minoranza degli incassi; crea il furbo; obbliga a Stripe chi non è pronto |
| 5% solo sulle prenotazioni «portate da Aurya» (provenienza sull'ordine) | riduce il problema ma non lo elimina; complica la frase; Aurya resta nel flusso del denaro |
| Vincolo «senza Stripe niente marketplace» | non esisteva nel codice; avrebbe escluso chi inizia; proteggeva un incasso che non c'è |
| Aurya incassa per tutti (merchant of record) | intermediario finanziario: fatture, rimborsi, contestazioni, licenze; due persone non reggono |
| Solo abbonamento obbligatorio | un canone d'ingresso uccide il funnel con 12 operatori e 0 traffico |
| Pay-per-lead | litigi su «era un lead vero?», complesso, conta i contatti e non i clienti |
| Pay-to-rank (commissione per la classifica) | contro il criterio invisibile; le recensioni furiose delle piattaforme di ritiri |
