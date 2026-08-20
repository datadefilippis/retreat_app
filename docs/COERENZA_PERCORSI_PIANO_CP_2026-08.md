# Piano CP — chiudere le cinque incoerenze dei percorsi (20 agosto 2026)

Riferimento: `docs/MAPPA_PERCORSI_IDENTITA_2026-08.md` §5. Nessuna di
queste rompe qualcosa oggi: sono i punti in cui il sistema è coerente
«per fortuna» invece che per progetto. Il filo che le unisce è uno solo:

> **lo stato di una persona deve essere visibile e reversibile là dove
> quella persona si trova.**

Ordine scelto per costo/beneficio decrescente. Ogni fase è autonoma e
deployabile da sola.

---

## CP1 — Lo stato della Lettera diventa vero (non più un booleano)

**Il problema.** `newsletter_status` dice solo «iscritto sì/no», dove
«sì» = confermato. Chi si iscrive e non conferma sparisce in un limbo:
`/account` gli ripropone «Iscriviti alla lettera» come se non avesse
mai fatto nulla, e la conferma che aspetta nella posta non è mai
nominata.

**Il fix.** Lo stato diventa a tre valori — `none` / `pending` /
`confirmed` — esposto come `newsletter_state` accanto al booleano
esistente (che resta per non toccare i chiamanti: BN3, AP2, il login).

`/account`:
- `confirmed` → come oggi (guide sbloccate);
- `pending` → **«Manca solo la conferma: controlla la posta»** +
  «Rimanda l'email» (che è una nuova POST subscribe con la stessa
  email: il flusso esistente rigenera il token e rimanda);
- `none` → come oggi (invito a iscriversi).

**Guardie.** `pending` non sblocca mai nulla (invariato); il rinvio
passa dalla route pubblica; nessun token emesso per chi non ha
confermato.

*Backend: `newsletter_status` + `/platform/me`. Frontend: AccountPage.
~½ giornata.*

---

## CP2 — L'operatore ha un posto suo per la Lettera

**Il problema.** Un operatore può iscriversi solo dalle superfici
pubbliche, e se non ha il cappello cliente non sa **da nessuna parte**
se è iscritto. Nel gestionale la Lettera non esiste.

**Il fix.** Una riga in **Impostazioni** del gestionale: «La lettera di
Aurya» con lo stato della SUA email (CP1: none/pending/confirmed) e
l'azione coerente — iscriviti / rimanda la conferma / disiscriviti.

Backend: due endpoint autenticati col token operatore, che riusano i
flussi pubblici invece di duplicarli:
- `GET /api/auth/letter` → stato per l'email dell'utente;
- `POST /api/auth/letter` `{subscribe: bool}` → iscrizione (route
  pubblica, `source=gestionale`) o disiscrizione (il token si genera
  server-side con `generate_subscriber_token`, mai richiesto all'utente).

**Perché non basta un link alle pagine pubbliche**: l'operatore
dovrebbe ridigitare la sua email e non saprebbe comunque lo stato.

*~½ giornata, incluse le guardie.*

---

## CP3 — L'acquisto da ospite racconta l'account che ha creato

**Il problema.** Comprando da ospite nasce un platform account
«guscio» (per il Passaporto) e **nessuno lo dice**. L'utente lo scopre
solo se prova ad accedere — e se prova con una password che non ha mai
scelto, non entra.

**Il fix.** Nella success page del checkout, dove oggi c'è «Attiva il
tuo account Aurya», il testo diventa esplicito su ciò che è già
successo e offre le due strade reali:
«**Il tuo account Aurya è già pronto** — ci trovi biglietti e
ricevute. Entra senza password (ti mandiamo un link) oppure impostane
una.» → `/accedi?email=…` (link) e `/accedi?vista=recupero&email=…`
(imposta password, che per un guscio è il flusso di reset).

**Guardia.** La success page non deve MAI mostrare l'invito se
l'account esiste già verificato con password (non è «pronto», è suo da
prima): il dato arriva da un check leggero sull'email.

*~½ giornata.*

---

## CP4 — La porta dormiente `/account/login` si spegne

**Il problema.** Il vecchio portale clienti org-scoped
(`customer_accounts`) ha ancora la sua pagina di login, non linkata da
nessuna parte, con un token di tipo diverso. È una terza porta viva.

**Il fix, in due tempi** (perché dietro c'è ancora roba viva: le aule
corsi `/account/courses` sono protette da `CustomerProtectedRoute`):
1. **spegnere l'ingresso**: `/account/login` → redirect a `/accedi`,
   conservando `?next=`; le sessioni customer già emesse continuano a
   valere (nessun token invalidato);
2. **dare una via alle aule**: chi arriva a `/account/courses` senza
   token customer viene mandato a `/accedi` con `?next=`; se il
   corso è stato comprato con l'account Aurya, il Passaporto lo porta
   già lì.

**Verificato in produzione (20/8, sola lettura)**: `customer_accounts`
= **0 documenti**, zero accessi registrati, collezione `course_enrollments`
inesistente. Nessuno usa quel portale: si può spegnere per intero senza
migrazioni e senza rompere niente a nessuno.

*~½ giornata + la verifica in produzione.*

---

## CP5 — `/benvenuto` smette di essere un vicolo cieco

**Il problema.** Città, telefono, Instagram e discipline sono
facoltativi e saltabili: chi salta non se li vede più richiedere.
Sono esattamente i campi che alimentano directory, mappa e filtri —
cioè la visibilità dell'operatore.

**Il fix.** Nessuna nuova schermata: si riusa la **striscia-guida**
che già esiste (`OnboardingStrip`, ciclo AC) e che già sa dire «cosa
manca per spuntare *Presentati*». Si aggiunge il controllo su città e
discipline (le due che contano per essere trovati) con il suo
suggerimento: «aggiungi la tua città e cosa fai: senza, non compari
nelle ricerche» → CTA al profilo pubblico, dove i campi già vivono.

**Guardia.** La striscia non deve diventare un secondo onboarding:
una riga sola, che sparisce appena i campi ci sono.

*~½ giornata.*

---

## Ordine, rischi, verifica

| fase | tocca | rischio | verifica |
|---|---|---|---|
| CP1 | account + status | basso | E2E: iscrizione senza conferma → /account dice «manca la conferma» |
| CP2 | gestionale | basso | E2E: operatore si iscrive e disiscrive dalle Impostazioni |
| CP3 | checkout | basso (solo copy + link) | E2E: acquisto ospite → success page → accesso senza password |
| CP4 | rotte legacy | **basso** (verificato: 0 account in prod) | E2E: /account/login → /accedi con ?next= conservato |
| CP5 | onboarding | basso | E2E: profilo senza città → striscia lo dice → salvato, sparisce |

Totale ~2,5 giornate. Nessuna migrazione dati, nessun token
invalidato, nessun flusso di pagamento toccato.

**CP4 non ha più incognite**: la verifica in produzione dice zero
account e zero aule, quindi la porta si chiude tutta in una volta.
