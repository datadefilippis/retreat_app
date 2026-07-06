"""
Background Service — asyncio-based periodic jobs.

Zero new dependencies: uses only Python stdlib asyncio + the existing
alert_service and kpi_snapshot_service.

Design:
- Multiple asyncio.Tasks are created inside the FastAPI lifespan context.
- Each task runs an infinite loop with its own configurable sleep interval.
- Tasks:
    1. Alert + Digest job (every BACKGROUND_ALERT_INTERVAL_HOURS, default 6h):
       - Fetches all organisations that have any module active.
       - Calls generate_and_save_alerts(org_id) for each one.
       - Generates weekly/monthly digests on schedule.
    2. Billing sweep job (every BILLING_SWEEP_INTERVAL_HOURS, default 1h):
       - Finds orgs with expired trials or stale past_due states.
       - Checks Stripe for live subscription status.
       - Syncs internal DB to match Stripe truth.
- Both startup and per-tick errors are caught and logged; the loop continues
  after the next sleep interval on failure.
- Graceful shutdown: CancelledError from asyncio.Task.cancel() is allowed
  to propagate so the lifespan context manager can exit cleanly.

Public API:
    start() -> list[asyncio.Task]  — call inside lifespan startup
    stop(tasks)                    — call inside lifespan shutdown

Configuration (via environment variables):
    BACKGROUND_ALERT_INTERVAL_HOURS  — default 6
    BACKGROUND_INITIAL_DELAY_SECONDS — default 30
    BILLING_SWEEP_INTERVAL_HOURS     — default 1
"""
import asyncio
import logging
import os
from typing import List, Optional, Union

logger = logging.getLogger(__name__)

# ── Configuration ─────────────────────────────────────────────────────────────
#
# Wave 11.2 (2026-05): _ALERT_INTERVAL_HOURS changed from 6 → 24.
#
# Combined with Wave 11.1 reverting non-chat features to Sonnet, the net
# cost of the alert AI analysis stays roughly flat (4× fewer calls × 3.75×
# more expensive model). Net effect: quality jump on narrative synthesis,
# no cost increase.
#
# The digest cron lives inside the same tick (_periodic_job runs both
# alert + digest sequentially) so it also drops to 1×/day. The digest
# generation has its own 24h dedup (B-3 fix in _run_digest_generation)
# and 9-day catch-up window (B-22 fix), so a single daily tick is plenty.
#
# Entitlement gate: the AI portion is already filtered by
# check_module_access in services/alert_service.py:103-112 — orgs on
# free/starter (alert_analysis: 0) get rule-based detection + email
# only, zero Anthropic consumption. Wave 11 keeps this behaviour
# intentionally (Option 2 from the audit).
_ALERT_INTERVAL_HOURS: float = float(
    os.environ.get("BACKGROUND_ALERT_INTERVAL_HOURS", "24")
)
_INITIAL_DELAY_SECONDS: float = float(
    os.environ.get("BACKGROUND_INITIAL_DELAY_SECONDS", "30")
)
_BILLING_SWEEP_INTERVAL_HOURS: float = float(
    os.environ.get("BILLING_SWEEP_INTERVAL_HOURS", "1")
)


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_active_org_ids() -> list[str]:
    """Return distinct org_id strings for all orgs with any module active.

    Queries organization_modules collection directly instead of going through
    a service layer — keeps the dependency graph minimal.

    Returns an empty list on any error (never raises).
    """
    try:
        from database import organization_modules_collection
        cursor = organization_modules_collection.find(
            {"is_active": True},
            {"_id": 0, "organization_id": 1},
        )
        docs = await cursor.to_list(1000)
        return list({d["organization_id"] for d in docs if d.get("organization_id")})
    except Exception as exc:
        logger.error("background_service: failed to fetch active orgs: %s", exc, exc_info=True)
        return []


async def _run_alert_check_for_all_orgs() -> None:
    """Run alert generation for every org with any active module."""
    from services.alert_service import generate_and_save_alerts

    org_ids = await _get_active_org_ids()
    if not org_ids:
        logger.debug("background_service: no active orgs — skipping alert tick")
        return

    logger.info("background_service: running alert check for %d org(s)", len(org_ids))
    for org_id in org_ids:
        try:
            result = await generate_and_save_alerts(org_id)
            generated = result.get("alerts_generated", 0)
            if generated:
                logger.info(
                    "background_service: %d new alert(s) for org=%s", generated, org_id
                )
        except Exception as exc:
            logger.error(
                "background_service: alert error for org=%s: %s", org_id, exc, exc_info=True
            )


