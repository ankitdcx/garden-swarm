#!/usr/bin/env python3
"""Run one material-change-gated GPT-6 Astra synthesis call through OpenRouter.

This is proposal synthesis only. It never replaces independent-family review,
admits semantic deltas, grants authority, or promotes Garden canon.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import time
from pathlib import Path
from typing import Any
from urllib import error, request

from tools import matrix_design_review as review
from tools import run_paid_matrix_review as paid

CHAT = "https://openrouter.ai/api/v1/chat/completions"
POLICY = Path("agents/event-driven-context-policy.json")
PAID_POLICY = Path("agents/openrouter-paid-review-policy.json")
DEFAULT_PACKET = Path("agents/runtime/material-context.json")
DEFAULT_OUTPUT = Path("agents/outbox/event-driven/frontier-council.json")


def load_policy() -> tuple[dict[str, Any], dict[str, Any]]:
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    paid_policy = json.loads(PAID_POLICY.read_text(encoding="utf-8"))
    if policy.get("schema") != "GardenEventDrivenContextPolicy/v1":
        raise ValueError("unsupported event-driven context policy schema")
    if paid_policy.get("schema") != "GardenOpenRouterPaidReviewPolicy/v1":
        raise ValueError("unsupported OpenRouter paid policy schema")
    if policy.get("public_only") is not True or paid_policy.get("public_only") is not True:
        raise ValueError("frontier public adapter requires public-only policies")
    return policy, paid_policy


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
    cfg = policy["frontier_council"]
    if not cfg.get("enabled"):
        return False, "FRONTIER_COUNCIL_DISABLED"
    if packet.get("material") is not True:
        return False, "NOT_MATERIAL"
    if packet.get("frontier_call_eligible") is not True:
        return False, str(packet.get("packet_status") or "PACKET_NOT_ELIGIBLE")
    if not packet.get("materiality_reasons"):
        return False, "MISSING_MATERIALITY_RECEIPT"
    chars = len(json.dumps(packet, ensure_ascii=False, separators=(",", ":")))
    if chars > int(cfg["max_prompt_characters"]):
        return False, "PACKET_TOO_LARGE"
    return True, "MATERIAL_CONTEXT_ELIGIBLE"


def build_prompt(packet: dict[str, Any]) -> str:
    return f"""You are Garden's selective frontier synthesis reviewer. You are seeing a compact public
context packet only because a separate materiality gate fired.

Your job is to synthesize what changed, test contradictions, identify missing evidence,
and recommend bounded next checks. Do not invent source facts. Source/evidence references
in the packet are back-pointers, not proof by themselves. If the packet is insufficient,
say so.

This output is proposal evidence only. You cannot grant authority, admit a semantic delta,
declare proof/certification, merge code, or promote Garden canon.

Return one JSON object only with exactly these fields:
material_change (string);
contradictions (array);
missing_evidence (array);
recommended_next_checks (array);
context_snapshot (string);
uncertainty (string);
disposition (NO_CHANGE|PROPOSAL_ONLY|NEEDS_MORE_EVIDENCE|BLOCKER).

