# Strategia prodotto, monetizzazione e scala del valore — analisi PO/marketing

**Data:** 2026-07-07 · **Contesto:** pre-lancio, GTM manuale (founder contatta gli operatori uno a uno, ingresso profilo-first).

---

## PARTE 1 — Cosa abbiamo davvero in mano (inventario del valore)

### Per l'operatore olistico (il cliente pagante)
Il prodotto oggi risolve QUATTRO dolori reali, in un'unica app in 4 lingue:
1. **Farsi trovare** — directory/calendario pubblico SEO-industriale (sitemap, hreflang, JSON-LD, IndexNow, aggregatori per destinazione/esperienza/operatore) + profilo-vetrina con recensioni;
2. **Farsi pagare** — caparre/saldi/rate con link di pagamento, scadenzario, solleciti WhatsApp/email a un click, tesoreria unificata (anche incassi fuori piattaforma);
3. **Non impazzire con gli strumenti** — gestionale completo (ordini multi-anima, partecipanti/QR, CRM, newsletter, POS, dati manuali) al posto di Excel+WhatsApp+Wix+Calendly;
4. **Costruire fiducia** — recensioni verificate SOLO da chi ha davvero prenotato (OTP su email dell'ordine): un asset che i competitor directory non hanno con questo rigore.

### Per l'utente finale della directory
1. **Trovare** ritiri per data/regione/categoria/prezzo in italiano (nessuno lo fa bene in Italia);
2. **Fidarsi** — recensioni verificate, prezzi e caparre trasparenti, pagamento protetto;
3. **Semplicità** — Passaporto: un solo account per tutti gli operatori, biglietti QR, storico.
Il valore lato domanda È il prodotto lato offerta: ogni operatore che entra rende la directory più utile, ogni visitatore in più rende l'abbonamento più prezioso. Il flywheel esiste; va innescato.

## PARTE 2 — Mercato e competitor

| Competitor | Modello | Debolezza per noi sfruttabile |
|---|---|---|
| BookRetreats / Tripaneer (BookYogaRetreats) | Directory globale, commissione ~15-20% sul prenotato | Costosissimi, inglese-first, zero gestionale, l'operatore è un listing |
| Retreat Guru | Directory + software | Software pesante, USD, pensato per centri grandi; Italia non presidiata |
| Eventbrite / ticketing | Fee su biglietti | Nessuna semantica ritiro (niente caparre/rate), zero directory di nicchia |
| Bókun/Regiondo (experiences) | SaaS + channel | Tour/attività, non ritiri; nessuna community olistica |
| Fai-da-te (Wix+Stripe+Excel+WhatsApp) | ~30-60€/mese di tool sparsi | Il vero incumbent: il nostro Gratis lo batte su costo E funzioni |

**Differenziazione (dove vinciamo):** (a) fee 5% vs 15-20% delle directory — dirompente nel pitch («con loro un ritiro da 800€ ti costa 120-160€, con noi 40€, e a Pro 16€»); (b) unica offerta directory+gestionale in italiano per l'olistico; (c) multi-anima (ritiri+consulenze+prodotti+digitale+corsi) = tutta la vita economica dell'operatore in un posto; (d) recensioni verificate come moat di fiducia.

## PARTE 3 — La monetizzazione: dove guadagniamo e dove NON guadagniamo

### Il buco che hai visto è vero (verificato nel codice)
`application_fee_percent` viene applicato SOLO in `payment_checkout_service` (checkout Stripe). Ordini manuali, mark-paid (contanti/bonifico), POS, entrate della pagina Dati: **ricavo piattaforma = 0**. E con i cicli CG/RF abbiamo reso il gestionale off-Stripe *eccellente* — cioè abbiamo reso comodissima la via che non ci paga. Un operatore razionale sul Gratis può usare la directory per i contatti e chiudere tutto fuori.

### Ma attenzione: NON è (solo) un bug, è una scelta di design da governare
Il gestionale gratuito è l'esca giusta (batte il fai-da-te, crea lock-in sui dati). Il problema non è che il manuale non paghi fee — è che **il canale marketplace non è ancora obbligatoriamente on-platform** e che **gli incentivi a restare on-platform non sono espliciti**. Tre leve, in ordine di forza:

1. **Regola di canale (policy, non punizione):** ciò che arriva DALLA directory si prenota SULLA piattaforma. Il calendario pubblico già porta al checkout con caparra — va reso l'unico percorso: sulla landing marketplace la prenotazione è LA cta, il contatto diretto dell'operatore non è esposto prima della prenotazione (standard di ogni marketplace serio). Il gestionale resta libero per il flusso proprio dell'operatore (suo sito, telefono, banco): lì la fee non c'è e non ci deve essere — «paghi solo quando ti portiamo noi il cliente».
2. **Il moat delle recensioni come incentivo economico:** le recensioni verificate nascono SOLO da ordini in piattaforma (già così!). Messaggio all'operatore: ogni prenotazione portata fuori è una recensione che non avrai mai, visibilità che non accumuli. Rendiamolo esplicito nel prodotto (nudge post-vendita manuale: «questa vendita non genererà una recensione verificata») e nel pitch.
3. **Passaporto/caparra come valore per il cliente finale:** rate gestite, QR, storico, tutela — il compratore stesso preferisce prenotare in piattaforma. Più il checkout è meglio dell'IBAN su WhatsApp, meno leakage esiste.

### La matematica Gratis vs Pro (la tua sensazione è corretta)
Break-even: 29€/mese ÷ (5%−2%) = **~967€/mese di transato Stripe**. Sotto ~1.000€/mese il Gratis conviene; sopra, il Pro si ripaga da solo (a 3.000€/mese risparmi 61€/mese netti). Questo NON è un difetto: è una scala sana **se** la raccontiamo così e **se** la fee viene effettivamente catturata (v. sopra). Il Pro oggi soffre perché: (a) il leakage rende la fee evitabile → il risparmio-fee non attrae; (b) le voci qualitative erano deboli (una era vuota, l'abbiamo tolta; featured era solo testo, ora è vero).

### "Evidenza nel calendario pubblico" — cosa significa ORA (dopo MD3) e cosa deve diventare
Oggi (costruito ieri): badge ✦ sulla card + priorità a parità di giorno nel calendario e nel sort geografico. È onesto ma tenue. Per farne una leva Pro percepibile va esteso: **(1)** sezione "In evidenza" in testa alla directory e alle pagine categoria/destinazione; **(2)** priorità nell'aggregatore operatori; **(3)** badge sul profilo operatore. La distinzione col Gratis è: *tutti sono in directory* (è il patto d'ingresso), *i Pro sono visti per primi* — come le inserzioni in testa su Booking, ma dichiarate e discrete.

## PARTE 4 — Posizionamento prezzi e piani (raccomandazione)

**Gratis (il cavallo di Troia, resta generoso):** «Tutto per lavorare. Paghi il 5% solo sulle prenotazioni che ti porta il marketplace.» Non togliere feature al Gratis: il costo marginale è zero, il lock-in sui dati è la vera conversione, e il fai-da-te si batte solo così.

**Pro 29€ (il piano per chi fattura):** riposizionarlo come **"fee saver + visibilità"**: fee 2%, In evidenza (potenziato), 3 store, team 5, catalogo illimitato. Il venditore del Pro dev'essere il prodotto stesso: **banner-calcolatore onesto in /incassi** quando il transato Stripe supera la soglia: «Questo mese hai processato 1.850€ online: col Pro avresti risparmiato 26€. Passa a Pro». Si converte da solo esattamente quando conviene davvero — coerente con la nostra filosofia realtà-dei-dati.

**Founding (leva GTM):** perfetto per la fase contatti 1-a-1: «tutto Pro gratis 3 mesi, mi dai feedback settimanale». Usalo come default per i primi 10-20 operatori.

**Non fare:** paywall sugli insight (uccide l'essenzialità), canone d'ingresso (uccide il funnel), fee sul gestionale manuale (uccide il wedge e la fiducia).

## PARTE 5 — La scala del valore per il TUO GTM (profilo-first, step by step)

Il principio: **ogni gradino deve dare valore da solo, in <15 minuti, senza chiedere il gradino dopo.**

| Gradino | Cosa attivi | Valore immediato percepito | Trigger per il gradino dopo |
|---|---|---|---|
| **0 — Vetrina** (giorno 1) | Profilo pubblico (foto, bio, lingue, link) + presenza in directory/aggregatori | «La tua pagina professionale, in 4 lingue, indicizzata su Google — gratis, 10 minuti» — nessuno Stripe, nessun prodotto | «Vuoi che il prossimo ritiro compaia nel calendario?» |
| **1 — Calendario** | Primo ritiro pubblicato + landing prenotabile con caparra (qui serve Stripe Connect) | Prenotazioni online con caparra automatica; il cliente riceve QR e Passaporto | La prima prenotazione vera |
| **2 — Soldi in ordine** | /incassi + scadenzario + solleciti one-click; pagina Dati per gli incassi fuori | «Sai sempre chi ti deve cosa, e il sollecito è già scritto» | Il primo ritiro concluso |
| **3 — Fiducia** | Recensioni verificate (banner post-ritiro con richiesta one-click) | Le prime recensioni col badge "Cliente verificato" sulla vetrina | «Hai clienti che tornano?» |
| **4 — L'app completa** | Altre anime (consulenze/prodotti/digitale/corsi), newsletter, CRM+cross-sell, team, POS | «Da cosa guadagni» per anima, cross-sell suggerito, tutta l'attività in un posto | Il calcolatore fee → Pro |

Nota di prodotto: il gradino 0 già esiste tecnicamente pulito (signup → moduli attivi → editor profilo). Va solo protetto: l'onboarding /inizia non deve costringere a creare store/prodotti per avere la vetrina.

## PARTE 6 — Azioni conseguenti proposte (backlog GT, da approvare)

- **GT1 — Canale marketplace on-platform:** sulla landing pubblica del ritiro la prenotazione è l'unica CTA; contatti diretti dell'operatore visibili solo post-prenotazione (o su profilo, non su landing con checkout attivo). ~½ giornata.
- **GT2 — Calcolatore fee→Pro in /incassi:** transato Stripe mensile × 3% vs 29€, banner onesto solo sopra soglia. ~½ giornata.
- **GT3 — Featured potenziato:** sezione "In evidenza" in testa a /ritiri e pagine categoria/destinazione + priorità aggregatore operatori + badge profilo. ~1 giornata.
- **GT4 — Nudge recensioni-moat:** su mark-paid manuale, hint discreto «gli incassi manuali non generano recensioni verificate — porta la prossima prenotazione sul calendario». ~2 ore.
- **GT5 — Copy pricing riscritta** secondo Parte 4 (Gratis = paghi quando incassi dal marketplace; Pro = fee saver + visibilità) ×4 lingue. ~2 ore.
- **GT6 — Onboarding profilo-first:** checklist /inizia con gradino 0 completabile senza store/prodotti. ~½ giornata.

Con GT1+GT2 la monetizzazione smette di essere aggirabile-per-caso e il Pro si vende da solo al momento giusto. GT3-GT6 sono l'allineamento del racconto.
