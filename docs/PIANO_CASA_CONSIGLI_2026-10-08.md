# La casa delle meditazioni: il motore dei consigli (lotto «CS»)

8/10/2026, sera. Il founder: «con una meditazione sola la casa la ripete
in sette righe: fuorviante e brutto. Voglio un sistema intelligente, non
banale, senza ridondanze. È il miglior meccanismo possibile? Approfondisci».

## 0. Cosa c'è oggi, e perché non basta
La casa è una **lista di liste**: Vetrina, Riprendi, Recenti, Preferite,
Per iniziare, Novità, Le più ascoltate, una riga per categoria, Con la
voce, Solo suono. Ogni riga filtra lo stesso catalogo per conto suo: con
pochi titoli si ripetono, con molti titoli dicono cose ovvie («Novità» =
l'ordine di pubblicazione, «Le più ascoltate» = la vetrina che ha più
ascolti perché è in vetrina). Non c'è un'idea di **persona** né di
**momento**: la stessa casa alle 7 e alle 23, per chi ascolta ogni sera e
per chi entra la prima volta.

Una regola «niente doppioni + soglie» (la prima proposta) toglie il brutto
ma non aggiunge intelligenza. Il meccanismo giusto per un catalogo che va
da 1 a qualche decina di titoli, con poche persone, **non è il machine
learning**: è un **motore a segnali, deterministico e spiegabile**, che
compone la casa come una playlist personale del giorno. Il filtraggio
collaborativo («chi ha ascoltato X ascolta Y») ha senso solo con centinaia
di ascolti incrociati: si aggiunge come segnale quando i numeri ci sono,
senza cambiare l'impianto.

## 1. I segnali che abbiamo già (nessun backend nuovo per la v1)
| Della meditazione | Della persona (account) | Del contesto |
|---|---|---|
| `categoria`, `intent` (dormire · meditare · rilassare · concentrare · elaborare · energizzare), `momento` (mattina · pausa · sera · notte), `tags`, `duration_sec`, `has_voce`, `published_at`, `plays_total`, `in_vetrina` | `sound_riprendi` (slug, secondo), `sound_recenti` (20 slug), preferite (tracce e playlist), gli **eventi** `sound_ascolti` (play, quartili, fine; `at`, `slug`, `provenienza`, playlist) | l'ora e il giorno; per chi non ha l'account, i recenti nel browser |

Dagli eventi si ricavano, per persona, tre cose che oggi non usiamo: **a
che ora ascolta** (l'abitudine), **cosa porta a termine** (il completamento
per traccia), **quanto dura** in media un suo ascolto. Il backend le
riassume in `GET /platform/me` (tre campi in più, calcolati dagli eventi):
nessuna raccolta nuova.

## 2. Il motore: una casa composta, non filtrata

### 2.1 Un solo bacino, una carta una volta
Tutto parte da un **bacino** (le meditazioni pubblicate). Le sezioni
pescano dal bacino in ordine; **ogni carta, una volta sola**: quando una
sezione la prende, le altre non la vedono più. L'unica eccezione è la
vetrina, che è il manifesto del giorno. Una sezione compare solo se ha
**almeno 3 carte** dopo la deduplica (2 per «Il tuo spazio»). Così la
ridondanza sparisce per costruzione, non per soglia.

### 2.2 Il punteggio di ogni meditazione, per questa persona, adesso
`punteggio(t) = momento + affinità + continuità + scoperta + popolarità + novità − stanchezza`
- **momento** (0–3): il `momento` della traccia coincide con la fascia
  dell'ora (mattina 5–11, pausa 11–17, sera 17–22, notte 22–5), **oppure**
  con l'abitudine della persona (se ascolta di solito la sera, la sera
  pesa anche di giorno). L'`intent` aiuta: *dormire* la notte, *energizzare*
  la mattina, *concentrare* nella pausa.
