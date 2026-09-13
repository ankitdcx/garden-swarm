#!/usr/bin/env python3
"""Review one bounded public repository-design target with 3-4 independent families.

Round 1 is blind. Round 2 is peer cross-examination. The output is proposal-only
and cannot admit a repository change, semantic delta, constitutional change, or
canonical Garden promotion.
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

from tools.matrix_design_review import (
    call_openrouter,
    canonical_hash,
    validate_final,
    validate_independent,
)

MATRIX = Path("agents/repo-review-matrix.json")
SELECTION = Path("agents/runtime/free-selection.json")
OUT_DIR = Path("agents/outbox/daily/repo-matrix-review")
BUNDLE = Path("agents/outbox/daily/repo-review-bundle.json")
PER_FILE_LIMIT = 12000
TOTAL_LIMIT = 52000


def load_matrix(root: Path, slot: int | None = None) -> tuple[dict[str, Any], dict[str, Any], int]:
    matrix = json.loads((root / MATRIX).read_text(encoding="utf-8"))
    if matrix.get("schema") != "GardenRepoDesignReviewMatrix/v1":
        raise ValueError("unsupported repository review matrix schema")
    if matrix.get("semantic_compliance_proved") is not False:
        raise ValueError("repository review matrix may not self-claim semantic compliance")
    minimum = int(matrix.get("minimum_independent_reviewer_families", 0))
    if minimum < 3:
        raise ValueError("repository review matrix may not require fewer than 3 independent families")
    targets = list(matrix.get("targets") or [])
    if not targets:
        raise ValueError("repository review matrix has no targets")
    resolved_slot = slot if slot is not None else int(time.time() // 86400)
    index = resolved_slot % len(targets)
    target = targets[index]
    if target.get("public_only") is not True:
        raise ValueError("non-public repository target refused by public free-review bus")
    return matrix, target, resolved_slot


def bounded_repo_pack(root: Path, target: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    chunks: list[str] = []
    trace: list[dict[str, Any]] = []
    remaining = TOTAL_LIMIT
    for rel in target.get("files") or []:
        path = (root / str(rel)).resolve()
        if root.resolve() not in path.parents:
            raise ValueError(f"repository target escapes root: {rel}")
        if not path.is_file():
            raise ValueError(f"repository target file missing: {rel}")
        raw = path.read_bytes()
        text = raw.decode("utf-8", errors="replace")
        take = min(PER_FILE_LIMIT, remaining)
        if take <= 0:
            break
        if len(text) <= take:
            excerpt = text
            coverage = "FULL"
        else:
            front = max(1, take * 2 // 3)
            back = max(1, take - front)
            excerpt = text[:front] + "\n...[bounded middle omitted]...\n" + text[-back:]
            coverage = "BOUNDED_HEAD_TAIL"
        remaining -= len(excerpt)
        chunks.append(f"\n--- {rel} sha256={hashlib.sha256(raw).hexdigest()} ---\n{excerpt}")
        trace.append({
            "source": str(rel),
            "source_sha256": hashlib.sha256(raw).hexdigest(),
            "coverage": coverage,
            "chars_supplied": len(excerpt),
        })
    if not chunks:
        raise ValueError("repository review target produced no evidence pack")
    return "".join(chunks), trace


def independent_prompt(target: dict[str, Any], source: str, trace: list[dict[str, Any]], model: dict[str, Any]) -> str:
    return f"""You are an independent Garden repository-design reviewer. You have not seen any peer conclusion.
Reviewer family: {model['family']}; posture: {model['role']}.
Analyze ONLY the identical already-public bounded repository evidence supplied below. Try to falsify the architecture/governance before proposing complexity. Distinguish implementation defect, repository-design defect, missing evidence, optional enhancement, and bounded-coverage limitation. Compare every proposed change with DO_NOTHING. Agreement is not proof; repeated or model-derived claims with common ancestry are not independent evidence.

