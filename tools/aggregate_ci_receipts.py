"""Aggregate GitHub run metadata for one exact commit; no write authority."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import re
from urllib.request import Request, urlopen

MANDATORY = ('.github/workflows/integrity.yml',
             '.github/workflows/constitutional-path-guard.yml',
             '.github/workflows/integration-provenance.yml')


def aggregate(runs: list[dict], *, head_sha: str, repository: str) -> dict:
    if not re.fullmatch('[0-9a-f]{40}', head_sha):
        raise ValueError('expected full commit SHA')
    stages = []
    for path in MANDATORY:
        candidates = [r for r in runs if r.get('head_sha') == head_sha
                      and r.get('path') == path
                      and (r.get('repository') or {}).get('full_name') == repository
                      and r.get('event') in ('pull_request', 'push')]
        latest = max(candidates, key=lambda r: (int(r['id']), int(r.get('run_attempt', 1))), default=None)
        result = 'UNKNOWN'
        if latest is not None and latest.get('status') == 'completed':
            result = 'PASS' if latest.get('conclusion') == 'success' else 'FAIL'
        stages.append({'workflow':path, 'result':result,
                       'run_id':latest['id'] if latest else None,
                       'run_attempt':latest.get('run_attempt', 1) if latest else None,
                       'evidence_url':latest.get('html_url') if latest else None})
    overall = 'FAIL' if any(s['result'] == 'FAIL' for s in stages) else (
        'PASS' if all(s['result'] == 'PASS' for s in stages) else 'UNKNOWN')
    return {'schema':'CIConformancePipelineReceipt/v1', 'scope':'MANDATORY_REPOSITORY_WORKFLOW_AGGREGATE',
            'repository':repository, 'head_sha':head_sha, 'stages':stages,
            'overall':overall, 'overall_status':overall,
            'certification_boundary':'Only the named GitHub workflow runs at this exact head. No semantic admission, provider-review quorum, protected approval or canonical promotion.'}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--head-sha', required=True)
    parser.add_argument('--repository', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    if not re.fullmatch('[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', args.repository):
        raise SystemExit('invalid repository')
    if not re.fullmatch('[0-9a-f]{40}', args.head_sha):
        raise SystemExit('invalid head')
    runs = []
    for page in range(1, 11):
        url = f'https://api.github.com/repos/{args.repository}/actions/runs?head_sha={args.head_sha}&per_page=100&page={page}'
        req = Request(url, headers={'Authorization':'Bearer '+os.environ['GITHUB_TOKEN'], 'Accept':'application/vnd.github+json'})
        with urlopen(req, timeout=30) as response:
            payload = json.load(response)
        rows = payload['workflow_runs']; runs.extend(rows)
        if len(rows) < 100:
            break
    else:
        raise SystemExit('run pagination exceeds bounded reader; cannot assert completeness')
    receipt = aggregate(runs, head_sha=args.head_sha, repository=args.repository)
    output = Path(args.output); output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps(receipt, sort_keys=True))
    return 0 if receipt['overall'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
