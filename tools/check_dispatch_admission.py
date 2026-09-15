"""Fail closed before any provider call from a legacy batch workflow."""
import json
from pathlib import Path

def main() -> int:
    status = json.loads(Path('agents/coordinator-status.json').read_text())
    policy = json.loads(Path('agents/openrouter-paid-review-policy.json').read_text())
    if status.get('scheduler_state') != 'RUNNING':
        raise SystemExit('DISPATCH_BLOCKED: Coordinator is paused or state is unknown')
    if policy['execution_limits']['max_model_calls_per_dispatch'] == 1:
        raise SystemExit('DISPATCH_BLOCKED: legacy batch worker is not an admitted single-review dispatcher')
    raise SystemExit('DISPATCH_BLOCKED: no qualified durable dispatch implementation is bound')

if __name__ == '__main__':
    main()
