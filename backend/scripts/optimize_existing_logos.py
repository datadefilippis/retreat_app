#!/usr/bin/env python3
"""
optimize_existing_logos.py
==========================
Apply the image optimization pipeline to every store logo already on
disk. New uploads after the refinement commit already go through the
optimization helper; this script backfills the legacy uploads (those
saved verbatim before the refinement landed).

What it does
------------
  1. Scans backend/uploads/logos/ for every file
  2. For each raster file (.jpg/.jpeg/.png/.webp):
       · reads the original bytes
       · runs services.image_optimizer.optimize_logo
       · if the optimization saved ≥ 10% bytes AND dimensions changed
         OR the file is significantly oversized:
            → writes the optimized bytes back to the same path
            → logs the savings
       · skips if savings would be negligible (avoid re-encoding
         no-op when admin already uploaded a tight file)
  3. SVG files are skipped (vector — pipeline passes through)
  4. The script DOES NOT touch the Mongo doc (`logo_url` stays the
     same; only the file at that path changes)

Idempotent — safe to re-run. Second run on already-optimized files
sees diminishing returns and skips them.

Usage
-----
    cd backend
    python -m scripts.optimize_existing_logos              # apply
    python -m scripts.optimize_existing_logos --dry-run    # report only
    python -m scripts.optimize_existing_logos --verbose    # detailed log

Exit codes
----------
    0  Migration succeeded (or no work to do).
    1  At least one file failed to optimize (others may have succeeded).
"""

import argparse
import os
import sys
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND_DIR))


# Threshold below which we skip the re-write: if the optimization
# would save less than this fraction of the original bytes, the file
# is already well-optimized and rewriting just churns disk for no
# meaningful gain.
_REWRITE_THRESHOLD_PCT = 10.0


def _process_file(path: Path, dry_run: bool, verbose: bool) -> dict:
    """Optimize a single logo file. Returns a stats dict."""
    from services.image_optimizer import optimize_logo

    ext = path.suffix.lower()
    raw = path.read_bytes()
    original_bytes = len(raw)

    try:
        optimized, meta = optimize_logo(raw, ext)
    except ValueError as e:
        return {
            "path": str(path),
            "status": "error",
            "error": str(e),
            "original_bytes": original_bytes,
        }

    final_bytes = len(optimized)
    savings_pct = meta.get("savings_pct", 0.0)

    if meta.get("note") == "passthrough_vector":
        return {
            "path": str(path),
            "status": "skip_vector",
            "original_bytes": original_bytes,
            "final_bytes": final_bytes,
            "savings_pct": 0.0,
        }

    # Skip the rewrite when the savings would be negligible — avoid
    # disk churn on already-optimized files. The threshold catches
    # the case where the file was uploaded recently AFTER the
    # optimization commit landed (those are already tight).
    if savings_pct < _REWRITE_THRESHOLD_PCT:
        return {
            "path": str(path),
            "status": "skip_negligible",
            "original_bytes": original_bytes,
            "final_bytes": final_bytes,
            "savings_pct": savings_pct,
        }

    if not dry_run:
        path.write_bytes(optimized)

    if verbose:
        print(
            f"  optimized {path.name}: "
            f"{meta.get('original_size')} → {meta.get('final_size')}  "
            f"{original_bytes} → {final_bytes} bytes ({savings_pct}% saved)"
        )

    return {
        "path": str(path),
        "status": "applied" if not dry_run else "would_apply",
        "original_bytes": original_bytes,
        "final_bytes": final_bytes,
        "savings_pct": savings_pct,
    }


def _run(dry_run: bool, verbose: bool) -> int:
    logos_dir = _BACKEND_DIR / "uploads" / "logos"
    if not logos_dir.is_dir():
        print(f"No logos directory at {logos_dir}. Nothing to do.")
        return 0

    files = sorted(logos_dir.iterdir())
    raster_files = [
        f for f in files
        if f.is_file() and f.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".svg"}
    ]

    print("=" * 70)
    mode = "DRY-RUN" if dry_run else "APPLY"
    print(f"optimize_existing_logos — {mode}")
    print("=" * 70)
    print(f"Logos directory: {logos_dir}")
    print(f"Raster files:    {len(raster_files)}")
    print()

    counts = {"applied": 0, "would_apply": 0,
              "skip_negligible": 0, "skip_vector": 0, "error": 0}
    total_original = 0
    total_final = 0
    errors = []

    for f in raster_files:
        result = _process_file(f, dry_run=dry_run, verbose=verbose)
        counts[result["status"]] = counts.get(result["status"], 0) + 1
        total_original += result.get("original_bytes", 0)
        total_final += result.get("final_bytes", 0)
        if result["status"] == "error":
            errors.append(result)

    print()
    print("=" * 70)
    print("Summary")
    print("=" * 70)
    for k, v in counts.items():
        if v:
            print(f"  {k:18s} {v}")
    if total_original > 0:
        saved = total_original - total_final
        pct = round(100.0 * saved / total_original, 1) if total_original else 0.0
        print(f"  total_original     {total_original} bytes")
        print(f"  total_final        {total_final} bytes")
        print(f"  saved              {saved} bytes ({pct}%)")

    if errors:
        print()
        print("Errors:")
        for e in errors:
            print(f"  - {e['path']}: {e['error']}")
        return 1
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--dry-run", action="store_true",
                        help="Inspect + report savings, no writes")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Log each file processed")
    args = parser.parse_args()
    rc = _run(dry_run=args.dry_run, verbose=args.verbose)
    sys.exit(rc)


if __name__ == "__main__":
    main()
