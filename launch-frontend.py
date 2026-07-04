#!/usr/bin/env python3
"""Frontend launcher — bypasses invalid shell cwd by using subprocess cwd arg."""
import os
import subprocess
import sys

FRONTEND_DIR = "/Users/davidedefilippis/Desktop/BI_PMI/frontend"
NODE_BIN = "/Users/davidedefilippis/.nvm/versions/node/v22.13.1/bin"
# Use craco (not react-scripts) so that webpack aliases in craco.config.js
# (e.g. '@' → 'src/') are applied correctly at compile time.
CRACO = os.path.join(FRONTEND_DIR, "node_modules", ".bin", "craco")

os.environ["PATH"] = NODE_BIN + ":" + os.environ.get("PATH", "")
os.environ.setdefault("BROWSER", "none")

result = subprocess.run(
    [os.path.join(NODE_BIN, "node"), CRACO, "start"],
    cwd=FRONTEND_DIR,
)
sys.exit(result.returncode)
