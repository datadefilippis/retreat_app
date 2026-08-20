# Mappa dei percorsi — identità, accessi, Lettera (20 agosto 2026)

Tutti gli scenari verificati sul codice dopo i cicli ID / NL. Serve a
due cose: capire dove passa una persona, e vedere dove il sistema è
ancora incoerente (§5).

Legenda archivi: **U** = `users` (operatore, org-scoped) · **P** =
`platform_accounts` (cliente) · **L** = `aurya_subscribers` (Lettera).
I tre sono indipendenti e legati SOLO dall'email.

---

## 1. Registrazione — dove nasce cosa

| # | Chi | Da dove | Cosa crea | Verifica | Dove atterra |
|---|---|---|---|---|---|
| R1 | Professionista | `/entra-nella-rete#presentati` (form incorporato) | **U** + organizzazione | email operatore | `/benvenuto` → `/inizia` |
| R2 | Professionista | `/signup` (link vecchio, condiviso) | → redirect a R1 | — | come R1 |
| R3 | Utente | omino → «Crea il tuo account» → `/accedi?vista=crea` | **P** con password | email cliente | `/account` |
| R4 | Utente | stessa vista → «Preferisci senza password?» | **P** senza password | il link stesso | `/account` |
| R5 | Utente | acquisto da ospite (checkout) | **P** «guscio» passwordless | nessuna (claim dopo) | success page |
| R6 | Chiunque | solo Lettera (nessun account) | **L** pending | clic di conferma | resta dov'era |

Note verificate:
- R3/R4 **non** creano U. R1 **non** crea P. Nessuno dei due crea L,
  se non spuntando la casella (§2, N5).
- R5 crea un P «guscio» mai verificato: al primo signup vero
  (R3) viene **adottato**, non duplicato.
- Nessun account nasce senza consenso legale timbrato (`aurya_legal`
  + audit): dal 20/8 vale anche per il magic link.

## 2. Lettera di Aurya — dove ci si iscrive

| # | Chi | Da dove | Sorgente | Serve un account? |
|---|---|---|---|---|
| N1 | Chiunque | home (form Lettera), `/newsletter` | `home_letter`, `newsletter` | no |
| N2 | Chiunque | Magazine: CTA in fondo e **gate delle guide riservate** | `blog_*` | no |
| N3 | Chiunque | gate `/meditazioni` | `meditazioni` | no |
| N4 | Chiunque | gate della traccia condivisa `/frequenze/:slug` | `frequenze:<slug>` | no |
| N5 | Utente in registrazione | casella «Iscrivimi anche alla Lettera» (entrambe le strade R3/R4) | `account_signup` | sì, la sta creando |
| N6 | **Operatore** | le stesse superfici pubbliche (N1-N4), con la sua email | come sopra | no |

Regole verificate:
- doppio opt-in sempre: `pending` → clic → `confirmed`. I benefici
  (guide sbloccate) valgono **solo da confirmed**.
- l'iscrizione è **per email**, slegata dall'account: la stessa email
  vale per U, P e L insieme senza conflitti.
- disiscrizione da `/public/newsletter/unsubscribe` (token nell'email).

## 3. Accesso — una porta

| # | Situazione | Cosa succede |
|---|---|---|
| A1 | `/accedi` con email+password | il server prova U poi P: entra nel mondo che combacia |
| A2 | email e password valide su **entrambi** | entra da operatore + (se collegati) anche il cappello cliente |
| A3 | identità **collegate** | un accesso rilascia **entrambi** i token (SSO) |
| A4 | `/login`, `/account/accedi`, `/account/signup` | redirect a `/accedi` conservando `?next=` e `?token=` |
| A5 | «Accedi senza password» | codice a 6 cifre / magic link — **solo** se l'account esiste |
| A6 | «Password dimenticata» | reset inviato a **ogni** mondo in cui l'email esiste |
| A7 | credenziali sbagliate, email inesistente, quota email superata | **stesso** errore, byte per byte |
| A8 | 5 tentativi falliti | blocco 15 min (poi 30, 60… fino a 24h), email di allerta |

## 4. Cambio di cappello

| # | Da → a | Come | Perché così |
|---|---|---|---|
| C1 | operatore → cliente | **un clic** dal menu dell'omino: il cappello nasce dall'identità già verificata e il token cliente arriva nella stessa risposta | è solo un'identità: nulla da dichiarare |
| C2 | cliente → operatore | `/account` → «Apri il tuo spazio» → registrazione professionale con l'email precompilata | nasce **un'attività**: servono nome e dati dell'organizzazione |
| C3 | account personale creato per sbaglio da un professionista | fa C2 con la stessa email: alla verifica i cappelli si collegano | nessun account da buttare |
| C4 | collegamento automatico | a ogni verifica email, se l'altra parte esiste ed è verificata | mai su email non verificate (anti-takeover) |
| C5 | cancellazione cliente (GDPR) / disattivazione org | il legame si spezza, l'altro cappello resta | i due mondi non si trascinano a vicenda |

## 5. Dove il sistema è ancora incoerente (da decidere)

1. **L'operatore non ha un posto suo per la Lettera.** Può iscriversi
   solo dalle superfici pubbliche (N6) e, se non ha il cappello
   cliente, non vede da nessuna parte se è iscritto o no. In `/account`
   lo stato c'è; nel gestionale no. *Proposta: una riga in
   Impostazioni → il suo stato Lettera, con iscrizione/disiscrizione.*
2. **Lo stato «pending» è invisibile.** Chi si iscrive e non conferma
   resta in sospeso e non lo sa più: nessuna schermata glielo ricorda,
   e `/account` mostra semplicemente «Iscriviti». *Proposta: se
   l'email risulta pending, dire «Controlla la posta: manca la
   conferma» invece di riproporre l'iscrizione.*
3. **R5 (acquisto da ospite) non è raccontato.** L'account guscio
   nasce e nessuno lo dice: l'utente lo scopre solo se prova ad
   accedere. *Proposta: nella success page, «Il tuo account è pronto:
   imposta una password o entra senza».*
4. **La porta dormiente `/account/login`** (portale clienti org-scoped)
   esiste ancora e non è raggiungibile da nessun link. Va spenta con
   un redirect quando decidiamo di toccarla (ha test suoi).
5. **`/benvenuto` è saltabile e non torna più.** Chi salta i campi
   (città, telefono, discipline) non li ritrova proposti da nessuna
   parte: restano nel profilo, ma nessuno glieli richiede.
