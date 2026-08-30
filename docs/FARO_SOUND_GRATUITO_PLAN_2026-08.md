# Il FARO — Aurya Sound gratuito, consolidato e indicizzato (piano profondo, 30/8/2026)

*Le richieste del founder, in un principio solo: il mondo gratuito di
Aurya Sound (landing, biblioteca, impara, lab, esperienze) è il
nostro faro — materiale vero regalato al mondo. Deve (1) funzionare
senza inganni, (2) parlare a un neofita come a un bambino, (3) farsi
trovare da Google con ogni best practice, (4) trasformare valore in
contatti — email e account — in modo snello e tracciato.*

## 0 · Le verifiche fatte prima di scrivere (i fatti)

- **Lo sweep del Banco non si ferma**: è UNA SCELTA nel codice
  («interrompere = tenere la nota», Generatore.jsx) — la stessa
  scelta che il founder ha già bocciato nelle Risonanze il 28/8
  («quando stoppiamo il suono si DEVE fermare»). Non è un bug del
  motore: è la decisione vecchia sopravvissuta in una stanza.
- **«→ Nella libreria (Campane)»** nel Ritratto è GIÀ visibile al
  solo system_admin (`user?.role === 'system_admin'`): nessun utente
  lo vede, niente è mai stato sporcato. Ma il founder ha ragione sul
  principio: il gesto di casa è il quaderno — il bottone esce.
- **La via del ritorno** nelle stanze esiste (`← La Sala del Lab`,
  testata e footer) ma è una riga di testo: su mobile sparisce.
- **Le fonti delle iscrizioni sono GIÀ tracciate**: ogni subscribe
  porta `source` (`frequenze:{slug}`, `cancello:{slug}`,
  `newsletter`, form embed…), il dettaglio utente in admin mostra
  «da: {source}» e c'è un aggregato per fonte. Manca: la tassonomia
  del mondo Sound (oggi il Lab non iscrive nessuno → nessuna fonte
  `sound:*`) e la colonna fonte a colpo d'occhio nella lista.
- **SEO**: le shell SSR esistono (landing, esplora, impara, lab e
  stanze, calm/ground, meditazioni) con titoli veri — base solida.
  Il buco è la PROFONDITÀ: le ~40 schede della biblioteca (il vero
  materiale) vivono TUTTE dentro una pagina sola senza URL propri →
  per Google siamo 1 pagina, non 40. Niente dati strutturati.

## 1 · Le onde

### FA1 — Lo sweep si ferma (la decisione RZ vale ovunque)
Nel Banco, interrompere lo sweep = **silenzio** + cattura della
frequenza del momento (mostrata accanto al bottone, cliccabile per
risuonarla — il pattern «fermo è una misura» delle Risonanze,
identico). Guardia che codifica la decisione per TUTTE le stanze
future: mai un suono che continua dopo uno stop.

### FA2 — La via del ritorno si vede
In ogni stanza il ritorno diventa una **pill sticky in alto a
sinistra** («← Sala del Lab»), sfondo pieno, visibile durante lo
scroll, tap-target da pollice. Una sola classe nel telaio Stanza.jsx
→ vale per tutte le stanze presenti e future.

### FA3 — Il Ritratto salva solo nel quaderno
Via il bottone libreria (e la sua didascalia): i gesti restano
Salva nel quaderno / WAV. (Il caricamento in libreria per il system
admin resta possibile da /admin/sound, la sua casa vera.)

### FA4 — I QUADERNI PERSISTENTI *(il cuore: fattibile, sì)*
Oggi i quaderni (scoperte delle Risonanze + ritratti) vivono in
localStorage: un dispositivo, una vita. Il processo:

1. **Backend**: collezione `sound_quaderni` — un documento per
   account (`platform_account_id`) con le voci dei due registri
   (tipo, payload, `client_id` univoco generato al salvataggio,
   `salvata_il`). API: `GET/PUT /api/sound/quaderni` (auth account).
2. **Sync dolce**: al login (o se già loggato al salvataggio) il
   client fonde locale+server per `client_id` (niente duplicati,
   vince il più recente) e scrive da entrambe le parti. Offline o
   anonimo: localStorage come oggi — mai un salvataggio perso o
   bloccato.
3. **Il momento dell'invito** (il «quando» chiesto dal founder): al
   **primo salvataggio** della sessione, sotto la conferma, una riga
   non-bloccante: *«Salvato su questo dispositivo. Con un account
   Aurya (gratis) ritrovi il tuo quaderno ovunque → Crea account ·
   Accedi»* — link con `?next=` di ritorno alla stanza. Mai un
   popup che interrompe il gesto; la riga resta finché non c'è un
   account. Al ritorno da login: sync automatico + «Il tuo quaderno
   ora ti segue» una volta sola.
