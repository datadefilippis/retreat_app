/* Diagnosi del suono (22/8/2026) — quattro canali, un rapporto.
   File separato perche' la CSP di produzione vieta gli script inline.
   Ogni test suona 2 secondi a 440 Hz (o un file) e registra TUTTO:
   lo stato del contesto, il livello che l'analizzatore misura (se >0
   il grafo PRODUCE suono: se non lo senti, muore all'uscita), gli
   errori. Il rapporto si copia e si incolla in chat. */
(function () {
  'use strict';
  var rapporto = {
    quando: new Date().toISOString(),
    ua: navigator.userAgent,
    audioSessionAPI: !!navigator.audioSession,
    audioSessionType: navigator.audioSession ? navigator.audioSession.type : null,
    test: {},
  };
  var ctx = null;

  function stato(t) { document.getElementById('stato').textContent = t; }
  function scrivi(id, oggetto, ok) {
    var el = document.getElementById(id);
    el.textContent = JSON.stringify(oggetto, null, 1);
    el.className = 'esito ' + (ok ? 'ok' : 'no');
  }
  function contesto() {
    if (!ctx) ctx = new (window.AudioContext || window.webkitAudioContext)();
    return ctx;
  }
  /* misura per ~1,8 s il livello massimo visto da un analyser */
  function misura(c, nodo, fatto) {
    var an = c.createAnalyser(); an.fftSize = 512;
    nodo.connect(an);
    var buf = new Uint8Array(an.frequencyBinCount);
    var max = 0, giri = 0;
    var t = setInterval(function () {
      an.getByteFrequencyData(buf);
      for (var i = 0; i < buf.length; i++) if (buf[i] > max) max = buf[i];
      if (++giri >= 18) { clearInterval(t); fatto(max); }
    }, 100);
  }
  function base(c) {
    return {
      statoContesto: c.state,
      sampleRate: c.sampleRate,
      currentTime: +c.currentTime.toFixed(2),
      audioSessionType: navigator.audioSession ? navigator.audioSession.type : null,
    };
  }

  /* 1 — WebAudio puro: oscillatore → destination */
  document.getElementById('t1').onclick = function () {
    stato('test 1 in corso… (senti un BEEP?)');
    try {
      var c = contesto();
      c.resume().then(function () {
        var o = c.createOscillator(); o.frequency.value = 440;
        var g = c.createGain(); g.gain.value = 0.25;
        o.connect(g); g.connect(c.destination);
        o.start(); o.stop(c.currentTime + 2);
        misura(c, g, function (livello) {
          var r = base(c);
          r.livelloMisurato = livello;
          r.nota = livello > 10 ? 'il grafo PRODUCE suono' : 'il grafo NON produce';
          rapporto.test.t1_destination = r;
          scrivi('e1', r, livello > 10);
          stato('test 1 finito — lo hai SENTITO? ricordalo per il rapporto');
        });
      });
    } catch (e) { rapporto.test.t1_destination = { errore: String(e) }; scrivi('e1', { errore: String(e) }, false); }
  };

  /* 2 — il ponte: oscillatore → MediaStreamDestination → <audio> */
  document.getElementById('t2').onclick = function () {
    stato('test 2 in corso… (senti un BEEP?)');
    try {
      var c = contesto();
      c.resume().then(function () {
        var msd = c.createMediaStreamDestination();
        var el = new Audio();
        el.srcObject = msd.stream;
        el.playsInline = true;
        document.body.appendChild(el);
        var esitoPlay = 'non chiamato';
        el.play().then(function () { esitoPlay = 'ok'; })
          .catch(function (e) { esitoPlay = 'RIFIUTATO: ' + e.name; });
        var o = c.createOscillator(); o.frequency.value = 440;
        var g = c.createGain(); g.gain.value = 0.25;
        o.connect(g); g.connect(msd);
        o.start(); o.stop(c.currentTime + 2);
        misura(c, g, function (livello) {
          var r = base(c);
          r.livelloMisurato = livello;
          r.elementoPlay = esitoPlay;
          r.elementoPaused = el.paused;
          r.elementoMuted = el.muted;
          rapporto.test.t2_ponte = r;
          scrivi('e2', r, livello > 10 && !el.paused);
          stato('test 2 finito — lo hai SENTITO?');
        });
      });
    } catch (e) { rapporto.test.t2_ponte = { errore: String(e) }; scrivi('e2', { errore: String(e) }, false); }
  };

  /* 3 — il canale delle anteprime: <audio src=file> */
  document.getElementById('t3').onclick = function () {
    stato('test 3 in corso… (senti un suono dalla libreria?)');
    fetch('/api/frequencies/sounds')
      .then(function (r) { return r.json(); })
      .then(function (d) {
        var items = d.items || d;
        var url = items[0] && (items[0].stream_url || items[0].url);
        if (!url) throw new Error('nessun suono in libreria');
        var el = new Audio(url);
        el.playsInline = true;
        document.body.appendChild(el);
        return el.play().then(function () {
          setTimeout(function () {
            var r = { url: url, elementoPaused: el.paused,
              readyState: el.readyState, currentTime: +el.currentTime.toFixed(2) };
            el.pause();
            rapporto.test.t3_audioFile = r;
            scrivi('e3', r, r.currentTime > 0);
            stato('test 3 finito — lo hai SENTITO?');
          }, 2000);
        });
      })
      .catch(function (e) {
        rapporto.test.t3_audioFile = { errore: String(e) };
        scrivi('e3', { errore: String(e) }, false);
      });
  };

  /* 4 — lo sblocco: un <audio> di file parte NEL TAP, e SUBITO dopo
     l'oscillatore va a destination. Se il 4 suona e l'1 no, iOS
     apre il canale solo quando un media element "vero" e' in play. */
  document.getElementById('t4').onclick = function () {
    stato('test 4 in corso… (senti PRIMA il suono, POI un beep?)');
    fetch('/api/frequencies/sounds')
      .then(function (r) { return r.json(); })
      .then(function (d) {
        var items = d.items || d;
        var url = items[0] && (items[0].stream_url || items[0].url);
        var el = new Audio(url);
        el.playsInline = true; el.loop = true; el.volume = 0.4;
        document.body.appendChild(el);
        el.play().catch(function () {});
        var c = contesto();
        return c.resume().then(function () {
          var o = c.createOscillator(); o.frequency.value = 660;
          var g = c.createGain(); g.gain.value = 0.25;
          o.connect(g); g.connect(c.destination);
          o.start(); o.stop(c.currentTime + 2.5);
          misura(c, g, function (livello) {
            el.pause();
            var r = base(c);
            r.livelloMisurato = livello;
            rapporto.test.t4_sblocco = r;
            scrivi('e4', r, livello > 10);
            stato('test 4 finito — hai sentito il BEEP (660 Hz)?');
          });
        });
      })
      .catch(function (e) {
        rapporto.test.t4_sblocco = { errore: String(e) };
        scrivi('e4', { errore: String(e) }, false);
      });
  };

  document.getElementById('copia').onclick = function () {
    var testo = JSON.stringify(rapporto, null, 1);
    function fatto(come) {
      document.getElementById('ecopia').textContent =
        'copiato (' + come + ') — incollalo in chat. E scrivi QUALI test hai SENTITO.';
    }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(testo).then(function () { fatto('appunti'); },
        function () { document.getElementById('ecopia').textContent = testo; fatto('a schermo'); });
    } else {
      document.getElementById('ecopia').textContent = testo; fatto('a schermo');
    }
  };
})();
