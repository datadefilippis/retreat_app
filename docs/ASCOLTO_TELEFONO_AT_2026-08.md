# L'ascolto dal telefono — ciclo AT (21 agosto 2026)

Due segnalazioni del founder, la stessa radice: **il telefono non è un
desktop con lo schermo piccolo**.

1. *«da telefono le frequenze non si sentono; con le cuffie sì»* — e
   l'avviso esistente non si capiva quando serviva;
2. *«se il telefono va in blocco schermo, il suono si interrompe»*.

## I fatti fisici e di piattaforma (non aggirabili)

| fatto | conseguenza |
|---|---|
| l'altoparlante di un telefono non riproduce quasi nulla sotto i ~500 Hz | **27 schede su 32** hanno il tono lì sotto: play → silenzio |
| il web **non può sapere** se le cuffie sono collegate (privacy) | non si può avvisare «solo chi ne ha bisogno»: si sceglie *quando* e *su cosa* |
| i browser mobili **sospendono WebAudio** in background | la sintesi dal vivo muore al blocco schermo, per regola loro |
| un **media element che riproduce un file** sopravvive al blocco | è come suona un lettore musicale: quella è la porta |

## AT1 — L'avviso cuffie, nel momento giusto

Prima: una riga passiva nella striscia delle controindicazioni, in
cima alla pagina — un cartello all'ingresso, sparito dalla vista quando
premi play. Ora:

- **una sola verità** in `engine/altoparlante.js`: la frequenza
  *dominante* (la portante, non il battito) decide; `noise` è banda
  larga e non avvisa mai — un falso allarme insegna a ignorare quelli
  veri;
- l'avviso compare **al play**, **solo su telefono** (la stessa media
  query di `.solo-telefono`: una sola definizione di «telefono»), e
  nomina **il numero vero**: *«110 Hz non esce dall'altoparlante del
  telefono: servono le cuffie.»*;
- sulla pagina pubblica il messaggio distingue il caso subdolo: voce e
  basi si sentono, le frequenze mancano in silenzio;
- coerenza dei testi (regola del founder: il testo dice quello che il
  codice fa): sul telefono la riga di metodo «🔊 Anche in
  altoparlante» — vera sul metodo, falsa sul dispositivo — diventa
  «🎧 Dal telefono: solo in cuffia» per le schede sotto soglia.

## AT2 — Lo schermo non si spegne da solo (`engine/veglia.js`)

Screen Wake Lock mentre qualcosa suona dal vivo (schede, linea del
tempo, pagina pubblica in modalità viva). Contratto: **un interruttore
derivato dallo stato** («qualcosa suona sì/no», via useEffect), non
conteggi sparsi nei punti di stop. Il lock si auto-rilascia in
background: al ritorno visibile si riprende. Dove l'API non c'è
(Safari vecchi), il modulo tace.

Copre il caso più frequente (lo schermo che si oscura da solo), non il
blocco volontario: per quello c'è AT3.

## AT3 — L'ascolto continuo (`engine/continuo.js`)

La sessione si **renderizza in un file** (con `renderPcm`, che già
esisteva per l'export dell'operatore) e si riproduce con `<audio>` +
**Media Session**: il suono continua a schermo bloccato, con titolo,
copertina e play/pausa/seek sulla schermata di blocco.

Le scelte, e il loro perché:

| scelta | perché |
|---|---|
| WAV, non MP3 | lamejs su un telefono comprime a pochi multipli del tempo reale: minuti d'attesa in più. Il WAV è pronto appena renderizzato |
| 22050 Hz | metà tempo e metà memoria; la portante massima del catalogo è 963 Hz (armoniche ~2,9 kHz), la voce sta sotto gli 8 kHz. Prezzo: un po' d'aria in meno sulle basi naturali — dichiarato |
| tetto 30 minuti | ~158 MB di WAV: il massimo che un telefono regge. Oltre, il pulsante non compare — un limite onesto batte un crash a metà notte |
| si prepara con un tocco | il render dura secondi/minuti (progresso visibile): è una scelta dell'utente, non un'attesa imposta a chi voleva solo l'anteprima |
| **solo a sblocco avvenuto** | un file intero in mano a chi ha i 90 secondi d'anteprima sarebbe il cancello demolito da un'altra porta |
| eventi → stato | play/pausa arrivano anche dalla schermata di blocco: la pagina si sincronizza dagli eventi dell'elemento, mai supponendo di essere l'unica a comandare |

Misura reale in locale: la traccia da 20 minuti con due livelli neuro
si prepara in pochi secondi su desktop (su telefono: decine di
secondi, con il progresso in vista).

**Fuori scope, con motivo**: le schede della biblioteca restano solo
dal vivo (sono loop infiniti: un file non li rappresenta, e il Wake
Lock le copre); niente MediaSource/streaming a pezzi (fragile su iOS,
non necessario sotto il tetto dei 30 minuti).

## Guardie

`backend/tests/test_ascolto_telefono.py` (18): soglia in un posto solo,
avviso al play e solo su telefono, una sola media query «telefono»,
niente falsi allarmi sul rumore, riga di metodo device-aware, wake lock
derivato dallo stato + feature-detect + riaggancio, cancello sovrano
sul continuo, sipario anche sulla preparazione, riuso del render
dell'export, limiti 22050/30min, Media Session completa, revoke del
blob, un solo caricamento basi.

## Debito dichiarato

- L'«app vera» (PWA/wrapper) resta la risposta definitiva al telefono:
  analisi in `docs/APP_SUL_TELEFONO_ANALISI_2026-08.md`;
- se un giorno serviranno sessioni continue oltre i 30 minuti, la
  strada è lo streaming a pezzi (ManagedMediaSource) — da non aprire
  di corsa.
