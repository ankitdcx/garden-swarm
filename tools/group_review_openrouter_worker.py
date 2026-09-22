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
from datetime import datetime, timezone
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
PUSH_TRIGGER_WORKFLOW = "group-review-openrouter-push-trigger.yml"
MAX_FINDING_CHARS = 10000
PUSH_REQUEST_SCHEMA = "GardenGroupReviewDispatchRequest/v1"
PUSH_REQUEST_PATH = Path("review-state/group-review-dispatch-request.json")


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


def _push_dispatch_request() -> dict:
    if not PUSH_REQUEST_PATH.exists():
        raise ValueError("GROUP_REVIEW push dispatch request missing")
    value = json.loads(PUSH_REQUEST_PATH.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("schema") != PUSH_REQUEST_SCHEMA:
        raise ValueError("invalid GROUP_REVIEW push dispatch request")
    if value.get("status") != "REQUESTED":
        raise ValueError("GROUP_REVIEW push dispatch request is not active")
    issue_number = int(value.get("run_issue_number", 0))
    if issue_number <= 0:
        raise ValueError("GROUP_REVIEW push dispatch issue number required")
    packet_sha = str(value.get("packet_sha256") or "")
    if not re.fullmatch(r"[0-9a-f]{64}", packet_sha):
        raise ValueError("GROUP_REVIEW push dispatch packet SHA-256 invalid")
    return value


def validate_push_dispatch_binding(
    request: dict, issue_number: int, packet: dict
) -> None:
    if int(request.get("run_issue_number", 0)) != issue_number:
        raise ValueError("GROUP_REVIEW push dispatch issue binding mismatch")
    if request.get("packet_sha256") != packet.get("packet_sha256"):
        raise ValueError("GROUP_REVIEW push dispatch packet binding mismatch")


def trigger_issue_number() -> int:
    if os.environ.get("GITHUB_REPOSITORY") != REPO or os.environ.get("GITHUB_REF") != "refs/heads/main":
        raise ValueError("GROUP_REVIEW OpenRouter worker requires installed main")
    event_name = os.environ.get("GITHUB_EVENT_NAME")
    payload = _event_payload()
    owner = os.environ.get("GITHUB_REPOSITORY_OWNER")
    actor = os.environ.get("GITHUB_ACTOR")
    expected_provider = REPO + "/.github/workflows/" + PROVIDER_WORKFLOW + "@refs/heads/main"
    expected_trigger = REPO + "/.github/workflows/" + TRIGGER_WORKFLOW + "@refs/heads/main"
    expected_push_trigger = REPO + "/.github/workflows/" + PUSH_TRIGGER_WORKFLOW + "@refs/heads/main"

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
    elif event_name == "push":
        if os.environ.get("GITHUB_WORKFLOW_REF") != expected_push_trigger:
            raise ValueError("unregistered GROUP_REVIEW push trigger workflow")
        if actor not in {owner, "github-actions[bot]"}:
            raise ValueError("GROUP_REVIEW push trigger actor not admitted")
        request = _push_dispatch_request()
        number = int(request["run_issue_number"])
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
    failures = cycle.get("reviewer_failures") or {}
    # A provider that returned a billed but unusable response must not starve
    # the other independent cheap reviewers. DeepSeek is attempted last while
    # its current endpoint returns null textual content.
    ordered = sorted(selected, key=lambda row: (row.get("family") == "deepseek", selected.index(row)))
    for row in ordered:
        if row["family"] not in findings and row["family"] not in failures:
            return row
    return None


def _model_identity_matches(requested: str, actual: str | None, identity: dict | None) -> bool:
    return actual == requested or bool(
        identity and identity.get("id") == requested and identity.get("canonical_slug") == actual
    )


def _endpoint_rejection_code(exc: Exception) -> str:
    if isinstance(exc, KeyError):
        return "ENDPOINT_METADATA_MISSING"
    if isinstance(exc, RuntimeError):
        return "ENDPOINT_RUNTIME_REJECTED"
    text = str(exc).lower()
    rules = (
        ("unavailable or unidentified", "ENDPOINT_UNAVAILABLE"),
        ("excluded endpoint", "ENDPOINT_EXCLUDED"),
        ("excluded", "MODEL_OR_PROVIDER_EXCLUDED"),
        ("above routing price cap", "PRICE_CAP"),
        ("additional endpoint fees unsupported", "ADDITIONAL_FEES"),
        ("cannot satisfy requested review output depth", "OUTPUT_DEPTH"),
        ("cannot fit the full review prompt", "PROMPT_LIMIT"),
        ("exceeds reserved cost/context", "RESERVE_OR_CONTEXT"),
        ("context too large", "PROMPT_POLICY_BOUND"),
        ("cannot satisfy requested reasoning effort", "REASONING_EFFORT"),
    )
    for needle, code in rules:
        if needle in text:
            return code
    return "ENDPOINT_POLICY_REJECTED"


def _budget_rejection_code(exc: Exception) -> str:
    text = str(exc).lower()
    rules = (
        ("paid inference key required", "KEY_TYPE_NOT_PAID"),
        ("daily reservation exhausted", "DAILY_BUDGET_EXHAUSTED"),
        ("key credit limit too low", "KEY_CREDIT_LIMIT_TOO_LOW"),
        ("unknown monetary value", "KEY_USAGE_UNKNOWN"),
        ("invalid monetary value", "KEY_USAGE_INVALID"),
        ("outstanding reservation/unknown cost", "OUTSTANDING_RESERVATION"),
        ("single worker paused", "WORKER_PAUSED"),
    )
    for needle, code in rules:
        if needle in text:
            return code
    return "BUDGET_POLICY_REJECTED"


def group_review_budget_check(
    state: dict,
    key_info: dict,
    policy: dict,
    now: float,
    *,
    cycle_id: str,
):
    """Enforce the controlling paid OpenRouter rule: USD 2/day, USD 0.01/call.

    Provider-reported current UTC-day usage is the spend source. The durable
    ledger still blocks unresolved RESERVED/UNKNOWN calls so a call cannot be
    silently double-spent while provider billing is uncertain. cycle_id is
    retained for interface compatibility but creates no task-specific budget.
    """

    if state.get("paused") is not False:
        raise ValueError("single worker paused")
    if legacy.review_campaign.blocking_attempts(state, None):
        raise ValueError("outstanding reservation/unknown cost; reconciliation required")
    if key_info.get("is_management_key") is True or key_info.get("is_free_tier") is True:
        raise ValueError("paid inference key required")

    reserve = legacy.money(policy["routine_model_call_cost_ceiling_usd"])
    daily_ceiling = legacy.money(policy["daily_openrouter_cost_ceiling_usd"])
    if reserve != legacy.money("0.05") or daily_ceiling != legacy.money("2"):
        raise ValueError("active OpenRouter budget rule must be USD 2/day and USD 0.05/call")

    usage_daily = legacy.money(key_info.get("usage_daily"))
    if usage_daily + reserve > daily_ceiling:
        raise legacy.DailyBudget("daily reservation exhausted")

    remaining = key_info.get("limit_remaining")
    if remaining is not None and legacy.money(remaining) < reserve:
        raise ValueError("key credit limit too low")

    day = datetime.fromtimestamp(now, timezone.utc).date().isoformat()
    return reserve, day, str(usage_daily), "OPENROUTER_2_USD_DAY_0_05_CALL"


def _profile(policy: dict) -> dict:
    routine = dict((policy.get("review_profiles") or {}).get("ROUTINE") or {})
    return {
        "max_output_tokens": min(int(routine.get("max_output_tokens", 8000)), 4000),
        "reasoning_effort": routine.get("reasoning_effort", "none"),
        "request_timeout_seconds": min(int(routine.get("request_timeout_seconds", 180)), 180),
    }


def preflight(root: Path = Path(".")) -> tuple[int, dict]:
    issue_number = trigger_issue_number()
    gh = os.environ.get("GH_REVIEW_TOKEN")
    if not gh:
        raise ValueError("GitHub review token unavailable")
    _, packet = fetch_run_issue(gh, issue_number)
    if os.environ.get("GITHUB_EVENT_NAME") == "push":
        request = _push_dispatch_request()
        validate_push_dispatch_binding(request, issue_number, packet)
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
            "reviewer_failures": {},
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
    print(
        "GROUP_REVIEW_PREFLIGHT:SOURCE_BUNDLE_OK:"
        + str(len(source_bundle.encode("utf-8")))
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

    try:
        key_response = legacy.http(legacy.OR + "/key", key)
        key_info = key_response["data"]
    except legacy.error.HTTPError as exc:
        print("GROUP_REVIEW_PREFLIGHT:KEY_INFO_HTTP:" + str(exc.code))
        raise
    except (KeyError, ValueError, TypeError):
        print("GROUP_REVIEW_PREFLIGHT:KEY_INFO_INVALID")
        raise
    print("GROUP_REVIEW_PREFLIGHT:KEY_INFO_OK")
    try:
        reserve, day, daily, budget_rule_id = group_review_budget_check(
            state, key_info, policy, time.time(), cycle_id=cid
        )
    except ValueError as exc:
        print(
            "GROUP_REVIEW_PREFLIGHT:BUDGET_REJECT:"
            + _budget_rejection_code(exc)
        )
        raise
    print("GROUP_REVIEW_PREFLIGHT:BUDGET_OK")
    identity = legacy.model_identity(key, model)
    print("GROUP_REVIEW_PREFLIGHT:MODEL_IDENTITY_OK")
    endpoints = legacy.http(legacy.OR + "/models/" + model + "/endpoints", key)["data"]["endpoints"]
    print("GROUP_REVIEW_PREFLIGHT:ENDPOINTS_DISCOVERED:" + str(len(endpoints)))
    eligible = []
    endpoint_rejections = []
    profile = _profile(policy)
    for endpoint in endpoints:
        try:
            endpoint_profile = dict(profile)
            if "reasoning" in endpoint.get("supported_parameters", []):
                supported = ((identity or {}).get("reasoning") or {}).get("supported_efforts")
                if supported and endpoint_profile.get("reasoning_effort") not in supported:
                    # Reasoning effort is a transport optimization, not review semantics.
                    # Prefer the least supported effort rather than rejecting an otherwise
                    # valid endpoint solely because the configured hint is unsupported.
                    endpoint_profile["reasoning_effort"] = supported[0]
            body, estimate = legacy.endpoint_request(
                endpoint,
                reviewer,
                prompt,
                reserve,
                policy,
                exclusions,
                profile=endpoint_profile,
                model_capabilities=identity,
            )
            eligible.append((legacy.money(estimate), endpoint, body))
        except (ValueError, KeyError, RuntimeError) as exc:
            endpoint_rejections.append(_endpoint_rejection_code(exc))
            continue
    if not eligible:
        codes = ",".join(sorted(set(endpoint_rejections))) or "NO_ENDPOINTS_RETURNED"
        print("GROUP_REVIEW_PREFLIGHT:NO_ELIGIBLE_ENDPOINT:" + codes)
        cycle.setdefault("reviewer_failures", {})[family] = {
            "stage": "ENDPOINT_SELECTION",
            "codes": sorted(set(endpoint_rejections)),
            "model": model,
            "cost_usd": "0",
        }
        ledger.save(state)
        if next_reviewer(cycle, selected) is not None:
            _dispatch_next(gh, issue_number)
            print("GROUP_REVIEW_OPENROUTER_NEXT_AFTER_UNAVAILABLE:" + family)
            return
        cycle["status"] = "PARTIAL_COMPLETE"
        ledger.save(state)
        print("GROUP_REVIEW_OPENROUTER_PARTIAL_COMPLETE")
        return
    print("GROUP_REVIEW_PREFLIGHT:ELIGIBLE_ENDPOINTS:" + str(len(eligible)))
    estimate, endpoint, request_body = min(eligible, key=lambda row: row[0])
    expected_provider = endpoint.get("provider_name")
    expected_endpoint = endpoint.get("tag")
    if not expected_provider or not expected_endpoint:
        raise ValueError("selected endpoint identity missing")

    attempt = {
        "protocol": "GardenGroupReviewOpenRouter/v1",
        "inference_reserved": True,
        "status": "RESERVED",
        "cycle": cid,
        "slot": "blind:" + family,
        "family": family,
        "model": model,
        "model_identity": identity,
        "expected_provider": expected_provider,
        "endpoint": expected_endpoint,
        "problem_id": packet["problem_id"],
        "run_issue_number": issue_number,
        "packet_sha256": packet["packet_sha256"],
        "prompt_sha256": prompt_sha,
        "source_bundle_sha256": source_bundle_sha,
        "source_ref_count": len(packet["source_refs"]),
        "utc_day": day,
        "started": time.time(),
        "usage_daily_before": daily,
        "budget_rule_id": budget_rule_id,
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
        if response.get("provider") != expected_provider:
            raise ValueError("GROUP_REVIEW provider identity mismatch")
        if not response.get("id"):
            raise ValueError("GROUP_REVIEW provider response identity missing")
        billing_verified = True

        choice = (response.get("choices") or [])[0]
        finish = choice.get("finish_reason")
        raw_text = choice.get("message", {}).get("content")
        if not isinstance(raw_text, str) or not raw_text.strip():
            raise ValueError("GROUP_REVIEW provider returned no textual review content")
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
        print("GROUP_REVIEW_EXCEPTION_DETAIL:" + type(exc).__name__ + ":" + str(exc)[:500])
        http_404 = isinstance(exc, legacy.error.HTTPError) and getattr(exc, "code", None) == 404
        null_content = isinstance(exc, ValueError) and "no textual review content" in str(exc)
        if isinstance(exc, legacy.error.HTTPError):
            legacy.record_http_failure(attempt, exc)
        if http_404 or (null_content and billing_verified):
            attempt.update(
                status="TRANSPORT_FAILED" if http_404 else "REVIEW_UNUSABLE",
                error_type=type(exc).__name__,
            )
            cycle.setdefault("reviewer_failures", {})[family] = {
                "stage": "INFERENCE_RESPONSE",
                "error_type": type(exc).__name__,
                "http_status": 404 if http_404 else None,
                "model": model,
                "cost_usd": attempt.get("cost") or "0",
                "reason": "HTTP_404" if http_404 else "NULL_TEXT_CONTENT",
            }
            ledger.save(state)
            if next_reviewer(cycle, selected) is not None:
                _dispatch_next(gh, issue_number)
                print("GROUP_REVIEW_OPENROUTER_NEXT_AFTER_FAILURE:" + family)
                return
            cycle["status"] = "PARTIAL_COMPLETE"
            ledger.save(state)
            print("GROUP_REVIEW_OPENROUTER_PARTIAL_COMPLETE")
            return
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
