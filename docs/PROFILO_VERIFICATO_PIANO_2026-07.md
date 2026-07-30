# Piano Profilo pubblico consolidato + Verificato Aurya — 30 lug 2026

Ciclo PV. Richieste founder: (1) foto senza stress di limiti, con
compressione automatica al caricamento e sostituzione che funziona;
(2) intervista NON piu' self-service: la crea il system admin da una
pagina Interviste e la alloca a un operatore, con link YouTube
opzionale embeddato; (3) l'operatore intervistato diventa "Verificato
Aurya" con badge accattivante (glifo del logo) su profilo e
marketplace; (4) intervista su pagina propria raggiungibile con un
bottone dal profilo.

## Parte 1 — Cosa dice il codice (verificato, bug riprodotti)

1. FOTO. Storage unico R3 (S3 o filesystem, mai base64 in Mongo) con
   ottimizzazione server S6 (resize 1600px + WebP q82) MA morta per i
   .jpg: i chiamanti costruiscono il MIME dall'estensione e "image/jpg"
   non e' nella whitelist → la foto piu' comune al mondo salta la
   compressione. Limite 2MB solo backend (5MB prodotti), HEIC rifiutato
   400 (iPhone via Safari si salva solo perche' il picker converte da
   solo). Nessun componente upload condiviso: 11 input file ognuno per
   conto suo, nessuna compressione client.
2. BUG SOSTITUZIONE (riprodotto pixel-per-pixel): il file sul server
   VIENE sostituito ma il filename e' deterministico ({org_id}.jpg) →
   stesso URL → il browser non rifetcha e mostra la foto vecchia (in
   prod S3 con cache immutable 1 anno sarebbe peggio); l'input non
   viene resettato quindi riprovare con lo stesso file non fa nulla;
   al sesto tentativo scatta il rate limit 5/min il cui messaggio ha
   la chiave sbagliata → toast generico "Errore nel caricamento".
   Tripla causa, tutta fixabile a basso rischio.
3. INTERVISTA. Oggi e' self-service puro: l'operatore la scrive nel
   suo editor (public_profile.interview, max 12 coppie Q&A) anche se
   il copy dice "la compila Aurya". Appare inline su /o/#intervista e
   come link dalla pagina rete. Il flag network_member e' GIA' solo
   system admin (bottone "Rete" nel pannello) ed e' gia' nel payload
   del profilo ma mai renderizzato come badge.
4. ADMIN. Pannello a tab (12): una vista nuova = un file Tab + due
   righe in AdminPage. Endpoint org admin gia' pronti per aggancio.
5. BADGE. Logo loto+sole in /public/logo-aurya-512.png, ori brand
   #8a7440/#cbb578; pattern pillola gia' rodato (In evidenza GT3) su
   hero profilo e card marketplace.

## Parte 2 — Onde PV

### PV1 — Foto solide (compressione client + fix sostituzione)
1. Helper condiviso frontend src/lib/compressImage.js: nativo, zero
   dipendenze (createImageBitmap → canvas → toBlob webp q0.82,
   resize max 1600px lato lungo, fallback jpeg q0.85). Un file da
   8-12MB scende a 150-400KB prima di partire. accept="image/*",
   niente piu' limiti percepiti; il 2MB backend resta come cintura.
2. Helper applicato a TUTTE le superfici upload immagine (profilo:
   cover, ritratto, gallery, logo; poi servizio/ritiro/listino, stessi
   input): spinner "Ottimizzo la foto" durante la compressione.
