#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any
from urllib import error, request

from tools.matrix_design_review import extract_target, load_matrix, validate_final, validate_independent

API = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-v4-flash"
BLIND_OUT = Path("agents/outbox/hourly/deepseek-independent.json")
FINAL_OUT = Path("agents/outbox/hourly/deepseek-final.json")
OPENROUTER_BUNDLE = Path("agents/outbox/hourly/design-review-bundle.json")
# Worst-case current peak list prices per 1M tokens. Cache discounts are ignored.
PEAK_INPUT_USD_PER_M = 0.44
PEAK_OUTPUT_USD_PER_M = 1.32


def estimate_tokens(text: str) -> int:
    return max(1, (len(text) + 3) // 4)


def worst_case_cost(prompt: str, max_tokens: int) -> float:
    return estimate_tokens(prompt) / 1_000_000 * PEAK_INPUT_USD_PER_M + max_tokens / 1_000_000 * PEAK_OUTPUT_USD_PER_M


def disabled_receipt(phase: str, reason: str) -> dict[str, Any]:
    return {
        "schema": "GardenDeepSeekReviewAvailabilityReceipt/v1",
        "provider": "deepseek",
        "model": MODEL,
        "phase": phase,
        "status": "DISABLED_OR_UNAVAILABLE",
        "reason": reason,
        "semantic_delta_admitted": False,
    }


def call_deepseek(prompt: str, *, phase: str, max_tokens: int, hourly_cap: float) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    key = os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        return None, disabled_receipt(phase, "DEEPSEEK_API_KEY not configured")
    if hourly_cap <= 0:
        return None, disabled_receipt(phase, "explicit paid DeepSeek hourly budget is zero or absent")
    phase_cap = hourly_cap / 2.0
    estimate = worst_case_cost(prompt, max_tokens)
    if estimate > phase_cap:
        return None, disabled_receipt(phase, f"worst-case call estimate ${estimate:.6f} exceeds phase cap ${phase_cap:.6f}")

    body = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "thinking": {"type": "enabled", "reasoning_effort": "low"},
        "temperature": 0.05,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"},
    }
    req = request.Request(API, method="POST", data=json.dumps(body).encode("utf-8"), headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    try:
        with request.urlopen(req, timeout=360) as response:
            data = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:1200]
        return None, disabled_receipt(phase, f"DeepSeek HTTP {exc.code}: {detail}")
    except Exception as exc:
        return None, disabled_receipt(phase, f"{type(exc).__name__}: {exc}")

    choice = (data.get("choices") or [{}])[0]
    content = str((choice.get("message") or {}).get("content") or "").strip()
    try:
        value = json.loads(content)
    except Exception as exc:
        return None, {
            **disabled_receipt(phase, f"invalid JSON output: {exc}"),
            "finish_reason": choice.get("finish_reason"),
            "raw_output_excerpt": content[:1000],
        }
    usage = data.get("usage") or {}
    actual_upper_bound = (int(usage.get("prompt_tokens") or 0) / 1_000_000 * PEAK_INPUT_USD_PER_M + int(usage.get("completion_tokens") or 0) / 1_000_000 * PEAK_OUTPUT_USD_PER_M)
    return value, {
        "schema":"GardenDeepSeekProviderReceipt/v1",
        "provider":"deepseek",
        "model":MODEL,
        "phase":phase,
        "status":"CALLED",
        "usage":usage,
        "finish_reason":choice.get("finish_reason"),
        "worst_case_preflight_usd":estimate,
        "actual_peak_rate_upper_bound_usd":actual_upper_bound,
        "hourly_budget_usd":hourly_cap,
        "semantic_delta_admitted":False,
    }


def blind_prompt(target: dict[str, Any], source: str, trace: dict[str, Any]) -> str:
    return f"""You are the independent DeepSeek Garden reviewer. You have not seen peer conclusions. Review ONLY this bounded public target and try to falsify it before proposing complexity. Keep JSON concise: strings <=300 chars; arrays <=2 items. Return one JSON object with keys source_anchors, current_semantic_claim, falsification_attempts, evidence_search_trace, proposed_delta, do_nothing_comparison, affected_invariants, affected_tests, affected_contracts, uncertainty, evidence_ancestry, overturn_conditions, disposition. disposition=NO_CHANGE|PROPOSE_DELTA|BLOCKER|NEEDS_CROSS_REFERENCE.
Target={target['target_id']} Question={target['review_question']} Trace={json.dumps(trace, ensure_ascii=False)}
--- TARGET ---
{source}
--- END ---"""


