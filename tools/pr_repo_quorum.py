#!/usr/bin/env python3
"""Fail-closed multi-model review of the exact pull-request change set.

This is review evidence only. It cannot merge, authorize, promote Garden canon,
or turn model agreement into proof. Round 1 is blind; round 2 exposes only the
validated blind findings to the same reviewers for adversarial cross-examination.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any
from urllib import error, request

from tools.free_model_rotation import catalog

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "agents/outbox/pr-review/quorum.json"
DETAIL_DIR = ROOT / "agents/outbox/pr-review/details"
CHAT = "https://openrouter.ai/api/v1/chat/completions"
MIN_FAMILIES = 3
PREFERRED_FINALS = 4
CANDIDATE_FAMILIES = 6
MAX_DIFF_CHARS = 60000


def run(*argv: str) -> str:
    return subprocess.run(argv, cwd=ROOT, check=True, text=True, capture_output=True).stdout


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def select_candidates(models: list[dict[str, Any]], slot: int, desired: int = CANDIDATE_FAMILIES) -> list[dict[str, Any]]:
    """Select distinct live free publisher namespaces rather than a stale hard-coded family list."""
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in models:
        model_id = str(row.get("id", ""))
        if not model_id.endswith(":free") or "/" not in model_id:
            continue
        publisher = model_id.split("/", 1)[0].strip().lower()
        if publisher:
            grouped.setdefault(publisher, []).append(row)
    if len(grouped) < MIN_FAMILIES:
        raise SystemExit(f"Only {len(grouped)} distinct live free publisher families available; need {MIN_FAMILIES}")
    families = sorted(grouped)
    start = slot % len(families)
    ordered = families[start:] + families[:start]
    selected: list[dict[str, Any]] = []
    for family in ordered[: min(desired, len(ordered))]:
        hits = sorted(grouped[family], key=lambda x: int(x.get("context_length") or 0), reverse=True)
        winner = hits[0]
        selected.append({
            "family": family,
            "role": "independent_free_reviewer",
            "model": winner["id"],
            "context_length": winner.get("context_length"),
        })
    if len(selected) < MIN_FAMILIES:
        raise SystemExit(f"Selected only {len(selected)} distinct free families; need {MIN_FAMILIES}")
    return selected


def exact_change_pack(base: str, head: str) -> tuple[dict[str, Any], str]:
    changed = [x for x in run("git", "diff", "--name-only", base, head).splitlines() if x.strip()]
    full = run("git", "diff", "--no-ext-diff", "--unified=3", base, head)
    full_hash = hashlib.sha256(full.encode()).hexdigest()
    if len(full) <= MAX_DIFF_CHARS:
        evidence = full
        coverage = "FULL_DIFF"
    else:
        half = MAX_DIFF_CHARS // 2
        evidence = full[:half] + "\n...[bounded middle omitted; full diff bound by SHA-256]...\n" + full[-half:]
        coverage = "BOUNDED_HEAD_TAIL"
    target = {
        "schema": "GardenPRReviewTarget/v1",
        "base_sha": base,
        "head_sha": head,
        "changed_paths": changed,
        "changed_path_count": len(changed),
        "full_diff_sha256": full_hash,
        "full_diff_chars": len(full),
        "evidence_coverage": coverage,
        "evidence_chars": len(evidence),
    }
    return target, evidence


def parse_object(text: str) -> dict[str, Any] | None:
    raw = (text or "").strip()
    if raw.startswith("```"):
        lines = raw.splitlines()[1:]
        if lines and lines[-1].strip() == "```":
            lines.pop()
        raw = "\n".join(lines).strip()
    try:
        value = json.loads(raw)
    except Exception:
        start, end = raw.find("{"), raw.rfind("}")
        if start < 0 or end <= start:
            return None
        try:
            value = json.loads(raw[start:end + 1])
        except Exception:
            return None
    return value if isinstance(value, dict) else None


def call(model: dict[str, Any], prompt: str, *, max_tokens: int = 1800) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    model_id = str(model["model"])
    if not model_id.endswith(":free"):
        return None, {"status": "PAID_ROUTE_REFUSED", "model": model_id}
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        return None, {"status": "KEY_UNAVAILABLE", "model": model_id}
    payload = {
        "model": model_id,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.05,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"},
        "provider": {"allow_fallbacks": True},
    }
    req = request.Request(
        CHAT,
        method="POST",
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/ankitdcx/garden-swarm",
            "X-Title": "Garden exact PR review quorum",
        },
    )
    try:
        with request.urlopen(req, timeout=240) as response:
            data = json.loads(response.read().decode())
    except error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")[:700]
        return None, {"status": f"HTTP_{exc.code}", "model": model_id, "detail": detail}
    except Exception as exc:
        return None, {"status": "PROVIDER_ERROR", "model": model_id, "detail": f"{type(exc).__name__}:{exc}"}
    usage = data.get("usage") or {}
    if usage.get("cost") not in (0, 0.0):
        return None, {"status": "ZERO_COST_NOT_VERIFIED", "model": model_id, "usage": usage}
    try:
        content = data["choices"][0]["message"].get("content", "")
    except Exception:
        content = ""
    value = parse_object(content)
    return value, {"status": "CALLED", "model": model_id, "usage": usage}


def validate_blind(value: dict[str, Any], model: dict[str, Any], target: dict[str, Any]) -> dict[str, Any]:
    required = {"disposition", "claim", "falsification", "proposed_delta", "do_nothing", "evidence_ancestry", "uncertainty"}
    if not required.issubset(value):
        raise ValueError("missing compact blind-review fields")
    if value["disposition"] not in {"NO_CHANGE", "PROPOSE_DELTA", "BLOCKER", "NEEDS_MORE_EVIDENCE"}:
        raise ValueError("invalid blind disposition")
    return {
        "schema": "GardenRepoBlindReview/v1",
        "reviewer_family": model["family"],
        "reviewer_model": model["model"],
        "target_hash": target["full_diff_sha256"],
        **{k: value[k] for k in sorted(required)},
    }


def validate_final(value: dict[str, Any], model: dict[str, Any], target: dict[str, Any]) -> dict[str, Any]:
    required = {"final_disposition", "surviving_claim", "peer_challenges", "correlated_evidence", "recommended_delta", "required_tests", "uncertainty"}
    if not required.issubset(value):
        raise ValueError("missing compact final-review fields")
    if value["final_disposition"] not in {"NO_CHANGE", "ACCEPT_PROPOSAL", "REJECT_PROPOSAL", "BLOCKER", "NEEDS_MORE_EVIDENCE"}:
        raise ValueError("invalid final disposition")
    return {
        "schema": "GardenRepoPeerCrossExam/v1",
        "reviewer_family": model["family"],
        "reviewer_model": model["model"],
        "target_hash": target["full_diff_sha256"],
        **{k: value[k] for k in sorted(required)},
    }


def blind_prompt(model: dict[str, Any], target: dict[str, Any], evidence: str) -> str:
    return f"""You are one blind independent reviewer of a Garden repository pull request. Do not infer any peer conclusion. Review only the supplied diff evidence. Try to falsify the change before proposing complexity. If bounded evidence is insufficient, use NEEDS_MORE_EVIDENCE. Model agreement is not proof and common training/source ancestry is not independent evidence. Do not output chain-of-thought. Return ONE compact JSON object only (keep total answer under 900 words) with exactly these fields: disposition=NO_CHANGE|PROPOSE_DELTA|BLOCKER|NEEDS_MORE_EVIDENCE, claim, falsification, proposed_delta, do_nothing, evidence_ancestry, uncertainty.
