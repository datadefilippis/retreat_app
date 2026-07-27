# Calendario editoriale del Magazine (BN5)

Regola: 2 articoli a settimana, giorno fisso (proposta: martedi' e
venerdi' mattina), SEMPRE allo standard editoriale. Meglio saltare
un'uscita che pubblicare fuffa.

## Lo standard editoriale (imposto anche dal software)

Al publish il backend BLOCCA gli articoli senza categoria o con
description sotto i 120 caratteri (routers/articles.py, _editorial_gate).
Il resto dello standard e' responsabilita' di chi scrive:

- 1.500+ parole per gli articoli, 2.000+ per le guide "definitive"
- voce onesta: controindicazioni dette, prezzi veri, zero promesse
- fonti citate quando si parla di ricerca (link SOLO se l'URL e' certo)
- almeno 2 link interni ad articoli correlati
- blocco finale "## Domande frequenti" (4-6 Q&A: genera FAQPage schema)
- zero trattini lunghi nel testo
- tabelle markdown dove aiutano il confronto

## Stato lotto upgrade (BN4)

- Lotto 1 (commerciali) — FATTO in bozza, da approvazione founder:
  come-scegliere, quanto-costa, cosa-portare, Toscana, Puglia
  (scripts/bn4_upgrade_articoli_lotto1.py)
- Lotto 2 (11 pratiche): fonti esterne, sezione "esercizio da fare
  oggi", cross-link sistematico — DA FARE
- Lotto 3 (3 operatori): CTA rete, casi veri dalle interviste — DA FARE

## Coda di espansione (in ordine di priorita')

### Guide locali (le SERP piu' vicine alla transazione)
1. Ritiri yoga in Umbria: il cuore verde (Assisi, Trasimeno, Valnerina)
2. Ritiri yoga in Sicilia: Etna, isole e mare d'inverno
3. Ritiri yoga in Sardegna: la stagione lunga
4. Ritiri sul Lago di Garda e i laghi del nord
5. Ritiri in Piemonte e Langhe
6. Ritiri in Trentino-Alto Adige: la montagna che cura

### Categorie scoperte (tassonomia a zero articoli)
7. Massaggio e bodywork: le discipline, spiegate bene
8. Cammini e ritiri itineranti in Italia (Francigena, cammini minori)
9. Benessere aziendale: perche' i team building olistici funzionano

### Pratiche step-by-step (il formato piu' iscrivibile)
10. 5 respirazioni per 5 momenti della giornata
11. La meditazione camminata, passo per passo
12. Lo yoga della sera: 15 minuti prima di dormire

### Interviste-articolo della rete (ponte col pivot)
- Ogni intervista pubblicata sul profilo diventa anche un articolo
  del Magazine (categoria della disciplina dell'operatore, link al
  profilo /o/): contenuto vero + volto vero + link interno alla rete.

## Le guide riservate (BN3, coda)

- FATTA (bozza): Il kit delle pratiche quotidiane (da estendere a
  2.500+ parole in revisione founder)
- DA FARE: La guida completa ai ritiri olistici in Italia (compendio
  gated del cluster ritiri; la versione aperta come-scegliere resta
  indicizzabile e ci punta)
