# Prodotti su Aurya — analisi profonda e piano (v3, 6 ottobre 2026)

*Riprende `PIANO_ACCADEMIA_2026-10-04.md` e lo restringe a quello che il founder chiede ora: **vendita di prodotti**, un'entità sola con tre tipologie (fisico, digitale, formazione in presenza), commissioni specifiche sui prodotti abbassate dall'abbonamento, modulo negli Strumenti con lista e modifica, vendite nella dashboard e negli insight, Stripe obbligatorio. Tutto riusando quello che c'è. I videocorsi in piattaforma (lotto B del piano precedente) restano fuori da questo giro.*

## 0. Il giudizio in una pagina

**Quanto c'è da fare: circa 10 giorni**, di cui 1 di Stripe (che serve comunque), 3 di fondamenta, 5 per i due tipi di prodotto, 1 per dashboard e insight. Il 70% del codice esiste già e va saldato all'Aurya di oggi, non inventato.

**La decisione di architettura che semplifica tutto: la formazione in presenza non è un prodotto, è un'esperienza con una data.** Un corso con data, luogo, posti e caparra è esattamente quello che il wizard degli eventi fa già (date, posti, fasce di prezzo, caparra con bonifico o Stripe, biglietti, check-in). In prod due dei dieci eventi sono già corsi («Corso I livello Reiki», «Corso Theta Healing»): gli operatori l'hanno capito da soli. Quello che manca è **un campo**: oggi l'unico asse è la disciplina (yoga, meditazione, reiki…), e la pagina chiama tutto «ritiro» per convenzione. Non esiste nulla che dica *che cosa* è: un ritiro di tre giorni, un evento di una sera, una formazione. Quindi si aggiunge un secondo asse, **«formato»** (ritiro · evento · formazione), separato dalla disciplina, che resta com'è. Nel selettore di tipologia dei prodotti la terza carta c'è («Formazione in presenza»), ma apre il wizard degli eventi con formato «formazione» già scelto. Niente terzo modello, niente duplicazione di date, posti e caparre. La formazione senza data (lezioni, percorsi individuali, formazione su richiesta) è già il Listino.

**Quindi il modulo Prodotti vende due cose: fisici e digitali.** Entrambi esistono nel codice (modelli, magazzino, spedizione, file protetti con download a token, emissione alla conferma, landing `/ph/` e `/dg/`), congelati dal 28/7 dietro un interruttore che non va riacceso. Si riusano le fondamenta, si riscrivono le superfici in tre gesti, si saldano al profilo e all'account Aurya.

**Stripe prima di tutto.** In prod: 45 organizzazioni, 3 hanno provato a collegare Stripe, 0 ci sono riuscite, perché l'account Express nasce svizzero. Senza il lotto S nessuno vende nulla, né prodotti né ritiri online. È il primo lotto, un giorno.

**Le commissioni sono un numero per tipo di riga, non un'architettura.** Il motore applica già una percentuale per organizzazione sulla sessione Stripe, con registro e rimborsi. Si passa alla percentuale per tipo di riga (prodotti X%, ritiri e servizi 0 per sempre), con il piano che la abbassa. Cinque punti di codice, tutti elencati sotto, tutti con guardie.

## 1. Cosa c'è davvero (verificato nel codice il 6/10)

| Pezzo | Dove | Stato | Verdetto |
|---|---|---|---|
| Registro dei tipi (7 tipi, validatori, schema metadata) | `models/product_types.py`, `models/product_metadata.py` | solido | riusa |
| Modello Product (prezzo, pubblicazione, slug, immagine, stock, `transaction_mode`) | `models/product.py` | solido | riusa |
| Opzioni e varianti («radio_variant», obbligatorie, facoltative) | `models/product_extra.py` | solido | riusa |
| Fisici: magazzino atomico, spedizione con opzioni e indirizzo strutturato, stati di evasione | `services/stock_service.py`, `models/shipping_option.py`, `models/order.py` | solido | riusa |
| Digitali: file privato, download a token con contatore e scadenza, landing `/d/` | `services/digital_storage.py`, `models/issued_download.py`, `routers/public.py` | solido | riusa, ma il file deve stare su un volume (oggi `private_uploads` non lo è) |
| Checkout condiviso inline sul profilo (già usato per servizi e ritiri) | `features/storefront/components/checkout/*` | solido | riusa |
| Stripe Connect Express, sessione sul conto dell'operatore, fee di piattaforma, registro, rimborsi | `services/payment_checkout_service.py`, `payment_providers/stripe/provider.py`, `services/platform_fee_ledger.py` | solido | adatta (fee per riga) |
| Wizard fisico (5 passi) e digitale (6 passi), hub `/products` | `features/physicals`, `features/digitals`, `features/products` | funzionanti ma pesanti, testi da gestionale | rifai in tre gesti |
| Dashboard fisici/digitali legacy | `features/physicals/*Dashboard`, `features/digitals/*Dashboard` | ridondanti | non riportare: le vendite stanno in Ordini e Incassi |
| Aggregazioni per tipo (cashflow `by_type`, ordini `revenue_by_type`, insight piattaforma `by_type_12m`, `sales-stats` per prodotto) | `routers/cashflow.py`, `routers/orders.py`, `services/platform_insights.py`, `routers/products.py` | generiche | riusa: un tipo nuovo entra gratis |
| Strumenti | `pages/StrumentiPage.js` | una scheda sola, stato letto da `user.sound_crea` | adatta: leggere il registro dei moduli |
| Registro moduli a piano | `core/module_registry.py`, `services/module_access.py`, `services/plan_provisioning.py` | solido | riusa: modulo `prodotti` |
| Gate legale (patto DPA) | `services/dpa_guard.py` `SELLABLE_ITEM_TYPES` | copre solo servizi ed eventi | estendi a fisici e digitali |
| Condizioni di vendita per negozio | `models/store.py` `merchant_*`, template legali | esistono, mai compilate nel mondo snello | precompila e pubblica in un passo |
| Eventi: wizard 4 passi, occorrenze, fasce, caparra, biglietti, check-in | `features/events/EventWizard.js`, `routers/event_occurrences.py` | vivo | riusa per la formazione in presenza |

