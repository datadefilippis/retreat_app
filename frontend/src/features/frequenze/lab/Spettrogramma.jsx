/**
 * SPETTROGRAMMA — lo spettro che scorre nel tempo (STEP 4, 26/8/2026).
 *
 * Terzo pannello con lo stesso identico contratto: importa React e il
 * quadro, riceve `ottieniAnalisi`, non conosce il generatore, non
 * possiede nodi audio, non ha un ciclo suo. Il motore non e' stato
 * toccato: `analisi.spettro()` e `hzPerBin` bastavano.
 *
 * X = tempo, Y = frequenza, luminosita' = energia. Una frequenza
 * ferma e' una riga orizzontale; un glissando e' una diagonale; le
 * armoniche sono righe parallele; il silenzio e' buio.
 *
 * TRE SCELTE, e il perche':
 *
 * 1. LE COLONNE VANNO A TEMPO, NON A FOTOGRAMMA. Una colonna ogni 40
 *    ms: cosi' l'asse X e' davvero un tempo (e la finestra si puo'
 *    dichiarare in secondi) invece di dipendere da quanti fotogrammi
 *    riesce a fare il dispositivo. Su un telefono lento l'immagine
 *    rallenta, non mente.
 *
 * 2. SI SCORRE, NON SI RIDISEGNA. Ogni colonna nuova entra a destra e
 *    la storia trasla a sinistra con un solo `drawImage` della tela su
 *    se stessa. Ridisegnare tutta la storia a ogni fotogramma
 *    vorrebbe dire tenerla in memoria e ricalcolarla: qui la memoria
 *    E' l'immagine.
 *
 * 3. LA COLONNA SI COSTRUISCE PER PIXEL, NON PER BIN — la stessa
 *    regola dello Spettro, per la stessa ragione: sull'asse
 *    logaritmico una riga di schermo puo' valere meno di un bin (in
 *    basso) o decine (in alto). Si prende il MASSIMO dei bin che le
 *    competono, cosi' una riga sottile non sparisce.
 *
 * La mappa delle frequenze e la finestra in dB sono le STESSE dello
 * Spettro (20 Hz → Nyquist in log10, −96 → 0 dBFS): i due pannelli
 * devono potersi leggere insieme. Sono ricopiate qui invece di essere
 * importate — i pannelli non si conoscono fra loro — e una guardia le
 * tiene gemelle.
 */
import React, { useEffect, useRef, useState } from 'react';
import { iscrivi } from './quadro';

const F_MIN = 20;               // come nello Spettro
const DB_MIN = -96, DB_MAX = 0; // come nello Spettro (dBFS)
const MS_COLONNA = 40;          // 25 colonne al secondo
const MAX_COLONNE = 6;          // dopo una pausa non si recupera all'infinito
const GUTTER = 30;              // la striscia delle etichette, che non scorre

/* la scala d'intensita': buio → acqua → crema. Una sola famiglia di
   colori, nessun arcobaleno. La gamma scurisce la parte bassa, cosi'
   le code di dispersione non diventano foschia. */
function rampa(t, ink, water, bone) {
  const u = Math.pow(Math.max(0, Math.min(1, t)), 1.5);
  const [a, b, q] = u < 0.62
    ? [ink, water, u / 0.62]
    : [water, bone, (u - 0.62) / 0.38];
  return [
    (a[0] + (b[0] - a[0]) * q) | 0,
    (a[1] + (b[1] - a[1]) * q) | 0,
    (a[2] + (b[2] - a[2]) * q) | 0,
  ];
}

