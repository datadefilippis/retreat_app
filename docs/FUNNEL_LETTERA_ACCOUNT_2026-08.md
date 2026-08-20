# Lettera e Account — analisi del funnel e piano NL (20 agosto 2026)

**La domanda del founder**: togliere l'iscrizione alla Lettera «solo
email» e rendere obbligatoria la creazione dell'account?

**La risposta corta**: no — ma il fastidio che l'ha generata è reale, e
non è dove sembrava. Il piano qui sotto lo toglie senza pagare il
prezzo di un funnel strozzato.

---

## 1. Diagnosi del «bug» (riprodotto, 20/8)

Test del founder: `utente@admin.com` iscritta alla Lettera, poi
creazione account → errore, più volte.

Riproduzione con i log davanti:

- l'iscrizione newsletter NON c'entra nulla: con una password valida il
  signup della stessa email risponde `202 verification_required`.
  I due sistemi non confliggono;
- i 5 errori erano la **policy password**: 12 caratteri minimi,
  maiuscola, minuscola, numero, E il controllo sui data-breach noti
  (una password formalmente valida come `ProvaProva123!` viene
  rifiutata perché compare nei leak pubblici);
- al sesto tentativo e' scattato il rate limit del signup (5/min) →
  altri errori, stavolta 429. Sei rifiuti di fila che, vissuti
  dall'utente, sembrano «il processo è rotto».

Il muro è la password, non la newsletter. E la beffa architetturale:
i platform account sono nati **magic-link-first** («nessuna password al
primo giro», piano P1) e `request_magic_link` è già find-or-create —
il backend sa creare account senza password da luglio. È la UI della
vista «Crea il tuo account» che impone il percorso password.

## 2. Perché NON legare la Lettera all'account (raccomandazione)

1. **La Lettera è la cima del funnel della fase rete.** Home, blog,
   gate delle meditazioni, gate delle tracce: è il motore lead/SEO su
   cui poggia tutta la fase (SEO_STRATEGY, ciclo NW). «Lascia l'email
   per leggere la guida» → «crea un account con password di 12
   caratteri non presente nei data-breach per leggere la guida» è il
   modo più rapido per strozzarlo nel punto di fiducia minima.
2. **GDPR / minimizzazione.** Newsletter = consenso marketing; account
   = contratto di servizio. Obbligare l'account per ricevere una email
   raccoglie più dati dello scopo e intreccia due basi giuridiche che
   oggi sono pulite (e già auditate: double opt-in, consent_audit).
3. **Il ponte esiste già, è solo invisibile.** `newsletter_status` al
   login aggancia i benefici da iscritto all'account (AP2); il claim
   retroattivo aggancia gli acquisti; il magic link crea l'account.
   Non serve fondere i sistemi: serve offrire il passaggio nel
   momento giusto.

## 3. Il piano NL — «Lettera leggera, account magnete»

### NL1 — L'account nasce senza password (il fix del muro)
La vista «Crea il tuo account Aurya» chiede nome, email e consensi.
Bottone primario: **«Crea l'account»** → passa dal flusso magic/OTP
esistente (find-or-create + verifica email in un gesto). La password
diventa opzionale, si imposta DOPO da /account («Imposta una password»
esiste già, TA5). La policy severa resta per chi la sceglie e per gli
operatori (dove protegge un business).
*Zero endpoint nuovi: è la UI che smette di imporre il percorso duro.*

### NL2 — Il ponte nei due sensi
- Dopo ogni iscrizione alla Lettera (home, blog, gate): riga inline
  «Vuoi ritrovare guide ed esperienze su ogni dispositivo? Crea
  l'account con questa email» → /accedi?vista=crea&email=... (un campo
  già compilato, zero password per NL1).
- Alla creazione account: checkbox **non preselezionata** «Iscrivimi
  anche alla Lettera» (consenso separato, stesso double opt-in).
  Se l'email è già iscritta confermata, la checkbox non appare.

### NL3 — Un errore che aiuta invece di respingere
Dove la password resta (vista login, imposta password): requisiti
mostrati PRIMA e validati live; il rifiuto da data-breach spiegato in
una riga umana; il form non si svuota; il 429 del rate limit dice
«aspetta un minuto», non «errore».

### NL4 — Guardie
- il signup senza password passa dallo stesso find-or-create del magic
  link (mai una terza strada);
- la checkbox Lettera mai preselezionata (GDPR);
- l'iscrizione email-only resta viva su tutte le superfici attuali;
- pending vs confirmed invariati: i benefici si agganciano solo da
  confermato (regola AP2 esistente).

## 4. Cosa risolve rispetto al test di oggi

| momento del test | oggi | col piano |
|---|---|---|
| iscrizione Lettera | ok, solo email | invariata + invito account |
| creazione account dopo | 6 errori (password + 429) | nome+email+consensi, fine |
| «mi perdo tra i due» | due token, nessun ponte visibile | ponte esplicito nei due sensi |

Stima: NL1+NL3 ~1 giornata, NL2 ~½, NL4 con le fasi. Nessuna
migrazione, nessun impatto su iscritti esistenti o su operatori.

**Aperto (decisione founder)**: procedere con NL, o insistere
sull'account obbligatorio? (Se obbligatorio: da progettare la sorte
delle superfici di cattura in home/blog e il consenso marketing
disaccoppiato — costi che il piano NL evita.)
