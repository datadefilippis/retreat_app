# Runbook — Flip al sito della rete (fase network in prod)

Piano di riferimento: docs/SITO_RETE_PIANO_2026-07.md (RT0-RT5).
Stato: codice RT1-RT5 completo e verificato in locale. Prod è ferma al
commit 975bc88 (pre-pivot): il flip coincide col PRIMO deploy di questo
codice. Nessun deploy senza ok esplicito del founder.

## Come funziona la fase (ripasso in 3 righe)

- `site_phase()` legge `SITE_PHASE` (network | marketplace); senza env
  esplicita deriva da `PRELAUNCH_MODE` (true → network).
- Prod oggi ha `PRELAUNCH_MODE=true`: al deploy del codice nuovo il sito
  entra DA SOLO in fase network. `SITE_PHASE` si aggiunge comunque, per
  leggibilità e per il flip futuro a marketplace.
- Gli URL non cambiano mai: i blocchi si sostituiscono. Il ritorno al
  marketplace (lancio vero) sarà `SITE_PHASE=marketplace` + restart.

## 0. Gate contenuti (RT0 — decisioni del founder, bloccanti)

- [ ] Testo definitivo del Manifesto (le 3 colonne in ManifestoPage.js
      sono BOZZE da rivedere: "Da dove nasce", "Cosa non ci convince",
      "Cosa vogliamo costruire")
- [ ] Nome, promessa e frequenza della newsletter confermati (bozza
      attuale: "La lettera di Aurya", ogni due settimane)
- [ ] Lead magnet vero pronto (PDF/risorsa) e caricato a un URL stabile
- [ ] Domande standard dell'intervista decise
- [ ] Prime interviste complete pronte da pubblicare (target piano: 5
      profili con intervista, ~800 parole)
- [ ] Almeno 4 articoli del Magazine freschi (ne abbiamo 19 live: ok)

## 1. Env sul server (/opt/aurya/.env.production)

```
SITE_PHASE=network
NEWSLETTER_LEAD_MAGNET_URL=<url del lead magnet, o lasciare vuota>
```

`PRELAUNCH_MODE=true` resta com'è. La lead magnet URL è runtime: si può
aggiungere/cambiare dopo, con un semplice restart del backend.

## 2. Deploy

```
VPS_HOST=root@46.224.0.96 ./deploy/deploy-prod.sh
```

(compose sul server SEMPRE con `--env-file .env.production`.)

## 2b. Dati blog (BN1, una tantum al primo deploy del funnel)

Assegna la categoria ai 10 articoli orfani (idempotente):

```
ssh -i ~/.ssh/aurya_deploy root@46.224.0.96 \
  "cd /opt/aurya && docker compose --env-file .env.production \
   exec backend python scripts/bn1_assign_article_categories.py"
```

## 3. Wipe campioni prod

Le org campione non appaiono in nessuna superficie della fase rete, ma
il DB va pulito comunque (igiene + niente sorprese al flip marketplace):

```
ssh -i ~/.ssh/aurya_deploy root@46.224.0.96 \
  "cd /opt/aurya && docker compose --env-file .env.production \
   exec backend python scripts/wipe_prelaunch_samples.py"
```

## 4. Membri della rete (system admin)

- Login system admin → tab Organizations → bottone "Rete" sulle org
  intervistate (flag `network_member`, solo admin).
- L'operatore compila l'intervista in Impostazioni → Profilo pubblico
  (o la inseriamo noi via PATCH col suo consenso).
- Verifica: la card appare su /operatori, la sezione "L'intervista" sul
  profilo /o/{slug} (cache profilo 45s).

## 5. Verifiche post-flip (da fare subito)

- [ ] `aurya.life/` → home della rete (hero + manifesto + articoli)
- [ ] `/manifesto`, `/operatori`, `/entra-nella-rete`, `/newsletter` → 200
- [ ] Redirect SPA: `/chi-siamo`→`/manifesto`, `/per-operatori`→
      `/entra-nella-rete`, `/cerca-ritiro`→`/newsletter`, `/ritiri`→`/`
- [ ] Shell crawler: `curl -A Googlebot https://aurya.life/manifesto`
      → title "Il manifesto di Aurya", canonical giusto, NO noindex;
      `/chi-siamo` → canonical su /manifesto; `/operatori` → NO noindex
- [ ] `curl https://aurya.life/sitemap-core.xml` → home, manifesto,
      entra-nella-rete, newsletter, operatori (NIENTE ritiri/chi-siamo)
- [ ] Iscrizione newsletter di prova → success + bottone download (se
      lead magnet configurato)

## 6. SEO e canali (dopo la verifica)

- [ ] Google Search Console: resubmit di `https://aurya.life/sitemap.xml`
- [ ] IndexNow: ping automatico sui publish; per le pagine nuove basta
      il resubmit della sitemap
- [ ] GA4: verificare eventi `generate_lead` (lead_context=newsletter) e
      `lead_magnet_download`; marcare generate_lead come conversione
      (founder, da UI GA4)
- [ ] Instagram: link in bio → `aurya.life/newsletter`

## Rollback

La fase è runtime: per tornare alla splash pre-pivot servirebbe il
rollback del codice (redeploy del commit precedente), non della env —
con questo codice `PRELAUNCH_MODE=true` significa già "fase network".
In pratica: il rollback è ri-deployare 975bc88.
