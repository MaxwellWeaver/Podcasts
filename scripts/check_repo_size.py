"""Capacity tripwire. Run from the deploy stage or manually.

Walks the git working tree and prints repo size + warnings as it approaches
the GitHub free-tier soft limits. When you see the WARN at 800 MB, plan the
R2 migration. When you see CRIT at 950 MB, do it now.

Usage:
    python scripts/check_repo_size.py            # human-readable
    python scripts/check_repo_size.py --quiet    # only print on warn/crit
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

WARN_MB = 800
CRIT_MB = 950


def repo_size_bytes(root: Path) -> int:
    total = 0
    for p in root.rglob("*"):
        # Skip the .git dir (we care about working-tree growth, which is what
        # GitHub's repo size warning is based on) and the venv.
        rel = p.relative_to(root).parts
        if rel and rel[0] in {".git", ".venv", "__pycache__", "episodes", "logs"}:
            continue
        try:
            if p.is_file():
                total += p.stat().st_size
        except OSError:
            pass
    return total


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quiet", action="store_true", help="Only print on WARN/CRIT.")
    args = ap.parse_args()

    n = repo_size_bytes(PROJECT_ROOT)
    mb = n / 1024 / 1024

    level = "OK"
    if mb >= CRIT_MB:
        level = "CRIT"
    elif mb >= WARN_MB:
        level = "WARN"

    if level != "OK" or not args.quiet:
        print(f"[{level}] tracked working-tree size: {mb:.1f} MB "
              f"(WARN at {WARN_MB} MB, CRIT at {CRIT_MB} MB)")

    if level == "WARN":
        print("Plan the Cloudflare R2 audio migration soon. See README -> Capacity.")
    elif level == "CRIT":
        print("MIGRATE NOW. GitHub will start blocking pushes near 1 GB. See README.")

    return 0 if level != "CRIT" else 2


if __name__ == "__main__":
    sys.exit(main())
