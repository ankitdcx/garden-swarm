import copy
from decimal import Decimal
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools import review_campaign as campaign
from tools import single_review_worker as legacy
from tools import independent_branch_worker as worker
from tools import independent_branch_continuation as continuation


class ReviewCampaignTests(unittest.TestCase):
    def setUp(self):
        self.policy = campaign.load_campaign()
        self.attempt = {'run_id': 'old-run', 'model': 'qwen/test', 'status': 'UNKNOWN',
                        'cost': None, 'reserved': '.05', 'utc_day': '1970-01-02',
                        'usage_daily_before': '0',
                        'administrative_disposition': {'status': 'CLOSED_ABANDONED_BY_USER'}}
        rule = self.policy['abandoned_attempts'][0]
        rule.update(attempt_sha256=campaign.digest(self.attempt), run_id='old-run', model='qwen/test')
        self.state = {'paused': False, 'attempts': [self.attempt]}

    def test_original_unknown_receipt_is_never_rewritten(self):
        before = copy.deepcopy(self.attempt)
        self.assertEqual(campaign.accounting_charge(self.attempt, self.policy), Decimal('.05'))
        self.assertEqual(campaign.blocking_attempts(self.state, self.policy), [])
        self.assertEqual(self.attempt, before)
        self.assertIsNone(self.attempt['cost'])
        self.assertEqual(self.attempt['status'], 'UNKNOWN')

    def test_no_general_exception_for_another_unknown_or_inflight_call(self):
        for change in ({'run_id': 'new-run'}, {'model': 'other/model'}, {'reserved': '.06'},
                       {'status': 'RESERVED'}, {'cost': '0'}, {'extra_field': 'changed'}):
            with self.subTest(change=change):
                a = {**self.attempt, **change}
                self.assertEqual(campaign.blocking_attempts({'attempts': [a]}, self.policy), [a])

    def test_absent_campaign_preserves_old_fail_closed_behavior(self):
        self.assertEqual(campaign.blocking_attempts(self.state), [self.attempt])
        with self.assertRaises(ValueError):
            campaign.accounting_charge(self.attempt)

    def test_insufficient_allowance_and_fake_success_are_rejected(self):
        for edit in ({'accounting_allowance_usd': '.01'}, {'retry_allowed': True},
                     {'review_evidence_admissible': True}, {'billing_status': 'KNOWN'}):
            p = copy.deepcopy(self.policy)
            p['abandoned_attempts'][0].update(edit)
            with self.subTest(edit=edit), self.assertRaises(ValueError):
                campaign.abandonment_charge(self.attempt, p)

    def test_total_ceiling_survives_day_and_target_changes(self):
        self.state['attempts'].append({'status': 'REVIEW_RECORDED', 'cost': '9.85',
                                      'utc_day': '1970-01-01', 'target_id': 'old-target'})
        receipt = campaign.check_total(self.state, self.policy, '.10')
        self.assertEqual(Decimal(receipt['accounted_before_usd']), Decimal('9.90'))
        self.assertFalse(receipt['abandoned_allowance_is_actual_billing'])
        with self.assertRaisesRegex(ValueError, 'total'):
            campaign.check_total(self.state, self.policy, '.10001')

    def test_campaign_requires_exact_source_and_identity(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            dest = root / campaign.POLICY_PATH
            dest.parent.mkdir()
            dest.write_text(json.dumps(self.policy))
            directive = {'campaign_id': self.policy['campaign_id']}
            self.assertEqual(campaign.bind_campaign(directive, self.policy['source_sha256'], root), self.policy)
            for d, source in [(directive, 'different-source'), ({'campaign_id': 'other'}, self.policy['source_sha256'])]:
                with self.assertRaisesRegex(ValueError, 'exact source'):
                    campaign.bind_campaign(d, source, root)
            self.assertIsNone(campaign.bind_campaign({}, 'different-source', root))

    def test_untrusted_directive_cannot_raise_limit(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            dest = root / campaign.POLICY_PATH
            dest.parent.mkdir()
            dest.write_text(json.dumps(self.policy))
            bound = campaign.bind_campaign({'campaign_id': self.policy['campaign_id'],
                                            'total_ceiling_usd': '1000'}, self.policy['source_sha256'], root)
            self.assertEqual(bound['total_ceiling_usd'], '10.00')
            self.policy['total_ceiling_usd'] = '10.01'
            dest.write_text(json.dumps(self.policy))
            with self.assertRaisesRegex(ValueError, 'authorization'):
                campaign.load_campaign(root)

    def test_reconciliation_does_not_retry_or_query_abandoned_call(self):
        class Ledger:
            value = self.state
            def save(self, value):
                raise AssertionError('abandoned original must not change')
        with patch.object(legacy, 'http') as http:
            worker._reconcile_known_attempts(Ledger(), 'fixture', self.policy)
            http.assert_not_called()
        with self.assertRaisesRegex(ValueError, 'unidentified'):
            worker._reconcile_known_attempts(Ledger(), 'fixture')

    def test_live_key_and_total_budget_still_apply(self):
        policy = json.loads(Path('agents/openrouter-paid-review-policy.json').read_text())
        bounded = campaign.spending_policy(policy, self.policy)
        key = {'usage': '.0024624', 'usage_daily': '0', 'limit_remaining': '20'}
        reserve, _, _ = legacy.budget_check(self.state, key, bounded, 100000, campaign=self.policy)
        self.assertEqual(reserve, Decimal('.10'))
        for edit in ({'usage': '9.90'}, {'usage_daily': '10'}, {'limit_remaining': '.09'}, {'usage_daily': None}):
            with self.subTest(edit=edit), self.assertRaises(ValueError):
                legacy.budget_check(self.state, {**key, **edit}, bounded, 100000, campaign=self.policy)
        self.state['attempts'].append({'status': 'UNKNOWN', 'reserved': '.10', 'cost': None})
        with self.assertRaisesRegex(ValueError, 'reconciliation'):
            legacy.budget_check(self.state, key, bounded, 100000, campaign=self.policy)

    def test_invalid_money_is_never_zero(self):
        for value in (None, True, '-1', 'NaN', 'Infinity', 'bad'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                campaign.amount(value)

    def test_staged_source_bound_directive_can_start_on_material_event(self):
        directive = json.loads(Path('review-inputs/v159/launch-directive.json').read_text())
        with patch.object(worker, 'load_directive', return_value=directive):
            ready = continuation.admitted_campaign_start(Path('.'), 'fixture')
        self.assertEqual(ready['status'], 'READY')
        self.assertEqual(ready['campaign_id'], 'GARDEN-V159-20260917')

    def test_source_event_does_not_invent_a_directive_or_reset_a_phase(self):
        for directive in (None, {}, {'start_on_matching_source_event': False}):
            with patch.object(worker, 'load_directive', return_value=directive):
                self.assertIsNone(continuation.admitted_campaign_start(Path('.'), 'fixture'))
        directive = json.loads(Path('review-inputs/v159/launch-directive.json').read_text())
        for edit in ({'phase': 'FINAL'}, {'source_packet_sha256': '0' * 64}):
            with patch.object(worker, 'load_directive', return_value={**directive, **edit}), self.assertRaises(ValueError):
                continuation.admitted_campaign_start(Path('.'), 'fixture')

    def test_registered_slice_must_belong_to_this_master(self):
        directive = json.loads(Path('review-inputs/v159/launch-directive.json').read_text())
        approved = campaign.load_campaign()
        source_hash = approved['source_slices'][0]['sha256']
        self.assertIsNotNone(campaign.bind_campaign(directive, source_hash))
        approved['source_slices'][0]['master_sha256'] = '0' * 64
        with patch.object(campaign, 'load_campaign', return_value=approved), self.assertRaises(ValueError):
            campaign.bind_campaign(directive, source_hash)


if __name__ == '__main__':
    unittest.main()
