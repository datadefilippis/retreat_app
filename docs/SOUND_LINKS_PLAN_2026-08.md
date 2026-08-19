# Aurya Sound — Piano linking pagine (ciclo LN, 19/8/2026)

## Il problema

Tutto il workspace vive su **una sola rotta** (`/frequenze`) e le quattro
viste (Esplora, Crea, Impara, Le mie tracce) sono `useState` interni
(`FrequenzePage.js:82-85`). Conseguenze:

- il refresh perde la vista: chi sta in Crea si ritrova altrove;
- nessuna pagina è linkabile: non puoi mandare a qualcuno «la Guida»
  o tornare con un bookmark alle tue tracce;
- il back del browser non sa nulla delle viste.

## La superficie di oggi (inventario verificato)

| URL | Chi ci arriva | Protezione |
|---|---|---|
| `/frequenze` | operatore (nessun altro link nel gestionale: solo App.js) | ProtectedRoute (login + email verificata) |
| `/frequenze/:slug` | **link condivisi in giro**, preferiti in /account, vetrina | pubblica + cancello Lettera/account server-side |
| `/meditazioni` | pubblico, CTA `/account/accedi?next=/meditazioni` | pubblica |

Sitemap: nessuna voce frequenze/meditazioni (niente SEO da toccare).
La pubblicazione genera `origin/frequenze/<slug>` (`FrequenzePage.js:526,540`).

## La mappa nuova

Il workspace si sposta sotto **`/sound`** — è il nome del prodotto
(Aurya Sound) e soprattutto **libera il namespace** `/frequenze/*` che
resta per sempre ai link pubblici delle tracce (nessun rischio che una
traccia intitolata «Crea» collida con una rotta interna).

| URL nuovo | Pagina | Stato profondo (query/ancore) |
|---|---|---|
| `/sound` | → redirect a `/sound/esplora` | — |
| `/sound/esplora` | biblioteca frequenze | `?categoria=bande-cerebrali\|altre-frequenze\|metodi` · `?mondo=suoni&categoria=ambient\|droni\|campane\|natura\|ritmi\|voce` |
| `/sound/crea` | compositore | `?bozza=<id>` → al refresh ricarica la bozza via `openDraft` |
| `/sound/impara` | Le fondamenta (Guida) | ancore `#gd-cervello` … già esistenti |
| `/sound/impara/glossario` | Glossario | — |
| `/sound/tracce` | Le mie tracce (salvataggi) | — |

**Legacy**: `/frequenze` (senza slug) → redirect a `/sound/esplora`,
così bookmark e abitudini non si rompono.

**Invarianti — non si toccano:**
- `/frequenze/:slug` player pubblico: URL, cancello Lettera/account
  server-side, «Copia link», preferiti, tutto INVARIATO;
- `/meditazioni` e il flusso `?next=` di `/account/accedi`;
- ProtectedRoute sul workspace (stessa protezione di oggi, su `/sound/*`);
- publish/unpublish, bozze org-scoped, motore audio, pagina Crea
  (cambia solo COME ci si arriva, non cosa contiene).

## Semantica della history (coerente con «back onesti», ciclo L2/PS)

- cambiare **vista** (Esplora→Crea) = `push`: il back torna alla vista di prima;
- cambiare **tab/categoria/mondo** = `replace`: il back non deve
  ripercorrere ogni tab cliccato;
- `?bozza=` si aggiorna in `replace` al salvataggio/apertura.

## Titoli documento

Ogni pagina timbra `document.title`: «Aurya Sound — Esplora»,
«— Crea», «— Le fondamenta», «— Glossario», «— Le mie tracce».
(Il player pubblico ha già il titolo della traccia.)

## Fasi

- **LN0 — diagnosi refresh→homepage.** Riprodurre il redirect segnalato
  dal founder (sospetto: race del token in AuthContext → `/login` →
  rimbalzo). Capire prima di costruire.
- **LN1 — rotte.** `/sound/*` → FrequenzePage (stesso componente, vista
  letta dall'URL invece che da `useState`), redirect `/frequenze`→
  `/sound/esplora`, aggiornare la guardia `test_pagina_lazy_in_app`
  che oggi pretende `path="/frequenze"`.
- **LN2 — stato profondo.** categoria/mondo in Esplora, glossario in
  Impara, `?bozza=` in Crea con ricarica al refresh. Push/replace come
  sopra.
- **LN3 — punti d'ingresso.** document.title per vista; verifica che i
  link generati (pubblicazione, copia link) restino su
  `origin/frequenze/<slug>`; nessun altro link interno da aggiornare
  (inventario: solo App.js).
- **LN4 — guardie & E2E.** Refresh su OGNI vista resta lì; back onesto;
  `/frequenze/<slug-vero>` suona ancora; gate Lettera intatto; `next=`
  intatto; batteria completa.

## Rischi e mitigazioni

| Rischio | Mitigazione |
|---|---|
| Rompere i link pubblici già condivisi | `/frequenze/:slug` non si tocca; guardia E2E dedicata |
| Perdere lavoro non salvato in Crea al refresh | il refresh ricarica `?bozza=` se salvata; il non-salvato si perde OGGI come dopo (nessuna regressione, e il salvataggio bozza esiste apposta) |
| La guardia sul router in App.js diventa rossa | aggiornata in LN1, nello stesso commit |
| Ordine delle rotte (`/sound` vs `/sound/:qualcosa` futuro) | nessuna rotta pubblica sotto `/sound`: namespace riservato al workspace |
