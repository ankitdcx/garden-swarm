"""Compute missing guard dependencies; emit migration evidence, never approval."""
import argparse
import json
from pathlib import Path


def evaluate(root: Path) -> dict:
    policy = json.loads((root / 'gsl/CHANGE_POLICY.json').read_text())
    declared = set(policy['constitutional_paths'])
    required = set(declared)
    required.update({'scripts/check_constitutional_change.py',
                     '.github/workflows/constitutional-path-guard.yml',
                     'agents/config-surface-contracts.json',
                     'agents/design-review-matrix.json'})
    provenance = []
    for path in sorted((root / 'gsl').glob('FUNCTION_CONTRACTS*.json')):
        for contract in json.loads(path.read_text()).get('contracts', []):
            if 'constitutional' in contract.get('authority_requirement', '').lower():
                required.add(contract['implementation_source'])
                required.add(path.relative_to(root).as_posix())
                provenance.append(contract['contract_id'])
    missing = sorted(required - declared)
    return {'schema':'ConstitutionalPathCoverageReceipt/v1',
            'declared_paths':sorted(declared), 'computed_required_paths':sorted(required),
            'missing_paths':missing, 'contract_dependencies':provenance,
            'status':'MIGRATION_REQUIRED' if missing else 'PASS',
            'authority_effect':'NONE',
            'activation':'Candidate evidence only; changing protected policy still requires the existing external/trusted-base approval verifier.'}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', default='.')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    receipt = evaluate(Path(args.root))
    output = Path(args.output); output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps(receipt, sort_keys=True))
    return 0 if receipt['status'] == 'PASS' else 2


if __name__ == '__main__':
    raise SystemExit(main())
