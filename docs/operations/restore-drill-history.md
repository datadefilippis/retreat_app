# Restore Drill History — AFianco

Audit trail of every restore drill executed. Append-only.
See `restore-drill.md` for the procedure.

---

## Schema

| Date | Backup timestamp restored | Result | Duration | Notes |
|---|---|---|---|---|

---

## Drill log

| Date | Backup timestamp restored | Result | Duration | Notes |
|---|---|---|---|---|
| 2026-05-09 | 20260509_030001 | PASS_WITH_FINDINGS | ~30 min | First drill post-deploy. **Encryption pipeline ✅** (age decrypt OK), **mongorestore ✅** (5186 docs, 57/57 collections match prod within ±5%, only `alerts` 464 vs 465 = -0.2% expected drift), **uploads tarball ✅** (26 entries, ~22 files match prod). **Finding critico**: `config_*.tar.gz` NON include `/etc/letsencrypt/` perché backup.sh cerca il path host che NON esiste — i certs SSL vivono nel volume Docker `ms-certbot-conf` e non vengono backuppati. Senza fix, un DR drill su VPS fresco richiederebbe re-issue certbot (5 min, non disastroso ma non ottimale). Follow-up: vedi sotto. |

---

## How to add a new entry

After completing a drill (procedure in `restore-drill.md`):

1. Add a new row at the top of the table above (newest first).
2. Fields:
   - **Date** = drill execution date (YYYY-MM-DD).
   - **Backup timestamp restored** = the `YYYYMMDD_HHMMSS` from the chosen archive.
   - **Result** = `PASS` or `FAIL: <reason>`.
   - **Duration** = total wall-clock time from start of Step 1 to end of Step 9.
   - **Notes** = any anomaly, deviation from runbook, or follow-up needed.
3. Commit (or schedule a commit batch) so the history lives in git.

If a drill FAILS, also:
- Open a follow-up task in the project tracker.
- Fix the root cause before the next scheduled drill.
- Add a referencing line in this file ("Drill 2026-XX-XX failed because …, fixed in commit YYY").

---

## Findings tracker

Open findings from past drills, to fix before next scheduled drill.

### 1. [2026-05-09] config tarball missing `/etc/letsencrypt`  ✅ RESOLVED same day

**Status**: fixed in commit `<pending>` (deploy/backup.sh + docs/operations/backup-recovery.md). Verified live on VPS by manually re-running `backup.sh` post-deploy: log shows `Volume snapshot: 2 cert chain(s) captured` and `config_*.tar.gz.age` size grew from 8044 → 15313 bytes (+90%).

**Severity**: medium (DR works, but adds 5 min for certbot re-issue on fresh VPS)

**Symptom**: `tar -tzf config_20260509_030001.tar.gz` mostra nginx + .env.production + docker-compose + crontab, ma NON `etc/letsencrypt/`.

**Root cause**: `deploy/backup.sh` line ~`tar ... etc/letsencrypt ...` cerca il path host filesystem `/etc/letsencrypt/` che **non esiste** sul VPS. I certificati SSL (afianco.app + ristobuddy.app) vivono nel volume Docker `ms-certbot-conf`, montato dentro il container nginx in `/etc/letsencrypt`.

**Impact**:
- Backup attuale è recuperabile per dati app + config nginx + .env, ma NON per i certs.
- DR su VPS fresco: dopo restore, certbot va riavviato per riemettere i certs (5 min).
- Non blocca il lancio (i certs si riottengono via certbot facilmente), ma il backup non è "completo" come progettato.

**Fix proposto**: in `backup.sh`, sostituire il riferimento a `/etc/letsencrypt/` con un dump del volume Docker:

```bash
docker run --rm \
    -v ms-certbot-conf:/data:ro \
    -v ${TMP_DIR}:/backup \
    alpine tar czf /backup/letsencrypt.tar.gz -C /data .
# Poi includere letsencrypt.tar.gz nel config_*.tar.gz
```

**Follow-up**: task aperto, da implementare prima del prossimo drill mensile (giugno).