def final_prompt(target: dict[str, Any], own: dict[str, Any], peers: list[dict[str, Any]]) -> str:
    compact_peers = [{k:r.get(k) for k in ("reviewer_family","current_semantic_claim","proposed_delta","disposition","uncertainty")} for r in peers]
    return f"""You are DeepSeek doing round-2 peer cross-examination for the SAME Garden target. Do not vote. Challenge concrete peer claims and common evidence ancestry. Keep JSON concise. Return one JSON object with keys peer_challenges, correlated_or_common_source_evidence, revised_disposition, revised_delta, do_nothing_comparison, uncertainty, overturn_conditions. revised_disposition=NO_CHANGE|PROPOSE_DELTA|BLOCKER|NEEDS_CROSS_REFERENCE.
Target={target['target_id']} Own={json.dumps(own, ensure_ascii=False)} Peers={json.dumps(compact_peers, ensure_ascii=False)}"""


def write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("independent","final"), required=True)
    args = parser.parse_args()
    cap = float(os.environ.get("GARDEN_DEEPSEEK_MAX_USD_PER_HOUR", "0") or 0)
    root = Path(".").resolve()
    matrix, target = load_matrix(root)
    source, trace = extract_target(root, target)

    if args.phase == "independent":
        raw, provider = call_deepseek(blind_prompt(target, source, trace), phase="INDEPENDENT", max_tokens=3200, hourly_cap=cap)
        if raw is None:
            write(BLIND_OUT, provider)
            return 0
        try:
            finding = validate_independent(raw, target_id=target["target_id"], family="deepseek", model_id=MODEL)
        except Exception as exc:
            write(BLIND_OUT, {**provider, "status":"INVALID_OUTPUT", "detail":str(exc)})
            return 0
        write(BLIND_OUT, {"schema":"GardenDeepSeekIndependentReviewReceipt/v1","target_id":target["target_id"],"design_epoch":matrix["design_epoch"],"source_root":matrix["canonical_source_root_sha256"],"source_trace":trace,"provider_receipt":provider,"finding":finding,"semantic_delta_admitted":False})
        return 0

    if not BLIND_OUT.is_file() or not OPENROUTER_BUNDLE.is_file():
        write(FINAL_OUT, disabled_receipt("CROSS_EXAMINATION", "independent DeepSeek receipt or OpenRouter bundle missing"))
        return 0
    blind = json.loads(BLIND_OUT.read_text(encoding="utf-8"))
    own = blind.get("finding")
    bundle = json.loads(OPENROUTER_BUNDLE.read_text(encoding="utf-8"))
    if not isinstance(own, dict) or blind.get("target_id") != bundle.get("target", {}).get("target_id"):
        write(FINAL_OUT, disabled_receipt("CROSS_EXAMINATION", "DeepSeek blind review is missing or target-mismatched"))
        return 0
    peers = list(bundle.get("independent_findings") or [])
    raw, provider = call_deepseek(final_prompt(target, own, peers), phase="CROSS_EXAMINATION", max_tokens=2200, hourly_cap=cap)
    if raw is None:
        write(FINAL_OUT, provider)
        return 0
    try:
        final = validate_final(raw, target_id=target["target_id"], family="deepseek", model_id=MODEL)
    except Exception as exc:
        write(FINAL_OUT, {**provider, "status":"INVALID_OUTPUT", "detail":str(exc)})
        return 0
    write(FINAL_OUT, {"schema":"GardenDeepSeekFinalReviewReceipt/v1","target_id":target["target_id"],"design_epoch":matrix["design_epoch"],"source_root":matrix["canonical_source_root_sha256"],"provider_receipt":provider,"disposition":final,"semantic_delta_admitted":False})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
