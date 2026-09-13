#!/usr/bin/env python3
"""Run exactly one free OpenRouter review per hour and degrade cleanly on free-tier exhaustion."""
from __future__ import annotations
import json, subprocess, sys
from pathlib import Path

SEL = Path("agents/runtime/free-selection.json")
OUT = Path("agents/outbox/hourly")


def main() -> int:
    sel = json.loads(SEL.read_text(encoding="utf-8"))
    slot = int(sel["hour_slot"])
    lane = "design" if slot % 2 == 0 else "repo"
    cmd = [sys.executable, f"tools/free_{lane}_review.py"]
    proc = subprocess.run(cmd, text=True, capture_output=True)
    print(proc.stdout, end="")
    if proc.returncode == 0:
        return 0
    print(proc.stderr, end="", file=sys.stderr)
    if "HTTP Error 429" not in proc.stderr:
        return proc.returncode
    OUT.mkdir(parents=True, exist_ok=True)
    receipt = {
        "schema": "GardenFreeReviewAvailabilityReceipt/v1",
        "hour_slot": slot,
        "lane": lane,
        "status": "RATE_LIMITED",
        "reason": "OpenRouter free-tier HTTP 429; no paid fallback attempted",
        "selected": sel.get("selected", []),
        "admission_status": "NO_MODEL_FINDING",
    }
    (OUT / "availability.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
