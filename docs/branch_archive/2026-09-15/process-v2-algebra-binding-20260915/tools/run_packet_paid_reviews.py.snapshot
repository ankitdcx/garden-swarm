#!/usr/bin/env python3
"""Run bounded paid OpenRouter blind reviewers on one validated packet."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from tools.packet_review_common import finding_prompt, load_valid_packet, validate_blind_finding
from tools.run_paid_matrix_review import _call

SELECTION = Path("agents/runtime/paid-selection.json")
OUT_DIR = Path("agents/outbox/hourly/packet-blind-paid")
BUNDLE = Path("agents/outbox/hourly/packet-blind-paid-bundle.json")


def main() -> int:
    packet, completeness, canonical_text = load_valid_packet()
    selection = json.loads(SELECTION.read_text(encoding="utf-8"))
    if selection.get("schema") != "GardenPaidModelSelection/v2":
        raise SystemExit("unsupported paid selection schema")
    selected = list(selection.get("selected") or [])
    families = [str(x.get("family")) for x in selected]
    approved = [str(x) for x in selection.get("approved_families") or []]
    if families != approved or len(set(families)) != len(families):
        raise SystemExit("paid selection family binding invalid")

    hourly_ceiling = float(selection["routine_hourly_cost_ceiling_usd"])
    per_call = float(selection["routine_model_call_cost_ceiling_usd"])
    charged = 0.0
    findings: list[dict[str, Any]] = []
    attempts: list[dict[str, Any]] = []
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    for model in selected:
        family = str(model["family"])
        role = str(model.get("role") or "independent_reviewer")
        if charged + per_call > hourly_ceiling:
            attempts.append({"phase": "BLIND", "status": "HOURLY_BUDGET_RESERVED_EXHAUSTED", "family": family, "model": model["model"], "cost": 0.0, "cycle_id": packet["cycle_id"], "packet_hash": packet["packet_hash"]})
            continue
        prompt = finding_prompt(packet=packet, canonical_packet_text=canonical_text, family=family, role=role)
        raw, attempt = _call(model=model, prompt=prompt, selection=selection)
        attempt.update({"phase": "BLIND", "cycle_id": packet["cycle_id"], "packet_hash": packet["packet_hash"]})
        attempts.append(attempt)
        cost = attempt.get("cost")
        if isinstance(cost, (int, float)) and float(cost) >= 0:
            charged += float(cost)
        if raw is None:
            continue
        try:
            finding = validate_blind_finding(raw, packet=packet, family=family, model=str(model["model"]), role=role)
        except Exception as exc:
            attempts.append({"phase": "BLIND_PARSE", "status": "INVALID_OUTPUT", "family": family, "model": model["model"], "cost": 0.0, "detail": str(exc), "cycle_id": packet["cycle_id"], "packet_hash": packet["packet_hash"]})
            continue
        findings.append(finding)
        (OUT_DIR / f"{family}.json").write_text(json.dumps(finding, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    completed = sorted({x["reviewer_family"] for x in findings})
    bundle = {
        "schema": "GardenPacketPaidBlindReviewBundle/v1",
        "created_at_unix": int(time.time()),
        "cycle_id": packet["cycle_id"],
        "packet_hash": packet["packet_hash"],
        "packet_completeness_status": completeness["status"],
        "selected_families": families,
        "completed_families": completed,
        "provider_attempts": attempts,
        "independent_findings": findings,
        "actual_cost_usd": round(charged, 8),
        "routine_hourly_cost_ceiling_usd": hourly_ceiling,
        "daily_openrouter_cost_ceiling_usd": float(selection["daily_openrouter_cost_ceiling_usd"]),
        "automatic_expensive_escalation_cost_ceiling_usd": 0.0,
        "peer_findings_consumed": False,
        "cross_exam_performed": False,
        "semantic_delta_admitted": False,
        "status": "BLIND_REVIEW_COMPLETE" if len(completed) == len(families) else "PARTIAL_BLIND_REVIEW"
    }
    BUNDLE.parent.mkdir(parents=True, exist_ok=True)
    BUNDLE.write_text(json.dumps(bundle, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"cycle_id": packet["cycle_id"], "packet_hash": packet["packet_hash"], "status": bundle["status"], "completed_families": completed, "actual_cost_usd": bundle["actual_cost_usd"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
