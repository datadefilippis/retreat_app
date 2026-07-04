# Entity Linking Layer — Design Document Tecnico

---

## Contesto

AFianco ha campi FK (`customer_id`, `product_id`, `supplier_id`) sui record transazionali che non vengono mai popolati. Questo rende 3 moduli su 5 inutilizzabili (customers_light, product_catalog, commerce_signals) e 13 dei 22 AI tool sempre vuoti. Il linking layer risolve questo gap collegando le transazioni alle entità master in modo affidabile.

---

# 1. Scope Esatto del Linking

## 1.1 SalesRecord <-> Customer (`customer_id`)

| Dimensione | Valore |
|-----------|--------|
| **Utilita business** | ALTA — Identifica chi compra cosa. CRM intelligence per PMI senza CRM |
| **Utilita analytics** | ALTA — Sblocca customers_light: LTV, churn risk, segmentazione, concentrazione |
| **Utilita AI** | ALTA — 7 AI tool in customers_light + 2 in commerce_signals dipendono da questo |
| **Priorita** | **P0** |
| **Stato attuale** | Campo `customer_id: Optional[str] = None` in `models/dataset.py:86` — commento "future linkage", mai popolato. `SalesRecordCreate` non accetta il campo. |

## 1.2 SalesRecord <-> Product (`product_id`)

| Dimensione | Valore |
|-----------|--------|
| **Utilita business** | ALTA — Revenue per prodotto, analisi margini |
| **Utilita analytics** | ALTA — Sblocca product_catalog: margini, ABC, trend. `refresh_product_metrics()` filtra su `product_id != null` e trova 0 record |
| **Utilita AI** | ALTA — 4 AI tool in product_catalog |
| **Priorita** | **P0** |
| **Stato attuale** | Campo `product_id: Optional[str] = None` in `models/dataset.py:87` — mai popolato. `SalesRecordCreate` non accetta il campo. Alias "prodotto" mappa a "category" (`dataset_service.py:144`), non a product_id |

## 1.3 PurchaseRecord <-> Product (`product_id`)

| Dimensione | Valore |
|-----------|--------|
| **Utilita business** | ALTA — Costo per prodotto -> margine = revenue - costo |
| **Utilita analytics** | ALTA — `product_catalog/service.py:67-76` aggrega costi da purchase_records per product_id, ma il campo NON ESISTE sul modello PurchaseRecord |
| **Utilita AI** | MEDIA — Tool margine dipendono dai dati costo |
| **Priorita** | **P0** |
| **Stato attuale** | PurchaseRecord in `models/dataset.py` NON ha `product_id`. PurchaseRecordBase in `models/financial_record.py` NON ha `product_id`. Campo da aggiungere. |

## 1.4 ExpenseRecord <-> Supplier (`supplier_id`)

| Dimensione | Valore |
|-----------|--------|
| **Utilita business** | MEDIA — Analisi spesa per fornitore |
| **Utilita analytics** | MEDIA — Nessun modulo consuma expense.supplier_id per dashboard |
| **Utilita AI** | BASSA — Nessun AI tool lo usa direttamente |
| **Priorita** | **P1** |
| **Stato attuale** | PARZIALMENTE implementato: auto-match durante CSV import in `dataset_service.py:1454-1460` con `_build_supplier_name_map()`. NON funziona su entry manuale. |

## 1.5 PurchaseRecord <-> Supplier (`supplier_id`)

| Dimensione | Valore |
|-----------|--------|
| **Utilita business** | MEDIA — Spesa acquisti per fornitore |
| **Utilita analytics** | MEDIA — Diversificazione fornitori |
| **Utilita AI** | BASSA |
| **Priorita** | **P1** |
| **Stato attuale** | Campo esiste su `financial_record.py:44` ma NON su `models/dataset.py` PurchaseRecord. Auto-match NON implementato per acquisti. |

## 1.6 ExpenseRecord <-> Product (`product_id`)

| Dimensione | Valore |
|-----------|--------|
| **Utilita business** | BASSA — Le spese sono tipicamente servizi/overhead, non prodotti |
| **Utilita analytics** | BASSA — Costi prodotto meglio serviti da PurchaseRecord |
| **Utilita AI** | BASSA |
| **Priorita** | **P2 (differire)** |
| **Stato attuale** | Campo esiste `models/dataset.py:116` ma resta best-effort |

### Riepilogo Priorita

