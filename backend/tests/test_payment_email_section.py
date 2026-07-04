"""Fase 2 S2 (2.6) — sezione piano pagamenti nell'email di conferma."""

import os, sys
from pathlib import Path
from unittest.mock import patch, AsyncMock

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")

import pytest

from services import order_email_service as oes

ORDER = {"id": "ord_x"}

SCHEDULE = {
    "currency": "EUR",
    "rows": [
        {"seq": 0, "label": "Caparra", "amount_minor": 24000,
         "status": "paid", "due_at": "2026-07-04T10:00:00+00:00"},
        {"seq": 1, "label": "Saldo", "amount_minor": 56000,
         "status": "pending", "due_at": "2026-09-02T10:00:00+00:00"},
    ],
}


def _patch_schedule(value):
    return patch(
        "services.payment_schedule_service.get_schedule_for_order",
        new=AsyncMock(return_value=value),
    )


class TestPaymentEmailSection:
    @pytest.mark.asyncio
    async def test_deposit_plan_renders_paid_and_pending(self):
        with _patch_schedule(SCHEDULE):
            html = await oes._render_payment_schedule_section(ORDER, "org", "it")
        assert "Il tuo piano di pagamenti" in html
        assert "Caparra" in html and "pagata" in html
        assert "Saldo" in html and "560,00" in html
        assert "promemoria" in html
        assert "checkout.stripe.com" not in html  # mai link Stripe grezzi

    @pytest.mark.asyncio
    async def test_no_schedule_no_section(self):
        with _patch_schedule(None):
            assert await oes._render_payment_schedule_section(ORDER, "org", "it") == ""

    @pytest.mark.asyncio
    async def test_single_row_full_plan_no_section(self):
        single = {"currency": "EUR", "rows": [SCHEDULE["rows"][0]]}
        with _patch_schedule(single):
            assert await oes._render_payment_schedule_section(ORDER, "org", "it") == ""

    @pytest.mark.asyncio
    async def test_render_error_never_breaks_email(self):
        with patch(
            "services.payment_schedule_service.get_schedule_for_order",
            new=AsyncMock(side_effect=RuntimeError("boom")),
        ):
            assert await oes._render_payment_schedule_section(ORDER, "org", "it") == ""
