# Piano: la durata onesta, il visual mobile, l'export video

**Data**: 22 agosto 2026 · **Stato**: piano, in attesa del «procedi»
**Tre richieste founder**: (1) durata — tetto 30 vero, bug del popup da
telefono, e il default nascosto che inganna; (2) `/sound/visual`
ottimizzato mobile come lo studio in Crea; (3) l'export video
YouTube/Instagram, locale e a costo zero, per chiudere il prodotto.

---

## CICLO DU — La durata onesta

### I tre difetti, verificati nel codice

1. **Il tetto è finto**: `onDurationChange` non clampa a 30 — clampa
   solo il valore derivato che va al motore. Risultato: a schermo 35,
   il motore suona 30. Un'interfaccia che mente.
2. **Il popup a metà digitazione** (il bug da telefono): il campo fa
   `onChange` A OGNI CIFRA. Digiti «3» di «35» → durata 3 min → parte
   subito il dialogo «Durata cambiata: riadatto le tracce?» sopra la
   tastiera. Da mobile è ingestibile.
3. **Il default nascosto** (il difetto più profondo): la sessione
   nasce a 20 minuti, scritti in un campo chiuso dietro un toggle.
   L'utente monta 5 minuti di tracce, lavora sul suo range, pubblica —
   e si ritrova 15 minuti di loop che non ha mai voluto. Il default
   decide al posto suo, in silenzio.

### La proposta: la durata è AUTO finché l'autore non la vuole

Il principio (lo stesso di tutto il ciclo: zero opzioni superflue, il
sistema accompagna): **di default la sessione dura quanto il suo
contenuto**. Non c'è più un numero arbitrario da scoprire.

- **Modalità AUTO (default)**: durata = fine dell'ultima traccia,
  aggiornata in diretta. La pill in barra la dice sempre, in chiaro:
  `⏱ 5:00 · segue le tracce`. Aggiungi una traccia che finisce a 8:00
  → la pill diventa 8:00. Nessun popup di adattamento: non c'è nulla
  da adattare, è la durata che segue le tracce e non il contrario.
- **Modalità FISSA (un tocco sulla pill)**: si apre un foglio
  (mobile-first) con preset rapidi `5 · 10 · 15 · 20 · 30` + campo
  minuti con stepper. Scegliere = fissare: la pill diventa
  `⏱ 20:00 · impostata` e le basi in loop riempiono fino a lì —
  stavolta per scelta dichiarata, non per caso.
