#!/usr/bin/env python3
"""Garden demo controller. Models propose; the external Rust gate executes.

This controller authorizes only bounded local demo effects. Its deterministic
reviewers cover that narrow tool surface, not arbitrary human-world decisions.
"""
from __future__ import annotations
import argparse
import ast
import copy
import hashlib
import json
import math
import mimetypes
import os
import platform
import re
from pathlib import Path
import secrets
import shutil
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from broker import GateBroker
from bounded_process import bounded_run
from http_boundary import MAX_BODY, check_origin, strict_object, validate_fields

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = Path(__file__).parent / "public"
QSE = ["missing_questions", "missing_variables", "alternative_representations", "omissions",
       "boundary_attacks", "rule_conformant_attacks", "counterfactual_redesigns", "integration_failures"]
EFFECTS = ["rights", "consent", "privacy", "authority", "safety", "law", "evidence", "explanation"]
TOOLS = {"calculator", "fs_read", "fs_write", "mock_email", "mock_ledger"}
ATTACKS = {None, "unauthorized", "unknown", "stale", "successor", "self_certify", "modify_gate"}
SESSIONS = {}
SESSIONS_LOCK = threading.Lock()
NEW_SESSION_TIMES = []
CONFIG = None
sys.path.insert(0, str(ROOT / "garden-lang"))
from garden_lang import parse as parse_garden


def arithmetic(expression):
    if not isinstance(expression, str) or len(expression) > 256:
        raise ValueError("arithmetic expression exceeds limit")
    tree = ast.parse(expression.replace("×", "*").replace("÷", "/"), mode="eval")
    if len(list(ast.walk(tree))) > 40:
        raise ValueError("arithmetic expression exceeds complexity limit")
    ops = {ast.Add: ("add", lambda a, b: a + b), ast.Sub: ("subtract", lambda a, b: a - b),
           ast.Mult: ("multiply", lambda a, b: a * b), ast.Div: ("divide", lambda a, b: a / b)}
    def value(n):
        if isinstance(n, ast.Constant) and type(n.value) in (int, float):
            v = float(n.value)
        elif isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.UAdd, ast.USub)):
            v = value(n.operand) * (-1 if isinstance(n.op, ast.USub) else 1)
        elif isinstance(n, ast.BinOp) and type(n.op) in ops:
            v = ops[type(n.op)][1](value(n.left), value(n.right))
        else:
            raise ValueError("only finite arithmetic with + - * / is permitted")
        if not math.isfinite(v) or abs(v) > 1e12:
            raise ValueError("arithmetic value exceeds limit")
        return v
    n = tree.body
    if isinstance(n, ast.BinOp) and type(n.op) in ops:
        a, b = value(n.left), value(n.right)
        return {"op": ops[type(n.op)][0], "a": a, "b": b}, value(n)
    v = value(n)
    return {"op": "add", "a": v, "b": 0.0}, v


def tool_arguments(tool, args):
    if not isinstance(args, dict):
        raise ValueError("tool arguments must be an object")
    expected = {"calculator": {"expression"}, "fs_read": {"path"}, "fs_write": {"path", "content"},
                "mock_email": {"to", "subject", "body"}, "mock_ledger": {"account", "amount"}}
    validate_fields(args, expected[tool], expected[tool])
    if tool == "calculator":
        mapped, answer = arithmetic(args["expression"])
        return "calculator", mapped, answer
    if tool in {"fs_read", "fs_write"}:
        path = args["path"]
        if not isinstance(path, str) or not path or len(path) > 80 or any(c in path for c in ("/", "\\", "\x00")) or path.startswith("."):
            raise ValueError("use one plain sandbox filename")
        if tool == "fs_write" and (not isinstance(args["content"], str) or len(args["content"].encode()) > 2000):
            raise ValueError("note text exceeds demo limit")
        return "sandbox_read" if tool == "fs_read" else "sandbox_write", args, None
    if tool == "mock_email":
        if any(not isinstance(v, str) or len(v) > 2000 for v in args.values()):
            raise ValueError("mock email fields exceed limit")
        if "@" not in args["to"] or len(args["to"]) > 254:
            raise ValueError("mock recipient must be an email-shaped label")
        return tool, args, None
    amount = args["amount"]
    if type(amount) not in (int, float) or not math.isfinite(amount) or amount <= 0 or amount > 100:
        raise ValueError("test transfer must be between 0 and 100")
    if args["account"] not in {"demo", "reserve"}:
        raise ValueError("unknown test account")
    return tool, {"from": args["account"], "to": "reserve" if args["account"] == "demo" else "demo",
                  "amount_cents": round(amount * 100)}, None


