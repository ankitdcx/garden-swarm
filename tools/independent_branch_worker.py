"""One OpenRouter inference call per dispatch under independent-branch convergence.

The worker is deliberately unable to synthesize across reviewer families. ChatGPT
owns the private baseline, branch reconciliation decisions, cross-branch synthesis
and final candidate construction outside OpenRouter. This worker only transports a
validated public directive to one isolated reviewer at a time and persists receipts.
"""
from __future__ import annotations

import base64
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import time
from urllib import error, parse

from tools import context_capsule
from tools import independent_branch_protocol as protocol
from tools import matrix_design_review as review
from tools import single_review_worker as legacy
from tools import review_context
from tools import review_campaign
from tools.review_budget import effective_policy
from tools.provider_exclusion import load_policy, require_allowed_model

DIRECTIVE_PATH = "review-state/convergence-directive.json"
DIRECTIVE_REF = legacy.STATE_BRANCH
WORKER_PROTOCOL = protocol.PROTOCOL_ID


def _model_identity_matches(requested: str, actual: str | None, identity=None) -> bool:
    return actual == requested or bool(identity and identity.get("id") == requested and identity.get("canonical_slug") == actual)


def load_directive(token: str) -> dict | None:
    url = legacy.API + "/contents/" + DIRECTIVE_PATH + "?ref=" + DIRECTIVE_REF
    try:
        result = legacy.http(url, token)
    except error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise
    content = result.get("content")
    if not content:
        blob = legacy.http(legacy.API + "/git/blobs/" + result["sha"], token)
        content = blob.get("content")
    if not content:
        raise ValueError("convergence directive has no content")
    return json.loads(base64.b64decode(content))


def _target_by_id(root: Path, target_id: str, directive=None) -> tuple[dict, dict, str, dict, str, str, str]:
    matrix = json.loads((root / "agents/design-review-matrix.json").read_text(encoding="utf-8"))
    if matrix.get("schema") != "GardenDesignReviewMatrix/v1":
        raise ValueError("unsupported design review matrix")
    matches = [row for row in matrix.get("targets", []) if row.get("target_id") == target_id]
    if len(matches) != 1:
        raise ValueError("directive target must resolve exactly once")
    target = matches[0]
    if target.get("public_only") is not True:
        raise ValueError("non-public target refused")
    source, trace = review.extract_target(root, target)
    directive = directive or {}
    if directive.get('context_requests') and directive.get('context_requests_reviewed_as_neutral') is not True:
        raise ValueError('expanded context requires ChatGPT neutral-reference review before sharing')
    policy = json.loads((root / 'agents/openrouter-paid-review-policy.json').read_text())
    profile = review_context.select_profile(policy, target, directive.get('review_profile'))
    packet = review_context.build_packet(root, target, source, trace, profile, directive.get('context_requests'))
    packet, capsule_hash, expansion_level = review_context.bind_capsule(packet, directive, target, trace)
    trace = {**trace, 'context_packet_sha256': packet['packet_sha256'],
             'source_root_sha256': packet['source_root_sha256'],
             'context_coverage': packet['coverage'], 'review_profile': profile}
    return matrix, target, review_context.packet_text(packet), trace, packet['packet_sha256'], capsule_hash, expansion_level


def _families(policy: dict) -> list[str]:
    rows = list(policy.get("routine_reviewers") or [])
    families = [str(row.get("family") or "") for row in rows]
    if len(families) != 4 or len(set(families)) != 4 or any(not f for f in families):
        raise ValueError("active convergence board must contain four distinct families")
    return families


def _cycle_id(*, target_id: str, source_packet_sha256: str, baseline_sha256: str, policy: dict, convergence_policy: dict) -> str:
    return protocol.sha256_value({
        "protocol": WORKER_PROTOCOL,
        "target_id": target_id,
        "source_packet_sha256": source_packet_sha256,
        "baseline_sha256": baseline_sha256,
        "model_policy_sha256": protocol.sha256_value(policy),
        "convergence_policy_sha256": protocol.sha256_value(convergence_policy),
    })


