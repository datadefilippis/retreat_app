# Consolidamento finale — i tre punti rimasti, analizzati e chiusi

26 agosto 2026, sera. Richiesta: chiudere gli ultimi punti «con
un'analisi solida e strutturata, non a caso», senza bug, restando
SEO-friendly.

## Il metodo

Prima di toccare qualsiasi cosa, ogni punto è stato **misurato**. Due
delle tre diagnosi precedenti sono cambiate davanti ai numeri — in
meglio — e una si è rivelata più semplice del previsto. Documento
prima le misure, poi le decisioni, poi cosa è stato fatto.

---

## 1 · Il bundle da 575 KB — misurato, la causa è UNA

**La diagnosi precedente** («code splitting del main, cantiere
grosso») era sbagliata per eccesso. Le librerie pesanti — grafici,
mappe, 3D, encoder audio — sono **già** in chunk separati che si
caricano solo dove servono. Il main contiene:

| cosa | peso |
|---|---|
| **Traduzioni: 4 lingue × 11 namespace, tutte caricate subito** | **~1.730 KB dei 1.997 raw** |
| Codice dell'app + pagine pubbliche + resto | ~270 KB |

Il 95% dei visitatori usa l'italiano (solo-italiano è pure la
strategia dichiarata), ma ogni visitatore scaricava anche inglese,
tedesco e francese.

**La soluzione, e perché è sicura**: il codice ha già il precedente —
i 18 namespace del back-office sono stati spostati fuori dal bundle
pubblico mesi fa (PL17) con questo esatto principio. Si replica per le
lingue: **l'italiano resta nel bundle** (nessun ritardo per nessuno),
en/de/fr diventano chunk che si scaricano solo quando qualcuno cambia
lingua. Chi cambia lingua vede l'italiano per una frazione di secondo
mentre arriva il pacchetto — comportamento onesto e standard.

**Effetto atteso**: main da ~575 KB compressi a una frazione. SEO:
neutro o positivo (Google raccomanda meno JavaScript; il contenuto
delle pagine arriva comunque dal server, quindi nulla dipende dal
bundle).

## 2 · La misura del traffico — il contatore che non ci esclude

**Misurato**: il ping di visita parte per chiunque, noi compresi. Il
dedup è su un'impronta giornaliera salata, quindi non possiamo
riconoscerci a posteriori: va impedito **alla fonte**.

**La soluzione, due cinture**:
1. **Chi è loggato come operatore o admin non viene tracciato.** Se
   c'è un token di lavoro nel browser, il ping non parte. Copre noi
   due nei browser di lavoro — e copre anche ogni operatore che
   guarda il proprio profilo, che oggi si conta da solo come
   visitatore.
2. **Il patto del telefono**: aprire una volta l'indirizzo
   `aurya.life/?siamo-noi` marca quel browser per sempre (una chiave
   locale) e il tracking tace. Per i nostri telefoni, dove non siamo
   sempre loggati.

GA4 resta com'è (il consenso è un vincolo di legge, non un difetto):
il contatore interno, ora pulito, diventa **il riferimento**.

## 3 · Le fonti negli articoli — l'audit si corregge da solo

**La diagnosi precedente** («zero link esterni in 47 articoli») era
un'estrapolazione da UN articolo — lo stesso tipo di errore
d'aggregato già pagato due volte. La misura vera su tutti i 47:

- **Già linkati**: la legge 4/2013 (4 articoli, via normattiva), JAMA
  (1), Nature (1), MBSR (3). La redazione linkava già, dove contava.
- **Menzioni istituzionali nude**, inequivocabili e linkabili in
  automatico sicuro: legge 4/2013 in 5 articoli, INPS in 2, Agenzia
  delle Entrate in 1. **Otto ritocchi chirurgici**, ognuno con la
  frase esatta verificata prima.
- **Menzioni di studi** (Britton, uno studio JAMA, Stanford,
  Kabat-Zinn): qui l'automatico si FERMA. Linkare lo studio sbagliato
  è peggio che non linkare: serve la persona che sa QUALE studio era.
  → elenco consegnato alla redazione, con articolo e frase.

**La regola che resta**: si automatizza solo l'inequivocabile
(istituzioni, leggi); gli studi si linkano a mano o non si linkano.

---

## Cosa NON è in questo consolidamento, e dove vive

- **GSC «Richiedi indicizzazione» + Bing Webmaster**: compito founder
  (30 minuti), nel piano strategico.
- **sameAs / social del brand**: in attesa degli URL.
- **La revisione redazionale degli «In breve»**: bozze in /admin.