Cosa manca davvero: la voce «formazione» nella tassonomia degli eventi; lo schema metadata del tipo `course` (irrilevante ora); le costanti frontend dei tipi non allineate al backend (`constants/itemTypes.js` non conosce `digital`); i contatori di customer insight per i tipi nuovi; il volume per i file; il modulo nel registro; la fee per riga.

## 2. Le quattro regole del disegno

1. **Un'entità, tre carte.** Chi crea sceglie prima la tipologia: *Prodotto fisico* · *Prodotto digitale* · *Formazione in presenza*. Le prime due aprono il wizard dei prodotti con i campi coerenti al tipo; la terza apre il wizard degli eventi con categoria «Formazione». Il modello sotto resta `Product` con `item_type`, come oggi.
2. **Stripe è un requisito del modulo, non un prerequisito nascosto.** Il primo riquadro della scheda Prodotti è «Collega gli incassi». Si può scrivere una bozza, non si può **pubblicare** senza Stripe pronto (`charges_enabled`). I prodotti si vendono solo con pagamento immediato (`transaction_mode = direct`): niente «su richiesta» per un libro o un PDF.
3. **La commissione la decide la riga, non l'organizzazione.** Ritiri e servizi: 0 per sempre (promessa stampata). Prodotti: percentuale del piano. Il piano abbassa la percentuale, non la cambia di natura.
4. **Il profilo è il negozio, l'account Aurya è il cliente.** I prodotti sono una sezione del profilo `/o/{slug}` con acquisto inline; i file comprati si ritrovano in `/account` → «I miei file»; gli ordini fisici in «I miei ordini». Il cliente legacy per negozio non entra.

## 3. Il modello economico (decisione del founder)

| | Ritiri e servizi | Prodotti fisici | Prodotti digitali |
|---|---|---|---|
| Gratis | 0 | **15% + Stripe** | **15% + Stripe** |
| Pro (19 €/mese) | 0 | **0% + Stripe** | **0% + Stripe** |
| Founding / Partner | 0 | come Pro | come Pro |

Decisione del founder (6/10): 15% nel Gratis, zero nel Pro. I numeri sono una tabella nel piano, cambiarli domani è una riga.

Cosa cambia nei testi, **prima** di accendere la fee: `/costi`, la landing professionisti, i piani (`seed_commercial_plans`), i Termini: «Ritiri e servizi senza commissioni, sempre. Sui prodotti che vendi dal tuo profilo tratteniamo il 15% (zero col Pro), più i costi Stripe: coprono consegna, download protetti e l'account del cliente.»

**Prova da fare nel lotto S**: la piattaforma Stripe è svizzera, gli operatori italiani. Una sessione con `application_fee` su un account IT in modalità test dice se la commissione tra paesi passa. Se no, le vie sono una piattaforma Stripe italiana (societaria) o «prodotti solo nel Pro». Si verifica prima di scrivere i testi.

## 4. Esperienza operatore