def _cycle(
    state: dict,
    cycle_id: str,
    *,
    directive: dict,
    source_packet_sha256: str,
    capsule_sha256: str,
    context_expansion_level: str,
) -> dict:
    cycles = state.setdefault("convergence_cycles", {})
    if cycle_id not in cycles:
        cycles[cycle_id] = {
            "protocol": WORKER_PROTOCOL,
            "target_id": directive["target_id"],
            "source_packet_sha256": source_packet_sha256,
            "architecture_context_capsule_sha256": capsule_sha256,
            "context_expansion_level": context_expansion_level,
            "baseline_sha256": directive["private_baseline_commitment"]["baseline_sha256"],
            "neutral_query_sha256": directive["private_baseline_commitment"]["neutral_query_sha256"],
            "attempts": [],
            "blind": {},
            "reconcile": {},
            "final": {},
            "confirm": {},
            "semantic_delta_admitted": False,
        }
    return cycles[cycle_id]


def _latest_branch_result(cycle: dict, family: str) -> dict:
    reconciled = list((cycle.get("reconcile") or {}).get(family) or [])
    if reconciled:
        return reconciled[-1]
    blind = (cycle.get("blind") or {}).get(family)
    if blind:
        return blind
    raise ValueError("branch has no prior response")


def _plan(cycle: dict, directive: dict, families: list[str]) -> tuple[str, str, str] | None:
    if cycle.get("context_expansion_required"):
        return None
    phase = directive["phase"]
    if phase == "BLIND":
        for family in families:
            if family not in cycle["blind"]:
                return phase, family, "blind:" + family
        return None
    if set(cycle.get("blind") or {}) != set(families):
        raise ValueError("all four initial reviews must finish before reconciliation or final review")
    if phase == "RECONCILE":
        if cycle.get("final") or cycle.get("confirm"):
            raise ValueError("branch reconciliation cannot change after final review starts")
        family = directive["family"]
        branch_round = int(directive["branch_round"])
        done = list(cycle["reconcile"].get(family) or [])
        if len(done) >= branch_round:
            return None
        if len(done) != branch_round - 1:
            raise ValueError("branch reconciliation rounds must be sequential")
        prior = _latest_branch_result(cycle, family)
        if prior.get("finding_sha256") != directive["own_response_sha256"]:
            raise ValueError("branch directive does not bind the latest own-branch response")
        return phase, family, f"reconcile:{branch_round}:{family}"
    closures = directive.get("branch_closures") or {}
    if set(closures) != set(families):
        raise ValueError("final review requires four explicit branch closures")
    for family in families:
        closure, latest = closures[family], _latest_branch_result(cycle, family)
        if closure.get("finding_sha256") != latest.get("finding_sha256"):
            raise ValueError("branch closure must bind the latest response")
        if not isinstance(closure.get("reason"), str) or not closure["reason"].strip():
            raise ValueError("branch closure needs a material-issue assessment")
        finding = latest["finding"]
        if finding.get("context_sufficiency") != "SUFFICIENT":
            raise ValueError("branch closure cannot waive missing context")
        if cycle["reconcile"].get(family):
            if closure.get("outcome") != "RECONCILED":
                raise ValueError("followed-up branch must be closed as RECONCILED")
        elif (closure.get("outcome") != "NO_FOLLOWUP_NEEDED" or
              finding.get("disposition") != "NO_CHANGE"):
            raise ValueError("only an explicit NO_CHANGE branch can omit followup")
    closures_hash = protocol.sha256_value(closures)
    if cycle.get("branch_closures_sha256", closures_hash) != closures_hash:
        raise ValueError("branch closures changed after final review began")
    cycle["branch_closures_sha256"] = closures_hash
    bucket = "final" if phase == "FINAL" else "confirm"
    audit = protocol.synthesis_audit_packet(cycle, directive, families)
    audit_key = bucket + "_synthesis_audit_sha256"
    if cycle.get(audit_key, audit["packet_sha256"]) != audit["packet_sha256"]:
        raise ValueError("synthesis audit changed inside a final-review round")
    cycle[audit_key] = audit["packet_sha256"]
    candidate_hash = directive["merged_candidate_sha256"]
    existing_hashes = {row.get("candidate_sha256") for row in cycle[bucket].values() if row.get("candidate_sha256")}
    if existing_hashes and existing_hashes != {candidate_hash}:
        raise ValueError("candidate changed inside a final-review round")
    if phase == "CONFIRM" and len(cycle.get("final") or {}) != 4:
        raise ValueError("confirmation requires a completed four-family final round")
    for family in families:
        if family not in cycle[bucket]:
            return phase, family, bucket + ":" + family
    return None


