# Piano sito-rete — Aurya (16 luglio 2026)

> Ribrand del sito pubblico: da "marketplace in pre-lancio" a **sito della
> rete** che dà valore dal primo giorno, anche senza operatori prenotabili.
> Un solo sito che cresce a blocchi: gli URL non cambiano mai, i contenuti
> si arricchiscono fase dopo fase. Sostituisce la coppia
> "sito pre-lancio / sito lancio" con un'unica superficie a fasi.

## 0. La diagnosi (perché questo piano)

- 400 follower Instagram, pochi contatti dal sito: chi arriva non trova
  valore (vetrina di campioni oscurati = nessun motivo per restare).
- Chiedere a un operatore di iscriversi a una piattaforma vuota crea
  resistenza. Invertire l'offerta: **prima diamo noi valore a loro**
  (intervista + profilo pubblico indicizzato + visibilità Instagram),
  poi, a rete viva, si vende la piattaforma.
- Il funnel diventa: Instagram → sito (Magazine/Newsletter) → iscritto →
  scopre operatori → contatta. E per gli operatori: Instagram/outreach →
  Manifesto → Operatori → candidatura → intervista → membro della rete.

## 1. Cosa esiste GIÀ nel codice (asset da riusare, non ricostruire)

| Pagina del piano | Asset esistente | Delta da fare |
|---|---|---|
| /journal | **Magazine /blog: 19 articoli live e indicizzati**, cover, JSON-LD completo, IndexNow, sitemap | NIENTE rename: /blog resta (URL indicizzati = capitale SEO). Etichetta resta "Magazine" |
| /manifesto | /chi-siamo con sezione founders (foto+testo) + /come-funziona | Nuova pagina /manifesto che assorbe /chi-siamo (301) |
| /operatori/[slug] | **Profilo pubblico operatore completo** (/o/slug): bio multilingua, gallery, social, SEO LocalBusiness, recensioni | Aggiungere la sezione INTERVISTA al modello + editor |
| /operatori | Aggregatore /operatori (ora redirect in prelaunch) | Trasformare in landing "la rete" + schede membri |
| /entra-nella-rete | Landing /per-operatori con form lead strutturato (telefono, località, attività, descrizione) + admin Lead + CSV | Nuovo copy candidatura + campi extra + URL nuovo con 301 |
| /newsletter | **Modulo Newsletter completo**: form embeddabili, iscritti in Customer Insights, GDPR | Landing pubblica /newsletter + lead magnet scaricabile |
| Home | Splash prelaunch 2 CTA | Home nuova a blocchi (vedi §3) |
| SEO/infra | Shell server-side, sitemap index, hreflang, llms.txt, GA4 Consent v2, 404 veri | Aggiornare gate noindex + redirect + eventi conversione |

Conclusione: delle 9 pagine del piano, 6 hanno fondamenta già in
produzione. Il lavoro vero è: manifesto, interviste sul profilo, ricablare
i gate di fase.

## 2. Divergenze deliberate dal piano di partenza

1. **/blog resta /blog** (etichetta "Magazine", scelta founder del 10/7).
   Rinominare in /journal butterebbe 19 URL indicizzati + segnali
   accumulati per un guadagno puramente estetico. Il piano incollato non
   sapeva che il blog esiste già con 19 pezzi sopra la soglia qualitativa.
2. **La soglia "4 articoli prima di aprire il Journal" è già superata**
   (19 pubblicati, piano editoriale 48 + 7 onde in docs/MAGAZINE_...).
3. **/chi-siamo → 301 → /manifesto**: una sola pagina identitaria, non
   due. Il contenuto founders (foto, percorso, testo coppia) migra nel
   Manifesto. /come-funziona resta finché parla del marketplace, ma esce
   dal menu in fase Rete.
4. **Campioni pre-lancio: SI ELIMINANO** (wipe_prelaunch_samples.py).
   Il valore ora lo danno contenuti veri; la vetrina di finti operatori
   oscurati è esattamente ciò che non funzionava. Coerente con la
   richiesta "le organizzazioni fake vanno rimosse".
5. **Lingue: già risolto meglio del piano** — l'italiano è a root e il
   sito è già ×4 lingue con hreflang. Nessun lavoro.

