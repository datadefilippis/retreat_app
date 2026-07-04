# Design Refresh — analisi e piano (4 luglio 2026)

Obiettivo del founder: **semplicità, modernità, zero carico cognitivo, colori che
riflettono il mondo olistico.**

## 1 · Fotografia dell'esistente (audit browser + codice)

### Il punto di leva: il design è già tokenizzato
Tutta l'app admin usa variabili CSS centralizzate (`frontend/src/index.css`,
pattern shadcn). Oggi:
- `--primary: 230 75% 57%` → **blu indaco SaaS** (bottoni, ring, badge, links)
- `--gradient-sidebar: 228 40% 16% → 232 35% 22%` → **navy scuro** (menu)
- `--accent: 168 72% 40%` (teal, poco usato) · charts blu/rosso/verde
- radius 0.625rem, ombre soft ben fatte

**Conseguenza:** il 90% del retheme olistico si fa cambiando UN file.
I componenti (Card, Button, Badge, Dialog) sono già coerenti tra loro.

### Dove il design tradisce l'origine "SaaS finanziario"
| Superficie | Problema osservato |
|---|---|
| **Ordini** (screenshot) | **7 file di controlli** prima della tabella: chips conteggio (Bozze/Confermati/Da gestire) + search + segmented Stato (5 voci) + segmented tempo (5 voci) + doppio date picker + segmented canale + segmented pagamento. **Ridondanze**: lo stato appare 2 volte (riga 1 e 3), "Da gestire" 2 volte (riga 1 e 7), il tempo 2 volte (riga 4 e 5). Il caso citato dal founder — confermato al 100%. |
| **Dashboard** | Empty state tecnico: "Aggiungi grafici e KPI dai tuoi moduli usando il pulsante pin". Un organizzatore di ritiri al primo login vede gergo da developer. Nessun "prossimo ritiro", nessun "incassi in arrivo". |
| **Sidebar** | Navy + blu = identità AFianco fintech. Nulla di olistico. |
| **Landing pubbliche** | Usano emerald/gray-900 **hardcoded** (30+ occorrenze) — casualmente già "verdi" ma scollegate dai token: col retheme vanno allineate o divergono. |
| **Tabelle** | Le righe ordine hanno 2 badge colorati (canale + tipo) + pallino + icone: troppi segnali per riga. |
| **Micro** | Icone emoji miste a lucide; radius leggermente rigido per il mood "retreat". |

### Cosa è GIÀ buono (non toccare)
Ombre morbide ben calibrate, spaziature consistenti, Card system pulito,
type-picker appena rifatto, menu snellito (WS-2), pagina piani nuova, i18n 4 lingue.

## 2 · Direzione visiva: palette "mondo olistico"

### Proposta A — «Salvia & Terracotta» (RACCOMANDATA)
Il linguaggio dei ritiri in Italia: verde salvia, terracotta pugliese, sabbia, crema.
Calda, materica, distintiva ma professionale.

```css
--background: 42 35% 97%;          /* crema caldo (era grigio-azzurro freddo) */
--foreground: 160 15% 15%;         /* verde-nero morbido */
--primary: 158 28% 30%;            /* salvia profonda — bottoni, links, focus */
--primary-foreground: 42 35% 97%;
--secondary: 42 25% 92%;           /* sabbia */
--muted: 42 20% 94%;
--muted-foreground: 160 8% 45%;
--accent: 20 55% 55%;              /* terracotta — evidenze, CTA secondarie */
--accent-foreground: 0 0% 100%;
--border: 42 18% 87%;
--ring: 158 28% 30%;
--radius: 0.75rem;                 /* +morbidezza */
--gradient-sidebar: linear-gradient(180deg, hsl(160 28% 13%), hsl(158 22% 19%));
--chart-sales: 158 28% 38%; --chart-expenses: 20 55% 55%;
--chart-net: 158 40% 30%; --chart-projection: 42 10% 60%;
```

### Proposta B — «Oliva & Sabbia» (alternativa più sobria)
Verde oliva `85 25% 32%` + sabbia calda + accent ambra `38 70% 50%`.
Più neutra/mediterranea, meno "wellness-brand" della A.

**In entrambe**: le landing pubbliche passano dagli emerald hardcoded ai token
(coerenza piattaforma↔vetrina). Font: si valuta in fase 4 un serif display
(Fraunces/Lora) SOLO per i titoli delle pagine pubbliche — mood retreat senza
toccare la leggibilità dell'admin.

## 3 · Piano operativo (fasi isolate, ognuna verificabile e mergiabile da sola)

### D1 · Retheme token ✅ (fatto 4/7/2026 — merge su main)
- [ ] Nuove variabili in `index.css` (palette scelta) + gradient sidebar + charts
- [ ] Landing pubbliche: emerald/gray-900 hardcoded → token (sweep mirato)
- [ ] Verifica browser di TUTTE le pagine admin + store + landing + /ritiri
- **DoD**: nessun blu AFianco residuo; contrasto AA sui testi primari.

### D2 · Ordini: da 7 file di filtri a 1 ✅ (fatto 4/7/2026 — merge su main)
- [ ] Riga unica: search + 3 chips di stato-vita: **Da gestire (n) · In corso · Tutti**
- [ ] Bottone "Filtri" (popover) per: stato dettagliato, periodo, canale, pagamento
      — con badge conteggio filtri attivi; chips-riassunto rimovibili quando attivi
- [ ] Tabella alleggerita: 1 badge per riga (stato), canale/tipo come testo muted;
      colonna "Pagamento" con caparra/saldo (es. "240€ / 800€" + barra)
- **DoD**: sopra la tabella al massimo 2 file; ogni info compare UNA volta.
- Assorbe WS-4.1 (vista "richiede attenzione" = chip "Da gestire" di default).

### D3 · Dashboard = home dell'operatore ✅ (fatto 4/7/2026 — merge su main; nuovo endpoint /orders/payments-overview)
- [ ] Default non vuoto: **Prossimi ritiri** (data, posti venduti/capienza),
      **In arrivo** (caparre+saldi attesi 30gg dal ledger), **Da fare**
      (ordini da gestire, saldi scaduti) — 3 card, zero configurazione
- [ ] Il pin/moduli resta come personalizzazione avanzata, non come primo impatto
- **DoD**: primo login → si capisce in 5 secondi come va il business.

### D4 · Rifiniture coerenza ✅ (fatto 5/7/2026 — merge su main)
- [ ] Emoji→lucide dove stonano; empty states col nuovo tono (caldi, operativi)
- [ ] Wizard: cue contenuti ricchi (WS-4/A.3) + tab Biglietti split (A.2)
- [ ] Microcopy sweep finale (A.4)

Ordine: D1 → D2 → D3 → D4. Ogni fase: branch dedicato, parse Babel su ogni JSX,
browser sweep completo, suite verde, merge.

## 4 · Cosa NON facciamo (per non sfasciare)
- Nessun cambio di layout strutturale (sidebar resta sidebar, tabelle restano tabelle)
- Nessuna riscrittura componenti shadcn — solo token + composizione
- Store pubblico: i template store hanno design custom per-merchant — si allineano
  i default, non si forzano gli override esistenti
