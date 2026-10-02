#!/usr/bin/env python3
"""Fixed rule-only Console shim; stdin task/args, stdout advisory bundle.

Ambient model settings cannot select native code or loopback inference here.
Native inference belongs to the separate operator observation CLI. The Console's
optional model route is its fixed WASM runner. Never pass gate credentials here.
"""
import json
import sys
from garden_agents import AgentRequest, build_bundle, RuleBasedBackend

def main():
    raw = sys.stdin.buffer.read(32769)
    if len(raw) > 32768:
        raise ValueError("worker input limit exceeded")
    request = AgentRequest.from_dict(json.loads(raw))
    bundle = build_bundle(request, RuleBasedBackend(), ("planner", "qse_explorer", "representation_escape", "verifier"))
    bundle["cognition"] = "RULE_BASED"
    bundle["cognition_status"] = "IMPLEMENTATION"
    bundle["roles"] = [{"role": r["role"].replace("_", " ").title(), "summary": r["analysis"], "cognition": r["cognition"]} for r in bundle["advisory_reports"]]
    bundle["limitations"] = ["This Console fallback uses deterministic rules; native model settings are ignored.", "Shared rule/controller copies are not independent verifiers.", "No successful open-model inference in this request; deterministic fallback used."]
    print(json.dumps(bundle, sort_keys=True, allow_nan=False))

if __name__ == "__main__":
    try:
        main()
    except (ValueError, TypeError, OSError) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        raise SystemExit(2)
