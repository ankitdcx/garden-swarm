#!/usr/bin/env python3
"""Independent integration attacks against the actual Python HTTP controller.

Launches a fresh server subprocess for each case. Requests are real loopback
HTTP and effects are checked in the temporary per-session sandbox. This suite
does not substitute a mocked gate or a model's promise for enforcement.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import hashlib
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]


class HTTPFixture:
    def __init__(self, binary):
        self.directory = tempfile.TemporaryDirectory(prefix="garden-http-attack-")
        self.root = Path(self.directory.name)
        self.state = self.root / "state"
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            self.port = s.getsockname()[1]
        self.origin = f"http://127.0.0.1:{self.port}"
        clean_env = {k: os.environ[k] for k in ("PATH", "LANG", "TZ") if k in os.environ}
        self.log = (self.root / "server.log").open("wb")
        self.server = subprocess.Popen([sys.executable, str(ROOT / "garden-console/server.py"),
                                        "--port", str(self.port), "--gate", str(binary),
                                        "--state", str(self.state)], env=clean_env,
                                       cwd=ROOT, stdout=self.log, stderr=self.log)
        self.observations = []
        for _ in range(40):
            try:
                status, value = self.call("/health")
                if status == 200:
                    break
            except (URLError, OSError):
                if self.server.poll() is not None:
                    raise RuntimeError("HTTP server exited during startup")
                time.sleep(0.025)
        else:
            raise TimeoutError("HTTP server did not become ready")

    def call(self, path, value=None, *, token=None, raw=None, headers=None):
        wire = raw if raw is not None else None if value is None else json.dumps(value).encode()
        request_headers = {"Content-Type": "application/json"}
        if token:
            request_headers["Authorization"] = "Bearer " + token
        request_headers.update(headers or {})
        request = Request(self.origin + path, data=wire, headers=request_headers)
        try:
            response = urlopen(request, timeout=15)
        except HTTPError as response:
            payload = json.loads(response.read())
            status = response.code
        else:
            status = response.status
            payload = json.loads(response.read())
        # Never store the bearer credentials emitted by session creation.
        recorded = {k: v for k, v in payload.items() if k not in {"token", "agent_token"}}
        self.observations.append({"path": path, "status": status, "response": recorded})
        return status, payload

    def session(self):
        status, value = self.call("/api/session", {})
        assert status == 201, value
        return value

    def work(self, tool="calculator", args=None, **changes):
        value = {"task": "Perform the exact bounded operation.", "tool": tool,
                 "args": args or {"expression": "17 * 23"}, "consent": True}
        value.update(changes)
        return value

    def proposal(self, **changes):
        value = {"id": "untrusted_" + secrets.token_hex(8), "nonce": secrets.token_hex(16),
                 "actor_id": "planner-demo", "delegation_id": "demo-delegation",
                 "policy_version": "garden-implementation-0.1", "tool": "sandbox_write",
                 "args": {"path": "intrusion.txt", "content": "untrusted write"},
                 "claims": [], "unknowns": [], "human_effect": True,
                 "assessment_ids": {k: None for k in ("verification", "qse", "truthfulness", "human_effect")},
                 "successor_of": None}
        value.update(changes)
        return value

    def sandbox(self, session):
        return self.state / session["id"] / "sandbox"

    def close(self):
        self.server.terminate()
        try:
            self.server.wait(timeout=3)
        except subprocess.TimeoutExpired:
            self.server.kill()
            self.server.wait(timeout=3)
        self.log.close()
        self.directory.cleanup()


def run(binary):
    results = []
    def case(name, function):
        f = None
        started = time.monotonic()
        try:
            f = HTTPFixture(binary)
            evidence = function(f)
            result = {"id": name, "outcome": "PASS", "evidence": evidence or {}, "observations": f.observations}
        except Exception as error:
            result = {"id": name, "outcome": "FAIL", "error": f"{type(error).__name__}: {error}", "observations": f.observations if f else []}
        finally:
            if f:
                f.close()
        result["duration_ms"] = round((time.monotonic() - started) * 1000, 2)
        results.append(result)
        print(result["outcome"], name, result.get("error", ""))

    def allowed_work(f):
        s = f.session()
        status, out = f.call("/api/run", f.work(), token=s["token"])
        assert status == 200 and out["decision"] == "ALLOW", out
        assert out["result"]["value"] == 391, out
        status, out = f.call("/api/run", f.work("fs_write", {"path": "allowed.txt", "content": "consented note"}), token=s["token"])
        assert status == 200 and out["decision"] == "ALLOW", out
        assert (f.sandbox(s) / "allowed.txt").read_text() == "consented note"
        return {"effects": "actual calculator result and exact sandbox file"}
    case("http_allowed_work", allowed_work)

    def unauthenticated(f):
        for token in (None, "forged-session-token"):
            status, _ = f.call("/api/run", f.work(), token=token)
            assert status == 401
        status, _ = f.call("/api/session", {"actor_id": "human-admin"})
        assert status == 400
    case("http_unauthenticated_and_session_identity_injection", unauthenticated)

    def raw_unreviewed(f):
        s = f.session()
        status, out = f.call("/api/propose", {"proposal": f.proposal()}, token=s["token"])
        assert status == 200 and out["decision"] in {"DENY", "QUARANTINE"}, out
        assert not (f.sandbox(s) / "intrusion.txt").exists()
    case("http_untrusted_raw_proposal_has_no_automatic_review", raw_unreviewed)

    def actor_spoof(f):
        s = f.session()
        for actor in ("human-demo", "verifier-demo", "smarter-successor"):
            status, _ = f.call("/api/propose", {"proposal": f.proposal(actor_id=actor)}, token=s["token"])
            assert status == 400
        assert not (f.sandbox(s) / "intrusion.txt").exists()
    case("http_actor_spoof", actor_spoof)

    def admin_injection(f):
        s = f.session()
        for fields in ({"control_token": "please-trust-me"}, {"operation": "register_assessment"}, {"trusted": True}, {"session_id": "another-session"}):
            status, _ = f.call("/api/run", {**f.work(), **fields}, token=s["token"])
            assert status == 400
        status, _ = f.call("/api/register_assessment", {"control_token": "please-trust-me", "assessment": {"status": "PASS"}}, token=s["token"])
        assert status == 404
        status, _ = f.call("/api/propose", {"proposal": f.proposal(), "control_token": "please-trust-me"}, token=s["token"])
        assert status == 400
    case("http_admin_operation_injection", admin_injection)

    def cross_session(f):
        a, b = f.session(), f.session()
        status, r = f.call("/api/run", f.work("fs_write", {"path": "source.txt", "content": "session A note"}), token=a["token"])
        assert status == 200 and r["decision"] == "ALLOW", r
        payload = r["receipt"]["payload"]
        p = f.proposal(assessment_ids={"verification": payload["verification"], "qse": payload["qse_findings"], "truthfulness": payload["truthfulness"], "human_effect": payload["human_effects"]["assessment"]})
        status, out = f.call("/api/propose", {"proposal": p}, token=b["token"])
        assert status == 200 and out["decision"] in {"DENY", "QUARANTINE"}, out
        assert not (f.sandbox(b) / "intrusion.txt").exists()
        status, receipts = f.call("/api/receipts", token=b["token"])
        assert status == 200
        assert all(receipt["payload"].get("proposal_id") != payload["proposal_id"] for receipt in receipts["receipts"])
    case("http_cross_session_receipt_and_assessment_reuse", cross_session)

    def consent_and_revoke(f):
        s = f.session()
        status, out = f.call("/api/run", f.work("fs_write", {"path": "consent.txt", "content": "note"}, consent=False), token=s["token"])
        assert status == 200 and out["decision"] in {"DENY", "QUARANTINE"}, out
        assert not (f.sandbox(s) / "consent.txt").exists()
        status, out = f.call("/api/run", f.work("fs_write", {"path": "consent.txt", "content": "note"}), token=s["token"])
        assert status == 200 and out["decision"] == "ALLOW", out
        status, out = f.call("/api/revoke", {}, token=s["token"])
        assert status == 200 and out.get("ok")
        status, out = f.call("/api/run", f.work(), token=s["token"])
        assert status == 200 and out["decision"] == "DENY", out
    case("http_consent_then_revocation", consent_and_revoke)

    def malicious_json(f):
        s = f.session()
        for raw in (b'{"task":"a","task":"b"}', b'{"amount":NaN}', b'{"amount":1e999}', b'null', b'[]', b'{"x":"' + b'x' * 33000 + b'"}'):
            status, _ = f.call("/api/run", token=s["token"], raw=raw)
            assert status == 400
        assert f.call("/api/status", token=s["token"])[0] == 200
    case("http_duplicate_nonfinite_null_and_oversized_json", malicious_json)

    def cross_origin(f):
        s = f.session()
        status, _ = f.call("/api/run", f.work(), token=s["token"], headers={"Origin": "https://evil.test"})
        assert status == 400
    case("http_cross_origin", cross_origin)

    def session_rate(f):
        s = f.session()
        for _ in range(20):
            assert f.call("/api/propose", {}, token=s["token"])[0] == 400
        status, out = f.call("/api/run", f.work(), token=s["token"])
        assert status == 400 and "rate" in out["error"], out
    case("http_per_session_rate_limit", session_rate)

    def global_rate(f):
        for _ in range(10):
            f.session()
        status, out = f.call("/api/session", {})
        assert status == 400 and "rate" in out["error"], out
    case("http_global_session_creation_limit", global_rate)

    def html_content(f):
        s = f.session()
        attack = '<img src=x onerror="fetch(\"/api/revoke\")">'
        status, out = f.call("/api/run", f.work("fs_write", {"path": "html.txt", "content": attack}), token=s["token"])
        assert status == 200 and out["decision"] == "ALLOW", out
        status, out = f.call("/api/run", f.work("fs_read", {"path": "html.txt"}), token=s["token"])
        assert status == 200 and out["result"]["content"] == attack
        script = (ROOT / "garden-console/public/app.js").read_text()
        assert "innerHTML" not in script and "textContent" in script
        return {"scope": "HTTP returns inert JSON content; static UI uses textContent. Browser DOM execution is not exhaustively proved."}
    case("http_user_html_stays_in_json_and_text_nodes", html_content)

    counts = {outcome: sum(r["outcome"] == outcome for r in results) for outcome in ("PASS", "FAIL")}
    return {"schema_version": "gardenbench.http-results.v1", "status": "IMPLEMENTATION", "generated_at": datetime.now(timezone.utc).isoformat(),
            "binary_sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
            "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "controller_sha256": hashlib.sha256((ROOT / "garden-console/server.py").read_bytes()).hexdigest(),
            "counts": counts, "results": results, "search_surface": "Actual HTTP controller subprocess, loopback requests, independent Rust gate processes, temporary sandbox effects and session boundaries",
            "residual_risk": ["No production reverse-proxy or browser-engine penetration test.", "Open-model semantic quality and general epistemic independence are outside this integration suite.", "Anonymous sessions have authority only over their harmless local mock data."],
            "completion_claim": "KNOWN_GAPS_OR_FAILED_CASES_REMAIN" if counts["FAIL"] else "NO_ADDITIONAL_MATERIAL_GAPS_DISCOVERED_WITHIN_DECLARED_SEARCH_SURFACE_AND_BUDGET"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", type=Path, default=ROOT / "garden-kernel/target/debug/garden-gate")
    parser.add_argument("--output", type=Path, default=Path(__file__).parent / "http-attack-receipts.json")
    args = parser.parse_args()
    if not args.binary.exists():
        print("NOT_TESTED: compiled gate unavailable", file=sys.stderr)
        return 2
    result = run(args.binary.resolve())
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result["counts"]))
    return 1 if result["counts"]["FAIL"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
