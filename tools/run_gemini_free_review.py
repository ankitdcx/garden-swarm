#!/usr/bin/env python3
"""Run the direct Gemini reviewer every hourly Garden review cycle.

The child module writes a typed availability receipt and exits cleanly when the
free-tier provider is unavailable or quota-limited, so other reviewer lanes are
not aborted.
"""
from __future__ import annotations

import subprocess
import sys


def main() -> int:
    # Module execution keeps the repository root on sys.path and avoids the
    # historical `ModuleNotFoundError: No module named 'tools'` failure caused
    # by executing tools/gemini_free_review.py as a script path.
    return subprocess.call([sys.executable, "-m", "tools.gemini_free_review"])


if __name__ == "__main__":
    raise SystemExit(main())
