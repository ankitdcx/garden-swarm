#!/usr/bin/env python3
"""Run a bounded OpenRouter review subset without weakening Garden admission quorum.

This adapter exists because the hourly workflow may intentionally execute fewer
OpenRouter calls than the Design Review Matrix admission minimum in order to stay
inside the zero-cost quota budget. The underlying matrix contract remains
unchanged: fewer than the matrix minimum can only produce proposal evidence and
must remain INSUFFICIENT_INDEPENDENT_REVIEW.
"""
from __future__ import annotations

import json
from pathlib import Path

from tools import matrix_design_review as review


def main() -> int:
    root = Path(".").resolve()
    matrix, target = review.load_matrix(root)
    source, trace = review.extract_target(root, target)
    selection = json.loads((root / review.SELECTION).read_text(encoding="utf-8"))
    selected = list(selection.get("selected") or [])
    minimum = int(matrix["minimum_independent_reviewer_families"])

    if not selected:
        raise SystemExit("execution-budget selection must contain at least one reviewer family")

    families = [str(model.get("family")) for model in selected]
    if len(set(families)) != len(families):
        raise SystemExit("execution-budget selection contains duplicate families")
    if not all(str(model.get("model", "")).endswith(":free") for model in selected):
        raise SystemExit("non-free OpenRouter route refused")

    # When the execution set itself reaches the admission minimum, preserve the
    # canonical matrix runner unchanged, including peer cross-examination.
    if len(selected) >= minimum:
        return review.main()

    review.OUT_DIR.mkdir(parents=True, exist_ok=True)
    attempts: list[dict] = []
    independent: list[dict] = []

    # Blind findings only. With fewer than the admission minimum, no peer phase
    # may start and no semantic admission can occur.
    for model in selected:
        family = str(model["family"])
        raw, attempt = review.call_openrouter(
            model=model,
            prompt=review.independent_prompt(
                target=target,
                source=source,
                trace=trace,
                model=model,
            ),
        )
        attempt.update({"phase": "INDEPENDENT", "family": family})
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
                "family": family,
                "model": model["model"],
                "status": "INVALID_OUTPUT",
                "cost": 0,
                "detail": str(exc),
            })
            continue
        independent.append(finding)
        (review.OUT_DIR / f"{family}-independent.json").write_text(
            json.dumps(finding, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    bundle = review.build_bundle(
        matrix=matrix,
        target=target,
        trace=trace,
        independent=independent,
        finals=[],
        attempts=attempts,
    )
    review.BUNDLE.parent.mkdir(parents=True, exist_ok=True)
    review.BUNDLE.write_text(
        json.dumps(bundle, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    # The bundle itself is the typed outage/insufficiency receipt. Provider
    # unavailability is evidence, not a reason to abort the remaining reviewer
    # lanes (for example Gemini) in the enclosing workflow.
    print(json.dumps({
        "target_id": target["target_id"],
        "execution_budget_families": len(selected),
        "semantic_admission_minimum_families": minimum,
        "status": bundle["status"],
        "independent_families": bundle["independent_reviewer_family_count"],
        "final_families": bundle["final_disposition_family_count"],
        "semantic_delta_admitted": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