async def _run_digest_generation() -> None:
    """Generate weekly/monthly digests for all modules with a digest_builder.

    Weekly: Monday (weekday=0) on the first tick of the day.
    Monthly: 1st of the month on the first tick.

    Dispatches through the module registry so each module provides its own
    digest content.  Entitlement is checked via the ai_assistant module's
    "digest" feature key (current gating model).
    """
    from datetime import datetime, timezone
    from core.module_registry import get_all as registry_get_all
    from repositories import digest_repository, organization_repository
    from models.digest import Digest
    from services.module_access import check_module_access, can_use_module

    from database import module_configs_collection

    DAY_MAP = {"monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
               "friday": 4, "saturday": 5, "sunday": 6}

    now = datetime.now(timezone.utc)
    current_weekday = now.weekday()  # 0=Monday, 6=Sunday
    generate_monthly = now.day == 1

    org_ids = await _get_active_org_ids()
    if not org_ids:
        return

    # Collect modules that have a digest_builder capability
    digest_modules = [m for m in registry_get_all() if m.digest_builder is not None]
    if not digest_modules:
        return

    for org_id in org_ids:
        # Soft gate: skip digest generation if org has no "digest" entitlement
        try:
            org_doc = await organization_repository.find_by_id(org_id)
            if not org_doc:
                continue
            await check_module_access(
                org_id, "ai_assistant", "digest", org_doc=org_doc,
            )
        except Exception:
            logger.debug("background_service: digest skipped for org=%s (no entitlement)", org_id)
            continue

        # Read org's digest preferences
        config_doc = await module_configs_collection.find_one(
            {"organization_id": org_id, "module_key": "cashflow_monitor"},
            {"_id": 0, "settings": 1},
        )
        org_settings = (config_doc or {}).get("settings", {})
        org_digest_day = org_settings.get("weekly_digest_day", "sunday")
        org_period_type = org_settings.get("digest_period_type", "weekly")

        # Check if today is this org's weekly digest day
        org_weekday_num = DAY_MAP.get(org_digest_day, 6)
        generate_weekly = current_weekday == org_weekday_num

        # Skip digest generation entirely if email is disabled (saves CPU/Claude costs)
        email_digest_enabled = org_settings.get("email_weekly_digest") is not False
        if not email_digest_enabled:
            logger.debug("background_service: digest skipped for org=%s (email_weekly_digest disabled)", org_id)
            continue

        # ── B-22 fix — catch-up window for missed weekly digests ──────────
        # Without this, a single outage on the configured weekday silently
        # eats the digest until the SAME weekday rolls around the next
        # week. The diagnostic confirmed Centro Benessere lost every
        # weekly digest since module activation (backend down on the
        # Monday slot, no recovery path). The catch-up fires the digest
        # opportunistically when:
        #   - the org has had at least one digest before (we don't fire
        #     for a freshly-created org outside its configured day — that
        #     would be confusing for the merchant), AND
        #   - the last weekly digest is at least 9 days old (7-day window
        #     + 2-day grace, so a 1-day glitch doesn't immediately
        #     double-fire).
        # The dedup-24h check below guarantees idempotency even if the
        # tick repeats inside the catch-up.
        if not generate_weekly and not generate_monthly:
            last_weekly = await digest_repository.find_latest(org_id, digest_type="weekly")
            if last_weekly and last_weekly.get("created_at"):
                last_created = last_weekly["created_at"]
                if isinstance(last_created, str):
                    last_created = datetime.fromisoformat(last_created)
                if last_created.tzinfo is None:
                    last_created = last_created.replace(tzinfo=timezone.utc)
                days_since = (now - last_created).days
                if days_since >= 9:
                    generate_weekly = True
                    logger.info(
                        "background_service: catch-up — fire weekly digest for org=%s (last was %d days ago)",
                        org_id, days_since,
                    )

        if not generate_weekly and not generate_monthly:
            continue

        # B-14 fix — read AI gating through the same entitlements system
        # the rest of the platform uses (was: hard-coded plan slug list
        # duplicated in routers/digests.py, prone to drift when new plans
        # are added). The entitlement guard above (check_module_access)
        # already validated digest access; here we only need to know
        # whether the AI tier is part of THIS org's plan, to enable the
        # AI insights/recommendations section in the PDF.
        include_ai = await can_use_module(org_doc, "ai_assistant", "digest")
        locale = org_doc.get("settings", {}).get("locale", "it")

        for module in digest_modules:
            # Build digest configs: weekly uses org's preferred period type
            digest_configs = []
            if generate_weekly:
                period = 7 if org_period_type == "weekly" else 30
                digest_configs.append((org_period_type, period))
            if generate_monthly and not generate_weekly:
                digest_configs.append(("monthly", 30))

            for digest_type, period_days in digest_configs:
                try:
                    # ── B-3 fix — 24h dedup ──────────────────────────────
                    # The tick runs every 6h, so on the configured weekday
                    # we'd otherwise hit ``digest_builder`` 4 times back to
                    # back (08:00/14:00/20:00/02:00). The diagnostic
                    # confirmed this empirically: 10 monthly digests for
                    # one org on 2026-05-01 in a 2-hour window when the
                    # uvicorn --reload triggered repeated restarts. The
                    # check below makes the tick idempotent — first hit
                    # wins, the rest log + skip. The 24h window also
                    # covers the catch-up branch above without producing
                    # a same-day duplicate.
                    #
                    # Wave 13.7 — note: this dedup intentionally checks
                    # ONLY (org, digest_type) within 24h. The cron always
                    # uses the same window per (digest_type, today), so a
                    # repeat tick within 24h is by definition a duplicate.
                    # Manual triggers with different windows are dedup-
                    # safe because they go through routers/digests.py
                    # (no 24h check), and ``find_latest`` now supports
                    # explicit period_start/period_end filters for any
                    # future caller that needs window-precise lookup.
                    existing = await digest_repository.find_latest(org_id, digest_type=digest_type)
                    if existing and existing.get("created_at"):
                        last_at = existing["created_at"]
                        if isinstance(last_at, str):
                            last_at = datetime.fromisoformat(last_at)
                        if last_at.tzinfo is None:
                            last_at = last_at.replace(tzinfo=timezone.utc)
                        hours_since = (now - last_at).total_seconds() / 3600.0
                        if hours_since < 24:
                            logger.info(
                                "background_service: digest dedup — skip %s for org=%s (last %d h ago)",
                                digest_type, org_id, int(hours_since),
                            )
                            continue

                    result = await module.digest_builder(
                        org_id=org_id, period_days=period_days, digest_type=digest_type,
                        locale=locale, format="report", include_ai=include_ai,
                    )
                    if result:
                        pdf_bytes = result.pop("pdf_bytes", None)
                        digest = Digest(**result)
                        doc = await digest_repository.create(digest)

                        # Store PDF and send email
                        if pdf_bytes:
                            await digest_repository.store_pdf(doc["id"], org_id, pdf_bytes)
                            from services.alert_notification_service import send_digest_report_email
                            await send_digest_report_email(
                                org_id=org_id, pdf_bytes=pdf_bytes,
                                sections=result.get("sections", {}),
                                digest_type=digest_type,
                                period_label=f"{result.get('period_start', '')} — {result.get('period_end', '')}",
                                locale=locale,
                            )

                        logger.info(
                            "background_service: %s digest report created for org=%s module=%s (pdf=%s)",
                            digest_type, org_id, module.module_key, bool(pdf_bytes),
                        )
                except Exception as exc:
                    logger.error(
                        "background_service: %s digest error for org=%s module=%s: %s",
                        digest_type, org_id, module.module_key, exc, exc_info=True,
                    )


# ── Main loop ─────────────────────────────────────────────────────────────────

_LAST_TICK_KEY = "background_last_tick_at"


async def _read_last_tick_iso() -> Optional[str]:
    """Read the persisted last-tick timestamp from platform_settings.

    Wave 9.C.4 — restart resilience: on every restart the in-memory
    "I just ran the tick" state is lost. Without persistence, the
    cron's _INITIAL_DELAY_SECONDS (30s) + _ALERT_INTERVAL_HOURS (6h)
    means a backend that restarts every 1-3 hours (frequent deploys,
    `uvicorn --reload`) MIGHT never reach the digest path. Reading a
    persisted timestamp lets us fire the tick immediately when more
    than ``interval`` has elapsed since the last successful tick.
    """
    try:
        from database import platform_settings_collection
        doc = await platform_settings_collection.find_one(
            {"key": _LAST_TICK_KEY}, {"_id": 0, "value": 1},
        )
        if doc and isinstance(doc.get("value"), str):
            return doc["value"]
    except Exception as exc:
        logger.debug("background_service: last_tick read failed: %s", exc)
    return None


async def _write_last_tick_iso() -> None:
    """Persist last-tick timestamp to platform_settings."""
    try:
        from database import platform_settings_collection
        from datetime import datetime, timezone
        await platform_settings_collection.update_one(
            {"key": _LAST_TICK_KEY},
            {"$set": {"value": datetime.now(timezone.utc).isoformat()}},
            upsert=True,
        )
    except Exception as exc:
        logger.debug("background_service: last_tick write failed: %s", exc)


