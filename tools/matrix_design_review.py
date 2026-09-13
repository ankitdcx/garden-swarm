#!/usr/bin/env python3
"""Run one bounded Garden Design Review Matrix target through independent free reviewers.

Admission boundary:
- exactly one public target per run;
- >=3 distinct OpenRouter :free model families must complete independently;
- all successful OpenRouter calls must report cost 0;
- peer cross-examination starts only after the independent threshold is met;
- >=3 independent final dispositions are required before the bundle is merely
  eligible for later Garden/GSL whole-source cross-reference;
- this tool never admits a semantic delta or writes canonical Garden source.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
from pathlib import Path
from typing import Any
from urllib import error, request

CHAT = "https://openrouter.ai/api/v1/chat/completions"
MATRIX = Path("agents/design-review-matrix.json")
SELECTION = Path("agents/runtime/free-selection.json")
OUT_DIR = Path("agents/outbox/hourly/matrix-review")
BUNDLE = Path("agents/outbox/hourly/design-review-bundle.json")

INDEPENDENT_SCHEMA = "GardenDesignFinding/v1"
FINAL_SCHEMA = "GardenDesignFinalDisposition/v1"


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def load_matrix(root: Path = Path(".")) -> tuple[dict[str, Any], dict[str, Any]]:
    payload = json.loads((root / MATRIX).read_text(encoding="utf-8"))
    if payload.get("schema") != "GardenDesignReviewMatrix/v1":
        raise ValueError("unsupported GardenDesignReviewMatrix schema")
    if payload.get("semantic_compliance_proved") is not False:
        raise ValueError("review matrix may not self-claim semantic compliance")
    minimum = int(payload.get("minimum_independent_reviewer_families", 0))
    if minimum < 3:
        raise ValueError("review matrix may not require fewer than 3 independent reviewer families")
    active = str(payload.get("active_target_id", "")).strip()
    matches = [row for row in payload.get("targets", []) if row.get("target_id") == active]
    if len(matches) != 1:
        raise ValueError("active Design Review Matrix target must resolve exactly once")
    target = matches[0]
    if target.get("public_only") is not True:
        raise ValueError("non-public target refused by public free-review bus")
    return payload, target


def extract_target(root: Path, target: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    rel = str(target["source_file"])
    path = (root / rel).resolve()
    if root.resolve() not in path.parents:
        raise ValueError("target source escapes repository root")
    raw = path.read_bytes()
    text = raw.decode("utf-8")
    start_anchor = str(target["start_anchor"])
    end_anchor = str(target["end_anchor"])
    start = text.find(start_anchor)
    if start < 0:
        raise ValueError(f"start anchor not found: {start_anchor}")
    end = text.find(end_anchor, start + len(start_anchor))
    if end < 0 or end <= start:
        raise ValueError(f"end anchor not found after start: {end_anchor}")
    bounded = text[start:end].strip()
    if not bounded:
        raise ValueError("bounded review target is empty")
    trace = {
        "source": rel,
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "start_anchor": start_anchor,
        "end_anchor": end_anchor,
        "coverage": "BOUNDED_EXACT_ANCHORS",
    }
    return bounded, trace


def _clean_json(text: str) -> dict[str, Any] | None:
    raw = (text or "").strip()
    if raw.startswith("```"):
        lines = raw.splitlines()[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        raw = "\n".join(lines).strip()
    if not raw:
        return None
    try:
        value = json.loads(raw)
        return value if isinstance(value, dict) else None
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.S)
        if not match:
            return None
        try:
            value = json.loads(match.group(0))
            return value if isinstance(value, dict) else None
        except json.JSONDecodeError:
            return None


def validate_independent(value: dict[str, Any], *, target_id: str, family: str, model_id: str) -> dict[str, Any]:
    required = [
        "source_anchors", "current_semantic_claim", "falsification_attempts",
        "evidence_search_trace", "proposed_delta", "do_nothing_comparison",
        "affected_invariants", "affected_tests", "affected_contracts",
        "uncertainty", "evidence_ancestry", "overturn_conditions", "disposition",
    ]
    if any(key not in value for key in required):
        raise ValueError("independent finding missing required fields")
    if value.get("disposition") not in {"NO_CHANGE", "PROPOSE_DELTA", "BLOCKER", "NEEDS_CROSS_REFERENCE"}:
        raise ValueError("invalid independent disposition")
    if not isinstance(value.get("source_anchors"), list) or not value["source_anchors"]:
        raise ValueError("source_anchors must be non-empty")
    if not isinstance(value.get("falsification_attempts"), list) or not value["falsification_attempts"]:
        raise ValueError("falsification_attempts must be non-empty")
    if not isinstance(value.get("evidence_search_trace"), list) or not value["evidence_search_trace"]:
        raise ValueError("evidence_search_trace must be non-empty")
    value.update({
        "schema": INDEPENDENT_SCHEMA,
        "target_id": target_id,
        "reviewer_family": family,
        "reviewer_model": model_id,
        "independent": True,
    })
    return value


def validate_final(value: dict[str, Any], *, target_id: str, family: str, model_id: str) -> dict[str, Any]:
    required = [
        "peer_challenges", "correlated_or_common_source_evidence", "revised_disposition",
        "revised_delta", "do_nothing_comparison", "uncertainty", "overturn_conditions",
    ]
    if any(key not in value for key in required):
        raise ValueError("final disposition missing required fields")
    if value.get("revised_disposition") not in {"NO_CHANGE", "PROPOSE_DELTA", "BLOCKER", "NEEDS_CROSS_REFERENCE"}:
        raise ValueError("invalid final disposition")
    if not isinstance(value.get("peer_challenges"), list):
        raise ValueError("peer_challenges must be a list")
    if not isinstance(value.get("correlated_or_common_source_evidence"), list):
        raise ValueError("correlated evidence must be a list")
    value.update({
        "schema": FINAL_SCHEMA,
        "target_id": target_id,
        "reviewer_family": family,
        "reviewer_model": model_id,
        "independent_final_disposition": True,
    })
    return value


def call_openrouter(*, model: dict[str, Any], prompt: str, max_tokens: int = 3600) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    model_id = str(model["model"])
    if not model_id.endswith(":free"):
        raise RuntimeError(f"paid route refused: {model_id}")
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        return None, {"status": "KEY_UNAVAILABLE", "model": model_id, "cost": None}
    body = {
        "model": model_id,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": max_tokens,
        "provider": {"allow_fallbacks": False},
    }
    req = request.Request(
        CHAT,
        method="POST",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/ankitdcx/garden-swarm",
            "X-Title": "Garden Design Review Matrix",
        },
    )
    try:
        with request.urlopen(req, timeout=300) as response:
            data = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        return None, {"status": f"HTTP_{exc.code}", "model": model_id, "cost": None, "detail": detail[:1000]}
    except Exception as exc:
        return None, {"status": "PROVIDER_ERROR", "model": model_id, "cost": None, "detail": f"{type(exc).__name__}: {exc}"}
    usage = data.get("usage") or {}
    cost = usage.get("cost")
    if cost not in (None, 0, 0.0):
        raise RuntimeError(f"non-zero inference cost refused: {model_id} cost={cost}")
    try:
        content = data["choices"][0]["message"].get("content", "")
    except Exception:
        content = ""
    return _clean_json(content), {"status": "CALLED", "model": model_id, "cost": 0 if cost is None else cost, "usage": usage}


def independent_prompt(*, target: dict[str, Any], source: str, trace: dict[str, Any], model: dict[str, Any]) -> str:
    return f"""You are an independent Garden design reviewer. You have not seen and must not infer any peer conclusion.