- **Il commit è al rilascio, mai per cifra**: il campo applica su
  blur/invio/stepper. Il dialogo «riadatto le tracce?» può apparire
  SOLO a commit avvenuto, e solo se la nuova durata taglia tracce
  esistenti (riduzione sotto l'end di qualcuno).
- **Il tetto 30 è vero e spiegato, ovunque**:
  - pill/foglio: impossibile fissare oltre 30; a chi prova: «Il
    massimo è 30 minuti: è il limite dell'ascolto a schermo bloccato,
    così nessuna sessione pubblicata ne resta esclusa»;
  - pannello della traccia: end oltre la durata → messaggio chiaro
    (oggi viene clampato in silenzio o lasciato incoerente);
  - il server già clampa (DURATION_MAX=1800): resta l'ultima rete.
- **Migrazione dolce**: le bozze esistenti hanno una durata salvata →
  si aprono in modalità FISSA col loro valore (nessun cambiamento a
  sorpresa). Solo le sessioni NUOVE nascono in AUTO.

Casi al margine, decisi ora:
- sessione vuota in AUTO: la pill dice `⏱ — · si adatta alle tracce`;
- sola registrazione voce: vale come traccia (l'end dello spezzone);
- passaggio FISSA→AUTO: un'azione «torna automatica» nel foglio;
- fade-out: resta agganciato alla fine effettiva, qualunque essa sia.

### Onde
- **DU1 (subito, è un bug)**: commit differito + clamp vero a 30 con
  messaggio + niente popup mid-digitazione. Consegnabile da solo.
- **DU2**: la durata AUTO + pill + foglio; via il campo dal toggle.
- **DU3**: messaggi di tetto nel pannello traccia; coerenza fasi.
- **DU4**: guardie (tetto UI+modello, commit-on-blur, auto-default) e
  verifica vera da telefono.

---

## CICLO VM — /sound/visual mobile come lo studio

Lo studio in Crea ha già la grammatica mobile giusta (fogli dal basso
62dvh, chip `◈ Preset / ☼ Regola`, X sulla tendina, tap sulla scena =
chiudi, safe-area, modebar scorrevole). La pagina strumento pubblica
`/sound/visual` — stesso prototipo, stessa classe CSS di base — oggi su
telefono ha ancora i pannelli fissi da 438px.

- **VM1**: portare la modalità-fogli anche allo strumento. Differenza
  UNICA rispetto allo studio: qui le SORGENTI (microfono / carica
  traccia) sono vive — restano nel foglio sinistro, in cima; niente
  chip «Fatto» (non c'è una sessione a cui tornare: il marchio riporta
  a /sound come oggi). Riuso dei CSS `.studio` con una classe gemella:
  zero secondo binario di stili.
- **VM2**: verifica su telefono vero (portrait/landscape, gate,
  tastiera 1-9 irrilevante su touch, drag&drop assente su mobile →
  il pulsante «carica» resta la via) + rifiniture.

---

## CICLO EX — L'export video (il pezzo che chiude il prodotto)

Obiettivo: dall'esperienza in `/sound/visual` (microfono o traccia
caricata) l'utente REGISTRA la scena e la porta via come video, in due
formati: **YouTube 16:9 (1920×1080)** e **Instagram 9:16 (1080×1920)**.
Tutto SUL DISPOSITIVO: zero upload, zero costi server, la promessa
privacy del gate resta intatta («il tuo audio non viene caricato da
nessuna parte» — e nemmeno il tuo video).

### Architettura (tutta client)
- video: `canvas.captureStream(30)` dal canvas WebGL;
- audio: il ramo è già nel grafo — mic o traccia passano
  dall'analizzatore; si aggiunge un nodo `MediaStreamDestination`
  dedicato alla registrazione (il monitor in cuffia non cambia);
- muxing: `MediaRecorder` sul MediaStream combinato (video+audio).

### Le scelte tecniche dichiarate (con i loro compromessi)
1. **Formato file**: si preferisce `video/mp4` (H.264+AAC) dove il
   browser lo registra nativamente — Safari/iOS sì, Chrome recenti sì;
   dove manca, fallback `webm` CON AVVISO onesto («per Instagram
   potrebbe servire una conversione»). NIENTE transcodifica client
   (ffmpeg.wasm = megabyte e minuti): meglio un file nativo subito.
2. **WYSIWYG di formato**: scegliendo 16:9 o 9:16 la scena si
   RIDIMENSIONA a quella proporzione già in anteprima (letterbox a
   schermo): quello che vedi è il quadro che registri. Il renderer
   passa alla risoluzione target (1080p) per la durata della
   registrazione, poi torna alla qualità scelta.
3. **Il flusso**: scegli formato → countdown 3s → REC (pallino
   discreto + durata) → stop (o fine traccia: auto-stop) → il file si
   scarica (su iOS: foglio di condivisione). Durante la REC: qualità e
   dimensioni bloccate, wake lock attivo.
4. **Consumo**: 1080p30 a ~10 Mbps ≈ 75 MB/min — dichiarato accanto al
   pulsante («~75 MB al minuto»). Tetto di sicurezza: 10 minuti per
   registrazione (limite RAM del blob su telefono), dichiarato.
5. **Watermark**: DA DECIDERE (founder) — una firma «Aurya» discreta
   nell'angolo renderebbe ogni video condiviso pubblicità del brand.
   Tecnicamente è un sprite nel canvas: costo zero. Proposta: sì,
   piccola, angolo basso-destra, rimovibile in futuro per account Pro.

### Onde
- **EX1**: motore di registrazione (captureStream + MediaRecorder,
  rilevamento mp4/webm, stream audio dedicato) — invisibile in UI.
- **EX2**: i due formati con anteprima WYSIWYG (resize del renderer,
  letterbox, ritorno pulito).
- **EX3**: UI export nello strumento (sezione «Esporta» nel pannello
  sinistro + versione nei fogli mobile), countdown/REC/stop, download
  e share-sheet iOS, tetto e stima MB dichiarati.
- **EX4**: verifica multipiattaforma (iPhone Safari/Brave, Android
  Chrome, desktop), guardie (mai upload: nessuna fetch col blob;
  formato preferito mp4; wake lock rilasciato), e la decisione
  watermark applicata.

---

## Ordine proposto e dipendenze

1. **DU1** subito (bug attivo che morde da telefono);
2. **DU2-DU4** (la durata onesta completa);
3. **VM1-VM2** (mobile dello strumento — breve: riusa lo studio);
4. **EX1-EX4** (l'export, il blocco più nuovo).

Domande aperte per il founder:
- watermark «Aurya» sui video esportati: sì/no?
- il default AUTO per le sessioni nuove convince? (le bozze esistenti
  non cambiano comunque);
- preset durate nel foglio: bastano 5·10·15·20·30?