async def _periodic_job() -> None:
    """Infinite loop: sleep → run → repeat.

    Structured so that:
    - asyncio.CancelledError propagates (clean shutdown).
    - Any other exception in the tick body is caught; the loop continues
      after the next sleep interval.

    Wave 9.C.4 — restart-resilient initial delay: if the last successful
    tick was more than ``interval`` ago (or the timestamp is missing),
    we fire the tick after the small initial delay. Otherwise we sleep
    until the gap closes. This prevents digest starvation on backends
    that restart frequently.
    """
    interval_seconds = _ALERT_INTERVAL_HOURS * 3600

    logger.info(
        "background_service: starting — initial delay %.0fs, interval %.1fh",
        _INITIAL_DELAY_SECONDS,
        _ALERT_INTERVAL_HOURS,
    )

    # Wave 9.C.4 — restart-resilient initial wait. Compute how long to
    # sleep based on the persisted last-tick timestamp, not just the
    # static _INITIAL_DELAY_SECONDS.
    last_tick = await _read_last_tick_iso()
    initial_sleep = _INITIAL_DELAY_SECONDS
    if last_tick:
        try:
            from datetime import datetime, timezone
            last_dt = datetime.fromisoformat(last_tick.replace("Z", "+00:00"))
            if last_dt.tzinfo is None:
                last_dt = last_dt.replace(tzinfo=timezone.utc)
            elapsed = (datetime.now(timezone.utc) - last_dt).total_seconds()
            if elapsed >= interval_seconds:
                logger.info(
                    "background_service: last tick was %.1fh ago "
                    "(interval=%.1fh) — firing immediately after initial delay",
                    elapsed / 3600, _ALERT_INTERVAL_HOURS,
                )
                initial_sleep = _INITIAL_DELAY_SECONDS
            else:
                remaining = interval_seconds - elapsed
                initial_sleep = max(_INITIAL_DELAY_SECONDS, remaining)
                logger.info(
                    "background_service: last tick was %.1fh ago, "
                    "sleeping %.0fs to align with the schedule",
                    elapsed / 3600, initial_sleep,
                )
        except (ValueError, TypeError) as exc:
            logger.debug("background_service: last_tick parse failed: %s", exc)

    await asyncio.sleep(initial_sleep)

    _alert_running = False

    while True:
        if _alert_running:
            logger.warning("background_service: alert tick skipped — previous still running")
            await asyncio.sleep(interval_seconds)
            continue

        _alert_running = True
        _tick_start = asyncio.get_event_loop().time()
        try:
            await _run_alert_check_for_all_orgs()
            _elapsed = asyncio.get_event_loop().time() - _tick_start
            if _elapsed > interval_seconds * 0.8:
                logger.warning("background_service: alert tick took %.1fs (interval=%.1fs)", _elapsed, interval_seconds)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.error("background_service: unhandled tick error: %s", exc, exc_info=True)
        finally:
            _alert_running = False

        # Digest generation (weekly Monday, monthly 1st)
        try:
            await _run_digest_generation()
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.error("background_service: digest tick error: %s", exc, exc_info=True)

        # Wave 9.C.4 — persist tick completion so a restart can compute
        # how long it has been since the last successful tick. Best-effort
        # write (failures don't abort the loop).
        await _write_last_tick_iso()

        try:
            await asyncio.sleep(interval_seconds)
        except asyncio.CancelledError:
            raise


# ── Billing sweep loop ───────────────────────────────────────────────────────

async def _billing_sweep_job() -> None:
    """Periodic billing state sync: find stale states, check Stripe, sync DB.

    Runs every BILLING_SWEEP_INTERVAL_HOURS (default 1h).
    Staggered start: initial delay + 60s to avoid overlapping with alert job.
    """
    interval_seconds = _BILLING_SWEEP_INTERVAL_HOURS * 3600

    logger.info(
        "background_service: billing sweep starting — interval %.1fh",
        _BILLING_SWEEP_INTERVAL_HOURS,
    )

    # Stagger start to avoid concurrent DB pressure with the alert job
    await asyncio.sleep(_INITIAL_DELAY_SECONDS + 60)

    while True:
        try:
            from services.billing_lifecycle import run_billing_sweep
            result = await run_billing_sweep()
            total = result["expired_trials_processed"] + result["past_due_processed"]
            if total > 0 or result["errors"] > 0:
                logger.info(
                    "background_service: billing sweep tick — "
                    "expired_trials=%d, past_due=%d, errors=%d",
                    result["expired_trials_processed"],
                    result["past_due_processed"],
                    result["errors"],
                )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.error(
                "background_service: billing sweep error: %s", exc, exc_info=True,
            )

        try:
            await asyncio.sleep(interval_seconds)
        except asyncio.CancelledError:
            raise


# ── Hard-delete cleanup job (v6.0, GDPR art. 17) ─────────────────────────────

_HARD_DELETE_CHECK_INTERVAL_HOURS = float(
    os.environ.get("HARD_DELETE_CHECK_INTERVAL_HOURS", "6")
)
_HARD_DELETE_GRACE_DAYS = 30


async def _hard_delete_cleanup_job() -> None:
    """Permanently delete orgs deactivated more than 30 days ago.

    Runs every HARD_DELETE_CHECK_INTERVAL_HOURS hours (default 6).
    Idempotent: delete_many on already-deleted records is a no-op.
    """
    from datetime import timedelta
    interval_seconds = _HARD_DELETE_CHECK_INTERVAL_HOURS * 3600

    logger.info(
        "background_service: hard delete cleanup starting — interval %.1fh, grace %dd",
        _HARD_DELETE_CHECK_INTERVAL_HOURS, _HARD_DELETE_GRACE_DAYS,
    )

    # Stagger: start after alert + billing sweep have had their turns
    await asyncio.sleep(_INITIAL_DELAY_SECONDS + 120)

    while True:
        try:
            from database import organizations_collection
            from services.hard_delete_service import cascade_hard_delete
            from datetime import datetime, timezone

            cutoff = datetime.now(timezone.utc) - timedelta(days=_HARD_DELETE_GRACE_DAYS)

            # Find orgs past the 30-day grace period
            cursor = organizations_collection.find(
                {
                    "deactivated_at": {"$ne": None, "$lt": cutoff},
                },
                {"_id": 0, "id": 1, "name": 1},
            )
            orgs = await cursor.to_list(100)  # process max 100 per tick

            if orgs:
                logger.info(
                    "background_service: hard delete cleanup — found %d org(s) to purge",
                    len(orgs),
                )

            for org in orgs:
                org_id = org["id"]
                try:
                    counts = await cascade_hard_delete(org_id)
                    logger.info(
                        "background_service: hard deleted org %s (%s) — %s",
                        org_id, org.get("name", "?"), counts,
                    )
                except Exception as exc:
                    logger.error(
                        "background_service: hard delete failed for org %s: %s",
                        org_id, exc, exc_info=True,
                    )

        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.error(
                "background_service: hard delete cleanup error: %s", exc, exc_info=True,
            )

        try:
            await asyncio.sleep(interval_seconds)
        except asyncio.CancelledError:
            raise


