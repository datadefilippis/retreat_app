# Aurya letta dalle AI: com'è oggi e piano (ciclo LX, 5/9/2026)

Domanda del founder: i vari LLM hanno tutto il contesto per leggere
bene e proporre Aurya in tutte le sue forme (ritiri, professionisti,
Magazine, Aurya Sound, frequenze e meditazioni, biblioteca)?

Metodo: richieste al sito vivo con gli user-agent dei crawler AI
(GPTBot, ClaudeBot, PerplexityBot, Google-Extended) e con un browser
normale; lettura di `robots.txt`, `/llms.txt`, del JSON-LD e del
testo reso per le pagine di ogni pilastro.

## Cosa è già a posto

- **Nessun blocco**: `robots.txt` non esclude alcun bot AI; l'unico
  Disallow è il gestionale e le API private, con `Allow: /api/public/`.
- **Stesso contenuto per tutti**: nginx instrada per percorso, non per
  user-agent. GPTBot, ClaudeBot, Perplexity e un browser vedono
  esattamente lo stesso HTML (home 3.650 caratteri, articolo 9.884,
  profilo 781). Niente cloaking, niente pagine vuote per le AI.
- **`/llms.txt` esiste** (109 righe): descrizione del brand, payoff,
  pagine principali e i 62 articoli del Magazine per categoria con
  la loro descrizione. È generato dal backend, quindi resta aggiornato.
- **Dati strutturati** su articoli (BlogPosting, FAQPage, Breadcrumb),
  profili (LocalBusiness) e schede Sound (Article).

## Cosa manca perché un LLM racconti Aurya intera

1. **`/llms.txt` conosce solo Magazine e rete.** Zero menzioni di
   frequenze, biblioteca, meditazioni, Lab, Crea Studio; «Sound»
   compare due volte come categoria di articoli. Chi legge quel file
   pensa che Aurya sia un magazine con una directory.
2. **La descrizione dell'Organization nel JSON-LD è vecchia**: «La
   casa dei ritiri olistici italiani: trova e prenota ritiri ed
   esperienze» è il posizionamento del marketplace, spento da luglio.
   È la frase che i motori e i modelli prendono come «cos'è Aurya».
   Mancano `sameAs` (profili social), `knowsAbout`, `foundingDate`,
   `areaServed`.
3. **Le pagine che spiegano chi siamo sono gusci per i bot**:
   `/chi-siamo` 224 caratteri contro 432 parole nella pagina vera,
   `/manifesto` 282 contro 525, `/entra-nella-rete` 285 contro 1.028,
   `/meditazioni` 294, `/operatori` 1.279 (solo l'elenco). Un modello
   che cerca «perché esiste Aurya» trova un titolo e una riga.
4. **Niente JSON-LD** su /sound (l'hub), /manifesto, /chi-siamo,
   /operatori (ItemList dei professionisti), /meditazioni,
   /entra-nella-rete, /newsletter.
5. **Le meditazioni e le esperienze Sound non hanno una scheda
   leggibile**: CALM, GROUND, RESPIRO hanno il testo ma nessun tipo
   strutturato (AudioObject/CreativeWork); le meditazioni riservate
   sono dietro il Cerchio, giusto, ma la pagina pubblica non spiega
   cosa sono.

## Piano proposto (ciclo LX)

**LX1. `/llms.txt` completo e `llms-full.txt`.** Sezioni per ogni
pilastro con una riga onesta ciascuna: la rete dei professionisti (con
i profili pubblici), il Magazine per categoria, Aurya Sound (le tre
esperienze gratuite, la biblioteca delle 38 schede, Le fondamenta, il
glossario, il Lab con le cinque stanze, Crea Studio), le meditazioni e
il Cerchio, i ritiri (come stanno oggi: raccontati, prenotabili quando
i professionisti li pubblicano). Un secondo file `llms-full.txt` con i
testi interi delle pagine cardine per chi li vuole in un colpo.
Generati dal backend come oggi. Guardia: ogni pilastro nominato.

**LX2. L'identità nel JSON-LD.** Organization con la descrizione di
oggi («rete di professionisti del benessere raccontati uno a uno,
Magazine, Aurya Sound»), `sameAs` (Instagram e gli altri profili
reali), `knowsAbout`, `foundingDate`, `inLanguage: it`; WebSite con
`potentialAction` di ricerca verso /operatori. Una sola fonte per la
descrizione del brand, riusata da home, llms.txt e meta.

**LX3. Le pagine cardine con il testo vero nel renderer.** Chi siamo,
Manifesto, Per i professionisti, Meditazioni, Newsletter, /operatori
con una introduzione: stessa copia delle pagine React (dai file di
traduzione, con guardia di parità come per la home). È anche SEO
classica: sono le pagine che oggi «Rilevate, non indicizzate».

**LX4. Dati strutturati dove mancano.** AboutPage e Article per
manifesto e chi siamo, ItemList dei professionisti su /operatori,
CreativeWork/AudioObject per CALM, GROUND, RESPIRO e le schede
Sound, CollectionPage per /sound e /meditazioni, FAQPage dove ci sono
domande e risposte vere (/costi, /entra-nella-rete).

**LX5. Verifica.** Dopo il deploy, tre domande ai modelli con
navigazione (Perplexity, ChatGPT con ricerca, Google AI Overview):
«cos'è Aurya», «Aurya Sound frequenze», «professionisti del benessere
verificati in Italia»; si confrontano le risposte prima e dopo.

Costo: LX1 e LX2 poche ore; LX3 mezza giornata (è la stessa
meccanica di IX2); LX4 mezza giornata; LX5 dipende dai tempi di
ricrawl.
