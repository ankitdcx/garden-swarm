"""Sequential real-OpenRouter worker for repo-native GROUP_REVIEW runs.

One GitHub Actions dispatch performs at most one external inference. A successful
record dispatches the same workflow for the next governed reviewer family. The
worker reads only the frozen public GROUP_REVIEW run issue; peer findings are
never included in blind prompts.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
import re
import time
from urllib import error
from urllib.parse import quote

from tools import group_review_bus as bus
from tools import matrix_design_review as review
from tools import select_paid_matrix_reviewers as selector
from tools import single_review_worker as legacy
from tools.provider_exclusion import load_policy

REPO = legacy.REPO
API = legacy.API
STATE_BRANCH = legacy.STATE_BRANCH
STATE_PATH = "review-state/group-review-ledger.json"
LEDGER_SCHEMA = "GardenGroupReviewOpenRouterLedger/v1"
PROVIDER_WORKFLOW = "group-review-openrouter.yml"
TRIGGER_WORKFLOW = "group-review-openrouter-trigger.yml"
MAX_FINDING_CHARS = 10000


class GroupReviewLedger:
    def __init__(self, token: str):
        self.token = token
        result = legacy.http(API + "/contents/" + STATE_PATH + "?ref=" + STATE_BRANCH, token)
        self.sha = result["sha"]
        content = result.get("content")
        if not content:
            result = legacy.http(API + "/git/blobs/" + self.sha, token)
            content = result.get("content")
        if not content:
            raise ValueError("GROUP_REVIEW ledger has no content")
        self.value = json.loads(base64.b64decode(content))
        if self.value.get("schema") != LEDGER_SCHEMA or self.value.get("repository") != REPO:
            raise ValueError("unrecognized GROUP_REVIEW ledger")

    def save(self, value: dict) -> None:
        raw = bus.canonical_json(value) + "\n"
        if len(raw.encode("utf-8")) > 8_000_000:
            raise ValueError("GROUP_REVIEW ledger capacity reached")
        result = legacy.http(
            API + "/contents/" + STATE_PATH,
            self.token,
            {
                "message": "Record GROUP_REVIEW OpenRouter state",
                "branch": STATE_BRANCH,
                "sha": self.sha,
                "content": base64.b64encode(raw.encode("utf-8")).decode(),
            },
            method="PUT",
        )
        self.sha = result["content"]["sha"]
        self.value = value


def _event_payload() -> dict:
    path = os.environ.get("GITHUB_EVENT_PATH")
    if not path:
        raise ValueError("GitHub event payload unavailable")
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("invalid GitHub event payload")
    return value


def trigger_issue_number() -> int:
    if os.environ.get("GITHUB_REPOSITORY") != REPO or os.environ.get("GITHUB_REF") != "refs/heads/main":
        raise ValueError("GROUP_REVIEW OpenRouter worker requires installed main")
    event_name = os.environ.get("GITHUB_EVENT_NAME")
    payload = _event_payload()
    owner = os.environ.get("GITHUB_REPOSITORY_OWNER")
    actor = os.environ.get("GITHUB_ACTOR")
    expected_provider = REPO + "/.github/workflows/" + PROVIDER_WORKFLOW + "@refs/heads/main"
    expected_trigger = REPO + "/.github/workflows/" + TRIGGER_WORKFLOW + "@refs/heads/main"

    if event_name == "issues":
        if os.environ.get("GITHUB_WORKFLOW_REF") != expected_trigger:
            raise ValueError("unregistered GROUP_REVIEW issue trigger workflow")
        if payload.get("action") != "opened":
            raise ValueError("only opened run issues may start GROUP_REVIEW OpenRouter")
        issue = payload.get("issue") or {}
        if actor != owner or (issue.get("user") or {}).get("login") != owner:
            raise ValueError("only repository owner may start GROUP_REVIEW OpenRouter")
        title = str(issue.get("title") or "")
        if not title.startswith(bus.RUN_TITLE_PREFIX + " "):
            raise ValueError("issue is not a GROUP_REVIEW run")
        number = int(issue.get("number", 0))
    elif event_name == "workflow_dispatch":
        if os.environ.get("GITHUB_WORKFLOW_REF") != expected_provider:
            raise ValueError("unregistered GROUP_REVIEW provider workflow")
        if actor not in {owner, "github-actions[bot]"}:
            raise ValueError("GROUP_REVIEW continuation actor not admitted")
        number = int((payload.get("inputs") or {}).get("trigger_issue_number", 0))
    else:
        raise ValueError("unsupported GROUP_REVIEW OpenRouter event")

    if number <= 0:
        raise ValueError("trigger issue number required")
    return number


def fetch_run_issue(token: str, issue_number: int) -> tuple[dict, dict]:
    issue = legacy.http(API + f"/issues/{issue_number}", token)
    owner = os.environ.get("GITHUB_REPOSITORY_OWNER") or REPO.split("/", 1)[0]
    packet = bus.validate_run_issue(issue, owner)
    if packet.get("openrouter_requested") is not True:
        raise ValueError("run issue did not request OpenRouter")
    return issue, packet


def _config(root: Path) -> tuple[dict, list[dict], dict]:
    policy = json.loads((root / "agents/openrouter-paid-review-policy.json").read_text(encoding="utf-8"))
    registry = json.loads((root / "agents/reviewer-slot-registry.json").read_text(encoding="utf-8"))
    exclusions = load_policy(root / "agents/provider-exclusion-policy.json")
    selected = selector.active_reviewers(policy, registry, exclusions)
    if int(policy["execution_limits"]["max_model_calls_per_dispatch"]) != 1:
        raise ValueError("GROUP_REVIEW requires one OpenRouter call per dispatch")
    if int(policy["execution_limits"]["max_concurrent_model_calls"]) != 1:
        raise ValueError("GROUP_REVIEW OpenRouter calls must remain sequential")
    return policy, selected, exclusions



_REPO_SOURCE_RE = re.compile(
    r"^repo:([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)@([0-9a-f]{40}):(.+)$"
)


def _repo_source_parts(source_ref: str) -> tuple[str, str, str]:
    match = _REPO_SOURCE_RE.fullmatch(source_ref)
    if not match:
        raise ValueError(
            "automatic OpenRouter GROUP_REVIEW requires exact-commit repo source_refs"
        )
    source_repo = match.group(1) + "/" + match.group(2)
    if source_repo != REPO:
        raise ValueError("automatic OpenRouter cross-repository source is not supported")
    return match.group(3), match.group(4), source_repo


def _github_source_bytes(token: str, *, commit: str, path: str) -> bytes:
    encoded_path = quote(path, safe="/")
    result = legacy.http(API + "/contents/" + encoded_path + "?ref=" + commit, token)
    if not isinstance(result, dict) or result.get("type") not in {None, "file"}:
        raise ValueError("frozen source_ref did not resolve to a file")
    content = result.get("content")
    if not content:
        blob_sha = result.get("sha")
        if not blob_sha:
            raise ValueError("frozen source file has no content or blob SHA")
        result = legacy.http(API + "/git/blobs/" + str(blob_sha), token)
        content = result.get("content")
    if not content:
        raise ValueError("frozen source file content unavailable")
    try:
        return base64.b64decode(content, validate=False)
    except Exception as exc:
        raise ValueError("frozen source file is not valid base64 content") from exc


def materialize_frozen_sources(
    packet: dict, token: str, *, max_characters: int
) -> str:
    """Fetch every frozen repo source, verify exact SHA-256 bytes, and render text.

    Automatic OpenRouter review deliberately refuses inline/content-only or
    cross-repository refs because the installed GitHub execution host cannot
    independently retrieve and re-hash those bytes under this contract.
    """

    bus.validate_packet(packet)
    if max_characters <= 0:
        raise ValueError("positive source-bundle bound required")
    parts: list[str] = []
    total = 0
    for source_ref in packet["source_refs"]:
        commit, path, _ = _repo_source_parts(source_ref)
        raw = _github_source_bytes(token, commit=commit, path=path)
        actual = hashlib.sha256(raw).hexdigest()
        expected = packet["source_hashes"][source_ref]
        if actual != expected:
            raise ValueError("frozen source SHA-256 mismatch")
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("automatic OpenRouter source must be strict UTF-8 text") from exc
        rendered = (
            "\n===== FROZEN SOURCE =====\n"
            + source_ref
            + "\nsha256:"
            + actual
            + "\n"
            + text
            + "\n===== END FROZEN SOURCE =====\n"
        )
        total += len(rendered)
        if total > max_characters:
            raise ValueError("frozen source bundle exceeds full-prompt bound; no truncation")
        parts.append(rendered)
    if not parts:
        raise ValueError("OpenRouter review requires at least one frozen source")
    return "".join(parts)


def cycle_id(packet: dict, selected: list[dict], policy: dict) -> str:
    return bus.sha256_value(
        {
            "protocol": "GardenGroupReviewOpenRouter/v1",
            "packet_sha256": packet["packet_sha256"],
            "reviewers": selected,
            "policy_sha256": bus.sha256_value(policy),
        }
    )


def next_reviewer(cycle: dict, selected: list[dict]) -> dict | None:
    findings = cycle.get("findings") or {}
    for row in selected:
        if row["family"] not in findings:
            return row
    return None


def _model_identity_matches(requested: str, actual: str | None, identity: dict | None) -> bool:
    return actual == requested or bool(
        identity and identity.get("id") == requested and identity.get("canonical_slug") == actual
    )


def _profile(policy: dict) -> dict:
    routine = dict((policy.get("review_profiles") or {}).get("ROUTINE") or {})
    return {
        "max_output_tokens": min(int(routine.get("max_output_tokens", 8000)), 4000),
        "reasoning_effort": routine.get("reasoning_effort", "medium"),
        "request_timeout_seconds": min(int(routine.get("request_timeout_seconds", 180)), 180),
    }


def preflight(root: Path = Path(".")) -> tuple[int, dict]:
    issue_number = trigger_issue_number()
    gh = os.environ.get("GH_REVIEW_TOKEN")
    if not gh:
        raise ValueError("GitHub review token unavailable")
    _, packet = fetch_run_issue(gh, issue_number)
    ledger = GroupReviewLedger(gh)
    if ledger.value.get("paused") is not False:
        raise ValueError("GROUP_REVIEW OpenRouter ledger paused")
    policy, selected, _ = _config(root)
    if len(selected) != 5:
        raise ValueError("GROUP_REVIEW requires five governed OpenRouter families")
    if packet["triage"] not in {"MATERIAL", "HIGH_RISK"}:
        raise ValueError("OpenRouter GROUP_REVIEW requires MATERIAL/HIGH_RISK")
    return issue_number, packet


def _publish_result_issue(gh: str, packet: dict, issue_number: int, cycle: dict, selected: list[dict]) -> int:
    existing = cycle.get("result_issue_number")
    if existing:
        return int(existing)
    records = [cycle["findings"][row["family"]] for row in selected]
    bundle = bus.make_openrouter_bundle(packet=packet, run_issue_number=issue_number, records=records)
    body = bus.render_issue(bus.OPENROUTER_MARKER, bundle)
    if len(body) > 64000:
        raise ValueError("OpenRouter result issue exceeds GitHub issue bound")
    result = legacy.http(
        API + "/issues",
        gh,
        {
            "title": f"{bus.OPENROUTER_RESULT_TITLE_PREFIX} {packet['problem_id']}",
            "body": body,
        },
    )
    number = int(result.get("number", 0))
    if number <= 0:
        raise ValueError("OpenRouter result issue creation failed")
    cycle["result_issue_number"] = number
    cycle["bundle_sha256"] = bundle["bundle_sha256"]
    return number


def _dispatch_next(gh: str, issue_number: int) -> None:
    legacy.http(
        API + "/actions/workflows/" + PROVIDER_WORKFLOW + "/dispatches",
        gh,
        {"ref": "main", "inputs": {"trigger_issue_number": str(issue_number)}},
    )


def run(root: Path = Path(".")) -> None:
    issue_number, packet = preflight(root)
    key = os.environ.get("OPENROUTER_API_KEY")
    gh = os.environ.get("GH_REVIEW_TOKEN")
    if not key or not gh:
        raise ValueError("required OpenRouter/GitHub credentials unavailable")

    policy, selected, exclusions = _config(root)
    ledger = GroupReviewLedger(gh)
    state = ledger.value
    cid = cycle_id(packet, selected, policy)
    cycles = state.setdefault("cycles", {})
    cycle = cycles.setdefault(
        cid,
        {
            "protocol": "GardenGroupReviewOpenRouter/v1",
            "problem_id": packet["problem_id"],
            "run_issue_number": issue_number,
            "packet_sha256": packet["packet_sha256"],
            "reviewer_families": [row["family"] for row in selected],
            "findings": {},
            "attempts": [],
            "semantic_delta_admitted": False,
            "status": "BLIND_IN_PROGRESS",
        },
    )
    if cycle.get("run_issue_number") != issue_number or cycle.get("packet_sha256") != packet["packet_sha256"]:
        raise ValueError("GROUP_REVIEW cycle binding mismatch")

    blocking = [
        attempt
        for attempt in state.get("attempts", [])
        if attempt.get("cycle") == cid
        and attempt.get("status") in {"UNKNOWN", "RESERVED", "INCOMPLETE"}
    ]
    if blocking:
        raise ValueError("prior GROUP_REVIEW OpenRouter call requires explicit reconciliation; no silent retry")

    reviewer = next_reviewer(cycle, selected)
    if reviewer is None:
        _publish_result_issue(gh, packet, issue_number, cycle, selected)
        cycle["status"] = "BLIND_COMPLETE"
        ledger.save(state)
        print("GROUP_REVIEW_OPENROUTER_COMPLETE")
        return

    model = reviewer["model"]
    family = reviewer["family"]
    base_prompt = bus.openrouter_prompt(
        packet, family=family, role=reviewer["role"], model=model
    )
    prompt_cap = min(int(policy["max_prompt_characters"]), 200000)
    source_budget = prompt_cap - len(base_prompt) - 512
    source_bundle = materialize_frozen_sources(
        packet, gh, max_characters=source_budget
    )
    prompt = (
        base_prompt
        + "\nThe following source bundle is the exact SHA-256-verified content "
        + "you must review. Do not infer missing source text from filenames.\n"
        + source_bundle
    )
    if len(prompt) > prompt_cap:
        raise ValueError("full GROUP_REVIEW prompt exceeds configured bound")
    prompt_sha = bus.sha256_text(prompt)
    source_bundle_sha = bus.sha256_text(source_bundle)

    key_info = legacy.http(legacy.OR + "/key", key)["data"]
    reserve, day, daily = legacy.budget_check(state, key_info, policy, time.time())
    identity = legacy.model_identity(key, model)
    endpoints = legacy.http(legacy.OR + "/models/" + model + "/endpoints", key)["data"]["endpoints"]
    eligible = []
    profile = _profile(policy)
    for endpoint in endpoints:
        try:
            body, estimate = legacy.endpoint_request(
                endpoint,
                reviewer,
                prompt,
                reserve,
                policy,
                exclusions,
                profile=profile,
                model_capabilities=identity,
            )
            eligible.append((legacy.money(estimate), endpoint, body))
        except (ValueError, KeyError, RuntimeError):
            continue
    if not eligible:
        raise ValueError("no permitted affordable GROUP_REVIEW OpenRouter endpoint")
    estimate, endpoint, request_body = min(eligible, key=lambda row: row[0])

    attempt = {
        "protocol": "GardenGroupReviewOpenRouter/v1",
        "inference_reserved": True,
        "status": "RESERVED",
        "cycle": cid,
        "slot": "blind:" + family,
        "family": family,
        "model": model,
        "model_identity": identity,
        "expected_provider": endpoint["provider_name"],
        "endpoint": endpoint["tag"],
        "problem_id": packet["problem_id"],
        "run_issue_number": issue_number,
        "packet_sha256": packet["packet_sha256"],
        "prompt_sha256": prompt_sha,
        "source_bundle_sha256": source_bundle_sha,
        "source_ref_count": len(packet["source_refs"]),
        "utc_day": day,
        "started": time.time(),
        "usage_daily_before": daily,
        "reserved": str(reserve),
        "estimated_upper_cost": str(estimate),
        "cost": None,
        "semantic_delta_admitted": False,
    }
    state.setdefault("attempts", []).append(attempt)
    cycle["attempts"].append({"family": family, "attempt_index": len(state["attempts"]) - 1})
    ledger.save(state)

    billing_verified = False
    try:
        response = legacy.http(
            legacy.OR + "/chat/completions",
            key,
            request_body,
            timeout=profile["request_timeout_seconds"],
        )
        attempt.update(
            response_id=response.get("id"),
            actual_model=response.get("model"),
            actual_provider=response.get("provider"),
            usage=response.get("usage"),
        )
        cost = legacy.money((response.get("usage") or {}).get("cost"))
        attempt["cost"] = str(cost)
        if cost > reserve:
            raise ValueError("GROUP_REVIEW cost exceeds reservation")
        if not _model_identity_matches(model, response.get("model"), identity):
            raise ValueError("GROUP_REVIEW returned model identity mismatch")
        if response.get("provider") != endpoint["provider_name"]:
            raise ValueError("GROUP_REVIEW provider identity mismatch")
        if not response.get("id"):
            raise ValueError("GROUP_REVIEW provider response identity missing")
        billing_verified = True

        choice = (response.get("choices") or [])[0]
        finish = choice.get("finish_reason")
        raw_text = choice.get("message", {}).get("content", "")
        attempt["finish_reason"] = finish
        attempt["response_text_sha256"] = bus.sha256_text(raw_text)
        if finish != "stop":
            raise ValueError("GROUP_REVIEW review incomplete or truncated")
        if len(raw_text) > MAX_FINDING_CHARS + 2000:
            raise ValueError("GROUP_REVIEW raw response exceeds compact bound")
        finding = review._clean_json(raw_text)
        if not isinstance(finding, dict):
            raise ValueError("GROUP_REVIEW response must be JSON object")
        bus.validate_openrouter_finding(finding, packet=packet, family=family, model=model)
        finding_hash = bus.sha256_value(finding)
        record = {
            "family": family,
            "model": model,
            "provider": response.get("provider"),
            "response_id": response["id"],
            "prompt_sha256": prompt_sha,
            "source_bundle_sha256": source_bundle_sha,
            "source_ref_count": len(packet["source_refs"]),
            "finding": finding,
            "finding_sha256": finding_hash,
            "cost_usd": str(cost),
            "peer_content_seen": False,
        }
        cycle["findings"][family] = record
        attempt.update(status="REVIEW_RECORDED", finding_sha256=finding_hash)
    except Exception as exc:
        if isinstance(exc, error.HTTPError):
            legacy.record_http_failure(attempt, exc)
        attempt.update(
            status="INCOMPLETE" if billing_verified else "UNKNOWN",
            error_type=type(exc).__name__,
        )
        cycle["status"] = "BLOCKED"
        ledger.save(state)
        print("GROUP_REVIEW_OPENROUTER_BLOCKED:" + type(exc).__name__)
        raise SystemExit(2)

    if next_reviewer(cycle, selected) is None:
        _publish_result_issue(gh, packet, issue_number, cycle, selected)
        cycle["status"] = "BLIND_COMPLETE"
        ledger.save(state)
        print("GROUP_REVIEW_OPENROUTER_COMPLETE")
        return

    cycle["status"] = "BLIND_IN_PROGRESS"
    ledger.save(state)
    _dispatch_next(gh, issue_number)
    print("GROUP_REVIEW_OPENROUTER_NEXT_DISPATCHED:" + family)


def execute(mode: str, root: Path = Path(".")) -> None:
    if mode == "preflight":
        issue_number, packet = preflight(root)
        print(f"GROUP_REVIEW_PREFLIGHT_OK:{issue_number}:{packet['packet_sha256']}")
        return
    if mode == "dispatch":
        issue_number, packet = preflight(root)
        gh = os.environ.get("GH_REVIEW_TOKEN")
        if not gh:
            raise ValueError("GitHub review token unavailable")
        _dispatch_next(gh, issue_number)
        print(f"GROUP_REVIEW_PROVIDER_DISPATCHED:{issue_number}:{packet['packet_sha256']}")
        return
    if mode != "run":
        raise ValueError("mode must be preflight, dispatch or run")
    run(root)


if __name__ == "__main__":
    import sys

    try:
        execute(sys.argv[1] if len(sys.argv) > 1 else "run")
    except SystemExit:
        raise
    except Exception as exc:
        print("GROUP_REVIEW_OPENROUTER_STOPPED:" + type(exc).__name__)
        raise SystemExit(2)