Reviewer family={model['family']} role={model['role']}
Target={json.dumps(target, sort_keys=True)}
--- BEGIN PR DIFF EVIDENCE ---
{evidence}
--- END PR DIFF EVIDENCE ---"""


def final_prompt(model: dict[str, Any], target: dict[str, Any], own: dict[str, Any], peers: list[dict[str, Any]]) -> str:
    return f"""You are returning for Garden repository review round 2. Challenge the other blind findings; do not vote or average. A valid counterexample can defeat a majority. Identify correlated/common-source reasoning. Do not output chain-of-thought. Return ONE compact JSON object only (under 700 words) with exactly: final_disposition=NO_CHANGE|ACCEPT_PROPOSAL|REJECT_PROPOSAL|BLOCKER|NEEDS_MORE_EVIDENCE, surviving_claim, peer_challenges, correlated_evidence, recommended_delta, required_tests, uncertainty.
Reviewer family={model['family']} role={model['role']}
Target={json.dumps(target, sort_keys=True)}
Your blind finding={json.dumps(own, ensure_ascii=False)}
Peer blind findings={json.dumps(peers, ensure_ascii=False)}"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-sha", default=os.environ.get("BASE_SHA"), required=False)
    parser.add_argument("--head-sha", default=os.environ.get("HEAD_SHA"), required=False)
    args = parser.parse_args()
    if not args.base_sha or not args.head_sha:
        raise SystemExit("BASE_SHA and HEAD_SHA required")
    target, evidence = exact_change_pack(args.base_sha, args.head_sha)
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise SystemExit("OPENROUTER_API_KEY required")
    selected = select_candidates(catalog(key), int(time.time() // 3600), desired=CANDIDATE_FAMILIES)
    attempts: list[dict[str, Any]] = []
    blind: list[dict[str, Any]] = []
    model_by_family = {str(m["family"]): m for m in selected}
    DETAIL_DIR.mkdir(parents=True, exist_ok=True)
    for model in selected:
        raw, attempt = call(model, blind_prompt(model, target, evidence))
        attempt.update({"phase": "BLIND", "family": model["family"]})
        attempts.append(attempt)
        if raw is None:
            continue
        try:
            row = validate_blind(raw, model, target)
        except Exception as exc:
            attempts.append({"phase": "BLIND_PARSE", "family": model["family"], "status": "INVALID_OUTPUT", "detail": str(exc)})
            continue
        blind.append(row)
        (DETAIL_DIR / f"blind-{model['family']}.json").write_text(json.dumps(row, indent=2, ensure_ascii=False) + "\n")
    blind_families = sorted({x["reviewer_family"] for x in blind})
    finals: list[dict[str, Any]] = []
    if len(blind_families) >= MIN_FAMILIES:
        for family in blind_families[:PREFERRED_FINALS]:
            model = model_by_family[family]
            own = next(x for x in blind if x["reviewer_family"] == family)
            peers = [x for x in blind if x["reviewer_family"] != family]
            raw, attempt = call(model, final_prompt(model, target, own, peers), max_tokens=1400)
            attempt.update({"phase": "CROSS_EXAM", "family": family})
            attempts.append(attempt)
            if raw is None:
                continue
            try:
                row = validate_final(raw, model, target)
            except Exception as exc:
                attempts.append({"phase": "FINAL_PARSE", "family": family, "status": "INVALID_OUTPUT", "detail": str(exc)})
                continue
            finals.append(row)
            (DETAIL_DIR / f"final-{family}.json").write_text(json.dumps(row, indent=2, ensure_ascii=False) + "\n")
    final_families = sorted({x["reviewer_family"] for x in finals})
    status = "PASS_REVIEW_QUORUM" if len(blind_families) >= MIN_FAMILIES and len(final_families) >= MIN_FAMILIES else "INSUFFICIENT_INDEPENDENT_REVIEW"
    receipt = {
        "schema": "GardenExactPRReviewQuorumReceipt/v1",
        "target": target,
        "minimum_independent_families": MIN_FAMILIES,
        "preferred_final_families": PREFERRED_FINALS,
        "candidate_family_count": len(selected),
        "selected_families": [x["family"] for x in selected],
        "blind_families": blind_families,
        "final_families": final_families,
        "blind_reviews": blind,
        "final_reviews": finals,
        "attempts": attempts,
        "status": status,
        "semantic_delta_admitted": False,
        "authority_boundary": "Review quorum is evidence only; it grants no merge, execution, constitutional or canonical-promotion authority.",
    }
    receipt["receipt_sha256"] = canonical_hash({k: v for k, v in receipt.items() if k != "receipt_sha256"})
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"status": status, "target_hash": target["full_diff_sha256"], "selected_families": receipt["selected_families"], "blind_families": blind_families, "final_families": final_families}, sort_keys=True))
    return 0 if status == "PASS_REVIEW_QUORUM" else 1


if __name__ == "__main__":
    raise SystemExit(main())
