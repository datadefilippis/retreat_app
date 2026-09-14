# Aurya, 14 settembre 2026 — Più sedi per operatore: analisi e piano

Richiesta del founder: «più di un operatore vorrebbe inserire nel profilo
pubblico più località in cui opera. Oggi una sola. Vorrei una o più
località (massimo 3), tutte visibili nel profilo, e chi opera in Puglia e
in Lombardia deve comparire in entrambe secondo i filtri della directory.
Senza sfasciare nulla, e con la creazione del profilo che resta semplice».

Ogni affermazione viene da una verifica: il codice letto riga per riga,
i dati di produzione letti in sola lettura oggi, e una prova tecnica
fatta su un database locale per il punto più delicato (la ricerca per
raggio con più punti). Prima com'è oggi, poi la proposta, poi il piano.

---

## 1. Com'è oggi

### 1.1 Dove vive la località

Tutto sta dentro `organizations.public_profile`, in quattro campi
piatti: `city` (testo libero), `region` (testo libero), `latitude`,
`longitude`. Un quinto campo, `geo`, è un punto GeoJSON derivato dalle
coordinate al salvataggio e serve solo all'indice geografico
(`an3_org_geo`, 2dsphere). Non esistono provincia, indirizzo, paese,
né un elenco chiuso di regioni per il profilo (le tre liste di regioni
del repo servono a ritiri, strutture e Cerchio, non al profilo).

Chi scrive la località:

| Dove | Come | Coordinate |
|---|---|---|
| Profilo pubblico (`/public-profile`) | autocomplete Nominatim «Località (cerca e seleziona)»; della risposta si tiene **solo il primo pezzo prima della virgola** come `city`; la regione contenuta nella stessa risposta viene buttata | sì, se si sceglie dalla lista |
| Benvenuto (`/benvenuto`) | campo di testo libero «La tua città» | no: il server prova a geocodificare dopo, in silenzio |
| Regione | campo di testo libero nella sezione avanzata, quasi nessuno lo compila | — |

### 1.2 Chi la legge

Quindici lettori, tutti sui quattro campi piatti:

- **Directory `/operatori`**: il filtro non è per regione, è **un punto più
  un raggio** (25/50/100/250 km) scelto con lo stesso autocomplete o con
  «Vicino a me», più un filtro testuale `?luogo` che cerca la parola in
  città, regione e nelle regioni dei ritiri futuri. La distanza arriva
  dall'indice (`$geoNear` su `public_profile.geo`). Chi non ha coordinate
  non compare mai in una ricerca per raggio. La mappa mette **un
  segnaposto per operatore**.
- **Pagine `/destinazioni/{luogo}`**: nascono dai ritiri, non dai profili;
  gli operatori vi compaiono per confronto esatto di stringa tra il nome
  del luogo e l'insieme `regions` (regione + città del profilo + regioni
  dei ritiri futuri).
- **Profilo `/o/{slug}`**: una riga «città, regione» nell'intestazione con
  link a `/destinazioni/…`; titolo SEO «Nome · discipline a {città}»;
  dati per Google `LocalBusiness` con un solo indirizzo e un solo punto.
- **Shell per i crawler, home, elenco operatori, `llms.txt`**: la stessa
  stringa «città, regione».
- **Ritiri, Lettera del Cerchio, pagina link, email**: **non** usano la
  località del profilo. I ritiri hanno la propria sede; il Cerchio
  ragiona sulla città dell'iscritto. Restano fuori da questo lavoro.

### 1.3 I dati veri di produzione (oggi, sola lettura)

Tredici organizzazioni, dieci con una località.

