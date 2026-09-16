#!/usr/bin/env python3
"""Durably queue recorded OpenRouter reviews for external ChatGPT quality adjudication.

This module performs no model inference and grants no authority. It is designed to
run inside the existing secret-free continuation transaction so quality events do
not require a second durable-state round trip.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from tools import independent_branch_protocol as protocol

ASSESSMENT_SCHEMA = "GardenReviewerQualityAssessmentRequest/v1"
QUALITY_STATUS = "AWAITING_CHATGPT_ADJUDICATION"
WORKER_PROTOCOL = protocol.PROTOCOL_ID


def _slot_for(registry: dict[str, Any], family: str, model: str) -> dict[str, Any]:
    if registry.get("schema") != "GardenReviewerSlotRegistry/v1":
        raise ValueError("unsupported reviewer slot registry")
    matches = [row for row in registry.get("slots", [])
               if row.get("family") == family and row.get("model") == model]
    if len(matches) != 1:
        raise ValueError("recorded reviewer does not resolve exactly one governed slot")
    return matches[0]


def _record_for_attempt(state: dict[str, Any], attempt: dict[str, Any]) -> dict[str, Any]:
    cycle = (state.get("convergence_cycles") or {}).get(attempt.get("cycle"))
    if not isinstance(cycle, dict):
        raise ValueError("recorded reviewer attempt has no convergence cycle")
    finding_hash = attempt.get("finding_sha256")
    records: list[dict[str, Any]] = []
    records.extend((cycle.get("blind") or {}).values())
    for rows in (cycle.get("reconcile") or {}).values():
        records.extend(rows or [])
    records.extend((cycle.get("final") or {}).values())
    records.extend((cycle.get("confirm") or {}).values())
    matches = [row for row in records if row.get("finding_sha256") == finding_hash]
    if len(matches) != 1:
        raise ValueError("recorded reviewer finding does not resolve exactly one branch record")
    return matches[0]


def _request_for(state: dict[str, Any], attempt: dict[str, Any], registry: dict[str, Any], now: float) -> dict[str, Any]:
    response = attempt.get("response_text")
    if not isinstance(response, str) or not response:
        raise ValueError("recorded review is missing response text")
    family = str(attempt.get("family") or "")
    model = str(attempt.get("model") or "")
    slot = _slot_for(registry, family, model)
    record = _record_for_attempt(state, attempt)
    finding = record.get("finding") or {}
    response_hash = protocol.sha256_text(response)
    core = {
        "task_key": attempt.get("task_key"),
        "cycle": attempt.get("cycle"),
        "review_slot": attempt.get("slot"),
        "slot_id": slot["slot_id"],
        "family": family,
        "model": model,
        "phase": attempt.get("phase"),
        "source_packet_sha256": attempt.get("source_packet_sha256"),
        "response_sha256": response_hash,
        "finding_sha256": attempt.get("finding_sha256"),
        "context_sufficiency": finding.get("context_sufficiency"),
        "peer_content_seen": bool(record.get("peer_content_seen")),
        "evidence_stage": record.get("evidence_stage", "ISOLATED_BRANCH"),
        "synthesis_audit_sha256": record.get("synthesis_audit_sha256"),
        "response_id": attempt.get("response_id"),
        "run_id": attempt.get("run_id"),
    }
    request_id = protocol.sha256_value(core)
    return {
        "schema": ASSESSMENT_SCHEMA,
        "request_id": request_id,
        **core,
        "status": QUALITY_STATUS,
        "assessment_owner": "EXTERNAL_CHATGPT_FRONTIER",
        "quality_receipt_schema": "GardenReviewerQualityReceipt/v1",
        "cost_usd": attempt.get("cost"),
        "created": now,
        "semantic_delta_admitted": False,
        "quality_assessment_is_not_proof_or_authority": True,
    }


def queue_pending_assessments(state: dict[str, Any], registry: dict[str, Any], *, now: float | None = None,
                              limit: int = 20) -> int:
    """Queue unassessed current-protocol REVIEW_RECORDED attempts, deduped by response hash."""
    if limit < 1 or limit > 100:
        raise ValueError("quality queue scan limit must be in [1,100]")
    now = time.time() if now is None else float(now)
    queue = state.setdefault("reviewer_quality_queue", [])
    queued_hashes = {row.get("response_sha256") for row in queue if isinstance(row, dict)}
    added = 0
    for attempt in state.get("attempts", []):
        if added >= limit:
            break
        if attempt.get("status") != "REVIEW_RECORDED":
            continue
        if attempt.get("protocol") != WORKER_PROTOCOL:
            continue
        response = attempt.get("response_text")
        if not isinstance(response, str) or not response:
            raise ValueError("current-protocol recorded review is missing response text")
        response_hash = protocol.sha256_text(response)
        if response_hash in queued_hashes:
            attempt["reviewer_quality_status"] = QUALITY_STATUS
            attempt["response_sha256"] = response_hash
            continue
        request = _request_for(state, attempt, registry, now)
        if request["peer_content_seen"] is not False:
            phase = attempt.get("phase")
            cycle = state["convergence_cycles"][attempt["cycle"]]
            bound = cycle.get(("final" if phase == "FINAL" else "confirm") + "_synthesis_audit_sha256")
            if (phase not in ("FINAL", "CONFIRM") or
                    request["evidence_stage"] != "POST_BLIND_SYNTHESIS_AUDIT" or
                    not bound or request["synthesis_audit_sha256"] != bound or
                    attempt.get("synthesis_audit_sha256") != bound):
                raise ValueError("quality request detected unauthorized peer-content exposure")
        queue.append(request)
        queued_hashes.add(response_hash)
        attempt["reviewer_quality_status"] = QUALITY_STATUS
        attempt["reviewer_quality_request_id"] = request["request_id"]
        attempt["response_sha256"] = response_hash
        record = _record_for_attempt(state, attempt)
        record["reviewer_quality_status"] = QUALITY_STATUS
        record["reviewer_quality_request_id"] = request["request_id"]
        record["response_sha256"] = response_hash
        added += 1
    return added


def load_registry(root: Path = Path(".")) -> dict[str, Any]:
    return json.loads((root / "agents/reviewer-slot-registry.json").read_text(encoding="utf-8"))
