# Crea per professionisti — le TRACCE RISERVATE (ciclo TR)

*Piano deciso col founder il 26/8/2026 sera. Contesto: Professional è
uscito dalla vetrina (il catalogo da solo non supera il valore del
premere play; la sua fase due sono le vibrazioni). La via
professionale promossa è CREA: comporre meditazioni proprie e
condividerle in privato coi propri clienti. Questo piano rende quella
promessa un modulo vero.*

---

## 0 · Le decisioni già prese (vincoli, non opzioni)

1. **Nessun conflitto col system admin.** La concessione di
   `sound_composer` — chi può comporre E pubblicare nelle Meditazioni
   pubbliche di Aurya — resta manuale, per-org, dal pannello
   `/admin/sound`, esattamente com'è. Il founder e gli account che lui
   sceglie continuano a pubblicare nel catalogo pubblico.
2. **Esclusione dalla pubblica.** Le tracce dei professionisti del
   modulo NON appaiono mai nelle Meditazioni di Aurya: né catalogo,
   né sitemap, né shell SEO, né profilo pubblico. Mai.
3. **Attivazione e pagamento separati** dal piano attuale (con
   l'analisi «o dentro l'abbonamento» al §4).

## 1 · Il modello: due cappelli, tre visibilità

**Due privilegi distinti, cumulabili per org:**

| Flag | Chi lo dà | Cosa permette |
|---|---|---|
| `sound_composer` (esiste) | system admin, manuale | comporre + pubblicare **nelle Meditazioni pubbliche** |
| `sound_studio` (nuovo) | modulo fatturabile | comporre + pubblicare **solo in riservato** |

Il portiere sta in UN punto (il publish): la visibilità ammessa la
decidono i flag. Chi ha solo `sound_studio` pubblica *forzatamente*
riservato; chi ha `sound_composer` sceglie (default: pubblica, il
flusso del founder non cambia di un pixel). Un org con entrambi ha
entrambe le strade.

**Tre visibilità della traccia** (oggi due: bozza/pubblicata):

- `draft` — come oggi.
- `published` + `visibility: "public"` — come oggi (catalogo, SEO).
- `published` + `visibility: "private"` — master renderizzato, URL
  d'ascolto con **pass firmato nel link**, invisibile a ogni
  superficie pubblica.

## 2 · L'ascolto del cliente finale (fase 1: il link riservato)

Il professionista copia UN link e lo manda al suo cliente (WhatsApp,
email — i canali che il CRM già usa). Il link è:

```
/ascolta/{slug-segreto}?p={pass-firmato}
```

- **slug segreto**: non indovinabile, non listato da nessuna parte;
- **pass firmato**: stesso meccanismo del master-pass esistente
  (`_firma_master_pass`), scope nuovo `fqz_privata`, org nel payload,
  scadenza lunga (90 giorni) e **revoca = rigenera** (il vecchio pass
  muore, il professionista rimanda il link);
- il player è il `PublicFrequencyPage` con un gate diverso: niente
  cerchio/Lettera, niente anteprima 90s — il pass NEL link è lo
  sblocco. Pagina `noindex`, esclusa da sitemap e registro rotte per
  i crawler;
- modello di fiducia dichiarato: come un «non in elenco» di YouTube —
  chi ha il link ascolta. La revoca c'è; il lucchetto per-persona è
  la fase 2 (assegnazione a contatti CRM con verifica email, che
  riusa lo sblocco del cerchio — NON ora).

## 3 · Le onde del ciclo

- **TR0 — le scelte del founder** (mezz'ora, prima di tutto):
  nome pubblico del modulo (proposta: «Crea Studio»), prezzo (vedi
  §4), quota tracce per il pilot (proposta: 10 tracce riservate,
  30 min l'una — i tetti del motore esistono già).
- **TR1 — la visibilità nel modello** (backend): campo `visibility`
  con default `public` (zero migrazioni: assenza = pubblica),
  portiere sul publish guidato dai flag, **esclusione strutturale**
  dal catalogo/sitemap/shell/profilo (il filtro vive nella query di
  base, stile `_mio()`: un posto solo, guardato). Guardie: una
  traccia privata NON esce da `/public/frequencies/catalog` né dalla
  sitemap MAI — test API veri, non fotografie.
- **TR2 — il link riservato**: pass `fqz_privata`, rotta d'ascolto,
  revoca/rigenera, `noindex`. Il master privato passa dallo stesso
  nginx interno (X-Accel) dei pubblici.
- **TR3 — la UI in Crea**: al «Pubblica», la scelta (se ammessa dai
  flag) *Meditazioni di Aurya / Riservata ai miei clienti*; ne «Le
  mie tracce» lo stato, il copia-link e il rigenera. Microcopy
  onesta: «chi ha il link ascolta; rigenera per revocare».
- **TR4 — il modulo fatturabile**: flag `sound_studio` per-org sul
  binario billing-per-modulo già pronto; gating dei 12 endpoint del
  compositore esteso al nuovo flag (`composer OR studio`, con la
  visibilità decisa al publish); `/admin/sound` mostra le due colonne
  (concessione composer manuale + stato modulo studio, sola lettura)
  con audit; voce in usage-summary. **Nel pilot l'attivazione è
  manuale del system admin** e la fattura viaggia fuori piattaforma:
  Stripe arriva quando il prezzo è validato da 2-3 clienti veri.
- **TR5 — i doveri**: quota nel sweep (lezione QF1: soglie a `ceil`,
  niente email legacy), hard delete che porta via anche i master
  privati, riga nei ToS sulla titolarità dei contenuti del
  professionista (le meditazioni che componi restano tue — già
  promesso in landing, va scritto nel legal), privacy: il cliente
  finale ascolta senza account, nessun dato nuovo raccolto.
- **TR6 — il collaudo del confine**: suite dedicata che prova il
  MURO — org solo-studio che tenta il publish pubblico (403), traccia
  privata cercata in catalogo/sitemap/shell/profilo (assente), pass
  scaduto/rigenerato (403 il vecchio), org senza moduli (403 ovunque),
  e il flusso founder invariato (composer pubblica in pubblico come
  oggi).

## 4 · Prezzo: separato o incluso? (analisi e raccomandazione)

- **Incluso nel Pro (19€)**: rende il Pro più ricco, zero attrito.
  Contro: il buyer di Crea Studio *può non essere* un cliente del
  gestionale (partnership, studi che non vendono su Aurya) — legarlo
  al Pro chiude quella porta; e regala il modulo a chi non lo usa.
- **Modulo separato**: prezzo suo (proposta: **14€/mese, 9€ per chi è
  già Pro**), vendibile anche in partnership fuori dal funnel
  gestionale. È la strada coerente con «billing per modulo» già
  costruito e con la natura del prodotto (un atelier, non una feature
  del negozio).

**Raccomandazione: separato, con lo sconto Pro.** Nel pilot il
prezzo è comunque a listino ma incassato a mano: i numeri veri li
diranno i primi tre professionisti.

## 5 · Cosa NON si costruisce ora (dette per non rifarle)

Assegnazione per-cliente con verifica email (fase 2), analytics
d'ascolto per cliente, watermark audio, percorsi/serie assegnabili,
app. E Professional resta com'è: spento in vetrina, intero nel
codice, substrato della fase-vibrazioni.

## 6 · Ordine e stima

TR1+TR2 sono il cuore e stanno insieme (un giorno di lavoro con
guardie). TR3 mezzo giorno. TR4 mezzo giorno (il binario c'è). TR5+TR6
mezzo giorno. Il pilot può aprire con TR1-TR4 e i doveri subito dopo,
prima del deploy.
