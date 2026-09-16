import copy
import json
from pathlib import Path
import unittest
import tempfile
from unittest.mock import patch

from tools.single_review_worker import budget_check, next_slot, money, endpoint_request, GitLedger
from tools import single_review_worker as worker


class SingleReviewTests(unittest.TestCase):
    def setUp(self):
        self.policy = json.loads(Path('agents/openrouter-paid-review-policy.json').read_text())
        self.exclusions = json.loads(Path('agents/provider-exclusion-policy.json').read_text())
        self.state = {'paused': False, 'attempts': []}
        self.key = {'usage': 0.01, 'usage_daily': 0.01, 'limit_remaining': 5}
        self.model = self.policy['routine_reviewers'][0]
        self.endpoint = {'tag': 'allowed', 'provider_name': 'Allowed', 'status': 0,
                         'context_length': 200000,
                         'pricing': {'prompt': '0.00000015', 'completion': '0.0000006', 'request': '0'}}

    def test_invalid_cost_never_becomes_zero(self):
        for value in (None, True, -1, 'NaN', 'Infinity', 'junk'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                money(value)

    def test_daily_existing_spend_included(self):
        self.key['usage_daily'] = '0.99'
        with self.assertRaisesRegex(ValueError, 'daily'):
            budget_check(self.state, self.key, self.policy, 100000)

    def test_unknown_and_crashed_reservations_block(self):
        for status in ('UNKNOWN', 'RESERVED'):
            self.state['attempts'] = [{'status': status}]
            with self.assertRaisesRegex(ValueError, 'reconciliation'):
                budget_check(self.state, self.key, self.policy, 100000)

    def test_routine_pool_exhaustion(self):
        self.key['usage'] = 9
        with self.assertRaisesRegex(ValueError, 'lifetime'):
            budget_check(self.state, self.key, self.policy, 100000)

    def test_blind_before_followup_and_four_round_bound(self):
        families = ['one', 'two', 'three', 'four']
        cycle = {}
        for n in range(16):
            round_no, family, key = next_slot(cycle, families)
            self.assertEqual((round_no, family), (n // 4, families[n % 4]))
            cycle[key] = {'status': 'REVIEW_RECORDED', 'finding': {'disposition': 'PROPOSE_DELTA'}}
        self.assertIsNone(next_slot(cycle, families))

    def test_can_stop_after_challenge_without_claiming_proof(self):
        families = ['one', 'two', 'three']
        cycle = {f'{n}:{f}': {'status': 'REVIEW_RECORDED', 'finding': {'disposition': 'NO_CHANGE'}}
                 for n in range(2) for f in families}
        self.assertIsNone(next_slot(cycle, families))

    def test_partial_failure_does_not_skip_to_other_family(self):
        with self.assertRaisesRegex(ValueError, 'reconciliation'):
            next_slot({'0:one': {'status': 'UNKNOWN'}}, ['one', 'two', 'three'])

    def test_provider_exclusions_apply_to_endpoint(self):
        for name in ('Anthropic', 'NVIDIA', 'Mistral'):
            endpoint = {**self.endpoint, 'tag': name.lower(), 'provider_name': name}
            with self.subTest(name=name), self.assertRaises((ValueError, RuntimeError)):
                endpoint_request(endpoint, self.model, 'public source', money('.05'), self.policy, self.exclusions)

    def test_request_forbids_fallback_and_has_price_and_output_bounds(self):
        body, estimate = endpoint_request(self.endpoint, self.model, 'public source', money('.05'), self.policy, self.exclusions)
        self.assertFalse(body['provider']['allow_fallbacks'])
        self.assertTrue(body['provider']['zdr'])
        self.assertEqual(body['provider']['only'], ['allowed'])
        self.assertLessEqual(money(estimate), money('.05'))
        self.assertEqual(body['max_tokens'], 8000)

    def test_large_context_never_silently_truncated(self):
        with self.assertRaises(ValueError):
            endpoint_request(self.endpoint, self.model, 'x' * 1000000, money('.05'), self.policy, self.exclusions)

    def test_cas_failure_is_not_retried(self):
        ledger = object.__new__(GitLedger)
        ledger.token, ledger.sha, ledger.value = 'fake', 'old', {'status': 'old'}
        with patch('tools.single_review_worker.http', side_effect=RuntimeError('conflict')) as transport:
            with self.assertRaises(RuntimeError):
                ledger.save({'status': 'new'})
            self.assertEqual(transport.call_count, 1)
            self.assertEqual(ledger.sha, 'old')

    def test_missing_or_unknown_daily_usage_blocks(self):
        for value in (None, True, 'NaN'):
            self.key['usage_daily'] = value
            with self.assertRaises(ValueError):
                budget_check(self.state, self.key, self.policy, 100000)

    def test_end_to_end_reserves_before_one_call_and_continues_next_family(self):
        state = {'scope': 'PUBLIC_MATRIX_REVIEW_ONLY', 'paused': False, 'attempts': [], 'cycles': {}}
        saved = []
        calls = []
        class FakeLedger:
            def __init__(self, token):
                self.value = copy.deepcopy(saved[-1] if saved else state)
            def save(self, value):
                saved.append(copy.deepcopy(value))
                self.value = value
        required = ['current_semantic_claim', 'proposed_delta', 'do_nothing_comparison',
                    'uncertainty', 'evidence_ancestry', 'overturn_conditions']
        finding = {k: 'test fixture' for k in required}
        finding.update(source_anchors=['CONSTITUTIONAL EVENTS'], falsification_attempts=['test'],
                       evidence_search_trace=['source'], affected_invariants=[], affected_tests=[],
                       affected_contracts=[], disposition='PROPOSE_DELTA')
        def fake_http(url, token, body=None, **kwargs):
            if url.endswith('/key'):
                return {'data': self.key}
            if url.endswith('/endpoints'):
                return {'data': {'endpoints': [self.endpoint]}}
            self.assertTrue(url.endswith('/chat/completions'))
            self.assertEqual(saved[-1]['attempts'][-1]['status'], 'RESERVED')
            calls.append(body)
            return {'id': 'fixture-' + str(len(calls)), 'model': body['model'], 'provider': 'Allowed',
                    'usage': {'cost': .001}, 'choices': [{'finish_reason': 'stop',
                     'message': {'content': json.dumps(finding)}}]}
        env = {'GITHUB_REPOSITORY': worker.REPO, 'GITHUB_REF': 'refs/heads/main',
               'GITHUB_WORKFLOW_REF': worker.REPO + '/.github/workflows/single-openrouter-review.yml@refs/heads/main',
               'GITHUB_EVENT_NAME': 'workflow_dispatch', 'OPENROUTER_API_KEY': 'fixture',
               'GH_REVIEW_TOKEN': 'fixture', 'GITHUB_SHA': 'fixture', 'GITHUB_RUN_ID': 'fixture'}
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for file in [t['source_file'] for t in json.loads(Path('agents/design-review-matrix.json').read_text())['targets']] + ['agents/openrouter-paid-review-policy.json', 'agents/provider-exclusion-policy.json',
                         'SOURCE_MANIFEST.json', 'agents/design-review-matrix.json',
                         'Garden_User_v15.5_FULL_2026-09-12.txt']:
                dest = root / file
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(Path(file).read_bytes())
            with patch.dict(worker.os.environ, env), patch.object(worker, 'GitLedger', FakeLedger), patch.object(worker, 'http', fake_http):
                worker.run(root)
                self.assertEqual(len(calls), 1)
                worker.run(root)
                self.assertEqual(len(calls), 2)
                self.assertNotEqual(calls[0]['model'], calls[1]['model'])
                self.assertEqual(saved[-1]['attempts'][-1]['status'], 'REVIEW_RECORDED')

    def test_other_workflow_cannot_use_single_lane(self):
        env = {'GITHUB_REPOSITORY': worker.REPO, 'GITHUB_REF': 'refs/heads/main',
               'GITHUB_EVENT_NAME': 'workflow_dispatch', 'GITHUB_WORKFLOW_REF': 'legacy'}
        with patch.dict(worker.os.environ, env), self.assertRaisesRegex(ValueError, 'unregistered'):
            worker.host_check()


if __name__ == '__main__':
    unittest.main()
