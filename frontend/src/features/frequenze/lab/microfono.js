/**
 * LA CURA DEL MICROFONO (founder 30/8, dal telefono) — una voce sola.
 *
 * «Nessun microfono disponibile» copriva OGNI errore: permesso
 * negato, browser di un'app senza l'API, mic occupato, vincoli
 * rifiutati. Ogni stanza che apre l'orecchio passa da qui: il
 * messaggio dice la CURA giusta per quel caso, e il codice tecnico
 * resta tra parentesi — è la diagnosi che ci serve quando un utente
 * ci scrive «non funziona».
 */
export function curaMicrofono(e) {
  const nome = (e && e.name) || 'Errore';
  const cure = {
    NotAllowedError: 'Permesso negato: consenti il microfono a questo sito (icona vicino all’indirizzo, o Impostazioni del telefono).',
    SecurityError: 'Il browser blocca il microfono su questa pagina: controlla i permessi del sito nelle impostazioni.',
    NotFoundError: 'Il browser non trova un microfono: controlla che non sia disattivato nelle impostazioni del telefono.',
    NotReadableError: 'Il microfono è occupato da un’altra app: chiudila e riprova.',
    InvalidStateError: 'Il motore audio del telefono ha rifiutato il collegamento: chiudi le altre app o schede che usano l’audio e riprova.',
    ApiMancante: 'Questo browser non dà accesso al microfono: apri la pagina in Safari o Chrome (non dal browser interno di un’app).',
  };
  return (cure[nome]
    || 'Il microfono non risponde: riprova, o apri la pagina in Safari o Chrome.')
    + ' (' + nome + ')';
}
