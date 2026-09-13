#!/usr/bin/env python3
"""Run Gemini only every third hourly cycle to preserve free-tier quota."""
from __future__ import annotations
import json, subprocess, sys, time
from pathlib import Path

OUT = Path("agents/outbox/hourly/gemini-review.json")


def main() -> int:
    slot = int(time.time() // 3600)
    if slot % 3 == 0:
        return subprocess.call([sys.executable, "tools/gemini_free_review.py"])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    receipt = {
        "schema": "GardenGeminiAvailabilityReceipt/v1",
        "provider": "google-gemini-developer-api",
        "model": "gemini-3.5-flash",
        "hour_slot": slot,
        "lane": "none",
        "status": "SKIPPED_FREE_QUOTA_PRESERVATION",
        "reason": "Gemini intentionally runs every third hourly cycle (8 calls/day).",
        "admission_status": "NO_MODEL_FINDING",
    }
    OUT.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