# ── Hard-delete WARNING email (Wave GDPR-Admin A) ────────────────────────────
#
# Sends a final reminder email 7 days before the hard-delete cascade
# fires. Runs as a SEPARATE job from the actual cleanup so:
#   - The cleanup logic (already in prod) is untouched.
#   - This new job can be enabled/disabled independently.
#   - A failure in the warning loop never blocks or delays the cleanup.
#
# Idempotency: orgs that already received the warning have
# ``hard_delete_warning_sent_at`` set; the cursor filters them out so
# re-runs don't spam users.

_HARD_DELETE_WARNING_INTERVAL_HOURS = float(
    os.environ.get("HARD_DELETE_WARNING_INTERVAL_HOURS", "12")
)
# Trigger the warning when the org is in [GRACE_DAYS - WARNING_LEAD_DAYS,
# GRACE_DAYS - WARNING_LEAD_DAYS + 1) days deactivated. So with the
# default 30-day grace and 7-day lead, the warning fires when the org
# has been deactivated for 23-24 days.
_HARD_DELETE_WARNING_LEAD_DAYS = int(
    os.environ.get("HARD_DELETE_WARNING_LEAD_DAYS", "7")
)


async def _hard_delete_warning_job() -> None:
    """Send a final reminder email 7 days before the hard-delete cascade.

    Loop:
      every HARD_DELETE_WARNING_INTERVAL_HOURS hours
        find orgs where:
          deactivated_at < (now - (GRACE_DAYS - LEAD_DAYS))   # at or past warning point
          AND deactivated_at >= (now - GRACE_DAYS)             # not already overdue
          AND hard_delete_warning_sent_at IS NULL              # never warned
        for each org:
          fetch all active org members (users)
          send send_final_delete_warning(...) in their locale
          mark hard_delete_warning_sent_at = now on the org doc

    Idempotency: the warning flag prevents duplicate sends across job
    runs. Failure to send to one user does NOT mark the flag — only a
    fully-successful send batch (all users notified or non-blocking
    individual failures logged) sets the flag.
    """
    from datetime import timedelta, datetime, timezone
    interval_seconds = _HARD_DELETE_WARNING_INTERVAL_HOURS * 3600

    logger.info(
        "background_service: hard delete warning starting — "
        "interval %.1fh, lead %dd before %dd grace cutoff",
        _HARD_DELETE_WARNING_INTERVAL_HOURS,
        _HARD_DELETE_WARNING_LEAD_DAYS,
        _HARD_DELETE_GRACE_DAYS,
    )

    # Stagger after the other jobs to keep DB pressure low
    await asyncio.sleep(_INITIAL_DELAY_SECONDS + 90)

    while True:
        try:
            from database import organizations_collection, users_collection
            from services.email_service import send_final_delete_warning

            now = datetime.now(timezone.utc)
            warning_cutoff = now - timedelta(
                days=_HARD_DELETE_GRACE_DAYS - _HARD_DELETE_WARNING_LEAD_DAYS
            )
            grace_cutoff = now - timedelta(days=_HARD_DELETE_GRACE_DAYS)

            # Orgs in the warning window: deactivated longer than
            # (grace - lead) but not yet past full grace.
            # Also: must not have been warned yet.
            cursor = organizations_collection.find(
                {
                    "deactivated_at": {
                        "$ne": None,
                        "$lt": warning_cutoff,
                        "$gte": grace_cutoff,
                    },
                    "$or": [
                        {"hard_delete_warning_sent_at": {"$exists": False}},
                        {"hard_delete_warning_sent_at": None},
                    ],
                },
                {"_id": 0, "id": 1, "name": 1, "deactivated_at": 1},
            )
            orgs = await cursor.to_list(50)

            if orgs:
                logger.info(
                    "background_service: hard delete warning — "
                    "found %d org(s) in warning window",
                    len(orgs),
                )

            for org in orgs:
                org_id = org["id"]
                org_name = org.get("name", org_id)
                deactivated_at = org.get("deactivated_at")
                if isinstance(deactivated_at, str):
                    deactivated_at = datetime.fromisoformat(deactivated_at)
                if deactivated_at.tzinfo is None:
                    deactivated_at = deactivated_at.replace(tzinfo=timezone.utc)
                days_ago = (now - deactivated_at).days
                delete_date = deactivated_at + timedelta(days=_HARD_DELETE_GRACE_DAYS)
                delete_date_str = delete_date.strftime("%Y-%m-%d")

                # Fetch the org members (org-scoped; admins included)
                members_cursor = users_collection.find(
                    {"organization_id": org_id},
                    {"_id": 0, "email": 1, "locale": 1, "name": 1},
                )
                members = await members_cursor.to_list(50)

                sent_count = 0
                for m in members:
                    email = m.get("email")
                    if not email:
                        continue
                    locale = m.get("locale") or "it"
                    try:
                        if send_final_delete_warning(
                            email, org_name, days_ago, delete_date_str, locale,
                        ):
                            sent_count += 1
                    except Exception as exc:
                        logger.warning(
                            "background_service: hard delete warning email "
                            "to %s for org %s failed: %s",
                            email, org_id, exc,
                        )

                # Mark the org so we don't re-send. We mark even if a
                # subset of users failed (the failures are logged for
                # ops follow-up; the rest of the batch already got their
                # warning, and re-running would re-send to them too).
                if sent_count > 0 or not members:
                    await organizations_collection.update_one(
                        {"id": org_id},
                        {"$set": {"hard_delete_warning_sent_at": now}},
                    )
                logger.info(
                    "background_service: hard delete warning for org %s "
                    "(%s) — sent=%d/%d, delete_date=%s",
                    org_id, org_name, sent_count, len(members), delete_date_str,
                )

        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.error(
                "background_service: hard delete warning error: %s",
                exc, exc_info=True,
            )

        try:
            await asyncio.sleep(interval_seconds)
        except asyncio.CancelledError:
            raise


# ── Order cleanup loop (Fase 6b) ─────────────────────────────────────────────

_ORDER_CLEANUP_INTERVAL_HOURS: float = float(
    os.environ.get("ORDER_CLEANUP_INTERVAL_HOURS", "24")
)


async def _order_cleanup_job() -> None:
    """Periodically expire abandoned unpaid draft orders.

    Runs every ORDER_CLEANUP_INTERVAL_HOURS (default 24h).
    Never touches collected, confirmed, cancelled, or completed orders.
    Delegates the selection + update to services.order_cleanup_service.
    """
    interval_seconds = _ORDER_CLEANUP_INTERVAL_HOURS * 3600

    logger.info(
        "background_service: order cleanup starting — interval %.1fh",
        _ORDER_CLEANUP_INTERVAL_HOURS,
    )

    # Stagger further than hard-delete to avoid same-tick DB pressure
    await asyncio.sleep(_INITIAL_DELAY_SECONDS + 180)

    while True:
        try:
            from services.order_cleanup_service import sweep_orphan_draft_orders
            summary = await sweep_orphan_draft_orders(apply=True)
            if summary.get("candidates", 0) > 0:
                logger.info(
                    "background_service: order cleanup tick — "
                    "candidates=%d expired=%d grace=%dd",
                    summary["candidates"], summary["expired"], summary["grace_days"],
                )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.error(
                "background_service: order cleanup error: %s", exc, exc_info=True,
            )

        try:
            await asyncio.sleep(interval_seconds)
        except asyncio.CancelledError:
            raise