4. **Scalabilità**: documento unico per account con tetto voci (es.
   200) e payload minimale (le voci sono già piccole: hz, etichette,
   ritratti = tabelle di numeri); niente audio sul server.

### FA5 — Le fonti del mondo Sound (targeting)
Tassonomia unica: `sound:lab:{stanza}`, `sound:esplora:{slug}`,
`sound:landing`, `sound:calm|ground`, già esistenti
`frequenze:{slug}`/`cancello:{slug}` restano. Ogni CTA del mondo
Sound passa la sua fonte. In admin: colonna «Fonte» nella lista
iscritti + filtro (l'aggregato per fonte c'è già). Così sai CHI
arriva dal Lab e targhettizzi.

### FA6 — LA LINGUA DEL LAB (il lavoro grande)
La biblioteca ha trovato la voce giusta (occhielli, «cosa stai
guardando», evidenza dichiarata). Il Lab la adotta, comando per
comando. Metodo, non ispirazione:

1. **Inventario completo**: ogni stanza → ogni sezione → ogni
   controllo, slider, bottone, grafico, numero a schermo. Niente
   esiste senza spiegazione.
2. **Il pattern in tre voci**, ovunque identico:
   - *Cosa stai guardando* (una frase, prima del grafico);
   - *Cosa succede se…* (sotto ogni controllo: «alza questo e
     senti…»);
   - *La parola difficile* (ogni termine tecnico linkato al
     glossario o spiegato in parentesi la prima volta: «frequenza
     (quante volte l'onda si ripete in un secondo)»).
3. **L'apertura di ogni stanza** riscritta come una storia di 4
   righe per un bambino curioso: cosa farai, cosa proverai, cosa
   scoprirai, da dove cominciare (il «primo gesto» evidenziato).
4. **Tono**: umano, semplice, zero date-per-scontato; l'onestà di
   casa (ciò che non è dimostrato porta il cartellino).
5. Guardia di completezza: ogni controllo con data-testid nel Lab
   deve avere la sua didascalia associata (il test conta).

### FA7 — SEO PROFONDO (da 1 pagina a ~50)
1. **Ogni scheda della biblioteca ha il suo indirizzo**:
   `/sound/esplora/{slug}` (Delta, Theta, 432 Hz, battiti
   binaurali…). La pagina client riusa la scheda esistente (la
   biblioteca è già dati in biblioteca.js); la shell SSR serve il
   CONTENUTO INTERO della scheda (testo, evidenza, «come si
   ascolta») + link alle sorelle. ~40 pagine indicizzabili di
   materiale vero, non thin: è il testo che già abbiamo.
2. **Shell arricchite** per stanze/esperienze: non solo titolo e
   abstract ma il testo didattico completo di FA6 (il crawler legge
   la stessa lezione dell'utente).
3. **Dati strutturati** (JSON-LD): `Article` sulle schede e su
   impara, `BreadcrumbList` (Sound → Esplora → Delta), `FAQPage`
   dove il formato è domanda/risposta (le stanze del Lab lo sono
   già: «A quale frequenza canta il mio oggetto?»).
4. **Igiene**: canonical su ogni URL, OG/Twitter card con immagine,
   H1 unico, sitemap con le ~40 schede e lastmod onesto, interlink
   sistematico biblioteca↔Lab↔Impara (ogni scheda linka la stanza
   dove PROVARE il fenomeno — questo è oro sia per Google che per
   il neofita).
5. **Misura**: dopo il deploy, sitemap ricaricata in GSC (founder) e
   monitoraggio indicizzazione delle nuove URL.

### FA8 — LA RACCOLTA SNELLA (un solo invito, ovunque)
Un componente-invito unico (fratello di CancelloLettera, variante
leggera «riga», non cancello: qui il materiale è GRATIS e resta
gratis) nei punti caldi, ciascuno con la sua fonte FA5:
- fine esperienza Calm/Ground (esiste già → si allinea al copy);
- primo salvataggio nei quaderni (FA4);
- fondo di ogni scheda della biblioteca («ricevi le nuove schede»);
- fondo delle stanze del Lab.
Copy chiaro stile FN («l'iscrizione è gratuita, una email ogni
tanto»), mai bloccante, mai due inviti nella stessa schermata.

## 2 · Ordine e collaudo
FA1+FA2+FA3 subito (piccoli, rimuovono attriti veri) → FA4 (il
processo account) → FA5 (fonti) → FA6 (lingua, il lavoro lungo) →
FA7 (SEO, che di FA6 riusa i testi) → FA8 (inviti). Ogni onda:
collaudo nel pane + guardie. Effort: FA1-3 ~½ giornata; FA4 ~1;
FA5 ~½; FA6 ~1½; FA7 ~1½; FA8 ~½. Totale ~5-6 giornate,
deployabile a tappe (FA1-3 anche subito).

*In attesa del «procedi» (tutto o per onde).*
