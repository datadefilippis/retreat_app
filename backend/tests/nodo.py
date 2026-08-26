"""Dove sta Node — deciso in un posto solo (26/8/2026).

Le guardie che eseguono il motore JS scrivono moduli ES in una
cartella temporanea senza package.json: serve la syntax detection di
Node >= 22. Ma `shutil.which("node")` risponde col PATH della shell
del momento, e nvm può metterci davanti un v15 (successo oggi: nove
suite «rosse» per un `import` che quel binario non sa leggere).

Qui il binario si SCEGLIE, non si spera: il primo candidato che
esiste E ha una major sufficiente. I test importano `NODE` e
`node_c_e` da qui.
"""
import re
import shutil
import subprocess
from pathlib import Path

import pytest

_MAJOR_MINIMA = 20   # syntax detection dei moduli, stabile dal 22

_CANDIDATI = (
    shutil.which("node"),
    "/Users/davidedefilippis/.nvm/versions/node/v22.13.1/bin/node",
)


def _major(binario: str) -> int:
    try:
        r = subprocess.run([binario, "--version"],
                           capture_output=True, text=True, timeout=10)
        m = re.match(r"v(\d+)", r.stdout.strip())
        return int(m.group(1)) if m else 0
    except OSError:
        return 0


NODE = next((b for b in _CANDIDATI
             if b and Path(b).exists() and _major(b) >= _MAJOR_MINIMA),
            None)

node_c_e = pytest.mark.skipif(
    NODE is None, reason=f"nessun node >= {_MAJOR_MINIMA} su questa macchina")
