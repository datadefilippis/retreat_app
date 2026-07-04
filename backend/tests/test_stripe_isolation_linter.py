"""Test for ``scripts/check_stripe_isolation.py`` itself.

The lint script is what stops a future PR from quietly re-introducing
``import stripe`` in a banned location and undoing the provider
abstraction work. This test pins down its behaviour so it can't
silently regress to "always passes".
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
SCRIPT = BACKEND_DIR / "scripts" / "check_stripe_isolation.py"
PYTHON = sys.executable


def _run_script_against_tree(root: Path) -> tuple[int, str]:
    """Invoke the linter against an arbitrary backend root and return
    (exit_code, combined_stdout_stderr).
    """
    # Patch the _ROOT computation by monkey-patching via a small launcher
    # that imports the script and overrides _ROOT before _scan runs.
    launcher = (
        "import sys, importlib, pathlib\n"
        f"sys.path.insert(0, {str(BACKEND_DIR)!r})\n"
        "mod = importlib.import_module('scripts.check_stripe_isolation')\n"
        f"mod._ROOT = pathlib.Path({str(root)!r})\n"
        "mod._ALLOW_FILES = {p for p in mod._ALLOW_FILES}\n"
        "mod._ALLOW_PREFIXES = tuple(p for p in mod._ALLOW_PREFIXES)\n"
        "mod._POLICE_PREFIXES = (mod._ROOT / 'routers',)\n"
        "mod._POLICE_SERVICES_GLOB = mod._ROOT / 'services'\n"
        "import sys; sys.exit(mod.main())\n"
    )
    proc = subprocess.run(
        [PYTHON, "-c", launcher],
        capture_output=True, text=True,
    )
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def test_real_codebase_is_clean():
    """The actual backend tree must pass the lint as we ship it.

    If this test fails, someone added ``import stripe`` to a banned
    location or removed an entry from the allow-list without scrubbing
    the codebase first.
    """
    proc = subprocess.run(
        [PYTHON, "-m", "scripts.check_stripe_isolation"],
        capture_output=True, text=True, cwd=str(BACKEND_DIR),
    )
    assert proc.returncode == 0, (
        f"Stripe isolation lint failed:\n{proc.stdout}\n{proc.stderr}"
    )


def test_lint_catches_banned_import_in_router(tmp_path: Path):
    """Drop a synthetic offender into a fake routers/ tree and confirm
    the lint script flags it with exit code 1.
    """
    fake = tmp_path / "fake_backend"
    (fake / "routers").mkdir(parents=True)
    (fake / "services").mkdir(parents=True)
    bad = fake / "routers" / "rogue.py"
    bad.write_text("import stripe\nstripe.api_key = 'x'\n")

    rc, output = _run_script_against_tree(fake)
    assert rc == 1
    assert "rogue.py" in output
    assert "stripe" in output.lower()


def test_lint_passes_when_only_allowed_files_have_imports(tmp_path: Path):
    """A clean tree with no banned imports must exit 0."""
    fake = tmp_path / "fake_clean"
    (fake / "routers").mkdir(parents=True)
    (fake / "services").mkdir(parents=True)
    (fake / "routers" / "ok.py").write_text("# nothing here\n")
    (fake / "services" / "ok.py").write_text("# nothing here either\n")

    rc, _output = _run_script_against_tree(fake)
    assert rc == 0


def test_lint_catches_from_stripe_import_form(tmp_path: Path):
    """``from stripe.error import Foo`` is also banned."""
    fake = tmp_path / "fake_from_form"
    (fake / "routers").mkdir(parents=True)
    (fake / "services").mkdir(parents=True)
    bad = fake / "routers" / "rogue2.py"
    bad.write_text("from stripe.error import CardError\n")

    rc, output = _run_script_against_tree(fake)
    assert rc == 1
    assert "rogue2.py" in output
