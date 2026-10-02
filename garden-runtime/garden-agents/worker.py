#!/usr/bin/env python3
"""Small controller-facing worker shim; stdin task/args, stdout advisory bundle.

The trusted host chooses model files. Never pass gate credentials to this process.
"""
import json
import os
import sys
from garden_agents import AgentRequest, build_bundle, RuleBasedBackend, LlamaCppBackend, BackendError

def main():
    raw = sys.stdin.buffer.read(32769)
    if len(raw) > 32768:
        raise ValueError("worker input limit exceeded")
    request = AgentRequest.from_dict(json.loads(raw))
    backend = RuleBasedBackend()
    model_path = os.environ.get("GARDEN_MODEL_PATH")
    binary = os.environ.get("GARDEN_LLAMA_BINARY")
    setup_error = None
    if model_path and binary:
        name = os.environ.get("GARDEN_MODEL_NAME", "local-unconfigured")
        family = "SmolLM2" if "SmolLM2" in name else "Qwen3.5" if "Qwen3.5" in name else "Qwen3" if "Qwen3" in name else "UNRESOLVED"
        try:
            backend = LlamaCppBackend(binary, model_path, name, family, timeout=12, max_tokens=96)
        except (BackendError, OSError, TypeError) as exc:
            setup_error = str(exc)
    bundle = build_bundle(request, backend, ("planner", "qse_explorer", "representation_escape", "verifier"))
    successful_llm = any(r["cognition"] == "OPEN_WEIGHT_LLM" for r in bundle["advisory_reports"])
    bundle["cognition"] = "OPEN_WEIGHT_LLM" if successful_llm else "RULE_BASED"
    bundle["cognition_status"] = "EXPERIMENTAL" if successful_llm else "IMPLEMENTATION"
    bundle["roles"] = [{"role": r["role"].replace("_", " ").title(), "summary": r["analysis"], "cognition": r["cognition"]} for r in bundle["advisory_reports"]]
    bundle["limitations"] = ["Advisory cognition is not HSA certified or canonical admission.", "Shared model/controller copies are not independent verifiers.", "Open-weight model output can be wrong, injected, incomplete or misleading; it has no tool authority."]
    if not successful_llm:
        bundle["limitations"].append("No successful open-model inference in this request; deterministic fallback used.")
    if setup_error:
        bundle["limitations"].append("Model initialization failed: " + setup_error)
    print(json.dumps(bundle, sort_keys=True, allow_nan=False))

if __name__ == "__main__":
    try:
        main()
    except (ValueError, TypeError, BackendError, OSError) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        raise SystemExit(2)