| Operatore | `city` | `region` | Coordinate |
|---|---|---|---|
| Brillare · Valentina | Milano | Lombardia | ok |
| Ilaria | **Umbria** | Umbria | centro regione |
| Cristina Cordisco | Acri | — | ok |
| Rigveda · Claudia Cannatà | Roma Capitale | — | ok |
| Claudia Rossato | Sappada / Plodn / Sapade | — | ok |
| Metodo Oltre | Roma | — | ok |
| Selva Viva · Silvia | Genova | — | ok |
| Elena Daldoss | Collebeato (BS) | — | ok |
| Gabriella Balascio | **Bellinzona** | — | **41.92, 12.51 = Roma** |
| Claudia Pietrantuoni | **Puglia** | — | centro regione |

Tre cose da sapere prima di progettare:

1. **La regione è vuota in 11 profili su 13**, anche se Nominatim la
   restituisce a ogni selezione («Ostuni, Brindisi, Puglia, 72017,
   Italia»): la buttiamo noi. Per questo oggi «Puglia» come filtro delle
   destinazioni trova solo chi ha scritto «Puglia» a mano.
2. Due operatrici hanno scelto **la regione come località** (Umbria,
   Puglia): il punto sulla mappa è il centro geografico della regione.
   È un uso legittimo («lavoro in tutta la Puglia») che il modello di
   oggi non sa distinguere da una città.
3. Un profilo ha **coordinate sbagliate** (Bellinzona con il punto a
   Roma): il campo testo e le coordinate possono divergere, perché il
   testo si può modificare senza riselezionare dalla lista.

### 1.4 La prova tecnica che decide tutto

La domanda: un operatore con tre sedi può restare **un solo documento**
e comparire in una ricerca per raggio intorno a Bari e in una intorno a
Milano, con la distanza giusta in ciascuna? Provato su un database
locale con l'indice 2dsphere e la stessa query della directory:

| Forma di `geo` | Indice | Ricerca a 150 km da Lecce | da Como | da Roma |
|---|---|---|---|---|
| lista di punti `[Point, Point]` | **rifiutata** da MongoDB | — | — | — |
| `MultiPoint` [Ostuni, Milano] | ok | trovato, **66 km** (Ostuni) | trovato, **39 km** (Milano) | non trovato |

Un `MultiPoint` funziona con la query di oggi senza cambiarla: un solo
documento, nessun doppione in lista, la distanza è quella dalla sede più
vicina. È il fondamento del piano.

---

## 2. La proposta: le «sedi»

### 2.1 Il modello

Un solo campo nuovo, `public_profile.sedi`, una lista da **1 a 3** voci:

```
sedi: [
  { citta: "Ostuni", provincia: "Brindisi", regione: "Puglia",
    paese: "Italia", lat: 40.7297, lng: 17.5776, etichetta: "Ostuni, Brindisi, Puglia" },
  { citta: "Milano", provincia: "Milano", regione: "Lombardia", ... }
]
```

- La prima è la **sede principale**. I quattro campi di oggi (`city`,
  `region`, `latitude`, `longitude`) diventano **specchi della prima
  sede**, ricalcolati a ogni salvataggio, mai modificabili a parte.
  Così i quindici lettori continuano a funzionare **senza toccarli**,
  e si aggiornano uno per uno solo dove si vuole mostrare di più.
- `geo` diventa un `MultiPoint` con tutte le sedi: la directory per
  raggio funziona subito, per tutte le sedi, senza cambiare la query.
- **La regione non si chiede più**: si prende da Nominatim
  (`addressdetails=1`, campo `state`) al momento della selezione e si
  controlla contro l'elenco chiuso delle 20 regioni già usato dai
  ritiri. Fuori Italia la regione resta vuota e si tiene il paese.
- Chi seleziona **una regione intera** dalla lista (il caso Umbria e
  Puglia di oggi) ha una sede con `citta` vuota e `regione` piena: un
  caso previsto, non un errore.
- Testo e coordinate non possono più divergere: una sede esiste solo
  se scelta dalla lista. Il testo digitato senza scegliere non salva
  nulla e lo dice («scegli dalla lista per comparire sulla mappa»).

### 2.2 Il gestionale, senza appesantire

**Profilo pubblico**, blocco «Dove lavori»:

