"""AC0 (6/10/2026) — modulo ACCADEMIA: corsi online con moduli e lezioni,
venduti dal profilo e seguiti dallo studente nel suo account Aurya.
Si registra all'import (server.py). Non ha ancora rotte: arrivano con
AC1 (operatore) e AC2 (studente). Esiste gia' nel registro perche':
  - i piani commerciali lo agganciano (accademia_retreat_free/_pro);
  - require_module("accademia") e l'interruttore `accademia_spento`
    proteggeranno le rotte;
  - la scheda negli Strumenti lo legge da /modules/active.
Piano: docs/PIANO_ACCADEMIA_2026-10-06.md.
"""
from core.module_registry import register, ModuleDefinition

register(ModuleDefinition(
    module_key="accademia",
    module_name="Accademia",
    is_available=True,
    description="Crea percorsi online con moduli e lezioni video: chi li compra li segue nel suo account Aurya, lezione dopo lezione, con i progressi.",
    category="commerce",
    icon="GraduationCap",
))