def _require_explicit_retry(state: dict, cycle_id: str, slot: str, directive: dict, campaign=None, now=None) -> None:
    prior = [a for a in state.get("attempts", [])
             if a.get("cycle") == cycle_id and a.get("slot") == slot and a.get("inference_reserved")]
    if not prior:
        return
    if len(prior) >= 2:
        raise ValueError("two attempts per review slot exhausted; stop and escalate")
    latest = prior[-1]
    recovery = review_campaign.rate_limit_recovery(latest, campaign)
    if recovery and Decimal(str(time.time() if now is None else now)) < recovery["retry_not_before"]:
        raise ValueError("rate-limit retry backoff has not elapsed")
    if not recovery and latest.get("status") not in ("INCOMPLETE", "INCOMPLETE_REQUIRES_EXPLICIT_DIRECTIVE"):
        raise ValueError("prior slot is unresolved or already completed")
    if (directive.get("retry_of_attempt_sha256") != protocol.sha256_value(latest) or
            not isinstance(directive.get("retry_reason"), str) or not directive["retry_reason"].strip()):
        raise ValueError("incomplete call requires an explicit receipt-bound retry directive")


def _prefer_alternate_rate_limit_endpoint(eligible, state, cycle_id, slot, directive, campaign):
    """Choose once from verified endpoints of the same pinned model; no fallback."""
    prior = [a for a in state.get('attempts', [])
             if a.get('cycle') == cycle_id and a.get('slot') == slot and a.get('inference_reserved')]
    if not prior:
        return eligible
    previous = prior[-1]
    if (directive.get('retry_of_attempt_sha256') != protocol.sha256_value(previous) or
            review_campaign.rate_limit_recovery(previous, campaign) is None):
        return eligible
    alternatives = [row for row in eligible if row[1]['tag'] != previous.get('endpoint')]
    return alternatives or eligible


def _prompt(*, phase: str, family: str, directive: dict, target: dict, source: str, trace: dict, cycle: dict) -> str:
    if phase == "BLIND":
        prompt = protocol.blind_prompt(target=target, source=source, trace=trace)
        prior_hash = cycle.get("blind_prompt_sha256")
        current_hash = protocol.sha256_text(prompt)
        if prior_hash is not None and prior_hash != current_hash:
            raise ValueError("blind prompt changed across reviewer families")
        cycle["blind_prompt_sha256"] = current_hash
        return prompt
    if phase == "RECONCILE":
        previous = _latest_branch_result(cycle, family)["finding"]
        return protocol.reconciliation_prompt(
            target=target,
            source=source,
            trace=trace,
            own_previous=previous,
            branch_candidate=directive["branch_candidate"],
            branch_round=int(directive["branch_round"]),
        )
    prompt = protocol.final_prompt(
        target=target,
        source=source,
        trace=trace,
        merged_candidate=directive["merged_candidate"],
        phase=phase,
        audit_packet=protocol.synthesis_audit_packet(cycle, directive, directive["reviewer_families"]),
    )
    bucket = "final" if phase == "FINAL" else "confirm"
    key = bucket + "_prompt_sha256"
    current_hash = protocol.sha256_text(prompt)
    if cycle.get(key) is not None and cycle[key] != current_hash:
        raise ValueError("final/confirmation prompt changed across reviewer families")
    cycle[key] = current_hash
    return prompt


