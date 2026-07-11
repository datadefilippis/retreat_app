# Strategia SEO olistica — Aurya (luglio 2026)

> Obiettivo: diventare il portale numero uno in Italia per ritiri olistici,
> operatori olistici, benessere e discipline olistiche. Budget marketing
> minimo → la SEO è il canale primario di acquisizione, e va accesa ORA
> (in pre-lancio), perché i risultati organici hanno 3-6 mesi di latenza.

---

## 1. Dove siamo oggi (audit)

### Fondamenta tecniche (già costruite, sopra la media del settore)
| Asset | Stato |
|---|---|
| SEO shell server-side (title/description/OG per pagina, no JS richiesto) | ✅ live |
| JSON-LD: Event, LocalBusiness geo, FAQPage, ItemList, BreadcrumbList | ✅ live |
| Sitemap index (core, retreats, products, operators, articles) + lastmod | ✅ live |
| hreflang ×4 (it/en/de/fr) + html lang dinamico | ✅ live |
| IndexNow su publish/update | ✅ live |
| CWV: bundle 505KB gz, lazy admin, WebP pipeline, fetchpriority hero | ✅ live |
| Blog engine con SEO industriale + cover autogenerate | ✅ costruito, **vuoto e nascosto** |
| Recensioni verificate (futuro Review schema) | ✅ costruito |
| Tracking first-party page_views con attribuzione canale (no cookie) | ✅ live |

### Il problema vero: superficie indicizzabile ≈ zero
In pre-lancio abbiamo (scelta giusta) messo `noindex` su directory,
operatori, destinazioni e blog. Oggi Google può indicizzare SOLO:
`/` (splash), `/cerca-ritiro`, `/per-operatori`, `/chi-siamo`,
`/come-funziona`, legal. Sei pagine. Dominio nuovo, zero backlink,
zero contenuti informazionali. **La leva disponibile SUBITO è il blog:**
è l'unica superficie che possiamo riempire e indicizzare senza
compromettere l'onestà del pre-lancio.

Decisione founder (11/7): il blog, una volta partito, resta attivo
anche in pre-lancio e per sempre. Implementazione: togliere BlogGate +
togliere `blog` dai noindex (2 righe, guardie da aggiornare) **appena
i primi 5 articoli sono pubblicati** — un blog vuoto indicizzato fa
più danno che bene.

### Cosa manca (azioni founder)
- [ ] **Google Search Console**: verifica dominio (DNS TXT su aurya.life) e submit sitemap.xml — senza GSC voliamo alla cieca
- [ ] **Bing Webmaster Tools**: importa da GSC (IndexNow è già attivo, Bing lo consuma)
- [ ] Profilo LinkedIn/Instagram del brand linkato dal footer (segnali entità)

---

## 2. Analisi della concorrenza (SERP italiane, luglio 2026)

### I 4 modelli in campo

| Player | Modello | Forza SEO | Debolezza | Cosa impariamo |
|---|---|---|---|---|
| **EventiYoga.it** | Listing a pagamento (per evento o abbonamento annuale), NO booking online | Dominante: occupa 4-6 risultati in prima pagina su "ritiri yoga", blog enorme (guide per regione, per mese, glossario discipline), ~1M visite/anno dichiarate | Solo yoga-centrico; nessuna prenotazione (contatto diretto); monetizza l'operatore ma non gli porta transazioni | Il loro blog È il playbook: guide "ritiri yoga [regione]", "vacanze yoga [mese]", articoli "reiki cos'è", "costellazioni familiari". Copiare la struttura, superarla in ampiezza olistica |
| **OlisticMap.it** | Directory storica operatori/scuole/eventi olistici, iscrizione gratuita | Autorità di dominio anziana, pagine operatore per disciplina×città, news site collegato (news.olisticmap.it), copre TUTTE le discipline | UX datata, nessuna prenotazione, nessuna recensione verificata, schede statiche | Le loro pagine programmatiche disciplina×città sono il modello per la nostra fase local SEO. E la loro directory è un backlink da prendere (iscrizione gratuita) |
| **ItaliaOlistica.it** | Calendario eventi olistici con filtri regione/provincia | Presidia "eventi olistici [regione]" | Solo calendario, no profili ricchi, no booking | Conferma la domanda per il filtro geografico |
| **BookRetreats / Tripaneer (BookYogaRetreats)** | Marketplace internazionale CON booking, 319+ ritiri in Italia | Autorità enorme su query inglesi ("yoga retreat italy"), listing con recensioni e prezzi | **Debolissimi in italiano**: pagine tradotte male o assenti, zero contenuto informazionale in italiano; commissioni percepite alte dagli operatori | La battaglia in ITALIANO è aperta: nessun marketplace transazionale la presidia. Noi siamo l'unico player nativo italiano con booking vero |

