import copy
from decimal import Decimal
from email.message import Message
from io import BytesIO
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from tools import review_campaign as campaign
from tools import independent_branch_worker as worker
from tools import independent_branch_protocol as protocol
from tools import single_review_worker as legacy


class RateLimitRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.policy = campaign.load_campaign()
        self.attempt = {
            'status': 'UNKNOWN', 'http_status': 429, 'error_type': 'HTTPError',
            'cost': None, 'reserved': '.1', 'inference_reserved': True,
            'semantic_delta_admitted': False, 'full_review_complete': False,
            'spending': {'campaign_id': self.policy['campaign_id'],
                         'source_sha256': self.policy['source_sha256']},
            'started': 900, 'cycle': 'cycle', 'slot': 'blind:deepseek',
            'http_rate_limit': {'observed_at': 1000, 'retry_after_valid': True,
                                'retry_after_seconds': '120', 'retry_after_present': True},
        }
        self.state = {'attempts': [self.attempt]}
        self.directive = {'retry_of_attempt_sha256': protocol.sha256_value(self.attempt),
                          'retry_reason': 'Received HTTP429; retained full reservation and waited.'}

    def test_full_reserve_persists_without_claiming_billing_or_evidence(self):
        original = copy.deepcopy(self.attempt)
        self.assertEqual(campaign.accounting_charge(self.attempt, self.policy), Decimal('.1'))
        self.assertEqual(campaign.blocking_attempts(self.state, self.policy), [])
        self.assertEqual(self.attempt, original)
        self.assertEqual(self.attempt['status'], 'UNKNOWN')
        self.assertIsNone(self.attempt['cost'])
        self.assertFalse(self.attempt['full_review_complete'])
        self.state['attempts'].append({'status': 'REVIEW_RECORDED', 'cost': '9.8'})
        campaign.check_total(self.state, self.policy, '.1')
        with self.assertRaises(ValueError):
            campaign.check_total(self.state, self.policy, '.1001')

    def test_no_exception_for_timeouts_5xx_identified_or_other_campaign(self):
        variants = [{'http_status': 500}, {'http_status': 503}, {'http_status': None},
                    {'error_type': 'TimeoutError'}, {'response_id': 'gen-existing'},
                    {'status': 'RESERVED'}, {'cost': '0'}, {'inference_reserved': False},
                    {'spending': {}}, {'semantic_delta_admitted': True}]
        for edit in variants:
            a = {**self.attempt, **edit}
            with self.subTest(edit=edit):
                self.assertIsNone(campaign.rate_limit_recovery(a, self.policy))
        self.assertIsNone(campaign.rate_limit_recovery(self.attempt, None))

    def test_receipt_bound_retry_honors_deadline_and_maximum_two_total_attempts(self):
        with self.assertRaisesRegex(ValueError, 'backoff'):
            worker._require_explicit_retry(self.state, 'cycle', 'blind:deepseek', self.directive,
                                           campaign=self.policy, now=1119)
        worker._require_explicit_retry(self.state, 'cycle', 'blind:deepseek', self.directive,
                                       campaign=self.policy, now=1120)
        for d in ({}, {**self.directive, 'retry_of_attempt_sha256': 'wrong'},
                  {**self.directive, 'retry_reason': ''}):
            with self.subTest(d=d), self.assertRaises(ValueError):
                worker._require_explicit_retry(self.state, 'cycle', 'blind:deepseek', d,
                                               campaign=self.policy, now=1200)
        self.state['attempts'].append(copy.deepcopy(self.attempt))
        with self.assertRaisesRegex(ValueError, 'two attempts'):
            worker._require_explicit_retry(self.state, 'cycle', 'blind:deepseek', self.directive,
                                           campaign=self.policy, now=1200)

    def test_legacy_missing_headers_requires_exact_protected_policy_receipt(self):
        a = {k: v for k, v in self.attempt.items() if k != 'http_rate_limit'}
        self.assertIsNone(campaign.rate_limit_recovery(a, self.policy))
        self.policy['http_429_recovery']['legacy_receipts'] = [{
            'attempt_sha256': campaign.digest(a), 'observed_at': 1100,
            'approved_not_before': 4700, 'reason': 'Conservative operator cooldown; discarded header cannot be recovered.',
            'header_evidence': 'NOT_CAPTURED_BY_OLD_WORKER'}]
        self.assertEqual(campaign.rate_limit_recovery(a, self.policy)['retry_not_before'], Decimal(4700))
        self.assertIsNone(campaign.rate_limit_recovery({**a, 'started': 901}, self.policy))

    def test_unknown_rate_limit_receipt_is_not_queried_or_modified(self):
        class Ledger:
            value = self.state
            def save(self, value):
                raise AssertionError('receipt must remain unchanged')
        original = copy.deepcopy(self.state)
        with patch.object(legacy, 'http') as http:
            worker._reconcile_known_attempts(Ledger(), 'fixture', self.policy)
            http.assert_not_called()
        self.assertEqual(self.state, original)

    def test_retry_after_delta_date_absent_and_invalid_without_header_leak(self):
        for header, expected, valid in [('180', '180', True),
             ('Thu, 01 Jan 1970 00:20:00 GMT', '200.0', True),
             (None, '0', True), ('not-a-date', '0', False), ('-1', '0', False)]:
            headers = Message()
            if header is not None:
                headers['Retry-After'] = header
            headers['Secret-Test'] = 'do-not-copy'
            exc = HTTPError('https://fixture.invalid', 429, 'rate limit', headers,
                            BytesIO(b'{"error":{"code":429,"message":"rate limit"}}'))
            a = {}
            with patch.object(legacy.time, 'time', return_value=1000):
                legacy.record_http_failure(a, exc)
            self.assertEqual(a['http_rate_limit']['retry_after_seconds'], expected)
            self.assertEqual(a['http_rate_limit']['retry_after_valid'], valid)
            self.assertNotIn('do-not-copy', str(a))
        invalid = {**self.attempt, 'http_rate_limit': {'observed_at': 1000,
                   'retry_after_seconds': '0', 'retry_after_valid': False}}
        self.assertIsNone(campaign.rate_limit_recovery(invalid, self.policy))

    def test_same_pinned_model_prefers_alternate_eligible_endpoint_once(self):
        self.attempt['endpoint'] = 'provider-a'
        self.directive['retry_of_attempt_sha256'] = protocol.sha256_value(self.attempt)
        eligible = [(Decimal('.01'), {'tag': 'provider-a'}, {'model': 'pinned/model'}),
                    (Decimal('.02'), {'tag': 'provider-b'}, {'model': 'pinned/model'})]
        chosen = worker._prefer_alternate_rate_limit_endpoint(
            eligible, self.state, 'cycle', 'blind:deepseek', self.directive, self.policy)
        self.assertEqual(chosen, eligible[1:])
        self.assertEqual(worker._prefer_alternate_rate_limit_endpoint(
            eligible[:1], self.state, 'cycle', 'blind:deepseek', self.directive, self.policy), eligible[:1])
        self.assertEqual(worker._prefer_alternate_rate_limit_endpoint(
            eligible, self.state, 'cycle', 'blind:deepseek', {}, self.policy), eligible)

    def test_no_underreservation_or_policy_limit_expansion(self):
        for edit in ({'reserved': '.10001'}, {'reserved': '0'}):
            with self.subTest(edit=edit), self.assertRaises(ValueError):
                campaign.rate_limit_recovery({**self.attempt, **edit}, self.policy)
        self.policy['http_429_recovery']['max_attempts_per_slot'] = 3
        with self.assertRaises(ValueError):
            campaign.rate_limit_recovery(self.attempt, self.policy)


if __name__ == '__main__':
    unittest.main()