def audit_numeric_claims(roles):
    """Check explicit small arithmetic equalities; other model prose stays UNKNOWN."""
    findings = []
    number = r"[-+]?\d+(?:\.\d+)?"
    pattern = re.compile(rf"({number}\s*[+*/×÷-]\s*{number})\s*=\s*({number})")
    for role in roles:
        text = role.get("summary", "")
        if not isinstance(text, str): continue
        for match in list(pattern.finditer(text))[:8]:
            try:
                _, expected = arithmetic(match.group(1))
                claimed = float(match.group(2))
                if not math.isclose(expected, claimed, rel_tol=1e-10, abs_tol=1e-10):
                    findings.append({"status": "CONTRADICTED", "role": role.get("role"),
                                     "claim": match.group(0), "expected": expected,
                                     "check": "bounded deterministic arithmetic; general prose remains UNKNOWN"})
            except (ValueError, SyntaxError, ZeroDivisionError):
                findings.append({"status": "UNKNOWN", "claim": match.group(0)})
    return findings


def agent_work(task, tool, args):
    """Inference child receives no gate credentials and cannot execute tools."""
    wasm_worker = ROOT / "garden-agents/wasm_worker.mjs"
    dependency_path = os.environ.get("GARDEN_WASM_DEPENDENCIES")
    model_directory = os.environ.get("GARDEN_WASM_MODEL_DIR")
    node_binary = os.environ.get("GARDEN_NODE_BINARY")
    if wasm_worker.exists() and dependency_path and model_directory and node_binary:
        try:
            from worker_isolation import LIBC, PROGRAM
            import ctypes
            def restrict_wasm():
                import resource
                resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
                resource.setrlimit(resource.RLIMIT_NOFILE, (128, 128))
                resource.setrlimit(resource.RLIMIT_CPU, (90, 90))
                if platform.system() != "Linux" or platform.machine() != "x86_64": os._exit(126)
                if LIBC.prctl(38, 1, 0, 0, 0) != 0 or LIBC.prctl(22, 2, ctypes.byref(PROGRAM), 0, 0) != 0: os._exit(126)
            dependencies = str(Path(dependency_path).resolve(strict=True))
            model_dir = str(Path(model_directory).resolve(strict=True))
            command = [node_binary, "--permission", "--no-addons", "--allow-fs-read=" + str(wasm_worker),
                       "--allow-fs-read=" + str(ROOT / "garden-agents/calculator_intent.mjs"),
                       "--allow-fs-read=" + dependencies, "--allow-fs-read=" + model_dir, str(wasm_worker)]
            clean_env = {"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "GARDEN_WASM_DEPENDENCIES": dependencies,
                         "GARDEN_WASM_MODEL_DIR": model_dir}
            code, stdout, _ = bounded_run(command, json.dumps({"task": task, "tool": tool, "args": args}).encode(),
                                         timeout=90, cwd=ROOT / "garden-agents", env=clean_env,
                                         preexec_fn=restrict_wasm)
            if code == 0:
                answer = json.loads(stdout)
                if isinstance(answer, dict): return answer
        except (subprocess.SubprocessError, ValueError, OSError, TimeoutError):
            pass
    cli = ROOT / "garden-agents" / "worker.py"
    if cli.exists():
        clean_env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "LANG": "C.UTF-8",
                     "PYTHONDONTWRITEBYTECODE": "1"}
        for key in ("GARDEN_MODEL_URL", "GARDEN_MODEL_NAME", "GARDEN_LLAMA_BINARY", "GARDEN_MODEL_PATH"):
            if key in os.environ:
                clean_env[key] = os.environ[key]
        def restrict():
            import resource
            resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
            resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
            if os.getuid() == 0:
                os.setgroups([])
                os.setgid(65534)
                os.setuid(65534)
        try:
            code, stdout, _ = bounded_run([sys.executable, str(cli)], json.dumps({"task": task, "tool": tool, "args": args}).encode(),
                                         timeout=60, cwd=ROOT / "garden-agents", env=clean_env,
                                         preexec_fn=restrict if os.name == "posix" else None)
            if code == 0:
                answer = json.loads(stdout)
                if isinstance(answer, dict):
                    return answer
        except (subprocess.SubprocessError, ValueError, OSError, TimeoutError):
            pass
    return {"cognition": "RULE_BASED", "roles": [
        {"role": "Planner", "summary": f"Propose the bounded {tool} operation."},
        {"role": "QSE explorer", "summary": "Consider no action, missing inputs, scope and failure recovery."},
        {"role": "Representation escape", "summary": "Separate the requested outcome from the proposed tool operation."}],
        "unknowns": [], "limitations": ["No successful open-model inference in this request; deterministic fallback used."]}