Attori minori: ViaggiYoga/Holidayoga/Vawanda (agenzie viaggio verticali),
blog di singole strutture (es. alberimaestri.eu che ranka con guide sui
ritiri spirituali → dimostra che il contenuto in questa nicchia ranka
facilmente, la concorrenza editoriale è battibile).

### La nostra finestra strategica
Nessuno in Italia combina: **directory olistica completa + prenotazione
online con caparra + recensioni verificate + gestionale per l'operatore**.
EventiYoga ha il traffico ma non la transazione; OlisticMap ha l'ampiezza
ma non la modernità; Tripaneer ha la transazione ma non l'italiano.
Il posizionamento SEO ricalca il posizionamento prodotto: **"la casa dei
ritiri olistici"** = ampiezza olistica di OlisticMap + macchina contenuti
di EventiYoga + booking di BookRetreats, in italiano nativo.

---

## 3. Mappa keyword (per intento)

Volumi stimati qualitativamente (Alto/Medio/Basso); da validare in GSC
appena arrivano le prime impression. Priorità = volume × pertinenza ×
vincibilità.

### A. Transazionali / commerciali → directory (al lancio)
| Cluster | Esempi | Vol. | Priorità | Pagina target |
|---|---|---|---|---|
| Ritiri yoga | ritiri yoga italia, ritiro yoga weekend, vacanze yoga | Alto | ★★★ | /ritiri/yoga (+regioni) |
| Ritiri per regione | ritiri yoga toscana/puglia/umbria/sicilia | Medio | ★★★ | /ritiri/{cat}/{regione} (già programmatiche) |
| Ritiri meditazione/silenzio | ritiro meditazione, ritiro spirituale italia, vipassana italia | Medio-Alto | ★★★ | /ritiri/meditazione |
| Detox & digiuno | ritiro detox, digiuno consapevole | Medio | ★★ | /ritiri/detox |
| Femminile | cerchio di donne, ritiro per donne | Medio | ★★ | /ritiri/cerchi-femminile |
| Stagionali | ritiri yoga agosto/capodanno/pasqua | Medio | ★★ | guide blog → directory filtrata |
| Brand-defining | ritiri olistici, vacanze olistiche | Basso-Medio | ★★★ | home + /ritiri — parola che DOBBIAMO possedere al 100% |

### B. Local / operatori → pagine operatore e disciplina×città (fase 2)
"operatore olistico [città]", "reiki [città]", "massaggio sonoro [città]",
"campane tibetane [città]", "costellazioni familiari [città]".
OlisticMap vive di queste; noi le vinceremo con schede più ricche
(recensioni verificate + prenotabilità). Richiede massa critica di
operatori → post-lancio.

### C. Informazionali → blog (SUBITO, in pre-lancio)
| Cluster | Esempi | Vol. | Note |
|---|---|---|---|
| Glossario discipline | reiki cos'è, sound healing, breathwork, costellazioni familiari, bagno di gong, oracoli e tarocchi evolutivi, tema natale | Alto | EventiYoga ranka su tutte; SERP battibili con E-E-A-T vero (Valentina è operatrice) |
| Guide alla scelta | come scegliere un ritiro, quanto costa un ritiro yoga, cosa portare a un ritiro, ritiro da soli | Medio | Intent caldissimo, porta dritto alla lead landing |
| Benessere/percorsi | cosa significa olistico, routine benessere, meditazione per iniziare | Alto ma competitivo | Long-tail specifiche, non testa |
| Luoghi | dove fare un ritiro in toscana/puglia, masserie per ritiri | Medio | Ponte verso /destinazioni |

