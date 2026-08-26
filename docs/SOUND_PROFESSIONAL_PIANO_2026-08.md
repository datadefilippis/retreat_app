# Aurya Sound Professional — il piano (26/8/2026)

*Esito dell'audit strategico del 26/8 (due giri: architettura, poi
prodotto+biofeedback, con ricerca). Questo documento è la direzione;
le decisioni fini restano nei brief dei singoli step.*

## Cosa stiamo costruendo

**Il registro professionale delle sessioni sonore.** L'operatore
sceglie un protocollo curato, lo esegue con un cliente, e Aurya
ricorda cosa, con chi, e com'è andata. Non un editor (ne esistono già
due: Crea per comporre, il sequencer P2 per i protocolli a passi), non
una macchina terapeutica, non biorisonanza senza definizione.

La frase da cui non si esce: **l'operatore sceglie, non compone.**
Chi vuole comporre ha Crea; chi vuole il sequencer ce l'ha come porta
avanzata. Il prodotto è la scelta + l'esecuzione + la memoria.

## I tre ruoli (confermati dall'audit)

- **Crea** — lo studio: comporre meditazioni/tracce complete (voce,
  basi, visual, publish). Separato, non si tocca, non fa da backend.
- **Lab** — il banco: strumento interno per progettare e misurare.
  È con il Lab che NOI progettiamo i protocolli del catalogo.
- **Sound Professional** — il quaderno: catalogo curato, protocolli
  propri versionati (P2), sessioni, storico. Org-scoped, privato.

## La roadmap (S0–S9)

| step | cosa | stato |
|---|---|---|
| S0 | Potatura: scarto P4 parziale, /sound/pro → catalogo (non editor) | ✅ 26/8 |
| S1 | Catalogo Aurya Core: schede oneste (origine, evidenza, limiti) su ricette ESISTENTI | ✅ 26/8 |
| S2 | `sound_sessions`: entità sessione, snapshot score, org/customer/booking | — |
| S3 | Il rito: pre (1-10) → ascolto (player condiviso) → post (1-10 + nota) | — |
| S4 | Storico per cliente + riepilogo org | — |
| S5 | Gating commerciale: `module_key: sound_professional` (billing già multi-modulo) | — |
| S6 | Pilot: 4 operatori, 10 sessioni vere, prezzo validato | — |
| S7 | Sensore: fascia BLE (Polar H10) via Web Bluetooth, SOLO osservazione | — |
| S8 | Metriche oneste: RMSSD a finestre + scarto artefatti (matematica pura, testata in Node) | — |
| S9 | Biofeedback deterministico: regole nei protocolli, azioni via primitive del motore | — |

## Decisioni prese (con le fonti nell'audit in chat, 26/8)

- **Primo sensore: HR/HRV via fascia toracica BLE** (Polar H10 ≈ ECG a
  riposo). Web Bluetooth su Chrome/desktop/Android; iOS non lo
  supporta — il dispositivo di sessione è il laptop/tablet
  dell'operatore, limite dichiarato.
- **Primo caso d'uso biofeedback: respirazione guidata dal suono**
  (~6 respiri/min; il metodo `breath` del motore è già un pacer).
  Prima si osserva (S7), poi si adatta con regole deterministiche
  (S9): sensore → metrica → regola → azione prevista dal protocollo.
  MAI: sensore → AI → cambio arbitrario.
- **Regolatorio: general wellness.** Rilassamento/gestione dello
  stress senza claim di malattia. Le guardie sulle parole vietate si
  estendono al catalogo. La destinazione d'uso dichiarata decide il
  confine MDR: resta benessere.
- **Adattività**: le regole sono DATI del protocollo, versionate e
  snapshottate come lo score. Il motore non sa che esistono sensori;
  le azioni passano solo dalle primitive live (`setLayerGain`; il
  giorno di S9 servirà `setLayerBeat` — unica modifica al motore
  prevista, piccola e dichiarata).
- **Misure in collezione separata**, mai dentro la sessione; niente
  dati sanitari, niente diagnosi; il feedback 1-10 è un vissuto
  soggettivo, non una misura clinica.

## Il catalogo (S1, fatto)

`pro/catalogo.js` — dati React-free sul pattern del registry. AVVOLGE
le ricette esistenti, non le copia: CALM/GROUND da
`content/esperienze.js`, i sei protocolli per intento da
`content/protocolli.js` (coi gradi B/C e le note del founder,
verbatim). Ogni scheda dichiara: origine (`benessere` |
`letteratura`), evidenza (grado, nota INTERA con i punti deboli, data
revisione), indicazioni d'uso, cuffie (necessarie/consigliate),
durata, livello. Le controindicazioni restano il testo unico di
`content/safety.js`.

Due scaffali: **Catalogo Aurya** (questo file, contenuto nostro in
git) e **I tuoi protocolli** (`sound_protocols`, P2, privati per org
con versioni e audit). Un terzo scaffale futuro (fonti esterne
revisionate) è previsto ma NON si importa niente senza revisione —
CAFL e simili restano fuori (discovery 26/8).

## MVP vendibile (le 12 cose)

1. Catalogo con 8-10 protocolli e schede oneste ✅ (8)
2. Scheda che risponde a «cosa succederà» ✅
3. Avvio con sipario e avviso cuffie (S3)
4. Ascolto affidabile 10-30′ (player condiviso, esiste)
5. Interruzione onesta, anche `onPerso` (S3)
6. Feedback pre/post 1-10 + nota (S3)
7. Sessione legata al cliente del CRM (S2)
8. Storico per cliente (S4)
9. Protocolli propri versionati ✅ (P2)
10. Snapshot immutabile dell'eseguito ✅ (P2, esteso in S2)
11. Gate per-org ✅ (flag) → modulo (S5)
12. Zero claim, guardie automatiche ✅ (estese al catalogo in S1)