Reviewer family: {model['family']}; role/posture: {model['role']}. Analyze ONLY the supplied already-public bounded target.
Try to falsify the current semantics before proposing an upgrade. Agreement is not proof. If whole-source context is required, use NEEDS_CROSS_REFERENCE rather than guessing.
Return one JSON object only. Required fields:
source_anchors (array of exact quoted anchor strings from the supplied target), current_semantic_claim (string), falsification_attempts (array), evidence_search_trace (array), proposed_delta (string; use NO_CHANGE when none), do_nothing_comparison (string), affected_invariants (array), affected_tests (array), affected_contracts (array), uncertainty (string), evidence_ancestry (string), overturn_conditions (string), disposition (NO_CHANGE|PROPOSE_DELTA|BLOCKER|NEEDS_CROSS_REFERENCE).
Target ID: {target['target_id']}
Review question: {target['review_question']}
Supplied trace: {json.dumps(trace, ensure_ascii=False)}
--- BEGIN BOUNDED PUBLIC TARGET ---
{source}
--- END BOUNDED PUBLIC TARGET ---"""


def peer_prompt(*, target: dict[str, Any], source: str, trace: dict[str, Any], own: dict[str, Any], peers: list[dict[str, Any]], model: dict[str, Any]) -> str:
    return f"""You are reviewer family {model['family']} performing an independent final disposition after peer cross-examination on the SAME bounded target.