- **affinità** (0–3): la categoria e l'intent sono fra quelli che la
  persona ha ascoltato o salvato; la durata è vicina alla sua durata
  media di ascolto.
- **continuità** (0–4): c'è un punto da cui riprendere; oppure è la
  prossima in una playlist che stava ascoltando; oppure è una preferita
  non ascoltata da più di 7 giorni.
- **scoperta** (0–2): non l'ha mai ascoltata; bonus se è di una categoria
  che non ha ancora provato (si allarga l'orizzonte, non si chiude).
- **popolarità** (0–2): media bayesiana degli ascolti (`(plays + m·μ) /
  (n + m)`): con un ascolto solo non vince nessuno, con cento sì.
- **novità** (0–2): decadimento sulla data di pubblicazione (piena per 14
  giorni, zero dopo 90).
- **stanchezza** (−3…0): l'ha ascoltata ieri o oggi; l'ha portata a fine
  tre volte nell'ultima settimana (la conosce: non serve proporla).

I pesi stanno in **una tabella** (`casa/consigli.js`), con un test che li
pinza: si regolano a mano guardando i numeri, non a caso.

### 2.3 Le sezioni, nell'ordine in cui si pescano
1. **Di oggi** (la vetrina): come oggi, a rotazione fra le «in vetrina».
2. **Riprendi** (continuità ≥ 4): una carta grande, solo se c'è.
3. **Per questo momento**: le 3–6 col punteggio più alto, con la riga del
   perché («È sera: tre meditazioni per lasciare andare», «Di solito
   ascolti di notte»). È la riga che cambia ogni volta che torni.
4. **Da scoprire**: quelle mai ascoltate, in ordine di affinità e poi di
   popolarità; per chi è nuovo, è il catalogo ordinato bene.
5. **Le tue preferite** e **Playlist salvate**: solo con l'account, solo se
   non sono già uscite sopra.
6. **Le categorie**: una riga per categoria, solo con ≥ 3 carte residue.
7. **Tutte le meditazioni**: la griglia completa, sempre in fondo (è la
   mappa). Con **≤ 5 meditazioni** le righe 3–6 non compaiono: vetrina,
   Riprendi se c'è, e la griglia. La casa cresce col catalogo.
8. Playlist e Percorsi come oggi (righe proprie, se esistono).
- Via «Ascolti recenti» come riga: i recenti sono un segnale (affinità e
  stanchezza), non una vetrina di ciò che già conosci. Via «Novità» e «Le
  più ascoltate» come righe: sono due termini del punteggio.
- Via «Con la voce» e «Solo suono» (righe e filtri).

### 2.4 Il perché, sempre scritto
Ogni sezione personale ha una riga che dice il motivo (`perche`): «È
mattina», «Perché hai salvato Respiro profondo», «Non l'hai ancora
ascoltata». Un consiglio spiegato è un consiglio di cui ci si fida; e
rende i pesi controllabili a occhio.

### 2.5 Chi non ha l'account
Stessa macchina con meno segnali: ora del giorno, recenti e riprendi nel
browser (già c'è `localStorage`), nessuna abitudine. La casa resta
sensata al primo ingresso: vetrina, «Per questo momento» (solo momento +
popolarità + novità), «Da scoprire» = tutto, griglia.

## 3. I filtri (quello che hai chiesto)
- **Categorie**: solo quelle con almeno una meditazione pubblicata (già
  così; si blinda con un test).
- **Via** «Con la voce» e «Solo suono».
- **Durata** separata, un livello sotto le categorie: tre pastiglie
  piccole (≤ 10 · 10–20 · 20+), grigie, che compaiono solo se nel catalogo
  ci sono durate di fasce diverse. Si combinano con la categoria.
- La ricerca per testo resta (titolo, tema, chi guida, tag).

## 4. Fase 2 (quando i numeri ci sono, ≥ 20 titoli e qualche centinaio di ascolti)
- **Co-ascolto**: dagli eventi, «chi ha finito X ha finito anche Y» (matrice
  di co-occorrenza calcolata una volta al giorno nel backend, letta come
  segnale «affine» nel punteggio). Nessun modello, una tabella.
- **Completamento** come qualità: una traccia che la gente porta a fine
  pesa più di una che apre e chiude.
- **A/B sui pesi**: due tabelle, metà persone l'una metà l'altra, si
  misura il completamento. Solo quando ci sono abbastanza persone.

## 4b. La regia degli ascolti (system admin → Sound → «Ascolti»)
Il founder (8/10 sera): «per ogni utente quali registrazioni ascolta,
quante volte, quando, se la completa, per quanti minuti; uno score di chi
segue di più; chi aggiunge ai preferiti: uno strumento completo per
monitorare meditazioni, ascolti e preferenze».

Gli eventi ci sono già (`sound_ascolti`: `account_id`, `slug`, `track_id`,
`evento` play · quartile · fine, `secondo`, `at`, `provenienza`, `playlist`)
più i preferiti (`frequency_favorites`) e il profilo (`sound_recenti`,
`sound_riprendi`). La regia li **legge e riassume**: nessuna raccolta nuova,
un indice in più (`account_id`, `at`).

### Le quattro viste
1. **Panoramica** (periodo: 7 · 30 · 90 giorni · tutto): ascolti, persone
   attive, minuti ascoltati, completamento medio, nuovi ascoltatori,
   preferiti aggiunti; un grafico a giorni e uno a fasce d'ora (quando si
   ascolta).
2. **Per meditazione**: tabella con ascolti, persone uniche, minuti,
   completamento (fine ÷ play), punto medio di abbandono (il quartile in
   cui si esce), preferiti, momento di punta, provenienza (casa, vetrina,
   email, playlist, link riservato). Ordinabile; clic → la scheda con la
   curva di abbandono ai quattro quarti e l'elenco delle persone.
3. **Per persona**: tabella con nome ed email, primo e ultimo ascolto,
   ascolti, minuti, completamenti, titoli diversi, preferite, fascia d'ora
   abituale, e lo **score «seguito»** (0–100). Clic → la linea del tempo:
   data e ora, meditazione, da dove, minuti, completata o no, con i
   preferiti e il «riprendi» aperto.
4. **Esporta CSV** di ogni tabella (per lavorarci fuori).

### Lo score «seguito» (0–100), spiegato riga per riga
`seguito = 30·frequenza + 20·costanza + 25·profondità + 15·ampiezza + 10·affetto`
- **frequenza**: giorni con almeno un ascolto negli ultimi 30 (÷ 30, tetto 1 a 12 giorni);
- **costanza**: settimane consecutive con un ascolto (÷ 8);
- **profondità**: completamenti ÷ ascolti;
- **ampiezza**: titoli diversi ÷ titoli in catalogo;
- **affetto**: preferite e playlist salvate (÷ 5).
La formula sta in `services/ascolti_regia.py` con un test che la pinza; i
pesi si regolano a mano. Accanto allo score, le cinque componenti: lo
score non è un numero magico, è una somma leggibile.

### Backend
`routers/admin_sound_ascolti.py` (solo system admin): `GET /admin/sound/
ascolti/panoramica?periodo=`, `/meditazioni`, `/meditazioni/{slug}`,
`/persone`, `/persone/{account_id}`, `/export.csv?vista=`. Aggregazioni
sugli eventi (sono pochi: si calcolano a richiesta; se un giorno sono
milioni, si materializza una volta al giorno). Una sessione = un `play`;
i minuti = il `secondo` più alto raggiunto in quella sessione.

### Privacy (va fatto insieme, non dopo)
- Sono dati personali di comportamento: l'informativa (legal v2.5) li
  nomina («ascolti e preferenze, per consigliarti e per capire cosa
  funziona»), con conservazione **24 mesi** e cancellazione automatica.
- **Esportazione e cancellazione** dell'account includono gli eventi
  (`sound_ascolti`), i recenti, il riprendi e i preferiti (oggi il GDPR
  della piattaforma copre il profilo: si estende).
- Chi ascolta col Cerchio **senza account** resta anonimo: entra solo nei
  totali per meditazione, mai in «Per persona».
- Lo score serve alla regia e al motore dei consigli; non si mostra mai
  alla persona né agli operatori.

## 4c. Stato (8/10 sera, «procediamo»)
- **CS0–CS3 FATTI** (commit `c6f47469`): `casa/consigli.js` (PESI, SOGLIE,
  `punteggio`, `componiCasa`, `persona`), la casa dietro `CASA_CONSIGLI`
  (sezioni col perché, «Le altre» = le residue, la mappa dietro «Tutte le
  meditazioni · N», con un titolo solo una carta sola), filtri (categorie
  popolate, durata un livello sotto solo se serve, via la voce),
  `sound_abitudine` in `/platform/me` da `services/ascolti_regia.abitudine`
  (fuso di Roma), indice `(account_id, at)`, guardie che girano sul JS vero.
- **CS4 FATTO**: `routers/admin_sound_ascolti.py` (panoramica, meditazioni,
  dettaglio con curva di abbandono, persone con score e cinque parti,
  dettaglio con linea del tempo, CSV; solo system admin) +
  `SoundAscoltiSezione.jsx` in Regia → Sound. Score pinzato
  (`PESI_SEGUITO`, `TETTI_SEGUITO`). Verificato nel browser e dal vivo.
- **CS5 FATTO in parte**: export dell'account con `sound` (ascolti,
  preferite, recenti, riprendi), cancellazione che toglie ascolti e
  preferiti, conservazione 24 mesi (`conserva()` all'avvio +
  `scripts/ascolti_conservazione.py`), gli anonimi solo nei totali.
  **DA DECIDERE col founder**: la riga nell'informativa (7-quater, 24 mesi)
  cambia la versione legale (`CURRENT_VERSION_HASH`, hash dei testi) e
  chiede un nuovo consenso a chi ha già accettato: non si fa senza il suo ok.