def _reconcile_known_attempts(ledger: legacy.GitLedger, key: str, campaign=None) -> None:
    """Resolve identified old UNKNOWN calls without treating their text as v1 evidence."""
    state = ledger.value
    changed = False
    for attempt in state.get("attempts", []):
        if attempt.get("status") not in ("UNKNOWN", "RESERVED"):
            continue
        if review_campaign.unknown_allowance(attempt, campaign) is not None:
            continue  # Preserve unknown billing; retry gate separately checks authorization.
        response_id = attempt.get("response_id")
        if not response_id:
            raise ValueError("unidentified prior call blocks new inference")
        data = legacy.http(legacy.OR + "/generation?" + parse.urlencode({"id": response_id}), key)["data"]
        actual_model = data.get("model")
        actual_provider = data.get("provider_name")
        cost = legacy.money(data.get("total_cost"))
        prior_cost = attempt.get("cost")
        accounted = max(cost, legacy.money(prior_cost)) if prior_cost is not None else cost
        identity = attempt.get('model_identity')
        if actual_model != attempt.get('model') and identity is None:
            identity = legacy.model_identity(key, attempt['model'])
            attempt['model_identity'] = {**identity, 'evidence_timing': 'RECONCILIATION_TIME_NOT_ORIGINAL_REQUEST'}
        if data.get("id") != response_id or not _model_identity_matches(str(attempt.get("model")), actual_model, identity):
            raise ValueError("generation identity mismatch")
        expected_provider = attempt.get("actual_provider") or attempt.get("expected_provider")
        if not expected_provider or actual_provider != expected_provider:
            raise ValueError("generation provider mismatch")
        if accounted > legacy.money(attempt["reserved"]):
            raise ValueError("finalized cost exceeds reservation")
        if data.get("finish_reason") not in ("stop", "length", "error", "content_filter", "tool_calls"):
            raise ValueError("generation has no terminal outcome")
        attempt["response_reported_cost"] = prior_cost
        attempt["final_generation_cost"] = str(cost)
        attempt["cost"] = str(accounted)
        attempt["generation_metadata"] = {k: data.get(k) for k in (
            "id", "model", "provider_name", "total_cost", "finish_reason", "native_finish_reason",
            "tokens_prompt", "tokens_completion", "native_tokens_reasoning",
        )}
        if (attempt.get("binding") or {}).get("protocol") != WORKER_PROTOCOL:
            attempt["status"] = "SUPERSEDED_PROTOCOL_RECEIPT_ONLY"
            attempt["semantic_delta_admitted"] = False
        else:
            attempt["status"] = "INCOMPLETE_REQUIRES_EXPLICIT_DIRECTIVE"
        changed = True
    if changed:
        ledger.save(state)


def _result_status(cycle: dict, phase: str, families: list[str]) -> str:
    if cycle.get("context_expansion_required"):
        return "AWAITING_CHATGPT_CONTEXT_EXPANSION"
    if phase == "BLIND":
        return "READY" if len(cycle["blind"]) < len(families) else "AWAITING_CHATGPT_RECONCILIATION"
    if phase == "RECONCILE":
        return "AWAITING_CHATGPT_RECONCILIATION"
    if phase == "FINAL":
        return "READY" if len(cycle["final"]) < len(families) else "AWAITING_CHATGPT_FINAL_DECISION"
    if len(cycle["confirm"]) < len(families):
        return "READY"
    unresolved = [family for family in families
                  if cycle["confirm"][family]["finding"].get("verdict") != "APPROVE"]
    if unresolved:
        cycle["disagreement_receipt"] = {
            "schema": "GardenReviewDisagreementReceipt/v1",
            "phase": "CONFIRM", "families": unresolved,
            "response_hashes": {f: cycle["confirm"][f]["finding_sha256"] for f in unresolved},
            "status": "ESCALATE_UNRESOLVED", "semantic_delta_admitted": False,
        }
        return "ESCALATE_UNRESOLVED"
    return "AWAITING_CHATGPT_FINAL_DECISION"


