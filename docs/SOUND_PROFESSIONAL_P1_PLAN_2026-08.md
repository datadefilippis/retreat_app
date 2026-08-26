# Aurya Sound Professional V1 — Protocol Builder
### Piano di architettura · 26 agosto 2026 · IN ATTESA DI APPROVAZIONE

Nessun codice scritto. Il principio guida, verificato sul repo:
**Professional è un layer nuovo sopra ciò che già funziona** — e ciò
che già funziona è molto più di quanto sembrasse.

---

## 1 · STATO ATTUALE (letto, non presunto)

| pezzo | dove | riusabile per Professional |
|---|---|---|
| motore audio | `engine/synth.js` (score→audio), ponte, veglia | ✅ tal quale — INTATTO |
| contratto score | `models/frequency_track.py` v1-v3, `clean_score` | ✅ tal quale: un protocollo COMPILA verso uno score |
| CRUD tracce | `routers/frequencies.py` (create/patch/delete/publish, org-scoped, tetto per-org, gate `require_sound_composer`) | ✅ come **modello da ricalcare**, non da riusare (vedi decisione D1) |
| player condiviso | `esperienze/ascolto.js` | ✅ tal quale per l'esecuzione in sessione |
| registro esperienze | `content/esperienze.js` (CALM, GROUND) | ✅ diventa la sorgente dei protocolli «di sistema» |
| Lab | `lab/` | resta R&D, fuori dal prodotto — INTATTO |
| auth/ruoli | `auth.py` (DB-authoritative, org-scoped) | ✅ tal quale |
| organizzazioni | modello org + flag per-org (`sound_composer` è il precedente) | ✅ stesso pattern: flag `sound_professional` |
| clienti | `models/customer.py`, per-org, GDPR | ✅ tal quale |
| billing | `ModuleSubscription`+`AddonSubscription`+Stripe, `module_access` per `module_key` | ✅ pronto per la fase billing — NON in questo step |
| audit | `models/audit.py` (già usato per Sound) | ✅ tal quale |

---

## 2 · DEFINIZIONE DEL PRODOTTO V1

L'operatore: **crea un protocollo a passi → lo ascolta in anteprima →
lo salva → lo esegue in sessione → aggancia la sessione a un cliente →
ritrova lo storico**. Tutto qui. CALM e GROUND compaiono nella sua
libreria come **protocolli di sistema, in sola lettura, duplicabili**:
il punto di partenza, non nuove esperienze.

Fuori dalla V1, per decisione: billing (fase dopo), libreria condivisa,
CAFL/import, sensori, claim di qualunque tipo.

---

## A · ARCHITETTURA PROPOSTA

```
Aurya account (identità unica esistente)
├── Gestionale (gratuito, com'è)
└── Sound Professional (flag per-org, poi module_key)
    ├── /sound/pro/protocolli     libreria (sistema + propri)
    ├── /sound/pro/protocolli/:id il Builder (sequencer a passi)
    └── /sound/pro/sessioni       esecuzione + storico

frontend: features/frequenze/pro/   (cartella nuova, come lab/ e esperienze/)
backend:  routers/sound_pro.py      (router nuovo)
          models/sound_protocol.py, models/sound_session.py
collezioni: sound_protocols, sound_sessions
```

**D1 — collezione nuova, NON `frequency_tracks` esteso.** La tentazione
era forte (il modello è quasi identico), ma le due entità hanno
pubblico e rischio opposti: le tracce sono contenuto PUBBLICO
(catalogo, pagine /frequenze/:slug, master, sblocchi), i protocolli
sono strumenti PRIVATI adiacenti ai dati dei clienti. Mischiare i due
mondi in una collezione significherebbe che ogni query del catalogo
pubblico è a un filtro sbagliato dalla fuga di dati professionali.
Isolamento = sicurezza; il riuso vero è il contratto (`clean_score`),
il motore e il player — non le righe del CRUD.

**D2 — il Builder è un SEQUENCER A PASSI, non il compositore Crea.**
Crea (FrequenzePage) esiste già e sa fare tutto, ma è costruito per le
meditazioni (basi audio, voce, momenti, pubblicazione): 126 KB di
sorgente col modello mentale sbagliato. Il professionista pensa per
passi — «220 Hz per 3 minuti, pausa 30 s, poi 180 Hz per 5» — e il
passo compila verso lo score (la scoperta della discovery: N passi = N
layer in finestre). Pagina nuova e sottile; il motore per l'anteprima è
quello di sempre.

---

## B · MODELLO DATI

