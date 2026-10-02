# La fascia d'età nel Cerchio — piano

*2 ottobre 2026. Decisione del founder: aggiungere l'età al modulo di `/cerca-ritiro` (oggi sponsorizzato), come fascia facoltativa e motivata; il dato, se compilato, deve vedersi nella regia «Iscritti al Cerchio». Vincolo: zero regressioni, la pagina deve restare snella.*

## 0. Le scelte (già prese nella conversazione)

| Scelta | Decisione | Perché |
|---|---|---|
| Età esatta o fascia | **Fascia**: 18-29 · 30-44 · 45-59 · 60 e oltre | nel pubblico di Aurya l'età esatta pesa, la fascia no; basta per proporre bene |
| Obbligatoria | **No**, facoltativa, con «preferisco non dirlo» = lasciare vuoto | ogni campo obbligatorio costa iscritti; il modulo ne ha già sei |
| Dove | **Dopo il budget**, dentro il blocco che già c'è (città, dove, budget), prima di «Cosa ti chiama?» | è l'ultima domanda di profilo, dove il modulo è già «pieno» |
| Motivazione sotto il campo | «Molti ritiri sono pensati per età diverse, nei ritmi e nel gruppo. Così ti proponiamo quelli giusti per te.» | vera: l'età entra nei filtri delle proposte e nelle liste Brevo da subito |
| Minori | **Nessuna opzione «meno di 18»** | aprirebbe un blocco in un modulo sponsorizzato; la regola 18+ resta su account e prenotazioni, com'è oggi |
| Testo della casella di consenso | **Non cambia** (versione invariata) | dice già «in base alle mie preferenze»; un testo pubblicato non si tocca (regola di `lib/testiConsenso.js`) |
| Informativa | riga 7-bis: «preferenze (temi, città, raggio, budget indicativo, **fascia d'età facoltativa**)», ×4 lingue, **v2.9** | trasparenza; nessuna finalità nuova, stessa base giuridica (consenso) |

## 1. Dove passa il dato oggi (e quindi dove si tocca)

Il campo gemello è **budget**: nasce nel modulo, viaggia nel subscribe, vive in `profile.budget`, lo vede e lo modifica l'iscritto, lo vede e lo filtra la regia, va a Brevo. L'età fa **esattamente lo stesso giro**, con lo stesso nome ovunque: `eta`.

| Punto | File | Cosa fa budget | Cosa farà eta |
|---|---|---|---|
| Vocabolario | `backend/routers/subscribers.py` (accanto a `TRAVEL_OPTIONS`) | valori liberi fino a 40 car. | `ETA_FASCE = ("18-29", "30-44", "45-59", "60+")`, tutto il resto scartato |
| Iscrizione | `SubscribePayload` + ciclo `for field in ("city","travel","budget")` | scrive `profile.budget` | `eta` nel payload; scritto solo se nella rosa |
| Preferenze dell'iscritto | `PreferencesPayload`, `GET/PUT /public/newsletter/preferences` | legge e aggiorna | idem |
| Regia: riga | `_riga_iscritto` | `"budget"` | `"eta"` |
| Regia: filtro | `_query_iscritti` + parametri di `list` ed `export.csv` | `?budget=` | `?eta=` |
| Regia: ripartizioni | `stats` → `by_budget` | conteggio per valore | `by_eta` |
| Regia: modifica | `AdminPreferencesPayload` + PATCH `/admin/subscribers/{email}/preferenze` + audit `campi` | `budget` | `eta` |
| CSV | `export.csv` | colonna `budget` | colonna `eta` **in coda** (le vecchie restano dove sono) |
| Brevo | `services/subscriber_brevo_sync._attributes` | `AURYA_BUDGET` | `AURYA_ETA` (attributo da creare in Brevo prima del deploy, come per BUDGET il 24/9) |
| Numeri del lunedì | `routers/admin_platform.numeri_del_lunedi` → `cerchio` | `con_citta` | `con_eta` (confermati con la fascia) |
| Sequenze | `services/sequenze.contesto_cerchio` | `travel` nel contesto | `eta` nel contesto (disponibile ai template, nessun template cambia ora) |
| Modulo | `features/prelaunch/PreferenzeRitiri.jsx` (blocco condiviso) + `LeadForm.jsx` | select `BUDGETS` | select `ETA` + riga di motivazione; reso **solo dove si passa `setEta`** |
| Chi lo passa | `LeadForm` (cerca-ritiro e ogni LeadForm col blocco ritiri), `NewsletterPreferencesPage` (l'iscritto lo può cambiare) | — | i cancelli (`AvvisamiRitiri` nudo) **no**: lì il blocco deve restare minimo |
| Etichette | `locales/{it,en,de,fr}/prelaunch.json` → `form.etaLabel`, `form.eta.*`, `form.etaHint` | `form.budget.*` | ×4 per la guardia di parità (era solo-italiano, ma la guardia pretende le chiavi) |
| Regia UI | `features/admin/IscrittiTab.js` | colonna, scheda, filtro, ripartizione, editor | idem, con mappa `ETA` delle etichette |
| Informativa | `backend/legal/privacy_*.md` riga 7-bis, `core/legal_versions.py` | — | v2.9 + hash ricalcolato |

Fuori perimetro, di proposito: `/public/leads` e la scheda «Contatti dalle landing» (il modulo di `/cerca-ritiro` non passa di lì), la pagina link `/@slug`, gli embed, i cancelli delle meditazioni.

## 2. Lotti

| Lotto | Cosa | Guardia |
|---|---|---|
| **ET1 backend** | rosa `ETA_FASCE`; `eta` in subscribe, preferenze pubbliche, riga regia, filtro, stats, PATCH admin con audit, CSV in coda, Brevo, numeri del lunedì, contesto sequenze | `test_cerchio_eta.py`: valore fuori rosa scartato, vuoto non scrive, riga/filtro/stats/CSV, PATCH con audit, payload senza `eta` (bundle vecchio) identico a oggi |
| **ET2 modulo** | `PreferenzeRitiri` con select + motivazione dietro `setEta`; `LeadForm` stato + `eta: eta \|\| null` nel solo ramo subscribe; `NewsletterPreferencesPage` legge/scrive; chiavi i18n ×4 | guardia sul sorgente (campo presente, facoltativo, nel ramo subscribe e non in `/public/leads`), parità locale |
| **ET3 regia** | `IscrittiTab`: mappa `ETA`, colonna «Età» dopo Budget (si accende anche per chi ha una scelta di colonne salvata), riga nella scheda, filtro `iscritti-f-eta`, ripartizione «Per età» cliccabile, select nell'editor preferenze | guardia sui testid e sui `toggleFiltro('eta'` |
| **ET4 informativa** | riga 7-bis ×4 lingue, `CURRENT_VERSION_TAG = "v2.9"`, hash ricalcolato, testo «Cosa è cambiato» del modal di ri-accettazione scritto giusto (oggi è generico) | guardie legali esistenti (hash, versioni) aggiornate |
| **ET5 prova e deploy** | prova in locale: iscrizione completa da `/cerca-ritiro` con la fascia → conferma email → regia (colonna, scheda, filtro, ripartizione, CSV) → preferenze dell'iscritto; prova **senza** fascia e con payload del bundle vecchio; suite al baseline; attributo `AURYA_ETA` creato in Brevo; giro backend+frontend | verifica in prod: subscribe di prova con la fascia, riga in regia, poi cancellazione della prova |

Ordine ET1 → ET2 → ET3 → ET4 → ET5, un giro solo. Stima: mezza giornata di lavoro più la prova.

## 3. Perché non può rompere la pagina sponsorizzata

- **Il campo è facoltativo e in più.** Chi non lo tocca manda lo stesso payload di oggi più `eta: null`; il backend ignora `null` e ignora i valori fuori rosa. Il flusso di iscrizione, il doppio opt-in, lo sblocco delle meditazioni e il «grazie» non cambiano di una riga.
- **Bundle vecchio in cache.** Durante e dopo il deploy ci sono visitatori col JavaScript precedente: mandano un payload **senza** `eta`. Il backend lo accetta come oggi (guardia esplicita in ET1).
- **Backend vecchio, frontend nuovo** non può succedere: il giro ricrea prima il frontend e poi il backend, ma un payload con una chiave in più su un `BaseModel` Pydantic senza `extra=forbid` viene comunque accettato (è così già oggi per gli altri campi).
- **Il testo della casella di consenso non cambia**, quindi `consenso_versione` resta la stessa e il registro dei consensi non vede discontinuità.
- **Regia e CSV**: colonna nuova in coda, filtro nuovo con default vuoto, ripartizione nuova accanto alle altre; chi ha salvato le colonne nel browser vede comparire «Età» senza perdere la sua scelta.
- **Brevo**: l'attributo va creato in Brevo prima del deploy; se manca, la sync continua a passare gli altri (stesso comportamento del 24/9 con BUDGET e CANALE).
- **Informativa v2.9**: il bump fa ricomparire il modal di ri-accettazione agli operatori al prossimo accesso (è il meccanismo esistente: confronta la versione accettata con quella corrente). È un clic, e stavolta il testo «Cosa è cambiato» dirà la cosa vera. Oggi sono circa 20 operatori.

## 4. Cosa misurare dopo

- **Tasso di compilazione** della fascia tra i nuovi iscritti da `/cerca-ritiro` (ripartizione «Per età» filtrata per porta, prime due settimane). Se resta vuota nella gran parte dei casi, il campo si toglie con un giro di solo frontend.
- **Conversione del modulo**: `nuovi_7g` nei numeri del lunedì e l'evento `generate_lead` su GA4, settimana prima contro settimana dopo. Se cala in modo netto, idem.
- **Uso**: le liste Brevo segmentate per `AURYA_ETA` e il filtro in regia sono l'uso immediato; le sequenze hanno già il dato nel contesto quando servirà un testo per fascia.

## 5. Decisioni del founder

1. Le quattro fasce (18-29, 30-44, 45-59, 60 e oltre) vanno bene, o preferisci tagli diversi (per esempio 30-39 / 40-49 / 50-59)?
2. La riga di motivazione sotto il campo: ok quella proposta, o la vuoi riscrivere tu?
3. Via al giro unico ET1-ET5 appena la prova in locale è pulita, o vuoi vedere il modulo in locale prima del deploy?
