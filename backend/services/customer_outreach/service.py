"""High-level service entry points.

The module surface is small on purpose — three functions covering
the entire merchant-facing API:

  build_outreach   compose template + channel into a deep-link URL
                   ready for window.open
  log_outreach     persist the click intent to audit_logs
  list_templates   power a "what messages do I have ready?" picker

Channels self-register on import via ``customer_outreach`` package
init below, so the registry is populated before any caller hits us.
"""

from __future__ import annotations

import logging
from typing import Optional

# Importing the channel modules registers them as a side effect.
# Don't reorder these without updating the registry tests.
from .channels import mailto, whatsapp, brevo  # noqa: F401
from .channels.base import CustomerContact, OutreachLink
from .channels.registry import OutreachChannelRegistry
from .templates import loader as templates

logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────────────────────


def build_outreach(
    customer: CustomerContact,
    template_key: str,
    channel: str,
    *,
    locale: str = "it",
    merchant_name: str = "",
    days_since_last: Optional[int] = None,
) -> OutreachLink:
    """Compose template + channel into a clickable deep-link.

    Raises:
        ValueError: when channel is unknown, template missing, or the
                    customer doesn't support the channel (e.g.
                    whatsapp without a phone).
        NotImplementedError: when the channel is a v2 stub.

    Returns:
        :class:`OutreachLink` ready to hand to ``window.open(url)``.
    """
    impl = OutreachChannelRegistry.get_by_name(channel)
    if impl is None:
        raise ValueError(
            f"Unknown channel {channel!r}. Available: "
            f"{OutreachChannelRegistry.list_names()}"
        )

    if not impl.supports(customer):
        raise ValueError(
            f"Channel {channel!r} unsupported for customer "
            f"{customer.id!r} (missing email/phone or invalid format)"
        )

    rendered = templates.render(
        template_key, locale,
        customer_name=customer.name or "",
        merchant_name=merchant_name,
        days_since_last=days_since_last,
    )
    if rendered is None:
        raise ValueError(
            f"Unknown template_key {template_key!r} for locale {locale!r}"
        )

    return impl.build_link(
        customer, subject=rendered["subject"], body=rendered["body"],
    )


async def log_outreach(
    org_id: str,
    user_id: str,
    customer_id: str,
    *,
    channel: str,
    template: Optional[str] = None,
    status: str = "opened",
) -> None:
    """Persist the outreach click event to ``audit_logs``.

    Best-effort: caught and logged, never raises. The Phase 4
    smart-suggestions panel reads this audit trail to dedupe "we
    already pinged at-risk customers today".
    """
    try:
        from repositories import audit_repository
        from models import AuditLog
        await audit_repository.create(AuditLog(
            organization_id=org_id,
            user_id=user_id,
            action="customer.outreach.sent",
            resource_type="customer",
            resource_id=customer_id,
            details={
                "channel": channel,
                "template": template,
                "status": status,
            },
        ))
    except Exception as exc:
        logger.warning(
            "customer_outreach.log_outreach: audit write failed for "
            "customer=%s channel=%s template=%s: %s",
            customer_id, channel, template, exc,
        )


def list_templates(locale: str = "it") -> list[dict]:
    """Public picker — return the available templates with previews."""
    return templates.list_templates(locale)
