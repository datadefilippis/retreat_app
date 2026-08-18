# Frequenze by Aurya — piano di integrazione (agosto 2026)

Origine: prototipo standalone del founder (`aurya-frequenze.html`, 18/8) — un
compositore di sessioni vibrazionali: livelli di entrainment (binaurale,
isocronico, monoaurale, bilaterale, soffio, tono puro) su una linea del tempo
con fasi, protocolli pronti, base musicale caricabile, ascolto live WebAudio e
export WAV/MP3 offline (lamejs incorporato). Analisi approvata dal founder il
18/8: si integra in Aurya come modulo **isolato ma integrato**.

## Il principio architetturale: si pubblica la RICETTA, non l'audio

Una traccia pubblicata è un **documento JSON di pochi KB** (lo "score"):
livelli, curve, tempi, volumi, fasi, più un riferimento alla base musicale.
Chi ascolta non scarica un file: il player pubblico ricostruisce la sessione
col motore WebAudio sul dispositivo, come il tasto «Ascolta sessione» del
prototipo. Conseguenze:

- storage ~zero (1.000 tracce ≈ pochi MB in Mongo, per sempre);
- banda solo per la base musicale (condivisibile tra tracce);
- le tracce restano modificabili dopo la pubblicazione;
- il costo CPU della sintesi sta sul client, mai sul server.

L'export MP3 (20 min a 320kbps ≈ 45MB) resta una funzione per l'operatore
(aula, uso personale), MAI il formato di pubblicazione.

## Dati

### `frequency_tracks`
```
id, organization_id, title, description, intent (slug protocollo o null),
status: draft | published (published da FQ1),
slug (pubblico, da FQ1), base_asset_id (da FQ2, null prima),
score: {
  score_version: 1,          # contratto versionato dal giorno uno
  duration_sec, fade_in_sec, fade_out_sec,
  layers: [{ id, kind: "neuro", name, method: bin|iso|mono|bil|noise|tone,
             timbre: pure|warm, carrier, f0, f1, curve: lin|exp|steps,
             start, end, gain, breath, mute }],
  phases: [{ t, name }],
},
plays_total (da FQ1), created_at, updated_at
```
Limiti di validazione (clean_score): durata 60–7200s, max 24 livelli,
gain 0–1, battiti 0.2–60 Hz (bil 0.2–3), portante 20–2000 Hz, fasi max 12.
`score_version` permette di evolvere il formato senza rompere le tracce
esistenti: mai riusare la v1 con semantiche diverse.

### `audio_assets` (da FQ2)
```
id, owner: "platform" | organization_id, category (Ambient|Droni|Campane|
Natura|Ritmi|Voce), title, duration_sec, size_bytes, mime, stream_url,
license_note, created_at
```
I byte audio NON vanno in Mongo. Fase 1: `uploads/audio/` su VPS servito da
nginx con Range + cache immutable (48GB liberi ≈ ~1.500 basi da 30MB).
Fase 2 (a crescita): Bunny Storage + CDN (già in ecosistema: la CSP ammette
iframe.mediadelivery.net). L'API espone sempre `stream_url`: il passaggio a
CDN è un cambio di URL, non di schema. Limite upload 60MB, formati mp3/m4a,
quota per-org quando l'upload si apre agli operatori.

**Legale**: basi della libreria curata solo licenziate o CC0; per gli upload
operatori clausola di responsabilità diritti nei Patti chiari.

## Isolamento

- Backend: `models/frequency_track.py` + `routers/frequencies.py` — nessuna
  modifica a collections esistenti. Da FQ1 cittadinanza modulo: chiave
  `frequencies` in MODULE_OWNERSHIP + provisioning MD1 (in FQ0 il gate è
  auth+org, il modulo dedicato entra con la prima superficie pubblica).
- Frontend: `features/frequenze/` chunk lazy; dentro, `engine/` è JS puro
  senza dipendenze React/DOM (testabile, riusabile dal player pubblico).
  lamejs vive SOLO in quel chunk: il bundle principale non cresce.
- Metriche: da FQ1 riuso page_views/VT con content_type dedicato.
- Se un giorno le tracce si vendono: diventano un item_type come gli altri.

## Superfici e gate (da FQ1)

- Pagina pubblica `/frequenze/:slug` + blocco sulla pagina link (/@slug) e
  sul profilo operatore.
- Cancello d'ascolto: anteprima libera 60–90s; ascolto completo con account
  Aurya (ciclo AP) **oppure** iscrizione Lettera (ciclo NW) → le tracce sono
  il lead magnet della Lettera.
- Disclaimer: mantenere i gradi A/B/C e le note di onestà del prototipo
  (EMDR, «valore simbolico»), più disclaimer salute standard sulla pagina
  pubblica. Coerente col brand «ci si fida di qualcuno».

## Fasi

- **FQ0** (questo ciclo): estrazione motore + contenuti, schema score v1,
  CRUD bozze org-scoped dietro login, compositore React a `/frequenze`
  (protocolli, editor livelli, ascolto, salvataggio bozze, export locale).
  La base musicale caricata resta locale alla sessione (non persistita).
  La timeline drag del prototipo arriva come FQ0.5 (l'editing numerico
  entra/esce copre già il flusso).
- **FQ1**: publish + slug, pagina pubblica con player e gate, contatori in
  Visibilità, modulo `frequencies` nel registry.
- **FQ2**: libreria basi curata (upload admin → uploads/audio con Range,
  categorie), le basi entrano nel compositore e nello score come
  `base_asset_id`; mondo «Suoni» del prototipo smette di essere segnaposto.
- **FQ3**: upload basi per operatori con quote; eventuale leva Pro sulla
  pubblicazione (decidere sull'uso reale).

## Il prototipo

`aurya-frequenze.html` resta il laboratorio personale del founder: utile per
sperimentare, mai deployato. Il motore è stato estratto fedelmente (matematica
delle curve, sintesi analitica campione-per-campione per il render, grafo
WebAudio per l'anteprima); la UI si riscrive in React col design system
dell'app. L'estetica scura del prototipo è un altro registro rispetto a
Salvia & Terracotta: da riconciliare in FQ0.5 (opzione: «modalità studio»
dedicata alla pagina compositore).
