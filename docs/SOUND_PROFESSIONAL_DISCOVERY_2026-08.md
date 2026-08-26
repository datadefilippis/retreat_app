# Aurya Sound Professional — Product Discovery
### Ricerca, architettura, rischio legale · 26 agosto 2026

Documento di discovery: **nessun file di prodotto è stato modificato**.
Ogni sezione dichiara cosa viene **[FONTE]** (ricerca online o codice
letto) e cosa è **[PROPOSTA]** (giudizio architetturale mio, da
decidere insieme).

---

## A · ARCHITETTURA ATTUALE [FONTE: il repo, letto]

```
FRONTEND (già esistente)
  features/frequenze/
    engine/        motore synth (score → audio), ponte iOS, veglia, render
    lab/           laboratorio (indipendente, 1 rAF)
    content/       protocolli.js (6 preset operatori), calm.js, ground.js,
                   esperienze.js (registro)
    esperienze/    ascolto.js (player condiviso), EsperienzaPage
    FrequenzePage  compositore operatori (gate per-org: sound_composer)
    PublicFrequencyPage  player tracce pubblicate

BACKEND (già esistente — è la scoperta chiave)
  models/frequency_track.py   CONTRATTO score v1-v3, validato (clean_score)
  models/customer.py          clienti per-org (nome, contatti, tags, metadata)
  models/customer_account.py  account del cliente finale
  models/addon_subscription.py + module_subscriptions
      abbonamenti per-org per-modulo con Stripe, e add-on ortogonali;
      module_access.get_effective_limit(org, module, feature)
  models/audit.py + admin_sound.py   audit trail (già usato per il
      privilegio sound_composer)
  auth.py                     ruoli DB-authoritative, require_admin,
                              system_admin, org-scoped
  GDPR                        consensi, export, legal v2.4 — infrastruttura viva
```

**Punti di estensione** (nessuno da inventare):

| serve a Sound Pro | esiste già come |
|---|---|
| abbonamento separato | `ModuleSubscription` (per-modulo, Stripe) — Sound Pro = un nuovo `module_key` |
| feature gating | flag per-org (`sound_composer` è il precedente esatto) + `module_access` |
| clienti | `customers` per-org, già con GDPR |
| storico per cliente | pattern «Passaporto» (servizi ricevuti) già in produzione |
| audit | `models/audit.py`, già usato per Sound |
| suono | il motore, INTATTO: uno score è uno score |

**Verdetto tecnico della sezione**: l'idea è sensata — il backend è già
un gestionale multi-modulo con billing per modulo. Sound Professional è
un modulo nuovo, non un fork.

---

## B · LE FONTI: COSA SONO DAVVERO [FONTE: ricerca web]

### B1 · «Biorisonanza» non è una cosa sola

| categoria | input | misura biologica? | hardware | evidenza |
|---|---|---|---|---|
| A. Rife-style frequency protocols | elenco frequenze | **NO** | generatore/audio | nessuna credibile |
| B. software da practitioner (Bicom, SCIO…) | «scansione» proprietaria | dichiarata, non dimostrata | dispositivo proprietario | nessuna credibile |
| C. sessioni sonore a frequenze | uno score | **NO** | audio | = ciò che Aurya fa oggi |
| D-I. biofeedback vero (HRV, EEG, GSR, respiro…) | **un parametro misurato** | **SÌ** | sensore | reale, per definizione |

**La regola che ne discende** (ed era già nel brief): senza sensore non
si pronuncia mai «biofeedback». Aurya oggi è nella riga C: *frequency-based
audio*. Punto.

### B2 · Le liste di frequenze

**CAFL** (Consolidated Annotated Frequency List, Electroherbalism /
Brian McInturff, consolidata ~2007, versioni successive circolanti):
- struttura: `Condizione_nome — f1, f2, f3, … (note)`; varianti `_1`,
  `_HC` (Hulda Clark), `_TR`; cross-reference («use X», «also see Y»);
  istruzioni temporali sporadiche nelle note; asterischi sulle
  frequenze «principali»; range **0,2 Hz → 11,78 MHz**;