Return ONE JSON object only with required fields:
source_anchors (non-empty array; use exact supplied file paths and/or exact snippets), current_semantic_claim (string), falsification_attempts (non-empty array), evidence_search_trace (non-empty array), proposed_delta (string; NO_CHANGE if none), do_nothing_comparison (string), affected_invariants (array), affected_tests (array), affected_contracts (array), uncertainty (string), evidence_ancestry (string), overturn_conditions (string), disposition (NO_CHANGE|PROPOSE_DELTA|BLOCKER|NEEDS_CROSS_REFERENCE).

Target ID: {target['target_id']}
Review question: {target['review_question']}
Supplied trace: {json.dumps(trace, ensure_ascii=False)}
--- BEGIN IDENTICAL PUBLIC REPOSITORY EVIDENCE ---
{source}
--- END IDENTICAL PUBLIC REPOSITORY EVIDENCE ---"""


def peer_prompt(target: dict[str, Any], source: str, trace: list[dict[str, Any]], own: dict[str, Any], peers: list[dict[str, Any]], model: dict[str, Any]) -> str:
    return f"""You are reviewer family {model['family']} in round 2 of a Garden repository-design quorum. You now see the blind round-1 findings on the SAME evidence pack. Challenge concrete peer claims; do not vote or average. Identify correlated/common-source evidence and revise your own conclusion if a counterexample survives. Agreement remains evidence, never proof or authorization.

Return ONE JSON object only with fields: peer_challenges (array), correlated_or_common_source_evidence (array), revised_disposition (NO_CHANGE|PROPOSE_DELTA|BLOCKER|NEEDS_CROSS_REFERENCE), revised_delta (string; NO_CHANGE when none), do_nothing_comparison (string), uncertainty (string), overturn_conditions (string).

