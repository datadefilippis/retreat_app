# Le mie tracce — refinement e consolidamento (ciclo TM, 27/8/2026)

*Le domande del founder («cosa succede se clicco Pubblica? mica vanno
nelle Meditazioni? il cliente non incappa nella newsletter, giusto?»)
sono la diagnosi: i PROCESSI sono giusti e testati, ma la UI non li
RACCONTA — e un processo che non si capisce non è consolidato, anche
se i test sono verdi.*

---

## 1 · Lo stato di fatto (verificato)

| Domanda | Risposta | Dove sta la prova |
|---|---|---|
| Come si condivide? | Le mie tracce → pubblica riservata → pannello link → contatto → crea/copia/WhatsApp | CondivisioniTraccia + test share |
| Un operatore può finire nelle Meditazioni? | NO: UI un solo pulsante; server 403 sul publish pubblico | portiere visibilità + «chiedere il pubblico è un 403» |
| Chi pubblica nelle Meditazioni? | SOLO chiave 1 (founder+Valentina) | «test di Valentina» + muro catalogo/sitemap/SEO |
| Come si revoca? | Revoca sul singolo link: quel contatto si spegne subito | revoca chirurgica, testata |
| Il cliente vede la Lettera? | NO: /ascolta/{token} non conosce il cerchio | canali fisicamente separati — MA senza guardia (→ TM4) |

## 2 · I difetti veri (la parte da sistemare)

**A. Il lessico dei gesti non dice cosa succede.** Per la chiave 1 i
pulsanti dicono «Pubblica» / «Riservata»: il primo manda la traccia
NELLE MEDITAZIONI PUBBLICHE senza nessuna conferma — un click
distratto del founder e una bozza è in vetrina a tutti gli iscritti.
Per la chiave 2 «Pubblica riservata» è meglio ma ancora gergo.

**B. La scheda è affollata e gerarchicamente piatta.** Sotto ogni
traccia: × (elimina, minuscolo ma distruttivo), Copia link, Ritira,
Pubblica, Riservata, Apri — sei gesti sullo stesso rango, più il
pannello condivisioni SEMPRE aperto per le riservate (rumore quando i
link sono tanti o zero).

**C. L'isolamento cliente/cerchio è vero ma non guardato.** Nessun
test impedisce a un refactor futuro di importare il cerchio dentro
/ascolta o di far passare gli share dal cancello Lettera.

## 3 · Le onde

- **TM1 — il lessico dei gesti** (½ giornata):
  - chiave 1: i due pulsanti diventano **«Nelle Meditazioni»** e
    **«Riservata ai clienti»**; il primo apre una CONFERMA esplicita
    («Questa traccia andrà nelle Meditazioni pubbliche di Aurya,
    visibile a tutti gli iscritti. Pubblicare?») — il gesto pubblico
    non deve mai essere un click distratto;
  - chiave 2: un pulsante solo, **«Pubblica per i tuoi clienti»**;
  - «Ritira» dice da dove: «Ritira dalle Meditazioni» / «Riporta in
    bozza» (riservata);
  - lo stato in scheda parla: PUBBLICA → «Nelle Meditazioni · N
    ascolti», RISERVATA → «Riservata · N link attivi».

- **TM2 — la scheda ridisegnata** (1 giornata):
  - gerarchia: UN gesto primario per stato (bozza→pubblica,
    riservata→gestisci link, pubblica→copia link), i secondari
    discreti, l'ELIMINA fuori dalla riga (angolo, ghost, con
    conferma già esistente);
  - il pannello condivisioni diventa RIPIEGABILE: una riga
    «Link riservati (2) ▸» che si apre solo quando serve, col
    conteggio degli attivi sempre visibile;
  - il pannello dentro: contatto, contatori (ascolti · ultimo),
    Copia/WhatsApp/Revoca come gesti chiari, «Crea link» in testa;
  - vestito Ora d'oro: carte di vetro coi raggi nuovi, niente
    pulsantini mono-uppercase da console per i gesti primari.

- **TM3 — il muro del pubblicare, anche in UI** (¼ giornata):
  guardie nuove — il pulsante pubblico esiste SOLO dentro il ramo
  `user?.sound_composer` (statico), la conferma esplicita esiste, e
  il testo del pulsante nomina le Meditazioni (mai più un «Pubblica»
  nudo). Il 403 server resta la frontiera vera (già testato).

- **TM4 — l'isolamento del cliente, guardato** (¼ giornata):
  guardie — AscoltaPage non importa MAI lib/cerchio ne' nomina la
  newsletter/Lettera; la rotta /condivise non tocca
  `_has_catalog_access`; il payload dello share non contiene inviti.
  Decisione founder inclusa: la topbar su /ascolta resta (marchio +
  uscite) ma senza passerella? → proposta: tenerla com'è (il cliente
  può scoprire Aurya Sound: è funnel buono, non cancello).

- **TM5 — il collaudo del racconto** (½ giornata): a schermo, col
  demo — bozza → «Riservata ai clienti» → link a Marco → /ascolta
  suona → revoca → messaggio neutro; poi «Nelle Meditazioni» con la
  conferma → appare in /meditazioni → «Ritira dalle Meditazioni» →
  sparisce. E da operatore chiave-2: UN solo pulsante, mai la parola
  Meditazioni nei suoi gesti.

## 4 · Fuori scope

Analytics per link oltre i contatori, scadenza automatica dei link,
invio email dalla piattaforma, permessi per-membro del team.