| Priorita | Relazioni |
|----------|-----------|
| **P0** | sales<->customer, sales<->product, purchases<->product |
| **P1** | expenses<->supplier (estendere), purchases<->supplier (aggiungere auto-match) |
| **P2** | expenses<->product (differire) |

---

# 2. Domain Rules

## 2.1 Quando auto-linkare (scrivere FK senza conferma utente)

1. **Match esatto normalizzato con UN solo candidato**: `text.lower().strip() == entity.name.lower().strip()` AND esattamente un match nella org. Pattern provato da `_build_supplier_name_map` (`dataset_service.py:189-202`).
2. **Match su external_id o SKU**: colonna CSV contiene valori che corrispondono a `customer.external_id`, `product.sku`, o `supplier.external_id`. Questi sono unici per org (indici sparse unique in `database.py:163-178`).

## 2.2 Quando il match deve essere solo suggerimento

1. **Candidati multipli**: "Rossi" matcha sia "Rossi S.r.l." che "Rossi & Figli".
2. **Fuzzy match**: nomi simili ma non identici (Phase 3, non Phase 1).

**Decisione di design: NESSUN fuzzy matching in Phase 1.** I CSV delle PMI sono troppo inconsistenti per matching automatizzato non esatto.

## 2.3 Quando il record deve restare unresolved

1. Nessuna entita master esiste nella org.
2. Il campo di testo sorgente e null o vuoto.
3. Match ambiguo senza possibilita di disambiguare.

## 2.4 Nomi duplicati

Se `name.lower().strip()` matcha piu entita attive, trattare come ambiguo — NON linkare. La funzione `_build_entity_name_map` deve rilevare e escludere chiavi duplicate: se una chiave esiste gia, rimuoverla (entrambe le entry diventano non-matchabili).

## 2.5 Rinomina entita master

- Record gia linkati restano correttamente linkati (FK basato su ID).
- Import futuri con il vecchio nome non matcheranno. L'admin puo aggiungere il vecchio nome come alias (Phase 2).
- Nessun de-linking retroattivo su rinomina.

## 2.6 Prevenire link sbagliati

1. Mai auto-linkare su fuzzy match (Phase 1).
2. Mai auto-linkare quando ci sono candidati multipli.
3. Import summary riporta conteggio match per tipo entita in UploadResponse.
4. Endpoint PATCH devono accettare null esplicito per rimuovere un link sbagliato.

---

# 3. Matching Strategy

## Livello 1: Match Esatto Normalizzato (Phase 1 — auto-apply)

**Metodo**: `text.lower().strip() == entity.name.lower().strip()`, singolo match.

- **Pro**: Zero falsi positivi con check unicita. Pattern provato. Dict lookup O(1).
- **Contro**: Non cattura variazioni ("S.r.l." vs "srl", "Mario Rossi" vs "Rossi Mario").
- **Rischio falsi positivi**: Quasi zero con check unicita.
- **Azione**: Auto-apply — scrive FK durante import.

## Livello 2: Match External ID / SKU (Phase 1 — auto-apply)

**Metodo**: valore colonna CSV matcha `customer.external_id`, `product.sku`, o `supplier.external_id`.

- **Pro**: Massima affidabilita. Constraint univoco da indice MongoDB.
- **Contro**: Richiede che l'utente abbia popolato external_id/sku E includa la colonna nel CSV.
- **Rischio falsi positivi**: Zero.
- **Azione**: Auto-apply.

## Livello 3: Tabella Alias (Phase 2 — auto-apply)

**Metodo**: tabella alias per org che mappa nomi alternativi a entity ID.