### D. B2B operatori → blog "Per operatori" (lead gen fondatori, SUBITO)
"come promuovere un ritiro", "come riempire un ritiro yoga", "quanto far
pagare un ritiro", "caparra ritiro come funziona", "gestione prenotazioni
ritiri", "operatore olistico normativa legge 4/2013", "come diventare
operatore olistico". Volume basso ma **intent perfetto per i lead
operatore**: chi cerca queste cose è il nostro cliente fondatore.
EventiYoga lo fa già ("come trovare nuovi allievi") → conferma che
funziona.

---

## 4. Architettura SEO on-site

```
aurya.life
├── / (home: "la casa dei ritiri olistici" → kw brand-defining)
├── /ritiri + /ritiri/{categoria} + /ritiri/{categoria}/{regione}   [programmatiche, ESISTONO, noindex fino al lancio]
├── /operatori + /operatori/{categoria}                             [ESISTONO, idem]
├── /destinazioni/{luogo}                                           [ESISTONO, idem]
├── /o/{operatore}  → LocalBusiness + Review schema                 [ESISTONO, idem]
├── /e/{org}/{ritiro} → Event schema + offers                       [ESISTONO, idem]
├── /blog → IL MOTORE DEL PRE-LANCIO                                [acceso appena 5 articoli pronti]
│    ├── categoria: Ritiri (guide scelta/regioni/stagioni)
│    ├── categoria: Discipline (glossario olistico)
│    ├── categoria: Percorsi (benessere, firma Valentina)
│    └── categoria: Per operatori (B2B)
└── [fase 3] /discipline/{disciplina} hub programmatici:
     cos'è + benefici + FAQ + operatori correlati + ritiri correlati
     (il ponte informazionale→transazionale che nessun competitor ha)
```

Regole di internal linking: ogni articolo → 1 link alla landing lead
pertinente (in pre-lancio) o alla pagina directory (al lancio) + 2-3
link ad articoli fratelli; ogni pagina directory → guida blog correlata
(già impostato con SEO3c/S5, estendere al blog).

---

## 5. Piano editoriale Blog/Magazine

### Principi
- **E-E-A-T reale**: gli articoli sulle discipline firmati da Valentina
  (operatrice olistica vera, bio autore con foto → la stessa credibilità
  della pagina Chi siamo). Quelli B2B e "come funziona" firmati da Davide.
  Box autore su ogni articolo.
- Formato: 1.200-1.800 parole, H2/H3 puliti, FAQ finale (FAQPage schema
  già supportato), 1 immagine originale + cover autogenerata, CTA
  contestuale alla landing lead.
- Cadenza sostenibile: **2 articoli/settimana** (1 disciplina/percorsi +
  1 ritiri/operatori). Meglio 2 a settimana per un anno che 8 al mese
  per due mesi.
- Zero trattini lunghi, voce del brand (evocativa, umana, onesta).

### I primi 10 articoli (mese 1) — ordine di pubblicazione
| # | Titolo (kw target) | Cluster | Perché subito |
|---|---|---|---|
| 1 | Ritiri olistici in Italia: cosa sono e come scegliere quello giusto | Ritiri | La keyword identitaria: definiamo NOI la categoria |
| 2 | Reiki: cos'è, come funziona una sessione, cosa si sente (firma Valentina) | Discipline | Volume alto, expertise autentica in casa |
| 3 | Quanto costa un ritiro yoga in Italia (e cosa è incluso davvero) | Ritiri | Intent pre-acquisto, nessuno risponde onestamente coi numeri |
| 4 | Come promuovere un ritiro e riempire i posti: guida per operatori | Per operatori | Lead magnet B2B per i fondatori |
| 5 | Bagno di gong e sound healing: benefici e cosa aspettarsi | Discipline | Trend in crescita, SERP debole |
| 6 | Ritiri yoga in Toscana: guida alle esperienze e ai luoghi | Ritiri | La regione col volume più alto |
| 7 | Cerchi di donne: cosa sono, come funzionano, come trovarne uno | Discipline | SERP quasi vuota, community fortissima |
| 8 | Caparra e cancellazioni nei ritiri: guida onesta per chi organizza | Per operatori | Posiziona il nostro modello di trasparenza |
| 9 | Cosa portare a un ritiro: la lista completa (e cosa lasciare a casa) | Ritiri | Long-tail facile, ottimo per link interni |
| 10 | Lettura del tema natale: a cosa serve e come si svolge (firma Valentina) | Discipline | Expertise Valentina, differenziante |