## 3. Il meccanismo di fase (uniformare pre-lancio e lancio)

Sostituire il binario PRELAUNCH_MODE true/false con **SITE_PHASE** a tre
valori, runtime via /public/site-config (stesso pattern, zero rebuild):

- `network` ← LA NUOVA FASE. Sito della rete: home a blocchi, Manifesto,
  Magazine, Operatori (rete), Newsletter. Marketplace SPENTO: /ritiri,
  checkout, prezzi, directory prenotabile non esistono per il visitatore.
- `marketplace` ← il lancio: si RIACCENDONO i blocchi transazionali
  (ritiri, prenotazioni, checkout, calendario pubblico) SOPRA il sito
  della rete. Gli URL non cambiano: /operatori guadagna filtri,
  la home guadagna il blocco esperienze.
- `legacy_prelaunch` ← alias di compatibilità del flag attuale, da
  eliminare a migrazione finita.

Regola d'oro (dal piano, confermata): **i blocchi si sostituiscono, gli
URL mai**. Tutte le guardie di regressione esistenti su PRELAUNCH_MODE
migrano su SITE_PHASE.

## 4. Sitemap fase Rete (10 URL, 3 template)

```
/                    Home a blocchi (identità in 10 secondi)
/manifesto           visione + missione + voi due  [pagina più importante]
/blog                Magazine (indice)             [esiste]
/blog/[slug]         Articolo                      [esiste]
/operatori           La rete: cos'è + criterio + schede membri
/o/[slug]            Profilo operatore + INTERVISTA [esiste, si estende]
/entra-nella-rete    Candidatura                   [evoluzione /per-operatori]
/newsletter          Landing iscrizione + lead magnet
/contatti            [esiste nel footer, si formalizza]
/privacy /cookie /termini                          [esistono]
```

Navigazione: `Manifesto · Magazine · Operatori · Newsletter` + CTA
**Entra nella rete**. Niente dropdown. Footer: stesse voci + legal + social.

Redirect 301 da posare: /chi-siamo→/manifesto, /per-operatori→
/entra-nella-rete, /cerca-ritiro→/newsletter (il pubblico viaggiatori si
coltiva in newsletter finché non c'è nulla da prenotare), /ritiri→/ (fase
network). /esperienze, /destinazioni: già gestiti.

## 5. Struttura delle pagine chiave (fase Rete)

### / Home
1. Hero: posizionamento in una frase (non slogan) + CTA newsletter
2. Manifesto in tre righe → /manifesto
3. Ultimi 3 articoli del Magazine
4. Estratto di UN'intervista con volto e nome (quando esiste)
5. Blocco operatori → /entra-nella-rete
6. Newsletter con promessa concreta
Evoluzione a fase marketplace: il blocco 4 diventa "operatori in
evidenza", si aggiunge il blocco esperienze prenotabili.

### /manifesto
Da dove nasce Aurya · cosa non ci convince del settore · cosa vogliamo
costruire · chi siamo (Davide + Valentina, nomi volti percorso — contenuto
già scritto per /chi-siamo, si migra) · UNA riga sugli strumenti digitali
in sviluppo. CTA: entra nella rete. È il filtro di credibilità per gli
operatori: va scritto da voi, non generato.

### /operatori (landing rete, NON directory)
Cos'è la rete · con che criterio si entra · le schede dei membri.
Con 5 schede una landing curata sembra selettiva; una directory con
filtri sembra abbandonata. I filtri arrivano a 25+ profili, URL invariato.
Tecnica: l'aggregatore esistente si riusa; il gate cambia da
"prenotabile online (GT1b)" a **network_member=true** (flag assegnato
dall'admin, come i piani). GT1b resta per la fase marketplace.

### /o/[slug] con intervista
Al profilo pubblico esistente si aggiunge la sezione intervista:
`interview: [{question, answer}]` multilingua sul modello operatore,
editor nel back-office (o compilato da voi in admin per conto loro).
Rendering: foto+nome+disciplina+zona · bio · L'INTERVISTA (6-10 domande
integrali, minimo ~800 parole o non si pubblica) · i servizi · contatti
(sito, social, email — QUI i link esterni sono un regalo, non una fuga) ·
CTA newsletter. Title: `Nome — Disciplina a Città | Aurya` (già così).
Profili membri: INDICIZZATI (è il valore offerto). JSON-LD Person+
LocalBusiness già pronto.