# ── v5.8 / Onda 6: Quota warning sweep ───────────────────────────────────────
#
# Periodic job that scans every active org and sends a quota_warning email
# when usage hits 80% / 100% of effective_limit on any monitored metric.
# Idempotency is enforced by the unique index on org_quota_notices —
# duplicate notices for (org, metric, level, period_start) raise
# DuplicateKeyError which the email service catches as "already sent".
#
# Default cadence: 6h. Configurable via QUOTA_SWEEP_INTERVAL_HOURS env.
# Stagger: starts ~180s after boot to avoid bumping into other crons.

_QUOTA_SWEEP_INTERVAL_HOURS = float(
    os.environ.get("QUOTA_SWEEP_INTERVAL_HOURS", "6")
)

# Metrics we monitor. Tuple shape: (metric_key, monthly_quota?). Monthly
# quotas count usage in the current calendar month; non-monthly metrics
# (stores_max, products) compute current count snapshot-style.
#
# Adding a metric to this list is the only change needed to monitor it
# — quota_email_service handles the rest via METRIC_TO_MODULE / labels.
_MONITORED_METRICS = [
    # (metric_key, module_key, is_monthly)
    ("chat",            "ai_assistant",     True),
    ("digest",          "ai_assistant",     True),
    ("data_rows",       "cashflow_monitor", True),
    ("orders_monthly",  "commerce",         True),
    ("products",        "product_catalog",  False),  # snapshot
    ("stores_max",      "commerce",         False),  # snapshot
]


async def _count_monthly_usage(org_id: str, module_key: str, feature_key: str) -> int:
    """Count usage for the current calendar month.

    Three sources depending on the metric:
      · ai_assistant.{chat, digest}            → AIUsageEvent records (sum quantity)
      · cashflow_monitor.data_rows             → AIUsageEvent records (sum quantity)
      · commerce.orders_monthly                → orders by created_at

    v5.8 / Onda 9.Y.0.2 (Step D) — `cashflow_monitor.data_rows` now reads
    from `ai_usage_events` (the SAME source the gate uses via
    repositories.usage_repository.count_usage). Pre-9.Y.0.2 this counter
    read from `datasets_collection.row_count` while the gate read from
    `ai_usage_events`, so the dashboard could show 145/200 while the gate
    saw only 80/200 (or vice versa). After Onda 9.Y.0/9.Y.0.1 patches
    every cashflow insert path now writes a usage event with the actual
    inserted row count, so `ai_usage_events` is the authoritative
    real-time source. UI dashboard and gate now agree.

    All AI / data_rows branches use $sum quantity (matches the gate's
    aggregation in repositories/usage_repository.py:38) — counting
    documents with `count_documents` would silently desync if any
    future bulk path writes events with `quantity > 1`.

    Each branch is wrapped so a Mongo blip never crashes the sweep —
    we'd rather skip a single org than abort the whole tick.
    """
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    month_start_iso = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()

    try:
        # v5.8 / Onda 9.Y.0.3 — cashflow_monitor.data_rows uses the same
        # authoritative source as the gate (max of ai_usage_events and
        # actual row counts in the 5 cashflow collections). This guarantees
        # the Settings dashboard and the entry-form gate ALWAYS show the
        # same number — no more "dashboard says exceeded but the form
        # still lets me save" mismatch.
        if module_key == "cashflow_monitor" and feature_key == "data_rows":
            from services.module_access import (
                _count_data_rows_authoritative,
                get_current_period_range,
            )
            period_start, period_end = get_current_period_range()
            return await _count_data_rows_authoritative(org_id, period_start, period_end)

        # ai_assistant.{chat,digest}: simple aggregation on ai_usage_events.
        # Single source — events are written by chat_service / digest_service
        # which never had the legacy-data instrumentation gap.
        if module_key == "ai_assistant":
            from database import db
            pipeline = [
                {"$match": {
                    "organization_id": org_id,
                    "module_key": module_key,
                    "feature": feature_key,
                    "created_at": {"$gte": month_start_iso},
                }},
                {"$group": {
                    "_id": None,
                    "total": {"$sum": {"$ifNull": ["$quantity", 1]}},
                }},
            ]
            cursor = db["ai_usage_events"].aggregate(pipeline)
            async for doc in cursor:
                return int(doc.get("total", 0) or 0)
            return 0
        if module_key == "commerce" and feature_key == "orders_monthly":
            from database import orders_collection
            return await orders_collection.count_documents({
                "organization_id": org_id,
                "created_at": {"$gte": month_start_iso},
            })
    except Exception as exc:  # noqa: BLE001 — best-effort
        logger.warning(
            "quota_sweep: usage count failed org=%s metric=%s.%s: %s",
            org_id, module_key, feature_key, exc,
        )
    return 0


async def _count_snapshot_usage(org_id: str, module_key: str, feature_key: str) -> int:
    """Count current state for non-monthly metrics (stores_max, products)."""
    try:
        if module_key == "commerce" and feature_key == "stores_max":
            from database import stores_collection
            return await stores_collection.count_documents(
                {"organization_id": org_id, "is_active": True},
            )
        if module_key == "product_catalog" and feature_key == "products":
            from database import products_collection
            return await products_collection.count_documents(
                {"organization_id": org_id, "is_active": True},
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "quota_sweep: snapshot count failed org=%s metric=%s.%s: %s",
            org_id, module_key, feature_key, exc,
        )
    return 0


async def _check_one_org_quotas(org_id: str) -> dict:
    """Check every monitored metric for one org and dispatch warning emails.

    Returns counters {checked, warn_sent, exceeded_sent, skipped}.
    """
    from services.module_access import get_effective_limit
    from services.quota_email_service import notify_quota_warning_email

    counters = {"checked": 0, "warn_sent": 0, "exceeded_sent": 0, "skipped": 0}

    for metric_key, module_key, is_monthly in _MONITORED_METRICS:
        counters["checked"] += 1

        # Effective limit considers base plan + active add-ons (Onda 3).
        try:
            limit = await get_effective_limit(org_id, module_key, metric_key)
        except Exception as exc:  # noqa: BLE001
            logger.debug("quota_sweep: limit lookup failed org=%s %s: %s", org_id, metric_key, exc)
            counters["skipped"] += 1
            continue

        if limit == -1 or limit == 0:
            # -1 = unlimited (nothing to warn about)
            #  0 = feature disabled (no quota concept)
            counters["skipped"] += 1
            continue

        # Resolve current usage (monthly count vs snapshot)
        if is_monthly:
            usage = await _count_monthly_usage(org_id, module_key, metric_key)
        else:
            usage = await _count_snapshot_usage(org_id, module_key, metric_key)

        # Warning levels
        if usage >= limit:
            sent = await notify_quota_warning_email(
                org_id, metric_key, "exceeded", usage, limit,
            )
            if sent:
                counters["exceeded_sent"] += 1
        elif usage >= int(limit * 0.8):
            sent = await notify_quota_warning_email(
                org_id, metric_key, "warn_80", usage, limit,
            )
            if sent:
                counters["warn_sent"] += 1

    return counters