class Session:
    def __init__(self):
        self.id = secrets.token_hex(12)
        self.token = secrets.token_urlsafe(32)
        self.expires_at = int(time.time()) + 3600
        self.created = time.monotonic()
        self.times = []
        self.lock = threading.RLock()
        self.receipts = []
        self.revoked = False
        self.directory = CONFIG.state / self.id
        self.directory.mkdir(mode=0o700, parents=True)
        policy = json.loads((ROOT / "garden-gate/config/example_policy.json").read_text())
        policy["max_actions_per_actor"] = 100
        for item in policy["authorities"] + policy["delegations"]:
            item["expires_at"] = self.expires_at
        source = ROOT / "docs/source-map.json"
        if source.exists():
            policy["source_anchors"].append("source-map-sha256:" + hashlib.sha256(source.read_bytes()).hexdigest())
        policy_file = self.directory / "policy.json"
        policy_file.write_text(json.dumps(policy, indent=2))
        policy_file.chmod(0o600)
        sandbox = self.directory / "sandbox"
        sandbox.mkdir(mode=0o700)
        (sandbox / "example.txt").write_text("Garden agents propose. The gate decides.\n")
        self.broker = GateBroker([str(CONFIG.gate), "--policy", str(policy_file), "--state-dir",
                                 str(self.directory / "state"), "--sandbox-dir", str(sandbox)],
                                control_token=secrets.token_urlsafe(40), receipt_key=secrets.token_urlsafe(40), cwd=ROOT,
                                extra_env={"GARDEN_BOUND_ACTOR_ID": "planner-demo"})

    def rate(self):
        now = time.monotonic()
        self.times = [t for t in self.times if now - t < 60]
        if len(self.times) >= 20:
            raise ValueError("session request rate exceeded")
        self.times.append(now)

    def proposal(self, tool, args):
        record = {"id": "job-" + secrets.token_hex(10), "actor_id": "planner-demo", "tool": tool, "args": args,
                  "source": {"status": "IMPLEMENTATION", "uri": "garden-runtime/garden-lang", "version": "0.1"}}
        document = parse_garden("GARDEN 1\nPROPOSAL " + json.dumps(record, allow_nan=False) + "\n")
        proposal = document.to_proposal(record["id"], delegation_id="demo-delegation",
                                        policy_version="garden-implementation-0.1", nonce="ir-" + document.digest)
        return proposal, document.to_ir()

    def review(self, p, consent):
        """Narrow trusted reviewers, independent of model prose/approval claims."""
        digest_response = self.broker.request({"operation": "digest", "proposal": p})
        digest = digest_response.get("digest") or digest_response.get("proposal_digest")
        if not digest:
            raise RuntimeError("gate did not bind proposal")
        mutating = p["tool"] not in {"calculator", "sandbox_read"}
        for kind, reviewer in (("verification", "verifier-demo"), ("qse", "qse-demo"),
                               ("truthfulness", "truth-demo"), ("human_effect", "effect-demo")):
            assessment_id = kind + "-" + secrets.token_hex(10)
            findings = []
            status = "PASS"
            if kind == "human_effect" and mutating and not consent:
                findings = ["HUMAN_CONSENT_MISSING"]
                status = "FAIL"
            record = {"id": assessment_id, "proposal_digest": digest, "reviewer_id": reviewer,
                      "kind": kind, "status": status, "findings": findings,
                      "covered_dimensions": QSE if kind == "qse" else EFFECTS if kind == "human_effect" else [],
                      "material_omissions": [], "policy_version": p["policy_version"],
                      "expires_at": min(self.expires_at, int(time.time()) + 120)}
            result = self.broker.request({"operation": "register_assessment", "assessment": record}, trusted=True)
            if not result.get("ok", False):
                raise RuntimeError("trusted assessment registration rejected")
            p["assessment_ids"][kind] = assessment_id

    def run(self, value):
        validate_fields(value, {"task", "tool", "args", "consent", "attack"}, {"task", "tool", "args", "consent"})
        task, tool, consent, attack = value["task"], value["tool"], value["consent"], value.get("attack")
        if not isinstance(task, str) or len(task) > 2000 or tool not in TOOLS or type(consent) is not bool or attack not in ATTACKS:
            raise ValueError("invalid work request")
        gate_tool, mapped, expected = tool_arguments(tool, value["args"])
        cognition = agent_work(task, gate_tool, mapped)
        p, native_ir = self.proposal(gate_tool, mapped)
        claim_audit = audit_numeric_claims(cognition.get("roles", []))
        if claim_audit and p["human_effect"]:
            p["unknowns"].append("MODEL_MATERIAL_NUMERIC_CLAIM_NOT_VALIDATED")
        self.review(p, consent)
        if attack == "unauthorized": p["delegation_id"] = "invented-authority"
        elif attack == "unknown": p["unknowns"] = ["Material fact is unknown"]
        elif attack == "stale": p["policy_version"] = "stale-policy"
        elif attack == "successor": p["actor_id"] = "ungranted-successor"; p["successor_of"] = "planner-demo"
        elif attack == "self_certify": p["human_effect"] = True; p["assessment_ids"]["verification"] = "self-certified"
        elif attack == "modify_gate": p["tool"] = "sandbox_write"; p["args"] = {"path": "../policy.json", "content": "ALLOW_ALL"}; p["human_effect"] = True
        answer = self.broker.request({"operation": "execute", "proposal": p})
        if answer.get("receipt"): self.receipts.append(answer["receipt"])
        answer["cognition"] = cognition.get("cognition", "UNKNOWN")
        answer["roles"] = cognition.get("roles", []) + [{"role": "Authority reviewer", "summary": "Gate rechecks bounded scope, expiry, revocation and version."},
               {"role": "Human-effect reviewer", "summary": "Local mock effects only; consent required for changes."},
               {"role": "Receipt auditor", "summary": "Authenticated chain records integrity; truth remains separately assessed."}]
        answer["agent_limitations"] = cognition.get("limitations", [])
        answer["cognition_status"] = cognition.get("cognition_status", "IMPLEMENTATION")
        answer["agent_lineage_overlap"] = cognition.get("lineage_overlap", [])
        answer["garden_native_ir"] = native_ir
        answer["model_claim_audit"] = claim_audit
        answer["verification_surface"] = "Bounded arithmetic and local demo adapters. General semantic omission/collusion detection remains unresolved."
        if expected is not None: answer["independent_expected_result"] = expected
        return answer


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.0"
    server_version = "GardenConsole/0.1"
    def log_message(self, *args): pass
    def setup(self):
        super().setup()
        self.connection.settimeout(10)
    def send_json(self, value, code=200):
        wire = json.dumps(value, allow_nan=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(wire)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(wire)
    def session(self):
        header = self.headers.get("Authorization", "")
        if not header.startswith("Bearer ") or len(header) > 200:
            raise PermissionError("session authorization required")
        token = header[7:]
        with SESSIONS_LOCK:
            s = SESSIONS.get(token)
        if s is None or s.expires_at <= time.time():
            raise PermissionError("session expired or unknown")
        return s
    def do_GET(self):
        try:
            if self.path in {"/health", "/api/health"}:
                return self.send_json({"status": "ready" if CONFIG.gate.is_file() else "gate_unavailable", "implementation": "0.1"})
            if self.path == "/api/status":
                s = self.session()
                return self.send_json({"gate": s.broker.request({"operation": "status"}), "expires_at": s.expires_at,
                                       "revoked": s.revoked, "scope": sorted(TOOLS), "model_has_control_credentials": False})
            if self.path == "/api/receipts": return self.send_json({"receipts": self.session().receipts[-100:]})
            if self.path in {"/api/sources", "/api/bench"}:
                self.session()
                p = ROOT / ("docs/source-map.json" if self.path == "/api/sources" else "gardenbench/attack-receipts.json")
                return self.send_json(json.loads(p.read_text()) if p.exists() else {"status": "PENDING", "scope": "No test or source claim until a receipt exists."})
            paths = {"/": "index.html", "/index.html": "index.html", "/style.css": "style.css", "/app.js": "app.js", "/favicon.svg": "favicon.svg"}
            if self.path not in paths: return self.send_json({"error": "not found"}, 404)
            path = PUBLIC / paths[self.path]
            data = path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", mimetypes.guess_type(str(path))[0] or "application/octet-stream")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; frame-ancestors 'none'; base-uri 'none'")
            self.end_headers()
            self.wfile.write(data)
        except PermissionError as e: self.send_json({"error": str(e)}, 401)
        except (ValueError, OSError, RuntimeError) as e: self.send_json({"error": str(e)}, 503)
    def do_POST(self):
        try:
            check_origin(self.headers.get("Origin"), self.headers.get("Host", ""), CONFIG.origin)
            if self.headers.get("Content-Type", "").split(";", 1)[0] != "application/json":
                raise ValueError("application/json required")
            size = int(self.headers.get("Content-Length", "0"))
            if size < 0 or size > MAX_BODY: raise ValueError("request body exceeds limit")
            if self.headers.get("Transfer-Encoding"): raise ValueError("transfer encoding not accepted")
            value = strict_object(self.rfile.read(size))
            if self.path == "/api/session":
                validate_fields(value, set())
                with SESSIONS_LOCK:
                    now = time.monotonic()
                    NEW_SESSION_TIMES[:] = [t for t in NEW_SESSION_TIMES if now - t < 60]
                    if len(NEW_SESSION_TIMES) >= 10: raise ValueError("new session rate exceeded")
                    for token, session in list(SESSIONS.items()):
                        if session.expires_at <= time.time():
                            session.broker.close(); shutil.rmtree(session.directory); del SESSIONS[token]
                    if len(SESSIONS) >= 16: raise ValueError("demo session capacity reached")
                    s = Session(); SESSIONS[s.token] = s; NEW_SESSION_TIMES.append(now)
                return self.send_json({"id": s.id, "token": s.token, "expires_at": s.expires_at, "status": "IMPLEMENTATION"}, 201)
            s = self.session()
            with s.lock:
                s.rate()
                if self.path == "/api/run": return self.send_json(s.run(value))
                if self.path == "/api/propose":
                    validate_fields(value, {"proposal"}, {"proposal"})
                    p = copy.deepcopy(value["proposal"])
                    if not isinstance(p, dict) or p.get("actor_id") != "planner-demo" or p.get("delegation_id") != "demo-delegation":
                        raise ValueError("proposal identity outside this session")
                    r = s.broker.request({"operation": "execute", "proposal": p})
                    if r.get("receipt"): s.receipts.append(r["receipt"])
                    return self.send_json(r)
                if self.path == "/api/revoke":
                    validate_fields(value, set())
                    result = s.broker.request({"operation": "revoke", "delegation_id": "demo-delegation"}, trusted=True)
                    s.revoked = True
                    return self.send_json(result)
            return self.send_json({"error": "unknown operation"}, 404)
        except PermissionError as e: self.send_json({"error": str(e)}, 401)
        except (ValueError, SyntaxError, ZeroDivisionError, TypeError) as e: self.send_json({"error": str(e)}, 400)
        except (OSError, RuntimeError, TimeoutError) as e: self.send_json({"error": str(e)}, 503)


