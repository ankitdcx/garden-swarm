"""Adversarial regressions for integrator filtering and post-blind disclosure."""
import copy
import unittest
from tools import independent_branch_protocol as p
from tools import independent_branch_worker as w
from tools import reviewer_quality_runtime as quality
from tests.test_review_phase_guards import FAMILIES, cycle, final_directive, response
from tests.test_reviewer_quality_runtime import state, REGISTRY


class SynthesisAuditTests(unittest.TestCase):
    def setUp(self):
        self.cycle = cycle()
        self.directive = final_directive(self.cycle)

    def packet(self):
        return p.synthesis_audit_packet(self.cycle, self.directive, FAMILIES)

    def test_missing_audit_blocks_final_before_provider(self):
        del self.directive['synthesis_audit']
        with self.assertRaisesRegex(ValueError, 'public baseline'):
            w._plan(self.cycle, self.directive, FAMILIES)

    def test_baseline_cannot_be_rewritten_after_seeing_reviews(self):
        self.directive['synthesis_audit']['baseline_text'] += ' changed'
        with self.assertRaisesRegex(ValueError, 'commitment mismatch'):
            self.packet()

    def test_private_baseline_cannot_be_disclosed_implicitly(self):
        self.directive['synthesis_audit']['public_baseline_approved'] = False
        with self.assertRaisesRegex(ValueError, 'public baseline'):
            self.packet()

    def test_integrator_cannot_drop_disposition(self):
        del self.directive['synthesis_audit']['dispositions']['BLIND:pareto:0']
        with self.assertRaisesRegex(ValueError, 'every original'):
            self.packet()

    def test_integrator_cannot_alter_original_finding(self):
        self.cycle['blind']['pareto']['finding']['disposition'] = 'HIDDEN'
        with self.assertRaisesRegex(ValueError, 'finding hash mismatch'):
            self.packet()

    def test_rejected_initial_finding_survives_chatgpt_synthesis(self):
        self.directive['synthesis_audit']['dispositions']['BLIND:pareto:0']['decision'] = 'REJECT'
        packet = self.packet()
        self.assertIn('BLIND:pareto:0', packet['evidence'])
        self.assertNotIn('RECONCILE:pareto:1', packet['evidence'])
        self.assertFalse(packet['independent_blind_evidence'])

    def test_audit_is_immutable_across_final_reviewers(self):
        w._plan(self.cycle, self.directive, FAMILIES)
        self.directive['synthesis_audit']['dispositions']['BASELINE']['reason'] = 'Changed rationale'
        with self.assertRaisesRegex(ValueError, 'audit changed'):
            w._plan(self.cycle, self.directive, FAMILIES)

    def review(self, packet):
        return {'verdict': 'APPROVE', 'synthesis_audit_sha256': packet['packet_sha256'],
                'disposition_audit': {key: {'verdict': 'SUPPORTED', 'reason': 'Checked source.'} for key in packet['evidence']}}

    def test_auditor_cannot_omit_original_finding(self):
        packet = self.packet(); review = self.review(packet)
        del review['disposition_audit']['BLIND:pareto:0']
        with self.assertRaisesRegex(ValueError, 'every synthesis'):
            p.validate_synthesis_audit_response(review, packet)

    def test_unresolved_or_contested_disposition_cannot_approve(self):
        packet = self.packet(); review = self.review(packet)
        review['disposition_audit']['BASELINE']['verdict'] = 'BLOCK'
        with self.assertRaisesRegex(ValueError, 'must BLOCK'):
            p.validate_synthesis_audit_response(review, packet)
        packet['dispositions']['BASELINE']['decision'] = 'UNRESOLVED'
        review = self.review(packet)
        with self.assertRaisesRegex(ValueError, 'must BLOCK'):
            p.validate_synthesis_audit_response(review, packet)

    def test_final_prompt_contains_complete_audit_and_no_final_peer_answer(self):
        packet = self.packet()
        prompt = p.final_prompt(target={'target_id': 'T', 'review_question': 'Q'}, source='source', trace={},
                                merged_candidate='candidate', phase='FINAL', audit_packet=packet)
        self.assertIn('Public baseline', prompt)
        self.assertIn('BLIND:pareto:0', prompt)
        self.assertIn('not fresh independent blind evidence', prompt)

    def test_quality_queue_accepts_only_bound_post_blind_exposure(self):
        value = state(); c = value['convergence_cycles']['cycle']; a = value['attempts'][0]
        r = c['blind'].pop('deepseek'); c['final']['deepseek'] = r
        for row in (a, r):
            row.update(phase='FINAL', synthesis_audit_sha256='d'*64)
        r.update(peer_content_seen=True, evidence_stage='POST_BLIND_SYNTHESIS_AUDIT')
        c['final_synthesis_audit_sha256'] = 'd'*64
        self.assertEqual(quality.queue_pending_assessments(copy.deepcopy(value), REGISTRY), 1)
        a['synthesis_audit_sha256'] = 'e'*64
        with self.assertRaisesRegex(ValueError, 'peer-content'):
            quality.queue_pending_assessments(value, REGISTRY)


if __name__ == '__main__':
    unittest.main()
