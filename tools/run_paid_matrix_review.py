#!/usr/bin/env python3
"""Run bounded DeepSeek + Qwen paid reviews under hard Garden budget controls.

This runner is proposal-only. It never admits a semantic delta, spends from
Challenger/Escalation/Emergency pools, or reviews non-public material.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any
from urllib import error, request

from tools import matrix_design_review as review

CHAT = "https://openrouter.ai/api/v1/chat/completions"
SELECTION = Path("agents/runtime/paid-selection.json")
OUT_DIR = Path("agents/outbox/hourly/paid-review")
BUNDLE = Path("agents/outbox/hourly/paid-review-bundle.json")


def _call(
    *,
    model: dict[str, Any],
    prompt: str,
    selection: dict[str, Any],
    reasoning: dict[str, Any] | None = None,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    model_id = str(model["model"])
    family = str(model["family"])
    if family not in {"deepseek", "qwen"}:
        raise RuntimeError(f"unapproved paid reviewer family: {family}")
    if model_id.endswith(":free"):
        raise RuntimeError(f"free route is not a paid routine reviewer: {model_id}")
    if len(prompt) > int(selection["max_prompt_characters"]):
        return None, {
            "status": "PROMPT_TOO_LARGE",
            "family": family,
            "model": model_id,
            "cost": 0.0,
            "prompt_characters": len(prompt),
        }

    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        return None, {"status": "KEY_UNAVAILABLE", "family": family, "model": model_id, "cost": None}

    provider_policy = selection["provider_policy"]
    max_price = provider_policy["max_price_usd_per_million_tokens"]
    body = {
        "model": model_id,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": int(selection["max_output_tokens"]),
        "provider": {
            "sort": provider_policy.get("sort", "price"),
            "allow_fallbacks": bool(provider_policy.get("allow_fallbacks", True)),
            "data_collection": provider_policy.get("data_collection", "deny"),
            "max_price": {
                "prompt": float(max_price["prompt"]),
                "completion": float(max_price["completion"]),
            },
        },
    }
    if reasoning is not None:
        body["reasoning"] = reasoning
    req = request.Request(
        CHAT,
        method="POST",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/ankitdcx/garden-swarm",
            "X-Title": "Garden Routine Paid Design Review",
        },
    )
    try:
        with request.urlopen(req, timeout=300) as response:
            data = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        return None, {
            "status": f"HTTP_{exc.code}",
            "family": family,
            "model": model_id,
            "cost": None,
            "detail": detail[:1000],
        }
    except Exception as exc:
        return None, {
            "status": "PROVIDER_ERROR",
            "family": family,
            "model": model_id,
            "cost": None,
            "detail": f"{type(exc).__name__}: {exc}",
        }

    usage = data.get("usage") or {}
    cost = usage.get("cost")
    if cost is None:
        return None, {
            "status": "COST_UNVERIFIED",
            "family": family,
            "model": model_id,
            "cost": None,
            "usage": usage,
        }
    cost = float(cost)
    if cost > float(selection["routine_model_call_cost_ceiling_usd"]):
        return None, {
            "status": "MODEL_COST_CEILING_EXCEEDED",
            "family": family,
            "model": model_id,
            "cost": cost,
            "usage": usage,
        }

    try:
        content = data["choices"][0]["message"].get("content", "")
    except Exception:
        content = ""
    raw = review._clean_json(content)
    return raw, {
        "status": "CALLED",
        "family": family,
        "model": model_id,
        "cost": cost,
        "usage": usage,
    }


def main() -> int:
    root = Path(".").resolve()
    matrix, target = review.load_matrix(root)
    if target.get("public_only") is not True:
        raise SystemExit("paid public reviewer refused non-public target")
    source, trace = review.extract_target(root, target)
    selection = json.loads(SELECTION.read_text(encoding="utf-8"))
    if selection.get("schema") != "GardenPaidModelSelection/v1":
        raise SystemExit("unsupported paid reviewer selection schema")
    if selection.get("design_epoch") != matrix.get("design_epoch"):
        raise SystemExit("paid reviewer selection DesignEpoch mismatch")

    selected = list(selection.get("selected") or [])
    families = [str(row.get("family")) for row in selected]
    if families != ["deepseek", "qwen"]:
        raise SystemExit("paid routine execution requires exactly DeepSeek + Qwen")

    attempts: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    for model in selected:
        family = str(model["family"])
        prompt = review.independent_prompt(target=target, source=source, trace=trace, model=model)
        raw, attempt = _call(model=model, prompt=prompt, selection=selection)
        attempt["phase"] = "INDEPENDENT"
        attempts.append(attempt)
        if raw is None:
            continue
        try:
            finding = review.validate_independent(
                raw,
                target_id=target["target_id"],
                family=family,
                model_id=str(model["model"]),
            )
        except Exception as exc:
            attempts.append({
                "phase": "INDEPENDENT_PARSE",
                "status": "INVALID_OUTPUT",
                "family": family,
                "model": model["model"],
                "cost": 0.0,
                "detail": str(exc),
            })
            continue
        findings.append(finding)
        (OUT_DIR / f"{family}-independent.json").write_text(
            json.dumps(finding, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    # Account for every observed non-negative provider charge, including a call
    # that itself exceeded the per-model ceiling. Never under-report spend.
    charged = [
        float(row["cost"])
        for row in attempts
        if isinstance(row.get("cost"), (int, float)) and float(row["cost"]) >= 0
    ]
    total_cost = sum(charged)
    hourly_ceiling = float(selection["routine_hourly_cost_ceiling_usd"])
    if total_cost > hourly_ceiling:
        status = "HOURLY_COST_CEILING_EXCEEDED"
    elif len({row["reviewer_family"] for row in findings}) == 2:
        status = "PAID_BLIND_REVIEW_COMPLETE_PROPOSALS_ONLY"
    else:
        status = "PARTIAL_PAID_REVIEW_PROPOSALS_ONLY"

    bundle = {
        "schema": "GardenPaidDesignReviewBundle/v1",
        "created_at_unix": int(time.time()),
        "design_epoch": matrix["design_epoch"],
        "canonical_source_root_sha256": matrix["canonical_source_root_sha256"],
        "target_id": target["target_id"],
        "source_trace": trace,
        "selected_families": families,
        "completed_families": sorted({row["reviewer_family"] for row in findings}),
        "provider_attempts": attempts,
        "independent_findings": findings,
        "routine_hourly_cost_ceiling_usd": hourly_ceiling,
        "actual_cost_usd": round(total_cost, 8),
        "status": status,
        "requires_separate_gemini_lane": True,
        "requires_separate_chatgpt_lane": True,
        "requires_cross_examination": True,
        "semantic_delta_admitted": False,
    }
    BUNDLE.parent.mkdir(parents=True, exist_ok=True)
    BUNDLE.write_text(json.dumps(bundle, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "target_id": target["target_id"],
        "status": status,
        "completed_families": bundle["completed_families"],
        "actual_cost_usd": bundle["actual_cost_usd"],
        "hourly_cost_ceiling_usd": hourly_ceiling,
        "semantic_delta_admitted": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