async def _quota_warning_sweep_job() -> None:
    """Periodic quota-warning email sweep.

    Idempotent per (org, metric, level, period_start) via the unique index
    on org_quota_notices. Safe to run on every interval — duplicates are
    silently skipped at the DB layer.
    """
    interval_seconds = _QUOTA_SWEEP_INTERVAL_HOURS * 3600

    logger.info(
        "background_service: quota_warning_sweep starting — interval %.1fh",
        _QUOTA_SWEEP_INTERVAL_HOURS,
    )

    # Stagger AFTER alert + billing + hard-delete jobs (initial+180s)
    await asyncio.sleep(_INITIAL_DELAY_SECONDS + 180)

    while True:
        try:
            org_ids = await _get_active_org_ids()
            if not org_ids:
                logger.debug("quota_sweep: no active orgs")
            else:
                totals = {"checked": 0, "warn_sent": 0, "exceeded_sent": 0, "skipped": 0}
                for org_id in org_ids:
                    try:
                        c = await _check_one_org_quotas(org_id)
                        for k, v in c.items():
                            totals[k] = totals.get(k, 0) + v
                    except Exception as exc:  # noqa: BLE001
                        logger.error(
                            "quota_sweep: org=%s tick error: %s",
                            org_id, exc, exc_info=True,
                        )
                logger.info(
                    "quota_sweep: tick summary — orgs=%d checks=%d warn_sent=%d exceeded_sent=%d skipped=%d",
                    len(org_ids), totals["checked"], totals["warn_sent"],
                    totals["exceeded_sent"], totals["skipped"],
                )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.error(
                "background_service: quota_warning_sweep error: %s", exc, exc_info=True,
            )

        try:
            await asyncio.sleep(interval_seconds)
        except asyncio.CancelledError:
            raise


# ── Catalog drift digest job (Onda 10 Step E.1) ──────────────────────────────

_CATALOG_DRIFT_CHECK_INTERVAL_HOURS = float(
    os.environ.get("CATALOG_DRIFT_CHECK_INTERVAL_HOURS", "24")
)
_CATALOG_DRIFT_DIGEST_RECIPIENT = os.environ.get(
    "CATALOG_DRIFT_DIGEST_RECIPIENT", ""
).strip()


async def _catalog_drift_digest_job() -> None:
    """Onda 10 Step E.1 — periodic catalog/billing consistency audit
    with email digest to system_admin.

    Wraps the existing scripts/audit_billing_consistency.py logic into
    a recurring background tick:
      · Scan all orgs for plan/subscription drift (HIGH/MEDIUM severity)
      · If any HIGH issues → email digest to CATALOG_DRIFT_DIGEST_RECIPIENT
      · Always logs the summary so it's visible in the backend log

    Runs every CATALOG_DRIFT_CHECK_INTERVAL_HOURS (default 24h).
    Initial delay = same staggering pattern as other jobs (after lifespan
    startup completes).

    NON-FATAL on errors: a failed scan logs warning, the loop continues.

    Recipient: env CATALOG_DRIFT_DIGEST_RECIPIENT (system admin email).
    If not set → only logs, no email sent.
    """
    interval_seconds = _CATALOG_DRIFT_CHECK_INTERVAL_HOURS * 3600

    logger.info(
        "background_service: catalog drift digest starting — "
        "interval %.1fh, recipient=%s",
        _CATALOG_DRIFT_CHECK_INTERVAL_HOURS,
        _CATALOG_DRIFT_DIGEST_RECIPIENT or "(unset; log-only)",
    )

    await asyncio.sleep(_INITIAL_DELAY_SECONDS + 180)

    while True:
        try:
            await _run_catalog_drift_digest()
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.error(
                "background_service: catalog drift digest tick error: %s",
                exc, exc_info=True,
            )
        try:
            await asyncio.sleep(interval_seconds)
        except asyncio.CancelledError:
            raise


async def _run_catalog_drift_digest() -> dict:
    """Single tick: scan + (optional) email. Public for testability.

    Returns:
      {"scanned": int, "high_issues": int, "medium_issues": int,
       "issues_per_org": [...], "email_sent": bool}
    """
    from database import organizations_collection
    cursor = organizations_collection.find(
        {"is_active": True}, {"_id": 0, "id": 1, "name": 1, "commercial_plan_slug": 1},
    )
    orgs = await cursor.to_list(10000)

    issues_per_org = []
    high_count = 0
    medium_count = 0

    # Reuse the audit script's scan logic by importing its module-level
    # function. The script is structured for CLI but exposes
    # `audit_org` and the catalog/pricing loaders for programmatic use.
    try:
        from scripts.audit_billing_consistency import (
            audit_org,
            load_commercial_plans,
            load_pricing_plans,
            load_pricing_plans_by_slug,
        )
    except Exception as e:
        logger.warning("catalog_drift_digest: could not import audit_org: %s", e)
        return {"scanned": 0, "high_issues": 0, "medium_issues": 0,
                "issues_per_org": [], "email_sent": False}

    try:
        commercial_plans = await load_commercial_plans()
        pricing_plans_by_id = await load_pricing_plans()
        pricing_plans_by_slug = await load_pricing_plans_by_slug()
    except Exception as e:
        logger.warning("catalog_drift_digest: catalog preload failed: %s", e)
        return {"scanned": 0, "high_issues": 0, "medium_issues": 0,
                "issues_per_org": [], "email_sent": False}

    for org in orgs:
        try:
            findings = await audit_org(
                org,
                commercial_plans,
                pricing_plans_by_id,
                pricing_plans_by_slug,
            )
        except Exception as e:
            logger.debug("catalog_drift_digest: audit failed for %s: %s", org["id"], e)
            continue
        if not findings or findings.get("consistent"):
            continue
        # Count severity
        org_high = sum(1 for i in findings.get("issues", []) if i.get("severity") == "HIGH")
        org_medium = sum(1 for i in findings.get("issues", []) if i.get("severity") == "MEDIUM")
        if org_high == 0 and org_medium == 0:
            continue
        high_count += org_high
        medium_count += org_medium
        issues_per_org.append({
            "org_id": org["id"],
            "name": org.get("name"),
            "plan": org.get("commercial_plan_slug"),
            "high": org_high,
            "medium": org_medium,
            "issues": [
                {"severity": i.get("severity"), "message": i.get("message")}
                for i in findings.get("issues", [])
                if i.get("severity") in ("HIGH", "MEDIUM")
            ][:5],  # cap at 5 per org for the digest brevity
        })

    logger.info(
        "background_service: catalog drift digest — scanned=%d high=%d medium=%d",
        len(orgs), high_count, medium_count,
    )

    email_sent = False
    if high_count > 0 and _CATALOG_DRIFT_DIGEST_RECIPIENT:
        try:
            await _send_catalog_drift_email(
                recipient=_CATALOG_DRIFT_DIGEST_RECIPIENT,
                scanned=len(orgs),
                high=high_count,
                medium=medium_count,
                issues_per_org=issues_per_org[:30],  # cap for email
            )
            email_sent = True
            logger.info(
                "background_service: catalog drift digest sent to %s",
                _CATALOG_DRIFT_DIGEST_RECIPIENT,
            )
        except Exception as e:
            logger.warning("catalog_drift_digest: email send failed: %s", e)

    return {
        "scanned": len(orgs),
        "high_issues": high_count,
        "medium_issues": medium_count,
        "issues_per_org": issues_per_org,
        "email_sent": email_sent,
    }


