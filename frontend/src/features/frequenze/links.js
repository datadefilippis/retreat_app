/*
 * SP3 — dove porta l'invito «per operatori».
 *
 * NON a una landing di racconto: dentro Aurya Sound, alla stessa
 * biblioteca da cui si e' partiti — che da operatore ha i bottoni
 * Ascolta e + Sessione accesi. E' la continuita' giusta: chi clicca
 * voleva ascoltare QUELLA frequenza, non leggere una brochure.
 *
 * Il passaggio dal login e' necessario, non burocratico: /sound/esplora
 * e' pubblica, quindi un link diretto lascerebbe il visitatore dov'era
 * senza chiedergli nulla. Con ?next= il login (che porta gia' il suo
 * «non hai un account? registrati») riporta esattamente qui.
 */
export const PRO_ENTRY = `/login?next=${encodeURIComponent('/sound/esplora')}`;
