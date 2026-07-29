# Runbook deploy — ciclo Listino TW1-TW4

Porta in prod il ciclo Listino (docs/LISTINO_PIANO_2026-07.md):
TW1 pagina /listino, TW2 profilo = negozio, TW3 potatura reversibile,
TW4 onboarding 3 passi. SOLO su ok esplicito del founder ("deploya").

Questo runbook copre anche i cicli successivi RS (Ritiri) e PN
(Profilo = negozio v2, checkout inline incluso): stessi passi,
zero migrazioni.

## Cosa cambia per chi e' gia' in prod

1. Nessuna migrazione dati: zero script da lanciare. Il flag
   organizations.legacy_commerce non esiste sui documenti vecchi e
   viene letto come false (mondo snello per tutti).
2. Le 2 org reali si ritrovano il menu snello a 7 voci. Se una
   delle due deve rivedere subito il commerce completo: pannello
   system admin → Organizations → bottone Legacy (nessun deploy).
3. Il service reale esistente ("Consulenza reiki") compare da solo
   in /listino e nella sezione Servizi e prezzi del profilo: e' un
   Product item_type=service come tutti gli altri.
4. /s/{slug} vetrina redirige a /o/{slug}. Legal e checkout /s/
   restano vivi: nessun link Stripe o GDPR si rompe.
5. /inizia diventa a 3 passi per le org non legacy; le org con flag
   legacy acceso vedono ancora i 5 passi storici.

## Sequenza

1. Pre-check locale: suite verde
   (cd backend && REACT_APP_BACKEND_URL=http://localhost:8000 \
    venv/bin/python -m pytest tests/ -q --ignore=tests/test_new_features.py)
2. git push origin main
3. ssh -i ~/.ssh/aurya_deploy root@46.224.0.96
4. cd /opt/aurya && git pull
5. Rebuild e restart (frontend ha nuove rotte e menu, backend nuovi
   endpoint): docker compose build backend frontend &&
   docker compose up -d backend frontend
6. Niente variabili d'ambiente nuove, niente nginx da toccare
   (le rotte /listino e /o/ passano gia' dalla SPA e dalla shell).

## Verifica post-deploy (2 minuti)

1. https://aurya.life/o/{slug reale} → sezione Servizi e prezzi
2. https://aurya.life/s/{slug reale} → redirige a /o/
3. https://aurya.life/s/{slug reale}/privacy → risponde (no redirect)
4. Login operatore reale → menu snello, /listino apre, /inizia a 3 passi
5. Landing evento /e/ esistente → 200 (invariante I1)
6. curl -sA Googlebot https://aurya.life/__seo/o/{slug} | grep OfferCatalog

## Rollback

git revert dei commit TW (fb22532, 6d5807d, 3e78e05, TW4) oppure
checkout del tag precedente + rebuild. Nessun dato da ripristinare:
il ciclo TW non scrive ne' migra nulla.

## Metrica di attivazione (TW4)

GA4 riceve l'evento first_service_online al primo servizio pubblicato
dal listino (rispetta il consenso cookie: parte solo con analytics
accettati). Da monitorare in GA4 → Engagement → Events.

## LM4 — indice di disponibilita' (filtro Quando)

Il ciclo LM4 introduce la collection `availability_index` (denormalizzata,
SOLO ricerca: checkout e slot veri restano su slot_generator). Gli indici
Mongo si creano da soli all'avvio (`create_indexes`, lm4_avidx_*), ma la
collection parte VUOTA: finche' e' vuota il filtro "Quando" su
/operatori resta nascosto (`date_filter_ready: false`) — nessun errore,
solo feature spenta.

1. Rebuild iniziale post-deploy (una tantum, come system admin):
   curl -X POST https://aurya.life/api/admin/availability-index/rebuild \
        -H "Authorization: Bearer $TOKEN_SYSTEM_ADMIN"
   (opzionale ?organization_id=... per una sola org). La risposta
   riporta {orgs, days} indicizzati.
2. Refresh di sicurezza: gia' coperto dallo scheduler in-process
   (job `availability_index_refresh`, ogni 24h, journal in
   scheduler_job_runs). Nessun cron esterno da configurare finche'
   SCHEDULER_ENABLED resta attivo; se lo scheduler fosse spento,
   agganciare un cron esterno che chiama l'endpoint del punto 1.
3. Gli aggiornamenti live (regole orarie, blocchi calendario,
   prenotazioni confermate/annullate) riallineano l'indice da soli,
   best-effort, in background.