def run(root: Path = Path(".")) -> None:
    legacy.host_check()
    key = os.environ.get("OPENROUTER_API_KEY")
    gh = os.environ.get("GH_REVIEW_TOKEN")
    if not key or not gh:
        raise ValueError("required Actions secret/token unavailable")
    ledger = legacy.GitLedger(gh)
    state = ledger.value
    if state.get("paused") is not False or state.get("scope") != "PUBLIC_MATRIX_REVIEW_ONLY":
        raise ValueError("review ledger paused or outside public scope")

    directive = load_directive(gh)
    if directive is None:
        state["continuation"] = {"status": "AWAITING_CHATGPT_BASELINE_OR_DIRECTIVE", "updated": time.time()}
        ledger.save(state)
        print("AWAITING_CHATGPT_BASELINE_OR_DIRECTIVE; no OpenRouter inference")
        return

    policy = json.loads((root / "agents/openrouter-paid-review-policy.json").read_text(encoding="utf-8"))
    convergence_policy = protocol.load_policy(json.loads((root / "agents/independent-branch-convergence-policy.json").read_text(encoding="utf-8")))
    exclusions = load_policy(root / "agents/provider-exclusion-policy.json")
    families = _families(policy)
    matrix, target, source, trace, source_packet_hash, capsule_hash, expansion_level = _target_by_id(root, str(directive.get("target_id") or ""), directive)
    protocol.validate_directive(directive, families=families, target_id=target["target_id"], source_packet_sha256=source_packet_hash)
    campaign = review_campaign.bind_campaign(directive, trace['source_sha256'], root)
    _reconcile_known_attempts(ledger, key, campaign)
    state = ledger.value
    expected_query = protocol.sha256_text(protocol.neutral_query(target))
    if directive['private_baseline_commitment']['neutral_query_sha256'] != expected_query:
        raise ValueError('baseline neutral query does not match current review instructions')
    profile = trace['review_profile']
    task_key = protocol.sha256_value({'target': target['target_id'], 'source_root': trace['source_root_sha256'], 'target_source': trace['source_sha256']})
    total_reserved = sum(a.get('inference_reserved') is True and a.get('task_key') == task_key for a in state['attempts'])
    if total_reserved >= convergence_policy['call_budget']['absolute_maximum_openrouter_inference_calls_per_task']:
        raise ValueError('context expansion cannot reset the task inference-call limit')
    cycle_id = _cycle_id(
        target_id=target["target_id"],
        source_packet_sha256=source_packet_hash,
        baseline_sha256=directive["private_baseline_commitment"]["baseline_sha256"],
        policy=policy,
        convergence_policy=convergence_policy,
    )
    cycle = _cycle(
        state,
        cycle_id,
        directive=directive,
        source_packet_sha256=source_packet_hash,
        capsule_sha256=capsule_hash,
        context_expansion_level=expansion_level,
    )
    protocol.assert_call_budget(cycle, convergence_policy)
    plan = _plan(cycle, directive, families)
    if plan is None:
        state["continuation"] = {"status": _result_status(cycle, directive["phase"], families), "updated": time.time(), "cycle": cycle_id}
        ledger.save(state)
        print(state["continuation"]["status"] + "; no OpenRouter inference")
        return

    phase, family, slot = plan
    _require_explicit_retry(state, cycle_id, slot, directive, campaign=campaign)
    model = next(row for row in policy["routine_reviewers"] if row["family"] == family)
    require_allowed_model(model_id=model["model"], family=family, policy=exclusions)
    prompt = _prompt(phase=phase, family=family, directive=directive, target=target, source=source, trace=trace, cycle=cycle)
    prompt_hash = protocol.sha256_text(prompt)

    spending_policy, spending_receipt = effective_policy(policy, directive, time.time())
    if campaign:
        spending_policy = review_campaign.spending_policy(spending_policy, campaign)
        spending_receipt = {**spending_receipt, 'mode': 'AUTHORIZED_DOCUMENT_CAMPAIGN',
                            'daily_ceiling_usd': spending_policy['daily_openrouter_cost_ceiling_usd'],
                            'pool_lifetime_allocation_usd': spending_policy['budget_pools_usd']['routine']}
    identity = legacy.model_identity(key, model['model'])
    key_info = legacy.http(legacy.OR + "/key", key)["data"]
    reserve, day, daily = legacy.budget_check(state, key_info, spending_policy, time.time(), campaign=campaign)
    if campaign:
        spending_receipt.update(review_campaign.check_total(state, campaign, reserve))
    endpoints = legacy.http(legacy.OR + "/models/" + model["model"] + "/endpoints", key)["data"]["endpoints"]
    eligible = []
    for endpoint in endpoints:
        try:
            body, estimate = legacy.endpoint_request(endpoint, model, prompt, reserve, policy, exclusions, profile=profile, model_capabilities=identity)
            eligible.append((legacy.money(estimate), endpoint, body))
        except (ValueError, KeyError, RuntimeError):
            continue
    if not eligible:
        raise ValueError("no permitted, affordable live endpoint; no model substitution")
    eligible = _prefer_alternate_rate_limit_endpoint(eligible, state, cycle_id, slot, directive, campaign)
    estimate, endpoint, body = min(eligible, key=lambda row: row[0])

    attempt = {
        "inference_reserved": True,
        "task_key": task_key,
        "spending": spending_receipt,
        "review_profile": profile,
        "context_coverage": trace['context_coverage'],
        "model_identity": identity,
        "expected_provider": endpoint['provider_name'],
        "reasoning_control_sent": body.get('reasoning', 'MODEL_NATIVE_DEFAULT_NOT_EXPLICITLY_CONTROLLED'),
        "status": "RESERVED",
        "protocol": WORKER_PROTOCOL,
        "cycle": cycle_id,
        "slot": slot,
        "retry_of_attempt_sha256": directive.get("retry_of_attempt_sha256"),
        "retry_reason": directive.get("retry_reason"),
        "phase": phase,
        "model": model["model"],
        "family": family,
        "endpoint": endpoint["tag"],
        "target_id": target["target_id"],
        "source_packet_sha256": source_packet_hash,
        "architecture_context_capsule_sha256": capsule_hash,
        "context_expansion_level": expansion_level,
        "baseline_commitment_sha256": directive["private_baseline_commitment"]["baseline_sha256"],
        "prompt_sha256": prompt_hash,
        "candidate_sha256": directive.get("merged_candidate_sha256"),
        "synthesis_audit_sha256": cycle.get(("final" if phase == "FINAL" else "confirm") + "_synthesis_audit_sha256") if phase in ("FINAL", "CONFIRM") else None,
        "binding": {"protocol": WORKER_PROTOCOL, "target": target, "trace": trace},
        "source_commit": os.environ["GITHUB_SHA"],
        "run_id": os.environ["GITHUB_RUN_ID"],
        "utc_day": day,
        "started": time.time(),
        "usage_daily_before": daily,
        "reserved": str(reserve),
        "estimated_upper_cost": str(estimate),
        "cost": None,
        "semantic_delta_admitted": False,
        "full_review_complete": False,
    }
    state["attempts"].append(attempt)
    cycle["attempts"].append(attempt)
    state["continuation"] = {"status": "IN_FLIGHT", "cycle": cycle_id, "slot": slot, "updated": time.time()}
    ledger.save(state)

    billing_verified = False
    try:
        response = legacy.http(legacy.OR + "/chat/completions", key, body, timeout=profile['request_timeout_seconds'])
        # Save response identity even when usage is absent, enabling later billing reconciliation.
        attempt.update(response_id=response.get('id'), actual_model=response.get('model'), actual_provider=response.get('provider'))
        cost = legacy.money((response.get("usage") or {}).get("cost"))
        attempt.update(
            response_id=response.get("id"),
            actual_model=response.get("model"),
            actual_provider=response.get("provider"),
            usage=response.get("usage"),
            cost=str(cost),
        )
        if cost > reserve:
            raise ValueError("cost exceeds reservation")
        if not _model_identity_matches(model["model"], response.get("model"), identity):
            raise ValueError("returned model identity does not bind to requested pinned model")
        if response.get("provider") != endpoint["provider_name"]:
            raise ValueError("returned provider identity mismatch")
        if not response.get("id"):
            raise ValueError("provider response identity missing")
        billing_verified = True
        choice = (response.get("choices") or [])[0]
        finish_reason = choice.get("finish_reason")
        content = choice.get("message", {}).get("content", "")
        attempt["finish_reason"] = finish_reason
        attempt["response_text"] = content
        if finish_reason != "stop":
            raise ValueError("review incomplete or truncated")
        raw = review._clean_json(content)
        if raw is None:
            raise ValueError("review response is not valid JSON")
        if phase in ("BLIND", "RECONCILE"):
            finding = review.validate_independent(raw, target_id=target["target_id"], family=family, model_id=model["model"])
            context_capsule.validate_context_verdict(finding)
        else:
            finding = protocol.validate_final_review(
                raw,
                family=family,
                model_id=model["model"],
                candidate_sha256=directive["merged_candidate_sha256"],
                phase=phase,
                audit_packet=protocol.synthesis_audit_packet(cycle, directive, families),
            )
        requests = finding.get('requested_context') or []
        if not isinstance(requests, list) or len(requests) > 12:
            raise ValueError('invalid requested-context list')
        if requests:
            state.setdefault('context_request_queue', []).append({
                'task_key': task_key, 'cycle': cycle_id, 'family': family,
                'source_packet_sha256': source_packet_hash, 'requests': requests,
                'status': 'AWAITING_CHATGPT_SHARED_PACKET_REBUILD', 'no_peer_answer_sharing': True})
            attempt['requested_context'] = requests
        finding_hash = protocol.sha256_value(finding)
        record = {
            "family": family,
            "model": model["model"],
            "phase": phase,
            "finding": finding,
            "finding_sha256": finding_hash,
            "response_id": response["id"],
            "prompt_sha256": prompt_hash,
            "candidate_sha256": directive.get("merged_candidate_sha256"),
            "architecture_context_capsule_sha256": capsule_hash,
            "context_expansion_level": expansion_level,
            "peer_content_seen": phase in ("FINAL", "CONFIRM"),
            "evidence_stage": "POST_BLIND_SYNTHESIS_AUDIT" if phase in ("FINAL", "CONFIRM") else "ISOLATED_BRANCH",
            "synthesis_audit_sha256": attempt.get("synthesis_audit_sha256"),
        }
        if phase == "BLIND":
            cycle["blind"][family] = record
        elif phase == "RECONCILE":
            cycle["reconcile"].setdefault(family, []).append(record)
        elif phase == "FINAL":
            cycle["final"][family] = record
        else:
            cycle["confirm"][family] = record
        if finding.get("context_sufficiency") != "SUFFICIENT" or requests:
            cycle["context_expansion_required"] = {
                "status": finding["context_sufficiency"],
                "requested_by_family": family,
                "phase": phase,
                "missing_context_reason": finding.get("missing_context_reason", ""),
                "requested_dependency_or_source_refs": finding.get("requested_dependency_or_source_refs", []),
                "previous_context_capsule_sha256": capsule_hash,
                "previous_context_expansion_level": expansion_level,
                "rule": "EXPAND_CONTEXT_AND_RESTART_ALL_FOUR_INITIAL_BRANCHES_ON_A_NEW_SOURCE_PACKET",
            }
        attempt.update(status="REVIEW_RECORDED", finding_sha256=finding_hash)
    except Exception as exc:
        if isinstance(exc, error.HTTPError):
            legacy.record_http_failure(attempt, exc)
        attempt.update(status="INCOMPLETE" if billing_verified else "UNKNOWN", error_type=type(exc).__name__)

    state["continuation"] = {
        "status": _result_status(cycle, phase, families) if attempt["status"] == "REVIEW_RECORDED" else "BLOCKED",
        "reason": attempt["status"],
        "cycle": cycle_id,
        "updated": time.time(),
    }
    if attempt.get('requested_context') and attempt['status'] == 'REVIEW_RECORDED':
        state['continuation']['status'] = 'AWAITING_CHATGPT_CONTEXT'
    out = root / "agents/outbox/single-review/receipt.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(protocol.canonical_json(attempt) + "\n", encoding="utf-8")
    ledger.save(state)
    print(attempt["status"] + ": " + family + " " + phase + "; isolated proposal evidence only")
    if state["continuation"]["status"] == "BLOCKED":
        raise SystemExit(2)


def execute(root: Path = Path(".")) -> None:
    try:
        run(root)
    except Exception as exc:
        try:
            legacy.host_check()
            token = os.environ.get("GH_REVIEW_TOKEN")
            if token:
                ledger = legacy.GitLedger(token)
                ledger.value["continuation"] = {
                    "status": "DEFERRED_DAILY" if isinstance(exc, legacy.DailyBudget) else "BLOCKED",
                    "resume_after": (int(time.time()) // 86400 + 1) * 86400,
                    "reason": str(exc) if type(exc) is ValueError else type(exc).__name__,
                    "updated": time.time(),
                    "run_id": os.environ.get("GITHUB_RUN_ID"),
                }
                ledger.save(ledger.value)
        except Exception:
            pass
        print("INDEPENDENT_BRANCH_WORKER_STOPPED: " + type(exc).__name__ + "; no retry authorized")
        raise SystemExit(2)


if __name__ == "__main__":
    execute()
