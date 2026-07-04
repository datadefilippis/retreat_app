"""Brevo / SendInBlue server-send channel — STUB FOR v2.

Documented and registered so the channel name space is reserved and
the registry has a stable ``"brevo"`` entry. Calls to ``build_link``
raise ``NotImplementedError`` with a roadmap-pointing message.

When this channel becomes real (likely 2-3 merchants in, when
someone asks for "send to all my customers at once"), the Phase
naming preserves the deep-link contract:

  • supports() should still return bool
  • build_link() should still return an OutreachLink, but ``url``
    will be a one-time confirmation page hosted by afianco
    (``/admin/outreach/confirm/{batch_id}``) so the merchant
    reviews + confirms the bulk send before it goes out.

Why register a stub instead of skipping? Two reasons:
  1. The registry's ``list_names()`` reflects what the UI can offer.
     A future "channel selector" dropdown reads from this list, so
     including ``brevo`` already makes the empty option visible
     (greyed out) and avoids "where did this channel come from?"
     surprise on day 1 of v2.
  2. The unit test for the registry contract pins the channel set,
     so removing it later is a deliberate decision not an oversight.

cf. docs/CUSTOMER_INSIGHTS_FORMULAS.md "Phase 3 close-out" section.
"""

from __future__ import annotations

from .base import CustomerContact, OutreachChannel, OutreachLink


class BrevoChannel(OutreachChannel):
    name = "brevo"

    def supports(self, customer: CustomerContact) -> bool:
        # Pretend we never can — keeps the UI from greying out *email*
        # buttons when only the brevo channel is unavailable. Mailto is
        # the email channel today; brevo simply doesn't take any traffic.
        return False

    def build_link(
        self, customer: CustomerContact, subject: str, body: str,
    ) -> OutreachLink:
        raise NotImplementedError(
            "Brevo channel is a v2 stub. Use channel='mailto' for email "
            "outreach in v1. Roadmap: when a merchant requests bulk send, "
            "implement build_link to return a /admin/outreach/confirm URL "
            "that fronts the actual Brevo POST. "
            "See docs/CUSTOMER_INSIGHTS_FORMULAS.md."
        )


# Auto-register on import — stub presence is intentional.
from .registry import OutreachChannelRegistry  # noqa: E402
OutreachChannelRegistry.register(BrevoChannel())