--- BEGIN MATERIAL CONTEXT PACKET ---
{json.dumps(packet, ensure_ascii=False, separators=(",", ":"))}
--- END MATERIAL CONTEXT PACKET ---"""


def _clean_json(text: str) -> dict[str, Any] | None:
    return review._clean_json(text)


def validate_output(value: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("frontier council returned no JSON object")
    required = [
        "material_change", "contradictions", "missing_evidence",
        "recommended_next_checks", "context_snapshot", "uncertainty", "disposition",
    ]
    if set(value) != set(required):
        raise ValueError("frontier council output must contain exactly the required fields")
    for key in ("contradictions", "missing_evidence", "recommended_next_checks"):
        if not isinstance(value[key], list):
            raise ValueError(f"{key} must be a list")
    if value["disposition"] not in {"NO_CHANGE", "PROPOSAL_ONLY", "NEEDS_MORE_EVIDENCE", "BLOCKER"}:
        raise ValueError("invalid frontier council disposition")
    return value


def call_astra(*, packet: dict[str, Any], policy: dict[str, Any], paid_policy: dict[str, Any]) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    ok, reason = eligible(packet, policy)
    cfg = policy["frontier_council"]
    model = str(cfg["primary_model"])
    if not ok:
        return None, {"status": f"SKIPPED_{reason}", "model": model, "cost": 0.0}

    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        return None, {"status": "KEY_UNAVAILABLE", "model": model, "cost": None}

    max_call = float(cfg["max_call_cost_usd"])
    daily_ceiling = float(paid_policy["daily_openrouter_cost_ceiling_usd"])
    usage_daily, daily_receipt = paid._key_usage_daily(key)
    if usage_daily is None:
        return None, {
            "status": "DAILY_USAGE_UNVERIFIED", "model": model, "cost": None,
            "daily_budget_receipt": daily_receipt,
        }
    if usage_daily + max_call > daily_ceiling:
        return None, {
            "status": "DAILY_BUDGET_RESERVED_EXHAUSTED", "model": model, "cost": 0.0,
            "usage_daily_before_call": usage_daily,
            "daily_openrouter_cost_ceiling_usd": daily_ceiling,
            "reserved_max_call_cost_usd": max_call,
            "daily_budget_receipt": daily_receipt,
        }

    prompt = build_prompt(packet)
    if len(prompt) > int(cfg["max_prompt_characters"]):
        return None, {"status": "PROMPT_TOO_LARGE", "model": model, "cost": 0.0, "prompt_characters": len(prompt)}

    provider = cfg["provider_policy"]
    max_price = provider["max_price_usd_per_million_tokens"]
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": int(cfg["max_output_tokens"]),
        "provider": {
            "sort": provider.get("sort", "price"),
            "allow_fallbacks": bool(provider.get("allow_fallbacks", True)),
            "data_collection": provider.get("data_collection", "deny"),
            "max_price": {
                "prompt": float(max_price["prompt"]),
                "completion": float(max_price["completion"]),
            },
        },
    }
    req = request.Request(
        CHAT,
        method="POST",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/ankitdcx/garden-swarm",
            "X-Title": "Garden Event-Driven Frontier Council",
        },
    )
    try:
        with request.urlopen(req, timeout=300) as response:
            data = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        return None, {
            "status": f"HTTP_{exc.code}", "model": model, "cost": None,
            "detail": detail[:1000], "daily_budget_receipt": daily_receipt,
        }
    except Exception as exc:
        return None, {
            "status": "PROVIDER_ERROR", "model": model, "cost": None,
            "detail": f"{type(exc).__name__}: {exc}", "daily_budget_receipt": daily_receipt,
        }

    usage = data.get("usage") or {}
    cost = usage.get("cost")
    try:
        if isinstance(cost, bool):
            raise ValueError("boolean cost")
        cost = float(cost)
        if not math.isfinite(cost) or cost < 0:
            raise ValueError("invalid cost")
    except (TypeError, ValueError):
        return None, {
            "status": "COST_UNVERIFIED", "model": model, "cost": None,
            "usage": usage, "daily_budget_receipt": daily_receipt,
        }
    if cost > max_call:
        return None, {
            "status": "MODEL_COST_CEILING_EXCEEDED", "model": model, "cost": cost,
            "usage": usage, "daily_budget_receipt": daily_receipt,
        }
    try:
        content = data["choices"][0]["message"].get("content", "")
    except Exception:
        content = ""
    return _clean_json(content), {
        "status": "CALLED", "model": model, "cost": cost, "usage": usage,
        "usage_daily_before_call": usage_daily, "daily_budget_receipt": daily_receipt,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet", default=str(DEFAULT_PACKET))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()
    policy, paid_policy = load_policy()
    packet = json.loads(Path(args.packet).read_text(encoding="utf-8"))
    raw, attempt = call_astra(packet=packet, policy=policy, paid_policy=paid_policy)

    if raw is None:
        output = {
            "schema": "GardenFrontierCouncilReceipt/v1",
            "created_at_unix": int(time.time()),
            "packet_sha256": packet.get("packet_sha256"),
            "provider_attempt": attempt,
            "status": attempt["status"],
            "frontier_output": None,
            "semantic_delta_admitted": False,
            "authority_granted": False,
            "canonical_effect": "NONE",
        }
    else:
        try:
            result = validate_output(raw)
            status = "FRONTIER_SYNTHESIS_COMPLETE_PROPOSAL_ONLY"
        except Exception as exc:
            result = None
            status = "INVALID_FRONTIER_OUTPUT"
            attempt = {**attempt, "validation_error": str(exc)}
        output = {
            "schema": "GardenFrontierCouncilReceipt/v1",
            "created_at_unix": int(time.time()),
            "packet_sha256": packet.get("packet_sha256"),
            "provider_attempt": attempt,
            "status": status,
            "frontier_output": result,
            "semantic_delta_admitted": False,
            "authority_granted": False,
            "canonical_effect": "NONE",
        }

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": output["status"],
        "model": attempt.get("model"),
        "cost": attempt.get("cost"),
        "semantic_delta_admitted": False,
        "authority_granted": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
