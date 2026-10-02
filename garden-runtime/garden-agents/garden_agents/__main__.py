import argparse
import json
import sys
from .backends import RuleBasedBackend, LlamaCppBackend, OllamaBackend, BackendError
from .swarm import build_bundle

def main():
    parser = argparse.ArgumentParser(description="Proposal-only Garden advisory worker; stdin request JSON")
    parser.add_argument("--backend", choices=["rule-based", "llama.cpp", "ollama"], default="rule-based")
    parser.add_argument("--binary")
    parser.add_argument("--model-path")
    parser.add_argument("--model", default="local-unconfigured")
    parser.add_argument("--family", default="UNRESOLVED")
    parser.add_argument("--roles", default="planner,qse_explorer,representation_escape,verifier,adversarial_reviewer")
    parser.add_argument("--strict-model", action="store_true")
    args = parser.parse_args()
    try:
        raw = sys.stdin.buffer.read(32769)
        if len(raw) > 32768:
            raise ValueError("worker input limit exceeded")
        backend = RuleBasedBackend()
        if args.backend == "llama.cpp":
            backend = LlamaCppBackend(args.binary, args.model_path, args.model, args.family)
        elif args.backend == "ollama":
            backend = OllamaBackend(args.model, args.family)
        result = build_bundle(json.loads(raw), backend, args.roles.split(","), allow_fallback=not args.strict_model)
        print(json.dumps(result, sort_keys=True, allow_nan=False))
    except (ValueError, TypeError, OSError, BackendError) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 2
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