### /entra-nella-rete
Cosa ricevi (profilo gratuito indicizzato, intervista, visibilità
Instagram) · cosa chiediamo (condividere la tua intervista) · come
funziona in 3 passi · tempi reali. Form: riusa il form lead operatore
esistente + campi nuovi: disciplina (tassonomia già esistente), organizza
ritiri sì/no, cerca location sì/no, follower/persone seguite. Ogni
candidatura finisce nell'admin Lead già fatto (tab, CSV, notifica info@).

### /newsletter
Nome proprio, frequenza dichiarata, promessa specifica (decisione
founder, vedi §8). Lead magnet scaricabile post-iscrizione. Tecnica:
modulo Newsletter esistente + pagina landing + consegna del PDF
(link nella mail di benvenuto o pagina di grazie). È la destinazione del
link in bio Instagram.

## 6. Piano di implementazione (onde RT)

**RT0 — Contenuti (founder, in parallelo a tutto):** testo Manifesto;
nome+promessa+frequenza newsletter; lead magnet (1 PDF vero); pipeline
prime 5 interviste (chi, domande standard, foto). Il codice non lancia
senza questi.

**RT1 — Fondamenta di fase:** SITE_PHASE runtime (network/marketplace) al
posto di PRELAUNCH_MODE; migrazione guardie; wipe campioni; redirect 301;
noindex ricablati (profili membri indicizzati, superfici marketplace
spente in fase network).

**RT2 — Identità:** template landing riusabile (hero + blocchi + CTA);
/manifesto con contenuto RT0; home nuova a blocchi; navigazione e footer
nuovi; /chi-siamo→301.

**RT3 — La rete:** modello intervista + editor admin; flag network_member
+ assegnazione da pannello system admin; /operatori landing rete;
rendering intervista sul profilo; /entra-nella-rete con form esteso.

**RT4 — Newsletter:** landing /newsletter; consegna lead magnet;
GA4 `generate_lead` esteso a candidatura rete e iscrizione newsletter
(già evento conversione).

**RT5 — Chiusura:** sitemap/SEO update; guardie di regressione per fase;
suite completa; runbook del flip (si accende quando RT0 è pronto:
manifesto + 5 profili completi + lead magnet — i 4 articoli li abbiamo
già, ×19).

Fino al flip resta live il pre-lancio attuale: si costruisce dietro la
fase, come già fatto con PL.

**Fase marketplace (futuro, invariata):** riaccensione ritiri/checkout
sopra il sito-rete; /operatori guadagna filtri; blocco esperienze in
home; runbook SEO del lancio già scritto nel playbook (sez. 6).

## 7. Percorsi (invariati dal piano, validi)

Utente: Instagram → /newsletter o /blog/[slug] → iscritto → email
ricorrente → scopre operatori → contatta.
Operatore: outreach/IG → /manifesto → /operatori → /entra-nella-rete →
intervista → pubblicazione+condivisione → report visite a 30 giorni
(la pagina Visibilità per-operatore ESISTE GIÀ: quel report è un'email
con i numeri veri del suo profilo).

## 8. Decisioni founder aperte (bloccano RT0/flip, non l'inizio dei lavori)

1. Testo del Manifesto (va scritto da voi; posso preparare la struttura).
2. Nome, promessa e frequenza della newsletter + primo lead magnet.
3. Domande standard dell'intervista (proposta: 8 fisse + 2 libere).
4. Conferma: campioni eliminati subito col flip (vetrina /ritiri sparisce
   fino alla fase marketplace).
5. Conferma etichetta "Magazine" (vs rinominare "Journal" — sconsigliato).

## 9. Cosa NON si costruisce ora (confermato)

/risorse (finché <4 materiali) · /esperienze /eventi (nulla di
prenotabile) · /luoghi (conflitto masseria) · /piattaforma (riattiva la
resistenza diagnosticata) · /community · categorie Magazine come pagine
(finché <6 articoli l'una) · directory con filtri (<25 profili) · /en/
(il multilingua c'è già, l'inglese editoriale è fase 2+).