- la sede principale con lo stesso autocomplete di oggi, obbligatoria
  come oggi (la barra di completezza la conta già);
- sotto, le sedi scelte come righe «Ostuni, Brindisi · Puglia ✕»;
- un solo pulsante «+ Aggiungi una sede» che sparisce alla terza;
- una riga di aiuto: «Comparirai nelle ricerche vicino a ognuna».

Niente altro: non si chiedono indirizzi, orari, «come lavori qui».

**Benvenuto** (`/benvenuto`): il campo «La tua città» diventa lo stesso
autocomplete, una sede sola. Le altre si aggiungono dopo dal profilo;
la striscia dell'onboarding già oggi ricorda chi non ha la località.
Chi si iscrive non vede una domanda in più.

### 2.3 Cosa cambia per chi guarda

| Superficie | Oggi | Dopo |
|---|---|---|
| Directory, scheda | «Milano, Lombardia» + distanza | «Ostuni · Milano» (le sedi, max 3) + «a 39 km (Milano)» quando si cerca per raggio |
| Directory, ricerca per raggio | trova solo la sede unica | trova l'operatore da **ognuna** delle sedi, una volta sola, con la distanza dalla più vicina |
| Directory, filtro testuale `?luogo` | città/regione unica | qualunque sede (città, provincia, regione) |
| Directory, mappa | un segnaposto | un segnaposto **per sede** (max 3), stesso popup |
| `/destinazioni/puglia` e `/destinazioni/lombardia` | l'operatore in una sola | in **entrambe**, perché `regions` contiene le regioni di tutte le sedi |
| Profilo, intestazione | «Milano, Lombardia» | «Ostuni (Puglia) · Milano (Lombardia)», ognuna col suo link alla destinazione |
| Profilo, titolo SEO | «… a Milano» | invariato: la sede principale (un titolo, una città) |
| Dati per Google | un indirizzo + un punto | indirizzo e punto della sede principale + `areaServed` con le altre (schema.org lo prevede) |
| Shell crawler, `llms.txt`, home, elenco | «città, regione» | «Ostuni, Puglia · Milano, Lombardia» |

### 2.4 Cosa NON si tocca

Ritiri (hanno la loro sede), Lettera del Cerchio e sequenze, pagina
link, email, Sound, checkout. Nessun cambio di rotte, nessuna pagina
nuova. La forma della risposta della directory resta la stessa con un
campo `sedi` in più.

### 2.5 La bonifica dei profili esistenti

Migrazione una tantum con flag, come per i link social:

- ogni profilo con `city` diventa `sedi: [{...}]` con le coordinate di
  oggi; la **regione si ricava dalle coordinate** (reverse geocoding
  Nominatim, uno al secondo, dieci profili: dieci secondi), così anche
  gli undici profili senza regione la ottengono;
- `geo` passa a `MultiPoint`;
- il risultato si legge in una tabella **prima** del deploy sulla copia
  di produzione, come fatto oggi per i social; i due casi anomali
  (Bellinzona/Roma; regioni scelte come città) si vedono lì e si
  decidono a occhio.

---

## 3. Rischi e come si tengono

| Rischio | Come si tiene |
|---|---|
| Rompere i quindici lettori | non si toccano: leggono gli specchi della sede principale, che restano identici a oggi |
| Doppioni in directory | impossibile per costruzione: un documento per operatore, `MultiPoint` provato |
| Indice geografico da ricostruire | no: lo stesso indice 2dsphere accetta `Point` (vecchi) e `MultiPoint` (nuovi) insieme |
| Nominatim lento o giù | come oggi: cache in `geocode_cache`, tutto best-effort, la sede si salva comunque con le coordinate della selezione |
| Guardie esistenti (test AN3 su marcatori del sorgente) | evolvono con docstring datata, come sempre; i marcatori `prof_regions`, `payload.latitude`, `/public/geo/search` restano |
| Utente che non sceglie dalla lista | il testo non salva più una sede senza coordinate: lo dice in chiaro |

