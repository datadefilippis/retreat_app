"""P0 (6/10/2026) — modulo PRODOTTI: fisici e digitali venduti dal profilo.

Si registra all'import (server.py). Non ha ancora rotte: arrivano con
P1 (digitali) e P2 (fisici). Esiste gia' nel registro perche':
  - i piani commerciali lo agganciano (prodotti_retreat_free/_pro);
  - require_module("prodotti") e l'interruttore `prodotti_spento`
    proteggono le rotte future;
  - la scheda negli Strumenti lo legge da /modules/active.
"""
from core.module_registry import register, ModuleDefinition

register(ModuleDefinition(
    module_key="prodotti",
    module_name="Prodotti",
    is_available=True,
    description="Vendi dal tuo profilo prodotti fisici e digitali: libri, kit, guide, audio. Incassi con Stripe, consegna e download protetti inclusi.",
    category="commerce",
    icon="ShoppingBag",
))