const rgb = (css, fallback) => {
  const m = String(css).trim().match(/^#([0-9a-f]{6})$/i);
  if (!m) return fallback;
  const n = parseInt(m[1], 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
};

export default function Spettrogramma({ ottieniAnalisi, fermo }) {
  const telaRef = useRef(null);
  const [finestra, setFinestra] = useState(null);   // secondi di storia a schermo

  useEffect(() => {
    const tela = telaRef.current;
    const c2d = tela.getContext('2d');
    let tinte = null, passo = 1, colonna = null, debito = 0, ultimo = 0;
    const fMaxRef = { current: 0 };
    const db = { buf: null };

    /* ALLESTIRE e SVUOTARE sono due cose diverse — distinguerle e' la
     * cura di un difetto latente trovato leggendo (26/8): tinte,
     * passo e colonna nascevano solo dentro lo svuotamento, che gira
     * SOLO al cambio di misura. Se il pittore si ri-iscriveva senza
     * che la tela cambiasse (basta un re-render della pagina), il
     * disegno ripartiva senza colori e moriva alla prima riga — in
     * silenzio, perche' il quadro non fa cadere il banco per un
     * pittore rotto. Ora l'allestimento si rifa' quando serve, e la
     * storia sopravvive. */
    const allestisci = (W, H, dpr) => {
      const s = getComputedStyle(tela);
      tinte = {
        ink: rgb(s.getPropertyValue('--ink'), [12, 22, 24]),
        water: rgb(s.getPropertyValue('--water'), [102, 183, 156]),
        bone: rgb(s.getPropertyValue('--bone'), [233, 228, 217]),
        linea: s.getPropertyValue('--line-soft').trim() || '#1B2E32',
        nota: s.getPropertyValue('--dimmer').trim() || '#86A0A4',
        fermo: s.getPropertyValue('--lamp').trim() || '#C9B37E',
      };
      passo = Math.max(1, Math.round(dpr));
      colonna = c2d.createImageData(passo, H);
      c2d.imageSmoothingEnabled = false;             // traslazione netta
      const utili = W - GUTTER * dpr;
      setFinestra(Math.round((utili / passo) * MS_COLONNA / 100) / 10);
    };

    /* la tela cambiata di misura si svuota: la storia riparte da qui.
       E' il prezzo onesto dello scorrimento — l'immagine E' la
       memoria, e la memoria non si stira. */
    const svuota = (W, H) => {
      c2d.fillStyle = `rgb(${tinte.ink.join(',')})`;
      c2d.fillRect(0, 0, W, H);
      debito = 0; ultimo = 0;
    };

    const etichette = (W, H, dpr) => {
      const g = GUTTER * dpr;
      c2d.fillStyle = `rgb(${tinte.ink.join(',')})`;
      c2d.fillRect(0, 0, g, H);
      c2d.strokeStyle = tinte.linea;
      c2d.lineWidth = 1;
      c2d.beginPath(); c2d.moveTo(g + 0.5, 0); c2d.lineTo(g + 0.5, H); c2d.stroke();
      c2d.fillStyle = tinte.nota;
      c2d.font = `${Math.round(9 * dpr)}px ui-monospace, Menlo, monospace`;
      c2d.textAlign = 'right'; c2d.textBaseline = 'middle';
      const fMax = fMaxRef.current || 22050;
      const lo = Math.log10(F_MIN), hi = Math.log10(fMax);
      [100, 1000, 10000].forEach((hz) => {
        if (hz > fMax) return;
        const y = H - ((Math.log10(hz) - lo) / (hi - lo)) * H;
        c2d.fillText(hz >= 1000 ? `${hz / 1000}k` : `${hz}`, g - 5 * dpr,
          Math.max(6 * dpr, Math.min(H - 6 * dpr, y)));
        c2d.strokeStyle = tinte.linea;
        c2d.beginPath();
        c2d.moveTo(g - 3 * dpr, Math.round(y) + 0.5);
        c2d.lineTo(g, Math.round(y) + 0.5);
        c2d.stroke();
      });
    };

    const dipingi = (fermo) => {
      const dpr = window.devicePixelRatio || 1;
      const W = Math.round(tela.clientWidth * dpr);
      const H = Math.round(tela.clientHeight * dpr);
      if (!W || !H) return;
      if (tela.width !== W || tela.height !== H) {
        tela.width = W; tela.height = H;
        allestisci(W, H, dpr);
        svuota(W, H);
      } else if (!tinte) {
        allestisci(W, H, dpr);        // ri-iscritto: si riprende, non si cancella
      }
      if (fermo) return;                             // fermo: la storia non avanza

      const analisi = ottieniAnalisi();
      if (!analisi) return;
      const N = analisi.analyser.frequencyBinCount;
      if (!db.buf || db.buf.length !== N) db.buf = new Float32Array(N);
      fMaxRef.current = analisi.analyser.context.sampleRate / 2;

      /* quante colonne deve il tempo trascorso */
      const ora = performance.now();
      if (!ultimo) { ultimo = ora; etichette(W, H, dpr); return; }
      debito += (ora - ultimo) / MS_COLONNA;
      ultimo = ora;
      let quante = Math.floor(debito);
      if (quante < 1) return;
      debito -= quante;
      quante = Math.min(quante, MAX_COLONNE);

      analisi.spettro(db.buf);
      const hzBin = analisi.hzPerBin;
      const fMax = fMaxRef.current;
      const lo = Math.log10(F_MIN), hi = Math.log10(fMax);
      const hzDaY = (y) => Math.pow(10, lo + ((H - y) / H) * (hi - lo));

      /* la colonna: per ogni riga il MASSIMO dei bin che le competono */
      const px = colonna.data;
      for (let y = 0; y < H; y++) {
        const f0 = hzDaY(y + 0.5), f1 = hzDaY(y - 0.5);
        let k0 = Math.floor(f0 / hzBin), k1 = Math.ceil(f1 / hzBin);
        if (k1 <= k0) k1 = k0 + 1;
        k0 = Math.max(0, Math.min(k0, N - 1));
        k1 = Math.max(k0 + 1, Math.min(k1, N));
        let v = -Infinity;
        for (let k = k0; k < k1; k++) if (db.buf[k] > v) v = db.buf[k];
        const [r, g, b] = rampa((v - DB_MIN) / (DB_MAX - DB_MIN),
          tinte.ink, tinte.water, tinte.bone);
        for (let i = 0; i < passo; i++) {
          const o = (y * passo + i) * 4;
          px[o] = r; px[o + 1] = g; px[o + 2] = b; px[o + 3] = 255;
        }
      }

      /* si trasla SOLO la parte a destra del gutter, cosi' le
         etichette restano ferme e leggibili */
      const g = GUTTER * dpr;
      const largo = quante * passo;
      const utile = W - g;
      if (utile > largo) {
        c2d.drawImage(tela, g + largo, 0, utile - largo, H, g, 0, utile - largo, H);
      }
      for (let n = 0; n < quante; n++) {
        c2d.putImageData(colonna, W - (n + 1) * passo, 0);
      }
      etichette(W, H, dpr);
    };

    return iscrivi(dipingi);
  }, [ottieniAnalisi]);

  return (
    <section className="lab-card lab-scope" data-testid="lab-spettrogramma">
      <div className="lab-chead">
        <h2>Spettrogramma</h2>
        <span className="lab-cnote">lo spettro che scorre: il tempo va a destra</span>
      </div>
      <canvas ref={telaRef} className="lab-tela lab-tela-alta" role="img"
        aria-label="Spettrogramma: le frequenze del segnale nel tempo" />
      <div className="lab-scope-info">
        <span>frequenza in verticale · log</span>
        <span data-testid="lab-finestra">
          {fermo ? 'immagine ferma — il suono continua'
            : finestra ? `finestra ${String(finestra).replace('.', ',')} s` : ''}
        </span>
        <span>più chiaro = più energia</span>
      </div>
    </section>
  );
}
