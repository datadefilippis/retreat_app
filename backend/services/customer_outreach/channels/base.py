"""Abstract base for an outreach channel.

Two channels in v1 (mailto + whatsapp), one stub (brevo). The
abstraction mirrors the PaymentProvider pattern: a small ABC that
forces every backend to declare exactly the same surface, and a
registry that maps channel name → implementation.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class CustomerContact:
    """Minimal customer surface the channels need.

    Reduces what the channel has to know to ``what we'll write to``,
    keeping the abstraction independent of the heavy ``Customer`` model.

    Attributes:
        id: Customer DB id (used for audit log resource_id).
        name: Display name for template interpolation ({customer_name}).
        email: Optional ESP-grade email address.
        phone: Optional free-form phone string. Will be normalised via
               :func:`phone_normalize.to_e164` inside the channel.
    """

    id: str
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None


@dataclass(frozen=True)
class OutreachLink:
    """The result a channel returns — ready for the frontend to consume.

    Attributes:
        channel: ``"mailto"`` / ``"whatsapp"`` / future channels.
        url: The URL to open. ``mailto:`` for email, ``https://wa.me/``
             for WhatsApp, etc.
        subject: The fully-rendered subject (mailto fills this; whatsapp
                 returns the leading line of the body or None).
        body: The fully-rendered body — exposed so the frontend confirm
              dialog can show a preview before the merchant clicks Send,
              and so the "Copy to clipboard" / "Open Gmail web" fallbacks
              have the same content as the deep-link.
        preview: First ~120 chars of body (kept for backward compat
                 with the table tooltip use case).
    """

    channel: str
    url: str
    subject: Optional[str] = None
    body: Optional[str] = None
    preview: Optional[str] = None


class OutreachChannel(ABC):
    """Abstract outreach channel.

    Implementations live under ``channels/`` and self-register with the
    :class:`OutreachChannelRegistry` on import.
    """

    name: str = "abstract"

    @abstractmethod
    def supports(self, customer: CustomerContact) -> bool:
        """Whether this channel can be used for the given customer.

        ``mailto`` requires ``email``; ``whatsapp`` requires a phone
        that normalises to E.164. The UI uses this to grey out
        unsupported buttons.
        """
        ...

    @abstractmethod
    def build_link(
        self, customer: CustomerContact, subject: str, body: str,
    ) -> OutreachLink:
        """Build a deep-link URL ready to hand to ``window.open``.

        ``subject`` and ``body`` are the already-rendered, locale-aware
        strings produced by the templates layer. The channel only
        encodes them into its URL syntax.
        """
        ...
