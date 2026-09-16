"""Regression checks against skipped phases, accidental retries and stale dispatch."""
import copy
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from tools import independent_branch_continuation as c
from tools import independent_branch_protocol as p
from tools import independent_branch_worker as w
from tools import single_review_worker as transport
from tools import context_capsule


FAMILIES = ['deepseek', 'qwen', 'glm', 'xiaomi']


def response(family, disposition='NO_CHANGE', verdict='APPROVE'):
    finding = {'disposition': disposition, 'verdict': verdict, 'context_sufficiency': 'SUFFICIENT'}
    return {'finding': finding, 'finding_sha256': p.sha256_value(finding)}


def cycle():
    return {'baseline_sha256': p.sha256_text('Public baseline'), 'blind': {f: response(f) for f in FAMILIES}, 'reconcile': {}, 'final': {}, 'confirm': {}}


def final_directive(value):
    return {'phase': 'FINAL', 'merged_candidate_sha256': 'c' * 64,
            'source_packet_sha256': 'a' * 64,
            'private_baseline_commitment': {'baseline_sha256': value['baseline_sha256']},
            'synthesis_audit': {'baseline_text': 'Public baseline', 'public_baseline_approved': True,
                'dispositions': {key: {'decision': 'RETAIN', 'reason': 'Source supports disposition', 'evidence_refs': ['source:fixture']}
                                 for key in [*p.synthesis_evidence(value, FAMILIES), 'BASELINE']}},
            'branch_closures': {f: {'finding_sha256': value['blind'][f]['finding_sha256'],
                                   'outcome': 'NO_FOLLOWUP_NEEDED',
                                   'reason': 'Existing source covers the attempted counterexample.'}
                                for f in FAMILIES}}


class PhaseGuards(unittest.TestCase):
    def test_context_sufficient_cannot_hide_expansion_request(self):
        for extra in ({'requested_context': [{'query': 'AuthorityScope'}]},
                      {'requested_dependency_or_source_refs': ['AuthorityScope']},
                      {'missing_context_reason': 'Source missing'}):
            finding = {'context_sufficiency': 'SUFFICIENT', 'missing_context_reason': '',
                       'requested_dependency_or_source_refs': [], **extra}
            with self.assertRaisesRegex(ValueError, 'SUFFICIENT cannot'):
                context_capsule.validate_context_verdict(finding)

    def test_approval_cannot_hide_unresolved_material_findings(self):
        finding = {'verdict': 'APPROVE', 'material_findings': ['authority bypass'],
                   'missing_evidence': [], 'surviving_counterexamples': [], 'affected_invariants': [],
                   'proposed_patch': '', 'uncertainty': '', 'overturn_conditions': '',
                   'context_sufficiency': 'SUFFICIENT', 'missing_context_reason': '',
                   'requested_dependency_or_source_refs': []}
        with self.assertRaisesRegex(ValueError, 'APPROVE cannot'):
            p.validate_final_review(finding, family='qwen', model_id='fixture', candidate_sha256='a'*64, phase='FINAL')

    def test_final_cannot_skip_initial_reviewers(self):
        value = cycle()
        directive = final_directive(value)
        del value['blind']['qwen']
        with self.assertRaisesRegex(ValueError, 'all four initial'):
            w._plan(value, directive, FAMILIES)

    def test_reconciliation_waits_for_all_blind_reviews(self):
        value = cycle()
        del value['blind']['glm']
        with self.assertRaisesRegex(ValueError, 'all four initial'):
            w._plan(value, {'phase': 'RECONCILE'}, FAMILIES)

    def test_no_change_easy_case_requires_explicit_closure(self):
        value = cycle()
        with self.assertRaisesRegex(ValueError, 'four explicit branch closures'):
            w._plan(value, {'phase': 'FINAL'}, FAMILIES)
        self.assertEqual(w._plan(value, final_directive(value), FAMILIES), ('FINAL', 'deepseek', 'final:deepseek'))

    def test_material_finding_cannot_waive_followup(self):
        value = cycle()
        value['blind']['qwen'] = response('qwen', disposition='PROPOSE_DELTA')
        with self.assertRaisesRegex(ValueError, 'omit followup'):
            w._plan(value, final_directive(value), FAMILIES)

    def test_closure_binds_latest_branch_not_initial_answer(self):
        value = cycle()
        directive = final_directive(value)
        value['reconcile']['qwen'] = [response('qwen', disposition='PROPOSE_DELTA')]
        with self.assertRaisesRegex(ValueError, 'latest response'):
            w._plan(value, directive, FAMILIES)
        directive['branch_closures']['qwen'].update(outcome='RECONCILED', finding_sha256=value['reconcile']['qwen'][-1]['finding_sha256'])
        directive['synthesis_audit'] = final_directive(value)['synthesis_audit']
        self.assertIsNotNone(w._plan(value, directive, FAMILIES))

    def test_closure_cannot_change_during_final_review(self):
        value = cycle()
        directive = final_directive(value)
        w._plan(value, directive, FAMILIES)
        directive['branch_closures']['glm']['reason'] = 'Different assessment'
        with self.assertRaisesRegex(ValueError, 'closures changed'):
            w._plan(value, directive, FAMILIES)

    def test_reconciliation_cannot_reopen_after_final_starts(self):
        value = cycle()
        value['final']['deepseek'] = response('deepseek')
        with self.assertRaisesRegex(ValueError, 'after final review'):
            w._plan(value, {'phase': 'RECONCILE'}, FAMILIES)

    def test_unresolved_confirmation_produces_disagreement_receipt(self):
        for verdict in ('BLOCK', 'APPROVE_WITH_PATCH'):
            value = cycle()
            value['confirm'] = {f: response(f) for f in FAMILIES}
            value['confirm']['glm'] = response('glm', verdict=verdict)
            self.assertEqual(w._result_status(value, 'CONFIRM', FAMILIES), 'ESCALATE_UNRESOLVED')
            self.assertEqual(value['disagreement_receipt']['families'], ['glm'])
            self.assertFalse(value['disagreement_receipt']['semantic_delta_admitted'])

    def test_agreement_still_needs_chatgpt_final_decision(self):
        value = cycle()
        value['confirm'] = {f: response(f) for f in FAMILIES}
        self.assertEqual(w._result_status(value, 'CONFIRM', FAMILIES), 'AWAITING_CHATGPT_FINAL_DECISION')

    def test_retry_requires_receipt_binding_and_is_bounded(self):
        attempt = {'cycle': 'c', 'slot': 's', 'inference_reserved': True, 'status': 'INCOMPLETE'}
        state = {'attempts': [attempt]}
        with self.assertRaisesRegex(ValueError, 'explicit receipt-bound'):
            w._require_explicit_retry(state, 'c', 's', {})
        directive = {'retry_of_attempt_sha256': p.sha256_value(attempt), 'retry_reason': 'Output truncation addressed'}
        w._require_explicit_retry(state, 'c', 's', directive)
        state['attempts'].append(copy.deepcopy(attempt))
        with self.assertRaisesRegex(ValueError, 'two attempts'):
            w._require_explicit_retry(state, 'c', 's', directive)

    def test_unknown_receipt_cannot_authorize_retry(self):
        attempt = {'cycle': 'c', 'slot': 's', 'inference_reserved': True, 'status': 'UNKNOWN'}
        with self.assertRaisesRegex(ValueError, 'unresolved'):
            w._require_explicit_retry({'attempts': [attempt]}, 'c', 's',
                                     {'retry_of_attempt_sha256': p.sha256_value(attempt), 'retry_reason': 'retry'})


