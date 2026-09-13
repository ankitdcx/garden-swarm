#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any
from urllib import error, request

from tools.matrix_design_review import extract_target, load_matrix, validate_final, validate_independent

MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
BASE = "https://generativelanguage.googleapis.com/v1beta/models"
BLIND_OUT = Path("agents/outbox/hourly/gemini-independent.json")
FINAL_OUT = Path("agents/outbox/hourly/gemini-final.json")
OPENROUTER_BUNDLE = Path("agents/outbox/hourly/design-review-bundle.json")


def availability(phase: str, reason: str) -> dict[str, Any]:
    return {"schema":"GardenGeminiMatrixAvailabilityReceipt/v1","provider":"google-gemini-developer-api","model":MODEL,"phase":phase,"status":"UNAVAILABLE","reason":reason,"semantic_delta_admitted":False}


def call_gemini(prompt: str, *, phase: str, max_tokens: int) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        return None, availability(phase, "GEMINI_API_KEY not configured")
    endpoint = f"{BASE}/{MODEL}:generateContent"
    body = {
        "contents":[{"role":"user","parts":[{"text":prompt}]}],
        "generationConfig":{"temperature":0.05,"maxOutputTokens":max_tokens,"responseMimeType":"application/json"},
    }
    req = request.Request(endpoint, method="POST", data=json.dumps(body).encode("utf-8"), headers={"Content-Type":"application/json","x-goog-api-key":key})
    try:
        with request.urlopen(req, timeout=360) as response:
            data = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:1200]
        return None, availability(phase, f"Gemini HTTP {exc.code}: {detail}")
    except Exception as exc:
        return None, availability(phase, f"{type(exc).__name__}: {exc}")
    try:
        content = "".join(part.get("text", "") for part in data["candidates"][0]["content"]["parts"]).strip()
        value = json.loads(content)
        if not isinstance(value, dict):
            raise ValueError("output is not object")
    except Exception as exc:
        return None, {**availability(phase, f"invalid structured output: {exc}"), "raw_excerpt": str(data)[:1000]}
    return value, {"schema":"GardenGeminiProviderReceipt/v1","provider":"google-gemini-developer-api","model":MODEL,"model_version":data.get("modelVersion"),"phase":phase,"status":"CALLED","usage":data.get("usageMetadata") or {},"cost_policy":"Free-tier project expected; no paid fallback/search grounding. Provider response does not expose a dollar-cost field, so this receipt does not claim metered-cost proof.","semantic_delta_admitted":False}


def blind_prompt(target: dict[str, Any], source: str, trace: dict[str, Any]) -> str:
    return f"""Independent Gemini Garden reviewer. Do not use peer conclusions. Review only this bounded public target; falsify before adding complexity. Concise JSON only: strings <=300 chars, arrays <=2. Keys: source_anchors,current_semantic_claim,falsification_attempts,evidence_search_trace,proposed_delta,do_nothing_comparison,affected_invariants,affected_tests,affected_contracts,uncertainty,evidence_ancestry,overturn_conditions,disposition. disposition=NO_CHANGE|PROPOSE_DELTA|BLOCKER|NEEDS_CROSS_REFERENCE.
Target={target['target_id']} Question={target['review_question']} Trace={json.dumps(trace, ensure_ascii=False)}
--- TARGET ---
{source}
--- END ---"""


def final_prompt(target: dict[str, Any], own: dict[str, Any], peers: list[dict[str, Any]]) -> str:
    compact = [{k:r.get(k) for k in ("reviewer_family","current_semantic_claim","proposed_delta","disposition","uncertainty")} for r in peers]
    return f"""Gemini round-2 cross-examination for the SAME Garden target. Challenge peers; do not vote. Concise JSON only with keys peer_challenges,correlated_or_common_source_evidence,revised_disposition,revised_delta,do_nothing_comparison,uncertainty,overturn_conditions. revised_disposition=NO_CHANGE|PROPOSE_DELTA|BLOCKER|NEEDS_CROSS_REFERENCE.
Target={target['target_id']} Own={json.dumps(own, ensure_ascii=False)} Peers={json.dumps(compact, ensure_ascii=False)}"""


def write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("independent","final"), required=True)
    args = parser.parse_args()
    root = Path(".").resolve()
    matrix, target = load_matrix(root)
    source, trace = extract_target(root, target)
    if args.phase == "independent":
        raw, provider = call_gemini(blind_prompt(target, source, trace), phase="INDEPENDENT", max_tokens=3200)
        if raw is None:
            write(BLIND_OUT, provider); return 0
        try:
            finding = validate_independent(raw, target_id=target["target_id"], family="gemini", model_id=MODEL)
        except Exception as exc:
            write(BLIND_OUT, {**provider,"status":"INVALID_OUTPUT","detail":str(exc)}); return 0
        write(BLIND_OUT, {"schema":"GardenGeminiIndependentReviewReceipt/v1","target_id":target["target_id"],"design_epoch":matrix["design_epoch"],"source_root":matrix["canonical_source_root_sha256"],"source_trace":trace,"provider_receipt":provider,"finding":finding,"semantic_delta_admitted":False}); return 0
    if not BLIND_OUT.is_file() or not OPENROUTER_BUNDLE.is_file():
        write(FINAL_OUT, availability("CROSS_EXAMINATION", "blind Gemini receipt or peer bundle missing")); return 0
    blind = json.loads(BLIND_OUT.read_text(encoding="utf-8")); own = blind.get("finding")
    bundle = json.loads(OPENROUTER_BUNDLE.read_text(encoding="utf-8"))
    if not isinstance(own, dict) or blind.get("target_id") != bundle.get("target",{}).get("target_id"):
        write(FINAL_OUT, availability("CROSS_EXAMINATION", "blind Gemini receipt missing or target-mismatched")); return 0
    raw, provider = call_gemini(final_prompt(target, own, list(bundle.get("independent_findings") or [])), phase="CROSS_EXAMINATION", max_tokens=2200)
    if raw is None:
        write(FINAL_OUT, provider); return 0
    try:
        final = validate_final(raw, target_id=target["target_id"], family="gemini", model_id=MODEL)
    except Exception as exc:
        write(FINAL_OUT, {**provider,"status":"INVALID_OUTPUT","detail":str(exc)}); return 0
    write(FINAL_OUT, {"schema":"GardenGeminiFinalReviewReceipt/v1","target_id":target["target_id"],"design_epoch":matrix["design_epoch"],"source_root":matrix["canonical_source_root_sha256"],"provider_receipt":provider,"disposition":final,"semantic_delta_admitted":False}); return 0


if __name__ == "__main__":
    raise SystemExit(main())
