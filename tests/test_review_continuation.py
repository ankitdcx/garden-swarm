import copy
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch
from tools import single_review_worker as w
from tools import review_continuation as c


class ContinuationTests(unittest.TestCase):
    def setUp(self):
        self.policy = json.loads(Path('agents/openrouter-paid-review-policy.json').read_text())
        self.exclusions = w.load_policy(Path('agents/provider-exclusion-policy.json'))
        self.state = {'scope': 'PUBLIC_MATRIX_REVIEW_ONLY', 'paused': False, 'attempts': [], 'cycles': {}}
        self.saved = []
        owner = self
        class Ledger:
            def __init__(self, token):
                self.value = owner.state
            def save(self, value):
                owner.saved.append(copy.deepcopy(value))
        self.ledger = Ledger
        self.env = {'GITHUB_REPOSITORY': w.REPO, 'GITHUB_REF': 'refs/heads/main',
                    'GITHUB_WORKFLOW_REF': w.REPO + '/.github/workflows/' + c.DISPATCHER + '@refs/heads/main',
                    'GITHUB_EVENT_NAME': 'push', 'GH_REVIEW_TOKEN': 'fixture', 'GITHUB_SHA': 'fixture'}

    def dispatch(self, event='push'):
        self.env['GITHUB_EVENT_NAME'] = event
        with patch.dict(os.environ, self.env), patch.object(w, 'GitLedger', self.ledger), patch.object(w, 'http', return_value={}) as http:
            c.dispatch()
            return http.call_count

    def test_push_starts_one_dispatch_and_duplicate_does_not_repeat(self):
        self.assertEqual(self.dispatch(), 1)
        self.assertEqual(self.dispatch(), 0)
        self.assertEqual(self.state['continuation']['status'], 'DISPATCHED')
        self.assertEqual(len(self.state['coverage']['targets']), 10)
        self.assertFalse(self.state['coverage']['full_garden_review_complete'])

    def test_clock_never_creates_new_review(self):
        self.assertEqual(self.dispatch('schedule'), 0)
        self.assertNotIn('queue_revision', self.state)

    def test_pause_and_unknown_call_are_not_retried(self):
        self.state['paused'] = True
        self.assertEqual(self.dispatch(), 0)
        self.state['paused'] = False
        self.state['attempts'] = [{'status': 'UNKNOWN'}]
        self.assertEqual(self.dispatch(), 0)
        self.assertEqual(self.state['continuation']['reason'], 'UNIDENTIFIED_CALL')

    def test_daily_quota_only_resumes_after_due_time(self):
        self.dispatch()
        self.state['continuation'] = {'status': 'DEFERRED_DAILY', 'resume_after': 2000}
        with patch.object(c.time, 'time', return_value=1000):
            self.assertEqual(self.dispatch('schedule'), 0)
        with patch.object(c.time, 'time', return_value=3000):
            self.assertEqual(self.dispatch('schedule'), 1)

    def test_dispatch_delivery_retries_are_bounded(self):
        self.dispatch()
        self.state['continuation'].update(updated=0)
        self.assertEqual(self.dispatch('schedule'), 1)
        self.state['continuation'].update(updated=0)
        self.assertEqual(self.dispatch('schedule'), 0)
        self.assertEqual(self.state['continuation']['status'], 'BLOCKED')

    def test_blocked_does_not_restart_on_identical_push(self):
        self.dispatch()
        self.state['continuation'] = {'status': 'BLOCKED'}
        self.assertEqual(self.dispatch(), 0)
        self.assertEqual(self.dispatch('schedule'), 0)

    def test_review_retry_is_bounded_and_cannot_skip_family(self):
        cycle = {'0:one': {'status': 'INCOMPLETE', 'attempt_number': 1}}
        self.assertEqual(w.next_slot(cycle, ['one', 'two', 'three']), (0, 'one', '0:one'))
        cycle['0:one']['attempt_number'] = 2
        with self.assertRaisesRegex(ValueError, 'retry exhausted'):
            w.next_slot(cycle, ['one', 'two', 'three'])

    def test_generation_metadata_reconciles_without_inference(self):
        attempt = {'status': 'UNKNOWN', 'response_id': 'fixture-gen', 'model': 'fixture-model',
                   'actual_provider': 'Fixture', 'reserved': '.05', 'cost': '.001', 'cycle': 'cycle', 'slot': '0:f'}
        self.state['attempts'] = [attempt]
        self.state['cycles'] = {'cycle': {'0:f': copy.deepcopy(attempt)}}
        data = {'id': 'fixture-gen', 'model': 'fixture-model', 'provider_name': 'Fixture',
                'total_cost': .001, 'finish_reason': 'length'}
        with patch.object(w, 'http', return_value={'data': data}) as http:
            w.reconcile(self.ledger('fixture'), 'fixture')
            self.assertEqual(http.call_count, 1)
            self.assertIn('/generation?id=fixture-gen', http.call_args.args[0])
        self.assertEqual(attempt['status'], 'INCOMPLETE')
        self.assertEqual(attempt['finish_reason'], 'length')
        self.assertEqual(len(self.state['attempts']), 1)

    def test_reconciliation_rejects_substituted_identity(self):
        self.state['attempts'] = [{'status': 'UNKNOWN', 'response_id': 'wanted', 'model': 'model',
                                  'actual_provider': 'Fixture', 'reserved': '.05', 'cost': '.001', 'cycle': 'c', 'slot': 's'}]
        self.state['cycles'] = {'c': {}}
        with patch.object(w, 'http', return_value={'data': {'id': 'wrong', 'total_cost': .001}}):
            with self.assertRaisesRegex(ValueError, 'mismatch'):
                w.reconcile(self.ledger('fixture'), 'fixture')
        self.assertEqual(self.state['attempts'][0]['status'], 'UNKNOWN')

    def test_final_billing_difference_preserves_conservative_accounting(self):
        attempt = {'status': 'UNKNOWN', 'response_id': 'fixture-gen', 'model': 'fixture-model',
                   'actual_provider': 'Fixture', 'reserved': '.05', 'cost': '.001', 'cycle': 'c', 'slot': 's'}
        self.state['attempts'] = [attempt]
        self.state['cycles'] = {'c': {'s': copy.deepcopy(attempt)}}
        data = {'id': 'fixture-gen', 'model': 'fixture-model', 'provider_name': 'Fixture',
                'total_cost': .002, 'finish_reason': 'length'}
        with patch.object(w, 'http', return_value={'data': data}):
            w.reconcile(self.ledger('fixture'), 'fixture')
        self.assertEqual(attempt['cost'], '0.002')
        self.assertEqual(attempt['response_reported_cost'], '.001')
        self.assertEqual(attempt['status'], 'INCOMPLETE')

    def test_executor_fix_rearms_but_preserves_review_cycle(self):
        self.dispatch()
        revision = self.state['queue_revision']
        self.state['continuation'] = {'status': 'BLOCKED'}
        self.state['executor_revision'] = 'old-executor'
        self.assertEqual(self.dispatch(), 1)
        self.assertEqual(self.state['queue_revision'], revision)

    def test_http_204_dispatch_success(self):
        from unittest.mock import MagicMock
        response = MagicMock()
        response.__enter__.return_value.read.return_value = b''
        opener = MagicMock()
        opener.open.return_value = response
        with patch.object(w.request, 'build_opener', return_value=opener):
            self.assertEqual(w.http(w.API + '/actions/workflows/test/dispatches', 'fixture', {'ref': 'main'}), {})

    def test_completed_queue_does_not_dispatch(self):
        for _, _, _, cycle_id, families in w.target_bindings(Path('.'), self.policy, self.exclusions):
            self.state['cycles'][cycle_id] = {f'{n}:{family}': {'status': 'REVIEW_RECORDED',
                'finding': {'disposition': 'NO_CHANGE'}} for n in range(2) for family in families}
        self.assertEqual(self.dispatch(), 0)
        self.assertEqual(self.state['continuation']['status'], 'COMPLETE_PROPOSALS_ONLY')

    def test_foreign_workflow_cannot_dispatch(self):
        self.env['GITHUB_WORKFLOW_REF'] = 'other'
        with self.assertRaises(ValueError):
            self.dispatch()


if __name__ == '__main__':
    unittest.main()
