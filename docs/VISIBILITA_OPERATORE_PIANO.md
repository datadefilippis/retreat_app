# Visibilità operatore — piano prodotto (VT)

**Data:** 2026-07-09 · **Sostituisce/estende:** TRACKING_VISITE_PIANO.md
**Obiettivo:** dare a ogni operatore uno SPECCHIETTO della visibilità che
Aurya gli produce — impression, visite, provenienza, conversioni — così
la promessa commerciale ("con noi ti trovano") diventa un numero che
l'operatore guarda ogni settimana. È il singolo miglior argomento di
retention e upsell della piattaforma.

---

## 0. Decisione di misurazione (banner modificabile ≠ banner da modificare)

Il founder conferma che il cookie banner SI PUÒ modificare. La
raccomandazione resta però **first-party cookieless per lo specchietto
operatore**, per tre ragioni pratiche e non ideologiche:

1. **Numeri PIÙ ALTI.** Con analytics a consenso (GA4 + banner opt-in)
   il 30-50% dei visitatori rifiuta → lo specchietto mostrerebbe MENO
   visite di quelle vere. La misurazione anonima aggregata senza consenso
   conta ~tutti: la prova per l'operatore è più forte, non più debole.
2. **I dati devono vivere nel NOSTRO db.** Lo specchietto è per-operatore,
   dentro la SUA dashboard, incrociato coi SUOI ordini (`sales_channel`).
   GA4 non sa niente di organization_id, e la sua API ha quote/ritardi:
   andrebbe comunque duplicato tutto internamente.
3. **Zero costi, zero dipendenze, zero consent-fatigue.**

**Quando toccare il banner:** solo se in futuro Aurya vorrà analytics di
MARKETING per sé (campagne, funnel di acquisizione operatori). In quel
caso: consenso separato "statistiche" + Consent Mode, ma è un progetto
indipendente dallo specchietto e non lo blocca. → Fase opzionale VT8.

## 1. Il funnel completo (tre livelli, tutti misurabili da subito)

```
IMPRESSION  →  VISITE  →  PRENOTAZIONI
"sei apparso    "hanno aperto   "hanno prenotato"
nei risultati"   la tua pagina"   (già tracciato: sales_channel)
```

- **Impression** (novità chiave, tipo Search Console): quante volte le
  card dell'operatore compaiono nelle liste — directory /ritiri, pagine
  categoria/destinazione, /operatori. Contate **server-side** negli
  endpoint di listing (`/public/retreats`, `/public/operators`,
  `/public/destinations` detail): +1 per org restituita, batch in memoria
  flushato ogni N secondi. Zero JS, zero impatto latenza percepita.
- **Visite**: ping JS `sendBeacon` da landing `/e/`, profilo `/o/`,
  store `/s/` (architettura del piano precedente, invariata).
- **Prenotazioni**: gli ordini col loro `sales_channel` esistono già —
  si incrociano, non si ricostruiscono.

Il funnel completo dà all'operatore la frase che vale la fee: *"Questo
mese sei apparso 1.240 volte nelle ricerche su Aurya, 218 persone hanno
aperto il tuo ritiro, 12 hanno prenotato."*

## 2. Attribuzione canale

| Sorgente | channel |
|---|---|
| Landing `/e/` aperta con `?store=1` | `store` |
| Landing/profilo con referrer interno Aurya (/, /ritiri, /destinazioni, /operatori, /blog) | `directory` |
| Referrer esterno google/bing | `search` |
| Referrer esterno social (instagram, facebook, tiktok, youtube) | `social` |
| Referrer nullo / altro | `direct` |

Cinque bucket, raccontano una storia chiara: *"Aurya ti porta directory +
search + parte del social; lo store è il TUO canale — e li vedi fianco a
fianco"*. In dashboard si mostrano raggruppati: **via Aurya**
(directory+search) vs **tuo store** vs **altro**.

## 3. Privacy (invariata, nessun cambio banner necessario)

- Visitatori unici: `sha256(ip + UA + day + salt-giornaliero)[:16]`,
  IP mai salvato, salt che ruota → nessun tracciamento tra giorni.