class ActiveContinuationGuards(unittest.TestCase):
    def setUp(self):
        self.state = {'scope': 'PUBLIC_MATRIX_REVIEW_ONLY', 'paused': False, 'attempts': [],
                      'admitted_source_commit': 'head', 'executor_revision_v3': 'revision',
                      'continuation': {'status': 'READY'}}
        owner = self
        class Ledger:
            def __init__(self, token): self.value = owner.state
            def save(self, value): owner.state = value
        self.ledger = Ledger

    def dispatch(self, event='schedule'):
        with patch.dict(os.environ, {'GH_REVIEW_TOKEN': 'fixture', 'GITHUB_SHA': 'head'}), \
                patch.object(c, 'host_check', return_value=event), \
                patch.object(c, '_digest_files', return_value='revision'), \
                patch.object(transport, 'GitLedger', self.ledger), \
                patch.object(transport, 'http', return_value={}) as http:
            c.dispatch(Path('.'))
            return http.call_count

    def test_scheduled_recovery_refuses_stale_executor(self):
        self.state['executor_revision_v3'] = 'old'
        self.assertEqual(self.dispatch(), 0)
        self.assertEqual(self.state['continuation']['status'], 'AWAITING_CHATGPT_BASELINE_OR_DIRECTIVE')

    def test_unknown_call_remains_visible_across_source_change(self):
        self.state['admitted_source_commit'] = 'old'
        self.state['attempts'] = [{'status': 'UNKNOWN', 'run_id': '123', 'model': 'qwen'}]
        self.assertEqual(self.dispatch('push'), 0)
        self.assertEqual(self.state['continuation']['status'], 'BLOCKED_UNRESOLVED_CALL')
        self.assertEqual(self.state['continuation']['attempts'][0]['run_id'], '123')
        self.assertEqual(self.state['attempts'][0]['status'], 'UNKNOWN')

    def test_ready_dispatch_and_lost_delivery_recovery_are_bounded(self):
        self.assertEqual(self.dispatch(), 1)
        self.assertEqual(self.dispatch(), 0)
        self.state['continuation']['updated'] = 0
        self.assertEqual(self.dispatch(), 1)
        self.state['continuation']['updated'] = 0
        self.assertEqual(self.dispatch(), 0)
        self.assertEqual(self.state['continuation']['reason'], 'DISPATCH_DELIVERY_UNCONFIRMED')

    def test_daily_deferral_waits_and_context_hold_does_not_dispatch(self):
        self.state['continuation'] = {'status': 'DEFERRED_DAILY', 'resume_after': 10**12}
        self.assertEqual(self.dispatch(), 0)
        self.state['continuation'] = {'status': 'AWAITING_CHATGPT_CONTEXT_EXPANSION'}
        self.assertEqual(self.dispatch(), 0)


if __name__ == '__main__':
    unittest.main()