**Strumenti → scheda «Prodotti»** con tre stati: *attiva* (inclusa nel piano), *in arrivo*, *spenta dalla regia*. Dentro:
1. **Collega gli incassi**: stato Stripe in italiano («non collegato · in corso · pronto»), bottone che apre l'onboarding Express col paese scelto (Italia preselezionata, lotto S). Finché non è pronto, il resto è visibile ma «Pubblica» è spento con la frase vera.
2. **Condizioni di vendita**: precompilate dal profilo (nome, email, P. IVA se c'è), recesso e digitali già nel template, un «Confermo».
3. **I tuoi prodotti**: lista con tipo, stato (bozza/online), prezzo, magazzino, venduti 30 giorni, azioni (modifica, duplica, metti in pausa). Vuota: le tre carte di tipologia.

**Nuovo prodotto → tre carte**:
- **Fisico**, tre gesti: *Cos'è* (titolo, foto, due righe, prezzo, quantità o illimitato) → *Come arriva* (ritiro di persona / spedizione con costo fisso / da concordare; peso facoltativo) → *Pubblica* (anteprima della scheda, Pubblica). Dietro «Altro»: varianti (taglia, colore: le opzioni `radio_variant` che esistono), categoria.
- **Digitale**, tre gesti: *Cos'è* (titolo, copertina facoltativa, due righe, prezzo) → *Il file* (PDF, ePub, audio, zip; upload con barra; limite per piano: 100 MB Gratis, 500 MB Pro) → *Pubblica*. Dietro «Altro»: anteprima gratuita (prime pagine), scaricamenti massimi, scadenza del link.
- **Formazione in presenza**: una riga che spiega («una data, dei posti, una caparra: è un evento») e il bottone «Crea la formazione» che apre il wizard eventi con categoria «Formazione». Nessun campo in più da inventare oggi: attestato, prerequisiti e materiali restano testo nel programma, come per i ritiri.

**Dopo**: Ordini mostra anche questi (coda di evasione per i fisici con gli stati esistenti: da spedire, spedito, consegnato, ritirato); Incassi mostra «per tipo» e «per prodotto» (già generico); la dashboard ha una riga «Prodotti venduti negli ultimi 30 giorni» solo se il modulo è attivo.

## 5. Esperienza cliente

1. Sul profilo, sezione **«Prodotti»** sotto il listino: card uguali a quelle dei servizi (foto, titolo, prezzo, «Compra»). Clic → landing `/ph/` o `/dg/` (già instradate, shell SEO, JSON-LD `Product`).
2. «Compra» → checkout inline con l'account Aurya (già richiesto per i contatti; per i prodotti è obbligatorio: il file deve finire da qualche parte). Carta su Stripe, sul conto dell'operatore, fee trattenuta.
3. Email con il tono nuovo (FL3): «Il tuo file è pronto» con un pulsante → `/account/file`; per i fisici «{operatore} ha ricevuto il tuo ordine» e poi gli stati di consegna.
4. `/account`: **I miei file** (nome, scaricamenti rimasti, bottone) e **I miei ordini** (già esiste). Cross-operatore, qualunque dispositivo, stesso login.

## 6. Dati e punti di innesto (precisi)

**Modello**: nessun campo nuovo su `products`. Sul piano: `transaction_fee_by_type: {physical: 15, digital: 15}` (Pro: 0). Sull'organizzazione resta `application_fee_percent` (0, ritiri) più la mappa propagata dal piano. `IssuedDownload` e gli ordini portano `platform_account_id` (indice).

**Fee per riga, i cinque tocchi**:
1. `models/commercial_plan.py` + `seed_commercial_plans.py`: la mappa per tipo, con lo scalare che resta per retrocompatibilità.
2. `services/plan_provisioning.py:180`: propaga la mappa sull'organizzazione.
3. `services/payment_checkout_service.py:231` e `:664`: fee = somma per riga (`items[].item_type` × totale riga, al netto dello sconto); si passa al provider l'**importo** (`application_fee_minor`, campo nuovo in `payment_providers/models.py`) e non più una percentuale.
4. `payment_providers/stripe/provider.py:192-207`: usa l'importo se presente.
5. `services/platform_fee_ledger.py`: scomposizione per tipo nei metadata della sessione, per rimborsi parziali; `services/payment_refund_service.py:201` storna in proporzione.
Attenzione documentata: il checkout a sola caparra (`payment_checkout_service.py:277-298`) riscrive le righe e perde il tipo: per i ritiri la fee è 0, quindi oggi non importa; la guardia lo pretende esplicitamente. Il vincolo `le=10` sul campo org va alzato.

**Modulo**: `backend/modules/prodotti/` (registro, chiave `prodotti`, tier per piano con `max_file_mb`, `products_max`), `MODULE_OWNERSHIP` per le rotte `/prodotti/*`, `feature_flags.prodotti_spento` come interruttore di emergenza. Scheda negli Strumenti letta da `/modules/available` + `canUse('prodotti')`, non da `user.sound_crea`.

**API** (sotto `require_module('prodotti')`): `GET/POST /prodotti`, `GET/PUT /prodotti/{id}`, `POST /prodotti/{id}/immagine`, `POST /prodotti/{id}/file` (riusa l'upload digitale), `POST /prodotti/{id}/pubblica` (gate: Stripe pronto + condizioni pubblicate + patto), `GET /prodotti/{id}/vendite` (riusa `sales-stats`). Pubblico: `/public/operator/{slug}` arricchito con `prodotti` pubblicati (stessa cache), landing per tipo già esistenti. Cliente: `GET /platform/me/file` (download con `platform_account_id`).

**Formato delle esperienze (campo nuovo, additivo)**: `EventTicketMetadata.formato` in `models/product_metadata.py` (oggi vuoto per scelta): `ritiro | evento | formazione`, facoltativo, `extra="ignore"` come tutto lo schema: i 10 eventi in prod non cambiano (formato assente = si mostrano come oggi). Il wizard eventi, nel primo passo, chiede «Che cos'è?» con tre carte (suggerita: ritiro se ci sono notti, evento se è un giorno); la disciplina resta la categoria obbligatoria di oggi. Il listing `/public/retreats` espone `formato` nelle card e accetta il filtro `formato`; `/esperienze` guadagna un secondo filtro «Tipo» (Tutti · Ritiri · Eventi · Formazione) e un'etichetta sulla card; `_categorie_con_ritiri` e le pagine categoria/regione non cambiano. Modifica dal pannello dell'evento (il campo vive nel prodotto, stesso PATCH del nome). Guardie: le 15 discipline identiche, un payload senza `formato` è accettato come oggi, un valore fuori lista dà 422, i 10 eventi in prod si aprono e si listano come prima.

**Frontend da allineare**: `constants/itemTypes.js` (aggiungere `digital`, etichette, badge), `features/cashflow/IncassiPage.js` (etichette già pronte), `modules/product_catalog/service.py:542` (contatori), `modules/customer_insights/refresh.py:443` (contatore acquisti prodotti).

## 7. Isolamento, sicurezza, scalabilità

- **Modulo spento = invisibile**: nessuna voce di menu, nessuna sezione sul profilo, nessuna rotta registrata nel frontend, 403 `module_not_active` dal backend. Interruttore di emergenza per organizzazione dalla regia, con audit.
- **Il motore pagamenti cambia in un punto** (fee per riga) con guardie: ordine solo ritiri (fee 0 identica a oggi, byte per byte), ordine misto (ritiro + libro), rimborso parziale, Pro attivo, Pro scaduto a metà mese, caparra.
- **File**: mai statici, sempre via token con contatore atomico e scadenza (già così); volume Docker per `private_uploads` nel primo lotto, con guardia sul compose; limiti per piano; tipo MIME controllato; nome non indovinabile.
- **Pubblicazione**: tre lucchetti server-side (Stripe pronto, condizioni pubblicate, patto accettato): il frontend li mostra, il backend li impone.
- **Scalabilità**: i byte dei file non passano dal checkout; download diretto dal backend con streaming (già così) fino a quando non serve S3 firmato (adapter già previsto). Indici: `(organization_id, item_type, is_published)`, `(platform_account_id, status)` sui download.
- **Regressioni**: la guardia di riattivabilità del legacy (`test_listino_tw.py`) non si tocca; `legacy_commerce` resta spento per tutti; il Listino e i ritiri non cambiano di una riga.

## 8. I lotti

| Ordine | Lotto | Contenuto | Giorni | Dipende |
|---|---|---|---|---|
| 1 | **S Stripe giusto** | paese scelto dall'operatore (Italia preselezionata) passato a Stripe con valuta coerente, TWINT solo CH, «Ricomincia col paese giusto» per i 3 account nati svizzeri, paese nel webhook e nella regia, copy italiano; **prova della commissione CH→IT in test** | 1 | — |
| 2 | **P0 Fondamenta** | fee per riga (5 tocchi + guardie); mappa nel piano; modulo `prodotti` nel registro + tier + interruttore; scheda Strumenti dal registro con «Collega gli incassi» e «Condizioni di vendita» in un passo; volume `private_uploads`; patto DPA esteso; testi (/costi, landing, piani, Termini) | 3 | S + decisione sulle percentuali |
| 3 | **P1 Digitali** | wizard in tre gesti; upload con limite per piano; sezione «Prodotti» sul profilo + landing `/dg/`; acquisto con account Aurya; `IssuedDownload` su `platform_account_id`; «I miei file» in `/account`; email FL3; lista e modifica in Strumenti; vendite per prodotto | 3 | P0 |
| 4 | **P2 Fisici** | wizard in tre gesti; spedizione e magazzino già pronti; landing `/ph/`; coda di evasione in Ordini; varianti dietro «Altro» | 2 | P0 |
| 5 | **P3 Dashboard e insight** | riga «Prodotti venduti» in dashboard, etichette e costanti allineate, contatori customer insight, `by_type` verificato in Incassi e nella regia | 1 | P1 |
| 6 | **P4 Formato delle esperienze** | campo `formato` (ritiro · evento · formazione) separato dalla disciplina; tre carte nel primo passo del wizard eventi; filtro «Tipo» ed etichetta su `/esperienze`; modifica dal pannello; terza carta del selettore prodotti che apre il wizard con formato «formazione»; guardie sugli eventi esistenti | 1 | — (si può fare subito) |
| | **Totale** | | **11** | |

Ogni lotto: guardia propria, suite al baseline, deploy separato con prova dal browser in prod (lezione della CSP), documento e memoria. P4 è il primo giro utile anche oggi: un giorno, e i due corsi già pubblicati si dichiarano «formazione» con un clic dal loro pannello.

## 9. Rischi veri

| Rischio | Risposta |
|---|---|
| Nessuno collega Stripe | lotto S toglie la causa (paese); poi «Collega gli incassi» è il primo riquadro, con stato in italiano; la regia vede chi manca; i primi due operatori li si accompagna al telefono |
| Commissione rifiutata tra piattaforma CH e account IT | prova in test nel lotto S prima dei testi; vie d'uscita note |
| Promessa «senza commissioni, mai» | i testi cambiano prima della fee; la distinzione resta netta: ritiri e servizi a zero |
| File persi a un rebuild | volume nel primo lotto + guardia sul compose |
| Ordine misto con fee sbagliata | fee per riga con guardie su ogni combinazione; registro confronta con quanto Stripe ha trattenuto |
| Operatore che vende senza condizioni legali | lucchetto server-side alla pubblicazione |
| La formazione «vuole» campi che gli eventi non hanno (attestato, prerequisiti) | per ora testo nel programma; quando tre operatori li chiedono, un lotto piccolo sugli eventi, non un tipo nuovo |

## 10. Decisioni del founder (6/10/2026)

1. Formazione in presenza = esperienza con una data (wizard eventi), con il **campo nuovo «formato»** separato dalla disciplina: ritiro · evento · formazione. Nessun terzo tipo di prodotto.
2. Percentuali: prodotti **15% nel Gratis, 0% nel Pro**, ritiri e servizi 0. Più i costi Stripe.
3. Account Aurya obbligatorio per comprare un prodotto, anche fisico.
4. Ordine: S → P4 → P0 → P1 digitali → P2 fisici → P3.
Vincolo dichiarato: gli eventi sono live e funzionano; ogni tocco agli eventi è additivo e coperto da guardie sui dati esistenti.

## 11. Stato (6/10/2026 sera)

**P4 «formato» IN PROD** (6/10 sera, `prod-2026-10-06-formato`, mappatura scritta: 2 formazione, 1 ritiro, 7 evento):
- backend: `FORMATI_ESPERIENZA` in `models/retreat_taxonomy.py` (+ `errore_formato`, `formato_suggerito`), `EventTicketMetadata.formato` facoltativo, 422 nel wizard e nel PATCH prodotto se fuori lista, `formati_esperienza` in `/products/taxonomies`, il duplica porta il formato, `/public/retreats` con `?formato=`, `formato` sulle card e conteggi `formati` (stessa regola RE-ter: mai un'opzione vuota), `formato` nel prodotto della landing pubblica; `scripts/formato_esperienze.py` (`--lista`, `--imposta pref=formato`, `--scrivi`) per la mappatura della regia;
- frontend: tre carte «Che cos'è?» nel primo passo del wizard eventi (suggerita dalle date finché non si tocca, `?formato=` dall'URL per la futura terza carta dei prodotti), selettore nel pannello evento (parte da «Non indicato» sulle righe vecchie), filtro «Tipo» ed etichetta sulla card in `/esperienze` (`?tipo=`);
- guardie: `backend/tests/test_formato_fm.py` (15 test: schema, wizard, PATCH, listing, superfici) + le suite storiche eventi/listing/prelaunch verdi;
- mappatura decisa per le 10 esperienze in prod (nel giro, prova generale poi scrittura): i due corsi (Reiki I livello, Theta Healing DNA Base) → formazione; «Il ritorno alle origini» (tre giorni con alloggio) → ritiro; le altre sette (serate, giornate, i quattro seminari di due giorni in sala de «Il Potere dell'Immaginazione») → evento. Si cambia con un clic dal pannello dell'evento o con lo script.

**Lotto S «Stripe giusto» IN PROD** (6/10 sera, `prod-2026-10-06-stripe`; i 3 account svizzeri restano finché gli operatori non ricominciano dalla card):
- `Account.create` passa SEMPRE `country` e `default_currency` (IT→eur, CH→chf, più DE/FR/AT/ES); TWINT chiesto solo per CH; paese scelto nel riquadro (Italia preselezionata, suggerito CH se valuta CHF o sede in Svizzera) e scritto in `payment_connections.country`; complete e webhook `account.updated` salvano il paese vero da Stripe anche sulle righe nate prima;
- «Ricomincia col paese giusto» (`POST /payment-connections/stripe/express/ricomincia`): solo su account mai completati (`details_submitted=False`, `charges_enabled=False`, non pronto): `Account.delete` su Stripe, riga archiviata con traccia (`metadata.ricomincia` + evento `restarted_with_country` nella history), nuovo account col paese nuovo; rifiutato con 400 sugli account operativi; i tre account svizzeri in prod NON si toccano d'ufficio: lo fa l'operatore dalla card (o la regia su richiesta);
- card Pagamenti: select del paese prima di «Collega gli incassi con Stripe», riga «Account Stripe registrato in …» con avviso se CH e non pronto, blocco «Ricomincia», righe archiviate nascoste, copia italiana dei badge;
- guardie: `backend/tests/test_stripe_paese_sp.py` (19 test) + suite Stripe storiche verdi (il test TWINT ora prova il caso CH esplicito);
- **prova della commissione CH→IT in test mode: CONCLUSA il 6/10 sera** (terzo tentativo, coi valori di verifica documentati da Stripe): account Custom IT sotto la piattaforma CH con `charges_enabled`, addebito di 20 € con `application_fee_amount` 3 € riuscito in tutte e tre le forme (diretto con `stripe_account`, destination, destination + `on_behalf_of`). La commissione tra paesi passa: nessuna piattaforma italiana necessaria.
- fuori dal lotto, rimandato: la colonna «Incassi» nella regia Operatori (nessun endpoint admin legge oggi le connessioni Stripe).

**Lotto P0 «Fondamenta» IMPLEMENTATO in locale** (6/10 notte, giro `deploy/giri/deploy-2026-10-06-prodotti-p0.sh`, attende il via). Niente si vende ancora: le rotte dei prodotti arrivano con P1.
- **fee per riga** (`services/fee_per_riga.py`): la mappa `{physical, digital}` viene dal piano (`transaction_fee_by_type`: Gratis 15/15, Club·Pro·Founding·Partner 0/0) e dall'org (`application_fee_by_type`, propagata al provisioning; fallback al piano per le org nate prima); il tipo della riga è quello VERO del prodotto oggi (lettura fresca: lo snapshot ha default «physical»); sconto coupon ripartito in proporzione; spedizione senza fee; caparre e rate portano una quota proporzionale; il provider riceve l'importo (`application_fee_minor`, vince sulla percentuale storica che resta a 0); metadata con importo, scomposizione e percentuale effettiva; ledger con `fee_minor` esatto e `fee_by_type`; i rimborsi usano la percentuale dell'incasso (`resolve_fee_percent_for_order`). Il tetto del campo storico resta `le=10` (la fee prodotti non ci passa).
- **modulo `prodotti`** registrato (`modules/prodotti`), tier `prodotti_retreat_free` (20 prodotti, 100 MB) e `prodotti_retreat_pro` (200, 500 MB) nei piani, `MODULE_OWNERSHIP["prodotti"]`, interruttore di regia `prodotti_spento` (flag per org, letto da `require_module`), patto DPA esteso a fisici e digitali.
- **migrazione d'avvio** `migrate_prodotti_p0_v1`: modulo attivo + abbonamento al tier + mappa fee su tutte le org `retreat_*` (in locale: 11 org, 8 al 15%, 3 abbonate a 0). Il seed riscrive la mappa dei piani a ogni avvio.
- **volume** `ms-backend-private-uploads` su `/app/private_uploads` nel compose di prod.
- **Strumenti**: scheda «Prodotti · In arrivo» letta dal registro (`/modules/active`) con lo stato degli incassi (Stripe pronto o «Collega gli incassi»).
- guardie: `backend/tests/test_prodotti_p0.py` (23) + i pin storici aggiornati (cinque moduli nel Gratis, ownership con `prodotti`, tier nel referenziale); suite completa senza rossi nuovi.
- i testi (/costi, landing, piani, Termini) e il bump legale sono arrivati con P1 (sotto).

**Lotto P1 «Digitali» IMPLEMENTATO in locale** (6/10 notte; giro unico P0+P1 `deploy/giri/deploy-2026-10-07-prodotti-p1.sh`, attende il via; il founder prova su localhost):
- **API** `routers/prodotti.py` sotto `require_module("prodotti")`: lista con prerequisiti (Stripe pronto, patto, pagina pubblica) e venduti a 30 giorni, crea (bozza, direct, prezzo fisso; via `create_product` per slug, quota `products_max`, tassonomia, patto), modifica, **pubblica** con i tre lucchetti + file per i digitali (409 `non_pubblicabile` con le ragioni in chiaro), ritira, elimina (disattiva), vendite (riusa `sales-stats`); l'upload del file riusa `/products/{id}/digital-file` con il **limite del piano** (`max_file_mb`).
- **Profilo pubblico**: `prodotti` nel payload (`_operator_prodotti`: pubblicati, direct, digitali solo col file, fisici non esauriti) e sezione «Prodotti» con card e **acquisto in pagina** (`InlineProdottoCheckout`, stesso hook e form dello storefront).
- **Account obbligatorio**: il token dell'account Aurya viaggia nell'header `X-Aurya-Account` (`storefrontAPI.submitOrder`); l'ordine con righe prodotto senza account è rifiutato (`prodotto_richiede_account`), con account l'ordine è timbrato con l'id vero; `CheckoutForm` con `richiedeAccount` (avviso + invio spento finché non si entra). Il link per email resta per gli ospiti di ritiri e servizi.
- **«I miei file»**: `GET /platform/me/file` (download attivi via `orders.platform_account_id` → `IssuedDownload`, link `/d/{token}` esistente) e sezione in `/account`.
- **Gestionale**: `/prodotti` (prerequisiti, lista, tre carte: digitale · fisico «in arrivo» · formazione → wizard eventi con `?formato=formazione`), `/prodotti/nuovo/digitale` (tre gesti: cos'è → il file con barra → pubblica; «Altro»: scaricamenti massimi e scadenza), `/prodotti/:id` (modifica, file, pubblica/ritira, vendite); scheda Strumenti «Prodotti · Attivo → I miei prodotti»; `itemTypes.js` conosce `digital`.
- **Testi e legale v2.12**: `/costi` (quattro verità e schede: l'unica commissione è sui prodotti, 15% Gratis / 0 Pro; `AURYA_FEE_PRODOTTI` pinnato al seed), piani (`billing.retreat`), landing (`doorOpText`, `prosOffer`, `faq4a`), Termini §6.4 e §7.1-7.2 ×4 lingue (commissione SOLO sui prodotti, riga per riga, spedizione esclusa, pro-quota nei rimborsi), `legal_versions` v2.12 con hash ricalcolato e avviso «cosa è cambiato» ×4. Il bump innesca il re-consent degli operatori (un clic).
- **Provato dal vivo in locale** (API + browser): creazione, upload, 409 senza Stripe, pubblicazione, card sul profilo, ordine rifiutato senza account, ordine con account → session Stripe di test con `application_fee_minor` 180 su 1200 (15%) nel metadata, download emesso e visibile in «I miei file».
- guardie: `backend/tests/test_prodotti_p1.py` (12) + `test_rebranding_rb` aggiornato alla nuova verità sui soldi.
- **Fuori da P1, rimandato**: email FL3 dedicate «Il tuo file è pronto» (oggi la conferma d'ordine storica porta già i link di download); la landing `/dg/` resta la via legacy (col carrello dello store): l'acquisto dei prodotti è dal profilo.

**Lotto P2 «Fisici» + chiarezza IMPLEMENTATO in locale** (6/10 notte, stesso giro `deploy-2026-10-07-prodotti-p1.sh`, attende il via). Decisioni del founder (6/10 sera) recepite:
- **Formazione fuori da Prodotti**: la carta è sparita; resta una riga che rimanda a Ritiri ed esperienze (`/events/new?formato=formazione`). Nessun conflitto tecnico (la commissione dipende dal tipo di riga: `event_ticket` = 0 e Stripe facoltativo da qualunque porta), ma una porta sola è più chiara.
- **Commissione in chiaro** in `/prodotti` (`commissione` nel payload, dalla mappa dell'org: «col tuo piano Aurya trattiene il X%» o «nessuna commissione sui prodotti»).
- **Termini a principio**: §6.4 e §7.1-7.2 ×4 dicono che la commissione riguarda solo i Prodotti «nella misura pubblicata su /costi per il Piano attivo»; i numeri vivono SOLO su `/costi`. Cambiare una percentuale domani non richiede un nuovo bump. Stessa v2.12 (mai andata in prod), hash ricalcolato `69137d1e3f451f81`.
- **Fisici**: `GET/PUT /prodotti/consegna` (modi dell'org via `update_store_settings` + opzione org-global «Spedizione» a costo fisso con soglia gratis, create-or-update), wizard `/prodotti/nuovo/fisico` in tre gesti (cos'è con quantità o illimitata → come arriva → pubblica), card «Fisico» sul profilo con «Compra»: il checkout in pagina propone ritiro/spedizione, indirizzo e l'opzione (il gancio carica le opzioni solo «a modale aperto»: l'inline lo dichiara con `setFormOpen(true)`); stock validato all'ordine, stati di evasione in Ordini.
- **Provato in locale**: consegna salvata (ritiro + spedizione 6 €, gratis sopra 50), catalogo pubblico con i due modi, wizard fisico dal browser fino a «Online», ordine fisico via API con account: totale 31 € (25 + 6), evasione «pending», session Stripe di test.
- **Design**: lista prodotti a card (foto, stato, tipo, prezzo in italiano, venduti, azioni), prezzi con `fmtEuro`, card del profilo con prezzo italiano; mobile verificato.
- guardie: `TestP2Fisici` in `test_prodotti_p1.py` (consegna, commissione, niente formazione, Termini a principio) + pin dei Termini aggiornati.

**Consolidamento pre-live IMPLEMENTATO in locale** (6/10 notte, stesso giro `deploy-2026-10-07-prodotti-p1.sh`, attende il via). Richiesta del founder: «tutto funziona? email solide, comunicative, umane». Flusso provato dal vivo con un pagamento Stripe di test (carta 4242, ordine ORD-10004):
- **Come funziona un digitale**: l'operatore carica il file (PDF o altro, limite del piano) e pubblica; il cliente compra dal profilo con l'account Aurya; il file NON è mai raggiungibile prima dell'incasso: `issue_for_order` emette il download SOLO dentro `confirm_order`, cioè dopo che Stripe ha detto «pagato» (webhook o verifica); il link `/d/{token}` è a scaricamenti contati e scadenza; lo ritrova in `/account → I miei file`.
- **Pagina di successo immediata**: `POST /public/orders/{id}/verifica-pagamento` (10/min) chiede a Stripe se la session è pagata e riconcilia subito, senza aspettare il webhook; la pagina chiama la verifica UNA volta e poi fa polling; se c'è una riga digitale mostra «Il tuo file è pronto → Vai ai miei file» (`item_types` nello status pubblico, mai le righe).
- **Idempotenza** (il bug trovato: due verifiche insieme → due «Nuovo ordine pagato»): lucchetto per ordine nell'endpoint (`_VERIFICHE_IN_CORSO`) + guardiano in `reconcile_checkout_event`: stessa session già incassata e ordine confermato → `already_collected`, niente seconda conferma né seconda email. Le session delle rate passano (incassi diversi). Provato: due riconciliazioni concorrenti → `already_collected | already_collected`, endpoint pubblico doppio → `already_reconciled`.
- **Email all'operatore «Nuovo ordine pagato — {cliente}»**: variante quando l'incasso è avvenuto (prima diceva «richiesta d'ordine» anche a soldi incassati): totale incassato, email e telefono del cliente, indirizzo di spedizione o «ritiro di persona», per i digitali «file consegnato in automatico: non devi fare nulla», CTA all'ordine. La variante storica resta per gli ordini non pagati (+ riga telefono).
- **Email al cliente**: corpo per tipo (digitale: «il pagamento è andato a buon fine e il tuo file è pronto… lo ritrovi in I miei file», CTA «Vai ai miei file»; spedizione; ritiro; storico per il resto); costo di spedizione formattato nella valuta dell'ordine.
- **Ordini nel gestionale**: email e telefono sotto il nome nella lista (`ordine-contatti`); il dettaglio aveva già indirizzo, righe, evasione.
- **Carta obbligatoria**: i prodotti nascono `transaction_mode="direct"` e si pubblicano solo con Stripe pronto (lucchetto), quindi ogni ordine prodotto passa dalla session Stripe: nessun «pago dopo».
- guardie: `TestConsolidamento` in `test_prodotti_p1.py` (verifica pubblica, lucchetto, idempotenza, hint file, varianti email); suite completa senza rossi nuovi (gli unici rossi fuori baseline erano falsi positivi da file modificati a suite in corso, verdi al rilancio).
- **Fuori, rimandato**: colonna «Incassi» nella regia Operatori; P3 dashboard/insight prodotti; un passo di design sul profilo pubblico.

**Lotto DP «Design + la pagina del prodotto» IMPLEMENTATO in locale** (6/10 notte, stesso giro `deploy-2026-10-07-prodotti-p1.sh`; in prod i Prodotti restano in ANTEPRIMA finché il founder non sblocca `PRODOTTI_UI_PRONTA`). Richiesta: «design olistico: moderno, stiloso, pulito, user-friendly, multipiattaforma; una landing per prodotto come per gli eventi; Compra + maggiori info sul profilo; via le categorie visibili».
- **La pagina del prodotto** `/prodotto/{public_slug}/{slug}` (`ProdottoLandingPage`): immagine, nome, chi lo vende (ritratto, città, verificato, stelle), descrizione, prezzo, «Compra» che apre in pagina lo stesso checkout del profilo (`InlineProdottoCheckout`, account Aurya + Stripe), «Condividi» (share nativo o copia), «come funziona» in tre righe vere (digitale: file e consegna automatica; fisico: ritiro/spedizione/soglia gratis/scorte), «Il racconto» (il `long_description`, a capo rispettati), «Altro di {operatore}», barra fissa prezzo+Compra su telefono, 404 gentile. Niente etichetta Digitale/Fisico: il tipo decide solo cosa si spiega.
- **Backend** `GET /public/prodotto/{org_slug}/{slug}`: risolve dal `public_slug` come il profilo (le landing legacy `/p` `/dg` `/ph` passano dallo store, che 4 operatori su 7 non hanno), campioni esclusi, pagina pubblica richiesta; usa la STESSA lista del profilo (`_operator_prodotti`): se non è sul profilo non ha pagina. Meta per i bot (`_meta_prodotto`: title, description sensata, OG, JSON-LD Product + breadcrumb), rotta nel registro (`pubblica` + `solo_con_slug`, nginx rigenerato), sitemap: fisici e digitali su `/prodotto/`.
- **Profilo**: card a immagine piena, senza etichetta di tipo, «Scopri di più» → pagina + «Compra» in pagina; stessi testid.
- **Gestionale**: kit `features/prodotti/ui.js` (campi con etichetta sopra e suggerimento sotto, bottoni 42px, schede, passi a tre segmenti, anteprima senza tipo, selettore immagine con miniatura, link della pagina con Copia/Apri); `/prodotti` (prerequisiti = riga verde quando tutto c'è, lista con «Copia link» del prodotto online, commissione e limiti in una riga in fondo), `/prodotti/:id` (La scheda con «Il racconto completo», Il file, La pagina del prodotto, Vendite a tre numeri; Salva attivo solo con modifiche), i due wizard (passi, «Altro» col racconto, modi di consegna a card). Il `public_slug` arriva dal payload del gestionale.
- guardie: `TestDesignDP` in `test_prodotti_p1.py`; pin `solo_con_slug` e nginx aggiornati in `test_indicizzazione_ix.py`.

**Rifinitura GL «Galleria + proporzioni» IMPLEMENTATA in locale** (6/10 notte). Founder: «nel profilo i prodotti della stessa misura dei ritiri; più foto per prodotto, nella pagina una principale e sotto le altre, ci si muove avanti e indietro».
- **Modello**: `image_url` = la principale, `metadata.galleria` = le altre in ordine; `_galleria(prod)` le unisce senza doppioni. Massimo 8 foto, 5 MB l'una, stesso storage delle copertine (`save_public_upload`, ottimizzate in WebP).
- **API** (`routers/prodotti.py`, prima del PATCH): `POST /prodotti/{id}/foto` (la prima diventa principale), `DELETE /prodotti/{id}/foto` {url} (se era la principale, la prossima prende il posto), `POST /prodotti/{id}/foto/principale` {url}. `galleria` nella riga del gestionale, nel profilo e nella landing. Provato dal vivo: 3 foto, principale cambiata, nona rifiutata, cancellazioni.
- **Gestionale**: scheda «Le foto» (`GestoreFoto`: griglia, badge Principale, Principale/Togli, aggiungi anche più foto insieme); i wizard accettano più foto al passo 1 (`SceltaImmagine multiple`), caricate dopo la bozza. Il selettore singolo nella scheda è uscito.
- **Landing**: `Galleria` (foto grande con frecce e contatore, miniature sotto, tastiera ← →, scorrimento col dito); con una sola foto niente frecce.
- **Profilo**: card prodotto della misura dei ritiri (immagine h-36, p-3, bottoni 34px): tutto proporzionato.
- guardie: `TestGalleriaGL` in `test_prodotti_p1.py`.