---

## 4. Il piano (ciclo SD, «sedi»)

| Passo | Cosa | Dove | Stima |
|---|---|---|---|
| **SD1** modello e salvataggio | `sedi` (1-3) con validazione, specchi della sede principale, `geo` MultiPoint, regione da `addressdetails` nell'autocomplete, elenco chiuso regioni; guardie | `routers/organizations.py`, `services/geocoding.py`, `database.py`, test nuovo `test_sedi_sd.py` | ½ giornata |
| **SD2** gestionale | blocco «Dove lavori» nel profilo (max 3, righe con ✕), autocomplete in `/benvenuto` | `PublicProfilePage.js`, `WelcomeRetePage.js`, locali it | ½ giornata |
| **SD3** directory e destinazioni | `sedi` e regioni di tutte le sedi nella risposta, scheda con sedi + distanza dalla più vicina, filtro `?luogo` su ogni sede, un segnaposto per sede | `routers/public.py`, `OperatorsIndexPage.js`, `OperatorsMapView.jsx`, `DestinationsPage.js` | ½ giornata |
| **SD4** profilo e SEO | intestazione con tutte le sedi, `areaServed`, shell crawler, `llms.txt`, home ed elenco | `OperatorIdentityHeader.jsx`, `OperatorProfilePage.js`, `seo_shell.py`, `identita.py` | ½ giornata |
| **SD5** bonifica e prova | migrazione `sedi_v1` con reverse geocoding, tabella sulla copia di prod, suite completa, giro in browser | `services/migrazioni_profilo.py`, `server.py` | ½ giornata |

Circa due giornate di lavoro in locale, un solo deploy insieme al ciclo
già pronto (abbonamenti, landing, `/costi`, link social). L'ordine è
quello: ogni passo lascia il sito funzionante, e SD1 da solo già fa
comparire l'operatore in più zone anche prima che l'interfaccia lo
mostri.

## 5. Le decisioni che spettano al founder

1. **Massimo tre sedi**: confermato dalla richiesta; il tetto vive in un
   solo posto e si alza senza rifare nulla.
2. **Sedi all'estero** (oggi c'è Bellinzona): proposta **sì**, con
   regione vuota e paese mostrato; la ricerca per raggio funziona
   comunque, la pagina della regione no. Alternativa: solo Italia.
3. **«Online / a distanza» come sede?** No: non è un luogo e
   confonderebbe la mappa. Se serve, è un interruttore a parte in un
   ciclo suo («ricevo anche online»), da mostrare nella scheda.
4. **Regione intera come sede** (Umbria, Puglia): proposta **sì**, come
   oggi, con la scritta «tutta la Puglia» al posto della città.

---

## Appendice — «Stripe obbligatorio per la directory»: cosa è rimasto indietro

Segnalazione del founder (14/9): creando un ritiro senza Stripe la
dashboard dice «I tuoi ritiri non compaiono nel calendario pubblico …
Attiva i pagamenti», e sul ritiro compare «Non in directory». «Mi sembra
che nei vecchi commit avessimo tolto l'obbligo di Stripe: o sbaglio?»

**Non sbaglia.** L'obbligo è stato tolto il 10/9 in due commit (P3
`8b9f0129` «marketplace aperto a tutti i ritiri» e, la notte,
`b6986b86` «UNA regola per i ritiri listabili»). Ma la regola è stata
riscritta **in tre posti su sei**: gli altri tre sono rimasti a luglio.

### La regola vera (quella del sito pubblico)

`_ritiro_listabile` in `routers/public.py`: un ritiro futuro pubblicato,
di un operatore con pagina pubblica, entra nella lista se **è «su
richiesta»** oppure se **è «prenotazione online» e Stripe è pronto**.
Un ritiro «prenotazione online» senza Stripe **non entra**, perché non
si potrebbe prenotare in nessun modo. In produzione oggi i due ritiri
veri (Elena, Silvia) sono «su richiesta», senza Stripe, e **sono in
lista**: la regola pubblica funziona.