- Referrer: solo hostname. Nessun cookie, nessun localStorage.
- Una riga in privacy policy: "misuriamo in forma aggregata e anonima le
  visualizzazioni delle pagine pubbliche per fornire statistiche agli
  organizzatori". Il banner NON cambia.

## 4. Anti-bot

- Impression: contate server-side ma SOLO su richieste senza UA bot
  (lista: googlebot, bingbot, ahrefs, semrush, gptbot, curl, python,
  headless...).
- Visite: doppio filtro — il ping parte dal JS dopo 3s/primo scroll
  (i crawler no-JS spariscono da soli) + filtro UA server-side + rate
  limit slowapi + dedup visitor_hash per (surface, slug, day).

## 5. Lo specchietto — pagina "Visibilità" dell'operatore

Nuova voce di menu back-office **Visibilità** (modulo con require_module,
pattern MD2) + riassunto nella home operatore.

**Sezione A — Il colpo d'occhio (mese corrente vs precedente)**
- StatCard: Impression · Visite · Visitatori unici · Prenotazioni
  (ognuna con delta % vs mese scorso)
- Donut "Da dove arrivano": via Aurya / tuo store / social / diretto

**Sezione B — Trend**
- TrendArea visite 12 mesi + MiniBars ultimi 30 giorni (kit CF1)

**Sezione C — Per ritiro** (tabella)
- Ritiro · Impression · Visite · Prenotazioni · Conversione % · canale
  dominante. Stessa riga linkata nella Event Dashboard (accanto alla
  timeline vendite CF5).

**Sezione D — La prova Aurya** (il pitch dentro il prodotto)
- Card evidenziata: "Questo mese Aurya ti ha portato **N visite** che
  non avresti avuto dal solo store" (directory+search) — con micro-copy
  onesto e link a /inizia per completare il profilo se scarso.

**Stato vuoto:** sotto ~10 visite/mese niente numeri nudi: "I primi dati
stanno arrivando: completa il profilo per farti trovare" (link editor).
I numeri piccoli non devono MAI imbarazzare.

**Gating piani (proposta):** al lancio TUTTO visibile a tutti — lo
specchietto È la prova di valore e deve convertire al Pro, non essere
nascosto dietro il Pro. Dopo il lancio, eventuale gating morbido: base
(mese corrente) per tutti, storico 12 mesi + per-ritiro + report email
per Pro. Decisione founder, lo schema non cambia.

## 6. Report email mensile "La tua visibilità su Aurya"

Primo del mese, template Salvia&Terracotta esistente (R2b): impression,
visite, prenotazioni, delta, top ritiro, CTA dashboard. È lo specchietto
che arriva DA SOLO nella casella: retention passiva pura. Scheduler
esistente (stesso lock), opt-out nelle preferenze email.

## 7. Vista piattaforma (per il founder)

In SA4 (scheda Operatore 360°): stessa metrica per il pitch commerciale
("ti stiamo già portando X visite/mese"). In SA5 Segnali: nuova regola
"molto traffico + zero Stripe → sbloccalo" e "traffico in calo → nudge".

## 8. Fasi

| Fase | Contenuto | Stima |
|---|---|---|
| VT1 | Collection page_views + endpoint /track (visite) + anti-bot UA + indici + TTL 13 mesi | ½ g |
| VT2 | Hook frontend useTrackView su /e/ /o/ /s/ + attribuzione 5 canali | ½ g |
| VT3 | Impression server-side nei listing (batch+flush) | ½ g |
| VT4 | Rollup giornaliero (scheduler) + GET /analytics/visibility (org-scoped) | ½ g |
| VT5 | Pagina Visibilità (A-D) + widget home operatore + riga Event Dashboard | 1,5 g |
| VT6 | Report email mensile + opt-out + riga privacy policy | ½ g |
| VT7 | Admin: SA4 traffico + segnale SA5 + guardie (no-PII, anti-bot, best-effort) | ½ g |
| VT8 (opz.) | SOLO se serve marketing analytics per Aurya: consenso "statistiche" nel banner + Consent Mode | separato |

Totale VT1-VT7: **~4,5 giornate**. Ordine consigliato: VT1→VT2→VT3 (da
quel momento i dati si ACCUMULANO anche se la UI non c'è ancora — partire
presto conta), poi VT4→VT7 con calma.
