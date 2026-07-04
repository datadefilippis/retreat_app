"""customer_outreach — Phase 3 of the Customer Insights restructuring.

Provides the merchant-facing "contact this customer" workflow that the
new Insights page needs. Strictly **deep-link-only in v1**:

    mailto:cust@email?subject=...&body=...
    https://wa.me/<E.164>?text=...

The merchant clicks a button on the customer profile / table row, we
build the right URL with a localised template, and the merchant's own
mail client / WhatsApp app takes it from there. Their domain, their
reputation, their compliance — afianco never sends the message.

When the day comes that a merchant says "I'd like to send to my whole
list at once", the channel-registry pattern (mirroring our
PaymentProvider abstraction) makes it cheap to add a Brevo / Mailchimp
back-end without rewriting the call sites. ``channels/brevo.py`` is
shipped as a stub that raises ``NotImplementedError`` so the registry
shape is already there.

Public API
----------
    build_outreach(customer, template_key, channel, locale="it")
        → ``{"channel": "...", "url": "https://...", "subject": "...",
            "preview": "..."}`` ready to hand to the frontend's
            ``window.open(url)`` / ``<a href={url}>``.

    log_outreach(org_id, user_id, customer_id, channel, template, status)
        → audit_logs entry; never raises.

    list_templates(channel, locale)
        → human-readable list of available template keys for the
            merchant-facing "what messages do I have ready?" picker.
"""

from .service import build_outreach, log_outreach, list_templates  # noqa: F401
from .channels.registry import OutreachChannelRegistry  # noqa: F401

__all__ = [
    "build_outreach",
    "log_outreach",
    "list_templates",
    "OutreachChannelRegistry",
]
