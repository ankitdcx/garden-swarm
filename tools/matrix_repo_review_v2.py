#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

from tools.gemini_structured_provider import MODEL as GEMINI_MODEL, call_gemini_structured
from tools.matrix_design_review import canonical_hash, validate_final, validate_independent
from tools.matrix_repo_review import BUNDLE, OUT_DIR, SELECTION, bounded_repo_pack, load_matrix
from tools.structured_review_provider import call_openrouter_structured


def independent_prompt(target: dict[str, Any], source: str, trace: list[dict[str, Any]], family: str, role: str) -> str:
    return f"""Independent Garden repo reviewer. You have NOT seen peers. Review only this identical public evidence pack and try to falsify it before proposing complexity. Be concise: every string <=300 chars; arrays <=2 items. If evidence is insufficient use NEEDS_CROSS_REFERENCE.
Return exactly one JSON object with keys: source_anchors(array), current_semantic_claim, falsification_attempts(array), evidence_search_trace(array), proposed_delta, do_nothing_comparison, affected_invariants(array), affected_tests(array), affected_contracts(array), uncertainty, evidence_ancestry, overturn_conditions, disposition. disposition is NO_CHANGE|PROPOSE_DELTA|BLOCKER|NEEDS_CROSS_REFERENCE.
Family={family} role={role} target={target['target_id']} question={target['review_question']}
Trace={json.dumps(trace, ensure_ascii=False)}
--- EVIDENCE ---
{source}
--- END ---"""


def peer_prompt(target: dict[str, Any], source: str, trace: list[dict[str, Any]], own: dict[str, Any], peers: list[dict[str, Any]], family: str) -> str:
    compact_peers = [
        {k: row.get(k) for k in ("reviewer_family", "current_semantic_claim", "proposed_delta", "disposition", "uncertainty")}
        for row in peers
    ]
    compact_own = {k: own.get(k) for k in ("current_semantic_claim", "falsification_attempts", "proposed_delta", "disposition", "uncertainty")}
    return f"""Garden repo peer cross-examination. Same evidence pack. Do not vote: challenge concrete claims and common evidence ancestry. Be concise: every string <=300 chars; arrays <=2 items.
Return exactly one JSON object with keys: peer_challenges(array), correlated_or_common_source_evidence(array), revised_disposition, revised_delta, do_nothing_comparison, uncertainty, overturn_conditions. revised_disposition is NO_CHANGE|PROPOSE_DELTA|BLOCKER|NEEDS_CROSS_REFERENCE.
Family={family} target={target['target_id']}
Own={json.dumps(compact_own, ensure_ascii=False)}
Peers={json.dumps(compact_peers, ensure_ascii=False)}
Trace={json.dumps(trace, ensure_ascii=False)}
--- EVIDENCE ---
{source}
--- END ---"""