Do not vote or average. Challenge concrete claims, identify correlated/common-source evidence, and revise your own finding when warranted. Agreement remains evidence, not proof. Do not use material outside the supplied public target and peer findings.
Return one JSON object only with fields: peer_challenges (array), correlated_or_common_source_evidence (array), revised_disposition (NO_CHANGE|PROPOSE_DELTA|BLOCKER|NEEDS_CROSS_REFERENCE), revised_delta (string; NO_CHANGE when none), do_nothing_comparison (string), uncertainty (string), overturn_conditions (string).
Target ID: {target['target_id']}
Review question: {target['review_question']}
Supplied trace: {json.dumps(trace, ensure_ascii=False)}
Your independent finding: {json.dumps(own, ensure_ascii=False)}
Peer independent findings: {json.dumps(peers, ensure_ascii=False)}
--- BEGIN BOUNDED PUBLIC TARGET ---
{source}
--- END BOUNDED PUBLIC TARGET ---"""


def build_bundle(*, matrix: dict[str, Any], target: dict[str, Any], trace: dict[str, Any], independent: list[dict[str, Any]], finals: list[dict[str, Any]], attempts: list[dict[str, Any]]) -> dict[str, Any]:
    minimum = int(matrix["minimum_independent_reviewer_families"])
    independent_families = sorted({row["reviewer_family"] for row in independent})
    final_families = sorted({row["reviewer_family"] for row in finals})
    costs = [a.get("cost") for a in attempts if a.get("status") == "CALLED"]
    zero_cost_verified = bool(costs) and all(cost in (0, 0.0) for cost in costs)
    if len(independent_families) < minimum:
        status = "INSUFFICIENT_INDEPENDENT_REVIEW"
    elif len(final_families) < minimum:
        status = "INSUFFICIENT_PEER_CROSS_EXAMINATION"
    elif not zero_cost_verified:
        status = "COST_VERIFICATION_FAILED"
    else:
        status = "REVIEW_COMPLETE_NEEDS_GSL_INTEGRATOR"
    payload = {
        "schema": "GardenDesignReviewBundle/v1",
        "created_at_unix": int(time.time()),
        "design_epoch": matrix["design_epoch"],
        "canonical_source_root_sha256": matrix["canonical_source_root_sha256"],
        "target": target,
        "source_trace": trace,
        "minimum_independent_reviewer_families": minimum,
        "independent_reviewer_family_count": len(independent_families),
        "final_disposition_family_count": len(final_families),
        "independent_reviewer_families": independent_families,
        "final_disposition_families": final_families,
        "zero_cost_verified": zero_cost_verified,
        "provider_attempts": attempts,
        "independent_findings": independent,
        "final_dispositions": finals,
        "status": status,
        "semantic_delta_admitted": False,
        "admission_boundary": "Even REVIEW_COMPLETE_NEEDS_GSL_INTEGRATOR is proposal evidence only. Whole-source Compare/Reason/Proof/Evidence, AAP, authority, ActionGate and human/canonical boundaries remain downstream.",
    }
    payload["bundle_sha256"] = canonical_hash({k: v for k, v in payload.items() if k != "bundle_sha256"})
    return payload


def main() -> int:
    root = Path(".").resolve()
    matrix, target = load_matrix(root)
    source, trace = extract_target(root, target)
    selection = json.loads((root / SELECTION).read_text(encoding="utf-8"))
    selected = list(selection.get("selected") or [])
    minimum = int(matrix["minimum_independent_reviewer_families"])
    if len(selected) < minimum:
        raise SystemExit(f"free-model selection has {len(selected)} families; matrix requires {minimum}")
    families = [str(m.get("family")) for m in selected]
    if len(set(families)) != len(families):
        raise SystemExit("free-model selection contains duplicate families")
    if not all(str(m.get("model", "")).endswith(":free") for m in selected):
        raise SystemExit("non-free OpenRouter route refused")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    attempts: list[dict[str, Any]] = []
    independent: list[dict[str, Any]] = []
    independent_by_family: dict[str, dict[str, Any]] = {}

    # All independent calls finish before any reviewer sees a peer finding.
    for model in selected:
        family = str(model["family"])
        raw, attempt = call_openrouter(model=model, prompt=independent_prompt(target=target, source=source, trace=trace, model=model))
        attempt.update({"phase": "INDEPENDENT", "family": family})
        attempts.append(attempt)
        if raw is None:
            continue
        try:
            finding = validate_independent(raw, target_id=target["target_id"], family=family, model_id=str(model["model"]))
        except Exception as exc:
            attempts.append({"phase": "INDEPENDENT_PARSE", "family": family, "model": model["model"], "status": "INVALID_OUTPUT", "cost": 0, "detail": str(exc)})
            continue
        independent.append(finding)
        independent_by_family[family] = finding
        (OUT_DIR / f"{family}-independent.json").write_text(json.dumps(finding, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    finals: list[dict[str, Any]] = []
    if len(independent_by_family) >= minimum:
        for model in selected:
            family = str(model["family"])
            own = independent_by_family.get(family)
            if own is None:
                continue
            peers = [row for row in independent if row["reviewer_family"] != family]
            raw, attempt = call_openrouter(model=model, prompt=peer_prompt(target=target, source=source, trace=trace, own=own, peers=peers, model=model))
            attempt.update({"phase": "PEER_CROSS_EXAMINATION", "family": family})
            attempts.append(attempt)
            if raw is None:
                continue
            try:
                final = validate_final(raw, target_id=target["target_id"], family=family, model_id=str(model["model"]))
            except Exception as exc:
                attempts.append({"phase": "PEER_PARSE", "family": family, "model": model["model"], "status": "INVALID_OUTPUT", "cost": 0, "detail": str(exc)})
                continue
            finals.append(final)
            (OUT_DIR / f"{family}-final.json").write_text(json.dumps(final, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    bundle = build_bundle(matrix=matrix, target=target, trace=trace, independent=independent, finals=finals, attempts=attempts)
    BUNDLE.parent.mkdir(parents=True, exist_ok=True)
    BUNDLE.write_text(json.dumps(bundle, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "target_id": target["target_id"],
        "status": bundle["status"],
        "independent_families": bundle["independent_reviewer_family_count"],
        "final_families": bundle["final_disposition_family_count"],
        "zero_cost_verified": bundle["zero_cost_verified"],
        "semantic_delta_admitted": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
