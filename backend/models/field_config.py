"""
FieldConfig — merchant-defined custom form field definition.

Introduced by Onda 9 / F2. A merchant can attach a list of FieldConfig
to an event_ticket product, at TWO scopes:

- `product.metadata.order_fields`     — collected once at checkout
- `product.metadata.attendee_fields`  — collected per ticket holder

The FieldConfig itself is only metadata (labels, type, required flag).
Filled values are persisted separately:

- `Order.order_fields_data: Dict[str, Any]`           — keyed by FieldConfig.id
- `IssuedTicket.attendee_fields_data: Dict[str, Any]` — keyed by FieldConfig.id

Tipi supportati: text / textarea / number (originali) + email / tel / select /
checkbox (aggiunti per il modulo Newsletter, retro-compatibili: i dati storici
con i 3 tipi base restano validi). `options` è richiesto solo per `select`.
"""

from typing import Optional, Literal, List
from pydantic import BaseModel, Field, model_validator


# Tipi di campo supportati. L'aggiunta di nuovi membri è retro-compatibile
# (i FieldConfig esistenti usano text/textarea/number).
FieldType = Literal[
    "text", "textarea", "number", "email", "tel", "select", "checkbox",
]


class FieldConfig(BaseModel):
    """One custom form field definition."""
    # Slug-like stable identifier. Used as dictionary key when serializing
    # filled values so the schema can evolve (label renamed, sort_order
    # shifted) without breaking historical data.
    id: str = Field(min_length=1, max_length=40, pattern=r"^[a-z0-9_-]+$")
    # Human-readable label shown above the input
    label: str = Field(min_length=1, max_length=120)
    type: FieldType = "text"
    required: bool = False
    placeholder: Optional[str] = Field(default=None, max_length=120)
    help_text: Optional[str] = Field(default=None, max_length=240)
    # Solo per type="select": valori selezionabili (1-50, non vuoti).
    options: Optional[List[str]] = Field(default=None, max_length=50)
    # Order within its scope (attendee_fields or order_fields). Lower = first.
    sort_order: int = 0

    @model_validator(mode="after")
    def _validate_options(self):
        """`select` richiede ≥1 opzione; gli altri tipi non devono averne."""
        if self.type == "select":
            cleaned = [o.strip() for o in (self.options or []) if o and o.strip()]
            if not cleaned:
                raise ValueError("Un campo 'select' richiede almeno un'opzione")
            self.options = cleaned
        else:
            # Normalizza: nessuna opzione sui tipi non-select.
            self.options = None
        return self