def build_multi_provider_bundle(*, matrix: dict[str, Any], target: dict[str, Any], day_slot: int, trace: list[dict[str, Any]], independent: list[dict[str, Any]], finals: list[dict[str, Any]], attempts: list[dict[str, Any]]) -> dict[str, Any]:
    minimum = int(matrix["minimum_independent_reviewer_families"])
    preferred = int(matrix.get("preferred_independent_reviewer_families", minimum))
    independent_families = sorted({row["reviewer_family"] for row in independent})
    final_families = sorted({row["reviewer_family"] for row in finals})
    openrouter_called = [a for a in attempts if a.get("provider") == "openrouter" and a.get("status") == "CALLED"]
    openrouter_zero = all((a.get("usage") or {}).get("cost") in (0, 0.0) for a in openrouter_called)
    if len(independent_families) < minimum:
        status = "INSUFFICIENT_INDEPENDENT_REVIEW"
    elif len(final_families) < minimum:
        status = "INSUFFICIENT_PEER_CROSS_EXAMINATION"
    elif not openrouter_zero:
        status = "COST_VERIFICATION_FAILED"
    else:
        status = "REVIEW_COMPLETE_NEEDS_GSL_INTEGRATOR"
    payload = {
        "schema":"GardenRepoDesignReviewBundle/v2",
        "created_at_unix":int(time.time()),
        "day_slot":day_slot,
        "design_epoch":matrix["design_epoch"],
        "canonical_source_root_sha256":matrix["canonical_source_root_sha256"],
        "target":target,
        "source_trace":trace,
        "minimum_independent_reviewer_families":minimum,
        "preferred_independent_reviewer_families":preferred,
        "independent_reviewer_family_count":len(independent_families),
        "final_disposition_family_count":len(final_families),
        "independent_reviewer_families":independent_families,
        "final_disposition_families":final_families,
        "openrouter_zero_cost_verified":openrouter_zero,
        "direct_provider_cost_boundary":"Gemini is admitted as a distinct reviewer only under the configured free-tier/no-paid-fallback lane; its Developer API response does not expose a dollar-cost field.",
        "provider_attempts":attempts,
        "independent_findings":independent,
        "final_dispositions":finals,
        "status":status,
        "semantic_delta_admitted":False,
        "admission_boundary":"Completed multi-provider quorum is proposal evidence only. Whole-repo cross-reference and applicable GSL Compare/Reason/Proof/Evidence, AAP, authority, RepoChangeEnvelope/ActionGate and CI remain downstream.",
    }
    payload["bundle_sha256"] = canonical_hash({k:v for k,v in payload.items() if k != "bundle_sha256"})
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--slot", type=int)
    args = parser.parse_args()
    root = Path(".").resolve()
    matrix, target, day_slot = load_matrix(root, args.slot)
    source, trace = bounded_repo_pack(root, target)
    selection = json.loads((root / SELECTION).read_text(encoding="utf-8"))
    selected = list(selection.get("selected") or [])
    minimum = int(matrix["minimum_independent_reviewer_families"])
    preferred = int(matrix.get("preferred_independent_reviewer_families", minimum))
    if len(selected) < minimum - 1 or len({str(x.get('family')) for x in selected}) != len(selected):
        raise SystemExit("reviewer selection does not provide enough distinct OpenRouter backup families")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    attempts: list[dict[str, Any]] = []
    independent: list[dict[str, Any]] = []
    by_family: dict[str, dict[str, Any]] = {}
    model_by_family: dict[str, dict[str, Any]] = {}

    # Blind round: direct Gemini first, still without any peer material.
    raw, attempt = call_gemini_structured(prompt=independent_prompt(target, source, trace, "gemini", "independent_lab_reviewer"), phase="INDEPENDENT", max_tokens=3600)
    attempt.update({"phase":"INDEPENDENT","family":"gemini","provider":"gemini"})
    attempts.append(attempt)
    if raw is not None:
        try:
            finding = validate_independent(raw, target_id=target["target_id"], family="gemini", model_id=GEMINI_MODEL)
            independent.append(finding); by_family["gemini"] = finding
            (OUT_DIR / "independent-gemini.json").write_text(json.dumps(finding, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
        except Exception as exc:
            attempts.append({"phase":"INDEPENDENT_PARSE","family":"gemini","provider":"gemini","model":GEMINI_MODEL,"status":"INVALID_OUTPUT","detail":str(exc)})

    # Continue blind OpenRouter reviewers until preferred valid diversity is reached or pool is exhausted.
    for model in selected:
        if len(by_family) >= preferred:
            break
        family = str(model["family"])
        raw, attempt = call_openrouter_structured(model=model, prompt=independent_prompt(target, source, trace, family, str(model["role"])), max_tokens=5200)
        attempt.update({"phase":"INDEPENDENT","family":family,"provider":"openrouter"})
        attempts.append(attempt)
        if raw is None:
            continue
        try:
            finding = validate_independent(raw, target_id=target["target_id"], family=family, model_id=str(model["model"]))
        except Exception as exc:
            attempts.append({"phase":"INDEPENDENT_PARSE","family":family,"provider":"openrouter","model":model["model"],"status":"INVALID_OUTPUT","usage":{"cost":0},"detail":str(exc)})
            continue
        independent.append(finding); by_family[family] = finding; model_by_family[family] = model
        (OUT_DIR / f"independent-{family}.json").write_text(json.dumps(finding, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")

    finals: list[dict[str, Any]] = []
    if len(by_family) >= minimum:
        # No cross-examination began until the complete blind round above ended.
        for family, own in list(by_family.items()):
            peers = [row for row in independent if row["reviewer_family"] != family]
            if family == "gemini":
                raw, attempt = call_gemini_structured(prompt=peer_prompt(target, source, trace, own, peers, family), phase="CROSS_EXAMINATION", max_tokens=2600)
                attempt.update({"phase":"CROSS_EXAMINATION","family":family,"provider":"gemini"})
                model_id = GEMINI_MODEL
            else:
                model = model_by_family[family]
                raw, attempt = call_openrouter_structured(model=model, prompt=peer_prompt(target, source, trace, own, peers, family), max_tokens=4200)
                attempt.update({"phase":"CROSS_EXAMINATION","family":family,"provider":"openrouter"})
                model_id = str(model["model"])
            attempts.append(attempt)
            if raw is None:
                continue
            try:
                final = validate_final(raw, target_id=target["target_id"], family=family, model_id=model_id)
            except Exception as exc:
                attempts.append({"phase":"CROSS_EXAMINATION_PARSE","family":family,"provider":attempt.get("provider"),"model":model_id,"status":"INVALID_OUTPUT","detail":str(exc)})
                continue
            finals.append(final)
            (OUT_DIR / f"final-{family}.json").write_text(json.dumps(final, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")

    bundle = build_multi_provider_bundle(matrix=matrix, target=target, day_slot=day_slot, trace=trace, independent=independent, finals=finals, attempts=attempts)
    BUNDLE.parent.mkdir(parents=True, exist_ok=True)
    BUNDLE.write_text(json.dumps(bundle, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
    print(json.dumps({"target_id":target["target_id"],"status":bundle["status"],"independent_families":bundle["independent_reviewer_family_count"],"final_families":bundle["final_disposition_family_count"],"families":bundle["independent_reviewer_families"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
