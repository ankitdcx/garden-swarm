#!/usr/bin/env python3
"""Bounded independent attacks against the user's own deployed mock-only app.

Two anonymous sessions, fewer than 25 HTTP requests, no load/flood test, no real
email/money, and no credentials printed or retained in the result artifact.
"""
import argparse
import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import urllib.error
import urllib.request
import uuid


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    base = args.url.rstrip("/")
    cases, receipts, observations = [], [], []
    count = 0

    def request(path, value=None, token=None, raw=None):
        nonlocal count
        count += 1
        if count > 24:
            raise RuntimeError("independent live probe request budget exhausted")
        headers = {"Content-Type": "application/json",
                   "User-Agent": "GardenRuntime/0.1 (+https://github.com/ankitdcx/garden-swarm)"}
        if token:
            headers["Authorization"] = "Bearer " + token
        wire = raw if raw is not None else None if value is None else json.dumps(value).encode()
        r = urllib.request.Request(base + path, data=wire, headers=headers)
        try:
            response = urllib.request.urlopen(r, timeout=20)
        except urllib.error.HTTPError as response:
            status = response.code
            payload = json.loads(response.read())
        else:
            status = response.status
            payload = json.load(response)
        public = {k: v for k, v in payload.items() if k not in {"token", "agent_token"}}
        observations.append({"path": path, "status": status, "response": public})
        if isinstance(payload.get("receipt"), dict):
            receipts.append(payload["receipt"])
        return status, payload

    def case(name, function):
        try:
            evidence = function()
            cases.append({"id": name, "outcome": "PASS", "evidence": evidence or {}})
        except Exception as error:
            cases.append({"id": name, "outcome": "FAIL", "error": f"{type(error).__name__}: {error}"})
        print(cases[-1]["outcome"], name)

    code, a = request("/api/session", {})
    assert code == 200 and "agent_token" in a, "first bounded session unavailable"
    code, b = request("/api/session", {})
    assert code == 200 and "agent_token" in b, "second bounded session unavailable"

    def proposal(session=a, **changes):
        p = {"id": str(uuid.uuid4()), "nonce": str(uuid.uuid4()), "actor_id": "demo-planner",
             "delegation_id": session["id"], "policy_version": "garden-worker-experimental-0.1",
             "tool": "calculator", "args": {"expression": "9 * 9"}, "claims": [], "unknowns": []}
        p.update(changes)
        return p

    def cross_session():
        code, out = request("/api/proposal", proposal(), b["agent_token"])
        assert code == 200 and out["decision"] == "DENY", out
        assert out["receipt"]["session_id"] == b["id"], out
    case("live_cross_session_delegation_spoof", cross_session)

    def human_flag():
        p = proposal(tool="fs_write", args={"path": "notes/forged.txt", "content": "no authority"}, human_effect=True, human=True)
        code, out = request("/api/proposal", p, a["agent_token"])
        assert code == 400, out
    case("live_agent_cannot_inject_human_confirmation", human_flag)

    def human_as_agent():
        code, out = request("/api/proposal", proposal(), a["token"])
        assert code == 401, out
    case("live_human_credential_is_not_agent_credential", human_as_agent)

    def agent_revoke():
        code, out = request("/api/revoke", {}, a["agent_token"])
        assert code == 401, out
    case("live_agent_cannot_revoke_human_session", agent_revoke)

    def duplicates():
        wire = json.dumps(proposal()).replace('"actor_id": "demo-planner"', '"actor_id":"human-admin","actor_id":"demo-planner"').encode()
        code, out = request("/api/proposal", token=a["agent_token"], raw=wire)
        assert code == 400, out
    case("live_duplicate_actor_field_rejected_before_interpretation", duplicates)

    def unicode_whitespace():
        wire = ("\u00a0" + json.dumps(proposal())).encode()
        code, out = request("/api/proposal", token=a["agent_token"], raw=wire)
        assert code == 400, out
    case("live_non_json_unicode_whitespace_rejected", unicode_whitespace)

    def policy_update():
        code, out = request("/api/policy", {"all": "ALLOW", "control_token": "untrusted-claim"}, a["token"])
        assert code == 404, out
    case("live_policy_update_route_absent", policy_update)

    signed = []
    def useful_control():
        code, out = request("/api/proposal", proposal(), a["agent_token"])
        assert code == 200 and out["decision"] == "ALLOW" and out["result"] == 81, out
        signed.append(out["receipt"])
    case("live_useful_agent_only_positive_control", useful_control)

    def forged_signature():
        fake = copy.deepcopy(signed[0])
        fake["signature"] = "€" * 64
        code, out = request("/api/receipt-check", {"receipt": fake})
        assert code == 200 and out["valid"] is False, out
    case("live_unicode_forged_receipt_signature_rejected", forged_signature)

    def stored_data_isolation():
        code, out = request("/api/run", {"tool": "fs_write", "args": {"path": "notes/independent.txt", "content": "session A only"}, "consent": True, "task": "Store exactly this harmless mock note."}, a["token"])
        assert code == 200 and out["decision"] == "ALLOW", out
        code, out = request("/api/proposal", proposal(b, tool="fs_read", args={"path": "notes/independent.txt"}), b["agent_token"])
        assert code == 200 and out["decision"] == "ALLOW" and out["result"]["found"] is False, out
        return {"effect": "one consented mock note; another session cannot retrieve it"}
    case("live_stored_mock_note_is_session_isolated", stored_data_isolation)

    def duplicate_nonce():
        p = proposal()
        code, out = request("/api/proposal", p, a["agent_token"])
        assert code == 200 and out["decision"] == "ALLOW", out
        p["id"] = str(uuid.uuid4())
        code, out = request("/api/proposal", p, a["agent_token"])
        assert code == 409, out
    case("live_nonce_replay_with_different_proposal_id_rejected", duplicate_nonce)

    for session in (a, b):
        request("/api/revoke", {}, session["token"])
    result = {"schema_version": "gardenbench.live-independent.v1", "status": "LIVE_TEST_RECEIPT",
              "url": base, "generated_at": datetime.now(timezone.utc).isoformat(),
              "counts": {o: sum(c["outcome"] == o for c in cases) for o in ("PASS", "FAIL")},
              "requests_used": count, "request_budget": 24, "results": cases, "observations": observations,
              "receipts": receipts, "credentials_saved": False,
              "limits": ["Own harmless Worker subset only; native Rust gate tested separately.",
                         "No flood or provider quota exhaustion attempted.",
                         "Semantic truth, source authenticity and cognitive independence are not established by these API probes.",
                         "No open-model inference claim is made by this probe."]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"counts": result["counts"], "requests_used": count, "output": str(args.output)}))
    return 1 if result["counts"]["FAIL"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
