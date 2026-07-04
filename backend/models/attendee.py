"""
AttendeeInfo — details about one ticket holder on an OrderLine.

Introduced by Onda 8 / F1 to support multi-participant event tickets. When a
customer buys N tickets for an event whose product has
`metadata.requires_attendee_details = True`, the storefront form collects one
AttendeeInfo per seat so:

- Each issued ticket has a distinct holder_name / holder_email / holder_phone
- The door can call guests by their real name at check-in
- Each guest receives their personal ticket email (link to landing page)

This model is used in three places:
- `OrderRequestItem.attendees` (public order endpoint, validated on write)
- `OrderLineBase.attendees` (snapshot persisted on the order line)
- `IssuedTicket.holder_*` (copy of each attendee into the individual ticket
  record at confirm time)

When the product's policy does NOT require attendee details, attendees is
None and ticket holder_* fall back to customer_name / customer_email as they
did before F1 (backward compat).
"""

from typing import Any, Dict, Optional
from pydantic import BaseModel, EmailStr, Field


class AttendeeInfo(BaseModel):
    """One ticket holder — populated per seat when requires_attendee_details is True.

    F2 Onda 9:
      - `email` is now Optional: the admin can mark it non-required on the
        product (`metadata.require_attendee_email = False`). When absent
        the ticket's holder_email falls back to the customer's email and
        the individual delivery is skipped for that seat.
      - `custom_fields` holds merchant-defined values keyed by
        FieldConfig.id (see models/field_config.py). Schema-less on
        purpose so the product can evolve its fields independently.
    """
    name: str = Field(min_length=1, max_length=120)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(default=None, max_length=40)
    custom_fields: Dict[str, Any] = Field(default_factory=dict)