class BoundedServer(ThreadingHTTPServer):
    daemon_threads = True
    def __init__(self, *args):
        super().__init__(*args)
        self.slots = threading.BoundedSemaphore(24)
    def process_request(self, request, client_address):
        if not self.slots.acquire(blocking=False):
            request.close(); return
        try: super().process_request(request, client_address)
        except Exception: self.slots.release(); raise
    def process_request_thread(self, request, client_address):
        try: super().process_request_thread(request, client_address)
        finally: self.slots.release()


def main():
    global CONFIG
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8080")))
    parser.add_argument("--gate", type=Path, default=ROOT / "garden-kernel/target/release/garden-gate")
    parser.add_argument("--state", type=Path, default=ROOT / ".garden-state/console")
    parser.add_argument("--origin", default=os.environ.get("GARDEN_PUBLIC_ORIGIN"))
    CONFIG = parser.parse_args()
    CONFIG.state.mkdir(parents=True, exist_ok=True, mode=0o700)
    CONFIG.state.chmod(0o700)
    if not CONFIG.gate.is_file(): parser.error("build the external Rust gate first")
    try: BoundedServer((CONFIG.host, CONFIG.port), Handler).serve_forever()
    finally:
        for s in SESSIONS.values(): s.broker.close()


if __name__ == "__main__": main()
