"""WhatsApp deep-link channel.

Uses the ``https://wa.me/<E.164>?text=...`` URL — opens WhatsApp app
on mobile, web.whatsapp.com on desktop, with the message pre-typed.
Merchant taps Send.

No WhatsApp Business API integration. That would require:
  • WhatsApp Business account + Meta verification
  • Pre-approved message templates (anti-spam)
  • Send infrastructure
  • Merchant onboarding flow

For 5-50 merchants chatting with 50-500 customers each, the deep-link
is dramatically simpler and works **today**. The Business API is the
right move when a merchant says "I want to send the same message to
500 customers at once" — Phase 6+ territory.
"""

from __future__ import annotations

from .base import CustomerContact, OutreachChannel, OutreachLink
from ..phone_normalize import to_e164, to_whatsapp_url


class WhatsAppChannel(OutreachChannel):
    name = "whatsapp"

    # WhatsApp web caps URL length around 2000; the deep-link with a
    # very long text param can fail silently on some Android versions.
    MAX_TEXT_CHARS = 1600

    def __init__(self, default_country: str = "CH"):
        self._default_country = default_country

    def supports(self, customer: CustomerContact) -> bool:
        if not customer.phone:
            return False
        return to_e164(customer.phone, self._default_country) is not None

    def build_link(
        self, customer: CustomerContact, subject: str, body: str,
    ) -> OutreachLink:
        e164 = to_e164(customer.phone, self._default_country)
        if not e164:
            raise ValueError(
                f"whatsapp channel needs a parseable phone; got "
                f"customer_id={customer.id} phone={customer.phone!r}"
            )

        # WhatsApp ignores subject/body distinction — we concatenate.
        # Subject becomes a leading line, body follows with blank line
        # separator. If subject is empty, just send the body.
        if subject:
            text = f"{subject}\n\n{body}"
        else:
            text = body
        text = text[: self.MAX_TEXT_CHARS]

        return OutreachLink(
            channel=self.name,
            url=to_whatsapp_url(e164, text),
            subject=subject or None,
            body=text,  # subject + body concatenated, what wa.me actually sends
            preview=body[:120],
        )


# Auto-register on import.
from .registry import OutreachChannelRegistry  # noqa: E402
OutreachChannelRegistry.register(WhatsAppChannel())
