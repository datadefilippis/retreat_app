"""mailto: deep-link channel.

Builds ``mailto:address?subject=...&body=...`` URLs that the merchant's
own mail client (Gmail / Apple Mail / Outlook / Thunderbird) opens
pre-populated. The merchant reviews the draft, hits Send.

Why deep-link instead of server-send (Brevo / SendGrid):
  • Reputation is the merchant's, not afianco's
  • Compliance (GDPR, anti-spam) is the merchant's responsibility
  • Zero infrastructure: works for 1 merchant or 1000 with no extra cost
  • Future Brevo channel can layer on top without reworking the API
"""

from __future__ import annotations

from urllib.parse import quote

from .base import CustomerContact, OutreachChannel, OutreachLink


class MailtoChannel(OutreachChannel):
    name = "mailto"

    # Most mail clients accept very long mailto: URLs but some
    # (older Outlook variants) cap around 2048. We trim long bodies
    # gracefully rather than producing a URL the client refuses to
    # parse silently.
    MAX_BODY_CHARS = 1800

    def supports(self, customer: CustomerContact) -> bool:
        return bool(customer.email and customer.email.strip())

    def build_link(
        self, customer: CustomerContact, subject: str, body: str,
    ) -> OutreachLink:
        if not self.supports(customer):
            raise ValueError(
                f"mailto channel requires customer.email; got "
                f"customer_id={customer.id} email={customer.email!r}"
            )

        body_trimmed = body[: self.MAX_BODY_CHARS]
        encoded_to = quote(customer.email or "", safe="@.")
        url = (
            f"mailto:{encoded_to}"
            f"?subject={quote(subject)}&body={quote(body_trimmed)}"
        )

        return OutreachLink(
            channel=self.name,
            url=url,
            subject=subject,
            body=body_trimmed,
            preview=body_trimmed[:120],
        )


# Auto-register on import.
from .registry import OutreachChannelRegistry  # noqa: E402
OutreachChannelRegistry.register(MailtoChannel())
