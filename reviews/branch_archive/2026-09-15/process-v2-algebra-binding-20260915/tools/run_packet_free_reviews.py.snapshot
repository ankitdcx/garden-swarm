#!/usr/bin/env python3
"""Run independent free OpenRouter reviewers on one validated packet; no peer cross-exam."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from tools import matrix_design_review as legacy
from tools.packet_review_common import finding_prompt, load_valid_packet, validate_blind_finding

SELECTION = Path("agents/runtime/free-selection.json")
OUT_DIR = Path("agents/outbox/hourly/packet-blind-free")
BUNDLE = Path("agents/outbox/hourly/packet-blind-free-bundle.json")


def main() -> int:
    packet, completeness, canonical_text = load_valid_packet()
    selection = json.loads(SELECTION.read_text(encoding="utf-8"))
    selected = list(selection.get("selected") or [])
    if not selected:
        raise SystemExit("no free reviewers selected")
    families = [str(x.get("family")) for x in selected]
    if len(families) != len(set(families)):
        raise SystemExit("duplicate reviewer families in free selection")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    findings: list[dict[str, Any]] = []
    attempts: list[dict[str, Any]] = []
    for model in selected:
        family = str(model["family"])
        role = str(model.get("role") or "independent_reviewer")
        prompt = finding_prompt(packet=packet, canonical_packet_text=canonical_text, family=family, role=role)
        raw, attempt = legacy.call_openrouter(model=model, prompt=prompt, max_tokens=3600)
        attempt.update({"phase": "BLIND", "family": family, "cycle_id": packet["cycle_id"], "packet_hash": packet["packet_hash"]})
        attempts.append(attempt)
        if raw is None:
            continue
        try:
            finding = validate_blind_finding(raw, packet=packet, family=family, model=str(model["model"]), role=role)
        except Exception as exc:
            attempts.append({"phase": "BLIND_PARSE", "family": family, "model": model["model"], "status": "INVALID_OUTPUT", "cost": 0, "detail": str(exc), "cycle_id": packet["cycle_id"], "packet_hash": packet["packet_hash"]})
            continue
        findings.append(finding)
        (OUT_DIR / f"{family}.json").write_text(json.dumps(finding, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    completed = sorted({x["reviewer_family"] for x in findings})
    bundle = {
        "schema": "GardenPacketBlindReviewBundle/v1",
        "created_at_unix": int(time.time()),
        "cycle_id": packet["cycle_id"],
        "packet_hash": packet["packet_hash"],
        "packet_completeness_status": completeness["status"],
        "provider": "openrouter-free",
        "selected_families": families,
        "completed_families": completed,
        "independent_findings": findings,
        "provider_attempts": attempts,
        "peer_findings_consumed": False,
        "cross_exam_performed": False,
        "semantic_delta_admitted": False,
        "status": "BLIND_REVIEW_COMPLETE" if len(completed) == len(families) else "PARTIAL_BLIND_REVIEW"
    }
    BUNDLE.parent.mkdir(parents=True, exist_ok=True)
    BUNDLE.write_text(json.dumps(bundle, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"cycle_id": packet["cycle_id"], "packet_hash": packet["packet_hash"], "status": bundle["status"], "completed_families": completed}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