### Mesi 2-3 (indicativo, 16 articoli)
Discipline: breathwork, costellazioni familiari, meditazione vipassana,
detox e digiuno consapevole, tarocchi e oracoli come strumento evolutivo,
campane tibetane. Ritiri: Puglia, Umbria, Sicilia, ritiri weekend vicino
a Milano/Roma, ritiro da soli è per me?, ritiri di capodanno. Per
operatori: recensioni come asset, prezzo giusto di un ritiro, gestire i
no-show. Percorsi: iniziare a meditare, il significato di olistico.

### Flusso di lavoro
Bozze scritte insieme (io preparo struttura+bozza SEO, Valentina/Davide
rivedono con la loro voce e esperienza → l'autenticità non si delega),
pubblicazione dall'ArticleEditor admin esistente, IndexNow spara in
automatico.

---

## 6. Off-page con budget zero

1. **Directory di settore** (backlink gratuiti, DA anziana): OlisticMap
   (iscrizione gratuita), ItaliaOlistica, directory locali/camere di
   commercio, Trustpilot (profilo).
2. **Operatori fondatori come rete di link**: badge "Prenotabile su
   Aurya" da mettere sui LORO siti (link in ingresso naturale e a tema).
   Da offrire nel programma fondatori.
3. **Digital PR della storia**: "due fondatori, un'operatrice olistica e
   un tecnologo, costruiscono la casa italiana dei ritiri" → pitch a
   blog/podcast di settore benessere e a media startup (StartupItalia,
   Millionaire). Un solo articolo buono vale 50 directory.
4. **Guest post mirati**: 1/mese su blog benessere italiani (in cambio:
   visibilità reciproca, non denaro).
5. **Associazioni di categoria** (SIAF, CSEN settore olistico): presenza
   nelle loro risorse per operatori = link .org autorevoli + canale lead.

## 7. Misurazione (senza cookie, coerente col nostro posizionamento privacy)

- **GSC**: impression, click, posizione media su 20 keyword sentinella
  (le testa di ogni cluster della sezione 3) — review quindicinale.
- **First-party page_views** (già live, VT1/VT2): traffico organico per
  pagina via canale `search`, conversione articolo→landing→lead.
- **KPI pre-lancio (90 giorni)**: 25+ articoli pubblicati e indicizzati,
  prime 10 keyword informazionali in top 20, 100+ click organici/mese,
  ≥10% dei lead con origine organica.
- **KPI lancio (+90 giorni)**: directory indicizzata, "ritiri olistici"
  top 3, 3+ cluster regionali in top 10, prime prenotazioni da organico.

## 8. Roadmap operativa

**Fase 0 — questa settimana (pre-lancio)**
1. GSC + Bing Webmaster: verifica dominio, submit sitemap *(founder)*
2. Scrivere e pubblicare i primi 5 articoli (lista sopra)
3. Accendere il blog: via BlogGate, via noindex blog, voce menu/footer
   ripristinata (2 righe + guardie) — il blog resta acceso PER SEMPRE
4. Iscrizione directory OlisticMap/ItaliaOlistica/Trustpilot

**Fase 1 — pre-lancio, settimane 2-12**
5. Cadenza 2 articoli/settimana (piano sezione 5)
6. Badge fondatori + primi guest post + pitch digital PR
7. Review GSC quindicinale, aggiustare i titoli in base alle query reali

**Fase 2 — al lancio (flag OFF)**
8. Il noindex directory sparisce da solo col flag → submit sitemap
   aggiornata, IndexNow di massa
9. Review schema sulle recensioni verificate (rich snippet ★ nelle SERP)
10. Interlink blog→directory (i 25+ articoli spingono PageRank alle
    pagine transazionali dal giorno uno: QUESTO è il vantaggio di aver
    iniziato in pre-lancio)

**Fase 3 — post-lancio**
11. Hub /discipline/{disciplina} programmatici (info→transazione)
12. Pagine disciplina×città quando c'è massa di operatori
13. Espansione EN via hreflang (già pronto) per "yoga retreat italy":
    lì sfidiamo Tripaneer sul loro terreno, ma con inventario italiano
    autentico
