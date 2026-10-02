import json
import sys
import argparse
from .dsl import parse, GardenError
def main():
    parser = argparse.ArgumentParser(description="Parse Garden advisory DSL; optionally compile a proposal for the external gate")
    parser.add_argument("--proposal-id")
    parser.add_argument("--delegation-id")
    parser.add_argument("--policy-version")
    parser.add_argument("--nonce")
    args = parser.parse_args()
    try:
        raw = sys.stdin.buffer.read(262145)
        document = parse(raw.decode("utf-8"))
        result = document.to_ir()
        if args.proposal_id:
            result = document.to_proposal(args.proposal_id, delegation_id=args.delegation_id, policy_version=args.policy_version, nonce=args.nonce)
        print(json.dumps(result, sort_keys=True))
    except (GardenError, UnicodeError) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 2
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
