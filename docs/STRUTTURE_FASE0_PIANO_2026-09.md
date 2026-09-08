# Strutture ricettive · Fase 0 — piano di implementazione (8/9/2026)

Decisione del founder: si parte dalla fase 0 (la scheda la scrive
il system admin), ma con la predisposizione per la fase 1 (la
struttura si registra e gestisce da sola) senza rifare niente. Tutto
isolato e scalabile. Nella nuova pagina dell'area amministratore si
inseriscono tutte le informazioni utili a organizzare un ritiro
olistico: camere, tipi e numero di letti, sala pratica, aria
condizionata, prezzi per stagione, posizione, piscina, spazi esterni e
il resto; tutto strutturato, consultabile e filtrabile, immediato da
inserire e da cercare.

## 0. Il principio: un solo modello, due porte

La scheda della struttura è **un unico modello dati** (`Struttura`)
dal primo giorno. In fase 0 la porta è il pannello di sistema; in
fase 1 si apre la seconda porta (l'area della struttura) sullo
**stesso** modello, stesse validazioni, stessa collezione, stesse API
di lettura. Nessuna migrazione: i campi della fase 1 esistono già
oggi, vuoti.

Campi di predisposizione (fase 0 li scrive, fase 1 li usa):
- `organization_id`: oggi `null`; in fase 1 punta all'organizzazione
  con `kind = "struttura"` che «adotta» la scheda.
- `origine`: `"redazione"` (scritta da voi) o `"struttura"` (scritta
  dal proprietario).
- `slug`: unico, generato dal nome, è l'URL pubblico futuro
  `/strutture/{slug}`.
- `visibilita`: `"riservata"` (solo voi e, in fase 1, gli operatori
  loggati) o `"pubblica"` (pagina SEO, solo quando la pubblicate voi).
- `stato_pipeline`: `da_contattare`, `contattata`, `visitata`,
  `in_lista`, `sospesa`. È il vostro CRM di campo.
- `redazione`: note interne mai pubbliche (giudizio onesto, referente,
  storia dei contatti). Separato da `descrizione` che è pubblicabile.
- `creato_da` / `aggiornato_da` / date: audit fin dall'inizio.

## 1. Il modello dati (`backend/models/struttura.py`)

Sezioni, ognuna un sotto-modello Pydantic, tutte opzionali tranne
identità e luogo. Le enumerazioni sono liste chiuse (filtrabili),
mai testo libero dove si deve cercare.

**Identità**: `nome`, `slug`, `tipo` (masseria, agriturismo, casale,
eremo, centro_ritiri, bed_and_breakfast, villa, hotel, rifugio,
altro), `descrizione` (pubblicabile), `sito`, `foto[]` (url, alt,
ordine), `foto_copertina`.

**Luogo**: `indirizzo`, `comune`, `provincia`, `regione` (le 20 di
`ITALIAN_REGIONS`, già nel codice), `cap`, `latitudine`, `longitudine`
(a mano, come per gli eventi), `come_si_arriva` (testo), `stazione_km`,
`aeroporto_km`, `contesto` (mare, collina, montagna, campagna, lago,
bosco, città), `silenzio` (1-5), `raggiungibile_senza_auto` (bool).

**Ricettività**: `posti_letto_totali`, `camere[]` con `tipologia`
(singola, doppia, matrimoniale, tripla, quadrupla, camerata, glamping,
appartamento), `quantita`, `letti` (numero letti nella camera),
`tipo_letti` (singoli, matrimoniale, castello, misti), `bagno`
(privato, condiviso), `note`; `bagni_totali`; `accetta_letti_condivisi`
(bool); `uso_esclusivo_possibile` (bool); `persone_min`, `persone_max`.

**Spazi di pratica**: `sale[]` con `nome`, `mq`, `altezza_m`,
`pavimento` (legno, cotto, pietra, moquette, altro), `capienza_persone`,
`riscaldata` (bool), `climatizzata` (bool), `luce_naturale` (bool),
`attrezzata` (tappetini, cuscini, coperte, impianto audio, proiettore),
`note`; `spazi_esterni[]` con `tipo` (prato, terrazza, giardino, uliveto,
bosco, spiaggia, piazzale), `mq`, `ombra` (bool), `adatto_pratica`
(bool).

**Comfort e servizi**: `aria_condizionata` (nessuna, camere, sale,
tutto), `riscaldamento` (bool), `wifi` (assente, debole, buono),
`piscina` (nessuna, esterna, interna, riscaldata), `sauna`, `vasca`,
`parcheggio` (posti), `accessibile_disabili` (bool), `animali` (bool),
`lavanderia` (bool), `altri_servizi[]` (testo breve).

**Cucina**: `cucina` (struttura, cuoco_esterno_ammesso, self_service,
nessuna), `regimi[]` (vegetariano, vegano, senza_glutine,
senza_lattosio, ayurvedico, crudista, macrobiotico), `pasti_inclusi`
(nessuno, colazione, mezza_pensione, pensione_completa, su_richiesta),
`prodotti_propri` (bool), `note_cucina`.

**Prezzi**: `valuta` (EUR), `stagioni[]` con `nome` (bassa, media,
alta, altissima o libero), `dal` / `al` (giorno-mese, ricorrenti),
`tariffe[]` con `base` (persona_notte, camera_notte,
struttura_notte, persona_soggiorno), `tipologia_camera` (o `tutte`),
`trattamento` (solo_pernotto, colazione, mezza_pensione,
pensione_completa), `prezzo`; `affitto_esclusivo_notte` (prezzo),
`minimo_notti`, `minimo_persone`, `acconto_percento`,
`cancellazione` (testo), `tassa_soggiorno` (bool + importo),
`note_prezzi`. Per i filtri si calcola e si salva `prezzo_da` (la
tariffa persona-notte più bassa) a ogni salvataggio.

**Adatta a**: `adatta_a[]` (yoga, meditazione, breathwork, digiuno_detox,
cerchi, sound_healing, cammini, aziende, famiglie, silenzio,
ayurveda, danza, arti), `esperienza_ritiri` (mai, qualche, abituale),
`ritiri_ospitati_note`.

**Disponibilità**: `stagionalita` (tutto_anno, chiusura[] mesi),
`disponibilita_note`; il calendario vero arriva in fase 2.

**Contatti** (mai pubblici in fase 0): `referente`, `ruolo`,
`telefono`, `email`, `preferisce` (telefono, email, whatsapp).

**Redazione**: `stato_pipeline`, `visitata_da`, `visitata_il`,
`giudizio` (1-5), `punti_forti`, `punti_deboli`, `storia[]`
(data, chi, nota), `prossimo_passo`.

Ogni enumerazione vive in `backend/models/struttura.py` come tupla,
esportata anche al frontend via un endpoint `GET /admin/strutture/schema`
(etichette italiane), così il form e i filtri non duplicano le liste.

## 2. Persistenza (`database.py` + `repositories/struttura_repository.py`)

- Collezione `strutture`; indici: `slug` unico, `regione`,
  `stato_pipeline`, `visibilita`, `posti_letto_totali`, `prezzo_da`,
  `adatta_a` (multikey), `organization_id` (sparse, per la fase 1), e
  un indice testuale su `nome`, `comune`, `descrizione`.
- Repository con: `crea`, `aggiorna` (merge di sezione, non
  sovrascrittura totale: il form salva una sezione alla volta),
  `trova` per id o slug, `cerca(filtri, pagina)`.
- Slug: dal nome, unico, con suffisso numerico in caso di conflitto;
  non cambia mai dopo la prima pubblicazione (fase 1).

## 3. API (`backend/routers/admin_strutture.py`, prefisso `/admin/strutture`)

Solo `require_system_admin` in fase 0. In fase 1 nascono
`/struttura/...` (area del proprietario) sullo stesso repository, con
`require_struttura`: per questo la logica sta nel repository e nel
service, non nel router.

- `GET /admin/strutture/schema`: enumerazioni con etichette.
- `GET /admin/strutture`: lista paginata (20) con filtri: `q` (testo),
  `regione[]`, `tipo[]`, `stato_pipeline[]`, `visibilita`,
  `posti_letto_min`, `persone_max_min`, `sala` (bool: almeno una sala),
  `sala_mq_min`, `aria_condizionata`, `piscina`, `cucina`, `regimi[]`,
  `adatta_a[]`, `prezzo_max` (su `prezzo_da`), `uso_esclusivo`,
  `contesto[]`; ordinamento per `aggiornato_il`, `nome`, `prezzo_da`,
  `posti_letto_totali`. Risposta: righe compatte per la tabella
  (nome, tipo, comune, regione, posti letto, sale, prezzo da, stato,
  visibilità, aggiornato) + conteggi per facet (quante per regione,
  stato, tipo) per rendere i filtri «vivi».
- `POST /admin/strutture`: crea con nome e regione minimi.
- `GET /admin/strutture/{id}`: scheda intera.
- `PATCH /admin/strutture/{id}`: aggiorna una o più sezioni (body
  parziale, validato per sezione).
- `POST /admin/strutture/{id}/foto` + `DELETE .../foto/{indice}`:
  stesso motore delle foto del profilo (compressione lato client,
  cartella `uploads/strutture/{id}/`), ordine con `PATCH`.
- `POST /admin/strutture/{id}/storia`: aggiunge una riga alla storia
  dei contatti (data, chi, nota, prossimo passo).
- `DELETE /admin/strutture/{id}`: solo se mai pubblicata; altrimenti
  `visibilita = "riservata"` e `stato_pipeline = "sospesa"`.
- Nessuna rotta pubblica in fase 0. Nel registro delle rotte si
  **riserva** `strutture` (pubblica, fase 1) e `struttura` (app,
  fase 1) senza collegarle: la guardia del registro le conosce già.

## 4. Il pannello (`frontend/src/features/admin/StruttureTab.js` + sottocomponenti)

Nuovo tab «Strutture» in `AdminPage` (deep link `?tab=strutture`).

**Lista** (`StruttureLista.jsx`):
- barra filtri sempre visibile: ricerca testo, regione (multi), tipo,
  stato pipeline, posti letto minimo, «ha una sala», piscina, aria
  condizionata, cucina, adatta a (chip), prezzo massimo a persona;
  i filtri sono nell'URL (`?regione=Puglia&posti_min=15`), così una
  ricerca si condivide tra voi due con un link.
- tabella con le colonne compatte, ordinabile, 20 per pagina, badge
  di stato e di visibilità, ultima modifica; conteggi per facet a
  fianco dei filtri.
- pulsante «Nuova struttura»: chiede solo nome e regione, apre la
  scheda.

**Scheda** (`StrutturaScheda.jsx`), una sezione per accordion, ognuna
con il suo «Salva» e stato «salvato / modifiche non salvate»:
1. Identità e foto (upload con anteprima, riordino, copertina).
2. Luogo (regione a tendina, coordinate a mano, contesto, silenzio).
3. Ricettività (righe camere: tipologia, quantità, letti, tipo letti,
   bagno; totale posti letto calcolato e correggibile).
4. Spazi di pratica (righe sale con mq, altezza, pavimento, comfort;
   righe spazi esterni).
5. Comfort e servizi (interruttori e tendine).
6. Cucina (regimi a chip).
7. Prezzi (stagioni con date ricorrenti; tariffe per base, camera,
   trattamento; affitto esclusivo; minimi; acconto; cancellazione).
8. Adatta a (chip) ed esperienza ritiri.
9. Contatti e referente.
10. Redazione: stato pipeline, visita, giudizio, punti forti e deboli,
    storia dei contatti con «aggiungi nota», prossimo passo.

Regole di immediatezza: ogni campo ha un'etichetta in italiano e un
esempio; le righe (camere, sale, stagioni) si aggiungono con un
pulsante e si duplicano; niente pagine intermedie; salvataggio per
sezione; la scheda si apre in una pagina intera (`/admin/strutture/{id}`),
non in un modale, perché è lunga.

**Mobile**: Valentina schederà anche dal telefono in visita: form a
una colonna, tap da pollice, salvataggio per sezione.

## 5. Le richieste degli operatori (seconda metà della fase 0)

Nel gestionale del professionista, nella pagina Ritiri, un solo
pulsante: «Cerco una struttura per un ritiro». Apre un modulo breve
(regione o zona, periodo, persone, budget a persona, esigenze) e crea
una `richiesta_struttura` (collezione propria, `organization_id`
dell'operatore, stato: nuova, in_lavorazione, proposta, chiusa).
Email a voi con i dati e link al pannello; tab «Richieste» accanto a
«Strutture» con la lista, lo stato e le strutture che avete
proposto (collegamento richiesta → strutture). L'operatore riceve
un'email di ricevuta e, quando cambiate stato, l'aggiornamento.
È la parte che porta il valore agli operatori e vi dà i numeri per il
cancello della fase 1.

## 6. Isolamento e guardie (`tests/test_strutture_sr.py`)

- Il modello, il repository, il router e il tab sono file nuovi: le
  guardie verificano che **nessun file dei professionisti** importi da
  `strutture` e che `organizations`, `Layout.js` e i menu non cambino
  (diff di stringhe note).
- Le rotte `strutture` e `struttura` sono nel registro, nginx si
  rigenera, `collauda_rotte` le conosce: `struttura` risponde con
  noindex, `strutture` non è ancora servita.
- Lessico: mai «professionista» per una struttura; le etichette delle
  enumerazioni sono italiane e in un solo posto.
- Live sul demo: crea, aggiorna per sezione, foto, filtri combinati
  (regione + posti letto + sala + prezzo), storia contatti, cancella,
  403 per l'admin di organizzazione.
- Parità schema BE↔FE: il form usa le enumerazioni servite dall'API,
  la guardia confronta le liste con il modello.

## 7. Sequenza e stima

| passo | cosa | tempo |
|---|---|---|
| SR0.1 | modello + repository + indici + schema endpoint | mezza giornata |
| SR0.2 | router admin con lista/filtri/facet, CRUD per sezione, foto, storia | mezza giornata |
| SR0.3 | tab Strutture: lista con filtri nell'URL | mezza giornata |
| SR0.4 | scheda a sezioni con salvataggio per sezione, mobile | una giornata |
| SR0.5 | richieste degli operatori: pulsante, collezione, email, tab | mezza giornata |
| SR0.6 | guardie, registro rotte, collaudo live sul demo, screenshot | mezza giornata |
| SR0.7 | seed della Masseria come prima scheda (dati veri dal founder) | con Valentina |

Totale: tre giornate e mezzo di sviluppo, deploy con il go. Nessun
tocco a professionisti, ordini, calendario, Sound, Magazine, Cerchio.

## 8. Cosa serve dal founder prima di partire

- Conferma delle liste chiuse (tipi di struttura, tipologie camera,
  regimi, «adatta a»): sono nel paragrafo 1, si possono allungare
  dopo senza migrazioni.
- I dati della Masseria per la prima scheda (o li compila Valentina
  dal pannello appena è online).
- Il testo dell'email che riceve l'operatore quando manda una
  richiesta: propongo io, tu correggi.
