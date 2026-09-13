#!/usr/bin/env python3
"""Run a fail-closed three-family Garden review quorum on one shared target.

Round 1 is blind/independent. Round 2 gives the same reviewers the peer findings
for adversarial cross-examination. Outputs are proposal-only evidence; this tool
has no write, merge, deployment, constitutional, or canonical-promotion authority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from pathlib import Path
from urllib import error, request

from tools.free_model_rotation import catalog, choose

CHAT = "https://openrouter.ai/api/v1/chat/completions"
SOURCE_ROOT = "63561ce9fcd4a72f44af333662b342fd18c4e99930209c30c5f801bcc5c74598"
MIN_INDEPENDENT_FAMILIES = 3
MAX_REVIEWERS = 3


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def bounded_excerpt(text: str, anchors: list[str], *, per_anchor: int = 5500, max_total: int = 22000) -> str:
    if not anchors:
        return text[:max_total]
    lower = text.lower()
    excerpts: list[str] = []
    for anchor in anchors:
        start = lower.find(anchor.lower())
        if start < 0:
            continue
        lo = max(0, start - per_anchor // 3)
        hi = min(len(text), lo + per_anchor)
        excerpts.append(text[lo:hi])
        if sum(len(x) for x in excerpts) >= max_total:
            break
    if not excerpts:
        return text[: min(max_total, 8000)]
    return "\n\n...[target-bounded]...\n\n".join(excerpts)[:max_total]


def load_target(root: Path, lane: str, slot: int) -> tuple[dict, str, list[dict]]:
    matrix_path = root / ("agents/matrices/design-review-matrix.json" if lane == "design" else "agents/matrices/repo-review-matrix.json")
    matrix = json.loads(matrix_path.read_text(encoding="utf-8"))
    targets = matrix.get("targets") or []
    if not targets:
        raise RuntimeError("review matrix has no targets")
    target = targets[slot % len(targets)]
    anchors = [str(x) for x in target.get("anchors") or []]
    sections: list[str] = []
    trace: list[dict] = []
    for rel in target.get("files") or []:
        path = root / rel
        if not path.is_file():
            trace.append({"source": rel, "coverage": "MISSING", "query_or_scope": "declared target file missing"})
            continue
        raw = path.read_bytes()
        text = raw.decode("utf-8", errors="replace")
        excerpt = bounded_excerpt(text, anchors) if lane == "design" else text[:18000]
        sections.append(f"\n--- {rel} sha256={sha256_bytes(raw)} ---\n{excerpt}")
        trace.append({
            "source": rel,
            "coverage": "ANCHOR_BOUNDED" if lane == "design" else ("FULL" if len(text) <= 18000 else "PREFIX_BOUNDED"),
            "query_or_scope": f"target={target['target_id']}; anchors={anchors}; sha256={sha256_bytes(raw)}",
        })
    if not sections:
        raise RuntimeError(f"no source material available for target {target['target_id']}")
    evidence = "".join(sections)
    target_hash = sha256_bytes((json.dumps(target, sort_keys=True) + evidence).encode("utf-8"))
    resolved = dict(target)
    resolved["target_hash"] = target_hash
    resolved["matrix_path"] = matrix_path.relative_to(root).as_posix()
    return resolved, evidence, trace


def call_openrouter(model: dict, prompt: str, *, max_tokens: int) -> tuple[dict | None, dict, str | None]:
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        return None, {}, "OPENROUTER_API_KEY_MISSING"
    model_id = str(model["model"])
    if not model_id.endswith(":free"):
        return None, {}, f"NON_FREE_ROUTE_REFUSED:{model_id}"
    payload = {
        "model": model_id,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.12,
        "max_tokens": max_tokens,
        "provider": {"allow_fallbacks": True},
    }
    req = request.Request(
        CHAT,
        method="POST",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/ankitdcx/garden-swarm",
            "X-Title": "Garden Three-Family Review Quorum",
        },
    )
    try:
        with request.urlopen(req, timeout=300) as response:
            data = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:1000]
        return None, {}, f"HTTP_{exc.code}:{detail}"
    except Exception as exc:
        return None, {}, f"{type(exc).__name__}:{exc}"
    usage = data.get("usage") or {}
    if usage.get("cost") not in (None, 0, 0.0):
        return None, usage, f"NONZERO_COST_REFUSED:{usage.get('cost')}"
    raw = str(data.get("choices", [{}])[0].get("message", {}).get("content", "")).strip()
    if raw.startswith("```"):
        lines = raw.splitlines()[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        raw = "\n".join(lines).strip()
    try:
        value = json.loads(raw)
    except Exception as exc:
        return None, usage, f"INVALID_JSON:{exc};excerpt={raw[:500]}"
    if not isinstance(value, dict):
        return None, usage, "OUTPUT_NOT_OBJECT"
    return value, usage, None


def independent_prompt(lane: str, target: dict, evidence: str, trace: list[dict], model: dict) -> str:
    return f"""You are one independent reviewer in a Garden review quorum. You MUST reason independently; you have not been shown any peer conclusion. Review exactly the same bounded target as the other reviewers.

Garden source root: {SOURCE_ROOT}
Lane: {lane}
Target: {json.dumps(target, sort_keys=True)}
Reviewer family: {model['family']}; posture: {model['role']}
Supplied trace: {json.dumps(trace)}