### Protocollo (`sound_protocols`) — CORE V1

```
{ id, organization_id, created_by,             ← multi-tenant esistente
  nome, descrizione,                            ← come le tracce
  steps: [ { metodo: 'tone'|'bin'|'iso'|'drone'|'noise',
             hz,                                ← portante (o battito per bin/iso)
             hz_fine?,                          ← solo bin/iso: f0→f1
             durata_sec, pausa_dopo_sec,
             gain } ],                          ← max 24 (LAYERS_MAX)
  score,                                        ← COMPILATO, validato con clean_score
  durata_sec,                                   ← derivata dagli step
  note_operative,                               ← testo dell'operatore
  stato: 'bozza'|'attivo'|'archiviato',
  visibilita: 'org',                            ← V1: solo privati (system vive nel registro)
  versione: int,                                ← +1 a ogni salvataggio di sostanza
  origine: { tipo: 'proprio'|'duplicato_da_sistema', rif? },
  created_at, updated_at }
```

**FUTURO (non ora)**: tags/categorie, visibilità `shared/library`,
storia completa delle versioni, provenance di fonti esterne, campi
`experimental`. Non si aggiungono campi «perché potrebbero servire».

### Perché lo score sta DENTRO il documento
Le sessioni devono suonare ciò che il protocollo era *quel giorno*: lo
score compilato e validato al salvataggio è la verità esecutiva; gli
`steps` sono la verità editoriale. Il compilatore è una funzione pura
(`steps → score`), testabile a tavolino contro `clean_score`.

## D · MODELLO SESSIONE (`sound_sessions`) — CORE V1

```
{ id, organization_id, operator_user_id,
  customer_id?,                                 ← FK verificata org-scoped (pattern orders)
  protocol_id, protocol_versione,
  score_eseguito,                               ← lo snapshot: com'è suonata DAVVERO
  iniziata_at, durata_prevista_sec, durata_effettiva_sec,
  esito: 'completata'|'interrotta',
  nota_operatore,                               ← testo suo
  riferito_dal_cliente,                         ← parole riportate, dichiarate tali
  created_at }
```

**Campi sensibili segnalati e ESCLUSI dalla V1**: diagnosi, patologie,
parametri fisiologici, qualunque campo che si chiami «risultato/
miglioramento/efficacia». `misurazioni: []` NON si crea finché non
esiste un sensore vero: un campo vuoto col nome giusto è già una
promessa.

---

## C · UX DEL BUILDER (V1)

Una pagina, tre zone, lingua di Aurya (niente DAW):

```
[nome protocollo]                     [stato] [Salva] [Duplica]
────────────────────────────────────────────────────────────────
PASSI                                  TIMELINE (orizzontale,
1  Tono 220 Hz      3:00   ▁▂▃ 25%     proporzionale, generata
   pausa 0:30                          dagli step — sola lettura)
2  Battito 7→6 Hz   4:00   25%
   su tono 330 Hz
[+ aggiungi passo]
────────────────────────────────────────────────────────────────
[▶ Anteprima]  (motore vero via startPreview, con sipario safety)
note operative [textarea]
```

Indispensabile V1: passi (metodo, frequenze, durata, pausa, gain),
riordino, timeline leggibile, anteprima vera, salva/duplica, versione
che avanza. **Rimandato**: drag&drop raffinato, editing sulla timeline,
loop di un passo, condivisione, export, template.

---

## E · INTEGRAZIONE CON AURYA

- **Identità/tenant**: quelli esistenti. Ogni query è
  `organization_id`-scoped; le FK cliente si verificano come negli
  ordini. **Nessun sistema parallelo.**
- **Gate**: `require_sound_professional` ricalcato su
  `require_sound_composer` (flag per-org, acceso da admin, audit già
  esistente). Gestionale gratuito NON toccato: chi non ha il flag non
  vede nulla.
- **Menu**: una voce nel mondo operatore, fuori dal Sound pubblico.
- **CALM/GROUND**: letti dal registro (`content/esperienze.js`) e
  mostrati come «di sistema» — non si copiano in Mongo; «Duplica»
  compila `costruisci()` → steps equivalenti → nuovo protocollo org.

## Commercializzazione futura (concetti da predisporre, zero codice ora)
Il giorno del billing: `module_key = "sound_professional"` in
ModuleSubscription; i limiti (n. protocolli, n. sessioni/mese) passano
da `module_access.get_effective_limit` — il tetto per-org del CRUD
(pattern TRACKS_MAX_PER_ORG) è già il punto dove agganciarli. Il flag
per-org di V1 diventa «entitlement manuale» e poi si sposta sotto il
modulo senza migrazione di dati.

