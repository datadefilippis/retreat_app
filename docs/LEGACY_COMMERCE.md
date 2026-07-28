# Commerce legacy — cosa c'e' dietro il flag e come si riattiva (TW3)

Il piano Listino (docs/LISTINO_PIANO_2026-07.md) ha congelato le parti
di commerce senza adozione reale. CONGELATO significa: fuori dalla UI,
dati intatti, codice intatto, riattivabile per singola org in un click.

## Cosa e' dietro il flag `organizations.legacy_commerce`

Con flag OFF (default, il "mondo snello"):
- menu operatore a 7 voci: Home, Listino, Ritiri, Calendario, Ordini,
  Profilo pubblico, Impostazioni
- spariscono dal menu: Stores, Prodotti, Corsi, Incassi, Dati,
  Recensioni, Visibilita', Newsletter form, Clienti, Fornitori
  (le PAGINE restano raggiungibili via URL: niente muore)
- la vetrina /s/{slug} redirige al profilo /o/{slug} (le pagine legal
  /s/{slug}/privacy e /terms e il checkout restano vivi)

Con flag ON tornano menu e superfici complete per quella org.

## Come si riattiva (garanzia R2)

Pannello system admin → Organizations → bottone "Legacy" sulla riga
dell'org. Nessun deploy, effetto immediato al prossimo caricamento.

## Garanzie tecniche (R1-R6 del piano)

- R1 codice nel repo: wizard e router di physical/digital/course/
  rental/stock/shipping NON eliminati
- R3 dati intatti: nessuna delete; ordini storici sempre leggibili
- R4 il registro product_types valida ancora tutti i 7 tipi
- R5 guardia di riattivazione nel test suite (test_listino_tw.py)
- Nota: il BACKEND non blocca i tipi congelati (riattivazione
  massima); e' la UI a non offrirli nel mondo snello

## Nota profile-first

store_guard.require_public_home ora AUTO-CREA lo store tecnico
invisibile (nome org, is_default) invece di fermare l'operatore con
il 409: ogni pubblicazione ha sempre un indirizzo pubblico senza che
l'operatore sappia cos'e' uno store.
