/**
 * IL REGISTRO DEI CONTEXT AUDIO (31/8/2026, il caso del telefono).
 *
 * Referto del founder: «AudioSession category is not compatible with
 * audio capture» ANCHE a sessione apparentemente libera. La verità:
 * la SPA naviga senza ricaricare, e ogni AudioContext acceso in
 * un'altra pagina (il player, l'engine di esplora, l'anteprima)
 * resta vivo — su iOS UNO SOLO di questi in riproduzione tiene la
 * sessione in «playback» e blocca la cattura del microfono, ovunque.
 *
 * Qui il costruttore viene avvolto UNA volta: ogni context che l'app
 * crea finisce nel registro, e chi deve accendere il microfono può
 * chiedere di liberare l'audio dell'intera scheda (sospendere gli
 * altri context, mettere in pausa i media). Non è un orologio e non
 * tocca l'audio in sé: è l'anagrafe.
 */

const lista = [];

const Orig = typeof window !== 'undefined'
  ? (window.AudioContext || window.webkitAudioContext) : null;

if (Orig && !Orig.__auryaRegistro) {
  const Avvolto = function AudioContextRegistrato(...args) {
    const ctx = new Orig(...args);
    lista.push(ctx);
    /* l'anagrafe non deve crescere per sempre: i chiusi si potano */
    for (let i = lista.length - 1; i >= 0; i--) {
      if (lista[i].state === 'closed') lista.splice(i, 1);
    }
    return ctx;
  };
  Avvolto.prototype = Orig.prototype;
  Avvolto.__auryaRegistro = true;
  try {
    window.AudioContext = Avvolto;
    if (window.webkitAudioContext) window.webkitAudioContext = Avvolto;
  } catch { /* ambienti blindati: pazienza, il registro resta vuoto */ }
}

/** i context vivi (non chiusi) noti all'app */
export function contestiVivi() {
  return lista.filter((c) => c.state !== 'closed');
}

/**
 * Libera l'audio dell'intera scheda per far posto alla cattura:
 * sospende ogni context vivo (tranne l'escluso) e mette in pausa
 * ogni <audio>/<video>. Best-effort totale: niente qui può lanciare.
 */
export async function liberaTutto(tranne = null) {
  try {
    document.querySelectorAll('audio, video').forEach((m) => {
      try { m.pause(); } catch { /* niente */ }
    });
  } catch { /* SSR */ }
  await Promise.all(contestiVivi()
    .filter((c) => c !== tranne)
    .map((c) => c.suspend().catch(() => { /* gia' */ })));
}