- **Pro**: Gestisce rinomina, abbreviazioni, typo ricorrenti. Curato dall'utente = alta precisione.
- **Contro**: Richiede effort utente.
- **Azione**: Auto-apply (alias curati dall'utente, trusted).

## Livello 4: Fuzzy / AI Match (Phase 3 — solo suggerimento)

**Metodo**: distanza Levenshtein, token overlap, o matching LLM-based.

- **Rischio falsi positivi**: ALTO.
- **Azione**: Solo suggerimento, presentato in coda di risoluzione per review manuale.

## Livello 5: Linking Manuale (sempre disponibile)

L'utente setta esplicitamente l'FK via endpoint PATCH o UI di risoluzione.

---

# 4. Data Model Impact

## 4.1 Campi da Aggiungere

### `models/dataset.py` — PurchaseRecord (L128-149)

```
+ product_id: Optional[str] = None   # FK -> products._id
+ supplier_id: Optional[str] = None  # FK -> suppliers._id (allineare con financial_record.py)
```

### `models/financial_record.py` — PurchaseRecordBase (L36-55)

```
+ product_id: Optional[str] = None
```

### `models/financial_record.py` — PurchaseRecordUpdate (L80-101)

```
+ product_id: Optional[str] = None
+ supplier_id: Optional[str] = None
```

### `models/dataset.py` — SalesRecordCreate (L204-211)

```
+ customer_id: Optional[str] = None
+ product_id: Optional[str] = None
```

### `models/dataset.py` — SalesRecordUpdate (L214-222)

```
+ customer_id: Optional[str] = None
+ product_id: Optional[str] = None
```

### `models/dataset.py` — ExpenseRecordCreate (L225-231)

```
+ supplier_id: Optional[str] = None
```

### `models/dataset.py` — ExpenseRecordUpdate (L233-239)

```
+ supplier_id: Optional[str] = None
```

### `models/dataset.py` — PurchaseRecordCreate (L151-160)

```
+ supplier_id: Optional[str] = None
+ product_id: Optional[str] = None
```

## 4.2 Nuovi Metodi Repository

Ogni repository entita necessita:

**customer_repository.py:**
```
+ find_by_name(organization_id, name) -> Optional[Customer]          # match esatto case-insensitive
+ find_by_external_id(organization_id, external_id) -> Optional[Customer]
```

**product_repository.py:**
```
+ find_by_name(organization_id, name) -> Optional[Product]
+ find_by_sku(organization_id, sku) -> Optional[Product]
```

**supplier_repository.py:**
```
+ find_by_name(organization_id, name) -> Optional[Supplier]
+ find_by_external_id(organization_id, external_id) -> Optional[Supplier]
```

## 4.3 Nuovi Indici (`database.py`)

```
# PurchaseRecord product_id (per aggregazione costi in product_catalog)
await purchase_records_collection.create_index(
    [("organization_id", 1), ("product_id", 1)]
)

# ExpenseRecord supplier_id
await expense_records_collection.create_index(
    [("organization_id", 1), ("supplier_id", 1)]
)
```

Nota: indici su `(org_id, customer_id)` e `(org_id, product_id)` per sales_records esistono gia (`database.py:313-321`).

## 4.4 Nuove Collection

**Nessuna in Phase 1.** Metadata linking nel dict `metadata` esistente del record. Audit usa `audit_logs_collection` esistente. Phase 2 puo introdurre `entity_aliases`.

## 4.5 Alias Colonna da Aggiungere (`dataset_service.py`)

**Nuovi alias generali** (in `_HARDCODED_ALIASES`):
```
"cliente" -> "customer_name_lookup"          # virtuale, consumato e rimosso
"customer" -> "customer_name_lookup"
"customer_name" -> "customer_name_lookup"
"nome_cliente" -> "customer_name_lookup"
"codice_cliente" -> "customer_extid_lookup"
"customer_id" -> "customer_extid_lookup"     # NON confondere con il campo FK
"customer_code" -> "customer_extid_lookup"
```

**Alias specifici per acquisti** (blocco `DatasetType.PURCHASES`):
```
"codice_prodotto" -> "product_sku_lookup"
"product_code" -> "product_sku_lookup"
"sku" -> "product_sku_lookup"
```

**Design: "Colonne virtuali lookup"** — mapate a nomi con suffisso `_lookup`. Vengono consumate dallo stage di entity resolution e **rimosse dal row** prima della creazione del record. Questo previene l'inquinamento del data model con colonne transitorie.

---

# 5. Import Pipeline Impact

## Pipeline Attuale (in `dataset_service.py`)

```
1. Upload file + salva disco
2. Parse CSV/Excel -> DataFrame
3. Rename colonne (alias hardcoded + mapping org DB)
4. Pulizia dati (numeri, date, testo)
5. Validazione schema (campi obbligatori)
6. Motore regole validazione
7. Build supplier_name_map (SOLO spese)
8. Iterazione righe: crea record dict, tenta match fornitore (SOLO spese)
9. Bulk insert
10. Post-upload hooks via module registry
11. Return UploadResponse
```

## Pipeline Ridisegnata

Stage 1-6 invariati. Modifiche da stage 7:

### Stage 7: Entity Resolution Maps (generalizzato)

In base al `dataset_type`, costruire le lookup dict appropriate:

| dataset_type | Map da costruire |
|-------------|-----------------|
| SALES | customer_name_map, customer_extid_map (se colonna presente), product_name_map, product_sku_map (se colonna presente) |
| EXPENSES | supplier_name_map (esistente), supplier_extid_map (se colonna presente) |
| PURCHASES | supplier_name_map (NUOVO), product_name_map, product_sku_map (se colonna presente) |

**Implementazione**: generalizzare `_build_supplier_name_map` in `_build_entity_name_map(org_id, collection, name_field="name")` che funziona identicamente per qualsiasi tipo entita. Replicare anche per external_id e sku.

**Gestione duplicati nel dict**: se due entita hanno lo stesso nome normalizzato, rimuovere la chiave dal dict (ambigua -> non matchabile automaticamente).

### Stage 8: Iterazione Righe con Entity Resolution (modificato)

Per ogni riga, PRIMA della creazione record:

**Sales records:**
1. Se colonna `customer_name_lookup` presente -> `customer_name_map.get(value.lower().strip())`; se match -> `row["customer_id"] = matched_id`; se no match -> `metadata["unresolved_customer_name"] = value`
2. Se colonna `customer_extid_lookup` presente -> `customer_extid_map.get(value.strip())`
3. Se colonna `product_sku_lookup` presente -> `product_sku_map.get(value.strip())` -> `row["product_id"]`
4. Fallback: tentare `product_name_map.get(row.get("category", "").lower().strip())` (perche "prodotto" mappa a "category")
5. Rimuovere tutte le colonne `*_lookup` dalla riga prima di passare al costruttore SalesRecord

**Purchase records:**
1. Se `supplier_name` presente -> `supplier_name_map.get(supplier_name.lower().strip())` -> `row["supplier_id"]` (NUOVO)
2. Se `product_sku_lookup` presente -> `product_sku_map.get(value.strip())` -> `row["product_id"]`
3. Fallback: `product_name_map.get(row.get("category", "").lower().strip())`
4. Rimuovere colonne `*_lookup`

**Expense records:**
Match fornitore invariato (codice esistente L1454-1460).

### Stage 11: UploadResponse (modificato)

Aggiungere statistiche match alla risposta:

```python
entity_match_stats: Optional[dict] = None
# Esempio: {
#   "customers_matched": 45,
#   "products_matched": 120,
#   "suppliers_matched": 30,
#   "unresolved_customers": 5,
#   "unresolved_products": 10,
#   "total_records": 200
# }
```

---

# 6. Manual Data Entry Impact

## POST /sales (`routers/sales.py:22-47`)

**Modifiche:**
1. `SalesRecordCreate` ora accetta `customer_id` e `product_id`
2. Nel router, prima di creare il record:
   - Se `customer_id` fornito -> `customer_repository.find_by_id(r.customer_id, org_id)`. HTTP 400 se non trovato.
   - Se `product_id` fornito -> `product_repository.find_by_id(r.product_id, org_id)`. HTTP 400 se non trovato.
3. Passare FK validati al costruttore SalesRecord
4. **Nessun auto-create entita.** Se l'entita non esiste, l'utente deve crearla prima via API CRUD.

## POST /expenses (`routers/expenses.py:22-47`)

**Modifiche:**
1. `ExpenseRecordCreate` ora accetta `supplier_id`
2. Se `supplier_id` fornito -> validare esistenza
3. Se `supplier_id` NON fornito ma `supplier` testo presente -> tentare auto-match con stesso pattern dict. Questo porta parita tra entry manuale e CSV import.

## POST /purchases (`routers/purchases.py:24-61`)

**Modifiche:**
1. `PurchaseRecordCreate` ora accetta `supplier_id` e `product_id`
2. Validare FK se forniti
3. Se `supplier_name` fornito ma `supplier_id` no -> tentare auto-match

## PATCH Endpoints

Tutti gli endpoint PATCH devono accettare campi FK per link/unlink manuale. Problema critico: il pattern attuale usa `model_dump(exclude_none=True)`, che significa che `{"customer_id": null}` verrebbe escluso invece di settare il campo a null.

**Risoluzione**: per i campi FK, usare `model_dump(exclude_unset=True)` invece di `exclude_none=True`. Questo distingue tra "campo non inviato nel body" (escluso) e "campo inviato esplicitamente come null" (incluso, setta a null in DB).

---

# 7. Retroactive Linking

## Problema

Organizzazioni con dati storici avranno migliaia di record con FK null. Le entita master potrebbero essere popolate dopo. Serve un meccanismo per linkare retroattivamente.

## Due Nuovi Endpoint

### Preview

```
POST /api/entity-linking/preview
Body: { record_type: "sales"|"expenses"|"purchases", entity_type: "customer"|"product"|"supplier" }
```

Scansiona record non linkati, costruisce entity name map, tenta matching, ritorna preview SENZA scrivere.

Risposta:
```json
{
  "total_unlinked": 1234,
  "matchable": 567,
  "matches": [
    {"text_value": "Rossi S.r.l.", "entity_id": "abc", "entity_name": "Rossi S.r.l.", "record_count": 45, "match_type": "exact_name"}
  ],
  "ambiguous": [
    {"text_value": "Rossi", "candidates": [{"entity_id": "abc", "name": "Rossi S.r.l."}, {"entity_id": "def", "name": "Rossi & Figli"}], "record_count": 12}
  ],
  "unmatchable_count": 655
}
```

### Apply

```
POST /api/entity-linking/apply
Body: { record_type: "sales", entity_type: "customer", matches: [{"text_value": "Rossi S.r.l.", "entity_id": "abc"}] }
```

Esegue bulk `update_many`. Ritorna conteggio record aggiornati.

## Sorgenti Testo per Retroactive Matching

| Record type | Entity type | Campo sorgente testo |
|-------------|-------------|---------------------|
| sales | customer | `metadata.unresolved_customer_name` (salvato durante import) |
| sales | product | `category` (poiche "prodotto" mappa a "category") |
| expenses | supplier | `supplier` (campo testo) |
| purchases | supplier | `supplier_name` (campo testo) |
| purchases | product | `category` |

**Critico**: la pipeline di import DEVE preservare valori non risolti in `metadata` durante import. Es: se CSV ha colonna "cliente" che non matcha nessuno, salvare `metadata["unresolved_customer_name"] = "Rossi S.r.l."`.

## Post-Apply: Ricalcolo

Dopo bulk linking:
```python
await _run_post_upload_hooks(org_id)
```
Triggera hook customers_light e product_catalog che ricalcolano le metriche materializzate.

---

# 8. Impact sui Moduli Esistenti

## customers_light

**Prima**: `count_linked_sales` ritorna 0 -> `build_overview` ritorna `has_data: False` -> 7 AI tool vuoti.

**Dopo**: Con customer_id popolato:
- `aggregate_revenue_by_customer` ritorna dati reali raggruppati
- `refresh_customer_metrics` calcola LTV, churn risk, segmenti, concentrazione
- `build_overview` ritorna dashboard completa
- Tutti i 7 AI tool funzionano
- `_compute_preferred_products` funziona SE anche product_id e popolato (dipendenza incrociata)

## product_catalog

**Prima**: `refresh_product_metrics` non trova sales con product_id -> `products_computed: 0`.

**Dopo**: Con product_id su sales E purchases:
- Revenue per prodotto da sales aggregation
- Costo per prodotto da purchase aggregation (richiede product_id su PurchaseRecord — campo da aggiungere)
- Margine = revenue - costo (attualmente sempre uguale a revenue perche costo = 0)
- Classificazione ABC diventa significativa
- Tutti i 4 AI tool funzionano

## commerce_signals

**Prima**: Dipende da customer_metrics -> `has_data: False`.

**Dopo**: Automaticamente attivato quando customers_light ha dati:
- Segnali riattivazione per clienti inattivi ad alto valore
- Segnali rischio concentrazione
- Segnali conversione nuovi clienti

## cashflow_monitor

Nessuna dipendenza diretta dal linking. Aggrega per data/categoria. Beneficio indiretto da accuratezza categorie migliorata.

---

# 9. Governance e Audit

## 9.1 Tracking Sorgente Link

Salvare metadata linking nel dict `metadata` esistente del record (nessun cambio schema):

```python
metadata = {
    "link_source": {
        "customer_id": {
            "method": "auto_import",          # auto_import | manual_create | manual_patch | batch_retroactive
            "matched_on": "name",             # name | external_id | sku
            "matched_value": "Rossi S.r.l.",
            "linked_at": "2026-04-06T10:00:00Z"
        }
    }
}
```

## 9.2 Confidence Score

Phase 1 (solo match esatto): confidence implicitamente 1.0. Non serve campo stored.
Phase 2+ (alias/fuzzy): aggiungere `"confidence": 0.95` all'entry link_source.

## 9.3 Audit Trail

Usare `audit_logs_collection` e modello `AuditLog` esistenti. Per operazioni bulk (import, retroactive), log entry di riepilogo:

```python
AuditLog(
    organization_id=org_id,
    action="bulk_entity_link",
    entity_type="sales_records",
    details={"records_linked": 567, "entity_type": "customer", "method": "batch_retroactive"}
)
```

Audit per-record non necessario per import (creerebbe N entry per upload). Livello riepilogo sufficiente.

---

# 10. Sequenza Consigliata di Implementazione

## Phase 1: Foundation (link P0 + pipeline import)

**Obiettivo**: Abilitare le 3 relazioni P0 tramite CSV import con auto-linking exact-match, piu supporto FK su entry manuale.

### Step 1.1: Data Model Changes

**File**: `models/dataset.py`, `models/financial_record.py`

- Aggiungere `product_id` e `supplier_id` a PurchaseRecord in dataset.py
- Aggiungere `product_id` a PurchaseRecordBase in financial_record.py
- Aggiungere campi FK a tutti i Create/Update model
- Aggiungere indici in `database.py`

**Nessuna dipendenza**. Primo step.

### Step 1.2: Repository Methods

**File**: `repositories/customer_repository.py`, `product_repository.py`, `supplier_repository.py`

- Aggiungere `find_by_name()`, `find_by_external_id()`, `find_by_sku()`

**Dipende da**: Step 1.1 (campi devono esistere)

### Step 1.3: Entity Resolution nella Pipeline Import

**File**: `services/dataset_service.py`

- Generalizzare `_build_supplier_name_map` in `_build_entity_name_map(org_id, entity_type)`
- Aggiungere `_build_entity_extid_map`, `_build_product_sku_map`
- Aggiungere alias colonna (customer_name_lookup, customer_extid_lookup, product_sku_lookup)
- Estendere iterazione righe con entity resolution per tutti i tipi record
- Salvare valori lookup non risolti in metadata
- Aggiungere contatori match a UploadResponse

**Dipende da**: Step 1.1, Step 1.2
**File critico**: dataset_service.py (1541 righe — toccare con cura)

### Step 1.4: Supporto FK su Entry Manuale

**File**: `routers/sales.py`, `routers/expenses.py`, `routers/purchases.py`

- Accettare e validare campi FK su POST endpoint
- Aggiungere auto-match su entry manuale per acquisti (supplier_name -> supplier_id)

**Dipende da**: Step 1.1, Step 1.2

### Step 1.5: Supporto FK su PATCH

**File**: `routers/sales.py`, `routers/expenses.py`, `routers/purchases.py`

- Accettare campi FK su endpoint PATCH
- Cambiare `exclude_none` in `exclude_unset` per gestione FK null esplicito

**Dipende da**: Step 1.1

### Stima scope Phase 1: ~12 file modificati, 0 nuovi file, 0 nuove collection

---

## Phase 2: Retroactive Linking + Entity Aliases

**Obiettivo**: Linkare record storici, gestire variazioni nomi.

- Step 2.1: Nuovo router per endpoint preview/apply retroactive linking
- Step 2.2: Nuova collection `entity_aliases` per nomi alternativi curati dall'utente
- Step 2.3: Includere alias nei name map durante import
- Step 2.4: UploadResponse migliorata con breakdown match/ambiguous/unmatched

**Dipende da**: Phase 1 completa

---

## Phase 3: Fuzzy Matching + Risoluzione AI-Assistita

**Obiettivo**: Gestire la coda lunga di inconsistenze nei nomi.

- Step 3.1: Suggerimenti basati su similarita (solo suggerimento, mai auto-apply)
- Step 3.2: Arricchimento AI tramite integrazione Claude esistente per casi ambigui

**Dipende da**: Phase 2 completa

---

## File Critici per Implementazione

```
backend/models/dataset.py                    — SalesRecord, ExpenseRecord, PurchaseRecord, Create/Update, UploadResponse
backend/models/financial_record.py           — PurchaseRecordBase, PurchaseRecordUpdate
backend/services/dataset_service.py          — Pipeline import, alias, entity resolution, _build_supplier_name_map
backend/routers/sales.py                     — POST e PATCH endpoint
backend/routers/expenses.py                  — POST e PATCH endpoint
backend/routers/purchases.py                 — POST e PATCH endpoint
backend/repositories/customer_repository.py  — Nuovi metodi find_by_name, find_by_external_id
backend/repositories/product_repository.py   — Nuovi metodi find_by_name, find_by_sku
backend/repositories/supplier_repository.py  — Nuovi metodi find_by_name, find_by_external_id
backend/database.py                          — Nuovi indici
```
