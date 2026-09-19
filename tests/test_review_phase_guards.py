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


FAMILIES = ['deepseek', 'xiaomi', 'nvidia', 'pareto', 'mistral']


def response(family, disposition='NO_CHANGE', verdict='APPROVE'):
    finding = {'disposition': disposition, 'verdict': verdict, 'context_sufficiency': 'SUFFICIENT'}
    return {'finding': finding, 'finding_sha256': p.sha256_value(finding)}


def cycle():
    return {'baseline_sha256': p.sha256_text('Public baseline'),
            'blind': {f: response(f) for f in FAMILIES},
            'reconcile': {}, 'final': {}, 'confirm': {}}


def final_directive(value, closure_overrides=None):
    closure_overrides = closure_overrides or {}
    closures = {}
    for family in FAMILIES:
        row = {'finding_sha256': value['blind'][family]['finding_sha256'],
               'outcome': 'NO_FOLLOWUP_NEEDED',
               'reason': 'No material issue found in the source-bound blind finding.'}
        row.update(closure_overrides.get(family, {}))
        closures[family] = row
    evidence_keys = [*p.synthesis_evidence(value, FAMILIES), 'BASELINE']
    return {'phase': 'FINAL', 'merged_candidate_sha256': 'c' * 64,
            'source_packet_sha256': 'a' * 64,
            'private_baseline_commitment': {'baseline_sha256': value['baseline_sha256']},
            'synthesis_audit': {'baseline_text': 'Public baseline', 'public_baseline_approved': True,
                'dispositions': {key: {'decision': 'RETAIN', 'reason': 'Source supports disposition',
                                      'evidence_refs': ['source:fixture']}
                                 for key in evidence_keys}},
            'branch_closures': closures}


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
            p.validate_final_review(finding, family='deepseek', model_id='fixture',
                                    candidate_sha256='a'*64, phase='FINAL')

    def test_final_cannot_skip_any_initial_reviewer(self):
        value = cycle()
        directive = final_directive(value)
        del value['blind']['mistral']
        with self.assertRaisesRegex(ValueError, 'all five initial'):
            w._plan(value, directive, FAMILIES)

    def test_model_reconciliation_phase_is_not_live_v2(self):
        policy = p.load_policy(__import__('json').loads(
            Path('agents/independent-branch-convergence-policy.json').read_text()))
        self.assertNotIn('RECONCILE', p.PHASES)
        self.assertEqual(policy['branch_protocol']['model_followups_per_branch'], 0)

    def test_final_requires_five_explicit_closures(self):
        value = cycle()
        with self.assertRaisesRegex(ValueError, 'five explicit branch closures'):
            w._plan(value, {'phase': 'FINAL'}, FAMILIES)
        self.assertEqual(w._plan(value, final_directive(value), FAMILIES),
                         ('FINAL', 'deepseek', 'final:deepseek'))

    def test_material_finding_cannot_be_closed_as_no_followup(self):
        value = cycle()
        value['blind']['pareto'] = response('pareto', disposition='PROPOSE_DELTA')
        directive = final_directive(value)
        with self.assertRaisesRegex(ValueError, 'NO_FOLLOWUP_NEEDED requires'):
            w._plan(value, directive, FAMILIES)

    def test_material_finding_can_close_only_with_evidence_bound_disposition(self):
        value = cycle()
        value['blind']['pareto'] = response('pareto', disposition='PROPOSE_DELTA')
        directive = final_directive(value, {
            'pareto': {'outcome': 'INTEGRATED_FOR_FINAL_AUDIT',
                       'evidence_refs': ['patch:test', 'regression:test']}
        })
        self.assertEqual(w._plan(value, directive, FAMILIES),
                         ('FINAL', 'deepseek', 'final:deepseek'))
        bad = final_directive(value, {
            'pareto': {'outcome': 'REJECTED_WITH_EVIDENCE', 'evidence_refs': []}
        })
        with self.assertRaisesRegex(ValueError, 'requires evidence_refs'):
            w._plan(cycle() | {'blind': value['blind']}, bad, FAMILIES)

    def test_unresolved_material_branch_blocks_final(self):
        value = cycle()
        directive = final_directive(value, {
            'deepseek': {'outcome': 'UNRESOLVED_BLOCK'}
        })
        with self.assertRaisesRegex(ValueError, 'unresolved material'):
            w._plan(value, directive, FAMILIES)

    def test_closure_cannot_change_during_final_review(self):
        value = cycle()
        directive = final_directive(value)
        w._plan(value, directive, FAMILIES)
        directive['branch_closures']['xiaomi']['reason'] = 'Different assessment'
        with self.assertRaisesRegex(ValueError, 'closures changed'):
            w._plan(value, directive, FAMILIES)

    def test_unresolved_confirmation_produces_disagreement_receipt(self):
        for verdict in ('BLOCK', 'APPROVE_WITH_PATCH'):
            value = cycle()
            value['confirm'] = {f: response(f) for f in FAMILIES}
            value['confirm']['mistral'] = response('mistral', verdict=verdict)
            self.assertEqual(w._result_status(value, 'CONFIRM', FAMILIES), 'ESCALATE_UNRESOLVED')
            self.assertEqual(value['disagreement_receipt']['families'], ['mistral'])
            self.assertFalse(value['disagreement_receipt']['semantic_delta_admitted'])

    def test_agreement_still_needs_chatgpt_final_decision(self):
        value = cycle()
        value['confirm'] = {f: response(f) for f in FAMILIES}
        self.assertEqual(w._result_status(value, 'CONFIRM', FAMILIES),
                         'AWAITING_CHATGPT_FINAL_DECISION')

    def test_retry_requires_receipt_binding_and_is_bounded(self):
        attempt = {'cycle': 'c', 'slot': 's', 'inference_reserved': True, 'status': 'INCOMPLETE'}
        state = {'attempts': [attempt]}
        with self.assertRaisesRegex(ValueError, 'explicit receipt-bound'):
            w._require_explicit_retry(state, 'c', 's', {})
        directive = {'retry_of_attempt_sha256': p.sha256_value(attempt),
                     'retry_reason': 'Output truncation addressed'}
        w._require_explicit_retry(state, 'c', 's', directive)
        state['attempts'].append(copy.deepcopy(attempt))
        with self.assertRaisesRegex(ValueError, 'two attempts'):
            w._require_explicit_retry(state, 'c', 's', directive)

    def test_unknown_receipt_cannot_authorize_retry(self):
        attempt = {'cycle': 'c', 'slot': 's', 'inference_reserved': True, 'status': 'UNKNOWN'}
        with self.assertRaisesRegex(ValueError, 'unresolved'):
            w._require_explicit_retry({'attempts': [attempt]}, 'c', 's',
                                      {'retry_of_attempt_sha256': p.sha256_value(attempt),
                                       'retry_reason': 'retry'})


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
        self.state['attempts'] = [{'status': 'UNKNOWN', 'run_id': '123', 'model': 'deepseek'}]
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