3. Fix sostituzione: suffisso random nel filename anche per cover,
   ritratto e logo (pattern gia' usato dalla gallery) → URL nuovo a
   ogni upload, cache mai stantia (S3 incluso); reset input dopo ogni
   upload; cleanup vecchi file con glob {org_id}*.
4. Fix pipeline server: MIME map corretta (.jpg → image/jpeg) nei 6
   chiamanti (riattiva la WebP oggi saltata); HEIC/HEIF accettati via
   pillow-heif (wheel puro, +1 dipendenza leggera) e convertiti WebP
   come il resto; messaggio 429 leggibile (chiave error vs detail).
5. Guardie: MIME map, filename non deterministico, HEIC accettato,
   429 con messaggio, helper presente nelle superfici.

### PV2 — Intervista in mano a system admin
1. Nuova tab "Interviste" nel pannello admin: lista operatori con
   stato intervista (nessuna / in bozza / pubblicata), editor Q&A
   (stesse regole: max 12 coppie, 200/2500 caratteri) + campo "Video
   YouTube (opzionale)" validato (solo URL youtube/youtu.be, salvato
   normalizzato) + azioni Salva bozza / Pubblica / Rimuovi.
2. Backend: PUT /admin/organizations/{org_id}/interview (items,
   video_url, published) con require_system_admin; alla PUBBLICAZIONE
   timbra interview_verified_at (la verita' del badge). Il campo
   interview SPARISCE dal PATCH self-service e la sezione
   "L'intervista" dall'editor operatore (il dato resta dove vive:
   public_profile.interview, zero migrazioni; le interviste
   self-compilate esistenti restano visibili ma NON verificate
   finche' l'admin non le pubblica dalla sua pagina).
3. network_member resta cosa separata (appartenenza alla rete);
   il badge Verificato deriva SOLO da interview_verified_at.

### PV3 — Pagina intervista pubblica + bottone dal profilo
1. Nuova pagina /o/:slug/intervista (MarketplaceShell): video YouTube
   embeddato in alto quando presente (youtube-nocookie, lazy, 16:9),
   poi le Q&A con la grafica editoriale del brand, CTA di ritorno al
   profilo e ai suoi ritiri. SEO: indicizzabile, breadcrumb, meta.
   CONTINUITA' COL PROFILO (richiesta founder): la pagina deve
   sembrare un tutt'uno col profilo anche cambiando pagina — stessa
   testata identitaria (avatar/nome/localita' e badge Verificato
   ripresi dal profilo, stessa palette e cover come sfondo della
   testata), breadcrumb "Operatori › {nome} › Intervista", il bottone
   torna-al-profilo sempre visibile, e le sezioni del profilo
   (ritiri, listino, recensioni) richiamabili dal fondo pagina come
   se si scorresse un'unica scheda.
2. Sul profilo /o/ la sezione inline #intervista diventa un blocco
   compatto: titolo, 1-2 domande di anteprima e bottone "Leggi
   l'intervista" → pagina dedicata. La pagina rete /operatori linka
   la pagina nuova.
3. Il payload pubblico espone interview_video_url e
   interview_verified_at solo se pubblicata.

### PV4 — Badge Verificato Aurya
1. Componente VerifiedAuryaBadge: pillola con il glifo loto del logo
   (asset esistente) + "Verificato Aurya", ori brand su fondo chiaro
   e variante su foto (backdrop-blur come In evidenza). Tooltip:
   "Operatore intervistato e verificato dal team Aurya".
2. Mostrato: hero del profilo /o/ (fila badge esistente), card di
   /esplora-operatori e /operatori (network_member gia' nel payload
   membri; aggiungere verified al payload /public/operators), quick
   view della card. Ordine: Verificato prima di In evidenza.
3. Incentivo: nell'editor profilo operatore un pannello informativo
   "Fatti intervistare da Aurya" (non compilabile: spiega il valore e
   invita a contattare il team) al posto della vecchia sezione.
4. Guardie: badge solo con interview_verified_at; payload coerenti;
   embed solo youtube-nocookie.

Ordine: PV1 → PV2 → PV3 → PV4. Invarianti: storage adapter R3
intatto, dati interviste esistenti mai migrati ne' persi, profilo
pubblico API retrocompatibile, niente dipendenze pesanti (una sola:
pillow-heif server).

## Valore
L'operatore carica qualsiasi foto dal telefono senza pensare a peso e
formati, e la sostituzione funziona sempre. L'intervista diventa un
rito di qualita' gestito da Aurya che produce un badge visibile
ovunque: fiducia per l'utente, incentivo potente per farsi
intervistare, contenuto editoriale indicizzabile per il SEO.