Try to falsify the current design before proposing complexity. Distinguish SOURCE-DESIGN defect, implementation gap, missing evidence, optional enhancement, and bounded-coverage limitation. Never infer absence from material outside this evidence pack. Compare any proposal against DO_NOTHING. Identify likely common evidence ancestry; synthetic repetition is not independent corroboration. Return ONE JSON object only with fields:
schema='GardenDesignFinding/v1', status=NO_CHANGE|PROPOSED|BLOCKER|NEEDS_CROSS_REFERENCE, target_id, current_claim, falsification_attempt, claim, evidence_or_failure, severity=INFO|LOW|MEDIUM|HIGH|CRITICAL, affected_invariant, proposed_fix, do_nothing_compare, test, uncertainty, evidence_ancestry, what_would_overturn, search_trace.

--- BEGIN IDENTICAL EVIDENCE PACK ---
{evidence}
--- END IDENTICAL EVIDENCE PACK ---"""


def cross_exam_prompt(lane: str, target: dict, evidence: str, trace: list[dict], model: dict, findings: list[dict]) -> str:
    peer_payload = [
        {"reviewer_family": row["model"]["family"], "reviewer_model": row["model"]["model"], "finding": row["finding"]}
        for row in findings
    ]
    return f"""You are returning for round 2 of a Garden review quorum. Re-evaluate the SAME target after seeing all blind round-1 findings. Challenge peers rather than voting. A valid counterexample can defeat majority agreement. Detect common evidence ancestry and correlated model reasoning. Consensus is evidence, not proof.

Garden source root: {SOURCE_ROOT}
Lane: {lane}
Target: {json.dumps(target, sort_keys=True)}
Your family: {model['family']}; posture: {model['role']}
Supplied trace: {json.dumps(trace)}
Round-1 findings: {json.dumps(peer_payload, ensure_ascii=False)}

Return ONE JSON object only with fields: schema='GardenPeerCrossExamination/v1', target_id, final_disposition=NO_CHANGE|ACCEPT_PROPOSAL|REJECT_PROPOSAL|NEEDS_MORE_EVIDENCE|BLOCKER, surviving_claim, peer_challenges, evidence_independence, recommended_delta, do_nothing_compare, required_tests, uncertainty, what_would_overturn. Do not claim authorization, canonical promotion, proof, or implementation.

--- BEGIN IDENTICAL EVIDENCE PACK ---
{evidence}
--- END IDENTICAL EVIDENCE PACK ---"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lane", choices=("design", "repo"), default="design")
    parser.add_argument("--slot", type=int)
    parser.add_argument("--output", default="agents/outbox/quorum/review-quorum.json")
    parser.add_argument("--repo-root", default=".")
    args = parser.parse_args()

    root = Path(args.repo_root).resolve()
    slot = args.slot if args.slot is not None else int(time.time() // 3600)
    target, evidence, trace = load_target(root, args.lane, slot)
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise SystemExit("OPENROUTER_API_KEY required")
    selected = choose(catalog(key), slot, count=MAX_REVIEWERS)

    initial: list[dict] = []
    availability: list[dict] = []
    for model in selected:
        finding, usage, failure = call_openrouter(model, independent_prompt(args.lane, target, evidence, trace, model), max_tokens=2600)
        if failure or not finding:
            availability.append({"model": model, "round": "INDEPENDENT", "status": "UNAVAILABLE_OR_INVALID", "reason": failure, "usage": usage})
            continue
        finding.setdefault("schema", "GardenDesignFinding/v1")
        finding["target_id"] = target["target_id"]
        initial.append({"model": model, "usage": usage, "finding": finding})

    final: list[dict] = []
    if len({row["model"]["family"] for row in initial}) >= MIN_INDEPENDENT_FAMILIES:
        for row in initial:
            model = row["model"]
            result, usage, failure = call_openrouter(model, cross_exam_prompt(args.lane, target, evidence, trace, model, initial), max_tokens=2200)
            if failure or not result:
                availability.append({"model": model, "round": "CROSS_EXAMINATION", "status": "UNAVAILABLE_OR_INVALID", "reason": failure, "usage": usage})
                continue
            result.setdefault("schema", "GardenPeerCrossExamination/v1")
            result["target_id"] = target["target_id"]
            final.append({"model": model, "usage": usage, "disposition": result})

    independent_families = sorted({row["model"]["family"] for row in initial})
    final_families = sorted({row["model"]["family"] for row in final})
    quorum_pass = len(independent_families) >= MIN_INDEPENDENT_FAMILIES and len(final_families) >= MIN_INDEPENDENT_FAMILIES
    receipt = {
        "schema": "GardenReviewQuorumReceipt/v1",
        "lane": args.lane,
        "hour_slot": slot,
        "source_root_sha256": SOURCE_ROOT,
        "target": target,
        "source_trace": trace,
        "review_requirement": {"minimum_independent_families": MIN_INDEPENDENT_FAMILIES, "blind_first_round": True, "peer_cross_examination_required": True},
        "independent_reviews": initial,
        "cross_examinations": final,
        "availability": availability,
        "independent_families": independent_families,
        "final_families": final_families,
        "quorum_status": "PASS" if quorum_pass else "INSUFFICIENT_INDEPENDENT_REVIEW",
        "admission_status": "REVIEW_QUORUM_ONLY_NEEDS_WHOLE_SOURCE_GSL_ADMISSION" if quorum_pass else "NOT_ADMISSIBLE",
        "authority_boundary": "Reviewers and this tool have proposal-only authority. The receipt cannot modify Garden, repositories, rights, authority, constitution, DesignEpoch acceptance, or canonical status."
    }
    out = root / args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"lane": args.lane, "target": target["target_id"], "quorum_status": receipt["quorum_status"], "independent_families": independent_families, "final_families": final_families}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
