"""CF1 — guardia del kit grafico condiviso (INSIGHTS_ACTION_PLAN).

Ogni grafico dell'app passa da ``frontend/src/components/charts`` —
palette Salvia&Terracotta unica, empty state onesti, coerenza visiva.
Un import diretto di recharts in una pagina feature reintroduce
colori/assi arbitrari: questa guardia lo blocca in CI.

L'allowlist NON deve crescere: contiene solo il kit stesso e il
legacy admin-only (AIGovernanceTab, dashboard spesa AI per
system_admin — non operator-facing, migrazione non prioritaria).
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SRC = REPO_ROOT / "frontend" / "src"

# Percorsi (relativi a src) autorizzati a importare recharts.
ALLOWED = (
    "components/charts/",              # il kit stesso
    "features/admin/AIGovernanceTab",  # legacy system_admin-only
)


def _js_files():
    for ext in ("*.js", "*.jsx"):
        yield from SRC.rglob(ext)


def test_recharts_only_imported_by_charts_kit():
    offenders = []
    for f in _js_files():
        rel = f.relative_to(SRC).as_posix()
        if any(rel.startswith(a) for a in ALLOWED):
            continue
        text = f.read_text(encoding="utf-8", errors="ignore")
        if "from 'recharts'" in text or 'from "recharts"' in text:
            offenders.append(rel)
    assert not offenders, (
        "Import diretto di recharts fuori dal kit components/charts "
        "(usa StatCard/TrendArea/MiniBars/DonutSplit):\n" +
        "\n".join(f"  {o}" for o in offenders)
    )


def test_charts_kit_exists_with_expected_exports():
    """Il kit espone le quattro forme del piano — se qualcuno le
    rinomina, le pagine costruite sopra si rompono in silenzio."""
    kit = SRC / "components" / "charts" / "index.js"
    assert kit.exists(), "components/charts/index.js mancante"
    text = kit.read_text(encoding="utf-8")
    for name in ("StatCard", "TrendArea", "MiniBars", "DonutSplit"):
        assert f"export function {name}" in text, f"export mancante: {name}"


def test_palette_is_salvia_terracotta():
    """La palette non deriva: primario salvia, attenzione terracotta."""
    palette = (SRC / "components" / "charts" / "palette.js").read_text(encoding="utf-8")
    assert "#376254" in palette   # salvia
    assert "#C97B5D" in palette   # terracotta
