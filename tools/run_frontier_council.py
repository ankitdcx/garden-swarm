#!/usr/bin/env python3
"""Build one materiality-gated external ChatGPT frontier-review request.

Legacy filename retained for reference compatibility. This module performs NO model
or provider call, accepts NO provider credential and never routes ChatGPT/Astra
through OpenRouter. It only emits a provenance-bound GardenFrontierReviewRequest/v1
for the separately operated ChatGPT frontier lane.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Any

POLICY = Path("agents/event-driven-context-policy.json")
DEFAULT_PACKET = Path("agents/runtime/material-context.json")
DEFAULT_OUTPUT = Path("agents/outbox/event-driven/chatgpt-frontier-request.json")


def _hash(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def load_policy() -> dict[str, Any]:
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    if policy.get("schema") != "GardenEventDrivenContextPolicy/v2":
        raise ValueError("unsupported event-driven context policy schema")
    cfg = policy.get("frontier_handoff") or {}
    if cfg.get("provider_boundary") != "NOT_OPENROUTER":
        raise ValueError("frontier handoff must remain outside OpenRouter")
    if cfg.get("model_identity") != "USER_SELECTED_CHATGPT_MODEL_NOT_HARDCODED_BY_REPOSITORY":
        raise ValueError("frontier ChatGPT model identity must not be hardcoded")
    if cfg.get("contains_provider_credentials") is not False or cfg.get("contains_openrouter_model_route") is not False:
        raise ValueError("frontier handoff policy may not contain provider credentials or OpenRouter model routes")
    return policy


def validate_packet(packet: dict[str, Any], policy: dict[str, Any]) -> None:
    if packet.get("schema") != policy["context_packet"]["schema"]:
        raise ValueError("unsupported material-context packet schema")
    if packet.get("public_only") is not True:
        raise ValueError("non-public packet refused")
    if packet.get("semantic_delta_admitted") is not False or packet.get("authority_granted") is not False:
        raise ValueError("context packet may not claim semantic admission or authority")
    if not isinstance(packet.get("observations"), list):
        raise ValueError("context packet observations must be a list")


def eligible(packet: dict[str, Any], policy: dict[str, Any]) -> tuple[bool, str]:
    validate_packet(packet, policy)
    cfg = policy["frontier_handoff"]
    if not cfg.get("enabled"):
        return False, "FRONTIER_HANDOFF_DISABLED"
    if packet.get("material") is not True:
        return False, "NOT_MATERIAL"
    if packet.get("frontier_handoff_eligible") is not True:
        return False, str(packet.get("packet_status") or "PACKET_NOT_ELIGIBLE")
    if not packet.get("materiality_reasons"):
        return False, "MISSING_MATERIALITY_RECEIPT"
    return True, "MATERIAL_CONTEXT_ELIGIBLE"


def review_instruction() -> str:
    return (
        "You are Garden's external ChatGPT frontier reviewer. This compact public packet is supplied "
        "only because a separate materiality gate fired. Synthesize what materially changed, test "
        "contradictions, identify missing evidence and recommend bounded next checks. Do not invent "
        "source facts. Source/evidence references are back-pointers, not proof. If the compact packet "
        "is insufficient, request context expansion or whole-source review. Your output is proposal "
        "evidence only: it cannot grant authority, admit a semantic delta, declare proof/certification, "
        "merge code or promote Garden canon. Return GardenFrontierReviewResponse/v1."
    )


def build_request(packet: dict[str, Any], policy: dict[str, Any], *, now: float | None = None) -> dict[str, Any]:
    ok, reason = eligible(packet, policy)
    if not ok:
        raise ValueError(reason)
    cfg = policy["frontier_handoff"]
    created = time.time() if now is None else float(now)
    request = {
        "schema": cfg["request_schema"],
        "created_at_unix": created,
        "lane": cfg["lane"],
        "provider_boundary": cfg["provider_boundary"],
        "model_selection": "USER_PRODUCT_CONTEXT",
        "packet_sha256": packet.get("packet_sha256"),
        "materiality_reasons": packet.get("materiality_reasons"),
        "instruction": review_instruction(),
        "context_packet": packet,
        "expected_response_schema": cfg["response_schema"],
        "public_only": True,
        "contains_provider_credentials": False,
        "contains_openrouter_model_route": False,
        "semantic_delta_admitted": False,
        "authority_granted": False,
        "canonical_effect": "NONE",
    }
    chars = len(json.dumps(request, ensure_ascii=False, separators=(",", ":")))
    if chars > int(cfg["max_request_characters"]):
        raise ValueError("REQUEST_TOO_LARGE_REQUIRES_RECOMPACTION_OR_CONTEXT_EXPANSION")
    request["request_characters"] = chars
    request["request_sha256"] = _hash({k: v for k, v in request.items() if k != "request_sha256"})
    return request


def validate_response(value: dict[str, Any], request: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(value, dict) or value.get("schema") != policy["frontier_handoff"]["response_schema"]:
        raise ValueError("unsupported frontier response schema")
    if value.get("request_sha256") != request.get("request_sha256"):
        raise ValueError("frontier response does not bind the request")
    required = ["material_change", "contradictions", "missing_evidence", "recommended_next_checks", "context_snapshot", "uncertainty", "disposition"]
    if any(key not in value for key in required):
        raise ValueError("frontier response missing required fields")
    for key in ("contradictions", "missing_evidence", "recommended_next_checks"):
        if not isinstance(value[key], list):
            raise ValueError(f"{key} must be a list")
    if value["disposition"] not in {"NO_CHANGE", "PROPOSAL_ONLY", "NEEDS_MORE_EVIDENCE", "NEEDS_CONTEXT_EXPANSION", "BLOCKER"}:
        raise ValueError("invalid frontier response disposition")
    if value.get("authority_granted") not in (None, False) or value.get("semantic_delta_admitted") not in (None, False):
        raise ValueError("frontier response may not grant authority or self-admit semantic deltas")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet", default=str(DEFAULT_PACKET))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()
    policy = load_policy()
    packet = json.loads(Path(args.packet).read_text(encoding="utf-8"))
    ok, reason = eligible(packet, policy)
    if not ok:
        output = {
            "schema": "GardenFrontierReviewRequestReceipt/v1",
            "created_at_unix": int(time.time()),
            "packet_sha256": packet.get("packet_sha256"),
            "status": f"SKIPPED_{reason}",
            "request": None,
            "semantic_delta_admitted": False,
            "authority_granted": False,
            "canonical_effect": "NONE",
        }
    else:
        try:
            request_payload = build_request(packet, policy)
            status = "CHATGPT_FRONTIER_REQUEST_READY_PROPOSAL_ONLY"
        except ValueError as exc:
            request_payload = None
            status = str(exc)
        output = {
            "schema": "GardenFrontierReviewRequestReceipt/v1",
            "created_at_unix": int(time.time()),
            "packet_sha256": packet.get("packet_sha256"),
            "status": status,
            "request": request_payload,
            "semantic_delta_admitted": False,
            "authority_granted": False,
            "canonical_effect": "NONE",
        }
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": output["status"],
        "frontier_lane": policy["frontier_handoff"]["lane"],
        "provider_boundary": policy["frontier_handoff"]["provider_boundary"],
        "request_ready": output["request"] is not None,
        "semantic_delta_admitted": False,
        "authority_granted": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
