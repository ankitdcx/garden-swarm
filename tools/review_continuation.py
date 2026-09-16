"""Secret-free event dispatcher for the bounded public review worker.

A daily wake can resume existing work, but cannot admit new source bindings.
The worker and dispatcher share the same GitHub concurrency group and CAS ledger.
"""
import json
import os
from pathlib import Path
import time
from tools import single_review_worker as w

WORKER = 'single-openrouter-review.yml'
DISPATCHER = 'continue-openrouter-review.yml'


def host_check():
    if os.environ.get('GITHUB_REPOSITORY') != w.REPO or os.environ.get('GITHUB_REF') != 'refs/heads/main':
        raise ValueError('untrusted dispatch host')
    path = os.environ.get('GITHUB_WORKFLOW_REF')
    event = os.environ.get('GITHUB_EVENT_NAME')
    if path == w.REPO + '/.github/workflows/' + WORKER + '@refs/heads/main':
        if event != 'workflow_dispatch':
            raise ValueError('untrusted completion event')
        return 'completion'
    if path == w.REPO + '/.github/workflows/' + DISPATCHER + '@refs/heads/main' and event in ('push', 'schedule', 'workflow_dispatch'):
        return event
    raise ValueError('unregistered dispatcher')


def dispatch(root=Path('.')):
    event = host_check()
    token = os.environ['GH_REVIEW_TOKEN']
    ledger = w.GitLedger(token)
    state = ledger.value
    if state.get('paused') is not False or state.get('scope') != 'PUBLIC_MATRIX_REVIEW_ONLY':
        print('PAUSED; no model call or dispatch')
        return
    policy = json.loads((root / 'agents/openrouter-paid-review-policy.json').read_text())
    exclusions = w.load_policy(root / 'agents/provider-exclusion-policy.json')
    bindings = list(w.target_bindings(root, policy, exclusions))
    revision = w.digest([b[3] for b in bindings])
    continuation = state.get('continuation', {})
    if event in ('push', 'workflow_dispatch') and state.get('queue_revision') != revision:
        state['queue_revision'] = revision
        state['admitted_source_commit'] = os.environ['GITHUB_SHA']
        continuation = {'status': 'READY', 'updated': time.time()}
        state['continuation'] = continuation
        ledger.save(state)
    if state.get('queue_revision') != revision:
        print('No material event admitted for this source binding; no dispatch')
        return
    # Paused/blocked jobs do not become eligible merely by repeated events.
    status = continuation.get('status')
    if status == 'DEFERRED_DAILY' and time.time() < continuation['resume_after']:
        return
    if status == 'DISPATCHED' and (event != 'schedule' or time.time() - continuation['updated'] < 3600):
        return
    if status not in ('READY', 'DEFERRED_DAILY', 'DISPATCHED'):
        print('Queue state: ' + str(status) + '; no dispatch')
        return
    if any(a['status'] in ('RESERVED', 'UNKNOWN') and not a.get('response_id') for a in state['attempts']):
        state['continuation'] = {'status': 'BLOCKED', 'reason': 'UNIDENTIFIED_CALL', 'updated': time.time()}
        ledger.save(state)
        return
    try:
        plan = w.pending_plan(root, state, policy, exclusions)
    except ValueError:
        state['continuation'] = {'status': 'BLOCKED', 'reason': 'SLOT_REQUIRES_RECONCILIATION', 'updated': time.time()}
        ledger.save(state)
        return
    state['coverage'] = w.coverage(root, state, policy, exclusions)
    if plan is None:
        state['continuation'] = {'status': 'COMPLETE_PROPOSALS_ONLY', 'updated': time.time()}
        ledger.save(state)
        print('Registered matrix review rounds finished; integration and broader Garden coverage remain pending')
        return
    attempts = continuation.get('dispatch_attempts', 0)
    if attempts >= 2:
        state['continuation'] = {'status': 'BLOCKED', 'reason': 'DISPATCH_DELIVERY_UNCONFIRMED', 'updated': time.time()}
        ledger.save(state)
        return
    # Reserve delivery before POST. Even an ambiguous dispatch can be recovered
    # once by the daily wake: worker slot CAS prevents duplicate inference.
    state['continuation'] = {'status': 'DISPATCHED', 'updated': time.time(),
                             'dispatch_attempts': attempts + 1,
                             'target_id': plan[0]['target_id'], 'round': w.ROUNDS[plan[4][0]],
                             'family': plan[4][1]}
    ledger.save(state)
    w.http(w.API + '/actions/workflows/' + WORKER + '/dispatches', token, {'ref': 'main'})
    print('Next bounded review dispatched: ' + plan[0]['target_id'] + ' ' + plan[4][1])


if __name__ == '__main__':
    try:
        dispatch()
    except Exception as exc:
        print('CONTINUATION_STOPPED: ' + type(exc).__name__ + '; no inference was made by dispatcher')
        raise SystemExit(2)
