# I percorsi delle meditazioni: analisi di consolidamento (MR7)

8/10/2026, sera. Richiesta del founder: «verificare e ottimizzare tutti i
flussi, renderli solidi pensando in termini di percorsi utente, per non
farlo perdere». Qui ogni percorso, cosa faceva, cosa fa ora, cosa resta.

## 1. Chi arriva e come entra

| Chi | Da dove | Cosa vede | Cosa succede |
|---|---|---|---|
| Visitatore senza nulla | menu «Meditazioni», social, Google | la **soglia del Cerchio** (nome, email, consenso) con l'assaggio di 90 s su /sound | iscrizione → email con il pulsante → `?prova=` → casa aperta. **Verificato dal vivo**: il link della Lettera apre direttamente la casa, la playlist e il player senza rimettere l'email |
| Già nel Cerchio (prova in questo browser) | qualsiasi | la casa | nessuna domanda |
| Già nel Cerchio, altro browser/telefono | | la soglia con «Sei già nel Cerchio? Sblocca con la tua email» | sblocca dichiarando l'email, senza seconda iscrizione |
| Con account Aurya | | la casa, «Buongiorno, Nome», il tuo spazio | l'account vale come il Cerchio |
| Professionista loggato | | la casa; «Crea» in passerella **solo se può comporre** | prima «Crea» appariva a ogni operatore (MR7 lo corregge) |

## 2. Il difetto visto dal founder: «ero dentro, sono uscito e tornato, e mi chiedeva di iscrivermi»

Due cause trovate nel codice, entrambe chiuse:

1. **Un errore qualsiasi chiudeva la casa.** Il caricamento del catalogo
   mostrava la soglia a ogni errore: con un **token dell'account scaduto**
   (30 giorni) il server rispondeva 401 e la casa chiedeva l'iscrizione anche
   a chi aveva la prova del Cerchio nel browser. Ora: con l'account si prova
   l'account; su 401 si **riprova con la prova del Cerchio**; la soglia si
   mostra solo se il server dice «locked»; se cade la rete si dice «Non
   riesco a raggiungere le meditazioni» con «Riprova», senza chiedere nulla.
2. **«Esci» dimentica anche il Cerchio.** Per scelta (ID-quater, SB1): su un
   telefono condiviso uscire deve chiudere tutto. Se il founder ha usato
   «Esci» dal menu, al ritorno la soglia è corretta; basta «Sei già nel
   Cerchio? Sblocca con la tua email». **Non cambiato**: è il contratto
   della privacy. Si può rivedere se si vuole che il Cerchio sopravviva
   all'uscita dall'account (una riga in `MarketplaceShell.logoutPlatform` e
   in `lib/cappelli.esci`).

## 3. Le email

- Benvenuto, promemoria, Lettera: il pulsante porta a `/meditazioni?prova=…`
  (link verificante): la prova si salva prima del primo render, l'indirizzo
  si pulisce, la casa è aperta. **Verificato** in questa sessione.
- Annuncio «nuova meditazione/playlist» (quando lo accenderai): stesso
  meccanismo, link diretto alla meditazione già sbloccata.

## 4. «Crea» per chi può

- Server: `require_sound_crea` (Pro o concessione del system admin) chiude
  tutte le API di Crea; la pagina ha il suo portiere.
- Passerella (MR7): «Crea» si vede solo con il privilegio (la cache
  `aurya_sound_crea` scritta da Crea dal profilo dell'operatore). Un
  operatore senza privilegio vede Meditazioni · Il suono e basta.
- Menu dell'omino: per il professionista «Il tuo gestionale» (dove sta
  Strumenti → Crea con il suo cancello), mai un link diretto a Crea.

## 5. Tornare indietro senza perdersi

| Da | A | Prima | Ora |
|---|---|---|---|
| casa → Percorso | pagina del corso | `<a>` con ricarica piena; «←» del corso andava **sempre al profilo** dell'operatore | `Link` della SPA con `?da=meditazioni`; «← Le meditazioni» torna alla casa. Il tasto indietro del browser funziona in entrambi i casi |
| casa → playlist | pagina playlist | «← Le meditazioni» | uguale |
| casa → «Il suono» | **usciva** nella landing chiara | | **un foglio** con le tre porte (Esplora le frequenze · Le fondamenta · Il Lab) e, in fondo, «La pagina di Aurya Sound»: l'utente resta nella casa (MR7) |
| schede, fondamenta, Lab | | passerella «Meditazioni» in testa | uguale: si torna con un tocco |
| pagina della meditazione (link condiviso) | | «tutte le Meditazioni» nel cancello, passerella | uguale |
| card → ascolto | **cambiava pagina** | | suona nella barra, il titolo apre il foglio; «Apri la pagina» solo se la si vuole (MR3) |
| account → «Meditazioni» | la casa | | uguale; «I tuoi» nella barra porta al tuo spazio |
| landing /sound → «Ascolta una meditazione» | anteprima sul posto, cancello sul posto | | uguale (FN3) |

## 6. Cosa resta da decidere (non cambiato)

- **«Esci» e il Cerchio** (punto 2.2): oggi uscire dall'account dimentica
  anche la prova del Cerchio. Tenere (privacy) o separare (comodità)?
- **Tablet 600–899 px**: la ricerca si apre dal foglio come su telefono.
- **Il Visual** resta solo a chi compone; al pubblico la copertina.

## 7. Le guardie

`tests/test_meditazioni_mr7.py`: la soglia solo su «locked», il riprovo con
la prova su 401, «Crea» solo col privilegio, il foglio del suono dalla casa,
il «torna» del corso che rispetta `?da=meditazioni`.
