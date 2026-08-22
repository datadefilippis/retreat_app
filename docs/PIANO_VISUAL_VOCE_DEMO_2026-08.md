# Piano — La voce dentro il visual: mix, stili, demo (22/8/2026)

Richieste del founder, testando /sound/visual dal telefono:

1. traccia caricata E microfono INSIEME, che coesistono;
2. per la voce registrata: scegliere lo stile come in Crea (Naturale,
   Sogno, Tempio, Sussurro), RIASCOLTARE prima di scaricare, poter
   CAMBIARE stile (es. da Sogno a Sussurro) e solo dopo scaricare;
3. alcune musiche ambiente già caricate in Sound disponibili come DEMO
   dentro /sound/visual;
4. (fix già fatto, `c7ee2742`) il video usciva più chiaro e meno
   immersivo del sito — era la scala delle particelle.

## Il vincolo che decide l'architettura

«Cambiare stile e solo dopo scaricare» esclude di cuocere lo stile
dentro il video: un mp4 congela l'audio, e ricucirlo dopo vorrebbe
dire re-encoding con perdita o un muxer esterno (dipendenza nuova,
WebCodecs non ovunque). La via giusta è tenere la voce CRUDA finché
si sceglie, e far nascere il video già giusto.

## MX — le sorgenti coesistono

Oggi `attivaMic()` e `caricaFile()` si spengono a vicenda
(`disconnect()`). Diventano indipendenti:

- mic → analyser E traccia → analyser insieme: la scena danza sul MIX,
  e l'export (che spilla dall'analyser) registra il mix. La strada
  audio c'è già — cambia solo chi si collega.
- la traccia continua a passare da analyser → destination (si sente);
  il mic NON va mai a destination (feedback). In cuffia l'utente sente
  la traccia; la sua voce la sente… dalla sua bocca.
- UI: le due voci del pannello Sorgente diventano interruttori
  indipendenti; l'etichetta in alto dice cosa è vivo («Mic + nome
  traccia»).

## VX — la voce col suo stile (il flusso del take)

1. **Registra la voce**: con la traccia che suona, un tasto avvia il
   take — il mic registra la voce CRUDA (resta sul dispositivo,
   come tutto). Timer visibile, stop manuale.
2. **Riascolta e scegli lo stile**: a fine take appare il leggio
   piccolo: play/pausa del mix (traccia + voce), selettore
   Naturale / Sogno / Tempio / Sussurro — gli stessi preset di Crea,
   motore `engine/voicefx.js` riusato pari pari (`buildVoiceChain` è
   WebAudio puro, zero DOM). La voce è cruda: cambi stile e riascolti
   SUBITO, senza rifare niente. «Rifai il take» se la voce non piace.
3. **Esporta video**: solo quando lo stile convince. Si suona il mix
   definitivo dall'inizio e si registra col motore EX esistente — la
   scena reagisce all'audio FINALE (voce stilizzata inclusa), una sola
   generazione di encoding, zero remux. Durata = la traccia (o il
   take, se più lungo).
4. La pulizia voce di Crea (`cleanVoiceBuffer`: silenzi, rumore) si
   applica al take appena chiuso, come nel leggio.

Guardie: il take non lascia mai il dispositivo (niente rete nel
modulo); i 4 preset restano il gemello di VOICE_FX backend; lo stile
si applica al PLAYBACK, mai inciso nel take.

## DM — le demo ambient

- Endpoint pubblico `GET /api/public/visual-demos`: 4–6 basi ambient
  curate a mano dal catalogo di piattaforma (marea, bordone, drone,
  pioggia…), con nome umano e `stream_url` (`/uploads/audio/{id}`,
  già servito da nginx — ES1, zero costi nuovi).
- Nel pannello Sorgente: «Prova con una musica di Aurya» — righe
  cliccabili, stesso percorso della traccia caricata (player.src).
  Utile anche come materiale per il flusso voce (parla sopra la demo).
- Verifica licenze: solo basi di piattaforma già pubbliche sul sito.

## Ordine e verifica

MX (piccolo) → DM (piccolo) → VX (il grosso). Ogni pezzo: prova viva
nel browser + guardie in test_aurya_mode.py. iOS resta l'unico giudice
per il percorso audio (il take passa da getUserMedia + MediaRecorder
audio: collaudo su iPhone del founder prima di dichiararlo fatto).
