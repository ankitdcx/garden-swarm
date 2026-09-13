#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from tools.matrix_design_review import validate_final, validate_independent
from tools.matrix_repo_review import BUNDLE, OUT_DIR, SELECTION, bounded_repo_pack, build_bundle, load_matrix
from tools.structured_review_provider import call_openrouter_structured


def independent_prompt(target: dict[str, Any], source: str, trace: list[dict[str, Any]], model: dict[str, Any]) -> str:
    return f"""Independent Garden repo reviewer. You have NOT seen peers. Review only this identical public evidence pack and try to falsify it before proposing complexity. Be concise so the JSON completes: every string <=300 chars; arrays <=2 items. If evidence is insufficient use NEEDS_CROSS_REFERENCE.
Return exactly one JSON object with keys: source_anchors(array), current_semantic_claim, falsification_attempts(array), evidence_search_trace(array), proposed_delta, do_nothing_comparison, affected_invariants(array), affected_tests(array), affected_contracts(array), uncertainty, evidence_ancestry, overturn_conditions, disposition. disposition is NO_CHANGE|PROPOSE_DELTA|BLOCKER|NEEDS_CROSS_REFERENCE.
Family={model['family']} role={model['role']} target={target['target_id']} question={target['review_question']}
Trace={json.dumps(trace, ensure_ascii=False)}
--- EVIDENCE ---
{source}
--- END ---"""


def peer_prompt(target: dict[str, Any], source: str, trace: list[dict[str, Any]], own: dict[str, Any], peers: list[dict[str, Any]], model: dict[str, Any]) -> str:
    compact_peers = [
        {k: row.get(k) for k in ("reviewer_family", "current_semantic_claim", "proposed_delta", "disposition", "uncertainty")}
        for row in peers
    ]
    compact_own = {k: own.get(k) for k in ("current_semantic_claim", "falsification_attempts", "proposed_delta", "disposition", "uncertainty")}
    return f"""Garden repo peer cross-examination. Same evidence pack. Do not vote: challenge concrete claims and common evidence ancestry. Be concise: every string <=300 chars; arrays <=2 items.
Return exactly one JSON object with keys: peer_challenges(array), correlated_or_common_source_evidence(array), revised_disposition, revised_delta, do_nothing_comparison, uncertainty, overturn_conditions. revised_disposition is NO_CHANGE|PROPOSE_DELTA|BLOCKER|NEEDS_CROSS_REFERENCE.
Family={model['family']} target={target['target_id']}
Own={json.dumps(compact_own, ensure_ascii=False)}
Peers={json.dumps(compact_peers, ensure_ascii=False)}
Trace={json.dumps(trace, ensure_ascii=False)}
--- EVIDENCE ---
{source}
--- END ---"""


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
    if len(selected) < minimum or len({str(x.get('family')) for x in selected}) != len(selected):
        raise SystemExit("reviewer selection does not satisfy distinct-family minimum")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    attempts: list[dict[str, Any]] = []
    independent: list[dict[str, Any]] = []
    by_family: dict[str, dict[str, Any]] = {}

    for model in selected:
        family = str(model["family"])
        raw, attempt = call_openrouter_structured(model=model, prompt=independent_prompt(target, source, trace, model), max_tokens=6400)
        attempt.update({"phase":"INDEPENDENT", "family":family})
        attempts.append(attempt)
        if raw is None:
            continue
        try:
            finding = validate_independent(raw, target_id=target["target_id"], family=family, model_id=str(model["model"]))
        except Exception as exc:
            attempts.append({"phase":"INDEPENDENT_PARSE","family":family,"model":model["model"],"status":"INVALID_OUTPUT","usage":{"cost":0},"detail":str(exc)})
            continue
        independent.append(finding)
        by_family[family] = finding
        (OUT_DIR / f"independent-{family}.json").write_text(json.dumps(finding, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")

    finals: list[dict[str, Any]] = []
    if len(by_family) >= minimum:
        for model in selected:
            family = str(model["family"])
            own = by_family.get(family)
            if own is None:
                continue
            peers = [row for row in independent if row["reviewer_family"] != family]
            raw, attempt = call_openrouter_structured(model=model, prompt=peer_prompt(target, source, trace, own, peers, model), max_tokens=5200)
            attempt.update({"phase":"CROSS_EXAMINATION", "family":family})
            attempts.append(attempt)
            if raw is None:
                continue
            try:
                final = validate_final(raw, target_id=target["target_id"], family=family, model_id=str(model["model"]))
            except Exception as exc:
                attempts.append({"phase":"CROSS_EXAMINATION_PARSE","family":family,"model":model["model"],"status":"INVALID_OUTPUT","usage":{"cost":0},"detail":str(exc)})
                continue
            finals.append(final)
            (OUT_DIR / f"final-{family}.json").write_text(json.dumps(final, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")

    bundle = build_bundle(matrix=matrix, target=target, day_slot=day_slot, trace=trace, independent=independent, finals=finals, attempts=attempts)
    BUNDLE.parent.mkdir(parents=True, exist_ok=True)
    BUNDLE.write_text(json.dumps(bundle, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
    print(json.dumps({"target_id":target["target_id"],"status":bundle["status"],"independent_families":bundle["independent_reviewer_family_count"],"final_families":bundle["final_disposition_family_count"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