async def _send_catalog_drift_email(
    *, recipient: str, scanned: int, high: int, medium: int, issues_per_org: list,
) -> None:
    """Send the digest. Best-effort; logs warning on failure.

    Note: services.email_service.send_email is SYNC and uses urllib (blocking).
    We dispatch it on a thread to avoid stalling the event loop.
    """
    from services.email_service import send_email
    subject = f"[Aurya] Catalog drift digest — {high} HIGH, {medium} MEDIUM in {scanned} orgs"
    rows = []
    for o in issues_per_org:
        issue_lines = "<br>".join(
            f"  · [{i['severity']}] {i['message']}" for i in o.get("issues", [])
        )
        rows.append(
            f"<tr><td>{o.get('name', '')}</td>"
            f"<td><code>{o.get('plan', '?')}</code></td>"
            f"<td><span style='color:#c00'>{o.get('high', 0)} HIGH</span> / "
            f"{o.get('medium', 0)} MED</td>"
            f"<td style='font-size:11px;color:#555'>{issue_lines}</td></tr>"
        )
    body_html = f"""
    <p>Hello system admin,</p>
    <p>The catalog/billing consistency scan ran in the last 24h.</p>
    <p><strong>Scanned: {scanned} active orgs · HIGH issues: {high} · MEDIUM: {medium}</strong></p>
    <p>HIGH issues require investigation. Open the admin panel
       (<code>/admin → Organizations → filter Drift</code>) for the
       affected orgs.</p>
    <table style="border-collapse:collapse" border="1" cellpadding="4">
      <tr><th>Org</th><th>Plan</th><th>Severity</th><th>Top issues</th></tr>
      {''.join(rows) or '<tr><td colspan=4>(no detail)</td></tr>'}
    </table>
    <p style="font-size:12px;color:#666">Onda 10 Step E.1 · sent
       automatically by background_service.</p>
    """
    await asyncio.to_thread(send_email, recipient, subject, body_html)


# ── Onda 20 Layer 3: orphan Stripe subscription audit (every 6h) ─────────────

_ORPHAN_SUB_CHECK_INTERVAL_HOURS = float(
    os.environ.get("ORPHAN_SUB_CHECK_INTERVAL_HOURS", "6")
)


async def _orphan_subs_audit_job() -> None:
    """Onda 20 Layer 3 — periodic detection of orgs with multiple active
    Stripe subscriptions on the same customer.

    Runs every ORPHAN_SUB_CHECK_INTERVAL_HOURS (default 6h). NEVER auto-
    cancels (too risky without operator visibility) — only LOGS a clear
    warning so an operator can run the manual cleanup script
    `scripts/cleanup_orphan_stripe_subs.py` after investigation.

    Layers 1+2 should prevent the issue ever reaching this audit, but
    this safety net catches anything that slips through (manual Stripe
    Dashboard interventions, exotic race conditions, missed webhooks).
    """
    interval_seconds = _ORPHAN_SUB_CHECK_INTERVAL_HOURS * 3600
    logger.info(
        "background_service: orphan-subs audit starting — interval %.1fh",
        _ORPHAN_SUB_CHECK_INTERVAL_HOURS,
    )
    # Stagger start so it doesn't pile on with the catalog drift digest
    await asyncio.sleep(_INITIAL_DELAY_SECONDS + 600)

    while True:
        try:
            await _run_orphan_subs_audit()
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.error(
                "background_service: orphan-subs audit tick error: %s",
                exc, exc_info=True,
            )
        try:
            await asyncio.sleep(interval_seconds)
        except asyncio.CancelledError:
            raise


async def _run_orphan_subs_audit() -> dict:
    """Single tick of the orphan-subs audit. Returns summary dict."""
    import os as _os
    try:
        import stripe as _stripe
    except ImportError:
        logger.warning("orphan_subs_audit: stripe SDK not installed")
        return {"orgs_inspected": 0, "orgs_with_orphans": 0, "total_orphans": 0}

    api_key = _os.environ.get("STRIPE_SECRET_KEY", "").strip()
    if not api_key:
        logger.info("orphan_subs_audit: STRIPE_SECRET_KEY not set — skipping")
        return {"orgs_inspected": 0, "orgs_with_orphans": 0, "total_orphans": 0}
    _stripe.api_key = api_key

    from database import organizations_collection
    cursor = organizations_collection.find(
        {
            "stripe_customer_id": {"$nin": [None, ""]},
            "is_active": {"$ne": False},
        },
        {"_id": 0, "id": 1, "name": 1,
         "stripe_customer_id": 1, "stripe_subscription_id": 1},
    )
    orgs = await cursor.to_list(10000)

    inspected = 0
    orgs_with_orphans = 0
    total_orphans = 0
    examples: list[dict] = []

    for org in orgs:
        inspected += 1
        cust_id = org["stripe_customer_id"]
        kept = org.get("stripe_subscription_id")
        try:
            active_data = await asyncio.to_thread(
                lambda: _stripe.Subscription.list(customer=cust_id, status="active", limit=20).data,
            )
            trialing_data = await asyncio.to_thread(
                lambda: _stripe.Subscription.list(customer=cust_id, status="trialing", limit=20).data,
            )
            all_active = list(active_data) + list(trialing_data)
        except Exception as e:
            logger.debug("orphan_subs_audit: list failed for %s: %s", cust_id, e)
            continue

        if len(all_active) <= 1:
            continue

        orphan_ids = [s.id for s in all_active if s.id != kept]
        if not orphan_ids:
            continue
        orgs_with_orphans += 1
        total_orphans += len(orphan_ids)
        examples.append({
            "org_id": org["id"],
            "org_name": org["name"],
            "stripe_customer_id": cust_id,
            "kept_sub_id": kept,
            "orphan_sub_ids": orphan_ids,
        })

    logger.info(
        "orphan_subs_audit: inspected=%d orgs_with_orphans=%d total_orphans=%d",
        inspected, orgs_with_orphans, total_orphans,
    )
    if examples:
        logger.warning(
            "[onda_20] ORPHAN STRIPE SUBS DETECTED — %d org(s) violate the "
            "one-active-sub invariant. Run scripts/cleanup_orphan_stripe_subs.py "
            "to remediate. Affected: %s",
            len(examples),
            [
                f"{e['org_name']} (orphans={e['orphan_sub_ids']})"
                for e in examples[:5]
            ],
        )
    return {
        "orgs_inspected": inspected,
        "orgs_with_orphans": orgs_with_orphans,
        "total_orphans": total_orphans,
        "examples": examples,
    }