Target ID: {target['target_id']}
Review question: {target['review_question']}
Supplied trace: {json.dumps(trace, ensure_ascii=False)}
Your blind finding: {json.dumps(own, ensure_ascii=False)}
Peer blind findings: {json.dumps(peers, ensure_ascii=False)}
--- BEGIN IDENTICAL PUBLIC REPOSITORY EVIDENCE ---
{source}
--- END IDENTICAL PUBLIC REPOSITORY EVIDENCE ---"""


def build_bundle(*, matrix: dict[str, Any], target: dict[str, Any], day_slot: int, trace: list[dict[str, Any]], independent: list[dict[str, Any]], finals: list[dict[str, Any]], attempts: list[dict[str, Any]]) -> dict[str, Any]:
    minimum = int(matrix["minimum_independent_reviewer_families"])
    independent_families = sorted({row["reviewer_family"] for row in independent})
    final_families = sorted({row["reviewer_family"] for row in finals})
    called = [a for a in attempts if a.get("status") == "CALLED"]
    explicit_zero = bool(called) and all((a.get("usage") or {}).get("cost") in (0, 0.0) for a in called)
    if len(independent_families) < minimum:
        status = "INSUFFICIENT_INDEPENDENT_REVIEW"
    elif len(final_families) < minimum:
        status = "INSUFFICIENT_PEER_CROSS_EXAMINATION"
    elif not explicit_zero:
        status = "COST_VERIFICATION_FAILED"
    else:
        status = "REVIEW_COMPLETE_NEEDS_GSL_INTEGRATOR"
    payload = {
        "schema": "GardenRepoDesignReviewBundle/v1",
        "created_at_unix": int(time.time()),
        "day_slot": day_slot,
        "design_epoch": matrix["design_epoch"],
        "canonical_source_root_sha256": matrix["canonical_source_root_sha256"],
        "target": target,
        "source_trace": trace,
        "minimum_independent_reviewer_families": minimum,
        "preferred_independent_reviewer_families": int(matrix.get("preferred_independent_reviewer_families", minimum)),
        "independent_reviewer_family_count": len(independent_families),
        "final_disposition_family_count": len(final_families),
        "independent_reviewer_families": independent_families,
        "final_disposition_families": final_families,
        "zero_cost_verified": explicit_zero,
        "provider_attempts": attempts,
        "independent_findings": independent,
        "final_dispositions": finals,
        "status": status,
        "semantic_delta_admitted": False,
        "admission_boundary": "Even completed quorum evidence cannot update repo design/code. Whole-repo cross-reference and applicable GSL Compare/Reason/Proof/Evidence, AAP, authority, RepoChangeEnvelope/ActionGate and CI remain downstream.",
    }
    payload["bundle_sha256"] = canonical_hash({k: v for k, v in payload.items() if k != "bundle_sha256"})
    return payload


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--slot", type=int, help="deterministic day slot override; slot 0 is the bootstrap/self-review target")
    args = parser.parse_args()

    root = Path(".").resolve()
    matrix, target, day_slot = load_matrix(root, args.slot)
    source, trace = bounded_repo_pack(root, target)
    selection = json.loads((root / SELECTION).read_text(encoding="utf-8"))
    selected = list(selection.get("selected") or [])
    minimum = int(matrix["minimum_independent_reviewer_families"])
    if len(selected) < minimum:
        raise SystemExit(f"free-model selection has {len(selected)} families; repo matrix requires {minimum}")
    families = [str(row.get("family")) for row in selected]
    if len(set(families)) != len(families):
        raise SystemExit("repository reviewer selection contains duplicate families")
    if not all(str(row.get("model", "")).endswith(":free") for row in selected):
        raise SystemExit("non-free repository reviewer route refused")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    attempts: list[dict[str, Any]] = []
    independent: list[dict[str, Any]] = []
    independent_by_family: dict[str, dict[str, Any]] = {}

    for model in selected:
        family = str(model["family"])
        raw, attempt = call_openrouter(model=model, prompt=independent_prompt(target, source, trace, model))
        attempt.update({"phase": "INDEPENDENT", "family": family})
        attempts.append(attempt)
        if raw is None:
            continue
        try:
            finding = validate_independent(raw, target_id=target["target_id"], family=family, model_id=str(model["model"]))
        except Exception as exc:
            attempts.append({"phase":"INDEPENDENT_PARSE","family":family,"model":model["model"],"status":"INVALID_OUTPUT","usage":{"cost":0},"detail":str(exc)})
            continue
        independent.append(finding)
        independent_by_family[family] = finding
        (OUT_DIR / f"independent-{family}.json").write_text(json.dumps(finding, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    finals: list[dict[str, Any]] = []
    if len(independent_by_family) >= minimum:
        for model in selected:
            family = str(model["family"])
            own = independent_by_family.get(family)
            if own is None:
                continue
            peers = [row for row in independent if row["reviewer_family"] != family]
            raw, attempt = call_openrouter(model=model, prompt=peer_prompt(target, source, trace, own, peers, model), max_tokens=3200)
            attempt.update({"phase": "CROSS_EXAMINATION", "family": family})
            attempts.append(attempt)
            if raw is None:
                continue
            try:
                final = validate_final(raw, target_id=target["target_id"], family=family, model_id=str(model["model"]))
            except Exception as exc:
                attempts.append({"phase":"CROSS_EXAMINATION_PARSE","family":family,"model":model["model"],"status":"INVALID_OUTPUT","usage":{"cost":0},"detail":str(exc)})
                continue
            finals.append(final)
            (OUT_DIR / f"final-{family}.json").write_text(json.dumps(final, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    bundle = build_bundle(matrix=matrix, target=target, day_slot=day_slot, trace=trace, independent=independent, finals=finals, attempts=attempts)
    BUNDLE.parent.mkdir(parents=True, exist_ok=True)
    BUNDLE.write_text(json.dumps(bundle, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "target_id": target["target_id"],
        "day_slot": day_slot,
        "status": bundle["status"],
        "independent_families": bundle["independent_reviewer_family_count"],
        "final_families": bundle["final_disposition_family_count"],
        "semantic_delta_admitted": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