### Le sei superfici, una per una

| Superficie | File | Stato | Cosa dice oggi |
|---|---|---|---|
| Lista pubblica, filtro categorie, destinazioni, sitemap | `routers/public.py`, `services/seo_listing.py` | **aggiornata** (10/9) | su richiesta entra; online entra solo con Stripe |
| Griglia ritiri del gestionale, bollino «Non in directory» | `routers/event_occurrences.py` (`directory_reasons`) | **aggiornata** (P3) | `stripe_not_ready` **solo** se il ritiro è «online»; il tooltip spiega «collega i pagamenti o scegli su richiesta» |
| Avviso nel wizard del ritiro | `components/DirectoryListingHint.jsx` | aggiornata **ma contraddice la regola** | per «online» senza Stripe promette «Il ritiro compare comunque in Ritiri ed esperienze»: **falso**, la lista pubblica lo esclude |
| **Riquadro in home del gestionale** | `dashboard/OperatorHome.js` riga 184 | **vecchia (luglio, GT1b)** | `ritiro pubblicato && Stripe non collegato` → avviso rosso, **anche se il ritiro è su richiesta**. In produzione lo vedono oggi **Elena e Silvia**, i cui ritiri sono in lista |
| **Admin › Directory e Segnali** | `services/platform_insights.py` righe 196-201 | **vecchia (SA3, agosto)** | `stripe_not_ready` per chiunque non abbia Stripe, e «in directory» conta **solo i ritiri online**: l'admin dice **0 operatori in directory** mentre il sito ne lista 2 |
| Testo della checklist «Inizia» | `onboarding/IniziaPage.js` + `dashboard.json` `stripe_why` | **vecchia** | «Serve anche per comparire nel calendario pubblico» |

Il bollino «Non in directory» che il founder ha visto sul ritiro nuovo è
quindi **giusto** se il ritiro era «prenotazione online» (senza Stripe
davvero non compare; il tooltip lo dice) oppure se all'operatore manca
la pagina pubblica; è il riquadro in home a essere **sbagliato**, e la
promessa del wizard a essere **in contrasto** con la lista.

### La correzione (piccola, in coda)

1. **Una funzione, tre lettori.** Spostare `_ritiro_listabile` in un
   servizio (`services/ritiri_visibilita.py`) e farla usare da lista
   pubblica, griglia del gestionale e admin: oggi sono tre copie a mano
   che divergono, ed è così che è nato il problema. Guardia che lo
   impone.
2. **Home del gestionale**: l'avviso compare solo se esiste un ritiro
   futuro «online» senza Stripe, con il testo giusto: «Un tuo ritiro
   con prenotazione online non compare finché Stripe non è attivo:
   collega i pagamenti o mettilo su richiesta». Il dato arriva dal
   backend (`onboarding/status` conta già i ritiri pubblicati: si
   aggiunge il conteggio di quelli «online senza Stripe»).
3. **Admin › Directory**: «in directory» e le ragioni seguono la
   funzione unica; i ritiri su richiesta contano come listati; il
   segnale «pronti a entrare in directory» resta ma con la regola vera.
4. **Wizard**: la riga per «online senza Stripe» dice la verità: «finché
   Stripe non è attivo il ritiro **non compare** e il pagamento non
   parte: scegli su richiesta o collega Stripe».
5. **Copy** `stripe_why`: via «Serve anche per comparire nel calendario
   pubblico».

Mezza giornata, guardie evolute (`test_modules_md`,
`test_platform_admin_sa`), nessun cambio alla regola pubblica: chi è in
lista oggi resta in lista. Alternativa possibile ma **sconsigliata**:
listare anche i ritiri «online» senza Stripe con un «chiedi un posto»
di riserva: mostrerebbe una prenotazione che poi non parte.
