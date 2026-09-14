#!/usr/bin/env python3
"""Direct Gemini free-tier reviewer for the SAME active Garden matrix target.

Proposal-only. No web/search grounding, no repository write authority, and no
paid fallback. The Google project must remain on Gemini Free Tier.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from urllib import error, request

from tools.matrix_design_review import extract_target, independent_prompt, load_matrix, validate_independent

MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
BASE = "https://generativelanguage.googleapis.com/v1beta/models"
OUT = Path("agents/outbox/hourly/gemini-review.json")

SCHEMA = {
    "type": "object",
    "properties": {
        "source_anchors": {"type": "array", "items": {"type": "string"}, "minItems": 1},
        "current_semantic_claim": {"type": "string"},
        "falsification_attempts": {"type": "array", "items": {"type": "string"}, "minItems": 1},
        "evidence_search_trace": {"type": "array", "items": {"type": "string"}, "minItems": 1},
        "proposed_delta": {"type": "string"},
        "do_nothing_comparison": {"type": "string"},
        "affected_invariants": {"type": "array", "items": {"type": "string"}},
        "affected_tests": {"type": "array", "items": {"type": "string"}},
        "affected_contracts": {"type": "array", "items": {"type": "string"}},
        "uncertainty": {"type": "string"},
        "evidence_ancestry": {"type": "string"},
        "overturn_conditions": {"type": "string"},
        "disposition": {"type": "string", "enum": ["NO_CHANGE", "PROPOSE_DELTA", "BLOCKER", "NEEDS_CROSS_REFERENCE"]}
    },
    "required": [
        "source_anchors", "current_semantic_claim", "falsification_attempts",
        "evidence_search_trace", "proposed_delta", "do_nothing_comparison",
        "affected_invariants", "affected_tests", "affected_contracts",
        "uncertainty", "evidence_ancestry", "overturn_conditions", "disposition"
    ]
}


def availability(*, slot: int, target_id: str | None, status: str, reason: str, detail: str = "") -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": "GardenGeminiAvailabilityReceipt/v2",
        "provider": "google-gemini-developer-api",
        "model": MODEL,
        "hour_slot": slot,
        "target_id": target_id,
        "status": status,
        "reason": reason,
        "detail": detail[:1000],
        "admission_status": "NO_MODEL_FINDING",
        "semantic_delta_admitted": False,
        "cost_policy": "Gemini Free Tier only; no search grounding, retries to paid routes, or paid fallback."
    }
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False))
    return 0


def main() -> int:
    slot = int(time.time() // 3600)
    root = Path(".").resolve()
    matrix, target = load_matrix(root)
    target_id = str(target["target_id"])
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        return availability(slot=slot, target_id=target_id, status="KEY_UNAVAILABLE", reason="GEMINI_API_KEY is not configured")

    source, trace = extract_target(root, target)
    model_meta = {"family": "gemini", "role": "independent_long_context_reviewer", "model": MODEL}
    prompt = independent_prompt(target=target, source=source, trace=trace, model=model_meta)
    endpoint = f"{BASE}/{MODEL}:generateContent"
    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "maxOutputTokens": 3600,
            "responseMimeType": "application/json",
            "responseJsonSchema": SCHEMA
        }
    }
    req = request.Request(
        endpoint,
        method="POST",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-goog-api-key": key}
    )
    try:
        with request.urlopen(req, timeout=300) as response:
            data = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        status = "FREE_TIER_QUOTA_OR_PROVIDER_UNAVAILABLE" if exc.code in {403, 429} else "PROVIDER_ERROR"
        return availability(slot=slot, target_id=target_id, status=status, reason=f"Gemini HTTP {exc.code}; no paid fallback attempted", detail=detail)
    except Exception as exc:
        return availability(slot=slot, target_id=target_id, status="PROVIDER_ERROR", reason=f"{type(exc).__name__}: {exc}")

    try:
        parts = data["candidates"][0]["content"]["parts"]
        text = "".join(part.get("text", "") for part in parts).strip()
        raw = json.loads(text)
        finding = validate_independent(raw, target_id=target_id, family="gemini", model_id=MODEL)
    except Exception as exc:
        return availability(slot=slot, target_id=target_id, status="INVALID_OUTPUT", reason=f"Gemini structured output unusable: {exc}", detail=json.dumps(data)[:1000])

    receipt = {
        "schema": "GardenGeminiMatrixReviewReceipt/v1",
        "provider": "google-gemini-developer-api",
        "model": MODEL,
        "model_version": data.get("modelVersion"),
        "hour_slot": slot,
        "design_epoch": matrix["design_epoch"],
        "canonical_source_root_sha256": matrix["canonical_source_root_sha256"],
        "target_id": target_id,
        "source_trace": trace,
        "usage": data.get("usageMetadata") or {},
        "independent_finding": finding,
        "admission_status": "PROPOSALS_ONLY_NEEDS_PEER_CROSS_EXAMINATION_AND_GSL_INTEGRATOR",
        "semantic_delta_admitted": False,
        "cost_policy": "Expected zero inference charge only while the Google AI Studio project remains on Gemini Free Tier; no search grounding or paid fallback is used."
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"model": MODEL, "target_id": target_id, "disposition": finding.get("disposition"), "usage": receipt["usage"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
