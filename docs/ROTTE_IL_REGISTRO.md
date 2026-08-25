# Il registro delle rotte — come si lavora da qui in avanti

26 agosto 2026. Documento operativo: **leggilo prima di aggiungere una
pagina**. Sono due minuti e ti risparmiano il difetto che abbiamo
pagato tre volte in due giorni.

---

## Il problema che risolve

La stessa conoscenza — *quali indirizzi esistono su Aurya* — viveva in
cinque posti diversi:

| dove | cosa sapeva |
|---|---|
| `frontend/src/App.js` | le rotte vere (131) |
| `deploy/nginx/nginx.conf` | chi passa dal renderer |
| `backend/routers/seo_shell.py` | chi ha delle meta |
| `backend/routers/seo.py` | chi sta in sitemap |
| `robots.txt` | chi è vietato |

Nessuno li teneva allineati, e il prezzo è stato **tre pagine mute**:

- `/meditazioni` — che sta nel **menu del sito**
- `/costi` — la pagina che ogni professionista apre per prima
- `/frequenze/{slug}` — **il link che l'operatore manda ai suoi clienti**

Tutte e tre servivano ai crawler 46 caratteri e il titolo marketplace
di luglio. Nessuna era un bug di codice: per una persona funzionavano
benissimo. Erano un bug di **organizzazione** — e quelli non si
risolvono ricordandosi meglio.

---

## Come funziona adesso

**`backend/config/rotte.json` è la fonte.** Classifica ogni segmento di
primo livello in tre tipi:

| tipo | significato | cosa riceve |
|---|---|---|
| **pubblica** | è contenuto: il web che vogliamo far vedere | meta e corpo server-side, può stare in sitemap |
| **servizio** | esiste ma non si indicizza: login, pagine a token, legali | 200 + `noindex` |
| **app** | il gestionale, dietro login | servita dal frontend con `X-Robots-Tag: noindex` |

**Chi non è nel registro non esiste: 404.** È così che si è chiuso lo
spazio infinito di URL che rispondevano 200.

Da lì tutto si deriva o si verifica:

- **nginx si genera**: `python3 scripts/genera_rotte_nginx.py --scrivi`
  scrive i due blocchi fra i marcatori. Una guardia rifà il calcolo e
  confronta: modificarlo a mano, o cambiare il registro senza
  rigenerare, rende la suite rossa.
- **la shell legge il registro** per decidere cosa è servizio, cosa è
  app e cosa non esiste.
- **le guardie** (`backend/tests/test_rotte_registro.py`, 10) tengono
  insieme le due estremità.

---

## Aggiungere una pagina: la procedura

1. **Scrivi la rotta** in `App.js`, come sempre.
2. **Classificala** in `backend/config/rotte.json` — `pubblica`,
   `servizio` o `app`.
3. **Rigenera nginx**: `python3 scripts/genera_rotte_nginx.py --scrivi`
4. Se è **pubblica**: dalle delle meta nella shell (`resolve_meta`) e,
   se merita di essere trovata, mettila in sitemap.
5. **Prova**: `python3 scripts/collauda_rotte.py http://localhost:3000`

Se salti il passo 2, la suite diventa rossa con il nome della rotta
che manca. Se salti il 3, la suite ti dice che nginx e registro
divergono. Se salti il 4, la guardia elenca le pubbliche senza meta.

**Non devi ricordarti niente: te lo dice la suite, prima del deploy.**

---

## Le trappole, per iscritto

Le abbiamo trovate tutte costruendo questa struttura. Sono qui perché
non si ritrovino due volte.

**In nginx una regex batte un prefisso.** La regola degli asset
(`~* "\.[A-Za-z0-9]{1,6}$"`) si prendeva anche
`/api/public/sitemap-core.xml` e `/uploads/.../cover.webp`: la sitemap
tornava HTML vuoto e le immagini degli articoli rispondevano 404. Il
prefisso vince solo se dichiarato **`^~`**.

**Le graffe in una regex vanno quotate.** `location ~* \.[a-z]{1,6}$`
fa morire nginx all'avvio (*unknown directive "1,6}$"*), e siccome il
deploy riavvia, il container entra in loop e **il sito sparisce**. Da
qui il `nginx -t` prima del riavvio: se la config non parte, il deploy
si ferma e i container vecchi restano in piedi.

**`proxy_pass http://host/uri` appende il resto del percorso.**
`/pagina-inventata` diventava `/__seo/404pagina-inventata`: una chiave
di cache diversa per ogni indirizzo inventato, cioè la cache senza fine
che l'endpoint unico doveva evitare. Serve `rewrite ^ /uri break`.

**Il contesto di build del backend è `backend/`.** Un file alla radice
del repo non entra nell'immagine — per questo il registro sta in
`backend/config/`. Ci siamo arrivati con le rotte di servizio che
rispondevano 404 in produzione.

**Una configurazione che manca deve degradare verso il permissivo.**
Il primo ripiego metteva insiemi vuoti: senza il file, ogni percorso
diventava «sconosciuto» e il sito intero avrebbe risposto 404. Ora
senza registro non si dichiara inesistente niente, e si urla nei log.

---

## Il collaudo

`scripts/collauda_rotte.py <base>` apre **ogni** segmento del registro
contro un sito vero e verifica che si comporti come dichiarato, più le
superfici che non sono pagine (sitemap, robots, llms) e una manciata di
indirizzi inventati che devono dare 404.

Va lanciato **dopo ogni deploy che tocca le rotte**. È il passo che
rende sicuro tutto il resto: se una rotta dell'app finisse fra le
sconosciute risponderebbe 404 solo aprendola da un link diretto o da un
refresh — invisibile a chi sviluppa, visibilissima a chi lavora.

Oggi: **74 superfici provate, tutte come dichiarate.**
