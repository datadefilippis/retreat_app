"""Cancella TUTTI i dati campione di pre-lancio (is_sample=True).

Un solo predicato, quattro collection. Idempotente. I dati VERI non
vengono mai toccati (non hanno il flag). I lead NON sono sample: restano.

Uso:
    JWT_SECRET_KEY=... venv/bin/python -m scripts.wipe_prelaunch_samples
"""

import asyncio
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from core.prelaunch import SAMPLE_FLAG

_COLLECTIONS = (
    "organizations", "stores", "products", "event_occurrences",
)


async def wipe_samples() -> dict:
    """Elimina i documenti marchiati is_sample. Ritorna i conteggi."""
    from database import db
    counts = {}
    for name in _COLLECTIONS:
        res = await db[name].delete_many({SAMPLE_FLAG: True})
        counts[name] = res.deleted_count
    return counts


async def _main():
    counts = await wipe_samples()
    total = sum(counts.values())
    for name, n in counts.items():
        print(f"  {name}: {n} eliminati")
    print(f"Totale documenti campione rimossi: {total}")


if __name__ == "__main__":
    asyncio.run(_main())