## F · PREPARAZIONE AL BIOFEEDBACK (solo punti d'innesto, zero codice)
1. **Il compilatore** è il punto dove un input fisiologico entrerebbe:
   ricompilare/adattare gli step, MAI toccare il motore.
2. **Il motore è già input-agnostico** (`generatore.imposta`, analisi
   `sorgente(nodo)` nel Lab): un «direttore» adattivo è un chiamante in
   più, non una modifica.
3. **La sessione** ha già il posto concettuale per le serie di misure
   (si aggiungerà `misurazioni` SOLO allora).
4. Nessuna parola della famiglia biofeedback/biorisonanza nel prodotto
   (guardia parametrica già esistente da estendere).

## Sicurezza e privacy (rischi architetturali, mitigazioni V1)
- Le note di sessione POSSONO contenere salute → potenziale dato
  art. 9. V1: accesso org-scoped (c'è), nessuna esposizione pubblica,
  audit sugli accessi admin (c'è), niente export pubblico. Da fare
  presto (P8): finalità dedicata nel consenso cliente, avviso
  nell'interfaccia («non inserire dati sanitari non necessari»).
- La verifica FK cliente↔org è OBBLIGATORIA in ogni endpoint (guardia).
- I protocolli non compaiono MAI in rotte pubbliche/sitemap/shell
  (guardia: la rotta /sound/pro è `app`, noindex, dietro login).

---

## G · ROADMAP P1→P9

| step | obiettivo | file coinvolti | intatto | test/criterio di chiusura |
|---|---|---|---|---|
| **P1** | modello + compilatore | `models/sound_protocol.py`, `pro/compilatore.js` (steps→score) | motore, contratto | il compilatore produce score che `clean_score` accetta SENZA correzioni (guardia sul validatore vero); proprietà: N passi→N layer, pause=buchi |
| **P2** | API CRUD protocolli | `routers/sound_pro.py`, gate `require_sound_professional` | frequencies.py | CRUD org-scoped, tetto per-org, 403 senza flag, audit su create/delete |
| **P3** | Builder (lista+editor) | `features/frequenze/pro/` (pagine nuove), rotta `app` nel registro rotte | Crea, esperienze, Lab | crea/modifica/riordina/salva/duplica dal browser; zero tecnicismi fuori |
| **P4** | anteprima | riuso `startPreview`+sipario | motore | anteprima udibile e stop pulito (misura al ponte come da metodo di casa) |
| **P5** | modello Sessione | `models/sound_session.py` | — | snapshot score+versione; FK cliente verificata |
| **P6** | esecuzione sessione | pagina sessione (riusa `ascolto.js`) | ascolto (o estensione minima dichiarata) | una sessione parte, si interrompe, si completa; esito e durate scritte |
| **P7** | storico | endpoint + vista per cliente | CRM | lo storico di un cliente si legge dal suo profilo; tre voci separate |
| **P8** | permessi+privacy | consenso finalità, avvisi, guardie di isolamento | — | test cross-org (un'org NON legge l'altra), rotte noindex, guardia parole vietate estesa |
| **P9** | polish | copy, mobile, empty states | — | giro completo su mobile 375 senza intoppi |

Ordine motivato dal repo: il compilatore per primo (P1) perché è
l'unica cosa *nuova* davvero — tutto il resto ricalca pattern esistenti
e va costruito sopra un compilatore già provato.

## H · RISCHI E DECISIONI DA PRENDERE (tue)

1. **D1** — collezione separata vs `frequency_tracks` esteso. Io
   propongo separata (isolamento dal pubblico); l'alternativa fa
   risparmiare un CRUD ma lega i protocolli al catalogo.
2. **D2** — sequencer a passi vs riuso del compositore Crea. Io
   propongo il sequencer; riusare Crea sarebbe più rapido ma porta il
   modello mentale delle meditazioni (e 126 KB di storia) dentro il
   prodotto professionale.
3. **D3** — CALM/GROUND «di sistema» letti dal registro (proposta) vs
   copiati in Mongo. La proposta evita la doppia verità.
4. **D4** — quando accendere il flag ai primi operatori: dopo P4
   (builder+anteprima) per un pilota ristretto, o dopo P7 (storico
   completo)? Io direi dopo P4: il feedback sul Builder vale più dello
   storico perfetto.
5. **Rischio principale**: scope creep verso la «app di biorisonanza».
   Mitigazione: le guardie anti-claim si estendono a `pro/` dal P1.