## 5. Cosa NON cambia
Il lettore in casa, le card, i cuori, le playlist, i percorsi, la soglia
del Cerchio, i testid letti dai test (`casa-riprendi`, `casa-preferite`,
`casa-filtro-*`, `casa-tutte-*`); le righe che spariscono restano nel
codice dietro il flag finché non si pota. Nessuna raccolta nuova nel
database: tre campi riassunti in `/platform/me`.

## 6. Lotti
| Lotto | Cosa | Giorni |
|---|---|---|
| CS0 | `casa/consigli.js`: bacino, punteggio, sezioni con deduplica e soglie, «perché»; la casa lo usa dietro `CASA_CONSIGLI` | 1 |
| CS1 | filtri: via voce, durata un livello sotto e solo se serve, categorie solo popolate (test) | ½ |
| CS2 | `/platform/me`: fascia d'ora abituale, durata media, completamenti per slug (dagli eventi, senza raccolte nuove) | ½ |
| CS3 | guardie `tests/test_casa_consigli.py` con scenari: 1 titolo, 4 titoli, 12 titoli, persona nuova, persona abituale, notte | ½ |
| CS4 | la regia degli ascolti: backend `admin_sound_ascolti` + `services/ascolti_regia.py` (score), sezione «Ascolti» in Regia → Sound (panoramica, per meditazione, per persona con linea del tempo, CSV), guardie | 1,5 |
| CS5 | privacy: informativa v2.5, export e cancellazione account con gli ascolti, conservazione 24 mesi (job notturno), anonimato del Cerchio | ½ |

Totale ≈ 4,5 giorni; nessun deploy senza «go». Ordine: CS1 (filtri) → CS0 (motore) → CS2 → CS3 → CS4 → CS5 prima del deploy di CS4.
