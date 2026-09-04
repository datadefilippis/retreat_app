"""
SR1 (3/9/2026) — il numero d'ordine dopo «ORD-9999».

Bug: get_next_order_number prendeva il MAX LESSICOGRAFICO (sort sulla
stringa): «ORD-10000» ordina prima di «ORD-9999», il massimo restava
9999 e ogni conferma riproponeva lo stesso numero → «Impossibile
assegnare numero ordine dopo 3 tentativi», per sempre. Stessa trappola
coi prefissi misti degli import («ORD-2024-007» > «ORD-0042»).
Cura: massimo NUMERICO sulla coda di cifre di tutti i numeri dell'org
+ il retry del servizio fa avanzare il numero (skip).
"""
import uuid
from pathlib import Path

import pytest

from repositories.order_repository import get_next_order_number

BACKEND = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.asyncio


async def _con_numeri(numeri):
    from database import orders_collection
    org = f"test-numero-ordine-{uuid.uuid4().hex[:8]}"
    docs = [{"id": str(uuid.uuid4()), "organization_id": org, "order_number": n,
             "status": "confirmed", "_test_numero_ordine": True} for n in numeri]
    if docs:
        await orders_collection.insert_many(docs)
    return org


async def _pulisci(org):
    from database import orders_collection
    await orders_collection.delete_many({"organization_id": org})


class TestMassimoNumerico:
    async def test_massimo_numerico_prefissi_skip_e_org_vuota(self):
        """Un solo test async: il client Motor si lega al loop del primo
        test e i successivi nello stesso modulo troverebbero il loop
        chiuso (flaky asyncio noto della suite)."""
        # dopo 9999 si va avanti (il bug: «ORD-10000» < «ORD-9999» come stringa)
        org = await _con_numeri(["ORD-9998", "ORD-9999", "ORD-10000"])
        try:
            assert await get_next_order_number(org) == "ORD-10001"
        finally:
            await _pulisci(org)
        # i prefissi misti degli import non ingannano
        org = await _con_numeri(["ORD-2024-007", "ORD-0042", "ORD-CB-0162"])
        try:
            assert await get_next_order_number(org) == "ORD-0163"
        finally:
            await _pulisci(org)
        # skip fa avanzare il retry
        org = await _con_numeri(["ORD-0005"])
        try:
            assert await get_next_order_number(org) == "ORD-0006"
            assert await get_next_order_number(org, skip=1) == "ORD-0007"
            assert await get_next_order_number(org, skip=2) == "ORD-0008"
        finally:
            await _pulisci(org)
        # org vuota parte da uno
        org = f"test-numero-ordine-vuota-{uuid.uuid4().hex[:8]}"
        assert await get_next_order_number(org) == "ORD-0001"
        assert await get_next_order_number(org, skip=1) == "ORD-0002"


class TestGuardia:
    def test_niente_sort_sulla_stringa_e_retry_che_avanza(self):
        repo = (BACKEND / "repositories" / "order_repository.py").read_text()
        i = repo.index("async def get_next_order_number")
        corpo = repo[i:repo.index("\nasync def", i + 10) if "\nasync def" in repo[i + 10:] else len(repo)]
        assert '.sort("order_number", -1)' not in corpo, \
            "il massimo del numero d'ordine deve essere numerico, non lessicografico"
        assert "max(tails) + 1 + skip" in corpo
        svc = (BACKEND / "services" / "order_service.py").read_text()
        assert "get_next_order_number(org_id, skip=_attempt)" in svc, \
            "a ogni collisione il numero deve avanzare"
