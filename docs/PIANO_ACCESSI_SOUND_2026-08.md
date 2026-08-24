# Piano — Il privilegio di comporre + lo sblocco senza email (24/8/2026)

Due richieste del founder, un vincolo: non rompere nulla di costruito.

---

## PARTE 1 · La creazione di Aurya Sound diventa un PRIVILEGIO

### Oggi (mappa verificata nel codice)

| area | chi la vede |
|---|---|
| Frequenze + tutorial (/sound, /sound/impara…) | tutti |
| Meditazioni pubblicate (/meditazioni, /frequenze/:slug) | anteprima libera, intero con sblocco Lettera/account |
| **Crea** (/sound/crea), **Le mie tracce**, leggio voce, publish/master | **qualunque operatore loggato** |
| Upload basi libreria | già solo system admin |

Il gate del comporre esiste già e ha un nome: **`canCompose`**
(FrequenzePage, ciclo SP del 19/8: «comporre resta professionale»).
Oggi vale `!!user` — qualunque operatore. La modifica è: canCompose =
operatore **con privilegio**, concesso dal system admin. Fattibilità:
ALTA — si stringe un gate esistente, non se ne inventa uno.

### Il modello: un flag per organizzazione

`organizations.sound_composer` (bool, default **false**). Per-org e
non per-utente: in Aurya l'operatore È l'org (i membri del team
ereditano — coerente con tutto il resto del sistema).

**Migrazione**: al deploy, `sound_composer: true` SOLO per le org che
hanno già bozze o tracce in `frequency_tracks` (chi compone oggi non
si sveglia chiuso fuori — zero sorprese per i pochi pionieri, founder
incluso). Tutte le altre: false.

### Backend — il portiere (fonte di verità)

1. Dependency `require_sound_composer(current_user)` in
   frequencies.py: carica l'org, se `sound_composer` non è true →
   403 con messaggio umano («La composizione è su invito: scrivici»).
2. Si applica a TUTTI gli endpoint di scrittura/lettura privata:
   `/tracks` (list/get/create/patch/delete), `publish`, `unpublish`,
   `master` (upload), gli endpoint voce (upload/lista/delete leggio).
3. NON si tocca: `/sounds` in lettura (alimenta il player pubblico),
   `/public/*` (meditazioni pubblicate), catalogo, demo del visual.
4. Il flag viaggia nel payload dell'utente loggato (dove il client
   legge org/piano — endpoint /auth/me o equivalente) come
   `sound_composer: bool`, così il frontend disegna senza chiamate in
   più.

### Frontend — cosa si disegna

1. `canCompose` diventa `!!user && user.sound_composer` (il valore
   arriva col profilo; in attesa del profilo si resta prudenti:
   niente flash dell'area creazione).
2. `/sound/crea` e `/sound/tracce` per l'operatore senza privilegio:
   pagina gentile «La composizione è su invito» con contatto — NON un
   redirect muto (un operatore incuriosito è un lead).
3. Voci di menu (topbar Sound, menu due mondi, eventuali CTA
   «Crea»): visibili solo con privilegio. Le superfici PUBBLICHE
   (Esplora, Impara, Meditazioni) intatte per tutti.
4. Nessun cambio per utenti/visitatori: già oggi non vedono Crea.

### Il pannello del system admin — PAGINA separata

Richiesta esplicita: «pagina separata, non sezione nella stessa
pagina come facciamo sempre». Oggi /admin è UNA pagina a 14 tab.

- Rotta nuova **`/admin/sound`** (lazy, dietro lo stesso guard
  system_admin di /admin), dentro AppLayout.
- Voce di menu: nel menu laterale (Layout) accanto a «System Admin»,
  visibile solo a system_admin: **«Aurya Sound»**. In più, nella
  TabsList di /admin, un trigger-link che NAVIGA a /admin/sound (così
  la si trova da entrambe le porte senza duplicare contenuto).
- La pagina: elenco org (nome, slug, piano, data ultima traccia,
  numero tracce/pubblicate) con **interruttore** sound_composer per
  riga + ricerca per nome. Endpoint dedicati:
  `GET /admin/sound/composers` (lista con conteggi) e
  `POST /admin/sound/composers/{org_id}` {enabled} — entrambi
  `require_system_admin`, con riga di audit log (già esiste il
  meccanismo audit del pannello).

### Cosa NON si rompe (verifiche previste)

- Le meditazioni GIÀ PUBBLICATE di org a cui non si dà il privilegio
  restano pubbliche e ascoltabili (il player usa /public/*, non
  gateato). Il privilegio governa il COMPORRE, non l'esistere.
- La suite ha ~40 guardie sul mondo frequenze: si aggiornano i test
  che creano tracce (le fixture ricevono il flag) — lavoro noto.
- L'org demo (fixture viva dei test) riceve il flag nella migrazione.

### Onde

- **PC1** modello+migrazione+dependency backend (con guardie 403).
- **PC2** flag nel profilo utente + canCompose stretto + pagina
  gentile + menu.
- **PC3** pagina /admin/sound + endpoint admin + audit.
- **PC4** guardie: portiere su TUTTI gli endpoint di scrittura,
  fixture aggiornate, smoke con org senza privilegio (403) e con
  (200); collaudo founder.

---

## PARTE 2 · Lo sblocco contenuti non manda più email al già iscritto

### Il fatto (riga trovata)

`routers/subscribers.py` → subscribe → ramo «già confermato» →
`_send_access_email(...)`: il «magic link di accesso» nato per il
gate delle GUIDE («nuovo dispositivo»). Ma il flusso di sblocco
(SB2, `iscriviESblocca` in lib/cerchio.js) subito dopo chiama
`/newsletter/unlock` che consegna la prova DIRETTAMENTE: l'email è
**ridondante** (costo Brevo) e il suo copy parla di guide anche
quando sblocchi una meditazione (sbagliato, come visto dal founder).

### La cura — chirurgica e reversibile

1. Il client dichiara il contesto: `iscriviESblocca` aggiunge
   `unlock_flow: true` al payload del subscribe (è il cervello unico
   di TUTTI i form di sblocco: guide e meditazioni insieme).
2. Il backend, nel ramo «già confermato»: se `unlock_flow` → aggiorna
   le preferenze e **niente email** (la prova arriva dalla chiamata
   unlock immediatamente successiva). Senza flag (form puri della
   Lettera: footer, home, blog compact) il magic link RESTA — lì
   serve davvero (nessuno sblocco contestuale segue).
3. La risposta resta identica in tutti i casi: nessun oracolo di
   enumerazione email (proprietà attuale, preservata).
4. Guardia: già-confermato + unlock_flow → zero send; già-confermato
   senza flag → send come oggi; pending/nuovo → conferma come oggi.

### Costo/rischio

Minimo: un campo opzionale nel payload (default false = comportamento
identico a oggi), un if nel ramo già-confermato. Zero migrazioni.

---

## Ordine proposto

PARTE 2 subito (mezz'ora, spegne un costo vivo) → PARTE 1 in onde
PC1→PC4. Deploy unico a fine PC4 o due deploy separati (PARTE 2 può
uscire da sola).