- **licenza: © Electroherbalism, riuso consentito SOLO non commerciale
  con attribuzione** → *incompatibile con un prodotto in abbonamento*;
- indicizzata **per patologia** (cancro, diabete, infezioni…): è
  questo, non le frequenze, il problema legale e di brand;
- evidenza: aneddotica per dichiarazione stessa della fonte.

**ETDFL** (dal 2006, «erede» del CAFL): dichiara che i dati vengono da
«12 cliniche che usano il Quantum SCIO» — un dispositivo il cui
inventore è celebre per frode. Lista commerciale (si vende), quindi non
importabile né legalmente né — soprattutto — *eticamente* per un brand
che ha l'onestà scientifica come patto.

**Hulda Clark**: frequenze nei suoi libri (copyright), range ~30 kHz–900
kHz — quasi tutto **fuori dall'udibile** e fuori da qualunque motore
audio. Storia di enforcement FTC contro il marketing.

**Rife**: le frequenze «originali» (anni '30) sono in gran parte
perdute; le liste moderne sono ricostruzioni. FDA/FTC hanno una storia
lunga di azioni contro dispositivi «Rife» venduti con claim su cancro
(caso BioPulse 2002, e altri). PolitiFact/ACS: nessuna evidenza.

**Bioresonanza commerciale** (Bicom/Regumed, Rayonex, SCIO/QXCI):
Ernst: «non plausibile, non di provata efficacia, potenzialmente
dannosa»; review AIHTA: evidenza assente; **Australia TGA 2020: TUTTI i
dispositivi di biorisonanza cancellati dal registro**. Il Bicom «non è
un dispositivo di biofeedback» (Ernst).

### B3 · Modello astratto del dataset CAFL [PROPOSTA, derivata dalla struttura reale]

Se un giorno si volesse rappresentare *una qualunque* lista (anche solo
quelle scritte dagli operatori), i campi giusti sono:

```
SOURCE      { id, nome, autore, versione/data, licenza, uso_commerciale,
              provenienza_dichiarata, nota_di_evidenza }
ENTRY       { source_id, etichetta, varianti[], cross_refs[], note }
SEQUENCE    { entry_id, steps[] ordinati }
STEP        { hz, durata_sec?, modulazione?, enfasi? }
PROVENANCE  per-step quando la lista mescola fonti (i suffissi _HC/_TR)
EVIDENCE    { grado, dichiarazione della fonte, nostra valutazione }
```

Nota di realtà: nel CAFL la **durata** per frequenza di regola NON c'è
(vive nelle convenzioni dei dispositivi: «3 minuti per frequenza»), le
sequenze sono ordinate ma senza pause esplicite, e molte voci sono
duplicate o storiche. Qualunque importazione richiederebbe cura
manuale voce per voce — un motivo in più per non farla.

---

## C · IL PROTOCOLLO PROFESSIONALE È GIÀ ESPRIMIBILE? [FONTE: contratto letto + PROPOSTA]

Contro il contratto v1 attuale (`models/frequency_track.py`):

| esigenza | esprimibile oggi? | come |
|---|---|---|
| singola frequenza | ✅ | 1 layer `tone` |
| sequenza di frequenze | ✅ | N layer `tone` con finestre `start/end` in fila (il motore già suona layer in sequenza) |
| pausa fra frequenze | ✅ | un buco fra `end` e lo `start` successivo |
| durata per frequenza | ✅ | la finestra del layer |
| ordine preciso | ✅ | le finestre |
| ripetizioni | ✅ | più layer uguali (entro il tetto) |
| multi-step | ✅ | fino a **24 step** (LAYERS_MAX) per score |
| sweep di una portante pura | ⚠️ **NO** | `tone` ha frequenza fissa (verificato nel motore allo STEP 9); f0→f1 muove il *battito*, non la portante |
| range di frequenza | ⚠️ **20–2000 Hz** (CARRIER_MIN/MAX) | il CAFL arriva ai MHz: fuori scala per QUALSIASI sistema audio, non solo nostro |
| durata totale | ⚠️ ≤ 30 min (DURATION_MAX) | per sessioni più lunghe: più score in coda |
| preset/sorgente/note/versione | ✅ ma NON nello score | vivono nel documento **Protocollo** (sotto), che *compila* verso lo score |

**[PROPOSTA] Il Frequency Protocol Engine non è un motore nuovo: è un
COMPILATORE.** `Protocollo (dati professionali) → score v1 → startPreview`.
Zero modifiche a synth.js nella V1. I tre limiti (sweep di portante,
>2000 Hz, >30 min) si dichiarano; se un giorno servissero, sarebbe un
contratto v4 deliberato — mai un aggiramento.

---

## D · ESPERIENZA vs PROTOCOLLO PROFESSIONALE [PROPOSTA]

| | ESPERIENZA (CALM/GROUND) | PROTOCOLLO PROFESSIONALE |
|---|---|---|
| autore | Aurya (curata, misurata) | **l'operatore** |
| pubblico | chiunque | i clienti dell'operatore, in sessione |
| contenuto | arco sonoro progettato | sequenza di step tecnici |
| claim | zero (guardie attive) | **zero da parte di Aurya**; le note dell'operatore sono sue, attribuite a lui |
| dove vive | registro nel codice | **database**, per-org |
| responsabilità | nostra | dell'operatore (stesso patto delle meditazioni pubblicate) |

```
Protocollo {
  id, org_id, created_by, updated_at, versione,
  nome, note_operatore,
  fonte: { tipo: 'proprio' | 'citata', riferimento?, licenza? },
  steps: [ { hz, durata_sec, metodo: 'tone'|…, gain, pausa_dopo_sec? } ],
  compilato_su: score_version,     // la firma del compilatore
  evidence_note,                    // testo LIBERO dell'operatore, mai nostro
  safety_ack: bool                  // l'operatore ha accettato il patto d'uso
}
```

---

## E · SESSIONE E STORICO CLIENTE [PROPOSTA, su modelli esistenti]

```
SessioneSound {
  id, org_id, operator_user_id,
  customer_id?,                 // aggancio al CRM esistente (opzionale: sessioni di gruppo)
  protocol_id + protocol_versione,   // COSA era il protocollo QUEL giorno
  parametri_effettivi,          // lo score compilato, com'è stato suonato davvero
  started_at, durata_effettiva, esito: 'completata'|'interrotta',
  // LE TRE VOCI SEPARATE, mai mescolate:
  nota_operatore,               // testo dell'operatore
  riferito_dal_cliente,         // parole riportate, dichiarate come tali
  misurazioni: []               // VUOTO in V1 — si riempie solo con sensori veri
}
```

Lo storico per cliente è lo stesso pattern del «Passaporto» già in
produzione. **Regola dura**: nessun campo si chiama «miglioramento»,
«risultato», «efficacia». La struttura stessa impedisce di registrare
un'opinione come un fatto.

**GDPR [FONTE: infrastruttura esistente + normativa]**: appena una nota
di sessione tocca lo stato di salute, è **dato particolare (art. 9)** —
serve consenso esplicito del cliente per quella finalità, registrato;
la Svizzera (nLPD) è allineata. L'infrastruttura consensi di Aurya c'è
già; va aggiunta la finalità specifica.

---

## F · BIOFEEDBACK FUTURO [FONTE: ricerca API/hardware + PROPOSTA]

| sensore | via browser? | precisione | costo | primo candidato? |
|---|---|---|---|---|
| **Fascia cardiaca BLE** (Polar H10 e simili) | Web Bluetooth: Chrome/Edge/Android **sì**, **Safari/iOS NO** (Apple ha dichiarato di non volerlo) | ottima (RR per HRV) | ~90€ | **SÌ** |
| Camera PPG (polpastrello) | getUserMedia ovunque | discreta per HR, debole per HRV | zero | seconda scelta |
| Respiro (fascia) | BLE, pochi standard | buona | ~50-150€ | dopo |
| GSR/EDA | quasi solo hardware proprietario | variabile | medio | no |
| Pulsossimetro BLE | GATT standard esiste, supporto irregolare | buona per SpO2 | ~30-80€ | no |
| EEG consumer (Muse…) | SDK nativi, non web | bassa fuori dal lab | 250€+ | no |

Il loop vero — sensore → metrica → adattamento del protocollo → audio →
nuova metrica — è **tecnicamente fattibile oggi** solo su
desktop/Android via Web Bluetooth con una fascia cardiaca. Su iPhone
servirebbe un'app nativa: un altro prodotto.

**[PROPOSTA]** Fase 6, non prima; primo sensore la fascia BLE (HR/HRV);
e finché non c'è, la parola «biofeedback» non compare da nessuna parte
— c'è già una guardia parametrica che vieta claim, vi si aggiunge
«biofeedback» e «biorisonanza».

---

## G · ARCHITETTURA ISOLATA MA INTEGRATA [PROPOSTA]

```
AURYA CORE (gratuito)
├── gestionale (clienti, calendario, ordini, GDPR)
└── AURYA SOUND
    ├── pubblico: biblioteca, Lab, CALM, GROUND     [resta gratuito]
    ├── operatori: compositore meditazioni          [resta com'è, gate sound_composer]
    └── PROFESSIONAL (modulo a pagamento)           [NUOVO]
        ├── Sequencer (protocolli → compilatore → motore esistente)
        ├── Libreria protocolli PER-ORG (mai spedita da Aurya con patologie)
        ├── Sessioni + storico cliente (CRM esistente)
        └── [fase 6] strato sensori
```

Compatibilità col backend attuale: **già pronta**. `module_key =
"sound_professional"` in ModuleSubscription; gating via il pattern
`sound_composer`; nessuna entità «SoundWorkspace» nuova — l'org È il
workspace. Identità: quella esistente (porta unica /accedi).

---

## H · MODELLO DI BUSINESS [PROPOSTA, struttura non prezzi]

- **Aurya gratis** = gestionale + Sound pubblico (com'è oggi).
- **Sound Professional** = abbonamento **per organizzazione** (il
  pattern billing esistente), con posti operatore come add-on
  (AddonSubscription è nato per questo).
- Incluso: sequencer, protocolli propri illimitati (o a tetto alto),
  sessioni + storico, export.
- Mai incluso, a nessun prezzo: una libreria patologia→frequenze
  spedita da noi.
- Estensioni future a pagamento: posti aggiuntivi, [fase 6] modulo
  sensori.
- Nota di coerenza con il piano strategico: «si regala l'informazione,
  si fa pagare la trasformazione» — qui: si regala l'ascolto, si fa
  pagare lo *strumento di lavoro*.

---

## I · RISCHIO LEGALE / CLAIM [FONTE dove indicato, il resto PROPOSTA di condotta]

1. **[FONTE] EU MDR 2017/745 + MDCG 2019-11**: un software è
   dispositivo medico se ha *destinazione d'uso medica* (diagnosi,
   terapia…). Software con finalità esclusivamente wellness/lifestyle
   **non** è MDSW. La Svizzera (MedDO/Swissmedic) è allineata.
   → La linea che non va MAI attraversata: **associare frequenze a
   patologie in contenuti nostri o nel marketing**. È esattamente ciò
   che farebbe scattare la qualificazione (e per un software
   terapeutico la Rule 11 parte da classe IIa: marcatura CE, QMS,
   documentazione clinica — un altro mestiere).
2. **[FONTE] Enforcement**: FTC contro dispositivi Rife con claim
   oncologici; TGA australiana ha cancellato tutti i dispositivi di
   biorisonanza. Il pattern colpito è sempre lo stesso: *dispositivo +
   claim su malattie*.
3. **Parole vietate nel prodotto e nel marketing**: biorisonanza,
   biofeedback (finché non c'è un sensore), terapia, trattamento,
   diagnosi, cura, guarigione, «efficace contro», nomi di patologie.
   Terminologia proposta: **«strumento professionale per sessioni
   sonore», «protocolli sonori/frequenziali», «sequencer di
   frequenze», «diario delle sessioni»**.
4. **Contenuti degli operatori**: l'operatore può scrivere le sue note
   nei SUOI protocolli (posizione da piattaforma, come per le
   meditazioni: contenuto suo, responsabilità sua, attribuzione
   chiara + patto d'uso accettato con `safety_ack`). Aurya non
   suggerisce, non autocompleta, non fornisce template con patologie.
5. **Privacy**: note su clienti = potenziali dati art. 9 → finalità
   dedicata nel consenso, cifratura in transito già in essere, accesso
   org-scoped già in essere, audit già in essere.
6. **Il quadro svizzero degli operatori** (RME/ASCA, registri dei
   terapeuti complementari) è un mondo di *qualifiche dei praticanti*,
   non del software: non ci riguarda direttamente, ma è il contesto
   dei nostri clienti — molti sono registrati e hanno LORO vincoli
   deontologici. Uno strumento sobrio li protegge.

---

## J · AURYA SOUND PROFESSIONAL 1.0 [PROPOSTA]

1. **Cosa fa**: permette a un operatore di comporre protocolli sonori
   a passi (frequenza, durata, pausa, volume), suonarli in sessione
   dal proprio dispositivo, e tenere il diario delle sessioni
   collegato ai clienti del gestionale.
2. **Chi lo usa**: operatori olistici già su Aurya (sound healing,
   campane, meditazione, discipline energetiche).
3. **Cosa serve**: un account Aurya, l'abbonamento del modulo, un
   impianto audio decente.
4. **In sessione**: sceglie il protocollo, vede i passi e il tempo,
   avvia/pausa/termina; volume; nessun dato del cliente a schermo se
   proietta.
5. **Cosa registra**: protocollo+versione, score effettivo, tempi,
   esito, le tre note separate (operatore / riferito dal cliente /
   misurazioni vuote).
6. **Cosa vede il cliente**: nulla di tecnico; eventualmente una
   schermata quieta stile esperienze.
7. **Nel gestionale**: il cliente, il suo storico, il consenso.
8. **Nell'abbonamento**: sequencer + libreria propria + sessioni +
   storico + export.
9. **Cosa NON fa**: non diagnostica, non tratta, non suggerisce
   frequenze per patologie, non spedisce CAFL/ETDFL, non parla di
   biofeedback/biorisonanza, non promette esiti.
10. **Tecnologie**: motore synth esistente, contratto v1, compilatore
    protocollo→score, moduli billing esistenti.
11. **Protocolli supportati**: sequenze fino a 24 passi, 20–2000 Hz,
    fino a 30 min per blocco (limiti del contratto, dichiarati).
12. **Fonti integrabili legalmente**: SOLO contenuto scritto
    dall'operatore. CAFL no (non-commerciale). ETDFL no (commerciale
    di terzi, e provenienza SCIO). Frequenze *tecniche* nostre senza
    riferimenti a condizioni: sì.
13. **Sensori nella V1**: nessuno.

---

## K · ROADMAP [PROPOSTA]

| fase | obiettivo | dentro | FUORI | rischio | conclusa quando |
|---|---|---|---|---|---|
| **0** | validare la domanda + perimetro legale | interviste ai 4 operatori live + Valentina; questo documento; parole vietate in guardia | qualunque codice | costruire ciò che nessuno compra | ≥1 operatore dice «lo userei in sessione, pagando» e sappiamo cosa intende |
| **1** | Professional Sequencer | compilatore protocollo→score; player sessione (riusa ascolto/motore); flag per-org spento di default | libreria spedita, billing, storico | scope creep verso la «app biorisonanza» | un pilota reale conduce una sessione vera |
| **2** | libreria per-org | CRUD protocolli, versioni, duplica | qualunque contenuto nostro con patologie | — | l'operatore pilota gestisce i suoi protocolli da solo |
| **3** | sessioni + storico | modello sessione, aggancio customers, consenso art. 9, export | misurazioni | privacy | lo storico di un cliente pilota è consultabile e esportabile |
| **4** | billing | module_key + prezzo + gating | — | — | primo franco/euro incassato dal modulo |
| **5** | integrazione piena gestionale | storico nel profilo cliente, calendario | — | — | l'operatore non cambia contesto |
| **6** | sensori | fascia BLE (HR/HRV), Chrome/Android; SOLO qui la parola «biofeedback» | EEG, GSR, iOS nativo | med-device creep | un loop misura→audio→misura dimostrato su un pilota |

---

## L · VERDETTO

**L'idea regge, ma il prodotto giusto non è quello che il mercato
«bioresonance» suggerisce.** Le fondamenta tecniche ci sono già tutte
(motore, contratto, billing per modulo, CRM, GDPR, audit): Sound
Professional è un modulo, non un fork — costruirlo è un lavoro di
settimane, non di mesi.

Ma le fonti sono state chiare tre volte: il CAFL è vietato all'uso
commerciale, l'ETDFL nasce da un dispositivo screditato, e ovunque i
regolatori sono intervenuti il bersaglio era sempre lo stesso —
*frequenze + claim su malattie*. Quella riga per Aurya è doppiamente
invalicabile: legalmente (MDR/MedDO) e per il patto di onestà che è il
brand (le guardie anti-claim che abbiamo scritto negli ultimi step
fallirebbero — giustamente — al primo tentativo).

**Cosa costruire per primo: niente. Prima si valida.** Fase 0: parlare
con i quattro operatori live e con Valentina — «useresti in sessione
uno strumento così? cosa dovrebbe fare? pagheresti?» — con un mock, non
con codice. È la lezione già scritta nel piano strategico di casa:
*validare prima di costruire*. Se la risposta è sì, la Fase 1 (il
sequencer) parte su fondamenta che esistono già.

---

### Fonti principali
- Electroherbalism — CAFL: https://www.electroherbalism.com/Bioelectronics/FrequenciesandAnecdotes/CAFL.htm (termini: © non-commerciale con attribuzione, dichiarati sul sito)
- ETDFL, about: https://etdfl.com/about-us/ (provenienza dichiarata: «12 cliniche con Quantum SCIO»)
- MDCG 2019-11 (qualificazione software MDR/IVDR): https://health.ec.europa.eu/system/files/2020-09/md_mdcg_2019_11_guidance_en_0.pdf
- Swissmedic, scheda Medical Device Software (MedDO)
- FTC v. BioPulse (2002): https://www.ftc.gov/news-events/news/press-releases/2002/07/company-touting-unproven-cancer-treatment-agrees-settle-ftc-charges
- PolitiFact sui «Rife machines» (2022): https://www.politifact.com/factchecks/2022/jul/29/viral-image/there-no-evidence-vibrational-frequencies-rife-mac/
- E. Ernst, Australia cancella i dispositivi di biorisonanza (TGA, 2020): https://edzardernst.com/2020/05/australia-cancels-all-bioresonance-devices/
- AIHTA, review biorisonanza: https://eprints.aihta.at/842/2/DSD_Nr.031.pdf
- Web Bluetooth, stato 2026 (Safari/iOS assente): https://codecrispi.es/blog/web-bluetooth-2026/