# ── Onda 24 Phase G: addon consistency audit job (every 6h) ──────────────────

_ADDON_AUDIT_INTERVAL_HOURS = float(
    os.environ.get("ADDON_AUDIT_INTERVAL_HOURS", "6")
)


async def _addon_consistency_audit_job() -> None:
    """Periodic detection of drift between AddonSubscription rows and the
    actual addon items inside the org's Stripe subscription.

    Onda 24 Phase G — read-only audit. NEVER auto-reconciles from cron;
    only logs warnings so operators can run
    `scripts/audit_addon_consistency.py --fix` after review.

    Layers 1-2 (Phase F + reconcile sync in modify_subscription) should
    keep DB↔Stripe in sync for addons. This audit catches anything that
    slips through (rare race, manual Stripe Dashboard edits, dropped
    webhooks).
    """
    interval_seconds = _ADDON_AUDIT_INTERVAL_HOURS * 3600
    logger.info(
        "background_service: addon consistency audit starting — interval %.1fh",
        _ADDON_AUDIT_INTERVAL_HOURS,
    )
    # Stagger so the 3 billing audits don't all hit Stripe simultaneously
    await asyncio.sleep(_INITIAL_DELAY_SECONDS + 900)

    while True:
        try:
            await _run_addon_consistency_audit()
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.error(
                "background_service: addon audit tick error: %s",
                exc, exc_info=True,
            )
        try:
            await asyncio.sleep(interval_seconds)
        except asyncio.CancelledError:
            raise


async def _run_addon_consistency_audit() -> dict:
    """Single tick of the addon consistency audit. Read-only; logs drift."""
    import os as _os
    try:
        import stripe as _stripe
    except ImportError:
        return {"orgs_inspected": 0, "drift_count": 0}

    api_key = _os.environ.get("STRIPE_SECRET_KEY", "").strip()
    if not api_key:
        return {"orgs_inspected": 0, "drift_count": 0}
    _stripe.api_key = api_key

    from database import organizations_collection, addon_subscriptions_collection

    cursor = organizations_collection.find(
        {
            "stripe_subscription_id": {"$nin": [None, ""]},
            "is_active": {"$ne": False},
        },
        {"_id": 0, "id": 1, "name": 1, "stripe_subscription_id": 1},
    )
    orgs = await cursor.to_list(10000)

    inspected = 0
    drift_count = 0
    examples: list[dict] = []

    for org in orgs:
        inspected += 1
        org_id = org["id"]
        sub_id = org["stripe_subscription_id"]

        # DB-side active addons
        db_cursor = addon_subscriptions_collection.find(
            {"organization_id": org_id, "status": "active"},
            {"_id": 0, "addon_slug": 1, "stripe_subscription_item_id": 1, "quantity": 1},
        )
        db_slugs = {a["addon_slug"]: a async for a in db_cursor}

        # Stripe-side addon items
        try:
            sub = await asyncio.to_thread(
                _stripe.Subscription.retrieve, sub_id, expand=["items"],
            )
        except Exception:
            continue

        stripe_slugs: dict = {}
        for it in (sub.get("items") or {}).get("data", []) or []:
            md = it.get("metadata") if hasattr(it, "get") else getattr(it, "metadata", None) or {}
            if not isinstance(md, dict):
                try:
                    md = dict(md)
                except Exception:
                    md = {}
            if md.get("is_addon") != "true":
                continue
            slug = md.get("addon_slug")
            if not slug:
                continue
            stripe_slugs[slug] = {
                "id": it.get("id") if hasattr(it, "get") else getattr(it, "id", None),
                "quantity": it.get("quantity") if hasattr(it, "get") else getattr(it, "quantity", 1),
            }

        # Compare
        db_only = set(db_slugs.keys()) - set(stripe_slugs.keys())
        stripe_only = set(stripe_slugs.keys()) - set(db_slugs.keys())
        if db_only or stripe_only:
            drift_count += len(db_only) + len(stripe_only)
            examples.append({
                "org_id": org_id,
                "org_name": org["name"],
                "db_only": sorted(db_only),
                "stripe_only": sorted(stripe_only),
            })

    if drift_count > 0:
        logger.warning(
            "[onda_24_phase_g] ADDON DRIFT DETECTED — %d issues across %d org(s). "
            "Run scripts/audit_addon_consistency.py --fix to reconcile. Sample: %s",
            drift_count, len(examples),
            examples[:5],
        )
    else:
        logger.info(
            "addon_consistency_audit: inspected=%d drift=0 ✓",
            inspected,
        )

    return {
        "orgs_inspected": inspected,
        "drift_count": drift_count,
        "examples": examples,
    }


# ── Public API ────────────────────────────────────────────────────────────────

def start() -> List[asyncio.Task]:
    """Schedule all periodic jobs and return the Tasks.

    Must be called inside an active asyncio event loop (i.e. inside the
    FastAPI lifespan context manager, after ``yield``-ing the startup phase).
    """
    tasks = [
        asyncio.create_task(_periodic_job(), name="background_alert_job"),
        asyncio.create_task(_billing_sweep_job(), name="billing_sweep_job"),
        asyncio.create_task(_hard_delete_cleanup_job(), name="hard_delete_cleanup_job"),
        # Wave GDPR-Admin A — final warning 7 days before hard-delete fires.
        # Isolated from the cleanup job so a failure here never blocks
        # the deletion path (which is the legally-binding commitment).
        asyncio.create_task(_hard_delete_warning_job(), name="hard_delete_warning_job"),
        asyncio.create_task(_order_cleanup_job(), name="order_cleanup_job"),
        asyncio.create_task(_quota_warning_sweep_job(), name="quota_warning_sweep_job"),
        # Onda 10 Step E.1
        asyncio.create_task(_catalog_drift_digest_job(), name="catalog_drift_digest_job"),
        # Onda 20 Layer 3 — orphan Stripe sub audit
        asyncio.create_task(_orphan_subs_audit_job(), name="orphan_subs_audit_job"),
        # Onda 24 Phase G — addon DB↔Stripe consistency audit
        asyncio.create_task(_addon_consistency_audit_job(), name="addon_consistency_audit_job"),
    ]
    return tasks


def stop(tasks: Union[asyncio.Task, List[asyncio.Task], None]) -> None:
    """Cancel background tasks (non-blocking — FastAPI lifespan handles await).

    Accepts a single Task (backward compat) or a list of Tasks.
    """
    if tasks is None:
        return
    if isinstance(tasks, asyncio.Task):
        tasks = [tasks]
    for task in tasks:
        if task and not task.done():
            task.cancel()
    logger.info("background_service: periodic jobs cancelled")
